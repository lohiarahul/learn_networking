# `mtr` — "Matt's traceroute" *(after Matt Kimball — widely reported, not in the project's docs)*

Continuous per-hop loss and latency, which is how you tell "one bad hop" from "the whole path is bad"

| | |
|---|---|
| **Speaks** | [`packet`](README.md) · flags |
| **Mode** | live |
| **Taught in** | **roster only** — named by the roster, run by no lesson |
| **In the lab** | ✅ `/usr/sbin/mtr` · mtr 0.96 |
| **Blind spot** | `packet` cannot tell you which process or rule was responsible. It sees bytes on a link, not the host state behind them — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `mtr --help` has that. These 2 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-T` | TCP probes, for the same reason as `traceroute -T` |
| `-c` | a bounded number of cycles, so it terminates — and per-hop loss over 100 probes is a measurement, where one traceroute is an anecdote |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### Loss per hop, continuously

| Command | What it gives you |
|---|---|
| `mtr -n <host>` | the interactive view: one line per hop, loss and latency updating |
| `mtr -n -r -c 100 <host>` | a report of 100 cycles, for pasting into a ticket |
| `mtr -n -T -P 443 <host>` | TCP mode |
