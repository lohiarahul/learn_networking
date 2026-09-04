# iptables — the five hooks

The last lesson left a promise unpaid. You built a cable, then a switch, and `ns1` could reach the host and its neighbours — but its *Check yourself* asked whether `ping 8.8.8.8` would work from in there, and the answer named three separate things that were missing. One was a route. One was the host's willingness to pass a packet that is neither from it nor for it. The third was the killer: a packet leaving with the source address `10.20.0.2` is a packet no router on earth can reply to.

This lesson pays two of those three, and then walks you up to the wall the third one is behind. By the end of it you will have a namespace whose packets reach the real internet's doorstep and die there, in front of you, for a reason you can point at on a diagram — and you will know the exact place in the kernel where you are allowed to do something about it.

### Take stock — four objects, and two tables you have never opened

Before building anything, look at what you already own. Every lesson in this act has made a kernel object and read it back out of a file, and the whole set is inspectable with commands you have had since Act II:

| What you built | Made with | Read it back with | Introduced in |
|---|---|---|---|
| a network namespace | `ip netns add ns1` | `ip netns list`; `/proc/<pid>/ns/net` | [Namespaces](01-namespaces.md) |
| a virtual cable | `ip link add … type veth peer name …` | `ip link show`; `/sys/class/net/<if>/iflink` | [veth and bridge](02-veth-and-bridge.md) |
| a software switch | `ip link add br0 type bridge` | `ip link show type bridge`; `ls /sys/class/net/br0/brif/` | [veth and bridge](02-veth-and-bridge.md) |
| what the switch learned | nobody — the kernel fills it in | `bridge fdb show br br0` | [veth and bridge](02-veth-and-bridge.md) |
| an address, and the route it implies | `ip addr add 10.20.0.1/24 dev br0` | `ip addr show`; `ip route`; `ip route get <dst>` | [Act II — IP and routing](../act-2-two-machines/02-ip-and-routing.md) |

Start the lab and survey it. **Note the absence of `--network host` this time** — that is deliberate and it is the single most important line on this page. A plain `--privileged` container gets its *own* network namespace, so everything below happens on a clean slate that no Docker daemon, no `kind` cluster and no half-cleaned-up previous lesson has ever touched, and `exit` destroys all of it:

```bash
docker run --rm -it --privileged --name gw nicolaka/netshoot
```

```bash
ip -brief addr show                 # every interface and its addresses, one line each
ip route                            # the routing table
ip route get 1.1.1.1                # which of those routes actually wins for one destination
ip link show type bridge            # bridges: none yet
iptables -t nat    -S               # the two tables this lesson is about
iptables -S
```

`-brief` is new and it is only a formatting flag — the same `ip addr` you have used since Act II, one line per interface instead of three. Read what comes back:

```
lo               UNKNOWN        127.0.0.1/8 ::1/128
tunl0@NONE       DOWN
gre0@NONE        DOWN
...
eth0@if363       UP             172.17.0.2/16
```

```
default via 172.17.0.1 dev eth0
172.17.0.0/16 dev eth0 proto kernel scope link src 172.17.0.2
```

```
-P PREROUTING ACCEPT        ← iptables -t nat -S
-P INPUT ACCEPT
-P OUTPUT ACCEPT
-P POSTROUTING ACCEPT

-P INPUT ACCEPT             ← iptables -S
-P FORWARD ACCEPT
-P OUTPUT ACCEPT
```

This is a whole small machine, and it is *empty*. One real interface with one address, one default route, no bridges. The `tunl0`/`gre0`/`sit0` entries are down and address-less — kernel tunnel modules that exist on every Linux box whether or not anybody wants them, not things somebody made. And the last two commands are the point of the survey: **`-S` prints the rules in a table, and both tables have none.** Three lines in `filter`, four in `nat`, every one of them a `-P` — a *policy*, which you will meet properly in a moment. Not one actual rule. Whatever `iptables` turns out to be, you are starting from nothing, which means every line that appears in there for the rest of this lesson is one you put there.

That is what reading a live Docker host cannot offer, and it is worth being blunt about why: on a working machine that same command prints a column of `MASQUERADE` lines you did not write, on bridges you did not make, for containers you may not be running. **You cannot learn a mechanism from a ruleset you did not build.** We come back for that column two lessons from now, once it is recognition rather than noise.

