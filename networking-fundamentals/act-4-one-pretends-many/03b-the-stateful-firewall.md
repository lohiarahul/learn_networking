# The stateful firewall

**The wall** — The last lesson ended with a firewall lying to its owner. `ufw status` said `8080 DENY`
while the port stood open to the internet, because `ufw` hung its rules on `INPUT` and the packet
walked `FORWARD`. The lesson's own conclusion was *read the table, not the tool* — so read it, and
write it. You now know the five hooks, you know which one a packet for this machine walks, and you know
how to attach a rule to it. There is nothing left between you and a firewall you actually understand.

So build the simplest useful one. This host should accept the port you meant to publish and nothing
else. Two lines, and the first is the one that matters, because a firewall built out of `ACCEPT` rules
is only a firewall if everything not accepted is refused *by default*.

### Why does a default-deny policy break the machine that set it?

We need a namespace we can ruin. Everything below sets a default-deny policy, and the interesting part
of the lesson is the half-hour of breakage between setting it and getting the machine working again —
so run this in a container with its own network namespace, deliberately **without** `--network host`
this time:

```bash
docker run --rm -it --privileged --name fw nicolaka/netshoot
```

That container is a small Linux host with a private address, one interface, and internet access. The
internet access, note, is the thing you read in the last lesson and nothing more: a `MASQUERADE` rule
in the *host's* `POSTROUTING` chain is the only reason a `172.17.x.x` packet from in here ever gets a
reply. This container has its own `filter` table, empty, with every policy at `ACCEPT`. Check that, and
confirm the machine works, before you break it:

```bash
iptables -L -n | grep policy
curl -s -o /dev/null -w 'before: %{http_code}\n' https://example.com
python3 -m http.server 80 --bind 127.0.0.1 >/tmp/lo.log 2>&1 &
sleep 1
curl -s -o /dev/null -w 'loopback before: %{http_code}\n' http://127.0.0.1
```

```
before: 200
loopback before: 200
```

The listener on `127.0.0.1:80` is there so that later, when loopback breaks, you can tell the
difference between *"the firewall stopped it"* and *"nothing was ever there to answer."* Two failures
that look identical from a `curl` exit code are the thing this whole lesson is about.

Now close the door. `-P` sets a **chain's policy** — the verdict applied to a packet that reaches the
end of a built-in chain without any rule having decided its fate:

> **Predict first —** you are about to set the `INPUT` policy to `DROP` and add nothing else. Outbound
> traffic is untouched: `OUTPUT` policy stays `ACCEPT`, so your `curl` will leave the machine exactly as
> before. Given that, will `curl https://example.com` still work? If not, name the first thing that
> fails — and be specific, because there are two candidates and they fail in different ways.

```bash
iptables -P INPUT DROP
curl -sS -m 20 https://example.com ; echo "exit=$?"
```

```
curl: (6) Could not resolve host: example.com (Timeout while contacting DNS servers)
exit=6
```

That takes about **eleven seconds** to come back, and the wait is part of the finding: the resolver
tries twice and waits five seconds each attempt before giving up. (Those are libc's defaults, not
something you will find written in this container's `/etc/resolv.conf` — it carries only a
`nameserver` line.) The generous `-m 20` is deliberate — with the `-m 5` you might reach for out of
habit, `curl`'s own deadline fires first and you get `exit=28` with a timeout message instead, which
hides the interesting failure behind a boring one.

Not a timeout. Not a refusal. **A name resolution failure**, and it is worth being precise about why,
because the reason is the whole lesson in miniature. `curl` never got as far as TCP. It asked the
resolver for `example.com`, the query left on `OUTPUT` (still `ACCEPT`), the answer came back — and the
answer is *inbound traffic*. It arrived at `INPUT`, matched no rule, reached the end of the chain, and
the policy said `DROP`. A firewall that only permits what you asked for has silently forbidden every
*answer* to everything you ask.

And it is worse than DNS, in a way that catches almost everyone the first time:

```bash
curl -sS -m 5 http://127.0.0.1 ; echo "exit=$?"
```

That times out too. Loopback is not an exception to `INPUT`. Act I taught that `127.0.0.1` is a
short-circuit inside the kernel rather than a trip to the wire, but "does not touch the wire" is not
"does not traverse netfilter": a packet delivered locally still arrives at `INPUT`, still matches
nothing, still dies at the policy. Every process on this machine that talks to another process over a
socket — and Act I established that this is *how* processes talk — has just been cut off from itself.

So the honest first rule of any default-deny ruleset is the one nobody puts in a diagram:

```bash
iptables -A INPUT -i lo -j ACCEPT
curl -sS -m 5 -o /dev/null -w 'loopback: %{http_code}\n' http://127.0.0.1 ; echo "exit=$?"
```

`-i lo` matches on the *interface the packet arrived on*, and `lo` is the only interface whose traffic
could not have come from anywhere but this machine. That is the whole justification for the rule: it is
not "trust localhost" as a convenience, it is "packets on `lo` were, by construction, sent by a process
you are already running."

### Can you allow the replies without opening the ports they arrive on?

DNS is still broken, and now you have to fix the real problem. Try it with what you have.

The rule you want is *"allow the answer to a question I asked."* The tools you own match on addresses,
ports, protocols and interfaces. So look at the answer you need to admit — the DNS reply — and describe
it in those terms. It arrives from the resolver's address, from source port 53, to *your* address, to
your **ephemeral source port**: some number the kernel picked, from a range, at the moment `curl`
started. Act I's `/proc/net/tcp` had a column for it and Act III's conntrack rows printed it as
`sport=51920`.

There is your problem, and it is not a syntax problem. Write the rule two ways and read what each one
actually permits:

```bash
iptables -A INPUT -p udp --sport 53 -j ACCEPT
```

That works — for *resolution*. Check it with `nslookup example.com` and names resolve again. Do not
reach for `curl` yet: it will still fail with `exit=28`, because a TCP reply is not a UDP reply and
nothing in this ruleset admits one. You have fixed exactly the thing you named and nothing else, which
is worth noticing before you read what else you just did. Because the rule also says: *anyone on the internet who sets their source port to 53 may reach any port
on this machine.* A source port is a number the sender chooses. It is not a credential, it is not
checked by anyone, and it costs an attacker one flag to set. You have not built a firewall with a hole
in it; you have built a firewall with a doorbell.

The other way:

```bash
sysctl net.ipv4.ip_local_port_range
```

```
net.ipv4.ip_local_port_range = 32768	60999
```

Those are the ports your kernel will pick from, and admitting replies means admitting that range:
`--dport 32768:60999 -j ACCEPT`. **28,232 ports, open to everybody**, on the reasoning that some of
them are sometimes yours. And every listening service you ever start above 32768 is now exposed by a
rule you wrote for an entirely different reason.

Sit with the shape of that, because both attempts fail for one reason and it is not carelessness. **A
reply to a request you made and an unsolicited knock at the same port are, in the packet header,
identical.** Source address, destination address, ports, flags — there is no field that says "you
started this." The information you need to write the rule you want is not in the packet, so no rule
that reads only the packet can ever express it.

Delete that and think about who *does* know:

```bash
iptables -D INPUT -p udp --sport 53 -j ACCEPT
```

`-D` deletes, and it takes the rule *as you wrote it* rather than a number — spell the match and target
out again and netfilter removes the rule that matches. (`-A` appends, which is all lesson 03 needed.
You are about to need two more: `-I <chain> <n>` inserts at a position, and `-R <chain> <n>` replaces
the rule at one. Order is the whole grammar of a ruleset, so the flags that manipulate it matter.)

### Where is "I started this conversation" written down?

