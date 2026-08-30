/**
 * Every dated, place-able claim the course makes, pulled out of the lessons for `/history-map/`.
 *
 * One array, three consumers: `HistoryMap.astro` draws the pins and the "first ARPANET link" line
 * from `MARKERS`, and its client script cross-highlights whichever `[data-hm-key]` element (a pin or
 * a ledger row) the reader points at; `HistoryLedger.astro` renders `EVENTS` as the chronological
 * ledger; `HistoryUnpinned.astro` renders `UNPINNED`. Keeping the data here rather than duplicated in
 * each component is the whole reason the three stay in sync.
 *
 * Coordinates are hand-placed pixels on a custom projection (see the comment in HistoryMap.astro),
 * not real latitude/longitude — this is a schematic strip, not a navigational chart. `source` is the
 * lesson file each claim is paraphrased from, relative to `networking-fundamentals/`.
 */

export interface HistoryMarker {
  /** Shown in the pin's label and the detail panel's heading. */
  name: string;
  x: number;
  y: number;
  /** Label offset from the pin centre, in the same SVG units. */
  labelDx: number;
  labelDy: number;
  anchor: 'start' | 'middle' | 'end';
}

export const MARKERS = {
  bayarea: { name: 'San Francisco Bay Area, CA', x: 37.9, y: 209.8, labelDx: 16, labelDy: 4, anchor: 'start' },
  la: { name: 'Los Angeles, CA', x: 52.1, y: 235.1, labelDx: 14, labelDy: 4, anchor: 'start' },
  seattle: { name: 'Seattle, WA', x: 37.2, y: 132.2, labelDx: 13, labelDy: 4, anchor: 'start' },
  cambridge: { name: 'Cambridge, MA', x: 250, y: 150, labelDx: 0, labelDy: -12, anchor: 'middle' },
  cornell: { name: 'Ithaca, NY', x: 185, y: 150, labelDx: 0, labelDy: -12, anchor: 'middle' },
  nj: { name: 'Murray Hill, NJ', x: 250, y: 205, labelDx: 0, labelDy: 16, anchor: 'middle' },
  pa: { name: 'Lewisburg, PA', x: 190, y: 205, labelDx: 0, labelDy: 16, anchor: 'middle' },
  amsterdam: { name: 'Amsterdam, Netherlands', x: 526.6, y: 96.1, labelDx: 14, labelDy: 4, anchor: 'start' },
  cern: { name: 'Geneva, Switzerland', x: 530.9, y: 142.7, labelDx: 14, labelDy: 4, anchor: 'start' },
  pakistan: { name: 'Islamabad, Pakistan', x: 788.7, y: 238.0, labelDx: 0, labelDy: 16, anchor: 'middle' },
  china: { name: 'Jinan, China', x: 957.4, y: 215.5, labelDx: -16, labelDy: 4, anchor: 'end' },
} as const satisfies Record<string, HistoryMarker>;

export interface HistoryEvent {
  key: keyof typeof MARKERS;
  year: number;
  label: string;
  title: string;
  detail: string;
  source: string;
}

export interface UnpinnedEvent {
  year: string;
  title: string;
  detail: string;
  source: string;
}

