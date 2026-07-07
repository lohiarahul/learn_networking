# Services and kube-proxy — what answers to a ClusterIP?

Act IV ended by handing you a task instead of an answer. A cluster gives you one stable address to dial for a service whose real processes are born and destroyed constantly; you know two ways an address can work — a device owns it, or a route leads to it — and Act IV showed you the machinery for a third, then told you to come here, go looking for that address with `ip addr` on every node, and see for yourself what is there before letting anyone settle it.

This lesson is built around that one experiment. Everything before it is the vocabulary you need in order to describe what you find, and there is not much of it: the name of the thing you are looking for, and the reason anybody wanted it.

### Why not just hand out a Pod's IP as "the database"?

Pods are mortal and their IPs are temporary. A Deployment kills a Pod and a fresh one comes up with a brand-new IP from the node's CIDR. So you cannot hand out a Pod IP as the address of "the database" — by tomorrow it points at nothing.

You need a *stable* address that fronts a *changing* set of Pods, and that distributes traffic across them, and that keeps working as Pods come and go. In Act IV you already learned the tool that rewrites a packet's destination on the fly: **DNAT**, an iptables rule that takes a packet headed for one address and silently rewrites it to another. A Service is that idea, applied to a virtual address.

### So what is a Service, really?

A Service is a stable virtual IP — the **ClusterIP** — plus a set of iptables rules that DNAT any packet sent to that IP onto one of the Service's backing Pod IPs. The ClusterIP comes out of a range the cluster reserves for itself: the service CIDR, `10.96.0.0/12` under kubeadm defaults and `10.96.0.0/16` on the kind cluster from [the lab lesson](01-lab-with-kind.md). What the cluster does with an address out of that range — whether it gives it to anything — is the experiment below.

The component that makes it real is **kube-proxy**, a daemon on every node that watches the API server. When you create a Service, kube-proxy writes DNAT rules into the node's `nat` table; when the Service's endpoints change (a Pod dies, another is born), kube-proxy rewrites those rules.

The "proxy" name is a historical fossil — modern kube-proxy in iptables mode proxies nothing; it programs the kernel's NAT engine and gets out of the way. The packet never passes through a userspace proxy. It is rewritten in the kernel, by a rule, at the same hooks you used in Act IV.

### What path does the packet actually take?

A packet from a Pod to a ClusterIP traverses a tree of chains. Each `KUBE-SVC-<hash>` is one Service; each `KUBE-SEP-<hash>` ("SEP" = service endpoint) is one backing Pod:

<!-- figure: k8s-service-path -->

```
  Pod does:  connect() to 10.96.55.10:80     ← the ClusterIP (exists in no interface)
       │
       ▼   packet enters the node's nat table, OUTPUT/PREROUTING jumps to:
  ┌─────────────────────── KUBE-SERVICES ───────────────────────┐
  │  match dst 10.96.55.10  tcp dpt 80   ──►  jump KUBE-SVC-XXXX │
  │  match dst 10.96.55.11  ...          ──►  jump KUBE-SVC-YYYY │   (one line per Service)
  └─────────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────── KUBE-SVC-XXXX ───────────────────────┐
  │  probability 0.333  ──►  jump KUBE-SEP-AAAA   (Pod 10.244.1.7)│
  │  probability 0.500  ──►  jump KUBE-SEP-BBBB   (Pod 10.244.2.3)│   load balancing
  │  (fallthrough)      ──►  jump KUBE-SEP-CCCC   (Pod 10.244.3.9)│   via statistic module
  └─────────────────────────────────────────────────────────────┘
       │   (probabilities chain so each endpoint gets an equal share)
       ▼
  ┌─────────────────────── KUBE-SEP-BBBB ───────────────────────┐
  │  DNAT  --to-destination 10.244.2.3:8080      ◄── the rewrite │
  └─────────────────────────────────────────────────────────────┘
       │
       ▼   conntrack records:  orig 10.96.55.10:80  ↔  reply 10.244.2.3:8080
       ▼
  packet now addressed to Pod 10.244.2.3:8080  →  routed via veth/bridge/overlay (Act IV)
       │
       ▼
  destination Pod does:  read()      ← write() on one machine became read() on another
```

