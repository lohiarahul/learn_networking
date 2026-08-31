# What starts the kubelet

The last lesson found the bottom of the boot order and stopped one step short of it. Every arrow pointed backwards until one component escaped, and that component escaped because it was "a plain background service on the node, started at boot by the init system." Then the lesson moved on, because it had a control plane to explain.

Two questions were left on the floor there, and they are both about the same missing thing.

The lesson taught you to **stop a component by moving its file** out of `/etc/kubernetes/manifests/`. That works for four of the five things running on this node. It does not work for the fifth, because the kubelet has no manifest — so how do you stop the kubelet, and what happens afterwards?

And the harder one. Everything else on this node is watched: the kubelet watches that directory, and the components it starts come back because the kubelet is still there. The kubelet is the bottom of the stack, so **nothing above it can restart it.** If it dies, what brings it back — and is there anything at all, or does the node simply stay broken?

Both answers are in one file, on the node, that nothing has opened yet.

> **Predict first —** the kubelet's config file is missing from the node. You then run `systemctl restart kubelet`. Predict which of these you get, and commit to it before reading on:
>
> - (a) the unit is `failed`, and the log shows the kubelet crashing on the missing file
> - (b) the unit is `activating`, restarting once a second forever
> - (c) the unit is `inactive`, and there is no crash at all
>
> And a second prediction, because it is the one that costs people hours: does `systemctl restart` **exit non-zero** in the case you picked?

## The service is a file, and you can read it

`systemctl` is how you talk to the init system — the program running as PID 1 on this node, which you can confirm with `docker exec netlab-control-plane ps -p 1 -o comm=` and get back `systemd`. Of its subcommands, `systemctl cat` is the one that prints a service's **definition** rather than its state, and the definition is a file:

```bash
docker exec netlab-control-plane systemctl cat kubelet
```

```
# /etc/systemd/system/kubelet.service
[Unit]
Description=kubelet: The Kubernetes Node Agent
# NOTE: kind deviates from upstream here to avoid crashlooping
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

[Install]
WantedBy=multi-user.target
```

That is a **unit** — the word lesson 02's boot-order figure ended on and never defined. A unit is an INI file describing one thing systemd manages, and `.service` is the kind that means "a process to keep running." The `[Service]` section is the interesting half: `ExecStart=` is the command line, and everything under it is a *policy* about that command line rather than part of it.

`[Install]` is the third section and it answers "who starts this at boot." `WantedBy=` does not run anything itself; enabling the unit makes a symlink in the named target's directory, and you can go and look at it:

```bash
docker exec netlab-control-plane ls -l /etc/systemd/system/multi-user.target.wants/kubelet.service
```

```
... /etc/systemd/system/multi-user.target.wants/kubelet.service -> /etc/systemd/system/kubelet.service
```

A **target** is a named group of units systemd brings up together, and `multi-user.target` is the ordinary "the machine is up and serving" one. So "starts at boot" is a symlink in a directory — which is the third time this act has found authority living in a directory listing, after `/etc/kubernetes/manifests/` and `/registry/`.

Nothing in that file is invented for teaching. This is the file on your node, and the rest of this lesson takes its lines in the order that each answers a question this act has already raised.

## `ConditionPathExists` — the third state nobody predicts

Start with the line kind's own authors annotated. Move the config file out of the way on the worker — not the control plane, which would take the API server with it — and restart:

```bash
docker exec netlab-worker mv /var/lib/kubelet/config.yaml /root/config.yaml.bak
docker exec netlab-worker sh -c 'systemctl restart kubelet; echo "RESTART EXIT=$?"'
sleep 3
docker exec netlab-worker sh -c 'systemctl is-active kubelet; echo "IS-ACTIVE EXIT=$?"'
docker exec netlab-worker systemctl show kubelet -p ActiveState -p ConditionResult -p Result -p NRestarts
```

```
RESTART EXIT=0
inactive
IS-ACTIVE EXIT=3
Result=success
NRestarts=0
ActiveState=inactive
ConditionResult=no
```

Answer (c) — and to the second prediction, **`systemctl restart` exited 0.** It reported success and left the kubelet not running. That is the one that costs people hours: in a script, in a CI job, in an upgrade playbook, this step passes. Only `is-active` disagrees, with exit `3`, and only because you asked it a different question.

