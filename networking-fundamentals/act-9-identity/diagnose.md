# Diagnose it — Act IX

Six drills. All of them run against the `netlab` cluster from Act V, and none of them break it — the damage in this act is never a crashed component, which is exactly what makes it hard. **Every system in these drills is working correctly.** The failures are all disagreements between what somebody meant and what they wrote down, and the only telemetry you get is a status code and a rule store.

Set up once:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act9.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
API=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl config view --minify --raw \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' \
  | base64 -d > "${TMPDIR:-/tmp}/ca.crt"
CA="${TMPDIR:-/tmp}/ca.crt"
URL="$API/api/v1/namespaces/default/pods"
```

## The clock

Every drill below carries a **target time**, and this is the one thing these drills do that the
lessons deliberately do not. The course is built to make you understand; a certification is scored on
whether you can act inside a budget, and those are different skills that look identical from the
inside. So the target is seven minutes, because that is what the exam allows: **17 tasks in 120 minutes**
is about seven minutes each, and these drills are the closest thing in the course to a task.

Three rules, taken straight from [the exam-day pacing doctrine](../../exam-prep/exam-day.md):

1. **Start the clock when the symptom appears**, not when you start the reproduce block. Building the
   broken state is setup, and on the exam somebody else has already done it.
2. **At the target, say your best hypothesis out loud** even if you are not confident. Naming a wrong
   hypothesis at 7 minutes is worth more than a right one at twenty, because the wrong one is
   falsifiable in one command and the exam pays for closed tasks.
3. **At 10 minutes, stop and open the reveal.** That is not giving up, it is the exam's own rule —
   *"the moment a task passes 10 minutes, flag it and move on"* — and the skill it builds is the
   costly one. A task that eats 25 minutes has cost you three others worth the same marks.

Run each drill untimed the first time if you like. Then run it again, weeks later, with a timer, and
notice that the second number is the one that predicts anything.

## The method for this act

Act V's five questions walked a network path. Act VI descended a dependency stack. Act VII asked which loop read which field. Act VIII had only a verdict to work from. This act has a method of its own, and it is three questions in a fixed order — the order matters because each one is meaningless until the previous is settled:

1. **Is there a name?** Look at the error, not at the code. A username in the message means authentication finished; no username means it never did, and nothing about permissions is relevant yet.
2. **Which credential actually got used?** Not which one you intended to send. Tools choose for you, and the choice is silent.
3. **What moment is this answer about?** Every yes and no in this act is a statement about some instant. Find out which one, and whether it is now.

Question 3 is the one nobody asks, and it is where the genuinely confusing incidents live.

---

## Drill 1 — three refusals, one of which is lying to you about its category

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

Three requests. Predict each status code, then run them.

```bash
kubectl create serviceaccount probe
GOOD=$(kubectl create token probe --duration=1h)
AUDT=$(kubectl create token probe --audience=vault --duration=1h)

echo -n "valid token    -> "; curl -s -o /dev/null -w '%{http_code}\n' \
  --cacert "$CA" -H "Authorization: Bearer $GOOD" "$URL"
echo -n "gibberish      -> "; curl -s -o /dev/null -w '%{http_code}\n' \
  --cacert "$CA" -H "Authorization: Bearer nonsense" "$URL"
echo -n "audience=vault -> "; curl -s -o /dev/null -w '%{http_code}\n' \
  --cacert "$CA" -H "Authorization: Bearer $AUDT" "$URL"
```

```
valid token    -> 403
gibberish      -> 401
audience=vault -> 401
```

The third one is the drill. That token was minted by this cluster, thirty seconds ago, for an account that exists, and it is cryptographically perfect. **Explain the `401`, and say what would happen if somebody responded to it by granting `probe` more permissions.**

<details>
<summary>Answer</summary>

Read the body rather than the code:

```bash
curl -s --cacert "$CA" -H "Authorization: Bearer $AUDT" "$URL"
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

**No username.** By question 1 of the method, authentication did not complete, so this is not a permissions problem and granting `probe` every verb in the cluster would change nothing.

What failed is the `aud` check from lesson 04, enforced by a real server. `--audience=vault` produced a token whose audience is `["vault"]`, and the API server declines to accept a token addressed to somebody else — correctly, because that is the entire point of the claim. Verify what you handed over:

```bash
python3 -c "
import base64, json
p = '$AUDT'.split('.')[1]
print(json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)))['aud'])"
```