The probabilities are the trick that makes one rule into a load balancer. iptables evaluates `KUBE-SEP-AAAA` with probability 1/3; if it doesn't match, `KUBE-SEP-BBBB` with probability 1/2 of the remaining two-thirds (= 1/3 overall); the last endpoint catches the rest. Three endpoints, one-third each, random per connection. Add a fourth Pod and kube-proxy rewrites every probability.

### How does the reply find its way back?

DNAT only rewrites the outbound packet. The reply from the Pod comes back addressed *from* `10.244.2.3:8080`, but the client believes it is talking to `10.96.55.10:80`. The same connection tracker from Act IV (`nf_conntrack`) recorded the mapping when the first packet went out, and it reverse-rewrites the reply so the client sees a response from the ClusterIP it dialed. This is why a Service "just works" in both directions from a single DNAT rule: conntrack remembers.

### Where in iptables do those rules live?

On a node, read the rules directly:

```
iptables -t nat -L KUBE-SERVICES -n          all Services: ClusterIP → KUBE-SVC chain
iptables -t nat -L KUBE-SVC-XXXX -n          one Service: probabilities → KUBE-SEP chains
iptables -t nat -L KUBE-SEP-BBBB -n          one endpoint: the DNAT to a Pod IP
conntrack -L | grep 10.96.55.10              the live ClusterIP→Pod mappings in flight
```

```
/proc/net/nf_conntrack                        every tracked connection, raw
/proc/sys/net/netfilter/nf_conntrack_max      the table's size limit
/proc/sys/net/netfilter/nf_conntrack_count    how full it is right now
```

### Can you prove no machine owns the ClusterIP?

On a node (or in a netshoot Pod with host network), pick a Service's ClusterIP and look for it:

> **Predict first —** will the Service's ClusterIP appear anywhere in `ip addr` on the node — and will a `curl` to it still answer?

```bash
kubectl get svc kubernetes -o jsonpath='{.spec.clusterIP}'   # e.g. 10.96.0.1
ip addr | grep 10.96.0.1
ip route get 10.96.0.1                                         # routed like any off-link address
```

Nothing owns that address — and yet `curl -k https://10.96.0.1:443/healthz` answers. That is the surprise: you are talking to an IP that exists on no network card in the entire cluster. The answer is in the rules, so go read them:

```bash
iptables -t nat -L KUBE-SERVICES -n | grep 10.96.0.1     # ClusterIP → KUBE-SVC-<hash>
iptables -t nat -L KUBE-SVC-XXXX -n                        # the probabilities → KUBE-SEP chains
iptables -t nat -L KUBE-SEP-BBBB -n                        # the DNAT to a real Pod IP
```

The packet you sent to `10.96.0.1` was caught in `PREROUTING` by `KUBE-SERVICES`, handed to the per-Service chain, sent down one `KUBE-SEP` branch by probability, and DNAT'd to a Pod IP before the routing decision ever ran. The ClusterIP was never a destination — it was a *trigger* for a rewrite. Change the number of backing Pods and re-read `KUBE-SVC-XXXX`, and the `KUBE-SEP` branches and their probabilities change within a second or two — kube-proxy rewriting the rules as endpoints come and go:

```bash
kubectl scale deployment web --replicas=4      # from your own terminal
iptables -t nat -L KUBE-SVC-XXXX -n            # on the node: four branches now
```

> **Check yourself —** `ip addr` on every node shows nothing holding the ClusterIP, yet connections to it succeed. Reconcile those two facts — and say which of Act IV's three possibilities (a device owns it, a route leads to it, a rule rewrites it) turned out to be the case.

<details>
<summary>Answer</summary>

