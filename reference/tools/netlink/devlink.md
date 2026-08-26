# `devlink` — *no documented expansion*

Hardware-level device and port config below what `ip link` can reach

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · obj-verb |
| **Mode** | mutate · live |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Below what ip link can reach

| Command | What it gives you |
|---|---|
| `devlink dev show` | the hardware devices behind the netdevs |
| `devlink port show` | physical ports and their split configuration |
| `devlink dev param show` | device-level tunables |
| `devlink monitor` | stream device events |
