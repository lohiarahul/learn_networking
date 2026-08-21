# Act VI — Test yourself

> Do this **after** working through all the lessons in [the act overview](README.md). Answer each one out loud or on paper *before* you open its answer — the attempt is what makes it stick, far more than re-reading. A wrong attempt followed by the right answer beats a confident skim every time.

> **Question 1 —** A Pod is running on a node. You have a root shell on that node. Explain why you cannot find the Pod's *object* anywhere on its disk, and say what `kubectl get pod` is actually doing instead.

<details>
<summary>Answer</summary>

The node holds the Pod's **consequences** — a network namespace, a veth, mounted volumes under `/var/lib/kubelet/pods/<uid>/`, a running process — but never the record. The kubelet was *told* about that Pod; it never owned it.

`kubectl get pod` is a `GET` on a path: `/api/v1/namespaces/<ns>/pods/<name>`. The API server answers by decoding a value out of etcd, which is a different machine's concern entirely. This is Act I's creed in its next form — "everything is a file" was always a claim about the **interface**, not a claim that bytes exist anywhere.

</details>

> **Question 2 —** What is the literal etcd key for a Pod named `db-0` in namespace `default`? Name two kinds whose keys do *not* follow that pattern.

<details>
<summary>Answer</summary>

`/registry/pods/default/db-0` — your `kubectl` arguments, in order, as a path.

Two exceptions: a **Service** splits into `/registry/services/specs/<ns>/<name>` and a sibling `/registry/services/endpoints/<ns>/<name>`, which is Act V's Service-and-EndpointSlice division showing through at the storage layer. And a **node** lives under `/registry/minions/<name>` — a fossil of an older word for a worker, still load-bearing in the store years after it left the API.

</details>

> **Question 3 —** The API server is a Pod. The scheduler, which assigns Pods to nodes, is also a Pod. Construct the boot order. When you fail, say precisely which component escapes the problem and why it can.

<details>
<summary>Answer</summary>

You cannot: every arrow points backwards. A Pod needs the API server, the API server is a Pod, Pods need the scheduler, the scheduler is a Pod.

The **kubelet** escapes it, because it is not a Pod. It is an ordinary service started at boot by systemd, holding no cluster state, and one field in its config breaks the deadlock: `staticPodPath: /etc/kubernetes/manifests`. It reads that directory off local disk and runs whatever Pod manifests it finds, with no API server, no scheduler and no etcd — and would do so on a machine with no cluster to belong to.

</details>

> **Question 4 —** You run `kubectl delete pod kube-scheduler-<node> -n kube-system`. It succeeds, and seconds later the Pod is listed again. What did you delete, what recovered it, and how would you *actually* stop the scheduler?

<details>
<summary>Answer</summary>

You deleted a **record**, and nothing recovered anything — because nothing was ever managing it. The container never noticed; `crictl` will show it still running from before your delete, with its restart count unmoved.

Once the API server is up, the kubelet **registers** its static Pods into it so you can see them. That registration is a report, not an instruction. You deleted the report and the kubelet filed it again. The record follows the container, never the reverse.

To actually stop it, move the file: `mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/`. The file is the authority, and the API server is downstream of it.

</details>

> **Question 5 —** You stop the controller manager, then delete one Pod of a three-replica Deployment. `kubectl get pods` shows two. What does `kubectl get deployment` show in its `READY` column, and what does your answer tell you about the nature of `status`?

<details>
<summary>Answer</summary>

**`3/3`** — and it is a lie that will not correct itself.

`READY` does not count anything when you ask for it. It reads `status.readyReplicas`, a field in the store, and the process that writes that field is the controller manager you just stopped. So you are reading the last thing it noticed before it died.

Which is the sharper half of the lesson: a stopped controller does not only stop *acting*, it stops **knowing** — and it does not say so. `status` is a note some controller left behind, exactly as much a stored document as `spec`, and just as capable of being stale. This is also why `kubectl wait --for=condition=Available` returns instantly and successfully here: a tool that waits on a field cannot outrun the controller that writes the field.

</details>

> **Question 6 —** A Pod has been `Pending` for ten minutes. Which two questions separate "no loop is placing it" from "a loop tried and could not"? Name the single field and the single piece of output that answer them.

<details>
<summary>Answer</summary>

Is `spec.nodeName` empty, and is the scheduler running?

That one field is the entire handoff: the scheduler watches for Pods without it, evaluates nodes, and writes one value; the kubelet on each node watches for Pods whose value matches itself. Neither ever speaks to the other.

