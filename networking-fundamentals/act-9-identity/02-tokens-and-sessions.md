# Not sending the password every time

Lesson 01 got a credential the easy way: it asked the cluster for one, over a connection that was already authenticated. That is how machines do it, and it dodges the interesting question, because a machine's credential arrives from a trusted parent. A person's does not.

A person has a password. And a password is the one credential with a peculiar property: **it is the only thing you have that cannot be replaced if it leaks**, because it is not a random string in a file — it is in their head, and it is the same one they used somewhere else.

So the first thing every login system in the world does, immediately after checking a password, is **stop using it**. It hands you something else and asks you to present that instead, forever. This lesson is about what that something else is, because the choice made at that moment determines almost everything about how the system fails later.

> **Predict first —** you are designing that hand-off. The obvious approach is to generate a random string, write it in a database next to the user's id, and give the string to the browser: on every request you look it up. Now scale it — a hundred servers in five regions, a thousand requests a second. Name the problem you hit, then name the fix that anyone would reach for, and then — this is the actual question — **name what that fix silently takes away.** You have already met the thing it takes away, in a completely different context, one act ago.

### Why not just send the password every time

Take the question seriously for a moment rather than dismissing it, because the reasons are not all the obvious one.

The server has to *check* the password, which means comparing it against something stored — and what is stored, as Act VIII's in-the-wild page established, is a deliberately **slow** hash. That is the point of it: argon2id and bcrypt are tuned to take real time so that guessing is expensive. Which means checking a password is expensive **for you too**, every single request, on purpose. A credential you present a thousand times cannot be one that costs 100 ms to verify.

Then the smaller reasons, which are the ones that actually cause incidents. Every place the password travels is a place it can be logged — and things which log request headers are legion. Every process that touches it is in scope for your password-handling review. And a password is not *scoped*: it is all-or-nothing, so anything holding it holds everything, forever, including the ability to change the password itself.

**So the hand-off is not an optimisation. A password proves who you are once; anything else is the wrong tool for it.** What you want in exchange is a credential that is cheap to check, narrow in what it permits, boring if logged, and disposable.

### The two ways, and the only real difference

There are exactly two, and everything else is a variation.

**Ask every time.** Generate a random opaque string, store it server-side against the user, hand over the string. It carries no information — it is a *handle*. To find out what it means you look it up.

**Carry the answer.** Put the facts *in* the credential — user, expiry, maybe some groups — and sign them. Nothing is stored. To find out what it means you check the signature and read it.

Everything people say about these is downstream of one difference, and it is worth being precise, because the usual framing ("stateful versus stateless") names the mechanism rather than the consequence:

> **A handle is a question. A signed claim is an answer.**

A question gets asked at the moment it matters, so it is always current. An answer was computed at some point in the past and does not know what happened since.

That is the act's whole thesis, and here it is again: **you can know instantly, or you can know that it is still true.** Look up a handle and you learn the truth as of *now*, at the cost of a lookup that must succeed. Verify a signature and you learn the truth as of *issuance*, at no cost and with nothing to be down.

### Watch the gap, and time it

This is not a theoretical trade-off, and you do not have to take it on faith, because Kubernetes sits at a deliberate midpoint and you can *measure* where.

A ServiceAccount token is a signed claim — lesson 03 takes one apart — so it should be un-revokable. But the API server does something extra: it also checks that the account named inside still exists. That check is a lookup, and lookups are expensive on every request, so it goes through a cache. Find the cache.

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act9.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
API=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl config view --minify --raw \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' \
  | base64 -d > "${TMPDIR:-/tmp}/ca.crt"
CA="${TMPDIR:-/tmp}/ca.crt"
URL="$API/api/v1/namespaces/default/pods"

kubectl create sa victim
TOK=$(kubectl create token victim --duration=1h)
echo "before deletion: $(curl -s -o /dev/null -w '%{http_code}' \
  --cacert "$CA" -H "Authorization: Bearer $TOK" "$URL")"
```

```
serviceaccount/victim created
before deletion: 403
```

`403`, which by lesson 01 means the credential authenticated fine and the account simply has no permissions. Now revoke it in the most total way available — **delete the account entirely** — and watch the credential:

```bash
kubectl delete sa victim
n=0; start=$SECONDS
while [ $((SECONDS - start)) -lt 30 ]; do
  c=$(curl -s -o /dev/null -w '%{http_code}' \
        --cacert "$CA" -H "Authorization: Bearer $TOK" "$URL")
  n=$((n+1))
  [ "$c" = "401" ] && { echo "request $n at t+$((SECONDS-start))s -> 401"; break; }
