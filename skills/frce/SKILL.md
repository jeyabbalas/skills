---
name: frce
description: "Field guide for doing work on NCI's FRCE (Frederick Research Computing Environment), the NCI-Frederick Slurm cluster at batch.ncifcrf.gov, with links to the official docs. Use whenever a task involves FRCE, including when the user mentions ncifcrf.gov hosts, fsitgl nodes, /scratch/cluster_scratch, /mnt/nasapps, or ondemand.ncifcrf.gov. Not for NIH's Biowulf or Helix (hpc.nih.gov, hpcondemand.nih.gov), or for Slurm questions unrelated to FRCE. Covers where an agent may run and what it may do there; accounts and access; sbatch, srun, and job arrays; partitions and GPUs; storage and transfers; modules, conda, containers, and workflows; OnDemand, VS Code, and Jupyter; Ollama LLMs; porting work from Biowulf; and troubleshooting."
---

FRCE, the Frederick Research Computing Environment, is NCI's Slurm cluster at NCI-Frederick, free to NCI and FNLCR staff and run by the FRCE administrators in EIT. This skill is a field guide for real work there: where an agent may run, how to size and write jobs, where data goes, how software is provided, and where the official documentation lives. It was compiled in September 2026 from https://ncifrederick.cancer.gov/staff/FRCE, checked against the live cluster on 30 September 2026, and corrects the official pages where they are stale or wrong. For facts such as limits, versions, paths, and hardware, a live command (`sinfo`, `scontrol show partition`, `freen`, `module avail`) or a newer official page wins over this guide; the ground rules below stand either way.

Table of contents

