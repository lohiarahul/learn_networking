# Entering what you did not name

You have a container running. `runc` built it, `/work/pid.txt` holds its PID, and you proved its network namespace is real by reading two inodes that differed. Everything in that sentence you own.

So go in and look at its addresses. The act has taught you exactly one way to run a command inside a network namespace, and you have used it since [lesson 01](01-namespaces.md): `ip netns exec`. It needs a name, and you have not given the container one — but `ip netns list` will tell you what names exist.

> **Predict first —** you are in the shell that started the container. Its PID is in `$PID` and its network namespace has an inode you have already read. Before you run anything: say what `ip netns list` prints, and say what its **exit code** is. Commit to both.

```bash
PID=$(cat /work/pid.txt)
ip netns list; echo "(exit=$?)"
```

```
(exit=0)
```

Nothing, and **exit 0**.

Sit with that for a moment, because the shape of it will come back. Not an error. Not "namespace not found." Not a warning that you might be looking in the wrong place. The tool ran, succeeded, and reported that there is nothing to report — while a namespace you can read the inode of is running two processes away.

## Where `ip netns` was looking

There is a second command in the act you have run without thinking about it, and it is the one that explains this:

```bash
ls /var/run/netns/
```

```
ls: /var/run/netns/: No such file or directory
```

The directory does not exist. That is where `ip netns list` was looking, and it found no directory, so it listed nothing, and exiting 0 on an empty list is the correct behaviour for a tool that lists things.

Which raises the real question: **what put anything in that directory in the first place?** In lesson 01 you ran `ip netns add red` and then `ip netns exec red`, and it worked. So `ip netns add` created something there.

It created a **bind mount**. A namespace exists as long as something holds it open — normally a process, through `/proc/<pid>/ns/net`. `ip netns add red` creates a fresh namespace and then bind-mounts its `/proc/self/ns/net` onto a new file at `/var/run/netns/red`, so the mount keeps the namespace alive even with no process in it, and gives it a name a human can type.

**A name, in `ip netns`, is a file in one directory.** That is the whole mechanism. And it means the tool's view of the world is not "namespaces on this machine" — it is "namespaces something chose to name." `runc` chose not to. Neither does `docker run`, `containerd`, or the kubelet. **`ip netns list` is blind to every container on the machine, and says so by saying nothing.**

## Name it yourself

You know where the namespace is — `/proc/$PID/ns/net`, which you read the inode of a moment ago — and you now know what a name is. So make one. Nothing here is a special command; it is the ordinary link you would make to any file:

```bash
mkdir -p /var/run/netns
ln -sf /proc/$PID/ns/net /var/run/netns/mybox
ip netns list
```

```
mybox
```

`ip netns add` makes a bind mount; a symlink is enough for `ip netns` to follow, so this shortcut works. And now the act's own tool works on a container it did not create:

```bash
ip netns exec mybox ip -o addr show          # -o: one line per address, easier to read here
```

```
1: lo    inet 127.0.0.1/8 scope host lo\       valid_lft forever preferred_lft forever
1: lo    inet6 ::1/128 scope host proto kernel_lo \       valid_lft forever preferred_lft forever
```

Loopback and nothing else — which is precisely what [lesson 01](01-namespaces.md) told you a fresh network namespace contains, and confirmation that `runc` did the namespace part of its job and none of the wiring. `config.json` asked for `{"type": "network"}` and got an empty one. The veth pair, the bridge and the NAT rule you built in [lesson 02](02-veth-and-bridge.md) and [lesson 03](03-iptables-and-nat.md) are exactly what `docker run` adds on top and `runc` alone does not.

Now prove the name points where you think it does, using the identity the act has used from the start:

```bash
readlink /proc/$PID/ns/net
ip netns exec mybox readlink /proc/self/ns/net
```

```
net:[4026533294]
net:[4026533294]
```

Same inode. **A name was the only thing missing** — not a permission, not a driver, not a runtime feature. The namespace was always addressable; `ip netns` simply had no entry for it, because entries are made by hand and nothing had made one.

## What the name is worth

Keep the name and use it, because there is one more thing to find out about it. Containers restart; this one has not yet. Stop it and look at what you built:

```bash
runc kill box KILL; sleep 2; runc delete -f box
ip netns list
ip netns exec mybox ip -o addr show; echo "(exit=$?)"
ls -l /var/run/netns/mybox
```

```
mybox
Cannot open network namespace "mybox": No such file or directory
(exit=255)
lrwxrwxrwx 1 root root 15 Aug 31 01:37 /var/run/netns/mybox -> /proc/47/ns/net
```

**`ip netns list` still says `mybox`.** The container is gone, the namespace is gone with it, and the name is still there — pointing at `/proc/47/ns/net`, a path that no longer exists. The name did not track anything; it was a link you made once, to a PID, by hand.

And that is worse than merely stale. PIDs are reused. Restart the container and it comes back with a different PID, so the name is now wrong rather than broken — and if some later process happens to get PID 47, `ip netns exec mybox` will run your command in **a namespace belonging to something else entirely**, reporting success the whole way.

So a name is a second thing you have to keep in sync with a process, in exchange for being allowed to type a word instead of a number. On a machine where containers come and go by the thousand, that is not a trade worth making.

```bash
rm /var/run/netns/mybox
```

## The tool that needs no name

So skip the name. There is a tool whose argument is the thing you actually have and which cannot go stale, because it *is* the process:

```bash
runc run -d -b bundle --pid-file /work/pid.txt box
PID=$(cat /work/pid.txt)
ip netns list; echo "(list exit=$?)"
nsenter -t $PID -n ip -o addr show
```

