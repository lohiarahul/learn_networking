# `probe` — attach to a running kernel and watch it decide

**What you see in `strace`:** `ptrace()`, `bpf()`, or `perf_event_open()`

Seven tools, and they are categorically different from every other interface here. The others *read
state* or *send traffic*. These **instrument code that is already running**, which is why they can
answer the one question nothing else can: not "what was configured" or "what was transmitted", but
**which function made the decision.**

[`strace`](strace.md) · [`ltrace`](ltrace.md) ·
[`bpftrace`](bpftrace.md) · [`bpftool`](bpftool.md) ·
[`pwru`](pwru.md) · [`retis`](retis.md) ·
[`falco`](falco.md)

---

## Two mechanisms with very different costs

They are grouped because they share a purpose, but they do not share a price, and confusing the two
gets people hurt on production boxes.

| Mechanism | Tools | Cost | Safe on a busy box? |
|---|---|---|---|
| **`ptrace`** | `strace`, `ltrace` | **stops the process on every call.** Slowdowns of 10–100× are normal | No. It can turn a working service into a timing-out one |
| **eBPF / perf** | `bpftrace`, `pwru`, `retis`, `falco`, `bpftool` | in-kernel, aggregated, single-digit-percent | Yes — this is the point of eBPF |

`bpftrace` is `strace`'s successor for exactly this reason: same questions, no stop-the-world.

## The trick that makes this interface teach you the others

Every classification in this reference was *measured* with one command shape:

```bash
strace -e trace=network ss -tan 2>&1 | grep NETLINK
strace -f -e trace=socket,openat,ioctl <any tool>
```

That is how you settle which interface any unfamiliar tool speaks, without documentation and without
trusting anyone's table — including this one. It is the most transferable thing on this page.

## What only this interface can do

```bash
pwru --filter-dst-ip 10.0.0.1     # every kernel function this packet passed, and the one that dropped it
retis collect -c skb-drop         # drops with the kernel's own reason code
bpftrace -e 'kprobe:tcp_retransmit_skb { @[comm] = count(); }'   # retransmits, by process
bpftool net show                  # which eBPF programs are attached where
bpftool cgroup tree               # the cgroup hooks — where Cilium's socket load balancing lives
```

`bpftool` is the odd one: it *inventories* eBPF rather than using it to observe. On a Cilium cluster it
is the only way to see the datapath at all, because the rules are programs and maps rather than
anything [`netlink`](../netlink/README.md) can list.

---

## What `probe` can never tell you

Almost nothing — which is the point — but it has one hard requirement the other interfaces do not:
**it needs a live target.** You cannot probe something that already finished. If the failure was a
30-millisecond event last night, this interface has nothing for you unless something was already
attached, which is exactly what [`falco`](falco.md) exists to do.

It also needs privilege (`CAP_BPF` / `CAP_SYS_ADMIN`, or `CAP_SYS_PTRACE`) and, for kprobes, kernel
symbols. In a locked-down cluster this interface may simply be unavailable — and knowing that in
advance is better than discovering it mid-incident.

## What streams here

**All of it, by construction.** Every tool on this page is live. There is no snapshot form.

---

Taught in: [minihttp](../../../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) ·
[seeing it happen](../../../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md) ·
[encryption between Pods](../../../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md)

Next: [`netlink`](../netlink/README.md), whose classification this interface is how you verify.
