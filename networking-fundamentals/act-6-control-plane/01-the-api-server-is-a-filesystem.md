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

### What does this cost you?

One store holds everything, which buys the coordination you just watched and hands you a single point of failure in exchange. Every component in the cluster is disposable except this one.

That is not a hypothetical. Three facts you now have, taken together, should make you uneasy: the whole cluster is a few hundred keys; those keys are reachable by anyone holding three files from `/etc/kubernetes/pki/etcd/`; and you just read one with a shell command. If a Secret is in there, it is in there the way that Pod was.

**Cleanup** — the `kubectl delete pod db-0` above already did it. Confirm nothing is left:

```bash
kubectl get pods
```

> **You understand this when you can** explain why a Pod cannot be found on the disk of the node that runs it, and what `kubectl get pod` is doing instead — a `GET` on a path, against a tree whose keys are literally `/registry/<kind>/<namespace>/<name>`; say what the API server computes its answers *from*, and why YAML is a rendering rather than the record; and describe what an `etcdctl watch` shows you when you label a Pod, including why writes you did not perform appear alongside the one you did.

**Which raises:** those extra writes came from somewhere. Something is watching this store and acting on what it sees — and if that is how a Pod gets a deletion stamp, it may also be how a Pod gets *scheduled to a node at all*. Before you can watch one of those watchers stop, you need to know where they run. You have never seen the API server as a *process*.

---

↑ **[Act VI overview](README.md)** · Next: **[Static pods — where the control plane lives](02-static-pods.md)** →
