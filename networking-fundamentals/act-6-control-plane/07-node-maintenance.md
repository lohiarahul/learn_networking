# Taking a node out of service

The upgrade sequence had six steps and you could do four of them. The two you could not were the first and the last: move the work off this node, and let it come back. They sound like the easy ones.

They are not, and the reason is that every other operation in this act moved a *file* or stopped a *process*. This one has to move **running workloads that other things depend on**, on a cluster that is still serving traffic, and it is the first operation in the act where the cluster is entitled to tell you no.

### Two different things that sound like one

> **Predict first —** you tell the cluster to stop scheduling new work onto a node. What happens to the Pods *already running* on it? Commit to an answer before you look, because the two commands ahead of you differ on exactly this point and people conflate them constantly.

```bash
kubectl get pods -o wide -A --field-selector spec.nodeName=netlab-worker | head
kubectl cordon netlab-worker
kubectl get nodes
```

`netlab-worker` now reads `Ready,SchedulingDisabled` — and every Pod on it is still running, untouched. **Cordon is a statement about the future only.** Nothing was moved, nothing was restarted, and no workload noticed.

Which raises the question this act always asks. What actually changed?

```bash
kubectl get node netlab-worker -o jsonpath='{.spec.unschedulable}{"\n"}'
kubectl describe node netlab-worker | grep -A2 Taints
```

**One boolean field, and a taint.** That is the entire mechanism. Lesson 03 showed you the scheduler as a loop that watches for Pods with an empty `spec.nodeName` and picks a node; cordon writes a field that makes this node ineligible for that choice. There is no cordon *process*, no cordon controller, nothing watching. You edited an object, and a loop that was already running reads it differently now.

So `kubectl uncordon` is the same write in reverse, and you can prove the whole thing is just a field by doing it yourself:

```bash
kubectl patch node netlab-worker -p '{"spec":{"unschedulable":true}}'
kubectl get nodes                      # still SchedulingDisabled -- same result, no new verb
kubectl uncordon netlab-worker
```

That is worth having done once. `cordon` is a convenience spelling for a one-field patch, and knowing that means you can never be stuck for want of the subcommand.

### Draining is not a field

Moving the existing Pods off is a different kind of operation entirely, and the difference is the interesting part of this lesson.

> **Predict first —** `kubectl drain` is one command. Is it one write to the API server, or many? And what do you expect to happen if you press Ctrl-C while it is running?

```bash
kubectl drain netlab-worker --dry-run=client
```

Try it for real and read the error, because the error is the lesson:

```bash
kubectl drain netlab-worker
```

It refuses, and it names two objections. It will not touch Pods managed by a **DaemonSet**, and depending on what you have running it may refuse over Pods with local scratch storage.

You have met a DaemonSet without the name. Act V's Services lesson had kube-proxy running on *every* node, rewriting that node's iptables; the CNI plugin was installed the same way. A DaemonSet is exactly that shape as an object — one Pod per node, by construction. Which is why draining cannot evict them: the whole point of such a Pod is that it runs *here*, and moving it elsewhere is meaningless. There is nowhere for it to go.

So you tell drain that you understand:

```bash
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data
```

`--delete-emptydir-data` is you accepting that any Pod using a scratch directory whose lifetime is the Pod's own will lose that data. Both flags are acknowledgements rather than behaviour changes: drain is refusing to make an irreversible decision on your behalf, and the flags are you making it.

Now watch what it actually did:

```bash
kubectl get pods -A -o wide --field-selector spec.nodeName=netlab-worker
kubectl get pods -A -o wide | grep -c Pending
```

The DaemonSet Pods are still there. Everything else is gone — and here is the part that matters on a two-node cluster: the replacements are **`Pending`**. There is exactly one other node, it is the control plane, and Act V taught you that it carries a `NoSchedule` taint. You have just cordoned the only node that would take the work.

That is not a flaw in the lab, it is the operation's actual cost made visible. A drain does not relocate Pods. It **deletes** them and lets the reconciliation loops from lesson 03 create replacements wherever the scheduler can put them — and if the scheduler cannot put them anywhere, they wait. Draining a node in a cluster with no spare capacity is an outage you performed on purpose.

### So what *is* drain?

```bash
kubectl uncordon netlab-worker
kubectl get pods -A -o wide --field-selector spec.nodeName=netlab-worker | head
```

Give it a moment and the work returns, because uncordoning removed the taint and the loops did the rest. Now answer the prediction.

**Drain is a loop running inside `kubectl` on your laptop.** It lists the Pods on the node, then asks the API server to evict them one at a time, waiting for each to go. There is no drain object in the store, no drain controller, and no record that a drain is in progress. Press Ctrl-C and it stops exactly where it was: the node stays cordoned, some Pods evicted, some not, and nothing anywhere will finish the job.

This is the sharpest instance in the act of the thing the act keeps insisting on. Everything else you have watched — a replacement Pod, a scheduled node assignment, a re-registered static Pod — happened because a process in the cluster wanted the world to match an object. Drain is the opposite: **a script, outside the cluster, issuing one request per Pod.** If your terminal closes, the operation simply stops existing.

Which tells you what to do when a drain hangs: it is *your* command that is stuck, waiting for one specific eviction that is not completing. So find out which Pod, and ask why that one.

### The thing that is allowed to say no

Eviction is not deletion. It is a distinct request — a write to a Pod's `eviction` subresource — and it is the one write in this whole act that the API server may **refuse on policy grounds**.

The policy is an object, and it is the last new kind this act introduces:

```bash
kubectl -n kube-system get poddisruptionbudget
kubectl create deployment web --image=hashicorp/http-echo --replicas=2 -- /http-echo -text=web -listen=:5678
kubectl wait --for=condition=Available deployment/web --timeout=90s
```

A **PodDisruptionBudget** says how much of an application may be missing *at once, voluntarily*. Create one that is deliberately impossible to satisfy:

```bash
kubectl create poddisruptionbudget web-pdb --selector=app=web --min-available=2
kubectl get pdb web-pdb
```

Two replicas, and a budget insisting all two stay available.

> **Predict first —** with that budget in place, you drain the node those Pods are on. What happens — does the drain evict them anyway, fail immediately, or something else? And how would you tell the difference between "blocked" and "slow"?

```bash
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=60s
```

It **blocks, retrying, and then times out.** Not an immediate error — the eviction request is rejected with `Cannot evict pod as it would violate the pod's disruption budget`, and `kubectl` treats that as *not yet* rather than *no*, because in the normal case it genuinely is: a rolling update in progress would clear in seconds. Your budget will never clear, so it retries until the timeout you supplied.

Which is why `--timeout` belongs on every drain you run interactively. Without it, the default behaviour is to wait indefinitely, and a drain that has been sitting there for forty minutes looks identical to a drain that is nearly finished.

And note the word *voluntarily* in what a PDB governs. It constrains eviction, which is a request. It does not constrain a node catching fire, a `kubectl delete pod`, or a kubelet dying — none of those ask permission. A PDB is a contract about **planned** disruption only, and reading it as a general availability guarantee is the most common way to be disappointed by one.

```bash
kubectl delete pdb web-pdb
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=60s   # now completes
kubectl uncordon netlab-worker
```

> **Check yourself —** You are draining a node during a planned upgrade. It has been running for twenty minutes with no output. Give the order you would investigate in, and say what each step distinguishes.

<details>
<summary>Answer</summary>

First, remember whose loop is stuck: the drain is running in your terminal, not in the cluster, so there is no controller to inspect and no status field to read. The evidence is on the node.

**Which Pods are left?** `kubectl get pods -A -o wide --field-selector spec.nodeName=<node>`. Whatever is still listed, minus the DaemonSet Pods, is the set your drain is waiting on — usually exactly one. That single name is the whole investigation, and everything after this step is about it.

**Is it blocked or is it slow?** Try the eviction yourself and read the answer, or look at the Pod's events. A disruption budget refusing you says so explicitly, and the fix is a conversation about the budget — either the application genuinely cannot lose a replica right now, or the budget is wrong. If nothing is refusing, the Pod is being deleted and is taking its time, which is a different problem: a long `terminationGracePeriod`, or a container ignoring the signal to stop.

**Is a replacement even possible?** `kubectl get pods -A | grep Pending`. If the evicted Pods have nowhere to go, the drain may well "succeed" and leave you worse off than before. On a cluster at capacity, checking this *before* draining is the difference between maintenance and an incident.

The general shape: a drain is a client-side loop over evictions, so a stuck drain is always one specific eviction, and an eviction is the one request in Kubernetes that something is allowed to refuse. Find the Pod, then find out whether you were refused or merely kept waiting.

</details>

<!-- figure -->

```
   CORDON                                    DRAIN

   one field:  spec.unschedulable: true      a LOOP IN YOUR TERMINAL
   + a NoSchedule taint                        for each Pod on the node:
        |                                          POST pods/<name>/eviction
        v                                          wait for it to go
   the scheduler skips this node             no drain object. no controller.
   for FUTURE placement only                 no record it is happening.
   running Pods: untouched                   Ctrl-C = stops, half-done, forever

   nothing "does" a cordon.                  refuses by default on:
   you edited an object and a loop              DaemonSet Pods  (nowhere to go)
   that was already running reads it             --ignore-daemonsets
   differently now.                             emptyDir data   (irreversible)
                                                 --delete-emptydir-data

   EVICTION is not DELETION
     it is the one write the API server may REFUSE on policy:
         PodDisruptionBudget: "how much may be missing AT ONCE, VOLUNTARILY"
         refusal looks like SLOWNESS -- kubectl retries. always pass --timeout.
     a PDB does not constrain: node failure, kubectl delete pod, a dead kubelet.
     nothing asks its permission.

   drain DELETES Pods. the loops recreate them SOMEWHERE ELSE -- if anywhere exists.
   no spare capacity => you have performed an outage on purpose.
```

**Cleanup:**

```bash
kubectl delete deployment web
kubectl delete pdb web-pdb --ignore-not-found
kubectl uncordon netlab-worker
kubectl get nodes                                                  # both Ready, neither disabled
docker exec netlab-control-plane ls /etc/kubernetes/manifests/     # all four, as ever
```

> **You understand this when you can** say what `cordon` writes and why no process is needed to enforce it; explain why `drain` is not a field or a controller but a loop in your terminal, and what that implies for a drain you interrupt and for a drain that hangs; name the two things drain refuses to do without being told and why each refusal is the safe default; and say what a PodDisruptionBudget constrains, what it does *not*, and why being blocked by one looks like slowness rather than an error.

**Which raises:** you now have the whole planned-maintenance sequence, and every step of it assumed you could ask the cluster questions. But this act has broken the API server twice, and both times `kubectl` went silent along with it. A node that will not come `Ready`, a control-plane component that crash-loops, a cluster that answers nothing at all — what is left to look at, and in what order?

---

← Prev: **[Upgrades, and what is allowed to be out of step](06-upgrades-and-version-skew.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Act VI overview](README.md)** — the control-plane diagnostic walk is being written →
