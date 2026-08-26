# `traceroute`

The hop list, by walking TTL upward

| | |
|---|---|
| **Speaks** | [`packet`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [ICMP and UDP](../../../networking-fundamentals/act-2-two-machines/03-icmp-and-udp.md) |
| **In the lab** | ✅ `/usr/bin/traceroute` — provided by **BusyBox**, which implements a *subset* of the flags below (`traceroute --help` is the authority on which) |
| **Blind spot** | `packet` cannot tell you which process or rule was responsible. It sees bytes on a link, not the host state behind them — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `traceroute --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-I` | ICMP probes instead of the UDP default. Firewalls treat the two differently, so the hop that goes dark changes |
| `-T` | TCP probes to a real port, which is the only variant that traces the path your application actually takes |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### The hop list

| Command | What it gives you |
|---|---|
| `traceroute -n <host>` | numeric, so a slow reverse lookup cannot stall it |
| `traceroute -I <host>` | ICMP probes instead of the UDP default |
| `traceroute -T -p 443 <host>` | TCP to a real port — gets through filters that drop UDP |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `traceroute 8.8.8.8` | sends packets with rising TTL; each hop that discards one replies with ICMP "time exceeded", revealing itself. opt: `-n` skip reverse DNS, which makes it much faster | Lesson 3 — ICMP, UDP, and TTL |
