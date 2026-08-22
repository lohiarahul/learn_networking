# Diagnose it — Act VIII

Six drills. Unlike the previous three acts these do not break a cluster, and unlike them there is nothing to `describe` — you get an error string and a filesystem, which is exactly what you get in production when a certificate goes wrong at three in the morning.

Set up a small PKI once and all six run against it:

```bash
mkdir -p "${TMPDIR:-/tmp}/drills" && cd "${TMPDIR:-/tmp}/drills"

openssl genpkey -algorithm ED25519 -out root.key
openssl req -new -x509 -key root.key -out root.crt -days 3650 -subj "/CN=Drill Root"

openssl genpkey -algorithm ED25519 -out int.key
openssl req -new -key int.key -out int.csr -subj "/CN=Drill Intermediate"
printf 'basicConstraints=critical,CA:TRUE,pathlen:0\n' > int.ext
openssl x509 -req -in int.csr -CA root.crt -CAkey root.key -out int.crt \
  -days 1825 -extfile int.ext

openssl genpkey -algorithm ED25519 -out leaf.key
openssl req -new -key leaf.key -out leaf.csr -subj "/CN=api.example.com"
printf 'subjectAltName=DNS:api.example.com\n' > leaf.ext
openssl x509 -req -in leaf.csr -CA int.crt -CAkey int.key -out leaf.crt \
  -days 365 -extfile leaf.ext
```

That is a two-level hierarchy: a root that signs an intermediate, and an intermediate that signs the leaf. Real PKI is always shaped this way, and the reason is worth knowing before you start — the root's private key can then be kept offline, in a safe, powered down, because it only ever signs one thing every few years.

## The method for this act

Act V's five questions walked a network path. Act VI descended a dependency stack. Act VII asked which loop was reading which field. This act needs something different again, because a cryptographic failure gives you almost no telemetry — just a verdict.

**Ask which of the four promises failed, and then which side noticed.** That second half is the one people skip, and it is where half of these drills live.

---

## Drill 1 — the same error, two unrelated causes

```bash
cd "${TMPDIR:-/tmp}/drills"
openssl verify -CAfile root.crt leaf.crt
```

```
CN=api.example.com
error 20 at 0 depth lookup: unable to get local issuer certificate
error leaf.crt: verification failed
```

You trust the root. The leaf chains to the root. It fails.

**Diagnose it before reading on.** Then fix it with one additional argument, and — this is the actual drill — write down the *other* thing `error 20` means, because you have already seen it, and the two fixes have nothing in common.

<details>
<summary>Answer</summary>

The verifier has the leaf and the root and no way to get between them. `leaf.crt`'s issuer is `Drill Intermediate`, which is not in the trust file and was not supplied, so there is no path. Supply it:

```bash
openssl verify -CAfile root.crt -untrusted int.crt leaf.crt
```

```
leaf.crt: OK
```

**Now the important half.** In lesson 05 you got the identical `error 20` from `openssl verify server.crt`, and the cause was completely different: there the chain was complete and the *root* was not trusted. Here the root is trusted and the *chain* is incomplete.

Same error code. Opposite fixes — add a trust anchor, or send a certificate you already have. And you cannot tell which from the error, because `error 20` says only "I could not get from here to something I trust," which is true of both.

The way to tell them apart, and the habit worth keeping: **count the certificates you were given, then read the leaf's issuer and ask whether anything you hold has that subject.**

```bash
openssl x509 -in leaf.crt -noout -issuer
openssl x509 -in root.crt -noout -subject
```

If the issuer names something you do not have, it is a missing intermediate. If it names something you have but do not trust, it is an anchor problem.

This is the single most common TLS misconfiguration in existence, and it has a signature symptom: **it works in `curl` and fails in the application, or works on your laptop and fails in the container.** Because a server that omits its intermediate still works for any client that happens to have cached that intermediate from a previous connection, and fails for every client that has not. Intermittent, environment-dependent, and entirely deterministic once you know.

