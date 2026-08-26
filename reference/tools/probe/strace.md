# `strace` — system call trace

The exact syscalls a process makes, with arguments and return values — and it stops the world to do it

| | |
|---|---|
| **Speaks** | [`probe`](README.md) · `-e trace=…` |
| **Mode** | live |
| **Taught in** | [minihttp](../../../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) |
| **In the lab** | ✅ `/usr/bin/strace` · strace -- version 6.18 |
| **Supersedes** | ✅ **prefer this one** over [`ltrace`](ltrace.md) |
| **Blind spot** | `probe` has none worth the name — this is the only [interface](README.md) that can say which kernel function dropped your packet. It does need a running target |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `strace --help` has that. These 4 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-e trace=<set>` | which syscalls. `trace=network` cuts thousands of `read`/`write` lines down to the ones about sockets |
| `-f` | follow forks. Without it, a server that handles each connection in a child shows you the `accept` and nothing after it |
| `-p <pid>` | attach to something already running, which is the only option when the problem takes an hour to appear |
| `-c` | a summary count and time per syscall instead of a line each — where the time went, not what happened |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### Exactly which syscalls a process makes

| Command | What it gives you |
|---|---|
| `strace -e trace=network <cmd>` | only the socket calls — how you see which kernel API a tool speaks |
| `strace -f -p <pid>` | attach to a running process and follow its children |
| `strace -e trace=openat -f <cmd>` | which files it looks for, in order — how you debug config lookup |
| `strace -c <cmd>` | a summary count per syscall, instead of the firehose |
| `strace -T -tt <cmd>` | timestamps and per-call duration — where the wait actually is |

## As the course runs it

*2 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `strace -e trace=socket,bind,listen,accept /tmp/minihttp 8080` | `strace` (*system call trace*); `-e trace=…` = a comma list of calls to show; the rest is the program and its args. **Stops the process on every call** — that cost is why eBPF exists | Lesson 3 — Building minihttp, the listening server |
| `strace -e trace=accept /code/minihttp 8080` | watch only `accept`: it hangs until a connection reaches ESTABLISHED, then prints `= 4` | Lesson 5b — TCP states and the SYN scan |
