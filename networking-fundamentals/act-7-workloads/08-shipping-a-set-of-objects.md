# Shipping a set of objects

Count what the last lesson made you write. A Service and a StatefulSet that had to agree on a label and a name. A Job and a CronJob repeating a Pod template. Every manifest carrying the same image string, the same namespace, the same `app: db` in three places that must match or the object silently selects nothing.

Now scale that to a real application — twenty objects — and add the requirement that made the question urgent: you need the *same* twenty in a staging namespace, with a different image tag, two replicas instead of six, and a different database hostname.

**So: how do you ship a set of objects as one thing, and change one value across all of them without editing twenty files?**

There are exactly two answers in general use, and they are worth meeting together because they disagree with each other at the root — about something as basic as what a manifest *is*. Read them in that spirit: not as two tools with different flags, but as two incompatible bets, each of which buys something the other cannot.

Before either, though, one question that decides how much of this you have to be afraid of.

> **Predict first —** whichever tool you pick, the cluster ends up holding Deployments and Services. Does the API server know which tool produced them? Put it concretely: after you install something with a tool, could a colleague with only `kubectl` tell? Act VI gave you everything you need to answer this.

### What does the cluster see?

```bash
kubectl api-resources | grep -i -E 'chart|release|kustom' ; echo "exit=$?"
```

**Nothing.** There is no `Chart` kind, no `Release` kind, no `Kustomization` kind — and, importantly, neither tool adds one when you use it. Kinds *can* be added to a cluster: Act V's Gateway lesson said so plainly, and the next lesson is about how. But adding one is something you do to the *server*, and these two tools never touch it. They are **client-side**: they run on your laptop, produce exactly the same object bodies you could have typed by hand, and POST those. The cluster receives ordinary YAML from an ordinary client.

That is the single most useful thing to know about this whole topic, and it has consequences you will use all week:

- Anything either tool can do, you could have done by editing files. They are labour-saving devices, not capabilities — which is a real distinction, because the next lesson's subject genuinely *is* a new capability.
- A cluster cannot be "a Helm cluster." Objects from either tool sit next to hand-written ones and the *API server* cannot tell them apart. (Helm does stamp a `app.kubernetes.io/managed-by: Helm` label on what it renders, and you will see it later in this lesson — but that is a label a human chose to write, exactly as you could have. Nothing in the machinery treats it specially.)
- When something is wrong, `kubectl get -o yaml` shows you the truth, and the truth has no templates in it.
- And since the API server has no idea what a release *is*, any tool that wants to remember "what did I install last time" has to store that somewhere itself — in the cluster, as one of the kinds that already exists. Hold onto that; you will find where in a few minutes.

### Answer one: describe a transformation

Start with the one you already have. Kustomize is built into `kubectl`, so there is nothing to install.

```bash
mkdir -p ~/pkg/base ~/pkg/overlays/staging && cd ~/pkg
cat > base/deployment.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: nginx:1.27-alpine
        volumeMounts:
        - name: conf
          mountPath: /etc/web
      volumes:
      - name: conf
        configMap:
          name: web-config
EOF
cat > base/service.yaml <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web
  ports:
  - port: 80
EOF
cat > base/kustomization.yaml <<'EOF'
resources:
- deployment.yaml
- service.yaml
configMapGenerator:
- name: web-config
  literals:
  - LOG_LEVEL=info
EOF
```

Now render it, and notice that rendering is a separate act from applying:

```bash
kubectl kustomize base/
```

**Plain YAML on stdout, and nothing has touched the cluster.** Three objects: your Deployment, your Service, and a ConfigMap you did not write a file for. Look closely at that ConfigMap's name:

```
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-config-hf678c7m2b
```

A **hash suffix**, derived from the content. And then look at what happened to the Deployment that referenced `web-config`:

```bash
kubectl kustomize base/ | grep -A1 'configMap:'
```

**The reference was rewritten to match.** Nobody edited `deployment.yaml`; the renderer parsed both objects, saw one point at the other, and updated the pointer.

Stop here, because this is the feature, not a detail. Lesson 05 left you with an awkward fact: a ConfigMap change reaches a *mounted file* in about a minute, and reaches an *environment variable* never — the only way to pick up a new env var is a new process, which means a rollout, which you have to remember to trigger. A content hash in the name solves that structurally. Change the value:

```bash
sed -i.bak 's/LOG_LEVEL=info/LOG_LEVEL=debug/' base/kustomization.yaml
kubectl kustomize base/ | grep -E 'name: web-config|configMap:' -A1
```

**A different hash, and the Deployment now points at the new name.** Which means the Deployment's Pod template changed, which means — by lesson 02 — applying this *is* a rolling update. Configuration changes and code changes become the same kind of event, and the "I changed the ConfigMap and nothing happened" class of confusion stops existing. You get this by making the config's identity depend on its content.

Now the part that answers the original question. An **overlay** does not copy the base; it points at it and says what is different:

```bash
cat > overlays/staging/kustomization.yaml <<'EOF'
resources:
- ../../base

namePrefix: staging-
namespace: staging

images:
- name: nginx
  newTag: 1.28-alpine

replicas:
- name: web
  count: 1

patches:
- target:
    kind: Deployment
    name: web
  patch: |
    - op: add
      path: /spec/template/spec/containers/0/env
      value:
      - name: DB_HOST
        value: db.staging.svc.cluster.local
EOF
kubectl kustomize overlays/staging/
```

Read the output against the four instructions and each one is visible: every `name` gained a prefix, every object gained a namespace, the image tag moved, `replicas` is `1`, and the container has an `env` block. **The base was not modified and does not know the overlay exists.** Point a second overlay at the same base and the two cannot interfere.

Two things about that file are worth saying out loud because they are where people get stuck.

`namePrefix` renamed the *Service* and the *Deployment* — and the Deployment's selector still says `app: web`, unprefixed. That is correct: a prefix applies to names, not to labels, and the selector has to keep matching the Pods. If it had blindly rewritten labels you would have a Service selecting nothing, which is Act V's most common failure wearing a new hat.

And the `patches` entry contains a **JSON patch** — the `op`/`path`/`value` form you used in lessons 03 and 05. The alternative is to supply a fragment of the object and let it merge, which is what you will see more often. There used to be separate fields for the two (`patchesJson6902` and `patchesStrategicMerge`) and separately a `bases:` field instead of `resources:`. All three are deprecated, and you will meet them constantly in existing repositories: `bases:` becomes `resources:`, and both patch fields become `patches:`.

Apply it, then destroy the evidence:

```bash
kubectl create namespace staging
kubectl apply -k overlays/staging/
kubectl -n staging get deploy,svc,cm
kubectl -n staging get deploy staging-web -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

`kubectl apply -k` renders and applies in one step — and there is no record anywhere that it did. The objects are ordinary objects.

### Answer two: print the YAML from a program

This one needs a binary you do not have. It is the first third-party tool this course has asked you to install since `kind` in Act V, and unlike Kustomize it is not part of `kubectl`:

```bash
helm version --short || brew install helm     # or: see helm.sh/docs/intro/install
```

Worth noting *why* it is a separate binary when Kustomize is not. Kustomize operates on Kubernetes objects, so it was absorbed into the Kubernetes client. Helm operates on text files and keeps its own idea of a "release" that Kubernetes has never heard of — as you are about to discover — so it could not be.

```bash
cd ~ && helm create demo >/dev/null && ls demo demo/templates
```

A **chart**: a directory with `Chart.yaml` (what this is), `values.yaml` (the knobs and their defaults) and `templates/` (the files that get rendered). Look at what a template actually is:

```bash
grep -n 'replicas\|image:' demo/templates/deployment.yaml | head -5
```

```
  replicas: {{ .Values.replicaCount }}
          image: "{{ .Values.image.repository }}:{{ ... }}"
