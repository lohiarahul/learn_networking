# Policy as a product

Lesson 04 ended with an inventory of what you had built and a complaint about it. A certificate, a server, a Service, a registration object, and a `failurePolicy` decision that took a whole section to reason about — for **one rule**, which you then proved was defeated by writing the same image name a different way.

The complaint was not that the mechanism is wrong. The mechanism is exactly right, and everything in this lesson is built on it. The complaint was that between "I can express one rule" and "my cluster has a policy" there is a list of things nobody wants to hand-write:

- **the hundred rules themselves**, and someone else's debugging of them
- **the narrowing** — `rules`, `namespaceSelector`, excluding `kube-system` and the webhook's own namespace, which lesson 04's Check-yourself made you work out and then left you to remember
- **the reporting** — a list of what *would* have failed, which is the only way anyone turns a policy on in a cluster that already has Pods in it
- **the operational hardening** of a service that, at `failurePolicy: Fail`, can stop the cluster

Two projects own this space: **OPA Gatekeeper** and **Kyverno**. This lesson installs both, writes the same rule in each, and then goes looking for the thing lesson 04 said CEL could not do.

> **Predict first —** three commitments. **(a)** Both engines are, underneath, admission webhooks. Given what you measured in lesson 04 by scaling your own webhook to zero, what have you signed up for the moment you install one — and can a product make that choice go away? **(b)** You install an engine and create **no policies at all**. What is its webhook registered to intercept? Write down an answer before you look; there are three plausible ones and they have very different consequences. **(c)** Lesson 04 proved CEL has no clock and cannot read another object. Will either product close either gap — and if one does, will it be because the *language* got richer, or because something else changed? Act IX gave you the vocabulary for this exact distinction; use it.

### Installing one, and reading what it installed

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

kubectl apply --server-side \
  -f https://github.com/kyverno/kyverno/releases/download/v1.19.0/install.yaml
```

`--server-side` is not a style preference, and the reason is a fact about `kubectl apply` rather than about Kyverno. A client-side apply records the document you sent in a `kubectl.kubernetes.io/last-applied-configuration` annotation so it can diff against it next time — and annotations are capped at 262144 bytes, while the largest CRD in that file is **1.4 MB**. Server-side apply keeps the same bookkeeping in `managedFields` on the server instead, which is the mechanism Act VII met when two controllers fought over one field.

Then wait for it, because the next measurement is only interesting once it is up:

```bash
kubectl wait --for=condition=Available deploy --all -n kyverno --timeout=180s
kubectl get pods -n kyverno
```

```
NAME                                             READY   STATUS    RESTARTS   AGE
kyverno-admission-controller-bc5cc9957-92fw5     1/1     Running   0          103s
kyverno-background-controller-7f8446f957-xdpg4   1/1     Running   0          103s
kyverno-cleanup-controller-6cfb8f79c4-t6tkg      1/1     Running   0          103s
kyverno-reports-controller-54f98468f7-974lp      1/1     Running   0          103s
```

**Four controllers**, and read their names as a table of contents for this lesson. You built one of these in lesson 04 — the admission controller. The other three are doing things you have not done at all yet, and one of them is doing something admission *cannot* do.

### A registration object with nothing in it

Prediction (b). No policies exist. Look at what got registered:

```bash
kubectl get validatingwebhookconfiguration | grep -E "NAME|kyverno-resource"
```

```
NAME                                            WEBHOOKS   AGE
kyverno-resource-validating-webhook-cfg         0          33s
```

**Zero.** The registration object exists and intercepts nothing.

Sit with that for a second, because the two answers you probably wrote down are both worse. If it registered for everything, you would have installed lesson 04's Check-yourself scenario — a webhook consulted for every Lease, Event and EndpointSlice in the cluster — as a *side effect of an install*. If it registered for nothing permanently, it could never enforce anything. So the object has to be **rewritten as policies come and go**, which means something in that namespace is reconciling a `ValidatingWebhookConfiguration` against the set of policies that exist.

That is Act VI's loop, pointed at the object you hand-wrote in lesson 04.

Now give it the rule. Kyverno's current API is deliberately shaped like the `ValidatingAdmissionPolicy` you already wrote — same `matchConstraints`, same `validationActions`, same CEL — so this should read as almost nothing new:

```bash
kubectl create ns kyvtest
kubectl apply -f - <<'EOF'
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: no-latest
spec:
  validationActions: ["Deny"]
  matchConstraints:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: kyvtest}
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE","UPDATE"]
      resources: ["pods"]
  validations:
  - expression: "object.spec.containers.all(c, !c.image.endsWith(':latest'))"
    message: "image must not use the :latest tag"
EOF
sleep 10
kubectl get validatingwebhookconfiguration kyverno-resource-validating-webhook-cfg \
  -o jsonpath='{range .webhooks[*]}{.name}{"  failurePolicy="}{.failurePolicy}{"  timeout="}{.timeoutSeconds}{"\n"}{end}'
```

```
vpol.validate.kyverno.svc-fail  failurePolicy=Fail  timeout=10
```

The expression is character-for-character the one you wrote by hand in lesson 04. What is new is everything around it — so read the whole webhook the engine derived from your one policy:

```bash
kubectl get validatingwebhookconfiguration kyverno-resource-validating-webhook-cfg -o json \
  | python3 -c "
import json, sys
for w in json.load(sys.stdin)['webhooks']:
    for r in w['rules']:
        print('rule:  ', r['apiGroups'], r['operations'], r['resources'])
    for k, v in w['namespaceSelector'].items():
        print('nsSel: ', k, '=', json.dumps(v))
