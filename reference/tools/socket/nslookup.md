# `nslookup` — name server lookup

Nothing `dig`, `drill` or `host` don't, but it is the one present on hosts with nothing else installed

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · interactive |
| **Mode** | read-only |
| **Taught in** | [policy shapes](../../../networking-fundamentals/act-5-kubernetes/07b-policy-shapes.md) |
| **In the lab** | ✅ `/usr/bin/nslookup` · nslookup 9.20.17 |
| **Standing** | ⚠️ **superseded** by [`dig`](dig.md) — not a drop-in |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## ⚠️ Prefer [`dig`](dig.md)

**Not a drop-in.** A different model and a different output shape, so anything built on this one gets rebuilt rather than renamed.

| instead of | type this |
|---|---|
| `nslookup example.com` | `dig example.com +noall +answer` |
| `nslookup -type=MX example.com` | `dig MX example.com` |
| `nslookup example.com 8.8.8.8` | `dig @8.8.8.8 example.com` |

**What you gain.** The whole DNS message rather than a summary of it: header flags (`qr aa rd ra`), the TTL on every record, the authority and additional sections kept separate, `+trace` to walk the delegation from the root yourself, and `+dnssec` with EDNS control.

**Why it is marked superseded.** It summarises the answer and cannot show you the message. No header flags (`qr rd ra`), no TTLs, no section structure, no `+trace`, no EDNS control — none of which is a missing flag, it has no such output mode. When DNS is the thing that is broken you need the message.

## What it can do

*2 commands, grouped by what you are trying to find out.*

### The one present when nothing else is

| Command | What it gives you |
|---|---|
| `nslookup example.com` | a query |
| `nslookup example.com 10.96.0.10` | against a specific server — the CoreDNS check inside a Pod |
