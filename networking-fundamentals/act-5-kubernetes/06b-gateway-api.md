# Gateway API — when routing outgrows annotations

The Ingress from the last lesson works. Two hostnames, one IP, TLS terminated at the edge, a 404 for anything you didn't declare. So here is a request your product manager will make on a Tuesday: **send 10% of the traffic for `api.example.com` to a new version, and leave the other 90% where it is.**

Go and look for the field. Open the Ingress spec you just wrote and find where a weight would go.

### Why can't you express a canary in an Ingress?

There is no field. You don't have to take that on trust — every Kubernetes object has a schema, and `kubectl explain` prints it straight from the API server, which makes it the authority rather than a document that might be out of date:

```bash
kubectl explain ingress.spec.rules.http.paths --recursive
```

`path`, `pathType`, and `backend` — one backend, no weight. The spec has looked like that since it went `v1` in 2019, and it was frozen deliberately.

So how does anyone split traffic on an Ingress? With **annotations**:

```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"
```

Look carefully at what you just wrote, because three things are wrong with it and none of them is cosmetic.

It is **a string in a map**, so nothing validates it. Misspell `canary-weigth` and the API server accepts your manifest cheerfully; you find out from your traffic graphs. It is **invisible to the schema** — run `kubectl explain` against it and there is nothing to find, because as far as Kubernetes is concerned that annotation is an opaque key/value pair. And it is **vendor-private**: the prefix `nginx.ingress.kubernetes.io` is doing real work in that sentence. Hand this manifest to a cluster running Traefik and the annotation is silently ignored — the canary just doesn't happen.

That last point is the one that matters. By around 2020 every controller had grown its own annotation dialect for rewrites, timeouts, retries, header matching, and traffic splitting. An Ingress manifest stopped being portable, which is most of the reason a Kubernetes API exists at all.

### Is that the only problem?

No, and the second one is structural rather than cosmetic.

Read your Ingress again and notice that it holds two completely different kinds of decision in one object. `spec.tls` and the choice of controller are **infrastructure**: which IP the world reaches, which certificate it presents, who operates it. `spec.rules` are **application routing**: this hostname and path go to my service.

In a real organisation those belong to different people. A platform team owns the address and the certificate; a dozen application teams own their own routes. But Kubernetes grants permissions per object *kind*, and here there is exactly one kind — so any permission you grant covers the whole document. Either application teams can edit the TLS configuration of the shared front door, or they file a ticket every time they add a path.

Ingress has no way to say "you may add routes, but not touch the listener." That is not a missing feature; it is a missing *shape*.

### So what is the Gateway API?

The same job, split into three objects along the seams that actually exist:

| Object | Scope | Owned by | Answers |
|---|---|---|---|
| `GatewayClass` | cluster | infrastructure provider | *which implementation?* |
| `Gateway` | namespace | platform team | *which address, port, protocol, certificate?* |
| `HTTPRoute` | namespace | application team | *which requests go to which backend, in what proportion?* |

`GatewayClass` is the same trick as the `ingressClassName` you set one lesson ago, promoted to an object: something that names an implementation, so the thing referencing it doesn't have to care which controller is installed.

Now the part that does the work the annotation couldn't. A route names the Gateway it wants to attach to, in `parentRefs`. And the Gateway declares, per listener, which routes are permitted to attach, in `allowedRoutes`. **Both sides have to consent.** A platform team can publish a Gateway that says "routes from any namespace may attach, but only for hostnames under `*.example.com`", and then stop being a ticket queue.

```yaml
# Platform team owns this.
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: shared
spec:
  gatewayClassName: nginx
  listeners:
    - name: web
      protocol: HTTP
      port: 80
      hostname: "*.example.com"      # this listener only serves these names
      allowedRoutes:
        namespaces:
          from: Same                 # or All, or Selector
```

```yaml
# Application team owns this, and cannot touch the listener above.
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
spec:
  parentRefs:
    - name: shared                   # "attach me to that Gateway"
  hostnames:
    - api.example.com
  rules:
    - matches:
        - path: { type: PathPrefix, value: / }
      backendRefs:
        - name: api-v1
          port: 80
          weight: 90                 # the field that did not exist in Ingress
        - name: api-v2
          port: 80
          weight: 10
```

Go and ask the API server whether `weight` is real this time:

```bash
kubectl explain httproute.spec.rules.backendRefs.weight
```

It answers — which is defect two closed. Misspell it and the manifest is rejected rather than accepted-and-ignored, which is defect one. (One caveat, since this lesson is about silent acceptance: that rejection depends on server-side field validation. Apply with `--validate=false` and an unknown field is quietly *pruned* instead, putting you right back in annotation territory.) And defect three closes because `weight` lives in `gateway.networking.k8s.io` — a shared API group rather than one vendor's prefix — so any controller claiming conformance has to honour it. The same manifest works on a different implementation.

