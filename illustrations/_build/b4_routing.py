"""Batch 4 -- Routing and Layer 3."""

from prims import *  # noqa: F401,F403

OUT = "../04-routing-layer3"


def routers_and_routing_tables():
    """The device and the table it consults for every packet."""
    body = [
        router(160, 56, 92, 32),
        packet(52, 56, 13, 6.5, 13), arrow(76, 56, 108, 56, stroke=MID),
        arrow(212, 56, 244, 56, stroke=PRIM), packet(272, 56, 13, 6.5, 13),
        arrow(160, 84, 160, 108, stroke=MID),
        table_card(66, 116, 188, 92, rows=4, accent_row=2, bar=False),
    ]
    return body, "A router deciding each packet's next hop from its table"


def static_vs_dynamic_routing():
    """A route placed by hand; routes learned by talking."""
    body = [
        router(84, 66, 74, 30),
        pin(84, 122, 0.9),
        line(84, 140, 84, 160, stroke=MID, dash="5 5"),
        node(84, 176, 6, TINT),
        router(236, 52, 74, 28),
        router(236, 158, 74, 28),
        curve_arrow(216, 70, 216, 142, bow=18, stroke=PRIM, head=6),
        curve_arrow(256, 142, 256, 70, bow=18, stroke=PRIM, head=6),
        node(236, 208, 6, TINT),
        line(236, 174, 236, 200, stroke=MID),
        line(160, 34, 160, 206, stroke=MID, sw=1.4, dash="4 6"),
    ]
    return body, "A hand-placed route beside routers learning routes from each other"


def rip():
    """Distance measured in hops, nothing else."""
    body = [
        router(50, 84, 62, 26), router(160, 84, 62, 26), router(270, 84, 62, 26),
        arrow(84, 84, 126, 84, stroke=PRIM), arrow(194, 84, 236, 84, stroke=PRIM),
        node(50, 150, 6, MID),
        node(148, 150, 6, MID), node(172, 150, 6, MID),
        node(246, 150, 6, MID), node(270, 150, 6, MID), node(294, 150, 6, MID),
    ]
    return body, "Routes chosen purely by counting the hops to the destination"


def ospf():
    """Every link has a cost; the cheapest path wins."""
    body = [
        dashed_boundary(22, 40, 276, 160, r=14),
        router(72, 74, 64, 26), router(248, 74, 64, 26),
        router(72, 164, 64, 26), router(248, 164, 64, 26),
        line(104, 74, 216, 74, stroke=PRIM, sw=SW * 1.8),
        line(248, 88, 248, 150, stroke=PRIM, sw=SW * 1.8),
        line(72, 88, 72, 150, stroke=MID, dash="6 5"),
        line(104, 164, 216, 164, stroke=MID, dash="6 5"),
        line(96, 92, 224, 148, stroke=MID, dash="6 5"),
        bit_ruler(128, 88, 64, bits=4, on=1, h=12),
        bit_ruler(128, 138, 64, bits=4, on=3, h=12),
    ]
    return body, "Link costs across an area with the cheapest path highlighted"


def bgp():
    """Two independent networks agreeing to carry each other's traffic."""
    body = [
        cloud(80, 78, 104),
        router(80, 82, 62, 24),
        cloud(240, 78, 104),
        router(240, 82, 62, 24),
        curve_arrow(112, 70, 208, 70, bow=20, stroke=PRIM, head=6),
        curve_arrow(208, 94, 112, 94, bow=20, stroke=DARK, head=6, dash="6 5"),
        globe(160, 178, 30),
        line(96, 108, 138, 160, stroke=MID), line(224, 108, 182, 160, stroke=MID),
    ]
    return body, "Two separate networks peering to exchange reachability"


def default_gateway():
    """When you don't know the way, use the one door out."""
    body = [
        dashed_boundary(24, 96, 200, 116),
        laptop(66, 152, 0.44), laptop(124, 152, 0.44), laptop(182, 152, 0.44),
        arrow(66, 132, 108, 84, stroke=MID),
        arrow(124, 132, 124, 84, stroke=MID),
        arrow(182, 132, 140, 84, stroke=MID),
        router(124, 62, 76, 30),
        globe(258, 62, 26),
        arrow(164, 62, 226, 62, stroke=PRIM),
    ]
    return body, "Every host sending unknown destinations to one exit router"


