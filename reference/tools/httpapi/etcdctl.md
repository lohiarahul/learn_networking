# `etcdctl` — etcd control

The cluster's stored state as raw keys — the layer beneath every Kubernetes object

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate · live |
| **Taught in** | [etcd backup and restore](../../../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `etcdctl --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `--prefix` | operate on a key *subtree*. etcd has no directories, so this is how you list anything at all |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### The layer beneath every Kubernetes object

| Command | What it gives you |
|---|---|
| `etcdctl get /registry/pods --prefix --keys-only` | raw keys — the object graph as storage |
| `etcdctl endpoint health --cluster` | quorum health |
| `etcdctl member list -w table` | who is in the cluster |
| `etcdctl snapshot save snap.db` | a backup |
| `etcdctl watch /registry/services --prefix` | stream changes |
