# `conntrack` — connection tracking

The kernel's flow table as a live stream (`-E`), which is the only way to watch NAT decisions happen

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · flags |
| **Mode** | mutate · live |
| **Taught in** | [conntrack](../../../networking-fundamentals/act-3-the-internet/02b-conntrack.md) |
| **In the lab** | ✅ `/usr/sbin/conntrack` · conntrack v1.4.8 (conntrack-tools) |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `conntrack --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-E` | the live event stream instead of a snapshot. `-L` shows what is tracked now; `-E` shows what is being created and torn down |
| `-C` | the current table count — one number, against `nf_conntrack_max`, which is the check that explains a box refusing new connections |

## What it can do

*8 commands, grouped by what you are trying to find out.*

### Read the flow table

| Command | What it gives you |
|---|---|
| `conntrack -L` | every tracked flow, with both the original and the reply tuple |
| `conntrack -L -p tcp --dport 443` | filtered |
| `conntrack -C` | just the count — the number that hits nf_conntrack_max |

### Watch NAT decisions happen

| Command | What it gives you |
|---|---|
| `conntrack -E` | stream NEW/UPDATE/DESTROY — the only way to see a translation being made |
| `conntrack -E -e NEW` | only new flows |

### Change it

| Command | What it gives you |
|---|---|
| `conntrack -D -p tcp --dport 443` | delete matching entries; the next packet is re-evaluated |
| `conntrack -F` | flush everything — blunt, and it breaks live connections |

### Counters

| Command | What it gives you |
|---|---|
| `conntrack -S` | per-CPU stats: insert_failed and drop are the ones that matter |

## As the course runs it

*2 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `conntrack -E -p tcp` | `-E` = **event mode**: stream flows as they change, rather than dumping the table. `-p tcp` filters by protocol. The only way to watch a NAT decision being made | Lesson 2b — conntrack |
| `conntrack -C` | `-C` = count the flows tracked right now. opt: `-L` to list them, `-D` to delete one | Lesson 2b — conntrack |
