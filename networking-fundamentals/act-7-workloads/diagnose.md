# Act VII — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act VII. This checks whether you can *use* it. Real failures never arrive labelled "that was the wrong probe" or "your ConfigMap was mounted with `subPath`" — they arrive as a symptom, a shrug, and a ticket. Each drill below puts your cluster into a **real broken state**, hands you only the symptom, and asks you to find the cause with the act's tools.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** Reading it closely spoils the hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud what you think is wrong and which field or command would prove it — *then* look.
3. **Open the reveal only after you've tried.**
4. **Then verify it — and say what was wrong.** Every drill ends with a `Verify it` line:

   ```bash
   tools/verify-drill.sh act-7 <n> "your one-line diagnosis"
   ```

   It exits `0` only if the workload is genuinely fixed **and** the cause you typed is right. The
   checks are deliberately not `kubectl get` on the object you edited — they read the thing the
   *next* loop in the chain produced, because that is the only evidence a claim was kept: an
   EndpointSlice with a ready endpoint, a symlink inside the container, an HPA condition going
   `True`. It will not tell you the answer — see [`drills/`](../../drills/README.md) for why the
   expected cause is stored as a hash.

**Where:** the same `kind` cluster as the lessons. If you do not have it, [the Act V lab lesson](../act-5-kubernetes/01-lab-with-kind.md) builds it in a minute.

Unlike Act VI, nothing here can break your cluster. These drills break *workloads*, which is what you will actually be paged about. The cost of abandoning one halfway is some leftover objects, and this catches all of it:

```bash
kubectl delete deploy,sts,ds,job,cronjob,hpa,svc,cm,secret,pvc -l drill --ignore-not-found
kubectl delete pv -l drill --ignore-not-found
kubectl delete namespace imagelab mountlab limitlab --ignore-not-found   # drills 8-10
kubectl get pvc                 # should be empty
kubectl get nodes               # both Ready, neither SchedulingDisabled
```

**The method this act adds to Act VI's five questions.** Act VI taught you to descend the dependency stack when the *cluster* is broken. When a *workload* is broken the cluster is fine, and the useful question is different — it comes straight from the act's spine:

```
  Every field is a claim, and each claim is read by a DIFFERENT loop.
  So: which loop is failing to keep which promise?

  1. Was the object even accepted?     it was, if kubectl get shows it
  2. Is there a Pod?                   no  -> a CONTROLLER problem (counting)
  3. Does the Pod have a node?         no  -> a SCHEDULER problem (placing)
  4. Is the container running?         no  -> a KUBELET/image problem
  5. Is it in the Service?             no  -> a READINESS problem
  6. Is it doing the right thing?          -> a CONFIG or VOLUME problem
```

Each `no` names the component to look at, and every drill below lands on exactly one of those rows.

**You now hold three checklists, so here is the rule for choosing.** Act VI's five questions descend a *dependency stack* and are for when the cluster is sick — start there only if `kubectl get nodes` is slow, wrong or unanswered. Act V's five questions descend the *network path* and are for when a request does not arrive at a Pod that is otherwise healthy. These six walk the *claim chain* between an object you wrote and a container doing work, and they are the right starting point for anything that reads as "my workload is not doing what I asked."

They also overlap deliberately at one point. Row 5 here — *is it in the Service?* — is where this list hands over to Act V's, and it hands over as soon as the answer is "yes, and traffic still isn't arriving." Getting to row 5 is usually one command; do that before choosing between the other two lists.

---

## The clock

Every drill below carries a **target time**, and this is the one thing these drills do that the
lessons deliberately do not. The course is built to make you understand; a certification is scored on
whether you can act inside a budget, and those are different skills that look identical from the
inside. So: Seven, because that is the number: **17 tasks in 120 minutes** is about seven minutes each, and these drills are the closest thing in the course to a task.

Three rules, taken straight from [the exam-day pacing doctrine](../../exam-prep/exam-day.md):

1. **Start the clock when the symptom appears**, not when you start the reproduce block. Building the
   broken state is setup, and on the exam somebody else has already done it.
2. **At the target, say your best hypothesis out loud** even if you are not confident. Naming a wrong
   hypothesis at 7 minutes is worth more than a right one at twenty, because the wrong one is
   falsifiable in one command and the exam pays for closed tasks.
3. **At 10 minutes, stop and open the reveal.** That is not giving up, it is the exam's own rule —
   *"the moment a task passes 10 minutes, flag it and move on"* — and the skill it builds is the
   costly one. A task that eats 25 minutes has cost you three others worth the same marks.

Run each drill untimed the first time if you like. Then run it again, weeks later, with a timer, and
notice that the second number is the one that predicts anything.

## Drill 1 — "the deploy finished but the site is down"1

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

**Reproduce it:**

```bash
kubectl create deployment shop --image=nginx:1.27-alpine --replicas=3
kubectl label deployment shop drill=1
kubectl expose deployment shop --port=80
kubectl label svc shop drill=1
kubectl patch deployment shop --type=json -p='[{"op":"add","path":"/spec/template/spec/containers/0/readinessProbe","value":{"httpGet":{"path":"/healthz","port":8080},"periodSeconds":5}}]'
kubectl rollout status deployment/shop --timeout=40s
```

**The symptom:** the rollout does not complete. A colleague says "it deployed fine yesterday."

**Diagnose it before reading on.** Which of the six rows is failing?

<details>
<summary>Reveal</summary>

Row 5 — readiness — and the tell is that everything above it is healthy:

```bash
kubectl get pods -l app=shop
```

```
NAME                    READY   STATUS    RESTARTS   AGE
shop-...-abc            0/1     Running   0          40s
```

**`Running` and `0/1`.** The container started, the scheduler placed it, the image pulled. Nothing crashed and `RESTARTS` is `0`. So the process is alive and something has decided it is not *ready*.

```bash
kubectl describe pod -l app=shop | grep -A3 'Readiness'
kubectl get endpointslice -l kubernetes.io/service-name=shop \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{" ready="}{.conditions.ready}{"\n"}{end}'
```

The probe is checking `:8080/healthz`. Nginx serves port 80 and has no `/healthz`. So the probe fails forever, the kubelet writes `Ready=False` on the Pod condition, the endpoint controller marks the endpoint not-ready, and kube-proxy never programs a rule for it. Act V's chain, refusing to complete at its first link.

And the rollout hangs rather than failing, because `maxUnavailable` will not let it retire old Pods until new ones are Ready — which is the safety property working exactly as designed. This deploy is *stuck*, not broken, and that distinction is why nothing rolled back on its own.

**Fix it:**

```bash
kubectl patch deployment shop --type=json -p='[{"op":"remove","path":"/spec/template/spec/containers/0/readinessProbe"}]'
kubectl rollout status deployment/shop --timeout=60s
```

