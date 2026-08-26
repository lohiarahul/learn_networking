# `bpftool` — "BPF tool" *(folklore — undocumented)*

What eBPF programs and maps are loaded and where they are attached. `bpftool net show` covers xdp/tc/tcx per device; **`bpftool cgroup tree` covers the cgroup hooks, which is where Cilium's socket-level load balancing actually lives.** The inventory command for an eBPF datapath, with no substitute

| | |
|---|---|
| **Speaks** | [`probe`](README.md) · obj-verb |
| **Mode** | mutate · live |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `probe` has none worth the name — this is the only [interface](README.md) that can say which kernel function dropped your packet. It does need a running target |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### The inventory command for an eBPF datapath

| Command | What it gives you |
|---|---|
| `bpftool prog show` | every loaded program, its type and where it came from |
| `bpftool net show` | xdp, tc and tcx attachments per device |
| `bpftool cgroup tree` | the cgroup hooks — where Cilium's socket load balancing lives |
| `bpftool map show` | every map |
| `bpftool map dump id <n>` | its contents — the actual service table |
