# The index — one row per instrument

Alphabetical, because that is what a lookup wants. If you have a symptom rather than a tool name, start
at **[by question](04-by-question.md)** instead. If you want to *derive* a command rather than find one,
**[the grammar](01-the-grammar.md)** is the page.

**How to read the columns.**

- **Name** — what the abbreviation expands to, where the project or man page says so. Entries marked
  *(folklore)* are popular expansions the tool's own documentation does not confirm; see
  [Rule 5](01-the-grammar.md#rule-5--what-the-names-expand-to-and-which-expansions-are-folklore).
- **The one thing only it shows you** — why this tool exists when the others do. If two rows have the
  same answer, one of them is redundant and should be cut.
- **Speaks** — two tokens: *which kernel interface the tool addresses*, then *its grammar*. The
  interface is the one that decides what the tool can possibly know; the grammar is the one that lets you
  guess a subcommand. `obj-verb` = noun first; `verb-obj` = verb first; `flags` = a conventional getopt
  tool; *filter* = it has an expression language of its own. The eight interfaces are defined below, each
  by a syscall you can see in `strace` — so this column is measurable, not a matter of taste.
- **Mode** — what it can do to the world. `read-only` = cannot change kernel or cluster state, so it is
  safe anywhere. `mutate` = can change state. `live` = **streams events as they happen**, which is the
  only way to catch something a polling loop misses. Cells combine: `mutate · live`.
- **In the course** — a link to the lesson that runs it, or **roster only**. `roster only` means
  [`Toolbelt.md`](../Toolbelt.md) names it and **no lesson runs it** — it is here as territory, not as
  something you have been taught. Verified by grep against the lesson sources.

---

## The eight interfaces — the whole roster on one screen

Every tool below is a **client of one kernel interface**, and that is the fact worth memorising, because
it is the only one you can *derive* things from. Tools sharing an interface share a grammar, share a
blind spot, and are often substitutable. Tools in different rows **never** substitute for each other, no
matter how similar their output looks.

Each interface is defined by what `strace` shows, so a disputed row can be settled by measurement. Every
signature below was measured in the course's own lab image.

| Interface | What `strace` shows | Tools | What this interface can never tell you |
|---|---|---|---|
| **`netlink`** | `socket(AF_NETLINK, …)` | `ip` · `ss` · `bridge` · `tc` · `conntrack` · `nft` · `ipset` · `ipvsadm` · `ethtool` · `devlink` · `wg` · `iptables`&nbsp;† · `iptables-save`&nbsp;† | What a packet *did* — it reports configured and tracked state, never a packet's path |
| **`procfs`** | `open()` on `/proc` or `/sys` | `cat` · `stat` · `readlink` · `netstat` · `nstat` · `lsof` · `sysctl` · `pgrep` · `arp` · `capsh` · `getpcaps` · `apparmor_parser` · `mount`/`findmnt` · `ulimit`/`prlimit` | Anything the kernel does not already export as a file — and it is a *snapshot*, so transients are invisible |
| **`socket`** | `socket(AF_INET, SOCK_STREAM｜SOCK_DGRAM)` | `nc` · `socat` · `curl` · `dig` · `drill` · `host` · `nslookup` · `getent hosts`&nbsp;¶ · `iperf3` · `ping`&nbsp;§ · `openssl`&nbsp;⁂ | Why it failed. A socket tool reports the *verdict*, and you need another interface for the cause |
| **`packet`** | `socket(AF_PACKET, …)` or `SOCK_RAW` | `tcpdump` · `tshark` · `scapy` · `arping` · `traceroute` · `mtr` · `nmap`&nbsp;‡ | Which *process* or *rule* was responsible — it sees bytes on a link, not the host state behind them |
| **`probe`** | `ptrace` · `bpf(2)` · `perf_event_open` | `strace` · `ltrace` · `bpftrace` · `bpftool` · `pwru` · `retis` · `falco` | Nothing, and that is the point — this is the only interface that can answer "which kernel function dropped it". It is also the only one that needs a running target |
| **`nsapi`** | `unshare` · `setns` · `clone` + bind mount | `ip netns`&nbsp;‖ · `unshare` · `nsenter` · `runc` | What is *inside* a namespace. These tools move you between namespaces; they read nothing |
| **`httpapi`** | HTTPS/gRPC to a daemon or API server | `docker` · `crictl` · `kubectl` · `kind` · `kubeadm` · `etcdctl` · `helm` · `cilium` · `trivy` · `cosign` · `crane` | What the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **`local`** | none — files or bytes you already have | `jq` · `xxd`/`base64` · `etcdutl` · `kustomize` · `kube-bench` | Anything at all about your machine. These reshape input another tool produced |

`13 + 14 + 11 + 7 + 7 + 4 + 11 + 5 = 72` — every row on this page except the macOS table, each in exactly
one interface.

> ### The unit is the *invocation*, not the binary
>
> Three rows carry a footnote because the same executable speaks two interfaces depending on how you
> call it, and this is not pedantry — it is the mechanism behind three separate traps in this course:
>
> | | Splits how | Why it matters |
> |---|---|---|
> | **†** `iptables` | `netlink` on the nf_tables backend · `setsockopt` on legacy | **`iptables -V` tells you which.** Measured: `iptables -t nat -L` opens `NETLINK_NETFILTER` — on a current box the tool this course teaches *is* the tool it lists as `roster only` |
> | **‡** `nmap` | `packet` for `-sS` · `socket` for the `-sT` default | The half-open scan needs raw packets; the default scan is an ordinary `connect()` your application logs |
> | **‖** `ip netns` | `nsapi` to create and enter · `netlink` to list nsids | `ip netns add` is `unshare` plus a bind mount under `/run/netns`. **This is exactly why it cannot see Docker's namespaces** — see [the state map](02-the-state-map.md#rule-namespace-flag-letters-are-the-filenames) |
>
> Two more rows carry markers for a different reason — the interface is not what people assume:
>
> - **§ `ping`** opens `AF_INET, SOCK_DGRAM`, **not** `SOCK_RAW`. ICMP datagram sockets, gated by
>   `net.ipv4.ping_group_range` — which is why `ping` no longer needs to be setuid.
> - **¶ `getent hosts`** opened **no socket at all** when measured against `localhost`: `/etc/hosts`
>   answered and NSS stopped there. That is the whole reason this row exists rather than being a
>   duplicate of `dig`.
> - **⁂ `openssl`** is `socket` for `s_client` and `local` for everything else (`dgst`, `genpkey`,
>   `enc`, `x509`) — the only tool here that is a whole crypto library with a network mode bolted on.

## What can catch a transient

The single most useful compartment on this page, because the answer is short and nobody has it
memorised. **22 of the 72 tools can stream events**; everything else hands you a snapshot, and
*"I looked and saw nothing"* is not evidence when the thing you are hunting lasted 40 ms.

| Interface | Streams with |
|---|---|
| `netlink` | `ip monitor` · `ss -E` · `bridge monitor` · `conntrack -E` · `nft monitor` · `tc monitor` · `devlink monitor` |
| `packet` | `tcpdump` · `tshark` · `scapy`'s `sniff()` · `mtr` |
| `probe` | `strace` · `ltrace` · `bpftrace` · `bpftool prog tracelog` · `pwru` · `retis` · `falco` |
| `httpapi` | `docker events` · `kubectl get -w` · `etcdctl watch` · `cilium monitor` |
| `procfs` · `socket` · `nsapi` · `local` | **nothing** — these four interfaces have no streaming form at all |

That last row is the load-bearing one. If your evidence has to come from `/proc`, you are polling, and
you will miss things. Reach for a `netlink` or `probe` tool instead.

## Reading the kernel's network state

| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `ip` | internet protocol utility | Everything netlink's route family knows: links, addresses, routes, neighbours, rules, namespaces. `-j` gives it to you as JSON | netlink · obj-verb, 30 objects | mutate · live | [ethernet and ARP](../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| `ss` | *"another utility to investigate sockets"* — "socket statistics" is *(folklore)* | Per-socket TCP internals: RTT, cwnd, retransmits (`-i`) and buffer accounting (`-m`). Also `--cgroup`, which attributes a socket to its cgroup — i.e. **to a container, without touching the container runtime** — and `-E` to stream sockets as they are destroyed, catching short-lived connections a polling loop misses | netlink · flags + *filter* | live | [ports and /proc/net/tcp](../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md) |
| `netstat` | network statistics | Nothing `ss` doesn't, and structurally less: it reads `/proc/net/tcp`, whose kernel documentation says *"these interfaces are deprecated in favor of tcp_diag"*. Kept because it is on every legacy box and in every old runbook | procfs · flags | read-only | [taught as `ss`'s rival](../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md) |
| `lsof` | list open files | The join from a socket back to *which process and which fd* owns it, across every process at once | procfs · flags | read-only | [the fd table](../networking-fundamentals/act-1-one-machine/01-the-fd-table.md) |
| `bridge` | — | A bridge's forwarding database (`fdb`), its VLAN filtering table, and per-port state. `ip` creates bridges; only this inspects them | netlink · obj-verb | mutate · live | [veth and bridge](../networking-fundamentals/act-4-one-pretends-many/02-veth-and-bridge.md) |
| `conntrack` | connection tracking | The kernel's flow table as a live stream (`-E`), which is the only way to watch NAT decisions happen | netlink · flags | mutate · live | [conntrack](../networking-fundamentals/act-3-the-internet/02b-conntrack.md) |
| `sysctl` | system control | Every kernel tunable by name, and `-a` makes it searchable | procfs · flags | mutate | [conntrack](../networking-fundamentals/act-3-the-internet/02b-conntrack.md) |
| `nstat` | network statistics | Protocol counters from `/proc/net/snmp` and `netstat`, *as deltas since last call* — retransmits, listen overflows, drops | procfs · flags | read-only | **roster only** |
| `ethtool` | "ethernet tool" *(folklore — undocumented)* | The NIC's own truth: link speed, ring sizes, offloads (`-k`), and per-queue hardware counters (`-S`). Explains why `tcpdump` shows a 64 KB "packet" on a 1500-byte link | netlink · flags | mutate | **roster only** |
| `devlink` | *no documented expansion* | Hardware-level device and port config below what `ip link` can reach | netlink · obj-verb | mutate · live | **roster only** |
| `bpftool` | "BPF tool" *(folklore — undocumented)* | What eBPF programs and maps are loaded and where they are attached. `bpftool net show` covers xdp/tc/tcx per device; **`bpftool cgroup tree` covers the cgroup hooks, which is where Cilium's socket-level load balancing actually lives.** The inventory command for an eBPF datapath, with no substitute | probe · obj-verb | mutate · live | **roster only** |

