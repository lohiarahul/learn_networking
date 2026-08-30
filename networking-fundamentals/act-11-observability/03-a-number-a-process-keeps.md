# A number a process keeps

Lesson 01 found where a log line lives, and that keeping it costs disk and outlives nothing longer than the Pod that wrote it. Getting the bytes off the node before they vanish is a real problem, and it is not this lesson's — a later one takes it on directly. Set it aside and ask a different question about the same log line, one that no amount of careful shipping fixes: however faithfully you keep it, verbatim, forever, on infinite disk, a log line answers exactly one question. **What did it say, this one time.** It has never once told you how many, how often, or how slow — not because nobody built that feature, but because the answer to "how many" is not sitting in any single line waiting to be read. It has to be counted, and counting means throwing away which request, which user, which exact line, and keeping only a number.

That trade is the whole subject of this lesson, and the mechanism behind it has been on your screen since Act VI, unnamed.

> **Predict first —** you scrape a number every 15 seconds and the process it comes from crashes and restarts between two scrapes. Before running anything: for **(a)** a counter of total requests served, and **(b)** a gauge of requests-in-flight right now, say what each one reports on the *next* scrape after the restart, and which of the two a monitoring system can silently get wrong without anyone noticing for weeks.

### The format was already on your screen

Act VI had you run this, to check for deprecated API usage before an upgrade:

```bash
kubectl get --raw /metrics | grep '^apiserver_requested_deprecated_apis'
```

You read one line out of that response and moved on. Read the whole thing this time:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act11.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
kubectl get --raw /metrics | head -6
```

```
# HELP aggregator_discovery_aggregation_count_total [ALPHA] Counter of number of times discovery was aggregated
# TYPE aggregator_discovery_aggregation_count_total counter
aggregator_discovery_aggregation_count_total 2
# HELP aggregator_unavailable_apiservice [ALPHA] Gauge of APIServices which are marked as unavailable broken down by APIService name.
# TYPE aggregator_unavailable_apiservice gauge
aggregator_unavailable_apiservice{name="v1."} 0
```

That is the entire format. Two comment lines of metadata per name — `HELP` (what it means, for a human) and `TYPE` (what it *is*, for software) — then one line per label combination: `name{label="value",...} number`. No schema registry, no binary encoding, no RPC. It is a plain-text file, served over HTTP, that a `GET` and a `grep` can read, and the API server has been handing it to you since the first command you ran against a cluster. **This is Prometheus's exposition format**, and you have been reading it, unnamed, for five acts.

Count what is actually in there before doing anything else, because the count is this act's whole opening argument about what "keeping everything" costs even before you have decided to keep anything on purpose:

```bash
kubectl get --raw /metrics | grep -vc '^#'
```

```
24569
```

**Twenty-four and a half thousand time series, from one component, before you have deployed a single workload.** Not because anyone asked for that much — because each one of a few hundred *metric names* is multiplied out across every label combination that has actually occurred, and this API server has a lot of resources, verbs and scopes to have combinations of. Keeping raw numbers is the compression that "throw away the individual" was supposed to buy you, and the bill is already five figures. Hold onto that; it is where lesson 04b picks the thread back up, and it is why a label is never as free as it looks when you type it.

### The two shapes that never explain themselves until something restarts

Every one of those lines has a `TYPE`, and the type is a promise about what happens to the number over time — not a formatting choice. Two of the four types cover almost everything you will ever read, and the difference between them is the shape of your prediction above.

A **gauge** is a snapshot: the value right now, and nothing about history. `aggregator_unavailable_apiservice` up there is one — it can go up, it can go down, and reading it twice tells you nothing about what happened between the two reads.

A **counter** only goes up (or resets to zero — more on that in a moment). `aggregator_discovery_aggregation_count_total` is one. Watch what that restriction buys you, with a number the kubelet keeps about a process's own CPU time — a fact you can measure directly, because it comes straight from the `cpu.stat` file Act IV made you read by hand:

```bash
kubectl run burner --image=busybox:1.36 --restart=Never \
  --overrides='{"spec":{"nodeName":"netlab-worker"}}' --command -- \
  sh -c 'i=0; while [ $i -lt 60000000 ]; do i=$((i+1)); done; sleep 300'
