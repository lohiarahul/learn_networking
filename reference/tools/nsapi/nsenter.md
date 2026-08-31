# `nsenter` — "namespace enter" *(folklore — undocumented)*

Entry into an *existing* process's namespaces, addressed by a **PID rather than a name** — the only handle a container actually gives you, and the way into one with no tools of its own

| | |
|---|---|
| **Speaks** | [`nsapi`](README.md) · same flag letters as `unshare` |
| **Mode** | mutate |
| **Taught in** | [entering what you did not name](../../../networking-fundamentals/act-4-one-pretends-many/05b-entering-what-you-did-not-name.md) |
| **In the lab** | ✅ `/usr/bin/nsenter` · nsenter from util-linux 2.41.3 |
| **Blind spot** | `nsapi` cannot tell you what is *inside* a namespace. These move you between namespaces; they read nothing — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `nsenter --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-t <pid>` | the target: whose namespaces to join, named by any process already in them |
| `-n` | the **network** namespace only. Your filesystem stays yours — so you run *your* `tcpdump` inside a container that has no tools installed |
| `-a` | all namespaces, which is closer to `docker exec`: their mounts, their binaries, their limits |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Enter an existing process's namespaces

| Command | What it gives you |
|---|---|
| `nsenter -t <pid> -n ip addr` | run in that process's network namespace — the way into a Docker container |
| `nsenter -t <pid> -a bash` | all namespaces |
| `nsenter -t 1 -n ss -tanp` | the host's namespace from inside a privileged container |
| `nsenter -t <pid> -n -- tcpdump -i eth0` | capture inside a container that has no tcpdump |
