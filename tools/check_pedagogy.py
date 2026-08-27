#!/usr/bin/env python3
"""
check_pedagogy.py — enforce the learn_networking pedagogy as automatable invariants.

This is the deterministic half of the build harness (see tools/README.md). It gates the
STRUCTURAL rules that can be checked without judgement. The semantic rules — Spirit
("does this keep the reader's drive alive?"), River ("nothing flows uphill"), and whether
an experiment's feedback loop actually lands — are deliberately NOT regex-gated here,
because lexical checks produce false positives on exactly the best-written lessons. Those
are the learner-simulator agent's job.

Exit code 0 = all hard checks pass. Non-zero = at least one hard failure.
Warnings never fail the build; they surface drift for a human to judge.

Usage:
    python3 tools/check_pedagogy.py                 # check the whole course
    python3 tools/check_pedagogy.py <file.md> ...   # check only these files (save-time hook)
    python3 tools/check_pedagogy.py --warn-only     # never exit non-zero (report mode)
"""
from __future__ import annotations
import os, re, sys, glob, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE = os.path.join(REPO, "networking-fundamentals")

# ── Config ────────────────────────────────────────────────────────────────────
# Acts that must carry the full four-file shape (README + test-yourself + diagnose + in-the-wild).
ACT_DIRS = ["act-1-one-machine", "act-2-two-machines", "act-3-the-internet",
            "act-4-one-pretends-many", "act-5-kubernetes", "act-6-control-plane",
            "act-7-workloads",
            "act-8-trust", "act-9-identity", "act-10-cluster-security"]
# No exemptions: every act carries the full four-file shape. Act V used to fold its drills into
# 08/09-debugging, but those are a method and a worked example — the reader receives the diagnosis
# rather than reaching for it — so Act V now has a real diagnose.md and the invariant is enforced
# everywhere. Re-adding an act here means the site promises drills it does not have.
DIAGNOSE_EXEMPT = set()

# A "lesson" is a numbered teaching file (NN- or NNx-). These are exempt from has-prediction
# because they are setup/orientation/method pages, not experiment-driven lessons.
PREDICTION_EXEMPT = {
    "00-orientation/01-what-is-a-process.md",     # orientation framing
    "00-orientation/02-how-processes-communicate.md",
    "act-1-one-machine/06b-the-container-filesystem.md",  # optional side-road
    "act-5-kubernetes/01-lab-with-kind.md",       # lab setup
    "act-5-kubernetes/08-debugging.md",           # the method itself (09 applies it)
}

PREDICTION_MARKERS = ["predict first", "predict —", "predict:", "predict, then"]
# A lesson must end its ladder rung: a milestone marker AND a forward pointer.
MILESTONE_MARKERS = ["you can now", "where you are now", "where this leaves",
                     "you understand this when"]
FORWARD_MARKERS = ["next:", "→"]

# ── Helpers ─────────────────────────────────────────────────────────────────
LINK_RE = re.compile(r"\]\(([^)]+)\)")
LESSON_RE = re.compile(r"\d\d[a-z]?-")

def is_lesson(path):
    """A lesson is a numbered teaching file *inside the course*.

    The distinction matters because the repo also carries numbered Markdown that is
    deliberately not a lesson, and there are now two such directories:

    - `exam-prep/` is rehearsal for a timed test, which is banking by design.
    - `reference/` is the instrument panel — lookup tables and naming grammar, consulted
      after the learning rather than during it. A `/proc` path table with a "Predict
      first" block would be incoherent.

    Both must never be held to the Predict-first / ladder invariants. Link integrity still
    applies to them, and does real work in `reference/`: every "taught in" citation there is
    a relative link, so a renamed lesson breaks the build instead of leaving a lie in a table.
    """
    if not LESSON_RE.match(os.path.basename(path)):
        return False
    return not os.path.relpath(os.path.abspath(path), COURSE).startswith(os.pardir)
FENCED_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")

def strip_code(text):
    # Markdown links never live inside code — strip fenced blocks and inline spans first,
    # so a doc/lesson that *shows* `](example.md)` as an example isn't a false positive.
    return INLINE_CODE_RE.sub("", FENCED_RE.sub("", text))

def rel(p): return os.path.relpath(p, REPO)
def read(p): return open(p, encoding="utf-8", errors="replace").read()
def has(text, markers):
    low = text.lower()
    return any(m in low for m in markers)

# Directories that hold generated or vendored Markdown, not course source. site/src/content/docs is a
# projection of networking-fundamentals/ built by site/scripts/sync-content.mjs — its links are already
# rewritten to site URLs, so checking them here would report every one of them as broken.
EXCLUDED_DIRS = ("site/node_modules", "site/dist", "site/src/content/docs", "node_modules")

def all_md():
    files = glob.glob(os.path.join(REPO, "**", "*.md"), recursive=True)
    return sorted(f for f in files if not rel(f).startswith(EXCLUDED_DIRS))

def lesson_files():
    out = []
    for f in glob.glob(os.path.join(COURSE, "*", "*.md")):
        if LESSON_RE.match(os.path.basename(f)):
            out.append(f)
    return sorted(out)

