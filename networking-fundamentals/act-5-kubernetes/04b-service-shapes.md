# Service shapes — when a load-balanced VIP is the wrong answer

You have one Service in your head so far: a virtual IP that exists on no interface, whose packets get DNAT'd to one of N Pods chosen by probability.

Now run a database. Three Postgres Pods, and they are **not interchangeable**: exactly one accepts writes, and the other two are read replicas that will refuse them. Two things you need, neither of which you can currently build:

1. **Reach the write-accepting Pod specifically.**
2. **Let a client reach each of the three by name**, because a database client library wants to know its cluster's members individually.

### Why does the default Service actively hurt here?

Because probability is the whole point of it, and here probability is the bug. A ClusterIP in front of three replicas sends a third of your writes to a Pod that will refuse them. There is no field to say "always that one" — you met the reason in [the Services lesson](03-services.md): `KUBE-SVC-<hash>` is a chain of `statistic`-module coin flips, and a coin flip has no notion of *which* backend.

So try to get past it with what you already have. A Service selects Pods by label, so give each Pod a unique label and write one Service per Pod. Set the lab up and actually do it, because the cost is countable.

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Service
metadata: { name: db }
spec:
  clusterIP: None                    # headless — we come back to this
  selector: { app: db }
  ports: [ { name: pg, port: 5432 } ]
---
apiVersion: v1
kind: Pod
metadata: { name: db-0, labels: { app: db, instance: "0" } }
spec:
  hostname: db-0
  subdomain: db
  containers:
    - { name: pg, image: hashicorp/http-echo, args: [ "-text=db-0", "-listen=:5432" ] }
---
apiVersion: v1
kind: Pod
metadata: { name: db-1, labels: { app: db, instance: "1" } }
spec:
  hostname: db-1
  subdomain: db
  containers:
    - { name: pg, image: hashicorp/http-echo, args: [ "-text=db-1", "-listen=:5432" ] }
---
apiVersion: v1
kind: Pod
metadata: { name: db-2, labels: { app: db, instance: "2" } }
spec:
  hostname: db-2
  subdomain: db
  containers:
    - { name: pg, image: hashicorp/http-echo, args: [ "-text=db-2", "-listen=:5432" ] }
EOF
kubectl wait --for=condition=Ready pod/db-0 pod/db-1 pod/db-2 --timeout=90s
```

Now the attempt. Count the chains on a node *before*, add three single-Pod Services, and count again.

> **Predict first —** in [the Services lesson](03-services.md) you counted the rules a Service costs. Three Services, each selecting exactly one Pod: how many `KUBE-SVC` chains will appear, and how many ClusterIPs will be spent?

```bash
docker exec netlab-worker sh -c "iptables-save -t nat | grep -c KUBE-SVC"     # before

for i in 0 1 2; do
  kubectl create service clusterip db-$i --tcp=5432:5432 -o yaml --dry-run=client \
    | kubectl set selector --local -f - "app=db,instance=$i" -o yaml \
    | kubectl apply -f -
done

kubectl get svc
sleep 3      # kube-proxy has not reconciled yet — count too early and you will see no change at all
docker exec netlab-worker sh -c "iptables-save -t nat | grep -c KUBE-SVC"     # after
```

That `sleep` is worth more than it looks. Run the second count immediately and it returns *exactly* the first number, because kube-proxy is still watching-and-rewriting and has not caught up. You would conclude three Services cost nothing. The rules arrive a second or two later, and this is the convergence lag the Services lesson warned about — visible here in three seconds on an idle cluster, which is why it bites hard on a large churning one.

Once it settles, the price is on your screen: **three more ClusterIPs** burned out of the service CIDR, and **four more `KUBE-SVC` lines per Service** — the chain declaration, the jump from `KUBE-SERVICES`, and two rules inside it — plus a `KUBE-SEP` set each. Twelve lines of machinery whose entire job is to load-balance across one backend, which is a coin flip with one side. You need a fourth Service the moment you add a replica, created by hand, because nothing generates them. You have used the load balancer to defeat the load balancer.

```bash
kubectl delete svc db-0 db-1 db-2        # we are not keeping these
```

Delete them properly before moving on. Leaving them behind quietly ruins the next experiment: a grep for `default/db` will match `default/db-0` too, and the number you are about to read as "zero" will not be zero.

What you actually want is not a better VIP. It is **no VIP at all** — ask a name for the *addresses*, and choose one yourself.

### What happens if a Service has no ClusterIP?

That is the `clusterIP: None` you already applied. It makes `db` a **headless Service**: a name that DNS answers with the Pod IPs themselves. Two subsystems change, and you should check both.

> **Predict first —** `dig` a normal ClusterIP Service and you get one A record. What comes back for a headless one? And what does the node's NAT table hold for each?

```bash
kubectl create deployment web --image=hashicorp/http-echo -- /http-echo -text=web -listen=:5678
kubectl expose deployment web --port=80 --target-port=5678        # a normal ClusterIP, for contrast
kubectl wait --for=condition=Available deployment/web --timeout=90s

