"""
Webhook handler for HeyReach events.
Processes EVERY_MESSAGE_REPLY_RECEIVED events and queues conversations for analysis.
"""
import logging
import json
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
    
    ALWAYS queues the conversation for re-analysis when a new message is received.
    This ensures messages are updated with fresh context from the latest reply.

    Expected HeyReach webhook structure:
    {
        "is_inmail": false,
        "recent_messages": [
            {"creation_time": "2026-04-01T13:08:22.377Z", "message": "hey", "is_reply": true}
        ],
        "conversation_id": "2-OTE3...",
        "sender": {
            "id": 110357,
            "first_name": "Artem",
            "last_name": "Morozov",
            "full_name": "Artem Morozov",
            "profile_url": "https://www.linkedin.com/in/..."
        },
        "lead": {
            "id": "918418165",
            "profile_url": "https://www.linkedin.com/in/helen-..."
        }
    }

    Returns True if successfully queued, False otherwise.
    """
    from database import add_to_queue, save_lead, get_lead_by_conversation_id

    # Check if this is a HeyReach webhook (no 'event' field, has 'conversation_id')
    event_type = event_data.get('event', '')
    
    if event_type and event_type != 'EVERY_MESSAGE_REPLY_RECEIVED':
        logger.info(f"Ignoring event type: {event_type}")
        return False
    
    # Extract data based on HeyReach webhook structure
    conversation_id = event_data.get('conversation_id')
    account_id = event_data.get('sender', {}).get('id')
    
    # Fallback: check nested structure
    if not conversation_id:
        data = event_data.get('data', {})
        conversation_id = data.get('conversationId')
        account_id = data.get('linkedInAccountId')
    
    if not conversation_id or not account_id:
        logger.error(f"Missing conversation_id or sender.id in webhook data: {json.dumps(event_data)[:500]}")
        return False

    # Check if currently being processed (pending/processing)
    # We still want to re-process completed leads to update messages with new context
    from database import get_db_connection
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, status FROM processing_queue 
            WHERE conversation_id = ? AND status IN ('pending', 'processing')
            ORDER BY created_at DESC LIMIT 1
        """, (conversation_id,))
        row = cursor.fetchone()
        
        if row:
            logger.info(f"Conversation {conversation_id} already being processed (status={row['status']}), skipping duplicate webhook")
            return False
    
    # Always add to queue for new message - this triggers full re-analysis
    logger.info(f"New message from {conversation_id}, queueing for full re-analysis")
    queue_id = add_to_queue(conversation_id, account_id)

    if queue_id is None:
        # This shouldn't happen since we checked above, but log it
        logger.warning(f"Failed to queue conversation {conversation_id}")
        return False

    # Extract lead info from HeyReach webhook structure
    lead_data = event_data.get('lead', {})
    sender_data = event_data.get('sender', {})
    
    # Build profile from lead data (the person who replied)
    profile = {
        'firstName': lead_data.get('first_name', sender_data.get('first_name', '')),
        'lastName': lead_data.get('last_name', sender_data.get('last_name', '')),
        'companyName': '',  # Will be fetched from HeyReach API
        'position': '',  # Will be fetched from HeyReach API
        'location': '',
        'profileUrl': lead_data.get('profile_url', sender_data.get('profile_url', '')),
        'headline': '',
    }
    
    save_lead(conversation_id, account_id, profile)

    logger.info(f"Queued conversation {conversation_id} for analysis (queue_id={queue_id})")
    return True