# ── Checks (return list of (level, message)) ────────────────────────────────
def check_links(files):
    issues = []
    for f in files:
        d = os.path.dirname(f)
        for t in LINK_RE.findall(strip_code(read(f))):
            t = t.strip()
            if t.startswith(("http", "#", "mailto")):
                continue
            path = t.split("#")[0]
            if path and not os.path.exists(os.path.join(d, path)):
                issues.append(("FAIL", f"broken link: {rel(f)} -> {t}"))
    return issues

def check_act_shape(_files):
    issues = []
    need = ["README.md", "test-yourself.md", "diagnose.md", "in-the-wild.md"]
    for a in ACT_DIRS:
        for fn in need:
            if fn == "diagnose.md" and a in DIAGNOSE_EXEMPT:
                continue
            if not os.path.exists(os.path.join(COURSE, a, fn)):
                issues.append(("FAIL", f"act-shape: {a} is missing {fn}"))
    return issues

def check_prediction(files):
    issues = []
    for f in files:
        r = os.path.relpath(f, COURSE)
        if not is_lesson(f):
            continue
        if r in PREDICTION_EXEMPT:
            continue
        if not has(read(f), PREDICTION_MARKERS):
            issues.append(("FAIL", f"no 'Predict first' in lesson: {rel(f)} "
                                   f"(add one, or add to PREDICTION_EXEMPT if it's setup)"))
    return issues

def check_ladder(files):
    issues = []
    for f in files:
        if not is_lesson(f):
            continue
        t = read(f)
        if not has(t, MILESTONE_MARKERS):
            issues.append(("FAIL", f"ladder: no milestone ('you can now'/'you understand this "
                                   f"when'/…) in {rel(f)}"))
        if not has(t, FORWARD_MARKERS):
            issues.append(("FAIL", f"ladder: no forward pointer ('Next:' link) in {rel(f)}"))
    return issues

MILESTONE_MAX_WORDS = 100

def check_milestone_length(files):
    """A milestone block must stay a *check*, not become a recap of the lesson.

    `check_ladder` above asserts the block exists. Nothing asserted it was still short, and one
    had quietly become a table of contents: `act-10/04-deciding-before-it-exists.md` carried 18
    bullets and 475 words, in a course where every other milestone is prose. A reader cannot
    self-assess against 18 claims — they skim it, which is the same outcome as not having one.

    The threshold is measured, not chosen. Across the 90 milestone blocks in the course the
    median is 74 words and the maximum is 86: the distribution stops dead just short of a
    ninety-word ceiling nobody wrote down. 100 sits above every block that exists, with enough
    headroom that a legitimate edit does not trip it, and still catches a block five times the
    norm. If a lesson genuinely needs more, the surplus is a summary and wants its own heading.

    Applies to any Markdown under the course, not just numbered lessons: `the-whole-stack.md`
    carries a milestone too, and it is exactly the kind of long capstone page that would drift.
    """
    issues = []
    for f in files:
        if os.path.relpath(os.path.abspath(f), COURSE).startswith(os.pardir):
            continue
        lines = read(f).split("\n")
        i = 0
        while i < len(lines):
            if not (lines[i].startswith(">") and has(lines[i], MILESTONE_MARKERS)):
                i += 1
                continue
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            words = len(" ".join(block).split())
            if words > MILESTONE_MAX_WORDS:
                issues.append(("FAIL", f"milestone block is {words} words (max "
                                       f"{MILESTONE_MAX_WORDS}, course median 74) in {rel(f)} "
                                       f"— cut it to a check, or give the summary its own heading"))
    return issues

def check_index_freshness(_files):
    # Warning-only: every lesson basename should be findable in LESSON-INDEX.md.
    # Tolerates the range notation Act V uses (e.g. "01-lab-with-kind … 09-…").
    issues = []
    idx_path = os.path.join(REPO, "LESSON-INDEX.md")
    if not os.path.exists(idx_path):
        return [("WARN", "LESSON-INDEX.md not found")]
    idx = read(idx_path)
    for f in lesson_files():
        base = os.path.basename(f)
        stem = base.replace(".md", "")
        if base not in idx and stem not in idx:
            issues.append(("WARN", f"index-freshness: {base} not referenced in LESSON-INDEX.md"))
    return issues

def check_map_vs_build(_files):
    # Warning-only: any stage the JOURNEY-MAP presents must be reconcilable with what's built.
    # We only assert the roadmap banner exists, so unbuilt stages are flagged honestly.
    jm = os.path.join(REPO, "JOURNEY-MAP.md")
    if not os.path.exists(jm):
        return [("WARN", "JOURNEY-MAP.md not found")]
    t = read(jm).lower()
    if "roadmap" not in t and "not yet written" not in t and "what's built" not in t:
        return [("WARN", "map-vs-build: JOURNEY-MAP.md advertises stages but has no "
                         "'what's built / roadmap' banner — unbuilt stages may read as built")]
    return []


REFERENCE = os.path.join(REPO, "reference")

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

