import json
from datetime import datetime, timezone


def create_analysis_prompt(conversation: dict) -> str:
    """Create the universal framework analysis prompt for any lead intent"""
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

LEVEL 1: PERSONAL PROFILE ANALYSIS (LinkedIn)

1.1 CURRENT ROLE ANALYSIS
Use web search to find:
✓ Position: exact title
✓ Time in role: months/years
✓ Department: sales/product/tech/ops/etc
✓ Reports to: who (CEO/CTO/etc)
✓ Team size: if mentioned (10 direct reports = manager level)

WHAT THIS GIVES YOU:
- New role (<6 months) → "congrats on new role" opener, usually open to new tools
- Long in role (2+ years) → expert, ask for insights
- Head of/Director → strategic questions
- VP/C-level → high-level business impact questions

1.2 CAREER TRAJECTORY
Use web search to find:
✓ Previous companies: where they worked
✓ Industry switches: fintech → healthcare = interesting
✓ Role progression: engineer → manager → director
✓ Time at each role: job hopper vs. stable

WHAT THIS GIVES YOU:
- Industry switchers = ask "what's different between X and Y industry?"
- Rapid progression = ambitious, growth-focused
- Similar backgrounds = "I see you also worked at..."

1.3 ACTIVITY & SIGNALS
Use web search to find:
✓ Recent posts: what they post about
✓ #HIRING badge: hiring = potential need
✓ #OPEN_TO_WORK: job seeking = different approach
✓ Event speaking: conferences = thought leader
✓ Recent certifications: learning mode

WHAT THIS GIVES YOU:
- Hiring = "saw you're hiring for X, curious about..."
- Recent posts = conversation starter
- Speaking = "saw your talk at X conference"

LEVEL 2: COMPANY BASICS (LinkedIn Company Page + Web)

2.1 COMPANY BASICS
Use web search to find:
✓ Founded: year
✓ Size: employee count
✓ Locations: HQ + offices
✓ Industry: actual industry
✓ Stage: startup/growth/enterprise

WHAT THIS GIVES YOU:
- Startup (<50 people, <3 years) → growth pain points, scaling questions
- Scaleup (50-500, 3-7 years) → platform optimization, team expansion
- Enterprise (500+, 7+ years) → modernization, legacy system questions

2.2 RECENT COMPANY ACTIVITY
Use web search to find:
✓ Recent posts: hiring/product launches/awards
✓ Job openings: which roles they're hiring
✓ Team growth: compare employee count vs 3 months ago
✓ New locations: expansion signals

WHAT THIS GIVES YOU:
- 5+ open engineering roles = scaling tech team
- New office = expansion mode
- Awards/recognition = "congrats on X award" opener

LEVEL 3: DEEP RESEARCH (Web Search Required)

3.1 FUNDING & GROWTH
Search query: "{lead_company} funding round 2025 2026"
Find:
✓ Last funding: Series A/B/C, amount, date
✓ Total raised: $X million
✓ Investors: who backed them
✓ Valuation: if public
✓ Revenue: if mentioned in articles

WHAT THIS GIVES YOU:
- Recent funding (<6 months) → "congrats on Series B! As you scale with new capital, what's the biggest tech challenge?"
- No recent funding + growing → bootstrapped, cost-conscious
- Big name investors → "saw a16z backed you, interesting"

3.2 PRODUCT & TECH STACK
Search queries:
- "{lead_company} product launch 2025 2026"
- "{lead_company} tech stack"
- "{lead_company} platform technology"

Find:
✓ Main product: what they sell
✓ Recent launches: new features/products
✓ Tech mentioned: React/Python/blockchain/AI
✓ Integrations: Stripe/Salesforce/etc
✓ Platform type: SaaS/marketplace/infrastructure

WHAT THIS GIVES YOU:
- Recent launch = "saw you launched X, curious about adoption"
- Tech stack visible = technical questions
- Platform type = specific pain points (marketplace scaling, SaaS onboarding, etc)

3.3 NEWS & RECENT DEVELOPMENTS
Search query: "{lead_company} news 2025 2026"
Find:
✓ Partnerships announced: with who, when
✓ Acquisitions: bought/sold
✓ Product milestones: user count, revenue
✓ Industry awards: recognition
✓ Executive changes: new CEO/CTO
✓ Controversies: if any - be careful

