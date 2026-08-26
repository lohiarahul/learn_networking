# Act IX drill 6 — a permission that no binding mentions
HINT='name what the grant was attached to. It is not an account, and every identity in the cluster
is in it.'
CAUSE_SHA='0f2935056f08e1ed4e27c3837324f64c6329b13ac4f494aeb516062d8c1a8ae9
ad936fcbed631fa67e05c3ea03953905221c9d46af0616b70badf105a966fb11
4a40389bb8bf60d3be91073d17edaf7cd0289c06d69c3bfd36d4ec2cad5b8025
ebb8bdb9f650eae1e7c988277becd92690d933192b23e74c6b4f7b7dde8e3d5e
4ed379d418bb86290a01117e9ceb0debffc4d1b7087db6c04882fbc4e50132f4'

# The strongest possible check for this drill, and it is the drill's own point: create an account that
# did not exist when the fix was made. If the grant is really gone, a brand-new ServiceAccount can do
# nothing — and if it is not, this catches it no matter how the fix was worded.
FRESH="verify-newcomer-$$"
kubectl create serviceaccount "$FRESH" >/dev/null 2>&1
require_eq "a ServiceAccount created *after* your fix cannot delete pods" no \
  kubectl auth can-i delete pods --as="system:serviceaccount:default:$FRESH"
require_eq "and cannot create them either" no \
  kubectl auth can-i create pods --as="system:serviceaccount:default:$FRESH"
kubectl delete serviceaccount "$FRESH" --ignore-not-found >/dev/null 2>&1
# And the direction that finds it: ask the rules, not the account.
require "no ClusterRoleBinding grants a writing role to system:authenticated or system:unauthenticated" \
  bash -c 'kubectl get clusterrolebindings -o json \
    | python3 -c "
import json,sys
bad=[]
for b in json.load(sys.stdin)[\"items\"]:
    role=(b.get(\"roleRef\") or {}).get(\"name\",\"\")
    if role not in (\"edit\",\"admin\",\"cluster-admin\"): continue
    for s in (b.get(\"subjects\") or []):
        if s.get(\"kind\")==\"Group\" and s.get(\"name\",\"\").startswith(\"system:\") \
           and s.get(\"name\") in (\"system:authenticated\",\"system:unauthenticated\"):
            bad.append(b[\"metadata\"][\"name\"]+\" -> \"+role)
print(\"; \".join(bad))
sys.exit(1 if bad else 0)"'
answer_check "${ANSWER:-}"
verdict
