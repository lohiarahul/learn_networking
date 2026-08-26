# Act X drill 4 — the namespace that stopped being protected
HINT='name the audit policy setting that made the trail a rumour — the one that let you prove a write
happened and not what it wrote.'
CAUSE_SHA='077ee27de898025fe3bc424cde2559b63df367194c79b065c766f4bb06b1d56a
95242d693aa3f58cf2ec558c063e21b1aea304d435e5234f698a415713fd1c0b
45447b7afbd5e544f7d0f1df0fccd26014d9850130abd3f020b89ff96b82079f
4cfecd7c74f9a6e7e6d4f2221bb673eda76d6865ae49a95be8f3c2b389d5aa02'

# Run this while bench B is still up, after applying the drill's fix to the audit policy.
#
# The strongest possible check here is the drill's own finding, run forwards: patch a label and then ask
# the log what it wrote down. Under `level: Metadata` the entry exists and `requestObject` is null;
# under the fix it carries the body. Nothing about the config file can tell you that — only the log can,
# which is the same argument drill 8 makes about etcd.
api_answers
require "bench B's audit log exists and is not empty" \
  docker exec "$CP" sh -c 'test -s /var/log/kubernetes/audit.log'
MARK="verify-audit-$$"
kubectl create namespace "$MARK" >/dev/null 2>&1
kubectl label ns "$MARK" pod-security.kubernetes.io/enforce=baseline --overwrite >/dev/null 2>&1
sleep 4
require "the audit log recorded the label write *and the value it wrote*" \
  bash -c "docker exec '$CP' sh -c 'grep \"\\\"name\\\":\\\"$MARK\\\"\" /var/log/kubernetes/audit.log' \
    | python3 -c '
import json,sys
for line in sys.stdin:
    e=json.loads(line)
    if e[\"verb\"] in (\"patch\",\"update\") and e.get(\"requestObject\"):
        sys.exit(0)
sys.exit(1)'"
kubectl delete namespace "$MARK" --wait=false >/dev/null 2>&1
# And Secrets must still be pinned at Metadata, because the fix that captures bodies captures theirs.
require "Secrets are still pinned at Metadata — the fix did not write passwords into the log" \
  bash -c "docker exec '$CP' sh -c 'cat /etc/kubernetes/audit/policy.yaml' \
    | python3 -c '
import sys
rules = sys.stdin.read()
# a rule naming secrets must appear above the write-capturing rule
i_sec = rules.find(\"secrets\")
i_req = rules.find(\"level: Request\")
sys.exit(0 if (i_sec != -1 and i_req != -1 and i_sec < i_req) else 1)'"
answer_check "${ANSWER:-}"
verdict
