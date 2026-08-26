# Act VII drill 1 — "the deploy finished but the site is down"
HINT='name the field that was added to the Deployment. The port it names is the tell.'
CAUSE_SHA='db491735c389e52efa8e40e741fd6773ea8d8ae146a7c32c09a93fe207650305
ba9c736f19e7f60b7f6764adb0b7908c0a2b394e09b6c09863528c7f2bc86095'

# READY 0/1 with STATUS Running is a readiness story, so the fix has to be read off readiness, not
# off phase. The EndpointSlice is the only thing that proves the Service will actually send traffic.
rollout_complete shop 3
require "the Service has three endpoints (not just three Pods)" \
  bash -c '[ "$(kubectl get endpointslices -l kubernetes.io/service-name=shop \
                 -o jsonpath="{range .items[*]}{range .endpoints[*]}{.conditions.ready}{\"\n\"}{end}{end}" \
                 | grep -c true)" = "3" ]'
require "and it answers over the ClusterIP" \
  bash -c 'kubectl run verify-a7d1 --rm -i --restart=Never --image=busybox:1.36 --command -- \
             wget -q -T 5 -O- http://shop/ >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
