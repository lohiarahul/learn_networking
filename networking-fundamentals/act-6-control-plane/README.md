# Act VI — The cluster that runs itself

Act V left you able to debug a cluster's whole network path from first principles, and carefully never mentioned who was arranging any of it. kube-proxy "watches the API server." The kubelet "writes `/etc/resolv.conf`." A CNI plugin is "invoked when a Pod is scheduled." Scheduled by whom? Watched from where? Every lesson in that act leaned on a machine it declined to open.

This act opens it — and the surprise is how little is in there.

There is no orchestrator. No component in Kubernetes calls another component. There is one document store, a set of processes that each watch it for one specific discrepancy and act on that discrepancy alone, and a convention that they coordinate by editing fields on shared objects rather than by talking. That is the entire architecture. Once you have seen it, most Kubernetes failures stop being mysterious and become a question of *which loop is not running*, which is a question with a short list of answers.

You already have the shape of it. In Act I, `/proc` turned out to be a filesystem interface answered by running code rather than by fetching bytes. Here the same trick is played across a fleet: a tree of paths, a fixed set of verbs, and processes behind them. Act I's resolution — that *"everything is a file" is a claim about the interface, not a claim that bytes exist anywhere* — is the thing this act cashes in.

## The lab for this act

The same `kind` cluster as Act V. If you have it, you are ready; if not, [the Act V lab lesson](../act-5-kubernetes/01-lab-with-kind.md) builds it in a minute.

One difference in character, though, and it is worth naming before you start. Act V's experiments read files. **This act's experiments stop things** — you will move a control-plane manifest out of its directory and watch a cluster lose an ability. Every such move has a matching restore in the text, but the responsibility is yours: if you stop reading mid-lesson, you leave a cluster with a component missing. The check is always the same one command, and it is worth making a habit of it before you close the terminal:

```bash
docker exec netlab-control-plane ls /etc/kubernetes/manifests/     # all four, every time
```

A cluster missing its scheduler looks completely healthy until the moment something needs placing.

## The lessons — read in this order

1. **[The API server is a filesystem](01-the-api-server-is-a-filesystem.md)** — go looking for a Pod on the node's disk, fail, and find the tree it actually lives in.
2. **[Static pods — where the control plane lives](02-static-pods.md)** — the API server is a Pod, so who starts it? The boot-order paradox, and the directory that breaks it.
3. **[The reconciliation loop](03-the-reconciliation-loop.md)** — stop a controller and watch a Deployment stop defending itself. Three loops, no calls between them.
4. **[The cluster's own PKI](04-the-clusters-own-pki.md)** — you have been authenticating with a file this whole time. Read what it claims about you, and find out what nothing can revoke.
5. **[Losing the cluster, and getting it back](05-etcd-backup-and-restore.md)** — snapshot the store, delete a namespace for real, and put it back. Then work out what a restore does *not* undo.
6. **[Upgrades, and what is allowed to be out of step](06-upgrades-and-version-skew.md)** — derive the skew rules from the fact that no component calls another, and find where a version is actually written down.
7. **[Taking a node out of service](07-node-maintenance.md)** — cordon is one field; drain is a loop in your terminal. Then meet the one request the cluster is allowed to refuse.
8. **[When the control plane breaks](08-when-the-control-plane-breaks.md)** — Act V's five questions, pointed down the dependency stack instead of the network stack. Break the API server on purpose and find out where the evidence went.

> **Act VI is not finished.** Lessons 1–4 are written and **verified command-by-command on a real cluster**. Lessons 5–8 are written but **not yet verified** — treat their timings and exact output as provisional, and expect a command or two to need adjusting. Still to come: this act's `test-yourself`, `diagnose` and `in-the-wild` pages, which every other act carries and this one does not yet. **The act's supporting pages do not exist yet either** — every other act carries a `test-yourself`, a `diagnose` set of on-call drills and an `in-the-wild`, and this one will when it is finished. The roadmap banner in [the journey map](../../JOURNEY-MAP.md) tracks what is real.

## What breaks here

Two failure modes, and they are opposites.

The first is the one Act V's Gateway API lesson planted: **an object the cluster stores but nobody reconciles.** A Deployment that wants three replicas and has two. A Pod that is `Pending` with no node. In both cases the record is perfect and the loop is absent, and no amount of staring at the YAML will show you that — because the YAML is right. The instinct this act builds is to ask *which process should have acted on this, and is it running?* before asking what is wrong with the manifest.

The second is the mirror image: **an object nobody is reconciling from.** A static Pod you delete comes straight back, and not because a loop rescued it — because the loop that owns it is reading a file on a node and has never cared what the API says. There the authority is elsewhere, and the mistake is editing the wrong copy.

Underneath both sits the sharpest problem of all: the tool you would normally reach for to investigate a broken control plane is `kubectl`, which talks to the control plane. When the API server is what is down, your whole Act V toolkit goes quiet at once. Everything in this act that works by reading files on a node — `kubeadm certs check-expiration`, the manifest directory, the kubelet's own config — works precisely because it needs no cluster. The diagnostic lesson that finishes this act goes further down still, to the container runtime and the kubelet's logs.

> **The question to carry forward:** if no component calls another, what is left to break — and what does the wreckage look like when the thing that broke is the thing you would use to look?
