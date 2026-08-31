# Who am I

Two lessons at the start of this act set up a frame you have used ever since. A namespace answers *what can this process **see***. A cgroup answers *how much can it **use***. [Lesson 01b](01b-cgroups.md) put them in a table, and you have been sorting failures into those two columns since — "it cannot reach it" against "it was killed."

Every command in both columns you ran as root, and nothing ever asked whether you should be. That is the third question, and the act has not posed it: **who is this process?**

You have also just seen where the answer lives. [The last lesson](05b-entering-what-you-did-not-name.md) listed `/proc/$PID/ns/` and found ten entries where `config.json` asked for five. One of the five it did not ask for is `user` — named once in [lesson 01](01-namespaces.md), in a parenthetical, and set aside as the kind that did not matter.

It is the one that decides what root means.

> **Predict first —** you are root in this container. You will drop to an ordinary user, UID 1000, and then ask the kernel for a new **user namespace** with `unshare -U --map-root-user sh`. Then, in there, `touch /etc/proof`. Commit to three things:
>
> - what `id -u` prints inside that namespace, given that UID 1000 asked for it and nobody granted UID 1000 anything
> - whether the `touch` succeeds
> - and if it fails, whether it fails for **the same reason** it would have failed a second earlier, as plain UID 1000

## The receipt

Every process has a file recording what its UIDs mean. Read yours, in the lab shell you have been root in all act:

```bash
cat /proc/self/uid_map
```

```
         0          0 4294967295
```

Three integers, and the format is `<inside> <outside> <range>`: **UID 0 in here is UID 0 out there, for all 4,294,967,295 of them.** That is the identity map — no translation at all.

Which is a statement about your container that is worth reading twice. Container root is not root-like, not root-for-this-namespace, not root-until-it-tries-something. It is the machine's root, wearing a different view of the filesystem and the network. Every isolation mechanism this act has built — the namespace, the cgroup, the bridge — narrows what a process can *reach*. None of them touched who it *is*, and this file is where that shows.

## An ordinary user, and what it cannot do

Drop to UID 1000. `setpriv` runs a command with a changed identity and nothing else changed — no login, no shell setup, no account required:

```bash
setpriv --reuid=1000 --regid=1000 --clear-groups sh -c '
  echo "id -u = $(id -u)"
  grep CapEff /proc/self/status
  cat /proc/self/uid_map
  mount -t tmpfs none /mnt
  touch /etc/proof'
```

```
id -u = 1000
CapEff:	0000000000000000
         0          0 4294967295
mount: /mnt: must be superuser to use mount.
       dmesg(1) may have more information after failed mount system call.
touch: /etc/proof: Permission denied
```

Three things worth separating.

`CapEff: 0000000000000000` is a bitmask of the privileged operations the kernel will let this process attempt, and it is **all zeroes** — none of them. Which of the 41 bits means what is [Act X lesson 01](../act-10-cluster-security/01-what-a-container-may-do.md)'s subject; here you only need the count, and the count is nought.

`uid_map` is **unchanged**. Dropping UID did not change what UIDs mean; it changed which one you are. The map belongs to the namespace, not the process.

And note that the two failures fail differently, which is easy to miss because both read as "no." Mounting a filesystem is a **privileged operation** — one of those 41 bits — and this process has none. Writing to `/etc` is not privileged at all: it is ordinary file permission against a `drwxr-xr-x root root` directory, which UID 1000 fails the way any user fails it. Keep them apart, because in a moment one of them changes and the other does not.

## A new user namespace

Same user. One extra command in front:

```bash
setpriv --reuid=1000 --regid=1000 --clear-groups unshare -U --map-root-user sh -c '
  echo "id -u = $(id -u)"
  grep CapEff /proc/self/status
  cat /proc/self/uid_map'
```

```
id -u = 0
CapEff:	000001ffffffffff
         0       1000          1
```

`id -u` says **0**. You did not authenticate, you did not `sudo`, and nothing was granted to you — an ordinary user created a namespace and became root in it, which is a thing the kernel simply allows.