sleep 10
kubectl get --raw "/api/v1/nodes/netlab-worker/proxy/metrics/resource" \
  | grep 'pod="burner"' | grep cpu_usage_seconds
```

`kubectl get --raw` against a **node's `proxy` subresource** — lesson 01 named this: the API server forwards the request to the kubelet itself rather than answering from etcd.

```
container_cpu_usage_seconds_total{container="burner",namespace="default",pod="burner"} 11.703316
pod_cpu_usage_seconds_total{namespace="default",pod="burner"} 11.68444
```

**11.7 seconds of CPU, spent burning a loop.** Now delete that Pod and make a new one under the same name — which is exactly what happens to a crashing container, or a rolling deploy, at 3am with nobody watching:

```bash
kubectl delete pod burner
kubectl run burner --image=busybox:1.36 --restart=Never \
  --overrides='{"spec":{"nodeName":"netlab-worker"}}' --command -- sh -c 'sleep 300'
sleep 10
kubectl get --raw "/api/v1/nodes/netlab-worker/proxy/metrics/resource" \
  | grep 'pod="burner"' | grep cpu_usage_seconds
```

```
container_cpu_usage_seconds_total{container="burner",namespace="default",pod="burner"} 0.016521
pod_cpu_usage_seconds_total{namespace="default",pod="burner"} 0
```

**The counter went backwards.** 11.7 down to nearly zero, in the same time series, with the same labels. Nothing failed, nothing lied — a new process has a new `cpu.stat`, and the counter for "CPU used by whatever is running under this name" restarted with it. A gauge of "requests in flight" would have done the same thing for a different reason: the process that was answering that question no longer exists to answer it, so the true value at the instant of the crash — however many requests were mid-flight — is simply gone, overwritten by zero, and nothing about the metric says so.

Here is the asymmetry prediction (a) and (b) were built to expose. **A counter that resets is a *visible* event** — the next value is lower than the last one, which is a fact a query can detect and correct for, because "the process must have restarted" is the only explanation for a counter going down. A **gauge has no such tell.** If a gauge said "3 requests in flight" right before the crash and "0" right after the restart, there is no way to distinguish "load dropped to zero, healthy" from "everything in flight at the moment of the crash was lost." The counter's one restriction — only ever go up — is not a limitation somebody forgot to lift. **It is the only shape from which a rate can be recovered after a gap**, because a monotonic sequence with one dip has exactly one explanation, and a sequence that can move either direction has none.

That is also the answer to the second half of the prediction: **the gauge is the one that silently lies.** A missed scrape around a genuine restart produces a counter reading that looks exactly like a reset — which downstream tooling (lesson 04's `rate()`) is built to detect and skip past — and a gauge reading that looks exactly like normal operation, indistinguishable from every other quiet minute in its history.

### A histogram, before the function that hides it

A single number per name answers "how much, right now." Latency is not one number, it is a distribution, and Kubernetes' own control plane keeps one for you: `apiserver_request_duration_seconds`. Read it raw, the way you read the exposition format above, because the raw shape is the whole lesson and the convenience function that eats it comes after.

```bash
kubectl get --raw /metrics | grep apiserver_request_duration_seconds_bucket \
  | grep 'resource="pods"' | grep 'verb="PATCH"' | grep 'subresource="status"'
