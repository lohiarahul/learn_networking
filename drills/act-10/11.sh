# Act X drill 11 — the profile that enforces on one node and not the other
HINT='every field the API server has is identical, so name where the difference lives. One word about
what `localhostProfile` actually is will do.'
CAUSE_SHA='545ea538461003efdc8c81c244531b003f6f26cfccf6c0073b3239fdedf49446
2139ae8e9cdd46cca22ee4ec9fd3f28411c04f2e33bf1fb9d1fff1c7b689b86a
c9b43bb0f064b363eab30539b8f1cc30dceb7cf6760de705f34f55fe65c05c36
dd83bdf2376a843a217a4ff0609b02278b899bf4401892da916fd58f6330d579
c0bb201727d37a6ba91bff4a05ec8b2ca994880532cc1b821f86fd8b90fd8988'

# The drill's closing box is the specification for this file: *for any Pod claiming a Localhost profile,
# the only honest verification is to make the container attempt the syscall the profile is supposed to
# block, on the node it is actually running on.* So that is what this does — on both nodes, with a Pod
# pinned to each, and it requires the two answers to agree.
#
# Reading `spec.securityContext` is exactly the check the drill proves worthless, so it is not here.
NS="verify-seccomp-$$"
kubectl create namespace "$NS" >/dev/null 2>&1
for node in "$CP" "$WORKER"; do
  kubectl -n "$NS" apply -f - >/dev/null 2>&1 <<EOF
apiVersion: v1
kind: Pod
metadata: { name: p-${node#netlab-} }
spec:
  nodeName: $node
  restartPolicy: Never
  tolerations: [ { operator: Exists } ]
  securityContext:
    seccompProfile: { type: Localhost, localhostProfile: profiles/no-mkdir.json }
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","mkdir /x 2>&1 && echo MKDIR-OK || echo MKDIR-BLOCKED"]
EOF
done
for i in $(seq 1 30); do
  n=$(kubectl -n "$NS" get pods --no-headers 2>/dev/null | grep -cE 'Succeeded|Error|CreateContainerError')
  [ "${n:-0}" -ge 2 ] && break
  sleep 2
done
A=$(kubectl -n "$NS" logs "p-${CP#netlab-}" 2>&1 | tr '\n' ' ')
B=$(kubectl -n "$NS" logs "p-${WORKER#netlab-}" 2>&1 | tr '\n' ' ')
kubectl delete namespace "$NS" --wait=false >/dev/null 2>&1

verdict_of() { case "$1" in *MKDIR-BLOCKED*) printf blocked;; *MKDIR-OK*) printf allowed;; *) printf 'no-such-profile';; esac; }
VA=$(verdict_of "$A"); VB=$(verdict_of "$B")
if [ "$VA" = "$VB" ]; then
  ok "both nodes now agree — $CP says $VA and $WORKER says $VB, measured by attempting the syscall"
else
  bad "the two nodes agree about what the profile blocks" \
      "$CP says $VA, $WORKER says $VB — the divergence the drill is about is still there"
fi
if [ "$VA" = "no-such-profile" ]; then
  note "both nodes lack the file, which is the *loud* version of this bug and the safe one: a Pod that"
  note "will not start gets found. That is a legitimate end state for this drill's teardown."
fi
absent "the drill's namespace is cleaned up" get namespace drill11
answer_check "${ANSWER:-}"
verdict
