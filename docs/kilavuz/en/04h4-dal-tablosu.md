<a id="dal"></a>
### Branch table card (burnup × condition)

The **Branch table** card on the **Analysis** page produces the *branch* table of lattice codes. At the
selected burnup points of a depletion result the **composition is frozen** (burnup does not
advance); only the condition changes and only transport is run:

    burnup step  ×  { T_fuel }  ×  { C_boron }  ×  { T_mod, ρ_mod }   →   k ± σ

The result is the **instantaneous** effect of a condition change at the same composition (Doppler,
boron worth, moderator temperature and density coefficients as a function of burnup); it is not a
new depletion. The runs go through the [run queue](04j-is-akisi.md#is-akisi) one after another and
the table fills as they finish.

**How it works.** (1) The condition is applied by **the same code** as a single-variable scan
(`tarama.parametre_uygula`): the base model does not change. (2) The model is built the way the
depletion run built it (subdivision and pin-by-pin clones in the same order, same material ids);
the volume of every material in the result file is compared with the model and the branch does not
start if they disagree (a wrong composition is never written silently). (3) The step composition
is written into the materials: first the material's atom/b-cm densities, then, for nuclides in the
chain that have cross sections, the atom count at the burnup step / volume (the same logic as
OpenMC 0.16 `Results.export_to_materials`). (4) `model.xml` is written and the job enters the queue.
The branch is built from the **model record in the depletion run directory**; the card says so when
the result no longer belongs to the current model.

| Field | Meaning | Unit | Typical range | Common misuse | Spec key |
|---|---|---|---|---|---|
| **Depletion step selection** | Time points of the result file where the branch is computed (0 = fresh fuel). | step | a few points (0, middle, end) | Selecting every step: the run count multiplies as steps × conditions | (not written to the spec) |
| **Fuel temperature [K]** | Temperature of the fissile burnable material (density fixed; solid fuel). | K | 600–1200 | Varying only T_fuel and calling it a "moderator coefficient" | (not written to the spec) |
| **Dissolved boron** | Boron concentration of the coolant/moderator water (the recipe of the static boron scan). | ppm | 0–1500 | Thinking the water boron burns: the branch composition is frozen | (not written to the spec) |
| **Coolant temperature [K] (density by correlation)** | Coolant temperature; density changes with it through a correlation (water: saturated-liquid table). | K | 550–600 | Assuming density is fixed (the coefficient comes out several times wrong) | (not written to the spec) |
| **Coolant density [g/cm³]** | Sets the density directly (ρ_mod). | g/cm³ | 0.6–0.8 | Giving it together with temperature: the two conflict | (not written to the spec) |
| **Combination** | **Each variable alone**: reference + every value of every variable (the same points as a single-variable scan). **All combinations**: Cartesian product. | — | each alone | Opening the Cartesian product with three variables: the run count explodes | (not written to the spec) |

**Table.** Every row is a (step, condition): k ± σ and **Δk [pcm] = (k − k_ref) × 10⁵** against the
reference branch, σ_Δk = √(σ² + σ_ref²) × 10⁵. Because the runs are treated as independent this
uncertainty is **conservative** (with the same seed the true uncertainty is smaller). **Save CSV**
writes every row (decimal point, fixed column keys).

**Consistency.** The step-0 branch gives, within statistics, the same k as the single-variable scan
at the same condition; the reference branch equals the depletion run's k at that step (measured to
within 2σ in the tests). Terminal: `python3 -m cekirdek.dal model.json depletion_dir --adimlar 0,4
--yakit-sicaklik 600,900 --bor 0,500` ([8. Terminal](08-terminal.md#terminal)).

This is a **teaching and scoping** tool: it does not replace a core simulator's branch tables (HFP/HZP,
exact boron steps, cooling); it is not a certification.
