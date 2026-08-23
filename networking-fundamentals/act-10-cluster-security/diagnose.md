# Diagnose it — Act X

Eleven drills. Nothing in this act breaks a cluster, which is precisely what makes it hard: in every drill below, **every component is healthy and every command succeeds.** There is no crash to find, no `CrashLoopBackOff`, no failing probe. The failures are all cases where a control is present, reports itself working, and is not doing the thing somebody believes it is doing.

Act V walked a network path. Act VI descended a dependency stack. Act VII asked which loop read which field. Act VIII had only a verdict. Act IX asked what moment an answer was about. This act's method is four questions, and the order matters:

1. **What exactly does this control take as input?** Not what it is *for* — what field it reads. A rule that reads a tag reads a variable. A rule that reads a label reads something the requester typed.
2. **What is outside its domain?** Every control here is a filter with a scope: a `namespaceSelector`, a `matchImageReferences` glob, a resource list, a set of nodes. The interesting question is never whether it works on what it sees.
3. **Does its declaration match its configuration?** Lesson 03 proved these live at different layers and that the declaration is what everybody reads.
4. **If it stopped working, what would be different?** If the answer is "nothing observable", you have found the bug before it happens.

Question 4 is the one nobody asks, and it is the whole act.

---

## The clock

Every drill below carries a **target time**, and this is the one thing these drills do that the
lessons deliberately do not. The course is built to make you understand; a certification is scored on
whether you can act inside a budget, and those are different skills that look identical from the
inside. So: Seven, because that is the number: **17 tasks in 120 minutes** is about seven minutes each, and these drills are the closest thing in the course to a task.

Three rules, taken straight from [the exam-day pacing doctrine](../../exam-prep/exam-day.md):

1. **Start the clock when the symptom appears**, not when you start the reproduce block. Building the
   broken state is setup, and on the exam somebody else has already done it.
2. **At the target, say your best hypothesis out loud** even if you are not confident. Naming a wrong
   hypothesis at 7 minutes is worth more than a right one at twenty, because the wrong one is
   falsifiable in one command and the exam pays for closed tasks.
3. **At 10 minutes, stop and open the reveal.** That is not giving up, it is the exam's own rule —
   *"the moment a task passes 10 minutes, flag it and move on"* — and the skill it builds is the
   costly one. A task that eats 25 minutes has cost you three others worth the same marks.

Run each drill untimed the first time if you like. Then run it again, weeks later, with a timer, and
notice that the second number is the one that predicts anything.

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
            -e SSL_CERT_FILE=/ca.crt gcr.io/go-containerregistry/crane:v0.21.9 "$@"; }
crane copy busybox:1.36 registry:5000/app:v1 2>&1 | tail -1
kubectl create ns drill
```

## Drill 1 — the rollback that changed nothing

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

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

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

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

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

**This one is on paper, and it says so.** Lesson 08 uninstalls Kyverno on its last page, so unless you
skipped that step there is no policy engine in your cluster to reproduce this against. The error string
below is the real one that lesson's bench produced, and diagnosing from a message alone is the drill.
If you would rather run it, put the engine back first — it needs **Kyverno 1.15 or newer**, because
that is where `ImageValidatingPolicy` arrived in `policies.kyverno.io/v1`:

```bash
kubectl apply --server-side \
  -f https://github.com/kyverno/kyverno/releases/download/v1.19.0/install.yaml
kubectl wait --for=condition=Available deploy --all -n kyverno --timeout=300s
kubectl api-resources --api-group=policies.kyverno.io | grep -i image   # ivpol must be listed
```

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
# Runnable only if you reinstalled Kyverno above; $REGTLS comes from bench A.
kubectl -n kyverno create configmap registry-ca --from-file=ca.crt="$REGTLS/tls.crt"
kubectl -n kyverno patch deploy kyverno-admission-controller --type=strategic -p '{
 "spec":{"template":{"spec":{
   "volumes":[{"name":"registry-ca","configMap":{"name":"registry-ca"}}],
   "containers":[{"name":"kyverno",
     "env":[{"name":"SSL_CERT_FILE","value":"/etc/registry-ca/ca.crt"}],
     "volumeMounts":[{"name":"registry-ca","mountPath":"/etc/registry-ca","readOnly":true}]}]
 }}}}'
kubectl -n kyverno rollout status deploy/kyverno-admission-controller --timeout=180s
```

