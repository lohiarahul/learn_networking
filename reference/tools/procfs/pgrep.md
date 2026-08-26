# `pgrep` — process grep

PID lookup by name, so `/proc/<pid>/…` paths can be built in one line

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [the socket object](../../../networking-fundamentals/act-1-one-machine/02-the-socket-object.md) |
| **In the lab** | ✅ `/usr/bin/pgrep` — provided by **BusyBox**, which implements a *subset* of the flags below (`pgrep --help` is the authority on which) |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `pgrep --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-f` | match against the **full command line**, not just the executable name — the only form that finds `python3 server.py` |
| `-n` | the newest match, which makes `$(pgrep -n <name>)` safe to paste into another command |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### PID lookup, so /proc paths can be built in one line

| Command | What it gives you |
|---|---|
| `pgrep -n <name>` | the newest matching PID |
| `pgrep -f <pattern>` | match the whole command line |
| `ls -l /proc/$(pgrep -n minihttp)/fd` | the composition that makes pgrep worth a row |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `pgrep -n fd-demo` | `pgrep` (*process grep*) = find pids by name; `-n` = newest match only. opt: `-f` match the full command line, `-l` also print the name | Lesson 2 — What a socket really is |
