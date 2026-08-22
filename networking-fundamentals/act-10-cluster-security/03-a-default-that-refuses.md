# A default that refuses

Two lessons of measurement produced a stanza. Drop all capabilities, refuse to be root, forbid privilege escalation, ask for a seccomp filter, make the root filesystem read-only. Every line earned by watching what happens without it.

And every line **optional**. A Pod that contains none of it is not malformed, not deprecated, not warned about — it is an ordinary valid Pod, and it will run as root with fourteen capabilities and no syscall filter, exactly as the first experiment in lesson 01 did. So the protection is not a property of the cluster. It is a property of whoever last edited the YAML.

Which is the shape of every real incident in this area. Nobody disables the hardening; they write a manifest that never mentioned it.

> **Predict first —** you label a namespace so the cluster enforces its strictest policy, then create a plain Pod in it. **(a)** Will the refusal tell you *which* fields are wrong, or just that the Pod is refused? **(b)** Now create a **Deployment** whose pod template has the same problem. Does `kubectl create deployment` fail? **(c)** Suppose you later find a namespace labelled `enforce: baseline` in which a privileged Pod is happily running with all 41 capabilities. Given only what you know so far, is that possible — and if it is, where is the truth?

### A policy that lives on the namespace

**Pod Security Admission** is built into the API server, and it is configured by putting labels on a Namespace. There are three levels, and they are cumulative:

| Level | What it is |
|---|---|
| `privileged` | no restrictions at all — the historical default, and what every namespace you have used so far has been |
| `baseline` | blocks the known escalation paths: `privileged`, host namespaces, `hostPath`, added capabilities beyond a small list |
| `restricted` | baseline plus the hardening from lessons 01 and 02, required rather than offered |

Take the strictest one and hand it a Pod that says nothing:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

kubectl create ns locked
kubectl label ns locked pod-security.kubernetes.io/enforce=restricted
kubectl run p --image=busybox:1.36 -n locked --restart=Never --command -- sh -c 'echo hi'
```

```
Error from server (Forbidden): pods "p" is forbidden: violates PodSecurity "restricted:latest":
allowPrivilegeEscalation != false (container "p" must set securityContext.allowPrivilegeEscalation=false),
unrestricted capabilities (container "p" must set securityContext.capabilities.drop=["ALL"]),
runAsNonRoot != true (pod or container "p" must set securityContext.runAsNonRoot=true),
seccompProfile (pod or container "p" must set securityContext.seccompProfile.type to "RuntimeDefault" or "Localhost")
```

Read that list and then read the last two lessons back.

`allowPrivilegeEscalation=false` — the `NoNewPrivs` bit that turned `topsecret` into `Permission denied`. `capabilities.drop=["ALL"]` — the fourteen, gone. `runAsNonRoot=true` — the `uid=0` that opened lesson 01. `seccompProfile` — the `Seccomp: 0` that opened lesson 02.

**Four requirements, and you derived all four by experiment before anyone told you they were a policy.** That is what `restricted` is: not a philosophy, but the specific set of fields whose absence you have already watched being exploitable, made mandatory. Which also answers (a) — the refusal names every field, gives the exact value it wants, and names the container it wants it on. It is the most helpful error message in Kubernetes, and it is a checklist you can work through without documentation.

So work through it:

```bash
kubectl apply -n locked -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: good}
spec:
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile: {type: RuntimeDefault}
  containers:
  - name: c
    image: busybox:1.36
    securityContext:
      allowPrivilegeEscalation: false
      capabilities: {drop: ["ALL"]}
    command: ["sh","-c","id -u; grep Seccomp /proc/self/status"]
EOF
sleep 8
kubectl logs -n locked good
```

```
pod/good created
1000
Seccomp:	2
Seccomp_filters:	1
```

Note where the fields sit, because the refusal message was precise about it. `runAsNonRoot` and `seccompProfile` are settable at pod *or* container level — the message says "pod or container". `allowPrivilegeEscalation` and `capabilities` are **container-level only**, because they are properties of a process rather than of the sandbox around it. Put them at pod level and you find out immediately:

```bash
kubectl apply -n locked -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: wrongplace}
spec:
  securityContext:
    capabilities: {drop: ["ALL"]}
    allowPrivilegeEscalation: false
  containers: [{name: c, image: "busybox:1.36"}]
