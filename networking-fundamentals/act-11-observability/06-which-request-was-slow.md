# Which request was slow

Lesson 05 closed on a page you cannot answer with anything built so far: an alert fired, p99 latency across the whole cluster crossed the line, and somewhere in a chain of a dozen services one of them was the one that actually took long. A metric threw the individual request away by design the moment it became a counter or a histogram — that is the entire reason it could be cheap — and a log line about one hop has no idea what happened on any of the others. Answering "which one" needs a signal built to survive crossing a network boundary, and it turns out to be nothing more exotic than one HTTP header, propagated correctly.

> **Predict first —** service A calls B, B calls C, and B forwards the request onward but forgets to copy one specific header along with it. Say how many separate traces your tracing backend ends up holding for this one logical request, and how complete each one looks to somebody reading it.

### A trace is a header

The W3C standard is one string, in one header, present on every request that is part of a trace:

```
traceparent: 00-<32 hex chars: trace-id>-<16 hex chars: span-id>-01
```

Version, trace ID, this hop's own span ID, flags. That is the entire wire format — no schema, no binary encoding, nothing a backend has to be running for the header itself to mean something. The **trace ID** stays identical across every service a request touches; each service mints its own fresh **span ID** for the work it does and, when it calls onward, generates a new outgoing `traceparent` that keeps the same trace ID but carries the new span as the "current" one. A trace, underneath every UI that renders it as a waterfall chart, is just: every span anyone ever logged that shares one trace ID.

Three small services prove the entire mechanism without needing a real backend at all — each one reads the `traceparent` header it received, prints it, and if it calls onward, mints a new span under the same trace ID and forwards that:

```python
import http.server, urllib.request, os, secrets

DOWNSTREAM = os.environ.get("DOWNSTREAM", "")
FORWARD = os.environ.get("FORWARD", "true") == "true"

def mint(trace_id=None):
    return f"00-{trace_id or secrets.token_hex(16)}-{secrets.token_hex(8)}-01"

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        incoming = self.headers.get("traceparent")
        tp = incoming or mint()
        print(f"received traceparent: {tp}", flush=True)
        body = f"tp={tp}\n"
        if DOWNSTREAM:
            trace_id = tp.split("-")[1]
            outgoing = mint(trace_id)
            req = urllib.request.Request(f"http://{DOWNSTREAM}:8080/")
            if FORWARD:
                req.add_header("traceparent", outgoing)
                print(f"calling {DOWNSTREAM}, forwarding traceparent: {outgoing}", flush=True)
            else:
                print(f"calling {DOWNSTREAM}, NOT forwarding (dropped the header)", flush=True)
            with urllib.request.urlopen(req, timeout=5) as r:
                body += r.read().decode()
        self.send_response(200); self.end_headers()
        self.wfile.write(body.encode())
    def log_message(self, *a): pass

http.server.HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
```

Mount that script into three Pods as `svc-a` (`DOWNSTREAM=svc-b`), `svc-b` (`DOWNSTREAM=svc-c`), `svc-c` (no downstream), each behind its own Service so the names resolve, plus one small client to call the front one:

```bash
kubectl create configmap tracer-script --from-file=svc.py=./svc.py

for pair in a:svc-b b:svc-c c:; do
  name="svc-${pair%%:*}"; down="${pair#*:}"
  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: $name, labels: {app: $name}}
spec:
  containers:
  - name: c
    image: python:3.12-slim
    command: ["python3","/app/svc.py"]
    env: [{name: DOWNSTREAM, value: "$down"}, {name: FORWARD, value: "true"}]
    volumeMounts: [{name: script, mountPath: /app}]
  volumes: [{name: script, configMap: {name: tracer-script}}]
---
apiVersion: v1
kind: Service
metadata: {name: $name}
spec:
  selector: {app: $name}
  ports: [{port: 8080, targetPort: 8080}]
EOF
done
kubectl run curltest --image=python:3.12-slim --restart=Never --command -- sh -c "sleep 3600"
```

Wait for all four to reach `Running`, then call the front one:

```bash
kubectl exec curltest -- python3 -c "import urllib.request; print(urllib.request.urlopen('http://svc-a:8080/', timeout=5).read().decode())"
kubectl logs svc-a; kubectl logs svc-b; kubectl logs svc-c
```

```
=== svc-a ===
received traceparent: 00-2e8a91f844ed90bc6e638c46b1d0fe02-c0fcb0b19dcb4409-01
calling svc-b, forwarding traceparent: 00-2e8a91f844ed90bc6e638c46b1d0fe02-1912d349d3ec9494-01
=== svc-b ===
received traceparent: 00-2e8a91f844ed90bc6e638c46b1d0fe02-1912d349d3ec9494-01
calling svc-c, forwarding traceparent: 00-2e8a91f844ed90bc6e638c46b1d0fe02-032e8afd183e384e-01
=== svc-c ===
received traceparent: 00-2e8a91f844ed90bc6e638c46b1d0fe02-032e8afd183e384e-01
```

