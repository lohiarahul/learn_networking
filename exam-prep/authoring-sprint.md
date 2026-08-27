# The authoring sprint — seven things you understood and cannot type

**This page is not teaching, and it is not a drill.** It is a timed authoring exercise, and every item
on it exists for one reason: the course made you *read* the thing and never made you *write* it.

That distinction is the whole point. Working through the acts leaves you able to explain what a
`StorageClass` is for, what `volumeBindingMode` decides, and why `WaitForFirstConsumer` puts
`nodeAffinity` on a PV. It does not leave you able to produce one from an empty file in ninety seconds
with only `kubectl explain` for company — and that second skill is the one a certification measures.
Nothing here reinforces a model. It closes the gap between recognition and recall, which is why it
lives in `exam-prep/` and not in an act.

> **Seven artifacts, 45 minutes, and only two references: `kubectl explain` and `--help`.** Close the
> Kubernetes documentation. If you cannot do an item at all, note which one and move on — the list of
> what you could not type is the actual output of this exercise.

The clock matters more here than in the drills. A diagnose drill rewards thinking; this rewards
fluency, and fluency is the thing that decays. Re-run it a fortnight before the exam and the second
set of times is the one that predicts anything.

---

## 1. A StorageClass with its own provisioner, and made the default

**Write it, apply it, and prove a PVC picks it up without naming it.**

<details>
<summary>What it should look like, and the one line that is not boilerplate</summary>

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: sprint-fast
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: rancher.io/local-path
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

Two things worth having at your fingertips. **The default is an annotation, not a field** — and it is
the only place in this list where a behaviour that important is expressed that way, which is exactly
why it is the one people cannot remember. And **a cluster may not have two defaults**, so making one
default means unmaking the other:

```bash
kubectl patch sc standard -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
```

The proof is a PVC that names no class at all:

```bash
kubectl create ns sprint
kubectl -n sprint apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: nosc }
spec:
  accessModes: [ReadWriteOnce]
  resources: { requests: { storage: 64Mi } }
EOF
kubectl -n sprint get pvc nosc -o jsonpath='{.spec.storageClassName}{"\n"}'
```

```
sprint-fast
```

**Something wrote a field you left blank.** That is the same admission-time mutation
[Act X lesson 04](../networking-fundamentals/act-10-cluster-security/04-deciding-before-it-exists.md)
measured on every Pod you have ever made, arriving here as a convenience you asked for.

</details>

---

## 2. A PriorityClass, and a preemption you can watch happen

**Two classes, a workload that fills a node, and one Pod that only fits if something leaves.**

<details>
<summary>What it should look like, and what the events actually say</summary>

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata: { name: sprint-low }
value: 100
globalDefault: false
description: "yields to anything that matters"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata: { name: sprint-high }
value: 100000
globalDefault: false
preemptionPolicy: PreemptLowerPriority
description: "takes the node it needs"
```

`value` is the whole object; everything else is documentation or a switch. Note that `PriorityClass`
is **cluster-scoped** — no namespace — and that the interesting field is the one you will not think to
write: `preemptionPolicy: Never` produces a Pod that jumps the *queue* and evicts nothing, which is a
completely different product from the default.

Fill a node with four low-priority Pods requesting 2200m each against 10 allocatable CPU, then send one
high-priority Pod that needs 2200m more than exists. Measured on the two-node `netlab` cluster:

```
$ kubectl -n sprint get events --sort-by=.lastTimestamp | grep -i preempt
Preempted   filler-fb44dbdf9-6fzrz   Preempted by pod 847d4915-… on node netlab-worker
```

```
NAME                     READY   STATUS    RESTARTS   AGE
filler-fb44dbdf9-2fmbh   0/1     Pending   0          31s
filler-fb44dbdf9-9c4m6   1/1     Running   0          32s
filler-fb44dbdf9-mcdzj   1/1     Running   0          32s
filler-fb44dbdf9-vxhnm   1/1     Running   0          32s
important                1/1     Running   0          31s
```

**Read the first line, because it is the part nobody expects.** Preemption did not *move* the evicted
Pod anywhere. The Deployment's replacement replica is `Pending` and will stay `Pending`, and the
scheduler says why:

```
0/2 nodes are available: 1 Insufficient cpu, 1 node(s) had untolerated taint(s).
preemption: 0/2 nodes are available: 1 No preemption victims found for incoming pod,
1 Preemption is not helpful for scheduling.
```

`No preemption victims found` — because the only Pods left on that node are *its own peers*, at its own
priority, and preemption only ever looks downward. So a single high-priority Pod has permanently
reduced a low-priority Deployment's capacity by one replica, and nothing is unhealthy. That is what
priority buys and what it costs.

</details>

---

## 3. The CoreDNS Corefile, edited and reverted

**Add a `rewrite` so that `legacy.internal` resolves to a Service, prove it, then put the file back.**

<details>
<summary>The edit, the proof, and the trap in the proof</summary>

```bash
kubectl -n kube-system get cm coredns -o jsonpath='{.data.Corefile}' > /tmp/Corefile.orig
```

**Save it first, every time.** This is the only item on the list that edits a running cluster's own
component, and the revert is the half people skip.

The line goes inside the `.:53 { … }` block, above `kubernetes`:

```
    rewrite name legacy.internal kubernetes.default.svc.cluster.local
