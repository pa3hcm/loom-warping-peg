#!/usr/bin/env python3
"""Generates the STL files for the loom warping peg (pure Python, no OpenSCAD needed).

    python3 generate_stl.py

Creates in this folder:
    peg_base.stl  - clamp foot: flat plate for an F-clamp with a socket for the dowel
                    and a radial hole for a 3.5 x 25 locking screw
    peg_cap.stl   - cap on top of the dowel, so the warp loops cannot slip off
Print 1 of each in PETG (or PLA), 4 walls, 30-40 % infill. Both parts lie flat on the bed
(the cap upside down) and need no supports.

Frame: the peg axis is the z axis, z = 0 is the table top. The plate extends towards -y,
towards the table edge; the loom is in the +y direction.
"""
import math
import os
import struct

# ---------------------------------------------------------------- dimensions (mm)
DOWEL_D = 21.7         # measured diameter of the beech dowel (nominal 22 mm), same as the loom
CLEARANCE = 0.4
BORE_R = (DOWEL_D + CLEARANCE) / 2
SCREW_HOLE = 3.8       # through hole for a 3.5 x 25 wood screw
PEG_HEIGHT = 150.0     # top of the peg above the table, cap included
FLOOR = 3.0            # material under the dowel
PLATE_T = 10.0         # plate thickness
PLATE_W = 70.0         # plate width (x)
PLATE_FRONT = 35.0     # plate edge on the loom side, from the peg axis (+y)
CLAMP_L = 55.0         # flat clamping zone between the table edge and the fillet
CORNER_R = 8.0
BOSS_R = 21.0          # socket around the dowel (wall ~10 mm, as the hubs of the loom)
BOSS_H = 35.0          # socket height above the plate
FILLET_R = 10.0        # concave fillet between socket and plate
SCREW_Z = PLATE_T + BOSS_H - 10.0
CAP_R = 17.0           # cap diameter 34 mm: 6 mm lip around the dowel
CAP_TOP = 4.0
CAP_SLEEVE = 15.0
CAP_WALL = 3.0
VENT_R = 1.5           # small air hole in the bottom of the socket and the cap

PLATE_BACK = BOSS_R + FILLET_R + CLAMP_L          # from the peg axis to the table edge (-y)
SOCKET_DEPTH = PLATE_T + BOSS_H - FLOOR
DOWEL_L = PEG_HEIGHT - FLOOR - CAP_TOP            # length of the dowel to saw

SAMPLES = 360
HERE = os.path.dirname(os.path.abspath(__file__))


def ray(poly, theta):
    """Largest distance at which a ray from the origin crosses the edge of poly (or None)."""
    dx, dy = math.cos(theta), math.sin(theta)
    best = None
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = (x1 * ey - y1 * ex) / den
        u = (x1 * dy - y1 * dx) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9:
            best = t if best is None else max(best, t)
    return best


class Shape:
    """Star-shaped outline around the origin: union of polygons (convex, or star-shaped)."""

    def __init__(self, *polys):
        self.polys = polys

    def r(self, theta):
        return max(r for r in (ray(p, theta) for p in self.polys) if r is not None)

    def angles(self):
        return [math.atan2(y, x) % (2 * math.pi) for p in self.polys for x, y in p]


class Round(Shape):
    """Circle with radius r (exact, without corner points)."""

    def __init__(self, r):
        self.radius = r

    def r(self, theta):
        return self.radius

    def angles(self):
        return []


# ---------------------------------------------------------------- 3D: stacked layers
class Layer:
    """Layer between z0 and z1 with an inner and an outer outline.

    hole: half angle (rad) of a radial hole around angle 0 (direction +x), or 0 for no hole.
    """

    def __init__(self, z0, z1, inner, outer, hole=0.0):
        self.z0, self.z1, self.inner, self.outer, self.hole = z0, z1, inner, outer, hole


