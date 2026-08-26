# Act VII drill 2 — "it worked in staging"
HINT='name the one volumeMount field that turned a live-updating symlink into a frozen plain file.'
CAUSE_SHA='868723ec93698afda218fcb1b7949d8465283bcc8e47117b7af66e001df617d2'

# The fix is not "the Pod restarted" — it is "the mount is a directory again, so the kubelet's
# symlink swap can reach it". Read the mount from inside the container, which is where the claim
# is either true or false.
require "the Deployment is available" \
  kubectl rollout status deployment/api --timeout=60s
require "the config is mounted as a directory, not a single file" \
  bash -c 'kubectl exec deploy/api -- sh -c "[ -d /etc/app ]"'
require "and the key inside it is a symlink — which is what makes updates arrive" \
  bash -c 'kubectl exec deploy/api -- sh -c "[ -L /etc/app/MODE ]"'
require "no subPath left anywhere in the Pod template" \
  bash -c '! kubectl get deploy api -o jsonpath="{.spec.template.spec.containers[*].volumeMounts[*].subPath}" | grep -q .'
answer_check "${ANSWER:-}"
verdict
