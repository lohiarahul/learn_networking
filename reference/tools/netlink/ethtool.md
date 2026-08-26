# `ethtool` — "ethernet tool" *(folklore — undocumented)*

The NIC's own truth: link speed, ring sizes, offloads (`-k`), and per-queue hardware counters (`-S`). Explains why `tcpdump` shows a 64 KB "packet" on a 1500-byte link

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · flags |
| **Mode** | mutate |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/usr/sbin/ethtool` · ethtool version 6.15 |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `ethtool --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-i` | the driver and firmware behind the interface. A `virtio_net` and an `ixgbe` fail in different ways |
| `-k` | which offloads are on. `gro`/`tso` on is why `tcpdump` shows you a 64KB "packet" that never existed on the wire |
| `-S` | the NIC's own counters, straight off the hardware — drops the kernel never saw and so never reported |

## What it can do

*7 commands, grouped by what you are trying to find out.*

### What the NIC really is

| Command | What it gives you |
|---|---|
| `ethtool <dev>` | negotiated speed, duplex, link detected — the physical truth |
| `ethtool -i <dev>` | driver and firmware version |

### Offloads — why tcpdump lies about packet size

| Command | What it gives you |
|---|---|
| `ethtool -k <dev>` | every offload feature and whether it is on |
| `ethtool -K <dev> tso off gro off` | turn them off, and captures show 1500-byte packets again |

### Hardware counters and queues

| Command | What it gives you |
|---|---|
| `ethtool -S <dev>` | per-queue drops and errors the kernel counters do not show |
| `ethtool -g <dev>` | ring buffer sizes — undersized rings appear as rx_no_buffer |
| `ethtool -l <dev>` | queue counts |
