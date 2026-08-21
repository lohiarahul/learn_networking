# Losing the cluster, and getting it back

Four lessons ago you counted the keys. A few hundred, in one store, on one node, in a directory you can `ls`. Since then every other component has turned out to be replaceable: delete a static Pod's record and the kubelet files it again; stop the controller manager and restart it, and it converges from nothing but the current state of the store.

Which is a lovely property right up until you notice what it rests on. Every one of those components recovers *by reading the store*. So there is exactly one thing here that cannot be recovered by reading the store, and lesson 02 told you where it lives: a `hostPath` at `/var/lib/etcd`, on one node's real disk.

Time to find out how bad it is.

> **Predict first —** you have a two-node cluster with work running on it. You delete `/var/lib/etcd` on the control-plane node and let the control plane start again. Commit to an answer for each of these four before you go on, because you are going to do it: what happens to **your Deployment**, to the **worker node's membership** of the cluster, to the **containers currently running**, and to your ability to **run `kubectl` at all**?

### Something worth losing

```bash
kubectl create namespace precious
kubectl create deployment payments --image=hashicorp/http-echo --replicas=2 \
  -n precious -- /http-echo -text=payments -listen=:5678
kubectl create secret generic api-key -n precious --from-literal=key=hunter2
kubectl wait --for=condition=Available deployment/payments -n precious --timeout=90s
kubectl get all,secret -n precious
```

A namespace, a Deployment, two Pods, a Secret. Now take a snapshot — the first command in this act whose purpose is to be run *before* you need it.

```bash
CP=netlab-control-plane
kubectl -n kube-system exec etcd-$CP -- etcdctl \
  --cacert /etc/kubernetes/pki/etcd/ca.crt \
  --cert   /etc/kubernetes/pki/etcd/server.crt \
  --key    /etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/lib/etcd/etcd-backup.db
```

Three cert flags, exactly as in the first lesson of this act — the same mutual TLS, because a snapshot is just another authenticated read.

Two details in that command are doing more work than they look like.

**The path matters, and getting it wrong fails silently.** The snapshot must land inside `/var/lib/etcd/`, because that is the `hostPath` — the one directory in that container that is really the node's disk. Write it to `/var/lib/etcd-backup.db` instead and `etcdctl` reports `Snapshot saved` quite happily, into the container's own temporary filesystem, where it ceases to exist the next time the container restarts. A backup that reports success and is not there is worse than no backup.

**And one of those flags should look wrong to you now.** You are presenting `server.crt` — etcd's *serving* certificate — as a client credential, when lesson 04 showed you the file whose name says it is the client, `apiserver-etcd-client.crt`. It works because etcd's CA signs certificates fit for both roles. It is a convenience, not a principle: using it means nothing downstream can distinguish your backup from etcd talking to itself, which matters on the day you need to know who read a Secret.

### Get it off the machine, and check it

A backup that lives only on the machine you are about to destroy is not a backup:

```bash
docker cp $CP:/var/lib/etcd/etcd-backup.db ./etcd-backup.db
ls -lh etcd-backup.db
```

Now verify it, and notice that you cannot use the tool you just used:

```bash
docker run --rm -v "$PWD:/w" registry.k8s.io/etcd:3.6.8-0 \
  etcdutl --write-out=table snapshot status /w/etcd-backup.db
```

```
+----------+----------+------------+------------+---------+
|   HASH   | REVISION | TOTAL KEYS | TOTAL SIZE | VERSION |
+----------+----------+------------+------------+---------+
| 368663ff |     3892 |        578 |     4.9 MB |   3.6.0 |
+----------+----------+------------+------------+---------+
```

A hash, a revision — etcd's running count of every write it has ever accepted — and a **total key count**. That last column is the whole cluster as one integer, so compare it against a number you already know how to get:

```bash
kubectl -n kube-system exec etcd-$CP -- etcdctl \
  --cacert /etc/kubernetes/pki/etcd/ca.crt \
  --cert   /etc/kubernetes/pki/etcd/server.crt \
  --key    /etc/kubernetes/pki/etcd/server.key \
  get /registry --prefix --keys-only | grep -c .
```

The two should agree within one or two — the snapshot counts a handful of etcd's own bookkeeping keys alongside `/registry`. **That comparison is the only honest verification a backup has.** A file that exists proves nothing; a file whose key count is the size of your cluster proves a great deal.

