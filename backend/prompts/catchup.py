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

    _INTENT_CONTEXT = {
        "catchup_thanks": (
            'The lead replied "Thank you" or similar to a congratulations/catch-up message.',
            f'Generate 10-15 follow-up message variants that naturally transition from "{first_name}\'s thank-you reply" into a business conversation.',
            f'- Start with "My pleasure, {first_name}!" or "Glad to hear, {first_name}!"',
        ),
        "interested": (
            "The lead expressed genuine interest in our services or asked to learn more.",
            "Generate 10-15 follow-up message variants that build on their interest and move toward a discovery call.",
            "- Acknowledge their interest directly and propose a concrete next step (call, demo, etc.)",
        ),
        "question": (
            "The lead asked a specific question about Interexy or our services.",
            "Generate 10-15 follow-up message variants that answer their implied question and open a dialogue.",
            "- Reference their question type (tech stack, pricing, team size) and provide a hook answer",
        ),
        "redirect": (
            "The lead redirected us to another person or department.",
            "Generate 10-15 follow-up message variants suitable for following up with the new contact or re-engaging the original lead.",
            "- Acknowledge the redirect and bridge to the business value",
        ),
        "ooo": (
            "The lead sent an out-of-office auto-reply.",
            "Generate 10-15 warm follow-up message variants to send once they return.",
            "- Reference their absence briefly, do not push",
        ),
        "hiring": (
            "The lead mentioned they are hiring or have open positions.",
            "Generate 10-15 follow-up message variants that connect their hiring needs to Interexy's augmentation services.",
            "- Lead with the staffing angle: faster hiring, no overhead",
        ),
    }

    ctx_description, ctx_task, ctx_requirement = _INTENT_CONTEXT.get(
        intent,
        (
            f'The lead sent a reply classified as "{intent}".',
            "Generate 10-15 follow-up message variants appropriate for this situation.",
            "- Adapt tone to the context of the reply",
        ),
    )

    prompt = f"""You are an expert B2B sales copywriter for Interexy (software development company).

CONTEXT: {ctx_description}
DETECTED INTENT: {intent}

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

TASK: {ctx_task}

CATEGORIES:
1. Synergy-based (2-3): overlap between what they do and what we offer
2. Question-based (3-4): strategic questions about challenges
3. Insight-based (2-3): show understanding of their situation
4. Soft touch (2-3): "not selling, just curious" approach
5. Direct value prop (2-3): clear about what we do

REQUIREMENTS:
- 2-3 sentences max per message
- {ctx_requirement}
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
