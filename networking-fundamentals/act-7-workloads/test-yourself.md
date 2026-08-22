# Act VII — Test yourself

> Do this **after** working through all the lessons in [the act overview](README.md). Answer each one out loud or on paper *before* you open its answer — the attempt is what makes it stick, far more than re-reading. A wrong attempt followed by the right answer beats a confident skim every time.

> **Question 1 —** You `kubectl run` a bare Pod and then `crictl stop` its container. The Pod comes back with `RESTARTS 1`. Then you drain the node and the Pod is gone forever. Both facts involve "something restarted it or did not." Name the two different mechanisms, and say which object each one was reading.

<details>
<summary>Answer</summary>

The first is the **kubelet**, reading `spec.restartPolicy` on the Pod object it was assigned. `Always` means a container that *exits* — including exiting successfully — gets started again, in the same Pod, on the same node, with the same IP. It is a local promise made by one machine about one record it already holds.

The second is **nothing**, and that is the point. No loop anywhere is watching to see whether a Pod named `solo` exists, because a bare Pod is not owned by anything that holds a count. When the record went, the last trace of your intent went with it.

Which is exactly why `drain` refused without `--force`: it is willing to delete a Pod it can see something will replace, and it makes you say so explicitly for one that nothing owns.

</details>

> **Question 2 —** A rolling update requires *two* ReplicaSets. Explain why one cannot do it, and say what `pod-template-hash` prevents.

<details>
<summary>Answer</summary>

A ReplicaSet's job is to make the world match *its* Pod template. Change that template and it wants everything replaced, immediately, with no notion of doing it gradually — so a single ReplicaSet cannot hold two versions at once. You need one draining from N to 0 while another fills from 0 to N, in steps small enough that enough Pods are serving throughout. Something has to conduct that, and the Deployment is it: its entire vocabulary is *writing counts into ReplicaSets*.

`pod-template-hash` is what lets the two coexist. Each ReplicaSet selects on `app=web` **plus its own hash**, so the two loops own disjoint sets of Pods. Without it both would believe they owned all the Pods and would spend the rollout deleting each other's work.

</details>

> **Question 3 —** `maxSurge` and `maxUnavailable` both default to 25%, and on 4 replicas both work out to 1. On 6 replicas they do not. Which rounds up, which rounds down, and what single principle explains both?

<details>
<summary>Answer</summary>

`maxSurge` rounds **up**; `maxUnavailable` rounds **down**. On 6 replicas at 25% that is 2 surge and 1 unavailable.

The principle is that both round in the direction of *more capacity*. Rounding surge up means possibly one extra Pod — you pay for a container for a few minutes. Rounding unavailable down means possibly one fewer Pod out of service — you keep capacity you might not have needed. Both errors cost money; the errors in the other direction cost availability.

This is the same reasoning as the HPA's asymmetric stabilisation windows in lesson 10, and it generalises: when you find an asymmetric default in this subject, ask which of the two mistakes it is refusing to make.

</details>

> **Question 4 —** `kubectl rollout undo` takes you back to the previous version, and yet the revision number goes *up*. Explain what it actually did, and why "rollback" is a misleading name for it.

<details>
<summary>Answer</summary>

It is not an undo log and nothing is being reversed. The old ReplicaSet was never deleted when the rollout finished — it was scaled to `DESIRED 0` with its Pod template intact. `undo` reads that template and performs a **new rolling update** towards it, which means scaling the old ReplicaSet back up and the current one down.

So it is a roll *forward* to a previous state, which is why history only ever grows. And it explains the two things people find surprising: rolling back is exactly as slow as rolling out, because it is the same operation; and if you prune old ReplicaSets there is nothing to roll back to.

Contrast Helm's `rollback` from lesson 08, which genuinely does restore a stored copy — Helm keeps the rendered manifest in a Secret per revision. Neither is an undo log, but for opposite reasons: one replays a recording, the other re-runs a rollout.

</details>

> **Question 5 —** Two probes, nearly identical syntax. One is set on a container that takes 40 seconds to warm up and the syntax is otherwise perfect. Describe the two possible outcomes depending on which probe it was, and say which is worse.

<details>
<summary>Answer</summary>

If it was a **readinessProbe**, the Pod runs, stays `Running`, reports `0/1` in the READY column, and is quietly kept out of its Service's endpoints for 40 seconds. Then it joins. Nothing is lost. That is the probe doing its job.

If it was a **livenessProbe**, the kubelet concludes the container is dead 40 seconds before it was ever alive and kills it. It restarts, fails to warm up in time again, and is killed again — `CrashLoopBackOff` on a container that has nothing wrong with it. The application can never start, and the logs look like a startup bug.

