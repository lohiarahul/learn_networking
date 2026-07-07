# Act I — Command reference

Every command you ran in Act I, grouped by lesson. The right column breaks down each syntax element. Placeholders: `<pid>` = a process id, `<inode>` = a socket inode number. "opt:" marks a useful optional variant.

## Lesson 1 — The file-descriptor table

| Command | Syntax breakdown |
|---|---|
| `exec 3>/tmp/scratch` | `exec` (*execute*) = apply the redirection to the shell itself (no child); `3>` = open fd **3** for writing; `/tmp/scratch` = file it points at. → adds a row to the fd table |
| `exec 3>&-` | `3>&-` = close fd **3** (`&-` means "close"). → removes the row |
| `ls -la /proc/self/fd` | `ls` (*list*); `-l` long format; `-a` include `.`/`..`; `/proc/self/fd` = this process's fd directory |
| `cat /proc/self/fdinfo/1` | `cat` (*concatenate*) = print file contents; `fdinfo/1` = kernel metadata for fd **1**: `pos:` byte offset, `flags:` open mode, `ino:` inode |
| `ls -l /proc/<pid>/fd` | same as above but `<pid>` = another process's id |
| `lsof -p <pid>` | `lsof` (*list open files*); `-p <pid>` = one process's open files/sockets, with a `TYPE` column (`REG`, `IPv4`). Reads the same `/proc/<pid>/fd`. Needs real `lsof` (netlab), not netshoot's busybox stub |
| `docker build -t netlab networking-fundamentals/code` | `docker` (container tool); `build` = build an image; `-t netlab` = name (tag) it `netlab`; trailing path = build context (the folder holding the `Dockerfile`). From your own folder of [the four files](../code/minihttp.c) that path is `.` — it's the only command in the course that names a path on your Mac |
| `docker run --rm -it --privileged --name lab netlab` | `run` = start a container; `--rm` = delete it on exit; `-it` = interactive + TTY; `--privileged` = full kernel access; `--name lab` = name it; `netlab` = image |
| `docker exec -it lab zsh` | `exec` = run a command in a *running* container; `-it` = interactive + TTY; `lab` = container name; `zsh` = shell to start |
| `cc -Wall -o /tmp/fd-demo /code/fd-demo.c` | `cc` (*C compiler*); `-Wall` = all warnings; `-o /tmp/fd-demo` = output binary path; trailing `.c` = source file |
| `/tmp/fd-demo` | run the binary by path, in the foreground |

## Lesson 2 — What a socket really is

| Command | Syntax breakdown |
|---|---|
| `/tmp/fd-demo &` | `&` = run in the background; shell prints a job number `[1]` and keeps the prompt |
| `kill %1` | `kill` = send a signal (default `TERM`); `%1` = job number 1. opt: `kill -9 %1` to force |
| `pgrep -n fd-demo` | `pgrep` (*process grep*) = find PIDs by name; `-n` = newest match only. opt: `-f` match full command line, `-l` also print the name |
| `ls -l /proc/$(pgrep -n fd-demo)/fd \| grep socket` | `$(…)` = command substitution (splices the PID in); `grep` (*global regex print*) keeps only socket lines |
| `grep <inode> /proc/net/tcp` | search the TCP table for `<inode>`; no match = the socket has no address yet |

## Lesson 3 — Building minihttp, the listening server

| Command | Syntax breakdown |
|---|---|
| `cc -Wall -o /tmp/minihttp /code/minihttp.c` | compiles minihttp (already built at `/code/minihttp` in netlab) |
| `/tmp/minihttp 8080` | `8080` = port, passed as an argument to the program |
| `strace -e trace=socket,bind,listen,accept /tmp/minihttp 8080` | `strace` (*system-call trace*); `-e trace=…` = comma-list of calls to show; rest = program + args |
| `curl -s localhost:8080` | `curl` (*client URL*) = HTTP client; `-s` = silent (no progress meter); `localhost:8080` = host:port |
| `grep State: /proc/$(pgrep -f minihttp \| head -1)/status` | `$(… \| head -1)` = first matching PID; `/status` file's `State:` line = `S` sleeping / `R` running |
| `strace -e trace=accept …` | (lesson 5b too) trace only the listed syscall(s) |
| `ltrace <prog>` | like `strace` but for **library** calls (`libc`) instead of syscalls — one layer up |
| `ulimit -n` | `ulimit` (*user limit*); `-n` = max open file descriptors (soft limit). opt: `ulimit -Hn` for the hard limit |
| `prlimit --pid <pid>` | show (or set) the resource limits of an *already-running* process |
| `cat /proc/interrupts` | per-device, per-CPU hardware interrupt counts |

## Lesson 4 — The loopback interface

| Command | Syntax breakdown |
|---|---|
| `ip addr show lo` | `ip` (*internet protocol* config tool); `addr` = address subsystem; `show` = display; `lo` = interface name. opt: `eth0` for the real NIC, `ip a` short form |
| `cat /proc/net/dev` | per-interface RX/TX byte & packet counters. opt: `\| grep lo:` for one interface |
| `ping -c 4 127.0.0.1` | `ping` (sonar-style probe; backronym *Packet InterNet Groper*); `-c 4` = stop after 4 packets; trailing = target address. opt: `-i 0.2` shorter interval |