**The habit:** `READY 0/1` with `STATUS Running` and `RESTARTS 0` is *always* a readiness story, and it is the one Pod state that means "your application is fine and something disagrees." Read the probe's port against what the container actually listens on before anything else.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-7 1 "the field that broke readiness"
```

---

## Drill 2 — "it worked in staging"2

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

**Reproduce it:**

```bash
kubectl create configmap appconf --from-literal=MODE=safe
kubectl label configmap appconf drill=2
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata: { name: api, labels: { drill: "2" } }
spec:
  replicas: 1
  selector: { matchLabels: { app: api } }
  template:
    metadata: { labels: { app: api, drill: "2" } }
    spec:
      containers:
      - name: api
        image: busybox:1.36
        command: ["sh","-c","while true; do echo mode=$(cat /etc/app/MODE); sleep 5; done"]
        volumeMounts:
        - { name: c, mountPath: /etc/app/MODE, subPath: MODE }
      volumes:
      - { name: c, configMap: { name: appconf } }
EOF
kubectl rollout status deployment/api --timeout=90s
kubectl patch configmap appconf -p '{"data":{"MODE":"live"}}'
```

**The symptom:** you changed the ConfigMap five minutes ago. `kubectl get configmap appconf -o yaml` clearly says `MODE: live`. The application still says `safe`.

**Diagnose it.** Row 6 — but *why*?

<details>
<summary>Reveal</summary>

```bash
kubectl logs deploy/api --tail=2
kubectl exec deploy/api -- cat /etc/app/MODE
kubectl exec deploy/api -- ls -la /etc/app/
```

The last command is the one that settles it:

```
-rw-r--r--    1 root root  5 ...  MODE
```

**A plain file.** Not `MODE -> ..data/MODE`. There is no symlink, which means there is no `..data` to repoint, which means the atomic swap has nothing to act on. This mount used `subPath`, so the kubelet copied the content in at container start and will never touch it again.

The reason it "worked in staging" is that in staging somebody restarted it, and a restart is the only thing that updates a `subPath` mount.

**Fix it** — mount the directory and reference the file inside it:

```bash
kubectl patch deployment api --type=json -p='[
  {"op":"replace","path":"/spec/template/spec/containers/0/volumeMounts/0","value":{"name":"c","mountPath":"/etc/app"}},
  {"op":"replace","path":"/spec/template/spec/containers/0/command","value":["sh","-c","while true; do echo mode=$(cat /etc/app/MODE); sleep 5; done"]}]'
kubectl rollout status deployment/api --timeout=90s
sleep 70
kubectl logs deploy/api --tail=1        # mode=live
```

**The habit:** when a mounted config will not refresh, `ls -la` the mount directory *before* theorising. A symlink means the mechanism is present and you are impatient; a plain file means it was never going to work. Ninety seconds of waiting distinguishes them.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-7 2 "the volumeMount field that froze the file"
```

---

## Drill 3 — "half the replicas never start"3

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

**Reproduce it:**

```bash
kubectl create deployment heavy --image=nginx:1.27-alpine --replicas=4
kubectl label deployment heavy drill=3
kubectl set resources deployment heavy --requests=cpu=3
sleep 20
```

**The symptom:** four replicas requested, some are `Pending`, and your monitoring dashboard shows both nodes under 5% CPU. A colleague concludes the cluster is out of capacity and asks you to add a node.

**Diagnose it, and decide whether they are right.**

<details>
<summary>Reveal</summary>

```bash
kubectl get pods -l app=heavy -o wide
kubectl describe pod -l app=heavy | grep -A3 FailedScheduling
kubectl describe node netlab-worker | grep -A7 'Allocated resources'
```

```
0/2 nodes are available: 1 Insufficient cpu, 1 node(s) had untolerated taint(s).
```

Row 3 — the scheduler — and both facts are true at once. Monitoring reads *actual usage* from the kernel; the scheduler reads the *sum of requests* from the store. You asked for 3 whole CPUs per replica, so two of them promise away nearly all of one node's `Allocatable` while using almost nothing.

Note the second clause too: `1 node(s) had untolerated taint(s)` is the control-plane node, which was never a candidate. So the real capacity of this cluster for this Deployment is one node, not two — and reading only the first clause is how people mis-size clusters.

Your colleague is not obviously right. Adding a node fixes the symptom at full price. The question is whether `cpu: 3` was measured or guessed, and in practice it is almost always guessed:

```bash
kubectl top pods -l app=heavy 2>/dev/null || echo "(nothing here measures usage — that is its own finding)"
```

**Fix it:**

```bash
kubectl set resources deployment heavy --requests=cpu=100m
kubectl rollout status deployment/heavy --timeout=90s
kubectl get pods -l app=heavy
```

**The habit:** `Insufficient cpu` against an idle cluster is a *ledger* problem, not a capacity problem, and the fix is upstream of the Pod that is complaining. Read the whole `FailedScheduling` tally, not the first clause — the per-reason counts must add up to the node count, and any node missing from the arithmetic is one you forgot was excluded.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-7 3 "what the scheduler was short of"
```

---

## Drill 4 — "we scaled it down but the bill didn't move"4

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

**Reproduce it:**

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata: { name: cache, labels: { drill: "4" } }
spec:
  clusterIP: None
  selector: { app: cache }
  ports: [ { port: 6379 } ]
**Verify it:**

```bash
tools/verify-drill.sh act-7 4 "the kind of object nothing cleaned up"
```

---
apiVersion: apps/v1
kind: StatefulSet
metadata: { name: cache, labels: { drill: "4" } }
spec:
  serviceName: cache
  replicas: 3
  selector: { matchLabels: { app: cache } }
  template:
    metadata: { labels: { app: cache, drill: "4" } }
    spec:
      terminationGracePeriodSeconds: 3
      containers:
      - name: c
        image: busybox:1.36
        command: ["sh","-c","sleep 3600"]
        volumeMounts: [ { name: data, mountPath: /data } ]
  volumeClaimTemplates:
  - metadata: { name: data }
    spec:
      accessModes: ["ReadWriteOnce"]
      resources: { requests: { storage: 64Mi } }
EOF
kubectl rollout status statefulset/cache --timeout=180s
kubectl scale statefulset cache --replicas=1
sleep 15
```

**The symptom:** a cost review flags storage spend that has not fallen since the team scaled this workload from 3 replicas to 1 last quarter. Compute spend fell as expected.

**Diagnose it, and say what you must check before fixing it.**

<details>
<summary>Reveal</summary>

```bash
kubectl get pods -l app=cache
kubectl get pvc
```

```
NAME           STATUS   VOLUME    CAPACITY   STORAGECLASS
data-cache-0   Bound    pvc-...   64Mi       standard
data-cache-1   Bound    pvc-...   64Mi       standard
data-cache-2   Bound    pvc-...   64Mi       standard
```

**One Pod, three claims.** Not a leak and not a bug: scaling a StatefulSet down deletes Pods and **keeps volumes**, deliberately, because the controller cannot distinguish "shrinking permanently" from "restarting" and one of those mistakes destroys data.