EOF
```

```
Error from server (BadRequest): error when creating "STDIN": Pod in version "v1" cannot be handled
as a Pod: strict decoding error: unknown field "spec.securityContext.allowPrivilegeEscalation",
unknown field "spec.securityContext.capabilities"
```

Worth noticing that this is a *different kind* of refusal from the one above it — not a policy verdict but a **decoding** error, from the API server failing to parse your object into the Go type at all. It happens before any admission plugin runs, names both bad fields, and is the cheapest error in the entire chain. Which is the first of many appearances of a pattern this act keeps returning to: the earliest checks are the ones that need to know the least, and "is this even a Pod" needs to know nothing about your cluster.

### What `baseline` is for

`restricted` is where you want to end up. `baseline` is what you can actually get to on Tuesday, and it is worth seeing that it is a list of specific known-bad fields rather than a smaller philosophy:

```bash
kubectl create ns based
kubectl label ns based pod-security.kubernetes.io/enforce=baseline
```

Three Pods, three fields, three refusals:

```bash
kubectl apply -n based -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: a}
spec:
  containers: [{name: c, image: "busybox:1.36", securityContext: {privileged: true}}]
EOF
kubectl apply -n based -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: b}
spec:
  hostNetwork: true
  containers: [{name: c, image: "busybox:1.36"}]
EOF
kubectl apply -n based -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: c}
spec:
  volumes: [{name: h, hostPath: {path: /}}]
  containers: [{name: c, image: "busybox:1.36"}]
