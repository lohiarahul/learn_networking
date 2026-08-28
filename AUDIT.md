# Audit — first-principles CKA/CKS competence

> ## Remediation status — everything below has been actioned
>
> This document is the assessment as written. It is kept unedited, because an audit rewritten after the
> fact stops being evidence. What follows is what happened to it.
>
> | Finding | Status |
> |---|---|
> | **P0** — nothing verifies the learner's fix | **Closed.** All **64** drills now end in `tools/verify-drill.sh`, with a verifier per drill and a `Verify it` block per drill — exact parity. Expected causes are stored as SHA-256 of a normalised form, so the harness is not a second reveal. Three modes: the cluster (Acts V–VII, IX–X), the lab container via `docker exec` (Acts I–IV), and locally against an openssl PKI (Act VIII). |
> | **P0** — five headline failure classes have no drill | **Closed.** `NotReady` became three drills rather than one, because pairing them yields the `Ready=Unknown` / `Ready=False` branch for free. Image-pull, volume-mount and the three resource enforcers followed. Act VI went 8 → 11 drills, Act VII 7 → 10. |
> | **P0** — no route to a real multi-node cluster | **Closed with a caveat that is stated on the page.** [`act-6/09-two-machines-from-nothing.md`](networking-fundamentals/act-6-control-plane/09-two-machines-from-nothing.md) covers `init` → `join` → in-place upgrade → `controlPlaneEndpoint`. It is **the one page in the course its author has not run** — it needs two VMs and a hypervisor the authoring environment did not have — and it says so at the top, as does every domain-map row citing it. |
> | **P1** — the NetworkPolicy mechanism claim is false on the lab's own CNI | **Closed**, and it paid better than expected: measuring kindnet's `queue flags bypass to 101` produced a teaching point nothing else in the course has — a policy engine is a process, and `bypass` decides that it fails **open** when that process dies. |
> | **P1** — `nftables` appears in no lesson | **Closed** in `act-4/03`, as the store both grammars write to: a native `nft` rule is invisible to `iptables-save` and loaded all the same. |
> | **P1** — the scheduler's own loop is never taught | **Closed** in `act-7/04`, measured. Filter is readable (the `FailedScheduling` tally), score is *absent* on a two-node cluster with one tainted node and the lesson says so rather than faking it, and bind is a write — a hand-bound Pod runs with no `Scheduled` event and no `default-scheduler` in its history. |
> | **P1** — §E lab 7, the named-but-never-authored gaps | **Closed** by [`exam-prep/authoring-sprint.md`](exam-prep/authoring-sprint.md). Six of seven items applied to the live cluster; the Gateway HTTPS listener is marked expected-not-measured. |
> | **P1** — §E lab 8, a scan that must be acted on | **Closed** as Act X drill 12, built on the measured disagreement between kubesec and kube-linter and closed with a `ValidatingAdmissionPolicy` rather than a report. |
> | **P2** — the understanding-checks in Acts VIII–X are unusable | **Closed, and extended past the finding.** All **89** checks in the course are now at or under 80 words with 3–5 independently checkable clauses — Acts V–VII were levelled too, since capping only VIII–X would have left the loosest checks in the middle of the course. |
> | **P2** — the capstone walks one path | **Closed.** A second, north-south descent, measured: the only hop in the course that routes on the payload, the client IP erased twice, and `externalTrafficPolicy: Local` producing `000 in 6.004s` against `200 in 0.007s`. |
> | **P3** — `cgroups` skips `pids` | **Closed** in `act-4/01b`: three limits, three symptoms — killed, slowed, **refused** — and no `resources.pids` field to ask for the third with. |
>
> **Three defects were found by the remediation that the audit did not catch**, all of them because the
> drills were *run* rather than read: Act II drill 4's cleanup used `sed -i` on `/etc/hosts`, which cannot
> work in a container; Act III drill 4 could take the reader's whole Docker VM down and now says so; and
> six commands derived a gateway or uplink from `ip route show default`, which prints **nothing** on
> Docker Desktop. Two Acts I–IV drills also turn out not to reproduce their symptom there at all, which
> both drills now state, with the environment check.
>
> The audit's one-sentence finding was that this repository's self-knowledge exceeded its self-repair.
> Two of those three defects were things the repository had already written down somewhere else and not
> acted on — which is the same finding, one level down.
>
> ### Round two — §F and §G, the learning-efficiency findings
>
> These were never in the remediation queue above, and they were the audit's **lowest score** (5.0/10).
> Worse: the first round moved that one number the wrong way. The course was 357,717 words when this
> audit was written and is **376,651** now — the repairs added ~19k while every other dimension improved.
>
> | Finding | Status |
> |---|---|
> | **P1** — 357k words, ~50k outside both curricula; §G's fix is "publish two routes" | **Closed**, as [`exam-prep/the-exam-path.md`](exam-prep/the-exam-path.md), linked from every entry point. Route A stays the JOURNEY-MAP. Route B is nine steps in exam order with measured per-step counts and drill counts. |
> | **P1** — the ~50k of non-curriculum material sits on the critical path | **Closed.** Ten lessons now carry an optional-track banner naming what is examined, what depends on them, and when to read them: Act VIII 01–04, Act IX 05, Act II 01b/02b/03c, and Act III 04/05. Nothing was deleted. |
> | **P2** — 45 of 83 illustrations are referenced by nothing; **delete or annex** | **Declined, and gated instead.** See below. |
> | **P2** — "the seven bloated understanding-checks in Acts VIII–X, ~2,600 words, cut to ≤80 each" | **Closed on one block, and the count was wrong.** See below. |
> | **P3** — `PYROUTE2-PLAN.md` is a planning document at the repo root, citing two files that no longer exist | **Closed by labelling it, not by moving it.** See below. |
> | **P3** — "`AUDIT.md`, `AUDIT-2.md`, this file — ~110,000 words at the repo root, move to `audits/`" | **Declined; the premise is off by 11×.** See below. |
>
> **§G's arithmetic does not survive measurement, and the correction matters more than the fix.** §G
> claimed Route B was "roughly 240k against 358k" — a third off. Measured, it is **342,257 against
> 376,651**: a **9%** saving. §G's estimate and §F's own inventory of off-syllabus material (~31k) never
> reconciled with each other, and §F was the one telling the truth. So: **the length of this course is
> not a sequencing problem and cannot be fixed by routing**, because 92% of it is on one syllabus or the
> other. What Route B genuinely delivers is a *split* — you can sit CKA having read 58% of the course,
> and 45 of the 67 drills fall on that path — not a reduction. Any real reduction has to come out of
> on-syllabus prose (Act X's 84k, Act VII's 48k), which is a compression job nobody has started.
>
> **"Seven bloated checks, ~2,600 words" is one bloated check and 395 surplus words.** Measuring all 90
> milestone blocks in the course: the median is **74 words**, the maximum is **86**, and the distribution
> stops dead just short of a ninety-word ceiling nobody ever wrote down. Twenty-five blocks sit at 81–86,
> a few words over §F's stated 80 — that is authors aiming at a cap, not bloat. **One block is 475
> words**: `act-10/04-deciding-before-it-exists.md`, 18 bullets where every other milestone in the course
> is prose, and the only bullet-form block in Acts VII–X. A reader cannot self-assess against 18 claims;
> they skim, which is the same outcome as having no check at all. It is now 86 words of prose, keeping the
> five discriminators — the stages in order, the bare `kubectl run` that proves mutating admission has
> always rewritten your Pods, what makes a rule checkable, both webhook-down failure modes, and
> `runAsUser: 0` as a floor rather than a default. Nothing was lost: the lesson body still teaches all of
> it and `test-yourself.md` still tests it. A milestone block is a check, not a table of contents.
>
> `check_ladder` had always asserted such a block *exists*; nothing asserted it was still short, which is
> how one grew to five times the norm unnoticed. `check_milestone_length` now caps it at **100** — above
> every block that exists, with headroom for a legitimate edit, and it catches the 475. Round-tripped in
> both directions, including on `the-whole-stack.md`, which carries a milestone and is not a numbered
> lesson.
>
> **`PYROUTE2-PLAN.md` was worse than §F said, and the repair is not the one §F proposed.** §F noticed the
> two dead filenames. It missed the actual defect: the document's **recommendation shipped**. The
> eight-interface taxonomy it argues for is `reference/tools/`, one directory per kernel interface — so a
> reader met a live-sounding proposal ("add an `Interface` column") for work that was already done in a
> stronger form, citing files that no longer exist. Moving it to a different directory would not have
> fixed a word of that. It now opens with a status banner: what shipped, where each dead filename went,
> and that quoted `sync-content.mjs` line numbers have moved. The body is deliberately **not** rewritten
> — "78 rows sorted by what a tool is *for*" was true of `03-the-index.md` and is not true of
> `tools/README.md`, so swapping the filename alone would leave the surrounding claims reading as current
> and wrong. It stays at the root because it is the only record of *why* the reference wing is sorted by
> kernel interface, measured against 71 tools rather than asserted.
>
> **The 110,000 words of audits at the repo root are 9,960 words in one file.** `AUDIT-2.md` does not
> exist and never did in this checkout; "this file" and `AUDIT.md` are the same document. So §F's largest
> single line item by word count is off by **11×** and names two files that are not there. Moving one 10k
> file — and updating six inbound links, one of them from the exam path — buys nothing a reader would
> notice, so it is declined rather than done. Recorded because the pattern by now has a name. Of the four
> §F line items examined closely, **three overstate their own measurement** — the bloated checks by 6.6×,
> `PYROUTE2-PLAN.md`'s length by 1.6×, the root audits by 11× — and the fourth, the illustrations, gave no
> number and got the recommendation backwards. Every error runs in the same direction: the problem is
> smaller than the audit says, and in two cases the repository had already solved it.
>
> **The illustration recommendation was wrong, and finding that out took one diff.** §F called the 45
> unplaced SVGs "ongoing maintenance for zero learner contact" and said to delete or annex them. But
> `illustrations/MANIFEST.md` already inventories all 45 by name under `## Not placed`, with reasons,
> including an argument for why keyword-placing them would contradict the lessons — and that list
> measures **exactly right, zero drift in either direction**. They are also deterministic output of a
> generator the 38 *placed* images need anyway, and the only page serving them is a `noindex`
> contributor gallery. So deleting them would have removed a documented reserve to save nothing. The
> maintenance §F correctly smelled was the risk of that list going stale, which is now
> `check_pedagogy.py::check_illustration_placement` — asserted in both directions, and round-tripped by
> breaking it each way before it was trusted. The gallery reads the same list, so page and checker
> cannot disagree.
>
> Which is the audit's own finding a third time, and the sharpest instance of it: **the repository had
> already done this piece of self-knowledge properly, and the audit read the symptom as the defect.**
>
> ### Round three — the two §F items that needed a decision
>
> | §F line item | §F's number | Measured | Done |
> |---|---|---|---|
> | Act X lesson 08 — split in two | 10,017 words | 9,616 | ✅ **split**, at §F's own enumeration rather than §F's quoted sentence |
> | `reference/tools/` pages for six tools with no path | "17 of 72 pages are `roster only`" | **15**, and **two of the named six are taught by lessons** | ✅ **four compressed** |
>
> **The split went where §F's list said, not where §F's sentence said, and they are 145 lines apart.**
> §F named a seam — *"you can verify signatures on your laptop; nothing so far constrains what the
> cluster runs"* — and separately enumerated the contents in two groups: tags, digests, the image store,
> `AlwaysPullImages`, scanning, CVE arithmetic, SBOMs / then `cosign`, keyless, Fulcio, Rekor, CEL's
> limits, the Kyverno policy. The enumeration breaks at `cosign`; the quoted sentence sits three sections
> later, after signing and keyless. Both are real boundaries, so the tie-breakers are balance and whether
> the prose already turns there. §F's sentence gives **6,343 / 3,273**; §F's list gives **5,385 / 4,876**,
> two lessons both under Act X's median of ~6,000 where the other leaves one at the act's second-largest.
> And the prose turns at the list's seam explicitly, in a paragraph nobody had to write for this purpose:
> *"Which sets up the real problem. Everything so far … is something you computed about bytes you had.
> None of it survives being handed to somebody else, because none of it is a claim anyone is accountable
> for."* That paragraph now ends lesson 08 and names the next one. The split is
> [`08b-who-says-so.md`](networking-fundamentals/act-10-cluster-security/08b-who-says-so.md), following
> the course's existing `b`-suffix convention (`01b`, `02b`, `03b`, `03c`, `05b`, and Act VII's `08b`),
> which avoids renumbering lessons 09–11 and the 24 references to them across 14 files.
>
> Each half now carries its own `Predict first` (the signature question moved with the signatures), its
> own milestone, and its own rung of the ladder; the shared bench is built in 08, stated to outlive it,
> and torn down at the end of 08b. Twelve textual "lesson 08" back-references across Act X, `exam-prep/`
> and `Toolbelt.md` were re-pointed by which half they actually mean — `cosign`'s roster row and the
> authoring sprint's checksum-versus-signature argument to 08b, `trivy`'s and the GitOps drift argument
> to 08. The `LESSON-INDEX.md` entry split at the same seam, and while rewriting it a pre-existing gap
> showed up: the entry never mentioned the build-secret section at all. It does now.
>
> **§F's tool-page list included two tools the course teaches, which its own criterion excludes.** The
> criterion is "no CKA, CKS or on-call route". `scapy` is run by Act II lesson 01 and its page carries
> **six hand-written syntax breakdowns**; `ltrace` is run by Act I lesson 03 and carries one. Compressing
> either would have deleted hand-written teaching material to satisfy a rule that does not apply to it.
> So four were compressed, not six — `tc`, `ipvsadm`, `ipset`, `devlink` — and the `roster only` count is
> 15, not 17.
>
> The compression is a mechanism rather than four deletions, because four deletions would come back the
> next time someone ran the generator. **A roster row whose tool name is a link claims a page; a bare name
> is a row and nothing more**, and `gen-tool-pages.py` deletes any page it finds for one — so de-linking
> the row is the entire edit. That puts the decision in the file that already decides which tools exist,
> and it made the reason legible: what a page added over its row was mostly furniture. The blind-spot row
> is the one every netlink tool shares, the *"4 commands, grouped by what you are trying to find out"*
> preamble sat over four commands derivable from [the grammar](reference/01-the-grammar.md) once you know
> the interface is `netlink`, and the row already carried the sentence that matters. `devlink` is not
> installed in the lab image at all.
>
> What did *not* survive derivation was moved to where a reader actually arrives — holding a symptom, not
> a tool name. `tc -s qdisc` and `netem` are now rows under *"it's slow, but nothing is broken"*, beside
> the `nstat`, `mtr` and `ethtool -S` that were already handled that way; the IPVS connection table is
> under *"it works from the node but not from the Pod"*, next to the `iptables-save` line it is the
> alternative to. `tc monitor` and `devlink monitor` were already in `netlink`'s streaming block. Then the
> now-inert `caps` came out of `capabilities.json`, because generator input nothing renders is the kind
> that goes stale unnoticed.
>
> Two checks had to learn about the new state, and the second one is the interesting failure.
> `check_index_facets`'s `iface-roster` clause asserts every roster tool is placed on its interface page —
> it fired four warnings immediately, correctly. Teaching it that an unpaged row is placed by *name*
> rather than by link was easy; the first version was **worthless**, because it scanned the whole page and
> every one of these four is discussed in netlink's grammar prose anyway, so an incidental backtick
> satisfied it. Round-tripping caught that: the "never names it" clause would not fire when the sibling
> list dropped `tc`. Scoped to the sibling list — everything above the page's first rule — it fires.
> The third clause matters most and does fire: an interface page linking a page-less tool is a 404 the
> moment the orphan sweep runs, and it is now both a hard `check_links` failure and a named warning.
>
> **Net: §F is closed.** Of its six line items, three overstated their measurement, one got its
> recommendation backwards, one named two tools its own criterion protected, and one — the 475-word
> milestone block — was exactly the defect it claimed. Two were declined with the reasoning recorded
> above; four were done. Every threshold and every seam in this round came out of a measured
> distribution or a sentence the prose had already written.



