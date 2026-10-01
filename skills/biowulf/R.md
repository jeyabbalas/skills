Running R on Biowulf: module versions, the private package library, package-specific install notes, batch jobs and swarms, parallel and multithreaded R sized to the allocation, MPI, RStudio and Shiny. Tunnel mechanics: TUNNELING.md. The OnDemand portal: ACCESS.md. sbatch and sinteractive options: JOBS.md. Swarm options: SWARM.md. R kernels in Jupyter: JUPYTER.md.

Table of contents

- [Versions](#versions)
- [Package library](#package-library)
- [Package-specific notes](#package-specific-notes)
- [Batch jobs](#batch-jobs)
- [Swarms and Rswarm](#swarms-and-rswarm)
- [Parallel R](#parallel-r)
- [Implicit multithreading](#implicit-multithreading)
- [MPI](#mpi)
- [RStudio](#rstudio)
- [Shiny](#shiny)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Versions

- Minor-release modules (`R/4.5`, holding the newest 4.5.x patch) and patch-level ones (`R/4.5.2`). Default (Sept 2026): R 4.5.2, since Mar 18 2026; the default changed 7 times between Jan 2024 and Mar 2026. List with `module -r avail '^R$'`.
- Pin the minor version in every script (`module load R/4.5`): private libraries are per minor version, so a minor-version bump of the default silently switches to an empty library.
- R is built against MKL. Many packages are preinstalled (tidyverse loads with no install): try `library(pkg)` before installing.
- R sessions are not allowed on the login node or Helix, for the user as well: use an interactive session or a batch job.
- Old scripts break on newer R:
  - R ≥ 4.3: `&&`/`||` with a length > 1 operand is an error, `'length = 4' in coercion to 'logical(1)'`.
  - R ≥ 4.2: `if()`/`while()` with a length > 1 condition is an error.
  - R ≥ 4.0: `stringsAsFactors = FALSE` is the default.

## Package library

- `R_LIBS_USER` defaults to `/data/$USER/R/rhel8/%v` (`%v` = major.minor, e.g. `4.5`). Some R versions don't create it, and installs then target the central library and fail. Create it before starting R:

  ```bash
  mkdir -p /data/$USER/R/rhel8/4.5
  ```

- To relocate it, the page exports `R_LIBS_USER="/data/$USER/code/R/rhel8/%v"` from `~/.bash_profile`. Ask the user before editing that file, or export the variable in the job script instead.
- After a minor-version change, or to move a pre-Jun-2023 `~/R/<ver>/library`, reinstall. The page's snippet, with its `loc.lib=` typo corrected to `lib.loc=`:

  ```r
  # Get the list of installed packages in R version 4.4 using the current user's directory
  packages <- installed.packages(lib.loc=paste0("/data/", Sys.getenv("USER"), "/R/rhel8/4.4"))[,"Package"]
  # Identify packages that are not installed in R version 4.5
  toInstall <- setdiff(packages, installed.packages(lib.loc=paste0("/data/", Sys.getenv("USER"), "/R/rhel8/4.5/"))[,"Package"])
  BiocManager::install(toInstall)
  ```

  Comparing against the private library alone still lists packages that R 4.5 provides centrally. `BiocManager::install()` skips those only while the central copy is as new as the repository's; otherwise it installs a private copy, and private copies of central packages are what break after updates (next bullet). To skip them all, compare against `installed.packages()[,"Package"]`, which spans every library (what the typo did by accident).
- Updates to R or the central packages can break private packages, most often a private `rlang`; the errors name the private library path. Either reinstall every private package (the page's pacman recipe below, corrected to loop over `my.pkgs`) or, with the user's go-ahead, delete the private copy so the central one loads: `rm -rf /data/$USER/R/rhel8/4.5/rlang`.

  ```r
  my.lib <- .libPaths()[1]   # check first that this is the private library
  my.pkgs <- list.files(my.lib)
  library(pacman)
  for (p in my.pkgs) p_install(p, character.only=T, lib=my.lib)
  ```

- Per-project libraries: the page recommends renv (packrat is the older option). renv keeps its shared package cache under `~/.cache/R/renv` by default (renv behavior, not NIH docs), inside `/home`: point `RENV_PATHS_ROOT` at a `/data` path.

## Package-specific notes

- GitHub-only packages: staff "generally don't install any new github-only R packages any more". Install them into the private library, e.g. `R -q --no-save --no-restore -e 'devtools::install_github("dynverse/dyno")'`.
- AnnotationHub, ExperimentHub, and packages built on them fail with `No internet connection` until given the proxy: `setAnnotationHubOption("PROXY", Sys.getenv("http_proxy"))` (or `setExperimentHubOption`) in R, or, when a package uses a Hub indirectly, the environment variables `ANNOTATION_HUB_PROXY`/`EXPERIMENT_HUB_PROXY` set to the proxy (`$http_proxy`).
- h2o: the R client talks HTTP to its own Java server, which fails while proxy variables are set. `unset http_proxy` before starting R, then `h2o.init(ip='localhost', nthreads=future::availableCores(), max_mem_size='12g')`, keeping `max_mem_size` below `--mem` (the page used a 20 GB session).
- System libraries for compiled packages: R.html is silent. Building against modules: DEVELOPMENT.md; otherwise the user asks staff.

## Batch jobs

```bash
#!/bin/bash
set -e
module load R/4.5
Rscript /data/$USER/proj/analysis.R > /data/$USER/proj/analysis.out
# or: R --no-echo --no-restore --no-save < analysis.R > analysis.out
```

Give the user: `sbatch --cpus-per-task=8 --mem=16g --gres=lscratch:5 --time=4:00:00 rjob.sh`. Always request lscratch: R puts its temp files there automatically when the job has it (other tools need `TMPDIR` exported: JOBS.md), and the page recommends at least 1 GB plus what the code needs.

- Arguments: `commandArgs(trailingOnly=TRUE)` reads `Rscript simple.R this is a test`; with `R < file`, pass them after `--args`: `R --no-echo --no-restore --no-save --args 'this is a test' < simple.R`.
- `getopt` parses flags but can't mix them with positional arguments.

## Swarms and Rswarm

One `Rscript` per line:

```text
Rscript /data/$USER/R/R1 > /data/$USER/R/R1.out
Rscript /data/$USER/R/R2 > /data/$USER/R/R2.out
```

Give the user: `swarm -g 4 --gres=lscratch:1 --time=1:00:00 --module R/4.5 rjobs.swarm`, adding `-t N` when each line runs parallel code (options: SWARM.md).

- Replicates with different seeds: pass the seed on each line (`Rscript sim.R 24963`), the page's alternative to Rswarm. Don't derive it from `SLURM_ARRAY_TASK_ID`: lines bundled (`-b`) or packed (`-p`) into one subjob share it.
- `Rswarm` (staff utility) writes one R file per replicate from a template, plus a swarmfile. Template placeholders: `DUMX` (sims per file), `DUMY1`/`DUMY2` (output files), `DUMZ` (seed, read from a seed file).

```bash
# on the compute node; it asks "Is this correct (y or n)?" before writing, which your shell can't answer:
echo y | Rswarm --rfile=rfile.R --sfile=seedfile.txt --path=. --reps=2 --sims=50 --start=0 --ext1=.rds   # untested; check rfile.sw appeared
# the user submits the generated swarmfile, on the login node:
swarm --time=10 --partition=quick --module R/4.5 rfile.sw
```

## Parallel R

Get the CPU count from `parallelly::availableCores()` (R ≥ 4.0.3) or `future::availableCores()`; both read the Slurm allocation. The page's dependency-free `detectBatchCPUs()` tries `SLURM_CPUS_PER_TASK`, then `SLURM_JOB_CPUS_PER_NODE`, then falls back to 2. With `ncpus <- parallelly::availableCores()`:

| Package | Sized to the allocation |
|---|---|
| parallel | `mclapply(X, FUN, mc.cores = ncpus)`; `options(mc.cores = ncpus)` sets the default for parallel packages |
| foreach + doMC | `registerDoMC(cores = ncpus)` |
| foreach + doParallel | `cl <- makeCluster(ncpus); registerDoParallel(cl)` … `stopCluster(cl)` |
| BiocParallel | `register(MulticoreParam(workers = ncpus), default = TRUE)`, or a param object passed to each call |
| future (not in the NIH docs) | `plan(multicore, workers = ncpus)` or `plan(multisession, workers = ncpus)` |

- BiocParallel isn't Slurm-aware: its default backend uses `parallel::detectCores() - 2` workers, and the page shows 54 in a 2-CPU session. Check with `BiocParallel::registered()`.
- Memory grows with each worker: size `--mem` for all of them.
- Each worker's random-number state needs deliberate handling: see `?mcparallel` and the parallel package docs.
- Aim for 70–80% parallel efficiency and benchmark before scaling. On the page, `mclapply` on 12 CPUs ran only 2.8× faster (23% efficiency); a separate `mclapply` benchmark stayed above 70% only up to 6 CPUs; a foreach benchmark justified 32 CPUs only for problem sizes `i > 300`.

## Implicit multithreading

- The R module sets `OMP_NUM_THREADS` and `MKL_NUM_THREADS` to 1. To use BLAS threads (e.g. `crossprod()`), raise `OMP_NUM_THREADS` after `module load R`, and only when a benchmark shows a gain: most code doesn't benefit, and in the page's `crossprod` benchmark more than 8 threads was highly inefficient.
- Forked workers (parallel, doMC, `MulticoreParam`) each start `OMP_NUM_THREADS` threads; the page warns the total can also exceed the process-count ulimit and fail.
- `dist()` uses a separate, barely documented mechanism that ignores `OMP_NUM_THREADS`: `.Internal(setMaxNumMathThreads(nt)); .Internal(setNumMathThreads(nt))`.

## MPI

- Rmpi and pbdMPI are included (OpenMPI). The doMPI foreach backend works; the snow MPI cluster interface and MPI from an interactive R prompt don't.
- Run MPI code as a batch job (multinode rules: JOBS.md):

  ```bash
  #!/bin/bash
  module load R/4.5 || exit 1
  srun --mpi=pmix Rscript test1.r        # or: mpiexec Rscript test1.r
  ```

  Give the user: `sbatch --partition=multinode --constraint=x6140 --ntasks=4 --nodes=2 --ntasks-per-core=1 test1.sh` (one node type, always: JOBS.md).
- doMPI: don't specify a worker count, because doMPI hangs at shutdown when it has to spawn workers. Let `mpiexec`/`srun` start every rank, call `startMPIcluster()` early, run the foreach loops only on rank 0 (`mpi.comm.rank(comm=0) == 0`), and end with `closeCluster(cl); mpi.quit(save="no")`.

## RStudio

Every launch, browser and GUI step here is the user's.

1. **OnDemand RStudio Server** (recommended; no tunnel): the user opens the [RStudio Server form](https://hpcondemand.nih.gov/pun/sys/dashboard/batch_connect/sys/bc_nih_rstudio/session_contexts/new), picks resources and a startup working directory under `/data`, and launches. It uses one of the user's interactive-job slots (JOBS.md); portal login and errors: ACCESS.md.
2. **RStudio Server in an interactive session** started with lscratch and a tunnel, both required (`sinteractive --mem=10g --gres=lscratch:5 --tunnel`). On the node, `module load rstudio-server` (it loads an R module too; check `module list` against the library version in use), then `rstudio-server`, which prints `http://localhost:<port>/auth-sign-in?user=...&password=...`. Run it in the background and hand the user that URL plus the local tunnel command (TUNNELING.md). Each start creates a new random password, so "permission denied" means an old link.
3. **Desktop RStudio** needs a graphical display: an OnDemand Graphical Session (ACCESS.md). In its terminal the user runs `sinteractive --mem=10g --gres=lscratch:5`, then `module load rstudio R` and `rstudio &`.

Pitfalls:

- The working directory defaults to `/home`: `setwd("/data/...")`, or better an RStudio Project under `/data` (File → New Project → New Directory).
- R sessions persist only within one job: save to disk, or Session → Save Workspace As….
- Desktop: `XDG_RUNTIME_DIR not set` is a harmless warning. `libGL error: ...` or `qt.qpa.xcb: could not connect to display` means no graphical connection: use the Graphical Session.

## Shiny

- **OnDemand**: the user opens the [Shiny form](https://hpcondemand.nih.gov/pun/sys/dashboard/batch_connect/sys/bc_nih_shiny/session_contexts/new), gives an app directory ("with a .R file that loads shiny"), sets the walltime, launches, then clicks "Connect to Shiny". The page says this submits "a batch job", but OnDemand's FAQ says every app except the Graphical Session runs as a standard interactive job within the two-job limit (JOBS.md).
- **Tunnel**: needs a session with a tunnel (the page uses `sinteractive --cpus-per-task=2 --mem=6g --gres=lscratch:10 --tunnel`). The app listens on `$PORT1` on localhost; end the app script with:

  ```r
  port <- as.integer(Sys.getenv("PORT1", NA))
  if (is.na(port)) stop("PORT1 unset: start the session with sinteractive --tunnel")
  shinyApp(ui, server, options = list(port = port, launch.browser = FALSE, host = "127.0.0.1"))
  ```

  This replaces the page's `tryCatch(as.integer(Sys.getenv("PORT1", "none")), error = ...)`, whose error branch never fires: `as.integer("none")` only warns and returns `NA`. `Rscript app.R` prints `Listening on http://127.0.0.1:<port>`. Start it in the background and hand the user that URL plus the local tunnel command (TUNNELING.md, which also covers `$PORT1` missing from other logins to the node).
- An app serves one user: "a running shiny app cannot be shared with other users". Colleagues with access to the code each run their own copy.

## Stale advice on the official pages

- R.html's module listing and most examples use `R/3.4`, `R/3.5`, `R/4.1.0` or `R/4.2`, and the swarm example `--module R/3.5` → a current version (`module -r avail '^R$'`).
- R.html pitfall: the library is `/data/R/rhel8/%v`, `%v` a "two digit version" → `/data/$USER/R/rhel8/%v`, `%v` = major.minor.
- Reinstall snippet `loc.lib=` → `lib.loc=`; pacman snippet `p_install(pkgs, …)`, with only `my.pkgs` defined and a vector that `p_install()` rejects on R ≥ 4.2 (`the condition has length > 1`) → one `p_install()` per package in `my.pkgs` (both fixed above).
- BiocParallel `options(MulticoreParam = quote(MulticoreParam(...)))` makes `bpparam()` return the unevaluated call, so `bplapply()` without `BPPARAM` fails (`unable to find an inherited method ... BPPARAM = "call"`; BiocParallel 1.42–1.46; the page checks only `registered()`) → `register(...)` (fixed above).
- `rm -rf ~/R/4.2/library/rlang` and the pacman output's `/spin1/home/linux/user/R/4.1/library` show the pre-Jun-2023 home-directory layout → `/data/$USER/R/rhel8/<ver>/`.
- The Shiny example's port check never fires → fixed above.
- Rmpi: the live text says MPI code runs "from an sinteractive session with `mpiexec` or `srun --mpi=pmix`", but a commented-out block in the page source calls that "not currently true" → use batch jobs.
- The RStudio pages show `Rstudio 1.1.447` and `rstudio-server 2023.03.0-386` with R 4.2.2; the apps index lists `rstudio-server (2025.05.0-496)` and `Rstudio (2024.12.0-467)` (Sept 2026) → `module spider rstudio-server`.

## Going further

- https://hpc.nih.gov/apps/R.html — pitfalls (`#gotcha`), reinstalling (`#gotcha1`), library (`#install`), batch (`#sbatch`), `#swarm`, `#rswarm`, `#parallel`, `#biocparallel`, `#threading`, MPI (`#rmpi`), `#shiny`, h2o and dyno (`#pkgnotes`), changelog (`#changes`).
- https://hpc.nih.gov/apps/rstudio-server.html — RStudio Server via OnDemand or a tunnel.
- https://hpc.nih.gov/apps/RStudio.html — desktop RStudio in a Graphical Session.
- https://hpc.nih.gov/apps/shiny.html — the OnDemand Shiny app.
- https://hpc.nih.gov/development/MPI.html — MPI on Biowulf.
- Live: `module -r avail '^R$'`, `module spider rstudio-server`, `Rswarm --help`; in R, `.libPaths()`, `BiocParallel::registered()`, `?mcparallel`.
