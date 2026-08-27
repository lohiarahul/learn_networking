# What you shipped

Seven lessons have decided what things may do **once they exist**. A capability set for a process that is already running. A seccomp filter on a container that has already been created. A policy on an object that is already being written. A token held by a Pod that is already scheduled.

Not one of them asked where the bytes came from.

That is the far left of the act's timeline — `BUILD`, the moment that knows the contents and nothing whatsoever about where they will run — and it is the only moment you have not touched. It is also the one that gets decided by somebody who has gone home. An image built on a Tuesday afternoon is still running in production two years later, on nodes that did not exist when it was built, under policies nobody had written yet.

Lesson 07 handed you the question in three pieces. Lesson 04 built an image allowlist and then defeated it by typing `docker.io/library/busybox:1.36` instead of `busybox:1.36` — the same bytes under a different name — and said the real answer was a digest and a signature. kube-bench named the same gap from a third direction with a `WARN` about `AlwaysPullImages`. And all three reduce to one question:

> **What does an image tag actually point at, who can change it after you have approved it, and what would it take to state — and have the cluster check — that the thing running is the thing you built?**

It is one question and it takes two lessons, because the two halves are answered by different machinery. This one is about what an image *is* and what you can establish about it yourself: the name, the bytes it currently resolves to, the software inside, and the thing that is inside without being software. [Lesson 08b](08b-who-says-so.md) is about turning any of that into a claim somebody else can check, and about the cluster checking it in the write path.

> **Predict first —** three commitments, and (b) is the one that decides whether the rest of this lesson surprises you. **(a)** You approve `ourregistry/app:v1` after reviewing it. Somebody with push access to that registry later pushes different content under the same tag. Is there any field in your Pod spec, as written, that would now read differently? **(b)** Two Pods, byte-identical specs except `imagePullPolicy` — the field that decides whether the kubelet asks the registry for the image every time (`Always`) or is content with a copy the node already holds (`IfNotPresent`); `Never` is the third value and means exactly that. Same namespace, same node, created a minute apart. Can they run **different programs**? Commit to yes or no. **(c)** A scanner reports zero vulnerabilities. Name two distinct things that could mean, only one of which is "this image has no known vulnerabilities."

### The bench

This lesson and the next need a registry you control, because the whole subject is what happens when somebody changes what a name points at, and you cannot do that to Docker Hub. It also wants that registry to speak TLS, because a real private registry does, and because Act VIII left you able to make a certificate in one line.

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

REGTLS="${TMPDIR:-/tmp}/regtls"; mkdir -p "$REGTLS"
openssl req -x509 -newkey rsa:2048 -nodes -days 90 \
  -keyout "$REGTLS/tls.key" -out "$REGTLS/tls.crt" \
  -subj "/CN=registry" -addext "subjectAltName=DNS:registry"

docker run -d --name registry --network kind \
  -v "$REGTLS":/certs \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/tls.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/tls.key \
  registry:2
