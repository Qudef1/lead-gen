import json
from datetime import datetime


def create_question_messages_prompt(analysis: dict, lead_name: str, lead_company: str, lead_position: str) -> str:
    """Create message generation prompt for leads who asked specific questions"""
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
    questions_asked = conv_analysis.get('questions_asked', [])
    news = deep_research.get('news', [])[:2]
    funding = deep_research.get('funding', {})
    product_info = deep_research.get('product', {})
    tech_stack = deep_research.get('product', {}).get('tech_stack', [])
    vp_relevant = value_props.get('most_relevant', [])[:3]
    case_studies = value_props.get('case_studies_to_mention', [])

    prompt = f"""You are an expert B2B sales copywriter for Interexy (software development company).

CONTEXT:
This lead asked a SPECIFIC QUESTION about Interexy, our services, tech stack, pricing, team, or process.
They are in RESEARCH/evaluation mode and need informative answers before making a decision.
We need to answer their question thoughtfully while opening a dialogue for further conversation.

LEAD INFORMATION:
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}
First name: {first_name}

ANALYSIS SUMMARY:
Qualification: {qual.get('status', 'N/A')}, Fit Score: {qual.get('fit_score', 0)}/10
Company Stage: {company.get('stage', 'N/A')}, Size: {company.get('size', 'N/A')}, Industry: {company.get('industry', 'N/A')}

QUESTIONS ASKED (from conversation):
{chr(10).join(f"- {q}" for q in questions_asked) if questions_asked else "General question about services"}

PAIN POINTS:
Role-Specific (top 3):
{chr(10).join(f"- {p}" for p in role_pains)}

Stage-Specific (top 3):
{chr(10).join(f"- {p}" for p in stage_pains)}

RECENT CONTEXT:
News: {json.dumps(news, indent=2)}
Funding: {json.dumps(funding, indent=2)}
Product Info: {json.dumps(product_info.get('main_product', 'N/A'), indent=2)}
Tech Stack: {json.dumps(tech_stack, indent=2)}

INTEREXY VALUE PROPS:
{chr(10).join(f"- {v}" for v in vp_relevant)}
Case Studies: {json.dumps(case_studies, indent=2)}

---

TASK:
Generate 12-15 follow-up message variants for a lead who asked questions.
Messages should be INFORMATIVE, HELPFUL, and position Interexy as a knowledgeable partner.

MESSAGE TYPES TO GENERATE:

1. DIRECT ANSWER + CONTEXT (3-4 variants)
Strategy: Answer their question directly, then add relevant context or example.
Example: "Great question, {first_name}! [Direct answer to their question]. For context, we typically [relevant context]. Does that align with what you're looking for at {lead_company}?"
Be specific and substantive.

2. ANSWER + RELATED QUESTION (3-4 variants)
Strategy: Answer their question, then ask a related question to understand their needs better.
Example: "Thanks for asking, {first_name}! [Answer]. I'm curious - what's your current approach to [related topic] at {lead_company}?"
Show genuine interest in their situation.

3. ANSWER + CASE STUDY (2-3 variants)
Strategy: Answer their question and reference a relevant case study or example.
Example: "Good question, {first_name}! [Answer]. We actually helped [similar company] with this - they were able to [result]. Think there could be similar opportunities at {lead_company}."

4. EDUCATIONAL / INSIGHT-BASED (2-3 variants)
Strategy: Provide educational content or industry insight related to their question.
Example: "Happy to clarify, {first_name}! [Answer + insight]. One thing we've noticed working with [industry] companies is [insight]. Have you seen this at {lead_company}?"

5. ANSWER + SOFT CTA (2 variants)
Strategy: Answer thoroughly, then propose a deeper conversation if they want more detail.
Example: "Hope this helps, {first_name}! [Answer]. If you'd like to dive deeper into how this could work for {lead_company}, happy to hop on a quick call. No pressure at all!"

REQUIREMENTS:
- Messages must be COMPLETE and ready-to-send (2-4 sentences max)
- Start with acknowledgment: "Great question!" / "Thanks for asking!" / "Happy to clarify!" / "Good question!"
- Always use first name: {first_name}
- ANSWER THE QUESTION substantively - don't dodge or deflect
- Based on REAL data from research - not generic
- INFORMATIVE but NOT overwhelming (don't write a novel)
- Each message should invite further dialogue
- Match technical depth to lead's role (CTO = technical, CEO = business impact)

Return ONLY valid JSON:
{{
  "messages": [
    {{
      "id": 1,
      "type": "direct_answer",
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
- Use REAL data (company name, role, tech stack, product, funding)
- Type values: direct_answer | answer_question | answer_case_study | educational | answer_cta
- Return ONLY JSON, no markdown blocks
- ACTUALLY ANSWER THE QUESTION - don't just pitch"""

    return prompt
