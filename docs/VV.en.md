# Verification and validation (V&V)

Türkçe: [VV.md](VV.md). This is the English version of `docs/VV.md`. Numbers, tables, source
names and section numbers are identical. The Turkish file is the one checked by the tests (BM4);
if the two ever differ, `docs/VV.md` is authoritative.

This document gives the tool's benchmark suite and the measured results. The numbers are
identical to the `referans.olcum` fields in `ornekler/*.json`; `testler/test_benchmark.py`
checks this (BM4).

**Environment:** OpenMC 0.16.0, ENDF/B-VIII.0 (HDF5, OpenMC's official library, 294 K).
First five benchmarks (Agent 9): 8 OpenMP threads, 29.09.2026. V&V set (`vv/…`,
Wave S-3): 12 OpenMP threads, 01.10.2026. In both cases the machine was shared with other Monte
Carlo jobs; the run times are therefore upper bounds. The number of inactive batches is given in
each row as "batches/inactive".

**Acceptance criterion:** |C − E| ≤ 3·√(σc² + σe²) and σc ≤ 30 pcm. This is the project's own
criterion; it does not come from a standard (docs/STANDARTLAR.en.md §6 items 15–17). A
benchmark that exceeds the criterion is accepted only if it is explained below as a library bias
(there is none at present; the largest deviations are PU-MET-FAST-008 at 2.62σ and
U233-SOL-INTER-001 at 2.19σ — inside the criterion, noted below).

Experimental (C/E) and calculation-to-calculation comparisons are kept SEPARATE: in an
experimental benchmark E is a measured critical assembly (ICSBEP); in a calculation-to-calculation
benchmark E is the result of other codes and is not the "true" value.

## Experimental benchmarks (C/E)

| Example | Benchmark | E ± σe | C ± σc | C − E [pcm] | diff/σ | C/E | particles | batches/inactive | time [s] | Result |
|---|---|---|---|---|---|---|---|---|---|---|
| godiva_kriter.json | HEU-MET-FAST-001 (Godiva) | 1.0000 ± 0.0010 | 1.00038 ± 0.00025 | +38 | 0.37 | 1.00038 | 100000 | 150/50 | 25.3 | passed |
| kriter_jezebel.json | PU-MET-FAST-001 (Jezebel) | 1.0000 ± 0.0020 | 0.99996 ± 0.00023 | −4 | 0.02 | 0.99996 | 50000 | 150/50 | 5.5 | passed |
| kriter_flattop25.json | HEU-MET-FAST-028 (Flattop-25) | 1.0000 ± 0.0030 | 1.00106 ± 0.00026 | +106 | 0.35 | 1.00106 | 100000 | 150/50 | 51.8 | passed |
| kriter_lct008.json | LEU-COMP-THERM-008, case 1 | 1.0007 ± 0.0012 | 1.00067 ± 0.00021 | −3 | 0.02 | 0.99997 | 100000 | 260/50 | 451.4 | passed |
| vv/kriter_hst009a.json | HEU-SOL-THERM-009, case 1 | 0.9990 ± 0.0043 | 1.00088 ± 0.00024 | +188 | 0.44 | 1.00188 | 100000 | 200/50 | 343.0 | passed |
| vv/kriter_hst013.json | HEU-SOL-THERM-013, case 1 | 1.0012 ± 0.0026 | 0.99854 ± 0.00025 | −266 | 1.02 | 0.99734 | 100000 | 200/50 | 361.2 | passed |
| vv/kriter_hst032.json | HEU-SOL-THERM-032 (ORNL-10) | 1.0015 ± 0.0026 | 0.99851 ± 0.00020 | −299 | 1.15 | 0.99701 | 100000 | 200/50 | 449.5 | passed |
| vv/kriter_imf003.json | IEU-MET-FAST-003, case 2 | 1.0000 ± 0.0017 | 1.00013 ± 0.00018 | +13 | 0.08 | 1.00013 | 100000 | 200/50 | 63.3 | passed |
| vv/kriter_imf004.json | IEU-MET-FAST-004, case 2 | 1.0000 ± 0.0030 | 1.00482 ± 0.00020 | +482 | 1.60 | 1.00482 | 100000 | 200/50 | 52.2 | passed |
| vv/kriter_lct006_01.json | LEU-COMP-THERM-006, case 1 | 1.0000 ± 0.0020 | 1.00085 ± 0.00027 | +85 | 0.42 | 1.00085 | 100000 | 200/50 | 640.6 | passed |
| vv/kriter_lct006_02.json | LEU-COMP-THERM-006, case 2 | 1.0000 ± 0.0020 | 1.00119 ± 0.00027 | +119 | 0.59 | 1.00119 | 100000 | 200/50 | 559.3 | passed |
| vv/kriter_lct006_03.json | LEU-COMP-THERM-006, case 3 | 1.0000 ± 0.0020 | 1.00116 ± 0.00030 | +116 | 0.57 | 1.00116 | 100000 | 200/50 | 706.0 | passed |
| vv/kriter_lct006_04.json | LEU-COMP-THERM-006, case 4 | 1.0000 ± 0.0020 | 1.00108 ± 0.00026 | +108 | 0.54 | 1.00108 | 100000 | 200/50 | 711.2 | passed |
| vv/kriter_lct006_05.json | LEU-COMP-THERM-006, case 5 | 1.0000 ± 0.0020 | 1.00084 ± 0.00025 | +84 | 0.42 | 1.00084 | 100000 | 200/50 | 525.1 | passed |
| vv/kriter_lst002a.json | LEU-SOL-THERM-002, case 1 | 1.0038 ± 0.0040 | 0.99994 ± 0.00020 | −386 | 0.96 | 0.99615 | 100000 | 200/50 | 322.4 | passed |
| vv/kriter_lst002b.json | LEU-SOL-THERM-002, case 2 | 1.0024 ± 0.0037 | 0.99578 ± 0.00023 | −662 | 1.79 | 0.99340 | 100000 | 200/50 | 226.8 | passed |
| vv/kriter_lst003c.json | LEU-SOL-THERM-003, case 3 | 0.9995 ± 0.0042 | 1.00396 ± 0.00028 | +446 | 1.06 | 1.00446 | 100000 | 200/50 | 221.6 | passed |
| vv/kriter_mmf001.json | MIX-MET-FAST-001 (Planet) | 1.0000 ± 0.0016 | 0.99937 ± 0.00017 | −63 | 0.39 | 0.99937 | 100000 | 200/50 | 49.9 | passed |
| vv/kriter_pci001.json | PU-COMP-INTER-001 (HISS/HPG) | 1.0000 ± 0.0110 | 1.00739 ± 0.00016 | +739 | 0.67 | 1.00739 | 100000 | 200/50 | 582.4 | passed |
| vv/kriter_pmf002.json | PU-MET-FAST-002 (Jezebel-240) | 1.0000 ± 0.0020 | 1.00194 ± 0.00016 | +194 | 0.97 | 1.00194 | 100000 | 200/50 | 18.7 | passed |
| vv/kriter_pmf006.json | PU-MET-FAST-006 (Flattop-Pu) | 1.0000 ± 0.0030 | 0.99950 ± 0.00020 | −50 | 0.17 | 0.99950 | 100000 | 200/50 | 73.3 | passed |
| vv/kriter_pmf008.json | PU-MET-FAST-008 (Thor), 1D model | 1.0000 ± 0.0006 | 0.99836 ± 0.00018 | −164 | 2.62 | 0.99836 | 100000 | 200/50 | 53.1 | passed |
| vv/kriter_pmf011.json | PU-MET-FAST-011 | 1.0000 ± 0.0010 | 1.00016 ± 0.00021 | +16 | 0.16 | 1.00016 | 100000 | 200/50 | 402.6 | passed |
| vv/kriter_pmf018.json | PU-MET-FAST-018 | 1.0000 ± 0.0030 | 0.99789 ± 0.00018 | −211 | 0.70 | 0.99789 | 100000 | 200/50 | 65.6 | passed |
| vv/kriter_pst001.json | PU-SOL-THERM-001, case 1 | 1.0000 ± 0.0050 | 1.00119 ± 0.00027 | +119 | 0.24 | 1.00119 | 100000 | 200/50 | 304.5 | passed |
| vv/kriter_pst021.json | PU-SOL-THERM-021, case 3 | 1.0000 ± 0.0065 | 1.00100 ± 0.00026 | +100 | 0.15 | 1.00100 | 100000 | 200/50 | 93.3 | passed |
| vv/kriter_umf001.json | U233-MET-FAST-001 (Jezebel-233) | 1.0000 ± 0.0010 | 1.00025 ± 0.00018 | +25 | 0.25 | 1.00025 | 100000 | 200/50 | 18.4 | passed |
| vv/kriter_umf005.json | U233-MET-FAST-005, case 2 | 1.0000 ± 0.0030 | 0.99689 ± 0.00021 | −311 | 1.03 | 0.99689 | 100000 | 200/50 | 63.5 | passed |
| vv/kriter_umf006.json | U233-MET-FAST-006 (Flattop-23) | 1.0000 ± 0.0014 | 0.99985 ± 0.00020 | −15 | 0.11 | 0.99985 | 100000 | 200/50 | 132.4 | passed |
| vv/kriter_usi001.json | U233-SOL-INTER-001, case 1 | 1.0000 ± 0.0083 | 0.98178 ± 0.00022 | −1822 | 2.19 | 0.98178 | 200000 | 200/50 | 196.2 | passed |
| vv/kriter_ust008.json | U233-SOL-THERM-008 (ORNL-11) | 1.0006 ± 0.0029 | 0.99973 ± 0.00021 | −87 | 0.30 | 0.99913 | 100000 | 200/50 | 410.4 | passed |

C − E [pcm] = Δk × 10⁵ (difference in k; not the reactivity difference Δρ).

Notes:

- **V&V set (`vv/…`, 22 cases):** `araclar/vv_kriter_uret.py` converts, from the OpenMC inputs
  of mit-crpg/benchmarks (MIT licence, © 2011–2024 Paul Romano and contributors), only the
  models consisting of **concentric spherical shells** into the `kuresel` (spherical assembly)
  template; atom densities are lossless (atom/b-cm, per nuclide; natural C0, which is absent from
  ENDF/B-VIII.0, is expanded into C12/C13 at natural abundance), and the geometry is identical.
  E ± σe come from the same repository's `uncertainties.csv`. Every JSON carries the
  `referans.kaynak_model` and `referans.lisans` fields. The ICSBEP handbook text is not
  redistributed (STANDARTLAR.en.md §6 item 13). Rejected candidates: partially filled spheres
  (LEU-SOL-THERM-003 cases 1/6 and -002 case 3: void above the solution), cylindrical tanks
  (SHEBA, STACY, the HEU-MET-FAST-004 water tank), lattices (MIX-COMP-THERM-002) — the importer
  does not recognise these patterns or they lie outside the template.
- All ICSBEP models are the handbook's **simplified** benchmark models; atom densities and
  dimensions were compared one to one with the OpenMC/MCNP inputs in the `mit-crpg/benchmarks`
  repository (`icsbep/<benchmark>/`). E and σe come from the same repository's
  `icsbep/icsbep/uncertainties.csv` table (ICSBEP values).
- **LCT-008 model equivalence:** the model built by the tool (the "tamburlu" core type without
  control drums, a 93×93 pin lattice, 76.2 cm tank) and the original OpenMC geometry of mit-crpg
  were run with the same library: original 1.0006 ± 0.0004 (100000 × 80 active batches), tool
  1.00067 ± 0.00021 — the difference is within statistics. The pin map was extracted from the
  original geometry by point queries (4961 pins).
- The earlier Godiva measurement (0.99957 ± 0.00054, 20000 particles) is consistent with the new
  measurement (1.00038 ± 0.00025) within 1.4σ.

## Calculation-to-calculation benchmarks

| Example | Benchmark | E ± σe | C ± σc | C − E [pcm] | diff/σ | particles | batches/inactive | time [s] | Result |
|---|---|---|---|---|---|---|---|---|---|
| kriter_vver1000_ugd.json | NEA VVER-1000 LEU (UGD), S5, burnup 0 | 1.3185 ± 0.0040 | 1.31910 ± 0.00021 | +60 | 0.15 | 100000 | 250/50 | 574.6 | passed |
| sfr_met1000_kor.json (info) | OECD/NEA SFR MET-1000, BOC | 1.0355 ± 0.0078 | 1.03014 ± 0.00053 | −536 | 0.69 | 10000 | 150/40 | 281.5 | consistent (σc > 30 pcm, not a reference run) |

C − E [pcm] = Δk × 10⁵ (difference in k; not the reactivity difference Δρ).

Notes:

- **VVER-1000 (NEA/NSC/DOC(2002)10):** E is the mean of the six participants in Appendix C,
  Table C.1 (MCU 1.3197, TVS-M 1.3213, WIMS8A 1.3122, HELIOS 1.3181, MCNP4B 1.3235,
  MULTICELL 1.3164); σe is the sample standard deviation (spread between codes and libraries;
  not a statistical uncertainty). Relative to MCNP4B, the only continuous-energy Monte Carlo
  participant, the difference is 1.31910 − 1.3235 = −440 pcm (+60 pcm relative to the participant
  mean); the MCNP4B library (1990s, based on ENDF/B-VI) differs from ENDF/B-VIII.0 — in
  particular, U-238 resonance and O-16 data have changed. This difference is for information
  only; the acceptance criterion is applied to the mean.
- **SFR MET-1000 (NEA/NSC/R(2015)9):** E is the BOC participant mean of Table 4.3 (20
  calculations, different codes and libraries); σe is the standard deviation between participants
  (780 pcm). This row is NOT part of the benchmark suite (an example; no run with σc ≤ 30 pcm was
  made); it is consistency information only.

## V&V set: AOA parameters

The parameters of each experimental benchmark's area of applicability (AOA, NUREG/CR-6698 §2.5
Table 2.3) are stored in `referans.aoa`. Fissile species, enrichment, H/X and physical form are
extracted **automatically from the spec** by `cekirdek/vv/aoa.py`; EALF (the energy of the
average lethargy of neutrons causing fission) comes from the run's `vv_ealf` tally (300
logarithmic groups, 10⁻⁵ eV – 20 MeV), and the spectrum class from EALF (thermal < 1 eV ≤
intermediate < 100 keV ≤ fast); reflector and physical form are entered from the benchmark
definition (`aoa_girdi`). The EALF of the four existing benchmarks was taken from a short
20000 × 60 batch run (the k measurement did not change). Enrichment: for a single fissile species,
the mass percentage of the fissile isotope (U-235, U-233 or Pu-239 + Pu-241) in its own element;
for "mixed" (`karisik`), fissile / heavy metal. H/X: H atoms / fissile atoms, only if H is inside
the fissile material; if H is only in a separate material (lattice, water reflector) it is **not
given**, because a volume would be needed.