```

`--network kind` puts it on the same Docker network as the nodes, where Docker's embedded DNS resolves the container name — so the nodes reach it at `registry:5000`, which is why the certificate's SAN is `DNS:registry` and not `localhost`. That is Act VIII's rule with no exceptions: the name in the certificate is the name the client types.

Now the part that is genuinely instructive. The nodes will refuse that certificate, because nothing signed it that they trust:

```bash
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
docker exec netlab-worker grep -A2 'cri".registry\]' /etc/containerd/config.toml
```

```
[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
```

That last line is why the directory works at all: containerd looks up per-registry configuration under `config_path`, and `kind` sets it for you.

And notice what you just did, because Act VIII spent a section on it. That certificate is self-signed — subject and issuer are the same string — which Act VIII was blunt about: it proves *nothing*, anybody can make one saying anything, in one command. It is not trusted because it signed itself. It is trusted because **you put it in a file that containerd reads.** Act VIII's finding about the 195 root certificates on your laptop was exactly this: every one of them is self-signed too, and *their authority comes entirely from being in the file*. You have just become a trust anchor for two nodes, by copying a file.

Finally, the tools. Three of them, and none needs installing, because each ships as a single-binary container image and this way they run **on the same Docker network as the registry**, which is the only place its name resolves:

```bash
crane()  { docker run --rm --network kind -v "$REGTLS/tls.crt":/ca.crt:ro \
             -e SSL_CERT_FILE=/ca.crt gcr.io/go-containerregistry/crane:v0.21.9 "$@"; }
trivy()  { docker run --rm --network kind -v trivycache:/root/.cache \
             -v "${TMPDIR:-/tmp}":/out aquasec/trivy:0.74.0 "$@"; }
```

**Both are pinned, and this lesson would be dishonest if they were not.** Later in this lesson you
will watch this same `trivy`, at this version, against a frozen database, give two different answers to
one question — and the habit that argument earns is *pin the tool, the version, the database and the
entry point, and treat a change in any of the four as a change in the finding.* A helper that said
`:latest` would be that argument's first counterexample. Use whatever versions are current when you read
this; pin them, and write down which ones you used.

The numbers printed in this lesson came from these two versions against the vulnerability database as it
stood when it was written. If yours are different, nothing has gone wrong — that difference **is** the
lesson. What must not differ is the two halves of a *comparison*, which is what `--skip-db-update` is for.

(A small joke at the pin's expense: `crane version` prints a git commit rather than its own tag, so the
image tag is the only place the version is legible. Pinning is not always the same as being told.)

`SSL_CERT_FILE` is Go's environment variable for "use this file as the trust store instead of the system one." Every tool in this lesson is written in Go, which is why one variable configures all of them — and worth filing away, because the next lesson ends on a component that ignores containerd's trust entirely and has to be told separately.

Verify the bench before building on it:

```bash
crane copy busybox:1.36 registry:5000/app:v1 2>&1 | tail -1
crane digest registry:5000/app:v1
```

```
registry:5000/app:v1: digest: sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
```

### A name, and the thing it currently names

Run it. `busybox` with no arguments prints its own version banner, which makes "which program is this" answerable by looking rather than by reasoning — and pin it to one node, because "which node" is going to matter:

```bash
kubectl create ns supply
kubectl -n supply wait --for=create serviceaccount/default --timeout=60s
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: a1, namespace: supply}
spec:
  nodeName: netlab-worker
  restartPolicy: Never
  containers:
  - name: c
    image: registry:5000/app:v1
    imagePullPolicy: Always
    command: ["sh","-c","busybox | head -1"]
EOF
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/a1 -n supply --timeout=90s
kubectl logs a1 -n supply
kubectl get pod a1 -n supply \
  -o jsonpath='status.image: {.status.containerStatuses[0].image}{"\n"}imageID:      {.status.containerStatuses[0].imageID}{"\n"}'
```

That `wait` is not ceremony. A namespace's `default` ServiceAccount is created by a controller *after* the namespace exists, and lesson 04 measured that every Pod gets that ServiceAccount attached by mutating admission — so a Pod created in the second before the controller catches up is refused with `serviceaccount "default" not found`. Act VI's reconciliation loop, in the smallest place it will ever bite you: `kubectl create ns` returning does not mean the namespace is finished.

```
pod/a1 condition met
BusyBox v1.36.1 (2023-05-18 22:34:17 UTC) multi-call binary.
status.image: docker.io/library/busybox:1.36
imageID:      registry:5000/app@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
```

Stop at `status.image` for a moment, because you did not type that string and there is no registry called `docker.io` in this experiment.

The bytes you pushed were copied out of `busybox:1.36`, so they are *the same bytes* the node already had under that name. containerd's image store is content-addressed — Act I's inodes, one layer up: the content is the thing, the name is a directory entry pointing at it — so when asked to record an image it already holds, it reported the name it knew those bytes by. **The cluster told you the truth about the content and something misleading about its origin**, in a field people read to answer "where did this come from".

The field that cannot mislead you is the one below it. `imageID` is a **digest**, and a digest is not a name at all.

### Three Pods, one spec, two programs

Prediction (b). Somebody with push access changes what the tag points at — which is not an attack, it is the normal way tags are used:

```bash
crane copy busybox:1.37 registry:5000/app:v1 2>&1 | tail -1
crane digest registry:5000/app:v1
```

```
registry:5000/app:v1: digest: sha256:9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0
sha256:9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0
```

Nothing anywhere in your cluster changed. No object was written, no controller ran, no event was recorded. Now create two more Pods, identical to `a1` and to each other in every character except one field:

```bash
mk() {
  cat <<EOF | kubectl apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: $1, namespace: supply}
