# Delegation without handing over a password

Every credential in this act so far has come from the thing that would consume it. The cluster minted a token for use against the cluster; you verified it against a key the cluster published. Issuer and audience were the same party, which made the whole arrangement easy in a way you probably did not notice.

Now break that. You want some tool — a reporting script, a CI job, a third-party dashboard — to read your repositories on your behalf. It is honest and well-meaning, and its request is the obvious one: *give me your password.*

**Everybody's instinct is that this is wrong, and almost nobody can say precisely why.** Start there, because the reason is a list, and the list is what the rest of the lesson is forced to satisfy.

### What is actually wrong with handing over the password

Four things, and only the first is the one people say out loud.

**It is not scoped.** You wanted it to read repositories. A password permits everything you can do, including things that did not exist when you handed it over.

**It cannot be withdrawn without punishing yourself.** The only way to stop the tool is to change your password, which stops *you*, and every other tool you ever gave it to. There is no way to revoke one relationship.

**It destroys attribution.** Every action the tool takes is recorded as you. Afterwards, no log anywhere can separate what you did from what it did — which is precisely the question you will want answered.

**It authorises changing itself.** A password is the credential that can be used to replace the password. Hand it over and you have handed over the ability to lock you out.

And one more from lesson 02, which now bites twice: a password has to be checked against a deliberately slow hash. Give it to the tool and the tool must either store it in the clear to replay it, or... there is no "or". **A password is not storable by anyone except the party that checks it.**

So the tool has to end up holding *something*, and that something cannot be what you hold. Which forces the shape of the answer:

> The credential the tool uses must be **created by whoever checks passwords**, **at your request**, **naming the tool**, and **narrower than you**.

Nothing in that sentence is a protocol yet. But notice it has already ruled out every design in which the tool receives your password and forwarded it — because the creator of the new credential must be the issuer, and the only way the issuer can act "at your request" is if **you talk to the issuer yourself.**

> **Predict first —** there are four parties: you, the tool, the issuer that checks passwords, and the API that holds your repositories. You are sitting in a browser at the tool's website. Write down the sequence of hops that gets a credential into the tool's hands, given that (a) your password may only ever reach the issuer, and (b) the tool and the issuer never talk to each other about you until *after* you have approved it. Then answer the hard part: **whatever the issuer sends back has to travel through your browser to reach the tool. What is wrong with that, and what does it force the returned thing to be?**

### Deriving the hops

Work it forward. There is not much freedom.

**Your password may only reach the issuer.** So the tool cannot render a login form. It must instead *send you to* the issuer — a redirect, with the tool naming itself in the URL so the issuer knows who is asking.

**The result must get back to the tool.** The issuer has no connection to the tool; the only thing joining them is your browser. So the issuer redirects you *back*, to an address belonging to the tool. Which raises an obvious hole: if the tool can nominate any address at that moment, an attacker registers a client and points the return at themselves. So **the return address must be registered with the issuer in advance**, and the issuer must refuse anything else. Client registration is not bureaucracy. It is the only thing binding "who is asking" to "where the answer may be delivered."

**Now the hard part you predicted.** Whatever comes back arrives as part of a URL in your browser. URLs land in history, in server access logs, in `Referer` headers sent to third parties, in the shoulder of the person next to you. **So the thing that comes back must not be the credential.** It has to be something useless to whoever finds it: single-use, short-lived, and meaningless to anyone who cannot prove they are the tool.

That is a *handle* — lesson 02's word, arriving from a completely different direction. It carries no answer; it refers to one.

**Which leaves one hop.** The tool takes the handle and calls the issuer directly, server to server, on a channel your browser never touches, and there it proves it is itself. Only then does it receive the credential.

**You have just derived the authorization code flow.** Four hops, and each one exists because of a specific thing that would otherwise leak. The name for the handle is the *authorization code*, and the reason it exists — the only reason — is that the front channel is a place where secrets go to die.

### An issuer, a person, and a registered client

