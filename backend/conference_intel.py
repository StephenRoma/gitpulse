"""
conference_intel.py — EdTech conference intelligence for Quorum.

Maintains a curated list of major K-12 EdTech conferences and
enriches them with registration status, attendee estimates, and
relevance scoring for each account.
"""

import asyncio
import httpx
import feedparser
import database as db
from datetime import datetime, timezone

# ─── Curated conference calendar (updated annually) ───────────────────────────
EDTECH_CONFERENCES = [
    {
        "name": "ISTE (International Society for Technology in Education)",
        "start_date": "2026-06-28",
        "end_date":   "2026-07-01",
        "location":   "San Antonio Convention Center, San Antonio, TX",
        "city":       "San Antonio, TX",
        "url":        "https://conference.iste.org/",
        "theme_tags": ["edtech", "curriculum", "devices", "professional_dev", "ai"],
        "attendee_count": 18000,
        "is_virtual": False,
        "notes": "Largest K-12 edtech conference. Massive vendor floor. Demo pods and networking.",
    },
    {
        "name": "CoSN Annual Conference",
        "start_date": "2026-03-23",
        "end_date":   "2026-03-26",
        "location":   "Marriott Marquis, Washington, DC",
        "city":       "Washington, DC",
        "url":        "https://www.cosn.org/conference",
        "theme_tags": ["cto", "it_leaders", "cybersecurity", "infrastructure", "policy"],
        "attendee_count": 1200,
        "is_virtual": False,
        "notes": "Focused on K-12 CTO/IT leaders. Best event for infrastructure and security vendors.",
    },
    {
        "name": "FETC (Future of Education Technology Conference)",
        "start_date": "2027-01-13",
        "end_date":   "2027-01-16",
        "location":   "Orange County Convention Center, Orlando, FL",
        "city":       "Orlando, FL",
        "url":        "https://www.fetc.org/",
        "theme_tags": ["edtech", "curriculum", "professional_dev", "devices"],
        "attendee_count": 8000,
        "is_virtual": False,
        "notes": "Strong southeastern US district attendance. Good for curriculum and device vendors.",
    },
    {
        "name": "SXSWedu",
        "start_date": "2026-03-02",
        "end_date":   "2026-03-05",
        "location":   "Austin Convention Center, Austin, TX",
        "city":       "Austin, TX",
        "url":        "https://www.sxswedu.com/",
        "theme_tags": ["innovation", "startups", "policy", "equity", "ai"],
        "attendee_count": 5000,
        "is_virtual": False,
        "notes": "Innovation-forward. Good for early-stage companies and thought leadership.",
    },
    {
        "name": "ASU+GSV Summit",
        "start_date": "2026-04-06",
        "end_date":   "2026-04-08",
        "location":   "Manchester Grand Hyatt, San Diego, CA",
        "city":       "San Diego, CA",
        "url":        "https://www.asugsvsummit.com/",
        "theme_tags": ["investment", "startups", "higher_ed", "workforce", "ai"],
        "attendee_count": 7000,
        "is_virtual": False,
        "notes": "Crossover of K-12, higher ed, and edtech investors. Strong CEO/founder presence.",
    },
    {
        "name": "EdLeader21 National Summit",
        "start_date": "2026-10-14",
        "end_date":   "2026-10-16",
        "location":   "TBD",
        "city":       "TBD",
        "url":        "https://edleader21.com/national-summit",
        "theme_tags": ["21st_century_skills", "curriculum", "leadership"],
        "attendee_count": 600,
        "is_virtual": False,
        "notes": "Superintendents and curriculum directors. Smaller but high-quality district decision-makers.",
    },
    {
        "name": "NCCE Tech Conference",
        "start_date": "2026-02-18",
        "end_date":   "2026-02-21",
        "location":   "Washington State Convention Center, Seattle, WA",
        "city":       "Seattle, WA",
        "url":        "https://www.ncce.org/",
        "theme_tags": ["pacific_northwest", "curriculum", "professional_dev"],
        "attendee_count": 3000,
        "is_virtual": False,
        "notes": "Northwest-focused educators. Good for WA, OR, ID, AK districts.",
    },
    {
        "name": "TCEA Annual Convention",
        "start_date": "2026-02-02",
        "end_date":   "2026-02-06",
        "location":   "Austin Convention Center, Austin, TX",
        "city":       "Austin, TX",
        "url":        "https://www.tcea.org/convention",
        "theme_tags": ["texas", "curriculum", "professional_dev", "devices"],
        "attendee_count": 6000,
        "is_virtual": False,
        "notes": "Texas-focused. High attendance from TX districts. Key for vendors targeting TX.",
    },
    {
        "name": "Ed100 Virtual Summit",
        "start_date": "2026-08-10",
        "end_date":   "2026-08-11",
        "location":   "Virtual",
        "city":       "Virtual",
        "url":        "https://ed100.org/summit",
        "theme_tags": ["equity", "california", "policy", "parent_engagement"],
        "attendee_count": 2000,
        "is_virtual": True,
        "notes": "California-focused virtual event. Policy and equity themes.",
    },
    {
        "name": "iNACOL Symposium (Aurora Institute)",
        "start_date": "2026-10-19",
        "end_date":   "2026-10-22",
        "location":   "Gaylord Opryland Resort, Nashville, TN",
        "city":       "Nashville, TN",
        "url":        "https://aurora-institute.org/event/symposium/",
        "theme_tags": ["competency_based", "personalized_learning", "policy"],
        "attendee_count": 1800,
        "is_virtual": False,
        "notes": "Focused on competency-based and personalized learning. Policy-forward districts.",
    },
    {
        "name": "EdTech Week NYC",
        "start_date": "2026-05-11",
        "end_date":   "2026-05-14",
        "location":   "New York, NY",
        "city":       "New York, NY",
        "url":        "https://edtechweeknyc.com/",
        "theme_tags": ["startups", "investment", "urban_districts", "ai", "nyc"],
        "attendee_count": 3500,
        "is_virtual": False,
        "notes": "Growing NYC-area event. Strong investor + district attendance.",
    },
    {
        "name": "CUE Annual Conference",
        "start_date": "2026-03-19",
        "end_date":   "2026-03-22",
        "location":   "Palm Springs Convention Center, Palm Springs, CA",
        "city":       "Palm Springs, CA",
        "url":        "https://www.cue.org/annual",
        "theme_tags": ["california", "curriculum", "professional_dev", "devices"],
        "attendee_count": 5000,
        "is_virtual": False,
        "notes": "California-centric. Strong CA district educator attendance.",
    },
]


