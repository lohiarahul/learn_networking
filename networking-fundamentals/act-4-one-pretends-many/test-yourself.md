# Act IV — Test yourself

> Do this **after** working through all the lessons in [the act overview](README.md). Answer each one out loud or on paper *before* you open its answer — the attempt is what makes it stick, far more than re-reading. A wrong attempt followed by the right answer beats a confident skim every time.

> **Question 1 —** What single number distinguishes one network namespace from another, where does it live, and why does sharing it mean two processes share a network?

<details>
<summary>Answer</summary>

The **inode number** of the `net:` file at `/proc/self/ns/net`. Two processes are in the same network namespace if and only if that symlink points at the same inode — same inode means the same interfaces, routes, iptables, socket table, and the same `127.0.0.1`; a different inode means they're as isolated as two separate machines.

</details>

> **Question 2 —** What is a veth pair, why does it always come in twos, and which single command — when you build one by hand — quietly installs the route that makes the first ping succeed?

<details>
<summary>Answer</summary>

A veth pair is two virtual interfaces permanently bonded like the two plugs of a patch cable — whatever goes in one end comes out the other. It comes in twos because a cable needs two ends, one for each namespace it joins. The command that installs the route is `ip addr add` — assigning an address to an interface tells the kernel the whole subnet is directly reachable out that device, which silently creates the directly-connected route (not any `ip route` command).

</details>

> **Question 3 —** What is the difference between a Linux bridge and a veth pair, and at which layer does each operate?

<details>
<summary>Answer</summary>

A veth pair is a point-to-point wire with exactly two ends; a bridge is a software Ethernet switch you plug many veth ends into, which learns MAC addresses and forwards frames port-to-port. Both operate at Layer 2 (frames, MACs), beneath IP routing — but the bridge does the many-port switching the bare veth cannot.

</details>

> **Question 4 —** Where in the netfilter hooks does DNAT happen versus SNAT, and why must each sit where it does relative to the routing decision? What does conntrack do that makes the whole NAT round-trip work?

<details>
<summary>Answer</summary>

**DNAT** rewrites the destination in **PREROUTING**, before the routing decision, so the rewritten destination is what routing actually chooses a path for. **SNAT** rewrites the source in **POSTROUTING**, after the path is chosen, on the way out. **conntrack** remembers each translated connection's mapping, so when the reply comes back the kernel can reverse the translation and deliver it to the original private address — without it, NAT could rewrite outgoing packets but never untangle the replies.

</details>

> **Question 5 —** Why does VXLAN add roughly 50 bytes to every packet, and what does paying that tax buy you?

<details>
<summary>Answer</summary>

The wrapping adds 20 bytes outer IP + 8 bytes UDP + 8 bytes VXLAN header + 14 bytes inner Ethernet = 50 bytes per packet. That tax buys portability: the Pod packet is hidden inside an outer packet addressed to real node IPs, so the physical network — which has never heard of pod CIDR addresses — can route it normally, letting Pods on different nodes talk without teaching the underlying network anything about Pod IPs. It is also why a tunnel built on a 1500-byte wire comes up with an MTU of 1450: the kernel subtracts the tax for you.

</details>

> **Question 6 —** A namespace and a cgroup both isolate a container. Which question does each one answer, which file would you read to find a container's memory ceiling, and why does `free` inside that container disagree with it?

<details>
<summary>Answer</summary>

A namespace answers **what can this process see** (its own interfaces, routes, socket table, `127.0.0.1` — identified by the inode of `/proc/self/ns/net`). A cgroup answers **how much can it use** — the ceiling lives in `/sys/fs/cgroup/memory.max`, with current usage in `memory.current` and the OOM-kill count in `memory.events`. `free` disagrees because it reads `/proc/meminfo`, which reports the whole machine and is not namespaced at all: the container sees the host's RAM and none of its own limit. Symptom-wise, a namespace fault looks like "it cannot reach it"; a cgroup fault looks like "it was killed" or "it is inexplicably slow."

</details>

> **Question 7 —** `config.json`'s `linux.namespaces` array lists five namespace types. If you started a container with bare `runc` and then ran `docker ps`, would Docker's list include it — and what does your answer say about where a container's identity actually lives?

<details>
<summary>Answer</summary>

No. `docker ps` reads Docker's own bookkeeping, not the kernel. A container `runc` starts directly is a real, live network namespace with a real inode and a real cgroup — the kernel holds it whether or not any tool is watching. Identity lives in the kernel object, not in any daemon's tracking of it.

</details>

> **Question 8 —** `ctr run` has an optional `--sandbox` flag. `crictl` has a whole separate verb family — `runp`, `pods`, `rmp`, `stopp` — that `ctr` lacks entirely. What does a `RunPodSandbox` call set up that a plain `ctr run`/`runc run` never does, and how did the CNI error prove it rather than just assert it?

<details>
<summary>Answer</summary>

`RunPodSandbox` sets up the Pod's **network** as part of creating the sandbox itself, before any application container exists inside it — which is why the container's own IP is really the sandbox's IP, shared by everything that joins it later. The CNI failure (`cni plugin not initialized`) proved this rather than just asserting it: the call failed *at the network-setup step*, before it ever got as far as pulling an image or creating a container. CRI makes the sandbox a first-class object with its own lifecycle; `ctr`'s bolted-on `--sandbox` flag has no equivalent lifecycle commands at all.

</details>

---

← Back to **[Act IV overview](README.md)** · Next: **[Diagnose it →](diagnose.md)** (apply it under fire), then **[Act V →](../act-5-kubernetes/README.md)**
