# Act V drill 2 — "the Service refuses every connection, instantly"
HINT='name the field that did not match. Two strings were involved and only one of them was wrong.'
CAUSE_SHA='c7567ce69f1b1b776aee60bdf06af3daebbec1142da282672f3be93515a993f8
3838a7bc3284140f509c8c3ce80043619caebb43a4e9d1a7347b40c9b4b1bb3b
444213c6a3a8b79a117b043e55aaf5898bbe1be7a5014f226023272eda875f56
3e47b669adf50d28ab2c97c002ea7579b35f34951acbe409a034fc22b005ed5b'

# Run this *before* the Cleanup line.
endpoints_ready drill2 shop 2
svc_answers drill2 shop
# The drill's real teaching point is what kube-proxy writes when there is nothing to DNAT to. A fix
# that works is a fix that made the REJECT rule disappear, and that is checkable on the node.
require "kube-proxy has replaced the REJECT with a real load-balancing jump" \
  bash -c 'cip=$(kubectl -n drill2 get svc shop -o jsonpath="{.spec.clusterIP}");
           r=$(docker exec "${CP:-netlab-control-plane}" iptables -t nat -S KUBE-SERVICES | grep -- "$cip");
           printf "%s\n" "$r" | grep -q KUBE-SVC && ! printf "%s\n" "$r" | grep -q REJECT'
answer_check "${ANSWER:-}"
verdict
