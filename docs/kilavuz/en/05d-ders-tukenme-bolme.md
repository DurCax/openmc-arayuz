<a id="ders-tukenme-bolme"></a>
## 5.20 Ring subdivision of a Gd pin and the branch table

**Example file:** `ornekler/bolme/pwr_gd_bolme.json` · **Level:** advanced · **Estimated time:** 40 minutes
(ring study: one run ~25 minutes, CASL chain, 2000 × 40 / 15 batches, 6 threads; branch table ~10 minutes) ·
**Reference:** [Region subdivision card](04i3-tukenme-bolme.md#tukenme-bolme), [Branch table card](04h4-dal-tablosu.md#dal)

**Goal.** (1) Measure that burning a pin with a burnable absorber (Gd) **with one average composition**
shows Gd depleting faster than it really does, that the result **converges** as the ring count
grows, and compare the ring types (equal volume / equal thickness / thinning outward). (2) Produce a
**branch table** (T_fuel, C_boron) at the burnup steps of a depletion result and see that it is
consistent with a single-variable sweep.

**Prerequisite.** [5.6 Depletion](05-dersler.md#ders-tukenme), [5.17 Depletion extensions](05c-ders-tukenme.md#ders-tukenme-genisletme).

**Steps.**

1. Open `ornekler/bolme/pwr_gd_bolme.json` (5×5 supercell, a UO₂ 2% + 8% Gd₂O₃ pellet in the middle, a
   single material). On the **Depletion** page the **Region subdivision** card shows **5 equal-volume
   rings**; the preview shows 5 nested rings and the summary line reads **Separate depletion
   materials: 25 → 29** and that the ring volumes sum to the analytic volume (the same radii as the
   hand-written equal-area rings of the old `pwr_gd_tukenme.json`: 0.1832 / 0.2591 / 0.3173 / 0.3664 /
   0.4096 cm).
2. **Particles / batches** 2000, 40 batches, 15 inactive; **Advanced › Chain** = CASL thermal;
   integrator CE/CM, steps 0.02, 0.08, 0.4, 0.5, 1, 1, 1, 1, 1 MWd/kg. **Start depletion**.
3. Set the ring count to 1 (subdivision off), 2, 3, 5, 8 and rerun; also run 5 rings with the **equal
   thickness** and **thinning outward** types. In every run select Gd-157 among the **tracked
   nuclides** and add up all rings of the Gd pin (material name `uo2_gd #i` in the result CSV).
4. On the **Analysis** page, **Branch table** card: tick steps 0 and 2 in **Depletion step
   selection**; **Fuel temperature [K]** 900, **Dissolved boron** 500, **Combination** = each
   variable alone → **Compute branch table**. Read Δk against the reference branch.

**Expected result** (CASL, 2000 × 40 / 15, seed 7; σ of k ≈ 0.004 = 400 pcm):

| Burnup (MWd/kg) → | Remaining Gd-157 fraction | | | | k (6 MWd/kg) |
|---|---|---|---|---|---|
| Run | 1 | 3 | 5 | 6 | |
| 1 ring (undivided) | 0.833 | 0.540 | 0.296 | 0.198 | 1.0551 |
| 2 rings, equal volume | 0.833 | 0.551 | 0.349 | 0.273 | 1.0616 |
| 3 rings, equal volume | 0.836 | 0.571 | 0.377 | 0.295 | 1.0580 |
| 5 rings, equal volume | 0.833 | 0.574 | 0.387 | 0.309 | 1.0543 |
| 8 rings, equal volume | 0.838 | 0.591 | 0.394 | 0.313 | 1.0586 |
| 5 rings, equal thickness | 0.832 | 0.561 | 0.364 | 0.291 | 1.0562 |
| 5 rings, thinning outward (0.6) | 0.840 | 0.590 | 0.390 | 0.312 | 1.0591 |

Branch table (pin cell `pwr_tukenme.json`, 3000 × 30 / 10, measured by the test `test_y5_dal.py`):
reference k = 1.3643 ± 0.0056 (step 0) and 1.3102 ± 0.0029 (5 MWd/kg); at T_fuel = 900 K Δk =
−3071 ± 670 pcm and −2706 ± 536 pcm; at boron 500 ppm −7484 ± 695 pcm and −7189 ± 470 pcm.

**Why?**

- **The average composition burns Gd too fast.** In the undivided pin a neutron absorbed on the outside
  also counts as having "burned" the inside; in reality the outer shell shields the interior
  (self-shielding). At 6 MWd/kg the undivided run leaves 19.8% of the Gd-157, the ringed runs leave
  29–31% (a ~35% relative difference). The value converges 0.295 → 0.309 → 0.313 for 3 → 5 → 8
  rings; 5 rings cannot be told apart from 8 rings within statistics.
- **The k(t) differences are at the level of statistics.** In this small example k fluctuates within
  ±400 pcm between runs; the remaining Gd-157 fraction is far less noisy (power and normalization are
  the same). Raise the particle count to see the ring effect on k(t) (no threshold is set).
- **Ring type.** Equal-volume, equal-thickness and thinning-outward rings give the Gd curve within
  1–3% at 5 rings; in equal thickness the outer ring is large-volume and thins least, which is why
  equal volume is recommended (source: Serpent `div` / CASMO practice).
- **The branch table is consistent with the sweep.** The step-0 branch equals a single-variable sweep at
  the same condition (T_fuel = 900 K: 1.3336 ± 0.0037 and 1.3392 ± 0.0035; boron 500 ppm: 1.2895 ±
  0.0042 and 1.2810 ± 0.0038) within 2σ; the reference branch agrees with the depletion run's k
  (1.3643 / 1.3621; 1.3102 / 1.3007) within 2σ. The boron worth ≈ −15 pcm/ppm (fresh, infinite pin
  cell) changes little with burnup.

**Questions.**

1. What does it mean that the remaining Gd-157 fraction still rises slightly at 8 rings? What would your
   convergence criterion be?
2. Why does the boron worth in the branch table shrink with burnup? (Hint: Gd-157 and U-235 decrease and
   the spectrum hardens.)
3. In the same example set only `gd_cubugu` to 2 rings and subdivide `yakit_cubugu` too: what do you expect?
