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

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#1A2158',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, name)
);

CREATE TABLE IF NOT EXISTS signal_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER REFERENCES signals(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL,
    theme TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(signal_id, theme)
);

CREATE TABLE IF NOT EXISTS reports (
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
    # Migrate: create new tables and add columns if they don't exist yet
    for sql in [
        """CREATE TABLE IF NOT EXISTS signal_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER REFERENCES signals(id) ON DELETE CASCADE,
            account_id INTEGER NOT NULL,
            theme TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(signal_id, theme)
        )""",
        """CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
            content TEXT,
            generated_at TEXT DEFAULT (datetime('now'))
        )""",
        "ALTER TABLE engineers ADD COLUMN team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL",
        "ALTER TABLE engineers ADD COLUMN company TEXT",
        "ALTER TABLE accounts ADD COLUMN ticker_symbol TEXT",
        "ALTER TABLE accounts ADD COLUMN news_name TEXT",
        "ALTER TABLE accounts ADD COLUMN avatar_url TEXT",
    ]:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(sql)
                await db.commit()
        except Exception:
            pass  # column already exists

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

async def create_account(name: str, github_org: str, account_type: str, engineers: list[str],
                         ticker_symbol: str = None, news_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO accounts (name, github_org, account_type, ticker_symbol, news_name) VALUES (?, ?, ?, ?, ?)",
            (name, github_org, account_type, ticker_symbol or None, news_name or None)
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

async def update_account(account_id: int, name: str = None, github_org: str = None, account_type: str = None,
                         ticker_symbol: str = None, news_name: str = None):
    updates, values = [], []
    if name is not None:
        updates.append("name = ?")
        values.append(name)
    if github_org is not None:
        updates.append("github_org = ?")
        values.append(github_org)
    if account_type is not None:
        updates.append("account_type = ?")
        values.append(account_type)
    if ticker_symbol is not None:
        updates.append("ticker_symbol = ?")
        values.append(ticker_symbol or None)
    if news_name is not None:
        updates.append("news_name = ?")
        values.append(news_name or None)
    if not updates:
        return await get_account(account_id)
    values.append(account_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", values)
        await db.commit()
    return await get_account(account_id)

async def get_engineers(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM engineers WHERE account_id = ?", (account_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def upsert_engineer(account_id: int, username: str, display_name: str = None, avatar_url: str = None, company: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO engineers (account_id, github_username, display_name, avatar_url, company)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(account_id, github_username)
            DO UPDATE SET display_name = excluded.display_name, avatar_url = excluded.avatar_url,
                          company = COALESCE(excluded.company, engineers.company)
        """, (account_id, username, display_name, avatar_url, company))
        await db.commit()

async def get_signals(account_id: int, limit: int = 500, per_engineer: int = 40):
    """Return signals evenly distributed across all engineers, ordered by sig_score descending.

    Uses a window function to cap at `per_engineer` signals per engineer (most recent
    events per person), then re-sorts the full pool by quality score so the briefing
    and feed always reflect the entire team rather than whoever was synced last.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            WITH ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY engineer_username
                           ORDER BY detected_at DESC
                       ) AS _rn,
                       COALESCE(
                           CAST(json_extract(raw_data, '$.sig_score') AS INTEGER), 0
                       ) AS _score
                FROM signals
                WHERE account_id = ?
            )
            SELECT * FROM ranked
            WHERE _rn <= ?
            ORDER BY _score DESC, detected_at DESC
            LIMIT ?
        """, (account_id, per_engineer, limit)) as cursor:
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

async def get_hot_signals(limit: int = 10) -> list:
    """Returns the top signals by sig_score across all accounts, with account name attached."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT s.*,
                   a.name AS account_name,
                   COALESCE(
                       CAST(json_extract(s.raw_data, '$.sig_score') AS INTEGER), 0
                   ) AS _score
            FROM signals s
            JOIN accounts a ON a.id = s.account_id
            ORDER BY _score DESC, s.detected_at DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d.pop('_score', None)
                if d.get('repo_topics'):
                    try:
                        d['repo_topics'] = json.loads(d['repo_topics'])
                    except:
                        d['repo_topics'] = []
                else:
                    d['repo_topics'] = []
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

async def update_account_meta(account_id: int, score: int, avatar_url: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if avatar_url:
            await db.execute("""
                UPDATE accounts SET signal_score = ?, last_synced = datetime('now'), avatar_url = ?
                WHERE id = ?
            """, (score, avatar_url, account_id))
        else:
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

# ── Teams ─────────────────────────────────────────────────────────────────────
async def get_teams(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM teams WHERE account_id = ? ORDER BY name", (account_id,)) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

async def create_team(account_id: int, name: str, color: str = '#1A2158'):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO teams (account_id, name, color) VALUES (?, ?, ?)",
            (account_id, name, color)
        )
        team_id = cursor.lastrowid
        await db.commit()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM teams WHERE id = ?", (team_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_team(team_id: int, name: str = None, color: str = None):
    updates, values = [], []
    if name is not None:
        updates.append("name = ?")
        values.append(name)
    if color is not None:
        updates.append("color = ?")
        values.append(color)
    if not updates:
        return
    values.append(team_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE teams SET {', '.join(updates)} WHERE id = ?", values)
        await db.commit()

async def delete_team(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        await db.commit()

async def assign_engineer_team(engineer_id: int, team_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE engineers SET team_id = ? WHERE id = ?", (team_id, engineer_id))
        await db.commit()

# ── Signal Tags ────────────────────────────────────────────────────────────────
async def tag_signal(signal_id: int, account_id: int, theme: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO signal_tags (signal_id, account_id, theme) VALUES (?, ?, ?)",
            (signal_id, account_id, theme)
        )
        await db.commit()

async def untag_signal(signal_id: int, theme: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM signal_tags WHERE signal_id = ? AND theme = ?",
            (signal_id, theme)
        )
        await db.commit()

async def get_signal_tags_map(account_id: int) -> dict:
    """Returns {signal_id: [theme, ...]} for all tagged signals in an account."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT signal_id, theme FROM signal_tags WHERE account_id = ? ORDER BY created_at",
            (account_id,)
        ) as cursor:
            rows = await cursor.fetchall()
    result: dict = {}
    for row in rows:
        sid = row["signal_id"]
        if sid not in result:
            result[sid] = []
        result[sid].append(row["theme"])
    return result

async def get_tagged_signals(account_id: int) -> list:
    """Returns signals that have at least one tag, with a 'themes' list attached."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT s.*, group_concat(st.theme) AS themes_csv
            FROM signals s
            JOIN signal_tags st ON st.signal_id = s.id
            WHERE s.account_id = ?
            GROUP BY s.id
            ORDER BY s.detected_at DESC
        """, (account_id,)) as cursor:
            rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["themes"] = d.pop("themes_csv", "").split(",") if d.get("themes_csv") else []
        if d.get("repo_topics"):
            try:
                d["repo_topics"] = json.loads(d["repo_topics"])
            except Exception:
                d["repo_topics"] = []
        else:
            d["repo_topics"] = []
        if d.get("raw_data"):
            try:
                d["raw_data"] = json.loads(d["raw_data"])
            except Exception:
                pass
        result.append(d)
    return result

# ── Reports ────────────────────────────────────────────────────────────────────
async def save_report(account_id: int, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reports (account_id, content) VALUES (?, ?)",
            (account_id, content)
        )
        await db.commit()

async def get_latest_report(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM reports WHERE account_id = ? ORDER BY generated_at DESC LIMIT 1",
            (account_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
