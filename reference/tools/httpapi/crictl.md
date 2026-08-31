# `crictl` — CRI control

The node's container runtime *directly* — the only view left when the API server is down and `kubectl` is useless

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [the kubelet's side](../../../networking-fundamentals/act-4-one-pretends-many/06-the-kubelets-side.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `crictl --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-a` | include exited containers. The one that crashed is the one you wanted to look at, and it is not in the default list |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### The node's runtime, with no API server involved

| Command | What it gives you |
|---|---|
| `crictl ps -a` | containers, when kubectl is useless |
| `crictl pods` | sandboxes |
| `crictl logs <id>` | logs straight from the runtime |
| `crictl inspectp <id>` | the pod sandbox config, including its network namespace |

## As the course runs it

*2 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `crictl version` | confirms `crictl` is a second, independent client of the same `containerd` `ctr` and `docker` both talk to | Lesson 6 — The kubelet's side |
| `crictl runp sandbox.json` | RunPodSandbox — the two-phase model `ctr run` has no equivalent of: a Pod's network is set up before any container inside it exists, proven by the failure happening at the network step | Lesson 6 — The kubelet's side |
