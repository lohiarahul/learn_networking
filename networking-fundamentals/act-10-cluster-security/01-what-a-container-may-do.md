# What a container is allowed to do

The orientation page asked you to type a flag and then admitted it was cheating:

> `--privileged` hands the container the full set of capabilities... You would never run a production workload this way — a privileged container that gets compromised is, effectively, root on the host — and that danger is itself a lesson this course returns to.

This is where it returns. But the flag is the less interesting half. `--privileged` has been in almost every command you have run since Act I, and you were told it *adds* things — so the question that actually matters is what a container has **without** it, because that is what every workload you will ever deploy is running with, and nobody chose it. It arrived as a default.

Act IX ended on exactly that: each of those defaults was picked to make a cluster start.

> **Predict first —** a Pod with no `securityContext` at all. Write down four answers before you run anything. **(a)** What uid does the process run as? **(b)** Can it change its own hostname? **(c)** Can it write to `/proc/sys/net/ipv4/ip_forward`? **(d)** With *every* capability dropped and running as uid 1000, can it bind port 80? Most people get (a) and (d) wrong, and wrong in opposite directions — (a) is more permissive than they expect and (d) is more permissive than they expect for a completely different reason.

### The default, measured

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

kubectl run d --image=busybox:1.36 --restart=Never --command -- \
  sh -c 'id; hostname newname'
sleep 5
kubectl logs d
```

```
uid=0(root) gid=0(root) groups=0(root),10(wheel)
hostname: sethostname: Operation not permitted
```

Two facts in three lines, and they disagree with each other.

**It is root.** Not a sandboxed user, not `nobody` — uid 0, the same uid as the thing that runs your kernel's init. Nothing in the manifest asked for that. It is what the image said in its `USER` directive, or rather what it didn't say, and the cluster took it at face value.

**And it cannot set its own hostname**, which is an operation root has been able to perform since 1970. So it is root, and it is not root, and the gap between those is the whole subject of this lesson.

### Counting what is left

The kernel stopped carving privilege out of a single "am I uid 0" test a long time ago. It split root's powers into **capabilities** — individually grantable pieces, each named for the thing it lets you do — and a process holds a set of them. Being uid 0 no longer *means* anything on its own; it is a number that happens to be what most capability-holding processes run as.

So ask the kernel which pieces this process holds. Act I taught you where to look for a process's own truth:

```bash
kubectl run caps --image=busybox:1.36 --restart=Never --command -- \
  sh -c 'grep -E "^Cap(Eff|Bnd)" /proc/self/status'
sleep 5
kubectl logs caps
```

```
CapEff:	00000000a80425fb
CapBnd:	00000000a80425fb
```

A bitmask, one bit per capability. Count the bits before you name them, because the count is the finding:

```bash
python3 -c 'print(bin(0xa80425fb).count("1"), "of", bin(0x1ffffffffff).count("1"))'
```

```
14 of 41
```

Fourteen. And now the names — `capsh` is not in the busybox image but it *is* on the kind node, which is an Ubuntu filesystem you can reach the same way Act VII reached the kubelet's directory tree:

```bash
docker exec netlab-control-plane capsh --decode=00000000a80425fb
```

```
0x00000000a80425fb=cap_chown,cap_dac_override,cap_fowner,cap_fsetid,cap_kill,
cap_setgid,cap_setuid,cap_setpcap,cap_net_bind_service,cap_net_raw,
cap_sys_chroot,cap_mknod,cap_audit_write,cap_setfcap
```

(One long line in reality; wrapped here to fit.)

Read that list as a statement about what a compromised process in a default Pod can do, because that is what it is. `cap_dac_override` **ignores file permissions entirely** — every `chmod` in the image is advisory to this process. `cap_setuid` lets it become any user it likes. `cap_net_raw` lets it forge and sniff packets on its network, which is the capability behind every ARP-spoofing experiment in Act II. `cap_mknod` lets it create device nodes.

And `cap_sys_admin` — the one that would have let it set the hostname — is not there. Neither is `cap_sys_module`, `cap_sys_ptrace`, or `cap_net_admin`. That is the shape of the default: **the powers that let you reconfigure the machine are withheld; a startling number of the powers that let you read and impersonate things on it are not.**

Nothing in Kubernetes chose that list. Run the same check under plain Docker and you get the identical fourteen:

```bash
docker run --rm busybox:1.36 grep CapEff /proc/self/status
```

```
CapEff:	00000000a80425fb
```

It is the **container runtime's** default set, and it is the same one in `docker run` and in a Pod because both end up asking the same kind of thing to build the same kind of process.

### Two walls, two error messages, one wrong intuition

Now prediction (c). Writing to `/proc/sys/net/ipv4/ip_forward` is the kernel switch Act II made you flip to turn a machine into a router.

```bash
kubectl run pw --image=busybox:1.36 --restart=Never --command -- \
  sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'
