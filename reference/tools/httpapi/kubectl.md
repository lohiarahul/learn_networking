# `kubectl`

The API server's whole object graph, and `explain` makes the schema self-describing

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate · live |
| **Taught in** | [pod networking](../../../networking-fundamentals/act-5-kubernetes/02-pod-networking.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `kubectl --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `--raw` | the API server's HTTP response, unmediated — no client-side formatting between you and what the API actually returns |
| `-w` | watch: changes as they happen, rather than one snapshot. Rollouts and endpoint churn only exist over time |
| `--as` | impersonate. Answers "can *that* service account do this", which is the question, not whether you can |

## What it can do

*15 commands, grouped by what you are trying to find out.*

### Find out what exists, without documentation

| Command | What it gives you |
|---|---|
| `kubectl api-resources` | every resource type, its short name and whether it is namespaced |
| `kubectl explain pod.spec.containers --recursive` | the schema, self-describing |
| `kubectl get --raw /api/v1/namespaces` | the REST API underneath, directly |

### Read state

| Command | What it gives you |
|---|---|
| `kubectl get pods -o wide` | adds node and Pod IP — the two columns you always want |
| `kubectl get pod <p> -o yaml` | the whole object, including what controllers wrote |
| `kubectl get endpointslices -l kubernetes.io/service-name=<svc>` | which Pods a Service actually points at |
| `kubectl describe pod <p>` | events at the bottom — where the real reason lives |

### Debug networking from inside the cluster

| Command | What it gives you |
|---|---|
| `kubectl run tmp --rm -it --image=nicolaka/netshoot -- bash` | a throwaway Pod with every tool |
| `kubectl debug <pod> -it --image=nicolaka/netshoot --target=<c>` | an ephemeral container sharing the target's namespaces |
| `kubectl port-forward svc/<svc> 8080:80` | a tunnel from your laptop into the cluster |
| `kubectl exec <pod> -- cat /etc/resolv.conf` | what the Pod's resolver is actually configured with |

### Watch and diff

| Command | What it gives you |
|---|---|
| `kubectl get pods -w` | stream changes |
| `kubectl get events --sort-by=.lastTimestamp` | chronological, which the default is not |
| `kubectl diff -f manifest.yaml` | what applying it would change |
| `kubectl auth can-i --list --as system:serviceaccount:default:my-sa` | what a service account may do |
