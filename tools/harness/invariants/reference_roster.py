"""The tool roster and its two facets — the closed vocabularies, and the guard on the guards.

Moved verbatim from `tools/check_pedagogy.py` — the bodies are unchanged, so the
parity test in `tools/harness/selftest.py` can prove the move changed no behaviour.
"""
from __future__ import annotations
import json, os, re
from ..corpus import read
from ..model import INTERFACES, MODES
from ..parsing import index_tool_rows, page_slug
from ..paths import CAPS_JSON, IFACE_MD, INDEX_MD, rel


def check_reference_shape(_files):
    """Hard: the reference's own files exist where the checkers below expect them.

    This is the guard on the guards. Three of the checks in this file — the facet vocabularies, the
    supersession compartment, the SHELL_COMMANDS cross-reference — read the roster by path, and
    every one of them used to hold its own copy of that path and skip quietly if the file was not
    there. So a rename anywhere in `reference/` disabled them *without failing anything*: the run
    went green while nothing was being checked. That is the one failure mode a checker must not
    have, and it is why this is a hard check rather than a warning.
    """
    missing = [p for p in [INDEX_MD, *IFACE_MD.values()] if not os.path.exists(p)]
    return [("FAIL", f"reference-shape: {rel(p)} is missing — the reference has been "
                     f"restructured and the checks that read it are no longer checking anything")
            for p in missing]


def check_iface_rosters(_files):
    """Warning-only: each interface page must name exactly the tools the roster gives it.

    `reference/tools/netlink/README.md` is both the netlink page and the landing page for the
    thirteen tool pages in that directory, and it opens with the list of them. That list is
    hand-written, so it is the kind of thing that is correct on the day it is typed and wrong two
    tools later — and it is now the *only* place a reader is offered the siblings of a tool, since
    the per-page "Same interface" list was seventy-two copies of it.

    So it gets the same bidirectional treatment as the eight-interfaces summary on the roster: a
    tool the roster puts in this directory must be linked from the page, and the page may not link
    a tool the roster puts somewhere else. Both directions, or the summary is free to drift.

    A row can also be *only* a row — an unlinked name on the roster, meaning the tool has no page
    (see `gen-tool-pages.py`). The membership claim still has to hold for those, so the check is over
    *placement* rather than over links: a paged tool must be linked, an unpaged one must be named in a
    code span, and an unpaged one must **not** be linked, because that link is a 404 the moment the
    orphan sweep runs. Without the third clause, compressing a tool to a row would leave its sibling
    list pointing at a file this repository deletes on every generator run.
    """
    if not os.path.exists(INDEX_MD):
        return []
    rows = index_tool_rows(read(INDEX_MD))
    by_iface, rowonly = {}, {}
    for r in rows:
        iface = re.split(r"[·&]", r["Speaks"], maxsplit=1)[0].strip()
        names = re.findall(r"`([^`]+)`", r["Tool"])
        if iface in INTERFACES and names:
            # The *page*, not the name. A row like `` `xxd` / `base64` `` is one page under the
            # first name, and `` [`findmnt`](mount.md) `` is a correct link wearing an alias as its
            # label — so the comparison has to be over filenames, which is the thing that either
            # exists or does not.
            target = rowonly if not re.search(r"\]\([^)]+\.md\)", r["Tool"]) else by_iface
            target.setdefault(iface, set()).add(page_slug(names[0]))
    issues = []
    for iface, path in sorted(IFACE_MD.items()):
        if not os.path.exists(path):
            continue
        # Only links *into this directory* count as "this page lists that tool". The page also
        # links sideways to other interfaces and to lessons, and a cross-interface link is a
        # comparison, not a claim of membership — which the pattern gets for free by refusing a
        # target with a slash in it.
        body = read(path)
        listed = {t[:-3] for t in re.findall(r"\]\(([a-z0-9_.-]+\.md)\)", body)} - {"README"}
        actual = by_iface.get(iface, set())
        for m in sorted(actual - listed):
            issues.append(("WARN", f"iface-roster: `{m}` speaks {iface} on the roster but "
                                   f"{rel(path)} does not link it"))
        bare = rowonly.get(iface, set())
        for e in sorted(listed - actual - bare):
            issues.append(("WARN", f"iface-roster: {rel(path)} links `{e}`, which the roster "
                                   f"does not place in {iface}"))
        # A tool with no page still has to be placed, and must not be linked. "Placed" has to mean
        # *in the sibling list*, not merely mentioned: every one of these is discussed somewhere in
        # its interface page's prose anyway, so a whole-body scan would pass on an incidental
        # backtick and guarantee nothing. The list is the header — everything above the first rule.
        named = set(re.findall(r"`([^`]+)`", body.split("\n---", 1)[0]))
        for m in sorted(bare):
            if m in listed:
                issues.append(("WARN", f"iface-roster: {rel(path)} links `{m}.md`, which does not "
                                       f"exist — the roster gives `{m}` a row and no page"))
            elif m not in named:
                issues.append(("WARN", f"iface-roster: `{m}` speaks {iface} on the roster but "
                                       f"{rel(path)} never names it"))
    return issues


