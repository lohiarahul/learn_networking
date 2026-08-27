# Adding a kind

Act V already told you the answer to the last lesson's question, and told you the punchline of this one too. It is worth quoting, because you are about to find out whether you believed it:

> *"Everything above is a **CustomResourceDefinition** — a kind the API server did not ship with, taught to it at runtime… And on a cluster where the CRDs are installed but no controller is running, every manifest in this lesson applies cleanly and nothing whatsoever happens."*

Two claims, handed over on trust while you were busy with `HTTPRoute`. That is the right way round for a lesson about routing — but it means you have been carrying the most important idea in this area as a *sentence you were told*, and there is a large difference between that and something you have watched happen.

So this lesson does two things. It makes you build the mechanism yourself, small enough to hold entirely in your head. And then it makes you build the missing half, which Act V could only describe as an absence.

**Start with the question Act V's sentence quietly begs: what does "taught to it at runtime" actually consist of?**

### Adding the noun

```bash
kubectl get crd 2>/dev/null | head -3
```

Probably nothing, on a clean lab. **CustomResourceDefinition** is itself an ordinary kind, which is the trick in one sentence: you extend the API by POSTing an object to the API you are extending.

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: websites.example.com
spec:
  group: example.com
  scope: Namespaced
  names:
    plural: websites
    singular: website
    kind: Website
    shortNames: [ws]
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            required: [content]
            properties:
              content:
                type: string
              replicas:
                type: integer
                minimum: 1
                maximum: 5
EOF
kubectl api-resources --api-group=example.com
```

```
NAME       SHORTNAMES   APIVERSION            NAMESPACED   KIND
websites   ws           example.com/v1        true         Website
```

A new row in the same table you grepped last lesson looking for `Chart` and `Release`. So make one:

```bash
kubectl apply -f - <<'EOF'
apiVersion: example.com/v1
kind: Website
metadata:
  name: hello
spec:
  content: "hello from a kind I invented"
  replicas: 2
EOF
kubectl get websites
kubectl get ws hello -o yaml | head -12
```

> **Predict first —** you have created an object of a kind you invented five seconds ago. It is stored, it has a `resourceVersion`, `kubectl get` lists it. So what is running? Say specifically what you expect to exist in the cluster now as a consequence of that `spec` — and be honest about it, because the answer is the whole lesson.

```bash
kubectl get pods,deploy,cm
```

```
NAME                         DATA   AGE
configmap/kube-root-ca.crt   1      4m48s
```

**Nothing.** No Pods, no Deployment, and the one ConfigMap is stock furniture the control plane puts in every namespace — Act VI's cluster CA, published so that anything running here can verify the API server. Nothing in that listing is a consequence of what you created. You said `replicas: 2` and there are no replicas of anything. You declared content and nothing serves it.

That is not a failure and it is worth being precise about why. Act VI's central claim was that the API server is a store you POST documents to, and that every *behaviour* is a separate loop watching those documents. A CRD extends the store. **It does not extend the set of loops** — there is no mechanism by which it could, because a loop is a running program and you have not written one.

So what did you get for free? Rather a lot, and it is worth cataloguing, because this is exactly the part people reimplement by hand when they should not:

```bash
kubectl explain website.spec
kubectl get ws hello -o jsonpath='{.metadata.resourceVersion}{" "}{.metadata.uid}{"\n"}'
kubectl get websites --watch --output-watch-events &
sleep 1; kubectl patch ws hello --type=merge -p '{"spec":{"replicas":3}}'; sleep 2; kill %1
```

Documentation, a UID, a `resourceVersion`, and a **watch stream** — the same one every controller in Act VI was consuming. And validation, which you can prove is real and server-side:

```bash
kubectl apply -f - <<'EOF'
apiVersion: example.com/v1
kind: Website
metadata:
  name: bad
spec:
  replicas: 99