export const EVENTS: HistoryEvent[] = [
  { key: 'cambridge', year: 1967, label: '1967', title: "IBM's CP-67 slices one mainframe into many", detail: 'A System/360 in a room the size of a tennis court gives every user what looks like their own private computer.', source: 'act-4-one-pretends-many/README.md' },
  { key: 'la', year: 1969, label: '1969', title: 'Charley Kline dials out from UCLA', detail: 'He types L, O — Stanford echoes both back — then types G, and the receiving machine crashes.', source: 'act-2-two-machines/README.md' },
  { key: 'bayarea', year: 1969, label: '1969', title: 'The other end of that call answers, in Menlo Park', detail: "SRI's machine is the far end of the first host-to-host connection on the ARPANET, October 29, 1969.", source: 'act-2-two-machines/README.md' },
  { key: 'nj', year: 1971, label: '1971', title: "Ritchie and Thompson build Unix's pipe", detail: "Programs learn to cooperate — feed one's output into another's input — without one scribbling on another's memory.", source: '00-orientation/01-what-is-a-process.md' },
  { key: 'bayarea', year: 1973, label: '1973', title: 'Ethernet is born at Xerox PARC', detail: 'Bob Metcalfe needs to address one Alto computer on a coaxial cable that every card on it can hear.', source: 'act-2-two-machines/01-ethernet-and-arp.md' },
  { key: 'bayarea', year: 1974, label: '1974', title: "Cerf and Kahn publish the internet's founding paper", detail: '"A Protocol for Packet Network Intercommunication" proposes gluing together networks that fail in different ways.', source: 'act-3-the-internet/README.md' },
  { key: 'la', year: 1980, label: '1980', title: 'UDP ships in eight bytes', detail: "RFC 768, out of USC's Information Sciences Institute, gets away with four sixteen-bit fields.", source: 'act-2-two-machines/03-icmp-and-udp.md' },
  { key: 'la', year: 1981, label: '1981', title: 'IP learns to fragment, ICMP learns to complain', detail: "RFC 791 lets a router chop a packet that doesn't fit; RFC 792 lets it tell the sender why one vanished.", source: 'act-2-two-machines/03b-mtu-and-fragmentation.md' },
  { key: 'cambridge', year: 1982, label: '1982', title: 'ARP starts asking "who has this address?"', detail: "David Plummer's RFC 826 trusts any reply it gets — built for a LAN of colleagues, not yet of attackers.", source: 'act-2-two-machines/01-ethernet-and-arp.md' },
  { key: 'la', year: 1983, label: '1983', title: 'DNS replaces one big file with delegated authority', detail: "Paul Mockapetris designs a distributed database so google.com's owner can answer for google.com.", source: 'act-2-two-machines/04-dns.md' },
  { key: 'nj', year: 1985, label: '1985', title: 'Robert Morris describes sequence-number prediction', detail: "The trick his son's worm would use three years later to impersonate a trusted host.", source: 'act-3-the-internet/01-tcp-handshake.md' },
  { key: 'cornell', year: 1988, label: '1988', title: 'The Morris Worm infects roughly 10% of the internet', detail: 'Launched via a machine at MIT to mask its Cornell origin; about 6,000 machines in 24 hours.', source: 'act-3-the-internet/01-tcp-handshake.md' },
  { key: 'cern', year: 1990, label: '1990', title: 'Tim Berners-Lee designs HTTP', detail: "Trivial enough that anyone, in any language, can write a server or a browser that speaks it.", source: 'act-3-the-internet/04-http.md' },
  { key: 'bayarea', year: 1994, label: '1994–95', title: "Netscape answers the web's privacy problem", detail: "SSL, later standardized and renamed TLS, so a router in the middle can't read or rewrite what it forwards.", source: 'act-3-the-internet/05-tls.md' },
  { key: 'pa', year: 1997, label: '1997', title: 'DHCP lets an addressless machine shout for help', detail: 'RFC 2131 broadcasts to ff:ff:ff:ff:ff:ff — the one thing a host with no address can still do.', source: 'act-2-two-machines/03c-dhcp.md' },
  { key: 'china', year: 2004, label: '2004', title: 'Wang and Yu break MD5', detail: 'Two 128-byte blocks, one byte apart, share an identical hash — collision resistance falls.', source: 'act-8-trust/01-hashing.md' },
  { key: 'bayarea', year: 2007, label: '2007', title: 'cgroups give every tenant a metered slice', detail: "Merged into the Linux kernel so one process's memory leak can't starve every other tenant on the box.", source: 'act-4-one-pretends-many/01b-cgroups.md' },
  { key: 'pakistan', year: 2008, label: '2008-02-24', title: 'Pakistan Telecom accidentally hijacks YouTube', detail: 'A route meant only to block YouTube domestically propagates, more specific, to the whole internet.', source: 'act-2-two-machines/02-ip-and-routing.md' },
  { key: 'seattle', year: 2008, label: '2008', title: "Dan Kaminsky breaks the DNS resolver's trust", detail: 'A 16-bit query ID is only 65,536 guesses — winnable, with enough retries, in seconds.', source: 'act-2-two-machines/04-dns.md' },
  { key: 'bayarea', year: 2014, label: '2014', title: 'Google publishes the Borg paper', detail: 'A decade of running Search, Gmail, and YouTube on one shared, self-healing pool of machines, described in public.', source: 'act-5-kubernetes/README.md' },
  { key: 'amsterdam', year: 2017, label: '2017', title: 'SHA-1 falls to a real collision', detail: 'CWI Amsterdam and Google engineer two distinct files that hash identically.', source: 'act-8-trust/01-hashing.md' },
  { key: 'bayarea', year: 2021, label: '2021-10-04', title: "Facebook withdraws its own routes — and vanishes", detail: "No wrong announcement, just none at all; every router's longest-prefix match has nothing left to hit.", source: 'act-2-two-machines/02b-routing-and-bgp.md' },
];

export const UNPINNED: UnpinnedEvent[] = [
  { year: '1989', title: 'BGP is sketched on a napkin at an IETF meeting', detail: "Kirk Lougheed and Yakov Rekhter's back-of-napkin design becomes RFC 1105.", source: 'act-2-two-machines/02b-routing-and-bgp.md' },
  { year: '1998', title: 'IEEE 802.1Q gives Ethernet virtual partitions', detail: 'One physical switch, many independent VLANs, defined by a number tagged on every frame.', source: 'act-2-two-machines/01b-vlans-and-segmentation.md' },
  { year: '2002–2009', title: 'Linux grows network namespaces', detail: 'Merged in pieces by the kernel community — started 2002, finished around 2009.', source: 'act-4-one-pretends-many/01-namespaces.md' },
  { year: '2009', title: 'sslstrip automates stripping HTTPS off the first request', detail: "Moxie Marlinspike's tool works because that very first request was never protected.", source: 'act-3-the-internet/05-tls.md' },
  { year: '2012', title: 'RPKI adoption begins', detail: "Still partial today, which is part of why route hijacks like Pakistan's still happen.", source: 'act-2-two-machines/02b-routing-and-bgp.md' },
  { year: '2019', title: 'The Gateway API spec freezes at v1', detail: 'One backend, no weight, deliberately — the shape has looked the same since.', source: 'act-5-kubernetes/06b-gateway-api.md' },
  { year: '2021', title: 'Cilium releases pwru', detail: "An eBPF packet tracer that answers the one question netlink and procfs can't: which kernel function dropped this packet.", source: 'reference/tools/probe/pwru.md' },
  { year: '2023', title: 'Red Hat releases retis', detail: 'Same job as pwru, from a different vendor — two independent teams building the same tool.', source: 'reference/tools/probe/retis.md' },
];