In `referans.aoa` the form, reflector and spectrum values are stored as Turkish identifiers
(e.g. `cozelti`, `dogal_u`, `termal`); the table shows their English meaning.

| Example | Series | Fissile | Enrichment [%] | Form | Reflector | H/X | EALF [eV] | Spectrum |
|---|---|---|---|---|---|---|---|---|
| godiva_kriter.json | HEU-MET-FAST-001 | U-235 | 93.71 | metal | none | 0 | 8.28e+05 | fast |
| kriter_jezebel.json | PU-MET-FAST-001 | Pu | 95.48 | metal | none | 0 | 1.27e+06 | fast |
| kriter_flattop25.json | HEU-MET-FAST-028 | U-235 | 93.24 | metal | natural U | 0 | 7.5e+05 | fast |
| kriter_lct008.json | LEU-COMP-THERM-008 | U-235 | 2.46 | oxide | water | — (heterogeneous) | 0.282 | thermal |
| vv/kriter_hst009a.json | HEU-SOL-THERM-009 | U-235 | 93.18 | solution | water | 35.8 | 0.522 | thermal |
| vv/kriter_hst013.json | HEU-SOL-THERM-013 | U-235 | 93.18 | solution | none | 1.37e+03 | 0.0327 | thermal |
| vv/kriter_hst032.json | HEU-SOL-THERM-032 | U-235 | 93.21 | solution | none | 1.84e+03 | 0.0313 | thermal |
| vv/kriter_imf003.json | IEU-MET-FAST-003 | U-235 | 36.53 | metal | none | 0 | 6.18e+05 | fast |
| vv/kriter_imf004.json | IEU-MET-FAST-004 | U-235 | 36.54 | metal | graphite | 0 | 5.79e+05 | fast |
| vv/kriter_lct006_01.json | LEU-COMP-THERM-006 | U-235 | 2.60 | oxide | water | 165 | 0.24 | thermal |
| vv/kriter_lct006_02.json | LEU-COMP-THERM-006 | U-235 | 2.60 | oxide | water | 165 | 0.246 | thermal |
| vv/kriter_lct006_03.json | LEU-COMP-THERM-006 | U-235 | 2.60 | oxide | water | 165 | 0.253 | thermal |
| vv/kriter_lct006_04.json | LEU-COMP-THERM-006 | U-235 | 2.60 | oxide | water | 201 | 0.185 | thermal |
| vv/kriter_lct006_05.json | LEU-COMP-THERM-006 | U-235 | 2.60 | oxide | water | 201 | 0.191 | thermal |
| vv/kriter_lst002a.json | LEU-SOL-THERM-002 | U-235 | 4.89 | solution | water | 1.1e+03 | 0.0385 | thermal |
| vv/kriter_lst002b.json | LEU-SOL-THERM-002 | U-235 | 4.89 | solution | none | 1e+03 | 0.0404 | thermal |
| vv/kriter_lst003c.json | LEU-SOL-THERM-003 | U-235 | 10.07 | solution | none | 897 | 0.039 | thermal |
| vv/kriter_mmf001.json | MIX-MET-FAST-001 | mixed | 94.05 | metal | HEU | 0 | 1.12e+06 | fast |
| vv/kriter_pci001.json | PU-COMP-INTER-001 | Pu | 94.62 | compound | infinite | 0.392 | 294 | intermediate |
| vv/kriter_pmf002.json | PU-MET-FAST-002 | Pu | 79.43 | metal | none | 0 | 1.28e+06 | fast |
| vv/kriter_pmf006.json | PU-MET-FAST-006 | Pu | 95.15 | metal | natural U | 0 | 1.07e+06 | fast |
| vv/kriter_pmf008.json | PU-MET-FAST-008 | Pu | 94.85 | metal | thorium | 0 | 1.08e+06 | fast |
| vv/kriter_pmf011.json | PU-MET-FAST-011 | Pu | 94.76 | metal | water | — (heterogeneous) | 8.26e+04 | intermediate |
| vv/kriter_pmf018.json | PU-MET-FAST-018 | Pu | 95.08 | metal | beryllium | 0 | 9.24e+05 | fast |
| vv/kriter_pst001.json | PU-SOL-THERM-001 | Pu | 95.32 | solution | water | 370 | 0.0867 | thermal |
| vv/kriter_pst021.json | PU-SOL-THERM-021 | Pu | 95.32 | solution | none | 131 | 0.305 | thermal |
| vv/kriter_umf001.json | U233-MET-FAST-001 | U-233 | 98.11 | metal | none | 0 | 1.11e+06 | fast |
| vv/kriter_umf005.json | U233-MET-FAST-005 | U-233 | 98.20 | metal | beryllium | 0 | 7.71e+05 | fast |
| vv/kriter_umf006.json | U233-MET-FAST-006 | U-233 | 98.13 | metal | natural U | 0 | 9.62e+05 | fast |
| vv/kriter_usi001.json | U233-SOL-INTER-001 | U-233 | 98.56 | solution | beryllium | 24.6 | 7 | intermediate |
| vv/kriter_ust008.json | U233-SOL-THERM-008 | U-233 | 97.67 | solution | none | 1.98e+03 | 0.0369 | thermal |