**The general lessons, and there are two.** First: **read the message, not the flag name** — twice in this drill the words in a name pointed away from the mechanism. Second, and more useful: when a control fails, establish *how far it got* before deciding what failed. "Denied by the signature policy" and "the signature did not verify" are different events with the same user-visible shape, and one of them is not a cryptography problem at all.

</details>

**Tear down bench A:**

```bash
kubectl delete ns drill --ignore-not-found
# only if you reinstalled Kyverno for drill 3 — put the cluster back as lesson 08 left it
kubectl delete -f https://github.com/kyverno/kyverno/releases/download/v1.19.0/install.yaml \
  --ignore-not-found 2>/dev/null
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
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"      # same discipline as bench A
kind get kubeconfig --name netlab > "$KUBECONFIG"

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
import sys
p="/tmp/kad.yaml"; t=open(p).read()

def sub(text, anchor, replacement):
    """Replace once, or refuse to write the file at all."""
    if anchor not in text:
        sys.exit("ANCHOR NOT FOUND, manifest NOT patched:\n  " + anchor.replace("\n", "\\n"))
    return text.replace(anchor, replacement, 1)

t = sub(t, "    - --allow-privileged=true",
  "    - --allow-privileged=true"
  "\n    - --audit-policy-file=/etc/kubernetes/audit/policy.yaml"
  "\n    - --audit-log-path=/var/log/kubernetes/audit.log")
t = sub(t, "    volumeMounts:\n    - mountPath: /etc/ssl/certs",
  "    volumeMounts:"
  "\n    - mountPath: /etc/kubernetes/audit\n      name: ap\n      readOnly: true"
  "\n    - mountPath: /var/log/kubernetes\n      name: al\n      readOnly: false"
  "\n    - mountPath: /etc/ssl/certs")
t = sub(t, "  volumes:\n  - hostPath:",
  "  volumes:"
  "\n  - hostPath:\n      path: /etc/kubernetes/audit\n      type: DirectoryOrCreate\n    name: ap"
  "\n  - hostPath:\n      path: /var/log/kubernetes\n      type: DirectoryOrCreate\n    name: al"
  "\n  - hostPath:")

for flag in ("--audit-policy-file=", "--audit-log-path="):
    assert flag in t, flag
open(p,"w").write(t); print("patched: all three anchors matched")
PY
docker exec -i $CP sh -c \
  'cat > /etc/kubernetes/manifests/.ka.tmp && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml' \
  < /tmp/kad.yaml
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done

# The bench is only built if the log actually exists. Prove it before going further.
kubectl get ns >/dev/null                                     # generate one auditable request
docker exec $CP sh -c 'test -s /var/log/kubernetes/audit.log' \
  && echo "bench B ready: audit.log exists and is non-empty" \
  || { echo "BENCH B NOT READY — no audit log. Do not start drills 4 or 5."; }

kubectl create ns drill2
kubectl label ns drill2 pod-security.kubernetes.io/enforce=restricted
kubectl -n drill2 wait --for=create serviceaccount/default --timeout=60s
```

**Read that `bench B ready` line before you go on, and do not skip it.** Drills 4 and 5 are both
answered by grepping the audit log, so a bench that came up without one does not fail — it produces
*empty greps*, and an empty grep in a drill about finding things reads exactly like a finding. This is
drill 1's own rule turned on the bench that hosts drills 4 and 5: a bench that can fail quietly needs a
check that fails loudly. The `sub()` helper in the Python above is the other half of it — if a future
`kubeadm` orders those flags differently, no anchor matches, the script exits without writing, and the
API server is left exactly as it was rather than restarting perfectly with no audit configuration.

That `wait --for=create` line matters and is worth a sentence, because without it this drill lies to you. A namespace's `default` ServiceAccount is created by a *controller* after the namespace exists, so for a second or two a brand-new namespace has none — and a Pod created in that window is refused with `error looking up service account drill2/default: serviceaccount "default" not found`. That is a `Forbidden`, from the API server, about a Pod you expected to be refused, for entirely the wrong reason. Act VI's reconciliation loop again: the namespace is not finished when `create` returns.