### The lab for this lesson

Two installs: the CRDs, then a controller. The kind cluster from [the lab lesson](01-lab-with-kind.md) is fine.

```bash
# 1. The API itself — CRDs only, no controller.
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
kubectl get crd | grep gateway.networking      # 8 of them: gateways, httproutes, gatewayclasses, ...

# 2. A controller that implements it. NGINX Gateway Fabric, NodePort flavour for kind.
#    --server-side is not optional here; see below.
kubectl apply --server-side -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.6.7/deploy/crds.yaml
kubectl apply -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.6.7/deploy/nodeport/deploy.yaml
kubectl -n nginx-gateway rollout status deployment/nginx-gateway
```

Two things in that block are worth more than a passing glance, because both are the lesson's own theme biting early.

**Why `--server-side`?** Drop it and the apply fails outright:

```
The CustomResourceDefinition "nginxproxies.gateway.nginx.org" is invalid:
metadata.annotations: Too long: may not be more than 262144 bytes
```

A client-side `apply` stashes a copy of the whole manifest in a `kubectl.kubernetes.io/last-applied-configuration` annotation so it can compute a diff next time — and that CRD's schema is about 650 KB, well past the 256 KB ceiling on annotation values. `--server-side` hands the object to the API server and lets *it* track ownership per field, so nothing is stashed. Without it the next line fails too, complaining it cannot find the kind `NginxProxy` — a cascade whose real cause is two commands earlier.

**Why `v1.5.1` and not the newest Gateway API release?** Because NGF v2.6.7 supports the `v1.2.1`–`v1.5.x` range, and it *tells you so* — in a status condition:

```bash
kubectl get gatewayclass                                        # ACCEPTED says True...
kubectl get gatewayclass nginx -o jsonpath='{.status.conditions}' | python3 -m json.tool
```

Pin a newer Gateway API and `ACCEPTED` is still `True`, which is exactly the kind of reassurance that gets people into trouble. The truth is one condition further in: `SupportedVersion: False`, reason `UnsupportedVersion`, message *"The Gateway API CRD versions are not recommended. Recommended version is v1.5.1."* With the pin above you get `SupportedVersion: True` instead. Read both conditions, not the column.

Pin whatever versions the projects' own install pages currently name — the paths are stable, the version strings are not, and the pairing matters. The controller choice is continuity rather than a recommendation: it is the same NGINX datapath you put behind an Ingress last lesson, driven by a different API, which is the cleanest way to see that the API is the thing that changed.

> **Image note —** two things about that install. The `LoadBalancer` flavour of it would leave `EXTERNAL-IP` at `<pending>` forever on kind, for exactly the reason [the Services lesson](03-services.md) gave, which is why this uses the NodePort manifest. And NGF pulls from **ghcr.io**, not Docker Hub — behind a registry allowlist the tell is `ImagePullBackOff` on the `nginx-gateway-cert-generator` Job, followed by the controller Pod stuck on `MountVolume.SetUp failed ... secret "server-tls" not found`. The second failure is a consequence of the first, not a separate problem.

Two backends to split traffic between:

```bash
kubectl create deployment api-v1 --image=hashicorp/http-echo -- /http-echo -text=v1 -listen=:5678
kubectl create deployment api-v2 --image=hashicorp/http-echo -- /http-echo -text=v2 -listen=:5678
kubectl expose deployment api-v1 --port=80 --target-port=5678
kubectl expose deployment api-v2 --port=80 --target-port=5678
```

Now save the Gateway manifest from above as `gateway.yaml` and apply just that one — not the route yet.

> **Predict first —** you are about to create exactly one object. When it settles, how many objects will exist that you did not create? Where would they be?

```bash
kubectl apply -f gateway.yaml
kubectl get gateway,deploy,svc          # in the Gateway's own namespace
```

A **Deployment and Service called `shared-nginx` have appeared**, named after your Gateway, in the namespace you put the Gateway in. You did not write them. NGINX Gateway Fabric's controller watched the Gateway object appear and *provisioned an NGINX for it* — that is what `Programmed` will mean on this implementation, and it is the most visible reconciliation loop in this act. You have seen two quieter ones already: kube-proxy watches Services and rewrites iptables chains, and last lesson's ingress controller watched Ingress objects and rewrote its own config. **Watch the object, make the world match it** — that loop is called **reconciliation**, and here it is concrete enough to `kubectl get`.

One caution, because it is easy to over-learn from a single implementation: *this shape is NGF's choice, not the API's requirement.* Another conformant controller might route every Gateway through one shared proxy it installed up front. What the API promises you is the `Gateway` object and its status — never the shape of the thing behind it.