Notes: PU-MET-FAST-011 (water-reflected Pu sphere) is in the "fast" class in ICSBEP, but thermal
neutrons returning from the reflector lower its EALF to 83 keV; because the tool applies the
EALF limit of 6698, it reports "intermediate". PU-COMP-INTER-001 is an infinite medium (a sphere
with a reflective boundary; the model check gate gives the warning "reflective boundary on a bare
assembly" — expected for this case).

## Method validation (NUREG/CR-6698): bias, USL, AOA

This section is the output of Wave S-3. Code: `cekirdek/vv/istatistik.py` (method),
`cekirdek/vv/kume.py` (set → `VVOzeti`), `cekirdek/vv/aoa.py` (AOA parameters). The criterion
and formulas are from **NUREG/CR-6698** (NRC, January 2001; open document, ML050250061); the
summary and the equation numbers are in `docs/STANDARTLAR.en.md` §4. The method is tested by
reproducing the 25-case example of the document's §3 exactly (`testler/test_vv.py` VV1:
k̄ = 0.99983, S_p = 0.010564, K_L = 0.97562, band K_L(971.7) = 0.9515, β = 72.26 %,
Shapiro–Wilk W = 0.9201).

**Procedure.** (1) k_norm = k_calc / k_exp and σ = √(σc² + σe²) (eqs. 9, 3); (2) weighted
k̄, s², σ̄², S_p (eqs. 4–7); (3) bias = k̄ − 1, set to 0 in the USL if positive (eq. 8);
(4) normality: Shapiro–Wilk (§2.4.3); if p ≤ 0.05 the non-parametric method is mandatory
(eqs. 31–34, Table 2.2); (5) trend: weighted linear fit against enrichment, H/X and log₁₀(EALF)
(eqs. 10–15), slope significance by a t-test (the t-test is not in 6698; SCALE/VADER
practice); (6) if there is a significant trend, a tolerance band (eqs. 23–30), otherwise a
one-sided tolerance limit (eqs. 20–22, U(n) from the non-central t distribution; U(50) for
n > 50); (7) USL = K_L − ΔSM − ΔAOA (eqs. 22/35), ΔSM ≥ 0.02 (§2.4.5); (8) acceptance
k + 2σ < USL (eq. 36; `denetle()` K6).

