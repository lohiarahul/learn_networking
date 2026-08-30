# Plan — Act XI: knowing before someone tells you (Stage 7.8, observability)

*Written 2026-08-30, as the detailed design for Phase 2 of
[`PLATFORM-DEPTH-PLAN.md`](PLATFORM-DEPTH-PLAN.md). Every number below was measured against a live
`kindest/node:v1.37.0` cluster and this repo's own files — coverage counts by `grep -rIl` over
`networking-fundamentals/`, `exam-prep/`, `reference/` and `drills/`; word counts by
[`tools/remeasure.py`](tools/remeasure.py) and `wc -w`. Where a lesson beat depends on a command's real
output, that output is quoted here from the run, not paraphrased from memory.*

> **Status: proposal.** Nothing in this document is shipped. The one thing it is *not* allowed to do is
> assert a lab that has not been run — §9 is the list of things that must be verified before a word of
> lesson prose is written, and it is ordered by risk on purpose.

---

## 1. The wall, measured

Phase 2's one-line justification in the depth plan is *"how do I know before someone tells me?"* That
is the right question and it is not yet earned, because the honest form of it is sharper and it is a
**defect the course can be shown to have**:

Every diagnostic method this course teaches starts after the phone rings, and every instrument it hands
you is present-tense.

| Method | Where | What it requires |
|---|---|---|
| The five-question network walk | [Act V 08](networking-fundamentals/act-5-kubernetes/08-debugging.md) | the path is failing **right now** |
| The dependency descent | [Act VI 08](networking-fundamentals/act-6-control-plane/08-when-the-control-plane-breaks.md) | the component is down **right now** |
| Which loop read which field | [Act VII](networking-fundamentals/act-7-workloads/diagnose.md) | the object is wrong **right now** |
| The four questions of a control | [Act X](networking-fundamentals/act-10-cluster-security/diagnose.md) | the control is misconfigured **right now** |

So the wall is not "you have no dashboards". It is: **ask this course "when did it start?" and every
tool it gave you is silent.** That is measurable, and the reader can measure it in the first three
commands of lesson 01:

- `kubectl get events` — the API server's `--event-ttl` is **not set** in kind's own manifest
  (`grep -c event-ttl /etc/kubernetes/manifests/kube-apiserver.yaml` → `0`), so the default one hour
  applies. An incident from this morning left no events.
- `kubectl logs` on a Pod that has restarted twice — `--previous` reaches one generation back, and no
  further.
- `kubectl top` — no `--since`, no history, and the numbers come from a cache with a resolution.
- `kubectl delete pod` and then `kubectl logs` — the logs are gone, and §5 shows exactly which
  directory went with them.

**The act's carried question**, in Act X's idiom (*"at what moment does this refuse, what did it know
then?"*):

> **What did this system write down before anyone asked — what did it therefore throw away, and what
> did keeping it cost?**

---

## 2. Where the act goes, and why after Act X

Stage 7.8 sits inside Stage 7 on the map, which invites the objection that observability belongs after
Act VII. **Act order has never been stage order in this repo**, and the precedent is not marginal:

| Act | Stage | Shipped after |
|---|---|---|
| VIII — trust | 4 | Act VII (stage 7.2–7.7) |
| IX — identity | 5 | Act VIII |
| X — cluster security | 7.5 | Act IX |

Act X is already a Stage 7 act shipped two acts after the Stage 4 material it depends on. So Act XI at
Stage 7.8, shipped after Act X, is the existing pattern rather than an exception to it — and there is a
positive reason to want it there rather than at VII+1:

**Act X lesson 10 built the only *record* in the course.** Its `AFTER` column — "the control that
refuses nothing and writes it down" — is the audit log, and the reader has already met the idea that a
system's memory is a design decision with a cost. But an audit log records **authorised changes**, and
nothing in eleven acts records **experience**. A user got a 502 for eleven minutes and every mechanism
in this repo would have shrugged. Act XI is the same column, pointed at health instead of abuse — which
makes its opening recognition rather than instruction, exactly the move Phase 1 used to place the
runtime peel *after* the by-hand work.

**Cost of the placement, and it is real:** Act X lesson 11 currently closes the built course with a
bridge to Stage 8 (AWS). That paragraph becomes wrong the day Act XI exists. It is a small, honest
edit — Stage 8 is unbuilt, so the bridge points at roadmap either way — but it is a **required** one,
listed in §10, and it must not be forgotten the way Act V lesson 02's phantom citation was (found and
fixed in Phase 1, having gone unnoticed since it was written).

- **Directory:** `networking-fundamentals/act-11-observability/`
- **Title:** *Act XI — Knowing before someone tells you*

---

## 3. The idea that holds the act together

Every act in this repo has one. Act VIII: four promises and the hole each one leaves. Act X: five
moments, and the earlier you decide the less you know. Act XI's has to be equally load-bearing, and the
industry's own framing — "the three pillars: metrics, logs, traces" — is exactly the taxonomy this repo
declines, because it groups by product boundary and explains nothing.

The reframe that makes it a mechanism:

**Metrics, logs and traces are not three technologies. They are three different answers to one
question: what do you keep, when you cannot keep everything?** Each one is a lossy compression, chosen
before the incident. The incident decides whether you chose right, and by then the choice is a
historical fact.