### The gateway that is not one yet

Rebuild the minimum from the last lesson — one bridge, one namespace, one cable — and this time give the namespace what its *Check yourself* said it lacked.

```bash
ip netns add ns1
ip link add br0 type bridge
ip addr add 10.20.0.1/24 dev br0
ip link set br0 up
ip link add veth-a type veth peer name veth-a-c
ip link set veth-a master br0
ip link set veth-a up
ip link set veth-a-c netns ns1
ip netns exec ns1 ip addr add 10.20.0.2/24 dev veth-a-c
ip netns exec ns1 ip link set veth-a-c up
ip netns exec ns1 ip link set lo up
```

Eleven lines, and every one of them is lesson 02's. Confirm the picture is the one you think it is, from both sides of the wall:

```bash
ip -brief addr show br0
ls /sys/class/net/br0/brif/
ip netns exec ns1 ip -brief addr show
ip netns exec ns1 ip route
```

`br0` holds `10.20.0.1/24`, `brif/` holds `veth-a`, and inside `ns1` there is `veth-a-c` with `10.20.0.2/24` and exactly one route — the `10.20.0.0/24` line that `ip addr add` installed for free. Now try the thing the last lesson asked about.

> **Predict first —** `ns1` has an address, a cable, a switch, and a host on the far side of it with working internet. Run `ping 1.1.1.1` from `ns1`. It will fail. **Name the error message you expect**, and be specific about one thing: does the packet leave `ns1` at all?

```bash
ip netns exec ns1 ping -c1 -W2 1.1.1.1 ; echo "exit=$?"
```

```
ping: connect: Network unreachable
exit=2
```

**Instant, and it never left.** That is not a timeout — nothing was sent. `ns1`'s own routing table has one entry, for `10.20.0.0/24`, and `1.1.1.1` is not in it, so `ns1`'s kernel had nowhere to send the packet and refused before a byte hit the wire. This is Act II's routing table doing exactly what Act II said it does, now inside a namespace of its own. Fix it the way Act II taught:

```bash
ip netns exec ns1 ip route add default via 10.20.0.1
ip netns exec ns1 ip route
ip netns exec ns1 ping -c2 -W2 1.1.1.1 ; echo "exit=$?"
```

```
2 packets transmitted, 0 received, 100% packet loss, time 1050ms
exit=1
```

A **completely different failure**, and the change is the whole lesson in miniature. No error, no refusal, no message — two seconds of nothing and a summary line. The packet was accepted by `ns1`'s routing table, handed down the cable to `br0`, and then something happened to it that nobody reported to anybody.

You now have two suspects and no way to choose between them. Either this host is refusing to pass a packet that is not addressed to it, or it is passing it perfectly and the *reply* is what never came. **Those two produce identical output.** Go and look.

> **Predict first —** take the first suspect, because it has a switch you can read. A host that forwards other people's packets is doing a different job from a host that only sends its own, and Linux keeps that as a setting. Guess whether it is on or off in this container before you read it.

```bash
sysctl net.ipv4.ip_forward
```

```
net.ipv4.ip_forward = 1
```

**Already on** — Docker turns it on, because a container host that could not forward would be useless. So the first suspect is eliminated without being fixed, which is an honest outcome and not a wasted step: you now know the switch exists, what it is called, and that it is not today's problem. Prove it is the switch it claims to be by turning it *off* and watching the failure change shape. Watch the uplink while you do it — `eth0` is the only way out of this machine, so if the packet is being forwarded it has to appear there:

```bash
sysctl -qw net.ipv4.ip_forward=0
timeout 4 tcpdump -i eth0 -n icmp &
sleep 1
ip netns exec ns1 ping -c2 -W1 1.1.1.1 >/dev/null 2>&1
wait
```

```
0 packets captured
```

**Nothing.** Not a dropped reply — the packet never reached the uplink at all. With forwarding off, the host took delivery of a packet addressed to `1.1.1.1`, noticed it was not for itself, and discarded it silently. Put it back and look again:

```bash
sysctl -qw net.ipv4.ip_forward=1
timeout 4 tcpdump -i eth0 -n icmp &
sleep 1
ip netns exec ns1 ping -c2 -W1 1.1.1.1 >/dev/null 2>&1
wait
```

