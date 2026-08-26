# `scapy`

Packets you *construct*: become the protocol instead of watching it. The active counterpart to `tcpdump`

| | |
|---|---|
| **Speaks** | [`packet`](README.md) · Python library |
| **Mode** | mutate · live |
| **Taught in** | [ethernet and ARP](../../../networking-fundamentals/act-2-two-machines/01-ethernet-and-arp.md) |
| **In the lab** | ✅ `/usr/bin/scapy` |
| **Blind spot** | `packet` cannot tell you which process or rule was responsible. It sees bytes on a link, not the host state behind them — a property of the [interface](README.md), not of this tool |
| **Also here** | [the roster](../README.md) · [by question](../../04-by-question.md) |

## What it can do

*4 commands, grouped by what you are trying to find out.*

### Construct packets instead of watching them

| Command | What it gives you |
|---|---|
| `sr1(IP(dst='10.0.0.1')/ICMP())` | send one, get one reply |
| `Ether()/ARP(op=2, psrc='10.0.0.1', hwsrc='de:ad:be:ef:00:01')` | a forged ARP reply — how you demonstrate spoofing |
| `sniff(iface='eth0', count=10)` | capture, as a Python list of objects |
| `IP(dst='10.0.0.1', flags='DF')/TCP()/('x'*2000)` | oversized with DF set — reproduce a black-hole MTU |

## As the course runs it

*6 commands this course actually runs, taken apart. The breakdowns are hand-written.*

| Command | Syntax breakdown | Lesson |
|---|---|---|
| `watch -n1 cat /proc/net/arp` | `watch` re-runs a command; `-n1` every second. The neighbour cache filling in, live | Lesson 1 — The wire and the two names |
| `scapy` | starts the interactive packet-crafting shell | Lesson 1 — The wire and the two names |
| `req = Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(op=1, pdst="<gateway>")` | `/` stacks layers outward-in; `ff:…:ff` = broadcast; `op=1` = request (`2` = reply); `pdst` = the address you're asking about | Lesson 1 — The wire and the two names |
| `req.show()` | print every field, including the ones scapy filled in for you. The habit that stops this being paste-and-run | Lesson 1 — The wire and the two names |
| `reply = srp1(req, iface="eth0", timeout=2)` | `srp1` = **s**end and **r**eceive at layer 2 (**p**acket), return the **1**st reply; `timeout=2` so it gives up | Lesson 1 — The wire and the two names |
| `reply[ARP].hwsrc` | index into the ARP layer of the reply; `hwsrc` = the hardware address of whoever answered | Lesson 1 — The wire and the two names |
