# Act VI drill 9 — "the node went NotReady and the app is still up"
HINT='name the process that stopped. It is the one that writes the Node object, and it is not on the
control plane.'
CAUSE_SHA='1ca4bc7eb9b3d6f1e205da9cfab437c89d3760d0765a29a6bcbccf4ad51a2cb1'

api_answers
nodes_ready 2
require "the worker's kubelet is running again" \
  bash -c '[ "$(docker exec '"$WORKER"' systemctl is-active kubelet 2>/dev/null)" = "active" ]'
# Ready is a *field* the kubelet writes, so a Node reading Ready is not evidence the kubelet is back —
# it is evidence the kubelet was there when it last wrote. The lease is the liveness signal, and a Pod
# that actually starts on the node is the proof.
require "the worker is renewing its node lease (Ready is fresh, not stale)" \
  bash -c 'r=$(kubectl -n kube-node-lease get lease '"$WORKER"' -o jsonpath="{.spec.renewTime}" 2>/dev/null);
           [ -n "$r" ] || exit 1
           now=$(date -u +%s)
           then=$(date -u -j -f "%Y-%m-%dT%H:%M:%S" "${r%%.*}" +%s 2>/dev/null || date -u -d "${r}" +%s)
           [ $(( now - then )) -lt 60 ]'
pod_runs_on "$WORKER"
absent "the drill's Deployment is cleaned up" get deployment frontline
answer_check "${ANSWER:-}"
verdict
