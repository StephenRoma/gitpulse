import os
import json
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

import database as db
import ingest as ingester
import brief as briefer
import rfp_search
import conference_intel
import texas_screener

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield

app = FastAPI(title="Quorum API", lifespan=lifespan)

_default_origins = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000"
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory sync status ────────────────────────────────────────────────────
sync_status: dict[int, dict] = {}

def set_syncing(account_id: int, status: str, detail: str = ""):
    sync_status[account_id] = {"status": status, "detail": detail}

# ── In-memory report status ───────────────────────────────────────────────────
report_status: dict[int, dict] = {}

# ── Pydantic models ──────────────────────────────────────────────────────────
class CreateAccountRequest(BaseModel):
    name: str
    district_domain: Optional[str] = ""
    account_type: str = "prospect"
    nces_id: Optional[str] = None
    district_legal_name: Optional[str] = None

class AddContactRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

class UpdateAccountRequest(BaseModel):
    name: Optional[str] = None
    district_domain: Optional[str] = None
    account_type: Optional[str] = None
    nces_id: Optional[str] = None
    district_legal_name: Optional[str] = None

class CreateTeamRequest(BaseModel):
    name: str
    color: str = '#1A2158'

class UpdateTeamRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class AssignTeamRequest(BaseModel):
    team_id: Optional[int] = None

class TagSignalRequest(BaseModel):
    theme: str

# ── Hot signals (cross-account) ───────────────────────────────────────────────
@app.get("/signals/hot")
async def get_hot_signals(limit: int = 10):
    return await db.get_hot_signals(limit=min(limit, 50))

# ── Accounts ─────────────────────────────────────────────────────────────────
@app.get("/accounts")
async def list_accounts():
    return await db.get_accounts()

@app.post("/accounts")
async def create_account(req: CreateAccountRequest):
    account_id = await db.create_account(
        name=req.name,
        district_domain=req.district_domain,
        account_type=req.account_type,
        nces_id=req.nces_id,
        district_legal_name=req.district_legal_name,
    )
    return {"id": account_id, "message": "Account created"}

@app.delete("/accounts/{account_id}")
async def delete_account(account_id: int):
    await db.delete_account(account_id)
    return {"message": "Account deleted"}

