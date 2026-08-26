# `host`

A one-line answer, which is what you want inside a loop

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/usr/bin/host` · host 9.20.17 |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `host --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-t <type>` | the record type. The default shows A, AAAA and MX — so `TXT`, `SRV` and `NS` are simply absent unless you ask |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### One line, which is what a loop wants

| Command | What it gives you |
|---|---|
| `host example.com` | the short answer |
| `host -t MX example.com` | one record type |
| `host 10.0.0.1` | reverse |
