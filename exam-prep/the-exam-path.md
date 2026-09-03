# The exam path

There are three ways through this course, and they are for different people.

**Route A — the course.** Orientation → I → II → III → IV → V → the capstone → VI → VII → VIII → IX
→ X. It is described in [`JOURNEY-MAP.md`](../JOURNEY-MAP.md) and it is the order the material was
written in. Every idea is earned before it is used: ARP before routing, routing before NAT, NAT
before a Service, certificates before a Pod-to-Pod tunnel. If you are here to understand networking,
read it in this order and ignore this page.

**Route B — the exam path.** This page. For a learner with a booked date.

**Route C — [the platform path](../the-platform-path.md).** The same material in container-floor
order — for a platform engineer who wants `runc` and `containerd` before ARP, not a certificate.

Route B is not a shortcut through the material. It is a *split* of it, and the honest headline is
this:

> **You can sit CKA having read 56% of the course.** The CKA path is 244,581 words. CKS is the other
> 127,372. Only 61,273 words — 13.7% — sit outside both curricula, and those are gated as an
> [optional track](#the-optional-track) rather than removed.

That is a smaller saving than it sounds like and a bigger one than it looks like. Smaller, because
sequencing cannot compress a syllabus — Act X is 87k words and *all* of it is CKS. Bigger, because
the thing that actually defeats self-study candidates is not total length, it is reaching Act VIII
with a date three weeks out and no idea which of the remaining 150k words are examined. Route B
answers that question.

> **A correction to the audit that produced this page.** [`AUDIT.md`](../AUDIT.md) §G estimated Route
> B at "roughly 240k against 358k". Measured, it is **371,953 against 458,417** — the saving is 15%,
> not 33%. §G's estimate and §F's own inventory of off-syllabus material (~31k) never reconciled, and
> §F was the one telling the truth. The consequence matters: **the length of this course is not a
> sequencing problem and cannot be fixed by routing.** If it needs to be shorter, that has to come
> out of on-syllabus prose — Act X's 87k, Act VII's 55k — which is a compression job, not an
> ordering one.

---

## The path

**Counts remeasured 31 August 2026**, from [`reference/routes.json`](../reference/routes.json) via
`tools/gen-route-tables.py` rather than by hand — this table used to drift every time an act gained
a lesson (Act VII's 08c, then Act IV's runtime/build and `nsenter`/user-namespace lessons, then Act
VI's `systemd` lesson, all landed here late or not at all) and now cannot, since the Words and Drills
columns are generated from the same globs the harness checks on every run.

Words are the whole act unless a lesson list narrows it — including its `README`, `diagnose.md`,
`test-yourself.md` and `in-the-wild.md`, because those are where the drills live and the drills are
the part that transfers to an exam.

| # | Read | Words | Drills | Why here |
|---|---|---|---|---|
| **1** | Orientation, **Act I**, **Act IV** | 79,895 | 15 | Process, fd, socket, namespace, cgroup, veth, bridge, iptables/nft. **Non-negotiable.** Everything in Act V is unreadable without it — a Service is a NAT rule and a Pod is a namespace, and if those two words are abstractions to you then Act V is memorisation. Act IV now also carries the runtime peel and build side (`runc`, `containerd`, CRI, BuildKit — Phase 1), `nsenter`/user namespaces (Phase 3), and the netfilter depth — a stateful firewall, NAT's ceiling and hairpin, and transparent proxying (Phase 5) — which is most of why this step's word count moved. Of the Phase 5 three, `03b` earns its place on the exam path (it is what makes step 3's `KUBE-` chain walk readable); `03c`/`03d` are listed in the optional track below. |
| **2** | **Act II** 01, 02, 03, 03b, 04 · **Act III** 01, 02, 02b, 03 | 34,568 | 8 | ARP, routing, ICMP/UDP, MTU, DNS, the handshake, TCP states, conntrack. Skip VLANs, BGP and DHCP (no exam surface) and HTTP/TLS *for now* — TLS is picked up properly at step 8. Keep 03b: MTU is paid off directly by VXLAN in Act IV and by every overlay-CNI question. |
| **3** | **Act V**, then [`the-whole-stack.md`](../networking-fundamentals/the-whole-stack.md), then Act V's debugging pages and drills | 41,015 | 4 | The capstone *before* the debugging method, as the course already instructs. You cannot follow a debugging discipline over a path you have not once traced end to end. |
| **4** | **Act VI** — including [02b](../networking-fundamentals/act-6-control-plane/02b-what-starts-the-kubelet.md) and [09, the two-VM build](../networking-fundamentals/act-6-control-plane/09-two-machines-from-nothing.md) | 48,489 | 13 | `kubeadm init` → `join` → in-place upgrade belongs *here*, where static pods and the cluster PKI have just been read from the inside. Doing it earlier makes it a recipe. **[02b](../networking-fundamentals/act-6-control-plane/02b-what-starts-the-kubelet.md) is on the path, not in the optional track**, and it is the exception worth naming: it is the only new Phase-3 lesson with real exam surface, because CKA's *troubleshoot clusters and nodes* bullet was marked covered on the strength of `journalctl -u kubelet` and `systemctl` commands the course had never explained — and `journalctl -n`, which [`kubectl-speed.md`](kubectl-speed.md) drills as reflex, appeared in no lesson at all. **Lesson 09 is the one page in the course its author has not run** — see the banner on it. |
| **5** | **Act VII** | 54,882 | 12 | Workloads, scheduling, storage, config, Helm/Kustomize, CRDs, autoscaling. The largest single block on the path, and the largest single block of CKA — lessons 08, 08b and 08c are its Helm/Kustomize section, and 08c plus drills 11–12 are the operational half: `crds/`, hooks, and a release Secret that is also a lock. |
| **6** | **Act IX lesson 06 only** — [RBAC and ABAC](../networking-fundamentals/act-9-identity/06-rbac-and-abac.md) — plus Act IX drills **2, 4 and 6** | 5,745 | 3 | Pulled forward, out of sequence. RBAC is a CKA bullet in the heaviest domain and it does not need lessons 01–05 to land. Those three drills are RBAC-only; the other three need the token material and wait for step 9. |
| **7** | [`exam-prep/`](README.md) — the domain maps, [`kubectl-speed.md`](kubectl-speed.md), [`exam-day.md`](exam-day.md), [`authoring-sprint.md`](authoring-sprint.md) — then killer.sh | 16,636 *(not counted below)* | 7 items | Speed and recall, which the course deliberately refuses to train. The authoring sprint is the one that finds gaps: every item is something the course made you read and never made you write. |
| | **→ sit CKA** | **264,594** course words | **55** | |
| **8** | **Act VIII** 05, 06 — certificates, TLS opened | 19,518 | 6 | Now, not earlier. CKS's Ingress-TLS bullet and the whole `cosign` half of Act X rest on these two, and Act III's TLS cliffhanger has been open since step 2. |
| **9** | **Act IX** 01–04 · **Act X** · Act IX's remaining drills | 107,854 | 16 | The entire CKS syllabus plus the identity material that CKS assumes. Act X is 87k of this and there is no way round it. |
| | **→ sit CKS** | **391,966** course words | **77** | |

**52 of the 83 drills are on the CKA path**, and every one of them ends in a verifier that exits
non-zero if your fix is wrong — see [`drills/README.md`](../drills/README.md). That is the part of
this repository that most resembles the exam, because the exam also does not care whether you can
explain the fix.

---

## The optional track

61,273 words, 13.7% of the course, examined by neither curriculum. **None of it is cut**, and the
reason is in the last row of each entry: this is the material that answers *why*, and the course is
better for having it.

**The two Act IV rows below are not part of that 61,273.** `05b`/`05c` and `03b`/`03c`/`03d` sit
inside step 1's whole-Act-IV glob, so their words are already in the CKA path's count — listing them
again here would have counted 5,037 and 9,691 words twice, which is exactly the kind of error this
table used to make silently. The rows stay because the reading guidance ("skip if short on time") is
still true; the word counts don't move to avoid double-counting them.

| Material | Words | Why it exists | Read it when |
|---|---|---|---|
| **Act VIII 01–04** — hashing, HMAC, ciphers, key exchange | 12,651 | A genuine cryptography short course. Lessons 05 and 06 are on the exam path and stand without it — but they *assert* things these four prove. | After CKA, or before step 8 if a certificate has ever felt like a magic file. |
| **Act IX 05** — OAuth2/OIDC against a live IdP | 5,561 | The only lesson in the repo needing a live external service (Keycloak). Kubernetes OIDC auth is examined nowhere and configured by hand rarely. | Whenever you next meet an identity provider at work, which is more likely than meeting one in an exam. |
| **Act II 01b, 02b, 03c** — VLANs, BGP, DHCP | 6,663 | A CCNA annex. Zero CKA/CKS surface. `03b` (MTU) is the opposite and stays on the path. | If you also want the networking certification, or the day a VLAN tag ruins your afternoon. |
| **Act III 04, 05** — HTTP, TLS | 6,658 | **Deferred, not optional — and the two differ.** Act VIII 05–06 at step 8 cover TLS properly, so `05` is genuinely superseded. `04` (HTTP) is not superseded by anything: Act V teaches Ingress and Gateway API without ever opening a request, so if header-and-method routing is not already yours, read `04` before step 3. | `05`: step 8 replaces it. `04`: before step 3, or never. |
| **Act XI** — observability: log-file mechanics, the Prometheus exposition format, a hand-rolled scrape loop, cardinality, alerting, dashboards, tracing | 29,740 | Closes no CKA/CKS gap by design — `kubectl top`, `kubectl logs` and "install a monitoring stack" appear on neither syllabus below the level this act teaches them, and Prometheus/Alertmanager/Grafana/Loki/tracing appear in neither curriculum at all. What it adds is the mechanism the exam only ever asks you to *use*: where a log line actually lives on a node, what a counter survives that a gauge does not, and why one label can double the size of a Prometheus instance's memory before anyone notices. | Whenever `kubectl logs --previous` or a flat, quiet dashboard panel has ever left you guessing instead of measuring — no exam deadline required. Read it after the certificate: this is the most job-relevant act in the repo and the least examinable one. |
| **Act IV 03b, 03c, 03d** — the stateful firewall; NAT's ceiling, hairpin, `mangle`/`raw`; the transparent proxy | 9,691 *(already in step 1 — see above)* | **Split verdict, and the split is the point.** `03b` is not really optional: chain traversal (`-j` into a user chain, `RETURN`, terminal vs non-terminal) is what makes step 3's `KUBE-SERVICES → KUBE-SVC → KUBE-SEP` walk readable rather than memorised, and `DROP` vs `REJECT` is the distinction under every *"the Service resolves and nothing answers"* symptom in Act V's debugging. `03c` and `03d` genuinely have no exam surface — neither curriculum mentions SNAT port exhaustion, `TPROXY` or `SO_ORIGINAL_DST` — and both are high job value: hairpin NAT is kubelet's `hairpin-mode` and a Pod that cannot reach its own Service, and `03d` is the entire mechanism a service mesh runs on. | `03b` before step 3, with the rest of Act IV. `03c`/`03d` when a NAT gateway, a latency tail, or a sidecar next lands on you — or after the certificate. Inside a week of the exam, read `03b` and defer the other two |
| **Act IV 05b, 05c** — `nsenter` and PID-addressed namespace entry; user namespaces and `/proc/self/uid_map` | 5,037 *(already in step 1 — see above)* | **Zero exam surface, highest practical value per word in the act.** Neither `nsenter` nor `hostUsers`/`uid_map` appears in either domain map. They are here because the course already leaned on both: `nsenter` was named 45 times and run never, and Act X's seccomp lesson cites the user namespace as *"Act IV's mechanism"* — a citation these two lessons make true. `05b` is also the floor under `kubectl debug`, which **is** examinable. | Before Act X, in reading order — `05c` is what makes Act X lesson 02's `unshare -U` a mechanism you own rather than a command you paste. Skip both only if you are inside a week of the exam |

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
