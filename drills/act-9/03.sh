# Act IX drill 3 — you deleted the account and the calls keep succeeding
HINT='one word, and it is a mechanism rather than a mistake. It explains why two correct components
disagreed about the present tense.'
CAUSE_SHA='5e1ecee06a7fc06f305ae5c12acfe7a7f67b8ece7af76932ed3afab00c3c6921
6fe78deb222783bc4f547007a32471da36efc0c41bbe4cb738dbe9e46cc7f8c4
354f3dee05ecc3d5e070ee53ed0256a2829defa8ed0ef32ac15a75103e3649e0
926505fe6faf5f4322b8d22015a2400bc6df79005ea2b5a83c186565d40be1b3
75aa879b0b486ba52ef0df9458438b3f7ef5b17e3b592af61bb68d97894e4b8d'

act9_env

# The drill's answer ends in advice — change the answer, not the identity — and advice is a prediction,
# so this measures it. One account, one busy token, two revocations, timed.
kubectl create sa revoketest >/dev/null 2>&1
kubectl create clusterrolebinding revoketest-view --clusterrole=view \
        --serviceaccount=default:revoketest >/dev/null 2>&1
TOK=$(kubectl create token revoketest --duration=1h 2>/dev/null)
require_eq "the token is accepted while the grant stands" 200 echo "$(api_status_settles 200 "$TOK")"

# Revoke the permission. The verdict is recomputed per request, so this should land at once.
kubectl delete clusterrolebinding revoketest-view --ignore-not-found >/dev/null 2>&1
AUTHZ=99
for i in $(seq 1 15); do
  [ "$(api_status "$TOK")" = "403" ] && { AUTHZ=$i; break; }
done
if [ "$AUTHZ" -le 3 ]; then ok "revoking the permission landed on request $AUTHZ — authorization is not cached this way"
else bad "revoking the permission lands within three requests" "it took $AUTHZ"; fi

# Revoke the identity instead, on the same busy token, and time that.
kubectl create clusterrolebinding revoketest-view --clusterrole=view \
        --serviceaccount=default:revoketest >/dev/null 2>&1
api_status "$TOK" >/dev/null   # keep it warm in the cache
kubectl delete sa revoketest >/dev/null 2>&1
START=$SECONDS; SECS=99
while [ $((SECONDS - START)) -lt 40 ]; do
  [ "$(api_status "$TOK")" = "401" ] && { SECS=$((SECONDS - START)); break; }
done
kubectl delete clusterrolebinding revoketest-view --ignore-not-found >/dev/null 2>&1
if [ "$SECS" -ge 5 ] && [ "$SECS" -le 20 ]; then
  ok "and revoking the identity took ${SECS}s on the same token — the gap the drill is about, measured"
else
  bad "revoking the identity takes measurably longer than revoking the permission" \
      "the 401 arrived at t+${SECS}s, which is not the ~10s window this cluster should show"
fi
require "nothing was left behind" \
  bash -c '! kubectl get clusterrolebinding revoketest-view >/dev/null 2>&1 && ! kubectl get sa revoketest >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