```

Then apply and restart — the `reload` plugin will pick it up on its own within a couple of minutes, and
`rollout restart` is how you stop waiting:

```bash
kubectl -n kube-system create cm coredns --from-file=Corefile=/tmp/Corefile.new \
  --dry-run=client -o yaml | kubectl -n kube-system apply -f -
kubectl -n kube-system rollout restart deployment/coredns
kubectl -n kube-system rollout status deployment/coredns --timeout=180s
```

Now the proof, and **this is where the item earns its place on the list**, because the obvious check
lies to you:

```bash
kubectl -n dnsq run q --image=busybox:1.36 --restart=Never --command -- \
  sh -c 'nslookup legacy.internal'
```

```
** server can't find legacy.internal: NXDOMAIN
```

The rewrite is working perfectly. `busybox`'s `nslookup` is the problem: `legacy.internal` has one dot,
`ndots:5` means it gets qualified against the search list first, and busybox gives up on the first
`NXDOMAIN` instead of walking to the bare name. Ask the question the resolver was actually configured
to answer — with a trailing dot, which skips the search list entirely — and from a client that does not
stop early:

```bash
kubectl -n dnsq run q --image=nicolaka/netshoot --restart=Never --command -- \
  sh -c 'dig +short legacy.internal. ; dig +short kubernetes.default.svc.cluster.local'
```

```
10.96.0.1
10.96.0.1
```

Same address. The rewrite landed. Everything Act V's
[CoreDNS lesson](../networking-fundamentals/act-5-kubernetes/04-coredns.md) taught about `ndots` and
the search list is what stands between a working config and a `NXDOMAIN` you will believe.

Then revert, and check that you did:

```bash
kubectl -n kube-system create cm coredns --from-file=Corefile=/tmp/Corefile.orig \
  --dry-run=client -o yaml | kubectl -n kube-system apply -f -
kubectl -n kube-system rollout restart deployment/coredns
kubectl -n kube-system get cm coredns -o jsonpath='{.data.Corefile}' | grep -c rewrite   # 0
```

</details>

---

## 4. A Gateway API HTTPS listener, with `tls.mode` and `certificateRefs`

**A `Gateway` with one HTTPS listener terminating TLS from a Secret you make.**

> **Not verified against a running cluster, unlike everything else on this page.** Act V's
> [Gateway API lesson](../networking-fundamentals/act-5-kubernetes/06b-gateway-api.md) uninstalls the
> CRDs on its last page, and the environment this was written in could not reach the release artifact
> to reinstall them. The manifest below is the shape `kubectl explain` describes and the shape the
> lesson used; treat the *outputs* as expected rather than measured, and correct this section when you
> run it.

<details>
<summary>The manifest, and the two refusals to go looking for</summary>

```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -keyout gw.key -out gw.crt \
  -subj "/CN=shop.example.com" -addext "subjectAltName=DNS:shop.example.com"
kubectl -n gwq create secret tls shop-tls --cert=gw.crt --key=gw.key
```

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: shop
  namespace: gwq
spec:
  gatewayClassName: sprint-class
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      hostname: shop.example.com
      tls:
        mode: Terminate
        certificateRefs:
          - kind: Secret
            name: shop-tls
      allowedRoutes:
        namespaces:
          from: Same
```

Four things to have in your fingers, because each is a place the object gets rejected:

- **`certificateRefs` is a list of object references, not a string.** `kind: Secret` is required
  spelling even though it is the only kind anyone uses.
- **`mode: Terminate` takes certificates; `mode: Passthrough` must not have any.** Passthrough means
  the Gateway forwards the TLS connection without decrypting it, so it has no use for a key — and a
  `Passthrough` listener carrying `certificateRefs` is refused.
