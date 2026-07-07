/**
 * Specs for annotated output blocks (`<kz-annotate spec="…">`).
 *
 * The course's central move is "read the kernel's own file rather than trusting a tool," and the files
 * it asks you to read are hostile: a `/proc/net/tcp` row is little-endian hex with no header, a
 * `conntrack` row is two tuples printed side by side with nothing marking where one ends. The lessons
 * handle this by drawing ASCII pointers under the fields — which works, and is exactly why those blocks
 * stay in the source as the fallback here.
 *
 * What an annotation adds is being able to ask about *one* field without decoding a diagram of all of
 * them. Hover or focus a field to see what it is; the numbered legend below says the same thing in a
 * form that survives print, touch, and no-JS.
 *
 * Same contract as diagrams.ts: a lesson only ever *names* an annotation, its raw block stays directly
 * underneath, and GitHub renders that block unchanged.
 *
 * Fields are listed **in the order they appear in `text`**, and the builder scans left to right,
 * continuing from the end of the previous match. That is what lets `01` mean the standalone state
 * column rather than the `01` inside `0100007F` two fields earlier — no occurrence counting, no
 * character offsets to re-count every time a lesson's example output changes.
 */

export interface AnnotatedField {
  /** Substring to mark, found at or after the end of the previous field's match. */
  find: string;
  /** Short name for the field — what a `man` page would call it. */
  label: string;
  /** What it means *here*, in this row. The decode, not the definition. */
  note: string;
}

export interface Annotation {
  /** The output being annotated, one string per line. Rendered in mono, fields marked. */
  text: string[];
  /** One line above the block: what you are looking at, and what produced it. */
  lead?: string;
  fields: AnnotatedField[];
  /** Rendered under the legend. Say what the *shape* teaches, not what the notes already say. */
  caption?: string;
}

export const ANNOTATIONS: Record<string, Annotation> = {
  /**
   * act-3/03-tcp-reliability.md — the row the whole "bytes in flight" idea is read from. The two hex
   * halves are the lesson: one is byte-swapped and one is not, and nothing in the file says so.
   */
  'proc-net-tcp-row': {
    lead: 'One row of /proc/net/tcp, as the kernel prints it. Every field is hex — but only the addresses are byte-swapped.',
    text: ['0: 0100007F:1F90 0100007F:C1A2 01 00000140:00000000'],
    caption:
      'The asymmetry is the thing to carry away: addresses are little-endian and must be reversed, '
      + 'ports are not. Once you can read this row, every tool that claims to show you connections '
      + 'becomes a program that reads this file and tidies it.',
    fields: [
      {
        find: '0100007F',
        label: 'local address',
        note: 'Little-endian hex. The bytes 01 00 00 7F, reversed, are 7F 00 00 01 → 127.0.0.1.',
      },
      {
        find: '1F90',
        label: 'local port',
        note: 'Plain big-endian hex: 0x1F90 = 8080. Ports are NOT byte-swapped — only addresses are.',
      },
      {
        find: '0100007F',
        label: 'remote address',
        note: 'Also 127.0.0.1, so this is a loopback connection with both ends on one machine.',
      },
      {
        find: 'C1A2',
        label: 'remote port',
        note: '0xC1A2 = 49570 — an ephemeral port the kernel picked for the client end.',
      },
      {
        find: '01',
        label: 'st (state)',
        note: '01 = ESTABLISHED. Also worth knowing: 06 TIME_WAIT, 08 CLOSE_WAIT, 0A LISTEN.',
      },
      {
        find: '00000140',
        label: 'tx_queue',
        note: '0x140 = 320 bytes written by the application but not yet acknowledged — the bytes in flight.',
      },
      {
        find: '00000000',
        label: 'rx_queue',
        note: '0 bytes received and buffered but not yet read() by the application. A backlog here means a slow reader.',
      },
    ],
  },

  /**
   * act-3/02b-conntrack.md — the conntrack row. Its most useful property is the single field where the
   * two tuples disagree, which is easy to miss when both are printed as walls of key=value.
   */
  'conntrack-row': {
    lead: 'One row of /proc/net/nf_conntrack: the original tuple, then the reply tuple. The one place they disagree is the NAT mapping.',
    text: [
      'ipv4 2 tcp 6 117 ESTABLISHED',
      '  src=10.0.0.7 dst=93.184.216.34 sport=51920 dport=443',
      '  src=93.184.216.34 dst=203.0.113.5 sport=443 dport=51920',
      '  [ASSURED] mark=0 use=1',
    ],
    caption:
      'Read the two tuples as a pair of questions: what did the host actually send, and what will the '
      + 'reply look like? Everything matches except the address NAT rewrote — and that single '
      + 'disagreement is the entire reason a reply can find its way home.',
    fields: [
      {
        find: '117',
        label: 'TTL',
        note: 'Seconds until this entry is evicted if the connection goes idle — which is why a finished connection still occupies a row.',
      },
      {
        find: 'ESTABLISHED',
        label: 'tracked state',
        note: "Conntrack's own view of the TCP state. Related to, but separate from, the socket's state in /proc/net/tcp.",
      },
      {
        find: 'src=10.0.0.7',
        label: 'original source',
        note: 'The private address the host really sent from. This is the truth NAT is about to hide.',
      },
      {
        find: 'dst=203.0.113.5',
        label: 'reply destination',
        note: 'THE MAPPING. The reply is addressed to the public NATted address, not to 10.0.0.7 — so the kernel must consult this row to rewrite it back.',
      },
      {
        find: '[ASSURED]',
        label: 'ASSURED',
        note: 'Traffic has been seen both ways, so this entry will not be evicted early when the table comes under pressure.',
      },
    ],
  },

  /**
   * act-5/04-coredns.md — three lines that explain most Kubernetes DNS surprises. Readers reliably read
   * the first one and skip the third, which is the one that costs them.
   */
  'pod-resolv-conf': {
    lead: "A Pod's /etc/resolv.conf, written by kubelet. You never configure this file — but nearly every cluster DNS oddity is explained by it.",
    text: [
      'nameserver 10.96.0.10',
      'search default.svc.cluster.local svc.cluster.local cluster.local',
      'options ndots:5',
    ],
    caption:
      'The line that costs you performance is the one that looks like a detail. ndots:5 means any name '
      + 'with fewer than five dots walks the whole search list first — so an external lookup from inside '
      + 'a Pod is several queries, not one.',
    fields: [
      {
        find: '10.96.0.10',
        label: 'nameserver',
        note: "A ClusterIP — so a Pod's very first DNS query already goes through kube-proxy's DNAT to reach a CoreDNS Pod.",
      },
      {
        find: 'default.svc.cluster.local',
        label: 'search (first)',
        note: 'Tried first, which is why a bare `database` resolves inside your own namespace with no qualification.',
      },
      {
        find: 'ndots:5',
        label: 'ndots',
        note: 'Fewer than 5 dots? Append every search domain before trying the name as given. api.example.com has 3 — so it pays the whole list first.',
      },
    ],
  },
};
