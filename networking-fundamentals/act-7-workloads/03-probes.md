# Who decides a container is working

Twice now the answer has come down to what "ready" means, and both times it was a default you did not choose. A container with no probe is considered ready the moment it starts — which cannot be right for anything that opens a database connection, loads a cache, or reads config at boot.

So the question this lesson exists to answer is not "how do I write a health check." It is: **who asks, and what do they do with the answer?** Because there are two probes with nearly identical syntax, and swapping them is the most reliable way to turn a small problem into an outage. Both are about to be put in front of you, deliberately without labels on what each one costs you when it fires.

### A container you can break on demand

You need a workload whose health you control, so make the probe read a file you can delete:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
  selector: { matchLabels: { app: web } }
  template:
    metadata: { labels: { app: web } }
    spec:
      containers:
        - name: nginx
          image: nginx:1.27-alpine
          command: ["sh", "-c", "touch /tmp/ready && exec nginx -g 'daemon off;'"]
          readinessProbe:
            exec: { command: ["cat", "/tmp/ready"] }
            periodSeconds: 2
EOF
kubectl expose deployment web --port=80
kubectl wait --for=condition=Available deployment/web --timeout=90s
kubectl get pods -l app=web
```

Two Pods, `1/1 READY`. That `READY` column is not decoration — it is the probe's verdict, and you are about to change it.

The Service gives you the second half of the picture, because Act V taught you where a Service actually keeps its list of backends:

```bash
kubectl get endpointslices -l kubernetes.io/service-name=web \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"  ready="}{.conditions.ready}{"\n"}{end}'
```

Two addresses, both `ready=true`.

> **Predict first —** you are about to delete `/tmp/ready` inside **one** Pod, so its readiness probe starts failing. Predict three things: what `kubectl get pods` shows for that Pod's `STATUS`, what it shows for `RESTARTS`, and what happens to the Service's endpoint list. Be specific about `STATUS` — it is the one people get wrong.

```bash
POD=$(kubectl get pod -l app=web -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD -- rm /tmp/ready
sleep 8
kubectl get pods -l app=web
```

```
NAME                   READY   STATUS    RESTARTS   AGE
web-...-aaaaa          0/1     Running   0          2m
web-...-bbbbb          1/1     Running   0          2m
```

**`0/1`, `Running`, `RESTARTS 0`.** The container was not restarted, not killed, not marked failed. It is running perfectly happily, and the only thing that changed is a `0` where a `1` was.

Now the consequence, which is somewhere else entirely:

```bash
kubectl get endpointslices -l kubernetes.io/service-name=web \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"  ready="}{.conditions.ready}{"\n"}{end}'
```

One address is now `ready=false`. Which means — from Act V — kube-proxy has rewritten that node's rules and the Service no longer sends it traffic.

**That is the whole of readiness.** The probe failed, the kubelet wrote a condition onto the Pod, a different controller read that condition and updated the EndpointSlice, and traffic stopped. Nobody restarted anything. **A readiness failure is a request to be left alone**, and it is reversible in both directions:

```bash
kubectl exec $POD -- touch /tmp/ready
sleep 8
kubectl get pods -l app=web        # 1/1 again, still RESTARTS 0
```

### The same probe, one word different

Now change nothing but the field name:

```bash
# --type=json is a different patch from Act V's: a list of explicit operations
# against a path, rather than a fragment of the object to merge in
kubectl patch deployment web --type=json -p='[
  {"op":"remove","path":"/spec/template/spec/containers/0/readinessProbe"},
  {"op":"add","path":"/spec/template/spec/containers/0/livenessProbe",
   "value":{"exec":{"command":["cat","/tmp/ready"]},"periodSeconds":2,"failureThreshold":2}}
]'
kubectl rollout status deployment/web
```

> **Predict first —** same probe, same failing command, one word of YAML different. Before you delete the file again: what will `RESTARTS` do, and what will the endpoint list do?

```bash
POD=$(kubectl get pod -l app=web -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD -- rm /tmp/ready
sleep 15
kubectl get pods -l app=web
kubectl describe pod $POD | grep -A10 'Events:'
```

**`RESTARTS` is `1`**, and the events say the container was killed — `Liveness probe failed` followed by `Killing`. And note what the container came back as: a fresh `nginx`, whose startup command ran `touch /tmp/ready` again. **The restart fixed the symptom**, which is exactly what liveness is for and exactly why it is dangerous.

The endpoint list, meanwhile, barely flickered. There is no readiness probe now, so the Pod is considered ready whenever its container is running — including in the seconds *before* the liveness probe notices anything is wrong, and again immediately after the restart.

So, the two sentences worth memorising:

- **Readiness answers "should traffic come here?"** Failing removes you from the Service and changes nothing else. It is read by the endpoint controller.
- **Liveness answers "should this container be killed?"** Failing restarts you. It is read by the kubelet, on that node, alone.

Identical syntax. Opposite consequences. **One is a load-balancer decision, the other is a life-or-death decision**, and they are eight characters apart in a YAML file.

### The failure mode this actually causes

Here is why this is worth a whole lesson rather than a table.

The natural thing to write in a liveness probe is a check that means "my service is working" — and for most real services, working means *able to reach its database*. So people write a liveness probe that queries the database.

Now the database has a five-second blip.

Every replica's liveness probe fails at once. The kubelet on every node kills every container simultaneously. They all restart, all reconnect to a database that is already struggling, all fail their probes again during startup, and get killed again — and now you have `CrashLoopBackOff` across an entire service, caused by a five-second blip that your application would have survived by retrying.

The correct probe for "cannot reach my dependency" is **readiness**, because the correct response is to stop taking traffic until it recovers, not to die. The rule that follows:

> **A liveness probe should only check whether *this process* is wedged. If the check can fail for a reason a restart cannot fix, it does not belong in a liveness probe.**

Which is why a lot of experienced practice is to have no liveness probe at all. A crashed process is already restarted by `restartPolicy` — you saw that in lesson 01, with `crictl stop`. Liveness only earns its place for the specific case of a process that is *running but stuck*: deadlocked, spinning, holding a socket open and never answering. That is a real failure mode, and it is rarer than the number of liveness probes in the world implies.

### The third probe, and the problem it solved

One more, and it exists because of an interaction between the first two.

```bash
kubectl get deployment web -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}{"\n"}'
```

Consider an application that takes ninety seconds to start — a JVM warming up, a large cache loading. Its liveness probe fails for that whole ninety seconds, because the app genuinely is not answering yet. So the kubelet kills it at the first `failureThreshold`, and it never once finishes starting. The Pod crash-loops forever on a perfectly healthy application.

The old fix was `initialDelaySeconds` — wait 120 seconds before probing at all — and it is a bad fix for a reason worth seeing: it is a *guess*. Too low and you kill a healthy slow start; too high and a genuinely wedged container sits there unnoticed for two minutes. You are trading startup safety against detection speed with one number that has to serve both.

A **`startupProbe`** separates them. While it is failing, the liveness and readiness probes are **suspended entirely**; the moment it succeeds once, it never runs again and the other two take over:

```yaml
startupProbe:
  exec: { command: ["cat", "/tmp/ready"] }
  periodSeconds: 5
  failureThreshold: 60        # up to 5 minutes to start...
