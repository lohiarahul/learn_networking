# kubectl speed

17 tasks in 120 minutes is about **7 minutes each**. Speed is not a virtue in engineering, but it
decides this exam, so this page is drills — no mechanism, no earning the idea. That's what the
[acts](../networking-fundamentals/README.md) are for.

> ## ⚠️ First, unlearn the alias ritual
>
> Nearly every CKA guide opens with:
>
> ```bash
> alias k=kubectl
> export do='--dry-run=client -o yaml'
> export now='--force --grace-period=0'
> ```
>
> **In the current exam environment this is mostly wasted keystrokes.** Two reasons:
>
> 1. **`kubectl`, the `k` alias, and bash completion are already installed** on the SSH hosts. You
>    don't need to create them. (They are *not* on the `base` node — but you don't work there.)
> 2. **Each task has you `ssh` from `base` into a host the task names.** Anything you export or
>    alias **dies when that session ends.** You would be re-typing your own setup 17 times.
>
> Any guide telling you to set these up once at the start, or to switch tasks with
> `kubectl config use-context`, is describing the pre-February-2025 exam. The
> [exam-day page](exam-day.md) covers the SSH model properly.
>
> **The one habit that still pays** is setting the namespace once per session instead of typing
> `-n <ns>` on every command:
>
> ```bash
> kubectl config set-context --current --namespace=<ns>
> ```
>
> Type `$do` out in full as `--dry-run=client -o yaml` and move on. It's 26 characters; the
> re-export costs more.

## Generate, never hand-write

The single biggest time saver. Almost nothing needs to be typed from scratch.

```bash
kubectl run nginx --image=nginx --dry-run=client -o yaml > pod.yaml
kubectl create deployment web --image=nginx --replicas=3 --dry-run=client -o yaml > dep.yaml
kubectl create service clusterip web --tcp=80:8080 --dry-run=client -o yaml
kubectl expose deployment web --port=80 --target-port=8080 --name=web-svc
kubectl create configmap app --from-literal=KEY=val --from-file=./conf/
kubectl create secret generic db --from-literal=password=s3cr3t
kubectl create secret tls example-tls --cert=tls.crt --key=tls.key
kubectl create serviceaccount deploy-bot
kubectl create role reader --verb=get,list,watch --resource=pods
kubectl create rolebinding read-pods --role=reader --serviceaccount=default:deploy-bot
kubectl create clusterrole node-reader --verb=get,list --resource=nodes
kubectl create job hello --image=busybox -- echo hi
kubectl create cronjob nightly --image=busybox --schedule="0 2 * * *" -- echo hi
kubectl create ingress web --rule="host/path=svc:80,tls=my-cert"
kubectl create quota mem --hard=cpu=1,memory=1G,pods=2
kubectl create namespace dev
```

Two that are easy to forget and save real minutes:

```bash
kubectl create token <serviceaccount> --duration=1h     # projected SA token, no Secret needed
kubectl create ingress ...                              # yes, Ingress has a generator
```

## Things with no generator

Be fluent hand-writing these — a 2025 write-up makes the point well that the February-2025
additions increasingly have **no imperative equivalent**, so "just generate it" is no longer a
complete strategy:

- **Gateway API** (`Gateway`, `HTTPRoute`) — copy from `gateway-api.sigs.k8s.io`, which is allowed
- **Kustomize** overlays — and `kustomize.io` is **not** allowed, so from memory
- **Helm values** files
- **NetworkPolicy** — copy the skeleton from the allowed kubernetes.io task page
- **PV / PVC / StorageClass**
- `EncryptionConfiguration`, audit `Policy`, `AdmissionConfiguration` (CKS)

## Read a field without opening the docs

```bash
kubectl explain pod.spec.containers.securityContext --recursive
kubectl explain networkpolicy.spec --recursive | head -40
kubectl api-resources                        # kind -> shortname, apiVersion, namespaced?
kubectl api-versions
```

`kubectl explain --recursive` is faster than a docs round-trip on the laggy remote desktop, and it
works for CRDs too — which is most of the "understand CRDs" competency:

```bash
kubectl get crd
kubectl explain <customkind>.spec --recursive
```

## Extract exactly one value

```bash
kubectl get pod web -o jsonpath='{.status.podIP}'
kubectl get pods -o jsonpath='{.items[*].metadata.name}'
kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}'
kubectl get pods -o custom-columns='NAME:.metadata.name,NODE:.spec.nodeName,IMAGE:.spec.containers[*].image'
kubectl get pods --sort-by=.metadata.creationTimestamp
kubectl get pods --sort-by='.status.containerStatuses[0].restartCount'
kubectl get events --sort-by=.metadata.creationTimestamp
```

