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

## Lesson 3b — The stateful firewall

| Command | Syntax breakdown |
|---|---|
| `iptables -P INPUT DROP` | `-P` sets a **chain policy** — the verdict for a packet that reaches the end of a *built-in* chain undecided. It is not a rule and it has no counters of its own beyond the chain header. Only the five built-in chains have one; a user chain returns to its caller instead |
| `iptables -A INPUT -i lo -j ACCEPT` | `-i` matches the interface the packet **arrived on** (`-o` is the departing one, and is meaningless in `INPUT`). `lo` is the only interface whose traffic must have come from a local process, which is the entire argument for this rule |
| `iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT` | `-m NAME` loads a **match extension** — a module that can test something the base syntax cannot. `conntrack` reads the flow table, so `--ctstate` matches on the *table* rather than on any header field. `ESTABLISHED` = a row exists with traffic both ways; `RELATED` = a different flow the table can prove belongs to a tracked one (ICMP errors, a helper's expected data connection). The older spelling `-m state --state` is the deprecated form of the same idea |
| `iptables -R INPUT 2 …` | `-R` **replaces** rule 2 in place, preserving position. `-A` appends, `-I` inserts (`-I INPUT 1` = to the top), `-D` deletes. Position is the whole semantics of a chain, so prefer `-R` over delete-then-append when editing |
| `iptables -j REJECT --reject-with tcp-reset` | `REJECT` *answers* the packet instead of discarding it; `--reject-with` picks the answer. `tcp-reset` is the RST an unoccupied port would have sent, so the client sees `Connection refused` instantly. Default without the flag is an ICMP port-unreachable. Contrast `DROP`, which sends nothing and costs the client its full timeout |
| `iptables -N GATE` / `iptables -A INPUT -j GATE` / `iptables -A GATE -j RETURN` | `-N` creates a **user chain** — a subroutine, not a hook. `-j GATE` jumps into it; `RETURN` (or falling off its end) resumes at the rule **after** the jump in the caller. Only `ACCEPT`/`DROP`/`REJECT` are terminal. This is the whole grammar of `DOCKER-USER` and of Act V's `KUBE-` tree |
| `iptables -L INPUT -n -v --line-numbers` | `-n` numeric (no DNS lookups, which are slow and can hang behind the very firewall you are debugging); `-v` adds the per-rule `pkts`/`bytes` counters, which are the only evidence of which rule traffic actually hit; `--line-numbers` gives you the index `-R`/`-D` take |
| `curl -s -o /dev/null -m 5 -w 'time=%{time_total}s\n' URL` | `-w` prints a chosen variable **after** the transfer; `%{time_total}` is the measurement that separates `DROP` (the full `-m` budget, exit 28) from `REJECT` (milliseconds, exit 7). `-o /dev/null` discards the body so only the measurement prints |
| `nmap -sS -p 9000 --reason -Pn <host>` | `--reason` adds the column that makes this a mechanism check rather than a verdict: `syn-ack` (a listener answered → `open`), `reset` (the RST an unoccupied port or a `REJECT` rule sends → `closed`), `no-response` (nothing came back → `filtered`). `-Pn` skips host discovery, which would otherwise be dropped by the same firewall you are measuring |

## Lesson 3c — When NAT runs out

| Command | Syntax breakdown |
|---|---|
| `curl --local-port 41000 http://1.1.1.1/` | pins the **source** port the client uses, which is normally the kernel's choice. Its purpose here is to force a NAT collision on demand rather than waiting for coincidence |
| `conntrack -D -d 1.1.1.1` | `-D` **deletes** matching rows; `-d` filters on destination. Clearing the view before an experiment, not a fix — a live connection whose row you delete simply establishes a new one |
| `sysctl net.ipv4.ip_local_port_range` | the two numbers the kernel picks ephemeral source ports from. Read it before writing any rule about "the ephemeral range", because the range is a tunable and not a constant |
| `iptables -t nat -A POSTROUTING -s 10.80.0.0/24 -d 10.80.0.0/24 -j MASQUERADE` | source **and** destination on the same subnet — the **hairpin** rule. Meaningless on an ordinary network; mandatory when a translated address lives on the same segment as the clients dialling it, because otherwise the reply crosses the segment direct and never passes the translator |
| `iptables -j MASQUERADE --random-fully` | allocate the replacement source port from the whole space at random instead of searching upward from the client's choice. Fixes collision-under-load, whose symptom is a dropped SYN and a ~1s retransmit tail. This is the flag kube-proxy carries |
| `iptables -t mangle -A OUTPUT -d 1.1.1.1 -j MARK --set-mark 1` | `-t mangle` is the table whose verb is *annotate*. A **mark** is a 32-bit integer attached to the packet inside this kernel only — never on the wire, invisible to every other machine. Useless alone; its whole point is the next line |
| `ip rule add fwmark 1 table 100` | the policy layer above the routing table: *packets marked 1 are looked up in table 100*. This is the join between netfilter and routing — a firewall match now selects a route, which is how VPNs, multi-homed hosts and egress gateways steer |
| `ip route add blackhole default table 100` | a route that discards rather than forwards, in a named table. Produces `Network is unreachable` — a **routing** failure with no rule having dropped anything, which is how you tell `mangle` steering apart from `filter` refusal |
| `iptables -t raw -A OUTPUT -d 1.1.1.1 -j NOTRACK` | `-t raw` runs at a priority **before** connection tracking, which is the only place a decision about tracking can be made. `NOTRACK` exempts the flow from the table: it stops costing a row, and simultaneously loses NAT and every `--ctstate` match. Not an optimisation — a semantic change |
| `sysctl -w net.bridge.bridge-nf-call-iptables=0` | Whether **bridged** frames traverse the iptables hooks and conntrack. Default `1` anywhere Docker or Kubernetes has run, which is why hairpin NAT bugs are hard to reproduce by hand: at `1`, conntrack un-NATs the bridged reply for you and the bug disappears. Per network namespace — in a `--network host` container this is the machine's setting, in an ordinary container it is the container's |
| `ip route add unreachable default table 100` | A route *type* rather than a destination. `unreachable` fails the lookup (as `blackhole` discards and `prohibit` rejects), which is how you prove a **routing** failure with no rule dropping anything. Prefer it to `blackhole` here because `ip route get` then reports the failure out loud |
| `ip route get 1.1.1.1 mark 1` | Asks for the routing decision *as if* the packet carried that mark, without sending anything. Run it twice — once with `mark 1`, once without — and the two answers are the proof that `ip rule` selected a different table. The only way to see a policy-routing decision in isolation |

## Lesson 3d — The transparent proxy

| Command | Syntax breakdown |
|---|---|
| `iptables -t nat -A OUTPUT -p tcp -d 1.1.1.1 --dport 80 -j REDIRECT --to-port 3129` | `REDIRECT` is DNAT with the destination address fixed to *this machine*, so you need name only a port. Legal in `nat` `PREROUTING` and `OUTPUT`. It is why a proxy can be inserted without knowing its own address — and why the original destination is gone by the time a socket sees the connection |
| `conn.getsockopt(socket.SOL_IP, 80, 16)` | socket option 80 is `SO_ORIGINAL_DST`. It reads the pre-rewrite destination out of the flow's **conntrack row** and returns a 16-byte `sockaddr_in`: family at `[0:2]`, port big-endian at `[2:4]`, address at `[4:8]`. Fails `Protocol not available` when the flow is untracked, because there is no row to read |
| `srv.setsockopt(socket.SOL_IP, 19, 1)` | option 19 is `IP_TRANSPARENT`: this socket may bind and accept connections addressed to **someone else**. Requires privilege. It is the userspace half of `TPROXY` — without it the marked packet arrives and no socket will claim it |
| `iptables -t mangle -A PREROUTING … -j TPROXY --on-port 3129 --tproxy-mark 1` | hands the packet to a local transparent socket **without rewriting it**, and marks it in the same action. Legal in `mangle PREROUTING` only — which is a statement about what it is for: traffic passing *through* you, never traffic you sent |
| `ip route add local default dev lo table 100` | route type `local` means *deliver here rather than forward*. Paired with `ip rule add fwmark 1 lookup 100`, it is what stops a packet addressed to `1.1.1.1` from being routed to `1.1.1.1` — the reason `TPROXY` costs a routing table and `REDIRECT` does not |
| `iptables -t raw -A OUTPUT … -j NOTRACK` (on a REDIRECTed flow) | Worth knowing as a **non**-tool: because NAT is implemented on top of the conntrack row, exempting a flow from tracking does not blind an interception, it removes it. The `nat` table is skipped entirely and the `REDIRECT` counter never moves. There is no configuration in which the interception fires and the row is absent |
