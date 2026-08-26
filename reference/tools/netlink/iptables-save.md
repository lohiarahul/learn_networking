# `iptables-save`

The whole ruleset in one atomic, diffable text dump — the only sane way to read a large ruleset

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [services](../../../networking-fundamentals/act-5-kubernetes/03-services.md) |
| **In the lab** | ✅ `/usr/sbin/iptables-save` · iptables-save v1.8.11 (nf_tables) — provided by **`xtables-nft-multi`**, the nftables-backed multi-call binary (which is the `Standing` row below, measured rather than argued) |
| **Standing** | ⚠️ **superseded** by [`nft`](nft.md) — not a drop-in |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## ⚠️ Prefer [`nft`](nft.md)

**Not a drop-in.** A different model and a different output shape, so anything built on this one gets rebuilt rather than renamed.

| instead of | type this |
|---|---|
| `iptables-save` | `nft list ruleset` |
| `iptables-save -t nat` | `nft list table ip nat` |

**What you gain.** `nft list ruleset` dumps the real backend state rather than an `iptables`-shaped rendering of it, and the output is a file `nft -f` can load back atomically.

**Read this one anyway.** The `iptables-save` format is what you will be shown in bug reports and what `kube-proxy` documentation quotes, so you still need to read it.

**Why it is marked superseded.** Same binary family, same backend — `iptables-save -V` also prints `(nf_tables)`. `nft list ruleset` dumps the real thing without the translation layer.

> **Two interfaces, depending on the build.** `netlink` on the nf_tables backend, `setsockopt` on legacy — and **`iptables -V` tells you which**. Measured: `iptables -t nat -L` opens `NETLINK_NETFILTER`, so on a current box this is an nftables front end.

## What it can do

*3 commands, grouped by what you are trying to find out.*

### The whole ruleset as diffable text

| Command | What it gives you |
|---|---|
| `iptables-save` | every table at once, atomically consistent |
| `iptables-save -t nat \| grep KUBE-SVC` | how you read kube-proxy's output without going mad |
| `iptables-save > before.txt` | the before half of a diff — the honest way to see what a controller changed |