# ── The index's two facets ──────────────────────────────────────────────────
# The roster classifies every tool by the kernel interface it speaks and by what it can
# do to the world. Both vocabularies are deliberately *closed*, because an open one is a taxonomy that
# quietly stops partitioning anything. These are the values; a cell outside them is the bug.
INTERFACES = {"netlink", "procfs", "socket", "packet", "probe", "nsapi", "httpapi", "local"}
MODES = {"read-only", "mutate", "live"}

# The roster, and the interface page that leads each tool directory. One constant rather than the
# four hard-coded copies this file used to carry, because a checker whose path has gone stale does
# not complain — it passes, which is the worst of the available behaviours.
TOOLS_DIR = os.path.join(REFERENCE, "tools")
INDEX_MD = os.path.join(TOOLS_DIR, "README.md")
IFACE_MD = {i: os.path.join(TOOLS_DIR, i, "README.md") for i in INTERFACES}


def check_reference_shape(_files):
    """Hard: the reference's own files exist where the checkers below expect them.

    This is the guard on the guards. Three of the checks in this file — the facet vocabularies, the
    supersession compartment, the SHELL_COMMANDS cross-reference — read the roster by path, and
    every one of them used to hold its own copy of that path and skip quietly if the file was not
    there. So a rename anywhere in `reference/` disabled them *without failing anything*: the run
    went green while nothing was being checked. That is the one failure mode a checker must not
    have, and it is why this is a hard check rather than a warning.
    """
    missing = [p for p in [INDEX_MD, *IFACE_MD.values()] if not os.path.exists(p)]
    return [("FAIL", f"reference-shape: {rel(p)} is missing — the reference has been "
                     f"restructured and the checks that read it are no longer checking anything")
            for p in missing]


def page_slug(tool):
    """`ip netns` -> `ip-netns`. The same transform `tools/gen-tool-pages.py` names the file with;
    duplicated rather than imported because that script is not an importable module (the hyphen in
    its name), and three lines of regex is a cheaper fix than renaming it."""
    return re.sub(r"[^a-z0-9]+", "-", tool.lower()).strip("-")


def check_iface_rosters(_files):
    """Warning-only: each interface page must name exactly the tools the roster gives it.

    `reference/tools/netlink/README.md` is both the netlink page and the landing page for the
    thirteen tool pages in that directory, and it opens with the list of them. That list is
    hand-written, so it is the kind of thing that is correct on the day it is typed and wrong two
    tools later — and it is now the *only* place a reader is offered the siblings of a tool, since
    the per-page "Same interface" list was seventy-two copies of it.

    So it gets the same bidirectional treatment as the eight-interfaces summary on the roster: a
    tool the roster puts in this directory must be linked from the page, and the page may not link
    a tool the roster puts somewhere else. Both directions, or the summary is free to drift.
    """
    if not os.path.exists(INDEX_MD):
        return []
    rows = index_tool_rows(read(INDEX_MD))
    by_iface = {}
    for r in rows:
        iface = re.split(r"[·&]", r["Speaks"], maxsplit=1)[0].strip()
        names = re.findall(r"`([^`]+)`", r["Tool"])
        if iface in INTERFACES and names:
            # The *page*, not the name. A row like `` `xxd` / `base64` `` is one page under the
            # first name, and `` [`findmnt`](mount.md) `` is a correct link wearing an alias as its
            # label — so the comparison has to be over filenames, which is the thing that either
            # exists or does not.
            by_iface.setdefault(iface, set()).add(page_slug(names[0]))
    issues = []
    for iface, path in sorted(IFACE_MD.items()):
        if not os.path.exists(path):
            continue
        # Only links *into this directory* count as "this page lists that tool". The page also
        # links sideways to other interfaces and to lessons, and a cross-interface link is a
        # comparison, not a claim of membership — which the pattern gets for free by refusing a
        # target with a slash in it.
        body = read(path)
        listed = {t[:-3] for t in re.findall(r"\]\(([a-z0-9_.-]+\.md)\)", body)} - {"README"}
        actual = by_iface.get(iface, set())
        for m in sorted(actual - listed):
            issues.append(("WARN", f"iface-roster: `{m}` speaks {iface} on the roster but "
                                   f"{rel(path)} does not link it"))
        for e in sorted(listed - actual):
            issues.append(("WARN", f"iface-roster: {rel(path)} links `{e}`, which the roster "
                                   f"does not place in {iface}"))
    return issues

def index_tool_rows(text):
    """Yield the data rows of the index's *topical* tables as dicts, keyed by column header.

    Table-aware on purpose. The page also carries summary tables whose first cell is a code span
    (`| `netlink` | ip monitor · ss -E | …`), and a naive "row starts with a backtick" scan reads those
    interface names as tool names — which is exactly the false positive this function exists to avoid.
    A topical table is identified by having an `In the course` column; nothing else does.
    """
    cols, rows = None, []
    for line in text.split("\n"):
        st = line.strip()
        if not st.startswith("|"):
            cols = None
            continue
        cells = [c.strip() for c in st.strip("|").split("|")]
        if "In the course" in cells:
            cols = cells
            continue
        if cols is None or all(set(c) <= {"-", ":"} for c in cells) or len(cells) != len(cols):
            continue
        rows.append(dict(zip(cols, cells)))
    return rows

