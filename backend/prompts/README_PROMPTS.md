# Message Generation Prompts Reference

## Overview

The system now uses **intent-specific message generation** based on the classified intent type from the lead's response.

## Intent → Prompt Mapping

| Intent Type | Prompt Function | File | Message Types | Count |
|-------------|-----------------|------|---------------|-------|
| `interested` | `create_interested_messages_prompt()` | `interested.py` | direct_cta, value_first, solution_pitch, social_proof, exploratory | 12-15 |
| `catchup_thanks` | `create_catchup_messages_prompt()` | `catchup.py` | synergy, question, insight, soft_touch, direct_value | 10-15 |
| `soft_objection` | `create_no_thanks_messages_prompt()` | `no_thanks.py` | assumption_question, clarification, future_focused, benchmark, alternative_angle | 12-15 |
| `hard_rejection` | `create_hard_rejection_messages_prompt()` | `hard_rejection.py` | polite_withdrawal, door_open, professional_closure | 5-7 ⚠️ |
| `question` | `create_question_messages_prompt()` | `question.py` | direct_answer, answer_question, answer_case_study, educational, answer_cta | 12-15 |
| `redirect` | `create_redirect_messages_prompt()` | `redirect.py` | thank_confirm, thank_intro, clarification, pivot_connect, context_redirect | 12-15 |
| `ooo` | `create_catchup_messages_prompt()` | `catchup.py` | (generic catchup logic) | 10-15 |
| `hiring` | `create_catchup_messages_prompt()` | `catchup.py` | (generic catchup logic) | 10-15 |
| `competitor` | *Skipped* | N/A | No messages generated | 0 |
| `neutral` | `create_catchup_messages_prompt()` | `catchup.py` | (generic catchup logic) | 10-15 |

---

## File Structure

```
backend/prompts/
├── __init__.py                    # Exports all prompt functions
├── base_research.py               # Deep analysis prompt (web search)
├── catchup.py                     # Original catchup logic + router
├── interested.py                  # NEW: For "interested" intent
├── hard_rejection.py              # NEW: For "hard_rejection" intent
├── question.py                    # NEW: For "question" intent
├── redirect.py                    # NEW: For "redirect" intent
└── no_thanks.py                   # For "soft_objection" intent
```

---

## Usage

### In `server.py` / `queue_processor.py`

```python
from prompts import create_catchup_messages_prompt

# The catchup function now routes to intent-specific handlers
if intent == 'soft_objection':
    msg_prompt = create_no_thanks_messages_prompt(
        analysis, lead_name, lead_company, lead_position
    )
else:
    # This now automatically routes to the correct handler
    msg_prompt = create_catchup_messages_prompt(
        analysis, lead_name, lead_company, lead_position, intent
    )
```

### Direct Usage

```python
from prompts import (
    create_interested_messages_prompt,
    create_question_messages_prompt,
    create_redirect_messages_prompt,
    create_hard_rejection_messages_prompt,
)

# For interested leads
prompt = create_interested_messages_prompt(analysis, name, company, position)

# For leads who asked questions
prompt = create_question_messages_prompt(analysis, name, company, position)

# For leads who redirected
prompt = create_redirect_messages_prompt(analysis, name, company, position)

# For hard rejections (use with caution!)
prompt = create_hard_rejection_messages_prompt(analysis, name, company, position)
```

---

## Message Type Descriptions

### `interested.py` — Lead expressed genuine interest

| Type | Description | Example Start |
|------|-------------|---------------|
| `direct_cta` | Propose specific next step (call, demo) | "Great to hear, John! Would you be open to a 20-min call..." |
| `value_first` | Offer value before asking for time | "Awesome, John! Before we hop on a call, I'd love to share..." |
| `solution_pitch` | Connect interest to specific capability | "Glad you're interested, John! Based on what you're building..." |
| `social_proof` | Use case studies + CTA | "Thanks for the interest, John! We recently helped [company]..." |
| `exploratory` | Low-pressure, exploratory | "Appreciate the interest, John! No pressure at all..." |

---

### `question.py` — Lead asked specific questions

| Type | Description | Example Start |
|------|-------------|---------------|
| `direct_answer` | Answer directly + context | "Great question, John! [Answer]. For context, we typically..." |
| `answer_question` | Answer + related question | "Thanks for asking, John! [Answer]. I'm curious - what's your current..." |
| `answer_case_study` | Answer + case study | "Good question, John! [Answer]. We actually helped [company]..." |
| `educational` | Provide educational insight | "Happy to clarify, John! [Answer + insight]. One thing we've noticed..." |
| `answer_cta` | Answer + soft CTA | "Hope this helps, John! [Answer]. If you'd like to dive deeper..." |

---

### `redirect.py` — Lead redirected to another person

| Type | Description | Example Start |
|------|-------------|---------------|
| `thank_confirm` | Thank + confirm next step | "Thanks for pointing me in the right direction, John! I'll reach out..." |
| `thank_intro` | Thank + ask for warm intro | "Thanks, John! Would you be open to making a quick intro..." |
| `clarification` | Ask for more specifics | "Got it, John! Out of curiosity, who at [company] typically owns..." |
| `pivot_connect` | Stay connected for future | "Understood, John! Even if this isn't your area, happy to stay..." |
| `context_redirect` | Explain why + acknowledge | "Thanks for clarifying, John! I reached out because [reason]..." |

---

### `hard_rejection.py` — Lead gave hard rejection ⚠️

| Type | Description | Example Start |
|------|-------------|---------------|
| `polite_withdrawal` | Acknowledge + withdraw | "Understood, John. Thanks for letting me know - I'll respect that..." |
| `door_open` | Leave door open (6+ months) | "Got it, John. I'll note this and won't bother you again..." |
| `professional_closure` | Professional sign-off | "Thanks for the transparency, John. I appreciate you taking the time..." |

**⚠️ WARNING:** Hard rejections should typically NOT receive any follow-up messages. Use these only for professional closure.

---

### `no_thanks.py` — Lead gave soft objection

| Type | Description | Example Start |
|------|-------------|---------------|
| `assumption_question` | Make assumption to spark correction | "Fair enough, John! I'm guessing you already work with [X]..." |
| `clarification` | Explain why you reached out | "Fair enough! The reason I reached out is I saw [news hook]..." |
| `future_focused` | Ask about future plans/timing | "Understood! What would typically trigger [company] to evaluate..." |
| `benchmark` | Offer value-add with no strings | "No worries! If helpful, I can share benchmarks on [KPI]..." |
| `alternative_angle` | Pivot to different angle | "Got it! Out of curiosity, who at [company] would typically own..." |

---

## Output Format

All prompts return JSON with this structure:

```json
{
  "messages": [
    {
      "id": 1,
      "type": "direct_cta",
      "message": "Full ready-to-send message text...",
      "rationale": "Why this message works based on research",
      "best_for": "Situation where this works best",
      "follow_up_ready": true
    }
  ],
  "recommended_top_3": [1, 5, 8],
  "overall_strategy": {
    "primary_approach": "...",
    "timing_recommendation": "..."
  },
  "notes": "Overall strategy notes for this lead"
}
```

---

## Best Practices

1. **Always use the router function** `create_catchup_messages_prompt()` with the `intent` parameter
2. **Hard rejections** — use with extreme caution, typically should NOT receive follow-ups
3. **Questions** — actually ANSWER the question, don't dodge or just pitch
4. **Redirects** — be genuinely grateful, redirects are positive engagement signals
5. **Interested** — capitalize on momentum, move toward concrete next step
6. **All messages** — use REAL data from analysis (company name, role, news, funding, etc.)
