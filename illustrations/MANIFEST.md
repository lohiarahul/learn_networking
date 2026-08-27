# Manifest

83 illustrations. Every file is `320 × 240` SVG, self-contained, with no text inside
the artwork. The **Depicts** column is the file's own `aria-label` — usable as alt
text as-is.

## Fundamentals

`illustrations/01-fundamentals/` — 8 files

| Topic | File | Depicts |
| --- | --- | --- |
| OSI model | `osi-model.svg` | Seven stacked protocol layers with data descending the stack |
| TCP/IP model | `tcp-ip-model.svg` | Two four-layer stacks exchanging data over a shared link |
| Packets & frames | `packets-and-frames.svg` | A packet wrapped inside a frame with header and trailer |
| Bandwidth vs latency | `bandwidth-vs-latency.svg` | A wide pipe moving many packets versus a narrow slow one |
| Circuit vs packet switching | `circuit-vs-packet-switching.svg` | A dedicated circuit compared with packets taking separate paths |
| Analog vs digital signals | `analog-vs-digital-signals.svg` | A continuous analog wave above a discrete digital square wave |
| Network topologies (star/mesh/bus/ring) | `network-topologies.svg` | Four network shapes: star, mesh, bus and ring |
| LAN vs WAN vs MAN | `lan-vs-wan-vs-man.svg` | A local network, a metro network and a global cloud in scope order |

## Addressing

`illustrations/02-addressing/` — 10 files

| Topic | File | Depicts |
| --- | --- | --- |
| IPv4 basics | `ipv4-basics.svg` | A four part numeric address identifying a host on the network |
| IPv4 subnetting | `ipv4-subnetting.svg` | One address block divided into three smaller subnets |
| CIDR notation | `cidr-notation.svg` | An address bar with a prefix boundary and a bit-length ruler |
| Subnet masks | `subnet-masks.svg` | A mask of ones and zeros splitting an address into network and host |
| Private vs public IP | `private-vs-public-ip.svg` | Reusable inside addresses behind one globally routable address |
| IPv6 basics | `ipv6-basics.svg` | An eight group address, far larger than the four part one |
| IPv6 address types | `ipv6-address-types.svg` | Addresses that reach one host, many hosts, or the nearest host |
| MAC addresses | `mac-addresses.svg` | A hardware address fixed to a network interface card |
| ARP | `arp.svg` | A broadcast question about an address that one host answers |
| NAT | `nat.svg` | Several inside addresses translated to a single outside address |

## Switching & Layer 2

`illustrations/03-switching-layer2/` — 8 files

| Topic | File | Depicts |
| --- | --- | --- |
| Hubs vs switches vs bridges | `hubs-vs-switches-vs-bridges.svg` | A repeater, a forwarder, and a device joining two segments |
| VLANs | `vlans.svg` | One switch carrying two isolated groups of ports |
| Trunking (802.1Q) | `trunking-802-1q.svg` | A single link between switches carrying tagged frames from both groups |
| Spanning tree protocol | `spanning-tree-protocol.svg` | A wiring loop with one redundant link blocked to leave a tree |
| Switch MAC tables | `switch-mac-tables.svg` | A learned table mapping each hardware address to a switch port |
| Collision vs broadcast domains | `collision-vs-broadcast-domains.svg` | One shared collision domain beside two router-bounded broadcast domains |
| Port security | `port-security.svg` | A switch port that admits a known device and refuses an unknown one |
| Link aggregation | `link-aggregation.svg` | Parallel links bundled so they behave as one wider link |

## Routing & Layer 3

`illustrations/04-routing-layer3/` — 10 files

