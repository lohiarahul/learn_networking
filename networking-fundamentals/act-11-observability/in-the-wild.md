# Act XI in the wild — the same four mechanisms, industrialised

This page covers the four lessons built so far. More will be added as lessons 02, 05, 05b and 06 ship.

## The stack you will actually meet has a name for everything you just built by hand

Every production Kubernetes cluster you touch will already have some assembly of Prometheus, a log store, an alerting layer and (sometimes) a tracing backend — usually installed as `kube-prometheus-stack`, a Helm chart bundling Prometheus, Alertmanager, Grafana, a set of dashboards and the `ServiceMonitor` CRD that lesson 04 named but did not install. Nothing about what you have built so far is a toy version of this — it *is* this, minus the packaging. The six-line loop is what a scrape target actually is; the RBAC token you minted by hand is what every `ServiceMonitor` needs behind the scenes; the `metric_relabel_configs` `labeldrop` you wrote is a config block that exists, verbatim, in every serious production Prometheus. Reading a real cluster's `kube-prometheus-stack` values file after this act should feel like reading assembly instructions for parts you already recognise, not like meeting a new subject.

The honest reason this act declines to install that chart as an *entry point*: doing so first would have hidden every mechanism this act exists to teach, the same way installing `kubeadm` on day one of Act VI would have hidden the control plane. It earns a place once — at the end of this act, once written — as recognition rather than instruction.

## The one number every SRE org tracks that you can already compute

`prometheus_tsdb_head_series`, which lesson 04b had you read directly, is the single most common cause of a real production Prometheus falling over — not disk, memory. Organisations running Prometheus at any scale set a **cardinality budget** per team or per metric, enforced at scrape time with exactly the `metric_relabel_configs` mechanism you used, and the postmortem for "why did our monitoring system stop answering queries" is overwhelmingly often "a label carrying something unbounded — a user ID, a URL, a Pod IP — and nobody noticed until the series count had already multiplied past what the box could hold." You have now seen the whole failure mode end to end, at a scale small enough to watch happen in thirty seconds instead of three weeks.

## `kubectl top`'s aggregation layer is not a curiosity

The APIService mechanism lesson 03 traced — the API server proxying `metrics.k8s.io` sideways to another Pod's cache rather than reading etcd — is the same mechanism behind every "custom metrics" or "external metrics" API a production cluster wires up for autoscaling on something other than CPU and memory (queue depth, request latency, a business metric). Every one of them registers as an `APIService` and every one of them has metrics-server's exact shape: a component polling on its own schedule, answering from memory, with no durability and no history. If a Horizontal Pod Autoscaler in a real cluster is scaling on a custom metric and the scaling looks "sticky" or delayed, the aggregation layer's caching behaviour — the same behaviour lesson 03 measured for `kubectl top` — is usually why.

## eBPF observability, already partly yours

Act V and Act X already taught **Hubble**, Cilium's flow-observability layer — which watches every packet at the kernel level with zero application change, the eBPF-based category this act otherwise declines to install a second time. Pixie and similar tools extend the same idea to full request tracing without code instrumentation, which is worth sitting with rather than taking on faith: an eBPF datapath sees a packet cross a socket boundary, going in and coming back out. Hold onto the question of what that datapath can and cannot see about the time *between* those two crossings — a later lesson on tracing answers it directly, and the answer is the reason most organisations still instrument their own code rather than trusting the network alone to explain a slow request.

## Vendor SaaS platforms

Datadog, New Relic, Honeycomb and similar products are, underneath their dashboards, an agent (often a DaemonSet, sometimes an OpenTelemetry Collector) shipping the same metrics/logs/traces you have been reading raw in this act into somebody else's time-series database, at a price scaled to the volume you send. Nothing about the mechanism changes — the agent still scrapes, the cardinality still costs money exactly the way lesson 04b measured, and the vendor's own pricing pages are frequently the most honest place to see the arithmetic of §3's table (a metric with high-cardinality labels is billed differently from one without, because the vendor is paying the same storage cost you would have). Choosing one is a build-vs-buy decision about *ops burden*, not a decision about which mechanism is correct.

## Deliberately not covered here

**A Grafana dashboard-building tutorial.** A GUI walkthrough ages in months and teaches nothing transferable; a later lesson builds the same panel from its own `query_range` JSON first, which is the part that survives a UI redesign.

**Installing Loki, Alertmanager or a tracing backend as a product tour.** Each earns exactly one page, for exactly one design decision (Loki's labels-not-lines indexing; Alertmanager's grouping; a `traceparent` header propagated by hand), once those lessons ship.

**The OpenTelemetry Collector's pipeline configuration.** OTLP's real contribution is being a wire format that ended an n×m adapter problem between every language and every vendor — worth one paragraph, not a YAML walkthrough.

**An SRE-book chapter on error budgets as philosophy.** The arithmetic — how a burn rate consumes a 30-day error budget in an hour — earns its place as one page of division once alerting is covered, not as a chapter of prose.

> **The question to carry out of this half of the act:** every mechanism here is a decision about what to throw away, made before an incident by someone who did not know what the incident would be. What does your own cluster keep, and did anyone decide that on purpose?

---

↑ **[Act XI overview](README.md)** · Prev: **[Diagnose it](diagnose.md)**