The thing to check before deleting anything is what happens if someone scales back up. The claim name is derived from the Pod name, so `cache-1` returning would rebind `data-cache-1` and come up **with last quarter's data in it**. For a cache that is harmless. For a database member it can be worse than an empty disk, because a member holding a stale copy of a dataset that has moved on will try to participate.

So: is this workload ever scaling back up, and is stale data safe for it? Only then:

```bash
kubectl delete pvc data-cache-1 data-cache-2
kubectl get pvc
```

**The habit:** `kubectl get pvc` is not a subset of `kubectl get pods`. After any StatefulSet scale-down, the claims are the part nothing cleans up, and they are also the only place the cluster remembers your old replicas — which makes them both the cost and the hazard.

</details>

---

## Drill 5 — "the cron job hasn't run and nothing is wrong"5

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

**Reproduce it:**

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata: { name: report, labels: { drill: "5" } }
spec:
  schedule: "*/1 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        metadata: { labels: { drill: "5" } }
        spec:
          restartPolicy: Never
          containers:
          - name: r
            image: busybox:1.36
            command: ["sh","-c","echo generating; sleep 600"]
EOF
sleep 150
```

**The symptom:** a report that should be produced every minute has produced one, several minutes ago. The CronJob exists, the cluster is healthy, `kubectl get cronjob` shows no errors.

**Diagnose it.**

<details>
<summary>Reveal</summary>

```bash
kubectl get cronjob report
kubectl get jobs -l drill=5
kubectl get pods -l drill=5
kubectl describe cronjob report | tail -6
```

One Job, still `Running`, and the `ACTIVE` column on the CronJob shows `1`. The events say it outright:

```
Normal  JobAlreadyActive  ...  Not starting job because prior execution is still running
```

Row 2 — a controller declining, on purpose. The Job takes ten minutes and the schedule is every minute, and `concurrencyPolicy: Forbid` means the controller skips a run rather than overlapping. So the workload is doing precisely what it was configured to do, and the schedule is a fiction: this can run at most once every ten minutes.

Worth knowing what the alternatives would have done. `Allow` — the **default** — would have started a new Job every minute regardless, accumulating ten concurrent copies and then more, which is how a cluster fills up overnight. `Replace` would kill the running one each minute, so the report would never finish at all. All three are wrong here; the *duration* is the bug.

Two related traps to check whenever a schedule looks unmet, neither of which is this drill:

```bash
kubectl get cronjob report -o jsonpath='{.spec.timeZone}{"\n"}'
```

Empty means the schedule is evaluated in the **controller manager's** timezone, not yours — so `"0 2 * * *"` is 2am wherever the control plane thinks it is. And if the controller was down long enough to miss more than a hundred schedules, it stops trying entirely rather than launching a hundred Jobs; `startingDeadlineSeconds` bounds how far back it looks. Both mean a CronJob can be silently not running on a completely healthy cluster.

**Fix it:**

```bash
kubectl delete cronjob report
kubectl delete jobs -l drill=5 --ignore-not-found
```

**The habit:** for a CronJob, always read `ACTIVE` and `LAST SCHEDULE` together. An `ACTIVE` that never returns to zero means the runtime has outgrown the interval, and no amount of looking at the schedule string will show you that.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-7 5 "the CronJob field that stopped it"
```

---

## Drill 6 — "the autoscaler is broken"6

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

**Reproduce it:**

```bash
kubectl create deployment busy --image=nginx:1.27-alpine --replicas=1
kubectl label deployment busy drill=6
kubectl expose deployment busy --port=80
kubectl label svc busy drill=6
kubectl autoscale deployment busy --min=1 --max=6 --cpu-percent=50
kubectl run loadgen --image=busybox:1.36 --restart=Never -l drill=6 -- \
  sh -c 'while true; do wget -q -O- http://busy/ >/dev/null; done'
sleep 90
```

**The symptom:** an HPA was added, load is being generated, and replicas have not moved off 1. This requires metrics-server from [lesson 10](10-choosing-the-number.md) to be installed — if it is not, that is the first finding and the drill is over.

**Diagnose it.**

<details>
<summary>Reveal</summary>

```bash
kubectl get hpa busy
kubectl top pods -l app=busy
```

```
NAME   REFERENCE         TARGETS              MINPODS   MAXPODS   REPLICAS
busy   Deployment/busy   cpu: <unknown>/50%   1         6         1
```

The two lines together are the whole diagnosis: `kubectl top` returns **real numbers** while the HPA says `<unknown>`. So metrics are flowing and the HPA still cannot form a value — which rules out the thing everyone checks first.

```bash
kubectl describe hpa busy | grep -A4 Conditions
```

```
ScalingActive   False   FailedGetResourceMetric   ... missing request for cpu
```

Utilisation is a *ratio*, and its denominator is the container's `requests` — not the node's capacity and not the limit. `kubectl create deployment` sets no requests, so there is no denominator, no ratio, and nothing to compare against 50%. The HPA declines to guess and reports `<unknown>` indefinitely. No error event, no restart, no crash: it simply never scales.

**Fix the cause, not the autoscaler:**

```bash
kubectl set resources deployment busy --requests=cpu=50m
kubectl rollout status deployment/busy --timeout=90s
sleep 90
kubectl get hpa busy                    # a real percentage, and REPLICAS climbing
```

**The habit:** `<unknown>` in `TARGETS` is never a metrics-server problem, whatever it looks like. It means the HPA could not build a fraction, and there are only two ways that happens: no metrics at all (in which case `kubectl top` also fails) or no denominator. One command distinguishes them.

**Cleanup:**

```bash
kubectl delete hpa busy
kubectl delete pod loadgen --now --ignore-not-found
kubectl delete deploy,svc,sts,cm -l drill --ignore-not-found
kubectl delete pvc -l drill --ignore-not-found
kubectl get pvc      # empty
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-7 6 "the missing denominator"
```

---


## Drill 7 — "the scheduler says we are out of nodes"7

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

**Reproduce it:**

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: reports-data, labels: { drill: "7" } }
spec:
  accessModes: [ ReadWriteOnce ]
  storageClassName: fast-ssd
  resources: { requests: { storage: 2Gi } }
**Verify it:**

```bash
tools/verify-drill.sh act-7 7 "the PVC field that named nothing"
```

---
apiVersion: apps/v1
kind: Deployment
metadata: { name: reports, labels: { drill: "7" } }
spec:
  replicas: 1
  selector: { matchLabels: { app: reports } }
  template:
    metadata: { labels: { app: reports } }
    spec:
      containers:
        - name: c
          image: nginx:1.27-alpine
          volumeMounts: [ { name: d, mountPath: /data } ]
      volumes:
        - name: d
          persistentVolumeClaim: { claimName: reports-data }
EOF
sleep 15
kubectl get pods -l app=reports
kubectl describe pod -l app=reports | grep -A4 Events:
```

**The symptom:** one replica, `Pending`, and the only event in the cluster is the scheduler's:

```
Warning  FailedScheduling  default-scheduler
  0/2 nodes are available: pod has unbound immediate PersistentVolumeClaims. not found
