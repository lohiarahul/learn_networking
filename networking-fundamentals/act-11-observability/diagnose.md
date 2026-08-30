# Diagnose it — Act XI

Six drills so far, covering the four lessons built to date — three more will arrive once the rest of the act ships. Act X's diagnose page found the sharpest possible framing for its own subject: *every component is healthy, every command succeeds, and the control is not doing what somebody believes.* That is also, precisely, what a monitoring failure is, so this act inherits the framing rather than inventing a new one — with one turn of the screw: here, **the thing that is wrong is the instrument you would have used to find out that something is wrong.**

This act's method, in the position where Act V has five questions and Act X has four:

1. **Is there a series at all?** Not "is it in range" — does the query return anything? Nothing is not zero and it is not false.
2. **What is the resolution of the thing I am reading, and what is shorter than it?**
3. **Who decided this target exists, and would I know if they stopped?**
4. **If this signal quietly stopped arriving, what would look different?** — Act X's question four, pointed at the monitoring instead of the control, and again the one nobody asks.

Three of the six drills below need no cluster at all — they are arithmetic over samples you can do on a train, which matters for the reason Act X said it does: it tells you which of these you can practice without a laptop.

---

## Then verify it

```bash
tools/verify-drill.sh act-11 <n> "your one-line diagnosis"
```

None of them will tell you the answer — see [`drills/README.md`](../../drills/README.md) for why the expected cause is stored as a hash rather than text.

## Bench D — a Prometheus that cannot see far enough

Drills 1 and 3 share one Prometheus, deliberately configured coarser than lesson 04's:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act11.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

cat > "${TMPDIR:-/tmp}/diag-exporter.py" <<'PY'
import http.server, socketserver, os, time
N = int(os.environ.get("N", "1"))
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        lines = ["# HELP hits_total total hits", "# TYPE hits_total counter"]
        t = int(time.time())
        for i in range(N):
            ip = f"10.{(i>>16)&255}.{(i>>8)&255}.{i&255}"
            lines.append(f'hits_total{{client_ip="{ip}"}} {t % 1000}')
        body = ("\n".join(lines) + "\n").encode()
        self.send_response(200); self.send_header("Content-Type", "text/plain")
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
with socketserver.TCPServer(("", 8000), H) as httpd:
    httpd.serve_forever()
PY
docker rm -f diag-exp >/dev/null 2>&1
docker run -d --name diag-exp --network kind -e N=1 \
  -v "${TMPDIR:-/tmp}/diag-exporter.py":/exporter.py python:3.12-slim python3 /exporter.py

cat > "${TMPDIR:-/tmp}/diag-prom.yml" <<'EOF'
global:
  scrape_interval: 60s
scrape_configs:
  - job_name: prometheus
    static_configs: [{targets: ["localhost:9090"]}]
  - job_name: diagexp
    static_configs: [{targets: ["diag-exp:8000"]}]
EOF
docker rm -f diag-prom >/dev/null 2>&1
docker run -d --name diag-prom --network kind \
  -v "${TMPDIR:-/tmp}/diag-prom.yml":/etc/prometheus/prometheus.yml prom/prometheus:v3.0.1