**Additional rule of the tool (no false confidence):** if the set has fewer than 10 cases
(6698 §2.2: requires technical justification), the statistics are reported but **no USL is
given** ("could not be calculated"); the user organisation can write its justification and lower
`n_usl_asgari` — K10 still warns. In the non-parametric method, if β ≤ 40 %, no USL is given
either (Table 2.2).

**ΔSM.** Default 0.05 (the value reported as accepted without further justification in
NUREG-1718 / NUREG-1520 Ch. 5 App. B — **NOT VERIFIED**, see STANDARTLAR.en.md §2.2); 0.02 is
the absolute lower limit. The choice of ΔSM and its justification belong to the user
organisation.

### Results (01.10.2026; ΔSM = 0.05, ΔAOA = 0)

σ_bias is given as the pooled standard deviation S_p (eq. 7; eq. 28 in the band method).
K_L is the tolerance limit / non-parametric lower limit; USL = K_L − ΔSM − ΔAOA. In the Trend
column, "none" means that the slope is not significant.

| Subset (AOA) | n | bias k̄ − 1 | S_p | Normality (Shapiro–Wilk) | Trend | Method | K_L | USL |
|---|---|---|---|---|---|---|---|---|
| Whole set | 26 | −0.00051 | 0.00235 | W = 0.794, p = 0.000 → not normal | EALF: none (t = 0.63), enrichment: none (t = 0.60) | non-parametric (β = 73.6 %) | 0.9535 | 0.9035 |
| Fast spectrum (EALF ≥ 100 keV) | 13 | −0.00050 | 0.00191 | W = 0.927, p = 0.311 → normal | EALF: none (t = 1.23), enrichment: none (t = 1.60) | tolerance limit | 0.9944 | 0.9444 |
| Thermal spectrum (EALF < 1 eV) | 10 | −0.00089 | 0.00355 | W = 0.984, p = 0.984 → normal | EALF: none (t = 1.89), enrichment: none (t = 0.52) | tolerance limit | 0.9888 | 0.9388 |
| Intermediate spectrum | 3 | −0.00005 | 0.00334 | W = 0.941, p = 0.530 → normal | EALF: none (t = 1.15), enrichment: none (t = 3.75) | tolerance limit | 0.9744 | **not calculated** |
| Solutions (thermal + intermediate) | 10 | −0.00203 | 0.00532 | W = 0.841, p = 0.045 → not normal | EALF: none (t = 0.40), H/X: none (t = 0.31), enrichment: none (t = 0.24) | non-parametric (β = 40.1 %) | 0.9235 | 0.8735 |
| U-235 (all forms) | 11 | −0.00006 | 0.00289 | W = 0.964, p = 0.819 → normal | EALF: none (t = 1.59), enrichment: none (t = 0.08) | tolerance limit | 0.9918 | 0.9418 |
| Pu (all forms) | 9 | −0.00086 | 0.00189 | W = 0.831, p = 0.046 → not normal | EALF: none (t = 1.37), enrichment: none (t = 1.98) | non-parametric (β = 37.0 %) | — | **not calculated** |
| U-233 | 5 | −0.00032 | 0.00268 | W = 0.689, p = 0.007 → not normal | EALF: none (t = 0.56), H/X: none (t = 0.15), enrichment: none (t = 0.52) | non-parametric (β = 22.6 %) | — | **not calculated** |
| LEU (U-235, enrichment ≤ 20 %) | 4 | −0.00056 | 0.00350 | W = 0.980, p = 0.904 → normal | EALF: none (t = 0.64), enrichment: none (t = 0.21) | tolerance limit | 0.9814 | **not calculated** |

