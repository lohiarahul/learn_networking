# `local` — no kernel interface at all

**What you see in `strace`:** ordinary file reads. No socket, no netlink, no probe.

Seven tools that are here for one reason: **they read or reshape bytes another program already
produced**, with no kernel call of their own. Saying so explicitly is the point of this page. A `local`
tool can never tell you anything its input did not already contain — which for six of them means they
cannot be the source of a networking answer at all, only the thing that makes another tool's answer
readable.

[`jq`](jq.md) · [`xxd`](xxd.md) ·
[`etcdutl`](etcdutl.md) · [`kustomize`](kustomize.md) ·
[`kube-bench`](kube-bench.md) · [`journalctl`](journalctl.md) · `umoci`

`journalctl` is the row that tests this page's own definition, and passes it. It looks like a daemon
client — its sibling `systemctl` is one — and it is not: `journalctl --file <a copy of the journal>`
returns the same field-filtered records with systemd never consulted, and a running `journalctl -f`
holds no socket at all in `/proc/<pid>/fd/`. It reads a file `systemd-journald` wrote. So it is the one
`local` tool that *is* a source of a diagnostic answer — not because it reaches into the machine, but
because the bytes it was handed are the machine's own record of itself. Everything it cannot tell you is
something the writer did not record, or has already discarded, which is exactly why
[Act VI 02b](../../../networking-fundamentals/act-6-control-plane/02b-what-starts-the-kubelet.md) has
the reader find out where the store lives before trusting an empty result.

`umoci` is the one bare name: it flattens an OCI image layout into the bundle `runc` reads, with no
page of its own, taught in [Act IV](../../../networking-fundamentals/act-4-one-pretends-many/05-who-does-this-for-you.md)
where that bundle is what gets run.

---

## Why `jq` earns a place

Because it changes how you use every other interface. `ip`, `kubectl` and `docker` all emit JSON, and
JSON turns "parse this text with `awk` and hope the column order never changes" into a field lookup:

```bash
ip -j addr | jq '.[].addr_info[].local'
kubectl get pods -o json | jq -r '.items[].status.podIP'
docker inspect <c> | jq '.[0].NetworkSettings'
```

The habit worth forming is `-j` first, `jq` second — not `grep` and `cut`.

## Why `xxd` earns a place

Because the text view lies more often than people expect. A certificate, a Kubernetes Secret and a
`/proc` file all have a byte-level truth that the rendered form hides:

```bash
base64 -d <<< '<value>' | xxd            # what is really in that Secret
openssl x509 -in cert.pem -outform der | xxd | head
```

## The two offline tools, and why offline matters

[`etcdutl`](etcdutl.md) and [`kustomize`](kustomize.md) are here because
they do their whole job with **no server involved**, which makes them safe in situations where their
online counterparts are not:

- `etcdutl snapshot restore` works on a snapshot file with etcd stopped — which is exactly when you
  need it. `etcdutl snapshot status snap.db -w table` verifies a backup *before* you trust it.
- `kustomize build overlays/prod` renders final manifests with no cluster and no templating language.
  Diff that against `kubectl get -o yaml` and you have the difference between intent and reality
  without changing anything.

`kube-bench` is the awkward member: it reads local node config files, which is `local`, but also
queries the API for some checks. It is filed here because the thing it is uniquely good at — scoring
`/etc/kubernetes/*` against CIS, file by file — needs no cluster at all.

---

## What `local` can never tell you

**Anything whatsoever about your machine.** This is not a limitation to work around; it is the
definition. If a `local` tool gave you a surprising answer about the network, the surprise came from
the tool that produced its input.

The practical form of this: when a `jq` filter returns nothing, check whether the upstream command
returned what you assumed, before debugging the filter. Most `jq` bugs are actually `ip -j` or
`kubectl -o json` returning a different shape than expected.

## What streams here

**Nothing.** `jq --stream` parses a large document incrementally; that is not the same as observing
events. If you need to watch something happen, the interface you want is
[`netlink`](../netlink/README.md), [`packet`](../packet/README.md), [`probe`](../probe/README.md) or [`httpapi`](../httpapi/README.md).

---

Taught in: [Act VIII in the wild](../../../networking-fundamentals/act-8-trust/in-the-wild.md) ·
[hashing](../../../networking-fundamentals/act-8-trust/01-hashing.md) ·
[etcd backup and restore](../../../networking-fundamentals/act-6-control-plane/05-etcd-backup-and-restore.md) ·
[shipping a set of objects](../../../networking-fundamentals/act-7-workloads/08-shipping-a-set-of-objects.md)

Next: [`httpapi`](../httpapi/README.md), which produces most of the JSON these tools reshape.