```

Someone has read "0/2 nodes are available" and opened a ticket to add a node. Drill 3 taught you to
distrust that sentence once. **Distrust it again, and say what the scheduler is actually telling you.**

<details>
<summary>Reveal</summary>

Row 3 of the table at the top — *does the Pod have a node?* — and this is the case where the row hands
you a component that is not at fault. Read the message as a sentence rather than a number: the
scheduler is not saying it ran out of room, it is saying **it will not place this Pod at all**, because
one of its inputs has not resolved yet. `0/2` is a count of nodes it declined to even consider.

So follow the claim, not the node:

```bash
kubectl get pvc reports-data
kubectl describe pvc reports-data | tail -4
```

```
NAME           STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS
reports-data   Pending                                      fast-ssd

  Warning  ProvisioningFailed  persistentvolume-controller
    storageclass.storage.k8s.io "fast-ssd" not found
```

```bash
kubectl get storageclass
```

```
NAME                 PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE
standard (default)   rancher.io/local-path   Delete          WaitForFirstConsumer
```

**There is no `fast-ssd` on this cluster, and naming a class that does not exist is not an error.** The
PVC was accepted — row 1 always says yes — and then sat there, because a claim names a class the same
way a Pod names an image: as a string that something else is expected to resolve. Nothing validates it
at admission, and the object that suffers is two hops downstream.

Now the part worth the drill, because "the class was misspelled" is one of four reasons and the other
three look the same from the outside. Put all four side by side against one hand-made 1Gi RWO volume:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolume
metadata: { name: drill7-pv, labels: { drill: "7" } }
spec:
  capacity: { storage: 1Gi }
  accessModes: [ ReadWriteOnce ]
  storageClassName: ""
  hostPath: { path: /tmp/drill7 }
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: too-big, labels: { drill: "7" } }
spec:
  accessModes: [ ReadWriteOnce ]
  storageClassName: ""
  resources: { requests: { storage: 5Gi } }
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: wrong-mode, labels: { drill: "7" } }
spec:
  accessModes: [ ReadWriteMany ]
  storageClassName: ""
  resources: { requests: { storage: 1Gi } }
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: waiting, labels: { drill: "7" } }
spec:
  accessModes: [ ReadWriteOnce ]
  resources: { requests: { storage: 1Gi } }
EOF
sleep 12
kubectl get pvc -l drill=7
for c in too-big wrong-mode reports-data waiting; do
  printf '%-14s ' "$c"
  kubectl describe pvc $c | grep -E '^\s+(Normal|Warning)' | tail -1
done
```

```
too-big        Normal   FailedBinding         no persistent volumes available for this
                                              claim and no storage class is set
wrong-mode     Normal   FailedBinding         no persistent volumes available for this
                                              claim and no storage class is set
reports-data   Warning  ProvisioningFailed    storageclass.storage.k8s.io "fast-ssd" not found
waiting        Normal   WaitForFirstConsumer  waiting for first consumer to be created
                                              before binding
```

Four `Pending` claims, and read what the events did and did not do for you.

**`too-big` and `wrong-mode` produce the identical message**, and it is the least useful one in
Kubernetes: *no persistent volumes available for this claim.* There is a volume available — it is sitting
in `kubectl get pv` marked `Available` — and the controller means "none that satisfy this claim" without
saying which field failed. One of these asks for 5Gi against a 1Gi volume; the other asks for
`ReadWriteMany` against a `ReadWriteOnce` one. **Nothing in the cluster will tell you which**, so the
comparison is yours to do: capacity, access modes, `storageClassName`, and any `selector` — all four have
to be satisfied by the same PV, and a claim is never given a volume that is smaller or less capable than
it asked for, only one that is equal or better.

**And `waiting` is not broken at all.** `standard` is `WaitForFirstConsumer`, so its claims are *supposed*
to sit `Pending` until a Pod that mounts them is scheduled — the provisioner wants to know which node
before it creates a local volume. Prove it rather than believe it:

```bash
kubectl run consumer --image=busybox:1.36 --restart=Never --labels=drill=7 \
  --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.36","command":["sh","-c","sleep 300"],"volumeMounts":[{"name":"v","mountPath":"/d"}]}],"volumes":[{"name":"v","persistentVolumeClaim":{"claimName":"waiting"}}]}}'
sleep 15
kubectl get pvc waiting
```

```
NAME      STATUS   VOLUME                                     CAPACITY   STORAGECLASS
waiting   Bound    pvc-2aaa5392-6247-42be-9de4-10891b6bb426   1Gi        standard
```

That is the trap in the pair, and it runs both ways: a `Pending` claim on a `WaitForFirstConsumer` class
is healthy and looks broken, and it means **`Pending` is not a diagnosis.** Read the class's
`VOLUMEBINDINGMODE` before you conclude anything, because on an `Immediate` class the same status is a
real fault and on this one it is the design.

**Fix it:**

```bash
kubectl delete pvc reports-data
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: reports-data, labels: { drill: "7" } }
spec:
  accessModes: [ ReadWriteOnce ]
  resources: { requests: { storage: 2Gi } }
EOF
kubectl rollout status deployment/reports --timeout=120s
kubectl get pvc reports-data
```

Dropping `storageClassName` entirely is the fix, not renaming it to `standard`: an omitted class means
*use the default*, which survives somebody else changing what the default is. Note also what had to
happen for the Deployment to recover — nothing. No rollout, no restart, no edit to the Pod template. The
scheduler retries, the claim binds, the Pod places. Row 3 was never the problem and it was never going
to need fixing.

**The habit:** `FailedScheduling` names the scheduler, and the scheduler is the component least likely to
be wrong — it is a pure function of things other controllers wrote down. When it declines, read *which
input it says is unresolved* and go there. And when you get there, if the status is `Pending` on storage,
the first command is `kubectl get storageclass`, because it answers both of the two questions that
matter: does the class exist, and is `Pending` supposed to be happening.

**Clean up:**

```bash
kubectl delete pod consumer --ignore-not-found
kubectl delete deploy,pvc -l drill --ignore-not-found
kubectl delete pv drill7-pv --ignore-not-found
```

</details>

---

## Drill 8 — "the deploy went out and not one Pod ever started"