spec:
  nodeName: netlab-worker
  restartPolicy: Never
  containers:
  - name: c
    image: registry:5000/app:v1
    imagePullPolicy: $2
    command: ["sh","-c","busybox | head -1"]
EOF
  kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/$1 -n supply --timeout=90s >/dev/null
}
mk a2 IfNotPresent
mk a3 Always

kubectl get pods -n supply --sort-by=.metadata.name -o custom-columns=\
'POD:.metadata.name,POLICY:.spec.containers[0].imagePullPolicy,IMAGEID:.status.containerStatuses[0].imageID'
for p in a1 a2 a3; do printf "%-4s " $p; kubectl logs $p -n supply; done
```

```
POD   POLICY         IMAGEID
a1    Always         registry:5000/app@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
a2    IfNotPresent   registry:5000/app@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
a3    Always         registry:5000/app@sha256:9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0
```

```
a1   BusyBox v1.36.1 (2023-05-18 22:34:17 UTC) multi-call binary.
a2   BusyBox v1.36.1 (2023-05-18 22:34:17 UTC) multi-call binary.
a3   BusyBox v1.37.0 (2024-09-26 21:31:42 UTC) multi-call binary.
```

**Different programs.** `a2` and `a3` differ by one word of YAML, ran on the same node in the same minute in the same namespace under the same policies, and executed different binaries — because `IfNotPresent` means *do not ask the registry if you already have something under this name*, and the node did.

So answer prediction (a) properly. Fetch what the API server has stored:

```bash
kubectl get pods a2 a3 -n supply -o jsonpath='{range .items[*]}{.metadata.name}: {.spec.containers[0].image}{"\n"}{end}'
```

```
a2: registry:5000/app:v1
a3: registry:5000/app:v1
```

Identical. **The spec is not a description of what is running.** Every review you have ever done of a Pod spec, every `kubectl diff`, every GitOps repository that is the declared truth of a cluster — all of them are looking at a field that says which *name* to resolve, and the resolution happened elsewhere, at a time nobody recorded, against a registry whose contents have since changed.

Which reframes lesson 04's hole. That lesson defeated an image allowlist by writing the same bytes under a different name, and the fix looked like better string handling. It is not: this is the same defect from the other side — **one name, different bytes** — and no amount of care about the string helps, because the string is fine. Both are the same fact, that a tag is a mutable pointer, and a rule that reads a tag is reading a variable.

### The one reference that is not a variable

You have been staring at the fix for two sections. It is in `imageID`, and you can put it in `spec.image`:

```bash
D1=sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
cat <<EOF | kubectl apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: pinned, namespace: supply}
spec:
  nodeName: netlab-worker
  restartPolicy: Never
  containers:
  - name: c
    image: registry:5000/app@$D1
    command: ["sh","-c","busybox | head -1"]
EOF
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/pinned -n supply --timeout=90s >/dev/null
kubectl logs pinned -n supply
kubectl get pod pinned -n supply -o jsonpath='pullPolicy: {.spec.containers[0].imagePullPolicy}{"\n"}'
```

```
BusyBox v1.36.1 (2023-05-18 22:34:17 UTC) multi-call binary.
pullPolicy: IfNotPresent
```

`name@sha256:…` is **content addressing**, and it is the third time this course has handed you the same idea. Act I: the inode is the file, the name in the directory is a pointer. Act VIII: a hash is a name you cannot lie about, because producing different bytes with the same hash is the thing the function is designed to make impossible. Here: the digest is over the image manifest, which lists the digests of the config and every layer, so pinning one 64-hex string transitively pins every byte.

Note the pull policy it defaulted to. `IfNotPresent` — and that is now the *correct* default rather than a hazard, because "do you already have something under this name" and "do you already have these bytes" have become the same question. A digest reference makes the pull policy stop mattering, which is the clean way to state what the previous section's bug was.

And the failure mode is a refusal rather than a substitution:

```bash
kubectl run bogus -n supply --restart=Never \
  --image=registry:5000/app@sha256:0000000000000000000000000000000000000000000000000000000000000000 \
  --overrides='{"spec":{"nodeName":"netlab-worker"}}' >/dev/null
