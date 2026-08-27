# Rolling updates, and the promise nobody wrote down

Last lesson ended with a change you made and did not specify. You typed `kubectl set image`, and something decided how many Pods to replace at once, how long to wait between them, and what "replaced" even meant — none of which you said.

It also left an artefact you should be suspicious of: an old ReplicaSet, scaled to `0`, not deleted, with its Pod template intact. Nothing needs that. Unless something does.

So: **what did the Deployment assume, and what is that dead ReplicaSet for?**

### How many Pods exist during a rollout?

Set up something to watch, with enough replicas that the arithmetic is visible:

```bash
kubectl create deployment web --image=hashicorp/http-echo:1.0 --replicas=4 \
  -- /http-echo -text=v1 -listen=:5678
kubectl rollout status deployment/web        # blocks until the Deployment says it is done
kubectl get deployment web -o jsonpath='{.spec.strategy}{"\n"}'
```

There is the answer to the first half, and you never wrote it:

```json
{"rollingUpdate":{"maxSurge":"25%","maxUnavailable":"25%"},"type":"RollingUpdate"}
```

Two percentages, defaulted for you. **`maxSurge`** is how far above your replica count the Deployment may go while replacing; **`maxUnavailable`** is how far below.

> **Predict first —** you have 4 replicas, `maxSurge: 25%`, `maxUnavailable: 25%`. Work out two numbers before you run anything: the **most** Pods that can exist at once during the rollout, and the **fewest** that can be available. Then say what those numbers become if you had asked for 3 replicas instead of 4. The rounding is not obvious and it is the whole point.

```bash
kubectl set image deployment/web http-echo=hashicorp/http-echo:1.0
kubectl get pods -l app=web -w        # Ctrl-C when it settles
```

With 4 replicas, 25% is exactly 1 either way: at most **5** Pods exist, at least **3** stay available. You will see a fifth Pod appear before a first one leaves.

Now the part that catches people. Those two percentages round in **opposite directions** — `maxSurge` rounds **up**, `maxUnavailable` rounds **down** — and each rounds in the direction that is safer. So at 3 replicas, `maxSurge` becomes `ceil(0.75) = 1` and `maxUnavailable` becomes `floor(0.75) = 0`, which means a 3-replica Deployment on defaults **never drops below full capacity at all**. It goes to 4 Pods and back down.

That is not a coincidence; it is the design choice. When the arithmetic is ambiguous, Kubernetes spends a Pod rather than availability.

### What the dead ReplicaSet is for

Look at the two ReplicaSets again, then ask the Deployment what it remembers:

```bash
kubectl get rs -l app=web
kubectl rollout history deployment/web
```

Two revisions — and a `CHANGE-CAUSE` column that says `<none>` for both, which is useless and worth understanding rather than ignoring. There used to be a `--record` flag that filled it in; it is gone. The column reads an **annotation**, and nothing writes that annotation unless you do:

```bash
kubectl annotate deployment/web kubernetes.io/change-cause="pin http-echo to 1.0" --overwrite
kubectl rollout history deployment/web
```

Now revision 2 has a reason. This matters more than it looks: `rollout history` is the only record of *why* a version changed, and by default it is empty. A rollout you cannot explain at 3am is a rollout you will be reluctant to undo.

> **Predict first —** you are about to run `kubectl rollout undo`. Predict what happens to the *number of ReplicaSets*: does a third appear, holding the old template again, or does something else happen? Lesson 01 left you a clue you may not have used.

```bash
kubectl rollout undo deployment/web
kubectl rollout status deployment/web
kubectl get rs -l app=web
```

**Still two ReplicaSets.** The old one went from `0` back up to `4`, and the new one went to `0`. Nothing was created and nothing was reconstructed from a stored diff.

Which is what that dead ReplicaSet was for, and it reframes what a rollback *is*. **There is no undo log.** A Deployment does not remember how to reverse a change; it keeps the previous ReplicaSets around, templates and all, and "rolling back" is the same operation as rolling forward — write counts into ReplicaSets — aimed at one you kept. Revision history is not a journal, it is **a shelf of objects you have not thrown away yet**.

Which means it has a size, and the size is a field:

```bash
kubectl get deployment web -o jsonpath='{.spec.revisionHistoryLimit}{"\n"}'
```

`10` by default. Roll forward eleven times and the oldest ReplicaSet is deleted — and with it, the ability to roll back that far. Set it to `0` and you can never roll back at all, which is a thing people do to tidy up `kubectl get rs` output without realising what they are spending.

