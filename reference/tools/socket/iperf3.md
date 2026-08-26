# `iperf3` — internet performance

Achievable throughput between two points, which no passive tool can tell you

| | |
|---|---|
| **Speaks** | [`socket`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/usr/bin/iperf3` · iperf 3.19.1 (cJSON 1.7.15) |
| **Blind spot** | `socket` cannot tell you *why* it failed. A socket tool reports the verdict; the cause needs another [interface](README.md) |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `iperf3 --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-u` | UDP, which measures loss and jitter. TCP throughput hides loss by retransmitting it |
| `-P` | parallel streams. One TCP stream often cannot fill a fat, high-latency link, so a single-stream number under-reports the path |
| `-R` | reverse the direction. Uplinks and downlinks are not symmetric and are not the same test |

## What it can do

*5 commands, grouped by what you are trying to find out.*

### Achievable throughput, which no passive tool can tell you

| Command | What it gives you |
|---|---|
| `iperf3 -s` | run the server side |
| `iperf3 -c <host>` | ten seconds of TCP, one stream |
| `iperf3 -c <host> -P 8` | eight parallel streams — often the only way to fill a fast link |
| `iperf3 -c <host> -u -b 100M` | UDP at a fixed rate, which is how you measure loss |
| `iperf3 -c <host> -R` | reverse direction |
