# `netlink` — the kernel's configuration API

**What you see in `strace`:** `socket(AF_NETLINK, SOCK_RAW, …)`

Thirteen tools speak this one, more than any other interface, and they include the four the course
leans on hardest. Everything on this page is shared by all of them — which is why none of it is
repeated on the individual tool pages.

[`ip`](ip.md) · [`ss`](ss.md) · [`bridge`](bridge.md) ·
[`conntrack`](conntrack.md) · [`nft`](nft.md) ·
[`ethtool`](ethtool.md) · [`wg`](wg.md) ·
[`iptables`](iptables.md) · [`iptables-save`](iptables-save.md)

`tc` · `ipvsadm` · `ipset` · `devlink` are the other four, and they have no page — they are rows on
[the roster](../README.md#the-honest-tally) and everything on *this* page is what they have in common
with the nine above. Which is most of what there was to say about them: the grammar below, the sub-family
each sits in, and the blind spot all thirteen share.

---

## Four sub-families, and which tool sits on each

Netlink is not one protocol but a family of them, selected by a constant in the `socket()` call. This
is the single most useful thing to know about the group, because it tells you which tools can possibly
see each other's work.

| Sub-family | `socket()` constant | Tools | Carries |
|---|---|---|---|
| **rtnetlink** | `NETLINK_ROUTE` | `ip` · `bridge` · `tc` | links, addresses, routes, neighbours, rules, qdiscs |
| **sock_diag** | `NETLINK_SOCK_DIAG` | `ss` | the socket tables, per-socket TCP internals |
| **nfnetlink** | `NETLINK_NETFILTER` | `conntrack` · `nft` · `ipset` · `iptables`† | the flow table, rulesets, sets |
| **generic netlink** | `NETLINK_GENERIC` | `ethtool` · `devlink` · `wg` · `ipvsadm` | anything added since — one multiplexed family with named sub-protocols |

Measured in the lab image, so you can check any row yourself:

```bash
strace -e trace=socket ss -tan 2>&1 | grep NETLINK
# socket(AF_NETLINK, SOCK_RAW|SOCK_CLOEXEC, NETLINK_SOCK_DIAG) = 3
```

Try it on `ip route show` and you get `NETLINK_ROUTE`; on `conntrack -L`, `NETLINK_NETFILTER`. The
abstraction becomes visible in one command.

> **† `iptables` is here conditionally.** Since 1.8 the same CLI sits over two kernel backends. On the
> nf_tables backend it is an nfnetlink client; on legacy it uses `setsockopt` on a raw socket and is
> not a netlink tool at all. **Run `iptables -V`** — it prints `(nf_tables)` or `(legacy)`. Measured on
> a current image, `iptables -t nat -L` opens `NETLINK_NETFILTER`, so the tool this course teaches is
> an nftables front end on any modern distro.

---

## Rule 1 — the grammar is `TOOL OBJECT VERB`

`ip`, `bridge`, `tc` and `devlink` all read noun-first, and it is not a style choice — the objects and
verbs come from the netlink messages underneath.

```
ip     link      show
ip     addr      add     10.0.0.1/24 dev eth0
bridge fdb       show
tc     qdisc     add     dev eth0 root netem delay 100ms
```

Two conveniences that hold across all of them:

- **Any unambiguous prefix works.** `ip a`, `ip ad`, `ip addr`, `ip address` are the same command.
  Two prefixes are traps: `ip l` is `link`, not `list`, and `ip n` is `neigh`, not `netns`.
- **With no verb, `show` is implied.** `ip addr` is `ip addr show`.

`nft`, `ipset` and `wg` invert it to `verb-obj` (`nft add table …`), and `ss`, `conntrack`, `ethtool`
and `ipvsadm` are conventional getopt tools. Each tool page states which shape it takes.

---

## Rule 2 — the verbs *are* the kernel's flags

This is the strongest "now I can guess it" lever in the whole reference, because the kernel writes the
mapping down in its own header, `include/uapi/linux/netlink.h`:

```c
/* Modifiers to NEW request */
#define NLM_F_REPLACE 0x100  /* Override existing            */
#define NLM_F_EXCL    0x200  /* Do not touch, if it exists   */
#define NLM_F_CREATE  0x400  /* Create, if it does not exist */
#define NLM_F_APPEND  0x800  /* Add to end of list           */
```

and iproute2 implements exactly that:

| Verb | Message | Flags | So it fails when |
|---|---|---|---|
| `add` | `RTM_NEW…` | `CREATE｜EXCL` | it already exists |
| `change` | `RTM_NEW…` | `REPLACE` | it does **not** exist — **except for `addr`**, see below |
| `replace` | `RTM_NEW…` | `CREATE｜REPLACE` | never — you end up with this either way |
| `append` | `RTM_NEW…` | `CREATE｜APPEND` | never — adds at the end of the list |
| `del` | `RTM_DEL…` | — | it does not exist |
| `show` / `list` | `RTM_GET…` | `DUMP` | — |
| `get` | `RTM_GET…` | — | nothing matches |

> ### The one row that does not hold: `ip addr change`
>
> Measured on iproute2 6.18, the flags are exactly as above but the *kernel* does not enforce them
> uniformly:
>
> ```
> ip route change 10.9.8.0/24 dev dum0        # rc=2, No such file or directory   <- as documented
> ip neigh change 10.9.9.1 lladdr … dev dum0   # rc=2, No such file or directory   <- as documented
> ip addr  change 10.9.9.9/24 dev dum0         # rc=0 — and the address now exists
> ```
>
> The reason is written down, in `net/ipv4/devinet.c`'s `inet_rtm_newaddr`, on the branch taken when no
> matching address is found:
>
> ```c
> /* It would be best to check for !NLM_F_CREATE here but
>  * userspace already relies on not having to provide this.
>  */
> ```
>
> So for addresses, `change` behaves as `replace`. It is a frozen ABI compromise, not a flag you got
> wrong. `ip rule` goes the other way and has no `change` verb at all (`rc=255`).
>
> The lever still works — it is the *kernel side* that has exceptions, and they are the kind you find by
> checking `$?` rather than by reading harder.

**This is the payoff.** You now know, without testing, why `ip addr add` fails on an address that is
already there and `ip addr replace` does not; why `change` on a *route* fails when the route is absent;
and why `append` exists for routes and not for links. Three verbs that looked like arbitrary synonyms are three flag
combinations with three different failure modes.

You can watch the flags do it:

```bash
ip link add v0 type veth peer name v1     # ok
ip link add v0 type veth peer name v1     # RTNETLINK answers: File exists   <- EXCL
ip addr add 10.9.0.1/24 dev v0            # ok
ip addr add 10.9.0.1/24 dev v0            # File exists                      <- EXCL
ip addr replace 10.9.0.1/24 dev v0        # ok                               <- CREATE|REPLACE
```

### The three bits are overloaded, which is why `dump` and `change` collide

The same header defines a second set of modifiers for `GET` requests, on the *same three bits*:

| Bit | On a `GET` request | On a `NEW` request |
|---|---|---|
| `0x100` | `NLM_F_ROOT` — the whole tree | `NLM_F_REPLACE` |
| `0x200` | `NLM_F_MATCH` — all matching | `NLM_F_EXCL` |
| `0x400` | `NLM_F_ATOMIC` | `NLM_F_CREATE` |

`NLM_F_DUMP` is just `ROOT｜MATCH`. So a flag word only means something once you know whether the
message is a `GET` or a `NEW` — and that is why the two halves of the table above cannot be merged.

### Honest limits

The **verb** half is quotable from the kernel header; treat it as fact. The **object** half is a strong
correspondence rather than a documented design statement, and it is imperfect: five `RTM_` families
belong to `tc` rather than `ip`, a few are monitor-only with no verb at all, and roughly half of `ip`'s
objects (`netns`, `xfrm`, `l2tp`, `mptcp`, `macsec`, `fou`, `ila`, `sr`, `ioam`, `tcp_metrics`) use
generic netlink or plain userspace instead of rtnetlink. `ip netns` in particular is
[not a netlink tool at all](../nsapi/README.md).

The mapping is also **per object, not global**: `ip link add` is `RTM_NEWLINK` with `CREATE｜EXCL`, but
`bridge link set` is `RTM_SETLINK` with no modifier bits. Same family, different contract.

---

## Rule 3 — global options compose with every object

In `ip`, options *before* the object are orthogonal to it — which is what makes one table worth a great
many commands. `ip help` prints both lists, options and objects, so you can count the combinations
yourself. The twelve options worth carrying:

| Option | Long form | Meaning |
|---|---|---|
| `-4` / `-6` | `-family inet` / `inet6` | restrict to one address family |
| `-j` | `-json` | output as JSON |
| `-p` | `-pretty` | pretty-print — with `-j`, readable JSON without piping to `jq` |
| `-br` | `-brief` | "Print only basic information in a tabular format" |
| `-d` | `-details` | more detail, including the link kind |
| `-s` | `-stats` | counters — **stackable**: `-s -s` gives more again |
| `-n` | `-netns` | run inside a named namespace — **takes an argument** |
| `-N` | `-Numeric` | numbers instead of protocol/scope names |
| `-a` | `-all` | run the command over all objects |
| `-c` | `-color` | colourise |
| `-b` | `-batch` | read commands from a file or stdin |
| `-t` | `-timestamp` | timestamp `monitor` output |

`-j` is the one worth a habit: JSON into `jq` turns "parse this with `awk` and hope the column order
never changes" into a field lookup. It arrived in iproute2 4.14.1 (2017).

> ### Where Rule 3 breaks
>
> **`ss` has no `-j` at all** — `ss --json` is an unrecognised option. Its sibling in the *same
> package* supports JSON on every object and `ss` supports it nowhere, so "iproute2 speaks JSON" is a
> rule with one large hole. Parse `ss` with `awk`, or read `/proc/net/tcp` yourself.
>
> **`tc` and `bridge` follow `ip`; `bridge` has no `-N`.** Close, not identical.

---

## What netlink can never tell you

**What a packet did.** Every tool here reports *configured state* (a route, a rule, an address) or
*tracked state* (a conntrack flow, a socket). None of them observes a packet traversing the kernel.

So when the configuration looks right and traffic still fails, no amount of `ip`, `nft` or `conntrack`
will close the gap — you need [`packet`](../packet/README.md) to see the bytes, or [`probe`](../probe/README.md) to see
which kernel function dropped them. That is the most common dead end in real debugging, and it is
structural rather than a matter of finding the right flag.

## What streams here

Seven of the thirteen can emit events as they happen, which no other interface but
[`probe`](../probe/README.md) and [`packet`](../packet/README.md) can do:

```bash
ip monitor          # links, addresses, routes, neighbours
ss -E               # sockets as they are destroyed
bridge monitor      # fdb and port events
conntrack -E        # NEW/UPDATE/DESTROY — watch a NAT decision being made
nft monitor         # ruleset changes, as an orchestrator writes them
tc monitor          # qdisc and filter events
devlink monitor     # device events
```

If you are polling one of these in a loop, you are choosing to miss things.

---

Taught in: [ethernet and ARP](../../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md)
· [IP and routing](../../../networking-fundamentals/act-2-two-machines/02-ip-and-routing.md) ·
[ports and /proc/net/tcp](../../../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md)
· [conntrack](../../../networking-fundamentals/act-3-the-internet/02b-conntrack.md) ·
[veth and bridge](../../../networking-fundamentals/act-4-one-pretends-many/02-veth-and-bridge.md)

Next: [the eight interfaces](../README.md) · [`procfs`](../procfs/README.md), the other half of how the
kernel exposes itself.