## A. Executive assessment

| Dimension | Score | Basis |
|---|---|---|
| CKA readiness | **7.5 / 10** | Everything `kind` can teach is taught at or above exam depth. ~8% of the syllabus needs real machines and has no route at all; ~4% more is named-but-never-authored. Speed is untrained. |
| CKS readiness | **7.0 / 10** | Act X is the strongest security material in the repo and every control carries a threat model. Two curriculum bullets have zero coverage; four more teach the control without building the artifact. |
| First-principles depth | **9.0 / 10** | Best-in-class. Mechanism before tool, kernel file before command, and the abstraction is broken to prove who was holding it. Deductions: the scheduler's own loop, and one mechanism claim that is false on the lab's own CNI. |
| Troubleshooting depth | **8.5 / 10** | 57 genuine discover-the-cause drills with hidden reveals, target times and a walk-away rule. Five headline failure classes are absent, and nothing verifies the learner's fix. |
| Networking depth | **9.5 / 10** | The layered model is complete and the capstone walks it with the file that proves each layer. `nftables` appears in no lesson. |
| Learning efficiency | **5.0 / 10** | 357k words — four to five technical books — for two two-hour exams. ~50k words sit outside both curricula, Act X alone is 84k, and 45 of 83 illustrations are referenced by nothing. |

