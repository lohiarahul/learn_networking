# A panel is a query

Every number this act has produced so far has arrived one at a time: a `curl`, a `wget`, a JSON blob read with `python3 -m json.tool`. That was deliberate — it is the only way to be sure you know what a metric actually is before a tool draws a picture of one — but it leaves an obvious gap. Nobody stares at raw JSON in an incident. They look at a dashboard. This lesson closes that gap by building the dashboard's data yourself, by hand, before ever opening the tool that renders it — so the picture stops being magic and starts being a JSON response with axes drawn on it.

> **Predict first —** a panel shows the last 30 days of a metric, smoothly, with no visible incidents. A genuine two-minute outage happened exactly seven days ago, confirmed by other means. Before opening anything: say whether you would expect that outage to be visible in this panel, and why the panel's own honesty or dishonesty is not the deciding factor.

### The one HTTP call every panel makes

A Grafana panel is not a special kind of object. It is a saved **query**, a **time range**, and a **step**, and the request it sends to Prometheus is the same `/api/v1/query_range` endpoint you can call yourself:

```bash
docker run -d --name prom-panel --network kind prom/prometheus:v3.0.1
sleep 15
END=$(date +%s); START=$((END-300))
docker exec prom-panel wget -qO- \
  "http://localhost:9090/api/v1/query_range?query=up&start=$START&end=$END&step=15" \
  | python3 -m json.tool | head -25
```

```json
{
    "status": "success",
    "data": {
        "resultType": "matrix",
        "result": [
            {
                "metric": {
                    "__name__": "up",
                    "instance": "localhost:9090",
                    "job": "prometheus"
                },
                "values": [
                    [
                        1788081868,
                        "1"
                    ],
                    [
                        1788081883,
                        "1"
                    ]
                ]
            }
        ]
    }
}
```

**A matrix of `[timestamp, value]` pairs, one array per label combination.** That is the entire payload behind a line chart: each `values` array is one line, each pair is one point on it, and every axis, every color, every legend label Grafana ever draws is decoration on top of exactly this response. `query` picked *what*, `start`/`end` picked the window, and `step` picked how many points come back inside it — three parameters, and you already own the tool that sets all three by hand.

### Provision it from a file, the way every other tool in this act was configured

No wizard, no "add data source" click-through — one YAML file each, read at container start, the same habit as every Prometheus config in this act:

```bash
mkdir -p "${TMPDIR:-/tmp}/grafana/provisioning/datasources" \
         "${TMPDIR:-/tmp}/grafana/provisioning/dashboards" \
         "${TMPDIR:-/tmp}/grafana/dashboards"

cat > "${TMPDIR:-/tmp}/grafana/provisioning/datasources/prom.yml" <<'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prom-panel:9090
    isDefault: true
EOF

cat > "${TMPDIR:-/tmp}/grafana/provisioning/dashboards/dash.yml" <<'EOF'
apiVersion: 1
providers:
  - name: default
    folder: ''
    type: file
    options: {path: /var/lib/grafana/dashboards}
EOF

cat > "${TMPDIR:-/tmp}/grafana/dashboards/demo.json" <<'EOF'
{
  "title": "Demo",
  "panels": [
    {"id": 1, "title": "up", "type": "timeseries",
     "targets": [{"expr": "up", "refId": "A"}],
     "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}}
  ],
  "schemaVersion": 39,
  "version": 1
}
EOF

docker run -d --name graf-panel --network kind -p 3000:3000 \
  -v "${TMPDIR:-/tmp}/grafana/provisioning":/etc/grafana/provisioning \
  -v "${TMPDIR:-/tmp}/grafana/dashboards":/var/lib/grafana/dashboards \
  -e GF_AUTH_ANONYMOUS_ENABLED=true -e GF_AUTH_ANONYMOUS_ORG_ROLE=Admin \
  grafana/grafana:11.4.0
sleep 10
docker logs graf-panel 2>&1 | grep provisioning
```

```
logger=provisioning.dashboard t=… level=info msg="starting to provision dashboards"
logger=provisioning.dashboard t=… level=info msg="finished to provision dashboards"
```

**One panel, one PromQL expression, checked into a file** — the whole dashboard is now a JSON document sitting on disk that you can diff, review in a pull request, and reconstruct on a machine that has never seen a mouse. Open `http://localhost:3000` and the panel you provisioned is already rendering the exact `up` series you queried by hand a moment ago. That is not a coincidence to marvel at — it is the same HTTP call, made by a browser instead of by `curl`, and the fact that it feels like a different kind of thing is the trick worth un-learning.

