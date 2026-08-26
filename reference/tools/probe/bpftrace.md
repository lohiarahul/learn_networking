# `bpftrace` — BPF trace

Kernel and userspace probes at near-zero overhead, on a live production box, without stopping anything. `strace`'s successor

| | |
|---|---|
| **Speaks** | [`probe`](README.md) · its own language |
| **Mode** | live |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Supersedes** | ✅ **prefer this one** over [`ltrace`](ltrace.md) |
| **Blind spot** | `probe` has none worth the name — this is the only [interface](README.md) that can say which kernel function dropped your packet. It does need a running target |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `bpftrace --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-l` | list the probes this kernel actually exposes. The available tracepoints are a property of the running kernel, so this is discovery, not documentation |
| `-e` | the program itself, inline. The whole tool is this flag |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Probes on a live box, at near-zero cost

| Command | What it gives you |
|---|---|
| `bpftrace -l 'tracepoint:*'` | list every available probe |
| `bpftrace -e 'tracepoint:syscalls:sys_enter_connect { printf("%s\n", comm); }'` | who is calling connect |
| `bpftrace -e 'kprobe:tcp_retransmit_skb { @[comm] = count(); }'` | count retransmits by process |
| `bpftrace -e 'kretprobe:inet_csk_accept { @ = hist(retval); }'` | a histogram, aggregated in-kernel |
