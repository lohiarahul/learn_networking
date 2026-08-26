# Act X drill 5 — what happened inside the shell
HINT='quote the response code that explains the difference, or name what the connection became.'
CAUSE_SHA='16dc368a89b428b2485484313ba67a3912ca03f2b2b42429174a4f8b3dc84e44
160e2d8104adac89031c7cdf3bc933b89ccfc6ca0eafb94d971835f5aa8dc8a6
ce48a69c0fdc284767c7c2559bf0745efc8a086fc6faa428d6bdb4a3b2b9342e
9f27ea437f540fdadf5d9b0aa3770c261911af348de7de5edaabfa23f0cc8f9f'

# Run this while bench B is still up. There is nothing to repair, so the check is the measurement: run
# both shapes of exec and require the log to show exactly the asymmetry the answer claims. A learner who
# thinks the commands are "in the log somewhere" gets to watch the second one not be there.
api_answers
require "bench B's audit log exists and is not empty" \
  docker exec "$CP" sh -c 'test -s /var/log/kubernetes/audit.log'
NS="verify-exec-$$"
kubectl create namespace "$NS" >/dev/null 2>&1
kubectl -n "$NS" run t --image=busybox:1.36 --restart=Never --command -- sh -c 'sleep 300' >/dev/null 2>&1
kubectl -n "$NS" wait --for=condition=Ready pod/t --timeout=120s >/dev/null 2>&1
kubectl -n "$NS" exec t -- sh -c 'echo ARGS-IN-THE-URI' >/dev/null 2>&1
printf 'echo NOTHING-WILL-RECORD-THIS\nexit\n' | kubectl -n "$NS" exec -i t -- sh >/dev/null 2>&1
sleep 4
LOG=$(docker exec "$CP" sh -c "grep '$NS/pods/t/exec' /var/log/kubernetes/audit.log" 2>/dev/null)
kubectl delete namespace "$NS" --wait=false >/dev/null 2>&1
if printf '%s' "$LOG" | grep -q 'ARGS-IN-THE-URI'; then
  ok "the argv-style exec is legible in the log — kubectl put it in the query string"
else
  bad "the argv-style exec is legible in the log" "no exec entry carrying its arguments was found"
fi
if printf '%s' "$LOG" | grep -q 'NOTHING-WILL-RECORD-THIS'; then
  bad "and the interactive exec's commands are absent from the log" \
      "a command typed into the stream was recorded, which contradicts the drill — read the entry"
else
  ok "and the interactive exec's commands are absent — the log stopped where the stream started"
fi
if printf '%s' "$LOG" | grep -q '"code":101'; then
  ok "the entry that explains it is there: code 101, Switching Protocols"
else
  bad "an exec entry with code 101 is in the log" "found no 101; the upgrade is the thing to read"
fi
answer_check "${ANSWER:-}"
verdict
