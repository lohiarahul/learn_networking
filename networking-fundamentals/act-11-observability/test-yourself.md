# Test yourself — Act XI

Thirty questions over all eight lessons. Answer out loud or on paper *before* opening each answer — the point is to find out what you would have gotten wrong on a cluster, not to read a confirmation of what you already knew. Questions 1–4 are lesson 01, 5–8 are lesson 02, 9–12 are lesson 03, 13–16 are lesson 04, 17–19 are `04b`, 20–23 are lesson 05, 24–26 are `05b`, 27–30 are lesson 06.

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

**5.** A DaemonSet mounts a node's `/var/log/containers` directory — and *only* that directory — then tails every `*.log` file inside it. `kubectl get pod` reports `Running` and `1/1 Ready`. How many lines does it actually ship anywhere, and why?

<details>
<summary>Answer</summary>

**Zero.** Every entry in `/var/log/containers/` is a symlink whose target is an **absolute path** into `/var/log/pods/...`. Mount only `/var/log/containers` and that absolute path still says `/var/log/pods/...` — inside the container's own filesystem, where nothing was ever mounted at that location — so every open fails with "No such file or directory." `Running`/`Ready` only means the process is alive and answering its probes; it has no opinion about whether the file descriptors it opened point at anything real.
</details>

**6.** A hand-written log shipper keeps its read offsets in an in-memory dictionary, with no checkpoint file. It restarts. What happens to a line that was already shipped once, and which failure mode does that trade away?

<details>
<summary>Answer</summary>

It gets shipped **again** — the new process has no record of where the old one stopped, so it reopens every file and starts reading from byte zero. That is **at-least-once** delivery, trading duplicate lines for the alternative, **at-most-once**, which would silently drop whatever the shipper had not yet forwarded at the moment it died. Every serious log pipeline picks the duplicates on purpose, because a missing line during an incident is worse than a repeated one.
</details>

**7.** Loki does not index the content of a log line. What, specifically, does its index hold, and what does a `|= "error"` filter actually do underneath?

<details>
<summary>Answer</summary>

Only the **label names and values** attached to a stream — in this act's own shipper, `namespace`, `pod`, `container` and an auto-added `service_name`, regardless of how many distinct messages any of them ever logged. `|= "error"` is not an index lookup at all — it is a plain **grep**, run over every byte in the compressed chunks the label selector already narrowed down to. A specific label selector makes the grep fast because it shrinks what gets scanned; a broad one makes `|=` a full scan of everything under that label.
</details>

**8.** At three Pods, `kubectl logs -l app=web --all-containers --prefix` is a perfectly good answer. Why does it stop being the right tool well before three hundred, precisely — not "it gets slow," but what specifically breaks?

<details>
<summary>Answer</summary>

It streams live from every matching kubelet through one terminal, with **nothing persisted anywhere** — close the terminal and the stream is gone, and a Pod that already crashed and lost its `--previous` generation is unreachable through this command regardless of scale, because `kubectl logs` can only ever ask a kubelet for bytes the kubelet still has. It is not that the command becomes slow; it is that it was never a copy of anything, at any scale.
</details>

**9.** Read `# HELP requests_total ...` / `# TYPE requests_total counter` / `requests_total{code="200"} 42` line by line. What does each of the three lines contribute, and what tool have you already been using, unnamed, that speaks this exact format?

<details>
<summary>Answer</summary>

`HELP` is a human-readable description; `TYPE` is a machine-readable promise about how the number behaves over time; the last line is `name{label="value",...} number` — one line per unique label combination. You have been reading this format since Act VI, every time you ran `kubectl get --raw /metrics`.
</details>

**10.** A process's counter and its gauge both get read right before a crash and right after a restart. Which one's before/after values let you *detect* that a restart happened, and which one can silently look like nothing changed?

<details>
<summary>Answer</summary>

