"""routes_lib.py — the step→file map, as data, resolved.

`reference/routes.json` names which files belong to which step of a route; this module is the one
place that turns those globs into word counts, drill counts and coverage facts. Split out from
`gen-route-tables.py` (which owns the CLI and the page-rewrite) so that
`tools/harness/invariants/routes.py` can check the same arithmetic without re-deriving it, and so
neither has to import a hyphenated filename.

`kind` is load-bearing. A `split` route's steps need not cover the course — the remainder is the
optional track, and some of it may be a genuine third bucket (front matter nobody's prose claims,
see `unclaimed_words`). A `reorder` route's steps must partition the course exactly, once each —
`check_reorder_coverage` turns that from an assertion into a check.
"""
from __future__ import annotations
import glob, json, os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE = os.path.join(REPO, "networking-fundamentals")
DRILLS = os.path.join(REPO, "drills")
ROUTES_JSON = os.path.join(REPO, "reference", "routes.json")


def words(path: str) -> int:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return len(fh.read().split())


def load(path: str = ROUTES_JSON) -> dict:
    return json.load(open(path, encoding="utf-8"))


def rel(p: str) -> str:
    return os.path.relpath(p, REPO)


def resolve(base: str, globs: list[str]) -> list[str]:
    """Every file a list of globs matches, resolved against `base`, deduped, sorted.

    A glob that matches nothing is the caller's problem to report, not this function's — it
    returns an empty list rather than raising, so `check_globs_resolve` can say *which* glob is
    the dead one instead of the whole step failing silently.
    """
    seen: set[str] = set()
    for g in globs:
        for p in glob.glob(os.path.join(base, g), recursive=True):
            if os.path.isfile(p):
                seen.add(os.path.normpath(p))
    return sorted(seen)


def step_files(step: dict) -> list[str]:
    return resolve(COURSE, step.get("include", []))


def step_words(step: dict) -> int:
    return sum(words(p) for p in step_files(step))


def step_drill_files(step: dict) -> list[str]:
    return resolve(DRILLS, step.get("drills", []))


def step_drill_count(step: dict) -> int:
    return len(step_drill_files(step))


def optional_words(route: dict) -> int:
    """The optional track's word total — excluding any entry already counted on the path.

    `already_on_path` exists because Act IV 05b/05c sit inside step 1's whole-act glob (Route B
    never splits Act IV) and are *also* worth flagging as skippable reading. Counting their words
    a second time here would overstate "words outside both curricula" by exactly their length —
    found by summing the page's own model and getting more than the course contains.
    """
    return sum(
        sum(words(p) for p in resolve(COURSE, entry.get("include", [])))
        for entry in route.get("optional", [])
        if not entry.get("already_on_path")
    )


def cumulative_words(route: dict, through_step: int) -> int:
    return sum(step_words(s) for s in route["steps"]
               if s["n"] <= through_step and s.get("count", True))


def cumulative_drills(route: dict, through_step: int) -> int:
    return sum(step_drill_count(s) for s in route["steps"]
               if s["n"] <= through_step and s.get("count", True))


def path_words(route: dict) -> int:
    """Every course word a `count`-eligible step claims — step 7 (exam-prep) excluded by design;
    it is real prose, but it is not part of `networking-fundamentals/` and was never part of the
    course total either."""
    return sum(step_words(s) for s in route["steps"] if s.get("count", True))


def path_drills(route: dict) -> int:
    return sum(step_drill_count(s) for s in route["steps"] if s.get("count", True))


def unclaimed_words(route: dict, course_total: int) -> int:
    """Course words neither a `count`-eligible step nor the optional track claims.

    Zero for a `reorder` route by construction. For `split`, a small nonzero figure here is not
    automatically a bug — Route B's own prose never mentions the lab-setup files
    (`networking-fundamentals/README.md`, `your-own-machine.md`, `code/`), and there is no step for
    them to be assigned to without inventing one. What this function makes possible is *noticing*
    when that figure moves, rather than the multi-phase drift this whole module exists to end.
    """
    return course_total - path_words(route) - optional_words(route)


def course_total() -> int:
    return sum(words(p) for p in glob.glob(os.path.join(COURSE, "**", "*.md"), recursive=True))