**The one-sentence finding: this repository's self-knowledge exceeds its self-repair.** The domain maps
in `exam-prep/` are more honest and more precise than most external audits — they name roughly twelve
gaps, mark them ❌ or 🟡, and state exactly what is missing. Most of those gaps are 15 to 90 minutes of
lab authoring each. They are still open. The highest-return work here is not new analysis; it is
closing the list the repository already wrote.

---

## B. Critical gaps

| Priority | Gap | Why it matters | Domain | Recommended fix |
|---|---|---|---|---|
| **P0** | **Nothing verifies the learner's own fix.** 57 drills, zero shell scripts in the repo, no `verify` step anywhere. Every drill is self-graded by opening a `<details>` reveal. | The repo automates verification of the *author's* prose — `check_pedagogy.py` gates link integrity and predict-first, `probe-lab.py` re-runs declared outputs against `netlab:latest`. None of it is pointed at the learner. Reading a reveal and believing you would have got there is the single most common way a self-study learner overestimates readiness. | CKA · CKS · real-world | Add a `**Verify it**` block to every drill: one command that exits 0 only if the fix is genuinely correct, written so it cannot pass on a cluster that was merely restored. `capabilities.json` + `probe-lab.py` already prove the harness can run commands in the lab and compare output. |
| **P0** | **Five headline failure classes have no drill.** Verified by grep across all ten `diagnose.md`: `NotReady` — zero occurrences. `ImagePullBackOff`/`ErrImagePull` — zero. `OOMKilled`/`Evicted`/`DiskPressure`/`MemoryPressure` — zero. `FailedMount`/`MountVolume` — zero. Container runtime stopped — never induced. | Troubleshooting is **30% of CKA**, the largest domain, and "Troubleshoot clusters and nodes" is its first bullet. A `NotReady` node is the canonical form of that task. Image-pull and volume-mount failures are the two most common real Pod faults in production. The absence is not compensated elsewhere: these appear in lesson prose but never as a symptom you must diagnose. | CKA · real-world | Five drills, specified in §E. |
| **P0** | **No route to a real multi-node cluster.** `kind` only; no VM path anywhere in the repo (`multipass`, `lima`, `vagrant`, `UTM` — zero hits). The CKA map says "needs two VMs" and stops. | Structurally unreachable: *Prepare underlying infrastructure*, *`kubeadm init`/`join`*, in-place *`kubeadm upgrade apply`*, and *build* an HA control plane. That is ~8% of CKA — more than the whole Storage domain — and the in-place upgrade is a reliably-appearing task. | CKA | This is solvable on the author's own hardware. `limactl` or `multipass` gives two Ubuntu VMs on Apple Silicon in minutes. One new act-VI appendix lesson covering `kubeadm init` → `join` → `upgrade plan`/`apply`/`node` → `controlPlaneEndpoint` closes four bullets at once. |
| **P1** | **The NetworkPolicy lesson's mechanism claim is false on the lab's own default cluster.** `act-5/07` is titled *"iptables with a YAML interface"* and its central claim is that a policy is "exactly the Act IV filter table with a controller keeping it in sync". Its *Where does the CNI write the rule?* section offers two options: Calico's `cali-*` iptables chains, or Cilium's eBPF. Measured on the live `netlab` cluster: **`iptables -L -n \| grep -ci cali` → 0**. Enforcement is `table inet kindnet-network-policies` with `queue flags bypass to 101`, into **`kindnetd` in userspace** (`/proc/net/netfilter/nfnetlink_queue` shows queue 101 bound). | The lesson already knows kindnet *enforces* — line 101 correctly dates it to kind v0.24 — but never updated *how*. So a learner following the course's own strongest instinct ("go read the rule the kernel is holding") finds nothing on their own cluster, with no guidance, and keeps a mental model that is wrong in exactly the direction the act exists to correct. | CKA · CKS · first-principles | Rewrite the section around **three** enforcement architectures, and make the third the lab's default: nftables hook → nfqueue → userspace verdict. It is a gift, not a chore — it is readable in the course's own idiom (`/proc/net/netfilter/nfnetlink_queue`), and it teaches a real production property nothing else in the course teaches: what happens to traffic when the policy agent dies. |
| **P1** | **`nftables` appears in no lesson.** `nft` has a full reference page, correctly argued, marked **`roster only`** — verified by grep: zero hits in `networking-fundamentals/`. | The lab's own `iptables` is `v1.8.11 (nf_tables)` — a shim. kube-proxy's nftables mode is GA and is where the project is going; kindnet already enforces policy in nftables; RHEL 10 has dropped the legacy module. A learner who can only read `iptables -S` cannot read the ruleset their own lab is actually running. The audit's own tool list names `iptables` / `nft` as a pair. | Real-world · CKA (rising) | One section at the end of `act-4/03`: same three rules, both grammars, `iptables -V` first, and `nft list ruleset` against the rules they just wrote — proving the two are one backend. Then a `--proxy-mode=nftables` cluster as an optional aside in `act-5/03`. |
| **P1** | **The API-server request pipeline lands four acts after the API server does.** `act-6/01` — *"The API server is a filesystem"*, the lesson that introduces it — contains zero occurrences of authentication, authorization, admission, mutating or validating. The full chain (authn → authz → decode → mutating → object validation → validating → etcd) is taught, excellently, in `act-10/04`. | Act X is CKS. A learner preparing for CKA alone never meets the pipeline, and therefore cannot reason about the difference between a 401, a 403, a strict-decode error and an admission refusal — which is the discriminator in a large share of "my apply was rejected" tasks. It is also the frame that makes RBAC and PSA make sense rather than be memorised. | CKA · first-principles | Move the seven-stage chain diagram and the `LimitRange` mutation demo into `act-6/01` as its closing section, and have `act-10/04` open by *recalling* it rather than deriving it. Cost: one relocation, no new content. |
| **P1** | **The cheap named gaps are still open.** No `StorageClass` is authored anywhere in the course. `PriorityClass` — zero hits. `Corefile` — zero hits. Gateway API has no HTTPS listener, no `certificateRefs`. `169.254.169.254` — zero hits. Release-binary checksum verification — absent. `Kubesec`/`KubeLinter` — zero hits. Helm's read-only half — absent. | Together ~12% of CKA and ~8% of CKS, against pass marks of 66% and 67%. Every one is named in the repo's own maps with the fix spelled out. Each is one manifest or one command. | CKA · CKS | One authoring sprint, §E lab 7. |
| **P1** | **357,717 words.** Act X alone is 84,007; its lesson 08 is 10,017 — the length of a book chapter. ~50k words sit outside both curricula: Act VIII lessons 01–04 (12,655), Act IX lesson 05 (5,580), Act II's VLANs/BGP/DHCP set (6,465), plus the unreferenced illustration corpus. | The stated goal is employment and competence, not academic completeness. At a realistic technical-reading-plus-experiment pace this is a 250–400 hour commitment for two exams that most candidates clear in 100–150. The risk is not that the material is bad — it is that a learner runs out of runway in Act VIII and never reaches Act X, which is the entire CKS syllabus. | Learning efficiency | §F. Sequence, don't delete: mark the non-curriculum material as an explicitly optional track and route the exam path around it. |
| **P2** | **The "You understand this when you can" checklists have collapsed under their own weight in Acts VIII–X.** Measured: Acts I–VI, n=50, **median 64 words, max 144**. Act X lesson 08: **489 words** in a single run-on sentence with roughly twenty-five clauses. Lesson 10: 414. Lesson 05: 353. Lesson 11: 344. | The device works because it is a checklist a learner can hold in their head and fail honestly against. At 489 words it is a summary of the lesson wearing a checklist's clothes, and it cannot be used for its purpose. The regression is monotonic with act number, which means it is drift, not design. | Pedagogy | Cap at the Acts I–VI standard — ≤80 words, three to five clauses, each independently checkable. The overflow is a *summary*, and if it is worth keeping it belongs under its own heading. |
| **P2** | **The scheduler's own loop is never taught.** `act-6/03` gives the four-loop handoff via `spec.nodeName` perfectly, and `act-7/04` gives every input a learner writes — requests, `nodeSelector`, affinity, taints, `topologySpreadConstraints`. Neither describes what the scheduler *does*: filter, then score, then bind. | It is the reason `0/2 nodes are available: 1 node(s) had untolerated taint {...}, 1 Insufficient cpu` reads as two separate filter rejections rather than one message, and the reason a Pod can be schedulable yet land somewhere surprising. Without it, scheduling is taught as constraints-you-write. | CKA · first-principles | One section in `act-7/04`: two nodes, one Pod, read the filter rejections out of the event, then make both nodes pass the filter and predict the score. `--v=10` on the scheduler shows the scoring if you want the receipt. |
| **P2** | **The capstone descent stops at Pod→Pod.** `the-whole-stack.md` is the best page in the repo — seven layers, each with the file that proves it. It never covers the last two rungs of its own model: ingress/gateway/load-balancer, and the external network. | The audit's target mental model runs `... → Service → DNS → ingress/gateway/LB → external network`. A learner who can narrate a Pod-to-Pod call still cannot narrate a browser-to-Pod call, which is the one they will be asked about. | Real-world · CKA | A second, shorter descent on the same page: external client → node port 80 → ingress-nginx Pod → `Service` → backend Pod, with the file at each hop. Mostly assembly of existing material. |
| **P2** | **45 of 83 illustrations are referenced by nothing** — the whole `01-fundamentals/` and `02-addressing/` sets: `osi-model.svg`, `ipv4-subnetting.svg`, `network-topologies.svg`, `analog-vs-digital-signals.svg`, `circuit-vs-packet-switching.svg`. | These are Network+/CCNA-shaped diagrams for a syllabus the course then, correctly, did not follow. They carry a Python build pipeline, a `_previews` directory and ongoing maintenance for zero learner contact. | Repo quality | Delete, or move to an `illustrations/unused/` annex excluded from the build. |
| **P3** | CSI is taught only as an inference from an `ExternalExpanding` event. The extension-interface bullet is satisfied for CNI (in depth) and CRI (via `crictl`, constantly), but the C in CSI is the thinnest of the three. | Named bullet; low exam weight; genuinely low real-world return for a platform engineer who will never write a driver. | CKA | Accept as-is, or one paragraph naming the sidecar set (`provisioner`, `attacher`, `resizer`) against the actual Pods in a `kind` cluster. |
| **P3** | `cgroups` covers `memory` and `cpu` well and skips `pids`, and relegates v1-vs-v2 to a parenthesis. | `pids.max` is the fork-bomb control and the one cgroup limit with a direct CKS System-Hardening reading. | CKS | Two lines in `act-4/01b`. |
| **P3** | `kubectl logs` is used constantly and never taught as a subject — `-c`, `--since`, `--previous`, `-l`, `--all-containers`. The repo's own map marks this 🟡. | One CKA bullet ("Manage and evaluate container output streams"), ~1%. | CKA | Fold into the image-pull or multi-container drill rather than authoring a lesson. |

