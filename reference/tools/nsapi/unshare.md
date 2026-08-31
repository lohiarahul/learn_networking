# `unshare`

A new namespace of any type, created *around a new process* — the mechanism `docker run` performs for you, and the only one an unprivileged user can perform themselves

| | |
|---|---|
| **Speaks** | [`nsapi`](README.md) · flags (`-m -u -i -n -p -U -C -T`) |
| **Mode** | mutate |
| **Taught in** | [who am I](../../../networking-fundamentals/act-4-one-pretends-many/05c-who-am-i.md) |
| **In the lab** | ✅ `/usr/bin/unshare` · unshare from util-linux 2.41.3 |
| **Blind spot** | `nsapi` cannot tell you what is *inside* a namespace. These move you between namespaces; they read nothing — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `unshare --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-n` | a new, empty network namespace — loopback and nothing else |
| `-U` | a new user namespace, which is what lets an unprivileged user create the others at all |
| `--mount-proc` | remount `/proc` in the new namespace. Skip it and `/proc` still shows the old namespace's processes, so every tool reading it lies to you |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### A new namespace around a new process

| Command | What it gives you |
|---|---|
| `unshare -n <cmd>` | a fresh, empty network namespace |
| `unshare -Urm --fork <cmd>` | user + mount + PID, unprivileged — what a rootless container is |
| `unshare --net --mount-proc -f bash` | the flag letters ARE the /proc/<pid>/ns filenames |
