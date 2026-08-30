# Plan — platform depth: the container floor, and the restructure that was declined

*Written 2026-08-30. Every count below was measured, not estimated: word counts from
[`tools/remeasure.py`](tools/remeasure.py), topic coverage by `grep -rIo` over
`networking-fundamentals/`, `drills/`, `reference/` and `exam-prep/`, and the harness baseline from
[`tools/check_pedagogy.py`](tools/check_pedagogy.py) (**0 failures, 0 warnings** across the whole
course before this work began — the bar anything here has to leave standing).*

> **Status: Phase 0 shipped. Phases 1–4 are proposal.** Read the phase table's Status column, not the
> prose, for what exists.

## Why this document exists

A recommended learning path for "design, secure, debug and operate an enterprise container platform"
was put against this repo, and it proposed splitting the course into three: **Linux internals**,
**Docker internals**, **Kubernetes**. The proposal is declined. The gap audit inside it is not — it
found four real holes, and this plan closes them without the split.

## 1. The split, and why it is declined

The proposal and this course are organised on different axes:

- The proposal is a **taxonomy** — grouped by product boundary. Linux, then containers, then
  Kubernetes, then security, supply chain, delivery, observability.
- This course is a **motivation chain** — [`JOURNEY-MAP.md`](JOURNEY-MAP.md) commits to *"the question
  comes before the answer — always"*, and the River rule forbids using a concept before it is earned.

Reorganising along the taxonomy axis requires abandoning both rules, and the cost is concrete rather
than philosophical:

| Where it lives now | Why it lives there | What a Linux-first track would do to it |
|---|---|---|
| `seccomp`, `capabilities` — Act X, ~250k words in | First point at which the reader has a cluster worth attacking | Teach a confinement mechanism to someone with nothing to confine — the Spirit failure the map says to cut |
| `namespaces` — Act IV L1 | Act III ends on *"one host is a capacity ceiling and a single point of failure"* | Detach the answer from its wall; namespaces become a feature list |
| `overlayfs` — Act I 06b | Falls out of lesson 06's `mount`/VFS capstone | Either duplicate the VFS material or teach layers before files |
| `iptables`/NAT — Act IV L3 | Stateful *because of* `conntrack`, introduced in Act III | Arrives before the table it depends on exists |

There is also precedent that settles it. The repo has already met "I want this material in a different
order" once, and answered it **without forking**:
[`exam-prep/the-exam-path.md`](exam-prep/the-exam-path.md) is Route B over the same words — a step
table pointing into existing lessons, ~2k words of new prose, zero duplicated teaching. A
Linux → containers → Kubernetes ordering is Route C, and it is **a view, not a fork** (Phase 4).

## 2. What the proposal got right

Measured against the repo, most of its list is already taught deeply: `cgroup` 157 hits, `crictl` 159,
`kubeadm` 146, `nftables` 110, `Helm` 101, `Cilium` 68, `cosign` 57, `Falco` 57, `Kyverno` 30. Four
holes are real.

**2.1 The runtime peel is missing — and it is a River break already in flight.**
`docker → dockerd → containerd → shim → runc` is the one chain the course cannot answer. `OCI` is 8
hits across 6 files, `CRI` 7, `ctr` 2, `nerdctl` 1 — all name-drops. Yet Act VI teaches static pods and
leans on `crictl` 159 times. **The reader is driving a runtime layer that was never introduced.** This
is the highest-value item in the plan: it is not an enrichment, it is a defect.

**2.2 Nothing teaches how an image layer is *made*.**
[`act-1/06b`](networking-fundamentals/act-1-one-machine/06b-the-container-filesystem.md) teaches
overlayfs from the `mount` line down — the *read* side.
[`act-10/08`](networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) teaches scanning,
SBOMs and signing — the *verify* side. The build side between them is empty: `BuildKit|buildx` 1 hit,
`docker compose` 1. Act I 06b's own closing claim — that *"image layers retain deleted secrets because
a layer never forgets"* — is a claim about builds, asserted in a course that never builds one.

**2.3 Act IV is the thinnest floor in the course.**
5 lessons, 18,312 words including support pages — against Act X's 87,398 and Act VII's 54,882.
Everything from Act V onward stands on it:

| Act | Lessons | Words (incl. support pages) |
|---|---|---|
| **IV — one pretends to be many** | **5** | **18,312** |
| I — one machine | 8 | 23,850 |
| V — Kubernetes | 12 | 38,049 |
| VII — workloads | 12 | 54,882 |
| X — cluster security | 12 | 87,398 |

**2.4 Observability is a total hole.** `Prometheus`, `Grafana`, `Loki`, `OpenTelemetry` — **zero hits,
all four.** Already flagged as Stage 7.8 roadmap in the map, so this is confirmation rather than news.

## 3. What the proposal named that we keep declining

Recording these so the question does not return every six months.

| Named | Hits | Decision |
|---|---|---|
| **ArgoCD / Flux** | 1 | **Decline.** Act VII 08b builds the reconciliation loop in four lines and thereby shows that self-heal is a *time bound* not a prevention, that a deleted manifest is not a deletion, and that a repo holding tags is not a source of truth. Installing the product teaches less. Reasoned at `JOURNEY-MAP.md` §7.6. |
| **HashiCorp Vault** | 1 | **Decline.** Act X 11 covers external secret stores generically, which is the transferable half; the authoring environment's own policy is 1Password/env vars over Vault. |
| **Terraform / OpenTofu** | 0 | **Defer.** Stage 8–9 material, not a container-platform gap. |
| **Istio / Linkerd** | 6 / 1 | **Decline as install, keep as concept.** Taught at the right altitude already; a mesh install is operational knowledge, not mechanism. |
| **gVisor / Kata** | 12 / 2 | **Keep as named alternative.** Correct depth for "when ordinary containers are not enough". |
| **SPIFFE/SPIRE**, **Syft**, **SLSA**, **in-toto** | 5 / 0 / 2 / 0 | **Thin, deliberately.** Act X 08/08b teach provenance through `cosign` and SBOMs; these are vocabulary around a mechanism already taught. Revisit only if 08b grows a sequel. |

## 4. The per-lesson cost, which nobody guesses

This is the part that makes or breaks the estimate. This repo is not "add a Markdown file" — the
harness gives a new lesson **fifteen** obligations, **thirteen** of them machine-checked. Run `cd tools && python3 -m harness --list` for the live table with the reason each rule exists:

| # | Obligation | Enforced by |
|---|---|---|
| 1 | A `Predict first` marker in the lesson | `shape.predict-first` — **hard** |
| 2 | A milestone (`You can now`…) **≤100 words**, plus a forward pointer (`Next:` / `→`) | `shape.ladder`, `shape.milestone-length` — **hard** |
| 3 | Every relative link resolves | `links.resolve` — **hard** |
| 4 | A line in [`LESSON-INDEX.md`](LESSON-INDEX.md) | `index.freshness` — warn |
| 5 | Act `README.md` nav, and the act's four-file shape intact | `shape.act-files` — **hard**; reachability by `graph.lesson-reachable` — warn |
| 6 | New tool → roster row in [`reference/tools/README.md`](reference/tools/README.md), facets from the **closed** vocabularies: interface ∈ `netlink · procfs · socket · packet · probe · nsapi · httpapi · local`, mode ∈ `read-only · mutate · live` | `reference.index-facets`, `reference.iface-rosters` — warn |
| 7 | New tool → [`reference/capabilities.json`](reference/capabilities.json) entry: `mode`, `standing.level` ∈ `default · superseded · emerging`, `keys` (**max 4**), `caps`, `course` — and the `course[]` citation must name the lesson where the tool is genuinely **introduced**, not merely a notable invocation | `capabilities.standing`, `capabilities.keys`, `graph.course-citation-resolves`, `river.no-uphill-tool` — warn |
| 8 | Tool page regenerated — `tools/gen-tool-pages.py` | `reference.shape` — **hard** |
| 9 | New tool → `SHELL_COMMANDS` in [`site/scripts/sync-content.mjs`](site/scripts/sync-content.mjs), else its fences render as flat plaintext on the site | `commands.table-coverage` — warn |
| 10 | `reference/05-per-act-commands.md` rows — `tools/gen-command-tables.py`, then fill the syntax-breakdown cells | `commands.table-coverage` — warn |
| 11 | Drill in the act's `diagnose.md` + `drills/act-N/NN.sh` + a `tools/verify-drill.sh` verifier | drill-parity convention |
| 12 | [`exam-prep/the-exam-path.md`](exam-prep/the-exam-path.md) step table, per-step words, drill counts; CKA/CKS domain-map rows | hand-maintained |
| 13 | `python3 tools/remeasure.py --write` for every published total | `counts.published` — warn (**Phase 0**) |
| 15 | A lesson stays under **10,000 words** (course median 2,988) | `budget.lesson-words` — warn (**Phase 0**) |
| 14 | Spirit/River pass via the `learner-simulator` agent; every command run for real via `technical-accuracy-checker` | [`.claude/agents/`](.claude/agents/learner-simulator.md) |

