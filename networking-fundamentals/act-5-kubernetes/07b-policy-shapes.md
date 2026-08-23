# The four shapes of a NetworkPolicy — where the meaning lives in the indentation

The previous lesson gave you the model, and the model is the hard part: a policy selects Pods by label, any policy selecting a Pod makes that Pod default-deny for the direction it names, policies are additive, and there is no way to write a denial. All of that is true and none of it is enough, because every one of those sentences is about *reading* a policy. This lesson is about writing one, and writing one turns out to hinge on something the model does not mention at all.

Here is the whole problem in advance. A NetworkPolicy's `from:` is a **list**, and each element of that list is itself a small object with up to three fields. So there are two completely different ways to write down "two conditions", the YAML for them differs by one hyphen and two spaces, and they mean opposite things. Nothing in the document warns you which one you wrote.

> **Predict first —** below are two `from:` blocks. One says *Pods labelled `app=api`, in namespaces labelled `tier=frontend`*. The other says *anything in a `tier=frontend` namespace, or anything labelled `app=api`*. Decide which is which before you read on — and notice that you are not being asked a networking question.

```yaml
#  A                                    #  B
  from:                                   from:
    - namespaceSelector:                    - namespaceSelector:
        matchLabels: { tier: frontend }         matchLabels: { tier: frontend }
      podSelector:                          - podSelector:
        matchLabels: { app: api }               matchLabels: { app: api }
```

**A is the AND. B is the OR.** In A there is one list element carrying two fields, and a peer with two fields matches only when both are satisfied. In B there are two list elements, each carrying one field, and the `from:` list is satisfied by *any* member. The hyphen in front of `podSelector` is the entire difference between "the API Pods of the frontend team" and "the frontend team, plus anybody anywhere who calls themselves the API."

This is a list-nesting question wearing a networking costume, and it is reported as the most-cited technical failure on both the CKA and the CKS. It is worth ten minutes of proving rather than ten minutes of believing, so the rest of this lesson proves it.

## The bench

**On the policy-enforcing cluster only.** Everything below is measurement, and on kindnet every measurement returns the same answer whether or not the policy exists. Use the `netcni` cluster with Calico from [the lab lesson](01-lab-with-kind.md), and confirm before you spend any time:

```bash
kubectl config use-context kind-netcni
kubectl get pods -n kube-system | grep -c calico-node    # must be at least 1
```

Two namespaces, because a cross-namespace rule cannot be demonstrated inside one. One holds the target and two local clients; the other is labelled, and holds two more clients:

```bash
kubectl create ns polns
kubectl create ns other
kubectl label ns other tier=frontend

kubectl -n polns run db  --image=nginx:alpine --labels=app=database
kubectl -n polns run api --image=nicolaka/netshoot --labels=app=api   --command -- sleep infinity
kubectl -n polns run web --image=nicolaka/netshoot --labels=app=web   --command -- sleep infinity
kubectl -n other run api --image=nicolaka/netshoot --labels=app=api   --command -- sleep infinity
kubectl -n other run rogue --image=nicolaka/netshoot --labels=app=rogue --command -- sleep infinity

kubectl -n polns wait --for=condition=Ready pod --all --timeout=180s
kubectl -n other wait --for=condition=Ready pod --all --timeout=180s

kubectl -n polns expose pod db --port=80    # a Service, only so shape 4 has a name to resolve
DBIP=$(kubectl -n polns get pod db -o jsonpath='{.status.podIP}')
echo "$DBIP"
```

Every probe below talks to `$DBIP` directly, never to the Service — a NetworkPolicy selects Pods, and
routing a request through a ClusterIP would put kube-proxy's rewriting between you and the thing you
are trying to measure. The Service exists for one line at the very end of the lesson.

Four clients, and they are chosen so that each one differs from `other/api` in exactly one respect: `polns/api` has the right label in the wrong namespace, `other/rogue` is in the right namespace with the wrong label, and `polns/web` is wrong in both. That is the point of the bench — with four clients, the *shape* of the answer identifies the policy, and you never have to take anybody's word for what a document means.

