# `getent hosts` — get entries

**What the application will actually get** — it resolves the way an application does, through glibc's Name Service Switch (`/etc/nsswitch.conf`, then `/etc/hosts`, then DNS), rather than talking to a nameserver directly. The tool that resolves "`dig` works but the app can't"

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · `getent <db> <key>` |
| **Mode** | read-only |
| **Taught in** | [Act II diagnose](../../../networking-fundamentals/act-2-two-machines/diagnose.md) |
| **In the lab** | ✅ `/usr/bin/getent` |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

> **Files first.** Measured against `localhost` it opened **no socket at all** — `/etc/hosts` answered and NSS stopped there. That is the whole reason this is not a duplicate of `dig`.

## What it can do

*3 commands, grouped by what you are trying to find out.*

### What the application will actually get

| Command | What it gives you |
|---|---|
| `getent hosts example.com` | resolves the way glibc does: nsswitch.conf, then /etc/hosts, then DNS |
| `getent hosts localhost` | answered from /etc/hosts with no socket opened at all |
| `getent ahostsv4 example.com` | IPv4 only, via the same NSS path |
