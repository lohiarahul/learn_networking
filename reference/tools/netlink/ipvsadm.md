# `ipvsadm` — IP virtual server admin

The IPVS connection and destination tables (`/proc/net/ip_vs`, `ip_vs_conn`) when `kube-proxy` runs in IPVS mode — still the right way to read a cluster that inherited it. Note the split: **IPVS in Linux is not deprecated; `kube-proxy`'s IPVS *mode* is** — deprecated in Kubernetes 1.35, with removal targeted at 1.43. `kube-proxy`'s nftables mode went GA in 1.33, though iptables remains the default

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · flags |
| **Mode** | mutate |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/usr/sbin/ipvsadm` · modprobe: can't change directory to '/lib/modules': No such file or directory |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `ipvsadm --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-c` | the *connection* table rather than the service table — which real backend each client actually landed on |
| `--stats` | per-service packet and byte counters, which is how you see one backend taking nothing |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### The IPVS tables

| Command | What it gives you |
|---|---|
| `ipvsadm -L -n` | virtual services and their real servers, with weights |
| `ipvsadm -L -n --stats` | per-service packet and byte counters |
| `ipvsadm -l -n -c` | the live connection table — which client is pinned to which backend |
| `cat /proc/net/ip_vs_conn` | the same table, as a file |