sleep 12
kubectl get pod bogus -n supply \
  -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}: {.status.containerStatuses[0].state.waiting.message}{"\n"}'
```

```
ErrImagePull: rpc error: code = NotFound desc = failed to pull and unpack image
"registry:5000/app@sha256:0000…0000": failed to resolve reference: not found
```

`not found`. There is nothing a registry can hand back that satisfies that reference except the bytes that hash to it, so the worst it can do is fail. Compare with a tag, where the worst it can do is succeed.

But be precise about what you have bought, because it is narrower than it feels. A digest guarantees **these exact bytes**. It says nothing about whether they are *your* bytes. You copied that digest out of a registry at some point; if the thing you copied it from was already wrong, you have now pinned the wrong thing with great precision, forever. Integrity is not provenance, and the gap between them is the second half of this lesson.

### The plugin kube-bench warned about

`AlwaysPullImages` was one of the `WARN`s in lesson 07's CIS run, and it is the closest thing to a fix for the `a2` hole that the cluster can apply on its own. Turn it on — one flag this time, no volume and no mount, because there is no file to read:

```bash
docker exec netlab-control-plane cp /etc/kubernetes/manifests/kube-apiserver.yaml /root/ka.bak
docker exec netlab-control-plane sh -c \
  "sed 's|--enable-admission-plugins=NodeRestriction|--enable-admission-plugins=NodeRestriction,AlwaysPullImages|' \
   /etc/kubernetes/manifests/kube-apiserver.yaml > /etc/kubernetes/manifests/.ka.tmp \
   && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml"
for i in $(seq 1 30); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && { echo "healthy after $((i*4))s"; break; }
done
```

```
healthy after 44s
```

Now move the tag a third time, so "did it re-pull" is again visible in the payload rather than inferred, and create a Pod that *asks* for the cached copy:

```bash
crane copy busybox:latest registry:5000/app:v1 2>&1 | tail -1
cat <<'EOF' | kubectl apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: a4, namespace: supply}
spec:
  nodeName: netlab-worker
  restartPolicy: Never
  containers:
  - name: c
    image: registry:5000/app:v1
    imagePullPolicy: IfNotPresent
    command: ["sh","-c","busybox | head -1"]
EOF
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/a4 -n supply --timeout=90s >/dev/null
echo "I asked for: IfNotPresent"
kubectl get pod a4 -n supply -o jsonpath='stored:      {.spec.containers[0].imagePullPolicy}{"\n"}'
kubectl logs a4 -n supply
```

```
registry:5000/app:v1: digest: sha256:dc2d74b28e4cf8984fa52af1f39bc7c3d9c73760b41a74d629f5d11b1ab28616
I asked for: IfNotPresent
stored:      Always
BusyBox v1.38.0 (2026-05-13 02:21:49 UTC) multi-call binary.
```

**`AlwaysPullImages` is a mutating admission plugin.** It did not refuse your Pod and it did not check anything — it *rewrote a field you had set* and stored the rewrite, which is lesson 04's `MutatingAdmissionPolicy` in built-in form, shipping in every cluster since long before that API existed. The `a2` hole is closed, and it is closed at the `ADMIT` moment rather than at `CREATE`, by making a later moment's shortcut unavailable.

Two things follow, and the second is the reason the control exists at all.

The first is the price, and it is measurable. Stop the registry, leave the image sitting on the node, and create a Pod:

```bash
docker exec netlab-worker crictl images | grep "registry:5000/app"
docker stop registry
kubectl run a5 -n supply --restart=Never --image=registry:5000/app:v1 \
  --overrides='{"spec":{"nodeName":"netlab-worker"}}' --command -- sh -c 'busybox | head -1' >/dev/null
