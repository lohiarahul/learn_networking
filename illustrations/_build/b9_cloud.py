"""Batch 9 -- Cloud and Modern Networking."""

from prims import *  # noqa: F401,F403

OUT = "../09-cloud-modern"


def cloud_vpcs():
    """Fenced tenant networks living inside the provider's region."""
    body = [
        dashed_boundary(18, 30, 284, 182, r=16, stroke=MID),
        cloud(70, 54, 78),
        router(232, 56, 64, 24),
        dashed_boundary(38, 92, 118, 106, stroke=PRIM),
        rack(72, 124, 30, 38, slots=2), rack(122, 124, 30, 38, slots=2, accent=MID),
        rack(97, 176, 30, 32, slots=2, accent=MID),
        dashed_boundary(166, 92, 118, 106, stroke=MID),
        rack(200, 124, 30, 38, slots=2, accent=MID),
        rack(250, 124, 30, 38, slots=2, accent=MID),
        rack(225, 176, 30, 32, slots=2, accent=MID),
        line(97, 92, 97, 78, stroke=MID), line(225, 92, 225, 78, stroke=MID),
    ]
    return body, "Private fenced networks running inside a shared cloud"


def software_defined_networking():
    """The decisions move out of the boxes and into one place."""
    body = [
        card(96, 34, 128, 56, bar=False),
        gear(160, 62, 18),
        line(120, 90, 66, 128, stroke=PRIM, dash="5 5"),
        line(160, 90, 160, 128, stroke=PRIM, dash="5 5"),
        line(200, 90, 254, 128, stroke=PRIM, dash="5 5"),
        switch_dev(66, 148, 68, 24, ports=4),
        switch_dev(160, 148, 68, 24, ports=4),
        switch_dev(254, 148, 68, 24, ports=4),
        line(100, 148, 126, 148, stroke=MID), line(194, 148, 220, 148, stroke=MID),
        packet(66, 196, 10, 5, 10), packet(160, 196, 10, 5, 10),
        packet(254, 196, 10, 5, 10),
    ]
    return body, "Forwarding decisions taken by one controller above the switches"


def containers_and_container_networking():
    """Each container in its own namespace, all sharing one host bridge."""
    body = [rr(36, 34, 248, 140, 8, SURF)]
    for cx in (90, 160, 230):
        body += [
            dashed_boundary(cx - 27, 48, 54, 54, r=8, stroke=MID, dash="5 4"),
            packet(cx, 75, 15, 7.5, 15),
            line(cx, 102, cx, 122, stroke=MID),
        ]
    body += [
        switch_dev(160, 138, 176, 26, ports=6,
                   port_fills=[PRIM, MID, PRIM, MID, PRIM, MID]),
        line(160, 174, 160, 190, stroke=MID),
        router(160, 204, 64, 24),
    ]
    return body, "Isolated containers sharing one host bridge to reach the network"


def kubernetes_networking():
    """Pods come and go; the address in front of them does not."""
    body = [
        dashed_boundary(26, 30, 268, 148, r=14),
        hexagon(72, 74, 22), hexagon(126, 74, 22), hexagon(180, 74, 22),
        packet(72, 74, 9, 4.5, 9), packet(126, 74, 9, 4.5, 9),
        packet(180, 74, 9, 4.5, 9),
        rr(56, 126, 140, 24, 12, TINT), pill(72, 135, 108, 7, PRIM),
        line(72, 98, 96, 126, stroke=MID), line(126, 98, 126, 126, stroke=MID),
        line(180, 98, 156, 126, stroke=MID),
        router(248, 74, 62, 24),
        line(214, 74, 228, 74, stroke=MID),
        # the client stands outside the cluster it is calling into
        laptop(126, 210, 0.42),
        arrow(126, 188, 126, 154, stroke=PRIM, head=6),
    ]
    return body, "Short-lived pods reached through one stable service address"


