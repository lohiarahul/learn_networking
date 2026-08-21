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

The largest domain, and the one where time bleeds. All five bullets are now covered, and the course
carries two independent diagnostic methods — one for a broken *cluster*, one for a broken *workload*.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Troubleshoot clusters and nodes | ✅ covered | [node maintenance](../networking-fundamentals/act-6-control-plane/07-node-maintenance.md) · [when the control plane breaks](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md) — the five-question descent, `journalctl -u kubelet`, `crictl` · [the drills](../networking-fundamentals/act-6-control-plane/diagnose.md) | `-` |
| Troubleshoot cluster components | ✅ **covered, above exam depth** | [when the control plane breaks](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md) — a deliberately broken static-pod manifest, plus `crictl ps -a` / `crictl logs` with the apiserver down · [7 drills](../networking-fundamentals/act-6-control-plane/diagnose.md) | `-` |
| Monitor cluster and application resource usage | ✅ covered | [choosing the number](../networking-fundamentals/act-7-workloads/10-choosing-the-number.md) — metrics-server installed and made to fail first, `kubectl top` | `-` |
| Manage and evaluate container output streams | 🟡 partial | used throughout ([`logs --previous`](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md), `crictl logs`, [`logs -l`](../networking-fundamentals/act-7-workloads/07-the-other-workload-kinds.md)) but no lesson treats `-c` / `--since` / multi-container selection as a subject | `-` |
| Troubleshoot services and networking | ✅ **covered, above exam depth** | [the five-question method](../networking-fundamentals/act-5-kubernetes/08-debugging.md) · [a worked failure](../networking-fundamentals/act-5-kubernetes/09-debugging-walkthrough.md) · [the drills](../networking-fundamentals/act-5-kubernetes/diagnose.md) | `-` |

**The two traps candidates name most:**

1. **Static pods cannot be deleted with `kubectl`.** Edit or move the manifest in
   `/etc/kubernetes/manifests/`. And **back up `kube-apiserver.yaml` before you touch it** — a typo
   takes the cluster down and you no longer have `kubectl` to fix it.
2. The diagnostic path when `kubectl` is dead: `crictl ps -a` → `crictl logs <id>` →
   `journalctl -u kubelet`. `crictl` fluency is repeatedly named as a differentiator.

**Do the broken-cluster tasks last.** Two independent sources say so: this domain is 30% of the
marks and roughly 90% of the time-sink risk.

