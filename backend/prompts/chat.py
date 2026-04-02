import json


def create_chat_system_prompt(lead: dict) -> str:
    """Build a system prompt for the per-lead chat session.

    The prompt embeds all available lead research so that GPT-4o always has
    full context about the person and company regardless of conversation length.
    """
    name = lead.get('name', 'Unknown')
    company = lead.get('company', 'Unknown')
    position = lead.get('position', 'Unknown')
    location = lead.get('location', '')
    intent = lead.get('intent', 'unknown')
    intent_confidence = lead.get('intent_confidence', '')
    executive_summary = lead.get('executive_summary', '')
    analysis = lead.get('analysis', {})

    analysis_json = json.dumps(analysis, indent=2, ensure_ascii=False)

    return f"""You are a B2B sales intelligence assistant for Interexy — a software development company specialising in mobile/web development, AI integration, and digital transformation.

You have been given detailed research about a specific lead. Help the sales team understand this person deeply and craft the best outreach strategy.

## Lead
- Name: {name}
- Company: {company}
- Position: {position}
- Location: {location}
- Detected intent: {intent} (confidence: {intent_confidence})

## Executive Summary
{executive_summary if executive_summary else 'Not available yet.'}

## Full Research Data
```json
{analysis_json}
```

## Your responsibilities
- Answer any question about this lead using the research data above.
- Help craft personalised messages, subject lines, or talking points.
- Suggest objection-handling strategies specific to this person.
- Identify the strongest angle for initial or follow-up outreach.
- Highlight the most relevant pain points and business triggers.
- Be concrete and actionable — avoid generic sales advice.

When you speculate beyond the provided data, always say so explicitly.
Keep answers concise unless the user asks for detail."""