Time to use a real one. This part needs Docker and a free port 8080; nothing here touches your cluster.

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN | head -3    # expect no output
docker run -d --name idp -p 8080:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:26.4 start-dev
```

Wait for it — mine took three seconds:

```bash
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/realms/master)" = "200" ]
do sleep 1; done; echo "up"
```

Keycloak is an identity provider: the thing that owns passwords and mints tokens. It needs exactly the three objects the derivation demanded — a namespace to be the issuer, a person with a password, and a **registered** client:

```bash
docker exec idp bash -c 'cd /opt/keycloak/bin
./kcadm.sh config credentials --server http://localhost:8080 \
    --realm master --user admin --password admin
./kcadm.sh create realms -s realm=lab -s enabled=true
./kcadm.sh create users -r lab -s username=rahul -s enabled=true \
    -s email=rahul@example.com -s firstName=Rahul -s lastName=Example \
    -s emailVerified=true
./kcadm.sh set-password -r lab --username rahul --new-password hunter2
./kcadm.sh create clients -r lab -s clientId=report-tool -s enabled=true \
    -s publicClient=false -s secret=tool-secret \
    -s directAccessGrantsEnabled=true -s standardFlowEnabled=true \
    -s "redirectUris=[\"http://localhost:9000/callback\"]"'
```

```
Logging into http://localhost:8080 as user admin of realm master
Created new realm with id 'lab'
Created new user with id '69d40db8-a11b-4f61-861a-aa8c0f427433'
Created new client with id '5f734eb8-f0ba-40da-9a8a-f72a84986948'
```

(A *realm* is Keycloak's word for one independent issuer with its own users, keys and clients. `redirectUris` is the registration that matters, and nothing is listening on port 9000 — you will read the redirect rather than follow it, which is better anyway.)

### The same document, from an unrelated implementation

Lesson 04 got a cluster's public keys by starting at a well-known path. Try the identical path here:

```bash
curl -s http://localhost:8080/realms/lab/.well-known/openid-configuration \
 | python3 -c 'import json,sys; d=json.load(sys.stdin)
for k in ["issuer","authorization_endpoint","token_endpoint","jwks_uri",
          "revocation_endpoint","introspection_endpoint"]:
    print(f"{k:24} {d.get(k)}")
print(f"\n{len(d)} fields in total")'
```

```
issuer                   http://localhost:8080/realms/lab
authorization_endpoint   http://localhost:8080/realms/lab/protocol/openid-connect/auth
token_endpoint           http://localhost:8080/realms/lab/protocol/openid-connect/token
jwks_uri                 http://localhost:8080/realms/lab/protocol/openid-connect/certs
revocation_endpoint      http://localhost:8080/realms/lab/protocol/openid-connect/revoke
introspection_endpoint   http://localhost:8080/realms/lab/protocol/openid-connect/token/introspect

56 fields in total
```

There are your first two derived hops, published as URLs: the place you get sent, and the place the handle is exchanged. Now put the cluster's document next to it:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act9.kubeconfig"
kubectl get --raw /.well-known/openid-configuration \
 | python3 -c 'import json,sys; d=json.load(sys.stdin)
print(len(d), "fields:", sorted(d))'
```

```
5 fields: ['id_token_signing_alg_values_supported', 'issuer', 'jwks_uri', 'response_types_supported', 'subject_types_supported']
```

**Five against fifty-six, and the two missing ones are the interesting ones: the cluster has no `authorization_endpoint` and no `token_endpoint`.** It publishes enough to let you *verify* what it signed, and nothing to let you *obtain* anything, because a Kubernetes cluster is not a place where people log in — you got your token in lesson 01 by asking an API you were already authenticated to.

**Which is a general reading skill: what a party publishes tells you which role it plays.** One document, the same schema, two parties, and the field list alone distinguishes an issuer of credentials from a mere publisher of keys.

### Be the browser

Now walk the flow by hand, playing the part of the browser so that every hop is visible. Hop one: the tool sends you to the `authorization_endpoint`, naming itself and where to come back to.

