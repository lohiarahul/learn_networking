# By question — you have a symptom, not a tool name

Nothing arrives labelled "this is an ARP problem". It arrives as *"the app can't reach the database"*,
and the first useful move is narrowing which of six layers is lying to you.

This page is a router, not a method. **The method is
[the five questions, in order](../networking-fundamentals/act-5-kubernetes/08-debugging.md)** — read that
once and this page becomes a lookup for the tools it tells you to reach for. Each row below is
*symptom → the instrument that either confirms or eliminates a cause*, with the kernel file that settles
it when a tool and your expectation disagree.

The ordering inside each block matters: it runs cheapest-and-most-eliminating first.

---

## "Nothing resolves"

| Ask | Reach for | The file that settles it |
|---|---|---|
| Is the resolver config what I think? | `cat /etc/resolv.conf` | it *is* the file — check `search` and `ndots` (how many dots a name needs before it is tried as-is, rather than having each `search` domain appended first), not just `nameserver` |
| Does the nameserver answer at all? | `dig @<nameserver> <name>` | — |
| Does DNS answer but the app still fail? | `getent hosts <name>` | `/etc/nsswitch.conf` — `dig` skips NSS, applications don't |
| In a cluster: is it the *cluster* resolver? | `kubectl -n kube-system get pods -l k8s-app=kube-dns` | the Pod's own `/etc/resolv.conf`, which the kubelet wrote |

**The trap:** `dig` succeeding proves the nameserver works. It does not prove *the application* will
resolve. An application calls `getaddrinfo()`, which goes through the Name Service Switch (NSS) —
`/etc/nsswitch.conf` decides which sources are consulted and in what order, and `/etc/hosts` is usually
first. `dig` skips all of it and talks to the nameserver directly. `getent hosts` is the tool that
resolves the way the application does.

Lessons: [DNS](../networking-fundamentals/act-2-two-machines/04-dns.md) ·
[CoreDNS](../networking-fundamentals/act-5-kubernetes/04-coredns.md)

---

## "It works by IP but not by name"

You have already proved routing and filtering are fine, so this is resolution only — go to the block
above. The one addition: check whether something *else* is answering. `/etc/hosts` beats DNS, and a
stale entry there survives every DNS fix you make.

---

## "The connection just hangs"

Hanging and refusing are different failures, and separating them is the highest-value first move.