One probe, used unchanged for the rest of the lesson:

```bash
probe() {
  for t in polns/api polns/web other/api other/rogue; do
    ns=${t%/*}; pod=${t#*/}
    if kubectl -n "$ns" exec "$pod" -- curl -s -o /dev/null --max-time 4 "http://$DBIP/" 2>/dev/null
    then echo "  $t  -> ALLOWED"
    else echo "  $t  -> denied (timed out)"
    fi
  done
}
probe
```

```
  polns/api  -> ALLOWED
  polns/web  -> ALLOWED
  other/api  -> ALLOWED
  other/rogue  -> ALLOWED
```

Four for four, which is the flat network the previous lesson opened with. Note the shape of a denial before you cause one: `curl` returns non-zero because it *timed out*, not because anything refused it. That is the kernel drop from the last lesson, and it is why the probe reports on exit status rather than on an HTTP code — there is no HTTP code to report.

## Shape 1 — the AND

```bash
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: db-and, namespace: polns }
spec:
  podSelector:
    matchLabels: { app: database }
  policyTypes: [ Ingress ]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels: { tier: frontend }
          podSelector:
            matchLabels: { app: api }
EOF
probe
```

```
  polns/api  -> denied (timed out)
  polns/web  -> denied (timed out)
  other/api  -> ALLOWED
  other/rogue  -> denied (timed out)
```

**One of those four lines is the one to sit with, and it is not the ALLOWED one.** `polns/api` carries the exact label the policy names, in the same namespace as the policy and the target, and it is denied. It is denied because the peer said *and*, and `polns` is not labelled `tier=frontend`. Adding a `namespaceSelector` to a peer did not widen that peer to include other namespaces — **it replaced the peer's namespace scope entirely**, and once you have said which namespaces qualify, your own is only among them if it matches.

That is the sentence to keep, because it inverts the intuition people bring: a `namespaceSelector` is not an addition, it is a substitution. If you want *this* namespace as well, you have to say so, and saying so is the next shape.

## Shape 2 — the OR, from the same two selectors

Change nothing but the indentation. One hyphen, two spaces:

```bash
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: db-and, namespace: polns }
spec:
  podSelector:
    matchLabels: { app: database }
  policyTypes: [ Ingress ]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels: { tier: frontend }
        - podSelector:
            matchLabels: { app: api }
EOF
probe
```

```
  polns/api  -> ALLOWED
  polns/web  -> denied (timed out)
  other/api  -> ALLOWED
  other/rogue  -> ALLOWED
```

**Two rows flipped, and they flipped for different reasons.** `polns/api` is now allowed because a bare `podSelector` in a peer means *in this policy's own namespace* — which is the same substitution rule read from the other end: say nothing about namespaces and you get the local one. And `other/rogue` is now allowed because a bare `namespaceSelector` means *every Pod in those namespaces*, and nothing in that peer mentions labels at all.

So the two documents differ by one hyphen and disagree about half the cluster. Notice which mistake is dangerous. Writing the AND when you meant the OR breaks traffic, and broken traffic gets reported in minutes. Writing the OR when you meant the AND admits every Pod in a whole namespace, silently, and looks exactly like a working policy — the same asymmetry the previous lesson found in a policy the CNI ignores. **Policy mistakes that fail open do not generate tickets.**

Both documents were `kubectl apply`-ed with the same name and no complaint, because they are both valid. There is no field here that a schema check could have caught, and no status condition to read afterwards. The four-client probe is the check.

> **Check yourself —** you want "the `app=api` Pods in namespace `other`, and nothing else." You have both shapes above. Which do you write, and what would you have to change about the bench for the other shape to give the same four answers?

<details>
<summary>Answer</summary>

Write the AND (shape 1) — one peer, both selectors. It gives exactly `other/api`.

The OR would give the same four answers only if you removed the reason the extra rows match: label `polns` with something the `namespaceSelector` does not select (already true), *and* delete or relabel `other/rogue` so that no other Pod exists in `other`, *and* remove `polns/api`'s `app=api` label so the bare `podSelector` matches nothing locally. In other words you would be making the *cluster* enforce what the *policy* should have said — which works until somebody creates a Pod. This is the difference between a policy that is correct and a policy that happens to be true today.

