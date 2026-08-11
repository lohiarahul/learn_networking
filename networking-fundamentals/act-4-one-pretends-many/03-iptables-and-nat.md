# iptables and NAT

Our containers can talk to the host and to each other. But a container with a private address like `172.17.0.2` is invisible to the internet, and the internet is invisible to it. To fix that we need to *rewrite packets in flight*, which means first understanding the machinery that lets the kernel touch a packet at all.

![Several inside addresses translated to a single outside address](../../illustrations/02-addressing/nat.svg)

You have met the name of that machinery once already, as a promissory note. [Act III's conntrack lesson](../act-3-the-internet/02b-conntrack.md) described the kernel's NAT machinery as "the `iptables` chains Act IV takes apart" — a thing recording every translated connection, which you could read the *results* of and not the rules. This is where the note comes due.

### iptables — the kernel's packet processing hooks

**The problem that made this necessary** — As soon as Linux was routing other people's packets — for firewalls, for NAT, for traffic shaping — it needed a way to let administrators *intervene* at well-defined points in a packet's journey through the kernel, without rewriting the kernel. The answer, the **netfilter** framework (late 1990s, exposed to users as `iptables`), was a set of fixed hooks bolted onto the packet path: places where you can hang your own rules. The mental trap is thinking iptables is "a firewall." It isn't. It's a framework for attaching match-and-act rules to specific points in the kernel's packet flow; a firewall is just one thing you can build with it.

**What it actually is** — There are five hooks, each a point in the packet's path through the kernel:

- **PREROUTING** — packet just arrived, *before* the kernel decides where it goes.
- **INPUT** — the routing decision said "this is for me, locally."
- **FORWARD** — the routing decision said "this is passing through me to somewhere else."
- **OUTPUT** — a packet originating from a local process, heading out.
- **POSTROUTING** — about to leave the machine, *after* the routing decision.

At each hook you write rules that match on any field you like — source/destination IP, port, protocol, interface, even connection state — and then `ACCEPT`, `DROP`, or **rewrite** the packet.

Two words for the filing system, because the tools use them constantly. A **table** groups rules by what they do to a packet: `filter` accepts and drops, `nat` rewrites addresses. Inside a table, the rules attached to one hook are that hook's **chain** — so `iptables -t nat -L POSTROUTING` means "show me the address-rewriting rules that run as a packet leaves." Five hooks, a handful of tables, one list per pair.

**Draw it** — the netfilter packet flow, and where NAT lives:

<!-- figure: iptables-hooks -->

```
   packet                                                          packet
   arrives                                                          leaves
     │                                                                ▲
     ▼                                                                │
 ┌────────────┐     ┌──────────┐                          ┌─────────────┐
 │ PREROUTING │ ──▶ │ routing  │                          │ POSTROUTING │
 │  (DNAT)    │     │ decision │                          │   (SNAT)    │
 └────────────┘     └────┬─────┘                          └─────────────┘
                         │                                       ▲
          ┌──────────────┴───────────────┐                       │
          ▼ "for me"                      ▼ "for someone else"    │
     ┌─────────┐                     ┌──────────┐                 │
     │  INPUT  │ ─▶ local process    │ FORWARD  │ ────────────────┘
     └─────────┘                     └──────────┘
          ▲                                                        ▲
          │                                                        │
     local process ──────────────────▶  ┌────────┐ ───────────────┘
                                         │ OUTPUT │
                                         └────────┘

  DNAT rewrites the DESTINATION in PREROUTING (before routing chooses a path).
  SNAT rewrites the SOURCE in POSTROUTING (after the path is chosen, on the way out).
```

**The file** — The rules live in tables; read them raw:

```
iptables -t nat    -L -n -v     the NAT table — DNAT/SNAT/MASQUERADE rules
iptables -t filter -L -n -v     the filter table — the ACCEPT/DROP firewall rules
```

The `nat` table is where address rewriting happens; the `filter` table is where the firewall lives. `-n` keeps it numeric (no slow DNS), `-v` shows packet and byte counters per rule — and those counters are the single best debugging tool here, because they tell you which rule packets are actually hitting.

**The experiment** — Make the counters move and watch which hook the packet actually walked through. List the filter table with counters and line numbers:

> **Predict first —** after one `curl`, which of the five chains will have non-zero packet counters, and which will stay at zero?

```bash
iptables -t filter -L -n -v --line-numbers
```

Now generate one packet's worth of traffic — `curl -s http://example.com >/dev/null` — and run that same command again. The `pkts`/`bytes` columns on rules in the `OUTPUT` and `INPUT` chains tick upward, while the `FORWARD` chain stays frozen at zero.

That is the surprise made concrete: this packet was *born here and addressed elsewhere*, so it took the `OUTPUT → POSTROUTING` path out and the reply came back through `PREROUTING → INPUT`; it never touched `FORWARD`, which only sees traffic passing *through* the machine. The counters are the packet's footprints, and the chain whose counters move is the path it walked.

> **You understand this when you can** name, for a given packet, which of the five hooks it passes through, and predict which chain's counters will move for a locally-originated connection versus one merely forwarded through the machine.

**Kubernetes sees this as** — These five hooks are the whole stage on which Kubernetes performs. It adds no new place for a packet to be touched, because there isn't one: every `KUBE-`something chain you will meet in Act V is an ordinary custom chain, stitched into one of these five points, in one of these tables, readable with the command you just ran. So the entire iptables side of a cluster reduces to one question you can already ask of any packet — *which hook, which chain, which rule?*

> **On your own machine —** `docker run -p 8080:80` is a DNAT rule and nothing more. Find the rule Docker wrote for a port you published, in [Act IV in the wild](in-the-wild.md#publishing-a-port-is-a-dnat-rule).

> **Check yourself —** Why must DNAT happen in `PREROUTING` and SNAT in `POSTROUTING`, rather than the other way round?

<details>
<summary>Answer</summary>

Because of where the routing decision sits between them. DNAT changes the **destination**, so it has to happen *before* routing — otherwise the kernel picks a path for an address the packet is about to stop having. SNAT changes the **source**, which routing does not care about, so it can wait until the path is already chosen, on the way out.

</details>

### NAT — sharing one IP across many processes

**The problem that made this necessary** — Here's the puzzle. A container has `172.17.0.2`. The host has `192.168.1.5`. The container wants `google.com`. But `172.17.0.2` is a private address — the internet has never heard of it and will never route a reply to it. If the container just sends a packet with source `172.17.0.2`, the reply has nowhere to come back to. We need the host to *lie on the container's behalf*: rewrite the source so replies come back to the host, then quietly undo the lie. That trick is **NAT** (Network Address Translation), and it's how one public IP serves a whole house, a whole office, or a whole node full of containers.

![Reusable inside addresses behind one globally routable address](../../illustrations/02-addressing/private-vs-public-ip.svg)

**What it actually is** — Two directions:

**SNAT (Source NAT)** rewrites the source address on the way *out*, in POSTROUTING. The container's packet `src=172.17.0.2 → google.com` leaves the host rewritten to `src=192.168.1.5 → google.com`. Google replies to `192.168.1.5` — the only address it knows. The host's **conntrack** (connection tracking) remembers the mapping, so when the reply arrives it rewrites the destination back to `172.17.0.2` and delivers it inward. The container never knows it was translated; it thinks it talked to Google directly. **MASQUERADE** is SNAT's lazy cousin: instead of hardcoding `192.168.1.5`, it says "use whatever IP the outgoing interface has," which is what you want when the host's IP can change.

**DNAT (Destination NAT)** rewrites the destination on the way *in*, in PREROUTING. A packet arrives for some address and gets its destination rewritten to a different one before routing chooses a path. This is port forwarding — and note, without going any further with it yet, that nothing here requires the address the packet was *sent* to be an address anybody actually has.

**The experiment** — In `docker run --rm -it --privileged --network host nicolaka/netshoot`, find the rule that gives containers internet access:

> **Predict first —** which single rule type in POSTROUTING is responsible for letting every container reach the internet, and what address does it swap in?

```bash
iptables -t nat -L POSTROUTING -n -v
```

Look for a `MASQUERADE` rule, typically matching a source like `172.17.0.0/16` and an outbound interface. That single line is the entire reason every Docker container on the box can reach the internet: on the way out, the kernel swaps the container's private source for the host's real IP, and conntrack untangles the replies. Add `iptables -t nat -L PREROUTING -n -v` and you'll see the DNAT side — the rules that catch traffic for published ports and rewrite it inward to a container.

> **You understand this when you can** trace a container's packet to google.com and back: name the hook where the source is rewritten (POSTROUTING/MASQUERADE), the hook where the reply's destination is restored, and the component that remembers the mapping (conntrack) — and explain why the container never sees any of it.

> **On your own machine —** every `docker run` on your Mac performs this whole act for you: the namespace, the veth, the bridge, and the `-p` DNAT rule. See where macOS hides them (in a Linux VM) and prove the DNAT with a `curl`, in [Act IV in the wild](in-the-wild.md).

### The recognition — this act, assembled, on your own machine

Everything so far was built by hand for one reason: so that when you meet it pre-assembled you *recognise* it instead of trusting it. Docker is that assembly, and it is running on your box right now. On a Linux host with Docker, publish a port from another terminal:

```bash
docker run -d -p 8080:80 --name pub nginx
```

> **Predict first —** which of the pieces you built by hand — namespace, veth, bridge, MASQUERADE, DNAT — did that single command create, and which chain is the `-p 8080:80` rule sitting in?

```bash
ip link show docker0                          # a bridge (lesson 2), created for you
ls /sys/class/net/docker0/brif/               # nginx's host-side veth, plugged into it
iptables -t nat -L DOCKER -n                  # DNAT tcp dpt:8080 to:172.17.x.x:80
iptables -t nat -L POSTROUTING -n -v          # MASQUERADE for 172.17.0.0/16
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080     # 200 — the DNAT fired
```

Read those five lines again and there is nothing left over. `docker0` is the software switch. The entry under `brif/` is one end of a veth pair whose far end is inside nginx's namespace. The `DNAT … to 172.17.x.x:80` in the `DOCKER` chain *is* `-p 8080:80` — the flag is not a feature, it is that rule, written by a program instead of by you. The `MASQUERADE` is the only reason the container can reach the internet. A `docker compose` network is the same trick with one more bridge and one namespace per service; Docker's own "overlay" driver is the encapsulation you are about to build in [Overlay and VXLAN](04-overlay-vxlan.md). There is no such thing as Docker networking. There is namespace, veth, bridge, and netfilter, with a CLI in front — and you can now read all four directly, which means you can debug them when the CLI's story and the kernel's disagree. *(On a Mac these live inside the Docker Desktop VM — [Act IV in the wild](in-the-wild.md#peek-into-the-vm-where-the-primitives-actually-live) shows you how to get in.)*

**Tear it down:**

```bash
docker rm -f pub
```

**The shadow it casts** — Two tools writing rules into the same five hooks, neither aware of the other.

> **Predict first —** you published 8080 with `-p 8080:80`. Now you reach for `ufw` — the friendly firewall front-end most distributions ship, which writes iptables rules for you — and run `ufw deny 8080`. `ufw status` confirms `8080 DENY Anywhere`. Is the port closed? Before you answer: which hook does a packet bound for a *container* walk through, and which hook would a firewall for *this machine* hang its rules off?

```bash
iptables -L FORWARD -n --line-numbers | head
```

The first thing the `FORWARD` hook does is jump into `DOCKER-USER` and `DOCKER` — Docker inserted those jumps at the top. And that is the hook that matters, because a packet for a published port is DNAT'd in `PREROUTING` to the container's address and then **forwarded**; it is not for this machine, so it never reaches `INPUT`, which is where ufw's rules live. The port is wide open to the entire internet, and `ufw status` will keep saying `DENY` all the way through the incident. Countless production databases have been exposed exactly this way: the owner saw a green firewall and never knew what was underneath it. The insight is not "ufw is broken" — it is that *whoever writes the earliest matching rule on the hook the packet actually walks wins*, and a tool that reports on its own rules cannot report on anyone else's. Read the table, not the tool.

**Kubernetes sees this as** — Every rule a cluster adds to a node lands in the tables you just read, at the hooks you just traced. Nothing is hidden from you here any more; the only thing you lack is the vocabulary for what the rules are *for*.

Which is enough to set up the one question worth carrying out of this lesson. A cluster gives you a single stable address to dial for a service whose real backing processes are born and destroyed constantly, on machines you did not pick. You know two ways an address can work: a device owns it, or a route leads to it. Hold on to a third possibility you have just seen the machinery for, and then, in Act V, go looking for that service address with `ip addr` on every node and see for yourself what is there. Do not let anyone tell you the answer first — including the part of you that already suspects it.

**Where you are now** — You can name the five netfilter hooks and predict which of them a given packet walks, prove it from the rule counters rather than from documentation, and read the two rules that make container networking work: the `MASQUERADE` that lets a private address out and the `DNAT` that lets a knock in. You can look at any `docker run` line and say which kernel object each flag produced. And you know why a firewall that reports itself green can be lying.

Every one of these tricks, though, ends at the edge of this machine. Two containers on one host share a bridge; a container reaching the internet borrows the host's address on the way out. Now put the two private networks on two *different* hosts and neither trick is available: there is no shared switch to plug into, and the physical network in between would drop a `10.20.0.0/24` packet on sight. You could try NAT again and translate each private address into its host's — but then work out what the far side sees as the sender, and ask whether it could ever start a conversation in the other direction. So how do you make two software switches, on two machines, behave like one wire — without asking the network in between for permission?

---

← Prev: **[veth and bridge](02-veth-and-bridge.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Overlay and VXLAN](04-overlay-vxlan.md)** →