@app.get("/accounts/{account_id}")
async def get_account(account_id: int):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@app.patch("/accounts/{account_id}")
async def update_account(account_id: int, req: UpdateAccountRequest):
    account = await db.update_account(
        account_id, name=req.name, district_domain=req.district_domain,
        account_type=req.account_type, nces_id=req.nces_id,
        district_legal_name=req.district_legal_name,
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

# ── Contacts ─────────────────────────────────────────────────────────────────
@app.get("/accounts/{account_id}/engineers")
async def get_contacts_compat(account_id: int):
    return await db.get_contacts(account_id)

@app.get("/accounts/{account_id}/contacts")
async def get_contacts(account_id: int):
    return await db.get_contacts(account_id)

@app.post("/accounts/{account_id}/contacts")
async def add_contact(account_id: int, req: AddContactRequest):
    contact_id = await db.add_contact(
        account_id,
        name=req.name,
        role=req.role,
        email=req.email,
        linkedin_url=req.linkedin_url,
        phone=req.phone,
    )
    contacts = await db.get_contacts(account_id)
    match = next((c for c in contacts if c["id"] == contact_id), None)
    return match or {"id": contact_id}

@app.delete("/engineers/{contact_id}")
async def remove_contact_compat(contact_id: int):
    await db.remove_contact(contact_id)
    return {"message": "Contact removed"}

@app.delete("/contacts/{contact_id}")
async def remove_contact(contact_id: int):
    await db.remove_contact(contact_id)
    return {"message": "Contact removed"}

@app.patch("/engineers/{contact_id}")
async def assign_contact_team_compat(contact_id: int, req: AssignTeamRequest):
    await db.assign_contact_team(contact_id, req.team_id)
    return {"message": "Contact updated"}

@app.patch("/contacts/{contact_id}")
async def assign_contact_team(contact_id: int, req: AssignTeamRequest):
    await db.assign_contact_team(contact_id, req.team_id)
    return {"message": "Contact updated"}

# ── Teams ───────────────────────────────────────────────────────────────────
@app.get("/accounts/{account_id}/teams")
async def get_teams(account_id: int):
    return await db.get_teams(account_id)

@app.post("/accounts/{account_id}/teams")
async def create_team(account_id: int, req: CreateTeamRequest):
    return await db.create_team(account_id, req.name, req.color)

@app.patch("/teams/{team_id}")
async def update_team(team_id: int, req: UpdateTeamRequest):
    await db.update_team(team_id, req.name, req.color)
    return {"message": "Team updated"}

@app.delete("/teams/{team_id}")
async def delete_team(team_id: int):
    await db.delete_team(team_id)
    return {"message": "Team deleted"}

# ── Signals ───────────────────────────────────────────────────────────────────
@app.get("/accounts/{account_id}/signals")
async def get_signals(account_id: int, limit: int = 300):
    return await db.get_signals(account_id, limit)
@app.get("/accounts/{account_id}/signal-tags")
async def get_signal_tags(account_id: int):
    return await db.get_signal_tags_map(account_id)

@app.post("/signals/{signal_id}/tags")
async def tag_signal(signal_id: int, req: TagSignalRequest):
    # Look up account_id from the signal
    import aiosqlite
    from pathlib import Path
    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT account_id FROM signals WHERE id = ?", (signal_id,)) as cursor:
            row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")
    await db.tag_signal(signal_id, row["account_id"], req.theme)
    return {"message": "Tagged"}

@app.delete("/signals/{signal_id}/tags/{theme}")
async def untag_signal(signal_id: int, theme: str):
    await db.untag_signal(signal_id, theme)
    return {"message": "Untagged"}
# ── Reports ────────────────────────────────────────────────────────────────
# Auto-group signals by type when no manual tags exist
SIGNAL_TYPE_TO_THEME = {
    "board_minutes_item": "governance",
    "essa_profile":       "district_profile",
    "state_initiative":   "policy",
    "job_posting":        "procurement_signal",
    "news_mention":       "public_perception",
    "press_release":      "public_perception",
}

THEME_LABELS = {
    "governance":         "Board Governance",
    "district_profile":   "District Profile",
    "policy":             "State Policy & Mandates",
    "procurement_signal": "Active Procurement Signals",
    "public_perception":  "Public Perception & News",
    "tech_initiative":    "Technology Initiative",
    "budget":             "Budget & Finance",
    "esser":              "ESSER / Federal Funding",
}

@app.get("/accounts/{account_id}/report")
async def get_report(account_id: int):
    report = await db.get_latest_report(account_id)
    if not report:
        return None
    try:
        report["content"] = json.loads(report["content"])
    except Exception:
        pass
    return report

@app.get("/accounts/{account_id}/report/status")
async def get_report_status(account_id: int):
    return report_status.get(account_id, {"status": "idle"})

@app.post("/accounts/{account_id}/report/generate")
async def generate_report(account_id: int, background_tasks: BackgroundTasks):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    async def _generate():
        report_status[account_id] = {"status": "generating", "detail": "Claude is writing your report..."}
        try:
            await _do_generate_report(account_id, account, key)
            report_status[account_id] = {"status": "done"}
        except Exception as e:
            report_status[account_id] = {"status": "error", "detail": str(e)}
            print(f"[report] Error for account {account_id}: {e}")

    background_tasks.add_task(_generate)
    return {"message": "Report generation started"}

async def _do_generate_report(account_id: int, account: dict, key: str):
    tagged_signals = await db.get_tagged_signals(account_id)

    # Group signals by theme — fall back to auto-grouping if no manual tags
    theme_groups: dict[str, list] = {}
    if tagged_signals:
        for sig in tagged_signals:
            for theme in sig.get("themes", []):
                if theme not in theme_groups:
                    theme_groups[theme] = []
                theme_groups[theme].append(sig)
    else:
        # Auto-group recent signals by signal type
        recent = await db.get_signals(account_id, limit=60)
        for sig in recent:
            theme = SIGNAL_TYPE_TO_THEME.get(sig.get("signal_type", ""), "platform_eng")
            if theme not in theme_groups:
                theme_groups[theme] = []
            if len(theme_groups[theme]) < 10:
                theme_groups[theme].append(sig)
        # Keep only themes with signals
        theme_groups = {k: v for k, v in theme_groups.items() if v}

    # Fetch latest briefing for context
    briefing_row = await db.get_latest_briefing(account_id)
    briefing_content = {}
    if briefing_row:
        try:
            briefing_content = json.loads(briefing_row["content"]) if isinstance(briefing_row["content"], str) else briefing_row["content"]
        except Exception:
            pass

    # Build a single prompt for all themes
    theme_blocks = []
    for theme, sigs in theme_groups.items():
        label = THEME_LABELS.get(theme, theme)
        lines = []
        for s in sigs[:10]:
            raw = s.get("raw_data") or {}
            if isinstance(raw, str):
                try: raw = json.loads(raw)
                except: raw = {}
            desc = (s.get("repo_description") or "")[:80]
            lines.append(f"  - [{s['signal_type'].upper()}] {s.get('engineer_username','')} → {s['repo_name']}: {desc}")
        theme_blocks.append(f"THEME KEY: {theme}\nTHEME LABEL: {label}\n" + "\n".join(lines))

    prompt = (
        f"You are writing an EdTech sales intelligence report for {account['name']}.\n"
        f"Account type: {account.get('account_type','prospect')} | Signal score: {account.get('signal_score',0)}/100\n\n"
        f"The sales team has tagged district procurement signals into strategic themes. "
        f"For each theme below, write a 2-3 sentence narrative that:\n"
        f"1. States what pattern the signals reveal about this district\n"
        f"2. Explains the procurement implication or pain point\n"
        f"3. Suggests a specific sales angle to open a conversation\n\n"
        + "\n\n".join(theme_blocks)
        + "\n\nReturn a JSON array (no markdown fences) with one object per theme.\n"
        "Use the exact THEME KEY value in each object:\n"
        "[{\"theme\": \"<THEME KEY>\", \"narrative\": \"...\"}]"
    )

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=key)
    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw_text = response.content[0].text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"): raw_text = raw_text[4:]
    narratives = json.loads(raw_text.strip())
    narrative_map = {n["theme"]: n["narrative"] for n in narratives}

    # Build report JSON
    themes_out = []
    for theme, sigs in theme_groups.items():
        themes_out.append({
            "theme": theme,
            "label": THEME_LABELS.get(theme, theme),
            "narrative": narrative_map.get(theme, ""),
            "signals": sigs[:20],
        })

    report_content = {
        "account": {
            "name": account["name"],
            "district_domain": account.get("district_domain", ""),
            "account_type": account.get("account_type", "prospect"),
            "signal_score": account.get("signal_score", 0),
        },
        "briefing": briefing_content,
        "themes": themes_out,
        "generated_at": datetime.utcnow().isoformat(),
    }
    await db.save_report(account_id, json.dumps(report_content))
    return report_content