---

## C. Coverage matrix

Verdicts are this audit's, against the two PDFs pulled during it. Where they differ from
`exam-prep/`, the difference is noted.

### CKA v1.35

**Cluster Architecture, Installation and Configuration — 25%**

| Objective | Coverage | Evidence | Missing |
|---|---|---|---|
| Manage RBAC | **Strong** | `act-9/06` builds the four-object model and computes the reverse question live; `act-10/07` adds the Node authorizer and `NodeRestriction`; `act-9` drills 2 and 6 are RBAC faults | Typing speed only |
| Prepare underlying infrastructure | **Missing** | — | Everything. No VM path exists |
| Create/manage clusters using kubeadm | **Partial** | `act-6/02`, `/04`, `/05` read a real kubeadm cluster from inside; `kubeadm certs`, `etcdctl snapshot` | `kubeadm init`, `kubeadm join` — never run |
| Manage the lifecycle of clusters | **Partial** | `act-6/06` derives version skew rather than quoting it, runs `upgrade plan`, and covers the failure the skew table cannot predict (an API *removed*, found via `apiserver_requested_deprecated_apis`) | `upgrade apply` / `upgrade node` — the lesson declines to run them, correctly, because a `kind` node image cannot be upgraded in place. This is the exam task |
| Implement and configure an HA control plane | **Partial** | `act-6/05` now carries the quorum reasoning — majority table, why an even size buys nothing, why lost quorum breaks linearizable reads rather than going read-only, `member remove` before `member add`, `IS LEARNER`, multi-member restore | The build: stacked vs external etcd, `controlPlaneEndpoint`, `join --control-plane` |
| Use Helm and Kustomize | **Closed** | `act-7/08` contrasts both and runs the Helm write path end to end; **Act X installs three public charts for real** (Cilium, Falco, External Secrets) with `--version`, `--set`, `--reuse-values`; and `act-7/08c` closes the read-only half on charts you did not write — `helm pull --untar`, `--include-crds`, `--dry-run=server`, subchart scoping, hooks, and `--skip-crds` **derived** from the measurement that `crds/` is not templated and is never upgraded. Drills 11–12 grade it | `-` |
| Understand extension interfaces (CNI, CSI, CRI) | **Strong** | CNI in depth (`act-5/05`); CRI via `crictl` throughout Act VI including with the apiserver down; CSI inferred | CSI mechanism is thin — see §B P3 |
| Understand CRDs, install and configure operators | **Strong** *(above depth)* | `act-7/09` — write a CRD, discover it adds no behaviour, then write the controller in shell | — |

**Workloads and Scheduling — 15%**

| Objective | Coverage | Evidence | Missing |
|---|---|---|---|
| Deployments, rolling update and rollback | **Strong** *(above depth)* | `act-7/01`, `/02` — `maxSurge`/`maxUnavailable` rounding, and why `rollout undo` is not an undo log | — |
| ConfigMaps and Secrets to configure applications | **Strong** *(above depth)* | `act-7/05` — env vs mounted file, the `..data` swap, `subPath` silently never reloading, the three plaintext locations | — |
| Configure workload autoscaling | **Strong** | `act-7/10` — metrics-server made to fail first, then HPA; the reason a one-liner Deployment can never scale; `act-7` drill 6 | — |
| Primitives for robust, self-healing deployments | **Strong** | `act-7/03` probes with the outage each causes when swapped; `act-7/07` the other kinds; `act-7` drill 1 is a readiness fault | — |
| Configure Pod admission and scheduling | **Partial** | Scheduling is above depth (`act-7/04`). Admission is half-covered: `ResourceQuota` arrives as a *fault* in `act-6` drill 8 — a `kubectl scale` reporting `scaled` while the ReplicaSet carries the `exceeded quota` refusal — and `LimitRange` is created once | **`PriorityClass` and preemption appear nowhere.** Neither quota is ever *authored* |

**Servicing and Networking — 20%**

| Objective | Coverage | Evidence | Missing |
|---|---|---|---|
| Connectivity between Pods | **Strong** *(above depth)* | `act-5/02` the Pod as a shared netns, watched down to the shared inode; `act-5/05` CNI | — |
| Define and enforce Network Policies | **Strong**, with a mechanism defect | `act-5/07` for the model — a denial times out rather than returning 403, and enforcement is *measured* not assumed; `act-5/07b` for the four authoring shapes on a four-client bench; `act-5` drill 4 | The *mechanism* section is wrong for the lab's own CNI — §B P1 |
| ClusterIP / NodePort / LoadBalancer and endpoints | **Strong** *(above depth)* | `act-5/03` walks `KUBE-SERVICES` → `KUBE-SVC` → `KUBE-SEP` → DNAT; `act-5/04b` headless, SRV, `sessionAffinity`, `ExternalName`, `externalTrafficPolicy`. **Verified live** — chain structure exactly as taught | — |
| Use the Gateway API to manage Ingress traffic | **Partial** | `act-5/06b` — `GatewayClass`/`Gateway`/`HTTPRoute`, the delegation model, weighted canary, reading `.status` | Its only listener is `protocol: HTTP`. **`HTTPS`, `tls.mode`, `certificateRefs` appear nowhere** — and the reported task shape is Ingress→Gateway *with TLS* |
| Ingress controllers and Ingress resources | **Strong** | `act-5/06` including a TLS Secret and SNI | — |
| Understand and use CoreDNS | **Partial** | `act-5/04` is thorough on the resolver-*client* side: `/etc/resolv.conf`, `ndots`, the search walk, why a trailing dot changes the query count | **The server side is absent.** `Corefile` — zero hits in the repo. The ConfigMap is never read or edited; `dnsConfig`/`hostAliases` appear nowhere. The exam surface for this bullet *is* the server config |

