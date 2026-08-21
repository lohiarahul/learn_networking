# When the control plane breaks

Act V gave you five questions for a network that lies, and every one of them was answered by a file you could read. That method has a silent prerequisite you have now broken three times: it assumed you could talk to the cluster.

This lesson is the other half. Act V's five questions descend the **network stack** — DNS, routing, NAT, TCP, the application. These five descend a different one:

<!-- figure -->

```
  Question 1  Does the API server answer?  ->  kubectl get --raw /readyz     needs: everything
  Question 2  What does the cluster say?   ->  events, describe, logs -p     needs: the API server
  Question 3  Is the container running?    ->  crictl ps -a, crictl logs     needs: the runtime
  Question 4  What is the kubelet saying?  ->  journalctl -u kubelet         needs: systemd
  Question 5  What is on the disk?         ->  manifests, certs, df          needs: nothing
       ------  descend until something ANSWERS. the first tool that does is your ground truth.  ------
       ------  (Act V stopped at the first layer that LIED. this one is the inverse.)          ------
```

Same discipline, different axis — and **the opposite stopping rule**, which is worth fixing in your head before you start. Act V's order was forced by causality, so you read down and *stopped at the first layer that lied*. This order is forced by **dependency**: each question needs less of the cluster to be working than the one above it, so you read down and stop at the first tool that **answers**. A silent tool here is not a passed check, it is an instruction to go lower.

That is what makes the ladder terminate. Question 5 always answers, because a disk does not need a cluster.

Keep the orientation question the whole way down, unchanged: *what is the file here, who reads it, who writes it?*

### Question 1 — Does the API server answer?

Everything hinges on this, so it is one command and you should not skip it even when you are sure:

```bash
CP=netlab-control-plane          # used throughout this lesson
kubectl get --raw /readyz
kubectl get --raw '/readyz?verbose' | tail -20
```

`ok`, or a list of named checks with the failing ones marked. This is the same family of endpoint as the `/healthz` you curled in Act V, one step stricter: `healthz` asks whether the process is alive, `readyz` asks whether it is fit to serve requests. The verbose form is the one worth knowing, because it distinguishes two situations that look the same from a distance — `etcd` failing in that list means the API server is answering *you* while unable to reach the store, which is a very different problem from silence.

