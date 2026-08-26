# Act II drill 3 — "SSH connects, then freezes; small requests work, big ones hang"
HINT='one acronym. It is a property of a link and it is why small things work and big things do not.'
CAUSE_SHA='49be6e401e7f8b9844afb969dcbc96e78205ed86ec1e5a46150bd4ab4fdd5686
3b724dfa8f3a5c86d165ef763786ae0a15fc6511b29b85c21dc074f878a14da2
6accaa1f9dd882d3b085bc04c432e2b36ae386b50d8846329b4f54d11137d674
8d12c01f775dbe186f2c1afe2411de468f98da181e6b4c6a67d689c2d2dc6e1c'

lab_up
lab_require "the uplink is back at a normal MTU" \
  'u=$(ip route show default | awk "{print \$5}"); [ "$(cat /sys/class/net/$u/mtu)" -ge 1500 ]'
# The measurement that matters, and the one the drill teaches: a *large* frame, with fragmentation
# forbidden, has to make it to the gateway and back. A small ping never proved anything.
lab_require "and a 1450-byte payload gets through with DF set — small and large now behave alike" \
  'gw=$(ip route show default | awk "{print \$3}"); ping -c1 -W3 -M do -s 1450 "$gw" >/dev/null'
answer_check "${ANSWER:-}"
verdict
