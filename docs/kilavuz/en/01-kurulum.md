<a id="kurulum"></a>
# 1. Installation and first start

This chapter covers installing the program from scratch, downloading the nuclear data and the
**Start** screen shown at first start. The full text of the steps is in
[KURULUM.md](../../../KURULUM.md) in the repository; here you also find **why** each step is
needed and how to check it.

## 1.1 Requirements

| | |
|---|---|
| Operating system | Linux (developed on Ubuntu 22.04 / 24.04). On Windows via **WSL2** (Ubuntu); the WSLg support of Windows 11 is enough for the graphical window. macOS has not been tested. |
| Disk | ~20 GB free space (~13 GB once the nuclear data is unpacked) |
| Memory | 8 GB is enough; 16 GB is comfortable for 17x17 assemblies and 3D models |
| Internet | Only for the data download (once, a few GB) |

The program runs in a **conda environment**: OpenMC is not published on PyPI, it comes from conda-forge.

## 1.2 Installation steps

**1. Conda (Miniforge).** Skip if you already have conda/mamba.

```bash
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh        # accept the defaults, then close and reopen the terminal
```

**2. Environment.** In the repository folder:

```bash
conda env create -f environment.yml    # OpenMC 0.16.0 + PySide6 + matplotlib ... (a few minutes)
conda activate openmc-env
pip install -e . --no-deps             # commands: openmc-arayuz, openmc-arayuz-kosu
```

`--no-deps` is given on purpose: all dependencies were installed by `environment.yml`; letting
pip look for OpenMC on PyPI breaks the installation.