EOF
```

```
Error from server (Forbidden): ... violates PodSecurity "baseline:latest": privileged (container "c" must not set securityContext.privileged=true)
Error from server (Forbidden): ... violates PodSecurity "baseline:latest": host namespaces (hostNetwork=true)
Error from server (Forbidden): ... violates PodSecurity "baseline:latest": hostPath volumes (volume "h")
```

`privileged` is lesson 01's four-measurement disaster. `hostNetwork` is Act IV's namespace, un-created — the Pod sharing the node's interfaces, routes and `/proc/net/tcp`, which is the flag the orientation page told you to hold a question about. And `hostPath: /` is the node's entire filesystem, which Act VII already showed you is where every Secret on that node is sitting in plaintext.

None of these needs a capability or defeats a filter. They are all just *fields*, asked for politely, in a valid manifest. Which is why a check on the object at admission is the right place for them: **there is nothing for the kernel to refuse, because the kernel was told to do it on purpose.**

### One predicate, three dispositions

The level is only half a policy. The other half is what happens when a Pod violates it, and there are three labels:

```bash
kubectl create ns warned
kubectl label ns warned pod-security.kubernetes.io/warn=restricted
kubectl run p --image=busybox:1.36 -n warned --restart=Never --command -- sh -c 'echo hi'
```

```
Warning: would violate PodSecurity "restricted:latest": allowPrivilegeEscalation != false (container "p" must
set securityContext.allowPrivilegeEscalation=false), unrestricted capabilities (container "p" must set
securityContext.capabilities.drop=["ALL"]), runAsNonRoot != true (pod or container "p" must set
securityContext.runAsNonRoot=true), seccompProfile (pod or container "p" must set
securityContext.seccompProfile.type to "RuntimeDefault" or "Localhost")
pod/p created
```

Identical analysis, identical wording, and `pod/p created`. `would violate` rather than `violates`.

- **`enforce`** rejects the request.
- **`warn`** returns the same text as an HTTP warning header, which `kubectl` prints, and admits the Pod.
- **`audit`** writes it into the API server's audit log and says nothing to the client — invisible to whoever ran the command, visible to whoever is watching the cluster.

All three can be set at once, and that is the point of having three. You cannot turn on `enforce=restricted` in a namespace full of running workloads without breaking them; you can turn on `warn` and `audit` today, collect the list of what would have failed, fix them, and then flip `enforce`. The three labels exist because **the migration is the hard part**, and a policy engine that can only say no is unusable in a cluster that already has Pods in it.

### Pinning the policy to a version

One more label, and it is the one people leave off:

```bash
kubectl label ns locked pod-security.kubernetes.io/enforce-version=v1.30 --overwrite
kubectl run p2 --image=busybox:1.36 -n locked --restart=Never --command -- sh -c 'echo hi' 2>&1 | head -1
```

```
Error from server (Forbidden): pods "p2" is forbidden: violates PodSecurity "restricted:v1.30": allowPrivilegeEscalation != false (container "p2" ...
```

`restricted:v1.30` now, where it said `restricted:latest` before. The definition of `restricted` is versioned because it grows: when Kubernetes decides some newly-understood field belongs in the policy, `latest` picks it up on upgrade, and Pods that have run untouched for a year start being refused by a cluster nobody changed.

So `latest` is the honest default and a genuine operational hazard, and pinning to the version you tested is how you make a cluster upgrade not also be a policy change. The cost is that you have to remember to move the pin, or you are enforcing a policy from 2024 forever.

### The gap: a Deployment is not a Pod

Now prediction (b). The namespace `locked` enforces `restricted`. Create a Deployment whose pod template violates it in all four ways:

```bash
kubectl create deployment web --image=busybox:1.36 -n locked -- sh -c 'sleep 300'
kubectl get deploy,rs -n locked
```

```
Warning: would violate PodSecurity "restricted:latest": allowPrivilegeEscalation != false (container
"busybox" must set securityContext.allowPrivilegeEscalation=false), unrestricted capabilities (...)
deployment.apps/web created

NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/web   0/1     0            0           6s

NAME                             DESIRED   CURRENT   READY   AGE
replicaset.apps/web-7d6d6748bd   1         0         0       6s
```

**`deployment.apps/web created`** — in a namespace with `enforce=restricted`, and only a warning. Then `0/1`, a ReplicaSet that wants one Pod and has none, and no error anywhere in `kubectl get`.

The error is one more object down:

```bash
kubectl get events -n locked --field-selector reason=FailedCreate \
  -o custom-columns=M:.message --no-headers | head -1
```

```
Error creating: pods "web-7d6d6748bd-568sm" is forbidden: violates PodSecurity "restricted:latest":
allowPrivilegeEscalation != false (container "busybox" must set ...
```

Work out why before reading on, because the reason is mechanical and it generalises.

**PSA's predicate is on the Pod resource.** A Deployment is not a Pod — it is an object that *contains a pod template*, and creating one is a perfectly legal write of a Deployment. There is nothing for `enforce` to reject, because the thing being admitted is not the thing the policy is about. Later, the ReplicaSet controller creates a Pod, that Pod goes through admission like anything else, and *there* it is refused. Act VI's reconciliation loop is what turns your one write into the write that gets rejected, and it does so on its own schedule, in a different object, as an Event.

The warning exists to paper over exactly this: PSA looks at objects that carry a pod template, evaluates the template as if it were a Pod, and *warns*. It cannot enforce, because the template is not the Pod and the Deployment might be edited before anything is created from it. So **`enforce` silently degrades to `warn` for every controller object** — Deployment, StatefulSet, DaemonSet, Job, CronJob.

The operational consequence is worth writing on something. Your CI runs `kubectl apply`, gets exit code 0, and reports success. Your rollout sits at `0/1`. The reason is a message on an Event attached to a ReplicaSet whose name you do not know, and Events expire. Anyone who has debugged "the Deployment applied fine but no Pods exist" has met this; now you know which object to ask.

```bash
kubectl delete deployment web -n locked
```

### Where the policy really lives

Prediction (c). So far the policy has been namespace labels, which is a pleasant story: `kubectl get ns -o yaml` tells you what is enforced. It is not true.

PSA is an admission plugin, and admission plugins can be configured on the API server itself with a file. Act VI taught you how to change an API server: it is a static Pod, and you edit its manifest on the control-plane node.

```bash
docker exec netlab-control-plane cp \
  /etc/kubernetes/manifests/kube-apiserver.yaml /root/kube-apiserver.yaml.bak

docker exec netlab-control-plane mkdir -p /etc/kubernetes/admission
docker exec -i netlab-control-plane sh -c 'cat > /etc/kubernetes/admission/psa.yaml' <<'EOF'
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
- name: PodSecurity
  configuration:
    apiVersion: pod-security.admission.config.k8s.io/v1
    kind: PodSecurityConfiguration
    defaults:
      enforce: "baseline"
      enforce-version: "latest"
    exemptions:
      usernames: []
      runtimeClasses: []
      namespaces: ["kube-system", "local-path-storage", "based"]
EOF
```

Two halves. `defaults` is the level applied to a namespace with **no labels at all**, which is how you make a cluster secure-by-default instead of hoping every future namespace gets labelled. `exemptions` is the escape hatch, and it takes three kinds of thing: a **username** (so a specific controller can keep creating the privileged Pods it needs), a **runtimeClass** (lesson 02's sandbox — if a Pod is getting a different kernel, the argument for restricting it changes), and a **namespace**.

Now point the API server at it. Three separate edits, and the second is the one people forget:

```bash
docker exec netlab-control-plane cat /etc/kubernetes/manifests/kube-apiserver.yaml > /tmp/ka.yaml
python3 - <<'PY'
p = "/tmp/ka.yaml"; t = open(p).read()
t = t.replace("    - --allow-privileged=true",
    "    - --allow-privileged=true"
    "\n    - --admission-control-config-file=/etc/kubernetes/admission/psa.yaml", 1)
t = t.replace("    volumeMounts:\n    - mountPath: /etc/ssl/certs",
    "    volumeMounts:"
    "\n    - mountPath: /etc/kubernetes/admission\n      name: admission\n      readOnly: true"
    "\n    - mountPath: /etc/ssl/certs", 1)
t = t.replace("  volumes:\n  - hostPath:",
    "  volumes:"
    "\n  - hostPath:\n      path: /etc/kubernetes/admission\n      type: DirectoryOrCreate"
    "\n    name: admission"
    "\n  - hostPath:", 1)
open(p, "w").write(t)
print("patched")
PY
docker exec -i netlab-control-plane sh -c \
  'cat > /etc/kubernetes/manifests/.ka.tmp && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml' \
  < /tmp/ka.yaml
```

**The flag is not enough.** The API server runs in a container, and a path in a flag means nothing unless that path exists inside it — so the file needs a `hostPath` volume *and* a `volumeMount`, and if you add only the flag the API server starts, fails to read a file it cannot see, and crash-loops. That is one of the most reliable ways to lose a mark and a cluster in the same minute, and you will do the identical three-part edit twice more in this act.

Note also the `.tmp`-then-`mv`: the kubelet is watching that directory and will act on whatever it reads, so an atomic rename is how you avoid it reading half a file.

The API server is now being restarted by the kubelet, which takes a while:

```bash
for i in $(seq 1 30); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && { echo "healthy after $((i*4))s"; break; }
done
```

```
healthy after 40s
```

Now the two consequences. First the default, in a namespace with no labels whatsoever:

```bash
kubectl create ns plain
kubectl apply -n plain -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: pv}
spec:
  containers: [{name: c, image: "busybox:1.36", securityContext: {privileged: true}}]
EOF
```

```
Error from server (Forbidden): ... violates PodSecurity "baseline:latest": privileged (container "c" must not set securityContext.privileged=true)
```

An unlabelled namespace now refuses privileged Pods. Nothing was labelled; the cluster's *default* moved.

And then the other one:

```bash
kubectl apply -n based -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: pv}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext: {privileged: true}
    command: ["sh","-c","grep ^CapEff /proc/self/status"]
