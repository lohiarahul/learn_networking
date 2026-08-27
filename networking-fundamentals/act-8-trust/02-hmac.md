# A hash only certain people can compute

Last lesson ended with a colleague's proposal and a claim that it was wrong. This lesson is about taking that proposal seriously enough to break it, because the break is more instructive than the objection.

Their scheme: sign an API request by mixing a shared secret into the body and hashing the result.

```
signature = SHA256(secret + body)
```

The server holds the same secret, recomputes, and compares. Anyone who does not know the secret cannot produce a matching signature, so a matching signature proves the sender knew the secret. That is authentication, built out of a hash and nothing else, in one line.

And it is worth being clear how much of that reasoning is correct, because almost all of it is. SHA-256 is not broken. You cannot recover the secret from the digest — lesson 01 showed why the sizes forbid it. There is no collision attack in reach. Every individual claim your colleague made is true.

**The scheme still fails completely, and it fails without breaking SHA-256 at all.**

> **Predict first —** an attacker sees one legitimate request and its signature. They do not know the secret and will never learn it. Before reading on: what could they *do* with that pair? Not in principle — concretely, what other `(body, signature)` pair could they construct that the server would accept? Lesson 01 put the mechanism in your hands twice, once in the avalanche experiment and once in the collision append. One of those two is the door.

### Doing it

This needs a SHA-256 you can start in the middle, which no real library will let you do — so the script below carries its own. You do not have to trust that it is a real SHA-256, and you should not: line 62 is `assert sha256(b'msg') == hashlib.sha256(b'msg').hexdigest()`, so if the implementation were wrong in any way the script would refuse to run at all. Save it and read only the second half:

```bash
cd "${TMPDIR:-/tmp}" && cat > extend.py <<'PY'
import struct, hashlib

# ===== PART 1: a stock SHA-256. You do not have to read this. =====
# The one unusual thing: sha256() takes an optional starting STATE and a
# count of bytes ALREADY consumed. A real library will not expose those.
K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
     0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
     0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
     0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
     0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
     0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
     0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
     0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
M = 0xffffffff
IV = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
def rr(x,n): return ((x>>n)|(x<<(32-n))) & M
def compress(st, blk):
    w = list(struct.unpack('>16I', blk))
    for i in range(16,64):
        s0 = rr(w[i-15],7)^rr(w[i-15],18)^(w[i-15]>>3)
        s1 = rr(w[i-2],17)^rr(w[i-2],19)^(w[i-2]>>10)
        w.append((w[i-16]+s0+w[i-7]+s1) & M)
    a,b,c,d,e,f,g,h = st
    for i in range(64):
        t1 = (h + (rr(e,6)^rr(e,11)^rr(e,25)) + ((e&f)^(~e&g)) + K[i] + w[i]) & M
        t2 = ((rr(a,2)^rr(a,13)^rr(a,22)) + ((a&b)^(a&c)^(b&c))) & M
        h,g,f,e,d,c,b,a = g,f,e,(d+t1)&M,c,b,a,(t1+t2)&M
    return [(x+y)&M for x,y in zip(st,[a,b,c,d,e,f,g,h])]
def padding(total_len):
    "the bytes SHA-256 appends to a message of this length"
    return b'\x80' + b'\x00'*((55-total_len) % 64) + struct.pack('>Q', total_len*8)
def sha256(data, state=IV, already=0):
    st = list(state)
    data = data + padding(already + len(data))
    for i in range(0, len(data), 64):
        st = compress(st, data[i:i+64])
    return ''.join('%08x' % x for x in st)
assert sha256(b'msg') == hashlib.sha256(b'msg').hexdigest()

# ===== PART 2: the scheme, and the attack. Read this part. =====

# --- what the SERVER knows. The attacker never sees this.
SECRET = b'correct-horse'                       # 13 bytes
def server_accepts(body, sig):
    return hashlib.sha256(SECRET + body).hexdigest() == sig

# --- what the ATTACKER captured off the wire: one request, one signature.
body = b'user=alice&action=read'
sig  = hashlib.sha256(SECRET + body).hexdigest()
print("captured body :", body.decode())
print("captured sig  :", sig)
print("accepted?     :", server_accepts(body, sig))

# --- the attack. Note what does NOT appear below: SECRET.
keylen = 13                                     # guessed, or tried 1..64
state  = [int(sig[i*8:(i+1)*8], 16) for i in range(8)]
glue   = padding(keylen + len(body))
evil   = b'&action=delete_everything'

forged_body = body + glue + evil
forged_sig  = sha256(evil, state=state, already=keylen + len(body) + len(glue))
print()
print("forged body :", forged_body)
print("forged sig  :", forged_sig)
print("accepted?   :", server_accepts(forged_body, forged_sig))
PY
python3 extend.py
```

