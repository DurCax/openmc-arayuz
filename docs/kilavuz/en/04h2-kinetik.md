<a id="kinetik"></a>
### Point kinetics card

The **Point kinetics** card at the bottom of the **Analysis** page computes how the reactor
power responds in time to a reactivity change, using the **point kinetics** equations, and
plots P(t)/P₀. The card does not depend on the model; it takes the delayed neutron data from
one of three places: a run with kinetics parameters enabled (IFP), textbook data (Keepin), or
manual input. The computation takes well under a few seconds; no OpenMC run is made.

**Equations** (Duderstadt & Hamilton 1976, chapter 6; Keepin 1965):

    dn/dt   = [(ρ(t) − β) n + Σ λ_i c_i] / Λ
    dc_i/dt = β_i n − λ_i c_i                      i = 1 … N (N = 6 or 8)

n = P/P₀ (1 at t = 0, critical equilibrium), c_i is the precursor density of group i scaled by
Λ (equilibrium c_i = β_i/λ_i), β = Σ β_i. The gap between the prompt scale
(−(β − ρ)/Λ ≈ −10³ … −10⁶ 1/s) and the delayed scale (≈ 10⁻² 1/s) makes the system **stiff**;
the solver is therefore not an explicit method but `scipy.integrate.solve_ivp` with the
**Radau** method (analytic Jacobian, relative tolerance 10⁻⁹).

