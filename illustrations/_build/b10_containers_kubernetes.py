"""Batch 10 -- Containers and Kubernetes."""

from prims import *  # noqa: F401,F403

import os
OUT = os.environ.get("ILLO_OUT", "../10-containers-and-kubernetes")


def namespaces():
    """One kernel, several private network stacks that cannot see each other."""
    body = [
        rr(28, 28, 264, 168, 10, SURF),
        dashed_boundary(46, 48, 104, 132, r=10, stroke=PRIM),
        dashed_boundary(170, 48, 104, 132, r=10, stroke=MID),
        router(98, 100, 60, 24),
        router(222, 100, 60, 24, accent=MID),
        node(98, 150, 5, PRIM), node(222, 150, 5, MID),
        x_badge(160, 100, 13, MID),
    ]
    return body, "One kernel holding two private network stacks that cannot see each other"


def cgroups():
    """Namespace narrows the view; cgroup caps the share -- two subsystems on one kernel."""
    body = [
        rr(28, 28, 264, 168, 10, SURF),
        line(160, 44, 160, 180, stroke=MID, dash="5 5"),
        dashed_boundary(44, 58, 96, 124, r=10, stroke=PRIM),
        router(92, 120, 54, 22),
        pipe(182, 148, 104, 22, fill=BG),
        pipe(182, 148, 62, 22, fill=PRIM),
        line(244, 138, 244, 174, stroke=DARK, sw=2.2, dash="4 4"),
    ]
    return body, "Namespace narrows what a process can see; cgroup caps how much it can use"


def vxlan_encap():
    """The whole original packet becomes cargo inside a new outer packet for the tunnel."""
    body = [
        router(56, 120, 56, 24),
        router(264, 120, 56, 24, accent=MID),
        dashed_boundary(96, 62, 128, 118, r=12, stroke=MID),
        frame(100, 96, 120, 48, head=22, tail=16, fill=TINT),
        packet(160, 120, 10, 5, 10),
        line(84, 120, 96, 120, stroke=MID), line(224, 120, 236, 120, stroke=MID),
    ]
    return body, "An original packet carried whole as cargo inside a new outer packet through the tunnel"


def cni_cross_node():
    """Two nodes wire pods the same way locally; only the path between them differs."""
    body = [
        rr(20, 30, 120, 150, 8, SURF),
        packet(80, 56, 9, 4.5, 9),
        line(80, 68, 80, 86, stroke=MID),
        switch_dev(80, 100, 90, 24, ports=4),
        line(80, 118, 80, 148, stroke=MID),
        router(80, 160, 56, 22),
        rr(180, 30, 120, 150, 8, SURF),
        packet(240, 56, 9, 4.5, 9),
        line(240, 68, 240, 86, stroke=MID),
        switch_dev(240, 100, 90, 24, ports=4, accent=MID),
        line(240, 118, 240, 148, stroke=MID),
        router(240, 160, 56, 22, accent=MID),
        curve_arrow(108, 165, 212, 165, bow=-30, stroke=PRIM, head=6),
    ]
    return body, "Two nodes wiring pods identically, joined by one path between them"


def coredns_ndots():
    """A bare name tried against each entry in a search list until one query resolves."""
    body = [
        chip(56, 56, 64, 20),
        table_card(28, 88, 112, 112, rows=3, accent_row=2),
        arrow(142, 100, 178, 72, stroke=MID, head=5, dash="4 4"),
        arrow(142, 132, 178, 132, stroke=MID, head=5, dash="4 4"),
        arrow(142, 164, 178, 190, stroke=PRIM, head=5),
        x_badge(192, 72, 11, MID), x_badge(192, 132, 11, MID),
        check_badge(192, 190, 11, PRIM),
        router(254, 132, 56, 24),
        line(228, 132, 240, 132, stroke=MID),
    ]
    return body, "A bare name tried against each entry in a search list until one query resolves"


def pod_networking():
    """Several containers inside one pod share a single network namespace."""
    body = [
        dashed_boundary(50, 40, 220, 150, r=14, stroke=PRIM),
        rr(74, 66, 70, 50, 6, SURF),
        rr(166, 66, 70, 50, 6, SURF),
        rr(120, 140, 70, 34, 6, fill=TINT, stroke=None),
        line(109, 116, 155, 158, stroke=MID),
        line(201, 116, 155, 158, stroke=MID),
        node(155, 158, 5, PRIM),
    ]
    return body, "Several containers inside one pod sharing a single network namespace"


TOPICS = [
    ("namespaces", namespaces),
    ("cgroups", cgroups),
    ("vxlan-encap", vxlan_encap),
    ("cni-cross-node", cni_cross_node),
    ("coredns-ndots", coredns_ndots),
    ("pod-networking", pod_networking),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
