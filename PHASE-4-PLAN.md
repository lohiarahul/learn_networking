# Plan — Phase 4: Route C, the platform ordering, published as a view

*Written 2026-08-31, as the detailed design for Phase 4 of
[`PLATFORM-DEPTH-PLAN.md`](PLATFORM-DEPTH-PLAN.md). Every count below was measured, not estimated:
word counts by [`tools/remeasure.py`](tools/remeasure.py) and `wc -w`; the route validations in §4 by
running the real course graph from [`tools/harness/graph.py`](tools/harness/graph.py) over candidate
orderings; the historical figures in §3 by `git show` at the two commits named there. Where a number
here disagrees with a number published in the repo, §2 says which one is wrong.*

> **Status: proposal.** Nothing here is shipped. Unlike Phases 1–3, this phase adds **no lesson and no
> new teaching** — Route C is a view over material that already exists, which is the whole reason the
> original split was declined. What it does add is roughly 2,000 words of route prose and a piece of
> tooling the repo has owed itself since Phase 0.
>
> Read §2 before §5. The shape of this phase changed while it was being designed: Phase 0 wrote Route C
> down as "a step table pointing into existing lessons, no duplicated prose," and that is still the
> deliverable — but **Route B, the precedent it copies, has meanwhile gone stale by 13,087 words in its
> first row alone.** Shipping a second hand-maintained route table on top of a first one that has
> already drifted would be building the defect twice. So Phase 4 is two things now, and the tooling half
> comes first.

---

## 1. What Phase 4 is

The declined proposal ([`PLATFORM-DEPTH-PLAN.md`](PLATFORM-DEPTH-PLAN.md) §1) wanted the course split
into three: Linux internals, Docker internals, Kubernetes. The decline stands and its reasoning is
recorded. What the decline conceded is that the *request* underneath the proposal is legitimate — a
platform engineer arriving at this repo wants the container floor before the internet, and the course
gives them ARP first.

The repo has answered "I want this material in a different order" once already, without forking:
[`exam-prep/the-exam-path.md`](exam-prep/the-exam-path.md) is Route B, ~1,900 words of new prose
pointing into 437,040 words of existing lessons. Route C is the same move for the platform ordering.

**The sequencing instruction from Phase 0 is now satisfied.** It read: *"Do it last — a view over
material still in motion goes stale before it is read."* Phases 1, 2 and 3 are all shipped; the
last content commit is `99d98f9`; the working tree is clean. The material has stopped moving.

## 2. Route B has gone stale, and this is the measurement that reshapes the phase

Route B's step table is hand-maintained. Nothing checks it. Here is what it now claims against what
the files now contain:

| Route B claim | Published | Measured 2026-08-31 | Drift |
|---|---|---|---|
| Step 1 words — "Orientation, Act I, Act IV" | 46,795 | **59,882** | **+13,087** |
| Step 1 drills | 7 | **12** (Act I 3 + Act IV 9) | +5 |
| Total drills in the repo | 67 | **83** | +16 |
| `JOURNEY-MAP.md` banner: optional track share | 11% | **15.0%** (the route page's own figure) | banner never remeasured |
| Words on neither the path nor the optional track | — | **15,103** | `remeasure.py --check` **fails** on this today |

Reproduce the last row:

```bash
python3 tools/remeasure.py --check
```

```
  ✗ wordcount: 15,103 words are on neither Route B's path nor its optional track — the step
    figures were measured against a smaller course and want remeasuring

1 stale or unverifiable claim(s)
```

The drift is not mysterious: Act IV went from 18,312 words to 31,340 across Phases 1 and 3, and Route
B's step 1 is *"Orientation, Act I, Act IV"* in prose. Every phase that added a lesson to a named act
moved a number in a table nobody regenerated, and the depth plan tracked this honestly at each phase
(6,063 → 10,644 → 15,103) without ever fixing it, because the fix was believed to be blocked. §3 is
about that belief.

**Why this reshapes Phase 4.** Route C is a *finer* view than Route B — §5 splits Act IV in half at
lesson granularity, because that split is the entire point of a platform ordering. A hand-measured
table over half-acts cannot be kept honest by anybody, including its author. So the step→file map goes
in as data first, and both routes are generated from it.

## 3. The blocker that has held the honest fix for four phases does not reproduce

Encoding the step→file map as data has been named as "the honest fix" and left "unclaimed" since Phase
0. The stated reason is a specific number.
[`tools/remeasure.py`](tools/remeasure.py)'s docstring, and `PLATFORM-DEPTH-PLAN.md` §Phase 0 after it,
say:

> step 1 reads "Orientation, Act I, Act IV", but summing those three directories gives 46,834 against a
> published 46,795 — so the real scope excludes something by a rule stated nowhere. Guessing it would
> replace a stale number with a confident wrong one.

That reasoning is exactly right in principle. The number appears to be wrong in fact. Summed at the
commit that published `46,795`, and again at the commit that introduced the `46,834` claim:

```bash
git log -S"46,795" --oneline -- exam-prep/the-exam-path.md      # → 39f5671
for c in 39f5671 455734a; do
  git ls-tree -r --name-only $c -- \
    networking-fundamentals/00-orientation \
    networking-fundamentals/act-1-one-machine \
    networking-fundamentals/act-4-one-pretends-many \
  | grep '\.md$' | while read f; do git show $c:"$f" | wc -w; done \
  | paste -sd+ - | bc
done
```

```
46795
46795
```

**At both commits the three directories sum to exactly the published figure.** The 39-word exclusion
has no rule behind it because there is nothing to exclude. `wc -w` and Python's `len(read().split())`
were also checked against each other over the same 29 files and agree to the word (delta `0`), so the
discrepancy is not a counting-method artifact either.

**Stated as carefully as the evidence allows:** the `46,834` figure cannot be reproduced at either
commit that matters, so the documented blocker is unfounded and the step→file map is buildable. It is
still possible the original author summed a fourth directory or a different file set and mis-attributed
the result; **the first task of §7 is to try once more to reproduce `46,834` before deleting the
caveat**, and if it reproduces under some file set, that file set is the answer and goes in as data.
Either way the caveat stops being a reason to defer.

This matters beyond arithmetic. A blocker written down once, cited by three subsequent plan documents,
and never re-tested is the same failure mode as a stale word count — a number that stopped being
checked.

## 4. Route C, validated against the course graph rather than argued

Phase 0b built a course graph: 100 lessons, 40 tools with recorded introduction points, tool uses
counted **inside fenced blocks only**. That machinery was built for
[`river.py`](tools/harness/invariants/river.py) to check Route A. It also answers the question Route C
actually turns on — *does this ordering hand the reader anything they have not been given?* — for any
proposed ordering, not just the written one.

Two candidate orderings were run through it.

**C-naive** — whole acts, the proposal's own taxonomy: Orientation, I, **IV**, II, III, V, VI, VII,
VIII, IX, X, XI.

**C-split** — Act IV cut in half at the point where its own subject changes: Orientation, I,
**IV 01, 01b**, **IV 05, 05b, 05c, 07**, II, III, **IV 02, 03, 04, 06**, V, VI, VII, VIII, IX, X, XI.

### 4.1 Tool flow

Uphill tool uses — a tool run in a fenced block before the lesson the reference cites as its
introduction, `river.BASELINE` coreutils excluded:

| Ordering | Uphill tool uses | Which |
|---|---|---|
| **Route A** (as written) | **1** | `nc` in orientation 02 — the one already declared in `river.DECLARED_SEEDS` with a reason |
| **C-naive** | **3** | the declared `nc`, plus `tcpdump` in Act IV `04` and `05b` |
| **C-split** | **2** | the declared `nc`, plus `tcpdump` in Act IV `05b` |

C-split's single new finding is not a packet capture:

```bash
nsenter -t $PID -n which tcpdump
```

`05b` runs `which tcpdump` to prove that a namespace-entering process keeps *its own* filesystem — the
netshoot use case. It never captures a packet. That is a `DECLARED_SEEDS` entry with a one-line reason,
not an obstacle.

### 4.2 Concept flow, and the honest limit of the method

`graph.py`'s docstring is explicit that concepts are **not** modelled, and gives the reason: a
half-populated concept registry produces confident wrong answers. That warning was tested rather than
trusted. A first pass with nine hand-assigned introduction points reported **27 breaks**, headlined by
*"certificate: 80 prose uses in 12 lessons that Route C moves earlier."* That finding is garbage — it
came from hand-assigning "certificate" to Act VIII lesson 05, when Act III 05 and Act VI 04 both handle
certificates before it in Route A as well. The method had flagged Route A's own ordering as broken and
blamed Route C.

The fix removes the hand-assignment. **Define a concept's introduction as its first appearance in Route
A's prose**, since Route A is by construction the order in which everything is earned; then a
reordering is concept-safe if no use moves ahead of that point. Self-calibrating, needing only a term
list, and it cannot report a break that is really Route A's.

Measured over 20 load-bearing terms (`conntrack`, `ARP`, `MTU`, `default route`, `DNS`, `three-way
handshake`, `VXLAN`, `certificate authority`, `veth`, `cgroup`, `overlayfs`, `iptables`, `netfilter`,
`fragmentation`, `TLS`, `etcd`, `kube-proxy`, `CNI`, `seccomp`, `sysctl`), prose only, code stripped:

| Ordering | Concept-order breaks | Where |
|---|---|---|
| **C-naive** | **10** | `conntrack`, `DNS` → Act IV `03`; `MTU`, `fragmentation`, `TLS`, `DNS` → Act IV `04`; `default route` → Act IV `02`; `VXLAN` → Act IV `03`, `04`, `05` |
| **C-split** | **1** | `VXLAN` → Act IV `05` |

C-naive's ten breaks land in exactly four files — Act IV `02`, `03`, `04` — and they are precisely the
dependencies `PLATFORM-DEPTH-PLAN.md` §1's table predicted from first principles without measuring
them: *"`iptables`/NAT arrives before the table it depends on exists."* The prediction was right about
`conntrack` and about MTU→VXLAN; it was **wrong about ARP**, which has 0 prose uses in anything C-naive
moves earlier. Worth recording, because §1's table is the document that settled the split.

C-split's single remaining break is a navigation footer:

```bash
grep -n -i vxlan networking-fundamentals/act-4-one-pretends-many/05-who-does-this-for-you.md
```

```
182:← Prev: **[Overlay and VXLAN](04-overlay-vxlan.md)** · ↑ **[Act IV overview](README.md)** · Next: …
```

**So C-split has zero concept-order breaks in prose, and its one hit is the real cost of Phase 4.**
§6 is about that.

### 4.3 What this validation does not prove

Stated plainly, because a route that hides its own gaps is worse than no route:

- **Twenty terms is not the concept space.** It is the twenty this ordering stresses, chosen by looking
  at what C-naive moves. A term absent from the list is unchecked, not clean.
- **Prose matching is coarse.** A lesson that says "we will meet MTU in Act II" counts as a use. This
  biases toward *over*-reporting, which is the safe direction, and is why every finding above was read
  by hand rather than counted.
- **Nothing here checks whether the reader is motivated.** The River is machine-checkable; the Spirit is
  not, and `learner-simulator` exists because of that. §8 puts Route C in front of it.

## 5. The step table

Draft, with measured words. **A reordering must account for 100% of the course** — this is the property
Route B does not have and cannot be given, since Route B is a split. Route C's rows sum to **437,040**,
the whole measured course, which makes the table self-checking in a way Route B's never was.

| # | Read | Words | Drills | Why here |
|---|---|---|---|---|
| **0** | [`networking-fundamentals/README.md`](networking-fundamentals/README.md), [`your-own-machine.md`](networking-fundamentals/your-own-machine.md), [`code/`](networking-fundamentals/code) | 3,814 | — | The lab. Same setup Route A uses; nothing route-specific. |
| **1** | Orientation, **Act I** | 28,542 | 3 | Process, fd, socket, TCP states, `mount`/VFS, overlayfs. The floor under everything, and already first in Route A. |
| **2** | **Act IV 01, 01b** — namespaces, cgroups | 4,055 | — | Isolation before any networking: the inode of `/proc/self/ns/net`, and `memory.max`. This is the platform ordering's real headline — a container floor 100k words earlier than Route A delivers it. |
| **3** | **Act IV 05, 05b, 05c, 07** — `runc`/`containerd`, `nsenter`, user namespaces, BuildKit | 7,525 | 5 *(drills 5–9)* | The runtime peel and the build side. Needs a namespace and a cgroup, which step 2 gave; needs no IP address at all. |
| **4** | **Act II** | 26,662 | 4 | ARP, routing, MTU, DNS. Now — because step 5 is about to need `conntrack` and step 6 about to need MTU. |
| **5** | **Act III** | 21,227 | 4 | The handshake, TCP states, `conntrack`, HTTP, TLS. |
| **6** | **Act IV 02, 03, 04, 06** + Act IV's `README`, `test-yourself.md`, `diagnose.md`, `in-the-wild.md` | 19,760 | 4 *(drills 1–4)* | veth, bridge, `iptables`/NAT, VXLAN, CRI. The half of Act IV that is networking, read after the networking. Act IV's four support pages are read here, at the end of the act, because they span both halves. |
| **7** | **Act V** + [`the-whole-stack.md`](networking-fundamentals/the-whole-stack.md) | 41,015 | 4 | Kubernetes, then the capstone trace — same order Route A insists on, for the same reason. |
| **8** | **Act VI** | 48,489 | 13 | The control plane: static pods, the kubelet's unit, PKI, reconciliation, `kubeadm`. |
| **9** | **Act VII** | 54,882 | 12 | Workloads, scheduling, storage, config, Helm/Kustomize, CRDs, autoscaling. |
| **10** | **Act VIII** | 32,169 | 6 | Hashing through certificates. |
| **11** | **Act IX** | 31,258 | 6 | Identity, tokens, RBAC. |
| **12** | **Act X** | 87,902 | 13 | Securing the platform: capabilities, seccomp, policy, supply chain. |
| **13** | **Act XI** | 29,740 | 9 | Operating it: logs, metrics, cardinality, alerting, tracing. |
| | **total** | **437,040** | **83** | |

**What the reordering actually buys, in one number.** Measured on the same basis both ways — everything
a reader has read before opening Act IV lesson 05, `runc` from an OCI bundle:

| | Words read before Act IV 05 |
|---|---|
| Route A | 89,651 |
| Route C | **32,597** |

That is the platform ordering's entire claim, and it is **57,054 words of deferral, not a saving**:
nothing is cut, and steps 4–6 pay the networking back in full before Kubernetes.

**Steps 10–13 are Route A's order unchanged.** The proposal wanted security, supply chain, delivery and
observability grouped at the end; they already are. Route C diverges from Route A in exactly two places
— Act IV split around Acts II and III — and that is worth saying in the route page itself, because it
is the strongest available evidence that the original split was unnecessary.

## 6. The cost nobody guesses: 100 hardcoded navigation footers

Every lesson ends in a hand-written `← Prev … · ↑ Act overview · Next: … →` footer, and those footers
are Route A. Route B survives this because it reorders whole acts and mostly forward; a reader is never
sent backward. **Route C splits an act**, so a reader arriving at Act IV lesson 05 from step 3 reads:

```
← Prev: **[Overlay and VXLAN](04-overlay-vxlan.md)**
```

— a lesson at least 53,931 words further on (step 3's remainder, then all of Acts II and III, then two
more Act IV lessons before it). This is the one concept-order break §4.2 found,
and it is not a prose defect: it is the route colliding with the repo's navigation model.

The same collision appears once more, in the drills. `drills/act-4/05.sh` opens:

> "the container isn't as isolated as the last four drills assumed"

Under Route C, drills 5–9 are read at step 3 and drills 1–4 at step 6, so "the last four drills" is a
forward reference. Measured: this is the **only** cross-half back-reference in Act IV's nine drills.

Three ways to hold this, and the recommendation is the cheapest one:

| Option | Cost | Verdict |
|---|---|---|
| **(a) The route page says so.** One paragraph: footers are Route A's, here is the map, ignore them. Plus a one-line reword of `drills/act-4/05.sh`'s framing so it does not name a count. | ~120 words + 1 line | **Recommended.** It is what Route B already does implicitly, made explicit. Honest, zero risk to Route A. |
| **(b) Route-aware nav on the site.** [`site/scripts/sync-content.mjs`](site/scripts/sync-content.mjs) already projects the course; a route switcher could rewrite prev/next per route. | Real work in the site build; two navigation models to keep in step | **Defer.** Named in §11 as a follow-on, not folded into this phase. |
| **(c) A Route C callout in the split lessons.** An admonition at the head of Act IV `02` and `05`. | ~60 words × 2, inside Route A's own lesson files | **Decline.** It taxes every Route A reader to serve a Route C one, which is the direction of subsidy this repo has consistently refused. |

## 7. `routes.json`, and the generator both routes need

The deliverable that makes Route C maintainable, and retroactively fixes Route B.

**Schema** — one file, `reference/routes.json`, alongside `capabilities.json` and `lab-inventory.json`,
which are the two precedents for machine-read data in the reference wing:

```json
{
  "B": {
    "name": "The exam path",
    "page": "exam-prep/the-exam-path.md",
    "kind": "split",
    "steps": [
      {"n": 1, "label": "Orientation, **Act I**, **Act IV**",
       "include": ["00-orientation/**", "act-1-one-machine/**", "act-4-one-pretends-many/**"],
       "drills": ["act-1/*", "act-4/*"]}
    ],
    "optional": [
      {"label": "Act IV 05b, 05c", "include": ["act-4-one-pretends-many/05b-*.md",
                                               "act-4-one-pretends-many/05c-*.md"]}
    ]
  },
  "C": {"name": "The platform path", "page": "the-platform-path.md", "kind": "reorder", "steps": [...]}
}
```

`kind` is load-bearing. A `split` route's steps need not cover the course and its uncovered remainder is
the optional track; a `reorder` route's steps **must** cover it exactly, once each. That single field is
what lets one generator serve both and one invariant check both.

**`tools/gen-route-tables.py`** — same contract as `gen-tool-pages.py` and `gen-command-tables.py`:
regenerates the Words and Drills columns of a route page's step table from the globs, leaves the *Why
here* column alone (that is prose and stays hand-written), and refuses to run if a glob matches nothing.

**Three new harness invariants**, all `WARN`, all `REPO_WIDE`, in a new `invariants/routes.py`:

| id | Checks | Why it exists |
|---|---|---|
| `routes.step-globs-resolve` | every `include` glob matches ≥1 file | A renamed lesson silently shrinking a step is the `gen-tool-pages.py` failure mode already seen in the roster |
| `routes.reorder-covers-course` | a `kind: reorder` route's steps partition the course exactly — no file twice, none missing | §5's 437,040 identity, enforced instead of asserted |
| `routes.published-figures` | the numbers in the route page match the numbers the globs produce | Route B's 13,087-word drift, made impossible to repeat |

**`remeasure.py` changes.** `ROUTE_B`'s four hardcoded integers and the `OPTIONAL_WORDS` constant come
out and are derived from `routes.json`. The internal-arithmetic checks and the `unaccounted > 5_000`
warning become redundant for `split` routes and are replaced by the invariants above. The docstring's
"WHAT IS NOT AUTOMATED, AND WHY" section is rewritten to record §3's finding — **not deleted**, because
the reason it existed is worth keeping next to the evidence that retired it.

**Wave 1 also has to remeasure Route B**, since the generator's first run will move step 1 from 46,795
to 59,882 and the drill totals from 67 to 83. That is a `the-exam-path.md` prose edit (step 1's *Why
here* cell mentions neither Phase 1 nor Phase 3's Act IV lessons) plus the `JOURNEY-MAP.md` banner's
"45 of 67 drills" and "11%". Both are stale today, independent of Route C.

## 8. Obligations

Route C is **not a lesson**, so the fifteen-obligation table in `PLATFORM-DEPTH-PLAN.md` §4 does not
apply — no Predict-first marker, no milestone, no `LESSON-INDEX.md` line, no tool registration. What
does apply:

| # | Obligation | Enforced by |
|---|---|---|
| 1 | Every relative link in the route page resolves | `links.resolve` — **hard** |
| 2 | `JOURNEY-MAP.md`'s route banner names three routes, not two — its current heading is literally *"This map is Route A. There is a Route B."* | hand |
| 3 | `exam-prep/the-exam-path.md`'s "There are two ways through this course" opener becomes three, with one sentence on who Route C is for | hand |
| 4 | `site/scripts/sync-content.mjs` nav entry for the new page | site build |
| 5 | `PLATFORM-DEPTH-PLAN.md` §1's Route C sentence and the phase table's Status column | hand |
| 6 | `AUDIT.md` untouched — it declares itself unedited, and Phase 0 already established that stamping is the correct treatment | by rule |
| 7 | `python3 -m harness` at 0 failures, and the three new invariants proven able to go red — `selftest.py`'s mutation pass, not just its parity pass | `harness.selftest` |
| 8 | `python3 tools/remeasure.py --check` **exits 0**, which it does not today | `counts.published` |
| 9 | `learner-simulator` over the route page — the Spirit question here is specific and not rhetorical: *does a platform engineer reading step 4 understand why they are being sent into ARP after being promised containers?* | [`.claude/agents/`](.claude/agents/learner-simulator.md) |
| 10 | No `technical-accuracy-checker` run — **and this is the one place this phase is cheaper than its predecessors.** There are no commands to verify, because Route C teaches nothing. Every command it points at was verified when its lesson shipped. | n/a, stated |

Obligation 9 is the one that can actually fail. Route C's step 4 asks a reader who came for containers
to read 26,662 words of Ethernet and DNS in the middle of the container material. §5's *Why here* cells
are the whole defence, and if `learner-simulator` reports that the defence does not land, the fix is
prose, not reordering — C-split is already the ordering that measurement supports.

## 9. What Phase 4 declines

| Named | Decision |
|---|---|
| **A Docker-internals ordering** (the proposal's middle track) | **Decline as a step, keep as a step's contents.** Step 3 *is* the Docker-internals track — `runc` from an OCI bundle, `containerd`, `nsenter`, user namespaces, BuildKit. It is 7,525 words and it does not need a track of its own. |
| **A delivery track** (ArgoCD/Flux) | **Already declined**, at `JOURNEY-MAP.md` §7.6 and `PLATFORM-DEPTH-PLAN.md` §3. Route C changes nothing about it: Act VII 08b is where reconciliation lives, and it is on step 9. |
| **Route-aware navigation footers** | **Defer** — §6 option (b), §11. |
| **A fourth route** | **Decline pre-emptively.** Two views over one course are maintainable because §7 generates them. A third would be as well, but nobody has asked for one, and a route nobody reads is 2,000 words of surface that can go stale. |
| **Reordering Route A** | **Decline, permanently.** Nothing measured here argues Route A is wrong. C-split's clean run is evidence that Route A's dependencies are real and that a second ordering can respect them — not that the second is better. |

## 10. Sizing, and how it ships

**Two waves**, and the order is not negotiable: the tooling has to exist before the second route does,
or Phase 4 ships the defect §2 measured.

**Wave 1 — the step→file map as data.** `reference/routes.json` holding Route B only,
`tools/gen-route-tables.py`, `invariants/routes.py` with its three checks plus mutation selftests,
`remeasure.py` rewired, and Route B's own figures regenerated (step 1 → 59,882, drills → 83) with its
step-1 *Why here* cell updated to name the Act IV lessons Phases 1 and 3 added. Also: the second
attempt at reproducing `46,834`, and whichever way it goes, the docstring rewritten to record it.
**Ships green on `remeasure.py --check`, which is currently red.** ~400 lines of Python, ~200 words of
prose edits.

**Wave 2 — Route C.** `the-platform-path.md` at the repo root, next to `JOURNEY-MAP.md`, because Route C
is a peer ordering of the whole course rather than exam material and `exam-prep/` would misfile it.
~2,000 words: the two-paragraph framing, §5's step table, a *what this route does not fix* section
carrying §4.3's limits and §6's footer collision, and the `DECLARED_SEEDS` entry for `tcpdump`. Route C
added to `routes.json` as `kind: reorder`, which turns §5's 437,040 identity into a check. Plus
obligations 2–5, and the one-line reword of `drills/act-4/05.sh`.

**Total: ~2,200 words of prose and ~500 lines of tooling.** Against Phase 3's ≈13,600 words this is a
small phase, and it is the last one in `PLATFORM-DEPTH-PLAN.md`.

## 11. Open questions this plan does not decide

1. **Does `46,834` reproduce under some file set?** §3 could not reproduce it at either commit that
   matters and says so, but "I could not find the rule" and "there is no rule" are different claims and
   only the first is proven. Wave 1's first task, before the caveat is deleted.

2. **Where does the route page live?** §10 says repo root as `the-platform-path.md`. The rival is a new
   top-level `routes/` directory holding all three, which is tidier and moves `JOURNEY-MAP.md` — a file
   linked from everywhere. Recommendation is the root; the tidier option is not worth a rename of the
   most-linked file in the repo.

3. **§5's step 3 and step 6 rows contradict each other, on purpose, and one of them has to give.** The
   Drills column puts Act IV drills 5–9 at step 3; the Read column puts `diagnose.md` — the file those
   drills are *written in* — at step 6, because it spans both halves. Both cannot be true. The
   resolution is almost certainly to read `diagnose.md` twice, drills 5–9 at step 3 and 1–4 at step 6,
   which is how a reader would use it anyway and which the words column already accounts for by
   charging the page once. Say so explicitly in the page rather than leaving a reader to notice, and
   keep `test-yourself.md` whole at step 6 — a test covering half an act is not a test.

4. **Does the `kind: split` / `kind: reorder` distinction survive contact with Route A?** Route A is a
   `reorder` route with one step, and modelling it that way would let `routes.reorder-covers-course`
   check the `JOURNEY-MAP.md` figure too. Attractive, and it means the generator writes into the map,
   which is a bigger blast radius than this phase has earned. Left out of Wave 1 deliberately.

5. **Is `learner-simulator` the right check for a route page at all?** Its brief is a reader with only
   the anchor knowledge plus prior lessons, and a route page has no prior lessons. Obligation 9 asks it
   a question it was not built for. It may need a different prompt, or a different reviewer, and finding
   that out is part of Wave 2 rather than a reason to skip the check.