The **counter** — because it can only increase, any drop between two reads is proof of a reset, and `rate()` is built to look for exactly that and correct for it. The **gauge** has no such tell: "3 requests in flight, then 0" looks identical whether load genuinely dropped to zero or a crash destroyed everything mid-flight. There is nothing in the number itself that distinguishes the two.
</details>

**11.** A histogram has buckets `le="0.025"` at count 52 and `le="0.05"` at count 53, out of 54 total requests. Compute the 99th percentile by hand, and say whether any actual request took that long.

<details>
<summary>Answer</summary>

Target rank is `0.99 × 54 = 53.46`, which falls between the two buckets' cumulative counts (52 and 53) — so the answer sits somewhere in `(0.025, 0.05]`. Linear interpolation: `0.025 + (53.46−52)/(53−52) × (0.05−0.025) ≈ 0.061s`. **No request necessarily took exactly that long** — the number is a straight line drawn between two bucket edges on the assumption of an even spread inside the bucket, not a measurement of any one request.
</details>

**12.** `kubectl top nodes` returns a number. Trace exactly which components it passed through to get there, and say whether etcd was involved at any point.

<details>
<summary>Answer</summary>

`kubectl top` asks the API server for `metrics.k8s.io`, which is registered as an **APIService** with a real backing Service (not `Local`) — so the API server proxies the request sideways to metrics-server, which has already polled every kubelet's `/metrics/resource` on its own schedule and is answering from an in-memory cache. **etcd is never touched** — this whole path exists specifically because a CPU/memory reading is a fact about a running process, not a document worth storing.
</details>

**13.** Write, from memory, the shape of the six-line loop that turns `kubectl get --raw /metrics` into a time-series database, and name the one arithmetic operation that makes it equivalent to `rate()`.

<details>
<summary>Answer</summary>

`while :; do date +%s; <scrape a number>; sleep 15; done >> series` — appending a timestamp and a value on a schedule. The rate computation is: take two rows, subtract the values, divide by the difference in their timestamps. That subtraction-and-division *is* `rate()`, minus the four fixes lesson 04 covers.
</details>

**14.** Name the four things missing from the hand-rolled loop that Prometheus adds, and match each to the earlier act that already taught its underlying mechanism.

<details>
<summary>Answer</summary>

