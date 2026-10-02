<a id="tukenme-genisletme"></a>
### 4.9.1 Depletion extensions: integrator, cooling, restart, criticality search, fast mode

These fields are in the **Advanced** section of the **Depletion** page's **Burnup settings**
card. All of them are built on `openmc.deplete` (OpenMC 0.16); the interface does not write a
solver of its own. When a key is missing from the file its default is used, and **default
values are not written to the file** (old projects do not change on a round trip). The same
settings are written into the `tukenme_kos()` function of the generated Python script
([8. Terminal](08-terminal.md#terminal)).

#### Integrator

| Option | OpenMC class | Transport solutions per step | Note |
|---|---|---|---|
| Predictor | `PredictorIntegrator` | 1 | first order; previews with short steps |
| CE/CM (default) | `CECMIntegrator` | 2 | second-order predictor-corrector |
| CE/LI | `CELIIntegrator` | 2 | constant extrapolation / linear interpolation |
| LE/QI | `LEQIIntegrator` | 2 | also uses the previous step's rates (first step CE/LI) |
| EPC-RK4 | `EPCRK4Integrator` | 4 | extended predictor-corrector, Runge-Kutta 4 |
| CF4 | `CF4Integrator` | 4 | fourth-order commutator-free Lie |
| SI-CE/LI, SI-LE/QI | `SICELIIntegrator`, `SILEQIIntegrator` | inner iterations + 1 | stochastic implicit; one BOS transport on the first step (with inner-iterations times the particles) |

The transport counts are the `_num_stages` values in the OpenMC source; the step summary
reports them (including cooling and the criticality search). A higher order needs fewer steps
for the same accuracy but runs more transport solutions per step. There is no single answer to
**which one is better**: the CE/CM versus CE/LI difference on a small example is measured in
[lesson 5.17](05c-ders-tukenme.md#ders-tukenme-genisletme) (no threshold is set; the
difference is at the level of the statistical noise).

#### Fields

| Field | Meaning | Unit | Typical range | Common mistake | Spec key |
|---|---|---|---|---|---|
| **Cooling steps** | Steps at zero power (decay only) AFTER the burnup steps, comma separated. OpenMC runs no transport in a step with zero power; these steps have no k-eff ("—" in the table) and the burnup does not grow. | **Cooling unit** | 1, 10, 100, 1000 days | Entering cooling as burnup steps (the power stays on) | `tukenme.sogutma.adimlar` |
| **Cooling unit** | day, hour, year (Julian, 365.25 days) or second. MWd/kg is meaningless (no power). | — | day | — | `tukenme.sogutma.birim` |
| **SI inner iterations** | Visible only for the SI-* integrators: OpenMC `n_steps`. | — | 10 (OpenMC default) | A very large value: run time grows with (n+1) transport solutions per step | `tukenme.si_ic_adim` |
| **Resume from where it stopped** | The previous result in the directory is not deleted. An interrupted run continues from the start of the last saved step; if steps were added to a finished run only the new steps are run. The physics of the previous run (materials, geometry, power, integrator) must be the same and the step list must continue the previous one; otherwise the run does not start and the reason is shown. | — | off | Changing the physics and resuming (refused) | `tukenme.surdur` |
| **Fast mode (MicroXS, no transport)** | One-group microscopic cross sections from a single transport solution (`get_microxs_and_flux`, "direct"), then `IndependentOperator`: no transport in the steps. The spectrum change is not seen and k-eff is not computed step by step. For previews only. | — | off | Using the result at high burnup instead of full depletion | `tukenme.hizli_kip` |
| **Criticality search during depletion (k = 1)** | At the start of every powered step the value that gives k = 1 is searched (`Integrator.add_keff_search_control`, `Model.keff_search` GRsecant). The value found is in the result table and in the h5 file (`keff_search_root`). Not available with SI-* or fast mode. | — | off | A very tight tolerance: the search runs tens of transport solutions per step | `tukenme.kritik_arama.var` |
| **Search type** | **Dissolved boron [ppm]**: the water composition is rebuilt at every trial from the same recipe as the static boron scan. **Control rod insertion [%]**: in the rod universe the absorber + follower are moved into an inner universe and the outer cell's `translation` is the tip position (3D model). The moving absorber is not depleted. | ppm \| % | — | Using the rod search with rod-by-rod depletion (not supported) | `tukenme.kritik_arama.tur` (`bor` \| `cubuk`) |
| **Target** | The water (coolant/moderator) material for boron, the control rod for the rod search. | — | — | A boron search on the fuel (error) | `tukenme.kritik_arama.hedef` |
| **Initial guesses** | The first two GRsecant points. | ppm \| % | 500 and 1500 ppm | Two equal values (error) | `tukenme.kritik_arama.alt`, `tukenme.kritik_arama.ust` |
| **Bounds [min, max]** | The range the value cannot leave; a root outside is clipped to the bound (OpenMC warning). | ppm \| % | 0–3000 ppm; 0–100 % | A guess outside the bounds (error) | `tukenme.kritik_arama.sinir` |
| **k tolerance** | The search stops when \|k − 1\| ≤ tolerance and σ ≤ tolerance. Default 1e-3 (100 pcm): the statistical uncertainty level of a typical depletion step; OpenMC's default (1e-4) needs tens of transport solutions on a small model. | — | 1e-3 | Values such as 1e-5 | `tukenme.kritik_arama.k_tol`, `tukenme.kritik_arama.sigma` |

#### Activity, decay heat and photon source card

Computed with **Compute** once a result is shown (on a large chain it takes seconds per
step). **Series**: decay heat [W], [W/g]; activity [Bq], [Bq/g]; photon source [photons/s].
The table gives the totals at every time point; the text below gives, for the last step, the
**contact dose rate** and the **waste class** per material; **Export outputs as CSV** writes
every series per material.

| Quantity | Source (OpenMC 0.16) | Note |
|---|---|---|
| Activity | `Material.get_activity` | λN; half-lives from the run's chain |
| Decay heat | `Material.get_decay_heat` | λNQ; Q is the chain's `decay_energy` (ENDF/B-VIII.0 decay sublibrary; neutrinos excluded). W/g is per gram of material |
| Photon source | `Material.get_decay_photon_energy` | integral of the decay photon spectrum in the chain |
| Contact dose rate | `Material.get_photon_contact_dose_rate` | FISPACT-II method (semi-infinite slab, in air, build-up factor 2), Gy/h; no bremsstrahlung |
| Waste class | `Material.waste_classification` | US NRC 10 CFR 61.55 near-surface class; spent fuel is high-level waste — **for information, not a certification** |

The simplified CASL chain lacks many activation products (e.g. Co-60); activity and decay
heat come out incomplete. Choose the full ENDF/B-VIII.0 chain for these outputs.

#### Verification

During cooling the decay heat is compared with a single-nuclide analytic solution
(`testler/test_y4_cikti.py`): pure Co-60, P(t) = λN₀e^(−λt)Q; relative difference < 1e-6 (W)
and < 1e-4 (W/g; Co-60 → Ni-60 mass difference). In the criticality search the k of every
powered step satisfies \|k − 1\| ≤ tolerance + 3σ (`testler/test_y4_kosu.py`): the search stops
within the tolerance and the step's own transport solution is an independent measurement
(99.7 %). The results are for teaching, **not a certification**.