The decisive output is the Pod's **events**. `Events: <none>` means nothing ever looked at it — a missing process. An events list containing a complaint means the scheduler looked and refused, which is a conversation about your requirements (not enough CPU anywhere, a taint you cannot tolerate) rather than a missing component. And if `nodeName` *is* set while the Pod is still `Pending`, placement already succeeded and you are asking the wrong component — the problem is the kubelet on that node.

</details>

> **Question 7 —** Your `kubectl` presented no password. Where does the API server get your username and your group, and what makes it believe either?

<details>
<summary>Answer</summary>

From two fields of the client certificate in your kubeconfig: the **`CN`** is the username, the **`O`** is the group. On a current kubeadm cluster those read `CN=kubernetes-admin` and `O=kubeadm:cluster-admins`.

It believes them because of the **issuer**: `CN=kubernetes`, the cluster's own CA at `/etc/kubernetes/pki/ca.crt`. That is the whole authentication story — a signed statement, from an authority the server trusts.

Worth keeping separate: the certificate establishes *who you are*, and something else entirely decides what you may do. The group in your certificate is matched by a `ClusterRoleBinding` — an object, in the store, which you can go and read.

</details>

> **Question 8 —** Why is `ca.key` the most dangerous file on a control-plane node, and why can nothing revoke a credential minted with it?

<details>
<summary>Answer</summary>

Anyone holding it can mint a certificate claiming any username and any group, and become a cluster administrator. It is why keys are `600` and root-owned while certificates are world-readable.

Nothing revokes it because of what the API server actually checks: a signature, and two dates. It consults no list of cancelled certificates, so there is nowhere to write *this one is void*. The credential is good until `notAfter`, and the only remedies are drastic (re-issue the CA, invalidating everything) or slow (wait). This is why certificate *lifetime* is an operational concern rather than a detail.

</details>

> **Question 9 —** A cluster's certificates expired overnight and `kubectl` returns a TLS error for every command. Which of your tools still work, and in what order do you use them?

<details>
<summary>Answer</summary>

Everything that reads files, which is the entire toolkit here.

