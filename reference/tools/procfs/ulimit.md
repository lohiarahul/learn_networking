# `ulimit` — user limit / process limit

The descriptor ceiling that quietly breaks busy servers — `prlimit` reads it on an *already-running* process

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · shell builtin / flags |
| **Mode** | mutate |
| **Taught in** | [minihttp](../../../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) |
| **In the lab** | ✅ `ulimit` |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `ulimit --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-n` | the open-file-descriptor ceiling — the one limit a server hits first, because every socket is an fd |
| `-H` | the **hard** limit rather than the soft one. Two different numbers, and only one of them can be raised back |
| `--pid` | (`prlimit`) another process's limits, live. `ulimit` can only ever tell you about the shell you typed it in |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### The descriptor ceiling that quietly breaks servers

| Command | What it gives you |
|---|---|
| `ulimit -n` | the soft limit for this shell |
| `ulimit -Hn` | the hard limit — the ceiling you cannot raise yourself |
| `prlimit --pid <pid>` | every limit on an ALREADY-RUNNING process |
| `prlimit --pid <pid> --nofile=8192:8192` | raise it without a restart |

## As the course runs it

*2 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `ulimit -n` | `ulimit` (*user limit*); `-n` = max open file descriptors, soft limit. opt: `-Hn` for the hard limit | Lesson 3 — Building minihttp, the listening server |
| `prlimit --pid <pid>` | read (or set) the limits of an **already-running** process, which `ulimit` cannot do | Lesson 3 — Building minihttp, the listening server |
