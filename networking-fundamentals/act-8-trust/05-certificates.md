# A claim someone else vouched for

Mallory won last lesson for one reason, and it is worth stating as narrowly as possible: **`bob.pub` was 32 bytes on a wire, and 32 bytes look the same whoever sent them.**

Not because the mathematics failed. Because the bytes arrived with nothing attached to them. Alice needed to know that this particular public value belongs to *Bob*, and the file did not say so — and if it had said so, in plain text, Mallory would simply have edited the words along with the bytes.

> **Predict first —** do not reach for a mechanism yet. Say what would have to be *true* for Alice to accept `bob.pub` safely, given that she has never met Bob, cannot phone him, and is holding nothing but bytes that crossed a wire Mallory controls. There are two separate requirements and they are easy to conflate. Getting them apart is most of this lesson.

One of the two you can build, and this act has already taught you three mechanisms that nearly do it. Start there, and the second requirement will announce itself when the first one runs out.

### The mechanism lesson 02 could not build

What Alice wants is a tag on `bob.pub` that only Bob could have made, but that **Alice can check without being able to make it herself.** Lesson 02's HMAC failed exactly there: verifying and signing were the same operation with the same key, so every holder could forge every other's messages, and non-repudiation was impossible in principle.

Lesson 04 introduced the shape that breaks the symmetry — a private number and a published value derived from it. So ask the obvious question of the keys you already generated:

```bash
mkdir -p "${TMPDIR:-/tmp}/pki" && cd "${TMPDIR:-/tmp}/pki"
printf 'msg' > m.txt
openssl genpkey -algorithm X25519 -out x.pem
openssl pkeyutl -sign -inkey x.pem -rawin -in m.txt -out bad.bin
```

```
pkeyutl: Error initializing context
...:digital envelope routines:do_sigver_init:operation not supported
for this keytype:crypto/evp/m_sigver.c:305:
```

**A refusal, for the second time in this act, and again it is informative.** An X25519 key pair does key agreement and nothing else. The tool will not let you sign with it, even though a private number and a public value are exactly what signing needs. **A key pair is issued for one job**, and mixing jobs is the same error as lesson 03's "separate keys for cipher and MAC," enforced this time by the library rather than left to you.

The signing counterpart of X25519 is Ed25519 — same curve underneath, different operation:

```bash
cd "${TMPDIR:-/tmp}/pki"
openssl genpkey -algorithm ED25519 -out signer.key
openssl pkey -in signer.key -pubout -out signer.pub
openssl pkeyutl -sign -inkey signer.key -rawin -in m.txt -out sig.bin
wc -c < sig.bin
openssl pkeyutl -verify -pubin -inkey signer.pub -rawin -in m.txt -sigfile sig.bin
```

```
      64
Signature Verified Successfully
```

Now change one letter of the message and check again with the same signature:

```bash
cd "${TMPDIR:-/tmp}/pki"
printf 'msh' > m2.txt
openssl pkeyutl -verify -pubin -inkey signer.pub -rawin -in m2.txt -sigfile sig.bin
```

```
...:digital envelope routines:EVP_DigestVerify:provider signature failure...
Signature Verification Failure
```

**Sixty-four bytes that only the holder of `signer.key` could produce, that anybody holding `signer.pub` can check, and that stop being valid the instant the message changes.**

Take a moment on how much that is. It is lesson 01's integrity, lesson 02's authenticity, and — for the first time in this act — **the promise lesson 02 said a shared secret could never make.** Verification uses a *different* key from signing, so a verifier cannot forge. That asymmetry is non-repudiation: Bob cannot later claim Alice made it up, because Alice never had the means.

In practice you rarely sign a whole message. You hash it and sign the digest — which is why `openssl dgst -sign` exists and why every signature scheme names a hash alongside the key. The signature is over 32 bytes no matter how large the document, and lesson 01's collision resistance is suddenly load-bearing in a new place: find two documents with the same digest and one signature covers both. That is not a footnote. It is why the death of SHA-1 was an emergency for code signing and not merely for downloads.

### The recursion

So Bob signs his public key and sends `bob.pub` plus a signature. Alice verifies it and knows the signature was made by the holder of... which public key?

**Bob's.** Which is the thing she was trying to establish.

