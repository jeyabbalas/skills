NIH's in-house commands for seeing what is running, how efficiently it ran, what is free, and what the limits are, plus recipes for checking a running job and sizing the next one. Inside the session you may run every read-only tool here; anything that changes a job, permissions, or the user's setup is the user's to run. Writing and changing job requests: JOBS.md. Step-by-step diagnosis of pending, killed, or failed jobs: TROUBLESHOOTING.md. The node and GPU types behind `freen`'s rows: HARDWARE.md.

Table of contents

- [Which utility, and who runs it](#which-utility-and-who-runs-it)
- [whereami](#whereami)
- [freen, nodetype, batchlim](#freen-nodetype-batchlim)
- [sjobs and squeue](#sjobs-and-squeue)
- [jobload](#jobload)
- [jobhist](#jobhist)
- [jobdata](#jobdata)
- [dashboard_cli and the web dashboard](#dashboard_cli-and-the-web-dashboard)
- [GPUs, licenses, pasted text](#gpus-licenses-pasted-text)
- [Recipe: is my running job healthy?](#recipe-is-my-running-job-healthy)
- [Recipe: size the next run from the last one](#recipe-size-the-next-run-from-the-last-one)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Which utility, and who runs it

| Utility | Answers | You may run it (in the session)? | Example |
|---|---|---|---|
| `whereami` | Where am I; this session's CPUs, memory, GPUs, lscratch, time left | yes | `whereami -f pretty` |
| `freen` | Free nodes, CPUs, GPUs; per-node cores, memory, disk, features | yes | `freen` |
| `nodetype` | A node's features; does it have feature X | yes | `nodetype cn2039` |
| `batchlim` | Per-user limits per partition; default and maximum walltime | yes | `batchlim` |
| `sjobs` | The user's jobs, with pending reasons | yes | `sjobs` |
| `squeue`, `sacct` | Slurm's view: estimated start, time used, today's failures | yes, one-off calls | `sacct -S midnight -E now --state F` |
| `jobload` | Live threads, load, memory of running jobs | yes, but broken since Aug 2026 | `jobload -j JOBID` |
| `jobhist` | A finished job's CPUs, memory, runtime, submit command | yes | `jobhist JOBID` |
| `jobdata` | Everything about one job: script, log paths, time series | yes (slow) | `jobdata --show-scripts JOBID` |
| `dashboard_cli` | Utilization and history across jobs; filters; JSON | yes | `dashboard_cli jobs --since -5d` |
| User Dashboard (web) | The same job data in a browser; disk usage; unlock and storage forms | **user** (browser) | https://hpc.nih.gov/dashboard |
| `licenses` | License availability | yes | `licenses` |
| `nvidia-smi`, `nvtop` | GPU use on this node | yes, own node only | `nvidia-smi` |
| `highlightUnicode`, `highlightTabs` | Hidden Unicode or tabs in a file | yes | `highlightTabs samples.tsv` |
| `wazzup` | "Show your running processes" (nothing more documented) | yes | `wazzup` |
| `checkquota`, `dust`, `getfacl_path`, `setfacl_path -d`, `obj2 ls`/`df`/`put`/`get` | Quotas, what fills them, who can reach a path, ACL dry run, object-store listing and copies | yes (copies: when the user asked for them) | STORAGE.md |
| `setfacl_path` without `-d`, `obj2 rm` | Change ACLs; permanently delete object data | only with the user's go-ahead | STORAGE.md |
| `sbatch`, `sinteractive`, `spersist`, `salloc`, `swarm`, `newwall`, `scontrol update\|hold\|release`, `scancel` | Start, submit, change, or cancel jobs | **user** (the `swarm --devel` dry run is yours: SWARM.md) | JOBS.md |
| `mamba_install` | Installs conda under `/data`; edits dotfiles | only with the user's go-ahead | CONDA.md |
| `reconnect_tunnels` | The local `ssh -L` line for open tunnels | **user** | TUNNELING.md |
| `clearspace`, `split_fasta`, `histogram.pl` | Rename a file with a timestamp suffix; split a FASTA; histogram prep | only when asked (options undocumented) | — |

- **Where they run.** Nearly every documented example of NIH's own tools runs at the login prompt; only `whereami` and `mamba_install` are shown on a compute node. If a tool is "command not found" in the session, ask the user to run it at their login prompt and paste the output. Never go to the login node yourself.
- **`bwulf`.** Every in-house tool is also a `bwulf` subcommand (`bwulf -h` lists them), mostly with hyphens for underscores (`bwulf getfacl-path`); `bwulf dsh` is `dashboard_cli`, `bwulf procs` is `wazzup`.
- **Load.** `sjobs` and `dashboard_cli` read the dashboard database, not the scheduler; prefer them to `squeue`. `jobdata` and `dashboard_cli --archive` are slow: answer bulk questions with one `dashboard_cli ... --json` query, not a loop of `jobdata` calls. `dashboard_cli` shows only the user's own jobs (`-u` is staff and root only).

## whereami

```bash
whereami            # login node: "## You are on a login node" and a warning
whereami -f pretty  # sinteractive: box with JobId, CPUs, Memory, GPUs (e.g. "1 a100"), lscratch, Remaining time
whereami -f short   # sinteractive: prints "sinteractive"
```

- Check `Remaining time` before a long step. If the session will end first, write a batch script for the user instead (JOBS.md).
- Output in batch jobs, OnDemand jobs, `spersist`, on Helix, and of `-f short` on the login node is undocumented; fall back on `hostname -s` and `$SLURM_JOB_ID`.

## freen, nodetype, batchlim

```bash
freen                                    # one line per node type in each partition
freen | grep -E 'Partition|----|gpu'     # rows with GPU nodes, in any partition
```

- A snapshot of what is free now, not a start-time forecast (for that, `squeue` below). `FreeNds` (`19 / 397`) counts completely free nodes; `FreeCPUs` also counts free CPUs scattered over partly used nodes (Slurm allocates by core = 2 CPUs); `FreeGPUs` counts free GPUs, where a partition has them.
- `Cores` is physical cores, a guide to the most threads an app should run; `CPUs` is the hyperthreaded count; `GPUs` is per node.
- `Mem` is allocatable memory per node; `Disk` is local disk, the most `--gres=lscratch:N` can get there.
- `Features` are the `--constraint` values (HARDWARE.md). On a GPU row, `CPUs` ÷ `GPUs` is the per-GPU CPU cap (the rule: JOBS.md).

```bash
nodetype "$(hostname -s)"                              # this session's node: its features
( nodetype cn3118 ibfdr x2680 && echo yes ) || echo no # extra args are features: exit 0 only if all present
```

`batchlim` prints `Max jobs per user:` and `Max array size:`, then per partition: `Walltime Default` (applied when no `--time` is given), `Walltime Maximum` (`DD-HH:MM:SS`), `Per User Limits` (`CPUs` and `Other`, e.g. `60T mem`, `4 GPUs,2 jobs`; past these, further jobs wait in the queue), and `MaxPerJob` (e.g. `1 nodes`). It explains the pending reasons `QOSMaxCpuPerUserLimit` (the FAQ writes `QOSMaxCpusPerUserLimit`), `QOSJobLimit`, and `QOSMaxGRESPerUser` (a per-user limit reached), how far `newwall` can extend a job (the partition maximum), and the sinteractive limits (the `interactive` row).

The limits change: quote a live run, never the docs' example. Also at https://hpc.nih.gov/systems/status/#batch_limits (NIH-only).

## sjobs and squeue

- `sjobs` (or `sjobs -u USER`) columns: User, JobId, JobName, Part, St, Runtime (0 while pending), requested Nodes/CPUs/Mem, Dependency (e.g. `afterany:22391`), Features, and Nodelist, which shows the pending reason, e.g. `(Dependency)`, for pending jobs. Newer layouts add `Reason` and `Walltime` columns and totals (`cpus running = 48 / 64`); read the header rather than assuming positions. Your own session is one of the listed jobs (`$SLURM_JOB_ID`). Reason meanings: JOBS.md; fixes: TROUBLESHOOTING.md.
- Prefer `sjobs`: it "gets its data from the dashboard server, which doesn't place additional strain on the SLURM scheduler". For what only Slurm knows, make single calls (the docs define the first as `alias sq=...`; aliases don't expand in non-interactive shells, so run the command itself):

```bash
squeue --me -o '%18i %10j %10P %20S %20e'   # expected START_TIME/END_TIME ("may not always be calculable")
squeue -O jobid,timelimit,timeused -u $USER # walltime limit vs time used
sacct -S midnight -E now --state F,OOM,TO,NF   # today's failures; with --state, sacct needs both -S and -E
```

## jobload

**Unavailable since the 2 Aug 2026 Slurm upgrade** ([announcement](https://hpc.nih.gov/nih/about/announcements.php?1208)); staff were "working to restore functionality", and no later announcement reports it back (as of Sept 2026). The user guide, multinode, and swarm pages still recommend it. Try it once; if it errors, get the same numbers from `dashboard_cli`, the command line to the web dashboard the announcement points to.

When it works: `jobload -j JOBID` (or `-u USER`, `-n NODE`; `-v`) prints `TIME Elapsed / Wall`, `NODES`, `CPUS Alloc`, `THREADS Active`, `LOAD` (active threads ÷ allocated CPUs; ideally 1-to-1, and 5 threads on 6 CPUs is "all is well"), and `MEMORY Used/Alloc`, one line per node for multinode jobs. Threads "significantly more" than CPUs means an overloaded job, and `CPUS Alloc` "cannot be changed after the job has started".

## jobhist

`jobhist JOBID` reports finished jobs; data is kept at least a month.

- Header: `Submitted`, `Started`/`Ended`, `Submission Path` (where `slurm-JOBID.out` lands by default; older output says `Command Path`), `Submission Command` (the full `sbatch` line), and for swarms `Swarm Path` and `Swarm Command`: the fastest way to recover how a job was submitted.
- Table: `Partition State Nodes CPUs Walltime Runtime MemReq MemUsed Nodelist`, with one row per subjob (`JOBID_N`) for swarms and arrays. `Walltime` is the limit and `Runtime` the actual (older output differs: see stale advice).
- `MemReq` is per node (`4.0GB/node`) or per CPU (`0.8GB/cpu`: multiply by CPUs). Usage under 100 MB per CPU prints as `0.0GB`.
- `FAILED` with `MemUsed` equal to `MemReq` "probably failed due to memory". Rerunning only the failed subjobs: SWARM.md.

## jobdata

```bash
jobdata JOBID                              # running or finished; JOBID_N for one subjob; slow (several sources)
jobdata --show-scripts JOBID               # adds the job script's contents
jobdata --show-time-series --human JOBID   # samples ~30 s apart: timestamp node cpus memory gpus dthr
jobdata --json --pretty JOBID              # for parsing
```

Fields worth reading: `state`, `state_reason`, `sbatch_cmd`, `swarm_cmdline`, `work_dir`, `std_out` and `std_err` (where the logs are), `elapsed`, `time_limit`, `total_cpus`, `total_mem`, `total_gpus`, and `max_cpu_used`, `max_mem_used`, `max_gpu_used`, `max_dth_used` (each with `_node` and `_time` variants). Units are not stated; the docs' example fits seconds (`time_limit 86400`) and MB (`total_mem 73728`). More: `man jobdata`.

## dashboard_cli and the web dashboard

The User Dashboard (https://hpc.nih.gov/dashboard, also https://hpcnihapps.cit.nih.gov/auth/dashboard/; NIH network or VPN) shows each job's resource use (Job Info → click the job ID), disk usage, and the account-unlock and storage-request forms; it's the user's to open. `dashboard_cli` is the command line to the same job data. Run it with no options for help; `dashboard_cli jobs -h` lists everything below.

- **Scope.** By default: pending, running, and recently finished jobs. Finished jobs move to a slower archive after 10 days; add `--archive` (up to 1 year back). Running-job values are cached and can be 1 min old.
- **Select.** `-j/--jobid` (`N`, `N_M` for one subjob, `N_` for a whole array), `--joblist`, `--jobname`, `--partition`, `--state`, `--pending`/`--running`/`--ended`, `-n/--node`; `--overload` (load above 1.5x the CPU allocation) and `--zeroload`, both needing `--running`; `--mem-over` (overloaded memory); `--bad-swarm` (arrays whose subjobs finished too quickly); `--gpu-only`; range pairs such as `--cpu-util-min`/`--cpu-util-max` (value format undocumented).
- **Time.** `--since`/`--until` (submitted), `--start-since`/`--start-until`, `--end-since`/`--end-until`, and `--running-since` with `--running-until` (both required). Dates: `2008-05-17`, `5/17`, `yesterday`, `today`, `lastmonth`, `forever`, epoch seconds, `-24h`, `-2d`, `-100m`.
- **Output.** `--fields a,b`, `--add-fields`, `--allfields`, `--order F --desc`, `--vertical`, `--compact`, `--json`, `--tab`, `--noheader`, `--raw` (dates in epoch seconds, times in seconds, memory in MB), `--null STR`. Parse `--json` or `--tab --noheader`.
- **Fields** beyond the defaults: `jobname exit_code std_out std_err work_dir command nodelist gpus`, `cpu_util mem_util gpu_util`, and `{cpu,mem,gpu,D}_{cur,min,max,avg}`. Going by the docs' example, `cpu_*`/`gpu_*` count busy CPUs/GPUs, `D_*` counts threads in D state (uninterruptible, usually waiting on I/O), and `*_util` ≈ average ÷ allocated (`cpu_avg 9.00` of `cpus 12` gives `cpu_util 75.0%`). `eval` is undocumented.
- **Exit codes.** `0` no error, `1` job(s) not active, `2` database error, `3` incorrect input, `4` bad output.

```bash
dashboard_cli jobs --jobid JOBID --allfields --vertical                                   # one job, everything
dashboard_cli jobs --since -7d --ended --fields jobid,partition,state,exit_code | grep -v COMPLETED   # this week's failures
```

To act after a job ends, prefer a dependent job the user submits (`sbatch --dependency=afterok:JOBID post.sh`; JOBS.md): it needs neither your session nor you. To wait yourself (e.g. before post-processing in the session), use the docs' loop, in the background so it outlasts your tool calls' time limits. It reads the dashboard database, never `squeue`, and the data is cached for about a minute, so don't shorten the sleep; for a swarm or array, use `--jobid JOBID_`:

```bash
while dashboard_cli jobs --is-active --jobid 32535313
do
    echo "job is pending or running"
    sleep 30
done
echo job has finished
```

Exit codes 2–4 also end the loop, and so does a job that failed: confirm with `dashboard_cli jobs --jobid ID --fields jobid,state,exit_code` before using its output.

## GPUs, licenses, pasted text

- `nvidia-smi` and `nvtop` (in the apps list; `module -r spider '^nvtop$'`) show GPU use on the node you are on. The docs tell users to "login to the compute node where your job is running"; you stay on your own node, so for the user's other GPU jobs read `gpus,gpu_cur,gpu_avg,gpu_util` from `dashboard_cli` or the `gpus` column of `jobdata --show-time-series`. Deep-learning checks: DEEP-LEARNING.md.
- `licenses` shows current license availability (also at https://hpc.nih.gov/systems/status/license_status.html, NIH-only). Requesting licenses in a job: JOBS.md.
- `highlightUnicode FILE` prints `N:line` for lines containing Unicode (e.g. an em space, U+2003); `highlightTabs FILE` shows each tab as `➤`. Run them when a swarmfile, sample sheet, or parser chokes on pasted text.

## Recipe: is my running job healthy?

1. `sjobs`: still pending? The reason is in `Nodelist`/`Reason`.
2. Running: try `jobload -j JOBID`; if it fails, query the dashboard (for one job, your own session included, swap `--running` for `--jobid JOBID`):

```bash
dashboard_cli jobs --running --fields jobid,partition,elapsed_time,timelimit,cpus,cpu_cur,cpu_avg,mem,mem_cur,mem_max,gpus,gpu_cur,gpu_avg,D_cur,D_avg
dashboard_cli jobs --running --overload     # busy on more than 1.5x their CPUs
dashboard_cli jobs --running --zeroload     # doing nothing
```

| You see | It means | Do |
|---|---|---|
| `cpu_avg` ≈ `cpus`; `mem_max` well under `mem` | healthy | nothing |
| `cpu_avg` far below `cpus`, or listed by `--zeroload` | idle CPUs: single-threaded app, a thread option not set from `$SLURM_CPUS_PER_TASK`, or waiting on I/O | fix the thread option; request fewer CPUs next run |
| `cpu_cur` well above `cpus`, or listed by `--overload` | overloaded: more threads than CPUs | CPUs can't change mid-run; the user cancels and resubmits with more CPUs or a thread count matched to them |
| `mem_cur` or `mem_max` near `mem` | exceeding it gets the job killed | size memory up for the next run |
| `elapsed_time` near `timelimit` | it will hit its walltime | the user can extend it with `newwall`, up to the partition maximum (JOBS.md) |
| `D_cur`/`D_avg` high | threads stuck waiting on I/O | move heavy random I/O and small files to `/lscratch` |
| `gpu_avg` below `gpus` | idle GPUs | check that the app uses every GPU requested (DEEP-LEARNING.md) |

## Recipe: size the next run from the last one

```bash
jobhist JOBID    # State, Runtime vs Walltime, MemUsed vs MemReq (per subjob for swarms)
dashboard_cli jobs --jobid JOBID --fields jobid,state,exit_code,elapsed_time,timelimit,cpus,cpu_util,mem,mem_max,mem_util,gpus,gpu_util,D_max   # JOBID_ = whole swarm
jobdata --show-time-series --human JOBID    # only when phases matter: a single-threaded stretch, a memory spike
```

| Resource | Next request | Docs' examples |
|---|---|---|
| Memory | observed peak (`MemUsed`, `mem_max`) plus a small buffer | 2.0 GB used → `--mem=3g`; 4 GB expected → request 5 GB |
| Walltime | observed runtime plus a buffer | ran 15 min of 90 requested → 20 or 30 min; 5 h → 6 h; multinode: benchmark plus 15–25% |
| CPUs | what the app keeps busy (`cpu_util` near 100%) | "asking for 8 CPUs in an attempt to speed up a single-threaded application ... won't help" |
| GPUs | only if `gpu_util` shows use | "asking for a GPU that the application isn't written to use won't help" |
| Scale-out | benchmark several CPU counts; stop where parallel efficiency falls below 0.7 | efficiency = work on N CPUs ÷ (N × work on 1 CPU) |

- `FAILED` with `MemUsed` = `MemReq`, or a killed job: memory first (full flow: TROUBLESHOOTING.md). `TIMEOUT`: more walltime or checkpoints.
- An estimate under 4 h qualifies for `quick` (JOBS.md). Over-asking delays the start ("smaller jobs are scheduled before larger ones"), and wasted CPU-hours lower the priority of the user's future jobs ([benchmarking](https://hpc.nih.gov/policies/multinode.html#benchmark)).
- Audit many jobs at once:

```bash
dashboard_cli jobs --since -5d --fields jobid,partition,nodes,cpus,mem,gpus,state,elapsed_time,cpu_util,mem_util,gpu_util
dashboard_cli jobs --since -5d --mem-over     # overloaded memory
dashboard_cli jobs --since -5d --bad-swarm    # subjobs too short: bundle them (SWARM.md)
```

## Stale advice on the official pages

- The `freen` examples on the tools page and in the user guide predate the H200 and L40 nodes (as of Sept 2026); the tools page calls its output "just an example" and describes an asterisk on `norm` and two `ccr` lines the output doesn't show. Only a live `freen` counts.
- `dashboard_cli --gpu-type` lists only `p100,v100,v100x,a100`. For newer GPUs, select with `--gpu-only` and read the `gres` field.
- The `batchlim` example values are illustrative (its `persist` row even contradicts the NIMH page). Run `batchlim`.
- The tools page's 2015 `jobhist` example has no `Runtime` column, and its `Walltime` is the time the job ran. Its `0.8GB/cpu` default memory and `x2600` constraint are obsolete too (current defaults: JOBS.md).
- The 2020 cheat sheet's `showq`, `showjob`, and `freen -n` appear nowhere else; treat them as retired.

## Going further

- https://hpc.nih.gov/docs/biowulf_tools.html — every utility with sample output (anchors `#freen`, `#batchlim`, `#sjobs`, `#jobload`, `#jobhist`, `#jobdata`, `#dashboard_cli`, `#whereami`).
- https://hpc.nih.gov/docs/userguide.html#monitor — monitoring overview and the 21-min video "Job Monitoring tools on Biowulf" (https://youtu.be/fLMJ8-t5bm4).
- https://hpc.nih.gov/systems/status/ — service status and batch limits (NIH-only); https://hpc.nih.gov/systems/status/partitions.html — partition usage.
- https://hpc.nih.gov/policies/multinode.html#benchmark — benchmarking and parallel efficiency; https://hpc.nih.gov/docs/ExpUserGuide.html#donts — over-allocation and scheduler load.
- https://hpc.nih.gov/docs/FAQ.html#killed and https://hpc.nih.gov/docs/FAQ.html#swarm_select — reading the dashboard and `jobhist` after a failure.
- https://hpc.nih.gov/nih/about/announcements.php?1208 — the `jobload` outage.
- Live help: `bwulf -h`, `dashboard_cli` (no options), `dashboard_cli jobs -h`, `jobdata -h`, `man jobdata`, `jobload -h`.
