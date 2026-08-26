# When the kernel says no

Fourteen capabilities against a kernel that exposes over three hundred syscalls. Lesson 01 left that arithmetic sitting there, and it is worse than it looks: capabilities were never designed as a container boundary. They are a decomposition of *root*, so they gate the operations that used to require uid 0 — mounting, loading modules, changing the clock. The syscalls used to break out of containers are mostly not in that set, because breaking out of a container was not a thing anyone was decomposing root for.

So the question from the end of lesson 01 stands: what stops a process from making a syscall when no capability is standing in front of it?

> **Predict first —** three answers, committed before you run anything. **(a)** Does a default Kubernetes Pod have a syscall filter installed? **(b)** Does a default `docker run` container? **(c)** `unshare -U` creates a new **user namespace** — Act IV's mechanism, and the one an attacker reaches for first, because inside a fresh user namespace you are root and can then create the other namespace types. It needs **no capability at all**. Will it succeed in a default Pod? Get (a) and (b) the same way round and you have the standard mental model; they are not the same way round.

### The filter that is not there

`/proc/self/status` reports a process's seccomp state in one line, the same file that gave you `CapEff`:

```bash
export KUBECONFIG="${TMPDIR:-/tmp}/act10.kubeconfig"
kind get kubeconfig --name netlab > "$KUBECONFIG"

kubectl run sec --image=busybox:1.36 --restart=Never --command -- \
  sh -c 'grep Seccomp /proc/self/status'
sleep 5
kubectl logs sec
```

```
Seccomp:	0
Seccomp_filters:	0
```

`0` means **no filter**. Now the same image, same kernel, one layer down:

```bash
docker run --rm busybox:1.36 grep Seccomp /proc/self/status
```

```
Seccomp:	2
Seccomp_filters:	1
```

`2` is `SECCOMP_MODE_FILTER` — one filter attached.

**Docker installs a syscall filter on every container it starts. Kubernetes installs none.** That is the answer to (a) and (b), and almost everybody has it backwards, because the mental model is "Kubernetes is the serious production one, so it must be at least as locked down as my laptop."

The reason is worth having, because it is not an oversight and it recurs. Docker's default profile blocks roughly forty syscalls chosen so that the images people actually run on a laptop keep working. That is a bet you can make about `docker run`, where the blast radius of being wrong is one developer's afternoon. A kubelet is being asked to run *arbitrary* workloads for an entire organisation, and a default filter that breaks one of them breaks it at 3am with `Operation not permitted` and no explanation. So the projected default is no filter, and the flag to change it — `--seccomp-default` on the kubelet, which turns `RuntimeDefault` on for every Pod that does not say otherwise — exists and is off.

Which is Act IX's closing line again, now with a number attached: the default was chosen so that everything starts.

### What that profile was actually doing

