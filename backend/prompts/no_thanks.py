import json
from datetime import datetime


def create_no_thanks_messages_prompt(analysis: dict, lead_name: str, lead_company: str, lead_position: str) -> str:
    """Create message generation prompt for soft objection / no-thanks leads"""
    qual = analysis.get('qualification', {})
    company = analysis.get('company_basics', {})
    pain_points = analysis.get('pain_point_analysis', {})
    deep_research = analysis.get('deep_research', {})
    recommended = analysis.get('recommended_action', {})
    value_props = analysis.get('interexy_value_props', {})
    vendor_inference = analysis.get('vendor_approach_inference', {})
    timing_triggers = analysis.get('timing_triggers_analysis', {})
    conv_analysis = analysis.get('conversation_analysis', {})
    rejection = conv_analysis.get('rejection_analysis', {})

    first_name = lead_name.split()[0] if lead_name else 'there'

    role_pains = pain_points.get('role_specific_pain_points', [])[:3]
    stage_pains = pain_points.get('stage_specific_pain_points', [])[:3]
    evidence = pain_points.get('evidence_from_research', [])[:3]
    active_triggers = timing_triggers.get('active_triggers', [])[:2]
    upcoming_triggers = timing_triggers.get('upcoming_triggers', [])[:2]
    vendor_eval = timing_triggers.get('vendor_evaluation_pattern', {})
    urgency = timing_triggers.get('urgency_assessment', {})
    vp_relevant = value_props.get('most_relevant', [])[:3]
    differentiation = value_props.get('differentiation_angle', '')
    news = deep_research.get('news', [])[:2]
    funding = deep_research.get('funding', {})

    prompt = f"""You are an expert B2B sales copywriter for Interexy (software development company).

CONTEXT:
This lead gave a soft rejection / "no thanks" response to our outreach. We need re-engagement messages that are respectful, curiosity-driven, and non-pushy.

LEAD INFORMATION:
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}
First name: {first_name}

ANALYSIS SUMMARY:
Qualification: {qual.get('status', 'N/A')}, Fit Score: {qual.get('fit_score', 0)}/10
Vendor Readiness: {qual.get('vendor_readiness', 'unknown')}
Company Stage: {company.get('stage', 'N/A')}, Size: {company.get('size', 'N/A')}, Industry: {company.get('industry', 'N/A')}

REJECTION ANALYSIS:
Type: {rejection.get('rejection_type', 'not_applicable')}
Confidence: {rejection.get('confidence', 'low')}
Evidence: {rejection.get('evidence', 'N/A')}
Recommended Approach: {rejection.get('recommended_approach', 'N/A')}

PAIN POINTS:
Role-Specific (top 3):
{chr(10).join(f"- {p}" for p in role_pains)}

Stage-Specific (top 3):
{chr(10).join(f"- {p}" for p in stage_pains)}

Evidence from Research:
{chr(10).join(f"- {e}" for e in evidence)}

VENDOR APPROACH:
Hypothesis: {vendor_inference.get('current_solution_hypothesis', 'unknown')}
Confidence: {vendor_inference.get('confidence', 'low')}
Evidence: {json.dumps(vendor_inference.get('evidence', []), indent=2)}
Build vs Buy: {json.dumps(vendor_inference.get('build_vs_buy_philosophy', {}), indent=2)}

TIMING TRIGGERS:
Active (0-3 months): {json.dumps(active_triggers, indent=2)}
Upcoming (3-6 months): {json.dumps(upcoming_triggers, indent=2)}
Vendor Eval Pattern: {json.dumps(vendor_eval, indent=2)}
Urgency: {json.dumps(urgency, indent=2)}

RECENT CONTEXT:
News: {json.dumps(news, indent=2)}
Funding: {json.dumps(funding, indent=2)}

INTEREXY VALUE PROPS:
{chr(10).join(f"- {v}" for v in vp_relevant)}
Differentiation: {differentiation}

---

TASK:
Generate 12-15 re-engagement message variants for a lead who said "no thanks" / soft rejection.
Messages should be respectful, curious, and NOT salesy.

MESSAGE TYPES TO GENERATE:

1. ASSUMPTION QUESTIONS (3-4 variants)
Strategy: Make an assumption about their current setup to spark correction/confirmation.
Example: "Fair enough, {first_name}! I'm guessing you already work with [X] - am I right?"
Use the vendor_approach_inference to make smart assumptions.

2. CLARIFICATION - WHY I REACHED OUT (2-3 variants)
Strategy: Explain the specific reason you reached out based on news/research hook.
Example: "Fair enough! The reason I reached out is I saw [news hook]. Typically when companies [do X], they face [pain]. We specialize in [capability] - wanted to see if relevant."
Use real news/triggers from research.

3. FUTURE-FOCUSED / TIMING QUESTIONS (3-4 variants)
Strategy: Ask about future plans/timing rather than current needs.
Example: "Understood! What would typically trigger {lead_company} to evaluate [vendors/new solutions]?"
Use timing_triggers to ask about specific upcoming triggers.

4. BENCHMARK / VALUE-ADD (2 variants)
Strategy: Offer something valuable with no strings attached.
Example: "No worries! If helpful, I can share benchmarks on [specific KPI for their industry] - might be useful even if we don't work together."
Be specific to their industry/stage.

5. ALTERNATIVE ANGLES (2-3 variants)
Strategy: Pivot to a different angle - learning, referral, another person, or future timing.
Examples:
- "Got it! Out of curiosity, who at {lead_company} would typically own [X challenge]?"
- "Understood! Is there anyone else at {lead_company} I should be talking to?"
- "No worries! Mind if I check back in 6 months when timing might be better?"

REQUIREMENTS:
- Messages must be COMPLETE and ready-to-send (2-4 sentences max)
- Start with acknowledgment: "Fair enough!" / "Understood!" / "No worries!" / "Got it!"
- Always use first name: {first_name}
- Based on REAL data from research - not generic
- NO salesy language, no pressure, no urgency manufacturing
- Each message should feel genuinely curious and human
- Match sophistication to lead seniority

Return ONLY valid JSON:
{{
  "messages": [
    {{
      "id": 1,
      "type": "assumption_question",
      "message": "full ready-to-send message text",
      "rationale": "why this message works based on research",
      "best_for": "situation where this works best",
      "follow_up_ready": true
    }}
  ],
  "recommended_top_3": [1, 5, 8],
  "overall_strategy": {{
    "primary_approach": "...",
    "backup_approach": "...",
    "timing_recommendation": "..."
  }},
  "notes": "overall strategy notes for this lead"
}}

IMPORTANT:
- Use REAL data (company name, role, news, vendor signals, timing triggers)
- Type values: assumption_question | clarification | future_focused | benchmark | alternative_angle
- Return ONLY JSON, no markdown blocks"""

    return prompt
