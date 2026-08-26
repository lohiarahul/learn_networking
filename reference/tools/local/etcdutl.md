# `etcdutl` — etcd utility

Offline snapshot operations (`snapshot restore`) that need no running etcd

| | |
|---|---|
| **Speaks** | [`local`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [etcd backup and restore](../../../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `local` cannot tell you anything at all about your machine. These reshape input another tool produced — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*2 commands, grouped by what you are trying to find out.*

### Offline, so it needs no running etcd

| Command | What it gives you |
|---|---|
| `etcdutl snapshot restore snap.db --data-dir /var/lib/etcd-new` | restore into a fresh data directory |
| `etcdutl snapshot status snap.db -w table` | revision, keys and hash — verify a backup before you trust it |
