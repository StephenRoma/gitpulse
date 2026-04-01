import os
import json
import anthropic
from dotenv import load_dotenv
import database as db

load_dotenv()

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

BRIEFING_SYSTEM = """You are a sales intelligence analyst for Relevantz, a technology services company.
Your job is to analyze GitHub activity signals, org issue boards, release cadences, and HackerNews mentions
from engineers at target companies and generate prescient, actionable sales intelligence briefings.

Your edge is PRECIENCE — infer what is about to happen before announcements. Look for:
- Multiple engineers starring the same replacement tool = quiet migration evaluation in progress
- Open org issues labeled migration/deprecation/security = forced adoption or compliance pressure
- Engineer commenting on bugs in Tool X while the org is releasing something new = pain driving change
- HackerNews mentions = external market pressure and candid sentiment not visible internally
- Release cadence shifts (major version bumps, prereleases stacking) = platform overhaul imminent

Cross-reference signals to build hypotheses. A hypothesis needs at least 2 corroborating signals.
State confidence: HIGH (3+ signals), MEDIUM (2 signals), LOW (inference only).

Signal types you will see (format: [TYPE|CERTAINTY]):
- [STAR|EVALUATING] = engineer starred an external repo (evaluating a tool)
- [FORK|ACTIVE] = engineer forked a repo (actively building with it)
- [NEW_REPO|CONFIRMED] = engineer created their own new repo (shipping something)
- [NEW_REPO|ACTIVE] = engineer forked and created a new repo
- [ISSUE_COMMENT|ACTIVE] = engineer commented on a high-value labeled issue (hitting pain)
- [ISSUE_COMMENT|EVALUATING] = engineer commented on a general issue
- [RELEASE|CONFIRMED] = org published a full release (shipping cadence signal)
- [RELEASE|EVALUATING] = org published a prerelease / beta
- [ORG_ISSUE|ACTIVE] = open issue on org's repos with migration/roadmap/security labels
- [ORG_ISSUE|EVALUATING] = open issue on org's repos (general)
- [HN_MENTION|EVALUATING] = org or engineers mentioned on HackerNews (external perception)
- [NEWS_MENTION|ACTIVE] = risk news (breach, layoff, lawsuit, outage) about the company
- [NEWS_MENTION|CONFIRMED] = financial or product news (earnings, acquisition, product launch)
- [NEWS_MENTION|EVALUATING] = general news mention
- [PRESS_RELEASE|CONFIRMED] = official company press release (BusinessWire / PRNewswire) — treat as authoritative
- [SEC_FILING|CONFIRMED] = SEC 8-K filing — major corporate event (M&A, executive change, data breach disclosure, material event)
- [REDDIT_BUZZ|EVALUATING] = community discussion on Reddit — candid unfiltered sentiment

CERTAINTY tiers: CONFIRMED = definitive shipping/building; ACTIVE = in-progress work; EVALUATING = early signal/inference.

CROSS-REFERENCING RULES — elevate urgency when you see these combinations:
- SEC 8-K (acquisition/M&A) + engineers evaluating a competitor tool → budget disruption imminent, engage immediately
- Risk news (breach, fine) + org_issue labeled security/compliance → forced vendor evaluation underway
- Press release (new product launch) + engineers starring related tools → integration work kickoff signal
- Financial news (earnings miss, cost-cutting) + tech_debt org issues → consolidation / platform simplification play
- Reddit negative sentiment + HN mentions + org issues → public pain creating internal pressure to change

Be specific, data-driven, sales-focused. Reference actual engineer names, repo names, labels, headlines, and filing dates.
Format your response as JSON with this exact structure:
{
  "summary": "2-3 sentence executive summary of the technology signals",
  "key_themes": ["theme1", "theme2", "theme3"],
  "opportunities": [
    {"title": "Opportunity title", "detail": "Why Relevantz should engage on this"}
  ],
  "friction_signals": ["signal1", "signal2"],
  "recommended_action": "Specific next step for the sales team",
  "urgency": "high|medium|low",
  "tech_stack_signals": ["tech1", "tech2", "tech3"],
  "prescient_calls": [
    {
      "call": "Bold forward-looking prediction (what is about to happen)",
      "confidence": "high|medium|low",
      "evidence": "2-3 specific signals that support this call"
    }
  ]
}"""


