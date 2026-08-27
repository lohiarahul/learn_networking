# Act X drill 12 — the scan you must act on
HINT='the two reports were both correct and the manifest still shipped. Say what a score is not, or
what neither tool was in.'
CAUSE_SHA='a62f3c454a519c44fd2bee5d2aca0d7775f255d382e7d12fe63f8e0d6992e5d6
a3a9c56cbe55783037a1d9c0e550f0846fc5da1ed174462542c127e53e529ed4
f4e2c9e41a560f5f4e3d27ff398fe7344667bb33a656a509463257c84f764a0e
1fccdc6fc23bf3d9b66a549792ec8b3dad902eaf3b80af7ce5a5fd226daf8c38
bf972648c73ac5feffe2a02884b73cf47a74c52b01dc86acd4a0e187113de677
39a222e59a57377b11cb43530bce7866e7e7653357a68f71961ff9f28f9f29cc'

# Run this after the drill's tear-down. It rebuilds the gate and the three manifests in a namespace of
# its own, because the only claim worth checking is the drill's success condition: **the privileged
# manifest is refused by the cluster, not by a report.** And the middle manifest matters more than the
# privileged one — that is the one a scanner passed.
api_answers
NS="verify-scan-$$"
POL="verify-gate-$$"
cleanup_scan() {
  kubectl delete validatingadmissionpolicybinding "$POL" --ignore-not-found >/dev/null 2>&1
  kubectl delete validatingadmissionpolicy "$POL" --ignore-not-found >/dev/null 2>&1
  kubectl delete namespace "$NS" --wait=false >/dev/null 2>&1
}
kubectl apply -f - >/dev/null 2>&1 <<EOF
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata: { name: $POL }
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["pods"]
  validations:
    - expression: "object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || c.securityContext.privileged == false)"
      message: "privileged"
    - expression: "!has(object.spec.volumes) || object.spec.volumes.all(v, !has(v.hostPath))"
      message: "hostPath"
    - expression: "object.spec.containers.all(c, has(c.resources) && has(c.resources.limits) && 'memory' in c.resources.limits)"
      message: "no memory limit"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata: { name: $POL }
spec:
  policyName: $POL
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels: { verifyscan: "$$" }
EOF
kubectl create namespace "$NS" >/dev/null 2>&1
kubectl label namespace "$NS" "verifyscan=$$" >/dev/null 2>&1
sleep 16   # the CEL compile cache — lesson 04 measured ~12s

try() {  # try <name> <yaml>
  printf '%s' "$2" | kubectl -n "$NS" apply -f - 2>&1
}
CLEAN=$(try clean 'apiVersion: v1
kind: Pod
metadata: { name: tidy }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","sleep 60"]
      securityContext: { allowPrivilegeEscalation: false, runAsNonRoot: true, runAsUser: 1000, capabilities: { drop: ["ALL"] } }
      resources: { requests: { cpu: 50m, memory: 32Mi }, limits: { cpu: 200m, memory: 128Mi } }')
UNBOUND=$(try unbounded 'apiVersion: v1
kind: Pod
metadata: { name: unbounded }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","sleep 60"]
      securityContext: { allowPrivilegeEscalation: false, runAsNonRoot: true, runAsUser: 1000, capabilities: { drop: ["ALL"] } }')
RISKY=$(try risky 'apiVersion: v1
kind: Pod
metadata: { name: risky }
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","sleep 60"]
      securityContext: { privileged: true }
      resources: { limits: { memory: 128Mi } }
      volumeMounts: [ { name: host, mountPath: /host } ]
  volumes: [ { name: host, hostPath: { path: / } } ]')

case "$CLEAN" in
  *created*) ok "the compliant manifest is still admitted — the gate is a filter, not a wall" ;;
  *) bad "the compliant manifest is admitted" "${CLEAN:-no output}" ;;
esac
# The one that matters. A gate built only from kubesec's criticals lets this through, and this is the
# manifest that took the node down.
case "$UNBOUND" in
  *denied*|*"is invalid"*) ok "and the manifest kubesec *passed* is refused — the gate encodes the linter's rule too" ;;
  *) bad "the manifest with no memory limit is refused" "it was admitted: ${UNBOUND:-no output} — a gate built only from the scanner's criticals is the bug this drill is about" ;;
esac
case "$RISKY" in
  *denied*|*"is invalid"*) ok "the privileged, host-mounting manifest is refused by the cluster, not by a report" ;;
  *) bad "the privileged manifest is refused" "${RISKY:-no output}" ;;
esac
cleanup_scan
absent "the drill's own namespace is cleaned up" get namespace scanlab
require "and the drill's policy is not left bound cluster-wide" \
  bash -c '! kubectl get validatingadmissionpolicy gate-the-scan >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
