import json
from datetime import datetime


def create_hard_rejection_messages_prompt(analysis: dict, lead_name: str, lead_company: str, lead_position: str) -> str:
    """
    Create message generation prompt for hard rejection leads.
    
    NOTE: Hard rejections typically should NOT receive follow-up messages.
    This prompt is for edge cases where a polite closure or future re-engagement might be appropriate.
    Use with extreme caution.
    """
    qual = analysis.get('qualification', {})
    company = analysis.get('company_basics', {})
    conv_analysis = analysis.get('conversation_analysis', {})
    rejection = conv_analysis.get('rejection_analysis', {})

    first_name = lead_name.split()[0] if lead_name else 'there'

    prompt = f"""You are an expert B2B sales copywriter for Interexy (software development company).

CONTEXT:
This lead gave a HARD REJECTION - they explicitly asked not to be contacted, said "not interested", 
or requested removal from messaging list.

⚠️  IMPORTANT: Hard rejections should typically NOT receive follow-up messages.
However, in some cases, a SINGLE polite closure message may be appropriate to:
- Acknowledge their request respectfully
- Leave the door open for future (distant future) re-engagement
- Maintain professional relationship

LEAD INFORMATION:
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}
First name: {first_name}

ANALYSIS SUMMARY:
Qualification: {qual.get('status', 'N/A')}, Fit Score: {qual.get('fit_score', 0)}/10
Company Stage: {company.get('stage', 'N/A')}, Size: {company.get('size', 'N/A')}

REJECTION DETAILS:
Type: {rejection.get('rejection_type', 'hard_no')}
Evidence: {rejection.get('evidence', 'Explicit rejection')}
Recommended Approach: {rejection.get('recommended_approach', 'respect_and_withdraw')}

---

TASK:
Generate 5-7 VERY CAREFUL follow-up message variants for hard rejection scenarios.
These messages should be BRIEF, RESPECTFUL, and make NO attempt to sell or persuade.

MESSAGE TYPES TO GENERATE:

1. POLITE ACKNOWLEDGMENT + WITHDRAWAL (3-4 variants)
Strategy: Acknowledge their decision, confirm you'll respect it, wish them well.
Example: "Understood, {first_name}. Thanks for letting me know - I'll respect that and won't reach out again. Wishing you and {lead_company} all the best!"
NO sales pitch, NO attempt to re-engage.

2. DOOR-OPEN (1-2 variants) - USE SPARINGLY
Strategy: Briefly mention you're available if they ever change their mind (6+ months).
Example: "Got it, {first_name}. I'll note this and won't bother you again. If anything ever changes down the road, feel free to reach out. Best of luck with everything at {lead_company}!"

3. PROFESSIONAL CLOSURE (1-2 variants)
Strategy: Professional sign-off, no strings attached.
Example: "Thanks for the transparency, {first_name}. I appreciate you taking the time to respond. Best wishes to you and the team at {lead_company}!"

REQUIREMENTS:
- Messages must be COMPLETE and ready-to-send (1-3 sentences max)
- Start with acknowledgment: "Understood" / "Got it" / "Thanks for letting me know"
- Always use first name: {first_name}
- NO sales language whatsoever
- NO attempts to persuade or re-engage immediately
- NO guilt trips or passive-aggressive language
- Be genuinely respectful and professional
- These are CLOSURE messages, not re-engagement attempts

⚠️  CRITICAL:
- Do NOT generate messages that could be perceived as ignoring their request
- Do NOT suggest future contact unless very distant (6+ months)
- Do NOT ask questions that require responses
- Keep it brief and dignified

Return ONLY valid JSON:
{{
  "messages": [
    {{
      "id": 1,
      "type": "polite_withdrawal",
      "message": "full ready-to-send message text",
      "rationale": "why this approach is appropriate",
      "best_for": "situation where this works best",
      "follow_up_ready": false
    }}
  ],
  "recommended_top_3": [1],
  "overall_strategy": {{
    "primary_approach": "respect_and_withdraw",
    "timing_recommendation": "do_not_follow_up_unless_lead_initiates",
    "warning": "Hard rejections should typically not receive any follow-up"
  }},
  "notes": "These messages are for professional closure only. Do not use for re-engagement."
}}

IMPORTANT:
- Use REAL data (company name, lead name) but keep it minimal
- Type values: polite_withdrawal | door_open | professional_closure
- Return ONLY JSON, no markdown blocks
- ERR ON THE SIDE OF CAUTION - fewer messages is better"""

    return prompt
