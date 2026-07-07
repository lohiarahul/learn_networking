# Act V — Test yourself

> Do this **after** working through all the lessons in [the act overview](README.md). Answer each one out loud or on paper *before* you open its answer — the attempt is what makes it stick, far more than re-reading. A wrong attempt followed by the right answer beats a confident skim every time.

> **Question 1 —** A Service's ClusterIP appears on no network interface anywhere, yet `curl`-ing it works. How? Name the kernel mechanism and the chain of iptables rules a packet to a ClusterIP walks through.

<details>
<summary>Answer</summary>

The ClusterIP is virtual; kube-proxy writes a **DNAT** rule for it. A packet to the ClusterIP is caught in `PREROUTING`/`OUTPUT` by `KUBE-SERVICES`, sent to that Service's `KUBE-SVC-<hash>` chain, dispatched by probability to one `KUBE-SEP-<hash>` endpoint chain, and DNAT'd to a real Pod IP — and `conntrack` records the swap so the reply is reverse-translated back to the ClusterIP.

</details>

> **Question 2 —** What single Act IV primitive *is* a Pod, and what is the `pause` container's entire job?

<details>
<summary>Answer</summary>

A Pod is a **network namespace** (Act IV) shared by its containers — same IP, same loopback, same port space. The `pause` container's only job is to hold that namespace open so the Pod's IP survives even when the real containers restart.

</details>

> **Question 3 —** Inside a Pod, `cat /etc/resolv.conf` shows `options ndots:5`. What does that line cause to happen when an app dials the bare name `database`, and why does it make DNS a common cluster bottleneck?

<details>
<summary>Answer</summary>

`ndots:5` means a name with fewer than five dots is tried against each `search` domain first. So `database` is queried as `database.<ns>.svc.cluster.local`, then `database.svc.cluster.local`, then `database.cluster.local`, before being tried as absolute — several queries (each for A and AAAA) per lookup, which is why DNS becomes a hotspot under load.

</details>

> **Question 4 —** All three major CNI plugins do the identical thing locally when a Pod is scheduled — what is it? Where do Flannel, Calico, and Cilium actually differ?

<details>
<summary>Answer</summary>

Locally they all create a **veth pair**, put one end in the Pod's namespace, assign an IP, and add routes (exactly the Act IV experiment). They differ in cross-node routing: Flannel encapsulates in VXLAN, Calico programs real BGP routes with no encapsulation, Cilium uses eBPF programs instead of iptables.

</details>

> **Question 5 —** A NetworkPolicy is blocking traffic to a Pod. Will the client see an HTTP 403, a connection refused, or a timeout — and why does that tell you the policy is enforced in the kernel, not the application?

<details>
<summary>Answer</summary>

A **timeout** (the SYN is dropped silently in the kernel before any application sees it), not a 403 and usually not a refusal. The app layer never gets involved at all — enforcement happens at the node via iptables/eBPF on Pod identity (labels), which is exactly why a "connection hangs then times out" is the signature of a policy drop rather than an app-level rejection.

</details>

> **Question 6 —** One public address, port 443, two hostnames — `api.example.com` and `app.example.com` — reaching two different Services. Name both places the hostname is read, and say why it has to be read twice.

<details>
<summary>Answer</summary>

First in **SNI**, in the ClientHello, in cleartext, before anything is encrypted — that is how the controller knows which certificate to present. Then again in the **`Host:` header**, inside the decrypted HTTP request, which is what selects the backend Service. It has to be twice because the routing decision lives in encrypted bytes, and you cannot decrypt until you have chosen a certificate, which requires knowing the name. It also means the hostname you visit is visible on the wire even under HTTPS.

</details>

> **Question 7 —** A NodePort Service and a LoadBalancer Service — what does each one actually add on top of a ClusterIP, and what is missing on a kind cluster that leaves a LoadBalancer's external IP `<pending>` forever?

<details>
<summary>Answer</summary>

**NodePort** adds a rule in `KUBE-NODEPORTS` so a high port (30000–32767) on *every* node DNATs into the same `KUBE-SVC` endpoint selection — a door on each node, then the ClusterIP machinery unchanged. **LoadBalancer** is a NodePort plus a *cloud provider* that provisions an external load balancer with a real public IP pointing at `<NodeIP>:<NodePort>`. Kubernetes itself never allocates that IP; it records what a provider tells it. kind has no cloud provider, so nothing ever answers and the field stays `<pending>`. It is DNAT all the way down, and the external IP is the only part Kubernetes cannot do by itself.

