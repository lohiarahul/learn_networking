# Secrets from outside the cluster

Follow one password through this course and it reads like a farce.

Act VII created a Secret holding `hunter2` and then went looking for the plaintext. It found three places: etcd, a `tmpfs` file on the node, and the process environment. Lesson 06 spent a whole lesson closing the first — configured encryption at rest, discovered it does not apply to existing objects, rewrote every Secret, discovered the plaintext was still in an etcd snapshot, compacted etcd to prove it was gone — and then measured that the key to all of it sits in a `-rw-r--r--` file on the same machine as the ciphertext. Lesson 10 then added a **fourth** location with one line of audit policy, in a file that outlives the flag that created it.

Four locations, one of them created by a security control, and every fix so far has been an attempt to defend a copy of something that arguably should not have been in the cluster at all.

That is the thought worth taking seriously, and it is the last idea in this act: not *how do I protect the secret Kubernetes is holding*, but **why is Kubernetes holding it.**

> **Predict first —** four commitments. **(a)** Something outside the cluster holds the real password, and a controller inside the cluster fetches it so your Pods can use it. How many of Act VII's three locations does that remove? Give a number. **(b)** You delete the resulting Secret with `kubectl delete secret`. What happens? **(c)** The controller has to authenticate to that external store. So it needs a credential — which is a secret, which has to live somewhere, which is the problem you just started with. Is that circular, or is there a way out? Answer before reading on; you have already built every piece of the way out. **(d)** Which of the mechanisms in this lesson do you think appears on the CKS exam?

### Pattern one: the problem that is actually about git

Before the interesting patterns, dispose of the one people meet first, because it answers a different question than it appears to.

You want your cluster in git — Act VII's whole argument for declarative configuration — and you cannot commit a Secret, because a Secret is base64, which Act VII measured is not encryption. **Sealed Secrets** solves exactly this: a controller in the cluster holds a private key and publishes the public half, you encrypt your value to that public key with a CLI, and the resulting `SealedSecret` is safe to commit because only that controller can open it. The controller then decrypts it and creates an ordinary Secret.

Which is genuinely useful and worth knowing, and notice what it does *not* change: the authoritative copy of the password is still the thing in your git repository, the cluster still ends up holding a plaintext Secret in etcd, and rotating the value means a commit. It moves the secret safely *through* git. It does not move it *out of* the cluster. Every location Act VII found is still occupied.

So set it aside as a packaging answer and ask the real question.

### Pattern two: let something else be the source of truth

The **External Secrets Operator** inverts the ownership. Something outside — a cloud provider's secret manager, an on-premises secret store, a password manager with an API — holds the real value. A controller in the cluster reads it and creates a Secret from it.

It has a provider for testing that needs no account anywhere, which makes the mechanism measurable rather than described:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets --version 2.6.0 \
  -n external-secrets --create-namespace
kubectl -n external-secrets rollout status deploy --timeout=360s
kubectl get pods -n external-secrets
```

```
external-secrets-669c7cc7df-vfjk7                   1/1   Running   0   105s
external-secrets-cert-controller-7d75699655-btw5j   1/1   Running   0   105s
external-secrets-webhook-5f655d497c-7t49t           1/1   Running   0   105s
```

Three Deployments, and two of them should look familiar by now — a webhook and a cert controller, which is lesson 04's hand-built admission webhook and its certificate, shipped as a product. Nothing new; just the thing you already built, operated by somebody else.

Then two objects, and the split is the one you have now met four times:

```bash
kubectl create ns outside
cat <<'EOF' | kubectl apply -f -
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata: {name: the-vault, namespace: outside}
spec:
  provider:
    fake:
      data:
      - key: "prod/db/password"
        value: "hunter2-from-outside"
        version: "v1"
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata: {name: db-creds, namespace: outside}
spec:
  refreshInterval: 15s
  secretStoreRef: {name: the-vault, kind: SecretStore}
  target:
    name: db-creds
    creationPolicy: Owner
  data:
  - secretKey: password
    remoteRef: {key: "prod/db/password", version: "v1"}
EOF
sleep 20
kubectl get externalsecret db-creds -n outside
kubectl get secrets -n outside
```

```
NAME       STORETYPE     STORE       REFRESH INTERVAL   STATUS         READY   LAST SYNC
db-creds   SecretStore   the-vault   15s                SecretSynced   True    1s