- [First: where are you running?](#first-where-are-you-running)
- [Ground rules](#ground-rules)
- [FRCE at a glance](#frce-at-a-glance)
- [Which file to read](#which-file-to-read)
- [Going further](#going-further)

## First: where are you running?

FRCE has no policy on AI agents (Sept 2026). This skill adopts NIH HPC's rule for Biowulf ([policies#AI](https://hpc.nih.gov/policies/index.html#AI)) by analogy: an agent runs on the user's own computer or inside a compute-node allocation the user started, never on FRCE's shared login hosts. On the login node, "any process using over 10 CPU-minutes will be automatically killed with a cryptic error message" ([policies](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/MiscellaneousPoliciesandGuidelines)), and a long agent session is such a process.

Before running any command, find out where you are:

```bash
hostname -s; echo "job=${SLURM_JOB_ID:-none} cluster=${SLURM_CLUSTER_NAME:-none}"
```

| You see | You are | Then |
|---|---|---|
| `fsitgl-head01p`, `fsitgl-xfer03p`, or `fsitgl-nx…`, with `job=none` | on a shared login host: batch, batch2 (the transfer node), or the NoMachine host | **Stop.** Run no commands here and open none of the user's files; reading this guide's own files is fine. Tell the user why (this guide's rule, not an FRCE policy, and the 10 CPU-minute kill), answer from this guide what you can, and give them the restart recipe below; meanwhile they can run read-only checks such as `squeue --me` themselves. |
| `fsitgl-hpcNNNp`, a job ID, and `cluster=fnlcr` | on a compute node inside the user's allocation: an `srun` shell or an OnDemand app | Work, under the ground rules, inside the allocation. |
| `fsitgl-hpcNNNp` with `job=none` | on a compute node outside the job's environment: a VS Code `frce-cpu`/`frce-gpu` terminal or another ssh session into a job's node | Confirm once that the user holds a job on this node: `squeue --me -o '%.12i %.14j %N'` lists it under the Slurm name (`fsitgl-hpc058p` is `cn058`), and `scontrol show job JOBID` shows its CPUs and memory. Then work within that allocation, even when the user names more: a `frce-cpu` job has 1 CPU and 20 GB, so run builds and tests in one process (`pytest -n 0`, `make -j1`) and hand heavier runs over as a batch job or a bigger session (INTERACTIVE.md). |
| `biowulf…`, `helix…`, `cnNNNN`, or `cluster=biowulf` | on NIH's Biowulf, not FRCE | This guide doesn't apply there; NIH HPC's rules do (the `biowulf` skill, if installed). |
| anything else | off the cluster, e.g. the user's computer | Write scripts and files locally; hand the user every cluster command, labeled with where to run it. Never `ssh` to FRCE yourself. If nothing in the request names FRCE (NCI staff also use Biowulf), ask which cluster before writing anything cluster-specific. |

**Restart recipe**, for the user when you find yourself on a login host or when they want you working on the cluster directly:

```bash
# on your computer (NIH network or VPN)
ssh USERNAME@batch.ncifcrf.gov
# on the FRCE login node
tmux                                   # survives a dropped connection (reattach: tmux attach), not the monthly login-node reboot
srun -p norm --cpus-per-task=4 --mem=16g --time=8:00:00 --pty bash
# on the compute node (hostname fsitgl-hpcNNNp): cd to the project, then start the agent here
```

Size the session for the heaviest step you'll run in it (limits and GPU requests: JOBS.md). Other homes: a terminal in an OnDemand app (ONDEMAND.md), or VS Code on the user's computer attached to a compute node through `frce-cpu` or `frce-gpu`; INTERACTIVE.md (Choosing a home for an agent session) compares them.

## Ground rules

They govern everything you run on a compute node and everything you hand the user; on a login host, only the stop above applies. Rules 1, 2, and 7 hold even if the user asks otherwise: hand them the command instead. The rest are defaults, and the user's instructions win where they differ.

1. **Never submit, cancel, or change jobs.** This skill leaves every use of the shared queue to the user. That covers `sbatch`, `srun` or `salloc` outside your own allocation, `scancel`, `scontrol update|hold|release|requeue`, starting OnDemand sessions or `vscode-alloc` allocations, HPC API `submit_job` calls, and workflow runs that submit jobs (Snakemake or Nextflow with a Slurm executor). Write the script and check it (`bash -n job.sh`; `sbatch --test-only job.sh` checks the request and estimates its start without submitting, though it may miss one over a partition cap: JOBS.md), then give the user the exact command. Launching steps inside your own allocation (`srun`, `mpirun`) is fine.
2. **Stay inside the allocation.** Size every parallel thing from it, including worker counts the user names (`pytest -n 8`, `make -j 16`): `${SLURM_CPUS_PER_TASK:-${SLURM_CPUS_ON_NODE:-1}}` threads or workers, never `os.cpu_count()`, `multiprocessing.cpu_count()`, `parallel::detectCores()`, `n_jobs=-1`, or `pytest -n auto`, which can count every CPU on the node (`nproc` does respect the allocation). Keep threads × processes within the allocated CPUs, export `OMP_NUM_THREADS` (plus `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`) to match, and stay under the allocated memory: Slurm kills what exceeds it.
3. **Query, don't poll.** Read-only commands are fine: `squeue --me`, `sacct`, `seff`, `sstat`, `sinfo`, `freen`, `scontrol show job|partition|node`. Never `watch` or loop on them; to wait for a job, check at most every five minutes (MONITORING.md), or have the user add `--mail-type=END`.
4. **Protect data.** `/scratch/cluster_scratch` has no snapshots or backups, and nothing there is ever deleted for you. Get the user's explicit go-ahead before deleting, overwriting, syncing with deletion (`rsync --delete`), or changing permissions on shared directories. Never open other users' files or make anything world-readable on your own initiative. Don't read or print the contents of sensitive or controlled-access data (PII, PHI, dbGaP) into the conversation, since what you read goes to your model provider: work on it through scripts and look only at aggregate results, unless the user confirms its terms allow more.
5. **Put things where they belong** (map below). Working data, environments, container images, and caches go under `/scratch/cluster_scratch/$USER` or a group share; code, configs, and results worth keeping go in `/home/$USER`; per-job temporary files go in a directory you create under `/scratch/local` and remove when the job ends, since FRCE has no per-job scratch (JOBS.md). Before a large download or output, check free space (STORAGE.md); if it won't fit, stop and ask.
6. **Leave the user's login environment alone.** Don't edit `~/.bashrc` or `~/.bash_profile` without asking, and never add `module load`, `conda init`, or environment activation to them: an error there can break logins and file transfers.
7. **Stay on your node.** No `sudo` or `su`, no `ssh` to other nodes or to the login hosts, and no workarounds around Slurm or its limits.
8. **Some steps are the user's.** Passwords and NIH Login, SSH key passphrases, browser sessions (OnDemand, Globus, ServiceNow), anything on the user's own computer (SSH config, tunnels, VS Code), and requests to the FRCE administrators. Hand these over as exact commands or steps, each labeled with where it runs.
9. **Verify what changes, and don't assume Biowulf.** Partitions, GPU types, limits, and module versions change, and several official pages are stale (QuickStart still lists three GPU types; five are in service). Check live with `sinfo`, `scontrol show partition`, `freen`, or `module avail NAME`, and pin module versions in scripts. FRCE has no `swarm`, `sinteractive`, lscratch, `/data/$USER`, or `module spider`, and Biowulf partitions such as `quick` and `ccr` don't exist: read FROM-BIOWULF.md before reusing a Biowulf script, habit, or hpc.nih.gov page.

## FRCE at a glance

Hosts (all need the NIH network or VPN; log in with the lower-case NIH username and NIH password):

- `batch.ncifcrf.gov` (`fsitgl-head01p`): the login node, where the user submits and manages jobs.
- `batch2.ncifcrf.gov` (`fsitgl-xfer03p`): the transfer node, for scp, rsync, and some compiling; it can submit jobs too.
- `nx.ncifcrf.gov`: NoMachine desktops on a shared host; heavy work there still goes into a job.
- https://ondemand.ncifcrf.gov: Open OnDemand (NIH Login) for desktops, Jupyter, RStudio, VS Code, MATLAB, and Ollama; every app runs as a job on a compute node.
- `fsitgl-hpcNNNp`: compute nodes (Slurm names them `cnNNN`), reachable only through jobs.

Storage:

| Path | For | Size | Safety |
|---|---|---|---|
| `/home/$USER` | code, scripts, configs, results worth keeping | 256 GB (`df -h ~`), can't be increased | daily snapshots kept 30 days; the last 14 self-restorable from `/home/.snapshot` |
| `/scratch/cluster_scratch/$USER` | working data, environments, containers, job output | 5 TB per user, on a shared file system that can fill (STORAGE.md) | **no snapshots or backups; never purged, so clean up yourself** |
| `/scratch/local` (the same disk as `/tmp`) | per-job temporary files on one node | the node's local disk | not shared between nodes; no per-job cleanup is documented, so clean up yourself; may be wiped at reboot |
| `/mnt/<share>`, `/mnt/projects/<share>` | group data, by request | per share | most shares have snapshots |
| `/mnt/nasapps` | installed software and modulefiles | — | read-only |

## Which file to read

Read only what the task needs: a file's table of contents, then the sections the task touches. Each file names its siblings for adjacent topics; follow a pointer only when the task reaches that topic.

Getting on
- [ACCESS.md](./ACCESS.md) — Read when the user is getting or validating an account, setting up a connection (VPN, SSH clients and keys, X11 servers), changing their login shell, checking status or maintenance, looking for training, or needs the FRCE administrators (email, or which ServiceNow form: software, storage, groups, features).
- [FROM-BIOWULF.md](./FROM-BIOWULF.md) — Read before porting a Biowulf script, swarmfile, pipeline, or habit to FRCE, or when following an hpc.nih.gov page for work on FRCE.

Running work
- [JOBS.md](./JOBS.md) — Read its template and checklist before writing or reviewing any sbatch script or srun command, and other sections as needed: flags and defaults, partitions and walltime, GPU requests, temporary files, exit codes, dependencies, email, MPI, and submitting through the HPC REST API.
- [ARRAYS.md](./ARRAYS.md) — Read when running many independent commands, such as a per-sample or per-file loop or a Biowulf swarmfile: job arrays, throttling, bundling short tasks, and rerunning failures.
- [MONITORING.md](./MONITORING.md) — Read when checking what is running or pending, how efficiently a job ran, cluster load and wait times, or when sizing the next run from the last.
- [HARDWARE.md](./HARDWARE.md) — Read when choosing node or GPU types, when a resource request can't be satisfied, or when asked what hardware FRCE has.
- [WORKFLOWS.md](./WORKFLOWS.md) — Read when running or writing Snakemake or Nextflow pipelines on FRCE, including CCBR pipelines.

Interactive work
- [INTERACTIVE.md](./INTERACTIVE.md) — Read when the user needs a shell, GUI, or IDE on a compute node outside OnDemand, or when choosing where to run an agent session: `srun --pty` sessions, tmux, ssh into a job's node, VS Code through `frce-cpu`/`frce-gpu`, X11, VNC, NoMachine, and SSH tunnels to notebooks or web apps.
- [ONDEMAND.md](./ONDEMAND.md) — Read when using Open OnDemand: the FRCE Desktop, Jupyter, RStudio, VS Code, MATLAB, and other apps, their forms and limits, and managing sessions.

Software
- [MODULES.md](./MODULES.md) — Read when finding, loading, or pinning installed software, when a module or command isn't found, when making personal modulefiles, or when deciding how to get software that isn't installed.
- [PYTHON-R.md](./PYTHON-R.md) — Read when running Python or R: interpreters, installing packages, conda, mamba, and venv environments, R libraries, and Jupyter kernels.
- [CONTAINERS.md](./CONTAINERS.md) — Read when using Apptainer, Singularity, or Docker images: pulling, building, caches, bind paths, GPUs, and containers in jobs.
- [DEVELOPMENT.md](./DEVELOPMENT.md) — Read when compiling or building software: compilers and CPU targets, build systems, MPI, CUDA and cuDNN, and Go, Rust, Java, or Perl.
- [APPLICATIONS.md](./APPLICATIONS.md) — Read when running a scientific application FRCE documents (sequencing, cryo-EM, AlphaFold and structural biology, computational chemistry, image analysis, MATLAB, Dragen), or when looking for reference data.

GPUs and AI
- [DEEP-LEARNING.md](./DEEP-LEARNING.md) — Read when training or running machine-learning models on GPUs: choosing a GPU, PyTorch, TensorFlow, or JAX setup, CUDA compatibility, data staging, multi-GPU jobs, and TensorBoard.
- [LLM-INFERENCE.md](./LLM-INFERENCE.md) — Read when running or calling open-weight LLMs on FRCE: Ollama in OnDemand, an Ollama endpoint job, sizing a model to a GPU, OpenAI-compatible clients, and vLLM.

Data
- [STORAGE.md](./STORAGE.md) — Read when deciding where files go, checking usage or quotas, recovering deleted files, setting permissions, sharing with a group, requesting a share, cleaning up scratch, or handling sensitive data.
- [TRANSFER.md](./TRANSFER.md) — Read when moving data in or out: scp and rsync through the transfer node, data from Biowulf, Globus, and downloads on the cluster.

When things go wrong
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) — Read when a job pends too long, is killed, fails, or prints an error, when a login or connection fails, when a login-node command was killed, when something that used to work stopped working, or when drafting a help request to the FRCE administrators.

## Going further

- **Official hubs.** [Quick Start](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart) · [Documentation](https://ncifrederick.cancer.gov/staff/FRCE/Documentation) · [FAQ](https://ncifrederick.cancer.gov/staff/FRCE/FrequentlyAskedQuestions) · [Support](https://ncifrederick.cancer.gov/staff/FRCE/Support) · [Status](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/StatusandMetrics). The pages are undated and have no section anchors, so link whole pages; each topic file's "Stale advice on the official pages" lists the known errors on its topic.
- **Application docs.** FRCE documents a few dozen applications under [Scientific Software](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware) (APPLICATIONS.md indexes them). [AppDB](https://appdb.ncifcrf.gov/), maintained by ABCS and EIT, lists installed software with install paths and a "How to run" line; `module avail NAME` is the ground truth.
- **Live help.** `module avail NAME`, `module help NAME`, `sinfo -s`, `scontrol show partition NAME`, `freen`, `man sbatch`.
- **NIH-network hosts.** FRCE's service hosts under ncifcrf.gov (the login hosts, OnDemand, AppDB, the live status table, XDMoD) resolve only on the NIH network or VPN; the documentation site ncifrederick.cancer.gov is public. "Could not resolve host" means the machine you're on is off that network: ask the user to open the page and paste what you need.
- **Biowulf docs.** FRCE's own docs call hpc.nih.gov "largely applicable" to FRCE; use it for general how-tos after FROM-BIOWULF.md's translation.
- **Staff.** The FRCE administrators take email for short questions and ServiceNow tickets otherwise; the user sends either. Addresses and forms: ACCESS.md; a request template: TROUBLESHOOTING.md.