"
```

```
rule:   [''] ['CREATE', 'UPDATE'] ['pods']
rule:   ['apps'] ['CREATE', 'UPDATE'] ['daemonsets', 'deployments', 'replicasets', 'statefulsets']
rule:   ['batch'] ['CREATE', 'UPDATE'] ['cronjobs']
rule:   ['batch'] ['CREATE', 'UPDATE'] ['jobs']
nsSel:  matchExpressions = [{"key": "kubernetes.io/metadata.name", "operator": "NotIn", "values": ["kube-system"]}, {"key": "kubernetes.io/metadata.name", "operator": "NotIn", "values": ["kyverno"]}]
nsSel:  matchLabels = {"kubernetes.io/metadata.name": "kyvtest"}
```

Read that against lesson 04's Check-yourself answer, which told you the fixes were: scope `rules` to what the rule is actually about, and add a `namespaceSelector` excluding `kube-system` and the webhook's own namespace. **All three are there, and you wrote none of them.** Your namespace selector was merged with two exclusions the engine adds unconditionally — including its own namespace, which is the specific thing that turns "the webhook is down" into "the webhook can never come back up".

So the first honest answer to "what does the product add" is not a language and not a rule library. It is that **the registration object is now generated from your intent instead of maintained by you**, and the generator remembers the guardrails you would forget.

### And a gap from lesson 03 closes on its own

There is something else in those `rules` that you did not ask for. You wrote `resources: ["pods"]`. The registration covers `deployments`, `statefulsets`, `daemonsets`, `replicasets`, `jobs` and `cronjobs`.

Lesson 03 is where that matters. There you created a Deployment whose pod template violated an enforced `restricted` policy and watched it be **accepted** — `deployment.apps/web created`, a warning, `0/1` forever, and the real refusal hiding in a `FailedCreate` event on a ReplicaSet whose name you did not know. The reason was structural: PSA's predicate is on the Pod resource, and a Deployment is not a Pod.

Try the same shape here:

```bash
kubectl run bad --image=busybox:latest -n kyvtest --restart=Never --command -- sh -c 'echo hi'
kubectl create deployment web --image=busybox:latest -n kyvtest
```

```
Error from server: admission webhook "vpol.validate.kyverno.svc-fail" denied the request:
Policy no-latest failed: image must not use the :latest tag

error: failed to create deployment: admission webhook "vpol.validate.kyverno.svc-fail" denied
the request: Policy no-latest failed: image must not use the :latest tag
```

**The Deployment is refused at `kubectl create`.** Not a warning, not an event, not `0/1` — a non-zero exit code, in CI, at the moment somebody typed the wrong thing.

And the mechanism is not magic, it is written down. The policy object's own status holds the variants that were generated from your one expression:

```bash
kubectl get vpol no-latest -o jsonpath='{.status.autogen.configs.cronjobs.spec.validations[0].expression}{"\n"}'
kubectl get vpol no-latest -o jsonpath='{.status.autogen.configs.defaults.spec.validations[0].expression}{"\n"}'
```

```
object.spec.jobTemplate.spec.template.spec.containers.all(c, !c.image.endsWith(':latest'))
object.spec.template.spec.containers.all(c, !c.image.endsWith(':latest'))
```

There it is. A Pod keeps its containers at `spec.containers`; a Deployment at `spec.template.spec.containers`; a CronJob at `spec.jobTemplate.spec.template.spec.containers`. Writing this rule properly by hand means maintaining **one expression per controller shape**, forever, and getting the CronJob nesting right at 5pm on a Friday. The product wrote them from your one expression and put them where you can read them.

That is worth naming as a category, because it is most of what a policy product is: not new power, but **the removal of a class of clerical error that the raw mechanism makes easy and undetectable.** Lesson 03's gap was never conceptually hard. It was just extremely easy to not notice.

### The rival, and a language that is not CEL

Gatekeeper is the other answer, older, and it uses **Rego** — the query language from OPA, which is a real general-purpose policy language rather than an expression evaluator.

```bash
kubectl apply -f \
  https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.23.0/deploy/gatekeeper.yaml
kubectl wait --for=condition=Available deploy --all -n gatekeeper-system --timeout=180s
```

Gatekeeper splits a rule into two objects, and the split is going to look familiar:

```bash
kubectl create ns gktest
kubectl apply -f - <<'EOF'
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snolatest
spec:
  crd:
    spec:
      names: {kind: K8sNoLatest}
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8snolatest

      violation[{"msg": msg}] {
        c := input.review.object.spec.containers[_]
        endswith(c.image, ":latest")
        msg := sprintf("image must not use the :latest tag: %v", [c.image])
      }
EOF
sleep 15
kubectl get constrainttemplate k8snolatest -o jsonpath='created={.status.created}{"\n"}'
```

```
created=true
```

`created` — created *what*? Ask the cluster what kinds it knows:

```bash
kubectl api-resources | grep -i k8snolatest
```

```
k8snolatest       constraints.gatekeeper.sh/v1beta1    false    K8sNoLatest
```

**Writing a policy template added a new kind to your cluster's API.** That is Act VII lesson 09, exactly and literally: a CRD extends the store, and everything a built-in kind gets for free — a REST endpoint, a watch stream, schema validation, `kubectl explain` — comes with it. Gatekeeper's design decision is that the *second* object is an instance of a type the *first* object defined, so your rule's parameters get a schema and are validated by the API server rather than by the policy engine.

Now the second object:

```bash
kubectl apply -f - <<'EOF'
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoLatest
metadata:
  name: no-latest-gktest
spec:
  enforcementAction: deny
  match:
    kinds:
    - apiGroups: [""]
      kinds: ["Pod"]
    namespaces: ["gktest"]
