# Act IV drill 1 — "the new container can reach the host but not the internet"
HINT='the packet left carrying an address the internet cannot route back to. Name the rule that was
supposed to change it.'
CAUSE_SHA='ef21b5592240dac8ae10469ea5d728b97ff59c1a7785c4f1a870513ee187e387
a037dd31a4075646cdfada55ad668635f1247fa4481bf27c3a415ff94b556b5f
6d060a3085b8c3c84ba2f904262af10e7f4f90286b1b78701606cc66fe73bc75
04d2077fb33c409dbb0b063ded4b3211612688de17e0c26c132d75092b64d97e
43c944ebc3856e47fc4ada5150c447882aa612e843229b98116f33e3245230a8'

# Run this before the drill's Cleanup block — everything it reads lives in namespace `app`.
lab_up
lab_require "the drill's namespace still exists to test" 'ip netns list | grep -q "^app"'
# Function: the namespace reaches the internet. This is the only claim that matters and it needs no
# reading of any table.
ns_require "a Pod-shaped namespace now reaches 8.8.8.8" app 'ping -c1 -W3 8.8.8.8 >/dev/null'
# And at the right layer. Giving the namespace a routable address, or routing it some other way, also
# fixes the ping — and is not the rule Docker and kube-proxy write.
lab_require "and the fix is a source-NAT rule for the namespace's range, not a re-addressing" \
  'iptables -t nat -S POSTROUTING | grep -E "10\.50\.0\.0/24" | grep -Eq "MASQUERADE|SNAT"'
answer_check "${ANSWER:-}"
verdict
