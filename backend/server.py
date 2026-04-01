from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import sys
import logging
import uuid
import asyncio
import json
import hashlib
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from pydantic import BaseModel
from json_repair import repair_json

ROOT_DIR = Path(__file__).parent
# Ensure backend/ is on sys.path so local modules resolve regardless of working directory
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / '.env')

from classifier import classify_conversations
from prompts import create_analysis_prompt, create_catchup_messages_prompt, create_no_thanks_messages_prompt
from database import init_db, get_all_leads_for_account, get_lead_by_conversation_id, get_queue_stats
from webhook_handler import process_webhook_event

HEYREACH_API_KEY = os.environ.get('HEYREACH_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

_accounts_raw = os.environ.get('LINKEDIN_ACCOUNTS', '[]')
LINKEDIN_ACCOUNTS = json.loads(_accounts_raw)

app = FastAPI()
api_router = APIRouter(prefix="/api")

# In-memory job store
jobs: Dict[str, Dict[str, Any]] = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")
    
    # Start background queue processor
    from queue_processor import start_queue_processor
    start_queue_processor()
    logger.info("Background queue processor started")


# ==================== HEYREACH API ====================

async def fetch_unread_conversations(account_id: int) -> list:
    """Fetch all unread conversations from HeyReach API"""
    url = "https://api.heyreach.io/api/public/inbox/GetConversationsV2"
    headers = {"X-API-KEY": HEYREACH_API_KEY, "Content-Type": "application/json"}
    payload = {
        "filters": {
            "linkedInAccountIds": [account_id],
            "seen": False
        },
        "offset": 0,
        "limit": 50
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"HeyReach API error: {response.status_code} - {response.text}")
        data = response.json()
        return data.get('items', [])


# ==================== OPENAI HELPERS ====================

def extract_openai_text(data: dict) -> str:
    """Extract output text from OpenAI Responses API response"""
    output_array = data.get('output', [])
    for item in output_array:
        if item.get('type') == 'message':
            for content_item in item.get('content', []):
                if content_item.get('type') == 'output_text':
                    return content_item.get('text', '')
    return ''


def parse_json_from_text(text: str) -> dict:
    """Parse JSON from OpenAI response text, handling markdown wrappers and malformed JSON"""
    text = text.replace('```json', '').replace('```', '').strip()
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    if json_start != -1 and json_end > json_start:
        text = text[json_start:json_end]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = repair_json(text, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
        raise ValueError(f"Could not parse JSON even after repair")


async def call_openai(prompt: str, use_web_search: bool = False, timeout_sec: int = 180) -> dict:
    """Call OpenAI Responses API"""
    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o",
        "tools": [{"type": "web_search"}] if use_web_search else [],
        "input": prompt
    }

    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text[:500]}")
        data = response.json()
        output_text = extract_openai_text(data)
        if not output_text:
            raise Exception("No output_text in OpenAI response")
        return parse_json_from_text(output_text)



# ==================== BACKGROUND PIPELINE ====================

