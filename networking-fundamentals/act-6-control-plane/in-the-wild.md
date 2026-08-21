# Act VI in the wild — the control plane you are not allowed to see

Every other act's in-the-wild page points at your own machine. This one cannot, and the reason is the most useful thing on the page: **on every managed Kubernetes service — EKS, GKE, AKS — the four things this act taught you to read are hidden from you on purpose.** No `/etc/kubernetes/manifests`, no `ca.key`, no etcd, no node you can `ssh` into to run `crictl`.

That sounds like the act was wasted on you. It is the opposite. What you learned is exactly the thing that lets you work out **which half of a managed cluster is yours** — and the boundary is drawn precisely along the lines this act drew.

## The line is drawn where you would now draw it

Look at what a managed provider takes and what it leaves, and it is the act's own split:

| What Act VI taught | On a managed cluster |
|---|---|
| The API server as a tree of paths | **Yours.** Identical. Every `kubectl`, every `--raw`, every object. |
| The reconciliation loops | **Yours** to reason about; not yours to stop. |
| Static Pods in `/etc/kubernetes/manifests` | **Gone.** No node runs them, and no API exposes them. |
| etcd, and its snapshot | **Gone.** You cannot back it up, and you cannot lose it. |
| `ca.key` and the cluster PKI | **Gone.** You get certificates; you never hold the authority. |
| The kubelet and `crictl` on a node | **Node-dependent.** Sometimes reachable, often deliberately not. |
| `cordon` / `drain` / PDBs | **Entirely yours.** These are the same commands, on the same objects. |

The rule underneath: **everything that was a file on a control-plane node is theirs; everything that was an object in the store is yours.** That is not a coincidence of packaging. It is the same boundary the act kept pointing at — the store versus the disk — being sold to you as a product.

Which reframes the whole act as a purchase decision you can now evaluate. The reason managed Kubernetes is worth paying for is *specifically* lesson 05: etcd is the one component with durable state, the one whose loss is unrecoverable, and the one whose backup nobody tests until the morning they need it. You are buying the elimination of that problem. And the reason it costs you something is lesson 08: when the control plane misbehaves, Questions 3, 4 and 5 are gone, and you are left at Question 2 filing a support ticket.

## What you can still read on someone else's cluster

Quite a lot, and it is worth knowing which of your commands survive. Point `kubectl` at any cluster you have access to — managed, work, someone else's — and try these.

*Concept:* the API server is a tree of paths, and that part is never taken away.

```bash
kubectl get --raw /readyz?verbose | tail -20
kubectl get --raw /version
kubectl api-resources | wc -l
```

`/readyz` works on a managed cluster, and it is the one place the provider's control plane still reports on itself to you. A failing `etcd` line there is the difference between "my cluster is broken" and "raise it with them" — and knowing that distinction is worth the price of a support call.

*Concept:* your identity is a credential, and its shape tells you which kind of cluster you are on.

```bash
kubectl config view --raw --minify -o jsonpath='{.users[0].user}' | head -c 200; echo
kubectl auth whoami
```

On the lab cluster that printed two base64 blobs — a client certificate, as lesson 04 taught. On a managed cluster you will usually find an `exec` block instead, invoking `aws eks get-token` or `gke-gcloud-auth-plugin`, which fetches a short-lived **token** rather than presenting a certificate.

That difference is worth a moment, because it is lesson 04's uncomfortable finding being fixed. A certificate cannot be revoked — the API server checks a signature and two dates and consults no list of cancelled credentials. A token *can* be, because the thing that issued it is still running and can be asked. Every managed provider moved off certificates for exactly the reason that lesson made you feel.

*Concept:* the reconciliation loops are still there, and their absence still shows the same way.

```bash
kubectl get events -A --sort-by=.lastTimestamp | tail -20
kubectl get deployment -A -o custom-columns=\
'NS:.metadata.namespace,NAME:.metadata.name,WANT:.spec.replicas,READY:.status.readyReplicas'
```

That second command is Drill 2 as a habit. A `READY` that does not match `WANT` on a managed cluster means the same thing it meant in the lab, and comparing `status` against a real `get` is a reflex worth keeping wherever you are.

*Concept:* node maintenance is unchanged, and it is the part of this act you will use most often at work.

```bash
kubectl get nodes -o wide          # the VERSION column is each node's kubelet
kubectl get pdb -A                 # ALLOWED DISRUPTIONS: 0 is tomorrow's stuck drain
```

`cordon`, `drain`, `--ignore-daemonsets`, `--timeout` and PodDisruptionBudgets are identical on every cluster in the world, because they are objects and a client-side loop rather than anything on a control-plane node. Lesson 07 transfers completely.

## On your Mac: Docker Desktop's Kubernetes is a real kubeadm cluster

If you enable Kubernetes in Docker Desktop, you get something closer to the lab than to a managed service — and you can prove the act's central claims against it without `kind` at all:

```bash
kubectl config use-context docker-desktop
kubectl -n kube-system get pods -l tier=control-plane
kubectl get --raw /api/v1/namespaces/kube-system/pods/etcd-docker-desktop | head -c 200; echo
```

Four control-plane components, as Pods, in `kube-system`. Same architecture, same names.

Getting to the *files*, though, shows you the twist Act IV already prepared you for: there is no `ssh`, because those manifests live inside the Linux VM that Docker Desktop runs, not on macOS. The act's node commands need a shell in that VM rather than on your laptop, which is the same "one layer down" boundary [Act IV's in-the-wild page](../act-4-one-pretends-many/in-the-wild.md) hit with namespaces. macOS has no `/etc/kubernetes`, no systemd for `journalctl -u kubelet`, and no `crictl` — because it has no kubelet.

Worth internalising rather than working around: on macOS, **Questions 3, 4 and 5 always need a shell somewhere else.** Whether that is a `docker exec` into a `kind` node, a VM, or an `ssh` to a real Linux machine, the descent below `kubectl` is a descent onto a Linux host. Every command in this act assumed one, and every command in this act still works the moment you have one.

## The one habit to keep

Whatever cluster you are on, in whatever job, the act's method survives being locked out of the bottom three questions:

> Ask *which loop should have acted on this, and is it running* — before asking what is wrong with the manifest.

On the lab cluster you answer that by moving a file. On a managed cluster you answer it by reading `status` against reality and knowing, when they disagree, that the problem is a process and not your YAML. The command changes. The question does not.

---

← **[Diagnose it](diagnose.md)** · ↑ **[Act VI overview](README.md)**
