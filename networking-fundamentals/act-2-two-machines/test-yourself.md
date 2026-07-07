# Act II — Test yourself

> Do this **after** working through all the lessons in [the act overview](README.md). Answer each one out loud or on paper *before* you open its answer — the attempt is what makes it stick, far more than re-reading. A wrong attempt followed by the right answer beats a confident skim every time.

> **Question 1 —** ARP has no authentication of any kind. Why was it designed that way, and what attack does that omission make possible on a modern LAN?

<details>
<summary>Answer</summary>

ARP was designed in 1982 for a LAN full of trusted colleagues, so it simply believes any reply — including a *gratuitous* reply nobody asked for. An attacker on the same wire can announce "the gateway is at my MAC," every machine caches the lie, and traffic meant for the outside world flows through the attacker first (ARP spoofing / poisoning).

</details>

> **Question 2 —** A packet's destination matches three different rows in the routing table at once. How does the kernel decide which one wins, and why is that rule — not "first match" — the one that matters?

<details>
<summary>Answer</summary>

**Longest-prefix match**: the most specific route — the one with the longest network prefix — wins, regardless of order in the table. A `/16` beats a `/8` beats the `0.0.0.0/0` default. It matters because it lets a general fallback (the default route) coexist with precise exceptions (a single `/32` to one host) without conflict.

</details>

> **Question 3 —** Why does DNS run over UDP instead of TCP, and where does the roughly 5-second hang on a failed cluster DNS lookup actually come from?

<details>
<summary>Answer</summary>

A DNS lookup is one small question and one small answer; a TCP handshake would more than double the round trips for no benefit, so DNS uses fire-and-forget UDP. Because UDP has no acknowledgement or retransmission of its own, a single dropped query packet leaves the stub resolver waiting out its default per-query timeout — about 5 seconds — before it retries.

</details>

> **Question 4 —** TTL is named "Time To Live," but it is not a clock. What does it really count, and what happens at the moment it reaches zero?

<details>
<summary>Answer</summary>

TTL is a **hop budget**, not a time: a one-byte counter the sender sets (Linux defaults to 64), decremented by one at every router that forwards the packet. The instant a router decrements it to zero, that router drops the packet and sends an ICMP "time exceeded" back to the source — which is exactly how traceroute maps a path.

</details>

> **Question 5 —** You add a name to `/etc/hosts` that no DNS server on earth knows, and it resolves anyway. What makes the local file able to override the entire global DNS database?

<details>
<summary>Answer</summary>

The order in `/etc/nsswitch.conf`. Its `hosts:` line typically reads `files dns`, so the resolver consults `/etc/hosts` *first* and only falls through to DNS if the name is not found there. A name present in the file is answered locally and no DNS query is ever sent.

</details>

> **Question 6 —** Two machines plug into the *same physical switch* yet cannot reach each other even at Layer 2. How can one switch keep them apart, and what must their traffic do to cross between them?

<details>
<summary>Answer</summary>

**VLANs.** Each switch port is assigned a VLAN ID carried in a 12-bit 802.1Q tag, and the switch floods broadcasts only within a VLAN — so two ports in different VLANs are separate broadcast domains, as isolated as two physical switches. Crossing between them requires going *up to a router* (Layer 3), even though it's one physical switch.

</details>

> **Question 7 —** The routing table from question 2 — out on the internet, *who* fills it? Name the protocol, and explain why its trust model is a planetary-scale version of ARP's flaw.

<details>
<summary>Answer</summary>

**BGP.** Autonomous systems announce to each other which IP prefixes they can reach, carrying the AS-path (path-vector, for loop-prevention and policy); forwarding still uses longest-prefix match. BGP authenticates nothing, so a network can announce a prefix it doesn't own (a hijack) or accidentally withdraw its own (Facebook, 2021) and routers worldwide believe it — exactly ARP's "trust any reply," scaled to the whole internet.

</details>

> **Question 8 —** With the Don't-Fragment bit set, a 1473-byte ping payload fails on a 1500-MTU link but 1472 succeeds. Account for the missing 28 bytes — and explain the "small things work, big things hang" failure that follows when a firewall blocks ICMP.

<details>
<summary>Answer</summary>

1500 MTU − 20 (IP header) − 8 (ICMP header) = **1472** bytes of payload that fit. The Don't-Fragment bit forbids splitting, so 1473 must be dropped and an ICMP "fragmentation needed" sent back. If a firewall blocks that ICMP, Path MTU Discovery breaks: the sender never learns to shrink, so large packets vanish with no error while small ones pass — an **MTU black hole** (connections open, then hang on the first big transfer).

</details>

> **Question 9 —** A machine that has never spoken on the network has no IP address, yet it obtains one *over that network*. How is that chicken-and-egg solved, what are the four steps, and why can a rogue server hijack a victim through it?

<details>
<summary>Answer</summary>

The host **broadcasts** (to `ff:ff:ff:ff:ff:ff`, from source `0.0.0.0`) over UDP — the one thing it can do with no address. The four steps are **DORA**: Discover, Offer, Request, Acknowledge; the offer carries the IP plus gateway, DNS, and a lease. Because DHCP authenticates nothing and the client takes the first usable offer, a **rogue DHCP server** can answer first with itself as gateway and DNS, becoming a man-in-the-middle for all the victim's traffic.

</details>

> **Question 10 —** Every ARP tool in this act — `arp -n`, `ip neigh`, `cat /proc/net/arp` — only *reads* the cache. How would you instead *ask* the wire for a mapping yourself, and why is being able to craft that one request the very same capability an attacker uses to forge a reply?

<details>
<summary>Answer</summary>

Build the request as a frame and send it: in scapy, `srp1(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(op=1, pdst=<ip>))` broadcasts "who has this IP?" and reads the owner's MAC off the reply's `hwsrc` (the one-trick `arping` does the same). Because crafting it means you control *every* field, flipping `op=1` (request) to `op=2` (reply) and filling `psrc`/`hwsrc` with a lie is the **same one-line packet** — now a gratuitous ARP that poisons a victim's cache. The honest lookup and the spoof differ by a single field, which is exactly why a protocol that authenticates nothing is so easily turned against its users.

</details>

> **Question 11 —** A host is configured as `172.20.13.90/26`. On paper, with no tool: give its network address, its broadcast address, and the number of usable host addresses. Then say why none of the three can be read off the dotted decimals by eye.

<details>
<summary>Answer</summary>

`/26` means 26 network bits, so the mask is `255.255.255.192` and only the last octet is split. Write that octet in binary: `90` is `01011010`, and `192` is `11000000`.

- **Network** — address AND mask: `01011010 & 11000000 = 01000000 = 64`, so **`172.20.13.64`**.
- **Broadcast** — the network with every host bit set to 1: `01111111 = 127`, so **`172.20.13.127`**.
- **Usable hosts** — host bits are `32 − 26 = 6`, so `2^6 = 64` addresses, minus the network address and the broadcast address: **62**.

You cannot see any of it in the decimals because the prefix does not land on a dot: the last octet's top 2 bits belong to the network and its bottom 6 to the host, and `90` gives no hint of where that line falls. `/8`, `/16`, and `/24` are the only prefixes you can do by squinting — every other one requires writing the bits.

</details>

---

← Back to **[Act II overview](README.md)** · Next: **[Diagnose it →](diagnose.md)**
