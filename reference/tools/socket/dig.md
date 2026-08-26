# `dig` — "domain information groper" *(folklore — BIND's docs do not expand it)*

The full DNS response — flags, authority and additional sections, TTLs. Talks to the resolver directly, **skipping NSS**

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · `@server name type` + `+opts` |
| **Mode** | read-only |
| **Taught in** | [DNS](../../../networking-fundamentals/act-2-two-machines/04-dns.md) |
| **In the lab** | ✅ `/usr/bin/dig` · DiG 9.20.17 |
| **Supersedes** | ✅ **prefer this one** over [`nslookup`](nslookup.md) |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `dig --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `@<server>` | ask a *named* resolver instead of the system one. Two resolvers disagreeing is the answer to half of all DNS problems |
| `+trace` | walk the delegation from the root yourself, so you see which nameserver in the chain is actually wrong |
| `+tcp` | force TCP. A large answer truncated over UDP fails in a way that looks like nothing at all |

## What it can do

*7 commands, grouped by what you are trying to find out.*

### The full DNS answer

| Command | What it gives you |
|---|---|
| `dig example.com` | answer, authority and additional sections, with TTLs |
| `dig +short example.com` | just the data, for scripts |
| `dig @1.1.1.1 example.com` | ask a specific server, bypassing resolv.conf |
| `dig +trace example.com` | walk the delegation from the root — where a broken zone shows itself |
| `dig -x 10.0.0.1` | reverse lookup |
| `dig SRV _https._tcp.example.com` | any record type; SRV is how Kubernetes publishes ports |
| `dig +tcp +dnssec example.com` | force TCP; request DNSSEC records |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `dig +trace google.com` | `+trace` walks the delegation from the root down, one query per level. Note the syntax: `+option`, not `-flag` — `dig` is not a getopt tool | Lesson 4 — DNS |