The liveness case is far worse, and it is worse in a specific way: it turns a slow start into a permanent outage, and it does so *only under the conditions that make starting slow* — a cold cache, a busy database, a node under load. So it passes in testing and fires during the incident it makes worse. `startupProbe` exists precisely for this: it suspends liveness until the container has started once.

</details>

> **Question 6 —** `requests` and `limits` sit in the same block. Name what enforces each, when, and against what.

<details>
<summary>Answer</summary>

A **limit** is enforced by the kubelet writing a number into a cgroup file, and then by the **kernel, continuously, against reality** — Act IV's `memory.max`. It is a ceiling on a machine that already exists.

A **request** is enforced by the **scheduler, once, against arithmetic**. It sums the requests of every Pod already assigned to a node, compares that against `Allocatable`, and refuses if your number does not fit. It never looks at actual usage — it cannot usefully, because it is placing a Pod that has not started.

The consequence is the one worth carrying: a cluster can be completely full and almost entirely idle at the same time, because the ledger is full while the machines are not. That is the single largest source of wasted capacity in real clusters.

</details>

> **Question 7 —** Someone omits `resources` entirely, reasoning that an unconstrained Pod can use whatever is free. Name the three separate things that decision costs them.

<details>
<summary>Answer</summary>

1. **It is invisible to the scheduler's arithmetic.** Contributing zero to the ledger, it will be packed onto nodes whose capacity is already promised away — so it competes for real CPU with Pods that reserved it.
2. **It is `BestEffort`, so it is first to be evicted.** QoS is derived from the two numbers, not written, and it decides the order in which the kubelet kills things when a node runs short of memory.
3. **It can never be autoscaled on utilisation** — and that one has its own question later in this page, so work out why before you get there. The other two at least produce symptoms; this one is silent.

</details>

> **Question 8 —** A node loses power. Roughly five minutes later its Pods appear elsewhere. Where does the five minutes come from, and what field would you change?

<details>
<summary>Answer</summary>

It is a **toleration you did not write**. Every Pod is given `node.kubernetes.io/not-ready` and `node.kubernetes.io/unreachable` tolerations for the `NoExecute` effect with `tolerationSeconds: 300`.

The chain: the node stops sending heartbeats, a controller marks it `NotReady` and taints it with those keys, and `NoExecute` evicts Pods that do not tolerate the taint. Yours tolerate it — for exactly 300 seconds. When that expires, eviction proceeds.

So the delay is not a timeout on detection; it is a deliberate grace period, and you change it by setting those tolerations explicitly with a different `tolerationSeconds`. Shorten it and a brief network blip relocates your whole workload; lengthen it and a genuinely dead node holds its Pods hostage.

</details>

> **Question 9 —** You add a taint to a node to reserve it for one team, and give that team's Pods a matching toleration. Their Pods land on other nodes instead. Nothing is broken. Why?

<details>
<summary>Answer</summary>

Because a toleration **permits, it does not attract**. It removes an objection; it expresses no preference. Their Pods are now eligible for the reserved node *and* for every other node, and the scheduler will spread them as it sees fit.

Reserving a node takes both halves: a taint to keep everyone else off, and something on the Pod that actively wants that node — a `nodeSelector` or `nodeAffinity` on a label you also put there. Taints and tolerations are a one-sided lock; the pull has to come from somewhere else.

</details>

> **Question 10 —** One ConfigMap value, consumed two ways. You edit it. Describe what happens to each, and explain the difference from what a process *is*.

<details>
<summary>Answer</summary>

The **mounted file** changes, on its own, in about a minute (measured: 64 seconds), with no restart. The **environment variable** never changes, for the life of that process.

The reason is not a Kubernetes design choice. A process's environment is a block of strings inside its private address space, copied in by the kernel at `exec()`. There is no syscall to alter another process's environment, because the address space is private in both directions — and the read-only `/proc/<pid>/environ` you met in Act I is the shape of what is possible. So an env var is a snapshot, and changing it means a new process, which means a rollout.

A mounted ConfigMap is a directory, and a directory can be rewritten. The kubelet writes a whole new timestamped directory and swings the `..data` symlink to it, so a reader never sees a half-written value — an ordinary symlink and the ordinary guarantee that renaming one is atomic.

</details>

> **Question 11 —** Same setup, but the file was mounted with `subPath`. What changes, and how would you have predicted it from the mechanism?

<details>
<summary>Answer</summary>

It never updates. Not slowly — never, for the life of the container.

