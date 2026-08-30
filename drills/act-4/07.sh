# Act IV drill 7 — "the fix for the leaked secret closed the ticket. Did it fix anything?"
HINT='say what a later build step can never do to a layer that already shipped.'
CAUSE_SHA='06c79192aa22aa871f0b78f53eff8843a93d657e7189452280fc9d5b5736d568
f3e5c5359371f64fdba324fe95212fe36c7eafdb899c4f347facd580aa809126
7c3a7e6a04aeac4e2424ff8a01b45a224e441408d60632eb687c017df2111101
3b99c9bb92f491086c6ef427601bb1cefc3f47a692cdd2324ef4e565034d1580
78c7667366369262b28939091f9835bbdfcf401286989304e45cb08a8965b418'

lab_up
# Digest-agnostic on purpose: exact layer digests shift with the base image and the build clock, so this
# walks whatever blobs exist rather than naming one. The claim is about which of two builds ever
# committed the secret to a layer at all, not about a specific hash.
lab_require "the zero-and-delete build still has the secret recoverable from a raw layer" \
  'for f in /work/build7/out/blobs/sha256/*; do gunzip -c "$f" 2>/dev/null | grep -aq hunter2 && exit 0; done; exit 1'
lab_require "the real fix (a secret mount) leaves no layer containing it at all" \
  'for f in /work/build7/outfixed/blobs/sha256/*; do gunzip -c "$f" 2>/dev/null | grep -aq hunter2 && exit 1; done; exit 0'
answer_check "${ANSWER:-}"
verdict
