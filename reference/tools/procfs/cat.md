# `cat` — concatenate

The primary interface to `/proc` and `/sys`. Most of this course is `cat`

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | throughout |
| **In the lab** | ✅ `/bin/cat` — provided by **BusyBox**, which implements a *subset* of the flags below (`cat --help` is the authority on which) |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### The primary interface to /proc and /sys

| Command | What it gives you |
|---|---|
| `cat /proc/net/tcp` | every TCP socket, in hex — what ss and netstat read |
| `cat /proc/net/arp` | the neighbour cache, as a file |
| `cat /proc/sys/net/ipv4/ip_forward` | a sysctl, as the file it actually is |
| `cat /proc/<pid>/status` | including CapEff, the capability bitmask |
| `cat /sys/class/net/<dev>/mtu` | one file per field — guessable paths |

## As the course runs it

*17 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `cat /proc/self/fdinfo/1` | kernel metadata for fd **1**: `pos:` byte offset, `flags:` open mode, `ino:` the inode | Lesson 1 — The file-descriptor table |
| `cat /proc/interrupts` | per-device, per-CPU hardware interrupt counts | Lesson 3 — Building minihttp, the listening server |
| `cat /proc/net/dev` | per-interface RX/TX byte and packet counters. opt: `\\| grep lo:` for one interface | Lesson 4 — The loopback interface |
| `cat /proc/net/tcp` | the raw TCP socket table *for this network namespace* — the path is a symlink to `self/net`, so it is never global. Addresses are hex and **little-endian** (byte-reversed): `0100007F` is `127.0.0.1` | Lesson 5 — Ports and /proc/net/tcp |
| `cat /sys/class/net/eth0/address` | the MAC, read straight from sysfs. One file per field is what makes `/sys` better than `/proc` to script against | Lesson 1 — The wire and the two names |
| `cat /sys/class/net/eth0/statistics/rx_packets` | a single counter. Everything `ip -s link` prints lives as one file each under `statistics/` | Lesson 1 — The wire and the two names |
| `cat /proc/net/vlan/config` | each VLAN interface with its parent and tag — the kernel's own view of what you just built | Lesson 1b — VLANs and segmentation |
| `cat /sys/class/net/eth0.10/address` | **the same MAC as the parent.** A VLAN interface is a tag, not a second network card | Lesson 1b — VLANs and segmentation |
| `cat /proc/net/route` | the main table in hex, little-endian like `/proc/net/tcp` | Lesson 2 — IP and routing |
| `cat /proc/net/udp` | the UDP table — the same shape as `/proc/net/tcp` but with no state column, because UDP has no states | Lesson 3 — ICMP, UDP, and TTL |
| `cat /sys/class/net/eth0/mtu` | the largest payload this device will carry | Lesson 3b — MTU and fragmentation |
| `cat /etc/resolv.conf` | the recursive resolver's address, the `search` list, and `ndots` — how many dots a name must contain before the resolver tries it as-is instead of appending each `search` domain first. The option behind most cluster DNS surprises | Lesson 4 — DNS |
| `cat /proc/self/cgroup` | `0::/` — this process's cgroup path, as seen from inside, where it is always the root | Lesson 1b — cgroups |
| `cat /sys/fs/cgroup/cpu.max` | two numbers: quota and period. `50000 100000` = 50 ms of CPU per 100 ms, i.e. half a core | Lesson 1b — cgroups |
| `cat /sys/fs/cgroup/memory.current` | live usage, which is what the limit is compared against | Lesson 1b — cgroups |
| `cat /sys/fs/cgroup/memory.events` | `oom_kill` is no longer 0. **The evidence lives here**, not in the container's output | Lesson 1b — cgroups |
| `cat /sys/fs/cgroup/cpu.stat` | `nr_throttled` and `throttled_usec` — the difference between "slow code" and "code being held back by a quota" | Lesson 1b — cgroups |
