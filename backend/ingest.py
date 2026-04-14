import os
import asyncio
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote as urlquote
from dotenv import load_dotenv
import httpx
import feedparser
import database as db

load_dotenv()

LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "60"))

SIGNAL_WEIGHTS = {
    "board_minutes_item": 8,
    "essa_profile":       5,
    "state_initiative":   5,
    "job_posting":        7,
    "news_mention":       4,
    "press_release":      6,
}

# ─── Certainty mapping ────────────────────────────────────────────────────────

def _certainty_for(signal_type: str, sub_type: str = "") -> str:
    if signal_type == "board_minutes_item":
        if sub_type in ("budget_approval", "rfp"):
            return "confirmed"
        if sub_type in ("strategic_initiative", "tech_initiative"):
            return "active"
        return "evaluating"
    if signal_type == "essa_profile":
        return "confirmed"
    if signal_type == "state_initiative":
        return "active"
    if signal_type == "job_posting":
        return "confirmed"
    if signal_type == "press_release":
        return "confirmed"
    return "evaluating"


# ─── News helpers ─────────────────────────────────────────────────────────────

_RISK_KW    = {"layoff","lawsuit","breach","fine","investigat","hack","bankrupt","fraud",
               "regulat","penalty","outage","downtime","violat"}
_EDTECH_PRESS_SITES = (
    "businesswire.com", "prnewswire.com",
    "edsurge.com", "edweek.org", "k12dive.com", "eschoolnews.com"
)

def categorize_news(headline: str) -> tuple[str, int]:
    h = headline.lower()
    if any(kw in h for kw in _RISK_KW):
        return "risk", 7
    if any(kw in h for kw in ["budget","funding","esser","grant","expenditure","bond"]):
        return "financial", 7
    if any(kw in h for kw in ["launch","award","partner","pilot","deploy","initiative","rfp","bid"]):
        return "product", 6
    if any(kw in h for kw in ["technology","edtech","lms","device","1:1","chromebook","canvas","clever","google","microsoft"]):
        return "edtech", 6
    return "general", 3


# ─── 1. Board minutes ingestor ────────────────────────────────────────────────