```bash
cd "${TMPDIR:-/tmp}"
IDP=http://localhost:8080/realms/lab/protocol/openid-connect
curl -s -c jar -o page.html -w 'http %{http_code}  bytes %{size_download}\n' \
  "$IDP/auth?response_type=code&client_id=report-tool\
&redirect_uri=http://localhost:9000/callback&scope=openid&state=xyz123"
grep -o 'action="[^"]*"' page.html | head -1 | cut -c1-96
grep -o 'name="password"' page.html
```

```
http 200  bytes 6770
action="http://localhost:8080/realms/lab/login-actions/authenticate?session_code=sXBTiTi9zdmIpfA
name="password"
```

A login form, served by the issuer, on the issuer's origin. **That is the whole point of hop one made concrete: the box you type your password into belongs to the issuer, and the tool cannot see it, style it, or read it.** (It is also why phishing works on this flow: the *user* has to notice which origin the form came from, and users do not. Nothing in the protocol can help — the protocol's job was to keep the password from the tool, and it did that perfectly.)

Hop two: submit the credential to the issuer, and read where it sends you.

```bash
ACT=$(grep -o 'action="[^"]*"' page.html | head -1 \
      | sed 's/action="//; s/"$//; s/&amp;/\&/g')
curl -s -b jar -o /dev/null -D hdr.txt \
  -d username=rahul -d password=hunter2 "$ACT"
grep -i '^location' hdr.txt
```

```
Location: http://localhost:9000/callback?state=xyz123&session_state=99362f03-9e1a-e58c-77eb-8b20f370ac74&iss=http%3A%2F%2Flocalhost%3A8080%2Frealms%2Flab&code=55878f9e-7589-4860-5507-fbf165d7b292.99362f03-9e1a-e58c-77eb-8b20f370ac74.5f734eb8-f0ba-40da-9a8a-f72a84986948
```

Read that URL closely, because it is the whole design in one line.

- It is going to **the registered address**, not one supplied just now.
- `state=xyz123` came back exactly as sent. That is yours, not the issuer's: you invented it before the redirect and you compare it after, which is how the tool knows this callback belongs to a flow *it* started rather than one an attacker started in your browser.
- `code=` is three dot-separated UUIDs. **It is not a token — it says nothing.** It is a reference, and lesson 02 already named the species: a handle is a question. This one asks *"what did the issuer decide about that login?"*, and only the issuer can answer it.

Hop three is the back channel, and here the tool proves it is itself:

```bash
CODE=$(grep -i '^location' hdr.txt | sed 's/.*[?&]code=//; s/[&[:space:]].*//' | tr -d '\r')
curl -s -X POST $IDP/token \
  -d grant_type=authorization_code -d code="$CODE" \
  -d redirect_uri=http://localhost:9000/callback \
  -d client_id=report-tool -d client_secret=tool-secret > tok.json
python3 -c 'import json;d=json.load(open("tok.json"))
[print(f"{k:20} {str(v)[:44]}") for k,v in d.items()]'
```

```
access_token         eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lk
expires_in           300
refresh_expires_in   1800
refresh_token        eyJhbGciOiJIUzUxMiIsInR5cCIgOiAiSldUIiwia2lk
token_type           Bearer
id_token             eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lk
not-before-policy    0
session_state        950457f2-ec16-a121-e0e8-dcd8fab7c467
scope                openid email profile
```

(You asked for `scope=openid` and were given `openid email profile` — a client carries default scopes it always gets. What you receive is the *intersection* of what you requested and what the client is permitted, never simply what you asked for.)

Three tokens, and lesson 02's pair is right there as two numbers: **300 seconds and 1800 seconds.** A short-lived thing you present constantly and a longer-lived thing whose only job is asking for a fresh short one. You did not read that in a document; it fell out of a design decision you already reconstructed from scratch.

Now spend the code a second time:

```bash
curl -s -X POST $IDP/token -d grant_type=authorization_code -d code="$CODE" \
  -d redirect_uri=http://localhost:9000/callback \
  -d client_id=report-tool -d client_secret=tool-secret
```

```
{"error":"invalid_grant","error_description":"Code not valid"}
```

> **Check yourself —** the code is single-use, which you expected. But try the *refresh token you already hold* after that replay and it is dead too: `"Session doesn't have required client"`. The replay did not merely fail — it destroyed credentials that were working. Why is that the right behaviour, and what does the issuer believe when it sees a code used twice?

<details>
<summary>Answer</summary>

A code is exchanged exactly once, by exactly one party, over the back channel. So a *second* exchange is not a mistake anyone makes by accident — it means the code was seen by two parties. Which is to say: it leaked, from the one place the design admits it might, the URL in the front channel.

The issuer cannot tell which of the two exchanges was the legitimate tool. **It cannot even tell which came first in real time** — the attacker may well be faster than the tool. So there is no answer of the form "reject the impostor." The only safe move is to assume the whole session is compromised and tear down everything issued from it.

That is a *fail-closed* choice, and it is worth naming as a pattern because you have now seen it twice. Act VIII lesson 05's revocation problem had systems failing **open**: OCSP unreachable, so treat the certificate as good. Here, ambiguity resolves the other way. The difference is who pays: failing open on OCSP keeps the web working at the cost of accepting revoked certificates, and failing closed here logs a user out at the cost of nothing much.

The general rule this makes visible: **a single-use credential is also a leak detector.** Its second use carries information no other event carries, and throwing that information away is the actual mistake.

</details>

### Three tokens, and one field that explains all three

Before decoding anything, look again at the first few characters of each token above and notice they are not identical. Two begin `eyJhbGciOiJSUzI1NiI` and one begins `eyJhbGciOiJIUzUxMiI` — which lesson 03 taught you to read without a tool: `{"alg":"RS256"` twice, and `{"alg":"HS512"` once.

**One of these three is protected by a symmetric MAC rather than a signature.** Act VIII lesson 02 built the first and lesson 05 built the second, and the difference between them was never about strength — it was about *who can verify*. A MAC can be checked only by someone holding the same secret key. A signature can be checked by anybody.

> **Check yourself —** predict which of `id_token`, `access_token` and `refresh_token` is the HMAC'd one, from that property alone. Then decode all three and read the `aud` claim to check your reasoning.

<details>
<summary>Answer</summary>

The refresh token, because it has exactly one verifier: the issuer itself. It is never presented to anybody else. Asymmetric signing buys the ability for third parties to verify, and there are no third parties, so it buys nothing — and a MAC is faster.

Run it and the `aud` claim says the same thing out loud:

```bash
python3 - <<'EOF'
import json, base64
d = json.load(open("tok.json"))
def part(t, i):
    s = t.split(".")[i]
    return json.loads(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)))
for name in ("id_token", "access_token", "refresh_token"):
    h, p = part(d[name], 0), part(d[name], 1)
    print(f"{name:15} alg={h['alg']:6} typ={p['typ']:8} aud={p['aud']}  azp={p['azp']}")
EOF
```

```
id_token        alg=RS256  typ=ID       aud=report-tool  azp=report-tool
access_token    alg=RS256  typ=Bearer   aud=account  azp=report-tool
refresh_token   alg=HS512  typ=Refresh  aud=http://localhost:8080/realms/lab  azp=report-tool
```

**The refresh token's audience is the issuer's own URL.** Lesson 04 made `aud` the answer to "is this for me?"; here it is also the answer to "who needs to be able to verify this?", and those turn out to be the same question. The algorithm choice and the audience field agree, and either one predicts the other.

The other two are worth as much:

