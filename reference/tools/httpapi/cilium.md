# `cilium`

An eBPF datapath's own view: policy verdicts, identities, and its BPF maps

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate · live |
| **Taught in** | [encryption between Pods](../../../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `cilium --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `--type` | (`monitor`) which event class. `--type drop` is the direct answer to "where did my packet go" |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### An eBPF datapath's own view

| Command | What it gives you |
|---|---|
| `cilium status --verbose` | datapath mode, masquerading, kube-proxy replacement state |
| `cilium endpoint list` | every endpoint and its security identity |
| `cilium policy get` | the policy as the agent compiled it, not as you wrote it |
| `cilium monitor --type drop` | stream drops with the reason and the identities involved |
| `cilium bpf lb list` | the load-balancer map — the actual service table |
