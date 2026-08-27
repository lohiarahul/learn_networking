# Act X in the wild — the controls are the easy part

Act VIII's in-the-wild page said you would never implement any of it. Act IX's said you would implement all of it, badly, several times. This one is different again: **you will inherit most of it, already switched on, already believed in, and nobody will be able to tell you what it covers.**

That is the actual working condition of this subject. The YAML in this act takes an afternoon. The thing that takes years is answering "is this doing anything" about a control somebody else installed for a reason nobody wrote down.

## The five moments, as job descriptions

The act's spine was a timeline: `BUILD`, `ADMIT`, `CREATE`, `RUN`, `AFTER`. In any organisation large enough to have opinions, that timeline is an org chart.

- **`BUILD`** belongs to whoever owns CI. In practice this means image policy is decided by the platform team's pipeline templates, and the security property you get is whatever survived the last time somebody needed a build to go out at 5pm on a Friday.
- **`ADMIT`** is a product with a team behind it — the Kyverno or Gatekeeper install, the policy library, the exception process. This is the only moment in the act that reliably gets funded, because it is the one that generates a denial somebody can screenshot for an auditor.
- **`CREATE`** and **`RUN`** are node configuration: seccomp profiles on disk, a runtime's default capability set, whether `--seccomp-default` is on. Nobody owns these. They are set by whatever provisioned the node pool, they differ between pools, and lesson 02's finding that a missing profile is a per-node property with no admission check and no status field is exactly why.
- **`AFTER`** belongs to a detection team who are not in your standup, whose retention you do not know, and whose tuning you will discover during an incident.

The failure mode this produces is specific and worth expecting: **the moments are owned by different people, so nothing owns the gap between them.** Lesson 08's answer — a claim made at build, checked at admit — requires two teams to agree on a key. That is why image signing is common and image signing *with a pinned identity* is rare.

## Policy as a product, and the exemption ledger

Lesson 05 installed two engines and lesson 03 configured exemptions. In production those two facts collide, and the collision is the whole job.

Every policy engine in a real cluster accumulates exemptions, because the alternative is blocking the ingress controller, the CNI, the CSI driver, the monitoring agent, and the runtime detector — and lesson 10 measured that last one running `privileged: true` with the Docker socket mounted, which your own `baseline` would refuse. **Observability and security tooling are privileged by construction**, so the exemption list is not a sign of a badly run cluster. It is a load-bearing part of a well-run one.

What separates the two is whether the list is a **ledger or a residue**. A ledger has one entry per exemption, each naming a ServiceAccount, a namespace, a reason and a person. A residue is a namespace where somebody removed the `enforce` label at 2am so a DaemonSet would start, and the label never came back, and lesson 03 proved you cannot detect that by reading labels.

The useful audit is therefore always the *complement*, and it is the same query in every one of these systems: take the set of things actually running, and subtract the set the policy's selectors match. What is left is your real posture. Nobody ships this as a feature, which is why writing it once by hand is a genuinely good use of a day.

## Supply chain: what SLSA is actually for

Lesson 08b signed a digest and had a cluster verify it. Production adds one idea, and it is worth naming because the acronym is everywhere and the idea is simple.

A signature says *the holder of this key asserts something about these bytes*. It does not say what the assertion is. **Provenance** — the SLSA framework's contribution — is a structured attestation of *how the artifact was built*: which source commit, which builder, which parameters. Signed provenance lets a verifier ask a much better question than "is it signed": it can ask "was this built by our CI, from our repository, on a protected branch, without a human step".

Which turns the admission rule from "signed by us" into a predicate over build facts, and closes the attack lesson 08b could not: a developer with push access to the registry and a copy of the signing key cannot forge provenance naming a commit that does not exist.

Two things to know about it in practice. It moves the trust root to your CI system's identity, which is why the keyless flow matters — the certificate's subject is the workflow, not a person. And the infamous mistake is verifying the *issuer* without pinning the *subject*: trust GitHub's Fulcio without checking `sub`, and every repository on GitHub can produce artifacts your cluster accepts. That is Act IX's audience attack with a nine-figure blast radius, and it has happened.

## The class of bug this act is really about

Every lesson here ended with a control that appears to work and does not, and it is worth collecting them because the *shape* is transferable far beyond Kubernetes:

