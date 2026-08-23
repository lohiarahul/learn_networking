# Act IV — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act IV. This checks whether you can *use* it. Real
failures never arrive labelled "this is a missing MASQUERADE" or "that veth is down" — they arrive as a
symptom, a shrug, and a ticket. Each drill below puts your machine into a **real broken state** (not a
story), hands you only the symptom, and asks you to find the cause with the act's tools.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** If you read it closely you'll spoil the
   hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud what you think is wrong and which file or
   tool would prove it — *then* look.
3. **Open the reveal only after you've tried.**

**Where:** inside the lab container with the host's real network attached —
`docker run --rm -it --privileged --network host nicolaka/netshoot`. Each drill builds its **own**
namespaces and veths from scratch (the same commands you ran in lessons 1–3), so run a drill's
`Cleanup` line before starting the next one — and everything is wiped entirely on `exit`. The
`--privileged` flag is what lets you create namespaces, move interfaces, and write NAT rules.

---

## The clock

Every drill below carries a **target time**, and this is the one thing these drills do that the
lessons deliberately do not. The course is built to make you understand; a certification is scored on
whether you can act inside a budget, and those are different skills that look identical from the
inside. So: Five rather than seven, because each of these drills has a narrower surface than an exam task — one machine, or two, and a handful of files.

Three rules, taken straight from [the exam-day pacing doctrine](../../exam-prep/exam-day.md):

1. **Start the clock when the symptom appears**, not when you start the reproduce block. Building the
   broken state is setup, and on the exam somebody else has already done it.
2. **At the target, say your best hypothesis out loud** even if you are not confident. Naming a wrong
   hypothesis at 5 minutes is worth more than a right one at twenty, because the wrong one is
   falsifiable in one command and the exam pays for closed tasks.
3. **At 10 minutes, stop and open the reveal.** That is not giving up, it is the exam's own rule —
   *"the moment a task passes 10 minutes, flag it and move on"* — and the skill it builds is the
   costly one. A task that eats 25 minutes has cost you three others worth the same marks.

Run each drill untimed the first time if you like. Then run it again, weeks later, with a timer, and
notice that the second number is the one that predicts anything.

## Drill 1 — "The new container can reach the host but not the internet"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"We wired up a fresh container-style namespace. It can ping its own gateway, DNS is
> configured, forwarding is on — but every ping to the outside times out. The host itself reaches
> `8.8.8.8` fine. Same kernel, same uplink. Why can the host get out and the namespace can't?"*

