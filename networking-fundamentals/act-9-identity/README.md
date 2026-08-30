# Act IX — Identity and access

Act VIII ended one line short of useful. You can prove who is at the other end of a connection, exhaustively, with mathematics you performed by hand — and then the proof stops, holding a name, with no opinion whatsoever about what that name may do. `O=kubeadm:cluster-admins` was a superuser because somebody wrote a rule, and cryptography neither wrote nor validated that rule.

This act is the rules. It is a shorter act than the last, and a stranger one, because almost nothing in it is mathematics. The hard parts are all *design* — decisions about where a fact is stored, who is entitled to assert it, and how wrong it is allowed to be.

## The idea that holds the act together

Act VIII was organised around four separate promises. This act is organised around **one trade-off that you cannot escape**, and every lesson is a different attempt to escape it.

> **You can know an answer instantly, or you can know that it is still true. Not both.**

That is it. Every mechanism here — sessions, tokens, JWTs, OIDC, and the permission models at the end — is a position on that single line, and the position determines the failure mode:

```
   AT ONE END: ASK EVERY TIME
     the answer is CURRENT. you learn the instant
     something is revoked, disabled, or deleted.
     cost: a lookup on every single request, against
     something that must always be up, and must be
     reachable from everywhere.
        -> sessions, introspection, "is this still
           valid?" calls

   AT THE OTHER END: CARRY THE ANSWER WITH YOU
     the answer is INSTANT. verify a signature and
     you are done -- no lookup, no shared database,
     nothing to be down.
     cost: it is a PHOTOGRAPH. it was true when it
     was taken. you cannot un-issue it.
        -> JWTs, and every "stateless" design

   AND THIS IS NOT THE FIRST TIME YOU HAVE SEEN IT
     an earlier act ended on this exact line, about
     an object that has nothing to do with identity,
     and reached an answer the whole industry now
     uses. it is deliberately not named here.
```

Somewhere in this act you should catch yourself thinking *"wait — I have had this argument before, about something else entirely."* When you do, go back and find it: naming it yourself is worth considerably more than being told, and the two technologies look nothing alike from the outside. That recognition is the act working, and it is not scheduled — it may arrive in lesson 02 or not until lesson 06.

## The three decisions that keep getting conflated

The other thing to carry through the act. Every access-control system makes three separable decisions, and the classic production failure is a system that makes one of them while everybody believes it made another:

| | The question | Answered by | The failure when it is confused |
|---|---|---|---|
| **Authentication** | who is making this request? | a credential, and something that unpacks it | diagnosed as the row below, and "fixed" by widening permissions |
| **Authorization** | may *that* party do *this*? | rules, consulted against a name | diagnosed as the row above, and "fixed" by re-issuing the credential, repeatedly |
| **Delegation** | may this *third party* act for me, and how much of me? | a token with a scope | handing over the password, because it is easier |

Lesson 01 separates the first two hard enough that you will never confuse them again. Lesson 05 is the third one, which is the whole reason OAuth2 exists and is almost always explained as a protocol diagram rather than as the problem it solves.

## The lab

**You need the `netlab` kind cluster from Act V**, running. Nothing here creates or destroys a cluster, and nothing here needs a second one.

```bash
kind get clusters                     # expect: netlab
export KUBECONFIG="${TMPDIR:-/tmp}/act9.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
kubectl get nodes
```

Two notes on that, and the first is not optional.

- **Every lesson uses an exported, throwaway kubeconfig**, as above, rather than your default one. This is not ceremony: several experiments deliberately authenticate as somebody else, and one of them makes a mess of a context on purpose. Keep it in `$TMPDIR` where it cannot matter.
- **`curl` does the work, not `kubectl`.** That is deliberate and it is the point of lesson 01: `kubectl` chooses a credential for you and will silently prefer the one in your kubeconfig to the one you passed on the command line, which quietly destroys any experiment about credentials. Where a lesson cares which credential was used, it constructs the request itself.

Beyond that: `python3` for unpacking tokens, and the `cryptography` package from Act VIII lesson 03 for the one lesson that checks a signature by hand. Lesson 05 adds a real identity provider in a container, and says so at the point it does.

## The lessons — read in this order

1. **[Who are you, and what may you do](01-authn-vs-authz.md)** — three requests, three different answers, and the one with no credential at all does not do what you expect.
2. **[Not sending the password every time](02-tokens-and-sessions.md)** — why the first thing any login does is stop using the thing you logged in with, and the choice that decides everything afterwards.
3. **[Taking the credential apart](03-jwt.md)** — nine hundred characters you have been treating as opaque, in two commands. Then try to promote yourself.
4. **[Trusting a token you did not issue](04-verifying-a-token.md)** — check the signature on that credential by hand, against a key the cluster publishes to everyone it already trusts, and find the attacks that have nothing to do with breaking the mathematics.
5. **[Delegation without handing over a password](05-oauth2-and-oidc.md)** — the problem OAuth2 actually solves, built by hand before you meet a real provider.
6. **[Two ways to write down a permission](06-rbac-and-abac.md)** — the two models, kept deliberately vendor-neutral, so that Kubernetes RBAC and AWS IAM are both recognition rather than new material.

Then: **[test yourself](test-yourself.md)** · **[diagnose it](diagnose.md)** · **[in the wild](in-the-wild.md)**.

When you want to look something up rather than learn it, that is what [the instrument panel](../../reference/README.md) is for — [the map](../../reference/03-the-map.md) ties every tool to the piece of kernel state it reads, and [the grammar](../../reference/01-the-grammar.md) is the page that lets you work out a command nobody showed you.

## What breaks here

Three shapes, and the third is the one that ends careers.

**A stale answer that looks like a current one.** Nothing in a token knows what happened after it was signed. A user disabled ten minutes ago holds a credential that verifies perfectly, and every check passes, and the check is not wrong — it is answering a question about the past. Act VIII's expired-certificate outage was this shape with the sign reversed.

**A claim nobody checked.** Exactly how much of a signed credential a stranger can read is lesson 03's opening question, and you should answer it from Act VIII before you look. But whichever way it goes, the failure is the same: somebody writes code that pulls a field out of one and acts on the field, having verified nothing, because the field was right there and looked official.

**Permission that accumulated.** Authorization systems only ever seem to be edited in one direction. Every model in lesson 06 makes granting easy and auditing hard, and the question "who can currently delete this?" is genuinely difficult to answer in every one of them. That is not a flaw in a particular product; it is a property of the shape.

> **The question to carry forward:** Act VIII asked which of four promises a mechanism keeps. This act asks a different one, and it is the question to bring to any authorization system, cloud IAM included: **when this says yes, what moment in time is it telling me about — and what would have to happen for it to start saying no?**

---

↑ **[The course](../README.md)** · Prev: **[Act VIII — Trust on an untrusted wire](../act-8-trust/README.md)** · Next: **[Who are you, and what may you do](01-authn-vs-authz.md)** →