The map says how: **inside-0 is outside-1000, range 1.** One UID, translated. `id` is not lying and never was; `id` reads the map, and the map now says something different. The mistake was assuming `id -u` answered a question about the machine when it has only ever answered a question about a namespace — the same correction Act I made about `/proc`, and the same shape as [lesson 05b](05b-entering-what-you-did-not-name.md)'s empty `ip netns list`.

And `CapEff: 000001ffffffffff` is **every capability the kernel has.** All 41 bits. Compare it to the line above, from the same user one command earlier: zero. Creating a namespace turned an unprivileged process into one holding the complete capability set.

## Full capabilities, less power

So try the two things that failed:

```bash
setpriv --reuid=1000 --regid=1000 --clear-groups unshare -U --map-root-user sh -c '
  ls -ld /tmp
  touch /etc/proof'
```

```
drwxrwxrwt    1 nobody   nobody        4096 Dec 17  2025 /tmp
touch: /etc/proof: Permission denied
```

Still denied — holding every capability there is.

And look at what `ls` says about `/tmp`. Outside this namespace that directory is `root root`; you can check with a plain `ls -ld /tmp` in your lab shell. Inside, it is **`nobody nobody`** — same directory, same inode, two different owners. Host UID 0 is not in your map, so the kernel has no number to report it as, and `nobody` (65534) is what it says instead.

So put the two measurements side by side, because between them they are the lesson:

| | `id -u` | `CapEff` | `touch /etc/proof` |
|---|---|---|---|
| plain UID 1000 | 1000 | 0 of 41 | denied |
| UID 1000, in a new user namespace | 0 | **41 of 41** | **denied** |

Going from no privileges to every privilege the kernel has changed nothing about that file. **A capability is not a key to the machine; it is permission to attempt an operation, and the operation is still checked against a map.** `/etc` belongs to a UID this namespace cannot name, so there is no version of "more privileged" that reaches it.

Which is the number worth distrusting from here on. A count of capabilities tells you what a process may *attempt*. It tells you nothing about what it can *reach* until you also know the map — and [Act X lesson 01](../act-10-cluster-security/01-what-a-container-may-do.md), which measures that count for a real container, is where the two get put together.

## Three refusals, three different errors

Now the sharpest evidence, and it is three lines of one command:

```bash
setpriv --reuid=1000 --regid=1000 --clear-groups unshare -U --map-root-user sh -c '
  mkdir -p /tmp/mine
  chown 0:0 /tmp/mine        ; echo "chown 0:0 /tmp/mine       -> $?"
  chown 5000:5000 /tmp/mine  ; echo "chown 5000:5000 /tmp/mine -> $?"
  chown 0:0 /tmp             ; echo "chown 0:0 /tmp            -> $?"'
```

```
chown 0:0 /tmp/mine       -> 0
chown: /tmp/mine: Invalid argument
chown 5000:5000 /tmp/mine -> 1
chown: /tmp: Operation not permitted
chown 0:0 /tmp            -> 1
```

One operation, three outcomes, and the errors are the lesson:

| command | result | why |
|---|---|---|
| `chown 0:0 /tmp/mine` | succeeds | your own directory, and UID 0 is in your map |
| `chown 5000:5000 /tmp/mine` | **`EINVAL` — Invalid argument** | your own directory, but 5000 is **not in the map**. The kernel is not refusing; it has no way to *express* that UID |
| `chown 0:0 /tmp` | **`EPERM` — Operation not permitted** | UID 0 is fine; the *file* belongs to someone outside your map, so this is a genuine refusal |

**`EINVAL` and `EPERM` are not two flavours of "no."** One says *forbidden*; the other says *unnameable*. A UID outside your map does not exist as far as this namespace's vocabulary goes, which is a stronger and stranger thing than being denied — and it is why user namespaces are a containment mechanism rather than a permission setting. You cannot be talked into granting access to a UID you cannot type.

(And notice that `mkdir -p /tmp/mine` succeeded at all. That is not a capability doing work either — `/tmp` is `drwxrwxrwt`, world-writable, so any user could have made that directory. No privilege was involved in either direction.)