NAME       TYPE     DATA   AGE
db-creds   Opaque   1      16s
```

A Secret exists that nobody created. The `SecretStore` says *where to look and how to authenticate*; the `ExternalSecret` says *which key, and what to call the result* — a connection and a request, separately, which is `ConstraintTemplate` and `Constraint` from lesson 05, and `ValidatingAdmissionPolicy` and its binding from lesson 04, and a `StorageClass` and a `PVC` from Act VII. Four independent designs, one shape.

Now prediction (a), and this is where the pattern gets honest about itself:

```bash
kubectl get secret db-creds -n outside -o jsonpath='{.data.password}' | base64 -d; echo
kubectl get secret db-creds -n outside \
  -o jsonpath='{range .metadata.ownerReferences[*]}owner: {.kind}/{.name}{"\n"}{end}'

etcd() {
  kubectl -n kube-system exec etcd-netlab-control-plane -- etcdctl \
    --cacert /etc/kubernetes/pki/etcd/ca.crt \
    --cert   /etc/kubernetes/pki/etcd/server.crt \
    --key    /etc/kubernetes/pki/etcd/server.key "$@"
}
etcd get /registry/secrets/outside/db-creds | grep -ao "hunter2-from-outside" | head -1
```

```
hunter2-from-outside
owner: ExternalSecret/db-creds
hunter2-from-outside
```

**The answer to prediction (a) is zero.** What the operator produced is an ordinary Kubernetes Secret, and the last line is Act VI's `etcdctl` finding the plaintext in etcd exactly as it did four lessons ago. Every location Act VII catalogued is still occupied: etcd has it, the kubelet will write it to `tmpfs` on whatever node mounts it, and if you inject it as an environment variable it is in `/proc/1/environ`.

If you expected this pattern to keep the secret out of the cluster, it does not. It changes who *owns* it.

Prediction (b), which follows from that `ownerReference` and is the first genuinely double-edged property:

```bash
kubectl delete secret db-creds -n outside
sleep 20
kubectl get secrets -n outside
```

```
secret "db-creds" deleted from outside namespace
NAME       TYPE     DATA   AGE
db-creds   Opaque   1      20s
```

**A Secret you cannot delete.** Twenty seconds old — it came back. That is Act VI's reconciliation loop, which by now you should expect: a controller compares desired state to actual state and fixes the difference, and it does not care that the difference was your `kubectl delete`. Act VII taught the same idea through ownership: `kubectl drain` refused to delete a Pod that nothing owned, and was willing to delete the ones a ReplicaSet would replace. The deciding fact there was an `ownerReference`, and it is the deciding fact here.

The consequence for an incident is worth stating plainly, because it is a reflex people get wrong under pressure: **deleting the Secret is no longer revocation.** It is a twenty-second outage followed by the same credential.

Revocation, and rotation, happen at the source:

```bash
kubectl patch secretstore the-vault -n outside --type=json \
  -p '[{"op":"replace","path":"/spec/provider/fake/data/0/value","value":"rotated-hunter3"}]'
sleep 25
kubectl get secret db-creds -n outside -o jsonpath='{.data.password}' | base64 -d
echo "   <- and nobody touched the Secret"

kubectl delete externalsecret db-creds -n outside
sleep 8
kubectl get secrets -n outside
```

```
rotated-hunter3   <- and nobody touched the Secret

