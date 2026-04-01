import json
from datetime import datetime


def create_interested_messages_prompt(analysis: dict, lead_name: str, lead_company: str, lead_position: str) -> str:
    """Create message generation prompt for leads who expressed genuine interest"""
    qual = analysis.get('qualification', {})
    company = analysis.get('company_basics', {})
    pain_points = analysis.get('pain_point_analysis', {})
    deep_research = analysis.get('deep_research', {})
    recommended = analysis.get('recommended_action', {})
    value_props = analysis.get('interexy_value_props', {})
    conv_analysis = analysis.get('conversation_analysis', {})

    first_name = lead_name.split()[0] if lead_name else 'there'

    role_pains = pain_points.get('role_specific_pain_points', [])[:3]
    stage_pains = pain_points.get('stage_specific_pain_points', [])[:3]
    evidence = pain_points.get('evidence_from_research', [])[:3]
    news = deep_research.get('news', [])[:2]
    funding = deep_research.get('funding', {})
    product_info = deep_research.get('product', {})
    vp_relevant = value_props.get('most_relevant', [])[:3]
    differentiation = value_props.get('differentiation_angle', '')
    interest_signals = conv_analysis.get('interest_signals', [])

    prompt = f"""You are an expert B2B sales copywriter for Interexy (software development company).

CONTEXT:
This lead expressed GENUINE INTEREST in our services. They want to learn more, asked about services, or said something like "tell me more" / "sounds interesting".
We need to capitalize on their interest and move toward a discovery call or concrete next step.

LEAD INFORMATION:
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}
First name: {first_name}

ANALYSIS SUMMARY:
Qualification: {qual.get('status', 'N/A')}, Fit Score: {qual.get('fit_score', 0)}/10
Company Stage: {company.get('stage', 'N/A')}, Size: {company.get('size', 'N/A')}, Industry: {company.get('industry', 'N/A')}

PAIN POINTS:
Role-Specific (top 3):
{chr(10).join(f"- {p}" for p in role_pains)}

Stage-Specific (top 3):
{chr(10).join(f"- {p}" for p in stage_pains)}

Evidence from Research:
{chr(10).join(f"- {e}" for e in evidence)}

INTEREST SIGNALS (from conversation):
{chr(10).join(f"- {s}" for s in interest_signals) if interest_signals else "General interest expressed"}

RECENT CONTEXT:
News: {json.dumps(news, indent=2)}
Funding: {json.dumps(funding, indent=2)}
Product Info: {json.dumps(product_info.get('main_product', 'N/A'), indent=2)}

INTEREXY VALUE PROPS:
{chr(10).join(f"- {v}" for v in vp_relevant)}
Differentiation: {differentiation}

---

TASK:
Generate 12-15 follow-up message variants for a lead who expressed genuine interest.
Messages should be ENTHUSIASTIC but PROFESSIONAL, moving toward a discovery call or concrete next step.

MESSAGE TYPES TO GENERATE:

1. DIRECT CALL-TO-ACTION (3-4 variants)
Strategy: Propose a specific next step (call, demo, meeting) with clear value.
Example: "Great to hear, {first_name}! Would you be open to a 20-min call this week to explore how we could help {lead_company} with [specific pain point]?"
Use their interest as momentum.

2. VALUE-FIRST APPROACH (2-3 variants)
Strategy: Offer something valuable before asking for time (case study, audit, insights).
Example: "Awesome, {first_name}! Before we hop on a call, I'd love to share how we helped [similar company] solve [similar challenge] - think it's relevant for {lead_company}."

3. SPECIFIC SOLUTION PITCH (3-4 variants)
Strategy: Connect their expressed interest to a specific Interexy capability.
Example: "Glad you're interested, {first_name}! Based on what you're building at {lead_company}, our [specific expertise] team could help you [specific outcome]. Worth exploring?"
Reference their product/tech stack from research.

4. SOCIAL PROOF + CTA (2-3 variants)
Strategy: Use relevant case studies (RWE, E.ON, etc.) to build credibility, then propose call.
Example: "Thanks for the interest, {first_name}! We recently helped [similar company in their industry] achieve [result]. Could we explore similar opportunities at {lead_company}?"

5. LOW-PRESSURE EXPLORATORY (2 variants)
Strategy: Keep it light, exploratory, no pressure - just a conversation.
Example: "Appreciate the interest, {first_name}! No pressure at all - but if you're curious, I'd be happy to walk you through how we typically engage with companies like {lead_company}. 15 mins, zero commitment."

REQUIREMENTS:
- Messages must be COMPLETE and ready-to-send (2-4 sentences max)
- Start with acknowledgment: "Great to hear!" / "Awesome!" / "Glad you're interested!" / "Thanks for the interest!"
- Always use first name: {first_name}
- Based on REAL data from research - not generic
- ENTHUSIASTIC but NOT pushy or desperate
- Each message should have a CLEAR next step or question
- Match sophistication to lead seniority (CEO = high-level, CTO = technical)

Return ONLY valid JSON:
{{
  "messages": [
    {{
      "id": 1,
      "type": "direct_cta",
      "message": "full ready-to-send message text",
      "rationale": "why this message works based on research",
      "best_for": "situation where this works best",
      "follow_up_ready": true
    }}
  ],
  "recommended_top_3": [1, 5, 8],
  "overall_strategy": {{
    "primary_approach": "...",
    "timing_recommendation": "..."
  }},
  "notes": "overall strategy notes for this lead"
}}

IMPORTANT:
- Use REAL data (company name, role, news, product, funding)
- Type values: direct_cta | value_first | solution_pitch | social_proof | exploratory
- Return ONLY JSON, no markdown blocks"""

    return prompt
