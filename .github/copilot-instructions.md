# Copilot Instructions — Interexy Lead Analyzer

## Project Overview

B2B sales intelligence tool that fetches LinkedIn "catch-up" leads from HeyReach, runs deep company/profile research via OpenAI GPT-4o with web search, and generates 10–15 personalized follow-up message variants per lead.

**Stack:** Python 3.11+ FastAPI backend · React 19 frontend · Tailwind CSS + Shadcn UI · OpenAI GPT-4o · HeyReach API

---

## Commands

### Backend

```bash
cd backend
pip install -r requirements.txt

# Dev server (auto-reload)
uvicorn server:app --reload --port 8000

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
# Integration tests — requires backend running on :8000
python backend_test.py

# Single test (no dedicated test runner; run the file directly)
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

### Backend (`backend/server.py` — single file, 683 lines)

- **In-memory job store**: `jobs: Dict[str, Dict[str, Any]]` — no database. State is lost on restart by design.
- **Async pipeline** launched via `asyncio.create_task()` from `POST /api/run-analysis`. Steps: `starting → fetching → filtering → analyzing → done`.
- **Two-phase OpenAI calls per lead**:
  1. Analysis prompt → GPT-4o with `web_search` tool enabled (180 s timeout) — 4-level research framework.
  2. Message generation prompt → GPT-4o without web search (120 s timeout) — 5 message categories, 10–15 variants.
- **5-second rate-limit pause** between leads.
- **JSON repair**: `json-repair` library handles malformed OpenAI JSON responses; `parse_json_from_text()` strips markdown fences before parsing.
- **Retry mechanism**: `POST /api/retry-leads` resets failed leads and re-runs the pipeline for them only.

### Frontend (`frontend/src/`)

- `App.js` owns all state (`jobId`, `status`, `results`, `isRunning`, `error`, `accounts`, `selectedAccountId`).
- `Dashboard.jsx` receives state + callbacks as props; renders header, account selector, progress, and results.
- `LeadCard.jsx` → `MessageGroup.jsx` (leaf).
- **Polling**: `setInterval` every 3 s against `GET /api/status/{job_id}`; cleared via `useRef` on cleanup/completion.
- No external state manager (no Redux/Zustand); plain `useState` + prop drilling is intentional.

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