**Two methods, and picking the wrong one wastes minutes.** [Act VI's five questions](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md)
descend a *dependency stack* — does the API server answer, then the runtime, then the kubelet, then
the disk — and are for when the cluster itself is sick. [Act VII's six questions](../networking-fundamentals/act-7-workloads/diagnose.md)
walk the *claim chain* — is there a Pod, does it have a node, is the container running, is it in the
Service — and are for when the cluster is fine and a workload is not. Read the symptom for which one
it is before starting: `kubectl get nodes` answering normally means you want the second.

---

## Cluster Architecture, Installation and Configuration — 25%

The domain that changed most in 2025, and now the only one with real holes left — all of them
clustered around RBAC and building a cluster from bare machines.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Manage role based access control (RBAC) | ❌ **gap — the largest one left** | — planned for Act X. See the note below | `-` |
| Prepare underlying infrastructure for installing a Kubernetes cluster | ❌ gap | — `kind` cannot teach this honestly; needs two VMs | `-` |
| Create and manage Kubernetes clusters using kubeadm | 🟡 partial | Act VI reads a *real* kubeadm cluster from the inside — [static pods](../networking-fundamentals/act-6-control-plane/02-static-pods.md) · [the cluster's own PKI](../networking-fundamentals/act-6-control-plane/04-the-clusters-own-pki.md) (`kubeadm certs check-expiration`/`renew`) · [etcd backup and restore](../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md). A genuine `kubeadm init` + `join` is not done | `-` |
| Manage the lifecycle of Kubernetes clusters | ✅ covered | [upgrades and version skew](../networking-fundamentals/act-6-control-plane/06-upgrades-and-version-skew.md) — skew derived rather than memorised, half an upgrade done by hand, `upgrade plan`/`apply`/`node` | `-` |
| Implement and configure a highly-available control plane | ❌ gap | — one control-plane node in the lab | `-` |
| **Use Helm and Kustomize to install cluster components** | ✅ covered | [shipping a set of objects](../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) — both, contrasted; see the drill warning below | `-` |
| **Understand extension interfaces (CNI, CSI, CRI, etc.)** | ✅ covered | CNI [in depth](../networking-fundamentals/act-5-kubernetes/05-cni.md) · CRI via `crictl` throughout [Act VI](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md) · CSI derived from the `ExternalExpanding` event in [storage](../networking-fundamentals/act-7-workloads/06-storage.md) | `-` |
| **Understand CRDs, install and configure operators** | ✅ **covered, above exam depth** | [adding a kind](../networking-fundamentals/act-7-workloads/09-adding-a-kind.md) — write a CRD, discover it adds no behaviour, then write the controller in shell | `-` |

> **On RBAC:** this is now the single biggest hole between you and a pass, and it is worth being
> blunt about the arithmetic — it is one bullet of eight in a 25% domain, so perhaps 3% of the marks,
> but it is also the domain's most commonly reported task. [Act VII's CRD lesson](../networking-fundamentals/act-7-workloads/09-adding-a-kind.md)
> lays the groundwork by making `status` a separate subresource *because permissions can differ*, but
> the four-object model (Role, ClusterRole, RoleBinding, ClusterRoleBinding) and
> `kubectl auth can-i` are genuinely untaught. Until Act X lands, drill this externally — it is
> small, self-contained, and entirely on an allowed doc.

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
[The lesson](../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) builds a base and an overlay using every one of
those fields except `secretGenerator`, and flags the three deprecated spellings (`bases:`,
`patchesStrategicMerge:`, `patchesJson6902:`) you will meet in existing repositories. What it does
*not* do is make you fast, and this is the competency where speed decides the mark — so re-type the
overlay from a blank directory a few times rather than re-reading it.

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

**Fully covered**, and Act VII goes past exam depth on most of it.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Understand application deployments and how to perform rolling update and rollbacks | ✅ **above exam depth** | [Pod → ReplicaSet → Deployment](../networking-fundamentals/act-7-workloads/01-pod-to-deployment.md) · [rolling updates](../networking-fundamentals/act-7-workloads/02-rolling-updates.md) — `maxSurge`/`maxUnavailable` rounding, and why `rollout undo` is *not* an undo log | `-` |
| Use ConfigMaps and Secrets to configure applications | ✅ **above exam depth** | [configuration](../networking-fundamentals/act-7-workloads/05-configuration.md) — env vs mounted file, the `..data` swap, `subPath` silently never reloading, and the three plaintext locations | `-` |
| **Configure workload autoscaling** | ✅ covered | [choosing the number](../networking-fundamentals/act-7-workloads/10-choosing-the-number.md) — HPA, and the reason a Deployment made by a one-liner can never scale | `-` |
| Understand the primitives used to create robust, self-healing, application deployments | ✅ covered | [probes](../networking-fundamentals/act-7-workloads/03-probes.md) — readiness, liveness and startup, with the outage each one causes when swapped · [the other workload kinds](../networking-fundamentals/act-7-workloads/07-the-other-workload-kinds.md) | `-` |
| **Configure Pod admission and scheduling (limits, node affinity, etc.)** | ✅ **above exam depth** | [scheduling](../networking-fundamentals/act-7-workloads/04-scheduling.md) — `requests` vs `limits` and their different enforcers, QoS, `nodeSelector`/affinity, taints and tolerations, `topologySpreadConstraints`, and the auto-added `tolerationSeconds: 300` | `-` |

**Small-detail losses candidates report**, and where the course already addresses each:

- **The container name in `kubectl set image` must match exactly.** And it is not the name you
  expect: [lesson 01](../networking-fundamentals/act-7-workloads/01-pod-to-deployment.md) shows that `kubectl run` names the container
  after the *Pod* while `kubectl create deployment` names it after the *image*.
- **Changing a ConfigMap does not restart Pods.** [Lesson 05](../networking-fundamentals/act-7-workloads/05-configuration.md) explains
  precisely which half updates and which cannot; `kubectl rollout restart` is the exam answer, and
  [lesson 08](../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md)'s `configMapGenerator` hash is the production one.
- **Unmentioned taints silently blocking scheduling.** [Lesson 04](../networking-fundamentals/act-7-workloads/04-scheduling.md) drills
  reading the whole `FailedScheduling` tally — the per-reason counts must add up to the node count,
  and a node missing from that arithmetic is one you forgot was excluded.

---

## Storage — 10%

**Fully covered**, in one lesson that answers a question Act I posed six acts earlier.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| **Implement storage classes and dynamic volume provisioning** | ✅ covered | [three promises called "survives"](../networking-fundamentals/act-7-workloads/06-storage.md) — `WaitForFirstConsumer` derived rather than quoted, and `allowVolumeExpansion` accepted-then-ignored | `-` |
| Configure volume types, access modes and reclaim policies | ✅ covered | [storage](../networking-fundamentals/act-7-workloads/06-storage.md) — `emptyDir` vs PVC, `ReadWriteOnce` as *one node* not one Pod, `Delete` vs `Retain` | `-` |
| Manage persistent volumes and persistent volume claims | ✅ covered | [storage](../networking-fundamentals/act-7-workloads/06-storage.md) · [`volumeClaimTemplates` and why scale-down keeps volumes](../networking-fundamentals/act-7-workloads/07-the-other-workload-kinds.md) | `-` |

**The precise binding rule**, which resolves most "why won't my PVC bind" tasks: a PVC binds when
**capacity ≥ request AND accessModes match AND storageClassName matches**. Check those three before
anything else.

---

## Honest summary

| Domain | Weight | Course covers |
|---|---|---|
| Troubleshooting | 30% | 4½ of 5 bullets, two of them above exam depth |
| Cluster Architecture | 25% | 4½ of 8 bullets — the gaps are RBAC, HA, and bare-metal install |
| Servicing and Networking | 20% | 6 of 6 bullets, most above exam depth |
| Workloads and Scheduling | 15% | 5 of 5 bullets, most above exam depth |
| Storage | 10% | 3 of 3 bullets |

Roughly **85% of the CKA syllabus** is now covered, and what remains is concentrated and nameable:

| Gap | Domain share | Why it is still open |
|---|---|---|
| **RBAC** | ~3% | Needs the identity material planned for Acts IX–X. The most commonly reported of the three. |
| **HA control plane** | ~3% | The lab has one control-plane node. |
| **`kubeadm init` / `join` from bare machines** | ~3% | `kind` nodes arrive already provisioned; this needs two VMs. |
| **`kubectl logs` as a subject** | ~1% | Used constantly, never taught deliberately. |

**And the honest caution, which has not changed.** Coverage is not readiness. This course will make
you understand Kubernetes considerably better than a typical CKA holder, and it will not make you
*fast* — 15–20 hands-on tasks in two hours is decided by recall and typing speed. The load-bearing
remaining work is [`kubectl-speed.md`](kubectl-speed.md), re-typing manifests from a blank file, and
a timed simulator. Two killer.sh sessions ship with your exam registration; they are the only
environment that reproduces the SSH-per-task structure, and using both is worth more per hour at
this point than any further reading.
