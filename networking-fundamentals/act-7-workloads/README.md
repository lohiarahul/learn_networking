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
   spec.volumes[]                          ->  the KUBELET, and sometimes a CSI driver
   spec.replicas (on the enclosing object) ->  a CONTROLLER, counting
```

Every one of those is a field you write once and never think about again — and every one has a *different* reader, on a different machine, with a different failure mode. Which is why "my Pod won't start" is never one question. **Knowing which loop reads a field tells you where to look when the promise is not kept**, and that is the transferable skill this act is really about.

Act IV gave you half of this already and told you so. When you wrote `limits.memory`, something wrote a number into `memory.max` and the kernel took over. That lesson ended by pointing at the *other* number in the same block:

> *"A ceiling is a file on a machine that already exists. The other number is a claim made before any machine has been chosen… So who reads that second number, and what do they have to know that a kernel does not?"*

You have since met the answer without recognising it. In Act VI you stopped a loop and watched a Pod sit `Pending` with an empty `spec.nodeName`. That loop is what reads `requests`.

## The lab for this act

The same `kind` cluster as Acts V and VI. If you do not have it, [the Act V lab lesson](../act-5-kubernetes/01-lab-with-kind.md) builds it in a minute.

Two things about this act's experiments, in contrast to the last one. They are **gentler** — nothing here stops a control-plane component, and a mistake costs you a Pod rather than a cluster. But they are **slower**, because you will spend real time watching rollouts, probe intervals and eviction timers elapse. Where a wait is load-bearing the text says how long and why; resist shortening it, because the timing *is* the lesson in at least three places.

One genuine hazard, in the storage lessons: a `PersistentVolumeClaim` can outlive the Pod that used it and quietly hold disk. Each lesson cleans up after itself, and the check is:

```bash
kubectl get pvc -A        # empty, unless a lesson explicitly told you to keep one
```

## The lessons — read in this order

*(This act is being written. Lessons appear here as they land.)*

1. **[From a Pod to a Deployment](01-pod-to-deployment.md)** — you have used all three of these objects without being told why there are three.
2. **[Rolling updates, and the promise nobody wrote down](02-rolling-updates.md)** — the percentages you never typed, why a rollback is not an undo log, and the one bad deploy that rolling updates cannot save you from.
3. **[Who decides a container is working](03-probes.md)** — two probes, identical syntax, opposite consequences. One is a load-balancer decision; the other is life or death.
4. **[The claim made before there is a machine](04-scheduling.md)** — Act IV's unanswered question. Why a cluster can be full and idle at once, and every way to narrow where a Pod lands.
5. **[Configuration, and where a secret actually ends up](05-configuration.md)** — why an env var cannot change under a running process but a file can, and the three places your password is sitting in plaintext.
6. **[Three different promises called "survives"](06-storage.md)** — Act I's oldest unanswered question. Why the manifest that keeps your data through a machine failure and the one that loses it are the same manifest.
7. **[When replicas are not interchangeable](07-the-other-workload-kinds.md)** — you built a StatefulSet by hand in Act V. Four workload kinds, each existing because one assumption about a replica is false.

## What breaks here

Three shapes, and they map onto the spine above.

**A claim nobody can satisfy.** You ask for more than exists, or for a node that is not there, and the object is *accepted* — because the API server's job is to store your document, not to agree with it. Act VI taught you what that looks like: a perfectly valid record, and a loop that reads it and declines. `Pending` is not a failure, it is a negotiation you are losing, and the Pod's events are the transcript.

**A claim read by the wrong loop, or by two.** The most expensive confusions in Kubernetes come from fields that look adjacent and are not. `requests` and `limits` live in the same block and are enforced by different machines at different times. `livenessProbe` and `readinessProbe` have nearly identical syntax and *opposite* consequences — one restarts your container, the other quietly removes it from a Service and leaves it running. Getting those two the wrong way round is the single most common self-inflicted outage in the subject.

**A promise about durability that nobody actually made.** Act I ended on the split between the writable layer that dies with the container and the mount that outlives it, and asked who decides where the surviving path points. It also said Act V would answer, which was optimistic — Act V taught how traffic *reaches* a workload and said nothing about its data. The answer is here, and the reason it needs a whole lesson is that **"survives" is not one promise.** Surviving a restart, surviving a reschedule onto another node, and surviving the cluster are three different guarantees with three different mechanisms, and a volume that gives you the first while you assumed the third is how data gets lost.

> **The question to carry forward:** every field you are about to write is a request to some loop you have already met. So when the cluster does not do what your YAML says, which is more likely — that the field is wrong, or that you are asking the wrong loop?
