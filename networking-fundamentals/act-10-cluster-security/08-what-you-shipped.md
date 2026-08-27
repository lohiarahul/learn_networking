# What you shipped

Seven lessons have decided what things may do **once they exist**. A capability set for a process that is already running. A seccomp filter on a container that has already been created. A policy on an object that is already being written. A token held by a Pod that is already scheduled.

Not one of them asked where the bytes came from.

That is the far left of the act's timeline — `BUILD`, the moment that knows the contents and nothing whatsoever about where they will run — and it is the only moment you have not touched. It is also the one that gets decided by somebody who has gone home. An image built on a Tuesday afternoon is still running in production two years later, on nodes that did not exist when it was built, under policies nobody had written yet.

Lesson 07 handed you the question in three pieces. Lesson 04 built an image allowlist and then defeated it by typing `docker.io/library/busybox:1.36` instead of `busybox:1.36` — the same bytes under a different name — and said the real answer was a digest and a signature. kube-bench named the same gap from a third direction with a `WARN` about `AlwaysPullImages`. And all three reduce to one question:

> **What does an image tag actually point at, who can change it after you have approved it, and what would it take to state — and have the cluster check — that the thing running is the thing you built?**

> **Predict first —** four commitments, and (b) is the one that decides whether the rest of this lesson surprises you. **(a)** You approve `ourregistry/app:v1` after reviewing it. Somebody with push access to that registry later pushes different content under the same tag. Is there any field in your Pod spec, as written, that would now read differently? **(b)** Two Pods, byte-identical specs except `imagePullPolicy` — the field that decides whether the kubelet asks the registry for the image every time (`Always`) or is content with a copy the node already holds (`IfNotPresent`); `Never` is the third value and means exactly that. Same namespace, same node, created a minute apart. Can they run **different programs**? Commit to yes or no. **(c)** You sign an image. Where does the signature go — name the place, and say who can write to it. **(d)** A scanner reports zero vulnerabilities. Name two distinct things that could mean, only one of which is "this image has no known vulnerabilities."

### The bench

This lesson needs a registry you control, because the whole subject is what happens when somebody changes what a name points at, and you cannot do that to Docker Hub. It also wants that registry to speak TLS, because a real private registry does, and because Act VIII left you able to make a certificate in one line.

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

**Both are pinned, and this lesson would be dishonest if they were not.** Two hundred lines from here you
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

`SSL_CERT_FILE` is Go's environment variable for "use this file as the trust store instead of the system one." Every tool in this lesson is written in Go, which is why one variable configures all of them — and worth filing away, because in about two hundred lines you will meet a component that ignores containerd's trust entirely and has to be told separately.

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

Prediction (d), answered by the tool's own legend. That report is `-`, **not** `0`, and the tool goes out of its way to tell you the difference: *not scanned* versus *clean*. busybox is one static binary with no package database, so there was nothing a package-based scanner knew how to look at. A green pipeline step here means "I found nothing to inspect," and every dashboard that renders it as a tick is lying by rounding.

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

### Saying who built it

An SBOM is a claim. A scan result is a claim. "This is the image we reviewed" is a claim. Act VIII built the machine for making a claim checkable by someone who was not there: sign it.

```bash
COSIGNDIR="${TMPDIR:-/tmp}/cosign"; mkdir -p "$COSIGNDIR"
cosign() { docker run --rm --network kind \
             -v "$REGTLS/tls.crt":/ca.crt:ro -v "$COSIGNDIR":/work -w /work \
             -e SSL_CERT_FILE=/ca.crt -e COSIGN_PASSWORD="" \
             gcr.io/projectsigstore/cosign:v2.4.1 "$@"; }
cosign generate-key-pair
```

```
Private key written to cosign.key
Public key written to cosign.pub
```

Now prediction (c) — where does a signature go? Look at the repository before and after:

```bash
D1=sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
crane ls registry:5000/app
cosign sign --key cosign.key --tlog-upload=false --yes registry:5000/app@$D1
crane ls registry:5000/app
```

