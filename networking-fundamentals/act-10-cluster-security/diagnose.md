# Diagnose it — Act X

Seven drills. Nothing in this act breaks a cluster, which is precisely what makes it hard: in every drill below, **every component is healthy and every command succeeds.** There is no crash to find, no `CrashLoopBackOff`, no failing probe. The failures are all cases where a control is present, reports itself working, and is not doing the thing somebody believes it is doing.

Act V walked a network path. Act VI descended a dependency stack. Act VII asked which loop read which field. Act VIII had only a verdict. Act IX asked what moment an answer was about. This act's method is four questions, and the order matters:

1. **What exactly does this control take as input?** Not what it is *for* — what field it reads. A rule that reads a tag reads a variable. A rule that reads a label reads something the requester typed.
2. **What is outside its domain?** Every control here is a filter with a scope: a `namespaceSelector`, a `matchImageReferences` glob, a resource list, a set of nodes. The interesting question is never whether it works on what it sees.
3. **Does its declaration match its configuration?** Lesson 03 proved these live at different layers and that the declaration is what everybody reads.
4. **If it stopped working, what would be different?** If the answer is "nothing observable", you have found the bug before it happens.

Question 4 is the one nobody asks, and it is the whole act.

---

## Bench A — a registry you control

Drills 1–3 need lesson 08's bench. Build it once:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

REGTLS="${TMPDIR:-/tmp}/regtls"; mkdir -p "$REGTLS"
openssl req -x509 -newkey rsa:2048 -nodes -days 90 \
  -keyout "$REGTLS/tls.key" -out "$REGTLS/tls.crt" \
  -subj "/CN=registry" -addext "subjectAltName=DNS:registry"
docker run -d --name registry --network kind -v "$REGTLS":/certs \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/tls.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/tls.key registry:2
for n in netlab-control-plane netlab-worker; do
  docker exec $n mkdir -p "/etc/containerd/certs.d/registry:5000"
  docker cp "$REGTLS/tls.crt" "$n:/etc/containerd/certs.d/registry:5000/ca.crt"
  docker exec -i $n sh -c 'cat > "/etc/containerd/certs.d/registry:5000/hosts.toml"' <<'EOF'
server = "https://registry:5000"

[host."https://registry:5000"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/registry:5000/ca.crt"
EOF
done
crane() { docker run --rm --network kind -v "$REGTLS/tls.crt":/ca.crt:ro \
            -e SSL_CERT_FILE=/ca.crt gcr.io/go-containerregistry/crane "$@"; }
crane copy busybox:1.36 registry:5000/app:v1 2>&1 | tail -1
kubectl create ns drill
```

## Drill 1 — the rollback that changed nothing

A team ships `app:v1`. A bad build goes out. They re-push the previous, known-good image to `app:v1` and restart the Deployment. Half the replicas are still broken. Reproduce the shape:

```bash
mk() {
  cat <<EOF | kubectl apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: $1, namespace: drill}
spec:
  nodeName: netlab-worker
  restartPolicy: Never
  containers:
  - {name: c, image: registry:5000/app:v1, imagePullPolicy: $2,
     command: ["sh","-c","busybox | head -1"]}
EOF
  kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/$1 -n drill --timeout=90s >/dev/null
}
mk d1a Always
crane copy busybox:1.37 registry:5000/app:v1 2>&1 | tail -1
crane digest registry:5000/app:v1     # must now be ...9db7b599, not ...73aaf090
mk d1b IfNotPresent
mk d1c Always
kubectl get pods -n drill --sort-by=.metadata.name \
  -o custom-columns='POD:.metadata.name,SPEC:.spec.containers[0].image,POLICY:.spec.containers[0].imagePullPolicy'
for p in d1a d1b d1c; do printf "%-5s " $p; kubectl logs $p -n drill; done
```

**The specs are identical. Explain the outputs, name the one field that would have told you, and say what evidence you would ask the team for.**

<details>
<summary>Answer</summary>

```
registry:5000/app:v1: digest: sha256:9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0
sha256:9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0

