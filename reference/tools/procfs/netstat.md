# `netstat` — network statistics

Nothing `ss` doesn't — that is the honest answer, and the reason it is marked superseded. On the roster because every legacy box and every old runbook has it; the evidence is on its page

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [taught as `ss`'s rival](../../../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md) |
| **In the lab** | ✅ `/bin/netstat` — provided by **BusyBox**, which implements a *subset* of the flags below (`netstat --help` is the authority on which) |
| **Standing** | ⚠️ **superseded** by [`ss`](../netlink/ss.md) — drop-in |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## ⚠️ Prefer [`ss`](../netlink/ss.md)

**The swap is the name.** The replacement takes the same flag letters, so anything you can type here works there unchanged.

| instead of | type this |
|---|---|
| `netstat -tulnp` | `ss -tulnp` |
| `netstat -rn` | `ip route` |
| `netstat -i` | `ip -s link` |
| `netstat -s` | `nstat` |

**What you gain.** Per-socket TCP internals from tcp_diag — `ss -tin` prints `rtt:`, `rto:`, `cwnd:` and `mss:` per connection, which is the congestion state the kernel is actually in — plus server-side filtering (`ss -tn state established`, `ss '( dport = :443 )'`). `netstat` has no such output mode and no filter language.

**What will bite you in the swap.** In this lab `netstat` is a BusyBox applet, so `netstat -i` and `netstat -s` answer `unrecognized option` here even though net-tools supports them. The `ip -s link` and `nstat` columns opposite work either way, which is one more reason to type those.

**Why it is marked superseded.** Reads `/proc/net/tcp`, and the kernel's own documentation of that file says *"these interfaces are deprecated in favor of tcp_diag"*. `ss` is the tool that speaks tcp_diag. Every `netstat` fact is an `ss` fact; the reverse is not true.

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Recognise it in old runbooks

| Command | What it gives you |
|---|---|
| `netstat -tulnp` | the ss -tulnp of its day; reads /proc/net/tcp |
| `netstat -rn` | the routing table — ip route in old shell scripts |
| `netstat -i` | per-interface counters |
| `netstat -s` | protocol statistics |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `netstat -tlnp` | the tool `ss` replaced. Same flags, same idea — recognise it on legacy boxes, prefer `ss` | Lesson 5 — Ports and /proc/net/tcp |
