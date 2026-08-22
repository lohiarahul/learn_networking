# Test yourself — Act VIII

Twenty-three questions. The rule is the same as every other act: answer out loud or on paper *before* opening the answer, because recognising a correct answer is not the same as being able to produce one — and this act is the one where that gap is widest, since all the vocabulary is familiar from years of using it.

Questions 1–4 are lesson 01, 5–8 are lesson 02, 9–12 are lesson 03, 13–15 are lesson 04, 16–19 are lesson 05, 20–23 are lesson 06.

---

**1.** A hash's output is fixed-length whatever goes in. Give the argument, in one sentence and using numbers, for why that alone makes the function irreversible — without appealing to anything about how SHA-256 is built internally.

<details><summary>Answer</summary>

A 1 MB input has 2^8000000 possible values and there are only 2^256 possible outputs, so unimaginably many inputs share each output. The original cannot be recovered because it is not in there — the function discarded it. Irreversibility is a consequence of the *sizes*, not of clever design, which is why "we hash your passwords" is a claim about destruction rather than concealment.

</details>

**2.** You flip one bit of a hash's input and 124 of 256 output bits change. Why is *half* the right target? Explain what would be wrong with a hash where all 256 flipped, and what would be wrong with one where only a few did.

<details><summary>Answer</summary>

Half is what "no relationship" looks like. If each output bit is independently as likely to flip as not, then about 128 flip — so half is the signature of a function that has thrown away all structure.

A few flipping would be fatal: the output would be a *summary* that tracks the input, so you could work backwards along the correlation, and small input changes would produce nearby outputs.

All 256 flipping every time would be just as bad, because it is a *pattern*. If flipping one input bit always inverted the entire output, that is a deterministic relationship an attacker can exploit — knowing one hash would tell you another. Predictable is the problem, in either direction. Half means unpredictable.

</details>

**3.** Name the three resistance properties, say which attacker each one defends against, and say which is always the weakest and by how much.

<details><summary>Answer</summary>

- **Preimage**: given a hash, find any input producing it. Defends against an attacker holding your password database.
- **Second preimage**: given *this* file, find a different one with the same hash. Defends against an attacker substituting a download you published.
- **Collision**: find *any* two colliding inputs, with no constraint on what either one is. Defends against an attacker who gets to choose freely on both sides.

Collision resistance is always the weakest, at exactly **half the output bits**, because the attacker gets to choose both sides and the number of pairs grows as the square — so they need only the square root of the space. SHA-256's 256 bits give 128 bits of collision resistance. That is the birthday bound, and it is why MD5 (64) and SHA-1 (80) fell.

</details>

**4.** You have two files with the same MD5. Which of these are you now able to do, and which not? (a) forge a download of someone else's published file, (b) produce a document whose "signature" also validates a different document you wrote, (c) recover a password from its MD5.

<details><summary>Answer</summary>

Only **(b)**. A collision means you authored both, so you can present one for approval and substitute the other.

**(a)** needs a *second* preimage — someone else's file already exists and you must find a collision with that specific input. No practical second-preimage attack on MD5 is known.

**(c)** needs a preimage. Also not available — though for weak passwords, brute force does the job without any weakness in MD5 at all, which is a different problem.

So: still fine for detecting a corrupted download from a mirror you trust; useless anywhere the file's *author* is the adversary.

</details>

---

**5.** `signature = SHA256(secret + body)`. The attacker has one body and its signature, does not know the secret, and will never learn it. Describe what they can do and name the one piece of information about the secret they need.

<details><summary>Answer</summary>

They can append arbitrary bytes and produce a valid signature for the longer message. The digest is not a summary of the input — it is the internal state of a Merkle–Damgård computation that has already absorbed the secret, so it is a *resume point*. They restart the hash from that state and continue.

The one thing they need is the secret's **length**, to reconstruct the padding the server will compute. That is not a secret and cannot be made one: guessing costs one attempt, and looping 1 to 64 costs nothing.

Note what they do not need: no collision, no preimage, and no weakness in SHA-256. Length extension is the specified behaviour of a streaming hash.

</details>

**6.** Swapping to `SHA256(body + secret)` genuinely kills length extension. Why is it still the wrong answer?

<details><summary>Answer</summary>

Because it makes your authentication depend on **collision resistance** — the weakest property, at half the bits, and the one that always falls first.

With the secret last, any two bodies that collide reach an identical internal state at the point the secret begins, so appending the same secret to both gives the same digest. Capture a legitimate signature on `B1`, ship `B2` with it, and it verifies. With MD5 that is trivially exploitable today.

Neither ordering is safe *for the right reason*. What you want is a construction where the key is at neither end of the message.

</details>

**7.** Write out HMAC and say specifically what the outer hash accomplishes that the inner one cannot.