```
v1
Pushing signature to: registry:5000/app
v1
sha256-73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662.sig
```

**The signature is a tag in the same repository as the image**, named by mechanical transformation of the digest it signs — `sha256:` becomes `sha256-`, suffix `.sig`. No new server, no database, no protocol: it exploits the fact that a registry is a content-addressed blob store that will hold anything, so anything that can pull an image can find its signature by computing the name. That is why signing works in air-gapped environments and behind corporate proxies, and it is a genuinely elegant piece of design.

It also answers the second half of the prediction, which matters more: **whoever can push the image can push next to it.** Hold that.

Look inside:

```bash
crane manifest registry:5000/app:sha256-${D1#sha256:}.sig | python3 -m json.tool
```

```json
{
    "schemaVersion": 2,
    "mediaType": "application/vnd.oci.image.manifest.v1+json",
    "config": { "size": 233, "digest": "sha256:706cfff45f44…" },
    "layers": [
        {
            "mediaType": "application/vnd.dev.cosign.simplesigning.v1+json",
            "size": 233,
            "digest": "sha256:4629222496a7…",
            "annotations": {
                "dev.cosignproject.cosign/signature": "MEUCIQDYNCnyfEyLRVWcrUH88QqJLIVRmk+g6uCSkIUp6r7J/gIgcqq17w9jcW7BA6ohBbw/CKd/X6xdBK/kScuh4t9it/A="
            }
        }
    ]
}
```

A 233-byte payload and an ECDSA signature in an annotation. Now verify, and read what comes back:

```bash
cosign verify --key cosign.pub --insecure-ignore-tlog=true registry:5000/app@$D1
```

```
[{"critical":{"identity":{"docker-reference":"registry:5000/app"},
"image":{"docker-manifest-digest":"sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"},
"type":"cosign container image signature"},"optional":null}]

Verification for registry:5000/app@sha256:73aaf090… --
The following checks were performed on each of these signatures:
  - The cosign claims were validated
  - The signatures were verified against the specified public key
```

Those 233 bytes are the whole thing, and they are worth reading as a sentence. The signed document is **a tiny JSON statement naming a digest**. Nobody signed 1.9 MB of image; they signed a hash, and the hash stands in for the bytes because Act VIII's collision resistance says it may. This is exactly the shape of a certificate — a short assertion about a key, signed — and exactly the shape of `etcd`'s content addressing, and by now that recurrence should feel less like a coincidence and more like the only way anyone builds these things.

Then the measurement that answers lesson 07's question directly. The tag `v1` has been moved three times since you signed; verify **the tag**:

```bash
cosign verify --key cosign.pub --insecure-ignore-tlog=true registry:5000/app:v1
```

```
Error: no signatures found
```

**A re-pointed tag fails verification without anyone having to notice it moved.** Not because the tooling watches tags — it does not, and it cannot — but because verification resolves the tag to content and then looks for a signature *over that content*. The mutability that made `a2` and `a3` run different programs is the same mutability that makes this fail closed. You do not need a control that detects tag changes; you need one that is indifferent to them.

And a signature is not a mood:

```bash
cosign generate-key-pair --output-key-prefix attacker >/dev/null
cosign verify --key attacker.pub --insecure-ignore-tlog=true registry:5000/app@$D1 2>&1 | tail -1
```

```
Error: no matching signatures: invalid signature when validating ASN.1 encoded signature
```

### Whose key, and the thing you have not verified

Here is the trap, and it is the one the README promised: **a signature verified against a key anybody can push to.** You already have both halves. Signatures live in the registry, next to the image, writable by anyone with push access. So let somebody with push access sign the *unsigned* content with their own key:

```bash
D2=sha256:dc2d74b28e4cf8984fa52af1f39bc7c3d9c73760b41a74d629f5d11b1ab28616
cosign sign --key attacker.key --tlog-upload=false --yes registry:5000/app@$D2
crane ls registry:5000/app
cosign verify --key attacker.pub --insecure-ignore-tlog=true registry:5000/app@$D2 2>&1 | grep -c "verified against"
```