EOF
sleep 15
kubectl run bad --image=busybox:latest -n gktest --restart=Never --command -- sh -c 'echo hi'
```

```
Error from server (Forbidden): admission webhook "validation.gatekeeper.sh" denied the request:
[no-latest-gktest] image must not use the :latest tag: busybox:latest
```

Two things to notice, one small and one not.

The small one: the message names the offending image, `busybox:latest`, because Rego's `sprintf` built the string at evaluation time. Lesson 04's `message` was a fixed string. (`messageExpression` exists on a VAP for this, and is the field people forget.)

The large one: **you have now met the same two-object split three times.** `ValidatingAdmissionPolicy` + binding. `ConstraintTemplate` + `Constraint`. And in Kyverno, a policy plus the generated `rules` that decide where it applies. Three independent designs, one shape — a **rule** and a separate statement of **where it is switched on**. Lesson 04 justified that split by demonstrating one policy denying in one namespace and warning in another. Two other teams reached the same conclusion without coordinating, which is decent evidence that it is a property of the problem rather than an API quirk.

### Two products, and lesson 04's dilemma answered in opposite directions

Lesson 04's crown measurement was scaling your webhook to zero: at `failurePolicy: Fail` an allowed image was refused and the cluster stopped creating Pods; at `Ignore` a forbidden image sailed through with no error and nothing in the object. You were told to decide which you preferred, and that there was no third option.

Both products decided for you. Look at what each one installed:

```bash
for w in kyverno-resource-validating-webhook-cfg gatekeeper-validating-webhook-configuration; do
  echo "== $w"
  kubectl get validatingwebhookconfiguration "$w" \
    -o jsonpath='{range .webhooks[*]}{.name}{"  failurePolicy="}{.failurePolicy}{"  timeout="}{.timeoutSeconds}{"  apiGroups="}{.rules[0].apiGroups}{"  resources[0]="}{.rules[0].resources[0]}{"\n"}{end}'
done
kubectl get deploy -n kyverno -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas --no-headers
kubectl get deploy -n gatekeeper-system -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas --no-headers
kubectl get pdb -A --no-headers | grep -E "kyverno|gatekeeper" || echo "(no PodDisruptionBudget in kyverno)"
```

```
== kyverno-resource-validating-webhook-cfg
vpol.validate.kyverno.svc-fail  failurePolicy=Fail  timeout=10  apiGroups=[""]  resources[0]=pods
== gatekeeper-validating-webhook-configuration
validation.gatekeeper.sh  failurePolicy=Ignore  timeout=3  apiGroups=["*"]  resources[0]=*
check-ignore-label.gatekeeper.sh  failurePolicy=Fail  timeout=3  apiGroups=[""]  resources[0]=namespaces
kyverno-admission-controller    1
kyverno-background-controller   1
kyverno-cleanup-controller      1
kyverno-reports-controller      1
gatekeeper-audit                1
gatekeeper-controller-manager   3
gatekeeper-system   gatekeeper-controller-manager   1   N/A   2
```

Lay it out, because they disagree on every line:

| | Kyverno | Gatekeeper |
|---|---|---|
| `failurePolicy` | **`Fail`** — fail closed | **`Ignore`** — fail open |
| what it intercepts | only what a policy asked for | `apiGroups: ["*"]`, `resources: ["*"]` |
| timeout | 10s | 3s |
| replicas in the default install | **1** | **3**, with a PodDisruptionBudget |

Neither is careless; each is coherent with the other choices on its column. Gatekeeper intercepts everything, so it must be cheap and it must not be able to stop the cluster: hence a 3-second timeout, three replicas, a PDB, and `Ignore`. Kyverno intercepts almost nothing until you ask, so `Fail` is affordable — a narrow webhook that is down blocks a narrow set of writes.

And then read the default installs against those choices one more time, because there is a genuine trap in the intersection. **Kyverno's `install.yaml` is `failurePolicy: Fail` with one replica and no PodDisruptionBudget.** That is precisely the configuration lesson 04's Check-yourself described as an outage waiting for the node to reboot. In production you would deploy it in the high-availability shape its Helm chart offers; the point for now is that `kubectl apply -f install.yaml` does not give you that, and nothing warns you.

**So the answer to prediction (a) is no.** Installing a product does not make lesson 04's choice go away. It makes it a **default you inherit**, in an object you did not write, which is strictly worse than making it yourself unless you go and read it. The reflex to build from this lesson is: after installing any admission-based tool, print its `failurePolicy` and its replica count before you do anything else.

### The clock

Prediction (c). Lesson 04 tried to write "no deploys outside office hours" and got:

```
ERROR: <input>:1:29: undeclared reference to 'now'
```

— and the explanation was structural rather than accidental. CEL runs *inside the API server*, on the write path of every request, so it is deliberately deterministic and total: no clock, no network, no unbounded loops. Act IX had already separated this class of problem from the other one: a **syntax gap** can be closed by a richer rule language, an **interface gap** cannot, because it needs the decision point to be *given* something it is not given.

Rego runs in a different process. Try it there:

```bash
kubectl apply -f - <<'EOF'
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sofficehours
spec:
  crd:
    spec:
      names: {kind: K8sOfficeHours}
      validation:
        openAPIV3Schema:
          type: object
          properties:
            startHour: {type: integer}
            endHour: {type: integer}
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8sofficehours

      hour := time.clock(time.now_ns())[0]

      violation[{"msg": msg}] {
        hour < input.parameters.startHour
        msg := sprintf("deploys allowed %v:00-%v:00 UTC only; it is now %v:00", [input.parameters.startHour, input.parameters.endHour, hour])
      }

      violation[{"msg": msg}] {
        hour >= input.parameters.endHour
        msg := sprintf("deploys allowed %v:00-%v:00 UTC only; it is now %v:00", [input.parameters.startHour, input.parameters.endHour, hour])
      }
EOF
kubectl apply -f - <<'EOF'
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sOfficeHours
metadata: {name: office-hours}
spec:
  enforcementAction: deny
  match:
    kinds: [{apiGroups: [""], kinds: ["Pod"]}]
    namespaces: ["gktest"]
  parameters: {startHour: 9, endHour: 17}
