# The reconciliation loop — and what stops when a watcher stops

You have now met three watchers without ever being told they were a category. kube-proxy watches Services and rewrites iptables chains. A Gateway controller watched a Gateway and provisioned an NGINX. The kubelet watches a directory and starts containers. And in the first lesson of this act, `etcdctl watch` printed writes to a Pod that you did not perform.

So here is the question this lesson exists to answer: are those four mechanisms, or one? And if one, what happens to a cluster when a single instance of it stops running?

### What does a controller actually do?

Take the simplest possible statement of intent and watch it defended.

```bash
kubectl create deployment web --image=hashicorp/http-echo --replicas=3 -- /http-echo -text=web -listen=:5678
kubectl wait --for=condition=Available deployment/web --timeout=90s
kubectl get pods -l app=web
```

Three Pods. Now break it, and time the repair.

> **Predict first —** you delete one of the three Pods. Does a *new* Pod appear, or does the deleted one restart? What will its name be, and roughly how long will it take?

```bash
POD=$(kubectl get pod -l app=web -o jsonpath='{.items[0].metadata.name}')
echo "deleting $POD"
kubectl delete pod $POD --wait=false
kubectl get pods -l app=web -w        # Ctrl-C when you have seen enough
```

A **new** Pod, with a new random suffix, within a second or two. Nothing restarted the old one — it is gone. Something noticed that the number of Pods matching a selector had fallen to two, compared it against a number stored in an object, and created one.

That comparison is the whole of it, and it has a name you already used in [the Gateway API lesson](../act-5-kubernetes/06b-gateway-api.md): **reconciliation**. Watch the object. Compare desired against actual. Act on the difference. Repeat forever.

And as in that lesson, an object you did not create is sitting there doing the work:

```bash
kubectl get replicaset -l app=web
```

Your Deployment made a **ReplicaSet**, and the ReplicaSet is what actually holds the number `3` and counts Pods against it. The split matters later — a Deployment's job is to manage *successive* ReplicaSets, which is how a rolling update works — but for now the point is only that the chain is Deployment → ReplicaSet → Pod, and each link is one loop watching the link above.

What makes it worth a lesson rather than a definition is that it is *not* a request-response system. You did not tell anything to create a Pod. You changed the world, and a loop that was already running noticed. Nobody was called.

### Which loop, though?

"Something noticed" is not good enough for this course. Find out which process it was — by stopping it.

You can do that now, because the last lesson showed you where the control plane lives. The Deployment→ReplicaSet→Pod loops all run inside one binary:

```bash
docker exec netlab-control-plane sh -c 'mv /etc/kubernetes/manifests/kube-controller-manager.yaml /tmp/'
sleep 10
kubectl -n kube-system get pods -l component=kube-controller-manager    # gone
```

> **Predict first —** with the controller manager stopped, you delete a Pod from the three-replica Deployment. What does `kubectl get pods` show after twenty seconds? And what does `kubectl get deployment web` claim in its READY column?

```bash
POD=$(kubectl get pod -l app=web -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $POD --wait=false
sleep 20
kubectl get pods -l app=web            # two Pods. no replacement is coming.
kubectl get deployment web             # READY 3/3 -- which is now a LIE
```

**Two Pods, indefinitely** — and a Deployment that cheerfully reports `READY 3/3` about them. Count the rows above it if you doubt it, or ask the object directly:

```bash
kubectl get deployment web -o jsonpath='{.status.readyReplicas}{"\n"}'    # 3
kubectl get pods -l app=web --no-headers | grep -c .                      # 2
```

If you predicted `2/3` you predicted something reasonable and wrong, and the gap between them is the best thing in this lesson. `READY` does not *count* anything when you ask for it. It is a field, `status.readyReplicas`, sitting in the store — and the thing that writes that field is the controller manager. You stopped the process whose job was to notice, so what you are reading is the last thing it noticed before it died.

That is the lesson's own point pushed one step further than is comfortable. It is not only that Kubernetes stops *acting* when a controller stops. **It stops knowing** — and it does not say so. `status` is not an observation the API server makes on your behalf; it is a note some controller left behind, as much a stored document as `spec` is, and just as capable of being stale.

So the Deployment still says it wants three, the API server still holds both records faithfully, and nothing is wrong with the *desired state*. What is missing is the thing that reads it — and the thing that reports on it, which turns out to be the same thing.

This reframes what you have been looking at all act. The API server did not "fail to create a Pod" — creating Pods was never its job. It stores documents and serves them. Every behaviour you think of as *Kubernetes doing something* is a controller, **including telling you what is going on**, and if that controller is not running, the object is exactly as inert as the unreconciled Gateway from Act V. Same shape, one layer down.

Now restore it and watch the loop catch up:

```bash
docker exec netlab-control-plane sh -c 'mv /tmp/kube-controller-manager.yaml /etc/kubernetes/manifests/'
kubectl get pods -l app=web -w         # Ctrl-C once a third Pod appears
```

Time that, because it is slower than you expect: the container is running within a couple of seconds, and the third Pod does not appear for **about twenty**. A control-plane component that has just started does not begin work immediately — it must first win a **leader election**, a lock stored in the API server which the dead instance still holds until its claim times out. That is deliberate. Two controller managers reconciling the same Deployment would race each other, so the design prefers a gap of inaction to a moment of duplication.

Note also what you could *not* have used to wait for this. `kubectl wait --for=condition=Available deployment/web` would have returned instantly and told you everything was fine — because the condition it reads is part of the same stale status you just caught lying. A tool that waits on a field cannot outrun the controller that writes the field.