Predictable directly from the swap: the atomicity comes from repointing `..data`, which lives *one level up* from the file. A `subPath` mount is not in that directory at all — the kubelet copied the content in when the container started, and there is no symlink to repoint. You can see it before testing it: the `subPath` target is a plain file where the directory-mounted one is a symlink.

This is the worst failure shape in the act, because it works perfectly in development, where you restart things constantly, and fails in production, where you expected a config change to take effect and nothing said otherwise.

</details>

> **Question 12 —** Name the three places one Secret's plaintext exists, and which of them can be read without any cluster credentials.

<details>
<summary>Answer</summary>

1. **In etcd**, unencrypted by default — Act VI had you `grep -a` a password straight out of a snapshot file.
2. **On the node**, under `/var/lib/kubelet/pods/<uid>/volumes/kubernetes.io~secret/<vol>/<key>`. This is `tmpfs`, so it is in RAM rather than on disk — but that is not a meaningful protection against someone with a shell.
3. **In `/proc/<pid>/environ`**, if it was consumed as an environment variable. This one is the worst of the three because every child process inherits the copy, so a crash handler or a subprocess that logs its environment leaks it without knowing it handled a secret.

Two and three are readable with a shell on the node and no cluster credentials at all. Which is the same lesson Act VI taught about `ca.key`: a shell on a node is close to a shell in the cluster.

A Secret is not encryption. It is a separate object with separate access control, and that is its entire value.

</details>

> **Question 13 —** Three things a volume might "survive." Name them, and say which the lab's default StorageClass gives you.

<details>
<summary>Answer</summary>

Surviving a **container restart**, surviving the **Pod**, and surviving the **machine**.

Getting the middle one right matters, because "surviving a reschedule onto another node" is the plausible-sounding version and it is *not* what the middle promise says — the whole point of lesson 06's second half is that a `local-path` volume does not survive a reschedule at all.

`emptyDir` gives you the first only: the kubelet made the directory when the Pod was placed, so it outlives a crashed container and dies with the Pod.

A `local-path` PVC gives you the first two — the data outlives the Pod, on the same node — but the PV is a directory on one named node, pinned by node affinity. Lose that machine and the data is gone; make that machine unschedulable and the Pod cannot run anywhere.

And the sting: the manifest that gives you promise two and the manifest that gives you promise three are **the same manifest**. Which one you actually got depends entirely on what the StorageClass provisions, and `kubectl get storageclass` is the only place to find out.

</details>

> **Question 14 —** A StatefulSet has no `maxSurge`. Give two independent reasons why it could not have one.

<details>
<summary>Answer</summary>

1. **The name is the identity.** Surging means creating an extra Pod before removing an old one, which requires a Pod that needs no particular name. There cannot be two `db-1`s.
2. **The disk is `ReadWriteOnce`.** Even if two Pods could share a name, the replacement could not mount `data-db-1` while the original held it.

So surging is not disabled here as a policy choice — it is unavailable in principle, which is why updates are strictly sequential from the highest ordinal down. `partition` replaces it: a floor, below which nothing is updated, which gives you a canary keyed to *identity* rather than to a statistical fraction. A Deployment cannot express that at all, because "update one specific replica" is meaningless when the replicas have no names.

</details>

> **Question 15 —** You scale a StatefulSet from 5 to 2 to save money. What actually happens to the cost, and what will surprise the next person to scale it back up?

<details>
<summary>Answer</summary>

Three Pods go — in reverse ordinal order, `db-4` then `db-3` then `db-2` — and **all five PVCs remain**. You stopped paying for compute and kept paying for storage.

The controller cannot tell whether you are shrinking permanently or restarting something, and one of those two mistakes destroys a database. So it makes the recoverable choice and leaves you to delete the claims deliberately.

Which means the next person to scale back up gets Pods that come back with **data already in them**, because the claim name is derived from the Pod name: the controller needs `data-db-3`, finds a Bound PVC by that name, and uses it. Whether that is a relief or a disaster depends on what is on the disk — a database member rejoining with a stale copy of a dataset that has moved on can be considerably worse than an empty one, because it will try to participate.

`kubectl get pvc` before scaling up, not after.

</details>

> **Question 16 —** Where does a DaemonSet's replica count live, and how does that explain why `kubectl drain` needs a flag for its Pods?

<details>
<summary>Answer</summary>

There is no `spec.replicas` field on a DaemonSet at all. The count lives in **`status.desiredNumberScheduled`** — a derived fact, not a claim. The controller counted your nodes and wrote down what it found, which is a genuine exception to the rest of this act, where every count is intent you wrote in `spec`.

