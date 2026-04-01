"""
Webhook handler for HeyReach events.
Processes EVERY_MESSAGE_REPLY_RECEIVED events and queues conversations for analysis.
"""
import logging
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _extract_message_timestamp(data: Dict[str, Any]) -> str:
    """Extract message timestamp from webhook payload.

    HeyReach may use different field names; fall back to current UTC time
    if none are found so we always have a value to compare.
    """
    message = data.get('message', {})
    for field in ('sentAt', 'timestamp', 'createdAt', 'sent_at', 'created_at'):
        value = message.get(field)
        if value:
            return str(value)
    return datetime.now(timezone.utc).isoformat()


async def fetch_conversation_from_heyreach(conversation_id: str, account_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch full conversation details from HeyReach API.
    """
    from server import HEYREACH_API_KEY
    
    url = "https://api.heyreach.io/api/public/inbox/GetConversationsV2"
    headers = {
        "X-API-KEY": HEYREACH_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Fetch specific conversation by ID
    payload = {
        "filters": {
            "linkedInAccountIds": [account_id],
            "conversationId": conversation_id
        },
        "offset": 0,
        "limit": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"HeyReach API error: {response.status_code} - {response.text[:200]}")
                return None
            
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                logger.warning(f"Conversation {conversation_id} not found")
                return None
            
            return items[0]
            
    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {e}")
        return None


async def process_webhook_event(event_data: Dict[str, Any]) -> bool:
    """
    Process incoming webhook event from HeyReach.
    
    Expected event structure:
    {
        "event": "EVERY_MESSAGE_REPLY_RECEIVED",
        "data": {
            "conversationId": "abc123",
            "linkedInAccountId": 12345,
            "message": {...},
            "correspondent": {...}
        }
    }
    
    Re-queues analysis whenever the incoming message is newer than the last
    stored analysis, so fresh replies always trigger a fresh run.

    Returns True if successfully queued, False otherwise.
    """
    from database import add_to_queue, save_lead, get_lead_analysis_time, update_last_message_at
    
    event_type = event_data.get('event', '')
    data = event_data.get('data', {})
    
    if event_type != 'EVERY_MESSAGE_REPLY_RECEIVED':
        logger.info(f"Ignoring event type: {event_type}")
        return False
    
    conversation_id = data.get('conversationId')
    account_id = data.get('linkedInAccountId')
    
    if not conversation_id or not account_id:
        logger.error(f"Missing conversationId or linkedInAccountId in webhook data: {data}")
        return False

    # Extract the timestamp of the incoming message
    message_ts = _extract_message_timestamp(data)

    # Save/update lead profile from webhook data early so last_message_at can be set
    correspondent = data.get('correspondent', {})
    if correspondent:
        profile = {
            'firstName': correspondent.get('firstName', ''),
            'lastName': correspondent.get('lastName', ''),
            'companyName': correspondent.get('companyName', ''),
            'position': correspondent.get('position', ''),
            'location': correspondent.get('location', ''),
            'profileUrl': correspondent.get('profileUrl', ''),
            'headline': correspondent.get('headline', ''),
        }
        save_lead(conversation_id, account_id, profile)

    # Record when this message arrived
    update_last_message_at(conversation_id, message_ts)

    # Decide whether to re-run analysis
    analyzed_at = get_lead_analysis_time(conversation_id)
    if analyzed_at and analyzed_at >= message_ts:
        logger.info(
            f"Lead {conversation_id} analysis is up to date "
            f"(analyzed_at={analyzed_at}, message_ts={message_ts}), skipping"
        )
        return False

    # Queue for (re-)analysis — add_to_queue skips if already pending/processing
    queue_id = add_to_queue(conversation_id, account_id)
    if queue_id is None:
        logger.info(f"Conversation {conversation_id} already in queue")
        return False

    logger.info(
        f"Queued conversation {conversation_id} for account {account_id} "
        f"(queue_id={queue_id}, message_ts={message_ts}, analyzed_at={analyzed_at})"
    )
    return True