Ask for it explicitly and compare against asking for nothing:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: s-rd}
spec:
  restartPolicy: Never
  securityContext:
    seccompProfile: {type: RuntimeDefault}
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","grep Seccomp /proc/self/status; echo '-- unshare -U:'; unshare -U true 2>&1 && echo user-ns-OK; echo '-- unshare -m:'; unshare -m true 2>&1 && echo mount-ns-OK"]
---
apiVersion: v1
kind: Pod
metadata: {name: s-unc}
spec:
  restartPolicy: Never
  securityContext:
    seccompProfile: {type: Unconfined}
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","grep Seccomp /proc/self/status; echo '-- unshare -U:'; unshare -U true 2>&1 && echo user-ns-OK; echo '-- unshare -m:'; unshare -m true 2>&1 && echo mount-ns-OK"]
EOF
sleep 10
for p in s-rd s-unc; do echo "== $p"; kubectl logs $p; done
```

```
== s-rd
Seccomp:	2
Seccomp_filters:	1
-- unshare -U:
unshare: unshare(0x10000000): Operation not permitted
-- unshare -m:
unshare: unshare(0x20000): Operation not permitted
== s-unc
Seccomp:	0
Seccomp_filters:	0
-- unshare -U:
user-ns-OK
-- unshare -m:
unshare: unshare(0x20000): Operation not permitted
```

Read the four results as a two-by-two, because they separate the two walls cleanly.

**`unshare -m`** — a mount namespace — fails in both. It needs `CAP_SYS_ADMIN`, which lesson 01 showed is not among the fourteen. **Capabilities blocked it, and the filter was irrelevant.**

**`unshare -U`** — a user namespace — succeeds unconfined and fails under `RuntimeDefault`. It needs no capability, so nothing in lesson 01 was ever going to stop it. **The filter blocked it, and capabilities were irrelevant.**

That is prediction (c), and it is the whole reason this lesson exists. The single most useful primitive for escalating inside a container is one that lesson 01's entire toolkit does not touch, and one line of `securityContext` removes it. Which also means: on a cluster running the projected default, that line is not there.

### Writing one

`RuntimeDefault` is somebody else's list. Writing your own means putting a file on the node, because a seccomp profile is not a Kubernetes object — there is no `kind: SeccompProfile`, and the manifest only ever holds a *path*.

The kubelet looks under one directory, and everything is relative to it: `/var/lib/kubelet/seccomp/`. Act VII already had you inside that tree looking at Secret volumes, so you know how to get there.

```bash
for n in netlab-control-plane netlab-worker; do
  docker exec "$n" mkdir -p /var/lib/kubelet/seccomp/profiles
  docker exec -i "$n" sh -c 'cat > /var/lib/kubelet/seccomp/profiles/no-chmod.json' <<'EOF'
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "syscalls": [
    { "names": ["chmod","fchmod","fchmodat","fchmodat2"], "action": "SCMP_ACT_ERRNO" }
  ]
}
EOF
done
docker exec netlab-control-plane wc -c /var/lib/kubelet/seccomp/profiles/no-chmod.json
```

```
148 /var/lib/kubelet/seccomp/profiles/no-chmod.json
```

Two things about the JSON before you run it. `defaultAction` is the answer for every syscall not named — here, allow — and the `syscalls` list carries the exceptions. And **four names for one operation**: `chmod`, `fchmod`, `fchmodat`, `fchmodat2`. A filter matches syscall *numbers*, not intentions, and "change a file's mode" is reachable through four of them because the kernel has accumulated variants for thirty years. Miss one and you have blocked nothing, silently, which is the characteristic failure of writing these by hand.

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: l-nochmod}
spec:
  restartPolicy: Never
  securityContext:
    seccompProfile:
      type: Localhost
      localhostProfile: profiles/no-chmod.json
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","grep Seccomp /proc/self/status; id -u; touch /tmp/f; echo '-- chmod:'; chmod 700 /tmp/f 2>&1 && echo chmod-OK; echo '-- chown:'; chown 1000 /tmp/f 2>&1 && echo chown-OK"]
EOF
sleep 8
kubectl logs l-nochmod
```

```
Seccomp:	2
Seccomp_filters:	1
0
-- chmod:
chmod: /tmp/f: Operation not permitted
-- chown:
chown-OK
```

Note `localhostProfile: profiles/no-chmod.json` — relative, with the `/var/lib/kubelet/seccomp/` prefix implied. A leading slash there is one of the two ways this goes wrong.

And read the last three lines as a single finding. The process is **uid 0**. It holds `cap_fowner` and `cap_chown`, both in lesson 01's fourteen. `chown` — the capability-gated operation, capability held — **works**. `chmod` — for which it holds exactly the same authority — **does not**.

**So the filter is consulted before the capability check, and no capability buys past it.** That ordering is what makes seccomp a boundary rather than a permission: there is nothing to grant.

Now the uncomfortable half. Look at the error text: `Operation not permitted`. That is the identical string lesson 01 got from `sethostname` when a capability was *missing*. Two entirely different walls, the same seven words, because both surface as `EPERM` and `EPERM` has one spelling.

Lesson 01 told you to read the error rather than assume which wall you hit. This is the case where reading the error cannot tell you. What can:

```bash
kubectl get pod l-nochmod \
  -o jsonpath='{.spec.securityContext.seccompProfile}{"\n"}'
kubectl logs l-nochmod | grep Seccomp
```

```
{"localhostProfile":"profiles/no-chmod.json","type":"Localhost"}
Seccomp:	2
```

**A filter is loaded, so a filter is a suspect.** `Seccomp: 0` would have eliminated it in one line and sent you to the capability list instead. This is the diagnostic worth keeping from the lesson: before arguing about which capability is missing, find out whether anything is filtering at all.