- `aud=report-tool` on the **id_token** — it is addressed *to the tool*. Its content is an answer to "who is the user?", and the tool is the party that asked.
- `aud=account` on the **access_token** — addressed to an API. Its content is a permission to act, and the tool merely carries it. **The tool is not the audience of the token it uses.** That distinction is why "just send the id_token to the API" is a real and common vulnerability rather than a shortcut: the API would be accepting a document that says, on its face, that it was written for somebody else.
- `azp` — *authorized party* — is `report-tool` on all three. This is delegation written down: the token records both **who** (`sub`) and **through whom**. The attribution you destroyed by handing over a password is back, as a field.

</details>

### Verification did not change

You wrote code in lesson 04 to verify a Kubernetes ServiceAccount token: fetch the JWKS, match on `kid`, rebuild an RSA public key from `n` and `e`, check the signature over the base64 text. Point it at Keycloak without editing a line of it.

```bash
curl -s $IDP/certs > jwks.json
python3 - <<'EOF'
import json, base64, time
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
def b64(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

tok  = json.load(open("tok.json"))["access_token"]
head = json.loads(b64(tok.split(".")[0]))
jwks = json.load(open("jwks.json"))
print("published:", [(k["kty"], k.get("use"), k.get("alg")) for k in jwks["keys"]])
key = [k for k in jwks["keys"] if k["kid"] == head["kid"]]
print("matching this token:", len(key))

n = int.from_bytes(b64(key[0]["n"]), "big")
e = int.from_bytes(b64(key[0]["e"]), "big")
pub = rsa.RSAPublicNumbers(e, n).public_key()
signed, sig = tok.rsplit(".", 1)
for label, data in (("the real token  ", signed),
                    ("one byte changed", signed[:-1] + ("A" if signed[-1] != "A" else "B"))):
    try:
        pub.verify(b64(sig), data.encode(), padding.PKCS1v15(), hashes.SHA256())
        print(f"{label}: signature VALID")
    except Exception as ex:
        print(f"{label}: {type(ex).__name__}")
EOF
```

```
published: [('RSA', 'enc', 'RSA-OAEP'), ('RSA', 'sig', 'RS256')]
matching this token: 1
the real token  : signature VALID
one byte changed: InvalidSignature
```

Two things landed there. The obvious one: **twenty lines of verification code are portable across completely unrelated issuers**, because JWT and JWKS are the format and the format is all your code knew about. That portability is the entire commercial reason OIDC won.

The subtler one: this JWKS has **two** keys, and one of them is `use: enc` — for encryption, not signing. Lesson 04 gave you `kid` as the reason a JWKS is a set. Here is a second, independent reason: keys differ by *purpose*, and a verifier that grabbed `keys[0]` because there was only one key last week would now be trying to check a signature with an encryption key.

### The whole act, in one measurement

You now hold a token you have verified with your own hands. Ask the issuer about it — that `introspection_endpoint` from the discovery document:

```bash
AT=$(python3 -c 'import json;print(json.load(open("tok.json"))["access_token"])')
RT=$(python3 -c 'import json;print(json.load(open("tok.json"))["refresh_token"])')
curl -s -X POST $IDP/token/introspect -d client_id=report-tool \
  -d client_secret=tool-secret -d token="$AT" \
 | python3 -c 'import json,sys;d=json.load(sys.stdin)
print("active:",d.get("active"),"| username:",d.get("username"),"| claims:",len(d))'
```

```
active: True | username: rahul | claims: 25
```

Now be the user who changes their mind. Revoke — the thing a password could never do for one relationship — and then ask both parties, the issuer and the mathematics, about **the same unchanged token**:

```bash
curl -s -o /dev/null -w 'revoke -> http %{http_code}\n' -X POST $IDP/revoke \
  -d client_id=report-tool -d client_secret=tool-secret \
  -d token="$RT" -d token_type_hint=refresh_token
curl -s -X POST $IDP/token -d grant_type=refresh_token -d refresh_token="$RT" \
  -d client_id=report-tool -d client_secret=tool-secret; echo
curl -s -X POST $IDP/token/introspect -d client_id=report-tool \
  -d client_secret=tool-secret -d token="$AT" \
 | python3 -c 'import json,sys;print("introspection says active:",json.load(sys.stdin).get("active"))'
python3 -c 'import json,base64,time
p=json.loads(base64.urlsafe_b64decode(json.load(open("tok.json"))["access_token"].split(".")[1]+"=="))
print("the token itself says exp is", p["exp"]-int(time.time()), "seconds in the FUTURE")'
```

