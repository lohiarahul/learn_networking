# `ping` — named after sonar; "Packet InterNet Groper" is *(folklore)*

Whether ICMP echo returns, and the RTT distribution

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [loopback](../../../networking-fundamentals/act-1-one-machine/04-loopback.md) |
| **In the lab** | ✅ `/bin/ping` · ping from iputils 20250605 |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

> **Not what people assume.** It opens `AF_INET, SOCK_DGRAM` — ICMP datagram sockets, not `SOCK_RAW`. Gated by `net.ipv4.ping_group_range`, which is why `ping` no longer needs to be setuid.

## The flags that carry their weight

*Not the flag list — `ping --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-M do` | set DF — forbid fragmentation. With `-s`, this is the PMTU probe: the largest packet that fits, found by binary search |
| `-s <n>` | the payload size. The default 56 bytes fits through everything, which is exactly why it never finds an MTU problem |
| `-I <dev>` | leave by a named interface, bypassing the route lookup — the way to test a path the routing table would not choose |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Is it reachable, and how variable is the path

| Command | What it gives you |
|---|---|
| `ping -c 4 <host>` | four probes and an RTT summary |
| `ping -i 0.2 -c 100 <host>` | faster interval, enough samples to see jitter |
| `ping -M do -s 1472 <host>` | don't fragment at exactly 1500 bytes total — the MTU probe |
| `ping -I <dev> <host>` | force the source interface |

## As the course runs it

*6 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `ping -c 4 127.0.0.1` | `-c 4` = stop after 4 packets; trailing = target. opt: `-i 0.2` for a shorter interval | Lesson 4 — The loopback interface |
| `ping -c 4 172.17.0.3` | the container's own external address — same kernel, so it still never touches a wire | Lesson 4 — The loopback interface |
| `ping -c 2 "$(ip route get 8.8.8.8 \\| awk '{print $3}')"` | the same lookup, spliced in with `$(…)` so nothing is hardcoded | Lesson 1 — The wire and the two names |
| `ping -c 2 <unused address in your subnet>` | forces an ARP request for an address nobody owns, so you can watch the request go out and nothing come back | Lesson 1 — The wire and the two names |
| `ping -c1 -M do -s 1472 <gateway>` | `-M do` = set **Don't Fragment**; `-s 1472` = payload bytes. 1472 + 8 (ICMP) + 20 (IP) = exactly 1500, so it fits. Use your gateway, not `8.8.8.8` — external ICMP is often dropped entirely | Lesson 3b — MTU and fragmentation |
| `ping -c1 -M do -s 1473 <gateway>` | one byte over, and DF forbids splitting it, so it fails with **`ping: sendmsg: Message too large`**. Note *where* that came from: it is a local `EMSGSIZE` from your own stack, not an ICMP "fragmentation needed" from a router — a distinction the path-MTU-discovery story depends on. This pair is how you *measure* a path's MTU rather than guess it | Lesson 3b — MTU and fragmentation |
