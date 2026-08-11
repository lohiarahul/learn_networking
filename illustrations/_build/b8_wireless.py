"""Batch 8 -- Wireless."""

from prims import *  # noqa: F401,F403

OUT = "../08-wireless"


def wifi_standards_80211():
    """Successive generations, each carrying more."""
    body = [
        access_point(160, 76, 1.0),
        rr(72, 130, 176, 22, 4, SURF), pill(82, 138, 40, 7, MID),
        rr(72, 158, 176, 22, 4, SURF), pill(82, 166, 84, 7, MID),
        rr(72, 186, 176, 22, 4, TINT), pill(82, 194, 148, 7, PRIM),
    ]
    return body, "Successive wireless generations, each carrying more than the last"


def ssid_and_channels():
    """One name on the air; a choice of lane underneath it."""
    """One name on the air, sitting in one of several radio lanes."""
    heights = [18, 46, 10, 56, 26]
    body = [
        access_point(160, 66, 0.9),
        chip(160, 108, 76, 20, accent=PRIM),
        line(34, 206, 286, 206, stroke=MID, sw=1.8),
    ]
    for i, hh in enumerate(heights):
        x = 48 + i * 46
        body.append(rr(x, 138, 34, 66, 4, SURF))
        body.append(rr(x + 5, 199 - hh, 24, hh, 2,
                       fill=PRIM if hh > 40 else MID, stroke=None))
    return body, "One network name broadcast in one of several radio channels"


def wpa2_wpa3():
    """Two generations of the same promise, one stronger."""
    body = [
        access_point(160, 62, 0.82),
        shield(96, 152, 74, fill=SURF),
        padlock(96, 150, 0.66, fill=MID),
        shield(224, 152, 74, fill=TINT),
        padlock(224, 148, 0.66, fill=PRIM),
        key(224, 198, 0.56),
        line(132, 88, 106, 118, stroke=MID),
        line(188, 88, 214, 118, stroke=PRIM),
    ]
    return body, "Two generations of wireless encryption, the newer one stronger"


def wireless_interference():
    """Two radios shouting over each other."""
    body = [
        access_point(74, 84, 0.72, wave=False),
        waves(96, 84, 3, r0=16, step=13, spread=100, rot=0, stroke=MID),
        access_point(246, 84, 0.72, wave=False),
        waves(224, 84, 3, r0=16, step=13, spread=100, rot=180, stroke=MID),
        x_badge(160, 84, 14, MID),
        laptop(160, 182, 0.5),
        line(160, 100, 160, 152, stroke=MID, dash="4 5"),
    ]
    return body, "Two radios overlapping on the same channel and colliding"


def bluetooth_vs_wifi():
    """A short private hop, and a room-sized one."""
    body = [
        phone(70, 76, 0.9),
        waves(96, 76, 2, r0=14, step=11, spread=90, rot=0, stroke=PRIM),
        phone(152, 76, 0.9),
        line(24, 124, 296, 124, stroke=MID, sw=1.4, dash="4 6"),
        access_point(70, 176, 0.78, wave=False),
        waves(96, 176, 5, r0=18, step=17, spread=95, rot=0, stroke=PRIM),
        laptop(232, 176, 0.56),
    ]
    return body, "A short device-to-device link beside a room-sized wireless link"


def mesh_wifi():
    """Several radios covering a space between them."""
    body = [
        dashed_boundary(28, 40, 264, 168, r=14),
        access_point(90, 78, 0.6, wave=False), waves(90, 68, 2, r0=14, step=10),
        access_point(230, 78, 0.6, wave=False), waves(230, 68, 2, r0=14, step=10),
        access_point(160, 168, 0.6, wave=False), waves(160, 158, 2, r0=14, step=10),
        line(112, 88, 208, 88, stroke=MID, dash="6 5"),
        line(100, 100, 148, 158, stroke=MID, dash="6 5"),
        line(220, 100, 172, 158, stroke=MID, dash="6 5"),
        laptop(160, 112, 0.4),
    ]
    return body, "Several radios relaying to each other to cover one space"


TOPICS = [
    ("wifi-standards-802-11", wifi_standards_80211),
    ("ssid-and-channels", ssid_and_channels),
    ("wpa2-wpa3", wpa2_wpa3),
    ("wireless-interference", wireless_interference),
    ("bluetooth-vs-wifi", bluetooth_vs_wifi),
    ("mesh-wifi", mesh_wifi),
]

if __name__ == "__main__":
    for slug, fn in TOPICS:
        body, label = fn()
        print(write(OUT, slug, body, label))
