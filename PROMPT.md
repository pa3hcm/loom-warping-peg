# Reusable prompt: loom warping peg

Copy everything below the line into a new session with an AI assistant (preferably Claude Code in
a clone of this repository) and put your change request at the bottom under **My change**.

## Models and tools used

| What | Specification |
|---|---|
| AI model | Claude Opus 5.5 (model ID `claude-opus-5-5`, Anthropic), knowledge cutoff June 2026 |
| Environment | Claude Code in the Claude desktop app (Code tab), Linux, Python 3 |
| Period | November 2026 |
| 3D printer | FDM, PETG or PLA, 0.2 mm layers, 4 walls, 30–40 % infill; STLs need no supports |
| Local software | Python 3 (standard library only, **no** numpy/matplotlib/trimesh), ImageMagick (`convert`); **no OpenSCAD** |
| Storage | this git repository (`loom-warping-peg`) |

---

## Prompt

You are helping me with the design of a **warping peg with table clamp** for direct warping on my
home-built rigid heddle loom (https://github.com/pa3hcm/rigid-heddle-loom). All files are in this
repository (`loom-warping-peg`). The design is parametric in Python; `README.md` is the build
manual (English), `README_dutch.md` is the same manual in Dutch. Read `README.md` and
`generate_stl.py` before you change anything.

### Way of working and preferences

- **Everything is in English**: code, identifiers, comments, file names, image names,
  `README.md` and this prompt. The only exception is `README_dutch.md`, which must stay a
  complete Dutch translation of `README.md` (with the same English file and parameter names).
  Answer in the language I write in.
- Change **only what I ask for**.
- After every change: make all outputs again (STLs, images), check that the STLs are watertight
  and look at the images, and update both READMEs (how it works, file table, shopping list,
  printing, build steps, design decisions) and, if needed, this prompt.
- Be honest about what has not been tested. Propose design choices with a recommendation.
- Code: same style as the loom scripts. No external Python packages. The mesher (`stacked`,
  `Layer`, `Shape`, `Round`, `check`, `write_stl`) is copied from the loom's
  `print/generate_stl.py`: every part is a stack of layers around the peg axis, each layer with an
  inner and an outer star-shaped outline and an optional radial hole in the +x direction.

### Starting points

- The peg is a vertical round stick, **150 mm** high above the table top (cap included)
  (`PEG_HEIGHT`).
- Dowel: beech Ø 22 mm, the same as the rollers of the loom, measured **21.7** mm
  (`DOWEL_D` = 21.7, `CLEARANCE` = 0.4).
- Held at the far end of the table with an **F-clamp** on the table edge.
- Locking screw 3.5 × 25 mm, the same as on the loom's ratchet wheels (`SCREW_HOLE` = 3.8).

### Construction (current state)

Frame: the peg axis is the z axis, z = 0 is the table top, the plate extends towards −y (the table
edge), the loom is in the +y direction.

- **Base** (`peg_base.stl`, printed in one piece, plate on the bed): plate 70 × 121 × 10 mm
  (`PLATE_W`, `PLATE_T`), corner radius 8. From the table edge: flat clamping zone of 55 mm
  (`CLAMP_L`), then a concave fillet (R 10, stepped in 0.5 mm layers) to a socket of Ø 42
  (`BOSS_R` = 21), 35 mm above the plate (`BOSS_H`), 1 mm chamfer on top. The peg axis is 86 mm
  from the table edge, the plate extends 35 mm beyond the axis (`PLATE_FRONT`). Bore Ø 22.1,
  42 mm deep, with a 3 mm floor (`FLOOR`) and a Ø 3 air/push-out hole. Radial hole for the
  locking screw 10 mm below the top of the socket (`SCREW_Z`), towards +x (sideways, not towards
  the loom). About 119 cm³.
- **Cap** (`peg_cap.stl`, printed upside down): Ø 34 (`CAP_R` = 17), 4 mm top with a 1 mm
  chamfer, sleeve 15 mm long with a 3 mm wall, Ø 3 air hole. Pressed on, optionally glued.
- **Dowel** cut to 143 mm (`DOWEL_L` = `PEG_HEIGHT` − `FLOOR` − `CAP_TOP`).
- The warp pulls the peg towards the loom (+y); the plate then wants to lift at the table-edge
  side, where the clamp is. No lip over the table edge (table edges vary); optionally a non-slip
  mat under the plate.

### Files

| File | Role |
|---|---|
| `generate_stl.py` | all parameters + `peg_base.stl`, `peg_cap.stl` (own mesher, checks watertightness, prints the dowel length) |
| `render.py` | own z-buffer renderer with table, F-clamp and warp loops: `warping_peg.png`, and with argument `side` `warping_peg_side.png` |
| `README.md`, `README_dutch.md` | build manual in English and Dutch, shopping list, design decisions |

Make everything again:

```bash
python3 generate_stl.py && python3 render.py && python3 render.py side
```

### Open points

- Not printed or tested yet: check the fit of the dowel in the socket and the cap, and whether the
  base stays put under full warp tension.

### My change

<!-- describe what you want to change here -->
