# Act IV drill 3 — "the published service answers inside the container but nowhere else"
HINT='the process was listening and the address was right. Name the rewrite that never happened.'
CAUSE_SHA='4aac9266bd39cf579d0613448f3d3ef8104fd4e9aa37ec956c9ef6acd601fe9e
324f89979b03b666401b49924b43b2d1e34def10d39fbb7d5a44d78a427a5d7c
1ce87998a56b13693c4042c377e2cb96a0ec0aa1dde4280c708944a02621194c
87f5fec6a7bb092e850ce3febe8744d13acec6bda7b37c38bff195ad02c6c109'

lab_up
lab_require "the server is still listening inside the namespace" 'ip netns list | grep -q "^app"'
# The whole drill in one command: the *host* side reaches it now. Inside always worked.
lab_require "the service now answers from outside the namespace" \
  'curl -sf -o /dev/null --max-time 3 10.70.0.1:8080'
lab_require "and it answers because of a DNAT rule, which is what a port publish is" \
  'iptables -t nat -S | grep -E "8080" | grep -q DNAT'
answer_check "${ANSWER:-}"
verdict
