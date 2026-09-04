# Reading a ruleset you did not write

**The wall** — You published a port. A process in a private namespace is now reachable from anywhere that can route to this host, because you wrote two `DNAT` lines and no others. Which raises a question you have no way to answer yet: **who is allowed to reach it?** You wrote nothing about that. You did not choose a policy, you did not write a rule on the hook where such a decision would be made, and on a real machine you would not be the only author — Docker got there first, and so, on many hosts, did whatever firewall the distribution ships.

This lesson is about that situation, which is the normal one. Not "how do I write a rule" — you can do that — but *how do I find out what a machine will actually do to a packet, when the ruleset is a collaboration between me, a daemon, and a tool that reports only on itself.* It ends somewhere uncomfortable: with `iptables` telling you the opposite of the truth, and being right to.

### The port you published, and the firewall that does not protect it

Rebuild the gateway and the published port. Same clean container as the last two lessons:

```bash
docker run --rm -it --privileged --name gw nicolaka/netshoot
```

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
ip netns exec ns1 ip route add default via 10.20.0.1
iptables -t nat -A POSTROUTING -s 10.20.0.0/24 -o eth0 -j MASQUERADE
iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination 10.20.0.2:80
ip netns exec ns1 python3 -m http.server 80 --bind 0.0.0.0 >/tmp/ns1.log 2>&1 &
sleep 1
```

Get the address from your **normal terminal** and confirm the port is open:

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' gw
docker run --rm nicolaka/netshoot \
  curl -s -o /dev/null -m 4 -w 'outside -> :8080 = %{http_code}\n' http://<GW>:8080
```

```
outside -> :8080 = 200
```

Now close it. You want to refuse traffic to port 8080 on this machine, and you know how to write that rule: match the protocol and the destination port, and the verdict is `DROP`. The hook is the one for packets addressed to this machine.

> **Predict first —** you are about to add `-A INPUT -p tcp --dport 8080 -j DROP`. Then you will dial 8080 from outside again. Before you run it: is the port closed? Answer by naming the hook the outsider's packet actually walks — you proved which one that is two lessons ago, with counters.

```bash
iptables -A INPUT -p tcp --dport 8080 -j DROP
iptables -L INPUT -n -v --line-numbers
```

```
Chain INPUT (policy ACCEPT 0 packets, 0 bytes)
num   pkts bytes target     prot opt in     out     source               destination
1        0     0 DROP       tcp  --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:8080
```

The rule is there, it is unambiguous, and it says `DROP`. Dial it:

```bash
docker run --rm nicolaka/netshoot \
  curl -s -o /dev/null -m 4 -w 'outside -> :8080 = %{http_code}\n' http://<GW>:8080
```

```
outside -> :8080 = 200
```

**Two hundred.** The port is wide open, the rule is real, and the rule's counter has not moved a single packet. Read it again and it will still say zero, because **that packet never went near `INPUT`**. It arrived, hit `PREROUTING`, got its destination rewritten to `10.20.0.2` by your own `DNAT` rule, and at that point the routing decision looked at it and said *this is not for me* — so it went to `FORWARD`, and `FORWARD` has no rule and an `ACCEPT` policy. `INPUT` is the hook for traffic **for this machine**, and by the time the fork was reached, this traffic was for something else. Your own NAT rule is what made your own firewall rule irrelevant.

Prove the path rather than believing the story:

```bash
iptables -A FORWARD -d 10.20.0.2 -j ACCEPT
iptables -Z
```

```bash
docker run --rm nicolaka/netshoot curl -s -o /dev/null -m 4 http://<GW>:8080
```

```bash
iptables -L -n -v --line-numbers | grep -E "Chain|DROP|ACCEPT"
```

The `FORWARD` marker counts the packets; the `INPUT` `DROP` still reads zero. The correct rule is `-A FORWARD -d 10.20.0.2 -p tcp --dport 80 -j DROP`, on the other hook, matching the address *after* translation — which is a genuinely unobvious rule to have to write, because none of the numbers in it are the ones you typed when you published the port.