```
revoke -> http 200
{"error":"invalid_grant","error_description":"Session not active"}
introspection says active: False
the token itself says exp is 267 seconds in the FUTURE
```

(That last number is however much of the five minutes you have not spent reading; anything positive makes the point.)

Stop and look at the last two lines together, because they are the act's thesis and there is nothing left to argue about.

**One token. One instant. Two answers, and neither is wrong.** Verify it locally — signature good, issuer right, expiry still minutes away — and the correct answer is *yes*. Ask the issuer and the correct answer is *no*. The local check is answering "was this issued, unaltered, and is it still inside its window?" The issuer is answering "do I still stand behind it?" Those were never the same question, and you can only tell them apart when they disagree.

**And there is no third option that fixes it.** Introspect on every request and you have re-bought a lookup on the critical path, with the availability failure lesson 02 measured. Verify locally and you accept a window. The discovery document publishes both endpoints because both are legitimate, and choosing between them per-request is the actual engineering — an internal service can verify locally; a payments call can afford to ask.

### When the client cannot keep a secret

Hop three depended on the tool holding a `client_secret`. That works for a server. It is hopeless for a mobile app, a CLI, or anything running as JavaScript in a browser, where any "secret" ships to the attacker along with the product. Such a client — a **public** client — cannot prove it is itself.

So the code needs binding to the flow some other way. Make one:

```bash
docker exec idp bash -c 'cd /opt/keycloak/bin
./kcadm.sh create clients -r lab -s clientId=report-cli -s enabled=true \
  -s publicClient=true -s standardFlowEnabled=true \
  -s "redirectUris=[\"http://localhost:9000/callback\"]" \
  -s "attributes.\"pkce.code.challenge.method\"=S256"'
```

Then start the flow *without* the extra parameter, and read the failure carefully:

```bash
curl -s -o /dev/null -D h.txt \
  "$IDP/auth?response_type=code&client_id=report-cli\
&redirect_uri=http://localhost:9000/callback&scope=openid"
head -1 h.txt; grep -i '^location' h.txt
```

```
HTTP/1.1 302 Found
Location: http://localhost:9000/callback?error=invalid_request&error_description=Missing+parameter%3A+code_challenge_method&iss=http%3A%2F%2Flocalhost%3A8080%2Frealms%2Flab
```

**The error was delivered by redirect, to the registered address — exactly the way a success would have been.** It is not rendered on the issuer's page. That is deliberate and it generalises: in a front-channel protocol the failure path must use the same channel as the happy path, or the tool never finds out what went wrong.

What was missing is **PKCE**: the client invents a random `verifier`, sends only its hash as the `challenge` up front, and reveals the verifier at the exchange.

```bash
V=$(python3 -c 'import secrets,base64
print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("="))')
C=$(python3 -c "import hashlib,base64
print(base64.urlsafe_b64encode(hashlib.sha256('$V'.encode()).digest()).decode().rstrip('='))")
curl -s -c jar2 -o page2.html "$IDP/auth?response_type=code&client_id=report-cli\
&redirect_uri=http://localhost:9000/callback&scope=openid\
&code_challenge=$C&code_challenge_method=S256"
ACT=$(grep -o 'action="[^"]*"' page2.html | head -1 | sed 's/action="//; s/"$//; s/&amp;/\&/g')
curl -s -b jar2 -o /dev/null -D hdr2.txt -d username=rahul -d password=hunter2 "$ACT"
CODE=$(grep -i '^location' hdr2.txt | sed 's/.*[?&]code=//; s/[&[:space:]].*//' | tr -d '\r')

echo "-- exchange with a DIFFERENT random verifier:"
curl -s -X POST $IDP/token -d grant_type=authorization_code -d code="$CODE" \
  -d redirect_uri=http://localhost:9000/callback -d client_id=report-cli \
  -d code_verifier="$(python3 -c 'import secrets,base64
print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("="))')"; echo
echo "-- and now with the right one:"
curl -s -X POST $IDP/token -d grant_type=authorization_code -d code="$CODE" \
  -d redirect_uri=http://localhost:9000/callback -d client_id=report-cli \
  -d code_verifier="$V"; echo
```

