"""Batch 6 -- Core Services."""

from prims import *  # noqa: F401,F403

OUT = "../06-core-services"


def dns_resolution():
    """Ask, get pointed further up, ask again, get the answer."""
    body = [
        laptop(52, 108, 0.48),
        arrow(84, 100, 116, 100, stroke=PRIM, head=6),
        rack(148, 112, 46, 66, slots=3),
        chip(52, 160, 62, 18, accent=PRIM),
        # the chain up the hierarchy, asked in order
        arrow(174, 92, 230, 66, stroke=PRIM, head=6),
        rack(256, 56, 34, 40, slots=2, accent=MID),
        arrow(256, 80, 256, 106, stroke=MID, head=6),
        rack(256, 126, 34, 40, slots=2, accent=MID),
        arrow(256, 150, 256, 176, stroke=MID, head=6),
        rack(256, 196, 34, 40, slots=2, accent=MID),
        curve_arrow(234, 200, 176, 148, bow=-20, stroke=DARK, dash="6 5", head=6),
        curve_arrow(124, 132, 74, 132, bow=0, stroke=DARK, dash="6 5", head=6),
    ]
    return body, "A name looked up by asking servers up the hierarchy"


def dns_record_types():
    """Different kinds of answer for the same kind of question."""
    body = [
        card(58, 40, 204, 160, bar=False),
        tag(96, 68, 44, 20, fill=PRIM), pill(142, 65, 96, 7, MID),
        tag(96, 104, 44, 20, fill=TINT), pill(142, 101, 72, 7, MID),
        tag(96, 140, 44, 20, fill=MID), pill(142, 137, 88, 7, MID),
        tag(96, 176, 44, 20, fill=TINT), pill(142, 173, 60, 7, MID),
    ]
    return body, "Several kinds of record answering the same kind of question"


def dhcp():
    """A new arrival is handed its settings."""
    body = [
        laptop(64, 84, 0.5), rack(252, 88, 44, 62, slots=3),
        lifeline(64, 112, 176), lifeline(252, 124, 176),
        arrow(80, 132, 236, 132, stroke=PRIM, head=6),
        arrow(236, 152, 80, 152, stroke=DARK, head=6),
        arrow(80, 172, 236, 172, stroke=PRIM, head=6),
        arrow(236, 192, 80, 192, stroke=DARK, head=6),
        chip(64, 216, 72, 20, accent=PRIM),
    ]
    return body, "A newly joined host handed its addressing settings"


def ntp():
    """Everyone agreeing what time it is."""
    body = [
        clock(160, 72, 30),
        arrow(136, 96, 84, 134, stroke=PRIM, head=6),
        arrow(160, 104, 160, 138, stroke=PRIM, head=6),
        arrow(184, 96, 236, 134, stroke=PRIM, head=6),
        clock(70, 164, 22), clock(160, 164, 22), clock(250, 164, 22),
    ]
    return body, "Clients pulling the same time from an authoritative clock"


def load_balancing():
    """One address in front, several servers behind."""
    body = [
        globe(52, 108, 24),
        arrow(80, 108, 116, 108, stroke=PRIM, head=7),
        rr(126, 74, 40, 68, 6, TINT),
        dot(146, 92, 3.4, PRIM), dot(146, 108, 3.4, PRIM), dot(146, 124, 3.4, PRIM),
        arrow(168, 92, 208, 62, stroke=MID, head=6),
        arrow(168, 108, 208, 108, stroke=MID, head=6),
        arrow(168, 124, 208, 154, stroke=MID, head=6),
        rack(240, 62, 36, 44, slots=2), rack(240, 122, 36, 44, slots=2, accent=MID),
        rack(240, 182, 36, 44, slots=2, accent=MID),
    ]
    return body, "One front address spreading requests over several servers"


def proxy_servers():
    """Nothing talks to the far side directly."""
    body = [
        laptop(58, 112, 0.5),
        arrow(94, 106, 122, 106, stroke=PRIM, head=6),
        card(126, 68, 68, 88, bar=False),
        rr(140, 84, 40, 24, 3, TINT), pill(140, 122, 40, 7, PRIM),
        pill(140, 136, 26, 7, MID),
        arrow(198, 106, 228, 106, stroke=PRIM, head=6),
        globe(266, 106, 26),
        curve_arrow(228, 134, 198, 134, bow=10, stroke=DARK, dash="6 5", head=5),
        curve_arrow(122, 134, 94, 134, bow=10, stroke=DARK, dash="6 5", head=5),
    ]
    return body, "A middleman relaying every request on the client's behalf"


def reverse_vs_forward_proxy():
    """Which side the middleman is standing in front of."""
    body = [
        laptop(48, 54, 0.42), laptop(48, 100, 0.42),
        arrow(74, 54, 106, 68, stroke=MID, head=5),
        arrow(74, 100, 106, 84, stroke=MID, head=5),
        proxy_box(130, 76, 38, 50),
        arrow(152, 76, 214, 76, stroke=PRIM, head=6),
        globe(252, 76, 22),
        line(24, 120, 296, 120, stroke=MID, sw=1.4, dash="4 6"),
        globe(52, 168, 22),
        arrow(78, 168, 142, 168, stroke=PRIM, head=6),
        proxy_box(164, 168, 38, 50),
        arrow(186, 158, 220, 146, stroke=MID, head=5),
        arrow(186, 178, 220, 190, stroke=MID, head=5),
        rack(248, 146, 32, 38, slots=2), rack(248, 194, 32, 38, slots=2, accent=MID),
    ]
    return body, "A middleman in front of the clients, then one in front of the servers"


def cdns():
    """Copies kept near the people asking."""
    body = [
        globe(160, 108, 34),
        rack(60, 66, 32, 38, slots=2, accent=MID),
        rack(260, 66, 32, 38, slots=2, accent=MID),
        rack(60, 168, 32, 38, slots=2, accent=PRIM),
        rack(260, 168, 32, 38, slots=2, accent=MID),
        line(92, 80, 130, 96, stroke=MID, dash="6 5"),
        line(228, 80, 190, 96, stroke=MID, dash="6 5"),
        line(92, 158, 130, 122, stroke=MID, dash="6 5"),
        line(228, 158, 190, 122, stroke=MID, dash="6 5"),
        laptop(160, 194, 0.5),
        arrow(84, 194, 132, 194, stroke=PRIM, head=6),
    ]
    return body, "Cached copies held at edge locations near the audience"


TOPICS = [
    ("dns-resolution", dns_resolution),
    ("dns-record-types", dns_record_types),
    ("dhcp", dhcp),
    ("ntp", ntp),
    ("load-balancing", load_balancing),
    ("proxy-servers", proxy_servers),
    ("reverse-proxy-vs-forward-proxy", reverse_vs_forward_proxy),
    ("cdns", cdns),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