EOF
```

```
The Website "bad" is invalid:
* spec.replicas: Invalid value: 99: spec.replicas in body should be less than or equal to 5
* spec.content: Required value
```

Two errors, both from the schema you wrote, both refused by the API server before storage. Nothing client-side is involved — the same rejection happens to `curl`.

And it is stored exactly where Act VI taught you to look:

```bash
CP=netlab-control-plane
etcd() {
  kubectl -n kube-system exec etcd-$CP -- etcdctl \
    --cacert /etc/kubernetes/pki/etcd/ca.crt \
    --cert   /etc/kubernetes/pki/etcd/server.crt \
    --key    /etc/kubernetes/pki/etcd/server.key "$@"
}
etcd get --prefix --keys-only /registry/example.com/
```

```
/registry/example.com/websites/default/hello
```

`/registry/<group>/<plural>/<namespace>/<name>`. Compare it with what Act VI had you read, and there is one segment too many:

```bash
etcd get --prefix --keys-only /registry/deployments/
```

```
/registry/deployments/default/web
```

**No `apps`.** A Deployment is in the `apps` API group — `kubectl api-resources` says so — and yet its key has no group segment at all, exactly as Act VI's rule described. Your `Website` has one.

That asymmetry is a fossil, and reading it correctly is worth more than memorising either path. The built-in resources were given their storage paths before API groups existed, and those paths could never be changed afterwards, because the keys are what a live cluster's data actually sits at — moving them would be a migration of every object on every cluster in the world. So the old kinds keep their flat names and every kind added since is namespaced by its group, which is also why nobody can register a CRD called `deployments.example.com` that would collide with anything.

The useful generalisation: Act VI's rule that your `kubectl` arguments are the path holds for everything, but the *prefix* records when the kind was born. Your invented kind is not a second-class citizen in a side table — it is in the same filesystem, filed under a scheme that was tidier by the time it arrived.

### Two subresources worth understanding rather than copying

Before writing the loop, add two things to the CRD, because both explain a piece of Kubernetes you have already used.

```bash
kubectl patch crd websites.example.com --type=merge -p '{
  "spec":{"versions":[{"name":"v1","served":true,"storage":true,
    "subresources":{"status":{},"scale":{
      "specReplicasPath":".spec.replicas",
      "statusReplicasPath":".status.replicas"}},
    "additionalPrinterColumns":[
      {"name":"Replicas","type":"integer","jsonPath":".spec.replicas"},
      {"name":"Ready","type":"string","jsonPath":".status.ready"}],
    "schema":{"openAPIV3Schema":{"type":"object","properties":{
      "spec":{"type":"object","required":["content"],"properties":{
        "content":{"type":"string"},
        "replicas":{"type":"integer","minimum":1,"maximum":5}}},
      "status":{"type":"object","properties":{
        "replicas":{"type":"integer"},"ready":{"type":"string"}}}}}}}]}}'
kubectl get websites
```

**Your `kubectl get` now has columns.** Which tells you something about `kubectl` you may not have noticed in six acts: it has no knowledge of any kind. Every table you have ever read — Pods, Nodes, PVCs — was rendered from `additionalPrinterColumns` shipped with the resource definition. The CLI is entirely generic; the server tells it what to print.

The `status` subresource is the more consequential one. It makes `status` a **separate endpoint** — `/status` alongside the object — and that separation exists for a reason you can now derive. Act VI showed you Pods where `spec` was written by you and `status` was written by a controller, and lesson 03 showed a Pod condition written by the kubelet. Two different writers on one document. Splitting them into two endpoints means **permissions can differ**: a controller can be allowed to write `status` and forbidden from touching `spec`, which is exactly what you want from a program whose job is to report on reality rather than change your intent. That distinction becomes load-bearing when you meet the objects that grant those permissions.

And `scale` is a smaller marvel:

```bash
kubectl scale website hello --replicas=4
kubectl get ws hello -o jsonpath='{.spec.replicas}{"\n"}'
```

**`kubectl scale` works on a kind that did not exist ten minutes ago.** Not because anything special-cased it — because `scale` is a generic subresource, and you told the API server which field in *your* schema plays the role of the replica count. Anything that scales things by calling `/scale` will now scale your kind too, without knowing what it is.

### Adding the verb

Now write the loop. Act VI reduced every controller to three words — **watch, compare, act** — and the honest way to prove that is not a diagram:

```bash
cat > /tmp/website-controller.sh <<'SCRIPT'
#!/bin/sh
echo "controller: starting"
while true; do
  kubectl get websites \
    -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.spec.replicas}{"|"}{.spec.content}{"\n"}{end}' \
  | while IFS='|' read -r NAME REPLICAS CONTENT; do
      [ -z "$NAME" ] && continue
      [ -z "$REPLICAS" ] && REPLICAS=1
      kubectl create configmap site-$NAME --from-literal=index.html="$CONTENT" \
        --dry-run=client -o yaml | kubectl apply -f - >/dev/null
      cat <<EOF | kubectl apply -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site-$NAME