async def ingest_board_minutes(account: dict, cutoff: datetime) -> tuple[int, int]:
    account_id   = account["id"]
    legal_name   = (account.get("district_legal_name") or account.get("name", "")).strip()
    total_score  = 0
    signal_count = 0

    queries = [
        f"{legal_name} board meeting minutes",
        f"{legal_name} school board agenda",
    ]

    for query in queries:
        url = f"https://news.google.com/rss/search?q={urlquote(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                          headers={"User-Agent": "Quorum/1.0"}) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:10]:
                try:
                    pub = entry.get("published_parsed")
                    pub_date_str = None
                    if pub:
                        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                        pub_date_str = pub_dt.strftime("%Y-%m-%d")
                        if pub_dt < cutoff:
                            continue
                    title = entry.get("title", "")
                    link  = entry.get("link", "")

                    # Try fetching and classifying the page text with Claude
                    page_text = ""
                    try:
                        async with httpx.AsyncClient(timeout=10, follow_redirects=True,
                                                      headers={"User-Agent": "Quorum/1.0"}) as pclient:
                            pr = await pclient.get(link)
                            if pr.status_code == 200:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(pr.text, "html.parser")
                                # Strip scripts/styles
                                for tag in soup(["script","style","nav","footer","header"]):
                                    tag.decompose()
                                page_text = soup.get_text(separator=" ", strip=True)[:3000]
                    except Exception:
                        pass

                    # Try PDF if link ends in .pdf
                    if not page_text and link.lower().endswith(".pdf"):
                        try:
                            import io, pdfplumber
                            async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                                          headers={"User-Agent": "Quorum/1.0"}) as pclient:
                                pr = await pclient.get(link)
                                if pr.status_code == 200:
                                    with pdfplumber.open(io.BytesIO(pr.content)) as pdf:
                                        page_text = " ".join(
                                            (p.extract_text() or "") for p in pdf.pages[:10]
                                        )[:3000]
                        except Exception:
                            pass

                    # Claude classification
                    signals_extracted = []
                    if page_text:
                        try:
                            from anthropic import AsyncAnthropic
                            api_key = os.getenv("ANTHROPIC_API_KEY")
                            if api_key:
                                aclient = AsyncAnthropic(api_key=api_key)
                                classify_prompt = (
                                    "Extract structured signals from this school board document. "
                                    "For each signal found return JSON array: "
                                    "[{\"type\": \"budget_approval|strategic_initiative|vendor_mention|rfp|pain_point|tech_initiative\", "
                                    "\"description\": \"one sentence\", "
                                    "\"vendor_name\": \"vendor if mentioned or null\", "
                                    "\"dollar_amount\": \"dollar amount if mentioned or null\", "
                                    "\"certainty\": \"confirmed|active|evaluating\"}]\n\n"
                                    f"Document text:\n{page_text}"
                                )
                                cr = await aclient.messages.create(
                                    model="claude-3-5-sonnet-20241022",
                                    max_tokens=800,
                                    messages=[{"role": "user", "content": classify_prompt}]
                                )
                                raw_text = cr.content[0].text.strip()
                                if raw_text.startswith("```"):
                                    raw_text = raw_text.split("```")[1]
                                    if raw_text.startswith("json"):
                                        raw_text = raw_text[4:]
                                import json as _json
                                signals_extracted = _json.loads(raw_text.strip())
                        except Exception as e:
                            print(f"[ingest_board_minutes] Claude classify error: {e}")

                    if signals_extracted:
                        for sig in signals_extracted[:5]:
                            sub = sig.get("type", "")
                            cert = _certainty_for("board_minutes_item", sub)
                            sig_score = 9 if cert == "confirmed" else (7 if cert == "active" else 5)
                            await db.save_signal(
                                account_id=account_id,
                                engineer_username=legal_name,
                                signal_type="board_minutes_item",
                                repo_name=f"BoardMinutes/{sub}",
                                repo_url=link,
                                repo_description=sig.get("description","")[:200],
                                repo_language="",
                                repo_topics=[sub],
                                raw_data={
                                    "headline": title[:200],
                                    "signal_subtype": sub,
                                    "vendor_name": sig.get("vendor_name"),
                                    "dollar_amount": sig.get("dollar_amount"),
                                    "pub_date": pub_date_str,
                                    "sig_score": sig_score,
                                    "certainty": cert,
                                }
                            )
                            total_score  += SIGNAL_WEIGHTS["board_minutes_item"] * sig_score
                            signal_count += 1
                    else:
                        # Fallback: save headline as a general signal
                        category, sig_score = categorize_news(title)
                        cert = "evaluating"
                        await db.save_signal(
                            account_id=account_id,
                            engineer_username=legal_name,
                            signal_type="board_minutes_item",
                            repo_name="BoardMinutes/general",
                            repo_url=link,
                            repo_description=title[:200],
                            repo_language="",
                            repo_topics=[category],
                            raw_data={
                                "headline": title[:200],
                                "pub_date": pub_date_str,
                                "sig_score": sig_score,
                                "certainty": cert,
                            }
                        )
                        total_score  += SIGNAL_WEIGHTS["board_minutes_item"] * sig_score
                        signal_count += 1
                except Exception:
                    continue
        except Exception as e:
            print(f"[ingest_board_minutes] RSS error for '{query}': {e}")

    return total_score, signal_count


# ─── 2. ESSA data ingestor ────────────────────────────────────────────────────

