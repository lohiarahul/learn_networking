# `kube-bench`

The cluster's own config scored against the CIS benchmark, file by file

| | |
|---|---|
| **Speaks** | [`local`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [the doors left open](../../../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `local` cannot tell you anything at all about your machine. These reshape input another tool produced — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `kube-bench --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `--targets` | which node role to audit. Control-plane and worker checks are different sets, and running the wrong one reports a clean bill for tests it skipped |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### The CIS benchmark, file by file

| Command | What it gives you |
|---|---|
| `kube-bench run --targets master` | control-plane checks |
| `kube-bench run --targets node` | kubelet and node config |
| `kube-bench --json` | machine-readable, for a gate |