### Two binaries, and neither of them is on the node

That verification command needed a different tool and a different machine, and both facts are worth a moment.

`etcdctl` is a **client**: everything it does, it does by making an authenticated request to a running etcd. `etcdutl` is a **utility**: everything it does, it does to files on disk, with no server involved and nothing to authenticate to. Saving a snapshot needs a live cluster to read from, so it is a client operation. Inspecting one needs only the file. So does restoring one.

The etcd project used to put both under `etcdctl`; those subcommands were deprecated for years and **removed in 3.6**. Which spelling works depends on your etcd version, and the removal is not polite about it — `etcdctl snapshot status` on 3.6 prints the help text and **exits 0**, doing nothing at all, which is a far nastier failure than an error would be. If a snapshot command appears to succeed and produces no table, that is what happened.

Now the more interesting fact. Go looking for either binary on the node:

```bash
docker exec $CP sh -c 'ls /usr/local/bin/ | grep etcd; echo "exit: $?"'
```

**Nothing.** `crictl` and `ctr` are there; no `etcdctl`, no `etcdutl`. The tools for the cluster's only stateful component are not installed on the node that runs it — they ship *inside the etcd image*, which is why the commands above reach them two different ways: `kubectl exec` into the running etcd Pod while etcd is up, and `docker run` on your own machine, against a copied file, when it is not.

That second route is the one that matters, and it is worth seeing why it has to exist. In a moment you will restore a snapshot with etcd **stopped** — so `kubectl exec` is impossible, and the binary is not on the node. Your own Docker, running the same image against a file, needs neither.

### Read the Secret out of the file

Before going further, do something with that copied file that ought to be uncomfortable.

```bash
LC_ALL=C grep -a -o -E '.{0,20}hunter2.{0,20}' etcd-backup.db
```

```
keyhunter2Opaque
```

The field name, the value, and the Secret's type, sitting together in a file on your laptop. No cluster, no certificates, no etcd, no permissions.

And note what it is *not*:

```bash
LC_ALL=C grep -a -c 'aHVudGVyMg' etcd-backup.db      # 0
```

Zero. Act V told you a Secret is only base64 rather than encrypted, and that was generous — `aHVudGVyMg` is what base64 of `hunter2` looks like, and it does not appear. In the store the value is **plaintext**. Base64 is a thing the API server does on the way out to you, not a thing the store does.

So the sentence to carry out of this lesson before you have even restored anything: **whoever holds a snapshot file holds every Secret in the cluster, in a form that needs nothing to read.** Where you keep this file is a security decision of the same weight as who has a `kubeconfig`.

### Now lose it

One more object, created *after* the snapshot, so that you can tell what a restore does and does not do:

```bash
kubectl create deployment after-snap --image=hashicorp/http-echo -n precious \
  -- /http-echo -text=after-snap -listen=:5678
kubectl wait --for=condition=Available deployment/after-snap -n precious --timeout=90s
kubectl get pods -n precious -o wide          # note which node, and the Pod IP
```

That one exists in the world but not in your backup. Remember its IP.

Now destroy the store. Stop the control plane first — all four manifests, because an API server writing into a store that is being replaced underneath it is nobody's idea of a good time:

```bash
docker exec $CP sh -c 'mkdir -p /tmp/held && mv /etc/kubernetes/manifests/*.yaml /tmp/held/'
sleep 35
docker exec $CP sh -c 'mv /var/lib/etcd /var/lib/etcd-gone'
docker exec $CP sh -c 'mv /tmp/held/*.yaml /etc/kubernetes/manifests/'
sleep 20
```

The `sleep 35` is not padding. etcd's container goes within about ten seconds; the API server's takes closer to thirty, and it is the one you must not race.

Then the control plane starts again — and it starts *fine*. The manifest's `hostPath` is declared `DirectoryOrCreate`, so `/var/lib/etcd` is recreated empty, and etcd's own flags tell it to bootstrap a brand-new single-member store. Within about ten seconds you have a completely healthy, completely empty cluster.

Now collect your four predictions.

```bash
kubectl get nodes
```

```
Error from server (Forbidden): nodes is forbidden: User "kubernetes-admin"
cannot list resource "nodes" in API group "" at the cluster scope
```

