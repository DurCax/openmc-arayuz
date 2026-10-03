<a id="ders-triso-varyans"></a>
## 5.21 TRISO fuel and a shielding calculation with weight windows

**Example files:** `ornekler/htgr_kompakt.json`, `ornekler/htgr_pebble.json`,
`ornekler/zirh_agirlik_pencere.json` · **Level:** advanced · **Estimated time:** 40 minutes (runs
total ~10 minutes, 6 threads) · **Reference:** [TRISO card](04b-parcalar.md#triso),
[Variance reduction](04f-hesap-ayarlari.md#ayar-varyans), [Efficiency (FOM) card](04g-calistir.md#calistir-fom)

**Goal.** Answer two separate Monte Carlo questions with the same tool: (1) how a fuel body with
thousands of TRISO particles is modelled, whether the **packing fraction** holds the target, and
whether **random or regular** placement of the particles changes k; (2) how a deep-penetration
shielding problem is accelerated with **weight windows** and how to show the result stays
**unbiased**.

**Prerequisite.** [5.5 Drum](05-dersler.md#ders-tambur) (using a component in advanced geometry) and
[5.16 Shielding example](05d-ders-foton-sicaklik-yuzey.md#ders-foton-sicaklik-yuzey) (fixed source).

### A. TRISO compact and packing fraction

1. Open `ornekler/htgr_kompakt.json` (it opens as a copy). In **Parts** > **TRISO** select
   `agr1_kompakt`. The layers are the INL AGR-1 baseline design: kernel (UCO) diameter 350 um, buffer
   100, IPyC 40, SiC 35, OPyC 40 um (outer radii 0.0175, 0.0275, 0.0315, 0.0350, 0.0390 cm); compact
   radius 0.6225 cm; the model is a **5 mm slice** with reflective z faces (an axially infinite
   compact; the length does not change k, the slice speeds up setup).
2. The summary line reads **857 particles · actual packing fraction 0.3498 (target 0.3500)**. **Hand
   check:** V_container = pi*0.6225^2*0.5 = 0.6086 cm3, V_p = (4/3)*pi*0.039^3 = 2.485e-4 cm3,
   N = int(0.35*0.6086 / 2.485e-4) = 857, actual fraction = 857*V_p / V_container = 0.3498.
3. **Validation** checks the model before the run: a compact needs 3D (the root has a height),
   materials are defined, packing <= 0.64. Above 0.30 a **close random packing (CRP)** warning
   appears; that is expected and setup gets slower.
4. Draw the section on the **Geometry** page: the preview shows the particles. The script (**File >
   Python script**) writes the `openmc.model.pack_spheres(...)` and
   `openmc.model.create_triso_lattice(...)` lines; the script and the interface build the same
   particle centres with the same seed (`testler/test_y9_triso.py`).
5. **Run** (4 000 x 60 / 15). k_eff in this model is a **teaching example** value (a single compact
   cell, no helium channel; not a real HTGR block).

**Does the packing fraction hold the target?** With random placement N = int(pf*V/V_p), so the
fraction is within 1/N of the target (<= 0.12 % at 857 particles). The test recomputes the fraction
by **counting the TRISO particles in the lattice cells** of the built OpenMC model (copies of the
same particle in several lattice cells are made unique) and checks that it is within **+-1 %** of the
target, that the particles do not overlap (nearest centre distance >= 2r) and that they stay inside the
container.

### B. Lattice approximation: random and regular placement

Set **Placement** to **Regular (simple cubic)** (pf = 0.30; the simple cubic limit is pi/6 = 0.5236). In
the regular lattice the count is quantized; the pitch is scanned to give the count closest to the
target and the **actual** fraction is written in the summary line (validation warns when the
deviation exceeds 1 %).

**Measured** (`testler/test_y9_triso.py::test_yavas_duzenli_ve_rastgele_yerlesimin_k_farki`, pf = 0.30,
5 000 x 50 / 15, ENDF/B-VIII.0, OpenMC 0.16):

| Placement | k_eff ± σ |
|---|---|
| random, seed 1 | 1.37298 ± 0.00235 |
| random, seed 2 | 1.37521 ± 0.00250 |
| random, seed 3 | 1.36884 ± 0.00242 |
| regular (simple cubic) | 1.36965 ± 0.00233 |

Result: **the regular lattice is -269 pcm from the mean of the random seeds (1.37234; difference about 0.9 combined sigma); at this precision **no significant difference was measured**, the spread between seeds (636 pcm) is larger than the difference itself. Many more histories are needed to resolve a smaller effect.** This is a difference between modelling approximations: a regular lattice
treats the mutual shadowing of particles (self-shielding, resonance absorption) differently from
random packing; real fuel is randomly packed, the regular lattice is an **approximation** chosen for
speed or simplicity.

### C. Pebble (HTR-10)

Open `ornekler/htgr_pebble.json`. Particle: UO2 kernel diameter 500 um, buffer 90, IPyC 40, SiC 35,
OPyC 40 um; fuel sphere radius 2.5 cm (**about 8335 particles**, packing about 5.0 %; IAEA-TECDOC-1382),
0.5 cm graphite shell, around it a **Wigner-Seitz** helium shell matching the 0.61 packing of the bed
(cell radius 3.54 cm) and a reflective boundary: a **spherical cell approximation** of the infinite
bed. It is not the k_inf of the real bed. A pebble is a sphere; there is no 3D-model requirement. The
volume left in the container is filled with matrix; UO2 volume = N*(4/3)*pi*0.025^3 (the test
checks it through the traversal to a relative difference of 1e-9).

### D. Shield: weight windows

In a deep-penetration problem analog Monte Carlo brings very few particles to the detector. Open
`ornekler/zirh_agirlik_pencere.json`: a 14.1 MeV D-T point source at the centre, 35 cm water, 40 cm
steel, 30 cm water and a 5 cm **detector water** shell at the outside (same composition as water,
separate name); the tally is the flux in the detector material.

1. **Analog run.** With variance reduction off, **Run** (20 000 x 100 = 2e6 histories). The
   **Efficiency (FOM)** card shows the total, relative sigma and the FOM for `aki_dedektor`.
2. **Generate windows.** **Settings > Advanced > Variance reduction**: tick it, **Mode = Generate
   windows**, **Mesh type = Spherical**, **Mesh size = 8 x 1 x 1**, **Max realizations = 40**; **Run**
   with 20 000 x 40. The run transports analog and writes `weight_windows.h5` to the run directory.
3. **Apply the windows.** **Mode = Apply an existing window file**, **Use last run**; **Run** with
   1 000 x 20.

**Measured** (2 000 000 analog histories; 20 000 histories with windows; 6 threads; source:
`testler/test_y9_varyans.py` in this repository):

| Run | Histories | T [s] | detector flux ± sigma [1/s] | rel. sigma | FOM |
|---|---|---|---|---|---|
| analog | 2e6 | 62 | 1.687e9 ± 0.164e9 | 9.8 % | 1.69 |
| MAGIC windows (spherical, 8 divisions) | 2e4 | 109 | 1.597e9 ± 0.066e9 | 4.1 % | 5.37 |

- **Unbiased:** the windowed result agrees with the analog result within **0.51 sigma**
  (combined); the acceptance criterion is <= 2 sigma.
- **FOM gain:** **about 3.2 x** (excluding the time of the generation run; the generation run is an
  analog run and its time must be added separately). It is a measurement, not a threshold: the
  number depends on the depth of the problem.

**Weight windows do not pay off in every problem.** We measured the same calculation in a thinner
shield (35 cm water, 20 cm steel, 30 cm water, 5 cm detector; outer radius 90 cm): analog gave a 4 %
relative error with 10^6 histories (FOM about 14); with the same windows the FOM came out as 1.4-4.6.
In the deep shield (above) analog gave only 10 % error and its FOM was 1.7. So windows pay off at
depths where **analog is poor**; in a thin shield the cost of the split particles exceeds the gain.
The choice of mesh matters too: on an 18^3 regular mesh 3 924 of the 5 832 cells (67 %) got no window
at all; on an 8-division spherical mesh all of them did. With few histories ("generate and apply in
the same run", 2 000 x 60) no window was ever built and the result was bit-identical to analog.

**Scope note.** **FW-CADIS** (`method='fw_cadis'`) exists in OpenMC 0.16 but needs the random ray
**adjoint** solution; it is not in the interface in this version. A wwinp file can be **loaded**
(`WeightWindowsList.from_wwinp`) but OpenMC 0.16 cannot **export** wwinp.

**Not a certification.** The numbers are measurements of the test run in this repository; for your own
shield repeat the same bias check (<= 2 sigma against analog) before trusting the windows.
