#!/usr/bin/env python3
"""Renders an impression of the loom warping peg clamped to the table edge (pure Python, z-buffer).

    python3 render.py          -> warping_peg.png       (angled view from the table edge)
    python3 render.py side     -> warping_peg_side.png  (side view, along the table edge)
Requires ImageMagick ('convert') for the PNG.
"""
import math
import os
import subprocess
import sys

import generate_stl as p

SIDE = "side" in sys.argv
W, H, SS = 1200, 1000, 2
VIEW = (-0.8, 0.75, -0.55) if not SIDE else (-1.0, 0.0001, -0.02)
LIGHT = (-0.6, 0.3, 1.0)
PLA = (235, 120, 50)
WOOD = (226, 190, 140)
TABLE = (150, 110, 75)
STEEL = (120, 125, 135)
GRIP = (200, 40, 40)
YARN = (60, 110, 190)

tris = []          # (a, b, c, colour)


def add(mesh, colour, f=lambda q: q):
    tris.extend((f(a), f(b), f(c), colour) for a, b, c in mesh)


def box(x0, x1, y0, y1, z0, z1, colour):
    v = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        a, b, c, d = (v[i] for i in q)
        tris.extend([(a, b, c, colour), (a, c, d, colour)])


def cylinder(cx, cy, r, z0, z1, colour, n=48):
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        q0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
        q1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
        tris.extend([((*q0, z0), (*q1, z0), (*q1, z1), colour), ((*q0, z0), (*q1, z1), (*q0, z1), colour),
                     ((cx, cy, z0), (*q1, z0), (*q0, z0), colour), ((cx, cy, z1), (*q0, z1), (*q1, z1), colour)])


# ---------------------------------------------------------------- scene
edge = -p.PLATE_BACK                                   # table edge (y)
box(-170, 170, edge, 260, -25, 0, TABLE)               # table top
add(p.peg_base(), PLA)
add(p.peg_cap(), PLA, lambda q: (q[0], q[1], p.PEG_HEIGHT - q[2]))
cylinder(0, 0, p.DOWEL_D / 2, p.FLOOR, p.FLOOR + p.DOWEL_L, WOOD)
# screw head in the side of the socket
box(p.BOSS_R - 0.5, p.BOSS_R + 2.5, -3.5, 3.5, p.SCREW_Z - 3.5, p.SCREW_Z + 3.5, STEEL)
# F-clamp: rail outside the table edge, fixed arm over the plate, sliding arm under the table
jaw_y = edge + p.CLAMP_L / 2 + 2
rail_y = edge - 18
box(-6, 6, rail_y - 4, rail_y + 4, -130, 48, STEEL)                    # rail
box(-8, 8, rail_y - 4, jaw_y + 12, 30, 48, STEEL)                      # fixed arm
cylinder(0, jaw_y, 14, p.PLATE_T, p.PLATE_T + 4, (60, 60, 60))         # pad
box(-4, 4, jaw_y - 4, jaw_y + 4, p.PLATE_T + 4, 30, STEEL)
box(-8, 8, rail_y - 6, jaw_y + 12, -115, -95, STEEL)                   # sliding arm
cylinder(0, jaw_y, 4, -95, -29, STEEL)                                 # spindle
cylinder(0, jaw_y, 14, -29, -25, (60, 60, 60))                         # pad under the table
cylinder(0, jaw_y, 12, -175, -115, GRIP)                               # handle
# warp loops around the peg, running towards the loom (+y)
lines = []
for k in range(6):
    z = 70 + 9 * k
    x = [(-1) ** k * 0.5 * k, 0][0]
    r = p.DOWEL_D / 2 + 0.6
    arc = [(r * math.cos(a), r * math.sin(a), z) for a in
           [math.pi * i / 16 for i in range(17)]]
    lines.append([(r, 260, z - 6 * k)] + arc + [(-r, 260, z - 6 * k)])

# ---------------------------------------------------------------- render
def norm(v):
    l = math.sqrt(sum(c * c for c in v)) or 1
    return tuple(c / l for c in v)


D, L = norm(VIEW), norm(LIGHT)
UP = (0, 0, 1)
RIGHT = norm((D[1] * UP[2] - D[2] * UP[1], D[2] * UP[0] - D[0] * UP[2], D[0] * UP[1] - D[1] * UP[0]))
TOP = (RIGHT[1] * D[2] - RIGHT[2] * D[1], RIGHT[2] * D[0] - RIGHT[0] * D[2], RIGHT[0] * D[1] - RIGHT[1] * D[0])


def proj(q):
    return (sum(a * b for a, b in zip(q, RIGHT)), sum(a * b for a, b in zip(q, TOP)), sum(a * b for a, b in zip(q, D)))


pts = [proj(q) for t in tris for q in t[:3]]
xs, ys = [q[0] for q in pts], [q[1] for q in pts]
BW, BH = W * SS, H * SS
scale = 0.92 * min(BW / (max(xs) - min(xs)), BH / (max(ys) - min(ys)))
cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2


def screen(q):
    x, y, z = proj(q)
    return (BW / 2 + (x - cx) * scale, BH / 2 - (y - cy) * scale, z)


zbuf = [float("inf")] * (BW * BH)
pixels = bytearray(b"\xff" * (BW * BH * 3))
for a, b, c, rgb in tris:
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    n = norm((u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]))
    if sum(x * y for x, y in zip(n, D)) > 0:
        n = tuple(-x for x in n)
    f = 0.5 + 0.55 * max(0.0, sum(x * y for x, y in zip(n, L)))
    col = bytes(min(255, int(ch * f)) for ch in rgb)
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = screen(a), screen(b), screen(c)
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(den) < 1e-9:
        continue
    for py in range(max(0, int(min(y0, y1, y2))), min(BH, int(max(y0, y1, y2)) + 1)):
        for px in range(max(0, int(min(x0, x1, x2))), min(BW, int(max(x0, x1, x2)) + 1)):
            w0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / den
            w1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / den
            w2 = 1 - w0 - w1
            if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                continue
            z = w0 * z0 + w1 * z1 + w2 * z2
            k = py * BW + px
            if z < zbuf[k]:
                zbuf[k] = z
                pixels[3 * k:3 * k + 3] = col

for line in lines:
    for a, b in zip(line, line[1:]):
        sa, sb = screen(a), screen(b)
        steps = int(max(abs(sb[0] - sa[0]), abs(sb[1] - sa[1]))) + 1
        for s in range(steps + 1):
            t = s / steps
            x, y, z = (sa[i] + t * (sb[i] - sa[i]) for i in range(3))
            for py in range(int(y) - 2, int(y) + 3):
                for px in range(int(x) - 2, int(x) + 3):
                    if 0 <= px < BW and 0 <= py < BH and z <= zbuf[py * BW + px] + 0.5:
                        pixels[3 * (py * BW + px):3 * (py * BW + px) + 3] = bytes(YARN)

png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "warping_peg_side.png" if SIDE else "warping_peg.png")
ppm = png[:-4] + ".ppm"
with open(ppm, "wb") as f:
    f.write(f"P6 {BW} {BH} 255\n".encode())
    f.write(pixels)
subprocess.run(["convert", ppm, "-resize", f"{100 // SS}%", png], check=True)
os.remove(ppm)
print("written:", png)
