"""Batch 7 -- Security."""

from prims import *  # noqa: F401,F403

OUT = "../07-security"


def firewalls_stateful_stateless():
    """Judged rule by rule; or judged against a remembered conversation."""
    body = [
        brick_wall(140, 34, 40, 76, rows=4),
        packet(62, 52, 11, 5.5, 11), arrow(84, 52, 130, 52, stroke=PRIM, head=6),
        check_badge(212, 52, 12, PRIM),
        packet(62, 92, 11, 5.5, 11), arrow(84, 92, 130, 92, stroke=MID, head=6),
        x_badge(212, 92, 12, MID),
        line(24, 126, 296, 126, stroke=MID, sw=1.4, dash="4 6"),
        brick_wall(140, 146, 40, 68, rows=4),
        packet(62, 180, 11, 5.5, 11), arrow(84, 180, 130, 180, stroke=PRIM, head=6),
        table_card(196, 148, 88, 64, rows=3, accent_row=0, bar=False),
        curve_arrow(196, 168, 182, 172, bow=6, stroke=DARK, dash="5 4", head=5),
    ]
    return body, "A wall judging each packet alone, then one judging it in context"


def acls():
    """An ordered list of permits and denies."""
    body = [
        packet(48, 118, 13, 6.5, 13), arrow(74, 118, 104, 118, stroke=PRIM, head=6),
        card(112, 44, 152, 148, bar=False),
        pill(128, 66, 84, 7, MID), check_badge(240, 70, 11, PRIM),
        pill(128, 102, 68, 7, MID), x_badge(240, 106, 11, MID),
        pill(128, 138, 92, 7, MID), x_badge(240, 142, 11, MID),
        pill(128, 174, 74, 7, PRIM), check_badge(240, 178, 11, PRIM),
        line(112, 84, 264, 84, stroke=MID, sw=1.4),
        line(112, 120, 264, 120, stroke=MID, sw=1.4),
        line(112, 156, 264, 156, stroke=MID, sw=1.4),
    ]
    return body, "An ordered list of rules permitting or denying each packet"


def vpns():
    """Two offices joined; then one person joined."""
    body = [
        dashed_boundary(24, 42, 76, 62), rack(62, 72, 32, 40, slots=2),
        dashed_boundary(220, 42, 76, 62), rack(258, 72, 32, 40, slots=2),
        pipe(100, 62, 120, 22),
        padlock(160, 73, 0.52),
        line(24, 124, 296, 124, stroke=MID, sw=1.4, dash="4 6"),
        laptop(58, 176, 0.46),
        pipe(96, 166, 124, 22),
        padlock(158, 177, 0.52),
        dashed_boundary(226, 146, 70, 62), rack(261, 177, 32, 40, slots=2),
    ]
    return body, "An encrypted tunnel between two sites, and one for a single user"


def tls_ssl_handshake():
    """Agree on a cipher, prove identity, then lock the channel."""
    body = [
        laptop(58, 50, 0.44), rack(262, 52, 40, 48, slots=3),
        lifeline(58, 74, 196), lifeline(262, 80, 196),
        arrow(70, 98, 250, 98, stroke=PRIM, head=6),
        arrow(250, 128, 70, 128, stroke=DARK, head=6),
        tag(160, 112, 46, 20, fill=TINT),
        arrow(70, 164, 250, 164, stroke=PRIM, head=6),
        key(112, 150, 0.7),
        padlock(160, 200, 0.72),
    ]
    return body, "Keys and a certificate exchanged before the channel is locked"


def https():
    """The everyday lock in the address bar."""
    body = [
        card(56, 44, 208, 148),
        padlock(86, 80, 0.46),
        pill(106, 77, 126, 7, MID),
        rr(76, 100, 168, 78, 4, TINT, stroke=None),
        pill(92, 116, 92, 7, MID), pill(92, 136, 132, 7, MID),
        pill(92, 156, 70, 7, PRIM),
        globe(160, 214, 18),
    ]
    return body, "A page fetched over a channel that is locked end to end"


def ipsec():
    """The original packet, sealed inside another one."""
    body = [
        packet(60, 78, 16, 8, 16),
        arrow(88, 78, 122, 78, stroke=MID, head=6),
        shield(178, 78, 76),
        packet(178, 78, 12, 6, 12),
        arrow(224, 78, 258, 78, stroke=PRIM, head=6),
        pipe(52, 152, 216, 30),
        padlock(88, 167, 0.5),
        packet(160, 167, 11, 5.5, 11), packet(216, 167, 11, 5.5, 11),
    ]
    return body, "A packet sealed inside a protected outer packet for transit"


def zero_trust_networking():
    """No inside. Everything proves itself, every time."""
    body = [
        dashed_boundary(30, 40, 260, 168, r=14, stroke=MID, dash="3 7"),
        x_badge(290, 40, 13, MID),
        laptop(96, 82, 0.4), padlock(96, 114, 0.44),
        rack(224, 78, 32, 40, slots=2), padlock(224, 114, 0.44),
        laptop(96, 158, 0.4), padlock(96, 190, 0.44),
        rack(224, 154, 32, 40, slots=2), padlock(224, 190, 0.44),
        line(120, 96, 200, 96, stroke=MID, dash="5 5"),
        line(120, 172, 200, 172, stroke=MID, dash="5 5"),
        line(160, 110, 160, 158, stroke=MID, dash="5 5"),
    ]
    return body, "No trusted interior: every party authenticates for every request"


