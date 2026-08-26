# `helm`

What a chart *renders to* before it is applied (`template`), and what is currently released (`history`)

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [shipping a set of objects](../../../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### What a chart renders to, before it is applied

| Command | What it gives you |
|---|---|
| `helm template <rel> <chart> -f values.yaml` | the manifests, locally, with no cluster involved |
| `helm get manifest <rel>` | what is actually installed |
| `helm history <rel>` | revisions, so you can roll back |
| `helm diff upgrade <rel> <chart>` | the change an upgrade would make |
