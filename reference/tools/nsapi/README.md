# `nsapi` — moving between namespaces

**What you see in `strace`:** `unshare()`, `setns()`, `clone()`, and a bind `mount()`

Four tools, and they are unusual: **they read almost nothing.** Their job is to change *which*
namespaces the calling process belongs to, so that some other tool — from any other interface — sees a
different world. This interface is the reason the same `ip addr` gives different answers in different
places.

[`ip netns`](ip-netns.md) · [`unshare`](unshare.md) ·
[`nsenter`](nsenter.md) · [`runc`](runc.md)

---

## Rule: the flag letters *are* the filenames

`/proc/<pid>/ns/` holds one entry per namespace type, and the flags of `unshare` and `nsenter` map onto
them 1:1. This table makes two tools one thing to learn:

| File in `/proc/<pid>/ns/` | Flag | Long form | Isolates |
|---|---|---|---|
| `mnt` | `-m` | `--mount` | the mount table |
| `uts` | `-u` | `--uts` | hostname and domain name |
| `ipc` | `-i` | `--ipc` | SysV IPC, POSIX message queues |
| `net` | `-n` | `--net` | interfaces, routes, netfilter, socket tables |
| `pid` | `-p` | `--pid` | process IDs |
| `user` | `-U` | `--user` | UID/GID mappings and capabilities |
| `cgroup` | `-C` | `--cgroup` | the cgroup root |
| `time` | `-T` | `--time` | boot and monotonic clock offsets |

The entries are magic symlinks whose target is a type and an inode — `net:[4026531840]`. **Two
processes share a namespace if and only if that inode matches.** That is the whole test, and it is why
this course compares `readlink /proc/self/ns/net` rather than trusting any tool's opinion.

## Why `ip netns list` shows nothing on a machine full of containers

A namespace lives as long as something references it — a running process, or a bind mount. `ip netns
add` makes the bind mount under `/run/netns/`, and **`ip netns list` is really just a directory listing
of that path.** So a namespace created any other way is completely real and completely invisible to it:

| Path | Put there by | Does `ip netns list` see it? |
|---|---|---|
| `/run/netns/<name>` | `ip netns add` | **Yes** — the only reason it works at all |
| `/var/run/docker/netns/<id>` | Docker | **No** |
| `/run/netns` or `$XDG_RUNTIME_DIR/netns` | Podman / netavark | Rootful: yes |
| varies | containerd / CRI | Sometimes |

Hence the standard trick — **run it on the Docker host, not inside the lab container**, because
`/var/run/docker/netns` lives in the host's mount namespace:

```bash
ln -s /var/run/docker/netns /var/run/netns
ip netns list
```

And the always-works alternative, needing no mount and no tool: find the pid and read
`/proc/<pid>/net/` directly, or enter with `nsenter -t <pid> -n`.

## `unshare` versus `nsenter`, in one line each

- **`unshare`** makes a *new* namespace around a *new* process. It is what `docker run` performs.
- **`nsenter`** joins an *existing* process's namespaces. It is what `docker exec` and `kubectl exec`
  perform — and the way into a container that has no shell of its own:

```bash
nsenter -t $(docker inspect -f '{{.State.Pid}}' <c>) -n tcpdump -i eth0
```

That command is worth memorising: it runs the *host's* `tcpdump` inside the container's network
namespace, so the container needs no tools at all.

---

## What `nsapi` can never tell you

**Anything about what is inside a namespace.** These tools are a door, not a window. `nsenter` will
put you somewhere; it has no opinion on what you find. Every actual reading is done by a tool from
another interface once you are through.

The corollary is the useful part: a namespace problem never shows up as an error from these tools. It
shows up as [`netlink`](../netlink/README.md) or [`procfs`](../procfs/README.md) giving an answer that is correct for a
place you did not mean to be.

## What streams here

**Nothing.** There is no event stream for namespace membership. To watch containers come and go you
want `docker events` or `kubectl get pods -w` from [`httpapi`](../httpapi/README.md).

---

Taught in: [namespaces](../../../networking-fundamentals/act-4-one-pretends-many/01-namespaces.md) ·
[everything is a file](../../../networking-fundamentals/act-1-one-machine/06-everything-is-a-file.md) ·
[the kernel says no](../../../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md)

Next: [`procfs`](../procfs/README.md), whose `/proc/net` this interface is what makes ambiguous.
