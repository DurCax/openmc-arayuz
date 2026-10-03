<a id="tukenme-bolme"></a>
### 4.9.2 Depletion region subdivision: radial rings and axial slices

The **Region subdivision** card on the **Depletion** page splits pins into radial **rings** and axial
layers into **slices**; every piece burns as its own depletion material (the equivalent of Serpent's
`div` command). Why: a single-material pin burns with one average composition. In a pin with a
burnable absorber (Gd, Er) the neutron-absorbing outer shell burns first and shields the interior
(**self-shielding**); an average composition cannot see this, so the Gd depletion rate and the
k(t) curve come out wrong. Subdivision also makes the radial distribution of pin power over
burnup realistic.

The subdivision is applied **at the spec level**: rings go into the pin's `bolgeler` list (same
material, new radii), slices go into `kor.eksenel.bolgeler`, and **pin-by-pin burnup** is switched
on automatically (the pieces burn separately only that way). The geometry builder, the analytic
volumes, the script generator and pin power ([K3](04i-tukenme.md#tukenme)) therefore follow the
same path unchanged. Only the `tukenme.bolme` key stays in your file; the model record written to
the run directory is that plain model (the staleness check counts the subdivision as **physics**).

| Field | Meaning | Unit | Typical range | Common misuse | Spec key |
|---|---|---|---|---|---|
| **Subdivide depletion regions (rings / axial slices)** | Master switch. While off, `bolme` is absent from the file (old projects do not change on a round trip). | — | off | Interpreting a single-instance model's result without comparing against the undivided one | `tukenme.bolme` |
| **Pin types** | Pin types to subdivide (with a burnable region, cylindrical, not a control rod). In a checked pin the **burnable** (fissile or Gd/Er/B poison) regions are split; cladding, gap and water are not. | — | the Gd pin | Splitting a control rod (rejected: the absorber region depends on insertion) | `tukenme.bolme.cubuklar[].cubuk` |
| **Ring count** | How many rings the region is split into (1 = no subdivision). | rings | Gd pin: 3–6 | More than 20 (rejected); more rings cost time and memory | `tukenme.bolme.cubuklar[].halka` |
| **Ring type** | **Equal volume** (default, recommended start for Gd), **equal thickness** (for comparison) or **thinning outward** (geometric). See below. | — | equal volume | Choosing equal thickness and missing that the outer ring carries most of the power | `tukenme.bolme.cubuklar[].tur` (`esit_hacim` \| `esit_kalinlik` \| `dista_incelen`) |
| **Thinning ratio** | Only for the thinning type: each ring is this fraction as thick as the one inside it. An engineering choice, not a measured threshold. | — | 0.6 (0.2–0.95) | A very small ratio: the outer ring becomes numerically very thin | `tukenme.bolme.cubuklar[].oran` |
| **Axial slices** | Axial layers containing a burnable pin or plate are split into this many equal slices (h/n). Needs a 3D model (height or axial layers). | slices | 1–10 | Asking for slices in a 2D model (rejected) | `tukenme.bolme.eksenel.dilim` |

**Ring types** (r_in ≤ r ≤ r_out, n rings, k = 1 … n; the last radius is exactly r_out):

    equal volume      r_k² = r_in² + (k/n) (r_out² − r_in²)        every ring has the same area
    equal thickness   r_k  = r_in  + (k/n) (r_out  − r_in)          large-volume rings on the outside
    thinning outward  geometric thicknesses: t_(k+1) = ratio · t_k  tightest outer ring for n ≥ 4

In a Gd pin the absorption is strong at the surface, so the outer ring dominates power and burnup
(K3 review). **Equal-volume** rings already thin outward and are a good starting point (the Gd pin is split similarly in Serpent `div` and CASMO practice; an observation of
practice). "Thinning outward" gives an outer ring thinner than equal volume only for **n ≥ 4** rings (ratio 0.6,
r_in = 0: n = 2 → outer-ring radius ratio 0.375, equal volume 0.293, i.e. THICKER; n = 3 → 0.184 (same); n = 4 →
0.099 (0.134); n = 5 → 0.056 (0.106)). Compare the outer-ring thickness with the Gd-157 mean free path (~0.09 mm
at 0.025 eV; in 5 equal-volume rings the outer ring is ~43 µm, in 8 rings ~26 µm). The ring limit (20) and the
slice limit (50) are **interface limits, not physical thresholds**. Check on a small model that k(t) and the Gd curve converge as you add rings
([5.20 Lesson](05d-ders-tukenme-bolme.md#ders-tukenme-bolme)).

**Volume conservation (analytic).** The ring areas are π(r_k² − r_(k−1)²), so they sum to π(r_out² −
r_in²); the card shows this as **Sum of ring volumes equals the analytic volume (largest relative
deviation …)** (floating-point level, ~10⁻¹⁶; acceptance criterion 10⁻⁹). Depletion preparation
also computes every instance's volume from its own cell area × layer height and compares the sum
with the analytic volume to 10⁻⁹; if it does not match, the run does not start.

**Cost.** Every piece is a separate material: the card's summary states a number like **Separate
depletion materials: 264 → 1056**. Time and memory grow with it; in a large core subdivide only the
Gd pins. Subdivision is **not supported in advanced (tree) mode**.

**Consistency with pin power.** The power tally targets **all** fuel rings of the subdivided pin and
sums ring tallies at the same position: pin power is the sum of its sub-regions (the K3 review
rule). If the file has explicit power targets (old region numbers), all rings of the split region
become targets.

**Script.** The generated Python script contains the subdivided model (rings in the pin
definition, slices in the layers); the script and the interface build the same model with the same
radii.

**Limits.** This card is a teaching and scoping tool; its results are **not a certification**.
