# The transparent proxy

**The wall** — A machine in the middle can read a whole HTTP request and decide things no packet-level
rule could ever decide. But every such machine, quietly, requires something of every client:
that the client **address the proxy**. A reverse proxy works because clients dial it believing it is the
server. A forward proxy works because someone configured the client to send everything there. Both
depend on the client's cooperation.

Now do the job without it. The clients are containers somebody else built — an image off a registry, a
vendor's agent, a job someone's CI submits — and they dial `example.com:443` directly, because that is
what they were written to do. You have no configuration file to edit, no environment variable to set,
and in some of them no shell to set it in. You still have to put every one of their outbound connections
through a proxy of yours, for inspection, or logging, or policy, or because Act X will want them
encrypted.

You are not short of a mechanism to get the packet to your proxy. You have spent three lessons on
rewriting destinations. That part is easy. What is not easy is what happens one millisecond later.

### What does the proxy know when the connection arrives?

Build it and find out. A proxy needs to accept a connection and look at it, so write the smallest thing
that does exactly that and nothing else — in the spirit of Act I's server, where you learn what a socket
is by holding one. In a throwaway container:

```bash
docker run --rm -it --privileged nicolaka/netshoot
```

```bash
cat > /tmp/proxy.py <<'PY'
import socket
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("0.0.0.0", 3129))
srv.listen(1)
print("proxy: listening on 3129", flush=True)

conn, peer = srv.accept()
print("the client is        :", peer, flush=True)
print("my end of the socket :", conn.getsockname(), flush=True)
conn.close()
PY
```

That is deliberately every question a socket can be asked about itself: who is at the far end, and what
address is mine. A proxy needs two facts to do its job — who is talking to me, and **who were they
trying to reach** — so as you run this, keep score of which of the two you actually get. Without the
second, a forwarding proxy cannot forward: it has a byte stream and nowhere to send it.

Now capture a connection that was never addressed to you. `REDIRECT` is the rewrite for exactly this —
a special form of DNAT meaning *"send this to a port on this machine"*, so you do not have to name an
address you might not know:

> **Predict first —** the `curl` below asks for `1.1.1.1:80`. A `REDIRECT` rule will send it to your
> listener on port 3129 instead, and the listener will accept it and print both ends of its socket.
> Write down, before running it, what you expect `my end of the socket` to say. Then ask the harder
> question: from *inside* that accepted socket, is there any way left to discover that the client typed
> `1.1.1.1`?

```bash
python3 /tmp/proxy.py &
sleep 1
iptables -t nat -A OUTPUT -p tcp -d 1.1.1.1 --dport 80 -j REDIRECT --to-port 3129
curl -s -m 3 -o /dev/null http://1.1.1.1/ ; sleep 1
```

```
proxy: listening on 3129
the client is        : ('172.17.0.3', 49752)
my end of the socket : ('127.0.0.1', 3129)
```

(`curl` reports `exit=56` alongside this — the proxy accepts, prints, and closes without answering.
Expected, and not the point.) Note the first line while you are here: the client is the container's own
`eth0` address, not `127.0.0.1`. `REDIRECT` rewrote only the *destination*; the source was chosen by the
original route lookup toward `1.1.1.1` and never touched.

Read the middle line first, because it is the problem. **`my end of the socket` is your own proxy.** Of
course it is: the destination was rewritten in the `nat` table, and the `nat` table runs before the
packet is delivered to a socket at all — so by the time `accept()` returned, the address the client
actually dialled had been overwritten. Every tool you have for asking a socket about itself —
`getsockname()`, `getpeername()`, the `/proc/net/tcp` row from Act I — is downstream of the rewrite, and
so all of them tell you the truth about a packet whose truth you already destroyed. **You needed one
field to do your job and the mechanism that got you the connection is precisely the mechanism that ate
it.**

And notice what you do *not* have. There is no third line. You asked that socket every question a socket
answers, and not one of them came back `1.1.1.1` — so on the evidence in front of you the honest
conclusion is that this proxy cannot be built. Sit with that before reading on, because the way out is
not another socket call.

### Where did the original destination survive?

It survived. And it survived somewhere you have already read three times.

The rewrite was not a mutation the kernel performed and forgot. It could not be — Act III established
that a translation the kernel does not write down is a translation it cannot reverse, and this
connection's replies have to be un-rewritten on the way back. So the original destination is sitting in
the conntrack row for this flow, where it has been all along, in the field Act III had you point at.
`SO_ORIGINAL_DST` is a socket option that goes and reads it. Add it to the proxy and ask the same
socket the same question again — the option number is 80, and what comes back is a raw `sockaddr_in`:
two bytes of address family, then the port, then the four address bytes, which is why the unpacking
below looks the way it does. (`IP_TRANSPARENT`, option 19, is set here too; you will need it before the
end of the lesson and not before.)

