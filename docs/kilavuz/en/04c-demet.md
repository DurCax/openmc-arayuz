<a id="demet"></a>
## 4.3 Assembly

An assembly is a regular arrangement of pins (and, if needed, plate elements, inner
assemblies or material cells) in a lattice; in OpenMC it is a **lattice**: a rectangular
assembly is a `RectLattice`, a hexagonal assembly a `HexLattice`. The page has the paintable
**Grid** on the left and, on the right, the **Assemblies** list, the properties of the
selected assembly (**Rectangular assembly** / **Hexagonal assembly** card), the **Component
palette** and the **Advanced** section.

This tab is shown only in models that use assemblies: single assembly (`tek_demet`),
rectangular and hexagonal full core (`kare_kafes`, `altigen_kafes`), drum-controlled core
(`tamburlu`; the fill may be a lattice) and the advanced model whose geometry contains a
lattice (`agac`). An assembly is built from the pins of the **Components** tab; if there is no
pin yet, the add buttons are disabled and the page says "A pin is needed first"
([4.2](04b-parcalar.md#parcalar)).

![Assembly tab: 17×17 grid on the left, assembly properties and component palette on the right](../resimler/en/ilk-hesap-demet.png)

### Assemblies card (list)

Every assembly is listed with its name and type ("demet_17x17 · rectangular 17×17",
"demet_hex · hexagonal, 7 rings").

| Button | What it does |
|---|---|
| Rectangular assembly | Adds a new 5×5 rectangular assembly filled with the fuel pin. The pitch starts at 1.33 times the outer diameter of the pin (at least 1.26 cm). Not offered in a hexagonal core map (`altigen_kafes`): the cell of a rectangular core map is square and that of a hexagonal map is hexagonal; the other type does not fit. |
| Hexagonal assembly | Adds a new hexagonal assembly with 5 rings (61 cells). Not offered in a rectangular core map (`kare_kafes`). |
| Copy | Adds a copy of the selected assembly (for example an assembly with a second enrichment). |
| Delete | Deletes the selected assembly; if it is used in the core map, in an axial layer or inside another assembly, it first tells where it is used and asks. |

In a single assembly model, if the core does not yet point to an assembly, the first assembly
added becomes the core assembly automatically; in an empty model the model is built as soon
as the first assembly is added. The type of the assembly (rectangular or hexagonal) is chosen
when it is added and **cannot be changed later** (changing the type would destroy the map);
if you need the other type, add a new assembly.

### Assembly card (properties)

| Field | Meaning | Unit | Typical range | Common mistake | Spec key |
|---|---|---|---|---|---|
| **Name** | Name of the assembly. The core map, axial layers, drum fill and nested assemblies refer to it by this name; renaming updates every reference. | — | `demet_17x17`, `demet_hex`, `tvs` (ASCII) | The same name as a material or another component: a red warning appears below the name box and the name is not changed | `demetler[].ad` |
| **Pitch** | Distance between the centres of two neighbouring cells (*pitch*). In a rectangular assembly the side of the cell, in a hexagonal assembly the **flat-to-flat** size of the cell. The lower limit of the box is the largest content in the map (pin outer diameter, plate element size or inner assembly size); the tooltip gives this limit and its reason. | cm | PWR 17×17: 1.26; BWR 10×10: 1.295; VVER-1000: 1.275; SFR (`sfr_altigen`): 0.9 | A pitch smaller than the pin outer diameter: error "the outer diameter of pin … is larger than the lattice pitch … — the pin extends into the neighbouring cell" (OpenMC does not treat this as an error, the cell silently cuts the pin) | `demetler[].adim` |
| **Size** | Rectangular assembly only: number of cells, columns (x) × rows (y). When enlarging, the new cells are filled with the component that occurs most often in the map; shrinking **deletes** the right/bottom part of the map and asks for confirmation first (enlarging does not bring the deleted part back; Ctrl+Z does). | cell | 17×17 (PWR), 10×10 (BWR), 1×1–200×200 | Thinking that intermediate values are applied while typing: the value is applied on Enter, on focus loss or with the arrow keys (typing "15" in place of "17" does not first crop the map to one column) | `demetler[].boyut` (`[nx, ny]`) |
| **Number of rings** | Hexagonal assembly only: number of rings including the centre; ring k has 6k cells (2 rings → 7, 7 rings → 127, 11 rings → 331 cells). Reducing it **deletes** the outer rings and asks for confirmation first. | — | SFR 7–10, VVER-1000 11 | Not counting the centre (an assembly with 2 rings has 7 cells, not 13) | `demetler[].halka_sayisi` (for a hexagon `boyut` = `[rings, rings]` is written for backward compatibility) |
| **Assembly outer fill** | Material that fills the region outside the assembly cells: the corner gaps of a hexagonal assembly, the rest of the cell when nested or in a full core, the rest of the core cylinder in a drum-controlled core. Materials with the fuel role are not listed; **Void (no material)** can be chosen. If a rectangular assembly is the single assembly model itself, the model boundary is the assembly envelope, this region is never reached and the field is hidden (its value is not deleted from the file). | — | coolant: water, sodium | Leaving it void: leaking neutrons are lost; choosing fuel by mistake (not listed, but possible in a hand-written file) | `demetler[].dolgu_disi` |

The size summary below the card gives the outer size of the assembly and the number of cells
(rectangular: "21.420 × 21.420 cm · 289 cells"; hexagonal: the bounding rectangle + "127
cells, 7 rings").

### Grid card (map)

The map is painted **with component names**; you do not see letters:

- **Left click / drag:** paints the component selected in the palette (the brush) into the
  cells. One press-drag-release stroke is **one change**: Ctrl+Z undoes it in one step.
- **Right click:** makes the component in that cell the brush (no need to search the palette).
- Cells are drawn with the colour and short name of the component; an undefined cell is light
  grey.
- In a hexagonal map the rings are numbered **from the centre outwards**; the cell positions
  are identical to the OpenMC `HexLattice` layout (`cekirdek/altigen.py`, verified by a test).

In the file the map is still stored as letters: row by row for a rectangular assembly (the
first row is the top one), and as a ring list **from outside to inside** for a hexagonal
assembly; each ring starts at the top ('y' orientation) or on the right ('x' orientation) and
proceeds clockwise. Letters are assigned automatically on saving (first letter of the name:
`yakit_cubugu` → `y`, `kilavuz_boru` → `k`) and existing letters are kept; old files are
written back unchanged. The `.` character is an undefined cell.

| Concept | Meaning | Spec key |
|---|---|---|
| Map | One string of letters per row (rectangular) or per ring (hexagonal). Visible only in the JSON; painted in the interface. | `demetler[].harita` |
| Letter key | Letter → component name mapping (pin, plate, inner assembly, material or `bosluk`). Visible only in the JSON. | `demetler[].anahtar` |
| Type | `kare` (RectLattice) or `altigen` (HexLattice); set by the add button. | `demetler[].tur` |

### Component palette card

The palette lists the components that **can really be placed** in this assembly: pins; inner
assemblies of the same type (rectangular in rectangular, hexagonal in hexagonal) that do not
create a loop (the assembly itself, or an assembly containing it, is not offered); plate
elements only in the plate model and in a rectangular assembly; as material cells, only
materials with the coolant/moderator role. Every component **already present** in the map is
always listed (no data is hidden). The default brush is the component that occurs most often
in the map. Inner assemblies that do not fit the pitch are listed below the palette with the
note "Inner assemblies that do not fit the pitch: …": to place an assembly as an inner
assembly, the pitch must be at least the size of that assembly.

| Button / field | What it does |
|---|---|
| Fill all | Fills all cells with the selected component (Ctrl+Z undoes it). |
| Ring selection | Hexagonal assembly only: the ring to fill ("Centre cell", "Ring 1 · 6 cells", …, "(outermost)"). |
| Fill ring | Fills all cells of the selected ring with the selected component (for example the outer ring with pins of a different enrichment). |

### Advanced section

| Field | Meaning | Unit | Typical range | Common mistake | Spec key |
|---|---|---|---|---|---|
| **Orientation** | Hexagonal assembly only: **Top/bottom faces horizontal (cell at the top)** = `y` or **Right/left faces vertical (cell on the right)** = `x`. Meaning of `HexLattice.orientation`: with `y` the first neighbour is at the top. The map is redrawn when the orientation changes. | — | mostly `y` for assemblies | Giving the assembly and the core lattice the same letter in a hexagonal full core: if the pin lattice of the assembly is `y`, the core lattice must be `x` (at 90° to each other; `vver1000_kor`, `sfr_met1000_kor`) | `demetler[].yonelim` (`x` \| `y`) |
| **All materials and Void cell in the palette** | Extends the palette: not only coolant/moderator but **all materials** and the **Void (no material)** cell can be chosen (for example a gas channel, a water hole, an empty position). Not saved; it only affects the palette view. | — | — | Using a void cell in place of coolant: there is no material in that cell and neutrons fly freely | (not saved) |

### Duct — JSON only

The hexagonal duct around hexagonal assemblies (SFR, VVER-440) is not edited in the interface
today; it is given in the file with the `demetler[].kilif` field and kept:

| Key | Meaning | Unit | Typical value |
|---|---|---|---|
| `kilif.ic_duz` | **Inner** flat-to-flat size of the duct | cm | SFR MET-1000 (`sfr_met1000_demet`): 15.0191 |
| `kilif.kalinlik` | Duct wall thickness | cm | SFR MET-1000: 0.3966 |
| `kilif.malzeme` | Duct material | — | HT-9, SS-316 |

The region between the outside of the duct and the boundary of the assembly cell is filled
with the **Assembly outer fill** material (the inter-assembly gap). A duct is built only in a
hexagonal assembly (warning "ignored" in a rectangular assembly); the pins must fit into the
duct: the outermost pin centres are at a distance (rings − 1)·pitch·√3/2, and the inner size
must be at least twice this plus two pin radii (error "pins do not fit into the duct"). The
**Empty start** template of the **Full core — hexagonal** card on the start screen builds a
7-assembly core by adding an SS-316 duct (inner size 10.30 cm, 0.30 cm wall) to the SFR
hexagonal assembly.

### Two pitfalls of hexagonal assemblies

- **Orientation letters.** In OpenMC the orientations of `HexLattice` and `HexagonalPrism`
  use the same letter but their definitions are opposite (one is "perpendicular to the y
  axis", the other "parallel to the y axis"). The orientation of the prism surrounding a
  hexagonal lattice is the **same letter** as the lattice orientation; this was verified by
  measurement. A wrong mapping caused a 2.4 % Δk error (README "Known pitfalls"; details in
  [6. Known pitfalls](06-sonuclar.md#tuzaklar)). The interface does this mapping itself; take
  care when editing the JSON by hand.
- **Duct apothem.** The apothem (centre to flat face) of the hexagonal pin envelope is
  `(rings − 1)·pitch·√3/2 + pitch/2`, not `(rings − 0.5)·pitch`. The latter looks right at the
  corners but leaves too much space at the flat faces. In a single hexagonal assembly without
  a duct the model boundary is this envelope.

### Common model check findings (`demet:<name>`)

| Finding (summary) | Level | Fix |
|---|---|---|
| map is empty | error | Paint the map (Fill all). |
| map has N rows but the size expects M rows / row N has … characters but … are expected | error | In a hand-written file the map and the **Size** do not agree; correct the size or repaint the map. |
| N rings expected, the map has M rows / ring N expects … elements | error | A hexagonal map is a list of rings from outside to inside; a ring of radius k must have 6k elements and the centre 1. |
| undefined letter in the map: 'x' | error | Repaint the cell with a component from the palette (the letter has no entry in the key). |
| letter 'x' points to an undefined name | error | A deleted or renamed component; repaint the cells. |
| the outer diameter of pin … is larger than the lattice pitch … | error | Increase the **Pitch** or reduce the pin radii ([4.2](04b-parcalar.md#parcalar)). |
| nested assembly '…' … does not fit into the assembly pitch | error | Make the pitch of the outer assembly at least the size of the inner assembly. |
| letter defined in the key but not used in the map | info | Harmless; cleaned up on saving. |
| pins do not fit into the duct | error | Increase `kilif.ic_duz` or reduce the pitch. |

All finding types: [9. Troubleshooting](09-sorun-giderme.md#bulgu-turleri). Placing assemblies
in the core map: [4.4 Geometry](04d-geometri.md#geometri); placing an assembly inside another
shape (for example in the middle of a hexagonal ring):
[4.5 Advanced geometry editor](04e-geometri-gelismis.md#geometri-gelismis).
