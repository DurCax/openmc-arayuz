<a id="mgxs"></a>
### Group constants and random ray card

The **Group constants and random ray** card at the bottom of the **Analysis** page generates
**flux-weighted multigroup cross sections** (group constants) from a continuous-energy (CE)
Monte Carlo run (`openmc.mgxs`), writes them to an OpenMC multigroup (MG) library (`mgxs.h5`) and
reruns the same geometry with **multigroup Monte Carlo** and with the **random ray** solver,
comparing the results with CE. All three runs go through the [run queue](04j-is-akisi.md#is-akisi)
one after another; the card stays usable while they run. Step by step:
[5.19 Lesson](05d-ders-mgxs.md#ders-mgxs).

This is a **teaching and comparison** tool: the generated constants are not validated as input to
a core simulator (not a certification).

**Definitions** (OpenMC 0.16 `openmc.mgxs`; Stacey, *Nuclear Reactor Physics*, 2007, chapters 4
and 13). V is the region, g the energy group (g = 1 is the highest energy), φ the scalar flux:

    Σx,g   = ∫V ∫g Σx(r,E) φ(r,E) dE dV  /  ∫V ∫g φ(r,E) dE dV      (flux weighted)
    χg     = ∫g' νΣf φ χ(E'→g)  /  ∫ νΣf φ                           (ν-fission weighted, Σχg = 1)
    Σs(g→g') : scattering from g to g'; the ν-scattering matrix also counts (n,xn) multiplication

- **Consistent scattering matrix** (`consistent scatter matrix`): the matrix is the
  track-length estimate of Σs,g times the analog probability matrix, so that
  Σt,g − Σg' Σs(g→g') = Σa,g comes out consistently from the same histories. With the simple
  (analog) matrix this difference would be the difference of two large, noisy numbers
  (measured: a 950 pcm shift of the 2-group k∞ with 4 × 10⁵ histories).
- **P0 transport correction** (out-scatter approximation): Σtr,g = Σt,g − Σs1,g (Σs1,g: the P1
  scattering moment leaving group g) and the matrix diagonal is reduced by the same Σs1,g. The
  removal Σt − Σs(g→g) does not change, so **the infinite-medium k∞ does not depend on the
  correction**; what changes is leakage (D = 1/3Σtr). **None** assumes isotropic scattering and
  uses Σt.
- **Limit**: homogenization is exact only in an infinite medium (a reflective single assembly or
  pin). In a model with leakage the region constants belong to that model's flux spectrum.

| Field | Meaning | Unit | Typical range | Common misuse | Spec key |
|---|---|---|---|---|---|
| **Scope** | **Whole model** or (in core models) **Assembly: name**: the reflective 2D sub-model of the selected assembly (infinite lattice; [K5 sub-model](04c-demet.md#demet)). Per-assembly homogenization is done in this sub-model. | — | single assembly or pin model: whole model only | in a core model, choosing "whole model + Assembly region" and taking it for assembly constants: it is the single-region average of the whole core | (not written to the spec) |
| **Region type** | **Material**: each material is one region (`domain_type = material`). **Cell**: each material-filled cell is one region (`cell`; all instances of a cell repeated in a lattice are one region). **Assembly (whole model, single region)**: the root universe is one region (`universe`); 2–8 group assembly constants and the G×G k∞ are computed only here. | — | homogenization: Assembly; MG run: Material | expecting the k∞ eigenvalue with Material regions: with several regions only the reaction rate ratio is given | `ayarlar.mgxs.bolge` |
| **Group structure** | `openmc.mgxs.GROUP_STRUCTURES` names: CASMO-2/4/8/16/25/40/70, XMAS-172. In 2 groups the boundary is 0.625 eV. | groups | assembly constants: 2–8; MG run: ≥ 70 | running the "same geometry MG run" with 2 groups and blaming the large difference on the method: it is group condensation | `ayarlar.mgxs.grup_yapisi` |
| **Transport correction** | **None** (isotropic scattering, Σt) or **P0** (Σtr, diagonal correction). | — | None | running MG Monte Carlo with P0 in fine groups: the diagonal turns negative and MG MC cannot handle it (measured: −7600 pcm in the CASMO-70 pin cell). The card writes this in the result notes; random ray applies diagonal stabilization and stays correct. | `ayarlar.mgxs.duzeltme` (`yok` \| `P0`) |
| **Additional types** | In addition to the required ones: fission Σf, κ-fission κΣf, capture Σc, inverse velocity 1/v, diffusion coefficient D. Σt, Σa, νΣf, χ and the consistent (ν-)scattering matrices are always generated (needed by the MG library; with P0 also ν-transport). | — | empty | — | `ayarlar.mgxs.turler` |
| **Random ray settings** (advanced) | **Rays per batch**, **Batches / inactive**, **Dead / active distance** (the untallied and tallied path of a ray), **Source shape** (flat, linear, linear in x-y only), **Source region subdivision** (splits source regions with an N×N square mesh; 0 = none). Filled from the model when the group constants are ready: L = max(bounding box diagonal, 30 cm), dead = L, active = 5L (the OpenMC `convert_to_random_ray` rule), no subdivision, 200 rays × 500 batches, 300 inactive. In the pin cell subdivision 0 / 13 × 13 / 26 × 26 gave the same k (1.3574 / 1.3569 / 1.3569 ± 0.0005; 20 / 83 / 120 s). | rays, batches, cm | pin cell: 200 rays, no subdivision; in a large flat region (reflector) subdivision or a linear source | shortening the inactive batches: random ray does **one** source iteration per batch; in the thermal group of water convergence goes as ~0.93ⁿ (measured: 24 pcm off in a homogeneous medium after 150 inactive batches, < 1 pcm after 300) | (not written to the spec) |
| **Generate group constants** | CE run (with the particle/batch numbers of **Run settings**) + library. `ayarlar.mgxs` is written to a copy of the spec; your project does not change. Run directory `<run base>/mgxs_ce`. | — | — | — | — |
| **Rerun in MG** | Same geometry, each region bound to the macroscopic data in `mgxs.h5` (the same path as OpenMC `convert_to_multigroup`); tallies are removed and temperatures cleared (the library is at 294 K). Directory `mgxs_mg`. | — | — | — | — |
| **Run with random ray** | Same `mgxs.h5`, `settings.random_ray`; eigenvalue calculations only. Directory `mgxs_rr`. | — | — | — | — |
| **Save CSV…** | A copy of `mgxs.csv`: region, xsdata name, type, group, outgoing group, value, σ, relative σ. | — | — | — | — |
| **Shown type** | Filters the table to one type. The table shows at most 5000 rows; all are in the CSV. | — | All | — | — |

**Result area.** Summary lines:

- **CE k**: k of the MGXS run.
- **k from constants = Σ νΣf·φ / Σ Σa·φ** (all regions and groups): does not include the net
  (n,xn) production, so it is lower than CE k by that amount (−170 pcm measured in the pin cell).
- **Infinite-medium k∞ (G×G eigenvalue)**: single region only. M φ = (1/k) χ νΣfᵀ φ, M = diag(Σt)
  − νSᵀ (upscatter and (n,xn) included); in 2 groups it is a 2 × 2 problem. Random ray solves the
  same equation: in a homogeneous medium the flat source is exact, so the random ray k equals this
  eigenvalue (checked by a test).
- **Uncertainty**: the σ values in the table are OpenMC statistical deviations (1σ). The σ of the k
  estimates is **first order and assumes independence**: tallies from the same histories are
  correlated, so σ is an approximate magnitude (2 to 5 times the CE σ in the pin cell). The
  eigenvalue σ is propagated from the removal form (Σa + out-scatter); Σt − Σs(g→g) is the
  difference of two large correlated numbers and is not propagated directly.
- Notes: negative diagonal (P0) and k that could not be computed.

**Comparison table.** Rows CE, MG MC, random ray: k ± σ, **Δk vs CE** = (k − k_CE) × 10⁵ pcm and
± (the runs are independent: root sum of squares), for random ray **Δk vs MG** (same `mgxs.h5`: the
method difference only) and run time.

**Acceptance thresholds.** The thresholds come from these measurements and the expected method error: 500 pcm for CE↔MG in 70 groups (homogenization + condensation + isotropic scattering are a few hundred pcm, ~3 times the combined σ ≈ 180 pcm), 300 pcm for RR↔MG with the same `mgxs.h5` (spatial discretization only, ~3 times the MG MC σ ≈ 100 pcm); they are not certification limits.

**Measured values** (`ornekler/pwr_pinhucre.json`, 10 000 particles × 40 active batches,
ENDF/B-VIII.0, 6 threads; `testler/test_y8_kosu.py`):

| Case | k | Difference | Acceptance threshold and reason |
|---|---|---|---|
| CE (MGXS run) | 1.35817 ± 0.00153 | — | — |
| 2 groups, Assembly: G×G k∞ | 1.35891 | +74 pcm | ≤ 4σ_CE: a different estimator from the same histories; in a homogeneous infinite medium flux-weighted constants preserve the reaction rates |
| 2 groups, Assembly: MG MC | 1.35911 ± 0.00067 | +20 pcm vs k∞ | ≤ 3σ_MG |
| 2 groups, Assembly: random ray | 1.35891 | < 1 pcm vs k∞ | ≤ 10 pcm (the flat source is exact in a homogeneous medium) |
| CASMO-70, Material, no correction: MG MC | 1.3575 ± 0.0010 | −66 ± 181 pcm | ≤ 500 pcm: the method error expected in fine groups (region homogenization, group condensation, isotropic scattering) is a few hundred pcm; 500 pcm covers this and about 3 times the combined σ (~180 pcm) of these statistics |
| CASMO-70, Material: random ray (no subdivision, flat) | 1.3574 ± 0.0005 | −10 pcm vs MG (−57 with 13 × 13) | ≤ 300 pcm: spatial discretization error of the flat source and the σ of MG MC (~100 pcm; about 3 times the combined ~110 pcm) |
| CASMO-70, Material, P0: MG MC | 1.2822 ± 0.0014 | −7600 pcm | negative diagonal: invalid (warning note) |
| CASMO-70, Material, P0: random ray | 1.35695 ± 0.00035 | −122 pcm | diagonal stabilization |

Times (same runs): CE + MGXS 27 s (70 groups), MG MC 11 s, random ray 20 s (no subdivision) to
83 s (13 × 13), 200 rays × 500 batches. Random ray is not fast in this small problem; its advantage shows in large, optically
thick problems and in fixed source calculations.

**Output files** (`mgxs_ce/`): `mgxs.h5` (OpenMC MG library, xsdata names `m<id>_<name>`,
`c<id>_<name>`, `u<id>_<name>`), `mgxs.csv`, `mgxs_ozet.json` (settings, names, k estimates).
If a model whose spec has `ayarlar.mgxs` enabled (for example `mgxs_ce/spec.json` in the run
directory) is exported with **File › Export as Python script…**, the script builds the same
`openmc.mgxs.Library` (`mgxs_kutuphanesi`); generating the library after the run is written as
comment lines.

**Validation.** An invalid region/group/type/correction is an **error**; with depletion on, MGXS
tallies are not added (**info**); in a fixed source calculation χ and k∞ are specific to the source
(**info**); a **warning** if the estimated tally memory exceeds 2 GiB (fine groups × cell regions).
