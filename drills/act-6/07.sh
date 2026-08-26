# Act VI drill 7 — "the node is fine and the cluster says it does not exist"
HINT='name the process that has to be poked to recreate the Node object. It registers once, at
startup, which is the whole trap.'
CAUSE_SHA='1ca4bc7eb9b3d6f1e205da9cfab437c89d3760d0765a29a6bcbccf4ad51a2cb1'

api_answers
nodes_ready 2
require "the worker Node object exists again" kubectl get node "$WORKER"
# The trap is a Node that comes back Ready but takes no work, so prove placement, and prove it landed
# on the node that had gone missing rather than on the control plane.
require "the worker is schedulable and takes new Pods" bash -c '
  kubectl run verify-w7 --image=busybox:1.36 --restart=Never \
    --overrides="{\"spec\":{\"nodeName\":\"'"$WORKER"'\"}}" --command -- sh -c "sleep 60" >/dev/null 2>&1
  for i in $(seq 1 45); do
    p=$(kubectl get pod verify-w7 -o jsonpath="{.status.phase}" 2>/dev/null)
    [ "$p" = "Running" ] && break; sleep 1
  done
  kubectl delete pod verify-w7 --force --grace-period=0 --wait=false >/dev/null 2>&1
  [ "$p" = "Running" ]'
answer_check "${ANSWER:-}"
verdict
