# openmc-arayuz — an interface for building and running OpenMC reactor models

Türkçe: [README.md](README.md)

`openmc-arayuz` is a desktop application (PySide6) in which every model parameter, from
materials to the full core, is set up in one interface; the geometry is plotted before the
calculation is run; and the calculation is started and its results are read in the same place.
A GUI-free core layer (`cekirdek/`) does the same work from the terminal.

> **Status.** Version `2.0.0`. The interface is available in English and Turkish (View > Language).
> Interface names in this document follow the binding glossary [docs/SOZLUK.md](docs/SOZLUK.md).

## What it is

The interface does not edit OpenMC objects directly. It edits a validated **JSON model
definition** (the *spec*), which is the single source of truth:

```
spec (JSON) ──► builder ──► openmc.Model ──► XML ──► openmc run
     │
     └────────► script generator ──► model.py (standalone, editable by hand)
```

The interface is not a dead end: **File → Export as Python script (Ctrl+E)** turns any model
into a readable OpenMC script that does not depend on `openmc-arayuz`. The conversion is one-way:
a script cannot be read back into a spec. Test suites check that the builder and the exported
script produce the same model (the same materials and settings XML, the same tallies, the same
material at random sample points) and, with the same seed, the same k-eff.

## Who it is for

The program is developed for **universities**: course work, laboratory exercises and research.
Typical uses are a first k∞ calculation for a pin cell, a parametric study of an assembly, a
full-core power map, a depletion study, or a comparison with a criticality benchmark.

It is **not** developed as a safety-related calculation tool. The closest software framework is
ANSI/ANS-10.4 (verification and validation of non-safety-related scientific programs); see
[docs/STANDARTLAR.en.md](docs/STANDARTLAR.en.md) §1.

## Capabilities

### Model building

- **Materials.** A library of 21 materials grouped by role (fuel; cladding and structural;
  coolant and moderator; absorber; gas): UO₂, UN, U-10Mo, MOX, U₃Si₂-Al, Zircaloy-4, SS-316,
  MA956, FeCrAl, SiC, Al-6061, water (density from temperature, with boron), D₂O, LBE, Na, He,
  graphite, Be, B₄C, Gd₂O₃, Ag-In-Cd. Library materials are stored with their parameters, so a
  change of temperature, boron or enrichment recomputes density and composition. Materials can
  also be imported from `materials.xml` / `model.xml`.
- **Components.** Fuel pins (cylindrical, square or hexagonal cross section), guide tubes,
  control rods, fuel plates (MTR) and control drums.
- **Assemblies and cores.** Square and hexagonal assemblies are painted with a component
  palette; square and hexagonal core maps use the same palette. Axial layers (reflectors,
  blankets, plenum, enrichment zones) are set up in a table.
- **Start screen.** One card per model type (fuel pin, square/hexagonal assembly, full core, MTR
  plate element, core with control drums, shielding). No example is loaded at startup: start **from
  scratch** (a truly empty model with a step guide: material → component → assembly → geometry),
  **from template** (a working, simple model of that type) or **from example** (an unsaved copy;
  examples are never overwritten).

### Flexible geometry tree

The seven classic core types (single pin, single plate, single assembly, rectangular lattice core,
hexagonal lattice core, spherical assembly, core with control drums) remain as **templates**.
Each template expands into a **geometry tree** built from five node types — material, component
reference, lattice, container and axial stack — plus placements and transforms. In the
**advanced geometry** view the tree is edited directly. This makes layouts possible that no single
template covers, for example:

- a square core inside a ring of hexagonal reflector blocks;
- a hexagonal core with a ring of control drums;
- a square lattice core inside a cylindrical reflector with drums;
- a quarter core with per-face boundary conditions (two reflective symmetry faces, two vacuum
  faces).

A **control drum can be placed in any geometry** (ring, list or lattice-position placements;
the absorber arc faces the core at rotation 0°). Control rods have their own insertion, and
control groups move several drums or rods together. The model check reports truncated lattice
positions, overlaps and gaps before a run. See
[docs/GEOMETRI_MODELI.en.md](docs/GEOMETRI_MODELI.en.md).

### Run settings and checks

- **Accuracy preset** (Quick test / Normal / Accurate) with the expected k-eff uncertainty;
  expert fields under *Advanced*.
- Eigenvalue and fixed-source calculations; source energy spectrum (Watt, Maxwell,
  monoenergetic, discrete lines, histogram, fusion), angular distribution and particle type.
- **Model check before running.** Missing cross section data, missing S(α,β), inconsistent pin
  radii, undefined lattice letters, invalid boundary conditions, too few inactive batches and
  similar problems are reported as error / warning / info findings. **Plot first, then run:** the
  Run button stays disabled until the geometry preview has been produced and no errors remain.
- **Source convergence.** The Shannon entropy mesh is on by default; after the run the tool
  checks whether the source had settled by the end of the inactive batches.
- **Kinetics parameters** (β_eff, Λ = ℓ/k; per-group β_i and λ_i) by the iterated fission probability method, and a **point kinetics** solver (step/ramp reactivity → P(t), Inhour period, adiabatic feedback) under Analysis.