Then read `Result=success` twice, because systemd means it. It did not fail; it **declined**. And `NRestarts=0`, so `Restart=always` never fired — a restart policy governs a process that ran and stopped, and here no process ran.

Where did it say so? The kubelet's own output goes to systemd's **journal** — a single system-wide log store that captures every service's stdout and stderr — and `journalctl` reads it. Three flags do almost all the work: `-u <unit>` selects one unit's share of the store, `--since` bounds the time window, and `--no-pager` stops it opening an interactive pager, which matters through `docker exec` where there is no terminal for one.

```bash
docker exec netlab-worker journalctl -u kubelet --since '-1min' --no-pager | tail -2
```

```
kubelet.service: Consumed 1.213s CPU time, 36M memory peak.
kubelet.service - kubelet: The Kubernetes Node Agent skipped, unmet condition check ConditionPathExists=/var/lib/kubelet/config.yaml
```

**"Skipped, unmet condition check."** A condition is evaluated *before* the process starts, and an unmet condition is a no-op rather than an error. That is exactly what kind's comment means by "to avoid crashlooping": without this line the kubelet would start, fail to parse a file that is not there, exit, and be restarted a second later, forever — filling the journal and telling you nothing you could not have learned from one line.

So the diagnostic value is real and specific. `failed` means the kubelet ran and died, and the journal holds its reasons. **`inactive` with `ConditionResult=no` means the kubelet never ran, and the journal holds nothing** — because there is nothing to hold. If you go looking for a crash you will find silence and conclude the journal is broken.

Put it back, and watch the same line permit what it just refused:

```bash
docker exec netlab-worker mv /root/config.yaml.bak /var/lib/kubelet/config.yaml
docker exec netlab-worker systemctl start kubelet
sleep 5
docker exec netlab-worker systemctl is-active kubelet
docker exec netlab-worker systemctl show kubelet -p ConditionResult
```

```
active
ConditionResult=yes
```

Note that a `start` was enough. Nothing was retrying in the background waiting for the file to appear — a condition is checked when the unit is asked to start, and only then.

## `Restart=always` — the answer to "who brings it back"

That was the first of the two questions from lesson 02. Here is the second, and it is four lines:

```
Restart=always
StartLimitInterval=0
RestartSec=1s
KillMode=process
```

`Restart=always` means systemd starts it again whenever it exits, whatever the exit code. **That is the whole answer: nothing above the kubelet restarts it, and nothing needs to, because the thing below it does.** `RestartSec=1s` is the pause between attempts — kind lowers it from the upstream default so a broken node recovers fast. `StartLimitInterval=0` disables the rate limiter that would otherwise give up after five restarts in ten seconds and leave the unit `failed`.

Which is worth pausing on, because it means a kubelet that keeps failing for a *persistent* reason — a config it cannot parse, a cgroup tree it cannot reach — will exit, return one second later, exit again, and do that indefinitely, with nothing counting and nothing giving up. A restart loop is not a bug in the kubelet; it is these three lines meeting a problem that does not go away.

Now the other question lesson 02 left. How do you stop the kubelet, given it has no manifest to move? You ask systemd:

```bash
docker exec netlab-worker systemctl stop kubelet
docker exec netlab-worker systemctl is-active kubelet
sleep 5
docker exec netlab-worker systemctl is-active kubelet
```

```
inactive
inactive
```

Still stopped, five seconds later, with `Restart=always` in the file. **`Restart=` governs a process that exited on its own; it does not govern one you told systemd to stop.** An administrative stop is systemd's own decision, and systemd does not fight itself. One line, two opposite behaviours, and the gap between them is where every restart-loop mystery on a Linux host lives.

And `KillMode=process` decides what else that stop takes down with it. By default systemd kills every process in a unit's cgroup; `process` kills only the main one. Count what is running before and after:

```bash
docker exec netlab-worker sh -c 'crictl ps -q | wc -l'
docker exec netlab-worker systemctl stop kubelet
sleep 5
docker exec netlab-worker sh -c 'crictl ps -q | wc -l'
docker exec netlab-worker systemctl start kubelet
```

```
2
2
```

Same count, kubelet stopped the whole time. Nothing is *managing* those containers with the kubelet down, but `KillMode=process` is why nothing killed them either — and in a moment you will find out exactly what else shares that cgroup. Put the kubelet back before you go on.

