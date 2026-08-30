"""The invariant registry — one table you can read to know what this harness enforces.

The monolith carried two flat lists, `HARD_CHECKS` and `WARN_CHECKS`, and severity was a
property of *which list* a function sat in. Three consequences, all of which bit:

1. **Scope was implicit.** Warning checks were skipped on a single-file run, so the save hook
   silently checked less than the author believed. Here `scope` is declared, and a scoped run
   *reports what it deferred* instead of quietly not running it.
2. **Severity could not vary per finding.** A check that wanted to fail on one condition and
   warn on another had to be two functions. `Finding` carries its own severity; the invariant's
   is only the default.
3. **Nothing could describe itself.** No id, no rationale, so `--list` was impossible and a rule
   whose reason nobody could state was a rule the next author deleted.

Legacy-shaped checks — `fn(files) -> [(level, message)]` — are adapted rather than rewritten, so
moving them changed no behaviour. `selftest.py` proves that claim.
"""
from __future__ import annotations
import os, re

from .model import FAIL, WARN, REPO_WIDE, Finding, Invariant
from .paths import REPO

_PATH_RE = re.compile(r"[\w./-]+\.(?:md|json|mjs|py|sh)")


def _place(message: str) -> tuple[str | None, int | None]:
    """Best-effort: pull a real repo path out of a legacy message so the Finding is placeable.

    Legacy messages were written for a human reading a terminal and embed `rel(f)` inline. That
    is enough to recover a path, which is what SARIF needs to render the result on the right
    line in an editor. A message with no recoverable path still reports — it just isn't anchored.
    """
    for cand in _PATH_RE.findall(message):
        if os.path.exists(os.path.join(REPO, cand)):
            return cand, None
    return None, None


class Registry:
    def __init__(self) -> None:
        self._invariants: dict[str, Invariant] = {}

    def register(self, id: str, fn, *, severity: str = FAIL, scope: str = REPO_WIDE,
                 rationale: str = "", tags: tuple[str, ...] = ()) -> None:
        if id in self._invariants:
            raise ValueError(f"duplicate invariant id: {id}")
        self._invariants[id] = Invariant(id=id, fn=fn, severity=severity, scope=scope,
                                        rationale=rationale, tags=tags)

    def __len__(self) -> int:
        return len(self._invariants)

    def all(self) -> list[Invariant]:
        return sorted(self._invariants.values(), key=lambda i: (i.severity != FAIL, i.id))

    def get(self, id: str) -> Invariant | None:
        return self._invariants.get(id)

    def select(self, *, scoped: bool, only: list[str] | None = None) -> tuple[list, list]:
        """Return (to_run, deferred).

        `scoped` means the caller handed us a specific file list rather than the whole repo, so
        repo-wide invariants cannot be evaluated. They are returned as *deferred* rather than
        dropped — the report says so, which is the fix for the monolith's silent skip.
        """
        run, deferred = [], []
        for inv in self.all():
            if only and inv.id not in only:
                continue
            if scoped and inv.scope == REPO_WIDE:
                deferred.append(inv)
            else:
                run.append(inv)
        return run, deferred

    def run(self, invariants: list[Invariant], files: list[str]) -> list[Finding]:
        findings: list[Finding] = []
        for inv in invariants:
            for item in inv.fn(files) or []:
                if isinstance(item, Finding):
                    findings.append(item)
                    continue
                level, message = item
                sev = FAIL if str(level).lower().startswith("f") else WARN
                path, line = _place(message)
                findings.append(Finding(invariant=inv.id, severity=sev, message=message,
                                        path=path, line=line))
        return findings


REGISTRY = Registry()
