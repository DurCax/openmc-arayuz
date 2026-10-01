# Flexible geometry model (Wave G) — user-facing summary

Türkçe (full design document): [GEOMETRI_MODELI.md](GEOMETRI_MODELI.md)

> **This is a summary, not a translation of the full document.** It covers what a user needs:
> the purpose and scope of the geometry tree, its node types, the templates, and the user
> decisions of gate G-A (§15 of the Turkish document). The OpenMC translation rules, schema
> migration, consumer APIs, equivalence gate, work breakdown and risks (§5–§9, §11–§13, §16) are
> described only in [GEOMETRI_MODELI.md](GEOMETRI_MODELI.md), which is authoritative. Where the
> Turkish document's earlier sections and its §15 differ, §15 applies; this summary already
> follows §15. JSON keys and `tur` values are identifiers and are not translated (glossary
> [SOZLUK.md](SOZLUK.md)); their English meaning is given next to them.

## 1. Purpose and scope

**Purpose.** The user's request was: "The geometry model must be very flexible: surrounding a
square lattice with a hexagonal lattice, using control drums not only in the example but in any
geometry." A new layout should not require a new core type or a new branch in the builder.

**In scope:**
- square and hexagonal lattices nested in each other and side by side;
- concentric rings of different shapes (a square core with a cylindrical reflector, for example);
- placing control drums, channels or sub-lattices in any region;
- named, reusable components;
- axial stacks at any level;
- control groups for drums and control rods;
- rotating the whole model (for symmetry tests);
- per-face boundary conditions (quarter core; added by decision 4 in §5 below).

**Out of scope:** raw CSG cells (writing surface and region expressions), DAGMC/CAD, a stepped
lattice envelope (`kafes_zarfi`) for square lattices, rotation of a non-circular hole, a
symmetry-reduction wizard.

This is not a CSG editor. The user does not write surfaces; every node corresponds to one
well-defined structure that OpenMC knows and that can be checked.

## 2. Templates and the geometry tree

The seven classic core types (`kor.tur`) remain as **templates**. A template is expanded into a
tree at run time by a pure function (`geometri.genislet`); on disk the tree is written only in
**advanced geometry** mode (`kor.tur = "agac"`, the `geometri` section is then the single source
of truth). All consumers — builder, script generator, model check, power distribution, depletion
volumes, sweeps — work on the tree, so a template and its expanded tree build the same model
(checked by the equivalence gate on all examples: geometry fingerprint, material instance counts,
boundary and source box, depletion instance volumes, script XML; for `tamburlu_kor` the tree and
the template also gave bit-for-bit the same k with the same seed).

| Template (`kor.tur`) | Meaning | Root container of the expanded tree |
|---|---|---|
| `tek_cubuk` | single pin | rectangle `[pitch, pitch]` with the pin |
| `tek_plaka` | single plate | rectangle around the plate element |
| `tek_demet` | single assembly (square or hexagonal) | rectangle or hexagon around the assembly; reflector as a ring if enabled |
| `kare_kafes` | rectangular lattice core | rectangle with a square core lattice; reflector as a ring if enabled |
| `altigen_kafes` | hexagonal lattice core | lattice envelope (`kafes_zarfi`) with a hexagonal core lattice; reflector as a hexagonal ring if enabled |
| `kuresel` | spherical assembly (Godiva type) | sphere with concentric spherical shells as rings |
| `tamburlu` | core with control drums | cylinder (core fill), reflector ring with a ring placement of drums and a rotation group |

Three further templates build layouts that no classic core type covers; they are available on the
Geometry page and produce an advanced-mode tree directly:

| Template key | Layout | Example file |
|---|---|---|
| `kare_altigen` | square core + hexagonal ring: a square lattice core inside a ring of hexagonal blocks (reflector blocks or fuel) | `ornekler/pwr_kare_altigen_halka.json` |
| `altigen_tambur` | hexagonal core + drum ring: hexagonal core lattice, hexagonal reflector, a ring of drums facing the flat faces | `ornekler/altigen_tambur_halkasi.json` |
| `kafes_tambur` | lattice core + drum reflector: square lattice core, cylindrical reflector with drums | `ornekler/kafes_tamburlu_yansitici.json` |

**Switching to advanced geometry** is one-way: once the tree is edited the template form
closes, and the way back is **Undo** (Ctrl+Z), which returns to the template state in a single
step (decision 1).

## 3. Node types

Five node types are visible to the user; a sixth (`referans`) exists only as an intermediate
state while extracting a named component and is never shown.