**3. Nuclear data** (see [1.3](#nukleer-veri) below):

```bash
./veri_indir.sh --bashrc
```

When it finishes, **open a new terminal** (or `source ~/.bashrc`) and run `conda activate openmc-env`.

**4. Check and start:**

```bash
pytest -m hizli -n auto -q          # fast test suite; ends with "passed", 0 failed
./calistir.sh                       # the interface opens (or: openmc-arayuz)
./calistir.sh ornekler/pwr_17x17.json   # directly with an example (opened as a copy)
```

Before opening, `calistir.sh` checks the environment: is the `openmc` command on PATH, is
`OPENMC_CROSS_SECTIONS` set, is there a graphical session, is the depletion chain complete. If
something is missing it tells you what to do (see
[9.4 Installation and environment problems](09-sorun-giderme.md#kurulum-sorunlari)).

<a id="nukleer-veri"></a>
## 1.3 Nuclear data and depletion chain

A Monte Carlo calculation reads the **cross sections** of the nuclides from a library. This
program is validated with the OpenMC HDF5 version of the **ENDF/B-VIII.0** library (all
measurement anchors and benchmark results were obtained with it). `veri_indir.sh` downloads and
checks the following under `~/nucdata`:

| Data | Size | Used for |
|---|---|---|
| ENDF/B-VIII.0 HDF5 cross sections (`endfb-viii.0-hdf5/cross_sections.xml`) | ~13 GB unpacked | every calculation |
| Depletion chains: ENDF/B-VIII.0 thermal + fast (3820 nuclides) | ~27 MB each | depletion |
| CASL thermal + fast (228 nuclides) | ~1 MB each | quick preliminary depletion studies |

Options:

```bash
./veri_indir.sh --hedef /baska/disk/nucdata --bashrc   # to another disk
./veri_indir.sh --yalniz-zincir                        # chains only (~57 MB)
```

`--bashrc` adds two environment variables to `~/.bashrc`:

```
OPENMC_CROSS_SECTIONS = ~/nucdata/endfb-viii.0-hdf5/cross_sections.xml
OPENMC_CHAIN_FILE     = ~/nucdata/chain/chain_endfb80_thermal.xml
```

- `OPENMC_CROSS_SECTIONS` is **required**; without it no run starts and the model check panel
  shows a `veri kutuphanesi` error.
- `OPENMC_CHAIN_FILE` is only for the terminal and the exported script. The interface **chooses**
  the chain for each model itself (thermal or fast; see [4.9 Depletion](04i-tukenme.md#tukenme)).

**A partial download is not accepted.** The byte count and sha256 of the chains are compared
with the table in the script. (The first download in this project silently stopped at 13%; the
file name and location were right, nobody looking at it could have seen the problem.) If the
download is interrupted, run the script again; it resumes. The interface also shows a partial
chain as an **error** in the model check panel and does not start depletion.

> **WMP (windowed multipole) data is deliberately not downloaded.** The 1.7 GB file on
> openmc.org is the complete ENDF/B-VII.1 library; mixing it with VIII.0 cross sections would
> combine two different evaluations in one model.

**Temperature range.** The neutron data covers 250–2500 K, but for example **S(α,β) for water
covers only 284–800 K**. A material temperature or temperature sweep outside this range gives a
warning/error in the model check (see [6.5 Known pitfalls](06-sonuclar.md#tuzaklar)).

<a id="baslangic"></a>
## 1.4 First start: the Start screen

When the program opens without a model, the **"What would you like to model?"** screen appears.

![Start screen: model type cards, recent files and example gallery](../resimler/en/baslangic.png)

**Model type cards.** Each card has a description and two actions:

| Card | Start empty | From example | Model built (core type) |
|---|---|---|---|
| **Fuel pin (pin cell)** | yes | `ornekler/pwr_pinhucre.json` | `tek_cubuk` |
| **Fuel assembly — square** | yes | `ornekler/pwr_17x17.json` | `tek_demet` (square) |
| **Fuel assembly — hexagonal** | yes | `ornekler/sfr_altigen.json` | `tek_demet` (hexagonal) |
| **Full core (square map)** | yes | — | `kare_kafes` |
| **Full core — hexagonal** | yes | — | `altigen_kafes` |
| **MTR plate-type fuel element** | yes | `ornekler/mtr_plaka.json` | `tek_plaka` |
| **Compact core with drums** | yes | `ornekler/tamburlu_kor.json` | `tamburlu` |
| **Shielding (fixed source)** | — | `ornekler/zirh_kure.json` | `kuresel` |
| **Open from file** | **Open…** (Ctrl+O): a saved model (`.json`) or an OpenMC XML folder | | |

- **Start empty** builds a simple, working model: materials, components and geometry are ready;
  the run settings use the "Normal" accuracy preset. You can run it right away with **F9**.
- **From example** opens an **unsaved copy** of a ready example. `ornekler/*.json` are test
  references; they are never overwritten. For your own file use **File → Save as**.
- A spherical assembly (shielding, Godiva-type benchmarks) cannot be started blank: its shells are
  edited only in JSON ([4.4 Geometry](04d-geometri.md#geometri)).

**Recent.** The models you saved appear in this strip (file name, directory, time of last change).

**Example gallery.** All examples in the repository; at the top a search box (**Search
examples…**), a level selector (introductory / intermediate / advanced) and category buttons
(**PWR**, **BWR**, **VVER**, **SFR**, **Research**, **Benchmark**, **Shielding**). Clicking a card
opens the example as a copy. The list of examples, their sources and measured values:
[ORNEKLER.md](../../ORNEKLER.md).

While a model is open, **File → New…** returns to the Start screen; **Back to open model** (Esc)
returns to the model.

## 1.5 Checking the installation: the first run

On the Start screen choose **Fuel pin (pin cell) → Start empty**, then **F9** (Run). Within half a
minute the result card should show **k∞ ≈ 1.323 ± 0.001** (UO₂ 3.0%, hot operating condition,
"Normal" preset; measured 1.3227 ± 0.0008). Small differences in the last digit are statistics;
a difference larger than ±0.003 points to an installation problem (wrong library, missing S(α,β)
data).

For a more complete first session: [2. A first calculation in 15 minutes](02-ilk-hesap.md#ilk-hesap).

## 1.6 Log file and settings

- Application log: `~/.local/state/openmc_arayuz/openmc_arayuz.log` (under `XDG_STATE_HOME` if
  set). Attach this file when you report a problem.
- Interface settings (theme, language, recent files): `~/.config/openmc_arayuz/`.
- Language: **View → Language** (Turkish / English) or the environment variable `OPENMC_ARAYUZ_DIL=en`.