Confirm the whole thing with the directory you did create, read from both sides:

```bash
setpriv --reuid=1000 --regid=1000 --clear-groups unshare -U --map-root-user \
  sh -c 'mkdir -p /tmp/mine; ls -lnd /tmp/mine'
ls -lnd /tmp/mine
```

```
drwxr-xr-x    2 0        0             4096 Aug 31 01:08 /tmp/mine
drwxr-xr-x    2 1000     1000          4096 Aug 31 01:08 /tmp/mine
```

**One directory, one inode, owned by 0 and by 1000 at the same time.** Nothing was copied, nothing was translated on disk — the number stored in the inode is 1000, and the namespace you read it from decides what number you are shown.

Which closes the third thing you committed to. `touch /etc/proof` failed both times, with the same message both times — and **not for the same reason.** As UID 1000 it was an ordinary permission check against a directory owned by someone else. As namespace-root holding all 41 capabilities it was a permission check the process was entitled to override, against an owner it could not name. Identical output, different mechanism, and only `uid_map` distinguishes them.

## What a rootless container is

One thing is still missing from the account, and it is the thing that makes any of this useful. UID 1000 could not `mount`. A container needs to mount — that is what a root filesystem *is*, and [lesson 05](05-who-does-this-for-you.md) had `runc` do it for you as root. So can an unprivileged user build a container at all, or does the whole stack need a privileged daemon somewhere?

Ask for the mount and PID namespaces alongside the user namespace, in one command:

```bash
setpriv --reuid=1000 --regid=1000 --clear-groups unshare -Urmp --fork sh -c '
  echo "id -u = $(id -u)"
  echo "pid   = $$"
  mount -t tmpfs none /mnt
  touch /mnt/mine && ls -la /mnt/mine'
```

```
id -u = 0
pid   = 1
-rw-r--r--    1 root     root             0 Aug 31 01:07 /mnt/mine
```

Four letters, and each is one of the entries [lesson 05b](05b-entering-what-you-did-not-name.md) listed out of `/proc/$PID/ns/`: `-U` user, `-r` the map-root shorthand for `--map-root-user`, `-m` mount, `-p` pid. And `pid = 1` is the PID namespace working — this process believes it is the first process on the machine.

The `mount` that failed for UID 1000 two sections ago now succeeds — same user, same kernel, same binary. The privilege it needed is real *over namespaces this process created*, so it can mount a filesystem nobody else will see and own files in it as root, and can do nothing at all to yours.

**That is the whole answer, and it is the sequence rather than any one flag:** an unprivileged user creates a user namespace first, becomes root inside it, and is then privileged enough to create the others. Podman and rootless Docker are that sequence with an image and a config file attached. This is what people mean by a rootless container.

(`--fork` is not optional here. A process cannot move itself into a PID namespace it has just created — only its children are born into it — so `unshare` has to fork to make `-p` mean anything.)

## The wall this leaves standing

One thing here is not the kernel's doing, and it is worth finding before you leave. From your own terminal — not the lab shell — run the same image you have been working in, with one flag removed:

```bash
docker run --rm --privileged nicolaka/netshoot sh -c 'id -u; unshare -U --map-root-user id -u'
docker run --rm              nicolaka/netshoot sh -c 'id -u; unshare -U --map-root-user id -u'
```

```
0
0

0
unshare: unshare failed: Operation not permitted
```

Same image, same command, running as **root** both times. One variable: `--privileged`. And `unshare -U` needs no capability at all — an unprivileged UID 1000 did it successfully three sections ago.

