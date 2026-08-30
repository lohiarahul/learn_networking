"""The command reference, and the two places a runnable claim can quietly stop being one.

Moved verbatim from `tools/check_pedagogy.py` — the bodies are unchanged, so the
parity test in `tools/harness/selftest.py` can prove the move changed no behaviour.
"""
from __future__ import annotations
import os, re
from ..corpus import all_md, read
from ..parsing import index_tool_rows
from ..paths import INDEX_MD, REFERENCE, REPO, rel


def check_command_table_coverage(_files):
    """Warning-only: the hand-written half of the command reference, and the site's fence classifier.

    Two drifts this catches, both silent otherwise:

    1. A row in `reference/05-per-act-commands.md` whose *Syntax breakdown* cell is empty. That is the
       intended state for a freshly generated row (`tools/gen-command-tables.py` emits them blank), so
       it is a warning rather than a gate — but an empty cell that survives a few commits is a command
       the reference lists and does not explain.
    2. A tool named in the roster that `site/scripts/sync-content.mjs`'s
       `SHELL_COMMANDS` set does not know. That set decides which bare fences render as shell on the
       site, so a tool missing from it gets documented here as runnable and rendered there as flat
       plaintext — the two lists have to move together.
    """
    issues = []

    page = os.path.join(REFERENCE, "05-per-act-commands.md")
    if os.path.exists(page):
        blank = 0
        for line in read(page).split("\n"):
            st = line.strip()
            # A data row, not the header or the `|---|---|` rule.
            if not st.startswith("| `") or "---" in st:
                continue
            cells = [c.strip() for c in st.strip("|").split("|")]
            if len(cells) >= 2 and not cells[1]:
                blank += 1
        if blank:
            issues.append(("WARN", f"command-table-coverage: {blank} command row(s) in "
                                   f"reference/05-per-act-commands.md have no syntax breakdown"))

    sync = os.path.join(REPO, "site", "scripts", "sync-content.mjs")
    if os.path.exists(INDEX_MD) and os.path.exists(sync):
        m = re.search(r"const SHELL_COMMANDS = new Set\(`(.*?)`", read(sync), re.DOTALL)
        if m:
            known = set(m.group(1).split())
            named = set()
            for row in index_tool_rows(read(INDEX_MD)):
                for span in re.findall(r"`([^`]+)`", row["Tool"]):
                    tool = span.split()[0]
                    if re.fullmatch(r"[a-z0-9_.-]+", tool):
                        named.add(tool)
            missing = sorted(named - known)
            if missing:
                issues.append(("WARN", f"command-table-coverage: in {rel(INDEX_MD)} but not in "
                                       f"sync-content.mjs SHELL_COMMANDS (fences will render as "
                                       f"plaintext): {', '.join(missing)}"))
    return issues


MAN_CMD_RE = re.compile(r"`man\s+[0-9n]?\s*[a-z0-9_.-]+`|^\s*man\s+[0-9n]?\s*[a-z0-9_.-]+\s*$",
                        re.MULTILINE)


def check_runnable_citations(_files):
    """Warning-only: nothing should read as `man <page>`, because the lab image has no man pages.

    The lab image is built FROM nicolaka/netshoot (Alpine): `man` is not installed and
    /usr/share/man is empty, so a reader who follows `man 8 ip` gets `sh: man: not found`. A
    citation is still worth making — it just has to be written in a form that does not look like
    a command you can run here. Two accepted forms:

      * the reference form, `ip(8)` / `unshare(2)`, for provenance; and
      * an in-image equivalent, `ip help` / `ss --help` / `<tool> -V`, for instruction.

    Sometimes the man page really is the instruction — Act X sends the reader to `man 5 apparmor.d`
    on the *exam* machine, which is a different machine and does have it. Those lines carry an
    explicit `<!-- man-ok: why -->` marker, so the exception is stated rather than assumed.

    Warning rather than failure: a page may have a reason to name the command itself, and this
    cannot tell that apart from a dead citation on its own.
    """
    issues = []
    for f in all_md():
        for i, line in enumerate(read(f).splitlines(), 1):
            m = MAN_CMD_RE.search(line)
            if not m or "man-ok:" in line:
                continue
            issues.append(("WARN", f"runnable-citations: {rel(f)}:{i} cites {m.group(0).strip()} — "
                                   f"the lab image has no man pages. Use the `tool(8)` citation form, "
                                   f"or an in-image equivalent such as `tool help`"))
    return issues
