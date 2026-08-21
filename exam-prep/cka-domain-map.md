# CKA domain map — curriculum v1.35

Every domain and sub-competency, transcribed verbatim from `CKA_Curriculum_v1.35.pdf`
([`github.com/cncf/curriculum`](https://github.com/cncf/curriculum)), cross-checked against the
[LF program-changes page](https://training.linuxfoundation.org/certified-kubernetes-administrator-cka-program-changes/).
The two agree bullet for bullet.

**Re-pull before you book.** The curriculum is versioned per Kubernetes release. Most third-party
weighting tables are wrong — one well-ranked blog publishes an invented 12/22/31 split.

## Weightings

| Domain | Weight |
|---|---|
| [Troubleshooting](#troubleshooting--30) | **30%** |
| [Cluster Architecture, Installation and Configuration](#cluster-architecture-installation-and-configuration--25) | **25%** |
| [Servicing and Networking](#servicing-and-networking--20) | **20%** |
| [Workloads and Scheduling](#workloads-and-scheduling--15) | **15%** |
| [Storage](#storage--10) | **10%** |

Note the official domain name is **"Servicing and Networking"**, not "Services & Networking" — a
wording change in the 2025 revision.

## How to read the coverage column

- ✅ **covered** — a lesson teaches it hands-on, at or above exam depth.
- 🟡 **partial** — touched, but you will need more before the exam.
- ❌ **gap** — nothing in the course teaches this yet. Use the linked external resource.

Rate yourself in the last column as you go: `-` untried · `?` shaky · `✓` can do it under a clock.

---

## Troubleshooting — 30%

The largest domain, and the one where time bleeds. The course's network-troubleshooting material is
its strongest asset; the cluster-component half is the gap.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Troubleshoot clusters and nodes | ❌ gap | — needs `journalctl -u kubelet`, node `NotReady` triage, `crictl` | `-` |
| Troubleshoot cluster components | ❌ gap | — needs static-pod recovery, `crictl ps -a` / `crictl logs` when the apiserver is down | `-` |
| Monitor cluster and application resource usage | ❌ gap | — needs metrics-server, `kubectl top` | `-` |
| Manage and evaluate container output streams | 🟡 partial | — `kubectl logs` discipline (`--previous`, `-c`, `--since`) is never taught | `-` |
| Troubleshoot services and networking | ✅ **covered, above exam depth** | [the five-question method](../networking-fundamentals/act-5-kubernetes/08-debugging.md) · [a worked failure](../networking-fundamentals/act-5-kubernetes/09-debugging-walkthrough.md) · [the drills](../networking-fundamentals/act-5-kubernetes/diagnose.md) | `-` |

**The two traps candidates name most:**

1. **Static pods cannot be deleted with `kubectl`.** Edit or move the manifest in
   `/etc/kubernetes/manifests/`. And **back up `kube-apiserver.yaml` before you touch it** — a typo
   takes the cluster down and you no longer have `kubectl` to fix it.
2. The diagnostic path when `kubectl` is dead: `crictl ps -a` → `crictl logs <id>` →
   `journalctl -u kubelet`. `crictl` fluency is repeatedly named as a differentiator.

**Do the broken-cluster tasks last.** Two independent sources say so: this domain is 30% of the
marks and roughly 90% of the time-sink risk.

---

## Cluster Architecture, Installation and Configuration — 25%

The course's biggest gap, and the domain that changed most in 2025.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Manage role based access control (RBAC) | ❌ gap | — | `-` |
| Prepare underlying infrastructure for installing a Kubernetes cluster | ❌ gap | — | `-` |
| Create and manage Kubernetes clusters using kubeadm | ❌ gap | `kubeadm` appears only incidentally in [the kind lab](../networking-fundamentals/act-5-kubernetes/01-lab-with-kind.md) | `-` |
| Manage the lifecycle of Kubernetes clusters | ❌ gap | — this is where **upgrades** now live | `-` |
| Implement and configure a highly-available control plane | ❌ gap | — | `-` |
| **Use Helm and Kustomize to install cluster components** | ❌ gap | — see the warning below | `-` |
| **Understand extension interfaces (CNI, CSI, CRI, etc.)** | 🟡 partial | CNI is ✅ [covered well](../networking-fundamentals/act-5-kubernetes/05-cni.md); CSI and CRI are gaps | `-` |
| **Understand CRDs, install and configure operators** | ❌ gap | — `CustomResourceDefinition` appears nowhere in the course | `-` |

### Helm and Kustomize — the most-named weak spot

Both were promoted into this domain in 2025 from a vague "awareness of manifest management" bullet,
and `helm.sh/docs` being a whitelisted exam doc confirms they are genuinely examined.

**Helm** — reported task shapes: add a repo and render a manifest; **install a chart while excluding
CRDs** (`--skip-crds`); `helm template`. Candidates report charts "failing silently without specific
flags." Drill: `repo add`/`update`, `search repo`, `show values`, `install --set`/`-f`, `--dry-run`,
`template`, `upgrade --install`, `history`/`rollback`, `--skip-crds`, `-n --create-namespace`.

**Kustomize is the harder of the two, and for a non-obvious reason: `kustomize.io` is not an allowed
doc.** Your only reference is
[the single kustomization page on kubernetes.io](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/).
Practise base/overlay layout, `kustomize build`, `kubectl apply -k`, patches,
`configMapGenerator`/`secretGenerator`, `namePrefix` and `images` **from memory**.

### What changed in February 2025

Effective 18 Feb 2025 00:00 UTC. Per the LF, *the only date that matters is the date you sit the
exam* — not purchase date, not retake status. **Weightings did not change; competencies did.**

| Removed or folded away | Genuinely new |
|---|---|
| "Implement etcd backup and restore" — **no longer a listed competency** | **"Use the Gateway API to manage Ingress traffic"** |
| "Perform a version upgrade using kubeadm" → folded into "Manage the lifecycle" | **"Understand CRDs, install and configure operators"** |
| "Understand host networking configuration on the cluster nodes" | **"Define and enforce Network Policies"** — NetworkPolicy was not in the old CKA at all |
| "Choose an appropriate CNI plugin" → generalised to "extension interfaces" | **"Implement storage classes and dynamic volume provisioning"** |
| "Awareness of manifest management and common templating tools" → **promoted to** "Use Helm and Kustomize" and moved here from Workloads | "Manage a HA cluster" → "**Implement and configure** a HA control plane" |

Storage and Troubleshooting bullets were also reworded from passive "understand/evaluate" verbs to
active "implement/configure/troubleshoot" ones — a signal that tasks are more hands-on.

> **On etcd:** "Implement etcd backup and restore" is genuinely gone as a listed competency. Do not
> conclude etcd is off the exam — it remains the substrate for the 30% Troubleshooting domain, and
> 2026 first-hand reports still describe broken-control-plane recovery. Know
> `etcdctl snapshot save`/`restore` cold because it is cheap, but **don't let it crowd out Helm and
> Gateway API.** Circumstantial support: `etcd.io/docs` is allowed in CKS but *not* in CKA.

---

## Servicing and Networking — 20%

**The course's strength.** Act V is at or above exam depth on almost all of this.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Understand connectivity between Pods | ✅ **above exam depth** | [the Pod as a shared netns](../networking-fundamentals/act-5-kubernetes/02-pod-networking.md) · [CNI](../networking-fundamentals/act-5-kubernetes/05-cni.md) | `-` |
| **Define and enforce Network Policies** | ✅ covered | [NetworkPolicy](../networking-fundamentals/act-5-kubernetes/07-network-policy.md) | `-` |
| Use ClusterIP, NodePort, LoadBalancer service types and endpoints | ✅ **above exam depth** | [Services and kube-proxy](../networking-fundamentals/act-5-kubernetes/03-services.md) · [Service shapes](../networking-fundamentals/act-5-kubernetes/04b-service-shapes.md) — headless, SRV, `sessionAffinity`, `ExternalName`, `externalTrafficPolicy` | `-` |
| **Use the Gateway API to manage Ingress traffic** | ✅ covered | [Gateway API](../networking-fundamentals/act-5-kubernetes/06b-gateway-api.md) — `GatewayClass`/`Gateway`/`HTTPRoute`, the delegation model, weighted canary, and reading `.status` | `-` |
| Know how to use Ingress controllers and Ingress resources | ✅ covered | [Ingress](../networking-fundamentals/act-5-kubernetes/06-ingress.md) | `-` |
| Understand and use CoreDNS | ✅ **above exam depth** | [CoreDNS](../networking-fundamentals/act-5-kubernetes/04-coredns.md) | `-` |

**Gateway API is the thinnest-covered competency in the entire free ecosystem**, and its docs are
whitelisted at `gateway-api.sigs.k8s.io` — which is independent confirmation it is examined. Reported
task shape: **convert an existing Ingress into a `Gateway` + `HTTPRoute` with TLS.**

The course now covers this in [Gateway API](../networking-fundamentals/act-5-kubernetes/06b-gateway-api.md).
For exam rehearsal, drill the conversion specifically — the lesson teaches the model and the canary
split, but the exam wants you fluent at rewriting an existing Ingress. The allowed pages to know by
heart: [the guides](https://gateway-api.sigs.k8s.io/guides/),
[`api-types/gateway`](https://gateway-api.sigs.k8s.io/api-types/gateway/) and
[`api-types/httproute`](https://gateway-api.sigs.k8s.io/api-types/httproute/).

**NetworkPolicy is the most-cited technical failure across both exams.** The rule people get wrong:
**multiple selectors in one rule are ANDed; multiple rules are ORed.** The classic trap is
cross-namespace — `namespaceSelector` and `podSelector` in *one* `from` block (AND) versus two
separate blocks (OR). [editor.networkpolicy.io](https://editor.networkpolicy.io/) is a free visual
editor worth using to check your intuition.

---

## Workloads and Scheduling — 15%

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Understand application deployments and how to perform rolling update and rollbacks | ❌ gap | Deployments are *used* throughout Act V but never taught | `-` |
| Use ConfigMaps and Secrets to configure applications | ❌ gap | one hands-on beat only: [a TLS Secret is just base64](../networking-fundamentals/act-5-kubernetes/06-ingress.md) | `-` |
| **Configure workload autoscaling** | ❌ gap | — HPA. Note the verb changed from "know how to scale applications" | `-` |
| Understand the primitives used to create robust, self-healing, application deployments | 🟡 partial | readiness probes are taught well as an [endpoint gate](../networking-fundamentals/act-5-kubernetes/03-services.md); liveness and startup probes are gaps | `-` |
| **Configure Pod admission and scheduling (limits, node affinity, etc.)** | 🟡 partial | cgroup limits are ✅ [taught from the kernel up](../networking-fundamentals/act-4-one-pretends-many/01b-cgroups.md), but `requests` and the scheduler are an [open question the course deliberately never answers](../networking-fundamentals/act-4-one-pretends-many/01b-cgroups.md) | `-` |

**Small-detail losses candidates report:** the container name in `kubectl set image` must match
exactly; **changing a ConfigMap does not restart Pods** (needs `kubectl rollout restart`); and
unmentioned taints silently blocking scheduling.

---

## Storage — 10%

The course's cleanest gap — nothing here is covered.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| **Implement storage classes and dynamic volume provisioning** | ❌ gap | — the verb strengthened from "understand" to "implement" | `-` |
| Configure volume types, access modes and reclaim policies | ❌ gap | nearest is [overlayfs and Docker volumes](../networking-fundamentals/act-1-one-machine/06b-the-container-filesystem.md), which deliberately *poses* the PV/PVC question without answering it | `-` |
| Manage persistent volumes and persistent volume claims | ❌ gap | — | `-` |

**The precise binding rule**, which resolves most "why won't my PVC bind" tasks: a PVC binds when
**capacity ≥ request AND accessModes match AND storageClassName matches**. Check those three before
anything else.

---

## Honest summary

| Domain | Weight | Course covers |
|---|---|---|
| Troubleshooting | 30% | ~1 of 5 bullets, but that one (networking) very well |
| Cluster Architecture | 25% | ~0.5 of 8 bullets |
| Servicing and Networking | 20% | 5 of 6 bullets, most above exam depth |
| Workloads and Scheduling | 15% | ~0.5 of 5 bullets |
| Storage | 10% | 0 of 3 bullets |

Roughly **20–25% of CKA** is covered today, concentrated almost entirely in one domain. The fastest
paths to a passing score, in value-per-hour order: **Gateway API** (adjacent to material already
written, and the thinnest-covered competency anywhere), then **Helm and Kustomize**, then **cluster
component troubleshooting**, then **storage** (small, self-contained, 10% of the marks).
