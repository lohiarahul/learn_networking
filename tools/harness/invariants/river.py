"""River — nothing may hand the reader a tool they have not been given yet.

The monolith declined to check this, with a reason worth quoting: lexical checks "produce false
positives on exactly the best-written lessons." That is true of prose and false of *fenced
blocks*, and the gap between those two is what makes this invariant possible.

Measured on this repo while building it: counting inline code spans as uses produced 14 findings,
of which the two most interesting were `conntrack` in Act I 05b and `iptables` in Act III 02b —
both **deliberate seeds**, one of which reads "**Act IV builds it**" in the same sentence. The
monolith's warning was exactly right, and the fix is structural rather than semantic: a fenced
block is an instruction, an inline span is how you name a tool in a sentence. Only the first is
evidence the reader has been handed something. Fences-only took 14 findings to 8; resolving
lab-setup citations to their true position took 8 to 6.

Severity is WARN throughout. A forward reference can be intentional, and the honest way to hold
that is a declared exception with a reason attached, not a silent pass.
"""
from __future__ import annotations
import os

from ..corpus import LINK_RE, read, strip_code
from ..graph import PRE_COURSE, build
from ..model import WARN, Finding
from ..paths import COURSE, rel

# Utilities the course assumes rather than teaches. Each needs a reason, because an allowlist
# without reasons becomes a list of things nobody dared delete.
BASELINE: dict[str, str] = {
    "cat": "POSIX coreutil; the course assumes file reading from the first page",
    "pgrep": "POSIX process lookup; assumed alongside `ps`, which orientation introduces",
    "readlink": "POSIX coreutil; the /proc symlink reading it supports is the lesson, not the tool",
}

# Genuine forward references, declared: (tool, lesson-path-substring) -> why.
DECLARED_SEEDS: dict[tuple[str, str], str] = {
    ("nc", "00-orientation/02-how-processes-communicate.md"):
        "orientation is framing material, already exempt from Predict-first (see "
        "corpus.PREDICTION_EXEMPT). `nc -l` there opens a listening socket as a first look at "
        "'a socket is a file' — Act I 05b is where the TCP-state and SYN-scan mechanism `nc` "
        "sits inside is actually taught. Shallow use before deep use, not uphill flow.",
}


def check_river(_files=None) -> list[Finding]:
    g = build()
    findings: list[Finding] = []

    for tool in sorted(g.introduces):
        if tool in BASELINE:
            continue
        intro = g.introduces[tool]
        intro_order = g.intro_order[tool]
        for user in sorted(g.uses.get(tool, ())):
            if g.lessons[user].order >= intro_order:
                continue
            if any(k[0] == tool and k[1] in user for k in DECLARED_SEEDS):
                continue
            where = "lab setup" if intro == PRE_COURSE else intro
            findings.append(Finding(
                invariant="river.no-uphill-tool", severity=WARN,
                message=(f"`{tool}` is run in a fenced block in {user}, but the reference's "
                         f"earliest citation for it is {where} — so either the citation "
                         f"understates where it is taught, or this use is uphill. Fix the "
                         f"citation in capabilities.json, or declare the seed in "
                         f"river.DECLARED_SEEDS with a reason"),
                path=user))
    return findings


def check_course_citations(_files=None) -> list[Finding]:
    """Every `course[]` citation in capabilities.json must name a lesson that exists.

    Link integrity catches this for Markdown and cannot catch it for JSON, because a JSON string
    is not a link. A citation pointing at a renamed lesson is a lie in a table.
    """
    g = build()
    return [Finding(invariant="graph.course-citation-resolves", severity=WARN,
                    message=(f"capabilities.json: `{tool}` cites {act!r} / {lesson!r}, which "
                             f"resolves to no lesson file"),
                    path=rel(__file__))
            for tool, act, lesson in g.unresolved]


def check_lesson_reachable(_files=None) -> list[Finding]:
    """A lesson nothing links to is a lesson no reader arrives at."""
    g = build()
    linked: set[str] = set()
    for targets in g.cites.values():
        linked |= targets

    for act in sorted({l.act for l in g.lessons.values()}):
        readme = os.path.join(COURSE, act, "README.md")
        if not os.path.exists(readme):
            continue
        for t in LINK_RE.findall(strip_code(read(readme))):
            t = t.strip().split("#")[0]
            if t and not t.startswith(("http", "mailto")):
                linked.add(rel(os.path.normpath(os.path.join(os.path.dirname(readme), t))))

    return [Finding(invariant="graph.lesson-reachable", severity=WARN,
                    message=(f"{r} is linked from no README and no other lesson — a reader "
                             f"following the course has no route to it"), path=r)
            for r in sorted(g.lessons) if r not in linked]
