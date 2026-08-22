# The lock, opened

This lesson introduces nothing.

That is not modesty, it is the point, and it is worth checking before you go on. Every mechanism TLS uses is now in your hands: a hash, a keyed hash, an AEAD, an ephemeral key agreement, a signature, and a certificate chained to an anchor you chose. There is no seventh thing.

So the only question left is the one Act III could not even pose: **in what order do they run?** And that turns out to be the hard part, for a reason worth feeling before you see the answer.

> **Predict first —** you want the whole conversation encrypted and authenticated. But to encrypt you need a shared key, and lesson 04's exchange requires each side to send a public value. To be sure you are exchanging with the right party you need their certificate, and a certificate is several hundred bytes that also have to be sent. And you would rather not send a certificate in the clear, because it names who is talking to whom. **Write down the order.** Every ordering you try will have something arriving before the thing that protects it, and finding which compromise is the least bad is the actual design problem TLS 1.3 solves.

### Watch one happen

You do not need the internet for this, and it is better without: use the certificate authority you built last lesson, so that you are the server, the client, and the trust anchor, and nothing is hidden behind somebody else's infrastructure.

```bash
mkdir -p "${TMPDIR:-/tmp}/tls" && cd "${TMPDIR:-/tmp}/tls"
openssl genpkey -algorithm ED25519 -out ca.key
openssl req -new -x509 -key ca.key -out ca.crt -days 3650 -subj "/CN=My Toy Root CA"
openssl genpkey -algorithm ED25519 -out server.key
openssl req -new -key server.key -out server.csr -subj "/CN=localhost"
printf 'subjectAltName=DNS:localhost\n' > san.ext
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -out server.crt \
  -days 365 -extfile san.ext
```

Start a TLS server in the background, then connect to it:

```bash
openssl s_server -cert server.crt -key server.key -accept 4433 -www >/dev/null 2>&1 &
sleep 2
echo | openssl s_client -connect localhost:4433 -CAfile ca.crt 2>/dev/null \
  | grep -E 'depth=|^ [0-9] s:|^   i:|Peer signature|Negotiated|Cipher is|Protocol|Verify return'
```

```
 0 s:CN=localhost
   i:CN=My Toy Root CA
Peer signature type: ed25519
Negotiated TLS1.3 group: X25519MLKEM768
New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384
Protocol: TLSv1.3
Verify return code: 0 (ok)
```

**There is the string.** `TLS_AES_256_GCM_SHA384` — the one Act III printed and told you not to look inside, five acts ago — negotiated against a certificate authority you created yourself twenty minutes ago, with `Verify return code: 0` because your machine was told which list to consult.

Read it as a sentence, because that is what it is:

| Field | What it names | Where you built it |
|---|---|---|
| `TLS` | the protocol | this lesson |
| `AES_256` | the cipher, 256-bit key | lesson 03 |
| `GCM` | the AEAD mode — encryption *and* a tag | lesson 03 |
| `SHA384` | the hash used for key derivation and the transcript | lessons 01 and 02 |

And now the two things the string does **not** say, which are more informative than the four it does.

**It does not name a key exchange.** Lesson 04 explained why: TLS 1.3 deleted every non-ephemeral option, so there is nothing left to negotiate in the suite name. Forward secrecy stopped being a choice. What *did* get negotiated is on its own line — `Negotiated TLS1.3 group` — and on a current OpenSSL it will probably surprise you.

**It does not name a signature algorithm.** That is on its own line too: `Peer signature type: ed25519`. Which is exactly right, because the signature is a property of the *certificate* the server happens to hold, and the certificate was issued long before this connection existed. The cipher suite describes the session; the signature describes the identity. Conflating those is why TLS 1.2's suite names were four times longer and much less useful.

### The order, and why it is the only one that works

Now answer the prediction. Ask `s_client` to name each handshake message as it goes past:

```bash
echo | openssl s_client -connect localhost:4433 -CAfile ca.crt -msg 2>&1 \
  | grep -E '^(<<<|>>>).*(Hello|Certificate|Finished|Extensions|InnerContent)'
```

