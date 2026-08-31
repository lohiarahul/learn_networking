# Act VI — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act VI. This checks whether you can *use* it. Real failures never arrive labelled "this is a stale status field" or "that manifest will not parse" — they arrive as a symptom, a shrug, and a ticket. Each drill below puts your cluster into a **real broken state**, hands you only the symptom, and asks you to find the cause with the act's tools.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** Reading it closely spoils the hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud what you think is wrong and which file or tool would prove it — *then* look.
3. **Open the reveal only after you've tried.**
4. **Then verify it — and say what was wrong.** Every drill below ends with a `Verify it` line:

   ```bash
   tools/verify-drill.sh act-6 <n> "your one-line diagnosis"
   ```

   It exits `0` only if the cluster is genuinely repaired **and** the cause you typed is the right
   one. It checks by *function* rather than by configuration — a Pod created five seconds ago
   acquiring a `spec.nodeName` proves a scheduler is reconciling, where a file being back on disk
   proves nothing — and it will not tell you the answer: the expected cause is stored as a hash, so
   reading [`drills/`](../../drills/README.md) spoils nothing. This exists because the reveal above is
   graded by the person who just failed to solve the drill, which is the most reliable way anyone
   arrives at an exam confident and unready.

**Where:** the same `kind` cluster as the lessons. If you do not have it, [the Act V lab lesson](../act-5-kubernetes/01-lab-with-kind.md) builds it in a minute — pinned, and the pin matters here. **Drill 5 needs a server at 1.29 or newer**: it breaks the cluster by deleting `clusterrolebinding kubeadm:cluster-admins` and recovers through `/etc/kubernetes/super-admin.conf`, and neither of those exists on an older node image. `kubectl version` tells you the server version; if it is below 1.29 the drill's reproduce step fails `NotFound` and there is nothing to hunt.

**One warning this act needs and the others did not.** These drills stop control-plane components and edit files the kubelet is watching. Every one has a `Fix it` block that restores the cluster, and you should run it before starting the next drill. If you abandon a drill halfway, run this — it is the single check that catches almost everything:

```bash
docker exec netlab-control-plane ls /etc/kubernetes/manifests/     # all four, every time
```

A cluster missing a control-plane component looks completely healthy until the moment it needs the thing that is missing.

**Start every drill by descending the five questions from [the diagnostic lesson](08-when-the-control-plane-breaks.md).** They are the method these drills exist to build:

```
  1. Does the API server answer?    kubectl get --raw /readyz          needs: everything
  2. What does the cluster say?     events, describe, logs --previous  needs: the API server
  3. Is the container running?      crictl ps -a / crictl pods         needs: the runtime
  4. What is the kubelet saying?    journalctl -u kubelet              needs: systemd
  5. What is on the disk?           manifests, certs, df               needs: nothing
```

```bash
CP=netlab-control-plane        # used by every drill below
```

---

## The clock

Every drill below carries a **target time**, and this is the one thing these drills do that the
lessons deliberately do not. The course is built to make you understand; a certification is scored on
whether you can act inside a budget, and those are different skills that look identical from the
inside. So: Eight rather than seven, because this act's method is a *descent* — you may have to go down three layers before a tool answers — and because in real life these are the failures you get paged for rather than graded on.

Three rules, taken straight from [the exam-day pacing doctrine](../../exam-prep/exam-day.md):

1. **Start the clock when the symptom appears**, not when you start the reproduce block. Building the
   broken state is setup, and on the exam somebody else has already done it.
2. **At the target, say your best hypothesis out loud** even if you are not confident. Naming a wrong
   hypothesis at 8 minutes is worth more than a right one at twenty, because the wrong one is
   falsifiable in one command and the exam pays for closed tasks.
3. **At 10 minutes, stop and open the reveal.** That is not giving up, it is the exam's own rule —
   *"the moment a task passes 10 minutes, flag it and move on"* — and the skill it builds is the
   costly one. A task that eats 25 minutes has cost you three others worth the same marks.

Run each drill untimed the first time if you like. Then run it again, weeks later, with a timer, and
notice that the second number is the one that predicts anything.

## Drill 1 — "kubectl works, but nothing we deploy ever starts"

**Target: 8 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"We deployed a new service an hour ago and it is still `Pending`. `kubectl` is fine, the nodes say `Ready`, there is loads of spare CPU, and the manifest is byte-identical to one that worked last week. We've deleted and re-applied it three times. Nothing."*

