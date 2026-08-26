# `xxd` — hex dump / —

Reads the bytes when the text view is lying to you

| | |
|---|---|
| **Speaks** | [`local`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [hashing](../../../networking-fundamentals/act-8-trust/01-hashing.md) |
| **In the lab** | ✅ `/usr/bin/xxd` |
| **Blind spot** | `local` cannot tell you anything at all about your machine. These reshape input another tool produced — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### When the text view is lying to you

| Command | What it gives you |
|---|---|
| `xxd <file> \| head` | hex and ASCII side by side |
| `xxd -p -l 16 /dev/urandom` | plain hex, no offsets |
| `base64 -d <<< '<b64>' \| xxd` | decode then inspect — reading a Kubernetes Secret |
| `openssl x509 -in cert.pem -outform der \| xxd \| head` | the bytes behind a certificate |