```
>>> TLS 1.3, Handshake [length 05ed], ClientHello
<<< TLS 1.3, Handshake [length 04ba], ServerHello
<<< TLS 1.3, InnerContent [length 0001]
<<< TLS 1.3, Handshake [length 0006], EncryptedExtensions
<<< TLS 1.3, InnerContent [length 0001]
<<< TLS 1.3, Handshake [length 0157], Certificate
<<< TLS 1.3, InnerContent [length 0001]
<<< TLS 1.3, Handshake [length 0048], CertificateVerify
<<< TLS 1.3, InnerContent [length 0001]
<<< TLS 1.3, Handshake [length 0034], Finished
```

Look at where `InnerContent` starts, because that word is the whole answer. Everything from `EncryptedExtensions` onward is wrapped — **the certificate is sent encrypted.** So is the signature over it. So is the message that says the handshake is complete.

Which means the order is:

1. **`ClientHello`** — in the clear, and it already contains the client's ephemeral public value. Lesson 04's `A`, sent before anything else and before anyone has been authenticated.
2. **`ServerHello`** — in the clear, containing the server's ephemeral public value. `B`.
3. **At this instant both sides can compute the shared secret**, run it through HKDF, and start encrypting. Two messages. Nobody has proved anything about who they are yet.
4. **Everything else happens inside that encryption** — the server's certificate, its signature, and the finish.

That is the compromise, and now the reason it is the right one is visible. **Authentication is moved inside the confidentiality, rather than confidentiality waiting on authentication.** The exchange in steps 1–2 is unauthenticated, so Mallory can absolutely interpose herself there exactly as she did in lesson 04 — and it does not help her, because the very first thing sent through the resulting channel is the server proving, with a signature checkable against your trust anchor, that it is the party you asked for. If Mallory is in the middle she cannot produce that signature, and the connection dies before a single byte of application data moves.

One round trip. Compare TLS 1.2, which authenticated first and therefore needed two, and note what that bought at scale: a whole network round trip removed from the front of every HTTPS connection on Earth.

> **Check yourself —** step 3 looks like a hole. Both sides derive keys from an exchange in which neither has authenticated the other, and only *then* does the server prove who it is. So what exactly stops Mallory from sitting in the middle, completing the exchange with each side, and then — since she is now decrypting and re-encrypting everything — simply forwarding the server's real certificate on to the client?

<details>
<summary>Answer</summary>

She can forward it. The certificate is public data; there is nothing secret in it and nothing stopping her relaying it byte for byte. The client will verify the chain against its trust anchor and it will verify perfectly, because it is a real certificate.

What she cannot forward is `CertificateVerify`, and that message is the entire defence.

`CertificateVerify` is a **signature, made with the server's private key, over a hash of the whole handshake so far.** Not over a constant, not over the certificate — over the *transcript*: both hellos, both ephemeral public values, everything either side has said. Lesson 05 gave you the mechanism and lesson 01 gave you why a hash can stand in for the whole conversation.

So the transcript Mallory presented to the client contains *her* ephemeral value, not the server's, because she substituted it. The transcript the real server signed contains the server's. Those hash differently, so the signature the server produced does not verify against the transcript the client computed — and the client has no way to make it fit, and Mallory has no way to sign the version that would, because signing needs the private key she does not have.

That single design decision is what makes an unauthenticated key exchange safe to do first. **The signature is not over the identity; it is over the identity *plus everything that has happened*, which binds the proof of who you are to this specific connection.** It is the same idea as lesson 03's associated data — bind the context in, or a valid thing can be replayed somewhere it does not belong — arriving for the third time in this act.

It also kills a whole family of attacks for free. Because the transcript includes `ClientHello`, and `ClientHello` lists every version and cipher suite the client was willing to accept, an attacker who strips the strong options out of it to force a weak negotiation changes the transcript, and the signature stops verifying. **Downgrade protection falls out of the same signature**, at no extra cost, which is why TLS 1.3 does not need the bolted-on downgrade countermeasures its predecessors accumulated.

</details>

### The number is already moving

Go back to that one line and read it properly:

```
Negotiated TLS1.3 group: X25519MLKEM768
```

Lesson 04 taught X25519 and you would expect to see it alone. What you actually got is X25519 **combined with ML-KEM-768** — a key-encapsulation mechanism designed to resist an attacker with a quantum computer — and the shared secret is derived from both halves at once, so it is no weaker than X25519 was and no weaker than ML-KEM is.

The reason it is a hybrid rather than a replacement is the act's own thesis applied honestly in both directions. ML-KEM is new, and new cryptography is where mistakes live; X25519 is old and well-attacked but its hardness assumption is exactly the one a quantum computer is expected to demolish. Combining them means an attacker has to break *both*.

