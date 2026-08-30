# `crictl` — CRI control

The node's container runtime *directly* — the only view left when the API server is down and `kubectl` is useless

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [the kubelet's side](../../../networking-fundamentals/act-4-one-pretends-many/06-the-kubelets-side.md) (built and run against `containerd` directly); the tool of choice once real Pods exist, in [static pods](../../../networking-fundamentals/act-6-control-plane/02-static-pods.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — but `apk add cri-tools` puts it in the Act IV `netshoot` lab, same as `runc` |
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
