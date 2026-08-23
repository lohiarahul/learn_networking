# Configuration, and where a secret actually ends up

Everything you have written so far has been about the *shape* of a workload — how many, where, how to tell if it is alive. None of it was about the software's own settings, and those cannot live where you have been putting things.

They cannot live in the image, because an image is built once and runs in ten places, and rebuilding it to change a log level is absurd. Act I showed you the other reason, and it was sharper: a value baked into a layer is **still there** after a later layer deletes it, because layers never forget. That was the lesson about secrets in images, and it is the reason this lesson exists.

They cannot live in the Pod spec either, or at least not comfortably — the spec is the thing you templated, and a database password does not belong in the same file as your replica count.

So: **where does configuration live, and what changes when it changes?**

### Two ways in, and they are not equivalent

Make a ConfigMap and consume it *both* ways at once, so the difference has nowhere to hide:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata: { name: app-config }
data:
  LOG_LEVEL: "info"
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: watcher }
spec:
  replicas: 1
  selector: { matchLabels: { app: watcher } }
  template:
    metadata: { labels: { app: watcher } }
    spec:
      containers:
        - name: app
          image: busybox:1.36
          command:
            - sh
            - -c
            - 'while true; do echo "env=$LOG_LEVEL  file=$(cat /etc/config/LOG_LEVEL)"; sleep 5; done'
          env:
            - name: LOG_LEVEL
              valueFrom:
                configMapKeyRef: { name: app-config, key: LOG_LEVEL }
          volumeMounts:
            - { name: cfg, mountPath: /etc/config }
      volumes:
        - name: cfg
          configMap: { name: app-config }
EOF
kubectl wait --for=condition=Available deployment/watcher --timeout=90s
kubectl logs -l app=watcher --tail=2
```

```
env=info  file=info
```

The same value, arriving two ways: as an environment variable, and as a **file** — because a ConfigMap mounted as a volume becomes a directory, one file per key, named for the key.

```bash
kubectl exec deploy/watcher -- ls -l /etc/config/
```

> **Predict first —** you are about to change `LOG_LEVEL` to `debug` in the ConfigMap, without touching the Deployment or restarting anything. That container is printing both values every five seconds. Predict what happens to **each** of them, and how long it takes.

Start watching, then change it from another terminal:

```bash
kubectl logs -f -l app=watcher            # leave this running
```

```bash
kubectl patch configmap app-config --patch '{"data":{"LOG_LEVEL":"debug"}}'
```

Now wait, and keep watching. For about a minute nothing happens at all — 64 seconds, on this lab, timed from the moment `patch` returned. Then:

```
env=info  file=info
env=info  file=info
env=info  file=debug          <- and it stays like this
env=info  file=debug
```

**The file changed. The environment variable did not.** And it never will, for the life of that process.

That is not a bug and it is not a Kubernetes quirk. It follows from something Act I established about processes, though Act I never spelled out this consequence, so spell it out now.

Act I's first lesson defined a process as **a private address space it cannot escape**. The environment is *inside* that space: a block of `KEY=value` strings the kernel copies in when the process is created, at `exec()`, and never touches again. That is the whole argument. There is no syscall for "change another process's environment" — not because nobody wrote one, but because the address space is private in both directions, and the kernel would have to violate the guarantee it exists to make.

You have even seen the window onto it. Act I read `/proc/<pid>/environ` and noted it as an attack surface; what you were reading was that block, and note that it is exposed **read-only**. A `/proc` file you can read and not write is the kernel telling you the shape of what is possible.

So `env` is a snapshot taken at `exec()` time, and the only way to change it is to make a new process. One further consequence worth having now: every **child** process inherits that copy, which is why this matters more for secrets than for log levels.

The file, meanwhile, is a *file*. Something can rewrite it, and something does: the kubelet, on a polling interval, which is why it took about a minute rather than being instant. Look at how it does it, because the mechanism is one you already know:

```bash
kubectl exec deploy/watcher -- ls -la /etc/config/
```

Those entries are **symlinks**, into a `..data` directory that is itself a symlink to a timestamped one. The kubelet writes a whole new directory and then swings one symlink — so a process reading the file never sees a half-written value.

And these are ordinary symlinks, which is worth saying because Act I taught you a kind that is not. The `/proc/<pid>/fd/3` entries you read there were **magic** symlinks: nothing was stored, the size was always 64 whatever the target, and the kernel computed the answer on every read. Here `readlink` returns bytes that were genuinely written to a tmpfs, and the whole trick is that *rename of a symlink is atomic* — a plain filesystem guarantee, on a plain symlink. The kubelet is not using a kernel special case; it is using the oldest safe-update pattern there is.

Which gives you the rule, and it is not a preference:

- **Environment variables are immutable for the life of the process.** Changing one requires a restart, which means a rollout.
- **Mounted files change under a running process**, on the order of a minute, atomically.

So an application that re-reads its config file can be reconfigured without a restart. An application that reads env vars at startup cannot — and no amount of ConfigMap editing will change that.

### The exception that catches everyone

There is one way to mount a ConfigMap that silently gives up the hot reload:

**`subPath`** places one key as a single file inside a directory that already has other things in it — a very common need, and the reason the field exists. Mount the same ConfigMap both ways and the difference is visible before you test it:

```bash
kubectl set volumes deploy/watcher --add --name=sub -t configmap \
  --configmap-name=app-config --sub-path=LOG_LEVEL --mount-path=/etc/app/LOG_LEVEL
