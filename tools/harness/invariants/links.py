"""Link integrity — the only invariant that fires on `reference/` as hard as on a lesson.

Every "taught in" citation in the reference wing is a relative link into a lesson, so a
rename breaks the build instead of leaving a lie in a table.

Moved verbatim from `tools/check_pedagogy.py` — the bodies are unchanged, so the
parity test in `tools/harness/selftest.py` can prove the move changed no behaviour.
"""
from __future__ import annotations
import os
from ..corpus import LINK_RE, read, strip_code
from ..paths import rel


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
