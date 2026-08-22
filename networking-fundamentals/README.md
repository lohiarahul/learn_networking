# Networking, from `write()` to a cluster

One question runs through every page here: **how does `write()` on one machine become `read()` on another?** You answer it not by reading but by *running* — every lesson is experiments you do yourself in a throwaway Linux container, reading the kernel's own files before any tool prettifies them. The thread that never breaks: **everything is a file.** You don't take that on faith; you catch yourself saying it around the tenth time the kernel hands you one.

**Who this is for:** anyone who can use a shell and wants to *see the mechanism* under the abstractions — sockets, packets, TCP, containers, Kubernetes — instead of memorising flags. No prior networking required; the course builds from a single process outward.

**What you'll be able to do** by the end: read a row of `/proc/net/tcp` by hand, trace a name → IP → route → MAC, narrate a TCP connection's whole life, build container networking from `ip netns`/`veth`/`iptables`, debug a broken Kubernetes network call by walking straight down the stack, and operate a cluster's control plane below `kubectl` — break it, restore it from a snapshot, and find out why it will not start — because you built every layer it rests on.

## Start here

1. **[`00-orientation/`](00-orientation/README.md)** — set up the one-line lab container, then two short pages: what a process is, and how processes communicate. **Do this first.**

## The acts — read in order

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

## The capstone

Once Act V's lessons are behind you — and **before** its debugging pages, which build directly on it — read **[`the-whole-stack.md`](the-whole-stack.md)**: a single packet followed from `write()` to `read()` through all seven layers you built, with the file that proves each one. It is the synthesis that makes the debugging method obvious rather than arbitrary.

Then **[`your-own-machine.md`](your-own-machine.md)** points the same reflexes at the laptop in front of you.

## Where the road ends (for now)

The built course is Acts I–IX. Act V is scoped to Kubernetes **networking** — Pods, CNI, Services (with headless, SRV and the traffic-policy shapes), CoreDNS, Ingress, Gateway API, NetworkPolicy and a debugging discipline. **[Act VI](act-6-control-plane/README.md)** is the control plane in eight lessons: the API server as a filesystem over etcd, static pods, the reconciliation loop, the cluster's own PKI, etcd backup and restore, upgrades and version skew, node maintenance, and the diagnostic walk for a control plane that will not answer. Every lesson in it has been run against a real cluster and corrected against what actually happened.

**[Act VII](act-7-workloads/README.md)** is workloads in ten lessons — the Deployment family, scheduling, probes, configuration, storage, Helm, CRDs and autoscaling — every one of them run against a real cluster. **[Act VIII](act-8-trust/README.md)** finally opens Act III's padlock: hashes, HMAC, AEAD, key exchange, certificates, and a TLS 1.3 handshake narrated against a CA you build yourself. It needs no cluster at all, only `openssl`.

**[Act IX](act-9-identity/README.md)** takes the name Act VIII proves and asks who decides what it may do: authentication against authorization, tokens and sessions, a ServiceAccount JWT taken apart and then verified by hand against the cluster's published key, OAuth2 derived hop by hop against a real identity provider, and the two ways a permission can be written down. Six lessons, every command run against a real cluster.

Still **mapped but not written**: observability, Kubernetes security (Act X), and AWS networking and security — see the roadmap banner in [`../JOURNEY-MAP.md`](../JOURNEY-MAP.md).

If you are here for **CKA or CKS**, start at [`../exam-prep/`](../exam-prep/README.md): it maps every competency to the lesson that covers it and is honest about the ones nothing covers yet.
