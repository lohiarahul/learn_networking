#!/usr/bin/env python3
"""gen-route-tables.py — the Words and Drills columns of a route's step table, regenerated from data.

Why this exists
----------------
A route page is a step table pointing into existing lessons — `exam-prep/the-exam-path.md` (Route
B) is the precedent. Its Words and Drills columns were hand-measured once and never rechecked, so
they drifted: step 1 published 46,795 words while the three directories it names now sum to
59,882, thirteen thousand words later. `reference/routes.json` names, per step, the globs that
decide what belongs to it; this script sums them and writes the answer into the table. The *Why
here* column, and everything outside the table, is prose and is never touched — a generator that
could overwrite it could also delete the one part of the page worth reading.

The arithmetic itself lives in `routes_lib.py`, shared with
`tools/harness/invariants/routes.py` so the harness checks the exact numbers this script would
write, not an approximation of them.

Usage
-----
    python3 tools/gen-route-tables.py            # sync every route's page
    python3 tools/gen-route-tables.py B           # sync one route by id
    python3 tools/gen-route-tables.py --check     # exit 1 if any page is stale (for CI)
"""
from __future__ import annotations
import sys

import routes_lib as rl


def main(argv: list[str]) -> int:
    check = "--check" in argv
    ids = [a for a in argv if a != "--check"]
    routes = rl.load()
    if ids:
        routes = {k: v for k, v in routes.items() if k in ids}
        missing = set(ids) - set(routes)
        if missing:
            sys.exit(f"no such route id(s): {', '.join(sorted(missing))}")

    bad_globs = rl.check_globs_resolve(routes)
    if bad_globs:
        for p in bad_globs:
            print(f"  ✗ {p}", file=sys.stderr)
        return 1

    stale, written = [], 0
    for route_id, route in routes.items():
        path = rl.os.path.join(rl.REPO, route["page"])
        new_text, changes = rl.sync_page(route)
        if not changes:
            continue
        if check:
            stale.append((route_id, changes))
            continue
        open(path, "w", encoding="utf-8").write(new_text)
        written += 1
        print(f"{route_id} ({route['page']}): " + "; ".join(changes))

    if check:
        if stale:
            for route_id, changes in stale:
                print(f"stale: route {route_id}")
                for c in changes:
                    print(f"  {c}")
            return 1
        print(f"{len(routes)} route page(s) up to date")
        return 0

    if not written:
        print(f"{len(routes)} route page(s) already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