WHAT THIS GIVES YOU:
- Partnership announcement = "saw the Stripe partnership, curious how..."
- Acquisition = "congrats on acquiring X, integration challenges?"
- Milestones = "1M users is impressive, what's next?"

3.4 COMPETITIVE LANDSCAPE
Search query: "{lead_company} competitors alternatives"
Find:
✓ Direct competitors: who they compete with
✓ Market position: leader/challenger/niche
✓ Differentiation: what makes them unique
✓ Market trends: industry growing/declining

WHAT THIS GIVES YOU:
- "How do you differentiate from [competitor]?"
- "Market seems crowded - what's your moat?"
- Shows you understand their space

3.5 REGULATORY & INDUSTRY CONTEXT
Search queries based on industry:
- Fintech: "CSRD MiCA regulations EU 2026"
- Healthcare: "HIPAA compliance digital health 2025 2026"
- Crypto: "MiCA stablecoin regulations 2025 2026"
- Energy: "{lead_company} industry renewable energy transition 2025 2026"

Find:
✓ Recent regulations: what changed
✓ Compliance requirements: new mandates
✓ Industry trends: what's hot
✓ Market drivers: what's pushing change

LEVEL 4: PAIN POINT MAPPING

4.1 ROLE-SPECIFIC PAIN POINTS

Analyze based on position title:

HEAD OF DIGITAL/INNOVATION likely faces:
- Platform scaling challenges
- Legacy system integration
- Team capacity (build vs buy decisions)
- Innovation speed pressures
- Tech debt management

PRODUCT MANAGER likely faces:
- Feature velocity demands
- User feedback integration
- A/B testing infrastructure
- Technical feasibility assessments
- Cross-functional alignment issues

CEO/FOUNDER likely faces:
- Capital efficiency concerns
- Time to market pressures
- Team scaling challenges
- Product-market fit validation
- Go-to-market strategy

CTO/ENGINEERING LEAD likely faces:
- Technical debt accumulation
- Team productivity optimization
- Architecture decisions
- Hiring senior talent
- System reliability/uptime

4.2 STAGE-SPECIFIC PAIN POINTS

EARLY STAGE STARTUP (<2 years, Seed):
- MVP development speed
- Finding product-market fit
- Limited engineering resources
- Capital efficiency
- Rapid iteration needs

GROWTH STAGE (Series A/B, 2-5 years):
- Scaling infrastructure
- Team expansion (10x growth)
- Platform stability
- Feature velocity vs tech debt
- Customer success scaling

SCALE-UP (Series C+, 5+ years):
- Legacy modernization
- Enterprise features
- Compliance/security requirements
- Geographic expansion
- M&A integration

4.3 VENDOR APPROACH INFERENCE

Analyze signals about whether they use in-house vs vendors vs hybrid:
✓ Job postings: heavy engineering hiring = building in-house
✓ LinkedIn team: large internal eng team = less likely to vendor
✓ Tech stack visibility: public stack = open to external
✓ Past vendor mentions: Clutch/G2 reviews, case studies featuring them
✓ Company stage: early = lean, uses vendors; enterprise = both

Questions to answer:
- Are they currently building in-house or using vendors?
- Do they have a preference for vendor geography (nearshore/offshore/onshore)?
- What's their build-vs-buy philosophy?

4.4 TIMING TRIGGERS ANALYSIS

ACTIVE TRIGGERS (happening now, 0-3 months):
- Recent funding round
- New product launch
- New leadership hire
- Announced expansion
- Regulatory deadline approaching

UPCOMING TRIGGERS (3-6 months horizon):
- Series B companies hitting scale challenges
- Hiring surge indicating team growth
- Product roadmap launches
- Market expansion signals

POTENTIAL TRIGGERS (6-12 months):
- Annual budget cycles
- Contract renewals (typical 12-month vendor cycles)
- Growth milestones approaching

VENDOR EVALUATION PATTERNS:
- Triggered: evaluate after specific event (funding/launch/pain)
- Quarterly: review vendors every quarter
- Annual: yearly budget allocation