```

**That file is not YAML.** It will not parse; it is a text template that *produces* YAML when the placeholders are filled from `values.yaml`. Which is the opposite bet from the last section: Kustomize parsed real objects and transformed them, and Helm treats the manifest as text right up until the moment it is finished.

Render it without installing anything, so you can see the seam:

```bash
helm template mysite ./demo | head -30
helm template mysite ./demo --set replicaCount=4 | grep -m1 replicas
```

**Ordinary YAML, and `replicas: 4`.** `--set` overrides one value; `-f myvalues.yaml` overrides many, and file order decides who wins. This is the same relationship as `kubectl kustomize` to `kubectl apply -k`: rendering is a local, harmless act, and doing it before you install is the habit that separates people who trust these tools from people who are surprised by them.

Now install, and go looking for the thing the API server does not know about:

```bash
helm install mysite ./demo --namespace staging
helm list --namespace staging
```

> **Predict first —** `helm list` just told you a release name, a revision number, a chart version and a status. None of those are fields on a Deployment, and you established at the start of this lesson that the cluster has no `Release` kind. So where did that answer come from? There are only a few possibilities; pick one before you look.

```bash
kubectl -n staging get secret -l owner=helm
```

```
NAME                          TYPE                 DATA   AGE
sh.helm.release.v1.mysite.v1  helm.sh/release.v1   1      30s
```

**A Secret.** Because Helm needed somewhere in the cluster to remember what it installed, and the available kinds were the ones that already existed — so it uses one of those, with a naming convention carrying the release name and revision, and an invented value in `type` — a field on every Secret that Kubernetes mostly ignores and tools use to label what they put there. Look inside:

```bash
kubectl -n staging get secret -l owner=helm \
  -o jsonpath='{.items[0].data.release}' | base64 -d | base64 -d | gunzip | head -c 300