externalsecret.external-secrets.io "db-creds" deleted
No resources found in outside namespace.
```

Both of the properties that make this pattern worth its weight, measured. The value changed at the source and arrived in the cluster with no Kubernetes object edited by anybody. And removing the `ExternalSecret` removed the Secret with it — garbage collection via that `ownerReference`, which is what `creationPolicy: Owner` bought.

### What that actually bought, precisely

This act has asked the same question of every control: what does it defend against, exactly? Here the honest list is short, and none of the items are the one people say.

**It did not** remove the plaintext from etcd, the node, or the environment. All three, measured above or in Act VII.

**It did** change four things, and they are operational rather than cryptographic:

- **One place to revoke.** Before: a credential is in *n* clusters and nobody knows which. After: it is in one store, and the clusters are consumers. That is the difference between "we think we rotated it" and "we rotated it".
- **Rotation without a deploy.** The measurement above: the value changed and no manifest, commit or rollout was involved. Which matters because the reason credentials do not get rotated is almost never that nobody wanted to.
- **An audit trail on the secret itself.** Lesson 10 gave you an audit log of who read a Kubernetes Secret. A real secret store gives you the same thing for the authoritative copy, including reads from outside the cluster entirely — the laptop, the CI job, the contractor.
- **The blast radius of an etcd snapshot shrinks in time, not in content.** A stolen snapshot still contains whatever was synced when it was taken. But because the source can rotate cheaply, that plaintext has a shelf life, which lesson 06's version did not.

And it took on the cost this act has now shown you five times. Reading a secret needs a live external service, so there is a new outage mode: lesson 04's webhook at `failurePolicy: Fail`, lesson 06's KMS dependency, lesson 08's `AlwaysPullImages` needing the registry, lesson 09's key distribution needing the API server, and now this. **Every control in this act that adds an authority adds a dependency, and the dependency is always available less often than the thing it protects.**

### Pattern three: never make a Secret at all

There is one design that answers prediction (a) with a number greater than zero, and it works by declining to create a Kubernetes object.

The **Secrets Store CSI Driver** is a storage driver — Act VII's CSI, the interface that lets a volume come from anywhere. You declare a `SecretProviderClass`, and the Pod gets a volume whose contents the driver fetches from the external store at **mount time**, per Pod, on the node. There is no Secret object, so there is nothing in etcd, so there is nothing in an etcd snapshot, and lesson 06's whole lesson becomes unnecessary for that value.

This lab cannot demonstrate it, and the reason is worth being straight about: every provider is a real cloud one, and there is no fake. That is a limit of the lab rather than of the topic, the same as lesson 02's AppArmor and lesson 06's KMS.

What you should be able to reason about without running it is where the value ends up anyway:

- **etcd** — gone. This is the real win and it is a genuine one.
- **the node** — unchanged. The driver writes the value into a `tmpfs` file for that Pod, which is *precisely* Act VII's second location. A shell on the node still reads it.
- **the environment** — unchanged if you choose to put it there.

So the honest summary of the strongest available pattern is: it removes one of three locations, and it is the one that mattered most because it was the one that got copied into backups.

There is also a footgun that has swallowed a lot of people, and it is exactly this act's characteristic bug. The driver has an optional `secretObjects` feature that syncs the mounted value **into a Kubernetes Secret**, because some applications only read environment variables. Switch that on and you have re-created every location you just eliminated, while still running the driver, still holding the `SecretProviderClass`, and still believing the property you no longer have.

### Prediction (c): the credential for the credential

Every pattern above needs the cluster to authenticate to something external. That is a credential, which is a secret, which needs to live somewhere — and if the answer is "a Kubernetes Secret holding an API key for the secret store", the whole exercise has bought you one indirection and nothing else.

That is the real problem, it is called **bootstrapping trust**, and you have already built the way out. Ask the cluster what it is:

```bash
kubectl get --raw /.well-known/openid-configuration | python3 -m json.tool
```

```json
{
    "issuer": "https://kubernetes.default.svc.cluster.local",
    "jwks_uri": "https://172.19.0.2:6443/openid/v1/jwks",
    "response_types_supported": ["id_token"],
    "subject_types_supported": ["public"],
    "id_token_signing_alg_values_supported": ["RS256"]
}
```

Act IX lesson 04 had you fetch that document and the JWKS behind it, and verify a ServiceAccount token's signature by hand. At the time it was an exercise in how token verification works. **It was also the answer to this problem, and nothing said so.**

Because a cluster that publishes an OIDC discovery document and a JWKS is an **identity provider**. It can make signed, short-lived, verifiable statements about who its workloads are. And the one field that turns that into a usable credential is the audience:

```bash
kubectl create sa app -n outside
kubectl create token app -n outside --audience=https://secrets.example.com --duration=10m \
  > /tmp/wl.jwt
