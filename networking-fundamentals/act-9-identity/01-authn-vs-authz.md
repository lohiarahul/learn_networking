# Who are you, and what may you do

Act VIII ended by handing you a name and nothing else. You can prove, with mathematics you have performed by hand, that the party at the other end of a connection is the one named in a certificate — and you can read that name out of `depth=0`. `CN=rahul`, `O=kubeadm:cluster-admins`.

**And then what?** A name is not a permission. Nothing in five lessons of cryptography had any opinion about what `rahul` may do, and the group in that certificate meant something only because somebody, somewhere, wrote a rule saying it did.

So this act is about the rules. It opens with a distinction that sounds like vocabulary and is actually the most useful diagnostic tool in the subject, because almost every access-control incident is one of these two things being mistaken for the other.

> **Predict first —** you are going to send three requests to a Kubernetes API server. The first carries a valid credential belonging to an account with no permissions. The second carries a credential that is simply gibberish. The third carries **no credential at all** — no header, nothing. For each one, write down the HTTP status code you expect, and write down whether you expect the error message to contain a *username*. The third one is the interesting one, and most people get it wrong.

### Three requests

Set up a way to talk to the API server without `kubectl` choosing a credential for you. That last part matters — your kubeconfig holds a client certificate, and `kubectl` will use it in preference to anything you pass on the command line, which would quietly defeat the whole experiment.

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act9.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
API=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl config view --minify --raw \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' \
  | base64 -d > "${TMPDIR:-/tmp}/ca.crt"
echo "$API"
```

```
https://127.0.0.1:62183
```

That `ca.crt` is Act VIII lesson 05 in a file: the one trust anchor you are choosing to believe for these requests, and `--cacert` is the `-CAfile` argument under a different name.

Now make an identity that is real and powerless, and get a credential for it:

```bash
kubectl create serviceaccount probe
TOK=$(kubectl create token probe --duration=1h)
echo "${#TOK} characters"
```

```
serviceaccount/probe created
925 characters
```

(Your count will differ by a few — the credential contains the account's unique id, and yours is not mine. That it is *nine hundred characters of something* rather than a short opaque handle is the interesting part, and lesson 03 is where you find out why.)

**Request one — a real credential, belonging to an account nobody has granted anything:**

```bash
curl -s --cacert "${TMPDIR:-/tmp}/ca.crt" \
  -H "Authorization: Bearer $TOK" \
  "$API/api/v1/namespaces/default/pods"
```

```
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {},
  "status": "Failure",
  "message": "pods is forbidden: User \"system:serviceaccount:default:probe\" cannot list resource \"pods\" in API group \"\" in the namespace \"default\"",
  "reason": "Forbidden",
  "details": {
    "kind": "pods"
  },
  "code": 403
}
```

**Request two — gibberish:**

```bash
curl -s --cacert "${TMPDIR:-/tmp}/ca.crt" \
  -H "Authorization: Bearer not-a-real-token" \
  "$API/api/v1/namespaces/default/pods"
```

```
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {},
  "status": "Failure",
  "message": "Unauthorized",
  "reason": "Unauthorized",
  "code": 401
}
```

**Request three — nothing at all:**

```bash
curl -s --cacert "${TMPDIR:-/tmp}/ca.crt" \
  "$API/api/v1/namespaces/default/pods"
