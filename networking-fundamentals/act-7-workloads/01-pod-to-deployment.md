# From a Pod to a Deployment

You have created Pods three ways now without being asked to notice the difference. `kubectl run db-0` made a bare Pod. `kubectl create deployment web --replicas=3` made a Deployment, and in Act VI you ran one command against the result and found an object you had not written:

```
NAME             DESIRED   CURRENT   READY   AGE
web-5cb9f99b96   3         3         3       47s
```

A **ReplicaSet**, holding the number `3`. That lesson said the split between it and the Deployment "matters later" and moved on. This is later.

So: **three objects to run one program. Why three, and what would break if there were two?**

### What does a bare Pod actually promise?

Start at the bottom, with the thing you have used least. Make a Pod with nothing wrapped around it:

```bash
kubectl run solo --image=hashicorp/http-echo --command -- /http-echo -text=solo -listen=:5678
kubectl wait --for=condition=Ready pod/solo --timeout=90s
kubectl get pod solo -o wide
```

Running, on a node, with an IP. Now kill the container underneath it — not the Pod, the container. Act VI used `crictl` to *look* at containers one layer below `kubectl`; the same tool can also stop one, which is the first time in this course you reach past the API server to change something:

```bash
CID=$(docker exec netlab-worker sh -c "crictl ps --name solo -q | head -1")
docker exec netlab-worker crictl stop $CID
sleep 10
kubectl get pod solo
```

