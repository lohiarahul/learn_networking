# `retis`

libpcap filters compiled to eBPF and inlined at *arbitrary probe points*, correlating kernel packet-buffer (`skb`) drops, netfilter verdicts and conntrack against one packet

| | |
|---|---|
| **Speaks** | [`probe`](README.md) · verb-obj |
| **Mode** | live |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Standing** | 🆕 **emerging** — first released 2023, and you install it deliberately |
| **Blind spot** | `probe` has none worth the name — this is the only [interface](README.md) that can say which kernel function dropped your packet. It does need a running target |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## 🆕 New, and worth the install

**What you gain.** The same kernel-function-level trace as `pwru`, with a collect-then-analyse split, so you can capture on a broken node and do the reasoning somewhere else.

**Why it is marked emerging.** Red Hat's eBPF packet tracer, first released 2023, and the youngest tool on this roster. Same job as `pwru` from a different vendor, with a collect/post-process split. Two independent teams building the same tool is the signal worth reading here.

## The flags that carry their weight

*Not the flag list — `retis --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-c` | which collectors run — `skb`, `nft`, `ct`. This decides which subsystems appear in the trace at all |
| `-f` | a pcap-style filter, so the collectors only fire for the traffic you care about |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### Correlate drops, verdicts and conntrack for one packet

| Command | What it gives you |
|---|---|
| `retis collect -c skb-drop` | why packets are dropped, with the kernel's own reason code |
| `retis collect -f 'tcp port 80' -c skb,nft,ct` | one filter, probes across netfilter and conntrack |
| `retis sort` | reassemble collected events into per-packet timelines |
