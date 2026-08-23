# Act II — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act II. This checks whether you can *use* it. Real
failures never arrive labelled "this is an ARP bug" or "that's a route" — they arrive as a symptom, a
shrug, and a ticket. Each drill below puts your machine into a **real broken state** (not a story),
hands you only the symptom, and asks you to find the cause with the act's tools.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** If you read it closely you'll spoil the
   hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud what you think is wrong and which file or
   tool would prove it — *then* look.
3. **Open the reveal only after you've tried.**

**Where:** inside the lab container, with the host's real network attached:

```bash
docker run --rm -it --privileged --network host --name lab nicolaka/netshoot
```

**Read this before you run anything.** `--network host` means the container has no network namespace of
its own — it is *in the host's*. There is no separate "container view of the network" here to play with.
So every drill below changes the host's real networking, and `exit` undoes none of it: Drill 1 writes a
permanent wrong ARP entry for the real gateway, Drill 2 adds a real blackhole route, Drill 3 lowers the
real interface's MTU. (`--privileged` is what makes all three possible.)

Three rules follow, and they are not optional:

1. **Run each drill to its end, including its `Cleanup` block.** The cleanup sits directly under the
   drill, outside the reveal, so you cannot miss it. Stop halfway and you leave the machine broken.
2. **One drill at a time.** Clean up before starting the next, so a symptom is never two faults at once.
3. **On a Linux host, use a throwaway VM.** There, "the host" is the machine you are sitting at: that is
   its real ARP cache, its real routing table, its real MTU, and the changes outlive the container. On
   macOS with Docker Desktop "the host" is Docker's own Linux VM, so the damage is confined to that VM
   and restarting Docker Desktop resets it — but it is still a live network you are breaking, so treat it
   the same way.

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

## Drill 1 — "Internet's down, but the machine looks perfectly healthy"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"This box can't reach anything outside the LAN — every external ping times out. But the
> interface is up, the IP is right, the cable's fine, nothing changed in the routing. It's like the
> gateway just stopped existing."*

