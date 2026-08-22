# A function that destroys information on purpose

Start with a problem that has nothing to do with secrecy.

You have a file. It travelled across the internet — Act III taught you how many strangers' routers that involves — and you want to know whether it arrived as it left. You cannot compare it against the original, because if you had the original you would not need the copy.

So: **how do you check that a large thing is unchanged, without having the large thing to compare it to?**

Everything in this lesson follows from taking that question literally.

### The smallest possible answer

Whatever you keep must be *small* — that is the whole point, otherwise you would keep the file. So you need a function that turns any amount of input into a fixed, short output. Try one:

```bash
cd "${TMPDIR:-/tmp}" && printf 'a' > f_a && printf 'c' > f_c
openssl dgst -sha256 f_a
openssl dgst -sha256 f_c
```

```
SHA2-256(f_a)= ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb
SHA2-256(f_c)= 2e7d2c03a9507ae265ecf5b5356885a53393a2029d241394997265a1a25aefc6
```

Two one-byte files, 64 hex characters each — 256 bits, whatever the input. `a` is `0x61` and `c` is `0x63`, so those two inputs differ in **exactly one bit**.

> **Predict first —** you changed one bit of the input. Out of the 256 output bits, how many do you expect to change? Commit to a number before you count. There are three defensible answers and only one is right, and which one you pick says exactly what you currently think a hash is.

```bash
h1=$(openssl dgst -sha256 -r f_a | cut -d' ' -f1)
h2=$(openssl dgst -sha256 -r f_c | cut -d' ' -f1)
python3 -c "
a=int('$h1',16); b=int('$h2',16)
print('output bits changed:', bin(a^b).count('1'), 'of 256')"
```

```
output bits changed: 124 of 256
```

**About half.** Not one, which is what "small change, small effect" would predict. Not all 256, which is what "it scrambles everything" would predict. *Half* — and half is the interesting answer, because half is what you would get from **two unrelated random numbers**.

That is the property, and it has a name worth knowing because it is the design goal rather than a side effect: the **avalanche effect**. Every input bit affects every output bit with probability about one half. Try a few more inputs and the number stays near 128; it is not a coincidence of these two files.

Now notice what that buys you, because it is the answer to the opening question. If a single flipped bit produced a single flipped output bit, a hash would be a *summary* — and summaries can be forged, because you could work backwards from the summary you wanted. Half means the output carries no usable trace of the input's structure. There is nothing to work backwards along.

### The direction is the whole point

```bash
printf 'hunter2' | openssl dgst -sha256
```

You can compute that instantly. Now go the other way: given `f52fbd32b2b3b86ff88ef6c490628285f482af15ddcb29541f94bcf526a3f6c7`, recover `hunter2`.

There is no method. Not "a slow method" — no method that is better than trying inputs one at a time and hashing each. And that is not because someone failed to invent one; it is because **the function threw the information away.** Any amount of input, 256 bits of output: a 1 MB file has 2^8000000 possible values and there are only 2^256 outputs, so unimaginably many inputs share each one. The original cannot be recovered because it is not in there.

Which reframes the whole subject. A hash is not encryption and it is not a code. **It is a deliberately lossy function**, and its usefulness comes precisely from the loss. Anything reversible would be useless here.

So when you read that a service "hashes your password," the claim being made is not that your password is hidden somewhere clever. The claim is that it was **destroyed**, and only a fingerprint of it was kept — and the reason that is a good design is that a stolen database of fingerprints is not a database of passwords.

(Only *not a database of passwords* — not "harmless." Guessing is still available, and `hunter2` will be guessed. That is a different problem with a different fix, and it is the one place in this lesson where a plain hash is the wrong tool; hold the thought.)

### Three properties, and where they come from

Everyone lists these. They are much easier to keep straight if you derive them from attacks instead, so pick a use and ask what an attacker would need.

**Use one: you publish a file and its hash.** A reader downloads both and checks. What must an attacker be unable to do? Produce a *different* file with the *same* hash as yours — because that is a substitution nobody can detect. Being unable to do that is **second-preimage resistance**: given a specific input, you cannot find a second one that collides with it.

**Use two: a service stores hashes of passwords.** What must an attacker with the database be unable to do? Turn a hash back into *something that works* — note that it need not be the original password, just any input hashing to the same value. Being unable to do that is **preimage resistance**.

**Use three — and this is the one that bites.** You sign a contract by signing its hash. What must an attacker be unable to do? Here the attacker gets to choose *both* documents in advance: an innocuous one to show you and a damaging one to keep, crafted together so that they hash identically. Nobody has to work backwards from anything. Being unable to do this is **collision resistance**, and it is a strictly weaker guarantee than the other two.