kubectl run net --rm -it --image=nicolaka/netshoot --restart=Never -- \
  sh -c 'dig +short db.default.svc.cluster.local; echo ---; dig +short web.default.svc.cluster.local'
```

The headless name returns **one A record per ready Pod** — three addresses, the real Pod IPs out of the `10.244.x.y` range the lab lesson gave you. The ClusterIP name returns exactly one address: the VIP that exists nowhere.

Now the other subsystem:

```bash
docker exec netlab-worker sh -c "iptables-save -t nat | grep -c 'KUBE-SVC.*default/web'"   # non-zero
docker exec netlab-worker sh -c "iptables-save -t nat | grep -c 'KUBE-SVC.*default/db'"    # zero
```

**Nothing for `db`.** Not one rule — grep the whole nat table for `default/db` and it appears nowhere, not even as a chain declaration. Meanwhile `web`, an ordinary ClusterIP over the same kind of Pod, has its full set. That contrast is what "headless" means at the mechanism level: this Service never enters the datapath at all. It is an instruction to CoreDNS and nothing else, and a client talking straight to a Pod IP has one fewer thing between `write()` and `read()`.

### How do you address one Pod by name?

That is the other two fields you applied: `hostname` and a `subdomain` matching the headless Service's name. Together they make a Pod individually resolvable.

```bash
kubectl run net --rm -it --image=nicolaka/netshoot --restart=Never -- \
  dig +short db-0.db.default.svc.cluster.local
```

One address — `db-0`'s, and only `db-0`'s. That is the whole mechanism behind "stable per-Pod DNS names," and it is worth seeing at this level once, because the object you will reach for in practice — a workload controller that stamps out `db-0`, `db-1`, `db-2` and sets these two fields per replica — is automation over exactly these lines. You are not missing a feature; you are looking at what the feature is made of.

One trap before you move on, and it is the same gate you met in [the Services lesson](03-services.md). **All of these records exist only for Pods that are Ready.** Break a readiness probe on `db-1` and it disappears from the headless A set, from `dig db-1.db.default...`, *and* from the SRV answer below — every one of them, silently. So an empty `dig` for a Pod you can plainly see in `kubectl get pods` is not a DNS problem; it is a readiness symptom wearing a DNS costume.

And notice what the stable identity turned out to *be*. Not an address: Pod IPs still churn on every restart. The thing that stays put is **a name in DNS**, which is why a workload whose members must be individually addressable is always paired with a headless Service rather than a load-balanced one.

### What if you need the port too?

Every lookup in this course so far — Act II's `dig` walks, the CoreDNS lesson, both of the above — has asked for an **A record**, which maps a name to an address and nothing else. Here is the first time that is not enough.

An **SRV** record answers "where is this *service*" rather than "where is this *host*": it carries a port alongside the target, plus a priority and weight for choosing between targets.

```bash
kubectl run net --rm -it --image=nicolaka/netshoot --restart=Never -- \
  dig +short SRV _pg._tcp.db.default.svc.cluster.local