<details><summary>Answer</summary>

`HMAC(key, msg) = H( (key ^ opad) || H( (key ^ ipad) || msg ) )`

The outer hash makes the published digest **not a resume point for anything useful**. Its input is one block plus a 32-byte digest — a fixed length, already complete. An attacker holding the output can resume the outer computation, but there is nothing to extend that the verifier would ever read, because the verifier's own computation ends at the same place.

The inner hash cannot do that alone, because whatever it produces is the state of a computation that could always be continued.

</details>

**8.** You and a payment provider share an HMAC key. A correctly-signed instruction moves money out of your account and you deny sending it. What can the HMAC settle?

<details><summary>Answer</summary>

Nothing about *which* of you produced it. It proves the message came from someone holding the key, and two parties hold it.

Verification and creation are the same operation with the same key, so the provider can author an instruction, sign it validly, and present it as yours. No amount of hash strength changes this — the property is symmetric by construction.

The missing property is **non-repudiation**, and a shared secret cannot provide it. Any number of parties holding one key are, cryptographically, one indistinguishable party. This is not a reason to avoid HMAC: inside one system there is only one holder in any meaningful sense. Between mutually distrusting parties it is the whole question, and it needs a mechanism where verifying and signing use *different* keys.

</details>

---

**9.** The one-time pad is provably unbreakable. Give the reason it is nonetheless useless, in a form that explains why every other cipher exists.

<details><summary>Answer</summary>

The key is as long as the message. So if you have a secure channel capable of delivering the key, you had a secure channel capable of delivering the message — the cipher bought you a delay and nothing else.

Every other cipher is an attempt to get a *short* key to behave like a long one, and every interesting cipher failure is a consequence of that compromise.

</details>

**10.** Encrypting 48 identical bytes with AES-128-ECB produces three identical ciphertext blocks. Whose fault is that, and what class of real system does it break?

<details><summary>Answer</summary>

Not AES's. AES did exactly what it specifies: permute 16 bytes under a key, deterministically. The **mode** is at fault — ECB encrypts each block independently, so identical input blocks give identical output blocks and the ciphertext preserves every repetition in the plaintext.

It breaks anything with structure: an encrypted bitmap still shows its picture (the "ECB penguin"), and an encrypted database column keeps equal values visibly equal, which is enough to identify records without decrypting anything.

The general lesson: AES is a 16-byte permutation, not a way to encrypt a message. How you use it is a separate decision, and it is where the bugs live.

</details>

**11.** You hold an AES-CBC ciphertext and its IV, no key. You know the plaintext's *format* — a `role=` field at a known offset. What can you do, and what does that prove about the relationship between encryption and integrity?

<details><summary>Answer</summary>

You can flip any bits you choose in the first plaintext block, by XORing your desired change into the IV — turning `role=user` into `role=root` without touching a byte of ciphertext and without the key. CBC decryption computes `plaintext = AES_decrypt(ciphertext) XOR previous_block`, and for the first block the "previous block" is the IV, which travels in the clear precisely because it is not a secret. Later blocks work the same way using the preceding ciphertext block, at the cost of garbling that earlier block.

It proves that **encryption is not integrity**, and not as a slogan: a message an attacker cannot read is very often one they can *edit*, in a controlled way, with predictable results. Note what they needed — not the key and not the plaintext, just the format, which is documented.

</details>

**12.** `AESGCM.encrypt` on a 16-byte plaintext returns 32 bytes, and `openssl enc` refuses to do GCM at all. Connect those two facts.

<details><summary>Answer</summary>

The extra 16 bytes are the **authentication tag**. So AEAD output is not ciphertext — it is ciphertext plus a tag, and decryption has a third possible outcome besides "plaintext": it can *raise*, returning nothing at all.

`openssl enc` is a filter: bytes in, bytes out. It has somewhere to put plaintext and nowhere to put "this was tampered with," which is why it declines rather than fails. The refusal is the shape of the primitive showing through the tool's interface.

That third outcome is what makes the CBC attack impossible rather than merely detectable — a failed AEAD decryption yields no plaintext, not plaintext with a warning.

</details>

---

**13.** Derive why pre-shared keys could not scale, and give the number for 1000 parties. Where else in this act does the same expression appear, and doing the opposite damage?

<details><summary>Answer</summary>

Every *pair* needs its own key — if a third party shared it, they could listen. So `n(n-1)/2`: **499,500** keys for 1000 parties, each of which must be generated, delivered untampered, stored safely and destroyed on schedule.

The same expression is lesson 01's birthday bound. There, pairs growing as the square is what *halves* your security; here it is what makes distribution impossible. One expression, two disasters.

</details>