POD   SPEC                   POLICY
d1a   registry:5000/app:v1   Always
d1b   registry:5000/app:v1   IfNotPresent
d1c   registry:5000/app:v1   Always
d1a   BusyBox v1.36.1 (2023-05-18 22:34:17 UTC) multi-call binary.
d1b   BusyBox v1.36.1 (2023-05-18 22:34:17 UTC) multi-call binary.
d1c   BusyBox v1.37.0 (2024-09-26 21:31:42 UTC) multi-call binary.
```

That `crane digest` line is not decoration, and it is there because this drill was written after the failure it prevents. If the re-push silently fails — a stale CA in `SSL_CERT_FILE`, a registry that restarted with a new certificate — then all three Pods print `1.36.1`, the drill appears to disprove its own point, and nothing tells you why. **A bench that can fail quietly needs a check that fails loudly**, which is this act's whole subject pointed at the lab.

`d1b` ran the *old* bytes because `IfNotPresent` means "do not ask the registry if you already have something under this name", and the node did. Three Pods, one spec string, two programs.

**The field:** `status.containerStatuses[].imageID`, which is a digest. It is the only place in the API that says what actually ran. `spec.image` is a name to be resolved; the resolution happened on some node at some unrecorded time.

**The evidence to ask for:** not the manifest, not the git diff, not the pipeline log — `kubectl get pods -n <ns> -o custom-columns=POD:.metadata.name,ID:.status.containerStatuses[0].imageID` and a check for whether all replicas share one digest. If they do not, the deploy is not the unit of change you thought it was.

**Why this bites on a rollback specifically:** re-pushing a tag writes nothing to your cluster. No object changed, no event fired, no controller reconciled. A `kubectl rollout restart` recreates Pods with the same spec, and on any node holding a cached copy under that name, `IfNotPresent` reproduces the bug. The nodes that happened not to have it get the fix. "It works on some pods" is the signature.

**The fix, in the order you would actually do it:** pin digests in the manifest (then the reference *is* the content, and `IfNotPresent` becomes correct rather than dangerous); failing that, enable `AlwaysPullImages`, and read drill 2 before you do.

</details>

## Drill 2 — nothing is wrong and nothing will start

You take drill 1's advice and turn on `AlwaysPullImages`. A week later, during a network incident, a scale-up produces no Pods.

```bash
docker exec netlab-control-plane cp /etc/kubernetes/manifests/kube-apiserver.yaml /root/ka.bak
docker exec netlab-control-plane sh -c \
  "sed 's|--enable-admission-plugins=NodeRestriction|--enable-admission-plugins=NodeRestriction,AlwaysPullImages|' \
   /etc/kubernetes/manifests/kube-apiserver.yaml > /etc/kubernetes/manifests/.ka.tmp \
   && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml"
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done

docker exec netlab-worker crictl images | grep "registry:5000/app"
docker stop registry
kubectl run d2 -n drill --restart=Never --image=registry:5000/app:v1 \
  --overrides='{"spec":{"nodeName":"netlab-worker"}}' --command -- sh -c 'busybox | head -1' >/dev/null
