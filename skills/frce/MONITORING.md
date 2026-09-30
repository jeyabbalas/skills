Read-only ways to see what the user's jobs and the cluster are doing on FRCE: `squeue`, `scontrol show job`, `sstat`, `sacct`, `seff`, `sinfo`, `freen`, the status table, the wait-time graphs, and XDMoD; sizing the next run from the last; and waiting for a job without polling. You may run each query here once from your session (ground rule 3 in SKILL.md: no loops, no `watch`); anything that changes or cancels a job is the user's (JOBS.md (Changing or cancelling a job)). What states and pending reasons mean: JOBS.md (Exit codes and job states); what to do about them: TROUBLESHOOTING.md. The node and GPU types behind `freen`'s rows: HARDWARE.md.

Table of contents

- [Your jobs now](#your-jobs-now)
- [Finished jobs](#finished-jobs)
- [Sizing the next run](#sizing-the-next-run)
- [Cluster load and wait times](#cluster-load-and-wait-times)
- [Waiting for a job without polling](#waiting-for-a-job-without-polling)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Your jobs now

```bash
# on the compute node (inside your session) — read-only, once
squeue --me -o '%.12i %.14j %.9P %.10T %.10M %.10l %.10L %.4C %.7m %.20b %.12r %N'
squeue --me --start              # pending jobs: Slurm's estimated start, when it can compute one
scontrol show job JOBID          # everything about one job
```

- Your own session is one of the rows (`$SLURM_JOB_ID`), and so are OnDemand apps and VS Code allocations (`vscode-cpu`, `vscode-gpu`). `-r` lists array tasks one per line.
- Before a long step, check your session's time left once: `squeue -h -j $SLURM_JOB_ID -o %L`. If the step won't fit, write it as a batch job for the user (JOBS.md).
- `scontrol show job` adds the log's path (`StdOut`) and the allocation (`TRES`). It knows a job until 5 minutes after it ends (`MinJobAge`, live Sept 2026), and plain `squeue` drops it at once; after that, use `sacct`.
- `sprio -j JOBID` breaks down a pending job's priority. Fair share outweighs everything else (live, Sept 2026: `sprio -w`): weight 1,000,000, with past usage fading at a 7-day half-life (the user's factor: `sshare -U`). Age adds at most 10,000, after 7 days pending, and the partition a fixed 11,000–100,000; the QOS adds nothing (every QOS has priority 0). So a user who ran heavily this week waits behind light users, and waiting longer barely helps.

Inside a running job:

```bash
# on the compute node (inside your session) — read-only, once
sstat -a -j JOBID -o JobID,NTasks,AveCPU,MaxRSS   # CPU time and peak memory so far, per step
```

- A batch script's own processes are the step `JOBID.batch`. An array task needs its own job ID (the second column of `squeue --me -r -o '%i %A'`), since `sstat` doesn't take `JOBID_7`.
- In your own session, `top -u $USER`, `ps`, and `nvidia-smi` show your node, and `sstat -a -j $SLURM_JOB_ID` its memory peak.
- You never go to another job's node (ground rule 7 in SKILL.md). The user can look inside a running job with `top` or `nvidia-smi` from a shell that joins it, as a step (below) or by ssh to its node (INTERACTIVE.md (Interactive shells with srun)); what they run counts against the job's CPUs and memory.

```bash
# on the FRCE login node — the user runs:
srun --jobid=JOBID --overlap --pty bash   # a shell inside the running job; exit when done
```

## Finished jobs

```bash
# on the compute node (inside your session) — read-only, once
sacct -j JOBID -o JobID%18,JobName%12,Partition,State,ExitCode,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS --units=G
seff JOBID
sacct -S 2026-09-01 -X -s F,TO,OOM,NF -o JobID%18,JobName%12,State,ExitCode,Elapsed   # failures since a date
```

- `sacct` prints a line for the job and one per step (`.batch`, `.extern`, `.0`, …). `ReqMem` and `Timelimit` sit on the job line and `MaxRSS` on the steps; the `.batch` line is the script's own peak. `-X` keeps only the job lines and reports usage such as `MaxRSS` as zero.
- Its time window: without `-S`, jobs since midnight; with `-j`, all history; with `-s` but no `-S`, only jobs running now, so a search for failures needs `-S`.
- `ExitCode` reads `code:signal` (JOBS.md (Exit codes and job states)).
- `seff` "reports on resources utilized for a particular job" ([Slurm Utilities](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/SlurmUtilities)): CPU and memory used, and their efficiency. `seff JOBID_7` covers one array task; for a running job its numbers are incomplete.
- A finished job's log and script: `sacct -j JOBID -o WorkDir%70,SubmitLine%200` gives the directory it was submitted from (where `slurm-JOBID.out` lands unless `--output` put it elsewhere) and the `sbatch` command, which names the script. `sacct -j JOBID --batch-script` prints the script itself only if FRCE stores job scripts (unchecked: `scontrol show config | grep AccountingStoreFlags` lists `job_script` when it does); otherwise ask the user.

## Sizing the next run

"After the job completes, resource usage can be queried with `seff` and `sacct`. These numbers can be used … for tuning resource requests on future jobs" ([Quick Start](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart)).

| Resource | Read | Next request |
|---|---|---|
| Memory | the largest `MaxRSS`, or `seff`'s Memory Utilized | peak plus ~20%, with a unit: 13.1 GB used → `--mem=16g`; not for a job killed for memory (below) |
| Walltime | `Elapsed` | elapsed plus 15–25%, rounded up; 30 minutes or less runs in `short` (JOBS.md (Partitions and walltime)) |
| CPUs | `seff`'s CPU Efficiency, TotalCPU ÷ (Elapsed × CPUs) | near 100%: keep; near 1 ÷ CPUs: the program ran single-threaded, so request 1 or fix its thread flag; in between: fewer CPUs |
| GPUs | GPU use during the run (DEEP-LEARNING.md (Checking the GPU from inside a job)) | only if the program used them |

- **A job killed for memory** (`OUT_OF_MEMORY`) reports a `MaxRSS` near its limit, not its real need, so peak plus 20% fails again. Measure a representative input in your session if the session has the memory; if it doesn't, ask for 1.5–2× the old `--mem`, tell the user it's a guess, and size the run after from that job's `seff`.
- Slurm samples memory, so short spikes can slip past; the margin covers them.
- Size for the largest input. For an array, take the maximum over its tasks:

```bash
# on the compute node (inside your session) — read-only, once
sacct -j ARRAYID -n -P -o MaxRSS --units=G | sort -g | tail -1   # the highest peak of any task
sacct -j ARRAYID -X -n -P -o Elapsed | sort | tail -1           # the longest task, if all took under a day
```

- With nothing measured yet, run the largest input once in your session, or have the user submit a short pilot, and size from that.
- Over-asking costs the user: bigger requests wait longer, and idle reserved cores are lost to everyone (JOBS.md (Scheduler etiquette)).

## Cluster load and wait times

```bash
# on the compute node (inside your session) — read-only, once
sinfo -s                             # per partition: nodes allocated/idle/other/total
sinfo -o '%12P %.11l %.11L %.20C'    # maximum and default time; CPUs allocated/idle/other/total
freen                                # free and total nodes, CPUs, and GPUs by partition and node type
```

`freen` "lists the total and free resources by partition and node type" ([Slurm Utilities](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/SlurmUtilities)), and it runs on compute nodes too (live, Sept 2026). FreeNds counts wholly idle nodes, and the free / total counts leave out drained or down nodes; the per-node columns describe the node type (Disk stays empty). GPU rows name the type (`gpu (l40s)  0 / 15  334 / 928  1 / 56  64  64  4  503g  x6346,u58`), and `gpu (v100)` appears twice, once per host type (36 and 40 CPUs). It is "a current snapshot rather than a guarantee that a resource will still be free" ([Ollama endpoint](https://ncifrederick.cancer.gov/staff/FRCE/OllamaEndpoint)).

**Status table.** The [Status and Metrics](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/StatusandMetrics) page embeds a table generated on each request and readable without login from anywhere on the NIH network:

```bash
# on the compute node (inside your session), or the user's computer on VPN — read-only, once
{ echo "partition nodes_alloc nodes_idle nodes_unavail cores_alloc cores_idle cores_unavail running pending"
  curl -s https://fsitgl-head01p.ncifcrf.gov/jobTable.py | grep -o '<td>[^<]*</td>' | sed 's/<[^>]*>//g' | paste -d' ' - - - - - - - - -; } | column -t
```

- "Idle Nodes" counts only nodes with nothing running: in one reading on 30 Sep 2026, `norm` had 0 idle nodes but 2,045 idle cores. Nodes serve several partitions, so `short` can show allocated cores with no running jobs of its own. `csbdevel` isn't listed.

**Wait-time graphs.** The page's slideshow (https://fsitgl-head01p.ncifcrf.gov/waitTimes.html) shows eight PNGs, `https://batch.ncifcrf.gov/{short,norm,unlimited,gpu}_{7,28}.png`, covering one week and four weeks in log-scale seconds. A probe script submits a small job to each partition and records its wait; the probes "have no dependencies and will not ever hit any limits", so the graphs show best-case start latency: in Sept 2026 near 1 s (`gpu` 1–30 s), with a few peaks of 2–4 minutes. They aren't live (about two days old when checked on 30 Sep 2026): `curl -sI https://batch.ncifcrf.gov/gpu_7.png | grep -i last-modified`.

**XDMoD.** https://xdmod.ncifcrf.gov (Open XDMoD 11) publishes aggregate job statistics for any date range without login. Its waits "are averages of all jobs submitted to any partition over the past month", including jobs held by per-user limits, dependencies, and administrative holds, so they "may not accurately reflect how long any given job submission will take to begin executing" (Status and Metrics). For a large request they are the realistic figure (as of Sept 2026):

| Partition | Average wait, Aug 2026 | 1–29 Sep 2026 | Jobs, Aug 2026 |
|---|---|---|---|
| `gpu` | 8.8 h | 6.0 h | 120,149 |
| `norm` | 1.6 h | 0.4 h | 108,602 |
| `largemem` | 0.7 h | under 0.01 h | 1,036 |
| `short` | 0.2 h | under 0.01 h | 47,140 |
| `unlimited` | 0.1 h | 0.01 h | 1,546 |

Current numbers come from its public API; set the dates, and swap the statistic, in the query and the `jq` filter, for `job_count`, `avg_wallduration_hours`, `total_cpu_hours`, or `total_gpu_hours` as needed:

```bash
# on the compute node (inside your session), or the user's computer on VPN — read-only, once
curl -s https://xdmod.ncifcrf.gov/controllers/user_interface.php \
  --data 'public_user=true&realm=Jobs&group_by=queue&statistic=avg_waitduration_hours&start_date=2026-09-01&end_date=2026-09-29&operation=get_data&format=jsonstore&dataset_type=aggregate&aggregation_unit=Auto&limit=20&offset=0' \
  | jq -r '.records[] | "\(.queue) \(.avg_waitduration_hours)"'
```

XDMoD also lists `csbdevel`, which the status table omits, and a `debug` queue that no longer exists. The public view has no per-user breakdown, and personal XDMoD logins are undocumented (they aren't NIH single sign-on); the user asks the FRCE administrators, who also offer "other user and system metrics … on request" ([Services](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/Services)).

## Waiting for a job without polling

"Do not run squeue or other Slurm client commands that send remote procedure calls to slurmctld from loops in shell scripts or other programs" ([squeue manual](https://slurm.schedmd.com/squeue.html#SECTION_PERFORMANCE)): every query lands on the one controller all FRCE users share. In order of preference:

1. **Email.** The user adds `--mail-type=END,FAIL` and `--mail-user` (JOBS.md (Email)) and hears when the job ends; you do nothing.
2. **A dependent job.** Post-processing goes in a job submitted with `--dependency=afterok:JOBID` (JOBS.md (Dependencies)), so the scheduler waits instead of you.
3. **Check back.** When you must follow a job from your session, query once, do other work, and query again no sooner than five minutes later. A job that runs for hours doesn't need you waiting: tell the user what to check or run when it ends, and stop there.

The status table is generated on each request, so the no-loops rule covers it too, and XDMoD's monthly averages can't tell you when a job ends.

## Stale advice on the official pages

- [Status and Metrics](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/StatusandMetrics) says the probe script runs "every 15 minutes" in one paragraph and "every 30 minutes" in the next, and it doesn't say how old the graphs are → they are redrawn only now and then; read their `Last-Modified`.
- hpc.nih.gov's monitoring advice relies on `sjobs`, `jobhist`, `jobload`, `dashboard_cli`, and `batchlim`, none of which FRCE documents; all but `jobload` were checked and aren't installed (Sept 2026) → `squeue`, `sacct` and `seff`, `sstat`, XDMoD, and `scontrol show partition` (FROM-BIOWULF.md (Translation table)).

## Going further

- FRCE: [Status and Metrics](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/StatusandMetrics) (status table, wait-time graphs, XDMoD), [Slurm Utilities](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/SlurmUtilities) (`freen`, `seff`), [Quick Start](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart) (`squeue --me`, `seff`, `sacct`).
- Live pages, NIH network only: [status table](https://fsitgl-head01p.ncifcrf.gov/jobTable.py), [wait-time graphs](https://fsitgl-head01p.ncifcrf.gov/waitTimes.html), [XDMoD](https://xdmod.ncifcrf.gov); reaching them from elsewhere: SKILL.md (Going further).
- Slurm: [squeue](https://slurm.schedmd.com/squeue.html), [sacct](https://slurm.schedmd.com/sacct.html) with its [fields](https://slurm.schedmd.com/sacct.html#SECTION_Job-Accounting-Fields) and [default time window](https://slurm.schedmd.com/sacct.html#SECTION_DEFAULT-TIME-WINDOW), [sstat](https://slurm.schedmd.com/sstat.html), [sinfo](https://slurm.schedmd.com/sinfo.html), [scontrol](https://slurm.schedmd.com/scontrol.html), [job reason codes](https://slurm.schedmd.com/job_reason_codes.html); [seff's source](https://github.com/SchedMD/slurm/tree/master/contribs/seff); [Open XDMoD](https://open.xdmod.org/11.0/index.html).
- Biowulf docs: [freen](https://hpc.nih.gov/docs/biowulf_tools.html#freen), where the tool comes from; FRCE's prints the same columns, Disk left empty.
- Live: `squeue --me`, `sacct -j JOBID`, `seff JOBID`, `sprio -j JOBID`, `sshare -U`, `sinfo -s`, `freen`.
