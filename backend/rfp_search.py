"""
rfp_search.py — RFP discovery and AI proposal drafting for Quorum.

Sources:
  1. SAM.gov Opportunities API (federal, free with API key)
  2. Google News RSS for "{district} RFP" / "procurement"
  3. State e-procurement portals via RSS/scrape
"""

import asyncio
import os
import json
import httpx
import feedparser
import database as db
from anthropic import AsyncAnthropic
from datetime import datetime, timezone

_client = None

def _anthropic():
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _client

# EdTech NAICS codes and keywords that indicate edtech procurement
EDTECH_KEYWORDS = [
    "learning management system", "LMS", "student information system", "SIS",
    "edtech", "education technology", "chromebook", "ipad", "device",
    "broadband", "hotspot", "one-to-one", "1:1", "curriculum",
    "literacy platform", "math intervention", "ESSER", "E-Rate",
    "data analytics", "assessment platform", "tutoring", "professional development",
    "cybersecurity", "fiber", "wi-fi", "classroom technology"
]

# State e-procurement RSS feeds (publicly accessible)
STATE_EPROCUREMENT = {
    "ca": "https://caleprocure.ca.gov/rss/opportunities.xml",
    "tx": "https://www.txsmartbuy.gov/rss",
    "fl": "https://www.myfloridamarketplace.com/rss/solicitations.xml",
    "ny": "https://www.nysmarketplace.com/rss/opportunities",
    "wa": "https://fortress.wa.gov/ga/apps/osd/rss/solicitations.xml",
    "co": "https://www.solicitationresponses.com/rss",
    "ga": "https://ssl.doas.state.ga.us/GaPSRS/rss",
    "il": "https://www2.illinois.gov/cms/business/sell2/rss",
    "nc": "https://vendor.ncmalit.nc.gov/rss",
    "oh": "https://procure.ohio.gov/rss",
}


def _is_edtech_rfp(title: str, description: str) -> bool:
    text = (title + " " + (description or "")).lower()
    return any(kw.lower() in text for kw in EDTECH_KEYWORDS)


async def search_google_news_rfps(account) -> list[dict]:
    """Search Google News RSS for district RFP mentions."""
    domain = account.get("district_domain", "")
    name = account.get("name", account.get("district_legal_name", ""))
    queries = [
        f"{name} RFP bid proposal technology",
        f"{name} procurement information technology",
        f"{domain} technology solicitation",
        f"\"{name}\" \"request for proposal\"",
    ]
    results = []
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Quorum/1.0"}) as client:
        for q in queries:
            try:
                rss_url = f"https://news.google.com/rss/search?q={httpx.URL(q).params}&hl=en-US&gl=US&ceid=US:en"
                rss_url = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
                feed = feedparser.parse(rss_url)
                for entry in (feed.entries or [])[:5]:
                    title = getattr(entry, "title", "")
                    link  = getattr(entry, "link", "")
                    summary = getattr(entry, "summary", "")
                    pub    = getattr(entry, "published", "")
                    if not title or not link:
                        continue
                    rfp_kws = ["rfp", "bid", "solicitation", "proposal", "procurement", "request for"]
                    if not any(kw in (title + summary).lower() for kw in rfp_kws):
                        continue
                    results.append({
                        "title": title[:220],
                        "agency": name,
                        "posted_date": pub[:10] if pub else datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "due_date": None,
                        "url": link,
                        "estimated_value": 0,
                        "description": (summary or "")[:500],
                        "naics_code": "611710",
                        "source": "google_news",
                    })
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"[rfp_search] Google News error for '{q}': {e}")
    return results


