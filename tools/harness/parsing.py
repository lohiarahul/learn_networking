"""Parsers for the reference wing's tables, shared by more than one invariant.

`index_tool_rows` is read by both the roster invariants and the command-table invariant. It
lived in the monolith as a free function every check could reach; here it is a module so that
neither invariant module has to import the other.
"""
from __future__ import annotations
import re


def page_slug(tool: str) -> str:
    """`ip netns` -> `ip-netns`. The same transform `tools/gen-tool-pages.py` names files with."""
    return re.sub(r"[^a-z0-9]+", "-", tool.strip().lower()).strip("-")


def index_tool_rows(text):
    """Yield the data rows of the index's *topical* tables as dicts, keyed by column header.

    Table-aware on purpose. The page also carries summary tables whose first cell is a code span
    (`| `netlink` | ip monitor · ss -E | …`), and a naive "row starts with a backtick" scan reads those
    interface names as tool names — which is exactly the false positive this function exists to avoid.
    A topical table is identified by having an `In the course` column; nothing else does.
    """
    cols, rows = None, []
    for line in text.split("\n"):
        st = line.strip()
        if not st.startswith("|"):
            cols = None
            continue
        cells = [c.strip() for c in st.strip("|").split("|")]
        if "In the course" in cells:
            cols = cells
            continue
        if cols is None or all(set(c) <= {"-", ":"} for c in cells) or len(cells) != len(cols):
            continue
        rows.append(dict(zip(cols, cells)))
    return rows