**Forbidden — not "unable to connect".** Sit with that, because it is the sharpest thing in this act and lesson 04 built it for you without either of us knowing.

```bash
kubectl auth whoami
```

That *works*, and reports you as `kubernetes-admin` in group `kubeadm:cluster-admins`. Your authentication is perfect. Of course it is: your identity is a certificate, signed by a CA that lives in `/etc/kubernetes/pki/` on the node's disk, and you did not touch either. **The thing you destroyed was the `ClusterRoleBinding`** — the object lesson 04 had you read, the one saying that your group may do anything. It was in the store. It is not any more.

So the API server knows exactly who you are and will not let you list a node.

There is a credential that still works, and by now you can predict which:

```bash
docker exec $CP kubectl --kubeconfig /etc/kubernetes/super-admin.conf get nodes
docker exec $CP kubectl --kubeconfig /etc/kubernetes/super-admin.conf get ns
```

`O=system:masters` — the group lesson 04 described as wired into the API server rather than into an object in the store. Here is what that buys, and it is not a footnote: **the break-glass credential works precisely because it does not depend on anything you can delete.** Everything you have read about `super-admin.conf` being for emergencies was describing this emergency.

Use it for the rest of the diagnosis, because your own credential can no longer see anything:

```bash
docker exec $CP kubectl --kubeconfig /etc/kubernetes/super-admin.conf get nodes
docker exec $CP kubectl --kubeconfig /etc/kubernetes/super-admin.conf get pods -A
docker exec $CP crictl ps
```

Take those three in order, because together they are the answer to the whole prediction.

**`get nodes` returns `No resources found`.** Both nodes are gone. A Node is an object at `/registry/minions/<name>`, and that region of the tree no longer exists. Wait as long as you like — they do not come back on their own, and *why* is worth knowing: a running kubelet does not periodically re-register. It registered once, at startup, and everything it does now assumes the Node object exists. Its log fills with `Error updating node status ... nodes "netlab-worker" not found` — it is trying to *update* a record that is missing, and it has no code path for "then create it."

**`get pods -A` returns `No resources found` too.** Four namespaces were recreated by the API server itself — `default`, `kube-system`, `kube-public`, `kube-node-lease` — and they are empty. Your `precious` namespace is gone, and so is `local-path-storage`, which came with `kind`.

**And `crictl ps` lists nine running containers.** Including `payments`, including `after-snap`, including all four control-plane components.

```bash
docker exec netlab-worker crictl ps
curl -s http://<the after-snap Pod IP>:5678       # from the worker: still answers
```

Nothing died. Every container the cluster was running before you deleted the store is still running, still serving traffic, and the kubelets have not killed any of them. Which answers your third prediction in the way you should find most unsettling: **the cluster's beliefs and the world have come completely apart, and the world is the half that is still working.**

Note also what did *not* happen: the four control-plane components are running, and yet `kubectl get pods -n kube-system` is empty. In lesson 02 you learned the kubelet registers its static Pods into the API server so you can see them. It cannot do that now — the API server refuses the write, because the node those Pods claim to be on does not exist as far as it knows.

### Getting it back

> **Predict first —** you have the snapshot on your laptop. Before reading on: does `etcdutl snapshot restore` write into the running etcd, or somewhere else? And given the answer, what has to be true of the cluster before you can run it?

Restore on your own machine, into a new directory, and copy the result in. Do this *first*, while the cluster is still up, because a fresh directory harms nothing and it keeps the outage short:

```bash
docker run --rm -v "$PWD:/w" registry.k8s.io/etcd:3.6.8-0 \
  etcdutl snapshot restore /w/etcd-backup.db --data-dir /w/etcd-restored
ls etcd-restored/member/
docker cp ./etcd-restored $CP:/var/lib/etcd-restored
```

`snap` and `wal` — the same two directories you saw inside `/var/lib/etcd` in the static-pods lesson. You have manufactured a complete etcd data directory from a single file, with no cluster running, no certificates, and no etcd server anywhere in the picture. (If you need to run that restore twice, delete `./etcd-restored` first; `etcdutl` refuses to write into a directory that is not empty.)

