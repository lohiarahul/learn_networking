# Three different promises called "survives"

Act I ended a lesson with a question and left it deliberately unanswered. Here it is again, because it has been waiting six acts:

> *"The writable layer dies with the container. A filesystem mounted in at a path outlives it. So: what should happen to a program's data when the program is expected to be restarted, replaced, or moved to a different machine entirely — and **who gets to decide where 'the path that survives' actually points?**"*

It also gave you the warning that makes this lesson matter, and it is the sentence to keep in mind the whole way down:

> *"Notice that the question has more than one right answer, because 'survives a restart' and 'survives the machine' are different promises."*

They are. There are three, they look identical in a Pod spec, and choosing the wrong one is how data gets lost.

### Promise one: survives a restart

The cheapest volume there is:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: { name: scratch }
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - { name: tmp, mountPath: /data }
  volumes:
    - name: tmp
      emptyDir: {}
EOF
kubectl wait --for=condition=Ready pod/scratch --timeout=90s
kubectl exec scratch -- sh -c 'echo "written at $(date)" > /data/note.txt; cat /data/note.txt'
```

An **`emptyDir`** is a directory the kubelet creates when the Pod is placed. Now test what it survives, using the tool from lesson 01:

```bash
NODE=$(kubectl get pod scratch -o jsonpath='{.spec.nodeName}')
CID=$(docker exec $NODE sh -c "crictl ps --label io.kubernetes.pod.name=scratch -q | head -1")
docker exec $NODE crictl stop $CID
sleep 10
kubectl get pod scratch
kubectl exec scratch -- cat /data/note.txt
```

`RESTARTS 1`, and **the file is still there.** Which is already more than the container's own filesystem gives you — Act I showed that the writable layer is discarded, so anything the container wrote outside `/data` is gone while this survived.

> **Predict first —** so `emptyDir` survives a container restart. Now: does it survive the **Pod** being deleted and recreated by a controller? And can two Pods on different nodes share one? Answer both before you look — and reason from the name of the thing that created it rather than from the word "empty".

```bash
kubectl delete pod scratch
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: scratch }
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - { name: tmp, mountPath: /data }
  volumes:
    - name: tmp
      emptyDir: {}
EOF
kubectl wait --for=condition=Ready pod/scratch --timeout=90s
kubectl exec scratch -- ls -la /data/
```

**Empty.** And it had to be, because of *who* made it: the **kubelet**, on one node, in a directory under that Pod's own UID — the same `/var/lib/kubelet/pods/<uid>/` tree you read the Secret out of last lesson. A new Pod is a new UID, so it is a new directory. The old one was deleted with the Pod it belonged to.

So the answer to the second half is also no. An `emptyDir` cannot be shared between nodes, because it is a path on *a* node, and nothing outside that node knows it exists.

**`emptyDir` survives a restart and nothing more.** Which makes it exactly right for scratch space — a cache, a scratch file, a directory two containers in the same Pod pass data through — and exactly wrong for anything you would be upset to lose. It is also why `kubectl drain` made you type `--delete-emptydir-data`: draining a node destroys every one of these, permanently, and the flag is you saying you know.

```bash
kubectl delete pod scratch
```

### Promise two: survives the Pod

For data to outlive a Pod, it has to be described by something that is not a Pod. And that is the whole design:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: data }
spec:
  accessModes: [ReadWriteOnce]
  resources: { requests: { storage: 100Mi } }
EOF
kubectl get pvc data
```

Look at the state, because it is informative:

```
NAME   STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS
data   Pending                                      standard
```

**`Pending`, with no volume.** You have made a *claim* — a request for storage — and nothing has satisfied it yet. That word is chosen carefully, and by now you should recognise the shape: this is an object stating intent, waiting for a loop to act on it. Exactly like a Pod with no `nodeName`.

```bash
kubectl get storageclass
```

`standard`, with a `PROVISIONER` of `rancher.io/local-path`. **That** is the loop, and the `StorageClass` is how a claim finds it. Now give the claim a consumer:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: { name: keeper }
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - { name: d, mountPath: /data }
  volumes:
    - name: d
      persistentVolumeClaim: { claimName: data }
