# `nmap` — network mapper

What a *scanner* sees, including the half-open SYN scan that never completes a handshake so your application never logs it

| | |
|---|---|
| **Speaks** | [`packet`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [TCP states and the SYN scan](../../../networking-fundamentals/act-1-one-machine/05b-tcp-states-and-the-syn-scan.md) |
| **In the lab** | ✅ `/usr/bin/nmap` · Nmap version 7.98 ( https://nmap.org ) |
| **Blind spot** | `packet` cannot tell you which process or rule was responsible. It sees bytes on a link, not the host state behind them — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

> **Two interfaces, depending on the flag.** `packet` for `-sS`, the half-open scan; `socket` for the `-sT` default, which is an ordinary `connect()` your application logs.

## The flags that carry their weight

*Not the flag list — `nmap --help` has that. These 4 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-sS` | half-open SYN scan: raw packets, never a full handshake, so the target application logs nothing. Needs root, and is the `packet` half of this tool |
| `-sT` | an ordinary `connect()` — no privileges needed, and it *does* appear in the application's log. The default when you are not root |
| `-Pn` | skip host discovery. Without it a host that ignores pings is written off as down and its ports never get scanned |
| `-p-` | all 65535 ports. The default is a top-1000 list, so anything on an unusual port is invisible |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### What a scanner sees

| Command | What it gives you |
|---|---|
| `nmap -sT -p- <host>` | full TCP connect scan — your application logs every one |
| `nmap -sS -p 1-1000 <host>` | half-open SYN scan: never completes the handshake, so nothing logs it |
| `nmap -sU -p 53,123 <host>` | UDP, which is slow and inference-based |
| `nmap -sV <host>` | service and version detection from banners |
| `nmap -Pn -n <host>` | skip host discovery and DNS — the flags that matter inside a cluster |

## As the course runs it

*3 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `nmap -sS -p 8080 127.0.0.1` | `nmap` (*network mapper*); `-sS` = SYN ("stealth") scan — send SYN, read the reply, send RST instead of ACK. Stops at `SYN_RECV`, so `accept()` never fires and the application never sees it. `-p` = ports. Needs root | Lesson 5b — TCP states and the SYN scan |
| `nmap -sT -p 8080 127.0.0.1` | `-sT` = connect scan — completes the handshake, so the app *does* see it. opt: `-p 1-1024` a range, `-Pn` skip the host-up probe | Lesson 5b — TCP states and the SYN scan |
| `nmap --script broadcast-dhcp-discover -e eth0` | `--script` runs an NSE script; this one broadcasts a DHCP DISCOVER; `-e eth0` = out which interface. Shows the offer without accepting it | Lesson 3c — DHCP |