**This is one of the most expensive mistakes in production networking, and it has a name.** Most distributions ship a friendly firewall front-end — `ufw` on Debian and Ubuntu, `firewalld` on the Red Hat side — which writes `iptables` rules for you and reports on them. Run `ufw deny 8080` on a host publishing a container port and `ufw status` will tell you `8080 DENY Anywhere`, truthfully, forever, while the port stands open to the entire internet for exactly the reason you just reproduced: `ufw` hangs its rules on `INPUT`, and container traffic walks `FORWARD`. Databases have been exposed this way for months at a time, with a green firewall status on the dashboard the whole while.

The lesson is not "`ufw` is broken." `ufw` is doing precisely what it says. The lesson is the general one, and it is the reason this page exists: **a rule on a hook the packet never walks decides nothing, and a tool that reports on its own rules cannot report on anybody else's.** Read the table, not the tool.

> **You understand this when you can** explain why a `DROP` on `INPUT` does not close a published container port, name the hook and the post-translation address the correct rule has to match, and say what `ufw status` is actually a true statement about.

### So read the table — all of it

You have been reading your own two-rule tables. Now read a real one. Docker's rules live on the *host* — the machine running the daemon, which on a Mac is the Linux VM — so this is the one place we reach for `--network host`, and only to look:

```bash
docker run --rm --privileged --network host nicolaka/netshoot \
  sh -c 'iptables -t nat -S POSTROUTING; echo ---; iptables -S | head -30'
```

On a machine with Docker running and a `kind` cluster's networks left lying around, that comes back with something like this:

```
-A POSTROUTING -o docker0 -m addrtype --src-type LOCAL -j MASQUERADE
-A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j MASQUERADE
-A POSTROUTING -o br-c9a705a9f083 -m addrtype --src-type LOCAL -j MASQUERADE
-A POSTROUTING -s 172.19.0.0/16 ! -o br-c9a705a9f083 -j MASQUERADE
-A POSTROUTING -o br-52465a518f9d -m addrtype --src-type LOCAL -j MASQUERADE
-A POSTROUTING -s 172.20.0.0/16 ! -o br-52465a518f9d -j MASQUERADE
```

**Six `MASQUERADE` rules where you wrote one, and none of it is mysterious.** They come in pairs, one pair per bridge — `docker0` plus two `br-<12-hex>` bridges, which [the Docker networks lesson](02b-docker-networks.md) taught you to recognise as custom networks or a `kind` cluster's own. Within each pair:

- `-s 172.17.0.0/16 ! -o docker0 -j MASQUERADE` is **your rule**, exactly: this subnet, leaving by any interface that is not its own bridge. You wrote `-s 10.20.0.0/24 -o eth0`; Docker writes the negation instead of naming the uplink, because it does not know which uplink you have.
- `-o docker0 -m addrtype --src-type LOCAL -j MASQUERADE` is the other direction and a different job — traffic from the host *itself* going into the bridge. Do not chase it here; it exists to fix a specific reflection problem that [When NAT runs out](03d-when-nat-runs-out.md) builds and breaks on purpose, and it is the same problem your `127.0.0.1:8080` dial ran into last lesson.

Now the `filter` table, which is where the thing that matters lives:

```bash
docker run --rm --privileged --network host nicolaka/netshoot \
  sh -c 'iptables -S | grep -E "DOCKER|^-A FORWARD"'
```

```
-A FORWARD -j DOCKER-USER
-A FORWARD -j DOCKER-FORWARD
-A DOCKER-FORWARD -j DOCKER-CT
-A DOCKER-FORWARD -j DOCKER-INTERNAL
-A DOCKER-FORWARD -j DOCKER-BRIDGE
-A DOCKER-FORWARD -i docker0 -j ACCEPT
-A DOCKER-CT -o docker0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A DOCKER-BRIDGE -o docker0 -j DOCKER
-A DOCKER ! -i docker0 -o docker0 -j DROP
-A DOCKER-USER -i eth0 -j ACCEPT
```

