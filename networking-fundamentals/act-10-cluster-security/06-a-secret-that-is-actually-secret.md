# A Secret that is actually secret

Act VII followed one password. It created a Secret holding `hunter2`, mounted it into a Pod both ways, and then went looking for where the plaintext had ended up. It found **three** places:

1. **etcd**, in plaintext — and Act VI had already proved a snapshot file needs no cluster at all to read
2. **the node's memory**, in the kubelet's directory tree, readable with a shell on the node and no cluster credentials
3. **the process environment**, if you injected it that way — plus everything that process spawns

And it left you a sentence: *"Fixing (1) is called encryption at rest and needs cluster configuration. Avoiding (3) is free and is just a choice about how you consume them."*

This lesson does (1). It is the only one of the three that cluster configuration can touch, and the interesting part is not the YAML — it is discovering exactly what the fix buys, which turns out to be narrower than the phrase "encryption at rest" suggests, and discovering the two new ways to lose your data that you did not have before.

> **Predict first —** four commitments. **(a)** You turn on encryption at rest. Afterwards, does `kubectl get secret db-creds -o yaml` still show you the password? Answer before you reason about it, then reason about it — because whichever way you answered, the *implication* is the whole lesson. **(b)** You turn it on and then rewrite every existing Secret so they are all encrypted. You take an etcd snapshot immediately afterwards. Is your old plaintext in that snapshot? **(c)** Where does the key live? Not "in a file" — say *which machine*, and what that means about who can read your Secrets. **(d)** Act VI taught you to back up etcd and restore it. What have you just done to that procedure?

### The finding, reproduced

Act VI's `etcd()` shell function, unchanged, because nothing about reading etcd has changed:

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

kubectl create ns enc
kubectl create secret generic db-creds -n enc --from-literal=password=hunter2
etcd get /registry/secrets/enc/db-creds
```

```
/registry/secrets/enc/db-creds
k8s

v1Secret
db-creds enc" *$9b41d405-9cc9-4abc-8fef-741f463eb94f2 8 B
kubectl-createUpdatev1" 2FieldsV1:1
/{"f:data":{".":{},"f:password":{}},"f:type":{}}B
passwordhunter2Opaque "
```

`passwordhunter2`. Same as Act VI, on a cluster three acts later.

One detail worth a second, since it is visible for free: the record is not JSON. `k8s`, `v1Secret`, and binary field markers — this is **protobuf**, which is Act VI's "YAML is a rendering, not the record" with the mechanism showing. The `managedFields` bookkeeping from lesson 05's server-side apply is in there too. What the API server stores and what it hands you are different objects in different formats, and only one of them is the truth.

### The configuration, and the same three-part edit

Lesson 03 told you, when you first pointed the API server at an `AdmissionConfiguration` file, that you would do the identical three-part edit twice more in this act. This is the second.

First the key. A 32-byte key, base64-encoded, because that is what AES-256 takes:

```bash
head -c 32 /dev/urandom | base64
```

```
8IUDo6/WHRUZiqB9edQrNWWNs11hKjZd0cKifziajkc=
```

Then the configuration file, on the control-plane node — substitute your own key:

```bash
docker exec netlab-control-plane cp \
  /etc/kubernetes/manifests/kube-apiserver.yaml /root/kube-apiserver.yaml.bak
docker exec netlab-control-plane mkdir -p /etc/kubernetes/enc
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/enc/enc.yaml' <<'EOF'
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
```

Read the shape before running it, because two things in it are load-bearing and neither is obvious.

**`resources` is a list of resource types**, and `secrets` is a choice rather than a given. You can add `configmaps`, or any other resource; nothing is encrypted that you do not name, which is why a cluster with a beautiful `EncryptionConfiguration` for Secrets still has every ConfigMap in plaintext, including the ones people put credentials in by accident.

**`providers` is an ordered list, and the order is the entire semantics.** Hold that thought; there is a section on it below, because getting it backwards produces a cluster that looks encrypted and is not.

Now the three-part edit. A flag, a `volumeMount`, and a `hostPath` volume — the flag alone gives you an API server that cannot see the file and crash-loops:

```bash
docker exec netlab-control-plane cat /etc/kubernetes/manifests/kube-apiserver.yaml > /tmp/ka.yaml
python3 - <<'PY'
p = "/tmp/ka.yaml"; t = open(p).read()
t = t.replace("    - --allow-privileged=true",
    "    - --allow-privileged=true"
    "\n    - --encryption-provider-config=/etc/kubernetes/enc/enc.yaml", 1)
