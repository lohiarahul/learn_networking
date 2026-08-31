# The loop that scrapes

Lesson 03 left you able to read any of these numbers, once, on demand. A single `curl` is a photograph: correct at the instant it was taken, and forgotten by the process that produced it the moment it has answered. You cannot see a trend from one photograph. Something has to ask again, on a schedule, and keep what it heard — and there is nothing clever about that something. You can build the whole shape of it in six lines, right now, with tools you already have.

> **Predict first —** the loop you are about to write samples a counter every 15 seconds, appending one row per sample to a file. Say roughly how many rows a one-minute stretch of that file holds, and how many a thirty-second stretch holds. Now say whether a computation that needs *at least two rows* to produce an answer at all behaves the same way in both stretches, or whether one of them is close to a cliff the other is not.

### Six lines, and you have built a time-series database

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act11.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

while :; do
  printf '%s ' "$(date +%s)"
  kubectl get --raw /metrics | grep '^apiserver_request_total{' \
    | grep 'resource="pods"' | grep 'verb="GET"' | grep 'code="200"' \
    | awk '{print $2}'
  sleep 15
done >> "${TMPDIR:-/tmp}/series"
```

Let it run for a minute, `Ctrl-C` it, and look at the file:

```bash
cat "${TMPDIR:-/tmp}/series"
```

```
1788071690 212
1788071706 216
1788071721 219
1788071736 224
```

**That file is a time-series database.** Not a toy one — a real one, in the sense that matters: a timestamp and a value, appended forever, and every tool built on top of Prometheus is doing a more careful version of exactly this. Subtract two rows and divide by the time between them, and you have written `rate()` by hand:

```bash
awk 'NR==1{t0=$1;v0=$2} END{print ($2-v0)/($1-t0), "req/s"}' "${TMPDIR:-/tmp}/series"
```

```
0.25 req/s
```

**212 to 216 over sixteen seconds, a quarter of a request per second.** That is not an approximation of what a monitoring system does — it is the entire computation, and everything from here to the end of the act is either a fix for something wrong with this loop, or a tool built on top of the fixed version. Nothing about the mechanism gets more sophisticated than "subtract two numbers and divide by the time between them." The four things about to break are not about the arithmetic.

### Four ways this breaks, and each one happens rather than being described

**1. Nothing found the target.** This loop worked because you typed `kubectl get --raw /metrics`, which happens to proxy through the API server and needs no address of its own. Point the same idea at a Pod directly and the crack shows immediately:

```bash
kubectl run scrapetarget --image=busybox:1.36 --restart=Never --command -- sh -c 'sleep 600'
sleep 6
kubectl get pod scrapetarget -o jsonpath='{.status.podIP}{"\n"}'
```

```
10.244.1.9
```

Hard-code that IP into a loop and it will scrape correctly for as long as the Pod does not restart — and Act V already proved a Pod IP is not a name, it is a lease. **The loop has no way to find out a target exists, changed, or is gone; a human typed the address, once, and it goes stale the moment the Pod does not.**

**2. Samples do not land on the same clock.** Your loop's `sleep 15` is not exact — the `kubectl get --raw` call itself takes time, so consecutive samples land at 15 seconds plus a small, uneven drift. That drift does not matter for one series read by itself. It matters the instant you try to combine two: a ratio of *errors* to *total requests* needs an error count and a total count from the **same instant**, and two independently-drifting loops sampling two different metrics will not agree on what "the same instant" was. **No alignment means no ratio, and an error rate is nothing but a ratio.**

**3. The file only grows.** `${TMPDIR:-/tmp}/series` has no expiry, no downsampling, no cap. Leave the loop running for a month and you have a month of 15-second samples sitting in one file, and the disk under it does not care that most of those samples were never once read.

**4. A restart makes the counter lie to `awk`, on purpose.** Lesson 03 measured a real counter — `container_cpu_usage_seconds_total` on a Pod named `burner` — go from **11.7 seconds down to 0.016** the moment the Pod was deleted and recreated. Feed that transition through the same subtraction your loop just did:

```bash
python3 -c 'print((0.016 - 11.7) / 15, "req/s")'
```

```
-0.7789333333333334 req/s
```

**A negative rate.** Not a bug in the arithmetic — a completely accurate report of what the raw numbers did. The counter went down because a new process holds a new cgroup, not because negative work happened, and your six-line loop has no way to know that. This is the whole reason `rate()` is a function with logic in it rather than a subtraction: it watches for exactly this drop and, on seeing one, assumes a reset and adds the old value back in instead of reporting a number that cannot exist.

### Prometheus is this loop, plus those four fixes, and nothing else new

Everything Prometheus's own architecture does maps onto one of the four gaps above, and every piece of the mapping is something you already own from an earlier act — which is worth checking line by line rather than taking on faith:

- **Service discovery is a watch on the API server.** Prometheus's Kubernetes SD does exactly what a controller does — Act VI's whole subject — and asks "which Pods match this selector, right now, and tell me the moment that changes," instead of a human typing an IP into a config file once.
- **A `ServiceMonitor` is a CRD.** Act VII lesson 09 taught you that a CRD is a schema, nothing more, registered with the API server. Prometheus does not read `ServiceMonitor` objects itself — the **Prometheus Operator**, a controller in exactly Act VII 08b's shape, watches them and rewrites Prometheus's actual scrape config file underneath it.
- **Alignment** is Prometheus's scrape scheduler doing what your `sleep 15` was approximating badly: every target on a job gets scraped on the same declared interval, and `rate()` is defined over a *range* rather than two arbitrary points, which is precisely so that a few milliseconds of jitter between two series does not break a ratio between them.
- **Retention** is a flag (`--storage.tsdb.retention.time`) instead of an unbounded file, with the data downsampled and compacted rather than kept as raw text forever.
- **Counter resets** are handled inside `rate()` itself — the fix you just watched an accurate subtraction fail to provide.

None of that is new material. It is four things you already own, wired together, and the wiring is the only thing Prometheus contributes.

That range-versus-two-points distinction is the answer to the top of this lesson's prediction. `rate(x[1m])` at a 15-second scrape interval has roughly four rows to work with — three gaps to compute a rate from, which is enough for `rate()` to average across and smooth out a little jitter. `rate(x[30s])` has roughly two — one gap, no averaging possible, and if that scrape happened to land a second late or a series briefly had no sample at all, **the window can hold fewer than the two points `rate()` needs to produce a number**, and it returns nothing rather than a wrong answer. "Half as many samples" undersells it: going from four rows to two is not a smoother version of the same computation, it is standing right next to the cliff where there stops being a computation to perform at all. The fix people reach for first — "just shrink the range for a faster-updating graph" — is exactly the move that walks you closer to that edge.

### The measured surprise: it pulls, and absence has no alarm

Every scrape in this lesson so far has been **you, asking the target**. That is the one design decision worth stopping on, because most monitoring systems you will meet outside this course push — the application sends its numbers somewhere. Prometheus pulls: it decides who exists, on its own schedule, from its own service-discovery list, and a target never volunteers itself.

Which means: **a target that was never discovered produces no metric, no error, and no gap in a graph.** There is nothing to be absent *from*. A panel reading a metric from a target nobody is scraping renders exactly the way a panel reads a metric from a healthy target with a value of zero — flat, and quiet, and indistinguishable by looking at it. Comparisons in a query behave the same way an unset variable behaves in code you have written before: a value compared against **nothing** is not `false`, it produces nothing, and an alert rule built on "value > threshold" over an absent series never fires, because the comparison itself never ran. That single sentence is the most expensive thing in this act to learn during an incident instead of during a lesson, and lesson 05 spends its best page on exactly this.

### Meeting the wall you already diagnosed once

Install Prometheus for real — one container, a hand-written config, no operator yet — and point it at something with actual RBAC in front of it: the kubelet's own resource metrics, the same endpoint `kubectl top` reads through metrics-server.

```bash
kubectl create serviceaccount prom-reader
kubectl create clusterrole prom-reader --resource=nodes/metrics --verb=get,list,watch --dry-run=client -o yaml \
  | kubectl apply -f -
