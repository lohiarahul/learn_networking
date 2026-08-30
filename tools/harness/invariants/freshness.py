"""Indexes and maps that describe the course, and go stale silently when it moves.

Moved verbatim from `tools/check_pedagogy.py` — the bodies are unchanged, so the
parity test in `tools/harness/selftest.py` can prove the move changed no behaviour.
"""
from __future__ import annotations
import os
from ..corpus import lesson_files, read
from ..paths import REPO


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
