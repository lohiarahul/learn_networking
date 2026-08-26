# `socat` — SOcket CAT

`nc` with every socket type on both sides: TLS, Unix sockets, PTYs, and bidirectional relays between any two

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · `addr1 addr2` |
| **Mode** | read-only |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/usr/bin/socat` · socat by Gerhard Rieger and contributors - see www.dest-unreach.org |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### nc, but every socket type on both sides

| Command | What it gives you |
|---|---|
| `socat TCP-LISTEN:9000,fork,reuseaddr STDOUT` | a listener that handles more than one connection |
| `socat TCP-LISTEN:8080,fork TCP:10.0.0.1:80` | a TCP relay — a port forward in one line |
| `socat UNIX-CONNECT:/var/run/docker.sock STDIO` | speak to a Unix socket by hand |
| `socat OPENSSL:example.com:443,verify=1 STDIO` | a TLS client |
| `socat TCP-LISTEN:9000 EXEC:/bin/sh` | the pattern that explains why exposing socat is dangerous |
