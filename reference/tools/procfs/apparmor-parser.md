# `apparmor_parser`

Whether a profile loads, and in what mode — the difference between "enforcing" and "you thought it was enforcing"

| | |
|---|---|
| **Speaks** | [`procfs`](README.md) · flags |
| **Mode** | mutate |
| **Taught in** | [the kernel says no](../../../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `procfs` cannot tell you anything the kernel does not already export as a file, and it reads a *snapshot*, so a transient is invisible — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `apparmor_parser --help` has that. These 1 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-Q` | parse and check without loading. A profile that fails to compile is better found here than by the process it was meant to confine |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### Enforcing, or only pretending to

| Command | What it gives you |
|---|---|
| `apparmor_parser -r /etc/apparmor.d/<profile>` | load or reload |
| `apparmor_parser -Q /etc/apparmor.d/<profile>` | parse without loading — a syntax check |
| `cat /sys/kernel/security/apparmor/profiles` | what is loaded, and in which mode |