```
Pushing signature to: registry:5000/app
v1
v2
sha256-73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662.sig
sha256-dc2d74b28e4cf8984fa52af1f39bc7c3d9c73760b41a74d629f5d11b1ab28616.sig
1
```

Two signatures, side by side, both valid, in the repository your cluster pulls from. The registry stored the second without a murmur — it is a blob store and it was asked to store a blob. And the second one verifies perfectly, because it *is* a perfectly good signature.

So the sentence "the image is signed" carries no information at all. What carries information is "the image is signed **by a key we decided in advance to trust**", and the entire security of the scheme is in the phrase you were about to leave out. What an attacker with push access can do is *add*; what they cannot do is produce a signature that verifies against a key they do not hold. That is the whole guarantee, and it is enough — but only if the verifier names the key.

Which is why the industry moved off long-lived keys, and where Act IX walks back in. A key in a file has the problems Act IX catalogued for every credential: somebody has to hold it, rotate it, and not paste it into a CI log. **Keyless signing** replaces it with an identity:

- the signer authenticates to an OIDC provider — Act IX's flow, exactly, and in CI the token is the workflow's own identity, not a person's
- a CA called **Fulcio** issues a short-lived certificate binding that verified identity to a fresh key, which is [Act VIII lesson 05](../act-8-trust/05-certificates.md) — where you signed a certificate as your own CA — run as a service
- the signature and certificate are recorded in **Rekor**, an append-only transparency log, so a signature that exists can be shown to have existed and cannot be quietly withdrawn

And the verification changes shape. There is no key to name, so you name **who** and **which issuer** — `--certificate-identity` and `--certificate-oidc-issuer`. Get those wrong and you have rebuilt the bug above with more machinery: a verifier that accepts any Fulcio certificate accepts anybody who can log in to GitHub, which is everybody.

This lab cannot demonstrate that, because Fulcio and Rekor are internet services and this cluster is a laptop. But notice that you have not been running a clean verification either — `--tlog-upload=false` on the way in and `--insecure-ignore-tlog=true` on the way out, and cosign's own warning names the cost:

```
WARNING: Skipping tlog verification is an insecure practice that lacks of transparency
and auditability verification for the signature.
```

What the transparency log buys is a question the signature alone cannot answer: **when**. A signature over a digest is timeless. If a key is compromised on Friday, every signature it ever made is suspect, and without a log there is no way to say which ones existed before Friday — so the incident is "revoke and rebuild everything" rather than "revoke and rebuild what came after". Sit with that for the next lesson-and-a-half, because it is the same missing ingredient — an ordered record of what happened — that lesson 10 is entirely about.

### Having the cluster check

You can verify signatures on your laptop. Nothing so far constrains what the cluster runs. Lesson 04 drew the chain — authn, authz, decode, mutating, validation, validating, etcd — and the natural home for this is a validating admission plugin. So write it in CEL.

You cannot, and lesson 04 already proved why without knowing it was about this. `timestamp(now())` failed to *compile* there because CEL in the write path must be deterministic and total. Verifying a signature requires fetching an artifact from a registry over the network — non-deterministic, unbounded, and able to fail — so it is excluded by exactly the property that excluded the clock. This is a third reason for webhooks over CEL, and unlike lesson 04's operational one it is not a trade-off you can argue with.

So: Kyverno, from lesson 05, and its dedicated kind for this.

```bash
kubectl apply --server-side \
  -f https://github.com/kyverno/kyverno/releases/download/v1.19.0/install.yaml
kubectl wait --for=condition=Available deploy --all -n kyverno --timeout=300s
kubectl api-resources --api-group=policies.kyverno.io | grep -i image
```

```
imagevalidatingpolicies             ivpol    policies.kyverno.io/v1   false   ImageValidatingPolicy
namespacedimagevalidatingpolicies   nivpol   policies.kyverno.io/v1   true    NamespacedImageValidatingPolicy
```

Now the policy. Most of it is shapes you have already met — `matchConstraints` from lesson 04, `validationActions` and `failurePolicy` from lessons 04 and 05, CEL in `validations` — and only two fields are new:

```bash
kubectl create ns gate
PUB=$(cat "$COSIGNDIR/cosign.pub")
cat <<EOF | kubectl apply -f -
apiVersion: policies.kyverno.io/v1
kind: ImageValidatingPolicy
metadata:
  name: signed-by-us
spec:
  validationActions: [Deny]
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups: [""]
      apiVersions: ["v1"]
      operations: ["CREATE"]
      resources: ["pods"]
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: gate
  matchImageReferences:
  - glob: "registry:5000/app*"
  attestors:
  - name: ourkey
    cosign:
      key:
        data: |
$(echo "$PUB" | sed 's/^/          /')
      ctlog:
        insecureIgnoreTlog: true
  validationConfigurations:
    mutateDigest: true
  validations:
  - expression: >-
      images.containers.map(image, verifyImageSignatures(image, [attestors.ourkey])).all(e, e > 0)
    message: "image is not signed by our key"
EOF
```

`matchImageReferences` is the narrowing that lesson 04 had to hand-write and lesson 05 said nobody should: which image references this policy has an opinion about, so the cluster's own infrastructure images do not need a signature you never made. And the expression is worth reading rather than copying — `verifyImageSignatures` returns a **count**, and `all(e, e > 0)` says every container image must have at least one signature from the named attestor. It is a count and not a boolean because the interesting policies are the ones that require two.

Give it a signed tag to admit, then try both:

```bash
crane tag registry:5000/app@$D1 v2
sleep 15
kubectl run g-signed   -n gate --image=registry:5000/app:v2 --restart=Never --command -- sh -c 'busybox | head -1'
kubectl run g-unsigned -n gate --image=registry:5000/app:v1 --restart=Never --command -- sh -c 'busybox | head -1'
```

```
pod/g-signed created

Error from server: admission webhook "ivpol.validate.kyverno.svc-fail" denied the request:
Policy signed-by-us failed: image is not signed by our key
```

And the attacker's perfectly-valid signature, on content the cluster is being asked to run:

```bash
kubectl run g-attacker -n gate --image=registry:5000/app:v1 --restart=Never --command -- sh -c 'true'
```

```
Error from server: admission webhook "ivpol.validate.kyverno.svc-fail" denied the request:
Policy signed-by-us failed: image is not signed by our key
```

The signature is in the registry, it verifies, and it is irrelevant — because the policy named a key. That is the whole mechanism, and it holds for exactly one reason, which is the reason you should be able to state in one sentence when someone asks you whether image signing is worth it.

Then the payoff. Look at what the API server actually stored for the Pod you were allowed to create:

```bash
echo    "I typed:  registry:5000/app:v2"
kubectl get pod g-signed -n gate -o jsonpath='stored:   {.spec.containers[0].image}{"\n"}'
kubectl logs g-signed -n gate
```

```
I typed:  registry:5000/app:v2
stored:   registry:5000/app:v2@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
BusyBox v1.36.1 (2023-05-18 22:34:17 UTC) multi-call binary.
```

**The policy rewrote the reference to the content it verified.** `name:tag@digest` is the OCI form where both are present and the digest wins; the tag survives only as documentation of what it was called at admission time. So the Pod is pinned — not because its author was careful, but because the cluster made the author's carelessness impossible. That is `mutateDigest: true`, and it means a single object closed both holes in this lesson: the rename hole from lesson 04, because a digest has no synonyms, and the re-point hole from this one, because whoever moves `v2` tomorrow does not reach this Pod.

Which is why one policy produced **two** registrations:

```bash
kubectl get mutatingwebhookconfiguration,validatingwebhookconfiguration \
  -o custom-columns='KIND:.kind,NAME:.metadata.name,HOOK:.webhooks[*].name' | grep -i ivpol
```

```
MutatingWebhookConfiguration     kyverno-resource-mutating-webhook-cfg     ivpol.mutate.kyverno.svc-fail
ValidatingWebhookConfiguration   kyverno-resource-validating-webhook-cfg   ivpol.validate.kyverno.svc-fail
```