**Storage — 10%**

| Objective | Coverage | Evidence | Missing |
|---|---|---|---|
| Storage classes and dynamic volume provisioning | **Partial** | `act-7/06` derives `WaitForFirstConsumer` rather than quoting it, and shows `allowVolumeExpansion` accepted-then-ignored | **No `StorageClass` is authored anywhere in the course.** It consumes the one `kind` ships and patches a field |
| Volume types, access modes, reclaim policies | **Strong** | `act-7/06` — `emptyDir` vs PVC, `ReadWriteOnce` as *one node* not one Pod, `Delete` vs `Retain` | — |
| Manage PVs and PVCs | **Strong** | `act-7/06`; `act-7/07` `volumeClaimTemplates` and why scale-down keeps volumes; **`act-7` drill 7 is the exam task** — author a `hostPath` PV, then four claims and four different `Pending` causes, two of which emit the *same* event | Mount-time failures, as opposed to bind-time — §E lab 4 |

**Troubleshooting — 30%**

| Objective | Coverage | Evidence | Missing |
|---|---|---|---|
| Troubleshoot clusters and nodes | **Partial** | `act-6/07` node maintenance, `act-6/08` the five-question descent, `act-6` drills 6 and 7 | **No `NotReady` drill exists** — zero occurrences repo-wide in `diagnose.md`. This is the canonical form of the bullet |
| Troubleshoot cluster components | **Strong** *(above depth)* | `act-6/08` plus 8 drills. Drills 3 and 4 have identical symptoms and are separated by one command at layer 3 — a container to read, or no sandbox at all. Genuinely excellent | Runtime *itself* down is never induced |
| Monitor cluster and application resource usage | **Partial** | `act-7/10` installs metrics-server, makes it fail first, then `kubectl top` | **No resource-pressure drill.** `OOMKilled`, `Evicted`, `DiskPressure`, `MemoryPressure` — zero occurrences in any `diagnose.md` |
| Manage and evaluate container output streams | **Partial** | Used constantly — `logs --previous`, `crictl logs`, `logs -l` | Never taught as a subject |
| Troubleshoot services and networking | **Strong** *(above depth)* | `act-5/08` the five-question method, `act-5/09` a worked failure, 4 drills, and `the-whole-stack.md` as the synthesis that makes the method obvious rather than arbitrary | — |

### CKS v1.34

| Domain | Objective | Coverage | Evidence | Missing |
|---|---|---|---|---|
| **Cluster Setup 15%** | Network security policies for cluster-level access | **Strong** | `act-5/07` + `/07b` — cross-namespace peers, the AND-vs-OR hyphen, `ipBlock` + `except`, egress default-deny with the DNS outage it causes and the `kubernetes.io/metadata.name` fix | — |
| | CIS benchmark review | **Strong** | `act-10/07` runs `kube-bench`, maps findings back to lessons, and shows two are unfixable because the benchmark checks for controls Kubernetes deleted | — |
| | Ingress objects with TLS | **Strong** | `act-5/06` — TLS Secret and SNI | — |
| | Protect node metadata and endpoints | **Partial** | `act-10/07` covers the kubelet side thoroughly — port 10250, anonymous auth, `authorization.mode`, and why the same flag is right on the apiserver and fatal here | **`169.254.169.254` — zero hits.** No cloud-metadata egress policy. `readOnlyPort: 0` not exercised |
| | Verify platform binaries before deploying | **Partial** | `act-10/08` teaches digests and signature verification — applied to *images* | Release-binary checksum/signature verification. `sha256sum` appears once, in an Act VIII README |
| **Cluster Hardening 15%** | RBAC to minimize exposure | **Strong** | `act-9/06`, `act-10/07` | — |
| | Caution with service accounts | **Strong** | `act-10/07` is largely this bullet — the three files in the projected volume, the token's real lifetime, `automountServiceAccountToken`, and the 403→401 transition when the Pod is deleted | — |
| | Restrict access to the Kubernetes API | **Strong** | `act-10/07` — and its rule that a permissive auth flag is only as safe as the authorizer behind it | — |
| | Upgrade to avoid vulnerabilities | **Strong** | `act-6/06` | Shares CKA's in-place-upgrade gap |
| **System Hardening 10%** | Minimize host OS footprint | **Missing** | — | Everything. Repo admits it |
| | Least-privilege identity and access management | **Strong** | `act-9/06`, `act-10/07` | — |
| | Minimize external access to the network | **Strong** | `act-5/07b` egress policies; `act-10/07` | — |
| | Kernel hardening — AppArmor, seccomp | **Partial** | `act-10/02` is strong on seccomp (`RuntimeDefault`, `Localhost`, a profile that logs before it kills) and correct on AppArmor's field-vs-annotation trap and the pre-1.30 copy-paste hazard | An AppArmor profile the learner writes and **loads**. `SELinux` appears once, in passing |
| **Minimize Microservice Vulns 20%** | Pod security standards | **Strong** | `act-10/03` — and `act-10` drill 9 hides `warn` without `enforce` and a frozen `enforce-version` in a bench you build without reading | — |
| | Manage Kubernetes secrets | **Strong** *(above depth)* | `act-10/06` — generate the key, ordered `providers`, the three-part apiserver edit, `k8s:enc:aescbc:v1:` read out of etcd, re-encrypt, then *reverse* the provider order to prove the rule; `act-10/11` external stores; `act-10` drill 8 hides `identity` first | — |
| | Isolation techniques (multi-tenancy, sandboxed containers) | **Partial** | `act-10/02` names `RuntimeClass`, `runsc`, gVisor | gVisor never actually runs. No `RuntimeClass` is applied to a Pod that then demonstrably behaves differently |
| | Pod-to-Pod encryption (Cilium, Istio) | **Partial** | `act-10/09` builds a second cluster, installs Cilium by Helm, enables WireGuard, and captures the encrypted traffic | Istio's `PeerAuthentication` — the other tool the bullet names — appears nowhere |
| **Supply Chain 20%** | Minimize base image footprint | **Strong** | `act-10/08` | — |
| | Understand your supply chain (SBOM, CI/CD, artifact repos) | **Strong** | `act-10/08` — and it uses `bom`, which is the tool on the CKS allowed-docs list, not `trivy`'s SBOM | — |
| | Secure your supply chain (permitted registries, sign and validate) | **Strong**, with one named artifact absent | `act-10/08` — real `cosign` verification, a hand-built admission webhook, `AlwaysPullImages`, and a Kyverno `ImageValidatingPolicy` registering both a mutating and a validating webhook because you must resolve the tag to a digest *before* judging whether that digest is signed | **`ImagePolicyWebhook` is built nowhere** — and that is the exam's named artifact for permitted registries |
| | Static analysis of workloads and images (Kubesec, KubeLinter) | **Missing** | — | Both tools: zero hits repo-wide |
| **Monitoring/Runtime 20%** | Behavioral analytics to detect malicious activity | **Closed** | `act-10/10` installs Falco by Helm, watches a shipped rule fire, then opens `falco_rules.yaml` (25 rules against 87 macros and 49 lists — a ruleset is mostly exemptions) and authors one: `list`, `macro`, `rule`, `override.condition`, `customRules` → `/etc/falco/rules.d`. Drill 13 makes the learner write it under a clock and hides the mark in `falco.rules`'s post-load `disable` | `-` |
| | Detect threats across infra, apps, networks, users, workloads | **Partial** | `act-10/10` | Same as above |
| | Investigate and identify phases of attack | **Partial** | `act-10` drill 5 — "what happened inside the shell" — is exactly this and is good | One drill carrying a whole bullet |
| | Ensure immutability of containers at runtime | **Strong** | `act-10/01` — `readOnlyRootFilesystem`, and the section on a root filesystem you cannot write | — |
| | Kubernetes audit logs | **Strong** | `act-10/10` — the policy file, the three-part apiserver edit, and reading the log back | — |

**Totals.** CKA: **15 Strong, 11 Partial, 1 Missing** of 27. CKS: **16 Strong, 8 Partial, 2 Missing**
of 26. Counting a Partial as a half and weighting each domain by its published share:

| Exam | Weighted coverage | Repo's own figure |
|---|---|---|
| CKA v1.35 | **75.1%** | ~80% |
| CKS v1.34 | **77.2%** | ~75% |

