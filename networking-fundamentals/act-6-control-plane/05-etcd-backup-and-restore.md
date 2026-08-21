# Losing the cluster, and getting it back

Four lessons ago you counted the keys. A few hundred, in one store, on one node, in a directory you can `ls`. Since then you have watched every other component turn out to be replaceable: delete a static Pod's record and the kubelet files it again; stop the controller manager and restart it, and it converges from nothing but the current state of the store. Nothing anywhere holds a queue of work.

Which is a lovely property right up until you notice what it rests on. Every one of those components recovers *by reading the store*. So there is exactly one thing in this architecture that cannot be recovered by reading the store, and you know where it lives.

Let us find out how bad it is.

### How much of the cluster is in that directory?

> **Predict first —** you have a two-node cluster with a Deployment running on it. If you deleted `/var/lib/etcd` on the control-plane node and restarted etcd, what would you expect to still be true afterwards? Take a moment on this one; commit to an answer for each of: your Deployment, the worker node's membership, the running containers, and your ability to run `kubectl` at all.

Build something worth losing first:

```bash
kubectl create namespace precious
kubectl create deployment payments --image=hashicorp/http-echo --replicas=2 \
  -n precious -- /http-echo -text=payments -listen=:5678
kubectl create secret generic api-key -n precious --from-literal=key=hunter2
kubectl wait --for=condition=Available deployment/payments -n precious --timeout=90s
kubectl get all,secret -n precious
```

Nothing exotic — a namespace, a Deployment, two Pods and a Secret. Now take the backup, and note that this is the first command in the act whose *purpose* is to be run before you need it.

```bash
docker exec netlab-control-plane etcdctl \
  --cacert /etc/kubernetes/pki/etcd/ca.crt \
  --cert   /etc/kubernetes/pki/etcd/server.crt \
  --key    /etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/lib/etcd-backup.db
```

Three cert flags, exactly as in the first lesson of this act — the same mutual TLS, because a backup is just another authenticated read. If you get `Error: rpc error ... transport is closing`, you have the flags wrong, not the cluster broken.

One of those flags should look wrong to you now, and it is worth a moment because the last lesson is what makes it visible. You are presenting **`server.crt`** — etcd's *serving* certificate — as a client credential. Lesson 04 taught you that these are different jobs, and even showed you the file whose name says it is the client: `apiserver-etcd-client.crt`. Both work here, and the reason is that etcd's CA signs certificates fit for both roles, so `server.crt` is usable as a client cert as well. It is a convenience, not a principle — using it means the audit trail cannot distinguish your backup from etcd talking to itself, which is exactly the kind of thing that matters when you are trying to work out who read a Secret.

And look at what a snapshot *is*:

```bash
docker exec netlab-control-plane ls -lh /var/lib/etcd-backup.db
docker exec netlab-control-plane etcdutl --write-out=table \
  snapshot status /var/lib/etcd-backup.db
```

A single file of a few megabytes, and a table giving you a hash, a revision — etcd's internal counter of how many writes it has ever accepted — and a **total key count**.

That last column is the whole cluster in one integer, so compare it against a number you already have. In the first lesson of this act you counted the live tree:

```bash
etcd get /registry --prefix --keys-only | grep -c .
```

The two should be in the same neighbourhood, with the snapshot slightly the larger of the two because etcd stores keys of its own alongside `/registry`. That comparison is the only honest verification a backup has, and it is worth being pedantic about: a file that exists proves nothing at all, and a file whose key count is roughly the size of your cluster proves quite a lot.

Now look again at the two commands you just ran, because the tool changed and the reason is the whole lesson in miniature. `snapshot save` is **`etcdctl`** and needed three certificates. `snapshot status` is **`etcdutl`** and needed none.

That is not an inconsistency, it is the distinction drawn as a boundary between two binaries. `etcdctl` is a *client*: everything it does, it does by making an authenticated request to a running etcd. `etcdutl` is a *utility*: everything it does, it does to files on disk, with no server involved and nothing to authenticate to. Saving a snapshot requires a live cluster to read from, so it is a client operation. Inspecting one requires only the file.

The etcd project used to put both under `etcdctl`, and if you have followed a guide that says `etcdctl snapshot status`, that is why: those subcommands were deprecated for years and **removed in etcd 3.6**, which is what your cluster is running. If a command in this lesson fails with `unknown command`, check which of the two binaries you typed — and check your etcd version, because on an older cluster the `etcdctl` spellings still work:

```bash
docker exec netlab-control-plane etcdctl version
```

### Now lose it

Copy the snapshot somewhere outside the node before you break anything, because a backup that lives only on the machine you are about to destroy is not a backup:

```bash
docker cp netlab-control-plane:/var/lib/etcd-backup.db ./etcd-backup.db
ls -lh etcd-backup.db
```

Now delete something you care about, which stands in for whatever real accident you would rather not rehearse:

```bash
kubectl delete namespace precious
kubectl get ns precious                 # NotFound. the Pods are gone too.
```

That deletion is as permanent as anything in this course gets. There is no undo verb in the API — you have watched the `DELETE` land in etcd yourself. The Secret is gone, the Deployment is gone, and the reconciliation loops did exactly as they were told.

### What does a restore actually do?

Here is the part that catches people, and it follows from the last three lessons rather than from anything about etcd.

> **Predict first —** you have the snapshot. `etcdctl snapshot restore` will presumably put the data back. But *where* does it put it, and what is reading `/var/lib/etcd` at this very moment? What has to be true before a restore can possibly work?

A restore does not load data into a running etcd. It **writes a fresh data directory from the file**, offline. Which means the process holding that directory open has to be gone first — and you know how to stop it, because it is a static Pod.

So the shape of the operation is: stop the control plane, restore to a new directory, point etcd at it, start the control plane. Four steps, and the second is the only one that is about etcd at all.

Stop it. Move all four manifests, not just etcd's — the API server would otherwise spend the next minute writing to a store that is being replaced underneath it:

```bash
docker exec netlab-control-plane sh -c 'mkdir -p /tmp/held && mv /etc/kubernetes/manifests/*.yaml /tmp/held/'
sleep 20
docker exec netlab-control-plane crictl ps --state Running | grep -cE 'etcd|apiserver'   # 0
kubectl get nodes                                                                        # cannot connect
```

`kubectl` is dead, and from here to the end of this lesson every command runs on the node. This is the situation the last lesson prepared you for; it is worth noticing that you are not alarmed by it.

Restore into a *new* directory rather than over the old one, so that a failed restore costs you nothing:

```bash
docker exec netlab-control-plane etcdutl \
  snapshot restore /var/lib/etcd-backup.db \
  --data-dir /var/lib/etcd-restored
docker exec netlab-control-plane ls /var/lib/etcd-restored/member/
```

`etcdutl` again, and now the reason it *has* to be the utility rather than the client is unavoidable: there is no etcd running to send this to. A restore is a file-to-file operation by necessity, not by preference.

`snap` and `wal` — the same two directories you saw inside `/var/lib/etcd` in the static-pods lesson. You have manufactured a fresh, complete etcd data directory from a single file, with no cluster running and no certificates presented.

Now the step that is not about etcd. The manifest you moved to `/tmp/held/etcd.yaml` mounts `/var/lib/etcd` as a `hostPath`, and your data is in `/var/lib/etcd-restored`. Two ways to reconcile that; take the one that leaves the old data recoverable:

```bash
docker exec netlab-control-plane sh -c '
  mv /var/lib/etcd /var/lib/etcd-broken &&
  mv /var/lib/etcd-restored /var/lib/etcd'
```

The alternative — editing `hostPath` in the manifest to point at the new directory — works identically and is arguably clearer, but leaves you with a control plane whose manifests no longer match a stock cluster's. Moving the directory keeps the manifest canonical.

Bring it back:

```bash
docker exec netlab-control-plane sh -c 'mv /tmp/held/*.yaml /etc/kubernetes/manifests/'
sleep 45
kubectl get nodes
kubectl get all,secret -n precious
```

The namespace is back. The Deployment is back. **The Secret is back, with the same value** — which is a fact worth sitting with for one sentence, because you have just demonstrated that whoever holds a snapshot file holds every Secret in the cluster, in a form that needs no cluster to read.

Give it a minute if the first `kubectl get nodes` is slow or the worker shows `NotReady`. Four components are starting at once and the controller manager has a leader election to win before it reports anything, exactly as in the reconciliation lesson.

### What did you *not* get back?

This is the question that separates knowing the commands from understanding the operation, and the answer is a shape rather than a list.

