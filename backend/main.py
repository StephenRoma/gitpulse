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

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield

app = FastAPI(title="GitPulse API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory sync status ────────────────────────────────────────────────────
sync_status: dict[int, dict] = {}

def set_syncing(account_id: int, status: str, detail: str = ""):
    sync_status[account_id] = {"status": status, "detail": detail}

# ── Pydantic models ──────────────────────────────────────────────────────────
class CreateAccountRequest(BaseModel):
    name: str
    github_org: Optional[str] = ""
    account_type: str = "prospect"
    engineers: list[str] = []

class AddEngineerRequest(BaseModel):
    username: str

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

class UpdateAccountRequest(BaseModel):
    name: Optional[str] = None
    github_org: Optional[str] = None
    account_type: Optional[str] = None

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

# ── Accounts ─────────────────────────────────────────────────────────────────
@app.get("/accounts")
async def list_accounts():
    return await db.get_accounts()

@app.post("/accounts")
async def create_account(req: CreateAccountRequest):
    account_id = await db.create_account(
        name=req.name,
        github_org=req.github_org,
        account_type=req.account_type,
        engineers=req.engineers
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
        account_id, name=req.name, github_org=req.github_org, account_type=req.account_type
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

# ── Engineers ─────────────────────────────────────────────────────────────────
@app.get("/accounts/{account_id}/engineers")
async def get_engineers(account_id: int):
    return await db.get_engineers(account_id)

@app.post("/accounts/{account_id}/engineers")
async def add_engineer(account_id: int, req: AddEngineerRequest):
    await db.add_engineer_to_account(account_id, req.username)
    engineers = await db.get_engineers(account_id)
    match = next((e for e in engineers if e["github_username"] == req.username), None)
    return match or {"github_username": req.username}

@app.delete("/engineers/{engineer_id}")
async def remove_engineer(engineer_id: int):
    await db.remove_engineer(engineer_id)
    return {"message": "Engineer removed"}

@app.patch("/engineers/{engineer_id}")
async def update_engineer(engineer_id: int, req: AssignTeamRequest):
    await db.assign_engineer_team(engineer_id, req.team_id)
    return {"message": "Engineer updated"}

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
THEME_LABELS = {
    "modernization":   "Modernization",
    "cloud_migration": "Cloud Migration",
    "ai_adoption":     "AI / ML Adoption",
    "security":        "Security & Compliance",
    "platform_eng":    "Platform Engineering",
    "vendor_eval":     "Vendor Evaluation",
    "tech_debt":       "Tech Debt",
    "performance":     "Performance",
    "devex":           "Developer Experience",
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

@app.post("/accounts/{account_id}/report/generate")
async def generate_report(account_id: int):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    tagged_signals = await db.get_tagged_signals(account_id)
    if not tagged_signals:
        raise HTTPException(status_code=400, detail="No tagged signals. Tag signals in the feed first.")

    # Group signals by theme
    theme_groups: dict[str, list] = {}
    for sig in tagged_signals:
        for theme in sig.get("themes", []):
            if theme not in theme_groups:
                theme_groups[theme] = []
            theme_groups[theme].append(sig)

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
        theme_blocks.append(f"THEME: {label}\n" + "\n".join(lines))

    prompt = (
        f"You are writing a sales intelligence report for Relevantz about {account['name']}.\n"
        f"Account type: {account.get('account_type','prospect')} | Signal score: {account.get('signal_score',0)}/100\n\n"
        f"The sales team has tagged GitHub signals into strategic themes. "
        f"For each theme below, write a 2-3 sentence narrative that:\n"
        f"1. States what pattern the signals reveal\n"
        f"2. Explains the business implication or pain point\n"
        f"3. Suggests a specific Relevantz angle to open a conversation\n\n"
        + "\n\n".join(theme_blocks)
        + "\n\nReturn a JSON array (no markdown fences) with one object per theme:\n"
        "[{\"theme\": \"theme_key\", \"narrative\": \"...\"}]"
    )

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=key)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
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
            "github_org": account.get("github_org", ""),
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
        set_syncing(account_id, "syncing", "Collecting GitHub signals...")
        try:
            result = await ingester.ingest_account(account_id)
            set_syncing(account_id, "briefing", "Generating AI briefing...")
            await briefer.generate_briefing(account_id)
            set_syncing(account_id, "done", f"Synced {result['signals']} signals")
        except Exception as e:
            set_syncing(account_id, "error", str(e))
            print(f"Sync error for account {account_id}: {e}")

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

# ── Org member import ───────────────────────────────────────────────────────
@app.post("/accounts/{account_id}/import-org-members")
async def import_org_members(account_id: int):
    from github import Github, GithubException
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    org_name = account.get("github_org", "").strip()
    if not org_name:
        raise HTTPException(status_code=400, detail="Account has no GitHub org configured. Edit the account and set an org name.")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN not configured")
    try:
        g = Github(token)
        org = g.get_organization(org_name)
        # Scan top 20 most-recently-pushed public repos for contributors
        contributor_counts: dict[str, int] = {}
        repos = sorted(org.get_repos(type="public"), key=lambda r: r.pushed_at or r.created_at, reverse=True)[:20]
        for repo in repos:
            try:
                for contributor in repo.get_contributors():
                    login = contributor.login
                    contributor_counts[login] = contributor_counts.get(login, 0) + contributor.contributions
            except GithubException:
                continue  # some repos block contributor access
        # Also sweep org members in case they haven't committed to public repos
        try:
            for member in org.get_members():
                if member.login not in contributor_counts:
                    contributor_counts[member.login] = 0
        except GithubException:
            pass  # org member list may be hidden
        # Sort by total contributions descending, cap at 10
        logins = sorted(contributor_counts, key=lambda l: contributor_counts[l], reverse=True)[:10]
    except GithubException as e:
        msg = e.data.get("message", str(e)) if hasattr(e, "data") and isinstance(e.data, dict) else str(e)
        raise HTTPException(status_code=400, detail=f"GitHub error: {msg}")
    added = 0
    existing = {eng["github_username"] for eng in await db.get_engineers(account_id)}
    for login in logins:
        if login not in existing:
            await db.add_engineer_to_account(account_id, login)
            added += 1
            # Enrich company from GitHub profile
            try:
                user_obj = g.get_user(login)
                company_raw = user_obj.company or ''
                company = company_raw.lstrip('@').strip() or None
                if company:
                    await db.upsert_engineer(account_id, login, company=company)
            except Exception:
                pass
    # Suggest teams based on distinct company values not yet mapped to a team
    all_engineers = await db.get_engineers(account_id)
    existing_teams = {t['name'].lower() for t in await db.get_teams(account_id)}
    companies = set()
    for eng in all_engineers:
        c = eng.get('company')
        if c and c.lower() not in existing_teams:
            companies.add(c)
    skipped = len(logins) - added
    return {"added": added, "skipped": skipped, "total": len(logins), "suggested_teams": sorted(companies)}

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
    engineers = await db.get_engineers(account_id)
    briefing_row = await db.get_latest_briefing(account_id)
    signal_lines = []
    for s in signals[:100]:
        lang = s.get("repo_language", "") or ""
        desc = (s.get("repo_description", "") or "")[:80]
        signal_lines.append(f"- [{s['signal_type'].upper()}] {s.get('engineer_username','')} → {s['repo_name']} ({lang}): {desc}")
    eng_list = ", ".join(e["github_username"] for e in engineers[:20])
    briefing_text = "No briefing generated yet."
    if briefing_row:
        try:
            bdata = json.loads(briefing_row["content"]) if isinstance(briefing_row["content"], str) else briefing_row["content"]
            briefing_text = bdata.get("summary", "") if isinstance(bdata, dict) else str(bdata)
        except Exception:
            briefing_text = str(briefing_row.get("content", ""))
    system = (
        f"You are a sales intelligence assistant analyzing GitHub activity for "
        f"{account.get('name', 'this account')} (GitHub org: {account.get('github_org', 'unknown')}).\n\n"
        f"TRACKED ENGINEERS: {eng_list or 'None yet'}\n\n"
        f"RECENT GITHUB SIGNALS ({len(signals)} total):\n"
        + ("\n".join(signal_lines) if signal_lines else "No signals collected yet. Suggest running a sync.")
        + f"\n\nBRIEFING SUMMARY:\n{briefing_text}\n\n"
        "Help the user understand, question, or refine this intelligence. Be concise and sales-focused. "
        "Reference actual engineers and repos when relevant. Keep responses under 200 words unless asked for more. "
        "Format your responses with plain section headers (no # symbols, no asterisks), numbered or bulleted lists using hyphens. "
        "Never use markdown bold (**text**) or italic (*text*) — use plain text only."
    )
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=key)
    messages = [{"role": m["role"], "content": m["content"]} for m in req.history]
    messages.append({"role": "user", "content": req.message})
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
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