async def run_analysis_pipeline(job_id: str, account_id: int):
    """Main analysis pipeline running in background"""
    from database import save_lead, save_classification, save_analysis, save_messages
    
    job = jobs[job_id]
    try:
        # Step 1: Fetch conversations
        job['step'] = 'fetching'
        job['status_text'] = 'Fetching unread conversations from HeyReach...'
        logger.info(f"[{job_id}] Fetching conversations for account {account_id}")

        conversations = await fetch_unread_conversations(account_id)
        job['total_conversations'] = len(conversations)
        job['status_text'] = f'Found {len(conversations)} unread conversations. Classifying intent...'

        if not conversations:
            job['step'] = 'done'
            job['status_text'] = 'No unread conversations found'
            job['completed'] = True
            return

        # Step 2: Classify conversations by intent
        job['step'] = 'classifying'
        logger.info(f"[{job_id}] Classifying {len(conversations)} conversations")

        classifications = await classify_conversations(conversations)

        # Build index → classification map
        intent_map = {c['index']: c for c in classifications}

        # Collect conversations that were classified (have CORRESPONDENT in last 5)
        classified_convs = [(conversations[c['index']], c) for c in classifications if c['index'] < len(conversations)]

        job['total_leads'] = len(classified_convs)
        job['leads_info'] = []

        if not classified_convs:
            job['step'] = 'done'
            job['status_text'] = 'No conversations with recent replies found'
            job['completed'] = True
            return

        intent_counts = {}
        for _, cls in classified_convs:
            intent_counts[cls['intent']] = intent_counts.get(cls['intent'], 0) + 1
        counts_str = ', '.join(f"{k}: {v}" for k, v in intent_counts.items())

        job['status_text'] = f'Classified {len(classified_convs)} conversations ({counts_str}). Starting analysis...'

        # Populate lead info with intent
        for conv, cls in classified_convs:
            profile = conv.get('correspondentProfile', {})
            job['leads_info'].append({
                'name': f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
                'company': profile.get('companyName', ''),
                'position': profile.get('position', ''),
                'location': profile.get('location', ''),
                'profileUrl': profile.get('profileUrl', ''),
                'headline': profile.get('headline', ''),
                'intent': cls['intent'],
                'intent_confidence': cls['confidence'],
                'status': 'pending',
                'step': 'waiting',
                'conversation': conv
            })

        job['step'] = 'analyzing'

        # Step 3: Process each lead sequentially
        for idx, (conv, cls) in enumerate(classified_convs):
            lead_info = job['leads_info'][idx]
            lead_name = lead_info['name']
            lead_company = lead_info['company']
            intent = lead_info['intent']

            try:
                lead_info['status'] = 'processing'
                lead_info['step'] = 'analyzing'
                job['processed'] = idx
                job['status_text'] = f'Analyzing {lead_name} [{intent}] ({idx + 1}/{len(classified_convs)})...'
                logger.info(f"[{job_id}] Analyzing lead {idx + 1}: {lead_name} (intent={intent})")

                # Save lead to DB
                profile = conv.get('correspondentProfile', {})
                # Use conversationId from HeyReach, or generate from profile URL + account_id for stability
                conversation_id = conv.get('conversationId')
                if not conversation_id:
                    # Fallback: use profile URL + account_id as stable identifier
                    profile_url = profile.get('profileUrl', '')
                    if profile_url:
                        unique_str = f"{profile_url}:{account_id}"
                        conversation_id = hashlib.sha256(unique_str.encode()).hexdigest()[:16]
                    else:
                        conversation_id = str(uuid.uuid4())
                
                # Check if lead already exists (for logging)
                from database import get_lead_by_conversation_id
                existing_lead = get_lead_by_conversation_id(conversation_id)
                if existing_lead:
                    logger.info(f"[{job_id}] Updating existing lead: {lead_name} (conversation_id={conversation_id})")
                else:
                    logger.info(f"[{job_id}] Creating new lead: {lead_name} (conversation_id={conversation_id})")
                
                lead_id = save_lead(conversation_id, account_id, profile)

                # Save classification
                save_classification(lead_id, intent, cls['confidence'], cls.get('reasoning', ''))

                # Deep analysis
                analysis_prompt = create_analysis_prompt(conv)
                analysis = await call_openai(analysis_prompt, use_web_search=True, timeout_sec=180)
                lead_info['analysis'] = analysis

                # Save analysis to DB
                save_analysis(lead_id, analysis)

                # Select message prompt by intent
                lead_info['step'] = 'generating_messages'
                job['status_text'] = f'Generating messages for {lead_name} ({idx + 1}/{len(classified_convs)})...'
                logger.info(f"[{job_id}] Generating messages for {lead_name}")

                if intent == 'soft_objection':
                    msg_prompt = create_no_thanks_messages_prompt(
                        analysis, lead_name, lead_company, lead_info.get('position', '')
                    )
                else:
                    msg_prompt = create_catchup_messages_prompt(
                        analysis, lead_name, lead_company, lead_info.get('position', ''), intent
                    )

                messages_data = await call_openai(msg_prompt, use_web_search=False, timeout_sec=120)
                lead_info['messages_data'] = messages_data

                # Save messages to DB
                save_messages(lead_id, messages_data)

                lead_info['status'] = 'done'
                lead_info['step'] = 'done'
                logger.info(f"[{job_id}] Lead {lead_name} done")

            except Exception as e:
                logger.error(f"[{job_id}] Lead {lead_name} failed: {e}")
                lead_info['status'] = 'failed'
                lead_info['step'] = 'failed'
                lead_info['error'] = str(e)

            # Rate limiting pause between leads
            if idx < len(classified_convs) - 1:
                job['status_text'] = f'Completed {lead_name}. Pausing before next lead...'
                await asyncio.sleep(5)

        job['processed'] = len(classified_convs)
        job['step'] = 'done'
        job['completed'] = True
        done_count = sum(1 for l in job['leads_info'] if l['status'] == 'done')
        failed_count = sum(1 for l in job['leads_info'] if l['status'] == 'failed')
        job['status_text'] = f'Analysis complete! {done_count} successful, {failed_count} failed out of {len(classified_convs)} leads.'

    except Exception as e:
        logger.error(f"[{job_id}] Pipeline error: {e}")
        job['step'] = 'error'
        job['error'] = str(e)
        job['status_text'] = f'Error: {str(e)}'
        job['completed'] = True