## Drill 4 — the namespace that stopped being protected

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

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

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

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

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

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

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

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

## Bench C — a cluster that encrypts its Secrets, allegedly

Drills 8 and 9 need lesson 06's encryption bench, with one difference you are not being told about. Build it exactly as written and do **not** read the `enc.yaml` closely — that is the drill:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
CP=netlab-control-plane

etcd() {
  kubectl -n kube-system exec etcd-$CP -- etcdctl \
    --cacert /etc/kubernetes/pki/etcd/ca.crt \
    --cert   /etc/kubernetes/pki/etcd/server.crt \
    --key    /etc/kubernetes/pki/etcd/server.key "$@"
}

kubectl create ns drill8
kubectl create secret generic legacy-creds -n drill8 --from-literal=password=hunter2

docker exec $CP cp /etc/kubernetes/manifests/kube-apiserver.yaml /root/ka-enc.bak
docker exec $CP mkdir -p /etc/kubernetes/enc
docker exec -i $CP sh -c 'cat > /etc/kubernetes/enc/enc.yaml' <<'EOF'
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources: ["secrets"]
  providers:
  - identity: {}
  - aescbc:
      keys:
      - name: key1
        secret: 8IUDo6/WHRUZiqB9edQrNWWNs11hKjZd0cKifziajkc=
EOF

docker exec $CP cat /etc/kubernetes/manifests/kube-apiserver.yaml > /tmp/ka-enc.yaml
python3 - <<'PYEDIT'
import sys
p="/tmp/ka-enc.yaml"; t=open(p).read()
def sub(text, anchor, replacement):
    if anchor not in text:
        sys.exit("ANCHOR NOT FOUND, manifest NOT patched")
    return text.replace(anchor, replacement, 1)
t = sub(t, "    - --allow-privileged=true",
    "    - --allow-privileged=true"
    "\n    - --encryption-provider-config=/etc/kubernetes/enc/enc.yaml")
t = sub(t, "    volumeMounts:\n    - mountPath: /etc/ssl/certs",
    "    volumeMounts:"
    "\n    - mountPath: /etc/kubernetes/enc\n      name: enc\n      readOnly: true"
    "\n    - mountPath: /etc/ssl/certs")
t = sub(t, "  volumes:\n  - hostPath:",
    "  volumes:"
    "\n  - hostPath:\n      path: /etc/kubernetes/enc\n      type: DirectoryOrCreate"
    "\n    name: enc"
    "\n  - hostPath:")
assert "--encryption-provider-config=" in t
open(p,"w").write(t); print("patched: all three anchors matched")
PYEDIT
docker exec -i $CP sh -c \
  'cat > /etc/kubernetes/manifests/.ka.tmp && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml' \
  < /tmp/ka-enc.yaml
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done

# The bench is only built if the API server came back with the flag. Prove it loudly.
docker exec $CP grep -q -- '--encryption-provider-config=' /etc/kubernetes/manifests/kube-apiserver.yaml \
  && kubectl get --raw /healthz >/dev/null 2>&1 \
  && echo "bench C ready: flag present, API server healthy" \
  || echo "BENCH C NOT READY — do not start drills 8 or 9."