```

**Wait at least four minutes before running either drill.** A 60-second scrape interval needs several intervals to pass before there is enough history for either drill to mean anything — starting early is the single most common way to get a false positive on drill 1's own symptom for the wrong reason.

## Drill 1 — a panel and an alert both go quiet, and the metric plainly exists

**No repair needed here — read, run, and diagnose.** A dashboard panel and an alert rule both watch `rate(hits_total[1m])`. Both are empty. `hits_total` is not zero, not absent from `/metrics`, and the target's `up` value is `1` — `up` is a series Prometheus writes for itself, one per target, `1` if the last scrape succeeded and `0` if it did not, which is the fastest way to rule out "the target is unreachable" before looking anywhere else.

```bash
docker exec diag-prom wget -qO- 'http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22diagexp%22%7D' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['result'])"
docker exec diag-prom wget -qO- 'http://localhost:9090/api/v1/query?query=hits_total' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['result'][0]['value'])"
docker exec diag-prom wget -qO- 'http://localhost:9090/api/v1/query?query=rate(hits_total%5B1m%5D)' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['result'])"
```

**The target is up, the metric has a value, and `rate()` over it returns an empty result — not zero, nothing.** Read the scrape config before guessing at the query:

```bash
docker exec diag-prom wget -qO- 'http://localhost:9090/api/v1/status/config' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['yaml'])" | grep scrape_interval
```

**Name the relationship between that number and the window in the query, then try a window several times wider, and check that it is not merely "wider" but actually wide enough:**

```bash
docker exec diag-prom wget -qO- 'http://localhost:9090/api/v1/query?query=rate(hits_total%5B3m%5D)' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['result'])"
```

<details>
<summary>Answer</summary>

`rate()` needs **at least two samples inside the window** to compute anything — one point cannot have a slope. At a 60-second scrape interval, a `[1m]` window frequently contains only one sample, or exactly two landing right at its edges depending on alignment jitter, and Prometheus is conservative: if it cannot be confident it has two real samples spanning the window, it returns nothing rather than a guess. `[3m]` at the same interval reliably holds three or four samples, comfortably above the floor, and the same query starts returning a value.

The general rule, worth carrying past this one metric: **a range window should be at least two to three times the scrape interval**, and a dashboard built with a tighter window than that will intermittently go blank — not because anything failed, but because the arithmetic underneath the query occasionally runs out of room. This is this page's own opening question 1, made literal: there was a series the whole time, and the query returned *nothing*, which every tool in this act renders identically to *nothing wrong*.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-11 1 "why the 1-minute window came back empty"
```

## Drill 3 — queries time out, and Prometheus's own memory is climbing

**Reproduce it against Bench D**, by adding a second scrape target that emits a label with far too many values:

```bash
cat > "${TMPDIR:-/tmp}/diag-prom.yml" <<'EOF'
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: prometheus
    static_configs: [{targets: ["localhost:9090"]}]
  - job_name: diagexp
    static_configs: [{targets: ["diag-exp:8000"]}]
EOF
docker rm -f diag-exp2 >/dev/null 2>&1
docker run -d --name diag-exp2 --network kind -e N=80000 \
  -v "${TMPDIR:-/tmp}/diag-exporter.py":/exporter.py python:3.12-slim python3 /exporter.py
python3 -c "
p='${TMPDIR:-/tmp}/diag-prom.yml'
t=open(p).read()+'  - job_name: diagexp2\n    static_configs: [{targets: [\"diag-exp2:8000\"]}]\n'
open(p,'w').write(t)
"
docker restart diag-prom >/dev/null
sleep 30
docker exec diag-prom wget -qO- 'http://localhost:9090/api/v1/query?query=prometheus_tsdb_head_series' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['result'][0]['value'])"
docker stats --no-stream diag-prom
```

**You will see a head-series count in the tens of thousands and a Prometheus process consuming noticeably more memory than lesson 04b's own measurement predicted for a metric this simple.** Nobody wrote 80,000 lines of PromQL, nobody added 80,000 alerts, and no dashboard changed shape. Find the one label responsible, and fix it at the only place cheap enough to matter:

```bash
docker exec diag-prom wget -qO- 'http://localhost:9090/api/v1/query?query=count%20by%20(job)(%7B__name__%3D~%22.%2B%22%7D)' \
  | python3 -m json.tool
```

<details>
<summary>Answer</summary>

Every sample Prometheus scrapes gets `job` and `instance` labels attached automatically, named after the `job_name:` and target address in the scrape config — a fact lesson 04 never had reason to state, because there was only ever one job to look at. `count by (job)` uses that free label to split the total count per target instead of per series, which immediately isolates which scrape target is responsible — the label doing the damage never has to be found by eye. The fix is lesson 04b's own, and there is only one place it can go without re-explaining the same lesson: a `metric_relabel_configs` `labeldrop` on the offending job, applied at scrape time, before the label is ever written to a series.

