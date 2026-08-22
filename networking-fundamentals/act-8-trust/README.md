# Act VIII — Trust on an untrusted wire

Five acts ago you were handed a lock and told, in as many words, not to look inside it:

> *"Notice what you just did: you used the lock, read its label, and trusted it — but you never looked inside. What is a 'cipher suite' actually doing? How does `TLS_AES_256_GCM_SHA384` turn a wire that any router can read into a secret only two endpoints share, when they've never met and the whole handshake crossed the network in the clear? How can a signature prove a stranger's identity?"*

That was [the TLS lesson](../act-3-the-internet/05-tls.md), and it named the hole it was leaving. This is the act that fills it.

You have not been idle in the meantime, and it has not been wasted. You have driven TLS, terminated it at an Ingress, read a certificate chain with `openssl s_client`, found a private key sitting in a Secret, and watched a cluster mint certificates for its own components. Every one of those was a *use* of something you could not yet explain. **The question this act answers is not "what is cryptography" but "what exactly was I trusting?"**

## The idea that holds the act together

Here is the move that makes the whole subject tractable, and almost nothing teaches it first.

**Cryptography is not one thing. It is four separate promises, and every real protocol is a specific stack of them.** Confuse two and you build something that looks secure and is not — which is not a hypothetical, it is the single most common cryptographic failure in production software.

(Four promises, and you will build *five* mechanisms to keep them. Which one is the odd one out, and why it needs a mechanism of its own, is the hinge the second half of the act turns on.)

```
   PROMISE                      "did this change?"
   MECHANISM                    a HASH                          lesson 01
   what it does NOT give you    any protection against someone
                                who can change the hash too

   PROMISE                      "who says so?" (shared secret)
   MECHANISM                    an HMAC                          lesson 02
   what it does NOT give you    secrecy. an HMAC hides nothing.
                                and both parties can forge it.

   PROMISE                      "can anyone read this?"
   MECHANISM                    a CIPHER, and then AEAD           lesson 03
   what it does NOT give you    integrity. and the gap is not
                                theoretical -- you will use it

   PROMISE                      "how do two strangers agree on a
                                key, in public?"
   MECHANISM                    DIFFIE-HELLMAN                    lesson 04
   what it does NOT give you    any idea WHO you agreed with

   PROMISE                      "who says so?" (no shared secret)
   MECHANISM                    a SIGNATURE, then a CERTIFICATE   lesson 05
                                and a chain to something you
                                already trust
   what it does NOT give you    a guarantee the holder is honest,
                                or that the certificate is still valid
```

Read the right-hand column downwards and you have the plot. Each lesson's mechanism keeps one promise and leaves a specific hole; the next lesson exists because of that hole. By lesson 06 the stack is complete, and `TLS_AES_256_GCM_SHA384` stops being a magic string and becomes a *sentence naming which mechanism does which job* — which is exactly what it is.

## The one claim to hold onto all act

Nothing in this act is impossible to break. **Everything is merely infeasible, and "infeasible" is a number.**

That is not a caveat, it is the subject. Every guarantee here reduces to "an attacker would have to perform roughly 2^n operations," and every interesting failure in the history of cryptography has been someone discovering that the real n was smaller than advertised. So the habit this act builds is arithmetic rather than faith: when something claims 256 bits of security, the useful question is *256 bits against which attacker* — and lesson 01 finds, in one line of arithmetic, that the honest answer sometimes has to be renegotiated downwards.

You will break one thing yourself, with two commands, on your own machine.

## The lab for this act

**No cluster.** For the first time since Act IV, nothing here needs `kind`, `kubectl` or a container. Everything runs on your own machine with tools you already have:

```bash
openssl version                 # 3.x; the output format changed at 3.0, and it matters below
printf 'x' | openssl dgst -sha256
xxd -v | head -1
```

If `openssl` is missing: `brew install openssl` on macOS, or it is already there on any Linux. Two notes that will save you confusion:

- **OpenSSL 3.x prints `SHA2-256(file)=` where 1.x printed `SHA256(file)=`**, and likewise `HMAC-SHA2-256`. This act shows 3.x output. If yours says `SHA256`, nothing is wrong.
- `sha256sum` and `md5sum` exist on Linux and are *not* installed on macOS by default. Where a lesson needs them it uses `openssl dgst` or `shasum`, which are everywhere.
- **macOS's `/usr/bin/openssl` is LibreSSL, not OpenSSL**, even though it reports a version starting with 3 — and this one is not cosmetic. Lessons 01–03 work under it; **lessons 04, 05, 06 and the drills do not**, because LibreSSL has no `X25519` or `ED25519` in `genpkey`, no `-verify_hostname`, and no `-not_before`. So `brew install openssl` is a hard prerequisite for the second half. Check with `openssl version` — you want the words `OpenSSL 3.x`, not `LibreSSL`:
  - **≥ 3.4** for the certificate-expiry experiment in lesson 05.
  - **≥ 3.5** for one line of lesson 06 that is the most interesting output in the act. On an older 3.x that lesson still works and says so.
- One block in lesson 03 needs the Python `cryptography` package — the only third-party dependency in the act. That lesson checks for it and gives you a throwaway virtual environment if you need one.

This is a gentler act than the last two in one way and harsher in another. Nothing you do can break a cluster. But the experiments are **arithmetic you have to actually do**, and skipping the arithmetic leaves you with vocabulary instead of understanding — which is precisely the state you were in at the end of Act III.

## The lessons — read in this order

1. **[A function that destroys information on purpose](01-hashing.md)** — why "did this change?" is answerable without comparing anything, and how to break MD5 by hand in two commands.
2. **[A hash only certain people can compute](02-hmac.md)** — forge a signed API request without the key, then derive HMAC as the shape that stops you.
3. **[Unreadable is not the same as unchangeable](03-ciphers.md)** — turn `role=user` into `role=root` inside AES-CBC without the key, then build the missing half out of lesson 02.
4. **[Agreeing on a secret in public](04-key-exchange.md)** — why pre-shared keys were a dead end, why that was not a tautology, and the one thing a key exchange can never tell you.
5. **[A claim someone else vouched for](05-certificates.md)** — be a certificate authority for ten minutes, then find out that the same file verifies or fails depending only on a list you chose.
6. **[The lock, opened](06-tls-opened.md)** — the capstone. Nothing new is introduced; a real TLS 1.3 handshake is narrated against a CA you built, and `TLS_AES_256_GCM_SHA384` becomes a sentence.

Then: **[test yourself](test-yourself.md)** (23 questions) · **[diagnose it](diagnose.md)** (6 drills) · **[in the wild](in-the-wild.md)**.

## What breaks here

Three shapes, and unlike the previous two acts, none of them announce themselves.

**A mechanism keeping the wrong promise.** Encryption is not integrity. A hash is not authentication. Both of those sound like pedantry, and they read completely differently once you have performed the attack that separates them — which is lesson 03's job, and is the reason the table above spends a line on what each mechanism does *not* do. The rule underneath: you can never patch a missing promise with a mechanism that keeps a different one.

**A number that turned out to be smaller.** Every guarantee here is a work factor, and work factors erode — from cryptanalysis, from faster hardware, and from a birthday bound that quietly halves your bits the moment your problem changes from "find *this* collision" to "find *any* collision." MD5 and SHA-1 were not broken by anyone being wrong about the mathematics. They were broken by the numbers moving.

**A key that outlived its safety.** Nothing in cryptography expires on its own. A key is a file, a certificate is a document with a date on it, and neither of them stops working the day it should. Act III noticed this and asked what watches the clock; Act VI showed you a cluster doing it. This act explains why the answer cannot be "nothing."

> **The question to carry forward:** every lesson here ends with a mechanism that works and a hole it cannot fill. So when you meet a security claim anywhere — in a protocol, a cloud service, a code review — the useful question is not "is this encrypted?" It is: **which of the four promises is this making, and which one is everybody assuming it makes?**