| Topic | File | Depicts |
| --- | --- | --- |
| Routers & routing tables | `routers-and-routing-tables.svg` | A router deciding each packet's next hop from its table |
| Static vs dynamic routing | `static-vs-dynamic-routing.svg` | A hand-placed route beside routers learning routes from each other |
| RIP | `rip.svg` | Routes chosen purely by counting the hops to the destination |
| OSPF | `ospf.svg` | Link costs across an area with the cheapest path highlighted |
| BGP | `bgp.svg` | Two separate networks peering to exchange reachability |
| Default gateway | `default-gateway.svg` | Every host sending unknown destinations to one exit router |
| Route summarization | `route-summarization.svg` | Several neighbouring blocks advertised as one larger block |
| Inter-VLAN routing | `inter-vlan-routing.svg` | Two port groups reaching each other only via the router above |
| Longest prefix match | `longest-prefix-match.svg` | Three matching routes with the most specific prefix chosen |
| Anycast/multicast | `anycast-and-multicast.svg` | One send reaching many receivers, and one address served by the nearest |

## Transport Layer

`illustrations/05-transport/` — 6 files

| Topic | File | Depicts |
| --- | --- | --- |
| TCP handshake | `tcp-handshake.svg` | Three messages exchanged to open a connection |
| TCP vs UDP | `tcp-vs-udp.svg` | An ordered acknowledged stream above an unacknowledged one |
| Ports & sockets | `ports-and-sockets.svg` | A host with several numbered ports, each holding one conversation |
| Flow control | `flow-control.svg` | A receiver advertising how much data it can still accept |
| Congestion control | `congestion-control.svg` | A sending rate that climbs, collapses on loss, and climbs again |
| Common port numbers | `common-port-numbers.svg` | A short table of well-known service ports |

## Core Services

`illustrations/06-core-services/` — 8 files

| Topic | File | Depicts |
| --- | --- | --- |
| DNS resolution | `dns-resolution.svg` | A name looked up by asking servers up the hierarchy |
| DNS record types | `dns-record-types.svg` | Several kinds of record answering the same kind of question |
| DHCP | `dhcp.svg` | A newly joined host handed its addressing settings |
| NTP | `ntp.svg` | Clients pulling the same time from an authoritative clock |
| Load balancing | `load-balancing.svg` | One front address spreading requests over several servers |
| Proxy servers | `proxy-servers.svg` | A middleman relaying every request on the client's behalf |
| Reverse proxy vs forward proxy | `reverse-proxy-vs-forward-proxy.svg` | A middleman in front of the clients, then one in front of the servers |
| CDNs | `cdns.svg` | Cached copies held at edge locations near the audience |

## Security

`illustrations/07-security/` — 12 files

| Topic | File | Depicts |
| --- | --- | --- |
| Firewalls (stateful/stateless) | `firewalls-stateful-vs-stateless.svg` | A wall judging each packet alone, then one judging it in context |
| ACLs | `acls.svg` | An ordered list of rules permitting or denying each packet |
| VPNs (site-to-site/remote) | `vpns.svg` | An encrypted tunnel between two sites, and one for a single user |
| TLS/SSL handshake | `tls-ssl-handshake.svg` | Keys and a certificate exchanged before the channel is locked |
| HTTPS | `https.svg` | A page fetched over a channel that is locked end to end |
| IPSec | `ipsec.svg` | A packet sealed inside a protected outer packet for transit |
| Zero trust networking | `zero-trust-networking.svg` | No trusted interior: every party authenticates for every request |
| Network segmentation | `network-segmentation.svg` | Separate zones with a checkpoint on every path between them |
| DDoS attacks | `ddos-attacks.svg` | A target swamped by traffic until real requests cannot land |
| Man-in-the-middle attacks | `man-in-the-middle-attacks.svg` | Traffic quietly rerouted through a third party who can read it |
| Port scanning | `port-scanning.svg` | Every port probed in turn to see which ones answer |
| IDS/IPS | `ids-ips.svg` | One sensor watching a copy of the traffic, one sitting in its path |

## Wireless

`illustrations/08-wireless/` — 6 files

