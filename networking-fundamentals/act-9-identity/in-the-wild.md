# Act IX in the wild — the same trade, everywhere you look

Act VIII's in-the-wild page said you would never implement any of it. This act is the opposite: **you will implement almost all of it, badly, several times.** Not the cryptography — the *decisions*. Where a fact lives, who may assert it, how stale it may be, and which of two shapes the rules take. Nobody hands you those; they accumulate out of small choices made by people in a hurry, and then they are the architecture.

So this page is about recognising the act's ideas when they turn up wearing production clothes, and about the parts deliberately left out.

## The trade is not about tokens

Lesson 02 framed it as handles versus signed claims. That was a convenient place to meet it, not where it lives. Once you can see the shape you will find it in systems that have nothing to do with identity:

- **DNS TTLs.** A record you cached is a signed claim: instant, and possibly a photograph. Set the TTL to zero for freshness and you have bought a lookup on every request against something that must always be up. Act II's `ndots` fan-out was this bill arriving.
- **Cloud IAM propagation.** AWS says plainly that policy changes are *eventually consistent*. You revoked a permission and it is still being enforced somewhere, for a while, and no API tells you when it stops. That is drill 3's ten seconds with a longer window and worse visibility.
- **Certificate revocation.** Act VIII's wall. Same argument, same non-solution, same real solution.
- **Service discovery, feature flags, config caches, CDN invalidation.** All the same line, and the useful question at every one of them is the act's question: **when this says yes, what moment is it telling me about?**

**This is the actual transferable content of Act IX.** The Kubernetes specifics will change. The observation that you cannot have both an instant answer and a current one will not, because it is not a fact about software.

## The mechanism you have already built, in production

The strangest thing in the act, if you noticed it, is that a Kubernetes cluster publishes an OIDC discovery document and a JWKS at all. Lesson 04 had you fetch both and verify a token by hand — but the cluster verifies its *own* tokens with the private key, and needs none of that machinery to do it. So who is the public half for?

**Somebody else.** That is the entire point, and it is how workload identity works on every cloud:

- **EKS IRSA** and **GKE Workload Identity** configure the cloud's own identity service to trust *your cluster's* JWKS as an OIDC provider. Your Pod gets a projected ServiceAccount token with `aud` set to the cloud's STS, hands it over, and receives cloud credentials in exchange. No static keys anywhere.
- **GitHub Actions** does the same in reverse: the runner mints a token whose claims describe the repository and branch, and your cloud account is configured to trust GitHub's JWKS and to check those claims. The infamous mistake is trusting the issuer without pinning `sub` — which grants every repository on GitHub the ability to assume your role. That is lesson 04's audience attack, with a nine-figure blast radius.

Read those again with the act in hand and there is nothing new in them: a discovery document, a `kid`, a signature, an `aud` check, and short lifetimes because revocation is hard. **You built every part.** What production added was the idea that the issuer and the verifier can belong to different companies, which is exactly what lesson 05 said delegation was for.

## Identity as a certificate: meshes and SPIFFE

The other production shape puts Act VIII and Act IX directly on top of each other. **SPIFFE** gives every workload a short-lived X.509 certificate whose subject is a structured identity (`spiffe://cluster/ns/default/sa/probe`), and every connection is mutual TLS. Istio, Linkerd and Consul all do a version of this.

Which is worth seeing clearly, because it is a genuinely different arrangement of the same parts: **authentication becomes Act VIII entirely** — a certificate, a chain, a verified name — and Act IX's `AuthorizationPolicy` objects then hold rules about those names. The credential lives for minutes, so revocation is handled the way both fields ended up handling it. And a service mesh sidecar is the party doing the verification, which means the *application* receives an already-authenticated identity in a header and must never trust that header from anywhere else. Half the mesh misconfigurations in the world are that last sentence.

## The three failure shapes, as they actually arrive

The README named three. Here is what they look like on a Friday.

**A stale answer that looks current.** "We removed her access on Tuesday." The token she holds verifies perfectly, and every check passes, and every check is right — they are answering a question about the past. The remediation nobody likes: shorten lifetimes until the window is smaller than your incident response time, and stop treating credential deletion as containment.

**A claim nobody checked.** There is a long history of libraries and services accepting `alg: none`, accepting a token signed by any key in the file, or reading the payload without verifying at all — diagnose drill 5 is not a hypothetical, it is a recurring class. What makes it durable is that **the broken version is the simpler code and passes every honest test.** The only defence that scales is a rule rather than vigilance: nothing reads a claim except through a function that verified first.

**Permission that accumulated.** Somebody binds a role to a broad group to unblock a deploy — drill 6's `system:authenticated`, or a wildcard in an IAM policy, or an over-wide GitHub OIDC trust. It is one line in a review. It never appears in any audit of the account that ends up using it. And nobody deletes it, ever, because nobody can prove what would break. **The only tool that finds these is the reverse question**, and in the descriptive model the reverse question does not have an answer, which is why cloud IAM audit is a product category rather than a command.

## Deliberately not covered

Five things this act left out, so you know the shape of the hole.

**Proof of possession.** Every credential here was a *bearer* token: whoever holds it may use it. The alternative is a credential bound to a key the client must prove it has — mutual TLS, **DPoP**, WebAuthn — so that a stolen copy is useless. This is the single biggest lever on token theft and the act never touched it.

**Phishing, which lesson 05 admits it cannot fix.** The authorization code flow keeps your password from the tool and does nothing about a login page that merely *looks* like the issuer's. The protocol's job was the tool, and it did it. Closing the human half needs a credential that cannot be replayed at the wrong origin — which is WebAuthn, and which is the real reason passkeys exist.

**Lifecycle.** Nothing here covered how identities are created and destroyed at scale: SCIM provisioning, joiner-mover-leaver, and the fact that the hardest part of access control at any real company is not the model but knowing which accounts should still exist.

**Sessions as browser objects.** Cookie attributes (`Secure`, `HttpOnly`, `SameSite`), session fixation, CSRF, and why `state` in lesson 05 was doing security work rather than bookkeeping. All real, all a different subject.

**The third permission model.** Lesson 06 said there were two families, which is true at the level of representation — but **ReBAC** (Google's Zanzibar, and OpenFGA or SpiceDB in the open) deserves naming, and it fits the lesson rather than breaking it. It is the descriptive model with a deliberate restriction: the only attributes allowed are *relationships*, so a policy is a graph and the reverse question becomes graph reachability — computable again. Read it as somebody paying a large expressiveness cost specifically to buy back the property lesson 06 showed ABAC losing. That is what a good engineering trade looks like written down.

> **The question to carry out of this act.** Act VIII asked which of four promises a mechanism keeps. This one asks something you can put to any authorization system, cloud IAM included, and it is two halves that must both be answered: **when this says yes, what moment in time is it telling me about — and if I wanted to know who else it would say yes to, could I find out at all?**

---

↑ **[Act IX overview](README.md)** · Prev: **[Diagnose it](diagnose.md)**