kubectl create clusterrolebinding prom-reader --clusterrole=prom-reader --serviceaccount=default:prom-reader
TOKEN=$(kubectl create token prom-reader --duration=1h)
NODE_IP=$(kubectl get node netlab-worker -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')
docker exec netlab-control-plane cat /etc/kubernetes/pki/ca.crt > "${TMPDIR:-/tmp}/cluster-ca.crt"

cat > "${TMPDIR:-/tmp}/prometheus.yml" <<EOF
global:
  scrape_interval: 5s
scrape_configs:
  - job_name: kubelet
    scheme: https
    bearer_token: "$TOKEN"
    tls_config: {ca_file: /etc/prom/ca.crt}
    metrics_path: /metrics/resource
    static_configs: [{targets: ["$NODE_IP:10250"]}]
EOF
docker run -d --name prom --network kind \
  -v "${TMPDIR:-/tmp}/prometheus.yml":/etc/prometheus/prometheus.yml \
  -v "${TMPDIR:-/tmp}/cluster-ca.crt":/etc/prom/ca.crt \
  prom/prometheus:v3.0.1
sleep 10
docker exec prom wget -qO- http://localhost:9090/api/v1/targets \
  | python3 -c "import json,sys; [print(t['scrapeUrl'],t['health'],t.get('lastError','')) for t in json.load(sys.stdin)['data']['activeTargets']]"
```

```
https://172.19.0.3:10250/metrics/resource down tls: failed to verify certificate: x509: cannot validate certificate for 172.19.0.3 because it doesn't contain any IP SANs
```

**You have seen this exact sentence before.** Act VII lesson 10 hit it installing metrics-server, and diagnosed it in full then: the kubelet's serving certificate is self-signed, with no `subjectAltName` for the IP a scraper connects by, because this cluster never turned on `serverTLSBootstrap`. It is not a new failure mode arriving with Prometheus — it is the same certificate, the same missing SANs, and the same absent CSR-issued serving cert, met a second time from a different client. Metrics-server's fix was `--kubelet-insecure-tls`; Prometheus's own name for the identical waiver is `insecure_skip_verify`:

```bash
python3 -c "
import re
p='${TMPDIR:-/tmp}/prometheus.yml'
t=open(p).read().replace('tls_config: {ca_file: /etc/prom/ca.crt}', 'tls_config: {insecure_skip_verify: true}')
open(p,'w').write(t)
"
docker restart prom >/dev/null
sleep 15
docker exec prom wget -qO- http://localhost:9090/api/v1/targets \
  | python3 -c "import json,sys; [print(t['scrapeUrl'],t['health'],t.get('lastError','')) for t in json.load(sys.stdin)['data']['activeTargets']]"
```

```
https://172.19.0.3:10250/metrics/resource up
```

The token still matters — it is the other half of what changed, and worth confirming rather than assuming, because a scrape that "just works" after one fix is exactly how the second requirement goes unnoticed:

```bash
sed -i.bak 's/bearer_token:.*/bearer_token: ""/' "${TMPDIR:-/tmp}/prometheus.yml"
docker restart prom >/dev/null
sleep 15
docker exec prom wget -qO- http://localhost:9090/api/v1/targets \
  | python3 -c "import json,sys; [print(t['scrapeUrl'],t['health'],t.get('lastError','')) for t in json.load(sys.stdin)['data']['activeTargets']]"
```

```
https://172.19.0.3:10250/metrics/resource down server returned HTTP status 401 Unauthorized
```

**Blank the token and the kubelet refuses outright**, with no TLS involved at all — a completely different failure, from a completely different layer, that happened to be masked by the certificate error until that one was fixed. `ClusterRole`, `ClusterRoleBinding`, a token: Act IX's whole subject, arriving as the thing standing between "Prometheus" and "a number," rather than as an exercise about Pods.

<details>
<summary>Check yourself — before reading on</summary>

Your loop and Prometheus's scraper both eventually ask a kubelet the same question over the same protocol. Given that, what did switching from your hand-rolled loop to Prometheus actually change about *trust* — not about scheduling, not about storage, just trust?

Nothing changed about who is allowed to ask. Both need the same bearer token and the same TLS decision, because both are, underneath, an HTTPS client talking to the same endpoint with the same RBAC in front of it. What changed is *scale and repetition*: one client asking one kubelet by hand becomes one process asking every kubelet in the cluster, continuously, automatically rediscovering new ones — which means a credential or a certificate mistake that would show up once, to one human, in your loop's terminal now shows up identically on every target, forever, until someone reads the same targets page you just read. Prometheus does not need new trust. It needs the trust decision made once, correctly, and then it amplifies whatever you decided.

</details>

<!-- figure -->
```
   YOUR LOOP, AND WHAT PROMETHEUS ADDS -- NOTHING ELSE

   THE SIX LINES
     while :; do date +%s; scrape; sleep 15; done >> series
     two rows, subtract, divide by time -- THAT IS rate().
     measured: 212 -> 216 over 16s = 0.25 req/s.

   FOUR GAPS, EACH ONE MEASURED RATHER THAN LISTED
     1. NO SERVICE DISCOVERY .. a typed IP is a lease you froze
     2. NO ALIGNMENT .......... independent drift -> no valid ratio
     3. NO RETENTION .......... the file only grows
     4. COUNTER RESETS ........ 11.7 -> 0.016 on restart -> rate = -0.78/s
        (an ACCURATE report of a number that cannot mean what it looks like)

   THE FIX IS FOUR THINGS YOU ALREADY OWN, WIRED TOGETHER
     service discovery ... a WATCH on the API server        (Act VI)
     ServiceMonitor ....... a CRD read by a CONTROLLER       (Act VII 09, 08b)
     alignment ............ a scheduled interval + a RANGE, not two points
     counter resets ....... logic INSIDE rate(), not a subtraction

   THE DESIGN DECISION THAT COSTS MOST DURING AN INCIDENT
     Prometheus PULLS. it decides who exists.
     a target never discovered -> no metric, no error, NO GAP.
     absent != false. a comparison against NOTHING returns NOTHING.
     a panel with no data and a healthy panel at zero: LOOK IDENTICAL.

   THE WALL YOU ALREADY DIAGNOSED, MET AGAIN
     same "no IP SANs" error as Act VII's metrics-server, same cause.
     fix #1 (insecure_skip_verify) got past TLS.
     blank the bearer token -> 401, a SEPARATE layer, unmasked.
     switching to Prometheus changed SCALE, not TRUST.
```

**Cleanup:**

```bash
docker rm -f prom
kubectl delete pod scrapetarget --ignore-not-found
kubectl delete clusterrolebinding prom-reader --ignore-not-found
kubectl delete clusterrole prom-reader --ignore-not-found
kubectl delete serviceaccount prom-reader --ignore-not-found
```

> **You understand this when you can** write, from memory, the six-line loop and name what it is missing compared to Prometheus; explain why a counter reset produces a *negative* rate rather than a wrong-but-plausible one, and why that is the tell `rate()` looks for; state why "the target was never scraped" and "the target reported zero" are indistinguishable on a dashboard even though they mean opposite things about your infrastructure; and trace a Prometheus scrape of the kubelet through the same certificate failure Act VII already made you diagnose, plus the separate authorization failure it was hiding.

**Which raises:** you now have a real scrape loop, a real time series, and a query language sitting on top of it — and nobody is looking at any of it. History with nobody watching is not yet monitoring. Something has to notice on its own and say so.

---

↑ **[Act XI overview](README.md)** · Prev: **[A number a process keeps](03-a-number-a-process-keeps.md)** · Next: **[The cost of one label](04b-the-cost-of-one-label.md)** →
