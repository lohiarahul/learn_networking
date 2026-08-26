# Act X drill 6 — a claim to refuse to sign
HINT='name the traffic the scheme does not cover — the biggest hole, the one their own evidence
cannot see.'
CAUSE_SHA='72f02e04906f1c8baaf0e439642ca816920bd2a8c5207d61cca1168dc053f77e
211e0f724d88c6b81f36baa4c6ab684dfc454065989fe305987e94cd18cde8fb
4716d923cc394082a35eb2113163a678c8b02cb722232134fd8648dbfaf8938c'

# No cluster is needed to answer this drill, so the answer carries most of the weight. What *is*
# checkable is the cheapest disproof the answer names — and checking it beats reading it, because the
# answer's claim is that this takes thirty seconds and produces a counterexample rather than an
# argument. So: compute it. Any node hosting two Pods that talk to each other is the disproof.
note "drill 6 is a paper drill; this computes the counterexample the answer says to reach for."
require "some node in this cluster hosts more than one Pod — the counterexample to 'all', computed" \
  bash -c 'kubectl get pods -A --field-selector status.phase=Running \
             -o jsonpath="{range .items[*]}{.spec.nodeName}{\"\n\"}{end}" \
           | sort | uniq -c | awk "\$1 > 1 {found=1} END {exit !found}"'
# And name it, because the answer's claim is that this is thirty seconds of work producing a
# counterexample rather than an argument — so the verifier should hand you the counterexample.
PAIR=$(kubectl get pods -A --field-selector status.phase=Running \
         -o jsonpath='{range .items[*]}{.spec.nodeName}{" "}{.metadata.namespace}{"/"}{.metadata.name}{"\n"}{end}' \
       2>/dev/null | sort | awk '{ if ($1 == prev) { print prev, prevpod, "and", $2; exit } prev=$1; prevpod=$2 }')
if [ -n "$PAIR" ]; then note "the pair: $PAIR — one node, two Pods, no link between them to encrypt."; fi
answer_check "${ANSWER:-}"
verdict
