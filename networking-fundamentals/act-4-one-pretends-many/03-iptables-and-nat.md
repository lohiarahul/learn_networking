# iptables — the five hooks

Two lessons ago you built a cable, then a switch, and `ns1` could reach the host and its neighbours. That lesson's *Check yourself* asked whether `ping 8.8.8.8` would work from in there, and the answer named three separate things that were missing, in three different subsystems. One was a route. One was the host's willingness to pass a packet that is neither from it nor for it. The third was the killer: a packet leaving with a private source address is a packet no router on earth can reply to.

This lesson pays the first two and walks you up to the wall the third is behind. Every one of them is fixed — or refused — by `iptables`, so that is where we start: not with a rule to copy, but with the shape of the thing. Almost everything people find baffling about `iptables` is a consequence of its structure being three separate ideas wearing one command name.

### The structure: two axes, and a chain where they cross

`iptables` is not a firewall. It is a way of attaching rules to **fixed points in the kernel's packet path**, and a firewall is one of the things you can build with it. Three words carry the whole model, and each answers a different question:

- A **hook** answers ***when*** — at which point in a packet's journey the kernel stops to consult your rules. There are **five**, they are kernel-owned, and you cannot add one.
- A **table** answers ***what kind of edit*** the rules there are allowed to make — decide the packet's fate, rewrite its addresses, tag it. There are **five**, also fixed.
- A **chain** is ***the actual list of rules*** sitting at **one (table, hook) crossing**. A rule lives in a chain, so a rule's full address is a table *and* a hook — never just one of them.

Tables and hooks are **two independent axes, not a hierarchy**, and that is the single most useful thing to know about this tool. `filter`'s `INPUT` and `nat`'s `INPUT` are two different lists that happen to share a name: walked at the same moment, holding different rules, keeping separate counters.

One more term, because it shows up in output before anything else does:

- A **policy** is a chain's ***default verdict*** — what happens to a packet that reaches the end of that chain with no rule having decided it. Exactly **one per built-in chain**, always. `iptables` prints it as a `-P` line.

Which fixes the cardinality, and all four numbers are worth holding at once:

<!-- figure -->

```
   5 hooks  ×  5 tables   =  25 possible crossings
                             17 of them actually exist as chains
                              1 policy per chain, no more, no less
                              0 rules on a machine nobody has configured

   So a machine at rest prints 17 `-P` lines across all five tables and
   nothing else. Every other line you ever see is one somebody wrote.
```

**The five hooks**, in the order a packet meets them:

- **PREROUTING** — the packet just arrived, *before* the kernel decides where it goes.
- **INPUT** — the routing decision said "this is for me, locally."
- **FORWARD** — the routing decision said "this is passing through me to somewhere else."
- **OUTPUT** — a packet originating from a local process, heading out.
- **POSTROUTING** — about to leave the machine, *after* the routing decision.

**Draw it** — the five hooks, and the routing decision that chooses between the middle three:

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

**The five tables**, one verb each. The verb is the whole identity of a table, and it predicts which hooks that table bothers to have a chain at:

| Table | Its verb | Its chains — the hooks it has | # |
|---|---|---|---|
| **`filter`** | *decide* — accept or drop | `INPUT` · `FORWARD` · `OUTPUT` | 3 |
| **`nat`** | *rewrite* — change an address | `PREROUTING` · `INPUT` · `OUTPUT` · `POSTROUTING` | 4 |
| **`mangle`** | *annotate* — alter or tag fields | `PREROUTING` · `INPUT` · `FORWARD` · `OUTPUT` · `POSTROUTING` | 5 |
| **`raw`** | *exempt* — act before conntrack | `PREROUTING` · `OUTPUT` | 2 |
| **`security`** | *label* — tag for a security model | `INPUT` · `FORWARD` · `OUTPUT` | 3 |

**3 + 4 + 5 + 2 + 3 = 17.** That is where the number comes from, and you can now add it up yourself rather than take it from me. The other **8** of the 25 do not exist, and each blank is its own verb refusing its own hook — no blank is arbitrary, and this accounts for all eight:

| Missing chain | Why that hook makes no sense for that verb |
|---|---|
| `filter` at `PREROUTING` | Filtering asks **whose** packet this is, and the routing decision has not answered that yet. |
| `filter` at `POSTROUTING` | The packet already survived whichever of `INPUT`/`FORWARD`/`OUTPUT` applied. A second verdict would decide nothing new. |
| `nat` at `FORWARD` | An address edit is only useful as a packet **arrives** or **leaves**. Rewriting midway through a transit it is already committed to changes nothing about where it goes. |
| `raw` at `INPUT` | `raw`'s whole identity is *before conntrack*, and conntrack runs immediately after `PREROUTING`. By `INPUT` the packet is already tracked, so there is nothing left to exempt. |
| `raw` at `FORWARD` | Same reason — already tracked. |
| `raw` at `POSTROUTING` | Same reason — already tracked, and about to leave. |
| `security` at `PREROUTING` | Same as `filter`: no owner established yet, so there is nothing to label it against. |
| `security` at `POSTROUTING` | Same as `filter`: the decision has already been made. |

Two patterns fall out of that list, and they are worth more than the eight rows. **`mangle` is the only table with all five**, because tagging a packet is useful at any moment — it neither needs to know whose the packet is nor cares whether it has been tracked. And **`filter` and `security` have the identical three**, because they answer the same question (what may happen to this packet) and so are blocked by the same two facts.

**This lesson lives entirely in `filter` and `nat`**, and those two carry almost every rule you will ever meet — including all of Docker's and all of Kubernetes'. `mangle` and `raw` are built with properly in [When NAT runs out](03d-when-nat-runs-out.md). `security` belongs to an access-control system Act X meets properly; on most machines it is an empty table you see in a listing and nowhere else, and it is named here only so that "five" is a closed set rather than a hand-wave.

Now the grid those two axes make, tables stacked in the order they run:

<!-- figure -->

```
                 PREROUTING   INPUT   FORWARD   OUTPUT   POSTROUTING
   raw               ●                              ●
   mangle            ●          ●         ●         ●          ●
   nat               ●          ●                   ●          ●
   filter                       ●         ●         ●
   security                     ●         ●         ●

   ● = a chain exists at this (table, hook) pair, and a rule can live there
       17 of 25 cells filled — count the dots per row: 2, 5, 4, 3, 3
       the 8 blanks are the eight named in the table above, each one a
       verb refusing a hook where it would have nothing to do

   This grid is NOT a timeline. Time runs left to right, along the hooks;
   the rows are only five tables listed in a fixed order. So `filter`
   being drawn below `nat` does not put it later than nat's POSTROUTING
   — read across `filter`'s own row and it stops at OUTPUT. Nothing in
   the filter table ever runs at PREROUTING or POSTROUTING.

   Within ONE column, though, the order IS top to bottom as drawn:
   raw → mangle → nat → filter → security, all at that single hook.
   Exempt from tracking before you tag; tag before you translate;
   translate before you decide — so a firewall judges the address the
   packet is really going to, not the one it arrived with.

   `iptables -L` with no -t shows you ONE ROW of this grid: filter.
```

That ordering answers a question the two-axis model raises immediately: several tables have a chain at the same hook, so which runs first? It is fixed, not arbitrary, and readable out of the kernel rather than memorised — though the command that prints it belongs to [a later lesson](03b-reading-a-ruleset-you-did-not-write.md).

Finally the command shape. Every `iptables` command on this page is these five parts, and this is the whole flag vocabulary of the act:

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

  -t  picks the table and defaults to `filter` — which is why most people
      never notice the flag exists, and why the rules actually rewriting
      their packets are invisible to them. The default is not arbitrary:
      `filter` is the *decide* table, so `iptables` with no -t is a
      firewall tool, and a firewall is what most people came for.

  -j  is "jump": where the packet goes when the match hits. ACCEPT and DROP
      are *verdicts*, and a verdict ends the packet's walk through the table.
      Something that is not a verdict can also go here — hold that thought.
