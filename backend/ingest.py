import os
import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import quote as urlquote
from github import Github, GithubException
from dotenv import load_dotenv
import httpx
import feedparser
import database as db

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "30"))

SIGNAL_WEIGHTS = {
    "star": 1,
    "fork": 3,
    "new_repo": 4,
    "push": 2,
    "issue_comment": 5,
    "release": 3,
    "org_issue": 4,
    "hn_mention": 3,
    "news_mention": 4,
    "press_release": 6,
    "sec_filing": 8,
    "reddit_buzz": 3,
}

# Labels that raise the prescience score of an issue or comment
HIGH_VALUE_LABELS = {
    "migration", "migrate", "security", "compliance", "soc2", "gdpr",
    "performance", "regression", "roadmap", "rfc", "initiative",
    "breaking-change", "deprecation", "adopt",
}
MED_VALUE_LABELS = {"bug", "help wanted", "question", "enhancement", "tech-debt"}

TECH_KEYWORDS = [
    "llm", "ai", "ml", "machine-learning", "deep-learning", "neural",
    "kubernetes", "k8s", "docker", "terraform", "helm", "argo",
    "rust", "golang", "wasm", "webassembly",
    "kafka", "rabbitmq", "nats", "event-driven",
    "graphql", "grpc", "protobuf",
    "dbt", "airflow", "spark", "databricks", "snowflake",
    "langchain", "openai", "anthropic", "huggingface",
    "react", "nextjs", "svelte", "vue",
    "fastapi", "django", "flask",
    "postgres", "mongodb", "redis", "elasticsearch",
    "security", "devsecops", "soc2", "compliance",
    "platform-engineering", "developer-experience", "devex",
]

def score_repo(repo_name: str, description: str, topics: list, language: str) -> int:
    score = 0
    combined = f"{repo_name} {description or ''} {' '.join(topics or [])} {language or ''}".lower()
    for kw in TECH_KEYWORDS:
        if kw in combined:
            score += 2
    return min(score, 10)

def score_issue_labels(labels: list) -> int:
    label_set = {str(l).lower() for l in labels}
    if label_set & HIGH_VALUE_LABELS:
        return 7
    if label_set & MED_VALUE_LABELS:
        return 4
    return 2

def assign_certainty(signal_type: str, labels: list = None, prerelease: bool = False, is_fork: bool = False) -> str:
    """Returns confirmed / active / evaluating based on signal evidence strength."""
    labels_set = {str(l).lower() for l in (labels or [])}
    if signal_type == "release":
        return "evaluating" if prerelease else "confirmed"
    if signal_type == "new_repo":
        return "active" if is_fork else "confirmed"
    if signal_type in ("fork", "push"):
        return "active"
    if signal_type in ("issue_comment", "org_issue"):
        return "active" if (labels_set & HIGH_VALUE_LABELS) else "evaluating"
    return "evaluating"  # star, hn_mention, anything else


_RISK_KEYWORDS = {"layoff", "lawsuit", "breach", "fine", "investigat", "hack", "bankrupt", "fraud", "regulat", "penalty", "recall", "outage", "downtime", "violat"}
_FINANCIAL_KEYWORDS = {"earnings", "revenue", "profit", "loss", "guidance", "ipo", "quarter", "fiscal", "acquisition", "acquir", "merger", "funding", "valuation", "raises", "raises $"}
_PRODUCT_KEYWORDS = {"launch", "release", "announc", "partner", "integrat", "roadmap", "feature", "product", "platform", "api", "sdk", "open source", "general availability"}

def categorize_news(headline: str) -> tuple[str, int]:
    """Returns (category, sig_score) for a news headline using keyword matching."""
    h = headline.lower()
    if any(kw in h for kw in _RISK_KEYWORDS):
        return "risk", 8
    if any(kw in h for kw in _FINANCIAL_KEYWORDS):
        return "financial", 7
    if any(kw in h for kw in _PRODUCT_KEYWORDS):
        return "product", 6
    return "general", 3


