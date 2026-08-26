# `sysctl` — system control

Every kernel tunable by name, and `-a` makes it searchable

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | mutate |
| **Taught in** | [conntrack](../../../networking-fundamentals/act-3-the-internet/02b-conntrack.md) |
| **In the lab** | ✅ `/sbin/sysctl` — provided by **BusyBox**, which implements a *subset* of the flags below (`sysctl --help` is the authority on which) |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `sysctl --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-a` | every knob on the box. This is discovery: you cannot grep for a setting whose name you do not know |
| `-w` | the only form that changes anything — without it `sysctl` is a reader |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### Every kernel tunable by name

| Command | What it gives you |
|---|---|
| `sysctl -a \| grep <pattern>` | search — the discovery mode |
| `sysctl net.ipv4.ip_forward` | read one |
| `sysctl -w net.ipv4.ip_forward=1` | write it, until reboot |
| `sysctl net.netfilter.nf_conntrack_max` | the ceiling that turns into mysterious drops |
| `cat /proc/sys/net/ipv4/ip_forward` | the same value; sysctl keys ARE /proc/sys paths, dots for slashes |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `sysctl net.netfilter.nf_conntrack_max` | the table ceiling. Compare against `-C`: as they converge, new connections fail intermittently under load — a failure that looks exactly like a flaky network | Lesson 2b — conntrack |