python3 - <<'PY'
import base64, json
def b64u(s): return base64.urlsafe_b64decode(s + '='*(-len(s) % 4))
h, p, _ = open('/tmp/wl.jwt').read().strip().split('.')
print("header :", json.dumps(json.loads(b64u(h))))
pl = json.loads(b64u(p))
for k in ('iss','aud','sub','exp','iat'): print(f"{k:7}:", pl.get(k))
print("k8s.io :", json.dumps(pl.get('kubernetes.io')))
PY
```

```
header : {"alg": "RS256", "kid": "fNzzmn2keCMktTShWvQORjFrMZ1vC_RD0RVKbWDbBl0"}
iss    : https://kubernetes.default.svc.cluster.local
aud    : ['https://secrets.example.com']
sub    : system:serviceaccount:outside:app
exp    : 1787457162
iat    : 1787456562
k8s.io : {"namespace": "outside", "serviceaccount": {"name": "app", "uid": "074e5cbf-3589-4aad-bdb2-d76e509b450f"}}
```

Read `aud` and `sub` together, because between them they are the entire mechanism. The subject is a workload — namespace, ServiceAccount, and the ServiceAccount's UID, so a deleted-and-recreated ServiceAccount of the same name is a *different* subject. And the audience is a service that is not this cluster, which means this token is useless anywhere else: Act IX's diagnose drill measured a `vault`-scoped token getting a `401` from the API server, and lesson 07 read the `aud` claim that explains it. That same check, run by the secret store, is what stops it replaying your token back against the cluster.

And the last piece is the one Act IX made you do by hand:

```bash
kubectl get --raw /openid/v1/jwks > /tmp/jwks.json
python3 - <<'PY'
import base64, json, hashlib
def b64u(s): return base64.urlsafe_b64decode(s + '='*(-len(s) % 4))
h, p, s = open('/tmp/wl.jwt').read().strip().split('.')
key = next(k for k in json.load(open('/tmp/jwks.json'))['keys']
           if k['kid'] == json.loads(b64u(h))['kid'])
