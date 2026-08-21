# When replicas are not interchangeable

You have already built a StatefulSet. You just were not told that is what it was called.

In Act V you applied three Pods named `db-0`, `db-1`, `db-2`, each with `hostname` and `subdomain` set, in front of a headless Service — and that lesson ended by telling you plainly what you were looking at:

> *"the object you will reach for in practice — a workload controller that stamps out `db-0`, `db-1`, `db-2` and sets these two fields per replica — is automation over exactly these lines. You are not missing a feature; you are looking at what the feature is made of."*

So the name is easy and the name is not the point. The interesting question is the one the last lesson left you with: **your hand-built version had no disks. What does the real controller do about that, and what else does it have to change to make it work?**

Because there is a deeper pattern here, and it is the reason this lesson covers four kinds at once rather than one. Everything you built in lessons 01 through 06 quietly assumed three things about a workload:

1. the replicas are **interchangeable** — any one will do
2. **you** choose how many there are
3. the Pod **never finishes**

Each remaining workload kind exists because one of those is false.

### Assumption 1 is false: the replicas have names

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: db
spec:
  clusterIP: None
  selector:
    app: db
  ports:
  - port: 5432
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: db
spec:
  serviceName: db
  replicas: 3
  selector:
    matchLabels:
      app: db
  template:
    metadata:
      labels:
        app: db
    spec:
      terminationGracePeriodSeconds: 5
      containers:
      - name: shell
        image: busybox:1.36
        command: ["sh", "-c", "echo \"$HOSTNAME woke at $(date +%T)\" >> /data/log; sleep 3600"]
        volumeMounts:
        - name: data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 64Mi
EOF
```

Before it settles, watch it arrive — this is the first difference and it is visible only while it happens:

```bash
kubectl get pods -l app=db -w      # Ctrl-C when three are Running
```

**They appear one at a time, in order, and each waits for the one before it to be Ready.** A ReplicaSet creates all its Pods in a single burst — it has a count to satisfy and no reason to care about sequence. This controller has an *ordinal* to satisfy, and it will not create `db-1` until `db-0` is Ready, because for a workload where members find each other by name, "the second member joins a cluster that already has a first member" is often the only correct order. (`podManagementPolicy: Parallel` turns this off when your software does not care, and the fact that it is a field is the admission that the wait is a cost.)

Now the part that answers the last lesson's question:

```bash
kubectl get pvc
```

```
NAME          STATUS   VOLUME     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
data-db-0     Bound    pvc-...    64Mi       RWO            standard       60s
data-db-1     Bound    pvc-...    64Mi       RWO            standard       45s
data-db-2     Bound    pvc-...    64Mi       RWO            standard       30s
```

**Three PVCs, one per replica, named after the claim template *and* the Pod.** Not one shared volume — three separate ones, and the naming is the whole mechanism: `data-db-1` is derivable from the Pod's name, so any controller that recreates `db-1` can find `db-1`'s disk without storing a lookup table anywhere. Identity is a *string*, exactly as Act V found when it discovered the stable thing was a DNS name rather than an address.

Prove the pairing holds through a restart:

```bash
kubectl exec db-1 -- cat /data/log
kubectl delete pod db-1
kubectl wait --for=condition=Ready pod/db-1 --timeout=90s
kubectl exec db-1 -- cat /data/log
```

**Two lines now** — the original wake-up and a second one. Same name, same disk, and the earlier line still there to prove it. Compare that with what a Deployment would have done: a new random suffix, a fresh `emptyDir`, no memory of anything.

> **Predict first —** scale this StatefulSet down to 1 replica, then back up to 3. Say what you expect to happen to the two PVCs while the replicas are gone, and what `db-1` will find in `/data/log` when it returns. There is a defensible answer either way; commit to one before running it.

```bash
kubectl scale statefulset db --replicas=1
kubectl get pods -l app=db
kubectl get pvc
```

**One Pod. Three PVCs.** The Pods went in *reverse* ordinal order — `db-2` first, then `db-1`, mirroring the creation order for the same reason — and the disks did not go anywhere at all.

```bash
kubectl scale statefulset db --replicas=3
kubectl wait --for=condition=Ready pod/db-1 --timeout=90s
kubectl exec db-1 -- cat /data/log
```

**Three lines, and the first two are from before the scale-down.** `db-1` came back to its own disk.

That asymmetry is deliberate and it is the most important thing in this section. **Scaling down deletes Pods and keeps volumes.** The controller has no way to know whether you are shrinking a cluster permanently or restarting a node, and one of those two mistakes loses a database. So it makes the recoverable choice and leaves you holding storage you have to clean up by hand — which is why `kubectl get pvc -A` is in this act's cleanup check, and why "we scaled the StatefulSet down months ago" is a real line item on real cloud bills.

Two more consequences worth naming while the object is in front of you:

```bash
kubectl get statefulset db -o jsonpath='{.spec.serviceName}{"\n"}'
kubectl exec db-0 -- nslookup db-1.db.default.svc.cluster.local
```

`serviceName` is not optional and not decoration: it is how the controller knows what to put in the middle of each Pod's DNS name. It is setting the `subdomain` field you set by hand in Act V. And the Service it names must be the headless one — put a normal ClusterIP there and you get a VIP that load-balances across three members that were the entire point of not being interchangeable.

### Assumption 2 is false: the count is not yours

Act VI made you type `--ignore-daemonsets` and told you what a DaemonSet *means* — one Pod on every node — and then moved on. Look at one properly:

```bash
kubectl get daemonset -n kube-system
kubectl get daemonset kube-proxy -n kube-system -o jsonpath='{.spec.replicas}{"\n"}'
```

**The second command prints nothing.** There is no `spec.replicas` on a DaemonSet — not set to a default, not present. Confirm the field genuinely does not exist:

```bash
kubectl explain daemonset.spec | grep -i replicas
```

Nothing. So where does the number in the `DESIRED` column come from?

```bash
kubectl get daemonset kube-proxy -n kube-system \
  -o jsonpath='{.status.desiredNumberScheduled}{"\n"}'