sleep 5
kubectl logs pw
```

```
sh: can't create /proc/sys/net/ipv4/ip_forward: Read-only file system
```

**Read that error against the last one.** Setting the hostname failed with `Operation not permitted` — the kernel checking a capability and finding it absent. This failed with `Read-only file system` — a *mount option*. The runtime mounted `/proc/sys` read-only, and no capability in the world gets you past a read-only mount; you would have to remount it, which needs `cap_sys_admin`, which is how these two walls turn out to be stacked rather than parallel.

The reason to care is diagnostic, and it is the same shape as Act IX's 401-versus-403. "The container is not allowed to do that" is not one condition. It is at least two, they fail with different words, and **only one of them is something `securityContext` can change.** People spend afternoons adding capabilities to fix read-only mounts.

### So what was `--privileged`?

Ten acts of typing it. Now measure it, in a Pod, in one shot:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: priv}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext: {privileged: true}
    command: ["sh","-c","grep ^CapEff /proc/self/status; hostname newname && echo hostname-OK; echo 1 > /proc/sys/net/ipv4/ip_forward && echo sysctl-OK; ls /dev | wc -l"]
EOF
sleep 6
kubectl logs priv
```

```
CapEff:	000001ffffffffff
hostname-OK
sysctl-OK
170
```

Compare, line by line, with a default Pod:

| | default | `privileged: true` |
|---|---|---|
| capabilities | 14 | **41 — every one** |
| set the hostname | `Operation not permitted` | works |
| write `/proc/sys` | `Read-only file system` | works |
| entries in `/dev` | **16** | **170** |

```bash
kubectl run dev --image=busybox:1.36 --restart=Never --command -- sh -c 'ls /dev | wc -l'
sleep 5; kubectl logs dev
```

```
16
```

That fourth row is the one to sit with, because it is not about capabilities at all. Those 170 entries are **the host's devices** — including the block device holding the node's root filesystem. A process that can open the disk can read every file on it without asking the filesystem's permission bits, and can write a new `/etc/shadow` under the running kernel's nose.

Which is the mechanism behind the sentence you were asked to accept in the orientation. "A privileged container is effectively root on the host" is not a slogan; it is four measurements — all capabilities, writable `/proc/sys`, the host's devices, and the read-only mounts dropped — and any one of them is enough on its own.

### The correct starting posture, and what it costs

If fourteen is a default nobody chose, the fix is to choose. Drop everything and see what breaks:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: dropped}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext:
      capabilities: {drop: ["ALL"]}
    command: ["sh","-c","grep ^CapEff /proc/self/status; touch /tmp/f; chown 1000 /tmp/f"]
EOF
sleep 6
kubectl logs dropped
```

```
CapEff:	0000000000000000
chown: /tmp/f: Operation not permitted
```

Zero. And `chown` — which worked in the default Pod, because `cap_chown` was one of the fourteen — now doesn't. That is the trade in its entirety: `drop: ["ALL"]` is the only defensible starting point, and it will break things, and the breakages tell you what the workload was actually using.

The convention is to drop all and add back the named few:

```yaml
securityContext:
  capabilities:
    drop: ["ALL"]
    add: ["NET_BIND_SERVICE"]
```

Note the spelling, because it is a trap with no error message. The manifest wants `NET_BIND_SERVICE`; the kernel and `capsh` call the same thing `cap_net_bind_service`. Write the kernel's prefix into the manifest and see what happens:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: capcase}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext:
      capabilities: {drop: ["ALL"], add: ["CAP_NET_BIND_SERVICE"]}
    command: ["sh","-c","grep ^CapEff /proc/self/status"]
EOF
sleep 6
kubectl logs capcase
```

```
CapEff:	0000000000000000
```

**Accepted, scheduled, ran, granted nothing.** No validation error, no warning, no event — the string simply matched no capability the runtime knows, so it added none. Which means the failure mode of a typo here is not a broken Pod; it is a Pod that looks hardened, reviews as hardened, and is missing the one permission it was supposed to have. You find out when the workload fails.

