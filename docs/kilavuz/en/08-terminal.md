<a id="terminal"></a>
# 8. Terminal and HPC use

The core layer of the application (`cekirdek/`) does not depend on the user interface: a model
can be checked, run, reported, put through the conformity check and reproduced from the
terminal as well. This path is meant for long runs, work on a server or a computing cluster,
course automation and continuous integration (CI). The terminal uses **the same** model-check
gate, the same model builder and the same result reader as the user interface; results obtained
in either way are identical.

The commands work in the environment activated with `conda activate openmc-env`. If the package
was installed with `pip install -e . --no-deps` (see [Installation](01-kurulum.md#kurulum)) the
`openmc-arayuz-kosu` command exists; otherwise use the `python3 -m cekirdek.kosucu` equivalent of
each command (from the repository root). Every command prints its own usage with `--help`.

## 8.1 Running a model

```bash
openmc-arayuz-kosu ornekler/pwr_pinhucre.json                    # check, run, print the result
openmc-arayuz-kosu ornekler/pwr_17x17.json --dizin /tmp/deneme -s 24
openmc-arayuz-kosu ornekler/mtr_plaka.json --sadece-dogrula      # model check only
openmc-arayuz-kosu ornekler/pwr_17x17.json --betik model.py      # also write a Python script
python3 -m cekirdek.kosucu ornekler/pwr_pinhucre.json            # equivalent without installation
```

| Option | Meaning |
|---|---|
| `<spec.json>` | The JSON file of the model (a file saved by the user interface or an example under `ornekler/`). It is the first argument. |
| `--dizin D` | Run directory. Default: `calistirma.dizin` next to the spec file (default `kosu`). |
| `-s N`, `--is-parcacigi N` | Number of OpenMP threads (`openmc -s N`). Default: `calistirma.is_parcacigi` in the spec (default 8). |
| `--sadece-dogrula` | Runs the model check, prints the findings and does not run. With `--betik` the script is still written. |
| `--betik model.py` | Also writes the model as a stand-alone OpenMC Python script (see 8.6). |

The output has three steps: **[1/3] model check** (findings; with an error the run does not
start), **[2/3] run** (on a terminal, a single line `k = ... ± ...` updated every 10 batches),
**[3/3] results** (k-eff ± 1σ, criticality interpretation, number of batches / inactive batches /
particles, Shannon entropy source convergence, beta_eff and Λ if requested, power distribution and
peaking factors). A fixed source calculation has no k-eff; the command prints the source, its
strength and a note on tally units (OpenMC applies the strength itself; do not multiply again).
How to read the results: [6. Interpreting results](06-sonuclar.md#sonuclar).

Exit code: `0` success (or a model check without errors with `--sadece-dogrula`), `1` model-check
error or failed run, `2` unknown option.

> **Do not run the examples in place.** Without `--dizin` the run directory is written next to the
> spec file, i.e. under `ornekler/kosu`. The `ornekler/*.json` files are test references; use
> `--dizin /tmp/...` or your own project directory for trial runs. A run of an unsaved model in
> the user interface goes to `~/openmc_kosular`.

### What is in a run directory

| File | Contents |
|---|---|
| `model.xml` | The model OpenMC reads (geometry, materials, settings, tallies) |
| `spec.json` | The model of the run (the report and the conformity check read it) |
| `kapsul.json` | Reproducibility capsule: spec hash, application version and git commit, OpenMC version, library and chain summaries, seed, threads, platform, environment hash |
| `statepoint.*.h5`, `summary.h5` | OpenMC result files |
| `kosu.log` | The full screen output of OpenMC (including lost particle warnings) |

A depletion run has its own directory (`<dir>_tukenme`, e.g. `kosu_tukenme`) holding
`depletion_results.h5` and `tukenme_spec.json`, which records the model the result belongs to.

## 8.2 Creating a report

```bash
openmc-arayuz-kosu rapor kosu/                         # kosu/rapor.pdf
openmc-arayuz-kosu rapor kosu/ -o rapor.html           # format from the extension: .pdf | .html
openmc-arayuz-kosu rapor kosu_tukenme/ --spec model.json
```

Without `-o` (or `--cikti`) the report is written to the run directory as `rapor.pdf`. The model
is read from `spec.json` in the run directory (or from `tukenme_spec.json`); if neither exists,
give it with `--spec`. The report is the same as **File → Create report... (Ctrl+R)** in the user
interface and contains the conformity annex (see the [report lesson](05-dersler.md#ders-rapor)).
Exit code: `0` done, `1` the report could not be created, `2` usage error (extension is not
`.pdf`/`.html`, spec not found).

## 8.3 Conformity check

```bash
openmc-arayuz-kosu uygunluk kosu/                      # profiles from the spec selection (else A,D)
openmc-arayuz-kosu uygunluk kosu/ --profil A,B,C,D
openmc-arayuz-kosu uygunluk kosu/ --profil A,D --siki  # a rule that cannot be evaluated also fails
```

Each finding is one line: level (ERROR / WARNING / INFO), rule identifier (K1 ... K16), profile,
status (passed / NOT MET / not applicable / note) and message; the recommendation of a rule that
is not met is printed below it. At the end the command prints the counts, the USL note for the
selected profiles and the frame "this check is not a certification". Profiles and the meaning of
the rules: [7. Conformity check and V&V](07-uygunluk.md#uygunluk-denetimi); the rules one by one
and how to resolve them: [Conformity rules](09-sorun-giderme.md#uygunluk-kurallari).

| Exit code | Meaning |
|---|---|
| `0` | no finding at error level |
| `1` | at least one error finding, or the check could not be done (run directory unreadable) |
| `2` | usage error (unknown option, missing run directory, unknown profile) |
| `3` | `--siki` was given and some rule could not be evaluated ("not applicable") |

Without `--siki`, rules that cannot be evaluated do not count as failures; they appear in the
counts. Use the exit code for course automation and CI, for example in an assignment script
`openmc-arayuz-kosu uygunluk kosu/ --profil A,D || exit 1`.

## 8.4 Reproducing a run

```bash
openmc-arayuz-kosu yeniden kosu/ --kuru            # without running: plan and environment differences
openmc-arayuz-kosu yeniden kosu/                   # runs with the same spec, seed and threads
openmc-arayuz-kosu yeniden kosu/ --hedef /tmp/tekrar -s 8
```

The command first checks that `spec.json` in the run directory matches the hash stored in
`kapsul.json` (it refuses if it changed), then lists, field by field, the differences between the
current environment and the capsule (application version, OpenMC, library, chain, environment
hash...). Without `--kuru` it runs the same spec with the same seed and number of threads in a
**separate** directory (default `<run_dir>_yeniden`; change it with `--hedef`; the source run
directory is not written) and reports the k-eff difference. The difference measured on the same
machine is of the order of 10⁻¹⁶–10⁻¹⁵ (OpenMP reduction order); the tool reports this as
"identical to rounding level" and gives a larger difference in units of σ. The capsule is
**evidence, not a guarantee**: on a different machine, library or OpenMC version differences are
expected and listed (see `docs/YAZILIM_KALITE.md` §3,
[software quality evidence](../../YAZILIM_KALITE.md)). Old run directories created before
`kapsul.json` existed cannot be reproduced.

## 8.5 Depletion from the terminal

```bash
python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json --hazirla        # information, no run
python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json -s 16 --dizin /tmp/yanma
```

`--hazirla` prints, without running, the selected chain and the reason for it, the fission yield
energy, the power density, the steps and the number of transport solutions, the analytic volume
of every burnable material and the heavy metal mass; read this output before a long run (details:
[4.9 Depletion](04i-tukenme.md#tukenme)). At the end of a run a day / MWd/kg / k-eff table and the
path of `depletion_results.h5` are printed. Without `--dizin` the directory is
`<calistirma.dizin>_tukenme` next to the spec (again, do not run the examples in place). Whether
depletion is started from the user interface or the terminal, the application selects the chain
itself; `OPENMC_CHAIN_FILE` is only for the exported script and OpenMC's own tools.

## 8.6 Exporting as a Python script and as OpenMC XML

The user interface is not a dead end. **File → Export as Python script... (Ctrl+E)** or
`--betik model.py` turns the model into a readable, stand-alone OpenMC script:

- The script does **not** depend on `openmc_arayuz`; it needs only `openmc` and `matplotlib`.
- Variable names are prefixed by type and unique (`m_uo2`, `c_yakit_cubugu`, `d_demet_17x17`);
  the geometry is produced by the same traversal as the model builder, and a test checks that it
  gives the same XML as the builder.
- `python3 model.py` first plots the geometry (`geometri_xy.png`); the `model.run(...)` line is
  **commented out**: remove the comment once the plot is correct
  ([plot first, run later](06-sonuclar.md#once-ciz)). With depletion enabled a `tukenme_kos()`
  function is written as well.
- The conversion is **one-way**: a script cannot be turned back into a spec.

**File → Export as OpenMC XML...** writes a single `model.xml` into the selected directory;
OpenMC runs it directly with the `openmc` command.

<a id="hpc"></a>
## 8.7 Computing clusters (HPC)

OpenMC in this installation (conda-forge, 0.16.0) is built **without MPI**; it runs on a single
node with OpenMP threads. On a cluster there are two ways:

1. **With the application itself, on one node.** Install the environment (`environment.yml`) and
   the nuclear data (`./veri_indir.sh --hedef ...`) on a disk the node can see, submit the job with
   `openmc-arayuz-kosu` and set the number of threads to the number of cores of the node (`-s`).
   No user interface is needed; the commands work on a node without a graphical session. An
   example job script (SLURM; adapt it to the rules of your cluster):

   ```bash
   #!/bin/bash
   #SBATCH --job-name=pwr17
   #SBATCH --nodes=1
   #SBATCH --cpus-per-task=32
   #SBATCH --time=02:00:00
   source "$(conda info --base)/etc/profile.d/conda.sh"
   conda activate openmc-env
   export OPENMC_CROSS_SECTIONS=$HOME/nucdata/endfb-viii.0-hdf5/cross_sections.xml
   openmc-arayuz-kosu proje/pwr_17x17.json --dizin "$SCRATCH/pwr17" -s "$SLURM_CPUS_PER_TASK"
   openmc-arayuz-kosu uygunluk "$SCRATCH/pwr17" --profil A,D
   ```

2. **With the cluster's own OpenMC (including MPI).** Export the model as a script or as
   `model.xml` and run it with the (MPI-enabled) OpenMC installed on the cluster, e.g.
   `mpirun -n 4 openmc -s 16` (in the directory that holds `model.xml`). In this case the
   model-check gate, the capsule and the conformity check do **not** run during the run: check the
   model here first with `--sadece-dogrula`; after the run, put the statepoint files in the same
   directory as `spec.json` and read them with `openmc-arayuz-kosu uygunluk` and
   `openmc-arayuz-kosu rapor`. If the OpenMC version or the cross section library of the cluster is
   different, the result cannot be compared one to one with the measurements in this guide (the
   library and version are written in the report; see K4).

Give the number of threads with `-s`. The `OMP_NUM_THREADS` environment variable is OpenMP's
general setting; `openmc-arayuz-kosu` starts OpenMC explicitly with `-s N`, and depletion sets
`OMP_NUM_THREADS` itself when `-s` is given. Memory: 16 GB per node is comfortable for a 17×17
assembly and 3D models; in depletion the 3820 nuclides of the chain are added to the fuel, so
memory use and run time grow (measurements: [4.9 Depletion](04i-tukenme.md#tukenme)).

## 8.8 Environment variables

| Variable | Read by | Meaning |
|---|---|---|
| `OPENMC_CROSS_SECTIONS` | OpenMC, model check | Path of `cross_sections.xml`. If missing, the model check reports an error and the run does not start. `./veri_indir.sh --bashrc` sets it. |
| `OPENMC_CHAIN_FILE` | only the exported script and OpenMC tools | Depletion chain. The application selects the chain for every model itself and does not rely on this variable. |
| `OPENMC_ARAYUZ_DIL` | user interface, core messages | `tr` or `en`. Takes precedence over the saved setting and the system language. |
| `OPENMC_ARAYUZ_OPENMC` | runner | ABSOLUTE path of the `openmc` executable (`~` is expanded). A relative or non-executable path is ignored with a warning. Search order: this variable → `bin/openmc` next to the Python running the application (same environment) → only the absolute entries of `PATH` (empty, `.` and relative entries are skipped) → `$CONDA_PREFIX/bin`. |
| `OPENMC_ARAYUZ_VERI` | examples, translations, guide | Data root: the directory containing `ornekler/`, `locale/` and `docs/kilavuz/` (`ornekler/pwr_pinhucre.json` must exist). Default: the source tree or `share/openmc-arayuz` of the installation. Ignored with a warning if invalid. |
| `OPENMC_ARAYUZ_KILAVUZ` | in-app user guide | Directory of the guide sources (default `docs/kilavuz` in the data root). `~` and relative paths are expanded; ignored with a warning if the directory does not exist. |
| `OPENMC_ARAYUZ_LOCALE` | translation catalog | The `locale` directory (default `locale` in the data root). `~` and relative paths are expanded; ignored with a warning if the directory does not exist. |
| `OMP_NUM_THREADS` | OpenMP | General number of threads (depletion sets it from `-s`). |
| `XDG_STATE_HOME` | application log | Base of the log directory (default `~/.local/state`). |
| `QT_QPA_PLATFORM` | Qt | `offscreen`: Qt without a graphical session (screenshot scripts, tests). |

## 8.9 Log file

The application log is written to `~/.local/state/openmc_arayuz/openmc_arayuz.log` (under
`XDG_STATE_HOME` if it is set; it rotates at ~1 MB × 5 backups). When reporting a problem, attach
this file and `kosu.log` from the run directory concerned. If the log directory cannot be written,
the application does not crash; the situation is printed once to stderr. Common problems:
[9. Troubleshooting](09-sorun-giderme.md#sorun-giderme).
