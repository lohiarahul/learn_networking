# When NAT runs out

**The wall** — `MASQUERADE` was one line. One line in `POSTROUTING`, matching a whole `/16` of container
addresses, and every container on the box could reach the internet. Nothing in that line mentions a
container, or a connection, or a limit. It reads like a *function* — a stateless transformation applied
to a packet on the way past.

Work out for yourself whether it deserves to read that way, before you are told. Two containers on
your bridge both open a connection to the same server. The kernel in each namespace picks an ephemeral source port independently — neither knows
the other exists — so nothing stops both from picking 41000. On the way out, `MASQUERADE` rewrites both
source addresses to the host's. Write down what the two flows look like after that rewrite, and then
ask what happens when a reply arrives.

```
   container A          172.17.0.2:41000  →  1.1.1.1:80
   container B          172.17.0.3:41000  →  1.1.1.1:80

   after MASQUERADE rewrites the SOURCE ADDRESS only:

   both of them         203.0.113.9:41000 →  1.1.1.1:80
                        └──────────────────────────────┘
                        one flow. two conversations. the reply
                        matches both rows and belongs to one.
```

Act III told you what the reply is matched against: a row in the conntrack table, keyed on the tuple.
Two identical tuples cannot be two rows. So the rewrite *cannot* be address-only, which means
`MASQUERADE` has a second job nobody advertises — and a budget for doing it.

### Does SNAT rewrite the port too? Catch it doing it

Force the collision rather than waiting for one. `curl --local-port` pins the source port a client uses,
so you can make two containers do the thing they would otherwise do only by coincidence. Both dial the
same destination, from the same source port, at the same time.

Open a **peek shell** in your normal terminal — the host-network container from
[the Docker networks lesson](02b-docker-networks.md), which is the only way to read the *host's* tables:

```bash
docker run --rm -it --privileged --network host nicolaka/netshoot
```

In the peek shell, clear the view so you can see just this experiment (this only deletes rows for one
destination, and any live connection to it will simply re-establish):

```bash
conntrack -D -d 1.1.1.1 2>/dev/null ; conntrack -L -d 1.1.1.1 2>&1 | tail -1
```

Now, in your **normal terminal**, two containers pinned to the same source port:

> **Predict first —** both containers will succeed; that much is not in doubt. The question is what the
> host's conntrack table looks like afterwards. How many rows for `1.1.1.1`, and what do their two
> tuples say? Be specific about the *source port* in each of the four tuples you are about to see.

```bash
docker run -d --name c1 nicolaka/netshoot sleep 300
docker run -d --name c2 nicolaka/netshoot sleep 300
docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' c1 c2
docker exec c1 curl -s -o /dev/null -m 5 --local-port 41000 http://1.1.1.1/
docker exec c2 curl -s -o /dev/null -m 5 --local-port 41000 http://1.1.1.1/
```

Both containers have to be **alive at the same time**, which is why these are `-d` and not `--rm`. Run
two throwaway containers back to back instead and Docker hands the second one the address the first just
released — identical original tuples, so the second flow simply reuses the first one's row and you see
one row instead of two, with nothing to learn from it.

Then read the table in the peek shell:

```bash
conntrack -L -d 1.1.1.1 2>/dev/null
```

```
tcp 6 119 TIME_WAIT src=172.17.0.3 dst=1.1.1.1 sport=41000 dport=80 \
                    src=1.1.1.1 dst=192.168.65.3 sport=80 dport=41000 [ASSURED] mark=0 use=1
tcp 6 119 TIME_WAIT src=172.17.0.4 dst=1.1.1.1 sport=41000 dport=80 \
                    src=1.1.1.1 dst=192.168.65.3 sport=80 dport=5277  [ASSURED] mark=0 use=1
```

Your addresses will differ — `192.168.65.3` is this VM's own outside address, and **the second row's
final port will be some number nothing chose**; mine was `5277` on that run and something else on the
next. That arbitrariness is the finding, not a detail of it.