sleep 20
kubectl describe pod a5 -n supply | grep -m1 -A1 "Failed to pull"
```

```
registry:5000/app     v1     e0e8b3cbfed68     1.93MB
Failed to pull image "registry:5000/app:v1": failed to resolve reference
"registry:5000/app:v1": failed to do request: Head "https://registry:5000/v2/app/manifests/v1":
dial tcp: lookup registry on 192.168.65.254:53: no such host
```

The image is **on the node** and the Pod cannot start. You have made every container start in the cluster depend on the registry being reachable, which is the same trade as lesson 04's `failurePolicy: Fail` and lesson 06's KMS dependency, in a third place: *freshness costs availability*, and this act has now shown you that in the admission path, the decryption path and the image path.

The second is subtler, and it is why the CIS benchmark cares. Look again at what that message proves: with `IfNotPresent`, a container can start from bytes on the node **without the registry being consulted at all**. A registry that is not consulted does not get to apply its access control either. On a shared node, any Pod that can name an image already pulled by some other Pod — in another namespace, belonging to another team, from a registry it holds no credentials for — gets to run it, and the `imagePullSecrets` it does not have (the field naming the Secret a Pod uses to authenticate to a private registry) are never missed. `AlwaysPullImages` exists to make the registry's authorisation apply to every start, not to make the bytes fresher. The freshness is a side effect of asking.

Put the flag back before continuing; the rest of the lesson wants an unmutated pull policy:

```bash
docker start registry
kubectl delete pod a5 -n supply --wait=false >/dev/null
docker exec netlab-control-plane sh -c \
  'cp /root/ka.bak /etc/kubernetes/manifests/.ka.tmp \
   && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml'
for i in $(seq 1 30); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && { echo "healthy after $((i*4))s"; break; }
done
```

### What is in there, and what a scan actually is

You have pinned the bytes. Nothing yet has asked what the bytes *are*. Scan the image you shipped and signed off on:

```bash
trivy image -q --scanners vuln \
  registry:5000/app@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
```

```
2026-08-23T01:35:37Z WARN [report] Supported files for scanner(s) not found. scanners=[vuln]

Report Summary

┌────────┬──────┬─────────────────┐
│ Target │ Type │ Vulnerabilities │
├────────┼──────┼─────────────────┤
│   -    │  -   │        -        │
└────────┴──────┴─────────────────┘
Legend:
- '-': Not scanned
- '0': Clean (no security findings detected)
```

Prediction (c), answered by the tool's own legend. That report is `-`, **not** `0`, and the tool goes out of its way to tell you the difference: *not scanned* versus *clean*. busybox is one static binary with no package database, so there was nothing a package-based scanner knew how to look at. A green pipeline step here means "I found nothing to inspect," and every dashboard that renders it as a tick is lying by rounding.

Now something with contents, and something realistically stale — the version pin is the point, since this is what an image looks like eighteen months after somebody stopped updating it:

```bash
trivy image -q --scanners vuln --severity HIGH,CRITICAL nginx:1.25 | head -8
```

```
Report Summary

