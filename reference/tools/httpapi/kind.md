# `kind` — Kubernetes in Docker

A real multi-node cluster on one machine, where every node is a container you can `docker exec` into

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [the lab with kind](../../../networking-fundamentals/act-5-kubernetes/01-lab-with-kind.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### A real multi-node cluster where nodes are containers

| Command | What it gives you |
|---|---|
| `kind create cluster --config cfg.yaml` | multi-node, with port mappings |
| `kind get nodes` | the node containers |
| `docker exec -it <node> bash` | the payoff: a node you can actually get inside |
| `kind load docker-image <img>` | skip the registry entirely |
