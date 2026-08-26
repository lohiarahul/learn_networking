# Act VIII drill 6 — the intermediate that tries to be a root
HINT='name the extension whose value decided it. One field, in one certificate.'
CAUSE_SHA='e35227fa24b5a3cc4bcaa91c0d4adba165e4df39e26c15d0bfda44da976fc25e
e386b2bf6354615dcd79bcfec5158fe242eefea3b7f1effaba37d7a6503436b8
d4eadfb953984cb83f7cd967d9a8927fa5d160d61146075d4ba989c13780ff07
b490684153495cbddba1228374c1134818914ba847f8ff78a6e75dc3642eb82b'

openssl3
pki_ready
# The drill asks why the field has to be checked by the verifier rather than enforced at signing time,
# and the measurement that answers it is this: the signing succeeds. A certificate that violates the
# constraint gets *issued* without complaint, and only verification refuses it.
pki_require "the intermediate declares pathlen:0 — it may sign leaves and not more CAs" \
  'openssl x509 -in int.crt -noout -text | grep -A1 "X509v3 Basic Constraints" | grep -q "pathlen:0"'
pki_require "signing a second CA under it succeeds anyway — nothing refuses at issue time" \
  'openssl genpkey -algorithm ED25519 -out sub.key 2>/dev/null;
   openssl req -new -key sub.key -out sub.csr -subj "/CN=Sub CA" 2>/dev/null;
   printf "basicConstraints=critical,CA:TRUE\n" > sub.ext;
   openssl x509 -req -in sub.csr -CA int.crt -CAkey int.key -out sub.crt -days 365 -extfile sub.ext 2>/dev/null;
   [ -s sub.crt ]'
pki_require "and a leaf under that sub-CA is refused by the verifier, which is the only thing that checks" \
  'openssl genpkey -algorithm ED25519 -out sleaf.key 2>/dev/null;
   openssl req -new -key sleaf.key -out sleaf.csr -subj "/CN=deep.example.com" 2>/dev/null;
   openssl x509 -req -in sleaf.csr -CA sub.crt -CAkey sub.key -out sleaf.crt -days 365 2>/dev/null;
   ! openssl verify -CAfile root.crt -untrusted int.crt -untrusted sub.crt sleaf.crt >/dev/null 2>&1'
note "the constraint is a claim in a certificate, and a claim is only worth what the reader does with it."
answer_check "${ANSWER:-}"
verdict
