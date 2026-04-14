import os
import json
import anthropic
from dotenv import load_dotenv
import database as db

load_dotenv()

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

BRIEFING_SYSTEM = """You are a sales intelligence analyst specializing in K-12 EdTech procurement.
Your job is to analyze procurement signals from school districts — board meeting minutes, ESSA data,
state DOE initiatives, job postings, and news — and generate prescient, actionable intelligence
for EdTech sales teams.

Your edge is PRESCIENCE — infer what the district is about to buy before the RFP drops. Look for:
- Board budget approvals + IT job postings = active procurement window — vendors are being evaluated RIGHT NOW
- Vendor mentioned in board minutes + job posting for same role = pilot likely in progress — identify incumbent
- Strategic initiative + same-quarter budget approval = funded initiative — confirmed budget exists, not vaporware
- Multiple districts in the same state showing the same tech initiative = state-level mandate likely — pitch as compliance solution
- ESSER funds expiring + pain point in board minutes + IT hiring surge = emergency spend window — approach now
- Board RFP signal + state DOE initiative in same domain = externally driven mandate — timing is non-negotiable

Cross-reference signals to build hypotheses. A hypothesis needs at least 2 corroborating signals.
State confidence: HIGH (3+ signals), MEDIUM (2 signals), LOW (inference only).

Signal types you will see (format: [TYPE|CERTAINTY]):
- [BOARD_MINUTES_ITEM|CONFIRMED] = budget_approval or RFP extracted from board minutes
- [BOARD_MINUTES_ITEM|ACTIVE] = strategic_initiative or tech_initiative in board minutes
- [BOARD_MINUTES_ITEM|EVALUATING] = vendor_mention or pain_point in board minutes
- [ESSA_PROFILE|CONFIRMED] = district NCES profile (enrollment, Title I status, per-pupil spend)
- [STATE_INITIATIVE|ACTIVE] = state DOE news item — policy or mandate signal
- [JOB_POSTING|CONFIRMED] = EdTech-relevant job posting — district is spending money to hire
- [NEWS_MENTION|EVALUATING] = news article about the district or EdTech topic
- [PRESS_RELEASE|CONFIRMED] = official EdTech industry press release mentioning this district

CERTAINTY tiers: CONFIRMED = definitive action taken or funded; ACTIVE = in-progress initiative; EVALUATING = early signal/inference.

CROSS-REFERENCING RULES — elevate urgency when you see:
- ESSER funds expiring + board pain mention + IT job posting → "active procurement window — approach now"
- vendor_mention in board minutes + job posting for same role → "pilot likely in progress — identify incumbent and differentiate"
- strategic_initiative + budget_approval in same quarter → "funded initiative — confirmed budget exists"
- Multiple districts in same state showing same tech initiative → "state-level mandate likely — pitch as compliance solution"
- Job postings for LMS admin + board minutes mentioning curriculum platform → "LMS replacement cycle beginning"

Be specific and data-driven. Reference actual signal sources, dollar amounts, board dates, and job titles.
Format your response as JSON with this exact structure:
{
  "summary": "2-3 sentence executive summary of the procurement signals",
  "key_themes": ["theme1", "theme2", "theme3"],
  "opportunities": [
    {"title": "Opportunity title", "detail": "Why this is a sales opportunity and what to pitch"}
  ],
  "friction_signals": ["signal1", "signal2"],
  "recommended_action": "Specific next step for the EdTech sales team",
  "urgency": "high|medium|low",
  "tech_stack_signals": ["tech1", "tech2", "tech3"],
  "prescient_calls": [
    {
      "call": "Bold forward-looking prediction of what this district is about to procure",
      "confidence": "high|medium|low",
      "evidence": "2-3 specific signals that support this call"
    }
  ]
}"""


def _format_signal(s: dict) -> str:
    sig_type  = s["signal_type"].upper()
    source    = s.get("engineer_username", "")
    repo      = s.get("repo_name", "")
    desc      = (s.get("repo_description", "") or "")[:120]
    raw       = s.get("raw_data") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}

    certainty = raw.get("certainty", "evaluating").upper()
    type_tag  = f"{sig_type}|{certainty}"

    if sig_type == "BOARD_MINUTES_ITEM":
        sub       = raw.get("signal_subtype", "")
        vendor    = raw.get("vendor_name") or ""
        dollar    = raw.get("dollar_amount") or ""
        vendor_str = f" vendor={vendor}" if vendor else ""
        dollar_str = f" amount={dollar}" if dollar else ""
        return f"- [{type_tag}] {repo} → \"{desc}\"{vendor_str}{dollar_str}"

    if sig_type == "ESSA_PROFILE":
        enroll = raw.get("enrollment", "")
        return f"- [{type_tag}] NCES {raw.get('nces_id','')} enrollment={enroll}"

    if sig_type == "STATE_INITIATIVE":
        state = raw.get("state", source)
        return f"- [{type_tag}] {state} DOE → \"{desc}\""

    if sig_type == "JOB_POSTING":
        return f"- [{type_tag}] {source} → job: \"{raw.get('job_title', desc)}\""

    if sig_type in ("NEWS_MENTION", "PRESS_RELEASE"):
        category = raw.get("news_category", "general").upper()
        src_name = raw.get("source", repo)
        headline = (raw.get("headline", desc) or desc)[:120]
        return f"- [{type_tag}|{category}] {src_name} → \"{headline}\""

    return f"- [{type_tag}] {source} → {repo}: {desc}"


async def generate_briefing(account_id: int) -> dict:
    account = await db.get_account(account_id)
    if not account:
        raise ValueError("Account not found")

    signals = await db.get_signals(account_id, limit=300, per_engineer=40)
    if not signals:
        return {
            "summary": "No district signals collected yet. Run a Scan to gather data.",
            "key_themes": [],
            "opportunities": [],
            "friction_signals": [],
            "recommended_action": "Scan the district to collect procurement signals first.",
            "urgency": "low",
            "tech_stack_signals": [],
            "prescient_calls": []
        }

    signal_lines = [_format_signal(s) for s in signals[:80]]
    signal_text  = "\n".join(signal_lines)

    prompt = f"""Analyze these procurement signals from {account['name']} and generate a prescient EdTech sales intelligence briefing.

District: {account['name']}
District Domain: {account.get('district_domain', 'N/A')}
NCES ID: {account.get('nces_id', 'N/A')}
District Legal Name: {account.get('district_legal_name', 'N/A')}
Account Type: {account.get('account_type', 'prospect')}
Signal Score: {account.get('signal_score', 0)}/100
Total Signals: {len(signals)}

SIGNALS (last 60 days):
{signal_text}

Generate the briefing JSON now. Be bold in your prescient_calls — call the procurement before the RFP drops."""

    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
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
