# Act XI drill 6 — the crash that mattered is not in kubectl logs
HINT='name what removed the earlier generations before anyone looked, and say why it is not the
same limit as the 10Mi/5-file rotation setting, even though both produce the identical symptom.'
CAUSE_SHA='f146c8344f16433c1ee30e46550bbe443e05e9ce7ccbabc86d13a6917d5f1968
538a7090b565d84e783f3217f7d9b6e75c570a77a5728bd9cfab08528ded957d
957344eca6502193fd0c8ec07367d71f3ae7fa18f2df900a8b55b901575a2563
0f8e0b54bc3d91bb404b31d1bf4b7aa2c7455c586529712111a9b9565f11d629'

# There is no state to repair here — the collection already happened and is expected kubelet
# behaviour, not a bug. What this checks is that the symptom is real and reproducible, not a
# one-off: a fresh crash loop, taken to the same restart count the diagnose page used, still
# loses --previous by then.
gc_window_is_real() {
  local name="verify-drill6-$$"
  kubectl delete pod "$name" --ignore-not-found --wait=true >/dev/null 2>&1
  kubectl apply -f - >/dev/null 2>&1 <<EOF
apiVersion: v1
kind: Pod
metadata: {name: $name}
spec:
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","echo boom; exit 1"]
EOF
  local i rc=""
  for i in $(seq 1 60); do
    rc=$(kubectl get pod "$name" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null)
    [ "${rc:-0}" -ge 2 ] 2>/dev/null && break
    sleep 1
  done
  local out; out=$(kubectl logs "$name" --previous 2>&1)
  kubectl delete pod "$name" --ignore-not-found --wait=false >/dev/null 2>&1
  if ! [ "${rc:-0}" -ge 2 ] 2>/dev/null; then
    bad "reached restartCount>=2 within 60s" "stuck at rc=${rc:-<none>} — CrashLoopBackOff timing may differ on this machine"; return 1
  fi
  case "$out" in
    *"unable to retrieve container logs"*)
      ok "by restart 2, --previous already fails outright (reproduced live)" ;;
    *)
      bad "by restart 2, --previous already fails outright" "got: $out — this kubelet may retain generations longer than the one this drill was built against"
      return 1 ;;
  esac
}

gc_window_is_real
answer_check "${ANSWER:-}"
verdict