Tasks often say "write the result to `/opt/answer.txt`" — pipe straight there and don't retype:

```bash
kubectl get pods -o jsonpath='{.items[*].metadata.name}' > /opt/answer.txt
```

## Selecting and filtering

```bash
kubectl get pods -A --field-selector spec.nodeName=node01
kubectl get pods -l 'env in (prod,staging)'
kubectl get pods --show-labels
kubectl get pods -o wide                     # node + IP, almost always what you want
```

## Fast mutation

```bash
kubectl set image deployment/web nginx=nginx:1.27      # container name must match EXACTLY
kubectl scale deployment/web --replicas=5
kubectl rollout status deployment/web
kubectl rollout history deployment/web
kubectl rollout undo deployment/web --to-revision=2
kubectl rollout restart deployment/web                 # the ONLY way to pick up a ConfigMap change
kubectl label node node01 disk=ssd
kubectl taint node node01 key=value:NoSchedule
kubectl taint node node01 key=value:NoSchedule-        # trailing minus removes it
kubectl annotate pod web note=checked
kubectl patch deployment web -p '{"spec":{"replicas":4}}'
```

`kubectl edit` is fine and often fastest, but on a laggy VNC session a bad edit is expensive. For
anything structural prefer `--dry-run=client -o yaml > f.yaml`, edit the file, `kubectl replace -f`.

## Node maintenance

```bash
kubectl cordon node01
kubectl drain node01 --ignore-daemonsets --delete-emptydir-data
kubectl uncordon node01
```

You will need `--ignore-daemonsets` essentially always. `--delete-emptydir-data` whenever a Pod has
an `emptyDir`. If a drain hangs, suspect a **PodDisruptionBudget**.

## Debugging, in the order that finds things

```bash
kubectl get events --sort-by=.metadata.creationTimestamp | tail -20
kubectl describe pod web | sed -n '/Events/,$p'
kubectl logs web -c sidecar --previous          # --previous is the one people forget
kubectl logs -l app=web --tail=50 --prefix
kubectl exec -it web -- sh
kubectl debug -it web --image=nicolaka/netshoot --target=app
kubectl debug node/node01 -it --image=nicolaka/netshoot --profile=sysadmin
kubectl top pod / kubectl top node             # needs metrics-server
kubectl auth can-i create pods --as=system:serviceaccount:dev:builder
kubectl auth whoami
```

When `kubectl` itself is dead — apiserver down — drop below it:

```bash
sudo crictl ps -a
sudo crictl logs <container-id>
sudo journalctl -u kubelet -n 50 --no-pager
```

That path is worth rehearsing until it's reflex; it is the whole "troubleshoot cluster components"
competency and `kubectl` will not help you.

## Helm

Reported task shapes: add a repo and render a manifest, and **install a chart while excluding CRDs**.

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx && helm repo update
helm search repo ingress-nginx
helm show values ingress-nginx/ingress-nginx | head -40
helm template rel ingress-nginx/ingress-nginx -f values.yaml   # render, no cluster, no install
helm install rel ingress-nginx/ingress-nginx -n web --create-namespace
helm upgrade --install rel ingress-nginx/ingress-nginx --set controller.replicaCount=3
helm list -A
helm history rel -n web
helm rollback rel 1 -n web
helm uninstall rel -n web
```

`--skip-crds` needs a chart that actually has CRDs, and — this is the part that catches people — it
only skips a **`crds/` directory**:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install mon prometheus-community/kube-prometheus-stack \
  -n mon --create-namespace --skip-crds
```

`kube-prometheus-stack` keeps ten CRDs in `charts/crds/crds/`, so the flag removes ten objects from
the install. **On most other charts it removes nothing.** cert-manager, external-secrets and
ingress-nginx have no `crds/` directory at all — cert-manager and external-secrets render their CRDs
from `templates/` behind a value (`crds.enabled`, `installCRDs`), and `--skip-crds` does not look at
`templates/`. If a task says "install this chart without its CRDs", check which convention the chart
uses before reaching for the flag; the answer may be `--set crds.enabled=false`.
[Act VII lesson 08c](../networking-fundamentals/act-7-workloads/08c-when-the-chart-is-not-yours.md)
derives why the two conventions exist.

`helm.sh/docs` is an allowed doc, so you don't have to memorise flags — but you do have to know the
verbs exist.