Two rows, and read the last number on each. The first container got to keep its port: its reply tuple
expects `dport=41000`, the port it actually used. The second one **did not**. Its original tuple still
says `sport=41000` — that is genuinely what it sent, and it will never know otherwise — but its reply
tuple expects a completely different port, because by the time its packet reached `POSTROUTING` the
pair `(203.0.113.9:41000 → 1.1.1.1:80)` was already spoken for.

**So `MASQUERADE` rewrites the source port whenever, and only whenever, it must.** It tries to preserve
the original port, because doing so is free and keeps things debuggable; when the resulting tuple would
collide with a row already in the table, it allocates a different one. The second container's packets
went out with a port number no process on either machine ever chose.

That is the mechanism. Now the ceiling, which you can derive rather than look up.

### How many connections can one address translate?

A reply gets home by matching exactly one row, so every simultaneous flow needs a **distinct tuple**.
Count the fields and ask which of them are actually free to vary:

```
   protocol         fixed — TCP
   source IP        fixed — the host's one address. that is the whole point of NAT.
   destination IP   fixed — you chose the destination
   dest port        fixed — 443, say
   source port      ◄── the only field left. 16 bits.
```

**One NAT address, talking to one destination address on one port, can carry at most 65,535
simultaneous flows** — and that is the theoretical best case. Two things make the real number smaller.

The first you already know, and it is the one that turns a capacity limit into a *rate* limit: Act III
had you watch a conntrack row outlive its connection, ticking down a TTL. A `TIME_WAIT` row holds its
port reservation for a couple of minutes after the conversation ended. So the number that matters is not
"how many connections at once" but "how many connections *started* in the last two minutes", and a
service that opens a fresh connection per request rather than reusing one burns through the space
dozens of times faster than its concurrency suggests. Check the arithmetic on your own machine:

```bash
conntrack -C
sysctl net.netfilter.nf_conntrack_max
sysctl net.ipv4.ip_local_port_range
```

Do not be thrown if that last number disagrees with the `32768 60999` you read in the firewall lesson —
this shell is in the *host's* network namespace and that one was inside a container, and the ephemeral
range is per-namespace like almost everything else in this act. Two different machines, in every sense
that matters to netfilter.

The second is subtler, and it is a *collision* problem rather than a capacity one. Netfilter has to find
a free port, and historically it looked for one by starting at the port the client chose and searching
from there. Two packets being translated at the same instant can both find the same "free" port and both
try to insert it, and one insertion loses. A lost insertion is a **dropped SYN**, and Act III taught you
exactly what a client does with one of those: it waits, and retransmits, typically after one second.
That is the shape of the complaint — *"a small percentage of our requests take exactly one second
longer than the rest, and there is nothing in any application log"* — and its fix is a single flag that
tells netfilter to pick from the whole space at random instead of searching upward from a guess:

```
   -j MASQUERADE --random-fully
```

You do not have to take that on trust as a Kubernetes fact later: kube-proxy grew a `--random-fully`
flag for precisely this, on precisely this reasoning, and now you can read that flag as a sentence
rather than a setting.

> **You understand this when you can** say which single header field SNAT has left to vary, derive the
> per-destination ceiling from that, explain why connection *churn* consumes the space faster than
> concurrency does, and describe what a client sees when a port allocation collides.

### Why can't a container reach a published port on its own host?

Leave capacity behind; the next limit is about paths. This one you should build by hand, because the
failure is invisible from either end and completely obvious in the middle.

In the peek shell, build the shape from [the veth and bridge lesson](02-veth-and-bridge.md) — one bridge,
two namespaces, one of them publishing a port:

```bash
ip link add br1 type bridge && ip addr add 10.80.0.1/24 dev br1 && ip link set br1 up
for ns in app cli; do
  ip netns add $ns
  ip link add v-$ns type veth peer name p-$ns
  ip link set p-$ns master br1 && ip link set p-$ns up
  ip link set v-$ns netns $ns
done
ip netns exec app sh -c 'ip addr add 10.80.0.10/24 dev v-app; ip link set v-app up; ip link set lo up; ip route add default via 10.80.0.1'
ip netns exec cli sh -c 'ip addr add 10.80.0.20/24 dev v-cli; ip link set v-cli up; ip link set lo up; ip route add default via 10.80.0.1'
ip netns exec app python3 -m http.server 80 >/tmp/hp.log 2>&1 &
sysctl -w net.ipv4.ip_forward=1
```