async def ingest_news_signals(account_id: int, search_name: str, cutoff: datetime) -> tuple[int, int]:
    """Google News RSS — general headlines mentioning the company."""
    total_score = 0
    signal_count = 0
    url = f"https://news.google.com/rss/search?q={urlquote(search_name)}&hl=en-US&gl=US&ceid=US:en"
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                      headers={"User-Agent": "Temporality/1.0"}) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return 0, 0
        feed = feedparser.parse(resp.text)
        for entry in feed.entries[:20]:
            try:
                pub = entry.get("published_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                title = entry.get("title", "")
                link  = entry.get("link", "")
                source = entry.get("source", {}).get("title", "") if hasattr(entry.get("source", ""), "get") else ""
                category, sig_score = categorize_news(title)
                certainty = "active" if category == "risk" else ("confirmed" if category in ("financial", "product") else "evaluating")
                await db.save_signal(
                    account_id=account_id,
                    engineer_username=search_name,
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
                        "sig_score": sig_score,
                        "certainty": certainty,
                    }
                )
                total_score += SIGNAL_WEIGHTS["news_mention"] * sig_score
                signal_count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"[ingest] News RSS error for {search_name}: {e}")
    return total_score, signal_count


async def ingest_press_release_signals(account_id: int, search_name: str, cutoff: datetime) -> tuple[int, int]:
    """Google News RSS filtered to BusinessWire + PRNewswire — official press releases."""
    total_score = 0
    signal_count = 0
    q = f"{search_name} site:businesswire.com OR site:prnewswire.com"
    url = f"https://news.google.com/rss/search?q={urlquote(q)}&hl=en-US&gl=US&ceid=US:en"
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                      headers={"User-Agent": "Temporality/1.0"}) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return 0, 0
        feed = feedparser.parse(resp.text)
        for entry in feed.entries[:10]:
            try:
                pub = entry.get("published_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                title  = entry.get("title", "")
                link   = entry.get("link", "")
                category, sig_score = categorize_news(title)
                sig_score = max(sig_score, 5)  # press releases are always moderately high-value
                await db.save_signal(
                    account_id=account_id,
                    engineer_username=search_name,
                    signal_type="press_release",
                    repo_name="PRNewswire/BusinessWire",
                    repo_url=link,
                    repo_description=title[:200],
                    repo_language="",
                    repo_topics=[category],
                    raw_data={
                        "headline": title[:200],
                        "news_category": category,
                        "sig_score": sig_score,
                        "certainty": "confirmed",
                    }
                )
                total_score += SIGNAL_WEIGHTS["press_release"] * sig_score
                signal_count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"[ingest] Press release RSS error for {search_name}: {e}")
    return total_score, signal_count


async def ingest_sec_signals(account_id: int, ticker: str, cutoff: datetime) -> tuple[int, int]:
    """SEC EDGAR 8-K filings — major events for public companies."""
    if not ticker:
        return 0, 0
    total_score = 0
    signal_count = 0
    ticker = ticker.upper().strip()
    start_dt = cutoff.date().isoformat()
    url = (
        f"https://efts.sec.gov/LATEST/search-index?q=%22{urlquote(ticker)}%22"
        f"&forms=8-K&dateRange=custom&startdt={start_dt}"
    )
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Temporality contact@temporality.ai"}) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return 0, 0
            data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        for hit in hits[:10]:
            try:
                src = hit.get("_source", {})
                filed = src.get("file_date", "")
                if filed:
                    filed_dt = datetime.fromisoformat(filed).replace(tzinfo=timezone.utc)
                    if filed_dt < cutoff:
                        continue
                display_names = src.get("display_names", [])
                company = display_names[0].get("name", ticker) if display_names else ticker
                form_type = src.get("form_type", "8-K")
                description = src.get("period_of_report", "")
                accession = src.get("accession_no", "").replace("-", "")
                doc_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum=&type=8-K&dateb=&owner=include&count=10&search_text=" if not accession else f"https://www.sec.gov/Archives/edgar/data/{src.get('entity_id','')}/{accession}/{accession}-index.htm"
                category, _ = categorize_news(src.get("file_num", "") + " " + form_type)
                await db.save_signal(
                    account_id=account_id,
                    engineer_username=ticker,
                    signal_type="sec_filing",
                    repo_name=f"SEC/{form_type}",
                    repo_url=doc_url,
                    repo_description=f"{form_type} filing: {company} ({filed})",
                    repo_language="",
                    repo_topics=["regulatory"],
                    raw_data={
                        "ticker": ticker,
                        "form_type": form_type,
                        "company": company,
                        "filed_date": filed,
                        "news_category": "financial",
                        "sig_score": 9,
                        "certainty": "confirmed",
                    }
                )
                total_score += SIGNAL_WEIGHTS["sec_filing"] * 9
                signal_count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"[ingest] SEC EDGAR error for {ticker}: {e}")
    return total_score, signal_count