| Field | Meaning | Unit | Typical range | Common misuse | Spec key |
|---|---|---|---|---|---|
| **Data source** | **Keepin U-235 thermal (6 groups)**: Keepin, Wimett & Zeigler, Phys. Rev. 107, 1044 (1957) / Lamarsh & Baratta (2001) table 7.4 values, Σβ_i = 650.2 pcm. **Last run (IFP)**: β_i, λ_i and Λ read from the last successful run. **Manual**: you fill the table yourself (it starts from the current data). With textbook or run data the table cannot be edited. | — | Keepin | using the Keepin U-235 thermal data for a non-LWR system (fast, MOX): β and λ_i differ | (not written to the spec) |
| **Take from last run** | Reads the statepoint of the last successful run in this project. The run needs [Run settings](04f-hesap-ayarlari.md#hesap-ayarlari) > **Compute kinetics parameters** and **Delayed neutron groups** (6 or 8) enabled; otherwise the card says why. | — | — | expecting data from a run with kinetics off | — |
| **Number of groups** | Number of groups (table rows) for manual data. | groups | 6 (1–8) | — | — |
| Table **β_i [pcm]**, **λ_i [1/s]** | Effective delayed neutron fraction and precursor decay constant per group. β_i ≥ 0, Σβ_i > 0 and λ_i > 0 are required; otherwise an error is shown and nothing is computed. | pcm, 1/s | λ_1 ≈ 0.0124 (≈ 56 s half-life) … λ_6 ≈ 3 1/s | entering β_i as Δk/k (0.0002): the table expects **pcm** (21.5) | — |
| **Neutron generation time Λ** | Prompt neutron generation time. | μs | example values (measured with this program): PWR 17×17 assembly 18.9 μs, Godiva 5.6 ns = 0.0056 μs | confusing it with the prompt neutron lifetime ℓ: Λ = ℓ/k | — |
| **Reactivity type** | **Step**: constant ρ from t = 0. **Ramp**: ρ rises linearly over the **Ramp duration**, then stays constant. | — | Step | — | — |
| **Unit** | **pcm** (1 pcm = 10⁻⁵ Δk/k) or **$** (1 $ = β_eff). When the unit changes, the value is converted with the current Σβ_i. | — | pcm | thinking of $ with another system's β: 1 $ is a different number of pcm in every system | — |
| **Reactivity** | ρ inserted by the step; for a ramp, ρ reached at the end of the ramp. A negative value gives a subcritical transient. | pcm or $ | example: ±(10–300) pcm | entering ρ ≥ 1 $: a **PROMPT CRITICAL** warning appears (below) | — |
| **Ramp duration** | Duration of the ramp; visible only for a ramp. Ramp rate = ρ / duration. | s | 1–100 s | — | — |
| **Simulated time** | End time of the solution. The stable period is measured only after the transient of the longest-lived group has died out (a few × 1/λ_1 ≈ minutes). | s | 100 s | reading a "stable period" from a short run: the measured period has not yet approached the Inhour value | — |
| **Adiabatic temperature feedback** | No heat removal: dΔT/dt = P₀ (P/P₀) / C and ρ = ρ_ext + α_T ΔT. ΔT is drawn dashed on a second axis. | — | off | taking the adiabatic result as permanent for a case with heat removal (steady operation) | — |
| **α_T** | Temperature reactivity coefficient. A positive value gives a warning (unstable feedback). | pcm/K | example value: −2 pcm/K (no sourced typical range is given; measure the Doppler coefficient of your own model with an Analysis scan) | taking the unit as Δk/k/K: the box expects **pcm/K** | — |
| **Heat capacity C** | Total heat capacity of the heated mass. | J/K | — | — | — |
| **Initial power P₀** | Power at t = 0. | W | — | — | — |
| **Compute** | Validates the inputs and solves; the result text, warnings and the P(t)/P₀ plot are written. The plot switches to a logarithmic axis when the power changes by more than a factor of 100. | — | — | — | — |

The **result text** gives ρ (pcm and $), the **Inhour stable period** T = 1/ω₀ (below), the
**period measured from the solution** (slope of ln P over the last 10% of the time axis),
P(t_end)/P₀ and, with feedback, ΔT and the total ρ.

**Inhour equation.** For a step reactivity the solution has the form n(t) = Σ A_k e^(ω_k t);
the ω_k are the N + 1 roots of ρ = ω Λ + Σ β_i ω / (ω + λ_i). The largest root ω₀ gives the
stable period (T = 1/ω₀); for ρ > 0 there is a single positive root, for ρ < 0 all roots are
negative and ω₀ > −λ_1 (a negative period can never be shorter than −1/λ_1, ≈ −81 s with the
Keepin data). The roots are found separately in each interval between poles (Brent's method).

**Prompt critical (ρ ≥ 1 $).** The power no longer waits for delayed neutrons and rises on the
Λ time scale (period ≈ Λ/(ρ − β)). The card writes a **PROMPT CRITICAL** warning; if P/P₀
exceeds 10¹⁰ the solution is stopped and this is reported too. Point kinetics without
feedback gives only a qualitative picture in this region.

**Where does λ_i come from?** IFP does not give λ_i. In the run a separate tally scores
`decay-rate` and `delayed-nu-fission` per group; λ_i = ⟨λ_i ν_d,i Σ_f φ⟩ / ⟨ν_d,i Σ_f φ⟩ (the same
definition as OpenMC `mgxs.DecayRate`). This is the arithmetic average of the nuclide λ values
within group i weighted by the **precursor production rate** (ν_d,i Σ_f φ): a forward (not
adjoint-weighted) average. β_i, in contrast, is **adjoint-weighted**; the two weights differ (the
difference vanishes with a single dominant fissile nuclide). The inventory-preserving harmonic
average (Σ ν_d / Σ (ν_d/λ)) would need per-nuclide scores and is not computed. λ_i is **nuclear
data**: ENDF/B-VIII.0 has 6 groups with nuclide-dependent λ (U-235:
0.01334, 0.03274, 0.12078, 0.30278, 0.84949, 2.85300 1/s), JEFF-3.1+ has 8 groups with the same λ
for all nuclides. β_i, on the other hand, is the **adjoint-weighted** effective fraction from
IFP: β_eff,i = ⟨IFP beta numerator⟩_i / ⟨IFP denominator⟩. Λ follows the OpenMC
`StatePoint.get_kinetics_parameters` definition, Λ = ⟨IFP time numerator⟩ / (⟨IFP denominator⟩
k_eff). The λ_i uncertainty assumes independent numerator and denominator; since the two are
strongly correlated, it is an **upper bound**.

**Which β?** The $ conversion and the prompt-critical threshold use the same β everywhere: the
table's **Σβ_i** (for run data, the sum of the grouped IFP tally = β_eff on the result card). The
run also scores an unfiltered `delayed-nu-fission` tally; if Σ dnf_i is smaller than this total,
the library has more groups than requested (JEFF data with 6 groups) and the card warns that
β_eff is too small.

**Verification** (`testler/test_y6_kinetik.py`, `testler/test_y6_tally.py`):

| Check | Result |
|---|---|
| One-group step: solver vs analytic two-exponential solution | relative difference ≤ 1.4 × 10⁻¹⁰ |
| One-group Inhour roots vs closed-form quadratic roots | within 10⁻⁹ |
| 6-group step: solver vs matrix exponential (exact linear solution) | ≤ 1.2 × 10⁻¹⁰; Λ = 10⁻⁷ s (stiff) ≤ 10⁻¹¹ |
| Asymptotic period vs Inhour root (Keepin, 100 pcm) | 54.92 s vs 54.92 s (within 0.1%) |
| Prompt jump (0.5 $, Λ = 10⁻⁷ s) n = β/(β − ρ) | 2.008 vs 2.000 |
| Nordheim–Fuchs (ρ = β + 200 pcm, α = −2 pcm/K): ΔT at the peak = (ρ − β)/|α|, P_max, total ΔT = 2(ρ − β)/|α| | 101 K vs 100 K; 1.02 × 10⁹ vs 1.00 × 10⁹; 204 K vs 200 K |
| Godiva IFP 6 groups: Σβ_i = β_eff; β_i and Λ = OpenMC `get_kinetics_parameters` | identical (10⁻⁹) |
| Godiva λ_i vs ENDF/B-VIII.0 U-235 | within 0.4% |

**Limits.** Point kinetics assumes a fixed flux shape (no spatial effects, xenon or heat
removal); the feedback is a single adiabatic temperature only. Results are for education and
**are not a certification**. Step-by-step example: [point kinetics lesson](05b-ders-kinetik.md#ders-kinetik).