</details>

---

## Drill 2 — a certificate that will work, later

```bash
cd "${TMPDIR:-/tmp}/drills"
openssl x509 -req -in leaf.csr -CA int.crt -CAkey int.key -out future.crt \
  -not_before 20300101000000Z -not_after 20310101000000Z -extfile leaf.ext
openssl verify -CAfile root.crt -untrusted int.crt future.crt
```

```
CN=api.example.com
error 9 at 0 depth lookup: certificate is not yet valid or the system clock
is incorrect
```

**Two questions.** First: the error message offers two explanations — which one is more likely in production, and why does the message hedge? Second: name the single component whose failure produces this across an entire fleet at once.

<details>
<summary>Answer</summary>

The message hedges because **the verifier cannot distinguish them.** It compares a date in a file against its own clock and finds them inconsistent. Which of the two is wrong is not information it has.

In production, "not yet valid" is almost always the *clock*, not the certificate — because certificates are issued with `notBefore` set to roughly now, so a genuinely future-dated certificate means somebody made a mistake at issuance, whereas a wrong clock happens by itself.

The component is **NTP**. A host whose time drifts, or which boots without network time and starts from an epoch default, will reject every valid certificate it is offered — and will also present certificates that others reject. It fails closed, everywhere, at once, which is why it looks like a total outage rather than a time problem.

Note the shape, which is the act's second question: **the verifier checks the clock.** Nothing in a certificate notices its own dates. So a fleet with skewed clocks produces `error 9` and `error 10` reports from clients while every server insists it is serving a perfectly valid certificate — and both are telling the truth.

</details>

---

## Drill 3 — trusted, valid, signed, and refused

```bash
cd "${TMPDIR:-/tmp}/drills"
openssl verify -CAfile root.crt -untrusted int.crt \
  -verify_hostname api.example.com leaf.crt
openssl verify -CAfile root.crt -untrusted int.crt \
  -verify_hostname internal.example.com leaf.crt
```

```
leaf.crt: OK
CN=api.example.com
error 62 at 0 depth lookup: hostname mismatch
```

The certificate is trusted, unexpired, correctly signed by a CA you accept, and refused.

**The drill:** somebody proposes fixing this by adding `internal.example.com` to the trust store. Explain, in terms of which check is failing, why that cannot possibly work — and then find the two-line fix. Then re-read a failure from Act VII in these terms.

<details>
<summary>Answer</summary>

Adding anything to the trust store changes the answer to *"do I trust the issuer?"*, and that question already passed. The failing check is *"is this certificate for the name I asked for?"*, which consults the certificate's `subjectAltName` and nothing else. **The two checks are independent and the trust store is not involved in the second one.**

The fix is at issuance — the name has to be in the certificate:

```bash
printf 'subjectAltName=DNS:api.example.com,DNS:internal.example.com\n' > leaf2.ext
openssl x509 -req -in leaf.csr -CA int.crt -CAkey int.key -out leaf2.crt \
  -days 365 -extfile leaf2.ext
openssl verify -CAfile root.crt -untrusted int.crt \
  -verify_hostname internal.example.com leaf2.crt
```

```
leaf2.crt: OK
```

**Act VII in these terms.** metrics-server failed with `x509: cannot validate certificate for 172.19.0.2 because it doesn't contain any IP SANs`. That is this drill: the kubelet's certificate was signed by the cluster CA and metrics-server trusted that CA, so the *trust* check passed. The connection was made to an IP address and the certificate listed hostnames, so the *name* check failed.

Which is why the fix everybody pastes is what it is. `--kubelet-insecure-tls` does not add the missing name — **it stops asking the question**, and it disables the trust check along with it. The correct fix is the one above: reissue with the IP in the SAN list. Knowing the difference is knowing whether you have fixed something or hidden it.

</details>

---

## Drill 4 — the failure that reports success

