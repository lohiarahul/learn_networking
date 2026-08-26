# Act IX drill 2 — a RoleBinding that is syntactically perfect and grants nothing
HINT='both faults are the same class of mistake. Name the property that `roleRef` and `subjects` both
turn out not to have.'
CAUSE_SHA='adc2cf28303bc1a84cd973d2250dcb1544a59cea1c2454e736628c3d1ae6abf8
51ac5de78f2f8e4a736aa68086feadae63a86ddf05d5429ad2ddf7c7ab1f0ca7
4e4d699d5a5f1b45c14d7eac4acf8600058491f706a7f7ab89817248321f63f2
bd3a8c140305a4954ed34dd6bb723ab9ccf4ad30cc97466bdba8e6d68806a164
51b4130f3c7bb7d6f55b7c907dd953c9caa291d8f600af2239a71faa27f00cf7'

# Both faults, because the drill asked for both. `auth can-i --as` is the function check here: it is
# the authorizer's own verdict on a named subject, not a reading of the object you edited.
require_eq "fault 1 fixed: probe can list pods in default" yes \
  kubectl auth can-i list pods --as=system:serviceaccount:default:probe
require_eq "fault 2 fixed: app:worker — the account that exists — can list pods in app" yes \
  kubectl auth can-i list pods -n app --as=system:serviceaccount:app:worker
# The point of fault 1 was that a dangling roleRef is accepted and starts working later, so the fix has
# to be a reference that resolves *now*.
require "the roleRef on probe-reads names a Role that actually exists" \
  bash -c 'r=$(kubectl get rolebinding probe-reads -o jsonpath="{.roleRef.name}");
           [ -n "$r" ] && kubectl get role "$r" >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
