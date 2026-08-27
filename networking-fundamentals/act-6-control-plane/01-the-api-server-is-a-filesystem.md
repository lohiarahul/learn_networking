# The API server is a filesystem

Every answer in Act V came out of a file on a node. The socket ledger in `/proc/net/tcp`. The DNAT chains in `iptables-save`. The resolver config the kubelet wrote at `/etc/resolv.conf`. The namespace inode under `/proc/<pid>/ns/net`. Five lessons of *read the file, and if a tool disagrees with the file, the file wins*.

Now do the same thing for a Pod. Make one first — the Act V labs cleaned up after themselves, so nothing is running:

```bash
kubectl run db-0 --image=hashicorp/http-echo -- /http-echo -text=db-0 -listen=:5432
kubectl wait --for=condition=Ready pod/db-0 --timeout=90s
```

```bash
kubectl get pod db-0 -o yaml        # a document. so where is it?
```

You have a document on your screen. **Go and find it on disk.** Not the container, not the logs — the object. Open a shell on the node the Pod is running on and locate the bytes that `kubectl` just printed you.

### Why can't you find the Pod on the node?

Because it isn't there. Search the node's disk and you will find the *consequences* of that Pod everywhere — a network namespace, a veth, a directory of mounted volumes under `/var/lib/kubelet/pods/<uid>/`, a running process — and nowhere will you find the document. The kubelet was *told* about that Pod; it never owned the record of it.

So the creed looks broken. Every layer so far handed you a file, and this one hands you an HTTP response.

Except look at what you actually typed. A path, and a verb.

```bash
kubectl get --raw /api/v1/namespaces/default/pods/db-0 | head -c 200; echo
```

That is the same request `kubectl get pod` made, with the sugar removed — and it is a **path**. `GET` on a path returns the object. `PUT` replaces it. `DELETE` unlinks it. There is a `/api/v1/namespaces/default/pods` above it that lists what is inside, the way reading a directory does.

Act I already told you what to make of that, in a line worth re-reading now:

> *"Everything is a file" is a claim about the **interface**, not a claim that bytes exist anywhere.*

A `/proc` file has size 0 and still pours out content, because procfs answers a read by **running a function** over live kernel state rather than fetching stored bytes. The API server is that same trick, one machine wider: a tree of paths, a fixed set of operations, and code behind every path. `kubectl get pod` is `cat` for a cluster.

Which leaves exactly one question, the same one Act I asked of procfs. Reading `/proc/net/dev` computes its answer from live kernel state. What does the API server compute *its* answer from?

### What is behind the paths?

There is one answer, and it is the only stateful component in a Kubernetes control plane: **etcd**, a distributed key-value store. Everything else — the scheduler, the controller manager, the kubelets — holds no durable truth at all. Lose them and they rebuild. Lose etcd and the cluster is gone.

Do not take that on trust. Go and read the keys.

etcd runs as a Pod in `kube-system`, and its image ships `etcdctl`. It speaks mutual TLS, so every call needs three files — the CA to verify the server, plus a certificate and key to prove who you are. They are on the control-plane node at `/etc/kubernetes/pki/etcd/`, which is a location worth remembering; two lessons from now it is the whole subject.

```bash
CP=netlab-control-plane
etcd() {
  kubectl -n kube-system exec etcd-$CP -- etcdctl \
    --cacert /etc/kubernetes/pki/etcd/ca.crt \
    --cert   /etc/kubernetes/pki/etcd/server.crt \
    --key    /etc/kubernetes/pki/etcd/server.key "$@"
}
```

That is a shell function rather than a variable holding a command, and the difference is not cosmetic: `zsh` — the default shell on macOS — does not split an unquoted variable into separate words, so `$ETCD get ...` would arrive as one impossibly long filename. A function passes `"$@"` through correctly in both shells.

> **Predict first —** what shape will those keys have? You have been typing `kubectl -n <namespace> get <kind> <name>` all of Act V. Guess the key for `db-0`, exactly, then check.

```bash
etcd get /registry --prefix --keys-only \
  | grep -E '^/registry/(pods|services|namespaces|configmaps)/'
```

The filter is there only to keep the answer on one screen — keys come back sorted, and unfiltered the first hundred are internal machinery you have no reason to care about yet. Drop the `grep` when you want to see the whole tree.