```
captured body : user=alice&action=read
captured sig  : 371d8a6435e43f0f781dc64e06afcf7e0fe890257d7ca4e670757b6a775035b9
accepted?     : True

forged body : b'user=alice&action=read\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00
              \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x18&action=delete_everything'
              (one line in reality; wrapped here to fit)
forged sig  : c119bd5b469c0bd9f2bf35dccc6ea3d758804d28b55677b3cd5000149052a12b
accepted?   : True
```

**A signature the server accepts, for a message the server never authorised, produced by someone who does not have the key.** Read Part 2 again and confirm the important thing: `SECRET` appears in the server's two functions and nowhere in the eleven lines of attack.

### Why it worked

Reconstruct it, because the reason is one sentence and it recasts everything lesson 01 said.

SHA-256 eats its input in 64-byte blocks. Each block updates a 256-bit running state, and when the input runs out the final state *is* the digest. That is the construction — a small machine, fed a block at a time — and it has a name, **Merkle–Damgård**, worth knowing only because it is the label for "hashes that work this way, and therefore have this problem." SHA-1, SHA-256 and MD5 all do. Not everything does, which matters at the end of this lesson.

So look at what publishing a digest actually publishes. Not a summary of the input. **The machine's exact resume point.** Hand someone `SHA256(secret + body)` and you have handed them the internal state of a computation that has already absorbed the secret — so they can carry on from there, appending whatever they like, without ever knowing what went in before.

They need one more thing, and it is the ugly run of bytes in the middle of the forged body. SHA-256 does not hash a bare message; it appends **padding** first — a `0x80` byte, zeros, and the total bit length in the last eight bytes. Here `\x01\x18` is 280, which is `(13 + 22) × 8`: the length of the secret plus the body. The attacker cannot omit that, because the server will compute it. So the attacker includes it *in the message*, as literal bytes, and continues past it. That is why the forged body has garbage in the middle — and why the attack only matters where the receiver tolerates it, which query strings, JSON parsers and log lines very often do.

Two things fall out that are worth naming now:

- **The key's length is not a secret and cannot be made one.** The attacker guessed 13. Guessing wrong costs one attempt; a loop over 1 to 64 costs nothing. Any scheme whose safety rests on the length of a key has no safety.
- **This is not a flaw in SHA-256.** Length extension is the *specified behaviour* of a streaming hash, and it is exactly the property lesson 01 exploited to keep an MD5 collision alive across an append. Your colleague did not choose a weak hash. They chose a mechanism that keeps the promise *"did this change?"* and asked it for *"who says so?"*

> **Check yourself —** the obvious patch is to swap the order: `SHA256(body + secret)`. The secret now goes in last, the attacker cannot resume past it, and length extension is dead. Something is still wrong. What?

<details>
<summary>Answer</summary>

Length extension is genuinely fixed. The scheme now fails to a different attack, and the switch is instructive because it trades one of lesson 01's three resistance properties for another.

With the secret at the end, an attacker who finds **any collision** in the hash — two distinct bodies `B1` and `B2` with `SHA256(B1) == SHA256(B2)` — gets a signature forgery for free. The two computations reach an identical state at the point where the secret starts, so appending the same secret to both yields the same digest. Capture a legitimate signature on `B1`, ship `B2` with it, and the server accepts.

So the suffix scheme's safety rests on **collision resistance**, which lesson 01 established is the *weakest* of the three properties and the one that always falls first: half the output bits, and the reason MD5 and SHA-1 died. Sign with `MD5(body + secret)` and this is not theoretical — you already have the colliding blocks on your disk from lesson 01. With SHA-256 it is currently out of reach, but you have made your authentication depend on the property most likely to erode.

Neither ordering is safe for the right reason. The prefix version leaks resumable state; the suffix version inherits collision weakness. What is needed is a construction where **neither end of the message is where the key lives.**

</details>

### The fix, derived

You need the attacker to be unable to resume — which means the state they are handed must not be a state that has absorbed the key and is waiting for more input. So the digest they see must come from a hash that has *already finished*, and whose input length was fixed before they ever saw it.

There is a blunt way to get that: hash twice. Do the inner hash however you like, then hash *that result* with the key again. The attacker holding the outer digest can resume the outer computation, but the outer computation's input was a fixed-size block plus a 32-byte digest and is already over — there is nothing to extend that the server would ever read.

That is HMAC, and it is genuinely almost that simple:

```
HMAC(key, msg) = H( (key ^ opad) || H( (key ^ ipad) || msg ) )
```

Two passes. The key is XORed with a different constant each time — `ipad` is `0x36` repeated, `opad` is `0x5c` repeated.