sleep 20
kubectl get pod d2 -n drill -o jsonpath='{.spec.containers[0].imagePullPolicy}{"\n"}'
kubectl describe pod d2 -n drill | grep -m1 "Failed to pull"
```

**You did not set `imagePullPolicy`. Read what is stored. Then explain why an image sitting on the node cannot be used, and decide whether to revert.**

<details>
<summary>Answer</summary>

The stored policy is `Always`, and you wrote nothing — `AlwaysPullImages` is a **mutating** admission plugin. It refuses nothing and rewrites a field. So this is lesson 04's mutation mechanism, built in and shipping in every cluster for a decade.

The image is present (`crictl images` shows it) and the Pod cannot start, because `Always` means the registry is consulted on every container start, and the registry is down. `dial tcp: lookup registry ... no such host`.

**Whether to revert is the actual question, and the honest answer is "not on these grounds".** The plugin exists for a reason that has nothing to do with freshness: with `IfNotPresent`, the registry is never consulted, so **its access control is never consulted either.** Any Pod that can name an image another team already pulled onto that node gets to run it, with no `imagePullSecret` and no audit entry at the registry. That is the CIS finding.

So the choices are:

- **Digest-pinned references plus `IfNotPresent`.** Best outcome: content-addressed, no re-point risk, no registry in the container-start path. Does *not* solve the authorisation problem — a digest is still usable by anyone on that node.
- **`AlwaysPullImages`.** Solves authorisation, and puts the registry in the critical path of every Pod start. Then the registry needs the availability of your control plane, and you must know that before an incident rather than during one.

This is the fifth time in the act that adding an authority added a dependency — lesson 04's `failurePolicy: Fail`, lesson 06's KMS, this, lesson 09's key distribution via the API server, lesson 11's secret store. **The dependency is always available less often than the thing it protects.** The diagnosis is not "which is right" but "which failure do you want, and have you tested it".

Revert before the next drill:

```bash
docker start registry
kubectl delete pod d2 -n drill --wait=false
docker exec netlab-control-plane sh -c \
  'cp /root/ka.bak /etc/kubernetes/manifests/.ka.tmp \
   && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml'
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done
```

</details>

## Drill 3 — the signature gate that refuses everything

A team ships image signing. The policy denies every Pod in scope, including images they know they signed. The message mentions signatures, so they are re-signing, rotating keys, and checking the public key by eye. Give them the real diagnosis:

```
Error from server: admission webhook "ivpol.mutate.kyverno.svc-fail" denied the request:
Policy signed-by-us error: failed to update digest: failed to resolve digest for image
registry:5000/app:v2: Get "https://registry:5000/v2/": tls: failed to verify certificate:
x509: certificate signed by unknown authority; GET http://registry:5000/v2/: unexpected
status code 400 Bad Request: Client sent an HTTP request to an HTTPS server.
```

**The nodes pull from this registry perfectly. Nothing else in the cluster has a problem with it. What is wrong, why did their fix attempt make the message worse, and what is the general lesson?**

<details>
<summary>Answer</summary>

Read the message rather than the policy name. `failed to update digest` — it never got as far as verifying anything. It could not **resolve the tag**, because it could not establish TLS to the registry.

**Teaching containerd to trust a CA does not teach the policy engine to trust it.** They are different processes with different trust stores, and the engine talks to the registry *itself* — it has to, because verification needs a network fetch, which is exactly why this cannot be a CEL policy. The nodes are fine because their trust lives in `/etc/containerd/certs.d/`, which the engine has never heard of.

**Why the message got worse:** somebody found `spec.credentials.allowInsecureRegistry: true`, which sounds like "skip TLS verification" and actually means "fall back to plain HTTP". Against an HTTPS-only registry that produces a *second* failure stacked on the first — `Client sent an HTTP request to an HTTPS server`. A flag whose name says insecure and whose effect is a different error.

**The fix** is to give the CA to the engine's Deployment, as a mounted ConfigMap plus `SSL_CERT_FILE` (which every Go program honours):

```bash
kubectl -n kyverno create configmap registry-ca --from-file=ca.crt="$REGTLS/tls.crt"
kubectl -n kyverno patch deploy kyverno-admission-controller --type=strategic -p '{
 "spec":{"template":{"spec":{
   "volumes":[{"name":"registry-ca","configMap":{"name":"registry-ca"}}],
   "containers":[{"name":"kyverno",
     "env":[{"name":"SSL_CERT_FILE","value":"/etc/registry-ca/ca.crt"}],
     "volumeMounts":[{"name":"registry-ca","mountPath":"/etc/registry-ca","readOnly":true}]}]
 }}}}'
