# `jq` — JSON query

Turns `ip -j`, `kubectl -o json` and `docker inspect` into field lookups instead of `awk` guesses

| | |
|---|---|
| **Speaks** | [`local`](README.md) · *filter* |
| **Mode** | read-only |
| **Taught in** | [Act VIII in the wild](../../../networking-fundamentals/act-8-trust/in-the-wild.md) |
| **In the lab** | ✅ `/usr/bin/jq` · jq-1.8.1 |
| **Blind spot** | `local` cannot tell you anything at all about your machine. These reshape input another tool produced — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `jq --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-r` | raw output, without JSON quoting. The difference between `"10.0.0.1"` and something a shell can use |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Field lookups instead of awk guesses

| Command | What it gives you |
|---|---|
| `ip -j addr \| jq '.[].addr_info[].local'` | every address, as data |
| `kubectl get pods -o json \| jq -r '.items[].status.podIP'` | one field across a list |
| `docker inspect <c> \| jq '.[0].NetworkSettings'` | drill in |
| `jq -r '.[] \| [.a,.b] \| @tsv'` | back to columns for a shell loop |
