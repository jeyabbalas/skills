How Biowulf provides installed software through Lmod environment modules: finding and loading modules, pinning versions in scripts, fixing "module or command not found", writing personal or group modulefiles, and deciding how to install software that isn't there. Conda environments are covered in CONDA.md, containers in CONTAINERS.md, source builds in DEVELOPMENT.md, and Python or R package installs in PYTHON.md and R.md.

Table of contents

- [Find and load modules](#find-and-load-modules)
- [Load order and PATH clashes](#load-order-and-path-clashes)
- [Modules in scripts and jobs](#modules-in-scripts-and-jobs)
- [When a module or command isn't found](#when-a-module-or-command-isnt-found)
- [Personal and shared modulefiles](#personal-and-shared-modulefiles)
- [Choosing how to install software](#choosing-how-to-install-software)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Find and load modules

Scientific applications are on `PATH` only after `module load` (modulefiles live in `/usr/local/lmod/modulefiles`, install trees in `/usr/local/apps`). Listing and search commands are read-only; run them freely in the session.

```bash
module spider bed                  # case-insensitive substring search of module names
module spider bedtools/VERSION     # one version: description and the exact load line
module -r spider '^R$'             # regex match (-r also works with avail and list)
module -t avail python             # terse, one per line: easiest to parse
module -d avail                    # defaults only (same as: ml -d av)
module keyword alignment           # also searches module descriptions
module display samtools            # what loading would change (Lua), without loading it
module load NAME/VERSION NAME2/VERSION
module list
module unload NAME; module purge   # purge unloads everything
```

- Copy exact names from `spider`. They are case-sensitive and irregular: `R`, `GATK`, `CUDA`; extra variant levels (`fftw/3.3.4/gnu`, `openmpi/1.8.1/gnu-eth`); hash or date versions (`HLA-PRG-LA/f0833ed`, `trinity/r20140717`); aliases (`julia` = `julialang`).
- `(D)` in `module avail` output marks the default. Defaults move as new versions are installed, so pin `NAME/VERSION` in anything that must reproduce.
- Loading a second version of a loaded module swaps it ("reloaded with a version change"); `module switch NAME NAME/VERSION` does the same explicitly.
- Modules that pull in dependencies announce them (`[+] Loading python 3.10 ...`); `module -q load` silences this in large batch runs.
- Lmod normally prints listings to stderr, so add `2>&1` before a pipe: `module -t avail 2>&1 | grep -i blast`.
- If your tool calls don't share one shell, loads don't carry over between calls: chain them (`module load NAME/VERSION && cmd`).

## Load order and PATH clashes

NIH's best-practice list: "Load only the minimum environment modules necessary ... Modules can sometimes scramble paths required, especially for Python-, Perl-, and R-dependent applications."

- The `python` modules are conda environments that bundle command-line tools (e.g. samtools, bcftools): loading `python` after `samtools` puts python's samtools first on `PATH`.
- Some application modules load their own Python or Java as a dependency, which can shadow a version you loaded or activated.
- Diagnose with `module list` and `which -a TOOL`. Fix by loading the module whose tool you need last, dropping modules you don't need, or calling the tool by the full path `module display` shows.

## Modules in scripts and jobs

```bash
#!/bin/bash
set -e                                  # without it, a failed load doesn't stop the script
module use --prepend ~/modulefiles      # only if the job needs personal modulefiles
module -q load NAME/VERSION NAME2/VERSION
```

- A failed `module load` (typo, retired version) doesn't stop bash: the script runs on and the job can end `COMPLETED`. Use `set -e`, or `module load NAME/VERSION || exit 1` (exit-code handling: JOBS.md).
- Load modules in the script itself. The submitting shell's environment is exported to the job, so leaning on whatever the user had loaded makes results depend on their shell at submit time.
- tcsh job scripts submitted from a bash login don't inherit the `module` function: add `source /etc/profile.d/modules.csh` before the first `module` command.
- swarm: `--module NAME/VERSION,NAME2/VERSION` loads modules for every subjob; the alternative is `module load` on each line (SWARM.md).

## When a module or command isn't found

| Symptom | Cause and fix |
|---|---|
| `command not found` for an application | Its module isn't loaded: `module spider WORD`, then load the exact name. |
| `module load` reports an unknown module | Wrong case, spelling, or version, or the version was retired: `module spider WORD`. |
| `module avail` shows almost no scientific apps | Possibly Helix, which has none: rerun SKILL.md's where-am-I check. |
| `module: command not found` in a tcsh script | `source /etc/profile.d/modules.csh` first. |
| `module: command not found` in bash | A syntax error in `~/.bashrc` can remove the `module` function (NIH FAQ): show the user, who reverts the file or asks staff. In a non-interactive shell that never received the function, find the bash counterpart of `modules.csh` in `/etc/profile.d/` and source it (by analogy; undocumented). |
| Module loads, but the wrong tool version runs | PATH clash: see [Load order and PATH clashes](#load-order-and-path-clashes). |
| Job `COMPLETED` although a program never ran | A failed load without `set -e`: see [Modules in scripts and jobs](#modules-in-scripts-and-jobs). |

## Personal and shared modulefiles

Write one for software built into `/data/$USER/opt/NAME/VERSION` (DEVELOPMENT.md), or to load several modules under one name. Modulefiles are tiny, so `~/modulefiles` in /home is fine.

`~/modulefiles/NAME/VERSION.lua`, NIH's workshop template. `myModuleFullName()` returns `NAME/VERSION`, so the path matches the install prefix:

```lua
local basedir = "/data/" .. os.getenv("USER") .. "/opt/" .. myModuleFullName()

prepend_path("PATH", basedir .. "/bin")
prepend_path("MANPATH", basedir .. "/share/man")
-- prepend_path("LD_LIBRARY_PATH", basedir .. "/lib64")   -- if it installs shared libraries (lib or lib64)
-- load("DEP/VERSION")   -- runtime dependency, e.g. the gcc or CUDA module it was built with; Lmod unloads it too
```

```bash
module use --prepend ~/modulefiles      # personal modules win name clashes; --append lets system ones win
module load NAME/VERSION && which PROGRAM
```

- Run `module use` in each session or job script. The workshop slides suggest adding it to `~/.bashrc`; don't (ground rules in SKILL.md).
- `module load use.own` (a system module) also exposes `~/modulefiles`, listed above the system tree. `module purge` may drop it along with everything else; load it again after a purge.
- A modulefile may load the modules it requires (Tcl `module load X`, Lua `load("X")`), and Lmod reverses those loads on `module unload`. It sets search paths (`PATH`, `MANPATH`, `LD_LIBRARY_PATH`, `PERL5LIB`, `PYTHONPATH`) for its own application only, never for the modules it loads.
- Templates: read one with `module display NAME`, or copy from `/usr/local/lmod/modulefiles`. Files ending `.lua` are Lua; files without an extension that start with `#%Module` are Tcl. Tcl/Lua/shell equivalents: [modules_advanced](https://hpc.nih.gov/apps/modules_advanced.html).
- Group-shared modules ([modules#shared](https://hpc.nih.gov/apps/modules.html#shared)); members without access to the group directory can't see them:

```bash
mkdir -p /data/GROUP/modulefiles        # once; the group's modulefiles go here
mkdir -p ~/modulefiles && ln -s /data/GROUP/modulefiles ~/modulefiles/shared   # each member
module load use.own                     # they appear as shared/NAME/VERSION
```

## Choosing how to install software

Central installs cover most needs; personal installs give fixed versions or software staff don't provide. Language package managers (pip, cpan, gem) can't install requirements written in other languages (common for pipelines and for interfaces to compiled libraries); use conda or a container for those. Package specifics: pip in PYTHON.md, R packages in R.md, Julia, Perl, and other languages in DEVELOPMENT.md.

Try, in order:

1. **An existing module.** `module spider WORD`, the apps index (SKILL.md), and the packages already installed with the `python` and `R` modules (PYTHON.md, R.md).
2. **A conda environment** (CONDA.md). Anything on conda-forge or bioconda; needs no privileges; the usual route to pinned versions.
3. **A container** (CONTAINERS.md). An existing Docker/OCI image, software that needs OS packages (apt/yum/dnf need root, so they're only usable when building a container), or when long-term replicability and portability matter, which NIH recommends considering for any personal install. Only Singularity/Apptainer run on Biowulf; Docker images are converted.
4. **A source build** (DEVELOPMENT.md) into `/data/$USER/opt/NAME/VERSION`, plus a personal modulefile (above).
5. **Ask staff.** The user can request a central install. Staff maintain software likely to be useful to "more than one or two people" (not obscure, unpublished, or obsolete) that runs without elevated privileges such as write access to its install directory, and they help with personal installs that resist the steps above.

## Stale advice on the official pages

- modules.html examples (gromacs 4.5, `java/1.7.0 is loaded`, `python/2.7.8`, R 3.x, openmpi 1.8.1) date from about 2014–2018 → current modules print `[+] Loading ...`; check versions with `module -t avail NAME`.
- modules.html suggests `alias ml="module -d avail"` → it shadows Lmod's `ml` shorthand that other NIH pages use (`ml mamba_install`); don't add it.
- modules.html (titled "Biowulf & Helix") says `.bashrc` environment setups "will continue to work" → Helix has no scientific apps, and the startup-files page forbids pre-loading modules.
- Name-clash priority: #personal says the system module wins, #shared says the personal one does → it depends on `--append` versus `--prepend` or `use.own`; confirm with `module list` and `which`.
- modules_advanced.html puts its nested module in `/home/user/privatemodules/` yet loads it through `use.own` → put modulefiles in `~/modulefiles`.
- The #shared example mixes `/data/DBCImaging` with `/data/DCBImaging` and loads `3.2.4` but lists `3.6.1` → typos; use one group path.

## Going further

- https://hpc.nih.gov/apps/modules.html — Lmod on Biowulf: listing (#avail), personal (#personal) and shared (#shared) modulefiles, modules in scripts (#scripts).
- https://hpc.nih.gov/apps/modules_advanced.html — Tcl/Lua/shell table, nested modules (#nested), modulefile best practice.
- https://hpc.nih.gov/docs/diy_installation/ — personal installation options: package managers, personal modulefiles, manual builds.
- https://hpc.nih.gov/training/handouts/managing-personal-software.pdf — workshop slides: autotools and CMake builds ending in a Lua modulefile.
- https://hpc.nih.gov/docs/FAQ.html#module — "'module load xxx' fails"; https://hpc.nih.gov/docs/FAQ.html#best_practices — load the minimum modules.
- https://lmod.readthedocs.io/ — Lmod manual; https://lmod.readthedocs.io/en/latest/060_locating.html — how defaults are chosen.
- Live: `module spider NAME/VERSION`, `module help NAME`, `module display NAME`, `module --help`.
