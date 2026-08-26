# Act X drill 9 — the namespace that never enforced anything
HINT='two namespaces are wrong for two different reasons. Name the field that makes the one that
*does* enforce enforce something weaker than you think.'
CAUSE_SHA='68c4d7a00a18c4588bdc673996a4775a35c1e79cba1c784c58dda802bd3b0c8c
57f088c331cb9b3267467ca13d6c351c156f2b7dfb506554ebbea884311d50bc
fa784a01f1bd517617bf3f31d39fd80cb49121da10ac26ae625226c20be984b2
7b885225894918b6bd329d5ba24497438eada4fcaacd273e51e1ca7340f98bfb'

# Run this before the bench C teardown. The drill's own finding is that reading the label is not an
# audit, so this verifier does not read the label — it sends a Pod that `restricted` must refuse into
# each of the three namespaces and requires all three to refuse it. That is the check the answer says
# to do instead, and it is the only one that catches all three faults at once.
for ns in tenant-a tenant-b tenant-c; do
  out=$(kubectl -n "$ns" run "verify-priv-$$" --image=busybox:1.36 --restart=Never \
          --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.36","securityContext":{"privileged":true},"command":["true"]}]}}' \
          2>&1)
  if printf '%s' "$out" | grep -qi 'forbidden\|violates PodSecurity'; then
    ok "$ns refuses a privileged Pod at admission"
  else
    bad "$ns refuses a privileged Pod at admission" \
        "it was admitted — ${out:-no error at all}"
    kubectl -n "$ns" delete pod "verify-priv-$$" --force --grace-period=0 --wait=false >/dev/null 2>&1
  fi
done
# And the version pin, which is the fault that survives every behavioural probe a `restricted` standard
# older than the cluster still refuses. There is no way to catch this except by reading the field.
require "no namespace pins enforce-version — none of the three is frozen at an older restricted" \
  bash -c 'n=$(kubectl get ns tenant-a tenant-b tenant-c \
      -o jsonpath="{range .items[*]}{.metadata.labels}{\"\n\"}{end}" \
    | grep -c "enforce-version"); [ "$n" -eq 0 ]'
answer_check "${ANSWER:-}"
verdict