That also explains a Service you will trip over if you go looking. The `nginx-gateway` Service back in the `nginx-gateway` namespace exposes only port 443, named `agent-grpc`: it is how the control plane talks to its data planes. It is not a way in. **The traffic path is the provisioned `shared-nginx` Service**, whose ports are named after your listeners — `port-80`.

Now attach the route, and reach it. `kubectl port-forward` opens a tunnel to a Service through the API server — worth noticing that unlike every other path in this act, that one is a userspace proxy, not a route the kernel takes:

```bash
kubectl apply -f httproute.yaml         # the HTTPRoute shown above

kubectl port-forward svc/shared-nginx 8080:80 &
sleep 2                                 # the forwarder needs a moment to bind — see below
curl -s -H 'Host: api.example.com' http://127.0.0.1:8080/
```

You should get `v1` or `v2`. Something is routing.

That `sleep` is not politeness. Skip it and `curl` returns exit code 7, connection refused, because the forwarder has not finished binding the local port — and that failure is nastier than it looks. `curl -s` prints nothing on a refused connection, so when you get to the hundred-request count below, the first few requests vanish with no error and no output line. The ratio still looks about right, so nothing tells you that ten of your hundred samples never happened.

> **On your own machine —** the `ADDRESS` column on `kubectl get gateway shared` is the ClusterIP of that provisioned `shared-nginx` Service. Worth checking they match, because it is the one place the API object and the implementation's plumbing visibly touch.

### Predict, then break it

Here is the experiment that teaches the delegation model, because it fails in the way that catches people in production.

Apply an HTTPRoute that asks for a hostname the listener does not serve — `api.internal` against a listener scoped to `*.example.com`.

> **Predict first —** does `kubectl apply` fail? If it succeeds, what does `kubectl get httproute` show — and how would you find out whether the route is doing anything at all?

```bash
kubectl apply -f - <<'EOF'
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: wrong-host
spec:
  parentRefs:
    - name: shared
  hostnames:
    - api.internal
  rules:
    - matches:
        - path: { type: PathPrefix, value: / }
      backendRefs:
        - name: api-v1
          port: 80
EOF

kubectl get httproute                          # both routes, looking equally healthy
```

**The apply succeeds.** No error, no warning, exit code 0. The object is stored by the API server exactly as you wrote it, because it is structurally valid — and structural validity is all the API server checks. `kubectl get httproute` then lists `wrong-host` beside `api` and gives you no way at all to tell that one of them is doing nothing.

So where is the difference recorded?

### Where does the truth live when it doesn't work?

**In `.status`, on both objects** — and this is the payoff for the whole lesson.

A controller that reconciles your object also **writes back what it did** — and, crucially, why it refused when it refused. That report is the only place the refusal exists.

```bash
kubectl get gateway shared                     # PROGRAMMED and ADDRESS columns
kubectl describe gateway shared                # per-listener status, attachedRoutes count
kubectl get httproute wrong-host -o jsonpath='{.status.parents[0].conditions}' | python3 -m json.tool
```

Three conditions carry almost all the diagnostic weight:

- On a Gateway, **`Programmed`** means a controller has actually configured a datapath for it — not merely that the object was stored. On this implementation you can see what that bought you: it is why `shared-nginx` exists.
- On an HTTPRoute, **`Accepted`** means a parent Gateway agreed to the attachment.
- On an HTTPRoute, **`ResolvedRefs`** means every `backendRefs` service was found.

For `wrong-host`, `Accepted` is `False`, with reason **`NoMatchingListenerHostname`**. The Gateway looked at your route, found no listener willing to serve `api.internal`, and declined the attachment. Change `from: Same` to a namespace the route isn't in and you get the sibling failure, `NotAllowedByListeners`.

That is a different discipline from the rest of this act. There is no `/proc` file here and no iptables chain to read — the enforcement lives inside a controller you didn't write. But the principle survives intact: *the object's own status is the controller's report, and when the status disagrees with your expectation, your expectation is wrong.*

### Watch the weights actually split traffic

Now the thing Ingress could not express.

> **Predict first —** with weights 90 and 10, how many of 100 requests reach `api-v2`? And if you changed the weights to 9 and 1 instead, what would happen?

```bash
for i in $(seq 100); do
  curl -s -H 'Host: api.example.com' http://127.0.0.1:8080/
done | sort | uniq -c
```

Roughly ninety to ten, with the noise you would expect from a hundred samples — and **9 and 1 behave identically**, because these are weights, not percentages. The controller sums them and divides. That is worth knowing before you write `weight: 10` on one backend, forget to give the other one a weight at all, and discover the default is `1`.

<!-- figure -->

