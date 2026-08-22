# Taking the credential apart

There are nine hundred characters in that shell variable and you have been treating them as opaque. They are not opaque at all. Almost nobody who uses these daily has ever looked inside one, and looking inside is two commands.

> **Predict first —** it is a signed credential, so somewhere in there is a signature. Before you look: is the rest of it **encrypted**? Argue it from Act VIII rather than from what you have heard. Then answer the harder one: whatever the answer is, does it *matter* — and to whom?

### Three parts, separated by dots

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act9.kubeconfig"
kubectl create sa probe
TOK=$(kubectl create token probe --duration=1h)
echo "$TOK" | tr '.' '\n' | awk '{print NR": "length($0)" chars"}'
```

```
serviceaccount/probe created
1: 90 chars
2: 491 chars
3: 342 chars
```

Three fields. That is the whole format, and the name for it is a **JWT** — a JSON Web Token.

Two of the three are JSON, and the third is not. The first two carry the header and the claims, and you are about to read both. The third is the signature — **not a document but a fixed-length block of raw bytes**, base64 of a number, which is why it has no structure to read and why nothing below decodes it. It is the only part of a JWT that is not text, and it is the only part that means anything. Lesson 04 is about what to do with it.

Read the first one:

```bash
echo "$TOK" | cut -d. -f1 | base64 -d
```

```
{"alg":"RS256","kid":"fNzzmn2keCMktTShWvQORjFrMZ1vC_RD0RVKbWDbBl0"
```

**That is JSON, in plain text, and you did not need a key.** So the answer to the prediction is no — nothing here is encrypted, and Act VIII gives you the reason without any need to guess: **a signature keeps integrity and authenticity, and confidentiality is a separate promise requiring a separate mechanism.** Signing something does not hide it. There was never a cipher in this picture.

Note what else the header says, and note the one thing in it that is genuinely new. `RS256` is **RSA** with SHA-256. The *shape* is Act VIII lesson 05's exactly — you sign a digest rather than the message, and you verify with the published half of a pair — but Act VIII signed with Ed25519 from beginning to end and never once mentioned RSA. So this is a new algorithm in a slot you already understand, which is a much smaller thing to absorb than a new idea. Hold the obvious question rather than looking it up: **why would the cluster use a different one?** Lesson 04 puts a real RSA key in front of you and the answer falls out of its size.

And `kid` is a **key id**: the signer telling you *which* key it used, which is a strong hint that there is more than one and that they change. Lesson 04 is about following that hint.

Now the second field, and this one has a trap in it:

```bash
echo "$TOK" | cut -d. -f2 | base64 -d
```

```
...,"nbf":1787387234,"sub":"system:serviceaccount:default:probe
```

**Look at the end.** It stops mid-string — no closing quote, no closing brace. That is not corruption; it is `base64` refusing to guess. Base64 encodes three bytes into four characters, so unless the input length is a multiple of three the encoding needs `=` padding to say how much of the last group is real. **JWTs strip the padding**, because they travel in URLs and headers where `=` needs escaping, and they use a URL-safe alphabet too (`-` and `_` instead of `+` and `/`). So a bare `base64 -d` decodes everything it can and silently drops the remainder.

Which means the correct way to read one is to put the padding back:

```bash
echo "$TOK" | cut -d. -f2 | python3 -c "
import base64, sys, json
s = sys.stdin.read().strip()
s += '=' * (-len(s) % 4)                    # restore the stripped padding
print(json.dumps(json.loads(base64.urlsafe_b64decode(s)), indent=2))"
```

```json
{
  "aud": [
    "https://kubernetes.default.svc.cluster.local"
  ],
  "exp": 1787390358,
  "iat": 1787386758,
  "iss": "https://kubernetes.default.svc.cluster.local",
  "jti": "bb32aeb5-8243-45aa-9b98-6bac4d92debc",
  "kubernetes.io": {
    "namespace": "default",
    "serviceaccount": {
      "name": "probe",
      "uid": "ef877820-aef2-4a4d-8f8b-df10dcbe3a9e"
    }
  },
  "nbf": 1787386758,
  "sub": "system:serviceaccount:default:probe"
}
```

### Read it as a sentence

That is your identity, in a file, and lesson 01's mystery is solved: `sub` is exactly the string the API server put in the `403` message. It did not look anything up to find your name. **It read your name out of the credential you handed it.**

Five of those keys are standard and appear in every JWT ever issued, by anybody. They are worth knowing by name because they are the entire basis of lesson 04:

| Claim | Means | Why it is there |
|---|---|---|
| `iss` | **issuer** — who minted this | so you know whose signature to expect |
| `sub` | **subject** — who it is about | the identity itself |
| `aud` | **audience** — who it is *for* | so a token for one service is not valid at another |
| `exp` | **expiry** — after which it is void | Act VIII's `notAfter`, in a different costume |
| `iat` / `nbf` | issued-at, not-before | the other end of the same window |

Then `kubernetes.io`, which is not standard at all — it is a **private claim**, and any issuer may add any keys it likes. That is the format's real design: five fields everyone agrees on, and unlimited room for a specific system's own facts.

Note `exp` and `nbf`. `1787390358 - 1787386758 = 3600`, which is the `--duration=1h` you asked for, and it is lesson 02's window written down as a number inside the credential. And look at `aud`: the audience is the cluster's own issuer URL. **A token minted for this cluster carries a field saying so**, which is the mechanism that stops it being replayed at some other service that happens to trust the same signer.

### Now edit it

The payload is base64 of JSON. Nothing is stopping you.

```bash
API=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
CA="${TMPDIR:-/tmp}/ca.crt"
FORGED=$(python3 - "$TOK" <<'PY'
import base64, json, sys
h, p, s = sys.argv[1].split('.')
d = lambda x: base64.urlsafe_b64decode(x + '=' * (-len(x) % 4))
e = lambda b: base64.urlsafe_b64encode(b).rstrip(b'=').decode()
pay = json.loads(d(p))
pay['sub'] = 'system:serviceaccount:kube-system:root-ish'      # promote yourself
print(f"{h}.{e(json.dumps(pay, separators=(',',':')).encode())}.{s}")
PY
)
echo "the forged token says its subject is:"
echo "$FORGED" | cut -d. -f2 | python3 -c "
import base64,sys,json; s=sys.stdin.read().strip(); s+='='*(-len(s)%4)
print('  ', json.loads(base64.urlsafe_b64decode(s))['sub'])"

curl -s --cacert "$CA" -H "Authorization: Bearer $FORGED" \
  "$API/api/v1/namespaces/default/pods" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('server:', d['code'], d['message'])"
```

```
the forged token says its subject is:
   system:serviceaccount:kube-system:root-ish
server: 401 Unauthorized
```

**The edit succeeded and the token stopped working.** Two things there, and the second is the more useful.

The obvious one: the signature covers the header and payload, so changing a byte of either invalidates it. That is Act VIII lesson 01's avalanche and lesson 05's signature, and there is nothing new to learn — you already broke a signature by changing one letter of a message.

The one worth noticing: **`401`, not `403`.** Lesson 01's diagnostic, working. The signature check is part of *authentication*, so when it fails there is no identity at all, and the message contains no username — even though the token loudly claims one. The server never got as far as having an opinion about `root-ish`, because it never accepted that anybody was `root-ish`.

> **Check yourself —** so the contents are public and unforgeable. Given that, is it safe to put a user's email address in a JWT? Their role? A feature flag? Say what the actual rule is, in a form that decides all three.

<details>
<summary>Answer</summary>

The rule is not about sensitivity, though people usually state it that way. It is: **anything you put in a token is (a) readable by everyone who handles it and (b) frozen at the moment of issue.** Both halves have to be acceptable.

An email address: readable is usually fine — the holder knows their own email — but note it is readable by *every intermediary*, including logs and error trackers and the browser's developer console, which is a wider audience than people picture. Frozen is fine, since emails rarely change.

A role: readable is fine. **Frozen is the problem**, and it is lesson 02's window with sharp teeth — demote someone and their existing token still says `admin` until it expires. This is the single most common real-world JWT mistake, and it is not a cryptographic failure. Every check passes.

A feature flag: frozen is fatal, and the reason is mundane rather than dramatic. Flags change many times a day, so you have built a system where turning a feature off does not turn it off for anybody currently logged in, and no amount of debugging the flag service will explain it.

So the rule that decides all three: **put identity in a token, not state.** Identity is what the credential is *for*, and it is stable by nature. State belongs somewhere it can be read fresh — which costs a lookup, which is exactly the trade this act keeps making, and the correct place to make it is per-fact rather than once for the whole system.

</details>

### What you cannot tell by reading it

One more thing, and it is the reason there is a lesson 04. You just read that token perfectly, in one command, without holding any key. So ask what the reading told you.

It told you what the token **claims**. It told you nothing whatsoever about whether those claims are *true*, because reading requires no verification and you performed none. Your forged token read back exactly as cleanly as the real one — `python3` was delighted to tell you the subject was `root-ish`.

**Which is the same distinction Act VIII made about certificates**, in almost the same words: reading a field tells you what a document *asserts*, not what has been *vouched for*. There it was a certificate whose text said `bank.example.com` while `openssl verify` said `error 7`. Here it is a token whose `sub` says `root-ish` while the API server says `401`.

And this is the origin of a whole family of real vulnerabilities, none of which involve breaking any mathematics: code that decodes a JWT, reads a claim, and acts on it — because the claim was right there and looked official — having verified nothing. The library function is often called something like `decode`, and the one that checks is often called something like `verify`, and they are one letter apart in an autocomplete list.

<!-- figure -->
```
   A JWT IS THREE BASE64URL FIELDS, DOT-SEPARATED
     header . payload . signature
     NOTHING IS ENCRYPTED. a signature keeps
     INTEGRITY + AUTHENTICITY; confidentiality is a
     SEPARATE promise needing a SEPARATE mechanism.
     (Act VIII: signing does not hide.)

   THE PADDING TRAP
     JWTs use base64URL (- and _) and STRIP the '='
     padding, because they live in URLs and headers.
     so a bare `base64 -d` decodes what it can and
     SILENTLY DROPS THE TAIL -- you see JSON ending
     mid-string. always re-pad:  s += '=' * (-len(s)%4)

   THE FIVE CLAIMS EVERY JWT HAS
     iss  issuer   -- whose signature to expect
     sub  subject  -- the identity. this is the exact
                      string in lesson 01's 403.
     aud  audience -- who it is FOR. stops replay at
                      another service trusting the
                      same signer.
     exp  expiry   -- Act VIII's notAfter, renamed
     iat/nbf       -- the other end of the window
     + PRIVATE CLAIMS: any issuer may add anything
       (here: kubernetes.io/serviceaccount)

   EDIT THE PAYLOAD -> 401, NOT 403
     the edit WORKS. the token reads back as
     root-ish. and the signature is now wrong, so
     AUTHENTICATION fails -> no identity at all ->
     no username in the message.
     the server never had an opinion about root-ish
     because it never accepted anyone WAS root-ish.

   READING IS NOT VERIFYING
     you read that token with NO KEY. so reading
     tells you what it CLAIMS and nothing about
     whether the claims are TRUE.
     the forged one read back just as cleanly.
     = Act VIII's error 7: a cert can SAY
       bank.example.com. reading a field tells you
       what it ASSERTS, not what was VOUCHED FOR.
     the library call is `decode`. the one that
     checks is `verify`. one letter apart in an
     autocomplete list, and that is a CVE family.

   WHAT TO PUT IN ONE
     identity: YES -- stable by nature, and it is
       what the credential is for
     role / flags / any STATE: NO -- frozen at issue.
       demote someone and their token still says
       admin until exp. every check passes.
     PUT IDENTITY IN A TOKEN, NOT STATE.
```

**Cleanup:**

```bash
kubectl delete sa probe --ignore-not-found
```

> **You understand this when you can** name the three parts of a JWT and say which of them is not JSON; argue from Act VIII why nothing in it is encrypted, and say which promise a signature does and does not keep; explain why `base64 -d` truncates a JWT payload and what to do about it; name `iss`, `sub`, `aud` and `exp` and say what job each does, with `aud`'s job stated as an attack it prevents; explain what a private claim is; say why editing the payload produces `401` rather than `403` and connect that to lesson 01's diagnostic; state the difference between reading a token and verifying it, and connect it to Act VIII's `error 7`; and give the rule for what belongs in a token, with the reason a role is a worse idea than an email address.

**Which raises:** the API server rejected your forgery, so *it* can tell the difference between reading and verifying. You cannot yet. It holds a key you do not have — except that the header told you the key has a *name*, `kid`, which is a strange thing to publish if nobody is expected to look it up. **So: can you check that signature yourself, with no privileged access at all? And if you can, what stops you also issuing tokens?**

---

↑ **[Act IX overview](README.md)** · Prev: **[Not sending the password every time](02-tokens-and-sessions.md)** · Next: **[Trusting a token you did not issue](04-verifying-a-token.md)** →