┌──────────────────────────┬────────┬─────────────────┐
│          Target          │  Type  │ Vulnerabilities │
├──────────────────────────┼────────┼─────────────────┤
│ nginx:1.25 (debian 12.5) │ debian │       155       │
└──────────────────────────┴────────┴─────────────────┘
```

155 at HIGH or CRITICAL. That number is the one that goes in the ticket, and it is close to meaningless. Take it apart:

```bash
trivy image -q --scanners vuln --severity HIGH,CRITICAL --format json --output /out/scan.json nginx:1.25
python3 - <<'PY'
import json, collections, os
p = os.path.expandvars("${TMPDIR:-/tmp}/scan.json")
v = [x for r in json.load(open(p)).get("Results", []) for x in r.get("Vulnerabilities", [])]
print("findings          :", len(v))
print("distinct CVEs     :", len({x['VulnerabilityID'] for x in v}))
print("have a fix        :", len([x for x in v if x.get('FixedVersion')]))
print("have NO fix       :", len([x for x in v if not x.get('FixedVersion')]))
print("by status         :", dict(collections.Counter(x.get('Status','?') for x in v)))
PY
```

```
findings          : 155
distinct CVEs     : 106
have a fix        : 89
have NO fix       : 66
by status         : {'fixed': 89, 'affected': 48, 'fix_deferred': 14, 'will_not_fix': 4}
```

Four numbers, four different sentences you could put in the ticket:

- **155** findings but **106** distinct CVEs, because one CVE lands on several packages built from one source. Counting findings and calling them vulnerabilities inflates the number by half.
- **89** have a fixed version. Those are work.
- **66** do not. There is no upgrade, no rebuild, no base-image bump that clears them. `will_not_fix` is Debian saying so out loud, and `fix_deferred` is Debian saying "not before the next release."

So an admission rule that says *deny any image with a HIGH finding* denies this image today, tomorrow, and after any amount of diligent work anybody does — and the team will learn, correctly, to switch it off. That is why real gates are written against the number that can go down: `--ignore-unfixed`, plus an explicit, expiring, reviewed list of accepted findings. **A gate you cannot pass is not a strict gate, it is an ex-gate**, and this act has met that shape before in lesson 03's migration verbs.

And every number above has a timestamp, which the tool will tell you if you ask:

```bash
trivy -q version | head -6
```

```
Version: 0.74.0
Vulnerability DB:
  Version: 2
  UpdatedAt: 2026-08-22 18:49:45.818175579 +0000 UTC
  NextUpdate: 2026-08-23 18:49:45.818175378 +0000 UTC
  DownloadedAt: 2026-08-23 01:35:37.708489835 +0000 UTC
```

A scan is a **join**: the packages in the image, against a database of known vulnerabilities, as of a moment. Neither side is a property of the image. The left side is fixed the day you build; the right side changes daily, which is why an image that passed on Tuesday is not passing on Wednesday, it is *unexamined* on Wednesday. Lesson 07 got to this from kube-bench — a scanner tells you what it checked, not what is true, and its authority is bounded by its own version. Here it is again with a second tool and a clock attached.

### The inventory, and whether it agrees with the image

If a scan is a join, one side of it can be written down and shipped. That artifact is an **SBOM**:

```bash
trivy image -q --format cyclonedx --output /out/sbom.json nginx:1.25
python3 - <<'PY'
import json, os
p = os.path.expandvars("${TMPDIR:-/tmp}/sbom.json")
d = json.load(open(p))
print("format     :", d['bomFormat'], d['specVersion'])
print("components :", len(d['components']))
print("size (KB)  :", round(os.path.getsize(p)/1024))
print("nginx      :", next(c['purl'] for c in d['components'] if c['name']=='nginx'))
PY
```

```
format     : CycloneDX 1.7
components : 150
size (KB)  : 307
nginx      : pkg:deb/debian/nginx@1.25.5-1~bookworm?arch=amd64&distro=debian-12.5
```

150 components in 307 KB, each named by a **purl** — a package URL, which is just a naming convention precise enough to join on. And because it is the left side of the join, you can re-run the join later against a newer database, on the SBOM alone, with the image nowhere in sight:

```bash
trivy sbom -q --skip-db-update --severity HIGH,CRITICAL --format json \
  --output /out/sbomscan.json /out/sbom.json
python3 - <<'PY'
import json, os
def s(n):
    p = os.path.expandvars("${TMPDIR:-/tmp}/"+n)
    return {(v['PkgName'], v['VulnerabilityID'])
            for r in json.load(open(p)).get("Results", []) for v in r.get("Vulnerabilities", [])}
