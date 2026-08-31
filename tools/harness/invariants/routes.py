"""Routes — the step→file map lives in `reference/routes.json`, checked rather than trusted.

Three ways it can go quietly wrong, none of which a human rereading the page would necessarily
catch: a glob that stopped matching (a lesson renamed out from under it), a `reorder` route whose
steps no longer add up to the whole course, and a page whose printed numbers have drifted from
what the same globs would compute today — which is the exact defect that motivated encoding this
as data in the first place. See `tools/routes_lib.py` for the arithmetic these three delegate to.
"""
from __future__ import annotations
import sys

from ..model import WARN, Finding
from ..paths import TOOLS


def _routes_lib():
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import routes_lib
    return routes_lib


def check_step_globs_resolve(_files=None) -> list[Finding]:
    try:
        rl = _routes_lib()
        routes = rl.load()
    except Exception as e:                                     # pragma: no cover
        return [Finding(invariant="routes.step-globs-resolve", severity=WARN,
                        message=f"reference/routes.json could not be loaded ({e})")]
    return [Finding(invariant="routes.step-globs-resolve", severity=WARN, message=p)
            for p in rl.check_globs_resolve(routes)]


def check_reorder_covers_course(_files=None) -> list[Finding]:
    try:
        rl = _routes_lib()
        routes = rl.load()
    except Exception as e:                                     # pragma: no cover
        return [Finding(invariant="routes.reorder-covers-course", severity=WARN,
                        message=f"reference/routes.json could not be loaded ({e})")]
    return [Finding(invariant="routes.reorder-covers-course", severity=WARN, message=p)
            for p in rl.check_reorder_coverage(routes)]


def check_published_figures(_files=None) -> list[Finding]:
    try:
        rl = _routes_lib()
        routes = rl.load()
    except Exception as e:                                     # pragma: no cover
        return [Finding(invariant="routes.published-figures", severity=WARN,
                        message=f"reference/routes.json could not be loaded ({e})")]
    return [Finding(invariant="routes.published-figures", severity=WARN, message=p)
            for p in rl.check_published_figures(routes)]
