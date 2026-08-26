# Act IV drill 2 — "two containers on the same host can't reach each other"
HINT='both addresses were right and both namespaces were up. Name the state of the thing between
them.'
CAUSE_SHA='153584a518293323db2baea22865462dc610e11220ed00c86d68a85b68987fac
908aec4512d80ff4fefb1970899091e9de8e734b36b8fdb7678e77dc092f6959
5322d92186fc4bd1033789b257fadf57cbc4d7ae65079c7232f05d30957652cb
fc87dc50e95e06d549b4b42d85a8cff9a0b131c75640565c190173461b1c4d67
cf50d89df6e7835bd1b5ce2c69a045880d74f79ac8bd1478d600cf47d9843972'

lab_up
ns_require "ns1 reaches ns2 across the bridge" ns1 'ping -c1 -W3 10.60.0.2 >/dev/null'
ns_require "and ns2 reaches ns1 — both directions, so it is not a one-way rule" ns2 'ping -c1 -W3 10.60.0.1 >/dev/null'
# The bridge's own evidence, and the reason this drill sits next to the VLAN lesson: a bridge learns
# MACs from frames it has seen. Two entries means traffic has actually crossed it.
lab_require "the bridge has learned a MAC from each side — it has carried real frames" \
  'n=$(bridge fdb show br br0 2>/dev/null | grep -c "veth-"); [ "${n:-0}" -ge 2 ]'
lab_require "no interface on either end of the cable is left DOWN" \
  '! ip -o link show | grep -E "veth-(a|b)" | grep -q "state DOWN"'
answer_check "${ANSWER:-}"
verdict
