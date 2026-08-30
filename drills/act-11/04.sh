# Act XI drill 4 — the shipper is Running and Ready, and nothing is arriving
HINT='name what /var/log/containers actually contains, and say which absolute path has to be
mounted — matching the host, not renamed — for the entries in it to resolve.'
CAUSE_SHA='99ff6e859bfbff550b9f61def6be092dced85a81f2f5517436a08032bffe6e05
97d151a9a2b1c75a31d1d7e0648a5496c87b876aa9671a0858fb58d0d5df9882
c3a534e0b005afed7080b6cc5c55097351a0bd39266e50cb4837f6ded9af2dc9
cbd26b4f4efd4d9359508e6add7ae64d0016b4f1d809461d84f4d6957279c5c6'

# Prefer a probe that creates something new: a brand-new Pod, mounting /var/log at the same
# absolute path, that actually reads a real log line through the symlink farm.
fixed_mount_reads_a_real_line() {
  local name="verify-drill4-$$"
  kubectl delete pod "$name" --ignore-not-found >/dev/null 2>&1
  cat <<EOF | kubectl apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata: {name: $name}
spec:
  nodeName: netlab-worker
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","cat /var/log/containers/*.log 2>&1 | head -c 40"]
    volumeMounts:
    - {name: varlog, mountPath: /var/log}
  volumes:
  - name: varlog
    hostPath: {path: /var/log}
EOF
  local i out=""
  for i in $(seq 1 30); do
    out=$(kubectl logs "$name" 2>/dev/null)
    [ -n "$out" ] && break
    sleep 1
  done
  kubectl delete pod "$name" --ignore-not-found --wait=false >/dev/null 2>&1
  if [ -n "$out" ]; then ok "a Pod with /var/log mounted at /var/log read a real line through the symlink ($(printf '%s' "$out" | tr -d '\n' | cut -c1-24)...)"
  else bad "a Pod with /var/log mounted at /var/log read a real line through the symlink" "got no output — is netlab-worker reachable and does it have log files under /var/log/pods?"; return 1; fi
}

fixed_mount_reads_a_real_line
answer_check "${ANSWER:-}"
verdict
