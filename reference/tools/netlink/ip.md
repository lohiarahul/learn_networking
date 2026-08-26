# `ip` — internet protocol utility

Everything netlink's route family knows: links, addresses, routes, neighbours, rules, namespaces. `-j` gives it to you as JSON

| | |
|---|---|
| **Speaks** | [`netlink`](README.md) · obj-verb, 30 objects |
| **Mode** | mutate · live |
| **Taught in** | [ethernet and ARP](../../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| **In the lab** | ✅ `/sbin/ip` · ip utility, iproute2-6.18.0 |
| **Supersedes** | ✅ **prefer this one** over [`arp`](../procfs/arp.md) (as `ip neigh`) |
| **Blind spot** | `netlink` cannot tell you what a packet *did*. It reports configured and tracked state, never a packet's path — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `ip --help` has that. These 3 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-d` | the interface **kind** — `veth`, `bridge`, `vxlan`, `bond`. Without it every one of them is a device with a MAC and the topology is invisible |
| `-s` | counters: packets, errors, drops, overruns. `ip -s link` is where a cable or a driver problem becomes a number |
| `-n <ns>` | run it in another network namespace without entering one — the whole of `ip netns exec <ns> ip …` in three characters |

## What it can do

*26 commands, grouped by what you are trying to find out.*

### Links — interfaces and their state

| Command | What it gives you |
|---|---|
| `ip link show` | every interface: index, MAC, MTU, flags, oper state |
| `ip -d link show <dev>` | -d adds the kind: veth, bridge, vxlan, dummy, bond |
| `ip link add v0 type veth peer name v1` | create a virtual cable — both ends at once |
| `ip link set <dev> up \| mtu 1400 \| master br0` | bring up, resize, enslave to a bridge |
| `ip link set <dev> netns blue` | move an interface into another namespace — it vanishes from here |

### Addresses

| Command | What it gives you |
|---|---|
| `ip addr show` | every address on every interface, with scope and lifetime |
| `ip -br addr` | one line per interface — the form you actually read |
| `ip addr add 10.0.0.1/24 dev <dev>` | fails with EEXIST if it is already there |
| `ip addr replace 10.0.0.1/24 dev <dev>` | same end state either way — the idempotent form |
| `ip addr flush dev <dev>` | remove all of them |

### Routes — how the kernel picks an exit

| Command | What it gives you |
|---|---|
| `ip route show` | the main table |
| `ip route get 8.8.8.8` | the decision for one destination: which route, source and device |
| `ip route add 10.2.0.0/24 via 10.0.0.2 dev <dev>` | a static route |
| `ip route show table all` | every table, not just main — where policy routing hides |
| `ip route add default via <gw> metric 200` | a second default, lower priority |

### Neighbours — the ARP/NDP cache

| Command | What it gives you |
|---|---|
| `ip neigh show` | IP to MAC, with state: REACHABLE, STALE, FAILED |
| `ip neigh del <ip> dev <dev>` | force the next packet to re-ARP — the standard poke |
| `ip neigh add <ip> lladdr <mac> dev <dev> nud permanent` | a static entry |

### Policy routing — more than one table

| Command | What it gives you |
|---|---|
| `ip rule show` | which table is consulted for which traffic, in priority order |
| `ip rule add from 10.0.0.5 table 100` | source-based routing, the basis of multi-homing |

### Watch it change

| Command | What it gives you |
|---|---|
| `ip monitor` | stream every netlink event: links, addresses, routes, neighbours |
| `ip monitor route` | route changes only — catches a flap you could never poll fast enough for |

### Output options that work on every object

| Command | What it gives you |
|---|---|
| `ip -j -p link show` | JSON, pretty-printed — then jq, instead of guessing at awk |
| `ip -6 route show` | restrict to one address family |
| `ip -s link show <dev>` | counters; -s -s gives more again |
| `ip -n blue addr` | run the whole command inside namespace blue |

## As the course runs it

*33 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `ip addr show lo` | `ip` = the iproute2 tool; `addr` = the **object** (addresses); `show` = the **verb**; `lo` = which device. opt: `ip a` short form, `ip -br addr` one line per device | Lesson 4 — The loopback interface |
| `ip addr show eth0` | the same for the real NIC. opt: `-4` to drop the IPv6 lines | Lesson 4 — The loopback interface |
| `ip -4 addr show lo \\| grep inet` | `-4` = IPv4 only, so the output is one line worth reading | Lesson 5 — Ports and /proc/net/tcp |
| `ip -s link show eth0` | `-s` = statistics. opt: `-s -s` **stacks** for per-error-type detail | Lesson 1 — The wire and the two names |
| `ip -4 addr show eth0` | your address and its prefix length, IPv4 only | Lesson 1 — The wire and the two names |
| `ip route get 8.8.8.8 \\| awk '{print $3}'` | field 3 of `ip route get`'s answer is the gateway. Note **why this and not `ip route show default`**: `show` reads only the `main` table, and on some hosts — Docker Desktop's VM among them — the default route lives in a separate policy-routing table (`ip rule show` reveals it). `ip route get <dst>` asks which route the kernel would *actually* use, so it finds the gateway whichever table holds it | Lesson 1 — The wire and the two names |
| `ip neigh flush dev eth0` | `neigh` = the neighbour object; `flush` = empty it; `dev eth0` = scoped to one device. Makes the next ping re-ARP so you can watch it happen | Lesson 1 — The wire and the two names |
| `ip neigh` | the replacement. With no verb, `show` is implied — true for most `ip` objects | Lesson 1 — The wire and the two names |
| `ip link add link eth0 name eth0.10 type vlan id 10` | `link add` = create a device; the inner `link eth0` = its **parent**; `name` = what to call it; `type vlan` picks the kind; `id 10` = the 12-bit VLAN tag. The `.10` naming is convention, not a requirement | Lesson 1b — VLANs and segmentation |
| `ip -d link show eth0.10` | `-d` = details, which is what reveals `vlan protocol 802.1Q id 10`. Without `-d` the VLAN-ness is invisible | Lesson 1b — VLANs and segmentation |
| `ip route show default` | just the catch-all route | Lesson 2 — IP and routing |
| `ip route get 8.8.8.8` | **the decision, not the table.** Asks the kernel "which route would you use, out which device, from which source address" — the single most useful routing command | Lesson 2 — IP and routing |
| `ip route get 127.0.0.1` | the same for loopback, which resolves via a different table entirely | Lesson 2 — IP and routing |
| `ip route show` | note the `proto` word on the rows that have one: who installed this route — `kernel`, `static`, `bgp`, `dhcp`. A route added with no explicit origin is `boot`, and iproute2 prints **nothing** for it — which is why the default route, the first row everyone reads, usually has no `proto` at all | Lesson 2b — Routing protocols and BGP |
| `ip route add 203.0.113.0/24 dev eth0 proto bgp` | `add` = the verb; `dev eth0` = out which device; `proto bgp` **labels** the origin. Nothing verifies the label — you're pretending a daemon did it | Lesson 2b — Routing protocols and BGP |
| `ip route show proto bgp` | filter by origin. Any field on the route object can usually be used as a filter | Lesson 2b — Routing protocols and BGP |
| `ip route add blackhole 208.65.153.0/24` | `blackhole` = a route that silently discards. The BGP hijack, reproduced: a more specific prefix wins over a less specific one regardless of who announced it | Lesson 2b — Routing protocols and BGP |
| `ip route get 208.65.153.10` | which of the two competing routes wins, decided by prefix length. **Expect an error:** when the blackhole wins, this prints `RTNETLINK answers: Invalid argument` and exits 2. That error *is* the answer — the kernel chose the route that discards. Compare an address inside the wider prefix but outside the hijacked one, which still resolves normally | Lesson 2b — Routing protocols and BGP |
| `ip route del <prefix>` | `del` — and note you do **not** repeat the `dev`/`proto` attributes to delete | Lesson 2b — Routing protocols and BGP |
| `ip link set eth0 mtu 1500` | **do this first.** The pair below assumes a 1500-byte path, and on Docker Desktop `eth0` comes up at MTU 65535, where both sizes succeed and the lesson silently does not happen | Lesson 3b — MTU and fragmentation |
| `ip link add veth0 type veth peer name veth1` | `type veth` = a virtual Ethernet **pair**; `peer name` names the other end. Always two, like the two plugs of one cable | Lesson 2 — veth and bridge |
| `ip link set veth1 netns ns1` | `set` = the verb; `netns <name>` moves the device **into** a namespace. It vanishes from the host's `ip link` — a device belongs to exactly one namespace | Lesson 2 — veth and bridge |
| `ip addr add 10.10.0.1/24 dev veth0` | adds the address, and the kernel installs the directly-connected route for the whole `/24` **when the interface comes up** — `proto kernel`, because you did not write it. That route, not any `ip route` command, is what makes the first ping work. Check `ip route` straight after this line and you will see nothing: bring the link up and it appears, carrying `linkdown` until the peer is up too | Lesson 2 — veth and bridge |
| `ip link set veth0 up` | interfaces start administratively down. Both ends must be up | Lesson 2 — veth and bridge |
| `ip link add br0 type bridge` | a software switch | Lesson 2 — veth and bridge |
| `ip link set veth-a master br0` | `master` = enslave this device to that bridge — the equivalent of plugging a cable into a switch port. Visible afterwards as `/sys/class/net/br0/brif/veth-a` | Lesson 2 — veth and bridge |
| `ip link del veth-a` | deleting one end deletes the pair, including the end inside a namespace | Lesson 2 — veth and bridge |
| `ip link show docker0` | the bridge Docker created for you: exactly lesson 2's `br0`, under a different name | Lesson 3 — iptables and NAT |
| `ip link add vxlan0 type vxlan id 42 local 172.31.0.1 remote 172.31.0.2 dstport 4789 dev vu1` | `type vxlan`; `id 42` = the VNI, the tenant identifier; `local`/`remote` = the **underlay** endpoints; `dstport 4789` = the standard VXLAN UDP port (Flannel uses 8472); `dev` = which device carries the outer packet | Lesson 4 — Overlay and VXLAN |
| `ip -d link show vxlan0` | `-d` again: without it, none of the `vxlan id 42 local … remote …` detail prints | Lesson 4 — Overlay and VXLAN |
| `ip link set vu2 mtu 1400` | shrink the underlay MTU to break the overlay — the failure every real overlay eventually hits | Lesson 4 — Overlay and VXLAN |
| `ip -s link show vu2` | the RX `dropped` counter climbing with each large ping. **The evidence that a silent drop is happening**, and where to look for it | Lesson 4 — Overlay and VXLAN |
| `ip link set vxlan0 mtu 1350` | the fix: the overlay MTU must leave room for the outer headers. 1400 − 50 for VXLAN = 1350 | Lesson 4 — Overlay and VXLAN |