**Read item 14 as non-negotiable.** The map's standard is that every lesson has been *run*, and the
`LESSON-INDEX` build-status note names, honestly, the one page in the course whose author never ran it.
A new lesson that is merely written is not shippable here.

**Budget, from measured comparables:** Act IV's existing lessons average 2,400 words; Acts VIII/IX
shipped 6 lessons + support pages at ~31k. So **~3,000–4,000 words per new lesson**, plus items 1–14
each time. Phase 1 is therefore three lessons, not "a bit of Act IV".

## 5. The phases

| Phase | Work | Status |
|---|---|---|
| **0** | This document + the declined-split record in the map; `tools/remeasure.py` and the published-count guard; four stale published figures corrected | ✅ **shipped** |
| **0b** | Harness rebuilt as `tools/harness/` — invariant registry, course graph, River made machine-checkable, self-applying size budgets, SARIF output, parity + mutation selftests | ✅ **shipped** |
| **1** | Act IV: the runtime peel and the build side — three lessons | 🟡 **1 of 3 shipped** |
| **2** | Act XI: observability (Stage 7.8) | 🔜 |
| **3** | Thin spots: user namespaces / rootless, `nsenter`, `systemd` | 🔜 |
| **4** | Route C — the platform ordering, published as a view | 🔜 |

### Phase 0 — shipped

Recorded the declined split in the map's authoring notes, so the question is answered once. Then closed
the measurement hole that made the plan's own estimates untrustworthy: **four files quoted the course's
size and nothing checked any of them**, so they had drifted into three coexisting generations —
`376,651` (map, `exam-prep/README`, `AUDIT` ×2), `386,959` (`the-exam-path`), against a measured
`387,850`. Worse, `the-exam-path.md` called the *same* 30,801-word optional track **8.0%** in its header
and **8.2%** sixty lines down, because the header had been remeasured and the body had not.

`tools/remeasure.py` now derives what is derivable and checks what is not:

```bash
python3 tools/remeasure.py --check
```

It is wired into `check_pedagogy.py` as a **warning** check — deliberately, since warnings run
course-wide only, so editing one lesson never fails on a total that lesson cannot know it moved.
`--check` is the hard gate for CI and pre-publish; `--write` fixes what it finds.

`AUDIT.md`'s figures were **not** overwritten — that file declares itself kept unedited, because an
audit rewritten after the fact stops being evidence. They are stamped as-of instead, so they read as
history rather than as live claims.

*Not automated, and the reason matters:* Route B's per-step figures are measured over a file set the
step table names only in prose, and that prose does not reproduce them — step 1 reads "Orientation,
Act I, Act IV", but those three directories sum to 46,834 against a published 46,795. Some rule
excludes 39 words and is written down nowhere. Guessing it would replace a stale number with a
confident wrong one. The script checks the arithmetic those figures must satisfy internally and warns
when the course total moves underneath them. **Encoding the step→file map as data, and generating that
table, is the honest fix and is unclaimed work.**

### Phase 0b — the harness, rebuilt rather than extended

Phase 0 added a check to a file that was already 970 lines and nineteen checks. That was the wrong
move and the file said so itself: it carried four separate copies of the roster's path, with a
comment explaining that a rename had once disabled three checks *without failing anything*. Size
caused that. So the harness is now a package under [`tools/harness/`](tools/README.md), one module
per concern, and **it applies a size budget to itself** — 350 lines, which is what makes
`invariants/capabilities.py` at 310 visible as the next thing to split rather than the place the
next 200 lines quietly go.

