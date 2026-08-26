# Act X drill 2 — nothing is wrong and nothing will start
HINT='name the admission plugin, or name the category of plugin it turns out to be — the one that
explains a field you never wrote.'
CAUSE_SHA='58039e3a8a7fd362bc257b0e04f3ee9ad05d5231f681751b9f3c2ae47aac04fc
023b89507c1190eeed929b53dfd4806f8b1863791b5c58712f5792fa5031e45a
7af5309cb4c92bccff489216b0cd29e4b3abb3c1efa1897c08fcc7f4b324aa89
0d0ccb6ab16a3cfd41f6aec01ec701f3eda7ecb1e2ad05dd731a989f18e34095'

# Run this *after* the drill's revert block. The drill ends by telling you to put the flag back before
# the next drill, and the check is the mutation itself rather than the flag: create a Pod that says
# nothing about pull policy and read what got stored. That is the same measurement the drill used to
# find the plugin, pointed at proving it is gone.
api_answers
PROBE="verify-pullpolicy-$$"
kubectl run "$PROBE" --image=busybox:1.36 --restart=Never --command -- true >/dev/null 2>&1
POLICY=$(kubectl get pod "$PROBE" -o jsonpath='{.spec.containers[0].imagePullPolicy}' 2>/dev/null)
kubectl delete pod "$PROBE" --force --grace-period=0 --wait=false >/dev/null 2>&1
if [ "$POLICY" = "IfNotPresent" ]; then
  ok "a Pod that says nothing about pull policy is stored as IfNotPresent — nothing is rewriting it"
elif [ "$POLICY" = "Always" ]; then
  bad "a Pod that says nothing about pull policy is stored as IfNotPresent" \
      "it came back Always, so the mutating plugin is still enabled — the drill's revert block did not land"
else
  bad "a Pod that says nothing about pull policy is stored as IfNotPresent" "got '${POLICY:-<nothing>}'"
fi
require "and the plugin is gone from the running kube-apiserver's own flags" \
  bash -c '! kubectl -n kube-system get pod -l component=kube-apiserver \
      -o jsonpath="{.items[*].spec.containers[0].command}" 2>/dev/null | grep -q AlwaysPullImages'
# Conditional on purpose. `docker stop registry` is part of the drill and `docker start registry` is
# part of its revert, so while bench A is up this is a real check. Once bench A has been torn down the
# container is *supposed* to be gone, and failing then would be the verifier misreading its own scope.
if docker inspect registry >/dev/null 2>&1; then
  require "the registry container you stopped is running again" \
    bash -c 'docker inspect -f "{{.State.Running}}" registry 2>/dev/null | grep -q true'
else
  note "bench A is torn down (no registry container at all), so the restart check does not apply."
fi
require "no backup manifest left in /root" \
  docker exec "$CP" sh -c '[ ! -e /root/ka.bak ]'
answer_check "${ANSWER:-}"
verdict
