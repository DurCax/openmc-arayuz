<a id="malzemeler"></a>
## 4.1 Materials

Every material of the model is defined here: fuel, cladding and structural materials,
coolant and moderator, absorber and gas. Components (pins, plates), assemblies and the
geometry refer to materials **by name**. There are two ways to add a material:

- **Add from library…** (recommended): 21 ready, verified compositions. The production
  parameters (enrichment, temperature, boron…) are stored with the material; **Edit…** opens
  the same parameter form and the material is regenerated from those parameters.
- **Define manually…**: you enter the composition yourself as element or isotope rows.

`bosluk` is a reserved name: in the geometry it means "Void (no material)" and is not defined
here.

### Materials card

The table shows a summary of every material; double-clicking a row edits it. Columns:
**Colour** (colour in the preview), **Name**, **Description** (the text shown next to the
name in lists), **Role**, **Density**, **Temperature**, **S(α,β)** and **Composition**. The
tooltip of the name tells whether the material comes from the library (which entry) or was
defined manually.

| Button | What it does |
|---|---|
| Add from library… | Opens the library window (below). |
| Define manually… | Opens the new material window with an empty composition table. |
| Edit… | Edits the selected material (same as a double click). |
| Copy | Adds a copy of the selected material with a `_2` suffix (for example for two enrichments). |
| Delete | Deletes the selected material. If the material is used in the model, it says in how many places and asks for confirmation; if deleted, those places become undefined and the model cannot be built. |

**Role.** The interface derives the role of every material from its composition
(`cekirdek/uygunluk.py`, `malzeme_rolleri`): **fuel** (contains an element with atomic number
90 or above: Th, U, Pu…), **gas** (density below 0.01 g/cm³), **coolant** and **moderator**
(light, heavy or borated water is both; sodium and LBE are coolants; graphite, beryllium and
ZrH are moderators), **absorber** (at least 5 % of the atoms other than H, C, N, O are B, Gd,
Ag, In, Cd, Hf, Er, Eu, Dy or Sm), **structural** (everything else). Trace constituents
(atom fraction below 0.5 %) do not enter the family rules: graphite with 1 ppm boron is still
graphite. The role is not a field and cannot be edited; it decides which material a Components
template picks, what is offered in material lists (for example the follower list of a control
rod contains no fuel and no absorber) and which sweep in Analysis can be applied to which
material (for example the boron sweep only to materials that contain water).

**Renaming** updates every place of use in the model (pin regions, plates, assembly outer
fill, core, axial layers, advanced geometry). The name cannot be the same as a component or
assembly name: in assembly and layer selections the same name would denote two things.

### Library window ("Add material from library")

On the left the materials are grouped by role: **Fuel**, **Cladding and structural**,
**Coolant and moderator**, **Absorber**, **Gas**. When a material is selected, its
description, the **Name** field and only the parameters that make sense for that material
are shown on the right (boron is not asked for UO₂, enrichment is not asked for water;
temperature is asked for every material). At the bottom a summary of the composition to be
generated, the S(α,β) tables and the description text are shown. If the parameters are
physically doubtful (for example enrichment above 20 %, or a contradiction between density and
loading in U₃Si₂-Al) a ⚠ warning appears below the form; the warning does not change the
material. If the material cannot be built with these values (for example no room is left for
aluminium) the **Add** button is disabled and the reason is given.