| Topic | File | Depicts |
| --- | --- | --- |
| Wi-Fi standards (802.11) | `wifi-standards-802-11.svg` | Successive wireless generations, each carrying more than the last |
| SSID & channels | `ssid-and-channels.svg` | One network name broadcast in one of several radio channels |
| WPA2/WPA3 | `wpa2-wpa3.svg` | Two generations of wireless encryption, the newer one stronger |
| Wireless interference | `wireless-interference.svg` | Two radios overlapping on the same channel and colliding |
| Bluetooth vs Wi-Fi | `bluetooth-vs-wifi.svg` | A short device-to-device link beside a room-sized wireless link |
| Mesh Wi-Fi | `mesh-wifi.svg` | Several radios relaying to each other to cover one space |

## Cloud & Modern Networking

`illustrations/09-cloud-modern/` — 8 files

| Topic | File | Depicts |
| --- | --- | --- |
| Cloud VPCs | `cloud-vpcs.svg` | Private fenced networks running inside a shared cloud |
| Software-defined networking (SDN) | `software-defined-networking.svg` | Forwarding decisions taken by one controller above the switches |
| Containers & container networking | `containers-and-container-networking.svg` | Isolated containers sharing one host bridge to reach the network |
| Kubernetes networking | `kubernetes-networking.svg` | Short-lived pods reached through one stable service address |
| Edge computing | `edge-computing.svg` | Compute placed at the edge, close to the people using it |
| Network automation | `network-automation.svg` | One declared configuration applied identically to every device |
| API gateways | `api-gateways.svg` | One gateway fronting many services behind it |
| Service mesh | `service-mesh.svg` | Each service paired with a sidecar that handles its traffic |

## Containers & Kubernetes

`illustrations/10-containers-and-kubernetes/` — 6 files

| Topic | File | Depicts |
| --- | --- | --- |
| Network namespaces | `namespaces.svg` | One kernel holding two private network stacks that cannot see each other |
| cgroups | `cgroups.svg` | Namespace narrows what a process can see; cgroup caps how much it can use |
| VXLAN encapsulation | `vxlan-encap.svg` | An original packet carried whole as cargo inside a new outer packet through the tunnel |
| CNI across nodes | `cni-cross-node.svg` | Two nodes wiring pods identically, joined by one path between them |
| CoreDNS search list | `coredns-ndots.svg` | A bare name tried against each entry in a search list until one query resolves |
| Pod networking | `pod-networking.svg` | Several containers inside one pod sharing a single network namespace |

## Application Layer

`illustrations/11-application-layer/` — 1 file

| Topic | File | Depicts |
| --- | --- | --- |
| HTTP exchange | `http-exchange.svg` | A request and its response, each split by a blank line into headers and body |

## Notes for placement

- **Three list-shaped images look alike by nature:** `acls.svg`,
  `dns-record-types.svg` and `common-port-numbers.svg` are all tag-and-row tables,
  because all three topics *are* lists. They differ in tag colour and row count, but
  avoid putting two of them on the same page.
- **Contact sheets** for reviewing a whole category at once are in `_previews/`;
  `_previews/00-all-76.png` shows the entire set on one page.

## Where these are used

38 of 83 illustrations are placed on 27 lesson pages. This table is
generated from the lessons themselves (`grep` for `illustrations/` in `networking-fundamentals/`),
so it cannot drift from what is actually on the pages.