**14.** Alice and Bob exchange `g^a` and `g^b` in the clear and both end up with a secret the eavesdropper does not have, despite the eavesdropper holding every transmitted byte. Explain in one line of algebra, and name the value neither party knows.

<details><summary>Answer</summary>

Alice computes `B^a = (g^b)^a = g^(ba)`; Bob computes `A^b = (g^a)^b = g^(ab)`. Multiplication commutes, so both reach `g^(ab)` — by different routes, each requiring a private exponent the other never learned.

Neither party knows the other's exponent, and the secret is the product of both. The attacker would need to solve `A = g^a mod p` for `a` — the discrete logarithm — for which no fast method is known. Measured: microseconds forward at 255 bits, half a second backward at 20 bits.

</details>

**15.** Mallory replaces the public keys in transit. Describe exactly what she holds afterwards, why neither end detects it, and what this says about what Diffie–Hellman promises.

<details><summary>Answer</summary>

Two valid shared secrets — one with Alice, one with Bob. She decrypts everything from either side, reads it, re-encrypts under the other key, forwards it. Both ends have working AEAD, valid tags and no errors.

Neither detects it because **nothing was broken**. Diffie–Hellman did precisely what it promised: it gave each party a key shared with whoever is at the other end of the wire. It has no opinion whatsoever about who that is.

She also needed nothing clever — she ran the same four commands Alice and Bob ran. Being in the middle is not an attack posture; it is the job description of every router, proxy, access point and load balancer on the path.

</details>

---

**16.** Bob signs his own public key and sends both. Why does that achieve nothing, and what general statement about signatures does it establish?

<details><summary>Answer</summary>

The signature proves the message was made by the holder of the private half of *some* public key — and the public key in question is the one whose authenticity you were trying to establish. Mallory supplies her own key *and* a valid signature over it; everything verifies and nothing is established.

The general statement: **a signature can never introduce a stranger.** It can only move trust from a key you already had reason to trust to one you did not. It cannot produce the first one. So the chain must terminate outside the mathematics — which is what a trust anchor is, and why it is a social fact rather than a cryptographic one.

</details>

**17.** `openssl verify -CAfile ca.crt server.crt` says `OK`. `openssl verify server.crt` says `error 20`. Nothing about the file changed. What does that tell you about where verification lives?

<details><summary>Answer</summary>

Verification is **not a property of a certificate.** It is a relationship between a certificate and a list you chose. The only difference between those two commands is which list was consulted — a file you named, versus your system's default store of roughly 195 self-signed certificates you did not pick individually.

Every certificate error you have ever seen is one of those two commands, and the useful question is always which list was consulted and what is in it. Note the consequence: since any one of those anchors can issue a valid certificate for any name, the system's security is the *minimum* over a couple of hundred organisations rather than the maximum.

</details>

**18.** Distinguish `error 20`, `error 7`, `error 79`, `error 62` and `error 10`. For each, say what it tells you about the certificate.

<details><summary>Answer</summary>

- **20** — *unable to get local issuer certificate.* No path from this certificate to anything in the trust store. Says nothing bad about the certificate; says the verifier does not know the issuer.
- **7** — *certificate signature failure.* The signed bytes were altered. The certificate's *claims* may read perfectly — reading a field tells you what a certificate asserts, not what was vouched for.
- **79** — *invalid CA certificate.* Something in the chain signed a certificate without carrying `CA:TRUE`. Signing is arithmetic and cannot be prevented; what is checked is the field, which is why it must be checked by every verifier.
- **62** — *hostname mismatch.* The chain is trusted and the signature is good; the name does not match what you asked for. Trust and naming are independent checks, and a verifier stops at the first failure — so this code tells you the name check failed and says nothing at all about whether the trust check *would* have.
- **10** — *certificate has expired.* Note which side notices: the **verifier** checks the clock. The server serves an expired certificate happily forever, with no warning of any kind.

</details>

---

**19.** A certificate proves a server's hostname to a client. Explain how the *identical* mechanism, unchanged, becomes a client proving an identity to a server — and then say why that makes a control-plane `ca.key` a more dangerous file than a private key normally is.

<details><summary>Answer</summary>

Nothing in a certificate specifies a direction. It is a name, a public key, and a signature over both; the only question is who verifies it and what they do with the name afterwards. Reverse the roles and the client presents the certificate, the server verifies the chain against a CA *it* trusts, and then **reads the Subject to learn who it is talking to**. When both ends do it, that is mTLS.

Which means the Subject is not decoration — it is the identity. Kubernetes reads `CN` as the username and `O` as the groups, and there is no `User` object anywhere in the cluster, because the certificate *is* the record. There is nothing else to consult.