What the restructure bought, beyond layout:

- **An invariant registry.** Every rule carries an id, a severity, a scope and a *rationale*. The
  flat `HARD_CHECKS`/`WARN_CHECKS` lists could not express any of those, and the missing `scope`
  was a live bug: warning checks silently did not run on a single-file save, so the save hook
  checked less than the author believed. A scoped run now says what it deferred.
- **A course graph** — reading order, tool introduction points, uses, citation edges — which turns
  ordering questions into graph questions. Prerequisite validation as a DAG is well-trodden ground
  in curriculum design; this is that, over 86 lessons.
- **River, machine-checked for the first time.** Previously abandoned to the semantic layer. See
  below — this is the substantive win and it cost one insight, not a new data file.
- **SARIF 2.1.0 output**, so findings land on the right line of the right file in a pull request
  instead of in terminal scrollback.
- **Parity and mutation selftests.** All sixteen moved invariants are compared against the retained
  original on every run (**16/16 identical**), and five are checked by breaking the repo in a temp
  clone and asserting they fire (**5/5**). A green run only means something if the rules can still
  go red.

**River, and the one insight it needed.** The old harness declined to check the course's most
important rule and gave a reason worth keeping: lexical checks "produce false positives on exactly
the best-written lessons." That is true of prose and false of *fenced blocks*. A lesson that writes
"we will meet `nft` in Act IV" has not used it; a lesson with `nft list ruleset` in a fence has
handed the reader something to run. The distinction is structural, so it is decidable — and it
needs no new authoring, because `capabilities.json` has been recording introduction points all
along for another purpose.

Measured, in the order the mistakes were made: counting inline spans as uses gave **14** findings,
including `conntrack` in Act I 05b and `iptables` in Act III 02b — **both deliberate seeds**, and
Act III 02b's sentence reads "**Act IV builds it**". Exactly the false positive the old comment
predicted. Fences-only: **8**. Resolving lab-setup citations (`docker`'s introduction is declared
as "Starting the lab", which the first parser skipped): **6**. A declared baseline of assumed
coreutils — `cat`, `pgrep`, `readlink`, each with a stated reason: **1**.

That one is real, and it is left unsilenced: `nc` is taught in a fenced block in orientation
lesson 02 — `LESSON-INDEX.md` agrees it debuts there — but `capabilities.json`'s earliest citation
for it is Act I 05b. Either the citation understates where the tool is introduced, or the use is
uphill. It is a data question in the reference wing, so it is surfaced rather than decided here.

### Phase 1 — Act IV: the runtime peel and the build side

Three lessons, appended **after** the by-hand work, so each lands as recognition rather than
instruction. That placement is what keeps the River intact: the reader has already built namespaces,
cgroups, veth and NAT with their own hands in 01–03, so the runtime arrives as *"here is who does that
for you, and the contract they agreed on"* — an earned rival to their own labour, which is the method's
strongest move and is currently unused in this act.

- **`05-who-does-this-for-you.md`** ✅ **shipped.** Runs `runc` directly from an OCI bundle
  (`skopeo`/`umoci`, no Docker in the loop), then `containerd`/`ctr`, and proves equivalence with
  lessons 01–02 by the tool the reader already owns — the `/proc/<pid>/ns/net` inode read, differing
  from the shell's own — plus the cgroup leaf `0::/box` and UTS isolation. Closes on the **OCI runtime
  spec** as the contract, and redeems Act X 02's promissory note early (`runc` was named there only
  inside a Kubernetes error message; here it is run directly).

  **The open question resolved itself against evidence rather than needing a decision.** Act IV's lab
  invocation is already `docker run --privileged --network host nicolaka/netshoot` — checked directly
  in `networking-fundamentals/act-4-one-pretends-many/01-namespaces.md` — so no new lab variant was
  needed. `apk add runc containerd containerd-ctr skopeo umoci jq` and every command in the lesson was
  run for real in that exact container before being written down. The one genuine constraint met along
  the way: `ctr run` under containerd's `overlayfs` snapshotter fails inside Docker Desktop's own VM
  (`mount ... invalid argument`, nested overlay on its backing filesystem) and the `native` snapshotter
  then hits a cgroup v2 "domain invalid" error from the nesting — both real, both avoided by keeping
  the verified walkthrough on bare `runc` plus `ctr` for image operations only, the same
  honest-constraint move Act I 06b already models for `docker diff`.

  Fourteen of fifteen obligations closed as part of shipping it: `runc`'s `capabilities.json` entry
  (previously `course: []` — roster-only, never taught) now cites this lesson; `ctr` and `containerd`
  are new entries; both gained roster rows in `reference/tools/README.md` and a place in
  `reference/tools/httpapi/README.md`'s layering table; `lab-inventory.json` was regenerated for real
  against `netlab:latest` (`present: false` — correct, since it needs `netshoot`, not `netlab`);
  `sync-content.mjs`'s `SHELL_COMMANDS` got `ctr`, `containerd`, `skopeo`, `umoci`, `apk`; test-yourself
  gained question 7; the act README nav and both lessons' footer links were rewired
  (`04 → 05 → test-yourself`). **Not closed:** no `diagnose.md` drill. Building one to this repo's own
  bar — "a real, reproduced broken state... verify it runs on the real kernel before it ships," with a
  `verify-drill.sh` SHA-256 cause hash — is separable work, tracked below rather than rushed.

