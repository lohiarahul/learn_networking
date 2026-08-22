# The lock, opened

This lesson introduces no new mechanism.

That is not modesty, it is the point, and it is worth checking before you go on. Every mechanism TLS uses is now in your hands: a hash, a keyed hash, an AEAD, an ephemeral key agreement, a signature, and a certificate chained to an anchor you chose. There is no seventh thing. (One line of output near the end will name something you have not met, and it is there precisely because it is *not* a seventh thing — it is one of these five being replaced while you watch.)

So the only question left is the one Act III could not even pose: **in what order do they run?** And that turns out to be the hard part.

> **Predict first —** you want the whole conversation encrypted and authenticated. But to encrypt you need a shared key, and lesson 04's exchange requires each side to send a public value in the clear. To be sure you are exchanging with the *right* party you need their certificate, and that is several hundred bytes which also have to be sent — and which you would rather not send in the clear, because it names who is talking to whom to anyone watching the wire. **Write down the order those messages go in.** Then, for each one, write down what is protecting it when it arrives.

### Watch one happen

You do not need the internet for this, and it is better without. Rebuild last lesson's certificate authority — the same four commands, since you deleted it on the way out — so that you are the server, the client, *and* the trust anchor, and nothing in what follows is hidden behind somebody else's infrastructure.

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

Now start a TLS server. `openssl s_server` is the counterpart to the `s_client` you have used since Act III — a minimal TLS listener, where `-www` makes it answer an HTTP request so the connection completes rather than hanging. Start it in the background and connect to it:

```bash
openssl s_server -cert server.crt -key server.key -accept 4433 -www > s.log 2>&1 &
sleep 2
grep -q 'in use' s.log && echo 'PORT BUSY -- run: pkill -f s_server' && cat s.log
echo | openssl s_client -connect localhost:4433 -CAfile ca.crt 2>/dev/null \
  | grep -E '^ [0-9] s:|^   i:|Peer signature|Negotiated|Cipher is|Protocol|Verify return'
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
| `SHA384` | the hash — used for deriving keys, and for one more job you will meet below | lessons 01 and 02 |

And now the two things the string does **not** say, which are more informative than the four it does.

**It does not name a key exchange.** Lesson 04 explained why: TLS 1.3 deleted every non-ephemeral option, so there is nothing left to negotiate in the suite name. Forward secrecy stopped being a choice. What *did* get negotiated is on its own line — `Negotiated TLS1.3 group` — and on **OpenSSL 3.5 or newer** it will probably surprise you. (On 3.0 to 3.4 it says `X25519`, which is what lesson 04 would predict; if that is what you see, the section below is describing your near future rather than your present.)

**It does not name a signature algorithm.** That is on its own line too: `Peer signature type: ed25519`. Which is exactly right, because the signature is a property of the *certificate* the server happens to hold, and the certificate was issued long before this connection existed. The cipher suite describes the session; the signature describes the identity. Conflating those is why TLS 1.2's suite names were four times longer and much less useful.

### Every order is broken, so pick which way

Before looking at what TLS does, take the two orders you probably wrote down and find the flaw in each. There are only two sensible ones, because there are only two things that have to happen.

**Order A: authenticate first, then exchange keys.** It is the intuitive one — establish who you are talking to *before* agreeing a secret with them, which is exactly the lesson 04 → lesson 05 sequence this act just taught. And it means the certificate must be sent before any key exists to encrypt it with. So the certificate travels in the clear. Anyone watching the wire learns which site you are visiting and which client you are, and there is no way around it, because encryption is the thing that has not happened yet. Act III showed you this diagram — that is TLS 1.2, and it is why the certificate was visible in it.

**Order B: exchange keys first, then authenticate.** Now the certificate is encrypted, because there is a key by the time it is sent. But look at what you did the exchange with: an unauthenticated stranger. Lesson 04 spent a whole section on that exact situation and Mallory won it. The key you are encrypting the certificate with may be a key you share with the attacker.

So the honest statement is the one the prediction was pushing you towards: **there is no ordering in which the first message is protected, because the first message is what protection is built out of.** Something has to go first and be naked. The only design question available is *which*, and therefore what an eavesdropper gets for free.

TLS 1.3 chose B. Watch it happen — ask `s_client` to name each handshake message as it goes past:

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
>>> TLS 1.2, InnerContent [length 0001]
>>> TLS 1.3, Handshake [length 0034], Finished
>>> TLS 1.2, InnerContent [length 0001]
>>> TLS 1.2, InnerContent [length 0001]
```

