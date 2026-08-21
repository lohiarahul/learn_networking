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
import os, re, sys, glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE = os.path.join(REPO, "networking-fundamentals")

# ── Config ────────────────────────────────────────────────────────────────────
# Acts that must carry the full four-file shape (README + test-yourself + diagnose + in-the-wild).
ACT_DIRS = ["act-1-one-machine", "act-2-two-machines", "act-3-the-internet",
            "act-4-one-pretends-many", "act-5-kubernetes", "act-6-control-plane",
            "act-7-workloads"]
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
    deliberately not a lesson — `exam-prep/` is rehearsal for a timed test, which is
    banking by design and must never be held to the Predict-first / ladder invariants.
    Link integrity still applies to those files; only the lesson-shape rules don't.
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

HARD_CHECKS = [check_links, check_act_shape, check_prediction, check_ladder]
WARN_CHECKS = [check_index_freshness, check_map_vs_build]

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