### The capability that turns out not to be one

`NET_BIND_SERVICE` is the example every guide reaches for: ports below 1024 are privileged, so a non-root web server needs this capability to bind 80. Prediction (d) tested exactly that. Drop everything, run as uid 1000, try:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: bind80}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext:
      runAsUser: 1000
      capabilities: {drop: ["ALL"]}
    command: ["sh","-c","id -u; timeout 2 nc -l -p 80 -v"]
EOF
sleep 6
kubectl logs bind80
```

```
1000
listening on [::]:80 ...
punt!
```

(`punt!` is just busybox `nc` complaining that `timeout` killed it two seconds later. The line above it is the finding.)

**It bound port 80 as an unprivileged user holding no capabilities whatsoever.** The famous example does not reproduce. Before deciding the kernel is broken, ask what a "privileged port" actually is — it is a number in a comparison, and the number is a knob:

```bash
kubectl run ports --image=busybox:1.36 --restart=Never --command -- \
  sh -c 'sysctl net.ipv4.ip_unprivileged_port_start'
sleep 5; kubectl logs ports
docker run --rm --privileged --net=host busybox:1.36 \
  sysctl net.ipv4.ip_unprivileged_port_start
```

```
net.ipv4.ip_unprivileged_port_start = 0
net.ipv4.ip_unprivileged_port_start = 1024
```

Zero inside the container; the traditional 1024 on the machine underneath it. Something in the chain that started your container moved the boundary to the bottom, so there are no privileged ports left to be privileged about — Docker has set this for the containers it creates for years, precisely so that images which insist on port 80 work without being handed a capability.

Two things follow, and the second is the one worth keeping.

The small one: adding `NET_BIND_SERVICE` on this runtime grants a permission that is not being checked. Harmless, and cargo.

The large one: **a capability is a gate the kernel checks, and a sysctl can move the gate.** Your security posture is the conjunction of every layer's defaults, not the manifest you wrote, and the only way to know what a restriction does is to try the thing it forbids. Recite this table from a course and you will be confidently wrong on some other runtime, in the other direction, where the sysctl is 1024 and your carefully dropped capabilities break a web server at 3am.

> **Check yourself —** you drop `ALL` and your application still starts, serves traffic, and passes its tests. What has that told you, and what has it not?

<details>
<summary>Answer</summary>

It has told you the code paths you exercised needed no capability. It has told you nothing about the ones you didn't.

Capabilities are consulted at the moment of a privileged operation, not at startup. An application that reads a config file, listens, and answers requests may never touch one — and then, six weeks later, a rarely-used feature calls `chown` on an upload, or a crash handler tries `ptrace`, or a library falls back to a raw socket for an ICMP health check. Each of those is a syscall that has been returning success for years and now returns `EPERM`.

Which is why `drop: ["ALL"]` is a claim to be *tested*, not a line to be pasted, and why the useful version of this work is not "add the manifest stanza" but "find out what this workload actually asks the kernel for." Lesson 02 gives you a way to watch that happen instead of guessing.

And there is a second-order answer worth having. The list you end up with is a description of your application's privileged behaviour, written down, in the manifest, where a reviewer can see it. That is worth something even where the enforcement is redundant: `add: ["NET_RAW"]` on a payments service is a question somebody should ask.

</details>

### Who you are, decided much too late

`runAsUser: 1000` in the last experiment forced the uid, which is the direct fix for the first measurement in this lesson. But you cannot use it everywhere — plenty of images genuinely need to be a particular user, and hardcoding 1000 into a manifest that runs somebody else's image is a guess. The safer form states the requirement rather than the value:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: mustnotberoot}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext: {runAsNonRoot: true}
    command: ["sh","-c","id"]
EOF
sleep 6
kubectl get pod mustnotberoot -o jsonpath='{.status.containerStatuses[0].state}' | python3 -m json.tool
```

```json
{
    "waiting": {
        "message": "container has runAsNonRoot and image will run as root (pod: \"mustnotberoot_default(...)\", container: c)",
        "reason": "CreateContainerConfigError"
    }
}
```

The refusal is exactly right, and **where** it happened is the interesting part. Look at what it is not: it is not an error from `kubectl apply`. The Pod was accepted, validated, persisted in etcd, scheduled to a node — all of Act VI's machinery ran and was satisfied — and then the **kubelet**, on the node, at the moment of building the container, refused. `CreateContainerConfigError`, and the Pod sits there in that state forever.