```

## Drill 8 — encryption at rest, configured and signed off

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

A compliance finding said *Secrets must be encrypted at rest*. An engineer generated a 32-byte key, wrote an `EncryptionConfiguration`, mounted it, added `--encryption-provider-config`, restarted the API server cleanly, and closed the ticket with the diff attached. Every one of those steps is correct and the ticket is wrong.

Create a Secret **after** the change — the way anyone verifying would — and look:

```bash
kubectl create secret generic new-creds -n drill8 --from-literal=password=hunter3
etcd get /registry/secrets/drill8/new-creds | grep -ao 'password.*' | head -1
```

**Say what is wrong, why nothing anywhere reported it, and what the fix is in full — including the part that is not the config file.**

<details>
<summary>Answer</summary>

```
password"hunter3
```

Plaintext, in etcd, on a cluster with a valid encryption key and a healthy API server. `kubectl get secret` looks perfect, the flag is present, the file parses, the key is real, and the API server logged nothing.

**The fault is one line of ordering: `identity` is first in `providers`.** Go back and read bench C's `enc.yaml`. `providers` is an ordered list and the order *is* the semantics: **the first provider encrypts; all of them are tried for decryption.** `identity` is the no-op provider — "store as-is" — so putting it first configures a cluster to write everything in plaintext while holding a perfectly good key it will never use to write anything. Lesson 06 measured this exact swap deliberately; here it arrives as somebody's mistake.

Nothing reported it because there is nothing to report. Every component did what it was told. This is the act's fourth question — *if it stopped working, what would be different?* — and the answer for the key is **nothing observable**, which is why the reviewer signing off the diff had no way to catch it from the diff.

**The fix is three things, and only the first is the config file.**

1. **Reverse the providers** so `aescbc` is first and `identity` is last:

```bash
docker exec -i $CP sh -c 'cat > /etc/kubernetes/enc/enc.yaml' <<'EOF'
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources: ["secrets"]
  providers:
  - aescbc:
      keys:
      - name: key1
        secret: 8IUDo6/WHRUZiqB9edQrNWWNs11hKjZd0cKifziajkc=
  - identity: {}
EOF
docker exec $CP sh -c 'touch /etc/kubernetes/manifests/kube-apiserver.yaml'
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done
```

`identity` stays, at the end. Removing it would be the tempting tidy-up and it is wrong: it is the provider that decrypts everything written *before* the fix, and there is a lot of that.

2. **Re-encrypt what already exists.** This is the step people omit, and it is why the fix is not just a restart. Changing the config changes what happens to *future* writes; every existing Secret is still exactly as it was on disk. Force a rewrite of all of them, then prove both:

```bash
kubectl get secrets -A -o json | kubectl replace -f - >/dev/null
etcd get /registry/secrets/drill8/new-creds    | grep -c 'k8s:enc:aescbc:v1:key1'
etcd get /registry/secrets/drill8/legacy-creds | grep -c 'k8s:enc:aescbc:v1:key1'
```

```
1
1
```

Both — including `legacy-creds`, which predates the whole exercise. The prefix is self-describing, so the check is exact rather than a vibe.

3. **Compact and defragment**, because etcd is a versioned store and the plaintext revisions are still in it. Until you compact, `etcdctl get --rev=<old>` returns the plaintext you just "fixed", and so does any snapshot taken in between. Lesson 06 does this step and explains why a snapshot older than the fix is a copy of the problem.

**And the finding worth carrying past the exam:** every check that would have caught this is a check on the *data*, not on the configuration. The flag, the file, the key, the mount and the restart were all verifiable and all fine. `etcd get` is the only thing that answers the actual question. When somebody tells you a control is enabled, the useful reply is not "show me the config" — it is **"show me the stored bytes."**

</details>

## Drill 9 — the namespace that never enforced anything

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

*(Drill 4 handed you the misconfiguration in its reproduce block. This one does not.)*

Three namespaces are handed over from another team as "hardened to `restricted`". You have five minutes and no documentation. Set them up as you received them, then audit them:

```bash
for n in tenant-a tenant-b tenant-c; do kubectl create ns $n >/dev/null; done
kubectl label ns tenant-a pod-security.kubernetes.io/enforce=restricted
kubectl label ns tenant-b pod-security.kubernetes.io/warn=restricted \
                          pod-security.kubernetes.io/audit=restricted
kubectl label ns tenant-c pod-security.kubernetes.io/enforce=restricted \
                          pod-security.kubernetes.io/enforce-version=v1.21
for n in tenant-a tenant-b tenant-c; do
  kubectl -n $n wait --for=create serviceaccount/default --timeout=60s >/dev/null
done
```

**Two of those three namespaces refuse a privileged Pod, and only one of the two is hardened. Say which is which, say what the third does instead, and name the audit that would have missed all of it.**

<details>
<summary>Answer</summary>

Prove it before reading further. Start with the probe everyone reaches for:

```bash
for n in tenant-a tenant-b tenant-c; do
  printf '%-10s ' "$n"
  kubectl -n $n run t --image=busybox:1.36 --restart=Never --privileged \
    --command -- true >/dev/null 2>&1 && echo "ADMITTED" || echo "refused"