### Why you are not going to write an allowlist

The instinct after all that is to invert it: deny by default, allow what the application needs. Try it — deny everything except four syscalls no program can live without:

```bash
docker exec -i netlab-control-plane sh -c 'cat > /var/lib/kubelet/seccomp/profiles/minimal.json' <<'EOF'
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "syscalls": [
    { "names": ["read","write","exit","exit_group"], "action": "SCMP_ACT_ALLOW" }
  ]
}
EOF
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: l-minimal}
spec:
  restartPolicy: Never
  nodeName: netlab-control-plane
  securityContext:
    seccompProfile: {type: Localhost, localhostProfile: profiles/minimal.json}
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","echo hi"]
EOF
sleep 8
kubectl get pod l-minimal -o jsonpath='{.status.containerStatuses[0].state}' | python3 -m json.tool
```

```json
{
    "terminated": {
        "exitCode": 128,
        "message": "failed to create containerd task: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: error closing exec fds: get handle to /proc/thread-self/fd: fstatfs fsmount:fscontext:proc: operation not permitted",
        "reason": "StartError",
        "startedAt": "1970-01-01T00:00:00Z"
    }
}
```

Your program never ran. `runc` was still assembling the container — closing file descriptors it had opened for its own setup — and your filter killed **the thing that starts things**. `fstatfs` is not a syscall anyone would think to put on an allowlist for `echo hi`.

Which is the honest reason `RuntimeDefault` is the recommendation and hand-written allowlists are not. The set of syscalls a container needs is not the set *your code* makes; it is that plus everything the runtime, the libc, the dynamic linker, the language VM and the garbage collector do on the way. You cannot enumerate it by reading your source. The only reliable way to get an allowlist is to **record** the syscalls a real workload makes under real traffic and then restrict to what was observed — which means running it unrestricted first, and accepting that a code path you never exercised is a production outage the first time it fires.

So the practical ladder is: `RuntimeDefault` on everything (cheap, and it removes `unshare -U`), a denylist for a specific operation you know you never need, and a generated allowlist only where the workload is worth the effort of recording it.

### The file has to be on the node — every node

Point a Pod at a profile that is not there:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: l-missing}
spec:
  restartPolicy: Never
  securityContext:
    seccompProfile: {type: Localhost, localhostProfile: profiles/does-not-exist.json}
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","echo hi"]
EOF
sleep 8
kubectl get pod l-missing -o jsonpath='{.status.containerStatuses[0].state}' | python3 -m json.tool
```

```json
{
    "waiting": {
        "message": "failed to create containerd container: cannot load seccomp profile \"/var/lib/kubelet/seccomp/profiles/does-not-exist.json\": open /var/lib/kubelet/seccomp/profiles/does-not-exist.json: no such file or directory",
        "reason": "CreateContainerError"
    }
}
```

The message resolves the relative path for you, which is the fastest way to confirm what the kubelet was actually looking for.

But the operational fact is the one to carry: **a `Localhost` profile is a file on a filesystem, so a Pod's security posture now depends on which node it landed on.** Put the profile on three nodes out of five, and the Deployment works, and works, and works — until the scheduler picks node four. There is no admission check for this, no status condition, nothing in `kubectl get` that will tell you the fleet is inconsistent. It is a node-provisioning problem wearing a Pod-manifest costume, and the two ways it is solved in practice are baking profiles into the node image, or a DaemonSet whose only job is to write files into `/var/lib/kubelet/seccomp/` on every node it lands on.

### The other filter, and an honest limit of this lab

Seccomp filters **syscall numbers and their arguments**. It cannot express "may read `/etc/passwd` but not `/etc/shadow`", because by the time the kernel is in `openat` the path is a pointer into the calling process's memory, and a filter that dereferenced it could be raced. Paths are the job of a different mechanism: a Linux Security Module, of which **AppArmor** is the one Kubernetes has a field for.

An AppArmor profile is a list of paths and permissions:

```
#include <tunables/global>

