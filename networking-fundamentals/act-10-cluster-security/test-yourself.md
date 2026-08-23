# Test yourself — Act X

Thirty questions. Same rule as every act: answer out loud or on paper *before* opening the answer.

This act has a particular trap for self-assessment, and it is worth naming. Almost every question below can be answered with a YAML field, and almost none of them are *about* a YAML field. If your answer is the name of a setting, you have probably answered a different question — the one this act keeps asking is **when does this refuse, what did it know then, and what got past it**.

Questions 1–4 are lesson 01, 5–7 lesson 02, 8–10 lesson 03, 11–13 lesson 04, 14–15 lesson 05, 16–18 lesson 06, 19–20 lesson 07, 21–24 lesson 08, 25–26 lesson 09, 27–28 lesson 10, 29–30 lesson 11.

---

**1.** A Pod with no `securityContext` at all. Is its process root, and is it therefore root on the node? Answer both halves separately.

<details><summary>Answer</summary>

It is uid 0, and it is *not* root on the node. Those are different claims and the gap between them is the whole subject of lesson 01.

The measurement: a default Pod runs as uid 0 and yet cannot `sethostname` — `Operation not permitted` — because its effective capability set is **14 of 41**. Root in a container is root with most of root's powers removed, and the ones removed are the *reconfigure the machine* powers.

What it does still hold is worth knowing rather than being reassured about: `dac_override` (ignore all file permission checks), `setuid`, and `net_raw`.

</details>

**2.** Who chose those fourteen capabilities?

<details><summary>Answer</summary>

**The container runtime, not Kubernetes.** The identical set appears under `docker run`, which is how you can tell. This matters because it means the baseline security posture of your workloads is a property of the runtime on each node, not of anything in your cluster's API — so it can differ between node pools and nothing in a Pod spec records it.

</details>

**3.** You add `capabilities: {add: ["CAP_NET_BIND_SERVICE"]}`. What happens?

<details><summary>Answer</summary>

It is accepted silently and grants **nothing**. Kubernetes expects the name without the `CAP_` prefix, so `CAP_NET_BIND_SERVICE` is an unrecognised string rather than an error — a Pod that reviews as hardened and is not.

That is the act's characteristic bug in its smallest form, and the general lesson is that a control which accepts your input is not the same as a control that understood it.

</details>

**4.** `drop: [ALL]`, uid 1000 — and the container binds port 80 anyway. Explain, and say what it teaches about capabilities generally.

<details><summary>Answer</summary>

Because `net.ipv4.ip_unprivileged_port_start` is `0` inside that container, versus `1024` on the machine underneath. **A capability is a gate, and a sysctl moved the gate.**

So `NET_BIND_SERVICE` is cargo on this runtime and load-bearing on another. The transferable point: a capability's meaning is not intrinsic — it is defined by the kernel checks that consult it, and those checks are themselves configurable. Reasoning about a capability list without knowing the sysctls is guessing.

</details>

**5.** `docker run` and a default Kubernetes Pod differ on one line of `/proc/self/status`. Which, and why is Kubernetes' choice defensible?

<details><summary>Answer</summary>

`Seccomp: 2` under Docker, `Seccomp: 0` in a default Pod. **Docker filters syscalls by default; Kubernetes does not.**

The defence is operational rather than principled: a kubelet runs arbitrary third-party workloads, and a default filter that breaks one of them breaks it at 3am on somebody else's cluster. `--seccomp-default` exists and is off, which is the project saying "you may take this trade, we will not take it for you".

</details>

**6.** You write a `Localhost` seccomp profile denying `chmod`, and run a container as root holding every capability. `chown` succeeds, `chmod` returns `EPERM`. What does that ordering prove?

<details><summary>Answer</summary>

That the **seccomp filter is consulted before the capability check**. There is no capability that could rescue `chmod`, because the syscall never reaches the code that would consult one.

This is the useful mental model for the two walls: seccomp decides whether the syscall happens at all; capabilities decide whether a syscall that is happening is permitted. They are not two implementations of one idea, and they fail with the same message — `Operation not permitted` — which is why `grep Seccomp /proc/<pid>/status` is the only way to tell them apart.