## Filtering, NAT and traffic shaping

| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `iptables` | IP tables | The legacy rule syntax that most of the internet's documentation, and `kube-proxy`'s default mode, still speaks. **Run `iptables -V` first:** since 1.8 the same CLI sits over two different kernel backends and prints either `(nf_tables)` or `(legacy)`. Never mix the legacy and nft tools — both subsystems become active and the evaluation order between them is undefined | netlink&nbsp;† · flags (`-t -A -m -j`) | mutate | [iptables and NAT](../networking-fundamentals/act-4-one-pretends-many/03-iptables-and-nat.md) |
| `iptables-save` | — | The whole ruleset in one atomic, diffable text dump — the only sane way to read a large ruleset | netlink&nbsp;† · flags | read-only | [services](../networking-fundamentals/act-5-kubernetes/03-services.md) |
| `nft` | nftables — netfilter tables | One tool and one grammar for IPv4, IPv6, ARP and bridge (the `inet` family), plus the sets and maps that iptables needed `ipset` for. In-kernel since 3.13; netfilter's own wiki has called the xtables tools legacy since 2018, RHEL 10 no longer ships the legacy `ip_tables` module at all, and Docker Engine 29 has an experimental native nftables backend it intends to make the default | netlink · verb-obj | mutate · live | **roster only** |
| `ipset` | IP set | Hash sets of addresses/ports that iptables can match in one step instead of rule-by-rule. Now largely historical: nftables has native sets and maps, and `ipset` is unmaintained and slated for removal on RHEL | netlink · verb-obj | mutate | **roster only** |
| `tc` | traffic control | Queueing, rate limits, and — via `netem` — deliberately injected loss, delay, reordering and duplication. **The only way to *reproduce* a bad network**, and `netem` has no eBPF equivalent. eBPF did not replace `tc`; it replaced one thing that used to hang off it, the packet classifier. Modern eBPF datapath programs attach straight to a device's ingress and egress (an interface called TCX, since kernel 6.6) instead of hanging off one of `tc`'s queueing disciplines | netlink · obj-verb (qdisc/class/filter) | mutate · live | **roster only** |
| `ipvsadm` | IP virtual server admin | The IPVS connection and destination tables (`/proc/net/ip_vs`, `ip_vs_conn`) when `kube-proxy` runs in IPVS mode — still the right way to read a cluster that inherited it. Note the split: **IPVS in Linux is not deprecated; `kube-proxy`'s IPVS *mode* is** — deprecated in Kubernetes 1.35, with removal targeted at 1.43. `kube-proxy`'s nftables mode went GA in 1.33, though iptables remains the default | netlink · flags | mutate | **roster only** |