```bash
pkill -f proxy.py
cat > /tmp/proxy.py <<'PY'
import socket, struct, sys
SO_ORIGINAL_DST = 80
IP_TRANSPARENT  = 19

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
if "--transparent" in sys.argv:
    srv.setsockopt(socket.SOL_IP, IP_TRANSPARENT, 1)
srv.bind(("0.0.0.0", 3129))
srv.listen(1)
print("proxy: listening on 3129", flush=True)

conn, peer = srv.accept()
print("the client is        :", peer, flush=True)
print("my end of the socket :", conn.getsockname(), flush=True)
try:
    raw  = conn.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
    port = struct.unpack("!H", raw[2:4])[0]
    print("SO_ORIGINAL_DST      :", (socket.inet_ntoa(raw[4:8]), port), flush=True)
except OSError as e:
    print("SO_ORIGINAL_DST      : unavailable —", e, flush=True)
conn.close()
PY
python3 /tmp/proxy.py &
sleep 1
curl -s -m 3 -o /dev/null http://1.1.1.1/ ; sleep 1
```

```
proxy: listening on 3129
the client is        : ('172.17.0.3', 49756)
my end of the socket : ('127.0.0.1', 3129)
SO_ORIGINAL_DST      : ('1.1.1.1', 80)
```

Same rule, same socket, same rewrite — and the destination you watched get destroyed is back. Nothing
about the connection changed; you simply asked a different subsystem.

That is conntrack's third job, and it is the one nobody advertises:

```
   Act III   — a NAT ledger      the kernel reverses its own rewrites
   Act IV 03b — a firewall oracle  a rule asks it "have I seen this flow?"
   here      — an API             a userspace program asks it "what did the client
                                  originally ask for?", through getsockopt()
```

One table, three consumers, and the third one is why transparent proxying is possible at all rather
than merely convenient.

Which suggests an experiment, and it is worth running because it fails in an instructive way. You met
`NOTRACK` in the last lesson as a way to stop paying for a row. If the row *is* the answer here, then
`NOTRACK` should blind the proxy while leaving the interception intact. Try it on the chain the flow
actually leaves by:

```bash
iptables -t raw -A OUTPUT -p tcp -d 1.1.1.1 --dport 80 -j NOTRACK
pkill -f proxy.py ; python3 /tmp/proxy.py & sleep 1
curl -s -o /dev/null -m 3 -w 'code=%{http_code}\n' http://1.1.1.1/ ; sleep 1
iptables -t nat -L OUTPUT -n -v | grep 3129
```

```
proxy: listening on 3129
code=301
    2   120 REDIRECT   tcp  --  *      *       0.0.0.0/0            1.1.1.1              tcp dpt:80 redir ports 3129
```

Two packets on that counter and no third — one from each of the two passes you ran earlier, because
`nat` counters accumulate for the life of the rule. **The proxy never saw this connection at all, and
`curl` reached the real `1.1.1.1`.** `NOTRACK` did not
blind the proxy; it deleted the proxy. The reason is the sharpest statement of this section's whole
point: NAT is *implemented on top of* the conntrack row, so a flow with no row does not get its
destination rewritten either. The `REDIRECT` counter is stuck where it was.

So there is no ruleset in which the interception works and the row is missing — they are the same row.
The thing you were about to think of as a lookup that might fail is a lookup that cannot fail without
taking the interception with it. Undo it:

```bash
iptables -t raw -F OUTPUT
iptables -t nat -D OUTPUT -p tcp -d 1.1.1.1 --dport 80 -j REDIRECT --to-port 3129
```

Take the `REDIRECT` rule out as well, and not merely for tidiness. `TPROXY` is the mechanism from here
on, and a live `nat` rule in this namespace keeps conntrack recording flows that the next experiment
depends on *not* being recorded. Leave it in place and the next section quietly tells you a different
story than the one it means to.

### What does REDIRECT cost, and what is the alternative?

You have a working interception in two lines: one rule and one socket option. Now find its edges,
because there are two and both matter.

**First, `REDIRECT` can only send traffic to *this* machine.** That is what the target means. It is
perfect for a proxy running beside the client and useless for handing traffic to a proxy elsewhere —
for which you would need full `DNAT`, and then you are back to needing an address.