| `tur` | Meaning | Key fields |
|---|---|---|
| `malzeme` | material (leaf) | `ad`: a material name or `"bosluk"` (void). A material node cannot carry a transform (OpenMC does not rotate a material-filled cell). |
| `bilesen` | component reference | `ad`: the name of a pin, plate, assembly, control drum or named component. A name defined in two library sections is an error. |
| `kafes` | lattice | `sekil` (`kare` square / `altigen` hexagonal), `adim` (pitch), `boyut` (square: `[nx, ny]`) or `halka_sayisi` (hexagonal: number of rings), `yonelim` (hexagonal orientation, `x`/`y`), `harita` (map), `anahtar` (letter → content), `dis` (outer fill, required) |
| `kap` | container: a cross section with optional rings and holes | `kesit` (cross section), `ic` (inside), `halkalar` (rings), `yerlesimler` (placements), `dis` (outside; required except at the root); at the root only: `yukseklik` (height), `sinir` (boundary conditions) |
| `eksenel` | axial stack | `icerik` (default content), `katmanlar` (layers from bottom to top, each with `yukseklik` and optional `icerik` / `anahtar`) |

Common fields: `id` (a short identifier unique in the tree, used for selection, finding locations
and cell names), `ad` (display name), `donusum` (transform: `{"donme": degrees, "oteleme":
[x, y]}`, applied when the node is put in its slot).

**Slots.** A node can be put in `kap.ic`, `kap.dis`, a ring's `icerik`, a lattice key
`kafes.anahtar[letter]`, `kafes.dis`, `eksenel.icerik`, a layer's `icerik`, or a placement's
`icerik`. In hand-written JSON a slot may hold a string shorthand (resolved in the order pin →
plate → assembly → drum → named component → material); the interface always writes explicit
nodes.

**Cross sections** (`kesit` and ring `dis`): `dikdortgen` (rectangle, `boyut`), `silindir`
(cylinder, `yaricap`), `altigen` (hexagon, `apotem` and prism orientation `yonelim`), `kure`
(sphere, root only, no height), `kafes_zarfi` (lattice envelope; only for a root container whose
inside is a hexagonal lattice). A ring is given either by a `kalinlik` (thickness, which grows the
same shape uniformly) or by its own outer cross section `dis`.

**Lattices.** A square map is written row by row, the first row at the top. A hexagonal map is a
list of rings from the outside in. The character `.` fills a position with the lattice's `dis`
content (irregular core, hidden position). The pitch is the cell side for a square lattice and
the flat-to-flat size for a hexagonal lattice.

> **Two meanings of hexagonal orientation — do not mix them up.** `kafes.yonelim` follows
> OpenMC `HexLattice` (`'x'`: neighbours at 0°, 60°…; `'y'`: neighbours at 30°, 90°…), while
> `kesit.yonelim` follows OpenMC `HexagonalPrism` (`'y'`: flat faces left and right, vertical).
> A cross section that *surrounds* a hexagonal lattice uses the same letter as the lattice; the
> cell of a lattice *element* is a prism with the opposite letter. Both rules were measured.

**Height.** A model without height (`yukseklik: null`) and without an axial stack is 2D. If the
root's inside is an axial stack, the model height is the sum of the layers (single source of
truth). A stack below the root must add up to the model height; otherwise it is an error.

### Placements (`yerlesimler`)

A placement cuts a **hole** into the region that owns it (the inside of a container or a ring)
and puts its `icerik` (content) into the hole. Control drums, control rods, experimental channels
and a square core inside a hexagonal block lattice all use this one mechanism.

| `mod` | Instance centres |
|---|---|
| `halka` (ring) | `sayi` instances on a circle of radius `merkez_yaricap`, starting at `baslangic_acisi` |
| `liste` (list) | explicit `konumlar: [[x, y], ...]` |
| `kafes_konumu` (lattice position) | the centres of all positions of a lattice (`kafes` id) that carry a given letter (`harf`); the hole is cut inside the position cell |

The hole shape is `kesit`; it may be omitted only for content with a natural cross section
(a control drum: a circle of the drum radius).

**"Facing the core" convention.** The front of every placed content is its local +x direction;
the absorber arc of a control drum is centred on local +x. The rotation of instance i is

- ring mode: ψᵢ = φᵢ + 180 + D (φᵢ = start angle + 360·i/n);
- list and lattice-position modes with `bakis: {"tur": "merkez"}`: ψᵢ = atan2(m_y − y_i, m_x − x_i) + D;
- with `bakis: {"tur": "sabit", "aci": a}`: ψᵢ = a + D;

where D is the value of the rotation group the placement belongs to (0 if none) plus
`donme_ofset`. For drums the default is to face the centre (0, 0). The result: **drum rotation
0° = absorber faces the core (inserted, lowest k); 180° = absorber faces outwards (withdrawn).**
If the whole container is rotated, the placement rotates with it and keeps facing the core.

### Named components (`geometri.parcalar`) and control groups (`geometri.gruplar`)

- A **named component** is a named subtree `{"ad": ..., "dugum": <node>}`, referenced with
  `bilesen`. However many times it is used, OpenMC builds **one universe**; the distribcell
  power tally and per-instance depletion rely on this. A subtree that is used more than once
  should be a named component: two inline copies build two universes and split the instance
  count, so identical inline subtrees give a warning. A component may not contain itself.