## The drop-in — and a second program you have been reading without meeting

The output above was edited to fit. Run the real command and you get more files than you asked for:

```bash
docker exec netlab-control-plane systemctl show kubelet -p FragmentPath -p DropInPaths
```

```
FragmentPath=/etc/systemd/system/kubelet.service
DropInPaths=/etc/systemd/system/kubelet.service.d/10-kubeadm.conf /etc/systemd/system/kubelet.service.d/11-kind.conf
```

Three files, not one. A **drop-in** is a fragment in `<unit>.service.d/` that systemd merges over the base unit in filename order, which is why they are numbered. Nobody edited `kubelet.service` to configure this node — two other programs dropped files next to it.

One of those filenames names the program that has been invisible so far. `kind` built these node containers, and inside each one it ran **`kubeadm`** — the standard cluster bootstrapper, the tool that writes `/etc/kubernetes/manifests/`, issues the certificates, and configures the kubelet. You have been reading its output since lesson 01 without meeting it; [lesson 09](09-two-machines-from-nothing.md) runs it by hand on bare machines. Here you only need the one thing it did to this unit: the drop-in named after it.

`systemctl cat` prints the whole merged stack in the order it is applied, with each file's path as a comment, and that is the only honest way to read a unit.

Here is kubeadm's, and it contains the pattern that trips everyone:

```bash
docker exec netlab-control-plane cat /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
```

```
[Service]
Environment="KUBELET_KUBECONFIG_ARGS=--bootstrap-kubeconfig=/etc/kubernetes/bootstrap-kubelet.conf --kubeconfig=/etc/kubernetes/kubelet.conf"
Environment="KUBELET_CONFIG_ARGS=--config=/var/lib/kubelet/config.yaml"
EnvironmentFile=-/var/lib/kubelet/kubeadm-flags.env
EnvironmentFile=-/etc/default/kubelet
ExecStart=
ExecStart=/usr/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_CONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS
```

Two things in there are not obvious from reading them.

**`ExecStart=` on its own line is a deletion.** Most unit settings are lists that drop-ins append to, so a second `ExecStart=` would mean "run both." Assigning the empty value clears the list, and the next line rebuilds it. So the base unit's `ExecStart=/usr/bin/kubelet` is *gone*, replaced by a version carrying four variables. Miss the empty line and you will read this as two commands.

**`EnvironmentFile=-` means the file is optional.** The `-` prefix says "read it if it exists, and do not fail if it does not." That is how `$KUBELET_KUBEADM_ARGS` works at all: `kubeadm join` writes `/var/lib/kubelet/kubeadm-flags.env` at runtime, so the unit has to tolerate its absence before that has happened.

Read together, this answers the question you were just given a name for: kubeadm does not template the unit it did not write. It adds a numbered fragment, clears the one line it needs to own, and injects the rest through environment files it can regenerate whenever the node's identity changes.

The other drop-in is `kind`'s own, and it is shorter — `ExecStartPre=` lines that create a cgroup directory before the kubelet starts, worked around a WSL2 quirk kind's own comments explain:

```bash
docker exec netlab-control-plane cat /etc/systemd/system/kubelet.service.d/11-kind.conf
```

```
# kind specific additions go in this file
[Service]
# On cgroup v1, the /kubelet cgroup is created in the entrypoint script before running systemd.
# On cgroup v2, the /kubelet cgroup is created here. (See the comments in the entrypoint script for the reason.)
ExecStartPre=/bin/sh -euc "if [ -f /sys/fs/cgroup/cgroup.controllers ]; then /kind/bin/create-kubelet-cgroup-v2.sh; fi"
# on WSL2 (and potentially other distros without systemd) /sys/fs/cgroup/systemd is created after the entrypoint, during /sbin/init.
# This eventually leads to kubelet failing to start, see: https://github.com/kubernetes-sigs/kind/issues/2323
ExecStartPre=/bin/sh -euc "if [ ! -f /sys/fs/cgroup/cgroup.controllers ] && [ ! -d /sys/fs/cgroup/systemd/kubelet ]; then mkdir -p /sys/fs/cgroup/systemd/kubelet; fi"
```

`ExecStartPre=` is a setup command that has to succeed before `ExecStart=` runs at all — which is why the cgroup this whole lesson is about to read exists before the kubelet does.

