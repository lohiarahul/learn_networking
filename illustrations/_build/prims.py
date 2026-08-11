"""Shared primitive library for the networking spot illustrations.

Every illustration in illustrations/ is composed from these primitives, so the
whole set shares one palette, one line weight and one shape vocabulary.

Design rules (do not break them per-image):
  * canvas is always 320x240 with a rounded #f1f5f9 plate
  * strokes are always SW (2.2) in DARK, round cap and join
  * small details carry no stroke -- they are fill-only shapes
  * flat vector throughout; the ONLY isometric element is the packet cube
  * no text, no glyphs, no human figures inside the artwork
"""

import math

# ---------------------------------------------------------------- palette ---
BG = "#f1f5f9"      # plate
SURF = "#ffffff"    # device / panel surfaces
TINT = "#dbeafe"    # the one derived colour: a soft wash of PRIM
PRIM = "#3b82f6"    # primary accent
DARK = "#1e293b"    # outlines and dark accents
MID = "#94a3b8"     # mid-tone, secondary matter

W, H = 320, 240
SW = 2.2

# ------------------------------------------------------------- low level ---


def _s(v):
    """Trim floats so the SVG source stays readable."""
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def rr(x, y, w, h, r=5, fill=SURF, stroke=DARK, sw=SW, extra=""):
    st = f'stroke="{stroke}"' if stroke else 'stroke="none"'
    return (
        f'<rect x="{_s(x)}" y="{_s(y)}" width="{_s(w)}" height="{_s(h)}" rx="{_s(r)}" '
        f'fill="{fill or "none"}" {st} stroke-width="{_s(sw)}"{extra}/>'
    )


def circ(cx, cy, r, fill=SURF, stroke=DARK, sw=SW):
    st = f'stroke="{stroke}"' if stroke else 'stroke="none"'
    return (
        f'<circle cx="{_s(cx)}" cy="{_s(cy)}" r="{_s(r)}" fill="{fill or "none"}" '
        f'{st} stroke-width="{_s(sw)}"/>'
    )


def dot(cx, cy, r=3, fill=PRIM):
    return f'<circle cx="{_s(cx)}" cy="{_s(cy)}" r="{_s(r)}" fill="{fill}"/>'


def path(d, fill="none", stroke=DARK, sw=SW, dash=None):
    st = f'stroke="{stroke}"' if stroke else 'stroke="none"'
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill or "none"}" {st} stroke-width="{_s(sw)}"{da}/>'


def line(x1, y1, x2, y2, stroke=DARK, sw=SW, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{_s(x1)}" y1="{_s(y1)}" x2="{_s(x2)}" y2="{_s(y2)}" '
        f'stroke="{stroke}" stroke-width="{_s(sw)}"{da}/>'
    )


def poly(points, fill=SURF, stroke=DARK, sw=SW):
    pts = " ".join(f"{_s(a)},{_s(b)}" for a, b in points)
    st = f'stroke="{stroke}"' if stroke else 'stroke="none"'
    return (
        f'<polygon points="{pts}" fill="{fill or "none"}" {st} '
        f'stroke-width="{_s(sw)}"/>'
    )


def group(body, transform=None, opacity=None):
    at = f' transform="{transform}"' if transform else ""
    op = f' opacity="{opacity}"' if opacity else ""
    return f"<g{at}{op}>{''.join(body)}</g>"


