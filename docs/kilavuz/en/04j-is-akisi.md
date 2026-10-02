<a id="is-akisi"></a>
## 4.10 Workflow: queue, history, comparison, SLURM

The **Workflow** window manages many runs at once: it puts runs in a **queue**, runs them in
order or with limited parallelism, writes every finished run to the **run history**, shows the
k-eff and pin power difference of two runs together with its statistical significance, and
generates a **SLURM batch script** to take the model to a compute cluster (HPC). The window has
three tabs: **Run queue**, **History and comparison**, **SLURM script**. It is opened from the
main window with **Tools > Workflow...** (the current model goes to the queue and to the SLURM
form); it can also be opened on its own with `python -m arayuz.kuyruk model.json`.

Every run uses its own **run directory** (`model.xml`, `spec.json`, `kapsul.json`,
`statepoint.*.h5`, `kosu.log` side by side, the same layout as the Run tab); two unfinished
runs cannot share a directory.

<a id="is-akisi-kuyruk"></a>
### Run queue

![Run queue: parallelism settings, order and status table](../resimler/en/is_akisi_kuyruk.png)

- **Maximum parallel runs**: how many runs are active at the same time; 1 is a strictly
  sequential queue.
- **Total thread budget**: the sum of the threads of concurrent runs never exceeds this
  (default: number of CPU cores). The queue order is strict: if the next run does not fit in
  the budget, a smaller run behind it does not jump ahead.
- **Threads per run (OMP)**: the value of `OMP_NUM_THREADS` and `openmc -s`.
- **MPI process count**: 0 is a run without MPI; 2 or more starts with `mpiexec -n N openmc`
  and takes N x threads from the budget. `mpiexec` is searched first in
  `OPENMC_ARAYUZ_MPIEXEC` (absolute path), then in the `bin/` next to Python, then only in the
  absolute entries of `PATH`. If openmc was built without MPI (`openmc --version` gives
  `MPI enabled: no`) the run stops with a clear error instead of silently running as a single
  process.
- **Run folder**: every run goes to a separate subdirectory below it, named after the model.

Buttons: **Add current model** (the model in the main window; it passes the validation gate
before the run starts), **Add parametric model...** (below), **Start / Pause** (when paused,
active runs continue and no new run starts), **Up / Down** (order), **Cancel** (a waiting run
at once, an active run is ended with SIGTERM), **Remove**. The table shows the state (waiting,
running, done, failed, cancelled), the batch, the cumulative k +/- sigma and the elapsed time,
updated live.

<a id="is-akisi-gecmis"></a>
### History and comparison

Every queued run that is done, failed or cancelled (and every single run of the Run tab) is
written to
`~/.local/share/openmc_arayuz/kosu_gecmisi.sqlite3` (every write is a single SQLite
transaction; no half-written record remains). Removing a history row does not delete the run
directory.

![Comparison of two runs: k difference, pin power difference table and map](../resimler/en/is_akisi_karsilastir.png)

Select two rows and press **Compare the two selected runs** (or pick any two run directories
with **Choose two folders...**). The older run is run 1, the newer is run 2.

- **k difference:** dk = k2 - k1, sigma = sqrt(sigma1^2 + sigma2^2), **z = dk / sigma**. If
  |z| > 2 the difference is statistically significant (about 95 %; the 2 sigma method of the
  project). d rho = (1/k1 - 1/k2) x 1e5 pcm. The runs are assumed independent; models run
  with the same seed are correlated, then the true sigma is smaller and the z shown is
  **conservative**.
- **Pin power difference:** if both runs have the power distribution, the relative power
  difference, its sigma and its z at every common position; the table is sorted by |z| and a
  difference map is drawn for a rectangular lattice (red: run 2 higher, blue: lower). Among N pins
  about 4.6 % x N positions have |z| > 2 by chance alone; the window prints this number next
  to the count, so a single "significant" pin is not evidence of a difference.

<a id="is-akisi-parametrik"></a>
### Parametric model

