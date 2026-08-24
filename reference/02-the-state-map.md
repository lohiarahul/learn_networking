# The state map — where the kernel keeps a fact, and how to guess the path

The course reads the kernel's own files constantly — `/proc/net/tcp` alone appears in over a hundred
places — but it never draws the whole tree, because a lesson needs one file at a time.

This page is the tree. Like [the grammar](01-the-grammar.md), it is organised around the rules that let
you *derive* a path rather than remember it, with the places the rules break called out.

---

## The one fact that explains half of Acts IV–V

From `man 5 proc_net`, verbatim:

> "/proc/net is a symbolic link to the directory /proc/self/net, which contains the same files and
> directories as listed below."

and

> "these files and directories now expose information for the network namespace of which the process is
> a member."

And `man 7 network_namespaces` gives the full inventory of what a network namespace isolates, which is
worth reading once in full:

> "Network namespaces provide isolation of the system resources associated with networking: network
> devices, IPv4 and IPv6 protocol stacks, IP routing tables, firewall rules, the */proc/net* directory
> (which is a symbolic link to */proc/pid/net*), the */sys/class/net* directory, various files under
> */proc/sys/net*, port numbers (sockets), and so on."

Note **"various files under `/proc/sys/net`"**. Sysctl namespacing is genuinely uneven —
`net.ipv4.ip_forward` is per-namespace, several `net.core.*` knobs are host-wide — so there is no
blanket rule to learn here, only a per-sysctl fact to check.

Read those first two sentences together and a great deal stops being mysterious:

- `/proc/net/tcp` is **not** a global socket table. It is *this process's namespace's* socket table.
- Two `cat /proc/net/tcp` runs on the same machine can disagree completely, and both are right.
- A container "having its own network" is not a metaphor. It is this symlink resolving somewhere else.
- Reading another process's network view is therefore `cat /proc/<pid>/net/tcp` — no tool required, and
  no need to enter the namespace at all.

That last line is worth keeping: **`/proc/<pid>/net/*` is the read-only shortcut into any namespace on
the box.** It is how you look without `nsenter`, and it works when `nsenter` is unavailable.

Taught in: [namespaces](../networking-fundamentals/act-4-one-pretends-many/01-namespaces.md) ·
[ports and /proc/net/tcp](../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md)

---

## Rule: sysctl keys are `/proc/sys` paths with the dots turned into slashes

```
net.ipv4.ip_forward                    ->  /proc/sys/net/ipv4/ip_forward
net.netfilter.nf_conntrack_max         ->  /proc/sys/net/netfilter/nf_conntrack_max
net.ipv4.conf.eth0.rp_filter           ->  /proc/sys/net/ipv4/conf/eth0/rp_filter
```

It runs both ways, which is the useful part: if you can `cat` it, you can `sysctl` it, and if you know
one form you know the other. `sysctl -a | grep <word>` is then a search over every tunable on the
machine — the fastest way to find a name you half-remember.

The four top-level subtrees worth knowing by shape:

| Path | Holds |
|---|---|
| `/proc/sys/net/ipv4/` | IPv4 behaviour, including all TCP tunables (`tcp_*`) |
| `/proc/sys/net/ipv6/` | the IPv6 equivalents — **not** always the same names |
| `/proc/sys/net/core/` | family-independent socket and queue limits (`somaxconn`, `rmem_max`) |
| `/proc/sys/net/netfilter/` | conntrack sizing and timeouts |

### The `all` / `default` / `<dev>` triad, and why you can't guess its meaning

Under `/proc/sys/net/ipv4/conf/` there is a directory per interface, plus two special ones. The
kernel's own documentation:

> "`conf/default/*`: Change the interface-specific default settings. These settings would be used
> during creating new interfaces."

So **`default` changes nothing that already exists** — set it and then wonder why `eth0` didn't change,
and you have found the most common mistake in this subtree.