```

```
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {},
  "status": "Failure",
  "message": "pods is forbidden: User \"system:anonymous\" cannot list resource \"pods\" in API group \"\" in the namespace \"default\"",
  "reason": "Forbidden",
  "details": {
    "kind": "pods"
  },
  "code": 403
}
```

### The two questions, and which one each answer is about

Look at what separates request two from the other two, because it is not "how wrong the credential was."

**Request two got `401` and a message with no name in it.** The server is saying *I do not know who you are.* It never reached the question of permissions, because there was nobody to have permissions. `Unauthorized` is a badly-chosen word for it — the honest phrasing is **unauthenticated**, and the HTTP specification has apologised for this for thirty years.

**Requests one and three got `403`, and both messages contain a username.** The server is saying *I know exactly who you are, and no.* Two entirely separate things happened in order: it worked out an identity, and then it consulted rules about that identity and refused.

So there are two questions, always, and they are answered by different machinery:

| | Question | Kubernetes name | Failure | Name in the message? |
|---|---|---|---|---|
| **Authentication** | who is making this request? | authn | `401` | no — there is no name yet |
| **Authorization** | may *that* party do *this*? | authz | `403` | yes — and it names the exact verb and resource |

**Which gives you a diagnostic you will use constantly: the presence of a username in the error tells you authentication succeeded.** A `403` naming your account is never a credentials problem, and no amount of re-issuing tokens will fix it. A `401` is never a permissions problem, and no amount of granting permissions will fix it. People burn hours on this by treating "it says I'm not allowed" as one condition.

### Request three is the one worth sitting with

Now the prediction. Almost everyone says request three returns `401` — no credential, so authentication fails. It returned `403`, and it named a user: `system:anonymous`.

Read that carefully, because it inverts something. **Sending no credentials was not an authentication failure. It was a successful authentication, as a specific, named identity that has almost no permissions.** The API server has an anonymous authenticator, and its job is to say "this request is from `system:anonymous`, in the group `system:unauthenticated`" — which is an *answer* to the authentication question, not a refusal to answer it.

Which is a design decision, not an accident, and it is worth seeing why it is the right one. Something has to serve `/healthz` to a load balancer that holds no credential. If "no credential" short-circuited to a refusal, the only way to allow that would be a special case *outside* the permission system — and special cases outside the permission system are where breaches live. Instead, anonymous is an ordinary identity, and what it may do is written in ordinary rules, in the same place as everything else.

**The general principle, which outlives Kubernetes entirely: it is better for "nobody" to be a name than a hole.** You will meet the same move in every serious authorization system, and the smell of a bad one is a code path that skips the check rather than making the check say no.

> **Check yourself —** authentication produced the identity `system:serviceaccount:default:probe` for request one. You never told the server that string. Where did it come from, and what does that tell you about how many authenticators a server can have?

<details>
<summary>Answer</summary>

It came out of the token — the API server unpacked the credential, established it was genuine, and read the identity from inside it. You will do that unpacking by hand in lesson 03, and check the mathematics that makes it genuine in lesson 04.

But the useful half of the question is the second one. Count the credential types you have now seen this server accept: a **client certificate** (your kubeconfig, from Act VIII — `CN` became the username), a **bearer token** (request one), and **nothing at all** (request three, which produced a name). Three completely different mechanisms, three different formats, and all three produce the same kind of answer: a username and a set of groups.

So authentication is a *chain of authenticators*, tried in turn, and the first one that recognises a credential wins. Which explains something you saw at the start: `kubectl` preferred the client certificate in your kubeconfig over the `--token` you passed, and there is no error for that — the request was authenticated, just not as who you meant.

And it explains the shape of the whole system. Everything downstream of authentication deals in a **username and groups**, never in a credential. Whether you proved yourself with a certificate, a token, or an OIDC login, by the time any rule is consulted you are a string and a list of strings. That is why authorization can be written once and work for all of them — and it is why lesson 06's models say nothing about credentials at all.

</details>

### Asking without doing

One more thing follows from the split, and it is the reason this distinction is practical rather than academic. If authorization is a separate question with its own answer, you can ask it *without performing the action*:

```bash
kubectl auth can-i list pods
kubectl auth can-i list pods --as=system:serviceaccount:default:probe
kubectl auth whoami --as=system:serviceaccount:default:probe
```

```
yes
no
ATTRIBUTE   VALUE
Username    system:serviceaccount:default:probe
Groups      [system:serviceaccounts system:serviceaccounts:default system:authenticated]
```

**You just asked a question on behalf of an identity you do not hold, and got a truthful answer, without holding its credential.** That is only possible because "may X do Y?" is a pure function of the rules — it does not need X's token, only X's *name*. Authentication is what maps a credential to a name; authorization is what maps a name to a verdict; and the second half can be evaluated for any name you like.

Note the groups, too, because Act VIII made you build one into a certificate by hand: `system:serviceaccounts:default` and `system:authenticated`. **Group membership is not something you prove — it is attached to you by whatever authenticated you**, which is exactly what `O=kubeadm:cluster-admins` was doing in your kubeconfig.

<!-- figure -->
```
   TWO QUESTIONS, ALWAYS, IN THIS ORDER

     credential  --> [ AUTHENTICATION ] --> a NAME
                          who is this?        + GROUPS
                          fails: 401
                          no name in the error

     name+groups --> [ AUTHORIZATION ] --> yes / no
     + verb       consulted against RULES
     + resource   fails: 403
                  names the user, verb AND resource

   THE DIAGNOSTIC YOU WILL ACTUALLY USE
     is your username IN the error message?
       yes -> authn WORKED. it is a rules problem.
              re-issuing credentials cannot help.
       no  -> authn FAILED. authz never ran.
              granting permissions cannot help.

   THE SURPRISE
     NO credential at all -> 403, not 401
     because it authenticated FINE, as
       system:anonymous / system:unauthenticated
     "nobody" is a NAME, not a hole. so what it may
     do is written in ORDINARY rules, in the same
     place as everything else -- and /healthz can be
     served without a special case OUTSIDE the
     permission system. special cases outside the
     permission system are where breaches live.

   WHY THE SPLIT PAYS
     authn maps a CREDENTIAL to a name.
     authz maps a NAME to a verdict.
     so the second half needs no credential:
       auth can-i --as=<someone else>  -> truthful
     one authz system serves ALL credential types:
     certificate, token, anonymous -> all arrive as
     a username + groups and nothing else.
```

**Cleanup:**

```bash
kubectl delete serviceaccount probe
```

> **You understand this when you can** state the two questions in order and say which machinery answers each; predict `401` versus `403` for a bad credential and a valid-but-powerless one, and say which one contains a username; explain why a request with no credential at all returns `403` and what identity it runs as; argue why making "nobody" a name rather than a special case is the safer design; explain why granting permissions can never fix a `401` and re-issuing a credential can never fix a `403`; say why `auth can-i --as` can answer truthfully for an identity whose credential you do not hold; and explain why one authorization system can serve certificates, tokens and anonymous requests alike.

**Which raises:** request one worked because you had a token — nine hundred characters that the server unpacked into a name. But look at what you did to get it: you asked the cluster, over an authenticated connection, and it minted one. Which is fine for a script, and hopeless as a description of how *people* log in. A human has a password, and a password is the one credential you must never send twice, never store, and never let anywhere near a log file. **So what does a system hand you instead, the first time you prove who you are — and what does it cost to hand you anything at all?**

---

↑ **[Act IX overview](README.md)** · Next: **[Not sending the password every time](02-tokens-and-sessions.md)** →
