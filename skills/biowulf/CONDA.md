Personal conda/mamba installs on Biowulf: installing Miniforge with NIH's `mamba_install` module, activating it in a session, batch job, or swarm, creating environments and setting channels, and repairing broken setups (conda init in dotfiles, HTTP 403 errors, a full /home). Choosing conda over a module, container, or source build: MODULES.md. pip and the system python modules: PYTHON.md. R package libraries: R.md. A Jupyter kernel for an env: JUPYTER.md.

Table of contents

- [What differs on Biowulf](#what-differs-on-biowulf)
- [Install Miniforge (once)](#install-miniforge-once)
- [Activate in sessions, jobs, and swarms](#activate-in-sessions-jobs-and-swarms)
- [Create and manage environments](#create-and-manage-environments)
- [Fix a broken setup](#fix-a-broken-setup)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## What differs on Biowulf

- **Location.** The install and every env go under `/data`, by default `/data/$USER/conda` (envs in `envs/`, package cache in `pkgs/`). Never under `~`: NIH won't raise the /home quota for it, and `mamba_install` refuses home installs.
- **Where to run.** Inside the interactive session; NIH says conda operations "can be computationally intensive". The conda page also permits Helix, which is off-limits to you. NIH's install example uses `sinteractive --mem=20g --gres=lscratch:20`; if a solve is killed in a smaller session, ask the user for one that size.
- **No shell initialization.** Never run `conda init`, and never let an installer write a `# >>> conda initialize >>>` block or any activation into startup files. NIH warns that environments "can interfere with login or Graphical Sessions": conda's `dbus` on `PATH` can make TurboVNC fail to authenticate or leave a black desktop. Source an init file in each shell instead.
- **Channels.** Miniforge (recommended; includes mamba) uses conda-forge in place of Anaconda's `defaults` channels, which can fail with HTTP 403 (fix below). Add bioconda per env.
- **Not a module's conda.** Don't create envs with the `conda` that some python modules provide (which ones: PYTHON.md): their base isn't writable, so conda typically falls back to `~/.conda/envs`, in /home.

## Install Miniforge (once)

Look for an existing install and for init code in dotfiles first:

```bash
ls -d /data/$USER/*conda* /data/$USER/*forge* ~/*conda* ~/*forge* ~/.conda/envs ~/bin/myconda 2>/dev/null
grep -n 'conda initialize' ~/.bashrc ~/.bash_profile ~/.zshrc ~/.cshrc ~/.tcshrc 2>/dev/null
```

If `/data/$USER/conda` exists, use it rather than reinstalling (add `--init-only` if the init file is missing); an install under `~` is what fills /home ([Fix a broken setup](#fix-a-broken-setup)). Otherwise get the user's go-ahead before running `mamba_install`: it installs several GB under /data and, by default, also strips `conda init` code from all their shell dotfiles (`--no-cleanup` skips that part).

```bash
# on the compute node, after the user's go-ahead
export TMPDIR=/lscratch/$SLURM_JOB_ID   # needs --gres=lscratch; otherwise mkdir and use a dir under /data/$USER
module load mamba_install
mamba_install                           # installs to /data/$USER/conda, writes the init file ~/bin/myconda
source ~/bin/myconda && mamba --help
```

| Option | Effect |
|---|---|
| `DIR` (positional) | install there instead of `/data/$USER/conda` (e.g. a group directory) |
| `--init-file=FILE` | init file name (default `~/bin/myconda`) |
| `--init-only` / `--no-init` | only write the init file for an existing install / skip writing it |
| `--cleanup-only` / `--no-cleanup` | only strip `conda init` code from all shell dotfiles / leave dotfiles alone |
| `--shell=SHELL` | init code for bash, fish, tcsh, zsh, or xonsh (default: the login shell) |

- An existing init file is never overwritten: after installing somewhere new, pass a new `--init-file`, or the old file keeps activating the old install.
- Installed another way, e.g. by hand with `bash Miniforge3-Linux-x86_64.sh -p /data/$USER/conda -b` and `TMPDIR` on lscratch ([Option 2](https://hpc.nih.gov/docs/diy_installation/conda.html#example)): write the init file with `--init-only` (NIH's example: `mamba_install --init-only --shell=bash --init-file=~/bin/myminiconda /data/$USER/miniconda/`), then rerun the dotfile check.

## Activate in sessions, jobs, and swarms

```bash
source ~/bin/myconda        # makes conda and mamba usable in this shell; bare `source myconda` needs ~/bin on PATH
conda activate myenv        # envs live in /data/$USER/conda/envs/<name>
```

- No init file? `source /data/$USER/conda/etc/profile.d/conda.sh` does the same job.
- If your tool calls don't share one shell, activation is lost between calls: chain it (`source ~/bin/myconda && conda activate myenv && python run.py`) or call `/data/$USER/conda/envs/myenv/bin/PROGRAM` directly.
- A module loaded after activation can put its own python or tools ahead of the env's on `PATH` (MODULES.md): check `which python`.

A job script for the user to submit (JOBS.md):

```bash
#!/bin/bash
set -e
source ~/bin/myconda          # or: source /data/$USER/conda/etc/profile.d/conda.sh
conda activate proj
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-2}   # own envs set no default; use 1 if the script starts worker processes
export OPENBLAS_NUM_THREADS=$OMP_NUM_THREADS MKL_NUM_THREADS=$OMP_NUM_THREADS
python /data/$USER/proj/run.py
```

Swarm lines: call the env's binary by full path (`/data/$USER/conda/envs/proj/bin/python run.py s1`) or activate on the line (`source ~/bin/myconda && conda activate proj && python run.py s1`). If some subjobs fail to activate (a conda race NIH says "should not be happening any longer"), switch to full paths. Swarm options: SWARM.md.

## Create and manage environments

```bash
mamba create -n proj python=3.12 numpy scipy bioconda::pysam   # pin versions; CHANNEL::pkg picks the channel
conda activate proj
conda config --env --add channels bioconda       # per-env channels; the last one added goes on top,
conda config --env --add channels conda-forge    #   so conda-forge is searched first
conda config --env --set channel_priority strict
conda config --env --add pinned_packages 'blas=*=mkl'   # e.g. pin the BLAS flavor; quote specs with *
conda config --show-sources                      # every .condarc in effect
mamba install -q bedtools hisat2
conda info --envs
```

- Configure with `conda config`; mamba had no `config` command when NIH wrote its page.
- `pip install` inside an activated env is allowed, but pip "can sometimes cause problems when pip overwrites existing conda-installed packages": install conda packages first and pip packages last (more in PYTHON.md).
- GPU builds use build-string specs such as `mamba install 'tensorflow=*=cuda*'` (framework setup: DEEP-LEARNING.md).
- Upkeep, only with the user's go-ahead: `conda activate base && mamba update --all` updates the conda/mamba tooling in base; `mamba clean --all --yes` deletes cached tarballs from `/data/$USER/conda/pkgs`.

## Fix a broken setup

**conda init code in dotfiles** (Graphical Session or TurboVNC authentication fails, a black screen, login trouble):

1. Show the user what's there: `grep -n -A15 '>>> conda initialize' ~/.bashrc ~/.bash_profile ~/.zshrc ~/.cshrc 2>/dev/null`, plus any other `conda activate`, `source .../conda.sh`, or `module load` lines.
2. With their go-ahead, back up each affected file (`cp -p ~/.bashrc ~/.bashrc.bak`) and remove the blocks with `module load mamba_install && mamba_install --cleanup-only` (all shell dotfiles; documented for an install at `/data/$USER/conda`), or `conda init --reverse` from the sourced install, or by deleting from `# >>> conda initialize >>>` to `# <<< conda initialize <<<`.
3. Remove lines outside those blocks by hand, also with the user's OK; changes apply to new shells, so the user logs in again to confirm. For the TurboVNC symptom alone, removing the `dbus` package from the auto-activated env also works.

**HTTP 403 from repo.anaconda.com** (`RuntimeError: Multi-download failed. Reason: Transfer finalized, status: 403 [https://repo.anaconda.com/pkgs/...]`): add this to the install's own `.condarc`, `/data/$USER/conda/.condarc` (`$CONDA_ROOT/.condarc`, not `~/.condarc`), and make sure `~/.condarc` sets no channels or defaults (edit it only with the user's OK). NIH's alternative is the user's own Anaconda Professional license.

```yaml
channels:
  - conda-forge
  - bioconda
defaults: []
channel_priority: strict
```

**/home full because conda lives under `~`** (finding the culprit: STORAGE.md): a conda install can't simply be moved, because its paths are hard-coded. Install under /data with `mamba_install`, recreate the envs there (e.g. from `conda env export` files), then remove the old install once the user agrees.

**Base broken beyond repair.** NIH's "start from fresh" keeps the envs. Get the user's go-ahead first; `mamba_install` also runs the dotfile cleanup.

```bash
mv /data/$USER/conda /data/$USER/conda_backup
module load mamba_install && mamba_install
mv /data/$USER/conda_backup/envs /data/$USER/conda
source ~/bin/myconda && conda info --envs     # delete conda_backup only after the user confirms all works
```

## Stale advice on the official pages

- The page's `mamba_install -h` transcript gives the default location as `/data/apptest2/conda` → it is `/data/$USER/conda`. The help says it "Fails if the install directory exists already", while the page's step list says that step is skipped → never rerun it over an existing install; use `--init-only` or `--cleanup-only`.
- python.html recommends a private "mambaforge" → use Miniforge through `mamba_install`.
- The FAQ, workshop slides, and deep-learning pages link `apps/python.html#envs`, and python.html links `docs/diy_installation#conda`; neither anchor exists → use [the conda page](https://hpc.nih.gov/docs/diy_installation/conda.html) instead.
- The worked example (2022) builds `python=3.7` and `python=3.8` envs → both are end-of-life; choose current versions. Its `--show-sources` output puts the env `.condarc` under `/data/$USER/envs/project2/` (really `/data/$USER/conda/envs/project2/`), and its prose says "OpenBlas" while the command pins MKL.
- The 403 fix's `defaults: []` is not a documented conda key (conda's is `default_channels`) → what matters is that no `.condarc` lists `defaults` under `channels`; confirm with `conda config --show channels`.

## Going further

- https://hpc.nih.gov/docs/diy_installation/conda.html — NIH's conda page: pitfalls (#notes), `mamba_install` (#wrapper), worked setup including the manual Miniforge install (#example).
- https://hpc.nih.gov/docs/startup_files.html — what must stay out of `~/.bashrc`.
- https://hpc.nih.gov/docs/FAQ.html#home_directory — conda installs and caches filling /home.
- https://github.com/conda-forge/miniforge · https://mamba.readthedocs.io/en/latest/ · https://conda.io/docs/ · https://bioconda.github.io/ — upstream docs.
- Live: `module load mamba_install && mamba_install -h` (all options, including `--debug`), `conda config --show-sources`, `conda info --envs`, `mamba --help`.
