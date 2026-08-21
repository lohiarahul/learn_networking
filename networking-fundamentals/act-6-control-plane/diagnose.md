# Act VI — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act VI. This checks whether you can *use* it. Real failures never arrive labelled "this is a stale status field" or "that manifest will not parse" — they arrive as a symptom, a shrug, and a ticket. Each drill below puts your cluster into a **real broken state**, hands you only the symptom, and asks you to find the cause with the act's tools.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** Reading it closely spoils the hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud what you think is wrong and which file or tool would prove it — *then* look.
3. **Open the reveal only after you've tried.**

**Where:** the same `kind` cluster as the lessons. If you do not have it, [the Act V lab lesson](../act-5-kubernetes/01-lab-with-kind.md) builds it in a minute.

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

## Drill 1 — "kubectl works, but nothing we deploy ever starts"

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

---

## Drill 2 — "the dashboard says everything is healthy and it is not"

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

---

## Drill 3 — "kubectl died after a config change and we cannot get in"

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

---

## Drill 4 — "same symptom, and this time crictl shows nothing"

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

---

## Drill 5 — "we are locked out of our own cluster and nothing is down"

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

---

## Drill 6 — "the drain has been running for half an hour"

> **Ticket:** *"Patching a node. The drain has been sitting there for thirty minutes with no output. No error. Do we Ctrl-C it? Is it nearly done? Is it stuck? We cannot tell and we have a maintenance window."*

**Reproduce it** (run; don't read):

```bash
kubectl create deployment checkout --image=hashicorp/http-echo --replicas=2 -- /http-echo -text=c -listen=:5678
kubectl wait --for=condition=Available deployment/checkout --timeout=90s
kubectl create poddisruptionbudget checkout-pdb --selector=app=checkout --min-available=2
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=45s
```

**Your symptom:** a drain that waits, then times out, having achieved nothing obvious.

<details>
<summary>Reveal</summary>

Start from the right place: **the drain is a loop in your terminal, not in the cluster.** There is no drain object, no controller and no status field, so there is nothing to inspect *about the drain*. The evidence is about the node.

```bash
kubectl get pods -A -o wide --field-selector spec.nodeName=netlab-worker
```

Whatever is still listed, minus the DaemonSet Pods, is what your drain is waiting on — usually exactly one thing. That name is the whole investigation.

Now the one question that matters: **blocked, or slow?** Ask for the eviction yourself and read the refusal:

```bash
kubectl get pdb
kubectl describe pdb checkout-pdb | tail -8
```

`ALLOWED DISRUPTIONS: 0`. A budget insisting both replicas stay available, so no eviction can ever be permitted. The rejection text is explicit — `Cannot evict pod as it would violate the pod's disruption budget` — and `kubectl` treats that as *not yet* rather than *no*, retrying until your timeout. Which is correct in the normal case, where a rolling update clears in seconds, and useless here.

If nothing had been refusing, this would be a completely different problem: the Pod is terminating and taking its time — a long `terminationGracePeriod`, or a container ignoring the signal to stop.

The fix is a conversation, not a command. Either the application genuinely cannot lose a replica right now — in which case scale it up first and the budget satisfies itself — or the budget is wrong:

```bash
kubectl scale deployment checkout --replicas=3
kubectl wait --for=condition=Available deployment/checkout --timeout=90s
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --timeout=60s
```

**The reasoning worth keeping:** always pass `--timeout` to an interactive drain. Without it the default is to wait indefinitely, and a drain that will never finish is visually identical to one that is nearly done. And check `ALLOWED DISRUPTIONS: 0` *before* you start a maintenance window rather than thirty minutes into it.

</details>

**Fix it:**

```bash
kubectl uncordon netlab-worker
kubectl delete deployment checkout
kubectl delete pdb checkout-pdb --ignore-not-found
kubectl get nodes                                  # both Ready, neither SchedulingDisabled
docker exec $CP ls /etc/kubernetes/manifests/      # all four
```

---

## Drill 7 — "the node is fine and the cluster says it does not exist"

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

---

## When you can do these without the reveals

You can operate a cluster below `kubectl` — which is the thing this act existed to give you, and the thing that separates knowing Kubernetes from being able to fix it. Notice what every drill had in common: **the fix was never in the manifest the ticket was about.** Six of these seven were solved by asking *which process should have done this, and did it* — and the seventh by asking *which of authentication and authorisation actually failed*.

The two questions to carry:

- *What is the file here, who reads it, who writes it?*
- *Which loop should have acted on this, and is it running?*

---

← **[Test yourself](test-yourself.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Act VI in the wild](in-the-wild.md)** →
