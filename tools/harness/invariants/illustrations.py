"""Illustrations are placed by the manifest, or they are not placed at all.

Moved verbatim from `tools/check_pedagogy.py` — the bodies are unchanged, so the
parity test in `tools/harness/selftest.py` can prove the move changed no behaviour.
"""
from __future__ import annotations
import os, re
from ..corpus import all_md, read
from ..paths import ILLUSTRATIONS, MANIFEST_MD, rel


NOT_PLACED_H2 = "## Not placed"


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