done
```

```
tenant-a   refused
tenant-b   ADMITTED
tenant-c   refused
```

**That probe found one problem and cleared one namespace it should not have.** `tenant-b` is caught. `tenant-c` refused, so it looks like `tenant-a`, and if this were the whole audit you would sign it off.

The reason it cleared `tenant-c` is that a privileged container is the *wrong instrument*. `privileged` is forbidden by Baseline and carries **no version annotation at all** — it has been part of the standard since the standard existed, so no `enforce-version` you can write will ever admit it. A version pin can only weaken the controls that were *added* after the pinned version, so the probe has to be a Pod that violates one of those and nothing else.

Two controls became Restricted requirements after PSA first shipped: dropping every capability, in **v1.22**, and refusing an explicit `runAsUser: 0`, in **v1.23**. So build a Pod that satisfies the whole `restricted` standard *except* the capability drop, and ask the same three namespaces again:

```bash
cat > probe.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: probe }
spec:
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: c
      image: busybox:1.36
      command: ["true"]
      securityContext:
        allowPrivilegeEscalation: false
EOF

for n in tenant-a tenant-b tenant-c; do
  printf '%-10s ' "$n"
  kubectl -n $n apply -f probe.yaml >/dev/null 2>&1 && echo "ADMITTED" || echo "refused"
done
```

```
tenant-a   refused
tenant-b   ADMITTED
tenant-c   ADMITTED
```

`tenant-a`'s refusal names the single violation, which is how you know the Pod is compliant in every other respect:

```
Error from server (Forbidden): pods "probe" is forbidden: violates PodSecurity
"restricted:latest": unrestricted capabilities (container "c" must set
securityContext.capabilities.drop=["ALL"])
```

**`tenant-a` is the only one enforcing the standard it claims.**

**`tenant-b` has `warn` and `audit` and no `enforce`.** It is not a hardened namespace, it is a *reporting* namespace. Every violating Pod is admitted, a warning goes to whoever ran the command — where it scrolls past in CI and no human reads it — and an annotation lands in the audit log. This is the correct **first** step of a rollout and a catastrophe as an end state, and it is the most common real PSA misconfiguration there is: somebody turned on the safe mode to measure the blast radius and nobody came back.

**`tenant-c` has `enforce` *and* a version pin of `v1.21`.** `enforce-version` pins which revision of the `restricted` standard is applied, and it is a legitimate field — it is how you stop a cluster upgrade from silently tightening admission under a running workload. It is also how you freeze a policy at a definition that predates every check added since. So the namespace is genuinely enforcing, genuinely reports `restricted`, refuses the probe everybody tries, and enforces a *weaker* `restricted` than the cluster's current one. A pin with no expiry date is a decision nobody revisits.

The two probes are the whole lesson of the drill and they are worth separating. Both were real measurements, both ran against a live admission controller, and the first one produced a **false negative** — not because it was executed badly but because the fault it was looking for was in the one part of the standard that never changes. `restricted:latest` and `restricted:v1.21` agree about `privileged`, about `runAsNonRoot`, about `allowPrivilegeEscalation`, and about `seccompProfile` (a v1.19 addition, so already inside a v1.21 pin). They disagree about exactly two fields, and unless your probe violates one of those two, a pinned namespace is indistinguishable from a current one. **A test that cannot fail is not a test**, which is the same sentence as drill 8's, arriving through a different door.

**The audit that misses all three.** Listing the label:

```bash
kubectl get ns -L pod-security.kubernetes.io/enforce
```

`tenant-a` and `tenant-c` both print `restricted` and look identical; `tenant-b` prints nothing, in a column that is empty for most namespaces anyway. So the enumeration that *feels* like an audit — which namespaces are labelled restricted? — gets one of three right and gives you no signal at all on the other two. Lesson 03 established the deeper version: a namespace can be **exempted** cluster-wide in the `AdmissionConfiguration`, in which case it carries a perfect `enforce=restricted` label and enforces nothing, and no amount of label reading will ever show you that.

**What to check instead, and it is three things rather than one:**

```bash
kubectl get ns -o json | python3 -c "
import json,sys
for n in json.load(sys.stdin)['items']:
    L = n['metadata'].get('labels', {})
    e = L.get('pod-security.kubernetes.io/enforce')
    v = L.get('pod-security.kubernetes.io/enforce-version')
    if e is None or e == 'privileged' or v:
        print(n['metadata']['name'], '-> enforce=%s version=%s' % (e, v))
