# Encryption between Pods

Act VIII spent six lessons building the machinery that makes bytes trustworthy, and lesson 08 used half of it: a signature over a digest, checked before anything ran. That was Act VIII applied to an artifact **at rest**.

The other half was about bytes **in flight**, and it stopped at the cluster's edge. Act V terminated TLS at an Ingress and then handed plaintext to a Pod. Act VI found the cluster running an entire certificate authority — `ca.crt`, `ca.key`, a serving certificate for every component — and used it to explain why the kubelet can talk to the API server at all. Ten acts, and not one packet between two of *your* Pods has ever been encrypted.

Act V did put a `tcpdump` on Pod-to-Pod traffic — `tcpdump -i any host 10.244.2.3 and port 8080 -nn`, in the debugging lesson. But it was hunting a handshake: SYN out, SYN-ACK back, or a RST. Flags, addresses and ports, which is what `-nn` with no `-A` gives you. Nobody ever asked it to print the bytes.

> **Predict first —** four commitments. **(a)** Two of your Pods on different nodes, talking HTTP. A third Pod, with no credentials, no relationship to either, and no permission to connect to anything. Can it read the conversation? Say what it would need in order to. **(b)** You apply a `NetworkPolicy` that permits exactly one client and denies everything else, on a CNI that really enforces it. Does that change your answer to (a)? **(c)** You turn on the CNI's transparent encryption and confirm it is working. Name a pair of Pods whose traffic is *still* plaintext afterwards. **(d)** That encryption needs both ends to agree on keys. Nobody typed a key. So where did the keys come from, what distributed them, and — the real question — what would someone have to compromise to read the traffic anyway?

### What is actually on the wire

Back on the `netlab` cluster, and this needs three Pods: a server, a client on the *other* node, and an observer that is party to neither.

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

kubectl create ns wire
kubectl -n wire wait --for=create serviceaccount/default --timeout=60s
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: server, namespace: wire, labels: {app: server}}
spec:
  nodeName: netlab-worker
  containers:
  - name: c
    image: python:3.12-alpine
    command: ["python3","-m","http.server","8080"]
---
apiVersion: v1
kind: Pod
metadata: {name: sniffer, namespace: wire}
spec:
  nodeName: netlab-worker
  hostNetwork: true
  containers:
  - name: c
    image: nicolaka/netshoot:latest
    command: ["sleep","3600"]
    securityContext: {capabilities: {add: ["NET_ADMIN","NET_RAW"]}}
EOF
kubectl wait --for=condition=Ready pod/server pod/sniffer -n wire --timeout=180s
SRV=$(kubectl get pod server -n wire -o jsonpath='{.status.podIP}'); echo "server: $SRV"
```

```
pod/server condition met
pod/sniffer condition met
server: 10.244.1.118
```

Look hard at what `sniffer` is, because every conclusion in this lesson depends on it and it is not exotic. `hostNetwork: true` plus `NET_RAW` — a Pod in the node's network namespace that may open a raw socket. Lesson 01 measured that `NET_RAW` is in the **default** capability set every container gets, and lesson 03 measured that `hostNetwork` is one of the specific fields `baseline` refuses. So this Pod is refused by a policy you know how to apply, and *only* by that policy. Nothing else in ten acts stops it.

Now capture, and send something worth stealing:

```bash
kubectl exec -n wire sniffer -- sh -c \
  'nohup tcpdump -i eth0 -A -s0 -c 20 "tcp port 8080" > /tmp/cap.txt 2>/dev/null & echo capturing'
sleep 3
kubectl run client -n wire --image=curlimages/curl:latest --restart=Never \
  --overrides='{"spec":{"nodeName":"netlab-control-plane"}}' --command -- \
  curl -s -m 10 -H "Authorization: Bearer s3cr3t-token-abc123" \
  "http://$SRV:8080/?password=hunter2"
sleep 5
kubectl exec -n wire sniffer -- sh -c 'grep -a -A6 "GET /" /tmp/cap.txt | head -10'
```

```
02:05:32.142171 IP 10.244.0.8.39944 > 10.244.1.118.8080: Flags [P.], seq 1:142, ack 1,
  win 64, length 141: HTTP: GET /?password=hunter2 HTTP/1.1