```
   THE QUESTION IT ANSWERS        WHAT IT KEEPS          WHAT IT THREW AWAY         WHERE
   ---------------------------------------------------------------------------------------
   "what did it actually say?"    every line, verbatim   nothing -- and that is     01, 02
     a LOG LINE                                          the entire bill

   "how much, how often,          the SHAPE over time    which request. which      03, 04
    how slow?"                                            user. which line.
     a COUNTER + a SCRAPE

   "is it wrong NOW, and who      one boolean, over      everything the query      05, 05b
    do I wake?"                    a window               did not think to ask
     a RULE ON A LOOP

   "which of the twelve was       the CAUSAL EDGES       almost all of it, on      06
    slow?"                                               purpose, by sampling
     a SPAN WITH A PARENT

   ---------------------------------------------------------------------------------------
   keeps everything, fits nothing ------> keeps almost nothing, answers one question well
```

The trade runs in one direction and never turns around, which is why the act reads left to right: each
mechanism's *cost* is what motivates the next one, and each one's *blindness* is what motivates the one
after that.

And the second claim, which is the act's version of Act VIII's *"infeasible is a number"*:

**Every one of these costs is arithmetic, and you can do it before you buy anything.** Measured on the
probe cluster, before a single component was installed:

| Measurement | Value | Command |
|---|---|---|
| Series lines from one **idle** API server | **28,741** | `kubectl get --raw /metrics \| grep -vc '^#'` |
| …of which one histogram's buckets | **3,576** | `grep -c apiserver_request_duration_seconds_bucket` |
| Kubelet `/metrics/resource` (what `kubectl top` reads) | **76** | node proxy |
| Kubelet `/metrics` | **1,774** | node proxy |
| Kubelet `/metrics/cadvisor` | **2,848** | node proxy |
| Container log retention, per container | **10Mi × 5 files** | `containerLogMaxSize`, `containerLogMaxFiles` from `/configz` |

Three endpoints on one component, differing by a factor of thirty-seven, each a different answer to
"what do you keep". That table *is* the act, and it needs nothing installed to produce.

---

## 4. What this act declines, and why — recorded so the question does not return

The failure mode for an observability act is that it becomes a product tour. Every decline below has a
mechanism-shaped replacement, and the pattern is the one the depth plan already used for ArgoCD.

| Named | Decision | Why |
|---|---|---|
| **`kube-prometheus-stack` as the teaching vehicle** | **Decline as entry, keep as exit.** | Installing it first hides every mechanism the act exists to teach. It appears **once, at the end**, as recognition — and it closes a real dangling thread: [Act VII 08c](networking-fundamentals/act-7-workloads/08c-when-the-chart-is-not-yours.md) had the reader read that chart's `charts/crds/crds/` directory and count **ten CRDs it never opened.** Act XI is where those ten stop being a filesystem fact. |
| **A Grafana dashboard-building tutorial** | **Decline.** | A GUI walkthrough ages in months and teaches nothing transferable. `05b` teaches `/api/v1/query_range` by hand, then shows that the panel *is* that JSON — mechanism before tool, and the panel becomes readable rather than memorised. |
| **A Jaeger / Tempo install** | **Decline.** | Installing a trace backend teaches storage. Lesson 06 teaches the `traceparent` header and the sampling arithmetic, which is the whole transferable idea. |
| **The OpenTelemetry Collector's pipeline config** | **Decline as a tour, keep as one paragraph.** | It is a config language over a real contribution: OTLP is a *wire format*, and the fight it ended was n×m adapters. State that; do not walk the YAML. |
| **An SRE-book SLO chapter** | **Decline as philosophy, keep as arithmetic.** | The error budget earns its place at exactly one point: it is where an alert threshold stops being typed and starts being *derived*. That is a mechanism, it belongs inside lesson 05, and it is one page of arithmetic. |
| **eBPF-based observability (Pixie)** | **Decline; already partly owned.** | [Act V 05](networking-fundamentals/act-5-kubernetes/05-cni.md) and [Act X 09](networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md) already teach **Hubble** — flow observability with no application change. An `in-the-wild` one-liner, cross-linked. |
| **Datadog / New Relic / Honeycomb** | **`in-the-wild` one-liners.** | Vendor comparison is not mechanism, and the mechanism is agent + OTLP + somebody else's TSDB. |
| **Loki, Prometheus, Alertmanager, Grafana** | **KEEP — one container each, hand-written config.** | Each is kept for exactly one idea: Loki indexes *labels, not lines*; Prometheus is the loop the reader wrote, plus four fixes; Alertmanager's grouping is the label model again; Grafana is `query_range` with axes. No Helm, no operator, until the recognition beat at the end. |

**And the decline that matters most to state out loud: this act closes no exam gap.** §8 gives the
accounting. An act that is honest about this is following Act X lesson 11's own precedent — *"and why
none of it is on an exam"* — and the alternative is worse: a reader with a CKA date three weeks out
spending 40,000 words on material neither curriculum examines, because the repo implied they should.

---

## 5. Four River repairs this act closes — the strongest argument for building it

Phase 1's highest-value finding was not new content, it was that `runc` and `crictl` were **used 159
times and never introduced**. The same audit over observability finds four more of exactly that shape.
Each is measured.

**5.1 The aggregation layer: zero hits, and `kubectl top` cannot work without it.**
`APIService`, `apiregistration`, `aggregation layer` — **0 files** across the whole repo.
Yet [Act VII 10](networking-fundamentals/act-7-workloads/10-choosing-the-number.md) installs
metrics-server and runs `kubectl top`, which works *only* because `v1beta1.metrics.k8s.io` is
registered as an aggregated API and the API server proxies to another Service. Act VI taught the API
server as a filesystem over etcd; `kubectl top` reads a path that **is not in etcd at all**, and nothing
says so. Lesson 03 closes it — and the evidence is already in the first ten lines of the file the reader
will be reading, which is the kind of coincidence worth building a beat on:

```
# HELP aggregator_unavailable_apiservice [ALPHA] Gauge of APIServices which are marked as unavailable
# TYPE aggregator_unavailable_apiservice gauge
aggregator_unavailable_apiservice{name="v1.apps"} 0
```

**5.2 `/var/log/pods`: zero hits, under a CKA bullet marked "covered".**
`/var/log/pods`, `/var/log/containers`, `container-log-max` — **0 files.** The CKA map marks *"Manage
and evaluate container output streams"* as ✅ covered, taught through `kubectl logs` flags. But the
course has never once read the file underneath, which is a **mechanism-before-tool** violation in the
one domain where the exam has a bullet. Verified on the probe cluster:

```
/var/log/pods/kube-system_kube-proxy-2bbr2_07dcc401-d565-4420-b2bf-626491213e98/kube-proxy/0.log
/var/log/containers/coredns-…_kube-system_coredns-04e0d5c0….log -> /var/log/pods/…/coredns/0.log
```

Two paths, two different identifiers — the pod directory is named by **Pod UID**, the symlink by
**container ID** — and the log line format is the CRI one:

```
2026-08-30T05:24:33.518077388Z stderr F I0830 05:24:33.517982  1 serving.go:411] Generated self-signed cert
```

`<RFC3339Nano> <stream> <F|P> <line>`. That `F` is `full`; a line over the runtime's chunk size arrives
as several `P` records. **`kubectl logs` reassembles them and a hand-rolled `tail -F` shipper does
not** — which is drill 5, and it is a real production bug rather than an invented one.

**5.3 The Pod UID names two things, and the course has taught one of them.**
Act IV taught cgroups. The probe cluster shows kube-proxy's cgroup slice as
`kubelet-kubepods-besteffort-pod07dcc401_d565_4420_b2bf_626491213e98.slice` and its log directory as
`kube-system_kube-proxy-2bbr2_07dcc401-d565-4420-b2bf-626491213e98`. **Same UID, underscores for
dashes.** So: the Pod UID is the only name the *node* uses for a Pod — it names the cgroup and it names
the log directory — and it is the name no object you routinely look at shows you. One measurement,
Act IV and Act XI joined, and it is free.

**5.4 The exposition format: zero hits, already read.**
[Act VI 06](networking-fundamentals/act-6-control-plane/06-upgrades-and-version-skew.md) has the reader
run `kubectl get --raw /metrics | grep '^apiserver_requested_deprecated_apis'` — a Prometheus exposition
response, parsed with `grep`, format never named. Lesson 03 opens by going back to that exact command
and reading the whole file. A seed that was planted for another purpose paying off two acts later is
this repo's favourite structure; here it costs nothing because it already happened.

**5.5 One more, smaller: `cAdvisor` is a program that reads cgroup files.**
`container_cpu_usage_seconds_total{container="etcd",…} 28.981676 1788068549113` — a counter, in core
seconds, with an explicit exposition-format timestamp, and its source is the `cpu.stat` file Act IV made
the reader read by hand. The creed lands again without being announced: **a metric is a file a process
keeps about itself, exposed as a file you `GET`.**

---

## 6. The lessons

Eight teaching files: six numbered, two `b` pages, following the act's own convention (`01b`, `02b`,
`08b`, `08c` all exist elsewhere in the course). Each subsection states the wall it inherits, the
mechanism, the rival it must beat, the prediction the reader commits to, the measured surprise, and the
wall it leaves for the next lesson. **Publish in this order; write in §9's order.**

### 01 — `01-nothing-here-remembers.md` (~3,600 words)

**Wall.** §1's table: four methods, all present-tense. The reader has just finished Act X, which built
the only record in the course, and it records authorised changes.

**Mechanism.** Where the log bytes are. `kubectl logs` is an API call the kubelet answers by reading a
file; find the file. `/var/log/pods/<ns>_<pod>_<uid>/<container>/N.log`, the `/var/log/containers`
symlink farm, the CRI line format with its `F`/`P` tag, and rotation from `/configz` rather than from
documentation (`containerLogMaxSize: 10Mi`, `containerLogMaxFiles: 5`). Then §5.3's cgroup/log-dir UID
identity, which is where Act IV walks back in.

**Rival.** `kubectl logs --previous` (one generation) and `kubectl logs -f > file.log` in a terminal
somebody will close.

**Predict first.** *"A Pod has restarted three times and you need the first crash. Before running
anything: say which of the three you can still read, and where the bytes for the others went."*

**The measured surprise.** The `N` in `N.log` is the restart count, the directory is named by a UID
nobody wrote down, and the whole directory is removed when the Pod object is — so **log retention is
bounded by Pod lifetime, which is bounded by a ReplicaSet's opinion.** Delete the Pod, then look.

**Leaves open.** The only copy is on a node, in a directory that will be deleted. Something has to copy
it off *while it exists* — and that something is a Pod that reads the node's filesystem, which the
reader already knows how to write.

**New tools:** none. (`/configz` as a kubelet endpoint is new *usage* of `kubectl get --raw`.)
**Exam value:** real. Makes a ✅ bullet mechanical, and gives the answer for "the API server cannot
answer and I need the log", which is CKA troubleshooting shaped.

