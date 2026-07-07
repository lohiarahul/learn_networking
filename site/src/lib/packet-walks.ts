/**
 * Declarative specs for the animated time–space diagrams (`<kz-packet-walk>`).
 *
 * Why a registry here rather than data in the lesson Markdown: the course files in
 * `networking-fundamentals/` are the single source of truth and have to stay readable as plain
 * Markdown on GitHub. So a lesson only ever *names* a figure — `<!-- figure: tcp-handshake -->` —
 * and keeps its ASCII diagram directly underneath. GitHub renders the ASCII; the site renders the
 * animation and uses the ASCII as its no-JS fallback. Neither surface loses anything, and the
 * course source stays prose, commands and ASCII.
 *
 * The idiom is the time–space (Kurose–Ross) diagram, not a UML sequence diagram: arrows slope
 * downward because a packet takes real time to cross a wire. That slope is the whole reason a
 * handshake costs a round trip, so it is worth drawing rather than asserting.
 *
 * No colours in this file. Same rule as astro.config.mjs's Mermaid block: the builder emits classed
 * elements only and `global.css` owns every colour, so diagrams follow the theme without a second
 * palette to keep in sync.
 */

/** One row of a walk: either a packet crossing between lanes, or a phase marker spanning them. */
export type Step =
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

export interface PacketWalk {
  /** Column headers, left to right. Two is the common case; three works (client, NAT, server). */
  lanes: string[];
  steps: Step[];
  /** Rendered under the diagram. Say what the *shape* teaches, not what the arrows already say. */
  caption?: string;
}

export const PACKET_WALKS: Record<string, PacketWalk> = {
  'tcp-handshake': {
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
};
