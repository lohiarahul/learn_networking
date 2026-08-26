# The drill verifiers

**This directory grades you, and it will not tell you the answer.**

Every `diagnose.md` in this course ends each drill with a `<details>Reveal` block. That block is the
weakest link in the whole repository, and it is worth being blunt about why: a reveal is graded by the
person who just failed to solve the drill. Reading an explanation and thinking *yes, I would have got
there* is the single most reliable way a self-study learner arrives at an exam confident and unready.
Meanwhile the repo automates verification of the **author** in two places — `tools/check_pedagogy.py`
gates structure and link integrity, `tools/probe-lab.py` re-runs every quoted output against
`netlab:latest` — and neither of them was ever pointed at the **learner**.

This is that missing half.

```bash
tools/verify-drill.sh act-6 1 "kube-scheduler"
tools/verify-drill.sh --list                    # what is covered so far
```

Exit code `0` means the drill is done. Anything else means it is not.

## What a verifier checks, and why it is built this way

**It verifies by function, never by configuration.** "The manifest file is back in
`/etc/kubernetes/manifests/`" is a claim about a file. "A Pod created five seconds ago acquired a
`spec.nodeName`" is a claim about a scheduler that is running *and* reconciling *and* reachable. Only
the second one is a fix. Every check in [`lib.sh`](lib.sh) that could be written as a live probe is
written as a live probe, because the failure mode this course keeps teaching — a status field that is
true and stale — applies to a learner checking their own work as much as to a monitoring dashboard.

**It requires you to name the cause.** The third argument is not optional and it is not a formality: a
drill you repaired without being able to say what was wrong is a drill you have not done, and it is
precisely the outcome that a `Fix it` block pasted without reading produces. The state checks alone
cannot tell those apart. Naming the cause can.

**It does not spoil the drill.** The expected answer is stored as a **SHA-256 of its normalised
form** — lowercased, `the ` stripped, punctuation removed — and never as text. You can read every file
in this directory and you will not find a cause; you can only be told whether yours matched. That is
also why each verifier carries a `HINT` that names the *shape* of the answer ("the name of a
control-plane component", "the flag whose value was rejected") without narrowing it to one.

Normalisation means the obvious variants are all accepted: `kube-scheduler`, `Kube Scheduler`, `the
scheduler` and `scheduler` are one answer. Where two genuinely different words are both right, the
verifier holds both hashes.

**It fails on debris.** A drill that left a Deployment, a namespace or a cordoned node behind is not
finished, because the next drill starts from this state and a cluster carrying four drills' worth of
leftovers produces symptoms no reveal accounts for. This is the check most likely to annoy you, and
it is the one that will save an hour.

## What it cannot check

It cannot tell whether you reasoned your way there or guessed, and it does not pretend to. What it can
do is make the two most common self-deceptions expensive: fixing without diagnosing (the cause check),
and diagnosing without fixing (the function checks). Beyond that, the honest instrument is the clock —
see *The clock* at the top of any `diagnose.md`.

## Adding one

A verifier is a shell fragment sourced by `tools/verify-drill.sh` after `lib.sh`, so every helper in
`lib.sh` is already in scope. It sets two variables and then asserts:

```bash
# drills/act-N/NN.sh
HINT='name the ... (say what shape the answer takes, not what it is)'
CAUSE_SHA='<sha256 of the normalised answer>
<sha256 of an equally-correct alternative>'

api_answers
all_static_manifests
probe_scheduled
absent "the drill's Deployment is cleaned up" get deployment foo
answer_check "${ANSWER:-}"
verdict
```

Generate a hash the same way the library does, so the two never drift:

```bash
printf '%s' "$(printf '%s' 'kube-scheduler' | tr 'A-Z' 'a-z' | sed 's/^the //' | tr -cd 'a-z0-9')" \
  | shasum -a 256 | cut -d' ' -f1
```

Two rules for a new check. Prefer a probe that creates something new over a read of something that
already exists — a stale field cannot fake a Pod that did not exist a moment ago. And make the failure
message say what to do rather than what went wrong: `run 'kubectl uncordon <node>'` is worth more at
2am than `assertion failed`.

## The one act where this works differently

Act IX has no repairs to check. Its opening sentence is *"every system in these drills is working
correctly"*, and four of its six drills ask only for an explanation — so a verifier that looked for a
fix would have nothing to look at.

What those four do instead is **run the experiment the explanation predicts**. Drill 1's answer says a
`401` cannot be repaired by granting permissions, so the verifier grants them and re-sends both
tokens: the ordinary one moves to `200`, the audience-scoped one does not move at all. Drill 3's
answer ends in advice — revoke what the credential *may do*, not the credential — so the verifier
times both revocations on one busy token and reports the two numbers. Drill 5's answer claims that
checking a signature is not the same as verifying a token, so the verifier mints a token whose
signature verifies against the cluster's own published key and shows the API server refusing it
anyway.

That is a harder test than checking a repair, not a softer one, because **a wrong explanation predicts
the wrong result** — and unlike a reveal, it cannot be graded generously by the person reading it.

## One trap worth naming

`Authorization: Bearer ` with nothing after it is a **well-formed request from `system:anonymous`**, so
it comes back `403`. Every Act IX check that took real debugging to write failed this way: a token that
silently failed to mint (`kubectl create token --duration` below ten minutes is refused outright), and
then a `403` that read exactly like a permissions result. `api_status` in [`lib.sh`](lib.sh) now
answers `no-token-was-minted` rather than sending the request, because a legible failure is worth more
than a plausible one.