```

```
...le="0.005"} 37
...le="0.025"} 52
...le="0.05"} 53
...le="0.1"} 54
...le="0.2"} 54
...le="+Inf"} 54
```

(Trimmed to the buckets that change; the label set is `component="apiserver",group="",resource="pods",scope="resource",subresource="status",verb="PATCH",version="v1"`, and the full series runs from `le="0.005"` to `le="+Inf"` in the standard buckets.)

Every kubelet on every node in your cluster is patching every Pod's status field continuously, so this series is never idle, and each `le` line is not "the count in this range" — it is **cumulative**: "the count of every request that took `le` seconds or less." 37 requests finished in 5ms; by 25ms, 52 had; by 50ms, 53; by 100ms, all 54 that existed at read time. The last bucket, `+Inf`, always equals the total request count, because every request took *some* amount of time or less than infinity.

**Compute a p99 from that by hand**, the way you would if `histogram_quantile()` did not exist, before you meet the function that pretends it is one number:

- Rank you need: `0.99 × 54 = 53.46`.
- Walk the cumulative counts: at `le=0.05`, cumulative is 53 — short of 53.46. At `le=0.1`, cumulative is 54 — past it.
- **The 99th percentile is somewhere inside the bucket `(0.05, 0.1]`**, and there is no data telling you exactly where — only that one request in that bucket separates you from the rank you want. Linear interpolation across the bucket's width is the only move left: `0.05 + (53.46 − 53) / (54 − 53) × (0.1 − 0.05) ≈ 0.073s`.

`histogram_quantile(0.99, rate(apiserver_request_duration_seconds_bucket[5m]))` computes exactly that arithmetic, on the rate of bucket increases rather than the raw cumulative counts (so it works across scrapes without recomputing everything — lesson 04 covers why rate exists at all). The number it hands back is not a measurement. **It is a straight line drawn between two bucket edges, on the assumption that latencies inside a bucket are spread evenly across it** — an assumption nobody checked and the histogram cannot check for you, because *the individual request's exact duration was never kept*. That 73ms is a latency no single one of the 54 requests necessarily experienced.

Which is the reason bucket boundaries are not a detail to skim past. If your SLO says "99% of requests under 50ms," and your buckets are `{..., 0.025, 0.05, 0.1, ...}`, then any p99 that lands between 0.05 and 0.1 is being reported as a number *inside a range your histogram cannot subdivide any further* — the honest answer is "somewhere between 5 and 10 percent slower than your bound, we cannot say more," and `histogram_quantile` will hand you a confident-looking six-decimal figure instead. Choose your bucket boundaries around the number you intend to alert on, or the report is arithmetic performed on an edge that was never measured — the same habit Act VIII's *"infeasible is a number"* was warning you about, arriving through a different door.

There is a fourth type, a **summary**, which computes quantiles *inside the process* instead of exposing buckets for you to compute them from later. It looks like a shortcut and it is a dead end for exactly one reason worth carrying: a summary's quantile is a property of *one process's* observations, and there is no way to average or combine two processes' pre-computed p99s into the p99 of both together — the underlying samples are gone. A histogram's raw buckets *can* be summed across every replica first and then have a single quantile computed over the total, which is the only version of "the p99 across the fleet" that means anything.

<details>
<summary>Check yourself — before reading on</summary>

You are told a service's dashboard reports p50 = 12ms and p99 = 40ms, both computed with `histogram_quantile` over five-minute windows. A single request that took 4 seconds is sitting in your access logs from the middle of that window. Does the dashboard's p99 being 40ms mean the 4-second request did not happen?

No. A histogram's bucket boundaries almost always include a final, wide bucket like `le="+Inf"` or `le="5"`, and a handful of outliers land in it without moving a percentile that is, by definition, about the *bulk* of the distribution. One 4-second request among a few thousand does not move the 99th percentile at all — it would need to be unusual enough to be among the top 1%, and even then it only tells you *a* slow request exists in that tail, not which one, not for which user, not why. The histogram was never going to answer "show me the slow request" — that is what lesson 01's log line does, and it is the reason this act keeps two mechanisms rather than picking a favourite.

</details>

### Three answers to "how busy is the node," and only one of them is `kubectl top`

The kubelet keeps its own set of these series, separately from the API server's, and it exposes three different endpoints rather than one — which is worth sitting with, because it means "the kubelet's metrics" is not a single thing:

| Endpoint | What it holds | Series on a fresh control-plane node |
|---|---|---|
| `/metrics/resource` | Per-pod/container CPU and memory only — the minimum `kubectl top` needs | **76** |
| `/metrics` | The kubelet's own operational metrics — request latencies, sync loop timings, volume stats | **1,759** |
| `/metrics/cadvisor` | Full per-container cgroup accounting — every counter cAdvisor can read off `cpu.stat`, `memory.stat` and friends | **2,842** |

Same node, three endpoints, a factor of thirty-seven between the smallest and the largest — the exact shape §3 of this act keeps returning to: **each one is a different answer to "what do you keep."**

```bash
NODE=netlab-control-plane
kubectl get --raw "/api/v1/nodes/$NODE/proxy/metrics/resource" | grep -vc '^#'
kubectl get --raw "/api/v1/nodes/$NODE/proxy/metrics" | grep -vc '^#'
kubectl get --raw "/api/v1/nodes/$NODE/proxy/metrics/cadvisor" | grep -vc '^#'
```

```
76
1759
2842
```

`kubectl top` reads none of these directly. Try it, and then ask where the answer actually came from — if Act VII's `metrics-server` is no longer on this cluster (its own cleanup step offered to remove it), reinstall it exactly as that lesson did before continuing:

```bash
kubectl top nodes
```

```
NAME                   CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
netlab-control-plane   164m         1%       757Mi           9%
```

That command talked to the **API server**, not to a node. `kubectl top` is a client of `metrics.k8s.io`, and that group has never been in etcd — Act VI taught the API server as a filesystem over etcd, and this is the path that breaks the analogy on purpose:

```bash
kubectl get apiservices | grep -E "v1\.apps|metrics.k8s.io"
```

```
v1.apps                   Local                        True   11m
v1beta1.metrics.k8s.io    kube-system/metrics-server   True   4m
```

**`v1.apps` says `Local`** — the API server answers it directly out of its own storage, the ordinary case. **`v1beta1.metrics.k8s.io` names an actual Service**, in `kube-system`, on port 443. That is the **aggregation layer**: the API server, on seeing a request for `metrics.k8s.io`, does not look in etcd at all — it proxies the request sideways to another Pod (metrics-server, which you already installed once, in Act VII), which polls every kubelet's `/metrics/resource` on its own schedule and answers from a cache it holds in memory. `kubectl top`'s numbers are never written anywhere durable; ask twice fast enough and you get the same cached value, ask again a scrape interval later and it may already be gone.

That explains the failure mode you have not yet had a name for: `kubectl top` returning nothing for a spike that plainly happened. metrics-server's own scrape interval has a floor — a burst shorter than it is invisible to this path by construction, not by bug, because the number you would need was never held anywhere long enough to be read.

And the endpoint's own first line, back at the very top of this lesson, was `aggregator_unavailable_apiservice` — a gauge, per `APIService` name, that goes to `1` the moment a proxy target like this one stops answering. The mechanism that makes `kubectl top` possible ships with its own dead-man's switch, sitting in the very file you have been reading the whole lesson, and nothing before this act ever pointed at it.

### One counter, and the file it came from

One last thread to close, because it is the cheapest measurement in the act. `container_cpu_usage_seconds_total` — the counter that reset when `burner` was recreated — is not synthesised by the kubelet. cAdvisor, the code inside it that produces `/metrics/cadvisor`, is a program whose entire job is **reading a cgroup file and printing what it says as a metric line**:

The cgroup path is named by container ID, not by Pod name, so resolve that first — Act VI already made you read a `containerID` field off a Pod's status more than once:

```bash
CID=$(kubectl get pod burner -o jsonpath='{.status.containerStatuses[0].containerID}' | sed 's#.*//##')
docker exec netlab-worker sh -c "find /sys/fs/cgroup -iname 'cri-containerd-${CID}.scope' -exec cat {}/cpu.stat \;" | head -3
```

```
usage_usec 7729379
user_usec 7719381
system_usec 9997
```

`usage_usec` in microseconds, divided by a million, is the same number `container_cpu_usage_seconds_total` reports in seconds — a file Act IV made you read with your own eyes, wearing a `# HELP` line and an HTTP response. **A metric is a file a process keeps about itself, exposed as a file you `GET`.** Nothing in this lesson has been a new fact about the kernel; every number in it was already sitting somewhere you had already been shown, and the only thing this lesson added was the vocabulary for reading many of them fast, without a `cat` per file, per node, per container.

