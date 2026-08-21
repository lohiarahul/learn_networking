# Upgrades, and what is allowed to be out of step

Twice now you have stopped a control-plane component and started it again, and both times the thing that came back was identical to the thing that left. That is the easy case, and it is not the case a cluster spends its life in. Kubernetes ships a minor release every four months and supports each one for about a year, so a cluster that lives two years is upgraded five or six times — and an upgrade cannot stop the cluster while it happens.

Which means components must run at *different versions from each other*, on purpose, for the duration. So: which combinations are allowed, and what decides?

You are in an unusually good position to reason about this rather than look it up, because the last three lessons established the only fact that matters. No component in this cluster calls another one. They coordinate exclusively by reading and writing objects in one store.

> **Predict first —** given that components never speak to each other, what is the compatibility question during an upgrade actually *about*? Not "can version A talk to version B" — there is no A-to-B conversation to have. Say what you think is being compared instead, and then say which single component the others must all be measured against.

### Every component talks to one component, and only one of them writes

Start with the second half, because you can settle it from what you already own. Lesson 01 established that etcd is the only store. Lesson 04 showed you that the API server holds its own credential into that store, `apiserver-etcd-client`, and that no other component has one.

```bash
kubectl get --raw /version
kubectl get nodes -o wide
```

The `VERSION` column in that node listing is worth a second look, because it is not the cluster's version — **it is each node's kubelet version**, unlabelled. On your cluster all the numbers agree and the column looks redundant. On a cluster mid-upgrade it is the single most useful column in Kubernetes.

So there is exactly one component whose idea of what an object *is* has any authority: the one that decodes the stored bytes, applies defaults, validates, and writes them back. **The API server's version is the reference, and every other component — including the ones that ship in the same release and run on the same node — is a client of it.**

Which sharpens the first half. Each component does have a conversation, but always with the API server and never with a peer. So what varies across an upgrade is not a protocol between two components; it is whether the **object** one of them asks for or sends still exists in the form it expects. A version of Kubernetes serves a particular set of API groups and versions and understands a particular set of fields, and a client built against a different set may ask for something that has been removed or send something not yet recognised.

That is the real compatibility question, and it explains the asymmetry in the rules that follow. **Nothing may be newer than the API server**, because a newer component is built against an API that this server does not serve yet — it may ask for a resource version that does not exist here. **Things may be older**, because the API server deliberately keeps serving old versions for several releases so that exactly this can work; that grace is the whole reason a rolling upgrade is possible at all.

The one apparent exception is worth spotting rather than glossing over, because it tells you the rule is about *reach* rather than about newness being inherently unsafe. `kubectl` is allowed to be one version newer, and it gets away with it for a reason no in-cluster component can claim: it is a general-purpose client that discovers what the server supports before acting, and a human is watching when it does not. A controller in a reconciliation loop has neither property.

### Where is a component's version actually written down?

> **Predict first —** you have read all four control-plane manifests. Which of the five processes on this node can you change the version of by editing a file, and which one cannot possibly work that way?

```bash
docker exec netlab-control-plane sh -c "grep -h 'image:' /etc/kubernetes/manifests/*.yaml"
docker exec netlab-control-plane kubelet --version
```

Note the `sh -c` wrapper, which is doing real work: without it your *own* shell tries to expand `/etc/kubernetes/manifests/*.yaml` before `docker` ever runs, finds no such path on your laptop, and — in `zsh` — refuses to run the command at all. A glob has to be quoted so that it is expanded on the machine where the files actually are.

Four image tags, and one binary that reports its own version and has no manifest at all.

Write down the version you just saw, because the rest of this lesson uses `v1.36.x` as a stand-in and yours is probably different — `kind` installs whatever its own release pinned, so your cluster's version is a fact about the day you installed `kind`, not about anything you chose. Wherever a version appears below, substitute your own.

That asymmetry is the whole shape of a Kubernetes upgrade, and you established it in the static-pods lesson without knowing what it would cost you. The API server, scheduler, controller manager and etcd are **containers**, so their version is a string in a file — change the tag, and the kubelet you have been watching notices the file and starts a different image. The kubelet itself is a **package installed on the node**, started by systemd, and no amount of editing YAML will change it.

