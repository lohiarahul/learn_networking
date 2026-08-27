# Who says so

Lesson 08 worked out a great deal about an image and proved every bit of it on the spot: the digest that
names bytes rather than a label, the one field that lets two byte-identical specs run different programs,
the packages a scanner enumerates and the two different things it means by *zero*, the credential still
sitting in the image config after being deleted from the filesystem.

Every one of those is something **you** computed about bytes **you** had. Hand the image to somebody else
and none of it travels with it. A digest is a fact about content, not a statement about who stands behind
that content — and lesson 07's question was never only *what is in here*. It was **whose word do I have
for it, and can the cluster check that word before the thing runs?**

That is two problems, and this lesson takes them in order: make a claim somebody is accountable for, then
move the checking of it off your laptop and into the write path.

> **Predict first —** three commitments. **(a)** You sign an image. Where does the signature go — name
> the place, and say who can write to it. **(b)** `cosign verify` exits zero against an image. State
> exactly what that establishes about who built it; the honest answer is smaller than it first looks.
> **(c)** Lesson 04 wrote admission rules in CEL and lesson 05 reached for a webhook instead. Only one of
> the two can verify a signature at admission time. Say which, and commit to a reason before you read on.

### Where you are typing

This continues on lesson 08's bench, and if you are in the same shell you already have it. If not, the
registry container and the containerd trust files are still on the nodes, and only the shell state needs
rebuilding — the certificate is still where the bench put it:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
REGTLS="${TMPDIR:-/tmp}/regtls"
crane() { docker run --rm --network kind -v "$REGTLS/tls.crt":/ca.crt:ro \
            -e SSL_CERT_FILE=/ca.crt gcr.io/go-containerregistry/crane:v0.21.9 "$@"; }
crane ls registry:5000/app
```

```
v1
```

If that last command cannot reach the registry, the bench is gone rather than idle — go back to
[lesson 08's bench](08-what-you-shipped.md#the-bench) and build it again, which takes under a minute.

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

Now prediction (a) — where does a signature go? Look at the repository before and after:

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

**Cleanup, for both halves of this pair.** The policy engine is in your write path and the plugin is off already; take both out, and note that lesson 05's warning applies — deleting the install file leaves the policy-derived webhooks behind, so delete the policy first:

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

> **You understand this when you can** say where a signature is stored and who can write there;
> demonstrate that a valid signature from the wrong key proves nothing, and state what image signing
> does and does not guarantee; explain from lesson 04's own measurements why CEL cannot verify a
> signature, and why that is not a trade-off you can argue with; say what a transparency log buys
> that a signature alone cannot; and diagnose a trust error from a policy engine against a registry
> the nodes pull from fine.

**Which raises:** these two lessons took Act VIII's mathematics and applied it to an artifact **at rest** — a signature over a digest, checked before anything ran. Act VIII's other half was about bytes **in flight**, and it ended by getting a TLS connection to the cluster's edge. Everything past that edge, this whole act has quietly assumed. Act V measured Pod-to-Pod traffic and read it with `tcpdump`; nothing since has revisited what was visible in that capture, and no lesson in ten acts has encrypted a single packet *between* two Pods. The cluster gave you mTLS for its own control-plane components in Act VI and never extended it to your workloads. **So what is actually on the wire between two Pods right now, who can see it, and why did the thing that built a certificate authority for itself not do the same for you?**

---

↑ **[Act X overview](README.md)** · Prev: **[The doors the cluster leaves open](07-the-doors-left-open.md)** · Next: **[Encryption between Pods](09-encryption-between-pods.md)** →