## Lesson 5 — Ports and /proc/net/tcp

| Command | Syntax breakdown |
|---|---|
| `cat /proc/net/tcp` | raw TCP socket table; addresses are hex and **little-endian** (byte-reversed) |
| `grep " 0A " /proc/net/tcp` | `" 0A "` = the state column (spaces anchor it): `0A`=LISTEN, `01`=ESTABLISHED, `06`=TIME_WAIT |
| `ls -la /proc/*/fd 2>/dev/null \| grep <inode>` | `*` = glob over every PID; `2>/dev/null` = discard permission errors; `grep <inode>` = find the owner |
| `ss -tlnp` | `ss` (*socket statistics*); `-t` tcp; `-l` listening only; `-n` numeric ports; `-p` show owning process. opt: drop `-l` for all states, `-u` for UDP |
| `netstat -tlnp` | the older tool `ss` replaced; same flags, same idea — recognise it on legacy boxes, but prefer `ss` |
| `lsof -i :8080` | `lsof -i` = internet sockets; `:8080` filters to that port. Joins socket→owning process for you (the inode walk, automated). Needs real `lsof` (netlab) |
| `python3 -m http.server 8081 --bind 127.0.0.1` | `-m http.server` = run the stdlib web server module; `8081` = port; `--bind 127.0.0.1` = listen on loopback only (vs `0.0.0.0` for every interface) |
| `ip -4 addr show eth0` | `-4` = IPv4 only; `addr show eth0` = the real interface's address (pipe `\| grep inet` for just the address line) |

## Lesson 5b — TCP states and the SYN scan

| Command | Syntax breakdown |
|---|---|
| `ss -tan` | `-t` tcp; `-a` **all** states (not just listening); `-n` numeric. The `State` column = `/proc/net/tcp`'s `st`, spelled out |
| `nc 127.0.0.1 8080` | `nc` (*netcat*) = open a raw TCP connection; with nothing typed it just *holds it open* (shows as `ESTAB`). Run with `&` to keep your shell |
| `strace -e trace=accept /code/minihttp 8080` | watch only `accept`: it hangs until a connection reaches **ESTABLISHED**, then prints `= 4` |
| `nmap -sS -p 8080 127.0.0.1` | `nmap` (*network mapper*); `-sS` = SYN ("stealth") scan — SYN, read reply, RST instead of ACK; stops at `SYN_RECV`, so `accept()` never fires. `-p` = port(s) (needs root) |
| `nmap -sT -p 8080 127.0.0.1` | `-sT` = connect scan — completes the full handshake to `ESTABLISHED`, so the app *does* see it. opt: `-p 1-1024` a range, `-Pn` skip host-up ping |

## Lesson 6 — Everything is a file

| Command | Syntax breakdown |
|---|---|
| `df -h /proc` | `df` (*disk free*); `-h` human-readable; trailing path = report the filesystem backing it. `/proc` shows size 0 → nothing on disk backs it |
| `stat /proc/net/dev` | `stat` = print a file's metadata (size, type, inode, owner). procfs files report `Size: 0` yet `cat` prints content — the size-0 contradiction |
| `ls -li /tmp/a.txt` | `-i` = show the **inode number** (first column) — the kernel's real ID for the file, independent of its name |
| `ln <target> <newname>` | **hard link**: a second directory entry pointing at the *same inode* (same inode number, link count `+1`). No `-s` |
| `ln -s <target> <name>` | **symbolic link**: its own inode whose *data is the target path string* (size = the string's length). opt: target need not exist (dangling allowed) |
| `readlink <name>` | print the path string stored inside a symlink. On a magic `/proc` symlink the string is *computed on read*, not stored |
| `mount` | list every filesystem grafted into the tree as `SOURCE on MOUNTPOINT type FSTYPE (options)`. `proc on /proc type proc` = no backing device. opt: `findmnt` draws it as a tree |
| `exec 7< file; rm file; cat /proc/self/fd/7` | open a file on fd 7, delete its name, still read it through `/proc` — the inode lives until its link count *and* open fds hit zero (forensics: recover deleted-but-running binaries) |

## Lesson 6b — The container's filesystem (optional)

| Command | Syntax breakdown |
|---|---|
| `mount \| grep 'on / '` | the container's root mount: `type overlay` with `lowerdir` (read-only image layers, colon-separated), `upperdir` (writable layer), `workdir` (scratch) |
| `df -h /` | `/` reports the *host* disk's size (~hundreds of GB) — the container sees host free space, with no per-container limit by default |
| `docker diff <container>` | (Mac shell) list the writable layer's changes vs the image: `A` added, `C` changed/copied-up, `D` deleted (whiteout). Reads `upperdir` for you |
| `docker run --rm … ` | `--rm` deletes the writable `upperdir` on exit — why container changes (and Pod restarts) lose data |
| `docker volume create <name>` | (Mac shell) make a persistent volume — a separate filesystem, not part of any overlay |
| `docker run -v <vol>:/data …` | mount the volume at `/data`; writes there bypass the overlay and survive the container (the `mount` idea, for persistence) |

---

← Back to **[Act I overview](README.md)**
