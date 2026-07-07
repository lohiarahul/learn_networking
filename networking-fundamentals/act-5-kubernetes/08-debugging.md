# The debugging method — five questions in order

This is the file the whole course was written to make possible. Everything before it was so that this would be easy. [The whole stack](../the-whole-stack.md) showed the packet *succeeding*, layer by layer; this is what you do when one of those layers lies.

When a network call fails in Kubernetes, the failure is somewhere in a tall stack: DNS, routing, NAT and firewall, TCP, and finally the application. The mistake almost everyone makes is to guess — to restart the Pod, bump the replica count, sprinkle retries, and stare at application logs for a problem that lives four layers below the application.

The cure is to stop guessing and **walk down the stack in order**, asking five questions, where each question has an exact file that answers it and a tool that reads that file. The five questions descend from Act III to Act I: name resolution, then routing, then NAT/firewall, then TCP, then the app.

You ask them in order because a failure at a lower layer makes every higher layer look broken; if DNS is wrong, nothing above it can possibly work, and there is no point inspecting TCP until you know the name resolved to the right address.

Hold the orientation question the entire way down: *what is the file here, who reads it, who writes it?* Every one of these five has a concrete answer.

> **On your own machine —** the same five questions work when it is not a cluster at all. [Act V in the wild](in-the-wild.md) translates each one into its macOS command — and walks them against the failure you are most likely to actually hit: `kubectl` unable to reach the cluster.

<!-- figure: debug-five-questions -->

```
  Question 1  DNS        →  /etc/resolv.conf, CoreDNS A records      (Act II / CoreDNS)
  Question 2  Routing    →  ip route, ip route get                    (Act II / CNI)
  Question 3  NAT/FW     →  iptables -t nat, conntrack, NetworkPolicy (Act IV / Services)
  Question 4  TCP        →  tcpdump: SYN / SYN-ACK / RST              (Act II–III)
  Question 5  Application→  ss -tlnp: is anything listening, where?   (Act I)
            ───────────────────────  read top to bottom, stop at the first lie  ───────────────────────
```

---

### Question 1 — Is it DNS?

The first thing a connection-by-name does is resolve the name, so it is the first thing to check. The file is the Pod's `/etc/resolv.conf` (is the nameserver even reachable?), and the test is a `dig` against CoreDNS (does it return an A record, and is that record the ClusterIP you expect?).

```
cat /etc/resolv.conf
dig database.data.svc.cluster.local @10.96.0.10
```

CORRECT — an answer, and the IP is a real ClusterIP from the service range:

```
;; ANSWER SECTION:
database.data.svc.cluster.local. 30 IN A 10.96.55.10     ← got a ClusterIP. good.
;; Query time: 1 msec
```

BROKEN, flavor A — `NXDOMAIN`: the name does not exist. The Service is misspelled, in a different namespace, or you under-qualified the name and `ndots` walked the wrong search domains.

```
;; ->>HEADER<<- opcode: QUERY, status: NXDOMAIN          ← name resolves to nothing
;; ANSWER SECTION:                                        ← empty
```

BROKEN, flavor B — timeout, no response at all: CoreDNS itself is unreachable or down. Check `kubectl get pods -n kube-system` for the CoreDNS Pods.

```
;; connection timed out; no servers could be reached      ← can't even reach the nameserver
```

NXDOMAIN and timeout are different diseases: NXDOMAIN means "I asked and the answer is *no such name*" (a naming/namespace problem); timeout means "I couldn't ask at all" (CoreDNS or the path to it is down). Do not confuse them.

---

### Question 2 — Is it routing?

DNS gave you an IP. Can the Pod actually reach that IP — is there a route, and out which interface? The file is the routing table inside the Pod.

```
ip route
ip route get 10.96.55.10
```

CORRECT — a route exists and `route get` resolves to a device:

```
default via 10.244.1.1 dev eth0                          ← a default route exists
10.96.55.10 dev eth0 src 10.244.1.7                       ← route get found a path out eth0
```

BROKEN — no route, or `route get` fails. The CNI didn't install routing, or the Pod's namespace is isolated, or the destination CIDR isn't routed from here.