def check_index_facets(_files):
    """Warning-only: the index's `Speaks` column, the `mode` field, and the summaries built on both.

    Four drifts, all silent otherwise:

    1. A `Speaks` cell or a `mode` value outside its closed vocabulary — a typo, or a new interface
       invented in one row and nowhere else.
    2. The `Speaks` column and the *eight interfaces* summary table disagreeing about which tools speak
       what. This is the check that makes the taxonomy hold: a tool cannot be added without being
       placed, which is how every tool taxonomy eventually dies.
    3. The counts asserted in prose (`13 + 14 + … = 72`, and "22 of the 72 tools can stream") not
       matching what they describe.
    4. Every roster row having a `name` and a `mode` in `capabilities.json`, and no orphan entry there
       naming a tool the roster does not list.

    `mode` is checked against the JSON rather than the roster because the roster no longer has that
    column — it came down to four so it would fit on a screen. Which makes the streaming claim a
    cross-file check now: the sentence lives on the roster, the evidence for it lives in the JSON, and
    the count has to reconcile.
    """
    issues = []
    # Skipping a missing roster is safe here — and only here — because `check_reference_shape`
    # is a hard check that reports it by name. Without that, this early return was the bug: the
    # file moved, this check quietly stopped running, and the suite stayed green. Reading it
    # unguarded is not the fix either, since the traceback kills the run before the failure that
    # explains it can be printed.
    if not os.path.exists(INDEX_MD):
        return issues
    text = read(INDEX_MD)
    rows = index_tool_rows(text)
    if not rows or "Speaks" not in rows[0]:
        return issues
    caps = {}
    if os.path.exists(CAPS_JSON):
        import json
        with open(CAPS_JSON) as f: caps = json.load(f)

    # 1. Closed vocabularies.
    by_iface, rows_by_iface, streams = {}, {}, set()
    for r in rows:
        tool = r["Tool"]
        iface = re.split(r"[·&]", r["Speaks"], maxsplit=1)[0].strip()
        if iface not in INTERFACES:
            issues.append(("WARN", f"index-facets: {tool} claims interface '{iface}', "
                                   f"not one of {sorted(INTERFACES)}"))
            continue
        # Two units, deliberately. The summary table names individual tools, so the set
        # comparison counts code spans (`ulimit` / `prlimit` is two). The arithmetic the page states is
        # over *rows*, because that is what the page says it is counting.
        by_iface.setdefault(iface, set()).update(re.findall(r"`([^`]+)`", tool))
        rows_by_iface[iface] = rows_by_iface.get(iface, 0) + 1
        tid = re.findall(r"`([^`]+)`", tool)[0]
        d = caps.get(tid)
        if d is None:
            issues.append(("WARN", f"index-facets: the roster lists {tool} and `capabilities.json` "
                                   f"has no entry for it, so it gets no page"))
            continue
        if "name" not in d:
            issues.append(("WARN", f"index-facets: `{tid}` has no `name` — the page title needs the "
                                   f"expansion, or an em dash to say there is not one"))
        modes = {m.strip() for m in d.get("mode", [])}
        if not modes:
            issues.append(("WARN", f"index-facets: `{tid}` has no `mode`, so its page cannot say "
                                   f"whether typing it can change anything"))
        bad = modes - MODES
        if bad:
            issues.append(("WARN", f"index-facets: `{tid}` claims mode {sorted(bad)}, "
                                   f"not in {sorted(MODES)}"))
        if "live" in modes:
            streams.add(tool)
    listed = {re.findall(r"`([^`]+)`", r["Tool"])[0] for r in rows}
    for orphan in sorted(set(caps) - listed):
        issues.append(("WARN", f"index-facets: `capabilities.json` describes `{orphan}`, which the "
                               f"roster does not list — a page nothing links to"))

    # 2. The summary table must name exactly the tools the column classifies.
    for line in text.split("\n"):
        m = re.match(r"\| \*\*`(\w+)`\*\* \|", line.strip())
        if not m or m.group(1) not in INTERFACES:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        listed = set(re.findall(r"`([^`]+)`", cells[2]))
        actual = by_iface.get(m.group(1), set())
        for missing in sorted(actual - listed):
            issues.append(("WARN", f"index-facets: `{missing}` speaks {m.group(1)} in its row but is "
                                   f"absent from the eight-interfaces summary"))
        for extra in sorted(listed - actual):
            issues.append(("WARN", f"index-facets: the {m.group(1)} summary names `{extra}`, "
                                   f"which no row classifies as {m.group(1)}"))

    # 3. The arithmetic the page states about itself.
    sums = re.search(r"`((?:\d+ \+ )+\d+) = (\d+)`", text)
    if sums:
        parts = [int(x) for x in sums.group(1).split(" + ")]
        want = sorted(rows_by_iface.values(), reverse=True)
        if sorted(parts, reverse=True) != want or int(sums.group(2)) != len(rows):
            issues.append(("WARN", f"index-facets: the page states {sums.group(0)} but the columns give "
                                   f"{'+'.join(str(n) for n in want)} = {len(rows)}"))
    # `[^*]*` because the sentence on the page reads "can stream events", and an exact-phrase
    # regex here silently matched nothing for as long as it existed — the same failure mode
    # `check_reference_shape` guards paths against, one level down in the pattern.
    live = re.search(r"\*\*(\d+) of the (\d+) tools can stream[^*]*\*\*", text)
    if live and (int(live.group(1)) != len(streams) or int(live.group(2)) != len(rows)):
        issues.append(("WARN", f"index-facets: the page claims {live.group(1)} of {live.group(2)} tools "
                               f"stream; the `mode` fields give {len(streams)} of {len(rows)}"))
    return issues
