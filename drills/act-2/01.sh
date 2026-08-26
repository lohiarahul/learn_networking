# Act II drill 1 — "internet's down, but the machine looks perfectly healthy"
HINT='name the table that had the wrong answer in it. Layer 2, and it is a cache.'
CAUSE_SHA='cf835fc094349f22c2214fc8256cb895fcbcc01c77083c0f94114703d9e79a29
7cbf1a87970184d929a362d89ac53700ea354f97a1e2464723b28cbf2b09add7
3167a7cb4738e853532fccdc1e01752b079b913d053148619ba75e5be4e32548
81a2140a4d8e51b88cdf58c7cb65f6a7670adcdd563e57793fb8dba74ef5b223
2611b5670368ec5ddaa3f1b5f21cbdb034c3a57d0963193676a4686803c2f829'

lab_up
lab_require "the machine reaches the internet again" 'ping -c1 -W3 8.8.8.8 >/dev/null'
# The anti-cheat, and the point of the drill: a route or a second address would also restore the ping.
# The fix is the removal of a wrong PERMANENT answer, so the wrong answer must be gone.
lab_require "and no permanent neighbour entry is left overriding the gateway" \
  '! ip neigh show | grep -q PERMANENT'
lab_require "the gateway now resolves by asking, not by being told" \
  'gw=$(ip route show default | awk "{print \$3}"); ip neigh show "$gw" | grep -Eq "REACHABLE|STALE|DELAY"'
answer_check "${ANSWER:-}"
verdict
