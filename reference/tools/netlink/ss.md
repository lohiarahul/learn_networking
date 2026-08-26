# `ss` — *"another utility to investigate sockets"* — "socket statistics" is *(folklore)*

Per-socket TCP internals: RTT, cwnd, retransmits (`-i`) and buffer accounting (`-m`). Also `--cgroup`, which attributes a socket to its cgroup — i.e. **to a container, without touching the container runtime** — and `-E` to stream sockets as they are destroyed, catching short-lived connections a polling loop misses

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · flags + *filter* |
| **Mode** | live |
| **Taught in** | [ports and /proc/net/tcp](../../../networking-fundamentals/act-1-one-machine/05-ports-and-proc-net-tcp.md) |
| **In the lab** | ✅ `/sbin/ss` |
| **Supersedes** | ✅ **prefer this one** over [`netstat`](../procfs/netstat.md) |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `ss --help` has that. These 4 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-i` | the tcp_diag internals — `rtt`, `cwnd`, `retrans`. A second read from a second kernel interface, and the only place the congestion state appears |
| `-p` | the owning process. Without it you have a port and no idea who holds it, which is usually the actual question |
| `-a` | **all** states, not just listening. The default hides every established and every `TIME-WAIT` socket |
| `-E` | sockets as they are *destroyed*. A polling loop cannot see a connection that lived 3ms; this can |

## What it can do

*9 commands, grouped by what you are trying to find out.*

### Which sockets exist

| Command | What it gives you |
|---|---|
| `ss -tuln` | TCP+UDP, listening, numeric — the first command on any strange box |
| `ss -tanp` | all TCP with the owning process |
| `ss -s` | a summary count by state and family |

### TCP internals no other tool exposes

| Command | What it gives you |
|---|---|
| `ss -ti` | RTT, cwnd, retransmits, pacing — per socket |
| `ss -tm` | send/receive buffer accounting, which is where "slow" often lives |

### Attribute a socket to a container

| Command | What it gives you |
|---|---|
| `ss --cgroup -tanp` | the cgroup path per socket — the container, without asking the runtime |

### Catch short-lived connections

| Command | What it gives you |
|---|---|
| `ss -E` | stream sockets as they are destroyed; a polling loop misses these entirely |

### Its own filter language

| Command | What it gives you |
|---|---|
| `ss -tan state established '( dport = :443 or sport = :443 )'` | expressions, not grep |
| `ss -tan 'dst 10.0.0.0/8'` | by network |

## As the course runs it

*5 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `ss -tlnp` | `-t` TCP; `-l` listening only; `-n` numeric (don't resolve service names); `-p` show the owning process. opt: drop `-l` for all states, `-u` for UDP, `-x` for Unix sockets | Lesson 5 — Ports and /proc/net/tcp |
| `ss -tan` | `-a` = **all** states, not just listening; the `State` column is `/proc/net/tcp`'s `st` field spelled out | Lesson 5b — TCP states and the SYN scan |
| `ss -tan state time-wait` | `state time-wait` is **`ss`'s own filter language**, not a flag — and not libpcap's. opt: `state established`, `state syn-sent`, or `state connected` for a group | Lesson 2 — TCP states |
| `ss -tmi dst :8080` | `-m` = socket memory; `-i` = internal TCP info; `dst :8080` = a filter on the destination. Together: buffers and congestion state for one connection | Lesson 3 — TCP and reliability |
| `ss -ti dst :80` | the same values with names attached, including `rtt`, `retrans` and the congestion algorithm | Lesson 3 — TCP and reliability |
