# Act VI drill 11 — "kubectl says the Pods are gone and the containers are still running"
HINT='name the daemon that stopped. The kubelet talks to it over a socket, and crictl talks to the
same one.'
CAUSE_SHA='2397d068a8d1552a4c3f9147ba9c94e086bfd66fb2acb5bbaf47197105127d5f
ee1ff929218173fc9cd4939af8014be4a25b0e39ebf6007d0bcf8eaaa05b11ef
d92c6a81b2ff50096bcda80885427d1f59a25b5f483f7055523504925d16ab23
3dd15efbff4406c10bdd4d3a5bdf9a0ef3e28e8598cad6250d8fbb589c059af5'

api_answers
nodes_ready 2
require "the runtime answers on its own socket, not through kubectl" \
  bash -c 'docker exec '"$WORKER"' crictl version >/dev/null 2>&1'
require "containerd itself is active, not merely reachable by luck" \
  bash -c '[ "$(docker exec '"$WORKER"' systemctl is-active containerd 2>/dev/null)" = "active" ]'
require_eq "and the kubelet is reporting Ready=True rather than 'container runtime is down'" "True" \
  kubectl get node "$WORKER" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
# The shims kept the containers alive through the outage, so containerd should have re-adopted them
# rather than started fresh ones. A node whose workloads all restarted did not recover, it rebooted.
require "the runtime re-adopted the containers that were already running" \
  bash -c '[ "$(docker exec '"$WORKER"' sh -c "crictl ps -q | wc -l" | tr -d " ")" -ge 2 ]'
pod_runs_on "$WORKER"
answer_check "${ANSWER:-}"
verdict