```bash
python3 -c "
p='${TMPDIR:-/tmp}/diag-prom.yml'
t=open(p).read().replace(
  '  - job_name: diagexp2\n    static_configs: [{targets: [\"diag-exp2:8000\"]}]\n',
  '  - job_name: diagexp2\n    static_configs: [{targets: [\"diag-exp2:8000\"]}]\n    metric_relabel_configs:\n      - action: labeldrop\n        regex: client_ip\n')
open(p,'w').write(t)
"
docker restart diag-prom >/dev/null
```

The fix stops the *bleeding* immediately — new samples stop growing the count — and it does **not** shrink `prometheus_tsdb_head_series` on the spot, which is the exact non-instant lesson 04b measured. What it does restore, right away, is the original question the metric existed to answer: `hits_total` summed across every client is still answerable, because summing was never impossible, only slow and memory-hungry with 80,000 separate series standing in the way of doing it.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-11 3 "the field that exploded the series count"
```

**Tear down Bench D:**

```bash
docker rm -f diag-prom diag-exp diag-exp2
```

## Drill 4 — the shipper is Running and Ready, and nothing is arriving

**No bench needed beyond the cluster itself.** A team's log shipper reports healthy on every check Kubernetes has: `Running`, `Ready`, no restarts. The destination has received zero lines since it was deployed an hour ago. Build the shape of what they built, and look:

```bash
kubectl delete pod shiptest --ignore-not-found --wait=true
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: shiptest}
spec:
  nodeName: netlab-worker
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","sleep 600"]
    volumeMounts:
    - {name: varlog, mountPath: /var/log/containers}
  volumes:
  - name: varlog
    hostPath: {path: /var/log/containers}
EOF
sleep 6
kubectl exec shiptest -- sh -c 'ls /var/log/containers | wc -l'
kubectl exec shiptest -- sh -c 'cat /var/log/containers/*.log 2>&1 | head -3'
```

**The directory listing works — every filename is there. Reading any one of them fails with `No such file or directory`.** `ls` and `cat` disagree about whether the files exist, which is the tell: `ls` only has to read directory entries, and a broken symlink is still a directory entry.

<details>
<summary>Answer</summary>

Lesson 01 already named the shape: `/var/log/containers/` is a **symlink farm**, and every entry in it is an absolute path pointing into `/var/log/pods/...` — a directory this shipper never mounted. The container can see that the symlinks exist, because reading a directory's entries does not follow them, but the moment it tries to open one, the kernel resolves the link against the container's own filesystem view, finds nothing at `/var/log/pods/...`, and fails. **The shipper is healthy because nothing about its own liveness or readiness probe ever opens a log file** — it reports on itself, not on whether it is doing its job.

The fix is not "mount `/var/log/pods` as well" in isolation — the symlink's target is an *absolute path*, so the parent of both, `/var/log`, has to be mounted at the *same absolute path* inside the container for the target to resolve at all:

```bash
kubectl delete pod shiptest --wait=true
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: shiptest}
spec:
  nodeName: netlab-worker
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","sleep 600"]
    volumeMounts:
    - {name: varlog, mountPath: /var/log}
  volumes:
  - name: varlog
    hostPath: {path: /var/log}
EOF
sleep 6
kubectl exec shiptest -- sh -c 'cat /var/log/containers/*.log 2>&1 | head -1'
```

Mount path and host path matching is not a convenience here, it is the entire fix — a `hostPath` mounted anywhere else leaves every symlink dangling regardless of which directories are present, because a symlink's target is text, resolved fresh on every open, and the text does not change to match wherever you decided to mount it.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-11 4 "why the filenames were visible but unreadable"
```