## `daemon-reload` — why a restart can do nothing at all

You have just read a merged stack of three files, and nowhere did you ask *when* systemd last read them. Unit files are on disk, and systemd parses them into memory once, when it last had a reason to — not on every command that touches the unit. Add a drop-in and watch what a plain restart does with it:

```bash
docker exec netlab-worker sh -c 'printf "[Service]\nEnvironment=\"KUBELET_EXTRA_ARGS=--v=4\"\n" > /etc/systemd/system/kubelet.service.d/99-verbose.conf'
docker exec netlab-worker systemctl restart kubelet
docker exec netlab-worker systemctl show kubelet -p DropInPaths
```

```
Warning: The unit file, source configuration file or drop-ins of kubelet.service changed on disk.
Run 'systemctl daemon-reload' to reload units.
DropInPaths=/etc/systemd/system/kubelet.service.d/10-kubeadm.conf /etc/systemd/system/kubelet.service.d/11-kind.conf
```

The restart **succeeded**, and it restarted the old configuration. Your file is not in `DropInPaths` and its variable is not in the environment. Systemd does warn — modern versions compare timestamps and tell you — but the warning goes to stderr, the exit code is 0, and the service is running, so every signal except the one sentence says the change took effect.

`daemon-reload` re-reads the files. Then the restart means what you thought it meant:

```bash
docker exec netlab-worker systemctl daemon-reload
docker exec netlab-worker systemctl restart kubelet
docker exec netlab-worker systemctl show kubelet -p DropInPaths
```

```
DropInPaths=/etc/systemd/system/kubelet.service.d/10-kubeadm.conf /etc/systemd/system/kubelet.service.d/11-kind.conf /etc/systemd/system/kubelet.service.d/99-verbose.conf
```

Three drop-ins, and no warning this time.

Clean up before you go on, because a `--v=4` kubelet will fill the journal:

```bash
docker exec netlab-worker rm /etc/systemd/system/kubelet.service.d/99-verbose.conf
docker exec netlab-worker systemctl daemon-reload && docker exec netlab-worker systemctl restart kubelet
docker exec netlab-worker systemctl show kubelet -p DropInPaths     # back to two
```

## `Slice=` — and systemd turns out to be something you already know

Two lines are left, and they are the ones that tie this file back to Act IV:

```
CPUAccounting=true
Slice=kubelet.slice
```

A **slice** is a unit type that holds no process of its own; it exists to *be a cgroup*, and other units are placed inside it. So `Slice=kubelet.slice` says "put this process in the cgroup called `kubelet.slice`," and `CPUAccounting=true` / `MemoryAccounting=true` ask systemd to enable that cgroup's counters.

