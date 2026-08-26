# `procfs` — the kernel as files

**What you see in `strace`:** `open()` / `openat()` on a path under `/proc` or `/sys`

Fourteen tools, and every one of them is a formatter over a file you could read yourself. That is the
useful thing about this interface: there is no privileged channel, so `cat` is always a valid
substitute, and when a tool and the file disagree, **the file wins**.

[`cat`](cat.md) · [`stat`](stat.md) · [`readlink`](readlink.md) ·
[`netstat`](netstat.md) · [`nstat`](nstat.md) · [`lsof`](lsof.md) ·
[`sysctl`](sysctl.md) · [`pgrep`](pgrep.md) · [`arp`](arp.md) ·
[`capsh`](capsh.md) · [`getpcaps`](getpcaps.md) ·
[`apparmor_parser`](apparmor-parser.md) · [`mount`](mount.md) ·
[`ulimit`](ulimit.md)

---

## The one fact that explains half of Acts IV–V

**`/proc/net` is per network namespace.** Two processes reading the same path get different content if
they are in different namespaces. `/proc/<pid>/net/` is *that pid's* view — which is the always-works
way into a container's networking without entering it at all:

```bash
cat /proc/$(docker inspect -f '{{.State.Pid}}' <c>)/net/tcp
```

No `nsenter`, no tool inside the container, no cooperation from the runtime.

---

## Rule: `sysctl` keys are `/proc/sys` paths with the dots turned into slashes

```
net.ipv4.ip_forward                ->  /proc/sys/net/ipv4/ip_forward
net.netfilter.nf_conntrack_max     ->  /proc/sys/net/netfilter/nf_conntrack_max
net.ipv4.conf.eth0.rp_filter       ->  /proc/sys/net/ipv4/conf/eth0/rp_filter
```

It runs both ways, which is the useful part: if you can `cat` it you can `sysctl` it, and knowing one
form gives you the other. `sysctl -a | grep <word>` is then a search over every tunable on the machine.

| Subtree | Holds |
|---|---|
| `/proc/sys/net/ipv4/` | IPv4 behaviour, including all TCP tunables (`tcp_*`) |
| `/proc/sys/net/ipv6/` | the IPv6 equivalents — **not** always the same names |
| `/proc/sys/net/core/` | family-independent socket and queue limits (`somaxconn`, `rmem_max`) |
| `/proc/sys/net/netfilter/` | conntrack sizing and timeouts |

### The `all` / `default` / `<dev>` triad, and why you cannot guess its meaning

Under `/proc/sys/net/ipv4/conf/` there is a directory per interface plus two special ones. From the
kernel's own documentation:

> "`conf/default/*`: Change the interface-specific default settings. These settings would be used
> during creating new interfaces."

So **`default` changes nothing that already exists.** Set it, then wonder why `eth0` did not change,
and you have found the most common mistake in this subtree.

`all` is worse, and this is the honest limit of the rule: **how `all` combines with the per-interface
value is defined per setting, and there is no way to derive it.**

| Setting | Documented combination |
|---|---|
| `rp_filter` | "The max value from conf/{all,interface}/rp_filter is used" |
| `log_martians` | set if *at least one* of `conf/{all,interface}` is true — an OR |
| `accept_redirects` | an AND when forwarding is on, an OR when it is off |

Three settings, three different rules. You can always derive the *path*; you must always read the docs
for the *semantics*. Guessing here gives you a machine that is subtly wrong rather than obviously
broken, which is the expensive kind.

---

## Rule: `/sys/class/net/<dev>/` is one file per field

Where `/proc/net/*` gives you a table, `/sys` gives one value per file — better to script against, and
better to cross-check a tool with.

