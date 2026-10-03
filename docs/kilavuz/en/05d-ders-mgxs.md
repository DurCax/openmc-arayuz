<a id="ders-mgxs"></a>
## 5.19 Group constants, multigroup Monte Carlo and random ray

**Example file:** `ornekler/pwr_pinhucre.json` · **Level:** advanced · **Estimated time:**
30 minutes (runs about 4 minutes in total, 6 threads) · **Reference:** [Group constants and random ray card](04h3-grup-sabitleri.md#mgxs)

**Goal.** See how continuous-energy Monte Carlo provides **group constants** to a core
simulator: recover the infinite-medium k∞ by hand (a 2 × 2 eigenvalue) from flux-weighted 2-group
constants, run the same geometry with a fine-group library in multigroup (MG) Monte Carlo and
random ray, separate where the differences come from (homogenization, group condensation,
method), and measure the effect of the transport correction.

**Prerequisite.** [5.1 Assembly k∞](05-dersler.md#ders-demet) (reflective boundary = infinite
lattice) and [5.11 Spectrum](05-dersler.md#ders-spektrum) (thermal cut-off 0.625 eV).

**Steps.**

1. Open `ornekler/pwr_pinhucre.json`. In **Run settings** set **Particles / batch** to 10 000,
   60 batches in total, 20 inactive (the statistics of the expected table).
2. On the **Analysis** page go to the **Group constants and random ray** card at the bottom.
   **Scope** = **Whole model**, **Region type** = **Assembly (whole model, single region)**,
   **Group structure** = **CASMO-2 (2 groups)**, **Transport correction** = **None** →
   **Generate group constants**.
3. When the run finishes, read the summary lines: **CE k**, **k from constants = Σ νΣf·φ / Σ
   Σa·φ** and **Infinite-medium k∞ (G×G eigenvalue)**. With **Shown type** look at the
   **Total Σt**, **Absorption Σa**, **ν-fission νΣf**, **Fission spectrum χ** and
   **ν-scattering matrix (consistent)** rows.
4. **Check by hand.** Build the 2 × 2 problem from the table (g = 1 fast, 2 thermal;
   S(g→g') ν-scattering):

       M = | Σt1 − S11    −S21     |        k∞ = νΣf ᵀ M⁻¹ χ
           | −S12         Σt2 − S22 |

   Since χ = (1, 0), k∞ = [νΣf1 (Σt2 − S22) + νΣf2 S12] / det M. Find the card's eigenvalue with
   a calculator (the upscatter S21 is small but not zero).
5. **Rerun in MG** and **Run with random ray**. In the comparison table both multigroup results
   equal the eigenvalue (homogeneous medium).
6. **Transport correction.** Repeat step 2 with **Transport correction** = **P0**: ν-transport
   Σtr replaces Σt and the diagonal of the scattering matrix gets smaller, but k∞ does not change.
7. **Fine groups, same geometry.** **Region type** = **Material**, **Group structure** =
   **CASMO-70 (70 groups)**, **Transport correction** = **None** → **Generate group constants**;
   then **Rerun in MG** and **Run with random ray**. The random ray settings are filled in when the
   library is ready (200 rays, 500 batches, 300 inactive, no subdivision).
8. Repeat step 7 with **P0** and read the summary note.

**Expected result** (ENDF/B-VIII.0; the numbers move by a few hundred pcm with statistics):

| Step | Method | k | Difference | Explanation |
|---|---|---|---|---|
| 2 | CE | 1.3582 ± 0.0015 | — | run with MGXS tallies |
| 3 | Σ νΣf·φ / Σ Σa·φ | 1.3565 | ≈ −170 pcm | the net (n,xn) production does not enter this ratio |
| 3–4 | G×G eigenvalue | 1.3589 | ≈ +70 pcm | ν-scattering includes (n,2n); difference from CE ≈ 0.5σ (σ_CE ≈ 153 pcm) |
| 5 | MG MC | 1.3591 ± 0.0007 | ≈ +20 pcm vs eigenvalue | same constants, homogeneous medium |
| 5 | Random ray | 1.3589 | < 1 pcm vs eigenvalue | the flat source is exact in a homogeneous medium |
| 6 | G×G eigenvalue (P0) | 1.3589 | same as without correction | removal Σtr − S11ᶜ = Σt − S11 |
| 7 | MG MC (CASMO-70, material) | 1.3575 ± 0.0010 | ≈ −70 pcm | homogenization + condensation + isotropic scattering |
| 7 | Random ray | 1.3574 ± 0.0005 | ≈ −10 pcm vs MG | flat source, no subdivision |
| 8 | MG MC (P0) | ≈ 1.28 | ≈ −7600 pcm | negative diagonal: the card warns |
| 8 | Random ray (P0) | ≈ 1.357 | ≈ −120 pcm | diagonal stabilization |

**Why?**

- **Flux weighting preserves reaction rates.** The definition Σx,g = ⟨Σx φ⟩/⟨φ⟩, multiplied by
  the same flux, gives the reaction rates of the CE run. In an infinite homogeneous medium the
  flux is a single number per group, so the 2-group constants reproduce the CE k∞ (within
  statistics). This exactness holds **only in an infinite medium**: in a problem with leakage the
  spatial and angular flux distribution changes and the constants stay tied to that problem's
  spectrum.
- **Why is the ratio lower?** Σ νΣf φ / Σ Σa φ does not count the extra neutrons born in (n,2n).
  The eigenvalue uses the ν-scattering matrix, which holds the (n,2n) multiplication. Their
  difference (≈ 170 pcm) is the (n,xn) contribution in the pin cell.
- **Why does P0 not change k∞?** Σtr = Σt − Σs1 and diagonal S11 − Σs1: the removal
  Σtr − (S11 − Σs1) = Σt − S11 stays the same. The correction only affects leakage (D = 1/3Σtr):
  it matters in a diffusion solver and is invisible in an infinite medium.
- **P0 and MG MC in fine groups.** In the fast groups forward scattering in water is strong
  (μ̄ ≈ 2/3); Σs1 exceeds the diagonal and the diagonal becomes negative. Monte Carlo cannot
  sample a negative probability; the result is invalid. Random ray stabilizes the diagonal
  (diagonal stabilization) and stays correct.
- **Why does same-geometry MG MC differ from CE?** Each material is one region (self-shielding
  and the flux depression inside the fuel collapse to a region average), the resonance structure
  is averaged inside 70 groups and scattering is assumed isotropic. Here the total effect is
  ≈ −70 pcm; it grows with coarse groups and large regions.
- **Why does random ray differ from MG MC?** Both use the same `mgxs.h5`; the difference is the
  **method**: random ray assumes a flat (or linear) source in each source region. Random ray also
  does one source iteration per batch; with too few inactive batches an unconverged k is read.

**Questions.**

1. Compute k∞ from the 2-group table with the formula of step 4. How much does k∞ change if you
   set the upscatter (S21) to zero?
2. The difference between the ratio and the eigenvalue is the (n,xn) contribution. The (n,2n)
   threshold of U-238 is ≈ 6 MeV; in which group does this difference arise?
3. In step 7 choose **Region type** = **Cell**. Does the result change in the pin cell? Why (one
   cell per material)?
4. Repeat random ray with **Source region subdivision** 0, 13 and 26; how do k and the run time
   change?

**Answers.** (1) The formula gives the card's eigenvalue; with S21 = 0 k∞ drops by ≈ 440 pcm
(measured table: 1.35891 → 1.35446): neutrons returning from the thermal to the fast group are
counted as lost. (2) The fast group (> 0.625 eV; the (n,2n) threshold is in the MeV range): (n,2n)
only enlarges the fast row of the ν-scattering matrix. (3) In the pin cell each material is in a
single cell; the regions are the same and the result stays the same within statistics (the names
become `c…`). (4) Measured (CASMO-70, material, 200 rays × 500 batches): subdivision 0 → 1.3574,
13 → 1.3569, 26 → 1.3569 (each ± 0.0005); run time 20, 83, 120 s. In the pin cell the regions are
already thin (fuel radius 0.39 cm; water between the cladding and the cell edge 0.17–0.43 cm):
the difference is at the level of the statistics and subdivision only adds run time. In optically
thick, large flat regions (reflector, water gap) the flat source error grows and subdivision or a
**Linear** source is needed.

**References.** OpenMC 0.16 documentation, *Multigroup Cross Section Generation* (`openmc.mgxs`) and
*Random Ray* chapters; W. M. Stacey, *Nuclear Reactor Physics* (2007), chapters 4 (multigroup
diffusion) and 13 (homogenization); J. R. Tramm et al., "The Random Ray Method for neutral particle
transport", *J. Comput. Phys.* 342 (2017) 229–252.

**Note.** This lesson is a teaching measurement; the group constants and the acceptance thresholds are **not a certification**. The "a few hundred pcm against CE" expected method error is a teaching bound set after the measurements (for homogenization/condensation error see Stacey 2007, chapter 13); it is not a physical threshold.