`all` is worse, and this is the honest limit of the whole page: **how `all` combines with the
per-interface value is defined per setting, and there is no rule to derive it.** From the kernel docs:

| Setting | Documented combination |
|---|---|
| `rp_filter` | "The max value from conf/{all,interface}/rp_filter is used" |
| `log_martians` | enabled "if at least one of conf/{all,interface}/log_martians is set to TRUE" — an OR |
| `accept_redirects` | an AND when forwarding is on, an OR when it is off |

Three settings, three different rules. You can always derive the *path*; you must always read the docs
for the *semantics*. Guessing here produces a machine that is subtly wrong rather than obviously
broken, which is the expensive kind.

Taught in: [iptables and NAT](../networking-fundamentals/act-4-one-pretends-many/03-iptables-and-nat.md)
· [conntrack](../networking-fundamentals/act-3-the-internet/02b-conntrack.md) ·
[what a container may do](../networking-fundamentals/act-10-cluster-security/01-what-a-container-may-do.md)

---

## Rule: namespace flag letters *are* the filenames

`/proc/<pid>/ns/` contains one entry per namespace type, and `nsenter`'s options map onto them 1:1.
This table makes `unshare` and `nsenter` one thing to learn instead of two:

| File in `/proc/<pid>/ns/` | `nsenter` flag | Long form | Isolates |
|---|---|---|---|
| `mnt` | `-m` | `--mount` | the mount table |
| `uts` | `-u` | `--uts` | hostname and domain name |
| `ipc` | `-i` | `--ipc` | SysV IPC, POSIX message queues |
| `net` | `-n` | `--net` | interfaces, routes, netfilter, socket tables |
| `pid` | `-p` | `--pid` | process IDs |
| `user` | `-U` | `--user` | UID/GID mappings and capabilities |
| `cgroup` | `-C` | `--cgroup` | the cgroup root |
| `time` | `-T` | `--time` | boot and monotonic clock offsets |

(`nsenter` flags quoted from `man 1 nsenter`; the same letters carry to `unshare`.)

The entries are magic symlinks whose target is a type and an inode — `net:[4026531840]`. **Two
processes are in the same namespace if and only if that inode matches**, which is the whole test, and
it is why the course compares `readlink /proc/self/ns/net` rather than trusting a tool.

Taught in: [namespaces](../networking-fundamentals/act-4-one-pretends-many/01-namespaces.md) ·
[everything is a file](../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md)

### Why `ip netns list` shows nothing on a machine full of containers

A namespace stays alive as long as *something* holds a reference to it — a running process, or a bind
mount. `ip netns add` makes the bind mount, under `/run/netns/`, and `ip netns list` is really just a
directory listing of that path. So a namespace created any other way is invisible to it, while being
perfectly real:

| Path | Who puts namespaces there | Does `ip netns list` see them? |
|---|---|---|
| `/run/netns/<name>` | `ip netns add` | **Yes** — this is the only reason it works at all |
| `/var/run/docker/netns/<id>` | Docker | **No** |
| `/run/netns` (rootful) or `$XDG_RUNTIME_DIR/netns` (rootless) | Podman / netavark | Rootful: yes |
| varies by plugin | containerd / CRI | Sometimes |

Which gives the standard trick for making Docker's namespaces visible to iproute2 — **run this on the
Docker host, not inside the lab container**, because `/var/run/docker/netns` lives in the host's mount
namespace and is not visible from inside a container at all:

```bash
# on the host
ln -s /var/run/docker/netns /var/run/netns
ip netns list
```

And the always-works alternative, needing no mount and no tool: find the container's pid and read
`/proc/<pid>/net/` directly, or enter it with `nsenter -t <pid> -n`.

---

## Rule: `/sys/class/net/<dev>/` is one file per field

Where `/proc/net/*` gives you a table, `/sys` gives you one value per file — which makes it the better
thing to script against and the better thing to cross-check a tool with.