def route_summarization():
    """Many adjacent blocks advertised as one."""
    body = [
        rr(38, 62, 68, 24, 4, SURF), pill(48, 70, 48, 8, MID),
        rr(126, 62, 68, 24, 4, SURF), pill(136, 70, 48, 8, MID),
        rr(214, 62, 68, 24, 4, SURF), pill(224, 70, 48, 8, MID),
        arrow(72, 96, 148, 122, stroke=MID),
        arrow(160, 96, 160, 122, stroke=MID),
        arrow(248, 96, 172, 122, stroke=MID),
        rr(70, 132, 180, 28, 4, TINT), pill(84, 142, 152, 8, PRIM),
        router(160, 194, 82, 30),
        line(160, 160, 160, 179, stroke=MID),
    ]
    return body, "Several neighbouring blocks advertised as one larger block"


def inter_vlan_routing():
    """Two groups that can only reach each other through the router."""
    body = [
        router(160, 50, 80, 28),
        # the trunk: one link up to the router and back down again
        arrow(148, 112, 148, 68, stroke=PRIM, head=6),
        arrow(172, 68, 172, 112, stroke=MID, head=6),
        switch_dev(160, 128, 130, 30, ports=8,
                   port_fills=[PRIM, PRIM, PRIM, PRIM, MID, MID, MID, MID]),
        laptop(84, 190, 0.44), laptop(236, 190, 0.44),
        line(112, 144, 92, 166, stroke=PRIM),
        line(208, 144, 228, 166, stroke=MID),
    ]
    return body, "Two port groups reaching each other only via the router above"


def longest_prefix_match():
    """Several routes match; the most specific one is used."""
    body = [
        card(48, 44, 224, 128, bar=False),
        bit_ruler(64, 62, 132, bits=8, on=2, h=16), x_badge(240, 70, 11, MID),
        bit_ruler(64, 96, 132, bits=8, on=4, h=16), x_badge(240, 104, 11, MID),
        bit_ruler(64, 130, 132, bits=8, on=7, h=16), check_badge(240, 138, 11, PRIM),
        arrow(160, 180, 160, 158, stroke=PRIM),
        packet(160, 206, 12, 6, 12),
    ]
    return body, "Three matching routes with the most specific prefix chosen"


def anycast_multicast():
    """One send reaching many; one address answered by the nearest."""
    body = [
        node(46, 62, 9),
        arrow(60, 58, 116, 40, stroke=PRIM), arrow(60, 62, 116, 62, stroke=PRIM),
        arrow(60, 66, 116, 84, stroke=PRIM),
        node(130, 40, 6, TINT), node(130, 62, 6, TINT), node(130, 84, 6, TINT),
        line(160, 34, 160, 206, stroke=MID, sw=1.4, dash="4 6"),
        # anycast: three servers wearing the same address, the nearest answers
        node(46, 160, 9),
        arrow(60, 160, 96, 160, stroke=PRIM, head=6),
        rack(122, 152, 34, 46, slots=2, accent=PRIM),
        chip(122, 192, 40, 14, accent=PRIM),
        rack(190, 152, 34, 46, slots=2, accent=MID),
        chip(190, 192, 40, 14, accent=MID),
        rack(258, 152, 34, 46, slots=2, accent=MID),
        chip(258, 192, 40, 14, accent=MID),
    ]
    return body, "One send reaching many receivers, and one address served by the nearest"


TOPICS = [
    ("routers-and-routing-tables", routers_and_routing_tables),
    ("static-vs-dynamic-routing", static_vs_dynamic_routing),
    ("rip", rip),
    ("ospf", ospf),
    ("bgp", bgp),
    ("default-gateway", default_gateway),
    ("route-summarization", route_summarization),
    ("inter-vlan-routing", inter_vlan_routing),
    ("longest-prefix-match", longest_prefix_match),
    ("anycast-and-multicast", anycast_multicast),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