async def ingest_essa_data(account: dict) -> tuple[int, int]:
    account_id = account["id"]
    nces_id    = (account.get("nces_id") or "").strip()
    if not nces_id:
        return 0, 0

    enroll = None
    try:
        url = f"https://data.ed.gov/dataset/a61d5b09-d7c8-4fa2-9e19-e53fbf4d2d69/resource/9cf49e2e-58b4-4a28-a4dc-2ee87bae8d47/download/lea_directory.csv"
        # Use a direct NCES CCD API endpoint if available
        api_url = f"https://educationdata.urban.org/api/v1/schools/ccd/directory/{nces_id}/?year=2022"
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Quorum/1.0"}) as client:
            resp = await client.get(api_url)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    row = results[0]
                    enroll  = row.get("enrollment")
                    title1  = row.get("titlei_status_text")
                    pppe    = row.get("per_pupil_expenditure")
                    await db.update_account_essa(
                        account_id,
                        total_enrollment=int(enroll) if enroll else None,
                        title1_status=str(title1) if title1 else None,
                        per_pupil_expenditure=int(pppe) if pppe else None,
                    )
    except Exception as e:
        print(f"[ingest_essa] Error for NCES {nces_id}: {e}")
        return 0, 0

    if enroll:
        desc = f"NCES {nces_id}: enrollment={enroll}"
        await db.save_signal(
            account_id=account_id,
            engineer_username=nces_id,
            signal_type="essa_profile",
            repo_name="ESSA/CCD",
            repo_url=f"https://nces.ed.gov/ccd/schoolsearch/",
            repo_description=desc[:200],
            repo_language="",
            repo_topics=["profile"],
            raw_data={
                "nces_id": nces_id,
                "enrollment": enroll,
                "sig_score": 6,
                "certainty": "confirmed",
            }
        )
        return SIGNAL_WEIGHTS["essa_profile"] * 6, 1
    return 0, 0


# ─── 3. State DOE RSS ingestor ────────────────────────────────────────────────

STATE_DOE_RSS: dict[str, str] = {
    "CA": "https://www.cde.ca.gov/nr/ne/yr/rss.asp",
    "TX": "https://tea.texas.gov/About_TEA/News_and_Multimedia/rss_feeds.aspx",
    "NY": "https://www.nysed.gov/news/rss",
    "FL": "https://www.fldoe.org/newsroom/rss.stml",
    "IL": "https://www.isbe.net/Pages/ISBE-RSS-Feeds.aspx",
    "PA": "https://www.education.pa.gov/pages/rss-feeds.aspx",
    "OH": "https://education.ohio.gov/Pages/Home.aspx",
    "GA": "https://www.gadoe.org/External-Affairs-and-Policy/communications/Pages/PressReleaseDetails.aspx",
    "NC": "https://www.dpi.nc.gov/news/news-releases/rss.xml",
    "MI": "https://www.michigan.gov/mde/news-announcements",
    "WA": "https://feeds.feedburner.com/ospi",
    "CO": "https://www.cde.state.co.us/news-releases.rss",
}

DOMAIN_TO_STATE: dict[str, str] = {
    "ca.us": "CA", "k12.ca.us": "CA",
    "tx.us": "TX", "k12.tx.us": "TX",
    "ny.us": "NY", "k12.ny.us": "NY",
    "fl.us": "FL", "k12.fl.us": "FL",
    "il.us": "IL", "k12.il.us": "IL",
    "pa.us": "PA", "k12.pa.us": "PA",
    "oh.us": "OH", "k12.oh.us": "OH",
    "ga.us": "GA", "k12.ga.us": "GA",
    "nc.us": "NC", "k12.nc.us": "NC",
    "mi.us": "MI", "k12.mi.us": "MI",
    "wa.us": "WA", "k12.wa.us": "WA",
    "co.us": "CO", "k12.co.us": "CO",
}

def _domain_to_state(domain: str) -> str | None:
    domain = domain.lower().strip()
    for suffix, state in DOMAIN_TO_STATE.items():
        if domain.endswith(f".{suffix}") or domain == suffix:
            return state
    return None


