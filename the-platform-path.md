# The platform path

There are three ways through this course now, and they are for different people.

**Route A — [the map](JOURNEY-MAP.md).** Orientation → I → II → III → IV → V → the capstone → VI →
VII → VIII → IX → X → XI, in the order the material was written and the order every idea is earned
before it is used: ARP before routing, routing before NAT, NAT before a Service, `conntrack` before
`iptables` depends on it. If you are here to understand networking from first principles, read it
in this order and ignore this page.

**Route B — [the exam path](exam-prep/the-exam-path.md).** The same material in CKA/CKS order, for
a learner with a booked date.

**Route C — this page.** The same material in *platform* order: the container floor before the
network, the network before Kubernetes. For a platform engineer who wants `runc` and `containerd`
before ARP, not after it.

Route C adds **no lesson and no new teaching**. Every word below already exists somewhere in
[`networking-fundamentals/`](networking-fundamentals/README.md); this page is a step table pointing
into it, generated from [`reference/routes.json`](reference/routes.json) the same way Route B's
table is. If a number here disagrees with a number in a lesson, the lesson is right and this page
is stale — run `tools/gen-route-tables.py`.

---

## Why a third route, and why it isn't a fork

A recommended path for "design, secure, debug and operate an enterprise container platform" was
once put against this repo, proposing three separate courses: Linux internals, Docker internals,
Kubernetes. That split was declined, for the reason [`PLATFORM-DEPTH-PLAN.md`](PLATFORM-DEPTH-PLAN.md)
§1 gives: this course is organised as a motivation chain, not a taxonomy, and abandoning that to
group by product boundary has a real cost — `iptables`/NAT would arrive before the `conntrack`
table it depends on, `seccomp` would be taught to a reader with nothing yet worth confining.

What the proposal got right is that a platform engineer arriving here wants the container floor
before the internet, and Route A gives them ARP first. Route C is that request, answered the way
Route B already answered "I want the exam order instead" — a step table, not a fork.

## The step table

**A reordering must account for 100% of the course.** Route C's steps are a `kind: reorder` route in
`routes.json`: every file under `networking-fundamentals/` is claimed by exactly one step, checked on
every harness run by `routes.reorder-covers-course` rather than asserted here.

| # | Read | Words | Drills | Why here |
|---|---|---|---|---|
| **0** | [`networking-fundamentals/README.md`](networking-fundamentals/README.md), [`your-own-machine.md`](networking-fundamentals/your-own-machine.md), [`code/`](networking-fundamentals/code) | 3,814 | — | The lab. Identical to Route A's — nothing route-specific. |
| **1** | Orientation, **Act I** | 28,542 | 3 | Process, fd, socket, TCP states, `mount`/VFS, overlayfs. The floor under everything, and already first in Route A. |
| **2** | **Act IV 01, 01b** — namespaces, cgroups | 4,055 | — | Isolation before any networking: the inode `/proc/self/ns/net` reads, and the cgroup leaf a container's memory ceiling lives in. This is the platform ordering's real headline — a container floor 84,773 words earlier than Route A delivers it. |
| **3** | **Act IV 05, 05b, 05c, 07** — `runc`/`containerd`, `nsenter`, user namespaces, BuildKit | 7,525 | 5 | The runtime peel and the build side. Needs a namespace and a cgroup, which step 2 gave; needs no IP address at all. |
| **4** | **Act II** | 26,662 | 4 | ARP, routing, MTU, DNS. Step 3 ended on a runtime and a filesystem with **no IP address at all** — a container that can build and run but cannot yet be reached. Everything from here on needs one. |
| **5** | **Act III** | 22,591 | 4 | The handshake, TCP states, `conntrack`, HTTP, TLS. |
| **6** | **Act IV 02, 03, 04, 06** + Act IV's `README`, `test-yourself.md`, `diagnose.md`, `in-the-wild.md` | 50,424 | 7 | veth, bridge, `iptables`/NAT, VXLAN, CRI — the half of Act IV that is networking, read after the networking it needs. Act IV's four support pages sit here because they span both halves of the act. |
| **7** | **Act V** + [`the-whole-stack.md`](networking-fundamentals/the-whole-stack.md) | 41,015 | 4 | Kubernetes, then the capstone trace — the same order Route A insists on, for the same reason. |
| **8** | **Act VI** | 48,489 | 13 | The control plane: static pods, the kubelet's unit, PKI, reconciliation, `kubeadm`. |
| **9** | **Act VII** | 54,882 | 12 | Workloads, scheduling, storage, config, Helm/Kustomize, CRDs, autoscaling. |
| **10** | **Act VIII** | 32,169 | 6 | Hashing through certificates. |
| **11** | **Act IX** | 31,258 | 6 | Identity, tokens, RBAC. |
| **12** | **Act X** | 87,902 | 13 | Securing the platform: capabilities, seccomp, policy, supply chain. |
| **13** | **Act XI** | 29,740 | 9 | Operating it: logs, metrics, cardinality, alerting, tracing. |
| | **→ total** | **469,068** course words | **86** | |

