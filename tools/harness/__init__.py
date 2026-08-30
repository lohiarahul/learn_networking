"""The learn_networking pedagogy harness.

A set of architecture fitness functions over a course: executable rules that guard the teaching
method the way unit tests guard behaviour. The split it is built around comes from the same
literature — **deterministic gates for objective invariants, agentic judges for evidence-bound
interpretation**. This package is the gates. The `learner-simulator` and
`technical-accuracy-checker` agents in `.claude/agents/` are the judges, and the division is not
an accident of tooling: Spirit ("does this keep the reader's drive alive?") is judgement, and a
regex that pretends otherwise fails on the best writing in the repo.

Layout, each module bounded by `invariants/budgets.py`:

    paths.py       every path, resolved once
    model.py       closed vocabularies, Finding, Invariant
    corpus.py      cached file access; fenced-block vs inline-span separation
    parsing.py     shared table parsers
    graph.py       the course as a graph: reading order, introductions, uses, citations
    registry.py    the invariant registry and runner
    report.py      human / JSON / SARIF 2.1.0
    cli.py         one entry point
    invariants/    one module per concern, registered in invariants/__init__.py
"""
from .model import FAIL, WARN, Finding, Invariant       # noqa: F401
from .registry import REGISTRY                          # noqa: F401

__version__ = "2.0.0"
