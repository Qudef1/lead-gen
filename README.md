# Interexy Lead Analyzer

B2B sales intelligence tool that automatically analyzes LinkedIn "catch-up" leads from HeyReach and generates personalized follow-up messages using OpenAI.

## How It Works

1. Fetches unread LinkedIn conversations from HeyReach
2. Classifies each conversation by intent type (interested, catchup_thanks, soft_objection, hard_rejection, question, redirect, ooo, hiring, competitor, neutral) using GPT-4o-mini
3. For each lead with a recent reply: runs deep AI research (company info, funding, news, pain points) via GPT-4o with web search
4. Generates 10–15 personalized follow-up message variants per lead, with prompt selected by intent type
5. Displays results with fit scores, executive summaries, and recommended messages

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Frontend | React 19, Tailwind CSS, Shadcn UI |
| AI | OpenAI GPT-4o (Responses API) |
| LinkedIn Data | HeyReach API |

---

## Project Structure

```
lead-gen/
├── backend/
│   ├── server.py          # FastAPI app — all API endpoints and pipeline logic
│   ├── classifier.py      # Intent classifier (gpt-4o-mini, 10 intent types)
│   ├── prompts/
│   │   ├── base_research.py   # Universal lead research prompt (GPT-4o + web search)
│   │   ├── catchup.py         # Message generation for catchup / general leads
│   │   └── no_thanks.py       # Message generation for soft objection leads
│   ├── requirements.txt   # Python dependencies
│   └── .env               # API keys (not committed to git)
└── frontend/
    ├── src/
    │   ├── App.js                     # State management and API calls
    │   └── components/
    │       ├── Dashboard.jsx          # Main UI layout
    │       ├── LeadCard.jsx           # Individual lead display
    │       └── MessageGroup.jsx       # Message variants display
    ├── package.json
    └── .env               # Frontend config (not committed to git)
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ — **system-wide installation required**: download from [nodejs.org](https://nodejs.org/) (LTS version recommended). Do **not** rely on a Node.js bundled inside a Python virtualenv — it won't be accessible from a regular terminal.
- npm (bundled with Node.js)

### 1. Clone and configure environment

**Backend** — create `backend/.env`:
```env
HEYREACH_API_KEY=your_heyreach_api_key
OPENAI_API_KEY=your_openai_api_key
LINKEDIN_ACCOUNTS=[{"id":12345,"name":"Account Name"},{"id":67890,"name":"Another Account"}]
```

**Frontend** — create `frontend/.env`:
```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

### 2. Start backend

```bash
pip install -r backend/requirements.txt
uvicorn backend.server:app --reload --port 8000
```

### 3. Start frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

Frontend: **http://localhost:3000**
Backend API docs: **http://localhost:8000/docs**

> All commands above are run from the repository root (`lead-gen/`), except `npm` commands which require `cd frontend` first.

---

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/accounts` | Returns list of available LinkedIn accounts |
| `POST` | `/run-analysis` | Start analysis pipeline. Body: `{"account_id": 12345}` |
| `GET` | `/status/{job_id}` | Poll job status (pending / processing / done / error) |
| `GET` | `/results/{job_id}` | Fetch complete results after job completes |
| `POST` | `/retry-leads` | Retry failed leads. Body: `{"job_id": "...", "lead_names": ["Name"]}` |

---

## Important Notes for Deployment

### Memory / State
- Info is stored **in-memory** — they are lost on server restart
- This is fine for the current use case (run analysis, read results, done)
- If persistence is needed in the future, MongoDB integration is planned (see backlog)

### API Costs
- Each lead costs approximately **$0.05–0.20** in OpenAI API usage (GPT-4o with web search)
- HeyReach API: standard plan limits apply

### Adding / Removing LinkedIn Accounts
Edit the `LINKEDIN_ACCOUNTS` array in `backend/.env` and restart the backend:
```env
LINKEDIN_ACCOUNTS=[
  {"id": 54937, "name": "Helen Grant"},
  {"id": 110357, "name": "Artem Morozov"}
]
```

---

## Backlog / Planned Features

- Export results to CSV/PDF
- Analysis history with MongoDB persistence
- Manual lead input by LinkedIn URL
- Send messages directly back to HeyReach
- Analytics dashboard

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `npm: command not found` / `npm is not recognized` | Node.js is not installed system-wide. Download and install it from [nodejs.org](https://nodejs.org/) (LTS). A Node.js that lives inside a Python venv is not on your PATH. |
| `npm install` fails with peer dependency error | Use `npm install --legacy-peer-deps` |
| `emergentintegrations` package not found | Skip it — it's listed in requirements.txt but not used in the code |
| `Analysis failed: Expecting value: line N column N` | JSON parsing error from OpenAI — handled automatically by `json-repair`. Retry the lead using the "Retry Selected" button |
| Frontend shows blank page after build | Check that `REACT_APP_BACKEND_URL` is set correctly in `frontend/.env` before running `npm run build` |
| Backend CORS error | Add your frontend URL to `CORS_ORIGINS` in `backend/.env` |
