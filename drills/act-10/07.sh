# Act X drill 7 — the deleted credential that came back
HINT='name the object that brought it back, or the field on the Secret that pointed at it.'
CAUSE_SHA='118785156761a89d60f12ca9ed61c4e5193b18e58cab73b918871b00ed81bace
4c1029697ee358715d3a14a2add817c4b01651440de808371f78165ac90dc581
6580c77bfbe282f4a3201b5ae602db9e5aa80ee695a79fe97458c0067d5e5fe3
2b10d2939f411f09408425f5fd6c7f73d8a84bf5347b1b6e4b3741e0f54a2f99'

# No cluster needed, and unlike drill 6 there is not even a measurement to stand in for one — the
# deliverable is a rewritten runbook. So this verifier is the answer check plus one honest structural
# claim, and it says so rather than dressing itself up.
note "drill 7 is a paper drill: the answer check is this verifier. The runbook you rewrote is the"
note "real output, and no script can grade it — read it back and ask whether step 1 changes the"
note "authoritative copy, because every other ordering is the bug you just diagnosed."
# The mechanism is checkable in general form, though: deleting an owned object is not a deletion.
require "the mechanism, in one line: an ownerReference means a controller is watching that object" \
  bash -c 'kubectl explain pod.metadata.ownerReferences 2>/dev/null | grep -qi "owner"'
answer_check "${ANSWER:-}"
verdict