spec:
  replicas: $REPLICAS
  selector: { matchLabels: { site: $NAME } }
  template:
    metadata: { labels: { site: $NAME } }
    spec:
      containers:
      - name: web
        image: nginx:1.27-alpine
        volumeMounts: [ { name: html, mountPath: /usr/share/nginx/html } ]
      volumes: [ { name: html, configMap: { name: site-$NAME } } ]
EOF
      READY=$(kubectl get deploy site-$NAME -o jsonpath='{.status.readyReplicas}')
      kubectl patch website $NAME --subresource=status --type=merge \
        -p "{\"status\":{\"replicas\":$REPLICAS,\"ready\":\"${READY:-0}/$REPLICAS\"}}" >/dev/null
      echo "reconciled $NAME -> $REPLICAS replica(s), ready ${READY:-0}"
    done
  sleep 5
done
SCRIPT
chmod +x /tmp/website-controller.sh
/tmp/website-controller.sh &
sleep 25
kubectl get websites
kubectl get deploy,cm,pods
```

```
NAME    REPLICAS   READY
hello   4          4/4
```

**Four Pods serving content you declared in a kind you invented, with a `READY` column your controller filled in.** Check the content actually arrived:

```bash
kubectl exec deploy/site-hello -- cat /usr/share/nginx/html/index.html
```

Note what you had to reach for, and what you could not. There is no `site-hello` Service, so nothing resolves by name — because your controller does not create one, because you did not write that. **A custom kind promises exactly as much as its controller implements and not one field more.** The CRD's schema will happily accept a `Website` forever whether or not anything reachable exists at the end of it, and that gap is the single most common thing wrong with a real operator.

That shell script is an **operator**. Not a toy version of one — the shape is exactly right, and the two properties that make it one are worth naming while it is running in your terminal:

```bash
kubectl delete deploy site-hello
sleep 10
kubectl get deploy
```

**It came back.** Nothing retried a failed command; the loop simply ran again, observed that reality did not match the `Website`, and acted. That is why controllers are written as loops that re-derive everything rather than as event handlers that apply diffs: **an event handler has to be right once, and a loop only has to be right eventually.** Miss an event, restart mid-operation, lose your connection for an hour — the next pass fixes it, because the desired state was never in the event, it was in the store.

And prove the second property:

```bash
kubectl patch ws hello --type=merge -p '{"spec":{"content":"changed"}}'
sleep 10
kubectl exec deploy/site-hello -- cat /usr/share/nginx/html/index.html
```

**Still the old content** — and that is not a bug in your controller. Check the object it actually writes:

```bash
kubectl get cm site-hello -o jsonpath='{.data.index\.html}{"\n"}'
```

The ConfigMap says `changed` already; your loop reconciled within five seconds. What has not caught up is the *mount*, and lesson 05 measured exactly this: the kubelet syncs a mounted ConfigMap roughly once a minute. Wait it out:

```bash
sleep 60
kubectl exec deploy/site-hello -- cat /usr/share/nginx/html/index.html
```

There it is. Two independent loops, each correct, with the reader's expectation sitting in the gap between them — which is what almost every "the operator didn't do anything" report turns out to be. The mounted file follows within about a minute without a restart. Your operator inherited that behaviour without implementing it, because it did not invent a mechanism: **it wrote the same objects you would have written by hand.** Every operator you will ever meet is doing this. `cert-manager` writes Secrets. The Gateway controller in Act V wrote a Deployment and a Service, which is why deleting the Gateway garbage-collected them.

```bash
kill %1
```

What real operators add over this script is not architecture — it is the same loop, with informers instead of polling, a work queue, leader election so two replicas do not fight, and `ownerReferences` on everything it creates so deletion cleans up. All of which are optimisations and hygiene around **watch, compare, act.**

### Reading an operator you did not write

Which is the skill you will actually need, because you will meet far more unknown CRDs than you write. There is a fixed procedure, and it works on anything:

```bash
kubectl api-resources --api-group=example.com          # 1. what kinds, what group
kubectl explain website.spec --recursive               # 2. what may I write
kubectl get crd websites.example.com \
  -o jsonpath='{.spec.versions[0].schema.openAPIV3Schema.properties.spec.required}{"\n"}'
