# Act VII — Describing the work

Two acts of Kubernetes, and you have never once described a workload.

Every Pod you have run came from a one-liner. `kubectl create deployment web --image=...`, `kubectl run db-0 --image=...` — typed to have *something* running so you could look at the machinery around it. You have read the network path a request takes to reach a workload, and you have read the loops that place and restart one. You have never said what the workload *needs*.

That is the gap this act closes, and the question it opens with is smaller than it sounds: **what do you actually have to tell a cluster about your software, and what does it work out for itself?**

## The idea that holds the act together

Act VI left you with a sentence worth repeating: no component calls another, so every behaviour you think of as *Kubernetes doing something* is a loop watching a stored document and acting on one part of it.

Turn that around and you get this act's spine. **A Pod spec is not a configuration file. It is a bundle of claims, and each claim is read by a different loop.**

```
   spec.containers[].resources.requests   ->  the SCHEDULER, before any machine exists
   spec.containers[].resources.limits     ->  the KUBELET, then the KERNEL (Act IV's cgroup)
   spec.nodeSelector / affinity / tolerations -> the SCHEDULER, narrowing its choice
   spec.containers[].livenessProbe        ->  the KUBELET on that node, alone
   spec.containers[].readinessProbe       ->  the ENDPOINT controller (Act V's Service)
   spec.volumes[]                          ->  the KUBELET, and sometimes a storage driver
   spec.replicas (on the enclosing object) ->  a CONTROLLER, counting
```

Every one of those is a field you write once and never think about again — and every one has a *different* reader, on a different machine, with a different failure mode. Which is why "my Pod won't start" is never one question. **Knowing which loop reads a field tells you where to look when the promise is not kept**, and that is the transferable skill this act is really about.

Act IV gave you half of this already and told you so. When you wrote `limits.memory`, something wrote a number into `memory.max` and the kernel took over. That lesson ended by pointing at the *other* number in the same block:

> *"A ceiling is a file on a machine that already exists. The other number is a claim made before any machine has been chosen… So who reads that second number, and what do they have to know that a kernel does not?"*

You have since met the answer without recognising it — you stopped a loop in Act VI and watched a Pod sit `Pending` with an empty `spec.nodeName`. Lesson 04 is where that becomes an answer, and where the second half of the question gets one.

## The lab for this act

The same `kind` cluster as Acts V and VI. If you do not have it, [the Act V lab lesson](../act-5-kubernetes/01-lab-with-kind.md) builds it in a minute.

Two things about this act's experiments, in contrast to the last one. They are **gentler** — nothing here stops a control-plane component, and a mistake costs you a Pod rather than a cluster. But they are **slower**, because you will spend real time watching rollouts, probe intervals and eviction timers elapse. Where a wait is load-bearing the text says how long and why; resist shortening it, because the timing *is* the lesson in at least three places.

One genuine hazard, in the storage lessons: a `PersistentVolumeClaim` can outlive the Pod that used it and quietly hold disk. Each lesson cleans up after itself, and the check is:

```bash
kubectl get pvc -A        # empty, unless a lesson explicitly told you to keep one
```

## The lessons — read in this order

1. **[From a Pod to a Deployment](01-pod-to-deployment.md)** — you have used all three of these objects without being told why there are three.
2. **[Rolling updates, and the promise nobody wrote down](02-rolling-updates.md)** — the percentages you never typed, why a rollback is not an undo log, and the one bad deploy that rolling updates cannot save you from.
3. **[Who decides a container is working](03-probes.md)** — two probes with almost the same syntax. One of them is a load-balancer decision and the other is life or death, and the syntax will not tell you which.
4. **[The claim made before there is a machine](04-scheduling.md)** — Act IV's unanswered question. Why a cluster can be full and idle at once, and every way to narrow where a Pod lands.
5. **[Configuration, and where a secret actually ends up](05-configuration.md)** — why an env var cannot change under a running process but a file can, and the three places your password is sitting in plaintext.
6. **[Three different promises called "survives"](06-storage.md)** — Act I's oldest unanswered question, and how much of the answer you cannot read off the manifest.
7. **[When replicas are not interchangeable](07-the-other-workload-kinds.md)** — you built a StatefulSet by hand in Act V. Four workload kinds, each existing because one assumption about a replica is false.
8. **[Shipping a set of objects](08-shipping-a-set-of-objects.md)** — two tools that disagree about what a manifest is, and the discovery that neither is a Kubernetes feature at all.
8b. **[GitOps, which you have already built](08b-gitops.md)** — the reconciliation loop with a git repo as desired state, in four lines. Self-heal turns out not to be healing, a deleted file turns out not to be a deletion, and the drift check reports `in sync` while an orphan runs.
9. **[Adding a kind](09-adding-a-kind.md)** — Act V told you what a CRD is and what happens when nobody watches one. This is where you prove it, and then write the watcher yourself in twenty-five lines of shell.
10. **[Choosing the number](10-choosing-the-number.md)** — every replica count in this act was one you typed. What would it take for the cluster to pick it, and what would it have to measure to do that honestly?

Then three pages to consolidate, in this order:

- **[Test yourself](test-yourself.md)** — twenty questions on the derivations rather than the flags.
- **[Diagnose it](diagnose.md)** — seven workload failures, symptom first. In six of the seven there is nothing wrong with the cluster and nothing wrong with the image.
- **[The instrument panel](../../reference/README.md)** — where to look a tool or a `/proc` path up once you have stopped meeting it for the first time, and the naming grammar that makes an unfamiliar command guessable.
- **[In the wild](in-the-wild.md)** — what changes on a managed cluster, and the three findings here that are line items on an invoice.

## What breaks here

Three shapes, and they map onto the spine above.

**A claim nobody can satisfy.** You ask for more than exists, or for a node that is not there, and the object is *accepted* — because the API server's job is to store your document, not to agree with it. Act VI taught you what that looks like: a perfectly valid record, and a loop that reads it and declines. `Pending` is not a failure, it is a negotiation you are losing, and the Pod's events are the transcript.

**A claim read by the wrong loop, or by two.** The most expensive confusions in Kubernetes come from fields that look adjacent and are not. `requests` and `limits` live in the same block and are enforced by different machines at different times. `livenessProbe` and `readinessProbe` have nearly identical syntax, different readers, and consequences that are not interchangeable at all. Getting those two the wrong way round is the single most common self-inflicted outage in the subject, and lesson 03 asks you to predict which is which before it says.

**A promise about durability that nobody actually made.** Act I ended on the split between the writable layer that dies with the container and the mount that outlives it, and asked who decides where the surviving path points. That question has been open for six acts. The answer is here, and the reason it needs a whole lesson is that **"survives" is not one promise.** There is more than one thing a volume can outlive, the manifests do not look as different as the guarantees are, and lesson 06 is mostly the work of telling them apart.

> **The question to carry forward:** every field you are about to write is a request to some loop you have already met. So when the cluster does not do what your YAML says, which is more likely — that the field is wrong, or that you are asking the wrong loop?