```

**The general lessons, and there are two.** First: **read the message, not the flag name** — twice in this drill the words in a name pointed away from the mechanism. Second, and more useful: when a control fails, establish *how far it got* before deciding what failed. "Denied by the signature policy" and "the signature did not verify" are different events with the same user-visible shape, and one of them is not a cryptography problem at all.

</details>

**Tear down bench A:**

```bash
kubectl delete ns drill --ignore-not-found
docker rm -f registry
for n in netlab-control-plane netlab-worker; do
  docker exec $n rm -rf "/etc/containerd/certs.d/registry:5000"
  docker exec $n sh -c 'crictl rmi registry:5000/app 2>/dev/null; true'
done
docker exec netlab-control-plane rm -f /root/ka.bak
rm -rf "$REGTLS"
```

---

## Bench B — a cluster that writes things down

Drills 4 and 5 need lesson 10's audit setup. Build it with the policy as it would be found in a real cluster:

```bash
CP=netlab-control-plane
docker exec $CP cp /etc/kubernetes/manifests/kube-apiserver.yaml /root/ka-audit.bak
docker exec $CP mkdir -p /etc/kubernetes/audit /var/log/kubernetes
docker exec -i $CP sh -c 'cat > /etc/kubernetes/audit/policy.yaml' <<'EOF'
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages: [RequestReceived]
rules:
  - level: None
    users: ["system:kube-scheduler", "system:kube-controller-manager", "system:apiserver"]
  - level: Metadata
EOF
docker exec $CP cat /etc/kubernetes/manifests/kube-apiserver.yaml > /tmp/kad.yaml
python3 - <<'PY'
p="/tmp/kad.yaml"; t=open(p).read()
t = t.replace("    - --allow-privileged=true",
  "    - --allow-privileged=true"
  "\n    - --audit-policy-file=/etc/kubernetes/audit/policy.yaml"
  "\n    - --audit-log-path=/var/log/kubernetes/audit.log", 1)
t = t.replace("    volumeMounts:\n    - mountPath: /etc/ssl/certs",
  "    volumeMounts:"
  "\n    - mountPath: /etc/kubernetes/audit\n      name: ap\n      readOnly: true"
  "\n    - mountPath: /var/log/kubernetes\n      name: al\n      readOnly: false"
  "\n    - mountPath: /etc/ssl/certs", 1)
t = t.replace("  volumes:\n  - hostPath:",
  "  volumes:"
  "\n  - hostPath:\n      path: /etc/kubernetes/audit\n      type: DirectoryOrCreate\n    name: ap"
  "\n  - hostPath:\n      path: /var/log/kubernetes\n      type: DirectoryOrCreate\n    name: al"
  "\n  - hostPath:", 1)
