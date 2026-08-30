"""File access, cached, plus the markdown helpers every invariant shares.

The monolith re-globbed and re-read the tree inside each check — nineteen checks, nineteen
walks. Here the corpus is built once and handed to the invariants, which is what makes the
graph in `graph.py` affordable and keeps a full run under a second.
"""
from __future__ import annotations
import functools, glob, os, re

from .model import EXCLUDED_DIRS
from .paths import COURSE, REPO, rel

LINK_RE = re.compile(r"\]\(([^)]+)\)")
LESSON_RE = re.compile(r"\d\d[a-z]?-")
FENCED_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
FENCE_BLOCK_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


@functools.lru_cache(maxsize=None)
def read(p: str) -> str:
    return open(p, encoding="utf-8", errors="replace").read()


def strip_code(text: str) -> str:
    """Markdown links never live inside code — strip fenced blocks and inline spans first, so a
    page that *shows* `](example.md)` as an example is not a false positive."""
    return INLINE_CODE_RE.sub("", FENCED_RE.sub("", text))


def commands_only(text: str) -> str:
    """Only the *fenced* blocks — the things a reader actually runs.

    The distinction between a fenced block and an inline span is the whole ballgame for River,
    and getting it wrong reproduces the exact false positive the monolith warned about. Measured
    on this repo: counting inline spans as uses flagged `conntrack` in Act I 05b and `iptables`
    in Act III 02b, and both are *deliberate seeds* — Act III 02b's sentence reads "**Act IV
    builds it**". Those are the best-written passages in the act, flagged for being well written,
    which is precisely the failure mode that made the previous harness give up on River.

    A fenced block is an instruction. An inline span is how you name a tool in a sentence. Only
    the first is evidence that the reader has been handed the tool.
    """
    return "\n".join(FENCE_BLOCK_RE.findall(text))


def has(text: str, markers) -> bool:
    low = text.lower()
    return any(m in low for m in markers)


def is_lesson(path: str) -> bool:
    """A lesson is a numbered teaching file *inside the course*.

    The repo also carries numbered Markdown that is deliberately not a lesson: `exam-prep/` is
    rehearsal for a timed test, which is banking by design, and `reference/` is the instrument
    panel, consulted after the learning rather than during it. Neither may be held to the
    Predict-first or ladder invariants. Link integrity still applies to both.
    """
    if not LESSON_RE.match(os.path.basename(path)):
        return False
    return not os.path.relpath(os.path.abspath(path), COURSE).startswith(os.pardir)


@functools.lru_cache(maxsize=1)
def all_md() -> tuple[str, ...]:
    files = glob.glob(os.path.join(REPO, "**", "*.md"), recursive=True)
    return tuple(sorted(f for f in files if not rel(f).startswith(EXCLUDED_DIRS)))


@functools.lru_cache(maxsize=1)
def lesson_files() -> tuple[str, ...]:
    out = [f for f in glob.glob(os.path.join(COURSE, "*", "*.md"))
           if LESSON_RE.match(os.path.basename(f))]
    return tuple(sorted(out))


def line_of(path: str, needle: str) -> int | None:
    """The 1-indexed line a substring first appears on, so a Finding can be placed."""
    for i, line in enumerate(read(path).split("\n"), 1):
        if needle in line:
            return i
    return None
