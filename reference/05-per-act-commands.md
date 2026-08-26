# Lab and shell commands, taken apart

Every command Acts I–IV run that is **not** a networking instrument — the shell built-ins, the compiler
and the file utilities the lessons lean on to set a scene. The right column breaks down each syntax
element. This is the page for *"I know what I ran, I've forgotten why the flag was there"*.

**Placeholders:** `<pid>` a process id · `<inode>` a socket inode number · `<dev>` an interface name.
**"opt:"** marks a useful variant the lesson didn't run.

> ## Where the networking commands went
>
> They are on the tool pages, one page per instrument, next to that tool's full capability surface —
> [`ip`](tools/netlink/ip.md) carries the thirty-one commands the course runs through it,
> [`tcpdump`](tools/packet/tcpdump.md) its five, and so on. That is a better home than this page was:
> a command means most when it sits beside the other things the same tool can do, and beside the
> [interface](tools/netlink/README.md) that explains why its syntax is shaped that way.
>
> What is left here is the residue that belongs to no instrument. `ls`, `grep`, `exec` and `cc` are
> not networking tools and never earned a row in [the index](tools/README.md), but the lessons run them
> and the breakdowns were worth keeping, so they are kept rather than quietly dropped.
>
> `tools/gen-command-tables.py --diff` still reports commands a lesson runs that nothing documents.

---

## Lesson 1 — The file-descriptor table

| Command | Syntax breakdown |
|---|---|
| `exec 3>/tmp/scratch` | `exec` = apply the redirection to **the shell itself**, with no child process; `3>` = open fd **3** for writing; the path = what it points at. Adds a row to the fd table |
| `exec 3>&-` | `3>&-` = close fd **3** (`&-` means "close"). Removes the row |
| `ls -la /proc/self/fd` | `-l` long format; `-a` include `.`/`..`; `/proc/self/fd` = this process's fd directory, one symlink per open descriptor |
| `ls -l /proc/<pid>/fd` | the same for another process — the `self` in the path above is just a magic symlink to your own pid |
| `cc -Wall -o /tmp/fd-demo /code/fd-demo.c` | `cc` = the C compiler; `-Wall` = all warnings; `-o <path>` = output binary; trailing `.c` = source |
| `/tmp/fd-demo` | run the binary by path, in the foreground |

## Lesson 2 — What a socket really is

| Command | Syntax breakdown |
|---|---|
| `/tmp/fd-demo &` | `&` = run in the background; the shell prints a job number `[1]` and returns the prompt |
| `kill %1` | `kill` = send a signal (default `TERM`); `%1` = job number 1. opt: `kill -9 %1` to force |
| `INO=$(readlink /proc/$(pgrep -n fd-demo)/fd/4 \| sed 's/[^0-9]//g')` | `readlink` prints a symlink's target — here `socket:[3209833]`; `sed 's/[^0-9]//g'` strips everything but the digits, leaving the bare inode. `$(…)` = command substitution, nested twice |
| `grep "$INO" /proc/net/tcp` | search the TCP table for that inode. **No match means the socket has no address yet** — it exists, but `bind()` hasn't happened |

## Lesson 3 — Building minihttp, the listening server

| Command | Syntax breakdown |
|---|---|
| `cc -Wall -o /tmp/minihttp /code/minihttp.c` | compiles the server (already built at `/code/minihttp` in netlab) |
| `/tmp/minihttp 8080` | `8080` = the port, passed as an argument to the program, not a flag |
| `grep State: /proc/$(pgrep -f minihttp \| head -1)/status` | `-f` matches the full command line; `head -1` takes the first pid; `State:` in `/status` is `S` sleeping / `R` running — this is how you see `accept()` blocking |

## Lesson 5 — Ports and /proc/net/tcp

| Command | Syntax breakdown |
|---|---|
| `grep " 0A " /proc/net/tcp` | `" 0A "` = the state column, with spaces anchoring it: `0A`=LISTEN, `01`=ESTABLISHED, `06`=TIME_WAIT |
| `ls -la /proc/*/fd 2>/dev/null \| grep <inode>` | `*` globs every pid; `2>/dev/null` discards the permission errors from processes you don't own; `grep <inode>` finds the owner. This is the join `lsof` does for you |
| `python3 -m http.server 8081 --bind 127.0.0.1 &` | `-m http.server` = run the stdlib module as a program; `8081` = port; `--bind 127.0.0.1` = **listen on loopback only**, versus `0.0.0.0` for every interface. This distinction is the whole lesson |

