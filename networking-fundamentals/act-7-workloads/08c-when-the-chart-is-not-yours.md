# When the chart is not yours

Every chart in this act has been one you wrote. [Lesson 08](08-shipping-a-set-of-objects.md) built
`mysite` from an empty directory, and that is the right way to learn what a chart *is* — a directory
of templates, a `values.yaml`, and a release Secret holding what got sent. It is also not what you
will spend your career doing.

The Helm you actually run is somebody else's. [Act X](../act-10-cluster-security/README.md) installs
three public charts for real — Cilium, Falco, External Secrets — and in each case the whole
interaction is a `--set` and a hope. This lesson is the other half of lesson 08: not writing a chart,
but **reading and operating one you did not write**, which turns out to have a different set of sharp
edges, most of them in the parts of a chart that are not templates at all.

The primitive is the same one this course has used since Act I. Do not ask the tool to summarise;
open the thing on disk:

```bash
helm pull prometheus-community/kube-prometheus-stack --untar
find kube-prometheus-stack -maxdepth 2 -type d
```

`helm show values` prints a values file with the comments stripped of context and
`helm show chart` prints metadata. `--untar` gives you the directory, and the directory tells you
things no `helm show` subcommand will — which is the same argument as reading `/proc/net/tcp`
instead of trusting `netstat`.

Because the first thing worth knowing is that a chart has a directory Helm treats completely
differently from all the others, and nothing in the CLI's output will tell you.

---

## Prediction (a): what `helm template` shows you

Build the smallest chart that has one. This is `demo`, with a `crds/` directory holding a
`CustomResourceDefinition` — the kind [Act VI lesson 01](../act-6-control-plane/01-the-api-server-is-a-filesystem.md)
named as the mechanism by which a cluster gains a new path in its own filesystem — plus one ordinary
template:

```bash
mkdir -p demo/crds demo/templates
cat > demo/Chart.yaml <<'EOF'
apiVersion: v2
name: demo
version: 0.1.0
EOF
cat > demo/crds/widget.yaml <<'EOF'
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: widgets.demo.example
  annotations:
    demo/rendered-version: "{{ .Chart.Version }}"
spec:
  group: demo.example
  scope: Namespaced
  names: { plural: widgets, singular: widget, kind: Widget }
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                size: { type: string }
EOF
cat > demo/templates/cm.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: demo-parent
data:
  version: {{ .Chart.Version | quote }}
EOF
```

Two files, both containing `{{ .Chart.Version }}`, both inside the chart.

> **Predict first —** `helm template demo ./demo`. How many documents come out, and what does the
> CRD's annotation say?

```bash
helm template demo ./demo | grep -c "kind: CustomResourceDefinition"
```

```
0
```

**The CRD is not in the output at all.** Not rendered with an unresolved annotation, not rendered
with the version filled in — absent. The verb the exam calls "render a manifest" does not render this
file. Ask for it explicitly:

```bash
helm template demo ./demo --include-crds | head -8
```

```
---
# Source: demo/crds/widget.yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: widgets.demo.example
  annotations:
    demo/rendered-version: "{{ .Chart.Version }}"
```

Read the last line again. `{{ .Chart.Version }}`, verbatim, in output that has been through the
templating engine. The engine did not skip this file by accident; **`crds/` is not a template
directory.** Helm's own documentation says so in one sentence — CRDs there "are not templated, but
will be installed by default when running a `helm install`" — and installing it proves the point
harder than reading it does:

```bash
helm install demo ./demo -n helmlab --create-namespace
kubectl get crd widgets.demo.example -o jsonpath='{.metadata.annotations}{"\n"}'
```

```
{"demo/rendered-version":"{{ .Chart.Version }}"}
```

Go template syntax, persisted in etcd, served by the API server. There is now an object in your
cluster whose annotation is a program that never ran.

---

## The upgrade that reports success