kubectl rollout status deploy/watcher --timeout=90s
kubectl exec deploy/watcher -- ls -la /etc/app/ /etc/config/
```

```
/etc/app/LOG_LEVEL      -rw-r--r--  1 root root  5    <- an ordinary file
/etc/config/LOG_LEVEL   lrwxrwxrwx  1 root root 16 -> ..data/LOG_LEVEL
```

**One is a plain file; the other is the symlink you just traced.** And that is the whole explanation — you can predict the rest of this section from it. The atomic swap works by repointing `..data`, which is one level *up* from the file. A `subPath` mount is not in that directory: the kubelet copied the content in at start-up, and there is no symlink to repoint.

So change the value and wait well past the interval that worked a moment ago:

```bash
kubectl patch configmap app-config -p '{"data":{"LOG_LEVEL":"trace"}}'
sleep 90
kubectl exec deploy/watcher -- cat /etc/config/LOG_LEVEL       # trace
kubectl exec deploy/watcher -- cat /etc/app/LOG_LEVEL          # still debug
```

**The directory mount followed. The `subPath` mount did not, and never will** — not slowly: still stale ten minutes later, with the container never restarted.

That is worth knowing precisely because the failure is silent and delayed: it works in testing, where you restart things constantly, and fails in production, where you expected a config change to take effect and it didn't.

The other field worth knowing here is the opposite intent:

```yaml
immutable: true      # on the ConfigMap or Secret
```

Set it and the object can never be changed, only deleted and recreated. Which sounds like a loss until you consider what the kubelet is doing on your behalf — watching every ConfigMap that every Pod on its node mounts. `immutable: true` lets it stop watching, and on a large cluster that is a meaningful reduction in load on the API server. It also removes a whole class of accident.

### Now the same thing, for secrets

```bash
kubectl create secret generic db-creds --from-literal=password=hunter2
kubectl get secret db-creds -o jsonpath='{.data.password}{"\n"}'
```

`aHVudGVyMg==`. Act V told you what that is — base64, not encryption — and Act VI proved it went further than that: in a snapshot of etcd, `grep -a hunter2` finds the value in **plaintext**, because base64 is something the API server does on the way out to you, not something the store does.

So a Secret differs from a ConfigMap in almost no mechanical way. Same two consumption paths, same hot-reload behaviour, same `immutable` field. What differs is where the value ends up — and it ends up in more places than most people count.

```bash
# --type=json again: explicit add/remove/replace operations against a path
kubectl patch deployment watcher --type=json -p='[
  {"op":"add","path":"/spec/template/spec/containers/0/env/-",
   "value":{"name":"DB_PASSWORD","valueFrom":{"secretKeyRef":{"name":"db-creds","key":"password"}}}},
  {"op":"add","path":"/spec/template/spec/volumes/-",
   "value":{"name":"sec","secret":{"secretName":"db-creds"}}},
  {"op":"add","path":"/spec/template/spec/containers/0/volumeMounts/-",
   "value":{"name":"sec","mountPath":"/etc/secret","readOnly":true}}
]'
kubectl rollout status deployment/watcher
```

**Location one — the file, and what backs it:**

```bash
kubectl exec deploy/watcher -- cat /etc/secret/password; echo
kubectl exec deploy/watcher -- sh -c 'mount | grep /etc/secret'
```

`hunter2`, decoded for you — and the mount is **`tmpfs`**. So a Secret volume is memory, not disk: the plaintext is never written to the node's filesystem, and it does not survive the node rebooting. Decide for yourself whether that is protection, and hold the answer for a few lines.

**Location two — the process's own environment:**

```bash
kubectl exec deploy/watcher -- sh -c 'tr "\0" "\n" < /proc/1/environ | grep DB_'
```

There it is, in `/proc/1/environ`, in plaintext. And that is a worse place than it looks, for a reason that has nothing to do with Kubernetes: **every child process inherits it.** A shell-out, a subprocess, a crash handler that dumps the environment into an error report, a language runtime that logs its own startup config — any of those leaks it, and none of them know they are handling a secret. A file has to be *opened* to be read; an environment variable is simply there, in everything.

**Location three — the node:**

```bash
PODUID=$(kubectl get pod -l app=watcher -o jsonpath='{.items[0].metadata.uid}')
NODE=$(kubectl get pod -l app=watcher -o jsonpath='{.items[0].spec.nodeName}')
docker exec $NODE ls /var/lib/kubelet/pods/$PODUID/volumes/kubernetes.io~secret/sec/
docker exec $NODE cat /var/lib/kubelet/pods/$PODUID/volumes/kubernetes.io~secret/sec/password; echo
```

Your password, readable with a shell on the node and no cluster credentials at all. It is `tmpfs`, so it is in that node's memory rather than on its disk — but "in memory on a machine someone has root on" is not a meaningful protection. This is the same lesson Act VI taught about `ca.key`: **a shell on a node is close to a shell in the cluster**, and the boundary you are relying on is filesystem permissions.

So, three locations for one password, and none of them encrypted:

1. **etcd**, plaintext (Act VI proved it — and a snapshot file needs no cluster to read)
2. **the node's memory**, via the kubelet's directory tree
3. **the process environment**, if you injected it that way — plus everything the process spawns

Which is the honest answer to "are Kubernetes Secrets secure?" They are not encrypted; they are a *separate object with separate access control*, which is genuinely useful — you can let someone read Deployments without reading Secrets — and is a completely different property from confidentiality. Fixing (1) is called encryption at rest and needs cluster configuration. Avoiding (3) is free and is just a choice about how you consume them.

> **Check yourself —** A colleague changes a password in a Secret and reports that "half the Pods picked it up and half didn't." Both Pods are from the same Deployment, nothing was restarted. How is that possible, and what is the general rule?

<details>
<summary>Answer</summary>

They are consuming the same Secret two different ways, or the Pods differ in age.

The likeliest version: the value is injected as an **environment variable** in one container and mounted as a **file** in another — or, more subtly, one Pod was recreated recently for an unrelated reason. A Pod created *after* the change has the new value in its environment, because env is a snapshot at process creation. A Pod created before it still has the old one, permanently. So "half picked it up" is really "half were born after the edit."

The mounted-file path updates in every Pod within about a minute, regardless of age, because it is a file being rewritten rather than memory being copied.

The general rule, and it is worth stating as a design decision rather than trivia: **if you want configuration to be changeable without a rollout, it must be a file, and your application must re-read it.** Two conditions, and people usually satisfy one. Mounting the file is not enough if the app reads it once at startup — that has exactly the same behaviour as an env var, with extra steps.

And the corollary for secrets, which is the reason rotation is hard: rotating a secret consumed as an env var *requires* restarting every consumer. If you did not plan for that, rotation is an outage, which is why it does not happen.

</details>

<!-- figure -->

```
   ONE VALUE, TWO CONSUMPTION PATHS, DIFFERENT PHYSICS

   env:  valueFrom.configMapKeyRef / secretKeyRef
     copied into the process's memory at exec(). the kernel offers NO way to
     change it afterwards. so: IMMUTABLE for the life of the process.
     changing it = a rollout. and every CHILD PROCESS inherits it.

   volumeMounts: a ConfigMap/Secret volume
     a DIRECTORY, one file per key.
     the kubelet rewrites it on a poll (~1 min) via an ATOMIC SYMLINK SWAP
       ls -la shows key -> ..data -> ..2026_..._timestamp/
       (ordinary symlinks on tmpfs -- NOT Act I's magic ones;
        the trick is only that renaming a symlink is atomic)
     so it changes UNDER a running process.
     EXCEPT with subPath -- which mounts the file directly, bypasses the
     swap, and NEVER updates. silent, and only bites in production.

   immutable: true   -> the kubelet stops watching it. real API-server load
                        win at scale, and removes a class of accident.

   WHERE A SECRET ACTUALLY IS (none of these are encrypted)
     1. etcd .................... plaintext. Act VI: grep -a on a snapshot,
                                  no cluster needed to read it.
     2. the node ................ /var/lib/kubelet/pods/<uid>/volumes/
                                    kubernetes.io~secret/<vol>/<key>
                                  tmpfs, so RAM not disk -- but a shell on
                                  the node reads it with no credentials.
     3. /proc/<pid>/environ ..... only if injected as env. plus every child
                                  process, crash dump and startup log.
   a Secret is not encryption. it is a SEPARATE OBJECT WITH SEPARATE ACCESS
   CONTROL, which is useful and is a different property entirely.
     fixing (1) = encryption at rest, needs cluster config.
     avoiding (3) = free. just mount it instead.
```

**Cleanup:**

```bash
kubectl delete deployment watcher
kubectl delete configmap app-config
kubectl delete secret db-creds
```

> **You understand this when you can** explain, from what a process *is*, why an environment variable cannot change under a running container while a mounted file can; describe the mechanism the kubelet uses to update that file without a reader ever seeing a partial value, and the one mount option that silently disables it; name the three places a Secret's plaintext exists and which of them a node shell reaches without credentials; and say what property a Secret actually provides, given that it provides no confidentiality.

**Which raises:** a mounted ConfigMap survived a config change, and a Secret volume was `tmpfs` — memory, gone the instant the Pod is. Which is fine for configuration, and useless for anything the application *writes*. Act I left you exactly this question and it has been waiting since: the writable layer dies with the container, a mount outlives it, and **who decides where the surviving path points?** Time to find out — and to discover that "survives" is not one promise.

---

← Prev: **[The claim made before there is a machine](04-scheduling.md)** · ↑ **[Act VII overview](README.md)** · Next: **[Three different promises called "survives"](06-storage.md)** →
