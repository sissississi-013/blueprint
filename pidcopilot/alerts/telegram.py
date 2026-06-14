"""NemoClaw Telegram bridge — TERSE notifications only.

Zero-egress discipline (build-plan §0b nit): only a short notification leaves the
box (to api.telegram.org). Diagram content / plant IP NEVER goes in the message.
In production this routes through NemoClaw's Telegram bridge; this direct sender
is the emergency parachute only.
"""
from __future__ import annotations

import httpx

from .. import config


def format_alert(revision: int, red_findings: list[dict], regressions: list[str]) -> str:
    """A terse, content-free notification. No tags of confidential equipment beyond
    what's needed to point the reviewer at the issue."""
    if not red_findings and not regressions:
        return f"Rev {revision}: review clean."
    lines = [f"Rev {revision}: {len(red_findings)} safety issue(s)."]
    for f in red_findings[:3]:
        lines.append(f"- {f.get('message')} ({f.get('standard_ref')})")
    for r in regressions[:2]:
        lines.append(f"- {r}")
    return "\n".join(lines)


def send(text: str) -> bool:
    """Best-effort send. Returns False if not configured (use the pane feed instead)."""
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        return False
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text},
            timeout=10.0,
        )
        return r.status_code == 200
    except Exception:
        return False