async def ingest_reddit_signals(account_id: int, search_name: str, cutoff: datetime) -> tuple[int, int]:
    """Reddit public search — community sentiment and discussions."""
    total_score = 0
    signal_count = 0
    url = f"https://www.reddit.com/search.json?q={urlquote(search_name)}&sort=new&limit=15&t=month"
    try:
        async with httpx.AsyncClient(timeout=12, headers={"User-Agent": "Temporality/1.0"}) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return 0, 0
            data = resp.json()
        posts = data.get("data", {}).get("children", [])
        for post in posts:
            try:
                p = post.get("data", {})
                created = p.get("created_utc", 0)
                created_dt = datetime.fromtimestamp(created, tz=timezone.utc)
                if created_dt < cutoff:
                    continue
                title   = p.get("title", "")
                link    = f"https://www.reddit.com{p.get('permalink', '')}"
                score   = p.get("score", 0)
                comments = p.get("num_comments", 0)
                subreddit = p.get("subreddit", "")
                sig_score = min(2 + (score // 20) + (comments // 10), 10)
                category, _ = categorize_news(title)
                await db.save_signal(
                    account_id=account_id,
                    engineer_username=search_name,
                    signal_type="reddit_buzz",
                    repo_name=f"Reddit/r/{subreddit}",
                    repo_url=link,
                    repo_description=title[:200],
                    repo_language="",
                    repo_topics=[subreddit],
                    raw_data={
                        "headline": title[:200],
                        "subreddit": subreddit,
                        "score": score,
                        "num_comments": comments,
                        "news_category": category,
                        "sig_score": sig_score,
                        "certainty": "evaluating",
                    }
                )
                total_score += SIGNAL_WEIGHTS["reddit_buzz"] * sig_score
                signal_count += 1
            except Exception:
                continue
    except Exception as e:
        print(f"[ingest] Reddit error for {search_name}: {e}")
    return total_score, signal_count

async def ingest_engineer_events(g, account_id: int, engineer: dict, cutoff: datetime) -> tuple[int, int]:
    """Collect IssueCommentEvents — engineer actively debugging a 3rd-party tool."""
    username = engineer["github_username"]
    total_score = 0
    signal_count = 0
    try:
        events = g.get_user(username).get_events()
        scanned = 0
        for event in events:
            if scanned >= 90:
                break
            scanned += 1
            event_dt = event.created_at
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
            if event_dt < cutoff:
                break
            if event.type != "IssueCommentEvent":
                continue
            try:
                payload = event.payload
                issue    = payload.get("issue", {})
                comment  = payload.get("comment", {})
                repo_url = event.repo.url.replace("api.github.com/repos", "github.com") if event.repo else ""
                issue_title = issue.get("title", "")
                labels  = [lb.get("name", "") if isinstance(lb, dict) else str(lb)
                           for lb in issue.get("labels", [])]
                sig_score = score_issue_labels(labels)
                # Extra bump if comment text contains high-value keywords
                body = (comment.get("body", "") or "").lower()
                if any(kw in body for kw in ["migrat", "replac", "evaluat", "switch", "deprecat", "security", "compliance"]):
                    sig_score = min(sig_score + 2, 10)
                await db.save_signal(
                    account_id=account_id,
                    engineer_username=username,
                    signal_type="issue_comment",
                    repo_name=event.repo.name if event.repo else "",
                    repo_url=repo_url,
                    repo_description=issue_title[:200],
                    repo_language="",
                    repo_topics=labels[:5],
                    raw_data={
                        "issue_number": issue.get("number"),
                        "issue_title": issue_title[:120],
                        "labels": labels[:5],
                        "comment_preview": (comment.get("body", "") or "")[:200],
                        "sig_score": sig_score,
                        "certainty": assign_certainty("issue_comment", labels=labels),
                    }
                )
                total_score += SIGNAL_WEIGHTS["issue_comment"] * sig_score
                signal_count += 1
                if signal_count >= 20:
                    break
            except Exception:
                continue
    except GithubException:
        pass
    return total_score, signal_count

async def ingest_org_signals(g, account_id: int, org_name: str, cutoff: datetime) -> tuple[int, int, str]:
    """Collect releases, open issues, and HackerNews mentions for the org."""
    total_score = 0
    signal_count = 0
    org_avatar = None

    try:
        org = g.get_organization(org_name)
        org_avatar = org.avatar_url or None
        repos = sorted(org.get_repos(type="public"),
                       key=lambda r: r.pushed_at or r.created_at, reverse=True)[:8]

        # ── Releases ────────────────────────────────────────────────────────
        for repo in repos:
            try:
                for release in list(repo.get_releases())[:5]:
                    release_dt = release.created_at
                    if release_dt.tzinfo is None:
                        release_dt = release_dt.replace(tzinfo=timezone.utc)
                    if release_dt < cutoff:
                        continue
                    tag = release.tag_name or ""
                    # Score: major bump = 8, prerelease = 1, otherwise 5
                    import re as _re
                    major = _re.match(r"v?(\d+)\.", tag)
                    if release.prerelease:
                        sig_score = 1
                    elif major and int(major.group(1)) >= 2:
                        sig_score = 8
                    else:
                        sig_score = 5
                    body_preview = (release.body or "")[:300]
                    await db.save_signal(
                        account_id=account_id,
                        engineer_username=org_name,
                        signal_type="release",
                        repo_name=repo.full_name,
                        repo_url=release.html_url,
                        repo_description=f"{tag}: {release.name or ''}".strip(": "),
                        repo_language=repo.language or "",
                        repo_topics=[],
                        raw_data={
                            "tag": tag,
                            "release_name": release.name or "",
                            "prerelease": release.prerelease,
                            "body_preview": body_preview,
                            "sig_score": sig_score,
                            "certainty": assign_certainty("release", prerelease=release.prerelease),
                        }
                    )
                    total_score += SIGNAL_WEIGHTS["release"] * sig_score
                    signal_count += 1
            except Exception:
                continue

        # ── Open Issues (org repos) ──────────────────────────────────────────
        issue_count = 0
        for repo in repos[:5]:
            if issue_count >= 30:
                break
            try:
                issues = repo.get_issues(state="open", sort="updated", since=cutoff)
                for issue in issues:
                    if issue_count >= 30:
                        break
                    labels = [lb.name for lb in issue.labels]
                    sig_score = score_issue_labels(labels)
                    body_preview = (issue.body or "")[:200]
                    await db.save_signal(
                        account_id=account_id,
                        engineer_username=org_name,
                        signal_type="org_issue",
                        repo_name=repo.full_name,
                        repo_url=issue.html_url,
                        repo_description=issue.title[:200],
                        repo_language="",
                        repo_topics=labels[:5],
                        raw_data={
                            "issue_number": issue.number,
                            "issue_title": issue.title[:120],
                            "labels": labels[:5],
                            "body_preview": body_preview,
                            "sig_score": sig_score,
                            "certainty": assign_certainty("org_issue", labels=labels),
                        }
                    )
                    total_score += SIGNAL_WEIGHTS["org_issue"] * sig_score
                    signal_count += 1
                    issue_count += 1
            except Exception:
                continue

    except Exception as e:
        print(f"[ingest] Org signals error for {org_name}: {e}")

    # ── HackerNews ──────────────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for tag in ["story", "comment"]:
                try:
                    resp = await client.get(
                        "https://hn.algolia.com/api/v1/search",
                        params={"query": org_name, "tags": tag, "hitsPerPage": 8}
                    )
                    if resp.status_code != 200:
                        continue
                    hits = resp.json().get("hits", [])
                    for hit in hits:
                        created_ms = hit.get("created_at_i", 0)
                        created_dt = datetime.fromtimestamp(created_ms, tz=timezone.utc)
                        if created_dt < cutoff:
                            continue
                        points = hit.get("points") or 0
                        num_comments = hit.get("num_comments") or 0
                        sig_score = min(2 + (points // 20) + (num_comments // 10), 10)
                        title = hit.get("title") or hit.get("comment_text", "")[:120] or ""
                        url   = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID','')}"
                        author = hit.get("author", "")
                        text_preview = (hit.get("story_text") or hit.get("comment_text") or "")[:200]
                        await db.save_signal(
                            account_id=account_id,
                            engineer_username=org_name,
                            signal_type="hn_mention",
                            repo_name=f"HackerNews/{tag}",
                            repo_url=url,
                            repo_description=title[:200],
                            repo_language="",
                            repo_topics=[tag],
                            raw_data={
                                "hn_type": tag,
                                "author": author,
                                "points": points,
                                "num_comments": num_comments,
                                "text_preview": text_preview,
                                "sig_score": sig_score,
                                "certainty": "evaluating",
                            }
                        )
                        total_score += SIGNAL_WEIGHTS["hn_mention"] * sig_score
                        signal_count += 1
                except Exception:
                    continue
    except Exception as e:
        print(f"[ingest] HN error for {org_name}: {e}")

    return total_score, signal_count, org_avatar

async def ingest_account(account_id: int) -> dict:
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set in .env")

    g = Github(GITHUB_TOKEN)
    account  = await db.get_account(account_id)
    engineers = await db.get_engineers(account_id)

    if not engineers:
        return {"signals": 0, "score": 0, "error": "No engineers tracked for this account"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    await db.clear_signals(account_id)

    total_score = 0
    signal_count = 0

    for engineer in engineers:
        username = engineer["github_username"]
        try:
            user = g.get_user(username)
            # Update engineer profile (including company)
            company_raw = user.company or ''
            await db.upsert_engineer(
                account_id, username,
                display_name=user.name or username,
                avatar_url=user.avatar_url,
                company=company_raw.lstrip('@').strip() or None
            )

            # --- Starred repos ---
            try:
                starred = user.get_starred()
                for repo in starred:
                    starred_at = getattr(repo, 'starred_at', None)
                    if starred_at:
                        if starred_at.tzinfo is None:
                            starred_at = starred_at.replace(tzinfo=timezone.utc)
                        if starred_at < cutoff:
                            break
                    topics = repo.get_topics()
                    sig_score = score_repo(repo.name, repo.description, topics, repo.language)
                    await db.save_signal(
                        account_id=account_id,
                        engineer_username=username,
                        signal_type="star",
                        repo_name=repo.full_name,
                        repo_url=repo.html_url,
                        repo_description=repo.description or "",
                        repo_language=repo.language or "",
                        repo_topics=topics,
                        raw_data={"stars": repo.stargazers_count, "sig_score": sig_score, "certainty": "evaluating"}
                    )
                    total_score += SIGNAL_WEIGHTS["star"] * sig_score
                    signal_count += 1
            except GithubException:
                pass

            # --- User's own public repos (new ones) ---
            try:
                repos = user.get_repos(type="public", sort="created")
                for repo in repos:
                    created_at = repo.created_at
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if created_at < cutoff:
                        break
                    if repo.fork:
                        signal_type = "fork"
                    else:
                        signal_type = "new_repo"
                    topics = []
                    try:
                        topics = repo.get_topics()
                    except:
                        pass
                    sig_score = score_repo(repo.name, repo.description, topics, repo.language)
                    await db.save_signal(
                        account_id=account_id,
                        engineer_username=username,
                        signal_type=signal_type,
                        repo_name=repo.full_name,
                        repo_url=repo.html_url,
                        repo_description=repo.description or "",
                        repo_language=repo.language or "",
                        repo_topics=topics,
                        raw_data={
                            "stars": repo.stargazers_count,
                            "forks": repo.forks_count,
                            "sig_score": sig_score,
                            "certainty": assign_certainty(signal_type, is_fork=repo.fork),
                        }
                    )
                    total_score += SIGNAL_WEIGHTS[signal_type] * sig_score
                    signal_count += 1
            except GithubException:
                pass

            # --- Engineer issue comments (pain / evaluation signals) ---
            eng_score, eng_sigs = await ingest_engineer_events(g, account_id, engineer, cutoff)
            total_score  += eng_score
            signal_count += eng_sigs

        except GithubException as e:
            print(f"[ingest] Error for {username}: {e}")
            continue
        except Exception as e:
            print(f"[ingest] Unexpected error for {username}: {e}")
            continue

        # Rate limit buffer
        await asyncio.sleep(0.5)

    # --- Org-level signals (releases, open issues, HackerNews) ---
    org_name   = (account or {}).get("github_org", "").strip()
    org_avatar = None
    if org_name:
        org_score, org_sigs, org_avatar = await ingest_org_signals(g, account_id, org_name, cutoff)
        total_score  += org_score
        signal_count += org_sigs

    # --- Business-level signals (news, press releases, SEC filings, Reddit) ---
    search_name = (account or {}).get("news_name") or (account or {}).get("name", "").strip()
    ticker      = ((account or {}).get("ticker_symbol") or "").strip()
    if search_name:
        news_score, news_sigs = await ingest_news_signals(account_id, search_name, cutoff)
        total_score  += news_score
        signal_count += news_sigs

        pr_score, pr_sigs = await ingest_press_release_signals(account_id, search_name, cutoff)
        total_score  += pr_score
        signal_count += pr_sigs

        rd_score, rd_sigs = await ingest_reddit_signals(account_id, search_name, cutoff)
        total_score  += rd_score
        signal_count += rd_sigs

    if ticker:
        sec_score, sec_sigs = await ingest_sec_signals(account_id, ticker, cutoff)
        total_score  += sec_score
        signal_count += sec_sigs

    final_score = min(int(total_score / max(signal_count, 1) * 10), 100)
    await db.update_account_meta(account_id, final_score, avatar_url=org_avatar)

    return {
        "signals": signal_count,
        "score": final_score,
        "engineers_processed": len(engineers)
    }
