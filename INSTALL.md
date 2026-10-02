# Installation — openmc-arayuz

Türkçe: [KURULUM.md](KURULUM.md) · Overview: [README.en.md](README.en.md)

`openmc-arayuz` is a desktop application for building and running OpenMC reactor models, from a
fuel pin to a full core and from shielding to depletion. The model is set up in the interface,
the geometry is plotted before the calculation, and the calculation is started and its results
are read in the same place.

Installation has four steps; the longest is the one-time nuclear data download.

## Requirements

| | |
|---|---|
| Operating system | Linux (developed on Ubuntu 22.04 / 24.04). On Windows it runs under **WSL2** (Ubuntu); Windows 11 WSLg is sufficient for the graphical window. A conda-forge OpenMC package exists for macOS, but macOS has not been tested. |
| Disk | ~20 GB free (the unpacked nuclear data take ~13 GB) |
| Memory | 8 GB is enough; 16 GB is comfortable for 17×17 assemblies and 3D models |
| Internet | For the data download (once, a few GB) |

## 1. Install conda (Miniforge)

Skip this step if conda or mamba is already installed.

```bash
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh        # accept the defaults, then close and reopen the terminal
```

## 2. Create the environment

In the directory where the program was unpacked:

```bash
cd openmc_arayuz
conda env create -f environment.yml    # OpenMC 0.16.0 + PySide6 + matplotlib ... (a few minutes)
conda activate openmc-env
pip install -e . --no-deps             # installs the commands openmc-arayuz, openmc-arayuz-kosu
```

The OpenMC version is pinned to **0.16.0**: the reference values in the tests were measured with
it, and one depletion test depends on its distribcell ordering. OpenMC is not published on PyPI;
it comes from conda-forge. This is why `pip install` runs with **`--no-deps`**: all dependencies
were already installed from `environment.yml`. If the environment existed before, add the missing
tools with `conda install -c conda-forge pytest pytest-xdist babel`.

## 3. Download the nuclear data

```bash
./veri_indir.sh --bashrc
```

The script downloads into `~/nucdata` and verifies:

- the **ENDF/B-VIII.0 HDF5 cross section library** (OpenMC's official library,
  https://openmc.org/data), unpacked to `~/nucdata/endfb-viii.0-hdf5/`;
- the **depletion chains**: ENDF/B-VIII.0 thermal and fast (3820 nuclides, ~27 MB each) and
  CASL simplified thermal and fast (228 nuclides, ~1 MB each), in `~/nucdata/chain/`.
  The byte count and sha256 of every chain file are checked against a table in the script;
  an incomplete download is not accepted, and a file that is already present and correct is not
  downloaded again.

`--bashrc` adds `OPENMC_CROSS_SECTIONS` and `OPENMC_CHAIN_FILE` to `~/.bashrc`. When it has
finished, **open a new terminal** (or `source ~/.bashrc`) and activate the environment again:
`conda activate openmc-env`.

Other options:

| Command | Effect |
|---|---|
| `./veri_indir.sh` | Download everything; print the lines to add to `~/.bashrc` instead of adding them |
| `./veri_indir.sh --hedef /other/disk/nucdata --bashrc` | Put the data on another disk |
| `./veri_indir.sh --yalniz-zincir` | Depletion chains only (~57 MB) |
| `./veri_indir.sh --yardim` | Help |

If the download is interrupted, run the script again; it resumes where it stopped.

The application selects the depletion chain for each model itself (thermal or fast); it does not
rely on `OPENMC_CHAIN_FILE`, which is used only for terminal and script work.

### Verifying a chain file by hand

The first chain download in this project stopped silently at 13 %: 3 645 440 of 27 526 672 bytes,
ending in the middle of an XML attribute. The file name and location were correct, so nothing
looked wrong. The script now checks size and sha256; the same check by hand:

```bash
URL=https://anl.box.com/shared/static/nyezmyuofd4eqt6wzd626lqth7wvpprr.xml
# 1. Size reported by the server (box.com answers HEAD with 404; use a 1-byte GET)
curl -sL -r 0-0 -D - "$URL" -o /dev/null | grep -i content-range   # .../27526672
# 2. Download under a temporary name; resume with -C - if interrupted
curl -L --fail --retry 3 -C - -o chain.xml.part "$URL"
# 3. Is the size equal, is the file closed, can it be parsed?
stat -c %s chain.xml.part
tail -c 200 chain.xml.part | grep -c "</depletion_chain>"            # must print 1
python3 -c "import openmc.deplete as d; print(len(d.Chain.from_xml('chain.xml.part').nuclides))"
sha256sum chain.xml.part   # compare with the table in veri_indir.sh
# 4. Only if everything matches, move it to its final name
mv chain.xml.part ~/nucdata/chain/chain_endfb80_thermal.xml
```

The interface and `calistir.sh` perform this check themselves: an incomplete chain appears as an
**error** finding in the model check, and depletion cannot be started.

Windowed multipole (WMP) data are deliberately not downloaded: the 1.7 GB file on openmc.org is
the complete ENDF/B-VII.1 library, and mixing it with ENDF/B-VIII.0 cross sections would combine
two evaluations in one model.

## 4. Check the installation and start

```bash
pytest -m hizli -n auto -q       # fast suite, in parallel (~40 s); expect "passed" and 0 failed
./calistir.sh                    # the application opens (or: openmc-arayuz)
```

First calculation: on the start screen (*What would you like to model?*) choose **Fuel pin →
From template**, then press **F9** (Run). Within about half a minute the result card should show
**k∞ ≈ 1.323 ± 0.001** (UO₂ 3.0 %, hot operating conditions, *Normal* accuracy preset; measured
1.3227 ± 0.0008, 1σ). Small differences in the last digit are normal on another machine because
of statistics; a difference larger than ±0.003 points to an installation problem.

The examples are listed at the bottom of the start screen (17×17 PWR assembly, hexagonal SFR
assembly, MTR plate, Godiva critical sphere, shielding sphere, depletion and others; see
[docs/ORNEKLER.en.md](docs/ORNEKLER.en.md)). Examples open as a **copy**; use **File → Save as**
for your own file.

## Tests

| Command | What it does |
|---|---|
| `pytest -m hizli -n auto -q` | Fast suite, parallel (~40 s) |
| `pytest -m hizli -q` | Fast suite, single core (~2.5 min) |
| `pytest -m "hizli and not veri"` | Tests that need no nuclear data (this is what CI runs) |
| `pytest -m yavas` | Monte Carlo tests (long; nuclear data required) |
| `python3 -m testler.test_regresyon --hizli` | Older runner; must end with "0 kaldi" (0 failed) |
| `python3 -m testler.test_regresyon` | Full suite including Monte Carlo |
| `TEST_SURE=1 python3 -m testler.test_regresyon --hizli` | Time per test and the 20 slowest tests |

Tests marked `veri` are skipped when `OPENMC_CROSS_SECTIONS` is not set (step 3); tests that also
need a depletion chain are skipped when no chain is found. The tests never write to the user's
real application settings (they are redirected to a temporary directory).

Reproducing the validation tables (benchmark runs, V&V set) is described in
[docs/VV.en.md](docs/VV.en.md), section "Reproduction".

## Running without a display (headless)

`calistir.sh` refuses to start without a graphical session (`DISPLAY` / `WAYLAND_DISPLAY`).
Without a display — over SSH, on a cluster node, in CI — use the GUI-free core layer:

```bash
openmc-arayuz-kosu ornekler/pwr_pinhucre.json                   # run and print the result
openmc-arayuz-kosu ornekler/pwr_17x17.json --dizin /tmp/run -s 24 # run directory, 24 OpenMP threads
openmc-arayuz-kosu ornekler/pwr_pinhucre.json --sadece-dogrula  # model check only
openmc-arayuz-kosu ornekler/pwr_17x17.json --betik model.py     # generate a standalone Python script
openmc-arayuz-kosu rapor <run directory> -o report.pdf          # report (PDF or HTML)
openmc-arayuz-kosu uygunluk <run directory> --profil A,D [--siki]  # conformity check
openmc-arayuz-kosu yeniden <run directory> --kuru               # environment differences vs. kapsul.json
python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json -s 16     # depletion (--hazirla: volumes/chain only)
```

Exit codes of `uygunluk` (for CI or course automation): 0 no error finding, 1 error finding
present (or the check could not be made), 2 usage error, 3 with `--siki`: at least one rule could
not be evaluated ("not applicable"). Without `--siki`, rules that cannot be evaluated are not
counted as failures; they appear in the printed counts. If `pip install -e .` was not run, the same
commands work as `python3 -m cekirdek.kosucu ...`. In the interface the script export is
**File → Export as Python script (Ctrl+E)**.

The GUI test suite itself runs headless with the Qt offscreen platform:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -m hizli -n 4 -q
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `openmc PATH'te yok` (openmc not on PATH) | The environment is not active: `conda activate openmc-env`. |
| `OPENMC_CROSS_SECTIONS ayarli degil` (not set) | Step 3 is not complete or no new terminal was opened: `source ~/.bashrc`. |
| `Grafik oturum yok (DISPLAY...)` (no graphical session) | You are connected over SSH, or WSL has no graphics. Open the application in a desktop session; WSL needs Windows 11 and an up-to-date WSL (`wsl --update`). Without a display, use the terminal commands above. |
| The Depletion page reports a missing or broken chain | `./veri_indir.sh --yalniz-zincir` |
| `conda env create` takes very long | `conda config --set solver libmamba` (the default in Miniforge) or `mamba env create -f environment.yml` |
| A temperature sweep stops in the middle of a run | The data library has narrow temperature ranges: neutron data 250–2500 K, but S(α,β) for water only 284–800 K. The model check reads these ranges in advance; keep the sweep inside them. |
| Where are the results written? | For a saved project, in the `kosu` directory next to the project file; for an unsaved (new or example) project, under `~/openmc_kosular`. The Run page shows the full path. |
| Reporting a problem | Attach the application log `~/.local/state/openmc_arayuz/openmc_arayuz.log` (under `$XDG_STATE_HOME` if set) and, for a run, the run directory with `spec.json` and `kapsul.json`. |
