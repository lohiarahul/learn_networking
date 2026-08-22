# Agreeing on a secret in public

Three mechanisms, three promises kept, and every experiment so far has cheated in the same place. Go back and look at any of them: the key was a variable in a script that played both parties. `SECRET = b'correct-horse'`. `key = os.urandom(16)`. Both ends of the conversation were the same process, so the key never had to go anywhere.

On a real network it does. Act III showed you exactly how many strangers' machines a packet crosses, and every one of them can read every byte. So:

**Two parties who have never met, with no shared secret, must end up holding the same key — while an eavesdropper records everything they send.**

Take a moment on why that sounds impossible rather than merely hard. Everything the two of them exchange, the attacker also has. Anything Alice can compute from what Bob sent, the attacker can compute too, because the attacker has the same message. There is no step where Alice receives something the attacker does not receive. The information available to her looks, on the face of it, identical to the information available to him.

Before that, though, note how badly you need this even *without* an eavesdropper.

> **Predict first —** suppose you give up and decide to distribute keys out of band: couriers, sealed envelopes, a USB stick handed over in person. It works for two people. Work out how many keys a network of *n* parties needs, so that every pair can talk without any third party being able to listen. Then put `n = 1000` in and look at the number. You have seen this exact expression before in this act, in a completely different context.

### Why out-of-band does not scale

Every pair needs its own key — if Alice and Bob shared a key with Carol too, Carol could read their traffic. So the count is every pair: `n(n-1)/2`.

```bash
python3 -c "
for n in (2, 10, 100, 1000):
    print(f'{n:>5} parties -> {n*(n-1)//2:>7} keys')"
```

```
    2 parties ->       1 keys
   10 parties ->      45 keys
  100 parties ->    4950 keys
 1000 parties ->  499500 keys
```

**Half a million secrets, each of which must be generated, delivered untampered, stored safely, and destroyed on schedule** — for a network smaller than one office. And it is the same `n(n-1)/2` from lesson 01: there, pairs growing as the square was what *halved* your security through the birthday bound; here it is what makes key distribution impossible. One expression, two disasters.

This was not a theoretical concern. It was the actual, practical, budget-consuming problem of twentieth-century secure communication — embassies with diplomatic bags of key material, banks couriering tapes — and it was thought to be irreducible. There is no mathematics here yet. The reason the problem looked permanent is that "you must already share a secret to establish a secret" reads like a tautology.

### It is not a tautology

Do it with numbers small enough to check by hand. Two public constants that nobody has to keep secret — a prime `p = 23` and a base `g = 5` — and one private number each, never transmitted:

```bash
python3 - <<'PY'
p, g = 23, 5                              # PUBLIC. printed in the RFC.
a, b = 6, 15                              # PRIVATE. never sent.

A = pow(g, a, p)                          # Alice -> Bob, in the clear
B = pow(g, b, p)                          # Bob -> Alice, in the clear
print(f"Alice sends A = {g}^{a} mod {p} = {A}")
print(f"Bob   sends B = {g}^{b} mod {p} = {B}")

print("Alice computes B^a mod p =", pow(B, a, p))
print("Bob   computes A^b mod p =", pow(A, b, p))
PY
```

```
Alice sends A = 5^6 mod 23 = 8
Bob   sends B = 5^15 mod 23 = 19
Alice computes B^a mod p = 2
Bob   computes A^b mod p = 2
```

**They both have 2, and 2 was never sent.** The eavesdropper has `p=23`, `g=5`, `A=8` and `B=19`, which is everything that crossed the wire, and none of it is 2.

The trick is one line of school algebra. Alice computes `B^a = (g^b)^a = g^(ba)`. Bob computes `A^b = (g^a)^b = g^(ab)`. Multiplication commutes, so they are the same number — each of them reached `g^(ab)` by a different route, and each route required a private number the other one never learned. **Neither party knows both exponents, and the secret is the product of both.**

That is Diffie–Hellman, and the reason it is one of the genuinely astonishing results in the subject is that it dissolves the tautology. You do not need a prior secret. You need an operation that is cheap forwards and expensive backwards.

### The expensive direction, measured

Everything above is public. So why can the attacker not just work out `a` from `A = g^a mod p` and finish the calculation exactly as Alice did?

