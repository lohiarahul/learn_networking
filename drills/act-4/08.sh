# Act IV drill 8 — "the runbook's first command says the namespace does not exist"
#
# Nothing was ever broken here, which is the drill. So the checks cannot ask "is it repaired" — they
# ask whether the learner made the runbook's own command work *against the container that was always
# there*, and whether they left the container running rather than deleting the thing they could not
# reach. Function, not configuration: the last check runs `ip netns exec` and compares the inode it
# lands in against the container's, so a stray `/var/run/netns/drillbox` pointing at the wrong
# namespace fails.
HINT='say what ip netns can and cannot see, and what makes the difference.'
CAUSE_SHA='e9bc352fa5d9d5b31b0d2d79f372381f4ed274904ff3f95f76ea6be442f615ee
c9c351d5111e64ba9a6b2363bc0192aacda24b50e5d3ab40aed87cbee3c09d2d
e7fd4dac1802f9e4a6fc36f0d5dfdf39e6c873290a157454b5a25a7f3beebd79
9b72376c2f09e61062af22493880100f625dfa9348396c8884f449811ada798d
0544ba3dae492be7dca93d94bb59915f973fd3dd3832e8c5cbad612026a5e538
8f17a085ed2b05f0131770b96e5be4f7e4cfa930fe564be20eae72fb91b139b6
0755cdb16397e4542b4828ad0b9f6ffa446a8edb69096350c88d7f9973dc2c20
82919895fd696799520e4db0e4cb0fef4f2f84eff6dc598126335e90411c2de3'

lab_up
lab_require "the container the ticket is about is still running (not deleted to make the error go away)" \
  'runc list 2>/dev/null | grep drillbox | grep -q running'
# The container's namespace was always distinct. Assert it, so a learner who "fixed" this by removing
# the network namespace from config.json fails rather than passes.
lab_require "and it still holds a network namespace of its own" \
  'PID=$(runc state drillbox 2>/dev/null | jq -r .pid); [ -n "$PID" ] && [ "$PID" != null ] &&
   a=$(readlink /proc/$PID/ns/net) && b=$(readlink /proc/self/ns/net) && [ "$a" != "$b" ]'
# The runbook command itself, run for real, landing in the right namespace.
lab_require "you can now reach that namespace by the name the runbook uses, and it is the right one" \
  'PID=$(runc state drillbox 2>/dev/null | jq -r .pid);
   want=$(readlink /proc/$PID/ns/net);
   got=$(ip netns exec drillbox readlink /proc/self/ns/net 2>/dev/null);
   [ -n "$got" ] && [ "$got" = "$want" ]'
# Either route the reveal offers has to work, and nsenter needs nothing set up at all — so this check
# also passes for a learner who never made a name and went straight to the PID.
lab_require "and by PID, with no name involved at all" \
  'PID=$(runc state drillbox 2>/dev/null | jq -r .pid);
   nsenter -t $PID -n ip -o addr show 2>/dev/null | grep -q "127.0.0.1/8"'
answer_check "${ANSWER:-}"
verdict