**Read the shape before any single line.** `FORWARD` — the hook, the one your published port walks — contains **no rules of its own at all**. It has two jumps. Each of those lands in a list which contains more jumps. This is a tree, four levels deep in places, and the actual verdicts are at the leaves.

Which is a problem, because you cannot yet read it. You know these named chains are not hooks — there are five hooks and none is called `DOCKER-CT` — and you know a jump sends a packet into a list. What you do not know is what happens to a packet that goes into `DOCKER-CT`, matches nothing there, and reaches the end. Two answers are possible and they are not close: either the jump is one-way and the packet's fate is settled inside, or the packet comes back and `DOCKER-FORWARD` carries on at the next line. **Docker has staked its entire firewall integration on one of those being true**, and so has Kubernetes: Act V's `KUBE-SERVICES → KUBE-SVC-… → KUBE-SEP-…` is this same picture, three levels deep, written by kube-proxy. [The stateful firewall](03c-the-stateful-firewall.md) has you build a two-chain jump and read the counters to find out which, and after that this tree is ordinary.

Three things are worth taking from it now, though, without needing that answer.

**One: `DOCKER-USER` is a room left for you.** It is jumped to *first*, above everything Docker wrote, and Docker never writes rules into it. That is a deliberate contract: put your own rules there and they are evaluated before Docker's, and Docker will keep rewriting everything below without touching yours. It is the actual fix for the trap at the top of this page — a rule in `DOCKER-USER` would have worked where the one on `INPUT` did not. Note also that on Docker Desktop it is **not empty**: it carries `-i eth0 -j ACCEPT` and a few rules mentioning a `services1` interface, which are the VM's own plumbing. "Reserved for you" and "empty" are different claims, and only the first one is true.

**Two: one rule in there is not like the others.** Look at `DOCKER-CT`: `-m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT`. Every rule you have written in three lessons matched an address, a port, a protocol or an interface. This one matches none of those — and if you go looking for a field called `ctstate` in a packet header, there isn't one. Something is being consulted here that is not in the packet at all. **Do not look it up.** Sit with the fact that it exists, on the hook protecting every container on this box, written by a program.

**Three: the policy on the hook protecting every container on the box is not yours.** Whatever it is, Docker set it when the daemon started, and the rules above it were written by a program that will rewrite them again the next time a container starts.

### One backend, two grammars

There is one more rung in *read the table, not the tool*, and it is aimed at the tool you have used for all three of these lessons. Ask `iptables` what it is — and then ask the filesystem what it is, which is more revealing:

```bash
iptables -V
ls -l $(which iptables)
```

```
iptables v1.8.13 (nf_tables)
lrwxrwxrwx    1 root     root            17 /usr/sbin/iptables -> xtables-nft-multi
```

**That parenthesis is not a build detail, and that symlink is the whole story.** Since version 1.8, `iptables` is a **front-end**: it parses the syntax you know and programs **nftables**, the netfilter subsystem that replaced the old `ip_tables` module. The binary you have been typing is literally a translator, and its real name says so. Every rule you have written in this act went into a store you have not looked at.

Which retroactively explains the loose thread from two lessons ago. `/proc/net/ip_tables_names` existed, was readable, and was empty while your rules plainly worked — because that file belongs to `ip_tables`, the module your rules did not go to.

#### The exact relationship: two binaries, several tables, one store

Do not take that on faith; make the store show you its shape. Write one IPv4 rule with `iptables`, one IPv6 rule with `ip6tables`, and then ask `nft` what tables exist:

```bash
iptables  -A FORWARD -s 10.20.0.9 -j DROP
ip6tables -A FORWARD -s fd00::9   -j DROP
nft list tables
```

