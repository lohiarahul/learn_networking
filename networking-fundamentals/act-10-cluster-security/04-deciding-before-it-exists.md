# Deciding before it exists

Pod Security Admission is a good mechanism with one structural limit: **the predicate is not yours.** Somebody at the Kubernetes project decided which fields matter, wrote three levels, and shipped them. You can choose a level and you cannot choose a rule.

A rule like *no image may use the `latest` tag* is the same *kind* of statement as `baseline` — a predicate over an object being written — and it is not expressible as a `pod-security.kubernetes.io/*` label, because no level was built for it.

Act IX left the same thread hanging from the other end. It proved that a Role cannot hold a predicate, observed that a cluster is evidently evaluating some, and asked where they went and, specifically, *why later is better*.

> **Predict first —** three commitments. **(a)** You need the rule "no image may use the `:latest` tag". Given RBAC (Act IX), namespace labels (lesson 03), and the kernel (lessons 01–02), which of those three could hold it — and if none, what does that tell you about what a rule needs in order to be checkable? **(b)** Act IX proved that *"an owner may only touch their own object"* is inexpressible in RBAC, because rules list names and cannot make a comparison. Do not guess a mechanism — instead write down what a decision point would have to be *handed* in order to make that comparison at all, and keep the note. **(c)** Suppose you deploy your own policy service into the cluster and it crashes at 2am. What happens to Pod creation?

### What a write already goes through