- A **control group** holds one value for several members: `donme` (rotation; members are
  placements, all their instances rotate) or `daldirma` (insertion; members are control rod
  definitions). The value is stored only in the group; a member belongs to at most one group of
  each kind. Parameter sweeps and the critical search act on groups (`grup_donme`,
  `grup_daldirma`).

### Pin cross sections

Fuel pins can have a **cylindrical, square or hexagonal** cross section (`cubuklar[i].kesit =
"silindir" | "kare" | "altigen"`, with `kesit_yonelim` for hexagonal pins). Regions (fuel / gap /
cladding) are nested in the same shape; the region radius is half the size (square side 2r,
hexagon flat-to-flat 2r); the outermost boundary is the cell pitch.

### Boundary conditions per face

The root's `sinir.yuzler` gives one condition per side face: four faces `-x`, `+x`, `-y`, `+y`
for a rectangle, six faces for a hexagon or lattice envelope (vacuum / reflective / periodic;
periodic faces must be paired consistently). Example: the quarter core
`ornekler/pwr_ceyrek_kor.json` has two reflective symmetry faces and two vacuum outer faces.

## 4. What the model check reports

- **Errors** (the model is not built or run): unknown node type or missing field; undefined
  reference; ambiguous name; a component that contains itself or nesting deeper than 10 levels;
  lattice map size, undefined letter or missing `dis`; a ring that does not enclose the previous
  one; a hole that leaves its region or overlaps another hole; an undefined facing direction; an
  axial stack in a 2D model or with the wrong total height; a control rod in a 2D model; a
  transform on a material node; a periodic condition on an unsuitable surface.
- **Warnings:** a **truncated position** (a lattice element or component clipped by the region
  above it; the count and the first five positions are listed; its volume falls back to a
  stochastic estimate and the power map marks it); a truncated pin; identical inline subtrees;
  nesting deeper than 6 levels or more than 50 holes in one region (slower tracking); a void region
  inside the root; groups with one member or none; a drum in a 2D model; a power target only in
  truncated positions.
- **Info:** a position completely hidden under a hole; an unused definition; an ignored
  `kafes.dis`; a skipped 0 cm layer; a control rod's own insertion overridden by its group.
- **Geometry probe:** sample points are checked for cells that contain no point (gaps) or more
  than one (overlaps); the first points are reported with their node path.

## 5. User decisions at gate G-A (30.09.2026; §15 of the Turkish document)

These are the answers to the open questions of the design. Where they conflict with the earlier
sections of the design document, they apply.

1. **Switching to advanced geometry is one-way; the way back is only Undo.** Once the tree has
   been edited, the template form closes. The undo stack must include the switch itself (it must
   be possible to return in a single step to the template state before the switch).
2. **A truncated (clipped) block or pin is a WARNING.** Its volume falls back to a stochastic
   estimate and it is marked separately in the power map; in pin-by-pin depletion it is an ERROR
   (as proposed).
3. **The fuel pin cross section supports three shapes: cylinder, hexagon and square** (previously
   only concentric cylinders). Regions (fuel / gap / cladding) can be nested in the same shape; the
   outermost boundary is the cell pitch. Builder, script, model check (outer region size smaller
   than the pitch), analytic depletion volume (square: a², hexagon: (√3/2)·d² flat to flat) and
   preview support this. The orientation of a hexagonal pin cross section must match the lattice
   in which the pin is placed (measured). In addition, **a hexagonal ring must be possible as a
   reflector around a square assembly**: in target layout (a) the content of the hexagonal ring
   blocks is the user's choice (reflector block or fuel); the example uses a reflector, and a fuel
   block is also built in a test.
4. **Per-face side boundary conditions are implemented in this wave** (moved out of the
   out-of-scope list). A rectangular outer boundary can take a separate condition on four faces
   (−x, +x, −y, +y), a hexagonal outer boundary on six faces (vacuum / reflective / periodic;
   periodic pairs must be consistent). The quarter core example (`pwr_ceyrek_kor`) is corrected to
   two reflective symmetry faces + two vacuum outer faces; the "+89 pcm" note in its description is
   removed, and the k of the quarter and the full core agree within 2σ (acceptance test).
5. **Every control rod is a separate volume/instance; it is not shared with another location.**
   Sharing the same definition at other locations (through distribcell) does NOT apply to control
   rods: every rod placement carries its own identity, its own insertion and its own volume
   (depletion and tallies see this volume separately). Groups exist only to drive several rods at
   once (optional); a rod is a member of at most one group.

Results of these decisions in the examples: [ORNEKLER.en.md](ORNEKLER.en.md) (sections "Advanced
geometry examples", "Physics acceptance tests of the geometry tree" and "Quarter-symmetric
core").
