# The index — one row per instrument

Alphabetical, because that is what a lookup wants. If you have a symptom rather than a tool name, start
at **[by question](../04-by-question.md)** instead. If you want to *derive* a command rather than find one,
**[the grammar](../01-the-grammar.md)** is the page.

**How to read the columns.**

- **The one thing only it shows you** — why this tool exists when the others do. If two rows have the
  same answer, one of them is redundant and should be cut.
- **Speaks** — two tokens: *which kernel interface the tool addresses*, then *its grammar*. The
  interface is the one that decides what the tool can possibly know; the grammar is the one that lets you
  guess a subcommand. `obj-verb` = noun first; `verb-obj` = verb first; `flags` = a conventional getopt
  tool; *filter* = it has an expression language of its own. The eight interfaces are defined below, each
  by a syscall you can see in `strace` — so this column is measurable, not a matter of taste.
- **The tool** — a link when the tool has a page, and a bare name when it does not. Four rows are bare
  (`tc`, `ipvsadm`, `ipset`, `devlink`), and that is a statement rather than an omission: see
  [the honest tally](#the-honest-tally).
- **In the course** — a link to the lesson that runs it, or **roster only**. `roster only` means
  [`Toolbelt.md`](../../Toolbelt.md) names it and **no lesson runs it** — it is here as territory, not as
  something you have been taught. Verified by grep against the lesson sources.

Four columns, because a table you have to scroll sideways is not *"the whole thing on one screen"*. Two
facts that used to be columns are now rows on each tool's own page: what the name expands to, and whether
the tool can **change state** — the second one is a check you make before typing a command, not something
you scan a roster for. What streams is the exception, and it has its own compartment below.

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

`13 + 14 + 11 + 7 + 7 + 4 + 11 + 5 = 72` — every row on this page, each in exactly one interface.

> ### The unit is the *invocation*, not the binary
>
> Three rows carry a footnote because the same executable speaks two interfaces depending on how you
> call it, and this is not pedantry — it is the mechanism behind three separate traps in this course:
>
> | | Splits how | Why it matters |
> |---|---|---|
> | **†** `iptables` | `netlink` on the nf_tables backend · `setsockopt` on legacy | **`iptables -V` tells you which.** Measured: `iptables -t nat -L` opens `NETLINK_NETFILTER` — on a current box the tool this course teaches *is* the tool it lists as `roster only` |
> | **‡** `nmap` | `packet` for `-sS` · `socket` for the `-sT` default | The half-open scan needs raw packets; the default scan is an ordinary `connect()` your application logs |
> | **‖** `ip netns` | `nsapi` to create and enter · `netlink` to list nsids | `ip netns add` is `unshare` plus a bind mount under `/run/netns`. **This is exactly why it cannot see Docker's namespaces** — see [`nsapi`](nsapi/README.md#rule-the-flag-letters-are-the-filenames) |
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

## Six to stop reaching for, and two to start

Six tools here are on the roster because *other people's runbooks* are full of them, not because you
should type them. Two are here because they are new enough that you install them deliberately. Every
verdict is a measurement, stated on the tool's own page — and every superseded row names a successor,
because "deprecated" without one is a complaint rather than advice.

| Reach for this | Instead of | What the swap costs |
|---|---|---|
| [`ss`](netlink/ss.md) | [`netstat`](procfs/netstat.md) | **drop-in** — same flag letters, so `netstat -tulnp` becomes `ss -tulnp` and nothing else changes |
| [`ip neigh`](netlink/ip.md) | [`arp`](procfs/arp.md) | a minute's relearning — `arp` cannot show an IPv6 neighbour at all, nor an entry's NUD state |
| [`nft`](netlink/nft.md) | [`iptables`](netlink/iptables.md) · [`iptables-save`](netlink/iptables-save.md) | a rewrite — **but learn `iptables` first anyway**, because every existing cluster is written in it |
| [`dig`](socket/dig.md) | [`nslookup`](socket/nslookup.md) | a rewrite — different output shape, and `nslookup` has no mode that shows you the DNS *message* |
| [`strace`](probe/strace.md) · [`bpftrace`](probe/bpftrace.md) | [`ltrace`](probe/ltrace.md) | a rewrite — and `ltrace` does not even run in this lab image |

The **drop-in** row is the only one you can act on without thinking. The other three cost real work,
which is why they say so: a page that tells you to stop using something without telling you what
stopping costs is a page you will ignore.

And the two bets — both eBPF packet tracers, both answering the one question no other interface can,
*which kernel function dropped this packet*:

| New | Since | Why it is worth installing |
|---|---|---|
| [`pwru`](probe/pwru.md) | 2021 | Cilium's, and the tool Cilium support asks you to run |
| [`retis`](probe/retis.md) | 2023 | Red Hat's, with a collect-then-analyse split so you can capture on a broken node and reason somewhere else |

Two independent vendors building the same tool is the signal worth reading here. Neither is packaged by
a distribution, and neither is in `netlab:latest` — the tool pages say so rather than letting the shell
tell you.

## Reading the kernel's network state

| Tool | The one thing only it shows you | Speaks | In the course |
|---|---|---|---|
| [`ip`](netlink/ip.md) | Everything netlink's route family knows: links, addresses, routes, neighbours, rules, namespaces. `-j` gives it to you as JSON | netlink · obj-verb, 30 objects | [ethernet and ARP](../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| [`ss`](netlink/ss.md) | Per-socket TCP internals: RTT, cwnd, retransmits (`-i`) and buffer accounting (`-m`). Also `--cgroup`, which attributes a socket to its cgroup — i.e. **to a container, without touching the container runtime** — and `-E` to stream sockets as they are destroyed, catching short-lived connections a polling loop misses | netlink · flags + *filter* | [ports and /proc/net/tcp](../../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md) |
| [`netstat`](procfs/netstat.md) | Nothing `ss` doesn't — that is the honest answer, and the reason it is marked superseded. On the roster because every legacy box and every old runbook has it; the evidence is on its page | procfs · flags | [taught as `ss`'s rival](../../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md) |
| [`lsof`](procfs/lsof.md) | The join from a socket back to *which process and which fd* owns it, across every process at once | procfs · flags | [the fd table](../../networking-fundamentals/act-1-one-machine/01-the-fd-table.md) |
| [`bridge`](netlink/bridge.md) | A bridge's forwarding database (`fdb`), its VLAN filtering table, and per-port state. `ip` creates bridges; only this inspects them | netlink · obj-verb | [veth and bridge](../../networking-fundamentals/act-4-one-pretends-many/02-veth-and-bridge.md) |
| [`conntrack`](netlink/conntrack.md) | The kernel's flow table as a live stream (`-E`), which is the only way to watch NAT decisions happen | netlink · flags | [conntrack](../../networking-fundamentals/act-3-the-internet/02b-conntrack.md) |
| [`sysctl`](procfs/sysctl.md) | Every kernel tunable by name, and `-a` makes it searchable | procfs · flags | [conntrack](../../networking-fundamentals/act-3-the-internet/02b-conntrack.md) |
| [`nstat`](procfs/nstat.md) | Protocol counters from `/proc/net/snmp` and `netstat`, *as deltas since last call* — retransmits, listen overflows, drops | procfs · flags | **roster only** |
| [`ethtool`](netlink/ethtool.md) | The NIC's own truth: link speed, ring sizes, offloads (`-k`), and per-queue hardware counters (`-S`). Explains why `tcpdump` shows a 64 KB "packet" on a 1500-byte link | netlink · flags | **roster only** |
| `devlink` | Hardware-level device and port config below what `ip link` can reach | netlink · obj-verb | **roster only** |
| [`bpftool`](probe/bpftool.md) | What eBPF programs and maps are loaded and where they are attached. `bpftool net show` covers xdp/tc/tcx per device; **`bpftool cgroup tree` covers the cgroup hooks, which is where Cilium's socket-level load balancing actually lives.** The inventory command for an eBPF datapath, with no substitute | probe · obj-verb | **roster only** |

