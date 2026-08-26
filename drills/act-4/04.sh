# Act IV drill 4 — "small requests are fine, big responses hang forever"
HINT='one acronym, and the interesting part is that the two ends disagreed about it.'
CAUSE_SHA='49be6e401e7f8b9844afb969dcbc96e78205ed86ec1e5a46150bd4ab4fdd5686
8d12c01f775dbe186f2c1afe2411de468f98da181e6b4c6a67d689c2d2dc6e1c'

lab_up
# The measurement the drill turns on: small worked all along, so a check that pings with the default
# 56-byte payload proves nothing. Large, with DF set, is the whole test.
ns_require "a 1450-byte payload now crosses the link with DF set" mtu1 \
  'ping -c1 -W3 -M do -s 1450 10.80.0.2 >/dev/null'
ns_require "and a small one still does, so nothing was broken to achieve it" mtu1 \
  'ping -c1 -W3 10.80.0.2 >/dev/null'
lab_require "both ends of the link agree on the MTU" \
  'a=$(ip netns exec mtu1 cat /sys/class/net/veth-m1/mtu 2>/dev/null);
   b=$(ip netns exec mtu2 cat /sys/class/net/veth-m2/mtu 2>/dev/null);
   [ -n "$a" ] && [ "$a" = "$b" ]'
answer_check "${ANSWER:-}"
verdict