## Lesson 6 — Everything is a file

| Command | Syntax breakdown |
|---|---|
| `df -h /proc` | `df` (*disk free*); `-h` human-readable; trailing path = report the filesystem backing it. `/proc` shows size 0 — nothing on disk backs it |
| `cd /tmp` | change directory — the lesson works in `/tmp` because the inode experiments below create and delete real files, and a scratch filesystem is the right place for that |
| `ls -li /tmp/a.txt` | `-i` = show the **inode number** first — the kernel's real identity for a file, independent of its name |
| `ln <target> <newname>` | **hard link**: a second directory entry pointing at the *same inode*. Same inode number, link count `+1`. No `-s` |
| `ln -s <target> <name>` | **symbolic link**: its own inode whose *data is the target path string*, so its size equals the string's length. The target need not exist |
| `exec 7< file; rm file; cat /proc/self/fd/7` | open on fd 7, delete the name, still read through `/proc`. The inode survives until link count **and** open fds both hit zero — which is how you recover a deleted-but-running binary |

## Lesson 6b — The container's filesystem (optional)

| Command | Syntax breakdown |
|---|---|
| `df -h /` | reports the **host** disk's size — a container sees host free space, with no per-container limit by default |

---

## Lesson 1 — The wire and the two names

| Command | Syntax breakdown |
|---|---|
| `watch -n1 cat /proc/net/arp` | `watch` re-runs a command; `-n1` every second. The neighbour cache filling in, live |

## Lesson 2 — IP and routing

| Command | Syntax breakdown |
|---|---|
| `head -20 /proc/net/fib_trie` | the kernel's actual routing structure — a trie, showing how longest-prefix match is implemented rather than just its result |

## Lesson 3 — ICMP, UDP, and TTL

| Command | Syntax breakdown |
|---|---|
| `echo hello \| nc -u -w1 8.8.8.8 9999` | `-w1` = give up after 1 second, so `nc` exits. The packet leaves and nothing comes back — and UDP cannot tell you that |

## Lesson 4 — DNS

| Command | Syntax breakdown |
|---|---|
| `grep '^hosts:' /etc/nsswitch.conf` | the **order** of resolution sources — `files dns` means `/etc/hosts` is consulted first. On glibc this file decides whether DNS is asked at all. **Not in this lab:** Alpine uses musl, which implements no NSS and ignores the file entirely — see [`procfs`](tools/procfs/README.md) |
| `echo "127.0.0.1 my-fake-service" >> /etc/hosts` | `>>` appends. Proves `/etc/hosts` beats DNS, because NSS asked `files` first |

---

## Lesson 3 — TCP and reliability

| Command | Syntax breakdown |
|---|---|
| `grep ':1F90' /proc/net/tcp` | `1F90` is 8080 in hex; the `tx_queue:rx_queue` columns are bytes sitting in each buffer — the same numbers `ss -m` prettifies |
| `awk '$3 ~ /:1F90$/ {print "cwnd=" $16, "ssthresh=" $17}' /proc/net/tcp` | `$3` = the remote address column, matched by regex; fields 16 and 17 are the congestion window and slow-start threshold. Reading congestion control out of the raw file |

## Lesson 5 — TLS

| Command | Syntax breakdown |
|---|---|
| `echo \| openssl s_client -connect … 2>/dev/null \| openssl x509 -noout -issuer -subject -dates` | `echo \|` feeds EOF so `s_client` exits instead of waiting; the second `openssl` parses the certificate it printed. `-noout` = don't re-print the certificate itself, just the fields asked for |

---

## Lesson 1 — Namespaces

| Command | Syntax breakdown |
|---|---|
| `ls -la /proc/self/ns/` | one magic symlink per namespace type; each target is `type:[inode]`. **The inode is the identity** |

## Lesson 1b — cgroups

| Command | Syntax breakdown |
|---|---|
| `free -h` | reports the **whole machine's** RAM. A cgroup limits you without telling `free` about it, which is why JVMs and Node used to get this catastrophically wrong |
| `python3 -c 'x = bytearray(200 * 1024 * 1024); print("got it")'` | allocate 200 MB against a 64 MB limit. The shell prints `Killed` and exit 137 — but no *reason*, and nothing about memory. The explanation is in the file below |

## Lesson 3 — iptables and NAT

| Command | Syntax breakdown |
|---|---|
| `ls /sys/class/net/docker0/brif/` | the container's host-side veth end, plugged into that bridge |
