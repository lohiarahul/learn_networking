# An alert is a loop

Lesson 04b closed with a system that can survive its own cardinality and answer a query in milliseconds — and nobody watching it decide anything on your behalf. Every number in this act so far has needed a human to type a query and read the answer back. That is still a dashboard, not monitoring, and the difference is one more loop: something that asks the same question Prometheus already knows how to answer, on its own schedule, and tells a human only when the answer crosses a line someone drew in advance.

> **Predict first —** you are about to delete the scrape config for the one target an alert rule watches. The target itself stays perfectly healthy; Prometheus just stops asking it anything. Before you do it: say whether the alert fires, stays quiet, or moves into some kind of error state.

### The rule is a query, `for:` is a clock, and you have met this shape before

An alerting rule has three parts: a PromQL expression, a threshold built into that expression, and a duration called `for`. Every `evaluation_interval`, Prometheus runs the expression. If the result is non-empty, the rule moves to **pending**. If it is still non-empty `for` seconds later, unbroken, it moves to **firing** and a notification goes to Alertmanager. Drop below the threshold at any point before `for` elapses and the rule falls back to **inactive**, no notification sent, as if the last few evaluations never happened.

**`for` is a time bound, the same shape Act VII lesson 08b found underneath GitOps self-heal.** That lesson's own conclusion was not "there is no guarantee" — it was sharper than that: self-heal does not stop you changing the cluster, it *bounds how long your change survives*, and that bound is itself "a real and valuable guarantee," just not the one people mean when they say the cluster "cannot" drift. `for` is the identical shape, pointed at a symptom instead of a drifted field: it does not stop a flapping metric from crossing a threshold for a few seconds here and there, but it bounds how long a symptom has to persist, unbroken, before that persistence itself becomes the thing that pages someone. Desired state here is "this expression should be empty," the reconciler is Prometheus's rule evaluator, and the action taken when reconciliation fails for long enough is not a `kubectl apply`, it is paging a human.

Build the smallest version that can show all three states, watching a metric you have not had to write yourself: for every target it scrapes, Prometheus writes one series of its own, `up`, valued `1` if the last scrape succeeded and `0` if it did not — and the `job` label on it is not something the exposition format ever sent; Prometheus attaches it automatically, taken straight from the `job_name:` in the scrape config that found the target in the first place. A target that answers with an empty, valid response is enough to make `up` `1`:

```bash
cat > "${TMPDIR:-/tmp}/demo_exporter.py" <<'PY'
import http.server
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass
http.server.HTTPServer(("0.0.0.0", 9200), H).serve_forever()
PY
docker run -d --name demo-exp --network kind \
  -v "${TMPDIR:-/tmp}/demo_exporter.py":/exp.py \
  python:3.12-slim python3 /exp.py

mkdir -p "${TMPDIR:-/tmp}/act11-alert"
cat > "${TMPDIR:-/tmp}/act11-alert/alert.rules.yml" <<'EOF'
groups:
  - name: demo
    rules:
      - alert: DemoTargetDown
        expr: up{job="demo"} == 0
        for: 15s
        labels: {severity: page}
        annotations: {summary: "demo target is down"}
EOF
cat > "${TMPDIR:-/tmp}/act11-alert/prometheus.yml" <<'EOF'
global:
  scrape_interval: 5s
  evaluation_interval: 5s
alerting:
  alertmanagers: [{static_configs: [{targets: ["am-test:9093"]}]}]
rule_files: ["/etc/prometheus/alert.rules.yml"]
scrape_configs:
  - job_name: demo
    static_configs: [{targets: ["demo-exp:9200"]}]
EOF
cat > "${TMPDIR:-/tmp}/act11-alert/alertmanager.yml" <<'EOF'
route: {receiver: null-receiver, group_by: ['alertname']}
receivers: [{name: null-receiver}]
EOF
docker run -d --name am-test --network kind \
  -v "${TMPDIR:-/tmp}/act11-alert/alertmanager.yml":/etc/alertmanager/alertmanager.yml \
  prom/alertmanager:v0.28.0
docker run -d --name prom-alert --network kind \
  -v "${TMPDIR:-/tmp}/act11-alert/prometheus.yml":/etc/prometheus/prometheus.yml \
  -v "${TMPDIR:-/tmp}/act11-alert/alert.rules.yml":/etc/prometheus/alert.rules.yml \
  prom/prometheus:v3.0.1
sleep 8
```

This lesson uses `for: 15s` where a production rule would say `5m` — long enough only to watch the transition happen without staring at a terminal for five minutes. Nothing about the mechanism changes with the number. Kill the target and poll the rule's own state every two seconds:

```bash
docker stop demo-exp
for i in $(seq 1 12); do
  sleep 2
  docker exec prom-alert wget -qO- http://localhost:9090/api/v1/rules 2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['groups'][0]['rules'][0]['state'])"
done
```

```
inactive
inactive
inactive
pending
pending
pending
pending
pending
pending
pending
firing
firing
```

