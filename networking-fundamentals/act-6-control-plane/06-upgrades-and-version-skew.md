# Upgrades, and what is allowed to be out of step

Twice now you have stopped a control-plane component and started it again, and both times the thing that came back was identical to the thing that left. That is the easy case, and it is not the case a cluster spends its life in. Kubernetes ships a minor release every four months and supports each one for about a year, so a cluster that lives two years is upgraded five or six times — and an upgrade cannot stop the cluster while it happens.

Which means components must run at *different versions from each other*, on purpose, for the duration. So: which combinations are allowed, and what decides?

You are in an unusually good position to reason about this rather than look it up, because the last three lessons established the only fact that matters. No component in this cluster calls another one. They coordinate exclusively by reading and writing objects in one store.

> **Predict first —** given that components never speak to each other, what is the *actual* compatibility question during an upgrade? Not "can version A talk to version B" — there is no conversation. Say what it is instead, and then say which single component the others must all be measured against.

### There is no protocol between them, only a schema

The question is not whether two components can talk. It is whether an object written by one version is **legible to another version** — whether a field a new scheduler writes still means what an old kubelet thinks it means, and whether a field an old controller manager omits still has a sensible default when a new API server reads it.

That reframes everything. Compatibility is a property of the **stored objects**, not of the wires. And that immediately tells you which component is the reference point, because only one of them touches the store:

```bash
kubectl get --raw /version | head -c 200; echo
kubectl get nodes -o wide
```

The API server's version is the one everything else is measured against. It is the only component that reads and writes etcd, the only one that applies defaults and validates, and therefore the only one whose idea of what an object *is* has any authority. Every other component is a client of it — including the ones that ship in the same release and run on the same node.

From which the two rules follow without being memorised. **Nothing may be newer than the API server** — a newer component would write fields the API server does not know how to store, and there is no version of "store this field I do not understand" that is safe. And **things may be older, by an amount that depends on how hard they are to upgrade.**

### Where is a component's version actually written down?

> **Predict first —** you have read all four control-plane manifests. Which of the five processes on this node can you change the version of by editing a file, and which one cannot possibly work that way?

```bash
docker exec netlab-control-plane grep -h 'image:' /etc/kubernetes/manifests/*.yaml
docker exec netlab-control-plane kubelet --version
```

Four image tags, and one binary that reports its own version and has no manifest at all.

That asymmetry is the whole shape of a Kubernetes upgrade, and you established it in the static-pods lesson without knowing what it would cost you. The API server, scheduler, controller manager and etcd are **containers**, so their version is a string in a file — change the tag, and the kubelet you have been watching notices the file and starts a different image. The kubelet itself is a **package installed on the node**, started by systemd, and no amount of editing YAML will change it.

So an upgrade is two entirely different operations wearing one name. Editing four strings on the control-plane node, which is fast and reversible. And replacing a binary on every node in the cluster, which is neither — it is a package upgrade and a service restart, on a machine that is currently running your workloads.

Everything awkward about Kubernetes upgrades comes from that second half.

### The skew policy, and why the numbers differ

Now the numbers, which are a support policy rather than a law of physics, but a policy with a visible rationale:

| Component | Relative to the API server |
|---|---|
| Another API server (in an HA control plane) | within **1** minor version |
| `kube-controller-manager`, `kube-scheduler` | no newer; up to **1** minor older |
| `kubelet` | no newer; up to **3** minor older |
| `kube-proxy` | no newer; matches its node's kubelet window |
| `kubectl` (yours) | within **1** minor, either direction |

The interesting entry is the kubelet's three, and it is generous for exactly the reason the last section gave: it is the hard one. The scheduler and controller manager live next door to the API server on the same nodes and get upgraded in the same breath, so a one-version window is plenty. Kubelets live on every node you have, and upgrading one means draining the work off it first. A cluster with hundreds of nodes cannot do that in an afternoon, so the policy grants enough room to roll through them over several releases if it must. (It was two versions until Kubernetes 1.28, and was widened precisely because that was not enough room.)

`kubectl` is the one that catches people, because it is on *your* laptop and nobody upgrades a cluster to match it. It is also the only entry allowed to be newer, and the failure is soft and confusing rather than loud: commands mostly work, and then one silently omits a field or fails to parse an object it has never seen a version of.

```bash
kubectl version
```

Read both lines. If the minor versions differ by more than one, that is worth fixing before you debug anything else — a `kubectl` two versions off is an unreliable witness, and an unreliable witness is the worst possible tool for the work this act is about.

### So what does an upgrade actually look like?

The order is forced by the rule that nothing may be newer than the API server: **the control plane goes first, always.** Upgrade a kubelet first and it is briefly newer than the API server it reports to, which is the one combination the policy flatly forbids.

`kubeadm` drives it, and it will tell you the plan before doing anything:

```bash
docker exec netlab-control-plane kubeadm upgrade plan
```

