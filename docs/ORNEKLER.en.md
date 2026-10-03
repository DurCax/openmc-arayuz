# Example models

Türkçe: [ORNEKLER.md](ORNEKLER.md). This is the English version of `docs/ORNEKLER.md`; numbers,
tables and source names are identical. If the two ever differ, `docs/ORNEKLER.md` is
authoritative.

Every JSON file under `ornekler/` is a model that can be opened. The gallery title, category and
level are read from the file's own metadata fields (`baslik`, `baslik_en`, `aciklama_en`,
`kategori`, `seviye`, and `referans` if present; see `cekirdek/ornek_bilgi.py`). The titles below
are the files' `baslik_en` values. Benchmark results and the C/E table: [VV.en.md](VV.en.md).

The Source column says where the numbers of the model come from. Values marked **"not
verified"** were not read from a primary document; they are typical or open-source values, meant
for teaching, and must not be used as design values.

## List

| File | Title | Category | Level | Reference | Source |
|---|---|---|---|---|---|
| pwr_pinhucre.json | PWR fuel cell (pin) | pwr | introductory | calculation: regression anchor k∞ 1.3570 ± 0.0020 | this tool's anchor |
| pwr_17x17.json | PWR 17×17 fuel assembly | pwr | introductory | — | Westinghouse typical |
| pwr_3b.json, pwr_eksenel.json, pwr_kontrol.json | PWR assembly variants | pwr | intermediate | — | Westinghouse typical |
| pwr_tukenme.json | PWR pin cell — depletion | pwr | advanced | — | — |
| **pwr_mox_demet.json** | PWR MOX assembly (3 zones) | pwr | intermediate | — | OECD/NEA–US NRC PWR MOX/UO2 core transient benchmark (2003), "MOX 4.3%" assembly |
| **pwr_gd_tukenme.json** | Gadolinia rod depletion | pwr | advanced | — | Westinghouse dimensions; Gd2O3 composition typical (not verified) |
| **pwr_smr_kor.json** | Square SMR-like full core (52 assemblies) | pwr | intermediate | — | teaching design |
| **pwr_ceyrek_kor.json** | Quarter-symmetric PWR core | pwr | advanced | — | quarter of pwr_smr_kor (per-face boundary) |
| ***pwr_kare_altigen_halka.json*** | Square core inside a hexagonal reflector ring | pwr | advanced | calculation: this tool's measurement 1.06492 ± 0.00086 | teaching design (G-4) |
| **pwr_beavrs_kor.json** | BEAVRS-like PWR core (193 assemblies) | pwr | advanced | — (simplified) | MIT BEAVRS, cycle 1 HZP ARO |
| **bwr_10x10.json** | BWR 10x10 assembly (water channel) | bwr | intermediate | — | ATRIUM-10-like, open-source dimensions (not verified) |
| **vver1000_demet.json** | VVER-1000 assembly (Gd rods) | vver | intermediate | — | NEA/NSC/DOC(2002)10 layout + TVS-2M/TVSA pin dimensions (not verified) |
| **vver1000_kor.json** | VVER-1000 full core (163 assemblies) | vver | advanced | — | 163-assembly layout; loading for teaching |
| sfr_altigen.json | SFR hexagonal assembly | sfr | intermediate | — | typical |
| **sfr_met1000_demet.json** | SFR metal-fuel assembly (MET-1000) | sfr | intermediate | — | NEA/NSC/R(2015)9 Tables 2.16–2.22 |
| **sfr_met1000_kor.json** | SFR full core (MET-1000) | sfr | advanced | calculation: 1.0355 ± 0.0078 | NEA/NSC/R(2015)9 |
| mtr_plaka.json | MTR plate fuel element | research | intermediate | — | typical U3Si2 MTR |
| **mtr_kor.json** | MTR research reactor core | research | intermediate | — | inspired by the IAEA 10 MW MTR benchmark (not identical) |
| tamburlu_kor.json | Compact core with control drums | research | advanced | — | — |
| ***altigen_tambur_halkasi.json*** | Hexagonal core with a control-drum ring | research | advanced | calculation: this tool's measurement 1.04745 ± 0.00084 | teaching design (G-4) |
| ***kafes_tamburlu_yansitici.json*** | Lattice core with a drum-controlled reflector | research | advanced | calculation: this tool's measurement 1.05046 ± 0.00097 | teaching design (G-4) |
| godiva_kriter.json | Godiva critical sphere | benchmark | introductory | experiment: ICSBEP HEU-MET-FAST-001 | ICSBEP |
| **kriter_jezebel.json** | Jezebel plutonium sphere | benchmark | introductory | experiment: ICSBEP PU-MET-FAST-001 | ICSBEP |
| **kriter_flattop25.json** | Flattop-25 reflected sphere | benchmark | intermediate | experiment: ICSBEP HEU-MET-FAST-028 | ICSBEP |
| **kriter_lct008.json** | B&W critical lattice (LCT-008) | benchmark | advanced | experiment: ICSBEP LEU-COMP-THERM-008/1 | ICSBEP |
| **kriter_vver1000_ugd.json** | VVER-1000 LEU assembly benchmark (NEA) | benchmark | advanced | calculation: NEA/NSC/DOC(2002)10 | NEA/NSC/DOC(2002)10 |
| zirh_kure.json | Shielding sphere (fixed source) | shielding | intermediate | — | — |
| **htgr_kompakt.json** | HTGR TRISO compact (AGR-1 dimensions, 5 mm slice) | research | advanced | - | INL AGR-1 baseline design; 35 % packing |
| **htgr_pebble.json** | HTR-10 pebble (Wigner-Seitz sphere) | research | advanced | - | IAEA-TECDOC-1382 dimensions |
| **zirh_agirlik_pencere.json** | Deep-penetration shield (weight window lesson) | shielding | advanced | - | lesson 5.21: window FOM measurement |
| **zirh_katmanli.json** | Layered shield (fixed source) | shielding | intermediate | — | PNNL-15870 concrete; Cf-252 Watt values (not verified) |