You already read the answer, one act ago, and you read it as a NAT ledger. Act III's
[conntrack lesson](../act-3-the-internet/02b-conntrack.md) had you find a row, point at the field where
the original and reply tuples disagree, and call that disagreement the NAT mapping. Then its
*Check yourself* asked about a row whose two tuples were an exact mirror — no translation at all — and
answered that the kernel tracks it anyway, because **the table's job is bigger than undoing rewrites:
it is the kernel's answer to "have I seen this flow before?"**

That is the field that is missing from the packet. It was never in the packet; it is in the table. And
netfilter can match on it. The match is not a port, not an address, not a flag — it is a *question put
to the flow table*:

```bash
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
curl -sS -m 5 -o /dev/null -w 'after: %{http_code}\n' https://example.com ; echo "exit=$?"
```

```
after: 200
exit=0
```

One rule. No port numbers anywhere in it. DNS works, TLS works, every protocol you have not thought of
yet works, and nothing unsolicited can get in. `-m conntrack` loads the module that can read the table
and `--ctstate` asks it which category this packet falls into:

```
   NEW           conntrack has no row for this flow. Somebody is starting something.
   ESTABLISHED   conntrack has a row and has seen traffic in both directions.
   RELATED       a different flow, but one this table can prove belongs to a tracked one.
   INVALID       conntrack cannot make sense of it — no row, and not a legal opening either.
   UNTRACKED     deliberately exempted from the table (there is a way; the next lesson does it).
```

**This is what the word "stateful" means, and it is narrower than it sounds.** A stateful firewall is
not a firewall that is cleverer about packets. It is a firewall whose rules are allowed to consult a
table the kernel was already keeping for another reason entirely — and the reason it was keeping that
table, remember, is that NAT could not function without it. The firewall got its best feature as a
side effect of address translation needing a memory.

You can watch the two halves line up. Make a connection and read the row the rule was reading:

```bash
curl -s -o /dev/null https://example.com & sleep 0.3 ; conntrack -L -p tcp 2>/dev/null | head -3
```

Every packet arriving for that flow matched your rule because that row existed. When the row expires —
Act III had you watch the TTL count down — the same packet arriving late matches nothing and dies at
the policy. **The firewall's memory and the NAT table's memory are the same memory, with the same
expiry.**

> **Predict first —** `traceroute` works by sending packets with a deliberately small TTL and reading
> the ICMP `time exceeded` errors that come back from each router. Those ICMP messages are not part of
> your TCP or UDP flow — different protocol, no ports at all. Your rule admits `ESTABLISHED,RELATED`.
> Now narrow it to `ESTABLISHED` alone and predict what happens to `traceroute`.

```bash
iptables -R INPUT 2 -m conntrack --ctstate ESTABLISHED -j ACCEPT
traceroute -m 4 -w 1 example.com 2>&1 | head -6
```

The hops go silent — `* * *` — because an ICMP error *about* a tracked flow is not that flow. It has no
row of its own and it never will. `RELATED` is the category conntrack uses for exactly this: a packet
it can *prove* belongs to a conversation it is tracking, without being part of it. Put it back:

```bash
iptables -R INPUT 2 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
traceroute -m 4 -w 1 example.com 2>&1 | head -6
```

```
traceroute to example.com (172.66.147.243), 4 hops max, 46 byte packets
 1  172.17.0.1 (172.17.0.1)  0.005 ms  0.015 ms  0.003 ms
 2  *  *  *
 3  *  *  *
 4  *  *  *
```

**Hop 1 comes back, and that is the entire result.** Do not read hops 2–4 as a failure: run this
container with no firewall at all and you get exactly the same one line, because Docker Desktop's
userspace uplink does not forward TTL-exceeded errors from beyond the gateway. The discrimination you
are looking for is one hop versus *no* hops — `RELATED` present, an ICMP error is admitted and you
learn something about the path; `RELATED` absent, the same error is dropped and the path is a blank.

