# Choosing the number

Every replica count in this act was a number you typed. `--replicas=3`, `completions: 6`, `count: 1` in an overlay. And in the last lesson you gave a kind you invented a `/scale` endpoint, which means something can change that number without knowing what it is changing.

So close the loop: **what would it take for the cluster to pick the number itself?**

> **Predict first —** do not reach for a feature name. List what such a thing would have to be *able to do*, from first principles — there are three requirements and they are not subtle. Then, for each one, say whether this cluster can already do it. One of your three is going to be a problem, and finding out which is the first half of this lesson.

```bash
kubectl top nodes
```

```
error: Metrics API not available
```

Three requirements, then, and they are: know how loaded the workload is now, hold an opinion about how loaded it should be, and be able to write a replica count. The third you built yourself last lesson — that is `/scale`, and it works on kinds nobody had heard of. The second is a number you type.

The first is the problem, and the command above is the proof. That failure was a teaching point in lesson 04 and it is now a blocker: **nothing in this cluster measures anything.**

### The measurement has to come from somewhere

That is not an oversight in your lab; it is how Kubernetes ships. The API server stores documents, and none of those documents contain "how much CPU is this Pod using" — that is a fact about a running machine, changing every second, and Act VI's store is the wrong shape for it entirely.

So it is a separate component, and it has to be installed:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n kube-system rollout status deploy/metrics-server --timeout=90s
```

> **Predict first —** that rollout will not complete. Before reading on: the thing being installed has to ask every kubelet for its Pod statistics, and the kubelet serves those over HTTPS. Act VI walked you through this cluster's PKI in detail. Say what you think goes wrong.

```bash
kubectl -n kube-system logs deploy/metrics-server --tail=5
```

```
E0822 03:00:06.163823  1 scraper.go:149] "Failed to scrape node"
  err="Get \"https://<node-ip>:10250/metrics/resource\": tls: failed to verify
  certificate: x509: cannot validate certificate for <node-ip> because it
  doesn't contain any IP SANs" node="netlab-control-plane"
```

A **certificate verification failure** — and read the reason precisely, because it is narrower than "the certificate is wrong." It says **no IP SANs**.

Act VI taught exactly what that means. Its PKI lesson noted that a client verifying a server checks the name it asked for against the certificate's `subjectAltName` list, and marked `apiserver.crt` as a serving cert that *has* one. metrics-server is connecting to a kubelet by IP, `172.18.0.3`, and finding a certificate that lists no IP addresses at all. So the identity check fails before anything about trust chains is even reached.

And the underlying cause is the gap Act VI left open. That lesson walked you through the certificates kubeadm creates and signs — and the kubelet's *serving* certificate is not one of them. Unless a cluster turns on `serverTLSBootstrap`, each kubelet generates its own, self-signed and without meaningful SANs, rather than asking the CSR API for a properly issued one. So there are two things wrong at once: the name does not match, and there is no chain to the cluster CA to fall back on.

Which leaves two honest options: make the kubelets get real certificates through the CSR API, or tell this one client to stop checking. Every kind tutorial does the second, and it is worth being clear that it waives *both* checks, not just the one in the error message:

```bash
kubectl -n kube-system patch deploy metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl -n kube-system rollout status deploy/metrics-server --timeout=120s
sleep 30
kubectl top nodes
kubectl top pods -A | head -5
```

Numbers, at last. Note what you have added: a Deployment that scrapes every kubelet and serves the results through the API server as a *different API*, not as objects in the store. `kubectl top` is not `kubectl get`, and there is nothing in etcd to find.

### The number that has no denominator

Now the autoscaler. Make something to scale, deliberately the way most people write it first:

```bash
kubectl create deployment web --image=nginx:1.27-alpine --replicas=1
kubectl expose deployment web --port=80
cat <<'EOF' | kubectl apply -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 1
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
EOF
sleep 60
kubectl get hpa web
```

> **Predict first —** you asked it to keep CPU utilisation at 50%. The Pod is idle, so utilisation is near zero, which is well under target. Say what the `TARGETS` column shows and what you expect `REPLICAS` to do. Then look, because it is neither of the two obvious answers.

```
NAME   REFERENCE        TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
web    Deployment/web   cpu: <unknown>/50%   1         8         1          60s
```

**`<unknown>`.** Not zero, not low — *unknown*. And metrics-server is working; you read real numbers out of it thirty seconds ago. Ask why:

```bash
kubectl describe hpa web | grep -A4 Conditions
```

```
Type           Status  Reason                   Message
AbleToScale    True    SucceededGetScale        the HPA controller was able to get the target's current scale
ScalingActive  False   FailedGetResourceMetric  the HPA was unable to compute the replica count: failed to
                                                get cpu utilization: missing request for cpu in container
                                                nginx of Pod web-7b8c57c6d6-xbmcf
