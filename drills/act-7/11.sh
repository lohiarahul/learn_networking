# Act VII drill 11 — "the upgrade succeeded and the new API version isn't there"
HINT='name what helm upgrade does to the one directory in a chart that is not a template directory.'
CAUSE_SHA='445c08bcd73c2f960f781d6e57e746986d66d43a82bdf28edaaae7e984eaa998
cb5cf3233134daf7f5a24a8f4a44018854f4ef13a4334f903d6cc95fccb1beec
026e6418d3ee665fa966099371d490a3c164c96dbc6c63c43eba4fe365e8dfec
51c5b287bcff622ec8bed8da65cf857b6cf7ec528c65c993a96b2f4e23bb3ddb
8123f016eefbd16cff564080998420ffa73c73cc79c3f6ca1563043d88d7d6df
9282281e6ffa2651ce490e55a2e88dcfdcfa31cdb3d984c5c985d8884245a0a7
15e1105931cc175b3b150db6a08c10dd7c12ce51ec3cba10496092026d8db6d4
f6ab3b1ec823e2fa0e9b702db11409d46945c23b2f311b06232bc481be7de179
86a0a5613c7ee0d366e91f5e8e2e86c3cba72693f4110c03d42ebb0af977062e
503976859bf52aa44e0853b870fe41395d3f813d581437c15bbc82fc754bc4f0'

# Run this BEFORE the tear-down, while the release is still installed.
#
# The fix for this drill is a `kubectl apply`, so a verifier that reads the CRD's YAML would pass for
# anyone who pasted the command — including the two ways of pasting it that lose data. So the checks
# are: (1) the new version actually serves, proved by creating an object through it rather than by
# reading `spec.versions`; (2) the object that existed before the fix is still there, which is the
# check that fails if you deleted and recreated the CRD; and (3) Helm still owns a healthy release,
# because `kubectl delete crd && helm upgrade` also produces a working cluster and is not the answer.
api_answers

REL=${REL:-crdlab}
NS=${NS:-crdlab}
GRP=crdlab.example

if ! helm status "$REL" -n "$NS" >/dev/null 2>&1; then
  bad "the '$REL' release is still installed in namespace '$NS'" \
      "helm status found nothing. This verifier runs BEFORE the drill's tear-down. Override with REL=<name> NS=<ns> if you named it differently."
  answer_check "${ANSWER:-}"
  verdict
fi

require_eq "the release is healthy and Helm thinks it upgraded" "deployed" \
  bash -c "helm status $REL -n $NS -o json | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"info\"][\"status\"])'"

# (1) Functional: does the version the chart ships actually serve? Reading spec.versions would also
#     pass for a CRD that lists a version it cannot serve.
PROBE="probe-$$"
NEW=$(kubectl get crd "gadgets.$GRP" -o jsonpath='{.spec.versions[?(@.storage==true)].name}' 2>/dev/null)
if [ -z "$NEW" ]; then
  bad "the Gadget CRD exists" "no crd gadgets.$GRP in this cluster — nothing below can be measured"
  answer_check "${ANSWER:-}"; verdict
fi
OUT=$(kubectl -n "$NS" apply -f - 2>&1 <<EOF
apiVersion: $GRP/$NEW
kind: Gadget
metadata:
  name: $PROBE
spec:
  size: small
  colour: green
EOF
)
case "$OUT" in
  *created*|*configured*)
    ok "an object can be created through the chart's current storage version ($NEW)" ;;
  *"no matches for kind"*)
    bad "an object can be created through the chart's current storage version" \
        "the cluster does not serve $GRP/$NEW: $OUT — the CRD in the cluster is still the one the *install* put there" ;;
  *) bad "an object can be created through the chart's current storage version" "${OUT:-no output}" ;;
esac
# And the field the new version added must survive the round trip — a CRD that serves the version but
# still carries the old schema prunes it silently, which is the same bug with a quieter symptom.
COLOUR=$(kubectl -n "$NS" get "gadget.$NEW.$GRP" "$PROBE" -o jsonpath='{.spec.colour}' 2>/dev/null)
if [ "$COLOUR" = "green" ]; then
  ok "and the field that version added survives the write — the schema was updated, not just the version list"
else
  bad "the field the new version added survives the write" \
      "spec.colour came back as '${COLOUR:-empty}'. The CRD serves the new version with the old schema, so the field is not declared — a strict client is refused outright, a non-strict one has it pruned and never told."
fi
kubectl -n "$NS" delete "gadget.$GRP" "$PROBE" --ignore-not-found >/dev/null 2>&1

# (2) The check that catches the destructive fix.
if kubectl -n "$NS" get "gadget.$GRP" keeper >/dev/null 2>&1; then
  ok "the Gadget that existed before the fix is still there"
else
  bad "the Gadget that existed before the fix is still there" \
      "'keeper' is gone. Deleting a CustomResourceDefinition deletes every object of that kind, cluster-wide, and the garbage collector does it without asking. Whatever you ran, it was not an in-place update."
fi

# (3) …and the fix that works by abandoning Helm.
require "Helm still has a release history for it, not a fresh install" \
  bash -c "helm history $REL -n $NS -o json | python3 -c 'import sys,json; d=json.load(sys.stdin); exit(0 if len(d)>=2 else 1)'"

answer_check "${ANSWER:-}"
verdict