Which should sound familiar, because you have read those counters by hand. Ask systemd how much the kubelet has used, then read the files [Act IV's cgroups lesson](../act-4-one-pretends-many/01b-cgroups.md) had you `cat` — in one command, so nothing can drift between the two:

```bash
docker exec netlab-control-plane sh -c '
  systemctl show kubelet -p CPUUsageNSec -p MemoryCurrent
  head -1 /sys/fs/cgroup/kubelet.slice/kubelet.service/cpu.stat
  cat /sys/fs/cgroup/kubelet.slice/kubelet.service/memory.current'
```

```
MemoryCurrent=47276032
CPUUsageNSec=1986594000
usage_usec 1986594
47276032
```

`1986594000` nanoseconds is `1986594` microseconds. `MemoryCurrent` and `memory.current` are the same integer, digit for digit. **`systemctl show` is a formatted read of a cgroup file**, and `CPUAccounting=true` is what turned the counter on. Systemd is not a monitoring system that collected these numbers; it is a process manager that put the kubelet in a cgroup, and a cgroup keeps this record about itself whether anyone reads it or not.

(One thing did change since Act IV, and it is only the path. There you read `/sys/fs/cgroup/memory.current` from *inside* a container, where the cgroup you are in is mounted at the root. Here you are reading the node's tree from outside, so the same file has a path down to the leaf you want.)

Now look at what else is inside that slice, because it decides something Act VI otherwise has to assert:

```bash
docker exec netlab-control-plane sh -c '
  ls -d /sys/fs/cgroup/kubelet.slice/*/
  ls -d /sys/fs/cgroup/kubelet.slice/kubelet-kubepods.slice/*/
  grep -i cgroup /var/lib/kubelet/config.yaml'
```

```
/sys/fs/cgroup/kubelet.slice/kubelet-kubepods.slice/
/sys/fs/cgroup/kubelet.slice/kubelet.service/
/sys/fs/cgroup/kubelet.slice/kubelet-kubepods.slice/kubelet-kubepods-besteffort.slice/
/sys/fs/cgroup/kubelet.slice/kubelet-kubepods.slice/kubelet-kubepods-burstable.slice/
cgroupDriver: systemd
cgroupRoot: /kubelet
```

Every Pod on this node has its cgroup **inside a systemd slice**, as a sibling of the kubelet's own — and those two leaf names are worth reading character by character. In systemd, a `-` inside a slice name is a **path separator**, so `kubelet-kubepods-burstable.slice` is not an arbitrary label; it *is* the path it sits at. The kubelet did not pick a naming style it liked. It is speaking systemd's own convention, because systemd is what will be asked to create these.

So `cgroupDriver: systemd` in that config file is not a preference between two equally good options. On a machine where systemd owns `/sys/fs/cgroup`, the alternative is two programs writing one tree by different rules — and the setting is simply the kubelet agreeing to ask, rather than write directly. (`cgroupRoot: /kubelet` is the other half: it says *where* in that tree to ask for.)

## The journal — a store, not a file

You read the journal once already, to see the condition refuse. One more flag finishes it: `-n <count>` takes the last *n* lines, which is how you look at a unit without a window in mind.

```bash
docker exec netlab-control-plane journalctl -u kubelet -n 3 --no-pager
```

That is the whole reading interface, and it is worth knowing you now have it: `journalctl -u kubelet -n 50 --no-pager` is the command [`kubectl-speed.md`](../../exam-prep/kubectl-speed.md) drills as reflex for the moment `kubectl` stops answering, and until now no lesson had shown you `-n`.

But the property that will cost you evidence one day is where the journal lives. Do not take the location on trust — Act I gave you the tool that reads a mount:

```bash
docker exec netlab-control-plane sh -c '
  ls -d /var/log/journal 2>&1
  ls -d /run/log/journal
  findmnt /run
  journalctl --disk-usage'
```

```
ls: cannot access '/var/log/journal': No such file or directory
/run/log/journal
TARGET SOURCE FSTYPE OPTIONS
/run   tmpfs  tmpfs  rw,nosuid,nodev,noexec,relatime,mode=755
Archived and active journals take up 8M in the file system.
```

`/var/log/journal` is the persistent location and it does not exist. The journal is under `/run`, and `findmnt` says `/run` is **`tmpfs`** — a filesystem that lives in RAM. **This node's log store is in memory and dies with the node**, which is the default on any host where nobody created `/var/log/journal`, and true of every `kind` node you will ever debug. So this is not a broken command:

```bash
docker exec netlab-control-plane journalctl -u kubelet --since '2020-01-01' --until '2020-01-02' --no-pager
```

```
-- No entries --
```

Ask for a window the store does not cover and you get `-- No entries --`, which looks identical to "this unit was quiet." After a node reboot, the reason your kubelet's crash left no trace may be that the evidence was never on a disk. And it is the shape this course keeps returning to: **an empty result is a claim about the thing you asked, not about the world.** `ip netns list` on a node full of containers, and now a journal window that predates the store.

And the journal is a binary store rather than a text file, which is why you read it with a query tool instead of `grep`. `-u` is a field match against structured records, not a search — that is the reason `journalctl -u kubelet` can separate one unit's lines from a thousand others interleaved by timestamp, and `grep kubelet /var/log/syslog` cannot.

## One command that shows most of this at once

```bash
docker exec netlab-control-plane systemctl status kubelet --no-pager
```

```
● kubelet.service - kubelet: The Kubernetes Node Agent
     Loaded: loaded (/etc/systemd/system/kubelet.service; enabled; preset: enabled)
    Drop-In: /etc/systemd/system/kubelet.service.d
             └─10-kubeadm.conf, 11-kind.conf
     Active: active (running) since Mon 2026-08-31 00:54:59 UTC; 5min ago
   Main PID: 755 (kubelet)
      Tasks: 18 (limit: 9563)
     Memory: 49.5M (peak: 50.6M)
        CPU: 9.667s
     CGroup: /kubelet.slice/kubelet.service
```

Most of that you can now trace to its source: the unit path and its drop-in stack, `enabled` meaning the `[Install]` symlink you looked at is in place, and — from the two accounting switches — a cgroup path with its counters formatted for humans. `Memory:` and `CPU:` are the same two files you read raw a moment ago.

> **Check yourself —** A colleague edits `/etc/systemd/system/kubelet.service.d/20-local.conf` to add a flag, runs `systemctl restart kubelet`, sees the unit `active (running)`, and reports the flag has no effect. What are the three independent explanations, and which single command tells you which family you are in?

<details>
<summary>Answer</summary>

One: systemd never read the file — no `daemon-reload`, so the running process was started from the cached definition. Two: it read it, and a drop-in later in the merge order overrode it. Three: it read it and honoured it, but the flag went into a variable the final `ExecStart` does not reference — which is easy here, because kubeadm's drop-in cleared that line and rebuilt it with exactly four variables in it.

`systemctl cat kubelet` distinguishes them, because it prints the merged stack from disk. If `20-local.conf` is absent from that output, systemd has not reloaded. If it is present, the file is being read and the problem is what it says: check whether the `ExecStart` line actually expands the variable it was written into, remembering that kubeadm's drop-in cleared and rebuilt that line.

`systemctl show kubelet -p ExecStart -p Environment` is the follow-up: it prints the definition **currently in memory**, so comparing it against `systemctl cat` tells you whether the two agree.

</details>

<!-- figure -->

```
   WHAT "systemctl restart kubelet" ACTUALLY TOUCHES

   /etc/systemd/system/kubelet.service          <- the unit. ExecStart + policy
        + kubelet.service.d/10-kubeadm.conf     <- drop-in: ExecStart= CLEARS, then resets
        + kubelet.service.d/11-kind.conf        <- drop-in: kind's own, adds ExecStartPre
                                                    (setup commands run before ExecStart)
                |
                |  parsed at daemon-reload, then CACHED IN MEMORY
                |  (edit a file without reload -> restart succeeds, changes nothing)
                v
   ConditionPathExists  --unmet-->  SKIPPED. inactive, Result=success, NO journal entry
                |                   (Restart= never applies: nothing ran)
              met
                v
   process starts in  Slice=kubelet.slice
                |            |
                |            +-- /sys/fs/cgroup/kubelet.slice/kubelet.service/  <- cpu.stat,
                |            |     memory.current   == systemctl show -p CPUUsageNSec
                |            +-- kubelet-kubepods.slice/  <- EVERY POD ON THE NODE
                |                  (this is what cgroupDriver: systemd means)
                v
   exits on its own  --> Restart=always, RestartSec=1s  --> comes back, forever
   told to stop      --> stays stopped.  SAME LINE, OPPOSITE OUTCOME.
                |
                v
   stdout/stderr --> the JOURNAL, at /run/log/journal on this node  <- tmpfs.
                     dies with the node. "-- No entries --" is a fact
                     about the store, not about the kubelet.
```

> **You understand this when you can** read a unit file and say what `ExecStart`, `Restart` and `Slice` each decide; explain why a crashed kubelet returns and a stopped one does not, from one line; say what an `inactive` unit with `ConditionResult=no` means and why nothing was logged; explain why an edited drop-in can restart cleanly, exit 0, and change nothing; and name the file `systemctl show -p CPUUsageNSec` is reading.

**Which raises:** you have now found two of these stacked. Systemd watches the kubelet and restarts it when it exits; the kubelet watches a directory and restarts what it finds there. Both are the same shape — something notices a gap and closes it, on a loop, without being told twice.

But almost nothing in a real cluster is a systemd unit or a file in `/etc/kubernetes/manifests/`. A Deployment is neither, and [Act V](../act-5-kubernetes/03-services.md) already showed you its Pods coming and going as you changed a replica count — with no unit anywhere in sight. So where is *its* `Restart=always`, and what is watching the store you read in lesson 01 on its behalf?

---

← Prev: **[Static pods — where the control plane lives](02-static-pods.md)** · ↑ **[Act VI overview](README.md)** · Next: **[The reconciliation loop](03-the-reconciliation-loop.md)** →
