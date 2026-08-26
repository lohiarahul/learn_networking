# Act III drill 2 — "the app logged 'upload complete' but the client is still waiting"
HINT='nothing on the network was wrong. Name what was slow, or what `write()` actually returned into.'
CAUSE_SHA='e2147e9fc5a059a581b2c211b33855355be3c0e7c844e7f9b81ffc64f6dd01e1
e6419765ad0e7868247f5e20a6ea3bac1458df541c6dfa9177e1d0ccb7987444
95296562ede4ef066f0052bf2daec729002b2d3f8c5ebcb279ef1f8d29d33bf6
07191d260e800840ba345ad9c124deefa5d86c219a15a40988f147c418bf929f
ebf6b34a0a04a96ee22de9ca25bd36a4eaec351e6bcb72b19e1d7ded50e65ec9'

# Nothing is broken in this drill — the machine behaved correctly throughout — so the verifier does
# what the answer implies and measures the claim: a `write()` that "succeeds" into a socket nobody is
# reading, and the exact byte at which it stops succeeding. That number is the buffer, and the gap
# between it and "the upload completed" is the whole bug.
lab_up
OUT=$(docker exec -i "$LAB" python3 - <<'PY' 2>&1
import socket, errno
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 8098)); srv.listen(1)
c = socket.create_connection(("127.0.0.1", 8098))
s, _ = srv.accept()                     # accepted, and deliberately never read from
c.setblocking(False)
sent = 0
chunk = b"x" * 4096
while True:
    try:
        sent += c.send(chunk)
    except BlockingIOError:
        break
    if sent > 64 * 1024 * 1024:
        break
print("accepted_without_reading_bytes=%d" % sent)
PY
)
N=$(printf '%s' "$OUT" | sed -n 's/.*bytes=\([0-9]*\).*/\1/p')
if [ -n "$N" ] && [ "$N" -gt 4096 ]; then
  ok "write() accepted $N bytes into a socket nobody read — that is what 'upload complete' measured"
else
  bad "write() accepts bytes the peer has not read" "got: ${OUT:-<no output>}"
fi
note "the client is still waiting because those bytes are in two kernel buffers, not in the peer."
answer_check "${ANSWER:-}"
verdict
