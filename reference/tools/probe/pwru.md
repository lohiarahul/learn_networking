# `pwru` — "packet, where are you?"

Which **kernel function** your packet passed through, and which one dropped it — kprobes on every `skb`-taking function. Structurally impossible with `tcpdump`, and the tool Cilium support asks you to run

| | |
|---|---|
| **Speaks** | [`probe`](README.md) · flags + *filter* |
| **Mode** | live |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Standing** | 🆕 **emerging** — first released 2021, and you install it deliberately |
| **Blind spot** | `probe` has none worth the name — this is the only [interface](README.md) that can say which kernel function dropped your packet. It does need a running target |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## 🆕 New, and worth the install

**What you gain.** The one question no other interface can answer: the name of the kernel function that dropped your packet. `tcpdump` can only tell you it never arrived.

**Why it is marked emerging.** Cilium's eBPF packet tracer, first released 2021. Not packaged by any distribution and not in this lab image — you install it deliberately. It answers the one question netlink and procfs cannot: which kernel function dropped this packet.

## The flags that carry their weight

*Not the flag list — `pwru --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `--filter-dst-ip` | trace only packets for one destination. Unfiltered, the kernel's per-packet path is far too much output to read |
| `--all-kmods` | include module functions, not just built-ins — which is where the answer is when a `veth`, `vxlan` or `nf_*` module is the thing dropping it |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### Which kernel function dropped your packet

| Command | What it gives you |
|---|---|
| `pwru --filter-dst-ip 10.0.0.1` | trace one destination through every skb-taking function |
| `pwru 'tcp port 443'` | a pcap-style filter, compiled to eBPF |
| `pwru --output-tuple --all-kmods` | print the tuple at each hop, across modules |
