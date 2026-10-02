<a id="ders-kinetik"></a>
## 5.12 Point kinetics: delayed neutrons and the period

**Example file:** `ornekler/godiva_kriter.json` · **Level:** intermediate · **Estimated time:**
15 minutes (the Godiva run takes about 1 minute)

**Goal.** See why delayed neutrons make reactor control possible: which period the same
reactivity gives in a thermal and in a fast system, what changes at prompt criticality, and how
a negative temperature coefficient stops a power excursion. Method and fields:
[point kinetics card](04h2-kinetik.md#kinetik).

**Steps.**

1. **Textbook data.** In any project go to the **Analysis** page; in the **Point kinetics** card
   at the bottom set **Data source** = **Keepin U-235 thermal (6 groups)**, **Neutron generation
   time Λ** = 20 μs. **Reactivity type** **Step**, **Unit** **pcm**, **Reactivity** 100,
   **Simulated time** 100 s → **Compute**.
2. Repeat with the same data for **Reactivity** 200 pcm, then −100 pcm.
3. **Unit** = **$**, **Reactivity** 0.5, **Simulated time** 1 s: the power makes a **prompt jump**
   in the first milliseconds and then rises slowly.
4. **Reactivity** 1.2 $: the card writes a **PROMPT CRITICAL** warning and the solution stops when
   P/P₀ exceeds 10¹⁰.
5. **Feedback.** **Reactivity** 200 pcm, **Simulated time** 50 s; **Adiabatic temperature
   feedback** on, **α_T** −2 pcm/K, **Heat capacity C** 10⁶ J/K, **Initial power P₀** 10⁶ W →
   **Compute**.
6. **Data from a run.** Open `ornekler/godiva_kriter.json` (kinetics parameters are on). Check
   that **Run settings** > Advanced > **Delayed neutron groups** = **6 groups (ENDF/B)** and run it
   in **Run**. Then **Analysis** > **Point kinetics** > **Take from last run**: the table fills with
   the IFP β_i and λ_i and the Λ box with the run's Λ. **Unit** $, **Reactivity** 0.1 →
   **Compute**.

**Expected result.**

| Step | Data | ρ | Inhour stable period | Note |
|---|---|---|---|---|
| 1 | Keepin, Λ = 20 μs | 100 pcm (0.154 $) | **54.92 s** | measured from the solution at 100 s: 54.79 s; the transient of the longest-lived group has not fully died out yet |
| 2 | Keepin | 200 pcm | **17.33 s** | — |
| 2 | Keepin | −100 pcm | **−130 s** | a negative period cannot be shorter than −1/λ_1 ≈ −81 s |
| 3 | Keepin | 0.5 $ | 5.73 s | P/P₀ = 2.07 at 0.1 s ≈ β/(β − ρ) = 2 (prompt jump) |
| 5 | Keepin + α_T = −2 pcm/K | 200 pcm | — | the power peaks at 3.0 P₀ around 21 s; at 50 s ΔT = 127 K, total ρ = −54 pcm, P = 1.97 P₀ |
| 6 | Keepin, Λ = 20 μs | 0.1 $ | **98.6 s** | thermal comparison at the same reactivity |
| 6 | Godiva, IFP 6 groups | 0.1 $ | **83.8 s** | β_eff = 680.7 ± 24.5 pcm, Λ = 5.62 ns |

Groups read from the Godiva run (ENDF/B-VIII.0, 20 000 particles × 120 active batches):

| Group | β_i [pcm] | λ_i [1/s] | ENDF/B-VIII.0 U-235 λ_i |
|---|---|---|---|
| 1 | 29.8 ± 5.1 | 0.01334 | 0.01334 |
| 2 | 119.1 ± 9.5 | 0.03273 | 0.03274 |
| 3 | 111.7 ± 9.5 | 0.12083 | 0.12078 |
| 4 | 281.0 ± 15.8 | 0.30320 | 0.30278 |
| 5 | 94.7 ± 10.3 | 0.85132 | 0.84949 |
| 6 | 44.5 ± 6.1 | 2.85853 | 2.85300 |

**Comparison with experiment (with caution).** The experimental β_eff of Godiva is given as
645 ± 13 pcm (a value derived from the Los Alamos Godiva Rossi-α measurements). The run's
680.7 ± 24.5 pcm is about 5% above it; the difference is ~1.3σ of the combined uncertainty, so
this single run does not show a significant deviation, but the value may be systematically
high (nuclear data ν_d, number of IFP generations). Rossi-α gives a second view: at
criticality α = β_eff/Λ = 0.006807 / 5.624 ns ≈ 1.21 × 10⁶ 1/s; the experimental value is
≈ 1.11 × 10⁶ 1/s, i.e. ~9% high. Together they suggest β_eff slightly overestimated and Λ
slightly underestimated. This is an educational comparison and **is not a certification**.

**What we learned / check questions.**

- Λ = 20 μs and Λ = 5.6 ns differ by a factor of 3600, so why are the periods for the same
  0.1 $ of the same order (Keepin 98.6 s; Godiva 83.8 s)? (For ρ < β the period is set by the decay
  times of the delayed precursors, not by Λ.)
- Why does Λ suddenly matter at prompt criticality (step 4)? (Period ≈ Λ/(ρ − β): microseconds
  for Godiva.)
- With feedback (step 5), is P = 1.97 P₀ at 50 s an equilibrium? (No. With no heat removal ΔT
  rises as long as P > 0, the total ρ becomes ever more negative and the power keeps falling
  towards zero; 1.97 P₀ is a moment of the transient. The decrease is limited by the decay of
  the delayed precursors: the period cannot be shorter than −1/λ_1. In a real reactor heat
  removal sets a new equilibrium power; the adiabatic model does not include it.)
- Why are the Godiva λ_i almost equal to the ENDF/B-VIII.0 U-235 values? (Most fissions are in
  U-235; λ_i is nuclear data and comes from the `decay-rate` / `delayed-nu-fission` tally, not
  from IFP.)