> **Predict first —** SHA-256 gives 256 bits. Roughly how many hashes must an attacker compute to find *some* pair of inputs that collide? The obvious answer is 2^256, or 2^255 for an even chance. Both are wrong, and the true answer is small enough to matter.

The reasoning is the one behind the "birthday paradox": in a room of 23 people two probably share a birthday, even though you need 253 people before one probably shares *yours*. Fixing the target is a much harder problem than finding any match, because with n items you get n(n−1)/2 *pairs* — the pairs grow as the square, so you need only about the square root of the space.

**The square root of 2^256 is 2^128.** So collision resistance is worth **half the bits**, always:

| Hash | Output bits | Preimage | Collision |
|---|---|---|---|
| MD5 | 128 | 2^128 | 2^64 |
| SHA-1 | 160 | 2^160 | 2^80 |
| SHA-256 | 256 | 2^256 | 2^128 |

That division is why hash outputs look extravagantly long. 256 bits is not paranoia about someone reversing your hash; it is 128 bits of collision resistance, which is the number that actually has to survive.

And it is why MD5 died. `2^64` was a plausible amount of work for a well-funded attacker even before anyone found a cleverer method — which they then did.

### Break one yourself

Two commands. These are the 128-byte blocks published by Wang and Yu in 2004, and they are the reason MD5 is not a security primitive any more:

```bash
cd "${TMPDIR:-/tmp}"
printf 'd131dd02c5e6eec4693d9a0698aff95c2fcab58712467eab4004583eb8fb7f8955ad340609f4b30283e488832571415a085125e8f7cdc99fd91dbdf280373c5bd8823e3156348f5bae6dacd436c919c6dd53e2b487da03fd02396306d248cda0e99f33420f577ee8ce54b67080a80d1ec69821bcb6a8839396f9652b6ff72a70' | xxd -r -p > one.bin
printf 'd131dd02c5e6eec4693d9a0698aff95c2fcab50712467eab4004583eb8fb7f8955ad340609f4b30283e4888325f1415a085125e8f7cdc99fd91dbd7280373c5bd8823e3156348f5bae6dacd436c919c6dd53e23487da03fd02396306d248cda0e99f33420f577ee8ce54b67080280d1ec69821bcb6a8839396f965ab6ff72a70' | xxd -r -p > two.bin
```

Confirm they are genuinely different files:

```bash
cmp one.bin two.bin
```

```
one.bin two.bin differ: char 20, line 1
```

Now hash them both, with the broken function and then a working one:

```bash
openssl dgst -md5 one.bin two.bin
openssl dgst -sha256 one.bin two.bin
```

```
MD5(one.bin)= 79054025255fb1a26e4bc422aef54eb4
MD5(two.bin)= 79054025255fb1a26e4bc422aef54eb4

SHA2-256(one.bin)= 8d12236e5c4ed9f4e790db4d868fd5c399df267e18ff65c1107c328228cffc98
SHA2-256(two.bin)= b9fef2a8fc93b05e7701e97196fda6c4fbeea25ff8e64fdfee7015eca8fa617d
```

**Two different files with the same MD5.** Sit with that for a moment, because the abstract sentence "MD5 has collisions" and the two identical strings on your own screen are not the same experience.

Then look at what it actually costs you, which is more specific than "MD5 is insecure." An MD5 collision breaks *use three* and leaves the other two standing: nobody has produced a second preimage for MD5, so `md5sum` still detects a corrupted download from a mirror you trust. It is useless the moment the *author* of the file is the adversary — which is exactly the case for signatures, for image digests, and for anything a supply chain depends on. And note what the attacker did *not* need: no key, no access to your system, nothing but a choice of two documents made in advance.

One more property of the failure, because it is what makes it lethal rather than academic. These blocks are 128 bytes, and MD5 processes input in 64-byte chunks with a running state — so **appending the same bytes to both files preserves the collision**:

```bash
cat one.bin > doc1; echo "  Transfer approved: 100 GBP" >> doc1
cat two.bin > doc2; echo "  Transfer approved: 100 GBP" >> doc2
openssl dgst -md5 doc1 doc2
```

```
MD5(doc1)= a73aac8c3f27ffeb6fdf31e26a5214ef
MD5(doc2)= a73aac8c3f27ffeb6fdf31e26a5214ef
```

Still identical — a *new* shared hash, because the content changed, but shared. So an attacker does not need two useless 128-byte blobs; they need two *documents* that differ in a chosen prefix and agree everywhere after it. Which is how a collision becomes a forged certificate rather than a curiosity.