So `ca.key` is not "a private key for the cluster's certificates." It is **the power to mint any identity in the cluster, at will** — pick a `CN`, pick an `O`, sign it, and the API server believes you, because believing signatures from that key is precisely its job. Act VI showed two groups that matter: `kubeadm:cluster-admins`, which is granted power by a `ClusterRoleBinding` object, and `system:masters`, which is wired into the API server and skips the permission check entirely. Both are text fields in a Subject.

And by lesson 05's other finding, none of it can be revoked. A certificate you minted is good until `notAfter`, and the only true remedy is replacing the CA — which invalidates every other certificate in the cluster at the same time.

</details>

**20.** TLS 1.3 completes a key exchange and starts encrypting *before* either party has authenticated. Explain why that is safe, and name the specific message that makes it safe.

<details><summary>Answer</summary>

Because authentication is moved *inside* the confidentiality rather than confidentiality waiting on authentication — and the message that makes it work is **`CertificateVerify`**.

`CertificateVerify` is a signature over a hash of **the entire handshake transcript**, not over the identity. Mallory can relay the server's real certificate — it is public data — but the transcript she showed the client contains *her* ephemeral public value, while the transcript the real server signed contains the server's. Those hash differently, so the signature does not verify, and she cannot produce one that does without the server's private key.

Binding the proof of identity to *this specific connection* is the load-bearing choice. It is lesson 03's associated-data idea for the third time.

Free consequence: because the transcript includes `ClientHello`, which lists everything the client was willing to accept, an attacker stripping the strong options out to force a weak negotiation changes the transcript and breaks the signature. **Downgrade protection falls out of the same signature at no extra cost.**

</details>

**21.** Read `TLS_AES_256_GCM_SHA384` field by field. Then say what it does *not* name, and why each omission is an improvement.

<details><summary>Answer</summary>

`AES_256` the cipher and key size; `GCM` the AEAD mode giving encryption and a tag together; `SHA384` the hash used for key derivation and the handshake transcript.

**No key exchange is named**, because TLS 1.3 deleted every non-ephemeral option. Forward secrecy stopped being negotiable, so there is nothing to put in the string. (What *is* negotiated appears on its own line, and on a current OpenSSL is likely a post-quantum hybrid such as `X25519MLKEM768`.)

**No signature algorithm is named**, because the signature is a property of the certificate the server holds, which was issued long before this connection existed. The cipher suite describes the *session*; the certificate describes the *identity*. Conflating them is why TLS 1.2's suite names were four times longer and much less informative.

</details>

**22.** Your handshake reports `Negotiated TLS1.3 group: X25519MLKEM768` rather than the `X25519` lesson 04 would predict. Say what the second half is, why it is combined with the first rather than replacing it, and why lesson 04's forward secrecy is no help against the threat it addresses.

<details><summary>Answer</summary>

`MLKEM768` is a **key-encapsulation mechanism** — it reaches the same destination as Diffie–Hellman by a different route (one side publishes a public key, the other generates a secret, encapsulates it under that key and sends the result) and rests on entirely different mathematics. Specifically, not the discrete logarithm, which is the assumption a quantum computer is expected to demolish.

It is **hybrid rather than a replacement** because the shared secret is derived from both halves, so an attacker must break *both*. X25519 is old and heavily attacked but has the vulnerable assumption; ML-KEM has a safe assumption but is new, and new cryptography is where mistakes live. Combining them means neither weakness is load-bearing alone.

Forward secrecy does not help here, and seeing why is the point. Forward secrecy protects a recording against **a key stolen later** — delete the ephemeral key and there is nothing left to steal. This threat is the same attacker with the same recording waiting for **the mathematics** instead, and there is no key whose deletion helps. Which is why the exchange had to be replaced *before* the machine exists: anything recorded today is already committed.

That is the act's opening claim arriving on your own screen. Nothing is impossible, everything is infeasible, and **infeasible is a number that moves.**

</details>

**23.** A colleague says a service is "encrypted with TLS, so the traffic is safe." Give the question that actually resolves this, and two examples from earlier acts where the answer was uncomfortable.

<details><summary>Answer</summary>

The question is **"where does the TLS stop, and what is on the other side of that point?"** — because TLS protects bytes between two things that *terminate* it, which is not the same as between two applications.

Act V: you terminated TLS at an Ingress and the hop onward to the Pod was plain HTTP across the cluster network. Act VII: you read a Secret's plaintext straight out of a node's memory. Both times the padlock was green, and both times it was telling the truth about exactly what it covers — which was less than anyone assumed.

The general form is the act's organising question: **which of the four promises is this making, and which one is everybody assuming it makes?** "Encrypted in transit" is a claim about one leg of a path, and every mesh, sidecar and compliance checkbox is an answer to where that leg ends.

</details>

---

↑ **[Act VIII overview](README.md)** · Prev: **[The lock, opened](06-tls-opened.md)** · Next: **[Diagnose it](diagnose.md)** →