A parametric model is a set of **named variables** applied to a base spec, together with
their **parameter sweep** values. The variable types are the sweep types of the Analysis tab
(fuel temperature, coolant temperature with the density correlation, boron, enrichment,
assembly pitch, group rotation ...); in addition the `yol` type changes any **numeric** field
of the spec through a dotted path (`ayarlar.parcacik`, `ayarlar.entropi_mesh.boyut.0`). The
sweep is `kartezyen` (all combinations) or `esli` (lists of equal length, element by element).
The file is JSON and does not change in a round trip:

```json
{
  "bicim": "openmc-arayuz-parametrik", "surum": 1, "ad": "zenginlik-parcacik",
  "degiskenler": [
    {"ad": "zen", "tur": "zenginlik", "hedef": "uo2", "deger": null, "birim": "%"},
    {"ad": "n", "tur": "yol", "hedef": "ayarlar.parcacik", "deger": 5000, "birim": ""}
  ],
  "tarama": {"bicim": "kartezyen", "degerler": {"zen": [2.0, 3.1, 4.5], "n": [5000]}},
  "taban": { "...": "model spec" }
}
```

`deger: null` means that the base value is kept at points where the variable is not swept.
**Add parametric model...** adds every point to the queue in the directories `nokta_000`,
`nokta_001` ... From Python: `parametre.kuyruga_ekle(model, kuyruk, kok_dizin)`; an existing
single-variable sweep is turned into a parametric model with
`tarama.parametrik_model(spec, tur, hedef, degerler)`.

<a id="is-akisi-slurm"></a>
### SLURM script

![SLURM script form and the preview checked with bash -n](../resimler/en/is_akisi_slurm.png)

The form generates the `sbatch` script: name, time limit (`hh:mm:ss`), nodes, MPI task count
(`ntasks`), CPUs per task (OMP threads), partition, account, memory, e-mail, `module load`
modules, conda environment, the openmc path on the cluster and `OPENMC_CROSS_SECTIONS`. If the
task count is above 1 the command is `srun openmc -s ...` (or `mpiexec`); openmc must be built
with MPI on the cluster. The preview is checked with `bash -n` after every change. **Prepare
run folder...** writes `model.xml`, `spec.json` and `is.sh` to the chosen folder; copy the
folder to the cluster and submit it with `sbatch is.sh`. The script is never executed on this
machine.

Security: `#SBATCH` lines are read by `sbatch`, not by the shell, and they have no quoting;
these fields are therefore checked against strict patterns and a value with a space, a new
line or a shell character is **rejected** (the field shows a red error). The folder path, the
openmc path and the environment variable values are quoted with single quotes: `$(...)`,
`` `...` `` and `;` are not interpreted by the shell.

<a id="ders-is-akisi"></a>
### Lesson: an enrichment sweep through the queue and comparing two runs

Goal: run three enrichments of the PWR pin cell in order through the queue, then compare two
runs of the same model with different seeds and answer "is the difference noise?" with z.

1. Open `ornekler/pwr_pinhucre.json`; in the calculation settings set particles to 2000,
   batches to 60 and inactive batches to 20 (to keep the lesson short).
2. In the Workflow window set **Maximum parallel runs** to 1 and **Threads per run** to 6.
3. Save the parametric file (format above; variable `zen`, type `zenginlik`, target `uo2`,
   values `[2.0, 3.1, 4.5]`) and load it with **Add parametric model...**; three rows appear.
   Press **Start**: the runs finish in order and k grows with enrichment.
4. In the main window change the seed from 1 to 2 and run the same model once more with
   **Add current model** (enrichment 3.1, seed 2).
5. In **History and comparison** select the `zen=3.1` run and the seed 2 run and compare
   them. Expected: |z| mostly below 2; the physics is the same and the difference is
   statistical. Comparing the 3.1 and 4.5 enrichment runs gives a very large |z|: the
   difference is real.

The result is not a certificate; the significance covers only the statistical uncertainty,
not the nuclear data and modelling uncertainty.