# ==================== RETRY PIPELINE ====================

async def retry_leads_pipeline(job_id: str, lead_names: List[str]):
    """Re-run analysis for specific failed leads"""
    from database import save_analysis, save_messages
    
    job = jobs[job_id]
    try:
        leads_to_retry = [li for li in job['leads_info'] if li['name'] in lead_names]

        for idx, lead_info in enumerate(leads_to_retry):
            lead_name = lead_info['name']
            lead_company = lead_info['company']
            conv = lead_info.get('conversation', {})

            try:
                lead_info['status'] = 'processing'
                lead_info['step'] = 'analyzing'
                job['status_text'] = f'Retrying {lead_name} ({idx + 1}/{len(leads_to_retry)})...'
                logger.info(f"[{job_id}] Retrying lead: {lead_name}")

                analysis_prompt = create_analysis_prompt(conv)
                analysis = await call_openai(analysis_prompt, use_web_search=True, timeout_sec=180)
                lead_info['analysis'] = analysis

                # Save analysis to DB
                profile = conv.get('correspondentProfile', {})
                conversation_id = conv.get('conversationId', str(uuid.uuid4()))
                lead_id_result = get_lead_by_conversation_id(conversation_id)
                if lead_id_result:
                    save_analysis(lead_id_result['id'], analysis)

                lead_info['step'] = 'generating_messages'
                job['status_text'] = f'Generating messages for {lead_name} ({idx + 1}/{len(leads_to_retry)})...'

                intent = lead_info.get('intent', 'catchup_thanks')
                if intent == 'soft_objection':
                    msg_prompt = create_no_thanks_messages_prompt(
                        analysis, lead_name, lead_company, lead_info.get('position', '')
                    )
                else:
                    msg_prompt = create_catchup_messages_prompt(
                        analysis, lead_name, lead_company, lead_info.get('position', ''), intent
                    )
                messages_data = await call_openai(msg_prompt, use_web_search=False, timeout_sec=120)
                lead_info['messages_data'] = messages_data
                lead_info['error'] = None

                # Save messages to DB
                if lead_id_result:
                    save_messages(lead_id_result['id'], messages_data)

                lead_info['status'] = 'done'
                lead_info['step'] = 'done'
                logger.info(f"[{job_id}] Retry done: {lead_name}")

            except Exception as e:
                logger.error(f"[{job_id}] Retry failed for {lead_name}: {e}")
                lead_info['status'] = 'failed'
                lead_info['step'] = 'failed'
                lead_info['error'] = str(e)

            if idx < len(leads_to_retry) - 1:
                await asyncio.sleep(5)

        done_count = sum(1 for l in job['leads_info'] if l['status'] == 'done')
        failed_count = sum(1 for l in job['leads_info'] if l['status'] == 'failed')
        job['processed'] = len(job['leads_info'])
        job['step'] = 'done'
        job['completed'] = True
        job['status_text'] = f'Retry complete! {done_count} successful, {failed_count} failed.'

    except Exception as e:
        logger.error(f"[{job_id}] Retry pipeline error: {e}")
        job['step'] = 'error'
        job['error'] = str(e)
        job['status_text'] = f'Retry error: {str(e)}'
        job['completed'] = True


# ==================== API ENDPOINTS ====================

@api_router.get("/")
async def root():
    return {"message": "Interexy Lead Analyzer API"}


@api_router.get("/accounts")
async def get_accounts():
    """Return available LinkedIn accounts"""
    return {"accounts": LINKEDIN_ACCOUNTS}




@api_router.post("/webhook/heyreach")
async def heyreach_webhook(request: Request):
    """
    Webhook endpoint for HeyReach events.
    Handles EVERY_MESSAGE_REPLY_RECEIVED events.
    """
    try:
        body = await request.json()
        logger.info(f"Received webhook: {json.dumps(body)[:500]}")
        
        success = await process_webhook_event(body)
        
        if success:
            return {"status": "queued", "message": "Conversation queued for analysis"}
        else:
            return {"status": "skipped", "message": "Event skipped or already processed"}
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")


@api_router.get("/leads/{account_id}")
async def get_leads(account_id: int):
    """Get all analyzed leads for a specific account"""
    try:
        leads = get_all_leads_for_account(account_id)
        return {"leads": leads}
    except Exception as e:
        logger.error(f"Error fetching leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/queue/stats")
async def get_stats():
    """Get processing queue statistics"""
    stats = get_queue_stats()
    return {"stats": stats}