def network_segmentation():
    """Three zones in a row, a checkpoint on each path between them."""
    body = [
        dashed_boundary(20, 76, 72, 92, stroke=PRIM),
        laptop(56, 102, 0.4), laptop(56, 144, 0.4),
        brick_wall(98, 96, 20, 52, rows=3),
        dashed_boundary(120, 76, 72, 92, stroke=MID),
        rack(156, 122, 30, 54, slots=3, accent=MID),
        brick_wall(198, 96, 20, 52, rows=3),
        dashed_boundary(220, 76, 72, 92, stroke=MID),
        rack(256, 122, 30, 54, slots=3, accent=MID),
    ]
    return body, "Separate zones with a checkpoint on every path between them"


def ddos_attacks():
    """Enough traffic that nothing legitimate gets through."""
    body = [
        node(40, 50, 6, MID), node(40, 82, 6, MID), node(40, 114, 6, MID),
        node(40, 146, 6, MID), node(40, 178, 6, MID),
        arrow(52, 50, 150, 100, stroke=MID, head=5),
        arrow(52, 82, 150, 106, stroke=MID, head=5),
        arrow(52, 114, 150, 112, stroke=MID, head=5),
        arrow(52, 146, 150, 118, stroke=MID, head=5),
        arrow(52, 178, 150, 124, stroke=MID, head=5),
        rack(190, 112, 48, 72, slots=3, accent=PRIM),
        x_badge(190, 176, 13, MID),
        rr(238, 78, 22, 68, 4, SURF),
        rr(241, 84, 16, 56, 2, fill=PRIM, stroke=None),
        laptop(268, 182, 0.46),
        line(232, 150, 258, 164, stroke=MID, dash="5 5"),
    ]
    return body, "A target swamped by traffic until real requests cannot land"


def man_in_the_middle_attacks():
    """The conversation still works. It just goes through someone else."""
    body = [
        laptop(52, 78, 0.46), laptop(268, 78, 0.46),
        line(88, 72, 232, 72, stroke=MID, dash="5 6"),
        x_badge(160, 72, 12, MID),
        node(160, 140, 11, PRIM),
        arrow(84, 92, 146, 130, stroke=PRIM, head=6),
        arrow(174, 130, 236, 92, stroke=PRIM, head=6),
        magnifier(160, 180, 14),
        line(160, 152, 160, 164, stroke=MID, dash="4 4"),
    ]
    return body, "Traffic quietly rerouted through a third party who can read it"


def port_scanning():
    """Knock on every door and note which ones answer."""
    body = [
        rr(150, 40, 60, 168, 6, SURF),
        rr(160, 56, 40, 12, 2, fill=PRIM, stroke=None),
        rr(160, 82, 40, 12, 2, fill=MID, stroke=None),
        rr(160, 108, 40, 12, 2, fill=PRIM, stroke=None),
        rr(160, 134, 40, 12, 2, fill=MID, stroke=None),
        rr(160, 160, 40, 12, 2, fill=MID, stroke=None),
        rr(160, 186, 40, 12, 2, fill=MID, stroke=None),
        arrow(96, 62, 142, 62, stroke=MID, head=5),
        arrow(96, 88, 142, 88, stroke=MID, head=5),
        arrow(96, 114, 142, 114, stroke=MID, head=5),
        arrow(96, 140, 142, 140, stroke=MID, head=5),
        magnifier(72, 118, 17),
        check_badge(238, 62, 11, PRIM), check_badge(238, 114, 11, PRIM),
        x_badge(238, 88, 11, MID), x_badge(238, 140, 11, MID),
    ]
    return body, "Every port probed in turn to see which ones answer"


def ids_ips():
    """One watches a copy; the other stands in the road."""
    body = [
        # watching a copy: traffic passes, a tap feeds the sensor
        node(40, 58, 7, MID), arrow(52, 58, 122, 58, stroke=PRIM, head=6),
        node(140, 58, 7, MID), arrow(152, 58, 236, 58, stroke=PRIM, head=6),
        node(254, 58, 7, MID),
        line(140, 70, 140, 92, stroke=MID, dash="5 5"),
        card(100, 92, 120, 48, bar=False),
        magnifier(150, 114, 13),
        pill(176, 111, 32, 6, MID),
        line(24, 156, 296, 156, stroke=MID, sw=1.4, dash="4 6"),
        # standing in the path: it can stop the traffic itself
        node(44, 192, 7, MID), arrow(56, 192, 122, 192, stroke=PRIM, head=6),
        brick_wall(132, 168, 32, 48, rows=3),
        x_badge(202, 192, 12, MID),
    ]
    return body, "One sensor watching a copy of the traffic, one sitting in its path"


TOPICS = [
    ("firewalls-stateful-vs-stateless", firewalls_stateful_stateless),
    ("acls", acls),
    ("vpns", vpns),
    ("tls-ssl-handshake", tls_ssl_handshake),
    ("https", https),
    ("ipsec", ipsec),
    ("zero-trust-networking", zero_trust_networking),
    ("network-segmentation", network_segmentation),
    ("ddos-attacks", ddos_attacks),
    ("man-in-the-middle-attacks", man_in_the_middle_attacks),
    ("port-scanning", port_scanning),
    ("ids-ips", ids_ips),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