> **Why not Bitnami.** Every Helm walkthrough written before 2025 — including this one, until it was
> checked — starts `helm repo add bitnami https://charts.bitnami.com/bitnami`. That URL now 302s to
> `repo.broadcom.com/bitnami-files`, and since **28 August 2025** `docker.io/bitnami/*` keeps only
> community-tier `latest` tags: the versioned tags the charts pin moved to `docker.io/bitnamilegacy`
> (archived, unsupported) or the paid `docker.io/bitnamisecure`. `helm template` still renders,
> because it never pulls — but `helm install` can hand you an `ImagePullBackOff` that has nothing to
> do with what you typed. Practise on charts that will still be there.

## Kustomize — the one to over-prepare

`kustomize.io` is **not** an allowed doc. Your only reference is
[one page on kubernetes.io](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/).
Practise until this is from memory:

```yaml
# kustomization.yaml
resources:                 # NOT `bases:` — that field is deprecated
  - ../../base
  - service.yaml
patches:                   # NOT `patchesStrategicMerge:` — also deprecated
  - path: replica-patch.yaml
namePrefix: prod-
namespace: production
commonLabels:
  env: prod
images:
  - name: nginx
    newTag: 1.27
configMapGenerator:
  - name: app-config
    literals:
      - LOG_LEVEL=debug
secretGenerator:
  - name: db-creds
    literals:
      - password=s3cr3t
```

```bash
kubectl kustomize overlays/prod          # render
kubectl apply -k overlays/prod           # apply
```

Note the deprecations: plenty of tutorials (and the material in `~/repos/k8s-learning`) still use
`bases:` and `patchesStrategicMerge:`. Use `resources:` and `patches:`.

## vi, since you have no choice

The INSERT key is disabled — use `i`. Set this up the moment you land on a host:

```vim
:set expandtab tabstop=2 shiftwidth=2
```

YAML indentation errors under 50–100ms keyboard lag are a named failure mode, and a tab in a YAML
file is fatal. Worth having: `:set number`, `:set paste` before pasting, `dd` delete line, `yyp`
duplicate line, `Shift+A` append at end of line, `Shift+C` change to end of line, `gg=G` reindent,
`u` undo, `/pattern` search, `:%s/old/new/g`.

## A checklist for the last week

Time yourself. If any of these takes more than 90 seconds, drill it:

- [ ] Pod with a `securityContext` dropping all capabilities, `runAsNonRoot`, read-only root FS
- [ ] Deployment → change image → verify rollout → roll back one revision
- [ ] Multi-container Pod where one container has a different resource limit
- [ ] NetworkPolicy allowing one namespace *and* one Pod label, denying everything else
- [ ] PVC bound to a manually-created PV (capacity, accessModes, storageClassName all matching)
- [ ] StorageClass with dynamic provisioning, then a PVC that uses it
- [ ] ServiceAccount + Role + RoleBinding, verified with `auth can-i --as=`
- [ ] HPA on a Deployment that actually has `resources.requests` set
- [ ] Node cordon → drain → schedule elsewhere → uncordon
- [ ] Static pod: break `/etc/kubernetes/manifests/kube-apiserver.yaml`, diagnose via `crictl`, fix
- [ ] `etcdctl snapshot save`, then restore it
- [ ] Ingress with TLS → convert it to a `Gateway` + `HTTPRoute`
- [ ] `helm template` a chart, and install one with `--skip-crds`
- [ ] Kustomize base + prod overlay with `namePrefix` and an image tag override, from memory

**CKS additions:**

- [ ] Namespace PSA labels at `restricted`, then a Pod that satisfies them
- [ ] seccomp `Localhost` profile in `/var/lib/kubelet/seccomp/profiles/`
- [ ] AppArmor profile loaded with `apparmor_parser`, applied via `securityContext.appArmorProfile`
- [ ] `EncryptionConfiguration`, then re-encrypt with `kubectl get secrets -A -o json | kubectl replace -f -`
- [ ] Audit policy + apiserver flags **+ the hostPath volume and volumeMount**
- [ ] A Falco rule written from scratch in `falco_rules.local.yaml`
- [ ] `bom generate --image`, then `bom document outline` to read it back
- [ ] `kube-bench run`, then apply one printed remediation and verify with `ps -ef`
- [ ] Cilium WireGuard encryption enabled and verified with `cilium encrypt status`

---

Next: **[exam day](exam-day.md)** — the environment, its friction, and the sweep.
