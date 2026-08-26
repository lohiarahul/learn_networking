# Act VI drill 1 — "kubectl works, but nothing we deploy ever starts"
HINT='name the control-plane component that was missing (one word, or its kube-* name).'
CAUSE_SHA='fffb3b216f41fe763b909866ddcd6fda977db3a317dd8bfa088e4ee0e12ddb0e
a02ba163f3a02db22fdd14b310119f1a4c2f9e4a773a573f757904dd5433d4dd'

# State: not "is the file back" — is anything *placing* Pods. A Pod that acquires a nodeName is the
# only evidence that survives someone restoring a file into the wrong directory.
all_static_manifests
control_plane_pods_ready
probe_scheduled
absent "the drill's Deployment is cleaned up" get deployment shipping
require "no manifest left stashed in /tmp/drill" \
  docker exec "$CP" sh -c '[ ! -e /tmp/drill/kube-scheduler.yaml ]'
answer_check "${ANSWER:-}"
verdict
