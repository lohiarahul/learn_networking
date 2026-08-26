# Act VI drill 2 — "the dashboard says everything is healthy and it is not"
HINT='name the control-plane component that was missing (one word, or its kube-* name).'
CAUSE_SHA='8e663fd2f3a9e63df0e89ebcfb23f3e005c013708861c3243185e469fab299d5
7250f14be60cf2f5acfa1bc4ad67e164c11c212baae29823a274765cb6d791bc'

# This drill's whole lesson is that a *status field* lies when its writer is gone. So the check must
# watch a field move on an object that did not exist before now — a stale 3/3 cannot fake that.
all_static_manifests
control_plane_pods_ready
probe_controller_writes
absent "the drill's Deployment is cleaned up" get deployment payments
require "no manifest left stashed in /tmp/drill" \
  docker exec "$CP" sh -c '[ ! -e /tmp/drill/kube-controller-manager.yaml ]'
answer_check "${ANSWER:-}"
verdict
