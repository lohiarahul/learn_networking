# Act III drill 3 — "curl works with a flag, the browser screams, and DNS is fine"
HINT='name what nobody the client trusts had signed.'
CAUSE_SHA='03d66dd08835c1ca3f128cceacd1f31ac94163096b20f445ae84285bc0832d72
4f9a5ffbf1d1ec45a4a56df5a1cc5dbd43a168083fc6aaea00584df9ca267618
6959097001d10501ac7d54c0bdb8db61420f658f2922cc26e46d536119a31126
f796e2f28ae5811737ccb8233f34e09f8bb75d2511a135543d1ca37be0199a1d
9a9d74619c037934afded505a280f3be926a390c42cde7906ccb2cf4102f4ff1'

# Run this while the drill's s_server is still up. The two measurements together are the drill: the
# same bytes, the same server, one connection that fails and one that succeeds, differing only in what
# the client was willing to trust. Neither is a network result.
lab_up
lab_require "the drill's TLS server is still listening on 8443" 'ss -tln | grep -q ":8443"'
lab_require "without the CA the connection is refused by *verification*, not by the network" \
  '! openssl s_client -connect 127.0.0.1:8443 -verify_return_error </dev/null >/dev/null 2>&1'
lab_require "and with the CA supplied the same server verifies — so nothing on the wire was wrong" \
  'openssl s_client -connect 127.0.0.1:8443 -CAfile /tmp/c.pem -verify_return_error </dev/null >/dev/null 2>&1'
answer_check "${ANSWER:-}"
verdict