The third. The ClusterIP is never a destination — it is a **match condition**. `KUBE-SERVICES` in the `nat` table catches packets addressed to it in `PREROUTING`/`OUTPUT` and DNATs them to a real Pod IP before routing ever runs, and conntrack remembers the rewrite so the reply can be reversed. Nothing needs to own the address because nothing ever routes *to* it — it is consumed by a rule on the way out. Act IV's first two possibilities were the only two you had a mechanism for; the third is the one you built and did not yet have a use for.

</details>

> **You understand this when you can** show that a ClusterIP appears in no `ip addr` output yet still answers, and point at the exact `KUBE-SERVICES` → `KUBE-SVC` → `KUBE-SEP` → `DNAT` rule that makes that possible.

### Where does kube-proxy get the list of Pods?

You have just watched the `KUBE-SEP` branches change when the replica count changed. Something told kube-proxy. It is not watching Pods directly, and it is certainly not reading your Deployment — kube-proxy only ever reads one object per Service, and that object is worth meeting by name, because more Kubernetes networking bugs live in it than in every iptables rule combined.

A Service does not name its Pods. It carries a **selector** — a set of labels — and a controller in the control plane watches for Pods whose labels match, then publishes their addresses into a separate object: the **EndpointSlice** (and its older, flatter twin, `Endpoints`). kube-proxy watches *that*, and writes one `KUBE-SEP` chain per address in it. So the chain from your YAML to a packet's destination has a link in the middle that nobody mentions:

```
Service selector {app: web}  ──►  controller matches Pod labels  ──►  EndpointSlice: [10.244.1.7, 10.244.2.3]
                                                                            │
                                                                            ▼  kube-proxy watches
                                                              one KUBE-SEP chain per address
```

Read both ends and the middle:

> **Predict first —** a Pod is `Running` and its labels match the Service's selector exactly. Is that enough for its address to appear in the EndpointSlice, or could something still hold it out?

```bash
kubectl get svc web -o jsonpath='{.spec.selector}{"\n"}'   # the labels the Service asks for
kubectl get pods --show-labels                              # the labels the Pods actually carry
kubectl get endpoints web                                   # the flat summary: addresses, or <none>
kubectl get endpointslice -l kubernetes.io/service-name=web -o yaml | grep -A6 addresses
```

Matching the selector is necessary and **not sufficient**. Each address in an EndpointSlice carries a `conditions.ready` flag, and the controller publishes an address as ready only when the kubelet says the Pod is ready to receive traffic. That is what a Pod's **readiness probe** is for: a check the kubelet runs against the container, whose result has exactly one networking consequence — a not-ready Pod is held out of every Service that selects it, while continuing to run untouched. `kubectl get pods` prints both facts in two different columns, and they are two different claims by two different parties: `STATUS: Running` is the runtime saying the process is alive, `READY: 0/1` is the kubelet's probe saying it is not fit to be sent traffic.

Which leaves one question you can answer from the chain diagram above rather than from experience.

> **Check yourself —** A Service's EndpointSlice is empty: no ready addresses at all. kube-proxy therefore has no Pod IP to DNAT toward. Given that it must write *something* into `KUBE-SERVICES` for that ClusterIP, what would you write, and what would the client see?

<details>
<summary>Answer</summary>

There is nothing sensible to DNAT to, so the only useful thing is to fail *fast and audibly* rather than let the packet wander off and time out — and Act IV gave you `DROP`, which says nothing. What kube-proxy writes is `DROP`'s answering sibling, **`REJECT`**: discard the packet and send back an ICMP port-unreachable. The client's `connect()` fails instantly with "connection refused." So an empty Service and a silently-dropped packet produce *opposite* symptoms, and the speed of the failure is your first clue about which one you have. Empty endpoints have exactly two causes — the selector matches no Pod's labels, or it matches Pods that are not ready — and only the EndpointSlice tells you which, because a Pod held out for readiness is still listed, just with `ready: false`.

</details>

### How does the outside world reach a ClusterIP?

A plain ClusterIP is only reachable from inside the cluster, because only nodes have the iptables rules and the routes to Pod IPs. Something has to give an outsider a door.

