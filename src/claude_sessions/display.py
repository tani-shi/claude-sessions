from __future__ import annotations

from pathlib import Path

from claude_sessions.sessions import Session

HOME = str(Path.home())


def abbreviate_path(cwd: str) -> str:
    if cwd.startswith(HOME):
        return "~" + cwd[len(HOME):]
    return cwd


def format_session_line(session: Session) -> str:
    name = session.name or session.session_id[:8]
    short_path = Path(abbreviate_path(session.cwd)).name
    ts = session.updated_at.astimezone().strftime("%m/%d %H:%M")
    msg = session.first_message
    if len(msg) > 80:
        msg = msg[:77] + "..."
    return f"{ts} | {name} | {short_path} | {msg}"
