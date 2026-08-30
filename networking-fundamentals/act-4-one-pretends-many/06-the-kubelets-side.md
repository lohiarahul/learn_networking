# The kubelet's side

`containerd` and `ctr` gave you a working runtime with one container per call. That is not what
Kubernetes needs. A Pod is *several* containers that share one network namespace — you have not built
that yet, and neither `runc` nor `ctr` has a way to ask for it. This lesson builds the missing piece:
the contract that turns "run a container" into "run several containers that agree to share one."

### The problem a kubelet actually has

A kubelet manages Pods on one node, and it needs to talk to *some* container runtime to do it — but
Kubernetes does not ship a runtime, and it never wants to. Different clusters run `containerd`,
`CRI-O`, or others; the kubelet has to work with any of them, without a special code path per vendor.

**The fix, again, is a specification.** The **Container Runtime Interface** (CRI) is a gRPC API — two
services, `RuntimeService` and `ImageService` — that any conforming runtime implements and any kubelet
can call. Recall [Act X's seccomp lesson](../act-10-cluster-security/02-the-kernel-says-no.md): a Pod
died with `failed to create containerd task: failed to create shim task: OCI runtime create failed:
runc create failed: ...`. Read that chain again now that you own every link in it: `containerd task` is
CRI asking `containerd` to run something, `shim task` is the per-container process from
[lesson 05](05-who-does-this-for-you.md), and `runc create` is the bottom you built by hand in lessons
01–02. The kubelet never touches any of that directly. It calls CRI, and CRI calls the chain you
already own.

**Predict first —** `ctr run` accepts one image and produces one container, same as `runc`. A Pod is
several containers sharing one network namespace. Does the kubelet ask for that by calling `ctr run`
several times and gluing the results together itself, or does CRI's API have to know about "a Pod"
as a first-class thing in its own right? Given what you know about namespace lifetime from lesson 01 —
a namespace only survives as long as *something* holds it open — what problem would gluing containers
together after the fact leave unsolved?

### `crictl` — the same client role as `ctr`, for a different contract

`crictl` is to CRI what `ctr` is to `containerd`'s own API: a debugging client, not something a real
cluster runs in production, but the fastest way to see the contract with nothing else in the way.

```bash
apk add --no-cache cri-tools
containerd &
crictl version
```

```
Version:  0.1.0
RuntimeName:  containerd
RuntimeVersion:  v2.3.3
RuntimeApiVersion:  v1
```

Same daemon as lesson 05 — `crictl` is a second, independent client of it, exactly the way `docker` and
`ctr` both are. Now compare what each client can even ask for:

```bash
ctr run --help | grep -i sandbox
crictl --help | grep -i 'pod\|sandbox'
```

```
--sandbox value    Create the container in the given sandbox

   inspectp    Display the status of one or more pods
   pods        List pods
   port-forward  Forward local port to a pod
   rmp         Remove one or more pods
   run         Run a new container inside a sandbox
   runp        Run a new pod
   statsp      List pod statistics ...
   stopp       Stop one or more running pods
```

`ctr` has *one* optional flag bolted onto a fundamentally container-first tool — no way to list, stop,
or inspect a "pod" as its own thing. `crictl` has a whole second vocabulary: `runp`, `pods`, `rmp`,
`stopp`, distinct from `run`, `ps`, `rm`, `stop`. That asymmetry is the answer to the prediction. CRI
does not let you assemble a Pod from ordinary containers after the fact — it makes **the sandbox** a
first-class object with its own lifecycle, created *before* any container exists inside it. That
sandbox is the thing that answers "a namespace only survives as long as something holds it open" —
recall the pause container Act V will show you next, holding exactly this namespace for exactly that
reason.

### Watch the two-phase model force itself into view

Ask for a Pod sandbox the way a kubelet would — one RPC, before any application container exists:

```bash
cat > sandbox.json <<'EOF'
{ "metadata": { "name": "mypod", "namespace": "default", "uid": "1", "attempt": 1 } }
EOF
crictl runp sandbox.json
```

```
E0830 04:27:00 remote_runtime.go:237] "RunPodSandbox from runtime service failed" err="rpc error:
code = Unknown desc = failed to setup network for sandbox \"a7d5...\": cni plugin not initialized"
```

Read what actually failed, not just that something did: **the network**. `RunPodSandbox` tried to wire
up networking *before* it got anywhere near creating a container — proof, not assertion, that CRI
treats "give this Pod an IP" as part of building the sandbox itself, prior to and independent of what
runs inside it. That is exactly why every container in a Pod shares one IP: the address was never
attached to a container in the first place. It was attached to the sandbox, and containers join it
afterward — which is also why the error is `cni plugin not initialized` rather than anything about an
image or a process: this lab never installed a CNI plugin, because [that's Act V's job](../act-5-kubernetes/05-cni.md),
not Act IV's. You are meant to hit this wall here. Building the plugin that clears it is the next act,
not this lesson.

**Predict first —** if you gave the sandbox host networking instead — skip CNI entirely, reuse the
node's own network namespace — would `RunPodSandbox` get further? What would that trade away that a
Pod normally has?

It does get further, and immediately hits a different wall — the same nested-container mount error
[lesson 05](05-who-does-this-for-you.md) already named as an honest constraint of this lab environment,
not a CRI concept to learn. The trade for skipping CNI is real, though, and it is one Act V spends real
time on: a Pod with host networking gives up its own IP entirely and shares the node's, which is a
capability, not a networking default — the same `hostNetwork: true` Act X's Pod-encryption lesson will
later hand a Pod so it can watch the wire above every scoping rule the rest of the course builds.

> **You understand this when you can** name the two CRI services a kubelet calls, explain why `crictl`
> has `runp`/`pods`/`stopp` and `ctr` does not, and say what a `RunPodSandbox` call is responsible for
> that a plain `ctr run` never was — using the CNI failure as your evidence, not a diagram.

**Kubernetes sees this as** — the reason a kubelet never crashes because of what your application does.
`RuntimeService` and `ImageService` are the only two doors it knocks on; whatever failure happens on
the other side of that door — `containerd`'s own state, a bad image, a broken `runc` — arrives back as
one gRPC error the kubelet can log, retry, or report, without ever needing to know it was `runc`
specifically that said no.

One assertion to carry into Act V, unexplained on purpose: a real cluster's sandbox holds its namespace
open with a tiny `pause` container whose only job is to exist. You have just watched *why* something
has to — a namespace with nothing running inside it closes the moment nothing holds it open, and a
sandbox created before any application container cannot yet have one. What that something is, and how
you'd notice if it died, is the next thing you check, not this one.

---

← Prev: **[Who does this for you](05-who-does-this-for-you.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Test yourself](test-yourself.md)** →