def stacked(layers):
    """Builds a watertight mesh from adjoining layers (bottom to top).

    Per angle step ('strip') each layer either has material between its inner and outer outline
    or not. Walls, horizontal faces between layers and radial side walls (at holes and windows)
    are built so that every edge is shared by exactly two triangles.
    """
    angles = set(2 * math.pi * i / SAMPLES for i in range(SAMPLES))
    for l in layers:
        for v in (l.inner, l.outer):
            for h in v.angles():
                angles.update((h - 1e-4, h, h + 1e-4))
        if l.hole:
            angles.update((l.hole, 2 * math.pi - l.hole))
    angles = sorted(h % (2 * math.pi) for h in angles)
    unique = [angles[0]]
    for h in angles[1:]:                  # near-duplicate angles give degenerate triangles
        if h - unique[-1] > 5e-5:
            unique.append(h)
    if 2 * math.pi - unique[-1] + unique[0] <= 5e-5:
        unique.pop()
    # add the exact angles where inner and outer outline touch (edge of a window)
    extra = []
    for l in layers:
        def f(a):
            return l.outer.r(a) - l.inner.r(a)
        for a0, a1 in zip(unique, unique[1:] + [unique[0] + 2 * math.pi]):
            if f(a0) * f(a1) < 0:
                for _ in range(60):
                    m = (a0 + a1) / 2
                    a0, a1 = (a0, m) if f(a0) * f(m) <= 0 else (m, a1)
                extra.append(((a0 + a1) / 2) % (2 * math.pi))
    angles = sorted(unique + [a for a in extra if min(abs(a - u) for u in unique) > 5e-5])
    n = len(angles)

    ri = [[l.inner.r(a) for a in angles] for l in layers]
    ro = [[l.outer.r(a) for a in angles] for l in layers]

    def present(k, i):
        a0, a1 = angles[i], angles[(i + 1) % n]
        if a1 < a0:
            a1 += 2 * math.pi
        mid = (a0 + a1) / 2 % (2 * math.pi)
        l = layers[k]
        if l.hole and min(mid, 2 * math.pi - mid) < l.hole:
            return False
        return l.outer.r(mid) > l.inner.r(mid) + 1e-6

    on = [[present(k, i) for i in range(n)] for k in range(len(layers))]
    tris = []

    def p(r, a, z):
        return (r * math.cos(a), r * math.sin(a), z)

    def face(r_in, r_out, i, z, up):
        """Horizontal ring strip between two radius profiles (per corner point) at height z."""
        j = (i + 1) % n
        (q0, q1), (r0, r1) = r_in, r_out
        if r0 - q0 <= 1e-9 and r1 - q1 <= 1e-9:
            return
        a0, a1 = angles[i], angles[j]
        t = [(p(q0, a0, z), p(r0, a0, z), p(r1, a1, z)), (p(q0, a0, z), p(r1, a1, z), p(q1, a1, z))]
        tris.extend(t if up else [(a, c, b) for a, b, c in t])

    for i in range(n):
        j = (i + 1) % n
        a0, a1 = angles[i], angles[j]
        for k, l in enumerate(layers):
            if not on[k][i]:
                continue
            z0, z1 = l.z0, l.z1
            o0, o1, b0, b1 = ro[k][i], ro[k][j], ri[k][i], ri[k][j]
            tris += [(p(o0, a0, z0), p(o1, a1, z0), p(o1, a1, z1)),
                     (p(o0, a0, z0), p(o1, a1, z1), p(o0, a0, z1))]
            tris += [(p(b0, a0, z0), p(b1, a1, z1), p(b1, a1, z0)),
                     (p(b0, a0, z0), p(b0, a0, z1), p(b1, a1, z1))]
        # horizontal faces at every layer boundary: material below and not above faces up
        for k in range(len(layers) + 1):
            below = k - 1 if k > 0 and on[k - 1][i] else None
            above = k if k < len(layers) and on[k][i] else None
            z = layers[k].z0 if k < len(layers) else layers[-1].z1

            def prof(m):
                return (ri[m][i], ri[m][j]), (ro[m][i], ro[m][j])

            for src, other, neighbour, up in ((below, above, k, True), (above, below, k - 1, False)):
                if src is None:
                    continue
                vb, vo = prof(src)
                if other is None:
                    if 0 <= neighbour < len(layers):
                        # split at the inner edge of the neighbouring layer, so the edges match
                        m = tuple(min(vo[e], max(vb[e], ri[neighbour][(i, j)[e]])) for e in (0, 1))
                        face(vb, m, i, z, up)
                        face(m, vo, i, z, up)
                    else:
                        face(vb, vo, i, z, up)
                    continue
                ab, ao = prof(other)
                # part inside the inner edge of the other layer
                face(vb, tuple(min(vo[e], max(vb[e], ab[e])) for e in (0, 1)), i, z, up)
                # part outside the outer edge of the other layer
                face(tuple(max(vb[e], min(vo[e], ao[e])) for e in (0, 1)), vo, i, z, up)
    # radial side walls where a strip with material borders a strip without
    for i in range(n):
        h = (i - 1) % n
        a = angles[i]
        for k, l in enumerate(layers):
            if on[k][i] == on[k][h] or ro[k][i] - ri[k][i] <= 1e-9:
                continue
            q = [p(ri[k][i], a, l.z0), p(ro[k][i], a, l.z0), p(ro[k][i], a, l.z1), p(ri[k][i], a, l.z1)]
            t = [(q[0], q[1], q[2]), (q[0], q[2], q[3])]
            tris.extend(t if on[k][i] else [(x, z, y) for x, y, z in t])
    return tris