def _format_signal(s: dict) -> str:
    sig_type = s["signal_type"].upper()
    eng      = s.get("engineer_username", "")
    repo     = s.get("repo_name", "")
    lang     = s.get("repo_language", "") or ""
    desc     = (s.get("repo_description", "") or "")[:120]
    topics   = s.get("repo_topics", []) or []
    raw      = s.get("raw_data") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}

    certainty = raw.get("certainty", "evaluating").upper()
    type_tag  = f"{sig_type}|{certainty}"

    if sig_type == "ISSUE_COMMENT":
        labels = ", ".join(raw.get("labels", []))
        preview = (raw.get("comment_preview", "") or "")[:80]
        return f"- [{type_tag}] {eng} → {repo} (issue: \"{raw.get('issue_title','')[:80]}\" labels: {labels}) \"{preview}\""

    if sig_type in ("RELEASE",):
        tag  = raw.get("tag", "")
        name = raw.get("release_name", "")
        pre  = " [PRERELEASE]" if raw.get("prerelease") else ""
        body = (raw.get("body_preview", "") or "")[:80]
        return f"- [{type_tag}] {eng} → {repo} ({tag} {name}){pre} \"{body}\""

    if sig_type == "ORG_ISSUE":
        labels = ", ".join(raw.get("labels", []))
        body   = (raw.get("body_preview", "") or "")[:80]
        return f"- [{type_tag}] {eng} → {repo} issue#{raw.get('issue_number','')} \"{raw.get('issue_title','')[:80]}\" [{labels}] \"{body}\""

    if sig_type == "HN_MENTION":
        pts     = raw.get("points", 0)
        cmts    = raw.get("num_comments", 0)
        preview = (raw.get("text_preview", "") or "")[:80]
        return f"- [{type_tag}] {eng} → \"{desc}\" ({pts}pts, {cmts} comments) \"{preview}\""

    if sig_type in ("NEWS_MENTION", "PRESS_RELEASE"):
        category = raw.get("news_category", "general").upper()
        source   = raw.get("source", repo)
        headline = (raw.get("headline", desc) or desc)[:120]
        return f"- [{type_tag}|{category}] {source} → \"{headline}\""

    if sig_type == "SEC_FILING":
        form     = raw.get("form_type", "8-K")
        company  = raw.get("company", eng)
        filed    = raw.get("filed_date", "")
        return f"- [{type_tag}] {company} filed {form} with SEC on {filed}"

    if sig_type == "REDDIT_BUZZ":
        subreddit = raw.get("subreddit", "")
        score_val = raw.get("score", 0)
        cmts      = raw.get("num_comments", 0)
        category  = raw.get("news_category", "general").upper()
        headline  = (raw.get("headline", desc) or desc)[:120]
        return f"- [{type_tag}|{category}] r/{subreddit} ({score_val}pts, {cmts} comments) \"{headline}\""

    topics_str = ", ".join(topics[:5])
    return (
        f"- [{type_tag}] {eng} → {repo} ({lang}) {desc} "
        f"{'[topics: ' + topics_str + ']' if topics_str else ''}"
    )


async def generate_briefing(account_id: int) -> dict:
    account = await db.get_account(account_id)
    if not account:
        raise ValueError("Account not found")

    signals = await db.get_signals(account_id, limit=300, per_engineer=40)
    if not signals:
        return {
            "summary": "No GitHub signals collected yet. Run a sync to gather data.",
            "key_themes": [],
            "opportunities": [],
            "friction_signals": [],
            "recommended_action": "Sync account to collect GitHub signals first.",
            "urgency": "low",
            "tech_stack_signals": [],
            "prescient_calls": []
        }

    signal_lines = [_format_signal(s) for s in signals[:80]]
    signal_text  = "\n".join(signal_lines)

    prompt = f"""Analyze these signals from engineers at {account['name']} and generate a prescient sales intelligence briefing.

Company: {account['name']}
GitHub Org: {account.get('github_org', 'N/A')}
Account Type: {account.get('account_type', 'prospect')}
Signal Score: {account.get('signal_score', 0)}/100
Total Signals: {len(signals)}

SIGNALS (last 30 days):
{signal_text}

Generate the briefing JSON now. Be bold in your prescient_calls — make the call before they announce it."""

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=BRIEFING_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.content[0].text.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    briefing_data = json.loads(content)
    if "prescient_calls" not in briefing_data:
        briefing_data["prescient_calls"] = []

    await db.save_briefing(account_id, json.dumps(briefing_data))
    return briefing_data
