# Act IX drill 5 — the service that reads a token and never checks it
HINT='three words about what the service failed to do. Not what it did wrong — what it never did
at all.'
CAUSE_SHA='4e6770a13e8683160cd32043265aa68694800f147f11686c56b5995d9236c22a
c54dd337b3f43dc9f3d62de13de177538c17ac3e8ad1bc8c343c4355082cece4
c4707fa5095ce775842e1232dbf7ac6572b1e5589461449acdd389a5f038ef2f
89a66ccefe38afebb07677aeaf907724fdd0146578ac81d088fe222157ab078c
1a2fc26dc7ea5a2a4748b7cb2b1ef193d96ab2c99f93092f69e63075b28d1278'

act9_env

# The drill's answer closes by saying the *fixed* version is still not finished, because it checks the
# signature and nothing else. That is a claim, and this is the experiment that settles it: a token whose
# signature verifies perfectly against the cluster's own published key, and which the API server
# refuses anyway. If a signature check were sufficient, this token would be accepted.
SCOPED=$(kubectl create token probe --audience=vault --duration=1h 2>/dev/null)
kubectl get --raw /openid/v1/jwks > "${TMPDIR:-/tmp}/verify-act9-jwks.json" 2>/dev/null
require "the cluster publishes a JWKS to verify against" \
  bash -c 'python3 -c "import json,sys; sys.exit(0 if json.load(open(\"${TMPDIR:-/tmp}/verify-act9-jwks.json\"))[\"keys\"] else 1)"'
require "the audience-scoped token's signature verifies against that key — it is a genuine token" \
  env TOKEN="$SCOPED" python3 -c '
import base64, json, os, sys
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
def b64(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
t = os.environ["TOKEN"]
jwks = json.load(open(os.path.join(os.environ.get("TMPDIR", "/tmp"), "verify-act9-jwks.json")))
head = json.loads(b64(t.split(".")[0]))
k = [k for k in jwks["keys"] if k["kid"] == head["kid"]][0]
pub = rsa.RSAPublicNumbers(int.from_bytes(b64(k["e"]), "big"),
                           int.from_bytes(b64(k["n"]), "big")).public_key()
signed, sig = t.rsplit(".", 1)
pub.verify(b64(sig), signed.encode(), padding.PKCS1v15(), hashes.SHA256())'
require_eq "and the API server refuses it anyway — so a signature check alone is not a verifier" 401 \
  echo "$(api_status "$SCOPED")"
answer_check "${ANSWER:-}"
verdict
