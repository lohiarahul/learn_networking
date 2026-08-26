# `nstat` — network statistics

Protocol counters from `/proc/net/snmp` and `netstat`, *as deltas since last call* — retransmits, listen overflows, drops

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/sbin/nstat` |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `nstat --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-a` | every counter, including the ones sitting at zero, so you can find a name you did not know to ask for |
| `-z` | do **not** zero the counters. `nstat` resets what it reads by default, so the second run of a bare `nstat` disagrees with the first for no reason |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### Counter deltas, not totals

| Command | What it gives you |
|---|---|
| `nstat` | everything that changed since the last call — retransmits, overflows, drops |
| `nstat -az` | absolute values, including zeros |
| `nstat -a TcpExtListenDrops TcpRetransSegs` | the two counters that explain most "it hangs" reports |