**Inactive for three polls, pending for seven, firing from the eighth.** The gap between the first `pending` and the first `firing` in that run was fifteen seconds, measured wall-clock, matching the `for: 15s` declared in the rule exactly — because that is the entire mechanism. Nothing about "how sick" changed between poll four and poll eleven. What changed was how long the sickness had been continuously true, which is a fact about a clock, not about the target.

### The most valuable page in this act: absence is not zero

Stop and change one thing about the setup above: instead of a target that fails, use a target that was **never scraped at all** — a job name the config never mentions, the same shape as a Service selector renamed out from under an alert rule that nobody updated to match.

```bash
docker start demo-exp
cat > "${TMPDIR:-/tmp}/act11-alert/alert.rules.yml" <<'EOF'
groups:
  - name: demo
    rules:
      - alert: GhostTargetDown
        expr: up{job="ghost"} == 0
        for: 15s
        labels: {severity: page}
        annotations: {summary: "ghost target is down"}
EOF
docker restart prom-alert
sleep 8
docker exec prom-alert wget -qO- 'http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22ghost%22%7D'
```

```json
{"status":"success","data":{"resultType":"vector","result":[]}}
```

**An empty result. Not `up{job="ghost"} = 0` — nothing at all,** because `job="ghost"` was never scraped by anything, so there is no series to have a value in the first place. Wait well past the fifteen-second `for` window and check the rule:

```bash
sleep 20
docker exec prom-alert wget -qO- http://localhost:9090/api/v1/rules 2>/dev/null \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['groups'][0]['rules'][0]['state'])"
```

```
inactive
```

**Still inactive, twenty seconds after a `for: 15s` rule was supposed to have long since fired.** This is the answer to this lesson's opening prediction, and it is the most expensive thing in this act to learn during an incident rather than during a lesson: `up{job="ghost"} == 0` is a comparison, and a comparison needs both sides to exist. `up{job="ghost"}` does not evaluate to `0` when nothing is being scraped under that name — it evaluates to *nothing*, an empty vector, and `nothing == 0` is not `true`, it is nothing too. The rule never even reaches **pending**, because the condition was never once satisfied. **Deleting the scrape config for a target an alert watches does not make the alert fire. It makes the alert permanently unable to fire, while looking, from the rule's own state, identical to "everything has been fine the entire time."**

The fix is a different function, not a different threshold:

```bash
docker exec prom-alert wget -qO- 'http://localhost:9090/api/v1/query?query=absent(up%7Bjob%3D%22ghost%22%7D)'
```

```json
{"status":"success","data":{"resultType":"vector","result":[{"metric":{"job":"ghost"},"value":[1788077159.058,"1"]}]}}
```

`absent()` asks a different question on purpose: not "what is the value of this series" but "does at least one series matching this selector exist right now." When nothing does, `absent()` returns a one-element vector with value `1` — and note there is no `== 1` anywhere in the rule that would use it. Prometheus fires an alert for every row an expression's result contains, regardless of what that row's *value* is; `absent(up{job="ghost"})` returning one row is already enough. The rule that actually catches a target vanishing looks like `expr: absent(up{job="ghost"})`, full stop, and it is a genuinely different sentence from `up{job="ghost"} == 0` even though a person skimming both would assume they cover the same failure.

The general form matters more than this one metric: **a panel showing "no data" and a panel showing a healthy `0` render identically**, and a threshold alert built against either one silently cannot see the other. Anywhere you write `metric == 0` or `metric > threshold` as your only check, ask the second question `absent()` asks — not "is the number wrong," but "is there a number here at all" — because Prometheus pulling, the design decision lesson 04 measured, means a target that stops existing produces no error, no gap, and no signal of any kind except its own silence.

### The stale-but-true field

A second, quieter way a watched value can lie: it can be exactly correct and also completely wrong, if it stopped updating and nobody noticed the difference between "current" and "cached." Lesson 03 already measured this shape once — `kubectl top` answers from metrics-server's own polling cache, on metrics-server's own schedule, not on demand — and the same fact recurs here in alerting form: a rule reading a gauge that a crashed exporter last wrote five minutes ago sees a value that is **true of five minutes ago** and treats it as true of now, because nothing about the number itself carries a "this might be old" flag. The fix is the same one Act IV's process-liveness material already gave you for a different subsystem: pair every "what is the value" check with a "when was it last updated" check, because a frozen number and a healthy one are indistinguishable by value alone.

### Cause versus symptom, priced

A cluster with twelve services has, conservatively, a dozen things you could threshold: CPU, memory, restart count, request latency, per service. Page on all twelve and you have written twelve rules and still missed the thirteenth failure mode nobody thought to threshold. Page on **"checkouts are failing"** instead and you have written one rule that catches all thirteen, because you stopped asking "is a resource unusual" and started asking "is the thing users actually want still happening."

**RED** (rate, errors, duration) and **USE** (utilization, saturation, errors) are not a taxonomy to memorize — they are the answer to *which four queries*, for a request-driven service and a resource respectively, tend to be the smallest set that catches almost everything without needing per-cause rules. They earn their place here because they are the mechanical answer to the paragraph above, not because they are industry vocabulary.

