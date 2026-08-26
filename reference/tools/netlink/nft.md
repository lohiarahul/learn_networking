# `nft` — nftables — netfilter tables

One tool and one grammar for IPv4, IPv6, ARP and bridge (the `inet` family), plus the sets and maps that iptables needed `ipset` for. In-kernel since 3.13; netfilter's own wiki has called the xtables tools legacy since 2018, RHEL 10 no longer ships the legacy `ip_tables` module at all, and Docker Engine 29 has an experimental native nftables backend it intends to make the default

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · verb-obj |
| **Mode** | mutate · live |
| **Taught in** | [iptables and NAT](../../../networking-fundamentals/act-4-one-pretends-many/03-iptables-and-nat.md) |
| **In the lab** | ✅ `/usr/sbin/nft` · nftables v1.1.6 (Commodore Bullmoose #7) |
| **Supersedes** | ✅ **prefer this one** over [`iptables`](iptables.md) · [`iptables-save`](iptables-save.md) |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `nft --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-a` | rule **handles**, which is the only way to delete one rule rather than reloading the ruleset |

## What it can do

*9 commands, grouped by what you are trying to find out.*

### Read everything at once

| Command | What it gives you |
|---|---|
| `nft list ruleset` | every table, chain and rule in one output — no per-table loop |
| `nft -a list ruleset` | with handles, which is how you delete a specific rule |
| `nft -j list ruleset` | JSON |

### One grammar for all families

| Command | What it gives you |
|---|---|
| `nft add table inet filter` | inet covers IPv4 and IPv6 together — the thing iptables cannot do |
| `nft add chain inet filter input '{ type filter hook input priority 0; policy drop; }'` | a base chain, hook and policy declared inline |

### Native sets and maps — no ipset needed

| Command | What it gives you |
|---|---|
| `nft add set inet filter bad '{ type ipv4_addr; flags interval; }'` | a typed set |
| `nft add element inet filter bad '{ 10.0.0.0/8, 192.168.1.1 }'` | populate it |
| `nft add rule inet filter input ip saddr @bad drop` | match the whole set in one rule |

### Watch it change

| Command | What it gives you |
|---|---|
| `nft monitor` | stream ruleset changes — see what an orchestrator is writing |

## As the course runs it

*5 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `nft list ruleset` | the whole store, every family and table at once. Run it after writing rules with `iptables` and your rules are in it — which is the point: since 1.8 `iptables` is a front-end and **this** is where it wrote them | Lesson 3 — iptables and NAT |
| `nft add table inet other` | a table of your own, in the `inet` family so one table covers IPv4 and IPv6. This is what lets two programs share a hook without fighting over one global table — `kindnet` does exactly this | Lesson 3 — iptables and NAT |
| `nft add chain inet other fw '{ type filter hook forward priority 0; policy accept; }'` | the hook and priority **declared**, not implied by which of five fixed tables you picked. Rule order stops being global and becomes `priority` | Lesson 3 — iptables and NAT |
| `nft add rule inet other fw ip saddr 10.20.0.9 drop` | a native rule in a native table — and therefore one that `iptables-save` reports nothing about, which is the shadow this lesson ends on | Lesson 3 — iptables and NAT |
| `nft list table inet kindnet-network-policies` | Act V cashes this in: the table `kind`'s CNI writes NetworkPolicy into, holding a `set` of Pod IPs and a `queue` verdict rather than any allow or drop rule | Lesson 7 — Network Policy |
