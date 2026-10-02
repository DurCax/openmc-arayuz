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
  collision (collision estimator).
- `heating-local`: for neutrons, gamma energy counted as deposited at the collision site (MT901).
- `kappa-fission`: recoverable fission energy (no neutrinos, gammas local); it does **not include
  capture gammas**.

**Measured** (pin cell, reflective boundary; 2 000 x 30 / 10, ENDF/B-VIII.0, OpenMC 0.16,
`testler/test_y7_fizik.py`):

| Quantity [eV / source neutron] | photons off | photons on |
|---|---|---|
| heating (H) | 9.97e7 | 1.101e8 |
| - neutron part H_n | 9.97e7 | 9.90e7 |
| - gamma part H_g | 0 | 1.11e7 (10.1%) |
| heating-local | 1.107e8 | 1.099e8 |
| kappa-fission (kF) | 1.076e8 | 1.069e8 |

Interpretation: with photons off, `heating` misses about 10% of the total heat (H / H_local =
0.90). With photons on, H = H_n + H_g and, since no gamma escapes an infinite lattice, H is close to
`heating-local` (0.2% apart). H / kF = **1.030**: the difference is mainly (n,gamma) capture gammas
(kF does not count them). The ratio depends on the model; equality is not expected and it **is not
a certification**. `damage-energy` (MT444) does not depend on the photon mode (within 3 sigma).

### B. Intermediate temperature with interpolation

ENDF/B-VIII.0 neutron data exist only at 250, 294, 600, 900, 1200 and 2500 K.

3. In **Materials** set the `uo2` temperature to 750 K. With **Calculation settings** >
   **Temperature method** = **Nearest temperature**, validation reports an **error** ("no data in the
   library for 750 K ..."; OpenMC stops at start-up). With **Temperature tolerance** 200 K the
   error becomes a **warning**: "only a library temperature is used: 600 K", so the physics is not
   that of 750 K.
4. Choose **Interpolation**: validation writes an **info** ("stochastic interpolation between
   600-900 K"). At each collision one of the two neighbouring temperatures is chosen with a
   probability linear in kT.
5. Run three times with fuel at 600, 750 and 900 K (30 000 x 100 / 20).

**Measured:** k(600) = 1.34498 +- 0.00067, k(750) = 1.34029 +- 0.00067, k(900) = 1.33541 +- 0.00063.
Monotonic (each step about 7 sigma); k(750) is 10 pcm from the linear midpoint of its neighbours
(limit 3 sigma = 243 pcm). Fuel Doppler coefficient (600-900 K) about **-1.8 pcm/K**. Water
S(alpha,beta) data cover 284-800 K; water outside this range stops the run.

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
source particle. Whole model: S - L + U - A = 0 (relative 1e-14). With the analog estimator the
balance holds in every history; the +- shown on the card is an upper bound without correlation.

> ⚠ **Why (n,xn) alone is not enough.** In ENDF/B-VIII.0 the MT5 (n,anything) channel of Fe56 has
> a neutron yield of 0.46 at 14 MeV (Fe54 0.84, Mn55 0.65): this reaction is not "absorption" but
> loses neutrons. A balance built from the (n,xn) channels only missed 0.15% in this model; U =
> nu-scatter - scatter covers every channel.

**Sources.** OpenMC 0.16 source code (`src/nuclide.cpp`, `src/thermal.cpp`,
`src/tallies/tally_scoring.cpp`, `src/particle.cpp`) and documentation (`energy_deposition.rst`,
`usersguide/tallies.rst`); Lamarsh & Baratta, *Introduction to Nuclear Engineering* (Doppler
broadening, neutron balance). Measurements were taken under the conditions above with one seed;
2-3 sigma differences with other settings are normal.