This reaches out to find which versions exist, compares them against what you are running, and prints a table of components with a `CURRENT` and a `TARGET` column — plus, usefully, the manual step it will *not* do for you. If your lab has no network access it will fail at the version lookup; that is the command's own network call failing, not your cluster.

Then, on the control-plane node:

```
kubeadm upgrade apply v1.36.2      # rewrites the four manifest image tags, upgrades addons
```

and on every other node:

```
kubeadm upgrade node               # upgrades that node's kubelet config and local components
```

Neither of those is the whole job, and the gap is the same gap as in the last lesson: `kubeadm` writes files. `kubeadm upgrade apply` rewrites the image tags in `/etc/kubernetes/manifests/`, and the kubelet notices and restarts the containers — the mechanism you proved by hand in lesson 02. But `kubeadm upgrade node` does *not* replace the kubelet binary, because the kubelet binary is a package. That step is yours: upgrade the package, then restart the service, on each node in turn.

Which is why the real per-node sequence has a step this act has not taught you yet:

```
1. drain the node                  <- move the work off it first
2. upgrade the kubeadm package
3. kubeadm upgrade node
4. upgrade the kubelet + kubectl packages
5. restart the kubelet service
6. uncordon the node               <- let work come back
```

Steps 1 and 6 are the ones you cannot yet do, and they are the entire subject of the next lesson. Note what they are *for*: an upgrade restarts the kubelet, and while the kubelet is restarting nothing on that node is being managed. Every Pod on it is running unsupervised, and any that dies stays dead until the kubelet returns. Draining first is how you make that interval boring.

This lesson deliberately does not run `kubeadm upgrade apply` on your lab. Not because it is dangerous in the way the etcd restore was — it is well-behaved — but because a `kind` node's Kubernetes packages come baked into its image rather than from a package manager, so steps 2, 4 and 5 above have nowhere to happen. A real in-place upgrade needs real machines, and it is the one thing in this act that your lab cannot honestly show you.

What your lab *can* show you is the mechanism underneath, which is the part worth owning:

> **Check yourself —** Without running `kubeadm` at all, describe how you would change the version of `kube-scheduler` on this cluster, using only what lesson 02 taught you. Then say why the same approach cannot work for the kubelet, and what that implies about which half of an upgrade is the risky half.

<details>
<summary>Answer</summary>

Edit the `image:` tag in `/etc/kubernetes/manifests/kube-scheduler.yaml`. The kubelet is watching that directory, notices the file changed, and starts a container from the new tag — the same watch-and-converge you used to stop and start the scheduler by moving its file. If the new image is broken or missing, you edit the tag back, and the recovery is as fast as the break. That is genuinely all `kubeadm upgrade apply` does to those four components.

It cannot work for the kubelet because the kubelet is not described by any file in that directory — it is the process *reading* that directory. It is a binary on the node's filesystem started by systemd, so changing its version means changing the installed package and restarting the service. There is no manifest to edit and no controller watching on your behalf.

Which locates the risk precisely. The control-plane half is four string edits on one node, each independently reversible in seconds, with a component that has no state to lose. The node half touches every machine you have, requires the work to be moved off each one first, and involves a service restart during which that node is unmanaged. The control plane is the part that sounds frightening and the nodes are the part that takes the week.

</details>

<!-- figure -->

```
   WHY THE API SERVER IS THE REFERENCE

     no component calls another. they only read/write OBJECTS.
     so compatibility = "is this object legible to that version?"
     and only ONE component reads and writes the store.

                     [ API server ]  <- the version everything is measured against
                       ^   ^   ^  ^
        never newer ---+   |   |  +--- kubectl   +/- 1  (yours; the one that drifts)
        than it:           |   |
          scheduler / controller-manager   up to 1 older   (next door, upgraded together)
          kubelet / kube-proxy             up to 3 older   (everywhere, hard to upgrade)

   WHERE A VERSION LIVES

     /etc/kubernetes/manifests/*.yaml   image: ...:v1.36.1   <- 4 strings, in a file
        |                                                       edit -> kubelet restarts it
        |                                                       reversible in seconds
        v
     the kubelet itself .............. a PACKAGE on the node, run by systemd
                                          no manifest. no controller watching.
                                          package upgrade + service restart, per node,
                                          after draining the work off it.

   ORDER IS FORCED: control plane first (nothing may be newer than the API server).
```

> **You understand this when you can** explain what "version skew" is actually about in a system where no component calls another, and derive from that alone why the API server is the reference and why nothing may be newer than it; say where each of the five processes on a control-plane node records its version, and which one cannot be changed by editing a file; and give the per-node upgrade order, naming the interval that draining exists to make safe.

**Which raises:** two steps of that sequence are still missing, and they are the two that touch running workloads rather than binaries. Moving every Pod off a node sounds like it should be one command — but the Pods have opinions, some of them are supposed to run on every node including this one, and something in the cluster is allowed to refuse. What actually happens when you tell a node to stop working?

---

← Prev: **[Losing the cluster, and getting it back](05-etcd-backup-and-restore.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Taking a node out of service](07-node-maintenance.md)** →