(`ip6tables` is the same tool for IPv6, and `fd00::/8` is IPv6's private range — the v6 equivalent of `10.0.0.0/8`. That is all you need from it here.)

```
table ip nat
table ip filter
table ip6 filter
```

**Three tables, and you can account for all three.** `table ip nat` is where your `MASQUERADE` and `DNAT` went at the top of this lesson. `table ip filter` is where `iptables` puts filter rules. And `table ip6 filter` is a *different table*, because `ip6tables` is a different binary writing into a different family.

So the relationship is exactly this: **each `(binary, -t value)` pair you have been typing addresses one table in one store.** `iptables -t nat` and `iptables -t filter` are two tables; `ip6tables -t filter` is a third. They are not views of one ruleset. Which is why "you have to maintain two rulesets" has always been true of iptables — that is the data model, not a style complaint about the command.

Now look at what your own rules became:

```bash
nft list table ip filter
```

```
table ip filter {
	chain INPUT {
		type filter hook input priority filter; policy accept;
		tcp dport 8080 counter packets 0 bytes 0 drop
	}

	chain FORWARD {
		type filter hook forward priority filter; policy accept;
		ip daddr 10.20.0.2 counter packets 6 bytes 399 accept
		ip saddr 10.20.0.9 counter packets 0 bytes 0 drop
	}
}
```

**That is your whole afternoon, in the other grammar** — the `DROP` that failed to close the port, the `FORWARD` marker that proved why, counters and all. Same rules, one storage layer, and **three things in that output are worth stopping on**.

**The hook is written down.** `type filter hook forward priority filter` — the five hooks you spent lesson 03 inferring from counters are, in this grammar, *declared*. And `filter` and `nat` stop being special: they are ordinary tables that happen to have those names, created by the translator because that is what your CLI expects. A chain says out loud which hook it attaches to, which means a program can bring its own table and still land at the hook it needs, without touching anybody else's.

**Rule order becomes `priority`.** In iptables, order is a global property of a chain, which means two programs writing to the same chain are in a fight. In nftables, each chain declares a priority at its hook, and the kernel walks them in that order. That is how two independent programs share a hook without a merge conflict, and it is why the modern answer to "Docker keeps overwriting my rules" is a separate table rather than a better position in `FORWARD`.

It also pays off a debt. [The five hooks](03-iptables-and-nat.md) told you that when several tables have a chain at the same hook the order is `raw` → `mangle` → `nat` → `filter`, and said you could read that out of the kernel rather than memorise it. This is the command. Put a rule in four different tables at the same hook and ask the store what it made:

```bash
iptables -t raw    -A PREROUTING -d 10.99.0.1 -j ACCEPT
iptables -t mangle -A PREROUTING -d 10.99.0.1 -j ACCEPT
nft list ruleset 2>/dev/null | grep 'hook prerouting'
```

```
		type nat hook prerouting priority dstnat; policy accept;
		type filter hook prerouting priority raw; policy accept;
		type filter hook prerouting priority mangle; policy accept;
```

**Three chains, one hook, and the traversal order written down as data — but not in the order the lines came out.** The listing follows the order the tables happen to exist in the store; `nat` is first only because you created it at the top of this lesson. The order that decides anything is in the `priority` field. `raw`, `mangle` and `dstnat` are names standing for fixed numeric priorities, and the kernel walks a hook's chains from the lowest number to the highest — so those three names, in that order, *are* the answer, printed by the kernel rather than remembered from a diagram. It is also a standing warning about reading any `nft` dump: **a ruleset listing is not a running order.**

And `dstnat`/`srcnat` are the giveaway that this grammar was designed by people who knew what the `nat` table is *for*: DNAT before the routing decision, SNAT after it, named after the job rather than the hook.

**And `counter` is a thing you asked for.** In iptables every rule counts, always. Here counting is an explicit part of the rule the translator added on your behalf, because that is what `iptables -v` needs in order to work.

#### What the second grammar buys, on problems that got big

So far this is the same ruleset with different punctuation. Here is where it stops being that. Take a genuinely ordinary requirement — block three addresses — and write it the way you have been writing it:

```bash
iptables -A FORWARD -s 10.20.0.10 -j DROP
iptables -A FORWARD -s 10.20.0.11 -j DROP
iptables -S FORWARD | grep -c -- '-s 10.20.0'
```

```
3
```

**Three addresses, three rules, and the kernel walks them one at a time.** Three is fine. Three thousand is a linear scan on every packet, and the only iptables answer has always been `ipset`, a separate subsystem with its own command that you bolt on the side. In nftables a set is a first-class thing:

```bash
nft add table inet mine
nft add chain inet mine fw '{ type filter hook forward priority 0; policy accept; }'
nft add rule inet mine fw ip saddr '{ 10.20.0.9, 10.20.0.10, 10.20.0.11 }' drop
nft list table inet mine
```

```
table inet mine {
	chain fw {
		type filter hook forward priority filter; policy accept;
		ip saddr { 10.20.0.9, 10.20.0.10, 10.20.0.11 } drop
	}
}
```

**One rule, one hashed lookup, three addresses** — and it would be one rule and one lookup for thirty thousand. That set is anonymous, though, which means changing the list means rewriting the rule. Give it a name and the rule stops needing to know what is in it:

```bash
nft 'add set inet mine blocked { type ipv4_addr; }'
nft add rule inet mine fw ip saddr @blocked drop
nft add element inet mine blocked '{ 10.20.0.9, 10.20.0.10 }'
nft add element inet mine blocked '{ 10.20.0.11 }'
nft list set inet mine blocked
```

```
set blocked {
	type ipv4_addr
	elements = { 10.20.0.9, 10.20.0.10,
		     10.20.0.11 }
}
```

**The rule was written once and has not been touched since.** The policy now lives in a named object that anything can add to and remove from, at any rate, without ever rewriting a rule or reloading a ruleset. That is the difference between a firewall you edit and a firewall you *feed* — and if that sounds like the shape of a problem Kubernetes has, hold the thought for one more example.

Because the same idea applies to the verdict, not just the match:

```bash
nft add rule inet mine fw tcp dport 'vmap { 80 : accept, 443 : accept, 23 : drop }'
nft list chain inet mine fw | tail -3
```

```
		ip saddr @blocked drop
		tcp dport vmap { 23 : drop, 80 : accept, 443 : accept }
```

A **verdict map**: one lookup that returns *what to do*, keyed on a packet field. In iptables that is one rule per port, walked in order. (Note that nft sorted the keys — a map is a lookup structure, so the order you typed them in is not a property it keeps.)

**Now hold the two side by side, because it is a question rather than a trick.** Three addresses is three rules, walked one at a time, every packet. That is obviously fine. A hashed set is one lookup no matter how many addresses are in it, which is obviously better and obviously more machinery. So: **at what number does a linear walk stop being fine?** Guess a number now and write it down. Act V puts thousands of rules on a hook for reasons you will find completely reasonable when you get there, and the number where that starts to hurt is smaller than most people guess.

Two more gains worth naming rather than running, because they are structural. `nft -f` loads an entire ruleset — every table, every family — as **one transaction**: either all of it applies or none of it does, so "half-applied firewall" stops being a state a machine can be in. And an `inet` family table (the one you just made) holds IPv4 and IPv6 rules side by side, which is the fix for the two-tables problem you proved above:

```bash
nft add rule inet mine fw ip6 saddr 'fd00::9' drop
nft list chain inet mine fw | grep saddr
```

Both address families, one chain, one place to look.

#### The shadow, one level deeper than `ufw`

The `ufw` trap at the top of this page was about looking at the wrong *hook*. This one is about looking through the wrong *interface*, and it is worse.

> **Predict first —** you are about to load a ruleset with `nft -f`. It begins with `flush ruleset` and installs a `forward` chain whose **policy is `drop`**. Afterwards you will run `iptables -S`. Predict what it prints. Not "will it see the new table" — predict the **`FORWARD` policy line** specifically, and predict what happens to the `MASQUERADE` rule you wrote at the start of this lesson.

```bash
cat > /tmp/r.nft <<'EOF'
flush ruleset
table inet clean {
  chain fw {
    type filter hook forward priority 0; policy drop;
    ip saddr 10.20.0.0/24 accept
  }
}
EOF
nft -f /tmp/r.nft
nft list ruleset
```

```
table inet clean {
	chain fw {
		type filter hook forward priority filter; policy drop;
		ip saddr 10.20.0.0/24 accept
	}
}
```

That is the kernel's own account of what it will do to a forwarded packet: accept it if it is from `10.20.0.0/24`, **drop it otherwise**. Now ask the tool you have trusted for three lessons:

```bash
iptables -S
iptables -t nat -S
```

```
-P INPUT ACCEPT
-P FORWARD ACCEPT
-P OUTPUT ACCEPT
-P PREROUTING ACCEPT
-P INPUT ACCEPT
-P OUTPUT ACCEPT
-P POSTROUTING ACCEPT
```

**Read that line again: `-P FORWARD ACCEPT`.** The kernel will drop. `iptables` says it will accept. This is not the failure mode people expect from a tool that "cannot see nftables rules" — it is not reporting a gap, it is reporting **the opposite verdict**, in the confident, familiar format you would paste into an incident channel. And every rule you wrote earlier in this lesson is gone: the `MASQUERADE`, the `DNAT`, the `DROP` on 8080. `flush ruleset` took them, because they were always nftables rules, and `iptables` now reports empty tables without a word about having lost anything.

`iptables-save` — the command everybody reaches for to capture "the firewall" for a ticket — has the same blindness for the same reason. **Neither is a complete record of what the kernel will do to a packet.**

There is one guard rail, and it is worth seeing:

```bash
iptables -t nat -A POSTROUTING -s 10.20.0.0/24 -j MASQUERADE
nft list ruleset 2>&1 >/dev/null
```

```
# Warning: table ip nat is managed by iptables-nft, do not touch!
```

`nft` can see the translator's tables and warns you off them, on stderr, every time. The two grammars can read each other and neither can safely edit the other's work — which is the whole reason the honest first move on an unfamiliar host is `iptables -V`, and if it says `(nf_tables)`, `nft list ruleset` is the command that was never lying to you.

**Tear it down** — `exit` the container and all of it goes: namespace, bridge, both grammars' rules.

```bash
exit
```

> **You understand this when you can** read `(nf_tables)` in `iptables -V` and say what it implies about where your rules went, point at the hook and priority in an `nft` chain header, name two things a set or a map does that a rule-per-item cannot, and explain why `iptables-save` is not a record of what the kernel will do.

**Kubernetes sees this as** — Every rule a cluster adds to a node lands in the store you just read, at the hooks you just traced, in one of these two grammars. When you go looking for a Kubernetes rule in [Act V](../act-5-kubernetes/07-network-policy.md#where-does-the-decision-actually-get-made) and `iptables -S` comes back empty, this page is why: kube-proxy has an nftables mode, `kindnet` enforces NetworkPolicy in a native table, and RHEL 10 has dropped the legacy backend altogether. Nothing there is hidden from you any more. The only thing you lack is the vocabulary for what the rules are *for*.

**Where you are now** — You can reproduce, by hand, the single most expensive firewall mistake in container operations, and say exactly which hook and which post-translation address the correct rule needs. You can read a four-level chain tree written by a daemon and name what each level is for, including the room it left for you. And you know that the tool you have been using is a translator over a different subsystem — one that declares its hooks, shares them by priority, holds sets and maps instead of repeated rules, and can be loaded atomically — and that when the two disagree, the one with the shorter name is right.

Which leaves the obvious thing undone. Twice now you have watched a firewall report itself green while a port stood open, and both times your conclusion was *read the table*. You did set a `policy drop` once, a few paragraphs ago — but you set it on `forward`, in a throwaway table, to win an argument about two grammars, and you never had to **live** behind it. Nothing you rely on was on the other side.

So do the obvious thing next and find out what that actually costs: refuse everything by default on the hook that protects *this* machine, allow back only what you meant to allow, and see how far you get with rules that match on addresses and ports — which, until this moment, is the only kind of rule you have ever written. Except one. You read a rule in `DOCKER-CT` that matched on none of those things, and you still do not know what it was looking at.

---

← Prev: **[Publishing a port](03a-publishing-a-port.md)** · ↑ **[Act IV overview](README.md)** · Next: **[The stateful firewall](03c-the-stateful-firewall.md)** →