Category and level are stored as identifiers (`arastirma`, `kriter`, `zirh`; `giris`, `orta`,
`ileri`); the table shows their English meaning.

Bold files were added in Wave 2 (16 files); the three bold-italic files are the **advanced
geometry (tree, schema 3)** examples added in Wave G-4. The "reference" of these three is not an
external value but the tool's own measurement (for regression). An "experiment" reference is a
measured critical assembly (C/E); a "calculation" reference is a result of other codes.

## Example details

### Advanced geometry examples (Wave G-4)

All three were produced with the templates in `arayuz/geometri/sablonlar.py` (Geometry page >
template) and then saved in advanced mode (`kor.tur = "agac"`, `geometri` tree). All are **for
teaching**; they are not data of a real reactor. Assemblies and materials were copied from
existing examples (the pwr_17x17 / pwr_ceyrek_kor assemblies, the sfr_altigen assembly, the
tamburlu_kor beryllium).

- **pwr_kare_altigen_halka** (2D): a 5×5 square PWR core (checkerboard 2.4 %/3.1 %) sits in the
  square hole in the middle of a 5-ring hexagonal block lattice (pitch 30 cm). The blocks are
  SS-304 (a Ø6 cm water channel in every block, 0.4 cm water between blocks). The outermost layer
  is 20 cm of water; the faces are vacuum. The model check gives **16 "truncated block"
  WARNINGS**. This follows from the design (a hexagonal lattice cannot surround a square hole
  without truncation); the volume falls back to a stochastic estimate. The fuel is not
  truncated; the fuel volume is analytic.
