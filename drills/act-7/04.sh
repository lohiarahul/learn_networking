# Act VII drill 4 — "we scaled it down but the bill didn't move"
HINT='name the kind of object nothing cleaned up when the StatefulSet shrank (kubectl short name is
fine).'
CAUSE_SHA='faf78c6d99be47c7e566f063d1339e3f088c3039a33407c797eddd799a7b6ca9
66c37f80d0ff6187bf12fc360a617ce7cd2b05482ae9241a263127259021c82b
e4786ba10eab7f95b3a8565d1356352ca286826f653d5edc9be4ac5f87543b78
e7d5f0d90750b0899862e58564112a4d47ee60670aeb01a85cd64f497c2500ac'

# The trap in this drill is over-deleting: data-cache-0 belongs to the replica that is still running,
# and a learner who deleted all three has destroyed live storage. So check both directions.
require "the surviving replica still has its claim" \
  kubectl get pvc data-cache-0
absent "the orphaned claim data-cache-1 is gone" get pvc data-cache-1
absent "the orphaned claim data-cache-2 is gone" get pvc data-cache-2
require "the StatefulSet's one replica is still serving" \
  bash -c '[ "$(kubectl get sts cache -o jsonpath="{.status.readyReplicas}")" = "1" ]'
answer_check "${ANSWER:-}"
verdict
