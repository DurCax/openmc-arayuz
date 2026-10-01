<a id="dersler"></a>
# 5. Guided lessons

Each lesson starts with an example file, goes step by step through the interface and ends with
an **expected result**. The lessons are ordered from easy to hard; lesson 1 is a prerequisite for
the others. Examples are opened from the example list of the start screen or with **File › Open…**
and they open as a **copy**: the files under `ornekler/` are test references and are never
overwritten. Use **File › Save as…** to keep your own changes.

| Lesson | Topic | Example file | Level |
|---|---|---|---|
| [5.1](#ders-demet) | Assembly k∞ | `ornekler/pwr_17x17.json` | introductory |
| [5.2](#ders-tam-kor) | Full core (square map) | `ornekler/pwr_smr_kor.json` | intermediate |
| [5.3](#ders-altigen-kor) | Hexagonal assembly and hexagonal core | `ornekler/sfr_altigen.json`, `ornekler/vver1000_kor.json` | intermediate |
| [5.4](#ders-kare-altigen) | Square core + hexagonal ring | `ornekler/pwr_kare_altigen_halka.json` | advanced |
| [5.5](#ders-tambur) | Placing a drum in any geometry | `ornekler/kafes_tamburlu_yansitici.json`, `ornekler/altigen_tambur_halkasi.json` | advanced |
| [5.6](#ders-tukenme) | Depletion and nuclide selection | `ornekler/pwr_tukenme.json` | advanced |
| [5.7](#ders-guc) | Power map and F_ΔH | `ornekler/pwr_3b.json` | intermediate |
| [5.8](#ders-benchmark) | Benchmark and C/E | `ornekler/godiva_kriter.json` and `kriter_*` | introductory–advanced |
| [5.9](#ders-kritik-arama) | Critical search | `ornekler/pwr_17x17.json`, `ornekler/pwr_kontrol.json`, `ornekler/tamburlu_kor.json` | intermediate |
| [5.10](#ders-rapor) | Report and conformity annex | any run | intermediate |

**Where do the expected results come from?** Every value has a source: the `referans.olcum` field
of the example file, [VV.md](../../VV.md), [ORNEKLER.md](../../ORNEKLER.md) or the measurement tables
of [README.md](../../../README.md). The measurement condition (particles × batches / inactive
batches) is given in each lesson. A Monte Carlo result is statistical: with the same settings but a
different seed or thread count the last digits differ; **a 2–3σ difference with different settings
is normal**. Uncertainties are 1σ standard uncertainties everywhere. How to read a result:
[6. Interpreting results](06-sonuclar.md#sonuclar).

Page names in the sidebar: **Materials**, **Components**, **Assembly**, **Geometry**,
**Run settings**, **Run**, **Analysis**, **Depletion**. Only the pages that make sense for the
model are shown ([4.0 Window layout](04-sekmeler.md#pencere-duzeni)).

---

<a id="ders-demet"></a>
## 5.1 Assembly k∞: PWR 17×17

**Example file:** `ornekler/pwr_17x17.json` · **Level:** introductory · **Estimated time:** 15 minutes
(run 1–3 minutes)

**Goal.** Read the model of a fuel assembly page by page, understand why **k∞** (the infinite
multiplication factor) is computed, run it and compare the result with the measured value. If this
is your first time, follow [2. First calculation in 15 minutes](02-ilk-hesap.md#ilk-hesap) first;
this lesson focuses on the physics of the same model.

**Steps.**

1. Open **PWR 17×17 fuel assembly** from the example list of the start screen. The model header
   states the type: single fuel assembly, 2D, eigenvalue (k-eff).
2. **Materials** page: there are four materials (`uo2`, `helyum`, `zirkaloy4`, `su`). Double-click
   `su` (water); it is a library material and is stored with its generation parameters such as
   temperature and boron ([4.1 Materials](04a-malzemeler.md#malzemeler)). Close it with **Cancel**
   without changing anything.
3. **Components** page: the fuel pin and the guide tube. Select the fuel pin; in the **Radial
   regions** card the fuel, gap and cladding regions are listed from the inside out. The outer radii
   of the regions must increase and the outermost region must stay smaller than the cell pitch
   ([4.2 Components](04b-parcalar.md#parcalar)).
4. **Assembly** page: a 17×17 square map; the coloured palette shows which pin is in which cell.
   The **Pitch** is 1.26 cm (distance between pin centres).
5. **Geometry** page: the configuration template is a single assembly; the **Radial boundary** is
   `reflective` and the model is 2D (infinite height). The preview on the right draws the xy
   cross-section of the assembly.
6. **Why k∞?** When all outer boundaries are reflective, no neutron can escape; the model is an
   infinitely repeated assembly medium. The result card then shows **k∞** and gives no criticality
   verdict: k∞ > 1 does not mean that the reactor is supercritical, only that the fuel carries
   excess reactivity ([6.1 Statistics](06-sonuclar.md#istatistik)).
7. **Run settings** page: the **Accuracy preset** should be **Normal** (10 000 particles × 150
   batches, 40 inactive). The line below gives the expected k-eff uncertainty
   ([4.6 Run settings](04f-hesap-ayarlari.md#hesap-ayarlari)).
8. Go to the **Run** page. The line under the button should say that the model is ready to run or
   give the number of warnings; the button is not enabled before the preview has been drawn
   ([Draw first, then run](06-sonuclar.md#once-ciz)). Press **Run** (or **F9**).
9. Watch the convergence plot during the run: after the inactive batches the cumulative mean should
   settle into a flat band. The **Shannon entropy** badge should say **Converged**.

**Expected result.** k∞ = **1.18325 ± 0.00075** ([README.md](../../../README.md), table of measured
reference results; 44 s with 24 threads). Your value should be within 2–3σ of this. A larger
difference or a lost-particle warning signals a problem
([9. Troubleshooting](09-sorun-giderme.md#sorun-giderme)).

**What we learned / check questions.**

- If all side boundaries were `vacuum`, would the result be k∞ or k-eff? Would the value of a single
  assembly grow or shrink? (Leakage → k-eff, it shrinks.)
- By roughly what factor must particles × active batches grow to halve σ? (σ ∝ 1/√N → about 4.)
- Regression anchor: the pin cell of the same fuel, `ornekler/pwr_pinhucre.json`, must give
  k∞ = 1.3570 ± 0.0020. Why is the assembly lower? (Water in the guide tubes and heterogeneity
  inside the assembly.)

---

<a id="ders-tam-kor"></a>
## 5.2 Full core: square SMR core

**Example file:** `ornekler/pwr_smr_kor.json` (also `ornekler/pwr_ceyrek_kor.json`) ·
**Level:** intermediate · **Estimated time:** 30 minutes (Normal run 1–3 minutes)

**Goal.** Place assemblies on a core map, see how leakage lowers k-eff in a finite core and build
quarter-core symmetry with the right boundary condition.

**Steps.**

1. Open the **square SMR full core (52 assemblies)** example. The model header shows the type
   "full core (square map)".
2. The **Assembly** page has two assemblies: `demet_24` (2.4 %) and `demet_31` (3.1 %); both are
   PWR 17×17 assemblies.
3. **Geometry** page, **Core map** card: a 12×12 map, **Cell pitch** (assembly pitch) 21.42 cm.
   Letters: `A` → `demet_24` (inner zone), `B` → `demet_31` (outer belt), `s` → `su` (two rows of
   water reflector around). Pick an item from the palette and click cells to paint; a right click
   picks the content of that cell ([4.4.3 Core map](04d-geometri.md#geo-harita)). Do not change
   the map.
4. On the same page the height is **3D, layered**: bottom water 20 cm, active 200 cm, top water
   20 cm ([4.4.8 Axial layers](04d-geometri.md#geo-katmanlar)). The **Radial**, **Bottom** and
   **Top boundary** are `vacuum`: neutrons escape and the result is **k-eff**.
5. **Run settings**: the example opens with **Quick test** (1 000 × 60, 20 inactive); this is only
   to see that the model runs (σ of a few hundred pcm). Set the **Accuracy preset** to **Normal**.
6. **Run**. Look at the k-eff interpretation on the result card (supercritical / critical /
   subcritical; criterion |k − 1| ≤ 2σ). Check the entropy badge: in a full core, 40 inactive
   batches are **borderline** for source convergence
   ([6.2 Source convergence](06-sonuclar.md#kaynak-yakinsamasi)).
7. (Optional) **Quarter core:** open `ornekler/pwr_ceyrek_kor.json`. Only a quarter of the map is
   present; on the **Geometry** page **Per-face radial boundary** is on: the −x and +y faces are
   `reflective` (symmetry planes), the +x and −y faces `vacuum` (outer faces)
   ([4.4.6 Height and boundary conditions](04d-geometri.md#geo-yukseklik)).

**Expected result.**

- Full core, **Normal** (10 000 × 150, 40 inactive): k-eff = **1.06005 ± 0.00086**
  ([ORNEKLER.md](../../ORNEKLER.md), table of run times per accuracy preset; 81 s with 6 threads).
- Full core and quarter core at 20 000 × 160 batches / 60 inactive: **1.05881 ± 0.00059** and
  **1.05922 ± 0.00066**; difference 41 pcm (Δk × 10⁵), i.e. 0.46σ ([ORNEKLER.md](../../ORNEKLER.md),
  quarter-core section).

**What we learned / check questions.**

- Where does the difference between the k∞ of the same assemblies (lesson 5.1, ~1.18) and the k-eff
  of the core (~1.06) come from? (Leakage and the lower enrichment of the inner zone.)
- Why can the quarter core not be built with a **checkerboard** loading? (The reflective symmetry
  plane **mirrors** the quarter; a checkerboard has no mirror symmetry, so the mirrored core is a
  different loading — measured difference +260 pcm. [ORNEKLER.md](../../ORNEKLER.md))
- Is the quarter core faster for the same number of particles? (No; the gain is in per-assembly
  statistics.)

---

<a id="ders-altigen-kor"></a>
## 5.3 Hexagonal assembly and hexagonal core

**Example files:** `ornekler/sfr_altigen.json` (assembly), `ornekler/vver1000_kor.json` (core) ·
**Level:** intermediate · **Estimated time:** 40 minutes

**Goal.** Learn the ring layout of a hexagonal lattice and the **orientation** rule; place hexagonal
assemblies on a hexagonal core map.

**Steps — hexagonal assembly.**

1. Open the **SFR hexagonal assembly** example. On the **Assembly** page the map is hexagonal, not
   square: **Number of rings** 7 (centre included; 1 + 6 + 12 + … = 127 pins), **Pitch** 0.9 cm,
   **Orientation** `y`. On a hexagonal map the positions are written ring by ring from the outside
   in ([4.3 Assembly](04c-demet.md#demet)).
2. On the **Geometry** page the radial boundary is reflective; the result is again k∞. This assembly
   has no duct; the space outside the pins is filled by the **Outside assembly** fill (`sodyum`).
3. Keep the **Run settings** as in the file (10 000 × 120, 30 inactive). **Run**.

**Expected result (assembly).** k∞ = **1.46634 ± 0.00070** ([README.md](../../../README.md), table of
measured reference results; 53 s with 24 threads). Because this is a fast-spectrum, U-10Mo fuelled,
sodium-cooled assembly, k∞ is much larger than for the PWR assembly.

**Steps — hexagonal core.**

4. Open the **VVER-1000 full core (163 assemblies)** example. The **Assembly** page has three
   assemblies (`tvs_a20`, `tvs_b30`, `tvs_c44`); each has 11 rings and a pin lattice with
   orientation **`y`**.
5. **Geometry** page: type "full core (hexagonal map)", **Number of rings** 8 (169 positions),
   **Assembly pitch** 23.6 cm, core lattice orientation **`x`**. The six corners of the outer ring
   are filled with `R` (steel-water reflector); the other 163 positions are assemblies. The radial
   reflector is 20 cm.
6. **Orientation rule:** if the pin lattice of the assembly is `y`, the core lattice must be `x`
   (the two at 90°). To try it, temporarily set the core orientation to `y`: the model check panel
   shows an **error** for every assembly saying that the orientation of assembly 'tvs_a20' ('y')
   equals the core orientation and that the assembly corners spill into the neighbouring cell.
   Undo with **Ctrl+Z**. The measurement behind this rule and the `HexLattice`/`HexagonalPrism`
   orientation pitfall: [6.5 Known pitfalls](06-sonuclar.md#tuzaklar).
7. The example opens with **Quick test**. Set the **Accuracy preset** to **Normal** and **Run**.

**Expected result (core).** k-eff = **1.09907 ± 0.00097**, **Normal** (10 000 × 150, 40 inactive;
66 s with 8 threads; [ORNEKLER.md](../../ORNEKLER.md), table of run times per accuracy preset). The
loading pattern is for teaching; it is not a real VVER-1000 map.

**What we learned / check questions.**

- How many positions does a hexagonal lattice with 8 rings have? (1 + 3·n·(n−1) = 169.)
- What does the **pitch** measure in a hexagonal lattice? (Flat to flat, not corner to corner.)
- Why is the duct apothem of a hexagonal assembly `(rings − 1)·pitch·√3/2 + pitch/2` and not
  `(rings − 0.5)·pitch`? ([6.5 Known pitfalls](06-sonuclar.md#tuzaklar))

---

<a id="ders-kare-altigen"></a>
## 5.4 Square core + hexagonal ring

**Example file:** `ornekler/pwr_kare_altigen_halka.json` · **Level:** advanced · **Estimated time:**
45 minutes (Normal run ~1 minute)

**Goal.** Read an arrangement that the templates cannot build (a square-lattice core surrounded by
a hexagonal block lattice) as a **geometry tree**, and build the same thing in your own model from a
template. Concepts: [4.5 Advanced geometry editor](04e-geometri-gelismis.md#geometri-gelismis).

**Steps — reading the example.**

1. Open the **square core + hexagonal reflector ring** example. The **Geometry** page opens directly
   in the advanced editor (tree + cross-section + property form); the note at the top says the
   template wizard is closed.
2. Read the tree from top to bottom:
   - **Root — hexagon a=121.244 (x)**: the root container, a hexagonal cross-section with
     orientation `x` (apothem 121.24 cm).
   - **Inside: lattice blok_kafesi (hexagonal, 5 rings)**: the inside of the root is a hexagonal
     lattice with 5 rings and a 30 cm pitch; its letter `B` points to the component
     `yansitici_blok` (SS-304 block + 6 cm diameter water channel).
   - **Placement: kare_cekirdek (list, 1)**: a **rectangular** hole (107.1 × 107.1 cm) is cut out of
     the middle of the lattice, and **lattice cekirdek_kafesi (square 5×5)** is put into it (a 5×5
     PWR assembly lattice with a 21.42 cm pitch, checkerboard 2.4 % / 3.1 %).
   - **Ring 1 (20 cm)**: a 20 cm water belt on the outside. Radial boundary `vacuum`; the model is 2D.
   - **Components (1)**: `yansitici_blok` is defined once and used as the same universe at every
     position.
3. Select the placement row and read the form: **Mode** List, one position (0, 0), hole
   cross-section Rectangle. In the cross-section the selected node is coloured and the others are
   faded.
4. Look at the strip at the bottom: there is a **16 truncated positions** warning. The square hole
   cuts some hexagonal blocks; it is not possible to surround a square core with a hexagonal lattice
   **without truncation**. This is not an error but a consequence of the design: the volume of the
   truncated blocks is computed stochastically. Blocks completely under the hole are hidden on the
   map with `.` (hidden position, info). The fuel is not truncated; the fuel volume is analytical
   ([4.5.10](04e-geometri-gelismis.md#gg-kesik)).
5. The **Run settings** are Normal (10 000 × 150, 40 inactive). **Run**.

**Expected result.** k-eff = **1.06492 ± 0.00086** (the `referans.olcum` field of the example; Normal,
56 s with 6 threads). This value is not an external reference but the tool's own measurement (for
regression).

**Steps — building it yourself.**

6. Open `ornekler/pwr_17x17.json` (a single assembly in template mode). Optionally add
   **SS-316 stainless steel** first with **Materials › Add from library…**; the template proposes the
   first structural material of the model as block material (`zirkaloy4` if you add nothing).
7. On the **Geometry** page choose **Square center + hexagonal ring** from the **Configuration
   template** list. In the window that opens, the fields are filled from the components of the
   model: core assembly A, core assembly B (checkerboard) (here both `demet_17x17`), core size (n×n)
   5, lattice pitch 21.42 cm, block pitch (flat to flat) 30 cm, number of block rings 5, block
   content "reflector block (material + channel)", block material, block channel radius 3 cm, gap
   fill `su`, outer reflector thickness 20 cm, reflector material `su`, height 2D. Press **OK**.
8. The model switches to advanced geometry and the tree has the same structure as the example. The
   model check again gives the **16 truncated positions** warning (same geometry). **Ctrl+Z** returns
   to the single assembly before the template.
9. In the block content list a "fuel: …" option appears only if the model contains a **hexagonal**
   assembly: the content of the hexagonal ring blocks can be a reflector block or a hexagonal fuel
   assembly ([GEOMETRI_MODELI.md](../../GEOMETRI_MODELI.md) section 15, decision 3).

**What we learned / check questions.**

- Why is a truncated position a warning and not an error? When does it become an error? (A
  truncated fuel instance with **Pin-by-pin burnup** on; [4.9 Depletion](04i-tukenme.md#tukenme).)
- Why use a **component** instead of copying the same block inline into every position? (One
  universe; distribcell and depletion instance counts are not split.)
- Why does the k-eff of your own model differ from the example? (A single-enrichment assembly and a
  different block material.)

---

<a id="ders-tambur"></a>
## 5.5 Placing a drum in any geometry

**Example files:** `ornekler/kafes_tamburlu_yansitici.json`, `ornekler/altigen_tambur_halkasi.json`
(and the model of lesson 5.4) · **Level:** advanced · **Estimated time:** 60 minutes

**Goal.** Use a control drum in any geometry, not only in the "drum-controlled core" template: a
placement (hole + content), the "facing the core" rule and a **group** that rotates the drums
together. Form details: [4.5.8 Placement form](04e-geometri-gelismis.md#gg-yerlesim) and
[4.5.9 Group and component forms](04e-geometri-gelismis.md#gg-grup).

**Rule (all modes).** The absorber arc of the drum is on the local +x side; the placement turns this
side towards the facing centre. **Rotation = group value + offset**: **0° the absorber faces the
core** (inserted, lowest k), **180° the absorber faces outwards** (withdrawn, highest k).

**Steps — A. Lattice core + drum reflector (reading and rotating).**

1. Open the **lattice core + drum reflector** example. In the tree: **Root — rectangle 64.26×64.26**,
   **Inside: lattice kor_kafesi (square 3×3)**, **Ring 1** (outer cross-section a cylinder,
   r = 80 cm; content `berilyum`) and under it **Placement: tamburlar_yansitici (ring, 4)** →
   **Content: component tambur_b4c**. At the bottom **Groups (1)** → **Group: tamburlar
   (rotation = 180)**.
2. Select the placement row. Form: **Mode** Ring, **Count** 4, **Center radius** 42 cm,
   **Start angle** 0°, **Natural cross-section (drum circle)** checked, **Facing the core** towards the
   centre (centre x 0, centre y 0), **Group** `tamburlar`, **Offset** 0. The drums face the four
   **faces** of the core.
3. Select the group row. The **Value** is 180° (drums withdrawn). See in the cross-section that the
   absorber arcs face outwards. Set the value to **0**: the arcs turn to the core. Do one run at 180°
   and one at 0° (Normal).
4. The **definition** of the drum (radius 8 cm, body `berilyum`, absorber `b4c`, absorber inner
   radius 6 cm, 120° arc) is in the library (`tamburlar[]`), not in the placement; the placement only
   says where and how many.

**Expected result (A).** 180°: k-eff = **1.05046 ± 0.00097** (`referans.olcum` of the example; Normal,
10 000 × 150, 40 inactive). In a rough measurement (2 000 × 40) the total drum worth was
~**3000 pcm** (Δk × 10⁵); the same drums placed to face the **corners** of the core (centre 60 cm,
45°) gave only ~600 pcm ([ORNEKLER.md](../../ORNEKLER.md)). These two numbers are rough; the
difference of your own Normal runs should be of this order.

**Steps — B. Hexagonal core + drum ring (group sweep).**

5. Open the **hexagonal core + drum ring** example: 19 SFR assemblies (3-ring core, lattice `x`, pin
   lattice `y`), a hexagonal beryllium ring (outer apothem 48.7 cm) with 6 B₄C drums inside:
   **Count** 6, **Center radius** 36 cm, **Start angle** 30° (the drums face the flat sides of the
   core).
6. On the **Analysis** page set **Calculate** to **Reactivity coefficient (parameter sweep)**;
   **Parameter**: rotation group (`grup_donme`, degrees); **Start** 0, **End** 180, **Number of
   points** 5. Check the **Estimated time** and press **Start sweep**
   ([4.8 Analysis](04h-analiz.md#analiz)).

**Expected result (B).** Strict measurement ([ORNEKLER.md](../../ORNEKLER.md), drum interaction
section, 20 000 × 230 batches, 100 inactive): all out (180°) **1.04766 ± 0.00056**, all in (0°)
**0.95286 ± 0.00051**; total worth Δk = **9480 ± 75 pcm** (Δk × 10⁵), Δρ = **9497 ± 76 pcm**
(Δρ × 10⁵). The G-4 measurement for 0° / 60° / 120° / 180° gave 0.95139 / 0.97516 / 1.02525 /
1.04533 (σ 0.0015–0.0019): k increases **monotonically** with the rotation angle. With Normal
settings at 180° the `referans.olcum` value of the example is **1.04745 ± 0.00084**.

**Steps — C. Placing drums in the square core + hexagonal ring.**

This part adds 6 drums to the geometry of lesson 5.4 (square core, hexagonal block ring, 20 cm water
belt on the outside). Every step was checked with the model check; all steps are done in the
interface.

7. Open `ornekler/pwr_kare_altigen_halka.json` (or the model you built in 5.4) and save it to your
   own file with **File › Save as…** (for example `kare_altigen_tambur.json`).
8. **Materials › Add from library…**: add **beryllium (Be)** (name `berilyum`) and **B₄C — boron
   carbide** (name `b4c`). **File › Save**.
9. **Drum definition.** Add a new drum definition with the drum form on the **Components > Drums**
   page (the same definition as in `ornekler/kafes_tamburlu_yansitici.json`): name `tambur_b4c`,
   radius 8 cm, body material `berilyum`, absorber material `b4c`, absorber inner radius 6 cm,
   absorber arc angle 120°. The definition is written to the `tamburlar[]` section (`ad`, `yaricap`,
   `govde_malzeme`, `emici_malzeme`, `emici_ic_yaricap`, `emici_aci`); the placement fields (count,
   centre, rotation) belong to the placement and the group, not to the definition.
10. On the **Geometry** page select the **Ring 1 (20 cm)** row in the tree and press **+ Placement**
    in the toolbar. Because the model has a drum definition, the content of the new placement is
    automatically **component tambur_b4c** and **Natural cross-section (drum circle)** is checked.
11. Fill in the placement form: name `tambur_halkasi`, **Mode** Ring, **Count** 6, **Center radius**
    131.2 cm, **Start angle** 30°, **Facing the core** towards the centre (centre x 0, centre y 0),
    **Offset** 0.
    *Where do the numbers come from?* The inner apothem of the water belt is 121.24 cm and the outer
    apothem 141.24 cm; the centre of a drum of radius 8 cm must lie between 129.24 and 133.24 cm along
    the normal of a flat side. The flat-side normals of an `x`-oriented hexagon are at 30°, 90°, …,
    330°; a start angle of 30° and 6 drums put one drum on each side.
12. Only two **warnings** should remain in the model check panel: the 16 truncated positions (from
    lesson 5.4) and "control drum in a 2D model: no axial leakage; the drum worth comes out too high".
    Try it: set the **Start angle** to 0°; the drums move to the **corners** of the hexagon and an
    **error** appears for each one saying that the hole of 'tambur_halkasi' crosses the inner
    boundary of the region (the inner corner is 121.24 × 2/√3 ≈ 140.0 cm from the centre). Set it
    back to 30°.
13. Press **+ Group** in the toolbar; a new rotation group appears under **Groups** (value 0). Select
    the group: name `tamburlar`, type rotation, **Value** 180, and tick `tambur_halkasi` under
    **Members**. (The same link can be made with the **Group** box of the placement form.)
14. In the xy cross-section see that the absorber arcs face outwards. **File › Save**. With Normal
    settings do one run at 180° and one at 0°.

**Expected result (C).** This is your design; there is **no** reference measurement. Check:
k(0°) < k(180°) must hold and the difference must be statistically significant:
|k₁₈₀ − k₀| > 2·√(σ₁₈₀² + σ₀²). Because the model is 2D, the drum worth comes out too high (there is
no axial leakage; the model check warns about it). For a more realistic value, untick
**2D (infinite height)** in the root form, give a **Height** and set the bottom/top boundaries to
`vacuum`.

**What we learned / check questions.**

- Why does a larger drum (for example r = 12 cm) give a model check error? (The hole does not fit in
  the water belt: a 24 cm diameter circle does not fit in a 20 cm belt.)
- What sets the direction in which the drums face the core? (In ring mode ψᵢ = φᵢ + 180 + D; with
  the facing centre in the middle, the absorber arc of every instance turns to the centre,
  D = group value + offset.)
- Why do Δk and Δρ give different numbers for the drum worth? (Δρ = Δk/(k₁·k₂); the difference
  grows as the k values move away from 1. Always state which quantity pcm is applied to.)