kubectl get ws hello -o jsonpath='{.status}{"\n"}'      # 3. what does it tell me
kubectl get ws hello -o yaml | grep -A5 ownerReferences # 4. what did it create
kubectl get pods -A | grep -i controller               # 5. WHOSE loop is this
```

Step five is the one people skip and the one that matters. A custom object that does nothing has exactly two explanations, and they are the same two as a `Pending` Pod in Act VI: either the loop looked and declined — in which case `.status` says so — or **no loop is running at all**, in which case `.status` is absent and there is nothing to read.

```bash
kubectl delete crd websites.example.com
kubectl get deploy,cm
```

Note that last result. Deleting the CRD deleted the `Website`, and the Deployment and ConfigMap **stayed** — because a shell script does not set `ownerReferences`, so nothing links them. That is the hygiene a real operator has and yours does not, and now you have seen the cost of not having it.

> **Check yourself —** A colleague applies a `Certificate` object from a tutorial. `kubectl get certificate` shows it, `kubectl describe` shows no events and an empty status, and no Secret ever appears. They conclude the YAML is wrong. What do you check first, and why is their conclusion unlikely?

<details>
<summary>Answer</summary>

Check whether cert-manager is installed and running: `kubectl get pods -A | grep cert-manager`.

Their conclusion is unlikely because the object was **accepted**. The API server validated it against the CRD's schema and stored it, which means the fields and their types are fine — that is the one thing being stored proves. A genuinely malformed spec would have been rejected at apply time, the way `replicas: 99` was.

An empty `status` and no events is the specific signature of *nobody looked*. Something that looked and disagreed writes a condition or an event saying so; that is what status is for. The absence of both means no loop is watching this kind.

Which is the same diagnostic as Act VI's `Events: <none>` on a Pending Pod, and it generalises to every custom kind you will ever meet: **installing a CRD and installing its controller are two separate acts**, and the CRD alone gives you a perfectly functional place to store objects that nothing will ever read.

</details>

<!-- figure -->

```
   ADDING A KIND = TWO INDEPENDENT HALVES

   THE NOUN: a CustomResourceDefinition
     you extend the API by POSTing an object TO that API.
     stored at /registry/<group>/<plural>/<ns>/<name>  -- same
       filesystem as apps and batch, not a side table (Act VI)
     FOR FREE: REST endpoint, watch stream, uid, resourceVersion,
       kubectl explain, and SERVER-SIDE validation from your
       openAPIV3Schema (curl gets rejected too)
     subresources:
       status: {}   -> a SEPARATE endpoint, so a controller can be
                       allowed to write status and NOT spec
       scale: {}    -> tell it which field is the count, and
                       `kubectl scale` works on your kind
     additionalPrinterColumns -> kubectl has NO knowledge of any
       kind; every table you have ever read came from these

   >>> A CRD EXTENDS THE STORE. IT DOES NOT ADD A LOOP. <<<
       apply one, create an object, and NOTHING runs.

   THE VERB: a controller = watch, compare, act (Act VI)
     ~25 lines of shell is genuinely an operator.
     it re-derives everything every pass, which is WHY it survives
       missed events and restarts: an event handler must be right
       ONCE, a loop only has to be right EVENTUALLY.
     it creates ORDINARY objects -- so it inherits rolling updates,
       ConfigMap refresh, endpoints, all of it, for free.
     real ones add: informers (not polling), a work queue, leader
       election, and ownerReferences so deletion cleans up.

   DIAGNOSING AN UNKNOWN CRD
     object exists + empty status + no events = NOBODY LOOKED.
       (the same signature as Act VI's `Events: <none>`)
     being stored proves the SCHEMA was fine and nothing else.
     installing a CRD and installing its controller are TWO ACTS.
```

**Cleanup:**

```bash
kill %1 2>/dev/null
kubectl delete crd websites.example.com --ignore-not-found
kubectl delete deploy site-hello --ignore-not-found
kubectl delete cm site-hello --ignore-not-found
rm -f /tmp/website-controller.sh
kubectl get crd 2>/dev/null | grep -q example.com && echo "still there" || echo "gone"
```

> **You understand this when you can** explain how a cluster gains a kind, and why that does not
> contradict the last lesson's finding; say what a custom resource's etcd key has that a
> Deployment's does not; explain why an object of your own kind can be created and validated while
> nothing happens at all, and connect it to Act VI's split between the store and the loops;
> describe a controller in three words; and diagnose a custom object with an empty status and no
> events.

**Which raises:** you gave your own kind a `/scale` endpoint, and `kubectl scale` used it — which means something can change a replica count without knowing what it is scaling. You have been typing those counts by hand all act. So what would it take for the cluster to choose the number itself, and what would it have to measure to do that honestly?

---

← Prev: **[GitOps, which you have already built](08b-gitops.md)** · ↑ **[Act VII overview](README.md)** · Next: **[Choosing the number](10-choosing-the-number.md)** →
