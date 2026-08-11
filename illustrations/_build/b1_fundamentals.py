"""Batch 1 -- Fundamentals."""

from prims import *  # noqa: F401,F403

OUT = "../01-fundamentals"


def osi_model():
    """Seven layers, a packet descending the stack."""
    body = [
        stack(126, 120, 7, w=150, lh=18, gap=5, accents=(2, 4)),
        arrow(34, 44, 34, 196, stroke=MID),
        packet(258, 76, 15, 7.5, 15),
        packet(258, 164, 15, 7.5, 15),
        arrow(258, 108, 258, 132, stroke=PRIM),
    ]
    return body, "Seven stacked protocol layers with data descending the stack"


def tcp_ip_model():
    """Two four-layer peers talking top-to-top, wire at the bottom."""
    body = [
        stack(78, 112, 4, w=104, lh=22, gap=6, accents=(0,)),
        stack(242, 112, 4, w=104, lh=22, gap=6, accents=(0,)),
        curve_arrow(78, 58, 242, 58, bow=26, stroke=PRIM, dash="6 5"),
        line(78, 178, 78, 200), line(242, 178, 242, 200),
        line(52, 200, 268, 200, stroke=DARK),
        packet(160, 200 - 20, 13, 6.5, 13),
    ]
    return body, "Two four-layer stacks exchanging data over a shared link"


def packets_and_frames():
    """A cube (packet) getting wrapped in a flat frame."""
    body = [
        packet(64, 118, 19, 9.5, 19),
        arrow(102, 118, 136, 118, stroke=MID),
        frame(152, 96, 138, 44, head=20, tail=15),
        packet(221, 118, 13, 6.5, 13),
    ]
    return body, "A packet wrapped inside a frame with header and trailer"


def bandwidth_vs_latency():
    """Wide pipe carrying many cubes; thin pipe, one cube, a clock."""
    body = [
        pipe(40, 62, 200, 38),
        packet(78, 81, 12, 6, 12), packet(140, 81, 12, 6, 12),
        packet(202, 81, 12, 6, 12),
        pipe(40, 168, 200, 12),
        packet(78, 174, 10, 5, 10),
        clock(268, 174, 20),
        arrow(240, 81, 264, 81, stroke=PRIM),
    ]
    return body, "A wide pipe moving many packets versus a narrow slow one"


def circuit_vs_packet_switching():
    """One reserved path above; independent hops below."""
    body = [
        node(46, 66), node(160, 66, fill=TINT), node(274, 66),
        path("M46 66 L160 66 L274 66", stroke=PRIM, sw=SW * 1.9),
        node(46, 174), node(274, 174),
        node(160, 140, fill=TINT), node(160, 200, fill=TINT),
        path("M46 174 Q100 140 160 140 T274 174", stroke=MID, dash="6 5"),
        path("M46 174 Q100 200 160 200 T274 174", stroke=MID, dash="6 5"),
        packet(120, 143, 9, 4.5, 9), packet(206, 197, 9, 4.5, 9),
    ]
    return body, "A dedicated circuit compared with packets taking separate paths"


def analog_vs_digital():
    """Continuous curve, then discrete steps."""
    body = [
        sine(46, 80, 228, amp=26, cycles=2, stroke=MID),
        square_wave(46, 166, 228, amp=24, steps=5, stroke=PRIM),
    ]
    return body, "A continuous analog wave above a discrete digital square wave"


def network_topologies():
    """Star, mesh, bus, ring in one 2x2 plate."""
    import math as m

    def star(cx, cy, r=26):
        out = [node(cx, cy, 7, TINT)]
        for a in range(0, 360, 72):
            x, y = cx + m.cos(m.radians(a)) * r, cy + m.sin(m.radians(a)) * r
            out += [line(cx, cy, x, y, stroke=MID), node(x, y, 4.6)]
        return out

    def mesh(cx, cy, r=24):
        pts = [(cx + m.cos(m.radians(a - 90)) * r, cy + m.sin(m.radians(a - 90)) * r)
               for a in range(0, 360, 90)]
        out = []
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                out.append(line(*pts[i], *pts[j], stroke=MID))
        return out + [node(x, y, 4.6) for x, y in pts]

    def bus(cx, cy, w=64):
        out = [line(cx - w, cy, cx + w, cy, stroke=MID)]
        for i in (-1, -0.33, 0.33, 1):
            x = cx + i * w * 0.86
            out += [line(x, cy, x, cy - 16), node(x, cy - 20, 4.6)]
        return out

    def ring(cx, cy, r=24):
        out = [circ(cx, cy, r, "none", stroke=MID)]
        for a in range(0, 360, 60):
            out.append(node(cx + m.cos(m.radians(a)) * r,
                            cy + m.sin(m.radians(a)) * r, 4.6))
        return out

    body = star(84, 74) + mesh(232, 74) + bus(84, 176) + ring(232, 172)
    body += [line(160, 34, 160, 206, stroke=MID, sw=1.4, dash="4 6"),
             line(28, 122, 292, 122, stroke=MID, sw=1.4, dash="4 6")]
    return body, "Four network shapes: star, mesh, bus and ring"


def lan_wan_man():
    """Nested scopes: a room, a city, the world."""
    body = [
        dashed_boundary(22, 58, 104, 124),
        switch_dev(74, 88, 64, 24, ports=5),
        laptop(50, 146, 0.48), laptop(98, 146, 0.48),
        line(74, 100, 74, 122, stroke=MID),
        line(126, 120, 140, 120, stroke=MID),
        dashed_boundary(140, 58, 76, 124),
        rack(178, 94, 38, 48, slots=3),
        rack(178, 152, 38, 38, slots=2),
        line(216, 112, 234, 102, stroke=MID),
        cloud(262, 90, 88),
        line(262, 114, 262, 154, stroke=MID),
        globe(262, 180, 22),
    ]
    return body, "A local network, a metro network and a global cloud in scope order"


TOPICS = [
    ("osi-model", osi_model),
    ("tcp-ip-model", tcp_ip_model),
    ("packets-and-frames", packets_and_frames),
    ("bandwidth-vs-latency", bandwidth_vs_latency),
    ("circuit-vs-packet-switching", circuit_vs_packet_switching),
    ("analog-vs-digital-signals", analog_vs_digital),
    ("network-topologies", network_topologies),
    ("lan-vs-wan-vs-man", lan_wan_man),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