img, sbom = s("scan.json"), s("sbomscan.json")
print("from the image :", len(img))
print("from the SBOM  :", len(sbom))
print("only in SBOM   :", sorted(sbom - img))
print("only in image  :", sorted(img - sbom))
PY
```

```
from the image : 155
from the SBOM  : 157
only in SBOM   : [('nginx', 'CVE-2026-42533'), ('nginx', 'CVE-2026-60005')]
only in image  : []
```

Read that twice. **Same tool, same version, same frozen database, same image, two entry points — and two different answers.** The difference is not noise and not a rounding error: it is two HIGH findings on `nginx`, the one package the image exists in order to run.

Before drawing a conclusion, kill the obvious explanation. Maybe the image scan never saw the package:

```bash
trivy image -q --skip-db-update --scanners vuln --list-all-pkgs --format json \
  --output /out/pkgs.json nginx:1.25
python3 - <<'PY'
import json, os
d = json.load(open(os.path.expandvars("${TMPDIR:-/tmp}/pkgs.json")))
for r in d.get('Results', []):
    for p in r.get('Packages', []):
        if p['Name'] == 'nginx':
            print("image scan enumerated:", p['Name'], p['Version'])
            print("with purl            :", (p.get('Identifier') or {}).get('PURL'))
PY
```

```
image scan enumerated: nginx 1.25.5
with purl            : pkg:deb/debian/nginx@1.25.5-1~bookworm?arch=amd64&distro=debian-12.5
```

The image scan enumerated `nginx` with the **byte-identical purl** the SBOM carries, and then reported zero findings against it while the other code path reported two. Both runs used `--skip-db-update` against one cached database, and it reproduces.

Do not over-read this into a diagnosis of one tool's internals — that is not what you measured, and the numbers will differ by version. What you measured is the general fact, and it is the one worth keeping: **a scan is a program's opinion, and two of its own entry points can disagree about the same package.** Lesson 07 taught you not to trust a scanner's completeness. This is stronger and it is uncomfortable: you cannot fully trust its *consistency*, so "we scan our images" is a description of a habit, not of a property. The usable version of the habit is to fix the tool, the version, the database snapshot and the entry point, record all four alongside the result, and treat a change in any of them as a change in the finding.

### The thing no inventory lists

An SBOM enumerates packages. A vulnerability scan joins packages against a database. Both of them are
answers to the question *what software is in here*, and there is a second question they cannot answer
at all: **what else is in here.** The most common wrong answer to that, by a wide margin, is a
credential — and it gets in during the build, from somebody who was trying to be careful.

Here is the shape, in the smallest form that still contains the whole problem. A build needs a token to
fetch a private dependency. The obvious way to hand it in is `ARG`:

```bash
SECDEMO="${TMPDIR:-/tmp}/secdemo"; mkdir -p "$SECDEMO"
printf 'SUPERSECRET_KEY_12345\n' > "$SECDEMO/secret.txt"   # stands in for a real token

cat > "$SECDEMO/Dockerfile.bad" <<'EOF'
FROM alpine
ARG API_KEY
RUN echo "fetching deps with $API_KEY" > /build.log
EOF

docker build -q -t leaky:v1 --build-arg API_KEY="$(cat "$SECDEMO/secret.txt")" \
  -f "$SECDEMO/Dockerfile.bad" "$SECDEMO"
```

The token was never `COPY`d, never written to a file you asked for, and never appears in the
Dockerfile. Now ask the image what it remembers:

```bash
docker history --no-trunc leaky:v1 | grep -o 'SUPERSECRET_KEY_[A-Za-z0-9]*' | head -1
docker run --rm leaky:v1 cat /build.log
```

```
SUPERSECRET_KEY_12345
fetching deps with SUPERSECRET_KEY_12345
```

**Two leaks, and they are different leaks.** The second one you can at least reason about — a command
wrote the value into a file, and the file is a layer. The first is the one that catches people:
`docker history` is reading the *build metadata*, and a `--build-arg` value is recorded there as part
of the command that consumed it. Delete `/build.log`, add a `RUN rm /build.log`, squash the layer you
think is guilty — the history entry is still there, and it travels with the image to every registry it
is ever pushed to. Anyone who can `docker pull` the image can read it, which is the point: **this is
not a filesystem problem, so no filesystem fix reaches it.**

> **Predict first —** BuildKit has a `--secret` mount for exactly this. Before you run it: the token
> has to be readable by the `RUN` command, so it must exist somewhere in the container at that moment.
> Where can it be such that neither the layer nor the history keeps it?

The answer is a mount, and it is the same reasoning as Act IV's — a mount is a thing the kernel
attaches for the life of a process and then detaches, so it is present during the `RUN` and belongs to
no layer:

```bash
cat > "$SECDEMO/Dockerfile.good" <<'EOF'
# syntax=docker/dockerfile:1
FROM alpine
RUN --mount=type=secret,id=apikey \
    KEY=$(cat /run/secrets/apikey) && echo "fetched deps with $KEY" > /build.log
