# Act VIII drill 1 — the same error, two unrelated causes
HINT='error 20 has two meanings and this is the one where nothing is untrusted. Name what was absent
from the chain you handed over.'
CAUSE_SHA='65dd416beb70aeabb15d814afb7dd0d285978162715329d54c8c2e193dc4b26c
6aaf787c17d9ca0ccdfba22f202c8b6336c422cb47908afead5c429470137dd2
9414886b1ebf025db067a4cbd13a0903fbd9733a5372bba1b58bd72c1699b798
6353de988bb15f611bd2eb9ca3a62eb2aeda604e2fdd570802f5c15404c073e3
b66c1fed4266021fba2e0f95d09865b4f8e9514ad7ec77077cfa304ecd13c4ed'

openssl3
pki_ready
# The drill asks for two things: the fix, and the *other* meaning of error 20. So this measures both,
# and the pair is the point — one error string, two causes, two unrelated fixes.
pki_require "as the drill ran it, verification fails — the root alone cannot reach the leaf" \
  '! openssl verify -CAfile root.crt leaf.crt >/dev/null 2>&1'
pki_require "supplying the intermediate as untrusted makes the same leaf verify" \
  'openssl verify -CAfile root.crt -untrusted int.crt leaf.crt >/dev/null 2>&1'
pki_require "and the other meaning of error 20: a complete chain against a store that lacks the root" \
  '! openssl verify -CAfile int.crt -untrusted int.crt leaf.crt >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