| Path under `/sys/class/net/<dev>/` | Is | The `ip` field that reports the same thing |
|---|---|---|
| `address` | MAC address | `ip link show <dev>` → `link/ether` |
| `mtu` | MTU | `ip link` → `mtu` |
| `operstate` | `up` / `down` / `unknown` | `ip link` → `state` |
| `carrier` | 1 if the cable/link is up | `ip link` → `NO-CARRIER` flag |
| `iflink` | the peer's index, for a veth | `ip link` → `eth0@if12`, where 12 is this number |
| `master` | symlink to the bridge or bond it is enslaved to | `ip link` → `master br0` |
| `brif/` | (on a bridge) one entry per enslaved port | `bridge link show` |
| `statistics/rx_packets`, `tx_bytes`, … | per-direction counters | `ip -s link` |

The right-hand column is the point. Course pedagogy rule 4 is *mechanism before tool* — if `ip` and the
file disagree, the file wins, and this table tells you which file to check.

Taught in: [ethernet and ARP](../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) ·
[veth and bridge](../networking-fundamentals/act-4-one-pretends-many/02-veth-and-bridge.md) ·
[MTU and fragmentation](../networking-fundamentals/act-2-two-machines/03b-mtu-and-fragmentation.md)

---

## The paths this course actually reads

Grouped by what you'd be looking for. Every entry here is used by a lesson, so if a path in this section
surprises you there is a lesson that will explain it.

### Sockets and processes

| Path | Holds | Lesson |
|---|---|---|
| `/proc/net/tcp`, `/proc/net/udp` | the socket tables, hex and little-endian | [ports and /proc/net/tcp](../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md) |
| `/proc/<pid>/fd/` | one symlink per open descriptor | [the fd table](../networking-fundamentals/act-1-one-machine/01-the-fd-table.md) |
| `/proc/<pid>/fdinfo/<n>` | offset, flags and inode for one descriptor | [the fd table](../networking-fundamentals/act-1-one-machine/01-the-fd-table.md) |
| `/proc/<pid>/status` | `State:`, `CapEff:`, `Seccomp:` | [what a container may do](../networking-fundamentals/act-10-cluster-security/01-what-a-container-may-do.md) |
| `/proc/<pid>/environ` | the process's environment, NUL-separated — including secrets passed as env vars | [configuration](../networking-fundamentals/act-7-workloads/05-configuration.md) |

### Interfaces, addresses, routes