EOF

DOCKER_BUILDKIT=1 docker build -q -t tight:v1 \
  --secret id=apikey,src="$SECDEMO/secret.txt" \
  -f "$SECDEMO/Dockerfile.good" "$SECDEMO"

docker history --no-trunc tight:v1 | grep -c 'SUPERSECRET_KEY'   # 0 — not in the metadata
docker run --rm tight:v1 ls /run/secrets/ 2>&1 | head -1         # gone — not in the filesystem
docker run --rm tight:v1 cat /build.log                          # but the build did read it
```

```
0
ls: /run/secrets/: No such file or directory
fetched deps with SUPERSECRET_KEY_12345
```

Read those three lines together, because separately each one is unremarkable and together they are the
whole control. The history does not have it. The filesystem does not have it. And the build demonstrably
*used* it — `/build.log` proves the `RUN` could read `/run/secrets/apikey` at the moment it ran. The
secret was present exactly once, for exactly one command, and left nothing behind.

**The part that generalises past Docker.** `/run/secrets/apikey` is a path that existed during one
process and does not exist in the result. You have now met that idea three times under three names: the
tmpfs the kubelet mounts for a projected ServiceAccount token, the `emptyDir` that dies with the Pod,
and now a build mount. It is the same trick each time, and it is the only honest way to put a secret
somewhere a program can read it: **make the reading and the existing the same interval.** Anything
longer-lived is a copy, and every copy is a thing somebody has to remember to delete.

Two footnotes worth carrying to an exam and to a code review. First, `ENV` is worse than `ARG`, not
better — an `ARG` at least stops existing after the build, while an `ENV` is written into the image
config and is handed to every process that ever runs in the container, `docker inspect` included.
Second, this is why "we removed the secret in a later layer" is never a fix and why scanning your
*registry* for leaked credentials is a real and separate control from scanning it for vulnerabilities:
the two look in different places, and the SBOM you built above lists neither.

Clean up:

```bash
docker rmi -f leaky:v1 tight:v1 >/dev/null 2>&1
rm -rf "$SECDEMO"
```

Which sets up the real problem. Everything so far — the digest, the scan, the inventory, the credential
you just proved was hiding in the metadata — is something *you* computed about bytes *you* had. None of
it survives being handed to somebody else, because none of it is a **claim anyone is accountable for**.
> **You understand this when you can** produce two Pods with byte-identical specs running different
> programs, and name the one field that distinguishes them; say what a digest establishes and what it
> does not; name two distinct things a scan reporting zero findings can mean; show that two entry
> points of one scanner, against one frozen database, can disagree about one package; and find a
> build secret in an image whose filesystem no longer contains it.

**Leave the bench up.** The registry, the trust file on both nodes and the three helper functions are
also the bench for the next lesson, which begins exactly where the paragraph above ends. If you are
stopping here instead, its last block is the teardown for both.

**Which raises:** everything this lesson computed, it computed for itself. The next one has to make a
claim that survives leaving your laptop — and then get the cluster to check it before a Pod is admitted.

---

↑ **[Act X overview](README.md)** · Prev: **[The doors the cluster leaves open](07-the-doors-left-open.md)** · Next: **[Who says so](08b-who-says-so.md)** →
