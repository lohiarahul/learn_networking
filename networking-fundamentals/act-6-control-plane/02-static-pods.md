# Static pods — where the control plane lives

The API server answered every request in the last lesson, so it is a process, on a machine, that someone started. Go and find out who started it.

```bash
kubectl -n kube-system get pods -l tier=control-plane
```

It is a Pod. So are the scheduler, the controller manager, and etcd. Which should stop you, because you now know exactly what a Pod is: a record at `/registry/pods/kube-system/kube-apiserver-...`, in a store that only the API server can read.

### How does the API server start itself?

It cannot. That is the whole problem, and it is worth feeling before you get the answer.

Follow the ordinary path a Pod takes. Something writes a Pod object to the API server; the scheduler watches for unassigned Pods and picks a node; the kubelet on that node watches for Pods assigned to it and starts the containers. Every step needs the API server to already be running.

So the API server would have to exist in order to be told to exist. And the scheduler — also a Pod — would have to be running in order to schedule *itself*. Try to construct a boot order out of that and you cannot; every arrow points backwards.

Which means the ordinary path is not the one they take. **There must be a way to start a Pod without asking the API server anything** — and, given this course, that way is going to be a file.

### The one component that starts without being told

The kubelet is not a Pod. It is a plain background service on the node, started at boot by the init system — `systemd`, on these nodes as on most Linux hosts — and holding no cluster state at all. That is the whole escape from the deadlock, and it is enough for this lesson; [the next one](02b-what-starts-the-kubelet.md) opens the file systemd starts it from, because the rest of this act ends up depending on what is in it.

And the kubelet takes a config file. One field in it breaks the deadlock:

```bash
docker exec netlab-control-plane grep -i staticpod /var/lib/kubelet/config.yaml
```

`staticPodPath: /etc/kubernetes/manifests`. The kubelet reads that directory off local disk and runs whatever Pod manifests it finds there — no API server, no scheduler, no etcd. Look:

```bash
docker exec netlab-control-plane ls -la /etc/kubernetes/manifests/
```

```
etcd.yaml
kube-apiserver.yaml
kube-controller-manager.yaml
kube-scheduler.yaml
```

Four files. **That is the entire control plane, as four Pod manifests in a directory.** The kubelet starts them because they are on its disk, and it would start them on a machine with no cluster to belong to.

A Pod started this way is a **static Pod**, and it has one property that matters more than any other.

### What happens if you delete a static pod?

> **Predict first —** a static Pod appears in `kubectl get pods`, so `kubectl delete pod` should work on it. Run it and predict what `kubectl get pods` shows fifteen seconds later.

```bash
kubectl -n kube-system delete pod kube-scheduler-netlab-control-plane
sleep 15
kubectl -n kube-system get pods -l component=kube-scheduler
```

It comes straight back — same name, an age of a few seconds. (Look sooner and you may catch it `Pending` for a moment; that is the record being re-filed, not the component restarting.) And nothing "recovered" it, because nothing was ever managing it.

In fact the container never went anywhere, and you can prove it. `crictl` is the node's own container CLI — the low-level tool the kubelet itself talks to, below `kubectl` entirely:

```bash
docker exec netlab-control-plane crictl ps --name kube-scheduler
```

The `CREATED` column reads minutes ago, and `ATTEMPT` has not incremented, while `kubectl` reports an age of seconds. Two tools, two different numbers, and the disagreement is the lesson: one is describing a container, the other a record.

Here is why it appeared in `kubectl get pods` in the first place. Once the API server is up, the kubelet **registers** its static Pods into it, so that you can see them. That record is a report, not an instruction — and you just deleted the report. The container never noticed, and the kubelet filed it again. **The record follows the container, not the other way round.**

**A static Pod cannot be deleted with `kubectl`.** The API server is downstream of the file. This is not an edge case to file away — it is the single most common way people lose time on a broken control plane, trying to restart a component through an API that has no authority over it.

The file is the authority. So to stop the scheduler, move its file:

```bash
docker exec netlab-control-plane sh -c 'mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/'
sleep 10
kubectl -n kube-system get pods -l component=kube-scheduler      # gone, and staying gone
```

Now put it back, and watch the same mechanism run forwards:

```bash
docker exec netlab-control-plane sh -c 'mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/'
sleep 20
kubectl -n kube-system get pods -l component=kube-scheduler      # back
```