EOF
sleep 8
kubectl logs -n based pv
kubectl get ns based -o jsonpath='{.metadata.labels}{"\n"}'
```

```
pod/pv created
CapEff:	000001ffffffffff
{"kubernetes.io/metadata.name":"based","pod-security.kubernetes.io/enforce":"baseline"}
```

**Read those three lines together.** A privileged Pod with all forty-one capabilities is running in a namespace whose own label says `enforce: baseline` — the exact configuration that refused this same Pod four sections ago. The label is still there. It is enforcing nothing.

That is prediction (c), and the answer to "where is the truth" is: **in a file on the control-plane node, referenced by a flag, mounted into a container.** Not in the API. Not in `kubectl get ns -o yaml`. Not visible to anyone reviewing the namespace, or to a script that audits labels across the cluster, or to a compliance report generated from the API.

So the technique that looks like an audit — list every namespace, check its `enforce` label — is **unsound in both directions**. A namespace can be labelled and exempt. A namespace can be unlabelled and covered by a default. And there is no field anywhere that says which.

The general form is worth more than the specific gotcha, because you will meet it repeatedly: **a control's declaration and a control's configuration can live at different layers, and the declaration is the one everybody reads.** When you need to know what a cluster actually enforces, the question is never "what do the objects say" — it is "what is the API server started with".

**Restore the API server before moving on:**

```bash
docker exec netlab-control-plane sh -c \
  'cp /root/kube-apiserver.yaml.bak /etc/kubernetes/manifests/.ka.tmp \
   && mv /etc/kubernetes/manifests/.ka.tmp /etc/kubernetes/manifests/kube-apiserver.yaml'
