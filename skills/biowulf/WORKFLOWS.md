Snakemake, Nextflow (including nf-core and EPI2ME), and Cromwell on Biowulf: who may start the head process, the NIH profiles and configs, head-job scripts, rate limits, and the errors these setups produce. sbatch options, partitions, lscratch, and GPU syntax are in JOBS.md; general container setup in CONTAINERS.md; job history and right-sizing in UTILITIES.md; independent per-sample commands with no dependency graph in SWARM.md.

Table of contents

- [Who runs what](#who-runs-what)
- [Rate limits: never loosen them](#rate-limits-never-loosen-them)
- [Snakemake](#snakemake)
- [Nextflow and nf-core](#nextflow-and-nf-core)
- [Cromwell](#cromwell)
- [Errors and fixes](#errors-and-fixes)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Who runs what

The head process (snakemake, nextflow, or the Cromwell JVM) never runs on the login node, and NIH prefers it as a batch job. Whether you may start it depends only on whether it submits jobs:

| Command | Submits jobs? | Who starts it |
|---|---|---|
| Checks: `snakemake -n` (with any profile: a dry run submits nothing), `nextflow config -profile biowulf`, `java -jar ${WOMTOOL_JAR} validate wf.wdl` | no | you, in the session |
| Local executors: `snakemake --profile none --workflow-profile none -j "${SLURM_CPUS_PER_TASK:-2}"`; `nextflow run … -profile biowulflocal`; `java -jar ${CROMWELL_JAR} run …` without `-Dconfig.file` | no | you, in the session, sized to it |
| Slurm executors: `snakemake --profile …`, `--executor slurm` or `cluster-generic`, `--cluster …`; `nextflow run … -profile biowulf` (or `test,biowulf`); `java -Dconfig.file=${CROMWELL_CONFIG} …` | yes | the user, as a batch head job |

Working sequence:
1. Write the Snakefile or `main.nf`, config overrides, `params.yaml`, and the head-job script in a project directory under `/data/$USER`, never `/home` (the small Snakemake profile clone in `~/.config` below is the one exception): `work/`, `.snakemake/`, and `cromwell-executions/` receive every intermediate file.
2. Dry-run, then make a small real run with the local executor in the session (a test profile, two samples). A local run lives and dies with the session; one too big or too long for it becomes a batch job the user submits.
3. Give the user the head-job script and its `sbatch` line, with a `--time` that outlasts the whole pipeline (partition defaults are short; JOBS.md).
4. Follow the logs ([Errors and fixes](#errors-and-fixes)), fix, and give the user the rerun: Nextflow with `-resume`; Snakemake reruns only what is missing, incomplete, or out of date.

## Rate limits: never loosen them

Every NIH setup throttles submissions and status checks (values as of Sept 2026). Keep them or make them stricter; never raise them or drop them from a copied config.

| Setup | Settings |
|---|---|
| snakemake.html command line | `--max-jobs-per-second 1 --max-status-checks-per-second 0.01` (Snakemake ≥ 9 ignores the first: below) |
| NIH Snakemake profile | `main`: `max-jobs-per-second: 1`, `max-status-checks-per-second: 1`, `jobs: 50` · `snakemake8`: `max-jobs-per-timespan: "60/1m"`, `max-status-checks-per-second: 1`, `jobs: 50` · `snakemake9`: `max-jobs-per-second: 1` (ignored by Snakemake 9: below), `max-status-checks-per-second: 0.1`, `jobs: 500` |
| NIH Nextflow config, `biowulf` profile | `submitRateLimit = '6/1min'`, `pollInterval = '2 min'`, `queueStatInterval = '5 min'`, `queueSize = 200` |
| `$CROMWELL_CONFIG` | `job-rate-control { jobs = 1  per = 1 second }`, `concurrent-job-limit = 10` |

- NIH: "please don't change settings for job submission and querying (`pollInterval, queueStatInterval, and submitRateLimit`)"; any config that defines its own `slurm` executor must carry them ([Common Pitfalls](https://hpc.nih.gov/apps/nextflow.html#gotcha)).
- Snakemake ≥ 9.0 silently ignores `max-jobs-per-second` wherever it is set: the `snakemake9` branch's config and snakemake.html's command line alike. The option is deprecated, and `--max-jobs-per-timespan` always carries its own default, 100/1s, which overrides it, so submissions run at up to 100 per second (checked against Snakemake 9.23.1's source and a test profile, Sept 2026). Pass `--max-jobs-per-timespan 1/1s`, or add `max-jobs-per-timespan: "1/1s"` to the clone's `config.yaml` (setup below): it restores NIH's rate and only tightens the profile. Counts must be whole numbers (`1/1s`, `30/1m`).
- Concurrency caps (`jobs`, `queueSize`, `concurrent-job-limit`) are not rate limits; the Cromwell page suggests raising its "low 10 jobs" for bigger workflows. The `main`/`snakemake8` profiles and the Cromwell config read job state from `dashboard_cli` to spare Slurm; never swap that for `squeue` or `sacct` polling.

## Snakemake

Use the NIH profile branch that matches `snakemake --version` ([repo](https://github.com/NIH-HPC/snakemake_profile)); snakemake.html shows only `--cluster`, which Snakemake 8 removed. The apps catalog lists 8.16.0 (Sept 2026); check `module -r spider '^snakemake$'`.

| Snakemake | Branch | Submits via | Notes |
|---|---|---|---|
| < 8 | `main` (default) | `bw_submit.py`, state from `dashboard_cli` | partition chosen automatically; `mem_mb` required; `disk_mb` → `--gres=lscratch:<GB>`; logs in `logs/{rule}-%j.out`; clone it into the workflow directory and pass `--profile snakemake_profile` |
| 8.x | `snakemake8` ("experimental") | `executor: cluster-generic` | as `main`; clone with `--branch snakemake8` (its README's `git clone` omits it). Needs Snakemake ≥ 8.17: on 8.0–8.16, the catalog's 8.16.0 included, its `max-jobs-per-timespan` line fails, so replace it in the clone with `max-jobs-per-second: 1`, or use 9.23.1 with `snakemake9`. May need `snakemake-executor-plugin-cluster-generic` installed "via pip or conda into the same environment as Snakemake", which, if the module lacks it, means the user's own conda env (CONDA.md) |
| ≥ 9 | `snakemake9` | `executor: slurm` | requires `snakemake-executor-plugin-slurm`; the README's install steps are just `module load snakemake/9.23.1` and the clone below; partition not automatic |

Setup for ≥ 9 (cloning submits nothing, so you may do it) and a rule; `config.yaml` defaults are `slurm_partition: "norm"`, `runtime: 720`, `mem_mb: 4096`. The rule uses the slurm plugin's own resources, not the `slurm_extra` and `lscratch_tmpdir` forms of NIH's README (Stale advice):

```bash
# on the compute node (inside the session)
module load snakemake/9.23.1    # the README's version; confirm: module -r spider '^snakemake$'
git clone --branch snakemake9 https://github.com/NIH-HPC/snakemake_profile.git ~/.config/snakemake/biowulf
grep -q '^max-jobs-per-timespan:' ~/.config/snakemake/biowulf/config.yaml ||
  echo 'max-jobs-per-timespan: "1/1s"' >> ~/.config/snakemake/biowulf/config.yaml   # the branch's max-jobs-per-second is ignored (Rate limits)
```
```python
import os
rule align:
    threads: 8                                  # becomes --cpus-per-task; pass {threads} to the tool
    resources:
        mem_mb=16384, runtime=240,              # MB, minutes
        gres="lscratch:100",                    # --gres=lscratch:100; disk_mb alone allocates no lscratch
        tmpdir=lambda wc: os.path.expandvars("/lscratch/$SLURM_JOB_ID")   # expands on the rule's node; needs the gres above
    shell: "my_tool --threads {threads} --tmp $TMPDIR ..."
```

- Give Slurm settings as the plugin's resources: `slurm_partition`, `runtime`, `mem_mb`, `gres` (one `name[:type]:count`, so not `lscratch:100,gpu:a100:1`), `constraint`, `tasks`, `nodes`. Give every rule that uses lscratch the `tmpdir` lambda too: Snakemake exports that resource as `$TMPDIR` (and `TMP`, `TEMP`) for the rule's shell command, and nothing else points `$TMPDIR` at lscratch. Never put `--gres`, `--constraint`, `--ntasks`, `--nodes`, `--mem`, `--cpus-per-task`, `--time`, or `--partition` in `slurm_extra`: plugin ≥ 1.9 (Oct 2025) refuses the job at submission, which `snakemake -n` doesn't catch. Check what the module ships, e.g. `python -m pip show snakemake-executor-plugin-slurm` after `module load snakemake` (generic).
- Set `slurm_partition="gpu"`, `"largemem"`, `"multinode"`, or `"quick"` yourself; everything else lands on `norm` (partition rules: JOBS.md). MPI: `slurm_partition="multinode", tasks=32, nodes=2`.
- GPU: `slurm_partition="gpu", gres="gpu:a100:1"` gives NIH's documented `--gres=gpu:a100:1`; for several acceptable types, `gres="gpu:2", constraint="gpua100|gpuv100x"`. The plugin turns `gpu=1, gpu_model="a100"` into `--gpus=a100:1`, a form NIH doesn't document (its README says `--gres`). GPU plus lscratch can't share `gres`, so use `gres="lscratch:100", gpu=1, gpu_model="a100"`, which needs plugin ≥ 2.6.1 (older ones stop with `GRES and GPU are set`). Plugins up to 2.7.0 also add `--ntasks-per-gpu=1`, making a rule's CPUs threads × GPUs: keep that within the per-GPU cap (HARDWARE.md). Check the first job's grant (`scontrol show job JOBID`) before scaling up.
- Head job: the user submits `sbatch --cpus-per-task=2 --mem=8g --time=24:00:00 snakemake.sh`. Two CPUs suffice when every rule is submitted; add CPUs for `localrules:`. The slurm plugin deletes the logs of successful jobs (and all after 10 days); add `slurm-keep-successful-logs: true` to the clone's `config.yaml` while debugging.

```bash
#!/bin/bash
cd /data/$USER/PROJECT || exit 1        # the workflow directory
module load snakemake/9.23.1 || exit 1
snakemake --profile biowulf --local-cores "${SLURM_CPUS_PER_TASK:-2}" all
```

Local run in the session. You may run it only with every profile switched off: pass `--profile none --workflow-profile none`, since Snakemake ≥ 7.29 otherwise loads `$SNAKEMAKE_PROFILE`, a `profiles/default/` beside the Snakefile, or a bare `default/` directory without being asked. `--resources` keeps rules that declare `mem_mb` within the session's memory, less room for your own process (1 GB below).

```bash
# on the compute node (inside the session); profiles off, so nothing is submitted
module load snakemake/9.23.1          # the version the head job will use
snakemake -n --profile none --workflow-profile none
snakemake --profile none --workflow-profile none -p --keep-going -j "${SLURM_CPUS_PER_TASK:-2}" --resources mem_mb=$(( ${SLURM_MEM_PER_NODE:-1536} - 1024 )) all
```

- Many short jobs: combine them with [job groups](https://hpc.nih.gov/apps/snakemake.html#group), via `group:` or `--groups stage1=grp1 stage2=grp1 stage3=grp1`, plus `--group-components grp1=3` for three samples per job. In NIH's (older) run, a group took the maximum memory and maximum, not summed, runtime of its rules, while components added up; check the request your version submits.
- Software in submitted rules: `module load NAME/VERSION &&` at the start of each rule's `shell:` (NIH's examples, now commented out of snakemake.html, do this), or Snakemake's `envmodules:` with `--use-envmodules` (generic).
- Containers: in the head job, run CONTAINERS.md's setup block minus its `SINGULARITY_TMPDIR` line (module, cache on `/data`, `sing_binds`) before `snakemake`; submitted rules inherit that environment (the plugin exports it), except that a `TMPDIR` or `SINGULARITY_TMPDIR` naming the head's lscratch doesn't exist on rule nodes: don't export them in the head, or reset `TMPDIR` per rule with the `tmpdir` lambda above.

## Nextflow and nf-core

`module load nextflow` gives the default, 25.10.0 since Dec 2025; pipelines not yet updated for strict syntax need `nextflow/25.04.2` (check `module -r spider '^nextflow$'`). The nf-core CLI is bundled (`nf-core --help`). Always copy NIH's config into the launch directory, `cp ${NXF_CONFIG:-none} .` (EPI2ME `wf-*` pipelines: `cp ${NXF_CONFIG_EPI2ME:-none} .`), and name a profile: with no config, Nextflow spreads tasks over every CPU of the node. Launch from a run directory of its own, so the copy never replaces your pipeline's own `nextflow.config`.

| Profile | Executor | For | Settings |
|---|---|---|---|
| `biowulflocal` | local | debugging, small or short runs, the first EPI2ME run | `cpus` = `$SLURM_CPUS_PER_TASK` (else 2), `memory` = `$SLURM_MEM_PER_NODE` MB (else 4000), so the allocation needs `-c`, `--mem`, and lscratch |
| `biowulf` | slurm | large or long runs | queue `norm`; the rate limits above; `maxRetries = 2` on listed exit codes (including 1, 137, 143); each task runs in `/lscratch/$SLURM_JOB_ID` with `--gres=lscratch:${100 * task.attempt}`; `resourceLimits = [ cpus: 192, memory: 751.GB, time: 240.h ]` |

Both profiles also get Singularity with `cacheDir` `/data/$USER/nxf_singularity_cache` and staff images in `libraryDir` `/fdb/nxf/singularity-images`; `params.igenomes_base = '/fdb/igenomes_nf/'`; `cleanup = true`; the timeline and report; and a task environment with tool caches under `/data/$USER/.cache` plus `OMP_NUM_THREADS = 1`, `OPENBLAS_NUM_THREADS = 1`, and `PYTHONNOUSERSITE = 1` (in your own processes, pass `${task.cpus}` to multithreaded tools). So:
- Put your own settings in a separate `-c my.config`, which outranks `nextflow.config`, so re-copying the NIH config (the fix for several errors below) keeps them. To use NIH's commented selector examples, remove the `//` and keep them inside `process { }`.
- `cleanup = true` deletes `work/` after a successful run, so `-resume` reuses only failed or interrupted runs; set `cleanup = false` in `my.config` while iterating. NIH asks that `work/` not fill with "millions of small files".
- A process-level `clusterOptions` replaces the profile's lscratch request, yet the task still runs in `/lscratch/$SLURM_JOB_ID`: keep `--gres=lscratch:N` in the same string, combined with any GPU (`--gres=lscratch:50,gpu:1`).
- Hybrid runs: in `biowulf`, send light processes to the head job (`withName: 'SAMTOOLS_INDEX|FASTQC' { executor = 'local' }`) and size the head job for them (NIH's example: 32 CPUs). For many short processes across nodes NIH points to [HyperQueue](https://hpc.nih.gov/apps/hyperqueue.html).

Local run in the session (you may run it; NIH's example session for nf-core/sarek is `-c 32 --mem=80g --gres=lscratch:200`):

```bash
# on the compute node (inside the session), in the launch directory under /data/$USER
module load nextflow
cp ${NXF_CONFIG:-none} .
export NXF_SINGULARITY_CACHEDIR=/data/$USER/nxf_singularity_cache SINGULARITY_CACHEDIR=/data/$USER/.singularity TMPDIR=/lscratch/$SLURM_JOB_ID
ulimit -u 10240 -n 16384          # NIH's fix when the local executor hits process or open-file limits
nextflow config -profile biowulflocal | grep -n "'slurm'"    # must print nothing: no process goes to Slurm
nextflow run nf-core/PIPELINE -r VERSION -profile test,biowulflocal -c my.config --outdir /data/$USER/OUTDIR   # test brings its own small input: no --input
```

Write `my.config` first. The local executor rejects a task that needs more than the allocation (`Process requirement exceeds available CPUs`, or memory), so cap requests there with `process.resourceLimits = [ cpus: 8, memory: 30.GB, time: 8.h ]`, set to the allocation with ~2 GB of memory left for Nextflow itself, or ask the user for a bigger session.

Head job, adapted from NIH's `nf_main.sh` (which pairs `--mem=4G` with the same 4 GB heap; this leaves headroom); the user submits it with `sbatch nf_main.sh`:

```bash
#!/bin/bash
#SBATCH --cpus-per-task=4
#SBATCH --mem=8g
#SBATCH --gres=lscratch:200
#SBATCH --time=24:00:00
cd /data/$USER/RUNDIR             # the launch directory: config, my.config, params.yaml, work/
module load nextflow
export NXF_SINGULARITY_CACHEDIR=/data/$USER/nxf_singularity_cache SINGULARITY_CACHEDIR=/data/$USER/.singularity TMPDIR=/lscratch/$SLURM_JOB_ID
export NXF_JVM_ARGS="-Xms2g -Xmx4g"
cp ${NXF_CONFIG:-none} .          # refreshes NIH's config; your overrides live in my.config
nextflow run nf-core/PIPELINE -r VERSION -profile biowulf -c my.config \
    -params-file params.yaml --outdir /data/$USER/OUTDIR -resume
```

- `--time` must outlast the whole pipeline; if the head job is still killed for memory, raise `--mem` further above the `-Xmx` heap. The exported `TMPDIR` names the head's lscratch, and tasks run on other nodes: give them their own in `my.config`, `process.beforeScript = 'export TMPDIR=/lscratch/$SLURM_JOB_ID'` (generic).
- NIH's local-executor variant, `nf_local.sh`: `--cpus-per-task=32 --mem=80G`, `ulimit -u 10240 -n 16384`, no `NXF_JVM_ARGS`, `-profile biowulflocal`. The EPI2ME basecalling variant adds `--partition=gpu`, `--gres=lscratch:200,gpu:1`, and `--constraint="gpua100|gpuv100x|gpuv100"`, and copies `$NXF_CONFIG_EPI2ME`.
- nf-core: pin `-r` (otherwise "the newest version will be used"), pass settings with `-params-file`, resume with `-resume`. For explicit references in nf-core/rnaseq (other pipelines name these parameters differently), give `--fasta`, `--gtf`, and `--star_index` under `/fdb/igenomes_nf/Homo_sapiens/Ensembl/pub/release-110/` plus `--igenomes_ignore --genome null`; for a custom genome, add `--save_reference` on the first run and reuse the indices. "Sarek/3.5.0 is a buggy version, please use sarek/3.5.1 instead."

## Cromwell

`module load cromwell` sets `$CROMWELL_JAR`, `$WOMTOOL_JAR`, `$CROMWELL_CONFIG`, and `$CROMWELL_TEST_DATA`. Cromwell runs local workflows (all on one node) or Slurm workflows (each task a job); server mode is not supported.

```bash
# on the compute node (inside the session)
module load cromwell
java -jar ${WOMTOOL_JAR} validate wf.wdl
java -Dbackend.providers.Local.config.concurrent-job-limit=4 -jar ${CROMWELL_JAR} run -i input.json wf.wdl
```

Local mode starts every runnable task at once unless capped (the Cromwell setting above); keep tasks × threads within your CPUs. JVM heap sizing is in DEVELOPMENT.md. Slurm mode is a head job run from a `/data` directory, because the head and its jobs exchange files there and lscratch won't work. The user submits it with `sbatch --cpus-per-task=2 --mem=8g --gres=lscratch:50 --time=24:00:00 cromwell.sh`; NIH gives no size, so treat these values as a starting point.

```bash
#!/bin/bash
module load cromwell singularity        # singularity only if tasks set docker
export SINGULARITY_CACHEDIR=/data/$USER/.singularity TMPDIR=/lscratch/$SLURM_JOB_ID   # unset, the config caches images in $HOME/.singularity
java -Dconfig.file=${CROMWELL_CONFIG} -jar ${CROMWELL_JAR} run -i input.json wf.wdl
```

- The config's runtime attributes are `cpu` (default 2), `memory_mb` (4000), `runtime_minutes` (600), `queue` ("norm"), and optional `gpuCount` (adds `--nv`), `gpuType`, and `docker`; use exactly these names in each task's `runtime {}`. `queue` becomes `--partition`, so a GPU task also needs `queue: "gpu"`.
- The head pulls each `docker` image once (under `flock`) into `$SINGULARITY_CACHEDIR`, which "needs to point to a directory accessible by the jobs (i.e. not lscratch)". Call caching uses an Hsqldb database in `cromwell-executions/cromwell-db`. For bigger workflows NIH suggests copying the config and adapting it (a MySQL backend, attribute names, a higher `concurrent-job-limit`); keep `job-rate-control`.

## Errors and fixes

| Symptom | Fix |
|---|---|
| Snakemake reports outputs missing after a cluster job finished | `--latency-wait 120`, which NIH calls required when jobs are submitted; the profiles set 120 or 240 |
| `ERROR - mem_mb is required to be in resources` (`main`); `snakemake8`: `ERROR - mem (as a string like '2G') or mem_mb (int like 1024 *2) is required to be in resources` | give every submitted rule `mem_mb` (`snakemake8` also accepts `mem="2G"`) |
| `--cluster` rejected (`unrecognized arguments`, or `ambiguous option: --cluster could match …`) | Snakemake ≥ 8: use the matching profile branch |
| `unrecognized arguments: --max-jobs-per-timespan=60/1m` | the `snakemake8` branch on Snakemake < 8.17: replace that line with `max-jobs-per-second: 1` (Snakemake table) |
| `Process requirement exceeds available CPUs` (Nextflow local executor) | cap `process.resourceLimits` in `my.config` to the allocation, or ask the user for a bigger session |
| `The --generic-resources-(GRES) option is not allowed in the 'slurm_extra' parameter` (or `--node-constraints`, `--number-of-tasks`, `--number-of-nodes`), at submission | the slurm plugin (≥ 1.9) refuses Slurm flags in `slurm_extra`: use its own resources (`gres`, `constraint`, `tasks`, `nodes`; Snakemake bullets above) |
| `GRES and GPU are set. Please only set one of them.` | plugin < 2.6.1 can't combine `gres` with `gpu`: drop lscratch for that rule, or run a Snakemake whose plugin is newer (a later module, or the user's own conda env: CONDA.md) |
| `Invalid GRES format` | `gres` takes one entry (`lscratch:100` or `gpu:a100:1`), not a comma list |
| `--cleanenv` misread as a Snakemake option | keep the leading space: `singularity-args: " --cleanenv"` (needed before Snakemake 8.12, harmless after) |
| `ERROR ~ Cannot invoke method optional() on null object` | the pipeline predates strict syntax: `module load nextflow/25.04.2` |
| Nextflow jobs ask for unlimited time and max memory and pend forever; or `FATAL: container creation failed: mount /gs6->/gs6 error` (retired `/gsx`) | refresh the config: `cp ${NXF_CONFIG:-none} .` |
| `docker: command not found` | Biowulf has no Docker: copy the NIH config and run with `-profile biowulflocal` or `biowulf` |
| `ERROR ~ Found unexpected parameters` (EPI2ME) | `cp ${NXF_CONFIG_EPI2ME:-none} .` |
| `/home` fills during a run | image caches: export `NXF_SINGULARITY_CACHEDIR` and `SINGULARITY_CACHEDIR` to `/data`; launch from `/data` |
| `sbatch` exits 123 inside a head job | Slurm maintenance (JOBS.md); the user reruns the head job later, resuming |

Read progress from files, not the scheduler: the head job's `slurm-<jobid>.out`, `.nextflow.log` and the execution report and timeline (nf-core: `<outdir>/pipeline_info/`), Snakemake's `.snakemake/log/` plus `logs/` (`main`, `snakemake8`) or `.snakemake/slurm_logs/` (`snakemake9`; failed jobs' logs only, unless kept), and Cromwell's `cromwell-executions/`. Size rules and processes from the finished child jobs (UTILITIES.md).

## Stale advice on the official pages

- snakemake.html shows only `--cluster` (removed in Snakemake 8), omits the rate-limit flags from its own batch example, uses `--max-jobs-per-second` (ignored by Snakemake ≥ 9), links the profile repo, whose default branch `main` is "for snakemake<8", and points its Documentation and Tutorial links at bitbucket → use the branch table above and [snakemake.readthedocs.io](https://snakemake.readthedocs.io/en/stable/executing/cli.html#profiles).
- The `snakemake9` README predates slurm plugin 1.9: its `slurm_extra` forms (`--gres=lscratch:N`, `--constraint`, `--ntasks`/`--nodes`) are refused at submission; its `tmpdir=lscratch_tmpdir` passes the literal string `/lscratch/$SLURM_JOB_ID` (biowulf.smk defines a plain string, which Snakemake doesn't expand), creating a directory by that name; its `gpu_model` becomes `--gpus=`, not `--gres=gpu:`; and the plugin never reads the profile's `jobscript:` → the rule forms above.
- The profile branches disagree. For `quick`, `main`'s code uses ≤ 120 min and ≤ 370 GB, the `snakemake9` README "< 4 hours, < 16 cores, < 370 GB". `norm`'s memory cutoff is 499 GB (`main`) or 751 GB (`snakemake8`). The `snakemake9` README gives a 120-minute default runtime; its `config.yaml`, which is what runs, sets 720. Partition limits: JOBS.md. The `main` and `snakemake8` READMEs also use the retired `k80`/`gpuk80` in GPU examples → current types in HARDWARE.md.
- NIH's `nextflow.config` has a commented GPU block that assigns `clusterOptions` twice; the second replaces the first, dropping `--gres=lscratch:50,gpu:1` → merge them into one string. Its commented `quick` example uses `4.h * task.attempt`, which exceeds quick's 4 h maximum on the first retry.
- The web page shows a copy of the config injected from `/examples/nextflow.config` → copy the on-cluster `$NXF_CONFIG`. Transcripts show Nextflow 20.10–24.10 and old nf-core releases → check `module spider` and pin current releases.
- cromwell.html's demo WDL sets `runtime { rt_mem: 2000 rt_time: 10 }`, names `$CROMWELL_CONFIG` doesn't declare, so its tasks get the config defaults → use `memory_mb` and `runtime_minutes`. Its 2017 transcripts show `/spin1/...` paths → `/data/$USER`.

## Going further

- https://hpc.nih.gov/apps/snakemake.html — NIH notes, interactive and batch examples, [job groups](https://hpc.nih.gov/apps/snakemake.html#group); exercises at https://github.com/NIH-HPC/snakemake-class.
- https://github.com/NIH-HPC/snakemake_profile — the profile; the [`snakemake9` branch](https://github.com/NIH-HPC/snakemake_profile/tree/snakemake9) has lscratch, GPU, and MPI rule examples. Its executor is documented at https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/slurm.html.
- https://hpc.nih.gov/apps/nextflow.html — [changelog](https://hpc.nih.gov/apps/nextflow.html#changes), [common pitfalls](https://hpc.nih.gov/apps/nextflow.html#gotcha), [config](https://hpc.nih.gov/apps/nextflow.html#config), [head-job scripts](https://hpc.nih.gov/apps/nextflow.html#sbatch); web copy of the config at https://hpc.nih.gov/examples/nextflow.config.
- https://hpc.nih.gov/apps/cromwell.html — local and Slurm modes and the full `$CROMWELL_CONFIG`. The other installed workflow managers are listed at https://hpc.nih.gov/apps/#workflow; miniwdl and caper have no NIH page.
- Live: `module -r spider '^snakemake$'`, `module -r spider '^nextflow$'`, `module help cromwell`, `snakemake --help`, `nextflow config -profile biowulf`, `cat $NXF_CONFIG`, `cat $CROMWELL_CONFIG`.