Sit with that rather than stepping over it, because it is the shape of the whole problem. A signature proves that a message was produced by whoever holds the private half of *some particular public key*. It converts the question "is this really Bob's key?" into "is that really Bob's key?" — and Mallory, who is replacing bytes in transit, will happily supply both her own public key and a perfectly valid signature made with it. Everything verifies. Nothing is established.

**A signature can never introduce a stranger.** It can only confirm something about a key you *already* had a reason to trust. So the chain has to start somewhere outside the mathematics, and this is the second of the two requirements you were asked to separate: a mechanism gets you from a key you trust to a key you do not, and nothing whatsoever gets you the first one.

Which means the honest version of the question is: **can Alice reuse trust she established once, long ago, to accept keys she has never seen?** That is answerable, and it is what a certificate is.

### Being the trusted party

Do it from the top, because you have all the pieces and it is four commands. Start by becoming a certificate authority. Note how much ceremony that takes:

```bash
cd "${TMPDIR:-/tmp}/pki"
openssl genpkey -algorithm ED25519 -out ca.key
openssl req -new -x509 -key ca.key -out ca.crt -days 3650 -subj "/CN=My Toy Root CA"
openssl x509 -in ca.crt -noout -subject -issuer
```

```
subject=CN=My Toy Root CA
issuer=CN=My Toy Root CA
```

**Subject and issuer are the same string.** That is what "self-signed" means and it is worth being blunt about what it proves: nothing. The signature on that document was made with the key inside that document. Anybody can make one, saying anything, in one command — and you just did.

Now be the server. A **certificate signing request** is a public key plus the name you are claiming, signed with your own private key to show you hold it:

```bash
cd "${TMPDIR:-/tmp}/pki"
openssl genpkey -algorithm ED25519 -out server.key
openssl req -new -key server.key -out server.csr -subj "/CN=shop.example.com"
openssl req -in server.csr -noout -subject -verify
```

```
Certificate request self-signature verify OK
subject=CN=shop.example.com
```

Note what the CSR does *not* contain: `server.key`. The private key never leaves the machine that generated it, which is the entire reason this is a request-and-sign dance rather than "send me your keys."

Now be the CA again, and sign:

```bash
cd "${TMPDIR:-/tmp}/pki"
printf 'subjectAltName=DNS:shop.example.com\n' > san.ext
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -out server.crt \
  -days 365 -extfile san.ext
openssl x509 -in server.crt -noout -subject -issuer -ext subjectAltName
```

```
Certificate request self-signature ok
subject=CN=shop.example.com
subject=CN=shop.example.com
issuer=CN=My Toy Root CA
X509v3 Subject Alternative Name:
    DNS:shop.example.com
```

