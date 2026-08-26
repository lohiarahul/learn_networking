# `lsof` — list open files

The join from a socket back to *which process and which fd* owns it, across every process at once

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [the fd table](../../../networking-fundamentals/act-1-one-machine/01-the-fd-table.md) |
| **In the lab** | ✅ `/usr/bin/lsof` · lsof version information: |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `lsof --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-i` | network files only, which is the entire reason this tool is in a networking reference |
| `-p` | one process's file descriptors. The bridge from a pid to the sockets it holds |
| `-nP` | no host or port name resolution. Also the difference between an instant answer and a tool that hangs on a dead resolver |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Join a socket back to a process and an fd

| Command | What it gives you |
|---|---|
| `lsof -i` | every network connection with its owning process |
| `lsof -i :443` | who holds this port |
| `lsof -p <pid>` | one process's open files and sockets, with their types |
| `lsof -nP -i TCP -sTCP:LISTEN` | listeners only, no name resolution |

## As the course runs it

*2 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `lsof -p $(pgrep -n fd-demo)` | `lsof` (*list open files*); `-p <pid>` = one process's open files and sockets, with a `TYPE` column (`REG`, `IPv4`). Reads the same `/proc/<pid>/fd`. Needs real `lsof` (netlab) — netshoot's is a busybox stub | Lesson 1 — The file-descriptor table |
| `lsof -i :8080` | `-i` = internet sockets; `:8080` filters to that port. Needs real `lsof` (netlab) | Lesson 5 — Ports and /proc/net/tcp |
