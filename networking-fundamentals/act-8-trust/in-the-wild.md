# Act VIII in the wild — you will never implement any of this

Every previous in-the-wild page had the same job: tell you which experiments survive contact with a managed cluster. This one is different, because the gap is not between your lab and production — it is between *understanding a mechanism* and *the job you will actually be given*.

**You will not implement a single thing from this act.** Not a hash, not an HMAC, not a mode of operation, not a key exchange, and — this is the one people get wrong — not a certificate verification either. Everything here already exists, correctly, in a library that has been attacked by strangers for twenty years, and the correct response to needing any of it is to call that library.

So the honest question is why the act exists, and the answer is in the shape of every one of its lessons. Not one of them ended with "and now you can build it." They ended with **which promise this keeps, which it does not, and what that costs you.** That is the transferable part, because in production you will be choosing between mechanisms, reading a verdict, or explaining to somebody why their scheme does not work — and all three are judgement, not implementation.

## The thought lesson 01 told you to hold

Lesson 01 raised something and then deliberately walked away from it: `hunter2` is destroyed, not concealed, and **`hunter2` will still be guessed** — "a different problem with a different fix, and it is the one place in this lesson where a plain hash is the wrong tool; hold the thought." Nothing in lessons 02 through 06 came back for it, because nothing in them was about it. Here is the fix.

The problem is speed. SHA-256 is designed to be fast — it has to be, since it hashes multi-gigabyte files — and fast is exactly wrong for passwords. An attacker with your database and commodity hardware tries **billions of SHA-256 guesses per second**, and human passwords come from a space small enough that this wins.

So password storage uses a deliberately *slow* function with a tunable cost, plus a per-user random **salt** so that identical passwords do not produce identical hashes and one precomputed table cannot attack every user at once. The current names are **argon2id**, **scrypt** and **bcrypt**, and the choice between them is mostly about which your language already has.

None of this contradicts lesson 01 — irreversibility still comes from the sizes, exactly as argued. It adds the second requirement lesson 01 pointed at and postponed: *irreversible* is necessary and not sufficient, because **an attacker who can afford to guess never needs to reverse anything.** The strength of the function was never the binding constraint; the size of the input space was.

**The rule: if the input has low entropy, a general-purpose hash is the wrong primitive.** Passwords, PINs, and short recovery codes are all in this class. File contents, API bodies and public keys are not.

## Where each mechanism actually shows up

| Mechanism | Where you have already met it, without knowing |
|---|---|
| SHA-256 | Every container image digest. `sha256:abc…` is why an image tag is a name and a digest is an identity. |
| Collision resistance | Git. A commit id is a hash of its content *and its parents*, which is what makes history tamper-evident — and is why Git's move off SHA-1 was slow and painful. |
| HMAC | Webhook signatures. GitHub, Stripe and every payment provider sign their callbacks this way, and lesson 02 is why the header is `X-Hub-Signature-256` and not a bare hash. |
| HMAC | JWT, when signed with `HS256`. Which means lesson 02's shared-secret problem — every holder can forge every other holder's messages — is *the* JWT question. |
| AES-GCM | Every TLS connection you have made since Act III, and etcd encryption at rest, which is what turns a Kubernetes Secret from base64 into ciphertext. |
| Ephemeral key exchange | The `Negotiated group` line in every handshake. You never configure it and it protects a year of recorded traffic. |
| Signatures | Package managers, image signing, and every certificate in the world. |
| Certificates | Your kubeconfig, the API server, every kubelet, and the Ingress Secret you read in Act V. |

Two of those deserve more than a row.

**A container image digest is lesson 01 being load-bearing.** When you pin `nginx@sha256:…` rather than `nginx:1.25`, you are relying on second-preimage resistance to guarantee that the bytes you get are the bytes you tested. Every supply-chain guarantee anyone sells you is built on that one property — which is why the fact that MD5 lost only *collision* resistance and not second-preimage resistance is a distinction with money attached.

**A Secret is base64, and now you know exactly what that means.** Act V made the point and Act VII made you read one out of a node's memory. This act gives you the vocabulary for why it is not a criticism of Kubernetes: base64 is an *encoding*, and encodings keep none of the four promises. There is no key, so there is nothing to not-have — it is not weak encryption, it is not encryption. What puts a cipher in that path is a cluster-level `EncryptionConfiguration`, and when you meet it you will find it is lesson 03's AEAD with a key read from a file.

## The one operational fact that causes most of the incidents

Certificates expire, and lesson 05 showed which side notices: **the verifier checks the clock, and the server serves an expired certificate happily forever.**

That asymmetry is the whole reason certificate outages are what they are. Nothing degrades. There is no warning, no elevated error rate the day before, no gradual anything. At one instant everything works, and at the next instant every client refuses — and the server's own logs and metrics look perfectly healthy, because from its side nothing changed.

