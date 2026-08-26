# `crane`

A registry's raw content: digests, manifests, layers, without pulling the image

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [what you shipped](../../../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### A registry's raw content, without pulling

| Command | What it gives you |
|---|---|
| `crane manifest <img>` | the manifest as JSON |
| `crane digest <img>` | the immutable identity behind a mutable tag |
| `crane config <img>` | the image config: entrypoint, env, user |
| `crane ls <repo>` | every tag |
| `crane copy <src> <dst>` | move an image between registries with no local docker |
