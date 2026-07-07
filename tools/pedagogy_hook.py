#!/usr/bin/env python3
"""
pedagogy_hook.py — PostToolUse hook entry point for the pedagogy linter.

Claude Code delivers PostToolUse events as JSON on stdin. This script pulls the edited file's
path out of that payload and, if it's a markdown file in the course, runs the deterministic
pedagogy checks on just that file. Non-zero exit surfaces the failures to the session.

Wire it in .claude/settings.json:
    { "hooks": { "PostToolUse": [ { "matcher": "Write|Edit",
        "hooks": [ { "type": "command",
                     "command": "python3 \"$CLAUDE_PROJECT_DIR/tools/pedagogy_hook.py\"" } ] } ] } }
"""
import json, os, subprocess, sys

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never block on a malformed event
    ti = payload.get("tool_input", {}) or {}
    path = ti.get("file_path") or ti.get("path") or ""
    if not path.endswith(".md"):
        return 0
    if "networking-fundamentals" not in path and not path.endswith(("README.md", "JOURNEY-MAP.md", "LESSON-INDEX.md")):
        return 0
    here = os.path.dirname(os.path.abspath(__file__))
    checker = os.path.join(here, "check_pedagogy.py")
    r = subprocess.run([sys.executable, checker, path], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out:
        print(out, file=sys.stderr)
    return r.returncode

if __name__ == "__main__":
    sys.exit(main())