async def ingest_state_doe_rss(account: dict, cutoff: datetime) -> tuple[int, int]:
    account_id  = account["id"]
    domain      = (account.get("district_domain") or "").strip()
    legal_name  = (account.get("district_legal_name") or account.get("name","")).strip()
    total_score = 0
    signal_count = 0

    state = _domain_to_state(domain)
    rss_url = STATE_DOE_RSS.get(state or "")
    if not rss_url:
        return 0, 0

    _EDTECH_KW = {
        "technology","edtech","lms","device","1:1","chromebook","canvas","clever",
        "esser","instructional","digital","curriculum","broadband","wi-fi","wifi",
    }

    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                      headers={"User-Agent": "Quorum/1.0"}) as client:
            resp = await client.get(rss_url)
            if resp.status_code != 200:
                return 0, 0
        feed = feedparser.parse(resp.text)
        for entry in feed.entries[:20]:
            try:
                pub = entry.get("published_parsed")
                pub_date_str = None
                if pub:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    pub_date_str = pub_dt.strftime("%Y-%m-%d")
                    if pub_dt < cutoff:
                        continue
                title = entry.get("title", "")
                link  = entry.get("link",  "")
                lower = title.lower()
                # Filter: mentions district or EdTech keywords
                if legal_name.lower() not in lower and not any(kw in lower for kw in _EDTECH_KW):
                    continue
                sig_score = 6
                await db.save_signal(
                    account_id=account_id,
                    engineer_username=state or domain,
                    signal_type="state_initiative",
                    repo_name=f"StateDOE/{state or 'Unknown'}",
                    repo_url=link,
                    repo_description=title[:200],
                    repo_language="",
                    repo_topics=["state_policy"],
                    raw_data={
                        "headline": title[:200],
                        "state": state,
                        "pub_date": pub_date_str,
                        "sig_score": sig_score,
                        "certainty": "active",
                    }
                )
                total_score  += SIGNAL_WEIGHTS["state_initiative"] * sig_score
                signal_count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"[ingest_state_doe_rss] Error for state {state}: {e}")
    return total_score, signal_count


# ─── 4. EdTech news ingestor ──────────────────────────────────────────────────

_EDTECH_PRESS_SITES_QUERY = (
    "site:edsurge.com OR site:edweek.org OR site:k12dive.com OR "
    "site:eschoolnews.com OR site:businesswire.com OR site:prnewswire.com"
)

async def ingest_edtech_news(account: dict, cutoff: datetime) -> tuple[int, int]:
    account_id  = account["id"]
    legal_name  = (account.get("district_legal_name") or account.get("name","")).strip()
    total_score = 0
    signal_count = 0

    # General news queries
    news_queries = [
        f"{legal_name} edtech",
        f"{legal_name} technology",
        f"{legal_name} LMS",
        f"{legal_name} devices",
        f"{legal_name} ESSER",
    ]
    for query in news_queries:
        url = f"https://news.google.com/rss/search?q={urlquote(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                          headers={"User-Agent": "Quorum/1.0"}) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:8]:
                try:
                    pub = entry.get("published_parsed")
                    pub_date_str = None
                    if pub:
                        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                        pub_date_str = pub_dt.strftime("%Y-%m-%d")
                        if pub_dt < cutoff:
                            continue
                    title  = entry.get("title","")
                    link   = entry.get("link","")
                    source = entry.get("source",{}).get("title","") if hasattr(entry.get("source",""),"get") else ""
                    category, sig_score = categorize_news(title)
                    certainty = "evaluating"
                    await db.save_signal(
                        account_id=account_id,
                        engineer_username=legal_name,
                        signal_type="news_mention",
                        repo_name=f"News/{source or 'General'}",
                        repo_url=link,
                        repo_description=title[:200],
                        repo_language="",
                        repo_topics=[category],
                        raw_data={
                            "headline": title[:200],
                            "source": source,
                            "news_category": category,
                            "pub_date": pub_date_str,
                            "sig_score": sig_score,
                            "certainty": certainty,
                        }
                    )
                    total_score  += SIGNAL_WEIGHTS["news_mention"] * sig_score
                    signal_count += 1
                except Exception:
                    continue
        except Exception as e:
            print(f"[ingest_edtech_news] News RSS error for '{query}': {e}")

    # EdTech press sites query
    pr_query = f"{legal_name} ({_EDTECH_PRESS_SITES_QUERY})"
    pr_url = f"https://news.google.com/rss/search?q={urlquote(pr_query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                      headers={"User-Agent": "Quorum/1.0"}) as client:
            resp = await client.get(pr_url)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                for entry in feed.entries[:8]:
                    try:
                        pub = entry.get("published_parsed")
                        pub_date_str = None
                        if pub:
                            pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                            pub_date_str = pub_dt.strftime("%Y-%m-%d")
                            if pub_dt < cutoff:
                                continue
                        title  = entry.get("title","")
                        link   = entry.get("link","")
                        category, sig_score = categorize_news(title)
                        sig_score = max(sig_score, 5)
                        await db.save_signal(
                            account_id=account_id,
                            engineer_username=legal_name,
                            signal_type="press_release",
                            repo_name="EdTechPress",
                            repo_url=link,
                            repo_description=title[:200],
                            repo_language="",
                            repo_topics=[category],
                            raw_data={
                                "headline": title[:200],
                                "news_category": category,
                                "pub_date": pub_date_str,
                                "sig_score": sig_score,
                                "certainty": "confirmed",
                            }
                        )
                        total_score  += SIGNAL_WEIGHTS["press_release"] * sig_score
                        signal_count += 1
                    except Exception:
                        continue
    except Exception as e:
        print(f"[ingest_edtech_news] EdTech press RSS error: {e}")

    return total_score, signal_count


