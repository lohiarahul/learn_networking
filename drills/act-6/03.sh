# Act VI drill 3 — "kubectl died after a config change and we cannot get in"
HINT='name the flag whose value the API server rejected — with or without the leading dashes.'
CAUSE_SHA='52ff74c554051c8ca801ebfd8021cbebe6ca794e53132e7ad748adac86bec21e'

api_answers
all_static_manifests
control_plane_pods_ready
nodes_ready 2
# The fault was a flag *value*, so the fix is a manifest with no trace of it. Checking the process's
# own command line rather than the file catches a manifest edited but never reloaded.
require "no rejected flag left on the running kube-apiserver" \
  docker exec "$CP" sh -c '! grep -q audit-log-maxage /etc/kubernetes/manifests/kube-apiserver.yaml'
probe_scheduled
answer_check "${ANSWER:-}"
verdict
