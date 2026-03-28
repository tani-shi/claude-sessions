# claude-sessions

Interactive session picker and resumer for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Browse, search, and resume past Claude Code sessions from your terminal using [fzf](https://github.com/junegunn/fzf).

## Features

- List sessions for the current directory, or all sessions with `-a`
- Filter by entrypoint type with `-e` (default: `cli`, supports prefix matching)
- Fuzzy search across session names, project paths, dates, and first messages
- Instantly resume a selected session via `claude --resume`
- Zero Python dependencies — only requires `fzf` as a system tool

## Requirements

- Python 3.10+
- [fzf](https://github.com/junegunn/fzf)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

## Installation

```bash
# With uv (recommended)
uv tool install git+https://github.com/tani-shi/claude-sessions

# Or clone and install locally
git clone https://github.com/tani-shi/claude-sessions.git
cd claude-sessions
uv tool install .
```

## Usage

```bash
# Show sessions for the current directory
claude-sessions

# Show all sessions (most recently updated first)
claude-sessions -a

# Show SDK sessions (matches sdk-cli, sdk-py, etc.)
claude-sessions -e sdk

# Show all entrypoints
claude-sessions -e all

# Help
claude-sessions -h
```

Each session is displayed as a single line:

```
03/28 15:06 | my-feature | my-project | Add authentication to the API...
03/28 14:30 | bugfix-auth | my-project | Fix login redirect loop when...
03/27 09:15 | a1b2c3d4   | other-proj | Refactor database connection...
```

Format: `last updated | session name (or ID) | project directory | first message`

Select a session with fzf and it will immediately resume via `claude --resume`.

## How it works

Claude Code stores conversation history as JSONL files under `~/.claude/projects/`. This tool scans those files to extract session metadata (last updated timestamp, working directory, first user message) and correlates session names from `~/.claude/sessions/` when available. Short-lived sub-agent sessions are automatically filtered out.