**Reproduce it** (run; don't read):

```bash
docker exec $CP sh -c 'mkdir -p /tmp/drill && mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/drill/'
sleep 20
kubectl create deployment shipping --image=hashicorp/http-echo -- /http-echo -text=x -listen=:5678
sleep 15
kubectl get pods -l app=shipping -o wide
```

**Your symptom:** a `Pending` Pod, and nothing obviously wrong anywhere.

<details>
<summary>Reveal</summary>

**Question 1 passes** — the API server answers, which already tells you something: whatever is broken is not the thing you talk to.

**Question 2 is where this drill is solved, and the decisive output is an absence.**

```bash
kubectl get pod -l app=shipping -o jsonpath='{.items[0].spec.nodeName}'; echo
kubectl describe pod -l app=shipping | tail -6
```

`spec.nodeName` is **empty**, and the events say **`<none>`**.

Those two facts together are the whole diagnosis. An empty `nodeName` means nothing has placed the Pod. `Events: <none>` means nothing even *looked* at it — because a scheduler that had looked and refused would have said so there, naming what it could not satisfy. No CPU complaint, no taint complaint, no complaint at all. Nobody is home.

So the question is not "why won't it schedule" but "which process should have, and is it running":

```bash
kubectl -n kube-system get pods -l tier=control-plane
```

Three components where there should be four. The scheduler is gone.

**The reasoning worth keeping:** the ticket's every detail was a red herring *because* the reporter was looking at the workload. Spare CPU, a known-good manifest, `Ready` nodes — all true, all irrelevant. `spec.nodeName` and an empty event list name the missing loop in two commands, and neither is about the Deployment at all.

</details>

**Fix it:**

```bash
docker exec $CP sh -c 'mv /tmp/drill/kube-scheduler.yaml /etc/kubernetes/manifests/'
sleep 25
kubectl get pods -l app=shipping -o wide      # scheduled and running
kubectl delete deployment shipping
docker exec $CP ls /etc/kubernetes/manifests/
```

**Verify it:**

```bash
tools/verify-drill.sh act-6 1 "the component you think was missing"
```

---

## Drill 2 — "the dashboard says everything is healthy and it is not"

**Target: 8 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Our monitoring says `payments` is at 3/3 and has been all morning. Support says a third of requests fail. We've checked the Service, the endpoints, the Ingress. The Deployment reports healthy. Somebody is lying."*

**Reproduce it** (run; don't read):

```bash
kubectl create deployment payments --image=hashicorp/http-echo --replicas=3 -- /http-echo -text=p -listen=:5678
kubectl wait --for=condition=Available deployment/payments --timeout=90s
docker exec $CP sh -c 'mkdir -p /tmp/drill && mv /etc/kubernetes/manifests/kube-controller-manager.yaml /tmp/drill/'
sleep 20
POD=$(kubectl get pod -l app=payments -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $POD --wait=false
sleep 20
kubectl get deployment payments
```

**Your symptom:** `READY 3/3`, and support is right.

<details>
<summary>Reveal</summary>

Count the Pods. That is the entire first move, and it is the move nobody makes because the Deployment already answered the question:

```bash
kubectl get deployment payments
kubectl get pods -l app=payments --no-headers | grep -c .
```

**`3/3` against two Pods.** The Deployment is not summarising anything — it is reporting a stored field:

```bash
kubectl get deployment payments -o jsonpath='{.status.readyReplicas}{"\n"}'
```

`3`. And the process that writes `status.readyReplicas` is the controller manager:

```bash
kubectl -n kube-system get pods -l tier=control-plane
```

Gone. So you are reading the last thing it noticed before it died, frozen. Confirm it with the timestamp, which is the detail that turns a suspicion into a finding:

```bash
kubectl get deployment payments -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.lastUpdateTime}{"\n"}{end}'
```

Every condition's `lastUpdateTime` is stuck at the moment before the component stopped.

**The reasoning worth keeping — and this is the drill's real point:** a stopped controller does not only stop *acting*, it stops **knowing**, and it does not say so. Which makes a whole class of tool useless exactly when you need it. `kubectl wait --for=condition=Available deployment/payments` returns **success in under a second** here, because the condition it reads is the same stale field. Anything that waits on a field cannot outrun the controller that writes the field.

So the general habit: when a status and a `get` disagree, believe the `get`. `status` is a note a controller left behind, not an observation the API server makes for you.

</details>

**Fix it:**

```bash
docker exec $CP sh -c 'mv /tmp/drill/kube-controller-manager.yaml /etc/kubernetes/manifests/'
kubectl get pods -l app=payments -w        # Ctrl-C once a third Pod appears (~20s: leader election)
kubectl delete deployment payments
docker exec $CP ls /etc/kubernetes/manifests/
```

**Verify it:**

```bash
tools/verify-drill.sh act-6 2 "the component you think was missing"
```

---

## Drill 3 — "kubectl died after a config change and we cannot get in"

**Target: 8 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Someone tuned an API server flag about twenty minutes ago. Now every `kubectl` command hangs and times out. We can SSH to the node. We have no idea what they changed and they have gone home."*

**Reproduce it** (run; don't read — and this one genuinely takes the cluster down):

```bash
docker exec $CP cp /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/apiserver.good
docker exec $CP sh -c "sed 's|    - kube-apiserver|    - kube-apiserver\n    - --audit-log-maxage=verymuch|' \
  /tmp/apiserver.good > /etc/kubernetes/manifests/kube-apiserver.yaml"
sleep 30
kubectl get nodes
```

**Your symptom:** `Unable to connect to the server`. Your whole Act V toolkit is silent.

<details>
<summary>Reveal</summary>

**Question 1 fails, so stop typing `kubectl`.** Everything at Question 2 is unavailable — no events, no `describe`, no `logs`. Descend.

**Question 3.** The runtime does not care that the API server is down:

```bash
docker exec $CP crictl ps -a --name kube-apiserver
```

An **`Exited`** container with a recent timestamp and a climbing `ATTEMPT`. That climbing count is itself information: the kubelet is starting it, it is dying, and the kubelet is trying again on a back-off — which is what `CrashLoopBackOff` is, seen from below.

Crucially, a container *exists*. So a process ran, so a process has an opinion:

```bash
CID=$(docker exec $CP sh -c "crictl ps -a --name kube-apiserver -q | head -1")
docker exec $CP crictl logs $CID 2>&1 | tail -5
```

```
Error: invalid argument "verymuch" for "--audit-log-maxage" flag: strconv.ParseInt: ...
```

One line, from the binary itself, naming the flag and the value. You did not need to know what they changed — the process that refused to start told you.

Then confirm against the file and fix it:

```bash
docker exec $CP grep -n 'audit-log-maxage' /etc/kubernetes/manifests/kube-apiserver.yaml
```

**The reasoning worth keeping:** the instinct when `kubectl` dies is to keep trying `kubectl`, and it is always wasted. One level down, `crictl` is completely unaffected — it talks to the container runtime, which never needed the API server. And the whole diagnosis was two commands, because a container that ran leaves logs.

</details>

**Fix it:**

```bash
docker exec $CP cp /tmp/apiserver.good /etc/kubernetes/manifests/kube-apiserver.yaml
until kubectl get nodes 2>/dev/null; do sleep 2; done
docker exec $CP rm -f /tmp/apiserver.good
```

**Verify it:**

```bash
tools/verify-drill.sh act-6 3 "the flag whose value was rejected"
```

---

## Drill 4 — "same symptom, and this time crictl shows nothing"

**Target: 8 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Identical to the last one — `kubectl` times out after someone edited a manifest. But we tried your `crictl` trick and it returns nothing at all. We think the runtime is broken too."*

**Reproduce it** (run; don't read):

```bash
docker exec $CP cp /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/apiserver.good
docker exec $CP sh -c 'printf "\n    - --oops\n  bad: [\n" >> /etc/kubernetes/manifests/kube-apiserver.yaml'
sleep 60
kubectl get nodes
docker exec $CP crictl ps -a --name kube-apiserver
```

**Your symptom:** `kubectl` is dead, and `crictl ps -a` is empty.

<details>
<summary>Reveal</summary>

The runtime is fine — prove it in one command before you believe the ticket:

```bash
docker exec $CP crictl ps | head -5
```

Other containers are running happily. So `crictl` works; there is genuinely no API server container.

**That emptiness is the finding, not a dead end.** A container that never existed cannot have logs, so the failure happened *before* any process was created — which means it happened in whatever was supposed to create it. Descend to Question 4:

```bash
docker exec $CP journalctl -u kubelet --since '-2min' --no-pager | grep -i 'manifest\|parse' | tail -5
```

```
"Could not process manifest file" err="/etc/kubernetes/manifests/kube-apiserver.yaml:
 couldn't parse as pod(yaml: line 139: did not find expected key), please check config file"
```

**A file, and a line number.** The kubelet could not read the manifest, so it never attempted anything.

And if you want certainty rather than inference, one more command separates this from a third case that also produces no container:

```bash
docker exec $CP crictl pods --name kube-apiserver
```

Empty — **not even a sandbox**. Had the file parsed and the *image* been wrong, the kubelet would have got as far as creating the Pod's network namespace and you would see a `Ready` sandbox with nothing inside it. No sandbox at all means the failure was earlier than that: the file itself.

**The reasoning worth keeping:** empty output at one layer is a **pointer to the layer below**, never an absence of information. Drills 3 and 4 have identical symptoms at Questions 1 and 2, and one command at Question 3 tells them apart — a container to read, or nothing to read. The evidence always lives at the lowest layer that got far enough to have an opinion.

</details>

**Fix it:**

```bash
docker exec $CP cp /tmp/apiserver.good /etc/kubernetes/manifests/kube-apiserver.yaml
until kubectl get nodes 2>/dev/null; do sleep 2; done
docker exec $CP rm -f /tmp/apiserver.good
```

**Verify it:**

```bash
tools/verify-drill.sh act-6 4 "the step the kubelet never got past"
```

---

## Drill 5 — "we are locked out of our own cluster and nothing is down"

**Target: 8 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Every `kubectl` command says Forbidden. Not a timeout — Forbidden. Our kubeconfig has not changed, the certificate has months left, and the cluster is up: the app is serving traffic fine. How can we be denied by a cluster that we own?"*

**Reproduce it** (run; don't read):

```bash
kubectl get clusterrolebinding kubeadm:cluster-admins -o yaml > /tmp/crb-backup.yaml
kubectl delete clusterrolebinding kubeadm:cluster-admins
sleep 5
kubectl get nodes
```

**Your symptom:** `Forbidden`, from a healthy cluster, with an unexpired certificate.

<details>
<summary>Reveal</summary>

Read the error properly first, because it is unusually informative:

```
Error from server (Forbidden): nodes is forbidden: User "kubernetes-admin"
cannot list resource "nodes" in API group "" at the cluster scope
```

It **names you**. Which means your certificate was read, its signature was verified against the cluster CA, and the API server knows precisely who you are. Confirm that, because it splits the problem in half:

```bash
kubectl auth whoami
```

That works. `kubernetes-admin`, group `kubeadm:cluster-admins`.

**So authentication is fine and authorisation is not** — and those are different systems with different homes. Your identity is a certificate: a file, signed by a CA on the node's disk. Your *permission* is an object, in the store. Only one of those can be deleted by a `kubectl` command.

```bash
kubectl auth can-i --list
```

`system:basic-user` and `system:discovery` — the bare minimum every authenticated user gets. Everything your group granted you is gone.

Now, how do you fix an authorisation object when you are not authorised to write one? With the credential that does not depend on authorisation objects at all:

```bash
docker exec $CP kubectl --kubeconfig /etc/kubernetes/super-admin.conf get nodes
```

That works completely. `O=system:masters` is wired into the API server itself rather than into anything in the store, so it **bypasses the permission check** instead of being granted by it. This is the emergency that file exists for.

```bash
docker exec $CP kubectl --kubeconfig /etc/kubernetes/super-admin.conf \
  create clusterrolebinding kubeadm:cluster-admins \
  --clusterrole=cluster-admin --group=kubeadm:cluster-admins
kubectl get nodes
```

**The reasoning worth keeping:** `Forbidden` and `Unable to connect` are opposite diagnoses and people conflate them under "kubectl is broken". A timeout means the API server is not there. `Forbidden` means it is there, it read your credential, it recognised you, and it declined — so the problem is an object, not a process, and never your certificate. Note also what a full etcd loss would look like from here: **exactly this**, because that binding was in the store too.

</details>

**Fix it** — already done above. Confirm, and clean up:

```bash
kubectl get nodes                    # answers again
rm -f /tmp/crb-backup.yaml
```

**Verify it:**

```bash
tools/verify-drill.sh act-6 5 "the object that was deleted"
```

---

## Drill 6 — "the drain has been running for half an hour"

**Target: 8 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Patching a node. The drain has been going for thirty minutes and has not finished. It keeps printing something every few seconds so we assume it is making progress. Do we let it run? We have a maintenance window closing."*

**Reproduce it** (run; don't read):

```bash
kubectl create deployment checkout --image=hashicorp/http-echo --replicas=2 -- /http-echo -text=c -listen=:5678
kubectl wait --for=condition=Available deployment/checkout --timeout=90s
kubectl create poddisruptionbudget checkout-pdb --selector=app=checkout --min-available=2
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=45s
```

**Your symptom:** a drain that scrolls, waits, then times out having achieved nothing.

<details>
<summary>Reveal</summary>

**The answer was on the screen the whole time, and the reporter scrolled past it.** That is the drill.

```
error when evicting pods/"checkout-..." -n "default" (will retry after 5s):
Cannot evict pod as it would violate the pod's disruption budget.
```

Every five seconds, naming the mechanism. Which is the single most useful thing to know about a stuck drain: **there are two kinds, and the output tells you which.** A drain refused by policy is *loud* — it says why, repeatedly, forever. A drain waiting on a Pod that will not terminate is *silent*. "It keeps printing something" was the diagnosis, mistaken for a sign of progress.

Confirm it against the object:

```bash
kubectl get pdb
kubectl describe pdb checkout-pdb | tail -8
```

`ALLOWED DISRUPTIONS: 0`. A budget insisting both replicas stay available, so no eviction can ever be permitted. `kubectl` treats a rejection as *not yet* rather than *no* and retries — correct in the normal case, where a rolling update clears in seconds, and hopeless here.

And note where the drain is running, because it changes where you look: **it is a loop in your terminal, not in the cluster.** There is no drain object, no controller and no status field, so there is nothing to inspect *about the drain* — only about the node:

```bash
kubectl get pods -A -o wide --field-selector spec.nodeName=netlab-worker
```

Whatever is still listed, minus the DaemonSet Pods, is what it is waiting on. Had the terminal been genuinely silent, that list would be the start of a different investigation: a Pod stuck `Terminating` means the eviction was *accepted* and the container is not stopping — a long `terminationGracePeriodSeconds` by design, or a process ignoring `SIGTERM`.

The fix is a conversation, not a command. Either the application genuinely cannot lose a replica right now — in which case scale it up first and the budget satisfies itself — or the budget is wrong:

```bash
kubectl scale deployment checkout --replicas=3
kubectl wait --for=condition=Available deployment/checkout --timeout=90s
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=60s
```

**The reasoning worth keeping:** read the output of a long-running command before deciding it is progress. Then pass `--timeout` to every interactive drain, for the *silent* case — because that one genuinely is indistinguishable from being nearly done. And check `ALLOWED DISRUPTIONS: 0` before you open a maintenance window rather than thirty minutes into it.

</details>

**Fix it:**

```bash
kubectl uncordon netlab-worker
kubectl delete deployment checkout
kubectl delete pdb checkout-pdb --ignore-not-found
kubectl get nodes                                  # both Ready, neither SchedulingDisabled
docker exec $CP ls /etc/kubernetes/manifests/      # all four
```

**Verify it:**

```bash
tools/verify-drill.sh act-6 6 "the kind of object that refused the eviction"
```

---

## Drill 7 — "the node is fine and the cluster says it does not exist"

**Target: 8 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"We restored an etcd snapshot last night after an incident. This morning one worker is missing from `kubectl get nodes` entirely. But we can SSH to it, its kubelet is running, and `crictl ps` shows our containers serving traffic on it. Do we rebuild the node?"*

**Reproduce it** (run; don't read):

```bash
kubectl get node netlab-worker -o yaml > /tmp/node-backup.yaml
kubectl delete node netlab-worker
sleep 30
kubectl get nodes
docker exec netlab-worker crictl ps | head -4
```

**Your symptom:** one node in `kubectl get nodes`, and a second machine cheerfully running containers.

<details>
<summary>Reveal</summary>

Do not rebuild anything. Ask what a Node actually is first.

It is an object, at `/registry/minions/<name>` — and a snapshot taken before that node joined does not contain it. So the record is missing while the machine is untouched. Two independent facts, and only one of them is a problem.

Wait as long as you like: it does not come back on its own. Find out why, from the component that would have to do it:

```bash
docker exec netlab-worker journalctl -u kubelet --since '-1min' --no-pager | grep -i 'node' | tail -5
```

```
"Error updating node status, will retry" err="error getting node \"netlab-worker\": nodes \"netlab-worker\" not found"
"Unable to update node status" err="update node status exceeds retry count"
```

**It is trying to `update` a record that does not exist, and it has no path for "then create it."** A kubelet registers **once**, at startup. Everything afterwards assumes the Node object is there. So a running kubelet will retry forever and never succeed, and every other thing it tries is refused as well — you will see `no relationship found between node 'netlab-worker' and this object`, because the authorizer that grants a kubelet access does so via a graph rooted at a Node that is no longer there.

Which makes the fix a one-liner, and not the one people reach for:

```bash
docker exec netlab-worker systemctl restart kubelet
sleep 20
kubectl get nodes
```

Back in under a second, `Ready` shortly after. **Not `kubeadm join`** — joining is for a node with no credentials. This node's credential is a client certificate in a file on its own disk, which no snapshot restore ever touched, so it can simply register again.

**The reasoning worth keeping — and it generalises past this ticket:** a restore reverts the cluster's *beliefs*, not the world. Anything recorded after the snapshot must be re-created, anything running that the store no longer knows about keeps running until something looks, and **making things look is a step you have to take.** That same kubelet restart is also what reaps the orphaned containers a restore leaves serving traffic. If you take one habit from this act, let it be: after a restore, restart the kubelets.

</details>

**Fix it** — done above. Confirm:

```bash
kubectl get nodes                    # both Ready
kubectl -n kube-system get pods -o wide | grep netlab-worker    # kube-proxy and CNI back
rm -f /tmp/node-backup.yaml
```

**Verify it:**

```bash
tools/verify-drill.sh act-6 7 "the process that has to re-register the node"
```

---


## Drill 8 — "the fix that worked last month is refused too"

**Target: 8 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

*(This one has no command at the end of it. That is the drill.)*

> **Ticket:** *"Same node, same maintenance window as drill 6. The drain is refused again, and this time
> the Pod belongs to `team-b`, who are not us. So we did what worked last month and scaled their
> Deployment up — `kubectl scale` said `scaled`, and nothing happened. No error. The window closes in
> forty minutes and the node still has not been patched. What do we do?"*

**Reproduce it** (run; don't read):

```bash
kubectl create namespace team-b
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: ResourceQuota
metadata: { name: tenant-cap, namespace: team-b }
spec:
  hard: { pods: "1" }
**Verify it:**

```bash
tools/verify-drill.sh act-6 8 "the kind of object whose cap was hit"
```

---
apiVersion: apps/v1
kind: Deployment
metadata: { name: ledger, namespace: team-b }
spec:
  replicas: 1
  selector: { matchLabels: { app: ledger } }
  template:
    metadata: { labels: { app: ledger } }
    spec:
      containers:
        - name: c
          image: hashicorp/http-echo
          args: [ "-text=ledger", "-listen=:5678" ]
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: ledger-pdb, namespace: team-b }
spec:
  minAvailable: 1
  selector: { matchLabels: { app: ledger } }
EOF
kubectl -n team-b rollout status deployment/ledger --timeout=120s

kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=20s
kubectl -n team-b scale deployment/ledger --replicas=2
sleep 8
kubectl -n team-b get deployment ledger
```

**Your symptoms**, and there are three of them:

```
error when evicting pods/"ledger-..." -n "team-b" (will retry after 5s):
Cannot evict pod as it would violate the pod's disruption budget.

deployment.apps/ledger scaled

NAME     READY   UP-TO-DATE   AVAILABLE   AGE
ledger   1/2     1            1           1m
```

The drain is refused. The scale is **accepted**. And one replica exists where two were asked for, with
no error anywhere near the command that asked.

**Your move, and it is not a command.** Find why the second replica does not exist, then enumerate every
way you *could* get this node drained in the next forty minutes — and for each one, say what it does to
somebody who is not in this ticket. One of them is right and it is not the fastest.

<details>
<summary>Reveal</summary>

**Where the missing replica went.** `kubectl scale` edited a Deployment and that is all it claims to have
done; the thing that creates a Pod is the ReplicaSet controller, and the thing that refuses one is
admission. So the refusal is in a controller's event stream, not yours:

```bash
kubectl -n team-b describe rs -l app=ledger | grep -i forbidden
```

```
Error creating: pods "ledger-..." is forbidden: exceeded quota: tenant-cap,
requested: pods=1, used: pods=1, limited: pods=1
```

`team-b` has a **ResourceQuota** capped at one Pod. Which is Act VII's spine arriving in a maintenance
window: *every field is a claim read by a different loop*, and when the loop that reads yours is refused
by an admission controller, your terminal is not on the path the error takes. `kubectl get deployment`
showing `1/2` with a successful `scale` behind it is the whole signature — and it is the reason this drill
gives you no error message to search for.

**And the blocker is not in your namespace, which is why one habit matters.** Drill 6's `kubectl get pdb`
lists the current namespace and would have shown nothing here:

```bash
kubectl get pdb -A
```

```
NAMESPACE   NAME         MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
team-b      ledger-pdb   1               N/A               0                     2m
```

**`-A` before a maintenance window, every time.** A node hosts whoever the scheduler put there, so the
set of people who can block your drain is not the set of people you know about.

Now the options, which is what the drill is for. Four of them work and three of them are somebody else's
decision to make:

| Option | Drains the node? | What it does to `team-b` |
|---|---|---|
| `drain --force --disable-eviction` | yes, immediately | Deletes their only Pod, bypassing the eviction API entirely. Their service goes to zero for as long as a reschedule takes. **The PDB existed to prevent exactly this**, and the flag's purpose is to override it. |
| `kubectl -n team-b delete pdb ledger-pdb` | yes | Same outage, and the protection is now gone permanently. Nobody will notice until the next incident, when it does not stop that one either. |
| Raise `tenant-cap` to `pods: 2` | yes, cleanly | No outage at all — but you have changed another team's capacity and cost envelope to unblock your own maintenance, and there is no record that says why. |
| Fix the PDB to `maxUnavailable: 1` | yes, cleanly | No outage, and it is the *correct* object — but it is their object. |

Notice what the table does not contain: an option that is fast, safe, and yours. That is not a gap in the
drill, it is the finding. **A cluster is one machine and a namespace is not a boundary against
maintenance** — the node is shared, so a decision about the node is a decision about every tenant on it,
and the only question is whether you make it deliberately or by reaching for `--force`.

**So the right move is to arrive at the conversation with the answer already worked out**, which takes
about two minutes and is the actual professional skill:

> *Node `netlab-worker` needs patching in the window. Your `ledger` Pod is on it. `ledger-pdb` says
> `minAvailable: 1` on a 1-replica Deployment, so `ALLOWED DISRUPTIONS` is 0 and no eviction can ever be
> permitted — the budget currently forbids the maintenance it was meant to survive. Two ways out: raise
> `tenant-cap` to 2 for twenty minutes and we drain with no downtime, or change the PDB to
> `maxUnavailable: 1`, which is what "one at a time" is actually spelled as. Your call; I need it by 14:40.*

Then prove the second option, because it is the one worth remembering:

```bash
kubectl -n team-b delete pdb ledger-pdb
kubectl -n team-b apply -f - <<'EOF'
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: ledger-pdb, namespace: team-b }
spec:
  maxUnavailable: 1
  selector: { matchLabels: { app: ledger } }
EOF
kubectl get pdb -A
kubectl uncordon netlab-worker
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=60s | tail -2
```

```
NAMESPACE   NAME         MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
team-b      ledger-pdb   N/A             1                 1                     5s

pod/ledger-... evicted
node/netlab-worker drained
```

**Same workload, same one replica, same protection against a bad rollout — and now the node can be
drained.** `minAvailable: 1` on a single-replica Deployment is not a strict policy, it is a
**misconfiguration that reads as one**: it says "this may never be disrupted", which no cluster can
honour and no maintenance can work around. `maxUnavailable: 1` says "one at a time", which is what
whoever wrote it meant. The general check is arithmetic: **if a PDB's selector matches exactly as many
Pods as `minAvailable` requires, `ALLOWED DISRUPTIONS` is 0 forever.** That is a linting rule, and it is
worth running over every PDB you own before somebody else's maintenance window finds it for you.

**One last thing, and it is the blast radius of merely trying.** Look at the node:

```bash
kubectl get node netlab-worker
```

```
netlab-worker   Ready,SchedulingDisabled
```

A drain that **failed** still cordoned. `drain` cordons first and does not roll it back on failure, so
every unsuccessful attempt above left the cluster one node smaller for scheduling — silently, for
everybody, including tenants who were never in the ticket. Nothing is broken and nothing will report it;
new Pods simply stop being placed there, and on a two-node cluster that is half your capacity. `kubectl
get nodes` after any drain, successful or not, and `uncordon` before you walk away.

</details>

**Fix it:**

```bash
kubectl uncordon netlab-worker
kubectl delete namespace team-b
kubectl get nodes                                  # both Ready, neither SchedulingDisabled
docker exec $CP ls /etc/kubernetes/manifests/      # all four
```

---

## Drill 9 — "a node went NotReady and half the site went with it"

**Target: 8 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"`frontline` started returning errors about a minute ago. `kubectl get nodes` shows a
> worker `NotReady`, which we assume is the cause, but nobody has touched that machine and it is
> still up — you can `docker exec` into it and it is perfectly healthy. We are about to reboot it.
> Talk us out of it or tell us to do it."*

**Reproduce it** (run; don't read):

```bash
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: { name: frontline }
spec:
  replicas: 2
  selector: { matchLabels: { app: frontline } }
  template:
    metadata: { labels: { app: frontline } }
    spec:
      nodeSelector: { kubernetes.io/hostname: netlab-worker }
      containers: [ { name: web, image: nginx:1.27-alpine } ]
---
apiVersion: v1
kind: Service
metadata: { name: frontline }
spec:
  selector: { app: frontline }
  ports: [ { port: 80 } ]
EOF
kubectl rollout status deployment/frontline --timeout=120s
docker exec netlab-worker systemctl stop kubelet
```

**Your symptom** — and note that it takes the best part of a minute to arrive, which is itself a clue:

```bash
kubectl get nodes
kubectl get pods -l app=frontline -o wide
CIP=$(kubectl get svc frontline -o jsonpath='{.spec.clusterIP}')
docker exec netlab-control-plane \
  curl -s -o /dev/null -w 'service: HTTP %{http_code}\n' --max-time 5 "http://$CIP/"; echo "curl exit $?"
```

```
netlab-worker   NotReady   <none>   4d22h   v1.36.1
frontline-...-5qt7s   1/1   Running   0   47s   10.244.1.210   netlab-worker
frontline-...-ghs4d   1/1   Running   0   47s   10.244.1.209   netlab-worker
service: HTTP 000
curl exit 7
```

`000` is not a status code — it is `curl`'s placeholder for *there was no response to read a code
from*, and exit `7` is `CURLE_COULDNT_CONNECT`. Note which failure that is: not a timeout, a
**refusal**. Keep that; it is the difference between two very different diagnoses, and it decides this
drill.

**Two Pods, both `1/1 Running`, and the Service refuses the connection.** Do not reboot anything
yet. Find out what is actually broken, and what is not.

<details>
<summary>Reveal</summary>

**Question 1 passes and question 2 is where this lives — but read the *whole* condition block, not
the `STATUS` column:**

```bash
kubectl describe node netlab-worker | sed -n '/^Conditions:/,/^Addresses:/p'
```

```
  Type             Status    LastHeartbeatTime    LastTransitionTime   Reason              Message
  MemoryPressure   Unknown   22:33:24             22:34:45             NodeStatusUnknown   Kubelet stopped posting node status.
  DiskPressure     Unknown   22:33:24             22:34:45             NodeStatusUnknown   Kubelet stopped posting node status.
  PIDPressure      Unknown   22:33:24             22:34:45             NodeStatusUnknown   Kubelet stopped posting node status.
  Ready            Unknown   22:33:24             22:34:45             NodeStatusUnknown   Kubelet stopped posting node status.
```

**Three things in that block, and each one changes what you do next.**

**`Unknown`, not `False`.** `kubectl get nodes` printed `NotReady`, which reads like a verdict; the
condition says the cluster has no idea. Nobody assessed this node and found it wanting — nobody
assessed it at all. `False` would mean a kubelet ran a check and reported failure. `Unknown` means
the reporter is gone, and the message says so in words: *Kubelet stopped posting node status.* Which
is [drill 2](#drill-2--the-dashboard-says-everything-is-healthy-and-it-is-not) exactly, one layer
down — a `status` field is a note some component left behind, and when that component stops the note
does not become false, it becomes stale. The only reason you were not fooled for longer is that
somebody wrote code specifically to notice this staleness, which is the `NodeStatusUnknown` reason.

**Two timestamps, and the gap between them is a setting.** `LastHeartbeatTime` is when the kubelet
last spoke — that is when it died. `LastTransitionTime` is when the control plane gave up on it —
that is when *you* found out. Here that is 81 seconds, and it is `--node-monitor-grace-period` on
the controller manager plus rounding. When someone asks how long a node can be dead before Kubernetes
reacts, this is the pair of numbers to point at, and the answer is not zero.

**Now the part that decides the ticket.** Ask the runtime rather than the API server:

```bash
docker exec netlab-worker crictl ps
docker exec netlab-control-plane curl -s -o /dev/null -w '%{http_code}\n' --max-time 4 http://10.244.1.203/
kubectl get endpointslices -l kubernetes.io/service-name=frontline \
  -o jsonpath='{range .items[*]}{range .endpoints[*]}{.addresses[0]}{" ready="}{.conditions.ready}{"\n"}{end}{end}'
```

```
fb9a234d90c20   96868d9fa38f4   Running   nginx   0   frontline-...-hg6ns
a231403356483   96868d9fa38f4   Running   nginx   0   frontline-...-fb278
200
10.244.1.203 ready=false
10.244.1.204 ready=false
```

**The containers are running and the Pod IPs are serving `200`.** Nothing is wrong with the
application, the network, or the node. What broke is the *Service*, and the EndpointSlice says why:
both endpoints are `ready=false`.

And they are `ready=false` for the same reason the Node is `Unknown` — **readiness is reported by
the kubelet.** No kubelet, no readiness reports, so the control plane cannot know whether those
containers are healthy and correctly refuses to send them traffic. The endpoints leave the slice,
kube-proxy rewrites the `KUBE-SVC` chain to have no backends, and a `KUBE-SVC` chain with no backends
**rejects** — which is why the client saw `Connection refused` rather than a timeout. Trace it back
and every symptom in the ticket comes from one dead process, and none of it comes from a sick machine.

So the answer to *"should we reboot it?"* is no, and the reason is better than "it is not necessary":
a reboot would take the containers down too, and they are the only thing still working.

**One more thing, before the clock runs out on its own.** Look at what the node controller has
already done to the node:

```bash
kubectl get node netlab-worker -o jsonpath='{range .spec.taints[*]}{.key}{"="}{.effect}{"\n"}{end}'
kubectl get pod -l app=frontline \
  -o jsonpath='{range .items[0].spec.tolerations[*]}{.key}{" "}{.effect}{" for "}{.tolerationSeconds}{"s\n"}{end}'
```

```
node.kubernetes.io/unreachable=NoSchedule
node.kubernetes.io/unreachable=NoExecute
node.kubernetes.io/not-ready NoExecute for 300s
node.kubernetes.io/unreachable NoExecute for 300s
```

There is your deadline. The node now carries a `NoExecute` taint, and every Pod on it tolerates that
taint for exactly **300 seconds** — the `tolerationSeconds` nobody wrote, added automatically, which
[Act VII lesson 04](../act-7-workloads/04-scheduling.md) told you about and this is the first time it
has ever fired. Five minutes after the transition, the Pods you were told are fine get deleted and
rescheduled elsewhere. That is not a bug and it is not your five minutes to fix the node; it is the
cluster's own decision that an unreachable node's Pods should be given up on, and it means a node
outage you resolve in four minutes costs nothing and one you resolve in six costs a full
reschedule.

**Fix it:**

```bash
docker exec netlab-worker systemctl start kubelet
until [ "$(kubectl get node netlab-worker --no-headers | awk '{print $2}')" = "Ready" ]; do sleep 3; done
kubectl rollout status deployment/frontline --timeout=120s
kubectl delete deploy frontline svc frontline
```

**The reasoning worth keeping:** `NotReady` is a statement about a *reporter*, not about a machine.
Before you touch the node, ask the runtime — `crictl ps` — and curl a Pod IP. If both answer, the
node is fine and what you have is a reporting outage, which is a completely different repair with a
completely different blast radius. And check the clock: you have five minutes before the cluster
stops waiting for you.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-6 9 "the process that stopped reporting"
```

---

## Drill 10 — "same NotReady, and this time the kubelet is running"

**Target: 6 minutes** — see [the clock](#the-clock) above.

> **Ticket:** *"Another `NotReady` worker, same as this morning. We restarted the kubelet like last
> time and it came back up and the node is still `NotReady`. Existing Pods are serving. New ones sit
> in `ContainerCreating` and never move."*

**Reproduce it** (run; don't read):

```bash
docker exec netlab-worker sh -c \
  'mkdir -p /tmp/cni && mv /etc/cni/net.d/* /tmp/cni/ && systemctl restart kubelet'
sleep 45
kubectl get nodes
docker exec netlab-worker systemctl is-active kubelet
```

```
netlab-worker   NotReady   <none>   5d   v1.36.1
active
```

**A `NotReady` node whose kubelet is running.** Drill 9's answer is already ruled out. Find the
difference in one command before you look at anything else.

<details>
<summary>Reveal</summary>

**The one command is the same one as drill 9, and this time it *speaks*:**

```bash
kubectl get node netlab-worker \
  -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status} | {.reason} | {.message}{"\n"}{end}'
```

```
False | KubeletNotReady | container runtime network not ready: NetworkReady=false
  reason:NetworkPluginNotReady message:Network plugin returns error: cni plugin not initialized
```

**`False`, not `Unknown` — and that single word is the whole diagnosis.** Put the two drills side by
side, because this is the most useful distinction in node troubleshooting and it costs one field:

```
  Unknown  +  "Kubelet stopped posting node status"   nobody is reporting.  Go and find the reporter.
  False    +  a reason and a message                  somebody IS reporting, and telling you why.
```

`Unknown` is written *by the node controller* after a timeout, and it means the control plane gave up
waiting. `False` is written *by the kubelet itself*, which means the kubelet is alive, has run its
checks, and is telling you which one failed. So a `False` node never needs guessing: read the message.

Here it says the CNI is not initialised. The kubelet looks for a network configuration on disk and
refuses to admit Pods without one, because a Pod with no network is worse than no Pod:

```bash
docker exec netlab-worker ls -la /etc/cni/net.d/
```

```
total 8
drwx------ 1 root root 4096 Aug 26 11:43 .
drwxr-xr-x 1 root root 4096 Jun  2 01:29 ..
```

Empty. And the new Pods that "sit in `ContainerCreating`" say the same thing from the other side:

```bash
kubectl run cnitest --image=busybox:1.36 --restart=Never \
  --overrides='{"spec":{"nodeName":"netlab-worker","tolerations":[{"operator":"Exists"}]}}' \
  --command -- sh -c 'sleep 120'
sleep 20
kubectl describe pod cnitest | grep NetworkNotReady | tail -1
```

```
Warning  NetworkNotReady  1s (x11 over 20s)  kubelet  network is not ready: container runtime
  network not ready: NetworkReady=false reason:NetworkPluginNotReady message:cni plugin not initialized
```

Which explains why restarting the kubelet did nothing: the kubelet was never the problem, and this
file is not something the kubelet creates. In a `kind` cluster the CNI's own DaemonSet writes it, once,
at startup — so the file going missing while the DaemonSet Pod keeps running produces a node that
stays broken until somebody either restores the file or restarts the thing that writes it.

**Fix it:**

```bash
kubectl delete pod cnitest --force --grace-period=0
docker exec netlab-worker sh -c 'mv /tmp/cni/* /etc/cni/net.d/ && ls /etc/cni/net.d/'
until [ "$(kubectl get node netlab-worker --no-headers | awk '{print $2}')" = "Ready" ]; do sleep 3; done
kubectl get nodes
```

*(The other repair is `kubectl -n kube-system delete pod -l app=kindnet --field-selector
spec.nodeName=netlab-worker` — let the DaemonSet write the file again. Worth knowing which of the two
you would reach for on a cluster where you cannot see the file.)*

**The reasoning worth keeping:** on a `NotReady` node, read `.status.conditions[Ready].status` before
anything else and branch on the word. `Unknown` sends you looking for a dead reporter. `False` hands
you a message that names the failing subsystem, and the only mistake left is not reading it.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-6 10 "what was missing from the node"
```

---

## Drill 11 — "the node says the runtime is down and the containers are still up"

**Target: 6 minutes** — see [the clock](#the-clock) above.

> **Ticket:** *"Third one this week. `NotReady`, kubelet running, and this time even `kubectl logs`
> and `kubectl exec` fail against Pods on that node — but the service those Pods back is still
> answering requests. We do not understand how both of those can be true."*

**Reproduce it** (run; don't read):

```bash
docker exec netlab-worker systemctl stop containerd
sleep 45
kubectl get nodes
docker exec netlab-worker systemctl is-active kubelet
```

**Your symptom:** identical to drill 10 from the outside. One command tells them apart.

<details>
<summary>Reveal</summary>

**Read the condition first, as drill 10 taught — it is `False` again, so the kubelet will tell you:**

```bash
kubectl get node netlab-worker \
  -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status} | {.reason} | {.message}{"\n"}{end}'
```

```
False | KubeletNotReady | container runtime is down
```

Four words, and they are the whole answer. The command that separates this from drill 10 is the one
[drill 4](#drill-4--same-symptom-and-this-time-crictl-shows-nothing) already made you reach for:

```bash
docker exec netlab-worker crictl ps
```

```
level=fatal msg="validate service connection: validate CRI v1 runtime API for endpoint
  \"unix:///run/containerd/containerd.sock\": ... dial unix /run/containerd/containerd.sock:
  connect: no such file or directory"
```

**The socket is gone.** In drill 10 `crictl ps` answered perfectly — the runtime was healthy and only
the network configuration was missing. Here `crictl` cannot connect at all, which is the same fact the
kubelet is reporting: it talks to containerd over that socket and there is nothing on the other end.

```bash
docker exec netlab-worker systemctl is-active containerd
```

```
inactive
```

**Now the part in the ticket that sounds impossible.** The service is still answering, and here is why:

```bash
docker exec netlab-worker sh -c 'ls /run/containerd/io.containerd.runtime.v2.task/k8s.io/ | head -4'
docker exec netlab-worker sh -c 'pgrep -c containerd-shim'
```

```
35ecb2d375449d8f149c1981fd297cb09dfc85d567c7421c9745548a13e0e2fe
89d4dd0d13199e9b4a432beb1648176063fe02b726db74c9a4a14f5b43e8554c
2
```

**Containerd is a manager, not a parent.** Each container's real parent is a `containerd-shim`
process, deliberately, so that containerd can be restarted or upgraded without taking every workload
on the machine down with it. So the containers keep running, keep serving, keep their network
namespaces and their `iptables` rules — and *nobody can ask them anything*, because every question
goes through the socket that is gone. `kubectl logs`, `kubectl exec`, `crictl`, liveness probes:
all of them are queries, and all of them are dead. The dataplane is not.

That is the shape worth carrying: this failure removes **observation and control**, not execution. It
is the most misleading node failure there is, because everything that reports is broken and everything
that serves is fine, and if you reboot the node to "fix" it you convert a control-plane outage into a
real one.

**Fix it:**

```bash
docker exec netlab-worker systemctl start containerd
until [ "$(kubectl get node netlab-worker --no-headers | awk '{print $2}')" = "Ready" ]; do sleep 3; done
kubectl get nodes
docker exec netlab-worker crictl ps -q | wc -l        # the same containers, re-adopted
```

The shims are still there, so containerd comes back and **re-adopts** the containers it left running.
Nothing restarted. That is what the shim design bought.

**The reasoning worth keeping:** three drills, one symptom, and the branch is two fields and one
command. `Ready=Unknown` → the kubelet is gone (drill 9). `Ready=False` → read the message, and if it
names the network, look on disk (drill 10); if it names the runtime, `crictl ps` and then
`systemctl is-active containerd` (this one). And in the last case, before you touch the node, work out
what is still *serving* — because it is probably everything.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-6 11 "the daemon that stopped"
```

---

## Drill 12 — "we capped the kubelet's memory and the cap is not there"

> **Ticket:** *"The kubelet on `netlab-worker` grew to eat most of the node last month, so we added a
> memory cap to its service. Change reviewed, file written, service restarted, no errors, service came
> back healthy. And `systemctl show` still says the limit is infinity. Did the change not apply, or is
> `show` lying to us?"*

**Reproduce it** (run; don't read):

```bash
docker exec netlab-worker sh -c 'printf "[Service]\nMemoryMax=512M\n" > /etc/systemd/system/kubelet.service.d/20-memcap.conf'
docker exec netlab-worker systemctl restart kubelet
sleep 3
```

**Confirm the symptom:**

```bash
docker exec netlab-worker sh -c 'systemctl is-active kubelet; systemctl show kubelet -p MemoryMax'
docker exec netlab-worker cat /sys/fs/cgroup/kubelet.slice/kubelet.service/memory.max
docker exec netlab-worker cat /etc/systemd/system/kubelet.service.d/20-memcap.conf
```

```
active
MemoryMax=infinity
max
[Service]
MemoryMax=512M
```

The file says `512M`. The service is healthy. Both the service manager and the kernel say there is no
limit. Nothing failed anywhere.

**Your move.** Do not edit the file — it is correct. Find out what systemd currently believes the
definition of this unit *is*, and where it got that from.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
docker exec netlab-worker systemctl show kubelet -p DropInPaths
```

```
DropInPaths=/etc/systemd/system/kubelet.service.d/10-kubeadm.conf /etc/systemd/system/kubelet.service.d/11-kind.conf
```

**Your file is not in the list.** Two drop-ins, and `20-memcap.conf` is not one of them — so systemd is
running a definition that does not contain your change, and `MemoryMax=infinity` is a truthful answer
about that definition.

Unit files are parsed from disk and then **cached in memory**. A `restart` restarts the process from the
cached definition; it does not re-read anything. And the restart reported success, because from
systemd's point of view it did exactly what it was asked ([lesson 02b](02b-what-starts-the-kubelet.md)).

The one signal you were given, and it is easy to lose in a CI log, was on stderr:

```
Warning: The unit file, source configuration file or drop-ins of kubelet.service changed on disk.
Run 'systemctl daemon-reload' to reload units.
```

Exit code 0, service `active`, one warning on the stream nobody reads.

**Root cause:** the drop-in was written but never loaded — no `systemctl daemon-reload`, so systemd
restarted the cached definition.
**Fix:**

```bash
docker exec netlab-worker systemctl daemon-reload
docker exec netlab-worker systemctl restart kubelet
sleep 3
docker exec netlab-worker sh -c 'systemctl show kubelet -p MemoryMax; cat /sys/fs/cgroup/kubelet.slice/kubelet.service/memory.max'
```

```
MemoryMax=536870912
536870912
```

Two tools, one number. `536870912` is 512 MiB, and it is now in `memory.max` — the same file
[Act IV's cgroups lesson](../act-4-one-pretends-many/01b-cgroups.md) had you read by hand. That is the
confirmation worth taking: a unit setting is not honoured until it is a byte in a cgroup file, and you
can go and look.

**Cleanup** — leave the kubelet uncapped, because 512 MiB is not a limit you want on a lab node:

```bash
docker exec netlab-worker sh -c 'rm -f /etc/systemd/system/kubelet.service.d/20-memcap.conf; systemctl daemon-reload; systemctl restart kubelet'
```

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-6 12 "no daemon-reload"
```

---

## Drill 13 — "the kubelet will not start and there is nothing in the log"

> **Ticket:** *"`netlab-worker` went `NotReady` after a maintenance window. We got as far as the kubelet
> being down, so we started it. `systemctl start` returned no error and the kubelet is still down.
> `journalctl -u kubelet` shows a clean shutdown and then nothing — no crash, no stack trace, no
> repeated attempts. Is systemd broken?"*

**Reproduce it** (run; don't read):

```bash
docker exec netlab-worker sh -c 'mv /var/lib/kubelet/config.yaml /root/held.yaml'
docker exec netlab-worker systemctl restart kubelet
sleep 45
```

**Confirm the symptom:**

```bash
kubectl get node netlab-worker
docker exec netlab-worker sh -c 'systemctl start kubelet; echo "start exit=$?"'
docker exec netlab-worker sh -c 'systemctl is-active kubelet; echo "is-active exit=$?"'
docker exec netlab-worker journalctl -u kubelet -n 3 --no-pager
```

```
netlab-worker   NotReady   <none>   12m   v1.37.0
start exit=0
inactive
is-active exit=3
kubelet.service: Deactivated successfully.
Stopped kubelet.service - kubelet: The Kubernetes Node Agent.
kubelet.service: Consumed 1.213s CPU time, 36M memory peak.
```

Read the first two lines together, because they are the drill: **`systemctl start` exited 0 and the unit
is `inactive`.** No error was reported and nothing started. And `Restart=always` is in that unit's file,
so a crash would be retrying once a second — it is not retrying.

**Your move.** You have two facts that do not fit a crash: an exit code of 0 from `start`, and a journal
with no failure in it. Stop looking for the crash. Ask systemd why it is not running instead.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
docker exec netlab-worker systemctl show kubelet -p ActiveState -p Result -p NRestarts -p ConditionResult
```

```
Result=success
NRestarts=0
ActiveState=inactive
ConditionResult=no
```

`Result=success` on a unit that is not running, `NRestarts=0`, and **`ConditionResult=no`**. Systemd did
not try and fail. It evaluated a condition, the condition was false, and it **declined to start** — which
it counts as a success, because declining is what it was asked to do.

Which condition, and what it wants, is in the unit:

```bash
docker exec netlab-worker systemctl cat kubelet | grep Condition
docker exec netlab-worker journalctl -u kubelet --since '-2min' --no-pager | grep -i condition
```

```
ConditionPathExists=/var/lib/kubelet/config.yaml
kubelet.service - kubelet: The Kubernetes Node Agent skipped, unmet condition check ConditionPathExists=/var/lib/kubelet/config.yaml
```

**"Skipped, unmet condition check"** — and note where that line is: in the journal, in the window you
already looked at, just not among the last three records and not containing the word "error." A condition
is checked *before* the process starts, so `Restart=` never came into it: a restart policy governs a
process that ran and exited, and here nothing ran ([lesson 02b](02b-what-starts-the-kubelet.md)).

This is deliberate on kind's part, and the file says so — `# NOTE: kind deviates from upstream here to
avoid crashlooping`. Without the condition you would get a kubelet failing to parse a missing file once a
second forever, which fills the journal and tells you nothing this one line does not.

**Root cause:** `/var/lib/kubelet/config.yaml` is missing, so `ConditionPathExists` is unmet and the unit
refuses to run rather than failing.
**Fix** — restore the path the condition names, then a plain `start`:

```bash
docker exec netlab-worker sh -c 'mv /root/held.yaml /var/lib/kubelet/config.yaml'
docker exec netlab-worker systemctl start kubelet
sleep 5
docker exec netlab-worker sh -c 'systemctl is-active kubelet; systemctl show kubelet -p ConditionResult'
until [ "$(kubectl get node netlab-worker --no-headers | awk '{print $2}')" = "Ready" ]; do sleep 3; done
kubectl get nodes
```

```
active
ConditionResult=yes
```

Notice that a `start` was enough, and that nothing had been retrying in the background waiting for the
file. A condition is evaluated when the unit is asked to start, and only then — which is why the fix has
two steps and why doing them in the wrong order looks like the fix not working.

**The reasoning worth keeping:** four drills now end at a `NotReady` node, and this is the one where the
node is not broken and the kubelet is not crashing. `Ready=Unknown` sent you to the kubelet, as in
drill 9 — and then the branch is `systemctl show`: `ActiveState=failed` means it ran and died and the
journal has the reason; **`inactive` with `ConditionResult=no` means it never ran and the journal has
nothing to give you.** Going looking for a crash in the second case is how this one eats an hour.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-6 13 "an unmet ConditionPathExists"
```

---

## When you can do these without the reveals

You can operate a cluster below `kubectl` — which is the thing this act existed to give you, and the thing that separates knowing Kubernetes from being able to fix it. Notice what every drill had in common: **the fix was never in the manifest the ticket was about.** Almost all of them were solved by asking *which process should have done this, and did it* — one by asking *which of authentication and authorisation actually failed*, and the last three by asking *is this node broken, or has it merely stopped talking about itself*. Those three are worth learning as a set, because they arrive as one symptom and separate on two fields and one command: `Ready=Unknown` means nobody is reporting and the reporter is what you go and find; `Ready=False` means the kubelet is alive and naming its own failing subsystem, and `crictl ps` then tells you whether the runtime is answering. Drill 11 is the one to remember on a bad night — it removes observation and control while leaving execution untouched, so everything that reports is broken and everything that serves is fine.

The two questions to carry:

- *What is the file here, who reads it, who writes it?*
- *Which loop should have acted on this, and is it running?*

---

← **[Test yourself](test-yourself.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Act VI in the wild](in-the-wild.md)** →