- **altigen_tambur_halkasi** (3D, 80 cm): 19 SFR assemblies (3 rings, core 'x', pin 'y'), a
  beryllium hexagonal reflector (outer apothem 48.7 cm), 6 B4C (90 % B-10) drums (r = 6 cm,
  centre at 36 cm, facing the flat faces). U-10Mo was written with explicit isotopes (U-235
  19.75 % by weight). At 19.75 % the enrichment shortcut assumes U-234/U-235 = 0.008 (model
  check warning); the price of this is that the "enrichment" sweep is not offered on the Analysis
  page for this example.
- **kafes_tamburlu_yansitici** (3D, 200 cm): a 3×3 square PWR core, a cylindrical beryllium
  reflector (r = 80 cm), 4 B4C (natural) drums (r = 8 cm, centre at 42 cm, opposite the core
  faces). Drums facing the **corners** of the core as in the design document (§4.3) (centre at
  60 cm, 45°) gave only ~600 pcm (Δk) of worth in a coarse measurement. Moved closer to the faces,
  the worth became ~3000 pcm (Δk) (coarse, 2000 × 40).

**pcm definition (all drum worths in this section):** pcm = × 10⁵. Drum worth is given in two
forms: Δk = k₂ − k₁ (pcm = Δk × 10⁵; difference in k, not a reactivity difference) and
Δρ = (k₂ − k₁)/(k₁k₂) = 1/k₁ − 1/k₂ (pcm = Δρ × 10⁵). Here k₂ is k with the drums out (180°) and
k₁ with the drums in (0°).

Measured drum worths (G-4 physics acceptance tests, below):
altigen_tambur_halkasi k(0°) = 0.95139 ± 0.00150, k(180°) = 1.04533 ± 0.00166 →
total Δk = 9394 pcm, Δρ = 9446 pcm.

### Physics acceptance tests of the geometry tree (testler/test_geometri_fizik.py, 01.10.2026)

OpenMC 0.16.0, ENDF/B-VIII.0, 6 threads. Criterion: differences in k within 2σ; volumes within
3σ in every measurement and mostly within 1σ.

| Acceptance test | Measurement | Result |
|---|---|---|
| Infinite medium, square: 3×3 lattice (two letters, same assembly) vs single assembly | 1.09889 ± 0.00095 / 1.09900 ± 0.00121 | 0.07σ, passed |
| Infinite medium, hexagonal: assembly in a single-position core lattice vs single assembly | 1.46689 ± 0.00068 / 1.46634 ± 0.00070 | 0.56σ, passed |
| tamburlu_kor in the tree (gelismise_gec) vs template, rotation 180° | 1.00719 ± 0.00110 (both) | 0σ (same model, same seed), passed |
| same, rotation 0° | 0.96346 ± 0.00092 (both) | 0σ, passed; k(0) < k(180) by 30σ, worth Δk = 4372 pcm, Δρ = 4506 pcm |
| 6 drums, rotation 0/60/120/180° | 0.95139 / 0.97516 / 1.02525 / 1.04533 (σ 0.0015–0.0019) | monotonic (steps 9.9σ, 18.6σ, 7.9σ), passed |
| INFO: single drum (one at 0°, five at 180°) | 1.03251 ± 0.00163 → single-drum Δk = 1282, Δρ = 1188 pcm | total / (6 × single) = 1.22 (Δk), 1.33 (Δρ); statistics ±0.23 (not an acceptance criterion). Rigorous remeasurement: 1.03 ± 0.05 (Δk), 1.12 ± 0.06 (Δρ) — "Drum interaction" |
| Symmetry: whole model 60° (donusum), drum 90° (chiral) | original 1.00094 ± 0.00108, part 0° 0.99960 ± 0.00138, part 60° 0.99891 ± 0.00134 | 1.18σ / 0.77σ, passed |
| Volume: square + hexagonal ring uo2_24 / uo2_31 | 1669.76 / 1660.1 ± 6.1; 1808.91 / 1812.1 ± 6.4 cm³ | 1.58σ / 0.49σ |
| Volume: hexagonal + drums u10mo | 62100.8 / 62143 ± 112 cm³ | 0.37σ |
| Volume: lattice + drum reflector uo2_31 | 139147 / 138621 ± 415 cm³ | 1.26σ |
| Pin cross-section volume: square-pin assembly uo2_24 | 177.167 / 177.164 ± 0.112 cm³ | 0.03σ |
| Pin cross-section volume: hexagonal-pin assembly u10mo | 45.0499 / 45.0051 ± 0.0293 cm³ | 1.53σ |