</details>

## Shape 3 — `ipBlock`, and the one peer that cannot share

The two selectors above both key on identity, which is the whole design. `ipBlock` is the deliberate exception, for the traffic that has no Kubernetes identity to select on — anything from outside the cluster.

It is also the only shape whose document cannot be copied from one cluster to another, because it names addresses rather than labels, and the addresses depend on what somebody chose the Pod network to be. So read them off the cluster instead of typing them:

```bash
PODNET="$(echo "$DBIP" | cut -d. -f1,2).0.0/16"
OTHERAPI=$(kubectl -n other get pod api -o jsonpath='{.status.podIP}')
echo "permit $PODNET  except $OTHERAPI/32"
```

Both clusters in this act use a `/16`, so the first two octets of any Pod IP name the network — a shortcut that holds here and is not a rule. `kubectl -n kube-system get pod -l component=kube-controller-manager -o yaml | grep cluster-cidr` is where a cluster states it properly, and on the Calico cluster it will read `192.168.0.0/16` rather than the `10.244.x.y` addresses the rest of this act shows.

> **Predict first —** the policy below permits the entire Pod network and subtracts one address: `other/api`'s. That Pod carries the exact label shape 1 selected, in the exact namespace shape 1 named. Which of the four clients reach the database now?

```bash
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: db-and, namespace: polns }
spec:
  podSelector:
    matchLabels: { app: database }
  policyTypes: [ Ingress ]
  ingress:
    - from:
        - ipBlock:
            cidr: $PODNET
            except:
              - $OTHERAPI/32
EOF
probe
```

```
  polns/api  -> ALLOWED
  polns/web  -> ALLOWED
  other/api  -> denied (timed out)
  other/rogue  -> ALLOWED
```

**The one Pod that both earlier shapes were written to admit is the only one now refused, and the three that neither shape could name are all through.** Nothing about identity changed — `other/api` still carries `app=api` and still lives in a `tier=frontend` namespace. The policy simply cannot see any of that: an `ipBlock` peer resolves a source address, and this Pod's address is in a hole. Labels and addresses are two different coordinate systems over the same Pod, and `ipBlock` is the only peer that uses the second one.

Notice also that the heredoc lost its quotes — `<<EOF` rather than `<<'EOF'`, so the shell fills the two values in. That is the working cost of `ipBlock`: it is the one peer you cannot finish writing until you know where you are.

`cidr` is what is permitted and `except` is subtracted from it, so this is the one place in NetworkPolicy where something that reads like a deny rule exists — and it is not one. It is a hole in an allow, which is why it can only ever narrow the `cidr` above it and can never reference an address outside it.

Now the constraint worth remembering, because the API server enforces it and the error is clear:

```bash
kubectl apply -f - <<'EOF' 2>&1 | tail -2
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: db-mixed, namespace: polns }
spec:
  podSelector:
    matchLabels: { app: database }
  policyTypes: [ Ingress ]
  ingress:
    - from:
        - ipBlock: { cidr: 10.244.0.0/16 }
          podSelector:
            matchLabels: { app: api }
EOF
```

```
The NetworkPolicy "db-mixed" is invalid: spec.ingress[0].from[0]: Forbidden:
may not specify both ipBlock and another peer
```

**`ipBlock` cannot share a peer with a selector**, and the reason is the same substitution rule again from a third angle: a selector-based peer is resolved against Pod identity, an `ipBlock` peer is resolved against a source address, and there is no coherent meaning for "both" — the two describe different things about the same packet. If you want either, use two list elements, which by shape 2 means OR.

One practical warning that follows directly. `ipBlock` matches the source address **as the enforcement point sees it**, and that address is not always the original sender. Traffic that arrived through a NodePort or a `LoadBalancer` with `externalTrafficPolicy: Cluster` has been SNAT-ed to a node address by the time it reaches the target's node, so an `ipBlock` naming the real client's network will not match, and one naming the node network will match every external client at once. Act IV's NAT lesson is the thing to re-read if that sentence is uncomfortable — this is that lesson's masquerade arriving in a security control.

