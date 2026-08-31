# `systemctl` — “system control”

What a service *is* rather than whether it is up: the unit file merged from its drop-in stack, the restart policy that decides whether a crash returns, and the cgroup the process was placed in

| | |
|---|---|
| **Speaks** | [`httpapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [what starts the kubelet](../../../networking-fundamentals/act-6-control-plane/02b-what-starts-the-kubelet.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `httpapi` cannot tell you what the kernel actually did. Every one of these reports *intent*, and Acts V–X exist because intent and mechanism diverge |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `systemctl --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `cat <unit>` | the unit's **definition, merged from disk** — base file plus every drop-in, each path printed as a comment. The only honest way to read a unit |
| `show -p <prop>` | one property of the definition **currently in memory**. It differs from `cat` exactly when somebody edited a file and did not `daemon-reload`, which is the bug |
| `is-active <unit>` | one word and an exit code. `3` means not running — the useful check, because `restart` exits **0** even when a condition refused to let the unit run at all |

## What it can do

*7 commands, grouped by what you are trying to find out.*

### What a service is, and what will happen to it

| Command | What it gives you |
|---|---|
| `systemctl cat <unit>` | the file, plus its drop-in stack in merge order |
| `systemctl show <unit> -p Restart -p ConditionResult -p Result` | why it is in the state it is in — `ConditionResult=no` with `Result=success` is a unit that *declined*, not one that failed |
| `systemctl show <unit> -p FragmentPath -p DropInPaths` | every file that contributed to the definition |
| `systemctl is-active <unit>` | one word, and an exit code worth reading: `3` is not-running. Check this rather than `restart`'s status, because `restart` exits 0 even when a condition stopped the unit from running |
| `systemctl daemon-reload` | re-read the files from disk. Without it a `restart` succeeds and runs the old definition |

### What it is using, which is a cgroup read in disguise

| Command | What it gives you |
|---|---|
| `systemctl show <unit> -p CPUUsageNSec -p MemoryCurrent` | the same integers as `cpu.stat` and `memory.current` in the unit's own cgroup — measured identical, digit for digit |
| `systemctl status <unit>` | state, drop-in stack, main PID and the cgroup path, on one screen |

## As the course runs it

*3 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `systemctl cat kubelet` | the whole unit — `ConditionPathExists`, the `Restart=`/`RestartSec=` trio, `Slice=`, and both drop-ins in merge order, including kubeadm's `ExecStart=`-clears-then-resets pattern | Lesson 2b — What starts the kubelet |
| `systemctl show kubelet -p CPUUsageNSec -p MemoryCurrent` | returns the same integers as the unit's `cpu.stat` and `memory.current`, proving `systemctl show` is a formatted read of Act IV's cgroup files rather than a monitoring system of its own | Lesson 2b — What starts the kubelet |
| `systemctl daemon-reload` | earned rather than pasted: the restart before it succeeds, exits 0, warns only on stderr, and runs the old configuration — with the new drop-in absent from `DropInPaths` | Lesson 2b — What starts the kubelet |