EOF
kubectl wait --for=condition=Ready pod/keeper --timeout=120s
kubectl get pvc data
kubectl get pv
```

Now the claim is `Bound`, and a **PersistentVolume** exists that you never wrote. That is the provisioner having acted — and note *when* it acted. The claim sat `Pending` until a Pod actually needed it, which is `volumeBindingMode: WaitForFirstConsumer` on that StorageClass, and it is not an optimisation. It exists because the volume is a directory on a *particular node*, so the storage cannot be created until the scheduler has decided which node — **the placement decision and the storage decision have to be made together, or one contradicts the other.**

So: write something, then destroy the Pod.

```bash
kubectl exec keeper -- sh -c 'echo "this should survive" > /data/note.txt'
kubectl delete pod keeper
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: keeper }
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - { name: d, mountPath: /data }
  volumes:
    - name: d
      persistentVolumeClaim: { claimName: data }
EOF
kubectl wait --for=condition=Ready pod/keeper --timeout=120s
kubectl exec keeper -- cat /data/note.txt
```

**`this should survive`.** The Pod died completely and the data did not, because the data belongs to the PVC and the PVC is a separate object with its own lifetime.

Which finally answers Act I's question directly. **Who decides where the surviving path points? A provisioner, told which class of storage to use, in response to a claim that outlives the Pod.** Three objects: the claim you write, the class that routes it, and the volume the provisioner creates.

### The promise this one does *not* make

Now find out where that volume actually is:

```bash
kubectl get pv -o jsonpath='{range .items[*]}{.metadata.name}{"  node="}{.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]}{"  path="}{.spec.hostPath.path}{"\n"}{end}'
```

A **path on one named node**, pinned by node affinity. Which means:

> **Predict first —** that PVC is bound to a volume that is a directory on one specific node. What happens if you cordon that node and delete the Pod? Remember from lesson 04 what `nodeAffinity` on the *volume* implies for the scheduler.

```bash
kubectl cordon $(kubectl get pv -o jsonpath='{.items[0].spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]}')
kubectl delete pod keeper --wait=true
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: keeper }
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - { name: d, mountPath: /data }
  volumes:
    - name: d
      persistentVolumeClaim: { claimName: data }
