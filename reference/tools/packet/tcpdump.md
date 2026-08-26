# `tcpdump` — TCP dump

Bytes actually on the wire, with a compositional filter language and `-w` to a `.pcap` you can open elsewhere

| | |
|---|---|
| **Speaks** | [`packet`](README.md) · flags + *libpcap filter* |
| **Mode** | live |
| **Taught in** | [ICMP and UDP](../../../networking-fundamentals/act-2-two-machines/03-icmp-and-udp.md) |
| **In the lab** | ✅ `/usr/bin/tcpdump` · tcpdump version 4.99.6 |
| **Blind spot** | `packet` cannot tell you which process or rule was responsible. It sees bytes on a link, not the host state behind them — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## The flags that carry their weight

*Not the flag list — `tcpdump --help` has that. These 4 change what the tool can **see**.*

| Flag | What it changes |
|---|---|
| `-nn` | resolve neither host nor **port** names. Single `-n` is hosts only. Resolution also generates traffic into your own capture, and stalls on a dead resolver |
| `-i <dev>` | which link you are watching. `-i any` sees all of them but loses the link-layer header — a different observation, not a wider one |
| `-e` | the link-layer header, so MAC addresses and VLAN tags appear at all |
| `-v` | TTL, IP id and flags. Absent by default, and TTL is how you count the hops a packet has already taken |

## What it can do

*12 commands, grouped by what you are trying to find out.*

### Capture

| Command | What it gives you |
|---|---|
| `tcpdump -i <dev> -nn` | no name or port resolution — always start here |
| `tcpdump -i any -nn` | every interface at once |
| `tcpdump -i <dev> -w cap.pcap` | to a file you can open in Wireshark |
| `tcpdump -r cap.pcap -nn` | read it back |
| `tcpdump -i <dev> -c 100 -s 0` | stop after 100 packets; full payload |

### The filter language — compositional, not grep

| Command | What it gives you |
|---|---|
| `tcpdump -nn 'tcp port 443'` | host, net, port, and the protocol keywords |
| `tcpdump -nn 'host 10.0.0.1 and not port 22'` | and / or / not |
| `tcpdump -nn 'tcp[tcpflags] & tcp-syn != 0'` | byte-level: SYNs only |
| `tcpdump -nn 'icmp[icmptype] == icmp-unreach'` | the fragmentation-needed message MTU bugs hide in |

### Read the packet

| Command | What it gives you |
|---|---|
| `tcpdump -nn -v` | TTL, id and flags |
| `tcpdump -nn -X` | hex and ASCII payload |
| `tcpdump -nn -e` | Ethernet headers, so you see MACs and VLAN tags |

## As the course runs it

*5 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `tcpdump -nn -i any icmp` | `-nn` = resolve neither hostnames nor **port names** (single `-n` is hosts only); `-i any` = every interface; `icmp` = the filter expression. opt: `-c 5` stop after 5, `-w f.pcap` write a capture file | Lesson 3 — ICMP, UDP, and TTL |
| `tcpdump -nn -i eth0 udp port 9999` | `udp port 9999` composes protocol + type + value from libpcap's filter grammar | Lesson 3 — ICMP, UDP, and TTL |
| `tcpdump -i eth0 -n -v port 67 or port 68` | `or` composes two filter primitives; 67 is the server, 68 the client; `-v` prints the option fields, which is where the interesting content is | Lesson 3c — DHCP |
| `tcpdump -i any -nn tcp port 8080` | capture both directions of one port. You will see exactly three packets before any data: `[S]`, `[S.]`, `[.]` | Lesson 1 — The three-way handshake |
| `tcpdump -ni vu2 -c 4 udp port 4789` | the **outer** packets. Your ICMP is now cargo inside UDP — the encapsulation, visible | Lesson 4 — Overlay and VXLAN |
