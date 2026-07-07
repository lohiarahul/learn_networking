# Act V — Diagnose it (the on-call drills)

`test-yourself` checked whether you can *recall* Act V. This checks whether you can *use* it. The
[worked failure](09-debugging-walkthrough.md) narrated a diagnosis for you, which is the right way to
meet a method once and the wrong way to learn it. Here nobody narrates. Each drill below puts your
cluster into a **real broken state**, hands you only the symptom, and asks you to find the cause by
reading files in the order [the five questions](08-debugging.md) prescribe.

**The rules (this is the whole point):**
1. **Don't study the "Reproduce it" block — just run it.** If you read it closely you'll spoil the
   hunt. Run it, then diagnose from the symptom like you would at 3am.
2. **Form a hypothesis before you inspect.** Say out loud which of the five questions you are on and
   which file would prove it — *then* look.
3. **Open the reveal only after you've tried.**

**Where:** your own terminal, with `kubectl` pointed at the two-node kind cluster from
[the lab lesson](01-lab-with-kind.md). Node-level commands go through `docker exec -it
netlab-control-plane bash`; Pod-level commands go through a throwaway netshoot Pod. Drill 4 is the
exception and says so: it needs the policy-enforcing cluster from the same lesson, because kindnet
will not enforce the policy that breaks it.

**The cleanup contract:** every drill builds everything it needs inside its **own namespace**, so its
`Cleanup` line is a single `kubectl delete namespace`, and nothing a drill creates can outlive it. Run
that line before starting the next drill. Nothing here touches `kube-system` or any cluster-wide
object, so a forgotten cleanup costs you a stray namespace, never a broken cluster — and
`kind delete cluster --name netlab` resets everything regardless.

---

## Drill 1 — "One new Pod can't reach anything by name"

> **Ticket:** *"We shipped a new client Pod and it cannot reach the `web` Service. Every other Pod in
> the same namespace reaches it fine — same node, same Service, same everything. The Pod is Running.
> And here's the strange part: if we hardcode the Service's ClusterIP into the client, it works
> perfectly. Only the name fails. How can DNS be broken for one Pod and fine for its neighbour?"*

