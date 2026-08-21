# Act V — Many machines each pretend to be many

In 2014, Google published a paper with a deliberately boring title — *"Large-scale cluster management at Google with Borg"* — that quietly described how the company had, for the better part of a decade, run Search, Gmail, and YouTube. There was no per-application fleet of machines. There was one enormous shared pool of computers, and a piece of software called Borg that placed containers onto those machines the way an operating system places processes onto CPUs: you stated what you wanted to run and roughly how much it needed, and the scheduler found it a home, restarted it when it died, moved it when a machine failed, and crammed the leftovers into the gaps.

The insight was that a datacenter is just a very large computer, and a cluster manager is just its kernel. Kubernetes is the open-source reconstruction of that insight, written by some of the same people, and it has eaten the industry.

This act is not a Kubernetes tutorial. It will not teach you `kubectl apply` from scratch or walk you through Deployments and ReplicaSets. It does something more useful and, frankly, more honest: it shows you that **you have already built Kubernetes, by hand, in Acts I through IV** — you just didn't know the marketing names yet.

Every networking feature Kubernetes offers is a specific, recognizable application of something you already understand. A Pod is the network namespace from Act IV, held open by a tiny process. A Service is the DNAT rule from Act IV's iptables file, plus conntrack to remember the reply. CoreDNS is `/etc/hosts` from Act II, scaled to a cluster. A CNI plugin is the `ip link add ... type veth` command you typed by hand, run by a binary instead of a person. Ingress is the TLS handshake from Act III, terminated at the cluster's front door.

Throughout, we keep asking the one question from the orientation: *what is the file here, who reads it, who writes it?* — and the central question stays the same as it has been since page one: **how do we make `write()` on one machine become `read()` on another?**

After this act you will be able to look at any Kubernetes networking object and immediately name the Act I–IV primitive underneath it; trace a packet from a Pod's `write()` to a ClusterIP, through the iptables chains, to a destination Pod's `read()`, naming every rule it hits; and — the real payoff — debug a broken cluster network call with a five-question method that walks straight down the stack, where the answer to every question is in a file.

## The lab for this act

The netshoot container from the orientation got you through Acts I–IV, but Act V needs real nodes, a real kube-proxy, and a real CoreDNS. You can run all of it on your laptop with **kind** (Kubernetes-in-Docker), where each node is itself a Docker container you can open a shell into — which means every node-level command in this act becomes real.

The setup, the two ways in (node-level via `docker exec`, Pod-level via a netshoot Pod), a command for every lesson below, and what to do when cluster creation fails are all in [the lab lesson](01-lab-with-kind.md). Set that up first if you want to *run* this act rather than only read it.

## The lessons — read in this order

Work through these in order. Each one runs experiments against the cluster and ends with a link to the next, so you never have to guess where to go. Start with the lab setup.

1. **[The lab for Act V — a real cluster with kind](01-lab-with-kind.md)** — set this up first if you want to run the act, not just read it.
2. **[The Pod — a shared network namespace](02-pod-networking.md)** — a Pod is the Act IV namespace, held open by the pause container.
3. **[Services and kube-proxy — what answers to a ClusterIP?](03-services.md)** — go looking for the address, then find out what really answers to it.
4. **[CoreDNS — /etc/hosts for the cluster](04-coredns.md)** — Act II naming, scaled to a cluster.
5. **[Service shapes — when a load-balanced VIP is the wrong answer](04b-service-shapes.md)** — headless, SRV, session affinity, `ExternalName`, and who the packet appears to be from.
6. **[CNI — the veth-pair installer](05-cni.md)** — the Act IV wiring, run by a binary instead of by hand.
7. **[Ingress — the front door](06-ingress.md)** — the Act III TLS handshake terminated at the cluster edge. The one lesson that installs something.
8. **[Gateway API — when routing outgrows annotations](06b-gateway-api.md)** — Ingress's successor: the same job split along the seams that actually exist, and a status you have to read.
9. **[Network Policy — iptables with a YAML interface](07-network-policy.md)** — kernel-level allow/deny on Pod identity.
10. **[The debugging method — five questions in order](08-debugging.md)** — which file to read first when it breaks.
11. **[The method in action — a worked failure](09-debugging-walkthrough.md)** — the debugging walk end to end.

When you've finished them all, do the recall exercise from memory (answers hidden): **[Test yourself →](test-yourself.md)**. Then prove you can *use* it under fire with the symptom-first **[Diagnose it →](diagnose.md)** on-call drills, which break a real cluster four ways and tell you nothing but the symptom.

## What breaks here

Kubernetes assembles all of Act IV automatically, thousands of times a second, across hundreds of machines. That automation is wonderful right up until something doesn't connect — and then you are standing in front of a Pod that "can't reach the database," with a dozen layers of namespace, veth, bridge, NAT, DNS, and TLS between the two, every one of which Kubernetes built for you and any one of which could be the culprit. The magic that saved you from typing `ip` commands is now a magic you cannot see through.

The cure is not more magic. The cure is to remember that every layer is still a file, and to read the files in order. First see the whole machine working in [the whole stack](../the-whole-stack.md) — one packet from `write()` to `read()` across all five layers. Then learn the diagnostic walk for when it breaks: [the five-question method](08-debugging.md) and its [worked example](09-debugging-walkthrough.md), the last and most important files in this course — and then go break a cluster on purpose in [Diagnose it](diagnose.md).

> **The question to carry forward:** when the abstraction breaks, which file do you read first, and which do you read next?
