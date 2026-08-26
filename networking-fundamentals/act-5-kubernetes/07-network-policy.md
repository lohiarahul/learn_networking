# Network Policy — a filter table someone else has to enforce

By default, Kubernetes is a flat, trusting network: every Pod can open a connection to every other Pod, in any namespace, on any port. That is wonderful for getting started and terrifying for production, where a compromised frontend should not be able to dial the database directly. NetworkPolicy is how you close those doors — and it turns out to be the firewall rules from Act IV, written in YAML instead of `iptables`, with the awkward detail that Kubernetes itself enforces not one of them.

![No trusted interior: every party authenticates for every request](../../illustrations/07-security/zero-trust-networking.svg)

### Why isn't flat Pod connectivity enough?

Flat connectivity means one breached Pod can reach everything. You want segmentation: the database should accept connections only from the API Pods, the API only from the frontend, and nothing should talk to internal services it has no business touching. In Act IV you already had the tool for "drop this packet unless it matches" — iptables filter rules. But Pod IPs are ephemeral; a firewall rule pinned to `10.244.1.7` is wrong the moment that Pod restarts with a new IP. You needed a way to express "allow traffic from the API Pods" that survives Pods coming and going.

### So what is a NetworkPolicy, really?

A **NetworkPolicy** is a declarative rule that selects a set of Pods by *label* and specifies which ingress (incoming) and egress (outgoing) traffic is allowed for them. The crucial design choice: it operates on **Pod identity (labels), not IP addresses**. You write "Pods labeled `app=database` may receive traffic on port 5432 from Pods labeled `app=api`."

The CNI plugin watches both the policies and the Pods, maintains the live mapping from labels to current Pod IPs, and translates the policy into actual enforcement on each node. There are three architectures in the wild, and they are not variations on a theme: **iptables filter rules** (Calico), **eBPF programs attached to the datapath** (Cilium), or **an nftables hook that hands the packet to a userspace process and does what it says** (kindnet — which is what `kind` gave you, so it is the one your lab is running). When a Pod restarts and gets a new IP, the agent updates whatever it maintains, so the label-based intent stays true even though the IPs changed.