Now publish it, the way the last lesson taught — a DNAT rule and nothing more. The published address is
the bridge's own `10.80.0.1`, standing in for a host address:

```bash
iptables -t nat -A PREROUTING -d 10.80.0.1 -p tcp --dport 8080 -j DNAT --to-destination 10.80.0.10:80
```

Prove the publish works from outside the subnet. Not from the peek shell — and that exclusion is a
finding, not a formality. Dial it from here and you get nothing:

```bash
curl -s -o /dev/null -m 3 -w 'from the translator itself -> %{http_code}\n' http://10.80.0.1:8080
iptables -t nat -L PREROUTING -n -v | grep 8080
```

```
from the translator itself -> 000
    0     0 DNAT       tcp  --  *      *       0.0.0.0/0            10.80.0.1            tcp dpt:8080 to:10.80.0.10:80
```

**Zero packets.** `PREROUTING` is the hook for traffic that *arrives on an interface*, and a connection
this machine originates itself never arrives anywhere — it is handed to the routing decision from
`OUTPUT` and skips the chain entirely. So build a client that genuinely is outside, on its own subnet
with a route in:

```bash
ip netns add ext
ip link add v-ext type veth peer name p-ext
ip link set v-ext netns ext
ip addr add 10.81.0.1/24 dev p-ext && ip link set p-ext up
ip netns exec ext sh -c 'ip addr add 10.81.0.20/24 dev v-ext; ip link set v-ext up; ip link set lo up
                         ip route add default via 10.81.0.1'
ip netns exec ext curl -s -o /dev/null -m 3 -w 'from outside the subnet -> %{http_code}\n' http://10.80.0.1:8080
```

```
from outside the subnet -> 200
```

One more line before you dial from inside, and it is the difference between seeing this bug and never
believing it exists:

```bash
# br_netfilter puts BRIDGED frames through conntrack too, which would quietly un-NAT the reply
# on our behalf and hide the whole problem. Off for this experiment; the teardown puts it back.
sysctl -w net.bridge.bridge-nf-call-iptables=0
```

This shell is the host's network namespace, so that setting is **the machine's**, not this lab's — it
changes reply handling for every Docker bridge on the box while it is `0`, which is exactly why the
teardown below restores it. (It defaults to `1` anywhere Docker or Kubernetes has ever run, which is
also why the hairpin bug is famously hard to reproduce on a laptop and perfectly reliable in a cluster
that has tuned it.)

> **Predict first —** now dial the *same published address and port* from `cli`, the namespace sitting
> on the same bridge as `app`. The DNAT rule is on `PREROUTING`, which every packet arriving on that
> bridge walks, so the rewrite will certainly fire. Will `cli` get its `200`? Trace the reply's journey
> before you answer: after the rewrite, what source address does `app` see, and where will `app` send
> its reply?

```bash
ip netns exec cli curl -s -o /dev/null -m 3 -w 'from cli -> %{http_code}\n' http://10.80.0.1:8080 \
  || echo 'from cli -> nothing came back'
```

It hangs and gives up. And the DNAT did fire — check its counter, which is the habit the last lesson
built:

```bash
iptables -t nat -L PREROUTING -n -v | grep 8080
```

The packet counter has moved. The rewrite happened, `app` received the request, and `app` answered.
Watch the answer go to the wrong place:

```bash
ip netns exec app timeout 5 tcpdump -n -i v-app -c 4 tcp port 80 &
sleep 1
ip netns exec cli curl -s -o /dev/null -m 3 http://10.80.0.1:8080
```