# ── Briefings ─────────────────────────────────────────────────────────────────
@app.get("/accounts/{account_id}/briefing")
async def get_briefing(account_id: int):
    briefing = await db.get_latest_briefing(account_id)
    if not briefing:
        return None
    try:
        briefing["content"] = json.loads(briefing["content"])
    except:
        pass
    return briefing

@app.post("/accounts/{account_id}/briefing/generate")
async def generate_briefing(account_id: int, background_tasks: BackgroundTasks):
    async def _generate():
        set_syncing(account_id, "briefing", "Generating AI briefing...")
        try:
            await briefer.generate_briefing(account_id)
            set_syncing(account_id, "done")
        except Exception as e:
            set_syncing(account_id, "error", str(e))

    background_tasks.add_task(_generate)
    return {"message": "Briefing generation started"}

# ── Sync ──────────────────────────────────────────────────────────────────────
@app.post("/accounts/{account_id}/sync")
async def sync_account(account_id: int, background_tasks: BackgroundTasks):
    async def _sync():
        set_syncing(account_id, "syncing", "Scanning district signals...")
        try:
            result = await ingester.ingest_account(account_id)
            set_syncing(account_id, "briefing", "Generating AI briefing...")
            await briefer.generate_briefing(account_id)
            set_syncing(account_id, "done", f"Scanned {result['signals']} signals")
        except Exception as e:
            set_syncing(account_id, "error", str(e))
            print(f"Scan error for account {account_id}: {e}")

    background_tasks.add_task(_sync)
    return {"message": "Sync started"}