So something refused an operation that neither the user nor the privileges explain. Do not paste the flag at it and move on: this is a wall, and the thing on the other side is [Act X's seccomp lesson](../act-10-cluster-security/02-the-kernel-says-no.md), where a refusal that no capability accounts for finally gets a mechanism. What `--privileged` actually switches off is [Act X lesson 01](../act-10-cluster-security/01-what-a-container-may-do.md)'s subject. Carry both.

**And one rival worth naming**, because it is the first thing everybody proposes: do not be root at all — start the container as UID 1000 and be done. You have run exactly that, with `setpriv`, and you saw what it costs: zero capabilities, no `mount`, and anything in the image that expects root simply fails. The identity map was untouched, so UID 0 on that machine still meant UID 0; you had merely declined to be it.

A user namespace is the other move. It leaves the process root and changes what root *refers to* — so a container can run its package manager, `chown` its own files and bind a low port, and still be a UID the host does not know. That distinction is the one to carry: **decline the number, or redefine it.**

> **Check yourself —** A container writes to a host directory mounted into it and the files come out owned by UID 165536, which exists in no `/etc/passwd` anywhere. Nothing in the image or the manifest mentions that number. Where did it come from, and what single file inside the container would confirm it?

<details>
<summary>Answer</summary>

The container is running in a user namespace, and 165536 is the outside end of its map. Something allocated it a range of host UIDs — on a plain Linux host that is `/etc/subuid`, a file listing which UID ranges each user may claim; in Kubernetes it is the kubelet picking an unused block — and the container's UID 0 lands at the bottom of that range. The image and the manifest do not mention it because neither one chose it.

`/proc/self/uid_map` inside the container confirms it in one read: the second column will be 165536, and the third will be the width of the range. That is also the diagnostic, because there is no other file where a host UID the container never names is written down.

And the reason it looks alarming and is not: the files are owned by a UID nothing else on the host is, which is the point. The alternative — files owned by 0 — is the identity map, which is where this lesson started.

</details>

<!-- figure -->

```
   THE THIRD QUESTION

   namespace  ->  what can it SEE?     (lesson 01)
   cgroup     ->  how much can it USE? (lesson 01b)
   user ns    ->  WHO IS IT?           <- this lesson

   /proc/self/uid_map     <inside>  <outside>  <range>

     0    0    4294967295     the IDENTITY MAP. a plain container.
                              container root IS host root. no translation.
                              every other isolation in act IV narrowed what
                              a process could REACH. none touched WHO IT IS.

     0    1000    1           one UID, translated.
                              id -u says 0.  the host sees 1000.

   AND THEN THE PART THAT LOOKS BACKWARDS:

     as UID 1000          CapEff 0000000000000000   0 of 41 capabilities
     + unshare -U         CapEff 000001ffffffffff  41 of 41 capabilities
                          ...and STILL cannot touch /etc.

     because a capability is evaluated AGAINST A MAP:

       chown 0:0 /tmp/mine        -> ok      my dir, nameable UID
       chown 5000:5000 /tmp/mine  -> EINVAL  my dir, UNNAMEABLE UID
       chown 0:0 /tmp             -> EPERM   nameable UID, not my dir

       EINVAL is not a stronger EPERM. forbidden vs. does-not-exist-here.

   one directory, one inode, two owners:
       ls -lnd /tmp/mine   inside -> 0 0        outside -> 1000 1000
```

> **You understand this when you can** read `/proc/self/uid_map` and say what a plain container's three integers mean; explain how an unprivileged user becomes root without being granted anything; say why holding every capability the kernel has does not get you into `/etc`, in terms of the map; distinguish `EINVAL` from `EPERM` on a `chown` and say which one means "unnameable"; and say what `unshare -Urmp --fork` gives an unprivileged user that plain UID 1000 does not.

**Which raises:** every user namespace in this lesson, *you* asked for, one command at a time. That is not how containers get made. `runc` built one for you in [lesson 05](05-who-does-this-for-you.md) and its `config.json` never mentioned a user namespace at all, which is why the map came out as the identity map — so the whole of this is something a runtime has to be *told* to do.

Which puts a question on the layer above `runc`: what exactly does the thing that asks for a container get to specify, and who is doing the asking on a real node?

---

← Prev: **[Entering what you did not name](05b-entering-what-you-did-not-name.md)** · ↑ **[Act IV overview](README.md)** · Next: **[The kubelet's side](06-the-kubelets-side.md)** →
