# Act VII drill 12 — "helm says another operation is in progress and nothing is running"
HINT='say what state the release is in, and what is holding it — the thing holding it is not a
process.'
CAUSE_SHA='1f7092377c2ac1348a80155fe0cbd364983c3562e128f23e029bf337af48d38a
777c0c28ad808597956ad7f278f4254e73fcf961433cb955c4d21d54d4d98510
f89f4b853f4f8171fe4bfdae518cfa59b4ac4923b6408d317d815083ebd19280
e8bcd7c5bdb706ce6110eea1eebe09ed8a2fe55d710310991129ee62cb6c810e
8ce96e6caee15be56fff4472cbb21c30b90f9b0b1a3482f42eebbe9807ef5c20
ad57dc81a8097c46f4518b93e58364a00f86fc1f96dfd615131432f61652340f
42ddd38e7c107f7dc82174cd0fd074bac0409baa022cfc1aba162903008e30ae
bdfcf59f545c36e3f7c1d3e218d8f0a1b202ce2d65f3fc20579b9dbe18cf4afa
268f038b1fe8d5a6e1b6024c03a2d392dd626fbc7aff8a9500a175ee4023b437
7aa0ad4ba134a022822b30cfb697fc928aef881f6929627bb1617b6bd186777e'

# Run this BEFORE the tear-down, while the release is still installed.
#
# `helm upgrade` working again is not the success condition, because three different things make it
# work again and two of them throw away evidence or availability. So the checks are ordered by how
# easy the wrong fix is to reach for:
#
#   * the upgrade the ticket asked for must have actually landed — measured on the Deployment's ready
#     replicas, not on `helm list`, because this whole drill is about `helm list` being confident.
#   * revision 1 must still say `Install complete`. `helm uninstall && helm install` clears the lock
#     and leaves a working cluster, having deleted the app to get there.
#   * a revision must still be recorded as `pending-upgrade`. Deleting the release Secret for the
#     stuck revision also clears the lock, and takes the only record that the incident happened.
api_answers

REL=${REL:-hooklab}
NS=${NS:-hooklab}

if ! helm status "$REL" -n "$NS" >/dev/null 2>&1; then
  bad "the '$REL' release is still installed in namespace '$NS'" \
      "helm status found nothing. This verifier runs BEFORE the drill's tear-down. Override with REL=<name> NS=<ns> if you named it differently."
  answer_check "${ANSWER:-}"
  verdict
fi

HIST=$(helm history "$REL" -n "$NS" -o json 2>/dev/null)
hist_py() { printf '%s' "$HIST" | python3 -c "$1" 2>/dev/null; }

require_eq "the release is out of the pending state" "deployed" \
  bash -c "helm status $REL -n $NS -o json | python3 -c 'import sys,json; print(json.load(sys.stdin)[\"info\"][\"status\"])'"

# The upgrade the ticket wanted. Ready replicas, not spec.replicas: a Deployment scaled to 3 that
# cannot schedule its third Pod has not delivered the upgrade either.
READY=$(kubectl -n "$NS" get deploy "$REL" -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
if [ "${READY:-0}" -ge 3 ] 2>/dev/null; then
  ok "the upgrade the ticket asked for actually landed — $READY replicas Ready"
else
  bad "the upgrade the ticket asked for actually landed" \
      "deploy/$REL reports ${READY:-0} ready replicas, wanted 3. Clearing the lock is half the job; the upgrade still has to be run."
fi

if [ "$(hist_py 'import sys,json;d=json.load(sys.stdin);print("yes" if len(d)>=3 and any(r["revision"]==1 and "Install complete" in r.get("description","") for r in d) else "no")')" = "yes" ]; then
  ok "the history still runs from the original install through the incident — the release was repaired, not replaced"
else
  bad "the history still runs from the original install through the incident" \
      "the history is too short to contain an install, a stuck upgrade and a repair. helm uninstall + helm install also clears the lock and leaves three Ready replicas — having deleted the workload, and every record of what it used to be, to get there."
fi

if [ "$(hist_py 'import sys,json;d=json.load(sys.stdin);print("yes" if any(r.get("status")=="pending-upgrade" for r in d) else "no")')" = "yes" ]; then
  ok "and the stuck revision is still in the history, recorded as pending-upgrade"
else
  bad "the stuck revision is still in the history" \
      "no pending-upgrade revision left. A correct rollback leaves it there permanently as the record of what happened; deleting the release Secret makes the error go away and the evidence with it."
fi

# Nothing should still be holding the release open.
require "no hook Job is left running against the release" \
  bash -c "test -z \"\$(kubectl -n $NS get jobs -o jsonpath='{range .items[?(@.status.active)]}{.metadata.name}{end}' 2>/dev/null)\""

answer_check "${ANSWER:-}"
verdict