EOF
sleep 15
date -u +"UTC now: %H:%M"
kubectl run t1 --image=busybox:1.36 -n gktest --restart=Never --command -- sh -c 'echo hi'
```

```
UTC now: 14:24
pod/t1 created
```

Admitted — but that proves nothing yet, since a rule that always says yes would also print this. Narrow the window so that "now" falls outside it, **changing only the parameters on the Constraint**:

```bash
kubectl patch k8sofficehours office-hours --type=merge \
  -p '{"spec":{"parameters":{"startHour":9,"endHour":12}}}'
sleep 12
kubectl run t2 --image=busybox:1.36 -n gktest --restart=Never --command -- sh -c 'echo hi'
```

```
Error from server (Forbidden): admission webhook "validation.gatekeeper.sh" denied the request:
[office-hours] deploys allowed 9:00-12:00 UTC only; it is now 14:00
```

**`it is now 14:00`.** The rule read a clock, and it is the real one.

Act IX's second inexpressible rule — "only during an incident", the one it said could not be fixed by any amount of rule syntax — is now enforced on your cluster. So before you conclude that Act IX was wrong, ask *why* it works here, because the answer is the opposite of "Rego is a better language":

It works because **the evaluator moved out of the API server.** A process that is not on the API server's critical path is allowed to be impure — to read a clock, to do I/O, to take as long as it takes. CEL has no clock not because CEL's designers forgot, but because of *where CEL runs*. The gap closed exactly the way Act IX said an interface gap has to close: somebody changed what the decision point is handed. Nobody made the syntax richer; they moved the decision somewhere it could see more.

And now check the price against the act's spine, because you have just bought something. A rule with a clock is a rule **whose verdict is not reproducible from the object**. Two identical `kubectl apply`s now legitimately disagree. Nothing in the stored Pod records which side of 12:00 it arrived on, so "why was this admitted?" stops being answerable by reading the cluster. Lesson 04 argued that a VAP is operationally safer than a webhook because its `failurePolicy` governs your expression erroring rather than a service being reachable; this is the same argument in a second currency, and it is the whole reason to reach for CEL first and Rego only when you must.

Before moving on, take the office-hours rule back off, or the rest of this lesson will fail at 17:00:

```bash
kubectl delete k8sofficehours office-hours
```

### The other object

The second thing lesson 04's CEL could not do was read anything other than the object in front of it. That is the same interface gap wearing different clothes, and it is the one that comes up constantly in real rules: *images may only come from registries on our list*, where the list is not something you want to redeploy a policy to change.

Kyverno's CEL environment adds a function for it. The policy is otherwise the shape you already know:

```bash
kubectl create cm allowed-registries -n kyvtest --from-literal=prefixes='ghcr.io/,quay.io/'
kubectl apply -f - <<'EOF'
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: registry-from-cm
spec:
  validationActions: ["Deny"]
  matchConstraints:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: kyvtest}
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE"]
      resources: ["pods"]
  variables:
  - name: allowed
    expression: "resource.Get('v1', 'configmaps', 'kyvtest', 'allowed-registries').data['prefixes'].split(',')"
  validations:
  - expression: "object.spec.containers.all(c, variables.allowed.exists(p, c.image.startsWith(p)))"
    message: "image registry is not in the allowed-registries ConfigMap"
EOF
sleep 10
kubectl run r1 --image=busybox:1.36 -n kyvtest --restart=Never --command -- sh -c 'echo hi'
```

```
Error from server: admission webhook "vpol.validate.kyverno.svc-fail" denied the request:
Policy registry-from-cm failed: image registry is not in the allowed-registries ConfigMap
```

Now the experiment that matters. Change **nothing about the policy** — edit the ConfigMap:

```bash
kubectl create cm allowed-registries -n kyvtest \
  --from-literal=prefixes='ghcr.io/,quay.io/,busybox' --dry-run=client -o yaml | kubectl apply -f -
sleep 6
kubectl run r2 --image=busybox:1.36 -n kyvtest --restart=Never --command -- sh -c 'echo hi'
```

```
pod/r2 created
```

**Same image, same policy, opposite verdict, because a different object changed.** The decision is now a function of cluster state, which is the thing Act IX said RBAC could never do because RBAC is handed four strings, and which lesson 04 could not do because CEL in the API server is handed one object and one requester.

Gatekeeper has the same capability under a different name — a `Config` object tells it which kinds to keep a cached copy of, and Rego reads them from `data.inventory`. Note the word **cached**, in both products, and note that the ConfigMap edit above took a few seconds to bite.

Which is Act IX's thesis walking back on stage. A cached lookup means the policy decision is a statement about **the cluster as of a moment ago**, so this rule inherits exactly the property lesson 02 of Act IX measured on a deleted ServiceAccount: the answer is correct, and it is about the past. Tighten the cache and you have put a live read on the write path of every Pod creation, with a new availability failure. There is no setting that gives you both, and now you own that trade in your admission policy as well as in your authentication.

### The predicate you were told you could not have

One more thing the products add, and it is the most direct possible answer to the complaint lesson 04 opened with. Lesson 03's limit was that PSA gives you three levels and no way to take four-fifths of one: `restricted` requires `seccompProfile`, and if your workload genuinely cannot have one, your options are `baseline` for the whole namespace or an exemption from everything.

Kyverno's older API — the one its own deprecation warning will point you away from, and worth seeing exactly once — treats PSA's levels as a component you can subtract from:

```bash
kubectl create ns psstest
kubectl apply -f - <<'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata: {name: pss-restricted-minus-seccomp}
spec:
  rules:
  - name: restricted
    match:
      any:
      - resources: {kinds: ["Pod"], namespaces: ["psstest"]}
    validate:
      failureAction: Enforce
      podSecurity:
        level: restricted
        version: latest
        exclude:
        - controlName: "Seccomp"
