# Act IV drill 12 — "the proxy sees every connection and cannot say where any of them was going"
HINT='the proxy is reachable. Ask instead whether anything ever put it in the path.'
CAUSE_SHA='04d2077fb33c409dbb0b063ded4b3211612688de17e0c26c132d75092b64d97e
1b0263c96d1ffa42f4b0fdab21e121e6bfa8765e7628e5bd8ea2ecba5712a388
1ce87998a56b13693c4042c377e2cb96a0ec0aa1dde4280c708944a02621194c
297d34c780bf8cba5ac8b7f6ceb8647b7c0bf2edd246411154c13c748ee366ea
3cd94f514a12565e12b2a5568cc60f3613a114ac6fc84a35fcdc20400cd7c4c2
4173ef61a8c16ce199dbc182a9282cb12ca8a468eb6297dacd5dc50e7918a7cf
55a2d3618fb99cb491c4b033fc2cefcfc1d2010e442885359e523f2fd54bcbda
7c8201e19ff7cea4436ba70bdd4431771c00d435354ff7fdc02a33dd433d07d1
83df92144f1b4fc4228c0e081ca0f76f8ff4790c9ab5a0fa0dd06dd6c5d0bf04
9c2a8db58abe538778a78a004212afb4c1cd012904eb3cf3efad7e555eb140be
b1153f5eb90b910683d22762f9bae27a61390098da317765a82980fd77ac0fe5
e991583891507100a720ebb54c25563eaff3d85d73effabd06edb0019b3f61d0
f6f97835cdf9124680d7f828e163c60a3b1c5812d94f052e6a2c1d281a087406
f95d51cbd7b03984e6c3e323be2f651744b2bf51911f67765ad94dd0d4f68f9f'

lab_up
lab_require "the mesh namespace is still there to test" 'ip netns list | grep -q "^mesh"'
lab_require "the proxy is still listening on 3129" \
  'ip netns exec mesh sh -c "ss -ltn | grep -q :3129"'
# The proxy must end up genuinely INTERPOSED, not merely reachable — that distinction is the drill.
lab_require "a REDIRECT rule now puts the proxy in the path" \
  'ip netns exec mesh iptables -t nat -S OUTPUT | grep -q "REDIRECT --to-ports 3129"'
# Function, not configuration: truncate the log first so a stale success line from an earlier attempt
# cannot pass this for us, then drive one fresh connection and read what the proxy actually recovered.
lab_require "and a fresh connection to 1.1.1.1 makes the proxy name that destination" \
  ': > /tmp/proxy.log
   ip netns exec mesh curl -s -m 3 -o /dev/null http://1.1.1.1/ >/dev/null 2>&1
   sleep 1
   tr -d "\000" < /tmp/proxy.log | grep -q "destination (.1\.1\.1\.1., 80)"'
# The tempting wrong fix: take the proxy out of the path and dial the destination directly. That also
# silences "destination: unavailable", by deleting the egress control the proxy existed to provide.
lab_require "the client still has no route that bypasses the proxy" \
  '! ip netns exec mesh iptables -t nat -S OUTPUT | grep -q "DNAT --to-destination 1.1.1.1"'
lab_require "and the destination was recovered from the NAT row, not guessed" \
  'ip netns exec mesh conntrack -L -d 1.1.1.1 2>/dev/null | grep -q "dport=3129\|sport=80"'
answer_check "${ANSWER:-}"
verdict
