"""Parity and mutation tests — who checks the checkers.

Two questions this answers, and the second is the one linters usually skip:

1. **Parity.** The sixteen invariants moved out of `tools/check_pedagogy.py` were moved
   verbatim. Do they still return exactly what the monolith returned? Compared function by
   function against the original file, which is kept for this purpose.
2. **Mutation.** A check that has quietly stopped checking anything passes. So for each
   invariant with a known perturbation, break the repo in a temp copy and assert the invariant
   *fires*. A green run only means something if the rules can still go red.

    python3 -m harness.selftest
"""
from __future__ import annotations
import importlib.util as iu
import os, shutil, subprocess, sys, tempfile

from .paths import REPO, TOOLS
from .registry import REGISTRY
from . import invariants  # noqa: F401

LEGACY = os.path.join(TOOLS, "_legacy_check_pedagogy.py")

# If this path goes stale, `parity()` reports "cannot compare" for all sixteen rather than
# passing — which is the behaviour that caught the rename that introduced this comment.

# invariant id -> the legacy function name it was moved from.
PARITY = {
    "links.resolve": "check_links",
    "shape.act-files": "check_act_shape",
    "shape.predict-first": "check_prediction",
    "shape.ladder": "check_ladder",
    "shape.milestone-length": "check_milestone_length",
    "reference.shape": "check_reference_shape",
    "index.freshness": "check_index_freshness",
    "map.vs-build": "check_map_vs_build",
    "commands.table-coverage": "check_command_table_coverage",
    "commands.runnable-citations": "check_runnable_citations",
    "reference.iface-rosters": "check_iface_rosters",
    "reference.index-facets": "check_index_facets",
    "capabilities.standing": "check_standing",
    "capabilities.keys": "check_keys",
    "illustrations.placement": "check_illustration_placement",
    "counts.published": "check_wordcounts",
}

# invariant id -> (relative path to break, mutation applied to its text)
MUTATIONS = {
    "links.resolve": ("networking-fundamentals/act-1-one-machine/README.md",
                      lambda t: t + "\n[dangling](no-such-file-here.md)\n"),
    "shape.predict-first": ("networking-fundamentals/act-2-two-machines/02-ip-and-routing.md",
                            lambda t: t.replace("Predict first", "XX").replace("predict first", "xx")),
    # Note: this file's milestone marker is "You understand this when", not "You can now".
    # The first draft of these mutations assumed the latter and silently failed to fire — a
    # mutation test that mutates nothing is the same false confidence it exists to prevent.
    "shape.ladder": ("networking-fundamentals/act-2-two-machines/02-ip-and-routing.md",
                     lambda t: t.replace("You understand this when", "XX")
                                .replace("Where you are now", "XX")
                                .replace("You can now", "XX")),
    "shape.milestone-length": ("networking-fundamentals/act-2-two-machines/02-ip-and-routing.md",
                               lambda t: t.replace("> **You understand this when you can**",
                                                   "> **You understand this when you can** "
                                                   + "padding " * 120)),
    "counts.published": ("JOURNEY-MAP.md",
                         lambda t: t.replace("437,039 words, nothing skipped",
                                             "1 words, nothing skipped")),
    "routes.step-globs-resolve": ("reference/routes.json",
                                  lambda t: t.replace('"00-orientation/**"',
                                                      '"00-orientation-typo/**"')),
    "routes.published-figures": ("exam-prep/the-exam-path.md",
                                 lambda t: t.replace("| **1** | Orientation, **Act I**, **Act IV** | 59,881 | 12 |",
                                                     "| **1** | Orientation, **Act I**, **Act IV** | 1 | 1 |")),
}

# `routes.reorder-covers-course` only fires for a `kind: reorder` route, and Route B (the only
# route registered so far) is `kind: split` — so its mutation is a JSON edit rather than a
# find-and-replace on prose: add a second, disjoint `reorder` route with one step that omits most
# of the course, and assert the coverage check names the gap.
MUTATIONS["routes.reorder-covers-course"] = (
    "reference/routes.json",
    lambda t: t.rstrip()[:-1] + ',\n  "Z": {"name": "test", "page": "exam-prep/the-exam-path.md", '
                                '"kind": "reorder", "steps": [{"n": 1, "include": ["00-orientation/**"]}]}\n}\n'
)


def _load_legacy():
    spec = iu.spec_from_file_location("legacy_check_pedagogy", LEGACY)
    mod = iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parity() -> tuple[int, int, list[str]]:
    from .corpus import all_md
    legacy = _load_legacy()
    files = list(all_md())
    ok, total, problems = 0, 0, []
    for inv_id, legacy_name in sorted(PARITY.items()):
        fn_old = getattr(legacy, legacy_name, None)
        inv = REGISTRY.get(inv_id)
        if fn_old is None or inv is None:
            problems.append(f"{inv_id}: cannot compare (legacy {legacy_name} missing)")
            total += 1
            continue
        total += 1
        old = sorted(m for _l, m in fn_old(files))
        new = sorted(f.message for f in REGISTRY.run([inv], files))
        if old == new:
            ok += 1
        else:
            problems.append(f"{inv_id}: legacy {len(old)} finding(s), new {len(new)} — differ")
    return ok, total, problems


def mutation() -> tuple[int, int, list[str]]:
    ok, total, problems = 0, 0, []
    for inv_id, (rel_path, mutate) in sorted(MUTATIONS.items()):
        total += 1
        with tempfile.TemporaryDirectory() as tmp:
            clone = os.path.join(tmp, "repo")
            shutil.copytree(REPO, clone, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "node_modules", "dist",
                                                          "_build", "_previews", "*.pdf", "*.zip"))
            target = os.path.join(clone, rel_path)
            if not os.path.exists(target):
                problems.append(f"{inv_id}: mutation target {rel_path} missing")
                continue
            text = open(target, encoding="utf-8").read()
            open(target, "w", encoding="utf-8").write(mutate(text))
            r = subprocess.run([sys.executable, "-m", "harness", "--only", inv_id,
                                "--format", "json"],
                               cwd=os.path.join(clone, "tools"),
                               capture_output=True, text=True)
            if inv_id in r.stdout and '"findings": []' not in r.stdout:
                ok += 1
            else:
                problems.append(f"{inv_id}: did NOT fire when {rel_path} was broken")
    return ok, total, problems


def main() -> int:
    p_ok, p_total, p_bad = parity()
    print(f"parity   {p_ok}/{p_total} invariants match the monolith exactly")
    for m in p_bad:
        print(f"  ✗ {m}")

    m_ok, m_total, m_bad = mutation()
    print(f"mutation {m_ok}/{m_total} invariants fire when the repo is broken")
    for m in m_bad:
        print(f"  ✗ {m}")

    bad = len(p_bad) + len(m_bad)
    print("✓ selftest passes" if not bad else f"\n{bad} problem(s)")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