This is the plainest possible illustration of the claim the act opened with. **Nothing here is impossible, everything is infeasible, and infeasible is a number** — and the number for the discrete logarithm is expected to change, in a foreseeable way, at some point nobody can date. The response is already shipping, by default, in the binary on your machine, in a connection you just made to yourself. Note the driver, too: an attacker recording ciphertext *today* can decrypt it whenever the capability arrives, so key exchange had to be fixed before the machine exists. Lesson 04's forward secrecy protects against a key stolen later; it does not protect against the *mathematics* being broken later. Different threat, same recording.

### Both directions

One command changes the shape of the whole thing. Restart the server demanding a certificate *from the client*, and give the client the kind of identity lesson 05 ended on:

```bash
cd "${TMPDIR:-/tmp}/tls"
pkill -f 's_server -cert' ; sleep 1
openssl genpkey -algorithm ED25519 -out client.key
openssl req -new -key client.key -out client.csr -subj "/CN=rahul/O=system:masters"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -out client.crt -days 1

openssl s_server -cert server.crt -key server.key -CAfile ca.crt -Verify 1 \
  -accept 4433 -www > server.log 2>&1 &
sleep 2
echo | openssl s_client -connect localhost:4433 -CAfile ca.crt \
  -cert client.crt -key client.key 2>/dev/null | grep -E 'CA names|Verify return'
grep 'depth=' server.log
```

```
Acceptable client certificate CA names
Verify return code: 0 (ok)
depth=1 CN=My Toy Root CA
depth=0 CN=rahul, O=system:masters
```

**The server walked a chain and learned a name.** `Acceptable client certificate CA names` is the server saying *prove yourself, and here is whose signature I will accept* — and the two `depth=` lines in the server's own log are it verifying the client exactly as the client verified it.

That is mTLS, it is symmetric, and it is the same five mechanisms twice. It is also, precisely, how every `kubectl` command you have run since Act V authenticated: the API server presents a certificate signed by the cluster CA, your kubeconfig presents one signed by the same CA, and the API server reads `CN` as your username and `O` as your groups out of `depth=0`.

Now cause the failure, because it is the single most confusing thing about mTLS in practice:

```bash
echo | openssl s_client -connect localhost:4433 -CAfile ca.crt 2>/dev/null \
  | grep 'Verify return'
tail -2 server.log
```

```
Verify return code: 0 (ok)
...error:0A0000C7:SSL routines:tls_process_client_certificate:peer did not
return a certificate:ssl/statem/statem_srvr.c:3916:
```

**The client reports success and the server reports failure, about the same connection.** Not a bug: `Verify return code` is the client's verdict on the *server's* certificate, which was fine. The client's own failure to authenticate is the server's finding, and in TLS 1.3 the client has already finished its side of the handshake by the time the server acts on it. So the symptom of a broken client certificate is almost never an error where you are looking — it is a connection that opens and then dies, and the only honest account of why is in the server's log. Add that to Act V's five-question method: **when mTLS fails, read the other end's log.**

### What none of this covers

Five mechanisms, four promises, and one honest boundary — which Act V made you build without naming it.

TLS protects bytes **between two endpoints that terminate it**. Not between two applications. In Act V you terminated TLS at an Ingress and the hop onward to the Pod was plain HTTP over the cluster network; in Act VII you read a Secret's plaintext off a node's tmpfs. Both times the padlock was green, and both times it was telling the truth about exactly what it covers.

So the useful question about any encrypted system is never "is it TLS?" but **where does the TLS stop, and what is on the other side of that point?** Every mesh, every sidecar, every "encryption in transit" checkbox is an answer to that question, and most incidents are a case of somebody assuming the terminator was further along than it was.

