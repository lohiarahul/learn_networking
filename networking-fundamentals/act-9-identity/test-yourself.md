# Test yourself — Act IX

Twenty-two questions. Same rule as every act: answer out loud or on paper *before* opening the answer. This act is the one where that gap bites hardest, because everything in it is a word you have used in meetings for years — and using a word is not the same as being able to say what it costs.

Questions 1–4 are lesson 01, 5–7 are lesson 02, 8–10 are lesson 03, 11–13 are lesson 04, 14–18 are lesson 05, 19–22 are lesson 06.

---

**1.** State the two questions every access-control system answers, in order, and say what each one takes in and hands out.

<details><summary>Answer</summary>

**Authentication** takes a credential and produces a **name and a set of groups**. **Authorization** takes that name, a verb and an object, consults rules, and produces one bit.

The order matters and is not negotiable: there is nothing for rules to be about until a name exists. And the hand-off between them is narrow on purpose — authorization receives a username and groups, never a credential — which is why one authorization system can serve certificates, bearer tokens and anonymous requests without knowing the difference.

</details>

**2.** You get a `403` whose message names your account. A colleague suggests re-issuing the credential. Why is that guaranteed not to help, and what is the general form of the diagnostic?

<details><summary>Answer</summary>

Because the message contains a username, which means authentication already succeeded — the server unpacked the credential, decided who you were, then consulted rules and refused. A new credential produces the same name and therefore the same refusal.

The general diagnostic: **is your username in the error?** If yes, authentication worked and it is a rules problem, so granting permissions is the only fix. If no, authentication failed and authorization never ran, so granting permissions cannot possibly help. Both mistakes are common because "it says I am not allowed" reads like one condition.

</details>

**3.** A request arrives with no `Authorization` header at all. Predict the status code, and then justify the design.

<details><summary>Answer</summary>

`403`, naming `system:anonymous`. **Sending no credential is a successful authentication**, as a specific named identity in the group `system:unauthenticated` — an *answer* to the authentication question, not a refusal to answer it.

The design argument: something must be able to reach `/healthz` without a credential. If "no credential" short-circuited to a refusal, allowing that would require a special case *outside* the permission system, and special cases outside the permission system are where breaches live. Making "nobody" a name means what nobody may do is written in ordinary rules, in the same place as everything else. **It is better for "nobody" to be a name than a hole**, and the smell of a bad authorization system is a code path that skips the check rather than making the check say no.

</details>

**4.** `kubectl auth can-i list pods --as=system:serviceaccount:default:probe` answers truthfully without you holding that account's credential. Why is that possible, and what does it tell you about where the boundary between the two halves sits?

<details><summary>Answer</summary>

Because "may X do Y?" is a function of the rules and X's *name*, not of X's credential. Authentication maps a credential to a name; authorization maps a name to a verdict; so the second half can be evaluated for any name you care to type.

It also tells you the boundary is *complete* — no residue of the credential leaks past it. If authorization could consult anything about how you authenticated, `--as` could not be truthful.

</details>

**5.** Give three distinct reasons a password is the wrong credential to present on every request. One of them must be about the cost of checking it.

<details><summary>Answer</summary>

1. **It is expensive to verify, deliberately.** It is checked against a slow hash (argon2id, bcrypt) tuned to take real time so guessing is costly — which makes it cost real time *for you*, on every request. A credential presented a thousand times cannot cost 100 ms to check.
2. **It travels through everything that logs headers**, and everything that touches it comes into scope for review.
3. **It is not scoped and it can change itself** — all-or-nothing, forever, including the ability to lock you out.

A password proves identity *once*. Anything beyond that is the wrong tool.

</details>

**6.** Distinguish a handle from a signed claim without using the words "stateful" and "stateless". Then say what each one costs.

<details><summary>Answer</summary>

**A handle is a question. A signed claim is an answer.**