Which answers the prediction. A restore does not load data into a running etcd — it **writes a fresh data directory from the file**, offline. And note what enforces that: nothing does. The only guard is that non-empty-directory check. `etcdutl` has no idea whether etcd is running, and would cheerfully build you a data directory while your cluster carried on writing to a different one. **Stopping the control plane is a correctness requirement you impose on yourself, not a rule the tool enforces** — which is exactly the kind of thing to know before a bad afternoon.

So stop it, swap the directory, start it:

```bash
docker exec $CP sh -c 'mv /etc/kubernetes/manifests/*.yaml /tmp/held/'
sleep 35
docker exec $CP sh -c 'mv /var/lib/etcd /var/lib/etcd-empty && mv /var/lib/etcd-restored /var/lib/etcd'
docker exec $CP sh -c 'mv /tmp/held/*.yaml /etc/kubernetes/manifests/'
until kubectl get ns 2>/dev/null; do sleep 2; done
```

Moving the old directory aside rather than deleting it is the habit worth keeping: a failed restore then costs you nothing. The alternative — editing `hostPath` in `etcd.yaml` to point at the new directory — works identically, but leaves you with a control plane whose manifests no longer match a stock cluster's.

That `until` loop returns almost immediately once the manifests are back. And your own `kubectl` is answering again, which is the first thing to notice: the `ClusterRoleBinding` came back with everything else.

```bash
kubectl get nodes
kubectl get all,secret -n precious
kubectl get secret api-key -n precious -o jsonpath='{.data.key}' | base64 -d; echo
```

Both nodes `Ready`. The namespace, the Deployment, the Pods, the Secret — and `hunter2`, the same value, because you restored the bytes that held it.

### What you did not get back

```bash
kubectl get deployment after-snap -n precious
```

`Error from server (NotFound)`. Correct: it was created after the snapshot, so it is not in the snapshot, and the store now believes it never existed. That is point-in-time semantics working exactly as advertised, and it is the part everyone expects.

Here is the part that is not:

```bash
docker exec netlab-worker crictl ps --name after-snap
curl -s http://<the after-snap Pod IP>:5678
```

**It is still running. It is still answering.** A workload with no Deployment, no ReplicaSet and no Pod anywhere in the cluster, serving HTTP quite happily, and it will keep doing so indefinitely — not for seconds while something notices, but for as long as you leave it.

You might expect lesson 03's reconciliation loops to sweep it away, and the reason they do not is worth the whole lesson. Every watch in Kubernetes is a stream of changes *since a revision*, and a restore moves the store's revision **backwards**. The kubelet is watching for changes after a revision that is now in the future, so no change ever arrives, and it goes on acting from the picture it had in memory before you started. Nothing is broken; nothing has noticed there is anything to notice.

Force it to look again, and the reckoning is immediate:

```bash
docker exec netlab-worker systemctl restart kubelet
sleep 15
docker exec netlab-worker crictl ps --name after-snap     # gone
kubectl get pods -n precious                              # payments, untouched
```

A restarted kubelet asks for a fresh list, finds a running container with no Pod behind it, and reaps it in a few seconds — while `payments`, which *is* in the restored store, is not disturbed at all.

Which is the honest shape of this technique. **A restore is not a rewind. It is an assertion about what the cluster is** — and the components will make it true, but only once they have looked. Between the assertion and the looking, you have a cluster whose beliefs and reality disagree, and you have just seen that gap serve traffic.

So the last step of any restore is to make the nodes look again. That is also the fix for the missing Node objects: the same restart re-registers a node in under a second, because its credential was a file on its own disk the entire time.

> **Check yourself —** Your snapshot is four hours old. In those four hours a colleague added a worker node, and it has Pods on it. You restore the snapshot. What is the state of that node, and what do you do about it?

<details>
<summary>Answer</summary>

The node has vanished from the cluster's point of view and has no idea.

Its Node object was created when it joined and is not in a snapshot taken before it joined, so after the restore `get nodes` will not list it and nothing will schedule to it. Meanwhile the node itself is entirely fine: its kubelet is running, it still holds the client certificate it was issued — a file on its own disk, which no snapshot touches — and it is still running the containers it was last told to run, unsupervised.

**Restart its kubelet.** Registration happens once at kubelet startup, so a running kubelet will keep trying to *update* a record that is not there and never think to create it. A restart makes it register again, and because its credential never went anywhere, that succeeds immediately. The same restart forces the fresh Pod list that reaps whatever it is running that the store no longer knows about. You would not use `kubeadm join` here — the node's credentials are intact, and joining is for a node that has none.

