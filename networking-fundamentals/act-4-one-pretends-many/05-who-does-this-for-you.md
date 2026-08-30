# Who does this for you

You have built a container by hand: a network namespace, a cgroup, a veth pair into a bridge, a NAT
rule, and — in the last lesson — a tunnel so two of these private networks can share one wire. Every
step was a command you typed and a file you could read afterward. Nobody has yet run `docker run`.

That silence was deliberate, and it ends here. `docker run` did not invent any of the four primitives
you just built — it called something else, which called something else, which made the exact same
system calls you made by hand. This lesson finds that chain and runs the bottom of it yourself, so the
rest of the course stops being a product you trust and becomes a mechanism you recognise.

### The problem `docker run` actually solves

Namespaces, cgroups, and a root filesystem are kernel features with no shared shape. `unshare` takes
flags; `cgroup.procs` is a file you write a PID into; a root filesystem is just a directory you `chroot`
or `pivot_root` into. Nothing forces two container tools to agree on how a container is *described* —
which means an image built for one tool would need a rewrite to run on another.

**The fix was a specification, not a program.** The **OCI Runtime Specification** defines exactly one
JSON document — `config.json` — that names every namespace a container needs, its cgroup limits, its
root filesystem, and the command to run. Any tool that can read that document and produce the
namespaces, cgroup and root filesystem it describes is a conforming **OCI runtime**. `runc` is the
reference implementation: a single static binary, no daemon, whose entire job is "read `config.json`,
call the kernel APIs you already know, exec the process." You have already met its name once, as a
promissory note — [Act X's seccomp lesson](../act-10-cluster-security/02-the-kernel-says-no.md) showed
you a Kubernetes Pod dying with `runc create failed: ... fstatfs ... operation not permitted`, and its
own tool page admits `runc` is "not installed in `netlab:latest` — you will meet this one outside the
lab." This is outside the lab.

**Predict first —** `config.json` has to describe *something* that creates isolation. Given what you
built in lessons 01–02, which JSON key do you expect to hold the list of namespaces a container gets,
and what do you expect its values to look like — flags, like `unshare`'s command line, or names, like
the ones you read out of `/proc/self/ns/`?

### Get the tools, and a real filesystem to run

Your netshoot lab already runs `--privileged --network host` — the flag Act X's lesson 01 will later
explain in full, already doing its job unexamined since Act II. That is enough root to run a container
runtime directly. Nothing here needs a new container or a new flag, only new binaries inside the one
you already have:

```bash
apk add --no-cache runc containerd containerd-ctr skopeo umoci jq
```

`runc` needs a root filesystem to point at — an unpacked image, not a `.tar` of layers. `skopeo` and
`umoci` get you there without Docker: `skopeo` copies an image out of a registry into the **OCI Image
Layout** (the on-disk form of the layers Act I's [container filesystem lesson](../act-1-one-machine/06b-the-container-filesystem.md)
described), and `umoci` unpacks that layout into a **bundle** — a root filesystem plus the `config.json`
that describes it.

```bash
mkdir /work && cd /work
skopeo copy docker://alpine:latest oci:alpine-oci:latest
umoci unpack --image alpine-oci:latest bundle
```

```
Copying config sha256:1991bd789d7184290c3cce84fd6af068b8b745e9bddf178661ce7f5ecf68135c
Writing manifest to image destination
```

`ls bundle` shows two things: `rootfs`, an ordinary directory tree — the same flattened image layers
Act I 06b read through `overlay`, just not overlaid here — and `config.json`, the document you
predicted a moment ago. Read the field you guessed at:

```bash
jq '.linux.namespaces' bundle/config.json
```

```json
[
  { "type": "pid" },
  { "type": "network" },
  { "type": "ipc" },
  { "type": "uts" },
  { "type": "mount" }
]
```

Names, not flags — and they are the same five words `unshare --help` uses. `config.json` is not a
new vocabulary. It is the vocabulary you already own, serialised.

### Run it, and check the identity the way you already know how

Point `config.json` at a process that outlives one command, then run the bundle:

```bash
jq '.process.terminal=false | .process.args=["/bin/sleep","300"]' bundle/config.json \
  > /tmp/c.json && mv /tmp/c.json bundle/config.json
runc run -d -b bundle --pid-file /work/pid.txt box
```

`runc` just did, in one call, everything lessons 01–02 did by hand: `unshare` the five namespaces,
enter the cgroup, `pivot_root` into `rootfs`, and exec `/bin/sleep`. Don't take that on faith — you
already have the tool that proves a namespace's identity. It's an inode, and you read it the same way
you read it in [lesson 01](01-namespaces.md):

```bash
PID=$(cat /work/pid.txt)
ls -la /proc/$PID/ns/net
ls -la /proc/self/ns/net
```

```
lrwxrwxrwx  1 root root 0 Aug 30 04:09 /proc/62/ns/net -> net:[4026532571]
lrwxrwxrwx  1 root root 0 Aug 30 04:09 /proc/self/ns/net -> net:[4026531833]
```

Two different inodes: `runc`'s container has a network namespace of its own, exactly as unshareable
from this shell as the one you built by hand. And the cgroup:

```bash
cat /proc/$PID/cgroup
```

```
0::/box
```

A leaf named after the container id you gave `runc run` — the same `cgroup.procs` mechanism from
[lesson 01b](01b-cgroups.md), just written by a program instead of your fingers. `runc exec box hostname`
returns a hostname that is not this shell's — the UTS namespace, isolated the same way.

**Predict first —** `runc list` shows every container this `runc` invocation knows about. `docker ps`
shows every container this Docker daemon knows about. If you started a container with `runc` directly
and then ran `docker ps`, would Docker's list include it? What does your answer say about where a
container's *identity* actually lives — in a kernel object, or in some tool's bookkeeping?

It would not. `docker ps` reads Docker's own state, not the kernel's. The container you just built is
real — a live network namespace with a real inode, a real cgroup, a real isolated process — and it is
invisible to a tool that never created it. **A container is not a thing a tool tracks. It is a thing
the kernel holds**, real whether or not anything is watching, and this is the fact every later
"where did my container go" debugging session eventually comes back to.

### Where `docker run` sits in this chain

`docker run` does not talk to `runc` directly. It talks to the Docker daemon (`dockerd`), which talks
to **`containerd`** — a small daemon whose only job is managing the lifecycle of the OCI runtime calls
underneath it — which in turn calls `runc`. `containerd` ships its own client, `ctr`, and you can watch
it do the same pull-and-run you just did by hand, one layer up:

```bash
containerd &
ctr images pull docker.io/library/alpine:latest
ctr run -d docker.io/library/alpine:latest box2 sleep 300
ctr task ls
```

```
TASK    PID    STATUS
box2    168    RUNNING
```

Read `ps -ef` in this shell right now and you will find `containerd-shim` sitting between `containerd`
and the `sleep` process — one shim per running container, the thing that keeps a container alive even
if `containerd` itself restarts. That shim execs `runc` under the hood, using the exact `create` /
`start` calls you just ran by hand.

So the full chain, top to bottom, is: `docker run` → `dockerd` → `containerd` → `containerd-shim` →
`runc` → the kernel APIs you have owned since lesson 01. Four programs, and at the bottom of every one
of them, the same five namespaces and the same cgroup leaf you have now built three different ways —
by hand, through `runc`, and through `containerd` — and read the same way each time.

> **You understand this when you can** point to the field in `config.json` that lists a container's
> namespaces and say why its values are names rather than flags, explain why `docker ps` cannot see a
> container `runc` started directly, and name the four programs between `docker run` and the kernel
> call that actually creates a namespace.

**Kubernetes sees this as** — a promise, not an implementation detail. Every conforming OCI runtime
reads the same `config.json` shape, so Kubernetes never has to know whether the machine underneath is
running `runc`, `crun`, or something stranger — it only has to know the contract was honoured. What
decides *which* runtime a node uses, and how a request to run a Pod actually becomes a call into this
chain, is the next layer up, and it has a name of its own: the **Container Runtime Interface**.

---

← Prev: **[Overlay and VXLAN](04-overlay-vxlan.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Test yourself](test-yourself.md)** →