```
-- exchange with a DIFFERENT random verifier:
{"error":"invalid_grant","error_description":"PKCE verification failed: Code mismatch"}
-- and now with the right one:
{"error":"invalid_grant","error_description":"Code not valid"}
```

**Both failed, and that second failure is the more instructive one.** The correct verifier was refused because the *earlier wrong attempt already spent the code*. Which is the previous section's rule applied without exception: a code is used once, whatever the outcome, because a failed PKCE check is exactly what a thief with a stolen code looks like. Repeat the block from the top for a clean run and the right verifier returns the full token set — with **no client secret anywhere in the exchange.**

Notice what PKCE is and is not. It does not authenticate the client; a public client still cannot prove who it is. It proves something weaker and sufficient: **whoever is redeeming this code is whoever started this flow.** A stolen code is now useless, because the thief never saw the verifier — it existed only in memory, in the process that made it, and never entered the front channel. Compare it to Act VIII's key exchange: send a value derived from a secret, keep the secret, and let the arithmetic connect them later.

### The shortcut that gives the whole game away

One loose end. That first client was created with `directAccessGrantsEnabled=true`, which switches on a grant type that does the obvious thing:

```bash
curl -s -X POST $IDP/token -d grant_type=password \
  -d username=rahul -d password=hunter2 -d scope=openid \
  -d client_id=report-tool -d client_secret=tool-secret \
 | python3 -c 'import json,sys;print(sorted(json.load(sys.stdin)))'
```

```
['access_token', 'expires_in', 'id_token', 'not-before-policy', 'refresh_expires_in', 'refresh_token', 'scope', 'session_state', 'token_type']
```

One request, the user's password in it, and **the identical set of tokens** you spent four hops obtaining. Same fields, same algorithms, same audiences, same expiry. A verifier receiving one of these cannot distinguish it from the ones you got the careful way.

Sit with that, because it is the sharpest statement of what this lesson is about. **The entire value of the flow you derived lies in a property that the resulting token cannot express: who saw the password.** No amount of checking the token recovers it. This is Act VIII's lesson in a new costume — a signature tells you who signed and never how carefully — and it is why the password grant is removed in OAuth 2.1 rather than merely discouraged. There is no way to detect its use downstream, so the only place to stop it is at the issuer.

While you are here, one last thing about scope, since a scope is the mechanism for "narrower than you":

```bash
curl -s -X POST $IDP/token -d grant_type=password -d username=rahul \
  -d password=hunter2 -d client_id=report-tool -d client_secret=tool-secret \
  -d scope="openid delete-everything"
```

```
{"error":"invalid_scope","error_description":"Invalid scopes: openid delete-everything"}
```

**A scope is not a wish typed into a request.** It has to already exist at the issuer and already be permitted for this client. Which means the ceiling on what a tool may ever ask for is set by an administrator at registration time, not by the tool at runtime — and that, finally, is the fourth item on this lesson's opening list.