```

Two of those are new to you (`-Z` and `-S`); the rest arrive as you need them. If you would rather work a command out than look one up, [the grammar](../../reference/01-the-grammar.md) teaches the shape of any command in this course, and [the map](../../reference/03-the-map.md) ties each tool to the kernel state it reads.

> **Predict first —** you have the model before the machine. On a container nobody has configured, `iptables -t nat -S` and `iptables -S` will each print some `-P` lines and nothing else. **Commit to two numbers** — how many lines from each — and say why they differ.

### Read it on a kernel that has none of it

Start the lab. **Note the absence of `--network host`** — that is deliberate. A plain `--privileged` container gets its *own* network namespace, so everything below happens on a clean slate no Docker daemon and no half-cleaned-up previous lesson has touched, and `exit` destroys all of it:

```bash
docker run --rm -it --privileged --name gw nicolaka/netshoot
```

```bash
ip -brief addr show                 # every interface and its addresses, one line each
ip route                            # the routing table
iptables -t nat -S                  # the nat table
iptables -S                         # no -t, so: filter
```

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

**Four and three**, and you can now read that as data rather than noise. Every `-P` line is one chain announcing its name and its default verdict, so counting `-P` lines counts chains: `nat` has four, `filter` has three, same kernel, same instant. That mismatch is the two-axis model showing through — a table is not one shared ruleset sliced five ways, it is its own compartment with its own membership, and `nat` has a `PREROUTING` and a `POSTROUTING` exactly where `filter` has a `FORWARD`. Not one actual rule anywhere. Every line that appears for the rest of this lesson is one you put there.

Ask all five tables at once and the grid comes back printed by the kernel instead of drawn by me:

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

Seventeen chain names across five tables — the seventeen filled cells, and each table's membership is exactly what its verb predicted. Now prove the two axes are genuinely independent: write what looks like the same rule twice, then delete it from one place.

```bash
iptables -t filter -A INPUT -d 10.99.0.7 -j ACCEPT
iptables -t nat    -A INPUT -d 10.99.0.7 -j ACCEPT
iptables -t filter -S INPUT
iptables -t nat    -S INPUT
```

Both print `-A INPUT -d 10.99.0.7/32 -j ACCEPT`, identical. They are not the same rule:

```bash
iptables -t filter -D INPUT -d 10.99.0.7 -j ACCEPT
iptables -t filter -S INPUT      # gone
iptables -t nat    -S INPUT      # still there
```

**One deletion, one survivor.** `-t` is not a display filter — it is part of the address of the rule. So run the command everybody runs, and note what it is *not* showing you:

```bash
iptables -L -n
```

Your surviving `nat` rule is nowhere in that output, and nothing in the output admits it. That is one row of the grid, and it is worth remembering the next time a machine is plainly rewriting your packets while "the firewall" looks empty.

The eight blank cells are blank in a stronger sense than "empty list" — the chain is *absent*, and asking for it is an error:

```bash
iptables -t filter -S PREROUTING ; echo "exit=$?"
iptables -t nat    -S FORWARD    ; echo "exit=$?"
```

```
iptables: No chain/target/match by that name.
exit=1
```

Both fail, and both failures are the verb column being enforced: there is nothing for `filter` to decide before the routing decision has established whose packet this is, and nothing for `nat` to usefully rewrite midway through a transit. Clean up the survivor before moving on:

```bash
iptables -t nat -D INPUT -d 10.99.0.7 -j ACCEPT
```

One caution about the word *chain*, because you will meet an apparent violation of it within two lessons. Every chain so far is a **built-in**: named after a hook, called by the kernel, carrying a policy. Nothing stops you — or a program — creating an extra, *named* list of rules and jumping into it from one of the five. Those have no hook and no policy, and `-L` tells you which kind you are looking at: a built-in prints `(policy ACCEPT)`, a named one prints `(2 references)`. So when you eventually run `iptables -t nat -L DOCKER` and find a chain named after a product, in a kernel with five hooks and no `DOCKER` among them, that is what you are looking at. Sit with the question it raises — *what happens to a packet that jumps somewhere and is not decided there?* — because it has two possible answers with very different consequences, and [the stateful firewall](03c-the-stateful-firewall.md) has you build one to find out which.

### The gateway that is not one yet

Rebuild the minimum from [veth and bridge](02-veth-and-bridge.md) — one bridge, one namespace, one cable — and this time give the namespace what it lacked:

```bash
ip netns add ns1
ip link add br0 type bridge
ip addr add 10.20.0.1/24 dev br0        # NEW — the HOST's address on this segment
ip link set br0 up
ip link add veth-a type veth peer name veth-a-c
ip link set veth-a master br0           # veth-a is now a switch port: no address
ip link set veth-a up
ip link set veth-a-c netns ns1
ip netns exec ns1 ip addr add 10.20.0.2/24 dev veth-a-c   # ns1's address
ip netns exec ns1 ip link set veth-a-c up
```

Ten lines, and only the **third** is new. The other nine are lesson 02's, with the same roles its [vocabulary table](02-veth-and-bridge.md#the-words-and-what-wears-them) named: `veth-a-c` is the namespace end and holds the address, `veth-a` is a bridge port and holds none, `br0` is the switch. (Lesson 02 also brought `lo` up inside the namespace. Nothing on this page ever talks to `ns1`'s loopback, so that line is gone.) The new line is the one to slow down on: **`ip addr add 10.20.0.1/24 dev br0` claims the `.1` that lesson 02 pointedly left unclaimed.**

**A bridge is two objects wearing one name.** There is a *switch*, which learns MACs and forwards frames between the ports in `brif/` and neither has nor wants an address — that is the whole of lesson 02. And there is an *interface* named `br0`, which the host's own IP stack can own like any other. `ip addr add ... dev br0` talks to the second one. It does not address the switch, and it does not address anything plugged into the switch; it gives **the host one port on that switch** — the port that leads into the host's routing table. Physical switch vendors call that port the SVI, or the management interface.

Last lesson nobody needed that half: three namespaces talking only to each other need a switch, not a host. Here `ns1` needs something only the host can fetch, so the host has to be *on* the subnet — hence `.1` on `br0` and `.2` in `ns1`, two hosts on one segment, one of which happens to be running the switch and takes `.1` because that is the number every network reserves for the way out.

```bash
ip -brief addr show br0        # the interface half: it holds 10.20.0.1/24
ip -brief addr show veth-a     # a port: no IPv4 address, and it needs none
ls /sys/class/net/br0/brif/    # what the switch half is made of
ip route                       # how the host reaches the segment
```

`veth-a` carries no address at all — only the link-local IPv6 the kernel gives every interface. Ports do not get addresses; they carry frames. And the route that `ip addr add` installed for free reads `10.20.0.0/24 dev br0`, not `dev veth-a`: when this host wants anything on that segment it goes **out through the bridge**, exactly like every namespace on it. That is "the host has one port on this switch", stated as a route.

If that feels inconsistent with the *first* half of lesson 02, it should — there you put an address on the host's end of the cable itself. What changed is that there is now a switch in the middle, and `master br0` is the line that changed it. Before the bridge, the host's end of the cable *was* the host's presence on the wire, so it held the address. After it, the host's presence is `br0`, and `veth-a` is demoted to plumbing. **The address did not disappear; it moved to the object that now represents the host.** Nothing enforces this, which is the part worth remembering: enslaving an interface does not clear an address it already had, and `ip addr` keeps displaying it as though it were fine. It is simply not where the host lives any more.

> **Predict first —** `ns1` has an address, a cable, a switch, and a host on the far side with working internet. Run `ping 1.1.1.1` from `ns1`. It will fail. **Name the error message you expect**, and be specific about one thing: does the packet leave `ns1` at all?

```bash
ip netns exec ns1 ping -c1 -W2 1.1.1.1 ; echo "exit=$?"
```

```
ping: connect: Network unreachable
exit=2
```

**Instant, and it never left.** Not a timeout — nothing was sent. `ns1`'s routing table has one entry, for `10.20.0.0/24`, and `1.1.1.1` is not in it, so `ns1`'s kernel had nowhere to send the packet and refused before a byte hit the wire. That is [Act II's routing table](../act-2-two-machines/02-ip-and-routing.md) doing exactly what Act II said it does, now inside a namespace of its own. Fix it the way Act II taught:

```bash
ip netns exec ns1 ip route add default via 10.20.0.1
ip netns exec ns1 ping -c2 -W2 1.1.1.1 ; echo "exit=$?"
```

```
2 packets transmitted, 0 received, 100% packet loss, time 1024ms
exit=1
```

A **completely different failure**, and the change is the lesson in miniature. No error, no refusal — two seconds of nothing. The packet was accepted by `ns1`'s routing table, handed down the cable to `br0`, and then something happened to it that nobody reported to anybody.

You have two suspects and no way to choose between them. Either this host is refusing to pass a packet not addressed to it, or it is passing it perfectly and the *reply* never came. **Those two produce identical output.** Go and look.

> **Predict first —** take the first suspect. A host that forwards other people's packets is doing a different job from one that only sends its own, and Linux keeps that as a setting. Guess whether it is on or off in this container before you read it.

```bash
sysctl net.ipv4.ip_forward
```

```
net.ipv4.ip_forward = 1
```

**Already on** — Docker turns it on, because a container host that could not forward would be useless. So the first suspect is eliminated without being fixed. Prove it is the switch it claims to be by turning it *off* and watching the failure change shape. Watch the uplink while you do it — `eth0` is the only way out of this machine, so a forwarded packet has to appear there:

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

**Nothing.** Not a dropped reply — the packet never reached the uplink. With forwarding off, the host took delivery of a packet addressed to `1.1.1.1`, noticed it was not for itself, and discarded it silently. Put it back:

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

**There it is, and there is the problem, printed in the first column.** The packet is leaving — forwarding works, the bridge works, the cable works, the route works — and it is leaving with the source address `10.20.0.2`, which exists nowhere except inside a namespace on this box. Cloudflare will receive it, compose a perfectly good reply, address that reply to `10.20.0.2`, and hand it to an internet with no idea such a place exists. The reply is not slow. It is not blocked. **It was never deliverable.**

Two identical silences, one on each side of a `sysctl`, told apart only by putting `tcpdump` on the wire. Two of the three missing things are now paid. The third cannot be fixed by routing, by switching, or by any setting, because nothing in the packet is *wrong*: it is a truthful report of where it came from, and the truth is unroutable. **The address itself has to change on the way out, and change back on the way in.**

### Which hook did the packet actually walk?

Every rule carries two counters — packets and bytes matched — and `-v` prints them. That turns a chain into an instrument: instead of believing a diagram about where your packet went, leave a marker at each hook and read which ones it tripped.

Set three, one per `filter` chain. Each is an `ACCEPT`, and each is deliberately a **no-op** — the policies are already `ACCEPT`, so these change the fate of nothing and exist purely to be counted:

```bash
iptables -A INPUT   -s 10.20.0.0/24 -j ACCEPT
iptables -A FORWARD -s 10.20.0.0/24 -j ACCEPT
iptables -A OUTPUT  -d 1.1.1.1      -j ACCEPT
iptables -Z
iptables -L -n -v --line-numbers
```

`-Z` zeroes every counter, which is what makes the next reading mean only what it claims to. Everything reads `0`.

> **Predict first —** two experiments: a `ping` from **inside `ns1`**, then a `curl` from **this container's own shell**. For each, say which of the three counters moves. Do not answer "the relevant ones" — commit to three numbers per experiment, including the zeros, and be ready to be wrong about which chain a *reply* arrives on.

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

`FORWARD`'s rule has **2 packets, 168 bytes**. `INPUT` and `OUTPUT` are untouched, for a reason you can now state precisely: those two packets were not for this machine and not from it.

Note also that `FORWARD`'s *policy* counter reads zero while its rule reads two. Not a contradiction — a policy only counts packets that reach the end of a chain with no rule having decided them, and yours decided them. (And nothing came *back*: two echo requests, no replies, because the reply is still undeliverable. That changes in one line, next lesson.)

Do not be thrown if a **policy** line elsewhere shows a stray packet you cannot account for; a container is never completely silent. It is the numbers on *your rules* that are the measurement, because you chose what they match. Now the other case:

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
Chain OUTPUT (policy ACCEPT 0 packets, 0 bytes)
1        6   391 ACCEPT     all  --  *      *       0.0.0.0/0            1.1.1.1
```