| The control | Why it looks fine |
|---|---|
| `add: ["CAP_NET_BIND_SERVICE"]` | accepted silently, wrong spelling, grants nothing |
| a seccomp profile on four nodes of five | posture depends on scheduling; no status field |
| `enforce: baseline` on an exempted namespace | the label is the thing everyone reads |
| `enforce` on a Deployment | degrades to `warn`; CI goes green, rollout hangs |
| `failurePolicy: Ignore` on a down webhook | admits forbidden objects, no error, no annotation |
| `identity` first in the provider list | a valid AES key in the file, never used to write |
| a signature verified without naming a key | any valid signature passes |
| WireGuard between co-scheduled Pods | `cilium-dbg` says `Wireguard`; the wire says `password=` |
| audit at `Metadata` for writes | proves a change happened, never what it was |
| a `secretObjects` sync on the CSI driver | re-creates every location it removed |

Ten mechanisms, one bug: **a control that is doing nothing looks exactly like a control that has nothing to do.** There is no error state for "correctly configured and irrelevant".

Which is why the only question that reliably finds these is the negative one — *what would be different if this were switched off?* — and why the answer must be something you can observe. A control whose absence is unobservable has already failed; you just have not been told yet.

## What managed Kubernetes changes

Most readers will meet this on EKS, GKE or AKS, and three things move.

**You lose the static Pod edits.** Lessons 03, 06 and 10 all edited `kube-apiserver.yaml`. On a managed control plane you cannot, so audit policy, encryption providers and admission configuration become provider-specific settings — a checkbox for audit logs going to the provider's log service, a KMS key reference, and in several cases *no* support for `--admission-control-config-file` at all. The mechanism is identical and the lever is somebody's console.

**You gain KMS almost for free**, which is the one lesson 06 could not demonstrate. Envelope encryption with a key the API server never holds is a one-line setting on all three, and it is the single highest-value item in this act that a managed cluster makes easy.

**You inherit an audit pipeline you did not design.** The provider ships events to its own logging product with its own retention and its own price per gigabyte — and lesson 10's measurement of 887 events per minute on an *idle* two-node cluster is why the first thing anyone does is filter, and the second is stop looking at it.

## Deliberately not covered

Six things, so you know the shape of the hole.

**Stronger isolation.** Lesson 02 named `RuntimeClass` and gVisor and did not use them. Everything in this act shares one kernel with the workload, which is why a kernel bug is a cluster compromise. **gVisor** (a user-space kernel) and **Kata** (a real VM per Pod) remove that assumption at a real cost in performance and compatibility, and they are the answer when the threat model includes hostile tenants rather than compromised ones.

**Multi-tenancy properly.** Namespaces are not a security boundary against a determined tenant, and this act shows several reasons why. The real answers — virtual control planes, cluster-per-tenant, hierarchical namespaces — are architecture rather than configuration.

**Detection engineering.** Lesson 10 got an alert out of Falco. Turning alerts into something a human acts on — tuning, suppression, enrichment at capture time, alert-to-case workflow — is a discipline, and the failure mode is a channel nobody reads, which is worse than no channel.

**Incident response.** Nothing here covered what you do after: isolating a node without losing evidence, snapshotting a compromised container's filesystem, deciding whether to kill the Pod (and destroy the evidence) or leave it running (and leave the attacker there). Those are decisions made under time pressure with incomplete information, and they are the actual job.

**Compliance as an artifact.** CIS benchmarks at fleet scale, control mapping, evidence collection, and the gap between "the control is on" and "we can prove it was on last March". Lesson 07 met kube-bench and its two unfixable findings; the industrial version of that problem is a full-time role.

**Signing your own admission chain.** Nothing verified the policy engine's own image, or the CA bundle in the webhook configuration, or who may edit a `ValidatingWebhookConfiguration`. Every control in this act is an object in the API, and objects have permissions — which is lesson 09's `CiliumNode` finding generalised, and the reason `can-i update validatingwebhookconfigurations` is one of the highest-value queries you can run against a cluster.

> **The question to carry out of this act.** Act VIII asked which of four promises a mechanism keeps. Act IX asked what moment an answer is about. This one asks three things of any control you meet, and they must be answered in this order: **at what moment does it refuse, what did it know at that moment — and if it stopped working tonight, what would be different tomorrow morning?** If the third answer is "nothing", the first two do not matter yet.

---

↑ **[Act X overview](README.md)** · Prev: **[Diagnose it](diagnose.md)**
