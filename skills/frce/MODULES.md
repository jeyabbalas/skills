How FRCE provides installed software: Environment Modules 5.3.1 (not Biowulf's Lmod), finding and pinning modules and their surprising defaults, initializing `module` in batch jobs and non-interactive shells, personal modulefiles, the `frce/1.0` example scripts, and getting software that isn't installed, with the request process and licensing rules. Module commands are yours to run in the session; software requests are the user's to file (ground rules in SKILL.md). Python and R packages and environments: PYTHON-R.md. Containers: CONTAINERS.md. Building from source: DEVELOPMENT.md. Notes on particular applications: APPLICATIONS.md.

Table of contents

- [Environment Modules, not Lmod](#environment-modules-not-lmod)
- [Finding software](#finding-software)
- [Loading and pinning versions](#loading-and-pinning-versions)
- [Modules in batch jobs and scripts](#modules-in-batch-jobs-and-scripts)
- [Personal modulefiles](#personal-modulefiles)
- [The frce module and example scripts](#the-frce-module-and-example-scripts)
- [When software isn't installed](#when-software-isnt-installed)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Environment Modules, not Lmod

FRCE runs Environment Modules (Tcl) 5.3.1 (live, Sept 2026: `module --version`). Biowulf runs Lmod, and its commands, flags, and messages differ.

- `MODULEPATH` (Sept 2026, `echo $MODULEPATH`) holds `/mnt/nasapps/modules-5.3.1/modulefiles`, where every module lives, and `/etc/scl/modulefiles` (listed twice; it contributes nothing). The older `/mnt/nasapps/modules/modulefiles` tree that the Environment Modules page shows is not on it. Installs live in `/mnt/nasapps/production/<name>/<version>`, mounted read-only.
- `module` prints to stdout only if it was initialized in a terminal session; in batch jobs and other non-interactive shells its output can stay on stderr, so pipe it with `2>&1` (`module -t avail 2>&1 | grep ...`).
- Loads print FRCE's own `[+] Loading NAME VERSION` lines; they are not errors.
- `ml` is on by default in Modules 5 but unchecked here (`type ml`): write `module` in scripts.

| Biowulf habit (Lmod) | On FRCE (Environment Modules 5.3.1) |
|---|---|
| `module spider bed` | `module avail -C bed` (substring) or `module avail bed` (names starting with "bed"). `spider` arrived in Modules 5.6, so here it fails: `ERROR: Invalid command 'spider'` |
| `module spider NAME/VERSION` | `module whatis NAME/VERSION`, `module help NAME/VERSION`, `module display NAME/VERSION` |
| `module keyword WORD` | the same, or `module search WORD` (both search `module-whatis` text) |
| `module -r avail '^R$'` | no regex option: `module -t avail 2>&1 \| grep -E '^R/'` |
| `(D)` marks in `module avail` | `module avail -d NAME` (the effective default), `module avail -L NAME` (the highest version) |
| `module load use.own` | `module use ~/modulefiles` (prepends; `-a` appends) |
| Lua modulefiles (`.lua`) | Tcl only, first line `#%Module` |

## Finding software

```bash
# on the compute node (inside your session)
module -t avail                                   # every module, one per line
module avail -C bwa                               # substring, case-insensitive
module -t avail 2>&1 | grep -E '^R/'              # one exact name: `module avail R` also lists RSEM, relion, ...
module avail -d samtools; module avail -L samtools   # the default version; the highest version
module search alignment                           # searches the one-line descriptions
module whatis samtools; module help samtools
module display samtools/1.21                      # paths and variables it sets, modules it loads
module is-avail samtools/1.21 && echo present     # exit status only, for scripts
```

Language packages live inside the language installs, per the [Scientific Software](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware) page: `pip3 list` after loading a Python module, and `R-packages`, a local script, after loading an R module (`command -v R-packages`). For Perl, check a module with `perl -MSome::Module -le 'print Some::Module->VERSION'`, not the page's `cpan -l` ([Stale advice](#stale-advice-on-the-official-pages)).

**Not everything is a module** (Sept 2026): the OS puts `git`, `python3`, `R`/`Rscript`, `java`, GNU `parallel`, `tmux`, `screen`, `vglrun`, and `apptainer` in /usr/bin. Prefer the pinned modules for Python, R, and Java (PYTHON-R.md; DEVELOPMENT.md (Other languages)) and the system Apptainer (CONTAINERS.md). `git-lfs` is neither a module nor installed (conda-forge packages it). Rust and Clang: DEVELOPMENT.md (Compilers; Other languages).

**AppDB** (https://appdb.ncifcrf.gov/) adds what `module avail` can't:

- `/browseSoftware` tabulates development and production versions with update dates; each `/software/<Name>` page gives the install Location and a "How to run" line. Copy that line exactly: module names can differ in case from the page name (the AlphaCryo4d page says `module load AlphaCryo4D/0.1.1`).
- `/softVersion` shows which version was installed on a given date, for reproducing old results.
- It centers on bioinformatics (no gcc, Python, CUDA, Go, Java, or Apptainer entries) and lags the modules (its openmpi is 4.1.4, its MATLAB R2022b): `module avail` is the ground truth.
- **Production vs development.** Modules load production installs. Development builds (`/mnt/nasapps/development/...`, `/bioinfoA/...`) are ABCS staging and legacy installs, run by full path or conda activation; "any production workflows should use the software available in production" (AppDB home page).

## Loading and pinning versions

`module load NAME` gives the default version: one staff set explicitly (marked `(default)` in `module -t avail`), or else the highest in Tcl dictionary order, which compares numbers numerically (1.21 beats 1.16.1) and sorts letters after digits. Defaults move when staff install or retire versions (samtools: 1.16.1 in QuickStart's transcript, 1.22.1 now), and some are traps (Sept 2026, `module avail -d NAME`):

| Bare `module load` | Gives | Instead |
|---|---|---|
| `cuda` | `cuda/cuda10.0`, the oldest CUDA | a pinned version: DEVELOPMENT.md (CUDA and cuDNN) |
| `cudnn` | `cudnn/9.14.0-cuda13`, mismatched with bare `cuda` | the build for your CUDA |
| `frce` | `frce/benchmarks` (convenience scripts) | `frce/1.0` |
| `alphafold` | `alphafold/2.3.2_conda`, set by staff; 3.0.1 exists | APPLICATIONS.md (Structural biology and AlphaFold) |
| `java` | `java/1.8.0`, set by staff | `java/17` or `java/21` |
| `jupyter` | `jupyter/6.5.2`, set by staff; it loads `python/3.11` | `jupyter/7.1.3` (PYTHON-R.md (Jupyter kernels)) |

Pin `NAME/VERSION` in anything that must reproduce. Version specifiers (Modules 5.3.1 defaults, which FRCE's `gcc@14` example relies on; `module config` would show a site override):

| You write | You get |
|---|---|
| `gcc/14.3.0` or `gcc@14.3.0` | exactly that version |
| `gcc@14` or `gcc/14` | a 14.x.y: the default if it is one, else the highest ("usually" the highest, as FRCE's page puts it) |
| `gcc@latest` | the highest version, even when staff set another default |
| `gcc@12:14`, `gcc@12:`, `gcc@:13` | the default if it falls in the (inclusive) range, else the highest in range |

- `load` is case-sensitive although `avail` is not: `module load STAR` works, `module load star` fails with `Unable to locate a modulefile for 'star'`. Copy names from `module -t avail`.
- A failed `module load` returns exit status 1; without `set -e` or `|| exit 1`, a job script runs on without the software.
- In your own tool calls, each call may start a fresh shell, so loads don't carry over: chain them (`module load samtools/1.21 && samtools --version`).

## Modules in batch jobs and scripts

Login shells set up `module` through `/etc/profile.d/modules.sh` (Sept 2026: present on the login node, and `module` works in `bash -l` jobs on compute nodes). A batch job usually inherits `module` from the submitting shell (sbatch exports the environment by default), but shells started other ways may lack it: `ssh host cmd`, cron, HPC API jobs (JOBS.md (Submitting without logging in)), wrappers that clear the environment, and your own non-interactive tool calls. `module: command not found` means the shell was never initialized. Start every script that calls `module` like this:

```bash
#!/bin/bash
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true   # FRCE staff's line; harmless when `module` was inherited
module purge                          # drop whatever the submitting shell had loaded
module load samtools/1.21 bwa/0.7.17  # pinned (versions here are examples)
module -t list 2>&1                   # records exact versions in the job log
```

- FRCE staff use this exact line under `set -euo pipefail` (Ollama endpoint page, 2026). Login shells run Modules from `/mnt/nasapps/modules-5.3.1`, so its `init/bash` is the likely direct init script (unverified: `ls /mnt/nasapps/modules-5.3.1/init`). Never source `/mnt/nasapps/modules/init/bash`, as a 2022 third-party pipeline did: it belongs to the old tree, off `MODULEPATH`.
- FRCE's Jupyter templates use a login-shell shebang (`#! /usr/bin/bash -l`) instead. That defines `module` too, but it also runs the user's `~/.bash_profile` and `~/.bashrc`, whose loads and conda setup then leak into the job.
- `module purge` makes the job independent of what the user had loaded when they ran `sbatch`, but it can't undo an activated conda env or PATH edits exported from that shell (PYTHON-R.md). Login shells load no modules of their own (Sept 2026: no `/mnt/nasapps/production` entries on a fresh login PATH), so the purge drops only the user's.

## Personal modulefiles

Write one for software you built (DEVELOPMENT.md (Build systems and install prefixes)) or to bundle a set of loads. Keep modulefiles in `~/modulefiles/NAME/VERSION` (tiny, and home has snapshots) and the software on cluster scratch or a group share. `mytool` is a placeholder:

```tcl
#%Module1.0
# ~/modulefiles/mytool/1.2.3
set prefix /scratch/cluster_scratch/$env(USER)/sw/mytool/1.2.3
module-whatis "mytool 1.2.3, built from source"
prepend-path PATH    $prefix/bin
prepend-path MANPATH $prefix/share/man
# prepend-path LD_LIBRARY_PATH $prefix/lib64   ;# only if its shared libraries aren't found through rpath
# module load gcc/14.3.0                        ;# the compiler runtime it was built with, if it needs one
```

```bash
# on the compute node (inside your session), or near the top of a job script
module use ~/modulefiles                      # once per shell or job; never from ~/.bashrc
module load mytool/1.2.3 && command -v mytool
module load /mnt/SHARE/modulefiles/tool.tcl   # a modulefile can also be loaded by path (SHARE is a placeholder)
```

- A group can keep shared modulefiles in its share: `module use /mnt/<share>/modulefiles`.

## The frce module and example scripts

FRCE staff ship Slurm templates at `/mnt/nasapps/production/frce/1.0/share/FRCE_EXAMPLES/slurm` ([Slurm Utilities](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/SlurmUtilities)). `module load frce/1.0` provides `sbatch_templates.sh` (in `/mnt/nasapps/production/frce/1.0/bin`), which copies them into `./FRCE_EXAMPLES/slurm/`. The templates (Sept 2026):

| Template | What it does |
|---|---|
| `jupyter_oel8.sh` (May 2024), and `jupyter.sh`, a link to it | loads `jupyter/7.1.3`, starts a notebook on the node's address, and emails the tunnel command |
| `jupyter_centos.sh` (2023) | the same with CentOS-era modules (`python/3.6.8`, `R/4.1.2`, `jupyter/py36`) that no longer exist |
| `vnc.sh` (2023) | starts `vncserver` (after a one-time `vncpasswd`) and emails the tunnel command |
| `cellranger.sh` (2022) | runs an unpinned `cellranger count` on another user's hard-coded paths and emails a tunnel to its web UI |

Read them in place rather than copying, and fix them before the user submits one:

- No `--partition`, `--time`, `--cpus-per-task`, or `--mem`: they get norm's defaults (JOBS.md (Flags and defaults)), and each ends in `while :; do sleep 1h; done`, which holds the allocation until `scancel` or the time limit. Add the directives with a realistic `--time`, and have the user cancel the job when done.
- They email the tunnel command (through the login node) to `$USER@mail.nih.gov` or `$USER@nih.gov`. `jupyter_oel8.sh` waits with no timeout for "10.156" in its log, then takes the URL from a line containing "127", and its `if [[ $0 ]]` failure branch can never run.
- OnDemand's Jupyter and desktop apps (ONDEMAND.md) or a tunnel set up by hand (INTERACTIVE.md (Tunnels to notebooks and web apps)) are simpler.

```bash
# on the compute node (inside your session)
module display frce/1.0
ls -l /mnt/nasapps/production/frce/1.0/share/FRCE_EXAMPLES/slurm
sed -n 1,80p /mnt/nasapps/production/frce/1.0/share/FRCE_EXAMPLES/slurm/jupyter_oel8.sh
```

## When software isn't installed

Work down the list and stop at the first option that fits:

1. **Search harder.** `module avail -C WORD`, `module search WORD`, AppDB (development builds are there too), the packages inside the Python and R modules, and pipeline installs the user can read, such as CCBR's (WORKFLOWS.md).
2. **An environment** under `/scratch/cluster_scratch/$USER`: pip, conda (bioconda), or R packages (PYTHON-R.md).
3. **A container** (CONTAINERS.md): an existing Docker or BioContainers image, or software built for another OS, which Apptainer lets you run although it "cannot run natively on OEL8".
4. **A source build** into cluster scratch plus a personal modulefile (DEVELOPMENT.md (Build systems and install prefixes), which also covers the `spack` module; above).
5. **A central install.** The user files the ServiceNow software request (form: ACCESS.md (Support and requests)). Worth it for software several people need, or anything licensed. Give the name, version, homepage, license, and who needs it.

What FRCE installs ([Software Request](https://ncifrederick.cancer.gov/staff/FRCE/Support/SoftwareRequest)): "In general, any open source or source available software", except a package "written specifically for a different Linux distribution or for a different version of the OS" or one with "restrictive license terms making it unsuitable for a shared environment". Bioinformatics requests go to ABCS's DSSB team, which installs, validates, and tests in development, then files a change request for production; EIT handles other software and every production install (AppDB).

Licensing ([Software Licenses](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandScriptingLanguages0)):

| License | On FRCE |
|---|---|
| Open source (OSI-approved) | installed "with no other approvals"; "the large majority" of packages |
| Academic | FNLCR "generally meets the definition"; edge cases need the owner's approval; some are "granted only to specific users and/or groups" (cryoSPARC, MAJIQ, ResMap, bcl2fastq2) |
| Self-written | "evaluated on a case-by-case basis" (ViennaRNA, NAMD) |
| Commercial | "prohibited unless a license is purchased"; use may be limited to the groups that own it (MATLAB, Schrödinger, Amber, Intel compilers) |
| Unlicensed | only the author may use it; "No unlicensed software packages have been installed" |

The requester obtains any license, and since jobs run on any node, "the license should use a network license manager and not be node-locked".

## Stale advice on the official pages

- [Environment Modules](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/EnvironmentModules): its transcripts come from the old `/mnt/nasapps/modules/modulefiles` tree, now off `MODULEPATH`, with 2018–2019 versions such as `gatk/4.0.12.0` and `STAR/2.7.3a` (both gone) and `bamtools/2.27.1` (a bedtools version; bamtools is 2.5.2); only the `gcc@14` example is recent → `module avail NAME`.
- The same page links http://modules.sourceforge.net/ (now envmodules.io) without naming a version, and FRCE calls Biowulf's docs "largely applicable" → Biowulf's modules.html describes Lmod (`spider`, `-r`, `(D)`, Lua, `use.own`); translate with the table above and read the 5.3.1 manual.
- The same page says only that "the modules command is automatically loaded for all interactive sessions" → the init line in [Modules in batch jobs and scripts](#modules-in-batch-jobs-and-scripts).
- QuickStart's example loads samtools unpinned → pin versions.
- The Scientific Software page's request "form" link (`/fredi/FRCE/Requests/SoftwareRequest`) returns 404 → the Software Request page (form in ACCESS.md).
- The same page lists Perl modules with `cpan -l`, but a first `cpan` run sets itself up in `~/perl5` and `~/.bashrc` (DEVELOPMENT.md (Other languages)) → the `perl -M` check in [Finding software](#finding-software).
- The licenses page's "OCI-approved" means OSI-approved (Open Source Initiative), and "majiiq" is MAJIQ. It says source-available software "does not mean that it is necessarily usable", while the Software Request page says it "can be installed" → expect a license review for anything not OSI-licensed.
- [Slurm Utilities](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/SlurmUtilities) and [Jupyter Notebooks](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/JupyterNotebooks) offer the FRCE_EXAMPLES templates as ready to submit → they lack resource directives and never end on their own ([The frce module and example scripts](#the-frce-module-and-example-scripts)).

## Going further

- FRCE: [Environment Modules](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/EnvironmentModules) · [Available Applications](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/AvailableApplications) · [Scientific Software](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware) · [Software Request](https://ncifrederick.cancer.gov/staff/FRCE/Support/SoftwareRequest) · [Software Licenses](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandScriptingLanguages0) · [Slurm Utilities](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/SlurmUtilities) (example scripts).
- AppDB (NIH network): [Browse](https://appdb.ncifcrf.gov/browseSoftware) · [Query Version](https://appdb.ncifcrf.gov/softVersion).
- Environment Modules 5.3.1 manual: [module](https://modules.readthedocs.io/en/v5.3.1/module.html) — [avail](https://modules.readthedocs.io/en/v5.3.1/module.html#subcmd-avail), [version specifiers](https://modules.readthedocs.io/en/v5.3.1/module.html#advanced-module-version-specifiers), [case matching](https://modules.readthedocs.io/en/v5.3.1/module.html#envvar-MODULES_ICASE); [modulefile](https://modules.readthedocs.io/en/v5.3.1/modulefile.html) — [how defaults are chosen](https://modules.readthedocs.io/en/v5.3.1/modulefile.html#locating-modulefiles); [NEWS, 5.6.0](https://modules.readthedocs.io/en/latest/NEWS.html#modules-5-6-0-2025-07-31) (`spider` added, after FRCE's version).
- Biowulf docs, written for Lmod (translate with the table above): [modules.html#personal](https://hpc.nih.gov/apps/modules.html#personal).
- Live: `module --version`, `echo $MODULEPATH`, `module config`, `module avail -d NAME`, `module help NAME`, `module display NAME`, `type ml`.