**The mirror image**, and the two chains that moved moved in opposite halves of the dump. `OUTPUT`'s **rule** counted six while its policy counted zero — the rule matched every outbound packet, so not one of them ever reached the end of the chain. `INPUT` is the same distinction pointing the other way: its **policy** counted five while its rule counted zero, because the replies came *from* `1.1.1.1` and so did not match a rule written for traffic *from* `10.20.0.0/24`; they fell off the end of the chain and the policy counted them. `FORWARD` stayed at zero throughout — nothing was passing through this machine.

**The number on the `Chain` line and the number on a rule line are different measurements.** Confusing them is how people conclude a rule fired when nothing of the sort happened, and it is why these two readings are worth more than the diagram they confirm: when someone insists their rule is not working, the counters tell you whether the packet ever *arrived* at that hook — almost always the real question, and almost never the one being asked.

**The file** — and here the creed does not hold, in a way worth stopping on. The rules are not in `/proc`. Check for yourself, after writing a rule so there is definitely something to find:

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

**A file with exactly the right name, readable, and empty — zero bytes — while `iptables` shows you the rule it is supposed to describe.** That is stranger than "there is no file", and it is a genuine loose thread rather than a tidy lesson: something in this kernel still publishes that filename, and whatever `iptables` just wrote to did not go there. Hold on to it. [Reading a ruleset you did not write](03b-reading-a-ruleset-you-did-not-write.md) pulls on that thread and finds something underneath that changes how much you trust the `iptables` command itself.