n = int.from_bytes(b64u(key['n']), 'big'); e = int.from_bytes(b64u(key['e']), 'big')
em = pow(int.from_bytes(b64u(s), 'big'), e, n).to_bytes((n.bit_length()+7)//8, 'big')
DI = bytes.fromhex('3031300d060960864801650304020105000420')
dg = hashlib.sha256(f"{h}.{p}".encode()).digest()
print("SIGNATURE VALID, using only the published key:",
      em == b'\x00\x01' + b'\xff'*(len(em)-3-len(DI)-32) + b'\x00' + DI + dg)
PY
```

```
SIGNATURE VALID, using only the published key: True
```

That is the way out of prediction (c), and it is worth saying slowly: **the external store verified who the workload is using nothing but a published public key and some arithmetic.** It did not call the cluster. It holds no credential for the cluster. The cluster holds no credential for it. There is no shared secret anywhere in the exchange, so there is no shared secret to store, rotate, or leak.

The workflow every cloud provider builds on this is the same three steps, whatever they call it — IRSA, Workload Identity, workload identity federation:

1. You tell the provider, once, to trust your cluster's issuer URL and to accept `system:serviceaccount:outside:app` as a principal.
2. The Pod reads its projected token — lesson 04's `kube-api-access-` volume, the one nobody asked for, which lesson 07 then decoded — and presents it.
3. The provider verifies the signature against the JWKS, checks `aud` and `exp`, and hands back a short-lived credential of its own.

Which retires this act's oldest complaint. Lesson 04 measured that every Pod comes back with a token volume you never requested and cannot opt out of, and lesson 07 spent a section on the blast radius of that token. This is what it is *for*: **the projected token is the bootstrap credential**, and it is a good one precisely because it is short-lived, audience-scoped, tied to a UID, and verifiable by a party that has never spoken to your cluster.

Notice the shape, because it is lesson 08's shape exactly. There, `BUILD` made a signed claim and `ADMIT` checked it, and the point was that you do not beat the trade-off between deciding early and knowing enough — you carry verifiable evidence forward. Here the cluster makes a signed claim about a workload and an unrelated service checks it, with no channel between them. **A signature is how a claim survives leaving the system that made it**, and that sentence covers a certificate, a JWT, a signed image and this, which is most of what Acts VIII, IX and X were about.

### Prediction (d): why almost none of this is examinable

The answer to (d) is roughly "none of it".

Which is not a criticism of the exam. Look at what every pattern in this lesson needs: a cloud account, a vendor's controller, a provider plugin, an issuer URL reachable from outside your network. None of it can be assessed in a two-hour session on a cluster in a box, and none of it is Kubernetes — it is the ecosystem that grew where Kubernetes deliberately stopped.

What *is* examinable is the diagnosis rather than the products: that a Secret is base64 and not encryption, where the plaintext ends up, how to configure encryption at rest, and how to consume a Secret so it does not end up in an environment. Lessons 06 and 07 and Act VII cover those, and they are the load-bearing knowledge — the rest is which vendor's controller your employer chose.

But it is the last lesson in the act and worth saying anyway, because the gap between the exam and the job is exactly here. **The exam tests whether you can protect a secret the cluster holds. The job is mostly deciding whether the cluster should hold it.**

> **Check yourself —** a team moves to the External Secrets Operator, backed by a cloud secret manager, with workload identity so nothing stores a static credential. They tell you Kubernetes Secrets are no longer a risk in their clusters, and ask whether encryption at rest can be switched off since the secrets "live outside now". What do you tell them?

<details>
<summary>Answer</summary>

**No, and the premise is wrong in a specific way worth naming rather than arguing about.**

**The Secrets are still in etcd.** That is the measurement in this lesson: the operator's output is an ordinary Secret, and `etcdctl` reads the plaintext out of it. Encryption at rest is protecting exactly what it protected before, against exactly the adversaries lesson 06 listed — a stolen snapshot, a disk, anything reading etcd without going through the API. Nothing about the source of the value changed any of that. If they want the etcd copy gone, the pattern that does it is the CSI driver with no `secretObjects` sync, and that is a different migration.

**What did improve is worth crediting, so the conversation is not just a no.** They now have one place to revoke, rotation without a deploy, an audit trail on the authoritative copy, and — because the source can rotate cheaply — a shelf life on the plaintext in any snapshot. Those are real, and they are better than what encryption at rest buys. They are simply not a substitute for it, because they defend against a different thing: bad *process*, rather than a stolen *file*.

**Then the two things to raise that they have not.**

Deleting a Secret is no longer revocation — it reappears in seconds. If that reflex is in an incident runbook, it is now wrong, and an incident is where it will be discovered.

And the availability question, which is the actual new risk. Every Pod start that needs a fresh sync now depends on the external store. Ask what happens to a scale-up during an outage of that store, and whether anyone has tested it. Lesson 06's version of this — an etcd snapshot is no longer a backup on its own — has a sibling here: **your secret store is now in the critical path of your deployments**, and it belongs on the dependency diagram at the same tier as the API server.

The reflex worth keeping: **"the secret lives outside now" is a claim about the source of truth, not about the copies** — and every control you are considering switching off protects a copy.

</details>

<!-- figure -->
```
   FOLLOW ONE PASSWORD AND IT READS LIKE A FARCE
     Act VII found hunter2 in THREE places: etcd · node tmpfs ·
       /proc/1/environ
     L06 closed #1: enc-at-rest, doesn't apply to existing objects,
       rewrite all, STILL in the snapshot, compact -- and the KEY is
       -rw-r--r-- on the same machine as the ciphertext
     L10 ADDED A FOURTH with one line of audit policy, in a file that
       OUTLIVES THE FLAG THAT MADE IT
   => every fix defended a COPY OF SOMETHING THAT SHOULD NOT HAVE BEEN
      IN THE CLUSTER. so stop asking how to protect what k8s holds.
      ASK WHY IT IS HOLDING IT.

   PATTERN 1 -- SEALED SECRETS: a git problem wearing a crypto costume
     controller holds a private key, publishes the public half;
     encrypt to it, commit the ciphertext safely.
     MOVES THE SECRET SAFELY *THROUGH* GIT. NOT *OUT OF* THE CLUSTER.
     source of truth = your repo. plaintext Secret still in etcd.
     rotation = a commit. all three Act VII locations still occupied.

   PATTERN 2 -- EXTERNAL SECRETS OPERATOR: invert the ownership
     3 Deployments, two of them a WEBHOOK + A CERT CONTROLLER =
       L04's hand-built webhook and its cert, shipped as a product.
     SecretStore  = where to look + how to authenticate
     ExternalSecret = which key + what to call the result
       -> the two-object split, met a FOURTH time (L04 VAP+binding,
          L05 ConstraintTemplate+Constraint, Act VII SC+PVC)
     MEASURED: a Secret exists that nobody created. SecretSynced/True

     *** PREDICTION (a) ANSWER: ZERO LOCATIONS REMOVED ***
       decoded          -> hunter2-from-outside
       owner            -> ExternalSecret/db-creds
       etcdctl get ...  -> hunter2-from-outside   <-- Act VI's grep,
                                                      four lessons on
       it is AN ORDINARY SECRET. etcd has it, the kubelet will tmpfs
       it, env injection still puts it in /proc/1/environ.
       IT CHANGES WHO *OWNS* IT, NOT WHERE IT IS.

     PREDICTION (b): kubectl delete secret -> IT IS BACK IN 20s
       Act VI's reconciliation loop; it does not care that the
       difference was your delete. (Act VII: drain deletes what is OWNED.)
       => DELETING THE SECRET IS NO LONGER REVOCATION. it is a
          20-second outage followed by THE SAME CREDENTIAL.
          if that is in a runbook, it is now wrong, and an INCIDENT
          is where you will find out.
     rotate at the SOURCE -> rotated-hunter3, no k8s object edited
     revoke = delete the ExternalSecret -> Secret GC'd via
       ownerReference (that is what creationPolicy: Owner bought)

   WHAT IT ACTUALLY BOUGHT (operational, not cryptographic)
     + ONE PLACE TO REVOKE ("we think we rotated it" -> "we did")
     + ROTATION WITHOUT A DEPLOY (nobody fails to rotate for lack
       of wanting to)
     + AN AUDIT TRAIL ON THE AUTHORITATIVE COPY, including reads
       from OUTSIDE the cluster -- the laptop, the CI job, the contractor
     + a stolen snapshot's plaintext now has A SHELF LIFE
       (shrinks in TIME, not in CONTENT)
     - AND A NEW DEPENDENCY. 5th time in this act: L04 failurePolicy:
       Fail · L06 KMS · L08 AlwaysPullImages needs the registry ·
       L09 keys via the API server · here.
       EVERY CONTROL THAT ADDS AN AUTHORITY ADDS A DEPENDENCY, AND
       THE DEPENDENCY IS AVAILABLE LESS OFTEN THAN WHAT IT PROTECTS.

   PATTERN 3 -- CSI DRIVER: decline to create the object
     Act VII's CSI. SecretProviderClass; the driver fetches AT MOUNT
     TIME, per Pod, on the node. NO SECRET OBJECT.
       etcd ........ GONE. the real win, and the one that mattered,
                     because etcd is what got copied into BACKUPS.
       node tmpfs .. UNCHANGED. exactly Act VII's location #2.
       environ ..... unchanged if you choose it.
     so the STRONGEST available pattern removes ONE OF THREE.
     (not demonstrable here: every provider is a real cloud one and
      there is no fake. same honest limit as L02 AppArmor, L06 KMS.)
     THE FOOTGUN, and it is this act's characteristic bug exactly:
       `secretObjects` syncs the mounted value INTO A SECRET, because
       some apps only read env vars. switch it on and you have
       re-created EVERY location you just eliminated, while still
       running the driver and STILL BELIEVING THE PROPERTY.

   PREDICTION (c) -- THE CREDENTIAL FOR THE CREDENTIAL
     if the answer is "a Secret holding an API key for the secret
     store", you bought ONE INDIRECTION AND NOTHING ELSE.
     called BOOTSTRAPPING TRUST -- and you built the way out in Act IX.
       /.well-known/openid-configuration -> issuer + jwks_uri + RS256
       A CLUSTER THAT PUBLISHES THESE IS AN IDENTITY PROVIDER.
       (Act IX L04 had you verify a token by hand. it was an exercise
        in HOW verification works. IT WAS ALSO THE ANSWER TO THIS,
        and nothing said so.)
     kubectl create token app -n outside --audience=https://secrets.example.com
       sub: system:serviceaccount:outside:app   <- and the SA's UID,
            so delete+recreate = A DIFFERENT SUBJECT
       aud: [https://secrets.example.com]       <- NOT this cluster,
            so it is useless anywhere else -- L07 measured the API
            server rejecting a wrong-audience token, and that same
            check stops the store REPLAYING it against the cluster
     verify by hand, RSA pow(sig,e,n), against the published JWKS:
       SIGNATURE VALID, USING ONLY THE PUBLISHED KEY: True
     *** THE STORE VERIFIED THE WORKLOAD WITHOUT CALLING THE CLUSTER.
         no shared secret ANYWHERE in the exchange, so none to store,
         rotate, or leak. ***
     IRSA / Workload Identity / federation = the same 3 steps:
       1. trust the issuer URL + accept this SA as a principal (once)
       2. Pod presents its PROJECTED TOKEN
       3. provider checks sig + aud + exp, returns its own short creds
     WHICH RETIRES THE ACT'S OLDEST COMPLAINT: L04 measured a token
     volume nobody asked for and cannot opt out of; L07 sized its
     blast radius. THIS IS WHAT IT IS FOR. it is a good bootstrap
     credential BECAUSE it is short-lived, audience-scoped, UID-tied,
     and verifiable by someone who never spoke to your cluster.
     SAME SHAPE AS L08: a claim made in one place, checked in another.
     => A SIGNATURE IS HOW A CLAIM SURVIVES LEAVING THE SYSTEM THAT
        MADE IT. (a certificate, a JWT, a signed image, and this --
        which is most of Acts VIII, IX and X.)

   PREDICTION (d): ~NONE OF THIS IS EXAMINABLE
     all of it needs a cloud account, a vendor controller, a provider
     plugin, an issuer URL reachable from outside. it is not
     Kubernetes -- IT IS THE ECOSYSTEM THAT GREW WHERE KUBERNETES
     DELIBERATELY STOPPED.
     what IS examinable is the DIAGNOSIS: base64 is not encryption,
     where the plaintext ends up, enc-at-rest, and how to consume a
     Secret without putting it in the environment. that is the
     load-bearing part; the rest is which vendor your employer picked.
     THE EXAM TESTS WHETHER YOU CAN PROTECT A SECRET THE CLUSTER
     HOLDS. THE JOB IS MOSTLY DECIDING WHETHER IT SHOULD HOLD IT.
```

**Cleanup.** The operator is a webhook in your write path, so lesson 05's warning applies — take the policy-shaped objects out first:

```bash
kubectl delete externalsecret,secretstore --all -n outside --ignore-not-found
kubectl delete ns outside --ignore-not-found
helm uninstall external-secrets -n external-secrets
kubectl delete ns external-secrets --ignore-not-found
kubectl get validatingwebhookconfiguration,mutatingwebhookconfiguration
rm -f /tmp/wl.jwt /tmp/jwks.json
```

> **You understand this when you can** predict what happens when you delete a synced Secret, name
> the mechanism, and say what that means for a runbook; list what the pattern buys and be explicit
> that none of it is cryptographic; name the dependency it adds; state the bootstrapping problem
> in one sentence and say why "a Secret holding an API key" is not a solution; and say what
> property makes workload identity work, in one sentence about shared secrets.

**Which raises:** the act asked one question of every control — *at what moment does this refuse, what did it know then, and what gets past it because of what it could not know?* Ten lessons answered it at five moments: `BUILD` signs an image, `ADMIT` refuses an object, `CREATE` refuses a container, `RUN` refuses a syscall, and `AFTER` refuses nothing and writes it down. This lesson did something none of the others did. It did not add a refusal anywhere on that timeline — it **changed what existed**, so that most of the timeline had nothing to guard. That is the most powerful move available and the one that is hardest to see, because it does not look like security work; it looks like an architecture decision, and it is usually made by somebody who is not thinking about security at all.

Which is the note to leave the cluster on. Everything in this act defended **one cluster**, and every mechanism in it — a rule that admits or refuses, an identity a service will accept, a key somebody has to distribute, an authoritative store outside the thing it protects, a log that is the only record of an authorised change — has just been shown to you at the scale of a laptop. The next territory is the one where all of it is somebody else's control plane, declared rather than configured, applied to networks and identities that span continents. **Every primitive there is one you have now built by hand: a subnet you subnetted, a route you added, a certificate you signed, a policy you wrote, a token you verified. So the only genuinely new question is what changes when the thing enforcing them is an API you cannot read the source of.**

Before that: three pages to make this act stick.

---

↑ **[Act X overview](README.md)** · Prev: **[Seeing it happen](10-seeing-it-happen.md)** · Next: **[Test yourself](test-yourself.md)** →