```
   INGRESS                              GATEWAY API
   one object, one owner                three objects, three owners

   ┌───────────────────────┐            ┌──────────────┐  cluster-scoped
   │ Ingress               │            │ GatewayClass │  "which controller"
   │  tls:      (platform) │            └──────┬───────┘
   │  rules:    (app team) │                   │ gatewayClassName
   │                       │            ┌──────┴───────┐  platform team
   │  annotations:         │            │ Gateway      │  address, port, TLS
   │   nginx.ingress...    │            │  listeners:  │  allowedRoutes ──┐
   │   traefik.ingress...  │            └──────┬───────┘                 │
   │   ^ vendor-private,   │                   │ parentRefs          consent
   │     unvalidated,      │            ┌──────┴───────┐  app team        │
   │     not in the schema │            │ HTTPRoute    │ ◄────────────────┘
   └───────────────────────┘            │  weight: 90  │  a real, shared,
                                        │  weight: 10  │  validated field
   permission covers it all             └──────────────┘
```

### What does this cost you?

Everything above is a **CustomResourceDefinition** — a kind the API server did not ship with, taught to it at runtime. Gateway API is not built in; it is CRDs plus a controller that reconciles them, which is why the lab installed two things rather than none.

That has a consequence worth sitting with. On a cluster with no Gateway API CRDs, `kubectl get gateway` doesn't return an empty list — it errors, because the *kind* does not exist. And on a cluster where the CRDs are installed but no controller is running, every manifest in this lesson applies cleanly and nothing whatsoever happens: `Programmed` never becomes `True`, `attachedRoutes` stays at zero, and no traffic moves.

You met the first half of that shape back in the lab lesson: kindnet accepts a NetworkPolicy and enforces nothing — no error, no effect. **Both are the same class of bug. The cluster stored your intent, and nobody reconciled it.** An unreconciled object is indistinguishable from a working one under `kubectl get`, and the only thing that tells them apart is a status somebody has to read.

> **Check yourself —** `kubectl get httproute` shows your route. `kubectl get gateway` shows your Gateway. `curl` times out. Which of the two `.status` blocks do you read first, and what are you hoping to distinguish?

<details>
<summary>Answer</summary>

Read the **Gateway** first, and look for `Programmed`. That single condition separates "no controller is reconciling this at all" from "the controller is running and rejected my route." If `Programmed` is missing or `False`, nothing about the route matters yet — you have an unreconciled object, and no amount of fixing the HTTPRoute will help.

Only once the Gateway is `Programmed` does the route's own `Accepted` / `ResolvedRefs` pair become the interesting question: `Accepted: False` means the attachment was refused (hostname or namespace), and `ResolvedRefs: False` means a `backendRefs` service name doesn't resolve.

The order matters for the same reason the five-question method you are about to meet has an order — a failure lower down makes everything above it look broken.

</details>

**Cleanup**, in reverse order:

```bash
kill %1                                  # the backgrounded port-forward
kubectl delete httproute --all
kubectl delete gateway shared            # takes shared-nginx with it — the loop runs both ways
kubectl delete svc api-v1 api-v2
kubectl delete deployment api-v1 api-v2
kubectl delete --ignore-not-found -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.6.7/deploy/nodeport/deploy.yaml
kubectl delete --ignore-not-found -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.6.7/deploy/crds.yaml
kubectl delete -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
```

`kubectl delete gateway shared` really does take the provisioned Deployment and Service with it — they carry an owner reference back to the Gateway, so deleting the object you wrote garbage-collects the objects the controller wrote. Reconciliation runs in both directions.

Two details in that block. `--ignore-not-found` is there because the install's `nginx-gateway-cert-generator` Job sets `ttlSecondsAfterFinished: 30` and has always deleted itself by the time you get here — without the flag the command exits non-zero on a resource that was *supposed* to disappear. And note there are three `delete`s for three `apply`s: forget the NGF CRD line and you leave eleven `gateway.nginx.org` CRDs behind for the next lesson.

> **You understand this when you can** say why a traffic weight was impossible to express in an Ingress without a vendor annotation, and name the three things that annotation lacked which `HTTPRoute.spec.rules.backendRefs.weight` has; say which of `GatewayClass`, `Gateway` and `HTTPRoute` a platform team keeps and which it delegates, and how `parentRefs` and `allowedRoutes` make that delegation mutual rather than a free-for-all; and explain why an HTTPRoute that applies with exit code 0 can still move no traffic at all — including which `.status` condition you read first to tell an unreconciled Gateway apart from a refused route.

**Which raises:** an unreconciled object is invisible to `kubectl get`, and you have now seen two of them — a Gateway nobody programmed, and a NetworkPolicy nobody enforced. The second one is next, and this time the silence has teeth: the rule that isn't running is the one that was supposed to keep traffic *out*.

---

← Prev: **[Ingress — the front door](06-ingress.md)** · ↑ **[Act V overview](README.md)** · Next: **[Network Policy](07-network-policy.md)** →