| Field | Meaning | Unit | Typical range | Common mistake | Spec key |
|---|---|---|---|---|---|
| **U-235 weight %** | Weight percent of U-235 in uranium (UO₂, UN, U-10Mo, U₃Si₂-Al). | % | 0.01–97; LWR 2–5 (`pwr_17x17` 3.2 %), HALEU 19.75 (default of U-10Mo, U₃Si₂-Al) | Above 5 % the model check warns: the OpenMC enrichment shortcut assumes a fixed U-234/U-235 ratio of 0.008; above 20 % the form warns too; above 97 % undefined | `malzemeler[].kutup.param.zenginlik` |
| **Pu weight %** | In MOX, weight percent of plutonium in the heavy metal (U + Pu). | % | 0.01–100; default 7 | Confusing it with the fissile Pu percentage | `malzemeler[].kutup.param.pu_orani` |
| **Fissile Pu %** | Weight percent of Pu-239 + Pu-241 in plutonium; the rest is Pu-240 and Pu-242. | % | 0–100; default 65 | The Pu vector is simplified; if a detailed vector is needed, define the material manually | `malzemeler[].kutup.param.pu_fissil` |
| **U-235 % in carrier U** | U-235 weight percent of the uranium in MOX (usually depleted U). | % | default 0.25 (depleted U) | Forgetting the depleted U value in place of natural U (0.711) | `malzemeler[].kutup.param.u_zenginlik` |
| **Uranium loading** | Uranium density of the fuel layer of U₃Si₂-Al dispersion fuel. The density is computed from it (and from the porosity). | gU/cm³ | 0.1–10; default 4.8 (MTR) | Entering a fixed mixture density: at 4.8 gU/cm³ the mixture is ≈ 6.73 g/cm³; the old 5.4 g/cm³ lowered the aluminium share from 23 % to 4 % (README "Known pitfalls") | `malzemeler[].kutup.param.u_yukleme` |
| **Porosity** | Void volume fraction of the fuel layer. | — (fraction) | 0–0.3; default 0 | Entering it as a percentage (5 instead of 0.05) | `malzemeler[].kutup.param.gozeneklilik` |
| **Dissolved boron [ppm]** | Weight ppm of natural boron dissolved in water (PWR chemical shim). | ppm | 0–5000; README examples: MTC measurement at 1300 ppm, critical boron of `pwr_17x17` 3430 ppm | Thinking borated water is a separate material: boron is this parameter; the boron sweep changes it as well | `malzemeler[].kutup.param.bor_ppm` |
| **D₂O purity (mol %)** | Molar percentage of D₂O in heavy water; the rest is light water. | % | 50–100; default 99.75 | Assuming 100 % purity: the small H₂O share changes reactivity noticeably in thermal systems | `malzemeler[].kutup.param.saflik` |
| **B-10 atom %** | Atom percentage of B-10 in the boron of B₄C. The smallest value (shown as "natural" in the box) means natural boron. | % | natural (≈19.9) – 100; `altigen_tambur_halkasi` 90 % B-10 | Entering a weight percentage | `malzemeler[].kutup.param.b10_zenginlik` |
| **Density** | Mass density of the material. For water, LBE and sodium it is computed from the temperature and shown read-only (change the temperature to change it). | g/cm³ | UO₂ 10.4, UN 13.5, U-10Mo 17.0, Zircaloy-4 6.55, SS-316 7.99, graphite 1.7, Be 1.85, B₄C 2.52, He 0.0001785 (library defaults) | Forgetting the pellet density in place of the theoretical density; trying to change the density of water separately | `malzemeler[].yogunluk.deger` |
| **Temperature** | Material temperature at which cross section data are used. The °C value is shown next to it. For water the density is also computed from the saturated liquid at this temperature. | K | 250–3000 (form); water 273.15–623.15; defaults: fuel 900, cladding 600, water 293.6 | Leaving the temperature range of the library: neutron data 250–2500 K, **S(α,β) of water only 284–800 K**; a sweep outside the range fails in the middle of the run (README "Known pitfalls") | `malzemeler[].sicaklik` |

In the library window **Add** adds the material and **Cancel** closes the window. The
`kutup` record of the added material (`malzemeler[].kutup.anahtar` and `kutup.param`) keeps
the production parameters; **Edit…** reopens the form from this record.

### Materials in the library

| Group | Entry (`kutup.anahtar`) | Material | Parameters (default) |
|---|---|---|---|
| Fuel | `uo2` | UO₂ — uranium dioxide | enrichment 3.2 %, density 10.4, 900 K |
| Fuel | `mox` | MOX — mixed oxide (U, Pu)O₂ | Pu 7 %, fissile Pu 65 %, carrier U 0.25 %, 10.4, 900 K |
| Fuel | `un` | UN — uranium nitride | 19.75 %, 13.5, 900 K |
| Fuel | `u10mo` | U-10Mo — metallic uranium alloy | 19.75 %, 17.0, 900 K |
| Fuel | `u3si2_al` | U₃Si₂-Al — dispersion fuel | 4.8 gU/cm³, 19.75 %, porosity 0, 350 K |
| Cladding and structural | `zirkaloy4`, `ss316`, `fecral`, `ma956`, `sic`, `al6061` | Zircaloy-4, SS-316, FeCrAl, MA956, SiC, Al-6061 | density and temperature |
| Coolant and moderator | `su` | Light water (H₂O) | 293.6 K, boron 0 ppm; density from temperature |
| Coolant and moderator | `agir_su` | Heavy water (D₂O) | purity 99.75 %, 1.1056, 293.6 K |
| Coolant and moderator | `sodyum`, `lbe` | Liquid sodium, lead-bismuth eutectic | temperature (673 K, 723 K); density from temperature |
| Coolant and moderator | `grafit`, `berilyum` | Graphite (C), Beryllium (Be) | density and temperature |
| Absorber | `b4c`, `agincd`, `gd2o3` | B₄C, Ag-In-Cd, Gd₂O₃ | B-10 percentage in B₄C; density and temperature |
| Gas | `helyum` | Helium (He) | 0.0001785 g/cm³, 600 K |

The S(α,β) table of a library material is selected automatically from the composition (for
example `c_H_in_H2O` for water, `c_Graphite` for graphite).

### Material window (editing and manual definition)

When a **library material** is edited, the window shows the same parameter form as in the
library. In its Advanced section the generated composition is shown in a read-only table;
**Edit composition manually** detaches the material from the library parameters (values such
as enrichment and temperature are no longer recomputed automatically). If a library material
was changed by hand in the JSON, the interface notices this and opens it with the composition
table.

For a **manually defined material** the form is:

