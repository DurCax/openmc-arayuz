<a id="sekmeler"></a>
# 4. Tab-by-tab reference

This chapter is a reference: it is not read from start to finish; you go to the relevant tab
when you want to know what a field means. Every form field and every check box of the user
interface appears here in the table of its own tab; a field without an entry in the guide
breaks an automated test (`testler/test_kilavuz.py`). The field list is extracted from the
code, not maintained by hand.

The tabs, in the order of the sidebar:

| Section | Tab | What you do there |
|---|---|---|
| [4.0](#pencere-duzeni) | (common) | window layout, menus, shortcuts, model check strip |
| [4.1](04a-malzemeler.md#malzemeler) | Materials | fuel, cladding, coolant, absorber and gas materials |
| [4.2](04b-parcalar.md#parcalar) | Components | pins and plate-type fuel elements |
| [4.3](04c-demet.md#demet) | Assembly | placing components in a rectangular or hexagonal lattice |
| [4.4](04d-geometri.md#geometri) | Geometry | core type (template), height, boundary conditions |
| [4.5](04e-geometri-gelismis.md#geometri-gelismis) | Geometry (advanced) | geometry tree editor |
| [4.6](04f-hesap-ayarlari.md#hesap-ayarlari) | Run settings | calculation type, accuracy preset, source, power distribution, tallies |
| [4.7](04g-calistir.md#calistir) | Run | run, live k-eff, result card, conformity panel |
| [4.8](04h-analiz.md#analiz) | Analysis | parameter sweep, reactivity coefficients, critical search |
| [4.9](04i-tukenme.md#tukenme) | Depletion | burnup calculation and tracked nuclides |

## How to read this chapter

Each tab's section follows the order of the cards on the page (every card is a `###`
subsection) and the fields of each card are given in a table. The columns:

| Column | What it gives |
|---|---|
| **Field** | The label shown in the user interface (without the trailing ":"). Use this text when searching. |
| **Meaning** | The physical or modelling meaning of the field; what it corresponds to in OpenMC. |
| **Unit** | The unit the interface expects. "—" means dimensionless. Angles in degrees, lengths in cm. |
| **Typical range** | Values taken from the example files, code defaults and the `docs/` documents. Not a design value. |
| **Common mistake** | The typical error the model check catches (or cannot catch); the related finding text. |
| **Spec key** | The path of the value in the model file (JSON "spec"). `[]` means a list element: `cubuklar[].daldirma` is the `daldirma` field of each pin. |

The model file is the single source of truth of the interface: the interface edits this JSON,
not OpenMC objects; the `openmc.Model` and the exported Python script are generated from it
([Concepts](03-kavramlar.md#kavramlar)). The last column of each table therefore tells you
where to look when you want to change a value by hand in the JSON or find it in the script.
The note "JSON only" means that the field has no editor in the interface.

<a id="pencere-duzeni"></a>
## 4.0 Window layout and common elements

The main window has five regions: the top bar, the sidebar on the left, the active page in
the middle, the preview panel on the right (design tabs only) and the model check strip at
the bottom.

### Top bar

| Element | What it does |
|---|---|
| New / Open / Save buttons | The same actions as in the File menu (Ctrl+N, Ctrl+O, Ctrl+S). |
| Undo / Redo buttons | Every edit is one step; a core type change and the switch to advanced geometry are undone as well. |
| Model name and type badge | The model name and the plain name of the core type ("17×17 fuel assembly", "hexagonal full core with 163 assemblies"). |
| Model summary | Size, dimensionality (2D / 3D / 3D layered) and calculation type (Eigenvalue (k-eff) / Fixed source); the links go to the relevant tab. |
| **Change type…** | Changes the core type. Only the types usable in this model are listed; Ctrl+Z undoes it. When the type changes, core fields that make no sense for the new type are not deleted from the file, only hidden. |
| **Search commands…** | Opens the command palette (Ctrl+K); see below. |
| **Run** / **Stop** | The primary button. It is not enabled until the geometry preview has been drawn and model check errors have been fixed ([Plot first, then run](06-sonuclar.md#once-ciz)); while a run is in progress it turns into Stop. Shortcut F9. |

### Sidebar and tab markers

The sidebar shows the tabs in three groups: **Model** (Materials, Components, Assembly,
Geometry), **Calculation** (Run settings, Run) and **Results** (Analysis, Depletion). The
tabs are not numbered and **only the tabs that make sense for the model are shown**. The
rules come from a single place (`cekirdek/uygunluk.py`, `gecerli_sekmeler`):

| Tab | When it is shown |
|---|---|
| Components | always except for a spherical assembly (a sphere only has material shells) |
| Assembly | single assembly, rectangular/hexagonal full core, drum-controlled core, advanced geometry, or when the geometry contains a lattice |
| Analysis | in an eigenvalue (k-eff) calculation with fissile material in the geometry, if at least one valid sweep exists |
| Depletion | in an eigenvalue calculation with fissile material in the geometry |
| Materials, Geometry, Run settings, Run | always |

The same principle holds for fields: a field that makes no sense in the model (for example
the power distribution of a pin cell, or the height of a sphere) is not shown. **The value
of a hidden field is not deleted from the file**; when you change the type back the old value
returns. The model check uses the same rules: an option the interface does not offer is a
model check error in a hand-written file.

The marker next to the tab name gives its state; hovering over it shows a one-sentence
explanation:

| Marker | Meaning |
|---|---|
| **!** | There is a model check error located in this tab (takes priority). |
| **•** | A required step is missing: no material, the core type needs a pin but there is none, the assembly or core map is empty, no core fill selected, the model has not been run yet. |
| **✓** | Nothing is missing and there is no error in this step. |
| (no marker) | An optional step (Analysis, Depletion) has not been used yet. |

### Preview panel

In the design tabs (Materials, Components, Assembly, Geometry) the panel on the right redraws
the geometry section after every change. The section is sliced by OpenMC's own library
(`openmc.lib.slice_data`), so the section you see is the geometry OpenMC will really build.
The preview plots a model without tallies (tallies do not affect the plot). **Run** is disabled
while the plot is being drawn and enabled once it finishes successfully.

| Control | Meaning |
|---|---|
| **Section** | xy (from above, z = 0), xz (from the side, y = 0), yz (from the side, x = 0). The default in a 3D model is "xy + xz": two sections side by side. In a 2D model only xy is drawn. |
| **Colour** | Colour by material or by cell. In advanced geometry the selected node is highlighted and the others are faded. |
| **Legend** | Explanation of the material colours. |
| **Refresh** | Redraws the preview (F6). |
| **Resolution** (Advanced) | Low (400) / Normal (800) / High (1400) pixels. |
| **Show overlaps** (Advanced) | Shows points claimed by more than one cell in a separate colour and reports how many there are. Makes plotting several times slower for large cores. |

The preview is drawn in the background, in a separate process; the interface does not wait ("Drawing…" label). OpenMC stays open while the model is unchanged: changing the section, colour or resolution is fast. While the panel is collapsed nothing is drawn, only the model is checked (the **Run** gate still works); it is drawn when the panel is opened. If the drawing process ends unexpectedly, the preview shows a clear error and the process is restarted.

The line below the panel gives the outer size of the model. The panel is collapsed with the
button at its top right.

### Model check strip and list of findings

The bottom strip summarises the model check that runs after every edit: status icon, the
counts of "error / warning / info", the text of the first finding, the **Go to finding**
link and the hint for the next step ("Next step: …"). Clicking the count badge opens the
**Model check findings** list; clicking a row takes you to the relevant page and (if any) the
relevant row. **Check against the data library** (F5) also checks that every nuclide the model
needs is present in `cross_sections.xml`; it is slow, so it does not run on every edit.

Levels: an **error** prevents the run, a **warning** leaves the decision to you, an **info**
only draws attention. The causes and fixes of the finding texts are in
[Troubleshooting](09-sorun-giderme.md#bulgu-turleri).

### Help, "?" buttons and the user guide

The Help menu opens this user guide inside the application, offline. The **?** button next to
a field and the model check findings take you to the relevant section of the guide; F1 opens
the section of the current page. The search box of the guide window searches the whole text.

### Command palette (Ctrl+K)

The **Search commands…** field in the top bar, or Ctrl+K, opens a search box. Menu actions and
the buttons of the active page (for example "Material: Add from library…") are listed by fuzzy
search. The search ignores accents, so typing plain ASCII also finds labels with accented
letters. The arrow keys move through the list, Enter runs, Esc closes. Only the actions that
are enabled at that moment are listed.

### Menus

| Menu | Action | Shortcut | Note |
|---|---|---|---|
| File | New… | Ctrl+N | Start screen ([Start](01-kurulum.md#baslangic)); Esc returns to the open model. |
| File | Open… | Ctrl+O | A model file (`.json`). Examples under `ornekler/` open as a **copy**; they are not overwritten. |
| File | Recent | — | Recently opened files. |
| File | Save / Save as… | Ctrl+S / Ctrl+Shift+S | Use Save as to save an example to your own file. |
| File | Import materials (OpenMC XML)… | — | Only materials are imported ([4.1](04a-malzemeler.md#malzemeler)); geometry is not. |
| File | Export as Python script… | Ctrl+E | A standalone OpenMC script that does not depend on `openmc_arayuz`. One-way: the script cannot be imported back. |
| File | Export as OpenMC XML… | — | A `model.xml` style input. |
| File | Save preview as PNG… | — | The section shown. |
| File | Create report… | Ctrl+R | HTML or PDF report of the model and the last run ([Report lesson](05-dersler.md#ders-rapor)). |
| Edit | Undo / Redo | Ctrl+Z / Ctrl+Y (or Ctrl+Shift+Z) | |
| View | Light theme / Dark theme | — | Plots use the same palette; the choice is remembered. |
| View | Language (Turkish / English) | — | Takes effect when the application is restarted. |
| View | Full screen | F11 | |
| Help | Help and terms (user guide), About | F1 | F1 opens the guide section that belongs to the current page. |

In a saved project the run results are written to the `kosu` directory next to the project;
in an unsaved (new or example) project they go under `~/openmc_kosular`; the Run tab shows the
full path ([4.7](04g-calistir.md#calistir)).

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| F1 | User guide (section of the current page) |
| F5 | Refresh the model check (including the data library) |
| F6 | Refresh the preview |
| F9 | Run |
| F11 | Full screen |
| Ctrl+K | Command palette |
| Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S | New / Open / Save / Save as |
| Ctrl+Z / Ctrl+Y | Undo / Redo |
| Ctrl+E | Export as Python script |
| Ctrl+R | Create report |
| Esc | On the start screen, return to the open model |

In assembly and core maps a left click paints, pressing and dragging paints a series of
cells, and a right click makes the component of that cell the brush; in a hexagonal map the
mouse wheel zooms ([4.3](04c-demet.md#demet)).

### "Advanced" sections

Rarely needed fields are in the collapsible **Advanced** sections at the bottom of the pages
(density unit, free S(α,β) name, assembly orientation, preview resolution…). They are closed
by default; their open/closed state is remembered. In this guide the fields under Advanced
are marked "(Advanced)" in the tables.

### Mouse wheel protection

While you scroll the page with the wheel, a number or selection box that passes under the
cursor does **not change** its value: boxes without focus ignore the wheel and the event goes
to the page scroll. To change a box with the wheel, click it first. (This protection was added
after a real bug in which the core type and the boundary condition changed silently while
scrolling.)