`kubeadm certs check-expiration` on the node needs no API server — it reads `/etc/kubernetes/pki/` off the disk and names exactly what lapsed. (You can prove that claim by moving the API server's manifest away and running it: the full table still prints, exit 0.) Then `kubeadm certs renew all` rewrites them, also with no cluster.

Then the static-Pod mechanism does the rest: the components read their certificates **at startup** and hold them in memory, so new files change nothing until they restart — move the four manifests out and back. Finally your own credential: `admin.conf` holds a certificate that was also renewed, so copy it to `~/.kube/config` again.

Notice the constraint underneath: every step had to work with no API server. That is the whole reason this act insists you can operate below `kubectl`.

</details>

> **Question 10 —** Name the one question that decides whether an etcd operation needs `etcdctl` or `etcdutl`, and say where either binary actually lives.

<details>
<summary>Answer</summary>

**Does it need a running server?** `etcdctl` is a client: it works by making an authenticated request to a live etcd, so it needs the three certificates. `etcdutl` is a utility: it works on files, so it needs nothing. Taking a snapshot reads a live cluster, so it is `etcdctl`. Inspecting or restoring one touches only a file, so it is `etcdutl` — and etcd 3.6 removed those subcommands from `etcdctl` precisely along that line.

Neither binary is on the node. They ship **inside the etcd image**, which is why you reach them two ways: `kubectl exec` into the running etcd Pod while etcd is up, and `docker run` against a copied file when it is not. That second route is not a convenience — a restore happens with etcd stopped, so it is the only route that exists.

</details>

> **Question 11 —** You delete `/var/lib/etcd` and let the control plane restart. Your own `kubectl get nodes` fails. Does it fail with a connection error or something else, and why?

<details>
<summary>Answer</summary>

**`Forbidden`** — not a connection error. And `kubectl auth whoami` still works, reporting you correctly as `kubernetes-admin` in `kubeadm:cluster-admins`.

Your authentication is untouched, because it is a certificate signed by a CA that lives in `/etc/kubernetes/pki/` on the node's disk, which you did not delete. What you destroyed was the **`ClusterRoleBinding`** that authorised that group — an object, which was in the store. So the API server knows exactly who you are and will not let you list a node.

`super-admin.conf` still works completely, and that is the point of it: `O=system:masters` is wired into the API server itself rather than into an object you can delete. Every note about that file being for emergencies is describing this one.

</details>

> **Question 12 —** You restore a snapshot. A Deployment created *after* that snapshot vanishes from the API. What is its container doing, and for how long?

<details>
<summary>Answer</summary>

Still running, still serving traffic, indefinitely — with no Deployment, no ReplicaSet and no Pod anywhere in the cluster.

A watch is a stream of changes *since a revision*, and a restore moves the store's revision **backwards**. So the kubelet is waiting on a revision that is now in the future, no change ever arrives, and it goes on acting from the picture it held in memory. Nothing is broken and nothing has noticed there is anything to notice.

`systemctl restart kubelet` forces a cold list; the orphan is reaped in seconds, while workloads that *are* in the restored store are untouched. Which is the honest shape of the technique: **a restore is an assertion about what the cluster is, not a rewind.** Between the assertion and something looking, you have a cluster whose beliefs and reality disagree — and you have watched that gap serve HTTP.

</details>

> **Question 13 —** No component in Kubernetes calls another. Given only that, derive why the API server's version is the one everything else is measured against.

<details>
<summary>Answer</summary>

Every component talks to the API server and never to a peer, so there is no A-to-B protocol to be compatible about. What varies across an upgrade is whether the **object** a component asks for or sends still exists in the form it expects.

And exactly one component has authority over that: the one that decodes stored bytes, applies defaults, validates, and writes them back. Lesson 01 established etcd is the only store; lesson 04 showed only the API server holds a credential into it (`apiserver-etcd-client`). Everything else is a client.

Hence: nothing may be **newer** than the API server, because a newer component is built against an API this server does not serve yet. Older is fine, deliberately, for several releases — that grace is what makes a rolling upgrade possible at all.

</details>

> **Question 14 —** `kubectl` is allowed to be one version *newer* than the API server, while a controller is not. Why the difference?

<details>
<summary>Answer</summary>

Because `kubectl` discovers what the server supports before it acts, and a human is watching when it goes wrong. A controller in a reconciliation loop has neither property — it acts unattended, repeatedly, on whatever it was built to expect.

Worth adding: the failure mode for a skewed `kubectl` is soft rather than loud. It mostly works, then quietly misrenders or omits a field. Which makes it the worst thing to have wrong while debugging, because it produces confident wrong answers instead of errors. Fix your witness before you take testimony.

</details>

> **Question 15 —** Where does each of the five processes on a control-plane node record its version? Which one cannot be changed by editing a file, and what does that imply about which half of an upgrade is the hard half?

<details>
<summary>Answer</summary>

Four of them record it as an `image:` tag inside `/etc/kubernetes/manifests/*.yaml` — etcd, the API server, the controller manager, the scheduler. Change the string and the kubelet notices the file and starts a different image. That is essentially all `kubeadm upgrade apply` does to them.

The **kubelet** cannot work that way, because it is the process *reading* that directory. It is a binary on the node's filesystem started by systemd, so changing its version means replacing the installed binary and restarting the service. No manifest, no controller watching on your behalf.

So the control-plane half is four string edits on one node, each reversible in seconds, on components with no state to lose. The node half touches every machine you have, needs the work moved off each one first, and involves a restart during which that node is unmanaged. **The control plane is the part that sounds frightening; the nodes are the part that takes the week.**

</details>

> **Question 16 —** What does `cordon` write, and what enforces it? Then say why `drain` is a fundamentally different kind of operation.

<details>
<summary>Answer</summary>

`cordon` writes **one field and nothing else**: `spec.unschedulable: true`. You can reproduce it exactly with a bare `kubectl patch`, which is worth having done once, because it means you can never be stuck for want of the subcommand.

Two independent things then read that field, and one of them is easy to mis-credit. The **scheduler** consults it when placing Pods — and `kubectl get nodes` renders `SchedulingDisabled` from it directly. Separately, a **controller inside the controller manager** reconciles it into a `node.kubernetes.io/unschedulable:NoSchedule` taint, so that everything reasoning in terms of taints sees it too. Stop the controller manager and cordon a node: the field is set, `SchedulingDisabled` displays, and the taint never appears. So `kubectl` did not write that taint — a loop did, and it is lesson 03 again.

`drain` is not a field and not a controller. It is a **loop running inside `kubectl` on your machine**: it lists the Pods on the node and `POST`s to each one's `eviction` subresource in turn, waiting for each to go. There is no drain object, no drain controller, and no record anywhere that a drain is happening. Press Ctrl-C and it stops where it was — some Pods evicted, some not — and nothing in the cluster will finish the job, because nothing ever knew there was a job.

</details>

> **Question 17 —** A PodDisruptionBudget can block a drain. Name what it constrains, three things it does not, and how you would tell a drain blocked by one from a drain that is merely waiting.

<details>
<summary>Answer</summary>

It constrains **eviction** — how much of an application may be voluntarily missing at once.

It does not constrain a node failing, a `kubectl delete pod`, or a kubelet dying. None of those ask permission. A PDB is a contract about *planned* disruption only, and reading it as a general availability guarantee is the usual way to be disappointed by one.

You tell them apart by whether the terminal is talking. `kubectl` treats a rejected eviction as *not yet* rather than *no* and retries every five seconds, printing `Cannot evict pod as it would violate the pod's disruption budget` each time — so **a PDB block is loud and names itself**, a dozen times a minute. The other kind of stuck is silent: the eviction was accepted and the Pod will not finish terminating, because of a long grace period or a container that ignores the signal to stop.

Which is also why `--timeout` matters — not for the loud case, which diagnoses itself, but for the silent one, where a drain that will never finish is genuinely indistinguishable from one that is nearly done.

</details>

> **Question 18 —** You are diagnosing a control plane that will not answer. Give the five questions in order, and say what each one *needs to be working* before it can answer at all.

<details>
<summary>Answer</summary>

1. **Does the API server answer?** `kubectl get --raw /readyz` — needs everything.
2. **What does the cluster say about itself?** events, `describe`, `logs --previous` — needs the API server.
3. **Is the container running?** `crictl ps -a`, `crictl logs` — needs only the container runtime.
4. **What is the kubelet saying?** `journalctl -u kubelet` — needs only systemd.
5. **What is on the disk?** the manifests, `kubeadm certs check-expiration`, `df` — needs nothing.

Each needs strictly less of the cluster than the one above, which is what guarantees the descent terminates: Question 5 always answers, because a disk does not need a cluster.

And note the stopping rule is the **inverse** of Act V's. There you read down and stopped at the first layer that *lied*. Here you read down and stop at the first tool that *answers* — a silent tool is not a passed check, it is an instruction to go lower.

</details>

> **Question 19 —** Two ways to break the same manifest: a flag that does not exist, and YAML that will not parse. Give the one command that tells them apart, and say what each result means.

<details>
<summary>Answer</summary>

`crictl ps -a --name kube-apiserver`.

With a bad **flag**, the file parsed, so the kubelet created a container, so there is one to see: `Exited`, with a climbing `ATTEMPT` count, and `crictl logs` on it gives you the binary's own one-line complaint. The process ran and had an opinion.

With unparseable **YAML** there is no container, because nothing was ever created. That empty result is not the tool failing — it is the answer, pointing you to whatever did the parsing: `journalctl -u kubelet`, which names the file and the line.

To be certain rather than probably right, `crictl pods` separates a third case that `crictl ps -a` cannot. A **missing image** also yields no container, but it *does* yield a `Ready` sandbox, because the file parsed and the kubelet built the Pod's network namespace before the pull failed. Bad YAML yields neither. So: sandbox but no container means the image; no sandbox at all means the file.

The general rule: **the evidence lives at the lowest layer that got far enough to have an opinion**, and empty output at one layer is a pointer to the layer below.

</details>

> **Question 20 —** A cluster where `kubectl get` works perfectly and every `kubectl apply` fails, with no component down and nothing useful in the events. What is your first hypothesis, and the two commands that confirm it?

<details>
<summary>Answer</summary>

etcd is out of disk and has raised a **`NOSPACE` alarm**, which stops it accepting writes while reads carry on as normal.

`df -h /var/lib/etcd` and `etcdctl alarm list`. Note that `alarm list` prints *absolutely nothing* on a healthy cluster — no header, no message — so it looks exactly like a command that failed; pair it with `--write-out=table endpoint status`, which shows the `DB SIZE`, the `QUOTA`, and an `ERRORS` column.

The reason events do not help is worth the detour: recording an event is itself a write. In a store that has stopped accepting writes, the cluster's own commentary is the one thing that cannot tell you what is wrong.

</details>

---

← **[Act VI overview](README.md)** · Next: **[Diagnose it — the on-call drills](diagnose.md)** →