EOF
```

```
Warning: ClusterPolicy (kyverno.io) is deprecated and will be removed in a future release;
migrate to ValidatingPolicy, MutatingPolicy, GeneratingPolicy or ImageValidatingPolicy
(policies.kyverno.io), see https://kyverno.io/docs/guides/migration-to-cel/
clusterpolicy.kyverno.io/pss-restricted-minus-seccomp created
```

A Pod that satisfies `restricted` in every respect except the seccomp profile — the exact Pod lesson 03's `locked` namespace refused:

```bash
kubectl apply -n psstest -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: noseccomp}
spec:
  restartPolicy: Never
  securityContext: {runAsNonRoot: true, runAsUser: 1000}
  containers:
  - name: c
    image: busybox:1.36
    securityContext:
      allowPrivilegeEscalation: false
      capabilities: {drop: ["ALL"]}
    command: ["sh","-c","echo hi"]
EOF
```

```
pod/noseccomp created
```

And now drop one of the controls you did *not* exclude:

```bash
kubectl apply -n psstest -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: alsoroot}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext:
      allowPrivilegeEscalation: false
      capabilities: {drop: ["ALL"]}
    command: ["sh","-c","echo hi"]
EOF
```

```
Error from server: error when creating "STDIN": admission webhook "validate.kyverno.svc-fail"
denied the request:

resource Pod/psstest/alsoroot was blocked due to the following policies

pss-restricted-minus-seccomp:
  restricted: 'Validation rule ''restricted'' failed. It violates PodSecurity "restricted:latest":
  (Forbidden reason: runAsNonRoot != true, field error list:
  [spec.containers[0].securityContext.runAsNonRoot: Required value])'
```

Read the message closely: `It violates PodSecurity "restricted:latest"`, `Forbidden reason: runAsNonRoot != true`. That is **lesson 03's wording**, because it is lesson 03's predicate — the engine is running the same PSA evaluator, minus the control you named.

So the product's answer to "the predicate is not yours" turns out to be two answers, not one. You can write your own; and you can also treat somebody else's as a **library component** and subtract from it, which is not something the mechanism you built in lesson 04 could do at all.

### The control that refuses nothing

Every mechanism in the last three lessons fires on a write. That is what makes it cheap and it is also a hole you cannot see from inside it: **admission has no opinion about anything that already exists.** Turn on a perfect policy today and every Pod that violates it keeps running, unmentioned, until something happens to recreate it — which is the state lesson 03's Check-yourself described as a cluster that looks healthy in every dashboard and has quietly lost the ability to heal.

Watch that directly. A Pod first, then the policy:

```bash
kubectl create ns already
kubectl run legacy --image=busybox:latest -n already --restart=Never --command -- sh -c 'sleep 600'
kubectl apply -f - <<'EOF'
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoLatest
metadata: {name: no-latest-already}
spec:
  enforcementAction: deny
  match:
    kinds: [{apiGroups: [""], kinds: ["Pod"]}]
    namespaces: ["already"]
EOF
```

Nothing happens, correctly — nothing was written. Then wait about a minute and ask the Constraint what it knows:

```bash
for i in $(seq 1 10); do sleep 12
  T=$(kubectl get k8snolatest no-latest-already -o jsonpath='{.status.totalViolations}' 2>/dev/null)
  echo "  ${i}: totalViolations=$T"; case "$T" in ""|0) ;; *) break;; esac
done
kubectl get k8snolatest no-latest-already -o jsonpath='{.status.violations}' | python3 -m json.tool
kubectl get pod legacy -n already
```

```
  1: totalViolations=
  ...
  5: totalViolations=1
[
    {
        "enforcementAction": "deny",
        "group": "",
        "kind": "Pod",
        "message": "image must not use the :latest tag: busybox:latest",
        "name": "legacy",
        "namespace": "already",
        "version": "v1"
    }
]
NAME     READY   STATUS    RESTARTS   AGE
legacy   1/1     Running   0          84s
```

`"enforcementAction": "deny"` — and `Running`.

That pair of lines is the most important output in this lesson. The policy says deny, the violation is found and named, and **nothing is refused**, because there is no write to refuse. What you are looking at is a **fourth Gatekeeper Deployment doing a completely different job from the other three**: `gatekeeper-audit` walks the objects that exist and evaluates the same rules against them on a timer. Kyverno's `reports-controller` is the same idea with a different output — a `PolicyReport` object per resource:

```bash
kubectl get policyreport -n kyvtest
```

```
NAMESPACE   NAME                                   KIND   NAME   PASS   FAIL   WARN   ERROR   SKIP   AGE
kyvtest     policyreport.wgpolicyk8s.io/08c1ba...   Pod    ok     1      1      0      0       0      9m14s
kyvtest     policyreport.wgpolicyk8s.io/95646a...   Pod    r2     2      0      0      0       0      6m4s
```

Pod `ok`: **one pass, one fail**, and it is running. It was admitted before `registry-from-cm` existed, and the report is the only place in the cluster that says so.

Go back to the diagram on the act's overview page and find the fifth column — **AFTER, the record, which knows everything and has no leverage, because it has already happened.** You have now met it. It is not a lesser version of admission; it answers a question admission cannot be asked. And it is the mechanism that makes turning a policy on possible at all: `enforcementAction: dryrun` on a Constraint, or `validationActions: ["Audit"]` on a Kyverno policy, gets you the list of everything that would break *before* you break it — which is the third item on the list this lesson opened with, and the one you had no way to build in lesson 04.

### Giving the write path back

One loose end, and it is the best thing in either product. Everything above is a service in your write path. Lesson 04's argument for a `ValidatingAdmissionPolicy` over a webhook was operational and it did not go away: a VAP is compiled into the API server, so there is nothing separate to be down.

Kyverno can hand that back. Ask it to:

```bash
kubectl apply -f - <<'EOF'
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: no-latest-native
spec:
  validationActions: ["Deny"]
  autogen:
    validatingAdmissionPolicy: {enabled: true}
  matchConstraints:
    namespaceSelector:
      matchLabels: {kubernetes.io/metadata.name: kyvtest}
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE","UPDATE"]
      resources: ["pods"]
  validations:
  - expression: "object.spec.containers.all(c, !c.image.endsWith(':latest'))"
    message: "image must not use the :latest tag"
