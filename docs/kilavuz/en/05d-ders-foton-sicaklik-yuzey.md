<a id="ders-foton-sicaklik-yuzey"></a>
## 5.16 Photon heating, temperature interpolation and surface current

**Example files:** `ornekler/pwr_pinhucre.json`, `ornekler/zirh_kure.json` · **Level:** intermediate ·
**Estimated time:** 25 minutes (runs take 1-3 minutes)

**Goal.** Answer three physics questions with the same tool: (1) how gamma energy enters the heat
and why `heating`, `heating-local` and `kappa-fission` differ; (2) how k is computed at a
temperature that is not in the library; (3) how the neutron current entering and leaving a region
balances absorption. Fields: [Advanced](04f-hesap-ayarlari.md#ayar-gelismis),
[surface current tallies](04f-hesap-ayarlari.md#ayar-yuzey),
[surface current card](04g-calistir.md#calistir-yuzey).

### A. Photon transport and heating scores

1. Open `ornekler/pwr_pinhucre.json`. **Calculation settings** > **Tallies** > **+ Tally**,
   **What to measure** = **Custom**, scores: heating, local heating (heating-local),
   kappa-fission, damage-energy.
2. **Run** (Normal). Then turn on **Advanced** > **Photon transport (gamma heating)** and run again.

**Definitions** (OpenMC `docs/methods/energy_deposition.rst`):
- `heating`, photons **off**: neutron KERMA only (MT301); the energy of fission and capture gammas
  is missing. Photons **on**: neutron KERMA (without gammas) + energy deposited by photons per
  collision (analog energy balance).
- `heating-local`: for neutrons, gamma energy counted as deposited at the collision site (MT901);
  on its own it counts gammas once. With photons on, **adding** it to the photon `heating` counts
  gammas twice. In eigenvalue mode OpenMC weights `heating-local` as keff*kerma(non-fission) +
  kerma(fission) and does not use MT301 (Griesheimer et al., PHYSOR 2020).
- `kappa-fission`: recoverable fission energy based on the MT18 Q value (the MT458 counterpart is
  `fission-q-recoverable`); no neutrinos, gammas local; it does **not include capture gammas**.

**Measured** (pin cell, reflective boundary; 2 000 x 30 / 10, ENDF/B-VIII.0, OpenMC 0.16,
`testler/test_y7_fizik.py`):

| Quantity [eV / source neutron] | photons off | photons on |
|---|---|---|
| heating (H) | 9.97e7 +- 0.07e7 | 1.101e8 +- 0.004e8 |
| - neutron part H_n | 9.97e7 +- 0.07e7 | 9.90e7 +- 0.04e7 |
| - gamma part H_g | 0 | 1.111e7 +- 0.003e7 |
| heating-local | 1.107e8 +- 0.008e8 | 1.099e8 +- 0.004e8 |
| kappa-fission (kF) | 1.076e8 +- 0.008e8 | 1.069e8 +- 0.004e8 |

Interpretation. The clean measure with photons on is **H_g / H = 10.1% +- 0.05**: the share of
gamma heating. H = H_n + H_g holds exactly. The closeness of `heating` and `heating-local`
(0.2% with photons on) is not an identity: in eigenvalue mode `heating-local` is keff weighted
(see above) and the agreement is partly a compensation; with photons off H / H_local = 0.90 is
not just the gamma loss either. H / kF = **1.030**; approximate budget: (n,gamma) capture gammas
about +1.9%, the extra fission neutron kinetic energy of kF for (k_inf - 1) about -0.6%, the
remaining about 1.7% photon data / MT458 inconsistency (James 1969, *J. Nucl. Energy* 23, 517;
Sher 1981). The ratio depends on the model and **is not a certification**. `damage-energy` (MT444)
does not depend on the photon mode (within 3 sigma).

### B. Intermediate temperature with interpolation

The ENDF/B-VIII.0 HDF5 library distributed by OpenMC is processed only at 250, 294, 600, 900,
1200 and 2500 K.

3. In **Materials** set the `uo2` temperature to 750 K. With **Calculation settings** >
   **Temperature method** = **Nearest temperature**, validation reports an **error** ("no data in the
   library for 750 K ..."; OpenMC stops at start-up; 750 K is outside the tolerance of both
   neighbours). With **Temperature tolerance** 200 K the error becomes a **warning**: "only a
   library temperature is used: 600 K", so the physics is not that of 750 K.
4. Choose **Interpolation**: validation writes an **info** ("stochastic interpolation between
   600-900 K"). At each collision one of the two neighbouring temperatures is chosen with a
   probability linear in kT.
5. Run three times with fuel at 600, 750 and 900 K (30 000 x 100 / 20).

**Measured:** k(600) = 1.34498 +- 0.00067, k(750) = 1.34029 +- 0.00067, k(900) = 1.33541 +- 0.00063.
Monotonic: steps of 4.9 and 5.3 sigma (sigma_diff = sqrt(s1^2 + s2^2)). k(750) is 10 pcm from the
linear midpoint of its neighbours (limit 3 sigma = 243 pcm): this shows that interpolation **is
applied**, not that the physics is right; the sqrt(T) curvature of about -25 pcm is below the
resolution and a stochastic mix of two temperatures is not true Doppler broadening. Fuel Doppler
coefficient (600-900 K) **-1.78 +- 0.17 pcm/K** (d rho/dT; about -2.4 pcm/K at k = 1, 1/k^2
scaling). Resonance scattering correction (DBRC/RVS) is off; with it the coefficient is about
10-15% more negative (Becker, Dagan & Lohnert 2009; Mosteller Doppler-defect benchmark). The value
belongs to this pin cell (UO2, reflective boundary, only the fuel temperature changes). Water
S(alpha,beta) data cover 284-800 K; water outside this range stops the run. If one nuclide has
data at a single temperature, OpenMC switches interpolation off for **the whole model**
(validation warns).

### C. Surface current and conservation (fixed source)

6. Open `ornekler/zirh_kure.json` (14 MeV fusion point source, water + steel sphere, vacuum boundary,
   strength 1e12 1/s). **+ Tally** > **Type** = **Surface: model boundary (leakage)**, **Energy
   groups** on: `1e-5, 0.625, 1e5, 1e6, 2e7`.
7. **+ Tally** > **Type** = **Surface: box mesh (in / out)**, **Box bounds** lower `-10, -10, -10`,
   upper `10, 10, 10` (source inside). One more: `12, -6, -6` ... `24, 6, 6` (source outside). **Run**.

**Balance** (outer faces of the box; inner faces cancel):

    S + J_in - J_out + U = A

S is the source in the box (the strength if the point source is inside), U = nu-scatter - scatter
(net neutron production in scattering: (n,xn) **and** MT5 with fractional yield; in fixed source
+ nu-fission), A absorption. OpenMC "out" is the partial current leaving a cell, "in" the one
entering. On the model boundary OpenMC signs the net current with the surface normal (+ along the
normal); every crossing of a vacuum surface goes out, so \|J\| per surface is the leakage.

**Measured** (4 000 x 5, strength 1e12 1/s):

| Box | S | J_in | J_out | U | A | residual |
|---|---|---|---|---|---|---|
| source inside | 1.000e12 | 4.993e11 | 1.2812e12 | 1.0e8 | 2.1815e11 | 0 (round-off) |
| outside | 0 | 1.470e11 | 1.3545e11 | 0 | 1.155e10 | 0 (round-off) |

Model boundary leakage 2.557e11 1/s = OpenMC global leakage x strength (same events); **0.245** per
source particle. Whole model: S - L + U - A = 0 (relative 1e-14). In fixed source, with the
analog estimator, the balance holds in every history, provided survival biasing is off and there
are no weight windows and no energy/time cutoffs (OpenMC defaults). **In eigenvalue mode it is
not exact**: S = nu-fission/k is only an expected value; with a converged source the residual is
statistical (small box in the pin cell: residual -0.0002 +- 0.005, |residual| < 3 sigma). The +-
on the card is first order without correlation: approximate. With photon transport on, the global
leakage also counts photons; the card hides that comparison.

> ⚠ **Why (n,xn) alone is not enough.** In ENDF/B-VIII.0 the MT5 (n,anything) channel of Fe56 has
> a neutron yield of 0.46 at 14 MeV (Fe54 0.84, Mn55 0.65): this reaction is not "absorption" but
> loses neutrons. A balance built from the (n,xn) channels only missed 0.15% in this model; U =
> nu-scatter - scatter covers every channel.

**Sources.** OpenMC 0.16 source code (`src/nuclide.cpp`, `src/thermal.cpp`,
`src/tallies/tally_scoring.cpp`, `src/particle.cpp`) and documentation (`energy_deposition.rst`,
`usersguide/tallies.rst`); Lamarsh & Baratta, *Introduction to Nuclear Engineering* (Doppler
broadening, neutron balance). Measurements were taken under the conditions above with one seed;
2-3 sigma differences with other settings are normal.
