<a id="kavramlar"></a>
# 3. Concepts

Every page of the interface corresponds to a concept, and the concepts nest inside each other:
**material → pin (or plate) → assembly → core**. In advanced mode this chain becomes a free
**geometry tree**. This chapter explains each concept with a sketch and ends with the table
"which nodes do I use for which arrangement". The JSON equivalents of the concepts are in
chapter 4; the design details are in [GEOMETRI_MODELI.md](../../GEOMETRI_MODELI.md).

## 3.1 Model (spec)

A **model** is a single JSON file (`*.json`). Materials, components, assemblies, geometry, run
settings, tallies, power distribution and depletion settings are sections of this file
(`malzemeler`, `cubuklar`, `plakalar`, `demetler`, `kor`, `geometri`, `ayarlar`, `tallyler`,
`guc_dagilimi`, `tukenme`, `calistirma`). The interface edits this file; the OpenMC model is
rebuilt from it for every run. Identifiers (names, `tur` values) are ASCII; visible descriptions
may be in Turkish.

## 3.2 Material

A **material** is a substance with a composition (nuclides or elements, by atom or weight
fraction), a density, a temperature and, where needed, thermal scattering data (S(α,β)). Library
materials (UO₂, water, Zircaloy-4, B₄C…) are stored with their parameters: when you change the
temperature or the enrichment, the density and the composition are recalculated.

Every material has a **role** (fuel, coolant, moderator, absorber, structural, gas); the role is
derived from the composition and decides which parameter sweeps, power distribution and depletion
are offered. The reserved name `bosluk` denotes a region without material (void).

## 3.3 Pin and plate

```
      fuel pin (cross-section)             cell (pitch p)
          +---------------+            +-----------------+
          |   +-------+   |            |    .-------.    |
          |   | +---+ |   |            |   | .---. |    |
          |   | |UO₂| | <- cladding    |   | | o | |    |  <- water (the outermost
          |   | +---+ |   |            |   | '---' |    |     region fills the cell)
          |   +-------+   |            |    '-------'    |
          +---------------+            +-----------------+
       r1 < r2 < r3 (inside out)           outer region radius < p/2
```

A **pin** is a cell made of concentric **regions**: from the inside out fuel, gas gap, cladding
and the coolant that fills the rest of the cell. The cross-section can be a cylinder, a square or
a hexagon. A control rod is a separate type: only in 3D models, **inserted** from the top (0%
withdrawn, 100% fully inserted). A **plate-type fuel element** (MTR) is a box made of flat plates.

## 3.4 Assembly

```
   square assembly (17x17, pitch 1.26 cm)    hexagonal assembly (4 rings)
   f f f f f f f f f f ...                       o o o o
   f f f f f g f f g ...                       o o o o o
   f f f g f f f f f ...                     o o o o o o
   ...                                      o o o o o o o   <- 37 positions incl. centre
   f = fuel pin, g = guide tube             ...
```

An **assembly** is a pin repeated in a **lattice**. The lattice is rectangular (`RectLattice`) or
hexagonal (`HexLattice`). The map puts a letter at every position; the letter key links the
letter to a pin (in the interface the map is painted with a palette and the letters are kept in
the background). A hexagonal lattice is defined by **rings** (centre = ring 1) and has an
**orientation** (`x` or `y`). The outer duct of a hexagonal assembly is optional.

## 3.5 Core

```
   square core map (5x5)            core with drums (cross-section)
   . A B A .                        .------- radial reflector -------.
   A B A B A                       |   D          D          D      |
   B A B A B   + radial reflector  |        +----------+            |
   A B A B A                       |   D    |   core   |    D       |  D = drum
   . A B A .                       |        +----------+            |  (absorber arc)
   . = no assembly (water)          '--------------------------------'
```

The **core** is the outermost structure of the model. In template (wizard) mode a **core type**
is chosen:

| Core type | What it builds |
|---|---|
| `tek_cubuk` | a single pin cell (k∞ with reflective boundary) |
| `tek_plaka` | a single plate-type fuel element |
| `tek_demet` | a single assembly (square or hexagonal) |
| `kare_kafes` | a square core map of assemblies (+ radial reflector) |
| `altigen_kafes` | a hexagonal core map of assemblies (+ radial reflector) |
| `tamburlu` | cylindrical core + radial reflector + rotating drums embedded in it |
| `kuresel` | concentric spherical shells (Godiva-type benchmarks, shielding) |
| `agac` | advanced geometry: a free node tree (below) |

**Control drum**: a rotating cylinder embedded in the radial reflector, with an absorber coating
on one arc. **Rotation 0°** turns the absorber towards the core (inserted, lowest k); **180°**
turns it outwards (withdrawn, highest k).

The **boundary condition** says what happens to a neutron at the outer surface of the model:
**vacuum** (`vacuum`) it escapes, **reflective** (`reflective`) it comes back like in a mirror
(infinite repetition; k∞), **periodic** (`periodic`) it re-enters through the opposite face,
**white** (`white`) it comes back in a random direction. On square and hexagonal outer boundaries
each face can get its own condition (quarter core symmetry).

## 3.6 Axial layer and height

```
   z ^   +--------------+  upper reflector (water)   Three different heights:
         +--------------+  plenum                    - total model  = sum of layers
         +--------------+  upper blanket (natural U) - fissile range = fissile layers
         |              |                            - target pin range
         | active fuel  |                              = layers containing that pin
         |              |
         +--------------+  lower blanket
         +--------------+  lower reflector (water)
```