### 02 — `02-copying-it-off-the-node.md` (~3,800 words)

**Wall.** Lesson 01's.

**Mechanism.** The reader writes a log shipper. A DaemonSet, a `hostPath` on `/var/log/pods`, and
`tail -F` — twelve lines, and the entire category (Fluent Bit, Promtail, Vector) becomes recognition.
Then the three walls those twelve lines expose, each measured rather than asserted:

1. **Which Pod said this?** The filename is the only metadata there is, so enrichment is a call to the
   API server — which means the shipper needs a ServiceAccount and RBAC. Act IX walks in.
2. **The shipper restarted. Where had it got to?** A checkpoint file, and then at-least-once versus
   at-most-once — which is Act III's reliability argument, one layer up, and the honest answer is that
   log pipelines pick at-least-once and you will see duplicate lines.
3. **It does not fit.** Which is the act's spine and the reason the destination has to index something.

Then Loki, kept for exactly one design decision: **it indexes the labels and not the line**, so
`|= "error"` is a grep over a fetched chunk rather than an index lookup. Earned against Elasticsearch,
which indexes everything — fast query, expensive write, and the cardinality problem arrives early.

**Rival.** `kubectl logs -l app=web --all-containers --prefix`, which is genuinely the right answer at
three Pods and unusable at three hundred. Show both.

**Predict first.** *"Your shipper mounts `/var/log/pods` and tails `/var/log/containers/*.log`. It will
report Running and Ready. Predict how many lines it ships."* (Zero — the symlinks point outside the
mount. This is drill 4, seeded here.)

**Leaves open.** You now keep every line and the bill scales with traffic. Nobody can answer "how many
requests per second" without reading all of them.

**New tools:** Loki, `logcli`. **Exam value:** none. Say so.

### 03 — `03-a-number-a-process-keeps.md` (~4,200 words)

**Wall.** Lesson 02's: a log keeps the individual and cannot cheaply answer a question about the shape.

**Mechanism, and it needs nothing installed.** Go back to Act VI lesson 06's own command and read the
whole response. `# HELP`, `# TYPE`, `name{label="v"} value [timestamp]`. It is a text file over HTTP.
Then the four types derived from problems rather than listed:

- **Counter vs gauge, and the prediction that carries the lesson.** *"A scrape is missed and the process
  restarts. Which of these two survives, and which one silently lies?"* A counter only goes up, which
  looks like a limitation until you see that it is the only shape from which a rate can be recovered
  after a gap — and that a gauge of "requests in the last minute" cannot be repaired by anyone.
- **Histograms, read raw before any function exists.** `apiserver_request_duration_seconds_bucket{…,
  le="0.005"}` — cumulative buckets. The reader computes a p99 **by hand** from the `le` series, and
  then meets `histogram_quantile()` and the honest kicker: the answer is a linear interpolation *inside*
  a bucket, so **the number it returns is a latency no request ever experienced**, and if your SLO
  boundary is not a bucket edge, the report is arithmetic on an edge. Same habit as Act VIII's
  "infeasible is a number."
- **Summaries**, and why they cannot be aggregated across Pods — one sentence, one reason.

Then the three kubelet endpoints (§3's table), what `kubectl top` actually reads (`/metrics/resource`,
76 series), and §5.1: `metrics.k8s.io` is an **APIService**, so `kubectl top` reads a path the API
server proxies and etcd has never seen. Finally §5.5: `container_cpu_usage_seconds_total` is the
`cpu.stat` file from Act IV, printed.

**Rival.** `kubectl top` — which is the aggregate, instantaneous, unlabelled, cached version of the
endpoint the reader just read, and its failure mode (a spike shorter than the resolution) is drill 6's
neighbour.

**Leaves open.** One `curl` is one instant. You cannot see a trend, and the endpoint forgets everything
the moment it answers.

**New tools:** none required (`curl`, `kubectl get --raw`, `grep`, `awk` all owned). `promtool check
metrics` optional here, natural in 04. **Exam value:** real for CKA's monitoring bullet — the failure
modes of `kubectl top` become derivable rather than memorised.

### 04 — `04-the-loop-that-scrapes.md` (~4,200 words)

**Wall.** Lesson 03's.

**Mechanism — the act's central "build the rival by hand" beat.** Six lines:

```
while :; do
  printf '%s ' "$(date +%s)"
  curl -s "$TARGET/metrics" | awk '$1=="apiserver_request_total_sum"{print $2}'
  sleep 15
done >> /tmp/series
```

That file is a time-series database. Subtract two counter samples, divide by the timestamp delta with
`awk`, and the reader has written `rate()`. **Then feel every one of the four things missing**, each as
a failure that happens rather than a bullet:

1. **No service discovery.** The IP was typed; the Pod restarted; Act V already proved a Pod IP is not
   a name.
2. **No alignment.** Samples land at 15s ± drift, so two series cannot be joined, so no ratio, so no
   error rate.
3. **No retention policy.** The file grows until the disk does not.
4. **Counter resets.** The Pod restarted and the value went *backwards* — the reader's `awk` prints a
   negative rate, and now knows why `rate()` is a function rather than a subtraction.

Prometheus then arrives as exactly that loop plus those four fixes, and its architecture is
recognition, not new material: **service discovery is a watch on the API server** (Act VI), a
`ServiceMonitor` is a **CRD** (Act VII 09) read by a **controller** that rewrites config (Act VII 08b).
Nothing new — four things the reader owns, composed.

