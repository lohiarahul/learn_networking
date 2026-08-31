# Act XI drill 5 — the stack trace in the log store is three broken lines
HINT='name the tag the container runtime writes on a record it had to split, and say which
tool already knows how to undo the split.'
CAUSE_SHA='7536e5d0cc609eac581e88ffd4b2262ecb8edb72e5be095e0a03b3e90346f4aa
28390fecb136f90bc32ec459525bd664cd5be84964d016d893760caa0a1f67a0
0f3351a26bc736727f2288e4fa29c8cf814f8acd8d62d54acec709978f47624f
446c77f8527e69da0adc241a9879a93294e36a3b86254fa7e118512778c00d10'

# No state to repair — reproduce the split live, and confirm the one tool that already
# reassembles it (kubectl logs) actually does, on a fresh line every time this runs.
long_line_reassembles() {
  local name="verify-drill5-$$"
  kubectl delete pod "$name" --ignore-not-found --wait=true >/dev/null 2>&1
  kubectl run "$name" --image=busybox:1.36 --restart=Never \
    --command -- sh -c "awk 'BEGIN{s=\"\"; for(i=0;i<70000;i++)s=s\"x\"; print s}'; sleep 600" >/dev/null 2>&1
  local i node uid dir
  for i in $(seq 1 30); do
    node=$(kubectl get pod "$name" -o jsonpath='{.spec.nodeName}' 2>/dev/null)
    [ -n "$node" ] && break
    sleep 1
  done
  uid=$(kubectl get pod "$name" -o jsonpath='{.metadata.uid}' 2>/dev/null)
  for i in $(seq 1 20); do
    dir=$(docker exec "$node" sh -c "ls /var/log/pods/ 2>/dev/null | grep '$uid'")
    [ -n "$dir" ] && break
    sleep 1
  done
  if [ -z "$node" ] || [ -z "$dir" ]; then
    bad "the pod's raw log directory appeared on its node" "node='${node:-<none>}' dir='${dir:-<none>}'"
    kubectl delete pod "$name" --ignore-not-found --wait=false >/dev/null 2>&1
    return 1
  fi
  local rawlines pcount
  rawlines=$(docker exec "$node" sh -c "wc -l < /var/log/pods/$dir/$name/0.log" 2>/dev/null | tr -d ' ')
  pcount=$(docker exec "$node" sh -c "grep -c ' P ' /var/log/pods/$dir/$name/0.log" 2>/dev/null)
  local reassembled
  reassembled=$(kubectl logs "$name" 2>/dev/null | wc -c | tr -d ' ')
  kubectl delete pod "$name" --ignore-not-found --wait=false >/dev/null 2>&1
  if [ "${rawlines:-0}" -lt 2 ] || [ "${pcount:-0}" -lt 1 ]; then
    bad "the raw log file on the node holds more than one record for this one write" "rawlines=${rawlines:-0} p-records=${pcount:-0} — this runtime may chunk at a different size"
    return 1
  fi
  ok "the raw file split one write into $rawlines records ($pcount tagged 'P' — partial)"
  if [ "${reassembled:-0}" -ge 70000 ]; then
    ok "kubectl logs reassembled them back into one line ($reassembled bytes) — this is the mechanism a shipper has to copy"
  else
    bad "kubectl logs reassembled the fragments into one full-length line" "got $reassembled bytes, expected at least 70000"
    return 1
  fi
}

long_line_reassembles
answer_check "${ANSWER:-}"
verdict