**Tear down:**

```bash
kubectl delete pod shiptest --ignore-not-found
```

## Drill 6 — the crash that mattered is not in `kubectl logs`, and `--previous` is empty

**No bench beyond the cluster.** An incident: a Pod crashed three times over several minutes before anyone looked. By the time someone runs `kubectl logs --previous`, it returns nothing.

```bash
kubectl delete pod crasher2 --ignore-not-found --wait=true
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: crasher2}
spec:
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","echo boom $(date +%s); exit 1"]
EOF
until [ "$(kubectl get pod crasher2 -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null)" = "3" ]; do sleep 2; done
kubectl logs crasher2 --previous
```

```
unable to retrieve container logs for containerd://...
```

**The person on call reads that error, tries `--previous` a second time in case it was a fluke, gets the same result, and concludes the crash is unrecoverable.** They are more right than they know, and for a reason that has nothing to do with how long they took.

<details>
<summary>Answer</summary>

Lesson 01 measured the actual window: this kubelet's container garbage collector clears a dead container — log file included — often within the time it takes for **one more restart** to happen, not after some generous grace period. By restart three, generations zero and one are already gone, and `--previous` can only ever name *the* immediately-prior generation; it has no flag for "two back" and no way to reach one that has already been collected. The person on call did nothing wrong and had no faster path available — the evidence was gone before the phone rang, not before they picked it up.

There is a second door to the same fate, worth naming because it is easy to conflate with the first even though this drill's own reproduction did not go through it: `containerLogMaxSize`/`containerLogMaxFiles` (10Mi × 5, a **kubelet setting**, not a `kubectl` flag, read from `/configz` in lesson 01) rotates and deletes *within* a single long-running container's own log history, independent of restarts entirely — a container that logs heavily enough for long enough without ever crashing has the same size-and-count ceiling waiting for it. Two different limits, two different triggers, the same user-visible result if either one is ever hit — logs that used to exist and no longer do — and neither one is a bug.

**The actual fix is not a kubelet flag.** Raising the retention numbers narrows the window without closing it, and it does nothing for a node that is rebooted or replaced. The only durable answer is lesson 01's own closing line: something has to copy these bytes off the node *while the container that wrote them still exists* — which is a lesson on its own, still ahead in this act.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-11 6 "why the previous generation was already gone"
```

**Tear down:**

```bash
kubectl delete pod crasher2 --ignore-not-found
```

## Drill 7 — the latency report and the SLO disagree

**No cluster needed — this one is on paper**, and the raw numbers are the ones lesson 03 already put in front of you:

```
apiserver_request_duration_seconds_bucket{...,le="0.005"} 37
apiserver_request_duration_seconds_bucket{...,le="0.025"} 52
apiserver_request_duration_seconds_bucket{...,le="0.05"}  53
apiserver_request_duration_seconds_bucket{...,le="0.1"}   54
```

Fifty-four requests total. Your SLO says **"99% of requests under 60ms."** `histogram_quantile(0.99, ...)` against this data reports **73ms** — well past the SLO's boundary — and the on-call engineer who reads only that number pages the team for a latency regression that a second engineer, reading the raw counts, insists never happened. Settle it.

<details>
<summary>Answer</summary>

Compute the p99 by hand, the way lesson 03 taught: rank `0.99 × 54 = 53.46`, which sits between the cumulative counts at `le="0.05"` (53) and `le="0.1"` (54) — the answer is somewhere in `(0.05, 0.1]`, interpolated to `0.05 + (53.46−53)/(54−53) × 0.05 ≈ 0.073s`. That is where the reported figure comes from, and it is real arithmetic, correctly performed.

The disagreement is not a bug in either engineer's reading — it is that **the SLO boundary, 60ms, does not land on a bucket edge at all.** The nearest edges are 50ms and 100ms, and every request that took between 50ms and 60ms — genuinely inside the SLO — is, from the histogram's point of view, indistinguishable from one that took 99ms. The interpolated p99 is being asked a question the bucket boundaries were never built to answer precisely, and it answers anyway, with a number that reads as exact.

**The fix is not a bigger on-call runbook — it is changing the bucket boundaries to include 0.06 the next time this metric's config is touched**, so that a genuine SLO breach and this specific false alarm stop being the same-looking event. Until that ships, the honest statement to page on is "somewhere between 98% and 99% of requests are inside the SLO, and the histogram cannot say more precisely than that" — which is a real answer, just a smaller one than the whole-millisecond number implies.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-11 7 "why the reported p99 and the SLO could not be compared directly"
```

