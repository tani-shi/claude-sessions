from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
SESSIONS_DIR = CLAUDE_DIR / "sessions"

MIN_SESSION_LINES = 7


@dataclass
class Session:
    session_id: str
    cwd: str | None
    updated_at: datetime
    name: str | None = None
    first_message: str = "(no message)"
    entrypoint: str | None = None
    jsonl_path: str | None = None

    @property
    def is_resumable(self) -> bool:
        """CLI sessions can be resumed; SDK sessions are view-only."""
        return self.entrypoint is None or self.entrypoint == "cli"


def _load_session_names() -> dict[str, str]:
    """Load session names from sessions/*.json (active sessions only)."""
    names: dict[str, str] = {}
    if not SESSIONS_DIR.is_dir():
        return names
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            sid = data.get("sessionId", "")
            name = data.get("name")
            if sid and name:
                names[sid] = name
        except (json.JSONDecodeError, OSError):
            continue
    return names


def _count_lines(path: Path, limit: int) -> int:
    """Count lines up to limit (for quick size check)."""
    count = 0
    try:
        with open(path) as f:
            for _ in f:
                count += 1
                if count >= limit:
                    return count
    except OSError:
        pass
    return count


def _extract_session_from_jsonl(path: Path) -> Session | None:
    """Extract session metadata and first user message from a JSONL file."""
    # Skip very short sessions (subagent / hook sessions)
    if _count_lines(path, MIN_SESSION_LINES) < MIN_SESSION_LINES:
        return None

    session_id = path.stem
    cwd: str | None = None
    updated_at: datetime | None = None
    first_message = "(no message)"
    entrypoint: str | None = None

    try:
        with open(path) as f:
            for raw_line in f:
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    continue

                # Get cwd and entrypoint from first entry that has them
                if not cwd and entry.get("cwd"):
                    cwd = entry["cwd"]
                if not entrypoint and entry.get("entrypoint"):
                    entrypoint = entry["entrypoint"]

                # Track the latest timestamp
                ts = entry.get("timestamp")
                if ts:
                    if isinstance(ts, str):
                        updated_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    elif isinstance(ts, (int, float)):
                        updated_at = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

                # Get first user message
                if (
                    first_message == "(no message)"
                    and entry.get("type") == "user"
                    and entry.get("message", {}).get("role") == "user"
                ):
                    content = entry["message"].get("content", "")
                    text = _extract_text(content)
                    if text:
                        first_message = _truncate(text, 80)
    except OSError:
        return None

    if not updated_at:
        return None

    return Session(
        session_id=session_id,
        cwd=cwd,
        updated_at=updated_at,
        first_message=first_message,
        entrypoint=entrypoint,
        jsonl_path=str(path),
    )


def _extract_text(content: str | list) -> str:
    raw = ""
    if isinstance(content, str):
        raw = content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                raw = block.get("text", "")
                break
    # Extract only <command-args> content if present (skill invocations)
    m = re.search(r"<command-args>(.*?)</command-args>", raw, re.DOTALL)
    if m:
        raw = m.group(1)
    text = raw.replace("\n", " ").strip()
    return re.sub(r"<[^>]+>", "", text).strip()


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def load_sessions() -> list[Session]:
    """Load all sessions from JSONL files in ~/.claude/projects/."""
    if not PROJECTS_DIR.is_dir():
        return []

    session_names = _load_session_names()
    sessions: list[Session] = []

    for jsonl_path in PROJECTS_DIR.glob("*/*.jsonl"):
        session = _extract_session_from_jsonl(jsonl_path)
        if session is not None:
            session.name = session_names.get(session.session_id)
            sessions.append(session)

    return sessions


def filter_by_cwd(sessions: list[Session], cwd: str) -> list[Session]:
    return [s for s in sessions if s.cwd == cwd]


def _entrypoint_matches(entrypoint: str | None, value: str) -> bool:
    """Check if an entrypoint matches a filter value using prefix matching.

    'sdk' matches 'sdk-cli' and 'sdk-py', but 'cli' does not match 'sdk-cli'.
    """
    if entrypoint is None:
        return value == "cli"  # pre-entrypoint sessions are treated as cli
    return entrypoint == value or entrypoint.startswith(value + "-")


def filter_by_entrypoint(sessions: list[Session], values: list[str]) -> list[Session]:
    return [
        s for s in sessions
        if any(_entrypoint_matches(s.entrypoint, v) for v in values)
    ]