The same instinct turns a typed threshold into a derived one. "Page when error rate exceeds 1%" is a number someone guessed. An **error budget** is the same threshold, computed instead of guessed, from a promise you already made: a 99.9% availability target over 30 days permits

```
30 days × 24h × 60m = 43,200 minutes = 2,592,000 seconds
2,592,000 × 0.001 = 2,592 seconds = 43 minutes 12 seconds
```

**43m 12s of allowed badness across the whole month, and not a second more, if you meant 99.9%.** That number is what "the error rate is too high" actually means, in the only unit that matters — time you promised and time you are spending. A **burn rate** is how fast you are spending it: burning at exactly 1× exhausts the entire month's budget in exactly a month; burning at **14.4×** exhausts the same budget in `30 ÷ 14.4 ≈ 2.08 days`, which means one hour at that rate spends

```
1 hour ÷ 50 hours ≈ 2%
```

**about two percent of the whole month's budget, in one hour.** That arithmetic — not a philosophy chapter about error budgets, one division performed twice — is the point at which "page someone" stops being a number typed into a YAML file and starts being a number derived from a promise the team already signed up to keep.

### The pager storm, and why it is the label model again

One node goes down and forty Pods on it start failing every liveness probe at once. Forty independent rules firing in the same ten seconds is forty pages, for one root cause, and a human paged forty times learns nothing that a human paged once would not have. Alertmanager's fix is `group_by`, set once in the routing config used in this lesson's own setup above (`group_by: ['alertname']`): alerts sharing the grouping labels are bundled into a single notification, however many of them fired. It is the label model — Act X's third appearance of grouping-by-label as the fix for too much undifferentiated noise — arriving once more, in exactly the shape it arrived in before. Nothing new to learn here beyond recognizing the pattern; that is why it earns one paragraph and not a page.

<details>
<summary>Check yourself — before reading on</summary>

A rule reads `expr: rate(errors_total[5m]) / rate(requests_total[5m]) > 0.01`. Traffic drops to zero overnight — no requests, no errors. Does this rule fire?

No, and the reason is the same one `absent()` exists to fix, arriving from a different direction: with zero requests, `rate(requests_total[5m])` is `0`, and dividing by zero in PromQL does not raise an error, it produces no result for that series — the whole expression evaluates to an empty vector, not to `0/0` treated as some sentinel. An empty vector cannot be greater than `0.01`, so the comparison never fires, silently, at the exact moment traffic patterns look the most unusual. The fix is the same shape as this lesson's main one: check whether requests exist at all (`rate(requests_total[5m]) > 0`) before trusting a ratio built on top of them.

</details>

<!-- figure -->
```
   AN ALERT IS A LOOP, AND for: IS A CLOCK, NOT A GUARANTEE

   THREE STATES, ONE MEASURED TRANSITION
     inactive -> pending -> firing
     measured: pending seen at t, firing seen at t+15s -- exactly `for: 15s`.
     drop below threshold before `for` elapses -> back to inactive, silently.

   THE MOST VALUABLE PAGE IN THE ACT
     up{job="ghost"} == 0        -- comparison against NOTHING, forever inactive
     absent(up{job="ghost"})     -- fires on the ABSENCE itself, no "== 1" needed
     "no data" and "healthy zero" render IDENTICALLY on a panel.
     a target that was never scraped cannot be caught by a threshold alone.

   STALE IS NOT THE SAME AS WRONG
     kubectl top's cache, met again: a frozen number and a fresh one
     look identical by VALUE. pair every check with "when was this updated."

   CAUSE VS SYMPTOM, PRICED
     12 resource-threshold rules miss the 13th failure mode.
     1 symptom rule ("checkouts are failing") catches all 13.
     RED / USE = the mechanical answer to WHICH four queries.
     error budget: 99.9% / 30d = 43m 12s. burn 14.4x -> 2% of it in 1 hour.

   THE PAGER STORM
     40 Pods, 1 node, 1 root cause -> group_by(alertname) -> ONE page.
     the label model, a third time.
```

**Cleanup:**

```bash
docker rm -f demo-exp prom-alert am-test
```

> **You understand this when you can** describe the three rule states and say exactly what `for:` measures; explain why `up{job=X} == 0` cannot detect a target that was never scraped, and why `absent()` can; state the difference between a value that is wrong and a value that is merely old, and why neither looks different from the other by itself; and turn an availability promise into a number of minutes without a calculator.

**Which raises:** the alert fired — p99 latency across the whole cluster just crossed the line. **Which of the twelve services actually caused it?** A metric threw the individual request away by design the moment it became a counter or a histogram, and nothing built so far in this act can join one slow request across a hop between two services to answer that question.

---

↑ **[Act XI overview](README.md)** · Prev: **[The cost of one label](04b-the-cost-of-one-label.md)** · Next: **[A panel is a query](05b-a-panel-is-a-query.md)** →
