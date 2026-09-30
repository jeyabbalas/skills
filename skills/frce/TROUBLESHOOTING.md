When something on FRCE breaks: a read-only triage, then sections by symptom (a job that pends too long, a job killed or refused, a process killed on the login node, software and environment problems, access and connection problems), an index of exact error strings, and a template for asking the FRCE administrators. The diagnosis commands here are yours to run in your session (off the cluster, hand them to the user); resubmitting, cancelling, or changing a job and every message to the administrators are the user's, and destructive fixes (deleting caches, editing dotfiles) need their go-ahead (ground rules in SKILL.md). What states and pending reasons mean: JOBS.md (Exit codes and job states). Monitoring commands and sizing from past runs: MONITORING.md. Rerunning failed array tasks: ARRAYS.md (Failures and reruns). Workflow drivers: WORKFLOWS.md.

Table of contents

- [Triage](#triage)
- [Job pending too long](#job-pending-too-long)
- [Job killed or failed](#job-killed-or-failed)
- [Killed on the login node](#killed-on-the-login-node)
- [Software and environment problems](#software-and-environment-problems)
- [Access and connection problems](#access-and-connection-problems)
- [Error-string index](#error-string-index)
- [Asking for help](#asking-for-help)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Triage

Run each once; all are read-only.

1. **Where.** SKILL.md's where-am-I check. Many failures are the wrong host: a GPU program on the transfer node (`No CUDA GPUs are available`), a long command on the login node ([Killed on the login node](#killed-on-the-login-node)).
2. **State.** `squeue --me` for pending reasons, `scontrol show job JOBID` for the rest while Slurm still knows the job (MONITORING.md (Your jobs now)).
3. **History.** `sacct -j JOBID` in MONITORING.md (Finished jobs)'s format, plus `NodeList`, and `seff JOBID`: which step failed, how, where, and at what memory (`ExitCode`: JOBS.md (Exit codes and job states)).
4. **Logs.** Tail the `StdOut` file (`slurm-JOBID.out` by default). Slurm's own messages (time limit, out of memory, node failure) come last; look them up in the [error-string index](#error-string-index).
5. **Space.** `No space left on device` or `Disk quota exceeded`: a quota, or the shared scratch file system filling up, which fails writes far below the user's own quota (the checks: STORAGE.md (Checking usage and quotas); what fills home: STORAGE.md (Home)).
6. **The cluster.** Status page and announcements: ACCESS.md (Status and maintenance); load per partition: MONITORING.md (Cluster load and wait times).
7. **Reproduce** the failing step on a small input in your session before handing the user a fix or a resubmission. A memory failure too big for your session is sized instead: MONITORING.md (Sizing the next run).

## Job pending too long

A job's own request is the usual cause: small probe jobs typically start within seconds (MONITORING.md (Cluster load and wait times)). What each reason means: JOBS.md (Exit codes and job states). Each fix is a change the user makes:

| Reason | What helps |
|---|---|
| `Priority`, `Resources` | Normal on a busy partition. Smaller requests start sooner: size from the last run (MONITORING.md (Sizing the next run)) and check what's free with `freen`. GPU jobs wait far longer than CPU jobs; if any GPU type will do, an untyped request widens the pool (JOBS.md (GPUs)). |
| `QOSMaxCpuPerUserLimit`, `QOSMaxGRESPerUser` | The user is at a partition's per-user CPU or GPU cap (JOBS.md (Partitions and walltime)): the job starts as their running jobs end, and one job bigger than the cap never starts. Staff grant some users higher caps "based on past usage and research need" (FRCE's submit filter): the user can ask (ACCESS.md (Support and requests)). |
| `PartitionTimeLimit` | `--time` exceeds the partition's maximum, so it never starts. The user lowers it in place or moves the job (JOBS.md (Changing or cancelling a job)). |
| `AccountNotAllowed` | `dragen` or `csbdevel`, which only named accounts may use: the user cancels it and resubmits elsewhere. |
| `PartitionNodeLimit`, `BadConstraints`, `PartitionConfig` | More nodes, a feature, or a shape the partition can't give: fix the request (HARDWARE.md (Partitions and node types)) and resubmit. |
| `ReqNodeNotAvail`, `NodeDown`, `PartitionDown`, `Reservation` | Nodes down, draining, or reserved: check the status page, and drop a `--nodelist` or `--exclude` the job doesn't need. |
| `Dependency` | Waiting by design (JOBS.md (Dependencies)). |
| `DependencyNeverSatisfied` | An `afterok` upstream failed, and FRCE cancels such jobs (JOBS.md (Dependencies)), so `sacct` shows it `CANCELLED`: the user resubmits it once the upstream is fixed. |
| `JobHeldUser`, `JobHeldAdmin` | Held: `scontrol release JOBID` (the user's), or ask the administrators. |

- A job over a limit is accepted and pends forever with one of these reasons (JOBS.md (Partitions and walltime)); only a request that no node in the partition could hold is refused at submission ([Refused at submission](#refused-at-submission)).
- **Moved by `--time`.** The submit filter moves a job among `short`, `norm`, and `unlimited` to fit its `--time`, and `squeue --me` shows where it landed: a brief `norm` job pending as `QOSMaxCpuPerUserLimit` while `norm` has room is under `short`'s smaller cap. The rules, and how to stay in `norm`: JOBS.md (Partitions and walltime).

## Job killed or failed

| You see | Likely cause | Next |
|---|---|---|
| state `OUT_OF_MEMORY`; `oom-kill` or `oom_kill event` near the end of the log | memory | a larger `--mem`, sized as MONITORING.md (Sizing the next run) says for a killed job; beyond the partition's nodes: `largemem` (HARDWARE.md (Large memory and Dragen)). Without `--mem` the job got the partition's per-CPU default (JOBS.md (Flags and defaults)) |
| `TIMEOUT`; `CANCELLED AT … DUE TO TIME LIMIT` | walltime | the measured time plus a buffer (MONITORING.md (Sizing the next run)), or checkpoint and resume. Partition maxima, and the `norm` overrun that lets `Elapsed` exceed `Timelimit`: JOBS.md (Partitions and walltime); a running job's limit: JOBS.md (Changing or cancelling a job) |
| `FAILED` with an exit code | the program or the script | the log's last lines (codes: JOBS.md (Exit codes and job states)); 127, command not found, usually means a module wasn't loaded |
| `COMPLETED`, but outputs missing or empty | a failed step followed by a successful last command | `set -euo pipefail` (JOBS.md (Batch script template)); even then, a failure inside an `if` test or an `&&`/`\|\|` list doesn't stop the script |
| `CANCELLED` | the user's `scancel`, a dependency that can never be met ([Job pending too long](#job-pending-too-long)), or an administrator | ask the user before proposing a resubmission |
| `NODE_FAIL`, `BOOT_FAIL`; `DUE TO NODE FAILURE` | the node, not the job | the user resubmits unchanged; if it recurs, the administrators get the job IDs and node names |
| an `srun` shell ends after 30 minutes | `-p short` without `--time`, as in the InteractiveAccess page's "general command" | a sized `norm` session (INTERACTIVE.md (Interactive shells with srun)) |
| an `srun` shell, and you with it, gone after a disconnect or a login-node reboot | its client runs on the login node | tmux there; better, tmux on a batch job's node (INTERACTIVE.md (Interactive shells with srun)) |

### Refused at submission

Biowulf habits, as FRCE users hit them (CCBR's first FRCE runs, [CHARLIE#99](https://github.com/CCBR/CHARLIE/issues/99), 2024), plus copies of official examples:

| `sbatch` prints | Cause | Fix |
|---|---|---|
| `sbatch: error: Invalid generic resource (gres) specification` | `--gres=lscratch:N`, or a GPU type FRCE lacks (`v100x`, `l40`) | drop lscratch (JOBS.md (Temporary files)); FRCE's GPU types (JOBS.md (GPUs)) |
| `sbatch: error: invalid partition specified: ccr`, then `Invalid partition name specified` | a Biowulf partition (`ccr`, `quick`, `multinode`, `gpuh200`, `interactive`), the retired `norm-oel8`, or QuickStart's `--partition=gres=gpu:p100:1` typo | FRCE's partitions (JOBS.md (Partitions and walltime)) |
| `sbatch: error: CPU count per node can not be satisfied` (or `Memory specification can not be satisfied`), then `Requested node configuration is not available` | more CPUs or memory per node than the partition's nodes have (Biowulf's 56-thread rules failed; 32 ran), or a `--time` that moved a `norm` job to `short` or `unlimited`, whose nodes are smaller ([Job pending too long](#job-pending-too-long)); more GPUs than a node holds usually gets the last line alone | fit a node type (HARDWARE.md (Partitions and node types)) |
| `Invalid feature specification` | a Biowulf `--constraint` (`x6140`, `gpua100`) | FRCE's feature for the same need, or none (HARDWARE.md (Features and constraints)) |
| `This does not look like a batch script` | no `#!` first line (the cellpose page's script) | `#!/bin/bash` as line 1 (JOBS.md (Batch script template)) |
| `sinteractive: command not found`, `swarm: command not found` | Biowulf-only tools | INTERACTIVE.md (Interactive shells with srun); ARRAYS.md (Converting a Biowulf swarmfile) |

## Killed on the login node

SKILL.md's 10 CPU-minute kill is a CPU-time limit per process (ACCESS.md (Connecting)), not a watchdog (live, Sept 2026), and jobs don't inherit it. Its soft and hard limits are equal, so at the limit Linux sends SIGKILL and the promised "cryptic error message" is the shell's `Killed` (exit status 137), not `CPU time limit exceeded` (SIGXCPU), which needs a lower soft limit (read from the limits file and the kernel source, not observed; the user's `ulimit -St; ulimit -Ht` on batch shows both). An idle shell lasts for days, but any process that works ten CPU-minutes dies: a long compile step, an `rsync` or `tar` of a big tree, a `pip` or conda solve, an R or Python session, a workflow driver, a VS Code server, an agent, or, after days of heavy output, tmux's server or an `srun` client.

| Work | Move it to |
|---|---|
| computing, R or Python sessions, workflow drivers, agents | an `srun` session (INTERACTIVE.md (Interactive shells with srun)) or a batch job (JOBS.md) |
| `scp`, `rsync`, downloads | the transfer node, batch2 (TRANSFER.md (Where to run transfers)) |
| compiling | an `srun` session, or batch2 (DEVELOPMENT.md (Where to build)) |
| GUI programs (MATLAB, RELION) | an OnDemand desktop (ONDEMAND.md) |
| VS Code | `frce-cpu` (INTERACTIVE.md (VS Code on a compute node)): Remote-SSH straight to batch runs the VS Code server on the login node |

Whether batch2 and nx set the same limit: ACCESS.md (Connecting).

## Software and environment problems

Exact error strings from modules, conda, Python, containers, CUDA, and compilers are in the [error-string index](#error-string-index), each with the file that fixes it. Problems without one telltale string:

- **It used to work.** An unpinned `module load` moved to a newer default (MODULES.md (Loading and pinning versions)); in 2023, unpinned loads even resolved to different versions on different node pools ([XAVIER#31](https://github.com/CCBR/XAVIER/issues/31)).
- **Python imports fail or load the wrong versions.** Packages in `~/.local`, a `python` module's `PYTHONHOME` and `PYTHONPATH` under a venv or another interpreter, and application modules that add their own site-packages (snakemake: WORKFLOWS.md (Snakemake)) shadow an environment's packages or break its interpreter: PYTHON-R.md (Python on FRCE).
- **Downloads and pulls fail on compute nodes.** Compute nodes normally reach the internet directly, but access has lapsed before: the one-time check, the fallback, and certificate errors are in TRANSFER.md (Downloads on the cluster). A `TLS handshake timeout` during an image pull that passes the check is usually the remote end: retry once.
- **A share vanishes on compute nodes.** In May 2024, paths under `/mnt/projects` existed on the login node but gave `No such file or directory` in jobs ([CHARLIE#99](https://github.com/CCBR/CHARLIE/issues/99)). The user reports it with host names and job IDs ([Asking for help](#asking-for-help)); don't copy data around it.
- **OnDemand** pages or apps that won't load, start, or connect: ONDEMAND.md (When OnDemand misbehaves).

## Access and connection problems

Every fix here is the user's, with the steps in ACCESS.md.

| Symptom | Cause | Fix in |
|---|---|---|
| `Could not resolve hostname batch.ncifcrf.gov` or `Could not resolve host`; the browser can't find ondemand.ncifcrf.gov | off the NIH network | ACCESS.md (Connecting): VPN |
| password refused | an `NIH\` prefix or capitals in the username | ACCESS.md (Connecting) |
| key login fails, or VS Code keeps prompting | key not installed, or not loaded in an agent | ACCESS.md (SSH keys and clients); INTERACTIVE.md (VS Code on a compute node) |
| VS Code times out connecting to `frce-cpu` or `frce-gpu` | the allocation is still queued, and a retry may queue a second | INTERACTIVE.md (VS Code on a compute node) |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | a changed host key | ACCESS.md (Connecting): ask the administrators first |
| `Permission denied` under `/mnt/...` | not in the share's AD group | ACCESS.md (Accounts and groups); STORAGE.md (Group shares) |

## Error-string index

Grep the log for these; substrings are enough.

| String | Means | Fix in |
|---|---|---|
| `Invalid generic resource (gres) specification`, `invalid partition specified`, `CPU count per node can not be satisfied`, `Memory specification can not be satisfied`, `Requested node configuration is not available`, `Invalid feature specification`, `This does not look like a batch script`, `sinteractive: command not found`, `swarm: command not found` | refused: a Biowulf habit, or bigger than any node in the partition | [Refused at submission](#refused-at-submission) |
| `Invalid --time specification` | a malformed `--time` | JOBS.md (Flags and defaults) |
| `QOSMaxCpuPerUserLimit`, `QOSMaxGRESPerUser`, `PartitionTimeLimit`, `AccountNotAllowed`, `ReqNodeNotAvail`, `DependencyNeverSatisfied` | why a job waits, or (the last) was cancelled | [Job pending too long](#job-pending-too-long) |
| `oom-kill`, `oom_kill event`, `OUT_OF_MEMORY`; `DUE TO TIME LIMIT`; `DUE TO NODE FAILURE` | memory; walltime; node failure | [Job killed or failed](#job-killed-or-failed) |
| `Killed` from a command on the login node | the 10 CPU-minute kill | [Killed on the login node](#killed-on-the-login-node) |
| `No space left on device`, `Disk quota exceeded`; `Connection refused` from `quota` | a quota, or the scratch share full; `quota` can't read FRCE's quotas (harmless) | STORAGE.md (Checking usage and quotas) |
| `ERROR: Invalid command 'spider'`; `Unable to locate a modulefile for`; `module: command not found` | an Lmod habit; wrong name, case, or version; no module init in a non-interactive shell | MODULES.md (Environment Modules, not Lmod; Finding software; Modules in batch jobs and scripts) |
| `Importing the numpy C-extensions failed`; `unrecognized arguments: --cluster`; `option is not allowed in the 'slurm_extra' parameter` | snakemake and python modules mixed; Snakemake 8+ has no `--cluster`; a flag the slurm executor sets itself | WORKFLOWS.md (Snakemake) |
| `Process requirement exceeds available CPUs`; `Script compilation error` | a local-executor task bigger than the allocation; a syntax error or the wrong parser (`NXF_SYNTAX_PARSER`) | WORKFLOWS.md (Nextflow) |
| `CondaError: Run 'conda init' before 'conda activate'`; older conda: `Your shell has not been properly configured to use 'conda activate'` | activation in a script | PYTHON-R.md (Virtual environments and conda) |
| `init_fs_encoding`, `No module named 'encodings'` | a python module's `PYTHONHOME` under another Python | PYTHON-R.md (Python on FRCE) |
| `unable to install packages` (R) | the R module's read-only library first in `R_LIBS` | PYTHON-R.md (R packages and libraries) |
| `TLS handshake timeout`, `Failed to pull singularity image`, `self signed certificate in certificate chain` | the registry unreachable, a passing fault, or TLS inspection | [Software and environment problems](#software-and-environment-problems); TRANSFER.md (Downloads on the cluster) |
| `'nodev' mount option set on /tmp` | an expected Apptainer warning, not the failure | CONTAINERS.md (Apptainer on FRCE) |
| a `/scratch`, `/mnt`, or `/SeqIdx` path missing in a container | not bound by default | CONTAINERS.md (Running containers) |
| `No DISPLAY variable set, cannot setup x11 forwarding` | `srun --x11` from a login without X forwarding | INTERACTIVE.md (X11 applications) |
| `No CUDA GPUs are available` | no GPU in the job, or the transfer node | JOBS.md (GPUs) |
| `CUDA driver version is insufficient`, `no kernel image is available`, `Unsupported gpu architecture` | a CUDA build that doesn't fit the driver or the GPU, as from an unpinned `module load cuda` or a pip PyTorch wheel built without the card's architecture | DEVELOPMENT.md (CUDA and cuDNN); for PyTorch, DEEP-LEARNING.md (Installing frameworks) |
| `Illegal instruction`; ``version `GLIBCXX_3.4.NN' not found``; `Compatibility with CMake < 3.5 has been removed` | CPU target; a module GCC's runtime missing; CMake 4 | DEVELOPMENT.md (CPU targets; Compilers; Build systems and install prefixes) |
| `/lscratch/` in a `No such file or directory` | a Biowulf temp path | JOBS.md (Temporary files) |
| `No such file or directory` under `/mnt/` in jobs only | a share missing on compute nodes | [Software and environment problems](#software-and-environment-problems) |
| `Could not resolve host`; `Permission denied` under `/mnt/` | off the NIH network; not in the share's group | [Access and connection problems](#access-and-connection-problems) |

## Asking for help

First search the exact text of a generic (not FRCE-specific) error, and check this file and the topic file it points to. Otherwise gather the facts with the triage commands and draft the request; the user sends it, through the channel ACCESS.md (Support and requests) gives for the problem.

```text
Brief Description: FRCE: <app or "batch job">: <symptom in a few words>

What happened: <expected vs actual, one or two sentences>
Where: login node batch | transfer node batch2 | job <JOBID> on <cnNNN> | OnDemand app <name> | NoMachine
Job IDs: failed <JOBID>; a similar job that worked: <JOBID>
Request: partition <P>, --cpus-per-task <C>, --mem <M>, --time <T>, --gres <G or none>
Working directory: <path>
Modules: <output of module list>
Command or script: <exact command, or the script's full path>
Error: <exact text, pasted>; full log: <path to slurm-JOBID.out>
Already tried: <each change and its result>
```

- Paste text, not screenshots. Leave out passwords, tokens, keys, and sensitive or controlled-access data (ground rule 4).
- Port-from-Biowulf questions: the administrators offer help adapting scripts and storage locations (FROM-BIOWULF.md (What carries over)).
- Problems inside a CCBR pipeline go to its GitHub issues, not the administrators (WORKFLOWS.md (CCBR pipelines on FRCE)).

## Stale advice on the official pages

- [Miscellaneous Policies and Guidelines](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/MiscellaneousPoliciesandGuidelines) promises a "cryptic error message" for the login-node kill without giving it → with FRCE's limits it is `Killed` ([Killed on the login node](#killed-on-the-login-node)).
- The [FAQ](https://ncifrederick.cancer.gov/staff/FRCE/FrequentlyAskedQuestions) lists "the questions that the EIT admin staff get asked the most" as links only; no FRCE page explains pending reasons, job states, exit codes, or error messages → this file, and Slurm's references below.

## Going further

- FRCE: [Status and Metrics](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/StatusandMetrics), [Contact FRCE Administrators](https://ncifrederick.cancer.gov/staff/FRCE/Support/ContactUs), [Miscellaneous Policies and Guidelines](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/MiscellaneousPoliciesandGuidelines).
- Slurm: [pending reasons](https://slurm.schedmd.com/job_reason_codes.html), [job states](https://slurm.schedmd.com/job_state_codes.html), [exit codes](https://slurm.schedmd.com/job_exit_code.html#displayed) (the `code:signal` form).
- FRCE failures reported in the open, with full logs: [CHARLIE#99](https://github.com/CCBR/CHARLIE/issues/99) (Biowulf-to-FRCE submission errors), [XAVIER#31](https://github.com/CCBR/XAVIER/issues/31) (module conflicts), [XAVIER#34](https://github.com/CCBR/XAVIER/issues/34) (image pulls on compute nodes).
- Biowulf's FAQ on writing a useful help request applies here too, with FRCE's channels: [FAQ.html#ask-question](https://hpc.nih.gov/docs/FAQ.html#ask-question).
- Live: `squeue --me`, `scontrol show job JOBID`, `sacct -j JOBID`, `seff JOBID`, `sinfo -s`, `freen`, `sacctmgr show qos format=Name,MaxTRESPU%80`, `scontrol show config | grep -E 'EnforcePartLimits|SchedulerParameters'`.
