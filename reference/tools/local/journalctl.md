# `journalctl` — “journal control”

One unit's share of a **structured** log store, selected by field match rather than text search — and the store's own limits, which is why an empty result is a claim about the store

| | |
|---|---|
| **Speaks** | [`local`](README.md) · flags |
| **Mode** | read-only |
| **Taught in** | [what starts the kubelet](../../../networking-fundamentals/act-6-control-plane/02b-what-starts-the-kubelet.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `local` cannot tell you anything at all about your machine. These reshape input another tool produced — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `journalctl --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-u <unit>` | one unit's share of the store. A **field match against structured records**, not a text search — which is why it can separate one unit's lines from a thousand interleaved by timestamp, and `grep` on a text log cannot |
| `-n <count>` | the last *n* records. The flag `exam-prep/kubectl-speed.md` drills as `journalctl -u kubelet -n 50 --no-pager` and no lesson had shown before Act VI 02b |
| `--no-pager` | do not open an interactive pager. Required through `docker exec`, where there is no terminal for one to attach to |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### One unit's output, when nothing above it will answer

| Command | What it gives you |
|---|---|
| `journalctl -u kubelet -n 50 --no-pager` | the last fifty records for one unit |
| `journalctl -u kubelet --since '-2min' --no-pager` | a bounded window — and `-- No entries --` is a claim about the store, not about the unit |
| `journalctl --disk-usage` | how much the store holds, which bounds how far back any question can reach |
| `journalctl --file <path>` | read a journal file directly, with systemd never consulted — the measurement that puts this tool in `local` rather than `httpapi` |

## As the course runs it

*2 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `journalctl -u kubelet --since '-1min' --no-pager` | the evidence that an unmet `ConditionPathExists` is recorded as “skipped, unmet condition check” rather than as a crash — an `inactive` unit whose journal holds no failure, because nothing ran | Lesson 2b — What starts the kubelet |
| `journalctl -u kubelet -n 3 --no-pager` | introduces `-n`, the flag `exam-prep/kubectl-speed.md` drills as reflex for the moment `kubectl` stops answering | Lesson 2b — What starts the kubelet |