Ask why it could not have been caught earlier, because the answer is the shape of this whole act. To know that "the image will run as root" you have to know what user the image specifies, and that is written in the image's own metadata — which nobody has until the image has been pulled onto a node that has a copy of it. The API server that accepted your Pod had a YAML document and no image. It could not have known. **The check had to wait for the node because the node was the first place with enough information to make it.**

Hold that, because it will keep happening, and by the end of the act it will have a name.

While you are here, the rest of the identity fields, which are less subtle:

```yaml
spec:
  securityContext:          # pod level: applies to every container
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000           # pod level ONLY -- there is no container-level fsGroup
  containers:
  - name: c
    securityContext:        # container level: overrides the pod for THIS container
      runAsUser: 2000
```

Two levels, container wins where both are set, and one field that exists at only one of them. `fsGroup` is the odd one: it is not about the process at all, it is about **volumes** — the kubelet chowns the volume's contents to that gid and sets the setgid bit on its directories, so a non-root process can write to storage it does not own. It is the answer to "I set `runAsNonRoot` and now my PersistentVolumeClaim is unwritable," which is the most common consequence of doing the right thing here.

### The flag whose name explains nothing

`allowPrivilegeEscalation` sounds like a summary of everything above, and is instead one specific, narrow kernel bit. Look at it directly:

```bash
for v in true false; do
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata: {name: esc-$v}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: ubuntu:24.04
    securityContext: {allowPrivilegeEscalation: $v}
    command: ["sh","-c","grep NoNewPrivs /proc/self/status; echo topsecret > /root/vault; chmod 600 /root/vault; cp /bin/cat /tmp/scat; chmod 4755 /tmp/scat; setpriv --reuid=1000 --regid=1000 --clear-groups /tmp/scat /root/vault"]
EOF
done
sleep 10
for v in true false; do echo "== allowPrivilegeEscalation: $v"; kubectl logs esc-$v; done
```

Read the experiment before the output. The container starts as root, writes a secret readable only by root, makes a **setuid copy of `cat`** — the setuid bit meaning "run this as the file's owner, whoever executes it" — and then deliberately becomes uid 1000 and tries to read the secret through it. One flag differs.

```
== allowPrivilegeEscalation: true
NoNewPrivs:	0
topsecret
== allowPrivilegeEscalation: false
NoNewPrivs:	1
/tmp/scat: /root/vault: Permission denied
```

A uid-1000 process read a root-only file. Then it couldn't.

`NoNewPrivs` is the whole mechanism, and it is one bit that, once set, cannot be unset for the life of the process or anything it forks. It means: **`execve` will never grant privileges the caller did not already hold.** Setuid bits are ignored. File capabilities are ignored. Nothing gained on exec, ever, down the entire process tree.

Which is why the flag deserves a place in your default stanza rather than a paragraph of explanation. Its whole job is to make an attacker's *second* step fail. Getting code execution as an unprivileged user inside a container is common; the next move is almost always to find a setuid binary and go up. This closes that, permanently, for one line of YAML. And note the direction the default runs: `NoNewPrivs: 0` unless you say otherwise.

### A root filesystem you cannot write

The last of the cheap wins, and the one that breaks the most applications:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: ro}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext: {readOnlyRootFilesystem: true}
    command: ["sh","-c","touch /etc/x; touch /tmp/x"]
EOF
sleep 6
kubectl logs ro
```

```
touch: /etc/x: Read-only file system
touch: /tmp/x: Read-only file system
```

`/etc` was the point. **`/tmp` is the lesson** — it is not a separate filesystem in this image, just a directory on the root, so "read-only root filesystem" means genuinely read-only, and every program that writes a lock file, a cache, a template render or an upload buffer stops working.

So you give back exactly the paths that need to be writable, and nothing else:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: ro-fixed}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext: {readOnlyRootFilesystem: true}
    volumeMounts: [{name: scratch, mountPath: /tmp}]
    command: ["sh","-c","touch /etc/x; touch /tmp/x && echo 'tmp write OK'"]
  volumes: [{name: scratch, emptyDir: {}}]
EOF
sleep 6
kubectl logs ro-fixed
```

```
touch: /etc/x: Read-only file system
tmp write OK
```

Which is a better outcome than a writable root even ignoring the attacker: the Pod now *declares* where it keeps mutable state. Anything that used to be quietly written into the image layer and lost on restart is now either a named volume or a visible failure.