```
RTNETLINK answers: Network is unreachable                 ← no route to the destination
```

No route means the packet never even leaves the namespace correctly; this is a CNI/routing problem (the file from the CNI chapter), not a Service or app problem. Recall: ClusterIPs are routed because the service CIDR routes back to the node where iptables intercepts it — if even that route is missing, fix routing before anything else.

---

### Question 3 — Is it firewall / NAT?

The route exists. Now: does the Service's DNAT rule exist to rewrite the ClusterIP onto a Pod, is the connection being tracked, and is a NetworkPolicy silently dropping the packet? These are node-level files.

```
iptables -t nat -L KUBE-SERVICES -n | grep 10.96.55.10
conntrack -L | grep 10.96.55.10
kubectl get networkpolicy -n data
```

CORRECT — a DNAT rule for the Service exists and conntrack shows the connection mapped:

```
KUBE-SVC-ABCD  tcp -- 0.0.0.0/0  10.96.55.10  tcp dpt:80    ← Service has its chain
tcp 6 ... src=10.244.1.7 dst=10.96.55.10 ... [ASSURED]       ← conntrack tracking the flow
```

BROKEN, flavor A — no `KUBE-SVC` rule for the ClusterIP: the Service has no endpoints (no Pods match its selector), so kube-proxy wrote no DNAT target. `kubectl get endpoints database -n data` will show `<none>`.

```
(no output)                                               ← no DNAT rule = nowhere to send it
```

BROKEN, flavor B — a NetworkPolicy is dropping it. There *is* a policy in the target namespace, the SYN never gets a reply, and conntrack shows the connection stuck in `SYN_SENT` rather than `ASSURED`:

```
tcp 6 ... src=10.244.1.7 dst=10.244.2.3 ... SYN_SENT       ← sent, never confirmed = dropped
```

A NetworkPolicy drop and a "nothing listening" drop look similar here; Question 4 tells them apart by showing whether the SYN even reaches the destination Pod.

---

### Question 4 — Is it TCP?

If DNS, routing, and NAT are all clean, watch the actual packets. The file is the wire itself, read with `tcpdump`. You are looking for the three-way handshake: SYN out, SYN-ACK back.

```
tcpdump -i any host 10.244.2.3 and port 8080 -nn
```

CORRECT — full handshake, the connection establishes:

```
IP 10.244.1.7.51000 > 10.244.2.3.8080: Flags [S]          ← SYN out
IP 10.244.2.3.8080 > 10.244.1.7.51000: Flags [S.]         ← SYN-ACK back. handshake works.
IP 10.244.1.7.51000 > 10.244.2.3.8080: Flags [.]          ← ACK
```

BROKEN, flavor A — SYN goes out, nothing comes back: either nothing is listening on that port, or a firewall/NetworkPolicy is dropping the SYN silently. (You distinguish these with Question 5 and Question 3 respectively.)

```
IP 10.244.1.7.51000 > 10.244.2.3.8080: Flags [S]          ← SYN out
(silence)                                                  ← no reply: dropped, or nothing home
```

BROKEN, flavor B — SYN gets a RST back: the host is reachable but the port is closed — something is there, but nothing is listening on *that* port.

```
IP 10.244.1.7.51000 > 10.244.2.3.8080: Flags [S]
IP 10.244.2.3.8080 > 10.244.1.7.51000: Flags [R.]         ← RST: port closed, app not on 8080
```

There is a third shape worth naming in one line: if the handshake *completes* and then the connection just stalls with no data, the network is fine and you are looking at an application-layer problem (slow query, deadlock, waiting on something else) — stop blaming the network.

You have met both of the broken shapes before, in different clothes. Act I's SYN scan taught you that a RST is a *live kernel's answer* — a reachable machine saying "nothing is listening there," which is why the scanner could tell a closed port from an unanswered one. Act IV taught you `DROP`: a rule that discards a packet and says nothing at all. Those two facts are enough to read the tcpdump without memorizing anything: **silence means the packet was killed before anything could answer it** (a `DROP` somewhere: a firewall, a NetworkPolicy, a black hole), and **a RST means it arrived somewhere alive that refused that port.** Silence points up to Question 3; RST points down to Question 5.