## Shape 4 — egress, and the outage everybody causes once

Everything so far has been `Ingress`. Egress is the same grammar pointed the other way, with one field renamed — `to:` instead of `from:` — and one consequence nobody predicts. Clear the ingress policy first, so that whatever fails next has exactly one possible cause:

```bash
kubectl -n polns delete networkpolicy db-and
probe                                    # four for four again, back to the flat network
```

Now deny all outbound traffic from the `polns` clients:

```bash
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: no-egress, namespace: polns }
spec:
  podSelector: {}
  policyTypes: [ Egress ]
EOF
```

That is the whole document. `podSelector: {}` is every Pod in the namespace, `policyTypes: [ Egress ]` switches every one of them to default-deny outbound, and there is no `egress:` list, so nothing is permitted. Now watch what breaks, and watch *how* it breaks:

```bash
kubectl -n polns exec api -- curl -s -o /dev/null --max-time 4 http://$DBIP/ ; echo "by IP: exit $?"
kubectl -n polns exec api -- nslookup db.polns.svc.cluster.local 2>&1 | tail -2
```

```
by IP: exit 28
;; no servers could be reached
```

Two failures, and only the first one is the one you asked for. The second is DNS, and it is the trap: **CoreDNS is an ordinary Pod in an ordinary namespace, so a query to it is ordinary egress**, and a default-deny egress policy blocks it along with everything else. The symptom is not "connection refused" and not "policy denied" — it is name resolution timing out, several layers away from the document you just wrote, in an application that has never heard of NetworkPolicy. People spend an afternoon on CoreDNS.

The fix is to allow the one thing the cluster cannot function without, and it needs a label you have not had to think about:

```bash
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: no-egress, namespace: polns }
spec:
  podSelector: {}
  policyTypes: [ Egress ]
  egress:
    - to:
        - namespaceSelector:
            matchLabels: { kubernetes.io/metadata.name: kube-system }
      ports:
        - { port: 53, protocol: UDP }
        - { port: 53, protocol: TCP }
EOF
kubectl -n polns exec api -- nslookup db.polns.svc.cluster.local 2>&1 | grep -c Address
```

```
2
```

`kubernetes.io/metadata.name` is set automatically on every namespace by the API server, with the namespace's own name as its value — so you can select a namespace by name without anyone having remembered to label it. It is the label to reach for whenever a policy has to name `kube-system`, and it exists precisely because policies need to and namespaces are not otherwise guaranteed to carry anything.

Both `protocol` entries matter. DNS is UDP until a response exceeds what a UDP packet will carry, at which point the resolver retries over TCP — so a policy allowing only UDP/53 works perfectly until somebody's answer gets big, which is the worst kind of working.

And the shape of the fix is the general lesson of the whole lesson. A default-deny is one line of YAML and an inventory problem: the line is easy, and everything the workload actually needed is now something you have to know and enumerate. DNS is the item everyone forgets. The API server, the metrics endpoint, an external payment provider and the cloud metadata IP are the next four.

## Clean up

```bash
kubectl delete ns polns other
kubectl config use-context kind-netlab
```

> **You understand this when you can** write, from a blank file, a policy that permits exactly *Pods labelled `app=api` in namespaces labelled `tier=frontend`* — and say what the same two selectors permit when you add one hyphen; explain why a bare `podSelector` in a peer means "this namespace" and a `namespaceSelector` therefore *replaces* rather than extends that scope; say why `ipBlock` may not share a peer with a selector, and why an `ipBlock` naming a client's real network silently fails to match traffic that arrived through a NodePort; and predict, before running it, the two things a `policyTypes: [Egress]` document with no `egress:` list breaks — naming which one presents as a DNS fault and which label lets you allow it back.

---

← Prev: **[Network Policy](07-network-policy.md)** · ↑ **[Act V overview](README.md)** · Next: **[The debugging method](08-debugging.md)** →
