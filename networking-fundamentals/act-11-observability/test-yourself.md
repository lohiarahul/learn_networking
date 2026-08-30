# Test yourself — Act XI

Fifteen questions over the four lessons built so far. Answer out loud or on paper *before* opening each answer — the point is to find out what you would have gotten wrong on a cluster, not to read a confirmation of what you already knew. Questions 1–4 are lesson 01, 5–8 are lesson 03, 9–12 are lesson 04, 13–15 are `04b`. More questions will be added here as the rest of the act ships.

---

**1.** `kubectl logs mypod` looks like a question to the API server. Which component actually reads the bytes, and what mechanism does the API server use to reach it?

<details>
<summary>Answer</summary>

The **kubelet**, on whichever node ran the Pod. The API server does not store logs anywhere — it proxies the request to the node's kubelet, resolving through the same node the way `/api/v1/nodes/<name>/proxy/...` does for `kubectl exec`. The kubelet then reads a plain file off its own disk.
</details>

**2.** You `echo` a single 70,000-character line inside a container. How many lines land in the node's `0.log`, and what tag marks all but the last of them?

<details>
<summary>Answer</summary>

Several — the container runtime's log pipe flushes in roughly 16KB chunks, so one large write becomes multiple **`P`** (partial) records followed by one final **`F`** (full) record that closes it out. `kubectl logs` knows this convention and reassembles all of them back into the single line you actually wrote; a shipper that tails the file and forwards each line verbatim will forward the fragments as separate entries instead.
</details>

**3.** Name the three separate limits governing what is on a node for a given container's logs, and say which one is *not* a retention setting.

<details>
<summary>Answer</summary>

`containerLogMaxSize` (bytes per file before rotation, measured at 10Mi), `containerLogMaxFiles` (rotated files kept before the oldest is deleted, measured at 5), and the restart-count `N` in `N.log`. The third is **not retention** — it is just the container's restart count at the moment it ran, and the kubelet garbage-collects old numbered files well before either of the other two limits would ever kick in.
</details>

**4.** A Pod has crashed and restarted four times. Roughly how many of those five containers' logs can `kubectl logs --previous` reach, and what happens the instant the Pod itself is deleted?

<details>
<summary>Answer</summary>

At most **one generation back** — the container immediately before the current one — and typically less than that, because the kubelet's garbage collector removes old dead containers (and their log files) on its own schedule, often before you get to look. The moment the Pod is deleted, its entire `/var/log/pods/<ns>_<pod>_<uid>/` directory is removed within a few seconds — every log any of its containers ever wrote, gone with the object, whether or not you had read them yet.
</details>

**5.** Read `# HELP requests_total ...` / `# TYPE requests_total counter` / `requests_total{code="200"} 42` line by line. What does each of the three lines contribute, and what tool have you already been using, unnamed, that speaks this exact format?

<details>
<summary>Answer</summary>

`HELP` is a human-readable description; `TYPE` is a machine-readable promise about how the number behaves over time; the last line is `name{label="value",...} number` — one line per unique label combination. You have been reading this format since Act VI, every time you ran `kubectl get --raw /metrics`.
</details>

**6.** A process's counter and its gauge both get read right before a crash and right after a restart. Which one's before/after values let you *detect* that a restart happened, and which one can silently look like nothing changed?

<details>
<summary>Answer</summary>

The **counter** — because it can only increase, any drop between two reads is proof of a reset, and `rate()` is built to look for exactly that and correct for it. The **gauge** has no such tell: "3 requests in flight, then 0" looks identical whether load genuinely dropped to zero or a crash destroyed everything mid-flight. There is nothing in the number itself that distinguishes the two.
</details>

**7.** A histogram has buckets `le="0.025"` at count 52 and `le="0.05"` at count 53, out of 54 total requests. Compute the 99th percentile by hand, and say whether any actual request took that long.

<details>
<summary>Answer</summary>

Target rank is `0.99 × 54 = 53.46`, which falls between the two buckets' cumulative counts (52 and 53) — so the answer sits somewhere in `(0.025, 0.05]`. Linear interpolation: `0.025 + (53.46−52)/(53−52) × (0.05−0.025) ≈ 0.061s`. **No request necessarily took exactly that long** — the number is a straight line drawn between two bucket edges on the assumption of an even spread inside the bucket, not a measurement of any one request.
</details>

**8.** `kubectl top nodes` returns a number. Trace exactly which components it passed through to get there, and say whether etcd was involved at any point.

