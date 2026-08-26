# `nft` — nftables — netfilter tables

One tool and one grammar for IPv4, IPv6, ARP and bridge (the `inet` family), plus the sets and maps that iptables needed `ipset` for. In-kernel since 3.13; netfilter's own wiki has called the xtables tools legacy since 2018, RHEL 10 no longer ships the legacy `ip_tables` module at all, and Docker Engine 29 has an experimental native nftables backend it intends to make the default

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · verb-obj |
| **Mode** | mutate · live |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/usr/sbin/nft` · nftables v1.1.6 (Commodore Bullmoose #7) |
| **Supersedes** | ✅ **prefer this one** over [`iptables`](iptables.md) · [`iptables-save`](iptables-save.md) |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `nft --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-a` | rule **handles**, which is the only way to delete one rule rather than reloading the ruleset |

## What it can do

*9 commands, grouped by what you are trying to find out.*

### Read everything at once

| Command | What it gives you |
|---|---|
| `nft list ruleset` | every table, chain and rule in one output — no per-table loop |
| `nft -a list ruleset` | with handles, which is how you delete a specific rule |
| `nft -j list ruleset` | JSON |

### One grammar for all families

| Command | What it gives you |
|---|---|
| `nft add table inet filter` | inet covers IPv4 and IPv6 together — the thing iptables cannot do |
| `nft add chain inet filter input '{ type filter hook input priority 0; policy drop; }'` | a base chain, hook and policy declared inline |

### Native sets and maps — no ipset needed

| Command | What it gives you |
|---|---|
| `nft add set inet filter bad '{ type ipv4_addr; flags interval; }'` | a typed set |
| `nft add element inet filter bad '{ 10.0.0.0/8, 192.168.1.1 }'` | populate it |
| `nft add rule inet filter input ip saddr @bad drop` | match the whole set in one rule |

### Watch it change

| Command | What it gives you |
|---|---|
| `nft monitor` | stream ruleset changes — see what an orchestrator is writing |