| Path | Holds | Lesson |
|---|---|---|
| `/proc/net/dev` | per-interface RX/TX counters | [loopback](../networking-fundamentals/act-1-one-machine/04-loopback.md) |
| `/proc/net/arp` | the neighbour cache, in text | [ethernet and ARP](../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| `/proc/net/route` | the main routing table, in hex | [IP and routing](../networking-fundamentals/act-2-two-machines/02-ip-and-routing.md) |
| `/proc/net/fib_trie` | the same routes as the kernel's actual trie | [IP and routing](../networking-fundamentals/act-2-two-machines/02-ip-and-routing.md) |
| `/proc/net/vlan/config` | VLAN interface → parent + tag | [VLANs](../networking-fundamentals/act-2-two-machines/01b-vlans-and-segmentation.md) |

### Flows and filtering

| Path | Holds | Lesson |
|---|---|---|
| `/proc/net/nf_conntrack` | every tracked flow, with state and timeout | [conntrack](../networking-fundamentals/act-3-the-internet/02b-conntrack.md) |
| `/proc/sys/net/netfilter/nf_conntrack_{max,count}` | table ceiling, and current occupancy | [conntrack](../networking-fundamentals/act-3-the-internet/02b-conntrack.md) |

### Limits and cgroups

| Path | Holds | Lesson |
|---|---|---|
| `/sys/fs/cgroup/memory.max`, `memory.current`, `memory.events` | the memory ceiling, usage, and OOM counts | [cgroups](../networking-fundamentals/act-4-one-pretends-many/01b-cgroups.md) |
| `/sys/fs/cgroup/cpu.max` | quota and period | [cgroups](../networking-fundamentals/act-4-one-pretends-many/01b-cgroups.md) |
| `/proc/<pid>/cgroup` | which cgroup a process is in | [cgroups](../networking-fundamentals/act-4-one-pretends-many/01b-cgroups.md) |

### Name resolution

| Path | Holds | Lesson |
|---|---|---|
| `/etc/resolv.conf` | nameservers, `search` domains, and `ndots` — the number of dots a name must contain before the resolver tries it as-is instead of appending each `search` domain first. Kubernetes sets it to 5, which is why one lookup inside a Pod can become five | [DNS](../networking-fundamentals/act-2-two-machines/04-dns.md) · [CoreDNS](../networking-fundamentals/act-5-kubernetes/04-coredns.md) |
| `/etc/nsswitch.conf` | *whether DNS is consulted at all*, and in what order — **on glibc**. See the warning below | [DNS](../networking-fundamentals/act-2-two-machines/04-dns.md) |
| `/etc/hosts` | the file that beats DNS | [DNS](../networking-fundamentals/act-2-two-machines/04-dns.md) |

`/etc/nsswitch.conf` is the one people forget, and it explains the classic "`dig` works but the
application can't resolve". An application does not speak DNS; it calls `getaddrinfo()`, which goes
through **NSS** — the Name Service Switch, glibc's pluggable lookup layer, whose order this file sets.
`dig` skips all of that and talks to the nameserver directly, which is exactly why the two can disagree.

> **⚠️ But not in this lab.** NSS is a **glibc** mechanism. The course's lab image is Alpine, which uses
> **musl**, and musl implements no NSS at all — `/etc/nsswitch.conf` is present and completely inert,
> with files-then-DNS hardcoded. Delete `files` from that file inside `netshoot` and `/etc/hosts` still
> wins. So the model above is correct on the glibc hosts you will actually operate, and unverifiable in
> the container you would naturally test it in. Test it on a Debian or RHEL box.

### Cluster state on a node

| Path | Holds | Lesson |
|---|---|---|
| `/etc/kubernetes/manifests/` | static Pod specs — the control plane itself | [static pods](../networking-fundamentals/act-6-control-plane/02-static-pods.md) |
| `/etc/kubernetes/pki/` | the cluster's CAs and certificates | [the cluster's own PKI](../networking-fundamentals/act-6-control-plane/04-the-clusters-own-pki.md) |
| `/var/lib/etcd/` | the entire cluster's data | [etcd backup and restore](../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) |
| `/var/lib/kubelet/config.yaml` | the kubelet's own configuration | [the API server is a filesystem](../networking-fundamentals/act-6-control-plane/01-the-api-server-is-a-filesystem.md) |
| `/var/run/secrets/kubernetes.io/serviceaccount/` | the projected token every Pod gets | [the doors left open](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) |
| `/sys/kernel/btf/vmlinux` | the kernel's own type info, which is what makes portable eBPF possible | [seeing it happen](../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md) |

---

## Territory the course does not visit

In the map, flagged as untaught, because a reference that quietly implies coverage is worse than one with
gaps. These are real and useful; no lesson runs them. (`/run/netns` belongs in this category too — no
lesson touches it — but it is load-bearing enough that it is explained in full above rather than listed
here.)

