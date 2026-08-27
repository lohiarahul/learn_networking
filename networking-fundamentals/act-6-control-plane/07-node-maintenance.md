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

**One boolean field — and a taint.** `spec.unschedulable: true`, and `node.kubernetes.io/unschedulable:NoSchedule`. (Read that taint's name carefully against the one you will meet in a moment on the control plane, `node-role.kubernetes.io/control-plane`. They differ by a hyphen and a word, and they are completely different things.)

So `kubectl uncordon` is the same write in reverse, and you can prove the whole thing is a field by doing it yourself:

```bash
kubectl patch node netlab-worker -p '{"spec":{"unschedulable":true}}'
kubectl get nodes                      # still SchedulingDisabled -- same result, no new verb
```

`cordon` is a convenience spelling for a one-field patch, and knowing that means you can never be stuck for want of the subcommand.

But "one field and a taint" is two things, and you have only accounted for one of them. Who wrote the taint?

> **Predict first —** you already know how to remove a controller from this cluster. If you stop the controller manager and *then* cordon a node, what appears — the field, the taint, both, or neither? And what will `kubectl get nodes` say?

```bash
kubectl uncordon netlab-worker
docker exec netlab-control-plane sh -c 'mv /etc/kubernetes/manifests/kube-controller-manager.yaml /tmp/'
sleep 20
kubectl cordon netlab-worker
kubectl get node netlab-worker -o jsonpath='{.spec.unschedulable}{"  taints="}{.spec.taints}{"\n"}'
kubectl get nodes
```

**The field is `true`. The taints are empty. And `kubectl get nodes` still says `SchedulingDisabled`.**

So `cordon` never wrote that taint. It wrote one field, and a controller inside the controller manager was watching for that field and reconciling it into a taint — which is why with the controller gone, the taint never appears. Put it back and watch it arrive on its own:

```bash
docker exec netlab-control-plane sh -c 'mv /tmp/kube-controller-manager.yaml /etc/kubernetes/manifests/'
sleep 40
kubectl get node netlab-worker -o jsonpath='{.spec.taints}{"\n"}'      # the taint, unprompted
kubectl uncordon netlab-worker
```

Which makes this lesson's opening claim true **twice over**, and it is worth saying precisely. There is no cordon process — but there *is* a controller doing part of the work you would naturally credit to `kubectl`. You wrote one field; the scheduler reads that field, and a separate loop translates it into a taint for everything else that reasons about taints. Two independent watchers, one write, and lesson 03's shape underneath both.

Notice the third detail as well: `kubectl get nodes` printed `SchedulingDisabled` even with no controller running, because that column is rendered from the **field**, not the taint. The display was honest the whole time about the only thing you actually did.

### Draining is not a field

Moving the existing Pods off is a different kind of operation entirely, and the difference is the interesting part of this lesson.

Give the node some work of your own first, so that what you are about to move is yours rather than the cluster's:

```bash
kubectl create deployment web --image=hashicorp/http-echo --replicas=3 -- /http-echo -text=web -listen=:5678
kubectl wait --for=condition=Available deployment/web --timeout=90s
kubectl get pods -l app=web -o wide
```

All three landed on `netlab-worker`, and it is worth knowing why before you drain it. Read the *other* node:

```bash
kubectl describe node netlab-control-plane | grep -A2 Taints
```

`node-role.kubernetes.io/control-plane:NoSchedule`. Act V mentioned this in passing — a parenthetical explaining why a Pod could not be on the control plane — and here it is as an actual field on an actual object. Note that it is a **different** taint from the one `cordon` just added to the worker: this one is permanent and set at install time, that one was yours and temporary. Both say `NoSchedule`, and confusing them is easy.

So this cluster has exactly one node that will accept ordinary work. Hold on to that.

> **Predict first —** `kubectl drain` is one command. Is it one write to the API server, or many? And what do you expect to happen if you press Ctrl-C halfway through?

Ask drain what it intends to do, without doing any of it:

```bash
kubectl drain netlab-worker --dry-run=client
```

It refuses, and it never gets as far as telling you — which is a better first result than the one you asked for. It has one objection and it names the Pods:

```
node/netlab-worker cordoned (dry run)
error: unable to drain node "netlab-worker" due to error: cannot delete DaemonSet-managed Pods
(use --ignore-daemonsets to ignore): kube-system/kindnet-..., kube-system/kube-proxy-...
```

A **DaemonSet** is a workload kind that means *one Pod on every node, by construction*, and you have been relying on two of them since Act V without meeting the name. `kube-proxy` is one: it runs on every node, watching Services and rewriting that node's iptables. (Act V introduced it as a daemon on each node and left how it got there alone. This is how.) The other is your CNI. Draining cannot evict either, because the entire point of such a Pod is that it runs *here* — there is nowhere for it to go, and nothing gained by removing it.

Note that a *dry run* told you this. Nothing was touched: the field is unset, there are no taints, and all three Pods are where they were. Worth knowing, because the same refusal from a real `kubectl drain` **cordons the node before it fails** — so anyone who runs the bare command "just to see the error" has quietly disabled scheduling on it.

Now say you understand, still without doing it:

```bash
kubectl drain netlab-worker --dry-run=client --ignore-daemonsets
```

```
node/netlab-worker cordoned (dry run)
Warning: ignoring DaemonSet-managed Pods: kube-system/kindnet-..., kube-system/kube-proxy-...
evicting pod default/web-... (dry run)
evicting pod default/web-... (dry run)
evicting pod default/web-... (dry run)
node/netlab-worker drained (dry run)
```

**One line per Pod.** A list, not an instruction — which is your answer to the first half of the prediction: whatever drain is, it operates per Pod.

Now do it:

```bash
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=120s
```

`--delete-emptydir-data` is you accepting that a Pod using a scratch directory whose lifetime is the Pod's own will lose that data. On this cluster nothing uses one, so the flag changes nothing — keep it anyway, because the habit is the point: both flags are **acknowledgements** rather than behaviour changes. Drain refuses to make an irreversible decision on your behalf, and a flag is you making it.

It finishes in about a second, which is too fast to watch. So watch the requests instead:

```bash
kubectl uncordon netlab-worker
kubectl wait --for=condition=Available deployment/web --timeout=90s
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=120s -v=6 2>&1 \
  | grep -i eviction
```

```
pod/web-... eviction started
I... "Response" verb="POST" url="https://127.0.0.1:PORT/api/v1/namespaces/default/pods/web-.../eviction" status="201 Created"
I... "Response" verb="POST" url="https://127.0.0.1:PORT/api/v1/namespaces/default/pods/web-.../eviction" status="201 Created"
I... "Response" verb="POST" url="https://127.0.0.1:PORT/api/v1/namespaces/default/pods/web-.../eviction" status="201 Created"
```

There it is: **one `POST` to `.../pods/<name>/eviction` per Pod**. Not one write, and not a controller — a sequence of individual HTTP requests. And look at the URL: `127.0.0.1`, on the port `kind` published for your cluster. Those requests are leaving *your machine*.

### So what *is* drain?

Now the prediction can be settled properly.

**Drain is a loop running inside `kubectl` on your laptop.** It lists the Pods on the node, then asks the API server to evict them one at a time, waiting for each to go — the exact requests you just watched it make. There is no drain object in the store, no drain controller, and no record anywhere that a drain is in progress. Press Ctrl-C and it stops precisely where it was: the node stays cordoned, some Pods evicted, some not, and **nothing in the cluster will finish the job**, because nothing in the cluster ever knew there was a job.

This is the sharpest instance in the act of the thing the act keeps insisting on. Everything else you have watched — a replacement Pod, a node assignment, a re-registered static Pod — happened because a process *inside* the cluster wanted the world to match an object. Drain is the opposite: a script, outside the cluster, issuing one request per Pod. Close your terminal and the operation stops existing.

Which tells you what to do when a drain hangs: it is *your* command that is stuck, waiting on one specific eviction. So find out which Pod, and ask why that one.

And now look at what the drain actually achieved:

```bash
kubectl get pods -A -o wide --field-selector spec.nodeName=netlab-worker
kubectl get pods -l app=web -o wide
```

The DaemonSet Pods are still there. Your three `web` Pods are gone — and their replacements are **`Pending`**, because you cordoned the only node that accepts work and the other one carries that `NoSchedule` taint you just read.

That is not a flaw in the lab, it is the operation's real cost made visible. **A drain does not relocate Pods. It deletes them**, and lets lesson 03's reconciliation loops create replacements wherever the scheduler can put them — and if the scheduler can put them nowhere, they wait. Draining a node in a cluster with no spare capacity is an outage you performed on purpose, and the `Pending` you are looking at is what that looks like from the inside.

```bash
kubectl uncordon netlab-worker
kubectl wait --for=condition=Available deployment/web --timeout=90s
kubectl get pods -l app=web -o wide          # back on the worker
```

Uncordoning removed the field and the taint; the loops did the rest, unprompted.

### The thing that is allowed to say no

You just watched drain `POST` to a Pod's `eviction` subresource rather than `DELETE` the Pod, and that is not a stylistic choice. Eviction is a distinct request, and it is the one write in this whole act that the API server may **refuse on policy grounds**.

The policy is an object, and it is the last new kind this act introduces. A **PodDisruptionBudget** states how much of an application may be missing *at once, voluntarily*. Create one that is deliberately impossible to satisfy:

```bash
kubectl create poddisruptionbudget web-pdb --selector=app=web --min-available=3
kubectl get pdb web-pdb
```

Three replicas, and a budget insisting all three stay available. There is no way to evict any of them without breaking it.

> **Predict first —** with that budget in place, you drain the node those Pods are on. What happens — does the drain evict them anyway, fail immediately, or something else? And how would you tell the difference between "blocked" and "slow"?

```bash
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=60s
```

It **blocks, retrying loudly, and then times out.** Not an immediate error — the eviction request is rejected, and `kubectl` treats that as *not yet* rather than *no*, because in the normal case it genuinely is: a rolling update in progress would clear in seconds. Your budget will never clear, so it retries every five seconds until the timeout you supplied, printing this each round:

```
error when evicting pods/"web-..." -n "default" (will retry after 5s):
Cannot evict pod as it would violate the pod's disruption budget.
```

That is worth reading rather than scrolling past, because it is a diagnosis handed to you unprompted — a dozen times a minute, naming the mechanism. **A drain blocked by a disruption budget is the loud kind of stuck.**

Which matters because there is a quiet kind, and telling them apart is the actual skill. A Pod that is simply slow to terminate — a long grace period, or a container ignoring the signal to stop — produces no such message. Drain sits there saying nothing. So: scrolling retries naming a budget means *blocked, and here is by what*; silence means *waiting on a Pod that will not die*, and the investigation is that Pod rather than any policy.

`--timeout` belongs on every drain you run interactively for the sake of the second case. Without it the default is to wait indefinitely, and a silent drain that will never finish is indistinguishable from one that is nearly done.

And note the word *voluntarily* in what a PDB governs. It constrains eviction, which is a request. It does not constrain a node catching fire, a `kubectl delete pod`, or a kubelet dying — none of those ask permission. A PDB is a contract about **planned** disruption only, and reading it as a general availability guarantee is the most common way to be disappointed by one.

```bash
kubectl delete pdb web-pdb
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=60s   # now completes
kubectl uncordon netlab-worker
```

> **Check yourself —** You are draining a node during a planned upgrade. It has been running for twenty minutes with no output. Give the order you would investigate in, and say what each step distinguishes.

<details>
<summary>Answer</summary>

Start with what "no output" already told you, because it is a real deduction and not a shrug: **it is not a disruption budget.** A PDB block prints a retry naming the budget every five seconds — twenty minutes of it would be several hundred lines. Silence rules that out before you run anything.

Then remember whose loop is stuck. The drain is running in your terminal, not in the cluster, so there is no controller to inspect and no status field to read. The evidence is on the node.

**Which Pod is left?** `kubectl get pods -A -o wide --field-selector spec.nodeName=<node>`. Whatever is still listed, minus the DaemonSet Pods, is what your drain is waiting on — usually exactly one, and often `Terminating`. That single name is the whole investigation.

**Why will it not die?** Silence plus `Terminating` means the eviction was *accepted* and the Pod is refusing to finish, which is a completely different problem from being refused. Look at its `terminationGracePeriodSeconds`, which may be minutes by design, and at whether the container actually stops on the signal it is being sent — a process that ignores `SIGTERM` waits out the full grace period and then gets killed, every time. A `preStop` hook that hangs does the same.

Had there been output, the diagnosis would already be in it, and the fix would be a conversation rather than a command: either the application genuinely cannot lose a replica right now, or the budget is wrong.

**Is a replacement even possible?** `kubectl get pods -A | grep Pending`. If the evicted Pods have nowhere to go, the drain may well "succeed" and leave you worse off than before. On a cluster at capacity, checking this *before* draining is the difference between maintenance and an incident.

The general shape: a drain is a client-side loop over evictions, so a stuck drain is always one specific eviction, and an eviction is the one request in Kubernetes that something is allowed to refuse. Find the Pod, then find out whether you were **refused** — which is loud — or merely **kept waiting**, which is not.

</details>

<!-- figure -->

```
   CORDON                                    DRAIN

   cordon writes ONE FIELD, and nothing else:   a LOOP IN YOUR TERMINAL
     spec.unschedulable: true                     for each Pod on the node:
        |                                             POST pods/<name>/eviction
        +--> the SCHEDULER reads the field            wait for it to go
        |      (kubectl get nodes renders
        |       SchedulingDisabled from it too)  no drain object. no controller.
        |                                        no record it is happening.
        +--> a CONTROLLER reconciles it into     Ctrl-C = stops, half-done, forever
               node.kubernetes.io/unschedulable    -- nothing knew there was a job
               :NoSchedule
               (stop kube-controller-manager and
                the taint never appears -- so it
                was never kubectl that wrote it)

   NOT the same as node-role.kubernetes.io/control-plane:NoSchedule,
   which is permanent and set at install time. one hyphen apart.

   running Pods: untouched. cordon is about the FUTURE only.

   nothing "does" a cordon.                  refuses by default on:
   you edited an object and a loop              DaemonSet Pods  (nowhere to go)
   that was already running reads it             --ignore-daemonsets
   differently now.                             emptyDir data   (irreversible)
                                                 --delete-emptydir-data

   EVICTION is not DELETION
     it is the one write the API server may REFUSE on policy:
         PodDisruptionBudget: "how much may be missing AT ONCE, VOLUNTARILY"
     a PDB does not constrain: node failure, kubectl delete pod, a dead kubelet.
     nothing asks its permission.

   TWO KINDS OF STUCK DRAIN, and the output tells you which
     LOUD   retry naming the budget every 5s  -> refused. a PDB. read it.
     SILENT nothing at all                    -> accepted, but the Pod won't die:
                                                 grace period, or SIGTERM ignored.
     always pass --timeout, for the silent one.

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

> **You understand this when you can** say what `cordon` actually writes — one field — and name
> the two independent things that read it; explain why `drain` is neither a field nor a controller
> but a loop in your terminal, and what that implies for a drain you interrupt; say why drain
> refuses to touch DaemonSet Pods; and tell a drain blocked by a PodDisruptionBudget from one
> waiting on a Pod that will not die, then say what a PDB does *not* constrain.

**Which raises:** you now have the whole planned-maintenance sequence, and every step of it assumed you could ask the cluster questions. But this act has broken the API server twice, and both times `kubectl` went silent along with it. A node that will not come `Ready`, a control-plane component that crash-loops, a cluster that answers nothing at all — what is left to look at, and in what order?

---

← Prev: **[Upgrades, and what is allowed to be out of step](06-upgrades-and-version-skew.md)** · ↑ **[Act VI overview](README.md)** · Next: **[When the control plane breaks](08-when-the-control-plane-breaks.md)** →
