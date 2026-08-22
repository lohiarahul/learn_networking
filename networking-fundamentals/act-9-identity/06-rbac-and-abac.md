# Two ways to write down a permission

Five lessons have been spent getting a trustworthy name to the place a decision is made. That work is finished, and it delivered surprisingly little: a string, some groups, maybe a scope. Lesson 05's token said `sub`, `azp` and `scope=openid email profile`; the cluster's said `system:serviceaccount:default:probe` — and every one of those is text that arrived unaltered from an issuer you chose to trust.

**Nothing in it says what any of that permits.** Somewhere a system holds rules, and the rules take a name, a verb and an object and return one bit.

Which makes an authorization system a *representation of a function* — from `(who, what, to which thing, in what circumstances)` to `yes` or `no`. Put that way the design space collapses, because there are only two families of way to write a function down. You can **enumerate** it, or you can **describe** it.

This lesson builds one of each and then asks both the same question. They answer it very differently, and that difference is what people are actually arguing about when they argue about IAM.

> **Predict first —** you are going to build both models and then ask each of them: **"who can delete this pod?"** For each model, write down whether you expect the answer to come back as a list of names, and roughly how you would compute it. Then predict which of the two makes the *forward* question — "may this specific person do this specific thing?" — the harder one. Commit to that last one in writing, because it is where most people's intuition goes wrong.

### Model one: name the permission, then hand out the name

The enumerating model is **RBAC**, and its whole trick is arithmetic. Ten people and twenty permissions is two hundred possible facts to maintain. Invent an intermediate noun — a *role* — and it becomes ten facts plus twenty facts. Roles exist to turn a multiplication into an addition, and nearly every other property of RBAC follows from that one move.

So it needs three things: a named set of permissions, a subject, and a join between them. Kubernetes is the cleanest RBAC in wide use, so build it there.

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act9.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
kubectl create serviceaccount probe
kubectl create role pod-reader --verb=get,list --resource=pods
kubectl create rolebinding probe-reads --role=pod-reader \
  --serviceaccount=default:probe