That detail is worth one sentence of *why*, because it looks arbitrary and is not. `0x36` and `0x5c` differ in four bits of every byte, so `key ^ ipad` and `key ^ opad` are two values that differ in half their bits — which, by lesson 01's avalanche property, makes the inner and outer passes behave as though keyed independently. Had the two constants been equal, the construction would be `H(k' || H(k' || msg))` with a *single* derived key used at both levels, and the security proof HMAC rests on would no longer apply. Two constants is the cheapest possible way to get two keys out of one.

Build it by hand and check it against the library:

```bash
python3 - <<'PY'
import hashlib, hmac
key, msg = b'k1', b'msg'
B = 64                                    # SHA-256's block size, in bytes
k = key + b'\x00' * (B - len(key))        # pad the key out to one block
inner = hashlib.sha256(bytes(x ^ 0x36 for x in k) + msg).digest()
outer = hashlib.sha256(bytes(x ^ 0x5c for x in k) + inner).hexdigest()
print("by hand :", outer)
print("library :", hmac.new(key, msg, hashlib.sha256).hexdigest())
PY
```

```
by hand : 7fe2f2cce3a8451c9159611204763cfca4fc7e3e5cf3da9f2c9aa756dfb40384
library : 7fe2f2cce3a8451c9159611204763cfca4fc7e3e5cf3da9f2c9aa756dfb40384
```

**Nine lines, and they are the whole of it.** No new mathematics appeared. HMAC is not a cipher, not a signature, not a new primitive — it is a hash you already had, wrapped in a shape chosen specifically to defeat the attack you just performed. Which is why it can be built from *any* Merkle–Damgård hash and inherits that hash's strength.

And `openssl` will do it directly, so you never have to write the nine lines again:

```bash
cd "${TMPDIR:-/tmp}" && printf 'msg' > m.txt
openssl dgst -sha256 -hmac "k1" m.txt
openssl dgst -sha256 -hmac "k2" m.txt
```

```
HMAC-SHA2-256(m.txt)= 7fe2f2cce3a8451c9159611204763cfca4fc7e3e5cf3da9f2c9aa756dfb40384
HMAC-SHA2-256(m.txt)= 2791076eb2511be973a89c6108c1f7ee8f728930880512125dbb33f8978b9f53
```

Same message, two keys, two unrelated answers — which is the property the whole thing exists for. **The digest is now a function of who you are as well as what you said.** Note also that the by-hand result matches `-hmac "k1"` exactly, so the nine lines were not an illustration of HMAC; they were HMAC.

One consequence to check rather than assume, since lesson 01 made a point of measuring avalanche on the *input*:

```bash
python3 -c "
import hmac, hashlib
a = hmac.new(b'k1', b'msg', hashlib.sha256).hexdigest()
b = hmac.new(b'k0', b'msg', hashlib.sha256).hexdigest()
print(a); print(b)
print('bits differ:', bin(int(a,16) ^ int(b,16)).count('1'), 'of 256')"
```

```
7fe2f2cce3a8451c9159611204763cfca4fc7e3e5cf3da9f2c9aa756dfb40384
da468e232446edf17bda4b770e5cf88dc6c27e87790ae352de88e24d39bf9ff7
bits differ: 128 of 256
```

`k1` and `k0` differ in one bit. **Exactly half the output changed** — the same number lesson 01 predicted for a one-bit message change, now holding for a one-bit *key* change. The key gets the avalanche too, which is why an attacker who knows the message and the digest learns nothing about the key by trying neighbours of a guess.

### The two holes

The first is a design detail with an operational sting, and you can see it in one command. Try a key longer than the 64-byte block:

```bash
LONG=$(python3 -c "print('A'*100)")
openssl dgst -sha256 -hmac "$LONG" m.txt
python3 -c "
import hashlib, hmac
print('hmac(sha256(key)):', hmac.new(hashlib.sha256(b'A'*100).digest(), b'msg', hashlib.sha256).hexdigest())"
```

```
HMAC-SHA2-256(m.txt)= 4444a6268d12b5d1f9145b0c214e98cab83bf6a9a5d5ee2d363fb630b850bb9c
hmac(sha256(key)): 4444a6268d12b5d1f9145b0c214e98cab83bf6a9a5d5ee2d363fb630b850bb9c
```

Identical. **A key longer than the block size is silently replaced by its own hash** — the construction has to fold it down to one block, and hashing is how. So a 100-byte key and its 32-byte digest are *the same key*, and any key longer than 64 bytes buys exactly nothing over 32 bytes of good randomness.

Nothing warns you, and it is worth being fair about why not. From the implementer's side this is not an error condition — it is the specified key-preprocessing step, defined for every input length, and returning it faithfully is the correct behaviour. There is no such thing as a key that is "too long"; there is only a key whose extra bytes stop counting. A warning would be a library second-guessing a specification it is required to implement. Which is exactly why *you* have to know it: the surprise is real, it is nobody's bug, and so nothing in the system is ever going to tell you. Same shape as lesson 01's birthday bound — a number you thought you had, quietly smaller.

The second hole is the one that ends the lesson, and it is not a flaw — it is the boundary of what a shared secret can ever prove.

> **Check yourself —** you and a payment provider share an HMAC key. A signed instruction arrives moving money out of your account. You say you never sent it. They say the HMAC verifies, so you must have. Who is right, and what can the HMAC actually settle?

<details>
<summary>Answer</summary>

Neither, and that is the point. The HMAC proves the message was produced by **someone holding the key**, and two parties hold it. It cannot distinguish between them.

Verification and creation are the *same operation* with the same input. So the provider can compute any HMAC you can compute, which means they can manufacture an instruction, sign it correctly, and present a verifying message they authored themselves. Nothing in the mathematics distinguishes that from you having sent it — and nothing ever will, because the property is symmetric by construction.

The name for what is missing is **non-repudiation**: evidence that binds a message to *one* party in a way even the other party cannot fake. A shared secret cannot give it. Any number of parties holding the same key are, cryptographically, one indistinguishable party.

This is not a reason to avoid HMAC. It is a reason to know what you bought. Inside one system — a service signing its own cookies, a cluster verifying its own tokens — there is only one holder in any meaningful sense and non-repudiation is not wanted. Between mutually distrusting parties it is the whole question, and it needs a mechanism where the power to *verify* is separable from the power to *sign*.

</details>

<!-- figure -->
```
   THE SCHEME YOU BROKE, AND THE ONE THAT REPLACES IT

     SHA256(secret || body)
       digest = the machine's RESUME POINT, key already
       absorbed -> attacker appends freely, no key needed
       (you did this. 11 lines. no crypto broken.)
       and the KEY LENGTH is not a secret: loop 1..64

     SHA256(body || secret)
       length extension DEAD. now rests on COLLISION
       resistance -- lesson 01's WEAKEST property, the
       one that is half the bits and always falls first

     HMAC(key, msg) = H( (key^opad) || H( (key^ipad) || msg ) )
       the key is at NEITHER end of the message.
       outer input = one block + one digest = FIXED LENGTH,
       already finished -> nothing to extend.
       ipad=0x36 opad=0x5c: two DIFFERENT derived keys,
       not the same key twice

   WHAT IT COSTS YOU TO KNOW
     key > 64 bytes is SILENTLY replaced by its own hash.
       a 100-byte key IS its 32-byte digest. no warning.
     no new primitive appeared. HMAC is a SHAPE around a
       hash you already had. that is why it inherits the
       hash's strength and works with any of them.

   WHAT AN HMAC CANNOT DO
     HIDE ANYTHING. the message travels in the clear;
       an HMAC is a tag beside it, not a wrapper round it.
                                             -> lesson 03
     PROVE WHICH HOLDER. verifying and signing are the
       SAME operation, so every holder can forge every
       other's messages. no non-repudiation, ever.
                                             -> lesson 05
     GET THE KEY TO THE OTHER PARTY. this lesson assumed
       you both already have it.             -> lesson 04
```

**Cleanup:**

```bash
cd "${TMPDIR:-/tmp}" && rm -f extend.py m.txt
```

> **You understand this when you can** state what a length-extension attack needs and what it does
> not, and explain why publishing `SHA256(secret + body)` publishes a resumable computation;
> explain why swapping the concatenation order kills it and what weaker property it then leans on;
> write HMAC's two-pass shape and say what the outer hash accomplishes that the inner one cannot;
> and explain why a shared secret cannot give non-repudiation however strong the hash.

**Which raises:** you now have integrity and you have authenticity, and between them they have not concealed a single byte. An HMAC travels *beside* the message, in the clear, and the message is as readable as it ever was — lesson 01's promise table said as much, but it lands differently now that you have watched a tag verify a plaintext instruction to move money. So the next question is the one everybody assumes cryptography is about in the first place: **making the bytes unreadable to anyone but the intended reader.** That turns out to be a much older problem than the two you just solved, and in one specific sense an easier one — there is a scheme for it that is not merely infeasible to break but provably impossible, which is a sentence that will not appear again in this act. The interesting part is what it costs, and what people do to avoid paying.

---

↑ **[Act VIII overview](README.md)** · Prev: **[A function that destroys information on purpose](01-hashing.md)** · Next: **[Unreadable is not the same as unchangeable](03-ciphers.md)** →