def check_index_facets(_files):
    """Warning-only: the index's `Speaks` column, the `mode` field, and the summaries built on both.

    Four drifts, all silent otherwise:

    1. A `Speaks` cell or a `mode` value outside its closed vocabulary — a typo, or a new interface
       invented in one row and nowhere else.
    2. The `Speaks` column and the *eight interfaces* summary table disagreeing about which tools speak
       what. This is the check that makes the taxonomy hold: a tool cannot be added without being
       placed, which is how every tool taxonomy eventually dies.
    3. The counts asserted in prose (`13 + 14 + … = 72`, and "22 of the 72 tools can stream") not
       matching what they describe.
    4. Every roster row having a `name` and a `mode` in `capabilities.json`, and no orphan entry there
       naming a tool the roster does not list.

    `mode` is checked against the JSON rather than the roster because the roster no longer has that
    column — it came down to four so it would fit on a screen. Which makes the streaming claim a
    cross-file check now: the sentence lives on the roster, the evidence for it lives in the JSON, and
    the count has to reconcile.
    """
    issues = []
    # Skipping a missing roster is safe here — and only here — because `check_reference_shape`
    # is a hard check that reports it by name. Without that, this early return was the bug: the
    # file moved, this check quietly stopped running, and the suite stayed green. Reading it
    # unguarded is not the fix either, since the traceback kills the run before the failure that
    # explains it can be printed.
    if not os.path.exists(INDEX_MD):
        return issues
    text = read(INDEX_MD)
    rows = index_tool_rows(text)
    if not rows or "Speaks" not in rows[0]:
        return issues
    caps = {}
    if os.path.exists(CAPS_JSON):
        import json
        with open(CAPS_JSON) as f: caps = json.load(f)

    # 1. Closed vocabularies.
    by_iface, rows_by_iface, streams = {}, {}, set()
    for r in rows:
        tool = r["Tool"]
        iface = re.split(r"[·&]", r["Speaks"], maxsplit=1)[0].strip()
        if iface not in INTERFACES:
            issues.append(("WARN", f"index-facets: {tool} claims interface '{iface}', "
                                   f"not one of {sorted(INTERFACES)}"))
            continue
        # Two units, deliberately. The summary table names individual tools, so the set
        # comparison counts code spans (`ulimit` / `prlimit` is two). The arithmetic the page states is
        # over *rows*, because that is what the page says it is counting.
        by_iface.setdefault(iface, set()).update(re.findall(r"`([^`]+)`", tool))
        rows_by_iface[iface] = rows_by_iface.get(iface, 0) + 1
        tid = re.findall(r"`([^`]+)`", tool)[0]
        d = caps.get(tid)
        if d is None:
            issues.append(("WARN", f"index-facets: the roster lists {tool} and `capabilities.json` "
                                   f"has no entry for it, so it gets no page"))
            continue
        if "name" not in d:
            issues.append(("WARN", f"index-facets: `{tid}` has no `name` — the page title needs the "
                                   f"expansion, or an em dash to say there is not one"))
        modes = {m.strip() for m in d.get("mode", [])}
        if not modes:
            issues.append(("WARN", f"index-facets: `{tid}` has no `mode`, so its page cannot say "
                                   f"whether typing it can change anything"))
        bad = modes - MODES
        if bad:
            issues.append(("WARN", f"index-facets: `{tid}` claims mode {sorted(bad)}, "
                                   f"not in {sorted(MODES)}"))
        if "live" in modes:
            streams.add(tool)
    listed = {re.findall(r"`([^`]+)`", r["Tool"])[0] for r in rows}
    for orphan in sorted(set(caps) - listed):
        issues.append(("WARN", f"index-facets: `capabilities.json` describes `{orphan}`, which the "
                               f"roster does not list — a page nothing links to"))

    # 2. The summary table must name exactly the tools the column classifies.
    for line in text.split("\n"):
        m = re.match(r"\| \*\*`(\w+)`\*\* \|", line.strip())
        if not m or m.group(1) not in INTERFACES:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        listed = set(re.findall(r"`([^`]+)`", cells[2]))
        actual = by_iface.get(m.group(1), set())
        for missing in sorted(actual - listed):
            issues.append(("WARN", f"index-facets: `{missing}` speaks {m.group(1)} in its row but is "
                                   f"absent from the eight-interfaces summary"))
        for extra in sorted(listed - actual):
            issues.append(("WARN", f"index-facets: the {m.group(1)} summary names `{extra}`, "
                                   f"which no row classifies as {m.group(1)}"))

    # 3. The arithmetic the page states about itself.
    sums = re.search(r"`((?:\d+ \+ )+\d+) = (\d+)`", text)
    if sums:
        parts = [int(x) for x in sums.group(1).split(" + ")]
        want = sorted(rows_by_iface.values(), reverse=True)
        if sorted(parts, reverse=True) != want or int(sums.group(2)) != len(rows):
            issues.append(("WARN", f"index-facets: the page states {sums.group(0)} but the columns give "
                                   f"{'+'.join(str(n) for n in want)} = {len(rows)}"))
    # `[^*]*` because the sentence on the page reads "can stream events", and an exact-phrase
    # regex here silently matched nothing for as long as it existed — the same failure mode
    # `check_reference_shape` guards paths against, one level down in the pattern.
    live = re.search(r"\*\*(\d+) of the (\d+) tools can stream[^*]*\*\*", text)
    if live and (int(live.group(1)) != len(streams) or int(live.group(2)) != len(rows)):
        issues.append(("WARN", f"index-facets: the page claims {live.group(1)} of {live.group(2)} tools "
                               f"stream; the `mode` fields give {len(streams)} of {len(rows)}"))
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