# ─── 5. Job postings ingestor ─────────────────────────────────────────────────

_JOB_EDTECH_KW = {
    "instructional technology","lms","director of technology","edtech","1:1",
    "device","data systems","canvas","google classroom","ed tech","information technology",
    "director of it","education technology","chief technology","cto",
}

def _job_is_edtech(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in _JOB_EDTECH_KW)


async def ingest_job_postings(account: dict) -> tuple[int, int]:
    account_id  = account["id"]
    domain      = (account.get("district_domain") or "").strip()
    if not domain:
        return 0, 0

    # Create a slug from domain: lausd.net -> lausd
    slug = domain.split(".")[0].lower()
    total_score  = 0
    signal_count = 0

    sources = [
        f"https://boards.greenhouse.io/{slug}/jobs",
        f"https://jobs.lever.co/{slug}",
    ]

    for src_url in sources:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True,
                                          headers={"User-Agent": "Quorum/1.0"}) as client:
                resp = await client.get(src_url)
                if resp.status_code != 200:
                    continue
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            # Collect all links whose text looks like a job title
            links = soup.find_all("a", href=True)
            seen  = set()
            for a in links:
                title = a.get_text(strip=True)
                href  = a["href"]
                if not title or len(title) < 5 or len(title) > 120:
                    continue
                if title in seen:
                    continue
                if _job_is_edtech(title):
                    seen.add(title)
                    job_url = href if href.startswith("http") else (src_url.rstrip("/") + "/" + href.lstrip("/"))
                    await db.save_signal(
                        account_id=account_id,
                        engineer_username=domain,
                        signal_type="job_posting",
                        repo_name=f"Jobs/{slug}",
                        repo_url=job_url,
                        repo_description=title[:200],
                        repo_language="",
                        repo_topics=["hiring"],
                        raw_data={
                            "job_title": title[:200],
                            "source": src_url,
                            "sig_score": 7,
                            "certainty": "confirmed",
                        }
                    )
                    total_score  += SIGNAL_WEIGHTS["job_posting"] * 7
                    signal_count += 1
        except Exception as e:
            print(f"[ingest_job_postings] Error for {src_url}: {e}")

    return total_score, signal_count


# ─── 6. USASpending federal grants ───────────────────────────────────────────

_ESSER_PROGRAMS = ["84.425", "84.425A", "84.425C", "84.425D", "84.011", "84.027"]