@api_router.get("/leads")
async def get_all_leads():
    """Get all leads from all accounts (for debugging)"""
    import sqlite3
    from database import get_db_connection

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT account_id FROM leads")
        account_ids = [row[0] for row in cursor.fetchall()]

    all_leads = []
    for acc_id in account_ids:
        leads = get_all_leads_for_account(acc_id)
        all_leads.extend(leads)

    return {"leads": all_leads, "total": len(all_leads)}


@api_router.delete("/leads/{conversation_id}")
async def delete_lead(conversation_id: str):
    """
    Delete a lead and all associated data (classifications, analyses, messages).
    """
    try:
        from database import delete_lead as db_delete_lead
        
        logger.info(f"Attempting to delete lead: {conversation_id}")
        deleted = db_delete_lead(conversation_id)
        
        if deleted:
            logger.info(f"Successfully deleted lead: {conversation_id}")
            return {"status": "success", "message": f"Lead {conversation_id} deleted"}
        else:
            logger.warning(f"Lead not found: {conversation_id}")
            raise HTTPException(status_code=404, detail="Lead not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lead {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete lead: {str(e)}")


class RunAnalysisRequest(BaseModel):
    account_id: int


@api_router.post("/run-analysis")
async def run_analysis(request: RunAnalysisRequest):
    """Start the analysis pipeline"""
    if not HEYREACH_API_KEY or not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing API keys configuration")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'job_id': job_id,
        'step': 'starting',
        'status_text': 'Starting analysis...',
        'total_conversations': 0,
        'total_leads': 0,
        'processed': 0,
        'leads_info': [],
        'completed': False,
        'error': None,
        'account_id': request.account_id,
        'created_at': datetime.now(timezone.utc).isoformat()
    }

    asyncio.create_task(run_analysis_pipeline(job_id, request.account_id))
    return {"job_id": job_id, "message": "Analysis started"}


class RetryLeadsRequest(BaseModel):
    job_id: str
    lead_names: List[str]


@api_router.post("/retry-leads")
async def retry_leads(request: RetryLeadsRequest):
    """Retry analysis for specific failed leads"""
    job = jobs.get(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.get('completed'):
        raise HTTPException(status_code=400, detail="Job is still running")

    for lead_info in job['leads_info']:
        if lead_info['name'] in request.lead_names:
            lead_info['status'] = 'pending'
            lead_info['step'] = 'waiting'
            lead_info['error'] = None

    job['completed'] = False
    job['step'] = 'retrying'
    job['status_text'] = f'Retrying {len(request.lead_names)} lead(s)...'
    job['error'] = None

    asyncio.create_task(retry_leads_pipeline(request.job_id, request.lead_names))
    return {"message": f"Retry started for {len(request.lead_names)} lead(s)"}


@api_router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get job status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    leads_summary = []
    for lead in job.get('leads_info', []):
        leads_summary.append({
            'name': lead.get('name', ''),
            'company': lead.get('company', ''),
            'position': lead.get('position', ''),
            'location': lead.get('location', ''),
            'intent': lead.get('intent', ''),
            'status': lead.get('status', 'pending'),
            'step': lead.get('step', 'waiting'),
            'error': lead.get('error')
        })

    return {
        'job_id': job_id,
        'step': job['step'],
        'status_text': job['status_text'],
        'total_conversations': job['total_conversations'],
        'total_leads': job['total_leads'],
        'processed': job['processed'],
        'completed': job['completed'],
        'error': job.get('error'),
        'leads': leads_summary
    }


@api_router.get("/results/{job_id}")
async def get_results(job_id: str):
    """Get full results"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    results = []
    for lead in job.get('leads_info', []):
        analysis = lead.get('analysis', {})
        messages_data = lead.get('messages_data', {})
        qualification = analysis.get('qualification', {})

        results.append({
            'name': lead.get('name', ''),
            'company': lead.get('company', ''),
            'position': lead.get('position', ''),
            'location': lead.get('location', ''),
            'profileUrl': lead.get('profileUrl', ''),
            'headline': lead.get('headline', ''),
            'intent': lead.get('intent', ''),
            'intent_confidence': lead.get('intent_confidence', ''),
            'status': lead.get('status', 'pending'),
            'error': lead.get('error'),
            'fit_score': qualification.get('fit_score', 0),
            'qualification_status': qualification.get('status', ''),
            'executive_summary': analysis.get('executive_summary', ''),
            'analysis': analysis,
            'messages': messages_data.get('messages', []),
            'recommended_top_3': messages_data.get('recommended_top_3', []),
            'strategy_notes': messages_data.get('notes', '')
        })

    return {
        'job_id': job_id,
        'completed': job['completed'],
        'total_leads': job['total_leads'],
        'results': results
    }


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