Because they would have to solve for an exponent inside a modulus, which is the **discrete logarithm problem** — and, unlike ordinary logarithms, nobody knows a fast way to do it. That is the entire security of the thing. It is worth making the asymmetry a number rather than a word:

```bash
python3 - <<'PY'
import time, secrets
p, g = (1 << 255) - 19, 2
a = secrets.randbits(255)
t = time.perf_counter(); A = pow(g, a, p); fwd = time.perf_counter() - t
print(f"forward, 255-bit exponent      : {fwd*1e6:.0f} microseconds")

sp, sg, sa = 1000003, 5, 987654           # a deliberately TINY problem: ~20 bits
sA = pow(sg, sa, sp)
t = time.perf_counter()
for i in range(1, sp):
    if pow(sg, i, sp) == sA: break
print(f"backward, 20-bit problem       : {time.perf_counter()-t:.2f} seconds (a={i})")
PY
```

```
forward, 255-bit exponent      : 72 microseconds
backward, 20-bit problem       : 0.45 seconds (a=987654)
```

**Microseconds forward on the real thing; half a second backward on a problem trillions of times smaller.** Take the comparison seriously, because it is the act's central claim made concrete: the backward problem there is roughly 2²⁰, and a real one is 2²⁵⁵. Nothing is impossible; the gap is a number, the number is large, and that gap is the only thing standing between the attacker and your key.

(Better attacks than brute force exist for both discrete logs and factoring, which is why key sizes are what they are — 2048 bits for classical Diffie–Hellman, but only 256 for the elliptic-curve version, where the best known attacks are much worse. Same idea, different arithmetic underneath, and the reason `X25519` appears where you might expect a huge number.)

### The real thing

You will never write modular exponentiation. What you will do is exactly this, and note that it is four commands and two of the files are meant to be published:

```bash
cd "${TMPDIR:-/tmp}"
openssl genpkey -algorithm X25519 -out alice.pem
openssl genpkey -algorithm X25519 -out bob.pem
openssl pkey -in alice.pem -pubout -out alice.pub
openssl pkey -in bob.pem   -pubout -out bob.pub
cat alice.pub
```

```
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VuAyEAH7GNzIM/vEg7wJ9Ur+VguJdui/j2PAGz0OX9Gc4IdUw=
-----END PUBLIC KEY-----
```

That is `A` — the value `g^a`, wrapped in a container that says which curve it belongs to. `alice.pem` holds `a`, and never moves. So the vocabulary lands where it should: a **key pair** is a private number and the public value derived from it, and "public key" means *publishable*, not merely "the other one."

Now derive, in both directions:

```bash
cd "${TMPDIR:-/tmp}"
openssl pkeyutl -derive -inkey alice.pem -peerkey bob.pub  | xxd -p -c 32
openssl pkeyutl -derive -inkey bob.pem   -peerkey alice.pub | xxd -p -c 32
```

```
463285e5e337ec7e05bfa15559cd288a37644bae57af40fec30ef00343ac7330
463285e5e337ec7e05bfa15559cd288a37644bae57af40fec30ef00343ac7330
```

**Thirty-two identical bytes, computed independently from opposite sides, and only the two `.pub` files ever needed to travel.** Your own values will differ; the two lines must match.

And that is the end of lesson 03's problem. You now have an AES key — one both ends possess, that never crossed the wire, that could have been agreed over a channel every router was recording. Combine it with lesson 03 and the pair is a working secure channel.

> **Check yourself —** in practice nobody feeds those 32 bytes straight into AES-GCM as a key. They are run through a *key derivation function* first — HKDF, which is built out of lesson 02's HMAC. Two reasons, and one of them is not "extra security by hashing things." What are they?

<details>
<summary>Answer</summary>

**One: the raw output is not uniformly random, and a key must be.** A Diffie–Hellman result is an element of a mathematical group, not 32 fair coin flips. In the classical version this is glaring — the shared secret is a number less than `p`, so if `p` is 2048 bits then the top bits are skewed and some values cannot occur at all. AES expects a uniformly random bit string; handing it a structured one is out of specification, and out-of-specification is where guarantees stop applying. A KDF's first job is *extraction*: turning a value with concentrated-but-unevenly-spread unpredictability into bits that are flat.

**Two: you almost always need more than one key, and they must be independent.** Lesson 03 already showed this: encrypt-then-MAC needed a cipher key and a MAC key and they had to be different. A real session needs more — separate keys per direction, so that a message the client sent cannot be replayed back at it as though the server had sent it. One exchange produces one secret, and a KDF *expands* it into as many independent keys as the protocol needs, each labelled with what it is for.