## Filtering, NAT and traffic shaping

| Tool | The one thing only it shows you | Speaks | In the course |
|---|---|---|---|
| [`iptables`](netlink/iptables.md) | The legacy rule syntax that most of the internet's documentation, and `kube-proxy`'s default mode, still speaks. **Run `iptables -V` first:** since 1.8 the same CLI sits over two different kernel backends and prints either `(nf_tables)` or `(legacy)`. Never mix the legacy and nft tools — both subsystems become active and the evaluation order between them is undefined | netlink&nbsp;† · flags (`-t -A -m -j`) | [iptables and NAT](../../networking-fundamentals/act-4-one-pretends-many/03-iptables-and-nat.md) |
| [`iptables-save`](netlink/iptables-save.md) | The whole ruleset in one atomic, diffable text dump — the only sane way to read a large ruleset | netlink&nbsp;† · flags | [services](../../networking-fundamentals/act-5-kubernetes/03-services.md) |
| [`nft`](netlink/nft.md) | One tool and one grammar for IPv4, IPv6, ARP and bridge (the `inet` family), plus the sets and maps that iptables needed `ipset` for. In-kernel since 3.13; netfilter's own wiki has called the xtables tools legacy since 2018, RHEL 10 no longer ships the legacy `ip_tables` module at all, and Docker Engine 29 has an experimental native nftables backend it intends to make the default | netlink · verb-obj | [iptables and NAT](../../networking-fundamentals/act-4-one-pretends-many/03-iptables-and-nat.md) |
| `ipset` | Hash sets of addresses/ports that iptables can match in one step instead of rule-by-rule. Now largely historical: nftables has native sets and maps, and `ipset` is unmaintained and slated for removal on RHEL | netlink · verb-obj | **roster only** |
| `tc` | Queueing, rate limits, and — via `netem` — deliberately injected loss, delay, reordering and duplication. **The only way to *reproduce* a bad network**, and `netem` has no eBPF equivalent. eBPF did not replace `tc`; it replaced one thing that used to hang off it, the packet classifier. Modern eBPF datapath programs attach straight to a device's ingress and egress (an interface called TCX, since kernel 6.6) instead of hanging off one of `tc`'s queueing disciplines | netlink · obj-verb (qdisc/class/filter) | **roster only** |
| `ipvsadm` | The IPVS connection and destination tables (`/proc/net/ip_vs`, `ip_vs_conn`) when `kube-proxy` runs in IPVS mode — still the right way to read a cluster that inherited it. Note the split: **IPVS in Linux is not deprecated; `kube-proxy`'s IPVS *mode* is** — deprecated in Kubernetes 1.35, with removal targeted at 1.43. `kube-proxy`'s nftables mode went GA in 1.33, though iptables remains the default | netlink · flags | **roster only** |