@app.get("/accounts/{account_id}/sync-status")
async def get_sync_status(account_id: int):
    return sync_status.get(account_id, {"status": "idle"})

@app.post("/sync-all")
async def sync_all(background_tasks: BackgroundTasks):
    accounts = await db.get_accounts()

    async def _sync_all():
        for account in accounts:
            aid = account["id"]
            set_syncing(aid, "syncing")
            try:
                await ingester.ingest_account(aid)
                await briefer.generate_briefing(aid)
                set_syncing(aid, "done")
            except Exception as e:
                set_syncing(aid, "error", str(e))
            await asyncio.sleep(1)

    background_tasks.add_task(_sync_all)
    return {"message": f"Syncing {len(accounts)} accounts"}

# ── Scan District (replaces import-org-members) ─────────────────────────────
@app.post("/accounts/{account_id}/import-org-members")
async def scan_district_contacts(account_id: int):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    # Contacts must be added manually in Quorum via the Add Contact form
    contacts = await db.get_contacts(account_id)
    return {"added": 0, "skipped": 0, "total": len(contacts), "suggested_teams": []}

# ── Chat ──────────────────────────────────────────────────────────────────────
@app.post("/accounts/{account_id}/chat")
async def chat_with_signals(account_id: int, req: ChatRequest):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    signals = await db.get_signals(account_id, limit=200)
    contacts = await db.get_contacts(account_id)
    briefing_row = await db.get_latest_briefing(account_id)
    signal_lines = []
    for s in signals[:100]:
        desc = (s.get("repo_description", "") or "")[:80]
        signal_lines.append(f"- [{s['signal_type'].upper()}] {s.get('engineer_username','')} → {s['repo_name']}: {desc}")
    contact_list = ", ".join(
        f"{c.get('name','?')} ({c.get('role','')})" for c in contacts[:20]
    )
    briefing_text = "No briefing generated yet."
    if briefing_row:
        try:
            bdata = json.loads(briefing_row["content"]) if isinstance(briefing_row["content"], str) else briefing_row["content"]
            briefing_text = bdata.get("summary", "") if isinstance(bdata, dict) else str(bdata)
        except Exception:
            briefing_text = str(briefing_row.get("content", ""))
    system = (
        f"You are an EdTech sales intelligence assistant analyzing procurement signals for "
        f"{account.get('name', 'this district')} (District domain: {account.get('district_domain', 'unknown')}).\n\n"
        f"TRACKED CONTACTS: {contact_list or 'None yet'}\n\n"
        f"RECENT DISTRICT SIGNALS ({len(signals)} total):\n"
        + ("\n".join(signal_lines) if signal_lines else "No signals collected yet. Suggest running a scan.")
        + f"\n\nBRIEFING SUMMARY:\n{briefing_text}\n\n"
        "Help the user understand, question, or refine this EdTech procurement intelligence. "
        "Be concise and sales-focused. Reference actual signal sources and contact names when relevant. "
        "Keep responses under 200 words unless asked for more. "
        "Format your responses with plain section headers (no # symbols, no asterisks), numbered or bulleted lists using hyphens. "
        "Never use markdown bold (**text**) or italic (*text*) — use plain text only."
    )
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=key)
    messages = [{"role": m["role"], "content": m["content"]} for m in req.history]
    messages.append({"role": "user", "content": req.message})
    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=600,
        system=system,
        messages=messages,
    )
    return {"response": response.content[0].text}

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "github_token": bool(os.getenv("GITHUB_TOKEN")),
        "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY"))
    }


