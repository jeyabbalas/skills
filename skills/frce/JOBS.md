How to write, size, and hand over Slurm batch jobs on FRCE: the script template and checklist, flags and defaults, partitions and walltime, GPU requests, per-job temporary files, exit codes and job states, dependencies, changing or cancelling a job, email, MPI, the HPC REST API, and scheduler etiquette. You write and check the scripts; every command here that submits, cancels, or changes a job is the user's to run (ground rules in SKILL.md). Interactive `srun` shells: INTERACTIVE.md. Many independent commands: ARRAYS.md. Watching jobs and sizing from past runs: MONITORING.md. Node and GPU hardware: HARDWARE.md. Jobs that pend, fail, or get killed: TROUBLESHOOTING.md.

Table of contents

- [Batch script template](#batch-script-template)
- [Checklist before handing over](#checklist-before-handing-over)
- [Flags and defaults](#flags-and-defaults)
- [Partitions and walltime](#partitions-and-walltime)
- [GPUs](#gpus)
- [Temporary files](#temporary-files)
- [Exit codes and job states](#exit-codes-and-job-states)
- [Dependencies](#dependencies)
- [Changing or cancelling a job](#changing-or-cancelling-a-job)
- [Email](#email)
- [MPI and multinode jobs](#mpi-and-multinode-jobs)
- [Submitting without logging in](#submitting-without-logging-in)
- [Scheduler etiquette](#scheduler-etiquette)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Batch script template

A threaded single-node job, saved as `/scratch/cluster_scratch/$USER/project/job.sh`; keep the structure (`mytool` is a placeholder).

```bash
#!/bin/bash
#SBATCH --job-name=s1
#SBATCH --partition=norm
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32g
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
set -euo pipefail

source /etc/profile.d/modules.sh 2>/dev/null || true   # `module` in batch shells: MODULES.md
module load mytool/1.2                                  # pin versions (MODULES.md)

TMPDIR=$(mktemp -d "/scratch/local/${USER}_${SLURM_JOB_ID}_XXXX"); export TMPDIR
trap 'rm -rf "$TMPDIR"' EXIT                            # no per-job cleanup of /scratch/local is documented

cd /scratch/cluster_scratch/$USER/project
mytool --threads "$SLURM_CPUS_PER_TASK" --tmpdir "$TMPDIR" in/s1.dat > out/s1.out
```

Keep `set -euo pipefail`. A job's state follows its script's exit status, so without `-e` a failed step followed by a successful one ends `COMPLETED` and `afterok` dependents run on bad input. `-u` stops on an unset variable such as `$SLURM_CPUS_PER_TASK` without `--cpus-per-task`, a bug in several official examples; wrap a sourced setup script that trips it (some conda activation scripts do) in `set +u` … `set -u`.

Check the script yourself (`--test-only` estimates a start without submitting, but may not flag a request over a cap: compare it with [Partitions and walltime](#partitions-and-walltime)), then hand it over:

```bash
# on the compute node (inside your session)
bash -n job.sh && sbatch --test-only job.sh
```

```bash
# on the FRCE login node — the user runs:
cd /scratch/cluster_scratch/$USER/project && mkdir -p logs out
sbatch job.sh                    # where a script needs the ID: jid=$(sbatch --parsable job.sh)
```

For a single command, the user can skip the script: `sbatch -p norm -c 4 --mem=8g -t 2:00:00 --wrap='mytool --threads $SLURM_CPUS_PER_TASK in.dat'`, single-quoted so the variable expands in the job, not at submission.

## Checklist before handing over

- Line 1 is `#!/bin/bash`, and every `#SBATCH` line precedes the first command (sbatch stops reading there). Directives are taken literally, so no `$USER` or `~` in them: use `%u` (user), `%x` (job name), `%j` (job ID), or relative paths.
- The `--output` directory exists before submission; Slurm doesn't create it, and the job fails without a log.
- `--mem` has a unit (`--mem=16g`; a bare number is MB), and `--time` is set: `1:00` is one minute, `1:00:00` one hour.
- Threaded programs get `--nodes=1 --cpus-per-task=N` and read `$SLURM_CPUS_PER_TASK`, never `--ntasks=N` with `$SLURM_NTASKS` ([Flags and defaults](#flags-and-defaults)).
- Sizes come from a measured run plus a buffer (MONITORING.md (Sizing the next run)) and fit the partition's limits ([Partitions and walltime](#partitions-and-walltime)).
- GPU jobs name `--partition=gpu`, a `--gres` string, and a `--time` ([GPUs](#gpus)).
- No Biowulf-only options: lscratch, Biowulf's `--constraint` features (FRCE's: HARDWARE.md (Features and constraints)), or its partitions (FROM-BIOWULF.md (Porting a batch script); the errors they cause: TROUBLESHOOTING.md (Error-string index)).
- Inputs and outputs live on `/scratch/cluster_scratch` or a group share, not `/home`, which is slow (STORAGE.md (Home)); temporary files go in a per-job directory ([Temporary files](#temporary-files)).
- Module versions are pinned, `bash -n` and `sbatch --test-only` pass, and the core command ran on a small input in your session. GPU code checked from a CPU session needs a short GPU test job, which the user submits. Off the cluster, hand the user `bash -n` and `sbatch --test-only` for the login node, and make the first submission a small pilot.

## Flags and defaults

FRCE runs Slurm 24.11.1 (Sept 2026: `sinfo --version`), and the upstream pages describe the newest release, so check `man sbatch` on FRCE when an option is refused.

| Flag | On FRCE |
|---|---|
| `--partition=P` or `P,Q` | default `norm`; a list starts the job in whichever partition can run it first; `--time` can move a job ([Partitions and walltime](#partitions-and-walltime)) |
| `--cpus-per-task=C` | threads of one process; `--ntasks` is processes, e.g. MPI ranks, and without `--nodes=1` Slurm may spread them over several nodes |
| `--mem=Ng`, `--mem-per-cpu=Ng` | memory per node or per CPU; `--mem=0` takes all of each node's memory |
| `--exclusive` | every CPU and GPU on the node, but only the memory requested; add `--mem=0` for all of it |
| `--export=ALL,VAR=val` | default `ALL`: the job inherits the submitting shell's environment, loaded modules included |

What a job gets for an omitted flag (live, Sept 2026); set every one anyway:

- **Memory:** a fixed amount per CPU, 20 GB on most partitions and 8 GB on `gpu` ([Partitions and walltime](#partitions-and-walltime)). It grows with the CPU count: 13 or more CPUs without `--mem` ask for more than the 250 GB of a 48-core Xeon 6342 node (HARDWARE.md (Node types)), so the job waits for the scarcer large-memory nodes, and in `short`, which has only 6342 nodes, it can't run at all.
- **Time:** the partition's default, which is its maximum on `short` and `norm` and effectively unlimited elsewhere ([Partitions and walltime](#partitions-and-walltime)).
- **CPUs:** one, and a CPU is a physical core: every compute node runs one thread per core, except the Dragen servers with two (`sinfo -e -o '%P %c %z'`). Biowulf counts differently: FROM-BIOWULF.md.

Inside a job, the standard `SLURM_*` variables are set, with these to watch: `SLURM_CPUS_PER_TASK` is **unset** without `--cpus-per-task`, and `SLURM_NTASKS` (= `SLURM_NPROCS`) without an `--ntasks*` option; `SLURM_MEM_PER_NODE` is `--mem` in MB; `SLURM_JOB_PARTITION` is where the job runs after any move by `--time`; `SLURM_CLUSTER_NAME` is `fnlcr`; `SLURMD_NODENAME` is the node's Slurm name, `cnNNN`; each array task has its own `SLURM_JOB_ID` (index: `SLURM_ARRAY_TASK_ID`, ARRAYS.md).

## Partitions and walltime

Live, Sept 2026 (`scontrol show partition NAME`, `sacctmgr show qos format=Name,MaxTRESPerUser%90`); the official partition page's numbers are stale ([Stale advice](#stale-advice-on-the-official-pages)). "None" means no maximum and a default of 8,333 days.

| Partition | Default / max time | Per user, all jobs together | Default memory | For |
|---|---|---|---|---|
| `norm` | 5 days / 5 days | 600 CPUs | 20 GB per CPU | the default; CPU jobs |
| `short` | 30 min / 30 min | 170 CPUs | 20 GB per CPU | tests and quick jobs; scheduled ahead of `norm` on the nodes they share |
| `unlimited` | none | 432 CPUs | 20 GB per CPU | CPU jobs longer than 5 days |
| `largemem` | none | 192 CPUs (both nodes) | 16 GB per CPU | two 3 TB nodes (HARDWARE.md (Large memory and Dragen)) |
| `gpu` | none | 1,200 CPUs; 40 GPUs, of which at most 2 A100, 4 H200, 26 L40S, 33 P100 | 8 GB per CPU | every GPU type ([GPUs](#gpus)) |
| `nci-dragen` | none | 64 CPUs (the one server) | 500 GB per node | the Illumina Dragen server, open to all (APPLICATIONS.md) |
| `dragen` | none | 256 CPUs | 200 GB per node | the CCR Sequencing Facility's accounts only |
| `csbdevel` | 5 days / 5 days | 642 CPUs | 20 GB per CPU | a few named accounts: "a priority channel for a set of programmers who make frequent changes to their code" |

- **Caps.** Each is a per-user limit of the partition's QOS and counts all of the user's running jobs there, interactive sessions and OnDemand apps included ([pending reasons](#exit-codes-and-job-states)). There are no per-user job-count or submission limits. The submit filter picks each job's QOS: `<partition>_<username>` where the administrators have granted that user larger caps (ACCESS.md (Support and requests)), otherwise the partition's own.
- **Nothing is refused for breaking a limit** (`EnforcePartLimits=NO`): a job larger than a cap (700 CPUs on `norm`), or for a partition the user's account may not use (`dragen`, `csbdevel`), is accepted and pends forever; only a request no node in the partition can hold is refused (HARDWARE.md (Node types)). Check requests against the table.
- **`--time` picks among `short`, `norm`, and `unlimited`.** The submit filter (`/etc/slurm/job_submit.lua`) moves a job submitted to any of the three to the one its `--time` fits: up to 30 minutes `short`, up to 5 days `norm`, beyond that `unlimited`. A 20-minute `norm` job therefore runs in `short`: under its 170-CPU cap, and on its nodes only, so a request bigger than a `short` node is refused. A `--time` over 30 minutes keeps a job in `norm`. Nothing moves without `--time` (the job keeps its partition and that partition's default) or with a list such as `--partition=short,norm`. No `--partition` at all means `norm`. `squeue` shows where a job landed.
- **Set `--time` even where there's no maximum:** a realistic limit lets the backfill scheduler start the job in gaps sooner, and a hung job stops. Jobs in `norm` and `csbdevel` may overrun their `--time` by up to 60 minutes (`OverTimeLimit`) before they're ended; don't size to that grace.
- No `debug` (still in XDMoD's history) or `norm-oel8` (a 2023 name in published FRCE scripts) exists; Biowulf's partitions: FROM-BIOWULF.md (Translation table). Typical waits: MONITORING.md (Cluster load and wait times).

## GPUs

- Request `--partition=gpu --gres=gpu:TYPE:N`, TYPE one of `p100`, `v100`, `a100`, `l40s`, `h200` (live, Sept 2026: `sinfo -p gpu -o '%G'`); there is no `l4`. Untyped `--gres=gpu:N` takes any type, a P100 or V100 included, which code built for newer GPUs may not run on (DEVELOPMENT.md (CUDA and cuDNN), DEEP-LEARNING.md (Choosing a GPU)).
- Without `--partition=gpu`, a `--gres` request goes to the default `norm`, which has no GPUs: always name the partition.
- Ask for more than one GPU only if the program uses several (QuickStart warns that many can't), and never for more than one node holds (HARDWARE.md (GPUs)). Per-user GPU caps: [Partitions and walltime](#partitions-and-walltime).
- Keep CPUs and memory within the node's per-GPU share (HARDWARE.md (GPUs)); nothing enforces it. GPU jobs wait longest (MONITORING.md (Cluster load and wait times)), so small requests and an accurate `--time` matter most here.
- Free GPUs by type: `freen` (MONITORING.md). OnDemand forms offer fewer types (ONDEMAND.md (Apps and their forms)).

```bash
#!/bin/bash
#SBATCH --partition=gpu
#SBATCH --gres=gpu:l40s:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64g
#SBATCH --time=08:00:00
set -euo pipefail
nvidia-smi -L                    # records which GPU the job got
# the rest as in the batch script template; framework setup: DEEP-LEARNING.md
```

## Temporary files

FRCE has no per-job scratch: no `lscratch` GRES, no directory Slurm makes for the job, and no documented per-job cleanup of `/scratch/local`. All jobs on a node share it, and the `TMPDIR` a job inherits is per user, not per job (STORAGE.md (Node-local scratch)), so each job makes, exports, and removes its own directory, as the template does:

```bash
# in the job script, after set -euo pipefail
TMPDIR=$(mktemp -d "/scratch/local/${USER}_${SLURM_JOB_ID}_XXXX"); export TMPDIR   # mode 0700, unique per job and array task
trap 'rm -rf "$TMPDIR"' EXIT
```

- The trap runs when the script ends, fails under `set -e`, or receives Slurm's SIGTERM at the time limit or on `scancel`. It can't run after the SIGKILL that follows 264 s later (`KillWait`), or when a node fails; those leftovers stay behind, identifiable by the job ID in their name.
- Write results to `/scratch/cluster_scratch` before the script ends: the trap deletes the directory.
- Temporary files that several nodes must see, or that may outgrow the node's disk, go in `mktemp -d -p /scratch/cluster_scratch/$USER` with the same trap.
- Most programs honor `TMPDIR`; others need a flag: `samtools sort -T "$TMPDIR"`, `java -Djava.io.tmpdir="$TMPDIR"`, GATK's `--tmp-dir`. Containers: CONTAINERS.md (Containers in jobs).
- Staging inputs onto `/scratch/local` buys little speed (STORAGE.md (Node-local scratch)); use it for scratch files.
- Skip `--tmp=SIZE`: it reserves nothing, only filters nodes by their configured temporary disk (`sinfo -N -o '%N %d'`).

## Exit codes and job states

A batch job's exit code is its script's exit status; any non-zero value ends it `FAILED` (reason `NonZeroExitCode`). `sacct` prints `ExitCode` as `code:signal`: `0:0` success, `1:0` exit 1, `0:9` killed by signal 9. A command killed by a signal gives the shell 128 plus the signal number: `137` SIGKILL (often memory), `139` segfault, `143` SIGTERM.

What to do about a job's state: TROUBLESHOOTING.md (Job killed or failed).

| Pending reason | Meaning |
|---|---|
| `Resources` | the requested CPUs, memory, or GPUs aren't free in the partition yet |
| `Priority` | higher-priority jobs are ahead; priority weighs "the job history of the submitter" ([Services](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/Services)), fair share above all (MONITORING.md (Your jobs now)) |
| `Dependency`, `DependencyNeverSatisfied` | waiting for another job; the second can never run (an `afterok` upstream failed), and FRCE cancels it ([Dependencies](#dependencies)) |
| `QOSMaxCpuPerUserLimit`, `QOSMaxGRESPerUser` | the user is at a partition's CPU or GPU cap; a job bigger than the cap never starts |
| `PartitionTimeLimit`, `AccountNotAllowed` | `--time` exceeds the partition's limit, or the user's account may not use the partition; it never starts |
| `ReqNodeNotAvail` | a node the job needs is down, drained, or reserved, often for maintenance |
| `JobHeldUser`, `JobHeldAdmin` | held; the user releases the first, the admins the second |

Every code: [job reason codes](https://slurm.schedmd.com/job_reason_codes.html). Where to see them: MONITORING.md (Your jobs now).

## Dependencies

FRCE's `sbatch` is stock Slurm and prints `Submitted batch job 40164997`, so a script captures the ID with `jid=$(sbatch --parsable job.sh)`; Biowulf-style `jid=$(sbatch job.sh)` captures the whole sentence.

- Types, as upstream: `afterok`, `afterany`, `afternotok` (non-zero exit, timeout, or node failure), `after` (started), `singleton`, and `aftercorr` for arrays (ARRAYS.md). Join them with `,` (all must hold) or `?` (any one), not both.
- When an `afterok` upstream fails, the dependent can never run, and FRCE cancels it (`SchedulerParameters=kill_invalid_depend`, live Sept 2026); `--mail-type=INVALID_DEPEND` reports it.
- Submit an `afterok` or `afternotok` dependent while the upstream is queued or running, or within 5 minutes of its end (`MinJobAge`); Slurm rejects an ID it no longer knows.

```bash
#!/bin/bash
# pipeline.sh — the user runs it on the FRCE login node: bash pipeline.sh
set -euo pipefail
cd /scratch/cluster_scratch/$USER/project
jid1=$(sbatch --parsable align.sh)
jid2=$(sbatch --parsable --dependency=afterok:$jid1 call.sh)
sbatch --dependency=afterany:$jid2 report.sh   # report.sh checks that its inputs exist
```

A job script may submit its own successor (`sbatch --dependency=afterany:$SLURM_JOB_ID next.sh`): fine inside a script the user submits, never from your session.

## Changing or cancelling a job

All of these are the user's; hand over each line with the real job ID. FRCE has no `newwall`.

```bash
# on the FRCE login node — the user runs:
scontrol update JobId=12345 TimeLimit=8:00:00     # pending: raise or lower, up to the partition's limit; running: lower only
scontrol update JobId=12345 Partition=unlimited   # pending jobs only
scontrol update JobId=12345 Dependency=afterany:12300
scontrol hold 12345                               # keeps a pending job from starting; undo: scontrol release 12345
scancel 12345                                     # an array's ID cancels every task
scancel -u $USER --state=PENDING                  # all of the user's pending jobs
scancel -u $USER -n vscode-cpu                    # by job name
```

- "Only a privileged user can increase a running or suspended job's TimeLimit" ([scontrol](https://slurm.schedmd.com/scontrol.html#OPT_TimeLimit)): the user asks the FRCE administrators (ACCESS.md (Support and requests)) well before it runs out.
- A running job's CPUs, memory, and GPUs can't change; the user cancels and resubmits.
- `scancel -u $USER` with no other filter cancels every job the user has, including the session you run in, OnDemand apps, and VS Code allocations.

## Email

- `--mail-type=END,FAIL` mails when the job ends or fails; also useful: `INVALID_DEPEND` (a dependency that can never be met), `TIME_LIMIT_80`, and `ARRAY_TASKS` (one mail per array task instead of one per array).
- Always set `--mail-user` to the user's NIH address. Without it, Slurm mails "the submitting user" ([sbatch](https://slurm.schedmd.com/sbatch.html#OPT_mail-user)), and FRCE sets no mail domain (`MailDomain` unset, live Sept 2026), so the mail goes to the bare username and where it lands is unknown. FRCE's own example scripts mail `$USER@mail.nih.gov`: write the address out in a directive, or pass `--mail-user=$USER@mail.nih.gov` on the `sbatch` command line. Test on one job before an array.
- Mail as a way to wait for a job: MONITORING.md (Waiting for a job without polling).

## MPI and multinode jobs

For tightly coupled programs, usually MPI, that need more cores than one node has; independent tasks belong in an array (ARRAYS.md).

- FRCE has no `multinode` partition and needs none: every partition takes multi-node jobs (`MaxNodes=UNLIMITED`, live Sept 2026), within the per-user CPU cap, as the [Open MPI page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/AdditionalLibraries/openMPI)'s 4-node example in the default partition assumes. Network: HARDWARE.md (Interconnect).
- Ranks land on whatever node types the partition has (HARDWARE.md (Partitions and node types)) unless a feature pins one, e.g. `--constraint=x6342` (HARDWARE.md (Features and constraints)). Keep `--ntasks-per-node` within the smallest node the job may get.

```bash
#!/bin/bash
#SBATCH --job-name=mpi1
#SBATCH --partition=norm
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=32
#SBATCH --mem=120g
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true
module load openmpi/5.0.9        # the Open MPI the program was built with (DEVELOPMENT.md (MPI))
cd /scratch/cluster_scratch/$USER/run1
mpirun ./myapp_mpi input.cfg     # 64 ranks: the rank count and hosts come from the allocation
# or Slurm's direct launch: srun --mpi=pmix ./myapp_mpi input.cfg
```

- Launch with `mpirun`, or with `srun --mpi=pmix`, never bare `srun` (why, and the plugins: DEVELOPMENT.md (MPI)). `--mem` is per node.
- Hybrid MPI and threads: add `--cpus-per-task=T` to the header. `mpirun` reads it from the environment, and so does `srun` in Slurm 23.11 and later, FRCE's 24.11 included.
- Benchmark on 1, 2, and 4 nodes before scaling; stop adding nodes when the speed-up per node falls off (QuickStart's Amdahl's-law warning).

## Submitting without logging in

**HPC REST API.** Version 0.0.1 from 2019, "provided by the Biowulf team" ([HPC REST API](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/HPCAPI)). A POST to `hpcapi.ncifcrf.gov`, served by the login node, submits a job as the user, authenticated by their Kerberos ticket, from the NIH network or VPN. Both calls are the user's: `submit_job` submits (ground rule 1), and each needs their ticket.

- JSON fields: `script-body` (the whole script, shebang included) and `partition` are required. Optional: `cpus-per-task`, `ntasks`, `ntasks-per-node`, `ntasks-per-core`, `mem-per-node` (= `--mem`), `mem-per-cpu` (not both), `dependency`, and `timelimit` (`DD-HH:MM:SS`). Value formats beyond `timelimit` are undocumented, so try a tiny job first.
- `#SBATCH` lines in the body "will be stripped out", so resources go in the fields, and the whole POST must stay under 4 KB (error `postdata_too_big`).
- "Not all partitions currently may receive API jobs" (error `bad_partition`); the user asks the FRCE administrators for the current list.
- The job starts outside any login shell: initialize `module` first (MODULES.md (Modules in batch jobs and scripts)). Where its output goes is undocumented, so redirect it into an existing directory at the top of the body: `exec > /scratch/cluster_scratch/USERNAME/api/$SLURM_JOB_ID.log 2>&1`.
- There is no cancel call: the user runs `scancel JOBID` on a login node.

```bash
# on the user's computer (NIH network or VPN) — the user runs:
klist                            # needs krbtgt/NIH.GOV@NIH.GOV; if missing: kinit USERNAME@NIH.GOV
jq -n --rawfile body job.sh '{partition: "norm", "script-body": $body, timelimit: "00-02:00:00"}' > job.json
wc -c < job.json                 # must stay under 4096
curl -s -X POST -H 'Content-Type: application/json' --negotiate -u : -d @job.json https://hpcapi.ncifcrf.gov/hpcapi/submit_job
# success: {"status": "call_success", "reason": "46185772"}, the reason being the job ID
curl -s --negotiate -u : https://hpcapi.ncifcrf.gov/hpcapi/query_status | jq   # the user's jobs of the last 24 h
```

**Web applications.** Approved web applications "always run the jobs under a dedicated service account" ([Submit from a web application](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/Submitwebapplication)). Each site is vetted, managed by the EIT Linux Systems team, and logs individual submissions, and the FRCE administrators can revoke the privilege; to set one up, the user contacts them (ACCESS.md (Support and requests)). OnDemand apps also start jobs from a browser: ONDEMAND.md.

## Scheduler etiquette

"FRCE has very few hard restrictions, with most policies running along the lines of being considerate of other users" ([policies](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/MiscellaneousPoliciesandGuidelines)).

- "Please do not request a large number of cores without considering if these cores can be used effectively" ([Quick Start](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart)). Single-threaded programs get 1 CPU; threaded ones get the count their documentation recommends, since doubling cores "may not double the performance" (Amdahl's law) and can slow a program down.
- Many similar jobs go in one array, not a shell loop of `sbatch` calls, and tasks of a few minutes get bundled (ARRAYS.md). A script that must submit many separate jobs pauses between calls (`sleep 1`).
- Idle interactive sessions and OnDemand apps hold cores and GPUs others need, and they count against the user's own per-partition cap (INTERACTIVE.md).
- Request GPUs only for GPU code, and end the job when the GPU work is done.

## Stale advice on the official pages

- [Quick Start](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart): its GPU batch recipe swaps in `--partition=gres=gpu:p100:1` → `--partition=gpu` plus `--gres=gpu:p100:1`, with the types in [GPUs](#gpus). Its hello.sh sets `--time=1:00`, which is one minute → `--time=01:00:00` for an hour.
- The [Slurm Partitions & Features](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/SlurmPartitionsFeatures) page's caps are stale: "Max Cores Per User" 575 on `norm` (the default QOS's cap; the partition's is 600) and 350 on `gpu` (now 1,200), and the `gpu` row's "24 P100 GPUs 48 V100 GPUs 4 A100 GPUs 32 L40s GPUs 8 H200 GPUs" (per-user caps are now 33, 64, 2, 26, and 4, with 40 in all). It also leaves out the default memory and the `--time` moves → [Partitions and walltime](#partitions-and-walltime).
- The same page says the `#!/bin/bash` line is needed or "SLURM will not let the script be submitted" → any interpreter line is accepted (QuickStart's example uses `#!/bin/sh`); only a missing one fails (APPLICATIONS.md (Fixing the official examples)). Use `#!/bin/bash` for `module` and bash syntax.
- Its first example asks `--ntasks=8` for what its text calls CPU cores, and its printf `{}` is never filled in → `--cpus-per-task` and `%s`.
- Several app pages and the Snakemake page request CPUs for threaded programs as `--ntasks=N` and pass `$SLURM_NTASKS` as the thread count, though Slurm may spread those tasks over several nodes → `--nodes=1 --cpus-per-task=N` and `$SLURM_CPUS_PER_TASK`. Which pages: APPLICATIONS.md (Fixing the official examples); WORKFLOWS.md (Stale advice on the official pages).
- [AlphaFold](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/StructuralBiology/AlphaFold) has the user copy the ID from "Submitted batch job" into `--dependency=afterok:########` by hand → `--parsable` ([Dependencies](#dependencies)).
- Biowulf's user guide, which FRCE calls "largely applicable", puts `-o ~/myjob.out` in a directive line → `~` isn't expanded there ([Checklist before handing over](#checklist-before-handing-over)).
- [HPC REST API](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/HPCAPI) documents response keys `Status` and `Reason` with values "call success" and "call failure" → the service returns `status` and `call_success`. Its "ntasks-per-node: number of tasks per core" means per node; the "service ticket for hpcjobapi" is `HTTP/hpcapi.ncifcrf.gov@NIH.GOV`; and "OTHER ERRORS REMAIN TO BE DOCUMENTED!"

## Going further

- FRCE: [Quick Start](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart) (running jobs), [Slurm Partitions & Features](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/SlurmPartitionsFeatures), [Miscellaneous Policies and Guidelines](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/MiscellaneousPoliciesandGuidelines), [HPC REST API](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/HPCAPI), [Submit from a web application](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/Submitwebapplication), [Slurm user guides](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/Slurmuserguides) (the tutorials FRCE recommends).
- Biowulf docs, which need translating (FROM-BIOWULF.md): [job dependencies](https://hpc.nih.gov/docs/job_dependencies.html) (pipeline scripts, once `--parsable` is added), [userguide#exitcodes](https://hpc.nih.gov/docs/userguide.html#exitcodes) (why a failed step can still end COMPLETED).
- Slurm: [sbatch](https://slurm.schedmd.com/sbatch.html), with [dependencies](https://slurm.schedmd.com/sbatch.html#OPT_dependency) and [mail types](https://slurm.schedmd.com/sbatch.html#OPT_mail-type); [srun](https://slurm.schedmd.com/srun.html); [job reason codes](https://slurm.schedmd.com/job_reason_codes.html); [job exit codes](https://slurm.schedmd.com/job_exit_code.html); [MPI guide, Open MPI](https://slurm.schedmd.com/mpi_guide.html#open_mpi). Open MPI: [launching with Slurm](https://docs.open-mpi.org/en/v5.0.x/launching-apps/slurm.html).
- Live: `sinfo -s`, `scontrol show partition NAME`, `scontrol show config`, `sacctmgr show qos format=Name,MaxTRESPerUser%90`, `sbatch --test-only job.sh`, `man sbatch`.