t = t.replace("    volumeMounts:\n    - mountPath: /etc/ssl/certs",
    "    volumeMounts:"
    "\n    - mountPath: /etc/kubernetes/enc\n      name: enc\n      readOnly: true"
    "\n    - mountPath: /etc/ssl/certs", 1)
t = t.replace("  volumes:\n  - hostPath:",
    "  volumes:"
    "\n  - hostPath:\n      path: /etc/kubernetes/enc\n      type: DirectoryOrCreate"
    "\n    name: enc"
    "\n  - hostPath:", 1)
open(p, "w").write(t)
print("patched")
PY
docker exec -i netlab-control-plane sh -c \
  'cat > /etc/kubernetes/manifests/.ka.tmp && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml' \
  < /tmp/ka.yaml
for i in $(seq 1 30); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && { echo "healthy after $((i*4))s"; break; }
done
```

```
patched
healthy after 40s
```

### What got encrypted, and what did not

```bash
kubectl create secret generic after-enc -n enc --from-literal=password=hunter3
etcd get /registry/secrets/enc/after-enc
```

```
/registry/secrets/enc/after-enc
k8s:enc:aescbc:v1:key1:!�PKI�L��D�Y=��zo��a��(p�1A� ��"{b��ʩ�R�s�P�Гq��-�*d3��˚:�?_��3��A/YG
��C�7Y�uJ1�*��Y���/N�� 0����� >T۷�2,釈�"H��ֈ��ez���'���i���Ҕ�G^7�������ө�Pyi�e�[�1I����tI
```

Ciphertext, and it is **self-describing**: `k8s:enc:aescbc:v1:key1:`. The provider that wrote it, and the *name* of the key. That prefix is not decoration — it is how the API server knows, years later, which of several keys to try, and it is the mechanism the whole rotation story is built on.

Now the Secret you made *before* all this:

```bash
etcd get /registry/secrets/enc/db-creds | grep -ao "password.*" | head -1
```

```
passwordhunter2Opaque "
```

**Still plaintext.** Which, if you have been reading this act, should be a familiar disappointment rather than a surprise: encryption is applied *when an object is written*, and nothing wrote that object. It is the same shape as lesson 03's PSA labels not touching running Pods and lesson 05's admission never looking back — **a control that fires on writes has no opinion about what already exists**, and this act has now shown you that three times in three different mechanisms.

So write them all, without changing any of them:

```bash
kubectl get secrets --all-namespaces -o json | kubectl replace -f -
etcd get /registry/secrets/enc/db-creds | head -3
```

```
secret/after-enc replaced
secret/db-creds replaced
/registry/secrets/enc/db-creds
k8s:enc:aescbc:v1:key1:��+M,8s�����o7,�� Ug���=�@�\Ģ+�G��IH��X��<n�6"��5�vI�+�"���gLu�2���
```

That pipeline is the whole migration and it is worth understanding rather than memorising. `kubectl replace` sends each object back unchanged, which is still a **write**, and a write goes through the encryption provider. There is no "encrypt existing data" API call because there does not need to be one.

### Prediction (b), and the reason it is the most important measurement here

Every guide stops at the pipeline above. Do not. Take a snapshot the way Act VI taught you, and run Act VI's grep:

```bash
etcd snapshot save /var/lib/etcd/etcd-backup.db
docker exec netlab-control-plane sh -c 'grep -ac hunter2 /var/lib/etcd/etcd-backup.db'
```

```
Snapshot saved at /var/lib/etcd/etcd-backup.db
1
```

**Your password is in the backup.** You enabled encryption, you rewrote every Secret, you verified the ciphertext with your own eyes, and the plaintext is in the file you would ship to backup storage.

Ask etcd how many versions of that key it is holding:

```bash
etcd get /registry/secrets/enc/db-creds -w json \
  | python3 -c "import json,sys; k=json.load(sys.stdin)['kvs'][0]; print('version:', k['version'], ' create_revision:', k['create_revision'], ' mod_revision:', k['mod_revision'])"
```

```
version: 2  create_revision: 126106  mod_revision: 126476
```

**Two.** etcd is an MVCC store — Act VI's `etcdctl watch` was watching *revisions* go by — and a write does not overwrite, it appends a new revision. Revision 126106 holds `hunter2` in plaintext. Revision 126476 holds the ciphertext. Both are in the store, so both are in the snapshot.

The old revision goes away when etcd **compacts**, which discards history below a chosen revision:

```bash
REV=$(etcd endpoint status -w json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['Status']['header']['revision'])")
etcd compact "$REV"
etcd snapshot save /var/lib/etcd/etcd-backup.db
docker exec netlab-control-plane sh -c 'echo -n "hunter2: "; grep -ac hunter2 /var/lib/etcd/etcd-backup.db; echo -n "aescbc markers: "; grep -ac "k8s:enc:aescbc:v1:key1" /var/lib/etcd/etcd-backup.db'
```

```
compacted revision 126581
Snapshot saved at /var/lib/etcd/etcd-backup.db
hunter2: 0
aescbc markers: 2
```

**Zero.** Now Act VI's experiment gives the opposite answer from the one Act VI got, and the migration is genuinely finished.

Two things to take away, and the second is bigger than this lesson.

The API server does ask etcd to compact on a timer — `--etcd-compaction-interval`, default `5m0s`. But do not treat that as the fix, because it is a schedule and not a guarantee: on this cluster a superseded revision was still present in a snapshot **taken 400 seconds later**, under stock settings and with no manual compaction. If you want to know the plaintext is gone, compact and then grep. Grepping is the only step in this entire procedure that checks the thing you actually care about.

And the general form: **your backup retention is your plaintext retention.** A snapshot is precisely the artifact that leaves the cluster — onto object storage, into somebody's home directory, through a CI job. Any snapshot taken between "the Secret existed" and "you compacted" contains the password forever, no matter what the live cluster now looks like. Encrypting at rest does nothing whatsoever about backups you already took, and there is no command that reaches into them.

### Prediction (a), and what this actually bought

```bash
kubectl get secret db-creds -n enc -o jsonpath='{.data.password}' | base64 -d; echo
```

```
hunter2
```

Of course it does. The API server holds the key; decrypting on read is its job. If this had stopped working, encryption at rest would have broken every workload in the cluster.

But sit with the implication, because it is the precise, narrow thing you have purchased. **Encryption at rest defends the store, not the API.** Anyone who can ask the API server for a Secret gets the plaintext, exactly as before, and the only thing standing between a user and that plaintext is the same thing that was standing there yesterday: RBAC, from Act IX. Nothing about confidentiality changed for any caller.

What changed is a specific and real threat model, and it is worth being able to state as a list rather than a slogan. After this change, the plaintext is no longer available to:

- **a stolen etcd snapshot** — the backup file, on the backup server, in the object store, in the CI artifact
- **the disk** the control-plane node is running on, or its cloud volume snapshot, or the decommissioned SSD
- **anyone who can read etcd directly** but cannot authenticate to the API server — including anything that reaches etcd's port without the API server's credentials

That is not a small set. It is, empirically, where a large share of real Kubernetes secret disclosure happens, precisely because a backup is a file that gets copied and a database is a service people forget is a service. It is simply not the set most people picture when they hear "our secrets are encrypted".

And it does nothing at all about Act VII's other two locations. The kubelet still writes the plaintext into `tmpfs` on the node; the environment variable is still in `/proc/1/environ`. Both remain exactly as Act VII measured them.

### The order of the providers is the whole configuration

Back to the thing flagged earlier. Swap the two providers — keep the same key, keep everything else, just put `identity` first:

```bash
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/enc/enc.yaml' <<'EOF'
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
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl stop $C'
for i in $(seq 1 40); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && break
done
kubectl create secret generic identity-first -n enc --from-literal=password=hunter4
etcd get /registry/secrets/enc/identity-first | grep -ao "password.*" | head -1
```

```
secret/identity-first created
passwordhunter4Opaque "
```

**Plaintext.** No error at startup, no warning, nothing in `kubectl get`, and a configuration file that contains a perfectly good AES key which is simply never used for writing. This is the act's characteristic bug in its purest form: the control is present, correctly configured in every respect except one, and doing nothing.

Now the other half, which is what makes the design make sense:

```bash
kubectl get secret db-creds -n enc -o jsonpath='{.data.password}' | base64 -d; echo
```

```
hunter2
```

The previously-encrypted Secret still reads fine, with `aescbc` sitting *second* in the list. So the rule is:

> **The first provider encrypts. Every provider is tried, in order, for decryption.**

Which is not an arbitrary rule — it is the only rule that makes every transition possible, and all four of them fall straight out of it:

| To do this | Put this first | Keep this after it | Then |
|---|---|---|---|
| **turn encryption on** | `aescbc` with `key1` | `identity` | rewrite all Secrets, compact |
| **rotate to a new key** | `aescbc` with `key2` *then* `key1` | `identity` | rewrite all Secrets, compact, then drop `key1` |
| **turn encryption off** | `identity` | `aescbc` with `key1` | rewrite all Secrets, compact, then drop the provider |
| **roll back a bad change** | — | — | the old provider is still listed, so nothing is unreadable |

Note what the rotation row requires and why: **a key must be able to decrypt before it is asked to encrypt.** On a multi-master cluster you therefore restart every API server with the new key in second place first, so that all of them can read what any of them writes, and only then promote it to first. Skip that and one API server writes ciphertext its peers cannot read, which presents as a Secret that is readable through some connections and not others.

Put the good configuration back before continuing:

```bash
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/enc/enc.yaml' <<'EOF'
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
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl stop $C'
for i in $(seq 1 40); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && break
done
```

Two restarts for two edits is tedious, and there is a flag for it — with a cost stated in its own help text:

```bash
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl exec $C kube-apiserver --help' \
  2>&1 | grep -A 1 "automatic-reload"
```

```
      --encryption-provider-config-automatic-reload   Determines if the file set by
      --encryption-provider-config should be automatically reloaded if the disk contents change.
      Setting this to true disables the ability to uniquely identify distinct KMS plugins via the
      API server healthz endpoints.
```

Worth reading twice. Turning on hot reload costs you **per-plugin health checks** — you can no longer tell from `/healthz` which of several key providers is broken. A convenience flag that trades away observability of the thing it makes convenient to change is a recognisable shape, and the right question to ask of it is the one this act keeps asking: when this stops working, how will I find out?

### Prediction (d): the new way to lose everything

You now have a cluster whose Secrets are unreadable without a 32-byte string that lives in one file on one machine. Find out what that means:

```bash
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/enc/enc.yaml' <<EOF
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources: ["secrets"]
  providers:
  - aescbc:
      keys:
      - name: key1
        secret: $(head -c 32 /dev/urandom | base64)
  - identity: {}
EOF
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl stop $C'
for i in $(seq 1 40); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && break
done
kubectl get secret db-creds -n enc -o jsonpath='{.data.password}'
```

```
Error from server (InternalError): Internal error occurred: invalid padding on input
```

`invalid padding on input`. That is a **CBC block-cipher padding failure** — Act VIII's mechanism, surfacing four acts later as a `500` from the Kubernetes API. And notice what it does *not* say: not "wrong key", not "cannot decrypt", not anything containing the word encryption. Somebody meeting this at 3am has an `InternalError` on one resource kind and a cluster that is otherwise completely healthy:

```bash
kubectl get pods -A --no-headers | awk '{print $4}' | sort | uniq -c
kubectl get ns enc --no-headers
```

```
  11 Running
enc   Active
```

Everything works. Nodes are Ready, Pods are Running, every other object reads and writes. Only Secrets encrypted with the previous key are gone — and any workload that needs to *mount* one is about to fail to start, which is how this normally announces itself.

Put the real key back, and watch it return:

```bash
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/enc/enc.yaml' <<'EOF'
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
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl stop $C'
for i in $(seq 1 40); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && break
done
kubectl get secret db-creds -n enc -o jsonpath='{.data.password}' | base64 -d; echo
```

```
hunter2
```

So here is what you have done to Act VI's backup and restore procedure, and it is the answer to prediction (d): **an etcd snapshot is no longer a backup.** It is half of one. The other half is a file that is not in it, on a machine that may not survive whatever made you need the backup, and if you restore the snapshot onto a cluster whose `EncryptionConfiguration` does not contain `key1`, every Secret in it is `invalid padding on input` — permanently, with no recovery path, because there is nothing wrong with the data and nothing to repair.

Act VI ended that lesson by having you verify a backup by counting keys rather than trusting `ls`. The same instinct, extended: **a backup you have not restored is a hypothesis**, and after this change the hypothesis includes the key. Whatever you do with snapshots now has to carry `enc.yaml` alongside them, in some place that is not the cluster and not the same blast radius, and the drill has to include reading a Secret.

### Where the key is, which is the honest limit

Prediction (c). Say it out loud by reading it:

```bash
docker exec netlab-control-plane ls -l /etc/kubernetes/enc/enc.yaml
docker exec netlab-control-plane tail -5 /etc/kubernetes/enc/enc.yaml
```

```
-rw-r--r-- 1 root root 239 Aug 22 14:49 /etc/kubernetes/enc/enc.yaml
      keys:
      - name: key1
        secret: 8IUDo6/WHRUZiqB9edQrNWWNs11hKjZd0cKifziajkc=
  - identity: {}
```

**The key to every Secret in the cluster is in a plaintext file, on the same machine as the encrypted data.** Those permissions are whatever your shell's umask left — nothing in Kubernetes checked them, nothing will warn you, and `-rw-r--r--` means every user account on that node can read it. `chmod 600` is the least you should do and it is not the point.

The point is that anyone with a shell on that node has both the lock and the key, so for that adversary you have bought nothing at all. This is Act VI's sentence again, the one it drew about `ca.key`: **a shell on a node is close to a shell in the cluster.** You have moved the plaintext out of etcd and into a file two directories away.

Which is what the fifth provider type is for. `kms` — and specifically **KMS v2**, the one to use — does not hold a key. It holds a *reference* to an external key manager, and the shape is one you built by hand in Act VIII:

- the API server generates a fresh **data encryption key** per write and encrypts the object with it — fast symmetric crypto on the payload
- it sends that DEK to the external KMS to be wrapped by a **key encryption key** it never sees, and stores the wrapped DEK beside the ciphertext
- to read, it unwraps the DEK by asking the KMS

That is **envelope encryption**, which is Act VIII's hybrid scheme exactly: symmetric for the bulk, something else for the key. And the property it buys is the one the local provider cannot: the KEK is not on the node, so a stolen disk, a stolen snapshot *and* a shell on the control plane all fail to yield plaintext — the last of those because reading now requires a live, authorised, and logged call to a service that can refuse and that recorded being asked. It also gives you key rotation without rewriting every Secret, since only the DEKs are re-wrapped.

The cost is a new dependency for reading Secrets, which means a new outage mode, which is the same trade in a new place. And it needs a KMS plugin running next to the API server and an external key manager, so this lab cannot demonstrate it — that is a genuine limit of the lab rather than of the topic, and the shape above is what you should be able to draw from memory.

> **Check yourself —** an auditor asks your team to confirm that Kubernetes Secrets are encrypted. Somebody produces the `EncryptionConfiguration`, a `kubectl get secret` showing the value still works, and an `etcdctl get` showing `k8s:enc:aescbc:v1:key1:` on three sampled Secrets. Is that sufficient evidence, and what would you add?

<details>
<summary>Answer</summary>

It is good evidence for one claim and no evidence at all for three others, and the sampling is the weakest part.

**What it establishes:** those three Secrets, right now, in that etcd, are ciphertext. That is real and worth having.

**What it misses, in rough order of how likely it is to be the actual gap:**

**Everything written before the change.** Sampling three Secrets that happen to have been written recently proves nothing about the ones nobody has touched in a year, and those are exactly the ones nobody rewrote. The check is not a sample, it is a scan: every key under `/registry/secrets/` must carry the prefix. One Secret without it is one Secret in plaintext, and it will be the interesting one.

**The backups.** Nothing above looks at a snapshot. If the pipeline was run and etcd was not compacted, the plaintext is in whatever snapshot was taken next, and that snapshot has since been copied somewhere with a completely different access policy. Ask what the oldest retained snapshot is, and grep one.

**The other resources.** `resources: ["secrets"]` means ConfigMaps are plaintext. Anyone who has grepped a real cluster's ConfigMaps for `password` knows how that goes, and the auditor's actual question — are our credentials encrypted — is not the same as the question about Secrets.

**Where the key is.** If it is a local `aescbc` key in a file on the control-plane node, then the honest statement is "encrypted against someone who steals the disk or a backup, not against someone who gets a shell on the control plane". That distinction is the whole content of the claim and a document that omits it is misleading rather than incomplete. Include the file's permissions, since somebody's umask decided them.

**And one thing to volunteer that nobody asks for:** whether a restore has been tested since encryption was enabled. That is not a confidentiality question, it is the availability risk *created by* the confidentiality control, and it is the one most likely to actually hurt.

The reflex worth keeping: **evidence that a control is on is not evidence of what it covers.** Three passing samples is the shape of a check that has never found anything.

</details>

<!-- figure -->
```
   ACT VII FOUND ONE PASSWORD IN THREE PLACES.
   THIS LESSON CLOSES EXACTLY ONE OF THEM.

     (1) etcd .............. THIS LESSON
     (2) node tmpfs ........ untouched. a shell on the node.
     (3) /proc/1/environ ... untouched. a choice you make.

   THE CONFIG, AND THE TWO THINGS THAT ARE NOT OBVIOUS
     resources: ["secrets"]   <- a CHOICE. configmaps are
                                 plaintext unless you say so.
     providers: [aescbc, identity]
       FIRST ENCRYPTS. ALL ARE TRIED FOR DECRYPT.
     three-part apiserver edit, again: flag + volume + mount.

   ORDER IS THE WHOLE CONFIGURATION
     [identity, aescbc]  -> new Secret written PLAINTEXT.
       no error. no warning. a valid AES key in the file,
       never used to write. the act's characteristic bug.
     and db-creds STILL DECRYPTS, because aescbc is listed.
     that one rule gives you all four transitions:
       on ...... aescbc first, identity after
       rotate .. key2 first, key1 after  (a key must be able
                 to DECRYPT before it is asked to ENCRYPT --
                 on multi-master, restart with it SECOND first)
       off ..... identity first, aescbc after
       rollback  free: the old provider is still in the list

   IT APPLIES ON WRITE, SO EXISTING DATA IS UNTOUCHED
     kubectl get secrets -A -o json | kubectl replace -f -
     (a no-op replace is still a WRITE. there is no
      "encrypt existing data" API and there needn't be.)
     third time this act: PSA labels don't touch running Pods,
     admission never looks back, encryption is write-only.

   AND THE STEP EVERY GUIDE OMITS
     rewrite everything, snapshot, then Act VI's own grep:
       grep -ac hunter2 etcd-backup.db  ->  1     <-- !!
     etcd is MVCC. version: 2. rev 126106 = plaintext,
     rev 126476 = ciphertext. BOTH are in the snapshot.
       etcd compact <current rev>  ->  grep gives 0
     --etcd-compaction-interval defaults to 5m but MEASURED
     still present at t=400s. compact, then GREP. grep is the
     only step that checks the thing you care about.
     => YOUR BACKUP RETENTION IS YOUR PLAINTEXT RETENTION.
        no command reaches into snapshots you already took.

   WHAT IT BOUGHT, PRECISELY
     kubectl get secret -> hunter2. OF COURSE IT DOES.
     THE STORE IS DEFENDED. THE API IS NOT. RBAC (Act IX) is
     still the only thing between a user and the plaintext.
     now unavailable to: a stolen SNAPSHOT · the DISK / volume
     snapshot / dead SSD · anything reading etcd directly.
     that is where most real disclosure happens. it is also
     not what people picture when they say "encrypted".

   AND TWO NEW WAYS TO LOSE EVERYTHING
     wrong key -> "Internal error occurred: invalid padding
                   on input"  <- Act VIII's CBC padding, as a
                   500 from the k8s API. the words "key" and
                   "encryption" appear NOWHERE.
                   cluster otherwise 11/11 Running, ns Active.
                   only Secrets. only ones written with the old key.
     AN ETCD SNAPSHOT IS NO LONGER A BACKUP. it is half of one.
       restore without key1 -> every Secret unreadable, forever,
       with nothing broken and nothing to repair.
       Act VI: a backup you have not RESTORED is a hypothesis.
       the hypothesis now includes the key. drill must READ A SECRET.

   THE HONEST LIMIT
     -rw-r--r--  /etc/kubernetes/enc/enc.yaml
     the key to every Secret, in PLAINTEXT, on THE SAME MACHINE
     as the ciphertext, with permissions your umask picked and
     nothing in k8s ever checks. chmod 600 is the least of it.
     Act VI again: a shell on a node is close to a shell in the
     cluster. you moved the plaintext two directories.

   WHICH IS WHAT KMS v2 IS FOR = ACT VIII'S HYBRID SCHEME
     per-write DEK encrypts the object (fast, symmetric)
     external KMS wraps the DEK with a KEK the apiserver
       NEVER SEES; wrapped DEK stored beside the ciphertext
     read = unwrap the DEK via a live, authorised, LOGGED call
       -> a service that can REFUSE and that RECORDED being asked
     so stolen disk AND stolen snapshot AND a control-plane
     shell all fail. rotation re-wraps DEKs, no Secret rewrite.
     price: reading a Secret now has a new DEPENDENCY, so a new
     outage. same trade, new place. (not demonstrable in this lab.)
```

**Cleanup.** Put the API server back, and note the order — remove the encryption while the key still exists, or you are practising the failure above by accident:

```bash
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/enc/enc.yaml' <<'EOF'
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
docker exec netlab-control-plane sh -c \
  'C=$(crictl ps --name kube-apiserver -q | head -1); crictl stop $C'
for i in $(seq 1 40); do sleep 4; kubectl get --raw /healthz >/dev/null 2>&1 && break; done
kubectl get secrets --all-namespaces -o json | kubectl replace -f - >/dev/null

docker exec netlab-control-plane sh -c \
  'cp /root/kube-apiserver.yaml.bak /etc/kubernetes/manifests/.ka.tmp \
   && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml'
for i in $(seq 1 30); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && { echo "healthy after $((i*4))s"; break; }
done
kubectl delete ns enc --ignore-not-found
docker exec netlab-control-plane rm -rf /etc/kubernetes/enc /root/kube-apiserver.yaml.bak \
  /var/lib/etcd/etcd-backup.db
```

That sequence is itself the "turn encryption off" row of the table: `identity` first, the key still listed underneath, rewrite everything, *then* remove the provider. Doing it in the other order is the `invalid padding` section, on purpose, to your own cluster.

> **You understand this when you can** name the three places Act VII found one password and say which one this lesson closes and why the other two are out of reach; write an `EncryptionConfiguration` from memory and say which two of its fields are decisions rather than boilerplate; perform the three-part API server edit and name the symptom of omitting each part; read `k8s:enc:aescbc:v1:key1:` and say what each segment is for; explain why enabling encryption leaves existing Secrets in plaintext, give the one-line fix, and connect it to two other write-time controls in this act that behave the same way; state what an etcd snapshot taken straight after that fix still contains, explain it in terms of MVCC and `version: 2`, and give the command that resolves it and the command that *checks*; say why backup retention is plaintext retention and why no fix reaches those files; predict whether `kubectl get secret` still works and derive from your answer the exact list of adversaries this control does and does not defeat; state the rule governing the `providers` list in one sentence and use it to derive all four of turn-on, rotate, turn-off and roll back; explain why a rotated key must be listed second before it is listed first, and what breaks on multi-master if you skip that; demonstrate that `identity` in first position silently disables everything while leaving a valid key in the file; recognise `invalid padding on input`, name which act taught you that mechanism, and describe what the rest of the cluster looks like at that moment; explain why an etcd snapshot is no longer a backup on its own and what a restore drill must now include; say where the key sits relative to the data it protects and why that bounds the whole claim; and sketch KMS v2 as envelope encryption, naming the DEK, the KEK, which one the API server never sees, the three adversaries it defeats that a local key does not, and the new dependency you took on.

**Which raises:** the honest limit of this whole lesson was one line — the key is a file on a node, and a shell on that node reads it. Which is the third time this act has arrived at a node's filesystem being the end of the argument: lesson 01's `hostPath: /`, lesson 02's seccomp profile that had to be on every node, and now this. Meanwhile lesson 04 handed you a different loose end and never picked it up: every Pod you have ever created came back with a `kube-api-access-*` volume you did not ask for, holding a credential for talking to the API server, and you were told it was lesson 07's whole subject. Both of those are the same question. **What is actually reachable, from a Pod or from a node, by someone who has arrived there with no credentials at all — and how much of it is switched on right now because switching it off would have broken something in 2016?**

---

↑ **[Act X overview](README.md)** · Prev: **[Policy as a product](05-policy-as-a-product.md)** · Next: **[The doors the cluster leaves open](07-the-doors-left-open.md)** →