```

**`missing request for cpu`.** Stop and derive what that tells you about the algorithm, because it is the single most useful fact in this lesson and almost nobody knows it.

You asked for 50% *utilisation*. Utilisation is a ratio, so it needs a denominator — and the denominator is not the node's capacity, and it is not a limit. It is the container's **`requests`**. The HPA computes `actual usage ÷ requests`, and your Deployment, created by a one-liner, has no `requests` at all.

So there is no denominator, so there is no ratio, so there is nothing to compare against 50%, and the autoscaler declines to guess. It does not scale. It does not error loudly. It sits there reporting `<unknown>` forever, and the Deployment stays at one replica through any amount of load.

That is the third consequence of leaving `requests` out, and it completes the set from lesson 04. A Pod with no requests is invisible to the scheduler's arithmetic, first in line to be evicted, **and impossible to autoscale on utilisation.** All three from the same omission, and the omission is what happens by default.

Fix the cause:

```bash
kubectl set resources deployment web --requests=cpu=50m,memory=32Mi
kubectl rollout status deployment/web --timeout=90s
sleep 120     # the HPA re-reads every 15s, but metrics-server needs ~70s for a new Pod
kubectl get hpa web
```

```
NAME   REFERENCE        TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
web    Deployment/web   cpu: 0%/50%     1         8         1          3m
```

A real ratio now. And notice the shape of what you did: you did not configure the autoscaler, you gave the workload a denominator.

### Watching it decide

```bash
kubectl run load --image=busybox:1.36 --restart=Never -- \
  sh -c 'while true; do wget -q -O- http://web/ >/dev/null; done'
kubectl get hpa web -w        # Ctrl-C after a few minutes
```

Replicas climb. Read the arithmetic behind each step, because it is short enough to hold:

**`desired = ceil( current × ( actual ÷ target ) )`**

Two Pods averaging 90% against a 50% target gives `ceil(2 × 1.8) = 4`. It is proportional, not incremental — the HPA does not add one and check; it computes where it thinks it should be and jumps there, then re-evaluates on its next pass about fifteen seconds later. Which is why a load spike produces one large step rather than a staircase.

Now stop the load and watch the other direction:

```bash
kubectl delete pod load --now
kubectl get hpa web -w        # Ctrl-C once it settles
```

**It takes about five minutes to come back down**, long after the CPU is idle. Scaling up took seconds.

> **Predict first —** that asymmetry is a default somebody chose, and it is roughly two orders of magnitude. Before reading the fields: which direction is the cautious one, and what is the cost of being wrong in each direction? You have made this exact argument once already in this act.

```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300      # the default
  scaleUp:
    stabilizationWindowSeconds: 0        # the default
