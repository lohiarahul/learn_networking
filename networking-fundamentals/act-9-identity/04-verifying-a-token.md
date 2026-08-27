# Trusting a token you did not issue

The API server rejected your forgery, so it can tell reading from verifying. You cannot — yet. It holds a key you do not have.

Except that the header told you the key has a *name*. `"kid":"fNzzmn2keCMktTShWvQORjFrMZ1vC_RD0RVKbWDbBl0"`. Naming a key is a strange thing to do if nobody is ever expected to go and find it.

> **Predict first —** you want to check that signature. Act VIII lesson 05 tells you what you need: the *public* half of whatever key signed it. So the cluster would have to publish it. Before you look for it, answer two things. First: **who should be allowed to fetch that key** — everyone in the world, everyone the cluster already trusts, or only the control plane? Argue it, because the answer is not obvious and the wrong argument is very tempting. Second: if you *do* get the public key, what exactly does that let you do — and what does it not let you do?

### Ask the cluster where its keys are

There is a convention for this, and it is not Kubernetes-specific. Any system that issues these tokens is expected to serve a **discovery document** at a fixed path — the same path, on every such system in the world:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act9.kubeconfig"
kubectl get --raw /.well-known/openid-configuration | python3 -m json.tool
```

```json
{
    "issuer": "https://kubernetes.default.svc.cluster.local",
    "jwks_uri": "https://172.19.0.2:6443/openid/v1/jwks",
    "response_types_supported": [
        "id_token"
    ],
    "subject_types_supported": [
        "public"
    ],
    "id_token_signing_alg_values_supported": [
        "RS256"
    ]
}
```

**Your Kubernetes cluster is an identity provider**, and that is not a metaphor — that document is the same format Google and Microsoft and Okta serve, at the same well-known path, and it exists so that software which has never heard of Kubernetes can nonetheless verify its tokens.

Read the two fields that matter. `issuer` is the string you saw as `iss` inside the token, which is the link that makes discovery work: **a token tells you who issued it, and the issuer's URL tells you where to find the key.** And `id_token_signing_alg_values_supported` is the issuer stating, in advance and in public, which algorithms it will ever use. Hold that one; it becomes an attack in a moment.

Follow `jwks_uri`:

```bash
kubectl get --raw /openid/v1/jwks | python3 -m json.tool
```

```json
{
    "keys": [
        {
            "use": "sig",
            "kty": "RSA",
            "kid": "fNzzmn2keCMktTShWvQORjFrMZ1vC_RD0RVKbWDbBl0",
            "alg": "RS256",
            "n": "uR_yNLgwJq5FSFrUDAad9BHFzWcHu2qhcvJT_wVIKGX1oPcYaZ51vl0...",
            "e": "AQAB"
        }
    ]
}
```

A **JWKS** — a JSON Web Key Set. A *set*, plural, because an issuer must be able to rotate: publish the new key alongside the old, start signing with the new one, and only drop the old once every token it signed has expired. That is what `kid` is for, and it is the whole reason the header names a key rather than assuming one. **`kid` is what makes key rotation possible without a flag day**, and Act VIII's lesson on short lifetimes is what makes it terminate.

And `n` and `e` are the public key itself, written as two numbers — a **modulus** and an **exponent**, each the base64url of its raw bytes. That pair *is* an RSA public key, and it is worth noticing how unlike Act VIII's keys it looks: X25519 and Ed25519 public keys were a single opaque 32-byte string, and this one is two integers of very different sizes. Same job in the same slot — the publishable half of a pair, here serialised into a JSON document instead of a PEM file — but the structure differs because the arithmetic underneath differs. Which is precisely why the header has to name an algorithm at all: `n` and `e` mean nothing without being told they are RSA's.

### Who may read it

Now answer the first half of the prediction, and do not guess — the cluster will tell you:

```bash
curl -s --cacert "${TMPDIR:-/tmp}/ca.crt" \
  "$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')/openid/v1/jwks"
```

```json
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {},
  "status": "Failure",
  "message": "forbidden: User \"system:anonymous\" cannot get path \"/openid/v1/jwks\"",
  "reason": "Forbidden",
  "details": {},
  "code": 403
}
```

**Not public.** And note the shape of that refusal, because it is lesson 01 arriving exactly as promised: `403`, with a username in it, for a request that carried no credential. Anonymous is a *name*, the rules about that name say no, and the rule is written in the same ordinary place as every other rule. There is no special case. Go and read it:

```bash
kubectl get clusterrole system:service-account-issuer-discovery \
  -o jsonpath='{.rules}' | python3 -m json.tool