Which makes a NetworkPolicy **an Act IV filter decision, with a controller keeping it in sync as Pod IPs churn underneath the labels** — and explains the odd division of labour: Kubernetes itself only stores your intent, and the plugin is the thing that enforces it. Note *decision*, not *table*. Where that decision physically happens is a property of your CNI and not of Kubernetes, it is measurable, and [further down this page](#where-does-the-decision-actually-get-made) you will find that on this cluster it is not where you would guess.

### What does one actually look like?

Four fields carry all of the meaning. Read them before you read the semantics:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-accepts-api-only
spec:
  podSelector:                       # WHO this policy applies to
    matchLabels: { app: database }
  policyTypes: [ Ingress ]           # WHICH direction it governs
  ingress:                           # WHAT is allowed in (everything else is not)
    - from:
        - podSelector:
            matchLabels: { app: api }
      ports:
        - port: 5432
```

`podSelector` is the same label-matching you met in [the Services lesson](03-services.md), doing a different job: there it chose which Pods a Service sends traffic *to*, here it chooses which Pods a rule applies *to*. Not one IP address appears anywhere in the document — that is the entire design.

Two of those four fields have behaviour that is not obvious from reading them, and both bite people.

First, an **empty `podSelector: {}` selects every Pod in the namespace**, not none. It is the widest possible selector, not the narrowest.

Second, **`policyTypes` plus an empty allow list means deny.** A Pod with no policy selecting it accepts everything; the moment *any* policy selects a Pod for `Ingress`, that Pod switches to default-deny for ingress and only the listed sources get through. So a document with `policyTypes: [ Ingress ]` and no `ingress:` list at all is not a no-op — it is "permit nothing inbound," which is how people write a namespace-wide default-deny on purpose, and how they write one by accident.

Policies are also **additive**: several may select the same Pod, and the Pod accepts the union of everything they allow. There is no ordering and no explicit `deny` rule to write — you deny by not allowing.

And one thing that is not visible in the document at all: **enforcement requires CNI support.** Flannel alone does not enforce NetworkPolicy; Calico and Cilium do. Applying a policy on a cluster whose CNI ignores it produces no error and no effect, which is its own debugging trap and the subject of a warning further down this page.

### What does it look like, before and after?

<!-- figure -->

```
   BEFORE any policy (default):           AFTER policy on app=database:
   every Pod → every Pod, all ports       ingress allowed ONLY from app=api : 5432

   frontend ──┐                            frontend ──X (dropped in kernel, no RST)
   api ───────┼──► database  :anything     api ───────► database :5432  ✓
   intruder ──┘                            intruder ──X (dropped in kernel)

   the agent keeps: { app=api } → { 10.244.1.7, 10.244.2.9, ... }  ← updated as Pods churn
   and enforces it: iptables chain (Calico) | eBPF program (Cilium) | nftables → userspace (kindnet)
```

### Why does a blocked request time out instead of returning 403?

**Because the SYN dies in netfilter — the application never sees the request, so it cannot refuse it.**

Enforcement happens in the **kernel, at the node level**, before the packet ever reaches the destination application. This has a sharp, practical consequence for debugging: when a NetworkPolicy blocks traffic, the source Pod sees a **connection timeout**, not an HTTP 403. There is no rejection from the app, no log line in the server, no response of any kind — the SYN is silently dropped in netfilter and the client just waits and gives up.

People burn hours staring at an application that "isn't logging the request" when the request never reached the application at all; it died in the kernel. A 403 means the app said no; a timeout (with everything else healthy) often means a NetworkPolicy said no first. The application layer is never involved, by design.

One precision that matters later: the packet always *dies* in netfilter, but the **decision** is not always made there. On the third architecture the kernel copies the packet to a userspace process, waits for a verdict, and then drops it — same timeout, same missing log line, an entirely different thing to debug when it goes wrong.

> **Check yourself —** A request between two Pods times out. The server logs nothing at all. Does that mean the server is broken?

<details>
<summary>Answer</summary>

No — it is evidence the request never *arrived*. Enforcement happens in the kernel at the node, so a NetworkPolicy drop produces a timeout with no log line anywhere in the application. A 403 would mean the app saw the request and refused it; silence with everything else healthy points at the layer below.

</details>

### Where does the decision actually get made?

Everything above said "the CNI enforces it," and that sentence has been doing a lot of work. Go and
find the enforcement point on your own node. Start with the one the internet will tell you to look for:

```bash
docker exec netlab-worker sh -c 'iptables -L -n | grep -ci cali'   # Calico's policy chains
docker exec netlab-worker nft list tables                          # every nftables table on the node
```

```
0
table ip nat
table ip mangle
table ip filter
table ip6 mangle
table ip6 nat
table ip6 filter
table inet kindnet-network-policies
```

Zero `cali-*` chains — of course, this is not a Calico cluster — and one table nobody has mentioned
yet. Read it:

```bash
docker exec netlab-worker nft list table inet kindnet-network-policies
```

```
table inet kindnet-network-policies {
        set podips-v4 {
                type ipv4_addr
                elements = { 10.244.1.177, 10.244.1.178 }
        }
        chain postrouting {
                type filter hook postrouting priority srcnat - 5; policy accept;
                udp dport 53 accept
                meta skuid 0 counter packets 105 bytes 12171 accept
                ct label 28 ct state established,related counter packets 0 bytes 0 accept
                ip saddr @podips-v4 queue flags bypass to 101
                ip daddr @podips-v4 queue flags bypass to 101
                ct label set 28
        }
        chain input     { ... ip saddr @podips-v4 ct state new queue flags bypass to 101 ... }
        chain prerouting{ ... ip daddr @podips-v4 queue flags bypass to 101 ... }
}
```

Read what is *not* there. **No allow rule and no drop rule mentions a policy, a label, or a port.**
There is no translated copy of your YAML anywhere in this table. What there is:

- `set podips-v4` — the label-to-IP mapping from four paragraphs up, materialised as a kernel object.
  Sets are why adding a Pod does not mean rewriting rules: you add an element.
- `ct state established,related accept` — decide once per *connection*, not once per packet, which is
  the conntrack lesson from Act IV paying for itself again.
- `queue flags bypass to 101` — the verdict on every packet involving one of those addresses:
  *stop, hand this packet to whoever is listening on netfilter queue 101, and do what they say.*

So who is listening?

```bash
docker exec netlab-worker cat /proc/net/netfilter/nfnetlink_queue
docker exec netlab-worker pgrep -a kindnetd
```

```
  101 3413175125     0 2   128     0     0       60  1
1422 /bin/kindnetd
```

Columns one and two are the queue number and **the port ID of the process bound to it** — and that
process is `kindnetd`, a Go program, in userspace. Which settles it: on the cluster this act built, a
NetworkPolicy is not evaluated by a kernel rule at all. The kernel's rule says *ask someone*.

That is the third architecture, and now all three fit on a line each:

| CNI | Where the decision is made | The file that proves it |
|---|---|---|
| Calico | iptables `cali-*` chains — an Act IV filter table, generated | `iptables-save \| grep cali` |
| Cilium | an eBPF program on the datapath; no chains at all | `cilium endpoint list`, `cilium monitor` |
| **kindnet** (your lab) | **userspace** — nftables queues the packet out and takes a verdict back | `nft list table inet kindnet-network-policies`, `/proc/net/netfilter/nfnetlink_queue` |

Only the first is literally "iptables with a YAML interface." The other two reach the same verdict on
machinery that does not resemble it — which is why the honest version of the sentence is *"a
NetworkPolicy is intent, and something else, elsewhere, decides."* The `cilium` commands need a Cilium
node, which this act does not build; [Act X](../act-10-cluster-security/09-encryption-between-pods.md)
does. And if you want the nftables grammar itself rather than just the shape of it, `nft` is taken
apart in [Act IV](../act-4-one-pretends-many/03-iptables-and-nat.md#one-backend-two-grammars) and on
its [reference page](../../reference/tools/netlink/nft.md).

### Can you watch a label flip a port open?

**Establish that your cluster enforces before you measure anything, or this experiment will lie to you.** The paragraph above said enforcement requires CNI support; here is where that stops being trivia. Apply a policy to a CNI that does not enforce and you get no error, no effect, and no status field that admits it — your `nmap` output is identical before and after, and the conclusion you draw is exactly the wrong one.

You cannot settle this by reading, which is the point. Calico and Cilium enforce. Flannel never has. kindnet did not until kind v0.24 embedded `kube-network-policies` into kindnetd, and does after — so two people running "a default kind cluster" get different answers depending on when they installed it. Measure it instead, with the one document that has no legitimate reason to allow anything:

```bash
kubectl create ns npcheck
kubectl -n npcheck run t --image=nginx:alpine
kubectl -n npcheck run c --image=nicolaka/netshoot --command -- sleep infinity
kubectl -n npcheck wait --for=condition=Ready pod --all --timeout=120s
TIP=$(kubectl -n npcheck get pod t -o jsonpath='{.status.podIP}')

kubectl -n npcheck exec c -- curl -s -o /dev/null --max-time 4 "http://$TIP/"
echo "before: exit $?"

kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: deny-all, namespace: npcheck }
spec:
  podSelector: {}
  policyTypes: [ Ingress ]