For now, the practical half: the ruleset lives in kernel memory and the only door in is a **netlink** query — exactly the situation you met one lesson ago with the bridge's learned MAC table, which also had no file and also needed its own command to ask the kernel directly. `iptables` is that command for the ruleset.

**Tear it down** — everything on this page lives in the container, so leaving destroys all of it: the namespace, the bridge, the cable, and the ruleset. That is the whole reason we did not use `--network host`.

```bash
exit
```

> **You understand this when you can** give a rule's full address as a table *and* a hook, say why 8 of the 25 crossings cannot exist, and name for a given packet which of INPUT/FORWARD/OUTPUT it visits and why never two — proving it from rule counters rather than a diagram, and telling a rule's own counter apart from its chain's policy counter.

> **Check yourself —** with `ip_forward=0`, the packet from `ns1` never appeared on `eth0`. Which of the five hooks did it still reach, and which did it never get to?

<details>
<summary>Answer</summary>

It reached **PREROUTING** — that hook runs before any routing decision, so a packet the host is about to refuse to forward has already been through it. Then the routing decision classified it as "for someone else," and that is where it died: with forwarding disabled the kernel does not pass it on, so it never reached **FORWARD**, and therefore never reached **POSTROUTING** either. Which is exactly why the counters matter more than the diagram — "it left `ns1`" and "it was forwarded" are two different claims, one hook apart.

