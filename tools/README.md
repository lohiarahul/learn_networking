# The build harness

This directory keeps the `learn_networking` pedagogy from drifting. The course has a precise,
written pedagogy (`JOURNEY-MAP.md` §"How we learn here" and the "Three checks"); this harness turns
as much of it as possible into checks that run automatically, so new content can't quietly fall
below Act I's standard the way later acts once did.

## The split: structure is deterministic, meaning is semantic

The single most important design decision here: **do not regex-gate the semantic rules.** A lexical
"does this lesson have a feedback loop?" check flags Act I's *best* lessons as failures, because they
phrase success in prose (`three of these four succeed — which?`) that no keyword list can catch. So:

That split has a name in the literature — **deterministic gates for objective invariants,
agentic judges for evidence-bound interpretation** — and this repo arrived at it independently
before adopting the vocabulary. The gates are `harness/`; the judges are the agents.

| Layer | What it checks | How | Gate? |
|---|---|---|---|
| **Structure** | links resolve, act-shape complete, every lesson has a prediction + a ladder rung | `harness/invariants/` (deterministic) | **hard fail** |
| **Order** | River: nothing hands the reader a tool they have not been given — *fenced blocks only* | `harness/invariants/river.py` over `harness/graph.py` | warn (declared exceptions) |
| **Budgets** | no harness module past 350 lines, no lesson past 10,000 words, every declared path exists | `harness/invariants/budgets.py` | **hard fail** (module/path) |
| **Freshness** | lessons indexed, roadmap banner present, published word counts match measurement | `harness/invariants/` (warnings) | warn only |
| **Meaning** | Spirit (drive kept alive?), does the feedback loop land? | learner-simulator **agent** | human-reviewed |
| **Correctness** | do the command blocks actually produce the stated output? | technical-accuracy-checker **agent** (runs them in the lab image) | human-reviewed |

**River moved layers, and that is the substantive change.** It used to sit entirely in the
semantic column with a stated reason: lexical checks "produce false positives on exactly the
best-written lessons." That reason is right about prose and wrong about *fenced blocks*. A lesson
that writes "we will meet `nft` in Act IV" has not used it; a lesson with `nft list ruleset` in a
fence has handed the reader something to run. Measured while building it: counting inline spans
as uses produced 14 findings, the two most interesting of which were `conntrack` in Act I 05b and
`iptables` in Act III 02b — **both deliberate seeds**, one of which says "**Act IV builds it**" in
the same sentence. Fences-only, plus resolving lab-setup citations, took 14 → 6 → 1. The one that
survives is real. Spirit stays semantic, permanently.

## `harness/` — the deterministic gate

```
cd tools && python3 -m harness              # every invariant, whole repo
cd tools && python3 -m harness --list       # the rule table, with the reason each rule exists
cd tools && python3 -m harness --graph      # what the course graph knows
cd tools && python3 -m harness --only river.no-uphill-tool
cd tools && python3 -m harness --format sarif > harness.sarif
cd tools && python3 -m harness.selftest     # parity vs the old monolith + mutation tests
```

`tools/check_pedagogy.py` still works and still takes the same arguments — the save hook, CI and
muscle memory all call it by name — but it is now a shim over `harness.cli`.

**Layout.** One module per concern, each bounded by `budgets.py` at 350 lines. The file this
replaced was **970 lines and nineteen checks**, and the cost was not aesthetic: it held four
separate copies of the roster's path and *said so in its own comments*, having noticed that a
rename disabled three checks without failing anything. A file you cannot hold in your head is a
file whose duplication you cannot see, so the harness now applies a size budget to itself.

```
paths.py       every path, resolved once
model.py       closed vocabularies, Finding, Invariant
corpus.py      cached file access; fenced-block vs inline-span separation
parsing.py     shared table parsers
graph.py       the course as a graph — reading order, introductions, uses, citations
registry.py    the invariant registry and runner
report.py      human / JSON / SARIF 2.1.0
cli.py         one entry point
invariants/    one module per concern; the registration table is invariants/__init__.py
selftest.py    parity + mutation — who checks the checkers
```

**Three things the flat `HARD_CHECKS`/`WARN_CHECKS` lists could not do.** Severity used to be a
property of *which list* a function sat in, which meant: scope was implicit, so a single-file save
silently skipped every warning check and the author believed otherwise — now scope is declared and
a scoped run *names what it deferred*; a check could not fail on one condition and warn on another;
and nothing could describe itself, so `--list` was impossible and a rule whose reason nobody could
state was a rule the next author deleted. Every invariant now carries an id, a scope and a
rationale, and `report.py` puts the rationale in the SARIF rule so a PR annotation explains itself.

