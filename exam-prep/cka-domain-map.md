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

The largest domain, and the one where time bleeds. Four of the five bullets are covered — three of them
above exam depth — and the course carries two independent diagnostic methods, one for a broken
*cluster* and one for a broken *workload*. It is the best-verified domain in the map, and since the
[drill verifiers](../drills/README.md) landed it is the only domain where the repo checks *your*
answer rather than its own prose.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Troubleshoot clusters and nodes | ✅ **covered, above exam depth** | [node maintenance](../networking-fundamentals/act-6-control-plane/07-node-maintenance.md) · [when the control plane breaks](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md) — the five-question descent, `journalctl -u kubelet`, `crictl` · [the drills](../networking-fundamentals/act-6-control-plane/diagnose.md), where **drills 9–11 are the canonical form of this bullet**: one `NotReady` symptom, three causes, and a two-field branch that decides the repair. `Ready=Unknown` means nobody is reporting — a dead kubelet, containers still serving on their Pod IPs, the heartbeat-vs-transition gap as `--node-monitor-grace-period`, `ready=false` endpoints explaining the refusal, and a 300-second `NoExecute` clock. `Ready=False` means the kubelet is alive and naming its own failing subsystem, so read the message: a missing CNI config is on disk and no kubelet restart will fix it, while `container runtime is down` is `crictl` unable to dial the socket — and there the `containerd-shim` processes keep every container running and serving while every question about them fails, so rebooting the node converts a control-plane outage into a real one | `-` |
| Troubleshoot cluster components | ✅ **covered, above exam depth** | [when the control plane breaks](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md) — a deliberately broken static-pod manifest, plus `crictl ps -a` / `crictl logs` with the apiserver down · [eleven drills](../networking-fundamentals/act-6-control-plane/diagnose.md), each ending in a `verify-drill.sh` run that exits 0 only if the cluster is functionally repaired **and** you named the cause | `-` |
| Monitor cluster and application resource usage | ✅ **covered, above exam depth** | [choosing the number](../networking-fundamentals/act-7-workloads/10-choosing-the-number.md) — metrics-server installed and made to fail first, `kubectl top`. [Act VII drill 10](../networking-fundamentals/act-7-workloads/diagnose.md) adds the half that monitoring cannot see: three workloads killed or slowed by **three different enforcers**, only one of which is Kubernetes. `OOMKilled`/`137` is the kernel's OOM killer against `memory.max`; the silent one is the kernel's CFS bandwidth controller, visible *only* as `nr_throttled` in `cpu.stat` on the node and in no Kubernetes object whatsoever; `Evicted` is the kubelet's eviction manager, and it is the only one with a `.status.reason` because it is the only one that made a decision. The asymmetry to carry: **`limits.memory` kills you, `limits.cpu` slows you down**. [Act XI lesson 03](../networking-fundamentals/act-11-observability/03-a-number-a-process-keeps.md) now traces `kubectl top`'s own path past this bullet's exam depth — the three separate kubelet metrics endpoints, and the `metrics.k8s.io` APIService that proxies sideways through the aggregation layer to a cache in metrics-server's memory rather than to etcd. Mechanism, not new exam coverage | `-` |
| Manage and evaluate container output streams | ✅ covered | [Act VII drill 8](../networking-fundamentals/act-7-workloads/diagnose.md) treats it as a subject where it actually matters — a `CrashLoopBackOff` whose reason exists **only** in the logs, on a two-container Pod, so `kubectl logs` silently defaults to the first container and says so (dangerous the day the broken one is second), then `-c`, `--all-containers --prefix`, `logs -l` across Pods, and the standing rule that a non-zero `RESTARTS` means run `--previous` before believing the Pod is healthy. Plus `crictl logs` throughout [Act VI](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md) for when the API server cannot answer | `-` |
| Troubleshoot services and networking | ✅ **covered, above exam depth** | [the five-question method](../networking-fundamentals/act-5-kubernetes/08-debugging.md) · [a worked failure](../networking-fundamentals/act-5-kubernetes/09-debugging-walkthrough.md) · [four drills](../networking-fundamentals/act-5-kubernetes/diagnose.md), each ending in a `verify-drill.sh` run that exits 0 only if a **new** Pod carries traffic to the Service by name *and* you named the cause. The pair worth the hour is drills 2 and 3: the identical symptom — an instant refusal through a Service, `200` straight to the Pod IP — from two different causes, told apart by one object. `kubectl get endpoints` prints `<none>` for both; the EndpointSlice shows **no addresses** (a selector matching nothing) versus **addresses present with `ready: false`** (a readiness probe holding a healthy app out of its own Service). Either way kube-proxy has nothing to DNAT to and installs a `REJECT`, which is why the failure is instant rather than a timeout — and why a silence in drill 4 means a filter, not a Service | `-` |

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