<!-- figure -->
```
   TLS_AES_256_GCM_SHA384 -- READ AS A SENTENCE
     AES_256   the cipher, 256-bit key      lesson 03
     GCM       AEAD: encryption + a TAG     lesson 03
     SHA384    key derivation + transcript  lessons 01,02
   AND THE TWO IT DOES NOT NAME, WHICH SAY MORE
     no key exchange -- TLS 1.3 DELETED every
       non-ephemeral option. forward secrecy stopped
       being a choice.            -> its own line
     no signature alg -- that belongs to the CERT,
       issued long before this connection existed
                                  -> its own line

   THE ORDER, WHICH IS THE WHOLE DESIGN
     1  ClientHello  CLEAR  + client's ephemeral value
     2  ServerHello  CLEAR  + server's ephemeral value
     3  both derive the secret. HKDF. START ENCRYPTING.
        nobody has authenticated ANYTHING yet.
     4  everything after is InnerContent = ENCRYPTED:
        Certificate, CertificateVerify, Finished
     => AUTHENTICATION MOVED INSIDE CONFIDENTIALITY,
        not confidentiality waiting on authentication.
     ONE round trip. TLS 1.2 needed two.

   WHY STEP 3 IS NOT A HOLE
     Mallory CAN relay the real certificate -- it is
     public data. she cannot relay CertificateVerify:
     a signature over a HASH OF THE WHOLE TRANSCRIPT,
     which contains HER ephemeral value, not the
     server's. hashes differ -> signature fails.
     binds WHO YOU ARE to THIS connection.
     (associated data, third appearance this act)
     FREE CONSEQUENCE: the transcript includes
     ClientHello, so stripping strong ciphers out of
     it breaks the signature. DOWNGRADE PROTECTION
     falls out at no cost.

   THE NUMBER IS ALREADY MOVING
     Negotiated group: X25519MLKEM768
     not X25519 alone -- HYBRID with a post-quantum
     KEM. both halves feed the secret, so an attacker
     must break BOTH. old-and-attacked + new-and-
     quantum-resistant, because new crypto is where
     mistakes live.
     driver: ciphertext recorded TODAY is decryptable
     whenever the capability arrives. forward secrecy
     does not help -- that protects a stolen KEY, not
     broken MATHEMATICS.

   mTLS -- the same five mechanisms, twice
     server log: depth=0 CN=rahul, O=system:masters
     that IS kubectl. CN=username, O=groups.
     THE CONFUSING PART: client prints
       "Verify return code: 0 (ok)"
     while the server prints
       "peer did not return a certificate"
     ...about the SAME connection. `Verify return
     code` is the CLIENT's verdict on the SERVER.
     WHEN mTLS FAILS, READ THE OTHER END'S LOG.

   THE BOUNDARY
     TLS protects bytes between two things that
     TERMINATE it -- not between two applications.
     Act V: terminated at the Ingress, plain HTTP
       onward to the Pod.
     Act VII: Secret in plaintext on node tmpfs.
     padlock green both times, and honest both times.
     never ask "is it TLS?". ask WHERE DOES IT STOP.
```

**Cleanup:**

```bash
cd "${TMPDIR:-/tmp}" && pkill -f 's_server -cert' ; rm -rf tls
```

> **You understand this when you can** explain why every ordering of a handshake has something arriving before the thing that protects it, and state TLS 1.3's compromise in one sentence; read `TLS_AES_256_GCM_SHA384` field by field and name the lesson each field came from; say what the suite name deliberately omits and why each omission is an improvement; describe what is sent in the clear and what is not, and identify the exact moment encryption begins; explain why an unauthenticated key exchange is safe to perform first, and why relaying the real certificate does not help an attacker; say what `CertificateVerify` signs and why signing the transcript rather than the identity is the load-bearing choice; derive downgrade protection from that same signature; explain what a hybrid key-exchange group is for and why the threat it answers is not the one forward secrecy answers; describe mTLS as a symmetric application of the same mechanisms and connect it to how `kubectl` authenticates; explain why a failing client certificate shows up as success on the client and a failure on the server; and say where TLS stops, with two examples from earlier acts.

**Which raises:** the act is finished and the lock is open. Look at what you can now do, though, and notice how narrow it is. You can prove that a connection reaches the party named in a certificate, and you can read a name out of `depth=0` — `CN=rahul`, `O=system:masters`. **And then what?** A name is not a permission. Nothing in five lessons of cryptography has any opinion about what `rahul` is allowed to do, and `O=system:masters` was a superuser only because somebody, somewhere, wrote a rule saying that string means unlimited power. Cryptography answers *who is this*, exhaustively and beautifully, and then stops — and the question it hands over, **what may they do**, is a different subject with its own vocabulary, its own models, and its own catastrophic failure modes. That is the next act.

---

↑ **[Act VIII overview](README.md)** · Prev: **[A claim someone else vouched for](05-certificates.md)** · Next: **[Test yourself](test-yourself.md)** →
