# Networking, from `write()` to a cluster

One question runs through every page here: **how does `write()` on one machine become `read()` on another?** You answer it not by reading but by *running* — every lesson is experiments you do yourself in a throwaway Linux container, reading the kernel's own files before any tool prettifies them. The thread that never breaks: **everything is a file.** You don't take that on faith; you catch yourself saying it around the tenth time the kernel hands you one.

**Who this is for:** anyone who can use a shell and wants to *see the mechanism* under the abstractions — sockets, packets, TCP, containers, Kubernetes — instead of memorising flags. No prior networking required; the course builds from a single process outward.

**What you'll be able to do** by the end of Act V: read a row of `/proc/net/tcp` by hand, trace a name → IP → route → MAC, narrate a TCP connection's whole life, build container networking from `ip netns`/`veth`/`iptables`, and debug a broken Kubernetes network call by walking straight down the stack — because you built every layer it rests on.

## Start here

1. **[`00-orientation/`](00-orientation/README.md)** — set up the one-line lab container, then two short pages: what a process is, and how processes communicate. **Do this first.**

## The five acts — read in order

Each act is a chain of lessons that ends by pointing at the next, so you never have to guess where to go. After the lessons come three transfer layers: **`test-yourself`** (recall, answers hidden), **`diagnose`** (symptom-first on-call drills — the real job), and **`in-the-wild`** (re-run the act's ideas on your own Mac).

| Act | Question it answers | You leave able to… |
|---|---|---|
| **[I — One machine](act-1-one-machine/README.md)** | If everything's a file, what kind of file is a network connection? | Read `/proc/net/tcp` unaided; explain a socket as a file. |
| **[II — Two machines](act-2-two-machines/README.md)** | Loopback only reaches itself — how do two separate machines find each other? | Trace name → IP → route → MAC; subnet on paper. |
| **[III — The internet](act-3-the-internet/README.md)** | IP drops, reorders, and forges — how do we get a stream that's reliable? | Name every TCP state; read an HTTPS exchange end to end. |
| **[IV — One pretends to be many](act-4-one-pretends-many/README.md)** | One honest IP per machine — what happens when one machine hosts a crowd? | Build container networking by hand from kernel primitives. |
| **[V — Kubernetes](act-5-kubernetes/README.md)** | One host is a ceiling — who wires up a fleet, declaratively? | Debug a cluster network call by reading the files in order. |
| **[VI — The control plane](act-6-control-plane/README.md)** *(half-built)* | Act V never said who was arranging any of it. Scheduled by whom, watched from where? | Stop a controller and know, from the symptom alone, which loop is missing. |

## The capstone

Once Act V's lessons are behind you — and **before** its debugging pages, which build directly on it — read **[`the-whole-stack.md`](the-whole-stack.md)**: a single packet followed from `write()` to `read()` through all seven layers you built, with the file that proves each one. It is the synthesis that makes the debugging method obvious rather than arbitrary.

Then **[`your-own-machine.md`](your-own-machine.md)** points the same reflexes at the laptop in front of you.

## Where the road ends (for now)

The built course is Acts I–V plus half of Act VI. Act V is scoped to Kubernetes **networking** — Pods, CNI, Services (with headless, SRV and the traffic-policy shapes), CoreDNS, Ingress, Gateway API, NetworkPolicy and a debugging discipline. **[Act VI](act-6-control-plane/README.md)** has four of eight lessons: the API server as a filesystem over etcd, static pods, the reconciliation loop, and the cluster's own PKI — and none of its supporting pages yet.

Still **mapped but not written**: the rest of the control plane (etcd backup/restore, upgrades, node maintenance, control-plane troubleshooting), workloads and scheduling, storage and config, Helm/Kustomize/CRDs, autoscaling, observability, cryptography (opening the TLS lock), identity/access, Kubernetes security, and AWS networking & security — see the roadmap banner in [`../JOURNEY-MAP.md`](../JOURNEY-MAP.md).

If you are here for **CKA or CKS**, start at [`../exam-prep/`](../exam-prep/README.md): it maps every competency to the lesson that covers it and is honest about the ones nothing covers yet.
