<a id="ders-mesh"></a>
## 5.11 Mesh flux and power map, ParaView

**Example:** `ornekler/pwr_mesh_aki.json` · **Level:** intermediate · **Prerequisite:** [5.1](05-dersler.md#ders-demet)
· **Reference:** [4.10 Mesh tally](04j-mesh-tally.md#mesh-tally)

Goal: produce a pin-by-pin power map and a two-group flux map of a 17 x 17 PWR assembly, check
with the σ map whether the statistics are sufficient, and export the result to ParaView.

<a id="ders-mesh-1"></a>
### Step 1: inspect the mesh

1. Open the example **PWR 17×17 assembly: mesh flux and power map** from the start screen.
2. In **Settings › Tallies** select the `mesh_aki_guc` tally: scores flux and kappa-fission,
   **Energy groups** on with **Group structure** CASMO-2 (0.625 eV boundary), **Mesh tally** on,
   **Mesh type** Regular, **Mesh divisions** 17 x 17. With **Take bounds from the model** on, the
   suggestion line shows +/-10.71 cm: mesh cell = 21.42 / 17 = 1.26 cm = rod pitch, so every cell
   is one rod cell. If the mesh did not match the pitch, a cell would collect parts of two rods.
3. Select the `silindirik_aki` tally: **Cylindrical (r, φ, z)**, 8 rings x 12 sectors. On a square
   assembly a cylindrical mesh misses the corners (r = 10.71 cm inscribed circle); it is still
   useful to see the radial profile.

<a id="ders-mesh-2"></a>
### Step 2: run and read the map

Press **Run**. Measurement (5000 particles x 60 batches / 20 inactive, 6 threads, ENDF/B-VIII.0,
OpenMC 0.16.0): ~34 s, k∞ = 1.1829 ± 0.0024. In the **Mesh map** card:

* **Score** kappa-fission, **Normalization** Relative to the mean: 25 cells are blank and marked
  × — 24 guide tubes and 1 instrument tube, no fission. Peak ~1.10 in the rods next to the guide
  tubes (more water, higher thermal flux); lowest ~0.88 near the assembly edge. Median relative
  error 2.7%, largest 4.2%: no fuel cell exceeds the 10% threshold.
* **Score** flux, **Energy group** Group 1 (thermal) and Group 2 (fast): the thermal/fast flux
  ratio is ~0.20 in a guide tube and ~0.16 in the corner fuel rod — the water moderation effect.
* **Display** Relative error: median relative error 2.4% in the thermal group, 1.0% in the fast
  group.
* In the cylindrical tally the ring averages are 0.994 to 1.004: the radial profile of an
  infinite lattice is flat (reflective boundary), which is a **sanity check**.

The same settings with a different seed differ by ±1–2σ; with fewer particles (e.g. 1000 x 20)
you see many × marks — relative error ~ 1/√N.

<a id="ders-mesh-3"></a>
### Step 3: absolute power density

Choose **Normalization** Absolute (from total power). The model is 2D (axially infinite) and the
mesh height is 2 x 10⁴ cm; **Total power** = linear power x 20 000 cm. 3400 MWth / 193
assemblies / 366 cm = 48.1 kW/cm -> enter 9.6 x 10⁸ W. Measurement: heating sum on the mesh
H = 9.38 x 10⁷ eV per source neutron (~ 193 MeV x k/ν ~ 0.486 fissions per source: a check),
mean of the fuel cells 114.5 W/cm³ = 48.1 kW/cm / 264 rods / 1.5876 cm² (rod cell area). The
map is 0.88 to 1.10 times this mean.

<a id="ders-mesh-4"></a>
### Step 4: ParaView

Write `mesh_aki_guc.vtk` with **Export VTK...** and open it in ParaView (**File › Open**,
**Apply**). Colour by `kappa_fission_toplam`, extract the cells with
`kappa_fission_toplam_bagil_hata` > 0.1 using **Threshold** (empty in the fuel for this example).
In a 3D model (e.g. `pwr_3b`) add z bins and take axial slices with **Slice**.

![Relative error map of the flux on a cylindrical mesh](../resimler/en/mesh-harita-silindirik.png)

**Checklist:** the mesh matches the rod pitch; no fuel cell is marked ×; the relative peak is in
the expected range; for absolute normalization the mesh covers the whole fissile region. The
result is a teaching calculation, not a licensing calculation (it is not a certificate).