- **A cross-namespace `certificateRefs` needs a `ReferenceGrant` in the Secret's namespace.** This is
  the Gateway API's answer to the mutual-consent problem Act V's lesson opens with: naming an object in
  another namespace is a request, not a right.
- **Without a controller for the `gatewayClassName`, `status.conditions` is empty** — not `Accepted:
  False`, empty. That is [Act VII's CRD lesson](../networking-fundamentals/act-7-workloads/09-adding-a-kind.md)
  exactly: the object is stored, the schema was fine, and nothing looked at it. An empty status is the
  signature of a missing loop and never of a bad manifest.

</details>

---

## 5. A ResourceQuota and a LimitRange, from scratch

**Both, in a new namespace, and then read what they did to a Pod that asked for nothing.**

<details>
<summary>Both objects, and the three refusals they generate</summary>

```yaml
apiVersion: v1
kind: ResourceQuota
metadata: { name: tenant }
spec:
  hard:
    requests.cpu: "1"
    requests.memory: 1Gi
    limits.cpu: "2"
    pods: "10"
    count/deployments.apps: "3"
---
apiVersion: v1
kind: LimitRange
metadata: { name: tenant }
spec:
  limits:
    - type: Container
      default:        { cpu: 200m, memory: 128Mi }
      defaultRequest: { cpu: 100m, memory: 64Mi }
      max:            { cpu: "1",  memory: 512Mi }
      min:            { cpu: 10m,  memory: 16Mi }
```

The two are almost always written together, and the reason is the first measurement below. `default` is
a *limit*; `defaultRequest` is a *request*; the names do not rhyme and the exam will not remind you.
`count/<resource>.<group>` is the syntax for quota-ing object counts, and it is worth writing once
because it is unguessable.

**A Pod that asks for nothing:**

```bash
kubectl -n q1 run defaults --image=busybox:1.36 --restart=Never --command -- true
kubectl -n q1 get pod defaults -o jsonpath='{.spec.containers[0].resources}{"\n"}'
```

```
{"limits":{"cpu":"200m","memory":"128Mi"},"requests":{"cpu":"100m","memory":"64Mi"}}
```

Four numbers the author never typed. **That is why a `ResourceQuota` on `requests.cpu` is enforceable
at all** — a quota can only count what is on the object, and without a `LimitRange` most real Pods
carry nothing to count. The two objects are one control.

**A Pod above the ceiling:**

```
Error from server (Forbidden): pods "toobig" is forbidden:
  maximum cpu usage per Container is 1, but limit is 2
```

**And a Deployment above the quota, which is the one worth dwelling on:**

```bash
kubectl -n q1 create deployment greedy --image=busybox:1.36 --replicas=3 -- sh -c 'sleep 600'
kubectl -n q1 patch deployment greedy --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"cpu":"900m"}}}]'
kubectl -n q1 get deploy greedy -o jsonpath='{.status.replicas}/{.spec.replicas}{"\n"}'
kubectl -n q1 describe rs -l app=greedy | grep -A2 FailedCreate
```

```
3/3
  ReplicaFailure   True    FailedCreate
```

**The Deployment reads 3/3 and the ReplicaSet carries the refusal.** The quota rejected a *Pod*, the
thing that tried to create the Pod was a ReplicaSet, and a Deployment's status is a count that the old
ReplicaSet is still satisfying — which is the same trap as
[Act VII drill 1](../networking-fundamentals/act-7-workloads/diagnose.md) and the same rule: the object
you edited is not the object that carries the error.

One more, and it is the difference between authoring these and operating them. **Applying a quota to a
namespace that already exceeds it evicts nothing and refuses everything:**

```
Error from server (Forbidden): pods "defaults" is forbidden: exceeded quota: sprint-quota,
  requested: requests.cpu=100m, used: requests.cpu=11, limited: requests.cpu=2
```

A 100m Pod refused because of 11 cores that were already there. Quotas are admission controls, so they
govern the next write and have no opinion about the past — the namespace stays over its limit
indefinitely, and the only symptom is that nothing new starts.

</details>

---

## 6. An egress NetworkPolicy that blocks `169.254.169.254/32`

**Block the cloud metadata endpoint for every Pod in a namespace, without breaking anything else.**

<details>
<summary>The policy, and the two things that make it hard</summary>

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: no-metadata-service }
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except: [ 169.254.169.254/32 ]
    - to:
        - namespaceSelector: {}
      ports:
        - { port: 53, protocol: UDP }
        - { port: 53, protocol: TCP }