```
(list exit=0)
1: lo    inet 127.0.0.1/8 scope host lo\       valid_lft forever preferred_lft forever
1: lo    inet6 ::1/128 scope host proto kernel_lo \       valid_lft forever preferred_lft forever
```

Nothing named, and the same view of the same namespace. **`nsenter` addresses a namespace by a process that is in it** — `-t` for target — which is the addressing scheme a container actually gives you. `ip netns` needs a name that only exists if someone made it and stays correct only while nobody restarts anything; `nsenter` needs a PID, and a running container *is* a PID.

And `-n` is not a special case. Look at what the kernel offers for that process:

```bash
ls -1 /proc/$PID/ns/
```

```
cgroup
ipc
mnt
net
pid
pid_for_children
time
time_for_children
user
uts
```

**That listing is `nsenter`'s flag list.** `-n` net, `-m` mnt, `-p` pid, `-u` uts, `-i` ipc, `-C` cgroup, `-U` user, and `-a` for all of them. There is nothing to memorise: the flags are the entries in a directory you can list, because the namespace types *are* the entries in a directory you can list.

Two of those are worth noticing while you are here. There are **ten entries** where [lesson 05](05-who-does-this-for-you.md)'s `config.json` listed five — so five is what the OCI spec asks a runtime to create, not how many kinds exist. And one of the five it does not ask for is `user`, which [lesson 01](01-namespaces.md) named once, in a parenthetical, and set aside.

## Which namespaces did you actually join?

You have run `nsenter -t $PID -n` three times now without asking what the `-n` cost you. Find out, with two commands that differ by one letter:

```bash
nsenter -t $PID -n hostname
nsenter -t $PID -a hostname
```

```
docker-desktop
umoci-default
```

Two different hostnames from the same PID. With `-a` you got the container's, because you joined all ten. With `-n` you got **your own**, because you joined only the network namespace and kept your own UTS namespace — and, more to the point, your own **mount** namespace.

Which is worth testing, because it decides what you can run in there:

```bash
nsenter -t $PID -n which tcpdump
runc exec box which tcpdump; echo "(exit=$?)"
```

```
/usr/bin/tcpdump
(exit=1)
```

`tcpdump` is not in that container. It is a stock `alpine` image, and adding a debugging toolchain to a production image is how images get to a gigabyte. `runc exec` therefore has nothing to run. But `nsenter -t $PID -n` never changed your filesystem, so you are running **your** `tcpdump` on **their** network, and every packet it sees is the container's.

**That is the whole reason to prefer a partial move**, and it is why the lab container you have been living in since Act I is called `netshoot`: it is an image whose entire purpose is to be the filesystem you bring to somebody else's namespace.

`docker exec` and `runc exec` are the right tool most of the time and are not being replaced here. They stop working in one specific situation, which you have just produced: the container has the network you want to look at and not the tools you want to look with.

> **Check yourself —** You are on a node, and a container is restarting every few seconds. Each time you find its PID and run `nsenter -t $PID -n`, the PID is already gone by the time you press return. `ip netns list` on the node is empty. What is the shape of the problem, and what would you have to find for `nsenter` to be usable at all?

<details>
<summary>Answer</summary>

`ip netns list` being empty tells you nothing about this container — it is true of every node running containers, for the reason this lesson opened with. So the list is not the problem.

The problem is that `nsenter` addresses a namespace *through a process*, and you have no stable process. That is the one weakness of PID addressing, and it is the mirror image of the name's weakness: a name outlives the namespace, and a PID can die before you use it.

So for `nsenter` to be usable you would need some process that stays alive across the restarts and is in the namespace you want. Whether anything like that exists is not something this lesson can tell you — but [lesson 01](01-namespaces.md) asked you to carry exactly this question ("what is holding the namespace open between the death of one container and the birth of the next?"), and it is about to be worth an answer.

</details>

<!-- figure -->

```
   TWO WAYS TO ADDRESS ONE NAMESPACE

   ip netns exec <NAME>              nsenter -t <PID> -n
        |                                  |
        | needs an entry in               | needs a process that is in it
        v                                  v
   /var/run/netns/<NAME>              /proc/<PID>/ns/net
   a BIND MOUNT, created by            a symlink the kernel maintains for
   `ip netns add` and by nothing       every process, always, whether or
   else. runc/docker/containerd/       not anyone named anything
   the kubelet create NONE.
        |                                  |
        +----------- same inode -----------+
                  net:[4026533294]

   so:  ip netns list  ->  (nothing)   exit 0
        an EMPTY LIST is a claim about /var/run/netns,
        not a claim about the machine.

   and each handle fails the other way round:
        the NAME outlives the namespace  -- container gone, `mybox` still listed,
                                            now pointing at a dead (or REUSED) pid
        the PID dies before you use it   -- a restarting container has no
                                            stable process to address

   and the flags are just a directory listing:
        ls /proc/<PID>/ns/  ->  net mnt pid uts ipc cgroup user time
                                 -n  -m  -p  -u  -i   -C    -U        -a = all
        -n alone = THEIR network, YOUR filesystem   <- this is netshoot
```

> **You understand this when you can** say why `ip netns list` is empty on a machine full of containers and why exiting 0 is correct; explain what `ip netns add` creates that a container runtime does not; name what `nsenter -t` needs instead of a name and why a container always has one; and say what `nsenter -t PID -n tcpdump` gives you that `runc exec` on that container cannot.

**Which raises:** every namespace in that listing, you can now enter, and every one of them you entered as root without anything asking whether you were entitled to. One entry in it this act has still never opened — `user` — is the one that decides what "root" refers to in the first place.

---

← Prev: **[Who does this for you](05-who-does-this-for-you.md)** · ↑ **[Act IV overview](README.md)** · Next: **[Who am I](05c-who-am-i.md)** →