=== OUTPUT FORMAT ===
Return ONLY valid JSON:
{{
  "lead_profile": {{
    "current_role": {{"title": "", "time_in_role": "", "department": "", "reports_to": "", "team_size": "", "insight": ""}},
    "career_trajectory": {{"previous_companies": [], "industry_switches": "", "progression": "", "insight": ""}},
    "activity_signals": {{"hiring": false, "recent_posts_topics": [], "speaking_events": [], "certifications": [], "insight": ""}}
  }},
  "company_basics": {{"founded": "", "size": "", "locations": [], "industry": "", "stage": "", "stage_insight": ""}},
  "company_activity": {{
    "recent_hiring": {{"open_roles_count": 0, "key_roles": [], "insight": ""}},
    "team_growth": "",
    "expansion": [],
    "awards": []
  }},
  "deep_research": {{
    "funding": {{"last_round": "", "total_raised": "", "investors": [], "funding_insight": ""}},
    "product": {{"main_product": "", "recent_launches": [], "tech_stack": [], "platform_type": "", "product_insight": ""}},
    "news": [{{"date": "", "headline": "", "summary": "", "source": "", "outreach_hook": ""}}],
    "competitive_landscape": {{"competitors": [], "market_position": "", "differentiation": "", "market_trend": ""}},
    "regulatory_context": {{"recent_regulations": [], "compliance_requirements": [], "industry_trend": ""}}
  }},
  "pain_point_analysis": {{
    "role_specific_pain_points": [],
    "stage_specific_pain_points": [],
    "evidence_from_research": []
  }},
  "vendor_approach_inference": {{
    "current_solution_hypothesis": "likely_in_house/likely_vendors/likely_hybrid",
    "confidence": "high/medium/low",
    "evidence": [],
    "vendor_geography_preference": {{"hypothesis": "", "reasoning": ""}},
    "build_vs_buy_philosophy": {{"assessment": "", "reasoning": "", "implications": ""}}
  }},
  "timing_triggers_analysis": {{
    "active_triggers": [{{"trigger": "", "timeframe": "0-3 months", "urgency": "high/medium/low", "how_it_creates_need": ""}}],
    "upcoming_triggers": [{{"trigger": "", "timeframe": "3-6 months", "probability": "high/medium/low", "how_to_use": ""}}],
    "potential_triggers": [{{"trigger": "", "timeframe": "6-12 months", "how_to_stay_on_radar": ""}}],
    "vendor_evaluation_pattern": {{"likely_pattern": "triggered/quarterly/annual", "decision_maker": "", "typical_timeline": "", "criteria": []}},
    "urgency_assessment": {{"urgency_level": "high/medium/low/none", "primary_driver": "", "timing_recommendation": ""}}
  }},
  "conversation_analysis": {{
    "conversation_stage": "",
    "messages_exchanged": 0,
    "lead_responsiveness": "",
    "interest_signals": [],
    "objections_raised": [],
    "questions_asked": [],
    "rejection_analysis": {{
      "rejection_type": "hard_no/soft_no/wrong_person/bad_timing/not_applicable",
      "confidence": "high/medium/low",
      "evidence": "",
      "recommended_approach": ""
    }}
  }},
  "qualification": {{
    "status": "qualified/partially_qualified/not_qualified/too_early",
    "fit_score": 5,
    "reasoning": "",
    "budget_indicator": "high/medium/low/unknown",
    "authority_level": "decision_maker/influencer/user/unknown",
    "need_urgency": "high/medium/low/none_detected",
    "vendor_readiness": "ready/maybe_soon/not_ready/never"
  }},
  "recommended_action": {{
    "next_step": "",
    "message_angle": "",
    "personalization_hooks": [],
    "questions_to_ask": [],
    "timing": "",
    "priority": ""
  }},
  "interexy_value_props": {{
    "most_relevant": [],
    "differentiation_angle": "",
    "case_studies_to_mention": [],
    "technical_expertise_highlight": ""
  }},
  "executive_summary": ""
}}

IMPORTANT:
1. Use web search extensively - search for company news, funding, product launches, regulatory context
2. Find REAL information with REAL sources and dates
3. If information not found, say "not found" - don't invent
4. Focus on RECENT information (last 12 months prioritized)
5. Provide specific, actionable insights - not generic
6. Match pain points to REAL evidence from research
7. Return ONLY valid JSON, no markdown blocks, no extra text
8. Today's date for reference: {today_date}"""

    return prompt