profile k8s-deny-write flags=(attach_disconnected) {
  #include <abstractions/base>

  file,             # allow all file operations, then subtract:
  deny /** w,       # no writing, anywhere
}
```

And since Kubernetes 1.30 it is an ordinary `securityContext` field:

```yaml
securityContext:
  appArmorProfile:
    type: Localhost                    # or RuntimeDefault, or Unconfined
    localhostProfile: k8s-deny-write   # the profile NAME, not a path
```

Two details that cost marks and outages. The profile is named, not pathed — AppArmor profiles are loaded into the kernel by name, so unlike seccomp there is no file for the kubelet to open, and the same "is it on every node?" problem applies to `apparmor_parser` having been run there. And this field **replaced** an annotation, `container.apparmor.security.beta.kubernetes.io/<container>`, which still works and must never be combined with the field on one Pod — setting both is a validation failure, and the ways people arrive at both are copy-paste from a pre-1.30 guide.

Now run it, and get the honest answer for this lab:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: aa}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.36
    securityContext:
      appArmorProfile: {type: RuntimeDefault}
    command: ["sh","-c","echo hi"]
EOF
sleep 8
kubectl get pod aa -o jsonpath='{.status.phase} / {.status.reason} / {.status.message}{"\n"}'
```

```
Failed / AppArmor / Pod was rejected: Cannot enforce AppArmor: AppArmor is not enabled on the host
```

**This lab cannot enforce AppArmor**, and the reason is the kernel underneath it. On macOS and Windows, Docker runs a small Linux VM whose kernel is built without AppArmor; on a Linux machine running Ubuntu or SUSE it is there and enabled. Confirm which you have:

```bash
docker exec netlab-control-plane cat /sys/kernel/security/lsm 2>&1
```

```
cat: /sys/kernel/security/lsm: No such file or directory
```

No security modules at all, so no AppArmor and no SELinux — which also means `securityContext.seLinuxOptions` is inert here for the same reason.

So take three things from the failure rather than pretending it succeeded. The syntax above is what you write, and there is a documented fallback for the syntax you will not remember: `man 5 apparmor.d`, on the machine, which is the only reference available in an exam that whitelists no AppArmor documentation. The **status message is exactly what a real cluster shows** when a profile has not been loaded on the node the Pod landed on, so you have now seen the diagnostic even though you cannot see the enforcement. And the rejection is *terminal* — phase `Failed`, `reason: AppArmor`, no retry — where the missing seccomp profile above sits in `CreateContainerError` retrying forever. Same class of mistake, two different dispositions, and knowing which one you are looking at tells you whether waiting will help.  <!-- man-ok: the CKS exam machine has man pages; the netlab image does not -->

### When you do not trust the list at all

Every mechanism so far narrows *which* syscalls reach the kernel. All of them still reach **the same kernel** — the node's, shared with every other Pod on it, and a bug in one of the hundreds of calls you allowed is a bug in the boundary itself. Which is a real objection, and it has a real answer: hand the container a different kernel.

Kubernetes expresses that as a `RuntimeClass` — a named alternative runtime the node can start Pods with:

```bash
kubectl apply -f - <<'EOF'
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata: {name: sandboxed}
handler: runsc
EOF
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: sandbox}
spec:
  restartPolicy: Never
  runtimeClassName: sandboxed
  containers:
  - name: c
    image: busybox:1.36
    command: ["sh","-c","uname -r"]
EOF
sleep 8
kubectl describe pod sandbox | tail -3
```

```
  Warning  FailedCreatePodSandBox  26s   kubelet  Failed to create pod sandbox: rpc error: code = Unknown
  desc = unable to get OCI runtime for sandbox "275b5cc...": no runtime for "runsc" is configured
```

`runsc` is **gVisor**, which is a user-space reimplementation of the Linux syscall interface: the container's syscalls are serviced by gVisor, and only gVisor talks to the real kernel. `no runtime for "runsc" is configured` is the node saying it has no such binary — which is what you should expect, and what an exam environment will have already done for you, since the interesting work is the `RuntimeClass` and the `runtimeClassName`, not the install.

Then make one mistake deliberately, because the *shape* of the refusal is the point:

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: rc-typo}
spec:
  runtimeClassName: sandboxd
  containers: [{name: c, image: "busybox:1.36"}]
EOF
```

```
Error from server (Forbidden): error when creating "STDIN":
pods "rc-typo" is forbidden: pod rejected: RuntimeClass "sandboxd" not found
```

**Rejected at `apply`.** Nothing was stored, nothing was scheduled, and you knew within a second. Compare that with every other failure in this lesson, and a pattern arrives.

### Five failures, five different stages

Every refusal in the last two lessons was some form of "you may not run this Pod like that." Line them up by *when*:

| The mistake | Refused by | When | Retries? |
|---|---|---|---|
| `runtimeClassName` names no RuntimeClass | API server | at `apply` — nothing stored | n/a |
| `appArmorProfile` on a host without AppArmor | kubelet, before creating anything | Pod goes `Failed`, terminally | no |
| `handler` names a runtime the node lacks | kubelet, creating the **sandbox** | `FailedCreatePodSandBox` | forever |
| `localhostProfile` names a missing file | kubelet, creating the **container** | `CreateContainerError` | forever |
| `runAsNonRoot` on a root image | kubelet, building the container's **config** | `CreateContainerConfigError` | forever |

Nothing arranged that ordering for tidiness. **Each check happens at the first stage that has enough information to make it.** A RuntimeClass name can be compared against objects the API server already holds, so it is caught instantly and for free. Whether AppArmor is enabled is a fact about one kernel, so only that node can answer. Whether the image runs as root requires the image. Whether the profile file exists requires the filesystem.

The pattern is worth naming now because the rest of the act is built on it: **the earlier a decision is made, the cheaper and more uniform it is — and the less it knows.** Every mechanism in this act sits somewhere on that line, and choosing where is the actual engineering.

> **Check yourself —** you set `seccompProfile: RuntimeDefault` on a Deployment and a week later one Pod in ten crashes with `Operation not permitted` from a library you did not write. Someone suggests switching to `Unconfined` to "unblock the release". What has that fixed, what has it given away, and what would you do instead?

<details>
<summary>Answer</summary>

It has fixed the crash and given away every syscall in the profile, including `unshare` — so the one demonstrable protection you measured in this lesson is the first thing gone.

What is worth noticing is that "one Pod in ten" is itself the diagnosis. A filter is deterministic: the same syscall with the same arguments gets the same answer every time. So an intermittent failure under a fixed filter means the *code path* is intermittent — a retry, a fallback, an error handler, something that runs only on the tenth request — which is exactly the class of thing recording-based allowlists miss and exactly why the failure arrived a week later rather than at rollout.

The move that keeps the protection is to find out which syscall. `Unconfined` on **one** Pod, reproduce, and watch — or, if you have a way to switch the profile's `defaultAction` to `SCMP_ACT_LOG`, log-and-allow tells you the answer with nothing broken. Then you have a choice between an exception for one call and a genuine reason to run that workload unconfined, and either way it is written down.

The general form, and it applies to every control in this act: **the fix for a control that fires is to find out what it caught.** Turning it off tells you nothing and cannot be reviewed, because a missing `seccompProfile` field looks identical to nobody having thought about it.

</details>

<!-- figure -->
```
   THE TWO WALLS ARE ORTHOGONAL, AND ONE WAS NEVER UP

     unshare -m  (mount ns)  needs CAP_SYS_ADMIN
       -> denied by CAPABILITIES. filter irrelevant.
     unshare -U  (user ns)   needs NO capability
       -> denied ONLY by the seccomp filter.
          and a user namespace is where an escape STARTS.

   AND KUBERNETES SHIPS NO FILTER
     docker run ......... Seccomp: 2   (~40 syscalls blocked)
     a default Pod ...... Seccomp: 0   (nothing blocked)
     because a kubelet runs ARBITRARY workloads and a bad
     default breaks one of them at 3am. the flag exists:
     kubelet --seccomp-default. it is OFF.

   THE FILTER SITS IN FRONT OF THE CAPABILITY CHECK
     uid 0, holding cap_chown AND cap_fowner:
       chown -> works        (capability consulted, held)
       chmod -> EPERM        (filter said no first)
     there is nothing to GRANT. that is what makes it a
     boundary rather than a permission.

   BOTH WALLS SAY "Operation not permitted"
     so the message cannot tell them apart. this can:
       grep Seccomp /proc/<pid>/status
       0 -> not the filter. go look at CapEff.
       2 -> a filter is a suspect.

   WHY YOU WILL NOT HAND-WRITE AN ALLOWLIST
     defaultAction ERRNO + [read,write,exit,exit_group]
       -> StartError. runc died in container init on fstatfs.
     the needed set is your code PLUS runc, libc, ld.so, the
     runtime, the GC. unknowable by reading source.
     also: chmod is FOUR syscall names. miss one, block nothing.

   AND IT IS A FILE, NOT AN OBJECT
     /var/lib/kubelet/seccomp/  <- localhostProfile is RELATIVE
     no kind: SeccompProfile. so posture depends on WHICH NODE.
     3 nodes of 5 provisioned = works until the scheduler picks 4.
     no admission check, no status field, nothing in kubectl get.

   PATHS NEED A DIFFERENT MECHANISM
     seccomp cannot say "not /etc/shadow" -- in openat the path
     is a POINTER into caller memory, so checking it can be raced.
     AppArmor does paths. securityContext.appArmorProfile (1.30+),
     NOT the old annotation, and never both. profile by NAME.
     this lab: "AppArmor is not enabled on the host" -- no LSM in
     Docker Desktop's kernel. syntax fallback: man 5 apparmor.d

   OR STOP SHARING THE KERNEL
     every filter above still calls YOUR node's kernel.
     RuntimeClass -> handler: runsc (gVisor) services syscalls
     in USER SPACE. different kernel, not a narrower door.

   FIVE REFUSALS, FIVE STAGES, ONE RULE
     RuntimeClass missing ... API SERVER, at apply. nothing stored.
     AppArmor unsupported ... kubelet, pre-create. Failed. TERMINAL.
     handler missing ....... kubelet, SANDBOX create. retries.
     profile file missing .. kubelet, CONTAINER create. retries.
     runAsNonRoot vs image . kubelet, container CONFIG. retries.
   each fires at the FIRST STAGE WITH ENOUGH INFORMATION.
   earlier = cheaper and more uniform. earlier = knows less.
   that trade is the rest of this act.
```

**Cleanup:**

```bash
kubectl delete pod sec s-rd s-unc l-nochmod l-minimal l-missing aa sandbox \
  --ignore-not-found
kubectl delete runtimeclass sandboxed --ignore-not-found
for n in netlab-control-plane netlab-worker; do
  docker exec "$n" rm -f /var/lib/kubelet/seccomp/profiles/no-chmod.json \
    /var/lib/kubelet/seccomp/profiles/minimal.json
done
```

> **You understand this when you can** say why capabilities were never a container boundary and give a syscall that proves it; read `Seccomp:` from `/proc/self/status` and say what `0` and `2` mean; state which of Docker and Kubernetes filters syscalls by default, and give the reason the other one does not; demonstrate with `unshare` that capabilities and seccomp block disjoint sets of operations; write a `Localhost` profile, say which directory it must live in and why `localhostProfile` has no leading slash, and explain why one logical operation needs four syscall names; prove that the filter is consulted before the capability check; explain why `Operation not permitted` cannot distinguish the two walls and name the one-line check that can; predict what a `defaultAction: SCMP_ACT_ERRNO` profile with four allowed syscalls does, and say whose code dies; explain why an allowlist cannot be derived by reading your own source; describe the fleet-consistency problem a `Localhost` profile introduces and the two ways it is solved; say why seccomp cannot filter on a path and which mechanism can; write an `appArmorProfile` stanza, name the annotation it replaced and what happens if you use both; distinguish a sandboxed runtime from a filter in one sentence; and, given a refusal, say which of the five stages it came from and whether waiting will help.

**Which raises:** every protection in these two lessons had to be *written on the Pod* — a `securityContext` here, a `seccompProfile` there, and a Pod that omits all of them is still perfectly valid and runs as root with fourteen capabilities and no filter. Which means none of it is a property of the cluster; it is a property of whoever last edited the YAML, and it is absent by default. **So how does a cluster refuse a Pod that simply does not say any of this — and where would such a refusal even live, given that the Pod is not wrong about anything?**

---

↑ **[Act X overview](README.md)** · Prev: **[What a container is allowed to do](01-what-a-container-may-do.md)** · Next: **[A default that refuses](03-a-default-that-refuses.md)** →
