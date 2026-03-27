import os
import asyncio
from datetime import datetime, timedelta
from github import Github, GithubException
from dotenv import load_dotenv
import database as db

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "30"))

SIGNAL_WEIGHTS = {
    "star": 1,
    "fork": 3,
    "new_repo": 4,
    "push": 2,
}

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

async def ingest_account(account_id: int) -> dict:
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set in .env")

    g = Github(GITHUB_TOKEN)
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
            # Update engineer profile
            await db.upsert_engineer(
                account_id, username,
                display_name=user.name or username,
                avatar_url=user.avatar_url
            )

            # --- Starred repos ---
            try:
                starred = user.get_starred()
                for repo in starred:
                    if repo.starred_at and repo.starred_at < cutoff:
                        break
                    if repo.starred_at is None:
                        continue
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

        except GithubException as e:
            print(f"[ingest] Error for {username}: {e}")
            continue
        except Exception as e:
            print(f"[ingest] Unexpected error for {username}: {e}")
            continue

        # Rate limit buffer
        await asyncio.sleep(0.5)

    final_score = min(int(total_score / max(signal_count, 1) * 10), 100)
    await db.update_account_meta(account_id, final_score)

    return {
        "signals": signal_count,
        "score": final_score,
        "engineers_processed": len(engineers)
    }
