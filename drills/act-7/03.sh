# Act VII drill 3 — "half the replicas never start"
HINT='name what the scheduler was actually short of. It is a field you wrote, not a resource the
nodes lack.'
CAUSE_SHA='ec72420df5dfbdce4111f715c96338df3b7cb75f58e478d2449c9720e560de8c
2f67197394a94acf68b5f61d032fc2a4e5c2d2275332ab250ffadef60186b727
63f59333c2d3b10f6e74ddb8626bbbfdf8e9ed5afab43258b29941ded762ff51
1e71f0885320ef88ab62cafbfd7ac21af498eb63da9159d0033f4ae964166d4f'

rollout_complete heavy 4
require "no Pod is left Pending" \
  bash -c '[ -z "$(kubectl get pods -l app=heavy --field-selector status.phase=Pending -o name)" ]'
# The point of the drill is that requests are a *ledger* entry, so check the ledger, not the load:
# the sum of what this Deployment reserves must now fit, and 3 CPU per replica never could.
require "the CPU request is back inside what a node can promise" \
  bash -c 'r=$(kubectl get deploy heavy -o jsonpath="{.spec.template.spec.containers[0].resources.requests.cpu}");
           case "$r" in *m) [ "${r%m}" -le 2000 ];; "") false;; *) [ "$r" -le 2 ];; esac'
answer_check "${ANSWER:-}"
verdict