Common notes: the bias used is min(k̄ − 1, 0) — the bias is negative in all subsets, so crediting
a positive bias does not arise (eq. 8). The H/X trend is computed only if H/X is defined for all
cases (undefined for LCT-008 and PMF-011 → no H/X trend in those subsets). No subset showed a
significant trend (t < t₀.₉₇₅,ₙ₋₂), so the tolerance band method was not selected. There are two
cases from the same experimental series (LEU-SOL-THERM-002 cases 1 and 2): K14 gives the
"not independent" note.

### Which subset the tool uses (panel, report annex, CLI)

The table above is a **descriptive** breakdown of the set. The compliance check (K6) calculates
the USL for an application **only** from cases that share the application's fissile species,
physical form and neutron spectrum; for U-235 the enrichment class must also match (ICSBEP
naming: LEU ≤ 10 %, IEU 10–60 %, HEU ≥ 60 %) — `cekirdek/vv/kume.py` `aoa_filtresi`, 6698
§2.5 and Table 2.3. If the matching subset has fewer than 10 cases, **no USL is given** and K6
says "no USL for this application (outside the AOA)". When K6 passes, the message states the
subset, n and the method. Reflector and H/X do not narrow the subset: K6-AOA and K12 check them
separately; if H/X cannot be derived for a heterogeneous lattice, K12 warns (H/X not compared).

