# Act IV drill 11 — "the published port answers from everywhere except the machine next door"
HINT='the rewrite fired and the server answered. Trace where the answer went, not where the request went.'
CAUSE_SHA='2548ea1e2a7da51eba1abf6622cd97ae196a05446548d9f2e2e2b42031e8a401
3e5681588f7b25b004d9ffbc6e85c348ca50728520d77699732493ab3ecb9224
43c944ebc3856e47fc4ada5150c447882aa612e843229b98116f33e3245230a8
492b06f31d01b04916e4ed980f0e416a8ccf1537a8e8fa16a9a9d6495b873860
60fdd0e45451111687bcddb85a1abd24fde37b498256cb3a7e88f3b7d845ca88
77173445a0936de225e48c9b6ffffe880ab470596a8e60a5a2cdbafb145678d8
7e27ec78d433a778aec7f1301049e5387b10063e9f4cdc64fdabe6c6d81e44c7
997b8d8ae683309c46926a1caa8c2f3b2c2ed71001f9fed02776e8fcb24d76dd
ffb95efb2b6a1d104290be2aeba095fab81b4055542c8f070d69f2592870ade3'

lab_up
lab_require "both namespaces are still there to test" \
  'ip netns list | grep -q "^app" && ip netns list | grep -q "^cli"'
# The publish must still be a publish: the client dials the PUBLISHED address, not the backend's.
lab_require "the DNAT for the published port is still in place" \
  'iptables -t nat -S PREROUTING | grep -E "8080" | grep -q "DNAT"'
lab_require "and app is still listening where the DNAT points" \
  'ip netns exec app curl -sf -o /dev/null --max-time 3 http://10.80.0.10:80'
# The whole drill in one line: the sibling on the same bridge, dialling the published address.
lab_require "cli reaches the published address it was always dialling" \
  'ip netns exec cli curl -sf -o /dev/null --max-time 3 http://10.80.0.1:8080'
# Function, not configuration — but this one is worth asserting as configuration too, because the
# tempting wrong fix is to have cli dial 10.80.0.10 directly, which passes the check above and fixes
# nothing: a published address exists precisely so callers do not have to know the backend's.
lab_require "and it reaches it because the return path now goes through the translator" \
  'iptables -t nat -S POSTROUTING | grep -E "10.80.0.0/24" | grep -qE "MASQUERADE|SNAT"'
# A learner can also make cli's curl succeed by setting bridge-nf-call-iptables back to 1, which lets
# conntrack un-NAT the bridged reply. That hides the bug rather than fixing it, so it must stay off.
lab_require "the bridge is still not silently un-NATting replies for you" \
  '[ "$(sysctl -n net.bridge.bridge-nf-call-iptables)" = "0" ]'
answer_check "${ANSWER:-}"
verdict
