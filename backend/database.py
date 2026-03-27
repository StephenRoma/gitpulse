import aiosqlite
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "gitpulse.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    github_org TEXT,
    account_type TEXT DEFAULT 'prospect',
    last_synced TEXT,
    signal_score INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS engineers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    github_username TEXT NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    UNIQUE(account_id, github_username)
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    engineer_username TEXT,
    signal_type TEXT,
    repo_name TEXT,
    repo_url TEXT,
    repo_description TEXT,
    repo_language TEXT,
    repo_topics TEXT,
    detected_at TEXT DEFAULT (datetime('now')),
    raw_data TEXT
);

CREATE TABLE IF NOT EXISTS briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    content TEXT,
    generated_at TEXT DEFAULT (datetime('now'))
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def get_accounts():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.*, 
                   COUNT(DISTINCT e.id) as engineer_count,
                   COUNT(DISTINCT s.id) as signal_count
            FROM accounts a
            LEFT JOIN engineers e ON e.account_id = a.id
            LEFT JOIN signals s ON s.account_id = a.id
            GROUP BY a.id
            ORDER BY a.signal_score DESC, a.name
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_account(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def create_account(name: str, github_org: str, account_type: str, engineers: list[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO accounts (name, github_org, account_type) VALUES (?, ?, ?)",
            (name, github_org, account_type)
        )
        account_id = cursor.lastrowid
        for username in engineers:
            username = username.strip()
            if username:
                await db.execute(
                    "INSERT OR IGNORE INTO engineers (account_id, github_username) VALUES (?, ?)",
                    (account_id, username)
                )
        await db.commit()
        return account_id

async def delete_account(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        await db.commit()

async def get_engineers(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM engineers WHERE account_id = ?", (account_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def upsert_engineer(account_id: int, username: str, display_name: str = None, avatar_url: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO engineers (account_id, github_username, display_name, avatar_url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(account_id, github_username)
            DO UPDATE SET display_name = excluded.display_name, avatar_url = excluded.avatar_url
        """, (account_id, username, display_name, avatar_url))
        await db.commit()

async def get_signals(account_id: int, limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM signals
            WHERE account_id = ?
            ORDER BY detected_at DESC
            LIMIT ?
        """, (account_id, limit)) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if d.get("repo_topics"):
                    try:
                        d["repo_topics"] = json.loads(d["repo_topics"])
                    except:
                        d["repo_topics"] = []
                else:
                    d["repo_topics"] = []
                result.append(d)
            return result

async def save_signal(account_id: int, engineer_username: str, signal_type: str,
                      repo_name: str, repo_url: str, repo_description: str,
                      repo_language: str, repo_topics: list, raw_data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO signals 
            (account_id, engineer_username, signal_type, repo_name, repo_url,
             repo_description, repo_language, repo_topics, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account_id, engineer_username, signal_type,
            repo_name, repo_url, repo_description, repo_language,
            json.dumps(repo_topics), json.dumps(raw_data)
        ))
        await db.commit()

async def clear_signals(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM signals WHERE account_id = ?", (account_id,))
        await db.commit()

async def get_latest_briefing(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM briefings WHERE account_id = ?
            ORDER BY generated_at DESC LIMIT 1
        """, (account_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def save_briefing(account_id: int, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO briefings (account_id, content) VALUES (?, ?)",
            (account_id, content)
        )
        await db.commit()

async def update_account_meta(account_id: int, score: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE accounts SET signal_score = ?, last_synced = datetime('now')
            WHERE id = ?
        """, (score, account_id))
        await db.commit()

async def add_engineer_to_account(account_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO engineers (account_id, github_username) VALUES (?, ?)",
            (account_id, username.strip())
        )
        await db.commit()

async def remove_engineer(engineer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM engineers WHERE id = ?", (engineer_id,))
        await db.commit()
