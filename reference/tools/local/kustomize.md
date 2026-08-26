# `kustomize`

The overlay-resolved manifests `helm template` would give you, with no templating language at all

| | |
|---|---|
| **Speaks** | [`local`](README.md) · verb-obj |
| **Mode** | read-only |
| **Taught in** | [shipping a set of objects](../../../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `local` cannot tell you anything at all about your machine. These reshape input another tool produced — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### Overlays with no templating language at all

| Command | What it gives you |
|---|---|
| `kustomize build overlays/prod` | the fully-resolved manifests |
| `kubectl kustomize overlays/prod` | the same, built into kubectl |
| `kustomize edit set image app=repo:tag` | mutate the kustomization file itself |
