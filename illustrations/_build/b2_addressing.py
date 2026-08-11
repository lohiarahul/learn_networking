"""Batch 2 -- Addressing."""

from prims import *  # noqa: F401,F403

OUT = "../02-addressing"


def ipv4_basics():
    body = [
        addr_bar(48, 66, 224, groups=4, h=30),
        line(160, 96, 160, 132, stroke=MID),
        laptop(100, 158, 0.6),
        arrow(146, 152, 194, 152, stroke=PRIM),
        globe(232, 152, 28),
    ]
    return body, "A four part numeric address identifying a host on the network"


def ipv4_subnetting():
    body = [
        rr(48, 54, 224, 26, 4, TINT),
        pill(60, 63, 60, 8, MID), pill(140, 63, 120, 8, MID),
        arrow(160, 90, 160, 112, stroke=PRIM),
        rr(48, 122, 68, 24, 4, SURF), pill(58, 130, 48, 8, PRIM),
        rr(126, 122, 68, 24, 4, SURF), pill(136, 130, 48, 8, PRIM),
        rr(204, 122, 68, 24, 4, SURF), pill(214, 130, 48, 8, PRIM),
        laptop(82, 196, 0.4), laptop(160, 196, 0.4), laptop(238, 196, 0.4),
        line(82, 146, 82, 176, stroke=MID), line(160, 146, 160, 176, stroke=MID),
        line(238, 146, 238, 176, stroke=MID),
    ]
    return body, "One address block divided into three smaller subnets"


def cidr_notation():
    """Address bar with a movable boundary, and the prefix length as bits."""
    body = [
        addr_bar(48, 72, 224, groups=4, h=30, split=3, accent_from=3),
        bit_ruler(48, 132, 224, bits=8, on=6, h=20),
        arrow(216, 172, 216, 156, stroke=PRIM),
        chip(96, 182, 64, 18, accent=PRIM),
    ]
    return body, "An address bar with a prefix boundary and a bit-length ruler"


def subnet_masks():
    body = [
        addr_bar(48, 56, 224, groups=4, h=28, accent_from=3),
        bit_ruler(48, 104, 224, bits=8, on=5, h=20),
        rr(48, 148, 224, 28, 4, TINT),
        pill(60, 158, 128, 8, PRIM), pill(200, 158, 60, 8, MID),
        arrow(34, 70, 34, 158, stroke=MID),
    ]
    return body, "A mask of ones and zeros splitting an address into network and host"


def private_vs_public_ip():
    """Reusable inside addresses; one address that the world sees."""
    body = [
        dashed_boundary(24, 48, 152, 148),
        laptop(62, 82, 0.42), laptop(138, 82, 0.42),
        chip(62, 108, 46, 15), chip(138, 108, 46, 15),
        laptop(62, 152, 0.42), laptop(138, 152, 0.42),
        chip(62, 178, 46, 15), chip(138, 178, 46, 15),
        router(230, 122, 66, 30),
        line(176, 122, 197, 122, stroke=MID),
        chip(230, 158, 60, 18, accent=PRIM),
        globe(230, 62, 22),
        line(230, 84, 230, 107, stroke=MID),
    ]
    return body, "Reusable inside addresses behind one globally routable address"


def ipv6_basics():
    """Eight groups against the old four, for scale."""
    body = [
        addr_bar(28, 58, 264, groups=8, h=32, accent_from=4),
        rr(28, 120, 92, 24, 4, SURF), pill(38, 128, 72, 8, MID),
        arrow(130, 132, 162, 132, stroke=MID),
        chip(232, 132, 72, 22, accent=PRIM),
    ]
    return body, "An eight group address, far larger than the four part one"


def ipv6_address_types():
    """One-to-one, one-to-many, one-of-many."""
    body = [
        node(52, 62, 8), arrow(66, 62, 118, 62, stroke=PRIM), node(132, 62, 8, TINT),
        node(52, 124, 8),
        arrow(66, 120, 118, 104, stroke=PRIM), arrow(66, 124, 118, 124, stroke=PRIM),
        arrow(66, 128, 118, 144, stroke=PRIM),
        node(132, 104, 6, TINT), node(132, 124, 6, TINT), node(132, 144, 6, TINT),
        node(52, 186, 8),
        arrow(66, 186, 112, 186, stroke=PRIM),
        node(126, 186, 6, TINT), node(150, 170, 6, MID), node(150, 202, 6, MID),
        addr_bar(196, 50, 100, groups=4, h=22, accent_from=3),
        addr_bar(196, 112, 100, groups=4, h=22, accent_from=2),
        addr_bar(196, 174, 100, groups=4, h=22, accent_from=1),
    ]
    return body, "Addresses that reach one host, many hosts, or the nearest host"


def mac_addresses():
    """An identity burned into the card itself."""
    body = [
        rr(60, 70, 200, 76, 6, SURF),
        rr(76, 88, 42, 40, 3, TINT),
        dot(88, 100, 2.4, MID), dot(106, 100, 2.4, MID),
        dot(88, 116, 2.4, MID), dot(106, 116, 2.4, MID),
        pill(136, 96, 104, 8, MID), pill(136, 116, 72, 8, MID),
        rr(96, 146, 40, 12, 2, fill=MID, stroke=DARK),
        rr(184, 146, 40, 12, 2, fill=MID, stroke=DARK),
        addr_bar(76, 174, 168, groups=6, h=24, accent_from=3),
    ]
    return body, "A hardware address fixed to a network interface card"


def arp():
    """Broadcast the question to everyone; exactly one host answers."""
    body = [
        laptop(58, 92, 0.5),
        switch_dev(160, 96, 76, 26, ports=5),
        laptop(262, 92, 0.5),
        line(88, 96, 122, 96, stroke=MID), line(198, 96, 232, 96, stroke=MID),
        waves(160, 72, 3, r0=16, step=10, spread=130, stroke=MID),
        curve_arrow(92, 74, 128, 74, bow=12, stroke=PRIM, head=6),
        curve_arrow(228, 116, 192, 116, bow=12, stroke=DARK, dash="6 5", head=6),
        table_card(74, 150, 132, 62, rows=2, accent_row=0, bar=False),
        arrow(210, 180, 236, 180, stroke=MID, head=6),
        tag(266, 180, 44, 22),
    ]
    return body, "A broadcast question about an address that one host answers"


def nat():
    """Three inside addresses folded into one on the way out."""
    body = [
        laptop(48, 60, 0.38), laptop(48, 120, 0.38), laptop(48, 180, 0.38),
        chip(48, 84, 42, 14), chip(48, 144, 42, 14), chip(48, 204, 42, 14),
        arrow(78, 66, 122, 110, stroke=MID),
        arrow(78, 120, 122, 120, stroke=MID),
        arrow(78, 174, 122, 130, stroke=MID),
        router(164, 120, 68, 32),
        arrow(200, 120, 232, 120, stroke=PRIM),
        globe(272, 120, 26),
        chip(240, 172, 60, 18, accent=PRIM),
    ]
    return body, "Several inside addresses translated to a single outside address"


TOPICS = [
    ("ipv4-basics", ipv4_basics),
    ("ipv4-subnetting", ipv4_subnetting),
    ("cidr-notation", cidr_notation),
    ("subnet-masks", subnet_masks),
    ("private-vs-public-ip", private_vs_public_ip),
    ("ipv6-basics", ipv6_basics),
    ("ipv6-address-types", ipv6_address_types),
    ("mac-addresses", mac_addresses),
    ("arp", arp),
    ("nat", nat),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
