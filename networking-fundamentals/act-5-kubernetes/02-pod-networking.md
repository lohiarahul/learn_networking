# The Pod — a shared network namespace

Everyone's first mistake with Kubernetes is to think a Pod is a fancy word for a container. It isn't. A Pod is the namespace from Act IV, and the containers are just processes that happen to share it.

### How do several processes share one network identity?

In Act IV you gave each isolated thing its own network namespace: its own interfaces, its own loopback, its own port space. That's perfect when each thing is one self-contained program.

But real applications often come in small clusters that must behave as a single unit — a web server and a sidecar that ships its logs, or an app and a proxy that handles its TLS. These want to be *separate processes* (separate images, separate restarts, separate failures) while sharing *one network identity*: one IP, one `localhost`, so the proxy can reach the app at `127.0.0.1` with no network in between.

A bare container gives you isolation but no sharing. A single giant container gives you sharing but no isolation. Kubernetes needed a unit that is several processes wearing one network namespace — and the answer is the one you already built: **they all join the same namespace instead of each making their own.**

### So what is a Pod, really?

A Pod is a group of one or more containers that share a single network namespace (and a few others). They share the same IP address, the same loopback interface, and — this is the part that surprises people — the same port space.

That last one has a consequence you can predict before you test it. If a Pod really is one namespace, then a Pod has exactly one port 8080, no matter how many containers are inside it. Two containers in one Pod trying to bind `0.0.0.0:8080` are in the same position as two processes you ran side by side in a single Act IV namespace. Hold your prediction about what the second one sees; the checkpoint below collects it. **A Pod is the Act IV network namespace, given a name and a scheduler** — not a new idea, an old one with a scheduler on top.

### So whose namespace is it?

At the end of Act IV you were told, in one line, that Kubernetes holds a Pod's namespace open with "a tiny `pause` container whose only job is to exist." That was an assertion. Here is where you check it, because it answers a question you now have: if the Pod *is* its containers, and containers restart, then which container *owns* the namespace — and what happens to the Pod's IP when that owner dies and comes back?

The **pause container** (also called the infra or sandbox container) is how Kubernetes dodges the question entirely. Its whole program is: set up signal handling, then sleep forever. It does nothing. Its only job is to *exist* — to be the process that holds the network namespace open. Every other container in the Pod is created by joining pause's existing namespace rather than making its own.

Because pause never restarts as long as the Pod lives, the namespace file stays open and the Pod IP stays stable even as your real containers crash, restart, and get replaced underneath it. So the namespace belongs to nobody useful, deliberately: the pause container is the answer to the orientation question *who holds the file open?* — a process whose whole purpose is to keep one file descriptor from closing. You can verify it two ways in a moment: `crictl ps` on the node shows one `pause` per Pod, and the inode check below shows the app sharing pause's namespace file.

> **Check yourself —** Two containers in one Pod both try to listen on `0.0.0.0:8080`. What happens?

<details>
<summary>Answer</summary>

The second one fails with `EADDRINUSE`. They share one network namespace, so there is exactly one port 8080 between them — the same thing that would happen to two processes in a single Act IV namespace. Sharing the namespace is what gives them one IP and a usable `localhost`; the shared port space is the other half of that same bargain.

</details>

### What does that sharing look like?

<!-- figure -->

```
            ┌──────────────────── Pod (one IP: 10.244.1.7) ───────────────────┐
            │                                                                   │
            │   pause  ──holds open──►  net namespace  ◄──joins──  app          │
            │   (sleeps forever)        /proc/<pause>/ns/net       (binds :8080)│
            │                                  ▲                                │
            │                                  └──────joins──────  sidecar      │
            │                                                      (reaches app │
            │   one loopback (127.0.0.1) shared by all three        at 127.0.0.1│
            │   one port space:  only ONE container may bind :8080  :8080)      │
            └───────────────────────────────────────────────────────────────────┘
```

### Where does the kernel keep the shared namespace?

On the node, the namespace is the same file it was in Act IV — a file under `/proc/<pid>/ns/net`:

```
/proc/$(pidof pause)/ns/net      the network namespace file the whole Pod shares
/proc/<app-pid>/ns/net           the app container's view of its network namespace
```

Act IV taught you what those files are: `ls -la` on one prints a magic symlink like `net:[4026532567]`, and that number is the namespace's inode — the namespace's real identity, independent of any name.

### Can you watch the two containers share one inode?

`docker exec` into the node, find a Pod's `pause` process and one of its app processes, and read both namespace files:

> **Predict first —** the two containers in one Pod: will `/proc/<pid>/ns/net` show the same inode number for each, or different ones?

```bash
crictl ps -a | grep pause            # one pause container per Pod on this node
crictl inspect --output go-template --template '{{.info.pid}}' <pause-container-id>
crictl inspect --output go-template --template '{{.info.pid}}' <app-container-id>
ls -la /proc/<pause-pid>/ns/net      # net:[...]
ls -la /proc/<app-pid>/ns/net        # net:[...]  — compare the numbers
```

The two inode numbers are **identical**. That equality *is* the Pod: two different processes, two different container images, one shared `net:` file. This is the literal, byte-level meaning of "a Pod is a shared network namespace" — and it is why the shared port space is not a design choice Kubernetes made but an arithmetic consequence of the file being one file.

The same equality shows up one level up, in two commands that turn out to be the same command:

```bash
ip netns exec <pod-namespace-id> ip addr     # Act IV: from the node, outside the ns
kubectl exec <pod> -- ip addr                # Act V: same view, asked over the API
```

Both enter the Pod's network namespace and dump its interfaces. `kubectl exec` is `ip netns exec` with an API server in front of it. To go further, attach an ephemeral debugger that *joins* the Pod's namespaces — the same move every Pod container already makes when joining pause:

```bash
kubectl debug -it <pod> --image=nicolaka/netshoot --target=<container>
ip addr
ss -tlnp
```

That ephemeral netshoot container shares the Pod's network namespace, so its `ip addr` shows the Pod's interfaces and its `ss` shows the Pod's listening sockets — you are inside the file, looking out. Kubernetes, seen this way, is a namespace manager at scale: it does for ten thousand namespaces what you did for one with `ip netns add`.

> **You understand this when you can** explain why two containers in one Pod can't both bind port 8080, and predict that `/proc/<pause>/ns/net` and `/proc/<app>/ns/net` show the same inode number — because the Pod *is* that one shared namespace file, held open by pause.

---

← Prev: **[The lab for Act V — a real cluster with kind](01-lab-with-kind.md)** · ↑ **[Act V overview](README.md)** · Next: **[Services and kube-proxy](03-services.md)** →
