# `drill`

The full DNS response like `dig`, but DNSSEC-aware — and it ships in `netshoot`, where `dig` sometimes doesn't

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [Act IV in the wild](../../../networking-fundamentals/act-4-one-pretends-many/in-the-wild.md) |
| **In the lab** | ✅ `/usr/bin/drill` |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `drill --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-S` | chase and verify the DNSSEC signature chain, which is the reason to reach for this over `dig` |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### DNSSEC-aware, and present in netshoot

| Command | What it gives you |
|---|---|
| `drill example.com` | a normal query |
| `drill -S example.com` | chase and verify the DNSSEC chain |
| `drill @1.1.1.1 example.com A` | a specific server and type |
