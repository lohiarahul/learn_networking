# GitOps, which you have already built

You have four pieces of this and nobody has put them next to each other.

[Act VI's reconciliation loop](../act-6-control-plane/03-the-reconciliation-loop.md) established the
shape: a controller reads a desired state, compares it to the world, acts on the difference, and does it
again forever. [The last lesson](08-shipping-a-set-of-objects.md) established that Helm and Kustomize are
both **client-side** — neither is a Kubernetes feature, and the thing that ends up in the cluster is a
plain manifest either way. It also showed you drift: `helm list` cheerfully reporting `deployed` while
the cluster disagreed with the release. And [Act X's supply-chain lesson](../act-10-cluster-security/08-what-you-shipped.md)
will make the uncomfortable point that a Pod spec is not a description of what is running, because a tag
is a name somebody else resolves.

Put those together and you have the whole idea, including its limits. **GitOps is the reconciliation loop
with a git repository as the desired state**, and every interesting property it has — and every
interesting failure — follows from that one sentence rather than from any product.

So build it. It is four lines, and building it is the only way to see which of its famous properties are
real and which are marketing.

> **Predict first —** you are about to run a loop that pulls a repo and applies it every ten seconds.
> Commit to an answer for each: (a) somebody runs `kubectl scale` by hand — what happens, and how long
> does it take? (b) somebody deletes a manifest **file** from the repo — what happens to the object it
> created? (c) two clusters sync the same commit — are they running the same code? Two of those three
> answers surprise people, and it is not the one everybody quotes.

## The bench

A "remote" that is just a directory, because nothing here needs a server:

```bash
mkdir -p ~/fleet-lab && cd ~/fleet-lab
git init -q --bare fleet.git
git clone -q fleet.git fleet
cd fleet
git config user.email you@example.com
git config user.name "you"
mkdir apps
```

Two manifests — a namespace and a Deployment, the smallest thing that is more than one object:

```bash
cat > apps/00-ns.yaml <<'EOF'
apiVersion: v1
kind: Namespace
metadata: { name: fleet }
EOF

cat > apps/web.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: { name: web, namespace: fleet }
spec:
  replicas: 2
  selector: { matchLabels: { app: web } }
  template:
    metadata: { labels: { app: web } }
    spec:
      containers:
        - name: c
          image: nginx:1.27-alpine
EOF

git add -A && git commit -q -m "web, two replicas" && git push -q origin HEAD
git log --oneline -1
```

The `00-` prefix is doing real work: `kubectl apply -f apps/` walks the directory in name order, and the
namespace has to exist before something is put in it. That is the entire content of what the products
call **sync waves** — an ordering problem that exists because a directory of manifests has no dependency
information in it at all.

## The reconciler

In a second terminal, and this is the whole thing:

```bash
cd ~/fleet-lab
git clone -q fleet.git live
while true; do
  git -C live pull -q
  kubectl apply -f live/apps/ | sed 's/^/  /'
  echo "--- $(date +%T) ---"
  sleep 10
done
```

```
  namespace/fleet created
  deployment.apps/web created
--- 14:22:31 ---
  namespace/fleet unchanged
  deployment.apps/web unchanged
--- 14:22:41 ---
```

`unchanged` on every pass after the first is the loop doing its job. It is also the answer to a question
people ask about GitOps controllers — *doesn't that hammer the API server?* — no, because `apply` sends a
patch the server computes to be empty and nothing is written. The store's revision does not move.

Leave that running. Everything below happens in the first terminal.

## What self-heal actually is

```bash
kubectl -n fleet scale deploy/web --replicas=5
kubectl -n fleet get deploy web -o jsonpath='{.spec.replicas}{"\n"}'
```

```
5
```

Wait for the loop's next pass, then ask again:

```bash
kubectl -n fleet get deploy web -o jsonpath='{.spec.replicas}{"\n"}'
```

```
2
```

**That is self-heal, and there is no healing in it.** Nothing detected an anomaly, nothing decided your
change was unauthorised, nothing was reverted. The loop asserted the repo's number, exactly as it does on
every pass, and the previous number stopped existing. It is the same non-event as Act VI's
`kubectl delete pod` — the deletion succeeds and a Pod comes back, and no component ever "noticed" the
deletion.

Which tells you the actual property, and it is more useful than the slogan: **a GitOps loop does not stop
you changing the cluster. It bounds how long your change survives.** Ten seconds here; a minute or two in
production. That is a real and valuable guarantee, and it is not the guarantee people describe when they
say the cluster "cannot" drift.

It also tells you what a GitOps repo turns `kubectl edit` into: a way to test a change with an automatic
expiry. Used deliberately that is a good tool. Used by accident it is an outage that fixes itself just
slowly enough to waste an afternoon of debugging.

## Drift, before anything acts on it

Stop the loop for a moment (`Ctrl-C` in the second terminal). Drift the cluster again and then ask the
question the loop asks, without letting it answer:

```bash
kubectl -n fleet scale deploy/web --replicas=5
kubectl diff -f live/apps/ ; echo "exit $?"
```

```
 spec:
   progressDeadlineSeconds: 600
-  replicas: 5
+  replicas: 2
   revisionHistoryLimit: 10
exit 1
```

`-` is the cluster, `+` is the repo, and **the exit code is the part that matters**: `1` means they
disagree. That is the whole of what a GitOps dashboard means by `OutOfSync`, available in one command with
no controller, no CRD and no product — which makes it the thing to reach for on any cluster whose desired
state lives in files. It is also the safety check to run before any `apply` you are not certain about, and
the reason to put it in CI: a pull request that changes more than its author thought will say so here.

## The property nobody predicts

Restart the loop, and now delete a manifest **from the repo** — the way you would decommission a service:

```bash
cat > apps/cache.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: { name: cache, namespace: fleet }
spec:
  replicas: 1
  selector: { matchLabels: { app: cache } }
  template:
    metadata: { labels: { app: cache } }
    spec:
      containers:
        - name: c
          image: nginx:1.27-alpine
EOF
git add -A && git commit -q -m "add cache" && git push -q origin HEAD
```

Wait for a pass, confirm `cache` exists, then remove it and push again:

```bash
git rm -q apps/cache.yaml
git commit -q -m "decommission cache" && git push -q origin HEAD
```

Wait for two more passes, and look:

```bash
kubectl -n fleet get deploy
kubectl diff -f live/apps/ >/dev/null 2>&1; echo "diff exit $?"
```

```
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
cache   1/1     1            1           2m
web     2/2     2            2           4m

diff exit 0
```

**The repo no longer mentions `cache`, `cache` is still running, and the drift check says everything is
in sync.** Read that third line twice, because it is worse than the second. `kubectl apply -f` is told
about files; a deleted file is not a file, so it is not in the input, so nothing about it is compared and
nothing about it is reported. The object is not *wrong*. It is **unmanaged** — and there is no longer
anything in your system that knows it was ever supposed to be managed.

This is why every real GitOps tool has an explicit, off-by-default **prune** setting, and why turning it
on is the scariest switch in the product. `kubectl` has the same one:

```bash
kubectl apply -f live/apps/ -n fleet \
  --prune -l app.kubernetes.io/managed-by=fleet
```

```
deployment.apps/web configured
deployment.apps/cache pruned
```

Look at what that command needed. **It cannot work from the files alone** — it needs a label selector,
because "delete everything in the cluster that this directory does not mention" is only a safe sentence
if you first say which part of the cluster the directory is responsible for. Get the selector wrong and
you have written `kubectl delete` against somebody else's namespace, phrased as a sync. Every object the
loop creates therefore has to carry the label, from the beginning, which is a decision you make on day
one and cannot retrofit safely — the objects that predate the label are exactly the ones prune will not
find, and the ones a wrong selector will.

Note also the deprecation warning that command prints about `--prune-allowlist`: the flag's own semantics
are still moving, which is a reasonable signal about how easy this is to get right.

## And whether two clusters running one commit are running one thing

```bash
grep image: apps/web.yaml
kubectl -n fleet get pod -l app=web \
  -o jsonpath='{.items[0].spec.containers[0].image}{"\n"}{.items[0].status.containerStatuses[0].imageID}{"\n"}'
```

```
          image: nginx:1.27-alpine
nginx:1.27-alpine
sha256:96868d9fa38f469a86d2f25787e43ee9ad330339d30be260aa9f5a338bb03751
```

Three lines, and two of them agree with each other while neither describes what is running. The repo says
a **tag**. The Pod spec says the same tag, faithfully. And `imageID` — the only one of the three that
identifies bytes — says something the repo has never contained and cannot control, because the tag was
resolved by a registry at pull time, on that node, at that moment.

So the claim that the repo is the single source of truth is exactly as true as the tag is immutable, which
is not at all. Sync two clusters from one commit a month apart and they can run different code with a
perfectly green dashboard on both. The fix is the one [Act X](../act-10-cluster-security/08-what-you-shipped.md)
argues at length — put digests in the repo, not tags — and the cost is that a digest is unreadable and has
to be produced by a build rather than typed by a human. Which is the honest trade, and the reason so many
GitOps repos quietly contain tags.

## What the real tools add

Nothing above needed Argo CD or Flux, and the four lines you wrote are not a toy version of them — they
are the mechanism, and the products are that mechanism plus the operational parts:

- **The loop runs in the cluster**, as a controller, so it survives your laptop closing. Which means the
  repository is now a production credential, and a merge is a deploy. Who may approve a pull request has
  become an authorisation question about the cluster — the single largest thing GitOps changes, and it is
  not technical.
- **A status you can read.** Yours has none: the loop's output scrolls past and nothing records that pass
  47 failed. `Synced` / `OutOfSync` / `Healthy` as fields on an object is what turns your `diff` exit code
  into something a human can be paged about.
- **Ordering that is declared rather than alphabetical.** Your `00-` prefix works and does not scale past
  the first thing that needs to wait for a CRD to be established.
- **Prune, with a blast radius somebody thought about**, which is the whole of the previous section.
- **Many repos, many clusters, one controller**, and the recursion where the thing that defines the apps
  is itself an app in a repo — *app-of-apps*, which is just this loop applied to its own configuration.

None of that changes the sentence at the top. If you can say why `unchanged` is the correct output, why
self-heal is not healing, and why a deleted file is not a deletion, you can read any GitOps tool's docs as
a list of decisions rather than a list of features.

## Clean up

```bash
kubectl delete namespace fleet
cd ~ && rm -rf ~/fleet-lab
```

(The loop is still running in the other terminal; `Ctrl-C` it first, or it will recreate the namespace on
its next pass — which is one last demonstration of the only property that was ever real.)

<!-- figure -->

```
   GITOPS = the RECONCILIATION LOOP (VI/03) with a GIT REPO as desired state.
     four lines: git pull ; kubectl apply -f . ; sleep. that is the mechanism.

   WHAT IS REAL
     "unchanged" every pass  -> apply sends an empty patch. store does not move.
     SELF-HEAL is not healing. nothing noticed your edit. the loop just
       asserts the repo again -> your change EXPIRES, in one interval.
       the guarantee is a TIME BOUND, not prevention.
     kubectl diff -f dir/ ; echo $?   ->  1 = OutOfSync. that is the
       whole dashboard, in one command, with no product.

   WHAT IS NOT
     DELETE A FILE -> the object LIVES. and diff exits 0, "in sync",
       because a deleted file is not in the input, so nothing compares it.
       the object is not wrong, it is UNMANAGED, and nothing knows.
       -> --prune needs a LABEL SELECTOR: "what is this dir responsible for?"
          get it wrong and you have typed kubectl delete, spelled "sync".
     THE REPO IS NOT THE SOURCE OF TRUTH while it holds a TAG.
       repo: nginx:1.27-alpine · spec: same · imageID: sha256:9686...
       one commit, two clusters, two months -> different code, green both.
       digests fix it; digests cannot be typed by a human.

   WHAT THE PRODUCTS ADD: loop in-cluster (so the REPO IS A CREDENTIAL and a
     merge is a deploy) · a status field to page on · declared ordering ·
     prune with a considered blast radius · app-of-apps = the loop on itself.
```

> **You understand this when you can** write a GitOps reconciler in four lines and say why
> `unchanged` is the correct output on every pass after the first; state what self-heal guarantees
> as a bound rather than a prevention; get `kubectl diff -f` to report `OutOfSync` and say which
> of `-` and `+` is the cluster; predict what happens to an object whose manifest is deleted, and
> name the flag that changes it; and say why two clusters on one commit can run different code.

**Which raises:** every object in that repo was a kind the API server already knew. The loop worked because
`apply` had somewhere to put a `Deployment`. So what happens when the thing you want to reconcile is not a
kind Kubernetes ships — and who writes the loop then?

---

← Prev: **[Shipping a set of objects](08-shipping-a-set-of-objects.md)** · ↑ **[Act VII overview](README.md)** · Next: **[Adding a kind](09-adding-a-kind.md)** →
