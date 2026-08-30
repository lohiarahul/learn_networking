"""The vocabularies, and the one shape a finding takes.

Two design rules carried over from the monolith and made explicit here:

* **Closed vocabularies.** `INTERFACES`, `MODES`, `STANDING_LEVELS` and `SWAP_KINDS` are
  deliberately finite, because an open taxonomy is one that has quietly stopped partitioning
  anything. A value outside the set is the bug, not a new category.
* **One finding shape.** The monolith passed `(level, message)` tuples, which cannot carry a
  file or a line, so nothing downstream could place a result in an editor. `Finding` can, which
  is what makes SARIF output possible at all.
"""
from __future__ import annotations
from dataclasses import dataclass, field

FAIL = "fail"
WARN = "warn"

# Scope declares what an invariant needs in order to mean anything. The monolith had this
# distinction and left it implicit: warning checks silently did not run on a single-file save,
# so the save hook checked less than the author believed. Declared, it can be *reported*.
FILE = "file"   # decidable from one file's own contents
REPO_WIDE = "repo"  # needs the whole corpus (rosters, indexes, totals, ordering)

SEVERITIES = (FAIL, WARN)
SCOPES = (FILE, REPO_WIDE)

# Acts that must carry the full four-file shape (README + test-yourself + diagnose + in-the-wild).
ACT_DIRS = ["act-1-one-machine", "act-2-two-machines", "act-3-the-internet",
            "act-4-one-pretends-many", "act-5-kubernetes", "act-6-control-plane",
            "act-7-workloads",
            "act-8-trust", "act-9-identity", "act-10-cluster-security",
            "act-11-observability"]

# The reading order of the course, which the River invariant needs and nothing else stated.
# Orientation precedes every act; the acts follow in numeric order.
READING_ORDER = ["00-orientation"] + ACT_DIRS

DIAGNOSE_EXEMPT: set[str] = set()

PREDICTION_EXEMPT = {
    "00-orientation/01-what-is-a-process.md",
    "00-orientation/02-how-processes-communicate.md",
    "act-1-one-machine/06b-the-container-filesystem.md",
    "act-5-kubernetes/01-lab-with-kind.md",
    "act-5-kubernetes/08-debugging.md",
}

PREDICTION_MARKERS = ["predict first", "predict —", "predict:", "predict, then"]
MILESTONE_MARKERS = ["you can now", "where you are now", "where this leaves",
                     "you understand this when"]
FORWARD_MARKERS = ["next:", "→"]
MILESTONE_MAX_WORDS = 100

INTERFACES = {"netlink", "procfs", "socket", "packet", "probe", "nsapi", "httpapi", "local"}
MODES = {"read-only", "mutate", "live"}
STANDING_LEVELS = {"default", "superseded", "emerging"}
SWAP_KINDS = {"rename", "reflag", "rewrite"}
EMERGING_YEARS = 5
MAX_KEYS = 4

EXCLUDED_DIRS = ("site/node_modules", "site/dist", "site/src/content/docs", "node_modules")


@dataclass(frozen=True)
class Finding:
    """One violation, placeable in a file so an editor or GitHub can render it inline."""
    invariant: str
    severity: str
    message: str
    path: str | None = None
    line: int | None = None

    def __post_init__(self):
        if self.severity not in SEVERITIES:
            raise ValueError(f"{self.severity!r} is not one of {SEVERITIES}")


@dataclass(frozen=True)
class Invariant:
    """A fitness function, with the metadata that makes it schedulable and explainable.

    `scope` decides whether a single-file run can evaluate it. `rationale` is not decoration:
    every invariant here exists because something actually went wrong once, and a rule whose
    reason nobody can state is a rule the next author deletes.
    """
    id: str
    fn: object
    severity: str = FAIL
    scope: str = REPO_WIDE
    rationale: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.severity not in SEVERITIES:
            raise ValueError(f"{self.id}: bad severity {self.severity!r}")
        if self.scope not in SCOPES:
            raise ValueError(f"{self.id}: bad scope {self.scope!r}")
