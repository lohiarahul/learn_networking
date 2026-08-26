# `ltrace` — library call trace

The calls `strace` shows, one layer up: libc calls such as `getaddrinfo` rather than the syscalls underneath them

| | |
|---|---|
| **Speaks** | [`probe`](README.md) · flags |
| **Mode** | live |
| **Taught in** | [minihttp](../../../networking-fundamentals/act-1-one-machine/03-minihttp-server.md) |
| **In the lab** | ✅ `/usr/bin/ltrace` · ltrace version 0.7.3. |
| **Standing** | ⚠️ **superseded** by [`strace`](strace.md) or [`bpftrace`](bpftrace.md) — not a drop-in |
| **Blind spot** | `probe` has none worth the name — this is the only [interface](README.md) that can say which kernel function dropped your packet. It does need a running target |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## ⚠️ Prefer [`strace`](strace.md) or [`bpftrace`](bpftrace.md)

**Not a drop-in.** A different model and a different output shape, so anything built on this one gets rebuilt rather than renamed.

| instead of | type this |
|---|---|
| `ltrace ./prog` | `strace -f ./prog` |
| `ltrace -e 'malloc*' ./prog` | `bpftrace -e 'uprobe:/lib/libc.so.6:malloc { @[comm] = count(); }'` |

**What you gain.** `strace` actually runs, and covers the syscall boundary — which is where the kernel is, and therefore where every networking question lives. `bpftrace` covers userspace calls via uprobes without ptrace stopping the process at every one.

**Why it is marked superseded.** Last upstream release is 0.7.3, tagged September 2013 — and in this lab image it does not run: `ltrace -e '*' /bin/true` dies on `Assertion failed: bp->libsym == NULL`. Present is not the same as working. `strace -e trace=...` covers the syscall boundary; `bpftrace` covers userspace calls.

## What it can do

*2 commands, grouped by what you are trying to find out.*

### One layer up from syscalls

| Command | What it gives you |
|---|---|
| `ltrace <cmd>` | libc calls, so you see getaddrinfo rather than the sockets under it |
| `ltrace -e getaddrinfo <cmd>` | filter to the call you care about |

## As the course runs it

*1 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `ltrace <prog>` | like `strace` but for **library** calls (libc) rather than syscalls — one layer up | Lesson 3 — Building minihttp, the listening server |