Notes:
- That the total drum worth came out **larger** than single drum × 6 (1.22, G-4) was remeasured
  with a rigorous method (section "Drum interaction" below): with Δk the ratio is
  **1.03 ± 0.05**, i.e. consistent with additivity. The 1.22 of G-4 came from a low-statistics
  single-drum worth (1282 ± 233 pcm; new measurement 1532 ± 78 pcm, a difference of ~1σ).
- Because the 60° symmetry model is already 60° symmetric, a builder that ignored the transform
  would also pass the test. The fast test [GF3] therefore also checks that a 30° rotation (not a
  symmetry) changes the material map (730 of 3000 points differ). In addition, it is checked
  without Monte Carlo that the models at 0° and 60° are pointwise identical to the original
  model.
- In tamburlu_kor, the tree and the template gave **bit-for-bit** the same k with the same seed:
  the expansion is equivalent.

### Drum interaction: altigen_tambur_halkasi (araclar/tambur_etkilesim.py, 01.10.2026)

Method: OpenMC 0.16.0, ENDF/B-VIII.0, 6 threads. Each configuration with a **separate seed**
(1001–1006, independent runs), 20000 particles × 230 batches, **100 inactive** → 2.6 × 10⁶ active
histories (~11 times the 4000 × 80/20 = 2.4 × 10⁵ of G-4). In every run the Shannon entropy
plateau (kosucu.entropi_yakinsama) **was reached**. "In" = rotation 0° (absorber arc faces the
core), "out" = 180°. Single and multiple drum models are built with list placements; the
orientation of the single drum at 0° is **pointwise identical in the material map** to the
original (ring mode) model (fast test GS14: 1500 points in the drum disc = ring 0°, 1500 points
outside = ring 180°). pcm = × 10⁵; Δk = k_out − k_X; Δρ = (k_out − k_X)/(k_out·k_X).
Uncertainties are 1σ; the σ of the ratios ignores the correlation through the common "out" run
(upper bound).

| Configuration (drums in) | k | Δk [pcm] | Δρ [pcm] |
|---|---|---|---|
| all out (original model, 180°) | 1.04766 ± 0.00056 | — | — |
| 1 drum (0) | 1.03234 ± 0.00054 | 1532 ± 78 | 1416 ± 72 |
| 2 adjacent (0, 1) | 1.01897 ± 0.00054 | 2869 ± 78 | 2687 ± 73 |
| 2 opposite (0, 3) | 1.01667 ± 0.00054 | 3098 ± 77 | 2909 ± 73 |
| 3 (0, 2, 4; 120° apart) | 0.99966 ± 0.00053 | 4800 ± 77 | 4583 ± 74 |
| 6 drums (all in) | 0.95286 ± 0.00051 | 9480 ± 75 | 9497 ± 76 |

| Ratio (additive = 1) | with Δk | with Δρ |
|---|---|---|
| 6 drums / (6 × single) | 1.031 ± 0.053 | 1.117 ± 0.057 |
| 2 adjacent / (2 × single) | 0.936 ± 0.054 | 0.949 ± 0.054 |
| 2 opposite / (2 × single) | 1.011 ± 0.057 | 1.027 ± 0.058 |
| 3 drums / (3 × single) | 1.044 ± 0.055 | 1.078 ± 0.057 |

