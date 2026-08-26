# `mount`

Which filesystems are grafted where; `findmnt` draws it as a tree with propagation flags

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | mutate |
| **Taught in** | [everything is a file](../../../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) |
| **In the lab** | ✅ `/bin/mount` · mount from util-linux 2.41.3 (libmount 2.41.3: btrfs, namespaces, idmapping, fd-based-mount, statx, assert, debug) |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Which filesystem is grafted where

| Command | What it gives you |
|---|---|
| `findmnt` | the whole tree |
| `findmnt -o TARGET,SOURCE,PROPAGATION` | propagation flags — why a bind mount did or did not appear elsewhere |
| `findmnt /run/netns` | where ip netns keeps its namespaces |
| `mount --bind /proc/<pid>/ns/net /run/netns/mine` | make an unnamed namespace visible to ip netns |

## As the course runs it

*2 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `mount` | every filesystem grafted into the tree, as `SOURCE on MOUNTPOINT type FSTYPE (options)`. `proc on /proc type proc` has no backing device. opt: `findmnt` draws it as a tree | Lesson 6 — Everything is a file |
| `mount \\| grep 'on / '` | the container's root: `type overlay`, with `lowerdir` (read-only image layers, colon-separated), `upperdir` (the writable layer) and `workdir` (scratch) | Lesson 6b — The container's filesystem (optional) |
