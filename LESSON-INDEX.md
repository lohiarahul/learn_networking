# Lesson index — the content abstraction

**Purpose:** locate a tool/concept *without* reading full lessons (just-in-time retrieval via
lightweight identifiers). One line per lesson: `file — gist — introduces`. If a tool isn't listed,
`grep` or spawn an Explore subagent; then add it here.

**Build status (2026-07-07):** Acts 1–5 (Stages 0–3, 6, 7) are **complete and teaching**. The open
gaps are *structural*, not lesson content: Act 4 lacks nothing now, Acts 3–4 gained `diagnose.md`,
and `the-whole-stack.md` exists. The genuinely *unbuilt* stages are **4 (crypto), 5 (identity),
8 (AWS networking), 9 (AWS security)** — see the roadmap banner in `JOURNEY-MAP.md`. Fill those
next; don't rewrite Acts 3–5, which are done.

Lab images: Act 1 = `netlab` (compiler) on bridge. Acts 2–5 = `nicolaka/netshoot --network host`
(Act 5 also `kind`/`kubectl`). scapy + tcpdump + nmap ship in netshoot.

## Act 0 — orientation (before the wire: the actor and its only tool)
- `01-what-is-a-process.md` — a process = address space + fd table — `ps`, `/proc/self/fd`, redirection
- `02-how-processes-communicate.md` — the socket entry the whole course is about — `nc`, `socket:[inode]`, the bridge question

## Act 1 — one machine (file-pure; no packet capture by design)
- `01-the-fd-table.md` — fd table = a process's whole link out — `exec N>`, `/proc/self/fd`, `/proc/self/fdinfo`, `lsof -p`, `docker exec`
- `02-the-socket-object.md` — socket = handle to a kernel object (tuple/buffers/state) — `/proc/net/tcp` (intro), bind-vs-bare
- `03-minihttp-server.md` — socket→bind→listen→accept ritual — `strace`/`ltrace`, `ulimit`/`prlimit`; **eBPF/bpftrace promised "earned in K8s stage, not here"**
- `04-loopback.md` — 127.0.0.1, the stack with no wire — `ip addr`, `/proc/net/dev`, `ping`; `0.0.0.0` vs `127.0.0.1`
- `05-ports-and-proc-net-tcp.md` — decode the socket ledger by hand — little-endian hex, `ss`, `lsof -i`, `netstat`(rival), `python3 -m http.server`
- `05b-tcp-states-and-the-syn-scan.md` — states + stealth scan — TCP states, SYN/ACK/RST flags, `nmap -sS/-sT`, `strace` accept
- `06-everything-is-a-file.md` — capstone: a file is an interface — inode, `mount`/`findmnt`, magic symlinks, VFS, `df`/`stat`/`ln`
- `06b-the-container-filesystem.md` — optional side road — overlayfs, copy-on-write, volumes
- supporting: `README` · `test-yourself`(10 Q) · `diagnose`(drills) · `commands` · `in-the-wild`(Mac: lsof/vmmap)

## Act 2 — two machines (first packet capture appears here, in L3)
- `01-ethernet-and-arp.md` — MAC vs IP, ARP the translator — frame fields, `/sys/class/net`, `ip link`/`-s`/`-d`, `/proc/net/arp`, `arp -n`, `ip neigh`; **scapy debut** ("ask for a mapping yourself" `srp1(Ether()/ARP(op=1))`) + `arping` rival; ARP-spoof shown (op=2, not run)
- `01b-vlans-and-segmentation.md` — broadcast domain as a number — 802.1Q tag, `ip link add type vlan`, `/proc/net/vlan/config`, `ip -d link`
- `02-ip-and-routing.md` — 32-bit addr + longest-prefix match — CIDR/mask, `/proc/net/route`, `/proc/net/fib_trie`, `ip route`, `ip route get`
- `02b-routing-and-bgp.md` — who fills the table — AS/ASN/AS-path, `ip route ... proto bgp`, RIB vs FIB; **hijack staged by hand** (`ip route get` on /22 vs blackhole /24)
- `03-icmp-and-udp.md` — error channel + bare datagram + hop budget — **`tcpdump` earned here** (`AF_PACKET`), ICMP types, `/proc/net/udp`, `dig`, `traceroute`, TTL
- `03b-mtu-and-fragmentation.md` — too big for the wire — MTU, DF/MF, PMTUD, `/sys/class/net/eth0/mtu`, `ping -M do -s`
- `03c-dhcp.md` — DORA over broadcast/UDP — `nmap --script broadcast-dhcp-discover`, **`tcpdump port 67 or 68`** (watch `0.0.0.0→255.255.255.255` live), `dhclient.leases`, `/etc/resolv.conf`
- `04-dns.md` — distributed name DB — stub/recursive/root/TLD/auth, `/etc/hosts`/`resolv.conf`/`nsswitch.conf`, `dig +trace`
- supporting: `README`(+lab-switch note) · `test-yourself`(10 Q, Q10=scapy) · `diagnose`(4 drills: ARP/route/MTU/hosts) · `in-the-wild`(arp -a, anycast, Wireshark/tshark)

