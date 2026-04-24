import aiosqlite
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).parent / "quorum.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    district_domain TEXT,
    nces_id TEXT,
    district_legal_name TEXT,
    avatar_url TEXT,
    account_type TEXT DEFAULT 'prospect',
    last_synced TEXT,
    signal_score INTEGER DEFAULT 0,
    total_enrollment INTEGER,
    title1_status TEXT,
    per_pupil_expenditure INTEGER,
    technology_spend INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    name TEXT,
    role TEXT,
    email TEXT,
    linkedin_url TEXT,
    phone TEXT,
    avatar_url TEXT,
    team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    UNIQUE(account_id, email)
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

CREATE TABLE IF NOT EXISTS outreach_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    content TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rfps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    agency TEXT,
    posted_date TEXT,
    due_date TEXT,
    url TEXT,
    estimated_value INTEGER,
    description TEXT,
    naics_code TEXT,
    source TEXT,
    status TEXT DEFAULT 'open',
    proposal_draft TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, url)
);

CREATE TABLE IF NOT EXISTS conferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    location TEXT,
    city TEXT,
    url TEXT,
    theme_tags TEXT,
    attendee_count INTEGER,
    is_virtual INTEGER DEFAULT 0,
    registration_open INTEGER DEFAULT 1,
    notes TEXT,
    UNIQUE(name, start_date)
);

CREATE TABLE IF NOT EXISTS spend_intel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    vendor TEXT,
    amount INTEGER,
    year INTEGER,
    program TEXT,
    cfda TEXT,
    award_type TEXT,
    data_source TEXT DEFAULT 'usaspending',
    retrieved_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS texas_districts (
    district_id TEXT PRIMARY KEY,
    district_name TEXT NOT NULL,
    esc_region INTEGER,
    enrollment INTEGER,
    accountability_rating TEXT,
    staar_reading_pct REAL,
    staar_math_pct REAL,
    staar_sped_reading_pct REAL,
    staar_sped_math_pct REAL,
    grad_rate REAL,
    teacher_turnover_pct REAL,
    sped_student_pct REAL,
    chronic_absent_pct REAL,
    trouble_score INTEGER DEFAULT 0,
    trouble_flags TEXT DEFAULT '[]',
    babbage_pitch TEXT,
    last_fetched TEXT,
    account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    # Migrations for any pre-existing quorum.db
    for sql in [
        "ALTER TABLE accounts ADD COLUMN district_domain TEXT",
        "ALTER TABLE accounts ADD COLUMN nces_id TEXT",
        "ALTER TABLE accounts ADD COLUMN district_legal_name TEXT",
        "ALTER TABLE accounts ADD COLUMN avatar_url TEXT",
        "ALTER TABLE accounts ADD COLUMN total_enrollment INTEGER",
        "ALTER TABLE accounts ADD COLUMN title1_status TEXT",
        "ALTER TABLE accounts ADD COLUMN per_pupil_expenditure INTEGER",
        "ALTER TABLE accounts ADD COLUMN technology_spend INTEGER",
        "ALTER TABLE rfps ADD COLUMN proposal_draft TEXT",
        "ALTER TABLE texas_districts ADD COLUMN client_report TEXT",
    ]:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(sql)
                await db.commit()
        except Exception:
            pass  # column already exists

    # Ensure texas_districts table exists for pre-existing databases
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS texas_districts (
                    district_id TEXT PRIMARY KEY,
                    district_name TEXT NOT NULL,
                    esc_region INTEGER,
                    enrollment INTEGER,
                    accountability_rating TEXT,
                    staar_reading_pct REAL,
                    staar_math_pct REAL,
                    staar_sped_reading_pct REAL,
                    staar_sped_math_pct REAL,
                    grad_rate REAL,
                    teacher_turnover_pct REAL,
                    sped_student_pct REAL,
                    chronic_absent_pct REAL,
                    trouble_score INTEGER DEFAULT 0,
                    trouble_flags TEXT DEFAULT '[]',
                    babbage_pitch TEXT,
                    last_fetched TEXT,
                    account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL
                )
            """)
            await db.commit()
    except Exception:
        pass


async def get_accounts():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.*,
                   COUNT(DISTINCT c.id) as contact_count,
                   COUNT(DISTINCT s.id) as signal_count
            FROM accounts a
            LEFT JOIN contacts c ON c.account_id = a.id
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

async def create_account(name: str, district_domain: str = None, account_type: str = "prospect",
                         nces_id: str = None, district_legal_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO accounts (name, district_domain, account_type, nces_id, district_legal_name)
               VALUES (?, ?, ?, ?, ?)""",
            (name, district_domain or None, account_type, nces_id or None, district_legal_name or None)
        )
        account_id = cursor.lastrowid
        await db.commit()
        return account_id