| Field | Meaning | Unit | Typical range | Common mistake | Spec key |
|---|---|---|---|---|---|
| **Name** | Name of the material (rules above). | — | — | Renaming updates every reference; a second material with the same name is an error ("the same name is defined 2 times") | `malzemeler[].ad` |
| **Description** | The text shown next to the name in lists (for example "UO₂ 4.0 %"). For a manual material it is not refreshed automatically. | — | — | Changing the enrichment and leaving the old description | `malzemeler[].gorunen_ad` |
| **Density** | The value of the density; its unit is shown next to it (the unit is in Advanced). The value is stored without rounding. | Density unit | positive | 0 or empty ("density not given", "density must be greater than zero"); entering an atom/b-cm value with the g/cm³ unit | `malzemeler[].yogunluk.deger` |
| **Temperature** | Material temperature (see above). | K | 0–5000 (form) | Outside the data range (250–2500 K; water S(α,β) 284–800 K) | `malzemeler[].sicaklik` |
| **Thermal scattering S(α,β)** | Thermal scattering tables that match the composition; if the composition has just started to look like water or graphite, the suggestion is selected automatically. "None (do not add thermal scattering data)" can also be chosen. If no table matches, the row is hidden. | — | water `c_H_in_H2O`, graphite `c_Graphite`, ZrH `c_H_in_ZrH` | Leaving it out: in a thermal spectrum k shifts by percents (warning: "… looks like … but no thermal scattering data (S(α,β)) has been added") | `malzemeler[].sab` |
| **Colour** (Advanced) | Colour in the preview and palettes. | RGB | — | — | `malzemeler[].renk` |
| **Density unit** (Advanced) | g/cm³, atom/b-cm or kg/m³. | — | mostly g/cm³; benchmark models atom/b-cm | Changing the unit without converting the value | `malzemeler[].yogunluk.birim` |
| **S(α,β) (manual)** (Advanced) | Comma-separated S(α,β) table names, for a table that is not in the suggested list. | — | OpenMC table names (`c_H_in_H2O, c_Graphite`) | Writing a hydrogen table for a material without hydrogen (README pitfall: `c_H_in_ZrH` for pure Zr) | `malzemeler[].sab` |

Columns of the **Composition** table (with the **Add row** / **Delete row** buttons):

| Column | Meaning | Common mistake | Spec key |
|---|---|---|---|
| **Type** | Natural element or Isotope (nuclide). | An invalid type is an error ("the type of row … is invalid") | `malzemeler[].bilesim[].tur` (`element` \| `nuklid`) |
| **Name** | Element symbol (`U`, `O`, `Zr`) or nuclide name (`U235`, `Am242_m1`). | Empty name; a nuclide that is not in the library (the F5 data check catches it) | `malzemeler[].bilesim[].isim` |
| **Amount** | Atom or weight fraction of the row (does not need to be normalised). | 0 or negative ("amount must be greater than zero") | `malzemeler[].bilesim[].miktar` |
| **Unit** | Atom fraction or Weight fraction. Do not mix the two units in one material. | An invalid unit is an error | `malzemeler[].bilesim[].birim` (`ao` \| `wo`) |
| **Enrichment %** | Can be entered only in a `U` element row: U-235 weight percent; empty means "natural". | Enrichment in another element or in a nuclide row is an error (the OpenMC shortcut works only for U); above 5 % a warning | `malzemeler[].bilesim[].zenginlik` |

At the bottom of the window it is stated with which role the composition will be recognised
in the model ("This composition is recognised in the model as: fuel"). **OK** saves; if the
density, a name or an amount is missing it does not save and gives the reason.

### Importing from OpenMC XML

**File → Import materials (OpenMC XML)…** adds the materials of a `materials.xml` or
`model.xml` file with their composition, density, temperature and S(α,β). On a name clash a
`_2`, `_3` suffix is added. The operation is undone in one step (Ctrl+Z). **Only materials are
imported**: the OpenMC geometry is raw CSG and cannot be safely converted into the material →
component → assembly → core layers of this interface; a wrong guess would silently produce a
wrong model. Build the geometry in the interface. Python scripts cannot be imported.

### Unused materials and common findings

- "material defined but not used in the model: X" is an **info**; the material does not enter
  the geometry and does not affect the result. Known limitation: materials that appear only in
  a core map or layer key may receive this info wrongly (`docs/ORNEKLER.md` "Changes needed in
  the core").
- "composition is empty" and "density not given" are **errors**; the model cannot be built.
- If water, graphite or beryllium is left without S(α,β), a **warning** is given. Fast spectrum
  systems (sodium, LBE) do not need S(α,β).
- The full list of finding texts and their fixes:
  [Troubleshooting](09-sorun-giderme.md#bulgu-turleri).

The temperature, density and boron sweeps of the Analysis tab change these values during the
run; the saved model does not change ([4.8](04h-analiz.md#analiz)). The materials burned in
depletion are the materials with the fuel role ([4.9](04i-tukenme.md#tukenme)).
