<a id="mesh-tally"></a>
## 4.11 Mesh tally and VTK

A mesh tally splits a quantity (flux, fission, heating, absorption ...) over the cells of a mesh
that is independent of the model geometry: pin-by-pin power map, radial flux profile, dose map
in a shield. The mesh is added to a tally in the **Tallies** card of the
[Run settings](04f-hesap-ayarlari.md#ayar-tally) page; the result appears on the
[Run](04g-calistir.md#calistir) page in the **Mesh map** card as a 2D slice and is exported to
**VTK** for ParaView. The computation lives in the `cekirdek/mesh_tally/` package; the model
built by the interface and the Python script exported with **Script** build the same mesh (the
same definition function; `testler/test_y1_mesh_tanim.py`).

Example: `ornekler/pwr_mesh_aki.json` (two-group flux and kappa-fission on a 17 x 17 regular
mesh, flux on an 8 x 12 cylindrical mesh). Step by step: [5.13 Lesson](05c-ders-mesh.md#ders-mesh).

![Cylindrical mesh in the tally form: bins, mesh type, explicit bounds and suggestion](../resimler/en/mesh-formu.png)

<a id="mesh-form"></a>
### Mesh fields in the tally form

| Field | Meaning | Unit | Typical range | Common misuse | Spec key |
|---|---|---|---|---|---|
| **Mesh tally** | Adds a mesh filter to the tally (switching it off removes the filter). | — | off | A very fine mesh: fewer histories per cell, larger relative error (see the × mark on the map). | `tallyler[].filtreler[]` (`tur`: `mesh`) |
| **Mesh type** | **Regular (x, y, z)** `RegularMesh`, **Cylindrical (r, φ, z)** `CylindricalMesh`, **Spherical (r, θ, φ)** `SphericalMesh`. A hexagonal mesh is out of scope: the installed OpenMC 0.16.0 has no `HexagonalMesh` class; use a regular or cylindrical mesh for a hexagonal assembly. | — | regular | A cylindrical mesh on a square assembly: the corners stay outside the mesh (suggested r = half the outer size). | `mesh_turu` (`duzenli` \| `silindirik` \| `kuresel`; regular if absent) |
| **Mesh divisions** | Division count on the three axes; the labels follow the type: x, y, z / r, φ, z / r, θ, φ. On regular and cylindrical meshes the z division is shown only in a 3D model and in a sphere. Grids are uniform (φ 0 to 2π, θ 0 to π). | divisions | 17 x 17 x 1 (one per pin), r 5 to 20 | Expecting z divisions in a 2D model (the mesh is a single slice in 2D). | `boyut` |
| **Take bounds from the model** | When on, the bounds are derived from the model bounding box when the model is **built** (`otomatik`); adding a reflector enlarges the mesh too. Switching it off writes the current suggestion as explicit bounds that can be edited. | — | on | Entering small bounds by hand and enlarging the model later. | `otomatik` |
| **Lower bound** / **Upper bound** | Corners of a regular mesh (x, y, z). | cm | bounding box | Lower >= upper: "mesh lower bound must be smaller than the upper bound on every axis". | `alt`, `ust` |
| **Outer radius** | Outer radius of a cylindrical or spherical mesh (inner radius 0). | cm | half the outer size | 0 or negative: "mesh outer radius must be greater than zero". | `r_ust` |
| **z range** | Axial bounds of a cylindrical mesh (lower, upper). | cm | core height | Lower >= upper. | `z_alt`, `z_ust` |
| **Group structure** | With energy groups on, predefined group boundaries: **Manual**, CASMO-2/4/8/16/25/40/70, XMAS-172, SHEM-361. Boundaries are taken from OpenMC (`openmc.mgxs.GROUP_STRUCTURES`) and written to the **Group boundaries [eV]** box; editing the box by hand shows **Manual**. | — | CASMO-2 (0.625 eV) | 172 groups on a 17 x 17 mesh: 49 708 bins, very few histories per bin. | `tallyler[].filtreler[].gruplar` |

The mesh centre `merkez` [x, y, z] (JSON only; default 0, 0, 0) shifts a cylindrical or
spherical mesh; the form keeps this field. Automatic suggestion:

* **x, y**: the model bounding box (reflector included).
* **z**: core height in a 3D model, sphere diameter in a sphere. In a **2D model** (infinite in
  the axial direction, unbounded z) +/-10⁴ cm (`Z_2B_YARI`): the mesh covers the whole z column
  and the value is a **z integral** (independent of the axial drift of the source). In v2 it was
  +/-1 cm; a 2 cm slice counted only a small fraction of the track length. Measured
  (`pwr_mesh_aki`, 5000 particles x 40 active batches): median kappa-fission relative error 21%
  at +/-1 cm, 2.7% at +/-10⁴ cm. Therefore in 2D a **per-volume value has no absolute meaning**
  (it would be divided by the arbitrary mesh height): in 2D the **Per volume** mode divides by
  the cell **area** (z integral / cm²) and the absolute mode asks for a linear power [W/cm]; the
  relative map is unaffected. If the geometry is bounded in z although the spec has no height,
  the mesh is clipped to those bounds (+/-10⁴ cm only for a truly unbounded model).
* **r**: half of the larger side of the bounding box for cylindrical and spherical meshes. Exact
  for a round model; on a **square or hexagonal** model the corners stay **outside** the mesh
  (21.5% of the area of a square assembly, 1 - π/4).

**v2 projects:** 2D mesh tallies without a `mesh_turu` field and with `otomatik: true` are now
built with +/-10⁴ cm (the v2.0 script wrote +/-1 cm; `testler/veri/y1_v2_mesh_betik.txt`).
Raw per-source values and z slices change; the relative map gives the same physics.
Details: [CHANGELOG](../../../CHANGELOG.md).

Scores are chosen from the **Scores** list of the form: flux (`flux`), fission, absorption,
`heating`, `heating-local` (local heating), `kappa-fission`, `fission-q-recoverable` ...

<a id="mesh-harita"></a>
### Mesh map on the Run page

When the run finishes (or a saved run directory is loaded) the mesh tallies of the statepoint
are read. A tally with a filter other than one mesh filter and an optional energy filter is not
mapped (the warning line gives the reason). The card is hidden when there is no mesh tally.

![Mesh map: kappa-fission relative to the mean in a 17 x 17 assembly; × guide tubes (no score)](../resimler/en/mesh-harita.png)

| Control | Meaning |
|---|---|
| **Tally**, **Score**, **Energy group** | The displayed array. The energy group is **Total (all groups)** or a single group; for the total the σ values are assumed independent (σ² summed) — the groups are positively correlated, so this is an **optimistic estimate**; for an exact σ define a separate tally without energy filter. |
| **Slice axis** and slider | The fixed axis and the slice number; the label gives the slice range. On a cylindrical mesh "z fixed" shows the (r, φ) plane in Cartesian form and "φ fixed" is the r-z section; on a spherical mesh "φ fixed" is the meridian plane (ρ, z). |
| **Normalization** | **Per source neutron** (raw OpenMC value; in fixed source OpenMC multiplies by the total source strength — measured: strength 1 -> 30.48, strength 1000 -> 30 478), **Per volume (/cm³)** (per area in 2D, z integral), **Relative to the mean (1 = mean)** (volume-weighted mean: Σ value / Σ volume over scored cells), **Absolute (from total power)**. |
| **Total power** / **Linear power** | Power for absolute normalization. In 3D **Total power** [W]: the power of the region covered by the model, opened with the **Total power** of the power distribution (same definition as `guc.py`). In 2D **Linear power** [W/cm]: total power / active height when the active height is known, otherwise it opens **empty** and you enter it (e.g. 17.6 MW / 366 cm = 48.1 kW/cm). |
| **Display** | **Value**, **Standard deviation (σ)**, **Relative error (σ / value)**. |
| **Mark unreliable cells** | Cells whose relative error exceeds the **Threshold** or that received no score are marked with ×; a cell without score is left out of the colour scale (blank). |
| **Threshold** | Default 10% — a **rough guideline (MCNP, for a single tally)**: the MCNP5 manual (LA-UR-03-1987, Chapter 2, "relative error R" interpretation table) calls R < 0.10 "generally reliable" (except point detectors). For a pin power map the target is **1–2%**. The ± values are OpenMC's **optimistic** deviations that ignore inter-batch correlation. |
| **Export VTK...** | Writes the selected tally with the selected normalization to a `.vtk` file: for each score (each nuclide in a multi-nuclide tally: `<score>_<nuclide>`) and group `<score>_g<n>` (+ `_toplam`), `_sigma` and `_bagil_hata` fields; the relative error of a cell without score is **-1**. `.vtk` is appended to a name without extension; an existing file asks before overwriting; writing is atomic (no half-written file). |

**Absolute normalization** is meaningful only in an eigenvalue calculation: source rate
S = P / (H · e), e = 1.602176634 x 10⁻¹⁹ J/eV (CODATA 2018, exact). **H** is read from the
**unfiltered global heating tally** added when the model is built (`mesh_genel_isi`:
`kappa-fission`, `heating-local`) — S is correct even if the mesh does not cover the fissile
region (on a square assembly a cylindrical mesh sees only ~78% of the heating; using the sum
inside the mesh would inflate absolute values by ~28%). When a heating score is displayed, H is
the same score; for flux and reactions `heating-local` (capture gammas included; local deposition
with photon transport off). `kappa-fission` excludes capture gammas: at the same power, flux and
reactions come out ~3–4% high. `fission-q-prompt` is not used as H (no delayed energy, ~7% low).
In 3D value · S / V (flux n/cm²·s, heating W/cm³); **in 2D** P is the linear power [W/cm] and
the denominator is the cell **area**: value · S / A — the mesh height does not enter the result.
In 2D a hand-made narrow z slice refuses the absolute mode (the slice value is an unknown fraction
of the column). Runs from before this version have no global tally: the absolute mode falls back
to per volume with a warning; rerun the case. The uncertainty of the normalization factor itself
is not added to σ.

<a id="mesh-vtk"></a>
### VTK and ParaView

The file is in legacy VTK format (`DATASET STRUCTURED_GRID`, ASCII). If the Python `vtk`
package is installed, OpenMC's own writer (`Mesh.write_data_to_vtk`, volume normalization off)
is used; otherwise (not in the default environment, no new dependency is added) a built-in
writer with the same point and cell order. Cylindrical and spherical cells are written as
straight-edged hexahedra (OpenMC's default). In ParaView: **File › Open** -> `.vtk` -> **Apply**;
choose a field for colouring (e.g. `kappa_fission_toplam`), extract the `_bagil_hata` > 0.1
cells with **Threshold**, take a slice with **Slice**.

The same mesh in the script (cylindrical example):

```python
import numpy as np
tally_2_mesh_0 = openmc.CylindricalMesh(
    r_grid=np.linspace(0.0, 10.71, 9),
    phi_grid=np.linspace(0.0, 6.283185307179586, 13),
    z_grid=np.linspace(-10000.0, 10000.0, 2),
    origin=[0.0, 0.0, 0.0])
```

<a id="mesh-hatalar"></a>
### Common findings

| Finding | Cause | What to do |
|---|---|---|
| Many × on the map | Few histories per cell (fine mesh, many groups) | Increase particles/batches or coarsen the mesh; relative error ~ 1/√N. |
| "Absolute normalization not possible ..." | Power box empty; run from before this version (no global heating tally); narrow z slice in 2D; fixed source calculation | Enter the total/linear power; rerun; use automatic bounds; in fixed source use "Per source neutron". |
| "Map could not be drawn: relative normalization: no scored cell on the mesh" | The mesh received no score (mesh outside the model, unsuitable score) | Check the bounds and the score. |
| "Mesh tally not shown on the map: ..." | The tally has a filter other than mesh and energy (material, cell) | Define a separate mesh tally. |
| "unknown mesh type: ..." | Wrong `mesh_turu` in the JSON (e.g. hexagonal) | Write `duzenli`, `silindirik` or `kuresel`. |
| "VTK file name must end with .vtk" | Missing extension | Add `.vtk` to the file name (the dialog adds it). |
