# CKS domain map — curriculum v1.34

Transcribed verbatim from `CKS_Curriculum v1.34.pdf`
([`github.com/cncf/curriculum`](https://github.com/cncf/curriculum) — note the space, not an
underscore, in that filename), cross-checked against the
[LF program-changes page](https://training.linuxfoundation.org/cks-program-changes/).

> **Version mismatch, and it matters.** The curriculum document is at **v1.34** while CKA/CKAD are
> already at v1.35 — but both the *Important Instructions: CKS* page and the LF certification page
> state the exam environment runs **Kubernetes v1.35**. The document lags the environment. **Study
> against 1.35 behaviour** (this is why the AppArmor guidance below uses the field, not the
> annotation).

**Prerequisite:** you must have passed CKA. It does **not** need to be active — an expired CKA
qualifies you to schedule CKS. And under the CARE program, in force since 18 June 2026, passing CKS
reinstates or extends your CKA.

## Weightings

| Domain | Weight |
|---|---|
| [Minimize Microservice Vulnerabilities](#minimize-microservice-vulnerabilities--20) | **20%** |
| [Supply Chain Security](#supply-chain-security--20) | **20%** |
| [Monitoring, Logging and Runtime Security](#monitoring-logging-and-runtime-security--20) | **20%** |
| [Cluster Setup](#cluster-setup--15) | **15%** |
| [Cluster Hardening](#cluster-hardening--15) | **15%** |
| [System Hardening](#system-hardening--10) | **10%** |

> **Two widely-cited sources publish the wrong weights.** Both `cncf/curriculum/cks/README.md`
> itself and the popular `walidshaari/Certified-Kubernetes-Security-Specialist` repo still show
> **Cluster Setup 10% / System Hardening 15%** — the pre-October-2024 split. The PDF and the LF
> program-changes page both say 15/10. Trust those.

## Course coverage, stated plainly

**[Act X](../networking-fundamentals/act-10-cluster-security/README.md) now covers most of CKS**, and
this map was rewritten against it. Eleven lessons, every command run against a real cluster: workload
hardening and capabilities, seccomp and AppArmor, Pod Security Admission, admission control from a
hand-built webhook up to two policy engines, encryption at rest, the cluster's own open doors and a
CIS benchmark run, supply-chain verification with digests and signatures, Pod-to-Pod encryption on a
second cluster with Cilium and WireGuard, audit logging and runtime detection with Falco, and
external secret stores.

**Two competencies are outright gaps**, both marked ❌ below: static analysis with **Kubesec /
KubeLinter**, and **host OS footprint** reduction. Both are cheap to rehearse and neither is worth
much of the syllabus.

**Four more read 🟡 for a reason worth stating once, because it is the same reason each time: the
course teaches the control and never makes you author the artifact.** A Falco rule you wrote rather
than one you watched fire; an AppArmor profile that can actually load; gVisor actually running;
Istio's `PeerAuthentication`. Every one of those is a thing you would type on exam day, and reading
about it does not transfer. Counting a 🟡 as a half: **19½ of 26 bullets, about 75% of the syllabus** —
strong, and not the ~90% an all-✅ table would have implied. (This total previously read *20 of 26,
about 77%*, which counted the AppArmor/seccomp row as a whole bullet on the strength of its own note
that the seccomp half *"would earn ✅ on its own."* Half a bullet is half a bullet. The arithmetic of
this table is the only thing it has.) The rows below say precisely what is
missing in each case rather than making you guess.

**Read the 🟡 rows carefully, because they are where a pass is lost.** In each of them the course
teaches the mechanism and does not build the exam's specific artifact — `bom` rather than `trivy`'s
SBOM, Istio's `PeerAuthentication` rather than Cilium's flag, gVisor actually running rather than
`RuntimeClass` named, a Falco rule you wrote rather than one you watched fire, an AppArmor profile
that can actually load. Understanding transfers; muscle memory under a clock does not, which is the
entire reason this `exam-prep/` track exists separately from the lessons.

**And one shortfall inside a ✅ row, because it does not fit the pattern above.** The *Secure your
supply chain* row is ✅ on the strength of a hand-built admission webhook and real `cosign`
verification — but the exam's named artifact for permitted registries is **`ImagePolicyWebhook`**, and
that specific object is built nowhere in the course. Rehearse it separately; the row says so in place.

One warning that survives Act X unchanged: the act is written to make you understand these controls,
and the exam is written to make you configure them in about seven minutes each. Act X's lessons will
tell you *why* `defaultAllow: false` matters; they will not make your fingers fast.

Coverage key: ✅ covered · 🟡 partial · ❌ gap. Rate yourself: `-` untried · `?` shaky · `✓` under a clock.

---

## Minimize Microservice Vulnerabilities — 20%

| Sub-competency | Coverage | Notes | Me |
|---|---|---|---|
| Use appropriate pod security standards | ✅ covered | [Lesson 03](../networking-fundamentals/act-10-cluster-security/03-a-default-that-refuses.md) does all of this and measures the two traps: `enforce` degrades to `warn` for anything containing a pod template, and a labelled namespace can be exempted so label-enumeration is an unsound audit. **PSA — reported as "a common opener" and "the fastest win."** [Drill 9](../networking-fundamentals/act-10-cluster-security/diagnose.md) hides three postures that all *look* hardened and makes the obvious probe fail: a privileged Pod is refused by a namespace pinned to `enforce-version: v1.21` as surely as by an unpinned one, because `privileged` carries no version annotation. Only a Pod violating a control **added after** the pin — `capabilities.drop: ["ALL"]`, a v1.22 addition — separates them. Worth knowing cold: a version pin can only weaken the checks that postdate it. Namespace labels `pod-security.kubernetes.io/{enforce,audit,warn}` = `privileged |baseline|restricted` (+ `-version`). Know what `baseline` vs `restricted` forbids, **and** the cluster-wide route: `AdmissionConfiguration` → `PodSecurityConfiguration` (`defaults`, `exemptions`) via `--admission-control-config-file`. | `-` |
| Manage kubernetes secrets | ✅ covered | [Lesson 06](../networking-fundamentals/act-10-cluster-security/06-a-secret-that-is-actually-secret.md) for `EncryptionConfiguration` (including the provider-order rule and the compaction step every guide omits) and [lesson 07](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) for projected tokens and `automountServiceAccountToken`. The examined material is `EncryptionConfiguration`, RBAC, `automountServiceAccountToken: false`, projected tokens — **not** Vault/ESO/Sealed Secrets (see the warning below). | `-` |
| Understand and implement isolation techniques (multi-tenancy, sandboxed containers, etc.) | 🟡 partial | [Lesson 02](../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md) introduces `RuntimeClass` and measures `no runtime for "runsc" is configured`; gVisor is never actually run, and multi-tenancy is an explicit omission ([in the wild](../networking-fundamentals/act-10-cluster-security/in-the-wild.md)). Lead with **RuntimeClass** (`node.k8s.io/v1`, `handler: runsc`, then `runtimeClassName`). gVisor and Kata are **no longer named** — the competency generalised. Expect `runsc` pre-configured in containerd; gVisor's own docs are not allowed. | `-` |
| **Implement Pod-to-Pod encryption (Cilium, Istio)** | 🟡 partial | [Lesson 09](../networking-fundamentals/act-10-cluster-security/09-encryption-between-pods.md) does Cilium WireGuard end to end on a second cluster — including the measurement most guides miss, that same-node traffic stays plaintext — but Istio and `PeerAuthentication` are described rather than run. Both `docs.cilium.io` and `istio.io` are whitelisted, so this is real. See below. | `-` |

### Pod-to-Pod encryption — the competency most study guides miss

**Cilium:** WireGuard is the easy path — `encryption.enabled=true`, `encryption.type=wireguard`, no
key management. Verify with `cilium status` / `cilium encrypt status` and by finding the
`cilium_wg0` interface. IPsec is the alternative and needs a `cilium-ipsec-keys` secret in
`kube-system`.

**Istio:** sidecar injection via `kubectl label ns X istio-injection=enabled`, then
`PeerAuthentication` with `mtls.mode: STRICT`. **Getting the scope right is the graded part** —
mesh-wide means putting it in the root namespace (`istio-system`), versus a single namespace, versus
a workload `selector`. One first-hand report describes it as "quick and simple changes to deploy
sidecars."

> ⚠️ **Do not invest in Vault, External Secrets Operator, or Sealed Secrets for this exam.** There
> is no curriculum mention, no whitelisted docs, and no first-hand report. They are good production
> practice and worth learning — just don't count them as CKS preparation.

---

## Supply Chain Security — 20%

| Sub-competency | Coverage | Notes | Me |
|---|---|---|---|
| Minimize base image footprint | 🟡 partial | [Lesson 08](../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) adds the sharp end of this: a minimal image scans to `Target -`, which the tool's own legend distinguishes from `0`. [image layers and the secret leak](../networking-fundamentals/act-1-one-machine/06b-the-container-filesystem.md) gets you the mechanism; multi-stage builds, distroless and non-root images are gaps | `-` |
| Understand your supply chain (e.g. SBOM, CI/CD, artifact repositories) | 🟡 partial | [Lesson 08](../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) generates a CycloneDX SBOM, re-runs the scan against the SBOM alone, and measures the two entry points disagreeing — but it uses `trivy`, not the exam's tool. **Use `bom`, not syft** — see below | `-` |
| Secure your supply chain (permitted registries, sign and validate artifacts, etc.) | ✅ covered | [Lesson 04](../networking-fundamentals/act-10-cluster-security/04-deciding-before-it-exists.md) builds a registry-allowlist admission webhook by hand and then defeats it by renaming; [lesson 08](../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) does digests, `cosign sign`/`verify`, and cluster-side verification with `mutateDigest`. **The one artifact the course does not build is `ImagePolicyWebhook` itself** — rehearse that separately. **ImagePolicyWebhook** for permitted registries; cosign for signing | `-` |
| Perform static analysis of user workloads and container images (e.g. **Kubesec, KubeLinter**) | ❌ gap | Both named in the curriculum yet neither has docs or a single first-hand report — the clearest "named but unverified" case. Cheap to rehearse anyway. | `-` |

### `bom` is the SBOM tool — this is the most under-appreciated finding

SBOM is curriculum-named, **`bom` has its own whitelisted docs domain**
(`kubernetes-sigs.github.io/bom/cli-reference/`), and a first-hand Kubestronaut write-up names "the
Bom utility by the Kubernetes project" on their supply-chain tasks. Learn:

- `bom generate --image <img> -o sbom.spdx`
- `bom generate --dirs .`
- **`bom document outline sbom.spdx`** — to *read* an SBOM and answer questions from it

**Corollary: `syft` has no curriculum mention, no docs, and no reports. Skip it.**

### The three items to calibrate carefully

**ImagePolicyWebhook** (for "permitted registries") is implied, first-hand reported, and documented
on kubernetes.io. It is a **three-file** setup: (1) `AdmissionConfiguration` naming the plugin and a
path, (2) the ImagePolicyWebhook config (`kubeConfigFile`, `allowTTL`, `denyTTL`, `retryBackoff`,
`defaultAllow: false`), (3) a kubeconfig pointing at the webhook — then `--enable-admission-plugins`
and `--admission-control-config-file` in the apiserver manifest **with hostPath mounts**.
**`defaultAllow: false` is the usually-graded detail.**

**Trivy** is *not* curriculum-named and **Trivy docs are not allowed** — contrary to several 2025
guides. But consensus says image scanning appears. From memory:
`trivy image --severity HIGH,CRITICAL --quiet <img>`, `--input archive.tar` for offline,
`--ignore-unfixed`, `-f json`. Two operational traps: **run it on the host the question names**
(often the control plane, since that's where it's installed), and **fix only what's asked** — extra
remediation earns nothing. Fallback: `trivy image --help`.

**cosign is the least-settled item in this whole map.** The competency says only "sign and validate
artifacts"; sigstore docs are **not** whitelisted; no first-hand report found. Learn the four
commands (`generate-key-pair`, `sign --key`, `verify --key`, plus registry-allowlist admission) and
stop there.

---

## Monitoring, Logging and Runtime Security — 20%

| Sub-competency | Coverage | Notes | Me |
|---|---|---|---|
| Perform behavioral analytics to detect malicious activities | 🟡 **partial — the course consumes Falco, the exam asks you to author for it** | [Lesson 10](../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md) installs Falco with `driver.kind=modern_ebpf`, gets a real detection, and measures the limit of the alert. What it never does is **write a rule**: `- rule:`, `condition:`, `output:`, `priority:`, `/etc/falco/falco.yaml`, `rules_files` and overriding a shipped rule are all absent from the course. One reported candidate *"had to improvise and write a new one from scratch."* Practise authoring one custom rule and reloading it | `-` |
| Detect threats within physical infrastructure, apps, networks, data, users and workloads | ✅ covered | [Lesson 10](../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md), and it also measures the limit: the alert arrives with `k8s_pod_name=<NA>`. Falco | `-` |
| Investigate and identify phases of attack and bad actors within the environment | ✅ covered | [Lesson 10](../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md) plus [diagnose](../networking-fundamentals/act-10-cluster-security/diagnose.md) drill 5 — the audit log knows *who* and not *what*, the runtime sensor the reverse, so an investigation is a join on container ID and timestamp. audit-log forensics with `jq` | `-` |
| Ensure immutability of containers at runtime | ✅ covered | [Lesson 01](../networking-fundamentals/act-10-cluster-security/01-what-a-container-may-do.md) measures all three, including that `readOnlyRootFilesystem` breaks `/tmp` and what `allowPrivilegeEscalation: false` actually stops. [Drill 10](../networking-fundamentals/act-10-cluster-security/diagnose.md) hides the trap in the stanza: **nothing validates a capability name**, so `add: ["CAP_CHOWN"]` — the kernel's spelling rather than the manifest's — is accepted, adds nothing, and leaves a Pod that reviews as hardened and is missing the permission it was built around. `CapEff` in `/proc/self/status` is the only check. `readOnlyRootFilesystem`, no shell in image, `allowPrivilegeEscalation: false` | `-` |
| Use Kubernetes audit logs to monitor access | ✅ covered | [Lesson 10](../networking-fundamentals/act-10-cluster-security/10-seeing-it-happen.md) — the three-part edit, the four levels, and the measured trap that `RequestResponse` on Secrets writes plaintext passwords to disk. see the trap below | `-` |

### Falco — expect to write a rule from scratch

Falco is **not** curriculum-named, but `falco.org/docs` is whitelisted and it is first-hand
reported, which makes it effectively certain. The important calibration, from a September 2025
candidate: *"I expected to only modify existing Falco rules, but had to improvise and write a new
one from scratch as default rules didn't capture the events."*

Rule shape: `- rule:` / `desc:` / `condition:` / `output:` / `priority:` / `tags:`, plus `- macro:`
and `- list:`. Output fields worth memorising: `%evt.time`, `%container.id`, `%container.name`,
`%container.image.repository`, `%k8s.ns.name`, `%k8s.pod.name`, `%proc.name`, `%proc.cmdline`,
`%user.name`, `%fd.name`.

File layout: `/etc/falco/falco.yaml` holds the `rules_files:` list ·
`/etc/falco/falco_rules.yaml` is **shipped — don't edit, it's overwritten on upgrade** ·
`/etc/falco/falco_rules.local.yaml` is where custom rules go · `/etc/falco/rules.d/`.
**Later files win on duplicate rule names** — that is how you override a shipped rule. Reload using
the method the task specifies rather than restarting blindly.

> ⚠️ Recent Falco releases moved rules to `falcoctl`-managed artifacts. **Read `rules_files:` on the
> actual exam box** rather than assuming these paths.

### Audit logging — and the mark people lose

Write an `audit.k8s.io/v1` `Policy`: rule **ordering matters**, `level: None|Metadata|Request|RequestResponse`,
plus `resources`, `namespaces`, `verbs`, `users`, `omitStages`. Then wire `--audit-policy-file`,
`--audit-log-path` and the `--audit-log-maxage`/`maxbackup`/`maxsize` trio into
`/etc/kubernetes/manifests/kube-apiserver.yaml`.

**The graded detail: you must also add the hostPath volume *and* the volumeMount — and the mount
must not be `readOnly`.** That is where candidates lose it. Confusing `Metadata` vs `Request` vs
`RequestResponse` is the other named recurring mistake. Then be ready to `jq` the log to answer an
investigation question ("who deleted this", "all exec sessions").

---

## Cluster Setup — 15%

*(Raised from 10% in October 2024.)*

| Sub-competency | Coverage | Notes | Me |
|---|---|---|---|
| Use Network security policies to restrict cluster level access | ✅ covered | [NetworkPolicy](../networking-fundamentals/act-5-kubernetes/07-network-policy.md) for the model, including the two things most material misses — a denial *times out* rather than returning 403, and whether your CNI enforces at all is something you measure with a default-deny and two curls rather than look up. Then [the four shapes](../networking-fundamentals/act-5-kubernetes/07b-policy-shapes.md) for the **cluster-level** half this bullet actually asks about: cross-namespace peers, the AND-vs-OR hyphen, `ipBlock` with `except`, and a `policyTypes: [Egress]` default-deny with the DNS outage and the `kubernetes.io/metadata.name` fix. Note which mistake is dangerous — the one that fails **open** files no ticket | `-` |
| Use CIS benchmark to review the security configuration of Kubernetes components (etcd, kubelet, kubedns, kubeapi) | ✅ covered | [Lesson 07](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) runs `kube-bench`, connects its findings to specific lessons, and shows two of them are unfixable. `kube-bench` — see below | `-` |
| Properly set up Ingress objects with TLS | ✅ **covered** | [Ingress with a TLS Secret and SNI](../networking-fundamentals/act-5-kubernetes/06-ingress.md). Note: **create TLS secrets with `kubectl create secret tls`, not by hand-editing a manifest** — a named failure. | `-` |
| Protect node metadata and endpoints | 🟡 partial | [Lesson 07](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) covers the kubelet side thoroughly (port 10250, anonymous auth, `authorization.mode`, and why the same flag is right on the apiserver and fatal here); the cloud metadata IP is still a gap, though its remedy is now buildable: an `egress` policy with an `ipBlock` is exactly [the four shapes](../networking-fundamentals/act-5-kubernetes/07b-policy-shapes.md), and blocking `169.254.169.254/32` is that lesson's `except` field pointed at one address. There is no cloud metadata endpoint on a `kind` node to prove it against. NetworkPolicy egress to the metadata IP; kubelet `readOnlyPort: 0` | `-`. [the authoring sprint](authoring-sprint.md) item 6 closes the egress half by making you write it: `podSelector: {}` with `policyTypes: [Egress]` and an `ipBlock` of `0.0.0.0/0` carrying `except: [169.254.169.254/32]`, because **there is no deny in a NetworkPolicy** and allowing everything else is the only available shape. The trap it makes you meet is the second rule — an egress default-deny takes **DNS** with it, since CoreDNS sits at a ClusterIP and a ClusterIP is not covered by an `ipBlock` at all, so the policy written one line short produces a namespace where nothing resolves. And the honest limit, stated there: on this cluster the verdict is made in **userspace** behind `queue flags bypass`, so a metadata block that stops existing when an agent restarts is a preference rather than a boundary | `-` |
| Verify platform binaries before deploying | 🟡 partial | [Lesson 08](../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) teaches exactly this mechanism — digests and signature verification — applied to images rather than to release binaries. checksum/signature verification of Kubernetes release binaries | `-`. [the authoring sprint](authoring-sprint.md) item 7 adds the client-side half and the format trap: `kubectl.sha256` holds a bare hash with no filename, so `shasum --check kubectl.sha256` fails with *"no properly formatted SHA checksum lines found"* — which reads like a download problem and is a format problem; the two-field line has to be constructed. It also states what the check does **not** buy: the hash arrived over the same connection from the same host as the binary, so it defends against corruption and against a mirror that changed one of the two, and not at all against anyone who can serve both — which is the gap a signature closes | `-` |

**kube-bench** is not itself curriculum-named (CIS is) and has no allowed docs — but that's fine,
because **the tool prints its own remediation text**. A September 2025 candidate: *"running and
fixing issues according to kube-bench, which often involved only copying and pasting the right
commands from suggested fixes."* Run `kube-bench run --targets=master,node`, read the FAILs, apply
the printed fix. Classic ones: `--anonymous-auth=false`, `--authorization-mode=Node,RBAC`,
`--profiling=false`, `protectKernelDefaults: true`, `readOnlyPort: 0`, file perms 600 / `root:root`.
Verify with `ps -ef | grep kube-apiserver` **after the kubelet restarts the static pod — don't
restart it manually.**

---

## Cluster Hardening — 15%

| Sub-competency | Coverage | Notes | Me |
|---|---|---|---|
| Use Role Based Access Controls to minimize exposure | ✅ covered | Act IX lesson 06 for the model, [lesson 07](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) for the Node authorizer and `NodeRestriction`. `kubectl auth can-i --as=system:serviceaccount:ns:sa verb resource`. Role vs ClusterRole vs the *binding's* namespace is the classic confusion. | `-` |
| Exercise caution in using service accounts (disable defaults, minimize permissions on new ones) | ✅ covered | [Lesson 07](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) is largely this competency, and [lesson 11](../networking-fundamentals/act-10-cluster-security/11-secrets-from-outside.md) shows what the projected token is actually *for*. `automountServiceAccountToken: false`; `kubectl create token --duration`; bound tokens since 1.21 | `-` |
| Restrict access to Kubernetes API | ✅ covered | [Lesson 07](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) — and its rule that a permissive auth flag is only as safe as the authorizer behind it. `--anonymous-auth=false`, RBAC, NetworkPolicy to the apiserver, `--authorization-mode` | `-` |
| Upgrade Kubernetes to avoid vulnerabilities | ✅ covered | Act VI lesson 06 covers upgrades and version skew. shared with CKA's lifecycle bullet | `-` |

**Secrets encryption at rest** lives across this and the Microservice Vulnerabilities domain, and it
used to be the biggest hole in the course. It no longer is: [lesson 06](../networking-fundamentals/act-10-cluster-security/06-a-secret-that-is-actually-secret.md)
generates the key, writes the ordered `providers` list, does the three-part apiserver edit, reads
`k8s:enc:aescbc:v1:key1:` out of etcd, re-encrypts, compacts, and then reverses the provider order to
prove the rule — which is above exam depth. [Act X drill 8](../networking-fundamentals/act-10-cluster-security/diagnose.md)
then hides the sharpest of its traps — `identity` first in `providers` — in a bench you build without
reading, so you meet it as a finding rather than as a paragraph, and drill 9 does the same for PSA
(`warn` without `enforce`, and an `enforce-version` pin that freezes a weaker standard). The material to have at your fingertips: `apiserver.config.k8s.io/v1` `EncryptionConfiguration` with an
**ordered** `providers` list (`aescbc`/`aesgcm`/`secretbox`/`kms`, then **`identity` last** — the
first provider encrypts, all are tried for decrypt), a base64 32-byte key,
`--encryption-provider-config` (plus `--encryption-provider-config-automatic-reload=true`). Then the
part people forget: **re-encrypt the existing Secrets** with
`kubectl get secrets -A -o json | kubectl replace -f -`. Verify with `etcdctl` showing the
`k8s:enc:aescbc:v1:` prefix.

---

## System Hardening — 10%

*(Lowered from 15% in October 2024.)*

| Sub-competency | Coverage | Notes | Me |
|---|---|---|---|
| Minimize host OS footprint (reduce attack surface) | ❌ gap | disable services, close ports | `-` |
| Using least-privilege identity and access management | ✅ **covered for what CKS examines** | Act IX lesson 06 builds RBAC vs ABAC from first principles and computes the reverse question against a live cluster; [lesson 07](../networking-fundamentals/act-10-cluster-security/07-the-doors-left-open.md) adds the Node authorizer and `NodeRestriction`. This row previously read 🟡 on account of *cloud* IAM, which is Stage 9 roadmap and outside the CKS syllabus — the in-cluster identity material is ✅-grade | `-` |
| Minimize external access to the network | 🟡 partial | NetworkPolicy egress is now covered — [the four shapes](../networking-fundamentals/act-5-kubernetes/07b-policy-shapes.md) builds a default-deny egress and the DNS allow it needs. Host-level firewalling (`iptables`/`nftables`/`ufw` on the node itself) is still a gap | `-` |
| Appropriately use kernel hardening tools such as **AppArmor, seccomp** | 🟡 **partial — seccomp yes, AppArmor not exercisable** | [Lesson 02](../networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md) does seccomp fully and would earn ✅ on its own: a `Localhost` profile, `RuntimeDefault`, and why the filter is consulted *before* the capability check. [Drill 11](../networking-fundamentals/act-10-cluster-security/diagnose.md) is the one that makes it stick — the same `localhostProfile` path on two nodes with different files behind it, both Pods Running, one enforcing and one not, and no field anywhere in the cluster that distinguishes them. `Localhost` is per-node state Kubernetes does not manage for you; `RuntimeDefault` names no file and has none of this problem. AppArmor is taught as mechanism and diagnostic only — the one Pod the lesson applies **fails**, with `Cannot enforce AppArmor: AppArmor is not enabled on the host`, and `aa-status` and `apparmor_parser` appear nowhere because no profile can be loaded on Docker Desktop. Half of a two-tool bullet is unrunnable on the documented platform; the Linux escape hatch is the only fix. see below | `-` |

### seccomp

Kubelet's seccomp root is **`/var/lib/kubelet/seccomp/`**, and `localhostProfile` is relative to it.
Know the JSON shape — `defaultAction: SCMP_ACT_ERRNO|SCMP_ACT_LOG|SCMP_ACT_ALLOW`, `architectures`,
`syscalls[].names` — and the kubelet-config route `seccompDefault: true` (GA since 1.27).
kubernetes.io has an excellent tutorial and it *is* allowed.

### AppArmor — use the field, not the annotation

There are **no AppArmor docs in the exam.** Fallback is `man 5 apparmor.d`. On v1.35:  <!-- man-ok: the CKS exam machine has man pages; the netlab image does not -->

```yaml
securityContext:
  appArmorProfile:
    type: Localhost          # or RuntimeDefault | Unconfined
    localhostProfile: k8s-apparmor-example-deny-write
```

Settable at Pod or container level. The old
`container.apparmor.security.beta.kubernetes.io/<name>` annotation has been deprecated since 1.30
and still functions in 1.35 — but **never put both the annotation and the field on one Pod**, which
is a validation failure. You must also be able to load a profile (`apparmor_parser -q <path>`, `-r`
to replace), check `aa-status`, and read a profile to find the rule that's blocking.

---

## What the exam does *not* test, despite what guides claim

Spending time here is the most common way to waste CKS preparation:

| Item | Why to skip or demote |
|---|---|
| **Writing Rego / OPA Gatekeeper** | Not curriculum-named, no whitelisted docs, no first-hand report of *authoring* either Gatekeeper or Kyverno. Be able to **apply a provided** ConstraintTemplate or ClusterPolicy and verify a non-compliant Pod is rejected — nothing more. Kyverno has **not** "replaced" Gatekeeper; neither is a first-class exam tool now. Spend the time on PSA and **ValidatingAdmissionPolicy** (GA in 1.30, built-in, documented on an allowed domain) instead. |
| **PodSecurityPolicy** | Removed from Kubernetes in 1.25, and its removal was the reason for the Oct 2024 refresh. Zero value. |
| **Vault / ESO / Sealed Secrets** | No evidence of any kind. |
| **syft** | No mention, no docs, no reports. `bom` is the whitelisted tool. |
| **Kubernetes Dashboard hardening** | The competency was **deleted** in Oct 2024. killer.sh still has a scenario for it. |
| **Dockerfile hardening as its own topic** | Dockerfile analysis is no longer named; the bullet became "static analysis of user workloads and container images". |
| **Sysdig** | An artefact of pre-2024 tool lists. Falco is the runtime tool. |
| **`docker` CLI hardening** | Sources conflict, and k8s 1.35 runs **containerd**. `/etc/docker/daemon.json` and socket perms are cheap to memorise, but expect **`crictl`/`nerdctl`** for container inspection. |

## What's pre-installed

**Officially guaranteed on the SSH hosts** (and *not* on `base`): `kubectl` with the `k` alias and
bash completion, `yq`, `curl`, `wget`, man pages. You are also explicitly permitted to install
distro packages.

**Consistently present but not officially published:** `kube-bench`, `trivy` (frequently **only on
the control plane** — read the task's host carefully), `falco` as a systemd unit,
`apparmor_parser`/`aa-status`, `crictl`, `etcdctl`, `openssl`, `jq`, `strace`, and pre-configured
containerd handlers such as `runsc`. **Assume the tool a task needs is already on the host that task
names.**

For the no-docs tools, the task's own **Quick Reference box** is the intended escape hatch — the
allowed-resources page says it "may include links to other resources that might be needed to solve a
task." Don't count on it; don't panic if one appears.