STANDING_LEVELS = {"default", "superseded", "emerging"}
SWAP_KINDS = {"rename", "reflag", "rewrite"}
# How long a tool gets to stay "emerging" before the verdict is re-read rather than inherited.
# Five years is roughly how long it takes a genuinely useful tool to reach a distro repository,
# which is the event that ends the claim.
EMERGING_YEARS = 5
CAPS_JSON = os.path.join(REPO, "reference", "capabilities.json")
LAB_JSON = os.path.join(REPO, "reference", "lab-inventory.json")

def check_standing(_files):
    """Warning-only: the `Standing` facet must stay a measurement, not an opinion.

    The facet answers "is this tool current, or am I only meeting it because other people's
    runbooks are full of it?" — which is worth having only if every non-default verdict names its
    evidence. So the shape is enforced:

      * the vocabulary is closed (default / superseded / emerging), like `Speaks` and `Mode`;
      * `superseded` must name a replacement that is itself on the roster — "superseded" with no
        successor is a complaint, not a fact;
      * `emerging` must carry a first-release year, and must *not* be installed in the lab image,
        because "you install it deliberately" is the claim the level makes;
      * every non-default verdict carries a rationale long enough to be an argument.

    Also checks that the measured inventory covers exactly the roster, so a tool added to
    capabilities.json without rerunning tools/probe-lab.py is caught rather than silently
    rendering as "not installed".
    """
    import json
    issues = []
    if not (os.path.exists(CAPS_JSON) and os.path.exists(LAB_JSON)):
        return [("WARN", "standing: capabilities.json or lab-inventory.json missing")]
    issues += check_standing_section()
    with open(CAPS_JSON) as f: caps = json.load(f)
    with open(LAB_JSON) as f: lab = json.load(f)
    inv = lab.get("tools", {})

    missing = sorted(set(caps) - set(inv))
    extra = sorted(set(inv) - set(caps))
    if missing:
        issues.append(("WARN", f"standing: lab-inventory.json has no measurement for "
                               f"{len(missing)} tool(s) ({', '.join(missing[:6])}) — "
                               f"rerun tools/probe-lab.py"))
    if extra:
        issues.append(("WARN", f"standing: lab-inventory.json measures {len(extra)} tool(s) no "
                               f"longer on the roster ({', '.join(extra[:6])})"))

    for tool in sorted(caps):
        st = caps[tool].get("standing")
        if not st:
            issues.append(("WARN", f"standing: `{tool}` has no standing facet"))
            continue
        lvl = st.get("level")
        if lvl not in STANDING_LEVELS:
            issues.append(("WARN", f"standing: `{tool}` has level {lvl!r}, outside the closed "
                                   f"vocabulary {sorted(STANDING_LEVELS)}"))
            continue
        if lvl == "default":
            continue
        why = st.get("why", "")
        if len(why) < 80:
            issues.append(("WARN", f"standing: `{tool}` is marked {lvl} with a "
                                   f"{len(why)}-character rationale — name the evidence"))
        if lvl == "superseded":
            by = st.get("by") or []
            if not by:
                issues.append(("WARN", f"standing: `{tool}` is superseded by nothing named"))
            for b in by:
                if b.split()[0] not in caps:
                    issues.append(("WARN", f"standing: `{tool}` is superseded by `{b}`, which is "
                                           f"not on the roster"))
            # "Superseded" without a migration cost is advice a reader cannot act on: whether the
            # swap is a rename, a relearn or a rewrite is the whole difference between "do it now"
            # and "schedule it". So the cost is required, and so is at least one worked rewrite.
            if st.get("swap") not in SWAP_KINDS:
                issues.append(("WARN", f"standing: `{tool}` is superseded with swap "
                                       f"{st.get('swap')!r}, outside {sorted(SWAP_KINDS)}"))
            instead = st.get("instead") or []
            if not instead:
                issues.append(("WARN", f"standing: `{tool}` is superseded with no `instead` "
                                       f"rewrites — name what to type instead"))
            for pair in instead:
                if not (isinstance(pair, list) and len(pair) == 2):
                    issues.append(("WARN", f"standing: `{tool}` has a malformed `instead` entry "
                                           f"{pair!r} — want [old, new]"))
                    continue
                old_cmd, new_cmd = pair
                # The left side must be this tool, or the row is telling you to stop using
                # something else; the right side must be a tool on the roster, or the reference
                # is sending you to a page that does not exist.
                if old_cmd.split()[0] != tool:
                    issues.append(("WARN", f"standing: `{tool}`'s `instead` row starts "
                                           f"`{old_cmd}`, which is not this tool"))
                if new_cmd.split()[0] not in caps:
                    issues.append(("WARN", f"standing: `{tool}`'s `instead` row points at "
                                           f"`{new_cmd}`, whose tool is not on the roster"))
        issues += check_evidence(tool, st, lab.get("evidence", {}).get(tool, []))
        # `gains` is the field that makes the verdict useful rather than merely disapproving:
        # what the reader gets, not what the reader loses. Required at both non-default levels.
        if len(st.get("gains", "")) < 60:
            issues.append(("WARN", f"standing: `{tool}` is marked {lvl} without saying what the "
                                   f"reader gains — that is a complaint, not a recommendation"))
        if lvl == "emerging":
            yr = st.get("since")
            if not (isinstance(yr, int) and 1990 <= yr <= 2100):
                issues.append(("WARN", f"standing: `{tool}` is emerging with since={yr!r} — "
                                       f"needs a four-digit first-release year"))
            if inv.get(tool, {}).get("present"):
                issues.append(("WARN", f"standing: `{tool}` is marked emerging but the lab image "
                                       f"now ships it — it has become a default"))
            # "Emerging" is a claim about *now* — new enough that you install it deliberately —
            # stored as a static year, which means it is the one facet guaranteed to rot: nothing
            # about `pwru` will change on its own, and in 2031 the page will still be calling a
            # ten-year-old tool new. The year stays in the page, because the year is a fact; the
            # judgement of whether it is still recent belongs here, where it can be re-read
            # against today rather than against the day someone typed it.
            elif isinstance(yr, int) and datetime.date.today().year - yr > EMERGING_YEARS:
                issues.append(("WARN", f"standing: `{tool}` is marked emerging but was first "
                                       f"released {yr}, "
                                       f"{datetime.date.today().year - yr} years ago — re-read "
                                       f"the verdict: still a deliberate install, or just "
                                       f"unpackaged?"))
    return issues