**The measured surprise.** Prometheus **pulls**. So the scraper decides who exists, and a target that
was never discovered produces no metric, no error, and no gap in a graph — **absence is silent.** That
is lesson 05's most valuable page, seeded here, and drill 2.

Also here, because it is where the reader will actually hit it: scraping the kubelet reproduces Act VII
lesson 10's `no IP SANs` error *exactly*. The reader has already diagnosed it once. Recognition, and it
retroactively validates the earlier lesson.

**Predict first.** *"You wrote the loop with `sleep 15`. You are about to ask Prometheus for
`rate(x[1m])`. How many samples is that, and what happens at `rate(x[30s])`?"* (Drill 1.)

**Leaves open.** You have history and a query language. Nobody is looking at it.

**New tools:** `prometheus`, `promtool`. **Exam value:** none. Say so.

### 04b — `04b-the-cost-of-one-label.md` (~2,400 words)

**Wall.** Lesson 04 gave you somewhere to put labels, and lesson 03 showed labels are what make a
metric answerable. So label everything.

**Mechanism.** Cardinality as multiplication, then as bytes. Count series with
`count({__name__=~".+"})`, add a label carrying a Pod IP (or a user ID, or a URL with an ID in it),
count again. Measure Prometheus's own RSS and `prometheus_tsdb_head_series` — Prometheus is scraped by
Prometheus, which is itself the lesson's neatest joke and its most useful habit.

**The arithmetic to carry.** A metric with 4 labels of 10 values each is 10,000 series. Change one label
to something unbounded and the ceiling is gone — and the idle API server already produced **28,741**
series before anyone added anything (§3). Then the fix, which is a mechanism and not advice:
`metric_relabel_configs` with a `labeldrop`, applied at scrape time, because **the only cheap place to
delete a label is before it is stored.**

**Rival.** "Just add the label, storage is cheap" — priced.

**Leaves open.** Nothing new; this page exists so lesson 05's thresholds are about a system that can
still answer a query.

**New tools:** none. **Exam value:** none. Highest practical value per word in the act.

### 05 — `05-an-alert-is-a-loop.md` (~4,000 words)

**Wall.** History and a query, and nobody watching.

**Mechanism, and it is the act's best callback.** An alerting rule is a query evaluated on an interval
against a threshold, and `for: 5m` is a **time bound**. That is Act VII 08b's insight about GitOps
self-heal — *"a time bound, not a prevention"* — arriving in a new place unchanged. Build a rule, watch
`inactive → pending → firing`, and read the state machine as the reconciliation loop it is: desired
state is a number you asserted, and the action is to tell a human.

**Then the four ways it fails, each measured, each a real 3am story:**

1. **The silent target.** Break the scrape selector. Every panel reads zero, and the alert **does not
   fire** — because no series is not `false`, it is *absent*, and a comparison against nothing yields
   nothing. The fix is a rule about a metric that does not exist: `absent()` / `up == 0`. **This is the
   single most valuable page in the act** and it is drill 2.
2. **The stale-but-true field.** The repo's own recurring theme, arriving where it started: a number
   that is being served and has not been updated.
3. **Cause versus symptom, as arithmetic.** Paging on "CPU > 80%" needs *n* rules and misses the
   *n+1*th; paging on "checkouts are failing" needs one. That is where **RED and USE** earn their place
   — they are not a taxonomy, they are the answer to *which* four queries — and where the **error
   budget** turns a typed threshold into a derived one: 99.9% over 30 days is **43m 12s**; a 14.4×
   burn rate consumes 2% of it in an hour. Show the division.
4. **The pager storm.** One node down, forty alerts. Alertmanager's `group_by` is the label model again
   — one mechanism, third appearance. Kept short on purpose.

**Predict first.** *"You will delete the scrape config for the Service your alert watches. Before you
do: say whether the alert fires, stays quiet, or goes into an error state."*

**Leaves open.** The alert fired: p99 latency is up. **Which of the twelve services?** A metric threw the
individual away by design, and a log kept the individual with nothing that joins it across a hop.

**New tools:** Alertmanager (light), `amtool` (optional). **Exam value:** none. Say so.

### 05b — `05b-a-panel-is-a-query.md` (~2,200 words)

**Wall.** Everything so far has been one number at a time.

**Mechanism.** `curl 'localhost:9090/api/v1/query_range?query=…&start=…&end=…&step=…'`, read the JSON,
*then* open the Grafana panel that renders exactly that response. A dashboard is a saved query, a time
range and a `step` — and the `step` is the one field that actually bites: **a panel silently changes its
own resolution with the width of your browser window**, so the same panel over 6 hours and over 30 days
answers two different questions, and the 30-day one cannot show a two-minute outage at all.

**Rival.** The dashboard somebody else built, with a variable pinned to a namespace that no longer
exists, rendering "no data" in the same colour as zero. (Drill candidate 10.)

**New tools:** Grafana (one container, provisioned from a file, no clicking through a wizard).
**Exam value:** none.

### 06 — `06-which-request-was-slow.md` (~3,800 words)

**Wall.** Lesson 05's closing question.

**Mechanism, stated as bluntly as it deserves: a trace is a header.**
`traceparent: 00-<32 hex trace-id>-<16 hex span-id>-01` (W3C Trace Context). Two toy services, and the
reader propagates the header by hand — then **deliberately fails to**, and watches one trace become two
unrelated trees, each of which looks complete. That is the entire distributed-tracing problem, and
everything else in the category is storage.

