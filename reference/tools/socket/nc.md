# `nc` — netcat

A raw TCP/UDP endpoint you drive by hand — the smallest possible client or server

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [the TCP handshake](../../../networking-fundamentals/act-3-the-internet/01-tcp-handshake.md) |
| **In the lab** | ✅ `/usr/bin/nc` |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `nc --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-l` | listen instead of connect. Same binary, opposite end of the conversation |
| `-u` | UDP instead of TCP — no handshake, so "it connected" stops meaning anything |
| `-z` | scan without sending data: report whether the port opens, then stop |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### The smallest possible client or server

| Command | What it gives you |
|---|---|
| `nc -l -p 9000` | listen on a port and print what arrives |
| `nc 10.0.0.1 9000` | connect and type at it |
| `nc -z -v -w 2 <host> 443` | just test the port, with a timeout — the reachability one-liner |
| `nc -u <host> 53` | UDP |
| `nc -l -p 9000 > out.bin` | receive a file; the sender redirects in |

## As the course runs it

*5 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `nc 127.0.0.1 8080` | `nc` (*netcat*) opens a raw TCP connection and, with nothing typed, just holds it open — so it shows as `ESTAB`. Run with `&` to keep your shell | Lesson 5b — TCP states and the SYN scan |
| `nc -u -l 9999` | `-u` = UDP; `-l` = listen. There is no handshake, so this "connection" is a fiction | Lesson 3 — ICMP, UDP, and TTL |
| `nc -l 8080` | listen. opt: `nc -l -k 8080` to keep listening after the first client disconnects | Lesson 1 — The three-way handshake |
| `nc 127.0.0.1 8080` | connect. Between these two commands, the whole handshake happens | Lesson 1 — The three-way handshake |
| `nc -l 8080 \\| (sleep 30; cat)` | listen but **don't read for 30 seconds**. The subshell is what makes the receive buffer fill, so you can watch the window close | Lesson 3 — TCP and reliability |
