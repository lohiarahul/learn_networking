# Act XI drill 9 — two complete-looking traces for one request
HINT='say which header has to be copied, unchanged in its trace-id, onto the outgoing request
at every hop — and what a service does with its own trace-id when that header never arrives.'
CAUSE_SHA='5b8c0dfcb4864b044989e419a3bf63b56fda33b1c0e88bc4a148bec13c7b556d
1957f0c32d32df7fab5bd58d08eb9477092d1abfeaeba54e8f441faaffbbb2e0
f3fbf3620cc7a2d91be75b3534e5ea6035b0363775bce531d595f7d5c0f5942d
e2692e86f73952536cadb20920d6ce6451a4dbf51cdef1c3157bb69090c0e01f'

# No state to repair — deploy the three-hop chain fresh, with the header correctly forwarded
# at every step, and confirm one trace-id actually spans all three services' own logs.
trace_spans_all_three() {
  local sfx="$$"
  local ns="verify-drill9-$sfx"
  kubectl create namespace "$ns" >/dev/null 2>&1
  cat > "${TMPDIR:-/tmp}/verify-drill9-svc.py" <<'PY'
import http.server, urllib.request, os, secrets
DOWNSTREAM = os.environ.get("DOWNSTREAM", "")
def mint(trace_id=None):
    return f"00-{trace_id or secrets.token_hex(16)}-{secrets.token_hex(8)}-01"
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        incoming = self.headers.get("traceparent")
        tp = incoming or mint()
        print(f"received traceparent: {tp}", flush=True)
        body = f"tp={tp}\n"
        if DOWNSTREAM:
            trace_id = tp.split("-")[1]
            outgoing = mint(trace_id)
            req = urllib.request.Request(f"http://{DOWNSTREAM}:8080/")
            req.add_header("traceparent", outgoing)
            with urllib.request.urlopen(req, timeout=5) as r:
                body += r.read().decode()
        self.send_response(200); self.end_headers(); self.wfile.write(body.encode())
    def log_message(self, *a): pass
http.server.HTTPServer(("0.0.0.0", 8080), H).serve_forever()
PY
  kubectl -n "$ns" create configmap tracer --from-file=svc.py="${TMPDIR:-/tmp}/verify-drill9-svc.py" >/dev/null 2>&1
  for svc in a:svc-b b:svc-c c:; do
    name="svc-${svc%%:*}"; down="${svc#*:}"
    cat <<EOF | kubectl -n "$ns" apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata: {name: $name, labels: {app: $name}}
spec:
  containers:
  - name: c
    image: python:3.12-slim
    command: ["python3","/app/svc.py"]
    env: [{name: DOWNSTREAM, value: "$down"}]
    volumeMounts: [{name: script, mountPath: /app}]
  volumes: [{name: script, configMap: {name: tracer}}]
---
apiVersion: v1
kind: Service
metadata: {name: $name}
spec:
  selector: {app: $name}
  ports: [{port: 8080, targetPort: 8080}]
EOF
  done
  local i ready=0
  for i in $(seq 1 40); do
    n=$(kubectl -n "$ns" get pods -o jsonpath='{range .items[*]}{.status.phase}{" "}{end}' 2>/dev/null | grep -o Running | wc -l | tr -d ' ')
    [ "${n:-0}" -ge 3 ] && { ready=1; break; }
    sleep 1
  done
  if [ "$ready" != "1" ]; then
    bad "all three services reached Running" "$(kubectl -n "$ns" get pods 2>&1 | tr '\n' ';')"
    kubectl delete namespace "$ns" --wait=false >/dev/null 2>&1
    return 1
  fi
  sleep 2
  kubectl -n "$ns" run curltest --image=python:3.12-slim --restart=Never \
    --command -- sh -c "python3 -c \"import urllib.request; urllib.request.urlopen('http://svc-a:8080/', timeout=5).read()\"; sleep 60" >/dev/null 2>&1
  sleep 5
  local ta tb tc
  ta=$(kubectl -n "$ns" logs svc-a 2>/dev/null | grep -o 'traceparent: 00-[0-9a-f]*' | head -1 | awk -F'-' '{print $2}')
  tb=$(kubectl -n "$ns" logs svc-b 2>/dev/null | grep -o 'traceparent: 00-[0-9a-f]*' | head -1 | awk -F'-' '{print $2}')
  tc=$(kubectl -n "$ns" logs svc-c 2>/dev/null | grep -o 'traceparent: 00-[0-9a-f]*' | head -1 | awk -F'-' '{print $2}')
  kubectl delete namespace "$ns" --wait=false >/dev/null 2>&1
  if [ -n "$ta" ] && [ "$ta" = "$tb" ] && [ "$tb" = "$tc" ]; then
    ok "one trace-id ($ta) appears in all three services' own logs"
  else
    bad "one trace-id spans all three services' logs" "a=${ta:-<none>} b=${tb:-<none>} c=${tc:-<none>}"
    return 1
  fi
}

trace_spans_all_three
answer_check "${ANSWER:-}"
verdict
