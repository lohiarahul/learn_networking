# Act VII in the wild — the act that transfers completely

Act VI's in-the-wild page had to open with an apology: on a managed cluster, most of what that act taught you to *look at* is hidden. No `/etc/kubernetes/manifests`, no `ca.key`, no etcd.

This act has no such problem, and it is worth understanding why, because the reason is structural rather than lucky.

Everything in Act VII is an **object in the API**. Not a file on a control-plane node, not a certificate, not a process you can only see with a shell — a document you POST and read back. And the API is the one part of a managed cluster that is identical everywhere, because it is the product. **So this act is the most portable thing you have learned since sockets.**

| What Act VII taught | On EKS / GKE / AKS |
|---|---|
| Deployment, ReplicaSet, `pod-template-hash` | **Identical.** Same controller, same fields, same behaviour. |
| Rolling updates, `maxSurge`/`maxUnavailable`, `rollout undo` | **Identical**, including the revision numbers going forwards. |
| Probes, and the readiness→EndpointSlice chain | **Identical.** |
| `requests`/`limits`, QoS, the scheduler's ledger | **Identical** — and it matters more, because you are paying for the nodes. |
| Taints, tolerations, affinity, `topologySpreadConstraints` | **Identical**, and the zone labels are finally real. |
| ConfigMap/Secret, the `..data` swap, `subPath` not reloading | **Identical.** Same kubelet, same 60-second sync. |
| StatefulSets, `volumeClaimTemplates`, scale-down keeping PVCs | **Identical** — and now the retained volumes have a monthly price. |
| DaemonSets, Jobs, CronJobs | **Identical.** |
| Helm, Kustomize | **Identical.** They were always client-side. |
| CRDs and controllers | **Identical**, and you will meet dozens you did not install. |
| HPA arithmetic, `actual ÷ requests` | **Identical**, but metrics-server is usually already there. |
| **The default StorageClass** | **The one real difference**, and it changes an answer. |

## The one thing that changes, and it changes a promise

Lesson 06 was careful about this and it is worth restating as the single most important production consequence of the act. Your lab's `local-path` provisioner makes a directory on one named node. A cloud provider's default StorageClass makes a **network volume** — an EBS volume, a persistent disk — which is a different machine entirely.

Both are used through an *identical* PVC manifest. What changes is which of the three promises you get:

```bash
kubectl get storageclass
kubectl get sc -o custom-columns=NAME:.metadata.name,PROV:.provisioner,BINDING:.volumeBindingMode,EXPAND:.allowVolumeExpansion
```

Run that on any cluster you are handed, before you write a PVC. Three things to read off it:

- **The provisioner** tells you whether your data survives the machine. `rancher.io/local-path` or anything with `local` in it: no. `ebs.csi.aws.com`, `pd.csi.storage.gke.io`, `disk.csi.azure.com`: yes.
- **`allowVolumeExpansion`** is almost always `true` in the cloud and was absent in your lab. So growing a PVC actually works there — and lesson 06's "accepted and then nothing happens" becomes "accepted and then a CSI driver does it," which is the behaviour the abstraction was promising all along.
- **`volumeBindingMode`** is usually still `WaitForFirstConsumer`, and for a sharper reason than in your lab: a network volume in one availability zone cannot be attached to a node in another. The scheduler and the provisioner have to agree, and the only way to guarantee that is to place the Pod first.

That last point is where the act's cross-zone content stops being theoretical. `topologySpreadConstraints` across zones and a zonal PVC are in direct tension: spread your StatefulSet across three zones and each member's disk is welded to its zone, so a member can never move to a different one. That is usually correct and always worth knowing you chose.

## Where the money is

Three of this act's findings are, in a managed cluster, line items on an invoice.

**Requests are a purchase order.** The ledger from lesson 04 is what the Cluster Autoscaler reads to decide how many machines to buy. So an inflated `requests.cpu` does not merely fail to schedule — it *buys a node*. The single most common cost problem in real clusters is requests set by copying a manifest, and the second is requests set to equal limits because someone read that `Guaranteed` is safest. Both are paid monthly, forever, and neither produces an alert.

**Orphaned PVCs are silent.** Lesson 06 and lesson 07 both ended on this and it is the same finding twice: scaling a StatefulSet down keeps its volumes, and deleting a StatefulSet keeps them too. Nothing warns you, nothing shows up in `kubectl get pods`, and the disks bill until someone runs:

```bash
kubectl get pvc -A --sort-by=.metadata.creationTimestamp
```

Anything old with no Pod referencing it is either a deliberate keep or money.

**Finished Jobs accumulate.** Without `ttlSecondsAfterFinished`, every completed Job and its Pods stay in the API forever. On a cluster with a busy CronJob this reaches tens of thousands of objects, and the cost is not storage — it is that every `kubectl get pods` and every controller's cache gets slower, and etcd's object count is a real limit.

## The CRDs you did not install

Lesson 09 gave you the procedure and this is where you spend it. A real cluster has dozens of custom kinds, and nobody documents them:

```bash
kubectl api-resources --api-group='' -o name | wc -l      # the built-ins
kubectl get crd -o custom-columns=NAME:.metadata.name,GROUP:.spec.group | head -30
```

You will typically find some subset of: `cert-manager.io` (Certificate, Issuer), `gateway.networking.k8s.io` (Act V's), `argoproj.io` (Application, Rollout), `external-secrets.io`, `karpenter.sh` (NodePool — a Cluster Autoscaler replacement), `keda.sh` (ScaledObject — an HPA that scales on queue depth), and one or two written in-house by someone who has left.

For each one the questions are lesson 09's, and the fifth is still the one people skip:

```bash
CRD=certificates.cert-manager.io
kubectl explain certificate.spec --recursive | head -20
kubectl get crd $CRD -o jsonpath='{.spec.versions[*].name}{"\n"}'
kubectl get certificates -A
kubectl get pods -A | grep -i cert-manager        # WHOSE loop is this?
```

**An object of a custom kind with an empty `status` and no events means nobody looked.** In a lab that means you forgot to install the controller. In production it usually means the controller is CrashLooping, was uninstalled while its objects were left behind, or is running with RBAC that forbids it from writing status — and the last of those is genuinely hard to see until you know that `status` is a separate subresource with separate permissions.

The worst version of this is a CRD whose controller was removed. The objects remain, perfectly valid, and everything about them looks fine. There is no signal anywhere in the API that the thing which gave them meaning is gone.

## The habits worth keeping

Three things from this act are worth doing every time, in any cluster, and none of them takes a minute.

**Read the StorageClass before writing a PVC.** One command, and it tells you which of three durability promises you are about to receive.

**`kubectl get pvc -A` after anything involving a StatefulSet.** It is the only place the cluster remembers replicas you no longer run.

**Render before you apply.** `helm template` and `kubectl kustomize` produce the exact bodies that are about to be POSTed, locally, harmlessly. Almost every "the tool did something unexpected" story is a story about somebody who did not look.

And one habit of thought, which is really the act's spine turned into a diagnostic reflex. When a workload misbehaves, the cluster is almost never broken. **A claim is being kept faithfully that you did not mean to make** — so the question is never "what is wrong with Kubernetes" but *which loop is reading which field, and is that the field I wrote?*

---

↑ **[Act VII overview](README.md)** · Prev: **[Diagnose it](diagnose.md)**
