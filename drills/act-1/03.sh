# Act I drill 3 — "we were scanned, but the logs are clean"
HINT='say what the application never did, or name the state the connection had to reach before it
would have been asked to.'
CAUSE_SHA='3fe6c25756dbf1d62259fd6576b6f7e8c8e9c08afa4c28267c1aa658222c0eed
b78cfbbab132651b95df692ba8f2815cb6b55a921e4805e2e4362fc21854b656
c125d0397b605657bc89340953f5f2897a7e00a9b7d3474fa53720c8ccbbb3e3
90221e9a0f042282ead93d7b309afac460d82d0377d12ebeed2ff9b913ab700e
7093d5c0109cf4dfb510f31754623f10fc9079ae22d0c33de78c75ae9fb75bec'

# There is nothing to repair here — the drill is about a hinge, not a fault. So the verifier does what
# the drill's answer implies and *demonstrates the hinge*, in a form the drill itself never runs: a
# socket that has called listen() and will never call accept(), two connections against it, and the
# kernel completing both handshakes on the application's behalf while the application does nothing.
#
# If you believed the application sees the connection, this is the measurement that says otherwise.
lab_up
OUT=$(docker exec -i "$LAB" python3 - <<'PY' 2>&1
import socket, subprocess, sys
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 8099)); srv.listen(8)          # listen, and never accept
peers = []
for _ in range(2):
    c = socket.create_connection(("127.0.0.1", 8099), timeout=3)
    peers.append(c)
out = subprocess.run(["ss", "-tan"], capture_output=True, text=True).stdout
est = sum(1 for l in out.splitlines() if ":8099" in l and "ESTAB" in l)
print("established=%d accepts=0" % est)
PY
)
case "$OUT" in
  *established=4*|*established=2*|*established=3*)
    ok "two clients reached ESTABLISHED against a socket nothing ever accept()ed — $OUT" ;;
  *) bad "the kernel completes the handshake without the application" "got: ${OUT:-<no output>}" ;;
esac
answer_check "${ANSWER:-}"
verdict