```
04:37:24.328898 IP 10.20.0.2 > 1.1.1.1: ICMP echo request, id 33, seq 1, length 64
04:37:25.378919 IP 10.20.0.2 > 1.1.1.1: ICMP echo request, id 33, seq 2, length 64
2 packets captured
```

**There it is, and there is the problem, printed in the first column.** The packet is leaving this machine — forwarding works, the bridge works, the cable works, the route works — and it is leaving with the source address `10.20.0.2`. That address exists nowhere except inside a namespace on this box. Cloudflare will receive that packet, compose a perfectly good reply, address it to `10.20.0.2`, and hand it to the internet, which has no idea such a place exists. The reply is not slow. It is not blocked. **It was never deliverable.**

Two identical silences, one on each side of a `sysctl`, told apart only by putting `tcpdump` on the wire — that is what the last lesson's *Check yourself* meant by "three different subsystems," and you have now felt all three. Two are fixed. The third cannot be fixed by routing, by switching, or by any setting, because nothing in the packet is *wrong*: the packet is a truthful report of where it came from, and the truth is unroutable. **The address itself has to change on the way out, and change back on the way in.**

So the question the last lesson ended on is now yours, sharpened: what in the kernel is even *allowed* to edit a packet mid-flight, and where in a packet's journey does it get to stand?

### netfilter — the kernel's packet processing hooks

**The problem that made this necessary** — As soon as Linux was carrying other people's packets — for firewalls, for address rewriting, for accounting — it needed a way to let administrators *intervene* at well-defined points in a packet's journey, without patching and recompiling the kernel. The answer, the **netfilter** framework (late 1990s, exposed to users as `iptables`), was a set of fixed hooks bolted onto the packet path: places where the kernel stops, consults a list of rules you wrote, and does what they say. The mental trap is thinking iptables is "a firewall." It isn't. It is a framework for attaching match-and-act rules to specific points in the kernel's packet flow; a firewall is one of several things you can build with it, and the thing you need today is not that one.

**What it actually is** — There are five hooks, each a point in the packet's path. You have already watched a packet pass through three of them without knowing their names:

- **PREROUTING** — the packet just arrived, *before* the kernel decides where it goes.
- **INPUT** — the routing decision said "this is for me, locally."
- **FORWARD** — the routing decision said "this is passing through me to somewhere else." *This is the hook your `ns1` packet walked, and the one that `ip_forward=0` stopped it ever reaching.*
- **OUTPUT** — a packet originating from a local process, heading out.
- **POSTROUTING** — about to leave the machine, *after* the routing decision.

At each hook you write rules that match on any field you like — source and destination address, port, protocol, interface — and then `ACCEPT` the packet, `DROP` it, or **rewrite** it.

**Draw it** — the five hooks, and the routing decision that chooses between them:

<!-- figure: iptables-hooks -->

```
   packet                                                          packet
   arrives                                                          leaves
     │                                                                ▲
     ▼                                                                │
 ┌────────────┐     ┌──────────┐                          ┌─────────────┐
 │ PREROUTING │ ──▶ │ routing  │                          │ POSTROUTING │
 └────────────┘     │ decision │                          └─────────────┘
                    └────┬─────┘                                 ▲
          ┌──────────────┴───────────────┐                        │
          ▼ "for me"                      ▼ "for someone else"    │
     ┌─────────┐                     ┌──────────┐                 │
     │  INPUT  │ ─▶ local process    │ FORWARD  │ ────────────────┤
     └─────────┘                     └──────────┘                 │
                                                                  │
     local process ──────────────────▶  ┌────────┐ ──────────────┘
                                        │ OUTPUT │
                                        └────────┘

  The routing decision is the fork, and it is why there are three middle
  hooks rather than one. A packet visits exactly one of INPUT, FORWARD or
  OUTPUT — never two — and which one is a fact about the packet, not a
  choice you make.

  Your ns1 ping took:   PREROUTING → routing → FORWARD → POSTROUTING
  A curl from this box: OUTPUT → POSTROUTING, and the reply comes back
                        PREROUTING → routing → INPUT
```

### Tables and chains are two different questions

Go back to the survey for a second, because something in it needed two commands and should not have. `iptables -t nat -S` and `iptables -S` both printed a short list of `-P` lines, and they printed *different* lists — four names against three. One machine, one ruleset, two answers. Why was that two commands? Because a table and a chain are not a hierarchy. **They are two independent axes, and a rule lives where they cross.**