<!-- figure -->
```
   WHY NOT JUST HAND OVER THE PASSWORD
     not scoped     -> everything you can do, forever
     not revocable  -> only by changing it, for EVERYONE
     no attribution -> its actions are recorded as YOURS
     self-amending  -> it can change itself and lock you out
     + unstorable: only the party that CHECKS a password
       can hold one (lesson 02's slow hash)

   SO THE CREDENTIAL MUST BE ISSUED, NOT SHARED
     by whoever checks passwords / at your request /
     naming the tool / narrower than you
     -> which forces YOU to talk to the issuer YOURSELF

   THE FOUR HOPS, EACH FORCED BY A LEAK
     1. tool REDIRECTS you to the issuer
          (your password may not touch the tool)
     2. issuer redirects back to a PRE-REGISTERED addr
          (else an attacker nominates their own)
     3. what comes back is in a URL: history, logs,
        Referer. so it must NOT be the credential ->
        a single-use HANDLE = the authorization CODE
     4. tool exchanges it on the BACK channel, proving
        it is itself. only now does a token exist.
     = the authorization code flow, derived, not learned

   THREE TOKENS, AND aud EXPLAINS ALL THREE
     id_token       aud=report-tool  RS256  "who is the user"
     access_token   aud=account      RS256  "may act at the API"
     refresh_token  aud=<the issuer> HS512  "give me another"
     the refresh token's only verifier IS the issuer,
     so a MAC suffices. aud and alg agree -- either
     one predicts the other.
     azp=the client on all three = DELEGATION, written down.
     the tool is NOT the audience of the token it uses.

   A CODE USED TWICE IS A LEAK DETECTOR
     two exchanges = two holders. the issuer cannot tell
     which is the thief, so it kills the whole session.
     FAILS CLOSED -- the opposite choice from OCSP.

   THE ACT'S THESIS, MEASURED
     revoke, then ask about the SAME token:
       introspection -> active: false
       the signature -> VALID, exp still MINUTES away
     both correct. different questions.
     local check: "was this issued, unaltered, in window?"
     issuer:      "do I still stand behind it?"
     no third option: introspect always = lesson 02's
     availability failure; verify locally = a window.

   PKCE, FOR A CLIENT THAT CANNOT HOLD A SECRET
     send hash(verifier) up front, verifier at exchange
     it does NOT authenticate the client. it proves
     REDEEMER == INITIATOR. a stolen code is useless.
     (front-channel errors arrive by REDIRECT, like
      successes -- same channel or the tool never knows)

   THE PASSWORD GRANT RETURNS IDENTICAL TOKENS
     the value of the whole flow is a property the
     token CANNOT EXPRESS: who saw the password.
     undetectable downstream -> stop it at the ISSUER.
     and scope=<anything> -> invalid_scope: the ceiling
     is set at REGISTRATION, not at runtime.
```

**Cleanup:**

```bash
docker rm -f idp
```

> **You understand this when you can** give four distinct reasons a password is the wrong thing to delegate with, one of which is about attribution; state the requirement that forces the credential to be issued rather than shared, and explain why that requirement puts you in direct contact with the issuer; derive all four hops of the authorization code flow, naming the specific leak each one prevents; explain why the returned code must be a handle rather than a token, and what `state` is for; say why a code used twice destroys the whole session, and contrast that fail-closed choice with OCSP's; predict which of the three tokens is HMAC'd from the audience alone, and explain why `aud` and `alg` agree; say why sending an id_token to an API is a vulnerability rather than a shortcut; describe an experiment in which local verification and introspection disagree about the same token at the same instant, and argue that both answers are correct; explain what PKCE proves and what it does not; and explain why the password grant cannot be detected by anything downstream of the issuer.

**Which raises:** you have a token containing `sub`, `azp`, and a `scope` of `openid email profile`. Every one of those is a **string**. Verification proved a string arrived unaltered from an issuer you trust — and had, and could have, no opinion whatsoever about what the string permits. So somewhere a system holds rules that turn `rahul` and `openid email profile` into *yes* or *no*. **Before the next lesson, try to say how many fundamentally different shapes such a rule set can have** — not how many products exist, but how many ways there are to write a function down at all. The answer is smaller than you would guess, the two shapes fail in opposite directions, and almost every argument you have ever heard about IAM is an argument about which one somebody is using.

---

↑ **[Act IX overview](README.md)** · Prev: **[Trusting a token you did not issue](04-verifying-a-token.md)** · Next: **[Two ways to write down a permission](06-rbac-and-abac.md)** →