```
['vault']
```

The general shape, and the reason this drill exists: **a genuine credential presented to the wrong audience fails as an authentication failure, not an authorization one** — and it will feel like a permissions problem, because you know the account is real and you can see the token in your hand. Audience-scoped tokens are the normal way to talk to anything that is not the API server, so this is a mistake you will make in production rather than in a lab.

</details>

---

## Drill 2 — a RoleBinding that is syntactically perfect and grants nothing

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

Two variants. Both created without complaint; neither works.

```bash
kubectl create role pod-reader --verb=get,list --resource=pods
kubectl create rolebinding probe-reads --role=pod-readers \
  --serviceaccount=default:probe
kubectl auth can-i list pods --as=system:serviceaccount:default:probe
```

```
role.rbac.authorization.k8s.io/pod-reader created
rolebinding.rbac.authorization.k8s.io/probe-reads created
no - RBAC: role.rbac.authorization.k8s.io "pod-readers" not found
```

And the second:

```bash
kubectl create namespace app
kubectl create serviceaccount worker -n app
kubectl create role pod-reader -n app --verb=get,list --resource=pods
kubectl create rolebinding worker-reads -n app --role=pod-reader \
  --serviceaccount=default:worker
kubectl auth can-i list pods -n app --as=system:serviceaccount:app:worker
```

```
no
```

**Find both faults. Then notice that the two `no`s are not equally informative, and work out why — because the difference is the whole drill.**

<details>
<summary>Answer</summary>

The first is a typo — `--role=pod-readers`, plural, against a role called `pod-reader` — and `can-i` volunteered it: `no - RBAC: role... "pod-readers" not found`. That string comes from the RBAC authorizer, which noticed the dangling reference while evaluating the request. Look at what got stored:

```bash
kubectl get rolebinding probe-reads -o jsonpath='{.roleRef}'; echo
```

```
{"apiGroup":"rbac.authorization.k8s.io","kind":"Role","name":"pod-readers"}
```

**`roleRef` is not a foreign key.** No such Role exists, the API server accepted the object anyway, and the binding will start working the instant somebody happens to create a Role by that name — which is a much worse property than failing.

The second fault is a namespace, and it is the same class of mistake: `--serviceaccount=default:worker` names the ServiceAccount `worker` **in `default`**, not the one you just made in `app`. The `-n app` on the command line scoped the *binding*, not the subject.

```bash
kubectl get rolebinding worker-reads -n app -o jsonpath='{.subjects}'; echo
kubectl auth can-i list pods -n app --as=system:serviceaccount:default:worker
```

```
[{"kind":"ServiceAccount","name":"worker","namespace":"default"}]
yes
```

So the binding does grant something — to an account that does not exist. Subjects are not foreign keys either.

**And here the second `no` came back bare.** No reason, no hint, nothing about namespaces. Which is correct and is the point: from RBAC's side *nothing is broken*. The binding resolves, the role exists, the rule was evaluated, and the subject simply is not the identity you asked about. There is no defect for an authorizer to report — only a difference between two strings that a human meant to be the same.

So the two failures sit either side of a line worth naming. A dangling `roleRef` is a **broken reference**, and the authorizer notices it while walking the rules. A wrong subject is a **correct rule about somebody else**, and it is indistinguishable from a deliberate one. The first is diagnosable; the second can only be found by comparing what you meant with what you wrote.

Then the question neither `no` answers. **For the cluster to have told you without being asked, a RoleBinding would need a `status`**, and it does not have one — nothing reconciles it, so there is no controller to write a complaint into. `can-i` produced the first diagnosis only because you named a subject and a verb; there is no way to ask "which of my bindings are dangling?" Compare Act V's Gateway, which *does* carry conditions and reports `Accepted: False` when no listener matches, with Act V lesson 07's NetworkPolicy, which does not. The pattern holds across the platform:

> **An object that is evaluated per request has nowhere to put a complaint.** Its only feedback is a refusal, delivered to whoever happened to make the next request — at the wrong time, to the wrong person, with no mention of the binding that failed to apply.

Which is why the reverse question from lesson 06 is not an academic exercise: enumerating who actually holds a permission is the only audit available for rules that never report on themselves.

Fix both and confirm:

```bash
kubectl delete rolebinding probe-reads
kubectl create rolebinding probe-reads --role=pod-reader --serviceaccount=default:probe
kubectl auth can-i list pods --as=system:serviceaccount:default:probe
```