</details>

**7.** Why does AppArmor exist if seccomp is already filtering syscalls?

<details><summary>Answer</summary>

Because seccomp cannot see paths. In `openat` the filename is a **pointer into the caller's memory**, and a seccomp filter runs in a context where dereferencing it is unsafe and racy — the caller could change it after the check. So seccomp can say "no `openat` at all" and never "no `openat` on `/etc/shadow`".

AppArmor sits in the LSM hooks, after the kernel has resolved the path, which is exactly where a path is a real thing. Two mechanisms because there are two moments, which is this act's whole shape at kernel scale.

</details>

**8.** Lesson 03's opening complaint about lessons 01 and 02, in one sentence.

<details><summary>Answer</summary>

**All of that hardening is optional, and a Pod that omits it is valid** — so the protection is a property of whoever last edited the YAML, which is not a property of the cluster at all.

</details>

**9.** `kubectl create deployment` into a namespace with `enforce=restricted`. Walk what happens.

<details><summary>Answer</summary>

It prints a warning, says `created`, and sits at 0/1 forever. The 403 is real but it happens to a *Pod*, created by a ReplicaSet controller, so it surfaces as a `FailedCreate` event on the ReplicaSet.

The mechanism: **PSA's predicate is on the Pod resource.** Anything that merely *contains* a pod template — Deployment, StatefulSet, CronJob, every operator's CRD — gets a warning instead of a refusal, so `enforce` silently degrades to `warn` for most of what people actually deploy. CI goes green, the rollout hangs, and events expire in an hour.

</details>

**10.** A namespace is labelled `pod-security.kubernetes.io/enforce: baseline`, and a privileged Pod runs in it at `CapEff 000001ffffffffff`. How, and what does it break about auditing?

<details><summary>Answer</summary>

An `AdmissionConfiguration` file, referenced by `--admission-control-config-file`, exempted the namespace. The label is still there and enforces nothing.

What it breaks is **label enumeration as an audit method, in both directions**: an unlabelled namespace can be refusing privileged Pods because of a cluster-wide default, and a labelled one can be exempt. A control's declaration and its configuration live at different layers, and the declaration is the one everybody reads.

(Lesson 10 gives the sound alternative: the `pod-security.kubernetes.io/enforce-policy` annotation in the audit log, which is the *resolved* policy per request.)

</details>

**11.** What has mutating admission been doing to every Pod you have made since Act V, without being asked?

<details><summary>Answer</summary>

Adding a ServiceAccount and a projected token volume — `kube-api-access-` plus five characters, with a ~3607-second token. Nobody installed it, nobody can opt out of it cluster-wide, and it has happened to every Pod in the course.

It is the cleanest available proof that admission control is not an optional add-on you install but a stage the API server always runs, and it is where lesson 07's whole subject came from.

</details>

**12.** `timestamp(now())` in a `ValidatingAdmissionPolicy` fails. At what point, and why is that the right design?

<details><summary>Answer</summary>

It fails to **compile** — `undeclared reference to 'now'` — not at evaluation.

CEL in the write path must be deterministic and total: it runs on every matching request, it must terminate, and two evaluations of the same input must agree. A clock breaks the first and last of those. So a richer expression language closes the *syntax* gap Act IX found in RBAC and cannot touch the *interface* gap, and knowing which of those two you are facing is the difference between choosing a better tool and needing a different kind of tool.

</details>

**13.** Scale an admission webhook to zero. Contrast `failurePolicy: Fail` and `Ignore`, and say why `ValidatingAdmissionPolicy` has no equivalent choice.

<details><summary>Answer</summary>

`Fail` refuses an **allowed** image with `connection refused` — no Pods can be created anywhere in scope. `Ignore` admits a **forbidden** one with no error, no warning, and nothing recorded on the object.

So the choice is literally "the cluster stops working" versus "the cluster stops being protected", and there is no third option as long as the decision requires a network call to something that can be down.

VAP has no such pair because **nothing separate has to be alive** — the expression evaluates inside the API server. That is an operational argument for CEL, not a security one, and it is the strongest argument CEL has.

</details>