kubectl get clusterrolebinding system:service-account-issuer-discovery \
  -o jsonpath='{.subjects}' | python3 -m json.tool
```

```json
[
    {
        "nonResourceURLs": [
            "/.well-known/openid-configuration",
            "/.well-known/openid-configuration/",
            "/openid/v1/jwks",
            "/openid/v1/jwks/"
        ],
        "verbs": [
            "get"
        ]
    }
]
[
    {
        "apiGroup": "rbac.authorization.k8s.io",
        "kind": "Group",
        "name": "system:serviceaccounts"
    }
]
```

There is the decision, in an object, and you can read it before knowing anything about how such objects work. A rule naming those exact URLs, granted to the **group `system:serviceaccounts`** — which is *every ServiceAccount in the cluster*, and which you saw attached to `probe` in lesson 01's `whoami`.

So the answer is the middle one: **everyone the cluster already trusts, and nobody else.** Which is worth defending, because both extremes are tempting and both are wrong.

*Why not public?* Nothing is leaked by a public key — that is what "public" means, and Act VIII was emphatic that publishing it is the whole point. But an anonymous, unauthenticated endpoint on a control plane is a thing to be probed, and an issuer's discovery document tells an attacker which algorithms you accept and what your issuer string is. There is no cryptographic reason to hide it and no operational reason to advertise it, so it sits behind the cheapest possible authentication.

*Why not control-plane-only?* Because then nothing else could ever verify a token, and the entire point of a signed credential — from lesson 02 — is that it can be checked *without* asking the issuer on every request. Lock the key away and you have thrown that away and kept only the costs.

**Which is the general shape: verification material must be as widely available as the set of things that need to verify, and not one step wider.**

### Verify it yourself

You have the key. Do what the API server does.

```bash
kubectl get --raw /openid/v1/jwks > "${TMPDIR:-/tmp}/jwks.json"
kubectl create sa probe
kubectl create token probe --duration=1h > "${TMPDIR:-/tmp}/tok.txt"

python3 - <<'PY'
import base64, json, os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

T = os.environ.get('TMPDIR', '/tmp')
d = lambda s: base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))

tok = open(T + '/tok.txt').read().strip()
header_b64, payload_b64, sig_b64 = tok.split('.')
hdr = json.loads(d(header_b64))

# 1. the token names a key. find that exact key in the published set.
jwks = json.load(open(T + '/jwks.json'))
matches = [k for k in jwks['keys'] if k['kid'] == hdr['kid']]
print("token's kid   :", hdr['kid'])
print("keys published:", len(jwks['keys']), "| matching this token:", len(matches))
key = matches[0]

# 2. rebuild the RSA public key from two integers.
n = int.from_bytes(d(key['n']), 'big')
e = int.from_bytes(d(key['e']), 'big')
print(f"public exponent e = {e},  modulus = {n.bit_length()} bits")
pub = rsa.RSAPublicNumbers(e, n).public_key()

# 3. the signature covers exactly "header.payload" -- the dot included, base64 as sent.
signed = f"{header_b64}.{payload_b64}".encode()

for label, blob in (("the real token", signed),
                    ("one byte changed", signed[:-1] + bytes([signed[-1] ^ 1]))):
    try:
        pub.verify(d(sig_b64), blob, padding.PKCS1v15(), hashes.SHA256())
        print(f"{label:<18}: signature VALID")
    except Exception as ex:
        print(f"{label:<18}: {type(ex).__name__}")