([Act V's in-the-wild page](../act-5-kubernetes/in-the-wild.md) walks the version of this you are most likely to actually hit — `kubectl` unable to reach a cluster because of something on *your* machine rather than the cluster's. Rule that out before you start moving manifests around.)

If you get `Unable to connect to the server`, stop. Every command in Question 2 is now useless, and the temptation to keep typing `kubectl` is the single biggest waster of time in this whole subject. **Descend.**

### Question 2 — What does the cluster say about itself?

If the API server answers, use it properly before going lower. The cluster keeps a running commentary that people ignore:

```bash
kubectl get events -A --sort-by=.lastTimestamp | tail -20
kubectl get nodes
kubectl -n kube-system get pods
```

Events are the cluster's own account of what it tried and what happened, and the reconciliation lesson gave you the reason they matter: **a loop that tried and failed says so here, and a loop that is not running says nothing at all.** An empty event list next to a stuck object is not "no information" — it is the information.

And the components themselves have things to say. `kubectl logs` fetches a container's standard output through the API server — the kubelet on that node holds the log file and the API server proxies to it, which is why this is a Question 2 tool and not a lower one:

```bash
kubectl -n kube-system logs kube-controller-manager-$CP --tail=5
```

For a component that is *restarting*, though, that is the wrong log. The container you can see has not failed yet; the one that failed is already gone. `--previous` asks for it:

```bash
kubectl -n kube-system logs kube-controller-manager-$CP --previous --tail=30
```

On a healthy cluster that errors — `previous terminated container ... not found` — and that is the correct answer, not a problem. There has been no previous container because nothing has crashed. Remember the shape of the error, because when it *does* return something you are looking at a component's dying words.

You will meet two failure states in `kubectl get pods` that look equally alarming and have nothing in common. **`CrashLoopBackOff`** means the container starts and exits — the process ran, so the process has an opinion, and `logs --previous` will hand it to you. **`ImagePullBackOff`** means nothing ever started, because the image could not be fetched; there are no logs and there never will be, and the evidence is in `describe` instead. You are about to cause both on purpose.

### Question 3 — is the container even running?

Now the interesting half, because from here down nothing needs the cluster.

Break something first. This is the classic control-plane failure, and inducing it deliberately is much cheaper than meeting it for the first time in anger:

> **Predict first —** you add a flag that does not exist to `/etc/kubernetes/manifests/kube-apiserver.yaml`. Predict two things: what `kubectl` does, and what the *kubelet* does — remembering from lesson 02 that the kubelet is watching that file and has no idea what a valid API server flag is.

```bash
# CP is already set from Question 1
docker exec $CP cp /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/apiserver.good
docker exec $CP sh -c "sed 's|    - kube-apiserver|    - kube-apiserver\n    - --this-flag-does-not-exist=true|' \
  /tmp/apiserver.good > /etc/kubernetes/manifests/kube-apiserver.yaml"
sleep 25
kubectl get nodes                          # gone
```

(Write a fresh copy rather than using `sed -i`. In-place editing leaves a temporary file *in* `/etc/kubernetes/manifests/`, and the kubelet does not care about file extensions — it tries to parse it and complains in the very log you are about to start trusting.)

`kubectl` is dead, as expected. The kubelet, meanwhile, is doing precisely its job and it is not helping: the file changed, so it started a container from it, and that container exited, so it will start it again, forever. **The kubelet has no opinion about whether the thing it starts works.**

So ask the runtime directly. `crictl` is the node's own container CLI — the tool the kubelet itself talks to, one layer below `kubectl` and completely independent of it:

```bash
docker exec $CP crictl ps -a --name kube-apiserver
```

`ps -a` rather than `ps`, because the container you care about is not running — it is the **`Exited`** one, and its state and its climbing `ATTEMPT` count are the first real evidence you have had since Question 1. That counter going up is the kubelet retrying on a back-off, which is exactly what `CrashLoopBackOff` means when you can see it from `kubectl`.

Note the container ID changes on every restart, which is why you list before you read. Then read what the process said on its way out:

```bash
CID=$(docker exec $CP sh -c "crictl ps -a --name kube-apiserver -q | head -1")
docker exec $CP crictl logs $CID 2>&1 | tail -20
```

```
Error: unknown flag: --this-flag-does-not-exist
```

One line, in the process's own words. Not a Kubernetes concept, not a distributed-systems problem — a typo, reported by a binary that refused to start, retrieved with no cluster involved at all.

Fix it the way lesson 02 established, and note the recovery is as fast as the break — about fifteen seconds:

```bash
docker exec $CP cp /tmp/apiserver.good /etc/kubernetes/manifests/kube-apiserver.yaml
until kubectl get nodes 2>/dev/null; do sleep 2; done
```

Before moving on, break it a second way — and predict the result before you read another word, because you now know enough about the mechanism to reason it out.

> **Predict first —** this time, instead of a bad flag, you make the manifest *invalid YAML*: not a wrong setting, but a file the kubelet cannot parse at all. Given what you just watched — the kubelet reading a file and starting a container from it — say what you expect `crictl ps -a --name kube-apiserver` to show, and where the evidence will be if it shows nothing.

### Question 4 — what is the kubelet saying?

```bash
docker exec $CP sh -c \
  'printf "\n  this is not valid yaml: [\n" >> /etc/kubernetes/manifests/kube-apiserver.yaml'
sleep 60
kubectl get nodes                                     # dead again
docker exec $CP crictl ps -a --name kube-apiserver    # nothing
docker exec $CP crictl pods --name kube-apiserver     # nothing -- not even a sandbox
```

**Nothing, and nothing.** No container, no exit code, no logs — and this time not even the sandbox that the broken image still managed to produce. The kubelet could not parse the file, so it never got as far as *attempting* anything, and every tool at Question 3's level is empty. There is no process to have an opinion, because no process was ever created and no namespace was ever set up to hold one.

(Sixty seconds, because the previous sandbox lingers for about that long before it too is torn down. The three breaks in this lesson all reward a little patience, and all three punish checking early with an answer that looks like the opposite of the truth.)

So the evidence has to be with whatever did the parsing, and that is the kubelet itself. Lesson 02 introduced systemd as the init system that starts the kubelet, and `systemctl` as the way to ask about one of its services. Systemd also *captures* every service's output into a single system journal, and **`journalctl -u <unit>`** is how you read one unit's share of it:

```bash
docker exec $CP journalctl -u kubelet --since '-2min' --no-pager | grep -i -A3 'manifest\|error' | tail -20
```

`-u kubelet` selects the unit, `--since '-2min'` limits it to the recent past, and `--no-pager` stops it trying to open an interactive pager you cannot use through `docker exec`. And there it is, repeating every twenty seconds or so:

```
"Could not process manifest file" err="/etc/kubernetes/manifests/kube-apiserver.yaml:
 couldn't parse as pod(yaml: line 139: did not find expected key), please check config file"
```

**A file, and a line number.** That is the whole answer, and no tool above this one could have given it to you — because every tool above this one was asking about a container that does not exist.

```bash
docker exec $CP cp /tmp/apiserver.good /etc/kubernetes/manifests/kube-apiserver.yaml
until kubectl get nodes 2>/dev/null; do sleep 2; done
```

And there is a third depth, between the other two, which completes the set. Break the image rather than the flags:

```bash
docker exec $CP sh -c "sed 's|\(image:.*kube-apiserver:\).*|\1v9.99.99|' /tmp/apiserver.good \
  > /etc/kubernetes/manifests/kube-apiserver.yaml"
sleep 45
docker exec $CP crictl ps -a --name kube-apiserver       # nothing
docker exec $CP crictl pods --name kube-apiserver        # a Ready sandbox
docker exec $CP journalctl -u kubelet --since '-1min' --no-pager \
  | grep -i 'pull\|ErrImage' | tail -5
```

Give this one the full forty-five seconds. The *old* container stays listed for a good half-minute after the break, so check too early and you will see the opposite of the point.

The file parsed perfectly, so the kubelet accepted it and got further than last time — but there is no container, because you cannot start one from an image that does not exist. **This is `ImagePullBackOff`**, and it is why that state has no logs to read: the failure happened before any process existed.

The second command is the interesting one, and it is a trap worth having sprung on you deliberately. A **sandbox** — the Pod's network namespace, the thing Act V taught you the `pause` container holds — was created, and it is `Ready`. So `crictl pods` reports a healthy-looking Pod with nothing inside it. Look only there and you would conclude the Pod is fine.

```bash
docker exec $CP cp /tmp/apiserver.good /etc/kubernetes/manifests/kube-apiserver.yaml
until kubectl get nodes 2>/dev/null; do sleep 2; done
```

Question 4 is also where you go for a node stuck `NotReady`, and the shape is the same: the kubelet on *that* node is the thing with the opinion, so that is where you read. A node goes `NotReady` because its kubelet stopped reporting, and the two things it most often has to say are that the container runtime is unreachable or that it cannot reach the API server — the second of which will look, from your laptop, exactly like a network problem.

### Question 5 — what is on the disk?

The floor. Everything here works with no cluster, no runtime, and no kubelet, which is why it is both last and the most reliable:

```bash
docker exec $CP ls /etc/kubernetes/manifests/
docker exec $CP kubeadm certs check-expiration | head -8
docker exec $CP df -h /var/lib/etcd /var
```

Three checks, and each catches a whole class of failure that makes everything above look broken at once.

**Are all four manifests there?** A missing file is a missing component, and lesson 03 showed you exactly how quietly that presents — a cluster with no scheduler looks perfectly healthy until something needs placing. This is also the one to run when a colleague "just tried something".

**Have the certificates expired?** The lesson-04 failure: every component fails to talk to every other component at the same moment, which looks like a catastrophe and is a date.

**Is the disk full?** etcd is the one component with durable state, and when it runs out of room it stops accepting writes and raises an **alarm** — a flag it sets on itself, which you can read with the same three certificates you used in the first lesson of this act:

```bash
etcd() {
  kubectl -n kube-system exec etcd-$CP -- etcdctl \
    --cacert /etc/kubernetes/pki/etcd/ca.crt \
    --cert   /etc/kubernetes/pki/etcd/server.crt \
    --key    /etc/kubernetes/pki/etcd/server.key "$@"
}
etcd alarm list
etcd --write-out=table endpoint status
```

(The same function as lesson 01, for the same reason — a variable holding a command does not word-split in `zsh`.)

The first prints **absolutely nothing** on a healthy cluster — no header, no "no alarms found", just an empty line and exit 0. That is the good answer, and it is worth knowing in advance because it looks exactly like a command that failed. The second gives you something to read: a `DB SIZE`, an `IN USE`, a `QUOTA`, and an `ERRORS` column that is empty here and is where an alarm would appear.

A `NOSPACE` alarm is the explanation for the most confusing symptom a cluster can present: **reads work perfectly and every single write fails.** `kubectl get` is fine, `kubectl apply` is not, no component is down, and nothing in `kubectl get events` is illuminating because recording an event is itself a write. Two commands — `df` and `alarm list` — turn that into a disk you need to grow.

(These are Question 5 by dependency but they do need a live etcd, since `alarm list` is a *client* operation in the sense lesson 05 established. If etcd itself is not running, `df` is what you have, and it is enough.)

> **Check yourself —** A colleague reports that `kubectl get pods` hangs and then times out, and that this started after they "edited a manifest to add a flag." Walk your five questions and say what each one would show if (a) the flag was bogus, versus (b) the edit left the file unparseable. Then say which single command distinguishes the two fastest.

<details>
<summary>Answer</summary>

Question 1 is identical in both cases — the API server does not answer, and you learn nothing except that you must descend. Question 2 is unavailable in both, for the same reason. So the first two questions cannot tell these apart, which is exactly why you do not stop there.

**Question 3 is the discriminator, and it is one command:** `crictl ps -a --name kube-apiserver`.

With a bogus flag the file parsed, so the kubelet created a container, so there is a container to see — `Exited`, recent, with a climbing `ATTEMPT`. `crictl logs` on it hands you the binary's own one-line complaint. The process ran and had an opinion.

With unparseable YAML there is no container, because nothing was ever created. An empty result there is not the tool failing, it is the answer: the failure happened *before* any process existed, so go to whatever did the parsing — Question 4, `journalctl -u kubelet`, which names the file and the line.

And if you want to be certain rather than merely probably right, `crictl pods --name kube-apiserver` separates them again, because it distinguishes a case `crictl ps -a` cannot. A **missing image** also produces no container — but it does produce a `Ready` sandbox, because the file parsed and the kubelet got as far as building the Pod's network namespace before the pull failed. Unparseable YAML produces neither. So: sandbox and no container means the image; no sandbox at all means the file.

The general rule worth keeping: **the evidence lives at the lowest layer that still got far enough to have an opinion.** A process that started and exited leaves logs. A pull that failed leaves a namespace and a journal line. A file that would not parse leaves only a complaint from whatever declined to read it. Empty output at one layer is a pointer to the layer below, never an absence of information.

</details>

<!-- figure -->

```
   ONE FILE, THREE DEPTHS -- measured by HOW FAR DOWN THE STACK IT GOT

                        unparseable YAML    missing IMAGE      bad FLAG
                        -----------------   ---------------    ---------------
   reached the kubelet?  parse FAILED        parsed             parsed
   crictl pods (sandbox) nothing             READY              READY
   crictl ps -a (ctr)    nothing             nothing            EXITED, ATTEMPT++
   crictl logs           -- no container --  -- no container --  "unknown flag: ..."
   journalctl -u kubelet "couldn't parse     "Failed to pull    "CrashLoopBackOff,
                          as pod(yaml:        image ..."         back-off 20s -> 40s"
                          line 139 ...)"
   seen from kubectl     no Pod at all       ImagePullBackOff   CrashLoopBackOff

   ONLY the middle column of evidence -- a container that ran -- is readable with
   crictl logs. the other two are JOURNAL-ONLY. that is the argument for Question 4.

   evidence lives at the LOWEST LAYER THAT GOT FAR ENOUGH TO HAVE AN OPINION.
   empty output is a pointer downward, not an absence of information.
   and a READY SANDBOX with no container is a Pod that looks fine and is not.

   AND THE THREE THAT BREAK EVERYTHING AT ONCE  (Question 5, needs nothing)
     a missing manifest ....... a silently absent component
     expired certificates ..... every component fails at the same instant
     a full disk .............. etcd goes read-only: reads fine, all writes fail
```

**Cleanup** — confirm you are back where you started:

```bash
docker exec $CP ls /etc/kubernetes/manifests/     # all four
docker exec $CP rm -f /tmp/apiserver.good
kubectl get nodes                                                  # both Ready
kubectl -n kube-system get pods                                    # all Running
```

> **You understand this when you can** say what each of the five questions needs to be working before it can answer, and why that ordering guarantees you reach ground — and why a silent tool means *descend* rather than *pass*; explain why `logs --previous` is the right log for a restarting component and why `ImagePullBackOff` has no logs to read at all, having caused both; and given a control-plane component that will not start, use one `crictl ps -a` to decide whether the evidence is in `crictl logs` or in `journalctl -u kubelet`, and say what an empty result at each layer tells you.

**Which raises:** you can now operate a cluster below `kubectl` — start it, break it, restore it, and find out why it will not start. But every object you have used to do that was one the cluster came with. You have never made Kubernetes run *your* software: not a Deployment you designed, not storage that outlives a Pod, not configuration kept out of the image. Act V taught you how traffic reaches a workload and this act taught you what runs it. What have you still never said about the workload itself?

That question is genuinely open — this is the last written page of the course, and the act it points at does not exist yet. [The journey map](../../JOURNEY-MAP.md) is where the road ahead is planned, including which parts of it are built. This act is also still missing the three pages every other act carries: a `test-yourself`, a set of `diagnose` drills, and an `in-the-wild`.

---

← Prev: **[Taking a node out of service](07-node-maintenance.md)** · ↑ **[Act VI overview](README.md)** · Next: **[Act VI overview](README.md)** →
