# Nothing here remembers

Act X ended on the only thing in this course that keeps a memory on purpose. Its audit log answers *"at what moment did this refuse, and what did it know then"* — a record built specifically so that a question asked after the fact still has an answer. It is also, if you are honest about its scope, a record of exactly one kind of event: **an authorised change**, made through the API server, by someone the cluster could name.

Nobody was harmed. Nothing was refused. A user hit a 502 for eleven minutes yesterday afternoon, and every mechanism in the ten acts before this one would shrug at the question "what happened." Try it, on your own cluster, right now, before installing anything:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act11.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"
docker exec netlab-control-plane grep -c -- --event-ttl /etc/kubernetes/manifests/kube-apiserver.yaml
```

```
0
```

Zero matches. `--event-ttl` is not set anywhere in kind's own control-plane manifest, so the default applies, and the default is **one hour**. An incident from yesterday afternoon has already been garbage-collected out of `kubectl get events` by the time you think to ask about it. That is not a misconfiguration — it is every cluster you will ever touch, because almost nobody sets this flag, and the reason nobody sets it is that Events were never designed to be a record. They are a courtesy notification with an expiry, and this course has been treating them as diagnostic evidence since Act V without ever saying so.

`kubectl logs --previous` reaches back exactly one container restart, as you are about to measure. `kubectl top` has no `--since`. Delete a Pod and its logs are gone with it — and *exactly* which directory they were in is this lesson's subject. **Every diagnostic method this course has taught you starts after the phone rings and assumes the evidence is still standing there, present tense, waiting.** This act's carried question, in Act X's own idiom: **what did this system write down before anyone asked, what did it therefore throw away, and what did keeping it cost?**

> **Predict first —** a Pod has crashed and restarted three times before anyone notices. Write down, before running anything: **(a)** of the three dead containers, which one's output can `kubectl logs` still reach? **(b)** where, physically, do the bytes for the other two currently sit — a database, a compressed archive, or somewhere else? **(c)** if you delete the Pod right now, what happens to whichever logs are still reachable?

### Finding the file `kubectl logs` reads

`kubectl logs` looks like it is asking the API server a question. It is not — the API server has no logs of your workload and never has. Trace what actually happens: the request goes to the API server, which proxies it to the **kubelet** on the node that ran the Pod, which reads a file and streams it back. Read the file yourself, on the node, and cut the API server out of the loop entirely:

```bash
kubectl run reader --image=busybox:1.36 --restart=Never --command -- sh -c 'echo hello from reader'
sleep 6
kubectl get pod reader -o jsonpath='{.metadata.uid}{" "}{.spec.nodeName}{"\n"}'
```

```
c1c8a0b1-...-uid netlab-worker
```

```bash
docker exec netlab-worker ls /var/log/pods/ | grep reader
```

```
default_reader_<uid>
```

**`<namespace>_<pod-name>_<uid>`.** Not the name alone — the UID, the one identifier this course has taught you to walk past on every `kubectl get -o yaml` you have ever run. Inside it, one subdirectory per container, and inside that:

```bash
docker exec netlab-worker sh -c 'ls /var/log/pods/default_reader_*/reader/'
docker exec netlab-worker sh -c 'cat /var/log/pods/default_reader_*/reader/0.log'
```

```
0.log
2026-08-30T06:xx:xx.xxxxxxxxxZ stdout F hello from reader
```

That line has a shape you have not been shown yet, and every field in it matters. **`<RFC3339Nano timestamp>` `<stream>` `<F|P>` `<the actual line>`.** The timestamp and stream (`stdout`/`stderr`) are obvious. `F` is not — it stands for **full**, meaning the container runtime received this as one complete write. There is a `P`, for **partial**, and you are about to produce one on purpose, because the difference between them is where a hand-rolled log pipeline quietly loses data and `kubectl logs` does not.

```bash
kubectl run longline --image=busybox:1.36 --restart=Never --command -- \
  sh -c 'head -c 70000 /dev/zero | tr "\0" "A"; echo; sleep 300'
sleep 8
docker exec netlab-worker sh -c \
  "awk '{print NR, length(\$0), \$3}' /var/log/pods/default_longline_*/longline/0.log"
