When something on Biowulf breaks: a read-only triage, then sections by symptom (pending, killed or failed, stopped working, interactive sessions, software, storage, graphics, connections, benign messages), an index of exact error strings, and a template for writing to NIH HPC staff. The diagnosis commands here are yours to run in the session (off the cluster, hand them to the user); resubmitting, cancelling, `newwall`, account unlocks, and staff emails are the user's, and destructive fixes (deleting caches, resetting dotfiles) need their go-ahead. Where a topic file owns a fix, this file points to it: state and reason meanings in JOBS.md, monitoring tools in UTILITIES.md, swarm reruns in SWARM.md.

Table of contents

- [Triage](#triage)
- [Job pending too long](#job-pending-too-long)
- [Job killed or failed](#job-killed-or-failed)
- [Keeping lscratch from a failed job](#keeping-lscratch-from-a-failed-job)
- [It used to work](#it-used-to-work)
- [Interactive session problems](#interactive-session-problems)
- [Software not found or broken](#software-not-found-or-broken)
- [Storage and quota](#storage-and-quota)
- [Graphics](#graphics)
- [Can't connect](#cant-connect)
- [Benign messages](#benign-messages)
- [Error-string index](#error-string-index)
- [Asking NIH HPC staff](#asking-nih-hpc-staff)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Triage

Run each once (ground rules in SKILL.md); all are read-only.

1. **Where.** SKILL.md's where-am-I check. For trouble in your own session, `whereami -f pretty` shows its CPUs, memory, GPUs, lscratch, and remaining time.
2. **State.** `sjobs`: a pending job's reason is in `Nodelist` (newer layouts: `Reason`).
3. **History.** `jobhist JOBID`: State, Runtime vs Walltime, MemUsed vs MemReq (a row per swarm subjob), `Submission Path`, `Submission Command`.
4. **Details.** `dashboard_cli jobs --jobid JOBID --allfields --vertical`: `state`, `exit_code`, `mem_max`, `std_out`, `std_err`, `work_dir`; add `--archive` for jobs that ended over 10 days ago. `sacct --state f` lists today's other failures.
5. **Logs.** Tail the files `std_out` and `std_err` name: by default `slurm-JOBID.out` in the Submission Path; swarms write `swarm_JOBID_N.e`, or `swarm_JOBID_N_p.e` under `-p` after a timeout or cancel. Slurm's memory and time-limit messages land at the end; look them up in the [error-string index](#error-string-index).
6. **Space.** `checkquota`: a full `/home` or `/data` breaks jobs in ways that never mention quota.
7. **Reproduce** the failing step on a small input in the session before handing the user a fix or a resubmission. A tool that is `command not found` in the session: the user runs it at their login prompt and pastes the output (UTILITIES.md).

## Job pending too long

Reason meanings: JOBS.md. Live limits: `batchlim`; free capacity: `freen`; an estimated start, when Slurm can compute one: the `squeue --me` query in UTILITIES.md. The FAQ's causes, most common first:

| Cause | Shows as | What helps |
|---|---|---|
| The user already holds their per-partition limit of CPUs, jobs, or GPUs | `QOSMaxCpuPerUserLimit`, `QOSJobLimit`, `QOSMaxGRESPerUser` | Nothing is wrong: it starts as their running jobs end. A second partition adds a pool. |
| The CPUs or memory requested aren't free in that partition | `Resources` | Two partitions; smaller, accurate requests |
| Low priority, which falls as the user's recent CPU-hours grow | `Priority` | `quick` (under 4 h) and `interactive` rank higher; accurate requests |
| Free CPUs stranded by jobs holding a node's memory or much of its lscratch, or held idle for a higher-priority job | shows `Resources` or `Priority` | Accurate requests; patience |

Fixes, each a change the user makes (the first three are the FAQ's; hand them the exact lines):

- **Two partitions:** `--partition=quick,norm` (NCI CCR: `ccr,norm`), never more ("larger lists of partitions have caused scheduling problems"); the job must fit both (JOBS.md).
- **Accurate requests:** "The more resources a job requests, the longer it will take for the batch system to carve out a slot." A job measured at 4 GB, 4 CPUs, and 5 h asks for about 5 GB and 6 h; under 4 h goes to `quick`. Sizing from past runs: UTILITIES.md.
- **Bundle** swarms of many short lines (the FAQ's case: 10,000 lines of 5 minutes) with `-b`, and **pack** single-threaded swarms with `-p 2`, since each subjob gets 2 CPUs by default (SWARM.md).
- **In place:** the user can lower a pending job's walltime with `newwall` or move it with `scontrol update` instead of resubmitting (JOBS.md, Changing or cancelling a job).

Never starts, however long it waits:

- `DependencyNeverSatisfied`: an `afterok` upstream failed; the user cancels it and resubmits with `afterany` (SWARM.md).
- A GPU job over the CPUs-per-GPU cap is accepted and never runs (JOBS.md, GPUs, which also has the `gpuh200` minimums); nor do Nextflow tasks asking for unlimited time and maximum memory, a sign of a stale NIH config (WORKFLOWS.md).
- `ReqNodeNotAvail`: a node it needs is down, drained, or reserved. Drop `--constraint`s it doesn't need (HARDWARE.md) and check [system status](https://hpc.nih.gov/systems/status/) for maintenance. `Dependency` and `Licenses` wait by design (`sjobs` shows the dependency, `licenses` the pool).

## Job killed or failed

| You see | Likely cause | Next |
|---|---|---|
| `FAILED` (or Slurm's `OUT_OF_MEMORY`) with MemUsed at MemReq; `slurmstepd: Exceeded job memory limit at some point.` at the end of the log | memory | [Out of memory](#out-of-memory) |
| `TIMEOUT` (`TO`); `CANCELLED AT … DUE TO TIME LIMIT` in the log | walltime | Next run: measured runtime plus a buffer, and if CPUs sat idle, the healthy-job recipe (both UTILITIES.md). Running: the user's `newwall`, up to the partition maximum. Beyond 10 days: `unlimited` (JOBS.md), or checkpoints and chained jobs (DEEP-LEARNING.md). |
| `FAILED`, memory well under the request | the program's own error | the end of `std_err`; reproduce in the session |
| `COMPLETED`, outputs missing or wrong | an earlier step failed and a later command succeeded (a failed `module load`, a crash, a swarm line joined with `;`) | read the whole log; `set -e` or a `fail` check (JOBS.md); swarms: `&&` and `--joblog` (SWARM.md) |
| `CANCELLED` (`CA`) | the user's `scancel`, or an `afterok` dependent whose upstream failed (JOBS.md, Dependencies) | ask the user before proposing a resubmission |
| `NF` (node failure) | the node, not the job | the user resubmits unchanged; if it recurs, staff get the job IDs and node names |
| `Illegal instruction` on some node types; `CUDA driver version is insufficient` | built for a newer CPU than the node's, or a newer CUDA than its driver supports | DEVELOPMENT.md |

### Out of memory

The FAQ's most likely reason for a killed job. A command that exceeds the job's memory is killed and the rest of the script runs on (user guide), so the job can even end `COMPLETED`.

1. **Confirm.** `jobhist JOBID`: MemUsed at or near MemReq (units: UTILITIES.md). `dashboard_cli jobs --jobid JOBID --fields jobid,state,exit_code,mem,mem_max,mem_util`. The `Exceeded job memory limit` line can be missing when the job died early.
2. **Rule out a slip.** `--mem=32` is 32 MB (JOBS.md); swarm `-g` is per line and `-p` multiplies it (SWARM.md); a JVM's `-Xmx` must sit well below `--mem` (DEVELOPMENT.md).
3. **Size the retry.** A killed job's MemUsed is a floor, not its need. Measure the peak on a representative input in the session (`/usr/bin/time -v`, as in SWARM.md's workflow), then give the user the resubmission at that peak plus a buffer: `--mem` for sbatch, `-g` for swarm. When only a few swarm subjobs failed, rerun just those (SWARM.md).
4. **Bigger than a node:** `largemem` (JOBS.md), or less memory per task: fewer workers or threads, since each worker holds its own (PYTHON.md, R.md).
5. **No message, just a hang until `TIMEOUT`:** a `multiprocessing.Pool` that lost a worker (PYTHON.md), or container processes stuck in D state (CONTAINERS.md).

## Keeping lscratch from a failed job

`/lscratch/$SLURM_JOB_ID` exists only if the job requested it and is deleted when the job exits. "There is no built-in mechanism in sbatch or slurm" to keep it: the script must test for failure (by its own definition, such as an empty output) and copy lscratch to `/data` before exiting. The FAQ's pattern, corrected (its tarball went to `/scratch/$USER`, which compute nodes can't reach, and its thread count used an undefined `$cpus`); `mytool` is a placeholder:

```bash
#!/bin/bash
#SBATCH --cpus-per-task=8
#SBATCH --gres=lscratch:50
#SBATCH --mail-type=FAIL
# FAIL mails the user when the job fails; add --mem and --time (JOBS.md)
set -e
rescue() {                               # save lscratch to /data, then fail the job
    echo "FAILED: $*; lscratch saved to /data/$USER/lscratch_$SLURM_JOB_ID.tar.gz" >&2
    tar -czf /data/$USER/lscratch_$SLURM_JOB_ID.tar.gz -C /lscratch/$SLURM_JOB_ID . ; exit 1
}
cd /lscratch/$SLURM_JOB_ID
module load samtools; cp /data/$USER/proj/sample.cram .
samtools index sample.cram || rescue "samtools index"
[ -s sample.cram.bai ] || rescue "sample.cram.bai missing or empty"   # the FAQ's test
mytool --threads "$SLURM_CPUS_PER_TASK" sample.cram > result.txt || rescue "mytool"
cp result.txt /data/$USER/proj/results/
```

- The message lands in `slurm-JOBID.out`. The tarball counts against `/data`: check `checkquota`, and tar only the subdirectories worth inspecting when lscratch is large.
- A step killed for memory lets the script reach its check. A walltime kill or `scancel` ends the whole job, and the docs offer no rescue for that: checkpoint to `/data` as the job runs (DEEP-LEARNING.md, whose template also copies outputs with `trap … EXIT`). In swarms, `--epilog` copies each subjob's lscratch out when its lines finish, not after a walltime kill (SWARM.md).

## It used to work

Check the [announcements](https://hpc.nih.gov/nih/about/announcements.php) and [system status](https://hpc.nih.gov/systems/status/) first; sudden breakage is usually a change on the cluster.

- **Versions moved.** An unpinned module default changed (MODULES.md). An R minor-version bump means a new, empty package library, and updates can break a private `rlang` (R.md). Python imports go wrong through `~/.local` packages, or `PYTHONNOUSERSITE=1` on python/3.11+ (PYTHON.md).
- **Retired pieces.** Node types `x2650`, `x2695`, `x2630`, `k80` (HARDWARE.md); `/gs6` in a bind list or copied config (CONTAINERS.md, WORKFLOWS.md).
- **Tools changed.** Snakemake 8 dropped `--cluster`, and Nextflow's strict syntax breaks older pipelines (WORKFLOWS.md); `jobload` was broken as of Sept 2026 (try it once: UTILITIES.md); Anaconda's channels return HTTP 403 (CONDA.md).
- **The system or the account.** Slurm commands exiting with status `123` mean maintenance (JOBS.md); logins refused after a break mean a 60-day lock or a lapsed annual renewal (ACCESS.md).

## Interactive session problems

| Symptom | Cause and fix |
|---|---|
| `sinteractive` sits at `salloc: job N queued and waiting for resources` | The [pending](#job-pending-too-long) causes; the user can ask for less, or wait. |
| A new `sinteractive` or OnDemand app fails to submit | Two interactive jobs already run (every OnDemand app but the Graphical Session counts); the user ends one (JOBS.md). |
| The session, and you, are gone | Its login-node shell ended (VPN drop without tmux, monthly reboot; ACCESS.md) or its walltime ran out. The user restarts per SKILL.md and can extend a live session with `newwall`, to 36 h (JOBS.md). lscratch is gone. |
| A command dies with `Killed` (bash's report of SIGKILL; generic) | Likely the session's memory: compare `mem_max` with `mem` in `dashboard_cli jobs --jobid $SLURM_JOB_ID --allfields --vertical`; the user starts a bigger session. |
| `$SLURM_CPUS_PER_TASK`, `/lscratch/$SLURM_JOB_ID`, a GPU, or `$PORT1` missing | Started without `--cpus-per-task`, `--gres=lscratch:N`, a GPU, or `--tunnel` (JOBS.md, TUNNELING.md); in a Remote-SSH shell, ACCESS.md. |

## Software not found or broken

- `command not found`, a failing `module load`, `module: command not found`, or the wrong version running: MODULES.md (When a module or command isn't found). Rule out Helix, which has no scientific applications, and the login node, where `whereami` warns "Many modules are not available here" (SKILL.md's where-am-I check).
- Anything else: the troubleshooting or pitfalls table of the topic's file (router in SKILL.md), found fastest through the [error-string index](#error-string-index). Software that isn't installed at all: MODULES.md (Choosing how to install software).

## Storage and quota

A full `/home` (16 GB, "cannot be increased") means "a lot of things can go wrong", usually without a quota message; Globus's `500 Sharing state dir has invalid permissions` is one documented case. Confirm with `checkquota`, then follow STORAGE.md (A full /home: `dust`, the culprits, the fixes); every fix moves or deletes the user's files, so get their go-ahead, and repoint the cache that filled it (CONTAINERS.md, DEEP-LEARNING.md, CONDA.md) or it refills.

- `/data` at its quota or file-count limit: clean up with the user, or the user files a storage request (STORAGE.md).
- `No space left on device`: during a container pull or build, `/tmp` (CONTAINERS.md); otherwise check the job's lscratch request, `/tmp` (about 8 GB per node, shared; JOBS.md), and `checkquota`. `Disk quota exceeded`: a quota'd area is full; `checkquota`, then STORAGE.md (a full /home, or a /data increase).
- Deleted or overwritten files: snapshots (STORAGE.md). "Permission denied" in a group directory: STORAGE.md (Shared group directories).

## Graphics

The FAQ's checklist, updated. The user's own computer almost always renders better: X11 from a node outside the visual partition is drawn by CPUs and sent over the network, so 3D apps "will run very slowly if they run at all". Every display step is the user's.

1. **Display route.** NoMachine was retired on 7 Aug 2025 and X11 on macOS is unsupported: use the OnDemand Graphical Session (ACCESS.md). `libGL error: No matching fbConfigs or visuals found`, `Unrecognized OpenGL version`, and `qt.qpa.xcb: could not connect to display` mean no graphical connection ([RStudio.html](https://hpc.nih.gov/apps/RStudio.html)).
2. **Environment.** Retest with stock startup files (ACCESS.md, Shell startup files; the user's go-ahead first), loading only the app's modules in a new session; if that works, re-add customizations one at a time. csh, tcsh, and zsh users do the same with their own files.
3. **Conda.** Deactivate any env and stop `~/.bashrc` from activating one ("conda sometimes writes to your .bashrc file automatically"; CONDA.md, Fix a broken setup). A conda `dbus` breaks TurboVNC logins or leaves a black screen.
4. **Memory.** `libGL error: failed to load driver: swrast` can also mean the app ran out of memory. The Graphical Session is fixed at 4 CPUs and 8 GB; for more, the user starts an `sinteractive` with a larger `--mem` from its Terminal and runs the app there (X forwarding is automatic).
5. **Not the `gpu` partition.** Its GPUs are configured for computation, and "the drivers can actually get in the way". GPU rendering is the `visual` partition (`svis`, TurboVNC, `vglrun`; ACCESS.md).

Complex graphics such as MATLAB's run "much better" on the user's own computer. Code that needs no screen should go headless: matplotlib's `agg` backend (PYTHON.md), Java's `-Djava.awt.headless=true` (DEVELOPMENT.md).

## Can't connect

Every fix is the user's, in ACCESS.md (When the user can't connect). Symptoms it covers: `ssh` hangs or times out (off the NIH network or VPN), a refused password (Windows username prefix, expired password), a locked account, OnDemand `Bad Request` or `Error -- user has disabled shell`, VS Code "Connecting with SSH timed out", and a Mac that keeps retrying an old helixdrive mount.

## Benign messages

- At `sinteractive` or `svis` start: `srun: error: x11: no local DISPLAY defined, skipping`, `error: unable to open file /tmp/slurm-spank-x11.JOBID.0`, `slurmstepd: error: x11: unable to read DISPLAY value`. NIH's transcripts show them and carry on, though no page calls them harmless; ignore them unless the user needs X11 ([Graphics](#graphics)).
- `QStandardPaths: XDG_RUNTIME_DIR not set`: "a harmless warning" (RStudio page). Module `[+] Loading …` banners (MODULES.md), the container warnings CONTAINERS.md lists, and OpenMPI 4.0.x's "confusing (but harmless)" OpenIB/UCX warnings (DEVELOPMENT.md).
- Not benign, though the swarm page calls it a warning: `slurmstepd: Exceeded job memory limit at some point.` means out of memory.

## Error-string index

Grep the log for these; substrings are enough.

| String | Means | Fix in |
|---|---|---|
| `QOSMaxCpuPerUserLimit` (FAQ: `QOSMaxCpusPerUserLimit`), `QOSJobLimit`, `QOSMaxGRESPerUser`, `Resources`, `Priority`, `ReqNodeNotAvail`, `DependencyNeverSatisfied`, `queued and waiting for resources` | why a job or session waits | [Job pending too long](#job-pending-too-long) |
| `slurmstepd: Exceeded job memory limit at some point.` | out of memory | [Out of memory](#out-of-memory) |
| `CANCELLED AT` … `DUE TO TIME LIMIT` | walltime reached | [Job killed or failed](#job-killed-or-failed) |
| `ERROR: Total time for bundled commands is greater than partition walltime limit.`, `ERROR: -g 400 requires --partition largemem` | swarm refused the submission | SWARM.md (Failures and reruns) |
| `sbatch failed`; exit status `123` from Slurm commands | submission rejected; maintenance | JOBS.md (Dependencies; Exit codes and job states) |
| `## You are on a login node` | you are on the login node: stop | SKILL.md (First: where are you running?) |
| `command not found`, `module: command not found` | module not loaded; `module` function lost | MODULES.md (When a module or command isn't found) |
| `Illegal instruction`, ``version `GLIBCXX_3.4.NN' not found``, `CUDA driver version is insufficient` | CPU target; GCC runtime; GPU driver | DEVELOPMENT.md |
| `docker: command not found`, `singularity: command not found`, `FATAL: container creation failed`, `No space left on device` (pull or build) | container setup | CONTAINERS.md (Pull and run; Troubleshooting) |
| `Could not connect to any X display` | matplotlib without a display | PYTHON.md (Headless plotting) |
| `libGL error: failed to load driver: swrast` (or out of memory), `libGL error: No matching fbConfigs or visuals found`, `Unrecognized OpenGL version`, `qt.qpa.xcb: could not connect to display` | no graphical connection | [Graphics](#graphics) |
| `Unable to contact settings server` | conda env active when `svis` ran | ACCESS.md (Graphical Session, X11, and svis) |
| `Jupyter command jupyter-lab not found`, `Permission denied: '/run/user/xxxx'` | Jupyter environment | JUPYTER.md (Pitfalls) |
| `Transfer finalized, status: 403` | Anaconda channels blocked | CONDA.md (Fix a broken setup) |
| `in coercion to 'logical(1)'`, `No internet connection` (AnnotationHub) | R ≥ 4.3 change; hub needs the proxy | R.md |
| `mem_mb is required to be in resources`, `Cannot invoke method optional() on null object`, `Process requirement exceeds available CPUs`, `Found unexpected parameters` | Snakemake and Nextflow setup | WORKFLOWS.md (Errors and fixes) |
| `Bad Request - Your browser sent a request`, `Error -- user has disabled shell`, `Connecting with SSH timed out` | OnDemand cookies; locked account; VS Code timeout | ACCESS.md (When the user can't connect) |
| `Address already in use` (local `ssh -L`) | local port taken | TUNNELING.md (Troubleshooting) |
| `500 Sharing state dir has invalid permissions`, `Sharing not enabled for user`, `Transfer terminated because it hit the deadline` | `/home` at quota; share permissions; unfixed Globus fault | GLOBUS.md (Troubleshooting) |
| `x11: no local DISPLAY defined`, `x11: unable to read DISPLAY value`, `XDG_RUNTIME_DIR not set` | benign | [Benign messages](#benign-messages) |

## Asking NIH HPC staff

First, per the FAQ, a web search on the exact text of a generic (not Biowulf-specific) error "will often produce the answer". Otherwise gather the facts with read-only commands and draft the email; the user sends it from their NIH address. The FAQ's minimum information:

```text
To: staff@hpc.nih.gov
Subject: <app and version, or "batch job problem">: <symptom in a few words>

What happened: <expected vs actual, one or two sentences>
Where: batch job | sinteractive session | OnDemand app | Helix
Job IDs: failed <JOBID or JOBID_N>; a similar job that succeeded: <JOBID>
Working directory: <pwd>
Modules: <module list>; with <other version>: <works | same error>
Command or script: <exact command, or the script's full path>
Error: <exact text, pasted>; full logs: <full paths to slurm-JOBID.out or swarm .e files>
Already tried: <each change and its result>
```

- For a version-dependent failure, include the FAQ's reproduction: the same command in a session under each module version, stderr saved per version (`XXX /A/B/C/YYY 2>XXX_1.2.0.error`), with both paths. Connection problems: add what ACCESS.md lists (OS, client and version, `ssh -v` output).
- Paste text, not screenshots (staff can't copy from an image) unless the problem is a graphics program. Leave out passwords, tokens, keys, PHI, and controlled-access data (ground rules in SKILL.md).

## Stale advice on the official pages

- FAQ#lscratch_recover tars to `/scratch/$USER`, though "access to /scratch ... is disabled from compute nodes (since September 2021)" (singularity page), and passes an undefined `$cpus` → the corrected script above.
- FAQ#graphics_problem recommends NoMachine (retired; ACCESS.md), and its "visual partition" link points back at the FAQ → https://hpc.nih.gov/docs/svis.html.
- FAQ#pending and the user guide's state table write `QOSMaxCpusPerUserLimit`; Slurm prints `QOSMaxCpuPerUserLimit` (as the user guide's reason section does) → grep for `QOSMaxCpu`. The FAQ's "entire node of 32 CPUs" example predates current nodes (HARDWARE.md).
- FAQ#mount-popup's "helixdrive" is now hpcdrive.nih.gov (ACCESS.md), and its System Preferences → Users and Groups menu path is from older macOS.

## Going further

- https://hpc.nih.gov/docs/FAQ.html — [#pending](https://hpc.nih.gov/docs/FAQ.html#pending), [#killed](https://hpc.nih.gov/docs/FAQ.html#killed), [#lscratch_recover](https://hpc.nih.gov/docs/FAQ.html#lscratch_recover), [#graphics_problem](https://hpc.nih.gov/docs/FAQ.html#graphics_problem), [#home_directory](https://hpc.nih.gov/docs/FAQ.html#home_directory), [#ask-question](https://hpc.nih.gov/docs/FAQ.html#ask-question); [policies#response](https://hpc.nih.gov/policies/index.html#response) — when staff answer.
- https://hpc.nih.gov/docs/userguide.html#states — job states and `sacct`; [#exitcodes](https://hpc.nih.gov/docs/userguide.html#exitcodes) — why a failed step can still end `COMPLETED`.
- https://slurm.schedmd.com/job_reason_codes.html — every pending reason, spelled as Slurm prints it.
- https://hpc.nih.gov/apps/swarm.html#output — swarm `.e` files and the out-of-memory message; https://hpc.nih.gov/ondemand/graphical.html and https://hpc.nih.gov/docs/svis.html — the two graphics routes.
- Live: `sjobs`, `jobhist JOBID`, `dashboard_cli jobs -h`, `batchlim`, `freen`, `checkquota`, `whereami -f pretty`.