"
```

...then read the API server's `--admission-control-config-file` for exemptions, and then — the only check that is about behaviour rather than configuration — **try to create a violating Pod**, which is the loop at the top of this answer. Same finding as drill 8, one layer up: the configuration is not the control, and only the attempt tells you what the control does.

</details>

**Tear down bench C:**

```bash
kubectl delete ns drill8 tenant-a tenant-b tenant-c --ignore-not-found
docker exec $CP sh -c \
  'cp /root/ka-enc.bak /etc/kubernetes/manifests/.ka.tmp \
   && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml'
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done
docker exec $CP rm -rf /etc/kubernetes/enc /root/ka-enc.bak
docker exec $CP ls /etc/kubernetes/manifests/     # all four, every time
```


## Drills 10–11 — System Hardening

Nothing to build. Both run on the two-node `netlab` cluster, and both reach a node with `docker exec`,
because that is where the thing they are about lives.

## Drill 10 — the hardening line that is not there

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"We rolled the standard hardened Pod template out across the estate last quarter. It
> passed review, the admission policy accepts it, and every scanner we own calls it compliant. Since
> Tuesday a job that has to `chown` the files it creates fails with `Operation not permitted`. Nobody
> has touched the template. The app team says it is a cluster problem. The platform team says the
> manifest is right — and the manifest is right. Which of them is wrong?"*

**Reproduce it** (run; don't read):

```bash
kubectl create namespace drill10
kubectl -n drill10 apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: chowner }
spec:
  restartPolicy: Never
  containers:
    - name: c
      image: busybox:1.36
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
          add: ["CAP_CHOWN"]
      volumeMounts:
        - { name: work, mountPath: /work }
      command: ["sh","-c","touch /work/f && chown 1000 /work/f && echo CHOWN-OK || echo CHOWN-DENIED"]
  volumes:
    - { name: work, emptyDir: {} }
EOF
sleep 8
kubectl -n drill10 logs chowner
```

```
chown: /work/f: Operation not permitted
CHOWN-DENIED
```

**Your move.** Both teams are describing the same manifest and both descriptions are accurate: the
template asks for exactly one capability and that capability is exactly the one the job needs. The Pod
was accepted with no error, no warning and no event. Start at question 1 of this act's method — *what
does this control take as input?* — and find the one command that shows you what the kernel actually
handed the process, as opposed to what the manifest asked for.

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

The mask, and nothing else, settles it. Two Pods differing in exactly one respect:

```bash
for cap in CAP_CHOWN CHOWN; do
  kubectl -n drill10 apply -f - >/dev/null <<EOF
apiVersion: v1
kind: Pod
metadata: { name: m-$(echo $cap | tr 'A-Z_' 'a-z-') }
spec:
  restartPolicy: Never
  containers:
    - name: c
      image: busybox:1.36
      securityContext:
        capabilities: { drop: ["ALL"], add: ["$cap"] }
      command: ["sh","-c","grep ^CapEff /proc/self/status; touch /f && chown 1000 /f && echo CHOWN-OK || echo CHOWN-DENIED"]
