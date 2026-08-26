# `openssl`

Every cryptographic primitive as a separate command (`dgst`, `enc`, `genpkey`, `x509`, `verify`) **and** `s_client`, which opens a TLS connection by hand so you read the handshake instead of trusting it. The only tool here that shows you a certificate chain as the peer actually presented it

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [TLS opened](../../../networking-fundamentals/act-8-trust/06-tls-opened.md) |
| **In the lab** | ✅ `/usr/bin/openssl` · OpenSSL 3.5.4 30 Sep 2025 (Library: OpenSSL 3.5.4 30 Sep 2025) |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

> **Two interfaces.** `socket` for `s_client`; `local` for everything else (`dgst`, `genpkey`, `enc`, `x509`), which is pure computation on files.

## The flags that carry their weight

*Not the flag list — `openssl --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-servername` | send SNI. Without it a shared host answers with the *wrong certificate*, and you debug a problem you do not have |
| `-showcerts` | the whole chain the server sent, not just the leaf — where a missing intermediate becomes visible |
| `-CAfile` | verify against a specific trust store, which is how you tell "this cert is bad" from "this box does not trust it" |

## What it can do

*11 commands, grouped by what you are trying to find out.*

### Inspect a live TLS connection

| Command | What it gives you |
|---|---|
| `openssl s_client -connect example.com:443` | the handshake and the chain as the peer presented it |
| `openssl s_client -connect example.com:443 -servername example.com` | with SNI — without it you get the default vhost |
| `openssl s_client -connect <h>:443 -showcerts` | every certificate in the chain, PEM encoded |
| `openssl s_client -connect <h>:443 -tls1_2` | pin a version to test what is still accepted |

### Read a certificate

| Command | What it gives you |
|---|---|
| `openssl x509 -in cert.pem -noout -text` | everything: subject, SAN, validity, extensions |
| `openssl x509 -in cert.pem -noout -dates -subject -ext subjectAltName` | just the fields you asked for |
| `openssl verify -CAfile ca.pem cert.pem` | does this chain actually validate |

### Primitives, one command each

| Command | What it gives you |
|---|---|
| `openssl dgst -sha256 <file>` | a hash |
| `openssl dgst -sha256 -hmac <key> <file>` | a keyed hash — authentication, not just integrity |
| `openssl genpkey -algorithm ed25519 -out key.pem` | a private key |
| `openssl rand -hex 16` | cryptographically random bytes |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `openssl s_client -connect example.com:443 -servername example.com` | `s_client` = a TLS client you drive by hand; `-connect host:port`; `-servername` sets SNI, without which a shared-IP server can't know which certificate to send | Lesson 5 — TLS |
