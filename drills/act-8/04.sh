# Act VIII drill 4 — the failure that reports success
HINT='say why the two verdicts do not contradict each other — one phrase about whose question each
one answers, or the operational rule that follows from it.'
CAUSE_SHA='451b2c5dabcbf4a178bda057d81ed1530898ccdf5101c45542ba3a7f46bba55e
1217c80e4f94970abcf7284c3ed42db22baf054f73d908faef745b333c23d6ff
53802168ae5c915e29fddf6935d62fc5fac27ed3dc0c52decb2ee5b92851d389
4cda48844d6aaf39a4cc4c6e0439bc4cdd7ac925494c3b8c9f8ff6807ed8ed2c
f4684bfc22b398ab4a352d9bb4b6a1d18052f459b9bca2b35accd6d717ed09f6'

openssl3
pki_ready
# The asymmetry, measured rather than quoted: one connection, the client reporting 0 (ok) while the
# server's log records the failure. Then the same client with a certificate, and the server naming it.
#
# This runs its own server so it does not depend on the drill's still being up, and kills it after.
SRV_LOG="$PKI/verify-server.log"
( cd "$PKI" && openssl genpkey -algorithm ED25519 -out vclient.key 2>/dev/null
  openssl req -new -key vclient.key -out vclient.csr -subj "/CN=svc-a/O=readers" 2>/dev/null
  openssl x509 -req -in vclient.csr -CA root.crt -CAkey root.key -out vclient.crt -days 1 2>/dev/null ) 
( cd "$PKI" && openssl s_server -cert leaf.crt -key leaf.key -cert_chain int.crt \
    -CAfile root.crt -Verify 1 -accept 14433 -www > "$SRV_LOG" 2>&1 & echo $! > "$PKI/verify-server.pid" )
sleep 2
NOCERT=$(cd "$PKI" && echo | openssl s_client -connect localhost:14433 -CAfile root.crt 2>/dev/null | grep 'Verify return code')
sleep 1
SRVSAW=$(grep -c 'peer did not return a certificate' "$SRV_LOG" 2>/dev/null)
WITHCERT=$(cd "$PKI" && echo | openssl s_client -connect localhost:14433 -CAfile root.crt \
             -cert vclient.crt -key vclient.key 2>/dev/null | grep 'Verify return code')
sleep 1
NAMED=$(grep -c 'depth=0 CN=svc-a' "$SRV_LOG" 2>/dev/null)
[ -s "$PKI/verify-server.pid" ] && kill "$(cat "$PKI/verify-server.pid")" 2>/dev/null
rm -f "$PKI/verify-server.pid"

case "$NOCERT" in
  *"0 (ok)"*) ok "the client, sending no certificate, reports: ${NOCERT# }" ;;
  *) bad "the client reports verify return code 0 despite sending no certificate" "got '${NOCERT:-nothing}'" ;;
esac
if [ "${SRVSAW:-0}" -ge 1 ]; then
  ok "and in the same second the server's log records 'peer did not return a certificate'"
else
  bad "the server's log records the failure the client did not" "nothing in $SRV_LOG said so"
fi
case "$WITHCERT" in
  *"0 (ok)"*) ok "with a client certificate the client's output is *identical* — it never distinguished the two" ;;
  *) bad "the client reports the same code when it does send a certificate" "got '${WITHCERT:-nothing}'" ;;
esac
if [ "${NAMED:-0}" -ge 1 ]; then
  ok "and only now does the server name who it is talking to (depth=0 CN=svc-a)"
else
  bad "the server names the client once it presents a certificate" "no depth=0 line appeared"
fi
answer_check "${ANSWER:-}"
verdict