```bash
cd "${TMPDIR:-/tmp}/drills"
openssl genpkey -algorithm ED25519 -out client.key
openssl req -new -key client.key -out client.csr -subj "/CN=svc-a/O=readers"
openssl x509 -req -in client.csr -CA int.crt -CAkey int.key -out client.crt -days 1

openssl s_server -cert leaf.crt -key leaf.key -cert_chain int.crt \
  -CAfile root.crt -Verify 1 -accept 4433 -www > server.log 2>&1 &
sleep 2
echo | openssl s_client -connect localhost:4433 -CAfile root.crt 2>/dev/null \
  | grep 'Verify return'
tail -1 server.log
```

```
Verify return code: 0 (ok)
...:SSL routines:tls_process_client_certificate:peer did not return
a certificate:ssl/statem/statem_srvr.c:3916:
```

(`-cert_chain int.crt` is drill 1 applied: without it the server sends only its leaf, the client cannot reach the root, and you get `Verify return code: 21` before anything about client certificates is even considered.)

**Two verdicts, one connection, and they disagree.** Explain why both are correct, then say what the *application-level* symptom of this is — because that is what you will actually be handed as a bug report.

<details>
<summary>Answer</summary>

Both are correct because they are answers to different questions. `Verify return code` is the **client's** verdict on the **server's** certificate, which was fine. The client's own failure to present a certificate is a finding the *server* makes, and in TLS 1.3 the client has already completed its side of the handshake before the server acts on it.

So the client believes the handshake succeeded, because from its side it did.

The application symptom: **a connection that opens and then dies with no error.** Not a refused connection, not a TLS error, not a timeout at connect — a successful connect followed by an empty response or a reset, which reads to every logging layer above it as "the server closed the connection." Application logs will say the upstream is unhealthy. Nothing anywhere on the client side will say "certificate."

Clean it up and prove the working case:

```bash
echo | openssl s_client -connect localhost:4433 -CAfile root.crt \
  -cert client.crt -key client.key 2>/dev/null | grep 'Verify return'
grep 'depth=0' server.log
pkill -f 's_server -cert'
```

```
Verify return code: 0 (ok)
depth=0 CN=svc-a, O=readers
```

Identical client output — and the server now names who it is talking to. So the rule, which belongs alongside Act V's five questions: **when mTLS fails, read the other end's log.** The end that is failing is not the end that reports it.

</details>

---

## Drill 5 — a tag that verifies for the wrong reason

No files for this one. You are handed a service that AEAD-encrypts each user's session data and stores the result in a database row, keyed by user id. The code is correct: AES-GCM, a fresh random nonce per write, tags checked on read, keys from a KDF. No nonce is ever reused.

An attacker who is a legitimate user of the service, and who can update their own row, escalates to another user's session.

**Diagnose it.** Which of the four promises was kept, and what was assumed that was never true?

<details>
<summary>Answer</summary>

Every promise was kept. Confidentiality, integrity and authenticity are all intact — nothing was forged and no tag was broken. The attacker **copied their own valid ciphertext into another user's row**, or another user's into their own, depending on which direction gains them something.

What was assumed is that a valid tag means *this data belongs here.* It never did. An AEAD authenticates exactly the bytes you gave it, and the row id was not one of those bytes.

This is lesson 03's associated-data reveal, in the form it actually appears in production: not header tampering, but a legitimate, correctly-tagged, genuinely-authentic ciphertext **relocated** to a context it was never written for. The tag verifies because it is a real tag on real ciphertext.

The fix is to bind the context in as associated data — the user id, the row id, the column name, the tenant — so that the ciphertext is valid *only in the place it was created*:

```python
ct = aead.encrypt(nonce, plaintext, associated_data=f"session:{user_id}".encode())
```