Interpretation (not an acceptance criterion; goes to the professor's review):
- With Δk all ratios are at most ~1.2σ away from 1: at this level of statistics the drum worths
  are **consistent with additivity**. The adjacent pair, at 0.94 ± 0.05, points slightly towards
  shadowing (not significant); the opposite pair is 1.01.
- With Δρ the 6-drum ratio is 1.12 ± 0.06. Most of this is definition, not physics:
  Δρ = Δk/(k_out·k_X), and with 6 drums k_X (0.953) is smaller than with one drum (1.032); for
  this reason alone the ratio grows by a factor k_single/k_6 = 1.083 (1.031 × 1.083 = 1.117). The
  Δk and Δρ ratios are therefore given separately.
- The explanation "with a single absorber the azimuthal flux tilt lowers the single-drum worth
  (compensation)" was **not needed** in this measurement: the low single-drum worth of G-4 was
  within statistics. A small effect of the tilt may remain below this sensitivity (~5 %); it was
  not measured.

### VVER-1000 assembly and core

- Assembly: 331 positions = 300 UO2 3.7 % + 12 TVEG (UO2 3.6 % + 4 % Gd2O3) + 18 guide tubes +
  1 central tube; 11 rings, pin pitch 1.275 cm, assembly pitch 23.6 cm, **no duct**.
  The Gd and guide tube positions were read from the cartogram in NEA/NSC/DOC(2002)10 Figure A.1,
  and the 60° rotational symmetry was checked.
- Pin: pellet outer r 0.3785, central hole r 0.07, cladding inner/outer r 0.386/0.455 cm (He gap).
  These are commonly quoted open-source values for TVS-2M/TVSA; they were **not verified** from a
  primary design document. The NEA benchmark (kriter_vver1000_ugd.json) uses its own simplified
  pin: fuel r 0.386, cladding outer 0.4582, no hole and no gap.
- Water between assemblies: in the core, the boundary of a single hexagonal assembly without a
  duct is the pin envelope (23.358 cm). To build the 23.6 cm container, the assembly is given a
  "duct" **0.01 cm thick made of the same material as the moderator**; physically it is an
  assembly without a duct. This is why the checker's "single assembly with a duct" warning
  appears and is a false alarm (see "Changes needed in the core layer").
- Core: an 8-ring hexagonal core lattice (169 positions); the 6 corners of the outer ring are
  steel-water reflector → 163 assemblies (test: testler/test_ornekler.py OR2). Core lattice 'x',
  assembly pin lattice 'y'. Three assembly types (A 2.0 % without Gd, B 3.0 % + TVEG, C 4.4 % +
  TVEG, outer ring). Radial reflector: 20 cm, 80 % steel + 20 % water, homogeneous; the loading
  pattern is not the map of a real VVER-1000.

### SFR MET-1000 (NEA/NSC/R(2015)9)

- Driver assembly: 271 pins (10 rings), fuel r 0.3236, HT-9 cladding outer r 0.3857 cm, duct
  outer 15.8123 cm / wall 0.3966 cm, assembly pitch 16.2471 cm.
- **Wire wrap:** the specification homogenises the wire into the cladding (the cladding outer
  radius is enlarged). The model follows the same path; mass conservation is tested with the
  volume fractions of the active zone: fuel 39.00, HT-9 25.66, Na 35.34 % (Table 2.20; test OR4).
- The pin pitch is **not given** in the specification; the volume fractions do not depend on
  the pitch. p = 0.90539 cm was chosen so that the pin lattice fits exactly to the inner face of
  the duct.
- Core: 379 positions (78 inner + 102 outer drivers, 114 reflectors, 66 shields, 15 + 4
  control), extracted by colour sampling from the image of Figure 2.7; all counts agree with the
  legend (test OR5). 11 axial layers (lower structure, lower reflector, 5 active slices, bond
  sodium, plenum ×2, upper structure; total 480.20 cm). Outside the active zone, and for the
  reflector/shield/control assemblies, the materials are homogeneous with the Table 2.20
  fractions. Control rods are fully withdrawn; the absorber is just above the active core.
- The single-assembly example is built with a 1-ring hexagonal core lattice
  (halka_sayisi = 1); the sodium gap between assemblies is in the model.

### BEAVRS-like core

193 17×17 assemblies, three enrichments (1.6 %: 65, 2.4 %: 64, 3.1 %: 64); the Pyrex layout and
all pin dimensions are from the MIT BEAVRS OpenMC model (models/openmc/beavrs). The layout in the
BEAVRS OpenMC model gives **1268** Pyrex rods; the specification table says 1266 — the
difference could not be resolved. Grid spacers, nozzles, the steel baffle, core barrel, neutron
shield and pressure vessel are **not** modelled; the measured critical boron (975 ppm) is
therefore not a reference for this model. When the multi-type power distribution
(`guc_dagilimi.cubuklar`, Agent 8b) is merged, it counts all three fuel types together; until
then test OR10 is skipped with a PRECONDITION (ÖN_KOŞUL).

### Quarter-symmetric core (and the mirror symmetry of the loading pattern)

A symmetry plane is built with a **reflective** boundary: the model that is solved is the core
obtained by **mirroring** the quarter across both axes. This has a consequence, and the first
attempt gave a wrong result because of it:

> **A checkerboard pattern has 180° rotational symmetry but NO mirror symmetry.** When the
> quarter is mirrored, the A/B pattern swaps places in the neighbouring quarters, i.e. the
> quarter-core model solves *a different loading*. Measured: a difference of **+260 pcm** between
> the quarter and the full core even with the same side boundary. For this reason the loading of
> `pwr_smr_kor.json` was changed to concentric zones (B = 3.1 % outer, A = 2.4 % inner).
> `testler/test_ornekler.py` OR9 compares the mirror image of the quarter with the map of the
> full core — a free check without Monte Carlo.

The boundary condition is given **per face** (Wave G, §15 decision 4):
`kor.sinir.yuzler = {"-x": reflective, "+y": reflective, "+x": vacuum,
"-y": vacuum}`. The two symmetry faces are reflective and the two outer faces are vacuum; the
quarter core thus solves the same physics as the full core (four vacuum faces). In the earlier
version a single condition was applied to all four side faces, so the outer faces were also
reflective (+89 pcm). This limitation and the note have been removed.

Measured (01.10.2026, 20000 × 160 batches, 60 inactive, 6 threads):

| Model | k | time |
|---|---|---|
| pwr_smr_kor (full, 4 vacuum faces) | 1.05881 ± 0.00059 | 132 s |
| pwr_ceyrek_kor (per face) | 1.05922 ± 0.00066 | 113 s |

The difference is 41 pcm, i.e. **0.46σ** (SLOW test OR12, criterion 2σ: passed).

- With the same number of particles the quarter core is **not** markedly faster (the number of
  neutrons tracked is the same). The gain is in statistics: the number of neutrons per assembly
  is four times larger, so assembly and pin powers come out more precise in the same time. (The
  statement "~4 times faster" in the earlier document has been corrected.)

### Others

- **pwr_mox_demet:** the fissile Pu percentage (2.5/3.0/5.0) was interpreted as fissile Pu
  (Pu-239 + Pu-241) by weight relative to heavy metal; since the benchmark gives no boron value,
  HZP without boron (560 K).
- **pwr_gd_tukenme:** a single Gd pin cell is not representative (an infinite Gd lattice); the Gd
  pellet at the centre of a 5×5 supercell is divided into 5 rings of equal area. Measured (OR13,
  5 MWd/kg): remaining Gd-157 fraction from inside to outside
  0.74 / 0.63 / 0.42 / 0.09 / 0.003 (01.10.2026; CECM, steps ≤ 1 MWd/kg; 1500 × 40/15; k∞
  1.1233 → 1.0646 ± 0.0049) — the spatial self-shielding ("onion skin") is clearly visible.
  **Step sensitivity:** the old settings (predictor, 0.02 / 0.08 / 0.9 / 2 / 2 MWd/kg) gave
  0.77 / 0.71 / 0.60 / 0.33 / 0.014 with the same statistics: the predictor uses the
  beginning-of-step rates (shielded by the outer ring) over the large step and under-burns the
  inner rings. The example therefore uses CECM with steps ≤ 1 MWd/kg. The 16 MWd/kg value was
  not remeasured.
  **k∞ does not peak in this model:** since only one of the 25 pins contains Gd, its reactivity
  hold-down is weak and fuel depletion dominates. In a real assembly (12–20 Gd pins) a peak is
  seen.
- **bwr_10x10:** no water channel wall; the box wall + bypass water form a homogeneous band of
  1.145 cm.
- **mtr_kor:** the plate element of the core layer is a finite box and the core lattice has a
  square pitch; the element is completed to a square (side plate 0.7105 cm, no water between
  elements).
- **zirh_katmanli:** neutron transport; c_H_in_H2O for the hydrogen in concrete (a common
  approximation).

## Accuracy presets and run times

The Wave 2 full cores open with **"Quick test"** (1000 particles × 60 batches, 20 inactive); the
three G-4 examples open with "Normal" (measured time well below 15 minutes). One can switch to
"Normal" under Run settings. Measured "Normal" (10000 × 150/40) times, 8 threads, while the
machine was shared with other runs:

| File | Normal time [s] | k (Normal) |
|---|---|---|
| vver1000_kor.json | 66.1 | 1.09907 ± 0.00097 |
| sfr_met1000_kor.json | 281.5 | 1.03014 ± 0.00053 |
| pwr_beavrs_kor.json | 104.5 | 1.00187 ± 0.00093 |
| pwr_smr_kor.json | 81.4 (6 threads) | 1.06005 ± 0.00086 (01.10; the earlier 1.08345 was the old checkerboard loading) |
| pwr_ceyrek_kor.json | 75.5 (6 threads) | 1.06118 ± 0.00098 (01.10, per-face boundary) |
| pwr_kare_altigen_halka.json | 56.0 (6 threads) | 1.06492 ± 0.00086 (2D) |
| altigen_tambur_halkasi.json | 177.3 (6 threads) | 1.04745 ± 0.00084 (drums at 180°) |
| kafes_tamburlu_yansitici.json | 60.2 (6 threads) | 1.05046 ± 0.00097 (drums at 180°) |
| mtr_kor.json | 114.1 | 1.16884 ± 0.00095 (30.09, after the U3Si2-Al correction; before 1.16743 ± 0.00098) |

For full cores, the 40 inactive batches of the "Normal" setting are borderline for source
convergence (the Shannon entropy was still decreasing); if you compare k values, increase the
number of inactive batches (SLOW test OR12 uses 20000 × 160/60). For the comparison of the
quarter and the full core see the section "Quarter-symmetric core" above.

All are below 15 minutes.

**Advanced setting (documented, not the default):** ≥ 10–20 axial bins for the power map
("guc_dagilimi.eksenel_dilim") and ≥ 5 seeds (Run settings > multiple seeds). For pin power
statistics in a full core at least 50000 particles × 300 batches are recommended; the time is
about 10 times that of "Normal".

## Changes needed in the core layer (revealed by these examples)

- In a single hexagonal assembly without a duct, the assembly pitch (cell) cannot be larger than
  the pin envelope; the water-"duct" workaround is needed.
- The plate element is a finite box; in a core lattice the region outside the element remains
  undefined (the lattice pitch must equal the element size and be square).
- `sema.kullanilan_malzemeler` does not count material names in map/layer keys → a wrong "unused
  material" info finding for these materials.