EOF
done
sleep 9
echo "as written:      $(kubectl -n drill10 logs m-cap-chown | tr '\n' ' ')"
echo "prefix removed:  $(kubectl -n drill10 logs m-chown     | tr '\n' ' ')"
```

```
as written:      CapEff:	0000000000000000 chown: /f: Operation not permitted CHOWN-DENIED
prefix removed:  CapEff:	0000000000000001 CHOWN-OK
```

**`CAP_CHOWN` is not a capability name that Kubernetes knows.** The manifest field takes the name
without the prefix — `CHOWN` — and the kernel and `capsh` are the ones that write it as `cap_chown`.
Put the kernel's spelling in the manifest and the string matches nothing the runtime recognises, so it
adds nothing. Bit 0 of `CapEff` is `CAP_CHOWN`; `...0001` is the capability present and `...0000` is the
whole `add:` list evaporating.

Neither team was wrong about anything they said. The platform team's manifest **is** right in the sense
they meant — it names the capability the job needs, in a stanza that drops everything else — and it is a
no-op. That is the entire failure: the field validated, the value did not, and **nothing validates a
capability name.** There is no schema for the contents of that list, so a typo is not a broken Pod, it
is a Pod that reviews as hardened, scans as hardened, and is missing the one permission it was designed
around. You find out when the workload does.

Which is why the answer to *"which of them is wrong?"* is neither, and why that is the uncomfortable
part. Question 4 of this act's method — *if this control stopped working, what would be different?* —
returns **nothing observable** for every `add:` entry in every manifest you own, until something needs
the capability. The only check is the mask:

```bash
kubectl -n <ns> exec <pod> -- grep ^Cap /proc/self/status
```

Four lines, and the one to read is `CapEff`. `getpcaps 1` and `capsh --decode=<hex>` are the friendlier
forms when the container has them; `busybox` does not, and `/proc` always does.

> **Check yourself —** the same template carries a second line whose effect is not where you would look
> for it. `readOnlyRootFilesystem: true` is in that stanza and this Pod never noticed. Which Pods will,
> and what is the fix?

<details>
<summary>Answer</summary>

Any Pod whose process writes outside a mounted volume — and almost every real image does, because
`/tmp` is on the root filesystem. This Pod escaped only because everything it wrote went to `/work`,
which is an `emptyDir` and therefore not part of the read-only root.

```bash
kubectl -n drill10 run rofs --image=busybox:1.36 --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.36","securityContext":{"readOnlyRootFilesystem":true},"command":["sh","-c","echo hi > /tmp/x && echo WROTE || echo FAILED"]}]}}'
sleep 8
kubectl -n drill10 logs rofs
```

```
sh: can't create /tmp/x: Read-only file system
FAILED
```

The fix is not to relax the field, it is to give the writable paths somewhere to be: an `emptyDir`
mounted at `/tmp` — and at `/var/run`, `/var/cache` or wherever the image actually writes, which you
find by running it and reading the errors. Note the message, because it is the distinction lesson 01
drew: `Read-only file system` is the mount, `Operation not permitted` is the capability. Two different
controls, two different words, and the word tells you which one you are fighting.

</details>

</details>

**Tear down:**

```bash
kubectl delete namespace drill10
```

## Drill 11 — the profile that enforces on one node and not the other

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

> **Ticket:** *"Audit asked us to prove that our seccomp profile is blocking what it says it blocks. We
> ran their test on a Pod, it blocked, we sent the screenshot. They ran it themselves on a different
> Pod of the same Deployment and it did not block. Both Pods are Running. Same Deployment, same image,
> same `securityContext` — `kubectl get -o yaml` on the two of them differs in nothing but the name and
> the node. We cannot reproduce their result and they cannot reproduce ours."*

**Reproduce it** (run; don't read):

```bash
kubectl create namespace drill11

docker exec netlab-control-plane sh -c 'mkdir -p /var/lib/kubelet/seccomp/profiles && cat > /var/lib/kubelet/seccomp/profiles/no-mkdir.json <<JSON
{"defaultAction":"SCMP_ACT_ALLOW","syscalls":[{"names":["mkdir","mkdirat"],"action":"SCMP_ACT_ERRNO"}]}
JSON'

docker exec netlab-worker sh -c 'mkdir -p /var/lib/kubelet/seccomp/profiles && cat > /var/lib/kubelet/seccomp/profiles/no-mkdir.json <<JSON
{"defaultAction":"SCMP_ACT_ALLOW"}
JSON'

for node in netlab-control-plane netlab-worker; do
  kubectl -n drill11 apply -f - >/dev/null <<EOF