MAX_KEYS = 4

def key_literal(key):
    """The typable part of a `keys` entry. A flag is documented with its argument where that is
    how you meet it — `-e trace=<set>`, `-M do` — but the thing that has to appear in a command
    is the flag itself."""
    return re.split(r"[ <]", key, maxsplit=1)[0].strip()

def flag_used(key, cmds):
    """Is this flag actually typed in one of the commands on the tool's own page?"""
    lit = key_literal(key)
    for c in cmds:
        for tok in re.split(r"[\s|'\"]+", c):
            tok = tok.split("=", 1)[0].split(":", 1)[0]
            if tok == lit:
                return True
            # `dig` drives on `+trace` and `@1.1.1.1`, neither of which is a dash-flag.
            if lit[:1] in "+@" and tok.startswith(lit):
                return True
            # Short-flag bundling, because getopt permits it and this course uses it throughout:
            # `ss -i` is only ever typed as `ss -ti`, `ulimit -H` as `-Hn`, `nstat -z` as `-az`.
            if len(lit) == 2 and lit[0] == "-" and lit[1].isalnum() \
               and tok.startswith("-") and not tok.startswith("--") and lit[1] in tok[1:]:
                return True
    return False

def check_keys(_files):
    """Warning-only: the `keys` facet must name flags the page also demonstrates.

    The facet exists because `--help` sorts flags alphabetically and treats all forty as equals,
    which is the opposite of what a reader needs. The editorial rule is that a flag earns a line
    only when leaving it off gives you a different *answer* rather than a different format:
    `ip -d` is the only way an interface's kind appears at all, while `ip -j` is the same facts in
    JSON. So `-j`, `-br` and `jq`'s pretty-printer are in the capability tables and not here.

    Which makes the facet sparse on purpose. Roughly a third of the roster names nothing, because
    a tool driven by objects and subcommands — `bridge fdb show`, `wg show`,
    `socat TCP-LISTEN:8080,fork -` — has no flag that carries weight, and inventing one would
    bury the ones that do. Absence is a claim here, so it is not flagged.

    What is enforced:

      * every flag named must be typed in one of that tool's own commands, so the reader has a
        worked example rather than a flag they have to go and look up. This is the check that
        keeps the facet from drifting into a transcription of `--help`;
      * at most four, since a list of ten is the thing this facet exists to replace;
      * no duplicates, and a rationale long enough to say what changes rather than what the flag
        is called;
      * nothing on a superseded tool. That page's job is the swap table — it is telling the reader
        to stop typing this command, and a section on how to type it better fights the page.
    """
    import json
    issues = []
    if not os.path.exists(CAPS_JSON):
        return []
    with open(CAPS_JSON) as f: caps = json.load(f)
    for tool in sorted(caps):
        d = caps[tool]
        keys = d.get("keys")
        if not keys:
            continue
        if d.get("standing", {}).get("level") == "superseded":
            issues.append(("WARN", f"keys: `{tool}` is superseded and still names key flags — "
                                   f"that page's job is the swap table, not how to drive this one"))
        if len(keys) > MAX_KEYS:
            issues.append(("WARN", f"keys: `{tool}` names {len(keys)} flags, over the {MAX_KEYS} "
                                   f"this facet exists to cut down to"))
        seen = set()
        cmds = [c for _, cs in d.get("caps", []) for c, _ in cs] \
            + [c["cmd"] for c in d.get("course", [])]
        for k, why in keys:
            if k in seen:
                issues.append(("WARN", f"keys: `{tool}` names `{k}` twice"))
            seen.add(k)
            if len(why) < 40:
                issues.append(("WARN", f"keys: `{tool}` `{k}` has a {len(why)}-character "
                                       f"rationale — say what it changes, not what it is called"))
            if not flag_used(k, cmds):
                issues.append(("WARN", f"keys: `{tool}` names `{k}` as a flag that carries its "
                                       f"weight, but no command on its page types it — either "
                                       f"add the command or drop the flag"))
    return issues

