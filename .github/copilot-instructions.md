# Copilot Instructions — Interexy Lead Analyzer

## Project Overview

B2B sales intelligence tool that fetches LinkedIn conversations from HeyReach, classifies each reply by intent (10 types) using GPT-4o-mini, runs deep company/profile research via GPT-4o with web search, generates 10–15 personalized follow-up message variants per lead, and provides a per-lead AI chat interface backed by GPT-5.1 with web search.

**Stack:** Python 3.11+ FastAPI backend · React 19 frontend · Tailwind CSS + Shadcn UI · OpenAI GPT-4o / GPT-4o-mini / GPT-5.1 · HeyReach API · SQLite (via `aiosqlite`)

---

## Commands

### Backend

```bash
# From repo root:
pip install -r backend/requirements.txt

# Dev server (auto-reload)
uvicorn backend.server:app --reload --port 8000

# API docs
# http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps   # --legacy-peer-deps is required

npm start          # http://localhost:3000
npm run build
npm test
```

### Testing

```bash
# Run all unit tests (from repo root)
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_classifier.py -v

# Run a single test
python -m pytest tests/test_classifier.py::TestKeywordFallbackIntent::test_keyword_matching -v

# Integration tests — requires backend running on :8000
python backend_test.py
```

### Linting / Formatting

```bash
cd backend
flake8 server.py
black server.py
```

---

## Architecture

### Backend

```
backend/
├── server.py            # FastAPI app, pipeline orchestration, all API routes
├── classifier.py        # Intent classifier (GPT-4o-mini + keyword fallback)
├── database.py          # SQLite persistence layer (aiosqlite); leads, queue tables
├── webhook_handler.py   # HeyReach webhook processing + smart re-analysis logic
├── queue_processor.py   # Background async loop: picks from queue → classify → analyze → save
├── prompts/
│   ├── __init__.py          # Re-exports all prompt builder functions
│   ├── base_research.py     # Universal lead research prompt (GPT-4o + web search)
│   ├── catchup.py           # Message generation for catchup/thanks intents
│   ├── no_thanks.py         # Message generation for soft_objection intent
│   ├── interested.py        # Message generation for interested intent
│   ├── hard_rejection.py    # Response strategy for hard_rejection
│   ├── question.py          # Message generation for question intent
│   ├── redirect.py          # Message generation for redirect intent
│   └── chat.py              # System prompt builder for per-lead AI chat
└── requirements.txt
```

- **Dual storage**: In-memory `jobs` dict for live pipeline runs + SQLite `leads.db` for persistence across restarts.
- **Async pipeline** launched via `asyncio.create_task()` from `POST /api/run-analysis`. Steps: `starting → fetching → classifying → analyzing → done`.
- **Three-phase OpenAI calls per lead** (pipeline):
  1. `classify_conversations` → GPT-4o-mini, no tools — batch-classifies all conversations by intent.
  2. Analysis prompt → GPT-4o with `web_search` tool (180 s timeout) — 4-level research framework.
  3. Message generation prompt → GPT-4o without web search (120 s timeout) — 5 categories, 10–15 variants.
- **Intent routing for message generation**:
  - `soft_objection` → `create_no_thanks_messages_prompt`
  - `interested` → `create_interested_messages_prompt`
  - `question` → `create_question_messages_prompt`
  - `redirect` → `create_redirect_messages_prompt`
  - `hard_rejection` → `create_hard_rejection_messages_prompt`
  - all others → `create_catchup_messages_prompt`
- **5-second rate-limit pause** between leads in pipeline.
- **JSON repair**: `json-repair` library handles malformed OpenAI JSON; `parse_json_from_text()` strips markdown fences before parsing.
- **Retry mechanism**: `POST /api/retry-leads` resets failed leads and re-runs the pipeline for them only.
- **sys.path fix**: `server.py` inserts `backend/` into `sys.path` at startup so bare `from classifier import` works when running from repo root.

### SQLite Persistence (`database.py`)