E...6.@.?...
...
..v.......Q.......@.......
M.e;X.-wGET /?password=hunter2 HTTP/1.1
Host: 10.244.1.118:8080
User-Agent: curl/8.21.0
Accept: */*
Authorization: Bearer s3cr3t-token-abc123
```

There it is. The password and the bearer token, in ASCII, read by a process that is **neither endpoint** and holds no credential for either of them.

And be precise about what that Pod needed, because the answer to prediction (a) is the uncomfortable part: it needed a place to stand. Not a key, not a certificate, not a token, not a route, not a `NetworkPolicy` exemption. It needed to be scheduled onto the node the traffic passes through — and a `nodeName` is not a permission, it is a scheduling hint. Everything this act has taught you about identity and authorisation is about who may **make** a request. None of it is about who may **read** one.

### The cluster already does this. For itself.

Same node, same tool, same second — point it at the control plane instead:

```bash
kubectl exec -n wire sniffer -- sh -c \
  'timeout 25 tcpdump -i eth0 -A -s0 -c 12 "tcp port 6443" > /tmp/cp.txt 2>/dev/null
   echo "packets: $(grep -ac "IP " /tmp/cp.txt)"
   echo "occurrences of GET/POST/Bearer/Authorization: $(grep -acE "GET |POST |Bearer |Authorization" /tmp/cp.txt)"'
kubectl exec -n wire sniffer -- sh -c 'grep -a -m1 -A2 "length 1" /tmp/cp.txt'
```

```
packets: 12
occurrences of GET/POST/Bearer/Authorization: 0
02:05:59.851531 IP netlab-control-plane.kind.6443 > netlab-worker.53910: Flags [P.],
  seq 3890712816:3890712939, ack 197819281, win 80, length 123
E...	$@.@............+........{....PX......
...Cg2s.....vf.5<..L....... ..AF.b....vV....dGW....y.6......Kb.{..R......$.0.Y.D...
```

Zero. The kubelet is issuing HTTP requests carrying its own client certificate and getting Pod specifications back, and none of it is legible. Act VI's PKI is doing exactly what it was built for.

So the cluster is entirely capable of this, on the same wire, and it does not do it for you. That is not an oversight, and the three reasons are worth having, because they are also the reasons the fixes look the way they do:

- **It does not know your protocol.** The kubelet-to-API-server link is HTTPS between two components the project ships. Your Pods speak Postgres, gRPC, Redis, AMQP, and something a contractor wrote in 2019. There is no single place to insert TLS into "whatever those two are doing."
- **It cannot rotate your certificates.** Act VI's `kubeadm certs renew` works because the cluster owns both ends. If Kubernetes issued a certificate to your container, something inside your container would have to notice it changed and reload — and that something is your application's code.
- **It would have to change your application.** Which is the honest summary: the cluster can hand a Pod a certificate (that is all a projected volume is), and it cannot make the process inside use it.

Hold those three, because every solution below is a different answer to "then who does the TLS?" — and the answers rank in exactly the order those constraints suggest.

### A CNI that enforces things, and a capture that still reads

kindnet cannot help us here for a reason Act V made a point of: **it does not enforce `NetworkPolicy`** — it accepts one and does nothing. So build the cluster Act V described for exactly this, with the CNI swapped for one that does transparent encryption.

Two changes from Act V's recipe, and the first matters more than it looks. Keep this cluster's kubeconfig in its own file:

```bash
cat > "${TMPDIR:-/tmp}/kind-enc.yaml" <<'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  disableDefaultCNI: true
nodes:
  - role: control-plane
  - role: worker
EOF

export ENCKUBE="${TMPDIR:-/tmp}/netenc.kubeconfig"
kind create cluster --name netenc --config "${TMPDIR:-/tmp}/kind-enc.yaml" --kubeconfig "$ENCKUBE"
```

Act V told you to switch between clusters with `kubectl config use-context`, which works and writes to `~/.kube/config`. `--kubeconfig` keeps a throwaway cluster's credentials in a throwaway file, so deleting the cluster deletes every trace of it and your real kubeconfig — the one with your employer's clusters in it — is never touched. Two clusters, two files, and `KUBECONFIG` selects one:

```bash
export KUBECONFIG="$ENCKUBE"
kubectl get nodes
```

```
NAME                   STATUS     ROLES           AGE   VERSION
netenc-control-plane   NotReady   control-plane   21s   v1.36.1
netenc-worker          NotReady   <none>          11s   v1.36.1
```

Both `NotReady`, which Act V taught you to read: there is no Pod network yet. Install one — Cilium, because it does encryption in the datapath and because Act V's CNI lesson already met it as "the Services moved out of a rule table and into a map":

```bash
helm repo add cilium https://helm.cilium.io
helm install cilium cilium/cilium --version 1.19.7 --namespace kube-system \
  --set ipam.mode=kubernetes --set image.pullPolicy=IfNotPresent
kubectl -n kube-system rollout status ds/cilium --timeout=420s
kubectl get nodes
```

```
daemon set "cilium" successfully rolled out
NAME                   STATUS   ROLES           AGE   VERSION
netenc-control-plane   Ready    control-plane   12m   v1.36.1
netenc-worker          Ready    <none>          12m   v1.36.1
```

Recreate the three Pods on this cluster — same manifests, `netenc-worker` in place of `netlab-worker` — and then ask Cilium what it is doing, because it has made a choice kindnet did not:

```bash
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status \
  | grep -E "^Routing|^Encryption"
```

Two names for one thing, and it is worth clearing up because there are genuinely three programs called some form of "cilium" here. **`cilium-dbg`** is the debug CLI *inside the agent* — Act V's CNI lesson called it `cilium service list` and `cilium monitor`, which still work, because `/usr/bin/cilium` in that image is a symlink to `cilium-dbg`. Separately there is a **`cilium` CLI you install on your laptop**, which manages the installation rather than inspecting the datapath. And `cilium-agent` is the daemon itself. This lesson only needs the first.

```
Routing:                 Network: Tunnel [vxlan]   Host: Legacy
Encryption:              Disabled
```

**`Tunnel [vxlan]`.** Which is Act IV's overlay lesson, and Act V's disappointment: Act V told you the `tcpdump -i any udp port 8472` experiment shows nothing on kindnet because kind's nodes route to each other directly with no encapsulation. On this cluster there is encapsulation, so point the sniffer at the tunnel and watch the two ideas collide:

```bash
kubectl exec -n wire sniffer -- sh -c \
  'nohup tcpdump -i eth0 -A -s0 -c 25 "udp port 8472" > /tmp/vx.txt 2>/dev/null & echo capturing'
sleep 3
kubectl run client -n wire --image=curlimages/curl:latest --restart=Never \
  --overrides='{"spec":{"nodeName":"netenc-control-plane"}}' --command -- \
  curl -s -m 10 -H "Authorization: Bearer s3cr3t-token-abc123" \
  "http://$SRV:8080/?password=hunter2"
sleep 6
kubectl exec -n wire sniffer -- sh -c \
  'L=$(grep -an "password=hunter2" /tmp/vx.txt | head -1 | cut -d: -f1); sed -n "$((L-1)),$((L+4))p" /tmp/vx.txt'
```

```
02:21:12.903986 IP netenc-control-plane.kind.36419 > netenc-worker.8472: VXLAN, flags [I] (0x08), vni 26851
IP 10.244.0.24.34804 > 10.244.1.139.8080: Flags [P.], seq 1:142, ack 1, win 64, length 141:
  HTTP: GET /?password=hunter2 HTTP/1.1
E...h..@..a.........C!..........h......v....m....E.....@.@...
D....-..GET /?password=hunter2 HTTP/1.1
Host: 10.244.1.139:8080
```

Read those two lines together, because they are the sentence worth taking out of this section. The outer header is node-to-node UDP. The inner header is Pod-to-Pod TCP. And the payload is `password=hunter2`.

**Encapsulation is not encryption.** VXLAN wraps a frame in another frame so it can cross a network that does not know about Pod addresses; it is an addressing mechanism, and it protects nothing. The word "tunnel" does most of the damage here — it sounds like something you cannot see into, and `tcpdump` decodes the outer header and prints the inside for you as a convenience.

### `NetworkPolicy` answers a different question

Prediction (b). Now do the thing that everybody reaches for, on a CNI that actually enforces it:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: server-allow-client, namespace: wire}
spec:
  podSelector: {matchLabels: {app: server}}
  policyTypes: [Ingress]
  ingress:
  - from: [{podSelector: {matchLabels: {role: allowed}}}]
    ports: [{protocol: TCP, port: 8080}]
EOF
sleep 5
kubectl run ok   -n wire --image=curlimages/curl:latest --restart=Never --labels=role=allowed \
  --command -- curl -s -m 8 -o /dev/null -w 'HTTP %{http_code}\n' "http://$SRV:8080/"
kubectl run nope -n wire --image=curlimages/curl:latest --restart=Never \
  --command -- curl -s -m 8 -o /dev/null -w 'HTTP %{http_code}\n' "http://$SRV:8080/"
sleep 20
for p in ok nope; do printf "%-5s " $p; kubectl logs $p -n wire; done
```

```
ok    HTTP 200
nope  HTTP 000
```

The policy is real — Act V's experiment, on a CNI that enforces it, with `nope` getting nothing at all. So with default-deny in force and exactly one permitted client, capture the permitted conversation:

```bash
kubectl delete pod ok nope -n wire
kubectl exec -n wire sniffer -- sh -c \
  'nohup tcpdump -i eth0 -A -s0 -c 25 "udp port 8472" > /tmp/np.txt 2>/dev/null & echo capturing'
sleep 3
kubectl run ok -n wire --image=curlimages/curl:latest --restart=Never --labels=role=allowed \
  --command -- curl -s -m 10 -H "Authorization: Bearer s3cr3t-token-abc123" \
  "http://$SRV:8080/?password=hunter2"
sleep 8
kubectl exec -n wire sniffer -- sh -c \
  'echo -n "password on the wire, occurrences: "; grep -ac "password=hunter2" /tmp/np.txt
   grep -a -m1 "Authorization" /tmp/np.txt'
```

```
password on the wire, occurrences: 4
Authorization: Bearer s3cr3t-token-abc123
```

Four times, in a twenty-five packet capture, while a policy that denies everything else is provably working.

This is the distinction the whole lesson turns on, and it is worth being blunt about it because the two get conflated constantly in design documents: **a `NetworkPolicy` decides who may open a connection. It has no opinion about who may read one.** It is an ACL on the *initiation* of traffic — the same shape as Act IX's RBAC, one layer down — and confidentiality is simply not the kind of thing it does. "We have a zero-trust network policy" and "our internal traffic is protected" are unrelated claims, and the first is regularly offered as evidence for the second.

### Turning it on

One flag, and a restart of the agent:

```bash
helm upgrade cilium cilium/cilium --version 1.19.7 --namespace kube-system --reuse-values \
  --set encryption.enabled=true --set encryption.type=wireguard
kubectl -n kube-system rollout restart ds/cilium
kubectl -n kube-system rollout status ds/cilium --timeout=420s
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status | grep -E "^Encryption"
```

```
Encryption:  Wireguard  [NodeEncryption: Disabled, cilium_wg0
             (Pubkey: touo4Gk9hTn22ftsi9FZacWGdPJLfJ8XTLzJI+0TXBo=, Port: 51871, Peers: 1)]
```

A device, a public key, a port and a peer count. **WireGuard** is the modern answer here — a few thousand lines in the kernel, one cipher suite with no negotiation, and therefore none of the downgrade and version-negotiation surface Act VIII spent a lesson on. There is no handshake to misconfigure because there is nothing to choose.

Now repeat the exact capture that just printed a password four times:

```bash
kubectl delete pod ok -n wire
kubectl exec -n wire sniffer -- sh -c \
  'nohup tcpdump -i eth0 -A -s0 -c 40 "udp" > /tmp/wg.txt 2>/dev/null & echo capturing'
sleep 3
kubectl run ok -n wire --image=curlimages/curl:latest --restart=Never --labels=role=allowed \
  --command -- curl -s -m 10 -H "Authorization: Bearer s3cr3t-token-abc123" \
  "http://$SRV:8080/?password=hunter2"
sleep 8
kubectl logs ok -n wire | grep -c "Directory listing"
kubectl exec -n wire sniffer -- sh -c \
  'echo -n "password on the wire, occurrences: "; grep -ac "password=hunter2" /tmp/wg.txt
   echo "and what is there instead:"; grep -a "IP netenc" /tmp/wg.txt | head -3'
```

```
2
password on the wire, occurrences: 0
and what is there instead:
02:23:29.010730 IP netenc-control-plane.kind.51871 > netenc-worker.51871: UDP, length 144
02:23:29.011184 IP netenc-worker.51871 > netenc-control-plane.kind.51871: UDP, length 144
02:23:29.011444 IP netenc-control-plane.kind.51871 > netenc-worker.51871: UDP, length 288
```

The request still worked — the client got its directory listing — and the wire is now UDP between two port-51871 endpoints with nothing legible in it. Note what disappeared along with the password: the VXLAN header, the Pod IPs, the ports, the fact that this was HTTP at all. WireGuard replaced the tunnel rather than sitting inside it, so the observer has lost the *metadata* too, which is more than TLS on the same connection would have hidden.

No application changed. No certificate was mounted. Nobody wrote a key.

### The pair of Pods this did not protect

Prediction (c), and this is the measurement to carry out of the lesson. Put the client on the **same node** as the server and run it again, with encryption still on and still verified:

```bash
kubectl exec -n wire sniffer -- sh -c \
  'nohup tcpdump -i any -A -s0 -c 30 "tcp port 8080" > /tmp/same.txt 2>/dev/null & echo capturing'
sleep 3
kubectl run same -n wire --image=curlimages/curl:latest --restart=Never --labels=role=allowed \
  --overrides='{"spec":{"nodeName":"netenc-worker"}}' --command -- \
  curl -s -m 10 -H "Authorization: Bearer s3cr3t-token-abc123" \
  "http://$SRV:8080/?password=hunter2"
sleep 8
kubectl exec -n wire sniffer -- sh -c \
  'echo -n "occurrences: "; grep -ac "password=hunter2" /tmp/same.txt
   grep -a -m1 "Authorization" /tmp/same.txt
   echo "on interfaces:"; grep -a "IP 10.244" /tmp/same.txt | awk "{print \$2}" | sort -u'
```

```
occurrences: 8
Authorization: Bearer s3cr3t-token-abc123
on interfaces:
lxc3cf7be70aa98
lxcd53c93ccd4af
```

**Eight.** Encryption is enabled, `cilium-dbg` confirms it, the cross-node capture is clean — and two Pods on one node exchange the password in the clear across two veth devices.

Once you see the mechanism this is not even surprising, which is the point: **the thing being encrypted is the link between nodes.** Two Pods on one node have no link between nodes; the packet goes veth to veth inside one kernel and never reaches a wire. There is nothing for a transport encryption scheme to encrypt, so it encrypts nothing, correctly.

The consequence is what matters, and it is a sentence you should be able to say to somebody who has just switched this on:

> Transparent CNI encryption defends against an observer **between** your nodes. It does nothing at all against an observer **on** one.

And "an observer on one" is not a stretch — it is the `sniffer` Pod, which needed `hostNetwork` and a capability every container already has. It is also, again, the place this act keeps arriving at: lesson 01's `hostPath: /`, lesson 02's per-node seccomp profile, lesson 06's encryption key in a file on the node, lesson 07's kubelet port. Five lessons, five mechanisms, one wall — **a shell on a node is close to a shell in the cluster** — and this is the first time that wall has cost you *confidentiality* rather than integrity.

Worth reading the status line again for the other limit it stated: `NodeEncryption: Disabled`. What you enabled covers Pod-to-Pod traffic. Traffic the *nodes* themselves originate — host-network Pods, the kubelet, anything on `hostNetwork: true` — is not in it unless you turn that on separately.

### Whose keys are those?

Prediction (d), and this is where the lesson stops being about networking. Nobody typed a key, and both ends agree on one. Find out how:

```bash
kubectl get ciliumnodes \
  -o jsonpath='{range .items[*]}{.metadata.name}{"  "}{.metadata.annotations.network\.cilium\.io/wg-pub-key}{"\n"}{end}'
```

```
netenc-control-plane  bSWVPI+RD83ORUNIYuLE7GrD+GrihIOZIRPg5qc12DQ=
netenc-worker         touo4Gk9hTn22ftsi9FZacWGdPJLfJ8XTLzJI+0TXBo=
```

Each agent generated a keypair, kept the private half on its node, and **published the public half as an annotation on an object in the API server.** Every other agent watches those objects and configures its peers from them.

Which means the confidentiality of every packet between your Pods rests on the integrity of a field in etcd. Act VIII's lesson on trust roots asked, every time, *who signed this, and why do you believe them* — and here the answer is that nothing signed it. There is no certificate, no chain, no authority. There is a value in an object, and the trust root is **whoever can write that object.**

So ask that question the way lesson 07 taught you to:

```bash
kubectl auth can-i update ciliumnodes --as=system:serviceaccount:kube-system:cilium
kubectl auth can-i patch  ciliumnodes --as=system:serviceaccount:kube-system:cilium
docker exec netenc-control-plane grep -o "enable-admission-plugins=[^ ]*" \
  /etc/kubernetes/manifests/kube-apiserver.yaml
```

```
yes
no
enable-admission-plugins=NodeRestriction
```

`CiliumNode` is cluster-scoped, so that `yes` means **any** `CiliumNode`, not just its own. The agent runs as a DaemonSet, one Pod per node, all sharing that one ServiceAccount. So an attacker who owns the agent on one node can rewrite the published public key of every other node and become the peer for their traffic.

And look at what did *not* save you. `NodeRestriction` is enabled — the plugin lesson 07 introduced precisely to stop a node from editing records that are not its own. It has no effect here, for two compounding reasons: it constrains the built-in `Node` and `Pod` resources, and `CiliumNode` is a **CRD** in the `cilium.io` group, which Act VII taught you is a first-class API object that nonetheless gets none of a built-in's special-case admission logic. And the agent's identity is `system:serviceaccount:kube-system:cilium`, not a `system:node:` name, so the plugin would not look at it anyway.

Be fair about the severity: an attacker who controls the Cilium agent on a node already has that node's traffic, because they hold its private key. What this grant does is turn *one* node's compromise into *every* node's traffic. That is the difference between an incident and a breach, and it is expressed entirely as an RBAC rule that nobody read while evaluating an encryption feature.

The general shape is the one this act keeps producing, now in its strongest form: **you cannot evaluate a cryptographic control without evaluating the authorisation on its key distribution.** A perfect cipher over a key anybody can replace is lesson 08's "signed by a key anybody can push to", one layer down the stack.

### The three answers, and what each one actually asserts

You now have enough measurements to rank the options honestly, and the useful axis is not strength — all three use sound cryptography — but **what identity the encryption binds to.**

| | Who does the TLS | Identity asserted | Same-node traffic | Cost |
|---|---|---|---|---|
| **In the application** | your code | whatever you put in the certificate — a service, a tenant, a user | encrypted | every app needs certs, rotation, and a code change |
| **In the CNI** (measured above) | the kernel, per node pair | **the node** | **plaintext** | one flag; no app changes |
| **In a mesh** (sidecar or ambient proxy) | a proxy beside your Pod | **the workload** — a SPIFFE identity per ServiceAccount | encrypted | a proxy per Pod, a control plane, real latency and real operational weight |

One word in that table needs unpacking, and Act IX's [in-the-wild page](../act-9-identity/in-the-wild.md) is where it was named. **SPIFFE** is a convention for giving a workload a *structured* identity — `spiffe://cluster/ns/default/sa/probe`, a string that says which namespace and which ServiceAccount — and handing it out as a short-lived X.509 certificate. So it is not a new mechanism at all: it is Act VIII's certificates carrying Act IX's ServiceAccount name, issued for minutes rather than months.

Now read the identity column, because it is the whole difference and it is where Act IX walks back in. CNI encryption lets you prove *this traffic came from that machine*. A mesh's mTLS lets you prove *this traffic came from that workload* — and a workload identity is a thing you can write authorisation rules about, which is why meshes end up shipping their own policy layer that looks a great deal like Act IX's RBAC with the subject changed.

That is also the honest answer to "should we run a mesh". The encryption is the cheapest thing a mesh gives you and the usual reason people install one; the identity is the expensive thing and the actual reason to. If the requirement is "traffic between our nodes must not be readable on the network", one flag does it and this lesson measured it working. If the requirement is "service A may call service B and service C may not, cryptographically, regardless of network position", nothing below the mesh row can express it — and note that `NetworkPolicy` cannot either, because it selects on labels which are an attribute of an object, not a credential the sender proves.

> **Check yourself —** a compliance requirement says "all data in transit must be encrypted." Your cluster has Cilium with WireGuard enabled, a default-deny `NetworkPolicy` in every namespace, and TLS terminating at the Ingress. Someone asks you to sign off. What do you refuse to sign, and what single piece of evidence would you gather first?

<details>
<summary>Answer</summary>

The claim is false as stated, and the fastest way to show it is a Pod count rather than an argument.

**What you would not sign:** "all". Three gaps, measured in this lesson and one from Act V:

**Same-node traffic is plaintext.** Any two Pods that happen to be co-scheduled talk in the clear. And this is worse than it sounds because it is *non-deterministic*: the same Deployment is encrypted or not depending on where the scheduler put the replicas this morning. A control whose coverage changes on a rollout is not a control you can attest to.

**Host-network traffic is not covered** unless `NodeEncryption` is on, which the status line will tell you and which was `Disabled` here by default.

**The Ingress terminates TLS and forwards plaintext.** Act V measured that. Encryption at the edge is often quoted as the answer to in-transit requirements, and it protects the leg you least control while leaving the leg inside the trust boundary open.

**The evidence to gather first:** for the top few workloads that handle regulated data, the actual co-location. `kubectl get pods -A -o wide` and check whether any pair that talks to each other is on one node right now. One such pair is a counterexample to "all", takes thirty seconds to find, and is far more persuasive than a description of the mechanism. Then ask what stops it happening tomorrow — because unless there is anti-affinity, nothing does. The honest control is this feature *plus* `podAntiAffinity`: the scheduling rule that keeps selected Pods **off** the same node, which is the mirror of the `nodeAffinity` Act VII used to pull them onto one. Nobody has ever written that down as a security requirement.

**And the thing to volunteer:** the `CiliumNode` RBAC finding. The requirement says encrypted; the interesting question is *against whom*, and the answer here is "anyone who cannot get a Pod onto a node and cannot write a `CiliumNode` object". Both of those are permissions, both are grantable, and neither appears in any document about encryption.

The reflex worth keeping: **"encrypted in transit" is not a property of a system, it is a property of a path.** Ask which paths, and the answer is always shorter than the claim.

</details>

<!-- figure -->
```
   TEN ACTS, AND NOT ONE PACKET BETWEEN TWO OF *YOUR* PODS
   HAS EVER BEEN ENCRYPTED.

   THE OBSERVER NEEDED NO CREDENTIAL
     hostNetwork: true + NET_RAW  ->  tcpdump
       NET_RAW is in the DEFAULT cap set (L01).
       hostNetwork is a field `baseline` refuses (L03).
     so it is stopped by ONE policy you know, and nothing else.
     GET /?password=hunter2 + Authorization: Bearer ... in ASCII,
     read by a process that is NEITHER ENDPOINT.
     what it needed was A PLACE TO STAND. a nodeName is not a
     permission. this act's identity/authz work is ALL about who
     may MAKE a request; none of it is about who may READ one.

   THE CLUSTER ALREADY DOES THIS -- FOR ITSELF
     same node, same tcpdump, port 6443:
       12 packets, GET/POST/Bearer/Authorization occurrences = 0
     Act VI's PKI, working. WHY NOT FOR YOU?
       1. it does not know your protocol (postgres/gRPC/2019 code)
       2. it cannot rotate YOUR certs (only owns both ends of its own)
       3. it would have to CHANGE YOUR APPLICATION -- it can hand a
          Pod a cert (a projected volume); it cannot make the process use it
     every solution below = a different answer to "then who does the TLS?"

   ENCAPSULATION IS NOT ENCRYPTION
     Cilium: Routing: Tunnel [vxlan]  (Act IV's overlay; Act V said
       kindnet has none, so you never got to see it)
     IP cp.36419 > worker.8472: VXLAN, vni 26851
       IP 10.244.0.24 > 10.244.1.139.8080: HTTP GET /?password=hunter2
     outer = node-to-node UDP. inner = pod-to-pod TCP. payload = the
     password. "tunnel" sounds opaque; tcpdump prints the inside FOR YOU.

   NetworkPolicy ANSWERS A DIFFERENT QUESTION
     enforced for real: allowed client 200 / unlabelled client 000
     and WITH default-deny in force, the permitted flow:
       password on the wire, occurrences: 4
     => AN ACL ON THE INITIATION OF TRAFFIC. Act IX's RBAC one layer
        down. IT HAS NO OPINION ABOUT WHO MAY READ.
        "we have a zero-trust network policy" is regularly offered as
        evidence for "our internal traffic is protected". unrelated claims.

   TURNING IT ON: one flag
     encryption.enabled + encryption.type=wireguard
     Encryption: Wireguard [NodeEncryption: Disabled, cilium_wg0
                 Pubkey: touo4..., Port: 51871, Peers: 1]
     WireGuard = a few thousand kernel lines, ONE cipher suite, NO
       negotiation -> none of Act VIII's downgrade surface. nothing to choose.
     re-run the capture:  occurrences: 0
       what's there: UDP 51871 <-> 51871, and the VXLAN header, the Pod
       IPs, the ports and "this is HTTP" are ALL GONE. it replaced the
       tunnel rather than riding inside it, so the METADATA went too --
       more than TLS on the same connection would have hidden.
     no app changed. no cert mounted. nobody wrote a key.

   *** AND THE PAIR IT DID NOT PROTECT ***
     same node, encryption ON and verified:
       occurrences: 8   on lxc3cf7be70aa98 + lxcd53c93ccd4af
     THE THING BEING ENCRYPTED IS THE LINK BETWEEN NODES.
     two Pods on one node have no such link -> nothing to encrypt,
     so it encrypts nothing, CORRECTLY.
     => defends against an observer BETWEEN your nodes. does NOTHING
        against an observer ON one.
     and it is NON-DETERMINISTIC: the same Deployment is protected or
     not depending on where the scheduler put the replicas today.
     5th arrival at the same wall: L01 hostPath:/ · L02 per-node seccomp
     · L06 the key in a file on the node · L07 port 10250 · here.
     A SHELL ON A NODE IS CLOSE TO A SHELL IN THE CLUSTER -- and this
     is the FIRST time that wall cost CONFIDENTIALITY, not integrity.
     also: NodeEncryption: Disabled -> host-network traffic not covered.

   WHOSE KEYS? -- and here it stops being about networking
     nobody typed a key, both ends agree on one:
       ciliumnodes  ->  annotation network.cilium.io/wg-pub-key
     each agent keeps the private half, PUBLISHES THE PUBLIC HALF AS A
     FIELD IN etcd. no certificate. no chain. NO AUTHORITY.
     Act VIII asked every time: WHO SIGNED THIS? here: nothing did.
     THE TRUST ROOT IS WHOEVER CAN WRITE THAT OBJECT:
       can-i update ciliumnodes (SA kube-system:cilium) -> YES
       (cluster-scoped, so ANY node's. one SA, one Pod per node.)
       can-i patch                                     -> no
     AND NodeRestriction IS ENABLED AND IRRELEVANT, twice over:
       it constrains built-in Node/Pod, and CiliumNode is a CRD
       (Act VII: first-class object, none of a built-in's special cases)
       and the identity is a ServiceAccount, not system:node:*
     FAIR SEVERITY: owning the agent already gives you THAT node's
     traffic. this grant turns ONE node's compromise into EVERY node's.
     => YOU CANNOT EVALUATE A CRYPTOGRAPHIC CONTROL WITHOUT EVALUATING
        THE AUTHORISATION ON ITS KEY DISTRIBUTION.
        a perfect cipher over a replaceable key = L08's "signed by a
        key anybody can push to", one layer down.

   THE THREE ANSWERS -- rank by IDENTITY, not by strength
     in the APP  : identity = whatever you put in the cert · same-node
                   ENCRYPTED · price: certs+rotation+a code change
     in the CNI  : identity = THE NODE · same-node PLAINTEXT
                   price: one flag
     in a MESH   : identity = THE WORKLOAD (SPIFFE, per ServiceAccount)
                   same-node ENCRYPTED · price: a proxy per Pod + a
                   control plane + real latency
     a workload identity is something you can write RULES about, which
     is why meshes ship a policy layer that looks like Act IX's RBAC
     with the subject swapped.
     the encryption is the CHEAPEST thing a mesh gives you and the usual
     reason people install one; THE IDENTITY IS THE REASON TO.
     and NetworkPolicy cannot express it either -- it selects on LABELS,
     an attribute of an object, not a credential the sender PROVES.
```

**Cleanup.** The second cluster is disposable and its kubeconfig goes with it, which was the point of `--kubeconfig`:

```bash
kind delete cluster --name netenc
rm -f "$ENCKUBE" "${TMPDIR:-/tmp}/kind-enc.yaml"

export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kubectl delete ns wire --ignore-not-found
```

> **You understand this when you can** capture a credential travelling between two Pods and say exactly what the capturing process needed in order to do it, naming the one field and the one capability and which earlier lessons measured each; explain why a `nodeName` is not a permission and what that says about the difference between this lesson's problem and everything else in the act; demonstrate that the cluster encrypts its own control-plane traffic on the same wire, and give the three reasons it does not do the same for your workloads; read `Routing: Tunnel [vxlan]` and predict what a capture of the tunnel shows; state in one sentence why encapsulation is not encryption, and say what misleads people about the word "tunnel"; prove a `NetworkPolicy` is being enforced and in the same breath show it protecting nothing about confidentiality, then state the question an ACL actually answers; enable WireGuard and verify it from both the agent's status and a packet capture; say what disappeared from the capture besides the payload, and why that is more than TLS would have hidden; predict, demonstrate and *explain* the pair of Pods it does not protect, in terms of what the scheme encrypts; say why that gap is non-deterministic and name the unrelated-sounding setting that is really a security control; connect this to the four earlier lessons that ended at the same wall, and say what is different about this one; find where the WireGuard public keys are published, and state what the trust root is in the absence of any certificate; run the authorisation check that matters, explain why `NodeRestriction` does not help — giving both independent reasons — and state the severity fairly; give the one-sentence general rule about cryptographic controls and key distribution; and lay out the three places encryption can live, ranked by the identity each one binds to, saying which of them a mesh is actually worth buying for and why `NetworkPolicy` cannot substitute.

**Which raises:** every control in this act refuses something. A capability refuses a syscall, a policy refuses an object, a signature check refuses an image, WireGuard refuses a reader. And this lesson just produced a failure mode that **nothing would refuse**: if somebody rewrote a `CiliumNode` annotation, every packet would still flow, every status line would still say `Wireguard`, `cilium-dbg` would still report a peer, and the only difference in the entire cluster would be *who else could read it*. There is no request to deny, because the write was authorised. Lesson 03 mentioned an `audit` verb and said it "tells only the audit log" — and you have never once looked at that log, or asked whether this cluster keeps one. **So what is written down about what has already happened here, who writes it, and what would you have to be recording to notice a control that is still reporting itself healthy while doing something else?**

---

↑ **[Act X overview](README.md)** · Prev: **[What you shipped](08-what-you-shipped.md)** · Next: **[Seeing it happen](10-seeing-it-happen.md)** →
