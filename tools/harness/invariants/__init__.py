"""The registration table — the one page to read to know what this harness enforces.

Metadata lives here rather than as decorators on each function, on purpose: the whole point of
the rewrite is that you can see the entire rule set at once. Nineteen checks scattered across two
flat lists is how the previous harness became unreadable.

`rationale` is required in spirit even though Python cannot require it: every invariant here
exists because something actually went wrong once, and a rule whose reason nobody can state is a
rule the next author deletes.
"""
from __future__ import annotations

from ..model import FAIL, WARN, FILE, REPO_WIDE
from ..registry import REGISTRY
from . import (budgets, capabilities, commands, freshness, illustrations, links,
               reference_roster, river, shape)
from . import counts

_TABLE = [
    # ── Hard gates: the shape of a lesson, and the integrity of what points at it ──────────
    ("links.resolve", links.check_links, FAIL, FILE,
     "A relative link that does not resolve is a 404 for a reader and a lie in a reference table."),
    ("shape.act-files", shape.check_act_shape, FAIL, REPO_WIDE,
     "An act missing test-yourself/diagnose/in-the-wild promises drills the site does not have."),
    ("shape.predict-first", shape.check_prediction, FAIL, FILE,
     "A lesson with no prediction hands over an answer to a question the reader does not hold."),
    ("shape.ladder", shape.check_ladder, FAIL, FILE,
     "Every lesson closes its rung: a milestone to self-assess against, and the next question."),
    ("shape.milestone-length", shape.check_milestone_length, FAIL, FILE,
     "A milestone over 100 words has become a recap; nobody self-assesses against 18 bullets."),
    ("reference.shape", reference_roster.check_reference_shape, FAIL, REPO_WIDE,
     "The guard on the guards: if the roster moved, the checks reading it check nothing."),
    ("budget.harness-module-lines", budgets.check_module_budget, FAIL, REPO_WIDE,
     "No harness module past 350 lines. The file this package replaced reached 970."),
    ("budget.declared-path-exists", budgets.check_declared_paths, FAIL, REPO_WIDE,
     "A checker whose target has moved passes silently, which is the worst available outcome."),

    # ── Calibrated signals: drift a human should judge ─────────────────────────────────────
    ("river.no-uphill-tool", river.check_river, WARN, REPO_WIDE,
     "Nothing may hand the reader a tool they have not been given. Fenced blocks only — an "
     "inline span is a mention, and counting those flags the best-written seeds."),
    ("graph.course-citation-resolves", river.check_course_citations, WARN, REPO_WIDE,
     "Link integrity cannot reach inside JSON; a citation to a renamed lesson is a lie in a table."),
    ("graph.lesson-reachable", river.check_lesson_reachable, WARN, REPO_WIDE,
     "A lesson linked from nothing is a lesson no reader arrives at."),
    ("index.freshness", freshness.check_index_freshness, WARN, REPO_WIDE,
     "A lesson absent from LESSON-INDEX cannot be found without reading the whole course."),
    ("map.vs-build", freshness.check_map_vs_build, WARN, REPO_WIDE,
     "Unbuilt stages must read as unbuilt, or the map promises road that is not paved."),
    ("counts.published", counts.check_wordcounts, WARN, REPO_WIDE,
     "Four files quoted the course's size and none was checked; they drifted three generations."),
    ("commands.table-coverage", commands.check_command_table_coverage, WARN, REPO_WIDE,
     "A tool missing from SHELL_COMMANDS is documented as runnable and rendered as plaintext."),
    ("commands.runnable-citations", commands.check_runnable_citations, WARN, REPO_WIDE,
     "A cited man page that does not exist in the lab is a dead end mid-lesson."),
    ("reference.iface-rosters", reference_roster.check_iface_rosters, WARN, REPO_WIDE,
     "Each interface page must list exactly the tools that speak it."),
    ("reference.index-facets", reference_roster.check_index_facets, WARN, REPO_WIDE,
     "Closed vocabularies: a value outside the set is the bug, not a new category."),
    ("capabilities.standing", capabilities.check_standing, WARN, REPO_WIDE,
     "A tool recommended as current must still be current, and the repo must show its work."),
    ("capabilities.keys", capabilities.check_keys, WARN, REPO_WIDE,
     "At most four keys per tool, and each must appear in a command the course actually runs."),
    ("illustrations.placement", illustrations.check_illustration_placement, WARN, REPO_WIDE,
     "An illustration referenced by nothing is either unplaced or unfindable."),
    ("budget.lesson-words", budgets.check_lesson_budget, WARN, REPO_WIDE,
     "A lesson far past the course's distribution is two lessons wearing one filename."),
]

for _id, _fn, _sev, _scope, _why in _TABLE:
    REGISTRY.register(_id, _fn, severity=_sev, scope=_scope, rationale=_why)