### Results and analysis

- **Power distribution and power map**, pin by pin, with peaking factors F_ΔH and F_q; a
  conservation check compares the sum of pin powers with an unfiltered tally. Optional
  multi-seed runs give a realistic spread: the tally uncertainty reported from a single
  eigenvalue run ignores the correlation between successive batches and is optimistic (measured
  in the 3D PWR assembly example: about 20 times smaller than the spread between seeds).
- **Parameter sweep** → reactivity coefficients (fuel temperature, moderator temperature with
  density correlation, boron, control group position).
- **Critical search** for boron, control rod insertion, drum rotation or other parameters; the
  uncertainty of the root is reported, and the search does not extrapolate outside the given
  range.

### Depletion

Depletion uses OpenMC's depletion module with an automatically chosen or user-selected depletion
chain (ENDF/B-VIII.0 thermal or fast, CASL simplified), analytic material volumes (checked against
stochastic volume estimates), power density in W/gHM, user-selected **tracked nuclides**, and
detection of **stale results** (a previous result that no longer belongs to the current model is
marked as such).

### Reports, reproducibility and the conformity checklist

- **Report** (HTML or PDF; **File → Create report**, Ctrl+R) of the model and the last run,
  including a reproducibility block.
- **Reproducibility capsule.** Every run writes `kapsul.json` next to `spec.json`: hashes of the
  spec, cross section index and depletion chain, OpenMC version, seed, thread count, platform and
  a summary hash of the conda environment. `openmc-arayuz-kosu yeniden <run directory>` lists
  what has changed in the environment and reruns the same spec in a separate directory.
- **Conformity check** with profiles A (Monte Carlo good practice), B (criticality safety,
  optional), C (reactor core design) and D (reporting). Every rule carries its source (standard,
  guide or good practice); thresholds without a citable source are user inputs. The result is a
  **checklist** with passed / not met / not applicable items, shown in a panel and appended to the
  report.

> **This is not a certificate.** The program does not certify conformity with any standard and
> cannot approve an analysis as "compliant". It produces the evidence that standards and good
> practice ask for and makes gaps visible. Use in facility licensing or safety analysis requires
> the user organisation's own quality assurance programme and independent review. Details:
> [docs/STANDARTLAR.en.md](docs/STANDARTLAR.en.md).

### Verification and validation

- Regression anchor: the pin cell example gives **k∞ = 1.3570 ± 0.0020**.
- **26 ICSBEP criticality experiments** (calculated-to-experimental ratio, C/E) and two
  calculation-to-calculation benchmarks (NEA VVER-1000, OECD/NEA SFR MET-1000); all experiments
  meet the project's acceptance criterion |C − E| ≤ 3·√(σc² + σe²).
- **Bias and upper subcritical limit (USL)** by the NUREG/CR-6698 method, per area of
  applicability (AOA). The compliance check uses only cases with the application's fissile species,
  physical form, spectrum and (U-235) enrichment class; no such subset in the current 26-case set has
  10 cases, so **no USL is given for any application today** (e.g. LWR/LEU lattice: 1 matching case).
  The mixed spectrum-only rows (fast 0.9444, n = 13; thermal 0.9388, n = 10; ΔSM = 0.05) are
  descriptive only.

See [docs/VV.en.md](docs/VV.en.md) for the tables and, importantly, for what these numbers do
**not** cover.

## Quick start

Installation (conda environment, OpenMC 0.16.0, ENDF/B-VIII.0 data, depletion chains) is
described step by step in **[INSTALL.md](INSTALL.md)**. After installation:

```bash
conda activate openmc-env
cd openmc_arayuz
./calistir.sh                          # start screen
./calistir.sh ornekler/pwr_17x17.json  # open a model directly (examples open as a copy)
```

A first check: on the start screen choose **Fuel pin → From template**, then press **F9** (Run).
Within about half a minute the result card should show **k∞ ≈ 1.323 ± 0.001** (UO₂ 3.0 %, hot
operating conditions, *Normal* accuracy preset; measured 1.3227 ± 0.0008).

Keyboard shortcuts: **F1** help and terms, **F5** refresh the model check (including the data
library), **F6** refresh the preview, **F9** run, **Ctrl+E** export as Python script, **Ctrl+R**
report, **Ctrl+K** command palette, **Ctrl+Z** undo.

## Terminal use (no GUI)

```bash
openmc-arayuz-kosu ornekler/pwr_pinhucre.json                    # run and print results
openmc-arayuz-kosu ornekler/pwr_17x17.json --dizin /tmp/run -s 24 # run directory, 24 threads
openmc-arayuz-kosu ornekler/mtr_plaka.json --sadece-dogrula      # model check only
openmc-arayuz-kosu ornekler/pwr_17x17.json --betik model.py      # export a Python script
openmc-arayuz-kosu rapor <run directory> -o report.pdf           # report (PDF or HTML)
openmc-arayuz-kosu uygunluk <run directory> --profil A,D         # conformity check
openmc-arayuz-kosu yeniden <run directory> --kuru                # compare with the capsule
```

