# Command reference — every command the course runs, taken apart

Every command from Acts I–IV, grouped by lesson, with the right column breaking down each syntax
element. This is the page for *"I know what I ran, I've forgotten why the flag was there"*.

**Placeholders:** `<pid>` a process id · `<inode>` a socket inode number · `<dev>` an interface name.
**"opt:"** marks a useful variant the lesson didn't run.

> ## Scope, stated honestly
>
> **This page covers Acts I–IV only** — the Linux, kernel and container-substrate half of the course,
> about 280 commands. Acts V–X are not here, and that is a decision rather than an omission:
>
> - Their command surface is overwhelmingly `kubectl`, and a `kubectl` line's meaning lives in the
>   *object* it names, not in its flags. A syntax breakdown of `kubectl get pods -o yaml` teaches
>   nothing; [`kubectl explain`](01-the-grammar.md#rule-7--derive-it-dont-recall-it) teaches everything.
>   For the flag-level speed drilling, [`exam-prep/kubectl-speed.md`](../exam-prep/kubectl-speed.md)
>   already exists and is better at it.
> - The maintenance honestly does not hold at that scale. The hand-written column is the half worth
>   reading and the half no generator can produce; spread over a thousand rows it would rot, and a
>   command reference that is subtly wrong is worse than one with a stated edge.
>
> `tools/gen-command-tables.py` will emit the skeleton for any act if you want to extend this —
> `python3 tools/gen-command-tables.py act-5-kubernetes` — and `--diff` reports commands a lesson runs
> that this page does not document.

## Starting the lab

Three commands open nearly every lesson, so they are here once rather than in every table.

| Command | Syntax breakdown |
|---|---|
| `docker build -t netlab networking-fundamentals/code` | `build` = build an image; `-t netlab` = tag (name) it; trailing path = the **build context**, the directory holding the `Dockerfile`. From your own folder of the four files that path is `.` — the only command in the course naming a path on your Mac |
| `docker run --rm -it --privileged --name lab netlab` | `--rm` = delete the container on exit; `-it` = interactive + TTY; `--privileged` = full kernel access, which is what lets you edit routes and namespaces; `--name lab` = a name to `exec` into later. **Acts I only** |
| `docker run --rm -it --privileged --network host --name lab nicolaka/netshoot` | `--network host` = **no network namespace of its own** — the container is *in the host's*. Acts II–IV need this, and it is why their drills change the host's real networking. `netshoot` carries the tools; `netlab` adds a C compiler |
| `docker exec -it lab zsh` | `exec` = run a command in an *already running* container; `zsh` = the shell to start |

---

# Act I — One machine talking to itself

## Lesson 1 — The file-descriptor table

| Command | Syntax breakdown |
|---|---|
| `exec 3>/tmp/scratch` | `exec` = apply the redirection to **the shell itself**, with no child process; `3>` = open fd **3** for writing; the path = what it points at. Adds a row to the fd table |
| `exec 3>&-` | `3>&-` = close fd **3** (`&-` means "close"). Removes the row |
| `ls -la /proc/self/fd` | `-l` long format; `-a` include `.`/`..`; `/proc/self/fd` = this process's fd directory, one symlink per open descriptor |
| `cat /proc/self/fdinfo/1` | kernel metadata for fd **1**: `pos:` byte offset, `flags:` open mode, `ino:` the inode |
| `ls -l /proc/<pid>/fd` | the same for another process — the `self` in the path above is just a magic symlink to your own pid |
| `cc -Wall -o /tmp/fd-demo /code/fd-demo.c` | `cc` = the C compiler; `-Wall` = all warnings; `-o <path>` = output binary; trailing `.c` = source |
| `/tmp/fd-demo` | run the binary by path, in the foreground |
| `lsof -p $(pgrep -n fd-demo)` | `lsof` (*list open files*); `-p <pid>` = one process's open files and sockets, with a `TYPE` column (`REG`, `IPv4`). Reads the same `/proc/<pid>/fd`. Needs real `lsof` (netlab) — netshoot's is a busybox stub |

## Lesson 2 — What a socket really is

| Command | Syntax breakdown |
|---|---|
| `/tmp/fd-demo &` | `&` = run in the background; the shell prints a job number `[1]` and returns the prompt |
| `kill %1` | `kill` = send a signal (default `TERM`); `%1` = job number 1. opt: `kill -9 %1` to force |
| `pgrep -n fd-demo` | `pgrep` (*process grep*) = find pids by name; `-n` = newest match only. opt: `-f` match the full command line, `-l` also print the name |
| `INO=$(readlink /proc/$(pgrep -n fd-demo)/fd/4 \| sed 's/[^0-9]//g')` | `readlink` prints a symlink's target — here `socket:[3209833]`; `sed 's/[^0-9]//g'` strips everything but the digits, leaving the bare inode. `$(…)` = command substitution, nested twice |
| `grep "$INO" /proc/net/tcp` | search the TCP table for that inode. **No match means the socket has no address yet** — it exists, but `bind()` hasn't happened |

## Lesson 3 — Building minihttp, the listening server

| Command | Syntax breakdown |
|---|---|
| `cc -Wall -o /tmp/minihttp /code/minihttp.c` | compiles the server (already built at `/code/minihttp` in netlab) |
| `/tmp/minihttp 8080` | `8080` = the port, passed as an argument to the program, not a flag |
| `strace -e trace=socket,bind,listen,accept /tmp/minihttp 8080` | `strace` (*system call trace*); `-e trace=…` = a comma list of calls to show; the rest is the program and its args. **Stops the process on every call** — that cost is why eBPF exists |
| `curl -s localhost:8080` | `curl` = HTTP client; `-s` = silent (no progress meter); `localhost:8080` = host:port |
| `grep State: /proc/$(pgrep -f minihttp \| head -1)/status` | `-f` matches the full command line; `head -1` takes the first pid; `State:` in `/status` is `S` sleeping / `R` running — this is how you see `accept()` blocking |
| `ltrace <prog>` | like `strace` but for **library** calls (libc) rather than syscalls — one layer up |
| `ulimit -n` | `ulimit` (*user limit*); `-n` = max open file descriptors, soft limit. opt: `-Hn` for the hard limit |
| `prlimit --pid <pid>` | read (or set) the limits of an **already-running** process, which `ulimit` cannot do |
| `cat /proc/interrupts` | per-device, per-CPU hardware interrupt counts |

## Lesson 4 — The loopback interface

| Command | Syntax breakdown |
|---|---|
| `ip addr show lo` | `ip` = the iproute2 tool; `addr` = the **object** (addresses); `show` = the **verb**; `lo` = which device. opt: `ip a` short form, `ip -br addr` one line per device |
| `ip addr show eth0` | the same for the real NIC. opt: `-4` to drop the IPv6 lines |
| `cat /proc/net/dev` | per-interface RX/TX byte and packet counters. opt: `\| grep lo:` for one interface |
| `ping -c 4 127.0.0.1` | `-c 4` = stop after 4 packets; trailing = target. opt: `-i 0.2` for a shorter interval |
| `ping -c 4 172.17.0.3` | the container's own external address — same kernel, so it still never touches a wire |

## Lesson 5 — Ports and /proc/net/tcp

| Command | Syntax breakdown |
|---|---|
| `cat /proc/net/tcp` | the raw TCP socket table *for this network namespace* — the path is a symlink to `self/net`, so it is never global. Addresses are hex and **little-endian** (byte-reversed): `0100007F` is `127.0.0.1` |
| `grep " 0A " /proc/net/tcp` | `" 0A "` = the state column, with spaces anchoring it: `0A`=LISTEN, `01`=ESTABLISHED, `06`=TIME_WAIT |
| `ls -la /proc/*/fd 2>/dev/null \| grep <inode>` | `*` globs every pid; `2>/dev/null` discards the permission errors from processes you don't own; `grep <inode>` finds the owner. This is the join `lsof` does for you |
| `ss -tlnp` | `-t` TCP; `-l` listening only; `-n` numeric (don't resolve service names); `-p` show the owning process. opt: drop `-l` for all states, `-u` for UDP, `-x` for Unix sockets |
| `netstat -tlnp` | the tool `ss` replaced. Same flags, same idea — recognise it on legacy boxes, prefer `ss` |
| `lsof -i :8080` | `-i` = internet sockets; `:8080` filters to that port. Needs real `lsof` (netlab) |
| `ip -4 addr show lo \| grep inet` | `-4` = IPv4 only, so the output is one line worth reading |
| `python3 -m http.server 8081 --bind 127.0.0.1 &` | `-m http.server` = run the stdlib module as a program; `8081` = port; `--bind 127.0.0.1` = **listen on loopback only**, versus `0.0.0.0` for every interface. This distinction is the whole lesson |
| `curl -s -o /dev/null -w '%{http_code}\n' 127.0.0.1:8080` | `-o /dev/null` = discard the body; `-w` = write out a chosen variable — `%{http_code}` is the status. The way to test reachability without reading a page |
| `curl --max-time 2 http://172.17.0.3:8081` | `--max-time 2` = give up after 2s, so a bound-to-loopback service fails fast instead of hanging |
| `docker run --rm -it --privileged -p 8080:8080 --name lab netlab` | `-p 8080:8080` = publish container port to host port. The DNAT rule this writes is opened up in Act IV |

## Lesson 5b — TCP states and the SYN scan

| Command | Syntax breakdown |
|---|---|
| `ss -tan` | `-a` = **all** states, not just listening; the `State` column is `/proc/net/tcp`'s `st` field spelled out |
| `nc 127.0.0.1 8080` | `nc` (*netcat*) opens a raw TCP connection and, with nothing typed, just holds it open — so it shows as `ESTAB`. Run with `&` to keep your shell |
| `strace -e trace=accept /code/minihttp 8080` | watch only `accept`: it hangs until a connection reaches ESTABLISHED, then prints `= 4` |
| `nmap -sS -p 8080 127.0.0.1` | `nmap` (*network mapper*); `-sS` = SYN ("stealth") scan — send SYN, read the reply, send RST instead of ACK. Stops at `SYN_RECV`, so `accept()` never fires and the application never sees it. `-p` = ports. Needs root |
| `nmap -sT -p 8080 127.0.0.1` | `-sT` = connect scan — completes the handshake, so the app *does* see it. opt: `-p 1-1024` a range, `-Pn` skip the host-up probe |

## Lesson 6 — Everything is a file

| Command | Syntax breakdown |
|---|---|
| `df -h /proc` | `df` (*disk free*); `-h` human-readable; trailing path = report the filesystem backing it. `/proc` shows size 0 — nothing on disk backs it |
| `stat /proc/net/dev` | print a file's metadata. procfs files report `Size: 0` and yet `cat` prints content: the contradiction the lesson is built on |
| `ls -li /tmp/a.txt` | `-i` = show the **inode number** first — the kernel's real identity for a file, independent of its name |
| `ln <target> <newname>` | **hard link**: a second directory entry pointing at the *same inode*. Same inode number, link count `+1`. No `-s` |
| `ln -s <target> <name>` | **symbolic link**: its own inode whose *data is the target path string*, so its size equals the string's length. The target need not exist |
| `readlink <name>` | print the path stored inside a symlink. On a magic `/proc` symlink that string is **computed on read**, not stored — which is what makes `/proc/self` work |
| `mount` | every filesystem grafted into the tree, as `SOURCE on MOUNTPOINT type FSTYPE (options)`. `proc on /proc type proc` has no backing device. opt: `findmnt` draws it as a tree |
| `exec 7< file; rm file; cat /proc/self/fd/7` | open on fd 7, delete the name, still read through `/proc`. The inode survives until link count **and** open fds both hit zero — which is how you recover a deleted-but-running binary |

## Lesson 6b — The container's filesystem (optional)

| Command | Syntax breakdown |
|---|---|
| `mount \| grep 'on / '` | the container's root: `type overlay`, with `lowerdir` (read-only image layers, colon-separated), `upperdir` (the writable layer) and `workdir` (scratch) |
| `df -h /` | reports the **host** disk's size — a container sees host free space, with no per-container limit by default |
| `docker diff <container>` | (run on your Mac) the writable layer's changes versus the image: `A` added, `C` changed/copied-up, `D` deleted (a whiteout). Reads `upperdir` for you |
| `docker volume create <name>` | a persistent volume — a separate filesystem, not part of any overlay |
| `docker run -v <vol>:/data …` | mount it at `/data`; writes there bypass the overlay and survive the container |

---

# Act II — Two machines on one wire

## Lesson 1 — The wire and the two names

| Command | Syntax breakdown |
|---|---|
| `cat /sys/class/net/eth0/address` | the MAC, read straight from sysfs. One file per field is what makes `/sys` better than `/proc` to script against |
| `cat /sys/class/net/eth0/statistics/rx_packets` | a single counter. Everything `ip -s link` prints lives as one file each under `statistics/` |
| `ip -s link show eth0` | `-s` = statistics. opt: `-s -s` **stacks** for per-error-type detail |
| `ip -4 addr show eth0` | your address and its prefix length, IPv4 only |
| `ip route show default \| awk '{print $3}'` | `default` is the route matching everything; field 3 of that line is the gateway's address. The idiom for "who is my gateway" with no hardcoding |
| `watch -n1 cat /proc/net/arp` | `watch` re-runs a command; `-n1` every second. The neighbour cache filling in, live |
| `ping -c 2 <unused address in your subnet>` | forces an ARP request for an address nobody owns, so you can watch the request go out and nothing come back |
| `ip neigh flush dev eth0` | `neigh` = the neighbour object; `flush` = empty it; `dev eth0` = scoped to one device. Makes the next ping re-ARP so you can watch it happen |
| `arp -n` | the old tool. `-n` = numeric, don't reverse-resolve |
| `ip neigh` | the replacement. With no verb, `show` is implied — true for most `ip` objects |
| `arping -c 1 <ip>` | ARP-level reachability: **layer 2 only, no IP involved**. Proves the wire when routing is broken |
| `scapy` | starts the interactive packet-crafting shell |
| `req = Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(op=1, pdst="<gateway>")` | `/` stacks layers outward-in; `ff:…:ff` = broadcast; `op=1` = request (`2` = reply); `pdst` = the address you're asking about |
| `req.show()` | print every field, including the ones scapy filled in for you. The habit that stops this being paste-and-run |
| `reply = srp1(req, iface="eth0", timeout=2)` | `srp1` = **s**end and **r**eceive at layer 2 (**p**acket), return the **1**st reply; `timeout=2` so it gives up |
| `reply[ARP].hwsrc` | index into the ARP layer of the reply; `hwsrc` = the hardware address of whoever answered |

## Lesson 1b — VLANs and segmentation

| Command | Syntax breakdown |
|---|---|
| `ip link add link eth0 name eth0.10 type vlan id 10` | `link add` = create a device; the inner `link eth0` = its **parent**; `name` = what to call it; `type vlan` picks the kind; `id 10` = the 12-bit VLAN tag. The `.10` naming is convention, not a requirement |
| `cat /proc/net/vlan/config` | each VLAN interface with its parent and tag — the kernel's own view of what you just built |
| `cat /sys/class/net/eth0.10/address` | **the same MAC as the parent.** A VLAN interface is a tag, not a second network card |
| `ip -d link show eth0.10` | `-d` = details, which is what reveals `vlan protocol 802.1Q id 10`. Without `-d` the VLAN-ness is invisible |

## Lesson 2 — IP and routing

| Command | Syntax breakdown |
|---|---|
| `head -20 /proc/net/fib_trie` | the kernel's actual routing structure — a trie, showing how longest-prefix match is implemented rather than just its result |
| `cat /proc/net/route` | the main table in hex, little-endian like `/proc/net/tcp` |
| `ip route show default` | just the catch-all route |
| `ip route get 8.8.8.8` | **the decision, not the table.** Asks the kernel "which route would you use, out which device, from which source address" — the single most useful routing command |
| `ip route get 127.0.0.1` | the same for loopback, which resolves via a different table entirely |

## Lesson 2b — Routing protocols and BGP

| Command | Syntax breakdown |
|---|---|
| `ip route show` | note the `proto` word on the rows that have one: who installed this route — `kernel`, `static`, `bgp`, `dhcp`. A route added with no explicit origin is `boot`, and iproute2 prints **nothing** for it — which is why the default route, the first row everyone reads, usually has no `proto` at all |
| `ip route add 203.0.113.0/24 dev eth0 proto bgp` | `add` = the verb; `dev eth0` = out which device; `proto bgp` **labels** the origin. Nothing verifies the label — you're pretending a daemon did it |
| `ip route show proto bgp` | filter by origin. Any field on the route object can usually be used as a filter |
| `ip route add blackhole 208.65.153.0/24` | `blackhole` = a route that silently discards. The BGP hijack, reproduced: a more specific prefix wins over a less specific one regardless of who announced it |
| `ip route get 208.65.153.10` | which of the two competing routes wins, decided by prefix length. **Expect an error:** when the blackhole wins, this prints `RTNETLINK answers: Invalid argument` and exits 2. That error *is* the answer — the kernel chose the route that discards. Compare an address inside the wider prefix but outside the hijacked one, which still resolves normally |
| `ip route del <prefix>` | `del` — and note you do **not** repeat the `dev`/`proto` attributes to delete |

## Lesson 3 — ICMP, UDP, and TTL

| Command | Syntax breakdown |
|---|---|
| `tcpdump -nn -i any icmp` | `-nn` = resolve neither hostnames nor **port names** (single `-n` is hosts only); `-i any` = every interface; `icmp` = the filter expression. opt: `-c 5` stop after 5, `-w f.pcap` write a capture file |
| `traceroute 8.8.8.8` | sends packets with rising TTL; each hop that discards one replies with ICMP "time exceeded", revealing itself. opt: `-n` skip reverse DNS, which makes it much faster |
| `nc -u -l 9999` | `-u` = UDP; `-l` = listen. There is no handshake, so this "connection" is a fiction |
| `cat /proc/net/udp` | the UDP table — the same shape as `/proc/net/tcp` but with no state column, because UDP has no states |
| `tcpdump -nn -i eth0 udp port 9999` | `udp port 9999` composes protocol + type + value from libpcap's filter grammar |
| `echo hello \| nc -u -w1 8.8.8.8 9999` | `-w1` = give up after 1 second, so `nc` exits. The packet leaves and nothing comes back — and UDP cannot tell you that |

## Lesson 3b — MTU and fragmentation

| Command | Syntax breakdown |
|---|---|
| `cat /sys/class/net/eth0/mtu` | the largest payload this device will carry |
| `ip link set eth0 mtu 1500` | **do this first.** The pair below assumes a 1500-byte path, and on Docker Desktop `eth0` comes up at MTU 65535, where both sizes succeed and the lesson silently does not happen |
| `ping -c1 -M do -s 1472 <gateway>` | `-M do` = set **Don't Fragment**; `-s 1472` = payload bytes. 1472 + 8 (ICMP) + 20 (IP) = exactly 1500, so it fits. Use your gateway, not `8.8.8.8` — external ICMP is often dropped entirely |
| `ping -c1 -M do -s 1473 <gateway>` | one byte over, and DF forbids splitting it, so it fails with **`ping: sendmsg: Message too large`**. Note *where* that came from: it is a local `EMSGSIZE` from your own stack, not an ICMP "fragmentation needed" from a router — a distinction the path-MTU-discovery story depends on. This pair is how you *measure* a path's MTU rather than guess it |

## Lesson 3c — DHCP

| Command | Syntax breakdown |
|---|---|
| `nmap --script broadcast-dhcp-discover -e eth0` | `--script` runs an NSE script; this one broadcasts a DHCP DISCOVER; `-e eth0` = out which interface. Shows the offer without accepting it |
| `tcpdump -i eth0 -n -v port 67 or port 68` | `or` composes two filter primitives; 67 is the server, 68 the client; `-v` prints the option fields, which is where the interesting content is |

## Lesson 4 — DNS

| Command | Syntax breakdown |
|---|---|
| `grep '^hosts:' /etc/nsswitch.conf` | the **order** of resolution sources — `files dns` means `/etc/hosts` is consulted first. On glibc this file decides whether DNS is asked at all. **Not in this lab:** Alpine uses musl, which implements no NSS and ignores the file entirely — see [the state map](02-the-state-map.md) |
| `cat /etc/resolv.conf` | the recursive resolver's address, the `search` list, and `ndots` — how many dots a name must contain before the resolver tries it as-is instead of appending each `search` domain first. The option behind most cluster DNS surprises |
| `dig +trace google.com` | `+trace` walks the delegation from the root down, one query per level. Note the syntax: `+option`, not `-flag` — `dig` is not a getopt tool |
| `echo "127.0.0.1 my-fake-service" >> /etc/hosts` | `>>` appends. Proves `/etc/hosts` beats DNS, because NSS asked `files` first |

---

# Act III — The internet

## Lesson 1 — The three-way handshake

| Command | Syntax breakdown |
|---|---|
| `tcpdump -i any -nn tcp port 8080` | capture both directions of one port. You will see exactly three packets before any data: `[S]`, `[S.]`, `[.]` |
| `nc -l 8080` | listen. opt: `nc -l -k 8080` to keep listening after the first client disconnects |
| `nc 127.0.0.1 8080` | connect. Between these two commands, the whole handshake happens |

## Lesson 2 — TCP states

| Command | Syntax breakdown |
|---|---|
| `curl -s google.com > /dev/null` | make and immediately finish one connection, so there is something in TIME_WAIT to look at |
| `ss -tan state time-wait` | `state time-wait` is **`ss`'s own filter language**, not a flag — and not libpcap's. opt: `state established`, `state syn-sent`, or `state connected` for a group |

## Lesson 2b — conntrack

| Command | Syntax breakdown |
|---|---|
| `conntrack -E -p tcp` | `-E` = **event mode**: stream flows as they change, rather than dumping the table. `-p tcp` filters by protocol. The only way to watch a NAT decision being made |
| `conntrack -C` | `-C` = count the flows tracked right now. opt: `-L` to list them, `-D` to delete one |
| `sysctl net.netfilter.nf_conntrack_max` | the table ceiling. Compare against `-C`: as they converge, new connections fail intermittently under load — a failure that looks exactly like a flaky network |

## Lesson 3 — TCP and reliability

| Command | Syntax breakdown |
|---|---|
| `nc -l 8080 \| (sleep 30; cat)` | listen but **don't read for 30 seconds**. The subshell is what makes the receive buffer fill, so you can watch the window close |
| `ss -tmi dst :8080` | `-m` = socket memory; `-i` = internal TCP info; `dst :8080` = a filter on the destination. Together: buffers and congestion state for one connection |
| `grep ':1F90' /proc/net/tcp` | `1F90` is 8080 in hex; the `tx_queue:rx_queue` columns are bytes sitting in each buffer — the same numbers `ss -m` prettifies |
| `awk '$3 ~ /:1F90$/ {print "cwnd=" $16, "ssthresh=" $17}' /proc/net/tcp` | `$3` = the remote address column, matched by regex; fields 16 and 17 are the congestion window and slow-start threshold. Reading congestion control out of the raw file |
| `ss -ti dst :80` | the same values with names attached, including `rtt`, `retrans` and the congestion algorithm |

## Lesson 4 — HTTP

| Command | Syntax breakdown |
|---|---|
| `curl -v http://httpbin.org/get 2>&1` | `-v` prints the request and response headers — `>` lines are sent, `<` received. `2>&1` merges stderr, where `-v` writes, so it can be piped |
| `curl -w "dns: %{time_namelookup}s\ntcp: %{time_connect}s\ntls: %{time_appconnect}s\ntotal: %{time_total}s\n" -o /dev/null -s <url>` | `-w` = write-out template with `%{variable}` fields. The cumulative timings that separate "slow DNS" from "slow TLS" from "slow server" in one command |
| `curl -v --http1.1 -o /dev/null <url> 2>&1 \| grep -i 'alpn\|^> GET\|^< HTTP'` | `--http1.1` pins the version; the grep picks out the ALPN negotiation and the request/status lines. Run against `--http2` to see the same page fetched differently |
| `curl -sI <url> \| grep -i 'alt-svc'` | `-I` = HEAD request, headers only; `alt-svc` is the server advertising HTTP/3 on another transport |
| `curl -V \| grep -o HTTP3` | `-V` (capital) = curl's **own** build info, not a request. Prints `HTTP3` only if your build supports it |

## Lesson 5 — TLS

| Command | Syntax breakdown |
|---|---|
| `openssl s_client -connect example.com:443 -servername example.com` | `s_client` = a TLS client you drive by hand; `-connect host:port`; `-servername` sets SNI, without which a shared-IP server can't know which certificate to send |
| `echo \| openssl s_client -connect … 2>/dev/null \| openssl x509 -noout -issuer -subject -dates` | `echo \|` feeds EOF so `s_client` exits instead of waiting; the second `openssl` parses the certificate it printed. `-noout` = don't re-print the certificate itself, just the fields asked for |
| `curl -sI http://github.com \| head -3` | the plain-HTTP response — a redirect, which is a request that already happened in cleartext |
| `curl -sI https://github.com \| grep -i strict-transport` | HSTS: the header that tells a browser never to try `http://` again |

---

# Act IV — One machine pretends to be many

## Lesson 1 — Namespaces

| Command | Syntax breakdown |
|---|---|
| `ls -la /proc/self/ns/` | one magic symlink per namespace type; each target is `type:[inode]`. **The inode is the identity** |
| `ip netns add test` | creates a named network namespace as a bind mount under `/run/netns/` — which is why `ip netns list` cannot see Docker's namespaces, which are not created this way |
| `ip netns exec test ip addr` | `exec <name> <cmd>` runs a command inside that namespace. Expect a down `lo` and, depending on which tunnel modules your kernel has loaded, a handful of per-namespace stubs (`tunl0`, `gre0`, `sit0`, …). What matters is what is *absent*: no addresses, no routes, no way out |
| `ip netns exec test ls -la /proc/self/ns/net` | **a different inode from the host's** — the whole proof, in one comparison |
| `ip netns exec test ping 8.8.8.8` | fails, because a namespace with no route and no device cannot reach anything. The failure is the lesson |
| `ip netns del test` | destroys it. opt: `ip netns list` to confirm |

## Lesson 1b — cgroups

| Command | Syntax breakdown |
|---|---|
| `docker run --rm nicolaka/netshoot cat /sys/fs/cgroup/memory.max` | `max` unlimited by default |
| `docker run --rm --memory 64m --memory-swap 64m nicolaka/netshoot cat /sys/fs/cgroup/memory.max` | `--memory` sets the limit; `--memory-swap` equal to it disables swap, so the limit is real. The file now reads `67108864` |
| `cat /proc/self/cgroup` | `0::/` — this process's cgroup path, as seen from inside, where it is always the root |
| `cat /sys/fs/cgroup/cpu.max` | two numbers: quota and period. `50000 100000` = 50 ms of CPU per 100 ms, i.e. half a core |
| `cat /sys/fs/cgroup/memory.current` | live usage, which is what the limit is compared against |
| `free -h` | reports the **whole machine's** RAM. A cgroup limits you without telling `free` about it, which is why JVMs and Node used to get this catastrophically wrong |
| `python3 -c 'x = bytearray(200 * 1024 * 1024); print("got it")'` | allocate 200 MB against a 64 MB limit. The shell prints `Killed` and exit 137 — but no *reason*, and nothing about memory. The explanation is in the file below |
| `cat /sys/fs/cgroup/memory.events` | `oom_kill` is no longer 0. **The evidence lives here**, not in the container's output |
| `cat /sys/fs/cgroup/cpu.stat` | `nr_throttled` and `throttled_usec` — the difference between "slow code" and "code being held back by a quota" |

## Lesson 2 — veth and bridge

| Command | Syntax breakdown |
|---|---|
| `ip link add veth0 type veth peer name veth1` | `type veth` = a virtual Ethernet **pair**; `peer name` names the other end. Always two, like the two plugs of one cable |
| `ip link set veth1 netns ns1` | `set` = the verb; `netns <name>` moves the device **into** a namespace. It vanishes from the host's `ip link` — a device belongs to exactly one namespace |
| `ip addr add 10.10.0.1/24 dev veth0` | adds the address, and the kernel installs the directly-connected route for the whole `/24` **when the interface comes up** — `proto kernel`, because you did not write it. That route, not any `ip route` command, is what makes the first ping work. Check `ip route` straight after this line and you will see nothing: bring the link up and it appears, carrying `linkdown` until the peer is up too |
| `ip link set veth0 up` | interfaces start administratively down. Both ends must be up |
| `ip netns exec ns1 ip link set lo up` | even loopback starts down in a fresh namespace |
| `ip link add br0 type bridge` | a software switch |
| `ip link set veth-a master br0` | `master` = enslave this device to that bridge — the equivalent of plugging a cable into a switch port. Visible afterwards as `/sys/class/net/br0/brif/veth-a` |
| `bridge fdb show br br0` | the **forwarding database**: which MAC was last seen on which port. `ip` can create a bridge; only `bridge` can show you this |
| `ip link del veth-a` | deleting one end deletes the pair, including the end inside a namespace |
| `ip netns del ns2` | deleting a namespace destroys every device still in it |

## Lesson 3 — iptables and NAT

| Command | Syntax breakdown |
|---|---|
| `iptables -t nat -L -n -v` | `-t nat` = which **table** (`nat` rewrites addresses, `filter` accepts/drops); `-L` = list; `-n` = numeric, no DNS; `-v` = verbose, which adds the packet and byte counters — the column that tells you whether a rule is actually being hit |
| `iptables -t filter -L -n -v --line-numbers` | `--line-numbers` gives you the index you need to delete a rule by position |
| `iptables -t nat -L POSTROUTING -n -v` | one **chain**: `POSTROUTING` is the last hook before a packet leaves, which is where source NAT has to happen |
| `docker run -d -p 8080:80 --name pub nginx` | `-d` detached; `-p 8080:80` publishes host 8080 to container 80 — and *writes the DNAT rule you are about to read* |
| `ip link show docker0` | the bridge Docker created for you: exactly lesson 2's `br0`, under a different name |
| `ls /sys/class/net/docker0/brif/` | the container's host-side veth end, plugged into that bridge |
| `iptables -t nat -L DOCKER -n` | Docker's own chain, holding the `DNAT tcp dpt:8080 to:172.17.x.x:80` that `-p` created |
| `iptables -L FORWARD -n --line-numbers` | the chain that decides whether traffic may be routed *through* this host — the rules that make container-to-outside work |

## Lesson 4 — Overlay and VXLAN

| Command | Syntax breakdown |
|---|---|
| `ip link add vxlan0 type vxlan id 42 local 172.31.0.1 remote 172.31.0.2 dstport 4789 dev vu1` | `type vxlan`; `id 42` = the VNI, the tenant identifier; `local`/`remote` = the **underlay** endpoints; `dstport 4789` = the standard VXLAN UDP port (Flannel uses 8472); `dev` = which device carries the outer packet |
| `ip netns exec vx1 ping -c3 10.200.0.2` | an overlay address reached across an underlay that has never heard of it |
| `tcpdump -ni vu2 -c 4 udp port 4789` | the **outer** packets. Your ICMP is now cargo inside UDP — the encapsulation, visible |
| `ip -d link show vxlan0` | `-d` again: without it, none of the `vxlan id 42 local … remote …` detail prints |
| `ip link set vu2 mtu 1400` | shrink the underlay MTU to break the overlay — the failure every real overlay eventually hits |
| `ip -s link show vu2` | the RX `dropped` counter climbing with each large ping. **The evidence that a silent drop is happening**, and where to look for it |
| `ip link set vxlan0 mtu 1350` | the fix: the overlay MTU must leave room for the outer headers. 1400 − 50 for VXLAN = 1350 |

---

## Keeping this page true

```bash
python3 tools/gen-command-tables.py --diff reference/05-per-act-commands.md \
  act-1-one-machine act-2-two-machines act-3-the-internet act-4-one-pretends-many
```

Prints any command a lesson runs that this page does not document. Run it after editing a lesson in
Acts I–IV; a new row with an empty breakdown is the intended state until someone writes the breakdown.

---

Next: **[derive it](06-derive-it.md)** — the drills that make you write commands that are *not* on this
page.
