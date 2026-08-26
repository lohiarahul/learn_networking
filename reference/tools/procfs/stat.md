# `stat`

Proves a `/proc` file reports `Size: 0` and still has content — the contradiction that makes "everything is a file" mean something

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [everything is a file](../../../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) |
| **In the lab** | ✅ `/bin/stat` — provided by **BusyBox**, which implements a *subset* of the flags below (`stat --help` is the authority on which) |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*2 commands, grouped by what you are trying to find out.*

### Proves a /proc file is not a file

| Command | What it gives you |
|---|---|
| `stat /proc/net/tcp` | Size: 0, and yet it has content — the contradiction that gives "everything is a file" meaning |
| `stat -c '%s %F' /proc/self/status` | size and type in one line |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `stat /proc/net/dev` | print a file's metadata. procfs files report `Size: 0` and yet `cat` prints content: the contradiction the lesson is built on | Lesson 6 — Everything is a file |