- DB file: `backend/leads.db` — created at runtime, **not committed to git** (in `.gitignore`).
- `init_db()` runs on FastAPI startup (idempotent — uses `CREATE TABLE IF NOT EXISTS` and safe `ALTER TABLE` for migrations).
- Key tables: `leads` (full analysis + messages JSON), `processing_queue` (webhook-triggered analysis jobs).
- Key columns on `leads`: `conversation_id` (HeyReach ID, primary key), `analyzed_at` (ISO timestamp), `last_message_at` (for re-analysis gating).
- Queue deduplication: `add_to_queue()` skips if `pending`/`processing` entry already exists for that `conversation_id`.

### Webhook & Re-analysis (`webhook_handler.py`)

- Endpoint: `POST /api/webhook/heyreach` — receives `EVERY_MESSAGE_REPLY_RECEIVED` events from HeyReach.
- Re-analysis logic: extracts message timestamp from event → compares vs `analyzed_at` in DB → re-queues only if message is **newer** than last analysis. Falls back to `now` if HeyReach doesn't send a timestamp.
- `queue_processor.py` runs as a background asyncio task; polls `processing_queue`, calls classify → analyze → save. Skips deep analysis for `hard_rejection`, `ooo`, `competitor` intents.
- Webhook signature verification: **not implemented** (pending mentor consultation).

### Per-lead AI Chat (`prompts/chat.py` + `/api/chat`)

- Each lead card has an **"Ask AI"** button that opens a ShadCN `Sheet` side panel (`LeadChatPanel.jsx`).
- Backend: `call_openai_chat()` uses the OpenAI **Responses API** (`/v1/responses`) with model `gpt-5.1` and `web_search` tool enabled (90 s timeout).
- System prompt built by `create_chat_system_prompt(lead)` — embeds lead name, company, position, intent, executive summary, and full analysis JSON.
- Full conversation history is sent on every request (API is stateless — no server-side session).
- **Lookup order** in `/api/chat`: (1) SQLite by `conversation_id`, (2) in-memory jobs by `job_id` + `lead_name` — chat works both after page reload and during a live analysis session.
- The "Ask AI" button renders when `lead.conversation_id` exists — this is always present for DB leads and is also attached to in-memory leads via the pipeline, so it survives page reloads.

### Intent Classification (10 types)

Defined in `classifier.py → INTENT_TYPES`:

| Intent | Meaning |
|---|---|
| `interested` | Positive, wants to learn more / schedule a call |
| `catchup_thanks` | Casual catch-up or thank-you reply |
| `soft_objection` | Polite rejection or "not now" |
| `hard_rejection` | Clear "not interested", do not contact |
| `ooo` | Out-of-office auto-reply |
| `hiring` | Recruiting or job offer |
| `question` | Asking a specific question |
| `redirect` | Routing to another person |
| `not_relevant` | Off-topic message |
| `other` | Doesn't fit any category |

Only conversations where CORRESPONDENT appears in last 5 messages are processed; others are silently skipped.

### Frontend (`frontend/src/`)

- `App.js` owns all state (`jobId`, `status`, `results`, `isRunning`, `error`, `accounts`, `selectedAccountId`).
- `Dashboard.jsx` receives state + callbacks as props; renders header, account selector, progress, results, and DB-backed lead list (`leadsFromDb`).
- `LeadCard.jsx` → `MessageGroup.jsx` (leaf). Shows `IntentBadge`, "Ask AI" button (when `lead.conversation_id` present), and delete button.
- `LeadChatPanel.jsx` — ShadCN `Sheet` side panel; sends `conversation_id` in requests; renders chat history with markdown-like formatting.
- **Polling**: `setInterval` every 3 s against `GET /api/status/{job_id}`; cleared via `useRef` on cleanup/completion.
- No external state manager (no Redux/Zustand); plain `useState` + prop drilling is intentional.

### Tests (`tests/`)

```
tests/
├── conftest.py          # Pytest fixtures: 10 conversation types + minimal_analysis
├── test_classifier.py   # 39 tests for classifier.py
└── test_prompts.py      # 46 tests for prompts/
```

