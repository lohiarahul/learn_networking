"""Batch 5 -- Transport Layer."""

from prims import *  # noqa: F401,F403

OUT = "../05-transport"


def tcp_handshake():
    """Three messages before any data moves."""
    body = [
        laptop(60, 52, 0.44), rack(260, 54, 40, 50, slots=3),
        lifeline(60, 76, 214), lifeline(260, 84, 214),
        arrow(72, 106, 248, 106, stroke=PRIM, head=7),
        arrow(248, 144, 72, 144, stroke=DARK, head=7),
        arrow(72, 182, 248, 182, stroke=PRIM, head=7),
    ]
    return body, "Three messages exchanged to open a connection"


def tcp_vs_udp():
    """Ordered and acknowledged; or fired off and forgotten."""
    body = [
        packet(58, 62, 12, 6, 12), packet(112, 62, 12, 6, 12),
        packet(166, 62, 12, 6, 12), packet(220, 62, 12, 6, 12),
        arrow(84, 62, 92, 62, stroke=MID, head=5),
        arrow(138, 62, 146, 62, stroke=MID, head=5),
        arrow(192, 62, 200, 62, stroke=MID, head=5),
        curve_arrow(248, 78, 58, 92, bow=-20, stroke=PRIM, dash="6 5", head=6),
        line(24, 122, 296, 122, stroke=MID, sw=1.4, dash="4 6"),
        packet(58, 168, 12, 6, 12), packet(122, 158, 12, 6, 12),
        x_badge(180, 176, 12, MID),
        packet(240, 162, 12, 6, 12),
        arrow(84, 168, 96, 162, stroke=MID, head=5),
        arrow(148, 158, 158, 166, stroke=MID, head=5),
        arrow(204, 172, 214, 165, stroke=MID, head=5),
    ]
    return body, "An ordered acknowledged stream above an unacknowledged one"


def ports_and_sockets():
    """One host, many numbered doors, each holding one conversation."""
    body = [
        rr(76, 52, 168, 76, 6, SURF),
        rr(90, 66, 34, 30, 3, TINT), rr(132, 66, 34, 30, 3, TINT),
        rr(174, 66, 34, 30, 3, TINT),
        rr(90, 106, 34, 10, 2, fill=PRIM, stroke=None),
        rr(132, 106, 34, 10, 2, fill=MID, stroke=None),
        rr(174, 106, 34, 10, 2, fill=PRIM, stroke=None),
        cable(107, 128, 72, 186, sag=26, stroke=PRIM),
        cable(191, 128, 246, 186, sag=26, stroke=PRIM),
        chip(72, 206, 62, 18, accent=PRIM),
        chip(246, 206, 62, 18, accent=PRIM),
    ]
    return body, "A host with several numbered ports, each holding one conversation"


def flow_control():
    """The receiver says how much it can take."""
    body = [
        laptop(58, 78, 0.46),
        arrow(96, 72, 196, 72, stroke=PRIM, head=7),
        rack(248, 78, 44, 60, slots=3),
        rr(96, 138, 128, 30, 4, SURF),
        rr(100, 142, 52, 22, 2, fill=PRIM, stroke=None),
        curve_arrow(206, 104, 100, 118, bow=-18, stroke=DARK, dash="6 5", head=6),
        bit_ruler(96, 182, 128, bits=6, on=2, h=16),
    ]
    return body, "A receiver advertising how much data it can still accept"


def congestion_control():
    """Push harder until it hurts, then back off."""
    body = [
        sawtooth(46, 112, 228, amp=56, teeth=3, stroke=PRIM),
        line(38, 118, 292, 118, stroke=MID, sw=1.8),
        line(38, 118, 38, 44, stroke=MID, sw=1.8),
        pipe(70, 156, 180, 26),
        packet(96, 169, 10, 5, 10), packet(122, 169, 10, 5, 10),
        packet(148, 169, 10, 5, 10),
        x_badge(232, 169, 12, MID),
    ]
    return body, "A sending rate that climbs, collapses on loss, and climbs again"


def common_port_numbers():
    """A short list of well-known doors."""
    body = [
        card(64, 44, 192, 152, bar=False),
        tag(102, 74, 46, 22, fill=PRIM), pill(150, 71, 84, 7, MID),
        tag(102, 112, 46, 22, fill=TINT), pill(150, 109, 68, 7, MID),
        tag(102, 150, 46, 22, fill=PRIM), pill(150, 147, 76, 7, MID),
        line(76, 93, 244, 93, stroke=MID, sw=1.4),
        line(76, 131, 244, 131, stroke=MID, sw=1.4),
        padlock(160, 210, 0.62, fill=MID),
    ]
    return body, "A short table of well-known service ports"


TOPICS = [
    ("tcp-handshake", tcp_handshake),
    ("tcp-vs-udp", tcp_vs_udp),
    ("ports-and-sockets", ports_and_sockets),
    ("flow-control", flow_control),
    ("congestion-control", congestion_control),
    ("common-port-numbers", common_port_numbers),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