# ─────────────────────────────────────────────────────────────────────────────
# RFP FINDER
# ─────────────────────────────────────────────────────────────────────────────

class DraftProposalRequest(BaseModel):
    vendor_name: str
    vendor_description: str

@app.get("/rfps")
async def list_rfps(account_id: Optional[int] = None):
    return await db.get_rfps(account_id)

@app.post("/accounts/{account_id}/rfps/scan")
async def scan_rfps(account_id: int, background_tasks: BackgroundTasks):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    background_tasks.add_task(_run_rfp_scan, account_id)
    return {"status": "scanning"}

async def _run_rfp_scan(account_id: int):
    try:
        added = await rfp_search.scan_rfps_for_account(account_id)
        print(f"[rfp_scan] Added {added} RFPs for account {account_id}")
    except Exception as e:
        print(f"[rfp_scan] Error: {e}")

@app.post("/rfps/{rfp_id}/draft")
async def draft_rfp_proposal(rfp_id: int, req: DraftProposalRequest):
    try:
        draft = await rfp_search.draft_proposal(rfp_id, req.vendor_name, req.vendor_description)
        return {"draft": draft}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/rfps/{rfp_id}")
async def delete_rfp(rfp_id: int):
    await db.delete_rfp(rfp_id)
    return {"deleted": rfp_id}


# ─────────────────────────────────────────────────────────────────────────────
# CONFERENCE INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/conferences")
async def list_conferences(upcoming: bool = True):
    confs = await db.get_conferences(upcoming_only=upcoming)
    if not confs:
        # Auto-seed on first call
        await conference_intel.seed_conferences()
        confs = await db.get_conferences(upcoming_only=upcoming)
    return confs

@app.post("/conferences/seed")
async def seed_conferences():
    count = await conference_intel.seed_conferences()
    return {"seeded": count}

@app.get("/conferences/relevance/{account_id}")
async def conferences_for_account(account_id: int):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    confs = await db.get_conferences(upcoming_only=True)
    if not confs:
        await conference_intel.seed_conferences()
        confs = await db.get_conferences(upcoming_only=True)
    scored = []
    for c in confs:
        c["relevance_score"] = conference_intel.score_conference_relevance(c, account)
        c["days_until"] = conference_intel.days_until(c.get("start_date"))
        scored.append(c)
    scored.sort(key=lambda x: (-x["relevance_score"], x.get("start_date") or ""))
    return scored


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC SPEND INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/accounts/{account_id}/spend")
async def get_spend(account_id: int):
    rows = await db.get_spend_intel(account_id)
    return rows

@app.post("/accounts/{account_id}/spend/scan")
async def scan_spend(account_id: int, background_tasks: BackgroundTasks):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    background_tasks.add_task(_run_spend_scan, account_id)
    return {"status": "scanning"}

async def _run_spend_scan(account_id: int):
    """Query USASpending.gov for grants/awards to this district."""
    import httpx
    account = await db.get_account(account_id)
    if not account:
        return
    name = account.get("district_legal_name") or account.get("name", "")
    if not name:
        return
    await db.clear_spend_intel(account_id)