A model can be **2D** (infinite height; no axial leakage), **3D single region** or **3D layered**.
**Axial layers** are listed from bottom to top; each layer has a height and a fill (if left empty,
the main fill of the core). With layers, the model height is the sum of the layers. Interfaces
between inner layers are always transparent; the boundary condition is applied only to the
bottom and top surfaces.

## 3.7 Geometry tree (advanced geometry)

When the template types are not enough — surrounding a square core with hexagonal blocks,
putting drums into the reflector of a square core, mixed lattices — the model is built as a
**node tree**. The user sees five node types:

| Node | What it does | Example |
|---|---|---|
| `malzeme` | fills a region with a single material | water, `bosluk` |
| `bilesen` | uses a definition from the library (pin, plate, assembly, drum, component) | `demet_24` |
| `kafes` | square or hexagonal lattice; one node per position | core map |
| `kap` | a shape (rectangle, cylinder, hexagon, sphere) + concentric **rings** + **placements** | root container, reflector ring |
| `eksenel` | a stack of layers in z | lower water / active / upper zone |

```
   Root container (hexagonal, vacuum boundary)
    +- Inside: lattice "blok_kafesi" (hexagonal, pitch 30 cm)  B -> celik_blok (component)
    |      +- Placement "kare_cekirdek" (list, square hole) -> 5x5 assembly lattice
    +- Ring 1 (20 cm water)
```

**Definition and use.** The library sections (pins, assemblies, drums, components) are
*definitions*; a `bilesen` node in the tree is a *use* of a definition. However many times a
definition is used, a single universe is built in OpenMC — the power distribution (distribcell)
and depletion rely on this sharing. A subtree used in more than one place should therefore be
**extracted into a component**.

A **placement** (`yerlesim`) cuts a **hole** into a container region and puts a node into it:
drums, experimental channels, control rod channels and a square core in the middle of a hexagonal
lattice are all placed by the same mechanism. There are three modes: `halka` (n instances on a
circle), `liste` (given positions), `kafes_konumu` (the positions of a given letter in a
lattice). The front of the placed content faces the core ("facing the core").

A **control group** drives several placements or control rods with a single value: a `donme`
group rotates drums together, a `daldirma` group inserts control rods together. Parameter sweeps
and critical searches target the group (`grup_donme`, `grup_daldirma`).

**Truncated position.** A lattice element clipped by the boundary of the region that contains it
is "truncated": the geometry is correct, but its volume cannot be computed analytically (it falls
back to the stochastic volume) and it is marked separately in the power map. This is a
**warning**; it is unavoidable when a square hole is surrounded by a hexagonal lattice.

Switching from the template to advanced mode is **one-way** (going back only with Undo). All
forms of the editor: [4.5 Advanced geometry editor](04e-geometri-gelismis.md#geometri-gelismis).

<a id="karar-tablosu"></a>
## 3.8 Which nodes do I use for which arrangement

| Arrangement you want | Template (wizard) | Advanced tree | Example / lesson |
|---|---|---|---|
| Single pin cell, k∞ | `tek_cubuk` | — | `ornekler/pwr_pinhucre.json` |
| Single assembly (square/hexagonal), k∞ | `tek_demet` | — | `ornekler/pwr_17x17.json`, [lesson](05-dersler.md#ders-demet) |
| Square full core + reflector | `kare_kafes` | — | `ornekler/pwr_smr_kor.json`, [lesson](05-dersler.md#ders-tam-kor) |
| Quarter core (two faces reflective, two vacuum) | `kare_kafes` + per-face boundary | — | `ornekler/pwr_ceyrek_kor.json` |
| Hexagonal full core (VVER, SFR) | `altigen_kafes` | — | `ornekler/vver1000_kor.json`, [lesson](05-dersler.md#ders-altigen-kor) |
| Plate-type element / MTR core | `tek_plaka` / `kare_kafes` | — | `ornekler/mtr_plaka.json`, `ornekler/mtr_kor.json` |
| Cylindrical core + reflector with drums | `tamburlu` | — | `ornekler/tamburlu_kor.json` |
| Critical sphere, shielding shells | `kuresel` (shells in JSON) | — | `ornekler/godiva_kriter.json`, `ornekler/zirh_kure.json` |
| Square core + hexagonal block ring | template "Square core + hexagonal ring" | root container (hexagonal) <- lattice (hexagonal blocks) + list placement (square hole <- square lattice) + water ring | `ornekler/pwr_kare_altigen_halka.json`, [lesson](05-dersler.md#ders-kare-altigen) |
| Hexagonal core + drum ring in the reflector | template "Hexagonal core + drum ring" | root container (`kafes_zarfi`) <- hexagonal core lattice + ring (reflector) <- `halka` placement (drum) + `donme` group | `ornekler/altigen_tambur_halkasi.json`, [lesson](05-dersler.md#ders-tambur) |
| Square core + drums in a cylindrical reflector | template "Lattice core + drum reflector" | root container (rectangle) <- square lattice + ring (cylinder outer section) <- `halka` or `liste` placement (drum) + `donme` group | `ornekler/kafes_tamburlu_yansitici.json` |
| Experimental channel in any region | — | `liste` placement in the container or ring (cylinder hole <- material) | [4.5](04e-geometri-gelismis.md#geometri-gelismis) |
| Control rod banks | control rod in components (3D) | `kafes_konumu` placement + `daldirma` group | `ornekler/pwr_kontrol.json` |
| Axial blanket / plenum / enrichment zones | 3D layered (every template) | `eksenel` node (at any level) | `ornekler/pwr_eksenel.json` |

First try to build an arrangement with a template: fewer fields, more checks. If the template is
not enough, build the closest template and convert it to a tree with **Switch to advanced
geometry**, then edit it there; building a tree from scratch is the last resort.
