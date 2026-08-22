# Act VII — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act VII. This checks whether you can *use* it. Real failures never arrive labelled "that was the wrong probe" or "your ConfigMap was mounted with `subPath`" — they arrive as a symptom, a shrug, and a ticket. Each drill below puts your cluster into a **real broken state**, hands you only the symptom, and asks you to find the cause with the act's tools.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** Reading it closely spoils the hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud what you think is wrong and which field or command would prove it — *then* look.
3. **Open the reveal only after you've tried.**

**Where:** the same `kind` cluster as the lessons. If you do not have it, [the Act V lab lesson](../act-5-kubernetes/01-lab-with-kind.md) builds it in a minute.

Unlike Act VI, nothing here can break your cluster. These drills break *workloads*, which is what you will actually be paged about. The cost of abandoning one halfway is some leftover objects, and this catches all of it:

```bash
kubectl delete deploy,sts,ds,job,cronjob,hpa,svc,cm,secret -l drill --ignore-not-found
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

## Drill 1 — "the deploy finished but the site is down"

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

---

## Drill 2 — "it worked in staging"

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

---

## Drill 3 — "half the replicas never start"

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

---

## Drill 4 — "we scaled it down but the bill didn't move"

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

## Drill 5 — "the cron job hasn't run and nothing is wrong"

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

---

## Drill 6 — "the autoscaler is broken"

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

---

## What these six have in common

Five of the six drills had **nothing wrong with the cluster and nothing wrong with the container image**. In every case an object was accepted, stored, and read by exactly the loop that was supposed to read it — and that loop then did precisely what the field said.

Which is the diagnostic value of this act's spine. A workload failure is almost never "Kubernetes is broken"; it is a claim being kept faithfully that you did not mean to make. So the productive question is never "what is wrong with it" but **which loop is keeping which promise, and is that the promise I wrote?**

The six rows at the top of this page are that question made mechanical. Each `no` hands you one component and eliminates the rest — and the most common mistake on a real incident is starting at row 6 with a theory, when row 5 would have told you in one command.

---

↑ **[Act VII overview](README.md)** · Prev: **[Test yourself](test-yourself.md)** · Next: **[In the wild](in-the-wild.md)** →
