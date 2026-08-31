# Act VI drill 13 — "the kubelet will not start and there is nothing in the log"
#
# The trap this verifier has to close: a learner can make the symptom go away by deleting the
# `ConditionPathExists` line from the unit, which starts the kubelet and leaves the node with no
# config-file guard at all. So check 2 asserts the condition is still *there* and now *met* — the
# condition passing is the fix; the condition being absent is a second fault.
HINT='say why systemd did not run it, in terms of what it checked before starting.'
CAUSE_SHA='b040b4064112440135178164ae1b4bede80de7a30d6c988f3365dbe9a91eaa1d
a03d174400bdda69a963b4f2852f35cecaec99b661b6a5b1bf7cb125fbb2241e
509dea2ae352c9f213fe55ad1b275df8b52c5d61e45386d8b1876fc661d63f28
624a43a2013f909c7a5401462b9b6e6f2ad86558f1c42adf97f6a21b00d26ccd
401959fac26d5d984c72a4865d56ce9bc36d03f6a57635b14b011f2e7d1cfd7c
bfd61066fa21b94b97dc850881e71dce4799b371c5a10a557dc8706babaeb799
ad547cc025a97f2a5f6f05a0a1f751dc8e3346763ec8f472d3975541f475e109
dcac46527196776e1b9b23d5b276e119e7254740176907a524100412c773a461'

require "the file the condition names is back where the unit expects it" \
  docker exec "$WORKER" test -f /var/lib/kubelet/config.yaml

# The condition must still be in the unit. Removing it also "fixes" the symptom, and is worse than
# the bug: the next missing config file becomes a crash loop instead of one clear line.
require "the ConditionPathExists guard is still in the unit (not deleted to force a start)" \
  sh -c 'docker exec '"$WORKER"' systemctl cat kubelet | grep -q "^ConditionPathExists=/var/lib/kubelet/config.yaml"'

require "and systemd now evaluates that condition as met" \
  sh -c 'docker exec '"$WORKER"' systemctl show kubelet -p ConditionResult | grep -qx "ConditionResult=yes"'

require "the kubelet is running" \
  docker exec "$WORKER" systemctl is-active --quiet kubelet

# Function, not configuration: a kubelet that is `active` but never registered leaves the node
# NotReady, which is the symptom the ticket actually reported.
require "the node has gone back to Ready — the kubelet is registering, not merely started" \
  sh -c '[ "$(kubectl get node '"$WORKER"' --no-headers 2>/dev/null | awk "{print \$2}")" = "Ready" ]'

answer_check "${ANSWER:-}"
verdict