**Reproduce it** (run; don't read):

```bash
UPLINK=$(ip route show default | awk '{print $5}')
ip netns add app
ip link add veth-h type veth peer name veth-a
ip link set veth-a netns app
ip addr add 10.50.0.1/24 dev veth-h
ip link set veth-h up
ip netns exec app ip addr add 10.50.0.2/24 dev veth-a
ip netns exec app ip link set veth-a up
ip netns exec app ip link set lo up
ip netns exec app ip route add default via 10.50.0.1
sysctl -qw net.ipv4.ip_forward=1
```

**Confirm the symptom:**

```bash
ip netns exec app ping -c1 -W2 10.50.0.1 && echo "gateway (host): OK"
ip netns exec app ping -c1 -W2 8.8.8.8   || echo "internet: FAILED"
```

The namespace reaches its gateway on the wire, forwarding is enabled — yet the internet ping fails.

**Your move.** The cable works (the gateway ping proves it) and the kernel is forwarding, so the
request *is* leaving the namespace. Sniff the uplink and watch what source address the packet carries
onto the real wire — then ask which table was supposed to fix that, and whether its rule exists.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Watch what actually leaves the box:

```bash
UPLINK=${UPLINK:-$(ip route show default | awk '{print $5}')}   # re-derive it if this is a new shell
echo "uplink is: $UPLINK"                                        # must not be empty
tcpdump -ni "$UPLINK" icmp &
ip netns exec app ping -c1 8.8.8.8
```

```
IP 10.50.0.2 > 8.8.8.8: ICMP echo request ...
```

The packet leaves the host still carrying its **private source `10.50.0.2`** — an address the internet
has never heard of and can never route a reply back to. The request goes; the reply has nowhere to
come home to. Now read the table that was supposed to rewrite that source (lesson 3):

```bash
iptables -t nat -L POSTROUTING -n -v
```

There is **no `MASQUERADE`/`SNAT`** rule matching `10.50.0.0/24`. Nothing swaps the container's private
source for the host's routable IP on the way out, so `conntrack` has no mapping to reverse and the reply
never appears.

**Root cause:** missing source NAT (lesson 3). Forwarding moves the packet, but without MASQUERADE the
private source leaks onto the public wire. **Fix:**

```bash
iptables -t nat -A POSTROUTING -s 10.50.0.0/24 -o "$UPLINK" -j MASQUERADE
ip netns exec app ping -c1 8.8.8.8      # now replies arrive
```

This is line-for-line the rule Docker writes for `docker0` and kube-proxy's node-egress path — the one
`MASQUERADE` that lets every container on a box reach the internet.

**Cleanup:**
```bash
kill %1 2>/dev/null
iptables -t nat -D POSTROUTING -s 10.50.0.0/24 -o "$UPLINK" -j MASQUERADE 2>/dev/null
ip netns del app
```

</details>

---

## Drill 2 — "Two containers on the same host can't reach each other"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Two namespaces are plugged into the same bridge, both have addresses in the same subnet,
> both interfaces show `UP` inside their namespace. But ns1 can't ping ns2 — no route error, it just
> times out. It's one switch and two cables; how is this not the simplest thing in the world?"*

**Reproduce it** (run; don't read):

```bash
ip netns add ns1
ip netns add ns2
ip link add br0 type bridge
ip link set br0 up
ip link add veth-a type veth peer name veth-a-c
ip link add veth-b type veth peer name veth-b-c
ip link set veth-a master br0
ip link set veth-b master br0
ip link set veth-a up
ip link set veth-a-c netns ns1
ip link set veth-b-c netns ns2
ip netns exec ns1 ip addr add 10.60.0.1/24 dev veth-a-c
ip netns exec ns2 ip addr add 10.60.0.2/24 dev veth-b-c
ip netns exec ns1 ip link set veth-a-c up
ip netns exec ns2 ip link set veth-b-c up
```

**Confirm the symptom:**

```bash
ip netns exec ns1 ip -br addr show veth-a-c     # UP, 10.60.0.1
ip netns exec ns2 ip -br addr show veth-b-c     # UP, 10.60.0.2
ip netns exec ns1 ping -c1 -W2 10.60.0.2 || echo "ns1 -> ns2: FAILED"
```

Both endpoints are up with the right addresses, on the same `/24` — and the ping still fails.

**Your move.** The addresses are right and the namespace-side interfaces are up, so this isn't IP and
isn't routing — the two are on one Layer-2 switch. A bridge only forwards a frame out a port that is
itself **up**. Every cable has two ends; you checked the ends *inside* the namespaces. Which ends
didn't you check?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Look at the *host-side* ends — the bridge's own ports:

```bash
ip -br link show veth-a        # host end of ns1's cable — UP
ip -br link show veth-b        # host end of ns2's cable — DOWN  ⟵
bridge link                    # veth-b listed, state disabled
```

The reproduce block brought up `veth-a` but **never brought up `veth-b`**. A veth is a cable with two
ends (lesson 2): the namespace end `veth-b-c` is up, but its partner `veth-b` — the port plugged into
the bridge — is down. The bridge will not forward a frame out a port that isn't up, so ns1's ARP for
`10.60.0.2` reaches the switch and dies there. The `fdb` confirms the bridge never learned ns2:

```bash
bridge fdb show br br0         # no entry pointing at veth-b
```

**Root cause:** one end of the cable left `DOWN` (lesson 2). The misleading part is that the
namespace's *own* view looks perfectly healthy — the fault is a port on the host side. **Fix:**

```bash
ip link set veth-b up
ip netns exec ns1 ping -c1 10.60.0.2       # now replies
bridge fdb show br br0                       # and the bridge has now learned both MACs
```

**Cleanup:**
```bash
ip netns del ns1; ip netns del ns2; ip link del br0
```

</details>

---

## Drill 3 — "The published service answers inside the container but nowhere else"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"The app is definitely running — `exec` into the container and `curl localhost:8080`
> returns 200 every time. But hitting the same port from the host gets `connection refused`. We didn't
> change the app. It's like the port publish just… didn't."*

**Reproduce it** (run; don't read):

```bash
ip netns add app
ip link add veth-h type veth peer name veth-a
ip link set veth-a netns app
ip addr add 10.70.0.1/24 dev veth-h
ip link set veth-h up
ip netns exec app ip addr add 10.70.0.2/24 dev veth-a
ip netns exec app ip link set veth-a up
ip netns exec app ip link set lo up
ip netns exec app python3 -m http.server 8080 --bind 0.0.0.0 >/tmp/app.log 2>&1 &
sleep 1
```

**Confirm the symptom:**

```bash
ip netns exec app curl -s -o /dev/null -w 'inside the ns -> %{http_code}\n' 10.70.0.2:8080
curl -s -o /dev/null -w 'from the host -> %{http_code}\n' --max-time 2 10.70.0.1:8080 \
  || echo 'from the host -> connection refused'
```

Inside the namespace the server answers `200`; from the host, the same port is refused.

**Your move.** The listener is real — it answered its own namespace. The refusal from the host is the
tell: *nobody on the host is listening on 8080, and nothing redirects a host-bound packet into the
namespace.* Which one command shows what the host itself has bound? And which table is supposed to
carry a host-port knock across the wall into the container?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

First, prove the host has no listener — the server lives in another namespace, invisible to a
host-local connect:

```bash
ss -tlnp | grep 8080 || echo "nothing on the HOST is bound to 8080"
```

The socket table the host can see is empty on 8080; the `python3` listener sits in the `app`
namespace's *own* socket table. A container port becomes reachable from outside only when a **DNAT**
rule rewrites the destination and sends the packet across (lesson 3) — exactly what `docker run -p
8080:8080` installs. Read the NAT table and it isn't there:

```bash
iptables -t nat -L OUTPUT -n -v        # no DNAT for dpt 8080
iptables -t nat -L PREROUTING -n -v    # nor here
```

**Root cause:** the port publish (a DNAT rule) is missing — the classic "`-p` never happened" (lesson
3). **Fix** — send host-originated traffic for `10.70.0.1:8080` on into the container:

```bash
iptables -t nat -A OUTPUT -p tcp -d 10.70.0.1 --dport 8080 -j DNAT --to-destination 10.70.0.2:8080
curl -s -o /dev/null -w 'from the host -> %{http_code}\n' 10.70.0.1:8080     # now 200
```

The reply finds its way back with no return rule, because `conntrack` recorded the rewrite when the
first packet crossed (lesson 3) — the same reason a Kubernetes Service answers in both directions from
a single DNAT rule.

**Cleanup:**
```bash
iptables -t nat -D OUTPUT -p tcp -d 10.70.0.1 --dport 8080 -j DNAT --to-destination 10.70.0.2:8080 2>/dev/null
pkill -f 'http.server 8080'; ip netns del app
```

</details>

---

## Drill 4 — "Small requests are fine, big responses hang forever"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Two namespaces, one cable, both ends up, both addresses in the same `/24` — and `ping`
> works. Small requests come back instantly. Anything that returns a big payload hangs until the client
> gives up. There is no error anywhere: nothing in the app log, no ICMP, no `unreachable`. Retrying
> changes nothing. It's the same cable the working requests go over."*

**Reproduce it** (run; don't read):

```bash
ip netns add mtu1
ip netns add mtu2
ip link add veth-m1 type veth peer name veth-m2
ip link set veth-m1 netns mtu1
ip link set veth-m2 netns mtu2
ip netns exec mtu1 ip addr add 10.80.0.1/24 dev veth-m1
ip netns exec mtu2 ip addr add 10.80.0.2/24 dev veth-m2
ip netns exec mtu1 ip link set veth-m1 up
ip netns exec mtu2 ip link set veth-m2 up
ip netns exec mtu2 ip link set veth-m2 mtu 1400
```

**Confirm the symptom:**

```bash
ip netns exec mtu1 ping -c1 -W2 10.80.0.2         && echo "small packets: OK"
ip netns exec mtu1 ping -c1 -W2 -s 1450 10.80.0.2 || echo "large packets: FAILED, silently"
```

The small ping replies. The large one produces no reply and no error at all.

**Your move.** Reachability is not the question — the small ping settled that. The only thing that
changed between the packet that arrived and the packet that didn't is its *size*. So find the one number
on an interface that a 64-byte ping never exercises and a 1450-byte one does. Then work out which side
of the wire the packet actually died on, and prove it by watching the sender's interface and the
receiver's drop counters at the same time.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Read that number on both interfaces:

```bash
ip netns exec mtu1 ip link show veth-m1     # mtu 1500
ip netns exec mtu2 ip link show veth-m2     # mtu 1400  ⟵ smaller
```

The sending side accepts a 1500-byte frame, so its kernel has nothing to object to — the packet is
perfectly legal *where it is created*, which is why no error ever appears there. It becomes illegal only
on arrival, and the receiving end discards any frame bigger than its own MTU before that frame is ever a
packet: at the link layer, beneath the layer that would generate an ICMP error. Nobody is told. Watch
both halves of that:

```bash
ip netns exec mtu1 tcpdump -ni veth-m1 -c 1 icmp &     # the sender's own wire
sleep 1
ip netns exec mtu1 ping -c1 -W2 -s 1450 10.80.0.2      # request goes out; no reply ever returns
ip netns exec mtu2 ip -s link show veth-m2             # RX … dropped, climbing
```

The request leaves. It is counted as dropped on the far side. Nothing in between says a word — this is
the black hole from [Act II's MTU lesson](../act-2-two-machines/03b-mtu-and-fragmentation.md), reproduced
on plumbing you built yourself.

**Root cause:** an MTU mismatch across one link (Act II's MTU, lesson 2's veth). **Fix** — make the path
agree. Either raise the small end:

```bash
ip netns exec mtu2 ip link set veth-m2 mtu 1500
ip netns exec mtu1 ping -c1 -s 1450 10.80.0.2      # replies now
```

— or, when the small link is not yours to raise (a VPN, a cloud interconnect, an overlay's underlay),
lower the *sending* interface instead. That is precisely what
[Overlay and VXLAN](04-overlay-vxlan.md) does when it sets a tunnel's MTU to the path's smallest MTU
minus the encapsulation overhead. In a cluster, that one number decides whether large Pod-to-Pod
responses arrive at all.

**Cleanup:**
```bash
kill %1 2>/dev/null
ip netns del mtu1; ip netns del mtu2
```

</details>

---

## Where this leaves you

Four failures, four primitives, one method: meet a bare symptom, decide *which* piece of hand-built
plumbing is missing or misconfigured, and read the one file, rule or counter that proves it — a private
source escaping onto the wire because no `MASQUERADE` caught it; a bridge port left down so frames die at
the switch; a published port that was never a DNAT rule at all; a link whose size nobody agreed on, which
fails only for packets big enough to matter. Nobody told you which idea applied; you ranged across the
whole act to find it. Every one of these is a bug you will meet again in Act V wearing a Kubernetes name —
a node that can't egress, a Pod unreachable on its node, a Service that resolves but never answers, an
overlay that delivers health checks and swallows real responses.

---

← **[Test yourself](test-yourself.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Act V — Kubernetes](../act-5-kubernetes/README.md)** →