`RELATED` is also how a firewall lets an application admit its own second connection — the classic case
being FTP, where a *helper* module reads the control channel, sees the port the data channel will use,
and enters an expectation into the table so the incoming data connection arrives already `RELATED`. A
firewall reading the payload of one connection in order to pre-authorise another is a genuinely
alarming idea, and it is on by default more often than anyone would like. Note that the mechanism is a
kernel module parsing application bytes and hold the discomfort; Act V will hand you something with the
same shape.

> **You understand this when you can** explain why no rule matching only on addresses and ports can
> distinguish a reply from an unsolicited packet, write the single rule that does distinguish them, and
> say which of `NEW`/`ESTABLISHED`/`RELATED` an ICMP `time exceeded` error falls into and why.

### What does the client feel when a packet is dropped?

You have two ways to refuse. They produce the same security outcome and completely different
experiences, and the difference is the most common ten-minute misdiagnosis in networking.

Start a listener in the `fw` container, on a port you will then close two different ways:

```bash
python3 -m http.server 9000 --bind 0.0.0.0 >/tmp/srv.log 2>&1 &
iptables -I INPUT 1 -p tcp --dport 9000 -j ACCEPT   # -I inserts AT position 1, ahead of everything
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' fw
```

Run that last line in **your normal terminal**, not in the container — `docker inspect` talks to the
daemon over a socket, exactly as [the Docker networks lesson](02b-docker-networks.md) established, so
it needs no namespace of its own. Note the address; call it `$FW`. Now dial it from a throwaway
container, the one-liner form that lesson used:

```bash
docker run --rm nicolaka/netshoot \
  curl -s -o /dev/null -m 5 -w 'time=%{time_total}s code=%{http_code}\n' http://<FW>:9000
```

You get `code=200` in a millisecond or two. Now close the port with the verdict you have been using all
lesson, in the container:

```bash
iptables -R INPUT 1 -p tcp --dport 9000 -j DROP
```

> **Predict first —** the client will not get its `200`. But *how* will it not get it? Give a number:
> roughly how long will that `curl` take to give up, and what will it say?

```bash
docker run --rm nicolaka/netshoot \
  curl -s -o /dev/null -m 5 -w 'DROP  -> time=%{time_total}s\n' http://<FW>:9000 ; echo "exit=$?"
```

```
DROP  -> time=5.003083s
exit=28
```

Five seconds — the entire `-m 5` budget — and then a timeout. The client sent a SYN and *nothing came
back*. Not a refusal: an absence. So the client did what Act III taught it to do with an unacknowledged
segment, and retransmitted, and waited longer, and retransmitted again, until you cut it off. Without
`-m 5` it would have sat there for a minute or more.

Now the other verdict:

```bash
iptables -R INPUT 1 -p tcp --dport 9000 -j REJECT --reject-with tcp-reset
```

```bash
docker run --rm nicolaka/netshoot \
  curl -s -o /dev/null -m 5 -w 'REJECT-> time=%{time_total}s\n' http://<FW>:9000 ; echo "exit=$?"
```

```
REJECT-> time=0.000195s
exit=7
```

Instant, and `exit=7` is `Couldn't connect to server`. `REJECT` does not discard the packet — it
*answers* it, with the same RST an unoccupied port would have produced. The port is exactly as closed
as before. The client's experience is the opposite of before.

**And there is a tool that reports this difference as its primary output.** Act I's
[SYN scan lesson](../act-1-one-machine/05b-tcp-states-and-the-syn-scan.md) had you scan a port that was
listening, and `nmap` said `open`. It has two other verdicts, and you have just built the machinery for
both — so scan the same port through all three states and read the reason column, which names the
mechanism rather than the conclusion. You are in the `REJECT` state now:

```bash
docker run --rm nicolaka/netshoot nmap -sS -p 9000 --reason -Pn <FW>
```

```
9000/tcp closed cslistener reset ttl 64
```

Now flip the same rule to `DROP`, scan again, then back to `ACCEPT` and scan a third time:

```bash
iptables -R INPUT 1 -p tcp --dport 9000 -j DROP
iptables -R INPUT 1 -p tcp --dport 9000 -j ACCEPT
```

```
9000/tcp filtered cslistener no-response      <- while the rule was DROP
9000/tcp open     cslistener syn-ack ttl 64   <- once it was ACCEPT again
```

One port, one listener running throughout, three verdicts. `closed` and `filtered` are not two degrees
of confidence in the same finding — they are your two refusals, observed from outside, and `--reason`
prints the evidence: a `reset` arrived, or nothing did. The scanner cannot see your rules, so it reports
what your rules *felt like*. Which is why `filtered` is the more informative answer of the two: it means
"somebody is refusing to be rude to me," and only a deliberately configured machine bothers to do that.

Which sets up the trade you actually have to make. `REJECT` is kind: your own clients fail fast, your
own logs fill with clear errors, and nobody waits sixty seconds to learn something you could have told
them instantly. `DROP` is silent: it costs a scanner time and tells them nothing, and it costs your own
users exactly the same. Pick per rule, not per firewall — the honest default in most rulesets is
`REJECT` inward-facing where humans are waiting, and `DROP` on the outside edge where nobody legitimate
should be knocking at all.

### How does a packet get from one chain into another?

One thing remains between you and reading anybody else's ruleset, and it is a control-flow question
rather than a matching question. Look at what the last lesson found sitting at the top of the host's
`FORWARD` chain: a jump to `DOCKER-USER`, then a jump to `DOCKER`. Those are not hooks. There are only
five hooks and neither is one of them. They are **user-defined chains**, and a jump into one is
closer to a subroutine call than to a verdict.

Build one and watch a packet walk through it. In the `fw` container:

```bash
iptables -F INPUT
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -N GATE
iptables -A GATE -p tcp --dport 9999 -j DROP
iptables -A GATE -j RETURN
iptables -A INPUT -j GATE
iptables -A INPUT -p tcp --dport 9000 -j ACCEPT
```

`-N` creates the chain. Note what it cannot have: **a user chain has no policy.** `-P` works on the five
built-in chains only, because a policy is what happens when a packet runs out of chain — and a packet
that runs out of a *user* chain has somewhere to go back to.

> **Predict first —** a client dials port 9000. `INPUT` rule 3 jumps it into `GATE`, whose only real
> rule is about port 9999 and will not match. The `ACCEPT` for 9000 is rule 4 of `INPUT` — *after* the
> jump. Does the connection succeed? And when you read the counters afterwards, which rules will have
> counted the packet: the jump, `GATE`'s `RETURN`, the `ACCEPT`, or some subset?

```bash
docker run --rm nicolaka/netshoot \
  curl -s -o /dev/null -m 5 -w 'through GATE -> %{http_code}\n' http://<FW>:9000
```

```bash
iptables -L INPUT -n -v --line-numbers
iptables -L GATE  -n -v --line-numbers
```

The connection succeeds, and the counters show the whole path: the `-j GATE` rule in `INPUT` counted it,
`GATE`'s `RETURN` counted it, and `INPUT`'s `ACCEPT` for 9000 counted it. Three rules, one packet, in
that order. So the traversal rule, stated once and for all:

<!-- figure: chain-traversal -->

```
  INPUT                                GATE
  ─────                                ────
  1  -i lo            ACCEPT           1  --dport 9999   DROP    ◄─ terminal: walk ends here
  2  --ctstate ...    ACCEPT           2                 RETURN  ──┐ non-terminal: go back
  3  -j GATE  ────────────────────────▶                            │
  4  --dport 9000     ACCEPT  ◄────────────────────────────────────┘
  5  (end of chain)  → POLICY applies      (end of a USER chain) → return to caller
     ▲                                      there is no policy to apply
     └─ only built-in chains have one

  ACCEPT / DROP / REJECT are TERMINAL: the packet's walk through this table stops.
  RETURN and falling off the end of a user chain are NOT: the walk resumes at the
  rule AFTER the jump that brought it in.
```