Without `pip install -e .` the same commands run as `python3 -m cekirdek.kosucu ...`. Exit codes
of `uygunluk` (for CI or course automation): 0 no error finding, 1 error finding (or the check
could not be made), 2 usage error, 3 with `--siki`: at least one rule could not be evaluated.

## Documentation map

| Document | Language | Content |
|---|---|---|
| [README.en.md](README.en.md) | EN | This overview |
| [README.md](README.md) | TR | Full Turkish README: workflow, measured reference results, physics notes, known pitfalls |
| [INSTALL.md](INSTALL.md) | EN | Installation, nuclear data, tests, troubleshooting |
| [KURULUM.md](KURULUM.md) | TR | Installation (Turkish) |
| [docs/VV.en.md](docs/VV.en.md) · [docs/VV.md](docs/VV.md) | EN · TR | Verification and validation: C/E tables, AOA, bias and USL, limitations |
| [docs/ORNEKLER.en.md](docs/ORNEKLER.en.md) · [docs/ORNEKLER.md](docs/ORNEKLER.md) | EN · TR | The examples, their sources and measured results |
| [docs/GEOMETRI_MODELI.en.md](docs/GEOMETRI_MODELI.en.md) | EN | Geometry tree: user-facing summary |
| [docs/GEOMETRI_MODELI.md](docs/GEOMETRI_MODELI.md) | TR | Geometry tree: full design document |
| [docs/STANDARTLAR.en.md](docs/STANDARTLAR.en.md) · [docs/STANDARTLAR.md](docs/STANDARTLAR.md) | EN · TR | Standards, conformity matrix, NUREG/CR-6698 method summary |
| [docs/SOZLUK.md](docs/SOZLUK.md) | TR → EN | Binding terminology glossary |
| [docs/GEREKSINIMLER.md](docs/GEREKSINIMLER.md) | TR | Requirements (R-… identifiers) |
| [docs/IZLENEBILIRLIK.md](docs/IZLENEBILIRLIK.md) | TR | Requirement → test → result matrix (generated) |
| [docs/YAZILIM_KALITE.md](docs/YAZILIM_KALITE.md) | TR | Software quality evidence and known gaps |

A user guide (`docs/kilavuz/`, Turkish and English) is in preparation.

## ⚠ DRAW FIRST, THEN RUN

The **Run button stays disabled** until the geometry preview has been produced and
validation errors are fixed: this prevents hours of running on a wrong geometry.
Details: [guide §6.4](docs/kilavuz/en/06-sonuclar.md#64-plot-first-then-run).

## Known pitfalls

Measured pitfalls and the story of their fixes (narrow data temperature ranges, water
S(α,β) only 284–800 K, hexagonal orientation letters, duct apothem, source box z range,
silent acceptance in the OpenMC API) are in the user guide:
[guide §6.5](docs/kilavuz/en/06-sonuclar.md#65-known-pitfalls).

## Limitations

The main limitations of the validation are stated in [docs/VV.en.md](docs/VV.en.md); the most
important ones for university users are:

- **No USL for LWR / LEU lattice applications.** The LEU subset of the validation set has four
  cases (one lattice, three solutions), so no USL is given. Independent LEU-COMP-THERM series with
  open models are not available in the model repository used and would have to be modelled from
  the ICSBEP handbook.
- **No USL for single-fissile-species AOAs** (Pu: n = 9; U-233: n = 5) or for the intermediate
  spectrum (n = 3). The fast and thermal USLs above mix fissile species and physical forms and
  are defensible only for applications that this mixture represents.
- Only one code and one library are validated (OpenMC 0.16.0, ENDF/B-VIII.0, 294 K). With another
  library or version the set must be rerun.
- The benchmark E ± σ values come from an open repository (mit-crpg/benchmarks) and have not been
  compared with the current ICSBEP edition; correlations between experiments are not treated.
- The bias/USL summary reaches the conformity checker only through the Python API; the
  conformity panel, the report appendix and the `uygunluk` command do not yet pass it, so there
  K6 reports "USL could not be calculated".

Other limitations:

- Tally uncertainties from a single eigenvalue run are optimistic (correlation between batches);
  use multi-seed runs for power distributions. F_ΔH is a maximum and is biased upward at low
  statistics.
- This is not a CSG editor: raw CSG cells, DAGMC and CAD geometry are outside the scope.
  The interface imports only materials from OpenMC XML. The core layer can convert an OpenMC
  geometry back into a geometry tree only for the patterns that the tool's own builder produces;
  any other geometry is rejected with a reason rather than guessed.
- Fission product yields in depletion use a fixed energy (thermal 0.0253 eV, fast 500 keV).
- OpenMP only (no MPI); tests run on Linux (Ubuntu); Windows (WSL2) and macOS are not verified.

The Turkish README lists further measured pitfalls and limits.

## License

Proprietary software, all rights reserved; see `LICENSE` (the file is added before the first
release). Third-party components keep their own licences: OpenMC (MIT); benchmark models adapted
from mit-crpg/benchmarks (MIT, © 2011–2024 Paul Romano and contributors); nuclear data
(ENDF/B-VIII.0) are downloaded separately from openmc.org and are not distributed with this
program.