- A **hook** answers ***when***: at which of five points in the packet's journey the kernel stops to look. Five, fixed, kernel-owned. You cannot add one.
- A **table** answers ***what***: which kind of edit the rules in it are allowed to perform — decide the packet's fate, rewrite its addresses, tag it, and so on. Also five, also fixed.
- A **chain** is the actual list of rules sitting at **one (table, hook) intersection**.

Which makes every `iptables` command you are about to write the same five-part shape. Worth reading once slowly, because it is also the whole flag vocabulary of this act:

```
  iptables  -t filter  -A  FORWARD  -s 10.20.0.0/24  -j DROP
            └────┬───┘ └┬┘ └───┬──┘ └───────┬──────┘ └───┬──┘
               table    │    chain        match        target
                        │
                  what to do to that list:
                    -A  append a rule to the end        -D  delete a rule
                    -I  insert at a position            -Z  zero the counters
                    -S  show it as the rules that would recreate it
                    -L  list it (add -n numeric, -v counters, --line-numbers)
                    -P  set the chain's policy

  -t  picks the table, and **defaults to `filter`** — which is why most
      people never notice the flag exists, and why the rules that are
      actually rewriting their packets are invisible to them.

  -j  is "jump": where the packet goes when the match hits. ACCEPT and DROP
      are *verdicts*, and a verdict ends the packet's walk through the table.
      Something that is not a verdict can also go here — hold that thought.
```

Two of those are new to you (`-Z` and `-S`); the rest you will meet as you need them. If you would rather work a command out than look one up, [the grammar](../../reference/01-the-grammar.md) is the page that teaches the shape of any command in this course, and [the map](../../reference/03-the-map.md) ties each tool to the kernel state it reads.

The confusing part of the three-part vocabulary above is a naming accident: a chain is *named after its hook* but *belongs to its table*. So `filter`'s `INPUT` and `nat`'s `INPUT` are two entirely different lists that happen to share a name, both walked at the same moment, holding different rules and keeping separate counters. Prove it rather than believing it — write what looks like the same rule twice and then delete it from one place:

```bash
iptables -t filter -A INPUT -d 10.99.0.7 -j ACCEPT
iptables -t nat    -A INPUT -d 10.99.0.7 -j ACCEPT
iptables -t filter -S INPUT
iptables -t nat    -S INPUT
```

Both print `-A INPUT -d 10.99.0.7/32 -j ACCEPT`, identical, and they are not the same rule:

```bash
iptables -t filter -D INPUT -d 10.99.0.7 -j ACCEPT
iptables -t filter -S INPUT      # gone
iptables -t nat    -S INPUT      # still there
```

**One deletion, one survivor.** `-t` is not a display filter — it is part of the address of the rule. So run the command everybody runs, with no `-t` at all, and say what it is *not* showing you:

```bash
iptables -L -n
```

Your surviving `nat` rule is nowhere in that output, and nothing in it says so. `-L` with no `-t` shows you `filter` and only `filter` — one row of a grid you are about to see — which is worth remembering the next time a machine is plainly rewriting your packets and "the firewall" looks empty.

And because it is a grid, some cells are simply empty — not empty lists, *absent*:

```bash
iptables -t filter -S PREROUTING ; echo "exit=$?"
iptables -t nat    -S FORWARD    ; echo "exit=$?"
```

```
iptables: No chain/target/match by that name.
exit=1
```

Both fail. There is no such thing as a `filter PREROUTING` chain or a `nat FORWARD` chain, and the next section is about why those particular holes are exactly where they should be. (The `-P` lines you keep seeing in this output are the chain **policies**: the verdict applied to a packet that reaches the end of a chain with no rule having decided it. A policy belongs to one chain in one table, like everything else here.)

Clean up the two demonstration rules before moving on:

```bash
iptables -t nat -D INPUT -d 10.99.0.7 -j ACCEPT
```