With this criterion the largest subset in the repository set (26 cases) has 5 cases:

| Subset | n |
|---|---|
| Pu, metal, fast | 5 |
| U-235, solution, thermal, HEU | 3 |
| U-233, metal, fast | 3 |
| U-235, metal, fast, HEU (Godiva, Flattop-25) | 2 |
| U-235, metal, fast, IEU (IMF-003, -004) | 2 |
| U-235, solution, thermal, LEU | 2 |
| Pu, solution, thermal | 2 |
| U-235, oxide, thermal, LEU (LCT-008) | 1 |
| 6 other subsets | one case each |

Result: **at present the repository set gives no USL for any application.** This is not a bug
but the honest result: for an LWR/LEU lattice (pwr_17x17 etc.) the matching subset is LCT-008
alone (n = 1); for a Godiva-like HEU fast metal n = 2. The previous version selected the subset
by spectrum only and gave pwr_17x17 a USL of 0.93877 from 9 solutions + 1 lattice (contrary to
6698 Table 2.3; fixed, regression test `testler/test_vv_altkume.py`). A USL needs at least 10
independent experiments added to the relevant subset (STANDARTLAR.en.md §5).

### Why the mixed subsets of the table are not used for a USL

- The **fast spectrum (0.9444, n = 13)**, **thermal spectrum (0.9388, n = 10)** and **U-235
  (all forms, 0.9418, n = 11)** rows are mixed in fissile species and/or form; 6698 Table 2.3
  asks for these to be the same. These rows are for information only; the tool does not give
  them to any application as a USL.