**`2e8a91f844ed90bc6e638c46b1d0fe02`, identical, on all three lines.** Three different span IDs — one per hop's own work — glued to one shared trace ID, by nothing more than each service reading a header, keeping one field of it, and writing a new value of the same field before it calls onward. A "distributed trace" is this, collected somewhere and grouped by that shared first field.

### The whole problem, in one dropped header

Now break exactly the thing the header depends on — have `svc-b` stop forwarding it, the `FORWARD=false` branch already sitting in the script above. A bare Pod's env can't be patched in place, so delete and recreate it with one field changed:

```bash
kubectl delete pod svc-b --wait=true
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: svc-b, labels: {app: svc-b}}
spec:
  containers:
  - name: c
    image: python:3.12-slim
    command: ["python3","/app/svc.py"]
    env: [{name: DOWNSTREAM, value: "svc-c"}, {name: FORWARD, value: "false"}]
    volumeMounts: [{name: script, mountPath: /app}]
  volumes: [{name: script, configMap: {name: tracer-script}}]
EOF
```

Wait for it to reach `Running` again, then send the same request through:

```bash
kubectl exec curltest -- python3 -c "import urllib.request; print(urllib.request.urlopen('http://svc-a:8080/', timeout=5).read().decode())"
kubectl logs svc-a --tail=2; kubectl logs svc-b --tail=2; kubectl logs svc-c --tail=2
```

```
=== svc-a ===
received traceparent: 00-c1d5495493f6a6a824708a59b11352f5-158d8febff07ca9d-01
calling svc-b, forwarding traceparent: 00-c1d5495493f6a6a824708a59b11352f5-c6567b3e257fd31c-01
=== svc-b ===
received traceparent: 00-c1d5495493f6a6a824708a59b11352f5-c6567b3e257fd31c-01
calling svc-c, NOT forwarding (dropped the header)
=== svc-c ===
received traceparent: 00-4cefa960b71a23cf87a6935507bbaac3-0c5dbc4e48f31280-01
```

**`svc-a` and `svc-b` still agree — `c1d5495493f6a6a824708a59b11352f5` on both. `svc-c` has an entirely different trace ID it minted for itself**, `4cefa960b71a23cf87a6935507bbaac3`, because from `svc-c`'s own point of view, receiving a request with no `traceparent` header is completely indistinguishable from being the very first service a brand-new request ever touched. This settles the prediction at the top of this lesson exactly: one logical request, one dropped header at one hop, and your tracing backend now holds **two complete-looking traces** — `svc-a`→`svc-b`, and a lone, parentless `svc-c` — and nothing about either one, read on its own, looks broken. Each is a well-formed trace with a beginning and an end. The only way to know they were the same request is context the traces themselves no longer carry, which is the entire distributed-tracing problem in one sentence: **every span already knows how to prove it belongs to a trace. Nothing forces the next hop to ask.**

### The honest ceiling, stated before you build anything on top of it

This is the one signal in the whole act you genuinely cannot get without touching the application, and it is worth saying plainly rather than discovering it after building a bigger version: an eBPF datapath — Hubble, which Act V and Act X already gave you — sees every packet cross a socket boundary, both directions, at line rate, with zero code changed. It can tell you a span for "A called B" and a separate span for "B called C." **It cannot see a single instruction of what happened inside B between receiving A's request and issuing its own to C**, because that gap is CPU time in a process, not bytes on a wire, and a datapath only ever sees the wire. A service mesh's sidecar has exactly the same horizon for exactly the same reason — it, too, only sees requests entering and leaving the Pod. Mesh-only tracing produces spans shaped precisely like the gaps in your own code: accurate at every boundary, and silent about everything in between, which is usually where the actual slowness lives.

That is why this signal is last in the act, and why most organizations that have logs and metrics still do not have this: it is the only one of the three that requires changing the thing being observed, deliberately, on purpose, at every hop.

### The arithmetic: sampling prices the trace you actually need against the one you can afford

Recording a full trace for every request is what changed the application in the first place bought you — and it does not stay cheap, because the write volume scales with total request volume, not with anything interesting about any one request. **Head sampling** decides whether to keep a trace at the moment the first span is created, before anyone knows how the request will turn out. Sample 1% of requests and the arithmetic is blunt: for any one specific slow or failed request, the odds it was among the 1% you kept are **1 in 100** — which means **the request you most want to look at during an incident is, 99 times out of 100, one you already decided to throw away**, minutes or hours before the incident happened.