`app` sees a request `from 10.80.0.20` — because DNAT rewrote only the *destination*. So `app` does what
any host does with a reply: it looks up `10.80.0.20`, finds it on its own directly-connected subnet, and
sends the reply **straight across the bridge**, never going near `10.80.0.1`. The reply arrives at `cli`
with a source of `10.80.0.10:80`.

And `cli` throws it away. `cli` opened a connection to `10.80.0.1:8080`. It has a socket, and Act I told
you what that socket is: a four-tuple. A segment arriving from `10.80.0.10:80` matches no socket it
holds, so from `cli`'s point of view an unrelated machine has sent it an unsolicited packet. The reply
was delivered perfectly and discarded on arrival.

**This is the shape called a hairpin** — a packet that enters and leaves by the same interface — and the
fix follows directly from the diagnosis. The problem is that the reply skipped the box that holds the
translation, so make the reply *have* to come back through it. If the request's source is also rewritten
to the bridge's address, `app` will have to send its reply to `10.80.0.1`, which is where the conntrack
row lives to undo both rewrites at once:

```bash
iptables -t nat -A POSTROUTING -s 10.80.0.0/24 -d 10.80.0.0/24 -j MASQUERADE
ip netns exec cli curl -s -o /dev/null -m 3 -w 'from cli -> %{http_code}\n' http://10.80.0.1:8080
```