PY
```

```
serviceaccount/probe created
token's kid   : fNzzmn2keCMktTShWvQORjFrMZ1vC_RD0RVKbWDbBl0
keys published: 1 | matching this token: 1
public exponent e = 65537,  modulus = 2048 bits
the real token    : signature VALID
one byte changed  : InvalidSignature
```

**You just authenticated a real Kubernetes credential, by hand, with no privileged access.** The `probe` account has no permissions whatsoever, and it did not need any — verification needs the *public* key, which is exactly the asymmetry Act VIII lesson 05 called non-repudiation: you can check what you could never have produced.

Three details in that code are the lesson rather than the plumbing.

**The signature covers `header.payload` as base64, including the dot.** Not the decoded JSON. Which is why you must never re-serialise a JWT before checking it — `json.dumps` is entitled to reorder keys and change whitespace, and a single byte's difference is `InvalidSignature`. **Verify the bytes you received, then decode.** In that order, always.

**`e = 65537` and a 2048-bit modulus** — and there is the answer to lesson 03's held question. Act VIII lesson 04 said, in a parenthesis, that the classical constructions need thousands of bits where the elliptic-curve ones need 256, because the best known attacks against the classical ones are so much better. RSA is a classical construction; its hard problem is factoring that modulus. So 2048 bits here buys roughly the security budget X25519 bought with 256, and the key you just fetched is an order of magnitude bigger than anything in Act VIII for no gain whatsoever. That is the entire reason the industry keeps drifting toward the curves — and the reason a cluster still ships RSA is not cryptographic, it is that RS256 is the algorithm every JWT library on earth already implements.

**One byte flipped and the whole thing collapses**, which is Act VIII lesson 01's avalanche and needs no further comment except to note that the flip was in the *payload* — the part you could read and edit freely in lesson 03.

### The two attacks that break nothing

Now the second half of the prediction: having the public key lets you *check* tokens and never lets you *make* them. Signing needs the private half, which never leaves the control plane. So an attacker who wants to forge cannot attack the mathematics — 2048-bit RSA is Act VIII's "infeasible is a number" and the number is large.

They attack the *verifier* instead. Two classics, and neither involves any cryptography at all.

**Attack one: tell the verifier there is no signature.** The header declares its own algorithm. So declare `none`:

```bash
python3 - "$(cat "${TMPDIR:-/tmp}/tok.txt")" <<'PY' > "${TMPDIR:-/tmp}/none.txt"
import base64, json, sys
h, p, s = sys.argv[1].split('.')
d = lambda x: base64.urlsafe_b64decode(x + '=' * (-len(x) % 4))
e = lambda b: base64.urlsafe_b64encode(b).rstrip(b'=').decode()
hdr = json.loads(d(h)); hdr['alg'] = 'none'; hdr.pop('kid', None)
pay = json.loads(d(p)); pay['sub'] = 'system:serviceaccount:kube-system:root-ish'
print(f"{e(json.dumps(hdr,separators=(',',':')).encode())}."
      f"{e(json.dumps(pay,separators=(',',':')).encode())}.")
PY
curl -s --cacert "${TMPDIR:-/tmp}/ca.crt" \
  -H "Authorization: Bearer $(cat "${TMPDIR:-/tmp}/none.txt")" \
  "$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')/api/v1/namespaces/default/pods" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['code'], d['message'])"
```

```
401 Unauthorized
```

Rejected, of course — but understand *why*, because the reason is not "because it is obviously silly." The specification really does define `alg: "none"`, for tokens whose integrity is guaranteed by something else, and a library that dutifully implements the whole specification will dutifully accept it. **The vulnerability is a verifier that reads the algorithm out of the very document it is trying to authenticate.** That is a category error, not a bug: you have let the attacker choose how they will be checked.

The API server is immune because it does not ask. It knows it signs with `RS256` — it *published* that fact in the discovery document — and anything else is rejected before the header is trusted for anything. **The fix is always the same shape: the verifier decides the algorithm, and the token is only allowed to say which *key*.**

**Attack two, which needs no forgery at all.** Suppose some service in your cluster trusts this issuer and verifies signatures correctly. Take the perfectly genuine `probe` token from lesson 01 and present it to that service. The signature is real. The issuer is right. It has not expired. Every cryptographic check passes — because the token *is* valid. It was simply never meant for that service.

The defence is a field you already read: `aud`. The token's audience is `https://kubernetes.default.svc.cluster.local`, and a verifier that checks the audience matches *itself* rejects a token minted for somebody else. Which is why `kubectl create token` takes `--audience`, and why a token meant for a third party should be minted for that party and nobody else.

And note what that is. **Binding a credential to the context it is valid in** — which by now has a track record: Act VIII's associated data (lesson 03), its HKDF `info` string (lesson 04), TLS 1.3's `CertificateVerify` signing the transcript (lesson 06), and its drill 5, where a ciphertext moved to a different database row stopped verifying. Fifth appearance of one idea, and the first one outside cryptography: *an authenticated value proves something about the bytes, and nothing about where you found them.*

> **Check yourself —** a colleague's service verifies the signature and the expiry, correctly, using the published JWKS. It does not check `iss` or `aud`. Describe the attack in one sentence, and say what the attacker needs — because it is much less than you would hope.

<details>
<summary>Answer</summary>

The attacker needs **any valid token from any issuer whose keys that service can fetch**, and often just: an account on some *unrelated* system that uses the same identity provider.