(`<<<` is received, `>>>` is sent, and the lengths are your own connection's — they shift with the
key exchange in use. The last four lines are the client's half, wrapped the same way.)

Two of those names are new and both are doing the same job. `EncryptedExtensions` is where the server puts the negotiated details that TLS 1.2 had to send in the clear — it is named for the fact that it is encrypted, which tells you that being encrypted was the novelty. And `InnerContent` is `s_client` reporting that what it just decrypted had a *record type hidden inside the ciphertext*: from here on, even the question "what kind of message is this?" is not answerable from the wire.

So look at where `InnerContent` starts, because that is the whole answer. Everything from `EncryptedExtensions` onward is wrapped — **the certificate is sent encrypted.** So is the signature over it. So is the message that says the handshake is complete.

Which means the order is:

1. **`ClientHello`** — in the clear, and it already contains the client's ephemeral public value. Lesson 04's `A`, sent before anything else and before anyone has been authenticated.
2. **`ServerHello`** — in the clear, containing the server's ephemeral public value. `B`.
3. **At this instant both sides can compute the shared secret**, run it through lesson 04's HKDF to turn one group element into a set of flat, labelled, per-direction keys, and start encrypting. Two messages. Nobody has proved anything about who they are yet.
4. **Everything else happens inside that encryption** — the server's certificate, its signature, and the finish.

That is Order B, and the naked message is the key exchange rather than the certificate. Say what that costs and what it buys. **Authentication is moved inside the confidentiality, rather than confidentiality waiting on authentication.**

The cost is real: steps 1–2 are unauthenticated, so Mallory can interpose herself there exactly as she did in lesson 04, and nothing at that moment stops her. What makes it survivable is what comes next — the very first thing sent through the resulting channel is the server proving, with a signature checkable against your trust anchor, that it is the party you asked for. If Mallory is in the middle she cannot produce that signature, and the connection dies before a single byte of application data moves. **The unauthenticated exchange is not a hole because it is repaired retroactively, before the channel is used for anything.**

And Order B is cheaper as well as more private. One round trip; TLS 1.2 authenticated first and therefore needed two. That is a whole network round trip removed from the front of every HTTPS connection on Earth — the same latency Act II made you count in milliseconds — obtained by sending the messages in the less intuitive order.

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

Lesson 04 taught X25519 and you would expect to see it alone. What you actually got is X25519 **combined with ML-KEM-768**, and the shared secret is derived from both halves at once.

ML-KEM is a *key-encapsulation mechanism*, which reaches lesson 04's destination by a different route. Diffie–Hellman was symmetric: both sides sent a public value, both sides did the same operation, and the secret was something neither chose. A KEM is one-directional — one side publishes a public key, the other **generates a random secret, encapsulates it under that key, and sends the result**, and only the holder of the private key can open it. Same outcome, both ends holding the same bytes with nothing useful on the wire; different shape, and built on entirely different mathematics, which is the entire reason it is here. Its hardness assumption is not the discrete logarithm.

The reason it is a hybrid rather than a replacement is the act's own thesis applied honestly in both directions. ML-KEM is new, and new cryptography is where mistakes live; X25519 is old and well-attacked but its hardness assumption is exactly the one a quantum computer is expected to demolish. Combining them means an attacker has to break *both*.

This is the plainest possible illustration of the claim the act opened with. **Nothing here is impossible, everything is infeasible, and infeasible is a number** — and the number for the discrete logarithm is expected to change, in a foreseeable way, at some point nobody can date. The response is already shipping, by default, in the binary on your machine, in a connection you just made to yourself.

Note the driver, because lesson 04 asked you to keep the shape of the argument. There it was: *someone records your traffic and waits for your key.* Ephemeral exchange answered it — delete the key and the recording is worthless. Here it is the same attacker with the same recording, waiting for something else entirely: **not for your key, but for the mathematics.** Forward secrecy has nothing to say about that, because there is no key to have deleted. Which is why the key exchange had to be replaced *before* the machine that breaks it exists — anything recorded today is already committed.

### Both directions

One command changes the shape of the whole thing. Restart the server demanding a certificate *from the client*, and give the client the kind of identity lesson 05 ended on:

```bash
cd "${TMPDIR:-/tmp}/tls"
pkill -f 's_server -cert' ; sleep 1
openssl genpkey -algorithm ED25519 -out client.key
openssl req -new -key client.key -out client.csr -subj "/CN=rahul/O=kubeadm:cluster-admins"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -out client.crt -days 1

openssl s_server -cert server.crt -key server.key -CAfile ca.crt -Verify 1 \
  -accept 4433 -www > server.log 2>&1 &
sleep 2
echo | openssl s_client -connect localhost:4433 -CAfile ca.crt \
  -cert client.crt -key client.key 2>/dev/null | grep -E 'CA names|Verify return'
grep 'depth=' server.log
```

```
Certificate request self-signature ok
subject=CN=rahul, O=kubeadm:cluster-admins
Acceptable client certificate CA names
Verify return code: 0 (ok)
depth=1 CN=My Toy Root CA
depth=0 CN=rahul, O=kubeadm:cluster-admins
```

**The server walked a chain and learned a name** — and it is the name Act VI showed you in your own kubeconfig. `Acceptable client certificate CA names` is the server saying *prove yourself, and here is whose signature I will accept* — and the two `depth=` lines in the server's own log are it verifying the client exactly as the client verified it.

That is mTLS, it is symmetric, and it is the same five mechanisms twice. It is also, precisely, how every `kubectl` command you have run since Act V authenticated: the API server presents a certificate signed by the cluster CA, your kubeconfig presents one signed by the same CA, and the API server reads `CN` as your username and `O` as your groups out of `depth=0`.

Now cause the failure, because it is the single most confusing thing about mTLS in practice:

```bash
echo | openssl s_client -connect localhost:4433 -CAfile ca.crt 2>/dev/null \
  | grep 'Verify return'
tail -1 server.log
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

   NO ORDER IS SAFE -- YOU PICK WHAT LEAKS
     A  authenticate first, then exchange keys
        -> the CERTIFICATE goes in the clear. anyone
           watching learns who is talking to whom.
           that is TLS 1.2.
     B  exchange keys first, then authenticate
        -> the exchange is with an UNAUTHENTICATED
           stranger. lesson 04: Mallory wins that.
     the first message cannot be protected, because it
     is what protection is BUILT OUT OF.
     TLS 1.3 picks B, and repairs it retroactively.

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
     server log: depth=0 CN=rahul,
                 O=kubeadm:cluster-admins
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

> **You understand this when you can** walk both candidate orderings of a handshake and name what each one exposes, say why no ordering protects its own first message, and state which one TLS 1.3 chose and what that buys; read `TLS_AES_256_GCM_SHA384` field by field and name the lesson each field came from; say what the suite name deliberately omits and why each omission is an improvement; describe what is sent in the clear and what is not, and identify the exact moment encryption begins; explain why an unauthenticated key exchange is safe to perform first, and why relaying the real certificate does not help an attacker; say what `CertificateVerify` signs and why signing the transcript rather than the identity is the load-bearing choice; derive downgrade protection from that same signature; explain what a hybrid key-exchange group is for and why the threat it answers is not the one forward secrecy answers; describe mTLS as a symmetric application of the same mechanisms and connect it to how `kubectl` authenticates; explain why a failing client certificate shows up as success on the client and a failure on the server; and say where TLS stops, with two examples from earlier acts.

**Which raises:** the act is finished and the lock is open. Look at what you can now do, though, and notice how narrow it is. You can prove that a connection reaches the party named in a certificate, and you can read a name out of `depth=0` — `CN=rahul`, `O=kubeadm:cluster-admins`. **And then what?** A name is not a permission. Nothing in five lessons of cryptography has any opinion about what `rahul` may do, and that group string means anything at all only because something *outside* the certificate treats it as meaningful. Act VI has already shown you that a cluster does this in more than one way — one group is granted its power by a rule you can read and edit, and another is hardwired into the API server and consults no rule whatsoever. Cryptography cannot tell those two apart. It put a string in a field, correctly, and stopped.

Which is the handover. Cryptography answers *who is this*, exhaustively and beautifully, and the question it does not touch — **what may they do** — is a different subject with its own vocabulary, its own models, and its own catastrophic failure modes. That is **[Act IX](../act-9-identity/README.md)**, and it starts by making you prove that the distinction is real rather than taking it on trust. Carry one habit into it: every time you meet a rule granting a permission, ask this act's question in its new costume — *what is being proved here, and what is merely being assumed?*

---

↑ **[Act VIII overview](README.md)** · Prev: **[A claim someone else vouched for](05-certificates.md)** · Next: **[Test yourself](test-yourself.md)** →