It did not need to be told what it missed. It observed a gap and closed it — which is why a controller can crash, be restarted, or be down for an hour, and still converge. It holds no queue of pending work. **The current state of the store is the entire input.** That is why this design survives its own components dying, and it is the reason "just restart it" is so often the correct operational instinct here.

### What does the scheduler do that this doesn't?

There is one gap the controller manager cannot close, and you can prove it is a separate job with the same technique.

```bash
docker exec netlab-control-plane sh -c 'mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/'
sleep 10
kubectl create deployment lonely --image=hashicorp/http-echo -- /http-echo -text=x -listen=:5678
sleep 10
kubectl get pods -l app=lonely -o wide
```

The Pod exists. It is `Pending`, and the `NODE` column reads `<none>`. The controller manager did its job perfectly — a Deployment wanted a Pod, so a Pod object exists — and then stopped, because *placing* it is somebody else's loop.

```bash
kubectl get pod -l app=lonely -o jsonpath='{.items[0].spec.nodeName}'; echo   # empty
kubectl describe pod -l app=lonely | tail -5
```

`spec.nodeName` is empty, and that single empty field is the entire handoff. The scheduler watches for Pods with no `nodeName`, evaluates the nodes, and writes one value. The kubelet on each node watches for Pods whose `nodeName` matches itself. Neither ever speaks to the other.

Look at the last line of that `describe` output, though, because it is the sharper evidence: **`Events: <none>`**. Not "no suitable node" — *nothing at all*. Nobody looked. A scheduler that was running and could not place this Pod would have said so here, and the difference between "an empty events list" and "an events list containing a complaint" is the difference between a missing component and a real scheduling problem.

```bash
docker exec netlab-control-plane sh -c 'mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/'
sleep 20
kubectl get pods -l app=lonely -o wide    # scheduled and running
```

So the pipeline that turns your `kubectl create deployment` into a running container is three independent loops that never call each other, coordinating entirely through fields on one object:

```
you            -> Deployment                          (kubectl writes)
controller mgr -> ReplicaSet -> Pod, nodeName empty    (watches Deployments)
scheduler      -> sets spec.nodeName                   (watches unassigned Pods)
kubelet        -> starts containers                    (watches Pods for its node)
```

Every arrow is a watch on the store, not a call. Cut any one and the pipeline stalls at exactly that point, leaving an object in a diagnosable half-state — which is why "`Pending` with no node" and "a `READY` count that no longer matches `kubectl get pods`" are not vague symptoms. Each one names the loop that is missing.

<!-- figure -->

```
   NOT THIS                          THIS

   kubectl                           kubectl --> [ API server / etcd ]
     | call                                            ^   ^   ^
     v                                          watch  |   |   |  write
   scheduler                                           |   |   |
     | call                              +-------------+   |   +-------------+
     v                                   |                 |                 |
   kubelet                          controller mgr      scheduler         kubelet
                                    replicas != 3?     nodeName == ""?   nodeName == me?
   a request pipeline;              create a Pod       pick a node       start containers
   any break loses the request
                                    no component calls another.
                                    stop one: the object stalls where it stalled,
                                    and the stall names the loop.

                                    it also stops WRITING STATUS.
                                    a stopped controller leaves its last
                                    report standing: READY 3/3 over 2 Pods.
                                    status is a stored note, not a live count.
```

> **Check yourself —** A Pod has been `Pending` for ten minutes. Before looking at anything else, which two questions separate "no loop is placing it" from "a loop tried and could not"?

<details>
<summary>Answer</summary>

Ask whether `spec.nodeName` is empty, and whether the scheduler is running.

If `nodeName` is empty **and** the scheduler is down, nothing has evaluated the Pod at all — the symptom is a missing loop, and the fix is on the control plane rather than in your manifest.

If `nodeName` is empty and the scheduler **is** running, then it has looked and refused, which is a completely different problem: it will say so in the Pod's events, naming what it could not satisfy — most often not enough CPU or memory anywhere, or a node it is not permitted to use (you met one such restriction as the control plane's `NoSchedule` taint). That is a conversation with the scheduler about your requirements, not a missing process.

And if `nodeName` is set while the Pod is still `Pending`, the scheduling question is already answered and you are asking the wrong component: placement succeeded, so the problem is downstream in the kubelet on that node.

</details>

**Cleanup:**

```bash
kubectl delete deployment web lonely
docker exec netlab-control-plane ls /etc/kubernetes/manifests/    # confirm all four are back
```

That last check matters. If you interrupted this lesson partway through, a manifest may still be sitting in `/tmp` — and a control plane missing its scheduler is a cluster that looks healthy right up to the moment something needs placing.

> **You understand this when you can** explain why a controller needs no queue of pending work and
> can be restarted freely; say what a `READY` count that never changes *and no longer agrees with*
> `kubectl get pods` tells you about which process is absent; and describe the three-loop handoff
> from `kubectl create deployment` to a running container in terms of the one field each loop
> reads or writes.

**Which raises:** you have been running `etcdctl` and reading `/etc/kubernetes/manifests` with nothing more than a shell on a node. Every one of those commands needed certificates, and you supplied them from a directory sitting on that same disk. Who issued them, what happens when they expire, and what exactly does holding them let someone do?

---

← Prev: **[Static pods — where the control plane lives](02-static-pods.md)** · ↑ **[Act VI overview](README.md)** · Next: **[The cluster's own PKI](04-the-clusters-own-pki.md)** →
