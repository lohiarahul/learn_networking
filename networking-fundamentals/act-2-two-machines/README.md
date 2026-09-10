# Act II — Two machines on one wire

On the night of October 29, 1969, a student programmer named Charley Kline sat at a terminal at UCLA, connected over a 50-kilobit-per-second leased line to a machine at the Stanford Research Institute, about to send the first message between two computers on the ARPAnet. The plan was to log in to the Stanford machine by typing `LOGIN`. He typed `L`. He typed `O`. Stanford received both and echoed them back. He typed `G` — and the receiving machine crashed.

The first message ever sent across the network that became the internet was the two characters `LO`, and the first networking event ever recorded was the crash that interrupted it. Networking began, fittingly, with a bug report. Kline's log of the session — the time, the characters, the failure — is the oldest surviving artifact of the thing this entire course is about. Two machines, one wire, and the immediate discovery that making `write()` on one become `read()` on the other is harder than it looks.

This act puts the wire back. In Act I a machine talked to itself, and every hard problem was hidden because the same kernel sat on both ends. Now there are two kernels, two cards, and a gap between them that no single kernel can reach across.

We will work up from the metal. First the **wire itself**, which does not understand IP addresses at all — it understands Ethernet frames addressed by hardware MAC addresses, and you will learn that there are two completely different naming systems stacked on top of each other and a protocol whose only job is to translate between them: **ARP**, which shouts "who has this IP?" across the wire and caches the answer. Because that shared wire floods every broadcast to everyone, you will then slice it into isolated virtual wires with **VLANs**, a 12-bit tag that turns one switch into many.

Then **IP**, the 32-bit integer that lets a packet cross from one network to another, and the routing table that decides where each packet goes by longest-prefix match — followed by **BGP**, the protocol that fills those tables across the whole internet by having networks announce what they can reach. Then the small protocols that ride on IP and make it usable: **ICMP**, the network's own error-reporting channel; **UDP**, IP with a port number bolted on and nothing else; and **TTL**, the countdown that keeps a misrouted packet from circling forever.

With those in hand you meet two hard facts of a real wire: **MTU and fragmentation**, what happens when a packet is too big for the next link, and **DHCP**, how a machine that has never spoken gets an address at all. And finally **DNS**, the distributed database that lets a human type a name instead of memorizing a 32-bit integer.

After this act you will be able to take any name a program wants to reach and trace it all the way down to a frame on the wire: name to IP through DNS, IP to a route through the routing table, IP to a MAC through ARP, MAC into a frame onto the wire. You will be able to read the raw kernel files behind every step and decode them by hand, and subnet a network on paper. You will also be carrying a short list of questions you cannot yet answer — one per lesson — that are exactly the questions a Kubernetes cluster turns out to be an answer to.

## The lab for this act

Act I ended in the **`netlab`** image (netshoot plus a C compiler), on Docker's default *bridge* network — all you needed for a machine talking to itself. Act II has to watch a *real* network — ARP neighbours, a routing table, a live DHCP server — so from here we switch back to plain **`nicolaka/netshoot`** with **`--network host`**, which attaches the container to the host's own network instead of an isolated bridge:

```bash
docker run --rm -it --privileged --network host --name lab nicolaka/netshoot
```

The `--name lab` matters. Several lessons need a **second shell** into the same container, and that shell is `docker exec -it lab zsh` — exactly as in Act I. No compiler is needed here, and every tool this act uses — `ip`, `arp`, `tcpdump`, `scapy`, `dig`, `nmap` — already ships in netshoot, so each lesson opens with that one line and goes.

### Read this before the first experiment — whose network is `--network host`?

`--network host` puts the container in **the host's own network namespace**. What "the host" means depends on where the Docker engine runs, and it changes both what you see and what you can break:

- **On macOS with Docker Desktop — the setup this course installs** — the engine runs inside a Linux virtual machine, so "the host" is *that VM*, not your Mac. You get the VM's interfaces, the VM's routing table, and a gateway of `192.168.65.1`. Your Wi-Fi router, your phone, and the rest of your LAN are **not** on this network and cannot be reached from it.
- **On a Linux host** "the host" is the machine itself. The gateway, the ARP neighbours, and the DHCP server you meet are your real LAN's — and anything you *change* changes that machine's real networking. There is no private copy, and `exit` undoes nothing.

Every mechanism this act teaches is visible either way: the VM's network has a real gateway to ARP for, a real routing table to decode by hand, a real MTU, a real resolver. Where an experiment genuinely needs a *populated* LAN — ARPing a neighbour you have never contacted, catching a DHCP offer, tracing real ISP hops — the lesson says so and hands you the Mac-native version in **[Act II in the wild](in-the-wild.md)**, which uses `arp -a`, `dig`, and `traceroute`. Run both: the container shows you the file, your Mac shows you the crowd.

## The lessons — read in this order

Work through these in order. Each one runs experiments in the lab container and ends with a link to the next, so you never have to guess where to go.

- **01 · [The wire and the two names](01-ethernet-and-arp.md)** — Ethernet frames, MAC addresses, and ARP the translator between the two naming systems.
- **01b · [VLANs and segmentation](01b-vlans-and-segmentation.md)** — slicing one physical wire into isolated broadcast domains with a 12-bit tag.
- **02 · [IP and routing](02-ip-and-routing.md)** — the 32-bit address and the routing table's longest-prefix match.
- **02b · [Routing protocols and BGP](02b-routing-and-bgp.md)** — who fills the routing table, and the trusting protocol that runs the whole internet.
- **03 · [ICMP, UDP, and TTL](03-icmp-and-udp.md)** — the error channel, the bare-minimum transport, and the hop budget.
- **03b · [MTU and fragmentation](03b-mtu-and-fragmentation.md)** — what happens when a packet is too big for the next wire.
- **03c · [DHCP — how a host gets its address](03c-dhcp.md)** — the broadcast that hands a brand-new machine its whole network identity.
- **04 · [DNS — the distributed naming database](04-dns.md)** — turning a human name into an address.

When you've finished all eight, do the recall exercise from memory (answers hidden): **[Test yourself →](test-yourself.md)**. Then prove you can *use* it under fire with the symptom-first **[Diagnose it →](diagnose.md)** on-call drills. When you want to look something up rather than learn it, that is what [the instrument panel](../../reference/README.md) is for — [the map](../../reference/03-the-map.md) ties every tool to the piece of kernel state it reads, and [the grammar](../../reference/01-the-grammar.md) is the page that lets you work out a command nobody showed you.

**What breaks here.** A wire connects two machines, and within those two machines everything works. But the internet is not one wire — it is millions of separate networks stitched together, and the moment a packet has to cross more than one of them, the comfortable guarantees of a single shared wire are gone. Packets get dropped when a router's queue fills. They get reordered when two of them take different paths. They get duplicated when something retransmits. Nothing you build in this act recovers from any of that: Ethernet, ARP, IP, and UDP will all happily lose your data and never tell you. Surviving a journey across many networks that drop, reorder, and duplicate whatever you hand them is a different problem, and it is Act III.
