# Act V drill 3 — "the Pod answers on its own IP and refuses through its Service"
HINT='name the thing that held a healthy Pod out of its own Service. It is a spec field with an
owner: something other than the container runtime decided this.'
CAUSE_SHA='db491735c389e52efa8e40e741fd6773ea8d8ae146a7c32c09a93fe207650305
0e06b84496798ba899c50de6eb2efc0b92c62a75e5ba69af7a158cba107352bc
13352562092b900b6a60080b32bb51fa85494482bd790930f2f11c84b6245098'

# Run this *before* the Cleanup line.
rollout_complete cart 2 drill3
endpoints_ready drill3 cart 2
svc_answers drill3 cart
# The check that matters most in this file. Deleting the probe makes every other assertion above pass
# and ships the original bug: an app with no readiness gate is *always* published, including while it
# is still starting. The fix was one string, so the probe must still be there.
require "the readinessProbe is still there — you corrected it, you did not delete it" \
  bash -c 'kubectl -n drill3 get deploy cart \
             -o jsonpath="{.spec.template.spec.containers[0].readinessProbe.httpGet.path}" | grep -q .'
answer_check "${ANSWER:-}"
verdict
