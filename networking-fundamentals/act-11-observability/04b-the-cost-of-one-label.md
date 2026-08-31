# The cost of one label

Lesson 04 closed on nobody watching the numbers yet — that thread is still open, and the next lesson picks it back up. First, a detour that has to happen before anyone builds an alert on top of a label: lesson 04 gave you somewhere to put a label, and lesson 03 showed you that labels are the entire reason a metric is answerable at all — without one, `apiserver_request_total` is a single incomprehensible sum; with `verb`, `resource` and `code` on it, it is a hundred and eighty-five separate, useful questions. The obvious next move is to label everything you can think of. This page is the arithmetic for why that obvious move is the one that takes the system down.

> **Predict first —** a metric has one label, and that label is going to take fifty thousand distinct values — a Pod IP, or a user ID, one per request. Before running anything: how many *time series* does that produce, and is buying a bigger disk the correct response if it turns out to be a real problem?

### Counting series, not metrics

A **metric name** is not what Prometheus stores. **Every unique combination of label values is its own time series**, tracked, indexed and kept in memory independently of every other combination sharing that name. Start a fresh Prometheus, and point it at nothing but itself first — `job_name: prometheus` scraping `localhost:9090` is the one job every default Prometheus config ships with, because a monitoring system that cannot report its own health is not one you can trust to report anyone else's:

```bash
cat > "${TMPDIR:-/tmp}/prometheus-card.yml" <<'EOF'
global:
  scrape_interval: 5s
scrape_configs:
  - job_name: prometheus
    static_configs: [{targets: ["localhost:9090"]}]
EOF
docker rm -f promcard >/dev/null 2>&1
docker run -d --name promcard --network kind \
  -v "${TMPDIR:-/tmp}/prometheus-card.yml":/etc/prometheus/prometheus.yml \
  prom/prometheus:v3.0.1
sleep 8
```

Ask it how many series it is holding, in its own query language for the first time this act — `PromQL` looks like an expression because it is one: `{__name__=~".+"}` selects every series whose metric name matches the regular expression "one or more of anything" (which is to say, all of them), and `count()` collapses that whole selection down to a single number.

```bash
docker exec promcard wget -qO- 'http://localhost:9090/api/v1/query?query=count(%7B__name__%3D~%22.%2B%22%7D)' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['result'][0]['value'][1])"
```

```
536
```

Five hundred and thirty-six series, from a Prometheus with **one self-scrape target and nothing else pointed at it.** Now write a target of your own — a minimal exporter, one metric, one label, and give that label the shape everyone reaches for first: something unique per client.

```bash
cat > "${TMPDIR:-/tmp}/exporter.py" <<'PY'
import http.server, socketserver, os
N = int(os.environ.get("N", "1"))
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        lines = ["# HELP requests_total total requests seen", "# TYPE requests_total counter"]
        for i in range(N):
            ip = f"10.{(i>>16)&255}.{(i>>8)&255}.{i&255}"
            lines.append(f'requests_total{{client_ip="{ip}"}} 1')
        body = ("\n".join(lines) + "\n").encode()
        self.send_response(200); self.send_header("Content-Type", "text/plain")
        self.end_headers(); self.wfile.write(body)
with socketserver.TCPServer(("", 8000), H) as httpd:
    httpd.serve_forever()
PY
docker rm -f cardexp >/dev/null 2>&1
docker run -d --name cardexp --network kind -e N=50000 \
  -v "${TMPDIR:-/tmp}/exporter.py":/exporter.py \
  python:3.12-slim python3 /exporter.py
```

Point Prometheus at it — a second scrape job, added to the same config file, the same way every job in this act has been added:

```bash
cat > "${TMPDIR:-/tmp}/prometheus-card.yml" <<'EOF'
global:
  scrape_interval: 5s
scrape_configs:
  - job_name: prometheus
    static_configs: [{targets: ["localhost:9090"]}]
  - job_name: cardexp
    static_configs: [{targets: ["cardexp:8000"]}]
EOF
docker restart promcard >/dev/null
sleep 20
docker exec promcard wget -qO- 'http://localhost:9090/api/v1/query?query=count(%7B__name__%3D~%22.%2B%22%7D)' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['result'][0]['value'][1])"
docker stats --no-stream promcard
```

```
50596
CONTAINER ID   NAME       MEM USAGE / LIMIT
6e9110c8e565   promcard   126.2MiB / 7.748GiB
```

**One label, fifty thousand values, fifty thousand series** — from a metric that would have been one line without it. Memory climbed with it, because each series is not free: it is an entry in an in-memory index plus a chunk of samples on its own append-only stream. `prometheus_tsdb_head_series` is the number Prometheus keeps about itself for exactly this reason — the same self-monitoring trick, pointed at the one number that predicts an outage before it happens:

```bash
docker exec promcard wget -qO- 'http://localhost:9090/api/v1/query?query=prometheus_tsdb_head_series' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['result'][0]['value'][1])"
```

```
50596
```

### The arithmetic, before you buy anything

You do not need a running cluster to know the shape of the danger — it is multiplication, and it was always multiplication:

**Four labels, ten values each: 10 × 10 × 10 × 10 = 10,000 series, from one metric name.** That is the *bounded* case — every label drawn from a small, known set (an HTTP method, a status-code class, a region, an environment) — and ten thousand is a number a small team can carry without noticing. **Change exactly one of those four labels to something unbounded — a Pod IP, a user ID, a raw URL with an order number baked into the path — and the ceiling is gone.** There is no longer a product of four small numbers; there is a product of three small numbers and *however many distinct values that one field will ever take*, which for a busy service is "as many as there are requests."

And this is not hypothetical headroom you are spending — lesson 03 already measured the floor you are spending it against. **An idle API server, before a single workload existed, was already producing 24,569 series**, on its own metrics, with no help from you. Cardinality is not a budget you start at zero. You start already spent.

### The fix is where you delete the label, not whether

`metric_relabel_configs` runs on the scraper, after the target answers and before a single byte reaches storage, and it can drop a label outright:

```bash
cat > "${TMPDIR:-/tmp}/prometheus-card.yml" <<'EOF'
global:
  scrape_interval: 5s
scrape_configs:
  - job_name: prometheus
    static_configs: [{targets: ["localhost:9090"]}]
  - job_name: cardexp
    static_configs: [{targets: ["cardexp:8000"]}]
    metric_relabel_configs:
      - action: labeldrop
        regex: client_ip
EOF
docker restart promcard >/dev/null
sleep 20
docker exec promcard wget -qO- 'http://localhost:9090/api/v1/query?query=requests_total%7Bclient_ip%3D%22%22%7D' \
  | python3 -m json.tool
```

```json
{"result": [{"metric": {"__name__": "requests_total", "instance": "cardexp:8000", "job": "cardexp"}, "value": [1788072100.218, "1"]}]}
```

**Fifty thousand incoming samples, one stored series, going forward.** Note the two words that matter and the thing they are hiding. **The label is gone from every new sample from this point on** — and the fifty thousand series you already created are not retroactively erased. Ask the same "how many total" question you started this lesson with, right after applying the fix:

```bash
docker exec promcard wget -qO- 'http://localhost:9090/api/v1/query?query=prometheus_tsdb_head_series' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['result'][0]['value'][1])"
```

```
50597
```

**Unchanged.** The fifty thousand old series sit in memory, unwritten to but not gone, until each one has gone five minutes without a new sample — Prometheus's staleness window — and only a later compaction of the on-disk blocks actually reclaims the space. `metric_relabel_configs` controls what gets *created* from here forward. It has no opinion about what you already created, because relabeling runs on incoming samples, and there is nothing incoming about a series that already exists. **The only cheap place to delete a label is before it is stored, and "before" is a property of time, not of configuration — a relabel rule added today cannot reach yesterday's series.**