```
yes
```

</details>

---

## Drill 3 — you deleted the account and the calls keep succeeding

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

A colleague reports that they revoked a compromised ServiceAccount, watched the deletion succeed, and the attacker's requests kept working for a while afterwards. You try to reproduce it and cannot — the token dies instantly. They try again on their machine and it survives ten seconds. Neither of you is doing anything wrong.

Here is the whole thing in one block. The only difference between the two halves is a single extra request:

```bash
probe_after_delete() {
  n=0; start=$SECONDS
  while [ $((SECONDS - start)) -lt 30 ]; do
    c=$(curl -s -o /dev/null -w '%{http_code}' --cacert "$CA" \
          -H "Authorization: Bearer $1" "$URL")
    n=$((n+1))
    [ "$c" = "401" ] && { echo "401 at request $n, t+$((SECONDS-start))s"; break; }
  done
}

kubectl create sa victim >/dev/null
TOK=$(kubectl create token victim --duration=1h)
kubectl delete sa victim >/dev/null
echo -n "deleted without ever being used : "; probe_after_delete "$TOK"

kubectl create sa victim >/dev/null
TOK=$(kubectl create token victim --duration=1h)
curl -s -o /dev/null --cacert "$CA" -H "Authorization: Bearer $TOK" "$URL"   # one request
kubectl delete sa victim >/dev/null
echo -n "deleted after one request       : "; probe_after_delete "$TOK"
```

```
deleted without ever being used : 401 at request 1, t+0s
deleted after one request       : 401 at request 628, t+10s
```

(Your request count will differ — it is however many round trips your machine fits into the window. The two things that will not differ are the first line's `request 1, t+0s` and the second line's roughly ten seconds.)

**Both deletions worked. Explain the difference, and then answer the question that matters: what do you tell the colleague to do the next time an account is actually compromised?**

<details>
<summary>Answer</summary>

Question 3 of the method: *what moment is this answer about?* The API server does check that the account named in a token still exists, but through a cache — so the check answers "did this account exist when I last looked?" rather than "does it exist?". Every one of those six hundred and twenty-seven authentications was a correct answer to the question actually being asked.

The difference between the two halves is that **a cache is filled by use.** In the first, nothing had ever asked about `victim`, so the first lookup went to the store and failed immediately. In the second, one request put it there, and the entry then stood for its full ten seconds. Both runs are deterministic; you can repeat them.

Which is the uncomfortable part, and it is why the reproduction gap matters rather than being a curiosity. **The staleness window is zero for idle accounts and ten seconds for busy ones** — and an account you are urgently deleting is, by definition, busy. The safe-looking case is the one you can reproduce in a quiet lab; the real case is the one you cannot.

Note also what the object store says in the same breath as the token still working:

```bash
kubectl get serviceaccount victim
```

```
Error from server (NotFound): serviceaccounts "victim" not found
```

**Two components of one system, disagreeing about the present tense, both right.** That is the signature of a cache in an authentication path, and it is the first thing to suspect whenever a revocation appears not to have taken.

What to tell the colleague: deleting the account is correct and it is not immediate, so **do not treat deletion as containment**. Ten seconds is fine for cleaning up a mistake and useless against somebody with a shell. Containment lives at a different layer — remove the permissions the token would use (an authorization change lands on the next request, because the verdict is not cached the same way), cut the network path, or evict the workload. The general rule outlives Kubernetes:

> **Revoking a credential is slower than revoking what the credential may do.** When you need a fast stop, change the answer, not the identity.

</details>

---

## Drill 4 — the powerless token that can see everything

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

Somebody is testing a locked-down ServiceAccount. They pass its token to `kubectl` and it lists every pod in the cluster. They conclude the account has far too much access and start auditing bindings.

```bash
kubectl --token="$(kubectl create token probe --duration=1h)" get pods -A | head -3
kubectl --token=totally-invalid get pods | head -2
```

```
NAMESPACE     NAME                       READY   STATUS    RESTARTS        AGE
kube-system   coredns-589f44dc88-njs8t   1/1     Running   2 (5h45m ago)   18h
kube-system   coredns-589f44dc88-qgfcm   1/1     Running   2 (5h45m ago)   18h
No resources found in default namespace.
```

The second command should end the discussion, but say precisely why — and name the command that proves it in one line.

<details>
<summary>Answer</summary>

