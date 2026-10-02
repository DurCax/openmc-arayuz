<a id="ders-tukenme-genisletme"></a>
## 5.17 Depletion extensions: cooling, decay heat and critical boron

**Example file:** `ornekler/pwr_tukenme.json` · **Level:** advanced · **Estimated time:** 30 minutes
(with low statistics the runs take a few minutes)

**Goal.** See how the decay heat and the activity of the fuel fall after burnup, measure the
effect of the integrator choice on a small example, and follow how the critical boron
concentration changes during depletion. Fields:
[4.9.1 Depletion extensions](04i2-tukenme-genisletme.md#tukenme-genisletme).

**Steps.**

1. Open `ornekler/pwr_tukenme.json`. In **Calculation settings** set particles 1000, batches
   15, inactive 5 (for the lesson; the results are noisy). On the **Depletion** page turn
   depletion on, **Steps** = `1, 5`, Advanced › **Chain** = **ENDF/B-VIII.0 thermal** (the full
   chain, for activation products), **Integrator** = **CE/CM**.
2. **Cooling.** Advanced › **Cooling steps** = `1, 10, 100, 1000`, **Cooling unit** = day. The
   step summary says "4 cooling steps (no transport)"; the transport count is 2 × 2 = 4 (the
   last step is a cooling step, so the final transport solution is not run). **Start
   depletion**.
3. In the result table the k column of the cooling rows is "—" and the burnup does not grow.
   On the **Activity, decay heat and photon source** card press **Compute**: the decay heat
   falls fast during the first day and slowly afterwards (short-lived fission products die
   out first). Repeat with **Series** = Activity [Bq] and Photon source; **Export outputs as
   CSV**.
4. **Integrator effect.** Delete the cooling steps, **Integrator** = **CE/LI**, run again with
   the same seed. Compare k and U-235 with the CE/CM run (the two runs'
   CSV files). The difference is at the level of the statistical noise: with steps this short the
   order of the integrator does not decide the result.
5. **Restart.** Set **Steps** = `1, 5, 10`, turn on **Resume from where it stopped** and start:
   only the new step is run, the first two rows do not change.
6. **Critical boron.** Turn restart off, turn on **Criticality search during depletion**,
   **Search type** = Dissolved boron, **Target** = su, guesses 500 and 1500 ppm, bounds 0–5000,
   **k tolerance** 0.005. Start: the table shows the boron found at every step and k ≈ 1.

**What you should see (measured, `testler/test_y4_kosu.py`, CASL chain, 1000 particles × 10 active batches).**

| Quantity | Value |
|---|---|
| k during cooling | "—" (no transport); burnup constant |
| Decay heat | falls after 1 day of burnup: 0.53 → 0.095 → 0.014 W (1 cm pin; days 1, 2, 12) |
| CE/CM − CE/LI | k difference ~1100 pcm (combined 1σ ≈ 1000 pcm); U-235 relative difference after 6 days 1.3e-5 (no threshold) |
| Fast mode (MicroXS) − full | U-235 relative difference ~3e-6 (2 days) |
| Critical boron (fresh pin) | ~3300 ppm; step k within \|k − 1\| ≤ 0.005 + 3σ |

**Questions.** (1) Why does the decay heat fall fastest during the first day of cooling?
(2) How does the CE/LI versus CE/CM difference change as the steps get longer — try a 50-day
step instead of 5 days. (3) Why does the critical boron fall with burnup? (4) Why is fast
mode wrong at high burnup?

**Limits.** The low statistics only speed up the lesson; increase the particle count for a
design value. The waste class (10 CFR 61.55) and the contact dose rate are for information,
**not a certification**.
