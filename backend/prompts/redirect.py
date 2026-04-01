import json
from datetime import datetime


def create_redirect_messages_prompt(analysis: dict, lead_name: str, lead_company: str, lead_position: str) -> str:
    """Create message generation prompt for leads who redirected to another person/department"""
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
    redirect_info = conv_analysis.get('redirect_info', {})
    redirected_to = redirect_info.get('redirected_to', 'another team member')
    redirect_reason = redirect_info.get('reason', 'not the right person')
    news = deep_research.get('news', [])[:2]
    funding = deep_research.get('funding', {})
    vp_relevant = value_props.get('most_relevant', [])[:3]

    prompt = f"""You are an expert B2B sales copywriter for Interexy (software development company).

CONTEXT:
This lead REDIRECTED us to another person, department, or team member.
They indicated they are not the right person to talk to about this topic.
We need to handle this gracefully and either:
1. Follow up with the new contact they provided
2. Ask for clarification on who the right person is
3. Thank them and pivot to see if there's still value in staying connected

LEAD INFORMATION:
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}
First name: {first_name}

ANALYSIS SUMMARY:
Qualification: {qual.get('status', 'N/A')}, Fit Score: {qual.get('fit_score', 0)}/10
Company Stage: {company.get('stage', 'N/A')}, Size: {company.get('size', 'N/A')}, Industry: {company.get('industry', 'N/A')}

REDIRECT DETAILS:
Redirected To: {redirected_to}
Reason: {redirect_reason}

RECENT CONTEXT:
News: {json.dumps(news, indent=2)}
Funding: {json.dumps(funding, indent=2)}

INTEREXY VALUE PROPS:
{chr(10).join(f"- {v}" for v in vp_relevant)}

---

TASK:
Generate 12-15 follow-up message variants for redirect scenarios.
Messages should be GRACIOUS, PROFESSIONAL, and help us either connect with the right person or salvage the relationship.

MESSAGE TYPES TO GENERATE:

1. THANK + CONFIRM NEXT STEP (3-4 variants)
Strategy: Thank them for the redirect, confirm you'll reach out to the new person.
Example: "Thanks for pointing me in the right direction, {first_name}! I'll reach out to {redirected_to} directly. Appreciate your help!"
Show gratitude, confirm action.

2. THANK + ASK FOR WARM INTRO (2-3 variants)
Strategy: Thank them and ask if they'd be willing to make a warm introduction.
Example: "Thanks, {first_name}! Would you be open to making a quick intro to {redirected_to}? Or should I just reach out directly? Either works!"
Make it easy for them to help.

3. CLARIFICATION / WHO ELSE (3-4 variants)
Strategy: If redirect was vague, politely ask for more specifics on who to talk to.
Example: "Got it, {first_name}! Out of curiosity, who at {lead_company} typically owns [specific area]? Want to make sure I'm talking to the right person."
Be specific about what you're looking for.

4. PIVOT + STAY CONNECTED (2-3 variants)
Strategy: Even if not the right person, see if they want to stay connected for future.
Example: "Understood, {first_name}! Even if this isn't your area, happy to stay connected here. Always great to have {lead_company} in my network!"
Long-term relationship building.

5. CONTEXT + REDIRECT ACKNOWLEDGMENT (2 variants)
Strategy: Briefly explain why you reached out to THEM specifically, then acknowledge redirect.
Example: "Thanks for clarifying, {first_name}! I reached out because [specific reason based on research]. I'll connect with {redirected_to} - appreciate the direction!"
Show you did your homework.

REQUIREMENTS:
- Messages must be COMPLETE and ready-to-send (2-4 sentences max)
- Start with acknowledgment: "Thanks!" / "Got it!" / "Appreciate it!" / "Understood!"
- Always use first name: {first_name}
- If redirected_to name is available, USE IT in the message
- Based on REAL data from research - not generic
- GRACIOUS and PROFESSIONAL - no frustration or pushback
- Each message should either confirm next step or ask for clarification
- Keep the door open for future connection even if not the right person

Return ONLY valid JSON:
{{
  "messages": [
    {{
      "id": 1,
      "type": "thank_confirm",
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
- Use REAL data (company name, role, redirected_to name if available)
- Type values: thank_confirm | thank_intro | clarification | pivot_connect | context_redirect
- Return ONLY JSON, no markdown blocks
- Be genuinely grateful - redirects are actually positive signals (they engaged!)"""

    return prompt
