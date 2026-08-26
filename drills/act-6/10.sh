# Act VI drill 10 — "same symptom, and this time the kubelet is running"
HINT='name what was missing from the node — the thing the kubelet needs before it will admit it can
build a Pod sandbox. A directory name is a fine answer.'
CAUSE_SHA='df08d57eecf39eb20ac9177e96c1c14708b9b0872b5a22aa6d7fb225ab182bd4
0589e063bbac8bb997bfe8b4b0cf87fae0c53b2db8921843cd31d78ea242c143
be95b219628dee6b10bfc235f2cb144260ace9a6c590808045f5fc3559c06206
ebce1f14c6396426cfa6ca79130b31bf7dd58c3c42b528c21110d83ef98ae699'

api_answers
nodes_ready 2
require "the node's CNI configuration directory is populated again" \
  bash -c 'docker exec '"$WORKER"' sh -c "ls /etc/cni/net.d/*.conflist /etc/cni/net.d/*.conf 2>/dev/null | grep -q ."'
# This is the check that separates this drill from drill 9. There, nothing ran at all. Here the kubelet
# was up the whole time and could not *network* a Pod — so the claim to test is the address, not the
# phase, and pod_runs_on tests both.
pod_runs_on "$WORKER"
require "nothing left stashed in /tmp/cni" \
  bash -c '! docker exec '"$WORKER"' sh -c "ls /tmp/cni/* 2>/dev/null | grep -q ."'
# The kubelet writes Ready=False with its own reason when it is alive and unhappy, so a clean
# condition is a claim only a working kubelet can make. Unknown here would mean drill 9, not this one.
require_eq "the kubelet is reporting Ready=True itself, not merely un-timed-out" "True" \
  kubectl get node "$WORKER" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
absent "the drill's test Pod is cleaned up" get pod cnitest
answer_check "${ANSWER:-}"
verdict