**14.** You uninstall Kyverno with `kubectl delete -f install.yaml`, every object reports deleted, and the cluster stops accepting Pods in one namespace. What happened?

<details><summary>Answer</summary>

Ten webhook configurations survived, because they were **never in `install.yaml`** — a controller wrote them at runtime from the policies that existed. `kubectl delete -f` deletes what a file describes, and the file does not describe them.

What is left is a registration with `failurePolicy: Fail` pointing at a Service that no longer exists, so the error is `service "kyverno-svc" not found` rather than `connection refused` — meaning whoever debugs it is looking for a Deployment nobody can find. The fix is to delete by the label the engine puts on its own handiwork.

The general shape: **an operator's runtime output is not covered by its install manifest**, and uninstalling by manifest is a partial operation for anything that generates objects.

</details>

**15.** Three products, one shape. Name it and the three instances.

<details><summary>Answer</summary>

**A rule, and a separate statement of where it is switched on.** `ValidatingAdmissionPolicy` + `ValidatingAdmissionPolicyBinding`; `ConstraintTemplate` + `Constraint`; and in Kyverno a policy plus the generated rules that decide where it applies. (Act VII's `StorageClass` + `PVC` and lesson 11's `SecretStore` + `ExternalSecret` are the same shape again.)

Three teams reached it without coordinating, which is decent evidence it is a property of the problem rather than an API quirk: the rule is the expensive thing to write and review, and where it applies is the thing that changes weekly.

</details>

**16.** You enable encryption at rest correctly. Does `kubectl get secret -o yaml` still show the value, and what follows?

<details><summary>Answer</summary>

Yes, of course — the API server holds the key and decrypting on read is its job. If it stopped working, every workload would break.

What follows is the precise scope of the purchase: **encryption at rest defends the store, not the API.** The only thing between a caller and the plaintext is what was there yesterday — RBAC. What is newly unavailable is a stolen etcd snapshot, the disk or its volume snapshot, and anything reading etcd directly without API credentials. That is a real and common threat set. It is just not what people picture.

</details>

**17.** You enable it, rewrite every Secret so they are all ciphertext, verify with `etcdctl`, take a snapshot, and grep it for the password. What do you find and why?

<details><summary>Answer</summary>

**The plaintext.** etcd is MVCC: a write appends a revision rather than overwriting, so the key is at `version: 2` with the old plaintext revision still present — and a snapshot contains the store, history included.

`etcd compact <current-rev>` discards it, after which the grep returns zero. `--etcd-compaction-interval` defaults to 5m but is a schedule, not a guarantee — the superseded revision was still present in a snapshot taken 400 seconds later.

And the part no fix reaches: **your backup retention is your plaintext retention.** Any snapshot taken between the Secret existing and the compaction contains it forever, and there is no command that reaches into files you have already shipped.

</details>

**18.** State the rule governing the `providers` list, and derive key rotation from it.

<details><summary>Answer</summary>

**The first provider encrypts. Every provider is tried, in order, for decryption.**

Rotation follows: list the new key *second* so every API server can read what any of them writes, restart them all, then promote it to first, rewrite every Secret, compact, and finally drop the old key. **A key must be able to decrypt before it is asked to encrypt** — skip that on multi-master and one server writes ciphertext its peers cannot read, which presents as a Secret that is readable through some connections and not others.

The same rule gives turn-on, turn-off and rollback, and it is why `identity` in first position silently disables everything while leaving a perfectly good AES key in the file.

</details>

**19.** You copy a Pod's token, delete the Pod, and present the token. Predict the code and name the flag.

<details><summary>Answer</summary>

`401`, not `403` — and the distinction is the point, because Act IX taught you those answer different questions. The token stops *authenticating*, rather than authenticating a principal who is then refused.

The mechanism is that a projected token carries a bound object reference — the Pod and its UID — and the API server checks the referent still exists. The general trick, stated without Kubernetes: **make the credential's validity depend on a fact the verifier can check cheaply at verification time**, which is how you get a third option out of Act IX's freshness-versus-availability trade instead of choosing between short lifetimes and a revocation list.

</details>

