"""Three renderings of the same findings: terminal, JSON, SARIF.

SARIF 2.1.0 is the OASIS standard for static-analysis output, and GitHub, Azure DevOps and IDE
extensions consume it directly. Emitting it is what turns this harness from "a script whose
output you read in a terminal" into findings that appear on the right line of the right file in
a pull request. That is the single largest ergonomic difference available here, and it costs one
function, because `Finding` carries a path.
"""
from __future__ import annotations
import json

from .model import FAIL, Finding

TOOL_NAME = "learn_networking pedagogy harness"
TOOL_VERSION = "2.0.0"
INFO_URI = "https://github.com/kaluza-platform/learn_networking"


def human(findings: list[Finding], *, scope: str, deferred: list = (), verbose: bool = False) -> str:
    fails = [f for f in findings if f.severity == FAIL]
    warns = [f for f in findings if f.severity != FAIL]
    out = []
    for f in fails:
        out.append(f"  ✗ FAIL  [{f.invariant}] {f.message}")
    for f in warns:
        out.append(f"  ⚠ warn  [{f.invariant}] {f.message}")
    if deferred:
        # One line, not eighteen ids: this prints on every save via the PostToolUse hook, and a
        # gate that shouts on success is a gate people learn to scroll past. `--verbose` names them.
        note = f"  … {len(deferred)} repo-wide invariant(s) deferred (run with no file args)"
        if verbose:
            note += ":\n    " + ", ".join(i.id for i in deferred)
        out.append(note)
    if not findings:
        out.append(f"✓ every invariant holds ({scope})")
    else:
        out.append(f"\n{len(fails)} failure(s), {len(warns)} warning(s) over {scope}")
    return "\n".join(out)


def as_json(findings: list[Finding], *, scope: str) -> str:
    return json.dumps({
        "scope": scope,
        "failures": sum(1 for f in findings if f.severity == FAIL),
        "warnings": sum(1 for f in findings if f.severity != FAIL),
        "findings": [{"invariant": f.invariant, "severity": f.severity, "message": f.message,
                      "path": f.path, "line": f.line} for f in findings],
    }, indent=2)


def sarif(findings: list[Finding], registry) -> str:
    """SARIF 2.1.0. Rules carry each invariant's rationale, so a reader of the PR annotation gets
    the *reason* the rule exists rather than only the violation."""
    rules, seen = [], set()
    for inv in registry.all():
        if inv.id in seen:
            continue
        seen.add(inv.id)
        rules.append({
            "id": inv.id,
            "shortDescription": {"text": inv.id.replace(".", " — ").replace("-", " ")},
            "fullDescription": {"text": inv.rationale or inv.id},
            "defaultConfiguration": {
                "level": "error" if inv.severity == FAIL else "warning"},
            "properties": {"scope": inv.scope, "tags": list(inv.tags)},
        })

    results = []
    for f in findings:
        result = {
            "ruleId": f.invariant,
            "level": "error" if f.severity == FAIL else "warning",
            "message": {"text": f.message},
        }
        if f.path:
            region = {"startLine": f.line} if f.line else {"startLine": 1}
            result["locations"] = [{"physicalLocation": {
                "artifactLocation": {"uri": f.path},
                "region": region}}]
        results.append(result)

    return json.dumps({
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": TOOL_NAME, "version": TOOL_VERSION,
                                "informationUri": INFO_URI, "rules": rules}},
            "results": results,
        }],
    }, indent=2)
