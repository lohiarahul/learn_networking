#!/usr/bin/env python3
"""Compatibility shim — the harness now lives in `tools/harness/`.

This file was 970 lines and nineteen checks in one module. It is kept as an entry point because
`.claude/settings.json`, `tools/pedagogy_hook.py`, CI and muscle memory all invoke it by name,
and breaking those to make a point about layout would be a poor trade.

    python3 tools/check_pedagogy.py                 # whole repo
    python3 tools/check_pedagogy.py <file.md> ...    # scoped
    python3 tools/check_pedagogy.py --warn-only

Everything else — `--list`, `--only`, `--graph`, `--format sarif` — is on the real entry point:

    cd tools && python3 -m harness --list

The original implementation is preserved as `tools/_legacy_check_pedagogy.py`, and it is not
dead weight: `harness/selftest.py` runs all sixteen moved invariants against it on every
invocation and asserts identical output, which is what makes "moved verbatim" a checked claim
rather than a hope. Delete it only when you are willing to lose that proof.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harness.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