A handle carries no information; to learn what it means you look it up, and the lookup happens at the moment it matters, so what you learn is current. It costs a lookup that must succeed, against something that must be up and reachable from everywhere.

A signed claim carries the facts; to learn what it means you verify a signature and read. It costs nothing and depends on nothing being available — but it is a photograph of the moment it was taken and knows nothing of what happened since.

The usual framing names the mechanism. This one names the consequence, which is the part that decides your failure mode.

</details>

**7.** You delete a ServiceAccount and its existing token keeps authenticating for about ten seconds. Explain why every check in that window was nonetheless correct, and say what setting the cache to zero would buy and cost.

<details><summary>Answer</summary>

Because the check was never "does this account exist?" — it was "**did this account exist when I last looked?**", and to that question the answer was truthfully yes. Nothing malfunctioned. The answer was stale, and stale answers are indistinguishable from current ones at the point of use.

Zeroing the cache buys perfectly current revocation. It costs a read on the critical path of every authenticated request — and, the part people miss, it introduces a **new kind of failure**: authentication now depends on the availability of the store it reads. A brief blip becomes a cluster-wide authentication outage, including the tooling you would use to fix it. Freshness and availability trade against each other and no setting gives you both. The window is the design; the only mistake is not knowing what yours is.

</details>

**8.** A JWT's three parts are separated by dots and none of them is encrypted. Why is a document anyone can read still worth signing, and what is the single most common way code gets this wrong?

<details><summary>Answer</summary>

Because the signature is not about secrecy, it is about **integrity and origin**: the claim cannot be altered by anyone who cannot sign, and it can be traced to whoever could. Reading it was never supposed to be hard.

The wrong turn is treating readable as trustworthy: code that base64-decodes the payload, pulls out a field, and acts on it. The field was right there and looked official, and *no check occurred*. **Reading and verifying are separate operations**, and only one of them tells you anything — which is Act VIII's `error 7` in a new format, where a certificate parsed perfectly and chained to nothing.

</details>

**9.** You edit the payload of a ServiceAccount token to name a different account and present it. Predict the status code and explain it.

<details><summary>Answer</summary>

`401`, not `403`. The signature no longer matches the altered payload, so the token is not recognised as a credential at all — authentication fails and no name is ever produced. It does not become a request from a different user with insufficient rights; it becomes a request from nobody the server can identify.

That distinction is the whole reason a signed claim is safe to hand out in readable form.

</details>

**10.** Name the five standard registered claims and, for each, the attack it defeats.

<details><summary>Answer</summary>

- `iss` — the issuer. Defeats a token from an issuer you never intended to trust but whose signature happens to verify against a key you loaded.
- `sub` — the subject. The identity itself; without it there is nothing to authorize.
- `aud` — the audience. Defeats a *completely genuine* token, correctly signed, presented to the wrong service.
- `exp` — expiry. Defeats a token that was legitimate and is not any more, and is the only thing standing in for revocation.
- `iat` — issued at. Lets a verifier apply its own maximum age policy rather than accepting whatever lifetime the issuer chose.

</details>

**11.** Describe how a verifier gets from a token in its hand to the key that signed it, and name the field that makes it possible.

<details><summary>Answer</summary>

The token's `iss` names the issuer; a well-known path under that issuer returns a discovery document; the document's `jwks_uri` points at a key set; the token header's **`kid`** selects which key in the set. Then the key is reconstructed from its parameters — for RSA, the modulus `n` and exponent `e` — and used to check the signature over the base64 text of the header and payload.

`kid` is the field that makes rotation possible: an issuer can publish the new key beside the old one, start signing with the new one, and retire the old one once nothing bearing it is still valid. Without `kid`, key rotation would be an outage.

</details>

**12.** Explain the `alg: none` attack, and state the fix as a rule about who decides what.

<details><summary>Answer</summary>

The token's own header declares the algorithm. A naive verifier reads that field and does what it says — so an attacker sets `alg` to `none`, strips the signature, and the verifier obediently performs no verification and accepts the payload.