EOF
sleep 15
kubectl get pod keeper
kubectl describe pod keeper | tail -4
```

**`Pending`** — and now read the event carefully, because it is a lesson in its own right:

```
0/2 nodes are available: 1 node(s) had untolerated taint(s), 1 node(s) were
unschedulable. preemption: 0/2 nodes are available: 2 Preemption is not helpful.
```

It says *unschedulable*. It does not mention the volume at all. And before you accept the explanation you were about to reach for, run the control:

```bash
kubectl run novol --image=busybox:1.36 --command -- sleep 3600
sleep 10
kubectl describe pod novol | tail -4
kubectl delete pod novol --now
```

**Byte-identical message, from a Pod with no volume whatsoever.** On a cluster with one worker, "the volume is pinned to that node" and "there is only one node and you cordoned it" predict exactly the same outcome, so this experiment cannot tell them apart — and neither can the event text. Add a second worker and the message changes to a real `volume node affinity conflict`; here it never appears.

Keep that, because it generalises past storage: **a `Pending` reason names the first constraint the scheduler tripped over, not the one you care about.** The volume pinning is real — the `nodeAffinity` is right there on the PV, which is evidence you read off the object rather than out of an event — but this cluster cannot demonstrate it, and pretending otherwise would be believing a message that says something else.

This is `local-path` storage being honest about what it is. **Your data survives the Pod, and it is welded to one machine.** Lose that machine and the volume is gone with it; make that machine unavailable and your Pod cannot run anywhere.

```bash
kubectl uncordon $(kubectl get pv -o jsonpath='{.items[0].spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]}')
kubectl wait --for=condition=Ready pod/keeper --timeout=120s
```

**Promise three — survives the machine — is the one your lab cannot make.** It needs storage that is not on any node: a network filesystem, a cloud disk that can detach and reattach elsewhere, a replicated block device. That is what a real `StorageClass` points at, and the interface is *identical* — same PVC, same `accessModes`, same YAML. Which is the genuine achievement of this design and also its sharpest hazard: **the manifest that gives you promise two and the manifest that gives you promise three are the same manifest.** The difference is entirely in what the StorageClass provisions, and nothing in your Pod spec tells you which you got.

Which is what `accessModes` is really declaring:

| Mode | Meaning |
|---|---|
| `ReadWriteOnce` | one **node** may mount it read-write |
| `ReadWriteOncePod` | one **Pod**, full stop |
| `ReadOnlyMany` | many nodes, read-only |
| `ReadWriteMany` | many nodes, read-write |

`ReadWriteOnce` is not "one Pod" — it is one *node*, so two Pods on the same node can both write, which surprises people. And note that these are a **request**, not an enforcement: a provisioner that cannot do `ReadWriteMany` will simply fail to bind, and `local-path` can only ever do `ReadWriteOnce`, because a directory on a node cannot be mounted from elsewhere at all.

### When the class promises something the provisioner cannot keep

One more experiment, because it teaches the seam between the abstraction and reality better than any explanation.

```bash
kubectl get sc standard -o custom-columns=NAME:.metadata.name,EXPANSION:.allowVolumeExpansion
kubectl patch pvc data -p '{"spec":{"resources":{"requests":{"storage":"200Mi"}}}}'
```

`EXPANSION` prints `<none>` — the field is *absent* from the object, not set to false, which is why a bare `jsonpath` on it returns an empty line rather than `false`. And the resize is refused outright, by the API server, with the reason spelled out:

```
Error from server (Forbidden): persistentvolumeclaims "data" is forbidden: only
dynamically provisioned pvc can be resized and the storageclass that provisions
the pvc must support resize
```

So grant the permission the class was missing:

```bash
kubectl patch storageclass standard -p '{"allowVolumeExpansion": true}'
```

> **Predict first —** the StorageClass now says volumes of this class can be expanded. You ask for more space. Does the PVC grow?

```bash
kubectl patch pvc data -p '{"spec":{"resources":{"requests":{"storage":"200Mi"}}}}'
sleep 20
kubectl get pvc data
kubectl describe pvc data | tail -6
```

The **request** is 200Mi and the **capacity** is still 100Mi, indefinitely. The API server accepted your edit because the StorageClass said expansion was allowed; nothing expanded, because nothing that could expand it exists.

The event says who it is waiting for:

```
Normal  ExternalExpanding  20s  volume_expand  waiting for an external controller
                                               to expand this PVC
