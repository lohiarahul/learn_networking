# Act VIII drill 5 — a tag that verifies for the wrong reason
HINT='name what the code should have authenticated and did not. Two words, and it is a parameter the
library already had.'
CAUSE_SHA='39b272cbc35fe7e56b1eb771f4ca06ad66ff186e954d469ec93c04ca727fd120
d0128e296de3da59e3848674f0699d139fa9eafa654b8bdac7c388e10aca33ba
cb02d26b7dc89ca119104c90a63f239876acefd605944f048488c13e6c91eec0
484ed561212e582f43938621a714129e4b2ac36b2c2c11c4f0930dd3bdcdabff
3ce5034d4622d3a1bc7e026bf8758e8722bcb7b2a833df446f5ab5677b43c34f'

# Nothing is broken and nothing verifies wrongly, so the only honest check is the pair of outcomes:
# the relocation succeeds while the ciphertext is unbound, and fails the moment the row id is inside
# the tag's coverage. Both halves run here, in one process, so the difference is the two lines.
require "python3 has the cryptography module the drill needs" \
  python3 -c 'import cryptography'
OUT=$(python3 - <<'PY' 2>&1
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

def run(bind):
    key = AESGCM.generate_key(bit_length=256); aead = AESGCM(key); db = {}
    aad = (lambda u: f"row:{u}".encode()) if bind else (lambda u: None)
    def w(u, d):
        n = os.urandom(12)                        # fresh every time. never reused.
        db[u] = (n, aead.encrypt(n, d.encode(), aad(u)))
    def r(u):
        n, ct = db[u]
        return aead.decrypt(n, ct, aad(u)).decode()
    w("alice", '{"user":"alice","role":"admin"}')
    w("eve",   '{"user":"eve","role":"guest"}')
    db["eve"] = db["alice"]                       # eve writes to her own row. that is all she does.
    try:
        return "eve reads: " + r("eve")
    except InvalidTag:
        return "InvalidTag"

print("unbound:", run(False))
print("bound  :", run(True))
PY
)
case "$OUT" in
  *'unbound: eve reads: {"user":"alice","role":"admin"}'*)
    ok "with no associated data the relocated ciphertext decrypts as admin — a genuine tag, wrong row" ;;
  *) bad "the unbound version lets the relocation through" "got: ${OUT:-<no output>}" ;;
esac
case "$OUT" in
  *'bound  : InvalidTag'*)
    ok "and with the row id bound in, the identical bytes raise InvalidTag — the tag now covers the place" ;;
  *) bad "binding the row id in makes the relocation fail" "got: ${OUT:-<no output>}" ;;
esac
note "no promise was broken in the first case. That is the drill: a valid tag says nothing about where"
note "you found the bytes."
answer_check "${ANSWER:-}"
verdict
