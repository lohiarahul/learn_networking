# `iptables` — IP tables

The legacy rule syntax that most of the internet's documentation, and `kube-proxy`'s default mode, still speaks. **Run `iptables -V` first:** since 1.8 the same CLI sits over two different kernel backends and prints either `(nf_tables)` or `(legacy)`. Never mix the legacy and nft tools — both subsystems become active and the evaluation order between them is undefined

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · flags (`-t -A -m -j`) |
| **Mode** | mutate |
| **Taught in** | [iptables and NAT](../../../networking-fundamentals/act-4-one-pretends-many/03-iptables-and-nat.md) |
| **In the lab** | ✅ `/usr/sbin/iptables` · iptables v1.8.11 (nf_tables) — provided by **`xtables-nft-multi`**, the nftables-backed multi-call binary (which is the `Standing` row below, measured rather than argued) |
| **Standing** | ⚠️ **superseded** by [`nft`](nft.md) — not a drop-in |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## ⚠️ Prefer [`nft`](nft.md)

**Not a drop-in.** A different model and a different output shape, so anything built on this one gets rebuilt rather than renamed.

| instead of | type this |
|---|---|
| `iptables -S` | `nft list ruleset` |
| `iptables -t nat -L -n -v` | `nft list table ip nat` |
| `iptables -A INPUT -p tcp --dport 80 -j ACCEPT` | `nft add rule ip filter input tcp dport 80 accept` |

**What you gain.** One ruleset covering IPv4 and IPv6 together instead of two parallel binaries, atomic whole-ruleset replacement (`nft -f`) so a half-applied firewall is not a state you can reach, sets and maps as first-class objects rather than the `ipset` bolt-on, and `nft -j` for JSON.

**What will bite you in the swap.** `iptables` creates its tables and built-in chains for you; `nft` does not. On a fresh host `nft add rule ip filter input tcp dport 80 accept` answers `Could not process rule: No such file or directory` until you have run `nft add table ip filter` and `nft add chain ip filter input { type filter hook input priority 0 \; }`. Likewise `nft list table ip nat` errors rather than printing an empty table. Measured in this lab — and it is the single most common first hour of an `nft` migration.

**Read this one anyway.** Every existing cluster, every `kube-proxy` rule and nearly every runbook you will be handed is written in it — and you cannot read an `nft list ruleset` dump back into an `iptables`-shaped mental model without having had the `iptables` one first.

**Why it is marked superseded.** Not a claim about the future — measure it: `iptables -V` in this lab prints `iptables v1.8.11 (nf_tables)`. The binary is already a translation front-end onto nftables' backend, so you are running `nft` whether you meant to or not. Learn it because every existing cluster is written in it.

> **Two interfaces, depending on the build.** `netlink` on the nf_tables backend, `setsockopt` on legacy — and **`iptables -V` tells you which**. Measured: `iptables -t nat -L` opens `NETLINK_NETFILTER`, so on a current box this is an nftables front end.

## What it can do

*14 commands, grouped by what you are trying to find out.*

### Read a ruleset

| Command | What it gives you |
|---|---|
| `iptables -V` | run this FIRST: prints (nf_tables) or (legacy) — two different kernel backends |
| `iptables -t nat -L -n -v --line-numbers` | one table, numeric, with counters and rule numbers |
| `iptables -L -n -v` | the filter table |

### The five tables, and what each is for

| Command | What it gives you |
|---|---|
| `iptables -t filter …` | accept/drop — the default |
| `iptables -t nat …` | translation: PREROUTING (DNAT), POSTROUTING (SNAT/MASQUERADE) |
| `iptables -t mangle …` | rewrite packet fields, set marks |
| `iptables -t raw …` | NOTRACK — the only place to opt out of conntrack |
| `iptables -t security …` | SELinux/MAC labels |

### Write rules

| Command | What it gives you |
|---|---|
| `iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -j MASQUERADE` | the container-networking rule |
| `iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT` | -I inserts at a position; -A appends |
| `iptables -D INPUT 1` | delete by line number |
| `iptables -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT` | -m loads a match module |

### Read and restore atomically

| Command | What it gives you |
|---|---|
| `iptables-save > rules.v4` | the whole ruleset as diffable text — the only sane way to read a big one |
| `iptables-restore < rules.v4` | applied atomically; a partial ruleset is never live |

## As the course runs it

*5 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `iptables -t nat -L -n -v` | `-t nat` = which **table** (`nat` rewrites addresses, `filter` accepts/drops); `-L` = list; `-n` = numeric, no DNS; `-v` = verbose, which adds the packet and byte counters — the column that tells you whether a rule is actually being hit | Lesson 3 — iptables and NAT |
| `iptables -t filter -L -n -v --line-numbers` | `--line-numbers` gives you the index you need to delete a rule by position | Lesson 3 — iptables and NAT |
| `iptables -t nat -L POSTROUTING -n -v` | one **chain**: `POSTROUTING` is the last hook before a packet leaves, which is where source NAT has to happen | Lesson 3 — iptables and NAT |
| `iptables -t nat -L DOCKER -n` | Docker's own chain, holding the `DNAT tcp dpt:8080 to:172.17.x.x:80` that `-p` created | Lesson 3 — iptables and NAT |
| `iptables -L FORWARD -n --line-numbers` | the chain that decides whether traffic may be routed *through* this host — the rules that make container-to-outside work | Lesson 3 — iptables and NAT |
