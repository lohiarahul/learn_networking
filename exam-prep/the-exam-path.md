# The exam path

There are two ways through this course, and they are for different people.

**Route A — the course.** Orientation → I → II → III → IV → V → the capstone → VI → VII → VIII → IX
→ X. It is described in [`JOURNEY-MAP.md`](../JOURNEY-MAP.md) and it is the order the material was
written in. Every idea is earned before it is used: ARP before routing, routing before NAT, NAT
before a Service, certificates before a Pod-to-Pod tunnel. If you are here to understand networking,
read it in this order and ignore this page.

**Route B — the exam path.** This page. For a learner with a booked date.

Route B is not a shortcut through the material. It is a *split* of it, and the honest headline is
this:

> **You can sit CKA having read 58% of the course.** The CKA path is 225,333 words. CKS is the other
> 127,232. Only 43,325 words — 10.5% — sit outside both curricula, and those are gated as an
> [optional track](#the-optional-track) rather than removed.

That is a smaller saving than it sounds like and a bigger one than it looks like. Smaller, because
sequencing cannot compress a syllabus — Act X is 87k words and *all* of it is CKS. Bigger, because
the thing that actually defeats self-study candidates is not total length, it is reaching Act VIII
with a date three weeks out and no idea which of the remaining 150k words are examined. Route B
answers that question.

> **A correction to the audit that produced this page.** [`AUDIT.md`](../AUDIT.md) §G estimated Route
> B at "roughly 240k against 358k". Measured, it is **352,565 against 411,490** — the saving is 9%,
> not 33%. §G's estimate and §F's own inventory of off-syllabus material (~31k) never reconciled, and
> §F was the one telling the truth. The consequence matters: **the length of this course is not a
> sequencing problem and cannot be fixed by routing.** If it needs to be shorter, that has to come
> out of on-syllabus prose — Act X's 87k, Act VII's 55k — which is a compression job, not an
> ordering one.

---

## The path

**Counts remeasured 28 August 2026**, after Act VII gained
[lesson 08c](../networking-fundamentals/act-7-workloads/08c-when-the-chart-is-not-yours.md) and two
drills, and Act X lesson 10 gained its Falco rule-authoring section and drill 13. The whole-course
figure carries forward the basis the original measurement used.

Words are the whole act unless a lesson list narrows it — including its `README`, `diagnose.md`,
`test-yourself.md` and `in-the-wild.md`, because those are where the drills live and the drills are
the part that transfers to an exam.

| # | Read | Words | Drills | Why here |
|---|---|---|---|---|
| **1** | Orientation, **Act I**, **Act IV** | 46,795 | 7 | Process, fd, socket, namespace, cgroup, veth, bridge, iptables/nft. **Non-negotiable.** Everything in Act V is unreadable without it — a Service is a NAT rule and a Pod is a namespace, and if those two words are abstractions to you then Act V is memorisation. |
| **2** | **Act II** 01, 02, 03, 03b, 04 · **Act III** 01, 02, 02b, 03 | 34,198 | 8 | ARP, routing, ICMP/UDP, MTU, DNS, the handshake, TCP states, conntrack. Skip VLANs, BGP and DHCP (no exam surface) and HTTP/TLS *for now* — TLS is picked up properly at step 8. Keep 03b: MTU is paid off directly by VXLAN in Act IV and by every overlay-CNI question. |
| **3** | **Act V**, then [`the-whole-stack.md`](../networking-fundamentals/the-whole-stack.md), then Act V's debugging pages and drills | 41,002 | 4 | The capstone *before* the debugging method, as the course already instructs. You cannot follow a debugging discipline over a path you have not once traced end to end. |
| **4** | **Act VI** — including [09, the two-VM build](../networking-fundamentals/act-6-control-plane/09-two-machines-from-nothing.md) | 42,726 | 11 | `kubeadm init` → `join` → in-place upgrade belongs *here*, where static pods and the cluster PKI have just been read from the inside. Doing it earlier makes it a recipe. **Lesson 09 is the one page in the course its author has not run** — see the banner on it. |
| **5** | **Act VII** | 54,867 | 12 | Workloads, scheduling, storage, config, Helm/Kustomize, CRDs, autoscaling. The largest single block on the path, and the largest single block of CKA — lessons 08, 08b and 08c are its Helm/Kustomize section, and 08c plus drills 11–12 are the operational half: `crds/`, hooks, and a release Secret that is also a lock. |
| **6** | **Act IX lesson 06 only** — [RBAC and ABAC](../networking-fundamentals/act-9-identity/06-rbac-and-abac.md) — plus Act IX drills **2, 4 and 6** | 5,745 | 3 | Pulled forward, out of sequence. RBAC is a CKA bullet in the heaviest domain and it does not need lessons 01–05 to land. Those three drills are RBAC-only; the other three need the token material and wait for step 9. |
| **7** | [`exam-prep/`](README.md) — the domain maps, [`kubectl-speed.md`](kubectl-speed.md), [`exam-day.md`](exam-day.md), [`authoring-sprint.md`](authoring-sprint.md) — then killer.sh | 16,636 *(not counted below)* | 7 items | Speed and recall, which the course deliberately refuses to train. The authoring sprint is the one that finds gaps: every item is something the course made you read and never made you write. |
| | **→ sit CKA** | **225,333** course words | **45** | |
| **8** | **Act VIII** 05, 06 — certificates, TLS opened | 19,505 | 6 | Now, not earlier. CKS's Ingress-TLS bullet and the whole `cosign` half of Act X rest on these two, and Act III's TLS cliffhanger has been open since step 2. |
| **9** | **Act IX** 01–04 · **Act X** · Act IX's remaining drills | 107,727 | 16 | The entire CKS syllabus plus the identity material that CKS assumes. Act X is 87k of this and there is no way round it. |
| | **→ sit CKS** | **352,565** course words | **67** | |

**45 of the 67 drills are on the CKA path**, and every one of them ends in a verifier that exits
non-zero if your fix is wrong — see [`drills/README.md`](../drills/README.md). That is the part of
this repository that most resembles the exam, because the exam also does not care whether you can
explain the fix.

---

## The optional track

43,325 words, 10.5% of the course, examined by neither curriculum. **None of it is cut**, and the
reason is in the last row of each entry: this is the material that answers *why*, and the course is
better for having it.

| Material | Words | Why it exists | Read it when |
|---|---|---|---|
| **Act VIII 01–04** — hashing, HMAC, ciphers, key exchange | 12,323 | A genuine cryptography short course. Lessons 05 and 06 are on the exam path and stand without it — but they *assert* things these four prove. | After CKA, or before step 8 if a certificate has ever felt like a magic file. |
| **Act IX 05** — OAuth2/OIDC against a live IdP | 5,485 | The only lesson in the repo needing a live external service (Keycloak). Kubernetes OIDC auth is examined nowhere and configured by hand rarely. | Whenever you next meet an identity provider at work, which is more likely than meeting one in an exam. |
| **Act II 01b, 02b, 03c** — VLANs, BGP, DHCP | 6,465 | A CCNA annex. Zero CKA/CKS surface. `03b` (MTU) is the opposite and stays on the path. | If you also want the networking certification, or the day a VLAN tag ruins your afternoon. |
| **Act III 04, 05** — HTTP, TLS | 6,528 | **Deferred, not optional — and the two differ.** Act VIII 05–06 at step 8 cover TLS properly, so `05` is genuinely superseded. `04` (HTTP) is not superseded by anything: Act V teaches Ingress and Gateway API without ever opening a request, so if header-and-method routing is not already yours, read `04` before step 3. | `05`: step 8 replaces it. `04`: before step 3, or never. |
| **Act XI** — observability, 4 of 8 lessons so far (log-file mechanics, the Prometheus exposition format, a hand-rolled scrape loop, cardinality) | 12,524 | Closes no CKA/CKS gap by design — `kubectl top`, `kubectl logs` and "install a monitoring stack" appear on neither syllabus below the level this act teaches them. What it adds is the mechanism the exam only ever asks you to *use*: where a log line actually lives on a node, what a counter survives that a gauge does not, and why one label can double the size of a Prometheus instance's memory before anyone notices. | Whenever `kubectl logs --previous` or a flat, quiet dashboard panel has ever left you guessing instead of measuring — no exam deadline required. |

---

## What this route does not fix

Three things, stated because a path that hides its own gaps is worse than no path.

**It does not make the course short.** 353k words is four technical books. At a realistic
read-plus-experiment pace that is 200+ hours for two two-hour exams that many candidates clear in
100–150. Route B tells you *which* hours; it does not give you fewer of them.

**It does not train speed until step 7.** Everything before that is deliberately slow — predict
first, derive the command, read the kernel file. That is the right way to learn and the wrong way to
sit a timed exam, and the switch happens all at once at step 7. Do not discover this in the last
week: run [`authoring-sprint.md`](authoring-sprint.md) once at the *end of step 5*, badly, to see
what a clock does to you.

**Two rows carry caveats you should know about.** Act VI lesson 09 has never been run by its author
— it needs two VMs and a hypervisor the authoring environment did not have — and item 4 of the
authoring sprint (a Gateway API HTTPS listener) was never applied to a live cluster because the CRDs
were unreachable. Both say so where they stand. Everything else on this path was measured on a real
kernel or a real cluster.
