# `socket` — an ordinary connection, like your application makes

**What you see in `strace`:** `socket(AF_INET, SOCK_STREAM｜SOCK_DGRAM, …)` then `connect()`

Eleven tools, and their shared property is the one that makes them trustworthy: **they reach the
network the same way your application does.** No raw packets, no privileged channel. If one of these
works and your service does not, the difference is in your service. If one of these fails, so will your
service.

[`nc`](nc.md) · [`socat`](socat.md) ·
[`curl`](curl.md) · [`dig`](dig.md) ·
[`drill`](drill.md) · [`host`](host.md) ·
[`nslookup`](nslookup.md) · [`getent hosts`](getent-hosts.md) ·
[`iperf3`](iperf3.md) · [`ping`](ping.md) ·
[`openssl`](openssl.md)

---

## The name-resolution split that causes the most confusion

Four of these resolve names, and **they do not resolve them the same way.** This is the single most
valuable distinction on the page, because it is the difference between "DNS is fine" and "the
application still cannot connect".

| Tool | Path it takes | So it tells you |
|---|---|---|
| [`dig`](dig.md), [`drill`](drill.md) | straight to a nameserver over UDP/TCP, **skipping NSS entirely** | what DNS says |
| [`getent hosts`](getent-hosts.md) | glibc's Name Service Switch: `/etc/nsswitch.conf`, then `/etc/hosts`, then DNS | **what your application will actually get** |
| [`host`](host.md), [`nslookup`](nslookup.md) | a resolver library, but not the full NSS chain | roughly what DNS says |

Measured: `getent hosts localhost` opened **no socket at all** — `/etc/hosts` answered and NSS stopped
there. That is why *"`dig` works but the app can't resolve it"* is a real and common state, and why
`getent` is the tool that diagnoses it.

## `ping` is not a raw-socket tool any more

Measured in the lab image, `ping -c1 127.0.0.1` opens `AF_INET, SOCK_DGRAM` — **not `SOCK_RAW`**. These
are ICMP datagram sockets, gated by `net.ipv4.ping_group_range`, and they are the reason `ping` no
longer ships setuid. Its relatives [`arping`](../packet/arping.md) and
[`traceroute`](../packet/traceroute.md) *are* still [`packet`](../packet/README.md) tools, so `ping`
working while they fail is a permissions story, not a network one.

## What these tools are active about

Unlike [`procfs`](../procfs/README.md) or [`netlink`](../netlink/README.md), every tool here **sends traffic**. That is
their whole method: they produce the evidence rather than reading state that already exists. Two
consequences worth holding:

- They perturb what they measure. An `iperf3` run fills the link you are diagnosing.
- They appear in the other side's logs. A `curl` is a request; an `nc -z` is a connection attempt.

---

## What `socket` can never tell you

**Why it failed.** A socket tool gives you the verdict — connected, refused, timed out, resolved — and
almost never the cause. `Connection refused` means something sent a RST; it does not tell you whether
that was a firewall, a missing listener, or a NAT rule sending you somewhere unexpected.

For the cause you have to leave this interface: [`netlink`](../netlink/README.md) for the rule or route that did
it, [`packet`](../packet/README.md) to see whether the bytes left at all, [`probe`](../probe/README.md) for which kernel
function dropped them.

## What streams here

**Nothing.** There is no streaming form of an ordinary socket tool — each run is one exchange. `curl`
in a loop is polling, and a `watch nc -z` will miss a service that flapped between checks.

---

Taught in: [the TCP handshake](../../../networking-fundamentals/act-3-the-internet/01-tcp-handshake.md) ·
[HTTP](../../../networking-fundamentals/act-3-the-internet/04-http.md) · [DNS](../../../networking-fundamentals/act-2-two-machines/04-dns.md) ·
[Act II diagnose](../../../networking-fundamentals/act-2-two-machines/diagnose.md) ·
[TLS opened](../../../networking-fundamentals/act-8-trust/06-tls-opened.md)

Next: [`packet`](../packet/README.md), for when you need to see the bytes rather than the verdict.
