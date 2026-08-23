/**
 * Where a lesson sits in the descent from `write()` to the wire.
 *
 * The rungs are not the OSI model, and that is deliberate. They are the course's *own* descent — the
 * exact sequence `the-whole-stack.md` walks and `08-debugging.md` turns into a diagnostic ladder:
 * resolve the name, get a socket, make it a reliable stream, survive the address rewrites, pick a
 * route, put it on the wire. A reader who has seen this strip on forty lesson pages arrives at the
 * debugging method already knowing the order, which is the whole point of the method.
 *
 * Why per-lesson rather than per-act: the acts are a *teaching* order (one machine, two machines, the
 * internet, virtualisation, Kubernetes), which deliberately cuts across the stack — Act V's Services
 * lesson is about NAT, and its CoreDNS lesson is about names. The eyebrow above the title already says
 * which act you are in; this says which layer you are in, and the two genuinely differ.
 *
 * Pages with no entry get no rail, which covers the ones that are about the whole stack at once
 * (overviews, `diagnose`, `test-yourself`, `in-the-wild`, the capstone) or about none of it (setup,
 * reference, progress). Silence is correct there — a rail claiming a drill lives on one rung would be
 * a lie, and the capstone's whole subject is that it visits every rung in turn.
 *
 * Which is also why the map below stops at Act V, and why that is a decision rather than a gap left
 * to fill in later. The rungs are the descent from `write()` to the wire, and Acts VI–X are not on
 * it: a controller loop, a Pod spec's claims, a key exchange, a token's expiry and an admission
 * webhook are not layers a packet passes through. Two of them look close enough to tempt you — Act
 * VIII is *about* what rides on the stream, and Act X's Pod-to-Pod encryption lesson is *about* the
 * wire — but the rail exists to teach one specific order before `08-debugging.md` asks the reader to
 * walk it, and a reader in Act VIII walked it three acts ago. Adding rungs there would buy nothing
 * and would blur what the strip means everywhere it does appear.
 */
export const RUNGS = [
  { id: 'name', label: 'Name', hint: 'DNS — turning a name into an address' },
  { id: 'socket', label: 'Socket', hint: 'the file descriptor and the kernel object behind it' },
  { id: 'stream', label: 'Stream', hint: 'TCP, UDP — making the bytes trustworthy (or not)' },
  { id: 'rewrite', label: 'Rewrite', hint: 'NAT, conntrack, firewall — the address you asked for is not the one used' },
  { id: 'route', label: 'Route', hint: 'IP and the routing table — which way out' },
  { id: 'wire', label: 'Wire', hint: 'frames, MACs, veths, tunnels — the actual hop' },
] as const;

export type RungId = (typeof RUNGS)[number]['id'];

/**
 * Lesson path -> rung. Paths are the site's own URLs, which sync-content.mjs guarantees, and are
 * written out in full rather than pattern-matched: every one of these is a judgement about what a
 * lesson is *really* about, and a regex would hide the cases that surprised me.
 */
const LAYER_BY_PATH: Record<string, RungId> = {
  // Orientation — a process, and how it reaches anything at all.
  '/orientation/what-is-a-process/': 'socket',
  '/orientation/how-processes-communicate/': 'socket',

  // Act I — the file descriptor and the kernel object behind it.
  '/act-1/the-fd-table/': 'socket',
  '/act-1/the-socket-object/': 'socket',
  '/act-1/minihttp-server/': 'socket',
  // Loopback is a device, but the lesson's subject is the cost of the kernel's own stack — and it is
  // where the reader first sees a packet leave the socket layer at all.
  '/act-1/loopback/': 'socket',
  '/act-1/ports-and-proc-net-tcp/': 'socket',
  // The SYN scan is a lesson about TCP's state machine, not about descriptors.
  '/act-1/tcp-states-and-the-syn-scan/': 'stream',
  '/act-1/everything-is-a-file/': 'socket',
  '/act-1/the-container-filesystem/': 'socket',

  // Act II — the wire, then addresses, then names.
  '/act-2/ethernet-and-arp/': 'wire',
  '/act-2/vlans-and-segmentation/': 'wire',
  '/act-2/ip-and-routing/': 'route',
  '/act-2/routing-and-bgp/': 'route',
  '/act-2/icmp-and-udp/': 'route',
  '/act-2/mtu-and-fragmentation/': 'route',
  '/act-2/dhcp/': 'route',
  '/act-2/dns/': 'name',

  // Act III — the whole act is the reliable stream and what rides on it.
  '/act-3/tcp-handshake/': 'stream',
  '/act-3/tcp-reliability/': 'stream',
  // Half state machine, half conntrack — but conntrack is the half the reader will come back for.
  '/act-3/tcp-states/': 'rewrite',
  '/act-3/http/': 'stream',
  '/act-3/tls/': 'stream',
  // conntrack is the flow table NAT is written into, so it belongs on the rung it makes possible
  // rather than on the state machine it grew out of.
  '/act-3/conntrack/': 'rewrite',

  // Act IV — one machine as many. Namespaces and veths are wire; NAT and overlays are rewrites.
  '/act-4/namespaces/': 'wire',
  '/act-4/veth-and-bridge/': 'wire',
  '/act-4/iptables-and-nat/': 'rewrite',
  '/act-4/overlay-vxlan/': 'rewrite',
  // `/act-4/cgroups/` is deliberately absent. It sits in a networking act because that is where the
  // reader can first ask the question, but "how much of the machine may this process use" is not a
  // rung in the descent — no packet passes through it.

  // Act V — every lesson is an earlier rung wearing a Kubernetes name.
  '/act-5/pod-networking/': 'wire',
  '/act-5/services/': 'rewrite',
  '/act-5/coredns/': 'name',
  '/act-5/cni/': 'wire',
  '/act-5/ingress/': 'stream',
  '/act-5/network-policy/': 'rewrite',
  // The three lessons that split off an existing one sit on the rung their parent does: Gateway API
  // is Ingress's rung, and both the Service and the policy shape-catalogues are rewrites.
  '/act-5/gateway-api/': 'stream',
  '/act-5/service-shapes/': 'rewrite',
  '/act-5/policy-shapes/': 'rewrite',
};

/** The rung a page sits on, or null for pages that span the stack or sit outside it. */
export function rungForPath(pathname: string): RungId | null {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const rest = base && pathname.startsWith(base) ? pathname.slice(base.length) : pathname;
  const path = rest.endsWith('/') ? rest : `${rest}/`;
  return LAYER_BY_PATH[path] ?? null;
}
