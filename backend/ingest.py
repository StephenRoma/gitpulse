import os
import asyncio
from datetime import datetime, timedelta
from github import Github, GithubException
from dotenv import load_dotenv
import httpx
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
            if event.created_at < cutoff:
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

async def ingest_org_signals(g, account_id: int, org_name: str, cutoff: datetime) -> tuple[int, int]:
    """Collect releases, open issues, and HackerNews mentions for the org."""
    total_score = 0
    signal_count = 0

    try:
        org = g.get_organization(org_name)
        repos = sorted(org.get_repos(type="public"),
                       key=lambda r: r.pushed_at or r.created_at, reverse=True)[:8]

        # ── Releases ────────────────────────────────────────────────────────
        for repo in repos:
            try:
                for release in repo.get_releases()[:5]:
                    if release.created_at < cutoff:
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
                        }
                    )
                    total_score += SIGNAL_WEIGHTS["release"] * sig_score
                    signal_count += 1
            except GithubException:
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
                        }
                    )
                    total_score += SIGNAL_WEIGHTS["org_issue"] * sig_score
                    signal_count += 1
                    issue_count += 1
            except GithubException:
                continue

    except GithubException as e:
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
                        created_dt = datetime.utcfromtimestamp(created_ms)
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
                            }
                        )
                        total_score += SIGNAL_WEIGHTS["hn_mention"] * sig_score
                        signal_count += 1
                except Exception:
                    continue
    except Exception as e:
        print(f"[ingest] HN error for {org_name}: {e}")

    return total_score, signal_count

async def ingest_account(account_id: int) -> dict:
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set in .env")

    g = Github(GITHUB_TOKEN)
    account  = await db.get_account(account_id)
    engineers = await db.get_engineers(account_id)

    if not engineers:
        return {"signals": 0, "score": 0, "error": "No engineers tracked for this account"}

    cutoff = datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)
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
                    if starred_at and starred_at < cutoff:
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
                        raw_data={"stars": repo.stargazers_count, "sig_score": sig_score}
                    )
                    total_score += SIGNAL_WEIGHTS["star"] * sig_score
                    signal_count += 1
            except GithubException:
                pass

            # --- User's own public repos (new ones) ---
            try:
                repos = user.get_repos(type="public", sort="created")
                for repo in repos:
                    if repo.created_at < cutoff:
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
                            "sig_score": sig_score
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
    org_name = (account or {}).get("github_org", "").strip()
    if org_name:
        org_score, org_sigs = await ingest_org_signals(g, account_id, org_name, cutoff)
        total_score  += org_score
        signal_count += org_sigs

    final_score = min(int(total_score / max(signal_count, 1) * 10), 100)
    await db.update_account_meta(account_id, final_score)

    return {
        "signals": signal_count,
        "score": final_score,
        "engineers_processed": len(engineers)
    }
