# Plan — Phase 3: the thin spots (`nsenter`, user namespaces, `systemd`)

*Written 2026-08-31, as the detailed design for Phase 3 of
[`PLATFORM-DEPTH-PLAN.md`](PLATFORM-DEPTH-PLAN.md). Every count below was measured by `grep -rIl` /
`grep -rIc` over `networking-fundamentals/`, `exam-prep/`, `reference/` and `drills/`; word counts by
[`tools/remeasure.py`](tools/remeasure.py) and `wc -w`. Every command output quoted in §5 and §9 was
run against the real lab — `netlab:latest` and a two-node `kindest/node:v1.37.0` cluster — and is
pasted from the run, not paraphrased. Where a claim has **not** been run, §9 says so in those words.*

> **Status: shipped.** All three lessons plus the Act X insertion are live —
> [`act-4/05b`](networking-fundamentals/act-4-one-pretends-many/05b-entering-what-you-did-not-name.md),
> [`act-4/05c`](networking-fundamentals/act-4-one-pretends-many/05c-who-am-i.md),
> [`act-6/02b`](networking-fundamentals/act-6-control-plane/02b-what-starts-the-kubelet.md), and the
> `hostUsers` section in `act-10/01`. §12 records how each open question was actually resolved during the
> build, rather than leaving them as open questions in a shipped phase. Unlike Phase 2, this phase's
> central argument was never "here is a subject the course lacks" — it was **"here are three things the
> course already leaned on and never built, and in one case the repo printed the contradiction itself."**
> §5 was that argument, verified again against a rebuilt lab during the build and found to still hold.

---

## 1. The wall, measured — and it is a defect, not a subject

Phase 2 earned its place by naming a question the course could not answer. Phase 3's justification is
different in kind and, per word of new prose, stronger: these are not gaps in coverage, they are
**mechanisms used as though introduced**. That is the §2.1 River shape whose highest-value instance
Phase 1 already found — `runc` and `crictl` used 159 times and never introduced.

The audit, per thin spot. "Lesson uses" counts only reader-facing occurrences in
`networking-fundamentals/`, excluding `reference/` catalog pages and harness drill internals:

| Thin spot | Files | Total uses | Introduced? | Ever run by hand? |
|---|---|---|---|---|
| **`nsenter`** | 11 | 45 | **No** | **Never — the repo says so itself** |
| **user namespaces** | 3 | ~14 | **No — and Act IV explicitly disclaims it** | **Never** |
| **`systemd`** | 14 | ~30 reader-facing | **33 words, one line** | **A unit file is read once, with no output shown** |

The depth plan's own figures (`:371–373` — "6 hits", "15 hits") are close for `systemd` and an
**over**count for user namespaces, whose real teaching footprint is one clause. Both are corrected
here; §10 lists the plan edit.

**What makes this phase unusual, and what makes it cheap:** two of the three gaps are *already
documented in this repo, in writing, as gaps.* This is not an inference from a grep.

[`Toolbelt.md:146`](Toolbelt.md), on the course's own tool policy:

