How to write, size, and hand over Slurm work on Biowulf: batch scripts and sbatch flags, allocation defaults, partitions, walltime, `sinteractive`, GPU requests, lscratch, exit codes, job states, dependencies, changing a submitted job, and multinode MPI. You write and check the scripts; every command here that submits, cancels, or changes a job is the user's to run (ground rules in SKILL.md). Many independent commands: SWARM.md. Node types, features, and GPU models: HARDWARE.md. Monitoring and sizing from past runs: UTILITIES.md. Jobs that pend, fail, or get killed: TROUBLESHOOTING.md.

Table of contents

- [Batch script template](#batch-script-template)
- [Checklist before handing over](#checklist-before-handing-over)
- [Flags and allocation defaults](#flags-and-allocation-defaults)
- [Partitions and walltime](#partitions-and-walltime)
- [Interactive sessions](#interactive-sessions)
- [GPUs](#gpus)
- [Local scratch and TMPDIR](#local-scratch-and-tmpdir)
- [Exit codes and job states](#exit-codes-and-job-states)
- [Dependencies](#dependencies)
- [Changing or cancelling a job](#changing-or-cancelling-a-job)
- [Multinode MPI jobs](#multinode-mpi-jobs)
- [Scheduler etiquette](#scheduler-etiquette)
- [Licenses, email, and citation](#licenses-email-and-citation)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Batch script template

A threaded single-node job, saved as `/data/$USER/project/job.sh`. Keep the structure; change names, sizes, and the program (`mytool` is a placeholder).

```bash
#!/bin/bash
#SBATCH --job-name=s1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32g
#SBATCH --time=12:00:00
#SBATCH --gres=lscratch:100
set -e                               # a failing step ends the job FAILED

export TMPDIR=/lscratch/$SLURM_JOB_ID
module load mytool                   # finding and pinning modules: MODULES.md
cd /data/$USER/project

cp inputs/s1.dat "$TMPDIR"/
mytool --threads "$SLURM_CPUS_PER_TASK" --tmpdir "$TMPDIR" "$TMPDIR/s1.dat" > "$TMPDIR/s1.out"
cp "$TMPDIR/s1.out" results/         # copy results off lscratch before the script ends
```

Hand it over as a command for the user:

```bash
# on Biowulf (login node) — the user runs:
sbatch /data/$USER/project/job.sh    # prints only the job ID
```

For one command without a script, the user can run `sbatch --cpus-per-task=4 --mem=8g --time=2:00:00 --wrap="mytool --threads 4 in.dat"`. Write the thread count literally: the user's shell would expand `$SLURM_CPUS_PER_TASK` at submission, where it is empty.

## Checklist before handing over

- `--mem` has a unit (`--mem=16g`). A bare number is MB, and the job "will likely" fail.
- Threaded programs get `--cpus-per-task` and read `$SLURM_CPUS_PER_TASK`; without the flag the variable is unset, in batch and interactive jobs alike.
- `--time` and `--mem` come from a measured run plus a small buffer (15–25% on time). Bigger requests wait longer, since smaller jobs are scheduled first.
- One `--gres` flag carries every GRES (`--gres=lscratch:50,gpu:a100:1`); repeated `--gres` flags keep only the last.
- `TMPDIR` is exported to lscratch, and results are copied to `/data` before the script ends.
- `set -e` or `|| fail` checks, so failures end `FAILED` and `afterok` dependents don't run on bad input.
- Partition rules hold: GPUs → `--partition=gpu`, `gpuh200`, or (H200s, under 4 h) `quick`; `largemem` → `--mem` of at least 350g; `multinode` → multi-node MPI only; at most two partitions.
- GPU jobs stay within the CPUs-per-GPU cap.
- No node or GPU types copied from old examples (`x2695`, `x2630`, `k80` are retired; `x2650` is absent from the hardware page).
- `bash -n job.sh` passes, and the core command ran on a small input inside your session (GPU code from a CPU session: a short GPU test job the user submits).

## Flags and allocation defaults

`#SBATCH` lines go at the top, directly after `#!/bin/bash`, one option per line, with `#SBATCH` in column 1. A flag given on the command line overrides the same directive in the script.

| Flag | Meaning on Biowulf |
|---|---|
| `--cpus-per-task=C` | CPUs for one multithreaded process |
| `--mem=Ng`, `--mem-per-cpu=Ng` | memory per node, or per CPU; always with a unit |
| `--time=HH:MM:SS`, `--time=D-HH:MM:SS` | walltime |
| `--partition=P` or `P,Q` | default `norm`; at most two |
| `--gres=lscratch:N,gpu:TYPE:G` | local disk in GB and GPUs, in one flag |
| `--constraint=FEATURE` | node type or feature (HARDWARE.md) |
| `--ntasks=N`, `--ntasks-per-core=1` | processes (MPI ranks); one per physical core, no hyperthreading |
| `--job-name`, `--output`, `--error` | logs default to one `slurm-JOBID.out` in the submit directory |

`--dependency`, `--license`, `--mail-type`, and `--qos=turbo` are covered below; every flag: `man sbatch`.

Slurm on Biowulf allocates by physical core: 1 core = 2 CPUs (hyperthreads), so CPU counts round up to an even number. Jobs share nodes, Slurm keeps each job within its allocated cores and memory, and a job that exceeds its memory is killed.

| Request | Allocation |
|---|---|
| `sbatch job.sh` | 2 CPUs, 4 GB |
| `sbatch --cpus-per-task=4 job.sh` | 4 CPUs, 8 GB (2 GB per CPU) |
| `sbatch --cpus-per-task=16 --mem=24g job.sh` | 16 CPUs, 24 GB |
| `sinteractive` | 2 CPUs, 1.5 GB (768 MB per CPU), 8 h |
| `--exclusive` | every CPU and GPU on the node, but memory is still the request or the per-CPU default (2 GB batch, 0.75 GB interactive) |
| `--exclusive --mem=0` | the whole node, all its memory included |

Programs that "auto-thread" (use every CPU they can see) belong in `--exclusive` jobs.

Inside a job: `SLURM_JOB_ID`; `SLURM_CPUS_PER_TASK` (**unset** unless `--cpus-per-task` was given); `SLURM_NTASKS` (MPI processes); `SLURM_MEM_PER_NODE` (MB, when `--mem` was given; standard Slurm); `SLURM_ARRAY_TASK_ID`; `PORT1`, `PORT2`, … from `sinteractive -T` (TUNNELING.md).

## Partitions and walltime

As of Sept 2026; `batchlim` shows current limits and `freen` the nodes behind each partition.

| Partition | For | Rules |
|---|---|---|
| `norm` | the default; CPU jobs | single node only |
| `quick` | jobs under 4 h | higher priority; dedicated quick nodes plus idle buy-in nodes |
| `largemem` | memory that won't fit on `norm` | `--mem` of at least 350g; nodes up to 3 TB. A 350–747g job also fits `norm`'s largest nodes (HARDWARE.md), so `--partition=norm,largemem` widens its pool |
| `multinode` | MPI jobs across nodes | no single-node jobs (Multinode MPI jobs) |
| `unlimited` | runs over 10 days that can't be split, or a first run of unknown length | small, low per-user CPU limit, older nodes; still set `--time`; maintenance can end jobs |
| `gpu` | GPU software (P100, V100, V100x, A100, L40) | request GPUs with `--gres` (GPUs) |
| `gpuh200` | H200 batch jobs | strict limits (GPUs) |
| `interactive` | `sinteractive` sessions | not in the user guide's table; `batchlim` lists it |
| `visual` | GPU-accelerated remote graphics via `svis` | whole-node allocation (ACCESS.md) |
| `ccr*`, `forgo`, `persist`, … | buy-in nodes | NCI CCR; some NHLBI and NINDS groups; NIMH |

- Give at most two partitions, e.g. `--partition=quick,norm`: the job runs on the first where it can be scheduled, and it must satisfy both, so here `--time` must fit `quick`.
- Priority falls as the user's CPU usage over the last few months grows; `quick` and `interactive` rank above the other partitions.
- Without `--time` a job gets its partition's default (`batchlim`; the documented sample shows 2–8 h for the general partitions). A job that reaches its walltime is killed.
- Walltime maximum is 10 days (`--time=10-00:00:00`) except on `unlimited`; `quick` under 4 h, `gpuh200` 24 h, interactive 36 h (Sept 2026). Formats in the docs: `--time=8:00:00`, `--time=1-12:00:00`, `--time=168:00:00`.
- Asking for 10 days when a job needs 2 only delays its start. Check limit and time used once, not in a loop: `squeue -O jobid,timelimit,timeused -u $USER`. The user can change a walltime with `newwall` (Changing or cancelling a job).

## Interactive sessions

`sinteractive` takes largely the same options as `sbatch` (`sinteractive -h` lists them) and opens a shell on a compute node; `exit` releases it. Size a session that will host you for the heaviest step you'll run in it. The user starts it inside tmux on the login node, since a session dies when its controlling login session exits (the restart recipe in SKILL.md does this).

```bash
# on Biowulf (login node, inside tmux) — the user runs one of:
sinteractive --cpus-per-task=8 --mem=32g --gres=lscratch:50 --time=24:00:00
sinteractive --cpus-per-task=8 --mem=32g --gres=gpu:a100:1,lscratch:50   # the docs' GPU examples omit --partition
```

- **At most two interactive jobs per user**, each up to 36 h, however obtained: every OnDemand app counts (Jupyter, RStudio, VS Code, Shiny) except the Graphical Session, and a third fails to submit. Your own session usually holds one of the two (a Graphical Session terminal doesn't).
- `-T`/`--tunnel` opens ports for a browser app: TUNNELING.md. GPU-accelerated visualization (`svis`): ACCESS.md.
- An interactive shell from `salloc` or `srun` is unsupported; use `sinteractive`.
- Time left in your session: `squeue -j $SLURM_JOB_ID -O jobid,timelimit,timeused`. Before it runs out, ask the user to extend it with `newwall` (36 h cap); lscratch does not outlive the session.
- NIMH users needing more than 36 h can start `spersist` themselves on the `persist` partition: default 2 CPUs and 4 GB, no walltime limit, ends when the login node reboots ([nimh.html#persist](https://hpc.nih.gov/docs/nimh.html#persist)).

## GPUs

Batch GPU jobs name the partition (`gpu`; H200s `gpuh200`) and request GPUs as `--gres=gpu:TYPE:N`. Documented types: `p100`, `v100`, `v100x`, `a100`. Request a GPU only for software built for GPUs. Which GPU to choose: HARDWARE.md; framework setup and multi-GPU training: DEEP-LEARNING.md; checking GPU use: UTILITIES.md.

**CPU cap:** per allocated GPU, at most (node CPUs ÷ node GPUs) CPUs, e.g. 56 ÷ 4 = 14 per P100. Slurm accepts a job over the cap, and it then pends forever. Caps for every type: HARDWARE.md.

```bash
#!/bin/bash
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a100:1,lscratch:100
#SBATCH --cpus-per-task=16
#SBATCH --mem=48g
#SBATCH --time=24:00:00
# 16 CPUs = the A100 cap (16 per GPU); GPU and lscratch share one --gres. Body as in the batch
# script template; nvidia-smi at the top records which GPU the job got
```

Request forms for the user's `sbatch` (flags) and `sinteractive` (Sept 2026):

```bash
--partition=gpu --gres=gpu:v100x:2                             # typed: documented
--partition=gpu --gres=gpu:1 --constraint="gpuv100x|gpua100"   # any listed type: documented pattern (app pages)
--partition=gpu --gres=gpu:1 --constraint=gpul40               # an L40; the type string gpu:l40:1 is unverified — check freen
--partition=gpuh200 --gres=gpu:2                               # H200 batch; gpu:h200:2 is unverified
--partition=quick --gres=gpu:2 --constraint=gpuh200 --time=3:00:00   # H200 nodes in quick
sinteractive --gres=gpu:1,lscratch:50 --constraint=gpuh200     # the one interactive H200; syntax unverified
```

H200 rules ([30 Sep 2026 announcement](https://hpc.nih.gov/nih/about/announcements.php?1223); staff "will adjust these limits as necessary"): `gpuh200` batch jobs need at least 2 H200s and at most 24 h, and a user may hold at most 8 H200s at a time. Each user may take one H200 through `sinteractive` for development and testing. H200 nodes in `quick` take jobs under 4 h. Longer or larger H200 needs: staff@hpc.nih.gov (the user writes). L40s are in `gpu` under the same limits as the other non-H200 types.

## Local scratch and TMPDIR

- `--gres=lscratch:N` reserves N GB of node-local SSD at `/lscratch/$SLURM_JOB_ID`; the top of `/lscratch` isn't writable. Multi-node jobs get N GB on each node. The most one node type offers is its SSD size (HARDWARE.md, or `freen`'s Disk column).
- Copy what you need to `/data` before the script ends. Keeping lscratch files from a failed job: TROUBLESHOOTING.md.
- Many files in one directory slow lscratch for every job on the node; use subdirectories, or delete files once used.
- `TMPDIR` doesn't point at lscratch unless you set it, and can't before the job starts: `export TMPDIR=/lscratch/$SLURM_JOB_ID` in the script or session. `/tmp` holds about 8 GB per node, shared; filling it can crash the node, and repeat incidents can get the user's access suspended.
- Several GRES go in one comma-separated flag (`--gres=lscratch:10,gpu:p100:1`); with repeated `--gres` flags only the last is honored.
- lscratch in swarms: SWARM.md.

## Exit codes and job states

A job's final state is its script's exit status, i.e. that of the last command. A failed step followed by `echo "DONE"` ends `COMPLETED`, even after a step was killed for exceeding memory. Make failures fail:

```bash
set -e                               # stop at the first failing command (a grep with no match counts)
fail() { echo "FAIL: $*" >&2; exit 1; }
module load mytool || fail "module load failed"      # or check only the steps that matter
```

Exit code **123** means maintenance: a downtime script stands in for `sbatch`, `squeue`, and the other Slurm commands. If one of your read-only Slurm queries returns 123, tell the user the batch system is down for maintenance; don't retry in a loop. A submission script the user runs can wait it out: `sbatch job.sh; while [ $? -eq 123 ]; do sleep 120; sbatch job.sh; done`.

States (meanings only; what to do: TROUBLESHOOTING.md): `PD` pending · `R` running · `CG` completing · `CA` cancelled · `F` failed (non-zero exit) · `TO` timeout, killed at its walltime · `NF` node failure · `OOM` out of memory (generic Slurm).

| Pending reason | Meaning |
|---|---|
| `Resources` | the requested CPUs, memory, or GPUs aren't free in that partition yet |
| `Priority` | higher-priority jobs are ahead |
| `Dependency` | waiting for another job |
| `DependencyNeverSatisfied` | its dependency can no longer be met (an `afterok` upstream failed); it will never start |
| `QOSMaxCpuPerUserLimit` | the user is at their CPU limit for the partition (`batchlim`); NIH's FAQ spells it `QOSMaxCpusPerUserLimit` |
| `QOSJobLimit`, `QOSMaxGRESPerUser` | the user is at a job-count or GRES (GPU) limit |
| `Licenses` | waiting for a software license |
| `ReqNodeNotAvail` | a node the job needs is unavailable (down, drained, or reserved) |

All codes: [Slurm job reason codes](https://slurm.schedmd.com/job_reason_codes.html). Finished jobs: `sacct` (today's), `sacct --state f --starttime 2026-09-01` (failures since a date).

## Dependencies

Biowulf's `sbatch` is a wrapper that prints only the job ID (stock Slurm prints `Submitted batch job N`), or `sbatch failed` with exit status 1; `swarm` also prints the ID. So `jid=$(sbatch ...)` captures it.

| Type | The dependent job may start once the listed jobs have… |
|---|---|
| `after:ID[:ID]` | started |
| `afterany:ID[:ID]` | ended, in any state |
| `afterok:ID[:ID]` | ended with exit 0; if one fails, the dependent job never runs |
| `afternotok:ID[:ID]` | failed |
| `singleton` | all earlier jobs with the same name and user ended (e.g. to collate a swarm) |

A job that depends on a swarm or array starts when all its subjobs have finished. When an `afterok` upstream fails, job_dependencies.html says the dependent is cancelled automatically, while swarm.html shows it queued forever as `DependencyNeverSatisfied` (the user then cancels it). After a swarm, prefer `afterany` and have the next script check its inputs. A pipeline script for the user:

```bash
#!/bin/bash
# pipeline.sh — the user runs it on the Biowulf login node: bash pipeline.sh
set -e
jid1=$(sbatch --cpus-per-task=8 --mem=32g --time=6:00:00 align.sh)
jid2=$(swarm -f per_sample.swarm -g 8 -t 4 --time=2:00:00 --dependency=afterok:$jid1)
sbatch --dependency=afterany:$jid2 --mem=16g --time=1:00:00 merge.sh   # merge.sh checks every sample's output exists
```

- A job script can chain its successor with `sbatch --dependency=afterany:$SLURM_JOB_ID next.sh`. That is a submission: fine inside a script the user submits, never something you run in your session.
- `sjobs` shows each job's dependency (UTILITIES.md); the user changes one with `scontrol update` (next section).

## Changing or cancelling a job

All of these are the user's. Hand over the exact line with the real job ID.

```bash
# on Biowulf (login node) — the user runs:
newwall --jobid 12345 --time 8:00:00                  # raise or lower walltime, pending or running (too low → TIMEOUT kill)
scontrol update JobId=12345 dependency=afterany:12300
scontrol update JobID=12345 partition=ccr QOS=ccr     # send a queued job to another partition
scancel 12345
scancel --name=JobName
scancel --user=$USER --state=PENDING                  # all of the user's pending jobs
```

- `newwall` stops at the partition's maximum walltime; beyond that only staff can help (staff@hpc.nih.gov, from the user). Options: `newwall --help`.
- `scancel --user=$USER` with no other filter cancels **every** job the user has, including the session you are running in.

## Multinode MPI jobs

For tightly coupled parallel jobs (usually MPI) that need more cores than one node has. `norm` takes single-node jobs only and `multinode` refuses them. Work that could run as independent tasks belongs in a swarm (SWARM.md), not here.

```bash
#!/bin/bash
#SBATCH --partition=multinode
#SBATCH --constraint=x6140
#SBATCH --ntasks=72
#SBATCH --ntasks-per-core=1
#SBATCH --exclusive
#SBATCH --time=8:00:00
# ONE node type, always (mixed types make fast CPUs wait for slow ones); 72 = 2 nodes x 36 cores; one rank per core
set -e
module load myapp                   # an MPI build; MPI modules and launchers: DEVELOPMENT.md
cd /data/$USER/run1
srun --mpi=pmix_v3 myapp_mpi input.cfg    # or: mpirun -np $SLURM_NTASKS myapp_mpi input.cfg
```

- Node types available in `multinode`: HARDWARE.md. With `--exclusive`, make `--ntasks` a multiple of the node's CPUs (or of its cores, with `--ntasks-per-core=1`) so no capacity sits idle.
- Add `--mem-per-cpu=Ng` only if a process needs more than the default 2 GB per CPU; size it with `jobhist` on the benchmark runs (UTILITIES.md).
- **Benchmark first:** short representative runs on 1, 2, 4, … nodes. Parallel efficiency = work done on N ÷ (N × work done on 1), computed per node if you like. Run at the largest size whose efficiency is above 0.7 (the policy's worked example lands on 128 cores). Staff will ask for proof that a job requesting more than 512 CPUs can use them, and wasted CPU lowers the user's future priority.
- `--qos=turbo` gives higher limits and slightly higher priority to jobs of 8 h or less. "This is only valid on the multinode partition!", and it doesn't excuse skipping the benchmark.
- I/O: estimate total bytes read and written ÷ runtime; about 144 MB/s is near the top of what storage sustains for one user. Put independent per-task temp files on lscratch, and scale up from a few nodes.

## Scheduler etiquette

- Submit at most 1 job per second; no shell loops over globbed job scripts. Use swarm for many jobs (SWARM.md); a script that calls `sbatch` repeatedly can `sleep 1` between calls.
- Prefer swarm to `sbatch --array` ("Use swarm instead of job arrays"). Arrays still work: each task gets 2 CPUs by default, its index is in `$SLURM_ARRAY_TASK_ID`, and `batchlim` shows the maximum array size.
- Don't flood the queue with jobs shorter than 15 minutes: bundle them (SWARM.md). Debugging a failed swarm: SWARM.md (Failures and reruns).
- Never call the raw Slurm binaries behind the `sbatch` and `salloc` wrappers: the wrappers catch typos that the scheduler would accept and then never run. If a wrapper breaks a workflow tool, the user tells staff.

## Licenses, email, and citation

- Licensed software includes MATLAB, IDL, and Mathematica. Batch jobs using licensed software other than MATLAB must pass `--license` (e.g. `--license=idl:6`, the 6 licenses one IDL instance needs), so the job waits for a license instead of starting, failing to get one, and exiting. Availability: `licenses`, or the [System Status](https://hpc.nih.gov/systems/status) page. MATLAB checks out licenses automatically ([Matlab.html#compiledbatch](https://hpc.nih.gov/apps/Matlab.html#compiledbatch) for batch jobs).
- `--mail-type=` takes a comma list of `BEGIN`, `END`, `FAIL`, `REQUEUE`, `ALL` (the first four), `TIME_LIMIT_50`, `TIME_LIMIT_80`, `TIME_LIMIT_90`, `TIME_LIMIT`. Mail goes to `$USER@biowulf.nih.gov`, forwarded to the user's NIH mailbox. Leave `--mail-user` out; if the user wants it, it must be their literal nih.gov address, tested on one job before any swarm or array, since every bounce lands on the staff mail server.
- Citation for publications that made significant use of Biowulf: "This work utilized the computational resources of the NIH HPC Biowulf cluster (https://hpc.nih.gov)." ([userguide#ack](https://hpc.nih.gov/docs/userguide.html#ack))

## Stale advice on the official pages

- Examples still use `x2650` (user guide, multinode policy; absent from the current hardware page) and types retired in April 2026 (`x2695` in the multinode policy, `k80` on the deep-learning pages) → current types from HARDWARE.md or `freen`.
- The user guide says GPU jobs must "specifically request the type"; the Experienced User Guide calls the type optional, and current app pages use untyped `gpu:1` with `--constraint` → both forms are in use.
- sinteractive default memory: the 2020 cheat sheet says 4 GB → 1.5 GB. Ignore the cheat sheet's `--partition=ibfdr` too (`ibfdr` is a node feature).
- The user guide sends readers to "the default walltime in the table above", which no longer exists → `batchlim`. The Experienced User Guide's "up to 10 days by default" → 10 days is the maximum, not the default.
- The user guide's MPI example omits `--partition=multinode` (required: `norm` is single-node) and loads `meep/1.2/mpi/gige` but runs `meme` → use the template above.
- The user guide says MATLAB licenses are interactive-only (since 2016) → Matlab.html documents `sbatch` and swarm jobs with automatic license checkout. Its unquoted `matlab -batch hyp(3,4)` is a bash syntax error → `matlab -batch "hyp(3,4)"`.
- job_dependencies.html's Python example is Python 2 (`commands` module, `print` statements) → port to Python 3 with `subprocess`.

## Going further

- [User Guide](https://hpc.nih.gov/docs/userguide.html) — the source for most of this file: [#submit](https://hpc.nih.gov/docs/userguide.html#submit), [#partitions](https://hpc.nih.gov/docs/userguide.html#partitions), [#gpu](https://hpc.nih.gov/docs/userguide.html#gpu), [#int](https://hpc.nih.gov/docs/userguide.html#int), [#local](https://hpc.nih.gov/docs/userguide.html#local), [#exitcodes](https://hpc.nih.gov/docs/userguide.html#exitcodes), [#modify_job](https://hpc.nih.gov/docs/userguide.html#modify_job).
- [Job dependencies](https://hpc.nih.gov/docs/job_dependencies.html) — types and pipeline scripts; a [mock ChIP-seq pipeline](https://hpc.nih.gov/docs/job_dependencies_example_bash.tgz).
- [Multinode policy](https://hpc.nih.gov/policies/multinode.html) — homogeneous nodes, benchmarking, I/O and memory, turbo, dos and don'ts.
- [Experienced User Guide, Don'ts](https://hpc.nih.gov/docs/ExpUserGuide.html#donts) — scheduler load, wrappers, over-allocation, debugging swarms.
- [Announcements](https://hpc.nih.gov/nih/about/announcements.php) — changes to partitions and limits, such as [?1223](https://hpc.nih.gov/nih/about/announcements.php?1223) (L40, H200, `gpuh200`).
- Live help: `sinteractive -h`, `newwall --help`, `man sbatch` ([online](https://slurm.schedmd.com/sbatch.html)), `batchlim`, `freen`.