```

```
{"name":"mysite","info":{"first_deployed":"...","last_deployed":"...",
"description":"Install complete","status":"deployed","notes":"1. Get the application URL...
```

**A JSON record, gzipped and base64'd twice.** Not bare YAML — a *release envelope*, about 20 kB of it, whose top-level keys are `name, info, chart, manifest, hooks, version, namespace`. Two of those are worth pausing on. `manifest` holds the rendered YAML Helm actually sent. `chart` holds **the entire chart** — every template, unrendered.

```bash
kubectl -n staging get secret -l owner=helm \
  -o jsonpath='{.items[0].data.release}' | base64 -d | base64 -d | gunzip \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["manifest"][:300])'
```

*That* is the copy of the YAML it sent. So Helm's memory, per revision, stored in the namespace it sent to, is: what I rendered, and what I rendered it *from*.

Which explains everything about `helm rollback` in one stroke. Upgrade, then look:

```bash
helm upgrade mysite ./demo --set replicaCount=2 --namespace staging
helm list --namespace staging
kubectl -n staging get secret -l owner=helm
```

**Two Secrets now, `.v1` and `.v2`.** A rollback is Helm reading the older Secret and applying the manifest it finds there. Compare that with lesson 02, where you learned that `kubectl rollout undo` is *not* an undo log — it works by scaling an old ReplicaSet back up, which is why the revision numbers go forwards. Helm's rollback genuinely is a stored-copy restore, and it is also *not* an undo log, for a different reason: it replays a manifest, so anything that happened outside Helm is not in the recording and will not be undone.

Which is the failure mode to carry away, and you can produce it:

```bash
kubectl -n staging scale deploy mysite-demo --replicas=7
helm list --namespace staging          # still says deployed, revision 2
kubectl -n staging get deploy mysite-demo
```

**`helm list` says everything is fine, and the cluster does not match the release.** Helm's Secret is a record of what it *sent*, not a description of what *is*; nothing reconciles them, because — as at the top of this lesson — there is no loop in the cluster that has ever heard of a release. The next `helm upgrade` will notice, because it diffs against the stored manifest, and that is the only moment anyone checks.

### Which one, and why the choice is real

The trade-off is not a matter of taste, and you can derive it from the two bets.

Helm treats manifests as **text**, so it can do anything text can do: conditionals, loops, a whole object appearing only if a value is set. That is why every piece of third-party software you install arrives as a chart — the author cannot know your ingress class, your storage class, or whether you want metrics enabled, and templating expresses "maybe" cleanly. The cost is that a template knows nothing about YAML. Get an indent wrong inside a conditional and you produce a document that does not parse, and the error you get is about line 47 of something you never wrote.

Kustomize operates on **parsed objects**, so it cannot produce invalid YAML, and it cannot rewrite a field that does not exist — errors surface as "no such path" while rendering rather than as a broken cluster. It also means your base is a real, applyable manifest that a newcomer can read. The cost is exactly the flexibility Helm has: there is no `if`. "Include this object only in production" is expressed by having a different overlay, not a condition.

Which is why the common arrangement is both: **charts for software other people wrote, overlays for software you wrote.**

> **Check yourself —** A colleague says a chart's `values.yaml` is "the configuration for the app," and that changing a value there is how you reconfigure the running service. What is wrong with that sentence?

<details>
<summary>Answer</summary>

It collapses two different things that this act has deliberately kept apart.

`values.yaml` is input to a **renderer, on your laptop**. Changing it changes nothing at all until you run `helm upgrade`, and what that does is send new object bodies to the API server. It is not read by anything in the cluster, ever.

Whereas "the configuration for the app" in the sense lesson 05 meant it — a value the running process reads — is a **ConfigMap or Secret**, which is a real object with a real reader. That is the thing with the one-minute file refresh and the never-refreshing env var.

The relationship is one-directional: a value in `values.yaml` typically *ends up in* a ConfigMap, via the template. So the sentence describes a real path, but it skips the step where a local file becomes a cluster object — and that step is where every question about "why hasn't my change taken effect" gets answered.

The tell that this matters: `helm get values` and `kubectl get configmap` can disagree, and when they do, the ConfigMap is what the application sees.

</details>

<!-- figure -->

```
   TWO ANSWERS TO "SHIP TWENTY OBJECTS AS ONE THING"

   NEITHER IS A KUBERNETES FEATURE.
     kubectl api-resources has no Chart, no Release, no Kustomization.
     both run on YOUR machine and POST ordinary objects.
     -> nothing in the cluster can tell which tool made an object
     -> anything they do, you could have done by editing files

   KUSTOMIZE  "your YAML is real YAML; describe a TRANSFORMATION"
     built into kubectl. base/ + overlays/, overlay points AT base.
     kubectl kustomize DIR   render only, touches nothing
     kubectl apply -k DIR    render and apply
     namePrefix / namespace / images / replicas / patches
     configMapGenerator -> CONTENT HASH in the name, and the
       Deployment's reference is rewritten to match
       => a config change IS a rollout (lesson 05's problem, solved
          structurally rather than remembered)
     deprecated, everywhere in old repos:
       bases:                  -> resources:
       patchesStrategicMerge:  -> patches:
       patchesJson6902:        -> patches:
     CANNOT: express "if". a condition is a different overlay.

   HELM       "your YAML is a PROGRAM that prints YAML"
     Chart.yaml + values.yaml + templates/ (which do NOT parse as YAML)
     helm template   render only            helm install/upgrade   send it
     --set one value, -f a file, later files win
     state has nowhere to live, so it lives in a SECRET:
       sh.helm.release.v1.<name>.<rev>, type helm.sh/release.v1
       payload = the rendered manifest, gzip + base64 TWICE
     helm rollback = apply the manifest in an older Secret
       -> it replays what Helm SENT. drift made outside Helm is
          invisible until the next upgrade diffs against it.
     CAN: conditionals, loops. CANNOT: guarantee valid YAML.

   the usual arrangement: charts for OTHER PEOPLE'S software,
                          overlays for YOURS.
```

**Cleanup:**

```bash
helm uninstall mysite --namespace staging
kubectl delete -k ~/pkg/overlays/staging/ --ignore-not-found
kubectl delete namespace staging
rm -rf ~/pkg ~/demo
kubectl get ns | grep -q staging && echo "still there" || echo "gone"
```

> **You understand this when you can** explain why no object in a cluster can be identified as Helm-managed or Kustomize-managed by the API server, and what that implies about where to look when something is wrong; say what `kubectl kustomize` and `helm template` have in common and why running them first is a habit worth having; explain what a `configMapGenerator`'s hash accomplishes that lesson 05 said you would otherwise have to remember to do by hand; say where a Helm release's state is stored and why it had to be stored in a kind that already existed; explain why `helm rollback` restores a manifest while `kubectl rollout undo` scales a ReplicaSet, and why neither is an undo log; and state the one thing Helm can express that Kustomize cannot, and the one guarantee Kustomize gives that Helm cannot.

**Which raises:** everything in this lesson reduced to POSTing kinds the server already serves. But Act V's Gateway lesson told you, in one sentence you may have walked past, that `Gateway` and `HTTPRoute` were *not* built in — they were "a kind the API server did not ship with, taught to it at runtime." It even told you what happens when such a kind exists and nothing watches it. So there is a mechanism here that is genuinely not client-side, and a claim of Act V's that you have never actually tested. What does it take to teach the server a kind — and what, exactly, do you get when you do?

---

← Prev: **[When replicas are not interchangeable](07-the-other-workload-kinds.md)** · ↑ **[Act VII overview](README.md)** · Next: **[Adding a kind](09-adding-a-kind.md)** →