> *(`ip netns` is taught in Act IV and `unshare` in Act X; `nsenter` is named in prose and never run —
> [derive it yourself](reference/06-derive-it.md#ladder-1--derive-the-command).)*

And the contradiction, which is a live River violation in shipped prose. Act IV
[`01-namespaces.md:13`](networking-fundamentals/act-4-one-pretends-many/01-namespaces.md) tells the
reader the user namespace does not matter:

> "there are several kinds (PID, mount, user, network, and more), and the network one is **the only one
> this course cares about**."

Act X [`02-the-kernel-says-no.md:7`](networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md)
then hands them `unshare -U` as something they were taught:

> "`unshare -U` creates a new **user namespace** — **Act IV's mechanism**, and the one an attacker
> reaches for first, because inside a fresh user namespace you are root and can then create the other
> namespace types."

Act IV introduced neither `unshare` nor the user namespace. It named it once, in a parenthetical, to
say it was out of scope. **The citation is phantom** — the same defect class as Act V lesson 02's
phantom citation, found and fixed in Phase 1 after going unnoticed since it was written. It is worse
than a missing lesson, because a reader who trusts the citation will go looking for material that does
not exist and conclude they forgot it.

**The carried question for the phase**, in the idiom the acts use:

> **You have been typing a name. What is on the other side of it?**

That is not a retrofit — it is literally true of all three, and §3 shows it is the same mechanism three
times.

---

## 2. Why these three together, and why not a new act

Phase 3 is **not** an act. It is three lessons placed inside acts that already exist, plus one
insertion. That decision is forced, not chosen, and the reasons are worth recording because they also
set the phase's budget:

1. **The River fixes the position.** Act X 02 already uses `unshare -U`. So the user-namespace
   mechanism must land *before* Act X — which means Act IV, the act that owns namespaces. A new Act XII
   could not repair a citation pointing backwards.
2. **`hostUsers: false` cannot go in Act IV.** Act IV is pre-Kubernetes; the reader does not know what a
   Pod is until Act V. So the user-namespace material **must split** across two acts: mechanism in
   Act IV, Kubernetes consequence in Act X 01. §6 does exactly that, and this is the only place in the
   phase where one subject spans two acts.
3. **No new act shape.** `shape.act-files` demands README + test-yourself + diagnose + in-the-wild per
   act. All three target acts have all four already. That is the single biggest saving against Phase 2,
   whose §10 named the obligations as where the time went.

**Placements**, each chosen because the motivated entry already exists and costs nothing to build:

| New file | Sits after | Why there |
|---|---|---|
| `act-4/01c-who-am-i.md` | `01b-cgroups.md` | Act IV establishes a two-question frame — namespaces answer *what can it **see*** ([`01-namespaces.md:103`](networking-fundamentals/act-4-one-pretends-many/01-namespaces.md)), cgroups answer *how much can it **use*** ([`01b-cgroups.md:111`](networking-fundamentals/act-4-one-pretends-many/01b-cgroups.md)). **The third question, *who is it*, is never posed.** `01c` puts it exactly where the first two were established. |
| `act-4/05b-entering-what-you-did-not-name.md` | `05-who-does-this-for-you.md` | Lesson 05 has the reader `runc run` a container and then run `ls -la /proc/$PID/ns/net` against `/proc/self/ns/net`. **The reader already holds the PID and has already compared the inodes.** `nsenter`'s wall is one command away, and needs no new setup. |
| `act-6/02b-what-starts-the-kubelet.md` | `02-static-pods.md` | The 33-word introduction is at `02-static-pods.md:23`, and lesson 02's whole boot-order argument terminates on the parenthetical "(systemd unit, needs nothing)" at `:138` — with "unit" undefined. |
| *(insertion)* `act-10/01-what-a-container-may-do.md` | at its `:296` heading | That heading is **"Who you are, decided much too late"** and currently covers only `runAsUser` / `runAsNonRoot` / `fsGroup` — fields that pick a number. `hostUsers: false` is the field that changes what the number *means*. Zero hits repo-wide. |

**Cost of the placement, and it is real:** inserting `01c` and `05b` into Act IV renumbers nothing (both
are `b`/`c` suffixes, the convention `01b`, `02b`, `08b`, `08c` already establishes) but **does** break
the nav-footer chain in four files, and Act IV's `README.md`, `test-yourself.md` and `diagnose.md` all
describe an act that no longer matches. §10 lists every one. Phase 1's lesson was that this is where the
time goes.

---

## 3. The idea that holds the three together

They look unrelated — a namespace type, a debugging tool, an init system. They are the same move three
times, and stating it is what turns three chores into a phase:

**Every one of them is a name the reader types confidently whose referent the course never opened.**

```
   THE NAME YOU TYPE          WHAT IS ACTUALLY ON THE OTHER SIDE           WHERE
   ------------------------------------------------------------------------------
   ip netns exec mybox        a BIND MOUNT in /var/run/netns/.             05b
                              a container has NO name there -- only a
                              PID holding the namespace open, and an
                              inode. ip netns list prints NOTHING and
                              EXITS 0.

   id -u  ->  0               a number that means something only
                              relative to a MAP. /proc/self/uid_map       01c
                              is the receipt, and in a plain container
                              it reads  0 0 4294967295  -- no
                              remapping at all.

   systemctl restart kubelet  a UNIT FILE on disk, plus a drop-in that
                              overrides it, placing the process in a      02b
                              CGROUP SLICE -- the same cgroup files
                              Act IV made you read by hand.
   ------------------------------------------------------------------------------
   in all three: the name resolved to something the reader already owns,
   and nobody ever turned it over.
```

The second claim, which is the phase's version of Act VIII's *"infeasible is a number"*:

**In all three cases the thing behind the name is a file, and the reader has already been taught to
read files.** `/var/run/netns/<name>` is a bind mount. `/proc/self/uid_map` is three integers.
`/etc/systemd/system/kubelet.service` is an INI file whose `Slice=` line names a directory under
`/sys/fs/cgroup`. Nothing in this phase requires a new *kind* of skill — which is precisely why the gaps
are cheap to close and inexcusable to leave open.

---

## 4. What this phase declines, and why

| Named | Decision | Why |
|---|---|---|
| **A systemd unit-writing tutorial** | **Decline.** | `systemctl enable`, timers, targets, socket activation and dependency ordering are a subject, not a mechanism the course needs. `02b` reads *one* real unit — the kubelet's, which the reader already depends on — and writes nothing. |
| **systemd timers as a cron replacement** | **Decline.** | Nothing in the course schedules anything. Would be coverage for its own sake. |
| **`journalctl`'s full query surface** | **Decline as a tour, keep three flags.** | `-u`, `--since`, `-n` earn their place because [`exam-prep/kubectl-speed.md:175`](exam-prep/kubectl-speed.md) already drills `-n 50`, a flag **no lesson has ever shown**. Fix that specific hole; skip `--priority`, `-o json`, cursors. |
| **Rootless Kubernetes (usernetes, rootless kubelet)** | **Decline; one `in-the-wild` line.** | Running the whole control plane rootless is a real project and a rabbit hole. `01c` teaches the primitive; Act X 01's insertion teaches the Pod-level field that actually ships. |
| **`podman` as a rootless demo** | **Decline.** | It would install a second container runtime to demonstrate a kernel feature `unshare -U` shows directly. [`Toolbelt.md:153`](Toolbelt.md) already names it; that is the right depth. |
| **`nsenter` as a tool tour** | **Decline the flag matrix, keep the wall.** | The lesson is *why a PID-addressed entry has to exist at all*. `-t/-n/-m/-p/-a` follow from `/proc/PID/ns/` once the wall is felt. |
| **User namespaces as a container-escape lesson** | **Decline — Act X already owns it.** | Act X 02 uses `unshare -U` as an escape primitive and does it well. `01c`'s job is to make that lesson's citation *true*, not to duplicate its argument. |
| **`systemd`, the unit file, the journal, `uid_map`, `nsenter -t`** | **KEEP.** | Each is load-bearing for prose already shipped. §5 shows exactly which. |

**And the decline that matters most:** this phase adds **no new tools to the lab image** and installs
nothing. `nsenter`, `unshare`, `systemctl` and `journalctl` are all present already — `systemctl` and
`journalctl` inside the kind nodes, the other two in `netlab:latest`. Phase 2 needed four containers and
a memory budget; this needs none.

---

## 5. The River repairs, quoted — the actual argument for building this

### 5.1 `nsenter`: 45 uses, never run, and the repo admits it

**Measured:** 45 occurrences across 11 files. In `networking-fundamentals/` it appears **four times**:
once in [`00-orientation/README.md:27`](networking-fundamentals/00-orientation/README.md) as a name in a
list of what netshoot contains, and three times in
[`act-4/in-the-wild.md:52,55,83`](networking-fundamentals/act-4-one-pretends-many/in-the-wild.md) — the
"what this looks like in the real world" page, not a teaching lesson. Everything else is `reference/`.

The reference catalog documents it properly ([`reference/tools/nsapi/nsenter.md`](reference/tools/nsapi/nsenter.md),
7 uses) and [`reference/06-derive-it.md`](reference/06-derive-it.md) builds a *derive-it ladder* for it —
a page whose whole premise is that the reader can reconstruct a command they were never given. That is a
good page. It is not a substitute for the mechanism, and `Toolbelt.md:146` says as much in the repo's
own voice.

**Why it is load-bearing rather than merely absent** — this is the part that makes it a defect. Act IV
teaches exactly one way to enter a namespace: `ip netns exec`. Every by-hand namespace in the act is
created with `ip netns add`. And that tool **cannot see a single container on the machine.** Run against
the real lab:

```
$ docker run --rm --privileged --pid=host netlab:latest sh -c 'ip netns list; echo "(exit=$?)"; ls /var/run/netns/'
(exit=0)
ls: /var/run/netns/: No such file or directory
```

Empty output. **Exit code 0.** No error, no warning, no hint. Meanwhile the namespace is
demonstrably there:

```
$ docker run --rm --privileged --pid=host netlab:latest readlink /proc/8592/ns/net
net:[4026534008]
```

An inode — which is *precisely* the identity Act IV taught: "The identity of a network namespace **is
its inode number**" ([`01-namespaces.md:46`](networking-fundamentals/act-4-one-pretends-many/01-namespaces.md)).
So the reader finishes Act IV holding a tool that silently reports nothing for every namespace they will
ever actually care about, and the act never says so.

### 5.2 User namespaces: a phantom citation, and a canonical list with a hole in it

**Measured:** three files. `uid_map`, `gid_map`, `subuid`, `subgid`, `newuidmap`, `hostUsers`,
`UserNamespacesSupport` — **zero hits repo-wide.** "rootless" — two hits, both right-hand table cells.

§1 quoted the phantom citation. Two further findings compound it:

**The five-namespace list omits `user`, and the course examines the reader on it.** Act IV lesson 05 has
the reader run `jq '.linux.namespaces' bundle/config.json` and presents the result as the complete OCI
vocabulary — `pid`, `network`, `ipc`, `uts`, `mount`. [`README.md:24`](networking-fundamentals/act-4-one-pretends-many/README.md)
calls it "the same five namespaces and cgroup", and
[`test-yourself.md:59`](networking-fundamentals/act-4-one-pretends-many/test-yourself.md) asks a question
premised on "`config.json`'s `linux.namespaces` array lists five namespace types". A reader who
internalises that list has learned a canon from which the security-relevant namespace is missing.

**The rootless equation is asserted in a table cell with no lesson behind it.**
[`reference/tools/nsapi/unshare.md:33`](reference/tools/nsapi/unshare.md):

> `unshare -Urm --fork <cmd>` | user + mount + PID, unprivileged — **what a rootless container is**

That is a true and genuinely illuminating sentence, and the command is never run anywhere in the course.

**What the mechanism actually shows, measured.** Baseline first — a plain container, which is the
comparison the lesson turns on:

```
$ docker run --rm netlab:latest cat /proc/self/uid_map
         0          0 4294967295
```

Inside-0 maps to outside-0, over the entire UID range. **Container root *is* host root**, and that one
line is the whole reason the feature exists. Now the same process inside a user namespace, started as an
unprivileged user:

```
$ docker run --rm --security-opt seccomp=unconfined --user 1000 netlab:latest sh -c '
    echo "outside userns: id -u = $(id -u)"
    unshare -U --map-root-user sh -c "echo \"inside userns: id -u = \$(id -u)\"; cat /proc/self/uid_map"'
outside userns: id -u = 1000
inside userns: id -u = 0
         0       1000          1
```

`id -u` says `0`. The map says inside-0 is outside-1000, range 1. **`id` is not lying — it is answering
a question about a namespace, and the reader thought it was answering a question about the machine.**
That is the same structure as Act X's "at what moment does this refuse", and it is the lesson.

**Then the surprise, which is better than the setup** (§9 risk 1 covers the seccomp flag):

```
id -u = 0
capabilities: CapEff:	000001ffffffffff
can I write a root-owned dir? touch: /etc/proof: Permission denied
can I chown to a UID not in my map? chown: /tmp: Invalid argument
```

`CapEff: 000001ffffffffff` is **the full capability set** — every capability the kernel has. And the
process cannot create a file in `/etc`. Act X lesson 01's central measurement is that container root
holds *14 of 41* capabilities; here the reader holds **41 of 41 and is less dangerous**, because
capabilities are evaluated against a namespace. That single contrast is worth the lesson on its own.

And the `chown` failure is **`EINVAL`, not `EPERM`** — "Invalid argument", not "Permission denied". The
kernel is not refusing; it is saying UID 5000 **cannot be named** in this namespace. Two different
errors for two different reasons, in one command, and the distinction is exactly the one Act X 02 built
its seccomp-versus-capabilities argument on.

**The Kubernetes payoff exists and works.** On the lab cluster (`v1.37.0`,
`kubernetes_feature_enabled{name="UserNamespacesSupport"} 1`), a Pod with `hostUsers: false`:

```
$ kubectl logs userns-demo
uid=0
         0  188940288      65536
```

Container UID 0 is host UID **188940288**, over a 65536-wide range the kubelet allocated. The Pod thinks
it is root; the node thinks it is a UID nothing else owns. That is the insertion into Act X 01, and it
turns that lesson's "it is root, and it is not root" from a paradox into a design decision.

### 5.3 `systemd`: a 33-word introduction carrying ~30 uses across four acts

**Measured:** 14 files. The introduction is
[`act-6/02-static-pods.md:23`](networking-fundamentals/act-6-control-plane/02-static-pods.md), and it is
this, in full:

> "The kubelet is not a Pod. It is a plain background service on the node, started at boot by the init
> system — `systemd`, on these nodes as on most Linux hosts — and holding no cluster state at all.
> `systemctl` is how you ask systemd about one of its services:"

Then `systemctl is-active kubelet` and `systemctl cat kubelet | grep -A3 ExecStart` — and **no output
block for either.** Line 30 moves on to "And it takes a config file." So the only command in the entire
course that puts unit-file text on the reader's screen shows them none of it, and `ExecStart` — which
appears exactly once in the repo, inside that pipe — is never defined.

What the course *does* teach well, and what `02b` must therefore not rebuild: the **architectural** fact
that the kubelet is a package under an init system while everything else is a container under a
manifest. That is stated four times, developed properly in
[`06-upgrades-and-version-skew.md:45`](networking-fundamentals/act-6-control-plane/06-upgrades-and-version-skew.md),
and it is the spine of Act VI's upgrade argument. It is not the gap.

The gap is systemd as a thing. Concretely, five dependencies the course creates and never discharges:

1. **"Unit" is used and never defined.** `02-static-pods.md:138`'s figure — `kubelet (systemd unit,
   needs nothing)` — is the line on which the whole boot-order argument terminates.
2. **Restart semantics are silently load-bearing, twice.**
   [`09-two-machines-from-nothing.md:157`](networking-fundamentals/act-6-control-plane/09-two-machines-from-nothing.md)
   says "the kubelet restarts in a loop"; `diagnose.md:802` runs `systemctl stop kubelet` and it stays
   stopped for a whole drill. **A crashed unit comes back and a stopped unit does not** — the asymmetry
   the drill depends on is never stated. It is `Restart=always`, and it is in the file.
3. **`daemon-reload` appears twice and is never explained** (`09-...:347,365`). It is meaningless
   without the unit-file-on-disk model, which does not exist yet.
4. **`SystemdCgroup` is a third, unbridged meaning of the word.** `09-...:143–157` has the reader flip
   `SystemdCgroup = true` in containerd's config and accept that `cgroupDriver: systemd` is "the only
   correct answer" on a systemd machine. Meanwhile
   [`act-4/01b-cgroups.md`](networking-fundamentals/act-4-one-pretends-many/01b-cgroups.md) — the
   cgroups lesson, the natural home for this — contains **zero** mentions of systemd.
5. **The journal gets one clause**, at `08-when-the-control-plane-breaks.md:137`, which correctly
   back-references lesson 02. But `journalctl` is named on page 1 of that same lesson (`:13`, in a
   figure, 124 lines earlier) as a Question-4 dependency, and the act's diagnostic argument rests on
   evidence being **"JOURNAL-ONLY"** (`:255`) — a property of a store the reader was told one thing
   about. Never mentioned: that it is a structured binary store rather than a text file, or that it can
   be volatile, so `--since` may legitimately find nothing after a node reboot.

**And two structural findings that make this the phase's highest-value lesson:**

- **There is no reference page for `systemctl` or `journalctl`.** `reference/tools/` holds 78 pages
  including `capsh`, `readlink` and `etcdutl` — but not the two tools Act VI's Question 4 depends on.
  Both are already in `SHELL_COMMANDS`, so the harness classifies them as runnable commands the course
  issues; they are simply undocumented. §10 adds them.
- **Acts I–V and VII–XI contain zero mentions.** The reader arrives at `02-static-pods.md:23` with
  nothing and is expected to carry `systemctl` and `journalctl` for ~30 further occurrences, including
  `systemctl is-active containerd` promoted into Act VI's three-drill diagnostic branch
  (`diagnose.md:1158`) as a reflex they are assumed to own, and two uses in Act X 07 four acts later
  with no back-reference at all.

**What the unit file actually contains, measured** — and it is a better lesson than any invented one,
because it connects straight back to Act IV:

```
$ docker exec netlab-control-plane systemctl cat kubelet
# /etc/systemd/system/kubelet.service
[Unit]
ConditionPathExists=/var/lib/kubelet/config.yaml
[Service]
ExecStart=/usr/bin/kubelet
Restart=always
StartLimitInterval=0
RestartSec=1s
CPUAccounting=true
MemoryAccounting=true
Slice=kubelet.slice
KillMode=process
```

Four teachable things in twelve lines, none invented: a **condition** that makes the unit refuse to
start rather than crash-loop (kind's own comment says it is there "to avoid crashlooping"); the
**restart** trio that explains both the loop in lesson 09 and the stop in drill 9; **accounting**
switches; and a **slice**.

That slice is the payoff. `systemctl show` and `cat` return the same number:

```
$ docker exec netlab-control-plane systemctl show kubelet -p CPUUsageNSec -p MemoryCurrent
CPUUsageNSec=1638057998000
MemoryCurrent=63459328

$ docker exec netlab-control-plane cat /sys/fs/cgroup/kubelet.slice/kubelet.service/cpu.stat
usage_usec 1638058645
```

`1638057998000` ns is `1638057998` µs against a `cpu.stat` of `1638058645` µs — **the same number, read
647 microseconds apart.** `systemctl show` is a formatted read of the cgroup files Act IV made the
reader `cat` by hand, and `CPUAccounting=true` in the unit is what turned them on. So systemd is not a
monitoring system; it is a process manager that owns a cgroup tree — which retroactively earns
`09-...`'s `cgroupDriver: systemd` claim, closes finding 4 above, and lands Act XI's creed a fourth
time: **a metric is a file a process keeps about itself.**

---

## 6. The lessons

Three teaching files and one insertion. Each states the wall it inherits, the mechanism, the rival it
must beat, the prediction, the measured surprise, and what it leaves open. **Write in §9's order, which
is not this order.**

### `act-4/01c-who-am-i.md` (~2,800 words)

**Wall.** Lesson 01 answered *what can it see*, `01b` answered *how much can it use*. Both were about
the machine's resources. Neither asked *who is asking* — and lesson 01 said the user namespace was the
one kind that did not matter.

**Mechanism.** `cat /proc/self/uid_map` in a plain container → `0 0 4294967295`, the identity map, which
is the security problem stated as three integers. Then `unshare -U --map-root-user` as an unprivileged
user, and the same file reading `0 1000 1`. Then the capability contrast (`CapEff: 000001ffffffffff`,
full set, and `touch /etc/foo` still denied), and the `EINVAL`-vs-`EPERM` distinction on `chown`.
Finally `unshare -Urm --fork` — the command
[`unshare.md:33`](reference/tools/nsapi/unshare.md) already calls "what a rootless container is",
finally run.

**Rival.** `runAsUser: 1000` — which Act X 01 will teach, and which changes *which* UID you are without
changing *what UID 0 means*. Name it as the thing this is not; Act X 01's insertion closes the loop.

**Predict first.** *"You will run `unshare -U --map-root-user` as UID 1000, then `id -u`, then `touch
/etc/foo`. Commit to all three outputs — and to whether the third fails for the same reason it would
have failed a moment ago."*

**The measured surprise.** Full capability set, less power. And the error for `chown 5000` is *Invalid
argument*: the UID is not forbidden, it is unnameable.

**Leaves open.** You can be a UID the host does not consider privileged. Nothing here says whether the
thing that *starts* containers will do this for you — and (for Act X) whether Kubernetes exposes it.

**New tools:** `unshare` — which moves its "Taught in" attribution from Act X 02 to here (§10).
**Exam value:** none. Say so.

### `act-4/05b-entering-what-you-did-not-name.md` (~2,200 words)

**Wall.** Lesson 05 had `runc` build a container and the reader compare `/proc/$PID/ns/net` against
`/proc/self/ns/net`. The reader holds a PID and two inodes. Now enter it — with the only tool the act has
taught.

**Mechanism.** `ip netns list` → nothing, **exit 0**, and `/var/run/netns/` does not exist. The tool is
not broken and not complaining; it only ever knew about *named* namespaces, and a name is a bind mount
that `ip netns add` creates and a container runtime does not. Then the fix in one line — and the reader
builds the naming mechanism by hand rather than being told about it:

```
$ ln -sf /proc/$PID/ns/net /var/run/netns/mybox
$ ip netns list
mybox
$ ip netns exec mybox ip -o addr show | awk '{print $2, $4}'
lo 127.0.0.1/8
eth0 172.17.0.2/16
$ readlink /proc/$PID/ns/net        # net:[4026534008]
$ ip netns exec mybox readlink /proc/self/ns/net   # net:[4026534008]
```

Same inode, both ways. **A name was the only thing missing.** *Then* `nsenter -t $PID -n` as the tool
that skips the naming step because it addresses the namespace by the process holding it open — and
`/proc/PID/ns/` becomes the flag list: `-n`, `-m`, `-p`, `-u`, `-i`, `-a`.

**Rival.** `docker exec` / `kubectl exec`, which work and are correct — until the container has no shell,
or is crash-looping, or you need to be in *only* its network namespace with your own filesystem. That
last case is what `nsenter -t PID -n tcpdump` is, and it is why netshoot exists.

**Predict first.** *"You have a running container's PID. Before you run anything: say what `ip netns
list` prints, and what its exit code is."*

**The measured surprise.** Exit 0 and silence — the failure mode Act XI lesson 05 spent a page on
(*absence is not zero and it is not false*), arriving in Act IV, one act before Kubernetes.

**Leaves open.** Nothing new. This lesson exists so that `kubectl debug`, netshoot and `nsenter1` stop
being magic, and so `reference/06-derive-it.md`'s ladder has a floor.

**New tools:** `nsenter`, finally run. **Exam value:** none directly, but it is the mechanism under
`kubectl debug`, which is examinable.

### `act-6/02b-what-starts-the-kubelet.md` (~3,200 words)

**Wall.** Lesson 02 said the kubelet is "a plain background service… started by the init system" and
piped its unit file through `grep` without showing it. Everything after that — `restart`, `stop`,
`daemon-reload`, `journalctl -u`, `is-active containerd` — assumes a model the reader was not given.

**Mechanism.** Read the whole unit (§5.3), and derive from it, in this order, because each answers a
question the course already raised and left:

1. **`ConditionPathExists`** — why a missing config makes the unit *refuse* rather than crash-loop, and
   kind's own comment saying that is deliberate.
2. **`Restart=always` + `RestartSec=1s`** — the asymmetry drill 9 depends on: a crash comes back, a
   `stop` does not. This retroactively explains `09-...:157`'s loop.
3. **The drop-in.** `/etc/systemd/system/kubelet.service.d/10-kubeadm.conf`, and the
   `ExecStart=` -then-`ExecStart=…` clear-and-reset pattern that trips everyone, plus
   `EnvironmentFile=-` where the `-` means "optional". **This is how kubeadm configures the kubelet** —
   a genuine Act VI deepening, not a systemd tour.
4. **`daemon-reload`** — now meaningful: unit files are on disk and systemd caches them.
5. **`Slice=` + `CPUAccounting=`** → the cgroup identity of §5.3. Act IV walks back in, and
   `cgroupDriver: systemd` stops being an assertion.
6. **The journal** — a structured store, not a file; `-u`, `--since`, and `-n` (closing
   `kubectl-speed.md:175`'s untaught flag); and that it can be volatile, so "nothing since the reboot"
   is a real answer rather than a broken command.

**Rival.** `docker exec … ps aux | grep kubelet` — which tells you it is running and nothing about what
will happen when it stops, what started it, or where its output went.

**Predict first.** *"The kubelet's config file is missing. Predict whether `systemctl is-active kubelet`
says `failed`, `inactive`, or `activating` — and whether the journal will show a crash."*

**The measured surprise.** `systemctl show -p CPUUsageNSec` and `cat …/cpu.stat` return the same number.
The service manager and the cgroup file are one mechanism.

**Leaves open.** Nothing — this is a repair, not a thread. It closes lesson 08's Question 4 dependency
and Act VI's `cgroupDriver` assertion.

**New tools:** `systemctl`, `journalctl` — both gaining their first reference pages (§10).
**Exam value: real, and the highest in the phase.** See §8.

### Insertion — `act-10/01-what-a-container-may-do.md`, at `:296` (~500 words)

Into the existing heading **"Who you are, decided much too late"**, after `fsGroup`. `runAsUser` picks a
number; `hostUsers: false` changes what the number means. The measurement is §5.2's
`0 188940288 65536`, and the payoff is that the lesson's own "it is root, and it is not root" becomes a
thing you can *configure* rather than a paradox you must accept. Cross-link back to `01c` for the
mechanism and forward to Act X 02 for why the namespace is what an escape reaches for.

Keeps the lesson at ~4,300 words, under the 10,000 ceiling and inside Act X's own distribution.

---

## 7. The drills

Four, and the phase's total is deliberately small — three of the four attach to existing `diagnose.md`
pages rather than creating new ones.

| # | Where | Symptom | Root cause | Verified by |
|---|---|---|---|---|
| **A** | `act-4/diagnose.md` | `ip netns exec` says the namespace does not exist; the container is plainly running | `ip netns` only sees bind mounts in `/var/run/netns`; a runtime makes none | `nsenter -t PID -n` returns the container's own address, **and** the two `/proc/*/ns/net` inodes match |
| **B** | `act-4/diagnose.md` | A process is UID 0, holds every capability, and cannot write to `/etc` | Capabilities are evaluated per user namespace; the file's owner is unmapped | `CapEff` full **and** the write denied **and** `uid_map` read to explain which |
| **C** | `act-6/diagnose.md` | `systemctl restart kubelet` has no effect after an edit | The edit was to a unit file; systemd is serving its cache. `daemon-reload` missing | the new `ExecStart` visible in `systemctl show`, and the kubelet running with it |
| **D** | `act-6/diagnose.md` | The kubelet is `inactive`, not `failed`, and the journal shows no crash | `ConditionPathExists` unmet — the unit refused rather than ran | `systemctl show -p ConditionResult` false, and the unit active again once the path exists |

Drill **B** needs no cluster and no kind — one `docker run`. Drill **A** needs Docker only. **C** and
**D** need the kind cluster. That ratio matters for the same reason Act X and Act XI stated theirs: it
tells the reader which drills they can do on a train.

**Deliberately not a drill:** the journal's volatility. "Run a command, reboot the node, observe the
absence" is slow, destructive to the lab, and the insight lands in one sentence of prose.

---

## 8. Exam accounting, honestly

**This is the first phase in the depth plan that closes a real exam gap, and it closes it in one lesson.**

| Bullet | Current state | What Phase 3 changes |
|---|---|---|
| CKA · Troubleshoot clusters and nodes | ✅ **covered, above depth** — [`cka-domain-map.md:44`](exam-prep/cka-domain-map.md) cites `journalctl -u kubelet` by name, and `:56` says "`crictl` fluency is repeatedly named as a differentiator" while naming `journalctl` in the same descent | Adds the **mechanism**: what a unit is, why a stopped kubelet stays stopped and a crashed one does not, what `daemon-reload` is for, and what the journal is. The bullet was marked covered on the strength of a command the course never explained — the same shape as Act XI §5.2's `/var/log/pods` finding |
| CKA · `journalctl -n` | Drilled in [`kubectl-speed.md:175`](exam-prep/kubectl-speed.md) as "worth rehearsing until it's reflex" | **A flag no lesson has ever shown.** `02b` shows it |
| CKS · `falco` as a systemd unit | [`cks-domain-map.md:350`](exam-prep/cks-domain-map.md) tells the reader to expect this on exam hosts | Assumes unit-file familiarity the course does not provide. `02b` provides it |
| **User namespaces / `hostUsers`** | — | **Not examined.** Zero hits in either domain map |
| **`nsenter`** | — | **Not examined.** Zero hits. High practical value; state it plainly |

So the phase splits, and the split should be stated in the optional-track row rather than smoothed over:
**`02b` belongs on Route B's path** (step 4, beside Act VI's diagnostic descent and Act XI lesson 01's
node-file section, which took the same exception for the same reason). **`01c` and `05b` are optional
track** — the most useful unexaminable material in Act IV.

---

## 9. The lab, and what is verified

**Nothing new is installed.** `nsenter` and `unshare` are in `netlab:latest`; `systemctl` and
`journalctl` are inside the kind nodes, where `systemd` is PID 1 (verified: `ps -p 1 -o comm=` →
`systemd`). No Prometheus, no extra containers, no memory budget. That is the phase's chief practical
advantage over Phase 2.

**Verified on the real lab during this plan** — every output in §5 is pasted from these runs:

- `ip netns list` empty with **exit 0** inside `--privileged --pid=host`; `/var/run/netns/` absent. ✅
- `readlink /proc/PID/ns/net` → `net:[4026534008]` for a running container. ✅
- The `ln -s` bridge: `ip netns list` → `mybox`, `ip netns exec mybox` returns the container's own
  `eth0 172.17.0.2/16`, and both inodes match. ✅
- `nsenter -t PID -n ip -o addr show` reproduces the container's view exactly. ✅
- Plain container `uid_map` → `0 0 4294967295`. ✅
- `unshare -U --map-root-user` as `--user 1000` → `id -u` = 0, `uid_map` = `0 1000 1`. ✅
- `CapEff: 000001ffffffffff`, `touch /etc/proof` → `Permission denied`, `chown 5000 /tmp` →
  **`Invalid argument`**. ✅
- `kubelet.service` + `10-kubeadm.conf` contents as quoted in §5.3, including `ConditionPathExists`,
  `Restart=always`, `RestartSec=1s`, `Slice=kubelet.slice`, `CPUAccounting=true`, and the
  `ExecStart=`-clear-then-reset pattern. ✅
- `systemctl show -p CPUUsageNSec` ≡ `cpu.stat usage_usec` (1638057998000 ns vs 1638058645 µs, 647 µs
  apart); `MemoryCurrent` ≡ `memory.current`. ✅
- `hostUsers: false` Pod on `v1.37.0`: `Running`, `uid=0`, `uid_map` = `0 188940288 65536`;
  `kubernetes_feature_enabled{name="UserNamespacesSupport"} 1`. ✅

**Unverified, in risk order. Each has a named fallback:**

| # | Risk | Test | Fallback |
|---|---|---|---|
| 1 | **`unshare -U` needs `--security-opt seccomp=unconfined`.** In a default container it fails with `Operation not permitted` — Docker's profile blocks it. Lesson 01c must not hand the reader a flag it has not earned | Confirm whether `netlab:latest`'s documented run recipe (`--privileged`) already permits it, and whether `unshare -U` works unflagged there | **This is an asset, not a blocker.** The denial *is* Act X 02's finding arriving early. Open `01c` with the unflagged failure, name the wall as "something you will meet properly in Act X", then add the flag. Do **not** silently paste `seccomp=unconfined` |
| 2 | **`01c`'s position may break Act X 02's Predict-first.** If `01c` demonstrates that `unshare -U` is blocked by default, Act X 02's prediction (c) is partly spoiled | Re-read `02-the-kernel-says-no.md:7` and `:100–102` after `01c` exists | Reword `01c` to establish the *mechanism* while leaving *whether a default Pod blocks it* explicitly open — a genuine seed, not a spoiler. Act X 02's beat is the capability/filter *orthogonality*, which `01c` does not touch |
| 3 | **Drill D's `ConditionPathExists` may leave the node wedged.** Moving `/var/lib/kubelet/config.yaml` on a kind control plane stops the kubelet and therefore the API server | Do it on `netlab-worker`, never the control plane; confirm recovery is just restoring the file | Make it a worker-only drill, and if recovery is unreliable make it paper-shaped, as Act X's `diagnose.md` already establishes is acceptable |
| 4 | **`05b`'s `ln -s` bridge needs a writable `/var/run/netns` and `--pid=host`.** Verified in `netlab:latest --privileged --pid=host`; not yet verified from inside a kind node | Run it against a kind node's containerd container rather than a plain `docker run` | Teach it against a plain container (verified) and *state* that a Pod is the same mechanism with a different PID source — which Act IV lesson 06 already establishes |
| 5 | **The kubelet's `MemoryCurrent`/`cpu.stat` equality is timing-sensitive.** The two reads differ by whatever elapses between them | Show both with the delta acknowledged, as Act XI lesson 03 does for `cpu.stat` | State the microsecond gap as the point rather than an error — it is evidence they are the same live counter |

**One environmental note, recorded because it cost time in this session:** both kind clusters
(`netlab`, `kind`) vanished mid-session — `docker ps -a` empty, all images intact — without being
deleted by any command run here. Whatever the cause (a Docker Desktop restart is the likeliest), **the
kind-dependent measurements above were taken before that and are not re-runnable until the lab is
rebuilt.** Anyone continuing this plan should rebuild `netlab` and re-confirm the four ✅ items that
touch the cluster before quoting them in prose. Everything measured in `netlab:latest` alone is
reproducible now.

**Write order (cheapest verification first), which is not the publish order:**
`02b → 05b → 01c → the Act X 01 insertion`. `02b` is verified end-to-end already and closes the exam
gap; the insertion goes last because it depends on `01c` existing to link back to.

---

## 10. Obligations

Every lesson carries the fifteen in [`PLATFORM-DEPTH-PLAN.md`](PLATFORM-DEPTH-PLAN.md) §4 — run
`cd tools && python3 -m harness --list` for the live table. **Three teaching files × fifteen**, and
Phase 1's lesson stands: the obligations are where the time goes.

This phase does **not** owe a new act shape, an `ACTS` entry in `sync-content.mjs`, or a `JOURNEY-MAP`
status row — the acts exist and are already ✅. What it does owe is unusually heavy on *repairing claims
already made*, and that is the part that must not be skipped:

**Prose that becomes wrong, or was already wrong, and must change in the same commit:**

1. **[`act-4/01-namespaces.md:13`](networking-fundamentals/act-4-one-pretends-many/01-namespaces.md)** —
   "the network one is **the only one this course cares about**" is false once `01c` and `01b` exist.
   Reword to name what each of the three lessons takes.
2. **The "five namespaces" framing, in three places** — `05-who-does-this-for-you.md:78–81`,
   `README.md:24`, `test-yourself.md:59`. The OCI array genuinely lists five; the fix is to stop
   presenting five as the complete namespace canon, not to falsify the `jq` output.
3. **[`act-10/02-the-kernel-says-no.md:7`](networking-fundamentals/act-10-cluster-security/02-the-kernel-says-no.md)** —
   "Act IV's mechanism" becomes **true**. Update the citation to link `01c` directly. *This is the
   phantom citation from §1; it is the single most important edit in the phase.*
4. **[`Toolbelt.md:146`](Toolbelt.md)** — "`unshare` in Act X; `nsenter` is named in prose and never
   run" must be rewritten. Both claims stop being true.
5. **[`reference/tools/nsapi/unshare.md:9`](reference/tools/nsapi/unshare.md)** — "Taught in" moves from
   Act X 02 to Act IV `01c`, and `capabilities.json`'s `"course": []` for `unshare` (currently empty)
   gains entries.
6. **`act-6/02-static-pods.md:23`** — the 33-word introduction becomes a pointer to `02b` rather than
   the whole treatment, and `:27`'s output-less `systemctl cat` pipe either gains its output or defers
   to `02b`.
7. **`act-6/08-when-the-control-plane-breaks.md:137`** — its back-reference to lesson 02 should point at
   `02b`, which is where the journal now lives.

**New reference material:**

8. **`reference/tools/` pages for `systemctl` and `journalctl`** — §5.3's structural finding. Facets from
   the **closed** vocabularies; both are `procfs`-adjacent but neither is obviously one of the eight
   existing families, so the interface classification is a **deliberate decision, not a default** —
   record the reasoning. Then `tools/gen-tool-pages.py`, `tools/gen-command-tables.py`, roster rows, and
   `capabilities.json` entries. **Phase 1's specific trap applies:** a roster row with two backtick
   names has only its first name checked. It shipped once before it was caught.
9. **`reference/06-derive-it.md`** — its `nsenter` ladder now has a lesson behind it; check whether the
   ladder's framing ("derive a command you were never given") still holds or needs rewording.

**Standard per-lesson obligations that bite here specifically:**

10. **Nav footers in four files** — Act IV's reading order becomes 01 → 01b → **01c** → 02 … 05 → **05b**
    → 06, and Act VI's 02 → **02b** → 03. Missing one leaves a reader in a dead end; Act XI Wave 2 hit
    exactly this and it is easy to miss.
11. **`act-4/README.md`, `act-6/README.md`** — lesson lists and "what breaks here".
12. **`test-yourself.md` in both acts** — new questions, plus the item-2 repair.
13. **`diagnose.md` in both acts** — four drills (§7), `drills/act-4/*.sh` + `drills/act-6/*.sh`
    verifiers with cause hashes, and `tools/verify-drill.sh --list` coverage.
14. **`LESSON-INDEX.md`** — `index.freshness` fails otherwise.
15. **`tools/remeasure.py --write`** in the same commit. Note `OPTIONAL_WORDS` (currently `60_541`) grows
    by `01c` + `05b` ≈ 5,000 while `02b` goes on-path — so **both** the optional-track constant and its
    hardcoded regex anchors move, and the unaccounted-words warning (now **10,890**) shifts again.
16. **`exam-prep/`** — `the-exam-path.md`'s optional-track row (§8's split, with `02b` named as the
    on-path exception) and the two CKA rows that gain a mechanism link without changing their verdict.

And item 14 of the fifteen remains non-negotiable: **`learner-simulator` for Spirit and River,
`technical-accuracy-checker` for every command, per file.** Act XI's two review rounds found real
defects — a script missing the prints its own transcript quoted, a metric used before definition — and
this phase's whole premise is that unreviewed prose accumulates exactly that.

---

## 11. Sizing, and how it ships

| File | Words |
|---|---|
| `act-4/01c-who-am-i.md` | 2,800 |
| `act-4/05b-entering-what-you-did-not-name.md` | 2,200 |
| `act-6/02b-what-starts-the-kubelet.md` | 3,200 |
| `act-10/01` insertion | 500 |
| drills + `diagnose.md` prose (4) | 2,000 |
| reference pages (`systemctl`, `journalctl`) | 900 |
| support-page edits (READMEs, test-yourself, index, exam-prep, repairs) | 1,400 |
| **Total** | **≈ 13,000** |

Against Phase 2's 41,700 this is a third the size, and that is the point: it is a repair phase. Every
file sits below the course median of 2,988 except `02b` at 3,200, and all are far inside the 10,000
ceiling. Act IV grows from 24,452 to ~29,500 — still below Act XI — and Act VI from 42,741 to ~46,000.

**Ship as one wave.** Phase 2 split because 41,700 words is where verification quality dies; 13,000 with
no new installs does not have that problem, and the three lessons are coupled by the §10 repairs — `01c`
without the Act X 02 citation fix leaves the phantom citation half-fixed, which is worse than leaving it
alone. The one defensible seam, if the phase must slip, is **`02b` alone first**: it is fully verified
already, closes the only exam gap, and touches Act VI only.

---

## 12. Open questions this plan left — and how the build actually resolved each

Phase 2 recorded its Loki question before evidence settled it; these five were written the same way,
and the build settled all five. Recorded here as resolved rather than deleted, because the reasoning is
the part worth keeping.

1. **Does the user-namespace lesson belong in Act IV at all, or in Act X 01 as one long section?**
   **Resolved: Act IV, but not at `01c` — moved to `05c`, after `05b`.** Writing it at `01b`'s position
   surfaced exactly the counter-argument this question named: with no container in front of the reader,
   "container root is host root" is an assertion, not a measurement. Placing it after `05` and `05b`
   means the reader already has a running `runc` container, a PID, and the `ip netns`-is-blind result —
   so `unshare -U --map-root-user` lands as *"you have just been shown one handle fails; here is a second
   thing about identity you have also been assuming."` The Pod payoff still waits for Act X 01, and that
   gap is now named explicitly in `05c`'s own closing rather than left implicit.
2. **What interface family do `systemctl` and `journalctl` belong to?** **Resolved: no ninth family.**
   Measured rather than argued: `/proc/net/unix` on the lab node shows live connections to
   `/run/systemd/private` while `systemctl` runs, which is the same shape as any other daemon client — so
   `systemctl` is `httpapi`, transport footnoted as a unix socket rather than HTTP/gRPC. `journalctl`
   measured the opposite way: `journalctl --file <a copy of the journal>` returns identical records with
   systemd never consulted, and a running `journalctl -f` holds no socket at all in `/proc/<pid>/fd/`. It
   reads a file, which is `local`'s definition exactly. Both pages shipped in `reference/tools/`, the
   roster's interface table carries a footnote explaining the split, and `reference/capabilities.json`
   gained both entries.
3. **Is `05b` a lesson or a section of `05`?** **Resolved: separate**, matching Phase 2's answer for the
   same question about a different `05b`. Final length 2,170 words against lesson 05's roughly 1,450 —
   folding would give ~3,600, unremarkable but with no gain, and the `ip netns`-is-blind finding is a
   complete argument on its own that a fold would bury under lesson 05's runtime-chain argument.
4. **Should `01b-cgroups.md` gain the systemd-slice bridge, or does `02b` own it?** **Resolved: `02b`
   owns it, as guessed.** `01b` was left untouched; `02b` carries the whole bridge, reading
   `/sys/fs/cgroup/kubelet.slice/kubelet.service/{cpu.stat,memory.current}` and Act IV's own file paths in
   one command so the connection is measured rather than asserted, with a parenthetical noting the path
   shape changed (a container's own cgroup root in Act IV vs. a nested slice path read from the node in
   Act VI) so the reader is not left to notice the discrepancy alone.
5. **Does the journal's volatility deserve the drill it was denied in §7?** **Resolved: still no**, on the
   original reasoning — reboot-shaped drills are destructive to a shared lab. It surfaces as prose
   instead, in `02b`'s own journal section (`/run/log/journal` on `tmpfs`, confirmed with `findmnt` rather
   than asserted) and in drill 13's reveal, which is the volatility's diagnostic consequence — an
   `inactive` unit with `ConditionResult=no` and an empty journal — without needing to actually reboot
   anything.

**One thing this plan did not anticipate and the build found anyway:** two review passes on `02b` (before
and after a revision) each surfaced the same defect class Phase 1 and Act XI kept finding — an argument
built by citing lessons the reader has not read yet (lesson 08, `diagnose.md`, lesson 09) instead of from
what lesson 02 itself left unanswered. The fix was to rebuild the opening from lesson 02's own two loose
threads — "how do you stop the kubelet, given it has no manifest" and "who restarts the one thing nothing
above it can restart" — which is the shape §5.3 argued for in the abstract; the first draft did not follow
its own argument.