# ─────────────────────────────────────────────────────────────────────────────
# TEXAS DISTRICT SCREENER
# ─────────────────────────────────────────────────────────────────────────────

# In-memory scan and report status for Texas screener
texas_scan_status: dict[int, dict]  = {}   # keyed by ESC region number
texas_report_status: dict[str, dict] = {}  # keyed by district_id
texas_client_report_status: dict[str, dict] = {}  # keyed by district_id


@app.get("/texas/regions")
async def list_texas_regions():
    """Returns the 20 ESC regions with names and cities."""
    return [
        {"region": region, **meta}
        for region, meta in texas_screener.ESC_REGIONS.items()
    ]


@app.get("/texas/districts")
async def list_texas_districts(region: int):
    """Returns all scanned districts for a given ESC region, scored and sorted."""
    districts = await db.get_texas_districts_by_region(region)
    return districts


@app.get("/texas/districts/{district_id}")
async def get_texas_district(district_id: str):
    district = await db.get_texas_district(district_id)
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    return district


@app.post("/texas/scan/{region}")
async def scan_texas_region(region: int, background_tasks: BackgroundTasks):
    if region not in texas_screener.ESC_REGIONS:
        raise HTTPException(status_code=400, detail=f"Invalid ESC region: {region}")
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    texas_scan_status[region] = {"status": "starting", "detail": "Initializing scan...", "progress": 0}

    async def _scan():
        async def _progress(status: str, detail: str):
            texas_scan_status[region] = {"status": status, "detail": detail}

        try:
            result = await texas_screener.scan_region(region, progress_cb=_progress)
            texas_scan_status[region] = {
                "status": "done",
                "detail": result.get("detail", f"Scanned {result['total']} districts"),
                "total": result["total"],
                "troubled": result["troubled"],
                "accounts_created": result["accounts_created"],
            }
        except Exception as e:
            texas_scan_status[region] = {"status": "error", "detail": str(e)}
            print(f"[TX scan] Region {region} error: {e}")

    background_tasks.add_task(_scan)
    return {"message": f"Scan started for ESC Region {region}"}


@app.get("/texas/scan/{region}/status")
async def get_texas_scan_status(region: int):
    return texas_scan_status.get(region, {"status": "idle"})


@app.post("/texas/districts/{district_id}/report/generate")
async def generate_texas_report(district_id: str, background_tasks: BackgroundTasks):
    district = await db.get_texas_district(district_id)
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    texas_report_status[district_id] = {"status": "generating", "detail": "Claude is writing your pitch..."}

    async def _generate():
        try:
            pitch = await texas_screener.generate_babbage_pitch(district)
            await db.update_texas_district_pitch(district_id, json.dumps(pitch))
            texas_report_status[district_id] = {"status": "done"}
        except Exception as e:
            texas_report_status[district_id] = {"status": "error", "detail": str(e)}
            print(f"[TX report] District {district_id} error: {e}")

    background_tasks.add_task(_generate)
    return {"message": "Report generation started"}


@app.get("/texas/districts/{district_id}/report/status")
async def get_texas_report_status(district_id: str):
    return texas_report_status.get(district_id, {"status": "idle"})


@app.post("/texas/districts/{district_id}/client-report/generate")
async def generate_texas_client_report(district_id: str, background_tasks: BackgroundTasks):
    district = await db.get_texas_district(district_id)
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    texas_client_report_status[district_id] = {"status": "generating", "detail": "Claude is writing your client proposal..."}

    async def _generate():
        try:
            report = await texas_screener.generate_client_report(district)
            await db.update_texas_district_client_report(district_id, json.dumps(report))
            texas_client_report_status[district_id] = {"status": "done"}
        except Exception as e:
            texas_client_report_status[district_id] = {"status": "error", "detail": str(e)}
            print(f"[TX client report] District {district_id} error: {e}")

    background_tasks.add_task(_generate)
    return {"message": "Client report generation started"}