**Target: 10 minutes** for all four, which is the point — see [the clock](#the-clock) above.

> **Ticket:** *"A batch of four services went out together and none of them is up. The cluster looks
> fine, the nodes look fine, and `kubectl get pods` is a wall of red words we have not seen before.
> Somebody said it is a registry outage. Somebody else said it is the images. We need to know which
> ones are the same problem and which are not."*

**Reproduce it** (run; don't read):

```bash
kubectl create namespace imagelab
kubectl -n imagelab create configmap appcfg --from-literal=settings.yml='mode: safe'
kubectl apply -n imagelab -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: badtag, labels: { drill: "8" } }
spec: { containers: [ { name: c, image: "nginx:1.27-alpine-nope" } ] }
---
apiVersion: v1
kind: Pod
metadata: { name: badregistry, labels: { drill: "8" } }
spec: { containers: [ { name: c, image: "registry.invalid.example/web:1" } ] }
---
apiVersion: v1
kind: Pod
metadata: { name: neverpull, labels: { drill: "8" } }
spec:
  containers:
    - name: c
      image: busybox:1.36.9
      imagePullPolicy: Never
      command: ["sh","-c","sleep 300"]
---
apiVersion: v1
kind: Pod
metadata: { name: crashloop, labels: { drill: "8" } }
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh","-c","test -f /etc/app/settings.yaml || { echo 'FATAL: /etc/app/settings.yaml missing, refusing to start' >&2; exit 78; }; sleep 300"]
      volumeMounts: [ { name: cfg, mountPath: /etc/app } ]
    - name: shipper
      image: busybox:1.36
      command: ["sh","-c","while true; do echo 'shipper: 0 events queued'; sleep 10; done"]
  volumes:
    - name: cfg
      configMap: { name: appcfg }
EOF
sleep 45
kubectl -n imagelab get pods
```

**Your symptom:**

```
NAME          READY   STATUS              RESTARTS
badregistry   0/1     ImagePullBackOff    0
badtag        0/1     ImagePullBackOff    0
crashloop     1/2     Error               3 (34s ago)
neverpull     0/1     ErrImageNeverPull   0
```

**Three different words in one column, and if you run `get pods` again you may see a fourth.** The
first two flip between `ErrImagePull` and `ImagePullBackOff` depending on whether you catch them
mid-attempt or mid-wait — same failure, two points in one retry loop, which is the first hint that this
column is describing *the kubelet's state* rather than your problem. Before you fix anything: which of those four
words are the same failure, and which are different? Sort them before you touch them — the ticket's
real question is how many problems there are, not how to fix any one of them.

<details>
<summary>Reveal</summary>

**Start by throwing away the STATUS column, because three of those four words are states rather than
causes.** `ImagePullBackOff` does not mean "the image is bad"; it means *a pull failed and the kubelet
is now waiting longer between retries*. The cause is only in the event text, and never in the status:

```bash
kubectl -n imagelab describe pod badtag      | grep 'Failed to pull' | head -1
kubectl -n imagelab describe pod badregistry | grep 'Failed to pull' | head -1
```

```
Failed to pull image "nginx:1.27-alpine-nope": ... failed to resolve reference
  "docker.io/library/nginx:1.27-alpine-nope": docker.io/library/nginx:1.27-alpine-nope: not found

Failed to pull image "registry.invalid.example/web:1": ... failed to do request:
  Head "https://registry.invalid.example/v2/web/manifests/1": dial tcp: lookup
  registry.invalid.example on 192.168.65.254:53: no such host
```

**Identical status, and the two least similar causes on the page.** The first got all the way to a
registry, authenticated, asked for a tag and was told it does not exist — the registry is *fine*. The
second never reached a registry at all: `no such host` is a DNS failure, and the address it names is
the node's resolver, not the cluster's. So "it's a registry outage" is wrong about the first and not
quite right about the second either — nothing is down, a name does not exist. One is a typo in a tag,
the other a typo in a hostname, and only the event text can tell you.

**Now the third, which is the useful one.** `ErrImageNeverPull` is not a variant of
`ImagePullBackOff`; it is the opposite kind of statement:

```bash
kubectl -n imagelab describe pod neverpull | grep ErrImageNeverPull | head -1
```

```
Container image "busybox:1.36.9" is not present with pull policy of Never
```

**No pull was attempted, so no pull failed.** `imagePullPolicy: Never` is an instruction to use only
what is already on the node, and the image is not there, so the kubelet refuses before it does
anything. That is why this is the one status in the set that needs no event: it *is* its own cause.
And it is the tell that separates a broken registry from a broken assumption — if you ever see this
in production, someone shipped a policy that expects a pre-loaded image onto a node that never got
one, and no amount of fixing the registry will help.

**The fourth was never an image problem at all**, which is why it is here. Note `1/2`, not `0/1`: one
container came up and one did not. The image pulled, the sandbox exists, the container was *created* —
and then it died:

```bash
kubectl -n imagelab describe pod crashloop | grep -E 'Exit Code|Back-off'
```

```
      Exit Code:    78
  Warning  BackOff  19s  kubelet  spec.containers{app}: Back-off restarting failed container app ...
```

An exit code and a back-off, and **nothing about why**. `describe` can tell you a container died; it
structurally cannot tell you what the process was complaining about, because that was written to
stdout and stderr, and those go somewhere else:

```bash
kubectl -n imagelab logs crashloop
```

```
Defaulted container "app" out of: app, shipper
FATAL: /etc/app/settings.yaml missing, refusing to start
```

There it is, in the one place nobody looked. Two things about that command worth having in your
fingers, because both cost people time on a clock:

**`kubectl logs` on a multi-container Pod picks one for you and says so.** It defaulted to `app`
because `app` is first in the spec — helpful here and dangerous in general, because on the day the
broken container is second you will read a healthy container's logs and conclude nothing is wrong.
Name it: `-c app`. And to read across the whole Pod at once:

```bash
kubectl -n imagelab logs crashloop --all-containers --prefix
kubectl -n imagelab logs -l drill=8 --all-containers --prefix --tail=2
```

```
[pod/crashloop/app]     FATAL: /etc/app/settings.yaml missing, refusing to start
[pod/crashloop/shipper] shipper: 0 events queued
```

**`--previous` is the flag for the case this drill *nearly* is.** Here the container is dying
repeatedly, so the current container's log is the failing run and plain `logs` works. The one that
catches people is a Pod that is `Running` now with a non-zero `RESTARTS` — the run that failed is
gone, and `--previous` is the only way to read it. Treat a non-zero restart count as a standing
instruction to run `logs --previous` before you believe the Pod is healthy.

Then fix the actual cause, which is one character:

```bash
kubectl -n imagelab get configmap appcfg -o jsonpath='{.data}'; echo
```

```
{"settings.yml":"mode: safe"}
```

The container wants `settings.yaml`; the ConfigMap has `settings.yml`. A ConfigMap volume is a
directory of files named after its keys, so a wrong key is a missing file — and the container is
right to refuse.

**Fix all four:**

```bash
kubectl -n imagelab create configmap appcfg --from-literal=settings.yaml='mode: safe' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n imagelab set image pod/badtag c=nginx:1.27-alpine    # image is a mutable field; the rest are not
kubectl -n imagelab delete pod badregistry neverpull crashloop  # blocking, and it has to be
kubectl apply -n imagelab -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: badregistry, labels: { drill: "8" } }
spec: { containers: [ { name: c, image: "nginx:1.27-alpine" } ] }
---
apiVersion: v1
kind: Pod
metadata: { name: neverpull, labels: { drill: "8" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      imagePullPolicy: IfNotPresent
      command: ["sh","-c","sleep 300"]
---
apiVersion: v1
kind: Pod
metadata: { name: crashloop, labels: { drill: "8" } }
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh","-c","test -f /etc/app/settings.yaml || { echo 'FATAL: /etc/app/settings.yaml missing, refusing to start' >&2; exit 78; }; sleep 300"]
      volumeMounts: [ { name: cfg, mountPath: /etc/app } ]
    - name: shipper
      image: busybox:1.36
      command: ["sh","-c","while true; do echo 'shipper: 0 events queued'; sleep 10; done"]
  volumes:
    - name: cfg
      configMap: { name: appcfg }
EOF
kubectl -n imagelab wait --for=condition=Ready pod --all --timeout=180s
```

Two things in that block are worth more than the fix. **`set image` works and nothing else would** —
a Pod is almost entirely immutable once created, and the API server will tell you so in a list of the
five fields you may change, which is why the other three had to be deleted and recreated. And the
delete is **blocking on purpose**: `--wait=false` here races the recreate, the `apply` lands on a Pod
that is still terminating, and you get *"pod updates may not change fields other than…"* — an error
about immutability that is really an error about timing.

**The reasoning worth keeping.** The kubelet's startup is a sequence, and each step fails in its own
vocabulary: no image (`ErrImagePull` → `ImagePullBackOff`, cause in the event), an image it was told
not to fetch (`ErrImageNeverPull`, cause in the status), a container that starts and dies
(`CrashLoopBackOff`, cause in the *logs*, and only in the logs). Read the `READY` fraction first —
`0/1` and `1/2` are different worlds — then let the depth choose your tool. `describe` for everything
before the process ran, `logs` for everything after.

</details>

**Verify it, then clean up:**

```bash
tools/verify-drill.sh act-7 8 "the status that names its own cause"
kubectl delete namespace imagelab
```

---

## Drill 9 — "four Pods will not start and the events are a wall"

**Target: 10 minutes** for all four — see [the clock](#the-clock) above.

> **Ticket:** *"A stateful service went out this morning and none of it came up. Four Pods, four
> different messages, and the on-call engineer's note says 'volume problems'. The storage team says
> nothing is wrong with the storage."*

**Reproduce it** (run; don't read):

```bash
kubectl create namespace mountlab
kubectl -n mountlab create secret generic appsecret --from-literal=DB_PASS=hunter2
kubectl -n mountlab create configmap appconf --from-literal=app.conf='listen: 8080'
kubectl apply -n mountlab -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: badkey, labels: { drill: "9" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","sleep 300"]
      env:
        - name: DB_PASSWORD
          valueFrom: { secretKeyRef: { name: appsecret, key: DB_PASSWORD } }
---
apiVersion: v1
kind: Pod
metadata: { name: badmap, labels: { drill: "9" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","sleep 300"]
      volumeMounts: [ { name: conf, mountPath: /etc/conf } ]
  volumes:
    - name: conf
      configMap: { name: app-config }
---
apiVersion: v1
kind: Pod
metadata: { name: readonly, labels: { drill: "9" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","echo 'state: starting' > /etc/conf/state.txt && sleep 300"]
      volumeMounts: [ { name: conf, mountPath: /etc/conf } ]
  volumes:
    - name: conf
      configMap: { name: appconf }
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: ledger, labels: { drill: "9" } }
spec:
  accessModes: [ ReadWriteOnce ]
  resources: { requests: { storage: 64Mi } }
---
apiVersion: v1
kind: Pod
metadata: { name: first-writer, labels: { drill: "9" } }
spec:
  nodeSelector: { kubernetes.io/hostname: netlab-worker }
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","echo primary > /data/owner; sleep 600"]
      volumeMounts: [ { name: d, mountPath: /data } ]
  volumes: [ { name: d, persistentVolumeClaim: { claimName: ledger } } ]
EOF
kubectl -n mountlab wait --for=condition=Ready pod/first-writer --timeout=180s
kubectl apply -n mountlab -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: second-writer, labels: { drill: "9" } }
spec:
  nodeSelector: { kubernetes.io/hostname: netlab-control-plane }
  tolerations: [ { operator: Exists } ]
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","sleep 600"]
      volumeMounts: [ { name: d, mountPath: /data } ]
  volumes: [ { name: d, persistentVolumeClaim: { claimName: ledger } } ]
EOF
sleep 30
kubectl -n mountlab get pods
```

**Your symptom:**

```
NAME            READY   STATUS                       RESTARTS
badkey          0/1     CreateContainerConfigError   0
badmap          0/1     ContainerCreating            0
first-writer    1/1     Running                      0
readonly        0/1     Error                        3 (63s ago)
second-writer   0/1     Pending                      0
```

**Four failures and four different statuses, and the on-call note is wrong about at least two of
them.** Before you fix anything: which of these ever reached a node, which ever mounted anything,
and which ever ran a process? Order them by how far they got.

<details>
<summary>Reveal</summary>

**Order them by depth and the diagnosis falls out, because each status is a different distance
travelled.** Read them in that order rather than top to bottom.

**`Pending` — never placed.** This one never got near a volume, so no volume tool will help:

```bash
kubectl -n mountlab describe pod second-writer | grep -A2 FailedScheduling
```

```
0/2 nodes are available: 1 node(s) didn't match PersistentVolume's node affinity,
1 node(s) didn't match Pod's node affinity/selector.
```

**Two clauses, and they must add up to the node count** — the arithmetic habit from
[drill 3](#drill-3--half-the-replicas-never-start). One node was refused by *your* selector, and one
node was refused by **the PersistentVolume's** node affinity, which is a field you never wrote. Go and
look at it:

```bash
kubectl get pv -o custom-columns='NAME:.metadata.name,CLAIM:.spec.claimRef.name,\
NODE:.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]'
```

```
NAME         CLAIM    NODE
pvc-7f7559…  ledger   netlab-worker
```

**The volume has a node.** The default StorageClass here provisions local directories, so when
`first-writer` was scheduled the provisioner created a directory on *that* machine and pinned the PV
to it — the `WaitForFirstConsumer` binding mode from [lesson 06](06-storage.md), doing exactly what it
says. `second-writer` asked for the same claim on the other node, and the volume cannot follow it.

Which is what `ReadWriteOnce` actually means, and it is worth saying out loud because the word invites
the wrong reading: **`ReadWriteOnce` is one *node*, not one Pod.** Two Pods on the same node may share
an RWO volume happily. One Pod on the wrong node cannot have it at all. So the fix is co-location, not
a second copy — and the reason this scheduler message exists rather than a mount error is that
Kubernetes checks volume topology *before* placing, precisely so you get a clear refusal instead of a
Pod stuck on a machine that can never mount.

**`ContainerCreating` — placed, and stuck trying to mount.** This is the only one of the four that is
genuinely a volume failure:

```bash
kubectl -n mountlab describe pod badmap | grep FailedMount | tail -1
```

```
MountVolume.SetUp failed for volume "conf" : configmap "app-config" not found
```

The name in the manifest is `app-config`; the object is `appconf`. Note the *shape* of this failure:
the kubelet will retry forever and never give up, because a ConfigMap that does not exist yet might
exist in a minute — a volume reference is not required to resolve at admission time. So a typo here
produces a Pod that waits patiently and indefinitely, with the answer in an event that scrolls.

**`CreateContainerConfigError` — placed, mounted, and refused before the process started.** Different
word, different stage:

```bash
kubectl -n mountlab describe pod badkey | grep "couldn't find" | tail -1
```

```
Error: couldn't find key DB_PASSWORD in Secret mountlab/appsecret
```

The Secret exists and the *key* does not — `DB_PASS`, not `DB_PASSWORD`. This is not a mount at all:
it is an environment variable, injected while the container is being configured, after every volume
has already succeeded. Which is why the status says `Config` and not `Mount`, and why looking at
volumes here wastes the clock.

**`Error` with a restart count — placed, mounted, configured, ran, and died.** The furthest of the
four, and the only one whose reason is not in `describe`:

```bash
kubectl -n mountlab logs readonly
```

```
sh: can't create /etc/conf/state.txt: Read-only file system
```

The mount **worked perfectly**. A ConfigMap volume is read-only and always has been — it is a
projection of an API object, and there is nowhere for a write to go. The container wants to keep state
in its config directory, which is a design mistake that only shows up once the config comes from
Kubernetes instead of from a file someone put there. This is the one where "nothing is wrong with the
storage" is exactly right.

**Fix all four:**

```bash
# 1. the key, not the Secret
kubectl -n mountlab delete pod badkey readonly second-writer
# 2. the ConfigMap the volume actually names
kubectl -n mountlab create configmap app-config --from-literal=app.conf='listen: 8080'
kubectl apply -n mountlab -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: badkey, labels: { drill: "9" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","sleep 300"]
      env:
        - name: DB_PASSWORD
          valueFrom: { secretKeyRef: { name: appsecret, key: DB_PASS } }
---
apiVersion: v1
kind: Pod
metadata: { name: readonly, labels: { drill: "9" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","echo 'state: starting' > /var/run/state.txt && sleep 300"]
      volumeMounts:
        - { name: conf, mountPath: /etc/conf }
        - { name: run, mountPath: /var/run }
  volumes:
    - name: conf
      configMap: { name: appconf }
    - name: run
      emptyDir: {}
---
apiVersion: v1
kind: Pod
metadata: { name: second-writer, labels: { drill: "9" } }
spec:
  nodeSelector: { kubernetes.io/hostname: netlab-worker }
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","sleep 600"]
      volumeMounts: [ { name: d, mountPath: /data } ]
  volumes: [ { name: d, persistentVolumeClaim: { claimName: ledger } } ]
EOF
kubectl -n mountlab wait --for=condition=Ready pod --all --timeout=180s
kubectl -n mountlab exec second-writer -- cat /data/owner      # primary — the same volume
```

The last line is the point of the fourth fault: `second-writer` now mounts the *same* RWO volume as
`first-writer`, reads what the other Pod wrote, and both are happy — because they are on one node.
Nothing about the volume changed.

**The reasoning worth keeping.** *Pending* and *ContainerCreating* are not two flavours of the same
problem; they are different components refusing at different times, and only one of them has anything
to do with volumes. Read the status word first and let it choose the tool:

```
  Pending                     -> the SCHEDULER refused. describe, read the FailedScheduling tally.
  ContainerCreating           -> the KUBELET is stuck mounting. describe, read FailedMount.
  CreateContainerConfigError  -> mounts succeeded; an env/config reference does not resolve.
  Error / CrashLoopBackOff    -> everything worked and the process disagreed. logs.
```

Each row up that list is one step further from your YAML and one step closer to your program, and the
status column tells you which step you are on for free.

</details>

**Verify it, then clean up:**

```bash
tools/verify-drill.sh act-7 9 "the field on the PV that refused it"
kubectl delete namespace mountlab
```

---

## Drill 10 — "the service is slow, and sometimes it just disappears"

**Target: 10 minutes** for all three — see [the clock](#the-clock) above.

> **Ticket:** *"Three symptoms on three workloads and we think they are the same underlying problem.
> One restarts on its own. One is just slow, and its own logs show nothing at all. One vanished
> overnight and came back on a different node. The node graphs look fine. Nobody has deployed
> anything."*

**Reproduce it** (run; don't read):

```bash
kubectl create namespace limitlab
kubectl apply -n limitlab -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: hungry, labels: { drill: "10" } }
spec:
  restartPolicy: Never
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","tail /dev/zero"]
      resources: { limits: { memory: 128Mi }, requests: { memory: 128Mi } }
---
apiVersion: v1
kind: Pod
metadata: { name: slow, labels: { drill: "10" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","while :; do :; done"]
      resources: { limits: { cpu: 50m }, requests: { cpu: 50m } }
---
apiVersion: v1
kind: Pod
metadata: { name: greedy, labels: { drill: "10" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","dd if=/dev/zero of=/scratch/blob bs=1M count=80; sleep 300"]
      resources: { limits: { ephemeral-storage: 16Mi }, requests: { ephemeral-storage: 16Mi } }
      volumeMounts: [ { name: s, mountPath: /scratch } ]
  volumes: [ { name: s, emptyDir: {} } ]
EOF
sleep 60
kubectl -n limitlab get pods
```

**Your symptom:**

```
NAME     READY   STATUS      RESTARTS
greedy   0/1     Error       0
hungry   0/1     OOMKilled   0
slow     1/1     Running     0
```

**`slow` is the interesting one, and it is the one that looks fine.** Three workloads, three fates,
and the ticket's guess is that they share a cause. Before you fix anything: **who killed each one?**
Name a component for each, and be specific — two of these three answers are not Kubernetes.

<details>
<summary>Reveal</summary>

**Start with `hungry`, because it is the only one that says what happened to it:**

```bash
kubectl -n limitlab describe pod hungry | grep -A2 'State:'
```

```
    State:          Terminated
      Reason:       OOMKilled
      Exit Code:    137
```

`137` is `128 + 9`, which is the shell's way of saying *killed by signal 9*. Nobody in Kubernetes sent
that signal. `limits.memory` becomes `memory.max` on the container's cgroup — the file you wrote by
hand in [Act IV lesson 01b](../act-4-one-pretends-many/01b-cgroups.md) — and when a process tries to
fault in a page past that ceiling the **kernel's OOM killer** takes it, synchronously, with no
negotiation and no event of its own. Kubernetes then *reports* what it found. The distinction matters
because it tells you where to look: there is no controller decision to audit here and no eviction to
find in the API. The evidence is a cgroup counter:

```bash
kubectl -n limitlab get pod hungry -o jsonpath='{.spec.containers[0].resources.limits.memory}{"\n"}'
```

The limit is the whole cause. `tail /dev/zero` will consume any number you write there, so the fix is
either a bigger number or a program that does not do that — and telling those two apart is the actual
engineering.

**Now `slow`, which reports nothing anywhere.** No restart, no event, no log line, `1/1 Running`, and
a service that misses its latency budget. Kubernetes has no field for this, so you have to go to the
node. Find its cgroup — note that the kubelet writes the UID with **underscores**, and the slice path
carries the Pod's QoS class:

```bash
N=$(kubectl -n limitlab get pod slow -o jsonpath='{.spec.nodeName}')
U=$(kubectl -n limitlab get pod slow -o jsonpath='{.metadata.uid}' | tr '-' '_')
F=$(docker exec $N sh -c "find /sys/fs/cgroup -maxdepth 6 -type d -name '*${U}*' | head -1")
echo $F
docker exec $N sh -c "cat $F/cpu.max; grep -E 'nr_periods|nr_throttled|throttled_usec' $F/cpu.stat"
```

```
/sys/fs/cgroup/kubelet.slice/kubelet-kubepods.slice/kubelet-kubepods-burstable.slice/
  kubelet-kubepods-burstable-pod64943435_907a_4817_ab21_9cbd7a1835eb.slice
5000 100000
nr_periods 1739
nr_throttled 1691
throttled_usec 91239598
```

**Read `5000 100000` first: that is `limits.cpu: 50m`, in the kernel's own units** — 5,000
microseconds of CPU time allowed in every 100,000-microsecond period. Not a share, not a priority: a
quota with a deadline. And `nr_throttled 1691` out of `nr_periods 1739` says this container was
stopped dead **in 97% of the periods it ran in** — every one of which is a hard stop until the next
period begins, up to 100ms of doing nothing while the request that is waiting keeps waiting.

Run it again twenty seconds later and `throttled_usec` will have climbed. That is the only signal this
failure produces, and it exists nowhere in the Kubernetes API — which is why "the app is slow and its
logs are clean" is a question about cgroups and not about the app. The enforcer is the kernel's **CFS
bandwidth controller**, and again nothing in Kubernetes decided anything: it wrote a number into a
file at container creation and walked away.

Note the asymmetry, because it is the whole point of `requests` versus `limits`:
**`limits.memory` kills you and `limits.cpu` slows you down.** Same word in the manifest, two
completely different enforcement regimes, and only one of them is survivable.

**Finally `greedy`, and this is the one Kubernetes did.** `Error` in the STATUS column is a summary;
the reason is on the Pod itself:

```bash
kubectl -n limitlab get pod greedy -o jsonpath='{.status.reason}: {.status.message}{"\n"}'
```

```
Evicted: Pod ephemeral local storage usage exceeds the total limit of containers 16Mi.
```

**`Evicted` is a Kubernetes verdict and the only one of the three that is.** No cgroup enforces
ephemeral storage — there is no `disk.max` — so the **kubelet's eviction manager** measures usage on a
housekeeping tick, compares it to the limit you declared, and *deletes the Pod*. That is a controller
decision, taken after the fact, by a component you can read the logs of and whose thresholds you can
configure. Which is why this is the one with a `.status.reason` at all: somebody in Kubernetes made
this call, so somebody in Kubernetes could write it down.

And it is why an evicted Pod behaves differently from a killed one. The object stays, in a terminal
state, holding the reason — that is your audit trail. A controller then makes a replacement somewhere
else, which is exactly the "vanished overnight and came back on a different node" in the ticket.

**Three symptoms, three enforcers, and the ticket's guess was wrong:**

```
  OOMKilled   ->  the kernel's OOM killer         limits.memory -> memory.max
  slow, silent->  the kernel's CFS bandwidth ctl  limits.cpu    -> cpu.max
  Evicted     ->  the kubelet's eviction manager  limits.ephemeral-storage (no cgroup at all)
```

Only the third is Kubernetes' decision. The first two are numbers Kubernetes wrote into cgroup files
and then stopped thinking about, which is why neither produces a controller event and why the middle
one produces nothing at all.

**Fix all three:**

```bash
kubectl -n limitlab delete pod hungry slow greedy
kubectl apply -n limitlab -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: hungry, labels: { drill: "10" } }
spec:
  restartPolicy: Never
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","sleep 300"]            # the program was the bug, not the limit
      resources: { limits: { memory: 128Mi }, requests: { memory: 128Mi } }
---
apiVersion: v1
kind: Pod
metadata: { name: slow, labels: { drill: "10" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","while :; do sleep 1; done"]
      resources: { limits: { cpu: 500m }, requests: { cpu: 100m } }
---
apiVersion: v1
kind: Pod
metadata: { name: greedy, labels: { drill: "10" } }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","dd if=/dev/zero of=/scratch/blob bs=1M count=80; sleep 300"]
      resources: { limits: { ephemeral-storage: 256Mi }, requests: { ephemeral-storage: 256Mi } }
      volumeMounts: [ { name: s, mountPath: /scratch } ]
  volumes: [ { name: s, emptyDir: {} } ]
EOF
kubectl -n limitlab wait --for=condition=Ready pod --all --timeout=180s
```

**The reasoning worth keeping.** When a workload misbehaves and nothing in Kubernetes says why, ask
which enforcer would have left a trace and where. An eviction leaves a `.status.reason` because a
controller decided it. An OOM kill leaves an exit code because the kernel decided it and Kubernetes
noticed afterwards. Throttling leaves **nothing but a counter on the node**, which is why it is the
one that gets misdiagnosed for weeks as a slow database. `kubectl` cannot see it; `cat cpu.stat` can.

</details>

**Verify it, then clean up:**

```bash
tools/verify-drill.sh act-7 10 "who made the third decision"
kubectl delete namespace limitlab
```

---

## What these ten have in common

Seven of the ten drills had **nothing wrong with the cluster**. In every case an object was accepted, stored, and read by exactly the loop that was supposed to read it — and that loop then did precisely what the field said. Drills 8, 9 and 10 are the exceptions, and they earn their place by going *below* the object — down to where the kubelet is turning a spec into a running process. Between them they teach two things the other seven cannot. **Those failures are ordered**, and the status word tells you which step you are on: no image, an image nobody was allowed to fetch, a volume that will not resolve, an env reference that does not exist, a container that starts and disagrees. Each step is one further from your YAML and one closer to your program, and each is read with a different tool. And **not every enforcer is Kubernetes.** Drill 10's three casualties were taken by three different authorities — the kernel's OOM killer, the kernel's CFS bandwidth controller, and the kubelet's eviction manager — and only the third left a `.status.reason`, because only the third was a decision anyone in Kubernetes made. The middle one leaves nothing but a counter on the node, which is why it is the failure that gets misdiagnosed for weeks.

Which is the diagnostic value of this act's spine. A workload failure is almost never "Kubernetes is broken"; it is a claim being kept faithfully that you did not mean to make. So the productive question is never "what is wrong with it" but **which loop is keeping which promise, and is that the promise I wrote?**

The six rows at the top of this page are that question made mechanical. Each `no` hands you one component and eliminates the rest — and the most common mistake on a real incident is starting at row 6 with a theory, when row 5 would have told you in one command.

---

↑ **[Act VII overview](README.md)** · Prev: **[Test yourself](test-yourself.md)** · Next: **[In the wild](in-the-wild.md)** →
