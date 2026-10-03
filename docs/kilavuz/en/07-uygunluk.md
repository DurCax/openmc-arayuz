<a id="uygunluk-denetimi"></a>
# 7. Conformity check and V&V

The model check (the findings panel) looks **before** a run at whether the model can be built and
is consistent. The **conformity check** runs **after** a run: it tells you where the run stands
with respect to Monte Carlo good practice and the evidence standards would ask for. The same check
appears in three places:

- the **Conformity** card on the **Run** page (when a run finishes or a saved run is loaded),
- the **checklist** annex of the report (File → Create report..., `openmc-arayuz-kosu rapor`),
- the command line: `openmc-arayuz-kosu uygunluk <run_dir>` (see [terminal](08-terminal.md#terminal)).

The rules are explained one by one, with causes and fixes, in the
[troubleshooting](09-sorun-giderme.md#uygunluk-kurallari) chapter; the source table is in
`docs/STANDARTLAR.md` §3 ([STANDARTLAR.md](../../STANDARTLAR.md)).

## 7.1 Reading the conformity card

At the top of the card there is a **Profiles:** row (A · Monte Carlo good practice, B · Criticality
safety, C · Reactor core design, D · Reporting). Below it are a badge and a summary line
("Profiles A, D · 5 passed · 1 not met · 0 not applicable · 2 notes"), and below that the list of
findings. Problems always come first (error > warning > info, then notes, rules that could not be
evaluated, and passed rules).

Each row has the form `K1 · not met — <finding>`; under a row that is not met there is a
`Recommendation: ...` line. The tooltip of a row shows the **source** (citation), the **label** and
the **profile** of the rule. Selecting a row and pressing **Go to finding** (or double-clicking it)
opens the page where the fix is made: K1 and K2 → Run settings (inactive batches, particles),
K3 → Geometry (a lost particle is a geometry error), K4-sicaklik → Materials.

**Statuses**

| In the panel | Status | Meaning |
|---|---|---|
| passed | met | The rule was evaluated and the condition holds. Passed rules stay in the list too, so that the report annex is a complete checklist. |
| not met | not met | The condition does not hold. Its level can be **error**, **warning** or **info**. |
| not applicable | not applicable | The rule could not be evaluated: a required input is missing (statepoint unreadable, no V&V set, no user-defined limit entered...). This is not a "pass". |
| note | info | Not an evaluation but an information note (e.g. a positive MTC alone is not an error; a note is added). |

The **badge** shows the most severe status: "N errors", "N warnings", "N notes"; if no rule could be
evaluated, "Not evaluated: N rules"; if some rules passed and some could not be evaluated,
"N checks passed · N rules not evaluated". The green **"No issues"** appears only when at least one
rule passed and no rule is left unevaluated: you do not see a green badge without a statepoint.

**Labels** (the kind of source; `docs/STANDARTLAR.md` §6 items 16-17)

| Label | Meaning | Example |
|---|---|---|
| good practice (not a clause of a standard) | Published good practice; it is not presented as a clause of a standard | K1-K3 (source convergence, statistical adequacy, lost particles), K14 |
| standard / guide | Based on an explicit clause of a standard or guide | K4, K5, K6-K13, K7, K16 |
| project criterion (not from a standard) | The project's own criterion | significance of a coefficient sign \|slope\| > 2σ; the V&V acceptance criterion |
| user / facility limit | The threshold comes from the user or the facility; **there is no default** | K7-SDM (shutdown margin), K7-F (F_ΔH / F_q) |

Two texts are always shown at the bottom of the card: when profile B is selected and there is no
V&V summary, the note **"USL could not be calculated: there is no validation (V&V) set. The k value of
this run was not compared with an upper subcritical limit; this result is not evidence of
criticality safety."**, and the [honest frame](#ne-kanitlar) text.

If the check cannot be done (e.g. `uygunluk_girdisi.json` in the run directory is corrupt), the list
shows a single red row and a "Could not be checked" badge; details are in the log file. If a rule
itself fails while running, the check does not stop: that rule is listed as an **error** finding
"Rule could not be evaluated" (it is not skipped silently).

<a id="profiller"></a>
## 7.2 Profiles, thresholds and user inputs

A **profile** is a set of rules that make sense together, with their sourced thresholds
(`cekirdek/uygunluk_denetimi/profiller.py`):

| Profile | For | Rules | Default thresholds (with source) |
|---|---|---|---|
| **A** Monte Carlo good practice | Every run | K1, K2, K3 | at least 1000 particles per batch (Brown 2009 §III.C), 5000 for a long production run (§V); z = 2 for batch correlation (Bartlett approximation); lost particles 0; **no** σ target and **no** lower limit on active batches (no standard gives a number → user) |
| **B** Criticality safety | Optional | K6, K6-AOA, K8-K14 | acceptance k + 2σ < USL (NUREG/CR-6698 eq. 36); ΔSM = 0.05 (source **NOT VERIFIED**), lower limit of ΔSM 0.02 (§2.4.5); at least 10 cases (§2.2); non-parametric confidence > 40 % (Table 2.2); extrapolation ≤ 10 % (§1.2, §5) |
| **C** Reactor core design | Power or research reactor core | K7, K7-SDM, K7-F, K16 | **no** limits for F_ΔH, F_q and the shutdown margin (NUREG-0800 §4.3 leaves them to the facility); sign significance 2σ (project criterion); reactor type "guc" (power; for a research reactor the SSR-3 source) |
| **D** Reporting | Every report | K4, K5 | uncertainty with at most 2 significant digits (GUM §7.2.6) |

**Selecting profiles.** The check boxes at the top of the card change the selection of the project;
it is written to the `calistirma.uygunluk_profilleri` field of the model. This field does not enter
the physics: changing the selection does not make a run result outdated. Without the field the
default is **A + D** and nothing is written to the file. On the command line `--profil A,B,C,D` is
used if given; otherwise the selection in `spec.json` of the run directory, and if that is missing
too, A,D.

**No threshold without a source.** Every threshold carries its citation together with its value. If
a standard gives no numeric value, the default is empty and the rule says "could not be compared" /
"not applicable"; the tool does not invent a limit. The profile file format for changing thresholds:

```json
{"C": {"F_dH_siniri": {"deger": 1.55, "kaynak": "Tesis TS 3.2.1"}},
 "A": {"parcacik_uretim": 10000}}
```

Without a source the threshold gets the label "user input, no source given"; an unknown threshold
name is rejected as a typo. In this version the profile file is read only through the Python API
(`profiller.dosyadan_uyarla(yol)`); the user interface and the command line have no option for it
yet.

**Run-specific inputs: `uygunluk_girdisi.json`.** This optional file, placed in the run directory
(next to the statepoint), gives information that cannot be derived from the run itself (the values
below only show the format; the Doppler slope is the `pwr_17x17` measurement in the README, the
shutdown margin is a made-up example):

```json
{"kor": {"katsayilar": {"yakit_sicaklik": {"egim": -1.98, "egim_sapma": 0.17, "birim": "pcm/K"}},
         "kapatma_marji": {"deger_pcm": 1800, "sapma_pcm": 90, "en_degerli_cubuk_sikisik": true},
         "dogrulama": ["ICSBEP LEU-COMP-THERM-008"]},
 "uygulama": {"zenginlik": 4.5, "tayf": "termal"}}
```

- `kor`: inputs of profile C: reactivity coefficients (the sweep result of the Analysis tab; `guc`,
  `yakit_sicaklik`, `sogutucu_sicaklik`, `void_orani`), the shutdown margin (Δρ × 10⁵, with the most
  reactive rod stuck out), F_ΔH / F_q (read from the statepoint if not given) and the benchmarks the
  core method was validated against (K16). The Analysis tab does not write this file itself; you
  enter the values.
- `uygulama`: the area of applicability (AOA) parameters of profile B (`bolunebilir`, `zenginlik`,
  `h_x`, `fiziksel_bicim`, `ealf`, `tayf`). Without them, whatever can be derived is taken from the
  model and the run.

<a id="ne-kanitlar"></a>
## 7.3 What it proves and what it does not

The honest frame, written **verbatim** on the card and in the report annex:

> This program does not certify against any standard and cannot approve an analysis as
> "conforming to a standard". What it does is to produce the evidence that standards and good
> practice would ask for, for a run or a model, and to make the gaps visible. Use in facility
> licensing or safety analysis additionally requires the user organization's own quality assurance
> program and independent review. No threshold is set without a source; thresholds can be adjusted
> in the profile.

**Evidence the check produces**
- Source convergence indicator (K1), statistical adequacy and batch correlation (K2), number of lost
  particles (K3).
- Data traceability (K4): library name and version, temperatures, S(α,β), data hashes, OpenMC
  version, operating system and hardware summary in the report. The `kapsul.json` in every run
  directory keeps the same evidence in a reproducible form.
- Uncertainty and unit statement (K5): the label "1σ, standard uncertainty" next to k, at most two
  significant digits, pcm with its definition written out.
- With a V&V summary, the comparison k + 2σ < USL and the statistical conditions of the validation
  set (profile B); in core design, sign consistency of coefficients and comparison with a user-defined
  limit (profile C).
- The C/E table of the benchmark package ([V&V](#vv)).

**What the check does NOT prove**
- **It is not a certification.** No finding means "conforming to a standard"; the report annex is a
  checklist, not an approval.
- **It does not replace an organization's quality assurance.** ASME NQA-1 (including Subpart 2.7) is
  the quality assurance program of an **organization**; a tool cannot be "NQA-1 compliant", and this
  tool is not developed under an NQA-1 program. In the sense of ANSI/ANS-10.4 the tool is
  **non**-safety-related scientific software (research, education); with respect to the IEEE 1012
  integrity level the developer places it at the lowest level (see `docs/YAZILIM_KALITE.md`,
  [YAZILIM_KALITE.md](../../YAZILIM_KALITE.md)).
- **It does not prove that the model is correct.** That the geometry, materials and operating
  conditions represent the real system is the user's responsibility. As NUREG/CR-6698 stresses,
  validation depends on the hardware and on the competence of the person building the model as much
  as on the code and the library.
- **"Passed" is not absolute.** K1 passing does not show that the source converged in every
  direction (entropy is a global scalar; see [source convergence](06-sonuclar.md#kaynak-yakinsamasi));
  K2 passing does not make local tally σ values real.
- **K7 is not a design judgement.** It only says whether the sign of a coefficient is "consistent" with
  or "contradicts" the expectation; it does not say that GDC 11 is met. A positive MTC alone is not an
  error (a note is added and a transient analysis is pointed to).
- **It is not evidence of criticality safety**: without a V&V summary profile B says "USL could not be
  calculated". Even with a V&V summary the USL is valid only within the area of applicability of the
  set: the set of this version gives a USL only to **LWR / LEU oxide lattice** applications (n = 24,
  two experimental series; a teaching figure, not licensing) ([V&V](#vv)).
- **There is no independent V&V.** The code, the tests and the reviews come from the same development
  process (`docs/YAZILIM_KALITE.md` §4).

<a id="vv"></a>
## 7.4 V&V: benchmark set, C/E, bias, USL and AOA

The benchmark package of the tool and the measured results are in `docs/VV.md`
([VV.md](../../VV.md)); the numbers there are identical to the `referans.olcum` fields of the example
files, and a test checks this. Environment: OpenMC 0.16.0, ENDF/B-VIII.0 (HDF5, 294 K). Step-by-step
lesson: [benchmark and C/E](05-dersler.md#ders-benchmark).

**The set.** 49 experimental benchmarks (ICSBEP; with v3 Y11): the first four are `ornekler/godiva_kriter.json`,
`ornekler/kriter_jezebel.json`, `ornekler/kriter_flattop25.json`, `ornekler/kriter_lct008.json`;
22 are under `ornekler/vv/`, imported as concentric spherical shells from the OpenMC models of
mit-crpg/benchmarks (MIT license); 24 are LEU oxide lattices (v3 Y11): LEU-COMP-THERM-006 (TCA,
18 cases, models built from the public primary report JAERI 1254) and LEU-COMP-THERM-008 (6 cases,
mit-crpg). LCT-008 case 1 was regenerated with h_x and replaces the v2 file in the V&V set. There are also two code-to-code benchmarks (VVER-1000 LEU assembly,
SFR MET-1000). **Experimental and code-to-code benchmarks are kept apart:** in an experimental
benchmark E is a measured critical assembly; in a code-to-code benchmark E is the average of other
codes' results, not the "true" value.

**Reading the C/E table**

| Column | Meaning |
|---|---|
| E ± σe | experimental value of the benchmark and its uncertainty |
| C ± σc | calculated value of this tool (1σ) |
| C − E [pcm] | **Δk × 10⁵** (difference in k; not a reactivity difference Δρ) |
| diff/σ | \|C − E\| / √(σc² + σe²) |
| C/E | calculated / experimental |

The **acceptance criterion** is \|C − E\| ≤ 3·√(σc² + σe²) and σc ≤ 30 pcm. It is the **project's own
criterion**, it does not come from a standard. No benchmark exceeds it at present; the largest
deviations are PU-MET-FAST-008 (2.62σ) and U233-SOL-INTER-001 (2.19σ, −1822 pcm; the outlier that
makes the normality test of the whole set fail). Both were studied in v3 with model variants: the
import, the 1D simplification, S(α,β) and temperature do not explain the deviations; the probable cause
is nuclear data (consistent with the published U-233 epithermal trend) — **not verified** with another
library (`docs/VV.md`, "Deviation study").

**Bias and USL: the NUREG/CR-6698 procedure.** (Code `cekirdek/vv/`, formulas `docs/STANDARTLAR.md` §4.)
1. Normalization k_norm = k_calc / k_exp and combined uncertainty σ = √(σc² + σe²) (eqs. 9, 3).
2. Weighted mean k̄, variance s², mean uncertainty σ̄², pooled S_p (eqs. 4-7).
3. Bias = k̄ − 1; **a positive bias is not credited** (taken as 0 in the USL, eq. 8; K8).
4. Normality: Shapiro-Wilk; if p ≤ 0.05 the non-parametric method is mandatory (eqs. 31-34).
5. Trend: weighted linear fit against enrichment, H/X and log₁₀(EALF); slope significance with a
   t-test (this test is not in 6698; it is the SCALE/VADER practice).
6. With a significant trend, a tolerance band (eqs. 23-30); otherwise a one-sided tolerance limit
   (eqs. 20-22).
7. USL = K_L − ΔSM − ΔAOA (eqs. 22/35).
8. Acceptance: **k + 2σ < USL** (eq. 36; strict inequality; K6).

**No false confidence.** With fewer than 10 cases in the set (6698 §2.2) the statistics are reported
but **no USL is given** ("could not be calculated"); in the non-parametric method no USL is given
either if the confidence β ≤ 40 % (Table 2.2: more data needed). The default ΔSM is 0.05 (source **NOT
VERIFIED**); **0.02 is the absolute lower limit**, and a smaller ΔSM in the profile gives a K11 error.
The choice of ΔSM and its justification belong to the user organization.

**Measured results (02.10.2026, with the v3 Y11 LEU lattice cases; ΔSM = 0.05, ΔAOA = 0; details in `docs/VV.md`)**

| Subset (AOA) | n | bias k̄ − 1 | Method | USL |
|---|---|---|---|---|
| Whole set | 49 | −0.00018 | non-parametric (β = 91.9 %) | 0.9235 (information only: mixes different AOAs) |
| Fast spectrum (EALF ≥ 100 keV) | 13 | −0.00050 | tolerance limit | 0.9444 (information only) |
| Thermal spectrum (EALF < 1 eV) | 33 | +0.00010 | non-parametric (β = 81.6 %) | 0.9297 (information only) |
| U-235 (all forms) | 34 | +0.00021 | non-parametric (β = 82.5 %) | 0.9297 (illustration only) |
| Solutions (thermal + intermediate) | 10 | −0.00203 | non-parametric (β = 40.1 %) | 0.8735 |
| **U-235, oxide, thermal, LEU (LCT-006 + LCT-008)** | **24** | +0.00029 | non-parametric (β = 70.8 %) | **0.9275** |
| Intermediate spectrum | 3 | −0.00005 | tolerance limit | **could not be calculated** |
| Pu (all forms) | 9 | −0.00086 | non-parametric (β = 37.0 %) | **could not be calculated** |
| U-233 | 5 | −0.00032 | non-parametric (β = 22.6 %) | **could not be calculated** |

**Which subset does the tool use?** The table above is descriptive. K6 calculates the USL of an
application **only** from cases that share the application's fissile species, physical form and
neutron spectrum; for U-235 the enrichment class must also match (ICSBEP: LEU ≤ 10 %, IEU 10-60 %,
HEU ≥ 60 %; NUREG/CR-6698 §2.5, Table 2.3). If the matching subset has fewer than 10 cases, no USL
is given. With this criterion the largest subset in the repository set is **U-235, oxide, thermal, LEU
(n = 24)**; LWR/LEU lattice applications (e.g. pwr_17x17) get **USL = 0.9275** (non-parametric; the
set is not normal because the two series differ by ~130 pcm — no U-234 in the TCA model,
`docs/VV.md`). The 24 cases come from only two experimental series (K14 note); 6698's independence
assumption is not fully met. For other AOAs the largest subset has 5 cases (Pu, metal, fast) → no
USL. The fast
spectrum, thermal spectrum and U-235 rows of the table are mixed in fissile species or form; they are
for information only.

**For which applications is there NO USL?**
- Single-species AOAs (Pu, U-233), the intermediate spectrum and every AOA with fewer than 10 matching
  cases in the set.
- MOX, oxide powders, heavy water, concrete/steel/lead reflectors, poisoned (B, Gd, Cd) systems, high
  Pu-240 (> 20 %) and enrichment/H/X/EALF values outside the AOA range are not represented in the set;
  K6-AOA and K12 warn. If H/X cannot be derived for a heterogeneous lattice, K12 warns about that too.

**Limitations.** The criterion and the formulas are from NUREG/CR-6698 (an NRC **guide**, not
binding); correlation between experiments is not treated (for two cases of the same series K14 adds
the note "not independent"); the cases are the simplified (mostly 1D spherical) ICSBEP models; E ± σ
was not compared with the current ICSBEP edition; only one code + one library has been validated (with
another library or version the set has to be run again).

**Using it in the tool.** When profile B is selected, the Conformity card, the report annex and the
`uygunluk` command use the V&V summary automatically (`kume.uygulama_ozeti`): the application's AOA
is derived from the model and the matching subset is selected; if there is a USL, the K6 message
states the subset, n and the method, otherwise "no USL for this application" and the reason are
shown. The spectrum needs the EALF tally (`vv_ealf`) in the run; without it the card offers to add
it. With the Python API:

```bash
python -c "from cekirdek.vv import kume; import json; print(kume.uygulama_ozeti(json.load(open('ornekler/pwr_17x17.json')), uygulama={'tayf': 'termal'})[0].usl_neden)"
```

The AOA parameters of the application (`kume.uygulama`) are derived from the model and from the EALF
tally of the run; a parameter that cannot be derived is not in the dictionary.