| Illustration | Used on |
| --- | --- |
| `01-fundamentals/bandwidth-vs-latency.svg` | `your-own-machine.md` |
| `01-fundamentals/packets-and-frames.svg` | `act-2-two-machines/03b-mtu-and-fragmentation.md` |
| `02-addressing/arp.svg` | `act-2-two-machines/01-ethernet-and-arp.md` |
| `02-addressing/ipv4-subnetting.svg` | `act-2-two-machines/02-ip-and-routing.md` |
| `02-addressing/mac-addresses.svg` | `act-2-two-machines/01-ethernet-and-arp.md` |
| `02-addressing/nat.svg` | `act-4-one-pretends-many/03-iptables-and-nat.md` |
| `02-addressing/private-vs-public-ip.svg` | `act-4-one-pretends-many/03-iptables-and-nat.md` |
| `03-switching-layer2/collision-vs-broadcast-domains.svg` | `act-2-two-machines/01b-vlans-and-segmentation.md` |
| `03-switching-layer2/switch-mac-tables.svg` | `act-4-one-pretends-many/02-veth-and-bridge.md` |
| `03-switching-layer2/vlans.svg` | `act-2-two-machines/01b-vlans-and-segmentation.md` |
| `04-routing-layer3/anycast-and-multicast.svg` | `your-own-machine.md` |
| `04-routing-layer3/bgp.svg` | `act-2-two-machines/02b-routing-and-bgp.md` |
| `04-routing-layer3/routers-and-routing-tables.svg` | `act-2-two-machines/02-ip-and-routing.md` |
| `05-transport/congestion-control.svg` | `act-3-the-internet/03-tcp-reliability.md` |
| `05-transport/flow-control.svg` | `act-3-the-internet/03-tcp-reliability.md` |
| `05-transport/ports-and-sockets.svg` | `act-1-one-machine/05-ports-and-proc-net-tcp.md` |
| `05-transport/tcp-handshake.svg` | `act-3-the-internet/01-tcp-handshake.md` |
| `05-transport/tcp-vs-udp.svg` | `act-2-two-machines/03-icmp-and-udp.md` |
| `06-core-services/dhcp.svg` | `act-2-two-machines/03c-dhcp.md` |
| `06-core-services/dns-record-types.svg` | `act-2-two-machines/04-dns.md` |
| `06-core-services/dns-resolution.svg` | `act-2-two-machines/04-dns.md` |
| `06-core-services/load-balancing.svg` | `act-5-kubernetes/03-services.md` |
| `06-core-services/reverse-proxy-vs-forward-proxy.svg` | `act-5-kubernetes/06-ingress.md` |
| `07-security/firewalls-stateful-vs-stateless.svg` | `act-3-the-internet/02b-conntrack.md` |
| `07-security/https.svg` | `act-3-the-internet/05-tls.md` |
| `07-security/port-scanning.svg` | `act-1-one-machine/05b-tcp-states-and-the-syn-scan.md` |
| `07-security/tls-ssl-handshake.svg` | `act-3-the-internet/05-tls.md` |
| `07-security/zero-trust-networking.svg` | `act-5-kubernetes/07-network-policy.md` |
| `09-cloud-modern/api-gateways.svg` | `act-5-kubernetes/06-ingress.md` |
| `09-cloud-modern/containers-and-container-networking.svg` | `act-4-one-pretends-many/02-veth-and-bridge.md` |
| `09-cloud-modern/kubernetes-networking.svg` | `act-5-kubernetes/03-services.md` |
| `10-containers-and-kubernetes/namespaces.svg` | `act-4-one-pretends-many/01-namespaces.md` |
| `10-containers-and-kubernetes/cgroups.svg` | `act-4-one-pretends-many/01b-cgroups.md` |
| `10-containers-and-kubernetes/vxlan-encap.svg` | `act-4-one-pretends-many/04-overlay-vxlan.md` |
| `10-containers-and-kubernetes/cni-cross-node.svg` | `act-5-kubernetes/05-cni.md` |
| `10-containers-and-kubernetes/coredns-ndots.svg` | `act-5-kubernetes/04-coredns.md` |
| `10-containers-and-kubernetes/pod-networking.svg` | `act-5-kubernetes/02-pod-networking.md` |
| `11-application-layer/http-exchange.svg` | `act-3-the-internet/04-http.md` |

These 7 were added specifically to close the inverse gap: topics the course
genuinely teaches (Act IV/V kernel and Kubernetes internals, plus HTTP) that fell
outside the original 76-topic taxonomy and so had no illustration at all, even
though 1-2 lessons per topic already carried a hand-drawn ASCII diagram doing the
detailed work. These spot illustrations sit beside those ASCII diagrams, not in
place of them.

## Not placed

