"""
Webhook handler for HeyReach events.
Processes EVERY_MESSAGE_REPLY_RECEIVED events and queues conversations for analysis.
"""
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


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
    
    Returns True if successfully queued, False otherwise.
    """
    from database import add_to_queue, save_lead, get_lead_by_conversation_id
    
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
    
    # Check if lead already exists and is fully processed
    existing_lead = get_lead_by_conversation_id(conversation_id)
    if existing_lead and existing_lead.get('messages'):
        logger.info(f"Lead {conversation_id} already processed, skipping")
        return False
    
    # Add to processing queue (will skip if already pending/processing)
    queue_id = add_to_queue(conversation_id, account_id)
    
    if queue_id is None:
        logger.info(f"Conversation {conversation_id} already in queue")
        return False
    
    # Save/update lead profile from webhook data
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
    
    logger.info(f"Queued conversation {conversation_id} for account {account_id} (queue_id={queue_id})")
    return True