### What happens when the new version is broken?

Now the case that matters operationally, and the answer is more reassuring than you might expect.

> **Predict first —** you roll out an image tag that does not exist. Think about the two percentages: how many of your 4 serving Pods will be gone by the time the rollout gives up? And does the rollout ever "give up", or does it hang forever?

```bash
kubectl set image deployment/web http-echo=hashicorp/http-echo:v9.99.99
sleep 30
kubectl get pods -l app=web
kubectl get deployment web
```

```
NAME                   READY   STATUS         RESTARTS   AGE
web-5c7f954f84-95mpc   0/1     ErrImagePull   0          30s
web-5c7f954f84-pcv27   0/1     ErrImagePull   0          31s
web-6bf8d7bb78-bc6ht   1/1     Running        0          44s
web-6bf8d7bb78-nwkrf   1/1     Running        0          45s
web-6bf8d7bb78-snd5d   1/1     Running        0          45s

NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    3/4     2            3           2m47s
```

**Three serving, two stuck**, and it stays exactly there — `ErrImagePull` becomes `ImagePullBackOff` after a minute or two and nothing else changes.

Now check those numbers against the arithmetic you did a moment ago, because they are not the numbers a careless reading predicts. Four replicas at 25% gives `maxUnavailable` **1** and `maxSurge` **2**. So the controller was entitled to retire one old Pod immediately — and it did, which is why `AVAILABLE` is `3` and not `4`. Having done that, its surge budget allowed two new ones. Three old plus two new is five, which is the cap. Then it stopped, because retiring a second old Pod would breach the promise and no new Pod is ever going to become available to buy it room.

So the guarantee is **not** "an old Pod is never removed until a new one is available" — that is the sentence people carry around, and this experiment disproves it in one line. The guarantee is that availability never drops below `replicas − maxUnavailable`. On four replicas that permits losing one, permanently, to a deploy that never succeeds.

That is still `maxUnavailable` earning its keep, and **a broken image is the safe kind of bad deploy** — you keep serving and you can take as long as you like to notice. But notice what "safe" cost you here: a quarter of your capacity, indefinitely, on a rollout that will never finish. On three replicas it would have cost nothing at all, because `maxUnavailable` rounds down to zero — which is the asymmetry from earlier in this lesson turning out to matter rather more than it looked.

It does eventually stop trying, and says so in the object rather than in the terminal:

```bash
kubectl get deployment web -o jsonpath='{.spec.progressDeadlineSeconds}{"\n"}'
kubectl get deployment web -o jsonpath='{range .status.conditions[*]}{.type}={.status}  {.reason}{"\n"}{end}'
```

Right now that prints `Progressing=True` with reason `ReplicaSetUpdated`, because `progressDeadlineSeconds` is **600** and the deadline has not passed. Which is worth sitting with rather than skipping: for a full ten minutes, a Deployment that is permanently and unrecoverably stuck reports that it is *progressing*. Come back later, or start a timer and carry on reading, and it becomes:

```
Available=True    MinimumReplicasAvailable
Progressing=False  ProgressDeadlineExceeded
```

**`Progressing=False`** with reason **`ProgressDeadlineExceeded`** — ten minutes after the `set image`, not ten minutes after you noticed. That condition is what a CI pipeline or an alert should be watching, and it is the reason `kubectl rollout status` eventually returns non-zero instead of hanging forever.

Undo it:

```bash
kubectl rollout undo deployment/web
kubectl rollout status deployment/web
kubectl get rs -l app=web         # the broken RS is kept too, at 0
```

### The bad deploy that is actually dangerous

So a broken image is safe. Sit with why, because the reason tells you what *is* unsafe.

The rollout stalled because the new Pod never became **available**, and availability is what gates every step. Which means the entire safety of a rolling update rests on one thing: **the cluster's idea of "this replica is working" being the same as yours.**

Act V taught you where that idea comes from — a Pod joins a Service's endpoints when it reports ready, and a Service sends traffic to endpoints. So if your container reports ready the instant its process starts, before it has loaded config or connected to a database, then every new Pod counts as a success, the rollout marches happily to completion, and it replaces all four of your working replicas with four that cannot serve. Nothing failed. Nothing stalled. The controller kept its promise exactly as written.

You can see the knob that would have caught it:

```bash
kubectl get deployment web -o jsonpath='{.spec.minReadySeconds}{"\n"}'   # prints an empty line
```

