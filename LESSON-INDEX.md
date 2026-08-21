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

## Act 6 — the control plane  ⟨all 8 lessons written; 01–04 cluster-verified, 05–08 unverified; no supporting files yet⟩
- `01-the-api-server-is-a-filesystem.md` — a Pod is not on the node's disk — Act-I creed's next form; `kubectl get --raw`, `/registry/<kind>/<ns>/<name>` in etcd, protobuf-vs-YAML rendering, `etcdctl` mTLS via `/etc/kubernetes/pki/etcd/`, **`etcdctl watch` while you label** (writes you didn't make)
- `02-static-pods.md` — the boot-order paradox — kubelet as the one non-Pod; `staticPodPath`, `/etc/kubernetes/manifests/`, **`kubectl delete` on a static Pod is a no-op**, stop a component by moving its file, etcd's `hostPath` as the only durable bytes
- `03-the-reconciliation-loop.md` — stop a watcher, watch intent go inert — controller-manager down → two Pods but **`READY 3/3` forever, because `status` is a stored note the same controller writes** (so `kubectl wait` believes it); scheduler down → `Pending`, empty `spec.nodeName`, `Events: <none>`; leader election as the restore delay; three loops, zero calls; "current state is the entire input"
- `04-the-clusters-own-pki.md` — your identity is a file — `CN`=username / `O`=group / issuer=trust, `openssl x509` on your own kubeconfig (`O=kubeadm:cluster-admins`, **not** the pre-2024 `system:masters`, which now lives only in `super-admin.conf` and skips the permission check), `ca.key` = unrevokable ownership, three CAs (`ca`/`etcd-ca`/`front-proxy-ca`) meeting at `apiserver-etcd-client`, CSR objects as a control loop → `O=system:nodes` kubelet cert, `kubeadm certs check-expiration` proven to work **with the API server stopped** + why renewal alone doesn't fix it
- `05-etcd-backup-and-restore.md` — the one component nothing else can rebuild — `etcdctl snapshot save` (client, certs, **must write inside the `hostPath` or it "succeeds" into a dying container**) vs `etcdutl status`/`restore` (utility, no certs — etcd 3.6 split the binaries on exactly that line, and `etcdctl snapshot status` now prints help and **exits 0**); **neither binary is on the node** — they ship in the etcd image, so `kubectl exec` while etcd is up and `docker run` on your own machine when it is down; verify by TOTAL KEYS vs your own `/registry` count; **`grep -a hunter2 backup.db` → plaintext, not even base64**; then **delete `/var/lib/etcd` for real**: etcd bootstraps empty and healthy, and `kubectl` answers **`Forbidden`, not disconnected** (authn is a file on disk; the `ClusterRoleBinding` was in the store) while `super-admin.conf` still works — nodes gone and **do not re-register** (a kubelet registers once, at startup, then only `UPDATE`s), yet `crictl ps` shows nine containers still serving; restore on the host → `docker cp` in → stop all four manifests → swap dir; **a restore is an assertion, not a rewind** — the revision goes *backwards*, so the post-snapshot workload keeps **serving traffic** with no object anywhere until `systemctl restart kubelet` forces a fresh list
- `06-upgrades-and-version-skew.md` — skew derived, not memorised — no component talks to a *peer*, so skew is "does this server still serve the API this client was built against?"; the API server is the reference because it is the only one holding `apiserver-etcd-client` (Act VI-04); why `kubectl` may be newer when a controller may not (it discovers, and a human is watching); the window is **a deadline, not a resting place** (3 minors ≈ a year at 4 months/release); **do half an upgrade by hand** — retag `kube-scheduler` to `v9.99.99`, watch it fail, roll back; a version lives in 4 manifest `image:` strings vs the kubelet's installed package; `kubeadm upgrade plan`/`apply`/`node` and what they do *not* do; in-place upgrade honestly out of reach in `kind`
- `07-node-maintenance.md` — the first operation the cluster may refuse — `cordon` = **one field** (`spec.unschedulable`) + a taint, provable by reproducing it with a bare `kubectl patch`; distinguished from the control plane's *permanent* `NoSchedule` taint, read off the object; **`drain` is a client-side loop in your terminal** — *shown*, via `--dry-run=client` (one line per Pod) then `-v=6` (**one `POST` to `pods/<name>/eviction` each**) — so no object, no controller, and Ctrl-C leaves it half-done forever because nothing knew there was a job; `--ignore-daemonsets` (DaemonSet named via Act V's kube-proxy) + `--delete-emptydir-data` as *acknowledgements*; drain deletes, loops recreate — the reader's own Pods go `Pending` with nowhere to go; **eviction ≠ deletion**, the one write refusable on policy → **PodDisruptionBudget** (governs *voluntary* disruption only; refusal looks like slowness, so always `--timeout`)
- `08-when-the-control-plane-breaks.md` — Act V's five questions turned down the **dependency** stack (each needs less of the cluster than the last, so the descent always reaches ground) — `/readyz?verbose`, events as "a loop that tried says so; a loop that isn't running says nothing", `logs --previous` vs `ImagePullBackOff` (no logs, ever); **and the opposite stopping rule to Act V's** — stop at the first tool that *answers*, not the first that lies; **the signature drill: one manifest broken at three depths, discriminated by how far down the stack it got** — bad *flag* → sandbox `Ready` + container `Exited`, `crictl logs` "unknown flag" (`CrashLoopBackOff`); missing *image* → sandbox `Ready` but **no container** (so `crictl pods` alone says "fine"), journal shows the pull (`ImagePullBackOff`, hence no logs, ever); unparseable *YAML* → **not even a sandbox**, journal names the file and line; only the middle case is readable with `crictl logs`, which is the argument for Question 4; **empty output is a pointer downward, not an absence of information**; the three that break everything at once (missing manifest, expired certs, full disk → `etcdctl alarm list`, which prints *nothing at all* when healthy, + `endpoint status`; `NOSPACE` = reads fine and every write fails)