**The honest ceiling, stated in the opening rather than buried.** This is the one signal you cannot have
without changing the application — which is why it is last, why most organisations do not have it, and
why the mesh's version has holes: a sidecar or an eBPF datapath can produce ingress and egress spans and
**never an in-process one**, so mesh-only traces are shaped like the gaps in your own code. Act V's
Cilium/Hubble material is the cross-reference and it is already written.

**The arithmetic.** Head sampling at 1%: the request that failed is 99% likely absent from your store —
which means the trace you most need is the one you probably threw away. Tail sampling fixes it by
buffering every span until the trace completes, which is exactly why it costs more. One division, and
the reader can price both.

**Then OpenTelemetry's real contribution, in a paragraph:** not a backend, a wire format and an SDK, and
the fight it ended was n×m adapters between every language and every vendor.

**Predict first.** *"Service A calls B calls C. B forwards the request and forgets one header. Say how
many traces your backend now holds, and how each one looks to somebody reading it."*

**Leaves open — the act's closer, which also has to re-point the bridge Act X currently owns.** Something
like: eleven acts built a system and then taught it to remember. Every mechanism in this act is a
decision about what to throw away, made before the incident by somebody who did not know what the
incident would be — and the next territory is the one where the metrics, the logs, the traces, the
retention and the bill all belong to a provider whose source you cannot read, and whose defaults were
chosen for their margin rather than your outage.

**New tools:** `curl` (owned); optionally `otel-cli`. **Exam value:** zero. State it the way Act X
lesson 11 does.

---

## 7. The drills — `diagnose.md` + `drills/act-11/NN.sh` (~6,500 words)

Act X's diagnose page found the strongest possible framing for its own subject: *every component is
healthy, every command succeeds, and the control is not doing what somebody believes.* **That framing is
literally what a monitoring failure is**, so Act XI inherits it rather than inventing one — with the
turn of the screw that here, the thing that is wrong is **the instrument you would have used to find out
that something is wrong.**

Act XI's method, in the position where Act V has five questions and Act X has four:

1. **Is there a series at all?** Not "is it in range" — does the query return anything? Nothing is not
   zero and it is not false.
2. **What is the resolution of the thing I am reading, and what is shorter than it?**
3. **Who decided this target exists, and would I know if they stopped?**
4. **If this signal quietly stopped arriving, what would look different?** — Act X's question four,
   pointed at the monitoring instead of the control, and again the one nobody asks.

Nine drills. Every one reproducible, every one verified by function against a real cluster before
shipping, every one a `verify-drill.sh` cause hash — the Phase 1 bar.

| # | Symptom | Root cause | Verified by |
|---|---|---|---|
| 1 | A panel and an alert both empty; the metric plainly exists | `rate(x[1m])` with a 60s scrape interval — under two samples in the window, so the function returns nothing | query returns a series again **and** the window is ≥ 2× the interval, read from config not from prose |
| 2 | Dashboard flat green, alert never fired, nothing unhealthy | A scrape selector matching nothing after a Service label was renamed. No series ≠ false | `up{job=…} == 1` **and** an `absent()`/`up == 0` rule now exists |
| 3 | Queries time out; Prometheus RSS climbing | A label carrying the Pod IP; series count exploded | `prometheus_tsdb_head_series` under a bound **and** the metric still answers its original question |
| 4 | Shipper `Running`, `Ready`, zero lines shipped | Mounted `/var/log/pods`, tailing `/var/log/containers` — the symlinks point outside the mount | lines arriving at the destination, for a Pod created *after* the fix |
| 5 | The stack trace in the log store is three broken lines | CRI split the long line into `P` records; `kubectl logs` reassembles, the shipper did not | the reassembled line present in the destination |
| 6 | The crash that mattered is not in `kubectl logs`, and `--previous` is empty | 10Mi × 5 rotation, plus a second restart; the file is gone and the flag is a kubelet setting | the log is off the node before rotation can reach it |
| 7 | The latency report and the SLO disagree | `histogram_quantile` interpolating inside a bucket whose edge is not the SLO boundary | the `le` series read raw, and the bucket boundary changed |
| 8 | A ratio that is provably wrong, from a rule everyone reviewed | An average of averages / `avg(rate(...))` where `rate(sum(...))` was meant | both computed by hand from raw samples; the rule matches the hand figure |
| 9 | Two complete-looking traces for one request | One service did not copy `traceparent` | one trace id spanning all three services |

**Optional tenth, paper-shaped** (Act X's `diagnose.md` already establishes that some drills honestly
have no state to check): one node down, forty pages — fix with `group_by`, and the deliverable is the
grouping key.

Drills 1, 7 and 8 need **no cluster at all** — they are arithmetic over samples — which matters for the
same reason Act X said it: it tells the reader which drills they can do on a train.

---

## 8. Exam accounting, honestly

**Act XI closes no CKA or CKS gap.** The two adjacent bullets are already marked ✅ **above exam depth**
in [`exam-prep/cka-domain-map.md`](exam-prep/cka-domain-map.md):

| CKA bullet | Current state | What Act XI changes |
|---|---|---|
| Monitor cluster and application resource usage | ✅ above depth — Act VII 10 + drill 10 | Adds the **mechanism** under `kubectl top`: the three kubelet endpoints, the APIService, and why a spike shorter than the resolution is invisible. Coverage unchanged; derivability improved |
| Manage and evaluate container output streams | ✅ covered — Act VII drill 8 | Adds the **file**: `/var/log/pods`, the CRI format, rotation, and the `crictl logs` path when the API server cannot answer. This is the one section with genuine exam value |
| Everything else in Act XI | — | **Not examined.** Prometheus, PromQL, Loki, Alertmanager, Grafana and tracing appear in neither curriculum |

