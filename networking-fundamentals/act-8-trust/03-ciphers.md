# Unreadable is not the same as unchangeable

> **Optional track — examined by neither CKA nor CKS.** **Act VIII 01–04 is a cryptography short
> course** — 12,323 words — sitting underneath the two lessons of this act that *are* on the exam
> path (`05` certificates, `06` TLS opened). Those two stand on their own: what they assert, these
> four prove. The [exam path](../../exam-prep/the-exam-path.md) skips straight to `05`. Route A — the
> course — does not, and this is the material the repository is proudest of.

Two lessons in and nothing has been hidden. A hash summarises a message that anyone can read; an HMAC travels *beside* a message that anyone can read. Both promises were about detection after the fact, and neither of them concealed a byte.

So: **confidentiality.** Make the bytes meaningless to anyone but the intended reader. This is the promise most people think cryptography *is*, and it is by far the oldest of the four — people were doing it two thousand years before anyone thought to ask "did this change?"

It is also, in one specific sense, the easiest. There is a scheme with *perfect* secrecy — provably, mathematically unbreakable, not merely infeasible — and it is one operation you already know.

> **Predict first —** you want a reversible operation that combines a message with a key. It has to be reversible, or the recipient cannot read it either. Name the operation. There is one obvious candidate available on every byte in existence, you have almost certainly used it for something else, and it is the answer.

### The scheme that cannot be broken

XOR. Combine each message byte with a key byte; XOR the same key back to undo it. If the key is **random, as long as the message, and never reused**, the result is a *one-time pad*, and it is genuinely unbreakable: for any ciphertext, every plaintext of that length is equally likely, so there is nothing to attack. Not infeasible — impossible. The only such thing in this act.

And it is nearly useless, for a reason worth stating precisely: **the key is as long as the message.** If you have a secure way to move a key that big, you had a secure way to move the message, so the cipher bought you nothing but a delay. This is not an engineering wrinkle. It is the reason every other cipher exists.

The interesting part is what happens when someone tries to fix that by reusing the pad — because it is the most tempting shortcut available and the failure is total:

```bash
cd "${TMPDIR:-/tmp}" && python3 - <<'PY'
import os
key = os.urandom(32)                          # one pad
m1  = b'transfer 100 to bob'
m2  = b'transfer 999 to eve'                  # SAME pad, second message
c1 = bytes(a ^ b for a, b in zip(m1, key))
c2 = bytes(a ^ b for a, b in zip(m2, key))
print("c1 ^ c2 =", bytes(a ^ b for a, b in zip(c1, c2)).hex())
print("m1 ^ m2 =", bytes(a ^ b for a, b in zip(m1, m2)).hex())
x = bytes(a ^ b for a, b in zip(c1, c2))
print("given m1, recovered:", bytes(a ^ b for a, b in zip(x, m1)))
PY
```

```
c1 ^ c2 = 00000000000000000008090900000000071907
m1 ^ m2 = 00000000000000000008090900000000071907
given m1, recovered: b'transfer 999 to eve'
```

**XOR the two ciphertexts and the key cancels out.** It appears in both, so it vanishes, and what is left is the XOR of the two *plaintexts* — which you can read structure out of directly (all those zeros are where the messages agree), and which hands you the second message outright if you can guess the first. The attacker never touched the key.

Remember that hex string. You will see it again at the end of this lesson, produced by a cipher considered state of the art.

### A short key that behaves like a long one

The requirement, then: something that turns a *small* key into an arbitrarily long stream of unpredictable-looking bytes. That is a **block cipher** — AES being the one you will meet everywhere — and it does exactly one thing:

**AES takes a 16-byte block and a key, and permutes the block.** That is all. It is not a system for encrypting messages; it is a keyed shuffle of sixteen bytes, and it is reversible only because you hold the key.

Sixteen bytes is not a message, so the question of how you use it to encrypt something longer is a separate design decision with a separate name: a **mode of operation**. Modes are where every interesting failure lives.

The most obvious mode is to chop the input into 16-byte blocks and encrypt each one independently. It is called ECB. Try it on 48 identical bytes:

```bash
cd "${TMPDIR:-/tmp}" && printf 'A%.0s' {1..48} > rep.bin
openssl enc -aes-128-ecb -nosalt -K 00112233445566778899aabbccddeeff -in rep.bin | xxd
```

