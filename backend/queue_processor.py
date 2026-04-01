"""
Background queue processor for analyzing leads.
Runs continuously and processes queued conversations.
"""
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def process_single_lead(
    conversation: Dict[str, Any],
    account_id: int,
    lead_id: int,
    intent: str,
    confidence: str,
    reasoning: str
) -> bool:
    """
    Process a single lead: run deep analysis and generate messages.
    Returns True if successful, False otherwise.
    """
    from database import save_analysis, save_messages
    from prompts import create_analysis_prompt, create_catchup_messages_prompt, create_no_thanks_messages_prompt
    from server import call_openai
    
    profile = conversation.get('correspondentProfile', {})
    lead_name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
    lead_company = profile.get('companyName', '')
    lead_position = profile.get('position', '')
    
    try:
        # Step 1: Deep analysis with web search
        logger.info(f"Running deep analysis for {lead_name} (intent={intent})")
        
        analysis_prompt = create_analysis_prompt(conversation)
        analysis = await call_openai(analysis_prompt, use_web_search=True, timeout_sec=180)
        
        # Save analysis to DB
        save_analysis(lead_id, analysis)
        logger.info(f"Analysis saved for {lead_name}")
        
        # Step 2: Generate messages
        logger.info(f"Generating messages for {lead_name}")
        
        if intent == 'soft_objection':
            msg_prompt = create_no_thanks_messages_prompt(
                analysis, lead_name, lead_company, lead_position
            )
        else:
            msg_prompt = create_catchup_messages_prompt(
                analysis, lead_name, lead_company, lead_position, intent
            )
        
        messages_data = await call_openai(msg_prompt, use_web_search=False, timeout_sec=120)
        
        # Save messages to DB
        save_messages(lead_id, messages_data)
        logger.info(f"Messages saved for {lead_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing lead {lead_name}: {e}")
        raise


async def queue_processor():
    """
    Main queue processor loop.
    Runs in background and processes pending conversations.
    """
    from database import (
        get_next_pending_queue_item, 
        update_queue_status,
        save_lead,
        save_classification
    )
    from classifier import classify_conversations
    from webhook_handler import fetch_conversation_from_heyreach
    
    logger.info("Queue processor started")
    
    while True:
        try:
            # Get next pending item from queue
            queue_item = get_next_pending_queue_item()
            
            if not queue_item:
                # No pending items, wait before checking again
                await asyncio.sleep(5)
                continue
            
            queue_id = queue_item['id']
            conversation_id = queue_item['conversation_id']
            account_id = queue_item['account_id']
            
            # Mark as processing
            update_queue_status(queue_id, 'processing')
            logger.info(f"Processing conversation {conversation_id} (queue_id={queue_id})")
            
            try:
                # Fetch full conversation from HeyReach
                conversation = await fetch_conversation_from_heyreach(conversation_id, account_id)
                
                if not conversation:
                    raise Exception(f"Could not fetch conversation {conversation_id} from HeyReach")
                
                # Save lead profile
                profile = conversation.get('correspondentProfile', {})
                lead_id = save_lead(conversation_id, account_id, profile)
                
                # Classify conversation
                logger.info(f"Classifying conversation {conversation_id}")
                classifications = await classify_conversations([conversation])
                
                if not classifications:
                    raise Exception("No classification result")
                
                classification = classifications[0]
                intent = classification['intent']
                confidence = classification['confidence']
                reasoning = classification.get('reasoning', '')
                
                # Save classification
                save_classification(lead_id, intent, confidence, reasoning)
                logger.info(f"Classification saved: {intent} (confidence={confidence})")
                
                # Skip analysis for certain intents
                if intent in ['hard_rejection', 'ooo', 'competitor']:
                    logger.info(f"Skipping deep analysis for intent={intent}, lead={lead_id}")
                    update_queue_status(queue_id, 'completed')
                    continue
                
                # Process lead: deep analysis + messages
                success = await process_single_lead(
                    conversation, account_id, lead_id, intent, confidence, reasoning
                )
                
                if success:
                    update_queue_status(queue_id, 'completed')
                    logger.info(f"Successfully processed conversation {conversation_id}")
                else:
                    update_queue_status(queue_id, 'error', 'Processing returned False')
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error processing queue item {queue_id}: {error_msg}")
                update_queue_status(queue_id, 'error', error_msg)
                
        except Exception as e:
            logger.error(f"Queue processor error: {e}")
            await asyncio.sleep(5)
        
        # Small delay between processing items
        await asyncio.sleep(1)


def start_queue_processor():
    """Start the queue processor as a background task."""
    asyncio.create_task(queue_processor())
    logger.info("Queue processor background task started")