The fix is not a blocklist. It is a rule about authority: **the verifier picks the algorithm; the token may only say which *key*.** Anything the attacker controls must not be able to select the strength of the check applied to it. The general form outlives JWT — never let untrusted input choose the validation path.

</details>

**13.** Why is a signature computed over the base64 text rather than over the decoded JSON?

<details><summary>Answer</summary>

Because JSON has no canonical serialisation. Key order, whitespace, unicode escaping and number formatting can all vary while the parsed object stays identical — so re-serialising before verifying would produce different bytes from the ones that were signed, and the check would fail for honest tokens or, worse, could be made to succeed for dishonest ones.

Signing the exact transmitted characters removes the question. The rule generalises: **sign the bytes you received, never a reconstruction of them.**

</details>

**14.** Give four reasons handing your password to a third-party tool is wrong, and then name the requirement those reasons force.

<details><summary>Answer</summary>

It is **not scoped** (everything you can do, including things that do not exist yet); it **cannot be withdrawn** except by changing it, which punishes you and every other tool; it **destroys attribution**, so no log can separate the tool's actions from yours; and it **authorises changing itself**, so handing it over hands over the ability to lock you out. A fifth, from lesson 02: only the party that *checks* passwords can store one, so the tool has nowhere safe to put it.

Together they force: the credential the tool uses must be **issued by whoever checks passwords, at your request, naming the tool, and narrower than you** — which in turn forces you into direct contact with the issuer, because that is the only way it can act at your request.

</details>

**15.** Derive the four hops of the authorization code flow and name the specific leak each one prevents.

<details><summary>Answer</summary>

1. **The tool redirects you to the issuer.** Prevents your password reaching the tool — the login form is served on the issuer's origin.
2. **The issuer redirects you back to a pre-registered address.** Prevents an attacker nominating their own delivery address at the moment of the request; registration is the only thing binding "who is asking" to "where the answer may go".
3. **What comes back is a single-use handle, not a token.** Whatever travels this hop is in a URL, and URLs land in browser history, server logs and `Referer` headers. So it must be useless to anyone who finds it.
4. **The tool exchanges the handle on a back channel**, proving it is itself. Only here does a credential come into existence, on a connection your browser never touches.

</details>

**16.** Of the three tokens an authorization server returns, one is protected by a symmetric MAC rather than a signature. Say which, and derive it from a property rather than remembering it.

<details><summary>Answer</summary>

The **refresh token**. A MAC can only be checked by a holder of the same secret; a signature can be checked by anyone. So the question is who needs to verify — and a refresh token is only ever presented back to the issuer that made it. There are no third parties, so asymmetry buys nothing.

Its `aud` says so explicitly: the audience is the issuer's own URL. The audience field and the algorithm choice agree, and either one predicts the other.

</details>

**17.** Why is sending an id_token to an API a vulnerability rather than a shortcut?

<details><summary>Answer</summary>

Because the two tokens have different audiences and different jobs. The id_token's `aud` is the **client** — it is a statement *to the tool* about who the user is. The access token's `aud` is the **API** — it is a permission to act, which the tool merely carries. So the tool is not the audience of the token it uses, and an API accepting an id_token is accepting a document that says on its face it was written for somebody else.

Skipping that check discards the only thing preventing a genuine, correctly-signed token being replayed at a service it was never meant for.

</details>

**18.** You revoke a refresh token. Introspection then reports the matching access token as inactive, while verifying that same token locally still succeeds and its expiry is minutes away. Which answer is wrong?

<details><summary>Answer</summary>

Neither. They are answers to different questions.

Local verification answers **"was this issued by whom it claims, unaltered, and is it still inside its stated window?"** — and it is. Introspection answers **"does the issuer still stand behind it?"** — and it does not. Both statements are true simultaneously, about the same bytes, at the same instant.

