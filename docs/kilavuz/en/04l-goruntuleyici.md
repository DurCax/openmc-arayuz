<a id="goruntuleyici"></a>
## 4.12 Viewer

**Tools › Viewer…** inspects the model geometry in a separate window: a slice at any axis,
position and width, material/cell/overlap color modes, the cell and material under the mouse,
[mesh tally](04k-mesh-tally.md#mesh-tally) results overlaid on the slice, source points and a 3D
shaded view. The window does **not** change the model; fix geometry or settings on the relevant
page, then bring them into the viewer with **Reload model**.

The viewer has its own plotting process (the H2 preview worker, `cekirdek/cizim_sureci.py`):
slicing, 3D ray tracing and source sampling run there and the interface never waits. The viewer
does not affect the preview session or the **Run** gate. Step by step:
[Lesson 5.18](05d-ders-goruntuleyici.md#ders-goruntuleyici).

<a id="goruntuleyici-kesit"></a>
### Slice

| Field | Meaning | Unit | Typical range | Common misuse |
|---|---|---|---|---|
| **Slice axis** | Slice plane: `xy` (z fixed), `xz` (y fixed), `yz` (x fixed). Changing the axis returns to the whole model on that axis. | — | xy | Expecting `xz`/`yz` in a 2D model: the model is axially infinite, the slice is a vertical strip. |
| **Slice position** | Position of the plane along its normal axis (z for xy). | cm | 0 (model centre) | In an axially layered model z = 0 shows one layer only; move z for plenum or reflector. |
| **Visible width** | Horizontal width of the window; the vertical width keeps the aspect ratio. The mouse wheel does the same, keeping the point under the cursor fixed. | cm | bounding box | Very small widths (< 1 um) are clamped. |
| **Resolution** | Horizontal pixels (400/800/1400); vertical pixels follow the aspect ratio (square pixels). | pixel | 800 | Look for detail by zooming, not by resolution: each new window is sliced at full resolution. |
| **Coloring** | **Material** (spec colors), **Cell** (by cell id), **Overlap and undefined region** (model faded grey; overlaps in the error color, cell-less region orange). | — | Material | Reading physics into cell colors: they only separate cells. |
| **Overlap check** | `slice_data(show_overlaps=True)`: finds points that lie in more than one cell. The overlap mode turns it on by itself. | — | off | Slow on large models (SFR ~12 s). |
| **Show whole model** | Returns the view to the bounding box. | — | — | — |

Mouse: the **wheel** zooms in/out, **dragging with the left button** pans; the point under the
cursor is written below the window: coordinates (x, y, z), cell id and name, instance, material id
and name. Special codes (OpenMC `slice_data`, 0.16.0):

| Code | Meaning | Shown as |
|---|---|---|
| −1 | void material | white |
| −2 | no cell: outside the geometry **or** an undefined region (OpenMC does not distinguish) | transparent; orange in overlap mode |
| −3 | overlap (only with the check on; measured: material channel −3, cell channel −4) | error color |

−2 in the corners of the bounding box of a cylindrical or hexagonal model is normal (outside the
geometry); −2 **inside** the model is an undefined region and gives "lost particle" in a run.

<a id="goruntuleyici-tally"></a>
### Mesh tally overlay

The statepoint of the last successful run is loaded on opening (otherwise **Choose
statepoint…**). Reading the statepoint runs in a separate thread.

| Field | Meaning | Unit | Typical range | Common misuse |
|---|---|---|---|---|
| **Tally** / **Score** / **Energy group** | The overlaid array; group **Total (all groups)** or one group. | — | first tally | The group-total sigma is optimistic (see 4.11). |
| **Normalization** | **Per source neutron**, **Per volume (/cm³)**, **Relative to mean (1 = mean)** — the same function as Y1 (`cekirdek/mesh_tally/normalizasyon.py`). For absolute values (W/cm³) use **Run › Mesh map**. | unit in the row | per volume | In a 2D model the per-volume value is a z integral (per area). |
| **Opacity** | Opacity of the overlay (0 = invisible, 100 = covers the geometry). | % | 60 | — |
| **Hide unreliable cells (σ mask)** | Cells whose relative error exceeds the threshold, or that have no score, are not drawn (the geometry shows through). | — | on | Turning the mask off and reading a noisy cell as physics. |
| **Relative error threshold** | Mask threshold (source: 4.11, MCNP rough guideline R < 0.10). | % | 10 | — |

The overlay is sampled on the pixel grid of the geometry slice: every pixel centre is converted to
mesh coordinates (regular x, y, z; cylindrical r, φ, z; spherical r, θ, φ) and the mesh cell is
looked up. A mesh cell therefore lies exactly on top of the geometry (`testler/test_y2_gorunum.py`,
`test_y2_pencere.py`: known cell ↔ coordinate). Color scale `cividis`; outside the mesh is
transparent. The value under the mouse is added to the info line.

<a id="goruntuleyici-kaynak"></a>
### Source points

| Field | Meaning | Unit | Typical range | Common misuse |
|---|---|---|---|---|
| **Source** | **Model source (sampled)**: `settings.source` (box or point) is sampled; the `fissionable` constraint is applied by looking up the material at the point. **Statepoint source bank**: the last source sites of the run (`source_bank`). | — | model source | Taking the model source for the converged distribution of the run: it is the first-cycle source. |
| **Number of points** | Points shown (random subset of the bank). | point | 2000 (10–20000) | — |
| **Slice thickness** | Only points within this thickness of the slice plane; **all (projection)** projects every point onto the plane. | cm | all | 3D model, xz, thickness 0: all axial points on top of each other. |

Sampling note: OpenMC's `openmc.lib.sample_external_source` terminates the process for a
fissionable-constrained source in plot mode (no nuclear data loaded; measured); sampling is
therefore done with numpy. Fissionable material: at least one actinide nuclide (Z ≥ 90). If the
acceptance fraction drops below 5% (OpenMC `source_rejection_fraction` default) a clear error is
shown.

<a id="goruntuleyici-3b"></a>
### 3D view

The **3D view** tab produces a shaded image with `openmc.lib.SolidRayTracePlot` (OpenMC 0.16.0).
The camera looks at the model centre.

| Field | Meaning | Unit | Typical range | Common misuse |
|---|---|---|---|---|
| **Coloring** | Material (spec colors) or cell (OpenMC default colors; not the same as the slice cell colors). | — | Material | — |
| **Azimuth** / **Elevation** | Camera direction: angle from the x axis around z / angle from the xy plane. | ° | 45 / 30 | — |
| **Distance factor** | 1 = the bounding sphere of the model just fits the field of view; smaller values zoom in. | — | 1.1 | Moving inside the model (< ~0.3): only an inner surface is visible. |
| **Field of view** | Horizontal field-of-view angle. | ° | 40 | — |
| **Hidden materials** | Checked materials become transparent (e.g. hide water to see the rods). Material coloring only. | — | none | — |
| **Draw** | Requests the 3D image (at canvas size). | — | — | — |

Limitations (measured, OpenMC 0.16.0): in a 2D model the geometry is axially infinite and the image
is an infinite prism. On the VVER-1000 and BEAVRS full-core examples the ray tracer crashes or hangs
the process ("pure virtual method called" / "Lost particle after reflection"); the viewer stops the
process after 30 s, shows a clear error in the 3D tab and restarts the process. On lattice 3D models
(PWR 3D assembly, SMR core) an elevation above about 45° or hidden water makes some rays fail with
"negative distance to a lattice boundary"; lower the elevation or unhide the material. With the
default camera (45° / 30°) the assembly, SMR core, SFR hexagonal, drum core and critical experiment
examples work (320 × 240 pixels 0.01–0.12 s).

**Save as PNG…** saves the image of the active tab (slice or 3D). The viewer is an inspection tool;
finding no overlap does not prove the geometry correct (only points in the drawn slices are
checked) — it is not a certificate.
