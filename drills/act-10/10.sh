# Act X drill 10 — the hardening line that is not there
HINT='the manifest asked for one capability and got none. Name the thing about the string that made
the whole add: list evaporate.'
CAUSE_SHA='1fe19703792a8dafe76fc6e7180909c0959c6430059c00fde1862d3f7efd3af6
45e84635bc4803c5cc5d456c798a13d37a7fd184f76b012b01c01676d5ce46c0
e7a2e8b216e5aec3facf743962d3997f2e7d70088ef257de472d6a258049832e
4fa1210803f00d2e40b6453c29d4c58c8e5e6297712e90a4bf9fde6e9a468256
d9b339b1364ea05dc0066799263d758876f0e4c57d288e7a33b69aaf3dd4fb67'

# This drill has no repair — the cluster was never broken. So the verifier runs the discriminating
# measurement itself, in a namespace of its own, and requires the asymmetry the answer claims: the
# kernel's spelling of the capability yields an empty mask, and Kubernetes' spelling yields bit 0.
#
# Two Pods differing in one string. If a learner has decided the problem is the volume, the emptyDir or
# the read-only root, this is the experiment that says otherwise.
NS="verify-caps-$$"
kubectl create namespace "$NS" >/dev/null 2>&1
for cap in CAP_CHOWN CHOWN; do
  kubectl -n "$NS" apply -f - >/dev/null 2>&1 <<EOF
apiVersion: v1
kind: Pod
metadata: { name: m-$(printf '%s' "$cap" | tr 'A-Z_' 'a-z-') }
spec:
  restartPolicy: Never
  containers:
    - name: c
      image: busybox:1.36
      securityContext:
        capabilities: { drop: ["ALL"], add: ["$cap"] }
      command: ["sh","-c","grep ^CapEff /proc/self/status; touch /f && chown 1000 /f && echo CHOWN-OK || echo CHOWN-DENIED"]
EOF
done
for i in $(seq 1 30); do
  n=$(kubectl -n "$NS" get pods --no-headers 2>/dev/null | grep -c Succeeded)
  [ "${n:-0}" -ge 2 ] && break
  sleep 2
done
AS_WRITTEN=$(kubectl -n "$NS" logs m-cap-chown 2>/dev/null | tr '\n' ' ')
NO_PREFIX=$(kubectl -n "$NS" logs m-chown 2>/dev/null | tr '\n' ' ')
kubectl delete namespace "$NS" --wait=false >/dev/null 2>&1

case "$AS_WRITTEN" in
  *CapEff*0000000000000000*CHOWN-DENIED*) ok "the kernel's spelling gives CapEff 0 and the chown is refused" ;;
  *) bad "the kernel's spelling of the capability yields an empty CapEff" "got: ${AS_WRITTEN:-<no logs>}" ;;
esac
case "$NO_PREFIX" in
  *CapEff*0000000000000001*CHOWN-OK*) ok "and Kubernetes' spelling gives bit 0 and the chown succeeds — one string apart" ;;
  *) bad "Kubernetes' spelling of the capability yields CapEff bit 0" "got: ${NO_PREFIX:-<no logs>}" ;;
esac
absent "the drill's namespace is cleaned up" get namespace drill10
answer_check "${ANSWER:-}"
verdict