The kubelet is watching that directory. Add a file, get a Pod; remove it, lose one. It is the same watch-and-converge shape you have now seen three times — in a Gateway controller provisioning an NGINX, in kube-proxy rewriting iptables — except the thing being watched is a directory rather than an API object.

### Why is one of those four different from the others?

Three of those manifests describe processes that can be killed and restarted with no consequence beyond a pause. Look at the fourth:

```bash
docker exec netlab-control-plane grep -A8 '^  volumes:' /etc/kubernetes/manifests/etcd.yaml
docker exec netlab-control-plane ls /var/lib/etcd/member/
```

```
  volumes:
  - hostPath:
      path: /etc/kubernetes/pki/etcd
      type: DirectoryOrCreate
    name: etcd-certs
  - hostPath:
      path: /var/lib/etcd
      type: DirectoryOrCreate
    name: etcd-data
```

`etcd.yaml` mounts a **hostPath** at `/var/lib/etcd`. The API server, scheduler and controller manager mount only certificates and config — nothing they cannot get again. etcd mounts a directory of write-ahead logs and snapshots on the node's real disk, and that directory is the few hundred keys you read in the last lesson.

So the asymmetry from that lesson has a physical location now. Delete the API server's container and you get an outage. Delete `/var/lib/etcd` and you have deleted the cluster — every Pod, Secret and Service, and every kind you have yet to meet — with nothing anywhere else to rebuild it from.

> **Check yourself —** You need to change a flag on the API server. Someone suggests `kubectl edit pod kube-apiserver-... -n kube-system`. Why will that not work, and what does the right move risk?

<details>
<summary>Answer</summary>

`kubectl edit` writes to the record, and the record is downstream of the file. The kubelet would keep running the container the manifest describes; at best your edit is ignored, at worst it is rejected because most Pod fields are immutable. Nothing you do through the API can change a static Pod.

The right move is to edit `/etc/kubernetes/manifests/kube-apiserver.yaml` on the node, which the kubelet notices and acts on within seconds. The risk is precisely that immediacy plus the identity of the component: a typo in that file means the API server does not come back, and **the tool you would normally use to investigate is the API server**. `kubectl` stops answering entirely.

Which is why the habit is to copy the file somewhere outside `/etc/kubernetes/manifests` before touching it — outside, because a stray `.yaml` backup left *inside* that directory is itself a manifest the kubelet will try to run. And why the next lesson's diagnostic tools are the ones that work with no API server at all.

</details>

<!-- figure -->

```
   THE BOOT ORDER PROBLEM                 HOW IT IS BROKEN

   Pod needs API server                   kubelet          (systemd unit, needs nothing)
   API server is a Pod                      | reads
   scheduler assigns Pods                 /etc/kubernetes/manifests/   <- local disk
   scheduler is a Pod                       |  etcd.yaml
        ^                |                  |  kube-apiserver.yaml
        |________________|                  |  kube-controller-manager.yaml
         every arrow points back            |  kube-scheduler.yaml
                                            v
                                     containers start, no API needed
                                            |
                                            v
                                     kubelet REGISTERS them into the
                                     API server once it is up
                                     (so kubectl can see, but not command, them)

   only etcd.yaml mounts hostPath /var/lib/etcd  <- the cluster's only durable bytes
```

**Before you close this page**, confirm you put the scheduler back. A control plane missing it looks perfectly healthy until something needs placing:

```bash
docker exec netlab-control-plane ls /etc/kubernetes/manifests/     # all four
```

> **You understand this when you can** explain the circular dependency that makes an ordinary Pod an impossible way to start a control plane, and name the one component that escapes it and why; say what `staticPodPath` does and why `kubectl delete pod` on a static Pod appears to work and changes nothing; and say which of the four manifests you must never lose the data directory of, and what you would have left if you did.

**Which raises:** you just stopped the scheduler for ten seconds and nothing appeared to break, because nothing needed scheduling in that window. What exactly would have failed — and what else is quietly holding the cluster together by watching the store you read in the last lesson?

---

← Prev: **[The API server is a filesystem](01-the-api-server-is-a-filesystem.md)** · ↑ **[Act VI overview](README.md)** · Next: **[What starts the kubelet](02b-what-starts-the-kubelet.md)** →