# ---------------------------------------------------------------- check & export
def check(tris):
    """Watertight: every edge occurs exactly once in each direction. Returns the volume."""
    def k(p):
        return tuple(round(c, 5) for c in p)
    edges = {}
    vol = 0.0
    for a, b, c in tris:
        for u, v in ((a, b), (b, c), (c, a)):
            edges[(k(u), k(v))] = edges.get((k(u), k(v)), 0) + 1
        vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
    errors = sum(1 for (u, v), n in edges.items() if u != v and (n != 1 or edges.get((v, u)) != 1))
    return vol, errors


def write_stl(name, tris):
    tris = [t for t in tris if len({tuple(round(c, 5) for c in p) for p in t}) == 3]
    with open(os.path.join(HERE, name), "wb") as f:
        f.write(name.encode().ljust(80, b" ")[:80])
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            u = [b[i] - a[i] for i in range(3)]
            v = [c[i] - a[i] for i in range(3)]
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            l = math.sqrt(sum(x * x for x in n)) or 1
            f.write(struct.pack("<12fH", *(x / l for x in n), *a, *b, *c, 0))
    return tris


# ---------------------------------------------------------------- parts
def rounded_rect(x0, x1, y0, y1, r, n=12):
    pts = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def plate_outline():
    return Shape(rounded_rect(-PLATE_W / 2, PLATE_W / 2, -PLATE_BACK, PLATE_FRONT, CORNER_R))


def base_layers():
    """Plate with the socket on top: floor, plate, stepped fillet, socket with screw hole, chamfer."""
    plate = plate_outline()
    layers = [Layer(0, FLOOR, Round(VENT_R), plate),
              Layer(FLOOR, PLATE_T, Round(BORE_R), plate)]
    steps = int(FILLET_R / 0.5)
    for i in range(steps):
        t = (i + 0.5) * FILLET_R / steps
        r = BOSS_R + FILLET_R - math.sqrt(FILLET_R ** 2 - (FILLET_R - t) ** 2)
        layers.append(Layer(PLATE_T + i * FILLET_R / steps, PLATE_T + (i + 1) * FILLET_R / steps,
                            Round(BORE_R), Round(r)))
    h = SCREW_HOLE / 2
    alpha = math.atan(h / BORE_R)
    top = PLATE_T + BOSS_H
    layers += [Layer(PLATE_T + FILLET_R, SCREW_Z - h, Round(BORE_R), Round(BOSS_R)),
               Layer(SCREW_Z - h, SCREW_Z + h, Round(BORE_R), Round(BOSS_R), alpha),
               Layer(SCREW_Z + h, top - 1, Round(BORE_R), Round(BOSS_R)),
               Layer(top - 1, top, Round(BORE_R), Round(BOSS_R - 1))]
    return layers


def peg_base():
    return stacked(base_layers())


def cap_layers():
    """Upside down, as printed: the top of the cap on the bed, the sleeve upwards."""
    return [Layer(0, 1, Round(VENT_R), Round(CAP_R - 1)),
            Layer(1, CAP_TOP, Round(VENT_R), Round(CAP_R)),
            Layer(CAP_TOP, CAP_TOP + CAP_SLEEVE, Round(BORE_R), Round(BORE_R + CAP_WALL))]


def peg_cap():
    return stacked(cap_layers())


if __name__ == "__main__":
    for name, make in (("peg_base.stl", peg_base), ("peg_cap.stl", peg_cap)):
        tris = write_stl(name, make())
        vol, errors = check(tris)
        status = "watertight" if errors == 0 else f"{errors} open edges!"
        print(f"{name:14s} {len(tris):6d} triangles  {vol / 1000:5.1f} cm3  {status}")
    print(f"plate {PLATE_W:.0f} x {PLATE_BACK + PLATE_FRONT:.0f} x {PLATE_T:.0f} mm, "
          f"clamping zone {CLAMP_L:.0f} mm, socket depth {SOCKET_DEPTH:.0f} mm, "
          f"saw the dowel to {DOWEL_L:.0f} mm")
