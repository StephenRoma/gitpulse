# ⚡ GitPulse — Sales Intelligence Dashboard

A local, fully-functional GitHub signal intelligence tool for Relevantz sales teams. Track what technologies target companies and existing clients are evaluating, experimenting with, and building — powered by the GitHub API and Claude AI.

---

## What It Does

- **Tracks GitHub activity** (stars, forks, new repos) from engineers at your target accounts
- **Scores accounts** by signal intensity and technology relevance
- **Generates AI briefings** via Claude — plain-language sales intelligence you can act on
- **Surfaces tech stack signals** — languages, frameworks, and topics engineers are engaging with
- Runs **entirely on your laptop** — no cloud infra, no database server, just SQLite locally

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Blueprint.js v5 + Vite |
| Backend | FastAPI (Python) |
| Database | SQLite (local file, zero config) |
| GitHub data | PyGithub |
| AI briefings | Anthropic Claude API |

---

## Prerequisites

Make sure these are installed on your machine:

- **Python 3.10+** — [python.org](https://python.org)
- **Node.js 18+** — [nodejs.org](https://nodejs.org)
- **npm** (comes with Node.js)

---

## Setup (One-Time)

### 1. Get Your API Keys

**GitHub Personal Access Token**
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **Generate new token (classic)**
3. Select scopes: `read:user`, `read:org`, `public_repo`
4. Generate and copy the token

**Anthropic API Key**
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Navigate to **API Keys** → **Create Key**
3. Add $5–10 credit (lasts months at demo usage)
4. Copy the key

---

### 2. Configure Environment

```bash
cd backend
cp .env.example .env
```

Open `backend/.env` and fill in your keys:

```env
GITHUB_TOKEN=ghp_your_token_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
LOOKBACK_DAYS=30
```

---

### 3. Start GitPulse

**Mac / Linux:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```
Double-click start.bat
```

The script will:
1. Create a Python virtual environment
2. Install all Python dependencies
3. Install Node.js dependencies
4. Start the FastAPI backend on port 8000
5. Start the Vite dev server on port 5173

Open your browser to **http://localhost:5173**

---

## Using GitPulse

### Adding Your First Account

1. Click **Add Account** in the top right
2. Enter the company name (e.g., "Acme Corp")
3. Enter their GitHub org handle (e.g., `acme-corp`) — optional but helpful
4. Choose type: **Prospect** or **Client**
5. Paste GitHub usernames of engineers you want to track, one per line
6. Click **Create Account**

> **Finding engineer GitHub usernames:** LinkedIn profiles often link to GitHub. Company GitHub orgs list their members publicly. Conference talk speaker bios frequently include GitHub handles.

### Running a Sync

Click **Sync Account** in the right panel to:
1. Collect GitHub activity for all tracked engineers (stars, forks, new repos from the last 30 days)
2. Score the account based on signal volume and technology relevance
3. Generate a Claude AI briefing with opportunities and recommended next steps

Sync time depends on how many engineers you're tracking. Expect ~5–30 seconds per account.

### Reading the AI Briefing

The briefing card at the top of each account shows:
- **Summary** — What's happening at this company, in plain language
- **Key Themes** — Technology patterns Claude detected
- **Opportunities** — Specific Relevantz service angles to pursue
- **Friction Signals** — Pain points or transitions happening
- **Recommended Next Step** — Concrete sales action to take
- **Urgency** — High / Medium / Low priority rating

### Managing Engineers

Use the right panel to add or remove engineers from any account without re-syncing. Then run a fresh sync to pick up their activity.

---

## API Reference

The FastAPI backend auto-generates interactive docs at:

```
http://localhost:8000/docs
```

Key endpoints:
- `GET /accounts` — List all accounts with signal counts
- `POST /accounts/{id}/sync` — Start background sync
- `GET /accounts/{id}/sync-status` — Poll sync progress
- `GET /accounts/{id}/signals` — Raw GitHub signals
- `GET /accounts/{id}/briefing` — Latest AI briefing
- `POST /sync-all` — Sync every account

---

## File Structure

```
gitpulse/
├── start.sh              # Mac/Linux launcher
├── start.bat             # Windows launcher
│
├── backend/
│   ├── main.py           # FastAPI app + all routes
│   ├── database.py       # SQLite async data layer
│   ├── ingest.py         # GitHub signal collection engine
│   ├── brief.py          # Claude AI briefing generator
│   ├── requirements.txt  # Python dependencies
│   ├── .env.example      # Environment template
│   └── .env              # Your keys (never commit this)
│
└── frontend/
    ├── index.html
    ├── vite.config.js    # Dev server + API proxy config
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx        # Root layout + state management
        ├── api.js         # Backend API client
        ├── index.css      # Relevantz-branded Blueprint overrides
        └── components/
            ├── TopNav.jsx
            ├── AccountSidebar.jsx
            ├── BriefingCard.jsx
            ├── SignalFeed.jsx
            ├── RightPanel.jsx
            └── AddAccountDialog.jsx
```

---

## Customization

### Adjust Signal Lookback Window

In `backend/.env`:
```env
LOOKBACK_DAYS=60   # Look back 60 days instead of 30
```

### Add More Tech Keywords

In `backend/ingest.py`, extend the `TECH_KEYWORDS` list with any technologies relevant to Relevantz's service areas. Repos matching these keywords score higher.

### Change Signal Weights

In `backend/ingest.py`, adjust `SIGNAL_WEIGHTS` to prioritize different signal types:
```python
SIGNAL_WEIGHTS = {
    "star": 1,      # Engineer starred a repo
    "fork": 3,      # Engineer forked a repo (stronger intent)
    "new_repo": 4,  # Engineer created a new repo (strongest signal)
    "push": 2,      # Push activity
}
```

### Tune the AI Briefing Prompt

In `backend/brief.py`, edit `BRIEFING_SYSTEM` to change what Claude focuses on — you can emphasize Relevantz's specific service areas, add competitor context, or change the output format.

---

## Rate Limits

With a single GitHub token you get **5,000 API requests/hour**. For a demo tracking ~20 engineers across 5–10 accounts this is more than sufficient. If you scale up significantly, GitHub's documented solution is token pooling (multiple tokens rotated per request).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `GITHUB_TOKEN not set` | Check `backend/.env` exists with your token |
| `Port 8000 already in use` | Kill any existing process: `lsof -ti:8000 \| xargs kill` |
| `Port 5173 already in use` | Kill: `lsof -ti:5173 \| xargs kill` |
| Sync returns 0 signals | Engineer may have no public activity in the lookback window. Try a longer `LOOKBACK_DAYS`. |
| Briefing says "No signals" | Run a sync first before generating a briefing |
| npm install fails | Make sure Node.js 18+ is installed: `node --version` |