CKS: nothing. Runtime detection and audit logging are Act X lesson 10, already shipped, and the
`/metrics` exposure question is Act X lesson 07.

**So Route B places Act XI in the optional track**, not on the path — the same treatment Act IX 05
(OAuth against a live IdP) and Act VIII 01–04 already get. Two exceptions worth arguing in the row
itself:

- **Lesson 01's node-file section** (~1,200 words) is worth pulling onto step 4, beside Act VI's
  `crictl logs` descent. "The API server cannot answer and I need the log" is exam-shaped, and the
  answer is a path.
- The optional-track row should say what is true rather than what is polite: **this is the most
  job-relevant act in the repo and the least examinable one.** Read it after the certificate.

---

## 9. The lab, and what must be verified before any prose is written

This repo's standard is that every command has been run. So the plan's job is to name the risks in the
order they should be settled, and to say what the fallback is if one does not hold — the discipline
Phase 1 used when nested overlayfs blocked `ctr run` three lessons in a row.

**The lab is the same two-node `kind` cluster**, with Act X's kubeconfig habit
(`export KUBECONFIG="${TMPDIR:-/tmp}/act11.kubeconfig"`). **No Helm and no operator** until the closing
recognition beat. Everything is one container with a hand-written config, and every lesson uninstalls
what it installed.

**Already verified, on `kindest/node:v1.37.0`, during this plan:**

- `kubectl get --raw /metrics` → 28,741 series lines, exposition format, `aggregator_unavailable_apiservice` in the first ten lines. ✅
- Kubelet `/metrics`, `/metrics/resource`, `/metrics/cadvisor` through the node proxy → 1,774 / 76 / 2,848. ✅
- `/configz` → `containerLogMaxSize: 10Mi`, `containerLogMaxFiles: 5`. ✅
- `/var/log/pods` layout, `/var/log/containers` symlinks, CRI line format with the `F` tag. ✅
- Pod UID naming both the log directory and the cgroup slice. ✅
- `apiserver_request_duration_seconds_bucket` present with real `le` series to hand-compute a quantile from. ✅
- `--event-ttl` unset in kind's apiserver manifest, so the 1h default applies. ✅

**That means lessons 01 and 03 — roughly 7,800 words, the act's whole foundation — are feasible today
with nothing installed.** Write those first.

**Unverified, in risk order. Each has a named fallback:**

| # | Risk | Test | Fallback if it fails |
|---|---|---|---|
| 1 | **Lesson 06's two toy services.** The act's biggest authoring risk: propagating a header needs *something* that makes an outbound call | Two busybox `httpd` CGI scripts, or `socat` pairs, forwarding `traceparent`; no backend | Drop the backend entirely and prove propagation from the **access logs** of the three services — the header is the lesson, the storage never was |
| 2 | **Loki single-binary config.** `schema_config`/`common` have been a moving target across versions | Pin an exact image tag, filesystem storage, monolithic mode; run `logcli` against it | Teach Loki's index-labels-not-lines decision from its own config file and `logcli` against a public demo, and keep the hand-built shipper as the only thing installed |
| 3 | **Prometheus scraping the kubelet.** Needs a ServiceAccount, RBAC, and `insecure_skip_verify` | Expect Act VII 10's `no IP SANs` error and use it as the beat | It is the *desired* outcome, not a blocker — but the RBAC (`nodes/metrics`) must be confirmed rather than guessed |
| 4 | **Memory in Docker Desktop's VM.** Prometheus + Loki + Grafana + a two-node kind cluster | Measure with `--storage.tsdb.retention.time=2h` and a two-target scrape list | Split the act's benches: 02 (Loki) and 04–05b (Prometheus/Grafana) never run at the same time, and each lesson tears down. Say the measured footprint in the README, as Act X does for AppArmor |
| 5 | **Drill 3's cardinality explosion** must be big enough to measure and small enough not to kill the lab | Find the series count that moves RSS visibly and recovers on restart | State the multiplier as arithmetic and measure a smaller one — the lesson is the exponent, not the crash |
| 6 | **Drill 5's `P` records** need a line longer than the runtime's chunk size | Emit a 64KB line and read `0.log` raw | It is visible in the raw file either way; if the runtime does not split at a reachable size, the drill becomes a `diagnose` note rather than a drill |

**Write order (cheapest verification first), which is not the publish order:**
`03 → 01 → 04 → 04b → 05 → 05b → 02 → 06`.

---

## 10. Obligations — the fifteen, plus what a *new act* adds

Every lesson carries the fifteen obligations in
[`PLATFORM-DEPTH-PLAN.md`](PLATFORM-DEPTH-PLAN.md) §4. Run `cd tools && python3 -m harness --list` for
the live table. **Eight teaching files × fifteen** is the real cost of this act, and Phase 1's lesson
was that the obligations are where the time goes, not the prose.

A new *act* adds nine more, and none of them are optional:

1. **The four-file shape** — `README.md`, `test-yourself.md`, `diagnose.md`, `in-the-wild.md`, enforced
   hard by `shape.act-files`.
2. **`networking-fundamentals/README.md`** — the act table row and the prose paragraph, in the register
   the other ten rows use.