### The one field that actually bites: `step`

Open the panel in a real browser with its developer tools open, watch the Network tab, and look at what actually went out when the panel rendered — Grafana's own response metadata says exactly what step it chose, in `results.A.frames[0].schema.meta.executedQueryString`. Measured on the exact panel above, `Expr: up`, three different ways:

```
"Last 6 hours" range, at the pane's default width  → Step: 30s
"Last 6 hours" range, same query, browser widened to 1920px → Step: 20s
"Last 30 days" range, same panel width as the first → Step: 1h0m0s
```

**The query string never changed. The range changed once, and the panel width changed once, and the step Grafana actually sent changed both times — nobody typed a `step` anywhere.** It is computed, by default, from the **width of the panel in pixels** and the length of the time range, so that a line chart never tries to draw more points than there are pixels to plot them at. That single design decision has a consequence worth sitting with: **the same panel, over two different time ranges — or the same range in a differently-sized browser window — is not answering the same question at the same resolution. It is silently deciding how much of the underlying reality it is willing to show you, based on how many pixels happen to be available to draw it in.**

Six hours of `scrape_interval: 15s` data has roughly 1,440 raw points to work with; the measured 20–30s step above sits close to the scrape interval itself, so a two-minute blip is visible as a real dip in the line. Thirty days of the same data has roughly 172,800 raw points, and no panel is 172,800 pixels wide — the measured `1h0m0s` step is Grafana widening the window until the point count is sane again. **A two-minute outage, six hours ago, is a visible notch. The same two-minute outage, thirty days ago, is averaged into a step thirty times its own length and is not there to see at all** — not hidden by a bug, erased by the same resolution trade-off lesson 03 already taught you to expect from a histogram bucket, arriving again at the level of an entire panel instead of one query.

This is drill-shaped rather than abstract: a dashboard reporting "all clear" over a 30-day window and a raw query over the same incident's actual six-hour span can legitimately disagree, and both are telling the truth about what they were asked to compute.

### The rival: someone else's dashboard, and the variable that silently means nothing

The panel you provisioned above is honest because you know exactly what `up` refers to. The dashboard you inherit from someone else usually is not: a template variable pinned to `namespace=checkout`, built when that namespace existed, still selected in the dropdown after the namespace was renamed or removed. The query still runs. It still returns successfully. It returns **nothing**, for the identical reason lesson 05's alert rule stayed silently `inactive` — a selector matching no series is not an error, it is an empty result — and an empty panel renders in exactly the shade of grey a healthy zero-traffic panel renders in. **"No data" and "healthy and quiet" are, once again, the same picture**, and the only way to tell them apart is to check what the variable currently resolves to, not to trust that the panel would have said something if it mattered.

<details>
<summary>Check yourself — before reading on</summary>

Someone asks why their dashboard "looks fine" during an incident their own users are reporting. They pull up the same panel, zoomed to the last 30 days, and it looks smooth. What is the first thing you would ask them to change, and why?

Zoom in to the actual incident window — the last few hours, not the last 30 days. A 30-day view forces `step` up to keep the point count sane, and a real but brief spike gets averaged into a wide step alongside three weeks of normal traffic; it does not disappear from the underlying data, it disappears from *that specific rendering* of it. The panel was never lying — it was answering "what did the last month look like," and that is a different question from "what is happening right now," even though both are the same query pointed at the same metric.

</details>

**Cleanup:**

```bash
docker rm -f prom-panel graf-panel
```

> **You understand this when you can** state, from memory, the three parameters behind every panel Grafana has ever drawn; explain why the same query over two different time ranges can visibly disagree about whether an incident happened; and say why a dashboard returning "no data" for a renamed namespace looks identical to one reporting a namespace with genuinely nothing going on.

**Which raises:** you can now see a trend and read a query anyone wrote. None of it tells you which of several services, chained together on one request, was the slow one — a metric threw the individual request away by design, on purpose, the moment it became a counter or a histogram.

---

↑ **[Act XI overview](README.md)** · Prev: **[An alert is a loop](05-an-alert-is-a-loop.md)** · Next: **[Which request was slow](06-which-request-was-slow.md)** →