**20.** `--anonymous-auth=true` is the default on the API server and a catastrophe on a kubelet. Same flag, opposite verdict. Why?

<details><summary>Answer</summary>

Because a flag that lets a request in is only as safe as **the authorizer behind it**. On the API server, an anonymous request falls through to RBAC, where "nobody" is an ordinary name with ordinary rules — measured as `200` on `/healthz` and `403` on everything else. On a kubelet configured with `authorization: AlwaysAllow` there is nothing to fall through to.

So the rule is to **assess the pair, never the flag** — and that generalises to every "allow unauthenticated" setting you will ever review.

</details>

**21.** Two Pods, byte-identical specs except `imagePullPolicy`, same node, same minute. Can they run different programs?

<details><summary>Answer</summary>

Yes, and this is the measurement to remember. With the tag re-pointed between the two creations: `IfNotPresent` ran BusyBox 1.36 from the node's cache, `Always` pulled and ran 1.37.

`.spec.containers[0].image` is *identical* on both. So **a Pod spec is not a description of what is running** — it names something to resolve, and the resolution happened elsewhere at a time nobody recorded. Every code review, `kubectl diff` and GitOps repository reads that field. The only field that tells the truth is `status.containerStatuses[].imageID`, which is a digest.

</details>

**22.** Lesson 04 defeated an image allowlist by writing `docker.io/library/busybox:1.36` instead of `busybox:1.36`. How is lesson 08's problem the same problem?

<details><summary>Answer</summary>

Lesson 04 was **one set of bytes under two names**. Lesson 08 is **one name over two sets of bytes**. Both are consequences of the single fact that a tag is a mutable pointer, so a rule that reads a tag is reading a variable.

Which is why better string handling was never the fix, and why a digest is: content addressing makes the reference *be* the content, so it has no synonyms and cannot be re-pointed.

</details>

**23.** Where does a cosign signature live, how is it named, and what does that design permit?

<details><summary>Answer</summary>

**A tag in the same repository as the image**, named by mechanical transformation of the digest: `sha256:abc…` becomes `sha256-abc….sig`. No new server and no new protocol — a registry is a content-addressed blob store that will hold anything, so a verifier *computes* where to look. That is why signing works air-gapped.

And it permits exactly one thing you must plan for: **whoever can push the image can push beside it.** Measured — an attacker signed unsigned content with their own key, and both signatures sat in the repository, both valid. What they cannot do is forge a signature verifying against a key they do not hold, which is why "the image is signed" carries no information and "signed by a key we chose in advance" carries all of it.

</details>

**24.** `mutateDigest: true` on an image policy. What does it do and which two problems does it close?

<details><summary>Answer</summary>

On successful verification it rewrites `spec.containers[].image` from `registry/app:v2` to `registry/app:v2@sha256:…` — the OCI form where the digest wins and the tag survives as documentation.

It closes the **rename** hole (a digest has no synonyms) and the **re-point** hole (whoever moves the tag tomorrow cannot reach this Pod), with one object. It is also why a single policy registers *both* a mutating and a validating webhook, and why lesson 04's measured mutation-before-validation ordering is required rather than incidental: you must resolve the tag to a digest before judging whether that digest is signed, or you are checking a different thing from the one you pin.

</details>

**25.** A `NetworkPolicy` is provably enforcing — an unlabelled client gets nothing. Does the permitted conversation's payload stay private?

<details><summary>Answer</summary>

No. Measured: the password appeared four times in a twenty-five packet capture while the policy was refusing everything else.

**A `NetworkPolicy` decides who may open a connection. It has no opinion about who may read one.** It is an ACL on the initiation of traffic, which is Act IX's RBAC one layer down, and confidentiality is not the kind of thing it does. "We have a default-deny network policy" and "our internal traffic is protected" are unrelated claims, and the first is routinely offered as evidence for the second.

</details>

**26.** You enable Cilium's WireGuard encryption and verify it works. Name the pair of Pods still exchanging plaintext, and explain rather than just naming.

<details><summary>Answer</summary>

**Two Pods on the same node** — measured at eight plaintext occurrences with encryption confirmed active.