3. **`site/scripts/sync-content.mjs`** — an `ACTS` entry (`{ srcDir: 'act-11-observability', slug: 'act-11' }`),
   plus `SHELL_COMMANDS` for every new tool (`promtool`, `logcli`, `amtool`, `prometheus`, `grafana`, …)
   or the fences render as flat plaintext.
4. **`JOURNEY-MAP.md`** — three separate places, and missing one leaves the map lying: the built/roadmap
   status table, Stage 7.8's "still unwritten" sentence, and Stage 7's **"You can now"** paragraph,
   which currently names observability as roadmap in two clauses.
5. **[Act X lesson 11's closing bridge](networking-fundamentals/act-10-cluster-security/11-secrets-from-outside.md)**
   — §2's cost. It currently hands the reader to Stage 8; it now hands them to Act XI, and Act XI's
   closer inherits the AWS bridge.
6. **`exam-prep/`** — `the-exam-path.md`'s optional-track table (§8's row, with the lesson-01
   exception), and the two CKA rows in `cka-domain-map.md` that gain a mechanism link without changing
   their verdict.
7. **`reference/`** — roster rows and `capabilities.json` entries for every new tool, with facets from
   the **closed** vocabularies. Every tool here is `httpapi` except `logcli`/`promtool`/`amtool`, which
   want a deliberate decision rather than a default; then `tools/gen-tool-pages.py` and
   `tools/gen-command-tables.py`, and the syntax-breakdown cells filled by hand. **Phase 1's specific
   trap:** one roster row with two backtick names has only its first name checked. It shipped once
   before it was caught. Do not ship it twice.
8. **`drills/act-11/` + `tools/verify-drill.sh`** — nine verifiers, cause hashes, and `--list` coverage.
9. **`tools/remeasure.py --write`**, in the same commit, or the repo re-acquires the exact defect Phase 0
   removed. Note that Route B's unaccounted-word figure will grow again — it is at **10,644** now — and
   that is expected and honest until the step→file map is encoded as data. This act is a good reason to
   finally do that; it is still unclaimed work.

And item 14 remains non-negotiable: **`learner-simulator` for Spirit and River, `technical-accuracy-checker`
for every command, per file.** A lesson that is merely written is not shippable here.

---

## 11. Sizing, and how it ships

Measured against comparables (Act VIII 32,169 words / 10 files; Act IX 31,258 / 10; Act X 87,398 / 16;
support pages measured at README 1,358–1,627, test-yourself 3,232–3,747, in-the-wild 1,502–1,946,
diagnose 3,933–12,438):

| File | Words |
|---|---|
| 01 nothing here remembers | 3,600 |
| 02 copying it off the node | 3,800 |
| 03 a number a process keeps | 4,200 |
| 04 the loop that scrapes | 4,200 |
| 04b the cost of one label | 2,400 |
| 05 an alert is a loop | 4,000 |
| 05b a panel is a query | 2,200 |
| 06 which request was slow | 3,800 |
| README | 1,600 |
| test-yourself (~28 questions) | 3,600 |
| diagnose (9 drills + method) | 6,500 |
| in-the-wild | 1,800 |
| **Total** | **≈ 41,700** |

Between Act IX and Act VII, above the Act VIII floor the depth plan set, and every file inside the
10,000-word budget with the largest at 4,200 against a course median of 2,988.

**Ship in two waves**, because the act has a natural seam and a 41,700-word single drop is where
verification quality goes to die:

- **Wave 1 — "what the system already writes down":** `01, 03, 04, 04b` + README + the drills that
  belong to them (1, 3, 4, 6, 7, 8 — note six of nine land here). ~19,000 words, and it is the wave
  that closes all four River repairs in §5 and delivers the entire exam-relevant portion.
- **Wave 2 — "what you do with it":** `02, 05, 05b, 06` + test-yourself + in-the-wild + drills 2, 5, 9.
  ~22,700 words, and it is the wave carrying every feasibility risk in §9.

Wave 1 is worth shipping on its own even if wave 2 slips, which is the test of whether a seam is real.

---

## 12. Open questions this plan does not decide

Recorded rather than resolved, in the manner Phase 1 recorded its lab question before evidence settled
it:

1. **Does lesson 02 install Loki at all?** §9 risk 2 may answer this against it, and the hand-built
   shipper plus Loki's config file read as a *document* might teach the index-labels decision just as
   well for a fifth of the setup. Settle by running it, not by preferring it.
2. **`05b` as a lesson or as a section of `05`?** It is 2,200 words and the `step`-resolution insight is
   good enough to stand alone. If it comes in under 1,500 once written, fold it.
3. **Does the act earn a `promtool`-only page?** `promtool check rules` / `promtool test rules` is unit
   testing for alerts, which is a genuinely good practice and possibly a `05c`. Left out of the budget
   deliberately; add only if lesson 05 proves too long.
4. **Which illustrations, if any.** There are none for this subject —
   [`illustrations/MANIFEST.md`](illustrations/MANIFEST.md) holds 83 files across networking topics and
   its 45-file reserve contains nothing observability-shaped. Placing none is fine; placing any requires
   updating the manifest's `## Not placed` list in the same commit, both directions, or
   `illustrations.placement` warns.
5. **The name.** *Act XI — Knowing before someone tells you* is the working title, taken from the depth
   plan's own phrasing of the wall. It should be re-read once lesson 01 exists, since in this repo the
   act title is a promise the first lesson has to keep.