The keys read:

```
/registry/configmaps/kube-system/coredns
/registry/namespaces/kube-system
/registry/pods/default/db-0
/registry/services/specs/default/kubernetes
...
```

**`/registry/<kind>/<namespace>/<name>`.** Your `kubectl` arguments, in that order, as a path. This is not an analogy the course is drawing — it is the literal key. The cluster is a filesystem, and this is its directory tree.

Two exceptions in the output above are worth a glance, because they are the kind of thing that only a real listing tells you. A Service is stored under `/registry/services/specs/...`, with a sibling `/registry/services/endpoints/...` — the spec and its endpoints are *separate keys*, which is Act V's Service-and-EndpointSlice split showing through at the storage layer. And nodes are stored under `/registry/minions/`, not `/registry/nodes/` — a fossil of an older name for a worker, still load-bearing in the store years after it vanished from the API.

Count the whole tree, because the number tells you something:

```bash
etcd get /registry --prefix --keys-only | grep -c .
```

A few hundred keys on an idle two-node cluster. That is the *entire* cluster: every Pod, Service, Secret and node, plus a dozen kinds you have not met yet, and nothing else. There is no second source of truth to reconcile against.

Now read one:

```bash
etcd get /registry/pods/default/db-0 | head -c 2000; echo
```

Mostly legible — the name and namespace come first, then a long stretch of bookkeeping, then the image and the node about two thirds of the way in — all wrapped in binary noise, because values are stored as **protobuf**, a compact binary encoding rather than the YAML `kubectl` showed you. (`head -c 2000` is cutting off roughly the last third of a 3 KB record.) That gap is the point: YAML is a rendering. The API server decodes the stored bytes, applies defaults, and serialises whatever format you asked for. `-o yaml` and `-o json` are two views of one record, exactly as `cat /proc/net/dev` was a rendering of counters that are not stored as text anywhere.

### Can you watch a write happen?

Here is the experiment that makes the whole act concrete. `etcdctl` can **watch** a key and print every change to it. So put a watch on one Pod and then change that Pod from the other side.

> **Predict first —** you will watch `/registry/pods/default/db-0` and then `kubectl label pod db-0 tier=primary`. How many writes reach etcd — one, or more than one? And who performs them?

Two terminals. In the first:

```bash
CP=netlab-control-plane
kubectl -n kube-system exec etcd-$CP -- etcdctl \
  --cacert /etc/kubernetes/pki/etcd/ca.crt \
  --cert   /etc/kubernetes/pki/etcd/server.crt \
  --key    /etc/kubernetes/pki/etcd/server.key \
  watch /registry/pods/default/db-0
```

In the second:

```bash
kubectl label pod db-0 tier=primary
```

The watch prints a `PUT` — occasionally two — the instant you press return. You edited an object with `kubectl`; the write landed in a key-value store on another machine; you saw it arrive. **That is the entire control plane in one observation** — `kubectl` talks to the API server, the API server writes etcd, and nothing else in the cluster stores anything.

Leave the watch running and keep going, because the interesting part is what you *didn't* do:

```bash
kubectl delete pod db-0 --wait=false
```

You get one `DELETE` — preceded by **three or four `PUT`s**, all inside about a second. Those extra writes are not yours, and there are more of them than the one thing you asked for. Something noticed the Pod was going away and updated it repeatedly — stamping a deletion time, changing its status, watching the container stop — before the key finally vanished. You asked for none of that. **Something else is watching this store and writing to it.**

You already have the name for that. In [the Gateway API lesson](../act-5-kubernetes/06b-gateway-api.md) you created one object and found two you hadn't written, and called the loop **reconciliation** — watch the object, make the world match it. What you are looking at here is the *other end* of every such loop: the store they all watch, and the store they all write back to. There is no message bus, no queue, no direct call between components. They coordinate by reading and writing this one tree.

<!-- figure -->

```
   ACT I                              ACT VI
   /proc/net/tcp                      /api/v1/namespaces/default/pods/db-0
      |  read()                          |  GET
      v                                  v
   +----------+                       +------------+
   |   VFS    |  one set of ops       | API server |  one set of verbs
   +----+-----+                       +-----+------+  GET/PUT/DELETE/WATCH
        |                                   |
   procfs runs a function             etcd stores the bytes
   over live kernel state             /registry/<kind>/<ns>/<name>
        |                                   |
   nothing is stored                  protobuf; YAML is a rendering

   the file is an INTERFACE, both times.
```