That is a curiosity. The consequence is not. Change the CRD — a new annotation and a renamed schema
property — bump the chart version, and upgrade:

```bash
sed -i.bak 's|"{{ .Chart.Version }}"|"0.2.0-CHANGED"|' demo/crds/widget.yaml
sed -i.bak 's|size: { type: string }|colour: { type: string }|' demo/crds/widget.yaml
sed -i.bak 's|^version: 0.1.0|version: 0.2.0|'             demo/Chart.yaml
helm upgrade demo ./demo -n helmlab
```

```
Release "demo" has been upgraded. Happy Helming!
NAME: demo
STATUS: deployed
REVISION: 2
```

Deployed. Revision 2. Now ask the cluster:

```bash
kubectl get crd widgets.demo.example \
  -o jsonpath='{.metadata.annotations}{"\n"}{.spec.versions[0].schema.openAPIV3Schema.properties.spec.properties}{"\n"}'
```

```
{"demo/rendered-version":"{{ .Chart.Version }}"}
{"size":{"type":"string"}}
```

**The chart says `colour` and the cluster says `size`, and Helm said success.** Nothing failed,
nothing warned, and `helm list` will report `deployed` for as long as you leave it. From Helm's
documentation, in the same paragraph, and it is worth quoting because it explains rather than
apologises:

> *"There is no support at this time for upgrading or deleting CRDs using Helm. This was an explicit
> decision after much community discussion due to the danger for unintentional data loss."*

Which is a defensible decision and completely reasonable. Deleting a CRD deletes **every custom
object of that kind, cluster-wide**, and a chart is a thing people uninstall by accident. Helm
declines to be the tool that does that. Two consequences follow, and the second one is why this
lesson exists.

**First, `crds/` is install-only in both directions.** Uninstall the release and the CRD stays:

```bash
helm uninstall demo -n helmlab
kubectl get crd widgets.demo.example -o name
```

```
release "demo" uninstalled
customresourcedefinition.apiextensions.k8s.io/widgets.demo.example
```

Still there. It has to be removed by hand, and if you are cleaning up a cluster by uninstalling
charts, `kubectl get crd` is the list of what you missed.

**Second — and this is the derivation that matters — `--skip-crds` now makes sense as a flag rather
than a spell.** `helm install --skip-crds` skips exactly this directory. Nothing else in a chart is
affected by it, because nothing else in a chart is treated this way. Which immediately raises the
question a study sheet cannot answer for you: *does the chart in front of you use `crds/` at all?*

---

## The convention the ecosystem actually picked

Go and look, because the answer is not the one the flag implies. These are the top-level entries of
four charts you are likely to meet:

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo add external-secrets https://charts.external-secrets.io
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

for c in jetstack/cert-manager external-secrets/external-secrets \
         prometheus-community/kube-prometheus-stack ingress-nginx/ingress-nginx; do
  helm pull "$c" --untar
done
ls -d */crds 2>/dev/null || echo "no chart here has a top-level crds/ directory"
ls cert-manager external-secrets kube-prometheus-stack ingress-nginx
```

```
no chart here has a top-level crds/ directory

cert-manager:           Chart.yaml  templates  values.schema.json  values.yaml
external-secrets:       Chart.yaml  templates  values.schema.json  values.yaml
ingress-nginx:          Chart.yaml  templates  values.yaml
kube-prometheus-stack:  Chart.yaml  charts  templates  values.yaml
```

**Not one of the four has a top-level `crds/` directory.** cert-manager, external-secrets and
ingress-nginx ship no such thing at all — and cert-manager and external-secrets are, between them,
responsible for a large fraction of the CRDs in the average cluster. Their CRDs are ordinary
templates:

```bash
ls cert-manager/templates | grep crd
ls external-secrets/templates/crds | head -3
grep -n -A4 '^crds:' cert-manager/values.yaml
```

```
crd-acme.cert-manager.io_challenges.yaml
crd-acme.cert-manager.io_orders.yaml
crd-cert-manager.io_certificaterequests.yaml
...