An **empty line** — and that is the answer, not a failed command. Unlike `revisionHistoryLimit` (`10`) and `progressDeadlineSeconds` (`600`), which the API server fills in and which therefore print, `minReadySeconds` has no server-side default at all, so the field is simply absent from the stored object. Absent means zero: a Pod counts as available the moment it is ready, with no probation.

(That distinction is worth keeping. An empty `jsonpath` result means *this field is not in the object*, which is a different statement from "its value is zero" — even when the effect is the same. It is the same reading skill Act VI needed for a Pod with no `nodeName`.) `minReadySeconds: 10` says *stay ready for ten seconds before I believe you*, which is a crude but real defence against a container that reports ready and then falls over.

**The uncomfortable summary: a rolling update is only as truthful as your readiness signal**, and you have not yet written one. What you have been relying on all lesson is a default — a container with no probe at all is considered ready as soon as it starts.

> **Check yourself —** A colleague reports that a deploy "took down the service for about a minute, then recovered on its own." The image was fine, the Pods all became `Running`, and no rollout stalled. What is your first hypothesis, and which two fields would you look at?

<details>
<summary>Answer</summary>

The Pods reported ready before they could serve, so the rollout replaced the old ones on schedule while the new ones were still warming up. It recovered on its own because they eventually finished warming up.

Nothing here is a failure of the rollout machinery — it did precisely what it was told. It was told wrong.

Two fields. **`readinessProbe`**, or its absence: with no probe, a container is ready the instant it starts, which for anything that loads state at boot is a lie. And **`minReadySeconds`**, which is `0` by default and would have made the Deployment wait before counting each new Pod as available — turning a one-minute outage into a rollout that visibly stalls instead.

The distinction worth keeping is between the two kinds of bad deploy. A **crash or a bad image** is safe: availability never rises, the rollout refuses to proceed, and your old Pods keep serving. A **false ready signal** is dangerous, because it is not an error — it is the rollout succeeding at the wrong thing, at full speed. `maxUnavailable` cannot protect you from it, because it is counting Pods the cluster believes are fine.

</details>

<!-- figure -->

```
   THE TWO PERCENTAGES (defaulted, never written by you)
     maxSurge       25%  rounds UP    -> how far ABOVE replicas it may go
     maxUnavailable 25%  rounds DOWN  -> how far BELOW it may drop
       at 4 replicas: max 5 exist, min 3 available
       at 3 replicas: ceil(.75)=1 surge, floor(.75)=0 unavailable
                      -> NEVER drops below full capacity
       rounding is asymmetric ON PURPOSE: spend a Pod, not availability.

   A ROLLBACK IS NOT AN UNDO LOG
     old ReplicaSets are KEPT at 0, templates intact.
     rollout undo = scale old RS up, new RS down. same verb as rolling forward.
     so revision history is A SHELF OF OBJECTS, not a journal
       -> revisionHistoryLimit: 10   (set it to 0 and you cannot roll back)
     CHANGE-CAUSE is an ANNOTATION and nothing writes it (--record is gone):
       kubectl annotate deployment/x kubernetes.io/change-cause="..." --overwrite

   TWO KINDS OF BAD DEPLOY
     broken image / crash        SAFE.  availability never rises, so the
                                        rollout cannot proceed. old Pods serve.
                                        gives up at progressDeadlineSeconds (600)
                                        -> Progressing=False ProgressDeadlineExceeded
     FALSE READY SIGNAL          DANGEROUS. not an error. the rollout SUCCEEDS,
                                        at full speed, replacing every good Pod.
                                        maxUnavailable cannot help: it is counting
                                        Pods the cluster believes are fine.
                                        minReadySeconds: 0 by default = no probation.
```

**Cleanup:**

```bash
kubectl delete deployment web
kubectl get rs -A -l app=web       # nothing left behind
```

> **You understand this when you can** compute the peak and floor Pod counts for a rollout from
> `maxSurge`/`maxUnavailable`, and say which way each rounds; explain what `rollout undo` does to
> which objects, and why `revisionHistoryLimit` limits your ability to roll back; say why a broken
> image is a *safe* failed deploy, and name the condition and default deadline that ends it; and
> describe the one bad deploy rolling updates cannot protect you from.

**Which raises:** twice now the answer has come down to what "ready" means, and both times it was a default you did not choose — a container is ready because it started. That cannot be right for anything that opens a database connection or loads a cache. So who is asking the question, how often, and what happens to a container that answers wrongly?

---

← Prev: **[From a Pod to a Deployment](01-pod-to-deployment.md)** · ↑ **[Act VII overview](README.md)** · Next: **[Who decides a container is working](03-probes.md)** →