async def delete_account(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        await db.commit()

async def update_account(account_id: int, name: str = None, district_domain: str = None,
                         account_type: str = None, nces_id: str = None,
                         district_legal_name: str = None):
    updates, values = [], []
    if name is not None:
        updates.append("name = ?"); values.append(name)
    if district_domain is not None:
        updates.append("district_domain = ?"); values.append(district_domain or None)
    if account_type is not None:
        updates.append("account_type = ?"); values.append(account_type)
    if nces_id is not None:
        updates.append("nces_id = ?"); values.append(nces_id or None)
    if district_legal_name is not None:
        updates.append("district_legal_name = ?"); values.append(district_legal_name or None)
    if not updates:
        return await get_account(account_id)
    values.append(account_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", values)
        await db.commit()
    return await get_account(account_id)


async def update_account_essa(account_id: int, total_enrollment: int = None,
                               title1_status: str = None, per_pupil_expenditure: int = None,
                               technology_spend: int = None):
    updates, values = [], []
    if total_enrollment is not None:
        updates.append("total_enrollment = ?"); values.append(total_enrollment)
    if title1_status is not None:
        updates.append("title1_status = ?"); values.append(title1_status)
    if per_pupil_expenditure is not None:
        updates.append("per_pupil_expenditure = ?"); values.append(per_pupil_expenditure)
    if technology_spend is not None:
        updates.append("technology_spend = ?"); values.append(technology_spend)
    if not updates:
        return
    values.append(account_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", values)
        await db.commit()


# ── Contacts ──────────────────────────────────────────────────────────────────

async def get_contacts(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM contacts WHERE account_id = ? ORDER BY role, name", (account_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def add_contact(account_id: int, name: str = None, role: str = None,
                      email: str = None, linkedin_url: str = None, phone: str = None,
                      avatar_url: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT OR IGNORE INTO contacts
               (account_id, name, role, email, linkedin_url, phone, avatar_url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (account_id, name, role, email or None, linkedin_url or None, phone or None, avatar_url or None)
        )
        await db.commit()
        return cursor.lastrowid


async def remove_contact(contact_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        await db.commit()


async def assign_contact_team(contact_id: int, team_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE contacts SET team_id = ? WHERE id = ?", (team_id, contact_id))
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
    """Kept for backward compat; adds a contact with no email."""
    await add_contact(account_id, name=username, role="Contact")


async def remove_engineer(engineer_id: int):
    await remove_contact(engineer_id)


# ── Teams (Schools) ───────────────────────────────────────────────────────────
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
    await assign_contact_team(engineer_id, team_id)


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

# ── RFPs ──────────────────────────────────────────────────────────────────────
async def save_rfp(account_id: int, title: str, agency: str, posted_date: str,
                   due_date: str, url: str, estimated_value: int,
                   description: str, naics_code: str, source: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT OR IGNORE INTO rfps
              (account_id, title, agency, posted_date, due_date, url,
               estimated_value, description, naics_code, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (account_id, title, agency, posted_date, due_date, url,
              estimated_value, description, naics_code, source))
        await db.commit()
        return cursor.lastrowid or 0

async def get_rfps(account_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if account_id:
            async with db.execute(
                "SELECT * FROM rfps WHERE account_id = ? ORDER BY posted_date DESC, created_at DESC",
                (account_id,)
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]
        async with db.execute(
            "SELECT r.*, a.name as account_name, a.district_domain FROM rfps r "
            "JOIN accounts a ON a.id = r.account_id ORDER BY posted_date DESC, r.created_at DESC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def save_rfp_draft(rfp_id: int, draft: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE rfps SET proposal_draft = ? WHERE id = ?", (draft, rfp_id))
        await db.commit()

async def get_rfp(rfp_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM rfps WHERE id = ?", (rfp_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def delete_rfp(rfp_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM rfps WHERE id = ?", (rfp_id,))
        await db.commit()

# ── Conferences ───────────────────────────────────────────────────────────────
async def upsert_conference(name: str, start_date: str, end_date: str,
                             location: str, city: str, url: str,
                             theme_tags: list, attendee_count: int,
                             is_virtual: bool, notes: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO conferences
              (name, start_date, end_date, location, city, url,
               theme_tags, attendee_count, is_virtual, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name, start_date) DO UPDATE SET
              end_date=excluded.end_date, location=excluded.location,
              city=excluded.city, url=excluded.url,
              theme_tags=excluded.theme_tags, attendee_count=excluded.attendee_count,
              is_virtual=excluded.is_virtual, notes=excluded.notes
        """, (name, start_date, end_date, location, city, url,
              json.dumps(theme_tags), attendee_count, int(is_virtual), notes))
        await db.commit()
        return cursor.lastrowid or 0

async def get_conferences(upcoming_only: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if upcoming_only:
            async with db.execute(
                "SELECT * FROM conferences WHERE start_date >= date('now') ORDER BY start_date",
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM conferences ORDER BY start_date DESC"
            ) as cur:
                rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["theme_tags"] = json.loads(d.get("theme_tags") or "[]")
        except Exception:
            d["theme_tags"] = []
        result.append(d)
    return result

# ── Spend Intelligence ─────────────────────────────────────────────────────────
async def save_spend_award(account_id: int, vendor: str, amount: int,
                            year: int, program: str, cfda: str,
                            award_type: str, data_source: str = "usaspending"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO spend_intel
              (account_id, vendor, amount, year, program, cfda, award_type, data_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (account_id, vendor, amount, year, program, cfda, award_type, data_source))
        await db.commit()

async def get_spend_intel(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM spend_intel WHERE account_id = ? ORDER BY year DESC, amount DESC",
            (account_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def clear_spend_intel(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM spend_intel WHERE account_id = ?", (account_id,))
        await db.commit()


# ── Texas Districts ───────────────────────────────────────────────────────────

async def upsert_texas_district(district_id: str, district_name: str, esc_region: int,
                                 enrollment: int = None, accountability_rating: str = None,
                                 staar_reading_pct: float = None, staar_math_pct: float = None,
                                 staar_sped_reading_pct: float = None, staar_sped_math_pct: float = None,
                                 grad_rate: float = None, teacher_turnover_pct: float = None,
                                 sped_student_pct: float = None, chronic_absent_pct: float = None,
                                 trouble_score: int = 0, trouble_flags: list = None):
    flags_json = json.dumps(trouble_flags or [])
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO texas_districts
                (district_id, district_name, esc_region, enrollment, accountability_rating,
                 staar_reading_pct, staar_math_pct, staar_sped_reading_pct, staar_sped_math_pct,
                 grad_rate, teacher_turnover_pct, sped_student_pct, chronic_absent_pct,
                 trouble_score, trouble_flags, last_fetched)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(district_id) DO UPDATE SET
                district_name=excluded.district_name,
                esc_region=excluded.esc_region,
                enrollment=excluded.enrollment,
                accountability_rating=excluded.accountability_rating,
                staar_reading_pct=excluded.staar_reading_pct,
                staar_math_pct=excluded.staar_math_pct,
                staar_sped_reading_pct=excluded.staar_sped_reading_pct,
                staar_sped_math_pct=excluded.staar_sped_math_pct,
                grad_rate=excluded.grad_rate,
                teacher_turnover_pct=excluded.teacher_turnover_pct,
                sped_student_pct=excluded.sped_student_pct,
                chronic_absent_pct=excluded.chronic_absent_pct,
                trouble_score=excluded.trouble_score,
                trouble_flags=excluded.trouble_flags,
                last_fetched=excluded.last_fetched
        """, (district_id, district_name, esc_region, enrollment, accountability_rating,
              staar_reading_pct, staar_math_pct, staar_sped_reading_pct, staar_sped_math_pct,
              grad_rate, teacher_turnover_pct, sped_student_pct, chronic_absent_pct,
              trouble_score, flags_json, now))
        await db.commit()


async def get_texas_districts_by_region(esc_region: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM texas_districts WHERE esc_region = ? ORDER BY trouble_score DESC, district_name",
            (esc_region,)
        ) as cur:
            rows = await cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["trouble_flags"] = json.loads(d["trouble_flags"] or "[]")
                except Exception:
                    d["trouble_flags"] = []
                if d.get("babbage_pitch"):
                    try:
                        d["babbage_pitch"] = json.loads(d["babbage_pitch"])
                    except Exception:
                        pass
                if d.get("client_report"):
                    try:
                        d["client_report"] = json.loads(d["client_report"])
                    except Exception:
                        pass
                result.append(d)
            return result


async def get_texas_district(district_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM texas_districts WHERE district_id = ?", (district_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["trouble_flags"] = json.loads(d["trouble_flags"] or "[]")
            except Exception:
                d["trouble_flags"] = []
            if d.get("babbage_pitch"):
                try:
                    d["babbage_pitch"] = json.loads(d["babbage_pitch"])
                except Exception:
                    pass
            if d.get("client_report"):
                try:
                    d["client_report"] = json.loads(d["client_report"])
                except Exception:
                    pass
            return d


async def update_texas_district_pitch(district_id: str, pitch_json: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE texas_districts SET babbage_pitch = ? WHERE district_id = ?",
            (pitch_json, district_id)
        )
        await db.commit()


async def update_texas_district_client_report(district_id: str, report_json: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE texas_districts SET client_report = ? WHERE district_id = ?",
            (report_json, district_id)
        )
        await db.commit()


async def link_texas_district_account(district_id: str, account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE texas_districts SET account_id = ? WHERE district_id = ?",
            (account_id, district_id)
        )
        await db.commit()