(The subject prints twice — once as `x509 -req`'s own progress line, once from the query that follows.)

**Subject and issuer now differ, and that difference is the entire mechanism.** A certificate is three things and nothing more: **a name, a public key, and a signature by somebody else over both.** Strip away the ASN.1 and the file formats and there is no fourth ingredient.

### The line that is doing the work

Verify the chain:

```bash
openssl verify -CAfile ca.crt server.crt
```

```
server.crt: OK
```

Now run the identical check without telling `openssl` which CA to trust, so it falls back to your system's trust store:

```bash
openssl verify server.crt
```

```
CN=shop.example.com
error 20 at 0 depth lookup: unable to get local issuer certificate
error server.crt: verification failed
```

**Same certificate. Same signature. Same CA. Opposite verdicts.** Nothing cryptographic changed between those two commands — the only difference is a filename you supplied, naming who you had decided to believe.

Act III told you this five acts ago — that trust comes not from a server claiming its own identity but from a CA *in your trust store* having signed the claim. You have been repeating it ever since. The difference is that you can now make it fail on demand, which is a different kind of knowing: **verification is not a property of a certificate. It is a relationship between a certificate and a list you chose.** Every "certificate error" you have ever seen is one of those two commands, and the interesting question is always which list was consulted.

Which raises the obvious follow-up: whose list, and how long is it?

```bash
openssl version -d
grep -c 'BEGIN CERTIFICATE' "$(openssl version -d | cut -d'"' -f2)/cert.pem"
```

```
OPENSSLDIR: "/opt/homebrew/etc/openssl@3"
195
```

**A hundred and ninety-five organisations** — that is this machine's Homebrew OpenSSL today; yours will differ, and LibreSSL on the very same laptop says 128 — whose signature your machine accepts as proof of anybody's identity, none of which you chose individually, all shipped by whoever built your OS or browser. These are **trust anchors**, and the word is exact: a chain of signatures has to be nailed to something that is not itself a signature. Every one of those 195 is self-signed, which — as you established two commands ago — proves nothing at all. **Their authority comes entirely from being in the file.** That is the social fact no mechanism can produce, and the whole of public-key infrastructure is a solution to the problem of there being no way to produce it.

> **Check yourself —** Act III already told you two things a padlock does not mean: nothing about whether the operator is honest, and nothing past the point where TLS terminates. That list was incomplete, and the number 195 is the missing item. **What third thing does a padlock not tell you, and why does the size of that file make it the worst of the three?**

<details>
<summary>Answer</summary>

It tells you nothing about whether the CA that signed this certificate *deserves* to be able to. Any one of those 195 can issue a valid certificate for any name in the world, and your browser will accept it with a green padlock, because being in the file is the entire qualification.

Why the count makes it worse than the other two: the first two limitations are things you can reason about. You can look at a URL and decide whether you trust the operator; you can ask an architect where TLS terminates. This one you cannot inspect at all, and it does not compose the way you would hope. **The system's security is the *minimum* over 195 organisations, not the average and certainly not the maximum** — one compromised or coerced CA anywhere in the world is enough, and you will never have heard of it. That is not theoretical: CAs have been caught mis-issuing, and the only remedy anyone has is removing them from the file afterwards.

Which is a strange thing to discover at the end of a lesson about how certificates work. Every mechanism in it is sound. The weak part is the list.

</details>

### Two ways it refuses, both worth causing

The claim in a certificate is plain text, and the signature is over that text. So what happens if you edit the text? Change `shop` to `bank` directly in the signed bytes:

```bash
cd "${TMPDIR:-/tmp}/pki"
openssl x509 -in server.crt -outform der -out server.der
python3 -c "
d = bytearray(open('server.der','rb').read())
i = d.find(b'shop.example.com'); d[i:i+4] = b'bank'
open('evil.der','wb').write(d); print('edited at offset', i)"
openssl x509 -in evil.der -inform der -out evil.pem
openssl x509 -in evil.pem -noout -subject
openssl verify -CAfile ca.crt evil.pem
```

```
edited at offset 114
subject=CN=bank.example.com
CN=bank.example.com
error 7 at 0 depth lookup: certificate signature failure
error evil.pem: verification failed
...:EVP_DigestVerify:provider signature failure:...ED25519 digest_verify:
...:ASN1_item_verify_ctx:EVP lib:crypto/asn1/a_verify.c:219:
```

(The offset depends on your OpenSSL version and the exact fields in the certificate — the number matters less than the fact that the name is *findable in plain text*, which is the point. The last two lines are `openssl` explaining, at a level of detail nobody wants, that an Ed25519 verification returned false.)

**The certificate now claims to be `bank.example.com`, and it says so when asked.** Reading a certificate's fields tells you what it *asserts*, which is not the same as what has been *vouched for* — a distinction worth holding onto next time you `describe` something and read a name out of it.

The second refusal is more interesting, because the certificate is untouched and correctly signed. Your `server.crt` was signed by a CA marked as a CA. Does the *leaf* get to sign things too?

```bash
cd "${TMPDIR:-/tmp}/pki"
openssl x509 -in ca.crt -noout -ext basicConstraints
openssl genpkey -algorithm ED25519 -out victim.key
openssl req -new -key victim.key -out victim.csr -subj "/CN=bank.example.com"
openssl x509 -req -in victim.csr -CA server.crt -CAkey server.key -out victim.crt -days 30
openssl verify -CAfile ca.crt -untrusted server.crt victim.crt
```

```
X509v3 Basic Constraints: critical
    CA:TRUE
Certificate request self-signature ok
subject=CN=bank.example.com
CN=shop.example.com
error 79 at 1 depth lookup: invalid CA certificate
error victim.crt: verification failed
```

**`openssl` cheerfully produced the certificate and the verifier rejected the chain.** Read those two facts together, because the gap between them is the point. Signing is just arithmetic — a private number and a message — so **nothing can be *enforced* here.** There is no way to prevent the holder of `server.key` from performing that operation on any input at all; the rule "only CAs may sign certificates" is unenforceable in principle. What exists instead is a boolean in the signed document, `CA:TRUE`, and a verifier that **checks** it. Without that check, anybody with a certificate for any name could mint certificates for every name, and the entire structure would be worth nothing — and note where that leaves the security: not in preventing the bad act, but in refusing to be impressed by it afterwards.

Notice the shape, because it is the same one Act V taught with `allowedRoutes` and Act VII with `ownerReferences`: **the check is not on the actor, it is on a field in a document.** What differs is what makes the field trustworthy. Those Kubernetes fields are trustworthy because only the API server can write them and it checks who is asking; `CA:TRUE` has no API server, so a signature has to do that job instead. Same pattern, and the interesting question each time is *what stops the wrong person setting the field.*

### Trust and naming are different questions

One more separation, and it pays off something you have already met. Verify the good certificate again, twice, asking about the hostname:

```bash
openssl verify -CAfile ca.crt -verify_hostname shop.example.com server.crt
openssl verify -CAfile ca.crt -verify_hostname evil.example.com server.crt
```

```
server.crt: OK
CN=shop.example.com
error 62 at 0 depth lookup: hostname mismatch
error server.crt: verification failed
```

Same certificate, same CA, same trust store, and one of them fails. **"Is this chain trusted?" and "is this certificate for the name I asked for?" are two independent checks**, and a verifier has to do both. A perfectly valid, correctly-signed, fully-trusted certificate for `shop.example.com` is worthless evidence when you meant to reach `bank.example.com` — which is precisely what stops Mallory from presenting her own real certificate and calling it Bob's.

That distinction explains a message you have already debugged. Act VII's autoscaling lesson had metrics-server fail with:

```
x509: cannot validate certificate for 172.19.0.2 because it doesn't contain any IP SANs
```

Read what that message is and is not. It is the *name* check failing — `error 62`, not `error 20` — because the connection was made to an IP address and the certificate listed no IP addresses at all. That is the check that happened to be reported.

But go back to what Act VII said was underneath it: unless a cluster turns on `serverTLSBootstrap`, each kubelet's serving certificate is **self-signed**, not issued by the cluster CA. So the trust check was never going to pass either. **Two independent checks were both going to fail, and you only got told about one** — which is exactly why the fix everybody pastes, `--kubelet-insecure-tls`, waives both rather than adding the missing name. If it only silenced the error you saw, it would not work.

That is worth more than the error code. A verifier reports the first thing that fails, so **an error message tells you a check that failed, never the set of checks that would have.**

### The same file, doing the opposite job

Everything so far has a server proving its name to a client. Nothing about a certificate requires that direction. Look at what a Subject can carry:

```bash
cd "${TMPDIR:-/tmp}/pki"
openssl genpkey -algorithm ED25519 -out admin.key
openssl req -new -key admin.key -out admin.csr -subj "/CN=rahul/O=system:masters"
openssl x509 -req -in admin.csr -CA ca.crt -CAkey ca.key -out admin.crt -days 1
openssl x509 -in admin.crt -noout -subject -nameopt sep_multiline
```

```
Certificate request self-signature ok
subject=CN=rahul, O=system:masters
subject=
    CN=rahul
    O=system:masters
```

**A username and a group membership, in a signed document.** Turn the mechanism round: instead of a server proving a hostname to a client, a client proves a *name* to a server — the server verifies the chain against a CA it trusts, and then reads the Subject to learn who it is talking to. Same certificate, same verification, opposite direction. That is a client certificate, and it is `mTLS` when both ends do it.

Two consequences that are the reason this lesson exists inside a Kubernetes course.

**Your kubeconfig is this.** Act VI told you the mechanism — `CN` is your username, `O` is your group, and the API server believes both because of the issuer — and then said plainly that what was inside the signature stayed sealed until a later act. This is that act. The sealed part was never *which field is the username*; it was why a signature is evidence of anything at all, and you have now built one by hand.

**And a Subject field can carry authority.** Act VI showed you two of them: your everyday `admin.conf` with `O=kubeadm:cluster-admins`, which is a group named by a `ClusterRoleBinding` object in the store, and the break-glass `super-admin.conf` with `O=system:masters`, which is wired into the API server itself and bypasses the permission check entirely. Either way the mechanism here is the same and the consequence is the one worth carrying: anyone who can get a CSR signed by the cluster CA, with the right string in it, holds that identity — permanently, with no way to revoke it short of replacing the CA. Which reframes something you did in Act VI: `ca.key` on a control-plane node is not "a certificate file." It is the ability to mint any identity in the cluster at will, including the one that skips the rules.

### What is still broken

Three things, and the first two are the same thing seen from different ends.

**Nothing expires on its own.** Cause it:

```bash
cd "${TMPDIR:-/tmp}/pki"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -out old.crt \
  -not_before 20240101000000Z -not_after 20240201000000Z -extfile san.ext
openssl x509 -in old.crt -noout -dates
openssl verify -CAfile ca.crt old.crt
```

```
Certificate request self-signature ok
subject=CN=shop.example.com
notBefore=Jan  1 00:00:00 2024 GMT
notAfter=Feb  1 00:00:00 2024 GMT
CN=shop.example.com
error 10 at 0 depth lookup: certificate has expired
error old.crt: verification failed
```

`error 10` is the single most common outage in this entire subject, and it is not a failure of anything — it is the design working. The date is a promise about how long the CA is willing to stand behind the binding, and a CA that promised forever could never take it back. Note which side detects it, though: **the verifier checks the clock.** Nothing on the server notices, nothing warns, and the certificate keeps being served happily to clients that keep refusing it.

**And you cannot take it back early.** Act VI made you predict this and gave you the fact: your kubeconfig leaks, and nothing revokes it, because the API server checks a signature and two dates and consults no list of cancelled certificates. Here is the reason that is not laziness on Kubernetes' part.

Suppose `server.key` leaks tomorrow. The certificate is still valid, still signed, still trusted, for the remaining 364 days — and Mallory holding it can now be `shop.example.com` legitimately. **The signature cannot be un-made; that is precisely what made it useful.** A thing that could be withdrawn would have to be checked against the withdrawer every time, which is the offline verification you were buying. So the only remedy is for verifiers to consult a *second* source saying "ignore this one," which means every verification now needs a network call to the CA, which is why revocation is the part of this system that has never worked properly. CRLs are too big; OCSP adds a round trip and a privacy leak and, when it fails, gets treated as success. In practice the industry gave up and made certificates short-lived instead: if it expires in 90 days, revocation matters for at most 90 days. **The fix for "revocation does not work" was to make expiry come round so fast that it hardly needs to.** That is why `cert-manager` exists, and why Act VI's cluster rotates its own certificates on a timer.

**And a CA can simply lie.** Nothing in the mechanism stops any of your 195 anchors from issuing a valid certificate for a name it has no business issuing. That is not a bug to be fixed — it is what a trust anchor *is*.

<!-- figure -->
```
   WHAT A CERTIFICATE IS
     a NAME + a PUBLIC KEY + a SIGNATURE by someone
     else over both.  there is no fourth ingredient.

   WHY A SIGNATURE AND NOT AN HMAC
     verifying uses a DIFFERENT key from signing, so a
     verifier CANNOT FORGE. that asymmetry is the
     non-repudiation lesson 02 said was impossible.
     an X25519 key REFUSES to sign -- a keypair is
     issued for ONE job. Ed25519 is the signing one.
     you sign the DIGEST, not the message, so lesson
     01's collision resistance is load-bearing here.

   WHY IT CANNOT BOOTSTRAP ITSELF
     Bob signs bob.pub -> valid signature by the holder
     of ... bob.pub. Mallory supplies her key AND a
     valid signature over it. everything verifies,
     NOTHING is established.
     A SIGNATURE CANNOT INTRODUCE A STRANGER.
     it moves trust from a key you have to one you
     don't. it cannot produce the first one.

   THE LINE THAT DOES THE WORK
     verify -CAfile ca.crt server.crt  -> OK
     verify              server.crt  -> error 20
     SAME CERT. SAME SIGNATURE. the difference is a
     LIST YOU CHOSE.
     verification is not a property of a certificate,
     it is a RELATIONSHIP with a list.
     that list: a couple of hundred self-signed certs
     you did not pick (195 here, 128 under LibreSSL on
     the same machine, and it drifts every update).
     self-signed proves NOTHING; their authority is
     BEING IN THE FILE. security = the MINIMUM over
     all of them, not the average.

   FOUR WAYS IT REFUSES, AND THEY ARE NOT THE SAME
     error 20  no path to a trusted root
     error  7  signature failure -- text was edited.
               reading a field tells you what a cert
               ASSERTS, not what was VOUCHED FOR
     error 79  invalid CA -- the leaf lacks CA:TRUE.
               signing is arithmetic: it cannot be
               ENFORCED, only CHECKED afterwards
     error 62  hostname mismatch -- TRUST and NAMING
               are independent checks.
               = Act VII's "no IP SANs" -- but there
               BOTH were failing (kubelet certs are
               self-signed); you were told about one.
               --kubelet-insecure-tls waives BOTH,
               which is why it works at all.
               AN ERROR NAMES A CHECK THAT FAILED,
               NOT THE SET THAT WOULD HAVE
     error 10  expired. THE VERIFIER checks the clock.
               the server serves it happily forever

   THE SAME FILE, REVERSED
     put CN=rahul/O=some-group in a Subject and a
     client proves an IDENTITY to a server. that is
     your kubeconfig; CN is your username; there is no
     User object because the CERT IS the record.
     Act VI's O=kubeadm:cluster-admins (a binding in
     the store) and O=system:masters (wired into the
     API server, skips the check) are both just this
     -> ca.key is not a file, it is the power to mint
     ANY identity at will, including that one.

   WHAT CERTIFICATES CANNOT DO
     BE TAKEN BACK. the signature cannot be un-made,
       so revocation needs a SECOND lookup: CRLs too
       big, OCSP a round trip + privacy leak + fails
       open. the industry's answer was SHORT LIVES --
       expire in 90 days and revocation barely matters
     STOP A CA LYING. any anchor can issue any name.
       not a bug; that is what an anchor IS
```

**Cleanup:**

```bash
cd "${TMPDIR:-/tmp}" && rm -rf pki
```

> **You understand this when you can** state the two separate requirements for accepting a stranger's public key and say which one no mechanism can supply; explain why a signature gives non-repudiation where an HMAC cannot, and why an X25519 key refuses to make one; say why signing a digest rather than a message makes collision resistance load-bearing; explain in your own words why Bob signing his own public key achieves nothing; list the three components of a certificate; explain why `openssl verify` gives opposite answers for the same file and what that says about where verification lives; say what a self-signed root proves and where a trust anchor's authority actually comes from; distinguish `error 20`, `error 7`, `error 79`, `error 62` and `error 10` by what each one means about the certificate; explain why `CA:TRUE` can only be checked and never enforced; explain why the trust check and the name check are separate, and say what Act VII's `no IP SANs` message did *not* tell you about the kubelet's certificate; describe how the same mechanism run backwards becomes client authentication, and why that makes a control-plane `ca.key` more dangerous than it looks; and explain why revocation has never worked and what the industry did instead.

**Which raises:** all four promises are now kept, and you have every part. Integrity from a hash. Authenticity from a signature over a digest. Confidentiality and tamper-detection from an AEAD. A shared key from an ephemeral exchange. An identity from a certificate chained to an anchor. That is the complete inventory — and Act III handed you a string that names three of them in one line, `TLS_AES_256_GCM_SHA384`, which you have been carrying unopened for five acts. **There is nothing left to introduce.** So the last lesson introduces nothing: it watches a real handshake happen, names which of these mechanisms is doing what at each step, and asks the only question left — in what *order* must they run, given that at the start of a connection the two parties share nothing at all and cannot yet encrypt the messages they need to send in order to be able to encrypt?

---

↑ **[Act VIII overview](README.md)** · Prev: **[Agreeing on a secret in public](04-key-exchange.md)** · Next: **[The lock, opened](06-tls-opened.md)** →