```

```
1 16424 P
2 16424 P
3 16424 P
4 16424 P
5 4504 F
```

**One `echo` produced five lines on disk.** The container runtime's log pipe flushes in roughly 16KB chunks, so a single write bigger than that arrives as several `P` records — partial, partial, partial, partial, then one final `F` that closes it out. `kubectl logs` knows the convention and stitches all five back into the one line you actually wrote:

```bash
kubectl logs longline | wc -l
kubectl logs longline | wc -c
```

```
1
70001
```

One line, seventy thousand and one characters (the trailing newline from `echo`). **A shipper that tails this file byte-for-byte and forwards each line verbatim will forward four fragments and one tail, as five separate log entries, because it does not know the convention `kubectl logs` was built to honour.** That is a real failure mode with a real name, and you will reproduce it deliberately once there is a shipper to break.

### The symlink farm, and the rotation nobody documents

`/var/log/pods/<ns>_<pod>_<uid>/<container>/N.log` is the ground truth. A second directory exists purely for convenience, and it is worth knowing which is which, because only one of them survives a Pod rename in the way you would expect:

```bash
docker exec netlab-worker ls -la /var/log/containers/ | grep longline
```

```
longline_default_longline-<hash>.log -> /var/log/pods/default_longline_<uid>/longline/0.log
```

`/var/log/containers/` is a flat directory of **symlinks**, named `<pod>_<namespace>_<container>-<containerID>.log`, every one of them pointing back into `/var/log/pods/`. Tools that want a human-readable filename read this directory; tools that want the authoritative path read the other one. They are the same bytes either way — this is a naming convenience, not a second copy.

Rotation is the other half of "how much of this can I actually read," and it is set by the kubelet, not by documentation you can trust to be current:

```bash
NODE=netlab-worker
kubectl get --raw "/api/v1/nodes/$NODE/proxy/configz" \
  | python3 -c 'import json,sys; kc=json.load(sys.stdin).get("kubeletconfig",{}); print(kc["containerLogMaxSize"], kc["containerLogMaxFiles"])'
```

That is the same `kubectl get --raw` you have used since Act VI to read the API server's own paths — the only new thing is the path itself. `/api/v1/nodes/<name>/proxy/<anything>` is a **subresource** of the Node object: the API server, on seeing it, does not look in etcd, it opens an HTTP connection to that node's kubelet and forwards whatever comes back. Same mechanism as `kubectl logs` and `kubectl exec` — you have been using this proxy path since Act V, you were just never shown its address.

```
10Mi 5
```

**Ten megabytes per file, five files, per container.** Once `0.log` (the current restart's log) passes 10Mi it rotates to a compressed `.log.1.gz` and a fresh `0.log` starts, and once there are more than five of those, the oldest is deleted. Note what that number is *not* about: it has nothing to do with the `N` in `N.log`, and nothing to do with the 16KB chunking you just measured. Three separate limits, three separate mechanisms, all living in the same small set of files, and confusing any two of them is how a real incident review goes sideways.

### Restart the container, and watch the number in the filename

Crash a Pod on purpose, and read the directory the moment the restart count changes — not a fixed number of seconds later, because you are about to measure that "later" is exactly the problem:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: crasher}
spec:
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","echo boom $(date +%s); exit 1"]
EOF
until [ "$(kubectl get pod crasher -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null)" = "1" ]; do sleep 1; done
docker exec netlab-worker sh -c 'ls /var/log/pods/default_crasher_*/c/'
kubectl logs crasher --previous
```

```
0.log
1.log
boom 1788072452
```

**Two files on disk, and `--previous` reads the first one.** Now do nothing except let one more restart happen, and ask exactly the same question again:

```bash
until [ "$(kubectl get pod crasher -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null)" = "2" ]; do sleep 1; done
docker exec netlab-worker sh -c 'ls /var/log/pods/default_crasher_*/c/'
kubectl logs crasher --previous
```

```
2.log
unable to retrieve container logs for containerd://7a13ab072d52664bf9e803e2529217b099fc92278096853d79529144cc83ea04
```

**`0.log` and `1.log` are both already gone. `--previous` does not even fail with an empty response — it fails outright,** because there is no longer a previous container object for it to ask about. The kubelet's garbage collector cleared the dead container, log file and all, in the time it took one more restart to happen. This is not "one generation back, comfortably" — it is **one generation back if you are already looking, and often nothing at all by the time a human reacts to a page.** The number in the filename (`0`, `1`, `2`, ...) is simply the restart count at the moment that container ran, and it is not a retention setting at all — the kubelet decides independently, on its own schedule, how many of these to keep before deleting one.

Now delete the Pod, and time how long the whole directory survives:

```bash
kubectl delete pod crasher
sleep 5
docker exec netlab-worker sh -c 'ls /var/log/pods/ | grep crasher || echo GONE'
```

```
GONE
```

Five seconds. **Every log that container ever wrote — including `2.log`, the one file that was still on disk — left with the Pod object.** Follow that one level further, because it is the sentence this whole lesson has been building to: a Pod is deleted whenever its ReplicaSet decides to delete it — a scale-down, a rolling update, a node drain, any of Act VII's ordinary reconciliation traffic. **So log retention on a node is bounded by Pod lifetime, and Pod lifetime is bounded by a ReplicaSet's ordinary, routine, entirely-successful opinion about how many replicas should exist right now.** Nothing has to go wrong for the evidence to disappear. The system doing exactly what it was designed to do is sufficient.

### The name the node was already using

One measurement costs nothing extra, because Act IV already put the other half of it in front of you. That Pod UID naming the log directory is not a coincidence of this one subsystem — it is the *only* name the node itself uses for a Pod, and it shows up in a second place you have already been shown:

```bash
PODUID=$(kubectl get pod -n kube-system -l k8s-app=kube-proxy -o jsonpath='{.items[0].metadata.uid}')
echo "$PODUID"
docker exec netlab-worker find /sys/fs/cgroup -iname "*$(echo "$PODUID" | tr '-' '_')*"
```

