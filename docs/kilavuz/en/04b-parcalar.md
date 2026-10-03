<a id="parcalar"></a>
## 4.2 Components

Components are the reusable building blocks placed in assemblies and in the core: **pins**
(fuel pin, guide tube, control rod; each one an OpenMC *universe*) and MTR type **plate-type
fuel elements**. The component list is on the left of the page and the editor of the selected
component on the right. This tab is not shown for a spherical assembly (a sphere only has
material shells).

Components are built from materials: if there is no material yet, the add buttons are
disabled and the page says "A material is needed first" ([4.1](04a-malzemeler.md#malzemeler)).

### Components card (list)

| Button | What it does |
|---|---|
| Pin ▾ | Adds a pin from a template; the materials are selected automatically **by their roles**. Menu: **PWR fuel pin** (fuel, fuel-cladding gap, cladding, coolant), **Guide tube** (water-filled tube: cladding + coolant), **Control rod** (absorber moving axially in a guide tube; offered only in a 3D model with a lattice). Shown only for core types that use pins. |
| Plate | Adds an MTR plate-type fuel element (23 plates). Offered only in the plate model (core type "Plate-type fuel element (MTR)"). |
| Copy | Adds a copy of the selected component (for example fuel pins with two different enrichments). |
| Delete | Deletes the selected component; if it is used, it asks first. |

The template dimensions are PWR 17×17 (Westinghouse) values: pellet 0.4096 cm, cladding
inner/outer 0.418/0.475 cm; guide tube 0.561/0.602 cm; absorber 0.433 cm. If no material with
the role the template needs exists (for example no absorber material), the missing roles are
named; the material of the region is marked in red as "— Select material —" and a ⚠ appears
next to the component in the list.

In the list, control rods are shown with the suffix "· control" and plate elements with
"· plate".

### Pin card

| Field | Meaning | Unit | Typical range | Common mistake | Spec key |
|---|---|---|---|---|---|
| **Name** | Name of the pin. Assembly maps, the core and the power distribution refer to it by this name; renaming updates every reference (lattice keys, core fill, axial layers, power target). | — | `yakit_cubugu`, `kilavuz_boru`, `kontrol_cubugu` (ASCII) | The same name as a material or another component (red warning below the name box) | `cubuklar[].ad` |
| **Type** | **Fixed pin** or **Control rod (moves axially)**. A control rod can only be chosen in a 3D model with a lattice (assembly, core map, drum fill); if the option is not available the field is hidden. | — | — | A control rod in a 2D model: error "a control rod needs a 3D model (core height undefined)" | `cubuklar[].tur` (`silindirik` \| `kontrol`) |
| **Cross section** | Shape of the regions: **Cylinder (concentric circles)**, **Square** or **Hexagon**. For square and hexagon the "radius" in the table is the half size: square side 2r, hexagon flat-to-flat 2r. The outermost boundary is the cell pitch. | — | cylinder (LWR, SFR); square/hexagon for special designs | Leaving the orientation of a hexagonal pin incompatible with the lattice (below) | `cubuklar[].kesit` (`silindir` \| `kare` \| `altigen`) |
| **Cross-section orientation** | Hexagonal cross section only: **y — flat faces left/right** or **x — flat faces top/bottom** (HexagonalPrism meaning). If the lattice is 'y' the pin must be 'x', if the lattice is 'x' the pin must be 'y' (measured). | — | — | Giving the same letter as the lattice: the pin corners extend into the neighbouring cell | `cubuklar[].kesit_yonelim` |
| **Absorber region** | In a control rod, the radial region that is inserted (absorber) axially. Regions are numbered from 1; the outer region cannot be selected. | — | usually region 1 | Selecting a region that is not an absorber: warning "the material of the absorber region (…) does not contain a strong neutron absorber" | `cubuklar[].emici_bolge` (counted from 0 in the JSON) |
| **Follower material** | The material that fills the part of the absorber region **below** the rod tip (follower). Fuel and absorber materials are not listed. | — | coolant (water) | Leaving it empty: warning "no follower material selected — when the rod is withdrawn its place stays empty (no material)" | `cubuklar[].izleyici_malzeme` |
| **Insertion** | How far the rod is inserted; the box and the slider change the same value. The rod is inserted **from the top**: 0 % fully withdrawn (no absorber in the active region), 100 % fully inserted. The insertion is measured over the **active fuel range**, not over the total height of the model. | % | 0–100; critical position of `pwr_kontrol` 87.85 ± 0.09 % (README) | Searching for the value here by hand: use the critical search in Analysis for the critical position ([4.8](04h-analiz.md#analiz)); if the rod is a member of an insertion group, the value here is ignored | `cubuklar[].daldirma` |
| **Tip position** | Absorber tip height computed from the insertion: z_tip = z_top − (insertion/100)·(z_top − z_bottom), over the active range. Read-only. | cm | — | If it says "2D model: define a height in the Core tab", the model is 2D and a control rod does not work | (computed, not stored) |

For a control rod the note at the bottom of the card summarises the rule: the part of the
absorber region below the tip is filled with the follower material; for the critical rod
position use "Critical search" and the "Control rod insertion" parameter in the Analysis tab.
In an axially layered model the active range consists of the layers that contain fissile
material (README "Three different heights").

### Radial regions card

The regions are ordered **from inside to outside**; the radius of each row is the **outer**
boundary of that region and must be larger than the previous one (the lower/upper bound of
each box comes from its neighbours). The last row is the **outer region**: it has no radius
and fills the surroundings of the pin up to the cell boundary (usually coolant).

| Column | Meaning | Unit | Typical range | Common mistake | Spec key |
|---|---|---|---|---|---|
| **Outer radius** | Outer radius of the region (half size for a square/hexagonal cross section). Stored with 6 decimals; the outer region shows "outer region". | cm | PWR: 0.4096 / 0.418 / 0.475; SFR (`sfr_altigen`): 0.32 / 0.345 / 0.395 | Not in increasing order ("radii must be in increasing order"); outer diameter larger than the assembly pitch ("the outer diameter of pin … is larger than the lattice pitch … — the pin extends into the neighbouring cell"; OpenMC does not treat this as an error, it silently cuts it) | `cubuklar[].bolgeler[].r` |
| **Material** | Material of the region. **Void (no material)** is a deliberate void choice (for example a fuel-cladding gap without gas). | — | fuel / gas / cladding / coolant | Leaving "— Select material —": error "… region material not selected"; an undefined material name | `cubuklar[].bolgeler[].malzeme` |
| **Region** | Readable description of the region (fuel, gap, cladding, outer region…). Read-only. | — | — | — | — |

| Button | What it does |
|---|---|
| Add region | Adds a new region just inside the outer region. |
| Delete region | Deletes the selected region (at least two regions must remain: inner region + outer fill). |
| Move in / Move out | Swaps the **material** of the selected region with its neighbour; the radii stay where they are. It cannot be moved into the outer region. |

In the JSON the region list is `cubuklar[].bolgeler` and every element has the form
`{"r": radius, "malzeme": name}`; the `r` value of the last element must be `null` ("the
radius of the last region must be empty").

### MTR type plate fuel element card

The cross section of a plate element is built in order along x: channel [cladding | fuel |
cladding] channel [cladding | fuel | cladding] … and one more channel at the end. The side
plates are located below and above the active region along y. Plate lists do not offer
materials that do not fit the role.

| Field | Meaning | Unit | Typical range | Common mistake | Spec key |
|---|---|---|---|---|---|
| **Name** | Name of the plate element. | — | `mtr_eleman` | The same name as another component or material | `plakalar[].ad` |
| **Number of plates** | Number of fuel plates in the element. | plate | 1–500; MTR 23 (`mtr_plaka`) | — | `plakalar[].plaka_sayisi` |
| **Fuel meat thickness** | Thickness along x of the fuel (meat) layer of one plate. | cm | 0.051 (MTR) | 0 or negative ("… must be greater than zero") | `plakalar[].et_kalinlik` |
| **Cladding thickness (each face)** | Cladding thickness on **each** of the two faces of the fuel layer (not the total). | cm | 0.038 (MTR) | Entering the total cladding (twice the cladding) | `plakalar[].zarf_kalinlik` |
| **Coolant channel gap** | Thickness of the coolant channel between two plates; there is a channel at both ends as well. | cm | 0.200 (MTR) | — | `plakalar[].kanal_kalinlik` |
| **Active width (y)** | Active (fuelled) width of the plate along y. | cm | 6.30 (MTR) | — | `plakalar[].plaka_genislik` |
| **Fuel material** | Material of the fuel layer (materials with the fuel role). | — | `u3si2_al` | Not selecting one ("fuel (meat) material not selected") | `plakalar[].et_malzeme` |
| **Cladding material** | Material of the cladding (structural; Al preferred in the template). | — | `al6061` | — | `plakalar[].zarf_malzeme` |
| **Coolant** | Coolant in the channels. | — | `su` | — | `plakalar[].sogutucu` |
| **Side plate thickness** | Thickness of the side plates below and above the active region; 0 builds no side plates. | cm | 0.475 (MTR) | Entering 0 and not noticing that the side plate material has no effect | `plakalar[].yan_levha_kalinlik` |
| **Side plate material** | Material of the side plates; "Same as cladding" can be chosen. Disabled when the thickness is 0. | — | `al6061` | — | `plakalar[].yan_levha_malzeme` |
| **Element outer size (x × y)** | Computed outer size: x = n·(2·cladding + fuel) + (n + 1)·channel, y = width + 2·side plate. Read-only. | cm | `mtr_plaka`: 7.7210 × 7.2500 | The element pitch in the core lattice being smaller than this size (the element is cut) | (computed, not stored) |

A plate element is a finite box. When it is used in a core lattice (for example
`ornekler/mtr_kor.json`) the lattice pitch must equal the element size and be square;
otherwise the region outside the element stays undefined (`docs/ORNEKLER.md` "Changes needed
in the core").

### Drums card

The library of control drum (rotating drum) **definitions** (`tamburlar[]`). The card is shown
only in **advanced geometry** mode or when the model already has a drum definition; that it is
hidden in template mode is deliberate: the drums of the **compact core with control drums**
template do not use this library, their dimensions are the drum fields on the **Geometry** page
(`kor.tambur`, [4.4 Geometry](04d-geometri.md#geometri)). To use a definition in the tree, switch
to advanced geometry ([4.5](04e-geometri-gelismis.md#geometri-gelismis)).

| Field | What | Unit | `spec` |
|---|---|---|---|
| **Name** | name of the definition (placements refer to it by this name) | - | `tamburlar[].ad` |
| **Radius** | outer radius of the drum | cm | `yaricap` |
| **Drum body material** | drum body (e.g. beryllium) | - | `govde_malzeme` |
| **Absorber material** | absorber arc (e.g. B₄C) | - | `emici_malzeme` |
| **Absorber inner radius** | inner radius of the absorber arc (< radius) | cm | `emici_ic_yaricap` |
| **Absorber arc** | angular width of the absorber arc | ° | `emici_aci` |

The number, the centre radius and the rotation are not in the definition but in the **placement**
and the **rotation group** of the advanced geometry ([5.5](05-dersler.md#ders-tambur)).

<a id="triso"></a>
### TRISO card

The library of **TRISO fuel** (compact and pebble) definitions (`trisolar[]`). The card is shown
only in **advanced geometry** mode or when the model already has a TRISO definition. A definition
is used in the tree as a **component** ([4.5](04e-geometri-gelismis.md#geometri-gelismis)); a
compact is a cylinder, so in advanced geometry it needs a **3D** model (height on the root
container). Step-by-step example: [lesson 5.21](05d-ders-triso-varyans.md#ders-triso-varyans).

A TRISO particle is a set of concentric layers (inside out: kernel, buffer, IPyC, SiC, OPyC).
Particles are packed in the container; the remaining volume is filled with the matrix material.
The **+ TRISO** button offers two starting templates (not a certification; enter your own design):

- **AGR-1 compact (UCO):** kernel diameter 350 um, buffer 100, IPyC 40, SiC 35, OPyC 40 um;
  compact diameter 12.45 mm, length 25 mm, packing about 35 % (INL AGR-1 baseline design).
- **HTR-10 pebble (UO2):** kernel diameter 500 um, buffer 90, IPyC 40, SiC 35, OPyC 40 um; fuel
  zone radius 2.5 cm, outer radius 3.0 cm, about 8335 particles (IAEA-TECDOC-1382).

| Field | What | Unit | `spec` |
|---|---|---|---|
| **Name** | name of the definition (the component node refers to it by this name) | - | `trisolar[].ad` |
| **Shape** | **Compact (cylinder)** or **Pebble (sphere)** | - | `sekil` |
| **Compact radius / height** | the cylinder in which particles are packed | cm | `yaricap`, `yukseklik` |
| **Fuel sphere radius**, **Pebble outer radius** | the TRISO-filled sphere of the pebble and the outside of its graphite shell | cm | `yakit_yaricap`, `dis_yaricap` |
| **Matrix material** | material between the particles (graphite) | - | `matris_malzeme` |
| **Shell material (pebble)**, **Outer gas (pebble)** | between the fuel sphere and the outer radius; outside it (helium) | - | `kabuk_malzeme`, `dis_malzeme` |
| **Packing fraction (target)** | N*(4/3)*pi*r^3 / V_container; random <= 0.64 (CRP limit), regular <= pi/6 = 0.5236 | - | `paketleme` |
| **Placement** | **Random (RSP/CRP)**: `openmc.model.pack_spheres`; **Regular**: simple cubic lattice | - | `yontem` |
| **Seed** | seed of the random packing (same seed, same placement) | - | `tohum` |
| **Layers** | each row: the **outer** radius and material of the layer (increasing order) | cm | `katmanlar[].r`, `.malzeme` |

The summary line under the card gives the **particle count and the actual packing fraction**: with
random placement N = int(pf*V / V_p), so the actual fraction is within 1/N of the target; in the
regular cubic lattice the count is quantized, so the deviation can exceed 1 % (validation warns)
and the **actual** value is used. Random packing switches to close random packing (Jodrey-Tory)
above pf = 0.30 and setup gets slower. Particles are given to OpenMC through a
`create_triso_lattice` lattice (a local list per lattice cell instead of a cell search per particle:
required for speed).

| Finding (summary) | Level | Cause and fix |
|---|---|---|
| TRISO compact needs a 3D model | error | no height on the root container; enter a height |
| compact height differs from the model height | warning | particles are packed only over the compact height; the excess is matrix, a shortfall cuts them |
| packing fraction must be between ... | error | random <= 0.64, regular <= 0.5236 |
| actual packing in the regular lattice differs from the target by x % | warning | the cubic lattice count is quantized; the actual value is used |
| packing > 0.30: CRP is used, setup gets slower | warning | expected; models with many particles can take minutes to build |

**Limits.** This card is a teaching tool; its results are **not a certification**. The cell size (3 particle diameters, `HUCRE_CAP_KATI`), the 50 000-particle warning threshold (`UYARI_PARCACIK_SAYISI`) and the packing-fraction tolerance (1 %, `PF_TOLERANSI`) are measured **interface limits in the code, not physical thresholds**.

### Common findings

| Finding (summary) | Level | Cause and fix |
|---|---|---|
| at least two regions are needed (inner region + outer fill) | error | The pin has only an outer region; add at least one inner region with Add region. |
| radii must be in increasing order | error | The radius of a region is smaller than or equal to the previous one; correct the table from inside to outside. |
| … region material not selected | error | The template found no material for the role; select a material or deliberately Void (no material). |
| a control rod needs a 3D model | error | Give a height in the Geometry tab (3D) or make the pin a Fixed pin. |
| insertion must be between 0 % and 100 % | error | A value out of range in the JSON. |
| no follower material selected | warning | The place of the withdrawn rod stays empty; usually the coolant is selected. |
| the outer diameter of pin … is larger than the lattice pitch … | error | Increase the pitch of the assembly or reduce the radii ([4.3](04c-demet.md#demet)). |

All findings: [Troubleshooting](09-sorun-giderme.md#bulgu-turleri). Driving several control
rods together with control groups is a job for the advanced geometry
([4.5](04e-geometri-gelismis.md#geometri-gelismis)).
