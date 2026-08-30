"""The word counts the course publishes about itself, checked against measurement."""
from __future__ import annotations
import os, sys

from ..model import WARN, Finding
from ..paths import TOOLS


def check_wordcounts(_files=None) -> list[Finding]:
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    try:
        import remeasure
    except Exception as e:                                     # pragma: no cover
        return [Finding(invariant="counts.published", severity=WARN,
                        message=(f"tools/remeasure.py could not be imported ({e}) — the "
                                 f"published word counts are no longer being checked"))]
    return [Finding(invariant="counts.published", severity=WARN, message=msg)
            for _lvl, msg in remeasure.claim_issues()]