@app.get("/texas/districts/{district_id}/client-report/status")
async def get_texas_client_report_status(district_id: str):
    return texas_client_report_status.get(district_id, {"status": "idle"})


@app.post("/texas/districts/{district_id}/pipeline")
async def add_texas_district_to_pipeline(district_id: str):
    district = await db.get_texas_district(district_id)
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    if district.get("account_id"):
        return {"account_id": district["account_id"], "created": False}
    account_id = await db.create_account(
        name=district["district_name"],
        district_domain=None,
        account_type="prospect",
        nces_id=district_id,
        district_legal_name=district["district_name"],
    )
    await db.link_texas_district_account(district_id, account_id)
    return {"account_id": account_id, "created": True}


    try:
        payload = {
            "filters": {
                "recipient_search_text": [name],
                "award_type_codes": ["02", "03", "04", "05", "A", "B", "C", "D"],
                "time_period": [{"start_date": "2020-01-01", "end_date": "2026-12-31"}],
            },
            "fields": ["Recipient Name", "Award Amount", "Award Type",
                       "Awarding Agency", "CFDA Number", "CFDA Title",
                       "Period of Performance Start Date"],
            "page": 1, "limit": 50, "sort": "Award Amount", "order": "desc",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                "https://api.usaspending.gov/api/v2/search/spending_by_award/",
                json=payload,
            )
            if r.status_code == 200:
                data = r.json()
                for award in (data.get("results") or []):
                    raw = award.get("generated_internal_id") and award
                    amount = award.get("Award Amount") or 0
                    try:
                        amount = int(float(str(amount).replace(",", "")))
                    except Exception:
                        amount = 0
                    start = (award.get("Period of Performance Start Date") or "")[:4]
                    year = int(start) if start.isdigit() else 0
                    await db.save_spend_award(
                        account_id=account_id,
                        vendor=award.get("Awarding Agency", "Unknown Agency"),
                        amount=amount,
                        year=year,
                        program=award.get("CFDA Title", ""),
                        cfda=award.get("CFDA Number", ""),
                        award_type=award.get("Award Type", ""),
                        data_source="usaspending",
                    )
        print(f"[spend_scan] Done for account {account_id}")
    except Exception as e:
        print(f"[spend_scan] Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# CONTACT ENRICHMENT
# ─────────────────────────────────────────────────────────────────────────────

class EnrichContactRequest(BaseModel):
    hint: Optional[str] = None  # any extra context (LinkedIn URL, company, etc.)

@app.post("/contacts/{contact_id}/enrich")
async def enrich_contact(contact_id: int, req: EnrichContactRequest):
    """Use Claude to suggest enrichment for a contact based on their name/role/district."""
    import os
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    async with __import__("aiosqlite").connect(db.DB_PATH) as conn:
        conn.row_factory = __import__("aiosqlite").Row
        async with conn.execute(
            "SELECT c.*, a.name as account_name, a.district_domain, a.district_legal_name "
            "FROM contacts c JOIN accounts a ON a.id=c.account_id WHERE c.id=?",
            (contact_id,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Contact not found")
    contact = dict(row)

    prompt = f"""Contact:
Name: {contact.get('name', 'Unknown')}
Role: {contact.get('role', 'Unknown')}
District: {contact.get('account_name', '')} ({contact.get('district_domain', '')})
{f"Hint: {req.hint}" if req.hint else ""}

Based on this person's name, role, and district, suggest:
1. Their likely LinkedIn URL format (e.g. linkedin.com/in/firstname-lastname-districtabbrev)
2. Likely email format (most districts use firstname.lastname@domain.org or flastname@domain.org)
3. 2-3 key talking points for an EdTech vendor reaching out to them
4. Best time of year to reach out (avoid testing periods, budget freeze, etc.)

Keep the response concise and structured."""

    message = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"suggestions": message.content[0].text, "contact": contact}