**Tail sampling** fixes exactly this by inverting the decision: buffer every span for a trace, wait until the whole trace completes, and *then* decide to keep it — keep every error, every request over some latency threshold, and sample the boring, fast, successful remainder at a low rate. It answers the actual question ("was this one interesting") instead of a proxy for it decided in advance, and it costs more for a precise reason: buffering means holding open state for every in-flight trace, for as long as the slowest span in it takes to finish, before you are allowed to decide whether any of that work was worth keeping.

### OpenTelemetry, in one paragraph, on purpose

OpenTelemetry is not a backend — it is a wire format and a set of SDKs, and its actual contribution was ending a fight that used to cost every team its own tax: before it, instrumenting a service for vendor X meant one SDK, and switching to vendor Y meant re-instrumenting, because each vendor shipped its own format and its own client library. One format, `N` languages, `M` vendors, and OTLP turned an `N × M` adapter problem into `N + M`. That is the entire idea worth carrying forward — the wire format, not the YAML pipeline configuration in front of it, which is furniture.

<details>
<summary>Check yourself — before reading on</summary>

A teammate proposes fixing the dropped-header bug by having every service independently start its own trace when it does not see one, and stitching them back together later in the backend by matching timestamps. Does that work?

Not reliably. Timestamp matching is a heuristic over correlated but not identical clocks, request volume, and coincidence — at low traffic it might look like it works, and at real traffic, with many concurrent requests hitting the same services within the same few milliseconds, it will confidently stitch together spans from completely unrelated requests that merely overlapped in time. The `traceparent` header exists specifically so that "which request is this" is answered by an explicit, unambiguous identifier carried on the request itself, not inferred after the fact from timing. The actual fix is upstream of the backend: fix the one hop that drops the header, because no amount of clever correlation downstream recovers information that was never sent.

</details>

<!-- figure -->
```
   A TRACE IS A HEADER, AND THE WHOLE PROBLEM IS WHETHER IT SURVIVES A HOP

   THE WIRE FORMAT, IN FULL
     traceparent: 00-<trace-id, 32 hex>-<span-id, 16 hex>-01
     same trace-id every hop. NEW span-id, every hop.

   MEASURED: PROPAGATED CORRECTLY
     A -> B -> C, one trace-id, three span-ids. one logical request,
     ONE trace, three spans, in the backend.

   MEASURED: ONE DROPPED HEADER AT ONE HOP
     A/B share a trace-id. B->C drops the header.
     C, with nothing to read, mints a BRAND NEW trace-id.
     result: 2 complete-looking traces for 1 real request.
     each one, read alone, looks perfectly fine.

   THE HONEST CEILING
     an eBPF datapath / mesh sidecar sees every hop's edges.
     it NEVER sees inside one process between an inbound and
     an outbound call -- CPU time, not bytes on a wire.
     mesh-only traces are shaped like the gaps in your OWN code.

   THE ARITHMETIC
     head sampling @ 1%: the ONE request you need is 99% likely
     the one you already threw away, before the incident happened.
     tail sampling: buffer until the trace completes, THEN decide.
     costs more because it holds state open for every in-flight trace.

   OTEL, IN ONE SENTENCE
     not a backend. a wire format + SDKs.
     ended an N x M adapter problem, turned it into N + M.
```

**Cleanup:**

```bash
kubectl delete pod svc-a svc-b svc-c curltest --ignore-not-found
kubectl delete service svc-a svc-b svc-c --ignore-not-found
kubectl delete configmap tracer-script --ignore-not-found
```

> **You understand this when you can** state the whole `traceparent` format from memory and say which part changes at every hop and which part never does; explain, using this lesson's own measurement, how one dropped header turns one request into two unrelated-looking traces; say precisely what an eBPF datapath or a mesh sidecar can and cannot see about a request, and why the boundary is architectural rather than a bug; and compute, without hesitating, why a 1% sampling rate makes the request you most want to see the one you were least likely to keep.

**Which raises — the act's own closer:** eleven acts before this one built a system, and this one taught it to remember, on purpose, at a cost measured the whole way through: a `10Mi × 5` file limit, a linear interpolation inside a histogram bucket, a resident-memory line item per time series, a sampling rate that decides in advance which requests get to matter later. Every mechanism in this act is a decision about what to throw away, made *before* the incident, by someone who did not yet know what the incident would be. The next territory is the one where every one of those decisions — the metrics, the logs, the traces, the retention, the bill — belongs to somebody else's control plane, and the only genuinely new question, the same one Act X's own closing line already asked of everything past this course's edge, is what changes when the thing making those decisions is an API you cannot read the source of.

---

↑ **[Act XI overview](README.md)** · Prev: **[A panel is a query](05b-a-panel-is-a-query.md)** · Next: **[Test yourself](test-yourself.md)** →
