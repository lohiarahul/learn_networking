# `falco`

Syscall-level events *as they happen* — the runtime half that no scanner can give you

| | |
|---|---|
| **Speaks** | [`probe`](README.md) · rules + flags |
| **Mode** | live |
| **Taught in** | [seeing it happen](../../../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `probe` has none worth the name — this is the only [interface](README.md) that can say which kernel function dropped your packet. It does need a running target |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### Syscall-level events as they happen

| Command | What it gives you |
|---|---|
| `falco -r /etc/falco/falco_rules.yaml` | run with a ruleset |
| `falco -L` | list loaded rules |
| `falco --list=syscall` | which events can be matched at all |