def check_evidence(tool, st, measured):
    """Warning-only: a prose field that quotes in-image output must still produce that output.

    This is the gap the rest of `check_standing` cannot close. Everything above checks *shape* —
    that a level is in the vocabulary, that a successor is on the roster, that a rationale is long
    enough to be an argument. None of it can tell that `arp -6` no longer answers
    `unrecognized option: 6`, and a quoted string is the most convincing sentence on the page and
    the first to go stale: one `apk add net-tools` in the Dockerfile and the reference is
    confidently wrong with every check green.

    So the claim declares itself — `standing.evidence` names the field, the command and the
    string — and this check joins the two halves:

      * the quoted string must actually appear in the field that is said to quote it, so evidence
        cannot drift away from the prose it is evidence *for*;
      * `tools/probe-lab.py` must have re-run the command and found the string, so the prose
        cannot drift away from the image.

    The measurement itself lives in probe-lab, not here, because it needs Docker. What is checked
    here is that a measurement exists, is current, and says yes.
    """
    issues = []
    declared = st.get("evidence", [])
    by_cmd = {m["cmd"]: m for m in measured}
    for e in declared:
        field, cmd, expect = e.get("field"), e.get("cmd"), e.get("expect") or []
        if field not in st:
            issues.append(("WARN", f"evidence: `{tool}` measures {cmd!r} for field {field!r}, "
                                   f"which its standing does not have"))
            continue
        for x in expect:
            if x not in st[field]:
                issues.append(("WARN", f"evidence: `{tool}`'s `{field}` is said to quote {x!r} "
                                       f"but does not — the evidence has drifted from the claim"))
        m = by_cmd.get(cmd)
        if m is None:
            issues.append(("WARN", f"evidence: `{tool}` quotes the output of `{cmd}` but "
                                   f"lab-inventory.json has no measurement of it — rerun "
                                   f"tools/probe-lab.py"))
        elif not m.get("matched"):
            got = m.get("got", "")
            issues.append(("WARN", f"evidence: `{tool}`'s `{field}` quotes output the lab image "
                                   f"no longer produces — `{cmd}` now says {got!r}. The prose is "
                                   f"wrong, not the measurement"))
        elif m.get("expect") != expect:
            issues.append(("WARN", f"evidence: `{tool}`'s measurement of `{cmd}` was taken "
                                   f"against {m.get('expect')!r}, not the current "
                                   f"{expect!r} — rerun tools/probe-lab.py"))
    for cmd in by_cmd:
        if cmd not in {e.get("cmd") for e in declared}:
            issues.append(("WARN", f"evidence: lab-inventory.json measures `{cmd}` for `{tool}`, "
                                   f"which no longer claims it — rerun tools/probe-lab.py"))
    return issues


HARD_CHECKS = [check_links, check_reference_shape, check_act_shape, check_prediction,
               check_ladder, check_milestone_length]
SECTION_H2 = "## Six to stop reaching for, and two to start"


def check_standing_section():
    """Warning-only: the roster's supersession compartment must name exactly the non-default tools.

    The same bidirectional check `check_index_facets` runs on the interface summary, for the same
    reason: a summary that is allowed to fall behind the rows it summarises is worse than no
    summary, because a reader trusts it. So a tool marked superseded or emerging in
    capabilities.json must appear in the section, and the section must name nothing else.

    Only the *left-hand* superseded name is looked for — the section links successors too, and
    `ss` appearing there is not a claim that `ss` is legacy.
    """
    import json, re as _re
    if not os.path.exists(INDEX_MD):
        return []   # check_reference_shape has already failed the run
    text = read(INDEX_MD)
    if SECTION_H2 not in text:
        return [("WARN", f"standing-section: {rel(INDEX_MD)} has no {SECTION_H2!r} section — "
                         f"the roster no longer says which tools are legacy")]
    body = text.split(SECTION_H2, 1)[1].split("\n## ", 1)[0]
    with open(CAPS_JSON) as f:
        caps = json.load(f)
    want = {t for t, d in caps.items()
            if d.get("standing", {}).get("level", "default") != "default"}
    # Rows are `| [`ss`](…) | [`netstat`](…) | …`; the second cell holds the tool being retired,
    # and the emerging table's first cell holds the tool being recommended. A tool link from the
    # roster is `<interface>/<tool>.md`, since the roster now sits above those directories rather
    # than beside them — matched against the interface names so an ordinary prose link cannot pass
    # for a tool page.
    named = set(_re.findall(r"\[`([a-z0-9_.-]+)`\]\((?:" + "|".join(INTERFACES) + r")/", body))
    missing = sorted(want - named)
    if missing:
        issues = [("WARN", f"standing-section: {', '.join(missing)} marked non-default in "
                           f"capabilities.json but absent from {SECTION_H2!r}")]
    else:
        issues = []
    return issues


