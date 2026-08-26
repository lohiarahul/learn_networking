# `getpcaps` — get process capabilities

The capability set `capsh --print` decodes, but for a **running PID** and in one line — no need to start a process inside it

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · `getpcaps <pid>` |
| **Mode** | read-only |
| **Taught in** | [Act X diagnose](../../../networking-fundamentals/act-10-cluster-security/diagnose.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*2 commands, grouped by what you are trying to find out.*

### What capsh decodes, for a running PID

| Command | What it gives you |
|---|---|
| `getpcaps <pid>` | the decoded capability set |
| `getpcaps 1` | PID 1 in a container — usually more than you expected |