So an upgrade is two entirely different operations wearing one name. Editing four strings on the control-plane node, which is fast and reversible. And replacing a binary on every node in the cluster, which is neither — it is a package upgrade and a service restart, on a machine that is currently running your workloads.

Everything awkward about Kubernetes upgrades comes from that second half.

### The skew policy, and why the numbers differ

Now the numbers, which are a support policy rather than a law of physics, but a policy with a visible rationale:

| Component | Relative to the API server |
|---|---|
| `kube-controller-manager`, `kube-scheduler` | no newer; up to **1** minor older |
| `kubelet` | no newer; up to **3** minor older |
| `kube-proxy` (Act V's per-node iptables writer) | no newer; the same window as its node's kubelet |
| `kubectl` (yours) | within **1** minor, either direction |
| another API server, if you have more than one | within **1** minor of each other |

The interesting entry is the kubelet's three, and it is generous for exactly the reason the last section gave: it is the hard one. The scheduler and controller manager live next door to the API server on the same node and get upgraded in the same breath, so a one-version window is plenty. Kubelets live on every node you have, and upgrading one means draining the work off it first. A cluster with hundreds of nodes cannot do that in an afternoon, so the policy grants enough room to roll through them over several releases if it must. (It was two versions until Kubernetes 1.28, and was widened precisely because that was not enough room.) `kube-proxy` shares the kubelet's window for the same reason and by the same logic: it is on every node too, and it is upgraded when that node is.

The last row is a real cluster's shape rather than yours. This act has shown you *one* of each control-plane component, because that is what `kind` builds and it is enough to see the architecture — but nothing in the design says there must be one. A production cluster runs several API servers behind a load balancer, which is why they need a rule about each other at all, and it is also the reason the reconciliation lesson's leader election exists: several controller managers may be running while only one is permitted to act.

One thing the table does not say, and the last lesson's closing question asked: **for how long?** A skew window is a distance, but versions keep arriving — roughly one minor release every four months. So being three versions behind is not a stable state you can settle into; it is a position from which the next release makes you non-compliant without your touching anything. Three versions is about a year, and that is the real deadline the table encodes.

`kubectl` is the one that catches people, because it is on *your* laptop and nobody upgrades a cluster to match it. It is also the only entry allowed to be newer, and the failure is soft and confusing rather than loud: commands mostly work, and then one silently omits a field or fails to parse an object it has never seen a version of.

```bash
kubectl version
```

Read both lines. If the minor versions differ by more than one, that is worth fixing before you debug anything else — a `kubectl` two versions off is an unreliable witness, and an unreliable witness is the worst possible tool for the work this act is about.

### Do half an upgrade by hand

You do not have to take on faith that a control-plane component's version is just a string in a file. Change one, badly, and watch.

> **Predict first —** you edit the `image:` tag in `kube-scheduler.yaml` to a version that does not exist. Say what the kubelet does with that file, what `kubectl get pods` will show for the scheduler, and — the part that matters — whether you will be able to undo it.

```bash
CP=netlab-control-plane
docker exec $CP cp /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/sched.good
docker exec $CP sh -c "sed 's|\(image:.*kube-scheduler:\).*|\1v9.99.99|' /tmp/sched.good \
  > /etc/kubernetes/manifests/kube-scheduler.yaml"
sleep 30
kubectl -n kube-system get pods -l component=kube-scheduler
docker exec $CP crictl ps -a --name kube-scheduler
```

`ImagePullBackOff`, and an `AGE` that has reset — this is a new Pod record, not the old one having trouble. Notice the second command returns **nothing at all**: no container was created, because there is nothing to create one from.

Two things the kubelet did not do, both worth naming. It did not validate the tag before acting, and it did not keep the old container running as a fallback while it tried. It read a file and obeyed it, and the working scheduler you had thirty seconds ago is gone.

(Edit the file by writing a fresh copy rather than with `sed -i`, by the way. In-place editing creates a temporary file *in that directory*, and the kubelet — which does not care about file extensions — tries to run it, and complains in its log about a manifest neither of you meant to create. Lesson 02's warning about stray files in `/etc/kubernetes/manifests/` applies to your tools as much as to your backups.)

So the cluster now has no scheduler, which lesson 03 taught you is invisible until something needs placing. Undo it:

```bash
docker exec $CP cp /tmp/sched.good /etc/kubernetes/manifests/kube-scheduler.yaml
sleep 30
kubectl -n kube-system get pods -l component=kube-scheduler       # Running again
docker exec $CP rm -f /tmp/sched.good
```

Both directions take about the same fifteen seconds, which is the point: **that was an upgrade, and then a rollback.** A real one differs only in that the tag you write is a version that exists and you write four of them. Which is the useful thing to carry: the control-plane half of an upgrade is four string edits, each independently reversible in seconds, on components holding no state. It is the half that sounds frightening and isn't.

### So what does the whole thing look like?

The order is forced by the rule that nothing may be newer than the API server: **the control plane goes first, always.** Upgrade a kubelet first and it is briefly newer than the API server it reports to, which is the one combination the policy flatly forbids.

`kubeadm` drives it, and it will tell you the plan before doing anything:

```bash
docker exec netlab-control-plane kubeadm upgrade plan v1.37.0
```

Name a target version explicitly. Run bare, `kubeadm upgrade plan` goes looking for the newest release it knows about, discovers you are already on it, and prints four lines saying so and no table — which is correct and completely uninstructive. Given a version to aim at, it prints what you came for:

```
Components that must be upgraded manually after you have upgraded the control plane
COMPONENT   NODE                   CURRENT   TARGET
kubelet     netlab-control-plane   v1.36.1   v1.37.0
kubelet     netlab-worker          v1.36.1   v1.37.0

COMPONENT                 NODE                   CURRENT   TARGET
kube-apiserver            netlab-control-plane   v1.36.1   v1.37.0
kube-controller-manager   netlab-control-plane   v1.36.1   v1.37.0
kube-scheduler            netlab-control-plane   v1.36.1   v1.37.0
kube-proxy                                       1.36.1    v1.37.0
CoreDNS                                          v1.14.2   v1.14.2
etcd                      netlab-control-plane   3.6.8-0   3.6.8-0
```

Read that table against everything above it and it confirms the whole lesson. The kubelets are in a **separate table headed "must be upgraded manually"** — `kubeadm` is telling you outright which half of the job it declines to do, and it is the half that is a package rather than a string. `kube-proxy` and CoreDNS appear with no node, because they run *in* the cluster rather than on a node. And etcd and CoreDNS show `CURRENT` equal to `TARGET`: they have their own release cycles and are not renumbered along with Kubernetes.

This command needs the network, twice — once to look up what versions exist, and once for a preflight check that runs a throwaway Job in your cluster. In a sealed lab it fails at one of those, which is the command's own connectivity failing rather than anything wrong with your cluster.

The two commands below are **not for your lab** — read them, do not run them; the reason follows in a moment. On the control-plane node:

```
kubeadm upgrade apply v1.36.2      # rewrites the four manifest image tags
```

and on every other node:

```
kubeadm upgrade node               # rewrites that node's kubelet configuration
```

Neither of those is the whole job, and the gap is the same gap as in the last lesson: `kubeadm` writes files. `kubeadm upgrade apply` rewrites the image tags in `/etc/kubernetes/manifests/` — the edit you just made by hand — and the kubelet notices and restarts the containers. It also updates a handful of cluster-managed components that live *in* the cluster rather than in that directory, CoreDNS and kube-proxy among them; you have used both since Act V without ever asking who upgrades them, and the answer is this command.

But neither form replaces the kubelet binary, because the kubelet binary is a package. That step is yours: upgrade the package, then restart the service, on each node in turn.

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

This lesson deliberately does not run `kubeadm upgrade apply` on your lab, and the reason is worth one command rather than a claim. It is not that a `kind` node is missing a package manager — it has one:

```bash
docker exec netlab-control-plane dpkg -S /usr/bin/kubelet
docker exec netlab-control-plane sh -c 'ls /etc/apt/sources.list.d/'
```

`no path found matching pattern`, and a sources list mentioning only Debian. **The kubelet on this node is not a package at all.** It is a bare binary baked into the node image, with no Kubernetes repository configured to replace it from — so steps 2, 4 and 5 above have nowhere to happen, and the only way to change this kubelet's version is to rebuild the image.

That is a fact about `kind` specifically, and it is exactly the fact that makes a real in-place upgrade the one thing in this act your lab cannot honestly show you.

> **Check yourself —** You inherit a cluster. The API server is `v1.30`. Half the nodes run kubelet `v1.27` and half run `v1.30`. Your laptop's `kubectl` is `v1.33`. What is out of policy, in what order would you fix it, and which of these is *dangerous* as opposed to merely unsupported?

<details>
<summary>Answer</summary>

Two things are out of policy, and they are not equally urgent.

The `v1.27` kubelets are exactly three minors behind a `v1.30` API server, which is the edge of the window rather than outside it — legal today, and illegal the moment the control plane moves to `v1.31`. So it is not currently broken; it is a deadline. And it constrains the order of everything else: you cannot upgrade the control plane past `v1.30` until those nodes move, which is the reverse of the usual instinct. The rule that the control plane goes first is about a *single* upgrade step, not a licence to run ahead of your nodes.

Your `kubectl` at `v1.33` is three ahead of the server and genuinely out of policy, and it is the one to fix first — not because it is the most dangerous, but because it is the cheapest and because **everything else on this list is a diagnosis you are about to make with that tool.** A client three versions off may quietly misrender or omit fields, so every conclusion you draw before fixing it is suspect. Fix your witness before you take testimony.

As for danger: none of it is *dangerous* in the sense of losing data. The kubelets at the window's edge are a scheduled problem. The `kubectl` skew is a correctness problem in your own understanding, which is worse than it sounds, because it produces confident wrong answers rather than errors. The genuinely dangerous move is the one nobody has made yet: upgrading the control plane to `v1.31` to "get current" and thereby putting half the fleet out of support in one command.

</details>

<!-- figure -->

```
   WHY THE API SERVER IS THE REFERENCE

     no component talks to a PEER. every one of them talks to the API server.
     and only ONE of them reads and writes the store.
     so skew is not "A vs B" -- it is "does this server still serve
     the API this client was built against?"

                     [ API server ]  <- the version everything is measured against
                       ^   ^   ^  ^
        never newer ---+   |   |  +--- kubectl   +/- 1   discovers what the server
        than it:           |   |                          supports, and a human is
          scheduler / controller-manager   1 older        watching. no controller
                              (next door, upgraded together)   can claim either.
          kubelet / kube-proxy             3 older
                              (everywhere, needs a drain per node)

     3 older ~= a year, at one minor release every 4 months.
     the window is a DEADLINE, not a resting place.

   WHERE A VERSION LIVES

     /etc/kubernetes/manifests/*.yaml   image: ...:v1.XX.Y  <- 4 strings, in a file
        |                                                       edit -> kubelet restarts it
        |                                                       reversible in seconds
        v
     the kubelet itself .............. a PACKAGE on the node, run by systemd
                                          no manifest. no controller watching.
                                          package upgrade + service restart, per node,
                                          after draining the work off it.

   ORDER IS FORCED: control plane first (nothing may be newer than the API server).
```

> **You understand this when you can** say why the API server is the version everything else is measured against, arguing it from which component holds a credential into the store rather than from having been told; explain why `kubectl` is allowed to be newer when a controller is not, and why "three versions behind" is a deadline rather than a resting place; say where each of the five processes on a control-plane node records its version, and — having changed one and put it back — which one cannot be changed by editing a file at all; and give the per-node upgrade order, naming the interval that draining exists to make safe.

**Which raises:** two steps of that sequence are still missing, and they are the two that touch running workloads rather than binaries. Moving every Pod off a node sounds like it should be one command — but the Pods have opinions, some of them are supposed to run on every node including this one, and something in the cluster is allowed to refuse. What actually happens when you tell a node to stop working?

---

← Prev: **[Losing the cluster, and getting it back](05-etcd-backup-and-restore.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Taking a node out of service](07-node-maintenance.md)** →
