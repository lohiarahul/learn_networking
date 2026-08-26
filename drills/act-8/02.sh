# Act VIII drill 2 — a certificate that will work, later
HINT='the certificate is fine. Name the thing that was wrong, or the fleet-wide component whose
failure produces this everywhere at once.'
CAUSE_SHA='d8198efa3604d164853468608c55efa148bc56e3564d5a30232bf98b8ab43aeb
7a2b4f275c77ab6c6b0c135f01fa975dacc225cd396eab25740d2e1d81a7d47a
72f8d7425185e5abbe200e275b7484cef0680cabc7a2a71eb91c35391bf2293d
fd6662beb9e25797d95fde3943b49da6228d5fd8d35cadc0f0945649f8e61fe1
336074805fc853987abe6f7fe3ad97a6a6f3077a16391fec744f671a015fbd7e'

openssl3
pki_ready
# The claim to measure: the certificate is not defective, the verifier's *clock* is the input that
# decided. `-attime` moves only the clock and nothing else, so if the same bytes verify at a later
# instant then the certificate was never the problem.
pki_require "a future-dated certificate is refused now" \
  'openssl genpkey -algorithm ED25519 -out later.key 2>/dev/null;
   openssl req -new -key later.key -out later.csr -subj "/CN=later.example.com" 2>/dev/null;
   openssl x509 -req -in later.csr -CA root.crt -CAkey root.key -out later.crt \
     -not_before $(date -u -v+2d +%Y%m%d000000Z 2>/dev/null || date -u -d "+2 days" +%Y%m%d000000Z) \
     -not_after  $(date -u -v+9d +%Y%m%d000000Z 2>/dev/null || date -u -d "+9 days" +%Y%m%d000000Z) 2>/dev/null;
   ! openssl verify -CAfile root.crt later.crt >/dev/null 2>&1'
pki_require "and the identical bytes verify when only the clock is moved forward" \
  'at=$(date -u -v+4d +%Y%m%d000000Z 2>/dev/null || date -u -d "+4 days" +%Y%m%d000000Z);
   openssl verify -attime $(date -u -v+4d +%s 2>/dev/null || date -u -d "+4 days" +%s) \
     -CAfile root.crt later.crt >/dev/null 2>&1'
note "nothing about the certificate changed between those two checks. The input that decided was time."
answer_check "${ANSWER:-}"
verdict