def edge_computing():
    """Do the work near the person, not in a distant building."""
    body = [
        cloud(160, 58, 116),
        rack(160, 62, 30, 34, slots=2, accent=MID),
        line(120, 84, 74, 122, stroke=MID, dash="6 5"),
        line(200, 84, 246, 122, stroke=MID, dash="6 5"),
        rack(66, 146, 34, 42, slots=2, accent=PRIM),
        rack(254, 146, 34, 42, slots=2, accent=PRIM),
        phone(120, 188, 0.72),
        laptop(214, 192, 0.5),
        arrow(86, 168, 102, 180, stroke=PRIM, head=6),
        arrow(234, 166, 226, 178, stroke=PRIM, head=6),
    ]
    return body, "Compute placed at the edge, close to the people using it"


def network_automation():
    """One description, applied everywhere, the same way every time."""
    body = [
        card(112, 34, 96, 68, bar=False),
        pill(126, 52, 68, 7, PRIM), pill(126, 68, 52, 7, MID),
        pill(126, 84, 60, 7, MID),
        gear(248, 68, 20),
        arrow(212, 68, 226, 68, stroke=MID, head=5),
        arrow(160, 106, 160, 128, stroke=PRIM, head=6),
        switch_dev(70, 158, 68, 24, ports=4),
        switch_dev(160, 158, 68, 24, ports=4),
        switch_dev(250, 158, 68, 24, ports=4),
        line(70, 140, 250, 140, stroke=MID),
        line(70, 140, 70, 146, stroke=MID), line(160, 140, 160, 146, stroke=MID),
        line(250, 140, 250, 146, stroke=MID),
        check_badge(70, 200, 11, PRIM), check_badge(160, 200, 11, PRIM),
        check_badge(250, 200, 11, PRIM),
    ]
    return body, "One declared configuration applied identically to every device"


def api_gateways():
    """One front door for many services behind it."""
    body = [
        laptop(50, 112, 0.44),
        arrow(82, 106, 112, 106, stroke=PRIM, head=6),
        rr(120, 60, 44, 96, 6, TINT),
        pill(130, 76, 24, 7, PRIM), pill(130, 100, 24, 7, PRIM),
        pill(130, 124, 24, 7, PRIM),
        arrow(166, 76, 210, 62, stroke=MID, head=5),
        arrow(166, 104, 210, 114, stroke=MID, head=5),
        arrow(166, 130, 210, 168, stroke=MID, head=5),
        rack(240, 62, 32, 40, slots=2), rack(240, 122, 32, 40, slots=2, accent=MID),
        rack(240, 182, 32, 40, slots=2, accent=MID),
    ]
    return body, "One gateway fronting many services behind it"


def service_mesh():
    """Every service gets a helper that handles the talking."""
    body = [
        rr(46, 52, 92, 60, 6, SURF), rr(52, 58, 46, 48, 4, TINT),
        rr(104, 58, 28, 48, 4, fill=PRIM, stroke=DARK),
        rr(182, 52, 92, 60, 6, SURF), rr(188, 58, 46, 48, 4, TINT),
        rr(240, 58, 28, 48, 4, fill=PRIM, stroke=DARK),
        rr(114, 148, 92, 60, 6, SURF), rr(120, 154, 46, 48, 4, TINT),
        rr(172, 154, 28, 48, 4, fill=PRIM, stroke=DARK),
        line(132, 82, 240, 82, stroke=PRIM, dash="6 5"),
        line(118, 112, 178, 148, stroke=PRIM, dash="6 5"),
        line(250, 112, 196, 148, stroke=PRIM, dash="6 5"),
    ]
    return body, "Each service paired with a sidecar that handles its traffic"


TOPICS = [
    ("cloud-vpcs", cloud_vpcs),
    ("software-defined-networking", software_defined_networking),
    ("containers-and-container-networking", containers_and_container_networking),
    ("kubernetes-networking", kubernetes_networking),
    ("edge-computing", edge_computing),
    ("network-automation", network_automation),
    ("api-gateways", api_gateways),
    ("service-mesh", service_mesh),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
