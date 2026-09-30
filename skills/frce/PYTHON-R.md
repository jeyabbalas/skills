Running Python and R on FRCE: the interpreters and what their modules set, keeping your packages out of the read-only installs and out of `~/.local`, venv and conda environments on cluster scratch and activating them in jobs, sizing threads and workers, R versions and personal libraries, Bioconductor and renv, and Jupyter kernels. You build environments and run code inside the user's allocation; submitting jobs and starting OnDemand sessions are the user's (ground rules in SKILL.md). Packages a module already has: MODULES.md (Finding software). PyTorch, TensorFlow, JAX, and their modules: DEEP-LEARNING.md. Containers: CONTAINERS.md. OnDemand forms: ONDEMAND.md.

Table of contents

- [Python on FRCE](#python-on-frce)
- [Virtual environments and conda](#virtual-environments-and-conda)
- [Threads and parallel workers](#threads-and-parallel-workers)
- [R on FRCE](#r-on-frce)
- [R packages and libraries](#r-packages-and-libraries)
- [Jupyter kernels](#jupyter-kernels)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Python on FRCE

| Interpreter | Use for | Notes |
|---|---|---|
| `/usr/bin/python3` | OS tools only | the OS's Python (EL8's default is 3.6; unchecked here: `/usr/bin/python3 --version`) |
| `module load python/3.12` or `python/3.13` | the base for a venv; quick work | staff builds of 3.6 to 3.13 (bare `python`: 3.13.1), read-only, with few packages (Sept 2026: `pip3 list` showed no numpy or pandas); they set `PYTHONHOME` and `PYTHONPATH` (below) |
| your venv or conda env on cluster scratch | anything you install; reproducible runs | [Virtual environments and conda](#virtual-environments-and-conda) |
| an application module with its own Python (snakemake, alphafold, jupyter, ...) | that application only | several are conda installs; never install into them |

- Pin a version: FRCE warns "not all libraries are included in every version".
- **The `python` modules set `PYTHONHOME`** to their install and prepend their site-packages to `PYTHONPATH` (`module display python/3.13`, Sept 2026). Both reach every Python the shell starts:
  - Any other interpreter (a conda env's, conda itself, `/usr/bin/python3`, one inside a container) loads the module's standard library and packages: it dies with `ModuleNotFoundError: No module named 'encodings'` or imports the wrong versions. conda brings its own Python, so load no `python` module for it: `module unload python` (or `unset PYTHONHOME PYTHONPATH`) before activating. Containers: CONTAINERS.md (Running containers).
  - A venv built on the module runs the same interpreter, but `PYTHONPATH` puts the module's packages ahead of the venv's: `unset PYTHONPATH` after activating.
  - Other modules add Python paths too: `jupyter/6.5.2` adds `python/3.11` and its own site-packages, `R/4.5.2` a Python 3.12 site-packages, and so does snakemake (WORKFLOWS.md (Snakemake)). Check `echo "$PYTHONHOME $PYTHONPATH"` when imports misbehave.
- Load order decides which `python3` runs: an application module loaded after `python/3.x` (or after `conda activate`) can put its own Python first (`which -a python3`).
- `/mnt/nasapps` is read-only, so `pip install` against a module Python falls back to your home. The only sign is one line, "Defaulting to user installation because normal site-packages is not writeable", and the package lands in `~/.local/lib/python3.12/site-packages`.
- **`~/.local` leaks.** Packages there load in every Python of that minor version whose user site is on: the module itself, a conda env's Python, a `--system-site-packages` venv, and a container that mounts your home. They shadow the versions those environments were built with. A plain venv ignores them.
  - In job scripts, `export PYTHONNOUSERSITE=1` (or run `python3 -s`); `python3 -m site` shows whether the user site is enabled.
  - Find strays with `python3 -m pip list --user`; remove them, or move `~/.local/lib/python3.*` aside, only with the user's go-ahead.
  - `%pip install` in a notebook on a shared kernel (as the OnDemand Jupyter screenshot does) lands in `~/.local` the same way: use your own env and kernel ([Jupyter kernels](#jupyter-kernels)).

## Virtual environments and conda

Environments and package caches go on cluster scratch, the files that rebuild them in /home or git (ground rule 5 in SKILL.md; STORAGE.md (Cluster scratch)). Downloads: TRANSFER.md (Downloads on the cluster).

**venv** on a module Python:

```bash
# on the compute node (inside your session)
module load python/3.12
python3 -m venv /scratch/cluster_scratch/$USER/envs/proj          # add --system-site-packages to reuse the module's packages
source /scratch/cluster_scratch/$USER/envs/proj/bin/activate
unset PYTHONPATH                                                  # else the module's packages shadow the venv's
export PIP_CACHE_DIR=/scratch/cluster_scratch/$USER/.cache/pip    # default ~/.cache/pip is in /home
python -m pip install -r ~/proj/requirements.txt
python -m pip freeze > ~/proj/requirements.lock.txt
```

The venv runs the module's interpreter: load the same `python/3.12` before activating it in later shells and jobs (and `unset PYTHONPATH` again), and rebuild it from the lock file if that version is ever retired.

**conda** modules (Sept 2026): `miniconda` 23.1.0, 24.3.0, and 25.9.1 (the default), and `mamba` 0.17.0 and 1.5.7 (the default; conda-based mamba 1.x). `miniconda/25.9.1` and `mamba/1.5.7` define `conda` shell functions (mamba also `mamba`), so `conda activate` works right after `module load` in a script, with no `conda init`. `miniconda/25.9.1` sets `CONDA_ENVS_PATH=$HOME/miniconda/envs` and `CONDA_PKGS_DIRS=$HOME/.conda/pkgs`; `mamba/1.5.7` sets neither, so it uses `~/.conda/envs` and `~/.conda/pkgs` (`conda config --show envs_dirs pkgs_dirs`). Redirect both, and pip's cache, after loading: `export CONDA_ENVS_PATH=/scratch/cluster_scratch/$USER/conda/envs CONDA_PKGS_DIRS=/scratch/cluster_scratch/$USER/conda/pkgs PIP_CACHE_DIR=/scratch/cluster_scratch/$USER/.cache/pip` (or `-p PREFIX` for one env). Prefer your own Miniforge (conda-forge by default, mamba included; several GB with environments, so get the user's go-ahead):

```bash
# on the compute node (inside your session)
cd /scratch/cluster_scratch/$USER
curl -fsSLo Miniforge3.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3.sh -b -p /scratch/cluster_scratch/$USER/miniforge3     # -b: no prompts, no ~/.bashrc changes
source /scratch/cluster_scratch/$USER/miniforge3/etc/profile.d/conda.sh
conda config --system --add channels bioconda      # --system: this install's .condarc, not ~/.condarc
conda config --system --add channels conda-forge   # added last, searched first
conda config --system --set channel_priority strict
mamba create -y -n proj python=3.12 pandas samtools
conda activate proj
conda env export --from-history > ~/proj/environment.yml
```

- **Activation in jobs and tool calls** without `conda init` (ground rule 6 in SKILL.md). A bare `conda activate` in a script fails with `CondaError: Run 'conda init' before 'conda activate'` (conda before 23.11: `Your shell has not been properly configured to use 'conda activate'`); source the install's `conda.sh` first (Miniforge), or load one of the modules above, which define the function. For a one-off command, `conda run -n proj CMD` needs no activation.
- `conda activate` works on envs made with mamba. mamba 2 (Miniforge's) needs `eval "$(mamba shell hook -s bash)"` before `mamba activate` and, under `set -u`, `MAMBA_ROOT_PREFIX` set to the install: scripts are simpler with `conda activate`. micromamba 2 defaults `MAMBA_ROOT_PREFIX` to `~/.local/share/mamba`, in /home: set it to cluster scratch.
- **Channels.** The miniconda module is Anaconda's installer, whose `defaults` channels fall under Anaconda's terms of service, which tie free use to the kind and size of organization; conda-forge and bioconda don't. Check `conda config --show channels`, and with a module conda pass `-c conda-forge -c bioconda --override-channels`.
- Don't create envs inside another person's or group's conda install (a module's, CCBR's shared one, ABCS's development envs); activate theirs as provided, or make your own.
- Caches: `conda clean --all` and `python -m pip cache purge` free space, with the user's go-ahead.

**A batch job for the user to submit** (flags: JOBS.md):

```bash
#!/bin/bash
#SBATCH --job-name=proj
#SBATCH --partition=norm
#SBATCH --cpus-per-task=8
#SBATCH --mem=16g
#SBATCH --time=4:00:00
set -euo pipefail
export PYTHONNOUSERSITE=1
unset PYTHONHOME PYTHONPATH                # a python module in the submitting shell would break conda's Python
source /scratch/cluster_scratch/$USER/miniforge3/etc/profile.d/conda.sh
set +u; conda activate proj; set -u        # some packages' activation scripts read unset variables
# a venv instead of the two lines above:
#   source /etc/profile.d/modules.sh 2>/dev/null || true; module load python/3.12
#   source /scratch/cluster_scratch/$USER/envs/proj/bin/activate; unset PYTHONPATH
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1} OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1} MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
python ~/proj/run.py                       # sizes its pools from SLURM_CPUS_PER_TASK (next section)
```

## Threads and parallel workers

Ground rule 2 in SKILL.md sets the rule; these are the idioms. `SLURM_CPUS_PER_TASK` is unset without `--cpus-per-task` (JOBS.md (Flags and defaults)); then count the CPUs the job is bound to (Sept 2026: 1 in a 1-CPU job, where `os.cpu_count()` reports the node's 48).

```python
# in your Python code
import os
ncpu = int(os.environ.get("SLURM_CPUS_PER_TASK") or len(os.sched_getaffinity(0)))
# multiprocessing.Pool(ncpu); ProcessPoolExecutor(max_workers=ncpu); scikit-learn and joblib: n_jobs=ncpu
```

- BLAS and OpenMP libraries read their thread variables once, at import: export them in the job script (the list in ground rule 2, plus `NUMEXPR_NUM_THREADS`), or set `os.environ` before the first `import numpy`. A pool of `ncpu` workers gets 1 thread each (`threadpoolctl.threadpool_limits(1)` inside a worker caps BLAS libraries already loaded).

```r
# in your R code
ncpu <- as.integer(Sys.getenv("SLURM_CPUS_PER_TASK", "1"))
res <- parallel::mclapply(xs, f, mc.cores = ncpu)
BiocParallel::register(BiocParallel::MulticoreParam(workers = ncpu))
```

- `parallelly::availableCores()` (and `future::availableCores()`) reads Slurm's allocation itself.
- R's own BLAS threads (`OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`) multiply with `mclapply` workers: set them to 1 when you fork. Which BLAS the R modules link is unchecked (`Rscript -e 'sessionInfo()'`).
- In OnDemand sessions `SLURM_CPUS_PER_TASK` may be unset (ONDEMAND.md (Working inside a session)): size workers with the affinity count or `availableCores()`.

## R on FRCE

- **Versions.** `R` modules (Sept 2026): 4.3.2, 4.4.3, 4.4.3.nonconda, 4.4.3_torch, 4.5.0, and 4.5.2 (the default). `/usr/bin/R` is the OS's (version unchecked: `/usr/bin/R --version`): use a module. RStudio Server in OnDemand has its own "R version" menu ("Version of R to load"; 4.5.0 in the May 2025 screenshot).
- **Pin the minor version** in scripts and pick the same one in RStudio: personal libraries are per minor version, so a default that moves from 4.5 to 4.6 silently switches to an empty library (reinstall there with `renv::restore()` or the package list).
- Try `library(pkg)` before installing: much is installed centrally (listing: MODULES.md (Finding software)).
- Packages that compile against system libraries (GDAL, HDF5, and the like) need those headers: load their modules if they exist, or use conda-forge's R (`r-base`, `r-sf`) or a Rocker image (CONTAINERS.md).

A batch job for the user to submit (flags and hand-over: JOBS.md):

```bash
#!/bin/bash
#SBATCH --job-name=rjob
#SBATCH --partition=norm
#SBATCH --cpus-per-task=4
#SBATCH --mem=16g
#SBATCH --time=2:00:00
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true         # MODULES.md
module load R/4.5.2                                          # the version you tested
export R_LIBS=/scratch/cluster_scratch/$USER/R/4.5:$R_LIBS   # your library first (next section)
Rscript ~/proj/analysis.R
```

## R packages and libraries

The `R` modules set `R_LIBS` to their own read-only library (`module display R/4.5.2`, Sept 2026), and R searches `R_LIBS` before `R_LIBS_USER`. So `install.packages()` and `BiocManager::install()` target that library, which fails in Rscript with `unable to install packages` (interactive R offers a personal library instead), and central packages shadow newer versions you install. Put your library first in `R_LIBS`, on cluster scratch rather than R's default `~/R/x86_64-pc-linux-gnu-library/4.5` in /home, and create it first: R leaves out a library directory that doesn't exist.

```bash
# on the compute node (inside your session)
module load R/4.5.2
mkdir -p /scratch/cluster_scratch/$USER/R/4.5                   # one library per R minor version
export R_LIBS=/scratch/cluster_scratch/$USER/R/4.5:$R_LIBS
Rscript -e '.libPaths(); install.packages("data.table", repos = "https://cloud.r-project.org")'
```

- For OnDemand RStudio and other R sessions the user starts, `R_LIBS_USER=/scratch/cluster_scratch/${USER}/R/%v` in `~/.Renviron` names the same library (R expands `%v` to 4.5). An R module's `R_LIBS` still comes first there, so run `.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))` before installing. Editing `~/.Renviron` changes every R session the user starts, so only with their go-ahead.
- **Bioconductor:** `install.packages("BiocManager"); BiocManager::install(c("DESeq2", "edgeR"))`. BiocManager picks the release for the R version (R 4.5: 3.21 or 3.22; 3.23 needs R 4.6, Sept 2026), and `BiocManager::valid()` flags mismatched packages.
- **renv** per project: its package cache defaults to `~/.cache/R/renv`, so export `RENV_PATHS_ROOT=/scratch/cluster_scratch/$USER/renv` in jobs (or in `~/.Renviron`, with the user's go-ahead), and keep `renv.lock` with the code in /home or git.

## Jupyter kernels

OnDemand's Jupyter app lists its own kernels (ONDEMAND.md (Apps and their forms)) and, as Jupyter does by default, any registered in `~/.local/share/jupyter/kernels` (unchecked in the app: `jupyter kernelspec list` in a session terminal). A kernel spec is a small JSON file naming your env's interpreter; the env stays on cluster scratch. Jupyter modules (Sept 2026): `jupyter/6.5.2` (the default: MODULES.md (Loading and pinning versions)), `jupyter/7.1.3`, and `jupyterlab/4.4.2`.

```bash
# on the compute node (inside your session), with the env active
python -m pip install ipykernel
python -m ipykernel install --user --name proj --display-name "Python (proj)" \
    --env PYTHONNOUSERSITE 1 --env PYTHONHOME '' --env PYTHONPATH ''
jupyter kernelspec list
```

For your R (IRkernel calls `jupyter kernelspec`, so run this where a `jupyter` is on PATH, such as after `module load jupyter/7.1.3` or in a terminal inside the OnDemand session):

```r
# in R on the compute node (inside your session), with the R module you'll use loaded
install.packages("IRkernel")
IRkernel::installspec(name = "ir45", displayname = "R 4.5 (personal)")   # registers the R running this call
```

- A kernel starts its interpreter without activation, in the environment of the Jupyter server that launches it: pass activation variables with ipykernel's `--env NAME VALUE` (ipykernel 5.4 and later). A server started from a `jupyter` module hands its python module's `PYTHONHOME` and `PYTHONPATH` to every kernel, which stops a conda env's Python from starting; the empty values above neutralize them (Python ignores empty ones). IRkernel's `installspec()` (1.3.2, on CRAN) has no `env` argument, so an R kernel finds a cluster-scratch library through the `~/.Renviron` line above, an `"env"` entry for `R_LIBS_USER` in its `kernel.json`, or `.libPaths()` at the top of the notebook.
- `jupyter kernelspec remove -y proj` deletes a registration (without `-y` it waits for an answer), with the user's go-ahead. GPU kernels and frameworks: DEEP-LEARNING.md.

## Stale advice on the official pages

- [Python](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandScriptingLanguages/Python): usage is an unpinned `module load python` (3.13.1 in Sept 2026) → `module load python/3.12` (or 3.13), plus `unset PYTHONPATH` in a venv. Its build line has a stray quote (`--prefix=/mnt/nasapps/production/python/3.13'`), and its "install all modules that were built for the previous version" loop is a staff recipe: run by a user against a read-only module, pip drops every package into `~/.local`.
- [Jupyter Notebooks](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/JupyterNotebooks): "Jupyter/7.1.3 is available with iKernels for bash, python 3.6-3.12 and R" (3.6 is long end-of-life), but its by-hand route's bare `module load jupyter` gets an older default (MODULES.md (Loading and pinning versions)), and OnDemand offers one Python 3 kernel → pin `jupyter/7.1.3` and register your own env as a kernel.
- No FRCE page mentions conda, mamba, venv, or `~/.local`, or that the `python` modules set `PYTHONHOME`. AppDB lists only the oldest conda modules (`miniconda` 23.1.0, `mamba` 0.17.0), a 2020 development R (`/mnt/nasapps/development/R/4.0.2`), and `bioconductor` 3.12 (2021) → this file, the R modules, and `module avail`.
- FRCE calls Biowulf's docs "largely applicable", but Biowulf's python.html, conda.html, and R.html describe conda-based python modules that preset `PYTHONNOUSERSITE=1`, `mamba_install` into `/data/$USER/conda`, and a library at `/data/$USER/R/rhel8/%v` → none exist here; use the cluster-scratch equivalents above (FROM-BIOWULF.md).

## Going further

- FRCE: [Python](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandScriptingLanguages/Python) · [Available Compilers & Scripting Languages](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/AvailableCompilersScriptingLanguages) · [Jupyter Notebooks](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/JupyterNotebooks) · [Open OnDemand](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/OpenOnDemand) (RStudio's R versions) · AppDB [miniconda](https://appdb.ncifcrf.gov/software/miniconda) (NIH network).
- Biowulf docs (translate paths and module names first): [python.html#gotcha](https://hpc.nih.gov/apps/python.html#gotcha) · [conda.html#notes](https://hpc.nih.gov/docs/diy_installation/conda.html#notes) · [R.html#install](https://hpc.nih.gov/apps/R.html#install) · [jupyter.html#custom](https://hpc.nih.gov/apps/jupyter.html#custom).
- Python and pip: [site and the user site](https://docs.python.org/3/library/site.html) · [PYTHONHOME and PYTHONPATH](https://docs.python.org/3/using/cmdline.html#environment-variables) · [ipykernel: kernels for different environments](https://ipython.readthedocs.io/en/stable/install/kernel_install.html).
- conda: [activating environments in shell scripts](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#activating-environments-in-shell-scripts) · [envs_dirs](https://docs.conda.io/projects/conda/en/latest/user-guide/configuration/settings.html#envs-dirs-specify-environment-directories) · [Miniforge](https://github.com/conda-forge/miniforge) · [Anaconda terms of service](https://www.anaconda.com/legal/terms/terms-of-service).
- R: [.libPaths, R_LIBS, and R_LIBS_USER](https://stat.ethz.ch/R-manual/R-patched/library/base/html/libPaths.html) · [Startup and .Renviron](https://stat.ethz.ch/R-manual/R-patched/library/base/html/Startup.html) · [renv paths](https://rstudio.github.io/renv/reference/paths.html) · [Bioconductor install](https://bioconductor.org/install/) · [parallelly availableCores](https://parallelly.futureverse.org/reference/availableCores.html).
- Live: `module avail python R miniconda mamba jupyter`, `module display python/3.13`, `echo "$PYTHONHOME $PYTHONPATH $R_LIBS"`, `python3 -m site`, `python3 -m pip list --user`, `conda config --show-sources`, `Rscript -e '.libPaths()'`, `jupyter kernelspec list`.