- **LWR / LEU lattice applications** (the most frequent at universities): the LEU oxide lattice
  subset has 1 case (LCT-008) → **no USL**. Independent LEU-COMP-THERM series with open models
  (LCT-001, -002, -039 …) are not in mit-crpg; they would have to be remodelled from the ICSBEP
  handbook (STANDARTLAR.en.md §5).
- **AOAs with a single fissile species:** Pu (n = 9, not normal, β = 37.0 %) and U-233
  (n = 5, β = 22.6 %) → **USL could not be calculated** (Table 2.2: additional data required).
- **Intermediate spectrum** (n = 3) → **USL could not be calculated**.
- MOX, oxide powders, wet powders/compounds, heavy water, concrete/steel/lead reflectors,
  poisoned (B, Gd, Cd) systems, high Pu-240 (> 20 %) and enrichment/H/X/EALF values outside the
  AOA range — not represented in the set; K6-AOA and K12 warn.
- The whole-set USL (0.9035, non-parametric) mixes different AOAs; 6698 requires the USL to be
  calculated separately for each AOA — this row is for information only.
- The PU-COMP-INTER-001 (PCI-001) model has no S(α,β) thermal scattering data for H (mit-crpg
  model; the H in the compound is transported as a free gas). The effect is expected to be small
  in an intermediate spectrum but was not measured; the case appears only in the descriptive
  table.