</details>

> **Question 8 —** A Pod in namespace `app` dials the bare name `database`. Write out, **in order**, the names its resolver actually queries, and say which one of them would have to be a real Service for the lookup to succeed.

<details>
<summary>Answer</summary>

`database.app.svc.cluster.local`, then `database.svc.cluster.local`, then `database.cluster.local`, then `database.` as an absolute name. The order comes from the `search` line kubelet wrote, which always begins with the Pod's **own namespace**. So only a Service named `database` *in namespace `app`* is found by that bare name — a `database` Service in namespace `data` is never queried at all, because `data` appears nowhere in the search list. Cross-namespace requires qualifying: `database.data`.

</details>

> **Question 9 —** Name the five debugging questions in order, and for each one name the file it reads and the tool that reads it. Then say why the order is not negotiable.

<details>
<summary>Answer</summary>

1. **DNS** — `/etc/resolv.conf` plus CoreDNS's A records, read with `cat` and `dig`. 2. **Routing** — the routing table, read with `ip route` / `ip route get`. 3. **NAT and firewall** — the `nat` table, the conntrack table, and NetworkPolicy objects, read with `iptables -t nat`, `conntrack -L`, `kubectl get networkpolicy`. 4. **TCP** — the wire, read with `tcpdump`, looking for SYN / SYN-ACK / RST. 5. **Application** — the socket table, read with `ss -tlnp`. The order is fixed because a failure at a lower layer makes every layer above it look broken: if the name resolved to the wrong address, everything you learn about TCP is about the wrong connection. Read top to bottom and stop at the first file that lies.

</details>

> **Question 10 —** kube-proxy's iptables mode writes a small, constant number of rules per Service. Given that, what exactly gets worse as a cluster grows to thousands of Services — and what gets worse that is *not* the packet's latency?

<details>
<summary>Answer</summary>

`KUBE-SERVICES` is a **chain**, and a chain is a list evaluated in order until something matches. Constant rules per Service times thousands of Services is a list thousands of lines long, and every packet — including packets not headed for any Service — is carried through it and compared against each entry before falling out the bottom. That is linear growth in comparisons. The second cost is **convergence**, not latency: when one endpoint changes, kube-proxy recomputes and reloads rules whose total size scales with the *whole* Service count, not with the size of the change, so a large churning cluster spends seconds with rules that do not yet describe reality.

</details>

> **Question 11 —** Why can a `KUBE-SVC` rule not express "allow `GET /books`, deny `POST /books`"? Then say what IPVS mode fixes about kube-proxy and what it leaves exactly as broken.

<details>
<summary>Answer</summary>

Because a netfilter rule matches on fields in the IP and TCP headers — address, protocol, port — and it decides on the first packet. The HTTP method and path are **payload**, arriving after the handshake, in later bytes, quite possibly encrypted. The blindness is structural, not an unimplemented feature: this machinery is L3/L4 and the question is L7. **IPVS** replaces the rule list with a kernel **hash table** of virtual services, so the endpoint lookup stops depending on how many other Services exist, and adds real scheduling algorithms (round-robin, least-connection, source-hash) instead of the `statistic` module's coin flips. It leaves the L7 blindness completely untouched, and it is still netfilter and still conntrack. It made the lookup cheap; it did not make the datapath expressive.

</details>

> **Question 12 —** A Service's EndpointSlice has no ready addresses. Name the two entirely different situations that produce that, and say why `kubectl get endpoints` cannot tell them apart.

<details>
<summary>Answer</summary>

Either the Service's **selector matches no Pod's labels** — nothing was ever eligible, so no address is listed at all — or it matches Pods that are **not ready**: their addresses *are* in the EndpointSlice, carrying `conditions.ready: false`, because a readiness probe is failing and the kubelet is holding them out of every Service that selects them. `kubectl get endpoints` prints the flat summary of *ready* addresses only, so it says `<none>` in both cases. Only the EndpointSlice distinguishes "no addresses" from "addresses, none ready" — and the second one is a Pod that shows `Running` in `kubectl get pods` while showing `0/1` in the column next to it.

</details>

---

← Back to **[Act V overview](README.md)** · Next: **[Diagnose it →](diagnose.md)** (apply it under fire), then **[The whole stack →](../the-whole-stack.md)**