> **Check yourself —** A colleague proposes signing API requests by appending a shared secret to the request body and hashing the result with SHA-256: `signature = SHA256(body + secret)`. They argue it is safe because SHA-256 is unbroken and an attacker cannot recover the secret from the hash. Both of those claims are true. Why is the scheme still wrong?

<details>
<summary>Answer</summary>

Because it makes a promise with the wrong mechanism, and the mechanism has a structural feature the scheme did not account for.

A hash like SHA-256 processes input as a chain of fixed-size blocks, carrying state forward — the same construction you just exploited to keep the MD5 collision alive across an append. That means someone who knows `SHA256(body + secret)` and the *length* of the secret can continue the computation and produce a valid `SHA256(body + secret + padding + anything_they_like)` **without ever learning the secret.** They append to the message and produce a signature that verifies. It is called a length-extension attack, and it needs neither a collision nor a preimage — the hash is doing exactly what it was designed to do.

The deeper error, though, is the one this act is organised around. Your colleague reached for a mechanism that keeps the promise *"did this change?"* and used it to make the promise *"who says so?"* Those are different promises. A hash has no notion of a sender; it takes bytes and returns bytes, and anyone holding the same bytes computes the same answer. The secret in the formula is doing something that looks like authentication and is not built for it.

What they want is a construction designed for that promise, with the block-chaining problem handled deliberately rather than by hope. That is the next lesson.

</details>

<!-- figure -->

```
   A HASH: any input -> a fixed 256 bits, ONE WAY

   WHY ONE WAY IS STRUCTURAL, NOT DIFFICULT
     1 MB of input = 2^8000000 possible values
     the output    = 2^256 possible values
     -> the information is DESTROYED. it is not hidden anywhere.
     -> "we hash your password" claims it was thrown away,
        not that it was stored cleverly

   AVALANCHE: flip ONE input bit -> ~HALF the output bits change
     (measured: 124 of 256)
     half is what two UNRELATED random numbers would give,
     which is the point: no trace of the input's structure
     survives, so there is nothing to work backwards along

   THREE PROPERTIES, DERIVED FROM WHO THE ATTACKER IS
     preimage         given a hash, find ANY input for it
                      (attacker has your password database)
     2nd preimage     given THIS file, find another with the
                      same hash   (attacker substitutes a download)
     collision        find ANY two colliding inputs, both chosen
                      in advance  (attacker AUTHORS both documents)
                      <- the weakest, and the one that breaks

   >>> COLLISION RESISTANCE IS HALF THE BITS. ALWAYS. <<<
     n(n-1)/2 pairs grow as the SQUARE, so you need the
     SQUARE ROOT of the space -- the birthday bound.
       MD5     128 bits -> 2^64      (broken; you did it above)
       SHA-1   160 bits -> 2^80      (broken, 2017)
       SHA-256 256 bits -> 2^128
     so 256 bits is not paranoia. it is 128 bits of the number
     that actually has to survive.

   WHAT AN MD5 COLLISION DOES AND DOES NOT COST YOU
     STILL FINE:  detecting a corrupted download from a mirror
                  you trust (no second preimage is known)
     USELESS:     anything where the file's AUTHOR is the
                  adversary -- signatures, image digests,
                  supply chains
     and appending the same bytes to both files PRESERVES the
     collision, which is how it becomes a forged document

   WHAT A HASH CANNOT DO
     nothing here stops an attacker who can change the HASH too.
     and a hash has no notion of a sender: same bytes in,
     same bytes out, for everybody. -> lesson 02
```

**Cleanup:**

```bash
cd "${TMPDIR:-/tmp}" && rm -f f_a f_c one.bin two.bin doc1 doc2
```

> **You understand this when you can** say what problem a hash solves and why the answer has to be small; explain from the sizes involved why a hash cannot be reversed, and why that makes "we hash your passwords" a claim about destruction rather than concealment; state what the avalanche effect is and why *half* is the right number rather than all; distinguish the three resistance properties by which attacker each one defends against, and say which of them MD5 lost; derive from the birthday bound why collision resistance is half the output bits, and give the number for SHA-256; and explain what an MD5 collision does and does not let an attacker do.

**Which raises:** every use in this lesson quietly assumed the reader gets the hash from somewhere trustworthy. Publish a file and its hash on the same page, and anyone who can change the file can change the hash beside it — so the check proves only that a tamperer was thorough. What is needed is a hash that **only certain people can compute**, so that matching it is evidence about *who*, not merely about *what*. And the obvious way to do that — mixing a secret into the input — turns out to have a hole you have already seen.

---

↑ **[Act VIII overview](README.md)** · Next: **[A hash only certain people can compute](02-hmac.md)** →
