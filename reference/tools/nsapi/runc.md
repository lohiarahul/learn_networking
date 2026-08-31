# `runc` — run container

The OCI runtime that actually creates the namespaces and cgroups. Below every higher-level tool

| | |
|---|---|
| **Speaks** | [`nsapi`](README.md) · verb-obj |
| **Mode** | mutate |
| **Taught in** | [who does this for you](../../../networking-fundamentals/act-4-one-pretends-many/05-who-does-this-for-you.md) |
| **In the lab** | ❌ not installed in `netlab:latest` — you will meet this one outside the lab |
| **Blind spot** | `nsapi` cannot tell you what is *inside* a namespace. These move you between namespaces; they read nothing — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*3 commands, grouped by what you are trying to find out.*

### The runtime that actually makes the namespaces

| Command | What it gives you |
|---|---|
| `runc list` | containers this runtime knows about |
| `runc state <id>` | its config and PID |
| `runc spec` | generate a default config.json — the OCI contract, readable |

## As the course runs it

*3 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `runc run -d -b bundle --pid-file /work/pid.txt box` | reads `config.json` and makes the five namespaces + cgroup itself — the same primitives lessons 01-02 built by hand, called by a program instead of typed | Lesson 5 — Who does this for you |
| `runc list` | every container this `runc` invocation knows about — and only those; `docker ps` cannot see one runc started directly, because identity lives in the kernel object, not in a daemon's bookkeeping | Lesson 5 — Who does this for you |
| `runc exec box hostname` | proves UTS isolation the same way lesson 01 proved network isolation — a different answer than the shell running it | Lesson 5 — Who does this for you |