livenessProbe:
  exec: { command: ["cat", "/tmp/ready"] }
  periodSeconds: 2
  failureThreshold: 2         # ...then 4 seconds to notice a hang
```

Five minutes of patience during boot, four seconds of vigilance afterwards, and no single number compromising between them.

### The knobs, and which one is the trap

```bash
kubectl explain deployment.spec.template.spec.containers.livenessProbe \
  | grep -E 'initialDelay|periodSeconds|timeoutSeconds|failureThreshold|successThreshold'
```

Six fields matter, and their defaults are worth knowing because you inherit them by silence:

| Field | Default | What it means |
|---|---|---|
| `initialDelaySeconds` | `0` | wait this long before the first probe |
| `periodSeconds` | `10` | how often to probe |
| `timeoutSeconds` | **`1`** | how long a single probe may take |
| `failureThreshold` | `3` | consecutive failures before acting |
| `successThreshold` | `1` | consecutive successes to recover (must be 1 for liveness) |
| `terminationGracePeriodSeconds` | pod's | override just for a liveness kill |

**`timeoutSeconds: 1` is the trap.** One second, for an HTTP request to an application that is under load — which is precisely when a probe is most likely to be slow, and precisely when killing a container is least helpful. A slow probe counts as a *failed* probe, so an overloaded service starts failing liveness checks and gets restarted, which reduces capacity, which increases load. This is the second-most-common way to convert a bad afternoon into an outage, and the fix is to set `timeoutSeconds` deliberately.

Notice also the arithmetic you own now: time-to-detect is `periodSeconds × failureThreshold`, plus up to one more period of luck. Defaults give you thirty seconds — which is either far too slow or far too fast depending on what you are protecting, and either way you should have chosen it.

> **Check yourself —** An application exposes one endpoint, `/health`, which returns 200 only if it can reach both its database and its cache. A colleague wires it to both `livenessProbe` and `readinessProbe`, identically. Describe what happens during a thirty-second database outage, and what should have been configured instead.

<details>
<summary>Answer</summary>

Every replica fails both probes at the same instant, and the two failures do different damage simultaneously.

Readiness removes every Pod from the Service's endpoints. With no ready endpoints, the Service has nowhere to send traffic — from Act V, that means connections are refused rather than queued. So the outage is total for clients, even though the application is running and might have served cached responses fine.

Liveness then kills every container, on every node, at the same moment. They restart into a database that is still down, fail again during startup, and get killed again. Thirty seconds of database trouble becomes a service that is still crash-looping minutes later, because the restarts have added their own startup load and their own failures.

What should have been configured is **two different endpoints, checked by two different probes.** Readiness on the dependency check — `/ready`, stop taking traffic while the database is unreachable, come back automatically when it returns. Liveness on something that only fails if *this process* is wedged — `/livez`, or nothing at all, since a crashed process is already restarted by `restartPolicy`.

The general test to apply to any liveness probe: **if this check fails, will restarting the container fix it?** If a restart cannot fix it, restarting is not merely useless — it is actively harmful, because it removes capacity from a system that is already struggling.

</details>

<!-- figure -->

```
   ONE PROBE SYNTAX, TWO READERS, OPPOSITE CONSEQUENCES

   readinessProbe  fails
     -> kubelet writes a CONDITION on the Pod
     -> the ENDPOINT controller reads it, marks the endpoint ready=false
     -> kube-proxy rewrites the rules (Act V) and traffic stops
     STATUS stays Running. RESTARTS stays 0.
     "should traffic come here?"     = a load-balancer decision, reversible

   livenessProbe   fails
     -> the KUBELET on that node kills the container. nobody else involved.
     RESTARTS increments. it may briefly stay in the endpoints.
     "should this container be killed?" = life or death

   startupProbe    while failing, SUSPENDS the other two entirely.
                   succeeds once -> never runs again.
     replaces initialDelaySeconds, which was one number forced to trade
     startup patience against detection speed.

   THE CASCADE (why this is a lesson and not a table)
     liveness probe that checks a DEPENDENCY
       -> dependency blips -> every replica fails at once
       -> every container killed at once -> restart into a struggling
          dependency -> fail again -> CrashLoopBackOff, service-wide,
          from a 5-second blip the app would have retried through.
     the test: IF THIS CHECK FAILS, WOULD A RESTART FIX IT?
               if no, it does not belong in a liveness probe.

   DEFAULTS YOU INHERIT BY SILENCE
     no probe at all  -> ready the instant the container starts (lesson 02's bug)
     periodSeconds 10 x failureThreshold 3 = ~30s to detect
     timeoutSeconds 1 <- THE TRAP. a slow probe counts as a failed probe,
                         so load causes restarts, which cause load.
```

**Cleanup:**

```bash
kubectl delete deployment web
kubectl delete service web
```

> **You understand this when you can** say what changes and what does not when a readiness probe fails, naming the two objects and the controller between them; explain why the same probe as a liveness probe has an entirely different consequence, and who acts on it; describe the cascade a dependency-checking liveness probe causes, and state the one-question test that prevents it; and say what `startupProbe` made unnecessary and why one `initialDelaySeconds` could not serve both purposes.

**Which raises:** every probe in this lesson ran on the node the Pod was already on, and the kubelet there did the asking. But nothing has yet explained how a Pod ends up on one node rather than another. Act IV left you a question about that and you have been carrying it ever since: `resources.requests` is a claim made *before* any machine has been chosen. So who reads it, and what do they know that a kernel does not?

---

← Prev: **[Rolling updates](02-rolling-updates.md)** · ↑ **[Act VII overview](README.md)** · Next: **[The claim made before there is a machine](04-scheduling.md)** →
