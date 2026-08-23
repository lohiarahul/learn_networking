# Act X — Securing the cluster

Nine acts built a thing that works. A process got a socket, two machines got a wire, the wire crossed the internet, one machine pretended to be many, a cluster scheduled and routed and stored, a control plane reconciled it, cryptography made the wire trustworthy, and identity made the requests attributable.

At no point did anyone ask whether any of it was **safe**, and the honest reason is that safety was never once the default. Every mechanism you built arrived with its behaviour already chosen — by an image maintainer, by a container runtime, by whoever wrote the kubelet's flags, by the Kubernetes project's idea of what should not break on upgrade. You accepted all of it, because accepting it was how you got a cluster that started.

Act IX ended there deliberately. **Defaults are chosen to make a cluster start, not to make it safe**, and the distance between those two aims is not a gap in your knowledge — it is the working space of an entire profession, and it is where clusters are actually broken into.

## The idea that holds the act together

Every control in this act is a place where something is refused. What differs between them — and it is the only thing that really differs — is **when** the refusal happens.

A rule can be applied when an image is built, when an object is written, when a container is created, when a syscall is made, or never at all, in which case something merely writes down what happened. Those are not five implementations of one idea. They are five genuinely different bargains, because each moment knows a different amount:

```
   BUILD        ADMIT         CREATE        RUN          AFTER
   the image    the object    the container the syscall  the record
   |            |             |             |            |
   knows: the   knows: the    knows: this   knows: the   knows:
   contents,    whole cluster node, this    actual call, EVERYTHING
   and nothing  and nothing   image, this   the actual   -- and it
   about where  about what    kernel        argument     has already
   it will run  it will do                               happened
   |            |             |             |            |
   cheapest, fewest places to put it -------> most context, least leverage
```

The trade runs in one direction and never turns around: **the earlier you decide, the less you know** — and the earlier you decide, the cheaper the decision is, the fewer places you have to put it, and the more uniformly it applies. Act IX left you a question that is exactly this trade in one instance: it showed that a Role provably cannot hold a predicate, that the cluster is plainly evaluating some anyway, and asked where they went and *why later is better*. You will answer that here, and then find that "later" was only one of five answers, and that real systems use all five at once because no single one of them is sufficient.

So the question to carry through this act, and to put to any control you meet in the wild:

> **At what moment does this refuse, what did it know at that moment, and what gets past it because of what it could not know?**

## What this act does not assume

Everything here leans on acts you have already built, and it is worth knowing which, because the leaning is heavy:

- **Act IV** for namespaces, cgroups and capabilities as kernel mechanisms — this act is largely about turning those from things you performed into things a cluster enforces.
- **Act VI** for the API server as a store, the reconciliation loop, and editing a static Pod manifest on a control-plane node. You will do that last one several times.
- **Act VII** for Secrets, and specifically for the three places it proved one password ends up, none of them encrypted. One of those three is fixable and this act fixes it.
- **Act VIII** for signatures, certificates and mTLS — the mathematics that makes "this artifact is the one we built" and "this Pod is talking to the Pod it thinks it is" mean anything.
- **Act IX** for authentication, tokens, JWTs and RBAC. The ServiceAccount token you took apart by hand is about to become an object with a lifetime and a blast radius.

## The lab

The same two-node `kind` cluster, plus one honest limitation and two additions.

The limitation: **AppArmor cannot be enforced on macOS or Windows**, because Docker runs a Linux VM whose kernel has no Linux Security Modules compiled in. Lesson 02 measures this rather than skipping it — the failure message is the same one a real cluster gives when a profile has not been loaded, so the diagnostic is learnable even where the enforcement is not. On a Linux host with Ubuntu or SUSE underneath, it works.

