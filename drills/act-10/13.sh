# Act X drill 13 — the rule is loaded and nothing fires
HINT='name the thing that answered "no" after the file, the syntax and the condition all answered
"yes" — it is not in the rules file.'
CAUSE_SHA='3fdb78c2d0044014568d9d3299a22298088c5f0aebf43b40134def1e232afccf
36ffd196906e78d9dd2de36ad6c905ccd7226d9a981dbd79c44d5bf00a9a989c
dff4e957e476dc3836994b9babe5c62a0759e3306a54a597f3e59039ff345236
4c8767af08b983f9734176901604688d0eeed62d9b2e913261895649cf546f9a
7ca5a934018839972ce4ecf7ae2acbe08f2e9f3a4a6f89cac0212552e906dd2f
7c861d232c054236217f5b76907756483220d7281e16cf4d4417cd3e46fccb42
0c57efdf408f0a26b66967d143330b922af540bacc8ca1c0b42475879f336728
d67e4787215decf1010e479094f22e1628ccab29e9570e70300219832a4ebbcc
c2b53dfcc678e5e9592f8503505eb751d981f07aa7bc547e0ee5cbabc728e57d
5f0326d68e444c72b96dac7b2df5e0245497e92565bce3c72bcfe41f82737cea
4a107058be445e6a002d4c6022d5e74a233247a1de0bdd0a5c3b4c469322e12a
158ca69a671a1ff23247aff05042197d2c0f3c0a80f12c3586f6be70c1ec51b3'

# Run this WHILE FALCO IS STILL INSTALLED, before the drill's tear-down.
#
# The only statement that means "the rule is on" is an alert, so nothing here reads the values file or
# the rules file to decide whether the fix worked. It builds its own Pod, writes the credential file,
# reads it with a process that is not the application, and requires the line to appear. Three of the
# five checks are there to separate the good fix from the two that also produce an alert:
#
#   * the /dev/shm probe is the control — it proves the sensor is attached, so a missing credential
#     alert is a rules decision and not a broken driver. A learner whose Falco is simply unhealthy
#     gets told that instead of being told their rule is wrong.
#   * the tag check catches the fix that works by lying: dropping `filesystem` from the rule's tags
#     re-enables it and makes it invisible to every future selection on that tag.
#   * the /etc/shadow probe catches the fix that works by exception: `disable: {tag: filesystem}`
#     followed by `enable: {rule: <yours>}` turns your rule back on and leaves every *other*
#     filesystem rule off, which is the state the ticket started in with a narrower blast radius.
api_answers

FALCO_NS=${FALCO_NS:-falco}
NS="verify-rule-$$"

falco_alerts() {  # falco_alerts <seconds-back>
  kubectl logs -n "$FALCO_NS" ds/falco -c falco --since="${1}s" 2>/dev/null
}

if ! kubectl -n "$FALCO_NS" get ds/falco >/dev/null 2>&1; then
  bad "Falco is installed in namespace '$FALCO_NS'" \
      "no DaemonSet ds/falco. This verifier runs BEFORE the drill's tear-down, while Falco is still up. If you installed it elsewhere, re-run with FALCO_NS=<ns>."
  answer_check "${ANSWER:-}"
  verdict
fi

require "the Falco DaemonSet is rolled out on every node" \
  kubectl -n "$FALCO_NS" rollout status ds/falco --timeout=120s

# ---- the probe Pod. The file is written by a shell so that fd.name is the literal path; a Secret
# ---- volume would give the kubelet's projected symlink and is a different (real) problem.
cleanup_rule() { kubectl delete namespace "$NS" --wait=false >/dev/null 2>&1; }
kubectl create namespace "$NS" >/dev/null 2>&1
kubectl -n "$NS" run creds --image=busybox:1.36 --restart=Never --command -- \
  sh -c 'mkdir -p /etc/app && echo hunter2 > /etc/app/db-password && sleep 600' >/dev/null 2>&1
if ! kubectl -n "$NS" wait --for=condition=Ready pod/creds --timeout=120s >/dev/null 2>&1; then
  bad "the probe Pod starts" "pod/creds in $NS never became Ready — nothing below can be measured"
  cleanup_rule; answer_check "${ANSWER:-}"; verdict
fi

# ---- control: a shipped rule with no `filesystem` tag. If this does not fire, the sensor is the
# ---- problem and every other result below is meaningless.
kubectl -n "$NS" exec creds -- sh -c 'cp /bin/busybox /dev/shm/x && /dev/shm/x ls / >/dev/null' >/dev/null 2>&1
# ---- target: the rule the drill is about.
kubectl -n "$NS" exec creds -- cat /etc/app/db-password >/dev/null 2>&1
# ---- and a shipped rule that IS tagged filesystem.
kubectl -n "$NS" exec creds -- cat /etc/shadow >/dev/null 2>&1
sleep 12
LOG=$(falco_alerts 90)

if printf '%s' "$LOG" | grep -qi '/dev/shm'; then
  ok "the sensor is attached — a shipped rule fired from inside the probe Pod"
else
  bad "the sensor is attached (control probe)" \
      "no /dev/shm alert, so Falco is not seeing syscalls on this node. Fix that before believing anything about a rule: kubectl logs -n $FALCO_NS ds/falco -c falco | grep -i 'event sources'"
fi

if printf '%s' "$LOG" | grep -qi 'credential'; then
  ok "and your rule fired on a credential read by a process that is not the application"
else
  bad "your rule fires on a credential read" \
      "no alert matching /credential/ after cat /etc/app/db-password by 'cat'. The rule is loaded and something is still selecting it off — read Falco's startup log, not the rules file."
fi

# The fix that works by lying. Read the tags off the rule as Falco has it, not off your source file.
TAGS=$(kubectl exec -n "$FALCO_NS" ds/falco -c falco -- \
         sh -c 'cat /etc/falco/rules.d/*.yaml 2>/dev/null' 2>/dev/null)
if printf '%s' "$TAGS" | grep -q 'filesystem'; then
  ok "the rule still declares itself a filesystem rule"
else
  bad "the rule still declares itself a filesystem rule" \
      "no 'filesystem' tag left in /etc/falco/rules.d. Dropping the tag does make the alert come back, and it makes the rule invisible to every future selection on that tag — you fixed the symptom by mislabelling the rule."
fi

# The fix that works by exception. Under `disable: {tag: filesystem}` + `enable: {rule: yours}`, this
# one stays off.
if printf '%s' "$LOG" | grep -qiE 'sensitive file|shadow'; then
  ok "and the shipped filesystem rules are working too — the blanket disable is gone, not worked around"
else
  bad "the shipped filesystem rules are working too" \
      "cat /etc/shadow produced no alert, so 'disable: {tag: filesystem}' is still in force and your rule was re-enabled by name. That leaves every other filesystem rule off, which is the state the ticket started in. Silence the noisy workload instead: append its image to read_sensitive_file_images."
fi

cleanup_rule
answer_check "${ANSWER:-}"
verdict
