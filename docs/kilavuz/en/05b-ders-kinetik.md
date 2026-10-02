<a id="ders-kinetik"></a>
## 5.11 Point kinetics: delayed neutrons and the period

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

The measured β_eff of Godiva used in IFP verification studies is about 659 ± 10 pcm (from a
Rossi-α measurement; e.g. Kiedrowski, Brown & Wilson, Nucl. Sci. Eng. 168, 2011); the run's
680.7 ± 24.5 pcm agrees with it within 1σ.

**What we learned / check questions.**

- Λ = 20 μs and Λ = 5.6 ns differ by a factor of 3600, so why are the periods of the same order
  (0.154 $ → 55 s in step 1; 0.1 $ → 84 s for Godiva)? (For ρ < β the period is set by the decay
  times of the delayed precursors, not by Λ.)
- Why does Λ suddenly matter at prompt criticality (step 4)? (Period ≈ Λ/(ρ − β): microseconds
  for Godiva.)
- With feedback, why does the power fall not to zero but to a value above P₀? (With no heat
  removal ΔT keeps rising and ρ stays negative; the power decreases slowly as the delayed
  precursors decay. In a real reactor heat removal sets a new equilibrium.)
- Why are the Godiva λ_i almost equal to the ENDF/B-VIII.0 U-235 values? (Most fissions are in
  U-235; λ_i is nuclear data and comes from the `decay-rate` / `delayed-nu-fission` tally, not
  from IFP.)
