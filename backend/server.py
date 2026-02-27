from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import uuid
import asyncio
import json
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from pydantic import BaseModel

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

HEYREACH_API_KEY = os.environ.get('HEYREACH_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
LINKEDIN_ACCOUNT_ID = os.environ.get('LINKEDIN_ACCOUNT_ID')

_accounts_raw = os.environ.get('LINKEDIN_ACCOUNTS', '[]')
LINKEDIN_ACCOUNTS = json.loads(_accounts_raw)

app = FastAPI()
api_router = APIRouter(prefix="/api")

# In-memory job store
jobs: Dict[str, Dict[str, Any]] = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
    """Parse JSON from OpenAI response text, handling markdown wrappers"""
    text = text.replace('```json', '').replace('```', '').strip()
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    if json_start != -1 and json_end > json_start:
        text = text[json_start:json_end]
    return json.loads(text)


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


# ==================== FILTERING LOGIC ====================

async def filter_catchup_leads(conversations: list) -> list:
    """Use OpenAI to filter conversations that are 'catch up' leads"""
    if not conversations:
        return []

    # Build a summary of conversations for batch filtering
    conv_summaries = []
    for idx, conv in enumerate(conversations):
        profile = conv.get('correspondentProfile', {})
        messages = conv.get('messages', [])
        last_sender = conv.get('lastMessageSender', '')
        last_text = conv.get('lastMessageText', '')

        # Get last few messages for context
        recent_msgs = messages[-5:] if len(messages) > 5 else messages
        msg_history = []
        for msg in recent_msgs:
            sender = "ME" if msg.get('sender') == 'ME' else "CORRESPONDENT"
            body = msg.get('body', '[no text]')[:200]
            msg_history.append(f"{sender}: {body}")

        conv_summaries.append({
            "index": idx,
            "name": f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
            "company": profile.get('companyName', ''),
            "position": profile.get('position', ''),
            "last_sender": last_sender,
            "last_message": last_text[:200] if last_text else '',
            "recent_messages": msg_history
        })

    prompt = f"""You are a B2B sales assistant analyzing LinkedIn conversations.

TASK: Analyze each conversation and identify "Catch Up" leads.

A "Catch Up" lead meets ALL these criteria:
1. The LAST message is from CORRESPONDENT (not ME)
2. The last message from ME before the correspondent's reply was a CONGRATULATION message (birthday, new role, work anniversary, promotion)
3. The correspondent replied with a positive acknowledgment like "Thanks", "Thank you", "Appreciate it", "Cheers", "Kind regards", etc.

EXCLUDE these:
- Cold outreach rejections ("Thanks but no", "Not interested", "No need")
- Conversations where the last message from ME was NOT a congratulation
- Conversations where the correspondent is asking questions about services (these are already engaged)
- Generic auto-replies

Analyze these conversations:

{json.dumps(conv_summaries, indent=2)}

Return ONLY valid JSON:
{{
  "catchup_leads": [list of index numbers that are Catch Up leads],
  "reasoning": {{
    "index_number": "brief reason why included/excluded"
  }}
}}"""

    try:
        result = await call_openai(prompt, use_web_search=False, timeout_sec=60)
        return result.get('catchup_leads', [])
    except Exception as e:
        logger.error(f"Filter error: {e}")
        # Fallback: simple keyword matching
        catchup_indices = []
        thank_keywords = ['thank', 'thanks', 'appreciate', 'cheers', 'glad', 'pleasure']
        for idx, conv in enumerate(conversations):
            last_sender = conv.get('lastMessageSender', '')
            last_text = (conv.get('lastMessageText', '') or '').lower()
            if last_sender == 'CORRESPONDENT' and any(kw in last_text for kw in thank_keywords):
                catchup_indices.append(idx)
        return catchup_indices


# ==================== ANALYSIS PROMPTS ====================

def create_analysis_prompt(conversation: dict) -> str:
    """Create the full framework analysis prompt"""
    correspondent = conversation.get('correspondentProfile', {})
    lead_name = f"{correspondent.get('firstName', '')} {correspondent.get('lastName', '')}".strip()
    lead_company = correspondent.get('companyName', 'Unknown Company')
    lead_position = correspondent.get('position', 'Unknown Position')
    lead_location = correspondent.get('location', '')
    lead_linkedin = correspondent.get('profileUrl', '')
    lead_headline = correspondent.get('headline', '')

    messages = conversation.get('messages', [])
    conversation_history = []
    for msg in messages:
        sender = "You" if msg.get('sender') == 'ME' else lead_name
        created_at = msg.get('createdAt', '')
        body = msg.get('body', '[no text]')
        try:
            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = date_obj.strftime('%Y-%m-%d %H:%M')
        except Exception:
            date_str = created_at
        conversation_history.append(f"[{date_str}] {sender}: {body}")

    history_text = "\n".join(conversation_history) if conversation_history else "No message history"
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    prompt = f"""You are an expert B2B sales researcher for Interexy, a premium software development company.

ABOUT INTEREXY:
- Company: American software development firm (Miami HQ)
- Services: Senior-level developers (top 2% of market), team augmentation, custom development
- Expertise: Healthcare, Fintech, Blockchain/Web3, AI/ML, Energy
- Team: 350+ senior engineers across US, Poland, Estonia, UAE
- Notable clients: RWE, E.ON (energy sector), healthcare & fintech companies
- Guarantee: 10-day engineer replacement, high-quality code standards

YOUR TASK:
Analyze this B2B lead using the RESEARCH FRAMEWORK below. Use web search extensively to gather current information. Return findings in structured JSON format.

=== LEAD INFORMATION ===
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}
Location: {lead_location}
LinkedIn: {lead_linkedin}
Headline: {lead_headline}

=== CONVERSATION HISTORY ===
{history_text}

=== RESEARCH FRAMEWORK ===

LEVEL 1: PERSONAL PROFILE ANALYSIS
1.1 CURRENT ROLE: exact title, time in role, department, reports to, team size
1.2 CAREER TRAJECTORY: previous companies, industry switches, role progression
1.3 ACTIVITY SIGNALS: recent posts, hiring badge, speaking events, certifications

LEVEL 2: COMPANY BASICS
2.1 COMPANY INFO: founded year, size, locations, industry, stage (startup/growth/enterprise)
2.2 RECENT ACTIVITY: hiring patterns, team growth, expansion, awards

LEVEL 3: DEEP RESEARCH (Web Search Required)
3.1 FUNDING & GROWTH: last funding round, total raised, investors
3.2 PRODUCT & TECH STACK: main product, recent launches, tech stack, platform type
3.3 NEWS & DEVELOPMENTS: partnerships, acquisitions, milestones, executive changes
3.4 COMPETITIVE LANDSCAPE: competitors, market position, differentiation
3.5 REGULATORY CONTEXT: relevant regulations, compliance requirements, industry trends

LEVEL 4: PAIN POINT MAPPING
4.1 ROLE-SPECIFIC pain points based on position
4.2 STAGE-SPECIFIC pain points based on company stage

=== OUTPUT FORMAT ===
Return ONLY valid JSON:
{{
  "lead_profile": {{
    "current_role": {{"title": "", "time_in_role": "", "department": "", "reports_to": "", "team_size": "", "insight": ""}},
    "career_trajectory": {{"previous_companies": [], "industry_switches": "", "progression": "", "insight": ""}},
    "activity_signals": {{"hiring": false, "recent_posts_topics": [], "speaking_events": [], "certifications": [], "insight": ""}}
  }},
  "company_basics": {{"founded": "", "size": "", "locations": [], "industry": "", "stage": "", "stage_insight": ""}},
  "company_activity": {{"recent_hiring": {{"open_roles_count": 0, "key_roles": [], "insight": ""}}, "team_growth": "", "expansion": [], "awards": []}},
  "deep_research": {{
    "funding": {{"last_round": "", "total_raised": "", "investors": [], "funding_insight": ""}},
    "product": {{"main_product": "", "recent_launches": [], "tech_stack": [], "platform_type": "", "product_insight": ""}},
    "news": [{{"date": "", "headline": "", "summary": "", "source": "", "outreach_hook": ""}}],
    "competitive_landscape": {{"competitors": [], "market_position": "", "differentiation": "", "market_trend": ""}},
    "regulatory_context": {{"recent_regulations": [], "compliance_requirements": [], "industry_trend": ""}}
  }},
  "pain_point_analysis": {{"role_specific_pain_points": [], "stage_specific_pain_points": [], "evidence_from_research": []}},
  "conversation_analysis": {{"conversation_stage": "", "messages_exchanged": 0, "lead_responsiveness": "", "interest_signals": [], "objections_raised": [], "questions_asked": []}},
  "qualification": {{"status": "", "fit_score": 5, "reasoning": "", "budget_indicator": "", "authority_level": "", "need_urgency": ""}},
  "recommended_action": {{"next_step": "", "message_angle": "", "personalization_hooks": [], "questions_to_ask": [], "timing": "", "priority": ""}},
  "interexy_value_props": {{"most_relevant": [], "case_studies_to_mention": [], "technical_expertise_highlight": ""}},
  "executive_summary": ""
}}

IMPORTANT:
1. Use web search extensively for company news, funding, product launches
2. Find REAL information - don't invent
3. If not found, say "not found"
4. Focus on RECENT information (last 12 months)
5. Return ONLY valid JSON
6. Today's date: {today_date}"""

    return prompt


def create_messages_prompt(analysis: dict, lead_name: str, lead_company: str, lead_position: str) -> str:
    """Create message generation prompt"""
    qual = analysis.get('qualification', {})
    company = analysis.get('company_basics', {})
    pain_points = analysis.get('pain_point_analysis', {})
    deep_research = analysis.get('deep_research', {})
    recommended = analysis.get('recommended_action', {})
    value_props = analysis.get('interexy_value_props', {})

    role_pains = '\n'.join(f"- {p}" for p in pain_points.get('role_specific_pain_points', []))
    stage_pains = '\n'.join(f"- {p}" for p in pain_points.get('stage_specific_pain_points', []))
    hooks = '\n'.join(f"- {h}" for h in recommended.get('personalization_hooks', []))
    vps = '\n'.join(f"- {v}" for v in value_props.get('most_relevant', []))

    prompt = f"""You are an expert B2B sales copywriter for Interexy (software development company).

CONTEXT: We analyzed this lead and need follow-up messages after they responded "Thank you" to a congratulations message.

LEAD: {lead_name}, {lead_position} at {lead_company}
Qualification: {qual.get('status', 'N/A')}, Fit Score: {qual.get('fit_score', 0)}/10
Company Stage: {company.get('stage', 'N/A')}, Size: {company.get('size', 'N/A')}

PAIN POINTS:
Role-Specific:
{role_pains}
Stage-Specific:
{stage_pains}

NEWS: {json.dumps(deep_research.get('news', [])[:2], indent=2)}
FUNDING: {json.dumps(deep_research.get('funding', {}), indent=2)}
RECOMMENDED APPROACH: {recommended.get('next_step', 'N/A')} / Angle: {recommended.get('message_angle', 'N/A')}
HOOKS:
{hooks}
VALUE PROPS:
{vps}

TASK: Generate 10-15 follow-up message variants transitioning from "Thank you" to business conversation.

CATEGORIES:
1. Synergy-based (2-3): overlap between what they do and what we offer
2. Question-based (3-4): strategic questions about challenges
3. Insight-based (2-3): show understanding of their situation
4. Soft touch (2-3): "not selling, just curious" approach
5. Direct value prop (2-3): clear about what we do

REQUIREMENTS:
- 2-3 sentences max per message
- Start with "My pleasure, {lead_name.split()[0]}!" or "Glad to hear, {lead_name.split()[0]}!"
- Use REAL data from analysis
- NO generic statements

Return ONLY valid JSON:
{{
  "messages": [
    {{"id": 1, "type": "synergy", "message": "...", "rationale": "...", "best_for": "...", "follow_up_ready": true}}
  ],
  "recommended_top_3": [1, 5, 8],
  "notes": "overall strategy notes"
}}"""

    return prompt


# ==================== BACKGROUND PIPELINE ====================

async def run_analysis_pipeline(job_id: str, account_id: int):
    """Main analysis pipeline running in background"""
    job = jobs[job_id]
    try:
        # Step 1: Fetch conversations
        job['step'] = 'fetching'
        job['status_text'] = 'Fetching unread conversations from HeyReach...'
        logger.info(f"[{job_id}] Fetching conversations for account {account_id}")

        conversations = await fetch_unread_conversations(account_id)
        job['total_conversations'] = len(conversations)
        job['status_text'] = f'Found {len(conversations)} unread conversations. Filtering for Catch Up leads...'

        if not conversations:
            job['step'] = 'done'
            job['status_text'] = 'No unread conversations found'
            job['completed'] = True
            return

        # Step 2: Filter catch-up leads
        job['step'] = 'filtering'
        logger.info(f"[{job_id}] Filtering {len(conversations)} conversations")

        catchup_indices = await filter_catchup_leads(conversations)
        catchup_conversations = [conversations[i] for i in catchup_indices if i < len(conversations)]

        job['total_leads'] = len(catchup_conversations)
        job['leads_info'] = []

        if not catchup_conversations:
            job['step'] = 'done'
            job['status_text'] = 'No new Catch Up replies found'
            job['completed'] = True
            return

        # Populate lead info
        for conv in catchup_conversations:
            profile = conv.get('correspondentProfile', {})
            job['leads_info'].append({
                'name': f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
                'company': profile.get('companyName', ''),
                'position': profile.get('position', ''),
                'location': profile.get('location', ''),
                'profileUrl': profile.get('profileUrl', ''),
                'headline': profile.get('headline', ''),
                'status': 'pending',
                'step': 'waiting',
                'conversation': conv
            })

        job['status_text'] = f'Found {len(catchup_conversations)} Catch Up leads. Starting analysis...'
        job['step'] = 'analyzing'

        # Step 3: Process each lead sequentially
        for idx, conv in enumerate(catchup_conversations):
            lead_info = job['leads_info'][idx]
            lead_name = lead_info['name']
            lead_company = lead_info['company']

            try:
                # Analysis step
                lead_info['status'] = 'processing'
                lead_info['step'] = 'analyzing'
                job['processed'] = idx
                job['status_text'] = f'Analyzing {lead_name} ({idx + 1}/{len(catchup_conversations)})...'
                logger.info(f"[{job_id}] Analyzing lead {idx + 1}: {lead_name}")

                analysis_prompt = create_analysis_prompt(conv)
                analysis = await call_openai(analysis_prompt, use_web_search=True, timeout_sec=180)
                lead_info['analysis'] = analysis

                # Message generation step
                lead_info['step'] = 'generating_messages'
                job['status_text'] = f'Generating messages for {lead_name} ({idx + 1}/{len(catchup_conversations)})...'
                logger.info(f"[{job_id}] Generating messages for {lead_name}")

                msg_prompt = create_messages_prompt(
                    analysis, lead_name, lead_company, lead_info.get('position', '')
                )
                messages_data = await call_openai(msg_prompt, use_web_search=False, timeout_sec=120)
                lead_info['messages_data'] = messages_data

                lead_info['status'] = 'done'
                lead_info['step'] = 'done'
                logger.info(f"[{job_id}] Lead {lead_name} done")

            except Exception as e:
                logger.error(f"[{job_id}] Lead {lead_name} failed: {e}")
                lead_info['status'] = 'failed'
                lead_info['step'] = 'failed'
                lead_info['error'] = str(e)

            # Rate limiting pause between leads
            if idx < len(catchup_conversations) - 1:
                job['status_text'] = f'Completed {lead_name}. Pausing before next lead...'
                await asyncio.sleep(5)

        job['processed'] = len(catchup_conversations)
        job['step'] = 'done'
        job['completed'] = True
        done_count = sum(1 for l in job['leads_info'] if l['status'] == 'done')
        failed_count = sum(1 for l in job['leads_info'] if l['status'] == 'failed')
        job['status_text'] = f'Analysis complete! {done_count} successful, {failed_count} failed out of {len(catchup_conversations)} leads.'

    except Exception as e:
        logger.error(f"[{job_id}] Pipeline error: {e}")
        job['step'] = 'error'
        job['error'] = str(e)
        job['status_text'] = f'Error: {str(e)}'
        job['completed'] = True


# ==================== RETRY PIPELINE ====================

async def retry_leads_pipeline(job_id: str, lead_names: List[str]):
    """Re-run analysis for specific failed leads"""
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

                lead_info['step'] = 'generating_messages'
                job['status_text'] = f'Generating messages for {lead_name} ({idx + 1}/{len(leads_to_retry)})...'

                msg_prompt = create_messages_prompt(
                    analysis, lead_name, lead_company, lead_info.get('position', '')
                )
                messages_data = await call_openai(msg_prompt, use_web_search=False, timeout_sec=120)
                lead_info['messages_data'] = messages_data
                lead_info['error'] = None

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
