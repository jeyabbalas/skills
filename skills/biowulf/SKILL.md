---
name: biowulf
description: "Field guide for working on NIH's Biowulf HPC cluster and Helix (hpc.nih.gov). Use whenever a task involves Biowulf or NIH HPC, including when the user mentions swarm, sinteractive, lscratch, sjobs, cnNNNN nodes, hpcondemand.nih.gov, or /data paths on the cluster; not for other Slurm clusters, NCI's FRCE included. Covers NIH HPC's AI-agent policy (no agents on the login node or Helix; the user submits jobs) and a where-am-I check; accounts, SSH, HPC OnDemand, and VS Code; sbatch jobs, interactive sessions, partitions, walltimes, GPUs, multinode MPI, dependencies, and swarm; monitoring and right-sizing jobs (jobhist, dashboard_cli, freen, batchlim); node and GPU hardware; storage, quotas, snapshots, ACLs, and sharing; data transfer (cloud, Box, SRA) and Globus; modules, conda, Python, and R; Jupyter, RStudio, and SSH tunnels; deep learning and Ollama; Singularity/Apptainer containers; compilers, CUDA, and building software; Snakemake and Nextflow; and troubleshooting pending, failed, or killed jobs."
---

Biowulf is the NIH intramural research program's Slurm cluster, run by the NIH HPC group together with Helix, its data-transfer host. This skill is a field guide for real work there: what NIH HPC allows an agent to do, how to size and write jobs, where data goes, how software is provided, and where the official documentation lives. It was compiled from hpc.nih.gov in September 2026. Where it disagrees with a live page, `--help` output, or a live command such as `batchlim`, `freen`, or `module spider`, the live source wins.

Table of contents