async def search_sam_gov_rfps(account) -> list[dict]:
    """Search SAM.gov Opportunities API for EdTech RFPs."""
    api_key = os.environ.get("SAM_GOV_API_KEY", "")
    if not api_key:
        return []  # No key — skip SAM.gov

    name = account.get("name", "")
    state_code = ""
    domain = account.get("district_domain", "")
    # Try to infer state from domain (e.g. lausd.net → CA)
    state_map = {
        "ca": "CA", "tx": "TX", "fl": "FL", "ny": "NY", "wa": "WA",
        "il": "IL", "ga": "GA", "nc": "NC", "oh": "OH", "pa": "PA",
    }
    for abbr, code in state_map.items():
        if f".{abbr}." in domain or domain.endswith(f".{abbr}.us"):
            state_code = code
            break

    edtech_keywords = "education technology learning management system LMS chromebook"
    params = {
        "api_key": api_key,
        "keyword": edtech_keywords,
        "typeOfSetAside": "",
        "limit": 20,
        "offset": 0,
        "postedFrom": (datetime.now(timezone.utc).replace(month=1, day=1)).strftime("%m/%d/%Y"),
    }
    if state_code:
        params["state"] = state_code

    results = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.sam.gov/opportunities/v2/search",
                params=params
            )
            if r.status_code == 200:
                data = r.json()
                for opp in (data.get("opportunitiesData") or []):
                    title = opp.get("title", "")
                    desc  = opp.get("description", "")
                    if not _is_edtech_rfp(title, desc):
                        continue
                    results.append({
                        "title": title[:220],
                        "agency": opp.get("organizationName", "Federal Agency"),
                        "posted_date": (opp.get("postedDate") or "")[:10],
                        "due_date": (opp.get("responseDeadLine") or "")[:10],
                        "url": f"https://sam.gov/opp/{opp.get('noticeId', '')}/view",
                        "estimated_value": 0,
                        "description": desc[:500] if desc else "",
                        "naics_code": opp.get("naicsCode", "611710"),
                        "source": "sam_gov",
                    })
    except Exception as e:
        print(f"[rfp_search] SAM.gov error: {e}")
    return results


async def scan_rfps_for_account(account_id: int) -> int:
    """Run all RFP searches for an account, save new RFPs, return count added."""
    account = await db.get_account(account_id)
    if not account:
        return 0

    all_rfps: list[dict] = []
    news_rfps, sam_rfps = await asyncio.gather(
        search_google_news_rfps(account),
        search_sam_gov_rfps(account),
        return_exceptions=True,
    )
    if isinstance(news_rfps, list):
        all_rfps.extend(news_rfps)
    if isinstance(sam_rfps, list):
        all_rfps.extend(sam_rfps)

    added = 0
    for rfp in all_rfps:
        r = await db.save_rfp(
            account_id=account_id,
            title=rfp["title"],
            agency=rfp["agency"],
            posted_date=rfp.get("posted_date") or "",
            due_date=rfp.get("due_date") or "",
            url=rfp["url"],
            estimated_value=rfp.get("estimated_value", 0) or 0,
            description=rfp.get("description", "") or "",
            naics_code=rfp.get("naics_code", ""),
            source=rfp["source"],
        )
        if r:
            added += 1
    return added


PROPOSAL_SYSTEM = """You are an expert EdTech proposal writer specializing in K-12 procurement.
Write compelling, concise RFP responses for EdTech vendors responding to school district RFPs.

Structure the proposal with:
1. **Executive Summary** (2-3 sentences why we're the best fit)
2. **Understanding of Requirements** (what the district needs)
3. **Proposed Solution** (our platform/service and how it addresses each requirement)
4. **Why Us** (differentiators, references, track record)
5. **Implementation Timeline** (brief phased rollout)
6. **Pricing Approach** (mention per-pupil or site license but leave $ blank if unknown)
7. **Next Steps**

Keep it under 600 words. Use professional but readable language. Focus on student outcomes."""


async def draft_proposal(rfp_id: int, vendor_name: str, vendor_description: str) -> str:
    """Use Claude to draft a proposal response for an RFP."""
    rfp = await db.get_rfp(rfp_id)
    if not rfp:
        raise ValueError("RFP not found")

    prompt = f"""RFP Details:
Title: {rfp['title']}
Agency: {rfp['agency']}
Due Date: {rfp.get('due_date') or 'Not specified'}
Description: {rfp.get('description') or 'No description provided'}

Vendor:
Name: {vendor_name}
What we do: {vendor_description}

Write a proposal response for this RFP."""

    message = await _anthropic().messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1200,
        system=PROPOSAL_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    draft = message.content[0].text
    await db.save_rfp_draft(rfp_id, draft)
    return draft
