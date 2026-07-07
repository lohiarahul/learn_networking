/**
 * Declarative specs for the built diagrams (`<kz-diagram spec="…">`).
 *
 * Why a registry here rather than data in the lesson Markdown: the course files in
 * `networking-fundamentals/` are the single source of truth and have to stay readable as plain
 * Markdown on GitHub. So a lesson only ever *names* a figure — `<!-- figure: tcp-handshake -->` —
 * and keeps its ASCII diagram directly underneath. GitHub renders the ASCII; the site renders the
 * built diagram and uses the ASCII as its no-JS fallback. Neither surface loses anything, and the
 * course source stays prose, commands and ASCII.
 *
 * Two kinds, because the lessons draw two genuinely different things:
 *
 *   'walk'  a time–space diagram — two parties, messages crossing between them in time order.
 *           The idiom is Kurose–Ross, not UML: arrows slope downward because a packet takes real
 *           time to cross a wire, which is the whole reason a handshake costs a round trip.
 *   'path'  a single packet's journey through a stack of stages, top to bottom. No second party;
 *           the interesting content is *what each stage does to the packet*.
 *
 * Diagrams that are neither — containment (a Pod holding three containers), side-by-side comparison
 * (before/after a NetworkPolicy), state machines — stay as framed ASCII. Forcing them into a
 * pipeline would throw away the very structure that makes them legible.
 *
 * No colours in this file. Same rule as astro.config.mjs's Mermaid block: the builders emit classed
 * elements only and `global.css` owns every colour, so diagrams follow the theme without a second
 * palette to keep in sync.
 */

/** One row of a walk: either a packet crossing between lanes, or a phase marker spanning them. */
export type WalkStep =
  | {
      kind: 'msg';
      /** Index into `lanes` — who sends. */
      from: number;
      /** Index into `lanes` — who receives. */
      to: number;
      /** The wire-level label: what a sniffer would show you. */
      label: string;
      /** Optional gloss — what the packet *means*, in the sender's voice. */
      says?: string;
    }
  | { kind: 'band'; label: string };

export interface WalkDiagram {
  kind: 'walk';
  /** Column headers, left to right. Two is the common case; three works (client, NAT, server). */
  lanes: string[];
  steps: WalkStep[];
  /** Rendered under the diagram. Say what the *shape* teaches, not what the arrows already say. */
  caption?: string;
}

/**
 * Official Kubernetes icons, served from `public/icons/k8s/`. Apache-2.0 / CC-BY-4.0 — see ASSETS.md.
 * Only used on Act V figures, where the boxes really are these named API objects.
 */
export type IconName = 'pod' | 'svc' | 'ing' | 'node';

export interface PathStage {
  icon?: IconName;
  /** Kept short — SVG text does not wrap, so a long title would run off the diagram. */
  title: string;
  /** Mono lines under the title: the concrete addresses, rules and rewrites. */
  detail?: string[];
  /** Label on the arrow leading *into* this stage — what moves the packet on. */
  via?: string;
}

export interface PathDiagram {
  kind: 'path';
  stages: PathStage[];
  caption?: string;
}

export type Diagram = WalkDiagram | PathDiagram;