```

An **external controller** — which is the first time this course has needed the name for that role. Kubernetes does not know how to grow a disk, and could not: growing an EBS volume, an NFS export and a directory on a node have nothing in common. So the work is delegated over a defined interface, the **Container Storage Interface**, and a vendor ships a driver that implements it. Every dynamic provisioner you meet in a real cluster is a CSI driver. `local-path` is not — it is a small provisioner predating that interface, it implements creation and deletion and nothing else, and there is no external controller listening for that event. So the PVC waits for a component that was never installed, forever, and says so quietly.

**A StorageClass field is a promise the provisioner has to keep.** Setting `allowVolumeExpansion: true` does not grant a capability — it declares one, and a declaration made on behalf of a provisioner that cannot deliver produces a PVC whose spec and status disagree forever. Which is a shape you have seen twice now: an object stating intent, and nothing able to satisfy it. `Pending` on a Pod, and a stuck `resources.requests` here.

> **Check yourself —** A team runs a database on a 3-node cluster with `local-path` storage and a `ReadWriteOnce` PVC. It has worked for a year. One night the node holding the volume loses its disk. What is the state of the database Pod, what is the state of the data, and which single earlier decision determined both?

<details>
<summary>Answer</summary>

The Pod is `Pending` and will stay there. The data is gone.

The Pod cannot be rescheduled because the PV carries node affinity for a node whose volume no longer exists, and no other node has a copy — so the scheduler has exactly zero candidates, and says so in the events. There is nothing to fix in the Deployment, the PVC, or the cluster; the storage the claim is bound to is on a disk that failed.

The decision that determined both was the **StorageClass**, chosen once, probably by default, a year earlier. `local-path` gives you promise two — survives the Pod — and the team was relying on promise three. Nothing in the Pod spec, the PVC, or a year of successful operation would have revealed the difference, because the manifests are identical either way. The only way to know was to look at what the provisioner actually was.

Two things follow. **First, the check is `kubectl get storageclass` and knowing what that provisioner does** — not reading your own YAML, which cannot tell you. **Second, and more importantly: replication is not a storage feature you can retrofit at 3am.** Either the volume was replicated or the data is gone, and that was settled before the incident. Which is why the honest form of "we have persistent storage" is a question: persistent against *what*?

</details>

<!-- figure -->

```
   THREE PROMISES, IDENTICAL-LOOKING YAML

   1. SURVIVES A RESTART        emptyDir: {}
        a directory the KUBELET makes under /var/lib/kubelet/pods/<uid>/
        new Pod = new UID = new empty directory. cannot cross nodes.
        this is why drain demands --delete-emptydir-data.

   2. SURVIVES THE POD          persistentVolumeClaim -> StorageClass -> PV
        the claim is a separate object with its own lifetime.
        WaitForFirstConsumer: the volume cannot be created until the
          SCHEDULER picks a node, because the volume IS on a node.
          placement and storage are one decision, not two.
        local-path => the PV has nodeAffinity to ONE node.
          lose the node -> Pod Pending forever, data gone.

   3. SURVIVES THE MACHINE      the same manifest, a different StorageClass
        needs storage on no node: NFS, a cloud disk, replicated block.
        *** THE HAZARD: 2 and 3 ARE THE SAME YAML. ***
        nothing in the Pod spec tells you which you got.
        the only check is: which provisioner does the StorageClass use?

   accessModes are a REQUEST, not enforcement
     ReadWriteOnce = one NODE (so two Pods on that node can both write)
     ReadWriteOncePod = one Pod, full stop
     a provisioner that cannot do the mode simply fails to bind

   allowVolumeExpansion: true is a PROMISE THE PROVISIONER MUST KEEP
     set it on local-path and the API server accepts a resize
     while status.capacity never moves. spec and status, disagreeing forever.
```

**Cleanup** — and this one matters, because a PVC outlives everything else you delete:

```bash
kubectl delete pod keeper
kubectl delete pvc data
kubectl patch storageclass standard -p '{"allowVolumeExpansion": null}'   # you changed a CLUSTER-scoped object
kubectl get pv                     # the PV goes too: reclaimPolicy Delete
kubectl get pvc -A                 # empty
```

That the PV vanished with the claim is `persistentVolumeReclaimPolicy: Delete`, the default on dynamically provisioned volumes. `Retain` keeps the volume and its data after the claim is gone — safer, and it leaves you tidying up by hand. (`Recycle` used to be a third option and has been removed; if you meet it in an old document, it is gone.)

> **You understand this when you can** name three things a volume might survive and say which of them `emptyDir` and a `local-path` PVC each give you; explain why a PVC sits `Pending` until a Pod needs it, and why placement and storage provisioning cannot be separate decisions; say what `ReadWriteOnce` actually restricts; and explain why identical manifests can give you data that survives a machine failure or data that does not, and name the one thing you must inspect to tell.

**Which raises:** that PVC belonged to one Pod, and you named the Pod yourself. But a Deployment's Pods have random suffixes and are interchangeable by design — which is fine for a stateless web server and useless for a database with three members that must each keep *their own* disk and be able to find each other by name. So what runs a workload whose replicas are not interchangeable?

---

← Prev: **[Configuration, and where a secret actually ends up](05-configuration.md)** · ↑ **[Act VII overview](README.md)** · Next: **[When replicas are not interchangeable](07-the-other-workload-kinds.md)** →