**Second, and sharper: your proxy's own outbound connection has your proxy's source address.** The
proxy accepted a stream, and now it must open its own connection onward to `1.1.1.1:80`. It opens that
socket as itself, from its own address. So the server at the far end sees the proxy as the client, and
every conclusion it draws about who is talking to it — rate limits, geography, access rules — is a
conclusion about your proxy. You have met this erasure twice now, at two layers: as
[`X-Forwarded-For` in Act III](../act-3-the-internet/04-http.md#who-chose-the-machine-in-the-middle),
where a proxy writes a header and hopes, and as
[hairpin masquerade in the last lesson](03c-when-nat-runs-out.md), where the kernel did it. It is the
same erasure, and it is inherent to *"two connections, not one relay"*.

Which is what the second mechanism exists to fix. **`TPROXY` does not rewrite the packet at all.** It
leaves the destination as `1.1.1.1:80` and instead hands the packet to a local socket that has declared
itself willing to accept connections addressed to someone else — the `IP_TRANSPARENT` option your script
already knows how to set. Nothing was destroyed, so nothing has to be recovered.

The price is that it cannot be done with one rule, and the reason is instructive: a packet addressed to
`1.1.1.1` will be *routed* to `1.1.1.1` unless something intervenes before the routing decision. So you
have to intervene, with exactly the pair of tools the last lesson built:

```
   iptables -t mangle -A PREROUTING ... -j TPROXY --on-port 3129 --tproxy-mark 1
   ip rule add fwmark 1 lookup 100                  ─┐  "marked packets look up table 100"
   ip route add local default dev lo table 100      ─┘  "in which everything is local"
```

That is `mangle` + `MARK` + `ip rule` doing the job they were introduced for. `local` is the route type
that means *deliver this here rather than forward it*, so a marked packet bound for `1.1.1.1` is
delivered to this host's socket layer with its destination intact.

And note where `TPROXY` is legal: `mangle PREROUTING` only. It cannot be used on `OUTPUT`, which is not
an oversight — it is the target's whole nature. `TPROXY` is for traffic that is **passing through you**,
never for traffic you sent yourself. That single restriction tells you what it is for.

So run it on traffic that is passing through. Build a client that is not you, inside this same container
so nothing outside it is touched:

```bash
ip link add br9 type bridge && ip addr add 10.90.0.1/24 dev br9 && ip link set br9 up
ip netns add cli
ip link add v-cli type veth peer name p-cli
ip link set p-cli master br9 && ip link set p-cli up
ip link set v-cli netns cli
ip netns exec cli sh -c 'ip addr add 10.90.0.20/24 dev v-cli; ip link set v-cli up; ip link set lo up
                         ip route add default via 10.90.0.1'
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.bridge.bridge-nf-call-iptables=0
```

That last line is not boilerplate and it is the difference between this working and silently not
working. With `br_netfilter` at its default of `1`, a bridged frame runs the netfilter hooks in *bridge*
context, where `TPROXY` has no local delivery to perform — the rule matches, its counter climbs, and
your proxy never receives a thing. Unlike the same setting in the last lesson, this container has its
own network namespace, so here the change is scoped to the lab and disappears when you `exit`.

Note also that `cli` has no route to the internet — nothing masquerades `10.90.0.0/24`. That is
deliberate: `TPROXY` is the only thing that will ever answer it, so there is no "it worked before" to
confuse with success.

> **Predict first —** `cli` is about to `curl http://1.1.1.1/`, and the rules below will intercept it
> with `TPROXY` instead of `REDIRECT`. The proxy will print both ends of its socket again. Last time
> `my end of the socket` was the proxy's own address and port. What will it say this time — and what
> does that imply about whether `SO_ORIGINAL_DST` is still needed?

```bash
pkill -f 'proxy[.]py'
python3 /tmp/proxy.py --transparent &
sleep 1
iptables -t mangle -A PREROUTING -p tcp -s 10.90.0.20 --dport 80 -j TPROXY --on-port 3129 --tproxy-mark 1
ip rule add fwmark 1 lookup 100
ip route add local default dev lo table 100
ip netns exec cli curl -s -m 3 -o /dev/null http://1.1.1.1/ ; sleep 1
```

```
proxy: listening on 3129
the client is        : ('10.90.0.20', 55654)
my end of the socket : ('1.1.1.1', 80)
SO_ORIGINAL_DST      : unavailable — [Errno 2] No such file or directory
```

**`my end of the socket` is `1.1.1.1:80`.** Your proxy is holding a socket that claims to be a server it
is not, talking to a client at its real address, and it never had to ask a socket option for anything —
the four-tuple arrived intact because no rewrite ever happened.

Which is exactly why the last line now *fails*, and you should have predicted it: `SO_ORIGINAL_DST`
reads the NAT translation conntrack recorded, and here conntrack recorded no translation, because there
was none to record. Check for yourself — `conntrack -L | grep 10.90.0.20` comes back empty. The error is
`ENOENT`: you asked for a receipt that was never written.

So the two mechanisms are exact complements rather than alternatives. `REDIRECT` destroys the
destination and hands you a receipt to look it up with. `TPROXY` never destroys it, so the socket
already knows — and there is no receipt, because nothing was taken.

Line the trade up, because you will choose between these two in real systems:

```
                 REDIRECT                        TPROXY
   rules         one, in nat                     one in mangle + ip rule + a route
   destination   rewritten, recovered via        never touched
                 SO_ORIGINAL_DST (needs the
                 conntrack row to exist)
   client addr   lost on the proxy's own          can be preserved — the proxy may bind
                 outbound connection             the client's address as its own source
                                                 (not shown above: that is a second use of
                                                  IP_TRANSPARENT, on the OUTBOUND socket)
   works on      OUTPUT and PREROUTING           PREROUTING only: other people's traffic
   proxy must    know one socket option          hold IP_TRANSPARENT, and own a routing rule
```

**Tear it down** — one `exit` takes the namespace, the bridge, the rules and the routing table with it,
which is the whole reason we did this in a container:

```bash
exit
```

> **You understand this when you can** explain why a proxy that receives a DNAT'd connection cannot
> learn the original destination from the socket itself, name where that destination did survive and the
> mechanism that reads it back, and say why `TPROXY` needs a routing rule while `REDIRECT` needs none.

### You have just built a service mesh

Not a toy version of one. The mechanism.

An init container runs once, before the application container in a Pod starts, inside the **same network
namespace** — and everything Act IV taught about namespaces says that "same network namespace" means
same interfaces, same routing table, and same netfilter tables. It writes `REDIRECT` rules: outbound
traffic to a sidecar's port, inbound traffic to another. Then it exits. The application container starts,
dials `payments.default.svc` directly because that is what its code says, and every byte it sends goes
through a proxy it does not know exists, which reads `SO_ORIGINAL_DST` to find out where the application
meant to go.

There is nothing else in it. If you have ever read a sidecar's iptables dump and found a wall of chains
with names like `ISTIO_REDIRECT`, you now know it is a jump table (lesson 03b) of `REDIRECT` rules
(this lesson) whose exemption lists are `RETURN`s, and that the proxy's magic trick is one `getsockopt`.
And you can now ask the good question about it, which is not *how does it work* but *what does it cost* —
a hop, a conntrack row, and a program in the path of every packet.

### The shadow it casts

Look at what you built from the client's side. `cli` opened a connection to `1.1.1.1:80`. It got answers.
Nothing in its socket, its routing table, its `/proc/net/tcp` row, or its logs differs in any way from a
conversation with the real server. A machine it never chose read every byte it sent and could have
changed any of them, and the client has **no mechanism whatsoever** for detecting this.

That should feel familiar. Act II's [ARP](../act-2-two-machines/01-ethernet-and-arp.md) trusted any
answer, and you were told to sit with it. This is the same shadow, with better tooling and a legitimate
job title. The only reason a transparent proxy cannot read your bank session is the sealed lock from
[Act III's TLS lesson](../act-3-the-internet/05-tls.md) — and now you can state precisely what a
corporate inspection box must do to get past it: refuse to relay those bytes untouched, terminate the
TLS itself, and present the client a certificate it will believe. (If you have read
[Act III's HTTP lesson](../act-3-the-internet/04-http.md#who-chose-the-machine-in-the-middle), you will
recognise the first of those three as declining the `CONNECT` tunnel a client asked for.) Everything hinges on *believe*. [Act VIII](../act-8-trust/05-certificates.md) is where you find
out what that word is made of, and why such a box has to be installed on the laptop rather than merely
plugged into the network.

**Where you are now** — You can intercept a connection that was never addressed to you, recover the
destination your own rewrite destroyed, and choose between the two mechanisms for doing it on the basis
of what each preserves rather than which one a tutorial showed you. You can read a sidecar's ruleset as
`REDIRECT` plus one socket option. And you can name the third role conntrack plays: an API, queried from
userspace, about a rewrite the kernel made on your behalf.

That is the netfilter floor complete. Four tables, five hooks, a jump table, a flow table consulted by
three different consumers, and every rewrite the kernel can perform on a header — and all of it,
without exception, **ends at the edge of this machine.** Two containers on one bridge share a switch. A
container reaching the internet borrows the host's address on the way out. A proxy intercepts traffic
that is already walking through its own kernel's hooks. Now put two private networks on two *different*
hosts. There is no shared switch to plug into, and the physical network in between would drop a
`10.90.0.0/24` packet on sight. You could reach for NAT one more time and translate each private
address into its host's — but work out what the far side would see as the sender, and then ask whether
anything on the far side could ever start a conversation in the *other* direction. So how do you make
two software switches, on two machines, behave like one wire — without asking the network in between
for permission?

---

← Prev: **[When NAT runs out](03c-when-nat-runs-out.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Overlay and VXLAN](04-overlay-vxlan.md)** →