(`-nosalt` because `openssl enc` otherwise derives the key from a passphrase and a random salt; here the key is being supplied directly with `-K`, so there is nothing to derive and a salt would only add a header.)

```
00000000: 5301 d125 1af0 8a9e a49c f859 82d8 df6e  S..%.......Y...n
00000010: 5301 d125 1af0 8a9e a49c f859 82d8 df6e  S..%.......Y...n
00000020: 5301 d125 1af0 8a9e a49c f859 82d8 df6e  S..%.......Y...n
00000030: 0065 7ea1 4065 5a44 7827 4770 5d42 2fad  .e~.@eZDx'Gp]B/.
```

**Three identical ciphertext blocks.** AES is not weak here — it is behaving exactly as specified. The mode is what leaked: identical input blocks produce identical output blocks, so **the ciphertext preserves every repetition in the plaintext.** Encrypt a bitmap this way and you can still see the picture; this is the famous "ECB penguin," and the hex above is the same fact without needing an image. Encrypt a database column this way and equal values stay visibly equal, which is enough to break it.

(The fourth block is padding — 48 bytes is exactly three blocks, so the cipher appends a whole block of it. A block cipher must emit whole blocks, so it always adds padding, even when the input divides evenly. That fact has its own catastrophic history, and it is not this lesson's.)

The fix is to make each block depend on the one before it. Chain them — CBC — XORing each plaintext block with the previous *ciphertext* block before encrypting. Same key, same input, one flag different:

```bash
openssl enc -aes-128-cbc -nosalt -K 00112233445566778899aabbccddeeff \
  -iv 00000000000000000000000000000000 -in rep.bin | xxd
```

```
00000000: 5301 d125 1af0 8a9e a49c f859 82d8 df6e  S..%.......Y...n
00000010: 9d61 b215 32da ce7b 1afe a738 ab28 ff57  .a..2..{...8.(.W
00000020: d033 877d ace7 87bc 32e9 d6bf 37b3 44a5  .3.}....2...7.D.
00000030: 6519 8316 f628 4b3f 56ff f59a 562c d625  e....(K?V...V,.%
```

**The pattern is gone.** The first block matches ECB's because the chain had nothing to XOR it with yet — which is what that `-iv` argument is for: an **initialisation vector**, a starting value to chain the first block against, so that encrypting the same message twice with the same key gives different ciphertext. It is not a secret. It travels with the ciphertext in the clear, because the recipient needs it.

### The tool refuses

Before going further, ask for what you actually want. `TLS_AES_256_GCM_SHA384` — the string Act III left you holding — names GCM, so ask `openssl enc` for it:

```bash
openssl enc -aes-256-gcm -nosalt \
  -K 00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff \
  -iv 000000000000000000000000 -in rep.bin
```

```
enc: AEAD ciphers not supported
enc: Use -help for summary.
```

If instead you got `bad decrypt`, you are running Apple's stock `/usr/bin/openssl`, which is **LibreSSL** — a different project that reports a version number starting with 3 and is not OpenSSL 3.x. Everything else in this act works identically on it; this one block does not. `brew install openssl` and use that binary for this section.

**A refusal, not a failure.** Worth stopping on, because a tool declining to do something it obviously knows how to do is usually telling you that your mental model is wrong. `enc`'s entire interface is *bytes in, bytes out* — it is a filter. Whatever GCM is, it does not fit that shape.

> **Predict first —** work out what GCM must produce that a filter cannot express, and you will have derived the rest of this lesson. The clue is in the name of the category the error message uses: **AEAD**, where the first two letters stand for "authenticated encryption." What extra thing would come out, and what extra thing could therefore go wrong on the way back in?

### The gap, demonstrated

CBC hid the pattern. Here is what it did not do. The reader below holds a key you will never see:

The next four blocks are the only place in this act that needs a Python package. Check whether you already have it, and install it only if not:

```bash
python3 -c 'import cryptography; print(cryptography.__version__)'
```

If that fails, note that a bare `pip install` is refused on most current systems — Homebrew Python and Debian/Ubuntu both mark themselves *externally managed*, and `--user` does not help. Use a throwaway virtual environment, which is the right answer anyway for a package you need for one lesson:

```bash
cd "${TMPDIR:-/tmp}" && python3 -m venv .venv && source .venv/bin/activate
pip install cryptography
```

```bash
python3 - <<'PY'
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
key = os.urandom(16)                    # the ATTACKER never sees this
iv  = os.urandom(16)
pt  = b'role=user;id=777'               # exactly one 16-byte block

e  = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
ct = e.update(pt) + e.finalize()

def server_reads(iv_, ct_):
    d = Cipher(algorithms.AES(key), modes.CBC(iv_)).decryptor()
    return d.update(ct_) + d.finalize()

print("server reads:", server_reads(iv, ct))

# --- the attacker has iv and ct, knows the FORMAT, and has no key
want    = b'role=root;id=777'
evil_iv = bytes(a ^ b ^ c for a, b, c in zip(iv, pt, want))
print("server reads:", server_reads(evil_iv, ct))
print("ciphertext modified:", False)
PY
```

```
server reads: b'role=user;id=777'
server reads: b'role=root;id=777'
ciphertext modified: False
```

**`user` became `root`, and the ciphertext was not touched.** Only the IV — the value that travels in the clear precisely because it is not a secret.

The mechanism is CBC run backwards. Decryption computes `plaintext = AES_decrypt(ciphertext) XOR previous_block`, and for the first block the "previous block" is the IV. So the IV is XORed straight into the output, which means **anyone who can change the IV can flip any bit they choose in the first plaintext block**, without the key and without touching a byte of ciphertext. Deeper blocks work the same way, using the preceding ciphertext block instead — at the cost of shredding that earlier block into garbage, which a receiver tolerating one mangled field will happily accept.

Note carefully what the attacker needed: not the key, and not even the plaintext. They needed to know its **format** — that a `role=` field sits at that offset. Formats are documented. This is the lesson's title, and it is the thing to carry out of this act:

**A message an attacker cannot read is very often one they can edit, in a controlled way, with predictable results.** Encryption is not integrity. They are two of the four promises, and a cipher keeps exactly one of them.

### Building the missing half

You already have the mechanism for the other one. Lesson 02 built a tag that proves *nobody changed this*, and nothing about it cared whether its input was readable. So: encrypt, then authenticate the ciphertext.

```bash
python3 - <<'PY'
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import hmac, hashlib, os
kE, kM = os.urandom(16), os.urandom(32)        # SEPARATE keys. see below.
iv, pt = os.urandom(16), b'role=user;id=777'

e   = Cipher(algorithms.AES(kE), modes.CBC(iv)).encryptor()
ct  = e.update(pt) + e.finalize()
tag = hmac.new(kM, iv + ct, hashlib.sha256).digest()      # over the IV too

def server_reads(iv_, ct_, tag_):
    if not hmac.compare_digest(tag_, hmac.new(kM, iv_ + ct_, hashlib.sha256).digest()):
        return "REJECTED: tag mismatch"
    d = Cipher(algorithms.AES(kE), modes.CBC(iv_)).decryptor()
    return d.update(ct_) + d.finalize()

print("honest  :", server_reads(iv, ct, tag))
want    = b'role=root;id=777'
evil_iv = bytes(a ^ b ^ c for a, b, c in zip(iv, pt, want))
print("tampered:", server_reads(evil_iv, ct, tag))
PY
```

```
honest  : b'role=user;id=777'
tampered: REJECTED: tag mismatch
```

**The same attack, refused.** You have just built an AEAD out of two mechanisms from two lessons, and three details in those fifteen lines are the difference between this working and this being a well-known vulnerability:

- **The tag covers the IV.** Authenticate only the ciphertext and the attack above still works, because the IV is what got edited. Anything that reaches the decryption function must be under the tag.
- **The tag is computed over the *ciphertext*, not the plaintext.** Encrypt-then-MAC. The other order — MAC-then-encrypt — means the receiver must decrypt *before* it can check anything, so it is doing cryptographic work on attacker-controlled input, and the errors it produces while doing so have historically been enough to recover the plaintext one byte at a time.
- **Two separate keys.** Never use one key for two different primitives. Deriving `kE` and `kM` from one master secret is fine and normal; passing the same bytes to AES and to HMAC means every tag you publish is computed under the same key that is encrypting your traffic, so any weakness in either primitive's use of that key now leaks into the other — and the analysis that says HMAC is safe assumed its key was used for nothing else. You are not defended by a proof that no longer covers your case.
- **`compare_digest`, not `==`.** A normal comparison returns as soon as two bytes differ, so how long it takes reveals *how much of the tag was right* — which lets an attacker build a valid tag a byte at a time. Constant-time comparison exists for exactly this.

That is four ways to get it wrong in a construction whose idea is one sentence. Which is the argument for the thing `openssl enc` refused to give you: a **single primitive that does both promises at once**, so that none of those four decisions is yours to make.

```bash
python3 - <<'PY'
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
key, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
a  = AESGCM(key)
ct = a.encrypt(nonce, b'role=user;id=777', None)
print("16 bytes in ->", len(ct), "bytes out")
print("decrypt:", a.decrypt(nonce, ct, None))
try:
    a.decrypt(nonce, bytes([ct[0] ^ 1]) + ct[1:], None)      # flip ONE bit
except Exception as ex:
    print("one flipped bit ->", type(ex).__name__)
PY
```

```
16 bytes in -> 32 bytes out
decrypt: b'role=user;id=777'
one flipped bit -> InvalidTag
```

**Sixteen bytes became thirty-two, and there is the answer to the prediction.** AEAD output is not ciphertext; it is ciphertext *plus a 16-byte authentication tag*, and decryption either returns the plaintext or raises — it has a third outcome that a filter cannot express. That is why `openssl enc` refused: `enc` can put bytes on stdout, but it has nowhere to put "this was tampered with."

`InvalidTag` on one flipped bit is what makes the CBC attack impossible rather than merely detected. There is no partial success and no plaintext returned alongside a warning: an AEAD decryption that fails yields *nothing*.

AES-GCM is one AEAD; the other you will meet constantly is **ChaCha20-Poly1305**, which pairs a different stream cipher with a different authenticator and exists for one practical reason. AES is fast when the processor has instructions for it and slow when it does not, so on hardware without AES acceleration — older phones, small embedded devices — ChaCha20 is several times quicker. Same two promises, same interface, same nonce discipline. Which one a connection uses is a negotiation, not a security decision.

> **Check yourself —** `AESGCM.encrypt` takes a third argument, which was `None` above. It is called **associated data**: bytes that get authenticated but not encrypted. That sounds like a contradiction. What is it for, and what breaks if you leave it out?

<details>
<summary>Answer</summary>

It is for the parts of a message that have to travel readable but must not be alterable — and almost every real protocol has some.

A packet needs its header in the clear, because the machinery that routes it has to read it before anyone decrypts anything: a sequence number, a message type, a destination, a key identifier saying which key to use. Encrypting those would make the message undeliverable. Leaving them out of the tag makes them editable, which is the attack you just performed, moved from the payload to the envelope.

So associated data is the third input: authenticated, not encrypted. Change one byte of it and decryption raises `InvalidTag`, exactly as if you had edited the ciphertext.

What breaks without it is subtler than tampering with a header, though, and it is worth knowing because it is a genuine class of bug. Suppose you correctly AEAD-encrypt a database field and a valid, correctly-tagged, perfectly-authentic ciphertext is *moved* — from one row to another, from a test account to a production one, from the `notes` column to the `password_reset_token` column. Nothing was forged. The tag verifies, because it is a real tag on real ciphertext. What the message no longer means is what it meant where it was written.

Binding the context in as associated data — the row id, the column name, the account — is what makes that ciphertext valid *only in the place it was created*. The rule underneath: an AEAD authenticates the bytes you gave it and nothing else, so anything the meaning depends on has to be one of those bytes.

</details>

### The hole, and it is the one from the first page

AEAD keeps two promises with one primitive and is the right default for essentially everything. It has one catastrophic failure mode, and you have already performed it:

```bash
python3 - <<'PY'
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
key, nonce = AESGCM.generate_key(bit_length=256), b'same-nonce!!'   # REUSED
a  = AESGCM(key)
m1, m2 = b'transfer 100 to bob', b'transfer 999 to eve'
c1 = a.encrypt(nonce, m1, None)[:len(m1)]        # drop the tags
c2 = a.encrypt(nonce, m2, None)[:len(m2)]
x  = bytes(p ^ q for p, q in zip(c1, c2))
print("c1 ^ c2 =", x.hex())
print("m1 ^ m2 =", bytes(p ^ q for p, q in zip(m1, m2)).hex())
print("given m1, recovered:", bytes(p ^ q for p, q in zip(x, m1)))
PY
```

```
c1 ^ c2 = 00000000000000000008090900000000071907
m1 ^ m2 = 00000000000000000008090900000000071907
given m1, recovered: b'transfer 999 to eve'
```

**That is the same hex string as the top of this lesson**, and the same recovered message, out of AES-256-GCM.

Because that is what GCM is. It uses AES to generate a *keystream* from the key and the nonce, and XORs. Reuse the nonce with the same key and you have generated the same pad twice — so you are back on page one, and every argument you made there applies unchanged. (It is worse than shown: nonce reuse in GCM also leaks the value used to compute tags, which lets an attacker forge messages, not merely read them.)

Hence the name. A nonce is a **n**umber used **once**, and the discipline is the whole of it: never twice with the same key, ever. Which is why 96 bits of random per message is safe and a counter is safer, and why "the same VM image was cloned and both copies started their counter at zero" is a real outage and not a puzzle.

<!-- figure -->
```
   FOUR MODES, AND WHAT EACH ONE LEAKS

     ONE-TIME PAD    perfect secrecy. genuinely unbreakable.
                     key as long as the message -> useless
                     REUSE THE PAD: c1^c2 = m1^m2, key cancels

     AES itself      permutes 16 bytes. THAT IS ALL IT DOES.
                     not a way to encrypt a message.
                     how you use it = the MODE = where bugs live

     ECB             identical blocks -> identical ciphertext.
                     48 'A' bytes gave THREE identical blocks.
                     the penguin. leaks every repetition.

     CBC             chain each block to the previous ciphertext.
                     pattern gone. IV travels in the CLEAR.
                     plaintext = AESdec(ct) XOR previous
                       -> edit the IV, FLIP ANY BIT you choose
                       -> role=user became role=root, no key,
                          ciphertext untouched
                     needs only the FORMAT, which is documented

     AEAD            ciphertext + a 16-BYTE TAG. decryption has
     (GCM,           a THIRD outcome -- raise -- which is why
      ChaCha20-      `openssl enc` REFUSES: a filter cannot
      Poly1305)      express "tampered".
                     one flipped bit -> InvalidTag, no plaintext

   IF YOU BUILD IT YOURSELF, FOUR WAYS TO LOSE
     tag must cover the IV        (else the attack above works)
     encrypt-THEN-mac, not the reverse
     separate keys for cipher and MAC
     constant-time tag compare    (else recover it byte by byte)
     ...which is the argument for not building it yourself

   AEAD'S ONE CATASTROPHE
     REUSE A NONCE and GCM degenerates to the two-time pad --
     same hex as the top of this lesson. also leaks the tag key,
     so forgery, not just disclosure.
     nonce = Number used ONCE. no exceptions, ever.

   WHAT A CIPHER CANNOT DO
     tell you WHO. an AEAD tag proves a key holder wrote this,
       exactly as far as lesson 02 did -- and no further.
     GET YOU THE KEY. every line above assumed both ends
       already share one.                       -> lesson 04
```

**Cleanup:**

```bash
cd "${TMPDIR:-/tmp}" && rm -f rep.bin
```

> **You understand this when you can** derive from XOR why reusing a pad hands over the second
> message given the first; state how CBC decryption uses the previous block, and derive from it
> why an attacker who can edit the IV flips chosen plaintext bits without the key; explain why
> encryption is not integrity in one sentence an engineer would act on; give the failure
> associated data prevents that is *not* header tampering; and explain why nonce reuse returns you
> to this lesson's first failure.

**Which raises:** three promises are now kept, and every single experiment in all three lessons began by assuming a key was already shared. The one-time pad needed a key as long as the message and you dismissed it for exactly that reason — but AES needs a key too, and you have quietly been passing it around by writing it into both halves of the same script. On a real network there is no both-halves-of-the-same-script. There is a wire that every router in Act III can read, two parties who have never met, and no shared secret of any kind. **They must end up agreeing on a key while an eavesdropper watches every byte they exchange.** That sounds impossible — and the reason it is not is the single most surprising result in this act.

---

↑ **[Act VIII overview](README.md)** · Prev: **[A hash only certain people can compute](02-hmac.md)** · Next: **[Agreeing on a secret in public](04-key-exchange.md)** →