## Capture and packet-level inspection

| Tool | The one thing only it shows you | Speaks | In the course |
|---|---|---|---|
| [`tcpdump`](packet/tcpdump.md) | Bytes actually on the wire, with a compositional filter language and `-w` to a `.pcap` you can open elsewhere | packet · flags + *libpcap filter* | [ICMP and UDP](../../networking-fundamentals/act-2-two-machines/03-icmp-and-udp.md) |
| [`tshark`](packet/tshark.md) | The same bytes `tcpdump` captures, but *dissected* — Wireshark's protocol decoders, so you read named fields instead of hex | packet · flags + *filter* | [Act II in the wild](../../networking-fundamentals/act-2-two-machines/in-the-wild.md) |
| [`scapy`](packet/scapy.md) | Packets you *construct*: become the protocol instead of watching it. The active counterpart to `tcpdump` | packet · Python library | [ethernet and ARP](../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| [`pwru`](probe/pwru.md) | Which **kernel function** your packet passed through, and which one dropped it — kprobes on every `skb`-taking function. Structurally impossible with `tcpdump`, and the tool Cilium support asks you to run | probe · flags + *filter* | **roster only** |
| [`retis`](probe/retis.md) | libpcap filters compiled to eBPF and inlined at *arbitrary probe points*, correlating kernel packet-buffer (`skb`) drops, netfilter verdicts and conntrack against one packet | probe · verb-obj | **roster only** |
| [`nmap`](packet/nmap.md) | What a *scanner* sees, including the half-open SYN scan that never completes a handshake so your application never logs it | packet&nbsp;‡ · flags | [TCP states and the SYN scan](../../networking-fundamentals/act-1-one-machine/05b-tcp-states-and-the-syn-scan.md) |

## Reachability and paths

| Tool | The one thing only it shows you | Speaks | In the course |
|---|---|---|---|
| [`ping`](socket/ping.md) | Whether ICMP echo returns, and the RTT distribution | socket&nbsp;§ · flags | [loopback](../../networking-fundamentals/act-1-one-machine/04-loopback.md) |
| [`arping`](packet/arping.md) | Reachability at **layer 2**, bypassing IP entirely — proves the wire works when routing does not | packet · flags | [ethernet and ARP](../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| [`traceroute`](packet/traceroute.md) | The hop list, by walking TTL upward | packet · flags | [ICMP and UDP](../../networking-fundamentals/act-2-two-machines/03-icmp-and-udp.md) |
| [`mtr`](packet/mtr.md) | Continuous per-hop loss and latency, which is how you tell "one bad hop" from "the whole path is bad" | packet · flags | **roster only** |
| [`arp`](procfs/arp.md) | Nothing `ip neigh` doesn't. Recognise it in old runbooks | procfs · flags | [taught as `ip neigh`'s rival](../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |

## Name resolution

| Tool | The one thing only it shows you | Speaks | In the course |
|---|---|---|---|
| [`dig`](socket/dig.md) | The full DNS response — flags, authority and additional sections, TTLs. Talks to the resolver directly, **skipping NSS** | socket · `@server name type` + `+opts` | [DNS](../../networking-fundamentals/act-2-two-machines/04-dns.md) |
| [`drill`](socket/drill.md) | The full DNS response like `dig`, but DNSSEC-aware — and it ships in `netshoot`, where `dig` sometimes doesn't | socket · flags | [Act IV in the wild](../../networking-fundamentals/act-4-one-pretends-many/in-the-wild.md) |
| [`host`](socket/host.md) | A one-line answer, which is what you want inside a loop | socket · flags | **roster only** — the word appears in the lessons only as prose ("host bits", an Ingress `host` rule); no lesson runs the command |
| [`nslookup`](socket/nslookup.md) | Nothing `dig`, `drill` or `host` don't, but it is the one present on hosts with nothing else installed | socket · interactive | [policy shapes](../../networking-fundamentals/act-5-kubernetes/07b-policy-shapes.md) |
| [`getent hosts`](socket/getent-hosts.md) | **What the application will actually get** — it resolves the way an application does, through glibc's Name Service Switch (`/etc/nsswitch.conf`, then `/etc/hosts`, then DNS), rather than talking to a nameserver directly. The tool that resolves "`dig` works but the app can't" | socket&nbsp;¶ · `getent <db> <key>` | [Act II diagnose](../../networking-fundamentals/act-2-two-machines/diagnose.md) |

## Sockets and syscalls

| Tool | The one thing only it shows you | Speaks | In the course |
|---|---|---|---|
| [`nc`](socket/nc.md) | A raw TCP/UDP endpoint you drive by hand — the smallest possible client or server | socket · flags | [the TCP handshake](../../networking-fundamentals/act-3-the-internet/01-tcp-handshake.md) |
| [`socat`](socket/socat.md) | `nc` with every socket type on both sides: TLS, Unix sockets, PTYs, and bidirectional relays between any two | socket · `addr1 addr2` | **roster only** |
| [`curl`](socket/curl.md) | Every byte of an HTTP(S) exchange with `-v`, plus timing breakdowns and protocol selection (`--http3`) | socket · flags | [HTTP](../../networking-fundamentals/act-3-the-internet/04-http.md) |
| [`openssl`](socket/openssl.md) | Every cryptographic primitive as a separate command (`dgst`, `enc`, `genpkey`, `x509`, `verify`) **and** `s_client`, which opens a TLS connection by hand so you read the handshake instead of trusting it. The only tool here that shows you a certificate chain as the peer actually presented it | socket&nbsp;⁂ · verb-obj | [TLS opened](../../networking-fundamentals/act-8-trust/06-tls-opened.md) |
| [`strace`](probe/strace.md) | The exact syscalls a process makes, with arguments and return values — and it stops the world to do it | probe · `-e trace=…` | [minihttp](../../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) |
| [`ltrace`](probe/ltrace.md) | The calls `strace` shows, one layer up: libc calls such as `getaddrinfo` rather than the syscalls underneath them | probe · flags | [minihttp](../../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) |
| [`bpftrace`](probe/bpftrace.md) | Kernel and userspace probes at near-zero overhead, on a live production box, without stopping anything. `strace`'s successor | probe · its own language | **roster only** |
| [`iperf3`](socket/iperf3.md) | Achievable throughput between two points, which no passive tool can tell you | socket · flags | **roster only** |
| [`ulimit`](procfs/ulimit.md) / `prlimit` | The descriptor ceiling that quietly breaks busy servers — `prlimit` reads it on an *already-running* process | procfs · shell builtin / flags | [minihttp](../../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) |

## Namespaces, cgroups, capabilities

| Tool | The one thing only it shows you | Speaks | In the course |
|---|---|---|---|
| [`ip netns`](nsapi/ip-netns.md) | Named network namespaces, created as bind mounts under `/run/netns` — which is why it cannot see Docker's | nsapi&nbsp;‖ · obj-verb | [namespaces](../../networking-fundamentals/act-4-one-pretends-many/01-namespaces.md) |
| [`unshare`](nsapi/unshare.md) | A new namespace of any type, created *around a new process* — the mechanism `docker run` performs for you | nsapi · flags (`-m -u -i -n -p -U -C -T`) | [the kernel says no](../../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md) |
| [`nsenter`](nsapi/nsenter.md) | Entry into an *existing* process's namespaces — the mechanism under `docker exec` and `kubectl exec`, and the way into a container with no shell of its own | nsapi · same flag letters as `unshare` | **roster only** *(named in prose, never run)* |
| [`capsh`](procfs/capsh.md) | Which Linux capabilities a process actually holds, decoded from `/proc/<pid>/status`'s `CapEff` bitmask | procfs · flags | [what a container may do](../../networking-fundamentals/act-10-cluster-security/01-what-a-container-may-do.md) |
| [`getpcaps`](procfs/getpcaps.md) | The capability set `capsh --print` decodes, but for a **running PID** and in one line — no need to start a process inside it | procfs · `getpcaps <pid>` | [Act X diagnose](../../networking-fundamentals/act-10-cluster-security/diagnose.md) |
| [`apparmor_parser`](procfs/apparmor-parser.md) | Whether a profile loads, and in what mode — the difference between "enforcing" and "you thought it was enforcing" | procfs · flags | [the kernel says no](../../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md) |
| [`runc`](nsapi/runc.md) | The OCI runtime that actually creates the namespaces and cgroups. Below every higher-level tool | nsapi · verb-obj | [the kernel says no](../../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md) |

## Container and cluster runtimes

| Tool | The one thing only it shows you | Speaks | In the course |
|---|---|---|---|
| [`docker`](httpapi/docker.md) | The developer-facing view, and `docker network inspect` — Act IV's bridge and veth pairs, printed as JSON | httpapi · obj-verb | [the fd table](../../networking-fundamentals/act-1-one-machine/01-the-fd-table.md) |
| [`crictl`](httpapi/crictl.md) | The node's container runtime *directly* — the only view left when the API server is down and `kubectl` is useless | httpapi · verb-obj | [static pods](../../networking-fundamentals/act-6-control-plane/02-static-pods.md) |
| [`kubectl`](httpapi/kubectl.md) | The API server's whole object graph, and `explain` makes the schema self-describing | httpapi · verb-obj | [pod networking](../../networking-fundamentals/act-5-kubernetes/02-pod-networking.md) |
| [`kind`](httpapi/kind.md) | A real multi-node cluster on one machine, where every node is a container you can `docker exec` into | httpapi · verb-obj | [the lab with kind](../../networking-fundamentals/act-5-kubernetes/01-lab-with-kind.md) |
| [`kubeadm`](httpapi/kubeadm.md) | What the control plane's own certificates and version skew actually are, and the upgrade plan | httpapi · verb-obj | [upgrades and version skew](../../networking-fundamentals/act-6-control-plane/06-upgrades-and-version-skew.md) |
| [`etcdctl`](httpapi/etcdctl.md) | The cluster's stored state as raw keys — the layer beneath every Kubernetes object | httpapi · verb-obj | [etcd backup and restore](../../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) |
| [`etcdutl`](local/etcdutl.md) | Offline snapshot operations (`snapshot restore`) that need no running etcd | local · verb-obj | [etcd backup and restore](../../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) |
| [`helm`](httpapi/helm.md) | What a chart *renders to* before it is applied (`template`) — and, in `crds/`, the one directory it will not render at all | httpapi · verb-obj | [shipping a set of objects](../../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) · [when the chart is not yours](../../networking-fundamentals/act-7-workloads/08c-when-the-chart-is-not-yours.md) |
| [`kustomize`](local/kustomize.md) | The overlay-resolved manifests `helm template` would give you, with no templating language at all | local · verb-obj | [shipping a set of objects](../../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) |
| [`cilium`](httpapi/cilium.md) | An eBPF datapath's own view: policy verdicts, identities, and its BPF maps | httpapi · verb-obj | [encryption between Pods](../../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md) |
| [`wg`](netlink/wg.md) | The live tunnel state — peers, handshakes, keys — under Cilium's or anyone else's encryption | netlink · verb-obj | [encryption between Pods](../../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md) |

## Supply chain and runtime security

| Tool | The one thing only it shows you | Speaks | In the course |
|---|---|---|---|
| [`trivy`](httpapi/trivy.md) | Known vulnerabilities and an SBOM for an image you are about to ship | httpapi · verb-obj | [what you shipped](../../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) |
| [`cosign`](httpapi/cosign.md) | Whether an image is signed *by a key you trust* — and the trap that any attacker can sign with theirs | httpapi · verb-obj | [who says so](../../networking-fundamentals/act-10-cluster-security/08b-who-says-so.md) |
| [`crane`](httpapi/crane.md) | A registry's raw content: digests, manifests, layers, without pulling the image | httpapi · verb-obj | [what you shipped](../../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) |
| [`kube-bench`](local/kube-bench.md) | The cluster's own config scored against the CIS benchmark, file by file | local · flags | [the doors left open](../../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) |
| [`falco`](probe/falco.md) | Syscall-level events *as they happen* — the runtime half that no scanner can give you | probe · rules + flags | [seeing it happen](../../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md) |

## General-purpose, used here to read kernel state

| Tool | Why it is in a networking reference | Speaks | In the course |
|---|---|---|---|
| [`cat`](procfs/cat.md) | The primary interface to `/proc` and `/sys`. Most of this course is `cat` | procfs · flags | throughout |
| [`stat`](procfs/stat.md) | Proves a `/proc` file reports `Size: 0` and still has content — the contradiction that makes "everything is a file" mean something | procfs · flags | [everything is a file](../../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) |
| [`readlink`](procfs/readlink.md) | Reads a magic symlink's *computed* target — `net:[4026531840]`, the namespace identity test | procfs · flags | [everything is a file](../../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) |
| [`mount`](procfs/mount.md) / `findmnt` | Which filesystems are grafted where; `findmnt` draws it as a tree with propagation flags | procfs · flags | [everything is a file](../../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) |
| [`pgrep`](procfs/pgrep.md) | PID lookup by name, so `/proc/<pid>/…` paths can be built in one line | procfs · flags | [the socket object](../../networking-fundamentals/act-1-one-machine/02-the-socket-object.md) |
| [`jq`](local/jq.md) | Turns `ip -j`, `kubectl -o json` and `docker inspect` into field lookups instead of `awk` guesses | local · *filter* | [Act VIII in the wild](../../networking-fundamentals/act-8-trust/in-the-wild.md) |
| [`xxd`](local/xxd.md) / `base64` | Reads the bytes when the text view is lying to you | local · flags | [hashing](../../networking-fundamentals/act-8-trust/01-hashing.md) |

## If your laptop is not Linux

`ifconfig`, `netstat -rn`, `pfctl`, `scutil --dns`, `nettop` — the acts' **`in-the-wild.md`** pages name
the nearest macOS equivalent where each mechanism comes up, which is where it belongs, because these are
not substitutes and the interesting part is always *how* the mechanism differs:
[Act I](../../networking-fundamentals/act-1-one-machine/in-the-wild.md) ·
[Act II](../../networking-fundamentals/act-2-two-machines/in-the-wild.md) ·
[Act V](../../networking-fundamentals/act-5-kubernetes/in-the-wild.md) ·
[your own machine](../../networking-fundamentals/your-own-machine.md).

The one worth knowing in advance is the gap: **Linux has no OS-level DNS cache by default**, so
`dscacheutil -flushcache` has no counterpart to look for.

---

## The honest tally

**Fifteen rows are `roster only`** — `nstat`, `ethtool`, `devlink`, `bpftool`, `ipset`, `tc`,
`ipvsadm`, `mtr`, `socat`, `nsenter`, `bpftrace`, `iperf3`, `pwru`, `retis`, `host`. They are here with the
gap stated rather than quietly left out, because a reference that lets you believe the course covered
something it didn't is worse than one with holes. [`JOURNEY-MAP.md`](../../JOURNEY-MAP.md) records which
are planned.

**Five of the fifteen speak `netlink`** — `ipset`, `tc`, `ipvsadm`, `ethtool`, `devlink` — which is
the encouraging half. They share an interface with the `ip`, `ss`, `bridge` and `conntrack` the course does
teach, so the grammar and the failure modes transfer: a tool no lesson runs is still *derivable* once you
know its interface.

**And four of those five are rows and nothing more.** `tc`, `ipvsadm`, `ipset` and `devlink` have no page,
because a page for them was mostly furniture: a facet table whose blind-spot row is the one every netlink
tool shares, and a *"4 commands, grouped by what you are trying to find out"* preamble over four commands
you can derive from [the grammar](../01-the-grammar.md) once you know the interface is `netlink` and the
shape is `obj-verb`. `devlink` is not even installed in the lab image and `ipset` is unmaintained and
slated for removal on RHEL, so a reader following a link to either was being sent somewhere for no reason.
The sentence in the row above **is** the entry. What did not survive derivation moved to where a reader
actually arrives — holding a symptom, not a name: `tc -s qdisc` and `netem` are under
[*"it's slow, but nothing is broken"*](../04-by-question.md#its-slow-but-nothing-is-broken), the IPVS
connection table is under [*"it works from the node but not from the Pod"*](../04-by-question.md#it-works-from-the-node-but-not-from-the-pod),
and `tc monitor` / `devlink monitor` are in [`netlink`](netlink/README.md#what-streams-here) with the other five streamers.

**One gap has no row at all.** `ssh` is in [`Toolbelt.md`](../../Toolbelt.md) as assumed knowledge and no
lesson runs it — defensible for `ssh` the login shell, indefensible for `ssh` the networking tool, since
`-L`, `-R` and `-D` are `socket`-family port forwarding competing directly with the `socat` relays above,
and `ProxyJump` is the bastion pattern every cloud network uses. Recorded here rather than papered over.

---

Next: **[by question](../04-by-question.md)** — the same set, indexed by the symptom you arrived with.