`totally-invalid` is not a credential, and it worked. So the token was never used at all.

Question 2 of the method: *which credential actually got used?* Your kubeconfig contains a client certificate, the client-certificate authenticator sits earlier in the chain than the bearer-token one, and the first authenticator that recognises a credential wins. `kubectl` sent both and the certificate answered first. **There is no error for this**, because nothing failed — the request was authenticated, just not as who you meant.

The one-line proof:

```bash
kubectl --token=totally-invalid auth whoami
```

```
ATTRIBUTE                                           VALUE
Username                                            kubernetes-admin
Groups                                              [kubeadm:cluster-admins system:authenticated]
Extra: authentication.kubernetes.io/credential-id   [X509SHA256=d6b667f1036a0ca8d4d4d9f455c2de882e2570fca5dde306bb92c5a2b8b39cda]
```

`kubernetes-admin`, in `kubeadm:cluster-admins` — Act VIII's certificate, doing the work. And the `credential-id` extra names the **X.509 fingerprint**, which is the server telling you unambiguously which of the several credentials in flight it decided to believe.

The fix for the experiment is to construct the request yourself, which is why every credential test in this act used `curl` and `--cacert`. The fix for the habit is broader: **when an identity experiment gives an answer that seems too good, verify the identity before verifying the permission.** `kubectl auth whoami` costs one line and settles it, and the mistake is nearly universal — it is the reason the act's README tells you to use `curl`.

</details>

---

## Drill 5 — the service that reads a token and never checks it

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

A small internal service accepts ServiceAccount tokens and reads the caller's name out of them, so that it can log who did what and apply its own rules. Here it is, and it works:

```bash
cd "${TMPDIR:-/tmp}"
kubectl create token probe --duration=1h > tok.txt
kubectl get --raw /openid/v1/jwks > jwks.json
python3 - <<'EOF'
import base64, json
def b64(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
def enc(o): return base64.urlsafe_b64encode(
    json.dumps(o, separators=(",", ":")).encode()).decode().rstrip("=")

# the service. it identifies the caller from the token.
def whoami(t):
    return json.loads(b64(t.split(".")[1]))["kubernetes.io"]["serviceaccount"]["name"]

tok = open("tok.txt").read().strip()
h, p, s = tok.split(".")
print("genuine token, service says :", whoami(tok))

payload = json.loads(b64(p))
payload["kubernetes.io"]["serviceaccount"]["name"] = "root-ish"
payload["sub"] = "system:serviceaccount:kube-system:root-ish"
forged = f"{h}.{enc(payload)}.{s}"
print("forged  token, service says :", whoami(forged))
open("forged.txt", "w").write(forged)
EOF
```

```
genuine token, service says : probe
forged  token, service says : root-ish
```

Now hand the identical forged bytes to the API server:

```bash
curl -s -o /dev/null -w 'API server: http %{http_code}\n' --cacert "$CA" \
  -H "Authorization: Bearer $(cat forged.txt)" "$URL"
```

```
API server: http 401
```

**One token, two consumers, opposite outcomes. Name the exact defect in three words, then fix the service and prove the fix.**

<details>
<summary>Answer</summary>

**It never verified.** `whoami` splits on dots, base64-decodes the middle part, and reads a field — which is *parsing*, and parsing establishes nothing. Lesson 03 said reading and verifying are separate operations; this is what it costs to conflate them. Note that the forged token kept the original signature untouched, which is why it still looks entirely well-formed: it has three parts, valid base64, and plausible JSON.

The fix is to check the signature before believing a single field, using the issuer's published key:

```bash
python3 - <<'EOF'
import base64, json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
def b64(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

jwks = json.load(open("jwks.json"))

def whoami(t):                                    # verify FIRST, then read
    head = json.loads(b64(t.split(".")[0]))
    k = [k for k in jwks["keys"] if k["kid"] == head["kid"]][0]
    pub = rsa.RSAPublicNumbers(int.from_bytes(b64(k["e"]), "big"),
                               int.from_bytes(b64(k["n"]), "big")).public_key()
    signed, sig = t.rsplit(".", 1)
    pub.verify(b64(sig), signed.encode(), padding.PKCS1v15(), hashes.SHA256())
    return json.loads(b64(t.split(".")[1]))["kubernetes.io"]["serviceaccount"]["name"]

for label, f in (("genuine", "tok.txt"), ("forged ", "forged.txt")):
    try:
        print(f"{label}: verified as {whoami(open(f).read().strip())}")
    except Exception as e:
        print(f"{label}: {type(e).__name__}")
EOF
```