### Limitations

- The criterion and formulas are from NUREG/CR-6698; this is an NRC **guide** (not binding).
  The ANS-8.24 text was not seen (STANDARTLAR.en.md §2.2). The source of the ΔSM = 0.05 default is
  **NOT VERIFIED**; 0.02 is the absolute lower limit. The choice of margin belongs to the user
  organisation.
- Correlation between experiments is not treated (6698 assumes independence; an open topic in
  UACSA).
- All cases are ICSBEP **simplified** models (most of them 1D spherical); the modelling bias is
  taken to be inside E ± σ (the ICSBEP evaluation). E ± σ were taken from mit-crpg
  `uncertainties.csv`; they were **not compared** with the current ICSBEP edition
  (STANDARTLAR.en.md §5 warning).
- Only one code + one library (OpenMC 0.16.0, ENDF/B-VIII.0, 294 K) is validated; with another
  library or version the set must be rerun (`araclar/vv_kriter_uret.py`).
- For n > 50, 6698 recommends no normality test; the tool still uses Shapiro–Wilk and notes it.
- The trend-significance t-test is not defined in 6698 (SCALE/VADER practice).
- This tool does not issue certificates (STANDARTLAR.en.md §1); the USL does not replace the user
  organisation's own validation report.

## Library bias explanations

At present no benchmark exceeds the 3σ criterion. Two deviations inside the criterion that
nevertheless stand out (their causes were not investigated in this work): PU-MET-FAST-008 (Thor)
C − E = −164 pcm, 2.62σ because σe is only 60 pcm; U233-SOL-INTER-001 C − E = −1822 pcm, 2.19σ
with σe = 830 pcm. Both cases enter the set statistics with their weights; U233-SOL-INTER-001 is
the outlier that makes the normality test of the whole set fail. If a benchmark that exceeds the
criterion is added, its explanation is written under this heading with a heading
"### <example file>" (in `docs/VV.md`), and that heading is added to the `KUTUPHANE_YANLILIGI`
dictionary in `testler/test_benchmark.py`.

## Reproduction

- Quick check (no Monte Carlo): `python -m pytest testler/test_benchmark.py -m hizli`
- Rerun with reduced statistics (each benchmark ≤ ~2 min, 8 threads):
  `python -m pytest testler/test_benchmark.py -m yavas`
- Reference runs of the table: open the example, set particles/batches/inactive to the values in
  the table, run with `OMP_NUM_THREADS=8`.

- Regenerating the V&V set (requires a clone of mit-crpg/benchmarks; ~2 hours, 12 threads):
  `OMP_NUM_THREADS=12 python araclar/vv_kriter_uret.py <benchmarks directory>`;
  AOA supplement for the four existing benchmarks: `... --aoa-mevcut`.
- Bias/USL summary: `python -c "from cekirdek.vv import kume; print(kume.ozet(filtre={'tayf': 'termal'}))"`;
  in the checker: `denetle(spec, kosu_dizini, ("B",), vv=kume.ozet(...), uygulama=kume.uygulama(spec, kosu_dizini))`.

## References

- NUREG/CR-6698: J.C. Dean, R.W. Tayloe Jr., Guide for Validation of Nuclear Criticality
  Safety Calculational Methodology, NRC, January 2001 (ML050250061) — bias, USL, AOA method.
- mit-crpg/benchmarks (MIT licence): https://github.com/mit-crpg/benchmarks — V&V set models and
  `icsbep/icsbep/uncertainties.csv` E ± σ values.

- ICSBEP: International Handbook of Evaluated Criticality Safety Benchmark
  Experiments, NEA/NSC/DOC(95)03 (HEU-MET-FAST-001, HEU-MET-FAST-028,
  PU-MET-FAST-001, LEU-COMP-THERM-008). Model inputs:
  https://github.com/mit-crpg/benchmarks
- NEA/NSC/DOC(2002)10: A VVER-1000 LEU and MOX Assembly Computational Benchmark,
  Specification and Results.
- NEA/NSC/R(2015)9: Benchmark for Neutronic Analysis of Sodium-cooled Fast
  Reactor Cores with Various Fuel Types and Core Sizes.