crds:
  # This option decides if the CRDs should be installed
  # as part of the Helm installation.
  enabled: false
```

Six CRDs in `templates/`, gated by `crds.enabled`, which **defaults to `false`** — so a
`helm install jetstack/cert-manager` with no values installs a controller and none of the kinds it
needs, which is the single most-asked cert-manager question there is. external-secrets does the
opposite: `installCRDs: true` by default, plus a `crds:` map with a boolean per CRD, and its comment
states the whole reason for the convention — *"If set, install **and upgrade** CRDs through helm
chart."*

And `--skip-crds` **does not look at `templates/`**. On all three of those charts the flag is a
silent no-op.

So the two conventions, and the reason for each:

| | CRDs in `crds/` | CRDs in `templates/` behind a value |
|---|---|---|
| rendered by the engine | no — literal text | yes |
| in `helm template` output | only with `--include-crds` | yes |
| installed on `helm install` | yes, unless `--skip-crds` | yes, unless the value says no |
| **updated on `helm upgrade`** | **never** | yes, like any other object |
| removed on `helm uninstall` | never | yes — *which deletes every custom object* |
| how you say "no CRDs" | `--skip-crds` | `--set crds.enabled=false` |

The ecosystem moved to the right-hand column because the left-hand column cannot be upgraded, and
CRDs change with every release of the thing they describe. The cost is the bottom row: those charts
*can* delete your CRDs, which is exactly the data loss Helm's decision was avoiding. So the safety
gets rebuilt one layer up, by hand, in the chart. cert-manager's is worth reading in full, because it
is the clearest statement of the trade-off anywhere in this lesson:

```yaml
  # This option makes it so that the "helm.sh/resource-policy": keep
  # annotation is added to the CRD. This will prevent Helm from uninstalling
  # the CRD when the Helm release is uninstalled.
  # WARNING: when the CRDs are removed, all cert-manager custom resources
  # (Certificates, Issuers, ...) will be removed too by the garbage collector.
  keep: true
```

`helm.sh/resource-policy: keep` on an object tells Helm to leave it alone on uninstall — the same
protection `crds/` gets for free, opted into per-object. It defaults to `true`, and the warning
explains why: without it, `helm uninstall cert-manager` deletes every `Certificate` in the cluster,
and it is the **garbage collector** that does it, not Helm, because the custom objects are owned by
the definition.

And the fourth chart is the one to read properly, because it took the left-hand column and had to
build its way out. `kube-prometheus-stack` has a `charts/` directory:

```bash
find kube-prometheus-stack/charts/crds -maxdepth 2 | head
```

```
kube-prometheus-stack/charts/crds
kube-prometheus-stack/charts/crds/crds        <- ten CRD files, install-only
kube-prometheus-stack/charts/crds/templates
kube-prometheus-stack/charts/crds/templates/upgrade
```

A subchart whose entire purpose is CRDs, holding ten of them in a real `crds/` directory — so
`--skip-crds` genuinely does something on this chart — and, next to it, `templates/upgrade`,
containing a `Job`, a `ServiceAccount`, a `ClusterRole` and a `ClusterRoleBinding`. Read the Job's
annotations:

```yaml
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade,pre-rollback
    "helm.sh/hook-weight": "5"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
```

Two containers: a `busybox` that unpacks the CRDs out of a ConfigMap, and a `kubectl` that applies
them. Gated by `upgradeJob.enabled`, which defaults to `false`.

**The chart hires a Job with cluster-wide CRD permissions to do the one thing Helm refuses to do**,
and ships it switched off. That is not a hack; it is the only available answer, and it tells you what
to expect operationally from any chart in the left-hand column: either you run something like that,
or somebody applies CRDs by hand before each upgrade, or the upgrade quietly does nothing to them —
and the third one is the default.

---

## Prediction (b): what a dry run knows

There is a second reason `helm template` is not a preview, and it bites on real charts because real
charts inspect the cluster. Add a `lookup` to the ConfigMap:

```bash
cat >> demo/templates/cm.yaml <<'EOF'
  kube-system-seen: {{ if (lookup "v1" "Namespace" "" "kube-system") }}"yes"{{ else }}"no"{{ end }}