There is no third option that removes the gap: introspect on every request and you have bought a lookup on the critical path with the availability failure lesson 02 measured; verify locally and you accept a window. The discovery document publishes both endpoints because both are legitimate, and choosing per call site — local for an internal service, an ask for a payment — is the actual engineering.

</details>

**19.** What is a role *for*? Answer in terms of arithmetic.

<details><summary>Answer</summary>

To turn a multiplication into an addition. Ten subjects and twenty permissions is up to two hundred facts to maintain; inserting a named intermediate makes it twenty facts (what the role permits) plus ten (who holds it). Roles are a factoring trick, and most of RBAC's other properties — its coarseness, its auditability — follow from the fact that the intermediate has to be reusable, which means it cannot mention any particular subject or object.

</details>

**20.** Kubernetes RBAC has no way to write a denial. Name the property that buys, and what it lets you do that you otherwise could not.

<details><summary>Answer</summary>

The authorization function is **monotone**: adding a binding can only add permissions, removing one can only remove them. So a one-line change can be reviewed *locally* — by reading the line — without holding the rest of the cluster's rules in your head.

Contrast AWS IAM, where an explicit deny wins — and where a deny can live in more than one place (on the identity, on the resource, or imposed from above the account), all evaluated together for one request. That buys precision, since you can carve exceptions out of broad grants, and gives up monotonicity: adding a statement can revoke, removing one can grant, and no single policy can be understood by reading it alone. **Find the combining rule first**, because it tells you what kind of reasoning the system will support.

</details>

**21.** Neither "an owner may delete their own pod" nor "only during an incident" can be written as a Kubernetes Role. They are impossible for two *different* reasons. Give both, and say why treating them as one reason is a mistake.

<details><summary>Answer</summary>

**"Their own" is a relation.** A role is a property of the **subject**, fixed when somebody wrote the binding; ownership is a fact about a subject and an object together. The rule would have to *compare* a field of the requester against a field of the thing requested, and RBAC rules only ever list names — `resourceNames` takes a list, never a comparison.

**"During an incident" is context that is never passed in.** The whole input to the decision is (subject, verb, resource, namespace). The hour, the incident state and the source address are not attributes RBAC evaluates badly — they are not arguments to the function at all, so no extension of the rule *syntax* could reach them.

Why the distinction matters: the first gap could in principle be closed by a richer rule language, and systems exist that close it (that is what ReBAC does). The second cannot be closed by language at all — it needs the decision point to be *given* more information. Collapsing them into "RBAC isn't expressive enough" hides the fact that one is a syntax problem and the other is an interface problem.

Either way, the practical consequence is the same and it is how the enumerating model rots: people widen a role until it covers the case.

</details>

**22.** Both models answer "may X do Y?" instantly. Explain what happens to "who can do Y?" in each, and why cloud IAM ships a simulator rather than a report.

<details><summary>Answer</summary>

In the enumerating model the reverse question has an answer **of the same kind** as the forward one: walk the rules, resolve the bindings, get a finite list of names. Tedious — a hundred and sixty objects on a two-node cluster — but complete, modulo authorizers outside the rule store.

In the describing model there is no such answer. The honest reply is a **predicate**: "alice, unless it is out of hours and she is not in the office; and bob, only during an incident." Producing even that required enumerating the whole state space, and the moment one attribute has an unbounded domain — a source IP, a free-text label — the space stops being finite and the question stops having a computable answer without a solver.

Hence the simulator: one concrete request, one answer, which is the only question that stays cheap. It is not a missing feature, it is the shape of the model. Which is also why "who can read this bucket?" is a genuinely hard question at every organisation — and why no real system picks one model outright. A cluster that authorizes with RBAC is nonetheless evaluating predicates over objects somewhere in its request path; finding out where, and why that stage is a better place for them than the Roles, is the next act's business.

</details>

---

↑ **[Act IX overview](README.md)** · Prev: **[Two ways to write down a permission](06-rbac-and-abac.md)** · Next: **[Diagnose it](diagnose.md)** →
