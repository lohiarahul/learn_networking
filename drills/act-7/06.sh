# Act VII drill 6 — "the autoscaler is broken"
HINT='utilisation is a ratio. Name the missing denominator — the field, not the tool.'
CAUSE_SHA='ec72420df5dfbdce4111f715c96338df3b7cb75f58e478d2449c9720e560de8c
2f67197394a94acf68b5f61d032fc2a4e5c2d2275332ab250ffadef60186b727
63f59333c2d3b10f6e74ddb8626bbbfdf8e9ed5afab43258b29941ded762ff51
1e71f0885320ef88ab62cafbfd7ac21af498eb63da9159d0033f4ae964166d4f'

require "the Deployment now declares a CPU request" \
  bash -c 'kubectl get deploy busy -o jsonpath="{.spec.template.spec.containers[0].resources.requests.cpu}" | grep -q .'
# The real fix is that the HPA can form a value at all. ScalingActive going True is the field that
# was False, and it is a claim only the HPA controller can make — a restart cannot fake it.
require "the HPA's ScalingActive condition is True" \
  bash -c 'for i in $(seq 1 60); do
             s=$(kubectl get hpa busy -o jsonpath="{.status.conditions[?(@.type==\"ScalingActive\")].status}" 2>/dev/null)
             [ "$s" = "True" ] && exit 0; sleep 2; done; exit 1'
require "and it is reporting a real utilisation, not <unknown>" \
  bash -c 'kubectl get hpa busy -o jsonpath="{.status.currentMetrics[0].resource.current.averageUtilization}" | grep -q "[0-9]"'
answer_check "${ANSWER:-}"
verdict