- **`06-the-kubelets-side.md`** 🔜 **not started.** The same contract seen from above: **CRI**. This is
  the lesson that turns Act V's CNI-as-callback and Act VI's 159 uses of `crictl` from incantation into
  recognition. Fixes the River break in §2.1 directly. Lesson 05 already surfaced the exact question it
  answers, in its own closing line: *"What decides which runtime a node uses... has a name of its own:
  the Container Runtime Interface."*
- **`07-how-a-layer-is-made.md`** 🔜 **not started.** The missing middle between Act I 06b and Act X 08.
  `Dockerfile` → BuildKit → layers, then read back with the `lowerdir` skill they already own. Ends by
  *demonstrating* the deleted-secret-in-a-layer claim Act I 06b currently only asserts.

**Outstanding from shipping 05, tracked rather than dropped:**
1. A `diagnose.md` drill and `drills/act-4/05.sh` — candidate symptom: *"a container is running but
   `docker ps` shows nothing"* (started with bare `runc`), which is the exact thing lesson 05 measured.
2. Route B's step-1 word count (`exam-prep/the-exam-path.md`) was **not** hand-adjusted. Attempting it
   exposed the gap `tools/remeasure.py` already documented: summing "Orientation, Act I, Act IV" gives
   a number that has never matched the published figure by a margin nothing in the repo explains, so
   patching it now would trade one unexplained number for another. `tools/remeasure.py --check` reports
   this honestly as "6,063 words are on neither Route B's path nor its optional track" — a real gap,
   correctly surfaced as a warning rather than silently absorbed. Encoding the step→file map as data
   (§ Phase 0b) is the actual fix and remains unclaimed.

### Phase 2 — Act XI: observability (Stage 7.8)

The motivated entry already exists and is unused: Act V's debugging discipline and Act VI's diagnostic
walk both end at *"I can debug one path I am already looking at."* Observability answers the wall
neither reaches — **how do I know before someone tells me?** Size against Act VIII (6 lessons, 32,169
words with support pages) as the realistic floor, not the ceiling. Full act shape required by
`check_act_shape`: README + test-yourself + diagnose + in-the-wild, plus drills.

### Phase 3 — thin spots

User namespaces / rootless (6 hits) into Act X 01, where "what UID?" is already the question.
`nsenter` deepened in Act IV — the by-hand mechanism under `exec`, and already on the map's own
shortlist. `systemd` (15 hits) where Act VI's static pods need it.

### Phase 4 — Route C, as a view

The platform ordering as a third route file, same pattern as `the-exam-path.md`: a step table pointing
into existing lessons, no duplicated prose. This is what actually satisfies the original proposal, at
~2k words instead of a fork. Do it **last** — a view over material still in motion goes stale before
it is read.

## 6. Sequencing note

Phase 1 lands three lessons in the act that Route B's step 1 calls *"non-negotiable"*, so it moves the
CKA path's word count and its drill count. Run `tools/remeasure.py --write` and revisit
`the-exam-path.md`'s step 1 row in the same commit, or the repo re-acquires the exact defect Phase 0
just removed.