That single picture is what makes every ruleset you will ever inherit readable. `DOCKER-USER` exists
precisely because it is jumped to *first* and returns: it is a deliberately empty room Docker leaves at
the top of `FORWARD` for you to put your own rules in, on the guarantee that Docker will keep rewriting
everything below it and never touch that. And Act V's `KUBE-SERVICES → KUBE-SVC-XXXX → KUBE-SEP-YYYY`
is this diagram three levels deep, written by a program — a jump per Service, a jump per endpoint, and a
`RETURN` for every packet that turned out to be none of kube-proxy's business.

**Tear it down** — leave the container and it all goes with it, which is why we used one:

```bash
exit
```

> **You understand this when you can** predict, for a jump into a user chain whose rules do not match,
> which rule the packet is evaluated against next — and say why `-P` cannot be applied to that chain.

### The shadow it casts — you hardened a machine, not the machines behind it

Everything in this lesson happened on `INPUT`, and `INPUT` means *for me*. That was the right hook,
because the whole exercise was protecting this host. Now recall what the container floor actually is: a
box with a bridge, several private namespaces plugged into it, and a routing decision that sends their
traffic to `FORWARD` — because it is not for this machine.

From your normal terminal, look at what the hook protecting *them* says on your Docker host:

```bash
docker run --rm --privileged --network host nicolaka/netshoot \
  sh -c 'iptables -L FORWARD -n | head -3'
```

Read the policy on the first line, and then read whose rules come before it. Whatever the policy is, you
did not choose it — Docker set it when it started, and Docker also wrote the rules above it that decide
which forwarded traffic is allowed. Two lessons in a row have now landed on the same finding from
different directions: the rules that govern a packet are written by whoever got to that hook first, and
your own careful work on a *different* hook is not a fact about them.

That is not a Docker complaint. It is the permanent shape of the problem, and it is why the next
question in the course is a policy question rather than a syntax one. You can write a stateful firewall
for one machine's own traffic. **Who writes one for a thousand namespaces that are created and destroyed
faster than you can type, where the thing you want to name in a rule is not an address at all but "the
payments service"?** Act V's [NetworkPolicy](../act-5-kubernetes/07-network-policy.md) is that question
answered, and you will recognise every mechanism under it.

One more, held as a question rather than answered, because you now own the mechanism it is built from.
You have just written a stateful firewall: a default-deny policy plus one rule that consults the flow
table, and *no return rules anywhere*, because the table made them unnecessary. Somewhere out there is
a network control — you will meet it by name in the cloud stages — that makes you write the return rule
by hand, explicitly, in both directions. Do not look it up. Work out what would have to be **missing**
from such a control for that to be necessary, and what it would therefore cost less of.

**Where you are now** — You can build a default-deny firewall on a Linux host and know why its first
two rules are `-i lo` and a conntrack match rather than anything about ports. You can say what
"stateful" buys and where the state came from. You can choose `DROP` or `REJECT` on purpose and predict
what a client and a port scanner each see. And you can read a jump into a user chain the way the kernel
does, which is the only thing that was standing between you and any real ruleset.

The firewall you built decides *whether* a packet passes. The `MASQUERADE` from the last lesson decides
*what a packet's addresses become* — and it looked free, a single line handling every container on the
box. It is not free, and the reason has nothing to do with speed. Two containers on your bridge both
open a connection to the same server, and the kernel picks their source ports independently, so both
could easily pick 41000. After translation both flows read `<host-ip>:41000 → <server>:443`. The reply
to one is indistinguishable from the reply to the other. So what does the kernel do about that, what is
the arithmetic ceiling on how many times it can do it — and what breaks, loudly and at 3am, when it
runs out?

---

← Prev: **[iptables and NAT](03-iptables-and-nat.md)** · ↑ **[Act IV overview](README.md)** · Next: **[When NAT runs out](03c-when-nat-runs-out.md)** →