| Path | What it would give you |
|---|---|
| `/proc/net/tcp6`, `/proc/net/udp6` | the IPv6 socket tables; separate files, same format |
| `/proc/net/unix` | Unix-domain sockets, which is where most local IPC actually is |
| `/proc/net/snmp`, `/proc/net/netstat` | protocol-level counters — `TCPSynRetrans`, `TCPLostRetransmit`, `ListenDrops`, `ListenOverflows`. `nstat` reads these |
| `/proc/net/softnet_stat` | per-CPU `processed` / `dropped` / `time_squeeze` — **the only place `netdev_budget` exhaustion shows up** |
| `/proc/net/dev_snmp6/<dev>` | per-interface IPv6 counters. Has no man page, and is the only sane source for per-interface IPv6 drops |
| `/proc/net/sockstat` | aggregate socket counts including orphans and `tw` — a cheap health signal |
| `/proc/self/mountinfo` | the mount table with propagation flags, which `mount` output omits |
| `/sys/fs/bpf/` | the bpffs, where pinned eBPF programs and maps live — how a CNI's eBPF state survives an agent restart |
| `/sys/kernel/tracing/` | tracefs — the tracepoints and kprobes `bpftrace` and `perf` build on. **Note the path:** tracefs has been its own filesystem since Linux 4.1 and this is its canonical mount; `/sys/kernel/debug/tracing` is a backward-compatibility path that most tutorials still show and that some kernels no longer provide at all. Expect the directory to be **empty** until tracefs is mounted on it — in a privileged container, `mount -t tracefs nodev /sys/kernel/tracing` populates it |

`/proc/net/snmp` is the highest-value one missing: "is this a network problem or an application
problem" is very often answered by a retransmit or listen-overflow counter, and nothing in the course
reads them.

### One trap worth naming: `net_cls` does not exist in cgroup v2

Every current distro boots cgroup v2 unified, and `cgroups(7)` is explicit that **`net_cls` and
`net_prio` were never ported to it** — "there is no direct equivalent of the net_cls and net_prio
controllers from cgroups version 1". So any guide telling you to write a class id into
`net_cls.classid` is describing a file that is not on your machine.

What replaced it, and where to look instead:

- **cgroup-BPF programs** attached to a cgroup directory (`CGROUP_SKB`, `CGROUP_SOCK`,
  `CGROUP_SOCK_ADDR`, `CGROUP_SOCKOPT`). Inventory them with `bpftool cgroup tree` — and note that this
  is exactly where Cilium's socket-level load balancing lives.
- **nftables** matching on `socket cgroupv2 level N`.

---

## Where `/proc` is the wrong file to trust

"Read the kernel's own file" is the course's best habit and it has a limit worth knowing.

`/proc/net/*` is an old, text-formatted interface that predates netlink, and the kernel says so
itself. From the documentation for `/proc/net/tcp`, verbatim:

> "Note that these interfaces are deprecated in favor of tcp_diag."

That is not a stylistic preference. The text formats have fixed field widths and no way to express
attributes added later, so a tool reading netlink can legitimately show you *more* than the file does:

| Legacy file | What it cannot tell you | The netlink path that can |
|---|---|---|
| `/proc/net/tcp`, `tcp6`, `udp` | complete TIME_WAIT data, cgroup or owning-thread attribution; expensive to read at scale | `NETLINK_SOCK_DIAG`, i.e. `ss` |
| `/proc/net/route` | anything outside the main table, and anything IPv6 — no policy routing, no multipath detail | RTNETLINK, i.e. `ip route show table all` |
| `/proc/net/dev` | per-queue and driver-private counters, where many drops appear and nowhere else | `ethtool -S` |
| `/proc/net/nf_conntrack` | anything, if `CONFIG_NF_CONNTRACK_PROCFS` is off — which it is on some distros | ctnetlink, i.e. `conntrack -L` |

There is a related lesson in files that are simply *absent*. `/proc/net/ip_tables_names` only exists
once the legacy xtables modules load, and RHEL 10 does not ship the `ip_tables` module at all — so on
that host the file is missing and the firewall is working fine. **"The file is not there" is not the
same finding as "the feature is broken."**

So the rule is not "the file always wins" — it is:

- **the file wins over your memory**, always; and
- **when the file and a netlink tool disagree, the tool is more likely to be complete**, and the
  disagreement itself is the interesting finding worth chasing rather than resolving by preference.

---

Next: **[the index](03-the-index.md)** — one row per tool, and which of them the course actually
teaches. Or **[derive it](06-derive-it.md)** to practise turning these rules into paths under time
pressure.
