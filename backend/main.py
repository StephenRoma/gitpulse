import os
import json
import asyncio
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

# ── Signals ───────────────────────────────────────────────────────────────────
@app.get("/accounts/{account_id}/signals")
async def get_signals(account_id: int, limit: int = 50):
    return await db.get_signals(account_id, limit)

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
    skipped = len(logins) - added
    return {"added": added, "skipped": skipped, "total": len(logins)}

# ── Chat ──────────────────────────────────────────────────────────────────────
@app.post("/accounts/{account_id}/chat")
async def chat_with_signals(account_id: int, req: ChatRequest):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    signals = await db.get_signals(account_id, limit=80)
    engineers = await db.get_engineers(account_id)
    briefing_row = await db.get_latest_briefing(account_id)
    signal_lines = []
    for s in signals[:60]:
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
