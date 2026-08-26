# Act VII drill 7 — "the scheduler says we are out of nodes"
HINT='name the PVC field that named something the cluster does not have.'
CAUSE_SHA='f8ee1ec3ae03b0550ba7edef92e28e8a62ade905e9045db34369f7fe88ed35a9
2d80e58855b3ab22ca6bc26902515b389fe678199ac5eac88ac95998b4318d84'

require "the claim is Bound" \
  bash -c '[ "$(kubectl get pvc reports-data -o jsonpath="{.status.phase}")" = "Bound" ]'
require "it bound through a StorageClass that actually exists" \
  bash -c 'sc=$(kubectl get pvc reports-data -o jsonpath="{.spec.storageClassName}");
           [ -z "$sc" ] || kubectl get storageclass "$sc" >/dev/null 2>&1'
rollout_complete reports 1
require "and the volume is really mounted in the container" \
  bash -c 'kubectl exec deploy/reports -- sh -c "mount | grep -q /data"'
answer_check "${ANSWER:-}"
verdict