```

Priority, weight, **port**, and target hostname, one line per Pod. The query name is built from the Service's *named* port — `name: pg` in the manifest above — which is why naming your ports is not decoration. This is how a client library discovers a cluster's members and their ports with nothing hard-coded.

### Who is the client, and what does the cluster remember about them?

Headless was about *choosing a backend*. The three remaining fields all turn on a different question — what the cluster knows about whoever is calling — and they answer it in escalating order, ending with a case where there is no cluster client at all.

**1. `sessionAffinity` — remembering where the last one went.** [The Services lesson](03-services.md) had you reason out that iptables balancing "keeps no state," so two requests from one client can land on different Pods. If your backend caches per session, that hurts.

```bash
kubectl patch svc web -p '{"spec":{"sessionAffinity":"ClientIP"}}'    # patch edits one field on a live object
docker exec netlab-worker sh -c "iptables-save -t nat | grep recent"
```

The rules that appear use netfilter's **`recent` module** — `--set` in the `KUBE-SEP` chain to record a source address against a backend, and `--rcheck --seconds 10800` in `KUBE-SVC` to send that source to the same one again. Note what that is *not*: conntrack pins packets of an already-established connection, which it has done since Act III without being asked. Affinity is a harder job — it must route a **brand-new** connection to where the *previous* one went, and that needs a record that outlives the flow. Hence a separate module, and hence a timeout: `sessionAffinityConfig.clientIP.timeoutSeconds`, three hours by default.

It keys on **source IP**, so every client behind one NAT gateway is a single "session," and a client whose address changes loses its pin. Affinity by IP is a coarse instrument.

**2. `externalTrafficPolicy` — whether the client's address survives.** This one you can derive from Act IV. When traffic arrives at a NodePort, kube-proxy may DNAT it to a Pod on a *different* node — so the reply must return through the node that did the translation, which means that node also has to **SNAT** the packet to its own address. The Pod therefore sees the *node's* IP as its client, and your access logs are useless for geography, rate limiting, or abuse.

`externalTrafficPolicy: Local` refuses to forward off-node: only Pods on the receiving node are eligible, so no SNAT is needed and the original source IP survives. Then it has a cost you can predict.

> **Predict first —** on your two-node cluster, `web` has one replica, and the control-plane node carries a `NoSchedule` taint so the Pod cannot be there. With `Local` set, what happens when you hit the NodePort on the *control-plane* node — refused, or something else?

```bash
kubectl patch svc web -p '{"spec":{"type":"NodePort","externalTrafficPolicy":"Local"}}'
kubectl get pod -o wide                       # confirm which node the Pod is on
kubectl get svc web                           # note the nodePort
kubectl get nodes -o wide                     # node IPs, no docker templating needed

# from inside the worker, hit BOTH nodes on the nodePort
docker exec netlab-worker sh -c "curl -s -m 5 http://<worker-ip>:<nodePort>/ ; echo \" exit=\$?\""
docker exec netlab-worker sh -c "curl -s -m 5 http://<control-plane-ip>:<nodePort>/ ; echo \" exit=\$?\""
```

The node with the Pod answers `web`. The node without it **does not answer at all** — the connection hangs until your timeout rather than being refused, because there is no local endpoint and the chain has nothing to send it to. That is the same silence-versus-answer distinction the Services lesson drew between `DROP` and `REJECT`: an empty-endpoints ClusterIP gets you `REJECT` and an instant refusal, while this gets you a drop and a wait.

You traded cluster-wide reachability for a truthful source IP, and every node without a Pod became a black hole. That is not a bug to fix; it is the deal. In production a real load balancer only sends traffic to nodes whose health check passes, and `Local` is what makes that health check meaningful. On a bare cluster with `curl`, it is a hole you fall into.

**3. `ExternalName` — when there is no cluster client to remember.** Two lessons have now taught you that a cluster name resolves to a ClusterIP which iptables rewrites to a Pod. So what should happen when the thing you want to call *is not in the cluster* — when there is nothing to rewrite to?

```yaml
apiVersion: v1
kind: Service
metadata: { name: extdb }
spec:
  type: ExternalName
  externalName: db.prod.example.com