**`_legacy_check_pedagogy.py` is not dead weight.** `selftest.py` runs all sixteen moved invariants
against it on every invocation and asserts identical output, so "moved verbatim" is a checked claim
rather than a hope. It reports **16/16 parity, 5/5 mutations firing**. Delete the legacy file only
when you are willing to lose that proof.

Hard invariants (exit non-zero on any failure):

1. **link-integrity** — every relative `](…)` target resolves. *(Would have caught the three dead
   `the-whole-stack.md` links and the missing `networking-fundamentals/README.md`.)*
2. **act-shape** — every act carries `README` + `test-yourself` + `diagnose` + `in-the-wild`, with
   **no exemptions**. Act V used to fold its drills into `08/09-debugging`; those are a method and a
   worked example, so it now has a real `diagnose.md` and the invariant is enforced everywhere.
   *(Would have caught the missing Act 3/4 `diagnose.md` and Act 4 `in-the-wild.md`.)*
3. **has-prediction** — every teaching lesson contains a "Predict first". Setup/method/orientation
   pages are listed in `PREDICTION_EXEMPT`.
4. **ladder-ends** — every lesson has a milestone marker ("you can now" / "you understand this when"
   / …) **and** a forward pointer (`Next:`).

Invariants 3 and 4 are scoped by `is_lesson()`: a lesson is a numbered file **inside
`networking-fundamentals/`**. That scoping is deliberate — `exam-prep/` holds rehearsal for a timed
certification exam, which is *banking* by design (memorised flags, speed, recall under a clock) and
is exactly what the Spirit rule forbids in a lesson. Holding it to Predict-first would be
incoherent. Link integrity (invariant 1) still covers `exam-prep/`, because its domain maps link
into real lessons and a dead link there is a genuine defect.

Warnings (surface drift, never fail the build): **index-freshness** (lesson referenced in
`LESSON-INDEX.md`), **map-vs-build** (the roadmap banner exists so unbuilt stages read honestly).

Calibrated so the current course passes clean (`exit 0`); a deliberately broken lesson fails with
one message per violated invariant.

## `new-lesson.py` — pass by construction

```
python3 tools/new-lesson.py act-3-the-internet 06 "HTTP caching" http-caching
```

Scaffolds a lesson pre-loaded with the required skeleton (a "Predict first" block, a "you can now"
milestone, a `Next:` footer) and appends its one-line entry to `LESSON-INDEX.md` — so a fresh lesson
starts life passing act-shape / prediction / ladder / index-freshness, and the author only has to
write the teaching.

## The agents (semantic layer — `.claude/agents/`)

The judgement-heavy checks are sub-agents, invoked on demand or in CI, not on every save:

- **learner-simulator** — given only the anchor knowledge + prior lessons, tries to answer the
  lesson's own "you understand this when" test and flags any term/tool used before it was introduced.
  This is the only reliable proxy for **Spirit** and **River**.
- **technical-accuracy-checker** — runs every command block inside the real lab image
  (`netlab` / `nicolaka/netshoot` / `kind`) and confirms the stated "you should see X" appears.
  Keeps the drills "verified on the real kernel," as the JOURNEY-MAP demands.
- **pedagogy-linter** — wraps the harness and explains failures in prose.
- **exercise-generator** — drafts the matching `test-yourself` question and `diagnose` drill for a
  new lesson, so the act shape stays complete.

## Where the checks fire (hooks)

- **On save** — a `PostToolUse` hook on `Write`/`Edit` of `**/*.md` runs the fast deterministic subset
  on the edited file. Add to `.claude/settings.json` (use the `update-config` skill, or paste):
  ```json
  {
    "hooks": {
      "PostToolUse": [
        {
          "matcher": "Write|Edit",
          "hooks": [
            {
              "type": "command",
              "command": "f=\"$CLAUDE_TOOL_FILE_PATH\"; case \"$f\" in *.md) python3 \"$CLAUDE_PROJECT_DIR/tools/check_pedagogy.py\" \"$f\";; esac"
            }
          ]
        }
      ]
    }
  }
  ```
- **On PR / pre-push** — `.github/workflows/pedagogy.yml` runs the full course-wide check. The
  correctness + learner-sim agents run here too (needs Docker/`kind` in the runner).
- **On new-lesson** — `new-lesson.py` scaffolds the invariants in from the start.

> The save-time hook, the scripts, and the CI workflow all work today. (An earlier version of this
> note said the repo was not yet under git — that has been true for a while now and the workflow
> is live.)
