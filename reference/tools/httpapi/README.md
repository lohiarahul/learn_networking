# `httpapi` — asking a daemon what it intends

**What you see in `strace`:** a TLS or Unix-socket connection, then HTTP or gRPC

Twenty-two tools. Every one of them talks to *another program* — a daemon, an API server, a registry, or
the init system — and that program answers with **what it intends**, not with what the kernel did.
Acts V–XI exist largely because those two things diverge.

[`docker`](docker.md) · [`crictl`](crictl.md) ·
[`kubectl`](kubectl.md) · [`kind`](kind.md) ·
[`kubeadm`](kubeadm.md) · [`etcdctl`](etcdctl.md) ·
[`helm`](helm.md) · [`cilium`](cilium.md) ·
[`trivy`](trivy.md) · [`cosign`](cosign.md) ·
[`crane`](crane.md) · `ctr` · `containerd` · `skopeo` · `buildctl` · `buildkitd` ·
`prometheus` · `alertmanager` · `grafana` · `loki` · `logcli` ·
[`systemctl`](systemctl.md)

`systemctl` is the one whose transport is not HTTP or gRPC, and it is here anyway because the *shape*
is identical: it opens a unix socket to a daemon — `/run/systemd/private`, PID 1's own, which
`/proc/net/unix` shows live connections to — and gets back that daemon's **cached** definition of a
unit. [Act VI 02b](../../../networking-fundamentals/act-6-control-plane/02b-what-starts-the-kubelet.md)
measures that cache diverging from the file on disk, which is this interface's blind spot arriving on a
single Linux host rather than across a cluster. Its sibling `journalctl` is deliberately **not** here;
it is [`local`](../local/journalctl.md), for reasons that page gives.

Ten of the rest have no page of their own. `ctr`, `containerd`, `skopeo`,
`buildctl` and `buildkitd` are named here and taught where they are actually run —
[Act IV](../../../networking-fundamentals/act-4-one-pretends-many/05-who-does-this-for-you.md), which
builds and runs a container by hand before ever installing Docker, then
[builds an image the same way](../../../networking-fundamentals/act-4-one-pretends-many/07-how-a-layer-is-made.md)
— rather than given a roster page each, since none of the five carries enough distinct commands to
earn one on its own. `prometheus`, `alertmanager`, `grafana`, `loki` and `logcli` are the same shape,
taught where each is actually run in
[Act XI](../../../networking-fundamentals/act-11-observability/README.md): every one of them is driven
almost entirely through one or two HTTP endpoints hand-rolled with `curl`/`wget` across that act's own
lessons, and a roster page over that thin a surface would be furniture, not content.

---

## The layers, and what each one still knows when the one above breaks

This is the most useful thing to hold about the group: they form a stack, and failures cascade
downward. When one layer is silent, the layer below it still answers.

| Layer | Tool | Still works when |
|---|---|---|
| Cluster API | [`kubectl`](kubectl.md) | the API server is up |
| Node runtime | [`crictl`](crictl.md) | **the API server is down** — this is its whole reason to exist |
| Container engine | [`docker`](docker.md) | you are on a Docker host or a `kind` node |
| Between docker and the kernel | `containerd`, then `ctr` as its own client | `dockerd` is a client of this too — it is not a fallback, it is the layer everything above shares |
| Storage | [`etcdctl`](etcdctl.md) | etcd has quorum, whatever the API server thinks |
| Below all of it | [`runc`](../nsapi/runc.md), then [`netlink`](../netlink/README.md) and [`procfs`](../procfs/README.md) | always |

"`kubectl` hangs" is therefore not a diagnosis. Drop a layer: `crictl ps`, then `docker ps` on the
node, then `ss -tlnp` for whether anything is even listening.

## The self-describing trick

Two of these tools remove the need to look anything up, which is worth more than any table:

```bash
kubectl api-resources                            # every type, its short name, whether namespaced
kubectl explain pod.spec.containers --recursive   # the whole schema, from the server
kubectl get --raw /api/v1/namespaces             # the REST API underneath, directly
crictl inspectp <id>                             # the sandbox config, including its netns path
```

`kubectl explain` is generated from the server's own OpenAPI, so it is correct for *your* cluster
version rather than for whatever the docs describe.

## Reading intent against mechanism

The recurring move in Acts V–X is to ask this interface what *should* be true, then ask
[`netlink`](../netlink/README.md) or [`procfs`](../procfs/README.md) what *is*:

| Intent, from here | Mechanism, from there |
|---|---|
| `kubectl get svc` — a ClusterIP | `iptables-save -t nat \| grep KUBE-SVC` — the rules implementing it |
| `kubectl get endpointslices` — which Pods back it | `conntrack -L` — which backend a flow actually picked |
| `kubectl get networkpolicy` | `cilium policy get`, or the packet simply not arriving |
| `docker network inspect bridge` | `ip link`, `bridge fdb show` — the actual veths and MACs |

When those two disagree, the mechanism is what your traffic obeys.

---

## What `httpapi` can never tell you

**What the kernel actually did.** Every answer here is a daemon's model of the world. A Service with
healthy endpoints can still be unreachable because a rule is missing, a route is wrong, or conntrack is
full — and nothing on this interface will say so.

It also fails in a way the others do not: **the answer can be stale or refused for reasons unrelated to
networking.** Authentication, RBAC, admission webhooks and a busy API server all produce errors that
look like infrastructure problems and are not.

## What streams here

Four of them, and all four are underused:

```bash
docker events                  # container lifecycle
kubectl get pods -w            # object changes
etcdctl watch /registry/services --prefix
cilium monitor --type drop     # policy verdicts with identities, live
```

---

Taught in: [pod networking](../../../networking-fundamentals/act-5-kubernetes/02-pod-networking.md) ·
[services](../../../networking-fundamentals/act-5-kubernetes/03-services.md) ·
[static pods](../../../networking-fundamentals/act-6-control-plane/02-static-pods.md) ·
[etcd backup and restore](../../../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) ·
[what you shipped](../../../networking-fundamentals/act-10-cluster-security/08-what-you-shipped.md) ·
[who says so](../../../networking-fundamentals/act-10-cluster-security/08b-who-says-so.md)

Next: [`netlink`](../netlink/README.md) — the mechanism this interface reports intentions about.
