<a id="ders-goruntuleyici"></a>
## 5.18 Viewer: slice, overlaps, tally overlay and 3D

**Example:** `ornekler/pwr_mesh_aki.json`, `ornekler/vver1000_kor.json`, `ornekler/pwr_3b.json` ·
**Level:** intermediate · **Prerequisite:** [5.13](05c-ders-mesh.md#ders-mesh) ·
**Reference:** [4.12 Viewer](04l-goruntuleyici.md#goruntuleyici)

Goal: inspect the inside of a model without running it (cell, material, overlap), see on the
geometry which rod a mesh tally result belongs to, show where the source starts, and check the
model in a 3D shaded view.

<a id="ders-goruntuleyici-1"></a>
### Step 1: slice and mouse info

1. Open the **PWR 17x17 assembly: mesh flux and power map** example and choose **Tools ›
   Viewer…**. The window opens the `xy` slice (z = 0) of the whole assembly: **Visible width**
   21.420 cm.
2. Move the mouse over a fuel rod: the line below shows the coordinates, cell id, instance number
   and material name (e.g. "UO2 ..."). In the water the material is the borated water of the
   example.
3. Zoom into a corner with the wheel: each step slices the new window at full resolution; the
   pellet, gap and clad rings separate. **Coloring** › **Cell** shows every cell in its own color.
   **Show whole model** goes back.

<a id="ders-goruntuleyici-2"></a>
### Step 2: overlaps and undefined regions

1. Choose **Coloring** › **Overlap and undefined region** (the overlap check turns on by
   itself). Expected: **no overlap** in the assembly — the status line has no "OVERLAP"; the model
   is faded grey.
2. Open the **VVER-1000 full core** example and press **Reload model**. The corners of the
   bounding box of the hexagonal core are orange: the region without a cell (−2). This is
   normal — the corners are outside the geometry. An orange patch **inside** the model would be an
   undefined region; an overlap (−3) shows in the error color and the mouse line says "OVERLAP:
   point in more than one cell".

Source of the expected result: the example models are built without overlaps
(`testler/test_h2_isci.py`, no overlap in a clean model); the position of the overlap code is
verified on a known overlapping model by `testler/test_y2_isci.py`.

<a id="ders-goruntuleyici-3"></a>
### Step 3: mesh tally overlay and source points

1. Go back to the PWR 17x17 mesh example and run it ([5.13](05c-ders-mesh.md#ders-mesh) Step 2).
   When the run ends press **Reload model** in the viewer: the statepoint of the last run is
   loaded.
2. Turn on **Mesh tally overlay**, **Score** kappa-fission. Every cell of the 17 x 17 mesh lies
   exactly on top of one rod cell (mesh pitch = rod pitch = 1.26 cm); guide tubes have low
   values. Use **Opacity** to keep the geometry visible; the tally value under the mouse is added
   to the info line.
3. With **Hide unreliable cells (σ mask)** on, cells with a relative error above 10% are not
   drawn. If cells disappear in a short run (e.g. 4000 particles x 40 cycles) the statistics are
   insufficient.
4. **Source points** › **Model source (settings.source)**: points lie only in the fuel rods (the
   `fissionable` constraint of the box source built by the model builder); there are no points in
   guide tubes or water. **Statepoint source bank** shows the fission sites of the last cycle of
   the run.

<a id="ders-goruntuleyici-4"></a>
### Step 4: 3D view and PNG

1. Open the **PWR 3D assembly** example, press **Reload model**, then **Draw** on the **3D view**
   tab. The default camera (azimuth 45°, elevation 30°) shows the outer water surface of the
   assembly.
2. Check the water in **Hidden materials** and press **Draw**: the rod bundle appears. Raising
   the elevation above 45° may fail in the OpenMC 0.16 ray tracer for this model (4.12
   Limitations); the viewer restarts the process.
3. **Save as PNG…** writes the image of the active tab.

The viewer is an inspection tool; seeing no overlap in the slices does not prove that the whole
model is free of overlaps — it is not a certificate.
