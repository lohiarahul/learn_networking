# Act VII drill 9 — "four Pods will not start and the events are a wall"
HINT='one of the four never reached a node at all. Name the field on the *PersistentVolume* that
refused it.'
CAUSE_SHA='8b15ae0510dd87e2650782994be654a1485f75ed3d32f4a4913ca72a7db71e7d
07816c02a1f483a9accaf5161a85446a0eb7257cf8b9a3e2870ccb835e855312
2e41cc8b6621eea9cab643d84f27c15e52b3f8d1792289f8c60f4ec0be9158f0'

# Four faults at four layers. Ready and not phase — see pod_ready() in lib.sh for why.
for p in badkey badmap readonly first-writer second-writer; do
  pod_ready mountlab "$p"
done
# Each has to be fixed at the layer it broke at, so check the layer.
require "the key the first Pod names now resolves in the Secret" \
  bash -c 'k=$(kubectl -n mountlab get pod badkey \
                -o jsonpath="{.spec.containers[0].env[0].valueFrom.secretKeyRef.key}");
           n=$(kubectl -n mountlab get pod badkey \
                -o jsonpath="{.spec.containers[0].env[0].valueFrom.secretKeyRef.name}");
           [ -n "$k" ] && kubectl -n mountlab get secret "$n" -o jsonpath="{.data.$k}" | grep -q .'
require "the ConfigMap the second Pod mounts exists" \
  bash -c 'c=$(kubectl -n mountlab get pod badmap \
                -o jsonpath="{.spec.volumes[0].configMap.name}");
           [ -n "$c" ] && kubectl -n mountlab get configmap "$c" >/dev/null 2>&1'
# The third is only fixed if it still has the read-only mount and stopped writing to it. Deleting the
# volume makes the Pod Ready and deletes the lesson with it.
require "the third Pod still mounts the ConfigMap it was fighting" \
  bash -c 'kubectl -n mountlab get pod readonly -o jsonpath="{.spec.volumes[*].configMap.name}" | grep -q .'
require "and it is writing somewhere writable instead" \
  bash -c 'kubectl -n mountlab exec readonly -- sh -c "ls /etc/conf >/dev/null"'
# The fourth is the punchline: the legal fix is co-location, not a second mount on a second node.
require "both writers of the ReadWriteOnce volume are on one node" \
  bash -c 'a=$(kubectl -n mountlab get pod first-writer -o jsonpath="{.spec.nodeName}");
           b=$(kubectl -n mountlab get pod second-writer -o jsonpath="{.spec.nodeName}");
           [ -n "$b" ] && [ "$a" = "$b" ]'
answer_check "${ANSWER:-}"
verdict