**These confirm the repo's own arithmetic**, which is worth stating plainly: an independent scoring
against the PDFs lands within five points of the domain maps in both directions. The maps are
trustworthy for time allocation.

The disagreement is not the headline number, it is **where the shortfall sits** — and it sits badly:

| Domain | Weight | Coverage |
|---|---|---|
| Workloads and Scheduling | 15% | 90.0% |
| Servicing and Networking | 20% | 83.3% |
| Storage | 10% | 83.3% |
| **Troubleshooting** | **30%** | **70.0%** |
| **Cluster Architecture** | **25%** | **62.5%** |

The two weakest domains are the two heaviest. Together they are 55% of the exam and they carry
roughly three-quarters of the total shortfall. Cluster Architecture scores 62.5% because four of its
eight bullets need machines the lab does not have; Troubleshooting scores 70% — despite carrying the
best material in the repo — almost entirely because of the five absent drill classes in §B. Both are
addressable, and §E's Labs 1–5 are aimed squarely at them.

On the CKS side the pattern is milder and the same shape: Cluster Hardening is the one domain at
100%, and the three 20%-weight domains all sit at 70–75%.

---

## D. First-principles gaps

Where the learner is told what to type without learning why the system behaves that way. This list is
short, which is the finding — the repo's default mode is the opposite of this.

1. **The scheduler is a black box with a well-documented input surface.** Every constraint you can
   write is taught; the filter/score/bind loop that consumes them is not. Consequence: a learner can
   author `topologySpreadConstraints` and cannot read `0/2 nodes are available: ...` as a list of
   filter verdicts.
2. **NetworkPolicy enforcement, on the learner's own cluster.** See §B P1. The mechanism taught is
   not the mechanism running.
3. **The API server's request pipeline, for anyone who stops before Act X.** The lesson that
   introduces the API server treats it purely as a store; the pipeline that guards it arrives four
   acts later.
4. **CSI.** CNI is derived from first principles across a whole lesson; CRI is met by using `crictl`
   when nothing else works; CSI is met as a single event string. The learner can say what a
   `StorageClass` field does and not what the provisioner is or where it runs.
5. **Ingress data-path.** The Ingress lesson explains the object and the controller relationship
   well. It does not walk a packet from the external client to the backend Pod the way
   `the-whole-stack.md` walks a Pod-to-Pod call — so Ingress remains the one layer in the model
   understood declaratively rather than mechanically.
6. **`nftables` as the substrate.** The course is scrupulous that a tool which disagrees with the
   file is wrong. `iptables -S` on the lab's own node is a *rendering* of an nftables ruleset, and
   the course never says so in a lesson — only on a reference page marked `roster only`.

---

## E. Missing labs

### Lab 1 — The node that says it is not ready

- **Scenario.** A worker went `NotReady` twenty minutes ago. Pods on it are still serving.
- **Environment.** The two-node `netlab` cluster.
- **Failure to induce.** Three variants, run one at a time, symptom identical:
  `docker exec netlab-worker systemctl stop kubelet`; or delete the CNI config
  (`rm /etc/cni/net.d/*`) and restart the kubelet; or fill the node
  (`fallocate -l <most of the disk> /var/lib/hog`) to trigger `DiskPressure`.
- **What they must discover.** Which of the three it is — and, in each case, why the *existing* Pods
  keep serving. `NotReady` is a statement about the kubelet's ability to accept new work, not about
  the dataplane.
- **Tools.** `kubectl describe node` (the `Conditions` block, and its `lastHeartbeatTime`),
  `journalctl -u kubelet`, `crictl ps`, `df -h`, `ls /etc/cni/net.d`.
- **Success condition.** Node `Ready`, and the learner can state which condition flipped and which
  process writes it.
- **Model reinforced.** A Node object is a record a kubelet updates. When updates stop, the record
  goes stale and the world does not change — the same lesson as `act-6` drill 2's frozen
  `status.readyReplicas`, one layer down.

### Lab 2 — Four ways an image does not arrive

- **Scenario.** A Deployment rolls out and no Pod ever runs.
- **Environment.** `netlab`.
- **Failure to induce.** Four Pods in one namespace: a typo'd tag on a real repo; a real tag on a
  registry that does not resolve; a private image with no `imagePullSecrets`; and a correct image
  with `imagePullPolicy: Never` that is not present on the node.
- **What they must discover.** That `ImagePullBackOff` is a *state*, not a cause, and the cause is
  only in the event text — and that the fourth produces `ErrImageNeverPull`, a different state
  entirely, which is the tell.
- **Tools.** `kubectl describe pod`, `kubectl get events --sort-by=.lastTimestamp`,
  `crictl images`, `crictl pull`, `kubectl create secret docker-registry`, `kubectl logs` with
  `--previous` and `-c` — which closes the *container output streams* bullet in passing.
- **Success condition.** All four running; a one-line cause for each; and the learner can say which
  one `AlwaysPullImages` would have changed.
- **Model reinforced.** The kubelet's failure modes are ordered, and each stops at a different depth:
  no sandbox, sandbox with no container, container that will not start. `act-6` drill 4 already
  taught the discrimination — this applies it.

### Lab 3 — Killed, throttled, or evicted

- **Scenario.** "The service is slow, and sometimes it just disappears."
- **Environment.** `netlab`.
- **Failure to induce.** Three Pods: one with `limits.memory` below its working set; one with
  `limits.cpu: 100m` running a busy loop; one `Burstable` Pod on a node pushed into `MemoryPressure`
  so the kubelet evicts it.
- **What they must discover.** That the three symptoms are produced by three different enforcers —
  the kernel OOM killer, the CFS bandwidth controller, and the kubelet's eviction manager — and only
  the third is Kubernetes' decision. Then: why QoS class decided *which* Pod was evicted.
- **Tools.** `kubectl describe pod` (`Last State: Terminated, Reason: OOMKilled`),
  `kubectl get events` for the `Evicted` reason, `crictl stats`,
  `cat /sys/fs/cgroup/.../memory.events` and `cpu.stat` inside the node,
  `kubectl top pod`.
- **Success condition.** Each of the three named with its enforcer, and the eviction order predicted
  from QoS before it is observed.
- **Model reinforced.** Directly pays the debt `act-4/01b` opens — one limit kills you, the other
  slows you down, and neither writes a line in the application's own logs — and adds the third
  enforcer that only exists once a scheduler does.

### Lab 4 — The volume that will not mount

- **Scenario.** A Pod sits `ContainerCreating` forever.
- **Environment.** `netlab`.
- **Failure to induce.** Four Pods: a `secretKeyRef` naming a key that does not exist; a ConfigMap
  volume naming a missing ConfigMap; a `subPath` pointing into a file rather than a directory; and an
  RWO PVC already mounted by a Pod on the other node.
- **What they must discover.** That `Pending` and `ContainerCreating` are different failures at
  different layers — `act-7` drill 7 covers *binding*, this covers *mounting* — and that the fourth
  is the practical meaning of "`ReadWriteOnce` is one node, not one Pod", which `act-7/06` states
  and never makes fail.
- **Tools.** `kubectl describe pod` (`FailedMount`, `FailedAttachVolume`), `kubectl get events`,
  `kubectl get volumeattachment`, `mount | grep kubelet` inside the node.
- **Success condition.** All four running; the RWO one explained in terms of node, not Pod.
- **Model reinforced.** The kubelet's Pod startup is a sequence of steps that can each fail
  separately, and the *status* tells you which step, never why.

### Lab 5 — Two machines, from nothing

- **Scenario.** You have two bare Ubuntu VMs and a cluster to build.
- **Environment.** `limactl start --name=cp` and `--name=w1` (or `multipass launch`), 2 vCPU / 2 GB
  each. This is the one lab that cannot use `kind`, which is the point.
- **Task.** Disable swap, load `br_netfilter`, set the three sysctls, install containerd and
  configure `SystemdCgroup`, `kubeadm init --pod-network-cidr`, install a CNI, `kubeadm join` the
  worker, then `kubeadm upgrade plan` → `upgrade apply` on the control plane and `upgrade node` on
  the worker, with `kubectl drain`/`uncordon` around it. Then set `controlPlaneEndpoint` and read what
  `join --control-plane` would need.
- **What they must discover.** Every prerequisite is a prerequisite because something fails without
  it — leave swap on and read the kubelet's refusal; skip `br_netfilter` and watch Pod-to-Pod
  traffic vanish; get the cgroup driver wrong and watch the kubelet flap. Do not list the steps
  first; let each one be earned by a failure, which is the course's own method.
