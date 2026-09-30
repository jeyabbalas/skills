Snakemake, Nextflow (nf-core included), and CCBR's pipelines on FRCE: when a workflow manager is the right tool, where its driver runs and who starts it, FRCE profiles for both managers, and the CCBR pipelines installed on an FRCE group share. You write the workflow, profile, config, and driver script, and you may run dry runs and local-executor tests inside your own allocation; every run that submits jobs, the driver job included, is the user's to start (ground rules in SKILL.md). Batch flags, partitions, GPU requests, and temporary files: JOBS.md. Per-sample commands with no dependency graph: ARRAYS.md. Container caches and binds: CONTAINERS.md. Internet access for pulls: TRANSFER.md (Downloads on the cluster).

Table of contents

- [Choosing an approach](#choosing-an-approach)
- [Running the driver](#running-the-driver)
- [Snakemake](#snakemake)
- [Nextflow](#nextflow)
- [CCBR pipelines on FRCE](#ccbr-pipelines-on-frce)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Choosing an approach

| The work | Use | Who starts it |
|---|---|---|
| Independent commands, one per sample or file | a job array, not a workflow manager (ARRAYS.md) | the user |
| A multi-step pipeline at test size (a test profile, two samples) | Snakemake or Nextflow with the local executor, inside your session | you |
| The same pipeline at full size | the Slurm executor, from a driver job ([Running the driver](#running-the-driver)) | the user |
| RNA-seq, exome, tRNA, or circRNA data that a CCBR pipeline covers | [CCBR pipelines on FRCE](#ccbr-pipelines-on-frce) | the user (you: setup and dry runs) |

- No FRCE profile exists for either manager (Sept 2026). FRCE's own pages show only a one-job Snakemake script and a local Nextflow hello-world ([Stale advice](#stale-advice-on-the-official-pages)), [nf-core/configs](https://github.com/nf-core/configs) has no FRCE or NCI-Frederick entry, and the `frce.config` files in CCBR's Nextflow repos are unfinished. Use the templates below.
- These submit jobs: `snakemake --executor slurm` or `cluster-generic`, `snakemake --profile frce`, `nextflow run` with any config that sets `executor = 'slurm'` (such as `-c frce.config`), and a CCBR pipeline's run step (`--mode slurm` without `--dry-run`, `--runmode run`, `-m=run`). Dry runs (`snakemake -n`, `nextflow config`) and local-executor runs submit nothing.
- A profile or config can switch the executor without being named: `$SNAKEMAKE_PROFILE`, a `profiles/default/` folder beside the Snakefile (loaded automatically since Snakemake 7.29), or a `nextflow.config` in the launch directory or `~/.nextflow/config`. The local-run commands below rule these out.

## Running the driver

The driver (the `snakemake` process, or Nextflow's JVM) lives for the whole run and accumulates CPU time, so on the login node it is killed at 10 CPU-minutes (SKILL.md) partway through. Run it as a batch job: that survives dropped connections and login-node reboots, which an `srun` shell doesn't (INTERACTIVE.md). Drivers can submit from compute nodes: FRCE's production pipelines (CCBR's, the CCR Sequencing Facility's) run theirs exactly this way.

The driver job, saved as `driver.sh` in the run directory; its last lines come from the Snakemake or Nextflow section:

```bash
#!/bin/bash
# driver.sh: the user submits it; it runs on a compute node and submits the pipeline's jobs
#SBATCH --job-name=driver
#SBATCH --partition=norm
#SBATCH --cpus-per-task=2
#SBATCH --mem=8g
#SBATCH --time=4-00:00:00
#SBATCH --output=%x-%j.out
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true   # module init: MODULES.md (Modules in batch jobs and scripts)
cd /scratch/cluster_scratch/$USER/RUN        # RUN: the run directory; .snakemake/ or work/ and the logs land here
# launch lines: from the Snakemake or Nextflow section below
```

```bash
# on the FRCE login node, in the run directory — the user runs:
sbatch --parsable driver.sh                  # prints the driver's job ID
```

- **Size.** 2 CPUs and 4–8 GB carry a driver whose rules or processes all run as jobs; add CPUs for Snakemake `localrules`. FRCE's production drivers (third-party code) mostly use 2 CPUs and 4–40 GB for 2–4 days. `--time` must outlast the pipeline: past `norm`'s limit, the user resubmits the driver to resume, or gives it a longer `--time`, which moves it to `unlimited` (JOBS.md (Partitions and walltime)).
- **Where files go.** The run directory is under `/scratch/cluster_scratch/$USER`: not `/home`, which is slow (STORAGE.md (Home)), and not `/scratch/local`, which other nodes can't see. After a good run, the user decides what to delete from `.snakemake/` or `work/` (ground rule 4).
- **No per-job `TMPDIR` in the driver.** Child jobs inherit the driver's environment, and a per-job directory under the driver's `/scratch/local` doesn't exist on their nodes. Tasks that write much temporary data make their own (JOBS.md (Temporary files)). Drop every Biowulf lscratch setting: FRCE refuses them.
- **Filesystem lag.** A file written on one node can appear late on another. Snakemake needs `latency-wait` (FRCE pipelines use 60–600 s; the profile below uses 120); Nextflow waits for each task's exit file for up to `executor.exitReadTimeout` (270 s by default).
- **Pacing.** FRCE caps CPUs per user, not submissions, and publishes no query limits (JOBS.md (Partitions and walltime; Scheduler etiquette)). Keep submissions near one per second, status checks sparse, and concurrency (`jobs`, `queueSize`) close to what the caps can run anyway; both templates below do. Rules asking 30 minutes or less run in `short`, under its smaller cap.
- **Stopping.** Cancelling the driver (`scancel DRIVERJOBID`, the user's) can leave its submitted jobs running: check `squeue --me` once and have the user cancel those too.
- **Watching.** Read the driver's log (`driver-JOBID.out`), `.snakemake/log/`, or `.nextflow.log` rather than the queue (ground rule 3).

## Snakemake

`module avail snakemake` lists 5.5.4, 7.20.0, 7.20.0_conda, 7.32.4, and the default 8.4.8 (live, Sept 2026). 8.4.8 is a self-contained install with its own Python 3.12, whose `site-packages` the module prepends to `PYTHONPATH`, so load it alone: with `module load python` beside it, imports broke on FRCE (`Importing the numpy C-extensions failed`, [XAVIER#31](https://github.com/CCBR/XAVIER/issues/31), 2023). Rules that need Python packages get a `conda:` or `container:` environment instead.

Snakemake 8 moved cluster execution into executor plugins and removed `--cluster`, `--cluster-config`, and `--cluster-status` ([migration notes](https://snakemake.readthedocs.io/en/stable/getting_started/migration.html#migrating-to-snakemake-8)). Two plugins suit FRCE. Which of their releases install depends on the Snakemake version, because the plugin interface changed at 8.6 (PyPI metadata, Sept 2026):

| Executor | What you supply | With Snakemake 8.6+ | With Snakemake 8.0–8.5 (the 8.4.8 module) |
|---|---|---|---|
| `slurm` (preferred) | resources per rule; the plugin builds the `sbatch` line and checks status with `sacct` | current releases | only ≤ 0.4.1, from early 2024 |
| `cluster-generic` | the `sbatch` line and a status script | 1.0.9 | ≤ 1.0.8 |

The 8.4.8 module carries only `snakemake-executor-plugin-cluster-generic` 1.0.9 and no `slurm` plugin (Sept 2026). That release declares the 8.6+ interface, so whether it works under 8.4.8 is untested: a dry run with the `frce-generic` profile below shows it (`snakemake --profile frce-generic -n`).

```bash
# on the compute node (inside your session): what the module carries
module load snakemake/8.4.8 && snakemake --version && pip list 2>/dev/null | grep -i -E 'snakemake-(executor|interface)'
```

For the `slurm` executor, build your own Snakemake on scratch (the module is read-only); for a conda environment instead, see PYTHON-R.md (Virtual environments and conda):

```bash
# on the compute node (inside your session); compute nodes reach PyPI directly (TRANSFER.md (Downloads on the cluster))
module load python/3.12                    # Snakemake 8+ needs Python 3.11 or newer
unset PYTHONPATH                           # else the module's packages shadow the venv's: PYTHON-R.md (Python on FRCE)
python3 -m venv /scratch/cluster_scratch/$USER/envs/snakemake
/scratch/cluster_scratch/$USER/envs/snakemake/bin/pip install snakemake snakemake-executor-plugin-slurm
```

The FRCE profile for the `slurm` executor. `max-jobs-per-timespan` needs Snakemake 8.17+; older versions take `max-jobs-per-second: 1`, which 9.x accepts but ignores.

```yaml
# ~/.config/snakemake/frce/config.yaml: used by `snakemake --profile frce`
executor: slurm
jobs: 50                          # jobs pending or running at once
max-jobs-per-timespan: "1/1s"
latency-wait: 120
rerun-incomplete: true
keep-going: true
printshellcmds: true
default-resources:
  slurm_partition: norm
  runtime: 240                    # minutes: becomes --time
  mem_mb: 4000                    # MB: becomes --mem
# for rules with container: images (binds and cache: CONTAINERS.md)
# software-deployment-method: apptainer
# apptainer-prefix: /scratch/cluster_scratch/$USER/containers/snakemake
# apptainer-args: "--cleanenv --bind /scratch/cluster_scratch/$USER"
```

- **Rules.** `threads:` becomes `--cpus-per-task`; `mem_mb`, `runtime`, and `slurm_partition` (`largemem`, `unlimited`) override the defaults per rule. GPU rules: `slurm_partition="gpu", gres="gpu:l40s:1"` (types: JOBS.md (GPUs)), with `threads` inside the node's per-GPU share (HARDWARE.md (GPUs)). Recent plugin releases refuse `--gres`, `--partition`, `--mem`, `--time`, and `--constraint` inside `slurm_extra` ("The --generic-resources-(GRES) option is not allowed in the 'slurm_extra' parameter"): use the matching resources.
- **Logs.** Job logs go to `.snakemake/slurm_logs/`, and the plugin deletes those of successful jobs: give rules `log:` files.
- **Modules in rules.** Jobs start in a non-interactive shell, so a rule that calls `module load` needs the init line (MODULES.md (Modules in batch jobs and scripts)). `conda:` and `container:` directives avoid the issue.

```bash
# driver.sh launch lines (Snakemake, own environment; with the module: module load snakemake/8.4.8 for the first three, --profile frce-generic)
module load python/3.12
unset PYTHONPATH
export PATH=/scratch/cluster_scratch/$USER/envs/snakemake/bin:$PATH
snakemake --profile frce --local-cores "$SLURM_CPUS_PER_TASK"
```

The `cluster-generic` variant, for the 8.4.8 module if its plugin works: copy the profile and replace its `executor:` and `max-jobs-per-timespan:` lines (8.4.8 lacks the latter) with the lines below. Always give it a status command: without one, Snakemake learns that a job ended only from a marker file the job writes itself, so a job Slurm kills for time or memory looks "running" forever. Create `logs/slurm/` in the run directory first.

```yaml
# ~/.config/snakemake/frce-generic/config.yaml: the frce profile with these lines instead
executor: cluster-generic
cluster-generic-submit-cmd: "sbatch --parsable --partition={resources.slurm_partition} --cpus-per-task={threads} --mem={resources.mem_mb}M --time={resources.runtime} --job-name=smk.{rule} --output=logs/slurm/{rule}-%j.out"
cluster-generic-status-cmd: status-sacct.sh      # a file in this folder: Snakemake resolves it there
cluster-generic-cancel-cmd: scancel
max-jobs-per-second: 1
max-status-checks-per-second: 1
```

```bash
#!/bin/bash
# status-sacct.sh JOBID: prints success, failed, or running; only reads sacct (chmod +x)
state=$(sacct -j "$1" -X -n -P -o State 2>/dev/null | head -n 1)
case "$state" in
    COMPLETED) echo success ;;
    FAILED*|CANCELLED*|TIMEOUT*|OUT_OF_MEMORY*|NODE_FAIL*|BOOT_FAIL*|DEADLINE*|PREEMPTED*) echo failed ;;
    *) echo running ;;                   # PENDING, RUNNING, or not yet recorded
esac
```

Local runs are yours: no profile applies, nothing is submitted, and rules are held to the session's CPUs and memory.

```bash
# on the compute node (inside your session), in the run directory
env -u SNAKEMAKE_PROFILE snakemake --workflow-profile none -n          # dry run
env -u SNAKEMAKE_PROFILE snakemake --workflow-profile none --keep-going \
    --cores "${SLURM_CPUS_PER_TASK:-1}" --resources mem_mb="${SLURM_MEM_PER_NODE:-4000}"
```

## Nextflow

`module avail nextflow` lists 23.08.0, 24.10.5, 25.10.0, and the default 26.04.2, which loads `java/21` (live, Sept 2026; the [FRCE page](https://ncifrederick.cancer.gov/fredi/nextflow) shows 24.10.5). Plugins download into `~/.nextflow` on first use and pipelines into `~/.nextflow/assets`, from a driver job too (TRANSFER.md (Downloads on the cluster)); `export NXF_HOME=/scratch/cluster_scratch/$USER/.nextflow` moves both out of home.

- `export` every `NXF_*` variable. An FRCE user's `NXF_SYNTAX_PARSER=v2`, set without `export`, never reached Nextflow ([nextflow#6516](https://github.com/nextflow-io/nextflow/issues/6516)). That variable picks the parser: the strict one is off by default in 25.04–25.10 and on from 26.04, so the default module parses strictly; `export NXF_SYNTAX_PARSER=v1` brings back the legacy parser for pipelines that fail to parse ([strict syntax](https://docs.seqera.io/nextflow/strict-syntax)).

`frce.config`, kept in the run directory and passed with `-c`:

```groovy
// frce.config: FRCE settings for a Nextflow driver job (nextflow run ... -c frce.config)
process {
    executor       = 'slurm'
    queue          = 'norm'
    resourceLimits = [ cpus: 36, memory: 750.GB, time: 120.h ]   // any capped task fits a 36-core, 755g norm node, within 5 days
    // no scratch and no '--gres=lscratch:N': FRCE has no per-job local disk allocation
}
executor {
    queueSize         = 100          // tasks pending or running at once
    submitRateLimit   = '6/1min'     // CCBR's value; FRCE publishes no limit
    pollInterval      = '2 min'
    queueStatInterval = '5 min'
}
apptainer {
    enabled    = true
    autoMounts = true
    cacheDir   = "/scratch/cluster_scratch/${System.getenv('USER')}/containers/nextflow"   // images; must be visible to every node
}
```

- `resourceLimits` needs Nextflow 24.04+ (node shapes: HARDWARE.md (Partitions and node types)); nf-core pipelines built on templates before 3.0 cap requests with `--max_cpus 36 --max_memory 750.GB --max_time 120.h` instead.
- GPU processes, in a `withName:` or `withLabel:` block: `queue = 'gpu'`, `clusterOptions = '--gres=gpu:l40s:1'` (types: JOBS.md (GPUs)), and `containerOptions = '--nv'`.
- The driver pulls container images straight from the registries, with the `apptainer` on its `PATH` (the system one, or a module: CONTAINERS.md (Apptainer on FRCE)); tasks inherit its `PATH`. Pre-pulling: CONTAINERS.md (Pulling images). A group share whose files reach tasks through symlinks may need `apptainer.runOptions = '-B /mnt/SHARE'` (CONTAINERS.md (Running containers)).
- `-with-trace` records each task's peak memory and run time, for sizing (MONITORING.md (Sizing the next run)).

```bash
# driver.sh launch lines (Nextflow); drop -profile apptainer for pipelines that don't define it
module load nextflow/26.04.2                     # loads java/21; apptainer: the system one on PATH
export APPTAINER_CACHEDIR=/scratch/cluster_scratch/$USER/.apptainer/cache   # layer cache: CONTAINERS.md (Apptainer on FRCE)
export NXF_JVM_ARGS="-Xms1g -Xmx4g"             # the driver's heap, well inside --mem
nextflow run nf-core/PIPELINE -r VERSION -profile apptainer -c frce.config \
    -params-file params.yaml --outdir results -resume
```

Local test runs are yours: launch from a directory without a `nextflow.config`, and let `local.config` pin the local executor (it overrides `~/.nextflow/config`), so every task runs in your allocation.

```bash
# on the compute node (inside your session), in a test run directory
module load nextflow/26.04.2
export APPTAINER_CACHEDIR=/scratch/cluster_scratch/$USER/.apptainer/cache NXF_APPTAINER_CACHEDIR=/scratch/cluster_scratch/$USER/containers/nextflow
cat > local.config <<EOF
process.executor       = 'local'
executor.cpus          = ${SLURM_CPUS_PER_TASK:-1}
executor.memory        = '$(( ${SLURM_MEM_PER_NODE:-4096} - 2048 )) MB'
process.resourceLimits = [ cpus: ${SLURM_CPUS_PER_TASK:-1}, memory: $(( ${SLURM_MEM_PER_NODE:-4096} - 2048 )).MB, time: 8.h ]
EOF
nextflow run nf-core/PIPELINE -r VERSION -profile test,apptainer -c local.config --outdir results-test
```

## CCBR pipelines on FRCE

CCR's Collaborative Bioinformatics Resource keeps its pipelines, containers, and references on an FRCE share owned by the group `nci-frederick-ccbr-pipelines` and describes it as "available for all users of FRCE". This is third-party material: CCBR maintains it, not the FRCE administrators, and support goes to each pipeline's GitHub issues. Its `db/` and `SIFs/` are world-readable (live, Sept 2026: `ls -ld /mnt/projects/CCBR-Pipelines/*/`).

```text
/mnt/projects/CCBR-Pipelines/
  pipelines/   (a link to Pipelines/) installed pipelines; guis/latest/bin/setup puts their commands on PATH
  bin/         CCBR's own snakemake and python (Snakemake 6.2.1 in 2023)
  SIFs/        prebuilt container images, for --sif-cache
  db/          references (GDC_refs, arriba, fastq_screen_db, ...)
  resources/   shared conda installs (miniconda3, miniforge3)
```

FRCE support as of Sept 2026, from each repo:

| Pipeline | Manager | FRCE support |
|---|---|---|
| [RENEE](https://github.com/CCBR/RENEE) (RNA-seq) | Snakemake | README section; FRCE genome configs |
| [XAVIER](https://github.com/CCBR/XAVIER) (exome) | Snakemake | README section; `cluster.frce.json` |
| [TRANQUIL](https://github.com/CCBR/TRANQUIL) (tRNA) | Snakemake | written for FRCE; installed under `pipelines/TRANQUIL` |
| [CHARLIE](https://github.com/CCBR/CHARLIE) (circRNA) | Snakemake | `config/slurm-fnlcr` profile |
| ASPEN, CARLISLE | Snakemake | detect FRCE; docs target Biowulf |
| [LOGAN](https://github.com/CCBR/LOGAN) | Nextflow | `-profile frce` wired, its config still marked TODO |
| CHAMPAGNE, SINCLAIR, CRISPIN, MOSuite | Nextflow | an `frce.config` that nothing includes ([CHAMPAGNE#74](https://github.com/CCBR/CHAMPAGNE/issues/74), open since 2023) |

```bash
# on the compute node (inside your session): RENEE's FRCE recipe with FRCE paths; setup and a dry run submit nothing
. /mnt/projects/CCBR-Pipelines/pipelines/guis/latest/bin/setup
renee run --input /scratch/cluster_scratch/$USER/fastq/*.R?.fastq.gz \
    --output /scratch/cluster_scratch/$USER/RNA_hg38 --genome hg38_36 --mode slurm \
    --tmp-dir /scratch/cluster_scratch/$USER --sif-cache /mnt/projects/CCBR-Pipelines/SIFs --dry-run
```

- Without `--dry-run`, `--mode slurm` submits RENEE's driver job (4-day walltime): that command is the user's. XAVIER (`--runmode init|dryrun|run`) and TRANQUIL (`-m=init|dryrun|run`) work the same way: `init` and `dryrun` are yours, `run` is the user's.
- Their READMEs' FRCE steps start with `srun --export all --pty --x11 bash`, which sets no partition, CPUs, memory, or time: size the session (INTERACTIVE.md). XAVIER's FRCE example keeps Biowulf's `/data/...` paths, and RENEE's docs show `--tmp-dir /cluster_scratch/$USER`: use `/scratch/cluster_scratch/$USER` for both.
- They bring their own Snakemake (6.x–7.x, with `--cluster`): don't mix in the snakemake module, and don't port their profiles to Snakemake 8.
- Unreadable files on the share have happened before (a `db/` directory closed to other users, RENEE#101, 2024): report to CCBR rather than copying around it. A share missing on compute nodes: TROUBLESHOOTING.md (Software and environment problems).

## Stale advice on the official pages

- [Snakemake page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/WorkflowManagers/Snakemake): its batch script asks for `--ntasks=8` and runs `snakemake --cores ${SLURM_NTASKS}`, and tasks can land on several nodes while Snakemake runs on one; it also sets no `--mem` → `--cpus-per-task=8` with `--cores "$SLURM_CPUS_PER_TASK"` and a `--mem`, or the local-run command above inside a job.
- The same page sends users to CCBR's Biowulf [tutorial](https://ccbr.github.io/snakemake_tutorial/usage/task/) with only the lscratch line removed. The tutorial uses `--cluster` and `--cluster-config`, which Snakemake 8 removed, and its repository was archived in June 2026 → the profile above.
- [Workflow Managers](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/WorkflowManagers): its nextflow card links `/nextflow`, which redirects to a staff login → the public page is https://ncifrederick.cancer.gov/fredi/nextflow.
- That Nextflow page runs `nextflow run hello.nf` with the local executor and opens `nextflow console` on the login node (its screenshot's title bar reads fsitgl-head01p) → run Nextflow in a job or session; the console is a GUI, so use an OnDemand desktop (ONDEMAND.md). Its "nextflow documentation" link now redirects to docs.seqera.io.
- AppDB lists Nextflow only as a 2020 development build (20.05.0) and Snakemake as of Apr 2024 → `module avail` is the ground truth.

## Going further

- FRCE: [Workflow Managers](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/WorkflowManagers), [Snakemake](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/WorkflowManagers/Snakemake), [Nextflow](https://ncifrederick.cancer.gov/fredi/nextflow); [AppDB's Snakemake entry](https://appdb.ncifcrf.gov/software/Snakemake) (NIH network only).
- Snakemake: the [slurm executor](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/slurm.html) (resources, GPUs, MPI, partition selection), the [cluster-generic executor](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/cluster-generic.html), [profiles](https://snakemake.readthedocs.io/en/stable/executing/cli.html#profiles).
- Nextflow: the [Slurm executor](https://docs.seqera.io/nextflow/executor/slurm), [executor settings](https://docs.seqera.io/nextflow/reference/config/executor), [Apptainer settings](https://docs.seqera.io/nextflow/reference/config/apptainer), [Apptainer containers](https://docs.seqera.io/nextflow/container/apptainer), [environment variables](https://docs.seqera.io/nextflow/reference/env-vars).
- Biowulf docs, translated first (FROM-BIOWULF.md): NIH's [Snakemake profile](https://hpc.nih.gov/apps/snakemake.html#profile) and [Nextflow config](https://hpc.nih.gov/apps/nextflow.html#config) show worked Slurm setups, with lscratch and Biowulf partitions to strip.
- Live: `module avail snakemake nextflow`, `snakemake --version`, `nextflow -version`, `nextflow config`, `sinfo -p norm -N -o '%c %m'`.