open(p,"w").write(t); print("patched")
PY
docker exec -i $CP sh -c \
  'cat > /etc/kubernetes/manifests/.ka.tmp && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml' \
  < /tmp/kad.yaml
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done
kubectl create ns drill2
kubectl label ns drill2 pod-security.kubernetes.io/enforce=restricted
kubectl -n drill2 wait --for=create serviceaccount/default --timeout=60s
```

That last line matters and is worth a sentence, because without it this drill lies to you. A namespace's `default` ServiceAccount is created by a *controller* after the namespace exists, so for a second or two a brand-new namespace has none — and a Pod created in that window is refused with `error looking up service account drill2/default: serviceaccount "default" not found`. That is a `Forbidden`, from the API server, about a Pod you expected to be refused, for entirely the wrong reason. Act VI's reconciliation loop again: the namespace is not finished when `create` returns.

## Drill 4 — the namespace that stopped being protected

A namespace that has enforced `restricted` for a year now runs privileged Pods. No alert fired. Reproduce it and then find it using only the log:

```bash
kubectl run before -n drill2 --image=busybox:1.36 --restart=Never --command -- true 2>&1 | tail -2
kubectl label ns drill2 pod-security.kubernetes.io/enforce=privileged --overwrite
sleep 3
kubectl run after -n drill2 --image=busybox:1.36 --restart=Never --command -- true 2>&1 | tail -1
kubectl get ns drill2 -o jsonpath='{.metadata.labels}{"\n"}'
kubectl get events -n drill2 -o custom-columns='REASON:.reason,MSG:.message' --no-headers
```

**Nothing refused the change and nothing recorded it as a problem. Find who did it and what they set, from the audit log — then say why the level in bench B's policy is a problem, and what you would change.**

<details>
<summary>Answer</summary>

The `before` Pod is refused with PSA's four-field message; the `after` Pod is created. The label now reads `privileged`, and nothing in the cluster is unhealthy.

Look at what the events say, because it is worse than an empty list:

```
Scheduled   Successfully assigned drill2/after to netlab-worker
Pulling     Pulling image "busybox:1.36"
Pulled      Successfully pulled image "busybox:1.36" in 1.828s
Created     Container created
Started     Container started
```

Five events, all of them reporting the healthy, successful start of the Pod that should have been refused. **Not one event anywhere in the cluster mentions that a control was switched off.** An empty list would at least look like nothing happened; this looks like everything worked.

Finding it:

```bash
docker exec netlab-control-plane sh -c 'grep "\"name\":\"drill2\"" /var/log/kubernetes/audit.log' \
 | python3 -c "
import json,sys
for line in sys.stdin:
    e=json.loads(line)
    if e['verb'] in ('patch','update'):
        print(e['stageTimestamp'], '|', e['verb'], '|', e['user']['username'],
              '| from', e['sourceIPs'], '| code', e['responseStatus']['code'],
              '| level', e['level'])
        print('   body:', json.dumps(e.get('requestObject')))
"
```

You get the who, the when, the source IP and `code: 200`, `decision: allow`. And `body: null` — **because bench B's policy is `level: Metadata`.** You can prove a namespace was patched and you cannot prove what it was patched *to*, which in an investigation is the difference between an audit trail and a rumour.

**The change:** add a rule above the catch-all so that writes keep the request body.

```yaml
  - level: Request
    verbs: ["create", "update", "patch", "delete"]
