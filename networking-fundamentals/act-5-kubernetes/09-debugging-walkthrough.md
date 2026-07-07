# The method in action — a worked failure

The five questions in [the debugging method](08-debugging.md) are the reference card. This is the method actually solving a bug, top to bottom, with every command and its real output. The value is in watching the discipline pay off: the failure is found at the very first question, and the rest of the walk is the good-debugger habit of *confirming the layers below are healthy* so you know there isn't a second problem hiding.

> **A Pod in namespace `app` cannot reach a Service named `database` in namespace `data`.** The app logs only `dial tcp: i/o timeout`. Walk all five questions.

> **Predict first —** you have one symptom, `i/o timeout`, and five layers it could be (DNS, routing, NAT/firewall, TCP, app). Before reading on: which layer do you bet is broken, and which single command would you run first to confirm it?

We `kubectl debug -it <app-pod> -n app --image=nicolaka/netshoot` and start at the top.

**Question 1 — DNS.** The app connects to the host `database` (just that, unqualified). We reproduce its resolution:

```
cat /etc/resolv.conf
nameserver 10.96.0.10
search app.svc.cluster.local svc.cluster.local cluster.local      ← note: app, not data
options ndots:5

dig database @10.96.0.10
;; ->>HEADER<<- opcode: QUERY, status: NXDOMAIN                    ← BROKEN
;; ANSWER SECTION:                                                  (empty)
```

NXDOMAIN. The name resolved to nothing. Why? `ndots:5` means `database` (zero dots, under five) is tried against the search list first: `database.app.svc.cluster.local`, then `database.svc.cluster.local`, then `database.cluster.local`. The Pod is in namespace `app`, so its first search domain is `app.svc.cluster.local` — but the Service lives in `data`. None of the search domains point at `data`, so every attempt is NXDOMAIN and the lookup fails. We confirm the Service is fine when properly qualified:

```
dig database.data.svc.cluster.local @10.96.0.10
;; ANSWER SECTION:
database.data.svc.cluster.local. 30 IN A 10.96.55.10              ← CORRECT, fully qualified
```

There it is. The Service exists, has a ClusterIP, and resolves perfectly — but only under its full cross-namespace name. The application asked for `database` and `ndots` never tried the `data` namespace. **Root cause found at Question 1: a missing namespace qualifier interacting with `ndots:5`.** The application must dial `database.data` (or the full `database.data.svc.cluster.local`), not `database`.

We could stop here — but a good debugger confirms the layers *below* the failure are healthy, so we know there isn't a second problem lurking. We continue, now using the resolved ClusterIP `10.96.55.10`.

**Question 2 — Routing.** Does the Pod have a route to that ClusterIP?

> **Predict first —** the ClusterIP `10.96.55.10` sits on no interface in the cluster. So what will `ip route get` inside the Pod say about it — no route, or a route out `eth0`?

```
ip route get 10.96.55.10
10.96.55.10 dev eth0 src 10.244.1.7                               ← CORRECT, route exists
```

Routing is clean — and if the answer surprised you, the Services lesson is where to go back to: the service CIDR is off-link, so the Pod's default route claims it like any other off-link address, and the DNAT happens *after* the routing decision, on the way out.

**Question 3 — NAT / firewall.** Does the Service's DNAT rule exist, and is anything blocking? (Run on the node.)

> **Predict first —** DNS was the only thing broken, so the Service itself is healthy. Given that, what should `iptables -t nat -L KUBE-SERVICES` show for `10.96.55.10` — and what would it show instead if the Service had no endpoints?

```
iptables -t nat -L KUBE-SERVICES -n | grep 10.96.55.10
KUBE-SVC-D4T4 tcp -- 0.0.0.0/0 10.96.55.10 tcp dpt:5432           ← CORRECT, DNAT chain present

kubectl get networkpolicy -n data
No resources found in data namespace.                             ← no policy blocking
```

A jump to a real `KUBE-SVC` chain, which is what a Service *with* endpoints looks like. Had the selector matched nothing, this line would read `REJECT` instead — an answer, not a rewrite, and the client would have failed instantly rather than timing out. No NetworkPolicy stands in the way either. NAT and firewall are clean.

**Question 4 — TCP.** When we connect to the *correct* name, does the handshake complete? (We test with the qualified name so DNS isn't in the way.)

```
nc -zv database.data.svc.cluster.local 5432
Connection to database.data.svc.cluster.local 5432 port [tcp] succeeded!

tcpdump -i any host 10.244.2.3 and port 5432 -nn
IP 10.244.1.7.52000 > 10.244.2.3.5432: Flags [S]
IP 10.244.2.3.5432 > 10.244.1.7.52000: Flags [S.]                ← SYN-ACK back. CORRECT.
```

The handshake completes once the name is right. TCP is clean.

**Question 5 — Application.** And the database is genuinely listening, reachable:

> **Predict first —** Question 4 already saw a SYN-ACK come back from the database Pod. Does that, on its own, prove the app is bound to `0.0.0.0` rather than `127.0.0.1` — or could `ss` still show something that would change your mind?

```
ss -tlnp        # inside the database Pod
LISTEN 0 244 0.0.0.0:5432 ... users:(("postgres",pid=1,fd=7))    ← 0.0.0.0, CORRECT
```

It does prove it, and this is the one place in the walk where Question 5 is redundant: a SYN-ACK from *outside* the Pod cannot come from a socket bound to that Pod's `127.0.0.1`, because no packet from another namespace can ever match a loopback-bound socket. Reading `ss` anyway costs one command and it is what you would need if the handshake had failed — the `127.0.0.1` trap is invisible from every layer except this one.

**Conclusion.** Four of five layers were healthy the entire time. The failure was at Question 1 and only Question 1: the application dialed the bare name `database`, and because the Pod lives in the `app` namespace, `ndots:5` expanded it against `app.svc.cluster.local` and the other search domains — never `data` — yielding NXDOMAIN, which the application surfaced as a generic `i/o timeout`. The fix is one string: change the app to dial `database.data`. No restart, no scaling, no retries would have helped, because nothing below DNS was ever broken. The method found it in the first question because the method reads the files in order, and the first file — `/etc/resolv.conf` plus a single `dig` — already contained the whole answer.

> **Check yourself —** The application reported `dial tcp: i/o timeout`, but the actual fault was an NXDOMAIN — a *fast, definite* "no such name." Why did a resolver failure surface to the app as a timeout, and what does that teach you about trusting the error string in a ticket?

<details>
<summary>Answer</summary>

Because the error the app prints is the error its own dial helper produced, several layers above the failure, and most clients wrap every dial failure in one generic message. A resolver walking four search domains, retrying, and eventually giving up can easily consume the client's dial deadline, at which point the client reports the deadline it hit rather than the NXDOMAIN it was handed. The lesson is the whole reason the method exists: an application-level error string tells you *when the app gave up*, not *what failed*. It is evidence that something is wrong, never evidence of which layer. Start at Question 1 regardless of what the ticket says the error was.

</details>

> **You understand this when you can** be handed a vague `i/o timeout` and, instead of guessing, run the five questions in order, prove four layers healthy, and pin the failure to the one file that lied — here, `/etc/resolv.conf` and an under-qualified name meeting `ndots:5`.

Now do it without the narration. [Diagnose it](diagnose.md) hands you four tickets with the symptom only, breaks the cluster for real, and tells you nothing about which layer to suspect.

---

← Prev: **[The debugging method](08-debugging.md)** · ↑ **[Act V overview](README.md)** · Next: **[Test yourself](test-yourself.md)** →
