# The claim made before there is a machine

Act IV left you a question and you have been carrying it for two acts. You had just watched `limits.memory` become a number in `memory.max`, with the kernel doing the enforcing, and the lesson pointed at the *other* number in the same block:

> *"A ceiling is a file on a machine that already exists. The other number is a claim made before any machine has been chosen, and no file on any host can satisfy it: ask for 8 GiB where there are 4, and the kernel you have been reading all lesson has nothing to say, because it only knows about **this** box. So who reads that second number, and what do they have to know that a kernel does not?"*

You have since met the reader without being told that is what it was. In Act VI you moved one file out of `/etc/kubernetes/manifests/`, created a Deployment, and got a Pod that sat `Pending` with an empty `spec.nodeName` and `Events: <none>`.

So the answer is *the scheduler*, and the interesting half of the question is the second half: **what does it have to know that a kernel does not?**

### What is a request, if it is not a reservation?

```bash
kubectl describe node netlab-worker | grep -A7 'Allocated resources'
```

Read that table carefully, because it is the entire scheduling model:

```
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests   Limits
  cpu                100m (1%)  100m (1%)
  memory             50Mi (0%)  50Mi (0%)
```

Two columns, and they are **two independent sums** — not one number shown two ways. On a fresh worker they happen to match, because the only thing running is a DaemonSet that sets both to the same value. That will not last; you will make them disagree yourself in a few minutes, and the parenthesis at the top of the table is a warning about exactly that.

Now the crucial question, and it is the one that separates understanding this from memorising it:

> **Predict first —** a node has 4 CPUs. You schedule four Pods each requesting `1` CPU, and the node is now "full" by the scheduler's arithmetic. Each Pod is actually idle, using about 1% of a core. **Can a fifth Pod requesting `1` CPU be scheduled onto that node?** And separately: is the *real* CPU on that node busy?

```bash
kubectl describe node netlab-worker | grep -A8 'Allocatable'
kubectl top node netlab-worker 2>/dev/null || echo "(no source of actual usage on this cluster — that is the point)"
```

The answer is **no, and no.** The fifth Pod cannot be scheduled, and the node is nearly idle.

Which tells you what a request actually is: **not a measurement, and not a reservation of anything physical. It is a number in a ledger.** The scheduler adds up the `requests` of every Pod already assigned to a node, compares against `Allocatable`, and refuses if your number does not fit. It never looks at actual usage. It could not usefully — it is placing a Pod that has not started yet, and past usage of *other* Pods tells it nothing about the future.

So the answer to Act IV's question is sharper than "the scheduler reads it":

**A `limit` is enforced by the kernel, continuously, against reality. A `request` is enforced by the scheduler, once, against arithmetic.** The kernel knows what is happening; the scheduler knows what has been promised. Neither knows the other's answer, and a cluster can be simultaneously "full" and idle — which is the single most common source of expensive over-provisioning in the industry.

### Two numbers, three classes

The pair you write has a consequence you did not write, and it is a field you can read:

```bash
kubectl run guaranteed --image=nginx:1.27-alpine \
  --overrides='{"spec":{"containers":[{"name":"c","image":"nginx:1.27-alpine","resources":{"requests":{"cpu":"50m","memory":"64Mi"},"limits":{"cpu":"50m","memory":"64Mi"}}}]}}'
kubectl run burstable --image=nginx:1.27-alpine \
  --overrides='{"spec":{"containers":[{"name":"c","image":"nginx:1.27-alpine","resources":{"requests":{"cpu":"50m","memory":"64Mi"},"limits":{"memory":"128Mi"}}}]}}'
kubectl run besteffort --image=nginx:1.27-alpine
sleep 20
kubectl get pods guaranteed burstable besteffort \
  -o custom-columns='NAME:.metadata.name,QOS:.status.qosClass'
```

```
NAME          QOS
guaranteed    Guaranteed
burstable     Burstable
besteffort    BestEffort
```