for i in $(seq 1 30); do sleep 4
  kubectl get --raw /healthz >/dev/null 2>&1 && { echo "healthy after $((i*4))s"; break; }
done
```

```
healthy after 44s
```

> **Check yourself —** a colleague proposes labelling every namespace `enforce=restricted` in one change, and points out correctly that it is a single `kubectl label --all` and cannot break anything that is already running, since PSA only checks Pods at creation. Is that last part true, and is it reassuring?

<details>
<summary>Answer</summary>

The claim is true and it is the opposite of reassuring.

PSA is an admission check, so it fires when a Pod is *created*. Labelling a namespace does not touch the Pods in it, and nothing is evicted. Every workload keeps running exactly as before, and the change appears to have cost nothing.

Then a node is drained, or a Pod OOMs, or a rollout happens, or the cluster is upgraded — and every Pod that needed recreating cannot be created. The damage is not deferred to a convenient moment; it is deferred to precisely the moments when Pods get recreated, which are the moments something is already going wrong. A cluster in that state looks healthy in every dashboard and has quietly lost the ability to heal.

Which is exactly the migration `warn` and `audit` exist for: label with those first, wait for the workloads to actually cycle, collect the violations, fix them, then enforce.

There is a second answer worth having, from the section above. `kubectl label --all` also does nothing at all in an exempted namespace, and the label will sit there afterwards looking like it worked. A "we enforce restricted everywhere" statement built out of that command is not checkable from the API.

</details>

<!-- figure -->
```
   THREE LEVELS, CUMULATIVE, ON A NAMESPACE LABEL

     privileged .. nothing. the historical default.
     baseline .... the KNOWN escalation FIELDS:
                     privileged, hostNetwork/PID/IPC,
                     hostPath, added capabilities
     restricted .. baseline + LESSONS 01 AND 02, mandatory:
                     allowPrivilegeEscalation=false
                     capabilities.drop=[ALL]
                     runAsNonRoot=true
                     seccompProfile RuntimeDefault|Localhost
     <- you derived all four by experiment. restricted is
        just those four made non-optional. and the refusal
        NAMES each one, with the value it wants.

   NOTHING HERE NEEDS THE KERNEL TO REFUSE ANYTHING
     hostPath and hostNetwork are FIELDS, asked for politely,
     in a valid manifest. so the only place to say no is
     ADMISSION -- before the object exists.

   ONE PREDICATE, THREE VERBS  (set all three at once)
     enforce -> 403, "violates"
     warn ---> HTTP warning header, "would violate", CREATED
     audit --> audit log only. client sees NOTHING.
     three verbs exist because THE MIGRATION IS THE HARD PART.
     warn+audit -> collect -> fix -> enforce.

   enforce-version: latest is a HAZARD
     the definition of "restricted" GROWS between releases.
     latest => a cluster upgrade is also a policy change and
     year-old Pods start failing. pin it. remember to move it.

   THE GAP THAT BITES: A DEPLOYMENT IS NOT A POD
     enforce=restricted + create deployment
       -> "deployment.apps/web created"   (only a WARNING)
       -> 0/1 forever, no error in kubectl get
       -> the 403 is a FailedCreate EVENT on the ReplicaSet
     because PSA's predicate is on the POD resource, and the
     admitted object was a Deployment. so enforce DEGRADES to
     warn for everything that merely CONTAINS a pod template.
     CI goes green. the rollout hangs. events expire.

   AND THE LABEL IS NOT THE POLICY
     --admission-control-config-file -> AdmissionConfiguration
       defaults:   the level for UNLABELLED namespaces
       exemptions: usernames | runtimeClasses | namespaces
     MEASURED: ns labelled enforce=baseline, exempt in the file,
     runs a privileged Pod with CapEff 000001ffffffffff.
     the label is still there. it enforces NOTHING.
     -> auditing PSA by reading labels is unsound BOTH ways.
        the truth is a file on a node, behind a flag.

   THE THREE-PART EDIT YOU WILL DO THREE TIMES THIS ACT
     1. the --flag
     2. a hostPath VOLUME
     3. a volumeMOUNT into the apiserver container
     flag alone => apiserver cannot see the file => crashloop.
     write manifests with .tmp + mv: the kubelet is WATCHING.