## Act 3 — the internet  ⟨complete⟩
- `01-tcp-handshake.md` (SYN/seq/ISN, `tcpdump` flags, Morris shadow) · `02-tcp-states.md` (state machine, `TIME_WAIT`) · `02b-conntrack.md` (flow table, NAT memory, table exhaustion) · `03-tcp-reliability.md` (window + flow control + congestion control/`cwnd`) · `04-http.md` (text protocol, HTTP/1.1→2→3 motivation chain, L4-vs-L7 proxies) · `05-tls.md`
- supporting: `README` · `test-yourself`(10 Q) · `diagnose`(4 drills, host-mutating — cleanup mandatory) · `in-the-wild`
- tools: `tcpdump`, `ss -ti/-tmi`, `nc`, `curl -v/--http1.1/--http2`, `conntrack`, `openssl s_client`. Deferred (roadmap): scapy SYN-craft, level-ip capstone, deepen TLS into Stage 4 crypto.

## Act 4 — containers  ⟨complete⟩
- `01-namespaces.md` · `01b-cgroups.md` (see vs use — cgroup v2 `memory.max`/`cpu.max`/`memory.events`, OOM-kill, `free` lies) · `02-veth-and-bridge.md` · `03-iptables-and-nat.md` (`iptables`/NAT/conntrack, `docker0`/`-p` recognition) · `04-overlay-vxlan.md` (VXLAN tunnel built by hand between two netns, `dstport 4789`, MTU black hole sprung)
- supporting: `README` · `test-yourself` · `diagnose`(drills) · `in-the-wild`(Docker Desktop VM)
- Deferred (roadmap): deepen `nsenter`, `nft` one-liner.

## Act 5 — kubernetes  ⟨complete⟩
- `01-lab-with-kind.md` — the real cluster — `kind`, `kubectl`, node via `docker exec` vs netshoot Pod
- `02-pod-networking.md` — a Pod = Act-4 netns held by the pause container — shared netns, `nsenter`
- `03-services.md` — what answers to a ClusterIP (Act-4 DNAT + conntrack) — `KUBE-SERVICES`/`SVC`/`SEP` chains, EndpointSlice + readiness, the iptables-scaling → IPVS → eBPF arc, NodePort/LoadBalancer
- `04-coredns.md` — Act-2 DNS scaled to the cluster — `/etc/resolv.conf`, search domains, `dig` in-Pod
- `05-cni.md` — the veth-pair installer (Act-4 wiring, run by a binary) — CNI contract, IPAM, Pod routes
- `06-ingress.md` — Act-3 TLS terminated at the edge — Host-header routing, one IP many hosts
- `07-network-policy.md` — iptables allow/deny on Pod identity — default-deny, timeout-not-403
- `08-debugging.md` — the five-question method — which file to read first when it breaks
- `09-debugging-walkthrough.md` — the method applied to a real failure end to end
- supporting: `README` · `test-yourself` · `in-the-wild`; diagnose folded into `08/09-debugging`; capstone `../the-whole-stack.md`
- `cilium`/eBPF referenced. Deferred (roadmap): bpftrace capstone (the Act-1 promise lands here), Hubble.