```
<!-- figure -->
   FOUR NUMBERS, FOUR DIFFERENT LIES A GAP TELLS

   THE FORMAT (unnamed since Act VI)
     # HELP name what it means      name{label="v",...} value
     # TYPE name counter|gauge|histogram|summary
     one plain-text HTTP response. 24,569 lines on an IDLE API server.

   COUNTER vs GAUGE -- what a missed scrape hides
     COUNTER: only up (or reset to 0). A dip IS the restart --
              visible, and rate() can correct for it.
     GAUGE:   any direction. A crash mid-flight and "load went
              to zero" look IDENTICAL. No tell. Ever.
     measured: burner's CPU counter went 11.7s -> 0.016s on
     delete+recreate -- a NEW cgroup, not a lie.

   HISTOGRAM -- cumulative buckets, read before the function
     le="0.05"->53, le="0.1"->54 (of 54 total)
     p99 rank = 0.99*54 = 53.46 -> falls inside (0.05, 0.1]
     LINEAR INTERPOLATION only. histogram_quantile() computes
     this same guess. The number is a latency NO REQUEST HAD.
     bucket edges not on your SLO boundary = arithmetic on air.

   SUMMARY -- computed too early to be combined later
     per-process quantile. cannot be averaged across replicas.
     the samples that made it are already gone.

   THREE KUBELET ENDPOINTS, x37 APART, SAME NODE
     /metrics/resource   76    <- kubectl top's whole diet
     /metrics          1,759   kubelet's own operations
     /metrics/cadvisor 2,842   full per-cgroup accounting

   kubectl top READS NONE OF THEM DIRECTLY
     v1.apps                 -> Local        (etcd, Act VI's model)
     v1beta1.metrics.k8s.io  -> a SERVICE     (the AGGREGATION LAYER)
     API server PROXIES SIDEWAYS. metrics.k8s.io was NEVER in etcd.
     cached in metrics-server's memory. ask twice fast: same number.
     a spike shorter than the scrape interval: INVISIBLE, by design.
     its own health gauge sits at the top of THIS FILE:
       aggregator_unavailable_apiservice{name=...} -- watch it.

   AND UNDER ALL OF IT
     a metric is a file a process keeps about itself,
     exposed as a file you GET. cpu.stat, read out loud.
```

**Cleanup:**

```bash
kubectl delete pod burner --ignore-not-found
```

> **You understand this when you can** name the three-line shape (`HELP`, `TYPE`, and the data line) that answers "what is the exposition format," explain why a counter's ability to only increase is what makes a gap in scraping recoverable and a gauge's is not, hand-compute a percentile from raw histogram buckets and say in your own words why the number `histogram_quantile()` returns may be a duration no request actually had, and trace `kubectl top`'s answer from the API server through the aggregation layer to a cache in metrics-server's memory rather than to etcd.

**Which raises:** a `curl` of any of these endpoints is one instant, a single photograph of numbers that are already stale by the time you read them. You cannot see a trend from one read, and the moment you have finished computing anything from the response, the process behind it has moved on and forgotten it ever told you. Something has to ask again, on a schedule, and keep what it heard.

---

↑ **[Act XI overview](README.md)** · Prev: **[Nothing here remembers](01-nothing-here-remembers.md)** · Next: **[The loop that scrapes](04-the-loop-that-scrapes.md)** →