The industry's answer, as lesson 05 described, was to give up on revocation and make lifetimes short instead. Which sounds like it would make the problem worse and makes it dramatically better, for a reason worth stating: **a certificate that must be renewed every 60 days has automated renewal, because nothing manual survives that cadence.** A three-year certificate is renewed by a human who has left the company. The short lifetime is not the safety feature; the automation it forces is.

Concretely, on any cluster:

```bash
kubectl get secrets -A -o json | jq -r '
  .items[] | select(.type=="kubernetes.io/tls")
  | "\(.metadata.namespace)/\(.metadata.name)"'
```

For each one, the question is not "when does it expire" but **"what renews it, and how would I know if that stopped?"** If the answer is `cert-manager`, look at whether its `Certificate` objects have a healthy `Ready` condition — and recall Act VII's finding that an object with an empty status means nobody looked. A `Certificate` whose controller was uninstalled is a perfectly valid object that will silently stop being renewed.

And the cluster's own PKI, which Act VI walked you through:

```bash
docker exec netlab-control-plane kubeadm certs check-expiration
```

That command makes sense now in a way it could not in Act VI. Every line is a certificate signed by `/etc/kubernetes/pki/ca.crt`, every `CN` is an identity, and the `residual time` column is the only warning you will ever get.

## Two things that exist because trust anchors cannot be trusted

Lesson 05 ended on the uncomfortable fact: any of ~195 CAs can issue a valid certificate for any name, and the system's security is the minimum over all of them. Two mechanisms exist purely to contain that, and both are worth recognising.

**Certificate Transparency.** Every publicly-trusted certificate must be published to append-only, publicly-auditable logs, and browsers reject certificates that are not. This does not prevent a CA from mis-issuing — nothing can — but it makes mis-issuance *discoverable*, because the owner of a domain can watch the logs for certificates they did not request. The logs are Merkle trees, which is lesson 01's hash chain doing the same job Git does. Several CAs have been distrusted as a direct result.

**Pinning, and why it mostly died.** The idea was to declare "for this host, only accept *this* key," bypassing the CA system. It works, and it bricks your service the moment you rotate a key you forgot was pinned — which happened enough that HTTP Public Key Pinning was removed from browsers entirely. What survives is pinning inside systems where one team controls both ends: mobile apps talking to their own backend, and service meshes. **The generalisation: pinning is safe exactly when the same people control rotation and verification**, which is almost never true on the open web and almost always true inside a cluster.

## What you will actually be asked to do

Four tasks, in rough order of frequency, and every one of them is a lesson from this act:

1. **Debug a chain.** Something says `unable to get local issuer certificate`. Drill 1 — count the certificates, read the issuer, work out whether it is a missing intermediate or an untrusted anchor. Two causes, one error code, unrelated fixes.
2. **Add a name to a certificate.** Someone reaches a service by a new hostname or an IP and gets a hostname mismatch. Drill 3 — the fix is at issuance, in `subjectAltName`, and it is never in the trust store.
3. **Set up mTLS between two services.** Both ends need a certificate from a CA the other trusts, and the failure will be reported on the side that is not broken. Drill 4 — read the other end's log.
4. **Explain why somebody's scheme is wrong.** Almost always because it uses a mechanism that keeps one promise to make a different one. Lesson 02's colleague, in a new costume.

For the fourth, the question that resolves it is the one this act was organised around, and it is worth carrying out of here as a sentence you can say in a meeting: **which of the four promises is this making, and which one is everybody assuming it makes?**

## The habits worth keeping

**Read the whole verdict, not the code.** `error 25 at 2 depth` named a certificate nobody had asked about. A chain error is reported against the certificate that broke the rule, so "my certificate is invalid" is very often a statement about somebody else's.

**Ask which side is in a position to notice.** The verifier checks the clock; the server does not. The client reports success on a failed client certificate; the server does not. This one question resolved five of the six drills, and it generalises past cryptography.

**Never write a construction.** Not `hash(secret + data)`, not encrypt-then-MAC by hand, not a nonce counter. Lesson 03 listed four ways to get encrypt-then-MAC wrong, in a scheme whose idea is one sentence, and there are more than four. Use an AEAD. The one place this act asks you to build something — lesson 02's forgery, lesson 03's hand-rolled AEAD — was to show you why not to.

**When something says "encrypted," ask where it stops.** Act V terminated TLS at an Ingress and spoke plain HTTP onward. Act VII had you read a Secret's plaintext out of a node's memory. Both were correctly described as encrypted. "Is it TLS?" is not a question; "where does the TLS stop, and what is on the other side of that point?" is.

---

↑ **[Act VIII overview](README.md)** · Prev: **[Diagnose it](diagnose.md)**