(Two inconsistencies between `kubectl run` and `kubectl create deployment` are worth banking now, because both cost people marks. The **container name**: `run` names it after the *Pod*, `create deployment` names it after the *image* — which is why the container above is `solo` and why the `kubectl set image` command further down addresses `http-echo=`. And **what `--` means**: for `create deployment` it sets `command`, but for `run` it sets `args`, which are *appended to the image's existing entrypoint*. Leave off `--command` above and the container execs `/http-echo /http-echo -text=solo …`, prints `Too many arguments!`, and exits 127 — after `kubectl wait` has already reported success, because the Pod was briefly Ready before the first exit.)

**`RESTARTS` is `1`, and the Pod is `Running` again.** Something restarted it, and it is worth naming who: the kubelet on that node, which Act VI established watches Pods assigned to it. A container that exits gets started again — in the same Pod, on the same node, with the same IP. That is the default `restartPolicy: Always`, and it is a promise made entirely locally.

> **Predict first —** so a bare Pod survives a crashed container. Does it survive losing its *node*? Say what you think happens to `solo` when that node is emptied — and, separately, predict what `kubectl drain` will do when it reaches this Pod, given what Act VI showed you about what drain refuses to touch.

```bash
kubectl get pod solo -o wide                       # note the node
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data
```

**Drain refuses, and it refuses over `solo` specifically:**

```
node/netlab-worker cordoned
error: unable to drain node "netlab-worker" due to error: cannot delete Pods that
declare no controller (use --force to override): default/solo, continuing command...
There are pending nodes to be drained:
 netlab-worker
cannot delete Pods that declare no controller (use --force to override): default/solo
```

Read the first line before the error, because it is the trap Act VI warned about in a different form: **it cordoned the node anyway.** The refusal came second. Anyone who runs a bare `drain` "just to see what it says" has quietly disabled scheduling on that node, and the error does not mention it again.

The refusal itself *is* the answer to the first half of the prediction, handed to you by a tool that already knows. Drain is willing to delete a Pod it can see something will replace. It will not quietly delete one that nothing owns, because it has no reason to believe that Pod will ever come back — and it makes you say `--force` to accept that.

So say it, and watch:

```bash
kubectl drain netlab-worker --ignore-daemonsets --delete-emptydir-data --force
kubectl get pods
```

**`solo` is gone.** Not pending, not restarting — gone, permanently, with nothing anywhere trying to fix it.

Look at what you actually created. A Pod object names a node in `spec.nodeName`, and Act VI showed you that field is written once and then read by one kubelet. No loop anywhere is watching to see whether a Pod named `solo` exists. The kubelet restarted the *container* because the Pod record told it to; when the record went, so did the last trace of your intent.

**A bare Pod is one machine's promise.** It survives a crash and nothing else.

```bash
kubectl uncordon netlab-worker
```

### So what holds the intent?

You want to say "there should be one of these, somewhere," and a Pod cannot express that, because a Pod *is* the one — it is the thing being counted, not the count.

So the count goes in a different object:

```bash
kubectl create deployment web --image=hashicorp/http-echo --replicas=2 -- /http-echo -text=web -listen=:5678
kubectl wait --for=condition=Available deployment/web --timeout=90s
kubectl get deployment,replicaset,pod -l app=web
```

Three rows of three kinds, and now read them as a chain rather than a list:

```bash
kubectl get pod -l app=web -o jsonpath='{range .items[*]}{.metadata.name}{"  owner="}{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}{end}'
kubectl get rs -l app=web -o jsonpath='{range .items[*]}{.metadata.name}{"  owner="}{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}{end}'
```

Each Pod carries an **`ownerReference`** to a ReplicaSet; the ReplicaSet carries one to the Deployment. That is not decoration — it is a field, in the store, that a controller reads. This is how a loop knows which Pods are *its* Pods, and you have already relied on the other thing it does: Act V's Gateway lesson pointed out that deleting the Gateway you wrote garbage-collects the Deployment and Service a controller wrote for it, because those carry an owner reference back to it. Same field, same collector.

Now prove the count lives where you think it does:

```bash
RS=$(kubectl get rs -l app=web -o jsonpath='{.items[0].metadata.name}')
kubectl get rs $RS -o jsonpath='{.spec.replicas}{"\n"}'
kubectl get deployment web -o jsonpath='{.spec.replicas}{"\n"}'
```

**Both say `2`.** Which is the first genuinely odd thing in this lesson, and the clue to why there are three objects rather than two.

### Why not two?

> **Predict first —** the Deployment says `2` and the ReplicaSet says `2`. If a ReplicaSet can hold a count and create Pods to match, the Deployment is doing nothing you can see. So what is it *for*? Before reading on, try this: what would you have to do, by hand, to move two replicas from one image to another without dropping traffic — using only ReplicaSets?

Work it through, because the answer is the design.

You have a ReplicaSet running two Pods of `v1`. You want two Pods of `v2`. A ReplicaSet's job is to make the world match *its* Pod template, so you cannot ask one ReplicaSet to hold both versions — the moment you change its template it wants everything replaced, and it has no notion of doing that gradually.

So you need **two** ReplicaSets, briefly: one draining down from 2 to 0, one filling up from 0 to 2, in steps small enough that enough Pods are serving throughout. Something has to own that dance — to decide the order, to wait for each new Pod to become ready before removing an old one, and to know how to stop halfway if the new version is broken.

That something is the Deployment. **A ReplicaSet keeps a number of identical Pods alive. A Deployment manages successive ReplicaSets.** The count appears in both because the Deployment's way of controlling the dance is precisely to *write counts into ReplicaSets* — that is its whole vocabulary.

You can see the seam by hand. Ask the Deployment for a change, and watch how many ReplicaSets exist:

```bash
kubectl set image deployment/web http-echo=hashicorp/http-echo:1.0
kubectl rollout status deployment/web --timeout=60s
kubectl get rs -l app=web
```

(The `rollout status` line is not decoration. Run the two `kubectl` commands back to back and you catch the rollout in flight — the new ReplicaSet at `1`, the old one still at `2` — which is a true picture of a moment you are not trying to look at yet.)

**Two ReplicaSets now** — the original at `DESIRED 0`, and a new one at `DESIRED 2`. The old one was not deleted. It was scaled to zero and left there, with its template intact, which is a fact with a use you will meet in the next lesson.

And the label on those Pods explains how two ReplicaSets can coexist without fighting over the same ones:

```bash
kubectl get pods -l app=web --show-labels
```

Every Pod carries a `pod-template-hash` alongside `app=web`, and each ReplicaSet selects on *its own* hash. Two loops, two disjoint sets of Pods, one shared label for you to query by. Without that hash the two ReplicaSets would both believe they owned all four Pods, and would spend the rollout deleting each other's work.

### The layer that is not there

Notice what no object in this chain does: **choose a node.** The Deployment does not, the ReplicaSet does not, and the Pod template does not name one. The ReplicaSet creates Pods with `spec.nodeName` empty and stops, exactly as Act VI showed you when you stopped the scheduler and got a `Pending` Pod that nothing had looked at.

That is the division of labour worth carrying out of this lesson. **Counting is one loop's job and placing is another's, and they only ever meet through one empty field on one object.** Which is why "I have two replicas and both are on the same node" is not a Deployment problem, and no amount of editing a Deployment will fix it.

> **Check yourself —** You scale a Deployment from 3 to 5 and two Pods stay `Pending` forever. Which of the three objects is misbehaving, and where do you look?

<details>
<summary>Answer</summary>

None of them. All three are working perfectly, and that is the point.

The Deployment wrote `5` into its ReplicaSet. The ReplicaSet counted three Pods, wanted five, and created two more — its job is done the moment the Pod objects exist. Both new Pods have an empty `spec.nodeName`, because assigning one was never any of these three objects' work.

So the object to look at is a **Pod**, and the question is Act VI's: is `spec.nodeName` empty, and does the Pod have events? Events naming insufficient CPU or memory mean the scheduler looked and refused, and the fix is in `resources.requests` or in the size of your cluster — not in the Deployment. `Events: <none>` would mean nothing looked at all, and you would be chasing the scheduler itself.

The general habit: `kubectl describe deployment` will not diagnose a scheduling problem, however natural it feels to start there. The Deployment's `status` will cheerfully tell you it wants five and has three, which you already knew.

</details>

<!-- figure -->

```
   THREE OBJECTS, THREE PROMISES

   Pod            "this container runs, here, and restarts if it exits"
                     spec.nodeName is SET -> one kubelet owns it
                     lose the node, lose the Pod. nothing is watching.

   ReplicaSet     "there are always N Pods matching this template"
                     holds spec.replicas. creates Pods with nodeName EMPTY.
                     selects on app=... PLUS its own pod-template-hash

   Deployment     "get from the old template to the new one without an outage"
                     owns SUCCESSIVE ReplicaSets. its only verb is
                     writing counts into them: old 2->0 while new 0->2.
                     the old RS is kept at 0, template intact.

   ownerReference: Pod -> ReplicaSet -> Deployment
     the field a controller reads to know which Pods are ITS Pods
     (and the reason deleting an owner collects its dependents)

   WHAT NONE OF THEM DO: pick a node.
     they hand over through ONE empty field, spec.nodeName,
     and the scheduler is a separate loop entirely (Act VI).
     so "both replicas landed on one node" is not a Deployment problem.
```

**Cleanup:**

```bash
kubectl delete deployment web
kubectl delete pod solo --ignore-not-found
kubectl get nodes                       # both Ready, neither SchedulingDisabled
```

> **You understand this when you can** say what a bare Pod does and does not survive, and why the
> kubelet restarting a container is a different guarantee from anything replacing a Pod; explain
> why a rolling update needs *two* ReplicaSets and therefore a third object to conduct them, and
> what `pod-template-hash` prevents; and say which of the three objects chooses a node, and what
> that means for where you look when a replica will not schedule.

**Which raises:** you have just seen two ReplicaSets exist at once, one of them scaled to zero with its template still intact — and the Deployment moved traffic between them without your saying how fast, how many at a time, or what "ready" even means. Those are all fields you did not write. What did it assume, and what happens when the new version is broken?

---

↑ **[Act VII overview](README.md)** · Next: **[Rolling updates, and the promise nobody wrote down](02-rolling-updates.md)** →