The explanation is the mechanism: what is encrypted is the *link between nodes*. Two Pods on one node have no such link; the packet crosses two veths inside one kernel and never reaches a wire. There is nothing for a transport encryption scheme to encrypt, so it correctly encrypts nothing.

Two consequences worth stating. The protection is **non-deterministic** — the same Deployment is covered or not depending on where the scheduler placed the replicas this morning — which makes `podAntiAffinity` a security control nobody writes down as one. And the defended adversary is one *between* your nodes, never one *on* one.

</details>

**27.** Name the field in an audit entry that answers a question Act IX said was expensive, and say what it is for.

<details><summary>Answer</summary>

`annotations["authorization.k8s.io/reason"]`, e.g. `RBAC: allowed by ClusterRoleBinding "kubeadm:cluster-admins" of ClusterRole "cluster-admin" to Group "kubeadm:cluster-admins"`.

**The log records which rule allowed the request.** Act IX's hard direction was *who can do X*, which needs every binding enumerated. This answers the retrospective form — who did, and by which grant — for free, and it is the evidence you need to remove a permission without guessing what breaks.

Its neighbour is worth knowing too: `extra["authentication.kubernetes.io/credential-id"]` names the *specific* certificate by SHA-256, which is what makes "rotate the compromised credential" an actionable sentence.

</details>

**28.** Somebody `kubectl exec`s into a Pod and types three commands. How many are in the audit log, and what status code explains it?

<details><summary>Answer</summary>

**None.** The request URI records only `command=sh`, because `kubectl` puts *arguments* in the query string — so a command passed on the command line is fully legible, and anything typed into an interactive shell is not.

The mechanism is in the entry: **`code: 101`**, Switching Protocols. The API server upgraded the connection and became a byte pipe; from that moment it is not parsing requests, so there are no requests to log. It does not lose the commands — it records the last moment at which it could see anything.

Which gives the definition: **an audit log is a record of requests to the API server, and nothing else is a request to the API server.** Not a process starting, not a file being read, not a packet. The whole `CREATE`/`RUN` end of this act is out of its reach, which is what runtime detection is for.

</details>

**29.** The External Secrets Operator syncs a value from an outside store. How many of Act VII's three locations does that remove?

<details><summary>Answer</summary>

**Zero.** What it produces is an ordinary Kubernetes Secret; `etcdctl` reads the plaintext straight out of etcd, the kubelet will write it to `tmpfs` on whatever node mounts it, and an environment variable is still an environment variable.

It changes who *owns* the value, not where the value is. What that buys is operational and real — one place to revoke, rotation with no deploy, an audit trail on the authoritative copy, and a shelf life on the plaintext in any snapshot — and none of it is a substitute for encryption at rest, because it defends against bad process rather than a stolen file.

The pattern that does remove one is the CSI driver, which creates no Secret at all: etcd is gone, the node's `tmpfs` copy is not.

</details>

**30.** The operator needs a credential for the external store, which is a secret, which needs storing. Resolve the circularity.

<details><summary>Answer</summary>

The cluster is an **OIDC issuer** — it publishes `/.well-known/openid-configuration` and a JWKS, which Act IX had you use without saying what it was for.

So: mint a ServiceAccount token with `--audience` set to the external service. Its `sub` is `system:serviceaccount:<ns>:<name>` plus the ServiceAccount's UID, and its `aud` is not this cluster — so the API server would reject it and the store cannot replay it. The store verifies the RS256 signature against the published JWKS using nothing but a public key and arithmetic. **It never calls the cluster, and there is no shared secret anywhere in the exchange, so there is none to store, rotate or leak.**

That is IRSA, GKE Workload Identity and workload identity federation, all three. It also retires the act's oldest loose end: the projected token volume lesson 04 found on every Pod, that nobody asked for and nobody can opt out of, is the bootstrap credential — good precisely because it is short-lived, audience-scoped, UID-bound, and verifiable by a party that has never spoken to your cluster.

And it is lesson 08's shape again: **a signature is how a claim survives leaving the system that made it.**

</details>

---

↑ **[Act X overview](README.md)** · Next: **[Diagnose it](diagnose.md)** →
