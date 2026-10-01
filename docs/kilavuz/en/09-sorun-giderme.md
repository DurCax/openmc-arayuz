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