86 tests total, all passing.

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/` | Health check |
| GET | `/api/accounts` | List LinkedIn accounts from env |
| POST | `/api/webhook/heyreach` | Receive HeyReach reply events → queue re-analysis |
| GET | `/api/leads/{account_id}` | Get persisted leads from DB for an account |
| GET | `/api/leads` | Get all persisted leads from DB |
| DELETE | `/api/leads/{conversation_id}` | Delete a lead from DB |
| GET | `/api/queue/stats` | Queue depth and status counts |
| POST | `/api/run-analysis` | `{"account_id": int}` → starts background job, returns `{job_id}` |
| POST | `/api/retry-leads` | `{"job_id": str, "lead_names": [str]}` |
| GET | `/api/status/{job_id}` | Poll live pipeline progress |
| GET | `/api/results/{job_id}` | Fetch full results from in-memory job |
| POST | `/api/chat` | `{"conversation_id": str, "messages": [...], "lead_name": str}` → GPT-5.1 reply |

### Environment Variables

**`backend/.env`**
```
HEYREACH_API_KEY=...
OPENAI_API_KEY=...
LINKEDIN_ACCOUNTS=[{"id":12345,"name":"Account Name"}]
CORS_ORIGINS=http://localhost:3000
```

⚠️ `LINKEDIN_ACCOUNTS` must be a **single-line** JSON string — `python-dotenv` does not support multiline values.

**`frontend/.env`**
```
REACT_APP_BACKEND_URL=http://localhost:8000
```

---

## Key Conventions

### Design System

Defined authoritatively in `design_guidelines.json`. Always follow it for UI work:

- **Colors**: Primary `#1a2744` (navy), Accent `#10b981` (emerald), Background `#f8fafc` (slate-50).
- **Fonts**: Inter (headings + body), JetBrains Mono (monospace).
- **Fit score badges**: green (8–10 High Fit), amber (5–7 Medium Fit), red (1–4 Low Fit).
- **Light mode only** — no dark mode, no gradients, flat colors.
- Every interactive element **must** have a `data-testid` attribute.
- Use **Lucide React** for all icons.
- Copy actions **must** trigger a **Sonner toast** notification.
- Show **detailed step-by-step progress text**, not generic spinners.

### Backend Patterns

- All HTTP calls use `async with httpx.AsyncClient()` inside async functions.
- Pydantic models validate all request bodies (see `RunAnalysisRequest`, `RetryLeadsRequest`, `ChatRequest`).
- Raise `HTTPException` (not generic exceptions) from API route handlers.
- New pipeline steps must update `jobs[job_id]["step"]` and `jobs[job_id]["status_text"]` so the frontend progress display stays accurate.
- Helper functions `_extract_openai_text` and `_parse_json_from_text` are intentionally duplicated in `classifier.py` (prefixed with `_`) to avoid circular imports with `server.py`.
- `call_openai()` (pipeline) and `call_openai_chat()` (chat) are separate functions intentionally — different models, timeouts, and return types.

### Testing Protocol (`PIPELINE.txt` + `test_result.md`)

The project uses a structured multi-agent testing protocol:

- `test_result.md` is the communication file between main agent and testing agent.
- The **main agent writes `test_result.md` first**, then calls the testing agent.
- Each task tracks `working: true/false/"NA"`, `stuck_count`, `needs_retesting`, and `status_history`.
- Increment `stuck_count` when a task fails repeated fix attempts; alerts trigger when the count is high.
- `backend_test.py` is the integration test suite; run it against a live backend.

### Naming

- Python: `snake_case` functions and variables, `UPPER_SNAKE_CASE` env constants.
- React components: `PascalCase` files and function names.
- API routes: `kebab-case` (e.g., `/run-analysis`, `/retry-leads`).
- CSS/Tailwind: `kebab-case` classes; CSS custom properties in HSL format defined in `index.css`.

### `batch_process_reference.py`

This 37 KB file is a **reference/legacy implementation** — do not modify or import from it.