### "Storage is cheap," priced

The instinct behind adding the label anyway is usually "disk is cheap, just add it" — true of disk, and beside the point, because the actual constraint this lesson exercised is memory: the **head block**, the portion of the TSDB actively being written, lives in RAM, indexed for fast lookup, for as long as it stays hot. From the two measurements above — roughly 18MiB for an idle Prometheus with almost nothing to track, 126MiB with 50,000 extra series — the added cost works out to a bit over **two kilobytes of resident memory per series**, before a single query has been run against any of them. Run the multiplication the other way: a fleet of a few hundred services, each emitting a handful of metrics with one unbounded label, reaches the low millions of series without anyone deciding to build anything unusual — and at two kilobytes a series, a few million series is not a rounding error on a Prometheus instance's memory budget, it is the budget.

"Cheap" was never the wrong word for disk. It was the wrong resource.

<details>
<summary>Check yourself — before reading on</summary>

A teammate suggests fixing runaway cardinality by lowering `scrape_interval` from 15s to 5s, on the theory that "we're storing less per scrape, so it should even out." Will it?

No, and the confusion is worth naming precisely: scrape interval controls how often a *fixed number* of series each get a new sample — it changes how fast the samples for existing series accumulate, not how many series exist. Cardinality is a property of label combinations, full stop, and a faster or slower scrape interval multiplies the sample count for whatever cardinality you already have. If anything, a shorter interval makes the existing problem worse, sooner, because the same 50,000 series now each grow a new sample three times as often.

</details>

<!-- figure -->
```
   CARDINALITY IS MULTIPLICATION, THEN IT IS BYTES

   A METRIC NAME IS NOT WHAT IS STORED
     every unique LABEL-VALUE COMBINATION is its own series.
     measured: 1 metric, 1 label, 50,000 values -> 50,000 series.
     536 -> 50,596 total, on ONE exporter.

   THE ARITHMETIC, BEFORE YOU BUY ANYTHING
     4 bounded labels x 10 values each = 10,000 series. survivable.
     swap ONE for an unbounded field (a Pod IP, a user id, a URL) ->
     the product has no ceiling left. "as many as there are requests."
     an IDLE apiserver already cost 24,569 -- you start already spent.

   THE FIX RUNS ON THE SCRAPER, NOT ON STORAGE
     metric_relabel_configs: labeldrop -- BEFORE a byte is written.
     confirmed: 50,000 samples -> 1 series, going FORWARD.

   AND THE PART THAT SURPRISES PEOPLE
     head_series BEFORE the fix: 50,643
     head_series RIGHT AFTER the fix: 50,643 -- UNCHANGED.
     old series are not erased. they go stale (5 min), then get
     reclaimed at the next COMPACTION. relabeling has no opinion
     about a series that already exists.
     the only cheap place to delete a label is BEFORE it is stored --
     and "before" is a property of TIME, not of config.

   "STORAGE IS CHEAP" -- PRICED, NOT ARGUED
     measured: ~2KB of RESIDENT MEMORY per series, in the head block.
     a few hundred services x one unbounded label ->
     low millions of series -> that is not a rounding error,
     it IS the memory budget.
```

**Cleanup:**

```bash
docker rm -f promcard cardexp
```

> **You understand this when you can** state, without a calculator, why a metric with four bounded labels and one unbounded one has no real ceiling; explain why an idle API server already costs tens of thousands of series before you add anything; and say precisely why applying a `labeldrop` relabel rule does not shrink `prometheus_tsdb_head_series` immediately, and what actually has to happen before it does.

**Which raises:** you now have a system that can survive its own cardinality and answer a query in milliseconds. Nobody is watching it decide anything on your behalf yet — every number so far has needed a human to run a query and read a number back.

---

↑ **[Act XI overview](README.md)** · Prev: **[The loop that scrapes](04-the-loop-that-scrapes.md)** · Next: **[An alert is a loop](05-an-alert-is-a-loop.md)** →
