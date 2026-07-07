# CoreDNS — /etc/hosts for the cluster

A Service gives you a stable ClusterIP. But nobody wants to hardcode `10.96.55.10` into their app — that number is allocated dynamically and means nothing. You want to dial `database` by name. In Act II you learned the oldest name-resolution file in the world, `/etc/hosts`, and then DNS, the network service that scales it.

Act II also left you with a sentence about Kubernetes you could not check: that every Pod is born pointing at a cluster nameserver, with a `search` list that completes short names. You now have Pods. So the job here is verification, and it is a real one — that `search` list has an *order*, the order has consequences, and the consequences are the single most common way a working cluster looks broken. Read the file kubelet wrote and see whether you can predict the queries before you watch them go out.

### Why can't we just dial the ClusterIP?

ClusterIPs are stable relative to Pods, but they are still assigned by the cluster at Service-creation time, and they differ between every cluster and every environment. Wiring them into code or config means rewriting config for every deploy. What you actually want is the same thing humans have always wanted from a network: to say a name and have the machine find the address. Kubernetes already had the address — the ClusterIP — sitting in the API. It needed a nameserver that turns Service names into those ClusterIPs, automatically, for every Pod.

### So what is CoreDNS, really?

CoreDNS is a DNS server that runs as a Pod (usually two, for redundancy) inside the cluster and acts as the authoritative nameserver for the synthetic zone `cluster.local`. It watches the API server, and for every Service it publishes a DNS **A record** mapping the Service's fully-qualified name to its ClusterIP — for example `database.data.svc.cluster.local → 10.96.55.10`.

When a Pod asks "what is `database`?", CoreDNS answers with the ClusterIP, and then the packet to that ClusterIP hits the iptables DNAT from the previous file. CoreDNS is the index; Services are the entries — which makes it **`/etc/hosts` from Act II, with two differences that matter: the file writes itself by watching the cluster, and it answers over the wire instead of from disk.**

### How does every Pod know where to ask?

When kubelet starts a Pod, it writes the Pod's `/etc/resolv.conf` — you do not configure this, kubelet injects it. It looks like:

*(Almost. There is a field in the Pod spec that tells kubelet to write something else entirely, and a Pod carrying it gets a resolver that knows nothing about the cluster. Nobody sets it on purpose. Keep the shape of the file below in mind, because the fastest way to recognize that bug is to notice these three lines are missing.)*

<!-- annotate: pod-resolv-conf -->

```
nameserver 10.96.0.10
search default.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

The `nameserver` is itself a ClusterIP — CoreDNS is exposed as a Service (commonly `kube-dns`) at a fixed address like `10.96.0.10`. So the very first DNS query a Pod makes goes to a ClusterIP, which means it goes through the iptables DNAT to reach a CoreDNS Pod. DNS in Kubernetes rides on the Service machinery it serves.

### Why does a bare name like `database` resolve at all?

The `search` list and `options ndots:5` together are why `database` resolves to `database.data.svc.cluster.local` without you typing the full name. The rule: **if a name contains fewer than `ndots` (5) dots, the resolver tries appending each `search` domain before treating the name as absolute.** So a query for `database` (zero dots) is tried as `database.default.svc.cluster.local`, then `database.svc.cluster.local`, then `database.cluster.local`, then finally `database.` on its own. The first that returns an answer wins. This is the convenience: short names just work within a namespace.

It is also why DNS is so often the Kubernetes performance bottleneck. A partially-qualified name with fewer than five dots generates *multiple* queries — and each is sent for both A and AAAA records, so a single lookup of `api.example.com` (three dots, under five) can fire eight DNS queries before it gives up on the search domains and resolves the real external name. Multiply by every connection in a busy cluster and CoreDNS becomes a hotspot.

The fix many people reach for is a trailing dot — `api.example.com.` — which makes the name fully qualified (absolute) and skips the search list entirely. Knowing *why* that dot helps requires knowing `ndots`, and knowing `ndots` requires having read the file.

> **Check yourself —** Why does looking up an *external* name like `api.example.com` from inside a Pod cost more DNS queries than the same lookup from your laptop?

<details>
<summary>Answer</summary>

Because it has three dots, fewer than `ndots:5`, so the resolver tries every `search` domain first — `api.example.com.default.svc.cluster.local`, and so on — before trying the name as written. Each attempt goes out for both A and AAAA. A trailing dot (`api.example.com.`) marks it absolute and skips the whole search list.

</details>

### What does that lookup walk look like?

<!-- figure: coredns-ndots -->

```
  Pod (in 'default' ns): connect to "database"   /etc/resolv.conf: search + ndots:5
       │
       ▼   "database" has 0 dots (< 5) → walk the search list in order:
   query database.default.svc.cluster.local  ─►  CoreDNS (10.96.0.10) ─► NXDOMAIN
   query database.svc.cluster.local          ─►  CoreDNS              ─► NXDOMAIN
   query database.cluster.local              ─►  CoreDNS              ─► NXDOMAIN
   query database.                           ─►  (tried as absolute)  ─► NXDOMAIN
       │
       ▼   a Service in another namespace only resolves if you qualify it:
   query database.data.svc.cluster.local     ─►  CoreDNS              ─► A 10.96.55.10
                                                                          ↑ the ClusterIP
       │
       ▼
   Pod connects to 10.96.55.10  →  iptables DNAT  →  backing Pod   (previous file)
```

### Where is this written, and how do you query it by hand?

Read what kubelet wrote, then query CoreDNS by hand:

```
cat /etc/resolv.conf                                     the nameserver, search, ndots
dig database.data.svc.cluster.local @10.96.0.10          ask CoreDNS for the A record
dig kubernetes.default.svc.cluster.local                 the API server's own Service
```

The `kubernetes.default` Service exists in every cluster — it is the API server, fronted by a ClusterIP, resolvable by name. It's a reliable target to prove DNS works at all.

### Can you watch a bare name fan out into queries?

From inside any Pod, or from `kubectl debug --image=nicolaka/netshoot`:

> **Predict first —** with `ndots:5` in `/etc/resolv.conf`, how many separate DNS queries will a single bare service name fire off before it resolves?

```bash
cat /etc/resolv.conf
dig database.data.svc.cluster.local @10.96.0.10
dig +search database                 # watch the search list expand a bare name
```

The `ANSWER SECTION` of the `dig` output is one line: an A record whose value is the Service's ClusterIP. That single line is the whole job of CoreDNS — turn a name into the virtual IP that the iptables rules know how to DNAT. Run `kubectl get svc -n kube-system` and you will find CoreDNS listed as a Service (`kube-dns`) with its own ClusterIP — and that ClusterIP is the `nameserver` line in every Pod's `/etc/resolv.conf`. The nameserver is a Service; the Service has a ClusterIP; the ClusterIP is a lie made real by iptables. It is turtles, but every turtle is something you already built.

> **You understand this when you can** explain why `dig database` from a Pod in the `default` namespace does *not* reach a Service named `database` in the `data` namespace — `ndots:5` appends `default.svc.cluster.local` first, CoreDNS returns NXDOMAIN, and the `data` namespace is never tried unless you write `database.data` — and when you can read `/etc/resolv.conf` and predict exactly which fully-qualified names a short name will expand to, in order.

---

← Prev: **[Services and kube-proxy](03-services.md)** · ↑ **[Act V overview](README.md)** · Next: **[CNI — the veth-pair installer](05-cni.md)** →
