# How a layer is made

[Act I's container filesystem lesson](../act-1-one-machine/06b-the-container-filesystem.md) taught you
to *read* layers: `lowerdir`, `upperdir`, copy-on-write, and a whiteout that hides a file without
erasing it. It even walked you through a hypothetical — a Dockerfile that writes `secret.pem` in one
layer and `rm`s it in the next — and told you the running container would show nothing while the
secret sat, fully recoverable, one layer down. You were asked to trust that. This lesson builds exactly
that Dockerfile and unpacks it with your own hands, because a claim about layers deserves the same
proof lessons 05–06 gave `runc` and CRI.

### The problem `docker build` actually solves

`FROM`, `RUN`, `COPY` — a Dockerfile is a recipe, and each instruction has to become one immutable,
content-addressed layer, cached so an unchanged step never reruns. Building that from scratch every
time is real work: run a step in a sandbox, snapshot the filesystem delta, hash it, stack it on the
last one. Nobody wants to write that per project.

**The fix, again, is a dedicated program, not a feature bolted onto `docker`.** **BuildKit** is that
program — the daemon `docker build` has called since Docker 18.09, the same displacement you already
know from [lesson 05](05-who-does-this-for-you.md): `docker run` doesn't touch `runc` directly, and
`docker build` doesn't build anything directly either. `buildctl` is BuildKit's own client, playing the
same role `ctr` played for `containerd` — the raw tool, with nothing hidden.

```bash
apk add --no-cache buildkit buildctl
buildkitd &
```

### Build Act I's hypothetical for real

```bash
mkdir /work/build && cd /work/build
cat > Dockerfile <<'EOF'
FROM alpine:latest
RUN echo "hunter2" > /secret.txt
RUN cat /secret.txt && rm /secret.txt
CMD ["cat", "/etc/os-release"]
EOF

buildctl build --frontend dockerfile.v0 --local context=. --local dockerfile=. \
  --output type=oci,dest=out.tar
```

```
#5 [2/3] RUN echo "hunter2" > /secret.txt
#5 DONE 0.1s

#6 [3/3] RUN cat /secret.txt && rm /secret.txt
#6 0.085 hunter2
#6 DONE 0.1s

#7 exporting to oci image format
#7 exporting manifest sha256:cc9d2129b57...
```

No `docker` in this command — `buildctl` talked straight to `buildkitd`, and out came a real OCI image
layout: `blobs/`, `index.json`, `oci-layout`. Three layers went in: the base image, one for each `RUN`.

### Predict first, then peel it back

**Predict first —** you watched `RUN cat /secret.txt && rm /secret.txt` run inside the build, so the
file is gone by the time the image finishes. Act I 06b already told you what a whiteout does. Given
that, which of the following do you expect to find if you open the *raw tar* of the layer that ran the
`rm` — nothing at all, the file itself, or a marker with a name you haven't seen a real one of yet?

```bash
tar -tzvf blobs/sha256/<layer-2-digest>       # the RUN that wrote the secret
tar -xzOf blobs/sha256/<layer-2-digest> secret.txt
```

```
-rw-r--r-- 0/0    8 2026-08-30 04:35 secret.txt
hunter2
```

The secret is not a hash, not a redaction — it is the literal string `hunter2`, sitting in a layer that
was just built, before any registry or `push` is involved. Now the layer that ran the `rm`:

```bash
tar -tzvf blobs/sha256/<layer-3-digest>
```

```
---------- 0/0    0 1970-01-01 00:00 .wh.secret.txt
```

A marker, not the file, and now you have its real name: **`.wh.secret.txt`** — exactly the whiteout Act
I 06b described for `/bin/df`, this time in the layer *you* just built, with the name written out where
`docker diff`'s `D` never showed it to you. `rm` inside a `RUN` does not shrink the image. It adds a
third layer whose only content is a note saying "hide the name `secret.txt`" — and the layer holding the
actual bytes ships regardless, because nothing before this line has told the builder it may throw a
layer away.

### Confirm the running side agrees, then ask what it actually proves

**Predict first —** if the whiteout only hides the name and the bytes still ship, what should
`docker history --no-trunc` show about the two `RUN` layers' sizes — should the delete layer be
roughly the same size as the write layer, larger, or near zero?

```bash
docker load -i docker-out.tar   # skopeo copy oci:./out.tar docker-archive:docker-out.tar first
docker run --rm localbuild sh -c 'ls / | grep secret || echo "secret.txt: absent"'
docker history localbuild --no-trunc
```

```
secret.txt: absent
IMAGE      CREATED BY                                                    SIZE
<image>    CMD ["cat" "/etc/os-release"]                                 0B
<missing>  RUN /bin/sh -c cat /secret.txt && rm /secret.txt # buildkit   4.1kB
<missing>  RUN /bin/sh -c echo "hunter2" > /secret.txt # buildkit        8.19kB
```

`ls /` genuinely finds nothing — the whiteout does its job at runtime, every time, which is exactly why
this is dangerous rather than merely untidy: **the running container itself cannot show you the leak.**
And the delete layer is not near zero — 4.1kB of metadata for one whiteout marker, next to 8.19kB for
the secret it hides. `docker history` never had to unpack a single tar for you to see this. It is the
tool that prettifies the fact you just read raw — the rival Act I 06b's own `docker diff` played for a
single running container, now doing the same job across an image nobody has run yet.

> **You understand this when you can** name what a `RUN rm` inside a Dockerfile actually adds to an
> image, explain why a running container's own filesystem can never be evidence that a secret is gone,
> and read `docker history --no-trunc`'s sizes as the same signal a raw layer unpack gives you, faster.

**Kubernetes sees this as** — nothing it can fix, and everything Act X's supply-chain lesson exists to
answer instead. A cluster has no way to know a pulled image's layer 5 holds what layer 6 hid; it can
only run what it was handed. [Image scanning and signing](../act-10-cluster-security/08-what-you-shipped.md)
is the answer this act cannot give you, because the leak already happened at the moment `docker build`
returned success — the layer was already made.

---

← Prev: **[The kubelet's side](06-the-kubelets-side.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Test yourself](test-yourself.md)** →