That labelling is the third reason, and it is the one people miss. HKDF takes an `info` string, so the same shared secret with `info="client to server"` and `info="server to client"` yields two unrelated keys. Binding a key to its purpose in the derivation is what stops a value that is legitimate in one context from being valid in another — which is the same idea as lesson 03's associated data, one layer down.

</details>

### What you have not got

Look again at the four commands that made this work, and ask the question the whole act is organised around: **which promise is this keeping, and which one is everybody assuming it makes?**

Alice derived a shared secret with the holder of `bob.pub`. Test what that sentence actually guarantees. Introduce a third party who sits on the wire and, rather than merely listening, *replaces* the public keys in transit:

```bash
cd "${TMPDIR:-/tmp}"
openssl genpkey -algorithm X25519 -out mallory.pem
openssl pkey -in mallory.pem -pubout -out mallory.pub
d() { openssl pkeyutl -derive -inkey $1.pem -peerkey $2.pub | xxd -p | tr -d '\n'; }

echo "Alice, who believes she is talking to Bob : $(d alice mallory)"
echo "Mallory's Alice-side secret               : $(d mallory alice)"
echo "Bob, who believes he is talking to Alice  : $(d bob mallory)"
echo "Mallory's Bob-side secret                 : $(d mallory bob)"
```

```
Alice, who believes she is talking to Bob : d11f42f7b13469192edc2f4d2a1422b9c9c838f2e2a9d448b94a9669e199dc51
Mallory's Alice-side secret               : d11f42f7b13469192edc2f4d2a1422b9c9c838f2e2a9d448b94a9669e199dc51
Bob, who believes he is talking to Alice  : d7d49a0f5cfac6c967c43197b603ff7876812340446e4c2f5f0e080acc46a411
Mallory's Bob-side secret                 : d7d49a0f5cfac6c967c43197b603ff7876812340446e4c2f5f0e080acc46a411

```

**Two perfectly good key exchanges, and Alice's secret is not Bob's.** Mallory holds both. She decrypts everything Alice sends, reads it, re-encrypts it under the other key, and forwards it. Both ends have working AEAD, valid tags, no errors, and no possible way to notice — because nothing was broken. Diffie–Hellman did precisely what it promised.

Which reveals what it promised, stated exactly:

**Diffie–Hellman gives you a key shared with whoever is at the other end of the wire. It has no opinion whatsoever about who that is.**

Everything in the last four lessons has this shape. A hash detects change but not a changer. An HMAC identifies a key holder but cannot say which one. A cipher hides content but not from an editor. And now: an exchange agrees a secret without establishing a party. Four mechanisms, four promises, and *none of them is identity*.

Notice also that the attack needed nothing clever. Mallory ran the same four `openssl` commands Alice and Bob ran. The entire attack is *being in the middle* — which, for anyone operating a router, a proxy, a Wi-Fi access point or a load balancer, is not an attack position but a job description.

### A different attacker, and a property you already have

Identity is the next lesson's problem. Before leaving this one, there is a second attacker worth taking seriously, and the reason to take it seriously is that it does not require being in the middle of anything.

**Suppose someone simply records your traffic and waits.** They cannot read it today. But encrypted bytes keep perfectly, and one day they get your private key — a stolen backup, a subpoena, a decommissioned server sold with its disk in it, an employee leaving. What happens to the year of recordings?

Answer it for the exchange you just ran, and notice that it depends entirely on a choice nobody made explicitly: **how long did `alice.pem` live?**

If Alice uses one long-term key pair for every conversation, that year of traffic decrypts the moment the key leaks — every session, retroactively, in one event. But look at what those key pairs cost. Generating one took microseconds. So there is nothing stopping Alice making a **fresh pair for every conversation and deleting it afterwards** — which is called an *ephemeral* exchange, the `E` in cipher suite names like `ECDHE`.

Now the recording is worthless forever. The keys that encrypted it were derived from private values that existed for one connection and were never written anywhere, so there is no key left to steal. **Compromising the key you have does not retroactively decrypt sessions that used keys you no longer have.** That property is called *forward secrecy*, and it is the reason TLS 1.3 removed every key-exchange method that lacked it. Act III's `TLS_AES_256_GCM_SHA384` does not name the exchange at all — because in TLS 1.3 there is nothing left to choose. It is always ephemeral.