EOF
```

> **Predict —** `helm template`, `helm install --dry-run`, and `helm install --dry-run=server`.
> Which of the three print `yes`?

```bash
helm template demo ./demo                  | grep kube-system-seen
helm install demo ./demo -n helmlab --dry-run        | grep kube-system-seen
helm install demo ./demo -n helmlab --dry-run=server | grep kube-system-seen
```

```
  kube-system-seen: "no"
  kube-system-seen: "no"
  kube-system-seen: "yes"
```

`kube-system` obviously exists. Two of the three renders say it does not, and one of those two is a
command that contacted the cluster to run. **`--dry-run` is a client-side render**; only
`--dry-run=server` gives the template functions a cluster to look at. If you have ever seen a chart
behave differently on install than its dry run suggested, and the chart contained a `lookup` — which
is how charts decide whether to generate a password or reuse the existing Secret — that is the
mechanism.

Two independent reasons, then, that `helm template` is not what you are about to install: it omits
`crds/`, and its `lookup` calls all return empty. It is a syntax check and a diff source, and it is
excellent at both. It is not a preview.

---

## The values you are allowed to set

The other thing a chart you did not write has is a values surface, and the trap in it is scoping.
Give `demo` a subchart:

```bash
mkdir -p demo/charts/sub/templates
printf 'apiVersion: v2\nname: sub\nversion: 0.1.0\n' > demo/charts/sub/Chart.yaml
printf 'message: sub-default\n'                       > demo/charts/sub/values.yaml
cat > demo/charts/sub/templates/cm.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: demo-sub
data:
  message: {{ .Values.message | quote }}
  env: {{ .Values.global.env | quote }}
EOF
```

and give the parent a `values.yaml`. The `hook:` block is for the next section; put it in now so
every command below renders:

```bash
cat > demo/values.yaml <<'EOF'
message: parent
sub:
  message: child
global:
  env: dev
hook:
  sleep: 0
  exit: 0
EOF
```

Then set things and watch where they land:

```bash
helm template demo ./demo --set message=TOP --set global.env=prod \
  | grep -E "name: demo-|message:|env:"
```

```
  name: demo-sub
  message: "child"
  env: "prod"
  name: demo-parent
  message: "TOP"
  env: "prod"
```

**`--set message=TOP` did not reach the subchart.** A subchart sees only the subtree under its own
name plus `global`, so the parent's `message` and the subchart's `message` are different keys that
happen to be spelled the same. This is the single most common cause of "I set the value and nothing
changed" on a big chart: the value you want is `subchartname.image.tag`, and you set `image.tag`,
which is a real key belonging to something else and was accepted without complaint.

`global` is the exception — the one namespace that crosses the boundary, which is why registry
mirrors and `imagePullSecrets` are conventionally set there. And one sharp edge:

```bash
helm template demo ./demo --set sub.message=null | grep -A2 "name: demo-sub"
```

```
  name: demo-sub
  message:
```

Setting a subchart value to `null` does **not** fall back to the subchart's own default of
`sub-default`. It sets it to empty. Nulling a key removes it from the merged values; it does not
restore the layer beneath.

Two habits for reading a values surface you did not write:

**`values.schema.json`, if it is there, is the real documentation.** cert-manager and
external-secrets both ship one, and it is a JSON Schema that Helm enforces at install time — types,
enums, required keys. It will refuse a typo that `values.yaml`'s comments only warn about.

**Read `values.yaml` on disk rather than `helm show values`.** The comments are the difference. On a
chart the size of `kube-prometheus-stack` the comments are the only place the interactions between
keys are written down.

---

## Prediction (c): the hook that does not finish

The last thing charts you did not write are full of is **hooks** — templates annotated with
`helm.sh/hook`, which Helm applies at a named point in the release lifecycle and waits for. You have
already seen two: `kube-prometheus-stack`'s CRD-upgrade Job, and, in `ingress-nginx`, the Job that
generates its admission webhook's certificate:

```yaml
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
```

A hook is a Job, and a Job is a thing that can fail. Give `demo` a `pre-upgrade` hook whose exit code
you control:

```bash
cat > demo/templates/hook.yaml <<'EOF'
apiVersion: batch/v1
kind: Job
metadata:
  name: demo-pre-upgrade
  annotations:
    "helm.sh/hook": pre-upgrade
    "helm.sh/hook-delete-policy": before-hook-creation
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: check
          image: busybox:1.36
          command: ["sh","-c","echo migrating; sleep {{ .Values.hook.sleep }}; exit {{ .Values.hook.exit }}"]
