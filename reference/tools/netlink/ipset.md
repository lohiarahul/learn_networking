# `ipset` — IP set

Hash sets of addresses/ports that iptables can match in one step instead of rule-by-rule. Now largely historical: nftables has native sets and maps, and `ipset` is unmaintained and slated for removal on RHEL

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/usr/sbin/ipset` · ipset v7.24, protocol version: 7 |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Sets iptables can match in one step

| Command | What it gives you |
|---|---|
| `ipset create bad hash:ip` | a hash set of addresses |
| `ipset add bad 10.0.0.1` | populate |
| `ipset list bad` | read it back |
| `iptables -A INPUT -m set --match-set bad src -j DROP` | one rule instead of thousands |