One authored object, two stages of lesson 04's chain: the mutating pass rewrites the reference, the validating pass refuses if the signature does not check. Lesson 04 measured that mutation runs before validation, and this is the design that requires it — you must resolve the tag to a digest *before* deciding whether that digest is signed, or you are checking a different thing from the one you pin.

One last note, and it is the reason `SSL_CERT_FILE` was worth flagging two thousand words ago. If your registry uses a private CA, this policy fails on the first try with a message that has nothing to do with signatures:

```
denied the request: Policy signed-by-us error: failed to update digest: failed to resolve digest
for image registry:5000/app:v2: Get "https://registry:5000/v2/": tls: failed to verify certificate:
x509: certificate signed by unknown authority
```

Teaching containerd to trust the CA did **not** teach Kyverno to trust it. They are different processes with different trust stores, and the policy engine talks to the registry itself — it has to, since verification is the thing CEL could not do. Fixing it means handing the CA to that Deployment as well:

```bash
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

There is a tempting shortcut in that CRD — `spec.credentials.allowInsecureRegistry: true` — and it is worth knowing what it does before you reach for it, because it does not mean "skip TLS verification." It means "fall back to plain HTTP," and against an HTTPS-only registry the result is the failure stacked on the first one:

```
tls: failed to verify certificate: x509: certificate signed by unknown authority;
GET http://registry:5000/v2/: unexpected status code 400 Bad Request:
Client sent an HTTP request to an HTTPS server.
```

A flag whose name says *insecure* and whose effect is *a second, different failure*. Read the message, not the flag.

> **Check yourself —** a team tells you their supply chain is covered: images are built in CI, scanned with a HIGH/CRITICAL gate, signed with cosign, and an admission policy requires a valid signature before anything runs. They show you a green pipeline and a denied Pod as evidence. Name the three most likely places this is not doing what they think, and say what single piece of evidence you would ask for in each case.

<details>
<summary>Answer</summary>

All three are things that look identical whether they are working or not, which is this act's whole subject.

**The policy may not name a key.** "Requires a valid signature" is the exact phrasing of the bug measured above. If the attestor is a broad keyless identity — any certificate from a public Fulcio, or a subject regexp like `.*github.com.*` — then anyone who can authenticate to that issuer can produce a signature it accepts, and everyone can. *Ask for:* the attestor block itself, not a description of it. For a key, who holds it and where it lives. For keyless, the literal `subject` and `issuer` values, and then ask who else can cause a workflow with that identity to run — which for a public repository with `pull_request` triggers can be a stranger.

**The gate probably covers a fraction of what runs.** `matchImageReferences` and `namespaceSelector` mean the policy applies to some images in some namespaces. Every cluster has exemptions — the ingress controller, the CNI, the monitoring stack, `kube-system` — and they accumulate. *Ask for:* not the policy, but the complement. Take the actual list of running container images, cluster-wide, and show which ones the policy's selectors do **not** match. Lesson 03 proved that reading a control's declaration tells you nothing about its configuration; this is the same audit and it fails the same way.

**The scan gate is either impassable or empty.** With 66 of 155 findings unfixable, a strict HIGH gate cannot pass, so either it has been quietly narrowed to unfixable-excluded, or narrowed to a base image with no package manager where the scanner reports `-` and the pipeline reads it as a tick. *Ask for:* the raw report from the last build of the image currently in production, including the tool version and DB timestamp, and check whether the target line says a distro or a dash. Then ask when the DB was last refreshed in CI, because a cached DB makes the gate quieter every day it survives.

**And the question nobody has asked:** does the signature apply to the thing running, or to a tag that has since moved? The verification happened at admission; the Pods running now were admitted at various times. If `mutateDigest` is off, `kubectl get pods -A -o …spec.containers[*].image` will show tags, and each of those Pods was verified against whatever the tag meant that day. *Ask for:* a list of running images by `spec` reference, and count how many are digests. That single count is the best available summary of whether any of this is load-bearing.

The reflex worth keeping: **every control in this pipeline is a filter with a domain, and the interesting question is always what is outside the domain** — not whether the filter works on what it sees.

</details>

<!-- figure -->
```
   THE ONE MOMENT NOTHING IN THIS ACT HAD TOUCHED: **BUILD**
   knows the contents. knows NOTHING about where it will run.
   decided by someone who has gone home; still running in 2 years.

   WHAT A TAG IS
     crane copy busybox:1.36 -> registry:5000/app:v1
     a1 Always        -> BusyBox v1.36.1   imageID ...73aaf090
     *** re-point the tag. NO object written. NO event. ***
     a2 IfNotPresent  -> BusyBox v1.36.1   imageID ...73aaf090
     a3 Always        -> BusyBox v1.37.0   imageID ...9db7b599
     SAME SPEC, SAME NODE, SAME MINUTE, DIFFERENT PROGRAMS.
     and `.spec.containers[0].image` is IDENTICAL on both:
       => THE SPEC IS NOT A DESCRIPTION OF WHAT IS RUNNING.
          every review, every kubectl diff, every GitOps repo
          reads a NAME, resolved elsewhere, at an unrecorded time.
     bonus: a1's status.image = docker.io/library/busybox:1.36
       a name NOBODY TYPED. containerd is content-addressed, so
       it reported the name it knew those bytes by. truth about
       content, fiction about origin, in the "where's it from" field.

   L04's HOLE WAS THE SAME HOLE FROM THE OTHER SIDE
     L04: one bytes, two names   (busybox vs docker.io/library/busybox)
     L08: one name, two bytes
     both = A TAG IS A MUTABLE POINTER. a rule reading a tag
     is reading a VARIABLE. no string handling fixes it.

   THE FIX: name@sha256:...  = CONTENT ADDRESSING, 3rd time
     Act I  inode is the file, the name is a pointer
     Act VIII a hash is a name you cannot lie about
     here: digest over the manifest -> transitively every layer
     pullPolicy defaults IfNotPresent AND THAT IS NOW CORRECT --
       "have this name?" and "have these bytes?" became one question.
     bad digest -> ErrImagePull "not found". a registry's WORST
       case for a digest is TO FAIL; for a tag it is TO SUCCEED.
     BUT: integrity != provenance. a digest says THESE BYTES,
     never OUR BYTES. pin the wrong thing precisely, forever.

   AlwaysPullImages (kube-bench's WARN, from L07)
     asked IfNotPresent -> STORED Always. it is a MUTATING plugin:
       rewrites your field, refuses nothing. L04's MutatingAdmission
       Policy, built in, shipping for a decade.
     price, MEASURED: image ON THE NODE + registry down =
       ImagePullBackOff. freshness costs availability -- 3rd time
       this act (L04 failurePolicy, L06 KMS, here).
     and the REAL reason it exists: IfNotPresent means the registry
       is never consulted, so ITS ACCESS CONTROL is never consulted.
       any Pod can run bytes another team pulled, with no pull
       secret. authorisation, not freshness. freshness is a side effect.

   A SCAN IS A JOIN, AND BOTH SIDES ARE SOMEONE ELSE'S
     the image you shipped and signed:  Target - | Type - | Vulns -
       the legend itself: '-' = NOT SCANNED, '0' = clean.
       no package DB in busybox -> nothing to look at. a green tick
       that means "I found nothing to inspect".
     nginx:1.25 -> 155 HIGH/CRIT ... which is 4 different sentences:
       155 findings but 106 DISTINCT CVEs (one CVE, many packages)
        89 have a fix .......... this is work
        66 have NO fix ......... will_not_fix 4 / fix_deferred 14
       => "deny any HIGH" DENIES THIS FOREVER, so the team switches
          it off. A GATE YOU CANNOT PASS IS AN EX-GATE. gate on
          --ignore-unfixed + an expiring reviewed exception list.
     and it all has a TIMESTAMP: DB UpdatedAt 2026-08-22 18:49.
       an image that passed Tuesday is not passing Wednesday,
       it is UNEXAMINED on Wednesday.

   THE SBOM IS THE LEFT SIDE OF THE JOIN, WRITTEN DOWN
     CycloneDX 1.7 · 150 components · 307 KB · purl per component
     re-join later with no image present. AND THEN:
       trivy image  -> 155      trivy sbom -> 157
       only in SBOM: nginx CVE-2026-42533, CVE-2026-60005
       same tool, same version, same FROZEN db (--skip-db-update),
       and the image scan ENUMERATED nginx with the IDENTICAL purl.
     one tool, two entry points, two answers, about the package
     THE IMAGE EXISTS TO RUN. L07 said a scanner is incomplete;
     this says you cannot fully trust its CONSISTENCY either.
     => pin tool+version+db+entry point, record all four, and
        treat a change in any of them as a change in the finding.

   SIGNING = ACT VIII, AND WHERE IT LIVES IS THE POINT
     cosign sign -> a NEW TAG in the SAME REPO:
       sha256-73aaf090....sig   (digest, s/:/-/, + .sig)
     no new server, no protocol: a registry is a blob store that
     will hold anything, so the name is COMPUTED. works air-gapped.
     AND THEREFORE: whoever can push the image can push BESIDE it.
     the signed document is 233 BYTES:
       {"critical":{"image":{"docker-manifest-digest":"sha256:73aa..."}}}
       nobody signed 1.9MB. THEY SIGNED A HASH. same shape as a
       certificate: a short assertion, signed.
     verify the DIGEST -> ok.  verify the TAG -> "no signatures found"
       A RE-POINTED TAG FAILS CLOSED, with nothing watching tags.
       don't detect tag changes -- be INDIFFERENT to them.
     wrong key -> "no matching signatures: invalid signature"

   THE TRAP THE ACT PROMISED
     attacker with PUSH signs the UNSIGNED digest with THEIR key:
       two .sig tags side by side, BOTH VALID, in your repo.
       cosign verify --key attacker.pub -> PASSES.
     => "THE IMAGE IS SIGNED" CARRIES NO INFORMATION.
        "signed BY A KEY WE CHOSE IN ADVANCE" is the whole thing.
        push access lets you ADD, never FORGE. that is the guarantee
        and it is enough ONLY IF THE VERIFIER NAMES THE KEY.
     keyless = Act IX walks back in: OIDC identity -> Fulcio issues
       a 10-minute cert (Act VIII L05 as a service) -> Rekor logs it.
       verify by --certificate-identity + --certificate-oidc-issuer.
       get those wrong and you accept anyone who can log in to GitHub.
     WHAT THE TLOG BUYS IS **WHEN**. a signature over a digest is
       TIMELESS, so a key compromised Friday taints everything it
       ever signed -> "rebuild everything" not "rebuild what came
       after". an ordered record of what happened == LESSON 10.

   THE CLUSTER CHECKS IT -- AND CEL CANNOT
     verification needs a NETWORK FETCH: non-deterministic,
     unbounded, can fail. excluded by the SAME property that
     killed timestamp(now()) in L04. a 3rd reason for webhooks,
     and the only one that is not a trade-off.
     ImageValidatingPolicy (ivpol): matchImageReferences is the
       narrowing L04 hand-wrote and L05 said nobody should.
       verifyImageSignatures returns a COUNT, not a bool --
       because the interesting policy requires TWO.
     signed v2 -> created.  unsigned v1 -> denied, reader's message.
     attacker-signed v1 -> STILL DENIED. the key is the authority,
       not the registry.

   AND THE CROWN: mutateDigest: true
     typed:  registry:5000/app:v2
     stored: registry:5000/app:v2@sha256:73aaf090...
     the policy REWROTE THE REFERENCE TO THE CONTENT IT VERIFIED.
     name:tag@digest -> the digest wins, the tag is documentation.
     ONE object closes BOTH holes: rename (a digest has no synonyms)
     and re-point (whoever moves v2 tomorrow cannot reach this Pod).
     hence ONE policy -> TWO webhooks:
       ivpol.mutate...   rewrites the reference
       ivpol.validate... refuses an unsigned digest
     L04 measured mutation-before-validation. THIS is the design
     that REQUIRES it: resolve the tag BEFORE judging the digest,
     or you check a different thing from the one you pin.

   THE SPINE, TURNED OVER
     every earlier control decided AT ONE MOMENT and was stuck with
     what that moment knew. this one doesn't:
       BUILD makes a claim it can prove   (sign the digest)
       ADMIT checks the claim + PINS it   (verify, mutateDigest)
       CREATE/RUN can only honour it      (content-addressed pull)
     you do not beat "the earlier you decide, the less you know".
     YOU CARRY VERIFIABLE EVIDENCE FORWARD FROM THE EARLY MOMENT
     TO A LATER ONE THAT KNOWS ENOUGH TO USE IT.
     which is what a capability, a token and a certificate all are.

   THE HONEST LIMITS
     private CA: teaching containerd did NOT teach Kyverno. separate
       processes, separate trust stores; the engine fetches ITSELF.
       -> mount the CA + SSL_CERT_FILE on the Deployment.
     allowInsecureRegistry does NOT mean "skip TLS". it means
       "fall back to HTTP" -> "Client sent an HTTP request to an
       HTTPS server". READ THE MESSAGE, NOT THE FLAG NAME.
```

**Cleanup.** The policy engine is in your write path and the plugin is off already; take both out, and note that lesson 05's warning applies — deleting the install file leaves the policy-derived webhooks behind, so delete the policy first:

```bash
kubectl delete ivpol --all
kubectl delete ns supply gate --ignore-not-found
kubectl delete -f https://github.com/kyverno/kyverno/releases/download/v1.19.0/install.yaml \
  --ignore-not-found
kubectl delete validatingwebhookconfiguration,mutatingwebhookconfiguration \
  -l webhook.kyverno.io/managed-by=kyverno --ignore-not-found
kubectl get validatingwebhookconfiguration,mutatingwebhookconfiguration

docker rm -f registry
docker exec netlab-control-plane rm -f /root/ka.bak
for n in netlab-control-plane netlab-worker; do
  docker exec $n rm -rf "/etc/containerd/certs.d/registry:5000"
  docker exec $n sh -c 'crictl rmi registry:5000/app 2>/dev/null; true'
done
rm -rf "$REGTLS" "$COSIGNDIR" "${TMPDIR:-/tmp}"/scan.json "${TMPDIR:-/tmp}"/sbom*.json "${TMPDIR:-/tmp}"/pkgs.json
```

Verify the API server flag really is back, because the next lesson edits the same file:

```bash
docker exec netlab-control-plane grep enable-admission-plugins /etc/kubernetes/manifests/kube-apiserver.yaml
```

```
    - --enable-admission-plugins=NodeRestriction
```

> **You understand this when you can** produce two Pods with byte-identical specs running
> different programs, and name the one field that distinguishes them; say what a digest does *not*
> establish; demonstrate that a valid signature from the wrong key proves nothing, and state what
> image signing guarantees; explain from lesson 04's measurements why CEL cannot verify a
> signature, and why that is not a trade-off; and diagnose a trust error from a policy engine
> against a registry the nodes pull from fine.

**Which raises:** this lesson took Act VIII's mathematics and applied it to an artifact **at rest** — a signature over a digest, checked before anything ran. Act VIII's other half was about bytes **in flight**, and it ended by getting a TLS connection to the cluster's edge. Everything past that edge, this whole act has quietly assumed. Act V measured Pod-to-Pod traffic and read it with `tcpdump`; nothing since has revisited what was visible in that capture, and no lesson in ten acts has encrypted a single packet *between* two Pods. The cluster gave you mTLS for its own control-plane components in Act VI and never extended it to your workloads. **So what is actually on the wire between two Pods right now, who can see it, and why did the thing that built a certificate authority for itself not do the same for you?**

---

↑ **[Act X overview](README.md)** · Prev: **[The doors the cluster leaves open](07-the-doors-left-open.md)** · Next: **[Encryption between Pods](09-encryption-between-pods.md)** →