```

**There is no "deny" in a NetworkPolicy.** The only way to block one address is to allow everything
else, which is what `except:` under an `ipBlock` is for — and it is the single most-forgotten field in
the API. Getting the shape right is most of the item.

**And the second rule is why the DNS block is there.** `policyTypes: [Egress]` makes every selected Pod
default-deny outbound, and `169.254.169.254` is not the only thing that stops working — *DNS* stops
working, because CoreDNS is a Pod at a ClusterIP and a ClusterIP is not covered by an `ipBlock` at all.
An egress policy written with only the `except:` clause produces a namespace where nothing resolves,
which reads as "the network is broken" and is a one-line omission. Measured, in a namespace with the
DNS rule and without it:

```
with the DNS rule:      target BLOCKED   other reachable   dns works
without the DNS rule:   target BLOCKED   other BLOCKED     dns BROKEN
```

> **On verifying the real thing:** a `kind` cluster has no metadata endpoint, so `169.254.169.254` is
> already unreachable and blocking it proves nothing. Prove the mechanism against an address that *is*
> reachable — put a Pod's own IP in `except:` and watch that one Pod become unreachable while its
> neighbour stays up. Same field, same enforcement, and a result you can actually read.

Finally, the honest limit worth stating out loud, because it is the reason this control is weaker than
it looks: an `ipBlock` is enforced by the CNI, and
[Act V lesson 07](../networking-fundamentals/act-5-kubernetes/07-network-policy.md) measured that on
this cluster the verdict is made **in userspace**, by a process that can die. `queue flags bypass`
means it fails *open*. A metadata block that stops existing when an agent restarts is not a boundary,
it is a preference.

</details>

---

## 7. `kubectl`, verified against its published `sha256`

**Download the binary and the checksum, and check one against the other.**

<details>
<summary>The four commands, and the one that people get wrong</summary>

```bash
V=$(kubectl version --client -o json | python3 -c 'import json,sys; print(json.load(sys.stdin)["clientVersion"]["gitVersion"])')
OS=$(uname -s | tr 'A-Z' 'a-z'); ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
curl -sLO "https://dl.k8s.io/release/$V/bin/$OS/$ARCH/kubectl"
curl -sLO "https://dl.k8s.io/release/$V/bin/$OS/$ARCH/kubectl.sha256"
echo "$(cat kubectl.sha256)  kubectl" | shasum -a 256 --check
```

```
kubectl: OK
```

and, on a file that does not match:

```
kubectl: FAILED
shasum: WARNING: 1 computed checksum did NOT match
```

**The line people get wrong is the last one.** `kubectl.sha256` contains a bare hash and no filename,
so it is not a valid checksum file and `shasum --check kubectl.sha256` fails with *"no properly
formatted SHA checksum lines found"* — which reads like a download problem and is a format problem. The
two-field line has to be constructed. On Linux the command is `sha256sum -c` and the same applies.

And the thing worth saying about what this actually buys, because it is the smaller half of what people
assume: this proves the bytes match **what that URL said they should be**, and the hash arrived over the
same connection from the same host as the binary. It defends against a corrupted or truncated download
and against a mirror that changed one of the two. It does not defend against anyone who can serve both,
which is the gap a *signature* closes and a checksum cannot —
[Act X lesson 08b](../networking-fundamentals/act-10-cluster-security/08b-who-says-so.md)'s whole
subject, and the reason `cosign` exists.

</details>

---

## What the output of this exercise actually is

Not seven applied objects. **The list of items you could not type**, which is the only honest map of
where understanding stopped short of fluency. Six of these seven were verified on the two-node `netlab`
cluster while writing this page, and the writing kept turning up things reading had not:

- a PVC picking up a `storageClassName` nobody wrote,
- a preempted Deployment losing a replica *permanently* and reporting nothing wrong,
- a `LimitRange` being the reason a `ResourceQuota` can enforce anything at all,
- a Deployment reading `3/3` while its ReplicaSet carried the refusal,
- an egress policy that blocks one address and, written one line short, breaks every name in the
  namespace,
- and `busybox nslookup` returning `NXDOMAIN` for a name `dig` resolves correctly.

Every one of those is a thing you cannot learn by reading a manifest, and none of them is on the
syllabus.

---

← **[kubectl speed](kubectl-speed.md)** · ↑ **[Exam prep](README.md)** · Next: **[Exam day](exam-day.md)** →