**Steps 10–13 are Route A's order unchanged.** The proposal wanted security, supply chain and
observability grouped at the end; they already are. Route C diverges from Route A in exactly two
places — Act IV split around Acts II and III — which is the strongest evidence available that the
original three-way split was unnecessary: one act, cut once, was the whole disagreement.

## What the reordering actually buys, in one number

Measured on the same basis both ways — every word a reader has read before opening Act IV lesson 05,
`runc` from an OCI bundle, lab setup excluded from both sides:

| | Words read before Act IV 05 |
|---|---|
| Route A | 88,587 |
| Route C | **32,597** |

That is the whole claim, and it is **55,990 words of deferral, not a saving**: nothing is cut, and
steps 4–6 pay the networking back in full before Kubernetes ever appears.

## What this route does not fix

Three things, named because a route that hides its own gaps is worse than no route.

**The ordering was checked against tool use and against twenty load-bearing concepts, not against
everything.** Run through the real course graph (`tools/harness/graph.py`), this exact split — Act
IV cut at `01b`/`05` rather than left whole — produces **zero** concept-order breaks in prose and
one tool-flow finding, and that finding is not a packet capture: `05b` runs `nsenter -t $PID -n
which tcpdump` to prove a namespace-entering process keeps its own filesystem, and never captures a
packet. The alternative — moving whole acts without splitting Act IV — produces ten concept breaks,
concentrated exactly where `PLATFORM-DEPTH-PLAN.md` §1 predicted from first principles:
`conntrack`, MTU→VXLAN. That table's prediction was wrong about one thing — ARP has zero prose uses
in anything the reordering moves earlier — which is worth knowing given that table is what settled
the original split. None of this proves the twenty checked concepts are the whole concept space,
only that they are the twenty this reordering stresses.

**The navigation footers are Route A's, and this route runs through the middle of one.** Every
lesson ends in a hand-written `← Prev · ↑ Act overview · Next →` line, and a reader following step 3
into Act IV lesson 05 reads:

```
← Prev: **[Overlay and VXLAN](04-overlay-vxlan.md)**
```

— a lesson at least 53,338 words further on: step 4, step 5, then two more Act IV lessons before it.
This is not a broken link — Route A's own order is intact — it is this route crossing a piece of
navigation that was never built to expect a reader arriving from anywhere else. Read the footers as
Route A's, not this page's, and keep going. The one drill with the same problem has been reworded
rather than left to confuse: `drills/act-4/05.sh`'s ticket used to open by naming "the last four
drills," a count that is only true in Route A's order.

**Nothing here checks whether the reordering is motivating, only whether it is safe.** The River —
nothing used before it is given — is machine-checked, above. The Spirit — does a platform engineer
reading step 4 understand why they are being sent into ARP after being promised containers — is not,
and is the harder question. `learner-simulator` was pointed at this page for exactly that reason.

---

*Numbers on this page are generated by [`tools/gen-route-tables.py`](tools/gen-route-tables.py) from
[`reference/routes.json`](reference/routes.json). If you edit this table by hand, the next run
overwrites it — edit the JSON, or the *Why here* prose, instead.*