- [First: where are you running?](#first-where-are-you-running)
- [Ground rules](#ground-rules)
- [Biowulf at a glance](#biowulf-at-a-glance)
- [Which file to read](#which-file-to-read)
- [Going further](#going-further)

## First: where are you running?

NIH HPC policy ([policies#AI](https://hpc.nih.gov/policies/index.html#AI), enforced since 8 Sep 2026):

> **The use of AI agents on Helix and the Biowulf login node is not allowed.** If an AI agent must have direct access to the cluster, users should create an interactive session and only allow the agent access to that compute node. Any AI agent processes found running on login nodes will be cancelled, and user accounts may be disabled after multiple incidents.
>
> **Users are responsible for any actions taken by the AI agent on their behalf.** Jobs will be cancelled and user accounts may be disabled if an agent is found to be exhibiting malicious or destructive behavior.

NIH HPC's [agent guidance](https://hpc.nih.gov/nih/codex.html) adds that agents cannot be sandboxed on Biowulf (an agent there can do anything the user can, including deleting all their data), so staff recommend running agents on the user's own computer instead.

Before running any command, find out where you are:

```bash
hostname -s; echo "job=${SLURM_JOB_ID:-none}"; whereami -f short 2>/dev/null
```

| You see | You are | Then |
|---|---|---|
| `biowulf…` or `helix…`, or `whereami` reports a login node | on the Biowulf login node or Helix | **Stop now.** Your own process there breaks the policy, so make no further tool calls, not even file reads (this skill's other files included). Quote the policy, ask the user to end this agent session, and give them the restart recipe below; meanwhile they can run read-only checks such as `jobhist JOBID` themselves. |
| `cnNNNN` and a job ID | on a compute node, inside one of the user's jobs: an `sinteractive` session (`whereami -f short` prints `sinteractive`), an HPC OnDemand app's terminal (VS Code, Jupyter), or a batch job | Work, under the ground rules, inside the allocation. In a batch job nobody can answer you or run what you hand over until it ends: do only what needs no go-ahead, and list every step left for the user in your final reply, which a non-interactive run prints to the job's output. |
| `cnNNNN` but no job ID (e.g. VS Code Remote-SSH into the session's node) | on a compute node, outside the job's shell | Confirm the user's job is on this node (`squeue -u "$USER" -w "$(hostname -s)" -o "%i %C %m %L"`, once), then work within that job's allocation; details in ACCESS.md. |
| any other host name (usually no `whereami` and no job) | off the cluster, e.g. the user's laptop | Write scripts and files locally, for the user to copy over (TRANSFER.md); hand the user every cluster command, labeled with where to run it, and ask them to paste back the output you need. Never `ssh` to Biowulf or Helix to run commands yourself. |

**Restart recipe** — give this to the user when you find yourself on a login node, or when they want you to work on the cluster directly:

```bash
# on your computer (NIH network or VPN)
ssh USERNAME@biowulf.nih.gov
# on the Biowulf login node
module load tmux; tmux             # survives a dropped connection (reattach: tmux attach), not the monthly login-node reboot
sinteractive --cpus-per-task=4 --mem=16g --gres=lscratch:50 --time=8:00:00
# on the compute node (prompt shows cnNNNN): cd to the project, then start the agent here
```

Size the session for the heaviest step you'll run in it, e.g. at least the memory of a failed job you'll reproduce (limits and options in JOBS.md); add `--tunnel` if a browser app will be needed (TUNNELING.md), or a GPU by replacing `--gres=lscratch:50` with `--gres=gpu:a100:1,lscratch:50` (only the last `--gres` counts; other GPU types, including L40 and H200: JOBS.md). An HPC OnDemand VS Code or Jupyter session is an equally valid home (ACCESS.md). Once you run in the session it holds that terminal, so the user runs the login-node commands you hand over in a second tmux window (`Ctrl-b c` opens one, `Ctrl-b n` switches back) or another SSH login.

## Ground rules

They govern everything you run on a compute node and everything you hand the user. On the login node or Helix you do nothing but the stop above.

1. **Never submit, cancel, or change jobs, even with the user's permission.** NIH HPC's agent guidance: "Under no circumstances should the Codex agent be used to submit jobs" — apply it to yourself. That covers `sbatch`, `swarm`, `sinteractive`, `spersist`, `salloc`, `srun` outside your own allocation, `scancel`, `newwall`, `scontrol update|hold|release`, and workflow runs that submit jobs (Snakemake, Nextflow, or Cromwell with a Slurm executor). Write the script, validate it (`swarm --devel` is a dry run and submits nothing), then give the user the exact command. Launching steps inside your own allocation (`srun`/`mpirun` in a shell that has `$SLURM_JOB_ID`) is fine; without that variable, `srun` asks for a new allocation.
2. **Stay inside the allocation.** Size every parallel thing from it: `${SLURM_CPUS_PER_TASK:-2}` threads or workers — never `os.cpu_count()`, `multiprocessing.cpu_count()`, or `parallel::detectCores()`, which see the whole node, nor `nproc` or `n_jobs=-1`, which can disagree with the allocation. Keep threads × processes ≤ allocated CPUs, and export `OMP_NUM_THREADS` (plus `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`) when using the user's own conda envs; the system python and R modules already set it to 1. Stay under the allocated memory, leaving room for your own process — Slurm kills what exceeds it, and a kill in your session can take you with it.
3. **Query, don't poll.** Read-only commands (`sjobs`, `jobhist`, `dashboard_cli`, `freen`, `batchlim`, `checkquota`) are fine. Never loop or `watch` on `squeue`; the scheduler only refreshes about every 2 minutes. To act after a job ends, prefer a dependent job the user submits (`--dependency`, JOBS.md); if you must wait yourself, run the documented `dashboard_cli --is-active` loop (UTILITIES.md), which reads the dashboard instead of Slurm, in the background.
4. **Protect data.** `/data` is not backed up, and its snapshots (2 nightly, 1 weekly) reach back a week at most. Get the user's explicit go-ahead before deleting or overwriting anything, syncing with deletion (`rsync --delete`, `rclone sync`), or changing permissions on shared directories. A request that names the exact files is the go-ahead for those; when you chose which files match (a pattern, "intermediates", "clean up"), show what matches (count, size, examples) and wait for a yes. Never open other users' files, never make anything world-readable on your own initiative (the sanctioned exceptions, datashare links and one-off `/scratch` hand-offs, are the user's call: STORAGE.md), and never put PII or PHI on the systems. Controlled-access data (e.g. dbGaP) moves only as its data-use terms allow — never into datashare links or shares with unauthorized people, and any transfer of it is the user's decision. Don't read or print the contents of controlled-access or other sensitive data into the conversation, since what you read goes to your model provider: work on it through scripts and look only at aggregate results, unless the user confirms the terms allow more.
5. **Put things where they belong** (map below). Real work lives in `/data/$USER`; temporary files go to `/lscratch/$SLURM_JOB_ID`; nothing large goes in `/home` — conda envs, pip/container/model caches, and R or Julia libraries all belong under `/data`. Before a large download or output, compare its size with `checkquota`; if it won't fit, stop and ask (options in STORAGE.md) rather than fill the quota.
6. **Leave the user's login environment alone.** Don't edit `~/.bashrc` or `~/.bash_profile` without asking, and never add `module load`, `conda init`, or env activation to them: an error there can lock the user out of their login.
7. **Stay on your node.** No `sudo` or `su` (it triggers a security investigation), no `ssh` to other nodes, the login node, or Helix, and no bypassing the Slurm wrappers.
8. **Some steps are the user's.** Passwords, PIV/MFA, SSH key passphrases, tokens and API keys (never ask for, print, or copy them), browser logins (OnDemand, Globus, cloud consoles), anything on their own computer (e.g. the local end of an SSH tunnel), anything on Helix, and requests to NIH HPC staff. Hand these over as exact commands or steps, each labeled with where it runs.
9. **Verify what changes.** Module versions and defaults, GPU types, partitions, tools, and limits change (`svis` and the `visual` partition retired January 2026, K80 GPUs April–May 2026; H200 and L40 nodes arrived September 2026). Check live with `module -r spider '^name$'`, `batchlim`, `freen`, or the page. Many official pages still carry stale examples — node types missing from the current hardware list (`x2650`, `k80`), `python/3.7`, old storage paths such as `/gs6` or `/spin1/users` — and each file here flags the known ones for its topic.

## Biowulf at a glance

Hosts (all require the NIH network or VPN):

- `biowulf.nih.gov` — the login node, where the user submits and manages jobs. Heavy processes and file transfers there get killed.
- `helix.nih.gov` — for interactive data transfers and large file operations; no scientific applications.
- `cnNNNN` — compute nodes, reachable only through the user's own jobs.
- https://hpcondemand.nih.gov — HPC OnDemand web portal (Jupyter, RStudio, VS Code, a desktop); every app runs as a job on a compute node.
- Compute nodes have no direct internet: http, https, ftp, and rsync (daemon protocol) go through a proxy (pip, conda, `wget`, `git` over https work; outbound `ssh`/`scp` do not). Details: TRANSFER.md.

Storage:

| Path | For | Size | Safety |
|---|---|---|---|
| `/home/$USER` | dotfiles, scripts, small code | 16 GB, never increased | backed up, plus snapshots |
| `/data/$USER` | all real work: data, envs, containers, results | 100 GB to start; more on request | **not backed up**; 2 nightly and 1 weekly snapshots |
| `/data/GROUPNAME` | shared group directories | set per group | as `/data` |
| `/lscratch/$SLURM_JOB_ID` | node-local SSD for one job's temp files | what the job requested (`--gres=lscratch:N`) | **deleted when the job ends** |
| `/scratch` | temporary files on the login node or Helix (also one-off sharing) | shared | purged 10 days after last access; **not on compute nodes** |
| `/fdb` | staff-maintained reference data (genomes, indices, BLAST DBs) | — | read-only |

Always write `/data/$USER`, never the physical `/vf/...` path it resolves to. `/tmp` is small and shared; point `TMPDIR` at lscratch.

## Which file to read

Read only what the task needs. Each file covers one topic and names its siblings for adjacent ones.

Getting on
- [ACCESS.md](./ACCESS.md) — Read when the user is connecting or can't connect (VPN, SSH, keys, Kerberos, X11), using HPC OnDemand or its desktop, setting up VS Code, mounting Biowulf storage on their computer (hpcdrive), fixing shell startup files, signing an agent's CLI or extension in from an OnDemand session, remote graphics (X11, the Graphical Session), or asking about accounts, renewals, fees, maintenance windows, or how to reach staff.

Running work
- [JOBS.md](./JOBS.md) — Read before writing or reviewing any sbatch script or sinteractive command: CPUs, memory, walltime, partitions, GPU requests, lscratch, environment variables, multinode MPI, dependencies, exit codes, email, job states, and changing a submitted job.
- [SWARM.md](./SWARM.md) — Read when running many independent commands, such as a per-sample or per-file loop: writing swarmfiles, choosing `-g`/`-t`/`-p`/`-b`/`--time`, dry runs, logs, and rerunning failed subjobs.
- [UTILITIES.md](./UTILITIES.md) — Read when checking what is running, how efficiently it ran, job history, free nodes, or per-user limits, or when sizing the next run from the last one (`sjobs`, `jobhist`, `jobdata`, `dashboard_cli`, `freen`, `batchlim`, `whereami`).
- [HARDWARE.md](./HARDWARE.md) — Read when choosing node or GPU types, `--constraint` features, CPUs-per-GPU limits, or large-memory nodes, or when asked what hardware Biowulf has.
- [WORKFLOWS.md](./WORKFLOWS.md) — Read when running or writing Snakemake, Nextflow (including nf-core), or Cromwell pipelines.

Software
- [MODULES.md](./MODULES.md) — Read when finding, loading, or pinning installed software, when a module or command isn't found, when making personal modulefiles, or when deciding how to install software that isn't installed (module → conda → container → source build → staff).
- [CONDA.md](./CONDA.md) — Read when installing, creating, activating, or repairing conda/mamba environments.
- [PYTHON.md](./PYTHON.md) — Read when running Python: choosing the interpreter, installing packages, multiprocessing and thread counts, headless plotting, Ray, mpi4py.
- [R.md](./R.md) — Read when running R: versions, package libraries, Bioconductor, parallel R, RStudio, Shiny.
- [CONTAINERS.md](./CONTAINERS.md) — Read when using Docker, Singularity, or Apptainer images: pulling, building, binding paths, GPUs, and containers in jobs.
- [DEVELOPMENT.md](./DEVELOPMENT.md) — Read when compiling or installing software from source (compilers and CPU targets, CMake/autotools, MPI, CUDA, math libraries, other languages) or running a Java tool (JVM heap, temp directory, GC threads).

Interactive apps and GPUs
- [JUPYTER.md](./JUPYTER.md) — Read when running Jupyter notebooks or adding a kernel for an environment.
- [TUNNELING.md](./TUNNELING.md) — Read when a web app or port on a compute node must reach the user's browser (TensorBoard, RStudio Server, Shiny, any dashboard), including on Windows.
- [DEEP-LEARNING.md](./DEEP-LEARNING.md) — Read when training or serving models on GPUs: picking and requesting GPUs, PyTorch/TensorFlow/JAX setup, data staging, multi-GPU and multi-node training, TensorBoard, Ollama.

Data
- [STORAGE.md](./STORAGE.md) — Read when deciding where files go, dealing with quotas or a full home directory, recovering deleted files, setting permissions or ACLs, sharing with colleagues, or using `/fdb` or object storage.
- [TRANSFER.md](./TRANSFER.md) — Read when moving data in or out without Globus: scp/rsync, downloads on compute nodes, cloud buckets, Box/OneDrive, SRA/GEO/dbGaP.
- [GLOBUS.md](./GLOBUS.md) — Read when using Globus: large transfers, sharing with outside collaborators, CLI or scheduled transfers, cloud connectors.

When things go wrong
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) — Read when a job pends too long, is killed, fails, or prints an error, when something that used to work stopped working, or when drafting a help request to NIH HPC staff.

## Going further

- **Application docs.** NIH HPC documents several hundred installed applications. Find the app on https://hpc.nih.gov/apps/ and copy its link: URLs are case-sensitive and don't always match the app's name ([STAR.html](https://hpc.nih.gov/apps/STAR.html), `samtools.html`, `fsl.html`). Each page follows one template — Important Notes (module name, test-data variable, reference-data paths), Interactive job (`#int`), Batch job (`#sbatch`), Swarm of jobs (`#swarm`). Adapt its examples rather than copying them: thread counts from `$SLURM_CPUS_PER_TASK`, temp paths on lscratch, current module versions.
- **Live help.** `module spider NAME`, `module help NAME`, `swarm --help`, `sinteractive -h`, `dashboard_cli` with no arguments, `man sbatch`.
- **Hubs.** [User Guide](https://hpc.nih.gov/docs/userguide.html) · [Experienced User Guide](https://hpc.nih.gov/docs/ExpUserGuide.html) · [FAQ](https://hpc.nih.gov/docs/FAQ.html) · [Policies](https://hpc.nih.gov/policies/index.html) · [Announcements](https://hpc.nih.gov/nih/about/announcements.php) (newest facts; they override older pages) · [System status](https://hpc.nih.gov/systems/status/) · [Training](https://hpc.nih.gov/training/).
- **NIH-only pages.** Pages under `hpc.nih.gov/nih/` (announcements, the agent guidance) and `hpc.nih.gov/systems/status/` load only from the NIH network or VPN. Elsewhere they answer HTTP 403, which means the machine you're running on is off that network, not that the page is gone: ask the user to open the page and paste the part you need.
- **Staff.** staff@hpc.nih.gov, weekday business hours; the user sends it (TROUBLESHOOTING.md has a template).