## Capture and packet-level inspection

| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `tcpdump` | TCP dump | Bytes actually on the wire, with a compositional filter language and `-w` to a `.pcap` you can open elsewhere | packet · flags + *libpcap filter* | live | [ICMP and UDP](../networking-fundamentals/act-2-two-machines/03-icmp-and-udp.md) |
| `tshark` | terminal shark | The same capture *dissected* — Wireshark's protocol decoders, so you read fields instead of hex | packet · flags + *filter* | live | [Act II in the wild](../networking-fundamentals/act-2-two-machines/in-the-wild.md) |
| `scapy` | — | Packets you *construct*: become the protocol instead of watching it. The active counterpart to `tcpdump` | packet · Python library | mutate · live | [ethernet and ARP](../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| `pwru` | "packet, where are you?" | Which **kernel function** your packet passed through, and which one dropped it — kprobes on every `skb`-taking function. Structurally impossible with `tcpdump`, and the tool Cilium support asks you to run | probe · flags + *filter* | live | **roster only** |
| `retis` | — | libpcap filters compiled to eBPF and inlined at *arbitrary probe points*, correlating kernel packet-buffer (`skb`) drops, netfilter verdicts and conntrack against one packet | probe · verb-obj | live | **roster only** |
| `nmap` | network mapper | What a *scanner* sees, including the half-open SYN scan that never completes a handshake so your application never logs it | packet&nbsp;‡ · flags | read-only | [TCP states and the SYN scan](../networking-fundamentals/act-1-one-machine/05b-tcp-states-and-the-syn-scan.md) |

## Reachability and paths

| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `ping` | named after sonar; "Packet InterNet Groper" is *(folklore)* | Whether ICMP echo returns, and the RTT distribution | socket&nbsp;§ · flags | read-only | [loopback](../networking-fundamentals/act-1-one-machine/04-loopback.md) |
| `arping` | ARP ping | Reachability at **layer 2**, bypassing IP entirely — proves the wire works when routing does not | packet · flags | read-only | [ethernet and ARP](../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| `traceroute` | — | The hop list, by walking TTL upward | packet · flags | read-only | [ICMP and UDP](../networking-fundamentals/act-2-two-machines/03-icmp-and-udp.md) |
| `mtr` | "Matt's traceroute" *(after Matt Kimball — widely reported, not in the project's docs)* | Continuous per-hop loss and latency, which is how you tell "one bad hop" from "the whole path is bad" | packet · flags | live | **roster only** |
| `arp` | ARP cache tool | Nothing `ip neigh` doesn't. Recognise it in old runbooks | procfs · flags | mutate | [taught as `ip neigh`'s rival](../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |

## Name resolution

| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `dig` | "domain information groper" *(folklore — BIND's docs do not expand it)* | The full DNS response — flags, authority and additional sections, TTLs. Talks to the resolver directly, **skipping NSS** | socket · `@server name type` + `+opts` | read-only | [DNS](../networking-fundamentals/act-2-two-machines/04-dns.md) |
| `drill` | — | The same, DNSSEC-aware, and it ships in `netshoot` where `dig` sometimes doesn't | socket · flags | read-only | [Act IV in the wild](../networking-fundamentals/act-4-one-pretends-many/in-the-wild.md) |
| `host` | — | A one-line answer, which is what you want inside a loop | socket · flags | read-only | **roster only** — the word appears in the lessons only as prose ("host bits", an Ingress `host` rule); no lesson runs the command |
| `nslookup` | name server lookup | Nothing the others don't, but it is the one present on hosts with nothing else installed | socket · interactive | read-only | [policy shapes](../networking-fundamentals/act-5-kubernetes/07b-policy-shapes.md) |
| `getent hosts` | get entries | **What the application will actually get** — it resolves the way an application does, through glibc's Name Service Switch (`/etc/nsswitch.conf`, then `/etc/hosts`, then DNS), rather than talking to a nameserver directly. The tool that resolves "`dig` works but the app can't" | socket&nbsp;¶ · `getent <db> <key>` | read-only | [Act II diagnose](../networking-fundamentals/act-2-two-machines/diagnose.md) |

## Sockets and syscalls

| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `nc` | netcat | A raw TCP/UDP endpoint you drive by hand — the smallest possible client or server | socket · flags | read-only | [the TCP handshake](../networking-fundamentals/act-3-the-internet/01-tcp-handshake.md) |
| `socat` | SOcket CAT | `nc` with every socket type on both sides: TLS, Unix sockets, PTYs, and bidirectional relays between any two | socket · `addr1 addr2` | read-only | **roster only** |
| `curl` | "a play on *Client for URLs*" | Every byte of an HTTP(S) exchange with `-v`, plus timing breakdowns and protocol selection (`--http3`) | socket · flags | read-only | [HTTP](../networking-fundamentals/act-3-the-internet/04-http.md) |
| `openssl` | — | Every cryptographic primitive as a separate command (`dgst`, `enc`, `genpkey`, `x509`, `verify`) **and** `s_client`, which opens a TLS connection by hand so you read the handshake instead of trusting it. The only tool here that shows you a certificate chain as the peer actually presented it | socket&nbsp;⁂ · verb-obj | mutate | [TLS opened](../networking-fundamentals/act-8-trust/06-tls-opened.md) |
| `strace` | system call trace | The exact syscalls a process makes, with arguments and return values — and it stops the world to do it | probe · `-e trace=…` | live | [minihttp](../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) |
| `ltrace` | library call trace | The same, one layer up: libc calls rather than syscalls | probe · flags | live | [minihttp](../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) |
| `bpftrace` | BPF trace | Kernel and userspace probes at near-zero overhead, on a live production box, without stopping anything. `strace`'s successor | probe · its own language | live | **roster only** |
| `iperf3` | internet performance | Achievable throughput between two points, which no passive tool can tell you | socket · flags | read-only | **roster only** |
| `ulimit` / `prlimit` | user limit / process limit | The descriptor ceiling that quietly breaks busy servers — `prlimit` reads it on an *already-running* process | procfs · shell builtin / flags | mutate | [minihttp](../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) |

## Namespaces, cgroups, capabilities

| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `ip netns` | — | Named network namespaces, created as bind mounts under `/run/netns` — which is why it cannot see Docker's | nsapi&nbsp;‖ · obj-verb | mutate | [namespaces](../networking-fundamentals/act-4-one-pretends-many/01-namespaces.md) |
| `unshare` | — | A new namespace of any type, created *around a new process* — the mechanism `docker run` performs for you | nsapi · flags (`-m -u -i -n -p -U -C -T`) | mutate | [the kernel says no](../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md) |
| `nsenter` | "namespace enter" *(folklore — undocumented)* | Entry into an *existing* process's namespaces — the mechanism under `docker exec` and `kubectl exec`, and the way into a container with no shell of its own | nsapi · same flag letters as `unshare` | mutate | **roster only** *(named in prose, never run)* |
| `capsh` | capability shell | Which Linux capabilities a process actually holds, decoded from `/proc/<pid>/status`'s `CapEff` bitmask | procfs · flags | mutate | [what a container may do](../networking-fundamentals/act-10-cluster-security/01-what-a-container-may-do.md) |
| `getpcaps` | get process capabilities | The same, for a running PID, in one line | procfs · `getpcaps <pid>` | read-only | [Act X diagnose](../networking-fundamentals/act-10-cluster-security/diagnose.md) |
| `apparmor_parser` | — | Whether a profile loads, and in what mode — the difference between "enforcing" and "you thought it was enforcing" | procfs · flags | mutate | [the kernel says no](../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md) |
| `runc` | run container | The OCI runtime that actually creates the namespaces and cgroups. Below every higher-level tool | nsapi · verb-obj | mutate | [the kernel says no](../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md) |

## Container and cluster runtimes

| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `docker` | — | The developer-facing view, and `docker network inspect` — Act IV's bridge and veth pairs, printed as JSON | httpapi · obj-verb | mutate · live | [the fd table](../networking-fundamentals/act-1-one-machine/01-the-fd-table.md) |
| `crictl` | CRI control | The node's container runtime *directly* — the only view left when the API server is down and `kubectl` is useless | httpapi · verb-obj | mutate | [static pods](../networking-fundamentals/act-6-control-plane/02-static-pods.md) |
| `kubectl` | — | The API server's whole object graph, and `explain` makes the schema self-describing | httpapi · verb-obj | mutate · live | [pod networking](../networking-fundamentals/act-5-kubernetes/02-pod-networking.md) |
| `kind` | Kubernetes in Docker | A real multi-node cluster on one machine, where every node is a container you can `docker exec` into | httpapi · verb-obj | mutate | [the lab with kind](../networking-fundamentals/act-5-kubernetes/01-lab-with-kind.md) |
| `kubeadm` | — | What the control plane's own certificates and version skew actually are, and the upgrade plan | httpapi · verb-obj | mutate | [upgrades and version skew](../networking-fundamentals/act-6-control-plane/06-upgrades-and-version-skew.md) |
| `etcdctl` | etcd control | The cluster's stored state as raw keys — the layer beneath every Kubernetes object | httpapi · verb-obj | mutate · live | [etcd backup and restore](../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) |
| `etcdutl` | etcd utility | Offline snapshot operations (`snapshot restore`) that need no running etcd | local · verb-obj | mutate | [etcd backup and restore](../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) |
| `helm` | — | What a chart *renders to* before it is applied (`template`), and what is currently released (`history`) | httpapi · verb-obj | mutate | [shipping a set of objects](../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) |
| `kustomize` | — | The same overlay-resolved output, with no templating language at all | local · verb-obj | read-only | [shipping a set of objects](../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) |
| `cilium` | — | An eBPF datapath's own view: policy verdicts, identities, and its BPF maps | httpapi · verb-obj | mutate · live | [encryption between Pods](../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md) |
| `wg` | WireGuard | The live tunnel state — peers, handshakes, keys — under Cilium's or anyone else's encryption | netlink · verb-obj | mutate | [encryption between Pods](../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md) |

## Supply chain and runtime security

| Tool | Name | The one thing only it shows you | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `trivy` | — | Known vulnerabilities and an SBOM for an image you are about to ship | httpapi · verb-obj | read-only | [what you shipped](../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) |
| `cosign` | — | Whether an image is signed *by a key you trust* — and the trap that any attacker can sign with theirs | httpapi · verb-obj | mutate | [what you shipped](../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) |
| `crane` | — | A registry's raw content: digests, manifests, layers, without pulling the image | httpapi · verb-obj | mutate | [what you shipped](../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) |
| `kube-bench` | — | The cluster's own config scored against the CIS benchmark, file by file | local · flags | read-only | [the doors left open](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) |
| `falco` | — | Syscall-level events *as they happen* — the runtime half that no scanner can give you | probe · rules + flags | live | [seeing it happen](../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md) |

## General-purpose, used here to read kernel state

| Tool | Name | Why it is in a networking reference | Speaks | Mode | In the course |
|---|---|---|---|---|---|
| `cat` | concatenate | The primary interface to `/proc` and `/sys`. Most of this course is `cat` | procfs · flags | read-only | throughout |
| `stat` | — | Proves a `/proc` file reports `Size: 0` and still has content — the contradiction that makes "everything is a file" mean something | procfs · flags | read-only | [everything is a file](../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) |
| `readlink` | — | Reads a magic symlink's *computed* target — `net:[4026531840]`, the namespace identity test | procfs · flags | read-only | [everything is a file](../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) |
| `mount` / `findmnt` | — | Which filesystems are grafted where; `findmnt` draws it as a tree with propagation flags | procfs · flags | mutate | [everything is a file](../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) |
| `pgrep` | process grep | PID lookup by name, so `/proc/<pid>/…` paths can be built in one line | procfs · flags | read-only | [the socket object](../networking-fundamentals/act-1-one-machine/02-the-socket-object.md) |
| `jq` | JSON query | Turns `ip -j`, `kubectl -o json` and `docker inspect` into field lookups instead of `awk` guesses | local · *filter* | read-only | [Act VIII in the wild](../networking-fundamentals/act-8-trust/in-the-wild.md) |
| `xxd` / `base64` | hex dump / — | Reads the bytes when the text view is lying to you | local · flags | read-only | [hashing](../networking-fundamentals/act-8-trust/01-hashing.md) |

## macOS companions

The lab is Linux; your laptop may not be. These appear on the acts' `in-the-wild.md` pages as the
nearest native equivalent, and they are **not** substitutes — the mechanisms differ.

| macOS tool | Linux counterpart | Where |
|---|---|---|
| `ifconfig` | `ip addr` / `ip link` | [Act II in the wild](../networking-fundamentals/act-2-two-machines/in-the-wild.md) |
| `netstat -rn` | `ip route` | [Act II in the wild](../networking-fundamentals/act-2-two-machines/in-the-wild.md) |
| `arp -a` | `ip neigh` | [Act II in the wild](../networking-fundamentals/act-2-two-machines/in-the-wild.md) |
| `pfctl` | `iptables` / `nft` | [Act V in the wild](../networking-fundamentals/act-5-kubernetes/in-the-wild.md) |
| `scutil --dns` | `/etc/resolv.conf` + `/etc/nsswitch.conf` | [Act V in the wild](../networking-fundamentals/act-5-kubernetes/in-the-wild.md) · [your own machine](../networking-fundamentals/your-own-machine.md) |
| `dscacheutil -flushcache` | (no direct equivalent — Linux has no OS-level DNS cache by default) | **not in the course** — listed because the absence of a Linux equivalent is itself worth knowing |
| `nettop` | `ss -tp` in a loop | [Act I in the wild](../networking-fundamentals/act-1-one-machine/in-the-wild.md) |

---

## The honest tally

Of the tools above, **sixteen are `roster only`**: `nstat`, `ethtool`, `devlink`, `bpftool`, `nft`,
`ipset`, `tc`, `ipvsadm`, `mtr`, `socat`, `nsenter`, `bpftrace`, `iperf3`, `pwru`, `retis`, and `host`. Several of these are things a
working network engineer reaches for weekly — `nft` is the modern replacement for the `iptables` the
course teaches in [Act IV](../networking-fundamentals/act-4-one-pretends-many/03-iptables-and-nat.md),
and `ethtool` explains an offload mystery Act II raises and never resolves.

They are listed with their gap stated rather than quietly omitted, because the alternative is a reader
who believes they have covered ground they have not.
[`JOURNEY-MAP.md`](../JOURNEY-MAP.md) records which of these are planned.

**Six of those sixteen are `netlink` tools** — `nft`, `ipset`, `tc`, `ipvsadm`, `ethtool`, `devlink`.
That is the most encouraging line on this page: they share an interface with `ip`, `ss`, `bridge` and
`conntrack`, which the course does teach, so the grammar and the failure modes transfer. A tool no
lesson runs is still *derivable* when you already know its interface.

**Two gaps this page found by classifying itself.** Adding the interface column meant placing every
tool, and placing every tool meant noticing which were not here to place:

- **`openssl` was missing entirely** — taught in nineteen lesson files across Act VIII and absent from
  the instrument panel. Now a row.
- **`ssh` is genuinely outside the course.** [`Toolbelt.md`](../Toolbelt.md) lists it under the tools it
  assumes you already have, and no lesson runs it. That is defensible for `ssh` the login shell and
  indefensible for `ssh` the networking tool: `-L`, `-R` and `-D` are port forwarding, a `socket`-family
  mechanism that competes directly with the `socat` relays this page lists, and `ProxyJump` is the
  bastion pattern every cloud network uses. **No row, because no lesson** — recorded here rather than
  papered over.

---

Next: **[by question](04-by-question.md)** — the same set, indexed by the symptom you arrived with.
