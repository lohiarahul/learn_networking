# Derive it — commands you were never shown

Every other page here is a lookup. This one is the opposite: each drill gives you a **goal** and
withholds the command, and your job is to build it from [the grammar](01-the-grammar.md) and
[the state map](02-the-state-map.md) rather than recall it.

That is the whole point. The course's own audit counts about 660 of its command blocks as *"type the
command shown"* — which is fine, because each one is the measurement half of a prediction. But nothing
in the acts ever asks you to **produce** a command, and producing one is a different skill: it is the
one that still works when the tool has a flag you have never seen, or when the thing you need was
invented after you learned.

**How to work these.** Say or type your answer *before* opening the reveal. A wrong attempt followed by
the right answer beats a confident skim, and it beats reading the answer first by a wide margin — the
attempt is what makes the second encounter stick. Grading yourself honestly matters more than being
right: on the site, a "not yet" brings the drill back tomorrow and a "got it" holds it for ten days.

> **Where:** these run inside the lab container, and none of them need a working network:
>
> ```bash
> docker run --rm -it --privileged --network host --pid host --name lab nicolaka/netshoot
> ```
>
> Two notes on that command line, both of which the drills below depend on:
>
> - **`--pid host` is new here** and the namespace drills need it. Without it, `/proc` shows only the
>   container's own processes, so `nsenter -t <pid>` cannot find anything to enter and the exercise
>   cannot be performed.
> - **`--network host` means there is no separate container network to play with** — you are in the
>   host's. Anything you *write* in Ladder 2 lands on the real machine. The drills say so where it
>   matters.
>
> Several drills ask you to *check your own answer* with `ip <object> help` before you run anything. Do
> that — and note it writes to stderr, so it is `ip neigh help 2>&1 | grep …`. Confirming a guess against
> the tool is the habit this page is really trying to build.

---

## Ladder 1 — Derive the command

Every answer below is buildable from three facts: `ip` is `OBJECT VERB`, the global options compose with
any object, and `ip <object> help` will confirm it.

> **Check yourself —** You want one line per interface, addresses only, IPv4 only, in a tabular form you
> can read at a glance. You have never been shown this combination. Build it.

<details>
<summary>Answer</summary>

```bash
ip -4 -br addr
```

Three independent pieces, each from the options table: `-4` restricts the family, `-br` is
`-brief` ("Print only basic information in a tabular format"), and `addr` is the object with `show`
implied. None of them know about each other, which is what "orthogonal" means — `ip -6 -br link` and
`ip -4 -br route` are equally valid and you did not have to learn them separately.

</details>

> **Check yourself —** You want the neighbour table as JSON, so a script can read a field instead of
> guessing at column positions. What is the command, and what would you pipe it into?

<details>
<summary>Answer</summary>

```bash
ip -j neigh show | jq .
```

`-j` is `-json`, and it composes with any object. This is the habit worth forming: the moment you find
yourself writing `awk '{print $5}'` against `ip` output, `-j` plus `jq` removes a whole class of bug —
column order is an implementation detail, a field name is a contract.

`ip -j -p neigh` also works; `-p` pretty-prints without needing `jq` at all.

</details>

> **Check yourself —** A device's neighbour entries are stale and you want to force re-resolution — but
> only for that one device, not the whole machine. And separately: how would you have checked that the
> verb you want even exists?

<details>
<summary>Answer</summary>

```bash
ip neigh flush dev eth0
```

`flush` is in the common verb set; `dev <name>` is the standard way `ip` scopes an operation to one
device. And the check is:

```bash
ip neigh help
```

which prints every verb and argument that object accepts. One second, works offline, and cannot be out
of date the way a cheat sheet can.

</details>

> **Check yourself —** You want to see only the routes the kernel installed itself, not ones added by
> hand or by a daemon. You know `ip route show` prints a `proto` word on each line. Now filter on it.

<details>
<summary>Answer</summary>

```bash
ip route show proto kernel
```

The generalisable move: **a field `ip` prints is usually a field `ip` can filter on.** The same shape
gives you `ip route show proto bgp`, `ip route show dev eth0`, `ip addr show scope global`. Act II's BGP
lesson uses `proto bgp`; nothing taught you `proto kernel`, and you didn't need to be taught it.

</details>

> **Check yourself —** You created a VLAN interface and `ip link show` tells you nothing about its tag or
> its parent. Why, and what fixes it?

<details>
<summary>Answer</summary>

```bash
ip -d link show eth0.10
```