EOF
sleep 12
kubectl get validatingadmissionpolicy
kubectl get vpol no-latest-native -o jsonpath='generated={.status.generated}  msg={.status.conditionStatus.message}{"\n"}'
```

```
No resources found
generated=false  msg=skip generating ValidatingAdmissionPolicy: pod controllers autogen is enabled.
```

**Refused, and read the reason.** Not a bug and not a missing feature: `pod controllers autogen is enabled`. A native `ValidatingAdmissionPolicy` is a single expression over a single resource shape. The six rewritten expressions from earlier in this lesson — the ones that closed lesson 03's Deployment gap — cannot be expressed as one VAP, so the engine will not pretend. Give up the autogen and it obliges:

```bash
kubectl apply -f - <<'EOF'
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: no-latest-native
spec:
  validationActions: ["Deny"]
  autogen:
    validatingAdmissionPolicy: {enabled: true}
    podControllers: {controllers: []}
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE","UPDATE"]
      resources: ["pods"]
  validations:
  - expression: "object.spec.containers.all(c, !c.image.endsWith(':latest'))"
    message: "image must not use the :latest tag"
EOF
sleep 12
kubectl get validatingadmissionpolicy,validatingadmissionpolicybinding
```

```
NAME                        VALIDATIONS   PARAMKIND   AGE
vpol-no-latest-native       1             <unset>     8s

NAME                                POLICYNAME              PARAMREF   AGE
vpol-no-latest-native-binding       vpol-no-latest-native    <unset>    8s
```

A real `ValidatingAdmissionPolicy` and a real binding — the two objects you hand-wrote in lesson 04 — generated for you. And they belong to the policy that made them:

```bash
kubectl get validatingadmissionpolicy vpol-no-latest-native \
  -o jsonpath='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}{.spec.validations[0].expression}{"\n"}'
