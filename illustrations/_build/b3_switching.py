"""Batch 3 -- Switching and Layer 2."""

from prims import *  # noqa: F401,F403

OUT = "../03-switching-layer2"

VA, VB = PRIM, MID  # the two VLAN colours, reused across this batch


def hubs_switches_bridges():
    """Repeat to everyone; forward to one; join two segments."""
    body = [
        hub(76, 56, 70, 24),
        arrow(76, 70, 44, 96, stroke=MID), arrow(76, 70, 76, 96, stroke=MID),
        arrow(76, 70, 108, 96, stroke=MID),
        switch_dev(76, 138, 76, 26, ports=5),
        arrow(76, 152, 76, 182, stroke=PRIM),
        node(44, 186, 5, TINT), node(108, 186, 5, TINT),
        dashed_boundary(188, 44, 92, 44),
        node(212, 66, 5, TINT), node(256, 66, 5, TINT),
        bridge(234, 122, 52, 26),
        line(234, 88, 234, 109, stroke=MID),
        line(234, 135, 234, 156, stroke=MID),
        dashed_boundary(188, 156, 92, 44),
        node(212, 178, 5, TINT), node(256, 178, 5, TINT),
    ]
    return body, "A repeater, a forwarder, and a device joining two segments"


def vlans():
    """One switch, two separate broadcast worlds sharing it."""
    body = [
        switch_dev(160, 78, 130, 32, ports=8,
                   port_fills=[VA, VA, VA, VB, VB, VB, VA, VB]),
        dashed_boundary(24, 128, 122, 84, stroke=PRIM),
        laptop(56, 168, 0.42), laptop(114, 168, 0.42),
        dashed_boundary(174, 128, 122, 84, stroke=MID),
        laptop(206, 168, 0.42), laptop(264, 168, 0.42),
        line(112, 94, 78, 128, stroke=PRIM), line(196, 94, 236, 128, stroke=MID),
    ]
    return body, "One switch carrying two isolated groups of ports"


def trunking_8021q():
    """One link between switches, every frame carrying its group tag."""
    body = [
        switch_dev(66, 74, 84, 28, ports=5, port_fills=[VA, VA, VB, VB, VA]),
        switch_dev(254, 74, 84, 28, ports=5, port_fills=[VA, VB, VB, VA, VA]),
        pipe(108, 66, 104, 16),
        frame(60, 140, 100, 26, head=22, tail=10, fill=TINT),
        tag(74, 153, 30, 18, fill=PRIM),
        frame(174, 140, 100, 26, head=22, tail=10, fill=TINT),
        tag(188, 153, 30, 18, fill=MID),
        packet(160, 74, 11, 5.5, 11),
    ]
    return body, "A single link between switches carrying tagged frames from both groups"


def spanning_tree_protocol():
    """A loop in the wiring, one link deliberately blocked."""
    body = [
        switch_dev(160, 54, 72, 24, ports=4),
        switch_dev(66, 150, 72, 24, ports=4),
        switch_dev(254, 150, 72, 24, ports=4),
        line(132, 66, 92, 138, stroke=PRIM, sw=SW * 1.6),
        line(188, 66, 228, 138, stroke=PRIM, sw=SW * 1.6),
        line(102, 156, 218, 156, stroke=MID, dash="6 5"),
        x_badge(160, 156, 13, MID),
        node(66, 196, 5, TINT), node(254, 196, 5, TINT),
    ]
    return body, "A wiring loop with one redundant link blocked to leave a tree"


def switch_mac_tables():
    """The switch learns which port each address sits behind."""
    body = [
        switch_dev(160, 62, 120, 30, ports=6,
                   port_fills=[MID, PRIM, MID, MID, MID, MID]),
        arrow(160, 92, 160, 116, stroke=PRIM),
        table_card(72, 124, 176, 84, rows=4, accent_row=1, bar=False),
        laptop(46, 62, 0.4), line(76, 62, 100, 62, stroke=MID),
        laptop(274, 62, 0.4), line(244, 62, 220, 62, stroke=MID),
    ]
    return body, "A learned table mapping each hardware address to a switch port"


def collision_vs_broadcast_domains():
    """Left: everyone shares one wire. Right: a router bounds each broadcast world."""
    body = [
        circ(84, 118, 58, "none", stroke=MID, sw=SW),
        hub(84, 92, 64, 22),
        line(58, 103, 58, 132, stroke=MID), line(84, 103, 84, 132, stroke=MID),
        line(112, 103, 112, 132, stroke=MID),
        node(58, 140, 5, TINT), node(84, 140, 5, TINT), node(112, 140, 5, TINT),
        dashed_boundary(180, 38, 116, 72, stroke=PRIM),
        switch_dev(238, 60, 68, 24, ports=4),
        node(216, 94, 5, TINT), node(260, 94, 5, TINT),
        router(238, 130, 64, 24),
        line(238, 110, 238, 118, stroke=MID),
        line(238, 142, 238, 150, stroke=MID),
        dashed_boundary(180, 150, 116, 72, stroke=PRIM),
        switch_dev(238, 172, 68, 24, ports=4),
        node(216, 206, 5, TINT), node(260, 206, 5, TINT),
    ]
    return body, "One shared collision domain beside two router-bounded broadcast domains"


def port_security():
    """A known device is let in; an unknown one is not."""
    body = [
        switch_dev(160, 70, 116, 30, ports=6,
                   port_fills=[MID, PRIM, MID, MID, MID, MID]),
        padlock(160, 128, 0.9),
        laptop(72, 176, 0.46), check_badge(72, 210, 12, PRIM),
        line(72, 152, 108, 100, stroke=PRIM),
        laptop(248, 176, 0.46), x_badge(248, 210, 12, MID),
        line(248, 152, 212, 100, stroke=MID, dash="6 5"),
    ]
    return body, "A switch port that admits a known device and refuses an unknown one"


def link_aggregation():
    """Three separate links above; the same link treated as one below."""
    body = [
        switch_dev(70, 64, 80, 28, ports=4),
        switch_dev(250, 64, 80, 28, ports=4),
        line(110, 54, 210, 54, stroke=PRIM),
        line(110, 64, 210, 64, stroke=PRIM),
        line(110, 74, 210, 74, stroke=PRIM),
        dashed_boundary(104, 42, 112, 44, r=10, stroke=MID),
        arrow(160, 104, 160, 130, stroke=MID),
        switch_dev(70, 176, 80, 28, ports=4),
        switch_dev(250, 176, 80, 28, ports=4),
        pipe(110, 164, 100, 24),
    ]
    return body, "Parallel links bundled so they behave as one wider link"


TOPICS = [
    ("hubs-vs-switches-vs-bridges", hubs_switches_bridges),
    ("vlans", vlans),
    ("trunking-802-1q", trunking_8021q),
    ("spanning-tree-protocol", spanning_tree_protocol),
    ("switch-mac-tables", switch_mac_tables),
    ("collision-vs-broadcast-domains", collision_vs_broadcast_domains),
    ("port-security", port_security),
    ("link-aggregation", link_aggregation),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