`DROP` has a sibling worth knowing now, because Kubernetes uses it: **`REJECT`** discards the packet too, but sends an answer back — a RST for TCP, or an ICMP port-unreachable. So a filter rule can produce *either* shape, deliberately, and which one an operator chose is information about their intent.

That single distinction is the most useful thing tcpdump tells you, and it is the reason to reach for it before reaching for logs.

> **Check yourself —** Two Pods cannot reach a Service. In case A the client's `connect()` fails instantly with "connection refused"; in case B it hangs for 30 seconds and times out. Which of the five questions do you go to for each, and why is the fast failure the *easier* bug?

<details>
<summary>Answer</summary>

Both are Question 3, approached from opposite ends. The instant refusal means something *answered* — a RST or an ICMP port-unreachable came back — so a live kernel on the path made a decision and told you about it; go look for the rule that decided. The hang means nothing answered: a silent `DROP`, or a route into nowhere. The fast failure is the easier bug precisely because an answer arrived — somebody is home and told you no, which narrows the search enormously. Silence tells you only that the packet stopped, and finding *where* is the rest of the work.

</details>

---

### Question 5 — Is it the application?

Everything below the app checked out: the name resolved, the route existed, the DNAT fired, the SYN arrived. So is the application actually listening — and on the right address? The file is the destination Pod's socket table, read with `ss`.

```
ss -tlnp
```

CORRECT — listening on all interfaces, reachable from outside the Pod:

```
LISTEN 0 128 0.0.0.0:8080 ... users:(("server",pid=1,fd=3))   ← listening on 0.0.0.0, reachable
```

BROKEN, flavor A — nothing on the port at all: the process crashed, or it binds a different port than the Service targets.

```
(no line for :8080)                                       ← nothing listening here
```

BROKEN, flavor B — the classic — listening only on `127.0.0.1`:

```
LISTEN 0 128 127.0.0.1:8080 ... users:(("server",pid=1))  ← localhost only: unreachable from outside
```

This is the trap that survives a perfect DNS, route, NAT, and firewall. The app binds `127.0.0.1` instead of `0.0.0.0`, so it answers connections from *inside its own namespace* but not from anywhere else. The SYN arrives at the Pod (Question 4 saw it) and the kernel RSTs it because nothing is listening on a public address — yet `ss` *inside* the Pod cheerfully shows it "listening." Every layer is green and it still doesn't work, because the app is listening on the one address no other Pod can use. The fix is in the app's config (`bind 0.0.0.0` / `--host 0.0.0.0`), not anywhere in the network.

---

### See the method solve a real bug

The five questions above are the reference. To watch them run end to end on a real, plausible failure — *"a Pod in namespace `app` cannot reach a Service named `database` in namespace `data`,"* where the app logs only `dial tcp: i/o timeout` — work through [the worked failure](09-debugging-walkthrough.md). Try to solve it yourself first; the walkthrough shows every command and its output, and the root cause is somewhere you have already learned to look.

Then stop reading answers. [Diagnose it](diagnose.md) breaks a real cluster four different ways and hands you nothing but the ticket — including two failures that produce the identical symptom from different root causes, which is the case no reference card can prepare you for by being read.

> **You understand this when you can** run these five in order without thinking and name which file each one reads: Question 1 reads `/etc/resolv.conf` and asks CoreDNS for an A record; Question 2 reads `ip route`; Question 3 reads `iptables -t nat` and the conntrack table; Question 4 reads the wire with `tcpdump`; Question 5 reads the socket table with `ss`. The bug is always in one of those five files. Read them top to bottom and stop at the first one that lies.

**On your own machine —** every one of these five questions has a macOS command, and the tell you will use most — *a number works and the name doesn't, so it's DNS* — needs two of them. [Act V in the wild](in-the-wild.md) has the translations, and the same walk for when `kubectl` itself is the thing that cannot connect.

---

← Prev: **[Network Policy](07-network-policy.md)** · ↑ **[Act V overview](README.md)** · Next: **[The method in action — a worked failure](09-debugging-walkthrough.md)** →
