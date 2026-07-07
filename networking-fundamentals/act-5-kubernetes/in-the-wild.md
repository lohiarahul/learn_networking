# Act V in the wild — the five questions, on your own Mac

The act's payoff is a method, not a cluster: walk down the stack, one question per layer, and read the
file that answers it. A cluster is where the method is most valuable, but nothing about it is
Kubernetes-specific. This page runs the *same five questions* against your own laptop, with tools that
ship with macOS, and then against the thing most likely to break in your Act V lab: `kubectl` itself.

## The five questions, translated to macOS

Same order, same rule — **stop at the first one that lies.**

| # | The question | In the cluster | On your Mac |
|---|---|---|---|
| 1 | Is it DNS? | `/etc/resolv.conf` + `dig @10.96.0.10` | `scutil --dns` (the resolver macOS is *actually* using) then `dig example.com` |
| 2 | Is it routing? | `ip route get <ip>` inside the Pod | `route -n get 1.1.1.1` · `netstat -rn` |
| 3 | Is it firewall / NAT? | `iptables -t nat`, `conntrack -L`, NetworkPolicy | `sudo pfctl -sr` (packet-filter rules) · System Settings → Network → Firewall |
| 4 | Is it TCP? | `tcpdump` for SYN / SYN-ACK / RST | `nc -vz example.com 443` then `sudo tcpdump -i en0 -nn 'tcp[tcpflags] & (tcp-syn\|tcp-rst) != 0'` |
| 5 | Is it the application? | `ss -tlnp` in the destination Pod | `lsof -nP -iTCP -sTCP:LISTEN` |

Two of those translations are worth dwelling on, because they are the ones that catch people out.

**Question 1 is not `cat /etc/resolv.conf` here.** macOS keeps that file for compatibility but the real
resolver configuration lives in `configd`, can differ *per interface*, and changes when you join a VPN.
`scutil --dns` is the only honest answer to "which nameserver am I actually using," and it will
sometimes show you several, scoped to different domains — macOS's version of the cluster's search list.
The old tell still holds, though, and it is the fastest single test in computing: **a number works and
the name doesn't, so it's DNS.**

```bash
ping -c 2 1.1.1.1        # routing beyond your router, no names involved
dig +short example.com   # the name
```

**Question 3 has no `iptables`.** macOS uses **pf**, and `sudo pfctl -sr` prints its rules — but on a
stock Mac that list is nearly empty and the thing actually blocking you is the *application* firewall
(which allows or denies per binary, not per port) or a corporate VPN client. There is also no
`conntrack` to read, which removes the single most useful diagnostic in Act IV and Act V. That absence
is worth feeling: state tracking is what made a Service work in both directions from one rule, and on a
Mac you cannot look at it at all.

## When the broken thing is `kubectl`

The failure you will actually hit in this act is not a Pod that cannot reach a Service — it is
`kubectl` on your Mac unable to reach the cluster at all. `Unable to connect to the server` is the same
kind of vague error as `dial tcp: i/o timeout`, and it yields to the same walk. Only the files change:

```bash
kubectl config current-context                                   # 1. which cluster are you even asking?
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}{"\n"}'
docker ps --filter name=netlab                                   # 2. is the node container running?
curl -sk https://127.0.0.1:<port-from-above>/healthz              # 4. does the API server answer at all?
kubectl get --raw /healthz                                       # 5. does it answer *you*, authenticated?
```

Read them in that order and each failure is unambiguous. No context means kubeconfig, not networking. A
context but no container means the cluster is gone (Docker Desktop restarted, or the machine slept) —
`kind get clusters` confirms, and creating it again is the fix. A running container whose port does not
answer means the API server is still coming up. And `ok` from `curl -k` but a failure from `kubectl` is
not a network problem at all; it is authentication — the certificate in your kubeconfig no longer
matches the cluster, which is what happens when you delete and recreate a cluster of the same name.

That last one is the `127.0.0.1` trap of Act V's fifth question, one level out: every layer green, and
it still doesn't work, because the problem was never in the network.

## macOS vs Linux — the swaps this act needs

**Direct 1:1 swaps:**

| Container (Linux) | Your Mac (macOS) |
|---|---|
| `ping` / `dig` | `ping` / `dig` (same) |
| `ip route` (default gateway) | `route -n get default` · `netstat -rn \| grep default` |
| `ss -tlnp` | `lsof -nP -iTCP -sTCP:LISTEN` |

**No 1:1 here — and why:**

- **There's no `ip route` on macOS** (no iproute2). Finding your default gateway becomes
  `route -n get default` (one route) or `netstat -rn` (the whole table) — same routing-table concept
  from Act II, different command.
- **There's no `iptables` and no `conntrack`.** The filter engine is pf, and there is no readable
  connection-tracking table at all. Everything you learned in Act IV about DNAT and conntrack is real,
  but on this machine it lives inside the Linux VM Docker Desktop runs — which is exactly why the act's
  node-level commands go through `docker exec` into a kind node rather than running here.
- **`/etc/resolv.conf` is not authoritative.** Use `scutil --dns`.

---

↑ **[Act V overview](README.md)** · Back to the method: **[The five questions](08-debugging.md)** · Under fire: **[Diagnose it](diagnose.md)**
