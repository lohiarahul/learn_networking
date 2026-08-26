# Act VIII drill 3 — trusted, valid, signed, and refused
HINT='name the check that failed. It is not the chain, which is why adding anything to a trust store
cannot help.'
CAUSE_SHA='6b9cd7872ae634539ea1a99e1c4c16b41c9314c99192560ecf9c4bb846647655
eb4b398e9e4e6aeda676994dfc85ef016d149cef7c9fcaca22c28a9c9e6c4f3a
82a3537ff0dbce7eec35d69edc3a189ee6f17d82f353a553f9aa96cb0be3ce89
7a67a1246f5834d69e82a4bccaf90bf77cc0d5143297bff2a2e13c88d5a6cb71
e3e801d71c97280ad294b09429528b6f265548e5c9e3775f6132b739292505e7'

openssl3
pki_ready
# The drill's whole question is why adding the name to a trust store cannot work. This runs that
# proposal and shows it failing — which is stronger than being told, because somebody will try it.
pki_require "the chain itself is fine: the leaf verifies against root plus intermediate" \
  'openssl verify -CAfile root.crt -untrusted int.crt leaf.crt >/dev/null 2>&1'
pki_require "but it is refused for a name it does not carry" \
  '! openssl verify -CAfile root.crt -untrusted int.crt \
      -verify_hostname internal.example.com leaf.crt >/dev/null 2>&1'
pki_require "and adding the certificate to the trust store changes nothing — a different check failed" \
  'cat root.crt leaf.crt > store-with-leaf.crt;
   ! openssl verify -CAfile store-with-leaf.crt -untrusted int.crt \
       -verify_hostname internal.example.com leaf.crt >/dev/null 2>&1'
pki_require "it verifies for the name it does carry, so nothing else was ever wrong" \
  'openssl verify -CAfile root.crt -untrusted int.crt \
     -verify_hostname api.example.com leaf.crt >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
