# Act III drill 1 — "the new API just hangs — no error, nothing"
HINT='the failure was silence rather than a refusal. Name what happened to the packets, or the kind
of route that did it.'
CAUSE_SHA='05993cc5b80907605d20360107a9927f6b7721a5c28759cc43348aa9800c6907
d90ee9ccf6bea1d2942a7b21319338198dec2a746f8a0d0771621f00da2e0864
6bdc2822e10fd576ecafc26cea707a9c3c60f573317bd5da7cc65cedbb9e6c08
d695afc1ad5384842074d4a493c7c2bebc4b0bcf8e7c6a1b45a6a0aac06d59c3
f07516e41b81099ec2b3e15b1c594896386a4b3d87d25e003cf010be1a904771'

lab_up
lab_require "no blackhole route is left for 93.184.216.0/24" \
  '! ip route show | grep -q "blackhole 93.184.216"'
# The discrimination this drill exists for: silence and refusal are different answers, and `ip route
# get` is where the kernel tells you which one it is going to give before you send anything.
lab_require "the kernel now has a real next hop for that range rather than a hole" \
  'ip route get 93.184.216.34 2>&1 | head -1 | grep -qv "unreachable"'
answer_check "${ANSWER:-}"
verdict