EOF

kubectl -n npcheck exec c -- curl -s -o /dev/null --max-time 4 "http://$TIP/"
echo "after:  exit $?"
```

```
before: exit 0
after:  exit 28
```

**`28` is curl's timeout, and it is the only evidence that a policy engine exists.** If the second number is also `0`, your CNI accepted a document forbidding all ingress and then served the page anyway — go build the `disableDefaultCNI` cluster with Calico from [the lab lesson](01-lab-with-kind.md), because nothing below this line will be real.

That check is worth more than its result, and it is the shape of the whole lesson: the only thing that tells you a policy engine is running is **a packet that does not arrive**.

This is the trap [the Gateway API lesson](06b-gateway-api.md) left you holding, and it is the same one exactly: the cluster stored your intent and nobody reconciled it. There it was a Gateway with no controller, and the tell was a `Programmed` condition that never went `True`. Here it is a NetworkPolicy with no enforcing CNI — and it is *worse*, because a Gateway that routes nothing fails loudly the moment someone curls it, while a policy that filters nothing looks exactly like a policy that is working. "The policy silently did nothing" is not only a lab problem; it is a production incident that ships as a false sense of security, and there is no status field to catch it.

### What happens when the policy engine dies?

The section above found that on this cluster the verdict is made by **a process**. Processes die. The
`npcheck` namespace is still up and `after: exit 28` is still true, so you can just ask.

> **Predict first —** `kindnetd` is killed while that default-deny is in force. The nftables rules it
> wrote are still loaded in the kernel. Does the blocked request keep timing out, start succeeding, or
> does *all* Pod traffic on the node stop?

```bash
docker exec netlab-worker sh -c 'kill -9 $(pgrep kindnetd)'
docker exec netlab-worker cat /proc/net/netfilter/nfnetlink_queue   # who holds queue 101 now?
docker exec netlab-worker sh -c 'nft list tables | grep kindnet'    # are the rules still loaded?
kubectl -n npcheck get netpol                                      # is the policy still declared?
kubectl -n npcheck exec c -- curl -s -o /dev/null --max-time 4 "http://$TIP/"; echo "exit $?"
```

```
                                          ← empty: nothing is bound to queue 101