| Ask | Reach for | Reading |
|---|---|---|
| Refused, or hanging? | `curl -v` or `nc -v <host> <port>` | **refused** = something answered with RST → a listener is missing or the port is wrong. **hangs** = nothing answered → a packet is being dropped silently |
| Is my SYN even leaving? | `tcpdump -ni any "tcp port <p> and tcp[tcpflags] & tcp-syn != 0"` | SYN out with no SYN-ACK back = drop on the path or at the far end |
| What does my side think the socket is doing? | `ss -tanp` | stuck in `SYN-SENT` confirms nothing came back |
| Is a rule dropping it? | `iptables-save` (then read, don't guess) | — |
| Is the flow being tracked, and as what? | `conntrack -E` while you retry | `/proc/net/nf_conntrack` |

**A silent drop is almost always a filter or a route.** A refusal is almost always the application.

Lessons: [the TCP handshake](../networking-fundamentals/act-3-the-internet/01-tcp-handshake.md) ·
[TCP states](../networking-fundamentals/act-3-the-internet/02-tcp-states.md) ·
[conntrack](../networking-fundamentals/act-3-the-internet/02b-conntrack.md)

---

## "Packets leave and never come back"

| Ask | Reach for | The file |
|---|---|---|
| Where does the kernel think this destination lives? | `ip route get <dst>` | `/proc/net/route` — and note `ip route get` gives you the *decision*, not the table |
| Does the next hop resolve at layer 2? | `ip neigh show` | `/proc/net/arp` — `FAILED` or `INCOMPLETE` is your answer |
| Is the wire itself working? | `arping <next-hop>` | proves L2 with IP entirely out of the picture |
| Is the return path different from the outbound one? | `tcpdump` on both ends at once | asymmetric routing is the classic cause of "half works" |

Lessons: [IP and routing](../networking-fundamentals/act-2-two-machines/02-ip-and-routing.md) ·
[ethernet and ARP](../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md)

---

## "Small requests work, large ones hang"

This is MTU, nearly every time, and it is worth its own entry because nothing about the symptom says so.

| Ask | Reach for |
|---|---|
| What is the MTU on each hop I control? | `ip link show` / `cat /sys/class/net/<dev>/mtu` |
| Does it break at a specific size? | `ping -M do -s <bytes> <host>` — walk the size up until it fails |
| Is ICMP "fragmentation needed" being dropped? | `tcpdump -ni any icmp` — if it is, path MTU discovery is blind and this hangs forever |

The overlay case is the common one: a VXLAN or WireGuard header eats bytes, so the effective MTU inside
a tunnel is lower than the interface claims.

Lessons: [MTU and fragmentation](../networking-fundamentals/act-2-two-machines/03b-mtu-and-fragmentation.md)
· [overlay and VXLAN](../networking-fundamentals/act-4-one-pretends-many/04-overlay-vxlan.md)

---

## "It works from the node but not from the Pod"

The single most useful framing: **a Pod is a network namespace.** Almost every instance of this is a
question about which namespace you are standing in.

| Ask | Reach for |
|---|---|
| Am I even in a different namespace? | compare `readlink /proc/self/ns/net` on both sides — same inode means same network |
| What does the Pod's own stack look like? | `kubectl exec` then `ip addr`, `ip route`, `cat /etc/resolv.conf` |
| Is it policy rather than plumbing? | `kubectl get networkpolicy -A` — and remember a namespace with any ingress policy denies everything not matched |
| Is the Service's backend list actually populated? | `kubectl get endpointslices -l kubernetes.io/service-name=<svc>` — empty means the selector matches nothing |
| Is `kube-proxy` programming what I expect? | `iptables-save \| grep <clusterIP>` on the node |
| …and if this cluster inherited IPVS mode? | `ipvsadm -L -n` for the services and their real servers, `ipvsadm -l -n -c` for which client is pinned to which backend — or `cat /proc/net/ip_vs_conn`, the same table as a file (roster only) |

**The trap:** a ClusterIP answers from nowhere. It is not a host, nothing listens on it, and pinging it
proves nothing at all — it exists only as a rewrite rule.

Lessons: [pod networking](../networking-fundamentals/act-5-kubernetes/02-pod-networking.md) ·
[services](../networking-fundamentals/act-5-kubernetes/03-services.md) ·
[network policy](../networking-fundamentals/act-5-kubernetes/07-network-policy.md)

---

## "`tcpdump` shows the wrong address, and I think my cluster is broken"

Worth its own entry, because everything you learned in Acts II–IV predicts the opposite and the
confusion is total.

If the cluster runs an eBPF datapath that replaces `kube-proxy` — Cilium in kube-proxy-free mode is the
common case — Service-to-backend translation happens in **socket-level load balancing**: a cgroup-BPF
program hooked onto `connect()`, `sendmsg()` and `recvmsg()`. The address is rewritten *inside the
syscall*, before a packet has been built.

So `tcpdump` on the Pod's veth shows the **backend Pod IP**, never the Service IP. Nothing is wrong. The
Service IP existed only for the duration of a `connect()` call, and packet capture is downstream of
that. No netfilter-based datapath behaves this way, which is exactly why this catches people.

| Ask | Reach for |
|---|---|
| Is there an eBPF datapath at all? | `bpftool net show`, and `bpftool cgroup tree` for the socket hooks |
| Is a Service being translated, and to what? | the datapath's own tooling — `cilium-dbg service list`, then `cilium-dbg monitor -v` |
| Where in the kernel did a packet actually go or die? | `pwru` or `retis` — both trace arbitrary kernel functions, which `tcpdump` structurally cannot |

The general form of the lesson: **`tcpdump` taps `AF_PACKET` on a device.** It can tell you what
crossed that point and nothing about what happened before or after — including where in the stack a
packet was dropped. Every tool in the third row exists to close that gap.

Lessons: [encryption between Pods](../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md)
· [CNI](../networking-fundamentals/act-5-kubernetes/05-cni.md)

---

## "Which process owns this socket / this port?"

| Ask | Reach for |
|---|---|
| What is listening, and whose is it? | `ss -tlnp` |
| Full join across every process | `lsof -i :<port>` |
| No tools available at all | the inode in `/proc/net/tcp`, then `ls -l /proc/*/fd 2>/dev/null \| grep <inode>` |

That last row is the one worth having done once by hand: it is what every tool in the first two rows is
doing for you.

Lessons: [ports and /proc/net/tcp](../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md)

---

## "It's slow, but nothing is broken"

The hardest class, because every binary check passes. This is where the course's toolset thins out, and
the honest answer is that most of the instruments below are
**[roster only](tools/README.md#the-honest-tally)**.

| Ask | Reach for | Taught? |
|---|---|---|
| Is TCP retransmitting? | `ss -ti` — read `retrans`, `rtt`, `cwnd` | ✅ |
| How often, machine-wide? | `nstat` — retransmits and listen overflows as deltas | roster only |
| Is loss on one hop or all of them? | `mtr` | roster only |
| Is the NIC dropping before the stack sees it? | `ethtool -S <dev>` | roster only |
| Is the conntrack table full? | `cat /proc/sys/net/netfilter/nf_conntrack_{count,max}` | ✅ |
| Is it the application, not the network? | `strace -c`, or `bpftrace` on a live box | `strace` ✅ · `bpftrace` roster only |
| Is a queueing discipline on this device the thing hurting me? | `tc -s qdisc show dev <dev>` — read `dropped` and `overlimits` | roster only |
| Can I *reproduce* what the customer is seeing? | `tc qdisc add dev <dev> root netem delay 100ms 20ms` — also `loss 5%`, `reorder 25% 50%`, `duplicate 1%` — and `tc qdisc del dev <dev> root` to undo it | roster only |

**Learn the `del` before the `add`.** `netem` is the one instrument here that makes things worse on
purpose, and it is the only way anything in this reference can reproduce a bad network — eBPF has no
equivalent, because `netem` is a qdisc and eBPF replaced `tc`'s *classifier*, not its queues. Type it on
a device you can afford to lose, and know how to take it off before you put it on.

`nf_conntrack_count` approaching `nf_conntrack_max` is worth checking early: the failure it produces is
intermittent, load-dependent, and looks exactly like a flaky network.

Lessons: [TCP and reliability](../networking-fundamentals/act-3-the-internet/03-tcp-reliability.md) ·
[conntrack](../networking-fundamentals/act-3-the-internet/02b-conntrack.md)

---

## "The cluster itself is broken"

When `kubectl` is the thing that stopped working, everything above is unreachable and the order inverts —
you drop to the node.

| Ask | Reach for |
|---|---|
| Is the API server's container even running? | `crictl ps -a` on the control-plane node |
| Why did it exit? | `crictl logs <id>` |
| Is its manifest valid? | `cat /etc/kubernetes/manifests/kube-apiserver.yaml` — the kubelet reads this file directly, no API needed |
| Is etcd alive? | `etcdctl endpoint health` with the PKI paths from `/etc/kubernetes/pki/etcd/` |

Lessons: [when the control plane breaks](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md)
· [static pods](../networking-fundamentals/act-6-control-plane/02-static-pods.md)

---

## Then practise it

Reading a routing table is not the same skill as reaching for one under pressure. The acts' drills exist
for that — each one puts a machine into a genuinely broken state and gives you only the symptom:

[Act I](../networking-fundamentals/act-1-one-machine/diagnose.md) ·
[Act II](../networking-fundamentals/act-2-two-machines/diagnose.md) ·
[Act III](../networking-fundamentals/act-3-the-internet/diagnose.md) ·
[Act IV](../networking-fundamentals/act-4-one-pretends-many/diagnose.md) ·
[Act V](../networking-fundamentals/act-5-kubernetes/diagnose.md) ·
[Act VI](../networking-fundamentals/act-6-control-plane/diagnose.md) ·
[Act VII](../networking-fundamentals/act-7-workloads/diagnose.md) ·
[Act X](../networking-fundamentals/act-10-cluster-security/diagnose.md)

Next: **[command reference, by act](05-per-act-commands.md)** — every command the course runs, broken
down element by element.