You drew this chain once already. [Act VI lesson 01](../act-6-control-plane/01-the-api-server-is-a-filesystem.md#what-did-that-write-pass-through-on-the-way-in) put five requests through the API server and read the stage each one died at off the wording — `401` with no user named, `is forbidden` naming user and verb, `unknown field`, `is invalid`, and one request that succeeded while quietly acquiring a ServiceAccount token nobody asked for. This section does not re-derive that. It adds the two things Act VI could not: a mutation **you** install, and the one stage on the chain that has still never refused you anything.

Start by confirming the mutation you already know about is still happening, because everything below hangs off it. Into an untouched namespace, create one perfectly ordinary Pod, asking for nothing:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

kubectl create ns mutshow
kubectl run m0 --image=busybox:1.36 -n mutshow --restart=Never --command -- sh -c 'echo hi'
sleep 4
kubectl get pod m0 -n mutshow -o jsonpath='serviceAccount: {.spec.serviceAccountName}
volumes: {.spec.volumes[0].name}{"\n"}'
```

```
serviceAccount: default
volumes: kube-api-access-fsmcf
```

(The trailing five characters are generated; yours will differ.)

**Nothing in your command mentioned either of those.** The object that got stored is not the object you sent — something assigned it an account and mounted a credential for it:

```bash
kubectl get pod m0 -n mutshow -o jsonpath='{.spec.volumes}' | python3 -m json.tool | head -12
```

```json
[
    {
        "name": "kube-api-access-fsmcf",
        "projected": {
            "defaultMode": 420,
            "sources": [
                {
                    "serviceAccountToken": {
                        "expirationSeconds": 3607,
                        "path": "token"
                    }
                },
```

That is Act IX's ServiceAccount token — the one you took apart by hand, with an hour of life — **mounted into a Pod that never asked for a credential.** Act VI showed you the volume; Act IX showed you what is in it. Put the two together and it is a live, cluster-scoped credential injected into every workload you have ever run, by a stage you cannot opt out of. Hold that; it is lesson 07's whole subject.

Now put something of your own into that same stage, so you can watch one fire deliberately. A `LimitRange` is a namespace-scoped object whose entire job is to fill in `requests` and `limits` on containers that omitted them — Act VII lesson 04's two numbers, written by the cluster instead of by you:

```bash
kubectl apply -n mutshow -f - <<'EOF'
apiVersion: v1
kind: LimitRange
metadata: {name: defaults}
spec:
  limits:
  - type: Container
    defaultRequest: {cpu: "50m", memory: "64Mi"}
    default: {cpu: "200m", memory: "128Mi"}
EOF
kubectl run m --image=busybox:1.36 -n mutshow --restart=Never --command -- sh -c 'echo hi'
sleep 4
kubectl get pod m -n mutshow -o jsonpath='resources: {.spec.containers[0].resources}{"\n"}'
```

```
resources: {"limits":{"cpu":"200m","memory":"128Mi"},"requests":{"cpu":"50m","memory":"64Mi"}}
```

Two mutations, honestly labelled: one you never installed and cannot switch off, and one you installed thirty seconds ago. Both edited the object between "you sent a request" and "an object exists". So here is Act VI's chain again — same six stages, now annotated with the receipt *this act* has for each, which is a different set of receipts and a much more uncomfortable one:

```
   request
     -> AUTHENTICATION      Act IX: 401, no name in the error
     -> AUTHORIZATION       Act IX: 403, names user + verb + resource
     -> DECODE, strict fields
                            lesson 03: "strict decoding error: unknown
                            field" -- and lesson 03 was explicit that this
                            happens BEFORE any admission plugin runs
     -> MUTATING admission  the token volume and the LimitRange, above
     -> OBJECT validation   is the decoded object internally consistent?
                            (the one stage here you have never seen refuse
                            anything. you will, at the end of this lesson,
                            and what trips it will be a mutation)
     -> VALIDATING admission lesson 03: "violates PodSecurity"
     -> persisted to etcd   Act VI
```

Every stage you have met so far is on that list. One thing about it is *not* settled by anything you have seen: a mutation and a validation both fired on that Pod, and nothing told you **which of the two ran first.** Hold the question — the answer is the whole last section of this lesson.

### A rule nobody built in

`ValidatingAdmissionPolicy` puts your predicate on that chain. It is two objects: a **policy**, which is one or more **CEL** (Common Expression Language) expressions and the resources they apply to, and a **binding**, which says where the policy is in force. Each carries a selector and they are easy to confuse, so separate them now: the policy's `matchConstraints` says what kinds of object the expression is even *valid for*; the binding's `matchResources` says *where it is switched on*.

Two objects, not one. Sit with why before reading on — lesson 03's three verbs are the clue, and you will measure the reason a few sections down.

```bash
kubectl create ns vaptest
kubectl apply -f - <<'EOF'
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata: {name: no-latest}
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE","UPDATE"]
      resources: ["pods"]
  validations:
  - expression: "object.spec.containers.all(c, !c.image.endsWith(':latest'))"
    message: "images must be pinned to a tag other than :latest"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata: {name: no-latest-binding}
spec:
  policyName: no-latest
  validationActions: ["Deny"]
  matchResources:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: vaptest}
EOF
sleep 5
kubectl run bad --image=nginx:latest -n vaptest --restart=Never
```

```
The pods "bad" is invalid: : ValidatingAdmissionPolicy 'no-latest' with binding
'no-latest-binding' denied request: images must be pinned to a tag other than :latest
```

Four things you just typed deserve a word before you go on.

`validationActions: ["Deny"]` is what to do when the expression comes back false. There are three of them, and which three is the answer to the question in the paragraph above.

`namespaceSelector` matches on namespace *labels*, and `kubernetes.io/metadata.name` is a label the API server maintains on every namespace holding that namespace's own name — lesson 03 saw it sitting in `based`'s labels without comment. It is how you scope a binding to exactly one namespace without labelling anything yourself.

`failurePolicy: Fail` is **not** about a service being down. There is no service; the expression is compiled into the API server. It governs what happens if the expression itself *errors* — a missing field, a type mismatch — and `Fail` means an erroring rule denies the request. Keep hold of that, because some odd punctuation in the next section depends on it.

And the `sleep 5` is not padding. The API server compiles policies and caches the compiled form, so a policy is not in force the instant `apply` returns. Change one, test it immediately, and you will measure the old one.

Now read the expression, because CEL is small and this is most of it. `object` is the thing being admitted. `.all(c, ...)` is a quantifier over a list. `!c.image.endsWith(':latest')` is the predicate. That is the whole rule, and it is answering prediction (a): none of RBAC, namespace labels, or the kernel could hold it, because **RBAC's input is a name and a verb, a namespace label is a single value from a fixed vocabulary, and the kernel never sees a manifest at all.** What this rule needs is *the object*, and admission is the first and only stage that has one.

### The comparison RBAC could not make

Now prediction (b), which is Act IX's dangling thread pulled straight. Its lesson 06 argued that "an owner may delete their own pod" is inexpressible in RBAC **because ownership is a relation** — the rule has to compare a field of the requester against a field of the thing requested, and a rule that lists names can never compare anything.

Add a second validation to the same policy:

```bash
kubectl apply -f - <<'EOF'
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata: {name: no-latest}
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE","UPDATE"]
      resources: ["pods"]
  validations:
  - expression: "object.spec.containers.all(c, !c.image.endsWith(':latest'))"
    message: "images must be pinned to a tag other than :latest"
  - expression: "object.metadata.?labels[?'owner'].orValue('') == request.userInfo.username"
    messageExpression: "'label owner must equal ' + request.userInfo.username"
EOF
sleep 5
kubectl run ok1 --image=busybox:1.36 -n vaptest --restart=Never \
  --labels=owner=nobody --command -- sh -c 'echo hi'
```

```
The pods "ok1" is invalid: : ValidatingAdmissionPolicy 'no-latest' with binding
'no-latest-binding' denied request: label owner must equal kubernetes-admin
```

**There it is.** A rule that compares a field of the object against the identity of the caller, evaluated on every write, refusing before anything exists. That is the comparison Act IX proved a Role could not make — and the reason is a difference in *inputs*, not in cleverness. RBAC is handed a subject, a verb, a resource and a namespace. Admission is handed **the entire object and the entire requester**: `request.userInfo` carries the username and the groups Act IX watched the authenticator produce, plus a field called `extra` that Act IX never saw an authenticator fill in — worth asking later what would.

Now read what you actually enforced, because it is narrower than Act IX's rule. This fires on `CREATE` and `UPDATE`, and it compares a label **the requester typed themselves** against their own username: it enforces *label your own Pods honestly*. Act IX's rule was about **deleting** a Pod whose `owner` label somebody else wrote. Which puts a sharp question in front of you, and you now have the vocabulary for it: on a `DELETE` there is no new object at all, so what would `object` even be bound to? A rule about touching someone else's Pod has to be handed the *old* one instead — and that is a door this lesson leaves shut.

Note `messageExpression` rather than `message`: the refusal is itself computed, so it can tell the caller what it expected. And the odd punctuation — `object.metadata.?labels[?'owner'].orValue('')` — is CEL's optional chaining, which exists because a Pod with no labels at all must not make the expression *error*; it must make it return `''` and compare cleanly. Write it the naive way and a label-less Pod gets you `no such key: labels`, which under the `failurePolicy: Fail` you set at the top becomes a **denial** — so the rule would start refusing Pods it was never about, for a reason the message does not explain. That is the most common way a policy misbehaves.

The conforming Pod, for completeness:

```bash
kubectl run ok2 --image=busybox:1.36 -n vaptest --restart=Never \
  --labels=owner=kubernetes-admin --command -- sh -c 'echo hi'
```

```
pod/ok2 created
```

(`kubernetes-admin` is who *you* are — `kubectl auth whoami` if you want to see the certificate identity Act VIII built.)

### And the gap that is still a gap

Act IX was careful about something, and it is worth going back for. It gave **two different** reasons RBAC could not express certain rules, and insisted the difference mattered: a relation needs a *comparison*, which is a limit of the rule language; but "during an incident" fails for a blunter reason — the hour of the day is **never passed in**. That one, it said, "cannot be closed by language at all."

You now have a much richer language. Test the claim:

```bash
kubectl apply -f - <<'EOF'
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata: {name: office-hours}
spec:
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE"]
      resources: ["pods"]
  validations:
  - expression: "timestamp(now()).getHours() < 17"
    message: "no deploys after 5pm"
EOF
```

```
The ValidatingAdmissionPolicy "office-hours" is invalid: spec.validations[0].expression:
Invalid value: "timestamp(now()).getHours() < 17": compilation failed:
ERROR: <input>:1:14: undeclared reference to 'now' (in container '')
 | timestamp(now()).getHours() < 17
 | .............^
```

**There is no clock.** The language got dramatically richer and this gap did not move an inch, exactly as predicted — and the refusal is not even a policy verdict, it is a *compile* error at the moment you create the policy, which is the cheapest possible place to find out.

This is not an oversight either. CEL here is deliberately **deterministic and total**: no clock, no network, no filesystem, no unbounded loops. It has to be, because it runs synchronously inside the API server on every matching write, and an expression that could hang or could return different answers for the same input would make the control plane's latency and behaviour unpredictable. The properties that make a policy language safe to put in that position are exactly the properties that stop it from knowing what time it is.

So Act IX's distinction survives contact with the best available tool: **a richer language closes the syntax gap and cannot touch the interface gap.** If a decision genuinely needs to know whether an incident is open, something has to *tell* the decision point — which means a different mechanism, with a network call in it, and everything that follows from that.

### Three dispositions, and why there are two objects

Here is the reason for the split, and it is measurable. Leave the policy exactly as it is — do not touch a line of it — and add a *second* binding, pointing at a second namespace, with a different disposition:

```bash
kubectl create ns vapwarn
kubectl apply -f - <<'EOF'
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata: {name: no-latest-warn}
spec:
  policyName: no-latest
  validationActions: ["Warn"]
  matchResources:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: vapwarn}
EOF
sleep 12
kubectl run warned --image=nginx:latest -n vapwarn --restart=Never
```

```
Warning: Validation failed for ValidatingAdmissionPolicy 'no-latest' with binding 'no-latest-warn': images must be pinned to a tag other than :latest
Warning: Validation failed for ValidatingAdmissionPolicy 'no-latest' with binding 'no-latest-warn': label owner must equal kubernetes-admin
pod/warned created
```

**One rule, two namespaces, two answers.** The same expression that refused `bad` in `vaptest` merely complains in `vapwarn`, and it was written once. That is what splitting policy from binding buys, and it is lesson 03's point about migration being the hard part — now for a rule *you* wrote. You can bind a new rule in `Warn` mode everywhere, read the complaints, fix the manifests, and only then add the binding that denies.

`Deny`, `Warn`, `Audit` — the same three verbs as PSA's labels, for the same reason, and each failing validation warns separately so you get the full list rather than the first problem.

### When CEL is not enough

CEL cannot call anything. So a rule that needs to ask a registry whether an image exists, or a ticket system whether a change is approved, or any question whose answer is not already inside the object, is out of reach — which is what an **admission webhook** is for. The API server makes an HTTPS request to a service you run, sends it the object, and believes the answer.

You are going to build one, and it will use everything Act VIII gave you. Start with the certificate, because the webhook's identity is the whole trust story:

```bash
mkdir -p /tmp/wh && cd /tmp/wh
openssl req -x509 -newkey rsa:2048 -nodes -days 30 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=imagegate.default.svc" \
  -addext "subjectAltName=DNS:imagegate.default.svc"
openssl x509 -in tls.crt -noout -subject -ext subjectAltName
```

```
subject=CN=imagegate.default.svc
X509v3 Subject Alternative Name:
    DNS:imagegate.default.svc
```

(On macOS this needs the Homebrew OpenSSL that Act VIII already made a prerequisite. Apple's `/usr/bin/openssl` is LibreSSL and answers `unknown option -ext`.)

The SAN has to be the Service's in-cluster DNS name, because the API server will connect to `https://imagegate.default.svc` and check the name the way Act VIII's `s_client` did — and Act V taught you where that name comes from.

Then the server. Forty lines of Python, and the shape is worth reading rather than skimming: it receives an `AdmissionReview`, and it must send one back containing the **same `uid`** and a boolean.

```bash
cat > server.py <<'PY'
import json, ssl
from http.server import BaseHTTPRequestHandler, HTTPServer

ALLOWED = ("registry.internal/", "busybox")

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        review = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        req = review["request"]
        bad = [c["image"] for c in req["object"]["spec"]["containers"]
               if not c["image"].startswith(ALLOWED)]
        resp = {"apiVersion": review["apiVersion"], "kind": "AdmissionReview",
                "response": {"uid": req["uid"], "allowed": not bad,
                             "status": {"message":
                                "image(s) not from an allowed registry: " + ", ".join(bad)}}}
        body = json.dumps(resp).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain("/certs/tls.crt", "/certs/tls.key")
s = HTTPServer(("0.0.0.0", 8443), H)
s.socket = ctx.wrap_socket(s.socket, server_side=True)
s.serve_forever()
PY
kubectl create secret tls webhook-cert --cert=tls.crt --key=tls.key
kubectl create configmap webhook-code --from-file=server.py
```

The `uid` echo is not ceremony. The API server sends a unique id per request and matches the response to it, which is what stops a slow or confused webhook from answering the wrong question. That is the same *shape* as the query ID in Act II's DNS lesson, minus the adversary: there the id had to be hard to guess because the channel was unauthenticated UDP, and here the channel is one authenticated TLS connection, so the id is doing correlation only.

Run it, with the certificate mounted from the Secret and the code from the ConfigMap:

```bash
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: {name: imagegate}
spec:
  replicas: 1
  selector: {matchLabels: {app: imagegate}}
  template:
    metadata: {labels: {app: imagegate}}
    spec:
      containers:
      - name: c
        image: python:3.12-alpine
        command: ["python3","/code/server.py"]
        ports: [{containerPort: 8443}]
        readinessProbe: {tcpSocket: {port: 8443}}
        volumeMounts:
        - {name: code, mountPath: /code}
        - {name: certs, mountPath: /certs}
      volumes:
      - {name: code, configMap: {name: webhook-code}}
      - {name: certs, secret: {secretName: webhook-cert}}
---
apiVersion: v1
kind: Service
metadata: {name: imagegate}
spec:
  selector: {app: imagegate}
  ports: [{port: 443, targetPort: 8443}]
EOF
kubectl rollout status deployment imagegate
```

The `readinessProbe` is load-bearing rather than decoration. Without it the EndpointSlice is marked ready the instant the container *process* starts — which is before `server.py` has finished binding 8443 — so `rollout status` returns, and your very first Pod gets a `connection refused` from a webhook that is running but not listening. That is Act V's endpoints doing exactly what Act V said they do, and it is worth knowing now rather than mistaking it for the failure mode two sections down.

And now register it, which is where Act VIII's trust anchor reappears under a new name:

```bash
kubectl create ns whtest
kubectl label ns whtest webhook=on
CA=$(base64 < /tmp/wh/tls.crt | tr -d '\n')
cat <<EOF | kubectl apply -f -
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata: {name: registry-gate}
webhooks:
- name: gate.example.com
  admissionReviewVersions: ["v1"]
  sideEffects: None
  failurePolicy: Fail
  namespaceSelector:
    matchLabels: {webhook: "on"}
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
  clientConfig:
    service: {name: imagegate, namespace: default, port: 443, path: "/validate"}
    caBundle: $CA
EOF
```

**`caBundle` is `-CAfile`.** It is the one certificate the API server will trust for this connection, base64'd into the object — Act VIII lesson 05's trust anchor, chosen per webhook, with no public CA involved anywhere. A self-signed certificate is entirely appropriate here precisely because the relying party is told exactly which one to accept.

Three smaller fields, since you typed them and they were not explained. `admissionReviewVersions: ["v1"]` is which wire format your server understands; there is only one that matters. `path: "/validate"` is the URL the API server will POST to — and note that the server above answers `do_POST` on *any* path, so nothing has actually checked that these two agree; a typo there would go unnoticed until you cared. And `sideEffects: None` is a promise that calling your webhook changes nothing outside the request, which you will cash in shortly.

`failurePolicy: Fail` again — and note the seam. On a `ValidatingAdmissionPolicy` this field could not be about a service being down, because there was no service. Here there *is* one, so it means the thing you probably assumed it meant the first time. That is the subject of the section after next.

```bash
kubectl run bad --image=nginx:1.28-alpine -n whtest --restart=Never
kubectl run good --image=busybox:1.36 -n whtest --restart=Never --command -- sh -c 'echo hi'
```

```
Error from server: admission webhook "gate.example.com" denied the request: image(s) not from an allowed registry: nginx:1.28-alpine
pod/good created
```

Your code, in the write path of a Kubernetes API server, refusing an object.

Now collect on `sideEffects: None`. Ask the API server to run the whole write and then throw it away:

```bash
kubectl run dry --image=nginx:1.28-alpine -n whtest --restart=Never --dry-run=server
kubectl get pod dry -n whtest
```

```
Error from server: admission webhook "gate.example.com" denied the request: image(s) not from an allowed registry: nginx:1.28-alpine
Error from server (NotFound): pods "dry" not found
```

That is `--dry-run=client` from Act VI grown up. The client version never left your laptop and could only check syntax; this one went through authentication, authorization, mutation and your webhook, got a real verdict, and discarded the write. It is only safe because every webhook in the path promised `sideEffects: None` — a webhook that files a ticket or increments a counter and claims `None` makes every dry run in the cluster have consequences.

### What your policy actually sees

Before being pleased with it, try the same image again under a different name:

```bash
kubectl run good2 --image=docker.io/library/busybox:1.36 -n whtest --restart=Never \
  --command -- sh -c 'echo hi'
```

```
Error from server: admission webhook "gate.example.com" denied the request: image(s) not from an allowed registry: docker.io/library/busybox:1.36
```

`busybox:1.36` was allowed. `docker.io/library/busybox:1.36` — **the identical image, byte for byte** — is denied. And the reverse mistake is worse: a rule allowing `docker.io/library/` is defeated by writing `busybox`.

Nothing normalised the reference, because `spec.containers[].image` is a free-text field that only the container runtime ever fully resolves, and the runtime is four stages later. Your policy sees the string a human typed. So `busybox`, `library/busybox`, `docker.io/library/busybox` and `index.docker.io/library/busybox:1.36` are one image and four different strings, and a prefix match over them is security theatre with a config file.

Which is a specific instance of something general enough to keep: **an admission rule is only as strong as the field it reads is well-defined.** The registry-allowlist problem does have a real answer, and it is not string matching — it is pinning to a digest, which names the bytes rather than a location, and verifying a signature over those bytes. That is lesson 08.

### The measurement that decides how you run these

Prediction (c). Take the webhook away — not delete the configuration, just lose the Pod, the way a crash or a bad rollout or a full node would:

```bash
kubectl scale deployment imagegate --replicas=0
kubectl wait --for=delete pod -l app=imagegate --timeout=60s
kubectl run f1 --image=busybox:1.36 -n whtest --restart=Never --command -- sh -c 'echo hi'
```

```
Error from server (InternalError): Internal error occurred: failed calling webhook
"gate.example.com": failed to call webhook: Post
"https://imagegate.default.svc:443/validate?timeout=10s": dial tcp 10.96.46.68:443:
connect: connection refused
```

(That address is the Service's ClusterIP, so yours will differ.)

**An image on the allowlist was refused, because the thing that checks the allowlist is down.** Not just this Pod: every Pod creation matching those rules, in every namespace matching that selector, for as long as the outage lasts. A policy service in the write path is a hard dependency of the cluster's ability to run workloads, and if you scope it carelessly — `namespaceSelector: {}` and a rule matching `*` — it becomes a hard dependency of its ability to *recover*, since the Pods that would restart your webhook are themselves Pods.

Yours is not that, and it is worth seeing why. The `namespaceSelector` you wrote matches only `whtest`, and `imagegate` lives in `default` — so scaling the webhook to zero a moment ago was itself a write your own webhook was never consulted about. That is the only reason the command worked, and it was not luck.

The other choice:

```bash
kubectl patch validatingwebhookconfiguration registry-gate --type=json \
  -p '[{"op":"replace","path":"/webhooks/0/failurePolicy","value":"Ignore"}]'
sleep 6
kubectl run f2 --image=nginx:1.28-alpine -n whtest --restart=Never
```

```
pod/f2 created
```

**A forbidden image, admitted, with no error, no warning, and nothing in the object recording that the check did not run.** The policy has evaporated and the cluster looks completely healthy. Every subsequent audit that asks "is the registry policy enforced?" by reading the `ValidatingWebhookConfiguration` will say yes.

So the choice is not between a safe option and a risky one. It is: **when your policy service is down, would you rather the cluster stop working, or stop being protected?** There is no third answer, and picking `Ignore` because `Fail` caused an incident once is how policy quietly stops existing.

Two things follow, and they are the practical content of this whole section. Scope every webhook as narrowly as the rule allows — specific resources, specific operations, a `namespaceSelector` that excludes `kube-system` and your webhook's own namespace — so that `Fail` is survivable. And notice what `ValidatingAdmissionPolicy` does *not* have: no `caBundle`, no Service, no Deployment, and no *reachability* to lose. It does have a `failurePolicy` — you set one in the first section — but it governs your expression erroring, which is a bug you can reproduce on demand from the object alone, not a separate component being unreachable at 2am. A broken expression under `Fail` can still refuse every Pod in scope; the difference is that nothing outside the API server has to be alive for the *working* case to keep working. **That is the real argument for CEL over a webhook, and it is an operational argument rather than a security one.**

### Mutation, and why the order matters

Lesson 03 ended in a genuine bind. `restricted` requires four fields, so every author of every manifest in the cluster has to write them, forever, correctly. That is not a policy; it is a hope.

The mutating stage is somewhere to put the fix — *if* the order works out. `MutatingAdmissionPolicy` is CEL that returns a patch instead of a boolean. Check your cluster has it before typing the rest, because it is new:

```bash
kubectl api-resources | grep mutatingadmissionpolic
```

```
mutatingadmissionpolicies                        admissionregistration.k8s.io/v1   false        MutatingAdmissionPolicy
mutatingadmissionpolicybindings                  admissionregistration.k8s.io/v1   false        MutatingAdmissionPolicyBinding
```

It reached `admissionregistration.k8s.io/v1` in Kubernetes 1.36, and on a 1.36 server that API group has no other version at all — no `v1beta1`, no `v1alpha1`. If the command prints nothing your server is older, which it may well be: Act V's `kind create cluster` takes whatever image your `kind` binary defaults to, and that tracks the `kind` release rather than the newest Kubernetes. Read the section anyway. The measurement at the end of it is the answer to the question this lesson opened in its first section, and once you have seen it, the paragraph that follows says how to get the same proof on any version.

```bash
kubectl create ns mut
kubectl label ns mut pod-security.kubernetes.io/enforce=restricted
kubectl apply -f - <<'EOF'
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicy
metadata: {name: harden}
spec:
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE"]
      resources: ["pods"]
  failurePolicy: Fail
  reinvocationPolicy: Never
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: >
        Object{
          spec: Object.spec{
            securityContext: Object.spec.securityContext{
              runAsNonRoot: true,
              runAsUser: 1000,
              seccompProfile: Object.spec.securityContext.seccompProfile{ type: "RuntimeDefault" }
            },
            containers: object.spec.containers.map(c, Object.spec.containers{
              name: c.name,
              securityContext: Object.spec.containers.securityContext{
                allowPrivilegeEscalation: false
              }
            })
          }
        }
  - patchType: JSONPatch
    jsonPatch:
      expression: >
        object.spec.containers.size() > 0 ?
          [JSONPatch{
             op: "add",
             path: "/spec/containers/0/securityContext/capabilities",
             value: {"drop": ["ALL"]}
           }] : []
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicyBinding
metadata: {name: harden-binding}
spec:
  policyName: harden
  matchResources:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: mut}
EOF
sleep 10
```

Two things in there were never introduced, and one of them is genuinely strange.

`reinvocationPolicy: Never` says: run my patches once. `IfNeeded` re-runs them if some later mutation changed the object afterwards — which opens a real question about ordering *between* mutators that this lesson does not go into.

`patchType: ApplyConfiguration` returns a **partial object**, and CEL needs a type for a partial object. The type's name is *the path to the field it is a partial of*: `Object.spec.securityContext{...}` means "a partial `spec.securityContext`", and the outermost one is bare `Object{...}`. Inside a `.map()` over a list, the element's type is still named by the **list's** path — `Object.spec.containers{...}`, for one container — which reads wrong and is correct.

And here is the part worth knowing before you get it wrong: **none of those type names is checked when you `apply`.** Misspell one as `Object.spec.securityContexts` and the policy is accepted, stored, and then fails on every matching write with `type mismatch: unexpected type name "Object.spec.securityContexts", expected "Object.spec.securityContext"`. Misspell a *field* inside a correct type and you get `field not declared in schema`, again per write. What `apply` checks is the CEL grammar and the function environment — `nosuchfunc(1)` really is rejected on the spot — not the partial-object vocabulary. Keep that; it comes back at the end of this section.

Now the test that matters — a completely naive `kubectl run`, with no security fields at all, into a namespace that enforces `restricted`:

```bash
kubectl run plain --image=busybox:1.36 -n mut --restart=Never --command -- \
  sh -c 'id -u; grep -E "^CapEff|NoNewPrivs|Seccomp:" /proc/self/status'
sleep 8
kubectl logs -n mut plain
```

```
pod/plain created
1000
CapEff:	0000000000000000
NoNewPrivs:	1
Seccomp:	2
```

**Read all five lines.** It was created — in a `restricted` namespace, from a command that mentioned nothing. And the process it produced runs as uid 1000, holds zero capabilities, has `NoNewPrivs` set, and has a seccomp filter attached. Every measurement from lessons 01 and 02, with the author of the manifest never having heard of any of them.

```bash
kubectl get pod plain -n mut \
  -o jsonpath='{.spec.securityContext}{"\n"}{.spec.containers[0].securityContext}{"\n"}'
```

```
{"runAsNonRoot":true,"runAsUser":1000,"seccompProfile":{"type":"RuntimeDefault"}}
{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}
```

The stored object *has* the fields — and there is the answer to the question left open in the first section. **Mutation ran first.** It cannot have been the other way round: lesson 03 measured a 403 for exactly this Pod in exactly this kind of namespace, so had PSA gone first there would be nothing here to inspect. Mutation ran, PSA then examined an object that already complied, and both were right. **That ordering is not bookkeeping — it is what makes "secure by default" implementable at all**, because the only way to be safe by default is for something to write the default in before anything checks it.

(If your server is below 1.36, the same proof is on your bench already. A `MutatingWebhookConfiguration` — same API group, old enough that every cluster this course has used has it — pointed at the webhook you built two sections ago, returning these four fields as a base64'd JSON Patch instead of a verdict, gets you the identical result in the identical namespace. It also puts your own code in the mutating stage, the way you already put it in the validating one.)

One detail earned by failing at it, and the failure teaches twice. The `capabilities.drop` list needs a `JSONPatch` rather than the `ApplyConfiguration` used for everything else. Try it the tidy way — the same container mutation, with `capabilities` moved up inside the `ApplyConfiguration` and the `JSONPatch` gone:

```bash
kubectl apply -f - <<'EOF'
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicy
metadata: {name: harden2}
spec:
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE"]
      resources: ["pods"]
  failurePolicy: Fail
  reinvocationPolicy: Never
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: >
        Object{
          spec: Object.spec{
            containers: object.spec.containers.map(c, Object.spec.containers{
              name: c.name,
              securityContext: Object.spec.containers.securityContext{
                allowPrivilegeEscalation: false,
                capabilities: Object.spec.containers.securityContext.capabilities{
                  drop: ["ALL"]
                }
              }
            })
          }
        }
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicyBinding
metadata: {name: harden2-binding}
spec:
  policyName: harden2
  matchResources:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: mut}
EOF
sleep 10
kubectl run p2 --image=busybox:1.36 -n mut --restart=Never --command -- sh -c 'echo hi'
```

```
mutatingadmissionpolicy.admissionregistration.k8s.io/harden2 created
mutatingadmissionpolicybinding.admissionregistration.k8s.io/harden2-binding created
The pods "p2" is invalid: : policy 'harden2' with binding 'harden2-binding' denied request:
error applying patch: invalid ApplyConfiguration: may not mutate atomic arrays, maps or
structs: .spec.containers[0].securityContext.capabilities.drop
```

**The policy was accepted and the Pod was not.** Take it back out before continuing, or every Pod created in `mut` from here on will fail the same way:

```bash
kubectl delete mutatingadmissionpolicybinding harden2-binding
kubectl delete mutatingadmissionpolicy harden2
sleep 5
```

The `sleep 5` is the compile cache from the first section, seen from the other side: for a couple of seconds after the delete, a policy that no longer exists is still refusing Pods.

Hold that against `now()` from three sections back. That was a **compile** error at policy-creation time, and this lesson called it the cheapest possible place to find out. This one is not that. The expression compiles, the policy is stored, and the patch fails per-write — so a broken mutator ships silently and then, under `failurePolicy: Fail`, refuses every Pod creation in the namespace it is bound to. Cheap failure is a real property of CEL policies and it is a *partial* one; the line between "caught at `apply`" and "caught on every write from now on" is the line between a rollout you can be confident about and an outage.

As for why: `drop` is marked **atomic** in the API's schema, which means the API server treats that list as one indivisible value and a merge-style patch may not reach inside it. Look again at what the `JSONPatch` in `harden` actually does — it never mentions `drop` as a list at all. It writes the entire `capabilities` object in a single `add` operation, so there is nothing for the server to merge into an atomic field. `ApplyConfiguration` is the right tool for fields that merge, `JSONPatch` is the escape hatch for the ones that do not, and the schema decides which is which, not you.

Two things about that patch are quietly load-bearing. It only lands because the `ApplyConfiguration` mutation ran first and created the `securityContext` for it to hang off — swap the order of the two mutations and every write that does not *already* carry a container `securityContext` fails with `add operation does not apply: doc is missing path`, which is every naive Pod this section is about.

And the path is `/spec/containers/0`, which hardens the first container and no others. Give the Pod a sidecar:

```
Error from server (Forbidden): error when creating "STDIN": pods "sidecar" is forbidden:
violates PodSecurity "restricted:latest": unrestricted capabilities (container "side" must
set securityContext.capabilities.drop=["ALL"])
```

PSA names exactly the container the patch never reached. An atomic field forces a per-container patch, so a real version of this generates one operation per container — and until it does, "secure by default" holds for container zero only.

### What mutation cannot do

It is tempting to read `harden` as supplying *defaults* — filling in blanks, deferring to an author who has an opinion. Test that, with a Pod that explicitly asks for root:

```bash
kubectl apply -n mut -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: root0}
spec:
  securityContext: {runAsUser: 0}
  restartPolicy: Never
  containers:
  - {name: c, image: busybox:1.36, command: ["sh","-c","id -u"]}
EOF
sleep 6
kubectl get pod root0 -n mut -o jsonpath='{.spec.securityContext}{"\n"}'
kubectl logs -n mut root0
```

```
pod/root0 created
{"runAsNonRoot":true,"runAsUser":1000,"seccompProfile":{"type":"RuntimeDefault"}}
1000
```

**It was not refused. It was overruled, and silently.** An `ApplyConfiguration` expression that names a field with a literal value *sets* that field — it never asks whether the author already wrote something there. So for every field it names, `harden` is a **floor, not a default**, and nothing in the response tells the author their `0` was discarded. Making it a genuine default means testing for absence inside the expression first, and then deciding which of you ought to win — a policy decision the mechanism will not make for you.

Now try a field the policy does not name at all:

```bash
kubectl apply -n mut -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: priv}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","sleep 5"]
    securityContext: {privileged: true}
EOF
```

```
The Pod "priv" is invalid: spec.containers[0].securityContext: Invalid value:
{"Capabilities":{"Add":null,"Drop":["ALL"]},"Privileged":true, ... ,"AllowPrivilegeEscalation":false, ... }:
cannot set `allowPrivilegeEscalation` to false and `privileged` to true
```

**The evidence is in the dump, not in the sentence.** `"Drop":["ALL"]` and `"AllowPrivilegeEscalation":false` are `harden`'s two mutations, sitting in the same object as the author's `"Privileged":true`. (The dump prints Go field names, capitalised, while the message below it uses the JSON ones — same fields, two spellings, and nothing in Kubernetes is consistent about which you get.)

Read *who* refused it, because it is not who you would expect. No policy is named, no binding, no mention of PodSecurity or a namespace label — this is not a policy verdict at all. It is **object validation**, the one stage in the chain you had never seen refuse anything, and the contradiction it found is one your own mutation created.

And notice who did *not* speak. This Pod is privileged, in a namespace labelled `enforce=restricted`, which lesson 03 measured a 403 for — and PodSecurity never got a word in. Object validation reached it first. That is the second arrow in the chain, measured the same way you measured the first one.

Which is the honest limit, and it is sharper than "defaults": **mutation can supply a field or overrule one, but it can never refuse on purpose.** The only way a mutator says no is by breaking — which is exactly what you watched `harden2` do a moment ago, and it refused Pods it had no opinion about whatsoever. Deliberate refusal belongs to a later stage, object validation here and PSA elsewhere, and that is why a cluster needs both kinds of stage rather than a sufficiently clever mutator.

### So why is later better?

Act IX asked it and this is the answer, now that all the pieces are on the table.

Not because later is inherently better — it is not; every stage in this act's chain is a real choice with real costs. It is because **each stage knows more than the one before it, and admission is the last moment at which refusing costs nothing.**

RBAC could not hold these rules because it is handed four strings. The kernel could not hold them because it never sees a manifest — by the time a syscall happens, the Pod is scheduled, the image is pulled, the container exists, and refusing means killing something that is already running. Admission sits at exactly the point where the whole object and the whole requester are known and **nothing has happened yet**: nothing scheduled, nothing pulled, nothing started, no state to unwind. That is a genuinely privileged position, and it is the only stage that has it.

The price is equally specific, and you have now measured all of it. Admission sees the object as *written*, so it cannot know that `busybox` and `docker.io/library/busybox` are one image. It cannot know what time it is. It cannot know what the process will actually do. And if you extend it with a webhook to learn things CEL cannot, you have put a service you operate in the write path of your control plane, and its two failure modes are "the cluster stops" and "the policy silently does not exist."

**Cleanup:**

```bash
kubectl delete validatingwebhookconfiguration registry-gate --ignore-not-found
kubectl delete validatingadmissionpolicybinding no-latest-binding no-latest-warn --ignore-not-found
kubectl delete validatingadmissionpolicy no-latest --ignore-not-found
kubectl delete mutatingadmissionpolicybinding harden-binding harden2-binding --ignore-not-found
kubectl delete mutatingadmissionpolicy harden harden2 --ignore-not-found
kubectl delete deployment imagegate --ignore-not-found
kubectl delete svc imagegate --ignore-not-found
kubectl delete secret webhook-cert --ignore-not-found
kubectl delete configmap webhook-code --ignore-not-found
kubectl delete ns mutshow vaptest vapwarn whtest mut --ignore-not-found
cd "$HOME" && rm -rf /tmp/wh
rm -f "${TMPDIR:-/tmp}/act10.kubeconfig"
```

> **Check yourself —** a colleague's admission webhook enforces "every Pod must have a `team` label". It is scoped to all namespaces, all resources, `operations: ["*"]`, and `failurePolicy: Fail`. It has worked perfectly for a year. Describe the outage.

<details>
<summary>Answer</summary>

The webhook's own Pod needs to be created by something, and creating a Pod is a write that matches the webhook's own rules.

While the webhook is running, everything is fine — including, confusingly, restarting the webhook, because a rolling update starts the new Pod while the old one is still answering. So the configuration is not merely unsafe, it is unsafe in a way that a year of ordinary operation cannot reveal.

The outage is any event that takes all replicas down at once: the node they are on fails, a cluster upgrade drains them together, someone scales to zero, an image pull starts failing. Now the API server needs to call the webhook to admit the Pod that would *be* the webhook, the call fails, `Fail` means deny, and the cluster cannot create the one thing that would fix it. Recovery is manual surgery on the `ValidatingWebhookConfiguration` — which, note, is itself a write, so the object had better not be in the webhook's own rules.

`operations: ["*"]` and all resources makes it worse in a way worth naming separately: the webhook is now consulted for writes to Leases, Events, EndpointSlices and every other high-frequency object in the cluster. That is a latency tax on everything, and it means an overloaded webhook degrades the control plane rather than just the workloads it was meant to police.

The fixes are all narrowing. Scope `rules` to the resources and operations the rule is actually about. Add a `namespaceSelector` that excludes `kube-system` and the webhook's own namespace. Run more than one replica, spread across nodes, with a PodDisruptionBudget. And be able to state, before shipping it, which of "the cluster stops" and "the policy stops" you have chosen — because `failurePolicy` is that choice and it has no third option.

</details>

<!-- figure -->
```
   THE CHAIN, ALL OF IT ALREADY OBSERVED

     authn ......... Act IX: 401, no name
     authz ......... Act IX: 403, names user+verb+resource
     decode ........ L03: "strict decoding error: unknown field"
                     -- L03 said it: BEFORE any admission plugin
     MUTATING ...... the SA controller mounted a token volume you
                     never asked for and never installed; then a
                     LimitRange you DID install filled in resources
     objectvalid ... "cannot set `allowPrivilegeEscalation` to false
                     and `privileged` to true" -- not a policy
                     verdict. a refusal CAUSED BY the mutation
                     upstream of it.
     VALIDATING .... L03: "violates PodSecurity"
     persist ....... Act VI
   mutation runs BEFORE validation -- proved by a bare kubectl run
   being CREATED in an enforce=restricted namespace, where L03
   measured a 403. that ordering is what makes "secure by default"
   implementable at all.

   WHAT ADMISSION HAS THAT NOTHING ELSE DOES
     RBAC is handed 4 strings. the kernel never sees a manifest.
     admission is handed THE WHOLE OBJECT + THE WHOLE REQUESTER
     at the last moment when NOTHING HAS HAPPENED YET.
     nothing scheduled/pulled/started. no state to unwind.
     -> that is the entire answer to "why is later better".

   THE RULE ACT IX PROVED RBAC COULD NOT WRITE
     object.metadata.?labels[?'owner'].orValue('')
        == request.userInfo.username
     -> "label owner must equal kubernetes-admin"
     the comparison a name-listing rule can never make.
     (optional chaining because a Pod with no labels must
      return '' and COMPARE, not ERROR -- an erroring expression
      under failurePolicy: Fail is a DENIAL, so the rule starts
      refusing Pods it was never about.)

   AND THE GAP THAT DID NOT MOVE
     timestamp(now())  ->  "undeclared reference to 'now'"
     rejected at POLICY CREATION, not at admission.
     CEL is deliberately deterministic + total: no clock, no
     network, no unbounded loops -- because it runs inside the
     apiserver on every write. the properties that make it safe
     there are the properties that stop it knowing the time.
     => Act IX was right: a richer LANGUAGE closes the syntax
        gap and cannot touch the INTERFACE gap.

   WEBHOOKS: YOUR CODE IN THE WRITE PATH
     caBundle IS Act VIII's -CAfile, base64'd. self-signed is
     CORRECT here: the relying party is told which one to trust.
     SAN must be <svc>.<ns>.svc. echo request.uid back or the
     apiserver cannot match the answer to the question.
     sideEffects: None is what makes --dry-run=server safe.

   AND THE FIELD IT READS IS NOT WELL-DEFINED
     busybox:1.36 ................ ALLOWED
     docker.io/library/busybox:1.36  DENIED   <- same bytes.
     nothing normalises .image. your policy sees a typed string.
     the real fix is a DIGEST + a signature. that is lessons 08/08b.

   THE FAILURE MODE, MEASURED BOTH WAYS
     webhook scaled to 0:
       failurePolicy: Fail   -> "connection refused", an ALLOWED
                                image is REFUSED. no Pods created.
       failurePolicy: Ignore -> "pod/f2 created". a FORBIDDEN
                                image admitted. no error, no
                                warning, nothing in the object.
     so: when your policy service is down, would you rather the
     cluster STOP WORKING or STOP BEING PROTECTED? no third option.
     VAP has no such pair: compiled in, nothing separate to be
     down. its failurePolicy governs YOUR EXPRESSION ERRORING,
     not reachability -- reproducible from the object alone.
     that is the real argument for CEL, and it is OPERATIONAL.

   MUTATION CLOSES LESSON 03'S BIND
     a bare kubectl run, in an enforce=restricted namespace:
       created. uid 1000 / CapEff 0 / NoNewPrivs 1 / Seccomp 2
     author wrote nothing. gotcha: capabilities.drop is ATOMIC,
     so ApplyConfiguration refuses it -> JSONPatch. and that one
     compiles fine and fails PER WRITE, unlike now(). cheap
     failure is real and PARTIAL.
     and the limit: mutation can SUPPLY a field or OVERRULE one
     -- runAsUser: 0 came back as 1000, silently, so this is a
     FLOOR not a default -- but it can never REFUSE. refusing is
     a later stage's job. you need both.
```

> **You understand this when you can** name the stages a write passes through, with a refusal or a
> mutation you watched at each; prove from one bare `kubectl run` that mutating admission has
> always rewritten your Pods; say what makes a rule checkable, and why that rules out RBAC,
> namespace labels and the kernel; state both failure modes of a webhook that is down, and which
> is invisible; and say why `runAsUser: 0` proves a mutator is a floor, not a default, and can
> never refuse.

**Which raises:** you have now written a policy engine — a certificate, a server, a Service, a registration object, and a `failurePolicy` decision you had to reason about for an entire section. For one rule about image prefixes, which you then proved was defeated by typing the same image name differently. Nobody runs a cluster this way, and the reason is not that the mechanism is wrong; the mechanism is exactly right and is what everything else is built on. What nobody wants to hand-write is the *hundred rules*, the library of them somebody else already debugged, the reporting on what would have failed, and the operational hardening of a service that can take the cluster down. **So what do the two projects that own this space actually add on top of what you just built — and does either of them give you something CEL genuinely cannot express?**

---

↑ **[Act X overview](README.md)** · Prev: **[A default that refuses](03-a-default-that-refuses.md)** · Next: *Policy as a product* — not yet written →
