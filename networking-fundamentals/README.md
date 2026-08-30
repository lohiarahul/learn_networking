# Networking, from `write()` to a cluster

One question runs through every page here: **how does `write()` on one machine become `read()` on another?** You answer it not by reading but by *running* — every lesson is experiments you do yourself in a throwaway Linux container, reading the kernel's own files before any tool prettifies them. The thread that never breaks: **everything is a file.** You don't take that on faith; you catch yourself saying it around the tenth time the kernel hands you one.

**Who this is for:** anyone who can use a shell and wants to *see the mechanism* under the abstractions — sockets, packets, TCP, containers, Kubernetes — instead of memorising flags. No prior networking required; the course builds from a single process outward.

**What you'll be able to do** by the end: read a row of `/proc/net/tcp` by hand, trace a name → IP → route → MAC, narrate a TCP connection's whole life, build container networking from `ip netns`/`veth`/`iptables`, debug a broken Kubernetes network call by walking straight down the stack, and operate a cluster's control plane below `kubectl` — break it, restore it from a snapshot, and find out why it will not start — because you built every layer it rests on.

## Start here

1. **[`00-orientation/`](00-orientation/README.md)** — set up the one-line lab container, then two short pages: what a process is, and how processes communicate. **Do this first.**

## The acts — read in order

> **Unless you have an exam date booked.** This order earns every idea before it uses one, which is the
> right way to understand the material and the wrong way to prepare for a timed test. If CKA or CKS is
> the reason you are here, read **[the exam path](../exam-prep/the-exam-path.md)** first: the same acts
> re-sequenced, with the 11% that neither curriculum examines marked as optional rather than removed.

Each act is a chain of lessons that ends by pointing at the next, so you never have to guess where to go. After the lessons come three transfer layers: **`test-yourself`** (recall, answers hidden), **`diagnose`** (symptom-first on-call drills — the real job), and **`in-the-wild`** (re-run the act's ideas on your own Mac).

| Act | Question it answers | You leave able to… |
|---|---|---|
| **[I — One machine](act-1-one-machine/README.md)** | If everything's a file, what kind of file is a network connection? | Read `/proc/net/tcp` unaided; explain a socket as a file. |
| **[II — Two machines](act-2-two-machines/README.md)** | Loopback only reaches itself — how do two separate machines find each other? | Trace name → IP → route → MAC; subnet on paper. |
| **[III — The internet](act-3-the-internet/README.md)** | IP drops, reorders, and forges — how do we get a stream that's reliable? | Name every TCP state; read an HTTPS exchange end to end. |
| **[IV — One pretends to be many](act-4-one-pretends-many/README.md)** | One honest IP per machine — what happens when one machine hosts a crowd? | Build container networking by hand from kernel primitives. |
| **[V — Kubernetes](act-5-kubernetes/README.md)** | One host is a ceiling — who wires up a fleet, declaratively? | Debug a cluster network call by reading the files in order. |
| **[VI — The control plane](act-6-control-plane/README.md)** | Act V never said who was arranging any of it. Scheduled by whom, watched from where? | Operate a cluster below `kubectl` — break it, restore it, and find out why it will not start. |
| **[VII — Describing the work](act-7-workloads/README.md)** | Two acts of Kubernetes and you have never described a workload. What must you tell it, and what does it work out? | Say what a workload needs and what the cluster infers; read a controller's status as evidence. |
| **[VIII — Trust on an untrusted wire](act-8-trust/README.md)** | Act III handed you a padlock and told you not to open it. What is actually inside it? | Say which of cryptography's four promises a mechanism keeps — and which one everybody assumes it keeps. |
| **[IX — Identity and access](act-9-identity/README.md)** | Act VIII proves who is at the other end and stops, holding a name. Who decides what a name may *do*? | Ask of any authorization system: when this says yes, what moment is it telling me about? |
| **[X — Securing the cluster](act-10-cluster-security/README.md)** | Nine acts built a thing that works. Nobody ever asked whether it was safe — and safety was never once the default. | Ask of any control: at what moment does it refuse, what did it know then, and what would be different if it stopped working? |
| **[XI — Knowing before someone tells you](act-11-observability/README.md)** *(4 of 8 lessons, in progress)* | Act X taught the cluster to remember every authorised change. What did it write down about everything nobody changed on purpose? | Find the exact file a Pod's logs live in and why deleting the Pod erases them; read the exposition format under `kubectl top`; hand-compute a percentile from raw histogram buckets; and price one label's cardinality in resident memory before it is ever stored. |

## The capstone

Once Act V's lessons are behind you — and **before** its debugging pages, which build directly on it — read **[`the-whole-stack.md`](the-whole-stack.md)**: a single packet followed from `write()` to `read()` through all seven layers you built, with the file that proves each one. It is the synthesis that makes the debugging method obvious rather than arbitrary.

Then **[`your-own-machine.md`](your-own-machine.md)** points the same reflexes at the laptop in front of you.

## Where the road ends (for now)

The built course is Acts I–X, plus the first half of Act XI. Act V is scoped to Kubernetes **networking** — Pods, CNI, Services (with headless, SRV and the traffic-policy shapes), CoreDNS, Ingress, Gateway API, NetworkPolicy and a debugging discipline. **[Act VI](act-6-control-plane/README.md)** is the control plane in eight lessons: the API server as a filesystem over etcd, static pods, the reconciliation loop, the cluster's own PKI, etcd backup and restore, upgrades and version skew, node maintenance, and the diagnostic walk for a control plane that will not answer. Every lesson in it has been run against a real cluster and corrected against what actually happened.

**[Act VII](act-7-workloads/README.md)** is workloads in ten lessons — the Deployment family, scheduling, probes, configuration, storage, Helm, CRDs and autoscaling — every one of them run against a real cluster. **[Act VIII](act-8-trust/README.md)** finally opens Act III's padlock: hashes, HMAC, AEAD, key exchange, certificates, and a TLS 1.3 handshake narrated against a CA you build yourself. It needs no cluster at all, only `openssl`.

**[Act IX](act-9-identity/README.md)** takes the name Act VIII proves and asks who decides what it may do: authentication against authorization, tokens and sessions, a ServiceAccount JWT taken apart and then verified by hand against the cluster's published key, OAuth2 derived hop by hop against a real identity provider, and the two ways a permission can be written down. Six lessons, every command run against a real cluster.

**[Act X](act-10-cluster-security/README.md)** is the one that asks whether any of it was safe, and finds that safety was never the default. Twelve lessons on a single timeline — a rule can fire when an image is **built**, when an object is **admitted**, when a container is **created**, when a syscall is **made**, or never, in which case something merely writes it down — and the trade never turns around: the earlier you decide, the less you know. Capabilities and seccomp, Pod Security Admission, admission webhooks and the two policy engines, encryption at rest, the cluster's own open doors, supply-chain signing and verification, Pod-to-Pod encryption, audit logging and runtime detection, and external secret stores. Every lesson run against a real cluster; every lesson ends with a control that appears to be working and is not.

**[Act XI](act-11-observability/README.md)** has started: four of eight planned lessons, on where a log line actually lives, the exposition format under every `kubectl top` and Grafana panel, and cardinality as arithmetic you can do before installing anything. Alerting, dashboards and tracing are not written yet.

Still **mapped but not fully written**: the rest of observability (alerting, dashboards, tracing), and AWS networking and security — see the roadmap banner in [`../JOURNEY-MAP.md`](../JOURNEY-MAP.md).

If you are here for **CKA or CKS**, start at [`../exam-prep/`](../exam-prep/README.md): it maps every competency to the lesson that covers it and is honest about the ones nothing covers yet.
