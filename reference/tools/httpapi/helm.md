# `helm`

What a chart *renders to* before it is applied (`template`) — and, in `crds/`, the one directory it will not render at all

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [shipping a set of objects](../../../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) · [when the chart is not yours](../../../networking-fundamentals/act-7-workloads/08c-when-the-chart-is-not-yours.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*11 commands, grouped by what you are trying to find out.*

### What a chart renders to, before it is applied

| Command | What it gives you |
|---|---|
| `helm pull <repo>/<chart> --untar` | the chart on disk — Chart.yaml, values.schema.json, and whether it has a crds/ directory at all |
| `helm template <rel> <chart> -f values.yaml` | the manifests, locally, with no cluster involved |
| `helm template <rel> <chart> --include-crds` | the CRDs as well: plain `helm template` omits `crds/` entirely |
| `helm install <rel> <chart> --dry-run=server` | a render whose `lookup` calls can see the cluster — plain `--dry-run` is client-side and returns empty |
| `helm get manifest <rel>` | what is actually installed |
| `helm history <rel>` | revisions, so you can roll back |
| `helm diff upgrade <rel> <chart>` | the change an upgrade would make |

### What state the release is in, and who is holding it

| Command | What it gives you |
|---|---|
| `helm status <rel> -o json` | the release's own status word — `deployed`, `failed`, `pending-upgrade` |
| `kubectl get secret -l owner=helm -o custom-columns=NAME:.metadata.name,STATUS:.metadata.labels.status` | the same word at its source: the release Secret, which is a lock as well as a record |
| `helm rollback <rel> <rev>` | replays a stored manifest — and is what clears a `pending-upgrade` that no process is holding |
| `kubectl get crd` | what `helm uninstall` left behind: `crds/` is install-only in both directions |