ILLUSTRATIONS = os.path.join(REPO, "illustrations")
MANIFEST_MD = os.path.join(ILLUSTRATIONS, "MANIFEST.md")
NOT_PLACED_H2 = "## Not placed"
# Directories under illustrations/ that hold artwork. The generator and its PNG proof sheets do not.
ART_DIR_RE = re.compile(r"^\d\d-[a-z0-9-]+$")


def check_illustration_placement(_files):
    """Warning-only, bidirectional: MANIFEST's 'Not placed' list must equal what is measurably unplaced.

    45 of the 83 illustrations sit on no lesson, and that is a deliberate reserve rather than a defect
    — the topics are ones this course does not teach, and `MANIFEST.md` says so per file and explains
    why placing on a keyword would contradict the page. AUDIT.md §F recommended deleting or annexing
    them; that was declined, because they are deterministic output of a generator the 38 *placed*
    images need anyway, and the only page that serves them is a noindex contributor gallery.

    What the reserve does need is this check. A hand-written list of what is unused goes stale the
    first time somebody places one, and then it is actively misleading — the same failure mode
    `check_index_facets` and `check_standing_section` guard against. So both directions are asserted:
    every file the manifest calls unplaced must really be unreferenced, and every unreferenced file
    must be named there.
    """
    if not os.path.exists(MANIFEST_MD):
        return [("WARN", "illustrations: MANIFEST.md not found")]
    text = read(MANIFEST_MD)
    if NOT_PLACED_H2 not in text:
        return [("WARN", f"illustrations: MANIFEST.md has no {NOT_PLACED_H2!r} section — the reserve "
                         f"is no longer inventoried")]
    body = text.split(NOT_PLACED_H2, 1)[1]
    claimed = set(re.findall(r"`(\d\d-[a-z0-9-]+/[a-z0-9-]+\.svg)`", body))

    # A lesson references an illustration relatively; the site rewrites those at sync time. So the
    # question is only ever "does any prose file name this basename".
    prose = [f for f in all_md() if not rel(f).startswith(("illustrations/", "AUDIT"))]
    named = set()
    for f in prose:
        named.update(re.findall(r"([a-z0-9-]+\.svg)", read(f)))

    measured = set()
    for d in sorted(os.listdir(ILLUSTRATIONS)):
        if not ART_DIR_RE.match(d):
            continue
        for fn in sorted(os.listdir(os.path.join(ILLUSTRATIONS, d))):
            if fn.endswith(".svg") and fn not in named:
                measured.add(f"{d}/{fn}")

    issues = []
    stale = sorted(claimed - measured)
    if stale:
        issues.append(("WARN", f"illustration-placement: MANIFEST lists {len(stale)} file(s) as "
                               f"unplaced that a lesson now uses — {', '.join(stale[:4])}"
                               f"{' …' if len(stale) > 4 else ''}"))
    absent = sorted(measured - claimed)
    if absent:
        issues.append(("WARN", f"illustration-placement: {len(absent)} unplaced file(s) missing from "
                               f"MANIFEST's {NOT_PLACED_H2!r} list — {', '.join(absent[:4])}"
                               f"{' …' if len(absent) > 4 else ''}"))
    return issues


WARN_CHECKS = [check_index_freshness, check_map_vs_build, check_command_table_coverage,
               check_index_facets, check_iface_rosters, check_runnable_citations, check_standing,
               check_keys,
               check_illustration_placement]

# ── Runner ──────────────────────────────────────────────────────────────────
def main(argv):
    warn_only = "--warn-only" in argv
    args = [a for a in argv if not a.startswith("--")]
    if args:
        files = [os.path.abspath(a) for a in args if a.endswith(".md")]
        scoped = True
    else:
        files = all_md()
        scoped = False

    issues = []
    for chk in HARD_CHECKS:
        issues += chk(files)
    # Warning checks always run course-wide (they reason about the whole set).
    if not scoped:
        for chk in WARN_CHECKS:
            issues += chk(files)

    fails = [m for lvl, m in issues if lvl == "FAIL"]
    warns = [m for lvl, m in issues if lvl == "WARN"]

    for m in fails: print(f"  ✗ FAIL  {m}")
    for m in warns: print(f"  ⚠ warn  {m}")

    scope = f"{len(files)} file(s)" if scoped else "whole course"
    if not fails and not warns:
        print(f"✓ pedagogy checks pass ({scope})")
    else:
        print(f"\n{len(fails)} failure(s), {len(warns)} warning(s) over {scope}")

    return 0 if (warn_only or not fails) else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