A snapshot is a *point in time*. Everything written to the cluster between the snapshot and the disaster is gone — that is obvious. What is less obvious is that the **world did not roll back with it.** Consider what you now have: a store that believes the cluster looked as it did before, and nodes whose kubelets are running containers as they were a moment ago. Anything created after the snapshot is still running on some node while no longer existing in the store, and the reconciliation loops will notice and remove it — which is correct, and is also the store's version of reality overwriting a running system's.

That is the honest cost of this technique. A restore is not a rewind; it is an **assertion** about what the cluster is, made to components that will then make it true.

> **Check yourself —** Your snapshot is four hours old. In those four hours a colleague added a worker node to the cluster, and it has Pods running on it. You restore the snapshot. What is the state of that node, and what would you have to do about it?

<details>
<summary>Answer</summary>

The node has vanished from the cluster's point of view and has no idea.

Node membership is an object in the store like everything else — `/registry/minions/<name>`, as you saw in the first lesson of this act. It was created when that node joined, and it is not in a snapshot taken before it joined. So after the restore, the API server has no record of the node, `kubectl get nodes` will not list it, and nothing will schedule to it.

Meanwhile the node itself is fine and completely unaware. Its kubelet is still running, still holds the client certificate it was issued (a file on its disk — the last lesson's point), and is still running the containers it was last told to run. It will keep trying to report to an API server that does not believe it exists.

The fix is to make it join again — which is `kubeadm join`, with a fresh token, after clearing its old state. And the general form of the lesson is the one worth keeping: **a restore reverts the cluster's beliefs, not the world.** Anything whose existence was recorded after the snapshot has to be re-created, and anything running that the store no longer knows about will be reconciled away. Which is also the argument for taking snapshots on a schedule measured in minutes rather than hours.

</details>

<!-- figure -->

```
   TWO BINARIES, split on exactly one question: does it need a server?
     etcdctl = CLIENT   talks to a running etcd, so needs --cacert/--cert/--key
     etcdutl = UTILITY  operates on files, so needs nothing   (3.6 moved these here)

   BACKUP
     etcdctl --cacert/--cert/--key snapshot save FILE      <- live read, authenticated
     etcdutl snapshot status FILE --write-out=table        <- reads the file
                                                        verify by TOTAL KEYS, not by ls

   RESTORE  (cluster STOPPED. this is the part people miss)
     1. mv /etc/kubernetes/manifests/*.yaml  ->  /tmp/held/      all four, not just etcd
             |                                                   kubectl is now dead
             v
     2. etcdutl snapshot restore FILE --data-dir /var/lib/etcd-restored
             |                                       writes a NEW dir, offline, no certs
             v
     3. make the hostPath in etcd.yaml point at the data
             mv /var/lib/etcd -> etcd-broken ; mv etcd-restored -> etcd
             v
     4. mv /tmp/held/*.yaml -> /etc/kubernetes/manifests/       kubelet starts them

   WHAT YOU RESTORED: the store's beliefs, as of the snapshot. Secrets included, in
   plaintext, from a file that needs no cluster to read.
   WHAT YOU DID NOT: the world. Nodes that joined after the snapshot are strangers;
   objects created after it are reconciled away.
```

**Cleanup** — put the cluster back to a state the next lesson can use:

```bash
kubectl delete namespace precious
docker exec netlab-control-plane sh -c 'rm -rf /var/lib/etcd-broken /var/lib/etcd-backup.db'
rm -f etcd-backup.db
docker exec netlab-control-plane ls /etc/kubernetes/manifests/   # all four, and /tmp/held empty
```

> **You understand this when you can** take a snapshot and verify it by something other than the file existing, and say from the command alone which of `etcdctl` and `etcdutl` a given etcd operation needs and why; explain why a restore requires the control plane to be stopped and why moving all four manifests is safer than moving only etcd's; say what `snapshot restore` produces and the one step afterwards that is about `hostPath` rather than about etcd; and describe what a restore does *not* undo, using a node that joined after the snapshot as the example.

**Which raises:** you have now stopped the control plane deliberately, twice, and put it back. Both times every component came back at the same version it left at. But a cluster that lives long enough gets upgraded — and an upgrade is precisely the case where the components come back *different*, one at a time, while the cluster keeps serving. What is allowed to be out of step with what, and for how long?

---

← Prev: **[The cluster's own PKI](04-the-clusters-own-pki.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Upgrades, and what is allowed to be out of step](06-upgrades-and-version-skew.md)** →