## Drill 8 — a ratio that is provably wrong, from a rule everyone reviewed

**No cluster needed.** Three replicas of a service, each exporting `requests_total` and `errors_total` as counters — two metric names, each producing one series per replica because `job`/`instance` are attached automatically at scrape time, the same fact drill 3 used. Dividing `rate(errors_total[5m]) / rate(requests_total[5m]))` pairs each replica's error-rate series with *its own* request-rate series (Prometheus matches vectors by their shared labels, one-to-one), giving one ratio per replica; `avg(...)` and `sum(...)` then collapse those per-replica numbers down to a single fleet-wide figure — the same collapsing `count()` did in 04b, just with a different aggregation than a plain count. A reviewed, merged alerting rule computes the fleet-wide error rate as:

```
avg(rate(errors_total[5m]) / rate(requests_total[5m]))
```

— one ratio per replica, averaged. Over one five-minute window, the per-replica rates were:

```
replica A:  errors 1/s   requests 10/s     (ratio 10%)
replica B:  errors 1/s   requests 10/s     (ratio 10%)
replica C:  errors 1/s   requests 990/s    (ratio ≈0.101%)
```

The rule reports a fleet-wide error rate of **≈6.7%**, and pages the team for a serious outage. Compute the fleet's actual error rate by hand, and say whether 6.7% is the right number to have paged on.

<details>
<summary>Answer</summary>

The rule computes one ratio *per replica* first — `10%`, `10%`, `0.101%` — and then averages those three numbers: `(10 + 10 + 0.101) / 3 ≈ 6.70%`. Every replica's ratio counts **equally in the average, regardless of how much traffic it actually carried.** Replica C served 990 of the fleet's 1,010 requests — the overwhelming majority of real traffic — and its near-clean 0.101% ratio is outvoted two-to-one by two low-traffic replicas whose ratio happens to be high only because their denominators are small.

The genuine fleet error rate sums first and divides once: `sum(errors) / sum(requests) = 3 / 1010 ≈ 0.297%` — twenty-two times smaller than what the rule reported. There was no outage; there were two replicas with negligible traffic and a coincidentally high ratio, and a formula that let them outvote the replica actually carrying the fleet.

**The general statement:** `avg(a/b)` computed per-series and then averaged is *not* the same quantity as `sum(a)/sum(b)`, except in the special case where every series carries identical weight — and production traffic almost never splits evenly. The two formulas agree only by coincidence, and the coincidence is exactly what makes the bug survive review: a reviewer checking the PromQL parses, and a staging environment where every replica happens to get similar load, will not catch a formula that only diverges once traffic gets lopsided in production.

The corrected rule is `sum(rate(errors_total[5m])) / sum(rate(requests_total[5m]))` — sum the rates across every replica *first*, and divide *once*, at the end, which weights each replica by how much traffic it actually carried rather than by how many replicas happen to exist.

</details>

**Verify it:**

```bash
tools/verify-drill.sh act-11 8 "why averaging the ratios gave the wrong fleet rate"
```

---

More drills will land here as lessons 02, 05, 05b and 06 ship.

---

↑ **[Act XI overview](README.md)** · Prev: **[Test yourself](test-yourself.md)** · Next: **[In the wild](in-the-wild.md)** →
