# Act IV drill 5 — "the container isn't as isolated as the last four drills assumed"
HINT='name what was missing from one JSON array, and where that array lives.'
CAUSE_SHA='dde8599cf2ab04ece7ae49ef512ef36839c1e0330f545f6d40e813de82b46033
573f0cc0b71956fb991a7b4bfa934ed6c5ba74e696c3a5a7bd7278674cd0c06e
1829cfc6f56e2c9f388bc6cf9d4f096ad812ac80b3abff563a2d3c716707f71b
a14db99732ebb1fda07edd9597ae952824a7e8af7b1e095ff64391915f1d150b
e40bd773ef1984fcde744254f2f5b323c907108c3f5c625e5b43e5a270567d3c'

lab_up
lab_require "runc still has a container named drillbox to test" 'runc list | grep -q drillbox'
lab_require "config.json's namespaces list has a network entry again" \
  "jq -e '[.linux.namespaces[].type] | index(\"network\") != null' /work/bundle/config.json >/dev/null"
# Function, not configuration: the JSON key is necessary but not sufficient — the running container has
# to actually hold a distinct namespace, the same inode check the lessons used throughout the act.
lab_require "and the running container actually has its own network namespace" \
  "PID=\$(runc state drillbox 2>/dev/null | jq -r .pid); [ -n \"\$PID\" ] && [ \"\$PID\" != null ] &&
   a=\$(readlink /proc/\$PID/ns/net) && b=\$(readlink /proc/1/ns/net) && [ \"\$a\" != \"\$b\" ]"
answer_check "${ANSWER:-}"
verdict