```

```
ValidatingPolicy/no-latest-native
object.spec.containers.all(c, !c.image.endsWith(':latest'))
```

`ownerReferences` — Act VII's garbage-collection mechanism — so deleting the Kyverno policy deletes the VAP, and Act VI's loop keeps them in step. And the expression is the string you typed in lesson 04, unchanged, now compiled into the API server with no webhook of anybody's in front of it.

Which is a genuinely elegant answer to prediction (a), and a strictly conditional one. **You can be out of the write path, or you can have the features that need a process. Not both, and the engine tells you which you chose.** The rules that are just expressions over one object should be compiled in and cost nothing. The rules that need a clock, another object, or six controller shapes need a service, and that service can be down, and you get to pick `Fail` or `Ignore`.

That is the act's spine again, one level up. Lesson 04 placed a decision on the timeline. This lesson places the *evaluator*, and the same sentence holds: the closer in you put it, the cheaper and more reliable it is, and the less it can know.

> **Check yourself —** your platform team standardises on one engine and writes forty policies. A year later, an incident review finds that a workload violating three of them has been running in production for eight months. Nobody disabled anything, no policy was edited, and all forty policies still evaluate correctly today. Give three separate mechanisms from this act that each fully explain it, and say which one you can rule out from the cluster alone.

<details>
<summary>Answer</summary>

**One — it was created before the policy, and admission never looks back.** The Pod was admitted when the rule did not exist or did not match its namespace, and has not been recreated since. This is the `legacy` Pod: `enforcementAction: deny` and `Running`, for as long as nothing restarts it. Ruling it out is easy and nobody does it, because it requires reading the audit output rather than the policy list.

**Two — the engine was down when it was created, at `failurePolicy: Ignore`.** One rollout during a node drain, one image-pull failure, one scale-to-zero, and the write went through unexamined. Lesson 04 measured this: no error, no warning, nothing in the stored object. If you inherited Gatekeeper's default you inherited `Ignore`, and the eight months are the gap between "the webhook was unavailable for ninety seconds" and anybody noticing.

**Three — the object it was created *from* was not covered.** If the rule is registered for `pods` only, a Deployment sails through and the Pod is refused later, as a `FailedCreate` event on a ReplicaSet — lesson 03's gap. Whether you are exposed depends on whether autogen was on, which is a field on the policy, not a thing anybody remembers.

And a fourth worth having even though it is out of scope for "three mechanisms": an exemption. A namespace exclusion, a `PolicyException`, or — worst — lesson 03's `AdmissionConfiguration` file, where the exemption is not in the API at all.

**The one you can rule out from the cluster alone is the third**, and only that one. It is a field on a policy object you can read right now, and it is either set or it is not. The first needs the audit or report output, which is retained for a while and then is not. The second needs the engine's availability history — Events that have long expired, or metrics if somebody was scraping them — and it is the most likely of the three precisely because it leaves the least evidence.

Which is the act's characteristic bug, one abstraction level up from where the README put it. It said a control that is doing nothing looks exactly like a control that has nothing to do. Here: **a control that was skipped looks exactly like a control that passed**, and the record of the difference is a thing you had to have been keeping.

</details>

<!-- figure -->
```
   WHAT THE PRODUCT ADDS, AND IT IS MOSTLY NOT POWER

   1. THE REGISTRATION OBJECT IS GENERATED FROM YOUR INTENT
        no policies -> WEBHOOKS: 0. an empty registration.
        one policy  -> rules = pods + deployments/statefulsets/
                       daemonsets/replicasets/jobs/cronjobs
                       nsSelector = yours AND NotIn[kube-system]
                                          AND NotIn[its own ns]
        <- every one of these is L04's check-yourself answer,
           which you were left to remember. you wrote none.

   2. LESSON 03'S DEPLOYMENT GAP, CLOSED
        L03: enforce=restricted + create deployment -> "created",
             0/1 forever, 403 buried in a ReplicaSet event.
        HERE: "error: failed to create deployment: ... denied"
        mechanism is READABLE in status.autogen.configs:
          pods ..... object.spec.containers
          default .. object.spec.template.spec.containers
          cronjobs . object.spec.jobTemplate.spec.template.spec
                     .containers
        one expression per controller shape, forever, by hand.
        that is what the product actually saves you.

   3. THE FIFTH COLUMN: A CONTROL THAT REFUSES NOTHING
        Pod created, THEN the constraint:
          "enforcementAction": "deny"   +   STATUS: Running
        gatekeeper-audit / kyverno reports-controller walk what
        EXISTS on a timer. admission cannot be asked this.
        -> and it is how you TURN A POLICY ON: dryrun / Audit
           gives the breakage list BEFORE the breakage.

   THE SAME TWO OBJECTS, INVENTED THREE TIMES
     VAP + binding | ConstraintTemplate + Constraint | policy + rules
     a RULE, and a separate statement of WHERE IT IS ON.
     three teams, no coordination -> it is the problem's shape.
     bonus: ConstraintTemplate GENERATES A CRD. Act VII L09.
     so constraint parameters get a schema and kubectl explain.

   L04'S DILEMMA IS NOT SOLVED. IT IS INHERITED.
                        KYVERNO        GATEKEEPER
     failurePolicy      Fail           Ignore
     intercepts         what a policy  apiGroups:[*]
                        asked for      resources:[*]
     timeout            10s            3s
     default replicas   1, no PDB      3, with a PDB
     coherent columns, opposite horns. and install.yaml gives
     you Fail + ONE replica -- L04's outage, preinstalled.
     REFLEX: after installing anything admission-based, print
     its failurePolicy and its replica count. first.

   AND CEL'S TWO GAPS DO CLOSE -- NOT BY BETTER SYNTAX
     A CLOCK   rego: time.clock(time.now_ns())[0]
               -> "deploys allowed 9:00-12:00 UTC only;
                   it is now 14:00"
               Act IX's "only during an incident", ENFORCED.
               kyverno's CEL still says: undeclared ref 'now'
               -- ON PURPOSE, so it can compile down to a VAP.
     ANOTHER    resource.Get('v1','configmaps',ns,name)
     OBJECT     edit the ConfigMap, NOT the policy
               -> same image: DENIED, then CREATED.
     both closed because THE EVALUATOR LEFT THE APISERVER.
     a process off the critical path may be impure. that is
     an INTERFACE change, exactly as Act IX said it must be.

   WHAT EACH ONE COST
     the clock -> the verdict is NOT REPRODUCIBLE FROM THE
                  OBJECT. two identical applies may disagree
                  and nothing records which side of 12:00.
     the lookup -> a CACHE. so the decision is about the
                  cluster A MOMENT AGO. Act IX L02's stale
                  answer, now on the write path of every Pod.

   AND PSA BECOMES A COMPONENT YOU CAN SUBTRACT FROM
     podSecurity: {level: restricted, exclude: [Seccomp]}
       Pod with no seccompProfile ....... created
       Pod also missing runAsNonRoot .... refused, and the
         message is L03'S OWN WORDING ("It violates
         PodSecurity restricted:latest ... runAsNonRoot != true")
     because it IS L03's evaluator, minus one control.
     L03's all-or-nothing was never the predicate's fault.

   THE ESCAPE HATCH, AND ITS PRICE, MEASURED
     autogen.validatingAdmissionPolicy.enabled: true
       -> "skip generating ValidatingAdmissionPolicy:
           pod controllers autogen is enabled."
     drop autogen and a REAL VAP + binding appear, with
     ownerReferences back to the kyverno policy, holding the
     expression you typed in L04, byte for byte.
     SO: out of the write path, OR the features that need a
     process. never both -- and the object tells you which.
     the act's spine, one level up: this time you are placing
     the EVALUATOR, and closer in still means knows less.

   AND THE UNINSTALL IS THE LAST TRAP
     kubectl delete -f install.yaml  -> success on every object
     ...and TEN registration objects survive, because a
     CONTROLLER wrote them at runtime and the FILE never
     described them. what is left:
       failurePolicy: Fail -> a Service that no longer exists
       "service \"kyverno-svc\" not found"  (not "connection
       refused" -- there is nothing to refuse)
       and the NotIn[kube-system]/NotIn[own-ns] guardrails are
       GONE, because they were merged into a policy-derived
       object and the policy is gone.
     delete -l webhook.kyverno.io/managed-by=kyverno
     GENERAL: an operator's most dangerous objects are the ones
     IT created, not the ones you installed.
```

### Uninstalling, which is the last measurement

**Cleanup.** Both engines are large, both are in your write path, and neither should be left installed by accident. Delete the policies first, then the engines:

```bash
kubectl delete vpol --all
kubectl delete cpol --all
kubectl delete k8snolatest --all
kubectl delete constrainttemplate --all
kubectl delete ns kyvtest gktest already psstest --ignore-not-found
kubectl delete -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.23.0/deploy/gatekeeper.yaml --ignore-not-found
kubectl delete -f https://github.com/kyverno/kyverno/releases/download/v1.19.0/install.yaml --ignore-not-found
```

That looks complete, and `kubectl delete -f` reported success on every object in both files. Check it:

```bash
kubectl get validatingwebhookconfiguration,mutatingwebhookconfiguration
```

```
NAME                                                        WEBHOOKS   AGE
kyverno-cel-exception-validating-webhook-cfg                1          21m
kyverno-cleanup-validating-webhook-cfg                      1          21m
kyverno-exception-validating-webhook-cfg                    1          21m
kyverno-global-context-validating-webhook-cfg               1          21m
kyverno-policy-validating-webhook-cfg                       1          21m
kyverno-resource-validating-webhook-cfg                     1          21m
kyverno-ttl-validating-webhook-cfg                          1          21m
...
```

**Ten registration objects survived an uninstall that succeeded.** And they survived it for the reason this whole section of the lesson has been about: they were *never in `install.yaml`*. A controller in that namespace wrote them at runtime, from the policies that existed. `kubectl delete -f` can only delete what the file describes, and the file does not describe these.

So look at what you are now running:

```bash
kubectl get validatingwebhookconfiguration kyverno-resource-validating-webhook-cfg -o json \
  | python3 -c "
import json, sys
for w in json.load(sys.stdin)['webhooks']:
    print(w['name'], '| failurePolicy:', w['failurePolicy'])
    print('  nsSelector:', json.dumps(w['namespaceSelector']))
"
kubectl run x --image=busybox:1.36 -n kyvtest --restart=Never --command -- sh -c 'echo hi'
```

```
vpol.validate.kyverno.svc-fail | failurePolicy: Fail
  nsSelector: {"matchLabels": {"kubernetes.io/metadata.name": "kyvtest"}}

Error from server (InternalError): Internal error occurred: failed calling webhook
"vpol.validate.kyverno.svc-fail": failed to call webhook: Post
"https://kyverno-svc.kyverno.svc:443/vpol/no-latest?timeout=10s": service "kyverno-svc" not found
```

`failurePolicy: Fail`, pointing at a Service that does not exist, referencing a policy that does not exist, in a cluster where you deliberately uninstalled the thing that would answer. This is lesson 04's outage — *created by cleaning up*.

Two details make it worse than lesson 04's version and both are visible above. The error is `service "kyverno-svc" not found` rather than `connection refused`, because there is no longer a Service at all, so anyone diagnosing it is looking for a Deployment nobody can find. And the `namespaceSelector` retains **only** the selector of the last policy — the two `NotIn` exclusions that the engine had merged in are gone, because they were merged into a policy-derived object and the policy is gone. The guardrails were never separable from the thing they were guarding.

The actual fix, using the label the engine puts on its own handiwork:

```bash
kubectl delete validatingwebhookconfiguration,mutatingwebhookconfiguration \
  -l webhook.kyverno.io/managed-by=kyverno
kubectl delete ns kyverno gatekeeper-system --ignore-not-found
kubectl run sanity --image=busybox:1.36 --restart=Never --command -- sh -c 'echo hi'
kubectl delete pod sanity --ignore-not-found
```

```
pod/sanity created
```

Keep the general form, because it is not about Kyverno. **An operator's most dangerous objects are the ones it created rather than the ones you installed**, and uninstalling by deleting the manifest you applied is a strictly incomplete operation. Anything that registers a webhook, writes a finalizer, or generates a CRD has left something behind that your `delete -f` will report success without touching — and in the webhook case, the thing left behind is a fail-closed gate in front of your API server.

> **You understand this when you can** name four things a policy product supplies that a hand-built webhook does not, and say which one is the removal of clerical error rather than an added capability; predict what an engine's `ValidatingWebhookConfiguration` intercepts before any policy exists, and explain why both of the other plausible answers are worse; read a generated webhook's `rules` and `namespaceSelector` and point at each thing lesson 04 told you to do by hand; explain autogen in terms of where a Pod's containers live in a Deployment and in a CronJob, and say which lesson 03 failure it closes and how the failure presented; say what a `ConstraintTemplate` adds to the cluster besides a policy, and connect it to Act VII lesson 09; give the three places you have now seen the rule/where-it-applies split and say what that repetition is evidence of; state Kyverno's and Gatekeeper's opposing defaults for `failurePolicy`, interception scope and replica count, explain why each set is internally coherent, and name the one-line check to run after installing either; demonstrate a rule that reads a clock, and explain why CEL cannot and Rego can *without* claiming Rego is the better language; say precisely what a clock costs you in terms of reproducing a verdict from the stored object; demonstrate a rule whose verdict depends on another object, name the staleness it introduces and the Act IX measurement it repeats; use PSA's own predicate with one control subtracted and say how the error message proves whose evaluator ran; explain why a Constraint can report `enforcementAction: deny` against a `Running` Pod, name the component that found it, and say which column of the act's opening diagram you have just reached; describe how `dryrun`/`Audit` makes turning a policy on possible; get an engine to emit a native `ValidatingAdmissionPolicy`, state the feature you had to give up for it, and explain from the mechanism why those two cannot coexist; and say why `kubectl delete -f install.yaml` leaves a fail-closed webhook behind, what the resulting error says, why the engine's own guardrails vanish with it, and what that generalises to for any operator.

**Which raises:** every control in this act so far has governed **whether an object may exist**. Not one of them has said anything about *what is inside it* once it does. And you have just spent a lesson installing services that read every object on its way into the cluster and write reports about what they found — which, the first time you scope a policy to Secrets, means the plaintext of every password in your cluster passes through a policy engine's evaluator and lands in its report. That is uncomfortable for a reason Act VII already proved and this act has so far walked past: it took one Secret, followed it, and found the same password sitting in **three** places, none of them encrypted, one of which was readable by anyone who could read a file on a node. Admission decides what may be written. It has no opinion whatever about the bytes afterwards. **So of those three locations, which one can cluster configuration actually close — and when the thing that decrypts a Secret is the same server that will happily hand it to you with `kubectl get secret -o yaml`, what exactly has "encrypted" bought?**

---

↑ **[Act X overview](README.md)** · Prev: **[Deciding before it exists](04-deciding-before-it-exists.md)** · Next: **[A Secret that is actually secret](06-a-secret-that-is-actually-secret.md)** →