Now moving the row makes decryption raise. And notice this is the same idea as TLS 1.3's `CertificateVerify` signing the transcript rather than the identity: **bind the proof to the context, or a valid thing can be replayed somewhere it does not belong.** Third appearance in this act, and the general rule is worth stating as a rule — *an authenticated value proves something about the bytes, and nothing about where you found them.*

</details>

---

## Drill 6 — the intermediate that tries to be a root

```bash
cd "${TMPDIR:-/tmp}/drills"
openssl genpkey -algorithm ED25519 -out sub.key
openssl req -new -key sub.key -out sub.csr -subj "/CN=Sub CA"
openssl x509 -req -in sub.csr -CA int.crt -CAkey int.key -out sub.crt \
  -days 365 -extfile int.ext

openssl genpkey -algorithm ED25519 -out evil.key
openssl req -new -key evil.key -out evil.csr -subj "/CN=bank.example.com"
printf 'subjectAltName=DNS:bank.example.com\n' > evil.ext
openssl x509 -req -in evil.csr -CA sub.crt -CAkey sub.key -out evil.crt \
  -days 365 -extfile evil.ext

openssl verify -CAfile root.crt -untrusted int.crt -untrusted sub.crt evil.crt
```

Every command succeeds. The last one produces a verdict.

**Predict the verdict before running it**, then explain which single field in which certificate decided it, and why that field has to be *checked by the verifier* rather than *enforced at signing time*.

<details>
<summary>Answer</summary>

```
CN=Drill Intermediate
error 25 at 2 depth lookup: path length constraint exceeded
error evil.crt: verification failed
```

Read the two halves of that verdict, because they are more informative than the code. The depth is **2** and the name is **`Drill Intermediate`** — not the leaf you passed in. A chain error is always reported against the certificate where the rule was broken, not the one you asked about, which is why "my certificate is invalid" is so often a statement about somebody else's certificate.

The deciding field is `pathlen:0` in `int.crt`'s basic constraints, which you set in the setup block without being told why. It means: *this CA may sign leaf certificates, and may not sign further CAs.* So `sub.crt` exists, is correctly signed, and is not permitted to be a CA under this root — and everything beneath it is rejected.

Why the verifier has to check it: **signing is arithmetic.** `openssl x509 -req` is a mathematical operation on bytes with a key, and there is no possible way to prevent the holder of `int.key` from performing it on any input at all. Every certificate in this drill was produced without error. Nothing at signing time can stop a CA from minting whatever it likes.

So the only place a constraint can live is in the *verification*, and the only thing that makes it stick is that the constraint itself is inside a signed document — `int.crt` says `pathlen:0` and `root.key` signed that statement, so the intermediate cannot remove it without invalidating itself.

That is the same structure as lesson 05's `CA:TRUE` (`error 79`), and the same structure as Act V's `allowedRoutes` and Act VII's `ownerReferences`: **the check is on a field in a document, and what makes the field trustworthy is who signed it.** It is worth recognising as a pattern, because it is the only way to constrain an actor you cannot supervise.

Real-world weight: this is how a company gets given a CA that can only issue for its own domain. `nameConstraints` does the same job for names rather than depth — and its history is instructive, because for years several major clients did not check it, which meant the constraint was in the document and enforced by nobody.

</details>

---

**Cleanup:**

```bash
pkill -f 's_server -cert' 2>/dev/null
cd "${TMPDIR:-/tmp}" && rm -rf drills
```

## What the six have in common

Five of them are the same finding in different clothes: **a cryptographic verdict tells you what the mechanism concluded, and almost nothing about why.** `error 20` covers two unrelated causes. `error 9` cannot tell a bad date from a bad clock. mTLS reports success on the failing side. A valid tag says nothing about location.

So the habit is not "read the error." It is: **decide which of the four promises was being made, then work out which side was in a position to notice.** In every drill above, the diagnosis came from asking who checked, not from the message.

---

↑ **[Act VIII overview](README.md)** · Prev: **[Test yourself](test-yourself.md)** · Next: **[In the wild](in-the-wild.md)** →