def svg(body, label):
    """Wrap composed primitives in the standard plate + stroke defaults."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" aria-label="{label}">'
        f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>'
        f'<g fill="none" stroke="{DARK}" stroke-width="{SW}" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        f"{''.join(body)}</g></svg>"
    )


# ------------------------------------------------------------------ flow ---


def arrow(x1, y1, x2, y2, stroke=DARK, dash=None, head=7, sw=SW):
    """Straight arrow; the shaft is shortened so the head tip lands on (x2,y2)."""
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - math.cos(ang) * head * 0.92, y2 - math.sin(ang) * head * 0.92
    wing = head * 0.52
    p1 = (x2 - math.cos(ang) * head + math.cos(ang + math.pi / 2) * wing,
          y2 - math.sin(ang) * head + math.sin(ang + math.pi / 2) * wing)
    p2 = (x2 - math.cos(ang) * head - math.cos(ang + math.pi / 2) * wing,
          y2 - math.sin(ang) * head - math.sin(ang + math.pi / 2) * wing)
    return line(x1, y1, bx, by, stroke, sw, dash) + poly(
        [(x2, y2), p1, p2], fill=stroke, stroke=stroke, sw=sw * 0.5
    )


def curve_arrow(x1, y1, x2, y2, bow=28, stroke=DARK, dash=None, head=7, sw=SW):
    """Quadratic arrow bowed perpendicular to the chord by `bow`."""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ang = math.atan2(y2 - y1, x2 - x1)
    cx = mx + math.cos(ang - math.pi / 2) * bow
    cy = my + math.sin(ang - math.pi / 2) * bow
    # tangent at t=1 points from control to end
    tang = math.atan2(y2 - cy, x2 - cx)
    ex, ey = x2 - math.cos(tang) * head * 0.9, y2 - math.sin(tang) * head * 0.9
    wing = head * 0.52
    p1 = (x2 - math.cos(tang) * head + math.cos(tang + math.pi / 2) * wing,
          y2 - math.sin(tang) * head + math.sin(tang + math.pi / 2) * wing)
    p2 = (x2 - math.cos(tang) * head - math.cos(tang + math.pi / 2) * wing,
          y2 - math.sin(tang) * head - math.sin(tang + math.pi / 2) * wing)
    return path(
        f"M{_s(x1)} {_s(y1)} Q{_s(cx)} {_s(cy)} {_s(ex)} {_s(ey)}",
        stroke=stroke, sw=sw, dash=dash,
    ) + poly([(x2, y2), p1, p2], fill=stroke, stroke=stroke, sw=sw * 0.5)


def cable(x1, y1, x2, y2, sag=22, stroke=MID, plug=True):
    """A slack cable: bezier droop with a plug nub at each end."""
    mx = (x1 + x2) / 2
    out = [path(
        f"M{_s(x1)} {_s(y1)} C{_s(mx)} {_s(y1 + sag)} {_s(mx)} {_s(y2 + sag)} "
        f"{_s(x2)} {_s(y2)}", stroke=stroke)]
    if plug:
        out += [rr(x1 - 5, y1 - 3.5, 10, 7, 2.5, fill=DARK, stroke=None),
                rr(x2 - 5, y2 - 3.5, 10, 7, 2.5, fill=DARK, stroke=None)]
    return "".join(out)


def waves(cx, cy, n=3, r0=11, step=9, spread=115, rot=-90, stroke=PRIM, sw=SW):
    """Radiating arcs -- signal, broadcast, radio."""
    out = []
    a0 = math.radians(rot - spread / 2)
    a1 = math.radians(rot + spread / 2)
    for i in range(n):
        r = r0 + i * step
        x1, y1 = cx + math.cos(a0) * r, cy + math.sin(a0) * r
        x2, y2 = cx + math.cos(a1) * r, cy + math.sin(a1) * r
        out.append(path(f"M{_s(x1)} {_s(y1)} A{_s(r)} {_s(r)} 0 0 1 {_s(x2)} {_s(y2)}",
                        stroke=stroke, sw=sw))
    return "".join(out)


# --------------------------------------------------------------- devices ---


def router(cx, cy, w=78, h=34, accent=PRIM):
    """Pill chassis + a four-way arrow cross.

    The pill silhouette carries the identity, so the face stays almost empty --
    anything more turns to mush at spot-illustration scale.
    """
    w = max(w, 62)
    x, y = cx - w / 2, cy - h / 2
    ax, ay = w * 0.26, h * 0.19
    return "".join([
        rr(x, y, w, h, h / 2, SURF),
        # two crossing arrows: traffic handed from one path to another.
        # (A four-way cross was tried first and read as a move cursor.)
        arrow(cx - ax, cy + ay, cx + ax, cy - ay, stroke=accent, head=5.4, sw=2.0),
        arrow(cx + ax, cy + ay, cx - ax, cy - ay, stroke=DARK, head=5.4, sw=2.0),
    ])


def switch_dev(cx, cy, w=94, h=32, ports=8, accent=PRIM, port_fills=None):
    """Rectangular chassis with a port row -- deliberately unlike the router pill.

    `port_fills` recolours individual ports, which is how VLAN membership and
    port state are shown without adding any new shape to the vocabulary.
    """
    x, y = cx - w / 2, cy - h / 2
    out = [rr(x, y, w, h, 5, SURF)]
    pw, gap = 6.5, 4
    total = ports * pw + (ports - 1) * gap
    px = cx - total / 2
    for i in range(ports):
        f = port_fills[i] if port_fills and i < len(port_fills) else MID
        out.append(rr(px + i * (pw + gap), y + h - 12, pw, 7, 1.6, fill=f, stroke=None))
    out += [dot(x + 9, y + 9, 2.4, accent), dot(x + 18, y + 9, 2.4, TINT)]
    return "".join(out)


def hub(cx, cy, w=76, h=26):
    """A dumb repeater: tinted body, ports, no logic lights."""
    x, y = cx - w / 2, cy - h / 2
    out = [rr(x, y, w, h, 4, TINT)]
    for i in range(4):
        out.append(rr(x + 12 + i * 14, y + h - 10, 8, 6, 1.6, fill=MID, stroke=None))
    return "".join(out)


def bridge(cx, cy, w=54, h=26):
    x, y = cx - w / 2, cy - h / 2
    return "".join([
        rr(x, y, w, h, 4, SURF),
        line(x, cy, x - 10, cy), line(x + w, cy, x + w + 10, cy),
        # two ports, not one dark band -- a solid band read as a capacitor symbol
        rr(cx - 11, cy - 3.5, 8, 7, 1.6, fill=MID, stroke=None),
        rr(cx + 3, cy - 3.5, 8, 7, 1.6, fill=PRIM, stroke=None),
    ])


def rack(cx, cy, w=54, h=84, slots=4, accent=PRIM):
    x, y = cx - w / 2, cy - h / 2
    out = [rr(x, y, w, h, 6, SURF)]
    sh = (h - 14) / slots
    for i in range(slots):
        sy = y + 8 + i * sh
        out.append(rr(x + 8, sy, w - 16, sh - 6, 2, fill=TINT, stroke=None))
        out.append(dot(x + w - 13, sy + (sh - 6) / 2, 2.1, accent if i == 0 else MID))
    return "".join(out)


def laptop(cx, cy, s=1.0, screen=TINT):
    """Host. Scaled about its own centre so it drops into any composition."""
    body = [
        rr(-30, -34, 60, 42, 4, SURF),
        rr(-24, -28, 48, 30, 2, fill=screen, stroke=None),
        poly([(-40, 8), (40, 8), (34, 18), (-34, 18)], fill=MID),
    ]
    return group(body, f"translate({_s(cx)} {_s(cy)}) scale({_s(s)})")


def phone(cx, cy, s=1.0):
    body = [rr(-13, -22, 26, 44, 5, SURF),
            rr(-8.5, -17, 17, 30, 1.5, fill=TINT, stroke=None),
            dot(0, 17, 2.1, MID)]
    return group(body, f"translate({_s(cx)} {_s(cy)}) scale({_s(s)})")


def access_point(cx, cy, s=1.0, wave=True):
    """Dome AP, optional radiating arcs above it."""
    body = [
        path("M-22 6 A22 22 0 0 1 22 6 Z", fill=SURF),
        rr(-24, 6, 48, 9, 4, SURF),
        dot(0, 10.5, 2.2, PRIM),
    ]
    out = group(body, f"translate({_s(cx)} {_s(cy)}) scale({_s(s)})")
    if wave:
        out += waves(cx, cy - 16 * s, 3, r0=13 * s, step=10 * s, spread=120)
    return out


def cloud(cx, cy, w=118, fill=SURF):
    """Three-bump cloud, drawn from a unit path so every cloud is the same shape."""
    k = w / 118.0
    d = ("M-40 20 A20 20 0 0 1 -34 -18 A26 26 0 0 1 12 -26 "
         "A21 21 0 0 1 45 -4 A17 17 0 0 1 41 20 Z")
    return group([path(d, fill=fill)],
                 f"translate({_s(cx)} {_s(cy)}) scale({_s(k)})")


def globe(cx, cy, r=30, fill=TINT):
    return "".join([
        circ(cx, cy, r, fill),
        f'<ellipse cx="{_s(cx)}" cy="{_s(cy)}" rx="{_s(r * 0.42)}" ry="{_s(r)}" '
        f'fill="none" stroke="{DARK}" stroke-width="{_s(SW)}"/>',
        path(f"M{_s(cx - r * 0.94)} {_s(cy - r * 0.34)} "
             f"Q{_s(cx)} {_s(cy - r * 0.18)} {_s(cx + r * 0.94)} {_s(cy - r * 0.34)}"),
        path(f"M{_s(cx - r * 0.94)} {_s(cy + r * 0.34)} "
             f"Q{_s(cx)} {_s(cy + r * 0.18)} {_s(cx + r * 0.94)} {_s(cy + r * 0.34)}"),
    ])


def shield(cx, cy, h=66, fill=TINT):
    k = h / 66.0
    d = ("M0 -33 L26 -24 C26 4 16 24 0 33 C-16 24 -26 4 -26 -24 Z")
    return group([path(d, fill=fill)],
                 f"translate({_s(cx)} {_s(cy)}) scale({_s(k)})")


def padlock(cx, cy, s=1.0, closed=True, fill=PRIM):
    shackle = ("M-9 -6 L-9 -13 A9 9 0 0 1 9 -13 L9 -6" if closed
               else "M-9 -6 L-9 -13 A9 9 0 0 1 9 -13 L9 -9")
    body = [path(shackle), rr(-15, -6, 30, 24, 5, fill), dot(0, 6, 3, SURF)]
    return group(body, f"translate({_s(cx)} {_s(cy)}) scale({_s(s)})")


def key(cx, cy, s=1.0, rot=0):
    body = [circ(-10, 0, 8, TINT), line(-2, 0, 18, 0),
            line(12, 0, 12, 6), line(17, 0, 17, 7)]
    return group(body, f"translate({_s(cx)} {_s(cy)}) rotate({rot}) scale({_s(s)})")


def pin(cx, cy, s=1.0, fill=PRIM):
    """A pinned, hand-placed thing: static config, a fixed entry."""
    body = [path("M0 18 L-7 2 A10 10 0 1 1 7 2 Z", fill=fill),
            dot(0, -6, 3.4, SURF)]
    return group(body, f"translate({_s(cx)} {_s(cy)}) scale({_s(s)})")


def brick_wall(x, y, w, h, rows=4, fill=TINT):
    out = [rr(x, y, w, h, 4, fill)]
    rh = h / rows
    for i in range(1, rows):
        out.append(line(x, y + i * rh, x + w, y + i * rh, sw=1.8))
    for i in range(rows):
        off = 0 if i % 2 == 0 else w / 6
        k = 2 if i % 2 == 0 else 3
        for j in range(1, k + 1):
            vx = x + off + j * (w / 3) - (w / 3 if i % 2 else 0)
            if x + 2 < vx < x + w - 2:
                out.append(line(vx, y + i * rh, vx, y + (i + 1) * rh, sw=1.8))
    return "".join(out)


def gear(cx, cy, r=20, teeth=8, fill=TINT):
    pts = []
    for i in range(teeth * 2):
        a = math.pi * 2 * i / (teeth * 2) - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.76
        pts.append((cx + math.cos(a) * rad, cy + math.sin(a) * rad))
    return poly(pts, fill=fill) + circ(cx, cy, r * 0.34, BG)


def magnifier(cx, cy, r=17, rot=45):
    """Inspection. The lens is filled and the grip is long and heavy -- a thin
    short handle on an empty circle read as a lollipop."""
    body = [
        line(r * 0.78, r * 0.78, r * 1.75, r * 1.75, sw=SW * 2.4),
        circ(0, 0, r, TINT, sw=SW * 1.3),
        path(f"M{_s(-r * 0.42)} {_s(-r * 0.1)} A{_s(r * 0.55)} {_s(r * 0.55)} 0 0 1 "
             f"{_s(-r * 0.05)} {_s(-r * 0.45)}", stroke=SURF, sw=SW),
    ]
    return group(body, f"translate({_s(cx)} {_s(cy)}) rotate({rot})")


def clock(cx, cy, r=22, fill=SURF):
    return "".join([circ(cx, cy, r, fill),
                    line(cx, cy, cx, cy - r * 0.55),
                    line(cx, cy, cx + r * 0.42, cy + r * 0.3)])


def hexagon(cx, cy, r=22, fill=TINT):
    pts = [(cx + math.cos(math.radians(60 * i - 30)) * r,
            cy + math.sin(math.radians(60 * i - 30)) * r) for i in range(6)]
    return poly(pts, fill=fill)


# ------------------------------------------------------ data / structures ---


def packet(cx, cy, a=17, b=8.5, c=17):
    """The one isometric element: a packet is always this cube."""
    ty = cy - b - c / 2
    T, R, B, L = (cx, ty), (cx + a, ty + b), (cx, ty + 2 * b), (cx - a, ty + b)
    bot = (cx, ty + 2 * b + c)
    return "".join([
        poly([L, T, R, B], fill=TINT),
        poly([L, B, bot, (cx - a, ty + b + c)], fill=PRIM),
        poly([R, B, bot, (cx + a, ty + b + c)], fill=MID),
    ])


def frame(x, y, w, h=30, head=16, tail=12, fill=TINT):
    """A frame is flat: header band, payload, trailer band."""
    return "".join([
        rr(x, y, w, h, 4, fill),
        rr(x, y, head, h, 4, fill=DARK, stroke=None),
        rr(x + w - tail, y, tail, h, 4, fill=MID, stroke=None),
        rr(x + head - 3, y, 6, h, 0, fill=fill, stroke=None),
        rr(x + w - tail - 3, y, 6, h, 0, fill=fill, stroke=None),
        rr(x, y, w, h, 4, None),
    ])


def pill(x, y, w, h=6, fill=MID):
    """Stand-in for text. Only ever place these INSIDE a container shape --
    a floating pill on the bare plate reads as unloaded skeleton UI."""
    return rr(x, y, w, h, h / 2, fill=fill, stroke=None)


def chip(cx, cy, w=54, h=18, fill=SURF, accent=MID):
    """A small labelled chip: the containerised way to hang an address or name
    off a device without floating a bare pill."""
    return rr(cx - w / 2, cy - h / 2, w, h, h / 2, fill) + pill(
        cx - w / 2 + 7, cy - 3, w - 14, 6, accent)


def card(x, y, w, h, r=8, bar=True, fill=SURF):
    out = [rr(x, y, w, h, r, fill)]
    if bar:
        out.append(line(x, y + 16, x + w, y + 16, sw=1.8))
        for i in range(3):
            out.append(dot(x + 11 + i * 8, y + 8, 2, MID))
    return "".join(out)


def proxy_box(cx, cy, w=38, h=48):
    """A relay that stands between two sides. Given its own small identity so it
    never reads as an empty placeholder rectangle."""
    x, y = cx - w / 2, cy - h / 2
    return "".join([
        rr(x, y, w, h, 5, SURF),
        rr(x + 7, y + 7, w - 14, h * 0.34, 2, fill=TINT, stroke=None),
        pill(x + 7, y + h - 20, w - 14, 6, PRIM),
        pill(x + 7, y + h - 11, (w - 14) * 0.6, 6, MID),
    ])


def table_card(x, y, w, h, rows=3, accent_row=0, bar=True):
    """Routing table, MAC table, DNS zone -- rows of pills, never text."""
    out = [card(x, y, w, h, bar=bar)]
    top = y + (22 if bar else 12)
    step = (h - (top - y) - 10) / max(rows, 1)
    for i in range(rows):
        ry = top + i * step
        out.append(pill(x + 10, ry, (w - 20) * 0.44, 6,
                        PRIM if i == accent_row else MID))
        out.append(pill(x + 10 + (w - 20) * 0.52, ry, (w - 20) * 0.48, 6,
                        TINT if i == accent_row else MID))
    return "".join(out)


def stack(cx, cy, layers, w=132, lh=17, gap=5, accents=(), fills=None):
    """Layered model bars (OSI, TCP/IP). accents = indices drawn in PRIM."""
    total = layers * lh + (layers - 1) * gap
    y0 = cy - total / 2
    out = []
    for i in range(layers):
        f = (fills[i] if fills else (PRIM if i in accents else TINT))
        out.append(rr(cx - w / 2, y0 + i * (lh + gap), w, lh, 3.5, f))
    return "".join(out)


def dashed_boundary(x, y, w, h, r=12, stroke=MID, dash="7 5"):
    return rr(x, y, w, h, r, fill="none", stroke=stroke, sw=SW, extra=f' stroke-dasharray="{dash}"')


def node(cx, cy, r=7, fill=PRIM):
    return circ(cx, cy, r, fill)


def check_badge(cx, cy, r=13, fill=PRIM):
    return circ(cx, cy, r, fill, stroke=DARK) + path(
        f"M{_s(cx - r * 0.42)} {_s(cy)} L{_s(cx - r * 0.08)} {_s(cy + r * 0.34)} "
        f"L{_s(cx + r * 0.46)} {_s(cy - r * 0.34)}", stroke=SURF, sw=SW * 1.1)


def x_badge(cx, cy, r=13, fill=MID):
    k = r * 0.4
    return circ(cx, cy, r, fill, stroke=DARK) + path(
        f"M{_s(cx - k)} {_s(cy - k)} L{_s(cx + k)} {_s(cy + k)} "
        f"M{_s(cx + k)} {_s(cy - k)} L{_s(cx - k)} {_s(cy + k)}",
        stroke=SURF, sw=SW * 1.1)


def sine(x, y, w, amp=14, cycles=2, stroke=MID, sw=SW):
    """One cubic segment per half period -- a clean, even wave."""
    hw = w / (cycles * 2)
    d = [f"M{_s(x)} {_s(y)}"]
    sign = -1
    for _ in range(cycles * 2):
        d.append(f"c{_s(hw * 0.36)} {_s(sign * amp * 1.33)} "
                 f"{_s(hw * 0.64)} {_s(sign * amp * 1.33)} {_s(hw)} 0")
        sign = -sign
    return path(" ".join(d), stroke=stroke, sw=sw)


def square_wave(x, y, w, amp=14, steps=4, stroke=PRIM, sw=SW):
    seg = w / steps
    d = [f"M{_s(x)} {_s(y + amp)}"]
    up = True
    for i in range(steps):
        d.append(f"L{_s(x + i * seg)} {_s(y - amp if up else y + amp)}")
        d.append(f"L{_s(x + (i + 1) * seg)} {_s(y - amp if up else y + amp)}")
        up = not up
    return path(" ".join(d), stroke=stroke, sw=sw)


def sawtooth(x, y, w, amp=22, teeth=3, stroke=PRIM, sw=SW):
    """Climb, collapse, climb again -- the shape of a congestion window."""
    tw = w / teeth
    d = [f"M{_s(x)} {_s(y)}"]
    for i in range(teeth):
        d.append(f"L{_s(x + i * tw + tw * 0.82)} {_s(y - amp)}")
        d.append(f"L{_s(x + i * tw + tw * 0.82)} {_s(y - amp * 0.32)}")
    d.append(f"L{_s(x + w)} {_s(y - amp * 0.32 - amp * 0.5)}")
    return path(" ".join(d), stroke=stroke, sw=sw)


def lifeline(x, y0, y1, stroke=MID):
    """The vertical time axis of a message ladder."""
    return line(x, y0, x, y1, stroke=stroke, sw=1.8, dash="5 5")


def pipe(x, y, w, h, fill=TINT):
    """A link with capacity -- thickness carries the meaning."""
    return rr(x, y, w, h, min(h / 2, 8), fill)


def antenna(cx, cy, h=22):
    return line(cx, cy, cx, cy - h) + dot(cx, cy - h - 2, 2.6, PRIM)


def wifi_router(cx, cy, w=78, h=32):
    return "".join([antenna(cx - 22, cy - h / 2, 20), antenna(cx + 22, cy - h / 2, 20),
                    router(cx, cy, w, h)])


def addr_bar(x, y, w, groups=4, h=26, split=None, fill=SURF, accent=PRIM,
             accent_from=None):
    """An address as a segmented bar: octets/hextets as pills, never digits.

    `split` draws the network/host boundary; `accent_from` colours every group
    from that index on (host portion, prefix portion, whatever the topic needs).
    """
    out = [rr(x, y, w, h, 4, fill)]
    gw = w / groups
    for i in range(groups):
        gx = x + i * gw
        if i:
            out.append(line(gx, y, gx, y + h, stroke=MID, sw=1.6))
        on = accent_from is not None and i >= accent_from
        out.append(pill(gx + gw * 0.22, y + h / 2 - 3, gw * 0.56, 6,
                        accent if on else MID))
    if split is not None:
        sx = x + split * gw
        out.append(line(sx, y - 8, sx, y + h + 8, stroke=accent, sw=SW))
    return "".join(out)


def bit_ruler(x, y, w, bits=8, on=3, h=14, accent=PRIM):
    """A run of cells, the leading `on` filled -- masks and prefix lengths."""
    out = []
    cw = w / bits
    for i in range(bits):
        out.append(rr(x + i * cw, y, cw, h, 1.6,
                      fill=accent if i < on else SURF, stroke=DARK, sw=1.7))
    return "".join(out)


def tag(cx, cy, w=44, h=22, fill=TINT):
    """A luggage-tag shape: labels, VLAN tags, record types."""
    x, y = cx - w / 2, cy - h / 2
    d = (f"M{_s(x + 8)} {_s(y)} L{_s(x + w)} {_s(y)} L{_s(x + w)} {_s(y + h)} "
         f"L{_s(x + 8)} {_s(y + h)} L{_s(x)} {_s(y + h / 2)} Z")
    return path(d, fill=fill) + dot(x + 11, cy, 2.4, DARK)


# ------------------------------------------------------------------ write ---


def write(out_dir, slug, body, label):
    import pathlib
    p = pathlib.Path(out_dir) / f"{slug}.svg"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(svg(body, label), encoding="utf-8")
    return p