(One thing about those two commands, since you will reuse the trick: `--overrides` is a *merge patch* on the object `kubectl run` would have generated, and a merge patch on a **list** replaces the whole list. That is why `name` and `image` have to be repeated inside the override — leave them out and you get a container with no image. It is also why `besteffort`'s container is called `besteffort` while the other two contain a container called `c`.)

**Nobody wrote `qosClass`.** It is derived: requests equal to limits on every container is `Guaranteed`; some requests set is `Burstable`; nothing set at all is `BestEffort`.

And it decides the order in which your Pods are killed. When a node runs genuinely short of memory, the kubelet evicts to save itself, and it goes for `BestEffort` first, then `Burstable` that is exceeding its requests, and `Guaranteed` last. So the two numbers you write are not only a scheduling claim and a kernel ceiling — **together they are a position in a queue you did not know you were in.**

Which reframes "just leave the resources out." A Pod with no requests is not unconstrained; it is first in line to die, and it is invisible to the scheduler's arithmetic, so it will be packed onto nodes that are already promised away.

Before deleting them, go back and read the node's ledger again — the three Pods you just made have changed it:

```bash
kubectl describe node $(kubectl get pod burstable -o jsonpath='{.spec.nodeName}') \
  | grep -A7 'Allocated resources'
```

```
  Resource   Requests    Limits
  cpu        200m (2%)   150m (1%)
  memory     178Mi (2%)  242Mi (3%)
```

**The cpu column now has limits *lower* than requests**, which reads like an error and is not. Work out where it came from before reading on: it is entirely your doing, and one of the three Pods is responsible.

`burstable` sets a cpu *request* of `50m` and no cpu *limit* at all. So it contributes to the left column and not the right, and the sums drift apart. Memory drifts the other way, because that same Pod has a limit of `128Mi` against a request of `64Mi`.

That is the real content of those two columns: **a node's requests total and its limits total are answers to different questions**, asked of different Pods, enforced by different components at different times. Comparing them to each other is meaningless. The only comparison that decides anything is requests against `Allocatable`.

```bash
kubectl delete pod guaranteed burstable besteffort --wait=false
```

### Narrowing the choice

The scheduler picks *a* node that fits. Everything else in this lesson is about telling it which.

Start with the bluntest instrument, and notice it is the same shape as the field Act VI showed you:

```bash
kubectl label node netlab-worker disk=ssd
kubectl run picky --image=nginx:1.27-alpine --overrides='{"spec":{"nodeSelector":{"disk":"ssd"}}}'
kubectl get pod picky -o wide
```

Scheduled, on the labelled node. `nodeSelector` is an exact-match requirement — every key must match, or the node is out.

> **Predict first —** you ask for a label that no node has. The Pod is a valid object and the API server will store it happily. So what state does it end up in, and — the part that matters — **where is the explanation?** You already know the answer to this from Act VI; say it before you look.

```bash
kubectl run impossible --image=nginx:1.27-alpine --overrides='{"spec":{"nodeSelector":{"disk":"unobtainium"}}}'
sleep 10
kubectl get pod impossible
kubectl describe pod impossible | tail -5
```

`Pending`, and this time the events are **not** empty:

```
Warning  FailedScheduling  ... 0/2 nodes are available: 1 node(s) didn't match
Pod's node affinity/selector, 1 node(s) had untolerated taint(s). no new claims
to deallocate, preemption: 0/2 nodes are available: 2 Preemption is not helpful
for scheduling.
```

That message is worth reading as a sentence rather than an error. It is the scheduler telling you it *looked*, how many nodes it considered, and why each was rejected — a **per-reason tally**, which is why the numbers add up to the node count. Act VI taught you that `Events: <none>` means nothing looked; this is the other case, and the distinction is the whole diagnostic.

So read the arithmetic: `0/2 nodes are available`, then `1 node(s)` failed your selector — the worker — and `1 node(s) had untolerated taint(s)`, which is the control-plane node, excluded for a reason you already know and that has nothing to do with what you asked for. Both halves are in the same sentence. The clause about preemption is the scheduler noting that evicting something would not have helped either; it appears on almost every `FailedScheduling` and is usually noise. (`no new claims to deallocate` refers to dynamic resource allocation and is recent — on an older cluster the same message is shorter.)

```bash
kubectl label node netlab-worker disk-
kubectl delete pod picky impossible --wait=false
```

### Taints, and the two-sided handshake

You have met taints twice: the control plane's permanent `NoSchedule`, and the one `cordon` produces. Both were things that *repelled* Pods. Now the other half.

```bash
kubectl taint node netlab-worker maintenance=true:NoSchedule
kubectl run unwelcome --image=nginx:1.27-alpine
sleep 10
kubectl get pod unwelcome
```

`Pending` — both nodes now repel it, for different reasons. A **taint** is on the node and says *keep away unless you say otherwise*. A **toleration** is on the Pod and is that otherwise:

```bash
kubectl run welcome --image=nginx:1.27-alpine --overrides='{"spec":{"tolerations":[{"key":"maintenance","operator":"Equal","value":"true","effect":"NoSchedule"}]}}'
sleep 10
kubectl get pod welcome -o wide
```

Scheduled. And note the asymmetry that catches people: **a toleration does not attract, it only permits.** `welcome` was not sent to the tainted node because it tolerated the taint; it was sent there because that was the only node that fit, and the toleration merely stopped it being excluded. Tolerating a taint you do not need costs nothing and gains nothing.

The three effects are worth having straight, because one of them acts on Pods that are already running:

| Effect | On scheduling | On Pods already there |
|---|---|---|
| `NoSchedule` | refused | **left alone** |
| `PreferNoSchedule` | avoided if possible | left alone |
| `NoExecute` | refused | **evicted** |

`NoExecute` is how a node that goes `NotReady` eventually sheds its Pods — the node controller taints it, and every Pod without a matching toleration is evicted after `tolerationSeconds`. Which is the mechanism behind something you may have wondered about in Act VI: why Pods on a lost node take about five minutes to be recreated elsewhere. That five minutes is a default toleration Kubernetes adds to every Pod for you:

```bash
kubectl get pod welcome -o jsonpath='{range .spec.tolerations[*]}{.key} {.effect} {.tolerationSeconds}{"\n"}{end}'
```

`node.kubernetes.io/not-ready` and `unreachable`, `NoExecute`, `300` seconds. Nobody wrote those. They are the cluster hedging against a node that is briefly unreachable rather than genuinely gone.

```bash
kubectl taint node netlab-worker maintenance=true:NoSchedule-
kubectl delete pod unwelcome welcome --wait=false
```

### Preference, not requirement

`nodeSelector` is all-or-nothing, and most real placement is a preference. `affinity` is the same idea with two flavours, and the field names say exactly what they do — verbosely, and the verbosity is the documentation:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:     # a hard filter, like nodeSelector
      nodeSelectorTerms:
        - matchExpressions:
            - { key: disk, operator: In, values: [ssd, nvme] }
    preferredDuringSchedulingIgnoredDuringExecution:    # a nudge, with a weight
      - weight: 100
        preference:
          matchExpressions:
            - { key: kubernetes.io/os, operator: In, values: [linux] }
```

Two halves of every one of those names carry information. **`DuringScheduling`** is when it is evaluated. **`IgnoredDuringExecution`** is the admission that scheduling is a one-time decision: once the Pod is placed, changing the node's labels does *not* move it. That is not a limitation to work around, it is the same fact as everything else in this act — `spec.nodeName` is written once.

And `operator: In` is the gain over `nodeSelector`: `In`, `NotIn`, `Exists`, `DoesNotExist`, `Gt`, `Lt`. Set membership rather than equality.

There is a **pod**Affinity too, which selects on other *Pods* rather than nodes — "put me near the cache" or, far more usefully, "keep my replicas apart." That second one is common enough to have got its own field, which is the last thing in this lesson.

### Spreading, and the reason it is not affinity

The most frequent placement wish is the plainest: *do not put all my replicas on one node.* There is a way to say it with affinity rules pointed at other Pods rather than at nodes, and it is awkward enough that it is not worth your time here. `topologySpreadConstraints` expresses it directly:

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels: { app: web }
```

Read it as a sentence: *across nodes, the count of Pods labelled `app=web` must never differ by more than 1.*

`maxSkew` is the allowed imbalance. `topologyKey` is the label that defines a "region" to spread across — `kubernetes.io/hostname` for nodes. Cloud providers label nodes with their physical location too, and swapping `kubernetes.io/hostname` for such a label is the whole of spreading across failure domains larger than a machine — the same field, a coarser definition of "somewhere else". And `whenUnsatisfiable` is the interesting field: `DoNotSchedule` makes spreading a **requirement** (a Pod that cannot be placed without breaking the skew stays `Pending`), while `ScheduleAnyway` makes it a preference.

Which is the choice worth thinking about rather than copying, and this lab shows why more sharply than a big cluster would. Apply that constraint to a 3-replica Deployment here and count what runs:

```bash
kubectl get pods -l app=web -o wide
kubectl describe pod -l app=web | grep -A3 'FailedScheduling' | head -6
```

**One Running, two `Pending`** — and the second replica is already refused, not the third:

```
0/2 nodes are available: 1 node(s) didn't match pod topology spread constraints,
1 node(s) had untolerated taint(s).
```

Derive that, because it is a trap rather than a quirk. There are two nodes, so two domains — and the control-plane node is one of them. It is tainted, so nothing you own can land there, but `nodeTaintsPolicy` defaults to `Ignore`, meaning the spread calculation **counts that node as a domain holding zero Pods anyway**. One Pod on the worker against zero on the control plane is already a skew of 1. A second would make it 2, which breaks `maxSkew: 1`, so `DoNotSchedule` refuses — and keeps refusing forever, because the domain it wants you to use is one no Pod of yours can enter.

So `DoNotSchedule` guarantees your spread and will refuse to run Pods to keep that guarantee, including for a domain that is unusable. `ScheduleAnyway` always runs your Pods and silently gives up on the spread exactly when you need it — during the node failure that made you want it. Neither is the safe default, which is why there is no default.

> **Check yourself —** A Pod has been `Pending` for ten minutes. `kubectl describe pod` shows `0/6 nodes are available: 3 Insufficient cpu, 3 node(s) had untolerated taint`. The cluster monitoring shows every node at under 15% CPU. Explain how both facts are true, and give two different fixes.

<details>
<summary>Answer</summary>

Both are true because they measure different things. Monitoring reads actual usage from the kernel; the scheduler reads the sum of `requests` from the store. Three of those nodes have had their capacity *promised away* by Pods that requested CPU and are not using it. The node is idle and full at the same time.

The other three were never candidates at all — they are tainted, and this Pod tolerates nothing. That is probably deliberate (control-plane nodes, or a dedicated pool), so the real capacity of this cluster for this Pod is three nodes, not six.

Two fixes, and they are genuinely different decisions rather than alternatives.

**Lower the requests** — either on this Pod, if its request is inflated, or on the over-requesting Pods that are hoarding the ledger. This is the correct fix when requests were set by guesswork, which is usually. The way to find out is to compare each Pod's `requests` against what it actually uses — which needs a source of actual usage, and you saw earlier in this lesson that this cluster has none. That gap is real and it has an ecosystem of answers; it is not one this act closes.

**Add capacity, or open up the tainted nodes** — a toleration if those nodes are genuinely suitable, more nodes if they are not. This is the correct fix when the requests are honest and the cluster is simply too small.

What will *not* work is anything that assumes the scheduler is looking at real load. It is not, it never was, and no amount of demonstrating that the nodes are idle changes the arithmetic it does.

</details>

<!-- figure -->

```
   ACT IV's QUESTION, ANSWERED

   limits   -> the KERNEL, continuously, against REALITY   (cgroup memory.max)
   requests -> the SCHEDULER, once, against ARITHMETIC     (a ledger, not a reservation)

     the scheduler never looks at actual usage. it sums the REQUESTS of
     Pods already assigned and compares to Allocatable.
     => a cluster can be FULL AND IDLE simultaneously.
        the biggest source of over-provisioning there is.

   THE PAIR ALSO SETS A QUEUE POSITION (nobody writes qosClass; it is derived)
     requests == limits, every container -> Guaranteed   evicted LAST
     some requests set                   -> Burstable
     nothing set                         -> BestEffort   evicted FIRST
     so "leave the resources out" = invisible to the ledger AND first to die

   NARROWING THE CHOICE
     nodeSelector      exact match, all keys, hard filter
     nodeAffinity      required...  = the same, with In/NotIn/Exists/Gt/Lt
                       preferred... = a weighted nudge
       ...IgnoredDuringExecution: relabel the node and NOTHING MOVES.
          because spec.nodeName is written ONCE. (Act VI)
     taints/tolerations   NODE repels; POD permits. a toleration does NOT
                          attract -- it only stops you being excluded.
       NoSchedule       refuse new, leave existing
       PreferNoSchedule avoid if possible
       NoExecute        refuse new, EVICT existing
         -> every Pod silently carries not-ready/unreachable NoExecute
            tolerations with tolerationSeconds: 300. that is the ~5 minutes
            before a lost node's Pods move.
     topologySpreadConstraints  maxSkew across a topologyKey
       hostname -> spread across nodes; zone -> spread across AZs
       DoNotSchedule  = a requirement (Pending rather than clumped)
       ScheduleAnyway = a preference (gives up exactly when you need it)

   DIAGNOSING: Events is the transcript.
     Events: <none>            -> nothing LOOKED (Act VI: is the scheduler up?)
     FailedScheduling + tally  -> it looked and refused, and told you why per node
```

**Cleanup:**

```bash
kubectl label node netlab-worker disk- 2>/dev/null
kubectl get pods                                   # empty, or Terminating on its way out
kubectl describe node netlab-worker | grep -A2 Taints    # no maintenance taint
```

> **You understand this when you can** state the difference between what enforces a `limit` and what enforces a `request`, and explain how a node can be full and idle at the same time; say where `qosClass` comes from and what it decides; explain what a toleration does *not* do; name the effect that acts on already-running Pods and connect it to the five minutes before a lost node's Pods move; and read a `FailedScheduling` message as a per-node tally rather than an error, distinguishing it from `Events: <none>`.

**Which raises:** you have now written a Pod's compute claims and its placement rules, and every one of them was a value typed into the Pod itself. But the image is built once and runs in ten places — dev, staging, production — and each needs different settings and different credentials. Baking them in means rebuilding the image to change a log level, and Act I showed you what baking a secret into a layer actually costs. So where does configuration live, if not in the image and not in the spec?

---

← Prev: **[Who decides a container is working](03-probes.md)** · ↑ **[Act VII overview](README.md)** · Next: **[Configuration, and where a secret actually ends up](05-configuration.md)** →