async def ingest_usaspending(account: dict) -> tuple[int, int]:
    """Fetch ESSER/Title I/IDEA federal grants from USASpending.gov (no API key required)."""
    account_id = account["id"]
    legal_name = (account.get("district_legal_name") or account.get("name", "")).strip()
    if not legal_name:
        return 0, 0

    total_score  = 0
    signal_count = 0
    payload = {
        "filters": {
            "recipient_search_text": [legal_name],
            "award_type_codes": ["02", "03", "04", "05"],
            "program_numbers": _ESSER_PROGRAMS,
            "time_period": [{"date_type": "date_signed",
                             "start_date": "2020-01-01",
                             "end_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")}],
        },
        "fields": ["Award ID", "Recipient Name", "Awarding Agency",
                   "Award Amount", "Start Date", "Description"],
        "sort": "Award Amount",
        "order": "desc",
        "limit": 10,
        "page": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "Quorum/1.0"}) as client:
            resp = await client.post(
                "https://api.usaspending.gov/api/v2/search/spending_by_award/",
                json=payload,
            )
        if resp.status_code != 200:
            return 0, 0
        for award in (resp.json().get("results") or []):
            amount   = award.get("Award Amount") or 0
            award_id = award.get("Award ID") or ""
            agency   = (award.get("Awarding Agency") or "Dept of Education")[:80]
            desc     = (award.get("Description") or "")[:80]
            start_dt = award.get("Start Date") or ""
            amt_str  = f"${amount:,.0f}" if amount else ""
            headline = f"{legal_name}: {amt_str} federal grant — {desc}" if desc else f"{legal_name}: {amt_str} federal grant"
            sig_score = 9 if amount >= 1_000_000 else (7 if amount >= 250_000 else 6)
            award_url = f"https://www.usaspending.gov/award/{award_id}" if award_id else "https://www.usaspending.gov"
            await db.save_signal(
                account_id=account_id,
                engineer_username=agency,
                signal_type="press_release",
                repo_name=f"FedGrants/{award_id or 'grant'}",
                repo_url=award_url,
                repo_description=headline[:200],
                repo_language="",
                repo_topics=["federal_grant"],
                raw_data={
                    "headline": headline[:200],
                    "dollar_amount": amt_str,
                    "agency": agency,
                    "news_category": "financial",
                    "source": "USASpending.gov",
                    "pub_date": start_dt,
                    "sig_score": sig_score,
                    "certainty": "confirmed",
                }
            )
            total_score  += SIGNAL_WEIGHTS["press_release"] * sig_score
            signal_count += 1
    except Exception as e:
        print(f"[ingest_usaspending] Error for '{legal_name}': {e}")
    return total_score, signal_count


# ─── Master ingest_account ────────────────────────────────────────────────────

async def ingest_account(account_id: int) -> dict:
    account = await db.get_account(account_id)
    if not account:
        raise ValueError("Account not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    await db.clear_signals(account_id)

    total_score  = 0
    signal_count = 0

    # 1 — Board minutes
    sc, sn = await ingest_board_minutes(account, cutoff)
    total_score += sc; signal_count += sn
    await asyncio.sleep(0.5)

    # 2 — ESSA profile
    sc, sn = await ingest_essa_data(account)
    total_score += sc; signal_count += sn

    # 3 — State DOE RSS
    sc, sn = await ingest_state_doe_rss(account, cutoff)
    total_score += sc; signal_count += sn
    await asyncio.sleep(0.5)

    # 4 — EdTech news
    sc, sn = await ingest_edtech_news(account, cutoff)
    total_score += sc; signal_count += sn
    await asyncio.sleep(0.5)

    # 5 — Job postings
    sc, sn = await ingest_job_postings(account)
    total_score += sc; signal_count += sn

    # 6 — Federal grants (USASpending)
    sc, sn = await ingest_usaspending(account)
    total_score += sc; signal_count += sn
    await asyncio.sleep(0.5)

    # Attempt favicon for avatar
    domain    = (account.get("district_domain") or "").strip()
    avatar_url = f"https://www.google.com/s2/favicons?sz=128&domain={domain}" if domain else None

    final_score = min(int(total_score / max(signal_count, 1) * 10), 100)
    await db.update_account_meta(account_id, final_score, avatar_url=avatar_url)

    return {
        "signals": signal_count,
        "score":   final_score,
    }