<details>
<summary>Answer</summary>

`kubectl top` asks the API server for `metrics.k8s.io`, which is registered as an **APIService** with a real backing Service (not `Local`) — so the API server proxies the request sideways to metrics-server, which has already polled every kubelet's `/metrics/resource` on its own schedule and is answering from an in-memory cache. **etcd is never touched** — this whole path exists specifically because a CPU/memory reading is a fact about a running process, not a document worth storing.
</details>

**9.** Write, from memory, the shape of the six-line loop that turns `kubectl get --raw /metrics` into a time-series database, and name the one arithmetic operation that makes it equivalent to `rate()`.

<details>
<summary>Answer</summary>

`while :; do date +%s; <scrape a number>; sleep 15; done >> series` — appending a timestamp and a value on a schedule. The rate computation is: take two rows, subtract the values, divide by the difference in their timestamps. That subtraction-and-division *is* `rate()`, minus the four fixes lesson 04 covers.
</details>

**10.** Name the four things missing from the hand-rolled loop that Prometheus adds, and match each to the earlier act that already taught its underlying mechanism.

<details>
<summary>Answer</summary>

**Service discovery** (a watch on the API server — Act VI's reconciliation model), **alignment** (a scheduled interval plus range queries, replacing independent drift), **retention** (a flag and compaction instead of an unbounded file), and **counter-reset handling** (logic inside `rate()` that watches for a drop and adds the old value back rather than reporting an impossible negative number).
</details>

**11.** Prometheus scrapes a kubelet directly and gets `x509: cannot validate certificate for <ip> because it doesn't contain any IP SANs`. Where have you seen this exact error before, and what are the *two* separate things that have to be true before the scrape succeeds?

<details>
<summary>Answer</summary>

Act VII lesson 10 hit this installing metrics-server — the kubelet's self-signed serving certificate has no SAN for the IP a client connects by, because `serverTLSBootstrap` was never turned on. Fixing the TLS check (`insecure_skip_verify`) is only the first requirement; the second is **authorization** — a valid bearer token tied to RBAC that permits reading `nodes/metrics`. Blanking the token after fixing TLS produces a completely separate `401 Unauthorized`, from a different layer entirely.
</details>

**12.** A target was never added to any scrape config. What does a dashboard panel reading a metric from that target show, and why is that answer more dangerous than an error would be?

<details>
<summary>Answer</summary>

**Nothing distinguishable from a healthy zero.** Prometheus pulls, so a target that was never discovered produces no metric and no gap — there is nothing to be absent *from*. A comparison in an alert rule against a series that does not exist returns nothing at all, not `false`, so the alert never fires. It is more dangerous than an error because an error draws attention; a flat, quiet panel looks exactly like success.
</details>

**13.** One metric, one label, and that label takes 50,000 distinct values. How many time series does that produce, and why is "storage is cheap" the wrong objection to raise against adding it?

<details>
<summary>Answer</summary>

**50,000 — one series per unique label-value combination**, regardless of how few metric names are involved. "Storage is cheap" answers the wrong resource: the head block that holds active series lives in RAM, indexed for fast lookup, and costs roughly a couple of kilobytes of resident memory per series — a genuinely large number of series is a memory problem, not a disk problem.
</details>

**14.** You add a `labeldrop` relabel rule to remove an unbounded label and restart Prometheus. You immediately query `prometheus_tsdb_head_series`. Has it gone down?

<details>
<summary>Answer</summary>

**No, not immediately.** The relabel rule changes what gets created from the next scrape onward; it has no effect on series that already exist. The old high-cardinality series sit in memory, unwritten to, until each one has gone five minutes without a new sample (Prometheus's staleness window), and the space is only actually reclaimed at a later compaction. Fixing the config going forward and shrinking what is already stored are two different events, separated by time.
</details>

**15.** An idle API server, before a single workload has been deployed, already exposes tens of thousands of metric series. What does that number tell you about how you should think about your own cardinality budget?

<details>
<summary>Answer</summary>

That you never start at zero. The control plane's own instrumentation already spends a five-figure baseline before any application-level metric exists, so any budget or alert threshold set against "how many series is too many" has to be set relative to that floor, not relative to an imagined empty system.
</details>

---

↑ **[Act XI overview](README.md)** · Prev: **[The cost of one label](04b-the-cost-of-one-label.md)** · Next: **[Diagnose it](diagnose.md)** →
