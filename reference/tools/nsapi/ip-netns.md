# `ip netns`

Named network namespaces, created as bind mounts under `/run/netns` — which is why it cannot see Docker's

| | |
|---|---|
| **Speaks** | [`nsapi`](README.md) · obj-verb |
| **Mode** | mutate |
| **Taught in** | [namespaces](../../../networking-fundamentals/act-4-one-pretends-many/01-namespaces.md) |
| **In the lab** | ✅ `/sbin/ip` |
| **Blind spot** | `nsapi` cannot tell you what is *inside* a namespace. These move you between namespaces; they read nothing — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

> **Two interfaces.** `nsapi` to create and enter — `unshare` plus a bind mount under `/run/netns` — and `netlink` to list nsids. The bind mount is exactly why it cannot see Docker's namespaces.

## What it can do

*5 commands, grouped by what you are trying to find out.*

### Named namespaces, as bind mounts

| Command | What it gives you |
|---|---|
| `ip netns list` | namespaces under /run/netns — NOT Docker's, which are unnamed |
| `ip netns add blue` | unshare plus a bind mount; this is why the name persists |
| `ip netns exec blue ip addr` | run a command inside it |
| `ip netns exec blue bash` | get a shell inside it |
| `ls -l /proc/<pid>/ns/net` | the namespace's real identity, as an inode — the test that actually works |

## As the course runs it

*8 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `ip netns add test` | creates a named network namespace as a bind mount under `/run/netns/` — which is why `ip netns list` cannot see Docker's namespaces, which are not created this way | Lesson 1 — Namespaces |
| `ip netns exec test ip addr` | `exec <name> <cmd>` runs a command inside that namespace. Expect a down `lo` and, depending on which tunnel modules your kernel has loaded, a handful of per-namespace stubs (`tunl0`, `gre0`, `sit0`, …). What matters is what is *absent*: no addresses, no routes, no way out | Lesson 1 — Namespaces |
| `ip netns exec test ls -la /proc/self/ns/net` | **a different inode from the host's** — the whole proof, in one comparison | Lesson 1 — Namespaces |
| `ip netns exec test ping 8.8.8.8` | fails, because a namespace with no route and no device cannot reach anything. The failure is the lesson | Lesson 1 — Namespaces |
| `ip netns del test` | destroys it. opt: `ip netns list` to confirm | Lesson 1 — Namespaces |
| `ip netns exec ns1 ip link set lo up` | even loopback starts down in a fresh namespace | Lesson 2 — veth and bridge |
| `ip netns del ns2` | deleting a namespace destroys every device still in it | Lesson 2 — veth and bridge |
| `ip netns exec vx1 ping -c3 10.200.0.2` | an overlay address reached across an underlay that has never heard of it | Lesson 4 — Overlay and VXLAN |
