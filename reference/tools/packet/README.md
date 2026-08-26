# `packet` — the bytes actually on the wire

**What you see in `strace`:** `socket(AF_PACKET, …)` or `socket(AF_INET, SOCK_RAW, …)`

Seven tools that bypass the normal socket path and work with frames directly. This is the only
interface that can show you *what was really transmitted*, as distinct from what any tool believes was
configured or requested.

[`tcpdump`](tcpdump.md) · [`tshark`](tshark.md) ·
[`scapy`](scapy.md) · [`arping`](arping.md) ·
[`traceroute`](traceroute.md) · [`mtr`](mtr.md) ·
[`nmap`](nmap.md)

---

## They all need a capability, and that is diagnostic

`AF_PACKET` requires `CAP_NET_RAW`. So "`ping` works but `tcpdump` shows nothing" is very often not a
network fault at all — it is a missing capability, and
[`capsh --print`](../procfs/capsh.md) settles it in one command. This is the most common false
alarm in container debugging.

## The filter language is a third grammar

`tcpdump`'s filters are libpcap expressions — not shell globs, not `ss`'s language, not regular
expressions. They compile to bytecode and are worth learning because they compose:

```bash
tcpdump -nn 'tcp port 443'
tcpdump -nn 'host 10.0.0.1 and not port 22'
tcpdump -nn 'tcp[tcpflags] & tcp-syn != 0'        # SYNs only, by byte offset
tcpdump -nn 'icmp[icmptype] == icmp-unreach'      # where MTU black holes hide
```

`tshark` accepts these *and* Wireshark display filters (`-Y 'http.request'`), which are a **different
language again** — field-based rather than byte-based. Mixing them up is the usual first frustration.

## Why the packet you see may not be the packet on the wire

Two effects routinely make this interface lie, and both have a fix outside it:

- **Offloads.** With TSO/GRO on, the kernel hands `tcpdump` a 64 KB "packet" that never existed on a
  1500-byte link. [`ethtool -k <dev>`](../netlink/ethtool.md) shows the offloads;
  `ethtool -K <dev> tso off gro off` makes captures honest again.
- **You are on the wrong side of a translation.** A capture on the host sees post-NAT addresses; the
  same flow inside the namespace sees pre-NAT. Neither is wrong. Capture on **both** sides of the veth,
  and read [`conntrack -L`](../netlink/conntrack.md) for the mapping.

---

## What `packet` can never tell you

**Which process, or which rule, was responsible.** A frame carries addresses and ports, not a PID and
not a rule handle. `tcpdump` will show you a SYN with no reply and cannot tell you whether a netfilter
rule dropped it, a route sent it elsewhere, or the peer simply never answered.

To close that gap: [`ss -tanp`](../netlink/ss.md) or [`lsof -i`](../procfs/lsof.md) for the
owning process, [`nft list ruleset`](../netlink/nft.md) for the rules, and
[`probe`](../probe/README.md) — `pwru` or `retis` — for the actual kernel function that dropped it.

## What streams here

**All of it.** This interface is inherently live: `tcpdump`, `tshark`, `scapy`'s `sniff()` and `mtr`
all emit as events happen. That is its main advantage over [`procfs`](../procfs/README.md), and the reason to
reach for it when the thing you are chasing is short-lived.

---

Taught in: [ICMP and UDP](../../../networking-fundamentals/act-2-two-machines/03-icmp-and-udp.md) ·
[ethernet and ARP](../../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) ·
[MTU and fragmentation](../../../networking-fundamentals/act-2-two-machines/03b-mtu-and-fragmentation.md) ·
[TCP states and the SYN scan](../../../networking-fundamentals/act-1-one-machine/05b-tcp-states-and-the-syn-scan.md)

Next: [`probe`](../probe/README.md), the only interface that can name the function that dropped your packet.