> **This list is now gated.** `tools/check_pedagogy.py::check_illustration_placement` asserts it in
> both directions on every run: nothing named below may actually be in use by a lesson, and nothing
> unreferenced may be missing from below. Place an illustration and forget to delete its line here and
> the check says so. A hand-written inventory of what is unused is worth having only if it cannot go
> quietly stale, which this one previously could.
>
> **`AUDIT.md` §F recommended deleting or annexing these 45. That was declined.** They are
> deterministic output of the generator in `_build/`, which the 38 placed images need anyway, so
> deleting the SVGs removes no build step and saves no maintenance; and the only page that serves them
> is a `noindex` contributor gallery, so they cost a learner nothing. The audit scored them as
> "ongoing maintenance for zero learner contact" — the maintenance was the risk of this list drifting,
> and that is now a check rather than a deletion.

The remaining 45 of the original 76 are built and served (visit `/illustrations/`) but sit on no
lesson, because the course does not teach those topics. 21 of them are not mentioned anywhere in the
course prose at all — the whole wireless category, spanning tree, RIP, route summarisation, ACLs,
IPsec, DDoS, SDN, edge computing, network automation, CDNs, network topologies, analog vs digital,
circuit vs packet switching, inter-VLAN routing and IPv6 address types.

The rest are mentioned only in passing, which is not the same as being taught: `proxy-servers` looks
like a match for `act-5-kubernetes/03-services.md` only because that page says *kube-proxy* 26 times,
and kube-proxy is not a proxy server. Placing on a keyword would contradict the page.

Use them as you write the lessons that need them:

- `01-fundamentals/analog-vs-digital-signals.svg`
- `01-fundamentals/circuit-vs-packet-switching.svg`
- `01-fundamentals/lan-vs-wan-vs-man.svg`
- `01-fundamentals/network-topologies.svg`
- `01-fundamentals/osi-model.svg`
- `01-fundamentals/tcp-ip-model.svg`
- `02-addressing/cidr-notation.svg`
- `02-addressing/ipv4-basics.svg`
- `02-addressing/ipv6-address-types.svg`
- `02-addressing/ipv6-basics.svg`
- `02-addressing/subnet-masks.svg`
- `03-switching-layer2/hubs-vs-switches-vs-bridges.svg`
- `03-switching-layer2/link-aggregation.svg`
- `03-switching-layer2/port-security.svg`
- `03-switching-layer2/spanning-tree-protocol.svg`
- `03-switching-layer2/trunking-802-1q.svg`
- `04-routing-layer3/default-gateway.svg`
- `04-routing-layer3/inter-vlan-routing.svg`
- `04-routing-layer3/longest-prefix-match.svg`
- `04-routing-layer3/ospf.svg`
- `04-routing-layer3/rip.svg`
- `04-routing-layer3/route-summarization.svg`
- `04-routing-layer3/static-vs-dynamic-routing.svg`
- `05-transport/common-port-numbers.svg`
- `06-core-services/cdns.svg`
- `06-core-services/ntp.svg`
- `06-core-services/proxy-servers.svg`
- `07-security/acls.svg`
- `07-security/ddos-attacks.svg`
- `07-security/ids-ips.svg`
- `07-security/ipsec.svg`
- `07-security/man-in-the-middle-attacks.svg`
- `07-security/network-segmentation.svg`
- `07-security/vpns.svg`
- `08-wireless/bluetooth-vs-wifi.svg`
- `08-wireless/mesh-wifi.svg`
- `08-wireless/ssid-and-channels.svg`
- `08-wireless/wifi-standards-802-11.svg`
- `08-wireless/wireless-interference.svg`
- `08-wireless/wpa2-wpa3.svg`
- `09-cloud-modern/cloud-vpcs.svg`
- `09-cloud-modern/edge-computing.svg`
- `09-cloud-modern/network-automation.svg`
- `09-cloud-modern/service-mesh.svg`
- `09-cloud-modern/software-defined-networking.svg`