Keep the shape of that argument, because a later lesson runs it again against a threat forward secrecy *cannot* answer: the attacker who records today and waits, not for your key, but for the mathematics.

<!-- figure -->
```
   THE PROBLEM
     n parties, every pair needing its own key
       -> n(n-1)/2 keys.  1000 parties = 499,500
     the SAME n(n-1)/2 as lesson 01's birthday bound.
     there it halved your security; here it makes
     distribution impossible.

   THE RESOLUTION -- and it is school algebra
     public:  p, g          private:  a          b
     wire:    A = g^a       and       B = g^b
     Alice:   B^a = (g^b)^a = g^(ba)
     Bob:     A^b = (g^a)^b = g^(ab)
     SAME NUMBER. multiplication commutes.
     neither party knows BOTH exponents, and the
     secret is the product of both.
     nothing secret ever crossed the wire.

   WHY THE ATTACKER CANNOT FINISH IT
     they have p, g, A, B -- everything sent -- and
     would need `a` from g^a mod p: the DISCRETE LOG.
       forward,  255-bit : 72 microseconds
       backward,  20-bit : half a second
     the gap is a NUMBER. that is all it ever is.
     ECC (X25519) needs 256 bits where classical DH
     needs 2048, because the best attacks are worse.

   THE FREE WIN: ephemeral (the E in ECDHE)
     keypairs cost microseconds -> make one per
     connection, discard it.
     steal the long-term key LATER and last year's
     recorded traffic is STILL unreadable.
     = FORWARD SECRECY. TLS 1.3 deleted every
       exchange that lacked it, which is why
       TLS_AES_256_GCM_SHA384 does not name one.

   WHAT KEY EXCHANGE CANNOT DO
     say WHO. Mallory swaps the .pub files in
     transit, runs the SAME four openssl commands,
     and ends up holding two valid secrets:
       alice<->mallory  and  mallory<->bob
     both ends see valid tags and no errors.
     NOTHING WAS BROKEN. DH did what it promised.
     being in the middle is not an attack posture,
     it is the job description of every router,
     proxy and access point on the path.
                                      -> lesson 05

   FOUR MECHANISMS, AND NOT ONE OF THEM IS IDENTITY
     hash  detects change,  not a changer
     HMAC  proves a holder, not WHICH holder
     AEAD  hides content,   not from an editor
     DH    agrees a secret, not with WHOM
```

**Cleanup:**

```bash
cd "${TMPDIR:-/tmp}" && rm -f alice.pem alice.pub bob.pem bob.pub mallory.pem mallory.pub
```

> **You understand this when you can** derive `n(n-1)/2` from the requirement that no third party can listen, and say why that made pre-shared keys a dead end; explain in one line of algebra why Alice and Bob reach the same number, and state precisely which value neither of them knows; name the problem an attacker would have to solve and give a sense of the forward-versus-backward cost from the numbers you measured; say what a key pair is and why "public" means publishable; explain the two jobs a KDF does on a raw shared secret and why binding a purpose into the derivation matters; describe the man-in-the-middle attack precisely enough to say what Mallory holds at the end of it and why neither party can detect her; explain forward secrecy in terms of a key stolen *after* the traffic was recorded, and why TLS 1.3 stopped offering a choice; and state, for each of this act's four mechanisms so far, the promise it keeps and the one it does not.

**Which raises:** the hole is now sharply shaped, which is progress. Mallory succeeded for one reason: **`bob.pub` arrived with nothing attached to it saying it was Bob's.** It was 32 bytes on a wire, and 32 bytes look the same whoever sent them. So what is needed is a way for a public key to carry a *claim about who it belongs to* — and for that claim to be checkable by someone who has never met Bob, cannot phone him, and is holding nothing but the bytes in front of them. Which sounds like it needs a trusted party who has met Bob, and immediately raises the obvious objection: how does *that* party's claim reach you unforged? The answer is the last mechanism in the act, and it is the one that turns everything you have built into something you have used every day for years without looking inside.

---

↑ **[Act VIII overview](README.md)** · Prev: **[Unreadable is not the same as unchangeable](03-ciphers.md)** · Next: **[A claim someone else vouched for](05-certificates.md)** →