> **Check yourself —** A colleague proposes backing up the cluster by running `kubectl get all -A -o yaml > backup.yaml` on a schedule. What does that capture, and what does it miss?

<details>
<summary>Answer</summary>

It captures a *rendering* of some of the tree, not the tree. Two problems, and the second is the dangerous one.

`kubectl get all` does not mean all — it is a short list of common workload and Service kinds. It omits Secrets, every custom resource behind a CRD, and everything cluster-scoped, along with a dozen kinds you have not met yet. Whole regions of `/registry` are simply absent, and you can prove it in one line: compare `kubectl get all -A -o name | wc -l` against the key count you took above.

More subtly, even for what it does capture it saves the decoded, defaulted, status-carrying view rather than the stored record — resource versions, UIDs and owner references that objects reference each other by. Restoring it re-creates objects that *look* right and are not the same objects.

The thing that would actually capture the cluster is a snapshot of the store itself, which is why the next few lessons are about etcd rather than about YAML.

</details>

### What did that write pass through on the way in?

You watched a `PUT` land in etcd. Nothing so far has said what happened between you pressing return and
that `PUT` appearing — and that gap is where most of *"my apply was rejected and the message means
nothing to me"* lives. The API server is not a thin door onto the store. A write walks a fixed line of
stages, each of which can refuse, and **each refusal has a different signature.** Five requests will
show you five of them.

> **Predict first —** you `curl` the API server with no credential at all, and then with a credential
> that is simply wrong. Same status code both times, or different — and if different, which gets which?

```bash
SRV=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
curl -sk -o /dev/null -w 'no header:  HTTP %{http_code}\n' "$SRV/api/v1/namespaces/default/pods"
curl -sk -o /dev/null -w 'bad token:  HTTP %{http_code}\n' \
     -H 'Authorization: Bearer not-a-real-token' "$SRV/api/v1/namespaces/default/pods"
```

```
no header:  HTTP 403
bad token:  HTTP 401
```

**That is the opposite way round from the guess almost everyone makes.** Read the bodies and the reason
appears:

```bash
curl -sk "$SRV/api/v1/namespaces/default/pods" | grep '"message"'
curl -sk -H 'Authorization: Bearer not-a-real-token' \
     "$SRV/api/v1/namespaces/default/pods" | grep '"message"'
```

```
  "message": "pods is forbidden: User \"system:anonymous\" cannot list resource \"pods\" ...",
  "message": "Unauthorized",
```

Presenting no credential is not the absence of an identity — it **is** an identity, called
`system:anonymous`. That request was named, and then refused on what the name is allowed to do. The bad
token never got a name at all. Which fixes the two words for good:

- **401** — *I could not work out who you are.* No user in the message, because there is no user.
- **403** — *I know exactly who you are, and no.* The message names the **user, the verb and the
  resource**, which is what makes it the more useful of the two errors, and the one you can act on.

Two stages, in that order. The third refusal is the one that looks like the second and is not:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: typo}
spec:
  contaners: [{name: c, image: busybox:1.36}]
EOF
```

```
Error from server (BadRequest): error when creating "STDIN": Pod in version "v1" cannot be handled
as a Pod: strict decoding error: unknown field "spec.contaners"
```

`BadRequest`, not `Forbidden`. Nobody refused you — the server could not turn your bytes into a Pod,
because `contaners` is not a field and it declines to silently drop what it does not recognise. That is
a **decode**, and it happens *after* the server knows who you are and *before* anything inspects the
object's meaning: there is nothing yet to inspect.

Which is exactly what makes the fourth one worth seeing next to it. Spell the field correctly and put a
nonsense *value* in it:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: badport}
spec:
  containers: [{name: c, image: busybox:1.36, ports: [{containerPort: 99999}]}]
EOF
```

```
The Pod "badport" is invalid: spec.containers[0].ports[0].containerPort: Invalid value: 99999:
must be between 1 and 65535, inclusive
```