done
echo "it authenticated $((n-1)) requests after its account ceased to exist."
```

```
serviceaccount "victim" deleted from default namespace
request 618 at t+10s -> 401
it authenticated 617 requests after its account ceased to exist.
```

**Six hundred and seventeen authenticated requests by an account that does not exist.** Run it again and the count will differ — it depends how fast your laptop can loop — but the *ten seconds* will not. That is the API server's ServiceAccount cache, and it is not a bug, it is the trade priced and paid: paying for a fresh lookup on every request was judged not worth it, and the bill is a ten-second window in which a deleted identity keeps working.

The `before deletion` request above was load-bearing, by the way, and not just as a sanity check. **A cache is filled by use**, so that one request is what put `victim` in it; delete an account that nobody has touched and the first lookup goes to the store and fails immediately. Which is worth sitting with, because it means the window is widest for exactly the accounts that are busy — and an account you are urgently revoking is, by definition, one that is busy.

Sit with the shape rather than the number. **Every check in that window returned a correct answer to the question it was actually asking**, which was not "does this account exist?" but "did this account exist when I last looked?" Nothing malfunctioned. The answer was stale, and stale answers are indistinguishable from current ones at the point of use — which is the entire difficulty.

> **Check yourself —** ten seconds is short. Suppose you disliked it and set the cache to zero, so every request re-reads the account. You have now bought perfectly current revocation. What did you pay, and — the part people miss — what *new* failure did you just introduce that did not exist before?

<details>
<summary>Answer</summary>

You paid a read on the critical path of every authenticated request in the cluster, which is a very large number of reads, all of them against the same store.

But the new failure is the interesting one, and it is a change in *kind* rather than degree. **You have made authentication depend on the availability of the thing it reads.** With a cache, a brief blip in the datastore is invisible: requests keep authenticating from cached state. Without one, that blip becomes a cluster-wide authentication outage — everything fails at once, including whatever tooling you would use to fix it.

So the cache is not only a performance choice. It is a **fault-isolation** choice, and it points at the awkward general rule: *a system that always tells you the current truth cannot tell you anything when it is unwell.* Freshness and availability are trading against each other, and there is no setting at which you have both.

Which is why real systems put the dial somewhere in the middle and are explicit about the window — ten seconds here, five minutes for a typical OIDC token, ninety days for a certificate. **The window is the design. The only mistake is not knowing what yours is.**

</details>

### The thing you have met before

Now name it. A signed claim cannot be withdrawn, because the signature is already made and verification consults nothing but the signature. To take one back you need a *second* lookup — some list of things to reject — and that lookup is expensive, has to be reachable from everywhere, and if it fails you must choose between refusing everyone and letting everyone through.

**That is Act VIII lesson 05, word for word, about certificates.** CRLs too big to distribute; OCSP adding a round trip and a privacy leak, and treated as success when it fails. The industry's conclusion there was not to fix revocation but to route around it: **make lifetimes short enough that revocation barely matters.**

Tokens reached the identical conclusion by the identical argument. It is why the token you just made defaults to a lifetime measured in hours rather than years, why `--duration=1h` was a natural thing to write, and why every serious token system has a *pair* — a short-lived one you present constantly, and a long-lived one whose only purpose is asking for a fresh short one. The presentation is cheap and stateless; the renewal is rare, so it can afford to be a real lookup that checks whether you are still allowed to exist.

**Two mechanisms, two decades apart, in unrelated parts of the stack, forced to the same answer by the same argument.** When a structural constraint is real you do not get to design around it — you only get to choose where to put the window.

<!-- figure -->
```
   WHY NOT SEND THE PASSWORD EVERY TIME
     it must be checked against a DELIBERATELY SLOW
       hash (argon2id/bcrypt). expensive BY DESIGN --
       and expensive for YOU, on every request.
     it gets logged wherever headers get logged.
     it is not SCOPED: all-or-nothing, and it can
       change itself.
     -> a password proves identity ONCE. anything
        more is the wrong tool.

   THE TWO KINDS, AND THE ONE DIFFERENCE
     HANDLE   opaque random string, meaning stored
              server-side.   A HANDLE IS A QUESTION.
              -> asked when it matters: ALWAYS CURRENT
              -> costs a lookup that must SUCCEED
     CLAIM    the facts, signed, inside the credential
              A SIGNED CLAIM IS AN ANSWER.
              -> verify + read: INSTANT, nothing to be
                 down, no shared store
              -> it is a PHOTOGRAPH of the past

   MEASURED, NOT ASSERTED
     delete a ServiceAccount, keep using its token:
       617 authenticated requests, then 401 at t+10s
     10s = the API server's SA cache. deterministic.
     every check in that window was CORRECT -- it
     answered "did this exist when I last looked?"
     STALE ANSWERS LOOK EXACTLY LIKE CURRENT ONES
     AT THE POINT OF USE.

   SET THE CACHE TO ZERO AND SEE WHAT YOU BUY
     + perfectly current revocation
     - a read on every request, one store
     - AND A NEW FAILURE MODE: authentication now
       depends on that store being UP. a blip becomes
       a cluster-wide auth outage, including the
       tooling you would fix it with.
     freshness vs availability. no setting has both.

   THE SAME WALL AS ACT VIII
     a signature cannot be un-made, so revocation
     needs a SECOND lookup: big, everywhere, and
     fails open or fails closed.
     certificates gave up and went SHORT-LIVED.
     tokens gave up and went SHORT-LIVED, in pairs:
       short one you present constantly (stateless)
       long one that only ASKS for a new short one
         (rare, so it can afford a real check)
     TWO MECHANISMS, TWO DECADES APART, SAME ANSWER.
     you do not design around a real constraint --
     you only choose WHERE TO PUT THE WINDOW.
```

**Cleanup:**

```bash
kubectl delete sa victim --ignore-not-found
```

> **You understand this when you can** state the difference between a handle and a signed claim in
> terms of questions and answers rather than "stateful and stateless"; describe the experiment
> that measures the gap, and say why every check inside the window was nonetheless correct;
> explain what setting a credential cache to zero buys, what it costs, and the new failure it
> creates; and explain why short-lived credentials plus renewal is the answer the certificate
> world also reached.

**Which raises:** you have been handed a signed claim and told it contains facts. That should be uncomfortable, because a credential you can *read* is a credential whose contents you might be tempted to *believe* — and it is sitting in a shell variable right now, nine hundred characters of something. **So what is actually in it, who can read it, and what happens if you edit it?**

---

↑ **[Act IX overview](README.md)** · Prev: **[Who are you, and what may you do](01-authn-vs-authz.md)** · Next: **[Taking the credential apart](03-jwt.md)** →