**Reproduce it** (run; don't read):

```bash
GW=$(ip route show default | awk '{print $3}')
ip neigh replace "$GW" lladdr de:ad:be:ef:00:01 dev eth0 nud permanent
```

**Confirm the symptom:**

```bash
ip addr show eth0 | grep 'inet '      # IP is present and correct
ip route show default                  # default route is present and correct
ping -c1 -W2 8.8.8.8 || echo "external ping: FAILED"
```

The address is fine, the route is fine, yet the ping fails. Everything Layer 3 looks right.

**Your move.** The IP layer is healthy and the route points at the gateway — so the failure must be one
layer *down*, in how the gateway's IP becomes a MAC on the wire. Which single file holds that mapping,
and what does it say about the gateway right now?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
ip neigh show | grep "$(ip route show default | awk '{print $3}')"
```

```
192.168.65.1 dev eth0 lladdr de:ad:be:ef:00:01 PERMANENT
```

The gateway resolves to a **bogus MAC**, and it's marked `PERMANENT` — not a normal dynamically learned
`REACHABLE`/`STALE` entry. Every frame for the outside world is being addressed to a hardware address
that doesn't exist on the wire, so it leaves and is never heard from again. The IP and route are
innocent; the translation underneath them (the ARP cache, from the first lesson) is poisoned.

**Root cause:** a wrong static ARP entry for the gateway — exactly the *effect* an ARP-spoofing attacker
produces (lesson 1's shadow), here done to ourselves. **Fix:** delete the bad entry and let the kernel
re-ARP for the real MAC.

</details>

### ⚠ Cleanup — Drill 1, run this now before starting the next drill

```bash
ip neigh del "$(ip route show default | awk '{print $3}')" dev eth0
ping -c1 -W2 8.8.8.8 && echo "recovered"
```

---

## Drill 2 — "One particular service is unreachable; everything else is fine"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"We can reach the whole internet — except one provider's API range. Pings to `8.8.8.8`
> time out, but `1.1.1.1` is instant. Same machine, same interface, same gateway. How can one
> destination be dead and the next one alive?"*

**Reproduce it** (run; don't read):

```bash
ip route add blackhole 8.8.8.0/24
```

**Confirm the symptom:**

```bash
ping -c1 -W2 1.1.1.1 && echo "1.1.1.1: OK"
ping -c1 -W2 8.8.8.8 || echo "8.8.8.8: FAILED"
```

`1.1.1.1` answers; `8.8.8.8` fails with `Network is unreachable`. One destination, singled out.

**Your move.** The gateway works (1.1.1.1 proves it), so this isn't ARP. Something is making the kernel
treat *this one destination* differently. Which command shows you the exact route the kernel will pick
for a given destination — and what decides which route wins when several could match?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
ip route get 8.8.8.8
ip route get 1.1.1.1
```

```
8.8.8.8 dev lo  ...  (blackhole / unreachable)
1.1.1.1 via 192.168.65.1 dev eth0 ...
```

`8.8.8.8` matches a `blackhole 8.8.8.0/24` route while `1.1.1.1` falls through to the default. Look at
`ip route show`: both `0.0.0.0/0` (the default) *and* `8.8.8.0/24` match `8.8.8.8` — and the `/24` wins
by **longest-prefix match** (lesson 2), because a more specific route always beats the default,
regardless of order. A single more-specific route silently swallowed one destination.

**Root cause:** an overly specific route (here a `blackhole`; in the wild, a leaked or fat-fingered
route, or a bad BGP announcement from lesson 2b) winning the longest-prefix match for that range.
**Fix:** remove it and let the default take over again.

</details>

### ⚠ Cleanup — Drill 2, run this now before starting the next drill

```bash
ip route del blackhole 8.8.8.0/24
ping -c1 -W2 8.8.8.8 && echo "recovered"
```

---

## Drill 3 — "SSH connects, then freezes; small requests work, big ones hang"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Login works, short commands work, but the moment a command prints a lot of output the
> session just freezes. `curl` of a small endpoint is fine; downloading anything large stalls forever.
> No errors anywhere. It 'works' just enough to be confusing."*

**Reproduce it** (run; don't read):

```bash
ip link set eth0 mtu 1300
```

**Confirm the symptom:**

```bash
ping -c1 -M do -s 1100 8.8.8.8 && echo "small (1100): OK"
ping -c1 -M do -s 1472 8.8.8.8 || echo "large (1472): FAILED"
```

The small packet goes; the 1472-byte one (fine on a normal 1500 link) now fails. Small works, big hangs
— the ticket's whole story in two pings.

**Your move.** Connections *open* and small payloads pass, so addressing and routing are correct — the
problem is *size*. Which integer file on the interface caps how big a packet can be, and what is it set
to now?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

```bash
cat /sys/class/net/eth0/mtu
```

```
1300
```

The link MTU is **1300**, not the usual 1500 (lesson 3b). A DF packet bigger than 1300 can't be
forwarded and can't be fragmented, so it's dropped — and if the ICMP "fragmentation needed" that would
tell the sender to shrink is lost or blocked, the sender keeps firing oversized packets into a hole.
That's the **MTU black hole**: the handshake's small packets succeed, so the connection *opens*, then
the first large transfer vanishes silently. Confirm the boundary by hand:

```bash
ping -c1 -M do -s 1272 8.8.8.8   # 1272 + 8 + 20 = 1300 — the largest that fits
ping -c1 -M do -s 1273 8.8.8.8   # one over — fails
```

**Root cause:** path MTU smaller than the packets being sent (here a misconfigured interface; in the
real world, an overlay or VPN's encapsulation overhead — the exact trap Act IV will spring).
**Fix:** restore the correct MTU (or lower the sender's to match the path).

</details>

### ⚠ Cleanup — Drill 3, run this now before starting the next drill

```bash
ip link set eth0 mtu 1500
cat /sys/class/net/eth0/mtu       # must read 1500 again
```

---

## Drill 4 — "The name resolves to the wrong server, and DNS swears it's right"

**Target: 5 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Our app keeps talking to the wrong backend for `example.com`. But when the network team
> runs `dig example.com` they get the correct address and tell us DNS is fine. Both can't be right — so
> who's lying?"*

**Reproduce it** (run; don't read):

```bash
echo "1.2.3.4 example.com" >> /etc/hosts
```

**Confirm the symptom.** One new tool here: **`getent hosts <name>`** resolves a name the way an
*application* would — it calls into the same libc stub resolver your program does, obeying whatever
`/etc/nsswitch.conf` says, rather than querying a nameserver directly. It is the closest thing to "what
would my app see?" that you can type:

```bash
getent hosts example.com           # what the application's resolver returns
dig +short example.com             # what DNS itself returns
```

`getent` (and your app) says `1.2.3.4`; `dig` says the real public address. The two disagree.

**Your move.** `dig` and the application are asking the *same* DNS — so why do they get different
answers? The difference isn't in DNS at all; it's in *what each tool consults first*. Which file decides
the order, and which source is winning?

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

`dig` queries a DNS server directly. The application calls the **libc resolver**, which obeys
`/etc/nsswitch.conf` — whose `hosts:` line reads `files dns` (lesson 4), so it checks `/etc/hosts`
*before* ever asking DNS:

```bash
grep '^hosts:' /etc/nsswitch.conf      # files dns  -> local file wins
grep example.com /etc/hosts            # 1.2.3.4 example.com   <- the override
```

A stale `/etc/hosts` entry is overriding the global database for the app, while `dig` — which bypasses
the file — sees the truth. Neither tool is lying; they consult different sources, and the local file
wins for everything that goes through libc.

**Root cause:** a leftover `/etc/hosts` override (lesson 4) — the same mechanism that makes a fake name
resolve, used by accident. In a Pod this is the "name resolves to the wrong place" failure exactly.
**Fix:** remove the stale line.

</details>

### ⚠ Cleanup — Drill 4, run this now

```bash
sed -i '/1.2.3.4 example.com/d' /etc/hosts
getent hosts example.com          # must agree with dig again
```

---

## Where this leaves you

Four failures, four layers, one method: meet a bare symptom, decide *which* layer it lives in, and open
the one file that proves it — a poisoned ARP entry under a healthy IP; a more-specific route swallowing
one destination; an MTU that lets small packets through and eats big ones; a local file quietly
overruling global DNS. Nobody told you which idea applied; you ranged across the whole act to find it.
That is the on-call skill the act was building toward.

Everything here assumed the wire either delivered your packet or didn't. Act III confronts the harder
truth: across many networks, packets are dropped, reordered, and duplicated as a matter of course — and
something has to turn that mess back into a reliable, ordered, private conversation.

---

← **[Test yourself](test-yourself.md)** · ↑ **[Act II overview](README.md)** · Next: **[Act III →](../act-3-the-internet/README.md)**