**Reproduce it** (run; don't read):

```bash
kubectl create namespace drill1
kubectl -n drill1 create deployment web --image=nginx
kubectl -n drill1 expose deployment web --port=80
kubectl -n drill1 apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: client
spec:
  dnsPolicy: Default
  containers:
    - name: net
      image: nicolaka/netshoot
      command: ["sleep", "3600"]
EOF
kubectl -n drill1 wait --for=condition=ready pod/client --timeout=120s
```

**Confirm the symptom:**

```bash
CIP=$(kubectl -n drill1 get svc web -o jsonpath='{.spec.clusterIP}')
kubectl -n drill1 exec client -- curl -sS -m 5 -o /dev/null -w 'by name    -> %{http_code}\n' http://web/
kubectl -n drill1 exec client -- curl -sS -m 5 -o /dev/null -w 'by ClusterIP -> %{http_code}\n' "http://$CIP/"
```

The name fails — you get either `Could not resolve host: web` or a resolver timeout, depending on the
cluster — and the ClusterIP returns `200`. Everything below naming is demonstrably healthy.

**Your move.** Two Pods in the same namespace, on the same node, behave differently. So nothing
*shared* can be the cause: CoreDNS is up, the Service exists, the Pod network works (the ClusterIP
proved it). Something is different about this one Pod. Question 1's file is written per-Pod, by the
kubelet, at Pod creation. Read it in the broken Pod and in a healthy one, and diff them line by line —
there are three lines and all three matter.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Start a healthy Pod alongside it and compare the one file:

```bash
kubectl -n drill1 run ok --image=nicolaka/netshoot --restart=Never -- sleep 3600
kubectl -n drill1 wait --for=condition=ready pod/ok --timeout=120s

kubectl -n drill1 exec client -- cat /etc/resolv.conf     # the broken Pod
kubectl -n drill1 exec ok     -- cat /etc/resolv.conf     # a normal Pod
```

The healthy Pod has the three lines the CoreDNS lesson taught you to read:

```
nameserver 10.96.0.10
search drill1.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

The broken Pod has none of them — a different `nameserver` (whatever the *node* uses), no cluster
`search` list, and no `ndots`. Both halves of Question 1 are missing at once: without the search list,
`web` is a bare name that expands to nothing; and without `10.96.0.10` there is nobody who knows the
`cluster.local` zone to ask even if you wrote the name out in full. Confirm with the FQDN, which
should work if only the search list were missing:

```bash
kubectl -n drill1 exec client -- dig +short web.drill1.svc.cluster.local
```

Nothing useful comes back, which rules out "just an unqualified name" and points at the nameserver
line. So why does this Pod have a different file? Read its spec:

```bash
kubectl -n drill1 get pod client -o jsonpath='{.spec.dnsPolicy}{"\n"}'   # Default
kubectl -n drill1 get pod ok     -o jsonpath='{.spec.dnsPolicy}{"\n"}'   # ClusterFirst
```

**Root cause:** `dnsPolicy: Default` — which does not mean "the default" in any useful sense. It means
*inherit the node's `/etc/resolv.conf`*, bypassing cluster DNS entirely. The policy every Pod gets
when the field is omitted altogether is `ClusterFirst`, and that is the one that makes kubelet write the
CoreDNS nameserver and the search list. Someone set the field believing it was a no-op.

**Fix** — remove the field and let kubelet write a cluster resolver:

```bash
kubectl -n drill1 patch pod client --type=json \
  -p '[{"op":"replace","path":"/spec/dnsPolicy","value":"ClusterFirst"}]' 2>/dev/null \
  || echo "dnsPolicy is immutable on a running Pod — recreate it without the field"
```

That patch is refused, and the refusal is instructive: `dnsPolicy` is part of the Pod's immutable
spec, because `/etc/resolv.conf` is written once, at sandbox creation. You cannot fix a Pod's DNS by
editing the Pod. You delete it and create it without the field — which is exactly why this bug reaches
production inside a Deployment template and stays there.

**Cleanup:**
```bash
kubectl delete namespace drill1
```

</details>

---

## Drill 2 — "The Service refuses every connection, instantly"

> **Ticket:** *"`shop` is down. The name resolves, both Pods are Running with zero restarts, and the
> app is definitely listening — we curled it on its Pod IP and got a 200. But every connection to the
> Service is **refused**, immediately. Not a timeout. Refused. Who is even there to refuse it?"*

**Reproduce it** (run; don't read):

```bash
kubectl create namespace drill2
kubectl -n drill2 apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shop
spec:
  replicas: 2
  selector:
    matchLabels: { app: shop }
  template:
    metadata:
      labels: { app: shop }
    spec:
      containers:
        - name: web
          image: nginx
          ports: [ { containerPort: 80 } ]
---
apiVersion: v1
kind: Service
metadata:
  name: shop
spec:
  selector: { app: shop-web }
  ports: [ { port: 80, targetPort: 80 } ]
EOF
kubectl -n drill2 rollout status deployment/shop
```

**Confirm the symptom:**

```bash
kubectl -n drill2 run probe --rm -it --image=nicolaka/netshoot --restart=Never -- sh -c '
  dig +short shop.drill2.svc.cluster.local
  curl -sS -m 5 -o /dev/null -w "service -> %{http_code}\n" http://shop/ '
```

`dig` prints a ClusterIP from the service range, so naming is fine — then `curl` fails with
`Connection refused` in a fraction of a second.

**Your move.** Question 1 is clean, so you are below it. Use the distinction the debugging method
calls the most useful thing on the wire: this is not silence, it is a **refusal**, and a refusal is an
*answer* — something on the path decided against you and said so, in less time than the app could have
taken. Before you read any rules, read the object the rules are generated from, and look at what is in
it.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Read the list a Service DNATs toward:

```bash
kubectl -n drill2 get endpoints shop
kubectl -n drill2 get endpointslice -l kubernetes.io/service-name=shop
```

```
NAME   ENDPOINTS   AGE
shop   <none>      1m
```

Empty. The Service exists, the Pods exist, and the Service is pointing at nothing. That is a matching
problem, and there are exactly two strings involved:

```bash
kubectl -n drill2 get svc shop -o jsonpath='{.spec.selector}{"\n"}'   # {"app":"shop-web"}
kubectl -n drill2 get pods --show-labels                               # app=shop,...
```

`app=shop-web` versus `app=shop`. Nothing matches, so the EndpointSlice is empty. Now the part that
explains the *shape* of the failure — go read what kube-proxy wrote on the node:

```bash
CIP=$(kubectl -n drill2 get svc shop -o jsonpath='{.spec.clusterIP}')
docker exec netlab-control-plane iptables -t nat -S KUBE-SERVICES | grep "$CIP"
```

```
-A KUBE-SERVICES -d 10.96.x.y/32 -p tcp -m tcp --dport 80 -j REJECT --reject-with icmp-port-unreachable
```

There is no jump to a `KUBE-SVC-<hash>` chain, because there is nothing to load-balance across. kube-proxy
writes a **`REJECT`** instead — and that single word is your whole symptom. `REJECT` is `DROP`'s
answering sibling from [the debugging method](08-debugging.md): it discards the packet *and* replies, so
the client fails instantly instead of hanging. kube-proxy chose it on purpose, and that choice is what
told you, before you read a single rule, that you were not looking at a policy drop.

**Root cause:** the Service's selector does not match its Pods' labels, so the EndpointSlice is empty,
so kube-proxy has no DNAT target and installs a REJECT. The app was never involved at any point.

**Fix** — make the selector agree with the labels:

```bash
kubectl -n drill2 patch svc shop -p '{"spec":{"selector":{"app":"shop"}}}'
kubectl -n drill2 get endpoints shop        # two addresses now
docker exec netlab-control-plane iptables -t nat -S KUBE-SERVICES | grep "$CIP"   # a KUBE-SVC jump
```

The REJECT line is gone and a `-j KUBE-SVC-…` jump has taken its place, within a second or two of the
patch. You just watched kube-proxy reconcile.

**Cleanup:**
```bash
kubectl delete namespace drill2
```

</details>

---

## Drill 3 — "The Pod answers on its own IP and refuses through its Service"

> **Ticket:** *"`cart` refuses every connection through its Service, instantly. We learned from the
> `shop` ticket, so we checked the selector first this time and it matches the Pod labels exactly.
> `kubectl get pods` shows both Pods `Running` with zero restarts. Curling a Pod's IP directly returns
> 200 every time. The selector is right, the Pods are up, the app is serving. What is left?"*

**Reproduce it** (run; don't read):

```bash
kubectl create namespace drill3
kubectl -n drill3 apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cart
spec:
  replicas: 2
  selector:
    matchLabels: { app: cart }
  template:
    metadata:
      labels: { app: cart }
    spec:
      containers:
        - name: web
          image: nginx
          ports: [ { containerPort: 80 } ]
          readinessProbe:
            httpGet: { path: /healthz, port: 80 }
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: cart
spec:
  selector: { app: cart }
  ports: [ { port: 80, targetPort: 80 } ]
EOF
```

Give it half a minute to settle (`kubectl -n drill3 get pods -w`, then interrupt).

**Confirm the symptom:**

```bash
POD_IP=$(kubectl -n drill3 get pod -l app=cart -o jsonpath='{.items[0].status.podIP}')
kubectl -n drill3 run probe --rm -it --image=nicolaka/netshoot --restart=Never -- sh -c "
  curl -sS -m 5 -o /dev/null -w 'pod IP -> %{http_code}\n' http://$POD_IP/
  curl -sS -m 5 -o /dev/null -w 'service -> %{http_code}\n' http://cart/ "
```

Straight to the Pod's IP: `200`. Through the Service: refused. The app is serving and the Service will
not carry you to it.

**Your move.** You are in Question 3 again and the answer that solved the last drill is wrong here, so
the useful move is to ask the question *underneath* it: matching the selector is clearly not
sufficient to be in the endpoint list — so what else gets a veto, and who holds it? One more nudge:
`kubectl get pods` prints two columns about health, and both tickets so far only quoted one of them.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

Read the column nobody quotes:

```bash
kubectl -n drill3 get pods -l app=cart
```

```
NAME                    READY   STATUS    RESTARTS   AGE
cart-...-abcde          0/1     Running   0          2m
cart-...-fghij          0/1     Running   0          2m
```

`Running` and `0/1`. Those are two different claims by two different parties: `STATUS: Running` is the
container runtime saying the process is alive, and `READY: 0/1` is the **kubelet's probe** saying it is
not fit to receive traffic. The endpoint list obeys the second one:

```bash
kubectl -n drill3 get endpoints cart
kubectl -n drill3 get endpointslice -l kubernetes.io/service-name=cart -o yaml | grep -B2 -A4 conditions
```

This is the discriminator against the previous drill. `kubectl get endpoints` shows `<none>` in both
cases — but the EndpointSlice tells you *why*: here the Pod addresses **are listed**, each carrying
`conditions: ready: false`. In drill 2 there were no addresses at all. Not-selected and
selected-but-not-ready look identical through a Service and are completely different bugs.

Now ask the kubelet why:

```bash
kubectl -n drill3 describe pod -l app=cart | grep -i -A2 readiness
```

```
Warning  Unhealthy  ... Readiness probe failed: HTTP probe failed with statuscode: 404
```

**Root cause:** the readiness probe requests `/healthz`, and this image has no such path — it answers
`404`, the kubelet reads any non-2xx/3xx as a failure, and the Pod never becomes ready. The
EndpointSlice controller publishes only ready addresses, so both Pods are held out of the Service, the
endpoint set is empty, and kube-proxy installs the same `REJECT` you diagnosed in drill 2. A healthy
app was removed from its own Service by a health check that was asking the wrong question.

**Fix** — point the probe at a path the app actually serves:

```bash
kubectl -n drill3 patch deployment cart --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/"}]'
kubectl -n drill3 rollout status deployment/cart
kubectl -n drill3 get endpoints cart          # addresses appear as the new Pods pass the probe
```

Note which direction the fix went. Nothing in the network was wrong at any point; the fix is one string
in a probe. This is the mirror image of the `127.0.0.1` trap in Question 5 — there, every layer was
green and the app was unreachable; here, the app was reachable and a layer above it declared otherwise.

**Cleanup:**
```bash
kubectl delete namespace drill3
```

</details>

---

## Drill 4 — "It hangs for thirty seconds and nothing is logged anywhere"

> **Ticket:** *"A batch of config changes went in yesterday. Since then one client cannot reach the
> `db` Service. There is no error — the client hangs for about thirty seconds and gives up. The
> database logs nothing at all: not a rejected connection, not a failed auth, nothing. Both Pods are
> Running and READY, the Service has endpoints, and rolling the client back changed nothing. Someone
> suggested restarting the database. Should we?"*

> **This drill needs the policy-enforcing cluster** — the `disableDefaultCNI` cluster with Calico from
> [the lab lesson](01-lab-with-kind.md). On a default kindnet cluster the reproduce block applies with
> no error and nothing breaks, which is worth seeing exactly once and then leaving behind. Check with
> `kubectl config current-context` and `kubectl get pods -n kube-system | grep -i -e calico -e cilium`
> before you start; node-level commands below use that cluster's node container name.

**Reproduce it** (run; don't read):

```bash
kubectl create namespace drill4
kubectl -n drill4 create deployment db --image=nginx
kubectl -n drill4 expose deployment db --port=80
kubectl -n drill4 rollout status deployment/db
kubectl -n drill4 apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: baseline-hardening
spec:
  podSelector: {}
  policyTypes: [ Ingress ]
EOF
```

**Confirm the symptom:**

```bash
kubectl -n drill4 run probe --rm -it --image=nicolaka/netshoot --restart=Never -- sh -c '
  dig +short db.drill4.svc.cluster.local
  time curl -sS -m 10 -o /dev/null -w "service -> %{http_code}\n" http://db/ '
```

The name resolves to a ClusterIP. The `curl` sits there for the full ten seconds and dies with
`Operation timed out`. Nothing appears in the database's logs, because nothing arrived.

**Your move.** Naming is fine, and the failure is the *other* shape: not a refusal, **silence**. Silence
means the packet was killed before anything could answer it, which puts you in the half of Question 3
that is not about NAT — the filter half. Two files answer it. One is a Kubernetes object you can list
in this namespace in a single command. The other is a *state*, readable from the node, that tells you
whether the SYN was ever confirmed by anybody.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

First, is anything filtering at all?

```bash
kubectl -n drill4 get networkpolicy
kubectl -n drill4 describe networkpolicy baseline-hardening
```

```
PodSelector:  <none> (Allowing the specific traffic to all pods in this namespace)
Allowing ingress traffic:
  <none> (Selected pods are isolated for ingress connectivity)
```

Read that second line carefully: *selected pods are isolated*, and the allow list is empty. Now confirm
from the kernel's side that the SYN never completed. A conntrack entry for a dead flow does not linger
long, so this one has to be read **while a connection is in flight** — two terminals. In the first, leave
a probe Pod hammering the Service:

```bash
kubectl -n drill4 run hang --image=nicolaka/netshoot --restart=Never -- \
  sh -c 'while true; do curl -sS -m 20 -o /dev/null http://db/; done'
```

In the second, attach netshoot to the node's own network namespace (the `sysadmin` profile from the lab
lesson is what buys you conntrack) and read the table:

```bash
DB_IP=$(kubectl -n drill4 get pod -l app=db -o jsonpath='{.items[0].status.podIP}')
kubectl debug node/netcni-control-plane -it --profile=sysadmin --image=nicolaka/netshoot \
  -- sh -c "conntrack -L 2>/dev/null | grep $DB_IP"
```

The entry for that flow sits in `SYN_SENT` and never reaches `[ASSURED]` — sent, never confirmed, which
is conntrack's way of saying the packet went out and nothing ever came back. An `nmap` from a Pod says
the same thing in one word: `filtered`, not `closed`. Stop the loop when you have seen it:

```bash
kubectl -n drill4 delete pod hang
```

**Root cause:** an empty `podSelector: {}` selects **every Pod in the namespace**, and
`policyTypes: [Ingress]` with no `ingress:` list means "permit nothing inbound." NetworkPolicy is
default-allow *until a policy selects a Pod*, and then that Pod is default-deny — so a policy written as
a harmless baseline flipped every Pod in the namespace to deny-all. The drop happens in the kernel at
the node, before the packet reaches any application, which is precisely why the database has nothing to
log and why restarting it would accomplish nothing.

**Fix** — a default-deny is only half a policy; the other half is the allowance it was supposed to
carry:

```bash
kubectl -n drill4 apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-probe-to-db
spec:
  podSelector:
    matchLabels: { app: db }
  policyTypes: [ Ingress ]
  ingress:
    - from:
        - podSelector:
            matchLabels: { run: probe }
      ports:
        - port: 80
EOF
```

Re-run the probe and it returns `200` — same packet, same addresses, one label now permitted. Policies
are additive: the deny-all still selects the Pod, and this one adds the single exception. Note what you
had to know to write it: the client's label, not its IP.

**Cleanup:**
```bash
kubectl delete namespace drill4
```

</details>

---

## Where this leaves you

Four tickets, and only one of them was a bug in the layer the symptom pointed at. A Pod whose
`/etc/resolv.conf` was written from the wrong policy. A Service pointing at a label nobody wore. A
healthy app evicted from its own Service by a health check asking for a page that does not exist. A
one-line "baseline" policy that turned a namespace into a blackhole.

Two of the four produced the identical symptom — an instant refusal through a Service — and you told
them apart by reading one EndpointSlice: addresses absent versus addresses present but `ready: false`.
Two produced opposite symptoms from the same layer, and you told *those* apart before running a single
command, because a refusal is an answer and silence is not. That distinction, plus the discipline to
start at Question 1 no matter what the ticket claims the error was, is the entire method. Everything
else is knowing which file to open — and you have now opened all of them.

---

← **[Test yourself](test-yourself.md)** · ↑ **[Act V overview](README.md)** · Next: **[The whole stack](../the-whole-stack.md)** →