`200`. That rule says something worth reading out loud: *masquerade traffic whose source and
destination are both on this subnet* — a rule that would be pointless on any normal network, and is
mandatory the moment a translated address lives on the same segment as the clients dialling it. `app`
now sees the request as coming from the bridge, replies to the bridge, and the reader on the bridge
reverses both rewrites. It also has the cost you would expect: `app`'s access log now says
`10.80.0.1` for every internal client, which is the same identity erasure the proxy section of
[Act III's HTTP lesson](../act-3-the-internet/04-http.md#who-chose-the-machine-in-the-middle) made you
sit with, arriving this time from the kernel rather than from a header.

Hold the general form, because it recurs: **a Pod that cannot reach its own Service, reached through
the Service address, is this bug.** Kubelet has a setting called `hairpin-mode` and now you know what it
must be doing and what it must cost.

**Tear it down:**

```bash
iptables -t nat -D PREROUTING -d 10.80.0.1 -p tcp --dport 8080 -j DNAT --to-destination 10.80.0.10:80
iptables -t nat -D POSTROUTING -s 10.80.0.0/24 -d 10.80.0.0/24 -j MASQUERADE
sysctl -w net.bridge.bridge-nf-call-iptables=1
pkill -f 'http[.]server'
for ns in app cli ext; do ip netns del $ns; done ; ip link del br1 ; ip link del p-ext
```

Delete the two rules **by name**, and resist the urge to reach for `-F PREROUTING` instead. You are in
the host's namespace: that chain also holds Docker's own `-j DOCKER` jump, and flushing it breaks every
published port on the machine until `dockerd` happens to rewrite it. Note also that deleting a namespace
does not kill what was running inside it — the `http.server` processes survive with no namespace to live
in, hence the `pkill`, bracketed so the pattern cannot match the shell running it.

### What is the third table for?

You have used two of netfilter's tables. `filter` decides whether a packet lives. `nat` decides what its
addresses become. There is a third, and its verb is neither: `mangle` **annotates**.

The annotation that matters is a **mark** — a 32-bit integer the kernel attaches to a packet as it moves
through the stack. It is not a header field. It does not appear on the wire, no other machine will ever
see it, and it is gone the moment the packet leaves. Which raises the only question worth asking about
it: what use is a label that nothing outside this kernel can read?

The answer is that something *inside* this kernel reads it — the routing layer, which has one more
floor than you have stood on. Act II showed you a glimpse of it and moved on: if your `/proc/net/route`
had no default row, you ran `ip rule show`, saw a `lookup 2` beside `lookup main`, and were told that
"the routing table" had always been a simplification. Here is what it was simplifying.

A host can hold **many** numbered routing tables. Before the kernel looks a destination up, it walks a
list of **rules** that decides *which* table to look it up in — that list is `ip rule`, it is consulted
ahead of the route lookup rather than inside it, and among the things a rule is allowed to match on is a
mark. That is the join, and now the two halves fit together:

```
   iptables -t mangle ... -j MARK --set-mark 1     a netfilter rule writes a label
   ip rule add fwmark 1 table 100                  the routing layer reads that label
   ────────────────────────────────────────────────────────────────────────────────
   a firewall match now selects a route. that is the entire trick, and it is
   how every VPN, every multi-homed host and every egress gateway steers traffic.
```

Prove it in a throwaway namespace, where a wrong route costs you nothing. In your normal terminal:

```bash
docker run --rm -it --privileged nicolaka/netshoot
```

Confirm two destinations work, then mark one of them and send only the marked traffic to a table whose
only route is a dead end:

> **Predict first —** the mark is written in `mangle OUTPUT` and matched by a rule that selects table
> 100, whose single route is a blackhole. Nothing about `1.1.1.1` appears in any routing table. So which
> of the two `curl`s below fails, and — the part that matters — is the failure a *routing* failure or a
> *firewall* failure? What error do you expect?

```bash
curl -s -o /dev/null -m 3 -w '1.1.1.1 before -> %{http_code}\n' http://1.1.1.1/
iptables -t mangle -A OUTPUT -d 1.1.1.1 -j MARK --set-mark 1
ip route add unreachable default table 100
ip rule add fwmark 1 table 100
ip route get 1.1.1.1 mark 1
ip route get 1.1.1.1
curl -sS -m 3 -o /dev/null http://1.1.1.1/ ; echo "1.1.1.1 after -> exit=$?"
curl -s -o /dev/null -m 3 -w 'example.com   -> %{http_code}\n' https://example.com
```

```
1.1.1.1 before -> 301
RTNETLINK answers: Host is unreachable
1.1.1.1 via 172.17.0.1 dev eth0 src 172.17.0.3 uid 0
    cache
curl: (28) Connection timed out after 3004 milliseconds
1.1.1.1 after -> exit=28
example.com   -> 200
```

**Two `ip route get` calls, one destination, one field of difference, two different answers** — that is
the claim, proved. With the mark, the kernel has no route at all; without it, the same address routes out
`eth0` as it always did. Nothing dropped the packet. A lookup simply failed.

Which makes the client's experience worth a second look, because it is *not* the error you would
expect. `exit=28` — a plain timeout, the same silence a `DROP` produces — where a routing failure at
`connect()` time would have given you `exit=7` and "Network is unreachable" immediately. The reason is
the order of operations you have just built: the socket did its own route lookup first and succeeded,
because at that moment the packet carried no mark; the mark is written in `mangle OUTPUT`, *after* that
decision, and the failed second lookup happens somewhere the kernel has no way to report back to the
application. So the packet is discarded with nobody to tell. A routing error, not a firewall error, and
the application cannot distinguish the two — which is the whole
point. No rule dropped anything. A `mangle` rule wrote a number on the packet, the policy layer read
that number and sent the packet to a different routing table, and that table had no way to the
destination. **`filter` can refuse a packet; `mangle` can change where a packet is even trying to go.**
Read the two sides and they are visibly sharing one field — note that neither command reads a mark on a
*flow*, because the mark does not live there — run `conntrack -L` here and you get
`0 flow entries have been shown`, since nothing in this namespace's ruleset has asked a question about
state yet, so the tracker was never engaged at all. (Drill 10 builds a whole diagnosis on that fact.)
What you *can* read is the rule that writes the mark and the policy that consumes it:

```bash
iptables -t mangle -L OUTPUT -n -v
ip rule show
```

Undo it:

```bash
ip rule del fwmark 1 table 100 ; ip route del unreachable default table 100
iptables -t mangle -F OUTPUT
```

### Can a flow opt out of being remembered?

One table left, and it exists because of a number Act III made you look at. Every flow costs a
conntrack row; `nf_conntrack_max` is a ceiling chosen at boot; a packet the kernel cannot record is a
packet it drops, silently. Given all that, here is a fair question: if a flow does not need NAT and does
not need stateful filtering, must it still pay for a row?

The `raw` table is the answer, and its whole reason for existing is *where it sits*. It runs at a
priority **before** connection tracking, which is the only place from which a decision about tracking
can be made at all. Still in the throwaway container:

```bash
conntrack -C
iptables -t raw -A OUTPUT -d 1.1.1.1 -j NOTRACK
curl -s -o /dev/null -m 3 http://1.1.1.1/
conntrack -L -d 1.1.1.1 2>&1 | tail -1
```

The connection succeeds and leaves no row. `NOTRACK` is not a filter and not a rewrite; it is an
instruction to the tracker to look away — so `raw`'s verb, the fourth and last, is **exempts**. Four
tables, four verbs, and you have now used every one of them: `filter` decides, `nat` rewrites, `mangle`
annotates, `raw` exempts.

Now the price, which is exactly the two things the table was paying for. That flow can no longer be
NATted — there is nowhere to write the mapping. And it can no longer match `--ctstate ESTABLISHED`,
which means the firewall you built in the last lesson would now break it: a default-deny `INPUT` with a
single conntrack rule has no rule that admits an untracked reply. That is the trade, stated plainly:
**you can stop paying for the memory, at the cost of everything the memory was buying.** It is the right
call for high-volume traffic that is neither translated nor filtered — and a very effective way to
break a firewall by "optimising" it.

Do not take the second half on trust — it is four lines, and it is the last lesson's firewall verbatim:

```bash
iptables -P INPUT DROP
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
curl -sS -m 4 -o /dev/null -w 'NOTRACKed dest -> %{http_code}\n' http://1.1.1.1/ ; echo "exit=$?"
curl -sS -m 4 -o /dev/null -w 'tracked dest   -> %{http_code}\n' http://1.0.0.1/ ; echo "exit=$?"
```

```
curl: (28) Connection timed out after 4003 milliseconds
NOTRACKed dest -> 000
exit=28
tracked dest   -> 301
exit=0
```

Same machine, same firewall, same single rule — and one destination is unreachable because a `raw` rule
three sections ago told conntrack to look away from it. The reply came back and arrived at an `INPUT`
chain whose only `ACCEPT` asks a question about a row that does not exist. Check
`iptables -L INPUT -n -v | head -3` and you will find the policy counter carrying those packets.

```bash
iptables -P INPUT ACCEPT ; iptables -F INPUT
iptables -t raw -F OUTPUT
exit
exit
```

> **You understand this when you can** name what each of the four tables does to a packet in one verb
> apiece, explain how a `mangle` mark changes a routing decision without any rule dropping anything,
> and say what a flow gives up by being `NOTRACK`ed and why that table has to run before conntrack
> rather than after.

**Where you are now** — You can explain why `MASQUERADE` has to rewrite ports as well as addresses,
derive its per-destination ceiling from the one field it has left to vary, and recognise a one-second
latency tail as a port-allocation collision. You can diagnose a hairpin by tracing where the reply
went instead of where it should have. And you can use `mangle` and `raw` — the two tables that neither
filter nor translate — to steer a packet by routing table, or to exempt it from being remembered at all.

Every mechanism in these three lessons has rewritten a **header**. That is the ceiling on all of it, and
you have felt where it bites: netfilter decides on the first packet, before there is any payload to
read. Which leaves one job it cannot do, and it is the job you will meet everywhere in a cluster. Act
III's proxies could read a whole HTTP request — but every one of them required the client to *address
them*. Now suppose the clients are containers somebody else built, dialling `example.com` directly, and
you must route every one of their connections through a proxy of yours without editing a single client.
You have a rule that can rewrite a destination, so getting the packet to your proxy is easy. Work out
what your proxy will *know* when that connection arrives — and whether it can still find out where the
client was actually trying to go.

---

← Prev: **[The stateful firewall](03b-the-stateful-firewall.md)** · ↑ **[Act IV overview](README.md)** · Next: **[The transparent proxy](03d-the-transparent-proxy.md)** →