`drain` evicts Pods so something can place them elsewhere, and it cordons first so replacements do not land back on the node being emptied. Against a DaemonSet Pod both halves fail: there is nowhere else it is *supposed* to be, and the DaemonSet controller automatically adds a `node.kubernetes.io/unschedulable` toleration to every Pod it creates — so the cordon does not keep it away. Evicting one produces an identical Pod on the same node about a second later.

`--ignore-daemonsets` is not a convenience. It is `drain` declining to enter a loop it cannot win.

</details>

> **Question 17 —** Derive, without looking it up, why `restartPolicy: Always` is rejected on a Job.

<details>
<summary>Answer</summary>

`Always` means the kubelet restarts a container when it *exits* — note the word: exits, not fails. Exit code 0 restarts too.

A Job is finished when its Pod reaches `Succeeded`, and a Pod reaches `Succeeded` only when its containers have exited and stayed exited.

Put those together and the very event that would complete the Job is the event that restarts it. The Job could never finish. The two fields are not a poor combination, they are logically contradictory, so validation refuses rather than letting you store an object no loop could ever satisfy.

That is also why failed Job Pods are *kept* rather than tidied away: with `restartPolicy: Never` each retry is a new Pod, and the failed ones hold the only record of why the work failed. `ttlSecondsAfterFinished` is the field that cleans up, and its absence is the default for the same reason.

</details>

> **Question 18 —** A colleague says their cluster is "managed by Helm." What is wrong with that sentence, and what single command demonstrates it?

<details>
<summary>Answer</summary>

Nothing in a cluster is managed by Helm, because Helm is a client. `kubectl api-resources` has no `Chart`, no `Release`, no `Kustomization` — the set of kinds is fixed, and Helm adds none of them. It renders YAML on your laptop and POSTs ordinary objects, which then sit indistinguishably next to hand-written ones.

Which is why `helm list` needs somewhere to keep its own memory, and — since the API server has no idea what a release is — it uses a kind that already exists: a **Secret** named `sh.helm.release.v1.<name>.<revision>`, holding the rendered manifest gzipped and base64'd twice.

And that explains the failure mode. `kubectl scale` a Helm-managed Deployment and `helm list` still cheerfully reports `deployed`, because the Secret records what Helm *sent*, not what *is*. Nothing reconciles them; the next `helm upgrade` is the only moment anyone checks.

</details>

> **Question 19 —** You apply a `Certificate` object from a tutorial. It appears in `kubectl get`, has a `uid`, and passes validation. Nothing happens, `status` is empty and there are no events. Which two facts have you proved, and what is the diagnosis?

<details>
<summary>Answer</summary>

You have proved that (a) the kind exists — a CRD is installed — and (b) your YAML is structurally fine, because the API server validated it against that CRD's `openAPIV3Schema` server-side before storing it. Being stored proves the schema was satisfied and nothing else whatsoever.

The diagnosis is **nobody looked.** A CRD extends the *store*; it does not add a *loop*. Something that looked and disagreed would write a condition or an event saying so — that is what `status` is for. An empty status with no events is the signature of no controller running, which is the same signature as Act VI's `Events: <none>` on a Pending Pod.

Installing a CRD and installing its controller are two separate acts, and the first one alone gives you a perfectly functional place to store objects that nothing will ever read.

</details>

> **Question 20 —** An HPA on CPU at 50% shows `TARGETS: <unknown>/50%` and never scales, while `kubectl top pods` reports real numbers for the same Pods. Explain it, then say what `Pending` has to do with autoscaling.

<details>
<summary>Answer</summary>

Utilisation is a ratio, and the denominator is not the node's capacity and not the limit — it is the container's **`requests`**. A Deployment created by a one-liner has none, so there is no denominator, so there is no ratio, and the HPA declines to guess. `describe hpa` says it outright: `ScalingActive: False`, `missing request for cpu`. `kubectl top` works because it reports raw usage; the HPA needs a fraction.

Fixing it means giving the workload a denominator, not configuring the autoscaler.

As for `Pending`: the HPA writes `spec.replicas` through the `/scale` subresource and knows nothing about capacity. Set `maxReplicas` above what your nodes can hold and the surplus Pods sit `Pending` with `Insufficient cpu`. On a cloud cluster a **Cluster Autoscaler** is watching for exactly that state and buys a machine in response.

So `Pending` — which this act treated throughout as a diagnosis — is also an **API between two autoscalers**. Whether an over-ambitious `maxReplicas` is harmless or expensive depends entirely on whether that second component is installed.

</details>

---

↑ **[Act VII overview](README.md)** · Next: **[Diagnose it](diagnose.md)** →
