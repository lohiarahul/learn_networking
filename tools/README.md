# The build harness

This directory keeps the `learn_networking` pedagogy from drifting. The course has a precise,
written pedagogy (`JOURNEY-MAP.md` §"How we learn here" and the "Three checks"); this harness turns
as much of it as possible into checks that run automatically, so new content can't quietly fall
below Act I's standard the way later acts once did.

## The split: structure is deterministic, meaning is semantic

The single most important design decision here: **do not regex-gate the semantic rules.** A lexical
"does this lesson have a feedback loop?" check flags Act I's *best* lessons as failures, because they
phrase success in prose (`three of these four succeed — which?`) that no keyword list can catch. So:

| Layer | What it checks | How | Gate? |
|---|---|---|---|
| **Structure** | links resolve, act-shape complete, every lesson has a prediction + a ladder rung | `check_pedagogy.py` (deterministic) | **hard fail** |
| **Freshness** | lessons indexed, roadmap banner present | `check_pedagogy.py` (warnings) | warn only |
| **Meaning** | Spirit (drive kept alive?), River (nothing uphill?), does the feedback loop land? | learner-simulator **agent** | human-reviewed |
| **Correctness** | do the command blocks actually produce the stated output? | technical-accuracy-checker **agent** (runs them in the lab image) | human-reviewed |

## `check_pedagogy.py` — the deterministic gate

```
python3 tools/check_pedagogy.py                 # whole course
python3 tools/check_pedagogy.py <file.md> ...    # only these files (used by the save hook)
python3 tools/check_pedagogy.py --warn-only      # report, never exit non-zero
```

Hard invariants (exit non-zero on any failure):

1. **link-integrity** — every relative `](…)` target resolves. *(Would have caught the three dead
   `the-whole-stack.md` links and the missing `networking-fundamentals/README.md`.)*
2. **act-shape** — every act carries `README` + `test-yourself` + `diagnose` + `in-the-wild`
   (Act V exempt from `diagnose`: it folds the drills into `08/09-debugging`). *(Would have caught
   the missing Act 3/4 `diagnose.md` and Act 4 `in-the-wild.md`.)*
3. **has-prediction** — every teaching lesson contains a "Predict first". Setup/method/orientation
   pages are listed in `PREDICTION_EXEMPT`.
4. **ladder-ends** — every lesson has a milestone marker ("you can now" / "you understand this when"
   / …) **and** a forward pointer (`Next:`).

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
- **pedagogy-linter** — wraps `check_pedagogy.py` and explains failures in prose.
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

> This repo is not yet a git repository, so the CI workflow lies dormant until `git init`. The
> save-time hook and the scripts work today.