The domain that changed most in 2025, and the one with the most words spent on it — six ✅ and two 🟡
across eight bullets. What is left is an honest lab limit (a real HA control plane needs machines this
authoring environment did not have) and the in-place upgrade, which the course derives on a live
cluster but cannot make you do on three nodes. Helm's repository workflow used to be the third item
here; [lesson 08c](../networking-fundamentals/act-7-workloads/08c-when-the-chart-is-not-yours.md)
closed it.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Manage role based access control (RBAC) | ✅ covered | [Act IX lesson 06](../networking-fundamentals/act-9-identity/06-rbac-and-abac.md) builds the four-object model from scratch and computes the reverse question against a live cluster; [Act X lesson 07](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) adds the Node authorizer and `NodeRestriction`. See the note below for the one exam-shaped gap. | `-` |
| Prepare underlying infrastructure for installing a Kubernetes cluster | ✅ **covered — but read the caveat** | [two machines, from nothing](../networking-fundamentals/act-6-control-plane/09-two-machines-from-nothing.md) does exactly this bullet and does it the course's way: swap, `br_netfilter`, the three sysctls and the container runtime are each **earned from the failure that happens without them** rather than listed. The two worth knowing cold are the ones that do not fail loudly — a cgroup-driver mismatch that **neither component notices** (both are correct; the disagreement is between them), and a missing `bridge-nf-call-iptables`, which lets `kubeadm init` succeed and then makes ClusterIP DNAT quietly not happen for same-node traffic only. **The caveat: this is the one page in the course its author has not run**, because it needs two VMs and a hypervisor. Its outputs are expected rather than measured and the page says so at the top | `-` |
| Create and manage Kubernetes clusters using kubeadm | ✅ **covered — with the same caveat** | Act VI reads a *real* kubeadm cluster from the inside — [static pods](../networking-fundamentals/act-6-control-plane/02-static-pods.md) · [the cluster's own PKI](../networking-fundamentals/act-6-control-plane/04-the-clusters-own-pki.md) (`kubeadm certs check-expiration`/`renew`) · [etcd backup and restore](../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) — and [two machines, from nothing](../networking-fundamentals/act-6-control-plane/09-two-machines-from-nothing.md) now performs the `init` and the `join`. The part of that worth the hour is not the commands: it is that `join` carries **two secrets pointing in opposite directions** (the token authenticates the node to the cluster; the `--discovery-token-ca-cert-hash` authenticates the cluster to the node, over a connection the node cannot yet verify), which is Act VIII's trust-the-first-key problem with the only available answer — you do not derive the first key, you carry it. **Not author-verified**, per the page's own banner | `-` |
| Manage the lifecycle of Kubernetes clusters | ✅ **covered — with the same caveat** | [upgrades and version skew](../networking-fundamentals/act-6-control-plane/06-upgrades-and-version-skew.md) derives the skew rules rather than memorising them, runs `kubeadm upgrade plan` for real, and covers the failure the skew table cannot predict — a release **removing** an API, found *before* an upgrade with `apiserver_requested_deprecated_apis` (note that `kubectl convert` is **not part of `kubectl`** and should not be planned around). What it could not do was the in-place upgrade itself, because a `kind` node's binaries come from its image. [two machines, from nothing](../networking-fundamentals/act-6-control-plane/09-two-machines-from-nothing.md) now runs it: `upgrade apply` on the control plane, `upgrade node` on the worker, `drain`/`uncordon` around each kubelet restart, and `apt-mark hold` on all three packages — with the note that **the one command name that differs between a control-plane node and a worker is the difference between the task passing and the task doing nothing**. **Not author-verified** | `-` |
| Implement and configure a highly-available control plane | 🟡 **partial — the reasoning, not the build** | [etcd backup and restore](../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) now closes the half that does not need a second node: `member list` and `endpoint health --cluster` as the first two commands, the majority table (1→0, 2→0, 3→1, 4→1, 5→2) and therefore why an even size buys nothing, why losing quorum is *worse* than filling the disk (no leader means linearizable reads fail too, so it is not read-only, it is silent), why `member remove` comes before `member add`, what `IS LEARNER` is for, and how a multi-member restore differs — same snapshot, per-member `--name` and peer URL, shared `--initial-cluster-token`. What is still missing is the build: stacked vs external etcd, a load balancer in front of `controlPlaneEndpoint`, and `kubeadm join --control-plane`. That needs machines this lab does not have | `-` |
| **Use Helm and Kustomize to install cluster components** | ✅ covered | [shipping a set of objects](../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md) contrasts both and is good on what templating *is*, and it runs `helm install`, `list`, `upgrade`, `rollback`, `template`, `uninstall` and `get values` against a chart from `helm create`. The repository workflow is covered too, and not in Act VII — **Act X installs three public charts for real**: [Cilium](../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md) (`helm repo add`, then `install --version 1.19.7 --set`, then `upgrade --reuse-values`), [Falco](../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md) (`install --version 9.1.0 --namespace falco --create-namespace`) and [External Secrets](../networking-fundamentals/act-10-cluster-security/11-secrets-from-outside.md). That is the whole task shape, done three times, on charts that have to actually work afterwards. And [lesson 08c](../networking-fundamentals/act-7-workloads/08c-when-the-chart-is-not-yours.md) closes the half that used to be missing, on charts you did not write: `helm pull --untar` as the reading primitive, the six read-only verbs in [kubectl-speed](kubectl-speed.md), and **`--skip-crds` derived rather than memorised** — `crds/` is not templated (a `{{ .Chart.Version }}` reaches etcd verbatim), is never touched by `helm upgrade`, and survives `helm uninstall`. Then the measurement that matters for the reported task shape: cert-manager, external-secrets and ingress-nginx have **no `crds/` at all**, so on them `--skip-crds` does nothing and the answer is `--set crds.enabled=false`. Plus `--dry-run` being client-side (only `--dry-run=server` resolves `lookup`), subchart value scoping, and hooks. [Drills 11 and 12](../networking-fundamentals/act-7-workloads/diagnose.md) make it a fix under a clock: an upgrade that reports success with the CRD unchanged, and `another operation is in progress` with nothing in progress | `-` |
| **Understand extension interfaces (CNI, CSI, CRI, etc.)** | ✅ covered | CNI [in depth](../networking-fundamentals/act-5-kubernetes/05-cni.md) · CRI via `crictl` throughout [Act VI](../networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md) · CSI derived from the `ExternalExpanding` event in [storage](../networking-fundamentals/act-7-workloads/06-storage.md) | `-` |
| **Understand CRDs, install and configure operators** | ✅ **covered, above exam depth** | [adding a kind](../networking-fundamentals/act-7-workloads/09-adding-a-kind.md) — write a CRD, discover it adds no behaviour, then write the controller in shell | `-` |

> **On RBAC:** this was the largest hole in the map and [Act IX](../networking-fundamentals/act-9-identity/README.md)
> closed it — the summary table at the foot of this page no longer lists RBAC as an open gap, only as
> a speed gap. The four-object model (Role, ClusterRole, RoleBinding, ClusterRoleBinding), the scope
> that is not one of them, `kubectl auth can-i --as`, and the reverse question — *who can do this* —
> are all built from first principles, and [Act VII's CRD lesson](../networking-fundamentals/act-7-workloads/09-adding-a-kind.md)
> still lays the groundwork by making `status` a separate subresource *because permissions can differ*.
>
> What remains is speed, not understanding, and it is worth naming because understanding is not the
> thing being graded here. Lesson 06 now shows the stored form of all four objects — `Role`,
> `ClusterRole`, `RoleBinding` and `resourceNames` — via `--dry-run=client -o yaml`, plus the two
> fields whose failures are silent (`roleRef.name` and `subjects[].namespace`). So the shape is
> familiar. What the course cannot give you is the clock: the exam wants a working Role and binding in
> about four minutes. Drill `kubectl create role`/`clusterrole`/`rolebinding`/`clusterrolebinding
> --verb --resource --resource-name`, each one piped through `--dry-run=client -o yaml` so you also
> practise reading what you produced, and `auth can-i --as=system:serviceaccount:ns:sa` to check your
> own work. It is one bullet of eight in a 25% domain, so perhaps 3% of the marks, but it is also the
> domain's most commonly reported task.

### Helm and Kustomize — the most-named weak spot

Both were promoted into this domain in 2025 from a vague "awareness of manifest management" bullet,
and `helm.sh/docs` being a whitelisted exam doc confirms they are genuinely examined.

**Helm** — reported task shapes: add a repo and render a manifest; **install a chart while excluding
CRDs** (`--skip-crds`); `helm template`. Candidates report charts "failing silently without specific
flags." Drill: `repo add`/`update`, `search repo`, `show values`, `install --set`/`-f`, `--dry-run`,
`template`, `upgrade --install`, `history`/`rollback`, `--skip-crds`, `-n --create-namespace`.

Three things to have straight before the clock starts, all measured in
[lesson 08c](../networking-fundamentals/act-7-workloads/08c-when-the-chart-is-not-yours.md):

- **`helm template` omits `crds/` entirely.** If the task says "render the manifest" and the chart has
  a `crds/` directory, you need `--include-crds` — and `helm install` has no such flag, because it
  installs them by default.
- **`--skip-crds` only skips a `crds/` directory.** Charts that render CRDs from `templates/` behind a
  value ignore it. Check which convention the chart uses (`ls <chart>` after `helm pull --untar`)
  before answering an "exclude the CRDs" task; the answer may be `--set crds.enabled=false`.
- **`--dry-run` is client-side.** A chart containing `lookup` renders differently under `--dry-run`
  than it installs. `--dry-run=server` is the one that sees the cluster.

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

**Act V's home domain, and the course's strength — but read the two 🟡 rows below carefully.**
Connectivity, Services, Ingress and NetworkPolicy are at or above exam depth. Gateway-API-**with-TLS**
and CoreDNS-as-a-**server** are where this domain stops being enough on its own, and both are small,
specific, one-evening gaps rather than missing topics.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| Understand connectivity between Pods | ✅ **above exam depth** | [the Pod as a shared netns](../networking-fundamentals/act-5-kubernetes/02-pod-networking.md) · [CNI](../networking-fundamentals/act-5-kubernetes/05-cni.md) | `-` |
| **Define and enforce Network Policies** | ✅ covered | [NetworkPolicy](../networking-fundamentals/act-5-kubernetes/07-network-policy.md) for the model — selectors are additive, any policy makes its Pods default-deny for that direction, `policyTypes` is what decides, and a denial times out rather than returning 403 — then [the four shapes](../networking-fundamentals/act-5-kubernetes/07b-policy-shapes.md) for the authoring: `namespaceSelector` with `podSelector` in one peer vs two (the AND-vs-OR hyphen), `ipBlock` with `except` and why it may not share a peer, and a `policyTypes: [Egress]` default-deny including the DNS outage it causes and the `kubernetes.io/metadata.name` label that fixes it. Proved against a four-client bench on Calico, not asserted | `-` |
| Use ClusterIP, NodePort, LoadBalancer service types and endpoints | ✅ **above exam depth** | [Services and kube-proxy](../networking-fundamentals/act-5-kubernetes/03-services.md) · [Service shapes](../networking-fundamentals/act-5-kubernetes/04b-service-shapes.md) — headless, SRV, `sessionAffinity`, `ExternalName`, `externalTrafficPolicy` | `-` |
| **Use the Gateway API to manage Ingress traffic** | 🟡 **partial — the HTTPS listener is now authored, not run** | [Gateway API](../networking-fundamentals/act-5-kubernetes/06b-gateway-api.md) — `GatewayClass`/`Gateway`/`HTTPRoute`, the delegation model, weighted canary, and reading `.status`, all genuinely hands-on. Its only listener is `protocol: HTTP`: **`protocol: HTTPS`, `tls.mode` and `certificateRefs` appear nowhere**, and the reported task shape is *convert an Ingress into a Gateway plus HTTPRoute **with TLS***. Add an HTTPS listener with a `certificateRefs` Secret yourself | `-`. [the authoring sprint](authoring-sprint.md) item 4 adds the TLS half as an authoring task — `mode: Terminate` with `certificateRefs` as a list of object references, why `Passthrough` must carry none, and the `ReferenceGrant` a cross-namespace certificate needs. It is the one item on that page **not verified against a running cluster** and is marked as such | `-` |
| Know how to use Ingress controllers and Ingress resources | ✅ covered | [Ingress](../networking-fundamentals/act-5-kubernetes/06-ingress.md) | `-` |
| Understand and use CoreDNS | 🟡 **partial — and this row used to overclaim** | [CoreDNS](../networking-fundamentals/act-5-kubernetes/04-coredns.md) is thorough on the **resolver-client** side: `/etc/resolv.conf`, `ndots`, the search-domain walk, the FQDN forms, why a trailing dot changes the query count. It never touches the **server**: the `Corefile` does not appear in the course, the CoreDNS ConfigMap and Deployment are never read or edited, and `dnsConfig`/`hostAliases` appear nowhere. The exam surface for this bullet is the server config — `kubectl -n kube-system edit cm coredns` and back again | `-`. [the authoring sprint](authoring-sprint.md) item 3 closes the server side: the `Corefile` in its ConfigMap, a `rewrite` added and reverted, and the trap in verifying it — `busybox nslookup` answers `NXDOMAIN` for a name `dig +short legacy.internal.` resolves correctly, because `ndots:5` qualifies it against the search list first and busybox gives up on the first `NXDOMAIN` | `-` |

### The NetworkPolicy note — still the highest-value hour in this map

This used to be a gap and is now a lesson, which changes what to do with it rather than removing the
work. [The four shapes](../networking-fundamentals/act-5-kubernetes/07b-policy-shapes.md) writes and
measures all of the following on the policy-enforcing `netcni` cluster. Reading it once is not the
point — **type each of these from a blank file, on that cluster, until you stop having to think**:

1. **`namespaceSelector` and `podSelector` in ONE `from` element** — this means *a Pod matching
   \[that label\] **in** a namespace matching \[that label\]*. Both must hold.
2. **The same two selectors as TWO `from` elements** — this means *any Pod matching \[that label\]
   anywhere*, **OR** *any Pod at all in that namespace*. The YAML differs by two characters of
   indentation and the meaning is completely different. This is the most-cited technical failure
   across both exams, and it is a list-nesting question wearing a networking costume.
3. **`ipBlock` with `except`**, and **one `egress` policy** with `policyTypes: [Egress]` — including
   the trap that a default-deny egress policy breaks DNS until you allow UDP/53 to `kube-system`.

If you do one hour of manifest practice for CKA, do this hour. The lesson supplies the bench and the
four-client probe so that you are checking your work rather than trusting it — which is the difference
between having read about the AND-vs-OR trap and being immune to it.

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
| **Configure Pod admission and scheduling (limits, node affinity, etc.)** | 🟡 **partial — scheduling above depth, admission absent** | [scheduling](../networking-fundamentals/act-7-workloads/04-scheduling.md) is above exam depth on the scheduling half: `requests` vs `limits` and their different enforcers, QoS, `nodeSelector`/affinity, taints and tolerations, `topologySpreadConstraints`, the auto-added `tolerationSeconds: 300`. The **admission** half is now half-covered: `ResourceQuota` arrives in [Act VI drill 8](../networking-fundamentals/act-6-control-plane/diagnose.md), which is the more instructive way to meet it — a `pods: "1"` cap in a namespace you do not own, and a `kubectl scale` that reports `scaled` while the ReplicaSet's events carry the `exceeded quota` refusal, because the loop that was refused is not the one you typed at. `LimitRange` is created once, in [configuration](../networking-fundamentals/act-7-workloads/05-configuration.md). **`PriorityClass` still appears nowhere.** Namespace-scoped quota is a common task — practise `create quota` and `create priorityclass` as *authoring* rather than reading | `-`. [the authoring sprint](authoring-sprint.md) items 2 and 5 add the two authoring gaps. The `PriorityClass` one is worth the time for what the events say rather than the manifest: preemption **does not move the evicted Pod anywhere** — its Deployment's replacement replica stays `Pending` with `No preemption victims found`, because preemption only looks downward and the only Pods left are its own peers. A single high-priority Pod permanently costs a low-priority Deployment a replica, and nothing reads as unhealthy | `-` |

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

One lesson answers a question Act I posed six acts earlier, and it does the *reasoning* better than
most paid material. It also never asks you to **author** a `StorageClass` or a `PersistentVolume`,
which is what the exam asks for — so the smallest domain has the map's worst authored-vs-explained
ratio. Two manifests of practice close it.

| Sub-competency | Coverage | Where | Me |
|---|---|---|---|
| **Implement storage classes and dynamic volume provisioning** | ✅ covered | [three promises called "survives"](../networking-fundamentals/act-7-workloads/06-storage.md) and [Act VII drill 9](../networking-fundamentals/act-7-workloads/diagnose.md) cover the reading and the failure modes — `WaitForFirstConsumer` putting `nodeAffinity` on a PV, `ReadWriteOnce` proved to mean one *node*. The authoring half is closed by [the authoring sprint](authoring-sprint.md) item 1, which is where the two unguessable facts live: **the default class is an annotation, not a field**, and a cluster may not have two, so making one default means unmaking the other. The proof is a PVC that names no class and comes back carrying one | `-` |
| Configure volume types, access modes and reclaim policies | ✅ **covered, above exam depth** | [storage](../networking-fundamentals/act-7-workloads/06-storage.md) — `emptyDir` vs PVC, `ReadWriteOnce` as *one node* not one Pod, `Delete` vs `Retain`. [Act VII drill 9](../networking-fundamentals/act-7-workloads/diagnose.md) makes that RWO claim *fail and then work*: a second Pod on the other node is refused by the **PV's** `nodeAffinity` — a field nobody wrote, put there by `WaitForFirstConsumer` — and the same Pod moved onto the first node mounts the same volume and reads what the other wrote. It also separates the four layers a volume-shaped failure can live at, since only one of the four is a mount: `Pending` (scheduler), `ContainerCreating` (`FailedMount`, retried forever because a ConfigMap may exist later), `CreateContainerConfigError` (mounts fine, an env reference does not resolve), and a `CrashLoopBackOff` whose reason is `Read-only file system` on a ConfigMap volume that mounted perfectly | `-` |
| Manage persistent volumes and persistent volume claims | ✅ covered | [storage](../networking-fundamentals/act-7-workloads/06-storage.md) · [`volumeClaimTemplates` and why scale-down keeps volumes](../networking-fundamentals/act-7-workloads/07-the-other-workload-kinds.md) cover the PVC side and the binding *rules*. [Act VII drill 7](../networking-fundamentals/act-7-workloads/diagnose.md) is the exam task itself: author a `hostPath` PV, then put four claims against it and account for four different `Pending` states — capacity, `accessModes`, a `storageClassName` naming a class that does not exist, and one that is `Pending` **by design** because the class is `WaitForFirstConsumer`. Note the pair that matters: capacity and access-mode failures emit the *same* event, so the cluster never tells you which field lost | `-` |

**The precise binding rule**, which resolves most "why won't my PVC bind" tasks: a PVC binds when
**capacity ≥ request AND accessModes match AND storageClassName matches**. Check those three before
anything else.

---

## Honest summary

Counting a 🟡 as a half, and stating the arithmetic so you can check it:

| Domain | Weight | Course covers | ✅ | 🟡 | ❌ |
|---|---|---|---|---|---|
| Troubleshooting | 30% | **4½ of 5** — two above exam depth | 4 | 1 | 0 |
| Cluster Architecture | 25% | **7 of 8** — HA and the in-place upgrade are what is left | 6 | 2 | 0 |
| Servicing and Networking | 20% | **5½ of 6** — the Gateway HTTPS listener is authored but not run | 4 | 2 | 0 |
| Workloads and Scheduling | 15% | **5 of 5** | 5 | 0 | 0 |
| Storage | 10% | **3 of 3** | 3 | 0 | 0 |

That is **25 of 27 bullets** counted this way, so roughly **92% of the CKA syllabus** — up from 80%,
and the increase is worth reading carefully because it is not all the same kind of progress.

**Two different things closed those gaps, and one of them is weaker than the other.** Five bullets were
closed by [the authoring sprint](authoring-sprint.md), which was written *by doing it* — every item but
one was applied to the live two-node cluster and several of them turned up behaviour that reading the
manifests would not have (a `LimitRange` turning out to be the reason a `ResourceQuota` can enforce
anything; a Deployment reading `3/3` while its ReplicaSet carried the quota refusal). Those rows are as
solid as anything else in this map.

Three more were closed by
[the two-machines appendix](../networking-fundamentals/act-6-control-plane/09-two-machines-from-nothing.md),
and that page **has not been run by its author** — it needs two VMs and a hypervisor the authoring
environment did not have. It is careful, it is derived from `kubeadm`'s documented behaviour and from
the real `kind` cluster's own configuration, and it is marked as unverified at the top of the page and
in every row above that cites it. Treat those three bullets as *written* rather than *measured* until
you have run them yourself, which is the point of the banner.

The gap between explaining a thing and authoring it under a clock is still the whole difference, and it
is still where the remaining hours should go.

What remains is concentrated and nameable:

| Gap | Domain share | Why it is still open |
|---|---|---|
| **Building an HA control plane** | ~2% | The quorum reasoning is taught, and the appendix now reads `controlPlaneEndpoint` on a cluster that does not have one — which makes the trap legible (every certificate SAN and every kubeconfig names one machine, so it is a decision taken at the moment of least information). Actually *building* it still needs a third machine and a load balancer. |
| **Helm's read-only commands** (`repo update`, `search repo`, `show values`, `history`) | ~1% | Act X adds repos and installs three real charts; what is missing is the inspection half, which changes nothing and is therefore easy to skip and easy to be asked. |
| **Gateway API with TLS** (`certificateRefs`, `tls.mode`) | ~1% | Authored in the sprint, and the *only* sprint item not applied to a live cluster — the CRDs were unreachable from the authoring environment. The manifest shape and the three refusals are right; the outputs are expected. |
| **RBAC under a clock** | ~2% | Understood well, and the manifest shape is now taught — see the note in Cluster Architecture. What is left is typing speed, which only a timed simulator gives you. |
| **`kubectl logs` as a subject** | — | **Closed.** Act VII drill 8 teaches it where it matters: a `CrashLoopBackOff` whose reason exists only in the logs, on a two-container Pod, so `kubectl logs` silently picks the first container — then `-c`, `--all-containers --prefix`, `logs -l`, and `--previous` as a standing rule whenever `RESTARTS` is non-zero. |

**And the honest caution, which has not changed.** Coverage is not readiness. This course will make
you understand Kubernetes considerably better than a typical CKA holder, and it will not make you
*fast* — 15–20 hands-on tasks in two hours is decided by recall and typing speed. The load-bearing
remaining work is [`kubectl-speed.md`](kubectl-speed.md), re-typing manifests from a blank file, and
a timed simulator. Two killer.sh sessions ship with your exam registration; they are the only
environment that reproduces the SSH-per-task structure, and using both is worth more per hour at
this point than any further reading.