```

**Cleanup:**

```bash
kubectl delete ns locked based warned plain --ignore-not-found
docker exec netlab-control-plane rm -rf /etc/kubernetes/admission /root/kube-apiserver.yaml.bak
```

> **You understand this when you can** explain why a Pod with no `securityContext` is not a malformed Pod, and what that implies about where hardening has to be enforced; name the three PSA levels and say what makes them cumulative; recite the four things `restricted` requires and point at the lesson that earned each one; say which of those four are container-level only and what happens if you put them at pod level; name three fields `baseline` blocks and explain why admission rather than the kernel is the right place to block them; distinguish `enforce`, `warn` and `audit` by who sees the result, and explain why a usable policy engine needs all three; say what `enforce-version: latest` does to a cluster upgrade; predict what happens when a Deployment's template violates an enforced policy, say which object carries the real error, and explain the reason in terms of which resource the predicate is about; perform the three-part API server edit and say which part is most often omitted and what the symptom is; write an `AdmissionConfiguration` that sets a cluster-wide default and exempts a namespace; and explain why enumerating namespace labels is an unsound audit of what a cluster enforces, in both directions.

**Which raises:** PSA is a genuinely good answer to lessons 01 and 02 — it takes a fixed list of fields somebody at the Kubernetes project chose and makes them mandatory. **A fixed list somebody else chose.** But the rules a real organisation needs are things like "images only from our registry", "never the `latest` tag", "every Pod carries a team label", "no LoadBalancer Services in staging" — every one of them a predicate over an object being written, every one of them exactly the kind of thing PSA does, and none of them expressible as a `pod-security.kubernetes.io/*` label, because nobody built a level for them. Act IX left this thread hanging when it showed that RBAC cannot hold a predicate and something in the cluster is evidently evaluating them anyway. **So where do you put a rule nobody built in — and why is admission the right place for it rather than the kernel or the rule store?**

---

↑ **[Act X overview](README.md)** · Prev: **[When the kernel says no](02-the-kernel-says-no.md)** · Next: *Deciding before it exists* — not yet written →
