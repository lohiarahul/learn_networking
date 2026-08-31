# Copying it off the node

Lesson 01 left one wall standing: the only copy of a container's logs lives on the node that ran it, in a directory a ReplicaSet can delete out from under you the instant it deletes the Pod, for entirely healthy reasons. At three Pods, `kubectl logs -l app=web --all-containers --prefix` is a completely reasonable answer — it fans out to every matching Pod's kubelet and prefixes each line with where it came from:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act11.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
kubectl logs -l k8s-app=kindnet --all-containers --prefix --tail=2 -n kube-system
```

```
[pod/kindnet-dqnpn/kindnet-cni] I0830 09:57:27.103502       1 main.go:320] Handling node with IPs: map[172.19.0.3:{}]
[pod/kindnet-dqnpn/kindnet-cni] I0830 09:57:27.103513       1 main.go:347] Node netlab-worker has CIDR [10.244.1.0/24]
[pod/kindnet-pq4dv/kindnet-cni] I0830 09:57:28.929753       1 main.go:320] Handling node with IPs: map[172.19.0.3:{}]
```

That is genuinely the right tool at this scale. At three hundred Pods it is not wrong, exactly — it is a command that streams from three hundred kubelets simultaneously through your one terminal, and the Pod that crashed twenty minutes ago and already lost its `--previous` generation is gone from that stream forever, because `kubectl logs` can only ever ask a kubelet for bytes the kubelet still has. Something has to read those bytes and copy them off the node **while the Pod still exists to be read from** — before deletion, before rotation, before the kubelet's own garbage collector gets there first.

> **Predict first —** you write a Pod that mounts the node's `/var/log/containers` directory and tails every file matching `*.log` inside it. Kubernetes reports the Pod `Running` and `Ready`. Predict how many log lines it actually ships anywhere.

### The shipper you already know how to write

The mechanism is a `hostPath` volume and a loop that watches files for new bytes — a DaemonSet, so one copy runs on every node, reading only that node's own directory. It needs no new primitive: Act VII taught DaemonSet as a workload kind (no `replicas`, a `status` count derived from how many nodes exist instead), Act VI's static-pod manifests and Act X's admission material both already had you read what a `hostPath` mount actually does, and reading a growing file is `tail -F`'s entire job description. The one design choice worth making deliberately is *which* directory to mount, and this is where the prediction above gets settled.

`/var/log/containers/*.log` looks like the natural target — one file per container, named for humans, exactly what you read in lesson 01. Mount only that directory into a Pod and try it:

```bash
kubectl run shipper-broken --image=busybox:1.36 --restart=Never \
  --overrides='{"spec":{"nodeName":"netlab-worker","volumes":[{"name":"c","hostPath":{"path":"/var/log/containers"}}],"containers":[{"name":"c","image":"busybox:1.36","command":["sh","-c","tail -F /var/log/containers/*.log; sleep 3600"],"volumeMounts":[{"name":"c","mountPath":"/var/log/containers"}]}]}}'
sleep 5
kubectl get pod shipper-broken
kubectl exec shipper-broken -- sh -c 'F=$(ls /var/log/containers | head -1); cat "/var/log/containers/$F"'
```

```
NAME             READY   STATUS    RESTARTS   AGE
shipper-broken   1/1     Running   0          5s
cat: can't open '/var/log/containers/kindnet-pq4dv_kube-system_kindnet-cni-…log': No such file or directory
```

**Running. Ready. Every file open fails.** Lesson 01 already told you why, and it is worth re-reading now that it costs you something: every entry in `/var/log/containers/` is a **symlink**, and its target is an **absolute path** — `/var/log/pods/kube-system_kindnet-pq4dv_…/kindnet-cni/0.log`, always starting with `/`. Mount only `/var/log/containers` into a container and the symlink still resolves to that same absolute path, but *inside the container's own filesystem*, where `/var/log/pods` was never mounted at all — so the target simply is not there. `kubectl get pod` cannot see any of this. `READY 1/1` only means the process is alive and answering its probes; it has no opinion about whether that process is reading anything real. **This is the exact shape of the outage this act keeps returning to: everything reports healthy, and the thing you built to find out what happened is itself silently doing nothing.**

The fix is not a different directory — it is mounting *both* real host paths at their own real absolute locations, so the symlink's target actually exists where the container looks for it, or reading `/var/log/pods` directly and skipping the human-friendly names entirely. This shipper does the second, in under twenty lines, tailing every container's log by its real path and pushing each line to a destination with three labels pulled straight out of the path itself — no API call needed for this much:

```bash
cat > "${TMPDIR:-/tmp}/shipper.py" <<'PY'
import glob, time, json, urllib.request

offsets = {}
LOKI = "http://loki:3100/loki/api/v1/push"

def push(ns, pod, container, line):
    body = json.dumps({"streams": [{"stream": {"namespace": ns, "pod": pod, "container": container},
                                     "values": [[str(time.time_ns()), line]]}]}).encode()
    urllib.request.urlopen(urllib.request.Request(LOKI, data=body,
        headers={"Content-Type": "application/json"}), timeout=2).close()

while True:
    for path in glob.glob("/var/log/pods/*/*/*.log"):
        ns, pod = path.split("/")[4].split("_", 1)
        container = path.split("/")[5]
        with open(path) as f:
            f.seek(offsets.get(path, 0))
            for raw in f:
                body = raw.rstrip("\n").split(" ", 3)[-1]
                if body:
                    push(ns, pod, container, body)
            offsets[path] = f.tell()
    time.sleep(1)
PY
```

Loki needs to be reachable by the name `loki` from inside the cluster, so it runs in-cluster too — a Pod and a Service, the same "one container, hand-written config" habit as every other tool in this act, just scheduled by Kubernetes instead of `docker run`:

```bash
cat > "${TMPDIR:-/tmp}/loki-config.yaml" <<'EOF'
auth_enabled: false
server: {http_listen_port: 3100}
common:
  path_prefix: /loki
  storage: {filesystem: {chunks_directory: /loki/chunks, rules_directory: /loki/rules}}
  replication_factor: 1
  ring: {kvstore: {store: inmemory}}
schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index: {prefix: index_, period: 24h}
EOF
kubectl create configmap loki-config --from-file=local-config.yaml="${TMPDIR:-/tmp}/loki-config.yaml"
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: loki, labels: {app: loki}}
spec:
  containers:
  - name: loki
    image: grafana/loki:3.3.2
    args: ["-config.file=/etc/loki/local-config.yaml"]
    volumeMounts: [{name: cfg, mountPath: /etc/loki}]
  volumes: [{name: cfg, configMap: {name: loki-config}}]
---
apiVersion: v1
kind: Service
metadata: {name: loki}
spec:
  selector: {app: loki}
  ports: [{port: 3100, targetPort: 3100}]
EOF
```

Now the shipper, as a ConfigMap holding the script above plus a DaemonSet mounting `/var/log/pods` read-only:

```bash
kubectl create configmap shipper-script --from-file=shipper.py="${TMPDIR:-/tmp}/shipper.py"
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: DaemonSet
metadata: {name: shipper}
spec:
  selector: {matchLabels: {app: shipper}}
  template:
    metadata: {labels: {app: shipper}}
    spec:
      containers:
      - name: c
        image: python:3.12-slim
        command: ["python3","/app/shipper.py"]
        volumeMounts:
        - {name: pods, mountPath: /var/log/pods, readOnly: true}
        - {name: script, mountPath: /app}
      volumes:
      - {name: pods, hostPath: {path: /var/log/pods}}
      - {name: script, configMap: {name: shipper-script}}
EOF
```

It genuinely ships — a real line, from a real kube-system container, with the CRI timestamp and stream tag already stripped by that one `split(" ", 3)[-1]`:

```bash
sleep 10
kubectl exec loki -- wget -qO- --header='Content-Type: application/json' \
  'http://localhost:3100/loki/api/v1/query_range?query=%7Bnamespace%3D%22kube-system%22%7D&limit=1'
```

```json
{"container": "kindnet-cni", "namespace": "kube-system", "pod": "kindnet-pq4dv_fcfe2152-…"}
"I0830 09:37:18.944611       1 main.go:347] Node netlab-control-plane has CIDR [10.244.0.0/24]"
```

Twenty lines, and Fluent Bit, Promtail and Vector all stop being names on a slide — they are more careful, more configurable, restart-safe versions of exactly this loop, the same relationship Prometheus has to lesson 04's six lines.

### Three walls this loop hits immediately, each one real

**1. Which Pod actually said this?** The path gave you namespace, Pod name and container for free, because the kubelet already encodes them there. Anything *not* in the path — which Deployment owns this Pod, which node, which labels a human attached for routing — is not in the log file at all, and getting it means asking the API server, which means the shipper needs its own `ServiceAccount` and a `ClusterRole` scoped to read Pods, the identical shape lesson 04 built for Prometheus to read the kubelet. Enrichment is not a shipper feature. It is Act IX's subject, arriving again because a filename can only ever tell you so much.

**2. The shipper itself restarted. Where had it got to?** Read the script again: `offsets` is a plain dictionary, held in memory, gone the instant the process exits. Prove it rather than take the sentence on faith — log exactly one line, once, and confirm it was shipped exactly once:

```bash
kubectl run onelogger --image=busybox:1.36 --restart=Never --command -- sh -c "echo UNIQUE_MARKER_7f3a9; sleep 3600"
sleep 5
kubectl exec loki -- wget -qO- --header='Content-Type: application/json' \
  'http://localhost:3100/loki/api/v1/query_range?query=%7Bpod%3D~%22onelogger.%2B%22%7D%20%7C%3D%20%22UNIQUE_MARKER_7f3a9%22&limit=100' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(len(s['values']) for s in d['data']['result']))"

kubectl delete pod -l app=shipper --wait=true   # DaemonSet recreates it immediately
sleep 10
kubectl exec loki -- wget -qO- --header='Content-Type: application/json' \
  'http://localhost:3100/loki/api/v1/query_range?query=%7Bpod%3D~%22onelogger.%2B%22%7D%20%7C%3D%20%22UNIQUE_MARKER_7f3a9%22&limit=100' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(len(s['values']) for s in d['data']['result']))"
```

```
1
2
```

**One occurrence in the source. Two in the destination**, the second appearing the moment the DaemonSet's replacement Pod comes up and reopens every file from byte zero, because nothing on disk told it where it had left off. The honest fix is a checkpoint file — the current offset for each path, written periodically to something that survives a restart, exactly the shape a real message queue consumer uses. And the honest ceiling on that fix is a genuine new distinction, worth naming precisely rather than glossing over: a checkpoint written *after* forwarding a line risks losing it if the process dies in the gap between sending and checkpointing — call that **at-most-once**, because the line is forwarded zero or one times, never more, and the failure mode is a silent gap; a checkpoint written *before* forwarding, or forwarding an unacknowledged line again on restart, risks sending it twice — **at-least-once**, the exact duplicate this measurement just produced, where the failure mode is a repeat rather than a loss. There is no third option that is both simple and free of one of these two failure modes. Every serious log pipeline picks at-least-once and accepts the duplicates, because during an incident a missing line is a worse failure than a repeated one — the same trade-off Act III's TCP material made for you once already, at a different layer, when it chose retransmission-with-possible-duplicates over silently dropping a packet.

**3. It does not fit.** Ship every line from a moderately busy cluster for a month and the destination has to hold every one of them, indexed well enough to find one during an incident, which is a bill that scales with total traffic rather than with anything you actually asked about.

### Loki, kept for exactly one decision

The obvious answer to "index it so I can search it" is to index everything — Elasticsearch's approach, and it is not wrong, it is priced differently: full-text indexing every log line makes *search* fast at the cost of making *ingestion* expensive, and the cardinality problem lesson 04b measured for metrics arrives here too, except now it is inverted — indexing structure derived from unbounded log content rather than from a label you chose. **Loki indexes the labels, not the line.** Query by `{namespace="kube-system", container="kindnet-cni"}` and Loki looks up exactly those two label values in a small index — the same kind of lookup as any of this act's earlier label-keyed queries — then fetches the handful of compressed chunks that combination actually wrote to, and only *then* does a full scan for content inside them:

```bash
kubectl port-forward svc/loki 3100:3100 &
logcli --addr=http://localhost:3100 query '{namespace="kube-system"} |= "error"' --since=15m
```

`|= "error"` is not an index lookup. It is a `grep` run over every byte in the chunks the label selector already narrowed down to — fast when the label selector is specific, and a full scan of everything under that label if it is not. Confirm the index really is only the labels, nothing about content:

```bash
curl -s http://localhost:3100/loki/api/v1/labels
```

```json
{"status":"success","data":["container","namespace","pod","service_name"]}
```

**Four label names, total, regardless of how many distinct messages any container has ever logged.** That is the entire index. Everything else about a search — the word "error," a request ID, a stack trace — is a scan, every time, over whatever the label selector already narrowed down. Loki trades index-everything's ingestion cost for search cost on the unindexed part, and the trade is a bet that you will usually know roughly *where* to look (which namespace, which container) even when you do not yet know *what* you are looking for.

<details>
<summary>Check yourself — before reading on</summary>

A teammate wants to add a label for `request_id` to every log line, so they can jump straight to one request's logs by label instead of by `|=`. Good idea?

No — for the same reason lesson 04b's Predict-first block existed. A `request_id` is unique per request by definition, so labeling by it recreates the metrics cardinality explosion inside the log store: one label value per request means one stream per request, forever, and Loki's index grows without bound in exactly the shape a metrics label did. The fix is to keep `request_id` **inside the line**, searchable with `|=` or a structured-log parser stage, and reserve labels for the small, bounded set of things you would actually want to filter a dashboard by — namespace, container, environment — the same bounded-versus-unbounded distinction lesson 04b already made you price once.

</details>

<!-- figure -->
```
   A LOG SHIPPER IS A LOOP TOO, AND IT INHERITS EVERY WALL A LOOP HAS

   THE PREDICTION, SETTLED
     mount /var/log/containers only, tail its symlinks ->
     Running, Ready, EVERY open fails: symlink target is an ABSOLUTE
     path into /var/log/pods, which was never mounted. Zero lines shipped.
     fix: mount /var/log/pods directly, read the real files.

   THREE WALLS, EACH MEASURED
     1. WHICH POD SAID THIS -- path gives ns/pod/container for free.
        anything else (labels, owner) needs the API server: ServiceAccount + RBAC.
     2. RESTARTED, LOST ITS PLACE -- in-memory offsets, no checkpoint.
        measured: one unique line shipped ONCE, TWICE after a restart.
        at-least-once (duplicates) beats at-most-once (silent gaps).
     3. DOES NOT FIT -- keep every line, bill scales with total traffic.

   THE FIX, PRICED AGAINST THE OBVIOUS ONE
     index everything (Elasticsearch) -- fast search, expensive ingest,
       and the log's own content becomes an unbounded cardinality problem.
     Loki: index ONLY 4 label names, total, ever. |= is a GREP over
       chunks the label lookup already narrowed down -- not an index hit.

   LEAVES OPEN
     you now keep every line, and the bill scales with traffic.
     nobody can answer "how many requests per second" without
     reading all of them.
```

**Cleanup:**

```bash
kubectl delete daemonset shipper --ignore-not-found
kubectl delete pod shipper-broken onelogger loki --ignore-not-found
kubectl delete configmap loki-config shipper-script --ignore-not-found
kubectl delete service loki --ignore-not-found
```

> **You understand this when you can** explain exactly why mounting `/var/log/containers` alone ships nothing, using the word "absolute"; describe what a log shipper needs beyond the file path to answer "which Deployment," and why that need is an RBAC problem and not a parsing problem; reproduce the duplicate-line measurement in your own words and say which failure mode it trades away; and state, in one sentence, what Loki indexes and what it grep's.

**Which raises:** you now keep every line, forever, and the bill scales with total traffic rather than with anything you actually wanted to know. Nobody can answer "how many requests per second" by reading a log — that question needs a different shape of answer entirely, one that never keeps the individual line in the first place.

**New tools in this lesson:** `Loki`, `logcli`. **Exam value: none.** Neither the CKA nor the CKS curriculum mentions a log aggregation backend by name — this lesson's node-file section (`hostPath`, `/var/log/pods`, the symlink farm) is the exam-relevant half of the act, and you already read it in lesson 01.

---

↑ **[Act XI overview](README.md)** · Prev: **[Nothing here remembers](01-nothing-here-remembers.md)** · Next: **[A number a process keeps](03-a-number-a-process-keeps.md)** →