`-d` is `-details`. By default `ip link` prints the generic device fields, and everything
type-specific — the VLAN id, a VXLAN's VNI and remote, a bridge's `stp_state` and `vlan_filtering`, a
bond's mode — is behind `-d`. Once you know that, you stop being surprised by it on every device type
instead of once per device type.

The instructive exception: **a veth's peer prints without `-d`**, as the `@` suffix —
`veth0@veth1` when the peer is in the same namespace, `veth0@if12` when it is elsewhere. Adding `-d`
there gets you only the bare word `veth`. So the rule is "type-specific detail needs `-d`", and the peer
link is not detail — it is identity, and `ip` treats it as part of the name.

The related habit: `-s` for counters, `-s -s` for more counters. Both stack onto anything.

</details>

> **Check yourself —** You need to run `ip addr` inside another running process's network namespace. You
> know the namespace files live at `/proc/<pid>/ns/`, and you know the flag letters match the filenames.
> Build the command. (This tool is not taught anywhere in the course.)

<details>
<summary>Answer</summary>

```bash
nsenter -t <pid> -n ip addr
```

`-t` = target pid, `-n` = the `net` namespace — the same letter as the `net` file in
`/proc/<pid>/ns/`. Add `-m` for `mnt`, `-p` for `pid`, `-U` for `user`, and so on down
[the namespace table](02-the-state-map.md#rule-namespace-flag-letters-are-the-filenames).

This is the mechanism under `docker exec` and `kubectl exec`, and it is the way into a container that
has no shell of its own — you bring your own binary and enter its namespaces.

**Read-only alternative, no tool required:** `cat /proc/<pid>/net/tcp` shows you that namespace's socket
table without entering anything. Worth knowing for the moment `nsenter` is not installed. Both this and
the `nsenter` form need to be able to *see* the target pid, which is what `--pid host` in the header
command is for.

</details>

> **Check yourself —** Capture only TCP SYN packets — connection attempts, not established traffic. The
> named filter primitives don't have a word for "SYN".

<details>
<summary>Answer</summary>

```bash
tcpdump -nn 'tcp[tcpflags] & tcp-syn != 0'
```

The byte-offset escape hatch: `tcp[tcpflags]` indexes into the TCP header, `& tcp-syn` masks the bit,
`!= 0` tests it. Whenever libpcap's named primitives don't cover what you want, this form does — the
named ones are conveniences over exactly this.

To exclude the SYN-ACKs of connections being accepted, add `and tcp[tcpflags] & tcp-ack == 0`.

</details>

> **Check yourself —** Two commands, one trap. What does `ip -n foo addr` do, and what does `ss -n` do?
> They are not the same kind of flag.

<details>
<summary>Answer</summary>

- `ss -n` = **numeric**: "Don't resolve service names."
- `ip -n foo addr` = `-netns foo`: run this in the network namespace named `foo`. It takes an argument.

So `ip -n eth0 addr` is not "numeric output for eth0" — it is "look inside a namespace called `eth0`".
`ip`'s numeric flag is capital **`-N`**.

The genuinely disorienting failure is not that one, though; it is that `-n` swallows **whatever token
comes next**, including a subcommand:

```
$ ip -n link show
Cannot open network namespace "link": No such file or directory
```

There is no namespace called `link`. You asked for one anyway, and the error names a thing you never
typed as a namespace.

This is the single most costly convention break in the toolchain, because `-n` means "numeric" in `ss`,
`netstat`, `nmap`, `iptables` and `tcpdump`, so the habit is strong and wrong in exactly one place.

</details>

---

## Ladder 2 — Derive the path

Two rules cover almost all of these: sysctl keys are `/proc/sys` paths with the dots turned into
slashes, and `/sys/class/net/<dev>/` is one file per field.

> **Check yourself —** Without running `ip`, read `eth0`'s MTU, its MAC, and whether the link is up.
> Three paths.

<details>
<summary>Answer</summary>

```bash
cat /sys/class/net/eth0/mtu
cat /sys/class/net/eth0/address
cat /sys/class/net/eth0/operstate
```

`carrier` (1 or 0) is the harder-edged version of `operstate` — it reports whether there is physically a
link, where `operstate` can read `unknown` on virtual devices.

Why bother when `ip link` prints all three: because if a tool and a file ever disagree, you need to know
which file to check. That is what the course means by *mechanism before tool*.

</details>

> **Check yourself —** You want to know whether this machine will forward IPv4 packets, and then turn it
> on. Give both the `sysctl` form and the file form.

<details>
<summary>Answer</summary>

```bash
sysctl net.ipv4.ip_forward                  # read
cat /proc/sys/net/ipv4/ip_forward           # the same value, same file

sysctl -w net.ipv4.ip_forward=1             # write
echo 1 > /proc/sys/net/ipv4/ip_forward      # the same write
```

Dots become slashes and it runs both ways: if you can `cat` it you can `sysctl` it. That makes
`sysctl -a | grep forward` a search over every tunable on the box — the fastest way to recover a name
you half-remember, and it needs no network.

> **⚠️ Read the value; think before you write it.** This sysctl is per network namespace, and the lab
> container in the header runs with `--network host` — so it has no namespace of its own and the write
> lands on the **host's**. Setting it to `0` there stops every other container on the machine from
> reaching anything. To experiment with the write, start a container *without* `--network host` and do it
> in there.

</details>

> **Check yourself —** You want `rp_filter` for `eth0` specifically. Give the path. Then the harder half:
> you set `/proc/sys/net/ipv4/conf/all/rp_filter` to `0` and `eth0`'s to `1`. What is in force on `eth0`?

<details>
<summary>Answer</summary>

The path is derivable:

```bash
/proc/sys/net/ipv4/conf/eth0/rp_filter
```

The semantics are **not** derivable, and this is the honest limit of the whole approach. The kernel's
own documentation says: *"The max value from conf/{all,interface}/rp_filter is used when doing source
validation."* So `max(0, 1)` = **1, in force**.

And that rule is specific to `rp_filter`. `log_martians` is an OR. `accept_redirects` is an AND when
forwarding is on and an OR when it is off. Three settings, three combination rules.

**So: derive the path, read the docs for the meaning.** Guessing here gives you a machine that is subtly
wrong rather than obviously broken.

One more from the same subtree worth knowing: `conf/default/*` is documented as *"used during creating
new interfaces"* — setting it changes nothing that already exists.

</details>

> **Check yourself —** Two processes. Decide whether they share a network namespace, using no tool more
> specialised than `readlink`.

<details>
<summary>Answer</summary>

```bash
readlink /proc/<pid1>/ns/net
readlink /proc/<pid2>/ns/net
```

Each prints something like `net:[4026531840]`. **Same inode number means the same network** — the same
interfaces, routes, netfilter rules, socket tables and the same `127.0.0.1`. A different inode means
they are as isolated as two separate machines.

That is the entire test, and it is why the course compares the symlinks rather than trusting a tool's
opinion about what a container is.

</details>

> **Check yourself —** The conntrack table filling up produces intermittent, load-dependent connection
> failures that look exactly like a flaky network. Two paths tell you whether that is what is happening.

<details>
<summary>Answer</summary>

```bash
cat /proc/sys/net/netfilter/nf_conntrack_count   # in use right now
cat /proc/sys/net/netfilter/nf_conntrack_max     # the ceiling
```

Or `conntrack -C` for the first. As `count` approaches `max`, new flows are dropped rather than tracked,
and the symptom is "sometimes it works". Worth checking early precisely because it is invisible to every
per-connection test — each individual retry may well succeed.

</details>

> **Check yourself —** Which interfaces are enslaved to the bridge `br0`, read from a file rather than
> from the `bridge` command?

<details>
<summary>Answer</summary>

```bash
ls /sys/class/net/br0/brif/
```

One entry per enslaved port. The reverse direction also exists: `/sys/class/net/veth-a/master` is a
symlink to the bridge that owns it, so you can walk the topology in either direction with `ls` and
`readlink` alone.

</details>

---

## Ladder 3 — Derive the tool

No syntax here. Given the symptom, name the instrument, and name the file that would settle it.

> **Check yourself —** `dig` resolves the name correctly. The application, on the same host, cannot. One
> tool tells you why. Which, and what is it doing differently?

<details>
<summary>Answer</summary>

```bash
getent hosts <name>
```

`dig` talks to the nameserver **directly**. An application calls `getaddrinfo()`, which goes through
NSS — `/etc/nsswitch.conf` decides which sources are consulted and in what order, `/etc/hosts` is
usually consulted first, and DNS may not be consulted at all. `getent hosts` walks that same path, so it
answers the question `dig` cannot.

The file that settles it: `/etc/nsswitch.conf`, specifically the `hosts:` line.

**One caveat that will bite you if you test this in the lab.** NSS is a glibc mechanism, and the lab image
is Alpine, which uses musl. musl implements no NSS: `/etc/nsswitch.conf` exists there and is completely
inert, with files-then-DNS hardcoded. So the model is right for the glibc hosts you will actually be
paged about, and you cannot verify it in `netshoot` — delete `files` from that file and `/etc/hosts` still
wins. Test it on Debian or RHEL.

</details>

> **Check yourself —** A connection to a service reaches ESTABLISHED and then transfers at a crawl.
> Nothing is refused, nothing times out. What do you reach for, and which numbers are you reading?

<details>
<summary>Answer</summary>

```bash
ss -ti dst :<port>
```

`-i` gives you the internals: `rtt`, `retrans`, `cwnd`, and the congestion-control algorithm. Rising
`retrans` means loss, and loss is what collapses throughput while leaving every binary check passing.
Add `-m` for the socket buffers if the window looks like the constraint.

Machine-wide rather than per-socket, the tool is `nstat` — retransmits and listen overflows as deltas
since the last call. It is **[roster only](03-the-index.md#the-honest-tally)**: no lesson in this course
runs it, and it is one of the highest-value gaps in the toolset.

</details>

> **Check yourself —** Small requests succeed, large ones hang forever. Nothing is refused. Name the
> cause, the command that confirms it, and why the hang is *permanent* rather than slow.

<details>
<summary>Answer</summary>

MTU, nearly always — often an overlay, where a VXLAN or WireGuard header eats bytes so the usable MTU
inside the tunnel is lower than the interface advertises.

```bash
ping -M do -s 1400 <host>      # walk the size up until it fails
```

`-M do` sets Don't Fragment, so an oversized packet must be rejected rather than split.

It hangs permanently rather than slowly because path MTU discovery depends on ICMP "fragmentation
needed" messages coming *back*. If a firewall drops those — and dropping "all ICMP" is a common
misconfiguration — the sender never learns to send smaller, and retries forever at the same size. So the
confirming capture is `tcpdump -ni any icmp`: the absence of those messages is the finding.

The evidence on the receiving side is the RX `dropped` counter in `ip -s link show <dev>`.

</details>

> **Check yourself —** You are on a node. `kubectl` does not respond at all. Name the tool you drop to,
> and the file that tells you what the control plane is *supposed* to be running.

<details>
<summary>Answer</summary>

```bash
crictl ps -a          # is the API server's container running, or crash-looping?
crictl logs <id>      # why did it exit?
```

`crictl` talks to the node's container runtime directly, so it works when the API server is the thing
that is broken — which is exactly when `kubectl` cannot help you.

The file is `/etc/kubernetes/manifests/kube-apiserver.yaml`. The kubelet reads that directory from disk
and starts what it finds there, with **no API server involved** — which is both how the control plane
bootstraps itself and how you fix it when it is down.

</details>

> **Check yourself —** A Pod cannot reach a Service. `kubectl get svc` shows the Service exists and has a
> ClusterIP. What is the *first* thing you check, and why is pinging the ClusterIP worthless?

<details>
<summary>Answer</summary>

```bash
kubectl get endpointslices -l kubernetes.io/service-name=<svc>
```

A Service with no endpoints is the most common cause by a wide margin, and it means the selector matches
no ready Pod. The Service object itself looks perfectly healthy either way, which is what makes this the
first check rather than a later one.

Pinging the ClusterIP proves nothing because **nothing listens on it**. It is not a host and not an
interface — it exists only as a rewrite rule in iptables or IPVS, matched on protocol *and port*. ICMP
matches no rule, so the ping is answered by nobody and tells you nothing about whether the Service
works.

Confirm the rules exist on the node with `iptables-save | grep <clusterIP>`.

</details>

---

## When you can do these without the reveals

You have the thing this directory was built for: you can stand in front of a tool you have not used and
work out what to type, instead of searching for someone else's example.

Two habits are what keep it:

1. **When you catch yourself about to search for a flag, try `<tool> --help | grep` first.** It is
   faster, it is version-correct for the box you are on, and it works with no network.
2. **When you find yourself parsing output with `awk`, look for `-j`.** Field names are a contract;
   column positions are not.

The drills in the acts are the other half of this — they hand you a genuinely broken machine and only a
symptom, on a clock:
[Act I](../networking-fundamentals/act-1-one-machine/diagnose.md) ·
[Act II](../networking-fundamentals/act-2-two-machines/diagnose.md) ·
[Act III](../networking-fundamentals/act-3-the-internet/diagnose.md) ·
[Act IV](../networking-fundamentals/act-4-one-pretends-many/diagnose.md) ·
[Act V](../networking-fundamentals/act-5-kubernetes/diagnose.md)

Back to **[the grammar](01-the-grammar.md)** · **[the index](03-the-index.md)**