async def seed_conferences():
    """Write the curated conference list into the database."""
    count = 0
    for conf in EDTECH_CONFERENCES:
        await db.upsert_conference(
            name=conf["name"],
            start_date=conf["start_date"],
            end_date=conf["end_date"],
            location=conf["location"],
            city=conf["city"],
            url=conf["url"],
            theme_tags=conf["theme_tags"],
            attendee_count=conf["attendee_count"],
            is_virtual=conf["is_virtual"],
            notes=conf["notes"],
        )
        count += 1
    return count


def days_until(date_str: str) -> int | None:
    if not date_str:
        return None
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        delta = target - datetime.now(timezone.utc)
        return delta.days
    except Exception:
        return None


def score_conference_relevance(conf: dict, account: dict) -> int:
    """
    Score 0-100 how relevant a conference is for a given account.
    Higher = more important to attend for this account.
    """
    score = 50  # base
    domain = account.get("district_domain", "").lower()
    tags = conf.get("theme_tags", [])

    # Near-term conferences get a boost
    d = days_until(conf.get("start_date"))
    if d is not None:
        if 14 <= d <= 60:
            score += 20  # happening soon
        elif 60 < d <= 120:
            score += 10

    # Large conferences are generally more valuable
    attn = conf.get("attendee_count", 0)
    if attn >= 10000:
        score += 15
    elif attn >= 5000:
        score += 8

    # State/region matching
    state_tags = {"texas": "tx", "california": "ca", "florida": "fl",
                  "pacific_northwest": "wa", "nyc": "ny"}
    for tag, state_abbr in state_tags.items():
        if tag in tags and f".{state_abbr}." in domain:
            score += 20

    # Tag alignment bonuses
    if "cto" in tags or "it_leaders" in tags or "cybersecurity" in tags:
        # Good for IT/infrastructure vendors
        score += 5
    if "ai" in tags:
        score += 10  # AI is hot right now
    if conf.get("is_virtual"):
        score -= 10  # virtual conferences are less valuable for networking

    return min(100, max(0, score))
