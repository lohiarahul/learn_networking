# Act VII drill 8 — "the deploy went out and not one Pod ever started"
HINT='four Pods, and two of them share a STATUS. Of the other two, name the one whose STATUS states
its own cause — the only status in the set you never need an event to explain.'
CAUSE_SHA='68749b65ceecd19ec36f4b6221d2fa61e0c391237d931d06fa6a66abb359abe9'

# Four Pods failing at four different depths, and the fix for each is different. Requiring all four is
# the point: a learner who fixed the two easy ones has not done the drill.
#
# Ready and not phase, deliberately. `status.phase` is Running for the crash-looper — the phase
# describes the sandbox, not the processes — and comparing restart counts over a window is worse still,
# because kubelet backoff grows past any window you pick. Ready is the claim that cannot be faked.
for p in badtag badregistry neverpull crashloop; do
  pod_ready imagelab "$p"
done
# And the fourth is only fixed at the layer it broke at: the container refused to start because a key
# it needed was not in the ConfigMap. Rewriting the command to stop checking passes every phase check
# and ships the original bug.
require "the ConfigMap now carries the key the container asked for" \
  bash -c 'kubectl -n imagelab get configmap appcfg -o jsonpath="{.data.settings\.yaml}" | grep -q .'
answer_check "${ANSWER:-}"
verdict
