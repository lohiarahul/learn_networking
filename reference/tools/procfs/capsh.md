# `capsh` — capability shell

Which Linux capabilities a process actually holds, decoded from `/proc/<pid>/status`'s `CapEff` bitmask

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | mutate |
| **Taught in** | [what a container may do](../../../networking-fundamentals/act-10-cluster-security/01-what-a-container-may-do.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `capsh --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `--drop` | actually remove a capability, then run something. This is how you prove which capability a tool needed rather than guessing |
| `--decode` | turn a hex capability mask from `/proc/<pid>/status` into names |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### Which capabilities a process really holds

| Command | What it gives you |
|---|---|
| `capsh --print` | the current set, decoded |
| `capsh --decode=0x00000000a80425fb` | turn a CapEff bitmask from /proc/<pid>/status into names |
| `capsh --drop=cap_net_raw -- -c 'ping -c1 127.0.0.1'` | prove a capability is what makes a thing work |
