"""Budgets — nothing in this repo, the harness included, grows without a ceiling.

The harness this package replaced reached 970 lines and nineteen checks in one file. Nothing
stopped it, because nothing was watching, and the cost was not aesthetic: it held four separate
copies of the roster's path and said so in its own comments, having noticed that a rename
disabled three checks *without failing anything*. Size caused that. A file you cannot hold in
your head is a file whose duplication you cannot see.

So the harness applies a budget to itself. This module is the reason `capabilities.py` at 310
lines is visible as the next thing to split rather than the place the next 200 lines quietly go.

THRESHOLDS ARE MEASURED, NOT CHOSEN — the same method the milestone cap used (course maximum 86
words, ceiling set at 100):

* Harness modules: largest is 310 lines. Ceiling **350** — above everything that exists, with
  enough headroom that a legitimate edit does not trip it, and still catching a doubling.
* Lessons: 86 lessons, median 2,988 words, maximum 8,764. Ceiling **10,000** — the same ~15%
  headroom over the observed maximum that the milestone cap used.
"""
from __future__ import annotations
import glob, os

from ..corpus import lesson_files, read
from ..model import FAIL, WARN, Finding
from .. import paths
from ..paths import HARNESS, REPO, rel

MAX_MODULE_LINES = 350
MAX_LESSON_WORDS = 10_000


def check_module_budget(_files=None) -> list[Finding]:
    """No harness module may exceed MAX_MODULE_LINES. This is the anti-monolith invariant."""
    findings = []
    for path in sorted(glob.glob(os.path.join(HARNESS, "**", "*.py"), recursive=True)):
        n = len(read(path).split("\n"))
        if n > MAX_MODULE_LINES:
            findings.append(Finding(
                invariant="budget.harness-module-lines", severity=FAIL,
                message=(f"{rel(path)} is {n} lines (ceiling {MAX_MODULE_LINES}) — split it by "
                         f"concern before it becomes the monolith this package replaced"),
                path=rel(path), line=MAX_MODULE_LINES))
    return findings


def check_lesson_budget(_files=None) -> list[Finding]:
    """A lesson far past the course's own distribution is two lessons wearing one filename."""
    findings = []
    for path in lesson_files():
        n = len(read(path).split())
        if n > MAX_LESSON_WORDS:
            findings.append(Finding(
                invariant="budget.lesson-words", severity=WARN,
                message=(f"{rel(path)} is {n:,} words (ceiling {MAX_LESSON_WORDS:,}, course "
                         f"median 2,988) — consider splitting it, as the act's `NNb-` lessons do"),
                path=rel(path)))
    return findings


def check_declared_paths(_files=None) -> list[Finding]:
    """Every path `paths.py` names must exist — the guard on the guards, generalised.

    The monolith had this as `check_reference_shape` for four hard-coded roster paths. The reason
    it existed applies to *every* path the harness knows: a checker whose target has moved does
    not complain, it passes, and a green run that checked nothing is the worst available outcome.
    """
    findings = []
    for name in sorted(dir(paths)):
        if name.startswith("_") or name.isupper() is False:
            continue
        value = getattr(paths, name)
        candidates = value.values() if isinstance(value, dict) else [value]
        for cand in candidates:
            if not isinstance(cand, str) or not cand.startswith(REPO):
                continue
            if not os.path.exists(cand):
                findings.append(Finding(
                    invariant="budget.declared-path-exists", severity=FAIL,
                    message=(f"paths.{name} points at {rel(cand)}, which does not exist — every "
                             f"invariant reading it is now checking nothing"),
                    path=rel(paths.__file__)))
    return findings
