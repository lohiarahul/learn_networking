# `bridge`

A bridge's forwarding database (`fdb`), its VLAN filtering table, and per-port state. `ip` creates bridges; only this inspects them

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · obj-verb |
| **Mode** | mutate · live |
| **Taught in** | [veth and bridge](../../../networking-fundamentals/act-4-one-pretends-many/02-veth-and-bridge.md) |
| **In the lab** | ✅ `/sbin/bridge` |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*8 commands, grouped by what you are trying to find out.*

### The forwarding database

| Command | What it gives you |
|---|---|
| `bridge fdb show` | MAC to port — what the bridge has learned |
| `bridge fdb show br br0` | one bridge only |
| `bridge fdb add <mac> dev <port> master` | a static entry |

### Ports and their state

| Command | What it gives you |
|---|---|
| `bridge link show` | per-port state, STP role, and which bridge each belongs to |
| `bridge link set dev <port> learning off` | stop learning on one port |

### VLAN filtering

| Command | What it gives you |
|---|---|
| `bridge vlan show` | the per-port VLAN table — invisible to ip |
| `bridge vlan add dev <port> vid 10 pvid untagged` | put a port in a VLAN |

### Watch it change

| Command | What it gives you |
|---|---|
| `bridge monitor` | stream fdb and port events |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `bridge fdb show br br0` | the **forwarding database**: which MAC was last seen on which port. `ip` can create a bridge; only `bridge` can show you this | Lesson 2 — veth and bridge |
