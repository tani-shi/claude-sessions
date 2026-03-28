from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

from claude_sessions.display import format_session_line
from claude_sessions.sessions import filter_by_cwd, filter_by_entrypoint, load_sessions


def _pick_with_fzf(lines: list[str]) -> int | None:
    fzf = shutil.which("fzf")
    if not fzf:
        print("Error: fzf is required. Install with: brew install fzf", file=sys.stderr)
        sys.exit(1)

    input_text = "\n".join(f"{i}\t{line}" for i, line in enumerate(lines))
    result = subprocess.run(
        [
            fzf,
            "--ansi",
            "--no-sort",
            "--header", "Select a session to resume (type to search):",
            "--with-nth", "2..",
            "--delimiter", "\t",
            "--tabstop", "1",
            "--layout", "reverse",
        ],
        input=input_text,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    if not selected:
        return None
    return int(selected.split("\t", 1)[0])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive session picker for Claude Code",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="show all sessions (default: current directory only)",
    )
    parser.add_argument(
        "-e",
        "--entrypoint",
        nargs="+",
        default=["cli"],
        metavar="TYPE",
        help="filter by entrypoint type (default: cli). use 'all' to show all. supports prefix matching (e.g. 'sdk' matches sdk-cli, sdk-py)",
    )
    args = parser.parse_args()

    sessions = load_sessions()
    if "all" not in args.entrypoint:
        sessions = filter_by_entrypoint(sessions, args.entrypoint)
    if not args.all:
        sessions = filter_by_cwd(sessions, os.getcwd())

    sessions.sort(key=lambda s: s.started_at, reverse=True)

    if not sessions:
        if args.all:
            print("No sessions found.")
        else:
            print("No sessions found for current directory. Use -a/--all to see all sessions.")
        sys.exit(0)

    lines = [format_session_line(s) for s in sessions]
    index = _pick_with_fzf(lines)

    if index is None:
        sys.exit(0)

    selected = sessions[index]
    try:
        os.execvp("claude", ["claude", "--resume", selected.session_id])
    except FileNotFoundError:
        print(
            "Error: 'claude' command not found. Is Claude Code installed and on your PATH?",
            file=sys.stderr,
        )
        sys.exit(1)
