<a id="sorun-giderme"></a>
# 9. Troubleshooting

This chapter starts from an error or warning text: **symptom → cause → fix**. The program itself
produces two kinds of messages, and they are read separately:

- **Model-check findings** are produced *before* a run, every time the model changes (the findings
  panel below the design pages and the badge in the status bar). Source: `cekirdek/dogrula/` and, in
  advanced geometry, `cekirdek/geometri/denetim.py`.
- **Conformity-check findings** are produced *after* a run, on the results in the run directory (the
  Conformity panel on the Run page, the report annex and `openmc-arayuz-kosu uygunluk`). Source:
  `cekirdek/uygunluk_denetimi/`. The rules are referred to by their identifiers K1-K16.

Quick orientation:

| Symptom | Where to look |
|---|---|
| The RUN button is disabled | [9.5 Run problems](#kosu-sorunlari) and [Plot first, run later](06-sonuclar.md#once-ciz) |
| A red row in the findings panel | [9.2 Finding types](#bulgu-turleri), the table of the row's location code |
| "not met" or "not applicable" in the Conformity panel | [9.3 Conformity rules](#uygunluk-kurallari) |
| "The source distribution ... is still drifting" | [K1: source not converged](#yakinsamadi) |
| "USL could not be calculated" | [USL could not be calculated](#usl-hesaplanamadi) |
| The application does not start, data not found | [9.4 Installation and environment problems](#kurulum-sorunlari) |

In every case look at the application log first: `~/.local/state/openmc_arayuz/openmc_arayuz.log`
(under `XDG_STATE_HOME` if it is set). Attach this file when you report a problem.

<a id="bulgu-okuma"></a>
## 9.1 Reading model-check findings

Every finding has three parts: **level**, **location** and **message** (most also have a
*recommendation*).

| Level | Meaning | What to do |
|---|---|---|
| **error** | The model cannot be built or the run would certainly be wrong. The RUN button is not enabled. | The run does not start until it is fixed. |
| **warning** | The run can be done, but the result may be biased or differ from what you expect. | Read it; run if you accept it knowingly. |
| **info** | Only draws attention (an ignored field, a default behavior). | Nothing to do unless needed. |

Findings are sorted errors first, then warnings, then info. On the calculation pages (Run
settings, Run, Analysis, Depletion) the same findings are in the badge in the status bar; clicking
the badge opens the list.

**Go to finding:** clicking a row makes the program find the page from the **location** code of the
finding and switch to it. The mapping is (`arayuz/pencere/model_islemleri.py`):

| Location code prefix | Page opened |
|---|---|
| `malzemeler`, `malzeme:` | Materials |
| `cubuk:`, `plaka:` | Components |
| `demet:` | Assembly |
| `kor`, `kor/katman ` | Geometry |
| `ayarlar`, `veri kutuphanesi`, `kaynak`, `tally:`, `guc dagilimi`, `guc_dagilimi` | Run settings |
| `tukenme`, `tukenme/` | Depletion |
| `geometri:`, `dogrulama`, `uygunluk:` | no automatic switch (see the tables below) |

The location code is an identifier and is not translated; the list shows it with a readable name
(`malzeme:uo2` → "Material uo2", `kor/katman 2 (su)` → "Core, layer 2 (su)").

<a id="bulgu-turleri"></a>
## 9.2 Finding types (by location code)

The messages below are taken from the code (`cekirdek/dogrula/*.py`, `cekirdek/geometri/denetim.py`,
`cekirdek/dogrula/agac.py`). "..." is the variable part (a name, a number). For a message you do not
find in the list, read its recommendation; recommendations come with the message itself.

### `veri kutuphanesi`: nuclear data library

These findings are produced only by the check against the data library (F5) and by the pre-run gate.

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| the OPENMC_CROSS_SECTIONS environment variable is not set | error | Step 3 of the installation was not done or the terminal was not reopened. | `./veri_indir.sh --bashrc`, then a new terminal; see [Nuclear data](01-kurulum.md#nukleer-veri). |
| cross_sections.xml not found: ... | error | The variable points to a wrong path (disk changed, data moved). | Correct the path or download the data again. |
| cross_sections.xml could not be read; nuclide check skipped | warning | The file is corrupt or unreadable. | Check the file; download the data again if needed. |

### `malzemeler`: the material list as a whole

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| 'bosluk' is a reserved name (void, no material); it cannot be used as a material name | error | `bosluk` is the reserved name of the void fill. | Rename the material. |
| material used but not defined: ... | error | A component or the core refers to a deleted or misspelled material. | Define the material or correct the reference ([Materials](04a-malzemeler.md#malzemeler)). |
| material defined but not used in the model: ... | info | The material is nowhere in the geometry; it has no effect on the result. | Delete it if not needed. |
| materials could not be built: ... | error | The composition could not be converted to OpenMC (invalid element/nuclide name). | Read the OpenMC text in the message and correct the composition row. |

### `malzeme:`: a single material (`malzeme:uo2`)

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| the same name is defined ... times | error | Two materials have the same name. | Rename one of them. |
| composition is empty | error | The composition table has no row. | Add at least one element/nuclide row. |
| density not given / density must be greater than zero: ... | error | The density is empty or ≤ 0. | Enter a positive value in g/cm³ or atom/b-cm. |
| the type / unit of row '...' is invalid | error | In hand-written JSON the type is not `element`/`nuklid` or the unit is not `ao`/`wo`. | Correct the type and the unit. |
| the amount of '...' must be greater than zero | error | The amount of a composition row is ≤ 0. | Enter a positive amount or delete the row. |
| enrichment is defined on element '...'; enrichment can only be used on the U element | error | OpenMC applies enrichment only to the U element and rejects it during the run. | Move the enrichment to the U row. |
| enrichment is defined on nuclide row '...'; enrichment is ignored for a nuclide | error | Enrichment makes no sense on a nuclide row. | Give the isotope amounts directly. |
| the enrichment of '...' must be in the range 0-100 % | error | Enrichment out of range. | Enter a weight percent between 0 and 100. |
| U enrichment ... %: OpenMC's enrichment shortcut assumes a fixed U234/U235 mass ratio of 0.008 | warning | Enrichment above 5 %; the shortcut is correct only at low enrichment. | Give the composition by nuclide (U234/U235/U238) or accept the U-234 sensitivity. |
| looks like ... but no thermal scattering data (S(α,β)) is added | warning | A dense moderator such as water, graphite, beryllium or ZrH has no S(α,β); in a thermal spectrum k shifts by about a percent. | On the Materials page add the S(α,β) the message suggests (e.g. `c_H_in_H2O`). |
| hydrogen in a dense phase but no thermal scattering data (S(α,β)) is added | warning | A hydrogenous dense material matches no ready-made rule. | Choose the S(α,β) that fits the phase the hydrogen is bound in. |
| nuclide not in the data library: ... | error | The library has no data for this nuclide. | Change the composition or use a library that contains this nuclide. |
| thermal scattering data (S(α,β)) not in the library: ... | error | The selected S(α,β) name is not in the library (typo). | Pick an existing entry from the list. |

### `cubuk:`: fuel pin and control rod (`cubuk:yakit_cubugu`)

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| at least two regions are needed (inner region + outer fill) | error | The pin has only one region. | Define an inner region and an outer fill (coolant) ([Components](04b-parcalar.md#parcalar)). |
| the radius of the last region must be empty | error | The last region fills the rest of the cell; it has no radius. | Delete the radius of the last region. |
| the radius of region ... must be greater than zero | error | The radius of an inner region is empty or ≤ 0. | Enter a positive radius. |
| radii must be in increasing order: r1 = ... ≥ r2 = ... | error | The regions are not ordered from inside to outside, or two radii are equal. | Put the radii in increasing order. |
| the material of region ... is not selected | error | A region was left empty. | Select a material; if it is empty on purpose, "Void (no material)". |
| undefined material: ... | error | A region refers to a deleted material. | Select or define the material. |
| a control rod requires a 3D model (core height undefined) | error | Insertion needs an axial tip position. | On the Geometry page set the height to "3D". |
| insertion must be between 0 % and 100 % | error | Insertion out of range. | Enter a value between 0 and 100 (0 % withdrawn, 100 % fully inserted). |
| invalid absorber region: ... | error | The absorber region number is not one of the regions of the pin. | Pick the absorber region from the list. |
| the material of the absorber region ('...') contains no strong neutron absorber | warning | The absorber region has no B, Gd, Ag, In, Cd, Hf... | Choose B4C, Ag-In-Cd, Gd2O3 or Hf. |
| no follower material selected: when the rod is withdrawn its place stays void (no material) | warning | No material fills the place of the withdrawn rod. | Usually choose the coolant. |

### `plaka:`: plate-type fuel element (`plaka:mtr_eleman`)

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| ... must be greater than zero: ... | error | Number of plates, a thickness or the width is ≤ 0. | Enter a positive dimension ([Components](04b-parcalar.md#parcalar)). |
| fuel (meat) material / cladding material / coolant not selected | error | An unselected material would be built as void (no material). | Select all three materials. |
| undefined material for ...: ... | error | Reference to a deleted material. | Select or define the material. |

### `demet:`: assembly (`demet:demet_17x17`)

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| the map is empty | error | The assembly map has no cell. | Paint the map with the palette ([Assembly](04c-demet.md#demet)). |
| the map has ... rows but the size expects ... rows / row ... has ... characters but ... are expected | error | The size of a hand-written square map does not match `boyut`. | Make the numbers of rows/columns equal. |
| ... rings expected, the map has ... rows / ring ... (radius ...) expects ... items | error | A hexagonal map does not follow the ring layout: rings from outside to inside, 6k items in the ring of radius k, 1 at the center. | Paint the map again in the user interface or correct the ring lengths. |
| undefined letter in the map: '...' | error | A letter in the map has no entry in the key. | Add the letter to the key. |
| letter defined in the key but not used in the map: '...' | info | Extra key entry. | Delete it if not needed. |
| the outer diameter of pin '...' (...) is larger than the lattice pitch (...): the pin spills into the neighboring cell | error | OpenMC does not count this as an error; the lattice cell silently cuts the pin. | Increase the pitch or decrease the pin radii. |
| the pins do not fit into the duct: inner size of the duct ..., at least ... needed | error | The duct of a hexagonal assembly cuts the pins of the outer ring. | Increase the inner size of the duct or decrease the pitch. |
| a duct is built only in a hexagonal assembly; it is ignored | warning | A duct was given to a square assembly. | Remove the duct. |

### `kor`: Geometry page (templates)

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| no pin selected / no assembly selected / no plate-type fuel element selected | error | The main fill of the core type is empty. | Select the fill on the Geometry page ([Geometry](04d-geometri.md#geometri)). |
| the outer diameter of the pin (...) is larger than the cell pitch (...) | error | In a pin cell the pin does not fit into the cell. | Increase the cell pitch. |
| the core map is empty / undefined letter in the map: '...' | error | The full-core map is not painted, or the letter has no assembly. | Paint the map, define the letter. |
| the orientation of assembly '...' ('...') is the same as the core orientation: the assembly corners spill into the neighboring cell | error | In a hexagonal core the core lattice must be rotated by 90° with respect to the pin lattice. | If the assembly is `y`, the core orientation is `x` (or the other way round). |
| the assembly pitch (...) is smaller than the outer size of assembly '...' (...) | error | The core cell cuts the assembly. | Make the assembly pitch at least as large as the outer size of the assembly. |
| '...' is a square assembly; only a hexagonal assembly can be placed in a hexagonal core map | error | Lattice types are mixed. | Use a hexagonal assembly or switch to a square core type. |
| the drums enter the core / the drums stick out of the radial reflector / neighboring drums overlap | error | The drum placement is geometrically invalid; model building stops. | Change the center radius, the drum radius or the number of drums according to the numbers in the message. |
| the drum absorber ('...') contains no strong neutron absorber | warning | The absorber material has no B, Gd, Hf... | Choose an absorber such as B4C. |
| the drum core is 2D: no axial leakage, k-eff comes out too high | info | No height given. | Define an active height for a realistic drum worth. |
| number of drums 0: a plain radial reflector without control drums | info | No drums. | Enter the number of drums unless this is intended. |
| a spherical assembly needs at least one shell / shell radii must be in increasing order | error | Shells missing or out of order (entered only in JSON). | Sort the `kor.kabuklar` list from inside to outside. |
| the outer boundary of the spherical assembly is reflective: if you model a bare criticality assembly it must be vacuum | warning | A reflective boundary means an infinite medium. | Choose vacuum for critical spheres. |
| side boundary vacuum in a single cell/assembly model: leakage breaks the infinite lattice assumption | warning | A vacuum boundary in a model that should give k∞. | Choose reflective for k∞. |
| side boundary reflective and the map has more than one assembly type: infinite lattice equivalence holds only for identical, symmetric assemblies | warning | In a hexagonal full core the broken-line boundary is not a symmetry plane for a mixed map. | Use a radial reflector and a vacuum boundary. |
| in a single assembly with a duct the boundary is on the outer face of the duct: the gap (coolant) between assemblies is not in the model | warning | A single assembly ends at the outer face of its duct. | Use a hexagonal full core with one ring (`halka_sayisi` = 1). |
| a periodic boundary can only be used on planar boundaries (x/y plane pairs) | error | The side surface is a cylinder or a broken line. | Choose reflective or vacuum. |
| the ... boundary is periodic but the ... boundary is not: the periodic surface has no partner | error | Bottom/top periodicity on one face only; OpenMC stops before starting. | Choose reflective or vacuum for bottom/top. |
| the model is 2D: the ... boundary condition (...) is ignored / no height given: the model is taken as infinite in the axial direction (2D) | info | A 2D model has no axial boundary. | Define a height for axial leakage. |
| no radial reflector is built in core type '...': it is enabled in the file but ignored / unused fields are filled | warning / info | Fields left over from another core type. | Harmless; delete the field from the JSON to clean up. |
| unknown core type: ... | error | A hand-written `kor.tur` is invalid. | Write one of the valid types. |

### `kor/katman `: axial layers (`kor/katman 2 (su)`)

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| the layer height must be greater than zero | error | Layer height ≤ 0. | Enter a positive height. |
| undefined fill name: '...' | error | The fill is not the name of a pin, a plate-type fuel element, an assembly or a material. | Pick the fill from the list. |
| the same name is used in more than one layer: '...' | warning | Layer names become cell names; this causes confusion. | Give the layers different names. |
| letter '...' does not appear in the core map / undefined assembly/material name: '...' | warning / error | The layer-specific `anahtar` mapping does not match the map. | Correct the mapping (JSON only). |

Layer-related messages at core level appear at the `kor` location: "axial layers are enabled but no
layer is defined" (error), "no axial layer contains fissile material" (error), "the height field is
ignored while axial layers are enabled" (info), "control rod insertion is measured within the active
fuel range" (info).

### `ayarlar`: Run settings

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| number of particles / number of batches must be greater than zero | error | Value ≤ 0. | Enter a positive value ([Run settings](04f-hesap-ayarlari.md#hesap-ayarlari)). |
| inactive batches (...) must be fewer than total batches (...) | error | No active batch is left. | Increase the total batches or decrease the inactive batches. |
| very few inactive batches (...): the source distribution may not have converged | warning | Fewer than 5 inactive batches. | Use 20-50 inactive batches; more in a full core. |
| few active batches (...): the statistics stay weak | warning | Fewer than 20 active batches. | Increase the total batches. |
| Shannon entropy is off: whether the source distribution converged cannot be measured | warning | The entropy mesh is off. | Keep it on in an eigenvalue calculation. |
| the entropy mesh dimensions must be greater than zero | error | A mesh division is 0. | At least 1 division on each axis. |
| few particles per batch (...): source convergence may suffer | warning | Fewer than 1000 particles. | Use at least a few thousand particles. |
| an eigenvalue (k-eff) calculation needs fissile material: there is no fissile material in the geometry | error | OpenMC stops in the first batch ("No fission sites banked"). | For shielding set the calculation type to fixed source. |
| no tally is defined in a fixed source calculation: the run produces no result | error | A fixed source calculation has no k-eff; what is to be measured must be defined as a tally. | Add a tally. |
| inactive batches (...) are ignored in a fixed source calculation / Shannon entropy is not used in a fixed source calculation / kinetics parameters ... are ignored | info | These fields make sense only in an eigenvalue calculation. | Nothing to do. |

### `kaynak`: source definition

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| the source strength must be greater than zero | error | Strength ≤ 0. | Enter a positive strength [1/s]. |
| unknown particle type: ... | error | A hand-written particle type is invalid. | `neutron` or `photon`. |
| a photon source makes no sense in an eigenvalue (k-eff) calculation | error | Photons do not carry the fission chain. | Set the calculation type to fixed source. |
| photon source selected but the library has no photon data | error | `cross_sections.xml` has no photon entries. | Install a library that contains photon data. |
| source energy ..., data ceiling ... | error | The source energy exceeds the upper data limit of a nuclide in the model; OpenMC stops during the run. | Lower the source energy. |
| point source z = ... is outside the model | error | Particles that start outside the geometry are lost at once. | Move the position into the model. |
| a box source needs fissile material: there is no fissile material in the geometry | error | A box source is sampled only in fissile regions. | Use a point source. |
| in a fixed source calculation a box source is sampled with the 'fissionable regions only' constraint | warning | The non-fissile part of the box stays empty. | Choose a point source for an external source. |
| the source strength (...) is ignored in an eigenvalue calculation / the energy spectrum ... is only an initial guess / the angular distribution is also only an initial guess | info | In an eigenvalue calculation the result is normalized to the fission source; the spectrum changes during the inactive batches. | Nothing to do. |

### `tally:`: user tallies (`tally:aki`)

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| at least one score must be selected | error | The tally has no score. | Select a score or a ready-made set. |
| '...' is not among the known scores | warning | OpenMC does not check score names until the run; the list is kept by hand. | Check the spelling; if it is a new OpenMC score the warning may be a false alarm. |

### `guc dagilimi` and `guc_dagilimi`: power distribution

Both spellings lead to Run settings (`guc_dagilimi` comes from the axial layer check).

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| no target pin selected / target pin undefined: ... | error | The power distribution is on but has no target. | Select the target pin. |
| '...' is not repeated in an assembly (core type: 'Fuel pin (pin cell)') | error | The distribution is calculated over repeated cell instances. | Build an assembly. |
| pin '...' is not used in the model: a power distribution can only be calculated for a pin that is in the geometry | error | The target pin is in no map. | Select a fuel pin that appears in the geometry. |
| the material of the selected region ('...') does not look fissile | warning | Cladding or coolant was selected. | Select the fuel region (usually region 1). |
| '...' is not an energy score | warning | `fission` gives the number of fissions, not the power. | Use `kappa-fission`. |
| the model is 2D: F_q cannot be calculated, only F_ΔH is given | info | F_q depends on the axial shape. | Define an active height. |
| only ... axial bins: F_q comes out too small | warning | Coarse bins average out the peak. | Use 10-20 bins. |
| the axial bin boundaries are not aligned with the layer boundaries: F_q may be inflated by a few % | warning | One bin falls into both a layer with the pin and one without it. | Choose the number of bins according to the layers. |
| the total power must be greater than zero / total power given but the model is 2D: linear power [W/cm] cannot be calculated | error / warning | The absolute power input is inconsistent. | Enter a positive power; a 3D model for W/cm. |
| F_ΔH covers only pin '...': the model also has other pin types that contain fuel | warning | The hottest pin may be of a type that is not in the target list. | Add every fuel pin type to the target list. |
| the fissile range is ... cm but pin '...' exists only over ... cm | warning | The power of fissile layers such as a blanket is shared among the target pins. | Read the W/cm result accordingly. |

### `tukenme` and `tukenme/`: depletion (`tukenme/uo2`)

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| depletion requires an eigenvalue (k-eff) calculation | error | There is no fixed source depletion (activation). | Set the calculation type to eigenvalue. |
| chain file missing / empty / incomplete: no closing tag | error | The depletion chain was not downloaded or the download was cut. | `./veri_indir.sh --yalniz-zincir`. |
| tracked nuclide not in the chain: '...' | error | Typo or a nuclide that is not in the chain. | Pick it with the nuclide selector ([Depletion](04i-tukenme.md#tukenme)). |
| ... chain selected but the model looks like a ... spectrum | warning | The thermal/fast chain does not match the spectrum of the model. | Leave the chain on "automatic". |
| simplified CASL chain: 228 nuclides (full chain 3820) | info | A preliminary-review chain. | Confirm the result with the full chain. |
| the power density must be greater than zero [W/gHM] / power density ... W/gHM is unusual | error / warning | The unit is W/gHM, not absolute power (typical PWR 38-40). | Enter the value in W/gHM. |
| at least one time step is needed / time steps must be greater than zero | error | The step list is empty or ≤ 0. | Enter the steps. |
| first step ... days: the Xe-135 equilibrium (~2 days) is squeezed into one step | warning | A long first step hides the xenon drop. | Keep the first steps short (0.5 and 1.5 days). |
| little active statistics (... particles × ... batches) | warning | Noise accumulates from step to step. | Particles × active batches ≥ 100 000. |
| no burnable (fissile) material in the model / volumes could not be calculated | error | There is no fuel to burn in the geometry, or the volume calculation failed. | Put the fuel into the geometry; read the reason in the message. |
| volume cannot be calculated: ... | error | A wrong volume distorts the burnup rate by the same factor and leaves no trace in k-eff. | Correct the geometry according to the details in the message. |
| the volume of '...' will be calculated stochastically | warning | A truncated position or a truncated pin; the analytic volume is not exact. | Read the uncertainty from the report. |
| in pin-by-pin depletion the instance volume is not exact | error | At truncated positions the instance volume is unknown. | Turn pin-by-pin depletion off or remove the truncated positions. |
| burnable absorber '...' does not take part in depletion | warning | Its volume cannot be calculated analytically; the material stays fresh. | Put the poison into a pin region with an exact volume. |
| undefined extra material: '...' | error | A deleted name in `tukenme.ek_malzemeler`. | Correct the list. |
| pin-by-pin depletion is on | info | Every cell becomes a separate material; memory and time grow. | No problem if you turned it on knowingly. |

The previous result on the Depletion page is also a kind of finding: "**Outdated result** (...): the
model has changed since that run" is written in red; the numbers shown do not belong to this model,
run again.

### `geometri:`: advanced geometry tree (`geometri:kok/halkalar/0/yerlesimler/1`)

The location is the path of the node in the tree; the list reads it as "geometry: root › ring 1 › ...".
This location code has **no automatic page switch**: follow the path in the tree on the Geometry page
(advanced view) ([Advanced geometry](04e-geometri-gelismis.md#geometri-gelismis)).

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| Undefined name / Undefined material / Undefined component: '...' | error | A slot refers to a deleted or misspelled name. | Correct the name or add the definition. |
| Ambiguous name '...': it exists in both ... sections | error | The same name in two library sections. | Rename one of them. |
| Cycle: part '...' contains itself | error | A part is used inside itself. | Break the cycle. |
| Undefined letter in the map / the map has ... rows; the size expects ... / the hexagonal map expects ... rings | error | The lattice map does not match its size. | Paint the map again. |
| The 'dis' slot of the lattice is mandatory | error | No fill for the outside of the lattice and the "." positions. | Select a material for `dis`. |
| A non-root container needs a 'dis' slot / The root container cannot have 'dis' | error | The container slots break the rule. | Give an outer fill to a non-root container; remove it from the root. |
| The outer section of the ring does not enclose the previous boundary / The ring thickness must be greater than zero | error | The rings are not nested. | Increase the thickness or the outer section. |
| hole '...' sticks out of its region / out of the inner boundary of the region / out of the lattice position cell | error | The placement hole does not fit into its owner region. | Change the center radius or the hole size. |
| holes '...' and '...' overlap | error | Overlapping cells produce lost particles. | Separate the placements. |
| Hexagonal assembly '...' in a hexagonal lattice element with the same orientation | error | The assembly does not fit into the element. | The assembly orientation must be perpendicular to the lattice orientation. |
| plate-type fuel element '...' does not fill its region | error | The point in between stays undefined (lost particle). | Put the plate-type fuel element into a position equal to its size. |
| An axial stack cannot be built in a 2D model / The total of a non-root axial stack is not equal to the model height | error | The axial stack is inconsistent with the height. | Give the root height or make the layers equal. |
| boundary ... on face '...' cannot be used on this outer boundary / boundary ... cannot be periodic | error | A periodic boundary is valid only on a rectangular/hexagonal outer boundary and on a pair of opposite faces. | Choose reflective or vacuum. |
| Point probe: ... | error | Overlapping or undefined regions were found at sample points. | Fill the region with a material; remove the overlap. |
| ... truncated positions/components are clipped by the parent region / ... truncated pins | warning | A lattice element or a pin is cut by the parent boundary. | Accept it if intended: the volume falls back to stochastic, and the power map marks it "truncated". |
| Void region inside the root / control drum in a 2D model | warning | Neutrons do not interact in a void; in 2D there is no axial leakage. | Correct it unless intended. |
| two inline subtrees with the same content | warning | Distribcell and depletion instance counting are split. | Turn the subtree into a part and use it in both places. |
| ... lattice position completely hidden (under a hole) / 0 cm layer skipped | info | Harmless. | You can write "." in the map. |
| Nesting depth more than ... levels / more than ... holes in one region | warning | Tracking and cell search slow down. | Simplify the tree. |

### `dogrulama`: the model check itself

| Finding (short text) | Level | Cause | Fix |
|---|---|---|---|
| error during the model check: ... | error | A check stopped with an unexpected exception (usually a corrupt JSON field). | Read the details in the log file; opening the file in the user interface and saving it completes the fields. If it persists, report it with the log. |

### `uygunluk:`: conformity-check findings

The location of conformity findings has the form `uygunluk:<rule>` (`uygunluk:K1`,
`uygunluk:K2-parcacik`). They appear not in the findings list but in the Conformity panel on the Run
page; look up the rule identifier in [9.3 Conformity rules](#uygunluk-kurallari). In the panel a
double click goes to Run settings for K1/K2, to Geometry for K3 and to Materials for `K4-sicaklik`.

<a id="uygunluk-kurallari"></a>
## 9.3 Conformity rules (K1-K16)

The conformity check is **not a certification**: it produces the evidence that standards and good
practice would ask for and makes the gaps visible (see [Conformity check](07-uygunluk.md#uygunluk-denetimi)
and [What it proves and what it does not](07-uygunluk.md#ne-kanitlar)). The sources of the rules are
in [docs/STANDARTLAR.md](../../STANDARTLAR.md) §3.

**Statuses.** Every rule produces a row also when it passes:

| Status | Meaning |
|---|---|
| passed | The rule was checked and met. |
| not met | The rule was checked and not met; the level can be error, warning or info. |
| not applicable | The data or threshold needed for the check is missing (e.g. no statepoint, no threshold entered). It does not count as a failure; with `--siki` it does. |
| note | An information note; no met/not met judgement. |

**Labels** (the kind of source): **good practice** (not a clause of a standard), **standard** (based on
an explicit clause of a standard/guide), **project criterion** (the project's own criterion),
**user-defined limit** (the threshold comes from the user/facility; no default).

**Profiles:** A Monte Carlo good practice (K1, K2, K3), B criticality safety (K6, K6-AOA, K8-K14), C
reactor core design (K7, K7-SDM, K7-F, K16), D reporting (K4, K5). The profiles are selected in the
Conformity panel on the Run page and written to the `calistirma.uygunluk_profilleri` field (details:
[Profiles](07-uygunluk.md#profiller)).

**Thresholds.** No threshold without a source is built into the tool. Thresholds such as
`sigma_hedef`, `aktif_asgari`, `F_dH_siniri`, `F_q_siniri`, `sdm_siniri_pcm` have **no** default; the
sub-rules that depend on them say "not applicable". This is not an error. Today a threshold can only
be given from Python (`cekirdek/uygunluk_denetimi/profiller.py`: `uyarla`, `dosyadan_uyarla`); the
user interface has no field for it. Some inputs of profiles C and B are read from a
`uygunluk_girdisi.json` file placed by hand in the run directory (keys `kor` and `uygulama`).

### Profile A: Monte Carlo good practice

<a id="kural-k1"></a>
#### K1: Source convergence (Shannon entropy plateau)

- **Label:** good practice. **Source:** F.B. Brown, LA-UR-09-03136 (2009) §II; NUREG/CR-6698 §2.4
  footnote (convergence is a judgement of the user).
- **What it checks:** the second half of the inactive period is split in two; does the drift between
  the entropy means of the two halves exceed twice the scatter (σ) of the entropy in the active
  batches.
- **Typical findings:**
  - "The source distribution is still drifting at the end of the inactive period (drift ..., active
    scatter σ = ...). Increase the number of inactive batches; k-eff may be biased." → **warning**, not
    met.
  - "Shannon entropy is off: source convergence cannot be shown." → warning.
  - "the number of inactive batches (...) is too small to judge source convergence" or "entropy is
    constant; could not be evaluated" → not applicable.
  - "Fixed source run: k-eff and source convergence are undefined." / "No statepoint in the run
    directory." → not applicable.
- **Fix:** step-by-step recipe below: [K1: source not converged](#yakinsamadi).

<a id="kural-k2"></a>
#### K2: Statistical adequacy

- **Label:** good practice; the thresholds do not come from a standard (profile value). Sub-identifiers:
- `K2-sigma`: σ_k ≤ `sigma_hedef`. No default target → "σ target not defined; k = ..., σ = ... (1σ)
  not compared." (not applicable). If a target is given and exceeded, "σ_k = ... is above the target
  (...)." (warning) → increase the active batches or the particles per batch.
- `K2-parcacik`: particles per batch. Below 1000 is a **warning** ("bias is expected in k-eff and in
  local tallies", Brown 2009 §III.C); between 1000 and 5000 a **note** ("at least 5000 is recommended
  for a long production run", Brown 2009 §V).
- `K2-aktif`: lower limit on active batches. The source gives no number, so there is no default →
  not applicable.
- `K2-ilinti`: if the lag-1 autocorrelation of the k values of the active batches exceeds 2/√N, a
  **note**: the reported σ ignores the correlation between batches and underestimates the true
  uncertainty. Fix: make a few runs with independent seeds and compare the scatter
  ([Statistics](06-sonuclar.md#istatistik)).

<a id="kural-k3"></a>
#### K3: Lost particles = 0

- **Label:** good practice (OpenMC). **What it checks:** the `kosu.log` and `particle_*.h5` files;
  the allowed loss `kayip_azami` = 0.
- **Typical finding:** "... lost particles (allowed 0). ..." → **error**. Cause: a gap in the geometry
  (a point covered by no cell) or overlapping cells. Fix: check the cross-section plots and the boundary
  conditions on the Geometry page; in advanced geometry run a point probe with "Probe".
- `K3-hata`: error messages OpenMC wrote to its output (error). `K3-uyari`: OpenMC warnings other than
  lost particles (note; check in the log whether they affect the result).
- "No run log (kosu.log)" → not applicable: the run was not made with this application; run it again.

### Profile B: Criticality safety

The method source is NUREG/CR-6698 (2001) and, in this tool, [docs/VV.md](../../VV.md). The rules of B
other than K6 need a **validation (V&V) set summary**. The Conformity panel, the report annex and the
`openmc-arayuz-kosu uygunluk` command build this summary automatically from the benchmark set of the
repository (`kume.uygulama_ozeti`): the USL is calculated only from cases with the same fissile
species, form and spectrum (and, for U-235, enrichment class) as the application; if the matching
subset has fewer than 10 cases, K6 says "no USL for this application" (see
[USL could not be calculated](#usl-hesaplanamadi)).

<a id="kural-k6"></a>
#### K6: Acceptance condition k + 2σ < USL

- **Label:** standard. **Source:** NUREG/CR-6698 eqs. (1), (35), (36). The inequality is strict; the
  factor `kabul_carpani` = 2.
- **Typical findings:** "k + 2σ = ..., USL = ...: the acceptance condition is not met." → **error** (the
  system does not meet the subcriticality criterion; change the design or the control parameters).
  "USL could not be calculated (...). k = ... was not compared with a subcriticality limit; this result
  is not evidence of criticality safety." → not applicable. When it passes: "k + 2σ = ... < USL = ...
  (subset: ...; n = ...; method: ...)". "No eigenvalue run result" → not
  applicable.

<a id="kural-k6-aoa"></a>
#### K6-AOA: Area of applicability (categorical)

- **Label:** standard (NUREG/CR-6698 §2.5, Table 2.3). **What it checks:** whether the fissile element,
  physical form, reflector and spectrum class of the application are present in the validation set.
- **Typical finding:** "...: application '...', the validation set contains only ...: outside the area
  of applicability." → warning. Fix: add benchmark experiments with this property to the set. If the
  properties of the application are not given, not applicable.

<a id="kural-k8"></a>
#### K8: A positive bias is not credited

- **Label:** standard (eq. 8). "A positive bias (...) is credited in the USL." → error; if the bias is
  > 0 it must be taken as 0 in the USL calculation. The tool applies this itself; this finding appears
  only when an external summary is given.

<a id="kural-k9"></a>
#### K9: k_calc / k_exp normalization

- **Label:** standard (eq. 9). "Cases with benchmark k_exp ≠ 1 are not normalized with k_calc / k_exp."
  → warning. Fix: k_norm = k_calc / k_exp and σ = √(σ_calc² + σ_exp²).

<a id="kural-k10"></a>
#### K10: Number of cases and confidence level

- **Label:** standard (§2.2, Table 2.2). "The set has ... cases (< 10): technical justification
  needed." → warning; add independent benchmark experiments to the set.
- `K10-guven`: in the non-parametric method a warning if the confidence β is not reported; an
  **error** if a USL is given while β ≤ 40 % ("more data needed, the USL cannot be calculated").

<a id="kural-k11"></a>
#### K11: Margin of subcriticality ΔSM ≥ 0.02

- **Label:** standard (§2.4.5). Default ΔSM = 0.05 (from NUREG-1520 / NUREG-1718; the value is **not
  verified**). "ΔSM = ... is below the absolute lower limit (0.02): the profile is invalid." → error;
  make ΔSM at least 0.02 and write its justification. The justification of the chosen value belongs
  to the user organization.

<a id="kural-k12"></a>
#### K12: Extrapolation beyond the validation range

- **Label:** standard (§5). Are the numeric AOA parameters of the application (enrichment, H/X, EALF)
  within the range of the set. With the tolerance limit method a value out of range is an **error**
  (it cannot be used for extrapolation); exceeding by more than 10 % is a **warning** ("the validation
  set should be extended"); with ΔAOA = 0 a small excess is a warning ("a ΔAOA margin and its
  justification should be entered").
- `K12-h_x`: "The H/X ratio of the application could not be derived (in a heterogeneous lattice the
  moderator is a separate material)..." → warning; the set has an H/X range but the application was
  not compared. Fix: calculate H/X with the cell volumes and enter it in the conformity input.

<a id="kural-k13"></a>
#### K13: Trend and normality

- **Label:** standard (§2.4.2-2.4.3).
- `K13-normallik`: "The data are not normal (...) but method '...' was used." → error; the
  non-parametric method is mandatory. If the result is not reported, a warning.
- `K13-egilim`: "There is a significant trend (...) but the tolerance limit method was used." →
  warning; use the tolerance band method. Without a trend analysis, a warning.

<a id="kural-k14"></a>
#### K14: Independence between experiments

- **Label:** good practice (NEA/NSC/WPNCS/DOC(2013)7, UACSA). "Several cases from the same experimental
  series: ... The cases are not independent; the statistical confidence may be overstated." → note.
  Example: LEU-SOL-THERM-002 cases 1 and 2 in the V&V set.

### Profile C: Reactor core design

The inputs are read from the `kor` key of the `uygunluk_girdisi.json` file in the run directory
(`katsayilar`, `kapatma_marji`, `faktorler`, `dogrulama`); if the power peaking factors are not given
they are read from the statepoint. Today the coefficients of the Analysis tab are **not written
automatically** to this file.

<a id="kural-k7"></a>
#### K7: Sign of the reactivity coefficients (GDC 11)

- **Label:** standard (NUREG-0800 §4.3 Rev. 3 II.2, GDC 11). The rule only tests the expected sign; it
  does **not** say "GDC 11 is met" (the judgement on the net feedback is a design analysis).
  Significance `anlamlilik_carpani` = 2 (project criterion: |slope| > 2σ).
- Sub-identifiers `K7-guc`, `K7-yakit_sicaklik`, `K7-sogutucu_sicaklik`, `K7-void_orani`:
  - negative → passed;
  - `K7-guc` positive → **error** (contradicts the expected sign);
  - Doppler (`K7-yakit_sicaklik`) positive → warning (unusual);
  - a positive MTC or void coefficient → **note**: not an error by itself (SRP 4.3 does not exclude a
    positive MTC); it must be evaluated in a transient analysis;
  - |slope| ≤ 2σ → sign could not be determined (warning for the power coefficient, info for the
    others): widen the sweep range or increase the statistics;
  - no σ given → not applicable.
- `K7-guc` also appears as the note "No net power coefficient given": GDC 11 cannot be judged from the
  component coefficients alone.
- If no coefficient is given at all, "No reactivity coefficient result given." (not applicable) → do a
  sweep in the Analysis tab and enter the result in `uygunluk_girdisi.json`.

<a id="kural-k7-sdm"></a>
#### K7-SDM: Shutdown margin (most reactive rod stuck out)

- **Label:** user-defined limit (NUREG-0800 §4.3; GDC 26/27). The limit `sdm_siniri_pcm` is specific
  to the facility; **there is no default** → "no limit entered, could not be compared" (not
  applicable). Here pcm = Δρ × 10⁵.
- `K7-SDM-N1`: the margin was not calculated with the most reactive rod stuck out (N−1) → warning.
  `K7-SDM-sigma`: no uncertainty given for the margin → warning. Below the limit is an error, within
  2σ of it a warning.

<a id="kural-k7-f"></a>
#### K7-F: Power peaking factors F_ΔH / F_q

- **Label:** user-defined limit. `K7-FdH` and `K7-Fq` compare the value with `F_dH_siniri` /
  `F_q_siniri`; without a limit, "no limit entered, could not be compared (facility specific; no
  default)" (not applicable). Above the limit is an error, within 2σ of the limit a warning. "No power
  distribution result" → turn the power distribution on and repeat the run.

<a id="kural-k16"></a>
#### K16: Reference for core method validation

- **Label:** standard (ANSI/ANS-19.3-2022; ISO 18075:2018, clause details not verified). "It is not
  stated against which benchmarks the core calculation method was validated, nor its range of
  application." → info. Fix: write the references (an IRPhEP case, a code-to-code comparison) into the
  `kor.dogrulama` list in `uygunluk_girdisi.json`.

### Profile D: Reporting

<a id="kural-k4"></a>
#### K4: Data traceability

- **Label:** standard (ANSI/ANS-10.4-2008 (R2021); NUREG/CR-6698 §2.3). If the reproducibility fields
  of the report (OpenMC version, library, chain sha256, seed...) are unknown, a warning: run again with
  this application; the version and the library are read from `kosu.log`.
- `K4-sicaklik`: "Material with undefined temperature: ..." → warning; enter the temperature on the
  Materials page.

<a id="kural-k5"></a>
#### K5: Uncertainty and unit statement

- **Label:** standard (JCGM 100:2008 §7.2.2, §7.2.3, §7.2.6; BIPM SI Brochure). The `rapor.html` in the
  run directory is checked; without a report, not applicable ("Create the report and repeat the
  check"). With more than one `.html` it is ambiguous which one is the report: save the report as
  `rapor.html`.
- `K5-etiket`: it is not stated that values given with "±" are 1σ standard uncertainties (warning).
- `K5-rakam`: the uncertainty has more than 2 significant digits (warning). Example of the correct
  form: 1.1822 ± 0.0029 (1σ).
- `K5-yuvarlama`: the value is not rounded to the same decimal place as its uncertainty (warning).
- `K5-pcm`: "pcm" is used but its definition (Δk × 10⁵ or Δρ × 10⁵) is not written in that section or
  at the beginning of the document (warning).
- `K5-SI`: a non-SI unit (inch, ft, psi, BTU, lbm, °F) → warning.

<a id="yakinsamadi"></a>
### K1: "source not converged", step by step

If the K1 row of the Conformity panel says "The source distribution is still drifting at the end of the
inactive period ...":

1. **What it means:** when the inactive batches end, the spatial distribution of the fission source has
   not settled yet; the k-eff and tallies collected in the active batches are affected by this
   unsettled source. It is usually not possible to notice this by looking at k-eff itself.
2. **Look at the entropy plot:** if, in the convergence plot on the Run page, the entropy still has a
   slope (rising or falling) at the end of the inactive period, the rule is right.
3. **Increase the inactive batches:** in Run settings increase **Inactive batches** so that it is larger
   than the batch at which the entropy flattens (typical: 20-50 in a single assembly, 100 and more in a
   full core). Increase **Total batches** by the same amount; otherwise the active batches decrease.
4. **Check the entropy mesh:** if the **Entropy mesh** is too coarse (e.g. 1 × 1 × 1) the drift is not
   visible; in a 3D model use divisions in the z direction as well.
5. **Number of particles:** with few particles per batch (`K2-parcacik`) the entropy is noisy; use a few
   thousand particles.
6. **Run again** and check that the K1 row in the panel says "passed".

Detailed interpretation: [Source convergence](06-sonuclar.md#kaynak-yakinsamasi).

<a id="usl-hesaplanamadi"></a>
### "USL could not be calculated", step by step

If, with profile B selected, the panel (and the report annex) says "USL could not be calculated: ...":

1. **This is not a model error.** The USL (upper subcritical limit) comes from the validation of the
   calculation method against benchmark experiments. When the limit cannot be calculated, the k value of
   your run has **not been compared** with a subcriticality limit; the result cannot be used as evidence
   of criticality safety, but the calculation itself is not wrong.
2. **Read the reason:** the reason in parentheses is one of these:
   - "no USL for this application (AOA could not be determined)": the neutron spectrum (EALF tally
     `vv_ealf`) or the fissile species/form could not be derived; the card offers to add the EALF
     tally;
   - "no USL for this application (outside the AOA): the set has n cases matching the subset (...)":
     fewer than 10 independent benchmarks share the fissile species, form, spectrum (and, for U-235,
     the enrichment class) (NUREG/CR-6698 §2.2, Table 2.3);
   - "the data are not normal and the non-parametric confidence β ≤ 40 %: more benchmark data needed"
     (Table 2.2).
3. **Which AOAs have a USL:** see the table "Which subset the tool uses" in
   [docs/VV.md](../../VV.md). In today's repository set the largest matching subset has 5 cases, so
   **no application gets a USL** (for an LWR/LEU lattice the only matching case is LCT-008). Details:
   [Verification and validation](07-uygunluk.md#vv).
4. **Check with a V&V summary (Python):** see the subset of your application and the reason:

   ```bash
   python -c "from cekirdek.vv import kume; import json; print(kume.uygulama_ozeti(json.load(open('ornekler/pwr_17x17.json')), uygulama={'tayf': 'termal'})[0].usl_neden)"
   ```

   The panel, the report annex and `uygunluk --profil B` use the same path (`kume.uygulama_ozeti`).
5. **If the set is not sufficient:** independent benchmark experiments representing your application
   (e.g. LEU-COMP-THERM series) have to be modeled from the ICSBEP handbook and added to the set
   ([docs/STANDARTLAR.md](../../STANDARTLAR.md) §5). Lowering the minimum number of cases with a
   technical justification is the decision of the user organization; K10 still warns.

<a id="kurulum-sorunlari"></a>
## 9.4 Installation and environment problems

Source: [KURULUM.md](../../../KURULUM.md) "frequent problems" and `calistir.sh`.

| Symptom | Cause | Fix |
|---|---|---|
| `HATA: openmc PATH'te yok` (openmc is not in PATH) | The conda environment is not active. | `conda activate openmc-env` |
| `openmc Python paketi bulunamadi` / `PySide6 bulunamadi` (package not found) | The environment is incomplete. | Rebuild the environment with `conda env create -f environment.yml`. |
| `OPENMC_CROSS_SECTIONS ayarli degil` (not set; warning) and a `veri kutuphanesi` error in the model check | The nuclear data were not downloaded or no new terminal was opened. | `./veri_indir.sh --bashrc`, then `source ~/.bashrc` ([Nuclear data](01-kurulum.md#nukleer-veri)). |
| `Grafik oturum yok (DISPLAY/WAYLAND_DISPLAY bos)` (no graphical session) | You are connected over SSH or WSL has no graphics. | Open it in a desktop session; for WSL, Windows 11 + `wsl --update`. Working without the user interface: [Terminal](08-terminal.md#terminal). |
| The Depletion page says "chain file missing/incomplete" | The chain was not downloaded or the download was cut (once it was measured to stop silently at 13 %). | `./veri_indir.sh --yalniz-zincir` |
| `conda env create` takes very long | Old solver. | `conda config --set solver libmamba` or `mamba env create -f environment.yml` |
| Some tests are skipped (marked `veri`) | No `OPENMC_CROSS_SECTIONS`. | Expected behavior; they run once the data are downloaded. |
| The application closed with an error code | An uncaught error. | Open the log file printed in the terminal (`~/.local/state/openmc_arayuz/openmc_arayuz.log`) and report the error with this file. |
| Where were the results written? | — | In a saved project, the `kosu` directory next to the project; in an unsaved project, under `~/openmc_kosular`. The Run page shows the full path. |

The `calistir.sh` messages above are printed in Turkish ASCII by the shell script; the English meaning
is given in parentheses.

<a id="kosu-sorunlari"></a>
## 9.5 Run problems

| Symptom | Cause | Fix |
|---|---|---|
| RUN button disabled: "The model check has ... errors; fix them first." | There are findings at error level. | Click the badge, select the finding and fix it on the page concerned ([9.2](#bulgu-turleri)). |
| RUN button disabled: "The geometry preview has not been plotted yet. Plot first, run later..." | The preview is still being plotted or could not be plotted. | Wait; if it could not be plotted see the next row ([Plot first, run later](06-sonuclar.md#once-ciz)). |
| "Preview failed: ..." / "Geometry could not be built" in the preview | The model could not be converted to an OpenMC geometry (undefined name, a component that does not fit, missing fill). | Read the text in the message; usually the same issue is listed as an error in the findings list. |
| "The run of the previous project is still running in the background..." | The old run had not finished when another project was opened. | End the old run with Stop. |
| Lost particles at the end of a run (K3 error) | A gap or overlapping cells in the geometry. | Inspect the cross sections, check the boundary conditions; in advanced geometry use "Probe". |
| The run stops with a temperature error | A material temperature is outside the data range. Neutron data cover 250-2500 K, water S(α,β) only 284-800 K. | Keep the temperature in range; check the end value of a temperature sweep ([Known pitfalls](06-sonuclar.md#tuzaklar)). |
| Warning: "Can be run. ... warnings" | Findings at warning level. | Read the list; they may affect the result. |
| k-eff very different from what you expect | Common causes: missing S(α,β), vacuum side boundary (k-eff instead of k∞), a 2D model, the enrichment shortcut above 5 %. | Read the warnings in the findings list; [Interpreting results](06-sonuclar.md#sonuclar). |
| F_ΔH larger than expected | With little statistics F_ΔH is biased upward (it is a maximum). | Increase the number of particles; Normal or Accurate preset. |
| Red "Outdated result (...): the model has changed since that run" on the Depletion page | The result shown does not belong to the current model. | Run again ([Depletion](04i-tukenme.md#tukenme)). |
| "Incomplete run (...): ... / ... steps completed" | Depletion was stopped or is still running. | Run again for a complete result (no restart from where it stopped). |
| "Result of the previous run (...). The run has no model record..." | No `tukenme_spec.json` in the run directory. | It cannot be verified that the result belongs to this model; run again if unsure. |
| The Conformity panel says "Could not be checked" | `uygunluk_girdisi.json` is corrupt or unreadable. | Fix the file as JSON or delete it; details in the log. |
| Many "not applicable" rows in the conformity check | No threshold or input (see "Thresholds" in 9.3). | Expected behavior; without `--siki` they do not count as failures. |
| Exit code 1 / 3 of `openmc-arayuz-kosu uygunluk` in the terminal | 1: there is an error finding; 3: with `--siki` some rule could not be evaluated; 2: usage error. | Read the list in the output ([Terminal](08-terminal.md#terminal)). |

The same check from the terminal:

```bash
openmc-arayuz-kosu uygunluk kosu/ --profil A,D
openmc-arayuz-kosu uygunluk kosu/ --profil A,B,C,D --siki
```