The general rule: **a restore reverts the cluster's beliefs, not the world.** Anything recorded after the snapshot has to be re-created, anything running that the store no longer knows about keeps running until something looks, and *making things look* is a step you have to take. Which is also the argument for snapshots on a schedule measured in minutes.

</details>

<!-- figure -->

```
   TWO BINARIES, split on one question: does it need a running server?
     etcdctl = CLIENT   authenticated request to a live etcd -> --cacert/--cert/--key
     etcdutl = UTILITY  operates on files -> needs nothing   (3.6 moved these here)
   NEITHER IS ON THE NODE. they ship inside the etcd image.
     etcd up   -> kubectl -n kube-system exec etcd-<cp> -- etcdctl ...
     etcd down -> docker run --rm -v "$PWD:/w" <etcd image> etcdutl ...

   BACKUP
     snapshot save  ->  MUST land in /var/lib/etcd/ (the hostPath).
                        anywhere else "succeeds" into a dying container.
     verify by TOTAL KEYS vs your own /registry count. not by ls.
     grep -a hunter2 backup.db  ->  PLAINTEXT. not base64. no cluster needed.

   LOSE THE STORE  (mv /var/lib/etcd aside, restart the control plane)
     etcd bootstraps EMPTY and healthy in ~10s. so:
       kubectl            -> FORBIDDEN, not disconnected. authn is a file on disk;
                             the ClusterRoleBinding that authorised you was in the store.
       super-admin.conf   -> WORKS. O=system:masters is wired into the API server,
                             not into an object you can delete. this is the emergency.
       get nodes          -> empty, and they do NOT come back: a kubelet registers
                             ONCE, at startup, then only ever UPDATEs.
       crictl ps          -> NINE containers, all still serving.
     the beliefs and the world came apart. the world is the half still working.

   RESTORE
     1. etcdutl snapshot restore --data-dir NEW   (on your laptop, cluster still up)
     2. docker cp NEW into the node
     3. STOP all four manifests (~35s; the API server is the slow one)
     4. swap the directory, put the manifests back
        nothing enforces step 3. etcdutl's only guard is "dir not empty".
        stopping the control plane is YOUR correctness requirement.

   WHAT A RESTORE DOES NOT UNDO
     the store's revision goes BACKWARDS, so every watch is waiting on a future
     revision and no change ever arrives. the post-snapshot workload keeps
     RUNNING AND SERVING, indefinitely, with no object anywhere.
     systemctl restart kubelet -> fresh list -> reaped in seconds.
     A RESTORE IS AN ASSERTION, NOT A REWIND. make the nodes look again.
```

**Cleanup** — and the last two commands are not optional, because the next lessons break static Pods and a kubelet still carrying pre-restore state will report nonsense about them:

```bash
kubectl delete namespace precious
docker exec $CP sh -c 'rm -rf /var/lib/etcd-gone /var/lib/etcd-empty /var/lib/etcd/etcd-backup.db'
rm -rf etcd-backup.db etcd-restored
docker exec $CP systemctl restart kubelet
docker exec netlab-worker systemctl restart kubelet
sleep 30
kubectl get nodes                                                  # both Ready
docker exec $CP ls /etc/kubernetes/manifests/                      # all four
```

> **You understand this when you can** take a snapshot, say why it must be written inside the `hostPath`, and verify it by something other than the file existing; say from any etcd operation alone whether it needs `etcdctl` or `etcdutl`, and why neither is on the node; explain why a cluster whose store has been wiped answers `Forbidden` rather than refusing to connect, and which credential still works and why; and describe what a restore does *not* undo — using both a node that joined after the snapshot and a workload that is still serving traffic — and name the one command that resolves both.

**Which raises:** you have now stopped the control plane deliberately and put it back, twice, and both times every component returned at exactly the version it left at. But a cluster that lives long enough gets upgraded, and an upgrade is the case where the components come back *different*, one at a time, while the cluster keeps serving. What is allowed to be out of step with what, and for how long?

---

← Prev: **[The cluster's own PKI](04-the-clusters-own-pki.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Upgrades, and what is allowed to be out of step](06-upgrades-and-version-skew.md)** →
