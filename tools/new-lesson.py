#!/usr/bin/env python3
"""
new-lesson.py — scaffold a lesson that passes the pedagogy invariants by construction.

    python3 tools/new-lesson.py <act-dir> <number> "<Title>" <slug>
    python3 tools/new-lesson.py act-3-the-internet 06 "HTTP caching" http-caching

Creates networking-fundamentals/<act-dir>/<number>-<slug>.md pre-loaded with the required
skeleton (a Predict-first block, a milestone, a Next: footer) and appends a one-line entry to
LESSON-INDEX.md. The author then replaces the TODOs with real teaching. Won't overwrite an
existing file.
"""
from __future__ import annotations
import os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE = os.path.join(REPO, "networking-fundamentals")

TEMPLATE = """\
# {title}

<!-- Open by raising the QUESTION the reader arrives at after the previous lesson — a wall they
     hit, not a truth you announce. (Spirit + forward tension.) TODO: write the hook. -->

## <!-- TODO: a section heading that IS the reader's question -->

<!-- Analogy before definition. Read the raw kernel file before the tool that prettifies it. -->

> **Predict first —** <!-- TODO: pose a guess the reader commits to before running the experiment. -->

```
# TODO: the experiment. Real command in the lab image.
```

<!-- State the surprising result and how to know they got it right (the feedback loop). -->

**You can now** <!-- TODO: name the concrete new thing the reader can do. --> — and that raises the
next question: <!-- TODO: the wall that the next lesson answers. -->

---

↑ **[{act_title} overview](README.md)** · Next: **[TODO next lesson](TODO.md)** →
"""

ACT_TITLES = {
    "act-1-one-machine": "Act I", "act-2-two-machines": "Act II",
    "act-3-the-internet": "Act III", "act-4-one-pretends-many": "Act IV",
    "act-5-kubernetes": "Act V",
}

def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    act, number, title, slug = argv
    act_dir = os.path.join(COURSE, act)
    if not os.path.isdir(act_dir):
        print(f"no such act dir: {act_dir}")
        return 1
    dest = os.path.join(act_dir, f"{number}-{slug}.md")
    if os.path.exists(dest):
        print(f"refusing to overwrite existing {os.path.relpath(dest, REPO)}")
        return 1
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(title=title, act_title=ACT_TITLES.get(act, act)))
    print(f"created {os.path.relpath(dest, REPO)}")

    idx = os.path.join(REPO, "LESSON-INDEX.md")
    if os.path.exists(idx):
        with open(idx, "a", encoding="utf-8") as fh:
            fh.write(f"\n- `{number}-{slug}.md` — {title} — TODO: gist / introduces\n")
        print("appended a stub line to LESSON-INDEX.md")

    print("Now: replace the TODOs, then run  python3 tools/check_pedagogy.py " + dest)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