EOF
```

> **Predict, then** run all three: (1) the hook exits 1; (2) the hook runs longer than `--timeout`;
> (3) the `helm` process itself is killed while the hook runs. For each — what does `helm list` say
> afterwards, and does `helm rollback` work?

**(1) The hook fails.**

```bash
helm upgrade demo ./demo -n helmlab --set hook.exit=1 --set hook.sleep=0
```

```
Error: UPGRADE FAILED: pre-upgrade hooks failed: resource Job/helmlab/demo-pre-upgrade
not ready. status: Failed, message: Job Failed. failed: 1/1
```

`helm list` says `failed`, the history gains a `failed` revision with that message in its
`DESCRIPTION`, and `helm rollback demo 1` works normally. This is the well-behaved case. The one
thing left behind is the Job:

```
NAME               STATUS   COMPLETIONS   AGE
demo-pre-upgrade   Failed   0/1           11s
```

`hook-delete-policy: before-hook-creation` means *delete it before the next one runs* — so a failed
hook's Pod is still there for you to read the logs of, which is the point, and it will accumulate one
per chart until something cleans it up. `hook-succeeded` (as `ingress-nginx` uses) deletes on
success and keeps failures, which is the combination you want.

**(2) The hook outlives the timeout.**

```bash
helm upgrade demo ./demo -n helmlab --set hook.exit=0 --set hook.sleep=300 --timeout 25s
```

```
Error: UPGRADE FAILED: pre-upgrade hooks failed: resource Job/helmlab/demo-pre-upgrade
not ready. status: InProgress, message: Job in progress
context deadline exceeded
```

Also `failed`, also rollback-able. But ask what happened to the Job:

```bash
kubectl -n helmlab get jobs
```

```
NAME               STATUS    COMPLETIONS   DURATION   AGE
demo-pre-upgrade   Running   0/1           37s        37s
```

**Still running.** Helm's timeout is a deadline on Helm's *waiting*, not on the work. There is no
cancellation: the Job is a Kubernetes object and the Job controller has no idea Helm gave up. So a
migration that took longer than `--timeout` is now executing against your database while Helm has
reported `UPGRADE FAILED` and you are deciding whether to roll back. **The rollback and the hook
will run concurrently**, and nothing in either tool will mention it. If a hook does anything
destructive or non-idempotent, read `kubectl get jobs` before you react to a Helm timeout.

**(3) The process dies.** Start the upgrade, kill `helm` while the hook is running, and look:

```bash
helm history demo -n helmlab | tail -1
```

```
6   Fri Aug 28 10:48:28 2026   pending-upgrade   demo-0.2.0   Preparing upgrade
```

```bash
helm upgrade demo ./demo -n helmlab
```

```
Error: UPGRADE FAILED: another operation (install/upgrade/rollback) is in progress
```

**There is no other operation in progress.** The process that held it is dead. `pending-upgrade` is a
state written into the release Secret at the *start* of the upgrade and rewritten at the end, and if
nothing rewrites it, it stays — so the message is not a lie about a running process, it is a report
of a flag nobody cleared. This is the payoff of lesson 08's finding that the release lives in a
Secret: **that Secret is a lock as well as a record**, held by a client that may not exist any more,
in a cluster with nothing whatsoever reconciling it. Nothing will time it out. It will still say that
next week.

`helm rollback demo <last-good>` clears it, and that is the fix worth knowing cold, because the
error message names three verbs and does not tell you that one of them is the way out.

> **Check yourself —** a colleague upgraded a chart from 4.2.0 to 5.0.0. `helm list` says `deployed`,
> `helm history` shows the new revision, the Pods are running the new image, and the operator is
> logging `no matches for kind "ScrapeConfig" in version "monitoring.coreos.com/v1alpha1"`. What
> happened, and what is the fix?

<details>
<summary>Answer</summary>

**The chart's new version added a CRD, and the CRD is in `crds/`, so the upgrade did not install
it.** Everything else in the release upgraded correctly, which is why every status is green: the
Deployment, the ConfigMaps and the RBAC all went through the normal path. `crds/` is install-only,
and this release was *upgraded*, not installed — so the ten CRDs the cluster has are the ten that
existed when somebody first ran `helm install`, and `ScrapeConfig` is the eleventh.

Confirm it in two commands, and note that neither one is a Helm command:

```bash
kubectl get crd | grep monitoring.coreos.com          # what the cluster has
helm pull <repo>/<chart> --version 5.0.0 --untar      # what the chart ships
ls <chart>/charts/crds/crds/ ; ls <chart>/crds/ 2>/dev/null
```

If the second list is longer than the first, that is the whole bug. `helm get manifest` will not show
you this, because CRDs from `crds/` are never in the stored manifest.

**The fix is `kubectl apply`, and the direction matters:**

```bash
kubectl apply --server-side -f <chart>/charts/crds/crds/
```

`--server-side` because CRD manifests routinely exceed the 256 KB annotation limit that client-side
apply uses to store its last-applied state — a `kubectl apply` of a large CRD is the canonical
`metadata.annotations: Too long` failure. Apply, do not delete-and-recreate: deleting a CRD deletes
every object of that kind.

**And the durable version of the fix** is to stop being surprised by it. For any chart with a
`crds/` directory, the upgrade procedure has two steps and Helm only performs one, so either enable
the chart's own CRD-upgrade Job if it ships one (`upgradeJob.enabled=true` on
`kube-prometheus-stack`), or put the `kubectl apply` in front of the `helm upgrade` in whatever runs
your deployments. A chart in this shape does not have a one-command upgrade, and treating it as
though it does is what produces a cluster whose CRDs are three releases behind its controllers.

**The tell to remember:** an operator logging `no matches for kind` about *its own* API group,
against a release Helm reports as healthy, is a CRD-drift symptom almost every time. `helm list` is
reporting on the objects Helm manages, and these are not among them.

</details>

> **You understand this when you can** say what `helm template` leaves out and give two independent
> reasons; explain why `--skip-crds` does nothing on cert-manager; predict what a `helm upgrade` does
> to a CRD in `crds/` and to a CRD in `templates/`, and say which of the two can lose you data;
> explain why `--set image.tag` on a large chart often changes nothing; and say what
> `another operation (install/upgrade/rollback) is in progress` means when nothing is in progress,
> and how to clear it.

**Which raises:** every object in these charts — every `Deployment`, every `ConfigMap`, and the
`Widget` you installed a definition for — was something the API server knew how to store. But you
only added the *definition*. A `Widget` can now be created, and nothing will happen to it. So what
happens when the thing you want to reconcile is not a kind Kubernetes ships — and who writes the loop
then?

---

← Prev: **[GitOps, which you have already built](08b-gitops.md)** · ↑ **[Act VII overview](README.md)** · Next: **[Adding a kind](09-adding-a-kind.md)** →