```

and keep Secrets pinned at `Metadata` above it, because `RequestResponse` on Secrets writes plaintext passwords into that file — lesson 10 measured it, and it is a fourth copy of a value lesson 06 spent an entire lesson protecting.

**The deeper finding, which is what the drill is for:** there was nothing to detect here, because nothing failed. The request was authorised and correct. A control was switched off by a legitimate operation, and the only artifact anywhere in the system is a line in a log — which is why an act full of refusals still needs a control that refuses nothing. If you want an *alert* rather than an investigation, the only place to put it is the log pipeline, keyed on writes to `pod-security.kubernetes.io/*` labels, and somebody has to have thought of that in advance.

</details>

## Drill 5 — what happened inside the shell

An alert says someone exec'd into a production Pod nine hours ago. You have the audit log.

```bash
kubectl run t5 -n drill2 --image=busybox:1.36 --restart=Never --command -- sh -c 'sleep 600' >/dev/null
kubectl wait --for=condition=Ready pod/t5 -n drill2 --timeout=120s >/dev/null
kubectl exec -n drill2 t5 -- sh -c 'cat /etc/passwd | head -1' >/dev/null
printf 'cat /etc/passwd | head -1\nid\nexit\n' | kubectl exec -i -n drill2 t5 -- sh >/dev/null 2>&1
sleep 4
docker exec netlab-control-plane sh -c 'grep "t5/exec" /var/log/kubernetes/audit.log' \
 | python3 -c "
import json,sys,urllib.parse
for line in sys.stdin:
    e=json.loads(line)
    print(e['stage'], '| code', e['responseStatus']['code'])
    print('   ', urllib.parse.unquote(e['requestURI']))
"
```

**Two sessions ran the same commands. Say exactly what you can and cannot establish about each, quote the field that explains the difference, and state what you would need to answer the question properly.**

<details>
<summary>Answer</summary>

The first session's URI contains `command=sh&command=-c&command=cat /etc/passwd | head -1` — fully legible, because `kubectl` puts arguments in the **query string** and the query string is part of the URI.

The second says `command=sh`, and that is all it will ever say. Two commands ran and neither exists in any record.

**The field that explains it: `code: 101`.** Switching Protocols. The API server upgraded the connection to a stream and became a byte pipe between a terminal and a process on a node. It is no longer parsing requests, so there are no requests to log. The log did not lose the commands — it correctly recorded the last moment at which it could see anything.

So the general statement, which is the one to carry: **an audit log is a record of requests to the API server, and nothing else is a request to the API server.**

**What you would need:** a sensor below Kubernetes. A runtime detector on the node sees the `execve` and `openat` syscalls with their actual arguments — lesson 10 measured Falco reporting `command=cat /etc/shadow`, the exact string the audit log did not have.

And the honest limit on *that*, which you should state when you propose it: the runtime alert arrives with `k8s_pod_name=<NA>` and a truncated container ID. The audit log knows *who* and not *what*; the runtime sensor knows *what* and not *who*. An incident is a sentence containing both, so every real investigation is a join on container ID and timestamp — **and its value is bounded by the shorter retention of the two**, plus the lifetime of the Pod object that maps the ID to a name. Nine hours is long enough for that Pod to be gone.

</details>

**Tear down bench B:**

```bash
kubectl delete ns drill2 --ignore-not-found
docker exec netlab-control-plane sh -c \
  'cp /root/ka-audit.bak /etc/kubernetes/manifests/.ka.tmp \
   && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml'
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done
docker exec netlab-control-plane sh -c 'ls -l /var/log/kubernetes/audit.log'
docker exec netlab-control-plane rm -rf /etc/kubernetes/audit /var/log/kubernetes /root/ka-audit.bak
rm -f /tmp/kad.yaml
```

That `ls` is deliberate. Auditing is off, the flags are gone, and the file — including anything it captured — is still on the node.

---

## Drill 6 — a claim to refuse to sign

No cluster needed. A team submits this for sign-off against "all data in transit must be encrypted":

> Cilium with WireGuard encryption is enabled cluster-wide and verified (`cilium-dbg status` reports `Encryption: Wireguard`, peers established on all nodes). A default-deny `NetworkPolicy` is applied in every namespace. TLS terminates at the Ingress with a certificate from our CA. Therefore all traffic is encrypted in transit.

**Find every false or unsupported claim, and name the single cheapest piece of evidence that disproves the headline.**

<details>
<summary>Answer</summary>

The headline word is `all`, and it is false three times over.

**Same-node traffic is plaintext.** Measured in lesson 09 at eight occurrences with encryption confirmed active. What WireGuard encrypts is the link *between* nodes; two co-scheduled Pods have no such link, so there is nothing to encrypt and it correctly encrypts nothing. This is the biggest hole and the one their evidence cannot see, because `cilium-dbg status` is a statement about the node's tunnel, not about a path.

**The gap is non-deterministic**, which is worse than its size. The same Deployment is covered or not depending on where the scheduler put the replicas this morning, so the attestation is not stable across a rollout. `podAntiAffinity` — Act VII's `nodeAffinity` inverted, keeping selected Pods off one node — is the missing control, and nobody writes it down as a security requirement.

**Host-network traffic is not covered.** `NodeEncryption` is a separate setting and was `Disabled` by default; anything on `hostNetwork: true` is outside the scheme.

**The Ingress claim is about the wrong leg.** Act V measured TLS terminating at the Ingress and plaintext going onward to the Pod. It protects the leg you least control and leaves the one inside your trust boundary open.

**And the `NetworkPolicy` is not evidence for this claim at all.** It decides who may open a connection, not who may read one — measured in lesson 09, four plaintext occurrences on the wire while a default-deny policy was provably refusing an unlabelled client.

**The cheapest disproof:** `kubectl get pods -A -o wide` and one pair of communicating Pods on the same node. Thirty seconds, and it is a counterexample to `all` rather than an argument about mechanisms.

**What to volunteer that they did not ask about:** the trust root. Each node's WireGuard public key is published as an annotation on a `CiliumNode` object — no certificate, no chain, no authority — so the confidentiality of every packet depends on who may write that object. The agent's ServiceAccount can `update` any of them, and `NodeRestriction` does not help, twice over: it constrains built-in `Node`/`Pod` resources, and `CiliumNode` is a CRD, and the agent is a ServiceAccount rather than a `system:node:` identity. That turns one node's compromise into every node's traffic, and it appears in no document about encryption. **You cannot evaluate a cryptographic control without evaluating the authorisation on its key distribution.**

The reflex: **"encrypted in transit" is a property of a path, not of a system.** Ask which paths; the honest answer is always shorter than the claim.

</details>

## Drill 7 — the deleted credential that came back

No cluster needed, though lesson 11 measured every step. An incident: a database credential is believed leaked. The runbook says *delete the Kubernetes Secret to revoke access, then rotate*. An engineer runs `kubectl delete secret db-creds -n payments`, confirms it is gone, and reports containment. Twenty minutes later the leaked credential still works.

**Explain, and rewrite the runbook step. Then say what this changes about the team's disaster-recovery assumptions.**

<details>
<summary>Answer</summary>

That Secret is managed by an `ExternalSecret`, so it has an `ownerReference` and a controller reconciling it. Deleting it is **a twenty-second outage followed by the same credential.** Lesson 11 measured it returning at 20 seconds old.

This is Act VI's reconciliation loop doing exactly its job — compare desired to actual, fix the difference — and it does not care that the difference was a human's `kubectl delete`. Act VII taught it through ownership — `drain` would delete a Pod something owned and refused to delete one nothing did — and the deciding field was the same `ownerReference`. The reason it is dangerous here is that the object *looks* like the credential.

**The rewritten step, in order:**

1. **Rotate at the source.** In the external store, because that is where the authoritative copy is. Lesson 11 measured the new value reaching the cluster with no Kubernetes object edited by anyone.
2. **Revoke at the consumer** if you need the credential gone from the cluster now: delete the `ExternalSecret`, which garbage-collects the Secret through that `ownerReference`. Deleting the Secret does not; deleting its owner does.
3. **Then invalidate the old credential at the database**, because rotation creates a new one and does not disable the old.
4. **Then check the store's own audit log** for who read it and from where — including from outside the cluster, which is the part no Kubernetes-side control can see.

**What it changes about DR, and this is the part teams miss.** The secret store is now in the critical path of deployments: any Pod start needing a fresh sync depends on it being reachable. So it belongs on the dependency diagram at the same tier as the API server, and the drill has to include "the store is unavailable, can we scale up".

That is the sibling of lesson 06's finding that an etcd snapshot is no longer a backup once you encrypt — both are cases where **a control that improved confidentiality created an availability dependency that nobody added to the runbook.** Fifth time in the act.

</details>

---

> **The reflex to carry out of these drills.** Every one of them had a healthy cluster, a successful command and a control reporting itself fine. So the question that found the bug was never "what is broken" — it was **what would be different if this control were doing nothing?** If you cannot answer that for a control you own, you do not yet know whether it is working, and neither does anyone else.

---

↑ **[Act X overview](README.md)** · Prev: **[Test yourself](test-yourself.md)** · Next: **[In the wild](in-the-wild.md)** →