```
genuine: verified as probe
forged : InvalidSignature
```

Two things to take away beyond "call verify".

First, **the vulnerable version is the one that looks simpler**, and it works perfectly in every test written by an honest developer. There is no failing test to write until somebody thinks of forging, which is why this defect survives code review: the diff that introduces it is three lines of obviously-correct base64 handling.

Second, the fixed version is still not finished. It checks the signature and nothing else, so it would accept a token from any issuer whose key happens to be in that file, addressed to any audience, expired by a year. Lesson 04's four checks are signature, `iss`, `aud`, `exp` — **and a verifier that does one of the four is closer to the vulnerable version than to a correct one.**

</details>

---

## Drill 6 — a permission that no binding mentions

**Target: 7 minutes**, clock starting when the symptom appears — see [the clock](#the-clock) above.

First, set the scene. Run this and then put it out of your mind — pretend a colleague ran it last quarter to unblock a deployment, and that it is one line among four hundred in a cluster you inherited:

```bash
kubectl create clusterrolebinding convenience \
  --clusterrole=edit --group=system:authenticated
```

Now the symptom. A ServiceAccount created seconds ago, with nothing anywhere pointing at it, can delete pods:

```bash
kubectl create serviceaccount newcomer
kubectl auth can-i delete pods --as=system:serviceaccount:default:newcomer
kubectl get rolebindings,clusterrolebindings -A -o json | grep -c 'newcomer'
```

```
serviceaccount/newcomer created
yes
0
```

Zero bindings mention it, by name, anywhere in the cluster — and it can delete pods. **Find the grant.**

<details>
<summary>Answer</summary>

Nothing about the account is wrong, so stop looking at the account. Lesson 01 established that authentication produces a name **and a set of groups**, and every rule can name either — so grep the subject list for the groups this identity is in, not for its name:

```bash
kubectl auth whoami --as=system:serviceaccount:default:newcomer
```

```
ATTRIBUTE   VALUE
Username    system:serviceaccount:default:newcomer
Groups      [system:serviceaccounts system:serviceaccounts:default system:authenticated]
```

`system:authenticated` — which contains every identity that authenticated by any means, which is every real user and every ServiceAccount in the cluster. One ClusterRoleBinding to that group granted `edit`, cluster-wide, to everybody at once, and it will grant it to every account anybody creates in future.

Then ask the question backwards, which is the only method that finds this reliably. Lesson 06's script, pointed at the verb — and if `$TMPDIR` has been cleared since you ran it, or you are simply in a later shell session, re-create it from lesson 06 first:

```bash
python3 "${TMPDIR:-/tmp}/whocan.py" | head -4
```

```
objects read: 162   (73 ClusterRoles, 14 Roles, 61 ClusterRoleBindings, 14 RoleBindings)
subjects that can delete pods in default: 16
  Group           kubeadm:cluster-admins             cluster-wide via kubeadm:cluster-admins
  Group           system:authenticated               cluster-wide via convenience
```

There it is, in the first two lines of results, named as a **Group** rather than an account. Two general points:

**Auditing an identity cannot find this, and auditing the rules can.** Every question of the form "what is bound to this ServiceAccount?" returns nothing, forever, no matter how carefully you ask. The grant does not mention the account and never will, because group membership is attached by whatever authenticated you — lesson 01's closing point, arriving as an incident.

**And this is the README's third failure shape**, the one about permission accumulating: a binding to a broad group is the cheapest possible way to make a complaint go away, it is a single line in a review, it never appears in any per-account audit, and nobody will ever delete it because nobody can prove what would break. Compare the two candidate groups if you want to see how close the footgun is: `system:authenticated` versus `system:unauthenticated`, one character of thought apart, and only one of them includes `system:anonymous`.

</details>

---

## Clean up

```bash
kubectl delete clusterrolebinding convenience --ignore-not-found
kubectl delete rolebinding probe-reads --ignore-not-found
kubectl delete role pod-reader --ignore-not-found
kubectl delete serviceaccount probe newcomer --ignore-not-found
kubectl delete namespace app --ignore-not-found
```

---

↑ **[Act IX overview](README.md)** · Prev: **[Test yourself](test-yourself.md)** · Next: **[In the wild](in-the-wild.md)** →