```

Scaling up too eagerly costs money for a few minutes. Scaling down too eagerly costs an outage the moment load returns, and the load that just went away is exactly the load most likely to come straight back. So the defaults are asymmetric in the direction where being wrong is cheaper — which is the same reasoning, and the same shape, as lesson 02's `maxSurge` rounding up while `maxUnavailable` rounds down. When you meet an asymmetric default in this subject, ask which mistake it is refusing to make.

Without that window an autoscaler oscillates: scale down, load per Pod rises, scale up, load per Pod falls, scale down. The stabilisation window is what makes a proportional controller stop hunting.

### Three things called autoscaling

They are routinely confused and they change three different fields.

```bash
kubectl get hpa web -o jsonpath='{.spec.scaleTargetRef}{"\n"}'
```

**The HPA changes `spec.replicas`** — a number in a document, through the `/scale` subresource, which is why it needs nothing but a `scaleTargetRef`. And that is the payoff of the last lesson: it never looks at what it is scaling. Point it at your `Website` kind and it works, because you defined `specReplicasPath` and that is the entire contract.

**A VerticalPodAutoscaler changes `requests`** — the denominator itself. Historically that meant replacing the Pod, and lesson 04 gives you the reason: `requests` is read once by the scheduler when placing the Pod, and the placement cannot be revisited because `spec.nodeName` is written once. Raising a request on a node that no longer has room is not a request the scheduler ever agreed to.

Recent Kubernetes can resize *some* resources in place, precisely to avoid that replacement — but only within what the current node can still satisfy, which is the same constraint stated from the other side rather than a repeal of it. Either way the important point stands: vertical and horizontal autoscaling on the same CPU metric fight, because one raises the denominator while the other multiplies the count of numerators.

**The Cluster Autoscaler changes the number of nodes**, and its input signal is the thing you have been treating purely as a diagnosis:

```bash
kubectl get hpa web -o jsonpath='{.spec.maxReplicas}{"\n"}'
```

Set `maxReplicas` above what your nodes can hold and the surplus Pods go `Pending` with `Insufficient cpu` — lesson 04's message exactly. On a cloud cluster, a component is watching for that specific state and buys a machine in response. **`Pending` is not only a symptom; it is the API between two autoscalers**, which is why an HPA whose `maxReplicas` exceeds your cluster capacity is either harmless or expensive depending entirely on whether that second component is installed.

> **Check yourself —** A team sets an HPA on CPU at 70% for a service that spends almost all its time waiting on a slow database. Load doubles, response times triple, and the HPA never scales. Nothing is misconfigured. What is wrong with the plan?

<details>
<summary>Answer</summary>

CPU is the wrong metric for that workload, and the HPA is behaving correctly.

A process blocked on a network read consumes no CPU. Traffic can double while CPU stays flat, so utilisation never approaches 70% and the autoscaler correctly concludes nothing needs to change. The queue is growing somewhere the HPA cannot see.

Worse, scaling on CPU would not have helped even if it had fired: more replicas hitting the same slow database makes the database slower. The constraint is not in the thing being scaled.

The fix in this subject is that `metrics` is a *list*, and `type: Resource` is one of several. `Pods` and `Object` metrics let an HPA target something meaningful — requests per second, or a queue depth — via an adapter that serves those the way metrics-server serves CPU. Note the shape: same HPA, same `/scale` call, different source of numerator. The autoscaler was never CPU-specific.

The habit worth taking: before choosing a target number, ask what the workload actually runs out of. CPU is the default because it is the only thing measured out of the box, not because it is usually the right answer.

</details>

<!-- figure -->

```
   WHO CHOOSES THE REPLICA COUNT

   REQUIREMENT 1: a measurement. NOT IN THE CLUSTER BY DEFAULT.
     "how much CPU right now" is a fact about a running machine,
     changing every second -- the wrong shape for Act VI's store.
     so metrics-server is a separate Deployment, scraping kubelets,
     serving a DIFFERENT API. `kubectl top` is not `kubectl get`
     and there is nothing in etcd to find.
     it fails on kind until --kubelet-insecure-tls, because the
     kubelet's SERVING cert is self-signed -- the one certificate
     kubeadm does not issue (Act VI's PKI, minus one)

   REQUIREMENT 2: a target.  REQUIREMENT 3: /scale (lesson 09)

   >>> THE HPA COMPUTES  actual / REQUESTS  <<<
     no requests => no denominator => TARGETS shows <unknown>
     forever, and it never scales. no error, no event storm.
     ScalingActive=False, "missing request for cpu"
     => the THIRD cost of omitting requests, with lesson 04's two:
        invisible to the scheduler, first evicted, unscalable.

   desired = ceil( current x (actual / target) )
     PROPORTIONAL, not incremental. one big jump, then re-evaluate
     ~15s later. hence a spike gives a step, not a staircase.

   asymmetric defaults, for the lesson-02 reason:
     scaleUp   stabilizationWindow 0s    (being wrong = money)
     scaleDown stabilizationWindow 300s  (being wrong = an outage)
     without the window a proportional controller HUNTS.

   THREE AUTOSCALERS, THREE FIELDS
     HPA      -> spec.replicas, via /scale. kind-agnostic by design.
     VPA      -> requests. cannot touch a running Pod: requests are
                 read once, and spec.nodeName is written once.
                 fights an HPA on the same metric.
     Cluster  -> the NODE COUNT, and its input signal is `Pending`.
                 so lesson 04's diagnosis is also an API between
                 two autoscalers.
```

**Cleanup:**

```bash
kubectl delete hpa web
kubectl delete deployment web
kubectl delete svc web
kubectl delete -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl get pods -A | grep -q metrics-server && echo "still there" || echo "gone"
```

**Read that last line before you run it.** Leaving metrics-server installed is harmless, and [the sixth diagnostic drill](diagnose.md) needs it — so if you are going straight on to those, skip the `delete -f`. Come back and run it afterwards: lesson 04's `kubectl top` failure is load-bearing for anyone reading this act a second time, and a lab where that command quietly works has lost the beat.

> **You understand this when you can** explain why a cluster cannot autoscale without installing something first, and why usage data does not live in the same store as objects; say which certificate in Act VI's PKI is never issued, read the `no IP SANs` error as a *name* check rather than a *trust* check, and say what `--kubelet-insecure-tls` waives beyond the error you were shown; state what the HPA divides by and derive from that why a Deployment created with a one-liner can never autoscale on utilisation, without an error ever appearing; compute a desired replica count from current, actual and target, and explain why the result is a jump rather than a step; derive why the scale-down window is long and the scale-up window is zero; and distinguish the three autoscalers by which field each one writes, including why one of them cannot act on a running Pod and why another one's input is a Pod that will not schedule.

**Which raises:** you now have the whole shape — objects describing work, loops reading them, measurements feeding some of those loops, and your own kinds where the built-in ones fall short. And in three acts of writing to this cluster, **nothing has ever once refused you on the grounds of who you are.** You created a CRD, patched a control-plane component's Deployment, read a private key off a node, and deleted a namespace, and the only objections you ever met were about arithmetic and syntax.

Two acts sit between here and that question, and this is a good moment to say plainly where the road goes rather than implying it is one step. Refusing an action on the grounds of identity needs two things this course has not built: a way to *establish* who someone is on an untrusted network, and a model for expressing what they may do. The first is cryptography — [Act VIII](../act-8-trust/README.md), which finally opens the lock Act III made you carry around unopened. The second is identity and authorization as ideas, before Kubernetes gets a vote on them. Only then does the Kubernetes answer — RBAC, ServiceAccount tokens, admission control — read as recognition rather than as four more object kinds to memorise.

Which is also the honest note to end an act on. You can now run essentially any workload on a cluster, and you have no idea how it decides to trust anybody.

---

← Prev: **[Adding a kind](09-adding-a-kind.md)** · ↑ **[Act VII overview](README.md)** · Next: **[Test yourself](test-yourself.md)** →