To let the outside in, a **NodePort** Service opens a high port (default 30000–32767) on *every node*. kube-proxy adds a rule in `KUBE-NODEPORTS`: a packet arriving at `<any-NodeIP>:31000` gets DNAT'd to the very same `KUBE-SVC-XXXX` endpoint selection — so it lands on a backing Pod, possibly on a different node. Any node can receive the traffic; the rules and conntrack handle the rest.

A **LoadBalancer** Service is a NodePort with a cloud provider stapled on: the provider provisions an external load balancer with a real public IP and points it at `<NodeIP>:<NodePort>` on your nodes. The external IP routes to the NodePort; the NodePort DNATs to the ClusterIP selection; the ClusterIP selection DNATs to a Pod.

So nothing new was invented for either one. The outside world does not reach a ClusterIP at all — **NodePort and LoadBalancer are the same DNAT trick, one and two layers further out**, and it is DNAT all the way down. (Which is why a kind cluster, with no cloud provider, leaves a LoadBalancer Service's external IP `<pending>` forever. There is nobody to ask.)

### How many rules is all this, and what happens at a thousand Services?

You have read three chains for one Service. A production cluster has hundreds or thousands of Services, and kube-proxy writes the same shape for every one of them. Count what is actually there before reasoning about scale.

`iptables -L` prints rules for humans; there is a second form, **`iptables-save`**, that prints the same rules as the `-A CHAIN …` command lines you would type to recreate them — one rule per line, machine-countable. That is the form to count with, and the `^-A KUBE-` pattern below only works because of it. First, from your own terminal, how many Services this node is programming for:

```bash
kubectl get svc -A --no-headers | wc -l
```

Then, inside the node (`docker exec -it netlab-control-plane bash`), count the rules and do the arithmetic yourself:

> **Predict first —** you have a handful of Services on this cluster. Roughly how many `nat`-table rules do you expect kube-proxy to have written per Service — one, a few, or dozens?

```bash
iptables-save -t nat | wc -l                    # every nat rule on this node
iptables-save -t nat | grep -c '^-A KUBE-'      # the ones kube-proxy owns
iptables-save -t nat | grep -c 'KUBE-SEP-'      # roughly: rules per endpoint
```

Divide the second number by the number of Services. Whatever you got, the shape of it is what matters: it does not grow with anything, so it is a per-Service constant, and the total is that constant times the Service count. Multiply by a thousand Services with several endpoints each and be honest about what you now have — a `KUBE-SERVICES` chain with a thousand match lines in it.

That matters because of *how* netfilter reads it. A chain is a **list**, evaluated in order, top to bottom, until a rule matches. And you can prove the consequence rather than take it, with the tool Act IV taught you to trust — the rule counters. Pick a rule near the bottom of `KUBE-SERVICES`, read its packet counter, `curl` something that is *not* a Service, and read it again:

```bash
iptables -t nat -L KUBE-SERVICES -n -v | tail -5     # on the node: note the pkts column
```

Then, from your own terminal, send a packet that is for no Service at all:

```bash
kubectl run poke --rm -it --image=nicolaka/netshoot --restart=Never \
  -- curl -s -o /dev/null -m 5 http://1.1.1.1/
```

And read the same rules again on the node:

```bash
iptables -t nat -L KUBE-SERVICES -n -v | tail -5     # the counters moved
```

The counters on rules that did not match still went up, because the packet was *compared against them* on its way through. Every packet in the cluster, Service-bound or not, walks that list. Doubling the Service count doubles the comparisons. That is the definition of linear, and you just watched a packet pay it.

There is a second, sharper cost, and it is not the packet's — it is kube-proxy's. When one endpoint changes, kube-proxy recomputes and reloads its rules, and the amount of text it has to write grows with the total number of Services, not with the size of the change. On a large, churning cluster the visible symptom is not slow packets but *slow convergence*: seconds where the rules on a node do not yet describe reality.

Resist the urge to invent a benchmark here. You have not measured a latency and neither has this page. What you measured is the rule count, its growth law, and the fact that non-matching rules are still walked. That is the whole argument.

> **Check yourself —** You want the rule "allow `GET /books`, deny `POST /books`" for a Service. Can kube-proxy's iptables mode express it? Answer from what a `KUBE-SERVICES` rule matches on.

<details>
<summary>Answer</summary>

No, and not because nobody implemented it. A `KUBE-SERVICES` rule matches on the destination address, the protocol, and the destination port — fields in the IP and TCP headers. The HTTP method and path are *payload*: bytes that arrive after the handshake, in a later segment, quite possibly encrypted. netfilter makes its decision on the first packet, before any of those bytes exist. So the blindness is structural: this machinery lives at L3/L4 and the question is an L7 question. Anything that answers it has to be a program that reads the stream — an Ingress controller, a mesh proxy, or something in the kernel that can parse.

</details>

### And what is wrong with a coin flip?

Nothing, for the traffic you have looked at so far. The probabilities distribute *connections* evenly, and if every connection is one short HTTP request to an identical Pod, even is exactly what you want.

Now change one thing about the workload and predict what happens.

> **Predict first —** three Pods behind a Service, and clients open **long-lived** connections — a database pool, a gRPC channel, a WebSocket — that each last hours. Two clients connect. The rule flips a coin per connection. What is the chance both land on the same Pod, and what does the rule do about it afterwards?

The coin is fair per connection, so both land on the same Pod one time in three, and then nothing happens — because the rule has no memory. It does not know how many connections a Pod is already carrying, or that this one will last four hours while the last one lasted 8 milliseconds, or that one of the three Pods is on a node under load. It flips, and conntrack pins that connection to the chosen Pod for its whole life. With a handful of long-lived connections, "even in expectation" and "even in practice" are different things, and the rule cannot tell the difference because it is not counting anything.

So there is a third complaint, and it is a real one: **the load balancing has no state to balance with.** Note that this is the same limitation as the other two, in a third costume — a `nat` rule is a stateless match, and everything you might want to balance *on* is state.

### Is there a fix that keeps netfilter?

Yes, partly, and it is worth meeting before the fashionable answer. kube-proxy has an **IPVS** mode. IPVS is the kernel's in-tree L4 load balancer, and it is a different data structure: instead of a list of rules it keeps a **hash table** of virtual services, so the lookup for "which endpoint for this virtual address" stops depending on how many other virtual addresses exist. And because it is a load balancer rather than a filter, it keeps per-endpoint state and can therefore offer real scheduling algorithms — round-robin, **least-connection**, source-hashing for stickiness — instead of a memoryless coin flip.

That is two of the three complaints addressed. Your cluster is not running it, so this is the one mechanism in the act you have to take on trust unless you go and build it — which you can, with one line in the kind config:

```bash
# in the cluster config from the lab lesson, alongside `nodes:`
kubeProxyMode: "ipvs"
```

On such a node, `ipvsadm -Ln` prints the virtual services and their real servers as a table, with a connection count per real server — the state the iptables version never had. You will also find a dummy interface named `kube-ipvs0` carrying every ClusterIP, and it is worth stopping on, because it looks like a contradiction of everything you just proved: an interface *does* hold the addresses. It is not a contradiction, it is a workaround. IPVS only inspects traffic addressed to the local machine, so kube-proxy parks the ClusterIPs on a device that belongs to nothing, purely to make the kernel deliver those packets locally instead of routing them away. Nobody serves anything on `kube-ipvs0`. The lie is still a lie; it now needs a prop.

Note what IPVS did *not* fix. It is still netfilter, still conntrack, still an L4 device: the `GET`-versus-`POST` rule is exactly as impossible as before, and it still has no notion of *who* the client is beyond its IP. It made the lookup cheap and the balancing stateful. It did not make the datapath able to see more.

### So what would fix the shape of the problem?

Line up the three complaints — the linear rule walk, the L7 blindness, the memoryless balancing — and they share one cause: the decision is being made by a *generic packet-filtering framework* configured with rules, at a fixed set of hooks, on fields in two headers. IPVS swapped the data structure under two of them and left the third untouched, because the third is not about data structures. To address all three you would need to run **your own program** in the kernel's datapath: a program that can hold a hash map, keep its own state, look at more than two headers, know which workload a packet came from, and be changed without reloading a thousand lines of text.

That is **eBPF**, and it is why **Cilium** replaces this machinery rather than tuning it. Service lookup becomes a map lookup in a program attached to the datapath, so there is no `KUBE-SERVICES` chain to walk — [the CNI lesson](05-cni.md) has you look for the chains on a Cilium node and find them absent. Because a program can parse, the `GET`/`POST` distinction that netfilter structurally cannot express becomes expressible. And instead of keying decisions on an IP that will be recycled the moment a Pod restarts, Cilium keys them on an **identity** it derives from a Pod's labels — which is a trade you will make yourself, by hand, in [the Network Policy lesson](07-network-policy.md), for exactly the same reason.

It also changes what you can *see*, and that cost is easy to miss. Everything you have diagnosed so far, you diagnosed by reading a rule table. When the forwarding decision lives inside a program, that table is empty and your best tool is gone. So something has to report the flows the way `tcpdump` reports packets — for the whole cluster, labelled by workload rather than by IP. That is **Hubble**, Cilium's observability layer, and it exists because the visibility had to be rebuilt after the rules went away.

None of that says eBPF is faster on your cluster; you have measured nothing of the kind, and this page will not pretend otherwise. What you have is three complaints you can each defend from something you did: you counted the rules and watched a non-matching rule's counter move, you derived the L7 blindness from the match fields, and you reasoned out what a memoryless coin flip does to long-lived connections. IPVS addresses two. That is the argument, and it is worth deciding for yourself how much weight it carries before anyone tells you what is taking over.

### How many Services can this node hold at once?

Not a rule-count question this time. In Act III you filled the conntrack table on purpose and watched what a full table does: a packet it cannot record is a packet it *drops* — no RST, no error, nothing any application can log. You know the failure. What is new here is who is exposed to it.

Every connection through a Service consumes one conntrack entry, because the DNAT is only half of a Service and the conntrack entry is the other half — that is what makes the reply come back. So a Service is not merely *tracked* by that table; it is *stored* in it, and the table's ceiling is now a limit on how much service traffic a node can carry:

```bash
cat /proc/sys/net/netfilter/nf_conntrack_max      # the ceiling
cat /proc/sys/net/netfilter/nf_conntrack_count    # how close you are to it
dmesg | grep -i conntrack                          # the complaint you produced in Act III
```

A node hammering many short-lived connections through Services — a chatty sidecar, a load test, a client retry-storm — walks toward that ceiling, and the two numbers above are the whole warning system. When it is reached you get the Act III symptom, now spread across every Service on the node at once: packets vanishing under load, connections timing out, and not one application error to point at. The fix is operational (raise the limit, fix the churn). The thing worth carrying is that a Service's reliability is bounded by the size of a kernel table, because a Service *is* entries in that table — and that IPVS and eBPF, whatever else they change, do not change this one.

> **You understand this when you can** trace a packet from a Pod's `write()` to a ClusterIP through iptables to a destination Pod's `read()`, naming every rule it hits — `KUBE-SERVICES`, then `KUBE-SVC-<hash>`, then `KUBE-SEP-<hash>`, then the `DNAT` — name the object kube-proxy reads to know which `KUBE-SEP` chains to write and the two reasons it can be empty, explain why the reply finds its way back without a single rule for the return path, and defend each of the three complaints that make this design run out of road: the chain is a list walked in order (you counted it), the match fields stop at L4 so no HTTP rule is expressible (you derived it), and the balancing keeps no state (you reasoned it out) — then say which two of those three IPVS addresses, and which one nothing at this layer can.

---

← Prev: **[The Pod — a shared network namespace](02-pod-networking.md)** · ↑ **[Act V overview](README.md)** · Next: **[CoreDNS — /etc/hosts for the cluster](04-coredns.md)** →