<!-- figure -->
```
   "ROOT" IN A CONTAINER IS 14 OF 41 CAPABILITIES

     uid 0, and still:  hostname -> Operation not permitted
     CapEff a80425fb = 14 bits, chosen by the RUNTIME, not by you
     the withheld ones are the RECONFIGURE powers
       (sys_admin, sys_module, net_admin, sys_ptrace)
     the granted ones include READ-EVERYTHING and BE-ANYONE
       dac_override .. ignores all file permissions
       setuid ....... become any user
       net_raw ...... forge and sniff packets (Act II's ARP)
       mknod ........ create device nodes

   TWO WALLS THAT LOOK THE SAME AND ARE NOT
     "Operation not permitted"  -> a CAPABILITY is missing.
                                   securityContext can fix it.
     "Read-only file system"    -> a MOUNT OPTION.
                                   no capability defeats it.
     read the error. do not assume which one you hit.

   PRIVILEGED = FOUR THINGS AT ONCE, ANY ONE FATAL
     41/41 caps · /proc/sys writable · read-only mounts gone
     /dev goes 16 -> 170  <-- the HOST's disks.
     open the block device and /etc/shadow has no permissions.

   THE DEFAULT STANZA, AND WHAT EACH LINE IS FOR
     capabilities.drop: [ALL] .... start from zero, add names back
     runAsNonRoot: true ......... refuse to be uid 0
     allowPrivilegeEscalation: false
                                  NoNewPrivs=1: execve NEVER grants
                                  privilege again. kills step TWO of
                                  an attack. one line, permanent.
     readOnlyRootFilesystem: true
                                  + an emptyDir for each writable path,
                                  so mutable state becomes DECLARED
     fsGroup (pod level only) ... chowns VOLUMES so a non-root
                                  process can write its PVC

   THE MEASUREMENT THAT SHOULD CHANGE HOW YOU READ GUIDES
     drop ALL + uid 1000 + bind port 80  ->  IT WORKS.
     net.ipv4.ip_unprivileged_port_start = 0 in here, 1024 outside.
     a capability is a gate; a SYSCTL MOVED THE GATE.
     so NET_BIND_SERVICE is cargo on this runtime -- and would be
     load-bearing on another. test the thing you forbade.

   AND ONE REFUSAL THAT ARRIVED LATE, ON PURPOSE
     runAsNonRoot on a root image is NOT rejected by apply.
     accepted -> stored -> scheduled -> then the KUBELET says
     CreateContainerConfigError. because "what user does this
     IMAGE run as" is unknowable until a node holds the image.
     the check waited for the first place that knew enough.
```

**Cleanup:**

```bash
kubectl delete pod d caps pw priv dev dropped capcase bind80 ports \
  mustnotberoot esc-true esc-false ro ro-fixed --ignore-not-found
```

> **You understand this when you can** explain why a container process is uid 0 and still cannot set its own hostname; read a `CapEff` mask, count it, and name what its absences and presences mean for a compromised process; say who chose that default set and demonstrate it is not Kubernetes; distinguish `Operation not permitted` from `Read-only file system` and say which one `securityContext` can act on; give four independent measurements that make a privileged container equivalent to root on the host, and say which single one would be enough; write the four-line hardening stanza and say what each line denies an attacker; explain `NoNewPrivs` in terms of `execve` and say which step of an attack it breaks; predict what `readOnlyRootFilesystem` does to `/tmp` and give the fix; say what `fsGroup` is for and why it exists only at pod level; demonstrate that dropping `ALL` does not stop a process binding port 80 on this runtime and explain the sysctl that makes that true; and explain why `runAsNonRoot` cannot be enforced when the Pod is created.

**Which raises:** every restriction in this lesson was about *who the process is* — its uid, its capabilities, its mounts. And each of them gates a handful of operations: fourteen capabilities against a kernel that exposes **more than three hundred syscalls**, the overwhelming majority of which are checked against no capability at all. A process running as uid 1000 with `CapEff: 0` can still call `keyctl`, `unshare`, `ptrace`, `userfaultfd` and every other entry point in that table, and the ones used to break out of containers are mostly in that unguarded majority. **So what stops a process from calling a syscall when there is no capability standing in front of it?**

---

↑ **[Act X overview](README.md)** · Next: **[When the kernel says no](02-the-kernel-says-no.md)** →