kubectl get nodes --no-headers | grep -c .
```

**Both say `2`, and the first one is in `status`.**

Stop on that, because it is a genuine exception to this act's spine. Every other count you have written this act was a *claim* in `spec` — your intent, stored for a loop to read. A DaemonSet's count is a *derived fact* in `status`: the controller counted your nodes and wrote down what it found. You cannot ask for four; there is no field in which to ask. Add a node and the number changes without anyone editing the object.

That is also, finally, why `kubectl drain` needs a special flag for these. Watch what a cordon does to one:

> **Predict first —** Act VI established that `cordon` sets `spec.unschedulable`, and that a controller turns that into a `NoSchedule` taint so the scheduler stops placing Pods there. So: cordon a node and delete the DaemonSet Pod on it. Does it come back?

```bash
kubectl cordon netlab-worker
POD=$(kubectl get pods -n kube-system -l k8s-app=kube-proxy \
  --field-selector spec.nodeName=netlab-worker -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod -n kube-system $POD
sleep 10
kubectl get pods -n kube-system -l k8s-app=kube-proxy -o wide
```

**It comes straight back, on the cordoned node.** Look at why:

```bash
kubectl get daemonset kube-proxy -n kube-system \
  -o jsonpath='{range .spec.template.spec.tolerations[*]}{.key}{" "}{.operator}{" "}{.effect}{"\n"}{end}'
```

Among the tolerations is `node.kubernetes.io/unschedulable NoSchedule` — added automatically by the DaemonSet controller to every Pod it creates. A cordon is a taint, and this Pod tolerates that taint by construction.

So now the flag explains itself. `drain` evicts Pods so that something can put them elsewhere; it cordons first precisely so the replacements do not land back on the node it is emptying. Against a DaemonSet Pod both halves fail: there is nowhere else it is *supposed* to be, and the cordon that would normally keep it away does not apply. Evicting it would produce an identical Pod on the same node about a second later. `--ignore-daemonsets` is not a convenience — it is `drain` refusing to enter a loop it cannot win.

The same toleration mechanism is why the control-plane node runs `kube-proxy` at all, despite carrying the `NoSchedule` taint Act VI showed you. Look at the toleration list again and you will find an entry with **no key at all** and `operator: Exists` — which reads as "tolerate every taint there is." That is how anything gets onto a control-plane node, and it is the only line you need in your own DaemonSet if you want it truly everywhere.

```bash
kubectl uncordon netlab-worker
```

### Assumption 3 is false: the Pod is supposed to stop

Every controller so far wants a Pod that runs forever. Break that, and see what breaks with it:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: once
spec:
  template:
    spec:
      restartPolicy: Always
      containers:
      - name: work
        image: busybox:1.36
        command: ["sh", "-c", "echo working; sleep 3; echo done"]
EOF
```

**Rejected, by the API server, before anything runs:**

```
The Job "once" is invalid: spec.template.spec.restartPolicy: Unsupported value:
"Always": supported values: "OnFailure", "Never"
```

This is not a style rule, and it is worth deriving rather than memorising, because it is the shortest possible statement of what a Job is.

Lesson 01 established `restartPolicy: Always` as the kubelet's local promise: a container that exits gets started again — and note the wording, *exits*, not *fails*. Exit code 0 restarts too. Meanwhile a Job is finished when its Pod reaches `Succeeded`, and a Pod reaches `Succeeded` only when its containers have exited and stayed exited. Put those together and `Always` makes a Job that can never complete, by definition: the very event that would finish it is the event that restarts it. The two fields are not merely a bad combination, they are contradictory — so validation refuses rather than letting you create an object no loop could ever satisfy.

Fix it and add the two fields that make a Job more than a Pod:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: once
spec:
  completions: 6
  parallelism: 2
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: work
        image: busybox:1.36
        command: ["sh", "-c", "echo working; sleep 5"]
EOF
kubectl get pods -l job-name=once -w      # Ctrl-C when six are Completed
```

**Two at a time, three waves.** `completions` is how many successes you need; `parallelism` is how many may be in flight. Separating them is the difference between "run this 600 times" and "melt the cluster running this 600 times at once" — and neither number has an equivalent on a Deployment, because a Deployment's replicas never accumulate toward a total.

Now fail one on purpose, because the failure behaviour is where Jobs surprise people:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: doomed
spec:
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: work
        image: busybox:1.36
        command: ["sh", "-c", "echo trying; exit 1"]
EOF
sleep 90
kubectl get pods -l job-name=doomed
kubectl get job doomed
```

**Several Pods, all in `Error`, and every one of them still listed.** With `restartPolicy: Never` a retry is a *new Pod*, and the failed ones are deliberately not deleted — their logs are the only record of why the work failed, and a controller that tidied them away would be destroying the evidence.

```bash
kubectl logs -l job-name=doomed --tail=1
kubectl describe job doomed | tail -8
```

`backoffLimit` bounds the retries and the delays between them grow exponentially, which is why that `sleep 90` was needed for a command that fails instantly. Two other fields belong in the same thought:

- **`activeDeadlineSeconds`** is a wall-clock limit on the whole Job, and it overrides `backoffLimit` — a Job that would be entitled to six more retries is killed anyway. Use it for work that must finish before something else starts; use `backoffLimit` for work that is probably just broken.
- **`ttlSecondsAfterFinished`** deletes the Job — and, through the ownership chain from lesson 01, its Pods — some seconds after it finishes. You have already been bitten by this without knowing: Act V's Gateway API install ships a certificate-generating Job with `ttlSecondsAfterFinished: 30`, which is exactly why that lesson's cleanup needs `--ignore-not-found`.

Without a TTL, finished Jobs accumulate forever. That is the default, and it is the right default for the same reason failed Pods are kept.

### A controller whose output is other objects

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: tick
spec:
  schedule: "* * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
          - name: work
            image: busybox:1.36
            command: ["sh", "-c", "date +%T"]
EOF
sleep 130
kubectl get cronjob,job,pod -l app!=db
```

Jobs named `tick-<number>` that you did not write. Read the chain the way lesson 01 taught you to:

```bash
kubectl get job -o jsonpath='{range .items[*]}{.metadata.name}{"  owner="}{.metadata.ownerReferences[0].kind}{"\n"}{end}'
```

**CronJob → Job → Pod**, one `ownerReference` per link, the same field and the same garbage collection as Deployment → ReplicaSet → Pod. A CronJob does not run anything. It writes Job objects on a schedule and lets the Job controller do the work — which is the third time in two acts that a loop's entire output has turned out to be *another object for a different loop to read*.

Three things about it that cost people real outages:

- **`concurrencyPolicy`** defaults to `Allow`. A Job that takes ninety seconds on a one-minute schedule will happily overlap itself forever until the cluster is full. `Forbid` skips the new run; `Replace` kills the old one. There is no default that is right for every job, which is why the default is the one that does what you literally asked.
- **The schedule is evaluated in the controller manager's timezone**, not yours, unless you set `spec.timeZone`. A nightly backup at `"0 2 * * *"` on a UTC control plane is not running at 2am where you are.
- **`startingDeadlineSeconds`** bounds how far back the controller looks for schedules it missed. If the controller was down long enough to miss more than a hundred, it stops trying entirely and says so in its logs rather than launching a hundred Jobs at once. That is a deliberate refusal, and it means a CronJob can be silently *not running* on a perfectly healthy cluster.

> **Check yourself —** A colleague converts a StatefulSet from 3 replicas to 5, and the two new members come up with data in them. Nobody restored a backup. What happened?

<details>
<summary>Answer</summary>

The StatefulSet had been scaled *down* from 5 (or more) at some point, and the PVCs `data-<name>-3` and `data-<name>-4` were never deleted — because scaling down deletes Pods and keeps volumes.

Scaling back up recreated Pods with those exact ordinals, and the claim name is derived from the Pod name, so each one bound to the disk it had before. From the controller's point of view nothing unusual happened: it needed `data-<name>-3`, a PVC by that name existed and was Bound, so it used it.

Whether this is a relief or a disaster depends entirely on what is on those disks. A database member returning to a stale copy of a dataset that has moved on without it can be considerably worse than an empty one, because it will try to participate.

The habit to take away: `kubectl get pvc` before scaling a StatefulSet up, not after. It is the only place the cluster remembers your old replicas.

</details>

<!-- figure -->

```
   FOUR KINDS, THREE BROKEN ASSUMPTIONS

   Deployment / ReplicaSet     replicas interchangeable, count is yours, runs forever
                                identity = pod-template-hash (a random suffix)

   StatefulSet                 BREAKS "interchangeable"
                                identity = ORDINAL. db-0, db-1, db-2, created in
                                order, deleted in reverse.
                                volumeClaimTemplates -> one PVC PER REPLICA,
                                named data-db-1, derivable from the Pod name.
                                serviceName MUST be a headless Service (Act V).
                                >>> scale DOWN keeps the volumes. every time. <<<

   DaemonSet                   BREAKS "the count is yours"
                                there is NO spec.replicas field at all.
                                the count lives in STATUS: desiredNumberScheduled,
                                derived from the node list.
                                auto-tolerates node.kubernetes.io/unschedulable
                                -> a cordon does not keep it off
                                -> which is WHY drain needs --ignore-daemonsets
                                toleration with NO key + Exists = "runs anywhere"

   Job                         BREAKS "runs forever"
                                restartPolicy: Always is REJECTED -- it would
                                restart the exit that completes the Job.
                                completions = how many successes
                                parallelism = how many at once
                                failed Pods are KEPT (their logs are the evidence)
                                ttlSecondsAfterFinished is the only cleanup

   CronJob                     a loop whose OUTPUT IS JOB OBJECTS
                                CronJob -> Job -> Pod, ownerReferences all the way
                                concurrencyPolicy: Allow is the default and overlaps
                                schedule is in the CONTROLLER's timezone
```

**Cleanup:**

```bash
kubectl delete cronjob tick
kubectl delete job once doomed --ignore-not-found
kubectl delete statefulset db
kubectl delete svc db
kubectl delete pvc -l app=db          # the StatefulSet did NOT take these with it
kubectl get pvc -A                    # empty
kubectl get nodes                     # both Ready, neither SchedulingDisabled
```

That `delete pvc` line is the lesson repeating itself one last time. Deleting the StatefulSet does not delete the claims, for the same reason scaling it down does not.

> **You understand this when you can** say what a StatefulSet gives you that the three Pods you hand-built in Act V did not, and why the claim name being derived from the Pod name is the whole identity mechanism; explain why scaling down keeps volumes and what that means for both your data and your bill; say where a DaemonSet's replica count lives and why that is not `spec`, and derive from one toleration why `drain` has to special-case DaemonSet Pods rather than evicting them; derive why `restartPolicy: Always` is rejected on a Job from what `Always` and `Succeeded` each mean; distinguish `completions` from `parallelism`, and `backoffLimit` from `activeDeadlineSeconds`; and explain why failed Job Pods are kept by default and what the one field is that cleans them up.

**Which raises:** count the manifests in this lesson. Every one of them repeated the same label in three separate places that must agree — the selector, the Pod template, and the Service — and nothing anywhere warned you if they did not. A real application is twenty of these, and you will need the same twenty in a test namespace with different image tags and a smaller replica count. So how do you ship a set of objects as *one thing*, and change one value across all of them without editing twenty files by hand?

---

← Prev: **[Three different promises called "survives"](06-storage.md)** · ↑ **[Act VII overview](README.md)** · Next: **[Act VII overview](README.md)** — packaging is being written →
