# Copilot Instructions — Interexy Lead Analyzer

## Project Overview

B2B sales intelligence tool that fetches LinkedIn conversations from HeyReach, classifies each reply by intent (10 types) using GPT-4o-mini, runs deep company/profile research via GPT-4o with web search, and generates 10–15 personalized follow-up message variants per lead.

**Stack:** Python 3.11+ FastAPI backend · React 19 frontend · Tailwind CSS + Shadcn UI · OpenAI GPT-4o / GPT-4o-mini · HeyReach API

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
├── server.py          # FastAPI app, pipeline orchestration, API routes
├── classifier.py      # Intent classifier (GPT-4o-mini + keyword fallback)
├── prompts/
│   ├── __init__.py              # Re-exports all 3 prompt functions
│   ├── base_research.py         # Universal lead research prompt (GPT-4o + web search)
│   ├── catchup.py               # Message generation for all non-objection intents
│   └── no_thanks.py             # Message generation for soft_objection intent
└── requirements.txt
```

- **In-memory job store**: `jobs: Dict[str, Dict[str, Any]]` — no database. State lost on restart by design.
- **Async pipeline** launched via `asyncio.create_task()` from `POST /api/run-analysis`. Steps: `starting → fetching → classifying → analyzing → done`.
- **Three-phase OpenAI calls per lead**:
  1. `classify_conversations` → GPT-4o-mini, no tools — classifies all conversations by intent in one batch call.
  2. Analysis prompt → GPT-4o with `web_search` tool enabled (180 s timeout) — 4-level research framework.
  3. Message generation prompt → GPT-4o without web search (120 s timeout) — 5 message categories, 10–15 variants.
- **Intent routing**: `soft_objection` → `create_no_thanks_messages_prompt`; all other intents → `create_catchup_messages_prompt`.
- **5-second rate-limit pause** between leads.
- **JSON repair**: `json-repair` library handles malformed OpenAI JSON; `parse_json_from_text()` strips markdown fences before parsing.
- **Retry mechanism**: `POST /api/retry-leads` resets failed leads and re-runs the pipeline for them only.
- **sys.path fix**: `server.py` inserts `backend/` into `sys.path` at startup so bare `from classifier import` works when running from repo root.

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
- `Dashboard.jsx` receives state + callbacks as props; renders header, account selector, progress, and results.
- `LeadCard.jsx` → `MessageGroup.jsx` (leaf). Each lead card shows a colored `IntentBadge` next to the lead name.
- **Polling**: `setInterval` every 3 s against `GET /api/status/{job_id}`; cleared via `useRef` on cleanup/completion.
- No external state manager (no Redux/Zustand); plain `useState` + prop drilling is intentional.

### Tests (`tests/`)

```
tests/
├── conftest.py          # Pytest fixtures: 10 conversation types + minimal_analysis
├── test_classifier.py   # 39 tests for classifier.py
└── test_prompts.py      # 46 tests for prompts/
```

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/accounts` | List LinkedIn accounts from env |
| POST | `/api/run-analysis` | `{"account_id": int}` → starts background job, returns `{job_id}` |
| GET | `/api/status/{job_id}` | Poll progress |
| GET | `/api/results/{job_id}` | Fetch full results after completion |
| POST | `/api/retry-leads` | `{"job_id": str, "lead_names": [str]}` |

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
- Pydantic models validate all request bodies (see `RunAnalysisRequest`, `RetryLeadsRequest`).
- Raise `HTTPException` (not generic exceptions) from API route handlers.
- New pipeline steps must update `jobs[job_id]["step"]` and `jobs[job_id]["status_text"]` so the frontend progress display stays accurate.
- Helper functions `_extract_openai_text` and `_parse_json_from_text` are intentionally duplicated in `classifier.py` (prefixed with `_`) to avoid circular imports with `server.py`.

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
