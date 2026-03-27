import os
import json
import anthropic
from dotenv import load_dotenv
import database as db

load_dotenv()

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

BRIEFING_SYSTEM = """You are a sales intelligence analyst for Relevantz, a technology services company.
Your job is to analyze GitHub activity signals from engineers at target companies and generate 
concise, actionable sales intelligence briefings.

Focus on:
- What technologies the company appears to be evaluating or adopting
- Infrastructure or platform shifts that signal pain points or opportunities
- Specific services Relevantz could offer to help
- The urgency/priority level of these signals

Be specific, data-driven, and sales-focused. Use concrete observations from the signals.
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
  "tech_stack_signals": ["tech1", "tech2", "tech3"]
}"""

async def generate_briefing(account_id: int) -> dict:
    account = await db.get_account(account_id)
    if not account:
        raise ValueError("Account not found")

    signals = await db.get_signals(account_id, limit=100)
    if not signals:
        return {
            "summary": "No GitHub signals collected yet. Run a sync to gather data.",
            "key_themes": [],
            "opportunities": [],
            "friction_signals": [],
            "recommended_action": "Sync account to collect GitHub signals first.",
            "urgency": "low",
            "tech_stack_signals": []
        }

    # Build signal summary for Claude
    signal_lines = []
    for s in signals[:80]:  # Cap tokens
        topics_str = ", ".join(s.get("repo_topics", [])[:5]) if s.get("repo_topics") else ""
        lang = s.get("repo_language", "") or ""
        desc = (s.get("repo_description", "") or "")[:120]
        line = (
            f"- [{s['signal_type'].upper()}] {s['engineer_username']} → "
            f"{s['repo_name']} ({lang}) {desc} "
            f"{'[topics: ' + topics_str + ']' if topics_str else ''}"
        )
        signal_lines.append(line)

    signal_text = "\n".join(signal_lines)

    prompt = f"""Analyze these GitHub activity signals from engineers at {account['name']} 
and generate a sales intelligence briefing for Relevantz's sales team.

Company: {account['name']}
GitHub Org: {account.get('github_org', 'N/A')}
Account Type: {account.get('account_type', 'prospect')}
Signal Score: {account.get('signal_score', 0)}/100

GitHub Signals (last 30 days):
{signal_text}

Generate the briefing JSON now."""

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=BRIEFING_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.content[0].text.strip()
    # Strip markdown fences if present
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    briefing_data = json.loads(content)

    # Persist to DB as JSON string
    await db.save_briefing(account_id, json.dumps(briefing_data))

    return briefing_data