table inet kindnet-network-policies       ← the rules are still loaded
NAME       POD-SELECTOR   AGE
deny-all   <none>         33s             ← the policy is still declared
exit 0                                    ← and the traffic it forbids now flows
```

**The answer was in a flag you already read: `queue flags bypass`.** Without `bypass`, a queue with no
listener drops everything it is handed — and the node's Pod network would go dark for the seconds
between `kindnetd` crashing and coming back. With it, a queue with no listener **accepts**. So the
failure mode is not an outage. It is a silently disabled firewall: every object still says the policy
is in force, `kubectl get netpol` agrees, `nft list ruleset` agrees, and the packet gets through.

`kindnetd` runs as a DaemonSet, so the kubelet restarts it and the door shuts again. Wait for the
queue to be *bound* rather than for a number of seconds — the gap is the whole point of this exercise,
so measure it instead of assuming it. Note the `grep -q .` and not `[ -s ... ]`: this is a `/proc`
file, and every one of them `stat`s as zero bytes because the content does not exist until you read it,
so the shell's "file is non-empty" test is false for a file that is about to hand you five columns.
That is the [procfs](../../reference/tools/procfs/README.md) property from Act I, arriving as a bug in
your own loop:

```bash
until docker exec netlab-worker \
        sh -c 'grep -q . /proc/net/netfilter/nfnetlink_queue'; do sleep 1; done
docker exec netlab-worker cat /proc/net/netfilter/nfnetlink_queue
kubectl -n kube-system get pod -l app=kindnet
kubectl -n npcheck exec c -- curl -s -o /dev/null --max-time 4 "http://$TIP/"; echo "exit $?"
kubectl delete ns npcheck
```

```
  101 3853769076     0 2   128     0     0        0  1
NAME            READY   STATUS    RESTARTS      AGE
kindnet-rr8dp   1/1     Running   1 (20s ago)   4d20h
exit 28
```

Same queue number, **different port ID** — `3413175125` before, `3853769076` after. A different
process doing the same job, which is the whole architecture visible in one diff. The `RESTARTS` column
is the other receipt, and it is the one that matters operationally: **that counter is the only place in
the cluster that records the window during which your policies were not being enforced.** Nothing
warns you. Nothing alerts. There is a number in a DaemonSet's status.

Kill it a few more times and the window gets *wider*, not narrower — the kubelet backs off
exponentially between restarts of a container that keeps dying, so a `kindnetd` in a crash loop is a
firewall that is off for ten seconds, then twenty, then forty. Which is the answer to a question no
NetworkPolicy tutorial asks: a policy engine is a piece of software with a restart policy, and its
availability *is* your security posture.

This is the trap [the Gateway API lesson](06b-gateway-api.md) set, for the third time and at its
sharpest. There it was an object with no controller. A few paragraphs ago it was a policy with no
enforcing CNI. Here it is a policy with a working, enforcing, correctly-configured CNI whose one
process is not running — and the distance between *secure* and *wide open* is a single `kill`, with no
error, no event, and no field anywhere in the Kubernetes API that changes. So ask it of any policy
engine you are handed, and ask it before you need the answer: **when your agent stops, does traffic
stop or does traffic flow?** Calico and Cilium have the better answer here almost by accident — their
rules *are* the verdict, so the last decision they made keeps being enforced with nothing running,
which fails closed for existing Pods (while quietly going stale for new ones). A queue-to-userspace
design has to pick one of the two bad options, and kindnet picked availability.

---

With enforcement confirmed and the engine back up, probe the target from a second Pod before and after applying the policy:

> **Predict first —** after you apply a deny NetworkPolicy, what word will `nmap` change to — and will the blocked port look like a refusal or a silent timeout?

```bash
nmap -p 5432,8080,9090 <database-pod-ip>      # BEFORE the policy
# apply a NetworkPolicy allowing ingress only from app=api on 5432
nmap -p 5432,8080,9090 <database-pod-ip>      # AFTER, from a non-api Pod
```

The word `nmap` reports is the tell. Before the policy, reachable ports read `open`. After, from a Pod that the policy does *not* permit, they read `filtered` — nmap's word for "the SYN went out and nothing, not even a rejection, came back," which is exactly the silent kernel drop. Run the same `nmap` from a Pod labeled `app=api` and `5432` is `open` again: identical packet, different source label, opposite result — because the rule keys on identity, not address.

That is the model, and the model is the part most material never gets right. What it is not is practice: every policy on this page has one `podSelector` and one port, and the exam's tasks do not. [The next lesson](07b-policy-shapes.md) writes the other four shapes — cross-namespace peers and the one hyphen that turns an AND into an OR, `ipBlock`, and egress — and proves each one against a four-client bench rather than asserting it.

> **You understand this when you can** explain why a denial shows up as a connection *timeout* and not an HTTP 403; why the rule survives Pods restarting with new IPs, when it names no IP; point at the enforcement point on *your* cluster and the file that proves it; and say what happens to forbidden traffic the moment the policy agent stops running.

---

← Prev: **[Gateway API](06b-gateway-api.md)** · ↑ **[Act V overview](README.md)** · Next: **[The four shapes of a NetworkPolicy](07b-policy-shapes.md)** →