</details>

> **On your own machine —** the container you just used stands in for a real Linux host, because macOS has no netfilter at all: no hooks, no tables, nothing to read. Where that machinery actually lives on a Mac, and why the answer is "inside a Linux VM," is in [Act IV in the wild](in-the-wild.md#peek-into-the-vm-where-the-primitives-actually-live).

**Kubernetes sees this as** — These five hooks are the whole stage on which Kubernetes performs. It adds no new place for a packet to be touched, because there is nowhere to add one: every `KUBE-`something chain you will meet in Act V is an ordinary named chain, jumped into from one of these five points, in one of these tables, readable with the command you just ran and countable with the `-v` you just used. So the entire iptables side of a cluster reduces to one question you can already ask of any packet — *which hook, which chain, which rule?*

**Where you are now** — You can state a rule's address on both axes, read a bare `-P` listing as a census of chains, and say which of the 25 crossings exist and why. You can name the five hooks, say which of the three middle ones a packet visits, and prove it from counters without mistaking a policy's count for a rule's. And you have a namespace that reaches the internet's doorstep and dies there, for one reason you can point at.

Which leaves exactly one of the three missing things unpaid, and it is the one no route and no setting can fix. You have watched `10.20.0.2` leave on the wire. You know the name of the table whose verb is *rewrite*, you know it has a chain at `POSTROUTING`, and you know `POSTROUTING` runs *after* the routing decision has already chosen the packet's path. That is a table, a hook, and a verb. Put them together before you turn the page: if you were the kernel, allowed exactly one edit to that packet at that moment, what would you change — and what would you have to write down in order to ever get the reply back where it belongs?

---

← Prev: **[Docker networks](02b-docker-networks.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Publishing a port](03a-publishing-a-port.md)** →