Without an `iss` check, the service will happily fetch keys named by the token's own header from whatever discovery document it is pointed at — so a token signed by a completely different issuer verifies fine, and the attacker becomes whatever `sub` says. Without an `aud` check, a token legitimately issued to the attacker for a *different* service is accepted here, and they arrive as themselves — genuinely authenticated, in the wrong place, with whatever permissions their `sub` maps to.

The second is the more dangerous, because nothing is forged and nothing looks anomalous. Logs show a valid token belonging to a real user. There is no failed request to alert on.

So verification is **four** checks, and only the first is cryptography:

1. the signature, against a key you obtained from the issuer you *expected* — not one the token named
2. `iss` — is this the issuer I trust?
3. `aud` — is this token for *me*?
4. `exp` / `nbf` — is it inside its window, per lesson 02?

Miss any one and the other three are theatre. **A signature answers "was this made by that key" and answers nothing else** — not who it is for, not whether it is current, not even whose key it was unless you decided that in advance.

</details>

<!-- figure -->
```
   DISCOVERY: /.well-known/openid-configuration
     a token's `iss` -> that issuer's URL -> jwks_uri
       -> the PUBLIC KEY. this is a WORLD convention,
       not a Kubernetes one -- your cluster serves the
       same document format as Google or Okta.
     it also PUBLISHES which algorithms it uses.
       remember that; it is attack one's antidote.

   JWKS: a SET, because keys must ROTATE
     publish new beside old, sign with new, drop old
     once every token it signed has EXPIRED.
     `kid` in the header names WHICH key ->
     ROTATION WITHOUT A FLAG DAY, and Act VIII's
     short lifetimes are what make it terminate.
     n + e = an RSA public key as two integers.

   WHO MAY FETCH IT  -> 403 for system:anonymous
     the rule is an ORDINARY object you can read:
       ClusterRole system:service-account-issuer-
       discovery, on nonResourceURLs, bound to the
       GROUP system:serviceaccounts.
     = lesson 01 exactly: "nobody" is a NAME and the
       rules about it say no. no special case.
     not public: nothing leaks, but do not advertise
       your algorithms on an unauthenticated port.
     not control-plane-only: then NOTHING could
       verify, and you kept the costs of stateless
       tokens while discarding the benefit.
     RULE: as widely available as the set of things
     that must verify, AND NOT ONE STEP WIDER.

   VERIFYING BY HAND, WITH NO PRIVILEGE
     the PUBLIC key checks what it could never make
     (Act VIII: that asymmetry IS non-repudiation).
     the signature covers "header.payload" AS BASE64,
     dot included -- NOT the decoded JSON. so never
     re-serialise before checking: json.dumps may
     reorder keys and one byte is InvalidSignature.
     VERIFY THE BYTES YOU RECEIVED, THEN DECODE.

   THE ATTACKS SKIP THE MATHEMATICS ENTIRELY
     1  alg: "none"  -- the header declares how it
        should be checked, and a spec-complete library
        obeys. the flaw is a verifier that reads the
        algorithm OUT OF THE DOCUMENT IT IS CHECKING.
        FIX: the VERIFIER picks the algorithm. the
        token may only say which KEY.
     2  a REAL token, presented somewhere else.
        nothing forged. every crypto check passes.
        FIX: check `aud`. = associated data (VIII L03),
        = HKDF's `info` string (VIII L04),
        = CertificateVerify signing the transcript,
        = VIII drill 5's relocated row.
        FIFTH appearance -- first one outside crypto.

   SO VERIFICATION IS FOUR CHECKS
     signature (vs a key from the issuer you EXPECTED)
     iss   is this who I trust?
     aud   is this FOR me?
     exp   is it current?
     miss one and the other three are theatre.
```

**Cleanup:**

```bash
kubectl delete sa probe --ignore-not-found
```

> **You understand this when you can** describe how a verifier gets from a token to the key that
> signed it, and name the field that links them; explain the `alg: none` attack and state the fix
> as a rule about who chooses the algorithm; describe an attack that uses a completely genuine
> token and name the claim that prevents it; and list the four checks that make up verification,
> saying what a signature alone does and does not tell you.

**Which raises:** every credential so far has arrived from the thing that will consume it — the cluster minted a token for use against the cluster. Now suppose the credential must be *accepted* by someone who did not issue it: you want a third-party tool to read your repositories, and its honest request is "give me your password." **That is intolerable, and it is not obvious what to do instead** — the tool needs to act as you, at some service that has never heard of it, without ever holding what makes you you, and with you able to change your mind later.

---

↑ **[Act IX overview](README.md)** · Prev: **[Taking the credential apart](03-jwt.md)** · Next: **[Delegation without handing over a password](05-oauth2-and-oidc.md)** →