One caution about the word *chain*, because you will meet an apparent violation of what I just said within two lessons. Every chain you have read so far is a **built-in** chain: it is named after a hook, the kernel calls it, and it has a policy. Nothing stops you — or a program — from creating an extra, *named* list of rules and jumping into it from one of the five. Those have no hook and no policy, and `-L` tells you which kind you are looking at: a built-in chain prints `(policy ACCEPT)`, a named one prints `(2 references)`. So when you eventually run `iptables -t nat -L DOCKER` and find a chain named after a product, in a kernel with exactly five hooks and no `DOCKER` among them, that is what you are looking at. Sit with the question it raises — *what happens to a packet that jumps somewhere and is not decided there?* — because it has two possible answers with very different consequences, and [the stateful firewall](03c-the-stateful-firewall.md) has you build one to find out which.



### The five tables, and why the grid has holes in it

The `-t` flag has been sitting in every command on this page and it takes five values. Rather than being told which, ask each table what chains it has — a table only *gets* a chain at a hook where its job makes sense, so the answer is also the explanation:

```bash
for t in filter nat mangle raw security; do
  printf '%-9s ' "$t"
  iptables -t $t -S | grep '^-P' | awk '{print $2}' | tr '\n' ' '
  echo
done
```

```
filter    INPUT FORWARD OUTPUT
nat       PREROUTING INPUT OUTPUT POSTROUTING
mangle    PREROUTING INPUT FORWARD OUTPUT POSTROUTING
raw       PREROUTING OUTPUT
security  INPUT FORWARD OUTPUT
```

That output *is* the grid. Drawn out, with the hooks in the order a packet meets them:

<!-- figure -->

```
                 PREROUTING   INPUT   FORWARD   OUTPUT   POSTROUTING
   raw               ●                              ●
   mangle            ●          ●         ●         ●          ●
   nat               ●          ●                   ●          ●
   filter                       ●         ●         ●
   security                     ●         ●         ●
                     ┆          ┆         ┆         ┆          ┆
        read a COLUMN and you are looking at several tables
        sitting at ONE hook — so in what order do they run?

   ● = a chain exists at this (table, hook) pair, and a rule can live there
       17 of 25 cells filled; the 8 blanks are not accidents — see the table below

   `iptables -L` with no -t shows you ONE ROW of this grid (filter).
```

Five tables, one verb each, and the gaps are the interesting part:

| Table | Its verb | Where it has chains, and why |
|---|---|---|
| **`filter`** | *decide* — accept or drop | The three post-fork hooks only. Filtering is a question about **whose** packet this is, and before the routing decision nobody knows yet. This is where a firewall lives. |
| **`nat`** | *rewrite* — change an address | Both ends, plus the two local hooks — but **not `FORWARD`**. Rewriting is worth doing at the moment a packet arrives or the moment it leaves; editing it halfway through a transit it is already committed to would change nothing. |
| **`mangle`** | *annotate* — alter or tag fields | **All five.** It is the only table with a chain at every hook, because marking a packet is useful anywhere. Its verb is neither of the two above, which is why it is easy to miss and why it gets a section of its own in [When NAT runs out](03d-when-nat-runs-out.md). |
| **`raw`** | *exempt* — decide before conntrack | Only the two hooks where a packet **enters** netfilter. That is its entire identity: `raw` runs before connection tracking does, so it is the only place you can say something about a packet before the kernel starts keeping a record of it. What you would say there is also [When NAT runs out](03d-when-nat-runs-out.md)'s business. |
| **`security`** | *label* — tag a packet for a security model | The same three hooks as `filter`, and in practice you will never write in it: it belongs to a whole access-control system that Act X meets properly. On the overwhelming majority of machines it is an empty table you see in a `-t` listing and nowhere else. |

**This lesson lives entirely in `filter` and `nat`, and those two carry almost every rule you will ever meet** — including all of Docker's and all of Kubernetes'. `mangle` and `raw` are real and you will build with both, two lessons from now, once you have hit the problems that make anyone want them. `security` is named here so that the five is a closed set rather than a hand-wave.

One more thing follows from the grid, and it answers a question you would otherwise have to guess at: **several tables have a chain at the same hook, so which runs first?** The order is fixed — `raw`, then `mangle`, then `nat`, then `filter` — and it is not arbitrary. Exempt from tracking before you tag; tag before you translate; translate before you decide, because a firewall should be judging the address the packet is really going to. You can read that order out of the kernel rather than memorising it, but the command that prints it belongs to [a later lesson](03b-reading-a-ruleset-you-did-not-write.md) and so does the reason it is spelled the way it is.

