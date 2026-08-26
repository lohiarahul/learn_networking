# `arp` — ARP cache tool

Nothing `ip neigh` doesn't. Recognise it in old runbooks

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | mutate |
| **Taught in** | [taught as `ip neigh`'s rival](../../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| **In the lab** | ✅ `/sbin/arp` — provided by **BusyBox**, which implements a *subset* of the flags below (`arp --help` is the authority on which) |
| **Standing** | ⚠️ **superseded** by [`ip neigh`](../netlink/ip.md) — same job, different invocation |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## ⚠️ Prefer [`ip neigh`](../netlink/ip.md)

**Same job, different invocation.** A minute to relearn by hand — but a script that shells out to this one needs editing, not renaming.

| instead of | type this |
|---|---|
| `arp -an` | `ip neigh` |
| `arp -d 10.0.0.1` | `ip neigh del 10.0.0.1 dev eth0` |
| `arp -s <ip> <mac>` | `ip neigh add <ip> lladdr <mac> dev <dev> nud permanent` |

**What you gain.** IPv6 neighbours, which `arp` cannot represent at all: ARP is an IPv4-only protocol, IPv6 uses NDP instead, and `ip neigh` reads both through the one command. (In this lab, where `arp` is a BusyBox applet, `arp -6` answers `unrecognized option: 6`.) Also the NUD state per entry — `REACHABLE`, `STALE`, `FAILED` — which is the field that says whether resolution is working or silently stale, and `ip monitor neigh` to watch it change.

**Why it is marked superseded.** Reads `/proc/net/arp`, a file with one address column and no address family — so no implementation of `arp` can show an IPv6 neighbour, whether it is net-tools or, as in this lab, a BusyBox applet. `ip neigh` reads netlink instead, and covers ARP and NDP through one command.

## What it can do

*3 commands, grouped by what you are trying to find out.*

### Recognise it in old runbooks

| Command | What it gives you |
|---|---|
| `arp -an` | the cache, read from /proc/net/arp — not netlink, which is why it can disagree with ip neigh |
| `arp -d <ip>` | delete an entry |
| `arp -s <ip> <mac>` | a static entry |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `arp -n` | the old tool. `-n` = numeric, don't reverse-resolve | Lesson 1 — The wire and the two names |
