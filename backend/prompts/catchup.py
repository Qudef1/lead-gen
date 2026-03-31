import json


def create_catchup_messages_prompt(analysis: dict, lead_name: str, lead_company: str, lead_position: str, intent: str = "catchup_thanks") -> str:
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

    first_name = lead_name.split()[0] if lead_name else 'there'

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
- Start with "My pleasure, {first_name}!" or "Glad to hear, {first_name}!"
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