| Path under `/sys/class/net/<dev>/` | Is | The `ip` field reporting the same thing |
|---|---|---|
| `address` | MAC address | `ip link show <dev>` → `link/ether` |
| `mtu` | MTU | `ip link` → `mtu` |
| `operstate` | `up` / `down` / `unknown` | `ip link` → `state` |
| `carrier` | 1 if the link is up | `ip link` → `NO-CARRIER` flag |
| `iflink` | the peer's index, for a veth | `ip link` → `eth0@if12`, where 12 is this number |
| `master` | symlink to the bridge or bond it is enslaved to | `ip link` → `master br0` |
| `brif/` | on a bridge, one entry per enslaved port | `bridge link show` |
| `statistics/rx_packets`, `tx_bytes`, … | per-direction counters | `ip -s link` |

The right-hand column is the point. If `ip` and the file disagree, the file wins — this table tells you
which file to check.

---

## The paths this course actually reads

| Path | Holds | The tool that formats it |
|---|---|---|
| `/proc/<pid>/fd/` | one symlink per open descriptor | [`lsof -p`](lsof.md) |
| `/proc/<pid>/fdinfo/<n>` | offset, flags, inode for one fd | — |
| `/proc/net/tcp`, `tcp6`, `udp` | the socket tables, in hex | [`ss`](../netlink/ss.md) · [`netstat`](netstat.md) |
| `/proc/net/arp` | the neighbour cache | [`arp`](arp.md) |
| `/proc/net/dev` | per-interface counters | `ip -s link` |
| `/proc/net/route`, `fib_trie` | the routing table | `ip route` |
| `/proc/net/nf_conntrack` | the flow table | [`conntrack -L`](../netlink/conntrack.md) |
| `/proc/net/ip_vs`, `ip_vs_conn` | IPVS services and connections | [`ipvsadm`](../netlink/ipvsadm.md) |
| `/proc/net/snmp`, `netstat` | protocol counters | [`nstat`](nstat.md) |
| `/proc/<pid>/status` | `CapEff` — the capability bitmask | [`capsh --decode`](capsh.md) · [`getpcaps`](getpcaps.md) |
| `/proc/<pid>/ns/` | one magic symlink per namespace | [`readlink`](readlink.md) — see [`nsapi`](../nsapi/README.md) |
| `/proc/self/mountinfo` | the mount table with propagation flags | [`findmnt`](mount.md) |
| `/proc/<pid>/limits` | the descriptor ceiling | [`prlimit`](ulimit.md) |
| `/sys/kernel/security/apparmor/profiles` | loaded LSM profiles and their mode | [`apparmor_parser`](apparmor-parser.md) |

---

## Where `/proc` is the wrong file to trust

Two places, both worth knowing:

- **`/proc/net/tcp` is deprecated.** The kernel's own documentation says *"these interfaces are
  deprecated in favor of tcp_diag"* — the [`netlink`](../netlink/README.md) sub-family `ss` uses. On a machine
  with many sockets the file is also slow to render and can be inconsistent mid-read.
- **`/proc/meminfo` inside a container describes the host.** A container without a `/proc` remounted
  by the runtime reads the machine's memory, not its own cgroup limit. The cgroup files are the truth.

## What procfs can never tell you

**Anything the kernel does not already export as a file** — and, more often the problem, **anything
transient**. Every read here is a snapshot. If a socket opened and closed between two reads, it never
existed as far as this interface is concerned.

There is no streaming form of `procfs`. Watching a file in a loop is polling, and *"I looked and saw
nothing"* is not evidence. When you need to catch something short-lived, leave this interface entirely:
[`netlink`](../netlink/README.md) has `ss -E` and `conntrack -E`, and [`probe`](../probe/README.md) has `bpftrace`.

---

Taught in:
[everything is a file](../../../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) ·
[the fd table](../../../networking-fundamentals/act-1-one-machine/01-the-fd-table.md) ·
[ports and /proc/net/tcp](../../../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md)
· [conntrack](../../../networking-fundamentals/act-3-the-internet/02b-conntrack.md) ·
[what a container may do](../../../networking-fundamentals/act-10-cluster-security/01-what-a-container-may-do.md)

Next: [`netlink`](../netlink/README.md), the other half of how the kernel exposes itself · [`nsapi`](../nsapi/README.md),
which is what makes `/proc/net` mean different things to different processes.