- **Tools.** `kubeadm`, `systemctl`, `journalctl`, `sysctl`, `crictl`, `kubectl drain`.
- **Success condition.** `kubectl get nodes` shows two `Ready` nodes at the new version, and a Pod on
  one can reach a Pod on the other.
- **Model reinforced.** Closes four CKA bullets. And it makes `kind`'s convenience legible — the
  learner finally sees what kind had already done for them in Act V.

### Lab 6 — Three ways to enforce one policy

- **Scenario.** The same `deny-all` NetworkPolicy, enforced three ways.
- **Environment.** `netlab` (kindnet), the `netcni` Calico cluster from `act-5/01`, and the Cilium
  cluster from `act-10/09` — all three already exist in the course.
- **Task.** Apply an identical policy on each and find the enforcement point.
- **What they must discover.** kindnet: `nft list table inet kindnet-network-policies` shows
  `queue flags bypass to 101`, `/proc/net/netfilter/nfnetlink_queue` shows queue 101 bound, and
  `pgrep kindnetd` names the userspace process holding it — so the verdict is made *outside the
  kernel*. Calico: `cali-*` chains in iptables. Cilium: no chains at all;
  `cilium endpoint list`. Then the question that makes it a lab rather than a tour: **kill the agent
  on each and re-test.** Which architecture fails open?
- **Tools.** `nft list ruleset`, `iptables-save`, `cat /proc/net/netfilter/nfnetlink_queue`,
  `cilium endpoint list`, `curl --max-time`.
- **Success condition.** Three enforcement points named with the file that proves each, and a stated
  prediction — verified — about what each does when its agent dies.
- **Model reinforced.** Repairs §B P1 and closes §B's `nftables` gap in the same hour. It also
  teaches something no CKA or CKS course teaches and every platform engineer eventually needs:
  a policy engine is a process, and processes die.

### Lab 7 — The authoring sprint

- **Scenario.** Not a failure — a timed authoring drill, because every item on it is a thing the
  course made you *read* and never made you *write*.
- **Environment.** `netlab`.
- **Task.** Seven artifacts, 45 minutes, no docs but `kubectl explain` and man pages: a
  `StorageClass` with its own `provisioner`, `reclaimPolicy` and `volumeBindingMode`, made default; a
  `PriorityClass` plus a preemption you can observe; the CoreDNS `Corefile` edited to add a
  `rewrite`, then reverted; a Gateway API `HTTPS` listener with `tls.mode` and `certificateRefs`; a
  `ResourceQuota` and a `LimitRange` written from scratch; an egress NetworkPolicy blocking
  `169.254.169.254/32`; and `kubectl` verified against its published `sha256`.
- **What they must discover.** How much of what they understood they cannot type.
- **Tools.** `kubectl explain`, `kubectl create ... --dry-run=client -o yaml`, `kubectl -n kube-system edit cm coredns`, `sha256sum`.
- **Success condition.** All seven applied and working, inside the clock.
- **Model reinforced.** None — and that is deliberate. This belongs in `exam-prep/`, not in an act.
  It closes ~12% of CKA and ~4% of CKS and teaches nothing, which is exactly the split the repo
  already draws between the acts and `exam-prep/`.

### Lab 8 — The scan you must act on

- **Scenario.** A manifest arrives from another team; gate it.
- **Environment.** Local, no cluster.
- **Task.** Run `kubesec scan` and `kube-linter lint` over three manifests — one clean, one with
  `privileged: true` and a `hostPath`, one that is merely missing `resources` — then wire the pass/fail
  into `act-10/05`'s existing policy engine so the gate is enforced at admission rather than advised
  at review.
- **What they must discover.** That the two tools disagree, and why: one scores, one lints. And that
  a scanner's finding is not a control until something refuses on it — which is `act-10/07`'s
  `kube-bench` lesson ("a scanner tells you what it checked, not what is true") pointed at the
  learner's own manifest.
- **Tools.** `kubesec`, `kube-linter`, `kubectl apply`.
- **Success condition.** The privileged manifest is refused by the cluster, not by a report.
- **Model reinforced.** Closes the last outright CKS gap, and does it in the act's own frame — at
  which moment does this refuse, and what did it know then.

---

## F. Material to remove or compress

