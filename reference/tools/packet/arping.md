# `arping` — ARP ping

Reachability at **layer 2**, bypassing IP entirely — proves the wire works when routing does not

| | |
|---|---|
| **Speaks** | [`packet`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [ethernet and ARP](../../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| **In the lab** | ✅ `/usr/sbin/arping` |
| **Blind spot** | `packet` cannot tell you which process or rule was responsible. It sees bytes on a link, not the host state behind them — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `arping --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-I <dev>` | which interface to ARP from. ARP is link-local, so there is no route lookup to fall back on and this is not optional |
| `-D` | duplicate address detection — ask whether anyone else already answers for this IP, before you assign it |

## What it can do

*2 commands, grouped by what you are trying to find out.*

### Reachability below IP

| Command | What it gives you |
|---|---|
| `arping -I <dev> -c 3 <ip>` | proves wire and neighbour work when routing does not |
| `arping -D -I <dev> <ip>` | duplicate address detection — is someone else already using it |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `arping -c 1 <ip>` | ARP-level reachability: **layer 2 only, no IP involved**. Proves the wire when routing is broken | Lesson 1 — The wire and the two names |
