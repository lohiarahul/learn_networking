# `readlink`

Reads a magic symlink's *computed* target — `net:[4026531840]`, the namespace identity test

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [everything is a file](../../../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) |
| **In the lab** | ✅ `/usr/bin/readlink` — provided by **BusyBox**, which implements a *subset* of the flags below (`readlink --help` is the authority on which) |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `readlink --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-f` | follow the whole chain to the real path. On `/proc/<pid>/ns/net` this is what turns a symlink into a namespace identity you can compare |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### A magic symlink's computed target

| Command | What it gives you |
|---|---|
| `readlink /proc/self/ns/net` | net:[4026531840] — the namespace identity test |
| `readlink /proc/<pid>/fd/3` | what fd 3 actually points at: a file, a socket, a pipe |
| `readlink -f <path>` | resolve every level |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `readlink <name>` | print the path stored inside a symlink. On a magic `/proc` symlink that string is **computed on read**, not stored — which is what makes `/proc/self` work | Lesson 6 — Everything is a file |