The additions are opt-in and flagged where they arrive. Lesson 08 wants a **local registry** you control — because the whole subject is what happens when somebody changes what a name points at, and you cannot do that to Docker Hub — plus three single-binary tools that all run as containers, so nothing is installed. Lesson 09 builds a **second cluster** with Cilium replacing the default CNI. Lessons 05, 10 and 11 install a policy engine, a runtime detector and a secret operator respectively, and every one of them is uninstalled again at the end of its lesson.

One habit is worth adopting from lesson 09 onwards, and it is why every command block in this act begins the same way: **the act keeps its kubeconfig in a scratch file** (`export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"`), and lesson 09 creates its second cluster with `kind create cluster --kubeconfig …` rather than letting `kind` write to `~/.kube/config`. Act V told you to switch clusters with `kubectl config use-context`, which works and edits your real kubeconfig — the one with your employer's clusters in it. A throwaway cluster should leave no trace when you delete it.

One tool carries over as a hard requirement. Lesson 04 issues a serving certificate for a webhook, which needs the **Homebrew OpenSSL** that Act VIII already asked for — Apple's `/usr/bin/openssl` is LibreSSL and rejects the `-ext` flag. Lesson 04's final section also needs a server at **Kubernetes 1.36 or newer** for `MutatingAdmissionPolicy`; it says so, and it gates on it.

Several lessons edit the API server's static Pod manifest. That is a real control plane being restarted, it takes about forty seconds each time, and every one of those lessons ends by putting it back. If you break it, Act VI lesson 08 is the recovery.

## The lessons — read in this order

1. **[What a container is allowed to do](01-what-a-container-may-do.md)** — the flag you have typed since the orientation page, and the far more interesting question of what a container has without it.
2. **[When the kernel says no](02-the-kernel-says-no.md)** — fourteen capabilities against three hundred syscalls, and what stands in front of the rest.
3. **[A default that refuses](03-a-default-that-refuses.md)** — making the previous two lessons mandatory instead of optional, and finding out where that policy actually lives.
4. **[Deciding before it exists](04-deciding-before-it-exists.md)** — a rule nobody built in.
5. **[Policy as a product](05-policy-as-a-product.md)** — the two engines everybody actually runs, and writing rules in both.
6. **[A Secret that is actually secret](06-a-secret-that-is-actually-secret.md)** — the one of Act VII's three locations that cluster configuration can close.
7. **[The doors the cluster leaves open](07-the-doors-left-open.md)** — the API server's own flags, the kubelet's own port, and the token every Pod is handed whether or not it wants one.
8. **[What you shipped](08-what-you-shipped.md)** — the decision made earliest, knowing least, about an artifact that will be running for two years.
9. **[Encryption between Pods](09-encryption-between-pods.md)** — Act VIII's handshake, applied to traffic that never leaves the cluster.
10. **[Seeing it happen](10-seeing-it-happen.md)** — the two controls that refuse nothing, and why a system needs them anyway.
11. **[Secrets from outside the cluster](11-secrets-from-outside.md)** — how organisations actually do this, and why none of it is on an exam.

Then **[test yourself](test-yourself.md)**, the eleven **[on-call drills](diagnose.md)** — where every component is healthy, every command succeeds, and the control is not doing what somebody believes it is doing — and **[in the wild](in-the-wild.md)**.

## What breaks here

More than in any previous act, and on purpose. Every lesson in this act has a failure mode where **the control appears to be working and is not**: a capability granted that is never checked, a policy label on an exempted namespace, a seccomp profile present on four nodes out of five, an admission webhook whose `failurePolicy` quietly lets everything through when it is down, a Secret encrypted in etcd and readable on a node, a signature verified against a key anybody can push to.

That is the characteristic bug of this whole subject and it is worth saying plainly before you start: **security controls fail silently by default, because a control that is doing nothing looks exactly like a control that has nothing to do.** Every lesson here ends with a way to tell those apart, and that — not the YAML — is the thing worth taking away.

---

↑ **[Course overview](../README.md)** · Prev: **[Act IX — Identity and access](../act-9-identity/README.md)** · Next: **[What a container is allowed to do](01-what-a-container-may-do.md)** →