def check_globs_resolve(routes: dict) -> list[str]:
    """Every glob named in every route must match at least one file."""
    problems = []
    for route_id, route in routes.items():
        for step in route.get("steps", []):
            for g in step.get("include", []) + step.get("drills", []):
                base = DRILLS if g in step.get("drills", []) else COURSE
                if not glob.glob(os.path.join(base, g), recursive=True):
                    problems.append(f"route {route_id} step {step['n']}: glob {g!r} matches nothing")
        for entry in route.get("optional", []):
            for g in entry.get("include", []):
                if not glob.glob(os.path.join(COURSE, g), recursive=True):
                    problems.append(f"route {route_id} optional {entry['label']!r}: "
                                    f"glob {g!r} matches nothing")
    return problems


def check_reorder_coverage(routes: dict) -> list[str]:
    """A `kind: reorder` route's steps must partition the course exactly — no file twice, none missing."""
    problems = []
    all_files = set(glob.glob(os.path.join(COURSE, "**", "*.md"), recursive=True))
    for route_id, route in routes.items():
        if route.get("kind") != "reorder":
            continue
        seen: dict[str, int] = {}
        for step in route["steps"]:
            for p in step_files(step):
                seen[p] = seen.get(p, 0) + 1
        dupes = sorted(rel(p) for p, n in seen.items() if n > 1)
        missing = sorted(rel(p) for p in all_files if p not in seen)
        if dupes:
            problems.append(f"route {route_id}: {len(dupes)} file(s) claimed by more than one "
                            f"step — {', '.join(dupes[:5])}" + (" …" if len(dupes) > 5 else ""))
        if missing:
            problems.append(f"route {route_id}: {len(missing)} course file(s) claimed by no "
                            f"step — {', '.join(missing[:5])}" + (" …" if len(missing) > 5 else ""))
    return problems


# ── The page's own table: parse it, compare it, rewrite it ────────────────────────────────────
# Deliberately strict — plain `N | N`, nothing else in either cell. Step 7 (exam-prep, `count:
# false`) writes "16,636 *(not counted below)*" and "7 items", which do not match this shape, so
# its row is left alone by construction rather than by a special case: its numbers are not a step
# word count and a drill count in the sense every other row's are, and rewriting them would be
# fabricating a comparison that means nothing.
STEP_ROW_RE = re.compile(r"^\| \*\*(\d+)\*\* \| (.*?) \| ([\d,]+) \| (\d+) \| (.*) \|$")
SUMMARY_ROW_RE = re.compile(r"^\| \| \*\*→ (.*?)\*\* \| \*\*([\d,]+)\*\* course words \| \*\*(\d+)\*\* \| \|$")


def fmt(n: int) -> str:
    return f"{n:,}"


def sync_page(route: dict) -> tuple[str, list[str]]:
    """Rewrite the route's page text with fresh Words/Drills — the Read and Why-here columns, and
    everything outside the table, are never touched. Returns (new_text, changes)."""
    path = os.path.join(REPO, route["page"])
    text = open(path, encoding="utf-8").read()
    steps_by_n = {s["n"]: s for s in route["steps"]}
    summaries_by_label = {s["label"]: s for s in route.get("summaries", [])}
    changes = []
    out = []
    for line in text.split("\n"):
        m = STEP_ROW_RE.match(line)
        if m:
            n, mid, old_w, old_d, tail = m.groups()
            step = steps_by_n.get(int(n))
            if step is not None:
                new_w, new_d = fmt(step_words(step)), str(step_drill_count(step))
                if new_w != old_w.strip() or new_d != old_d.strip():
                    changes.append(f"step {n}: {old_w} words/{old_d} drills -> {new_w} words/{new_d} drills")
                out.append(f"| **{n}** | {mid} | {new_w} | {new_d} | {tail} |")
                continue
        m = SUMMARY_ROW_RE.match(line)
        if m:
            label, old_w, old_d = m.groups()
            summ = summaries_by_label.get(label)
            if summ is not None:
                new_w = fmt(cumulative_words(route, summ["through_step"]))
                new_d = str(cumulative_drills(route, summ["through_step"]))
                if new_w != old_w.strip() or new_d != old_d.strip():
                    changes.append(f"summary {label!r}: {old_w}/{old_d} -> {new_w}/{new_d}")
                out.append(f"| | **→ {label}** | **{new_w}** course words | **{new_d}** | |")
                continue
        out.append(line)
    return "\n".join(out), changes


def check_published_figures(routes: dict) -> list[str]:
    problems = []
    for route_id, route in routes.items():
        path = os.path.join(REPO, route["page"])
        if not os.path.exists(path):
            problems.append(f"route {route_id}: page {route['page']} does not exist")
            continue
        _new_text, changes = sync_page(route)
        for c in changes:
            problems.append(f"route {route_id} ({route['page']}): {c} — run "
                            f"tools/gen-route-tables.py to fix")
    return problems