> **This section is closed, and the table below is the original text, kept as written.** Every line item
> in it was measured before being acted on, and most did not survive the measurement — three overstate
> their own numbers, one has its recommendation backwards, and one names two tools its own criterion
> protects. What was actually done, declined, and found wrong is in
> **[round two](#round-two--f-and-g-the-learning-efficiency-findings)** and
> **[round three](#round-three--the-two-f-items-that-needed-a-decision)** at the top of this file. Read
> those before acting on anything here.

Being aggressive, as asked. Nothing here is bad work; all of it competes for the same hours.

| Material | Words | Verdict |
|---|---|---|
| **Act VIII lessons 01–04** — hashing, HMAC, ciphers, key exchange | 12,655 | **Optional track.** Named in neither curriculum at this depth. Lesson 05 (certificates) and 06 (TLS opened) earn their place — CKS's Ingress-TLS bullet and the whole of `act-6/04` rest on them. The four below them are a cryptography course, and a good one, sitting on the critical path of a Kubernetes course. Move behind an explicit "you need this if you want to understand *why*, not to pass" gate. |
| **Act IX lesson 05** — OAuth2/OIDC against a live IdP | 5,580 | **Optional.** In neither curriculum. Kubernetes OIDC auth is not examined and rarely configured by hand. The Keycloak dependency is also the repo's only live-external-service requirement. |
| **Act II 01b VLANs · 02b BGP · 03c DHCP** | 6,465 | **Optional CCNA annex.** Zero CKA/CKS surface. `03b` (MTU and fragmentation) is the opposite — keep it, it is paid off directly by VXLAN in Act IV. |
| **Act X lesson 08** — what you shipped | 10,017 | **Split in two.** One lesson cannot carry tags, digests, containerd's image store, `AlwaysPullImages`, scanning, CVE arithmetic, SBOMs, `cosign`, keyless signing, Fulcio, Rekor, CEL's limits, and a Kyverno `ImageValidatingPolicy`. Split at "you can verify signatures on your laptop; nothing so far constrains what the cluster runs" — the seam is already written into the prose. |
| **The seven bloated understanding-checks** in Acts VIII–X | ~2,600 | **Cut to ≤80 words each**, the Acts I–VI standard. The surplus is a summary; if it earns keeping, give it a heading. |
| **45 unreferenced SVGs** in `illustrations/01-fundamentals/` and `02-addressing/` | — | **Delete or annex.** Plus the build pipeline overhead they carry. |
| **`PYROUTE2-PLAN.md`** at repo root | ~7,000 | **Move to a non-learner-facing directory.** It is a planning document sitting beside `README.md`, and it still refers to `03-the-index.md` and `02-the-state-map.md`, which no longer exist. |
| **`reference/tools/` pages for tools with no path** — `devlink`, `ipvsadm`, `scapy`, `ltrace`, `ipset`, `tc` | — | **Compress to roster rows.** A page-per-tool is right for the ~55 tools a lesson actually uses; for the six with no CKA, CKS or on-call route, a row and a sentence is the honest weight. 17 of 72 pages are marked `roster only`. |
| **`AUDIT.md`, `AUDIT-2.md`, this file** | ~110,000 | **Not learner-facing, and currently at the repo root.** Move to `audits/`. |

**What not to cut, despite the temptation.** The 57 drills, `the-whole-stack.md`, the `exam-prep/`
domain maps, and the `reference/` interface taxonomy. The drills are the repo's single biggest
differentiator against every paid course. The domain maps are the reason a learner can allocate time
honestly. And the eight-kernel-interfaces idea is the one piece of the reference layer that scales
past the flags it lists.

---

## G. Recommended curriculum order

The narrative order is right *as a narrative* — it earns every idea. It is not the shortest path to a
certificate, and it should not pretend to be. Publish two routes.

**Route A — the course (unchanged).** Orientation → I → II → III → IV → V → capstone → VI → VII →
VIII → IX → X. This is what the JOURNEY-MAP describes and it should stay exactly as it is.

**Route B — the exam path.** For a learner with a booked date.

1. **Orientation, Act I, Act IV** — process, socket, namespace, cgroup, veth, bridge, iptables/nft.
   Non-negotiable: everything in Act V is unreadable without it. *(~45k words)*
2. **Act II 01, 02, 03, 03b, 04; Act III 01, 02, 02b, 03** — ARP, routing, ICMP/UDP, MTU, DNS, the
   handshake, TCP states, conntrack. Skip VLANs, BGP, DHCP, HTTP and TLS for now. *(~24k)*
3. **Act V, then `the-whole-stack.md`, then Act V's debugging pages and drills.** The capstone
   before the debugging method, as the repo already instructs.
4. **Act VI, plus new Lab 5 (two VMs).** Put the kubeadm build here, where static pods and the PKI
   have just been read from the inside.
5. **Act VII.** Add Labs 1–4 to its drill set — they are workload faults and belong beside drill 7.
6. **Act IX lesson 06 (RBAC) only**, pulled forward out of sequence. It is a CKA bullet in the
   heaviest domain and it does not need lessons 01–05 to land.
7. **`exam-prep/` + Lab 7 (the authoring sprint) + killer.sh.** → **sit CKA.**
8. **Act VIII 05 and 06** (certificates, TLS opened) — now, because CKS's Ingress-TLS and
   `cosign` material rest on them.
9. **Act IX 01–05, Act X, Labs 6 and 8.** → **sit CKS.**
10. **Act VIII 01–04, Act II's b-lessons, Act III 04–05.** After the exams, for the understanding.
    This is the material the repo is proudest of and it costs nothing to read it second.

Route B is roughly 240k words against 358k, and it front-loads every high-weight domain.

---

## H. Top 10 additions

1. **A `Verify it` block on all 57 drills.** The single highest-leverage change in the repo. The
   harness already runs commands against the lab image and compares output; point it at the learner.
2. **Labs 1–4** — `NotReady`, image pull, resource pressure, volume mount. Four drills, the largest
   CKA domain, currently absent.
3. **Lab 5 — the two-VM kubeadm act.** Closes four bullets and ~8% of CKA, and is the only gap in the
   repo that is genuinely blocked by the lab choice rather than by authoring time.
4. **Rewrite `act-5/07`'s enforcement section around three architectures** (nftables+nfqueue,
   iptables, eBPF), and make the lab's own default the one it explains first. Fixes a wrong mechanism
   claim and closes the `nftables` gap together — Lab 6.
5. **Move the seven-stage request pipeline from `act-10/04` into `act-6/01`.** A relocation, not new
   content, and it puts authn/authz/admission in front of every CKA learner.
6. **Lab 7 — the authoring sprint in `exam-prep/`.** Seven artifacts the course explains and never
   makes you write. ~12% of CKA.
7. **Cap the understanding-checks at 80 words.** Restores the device that Acts I–VI use so well.
8. **The scheduler's filter/score/bind loop**, one section in `act-7/04`, read out of a real
   `0/2 nodes are available` event.
9. **A second descent in `the-whole-stack.md`** — external client through Ingress to a backend Pod,
   with the file at each hop. Completes the repo's own layered model.
10. **Publish Route B**, and mark Act VIII 01–04, Act IX 05 and Act II's b-lessons as an explicitly
    optional track. This costs one page and buys back a hundred hours for a learner with a date
    booked.

Items 1, 5, 7, 9 and 10 are edits to existing material. Items 2, 3, 4, 6 and 8 are new lab authoring,
and 3 is the only one that needs anything the author does not already have running.

---

## I. Final verdict

> **If someone completed this repository thoroughly without using another course, would you trust
> them to…**

**1. Pass CKA? — Mostly.** They would answer the deep questions better than most candidates and lose
marks on tasks the course never made them perform. The blocker is not understanding, it is the
un-practiced surface: an in-place `kubeadm upgrade`, a `StorageClass` authored from scratch, the
CoreDNS `Corefile`, a Gateway with TLS, a `PriorityClass`. Against a 66% pass mark that is survivable
and uncomfortable. **Biggest remaining blocker: the ~8% of the syllabus that needs two real machines,
which the repo names and does not route around.**

**2. Pass CKS? — Mostly.** Act X is stronger on *why* each control exists than any commercial CKS
course I am aware of, and its habit of ending each lesson with a control that appears to work and does
not is exactly the right instinct for this exam. But CKS is scored on configuring six controls in
about seven minutes each, and the course says so about itself. **Biggest remaining blocker: three
competencies where the artifact is never built — an AppArmor profile that loads, gVisor actually
running, `ImagePolicyWebhook`.** Two items have since come off this list: static analysis, closed by
drill 12 (kubesec and kube-linter over three manifests, then a `ValidatingAdmissionPolicy` that
refuses on the finding), and the Falco rule, closed by lesson 10's authoring section and drill 13.

**3. Troubleshoot a broken Kubernetes cluster? — Yes.** This is the repo's strongest claim and it is
earned. Two independent diagnostic methods, one for a broken cluster and one for a broken workload;
57 drills that induce a real fault, hand over only a ticket, and hide the reveal; and drills built
specifically to be indistinguishable at the top layer and separable by one command three layers down.
The gap is coverage, not method: they will not have seen a `NotReady` node, an `ImagePullBackOff`, an
eviction or a `FailedMount`, and those are four of the ten things they will actually be paged about.
**Biggest remaining blocker: nothing checks their answer, so a learner who consistently reads the
reveal a minute early cannot tell.**

**4. Explain Kubernetes networking from first principles? — Yes, without qualification.** They will
have decoded `/proc/net/tcp` by hand, built container networking from `ip netns` and `veth` and
`iptables` before ever seeing a Pod, traced `KUBE-SERVICES` → `KUBE-SVC` → `KUBE-SEP` → DNAT on a
real node, measured whether their own CNI enforces policy rather than assuming it, and narrated one
packet down seven layers naming the file that proves each. Verified live during this audit: the chain
structure the lessons teach is exactly what the cluster is running. The one hole is that they will
believe NetworkPolicy is iptables underneath, because their own cluster's lesson told them so and
their own cluster is doing something else.

**5. Operate Kubernetes in a production platform team? — Mostly.** Everything that matters for the
first year is here: the reconciliation model, the failure modes of every control-plane component, the
PKI, etcd restore and what a restore does *not* revert, admission control, supply chain, audit,
runtime detection. What is missing is the operational surface that has no `kind` analogue — building
a cluster, upgrading one in place, running an HA control plane, and observability, which the roadmap
marks as unwritten and which is most of what a platform team's week actually consists of.
**Biggest remaining blocker: observability.** There is no Prometheus, no Grafana, no `ServiceMonitor`,
no log pipeline and no SLO anywhere in 358,000 words. `kubectl top` and `metrics-server` are the whole
of it. For a platform-engineering job that is a larger gap than anything on the CKA or CKS syllabus,
and it is the one recommendation in this audit that the exams do not motivate at all.

---

## What this audit checked, and how

So the findings can be re-tested rather than trusted.

- **Curricula pulled live**, not recalled: `CKA_Curriculum_v1.35.pdf` and `CKS_Curriculum v1.34.pdf`
  from `cncf/curriculum` via the GitHub API. The repo's stated versions and weightings match them
  bullet for bullet — including the "Servicing and Networking" naming and the 30/25/20/15/10 split.
- **Executed against the live cluster** (`kindest/node:v1.36.1`, server v1.36.1): kube-proxy mode
  (`iptables`, confirmed in both the ConfigMap and `server_linux.go:137` in the logs);
  `KUBE-SERVICES` chain structure; conntrack entries reversing a ClusterIP DNAT; the `iptables`
  backend (`v1.8.11 (nf_tables)`); `nft list table inet kindnet-network-policies`; the absence of
  `cali-*` chains; nfqueue 101 bound in `/proc/net/netfilter/nfnetlink_queue`; and `kindnetd` as the
  process holding it.
- **Repo-wide greps** for every mechanism on the audit's first-principles list, every failure mode on
  its troubleshooting list, and every deprecated API surface. The deprecated-API sweep came back
  clean: every removed API in the repo appears deliberately, as material about deprecation.
- **The repo's own gates**: `python3 tools/check_pedagogy.py` exits 0 across the whole course. An
  independent link check over all 455 Markdown files found **0 broken relative links**.
- **Counted rather than estimated**: 81 numbered lessons, 57 drills, 357,717 words, 83 illustrations
  of which 38 are referenced, 50 understanding-checks in Acts I–VI (median 64 words) against 489 in
  Act X lesson 08.

Two suspicions this audit raised and then **refuted**, recorded rather than dropped: that kube-proxy
on a v1.36 `kind` node would have moved to nftables mode (it has not), and that `act-5/07`'s claim
about kindnet not enforcing NetworkPolicy would be stale (it is not — the lesson dates the change to
kind v0.24 correctly and measures rather than asserts). The lesson's defect is narrower and different
from what was suspected: it knows kindnet enforces, and does not know how.
