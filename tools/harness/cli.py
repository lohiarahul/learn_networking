"""One entry point, with the things the monolith's `main()` could not offer.

    python3 -m harness                       # every invariant, whole repo
    python3 -m harness <file.md> ...         # scoped: file invariants, deferred ones named
    python3 -m harness --list                # the rule table, with rationales
    python3 -m harness --only river.no-uphill-tool
    python3 -m harness --format sarif > harness.sarif
    python3 -m harness --graph               # what the course graph knows

`--list` is the one that matters most day to day: a harness you cannot enumerate is one whose
rules get rediscovered by tripping over them.
"""
from __future__ import annotations
import argparse, sys

from . import report
from .corpus import all_md
from .model import FAIL
from .registry import REGISTRY
from . import invariants  # noqa: F401  — importing registers the table


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="harness", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="restrict to these files (scoped run)")
    ap.add_argument("--format", choices=("human", "json", "sarif"), default="human")
    ap.add_argument("--only", action="append", help="run only this invariant id (repeatable)")
    ap.add_argument("--warn-only", action="store_true", help="never exit non-zero")
    ap.add_argument("--list", action="store_true", help="list invariants and exit")
    ap.add_argument("--graph", action="store_true", help="print course-graph coverage and exit")
    ap.add_argument("-v", "--verbose", action="store_true", help="name deferred invariants")
    args = ap.parse_args(argv)

    if args.list:
        for inv in REGISTRY.all():
            print(f"{inv.severity:<5} {inv.scope:<5} {inv.id}")
            if inv.rationale:
                print(f"                 {inv.rationale}")
        print(f"\n{len(REGISTRY)} invariants")
        return 0

    if args.graph:
        from .graph import build, coverage
        g = build()
        for k, v in coverage().items():
            print(f"  {k:<28} {v}")
        print(f"  {'tools used somewhere':<28} {len(g.uses)}")
        print(f"  {'citation edges':<28} {sum(len(v) for v in g.cites.values())}")
        return 0

    md = [f for f in args.files if f.endswith(".md")]
    scoped = bool(md)
    files = [__import__("os").path.abspath(f) for f in md] if scoped else list(all_md())

    to_run, deferred = REGISTRY.select(scoped=scoped, only=args.only)
    findings = REGISTRY.run(to_run, files)

    scope = f"{len(files)} file(s)" if scoped else "whole repo"
    if args.format == "json":
        print(report.as_json(findings, scope=scope))
    elif args.format == "sarif":
        print(report.sarif(findings, REGISTRY))
    else:
        print(report.human(findings, scope=scope, deferred=deferred, verbose=args.verbose))

    failed = any(f.severity == FAIL for f in findings)
    return 0 if (args.warn_only or not failed) else 1


if __name__ == "__main__":
    sys.exit(main())
