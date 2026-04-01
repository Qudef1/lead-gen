# Interexy Lead Analyzer

B2B sales intelligence tool that automatically analyzes LinkedIn "catch-up" leads from HeyReach and generates personalized follow-up messages using OpenAI.

## How It Works

### Automatic Mode (Webhook-driven)
1. **Lead replies on LinkedIn** → HeyReach detects the reply
2. **HeyReach sends webhook** → POST to `/api/webhook/heyreach`
3. **Auto-analysis starts** → Classification → Research → Message generation
4. **Results saved to SQLite** → Available instantly in the UI
5. **Lead gen opens the app** → Sees ready results, no waiting needed

### Manual Mode (On-demand)
1. Select LinkedIn account from dropdown
2. Click "Run Analysis" button
3. Wait for pipeline to complete (5-10 minutes)
4. View results

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Frontend | React 19, Tailwind CSS, Shadcn UI |
| AI | OpenAI GPT-4o (Responses API) |
| LinkedIn Data | HeyReach API |
| Database | SQLite (persistent storage) |

---

## Project Structure

```
lead-gen/
├── backend/
│   ├── server.py          # FastAPI app — all API endpoints and pipeline logic
│   ├── classifier.py      # Intent classifier (gpt-4o-mini, 10 intent types)
│   ├── database.py        # SQLite database module (leads, analyses, messages)
│   ├── webhook_handler.py # HeyReach webhook event processor
│   ├── queue_processor.py # Background queue processor for auto-analysis
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

## HeyReach Webhook Setup

### Configure Webhook in HeyReach

1. Go to HeyReach dashboard → Settings → Webhooks
2. Add new webhook with:
   - **URL**: `https://your-domain.com/api/webhook/heyreach`
   - **Event**: `EVERY_MESSAGE_REPLY_RECEIVED`
   - **Method**: POST
3. Save and test

### Webhook Payload

HeyReach sends JSON payload:
```json
{
  "event": "EVERY_MESSAGE_REPLY_RECEIVED",
  "data": {
    "conversationId": "abc123",
    "linkedInAccountId": 12345,
    "message": { ... },
    "correspondent": {
      "firstName": "John",
      "lastName": "Doe",
      "companyName": "Acme Corp",
      "position": "CEO",
      "profileUrl": "https://linkedin.com/in/johndoe"
    }
  }
}
```

### Local Testing with ngrok

For local development, use ngrok to expose your localhost:
```bash
ngrok http 8000
```
Then set webhook URL to `https://your-ngrok-subdomain.ngrok.io/api/webhook/heyreach`

---

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/accounts` | Returns list of available LinkedIn accounts |
| `POST` | `/webhook/heyreach` | HeyReach webhook endpoint (auto-analysis) |
| `POST` | `/run-analysis` | Start manual analysis pipeline. Body: `{"account_id": 12345}` |
| `GET` | `/status/{job_id}` | Poll job status (pending / processing / done / error) |
| `GET` | `/results/{job_id}` | Fetch complete results after job completes |
| `GET` | `/leads/{account_id}` | Get all analyzed leads from database |
| `GET` | `/queue/stats` | Get background queue statistics |
| `POST` | `/retry-leads` | Retry failed leads. Body: `{"job_id": "...", "lead_names": ["Name"]}` |

---

## Database Schema

SQLite database (`backend/leads.db`) stores all analyzed leads:

- **leads**: Conversation metadata (conversation_id, account_id, timestamps)
- **lead_profiles**: Profile info (name, company, position, LinkedIn URL)
- **classifications**: Intent classification (intent, confidence, reasoning)
- **analyses**: Deep research results (company info, funding, pain points, qualification)
- **messages**: Generated message variants (messages JSON, top 3 recommendations)
- **processing_queue**: Background job queue (pending/processing/completed/error)

---

## Important Notes for Deployment

### Persistence
- **SQLite database** stores all results permanently
- Results survive server restarts
- Queue processor runs continuously in background

### Automatic Analysis Flow
1. Webhook received → conversation queued
2. Queue processor picks up → fetches from HeyReach
3. Classification → Deep analysis → Message generation
4. All results saved to database
5. Frontend polls `/leads/{account_id}` every 5 seconds

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
- Webhook signature verification

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
| Webhook not received | Verify HeyReach webhook URL is correct and publicly accessible (use ngrok for local testing) |
| Queue stuck | Check `GET /api/queue/stats` — if pending > 0 for long time, restart backend |