`422 Unprocessable Entity`, and the wording changed from *unknown field* to **is invalid**. The decoder
was satisfied — `containerPort` is a real field holding a real integer — and then something further in
asked whether the object *means* anything, and it does not. Two errors, two stages, one letter of
difference in the manifest. Learn the three phrasings and you can place a failure without reading the
manifest at all: `is forbidden` (someone said no), `unknown field` (it did not parse), `is invalid`
(it parsed and is nonsense).

The fifth is not a refusal, which is why it is the one that changes how you read every object you own:

```bash
kubectl run w0 --image=busybox:1.36 --restart=Never --command -- sh -c 'echo hi'
sleep 3
kubectl get pod w0 -o jsonpath='serviceAccount: {.spec.serviceAccountName}{"\n"}volume: {.spec.volumes[0].name}{"\n"}'
```

```
serviceAccount: default
volume: kube-api-access-qwm2w
```

**Your command mentioned neither.** The object in etcd is not the object you sent: something on the way
in assigned it an account and mounted a credential into it. You installed nothing, and there was no way
to opt out, so this has happened to every Pod you have created since Act V. Objects are *edited* in
transit, not merely accepted or rejected — which means `kubectl get -o yaml` shows you the stored
result of a negotiation, and diffing it against your manifest will show differences that are nobody's
bug.

Line those five up and the pipeline draws itself. Every write you make, in order:

<!-- figure -->

```
   your request
     |
     v  AUTHENTICATION      who are you?            refuses: 401, no user named
     v  AUTHORIZATION       may you do this?        refuses: 403, names user+verb+resource
     v  DECODE (strict)     are these real fields?  refuses: 400, "unknown field ..."
     v  MUTATING admission  edit the object         the ServiceAccount token, above
     v  OBJECT validation   does it mean anything?  refuses: 422, "... is invalid"
     v  VALIDATING admission may it exist?          refuses: 403, names a policy
     |
     v  PERSISTED to etcd   the PUT you watched arrive
```

Read it as a filter, not a menu: a request that dies at stage two never reaches stage three, so **the
error you get tells you how far in you got.** A 401 means nothing about your YAML. A 403 that names a
user is RBAC; a 403 that names a policy is admission, and those are two different files to go and edit.
A `BadRequest` about a field means your permissions are fine and your typing is not. That distinction is
most of the debugging.

Two of the six stages are the interesting ones, because they are the only two the *cluster's operator*
gets to put rules into: the mutating stage, which you just watched write a volume you never asked for,
and the validating stage, which so far has refused you nothing. Everything Kubernetes calls **admission
control** lives in those two rows, and [Act X](../act-10-cluster-security/04-deciding-before-it-exists.md)
is where you write your own and find out which of the two runs first — a question this diagram
deliberately does not answer, because the order is not the one most people assume.

**Clean up the two objects this section left:**

```bash
kubectl delete pod w0 --wait=false
```

(The `typo` Pod was never created — that was the point.)

### What does this cost you?

One store holds everything, which buys the coordination you just watched and hands you a single point of failure in exchange. Every component in the cluster is disposable except this one.

That is not a hypothetical. Three facts you now have, taken together, should make you uneasy: the whole cluster is a few hundred keys; those keys are reachable by anyone holding three files from `/etc/kubernetes/pki/etcd/`; and you just read one with a shell command. If a Secret is in there, it is in there the way that Pod was.

**Cleanup** — the two `delete` commands above already did it. Confirm nothing is left:

```bash
kubectl get pods
```

> **You understand this when you can** explain why a Pod cannot be found on the disk of the node
> that runs it, and what `kubectl get pod` is doing instead; say what the API server computes its
> answers *from*, and why YAML is a rendering rather than the record; say why an `etcdctl watch`
> shows writes you did not perform; and, given a rejected `apply`, name the stage that rejected it
> from the wording alone.

**Which raises:** those extra writes came from somewhere. Something is watching this store and acting on what it sees — and if that is how a Pod gets a deletion stamp, it may also be how a Pod gets *scheduled to a node at all*. Before you can watch one of those watchers stop, you need to know where they run. You have never seen the API server as a *process*.

---

↑ **[Act VI overview](README.md)** · Next: **[Static pods — where the control plane lives](02-static-pods.md)** →
