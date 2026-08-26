# `tc` — traffic control

Queueing, rate limits, and — via `netem` — deliberately injected loss, delay, reordering and duplication. **The only way to *reproduce* a bad network**, and `netem` has no eBPF equivalent. eBPF did not replace `tc`; it replaced one thing that used to hang off it, the packet classifier. Modern eBPF datapath programs attach straight to a device's ingress and egress (an interface called TCX, since kernel 6.6) instead of hanging off one of `tc`'s queueing disciplines

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · obj-verb (qdisc/class/filter) |
| **Mode** | mutate · live |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/sbin/tc` · tc utility, iproute2-6.18.0 |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `tc --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-s` | per-qdisc statistics, including `dropped` and `overlimits` — the numbers that say whether your shaper is the thing hurting you |

## What it can do

*12 commands, grouped by what you are trying to find out.*

### See the queueing discipline

| Command | What it gives you |
|---|---|
| `tc qdisc show` | every qdisc on every device |
| `tc -s qdisc show dev <dev>` | with drop and backlog counters — where loss actually appears |
| `tc class show dev <dev>` | the class hierarchy under a classful qdisc |
| `tc filter show dev <dev>` | the classifiers, including attached eBPF programs |

### Reproduce a bad network — nothing else can do this

| Command | What it gives you |
|---|---|
| `tc qdisc add dev <dev> root netem delay 100ms 20ms` | 100ms latency with 20ms jitter |
| `tc qdisc add dev <dev> root netem loss 5%` | drop one packet in twenty |
| `tc qdisc add dev <dev> root netem reorder 25% 50%` | reorder — the one that breaks naive protocols |
| `tc qdisc add dev <dev> root netem duplicate 1%` | duplicates |
| `tc qdisc del dev <dev> root` | undo it — know this one before you run the others |

### Rate limiting

| Command | What it gives you |
|---|---|
| `tc qdisc add dev <dev> root tbf rate 1mbit burst 32kbit latency 400ms` | a token bucket |
| `tc qdisc add dev <dev> root handle 1: htb default 10` | hierarchical shaping, the classful route |

### Watch it change

| Command | What it gives you |
|---|---|
| `tc monitor` | stream qdisc and filter events |