**The file** — and here, for the second time in this act, the creed does not hold, in a way worth stopping on. The rules are not in `/proc`. Check for yourself, after writing a rule so there is definitely something to find:

```bash
iptables -A FORWARD -s 10.20.0.9 -j DROP
iptables -S FORWARD
cat /proc/net/ip_tables_names ; echo "[end of file]"
wc -c < /proc/net/ip_tables_names
```

```
-P FORWARD ACCEPT
-A FORWARD -s 10.20.0.9/32 -j DROP
[end of file]
0
```

**A file with exactly the right name, readable, and empty — zero bytes — while `iptables` shows you the rule it is supposed to describe.** That is a stranger result than "there is no file," and it is a genuine loose thread rather than a tidy lesson: something in this kernel still publishes that filename, and whatever `iptables` just wrote to did not go there. Hold on to it. [Reading a ruleset you did not write](03b-reading-a-ruleset-you-did-not-write.md) pulls on that thread and finds something underneath that changes how much you trust the `iptables` command itself.

For now, the practical half: the ruleset lives in kernel memory, and the only door in is a **netlink** query — exactly the situation you met one lesson ago with the bridge's learned MAC table, which also had no file and also needed its own command (`bridge`) to ask the kernel directly. `iptables` is that command for the ruleset. Which means the rule you just wrote has no `cat`-able ground truth to check it against, and that puts unusual weight on the one form of evidence netfilter does hand you for free. Delete the throwaway rule and go find it:

```bash
iptables -D FORWARD -s 10.20.0.9 -j DROP
```

### Which hook did the packet actually walk?

Every rule carries two counters — packets and bytes matched — and `-v` prints them. That turns a chain into an instrument: instead of believing a diagram about where your packet went, leave a marker at each hook and read which ones it tripped.

Set three, one per `filter`-table chain. Each is an `ACCEPT`, and each is deliberately a **no-op** — the policies are already `ACCEPT`, so these rules change the fate of nothing and exist purely to be counted:

```bash
iptables -A INPUT   -s 10.20.0.0/24 -j ACCEPT
iptables -A FORWARD -s 10.20.0.0/24 -j ACCEPT
iptables -A OUTPUT  -d 1.1.1.1      -j ACCEPT
iptables -Z
iptables -L -n -v --line-numbers
```

`-Z` zeroes every counter, which is what makes the next reading mean only what it claims to: without it you are looking at a total that started accumulating before you were watching. Everything reads `0`.

> **Predict first —** two experiments are coming. First a `ping` from **inside `ns1`**, then a `curl` from **this container's own shell**. For each, say which of the three counters moves. Do not answer "the relevant ones" — commit to three numbers per experiment, including the zeros, and be ready to be wrong about which chain a *reply* arrives on.

```bash
ip netns exec ns1 ping -c2 -W2 1.1.1.1 >/dev/null 2>&1
iptables -L -n -v --line-numbers | grep -E "Chain|ACCEPT"
```

```
Chain INPUT (policy ACCEPT 0 packets, 0 bytes)
1        0     0 ACCEPT     all  --  *      *       10.20.0.0/24         0.0.0.0/0
Chain FORWARD (policy ACCEPT 0 packets, 0 bytes)
1        2   168 ACCEPT     all  --  *      *       10.20.0.0/24         0.0.0.0/0
Chain OUTPUT (policy ACCEPT 0 packets, 0 bytes)
1        0     0 ACCEPT     all  --  *      *       0.0.0.0/0            1.1.1.1
```

`FORWARD`'s rule has **2 packets, 168 bytes**. `INPUT` and `OUTPUT` are untouched, and they are untouched for a reason you can now state precisely: those two packets were not for this machine and were not from it.

Note also that `FORWARD`'s *policy* counter reads zero while its rule reads two. That is not a contradiction — a policy only counts packets that reach the end of a chain with no rule having decided them, and yours decided them. (And nothing came *back*: there are two echo requests here and no replies, because the reply is still undeliverable. That is a fact you will see change in one line, next lesson.)

Do not be thrown if a **policy** line on some other chain shows a stray packet or two that you cannot account for. Those numbers count everything the machine does, and a container is never completely silent. It is the numbers on *your rules* that are the measurement here, because you chose what they match. Now the other case, on the same three markers:

```bash
iptables -Z
curl -s -o /dev/null -m 5 http://1.1.1.1
iptables -L -n -v --line-numbers | grep -E "Chain|ACCEPT"
```

```
Chain INPUT (policy ACCEPT 5 packets, 732 bytes)
1        0     0 ACCEPT     all  --  *      *       10.20.0.0/24         0.0.0.0/0
Chain FORWARD (policy ACCEPT 0 packets, 0 bytes)
1        0     0 ACCEPT     all  --  *      *       10.20.0.0/24         0.0.0.0/0
Chain OUTPUT (policy ACCEPT 6 packets, 391 bytes)
1        6   391 ACCEPT     all  --  *      *       0.0.0.0/0            1.1.1.1
```

**The mirror image.** `OUTPUT` counted six, `FORWARD` counted nothing — and look carefully at `INPUT`, because it is the same policy-versus-rule distinction pointing the other way: its *policy* counted five while its *rule* counted zero. The replies came back from `1.1.1.1`, so they did not match a rule written for traffic *from* `10.20.0.0/24`, fell off the end of the chain, and were counted by the policy instead. Which is a free lesson in reading these dumps: **the number on the `Chain` line and the number on a rule line are different measurements**, and confusing them is how people conclude a rule fired when nothing of the sort happened.

One packet, one hook — and which chain's counter moves is not a matter of opinion. This is the debugging technique that outlives every specific rule in this course: when someone insists their rule is not working, the counters tell you whether the packet ever *arrived* at that hook, which is almost always the real question and almost never the one being asked.

**Tear it down** — everything on this page lives in the container, so leaving destroys all of it: the namespace, the bridge, the cable, and the ruleset. That is the whole reason we did not use `--network host`.

```bash
exit
```

> **You understand this when you can** name, for a given packet, which of INPUT/FORWARD/OUTPUT it visits and why it cannot visit two — and prove it from rule counters rather than from a diagram, telling a rule's own counter apart from its chain's policy counter.

> **Check yourself —** with `ip_forward=0`, the packet from `ns1` never appeared on `eth0`. Which of the five hooks did it still reach, and which did it never get to?

<details>
<summary>Answer</summary>

It reached **PREROUTING** — that hook runs before any routing decision, so a packet the host is about to refuse to forward has already been through it. Then the routing decision classified it as "for someone else," and that is where it died: with forwarding disabled the kernel does not pass it on, so it never reached **FORWARD**, and therefore never reached **POSTROUTING** either. Which is exactly why the counters matter more than the diagram — "it left `ns1`" and "it was forwarded" are two different claims, one hook apart.

</details>

> **On your own machine —** the container you just used stands in for a real Linux host, because macOS has no netfilter at all: no hooks, no tables, nothing to read. Where that machinery actually lives on a Mac, and why the answer is "inside a Linux VM," is in [Act IV in the wild](in-the-wild.md#peek-into-the-vm-where-the-primitives-actually-live).

**Kubernetes sees this as** — These five hooks are the whole stage on which Kubernetes performs. It adds no new place for a packet to be touched, because there is nowhere to add one: every `KUBE-`something chain you will meet in Act V is an ordinary named chain, jumped into from one of these five points, in one of these tables, readable with the command you just ran and countable with the `-v` you just used. So the entire iptables side of a cluster reduces to one question you can already ask of any packet — *which hook, which chain, which rule?*

**Where you are now** — You can name the five netfilter hooks, say which of the three middle ones a given packet visits and why it can only visit one, and prove it from counters rather than documentation. You can read a chain dump without mistaking a policy's counter for a rule's. And you have a namespace that reaches the internet's doorstep and dies there, for one reason you can point at.

Which leaves exactly one of the three missing things unpaid, and it is the one no route and no setting can fix. You have watched `10.20.0.2` leave on the wire. You know the name of the table whose job is to rewrite addresses, and you know a packet on its way out passes POSTROUTING *after* the routing decision has already chosen its path. That is two facts and a hook. Put them together before you turn the page: if you were the kernel, allowed exactly one edit to that packet at that moment, what would you change — and what would you have to write down in order to ever get the reply back where it belongs?

---

← Prev: **[Docker networks](02b-docker-networks.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Publishing a port](03a-publishing-a-port.md)** →
