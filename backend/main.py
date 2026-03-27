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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
    return {"message": f"Engineer {req.username} added"}

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

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "github_token": bool(os.getenv("GITHUB_TOKEN")),
        "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY"))
    }