apiVersion: v1
kind: Pod
metadata: { name: p-${node#netlab-} }
spec:
  nodeName: $node
  restartPolicy: Never
  securityContext:
    seccompProfile: { type: Localhost, localhostProfile: profiles/no-mkdir.json }
  containers:
    - name: c
      image: busybox:1.36
      command: ["sh","-c","mkdir /x 2>&1 && echo MKDIR-OK || echo MKDIR-BLOCKED"]
EOF
done
sleep 10

kubectl -n drill11 get pod -o custom-columns='NAME:.metadata.name,PHASE:.status.phase,NODE:.spec.nodeName,PROFILE:.spec.securityContext.seccompProfile.localhostProfile'
kubectl -n drill11 logs p-control-plane
kubectl -n drill11 logs p-worker
```

```
NAME              PHASE       NODE                   PROFILE
p-control-plane   Succeeded   netlab-control-plane   profiles/no-mkdir.json
p-worker          Succeeded   netlab-worker          profiles/no-mkdir.json

mkdir: can't create directory '/x': Operation not permitted
MKDIR-BLOCKED
MKDIR-OK
```

**Your move.** Both Pods succeeded. Both name the same profile at the same path. Every field the API
server has ever seen about these two Pods is identical. So the difference is not in anything the API
server has, which narrows it to one place — and question 2 of this act's method is the one that gets
you there: *what is outside this control's domain?*

<details>
<summary><b>The diagnosis</b> — open after you've tried</summary>

`localhostProfile` is **a path on a node's filesystem**, and nothing else. It is not a name that
resolves to an object, there is no `kubectl get seccompprofile` for it, and the API server never reads
the file — it stores the string and the kubelet on whichever node wins the scheduling hands the path to
the container runtime. So the value is identical on both Pods and the *thing it points at* is not:

```bash
for n in netlab-control-plane netlab-worker; do
  printf '%-22s ' "$n"
  docker exec $n cat /var/lib/kubelet/seccomp/profiles/no-mkdir.json
done
```

```
netlab-control-plane   {"defaultAction":"SCMP_ACT_ALLOW","syscalls":[{"names":["mkdir","mkdirat"],"action":"SCMP_ACT_ERRNO"}]}
netlab-worker          {"defaultAction":"SCMP_ACT_ALLOW"}
```

One node has the profile. The other has a file of the same name that allows everything. Both Pods are
"running with a Localhost seccomp profile" and one of them is running with a profile that forbids
nothing — and **there is no field, event, condition or annotation anywhere in the cluster that
distinguishes them.** Everybody in the ticket was telling the truth.

Two things follow, and the second is the one worth carrying.

**The scope of a `Localhost` profile is a node, so the state you are trusting is per-node state**, in a
directory somebody has to have populated. Hand-copying it is how the two nodes diverge; the file
missing altogether is the visible version of the same bug, and it fails much more usefully —

```
CreateContainerError: cannot load seccomp profile
"/var/lib/kubelet/seccomp/profiles/audit.json": no such file or directory
```

— because a Pod that will not start gets found. A Pod that starts against the wrong profile does not.
Which is the asymmetry this whole act keeps arriving at: **the loud failure is the safe one.** So ship
profiles with something that reconciles them onto every node — a DaemonSet that writes the directory,
or the Security Profiles Operator, which exists for exactly this and makes the profile a cluster object
with a status you can read.

**And `RuntimeDefault` has none of this problem**, because it names no file. It is the container
runtime's own profile, it is present wherever the runtime is, and it is what `restricted` Pod Security
is satisfied by. `Localhost` is what you reach for when `RuntimeDefault` is too permissive for one
workload — and the moment you reach for it you have taken on a node-state problem that Kubernetes will
not manage for you and will not warn you about.

> **The check, in one line.** For any Pod claiming a `Localhost` profile, the only honest verification
> is to make the container attempt the syscall the profile is supposed to block, **on the node it is
> actually running on.** Reading `spec.securityContext` tells you what was asked for. It has never told
> anybody what happened.

</details>

**Tear down:**

```bash
kubectl delete namespace drill11
docker exec netlab-control-plane rm -f /var/lib/kubelet/seccomp/profiles/no-mkdir.json
docker exec netlab-worker rm -f /var/lib/kubelet/seccomp/profiles/no-mkdir.json
```

---

> **The reflex to carry out of these drills.** Every one of them had a healthy cluster, a successful command and a control reporting itself fine. So the question that found the bug was never "what is broken" — it was **what would be different if this control were doing nothing?** If you cannot answer that for a control you own, you do not yet know whether it is working, and neither does anyone else.

---

↑ **[Act X overview](README.md)** · Prev: **[Test yourself](test-yourself.md)** · Next: **[In the wild](in-the-wild.md)** →
