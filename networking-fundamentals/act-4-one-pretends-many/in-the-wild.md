# Act IV in the wild — where your Mac keeps the namespaces

The act builds namespaces, veth pairs, a bridge, and NAT rules by hand inside one Linux container. This
page points **the same ideas at the containers you already run on your Mac** — and confronts the honest
twist: none of Act IV's primitives exist on macOS at all. They live one layer down, and this page shows
you where.

## Every `docker run` is Act IV, performed for you

*Concept:* a container's network is a namespace, wired to a bridge with a veth pair, reachable through
NAT — exactly what you built by hand.
*(Container version: `ip netns add`, `ip link add … type veth`, `ip link add … type bridge`.)*

- **List the networks Docker keeps** — `bridge` is the default one, and it *is* lesson 2's software
  switch:
```bash
  docker network ls
  docker network inspect bridge
  ```
  The `Subnet` (usually `172.17.0.0/16`) and the `Containers` block are the bridge's address range and
  the veth ends plugged into it — the same `br0`/`ls /sys/class/net/br0/brif` you read by hand, printed
  as JSON.
- **Look inside a container's namespace.** Start one, then peek at its private stack:
```bash
  docker run -d --name web nginx
  docker exec web ip addr
  ```
  That `eth0` with a `172.17.x.x` address is the container's namespace interface — the far end of a
  veth pair whose other end is a port on `docker0`. `docker exec … ip addr` is the same window into a
  namespace that `kubectl exec … ip addr` gives you into a Pod (lesson 1).

## Publishing a port is a DNAT rule

*Concept:* `-p 8080:80` is not magic — it's the DNAT rule from lesson 3, rewriting a host-port knock to
the container's address, with conntrack carrying the reply home.

```bash
docker run -d -p 8080:80 --name pub nginx
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080     # 200 — the DNAT fired
```

On Linux you could now read that rule with `iptables -t nat -L`. On your Mac you can't — and *why* you
can't is the whole point of the next section.

## Peek into the VM where the primitives actually live

*Concept:* macOS has no namespaces, no veth, no netfilter. Docker Desktop runs a small **Linux VM**
(LinuxKit), and *that* VM is the machine doing everything in Act IV. Your `docker` commands are a window
into it; to touch the raw `ip`/`iptables`, you enter the VM:

```bash
docker run -it --rm --privileged --pid=host justincormack/nsenter1
```

That drops you into a root shell in the VM's own namespaces (it's `nsenter` into PID 1 — lesson 1's
inode trick, run against the VM's init). Now every Act IV command is real again:

```bash
ip netns list                          # (Docker uses hidden namespaces; containers may not show here)
ip link show docker0                    # the bridge from lesson 2, live
iptables -t nat -L POSTROUTING -n       # the MASQUERADE that gives containers internet (drill 1)
iptables -t nat -L PREROUTING  -n       # the DNAT rules your -p flags wrote (drill 3)
```

The `MASQUERADE` for `172.17.0.0/16` and the `DNAT … to 172.17.x.x:80` you'll find here are the exact
rules you added by hand in the diagnose drills — written by Docker instead of you. Type `exit` to leave
the VM.

## macOS vs Linux — the swaps this act needs

**There are almost no 1:1 swaps here, and that is the lesson.** Namespaces, veth, bridges, and
netfilter are **Linux kernel features**. The macOS kernel (XNU) has none of them — which is *why*
Docker Desktop ships an entire Linux VM. On a Mac, "the container's network" is two layers down:
**your Mac → the LinuxKit VM → the container's namespace.**

| Container / VM (Linux) | Your Mac (macOS) |
|---|---|
| `ip netns add` (make a private stack) | no equivalent — lives in the Docker Desktop VM |
| `ip link add … type veth` (the wire) | created for you by `docker run` / `docker network` |
| `ip link add … type bridge` (`docker0`) | inspect via `docker network inspect bridge`; the bridge itself is in the VM |
| `iptables -t nat` (MASQUERADE / DNAT) | invisible on macOS; `-p host:container` *is* the DNAT, applied inside the VM |
| `/proc/self/ns/net` (the namespace inode) | no `/proc` on macOS (as in Act I) |
| enter a namespace: `nsenter` / `ip netns exec` | enter the VM: `docker run --privileged --pid=host … nsenter1` |

**Why no `ifconfig`/`route` shortcut this time:** in earlier acts, macOS's BSD tools (`arp`, `netstat
-rn`, `ifconfig`) stood in for Linux's `ip`. Act IV has no such fallback — macOS never implemented
network namespaces or veth, so there is nothing local to inspect. The container networking you build in
this act genuinely runs on Linux; on a Mac you are always reaching *through* a Linux VM to see it. That
boundary — Mac tooling on the outside, real Linux primitives on the inside — is exactly the boundary
Kubernetes hides behind `kubectl`, which Act V opens up.

---

↑ **[Act IV overview](README.md)** · Back to the wiring: **[iptables and NAT](03-iptables-and-nat.md)**
