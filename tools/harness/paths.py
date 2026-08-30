"""Every path the harness knows, resolved once.

The monolith this package replaced held four separate copies of the roster's path, and said so
in its own comments: a rename disabled three checks *without failing anything*, because each
one skipped quietly when its file was missing. A checker that goes green while checking nothing
is the one failure mode a checker must not have. One module, one definition, and
`invariants/budgets.py` asserts the files named here exist.
"""
from __future__ import annotations
import os

HARNESS = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HARNESS)
REPO = os.path.dirname(TOOLS)

COURSE = os.path.join(REPO, "networking-fundamentals")
REFERENCE = os.path.join(REPO, "reference")
ILLUSTRATIONS = os.path.join(REPO, "illustrations")
EXAM_PREP = os.path.join(REPO, "exam-prep")
DRILLS = os.path.join(REPO, "drills")

TOOLS_DIR = os.path.join(REFERENCE, "tools")
INDEX_MD = os.path.join(TOOLS_DIR, "README.md")
IFACE_MD = {i: os.path.join(TOOLS_DIR, i, "README.md")
            for i in ("netlink", "procfs", "socket", "packet",
                      "probe", "nsapi", "httpapi", "local")}
CAPS_JSON = os.path.join(REFERENCE, "capabilities.json")
LAB_JSON = os.path.join(REFERENCE, "lab-inventory.json")
MANIFEST_MD = os.path.join(ILLUSTRATIONS, "MANIFEST.md")
JOURNEY_MAP = os.path.join(REPO, "JOURNEY-MAP.md")
LESSON_INDEX = os.path.join(REPO, "LESSON-INDEX.md")
SYNC_MJS = os.path.join(REPO, "site", "scripts", "sync-content.mjs")
PER_ACT_COMMANDS = os.path.join(REFERENCE, "05-per-act-commands.md")


def rel(p: str) -> str:
    return os.path.relpath(p, REPO)