**Service discovery** (a watch on the API server — Act VI's reconciliation model), **alignment** (a scheduled interval plus range queries, replacing independent drift), **retention** (a flag and compaction instead of an unbounded file), and **counter-reset handling** (logic inside `rate()` that watches for a drop and adds the old value back rather than reporting an impossible negative number).
</details>

**15.** Prometheus scrapes a kubelet directly and gets `x509: cannot validate certificate for <ip> because it doesn't contain any IP SANs`. Where have you seen this exact error before, and what are the *two* separate things that have to be true before the scrape succeeds?

<details>
<summary>Answer</summary>

Act VII lesson 10 hit this installing metrics-server — the kubelet's self-signed serving certificate has no SAN for the IP a client connects by, because `serverTLSBootstrap` was never turned on. Fixing the TLS check (`insecure_skip_verify`) is only the first requirement; the second is **authorization** — a valid bearer token tied to RBAC that permits reading `nodes/metrics`. Blanking the token after fixing TLS produces a completely separate `401 Unauthorized`, from a different layer entirely.
</details>

**16.** A target was never added to any scrape config. What does a dashboard panel reading a metric from that target show, and why is that answer more dangerous than an error would be?

<details>
<summary>Answer</summary>

**Nothing distinguishable from a healthy zero.** Prometheus pulls, so a target that was never discovered produces no metric and no gap — there is nothing to be absent *from*. A comparison in an alert rule against a series that does not exist returns nothing at all, not `false`, so the alert never fires. It is more dangerous than an error because an error draws attention; a flat, quiet panel looks exactly like success.
</details>

**17.** One metric, one label, and that label takes 50,000 distinct values. How many time series does that produce, and why is "storage is cheap" the wrong objection to raise against adding it?

<details>
<summary>Answer</summary>

**50,000 — one series per unique label-value combination**, regardless of how few metric names are involved. "Storage is cheap" answers the wrong resource: the head block that holds active series lives in RAM, indexed for fast lookup, and costs roughly a couple of kilobytes of resident memory per series — a genuinely large number of series is a memory problem, not a disk problem.
</details>

**18.** You add a `labeldrop` relabel rule to remove an unbounded label and restart Prometheus. You immediately query `prometheus_tsdb_head_series`. Has it gone down?

<details>
<summary>Answer</summary>

**No, not immediately.** The relabel rule changes what gets created from the next scrape onward; it has no effect on series that already exist. The old high-cardinality series sit in memory, unwritten to, until each one has gone five minutes without a new sample (Prometheus's staleness window), and the space is only actually reclaimed at a later compaction. Fixing the config going forward and shrinking what is already stored are two different events, separated by time.
</details>

**19.** An idle API server, before a single workload has been deployed, already exposes tens of thousands of metric series. What does that number tell you about how you should think about your own cardinality budget?

<details>
<summary>Answer</summary>

That you never start at zero. The control plane's own instrumentation already spends a five-figure baseline before any application-level metric exists, so any budget or alert threshold set against "how many series is too many" has to be set relative to that floor, not relative to an imagined empty system.
</details>

**20.** Name the three states an alerting rule moves through, and say exactly what `for:` measures.

<details>
<summary>Answer</summary>

**Inactive → pending → firing.** `for:` is a duration the rule's expression has to evaluate to a non-empty result *continuously*, with no break, before pending is allowed to become firing — a time bound on how long a symptom has to persist before it pages anyone, the same "time bound, not a guarantee" idea Act VII 08b already gave you for GitOps self-heal. Drop back below the threshold at any point before `for` elapses and the rule falls back to inactive, silently, with no notification sent.
</details>

**21.** A rule reads `expr: up{job="ghost"} == 0`, `for: 15s` — and `job="ghost"` was never scraped by anything, ever. Does the rule fire, and why or why not?

<details>
<summary>Answer</summary>

**No, and it never will**, no matter how long you wait. `up{job="ghost"}` is not `0` when nothing under that job exists to have a value — it is an **empty vector**, and an empty vector compared against `0` produces nothing too, not `true`. The rule never even reaches `pending`, because the condition was never once satisfied. `absent(up{job="ghost"})` is the fix: it asks a different question — "does at least one series matching this selector exist" — and returns a one-row vector with value `1` the moment the answer is no, which alone is enough to fire the rule, no `== 1` required.
</details>

**22.** A gauge is being served by a process that crashed three minutes ago and never restarted. What does a dashboard reading that gauge show, and what is the only reliable way to tell it apart from a healthy, current value?

<details>
<summary>Answer</summary>

**The exact same number it showed three minutes ago** — a stale value is not marked as stale by anything in the value itself. The only reliable check is a second, independent question: *when* was this last updated, not just *what* does it currently say. A frozen number and a fresh one are indistinguishable by value alone, the same lesson `kubectl top`'s polling cache already taught in a quieter form.
</details>

**23.** An availability target of 99.9% over a 30-day window permits how many minutes of downtime, exactly? And what does a 14.4× burn rate mean in terms of how fast that budget gets spent?

<details>
<summary>Answer</summary>

`30 × 24 × 60 = 43,200` minutes in the window; `0.1%` of that is **43 minutes, 12 seconds** — not a second more, if the promise was 99.9%. A burn rate of 1× spends the whole budget in exactly 30 days; **14.4× spends it in `30 ÷ 14.4 ≈ 2.08` days**, which means one hour at that rate consumes roughly `1 ÷ 50 ≈ 2%` of the entire month's allowance — turning "page someone" from a guessed number into a derived one.
</details>

**24.** Name the three parameters that appear in every single HTTP request a Grafana panel has ever made to Prometheus.

<details>
<summary>Answer</summary>

**`query`** (the PromQL expression), **`start`/`end`** (the time range), and **`step`** (how many points come back inside that range). Every axis, legend and color a dashboard renders is decoration on top of exactly this `/api/v1/query_range` response.
</details>

**25.** The same panel, over 6 hours and over 30 days, can honestly disagree about whether a two-minute outage happened. Why?

<details>
<summary>Answer</summary>

Grafana computes `step` from the panel's pixel width and the length of the time range, not from the query itself — a 30-day window forces a much wider `step` than a 6-hour one, because no panel is wide enough in pixels to plot every raw sample from a month. A two-minute blip survives inside a `step` close to the original scrape interval; the identical blip gets averaged into a `step` many times its own length once the range is wide enough, and disappears from *that specific rendering*, without the underlying data changing at all.
</details>

**26.** A dashboard's template variable is pinned to a namespace that was renamed months ago. The panel still runs, still returns success, and shows nothing. Why is that specific failure dangerous, and what is the fix?

<details>
<summary>Answer</summary>

A selector matching no series is not an error — it is an empty result, the exact same shape as lesson 05's silent-alert problem, and an empty panel renders in the same shade of grey a healthy, genuinely-quiet panel renders in. "No data" and "nothing going wrong" are, once again, the same picture. The fix is not a Grafana feature — it is checking what the variable currently resolves to before trusting that a panel would have said something if it mattered.
</details>

**27.** Write the W3C `traceparent` header format from memory. Which field is identical on every hop of one request, and which one is new every time?

<details>
<summary>Answer</summary>

`00-<32 hex trace-id>-<16 hex span-id>-01`. The **trace ID** stays identical across every service the request touches; each service mints a fresh **span ID** for its own hop before forwarding the request onward under the same trace ID.
</details>

**28.** Service A calls B calls C. B forwards the request but drops the `traceparent` header on the call to C. How many traces does your backend end up holding for this one logical request, and does either one look broken on its own?

<details>
<summary>Answer</summary>

**Two.** A and B still share a trace ID, because B received one and kept it. C, having received no header at all, cannot tell the difference between "the caller forgot to send a trace ID" and "I am the very first service this request ever touched" — so it mints a brand-new trace ID of its own. Read alone, both resulting traces look completely well-formed and complete; nothing in either one indicates that a third span used to belong to it.
</details>

**29.** What, precisely, can an eBPF datapath (or a service mesh sidecar) see about a request, and what can it never see, structurally?

<details>
<summary>Answer</summary>

It sees every packet cross a socket boundary — a request arriving at a Pod, a request leaving it — in both directions, with zero code changed. It **cannot see anything that happens inside one process** between receiving a request and issuing its own downstream call, because that gap is CPU time inside a process, not bytes on a wire, and a datapath only ever observes the wire. Mesh-only tracing is shaped exactly like the gaps in your own application code, not like the code itself.
</details>

**30.** At a 1% head sampling rate, what are the odds that the one specific slow or failed request you most want to investigate after an incident was actually kept? What does tail sampling trade to fix this, and why does that trade cost more?

<details>
<summary>Answer</summary>

**1 in 100** — head sampling decides whether to keep a trace before anyone knows how the request will turn out, so the request you most need is, 99 times out of 100, one you already discarded before the incident happened. Tail sampling fixes this by deciding *after* a trace completes instead — buffering every span until then, keeping every error and every slow request, sampling the rest lightly. It costs more because buffering means holding open, in-memory state for every trace still in flight, for as long as its slowest span takes to finish, before any keep-or-drop decision can even be made.
</details>

---

↑ **[Act XI overview](README.md)** · Prev: **[Which request was slow](06-which-request-was-slow.md)** · Next: **[Diagnose it](diagnose.md)** →