```
16404289-8c09-4209-be02-07e4b531d816
/sys/fs/cgroup/kubelet.slice/kubelet-kubepods.slice/kubelet-kubepods-besteffort.slice/kubelet-kubepods-besteffort-pod16404289_8c09_4209_be02_07e4b531d816.slice
```

**Same UID, dashes for the log directory, underscores for the cgroup slice.** Act IV taught you to read a cgroup's own accounting files by hand; this act is teaching you where a Pod's words go. Both are filed under the one identifier no object you routinely inspect ever shows you on its own — you had to go looking for it in `.metadata.uid`. The node does not know your Pod by name. It knows it by this.

### The rival, and why it is not enough

`kubectl logs -f mypod > /tmp/capture.log &` looks like a fix — start a follower, redirect it somewhere durable, walk away. It works, for exactly as long as the terminal session, the SSH connection, or the laptop lid stays open, and it captures exactly one container, chosen by hand, that somebody remembered to point it at *before* the incident started. It is not a mechanism. It is a single point of failure wearing the shape of one.

<details>
<summary>Check yourself — before reading on</summary>

A teammate proposes: "let's just raise `containerLogMaxFiles` to 50 and `containerLogMaxSize` to 100Mi on every node, and the retention problem goes away." What has that fixed, and what has it not?

It buys you more history *per container, per node, for as long as that specific container keeps restarting into the same Pod object*. It does nothing for the actual failure mode this lesson measured: the moment the Pod is deleted — which is the normal, frequent, nothing-went-wrong case, not the rare one — every log file under it is gone regardless of how large you let it grow first. It also does nothing for a node that dies outright, taking its whole `/var/log/pods` with it. Bigger retention on the node is a wider window on a copy that was always going to be destroyed with the thing it describes. It is not durability; it delays the deadline without changing the fact that there is one.

</details>

```
<!-- figure -->
   THE LOG LINE, AND EVERYTHING THAT DECIDES HOW LONG IT LIVES

   THE PATH kubectl logs ACTUALLY READS
     /var/log/pods/<ns>_<pod>_<UID>/<container>/N.log
     /var/log/containers/<pod>_<ns>_<container>-<id>.log  (a SYMLINK farm, convenience only)

   ONE LINE, FOUR FIELDS
     <RFC3339Nano timestamp> <stdout|stderr> <F|P> <the text>
     F = full write.  P = partial -- runtime's pipe flushed at ~16KB.
     ONE echo OF 70,000 CHARS -> 4 P records + 1 F record ON DISK.
     kubectl logs REASSEMBLES THEM. a byte-for-byte tail does not.

   THREE LIMITS, THREE MECHANISMS -- DO NOT CONFUSE THEM
     N in N.log ............ restart count, NOT retention
     containerLogMaxSize ... 10Mi per file before rotation (measured)
     containerLogMaxFiles .. 5 files kept before the oldest is deleted
     none of these care about the other two.

   MEASURED, ON A REAL CRASH LOOP
     restart 1: 0.log AND 1.log both on disk. --previous reads 0.log.
     restart 2, checked the SAME way: only 2.log remains. --previous
       fails OUTRIGHT -- "unable to retrieve container logs."
     one generation back, ONLY if you are already looking.
     `kubectl delete pod` -> the WHOLE directory is gone within 5 SECONDS.

   THE SENTENCE THIS LESSON IS FOR
     log retention is bounded by POD LIFETIME.
     Pod lifetime is bounded by a REPLICASET'S ORDINARY OPINION.
     nothing has to go wrong. routine reconciliation is sufficient.

   THE NAME THE NODE ACTUALLY USES (Act IV, reappearing)
     same Pod UID:
       log dir  ....... ...pod07dcc401-d565-4420-...  (dashes)
       cgroup slice ... ...pod07dcc401_d565_4420_...  (underscores)
     no object you routinely read shows you this name on its own.
```

**Cleanup:**

```bash
kubectl delete pod reader longline crasher --ignore-not-found
```

> **You understand this when you can** name the four fields of a CRI log line and explain what `F` versus `P` means for a single write larger than ~16KB; state, from measurement, how many restarts back `kubectl logs --previous` can actually reach; distinguish the three separate limits governing what is on a node (`containerLogMaxSize`, `containerLogMaxFiles`, and the restart-count filename) and say which of the three is not a retention setting at all; and explain why deleting a Pod — the ordinary, successful case, not the failure — is enough to erase every log it ever wrote.

**Which raises:** the only copy of any of this lives on one node, in a directory that a ReplicaSet can delete out from under you at any moment, for entirely healthy reasons. Something has to read these bytes and copy them somewhere that does not share the Pod's lifetime — *while the Pod still exists to be read from* — and that something is itself a workload you already know how to write.

---

↑ **[Act XI overview](README.md)** · Next: **[A number a process keeps](03-a-number-a-process-keeps.md)** →