```

Apply it and check all four: no selector, no endpoints, no ClusterIP, no chains.

```bash
kubectl get svc extdb                                    # EXTERNAL-IP is the name; CLUSTER-IP is <none>
kubectl get endpointslices -l kubernetes.io/service-name=extdb    # "No resources found"
docker exec netlab-worker sh -c "iptables-save -t nat | grep -c 'default/extdb'"   # zero
kubectl run net --rm -it --image=nicolaka/netshoot --restart=Never -- \
  dig extdb.default.svc.cluster.local CNAME +short
``` CoreDNS answers with a **CNAME** — a third record type, the one that says *"this name is an alias; go and resolve that other name instead."* The client does exactly that, and the cluster is out of the conversation from then on.

Which is where a trap lives, and it is worth getting the direction right because it is the opposite of what people assume. Following a CNAME **does not rename what the client was asking for.** Your code dialled `db.default.svc.cluster.local`, so that is the name it puts in its TLS **SNI** and its `Host:` header (recall Act III — SNI is chosen by the client, from the name it was given). The server at the far end presents a certificate for `db.prod.example.com`. The names do not match, and **TLS validation fails.** An `ExternalName` Service is a fine indirection for plaintext or for a server whose certificate happens to cover the cluster name — and a reliable way to break HTTPS otherwise. There is also no port remapping, since nothing proxies.

And because nothing proxies, these packets leave your cluster as ordinary egress to an outside address, carrying no Pod identity that a cluster-level rule could match on. Hold that thought; it comes back later in this act.

<!-- figure -->

```
   CHOOSING A BACKEND
   ClusterIP (default)          headless              ExternalName
   name -> 1 VIP                name -> N Pod IPs     name -> CNAME
   iptables: DNAT chains        iptables: nothing     iptables: nothing
   kernel chooses (coin flip)   client chooses        nothing in cluster to choose

   WHAT THE BACKEND SEES AS THE CLIENT
   sessionAffinity: ClientIP    -m recent, 3h        same source -> same Pod
   externalTrafficPolicy
     Cluster   node A -> Pod on node B   SNAT      source IP LOST, every node works
     Local     node A -> Pod on node A   no SNAT   source IP KEPT, Pod-less nodes drop
```

> **Check yourself —** A teammate says "our headless Service isn't load balancing." What has been misunderstood, and what is now doing the job the VIP used to do?

<details>
<summary>Answer</summary>

A headless Service was never going to load balance — that is the point of asking for one. Removing the ClusterIP removes the DNAT chains, and with them the coin flip; nothing in the kernel is choosing a backend any more. You verified exactly this: zero `KUBE-SVC` rules for `db`, a full set for `web`.

The choosing moved into **the client**. DNS handed it every ready Pod IP, and what happens next is the client library's business: it may take the first record and pin to it forever, round-robin them, or hold connections to all three. So "it isn't balancing" is usually a statement about the client's resolver behaviour rather than the cluster — and it is why a client that caches the first A record and never re-resolves will keep talking to a Pod that has since been replaced.

</details>

**Cleanup:**

```bash
kubectl delete svc web db
kubectl delete svc db-0 db-1 db-2 --ignore-not-found    # in case you kept the per-Pod attempt
kubectl delete svc extdb --ignore-not-found             # if you applied the ExternalName
kubectl delete deployment web
kubectl delete pod db-0 db-1 db-2
```

> **You understand this when you can** say why a default ClusterIP in front of three non-
> interchangeable replicas is worse than no Service, and what `clusterIP: None` removes in *two*
> subsystems; explain what a named port and an SRV record buy that an A record cannot; say why
> session affinity cannot ride on conntrack, and what that means for clients behind a shared NAT;
> and derive why `externalTrafficPolicy: Local` preserves a source IP and why a node with no local
> Pod then *hangs*.

**Which raises:** every shape here hands out Pod IPs, and headless Services depend completely on every Pod IP being routable from every other Pod. But nothing so far has said *who assigns those addresses*, or who strings the wire that makes a Pod on one node reachable from another. Act IV left that question open on purpose.

---

← Prev: **[CoreDNS — /etc/hosts for the cluster](04-coredns.md)** · ↑ **[Act V overview](README.md)** · Next: **[CNI — the veth-pair installer](05-cni.md)** →