export const DIAGRAMS: Record<string, Diagram> = {
  'tcp-handshake': {
    kind: 'walk',
    lanes: ['CLIENT', 'SERVER'],
    caption:
      'Every arrow slopes because a packet takes real time to cross the wire. Read the vertical '
      + 'distance before ESTABLISHED as one full round trip — the price TCP pays before it will '
      + 'carry a single byte of your data.',
    steps: [
      { kind: 'msg', from: 0, to: 1, label: 'SYN · seq=X', says: 'I start at X' },
      {
        kind: 'msg',
        from: 1,
        to: 0,
        label: 'SYN, ACK · seq=Y, ack=X+1',
        says: 'I start at Y, and I saw your X',
      },
      { kind: 'msg', from: 0, to: 1, label: 'ACK · ack=Y+1', says: 'saw your Y — go' },
      { kind: 'band', label: 'connection ESTABLISHED' },
      {
        kind: 'msg',
        from: 0,
        to: 1,
        label: 'data · seq=X+1 (PSH, ACK)',
        says: 'the first real byte',
      },
    ],
  },

  /** act-3/05-tls.md — TLS 1.2, because 1.3 folds these into fewer trips but the events are the same. */
  'tls-handshake': {
    kind: 'walk',
    lanes: ['CLIENT', 'SERVER'],
    caption:
      'Count the direction changes: four before any key material moves. This is the cost TLS 1.2 pays '
      + 'on top of the TCP handshake that had to finish first — and the reason TLS 1.3 exists is to '
      + 'collapse it.',
    steps: [
      { kind: 'band', label: 'TCP already ESTABLISHED' },
      {
        kind: 'msg',
        from: 0,
        to: 1,
        label: 'ClientHello',
        says: 'versions and ciphers I offer, a random, SNI: example.com',
      },
      {
        kind: 'msg',
        from: 1,
        to: 0,
        label: 'ServerHello',
        says: 'the version and cipher I chose, my random',
      },
      { kind: 'msg', from: 1, to: 0, label: 'Certificate', says: 'my leaf cert + chain' },
      { kind: 'msg', from: 1, to: 0, label: 'ServerHelloDone', says: 'your turn' },
      { kind: 'band', label: 'client verifies the chain to a trusted root' },
      {
        kind: 'msg',
        from: 0,
        to: 1,
        label: 'ClientKeyExchange',
        says: 'key material, encrypted to the server’s public key',
      },
      {
        kind: 'msg',
        from: 0,
        to: 1,
        label: 'ChangeCipherSpec · Finished',
        says: 'everything after this is encrypted',
      },
      { kind: 'msg', from: 1, to: 0, label: 'ChangeCipherSpec · Finished' },
      { kind: 'band', label: 'encrypted channel ready — HTTP can flow' },
    ],
  },

  /**
   * act-5/04-coredns.md — why an unqualified name is expensive. The four NXDOMAINs are the lesson,
   * so they are drawn one at a time rather than summarised: the waste is the point.
   */
  'coredns-ndots': {
    kind: 'walk',
    lanes: ['POD', 'CoreDNS'],
    caption:
      '“database” has zero dots, which is fewer than ndots:5 — so the resolver walks the whole search '
      + 'list before trying the name as given. Four wasted round trips, doubled again because each is '
      + 'sent for A and AAAA. Qualifying the namespace is the fix.',
    steps: [
      { kind: 'msg', from: 0, to: 1, label: 'database.default.svc.cluster.local' },
      { kind: 'msg', from: 1, to: 0, label: 'NXDOMAIN' },
      { kind: 'msg', from: 0, to: 1, label: 'database.svc.cluster.local' },
      { kind: 'msg', from: 1, to: 0, label: 'NXDOMAIN' },
      { kind: 'msg', from: 0, to: 1, label: 'database.cluster.local' },
      { kind: 'msg', from: 1, to: 0, label: 'NXDOMAIN' },
      { kind: 'msg', from: 0, to: 1, label: 'database.', says: 'tried as absolute' },
      { kind: 'msg', from: 1, to: 0, label: 'NXDOMAIN' },
      { kind: 'band', label: 'qualify the namespace' },
      { kind: 'msg', from: 0, to: 1, label: 'database.data.svc.cluster.local' },
      { kind: 'msg', from: 1, to: 0, label: 'A 10.96.55.10', says: 'the ClusterIP' },
    ],
  },

  /**
   * act-3/04-http.md — one request, one response. Modelled as two arrows rather than one per header
   * line, because the client writes the whole request with a single `write()`: drawing the headers as
   * separate messages would invent round trips that never happen. What the shape has to teach is that
   * the blank line, not any header, is what ends the headers.
   */
  'http-exchange': {
    kind: 'walk',
    lanes: ['CLIENT', 'SERVER'],
    caption:
      'One round trip, two text blocks. Notice that nothing in the protocol counts the headers — the '
      + 'blank line is the only thing that ends them, and Content-Length is the only thing that ends '
      + 'the body. Get either wrong and the parser reads your body as headers.',
    steps: [
      { kind: 'band', label: 'TCP already ESTABLISHED' },
      {
        kind: 'msg',
        from: 0,
        to: 1,
        label: 'request line · headers · BLANK LINE',
        says: 'GET /get HTTP/1.1, then Host:, then nothing at all',
      },
      {
        kind: 'msg',
        from: 1,
        to: 0,
        label: 'status line · headers · BLANK LINE · body',
        says: 'HTTP/1.1 200 OK, then Content-Length: 257, then 257 bytes',
      },
    ],
  },

  /**
   * act-2/03-icmp-and-udp.md — TTL as a hop budget. Drawn as a path because that is literally what
   * the field measures: one stage per router, one decrement each.
   */
  'ttl-decrement': {
    kind: 'path',
    caption:
      'The counter is the whole mechanism. It is not a clock and not a distance — it is a budget of '
      + 'hops, and the router that spends the last one is obliged to say so. Traceroute is that '
      + 'obligation turned into a mapping tool.',
    stages: [
      { title: 'sender', detail: ['sets TTL = 64', '(Linux default)'] },
      { via: 'forwarded', title: 'router R1', detail: ['TTL 64 → 63'] },
      { via: 'forwarded', title: 'router R2', detail: ['TTL 63 → 62'] },
      { via: 'forwarded', title: 'router R3', detail: ['TTL 62 → 61'] },
      {
        via: 'if the packet is looping, this keeps going',
        title: 'TTL reaches 0',
        detail: ['the router DROPS it', 'and sends ICMP time-exceeded', '(type 11) back to the sender'],
      },
    ],
  },

  /**
   * act-4/03-iptables-and-nat.md — the five hooks, drawn for a *forwarded* packet.
   *
   * The source ASCII shows the full branching diagram, which is the right reference. A path can only
   * show one route through it, so this draws the forwarding case — the one Kubernetes cares about —
   * and the caption names the local-delivery variant rather than pretending the fork isn't there.
   */
  'iptables-hooks': {
    kind: 'path',
    caption:
      'This is the route a *forwarded* packet takes. A packet addressed to the machine itself turns '
      + 'left after the routing decision into INPUT, and one born on the machine starts at OUTPUT — '
      + 'which is why the chain whose counters move tells you which of the three a packet was.',
    stages: [
      { title: 'packet arrives', detail: ['on some interface'] },
      {
        via: 'before any routing decision',
        title: 'PREROUTING',
        detail: ['nat table', 'DNAT rewrites the DESTINATION', '(this is where a ClusterIP dies)'],
      },
      {
        via: 'now the destination is real',
        title: 'routing decision',
        detail: ['for me → INPUT', 'for someone else → FORWARD'],
      },
      { via: '"for someone else"', title: 'FORWARD', detail: ['filter table', 'accept or drop'] },
      {
        via: 'the path is chosen; last chance to edit',
        title: 'POSTROUTING',
        detail: ['nat table', 'SNAT rewrites the SOURCE', '(MASQUERADE lives here)'],
      },
      { via: 'out', title: 'packet leaves' },
    ],
  },

  /**
   * act-4/04-overlay-vxlan.md — a packet inside a packet. The point of drawing it as a path is that
   * encapsulation is a *stage*, not a diagram of nesting: the same bytes acquire a wrapper, travel as
   * something else, and have it removed.
   */
  'vxlan-encap': {
    kind: 'path',
    caption:
      'The physical network never learns a Pod IP exists — it only ever sees 192.168.1.10 → '
      + '192.168.1.11. That is the whole trick, and the ~50 bytes of wrapper is its price: the reason '
      + 'an overlay Pod MTU must be set below the node MTU, exactly as Act II warned.',
    stages: [
      {
        icon: 'pod',
        title: 'Pod 10.244.1.5 on node A',
        detail: ['inner packet:', 'src 10.244.1.5 → dst 10.244.2.7'],
      },
      {
        via: 'the CNI hands it to the vxlan device',
        title: 'ENCAPSULATE',
        detail: [
          'outer UDP: 192.168.1.10 → 192.168.1.11',
          'dport 8472 (VXLAN)',
          '+ VXLAN header, inner frame inside',
          '≈ 50 bytes added',
        ],
      },
      {
        icon: 'node',
        via: 'routed by the OUTER header',
        title: 'physical network',
        detail: ['sees only node A → node B', 'knows no Pod IPs at all'],
      },
      {
        via: 'arrives on node B port 8472',
        title: 'DECAPSULATE',
        detail: ['strip outer UDP + VXLAN', 'recover the inner packet unchanged'],
      },
      {
        icon: 'pod',
        via: 'delivered into the Pod netns',
        title: 'Pod 10.244.2.7 on node B',
        detail: ['read() — it never knew it was wrapped'],
      },
    ],
  },

  /**
   * act-5/05-cni.md — the cross-node hop, one stage per device the packet actually crosses.
   *
   * Deliberately ends at "the CNI decides", because that last step is the one thing that differs
   * between plugins and the lesson's whole argument is that everything before it does not.
   */
  'cni-cross-node': {
    kind: 'path',
    caption:
      'Every stage above the physical network is Act IV, unchanged and run by a binary instead of by '
      + 'you. Only the last hop differs between plugins — Flannel wraps it, Calico routes it, Cilium '
      + 'redirects it in eBPF — which is why "which CNI?" is the last question, not the first.',
    stages: [
      { icon: 'pod', title: 'Pod 10.244.1.7 · eth0', detail: ['inside its own netns'] },
      { via: 'the veth pair — a virtual cable', title: 'veth peer on node A' },
      {
        via: 'plugged into the software switch',
        title: 'cni0 bridge',
        detail: ['same node? forwarded at L2, done', 'other node? no L2 path — climb to L3'],
      },
      {
        icon: 'node',
        via: 'longest-prefix match sends the /24 to node B',
        title: "node A's real nic",
        detail: ['the physical network knows no Pod IPs'],
      },
      {
        via: 'Flannel → VXLAN · Calico → BGP route · Cilium → eBPF',
        title: 'node B, in reverse',
        detail: ['nic → cni0 → veth → Pod eth0'],
      },
      { icon: 'pod', via: 'delivered', title: 'Pod 10.244.2.3 calls read()' },
    ],
  },

  /**
   * act-5/08-debugging.md — the five questions as a descent.
   *
   * The source ASCII is a list, and a list is exactly the wrong shape for it: the method's entire
   * claim is that these are *ordered*, because a lie at a lower layer makes every higher layer look
   * broken. Drawn as a path, the order is the diagram.
   */
  'debug-five-questions': {
    kind: 'path',
    caption:
      'Read top to bottom and stop at the first lie. The order is not a style preference — a wrong '
      + 'answer at any stage makes every stage below it look broken, so checking TCP before DNS tells '
      + 'you nothing you can trust.',
    stages: [
      {
        title: '1 · Does the name resolve?',
        detail: ['/etc/resolv.conf', 'dig @<CoreDNS ClusterIP>', '(Act II · CoreDNS)'],
      },
      {
        via: 'the name gave you an address — is it reachable?',
        title: '2 · Is there a route?',
        detail: ['ip route get <addr>', '(Act II · CNI)'],
      },
      {
        via: 'a route exists — is the packet rewritten or dropped?',
        title: '3 · NAT and firewall',
        detail: ['iptables -t nat -L', 'conntrack -L', 'NetworkPolicy', '(Act IV · Services)'],
      },
      {
        via: 'the packet is leaving — does anything answer?',
        title: '4 · Does TCP connect?',
        detail: ['tcpdump: SYN / SYN-ACK / RST', 'RST = refused · silence = dropped', '(Act II–III)'],
      },
      {
        via: 'it arrived — is anyone home?',
        title: '5 · Is the app listening?',
        detail: ['ss -tlnp inside the Pod', 'bound to 0.0.0.0 or just 127.0.0.1?', '(Act I)'],
      },
    ],
  },

  /** act-5/03-services.md — the chain walk that turns a ClusterIP into a real Pod address. */
  'k8s-service-path': {
    kind: 'path',
    caption:
      'Nothing owns 10.96.55.10 — it is on no interface in the cluster. It works because every node '
      + 'carries iptables rules that rewrite it before the packet is routed, and conntrack remembers '
      + 'the rewrite so the reply can be un-rewritten on the way back.',
    stages: [
      {
        icon: 'pod',
        title: 'Pod calls connect()',
        detail: ['10.96.55.10:80 — a ClusterIP', 'that exists on no interface'],
      },
      {
        via: "into the node's nat table, OUTPUT / PREROUTING",
        title: 'KUBE-SERVICES',
        detail: ['match dst 10.96.55.10 dpt 80', '→ jump KUBE-SVC-XXXX'],
      },
      {
        icon: 'svc',
        via: 'one rule per Service',
        title: 'KUBE-SVC-XXXX',
        detail: [
          'probability 0.333 → SEP-AAAA',
          'probability 0.500 → SEP-BBBB',
          '(fallthrough)     → SEP-CCCC',
        ],
      },
      {
        via: 'the statistic module picks one endpoint',
        title: 'KUBE-SEP-BBBB',
        detail: ['DNAT --to-destination', '10.244.2.3:8080 ← the rewrite'],
      },
      {
        icon: 'pod',
        via: 'conntrack records orig ↔ reply, then normal routing',
        title: 'Pod 10.244.2.3 calls read()',
        detail: ['reached via veth / bridge / overlay'],
      },
    ],
  },

  /** act-5/06-ingress.md — where TLS stops, and where the packet becomes plain HTTP. */
  'k8s-ingress-path': {
    kind: 'path',
    caption:
      'The single most useful fact on this page is where the TLS handshake from Act III terminates: at '
      + 'the controller Pod, not at the backend. Everything below that line is plain HTTP travelling '
      + 'inside the cluster.',
    stages: [
      { title: 'client', detail: ['HTTPS to api.example.com/v1'] },
      {
        via: 'DNS points at one public IP',
        title: 'LoadBalancer (cloud)',
        detail: ['one public IP, port 443'],
      },
      {
        icon: 'ing',
        via: 'forwarded to the controller Pods',
        title: 'Ingress controller Pod',
        detail: [
          'TLS TERMINATES HERE — holds the',
          'key and cert from a Secret',
          'reads Host: and path: /v1',
        ],
      },
      {
        icon: 'svc',
        via: 'plain HTTP from here on',
        title: 'ClusterIP 10.96.x.y:8080',
        detail: ['kube-proxy DNAT (Services)'],
      },
      {
        icon: 'pod',
        via: 'routed to the chosen endpoint',
        title: 'backend Pod 10.244.a.b:8080',
        detail: ['read()'],
      },
    ],
  },
};
