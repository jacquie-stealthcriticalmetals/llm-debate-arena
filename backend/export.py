from datetime import datetime
from pathlib import Path

from backend.debate import DebateSession

EXPORTS_DIR = Path(__file__).parent.parent / "exports"


def generate_markdown(session: DebateSession) -> str:
    model_names = ", ".join(m.label for m in session.models)
    total_rounds = len(session.rounds)

    status_map = {
        "consensus": "Consensus reached",
        "timeout": "Timed out — no consensus",
        "max_rounds": "Max rounds reached — no consensus",
        "stopped": "Stopped by user",
        "error": "Error during debate",
    }
    outcome = status_map.get(session.status, session.status)

    lines = [
        f"# LLM Debate: {session.prompt[:80]}",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Models:** {model_names}  ",
        f"**Rounds:** {total_rounds}  ",
        f"**Outcome:** {outcome}  ",
        "",
        "## Original Prompt",
        session.prompt,
        "",
    ]

    for r in session.rounds:
        if r.round_number == 1:
            lines.append("## Round 1: Initial Responses")
        else:
            lines.append(f"## Round {r.round_number}: Debate")
        lines.append("")

        for resp in r.responses:
            lines.append(f"### {resp.model_label}")
            lines.append(resp.content)
            lines.append("")

    if session.consensus_summary:
        lines.append("## Consensus Summary")
        lines.append(session.consensus_summary)
        lines.append("")

    return "\n".join(lines)


def save_export(session: DebateSession) -> Path:
    EXPORTS_DIR.mkdir(exist_ok=True)
    md = generate_markdown(session)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"debate_{timestamp}_{session.id[:8]}.md"
    path = EXPORTS_DIR / filename
    path.write_text(md, encoding="utf-8")
    return path
