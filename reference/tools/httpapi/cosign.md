# `cosign`

Whether an image is signed *by a key you trust* — and the trap that any attacker can sign with theirs

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [what you shipped](../../../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `cosign --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `--key` | verify against a key you hold. Without it, verification is keyless and trusts an OIDC identity plus a public log instead — two different trust models, same subcommand |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Signed by a key you trust — and the trap

| Command | What it gives you |
|---|---|
| `cosign generate-key-pair` | a keypair |
| `cosign sign --key cosign.key <img>` | sign, which writes a signature to the registry |
| `cosign verify --key cosign.pub <img>` | verify against a key YOU chose |
| `cosign verify <img>` | the trap: verifying without pinning a key proves only that someone signed it |