## Act 5 — kubernetes  ⟨complete⟩
- `01-lab-with-kind.md` — the real cluster — `kind`, `kubectl`, node via `docker exec` vs netshoot Pod
- `02-pod-networking.md` — a Pod = Act-4 netns held by the pause container — shared netns, `nsenter`
- `03-services.md` — what answers to a ClusterIP (Act-4 DNAT + conntrack) — `KUBE-SERVICES`/`SVC`/`SEP` chains, EndpointSlice + readiness, the iptables-scaling → IPVS → eBPF arc, NodePort/LoadBalancer
- `04-coredns.md` — Act-2 DNS scaled to the cluster — `/etc/resolv.conf`, search domains, `dig` in-Pod
- `04b-service-shapes.md` — when a load-balanced VIP is wrong — `clusterIP: None` (headless: N A-records **and** zero `KUBE-SVC` chains), per-Pod DNS `<pod>.<svc>.<ns>`, **SRV** on named ports, `sessionAffinity: ClientIP` (conntrack again; coarse behind NAT), `type: ExternalName` (CNAME, no endpoints, invisible to NetworkPolicy), `externalTrafficPolicy: Local` vs `Cluster` (source IP vs off-node blackhole)
- `05-cni.md` — the veth-pair installer (Act-4 wiring, run by a binary) — CNI contract, IPAM, Pod routes
- `06-ingress.md` — Act-3 TLS terminated at the edge — Host-header routing, one IP many hosts
- `06b-gateway-api.md` — the annotation wall → a real `weight` field — `GatewayClass`/`Gateway`/`HTTPRoute`, `parentRefs` + `allowedRoutes` (mutual consent), `kubectl explain` as the schema authority, `.status` conditions `Programmed`/`Accepted`/`ResolvedRefs`, `NoMatchingListenerHostname`, weighted canary (weights ≠ percentages), CRDs, **`reconciliation` named here** (from kube-proxy + the ingress controller); **the unreconciled-object trap planted here, cashed in `07`**
- `07-network-policy.md` — iptables allow/deny on Pod identity — default-deny, timeout-not-403
- `08-debugging.md` — the five-question method — which file to read first when it breaks
- `09-debugging-walkthrough.md` — the method applied to a real failure end to end
- supporting: `README` · `test-yourself` · `in-the-wild`; diagnose folded into `08/09-debugging`; capstone `../the-whole-stack.md`
- `cilium`/eBPF referenced. Deferred (roadmap): bpftrace capstone (the Act-1 promise lands here), Hubble.