```

```
serviceaccount/probe created
role.rbac.authorization.k8s.io/pod-reader created
rolebinding.rbac.authorization.k8s.io/probe-reads created
```

Three objects — and a fourth thing that is not one of them: the **namespace** the Role and the RoleBinding were created in. A Namespace is certainly an object in its own right; you have been making and deleting them since Act V. But it is not a *participant* in the grant the way the other three are. It is the scope the grant is written inside, and it is the reason every piece of this model has a cluster-wide twin: `Role` and `RoleBinding` are confined to one namespace, `ClusterRole` and `ClusterRoleBinding` are not. Now ask forward — and notice lesson 01 already handed you the tool for this, because "may this name do this thing?" needs no credential:

```bash
S=system:serviceaccount:default:probe
kubectl auth can-i list   pods --as=$S
kubectl auth can-i delete pods --as=$S
```

```
yes
no
```

And because the model enumerates, you can ask for everything a subject may do:

```bash
kubectl auth can-i --list --as=$S 2>/dev/null | head -8
```

```
Resources                                       Non-Resource URLs                      Resource Names   Verbs
selfsubjectreviews.authentication.k8s.io        []                                     []               [create]
selfsubjectaccessreviews.authorization.k8s.io   []                                     []               [create]
selfsubjectrulesreviews.authorization.k8s.io    []                                     []               [create]
pods                                            []                                     []               [get list]
                                                [/.well-known/openid-configuration/]   []               [get]
                                                [/.well-known/openid-configuration]    []               [get]
                                                [/api/*]                               []               [get]
```

Two things arrive there for free. `pods [get list]` is the role you just wrote. And **the discovery endpoints from lesson 04 are in the same table** — the `nonResourceURLs` rule you went hunting for when `system:anonymous` turned out to be unable to fetch the cluster's public keys. It was never a special case. It was a row in this list all along.

Now add a second permission through a second binding, and watch what combination means:

```bash
kubectl create role pod-deleter --verb=delete --resource=pods
kubectl create rolebinding probe-deletes --role=pod-deleter \
  --serviceaccount=default:probe
kubectl auth can-i --list --as=$S 2>/dev/null | grep '^pods'
kubectl delete rolebinding probe-deletes
kubectl auth can-i --list --as=$S 2>/dev/null | grep '^pods'
```

```
pods                                            []                                     []               [get list delete]
rolebinding.rbac.authorization.k8s.io "probe-deletes" deleted from default namespace
pods                                            []                                     []               [get list]
```

**Permissions are unioned, and there is no way to write a denial.** Kubernetes RBAC has no `deny` — not an oversight, a decision, and it buys a property worth naming precisely: the function is **monotone**. Adding a binding can only add permissions; removing one can only remove them. So a one-line change to a binding can be reviewed *locally*, by reading the line, without holding the rest of the cluster's rules in your head.

Hold on to that. It is exactly what the other model gives up.

### Ask it backwards

Now the question you predicted. `can-i --list` went forward, from a subject to its permissions. Go the other way: **who can delete pods in `default`?**

There is no command for this, which is itself a finding. But the model enumerates, so you can compute it — walk every role and decide whether its rules permit the verb, then walk every binding pointing at such a role:

```bash
cat > "${TMPDIR:-/tmp}/whocan.py" <<'EOF'
import json, subprocess
VERB, RES, NS = "delete", "pods", "default"

def get(kind, *a):
    out = subprocess.run(["kubectl", "get", kind, "-o", "json", *a],
                         capture_output=True, text=True).stdout
    return json.loads(out)["items"]

def permits(rules):
    for r in rules:
        if (VERB in r.get("verbs", []) or "*" in r.get("verbs", [])) \
        and (RES in r.get("resources", []) or "*" in r.get("resources", [])) \
        and ("" in r.get("apiGroups", []) or "*" in r.get("apiGroups", [])):
            return True
    return False

croles = {c["metadata"]["name"]: c for c in get("clusterroles")}
roles  = {(r["metadata"]["namespace"], r["metadata"]["name"]): r for r in get("roles", "-A")}
crb, rb = get("clusterrolebindings"), get("rolebindings", "-A")

hits = []
for b in crb:
    rr = b["roleRef"]
    if rr["kind"] == "ClusterRole" and permits((croles.get(rr["name"]) or {}).get("rules") or []):
        hits += [(s.get("kind"), s.get("name"), "cluster-wide via " + b["metadata"]["name"])
                 for s in b.get("subjects") or []]
for b in rb:
    ns, rr = b["metadata"]["namespace"], b["roleRef"]
    if ns != NS:
        continue
    src = croles.get(rr["name"]) if rr["kind"] == "ClusterRole" else roles.get((ns, rr["name"]))
    if src and permits(src.get("rules") or []):
        hits += [(s.get("kind"), s.get("name"), f"in {ns} via " + b["metadata"]["name"])
                 for s in b.get("subjects") or []]

print(f"objects read: {len(croles)+len(roles)+len(crb)+len(rb)}"
      f"   ({len(croles)} ClusterRoles, {len(roles)} Roles,"
      f" {len(crb)} ClusterRoleBindings, {len(rb)} RoleBindings)")
print(f"subjects that can {VERB} {RES} in {NS}: {len(hits)}")
for k, n, w in sorted(set(hits)):
    print(f"  {k:15} {n:34} {w}")
EOF
python3 "${TMPDIR:-/tmp}/whocan.py"
```

```
objects read: 160   (73 ClusterRoles, 14 Roles, 60 ClusterRoleBindings, 13 RoleBindings)
subjects that can delete pods in default: 15
  Group           kubeadm:cluster-admins             cluster-wide via kubeadm:cluster-admins
  Group           system:masters                     cluster-wide via cluster-admin
  ServiceAccount  cronjob-controller                 cluster-wide via system:controller:cronjob-controller
  ServiceAccount  daemon-set-controller              cluster-wide via system:controller:daemon-set-controller
  ServiceAccount  device-taint-eviction-controller   cluster-wide via system:controller:device-taint-eviction-controller
  ServiceAccount  generic-garbage-collector          cluster-wide via system:controller:generic-garbage-collector
  ServiceAccount  job-controller                     cluster-wide via system:controller:job-controller
  ServiceAccount  namespace-controller               cluster-wide via system:controller:namespace-controller
  ServiceAccount  node-controller                    cluster-wide via system:controller:node-controller
  ServiceAccount  persistent-volume-binder           cluster-wide via system:controller:persistent-volume-binder
  ServiceAccount  pod-garbage-collector              cluster-wide via system:controller:pod-garbage-collector
  ServiceAccount  replicaset-controller              cluster-wide via system:controller:replicaset-controller
  ServiceAccount  replication-controller             cluster-wide via system:controller:replication-controller
  ServiceAccount  statefulset-controller             cluster-wide via system:controller:statefulset-controller
  User            system:kube-scheduler              cluster-wide via system:kube-scheduler
```

**A finite, complete, nameable list.** That is the defining property of the enumerating model: the reverse question has an answer of the same kind as the forward one, and computing it is a matter of reading enough objects — a hundred and sixty of them, here, which is tedious rather than hard.

Two of the rows repay a second look. Thirteen of the fifteen are **controllers**, which is Act VI's reconciliation loop appearing in an entirely different guise: the ReplicaSet controller can delete your pods because deleting pods is how it makes the world match the spec. Permissions are where a control loop's *authority* is written down, and reading them backwards is a way of discovering what the cluster does to itself.

And `Group kubeadm:cluster-admins` is the `O=` field you built into a client certificate by hand in Act VIII, arriving here as a subject in a binding. That is the join finally visible from both ends: a certificate put a string in a group, and a binding gave that string a role.

> **Check yourself —** that list is wrong in two opposite directions at once. Name a reason it is too *long*, and a reason it is too *short*. The second one matters more, and Acts VI and VIII both told you about it.

<details>
<summary>Answer</summary>

**Too long**, most obviously, because a binding can name a subject that does not exist and nothing complains — RBAC bindings are not foreign keys, so a group nobody is in and a ServiceAccount you deleted last month both still appear. It also ignores `resourceNames`, which can narrow a rule to specific objects, so some of these "can delete pods" entries can in truth delete only one named pod.

**Too short** for a much more interesting reason: **`system:masters` does not need this binding at all.** Act VI showed that the group is wired into the API server itself and bypasses authorization entirely — the `cluster-admin` binding you see here is belt-and-braces. Delete it and that row would vanish from the report while losing exactly none of its power.

Which is the real lesson, and it survives leaving Kubernetes: **the rule store is not the whole truth.** An API server does not consult one authorizer, it consults a *chain*, and RBAC is one link in it — `system:masters` is short-circuited before the chain starts, and this cluster runs another link whose entire job is deciding what each kubelet may touch, answered from where the scheduler put the Pods rather than from any Role you could read. A cluster can also be configured to ask an external service over HTTP, in which case the rules are not in the cluster at all. Any report you build by reading Roles and bindings is therefore a lower bound on who can act.

Hence the discipline: an enumeration of permissions is *evidence*, not proof, and the first question to ask of any access report is what authorizers it did not know about.

</details>

### Model two: describe the permission with a predicate

The other family does not enumerate anything. It writes down a **boolean expression over attributes** — of the subject, the action, the object, and the surrounding world — and evaluates it per request. That is **ABAC**, and it is easiest to understand by building the whole thing, which takes about thirty lines.

```bash
cat > "${TMPDIR:-/tmp}/abac.py" <<'EOF'
import itertools
from dataclasses import dataclass

@dataclass
class Req:
    who: str; tags: frozenset; action: str; kind: str; owner: str
    hour: int; incident: bool; from_office: bool

ALLOW = [
  ("an owner may delete their own pod",
   lambda r: r.action == "delete" and r.kind == "pod" and r.owner == r.who),
  ("on-call may delete any pod, during an incident",
   lambda r: r.action == "delete" and r.kind == "pod"
             and "on-call" in r.tags and r.incident),
]
DENY = [
  ("no deletes outside 09-17 from outside the office",
   lambda r: r.action == "delete" and not (9 <= r.hour < 17) and not r.from_office),
]

def decide(r):
    if any(f(r) for _, f in DENY):
        return False
    return any(f(r) for _, f in ALLOW)

SUBJECTS = [("alice", frozenset()), ("bob", frozenset({"on-call"})), ("carol", frozenset())]

print("forward -- may bob delete alice's pod at 10:00, in the office, no incident?")
print("   ", decide(Req("bob", frozenset({"on-call"}), "delete", "pod", "alice", 10, False, True)))
print()
print("reverse -- WHO can delete pod 'web-1', owned by alice?")
space = list(itertools.product(SUBJECTS, range(24), (True, False), (True, False)))
yes = [(w, h, i, o) for (w, t), h, i, o in space
       if decide(Req(w, t, "delete", "pod", "alice", h, i, o))]
print(f"    states enumerated : {len(space)}   (3 subjects x 24 hours x incident x location)")
print(f"    states that permit: {len(yes)}")
for who in ("alice", "bob", "carol"):
    n = len([r for r in yes if r[0] == who])
    print(f"      {who:6} permitted in {n:3} of {len(space)//3} states")
EOF
python3 "${TMPDIR:-/tmp}/abac.py"
```

```
forward -- may bob delete alice's pod at 10:00, in the office, no incident?
    False

reverse -- WHO can delete pod 'web-1', owned by alice?
    states enumerated : 288   (3 subjects x 24 hours x incident x location)
    states that permit: 96
      alice  permitted in  64 of 96 states
      bob    permitted in  32 of 96 states
      carol  permitted in   0 of 96 states
```

Start with what this model can say that the other one cannot, because it is not one thing but two, and they are impossible in RBAC for genuinely different reasons.

**"An owner may delete their own pod" is inexpressible because ownership is a relation.** A role is a property of the *subject*, fixed at the moment somebody wrote the binding; ownership is a fact about a subject and an object *together*. There is no set of pods you can list in a role that means "the ones belonging to whoever is asking," because the rule needs to compare a field of the requester with a field of the thing requested — and RBAC's `resourceNames` takes a list of names, never a comparison.

**"During an incident" is inexpressible for a blunter reason: RBAC is never told.** Look again at what the forward question actually took: a subject, a verb, a resource, a namespace. That is the complete input. The hour of the day, whether an incident is open, and where the request came from are not attributes RBAC handles badly — they are not *arguments to the function at all*, so no extension of the rule syntax could mention them. Every field in that dataclass past `who` and `tags` is one or the other: `owner` is a relation RBAC cannot express, and `hour`, `incident` and `from_office` are context RBAC cannot see.

And the forward question is just as cheap as it was before: one call, one boolean. **If you predicted that the descriptive model would make the forward question harder, that is the prediction worth having got wrong** — both models answer "may X do Y?" instantly, because that is the question both were built to answer.

The asymmetry is entirely in the other direction.

### The answer that is not a list

Look at what came back from the reverse question. Not fifteen names. Three names with fractions attached: alice in 64 of 96 states, bob in 32, carol in none.

**"Who can delete this pod?" has no answer of the form "these people".** The honest answer is a *predicate* — "alice, unless it is outside working hours and she is not in the office; and bob, but only during an incident, and subject to the same hours rule." To produce even those fractions the script had to enumerate the whole state space: two hundred and eighty-eight evaluations, for three subjects and three attributes.

Now count what happens as the model gets more useful. Swap `from_office` for a source IP address and the space is multiplied by four billion. Add a label whose value is free text and the space stops being finite. **The reverse question does not get harder; it stops having a computable answer**, and the only way back is a constraint solver rather than a loop.

Which explains something you have probably noticed and filed away as vendor awkwardness. **Every cloud IAM ships a policy *simulator* — ask about one concrete request, get one answer — rather than a report of who can do what.** It is not a missing feature. In the descriptive model, one-request-at-a-time is the only question that is cheap, and "who can read this bucket?" is a genuinely hard problem at every organisation you will ever work for.

### The failures are opposite, and one of them is a story

You now have both models in front of you, so add a rule. A sensible one, of a kind somebody proposes in a review after a bad afternoon: *nobody should be deleting other people's pods during an incident — that is when mistakes are most expensive.*

```bash
python3 - <<'EOF'
import itertools
from dataclasses import dataclass
@dataclass
class Req:
    who: str; tags: frozenset; action: str; kind: str; owner: str
    hour: int; incident: bool; from_office: bool
ALLOW = [
  lambda r: r.action == "delete" and r.kind == "pod" and r.owner == r.who,
  lambda r: r.action == "delete" and r.kind == "pod" and "on-call" in r.tags and r.incident,
]
DENY = [
  lambda r: r.action == "delete" and not (9 <= r.hour < 17) and not r.from_office,
  # the new rule:
  lambda r: r.action == "delete" and r.kind == "pod" and r.owner != r.who and r.incident,
]
def decide(r):
    if any(f(r) for f in DENY): return False
    return any(f(r) for f in ALLOW)
SUBJECTS = [("alice", frozenset()), ("bob", frozenset({"on-call"})), ("carol", frozenset())]
space = list(itertools.product(SUBJECTS, range(24), (True, False), (True, False)))
yes = [(w, h, i, o) for (w, t), h, i, o in space
       if decide(Req(w, t, "delete", "pod", "alice", h, i, o))]
for who in ("alice", "bob", "carol"):
    print(f"      {who:6} permitted in {len([r for r in yes if r[0]==who]):3} of {len(space)//3} states")
EOF
```

```
      alice  permitted in  64 of 96 states
      bob    permitted in   0 of 96 states
      carol  permitted in   0 of 96 states
```

**Bob has gone from thirty-two states to none.** The rule that did it never mentions on-call, never mentions bob, and never mentions the break-glass path it destroyed — it is a statement about ownership and incidents that happens to intersect the only condition under which the emergency permission existed. Nothing errored. Nothing warned. The system is working exactly as written, and you find out during the next outage, at the worst possible moment, from the one person who needed it.

**That is the descriptive model's characteristic failure: a change whose effects cannot be enumerated, in a rule set nobody can hold in their head.** It is not carelessness — the reviewer would have had to evaluate a state space to catch it, and there was no state space small enough to evaluate.

RBAC's characteristic failure is the opposite and much duller. It cannot express "their own", so somebody widens a role until it covers the case. Nobody ever removes a binding, because removing one is how you cause an outage and nothing rewards you for it. And permissions are unioned, so the set a person holds is larger than any role they were given — the model computes exactly the accumulation you were trying to avoid. **The descriptive model fails by becoming incomprehensible; the enumerating model fails by becoming too permissive, slowly, in a way that is fully visible in a report nobody reads.**

|  | enumerating (RBAC) | describing (ABAC) |
|---|---|---|
| "may X do Y?" | cheap | cheap |
| "who can do Y?" | a finite list, from reading the rules | a predicate; needs a solver once attributes are unbounded |
| relations like "their own" | inexpressible | natural |
| context: time, source, incident state | inexpressible | natural |
| effect of one change | local, and monotone if there is no deny | potentially anywhere |
| how it rots | over-permission, visibly | complexity, invisibly |

### The combining rule is the actual argument

One thing decides most of the above, and it is the smallest part of either system: **what happens when two rules disagree.**

Kubernetes RBAC has no denials, so the combining rule is union, and union is monotone. Add a binding and no existing permission changes. That is why a Kubernetes RBAC change is reviewable as a diff.

AWS IAM takes the other option: **an explicit deny wins.** And a deny can be written in more than one place — attached to the identity, attached to the resource, or imposed from a level above the account entirely — with all of them evaluated together for a single request. The gain is real: you can carve exceptions out of broad grants, which is the only tractable way to manage thousands of accounts. The cost is that the function is no longer monotone — adding a statement can *revoke* something, and removing one can *grant* something — and no policy can be understood by reading it alone. Every IAM debugging session you will ever have is a hunt for a deny you did not know was there, in a document you did not know applied.

**Neither is a mistake. They chose different things to make reviewable.** And that is the sentence to carry into any authorization system, including ones this course never mentions: find the combining rule first, because it tells you what kind of reasoning the system will support.

Then notice what is underneath both of them, because you have met it twice already in this act.

> **RBAC stores the answer. ABAC computes it.**

A stored answer is instantly auditable and necessarily coarse — it cannot depend on anything that was not known when it was written down. A computed answer is exact and contextual and cannot be audited, because there is nothing to read.

**That is the act's trade with one term substituted, and the substitution is worth being exact about rather than waving at a resemblance.** Lessons 02 and 05 were both literally about *time*: a handle is current and costs you a lookup, a signed claim is instant and is a photograph. That is emphatically **not** what separates these two models. An RBAC verdict is computed against the live rule store on every single request, so it is no staler than an ABAC one; delete a binding and the next request feels it.

What carries over is the *structure*. One side commits to an answer in advance and gets back something you can read; the other works it out on demand and gets back something exact. In lessons 02 and 05, what committing early bought you was **speed**, and what it cost was **freshness**. Here what it buys is **auditability**, and what it costs is **precision**.

So: same shape, different currency — and noticing that it is a different currency is the point, because it tells you the shape was the general thing all along. *Commit early or compute late* is the form. Freshness was only the first thing anyone ever traded for it.

Which is also why you should not expect a real system to pick one — and there is evidence for that in front of you already, if you go looking.

This cluster is one you would describe without hesitation as "using RBAC". Yet lesson 04's `aud` check was a predicate over a request, not a role. And Act V's Ingress lesson mentioned, entirely in passing, a *webhook* that rejected a manifest — something consulted after the caller had been authorized, which had an opinion about the object's **contents** rather than about who was asking. Neither of those is expressible in a Role, and both were happening the whole time.

So hold the question rather than the answer. If the enumerating model provably cannot express a predicate, and the cluster is plainly evaluating some, **where did the predicates go?** Not into the Roles — you have read all seventy-three of the ClusterRoles' worth of vocabulary and there is nowhere to put one. Something else in the request path is doing that work, at a different stage, and the interesting part is not its name but *why later is better*: what does a system gain by refusing to mix predicates into its authorization rules, and instead running them afterwards, against the object rather than the caller? (AWS makes the opposite choice and hangs `Condition` keys directly off a policy statement. Which of those you prefer is a real argument, and having both models in your hands is what makes it arguable.)

<!-- figure -->
```
   AUTHORIZATION IS A FUNCTION
     (who, what, to which thing, in what circumstances)
       -> one bit
     and there are two ways to write a function down:
     ENUMERATE it, or DESCRIBE it.

   ENUMERATE = RBAC
     the trick is arithmetic: N subjects x M permissions
     becomes N + M by inventing an intermediate NOUN.
     objects: subject / role / binding (+ namespace as scope)
     k8s has NO DENY -> permissions are UNIONED -> the
     function is MONOTONE -> a one-line diff is reviewable
     LOCALLY, without holding the whole rule set in mind.

   ASK IT BACKWARDS: an answer of the same kind
     "who can delete pods in default?"
       160 objects read -> 15 named subjects. finite. complete.
     13 of the 15 are CONTROLLERS -- Act VI's reconcile
       loop, reappearing as its authority
     kubeadm:cluster-admins = the O= you put in a cert by
       hand in Act VIII, now a subject in a binding
     BUT the rule store is not the whole truth:
       an apiserver consults a CHAIN of authorizers.
       system:masters short-circuits before it starts.
       so the report is a LOWER BOUND. always ask which
       authorizers your report did not know about.

   DESCRIBE = ABAC
     a boolean expression over attributes of subject,
     action, object, and the WORLD.
     says things RBAC cannot say AT ALL, for TWO
     DIFFERENT reasons -- do not conflate them:
       "their OWN pod" = a RELATION. rbac rules list
         names; they never COMPARE two fields.
       time of day, incident, source address = CONTEXT.
         not handled badly -- never PASSED IN. the
         whole input is (subject, verb, resource, ns).
     forward question: still one call, still cheap.
     (if you predicted otherwise, that was the point.)

   ASK IT BACKWARDS: no answer of that kind exists
     "who can delete web-1?" -> 288 evaluations, and:
       alice 64/96,  bob 32/96,  carol 0/96
     the honest answer is a PREDICATE, not a list.
     swap office-or-not for a source IP: x 4 billion.
     add a free-text label: no longer finite.
     -> which is why every cloud IAM ships a SIMULATOR
        (one request, one answer) and not a report.

   THE FAILURES ARE OPPOSITE
     add ONE deny -- "no deleting others' pods during an
     incident" -- and bob goes 32 -> 0. the rule never
     mentions on-call. the break-glass path is gone. no
     error, no warning. you find out during the outage.
       ABAC rots by becoming INCOMPREHENSIBLE
     RBAC cannot say "their own", so roles get widened;
     nobody removes a binding; and the union of your
     roles exceeds any of them.
       RBAC rots by becoming OVER-PERMISSIVE, visibly,
       in a report nobody reads.

   THE COMBINING RULE DECIDES EVERYTHING
     k8s RBAC : union, no deny        -> monotone
     AWS IAM  : explicit DENY wins, across identity +
                resource + boundary + org policies
                -> precise, and NOT monotone: adding a
                statement can REVOKE. every IAM debug
                session is a hunt for an unseen deny.
     NEITHER IS WRONG. they made different things
     reviewable. find the combining rule FIRST.

   AND UNDERNEATH: THE ACT'S SHAPE, NEW CURRENCY
     RBAC STORES the answer  -> auditable, coarse
     ABAC COMPUTES it        -> exact, unauditable
     the SHAPE is L02's and L05's: commit early, or
     compute late. but NOT the same trade --
       L02/L05 : early bought SPEED, cost FRESHNESS
       here    : early buys AUDITABILITY, costs
                 PRECISION
     (an RBAC verdict is NOT stale. it is evaluated
      per request against the live rule store.)
     -> so freshness was never the point. "commit
        early or compute late" is the general form.

   AND NO REAL SYSTEM PICKS ONE
     this cluster "uses RBAC" -- and yet L04's aud
     check was a predicate, and Act V's ingress
     webhook judged an OBJECT, not a caller.
     so: WHERE DID THE PREDICATES GO? not into any
     Role -- there is nowhere to put one. something
     later in the request path does it.
     the question worth holding: why is LATER better?
     (AWS chose otherwise: Condition keys hang right
      off a policy statement. that is a real argument.)
```

**Cleanup:**

```bash
kubectl delete rolebinding probe-reads --ignore-not-found
kubectl delete role pod-reader pod-deleter --ignore-not-found
kubectl delete serviceaccount probe --ignore-not-found
```

> **You understand this when you can** describe authorization as a function and name the only two families of representation for one; explain what a role is *for* in terms of arithmetic; name the three objects a Kubernetes RBAC grant joins plus the scope that is not one of them, and say why that scope gives each of those objects a cluster-wide twin; explain why having no deny makes the function monotone and why that makes a change reviewable; compute who can perform a verb by reading the rule store, and give one reason such a report is too long and one reason it is too short; give the two *different* reasons "their own" and "during an incident" are both impossible in RBAC, and say why calling them the same reason is a mistake; say why the *forward* question is cheap in both models; explain why the reverse question in the descriptive model has no answer of the form "these names", and what happens to it when an attribute has an unbounded domain; account for why cloud IAM offers a simulator instead of a report; describe how a single reasonable deny rule can silently remove a permission it never mentions; state each model's characteristic way of rotting; explain what a combining rule is and contrast RBAC's union with IAM's explicit deny, including what each makes reviewable; and say what stored-versus-computed shares with lessons 02 and 05 — and, precisely, what it does *not*.

**Which raises:** every mechanism in this act now exists as something you have built or measured — an identity, a token, a signature you checked by hand, a delegation, and rules in both shapes. And a Kubernetes cluster has been quietly using all of them the whole time you were learning them separately: it authenticated you with a certificate in Act VIII and a token in Act IX, it publishes a JWKS, and it authorized you with RBAC just now. Which leaves the loose thread from a page ago — the predicates that are evidently being evaluated somewhere you have not looked — and a larger one behind it. **Every mechanism in this act arrived with its behaviour already chosen for you by whoever built the cluster.** Who may fetch the public keys, how long a token lives, whether an unauthenticated request gets anything at all: each of those was a setting, each had a default, and you accepted all of them without being asked. Defaults are chosen to make a cluster start, not to make it safe, and the distance between those two aims is where clusters are actually broken into. That is the subject of the act after this one, which is not yet written.

---

↑ **[Act IX overview](README.md)** · Prev: **[Delegation without handing over a password](05-oauth2-and-oidc.md)** · Next: **[Test yourself](test-yourself.md)** →
