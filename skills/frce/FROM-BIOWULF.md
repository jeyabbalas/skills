What changes when work moves from NIH's Biowulf to FRCE: what carries over, a translation table from Biowulf's hosts, storage, partitions, commands, and tools to FRCE's (each row pointing to the file that owns the details), a worked port of a batch script, where swarms and data moves are covered, and how to read hpc.nih.gov pages for FRCE work. You port and check the scripts; every command that submits, cancels, or changes a job is the user's to run (ground rules in SKILL.md). Swarmfiles: ARRAYS.md (Converting a Biowulf swarmfile). Copying data from Biowulf: TRANSFER.md (Data from Biowulf).

Table of contents

- [What carries over](#what-carries-over)
- [Translation table](#translation-table)
- [Porting a batch script](#porting-a-batch-script)
- [Porting a swarm](#porting-a-swarm)
- [Moving data between the clusters](#moving-data-between-the-clusters)
- [Using hpc.nih.gov pages on FRCE](#using-hpcnihgov-pages-on-frce)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## What carries over

FRCE's [Biowulf & FRCE differences](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/BiowulfFRCEdifferences) page: "Biowulf and FRCE have many features in common and most programs and scripts written on one will run on the other with only minor changes." Both run Red Hat–family Linux (FRCE: Oracle Linux 8.10) and Slurm, with software loaded by `module`. The differences it lists, each covered where it applies:

- Biowulf gives jobs scratch space "that is automatically cleaned when the job completes. FRCE has a permanent scratch area that the user is responsible for maintaining" (JOBS.md (Temporary files); STORAGE.md (Cluster scratch)).
- `swarm` and `sinteractive` "would be difficult to support on FRCE" (ARRAYS.md; INTERACTIVE.md).
- Labs' instruments can write straight to NCI-Frederick storage, where FRCE sees the data at once (TRANSFER.md (Instrument data)).
- Web servers and other remote systems submit jobs under AD service accounts (JOBS.md (Submitting without logging in)).
- FRCE takes UIDs from AD, so the clusters can't share NFS storage (STORAGE.md (Permissions and sharing)).
- Biowulf is much larger, "with a proportionally larger number of support staff" (its size: [Stale advice](#stale-advice-on-the-official-pages)).

What moves unchanged: standard Slurm (`sbatch`, `srun`, `squeue`, and `sacct` options, the `$SLURM_*` variables, `--cpus-per-task` with `$SLURM_CPUS_PER_TASK`, `--dependency`, job arrays), application command lines, and conda and container recipes once their paths change. What doesn't: everything NIH built around Slurm (the wrappers, lscratch, swarm, the dashboard tools, its partitions and node feature names), Lmod, and `/data` and `/fdb`. For help, the page says: "If you are transitioning a workflow from Biowulf to FRCE and need assistance in modifying scripts or storage locations please email the FRCE admins" (address: ACCESS.md (Support and requests)).

## Translation table

As of Sept 2026; each row points to the file that owns the details.

### Hosts, sessions, and support

| Biowulf | FRCE | Details |
|---|---|---|
| `biowulf.nih.gov`: 5 CPU-minutes per process, at most 4 CPUs at once | `batch.ncifcrf.gov`: 10 CPU-minutes per process | SKILL.md (First: where are you running?); TROUBLESHOOTING.md (Killed on the login node) |
| Helix, for transfers | the transfer node, `batch2.ncifcrf.gov` | TRANSFER.md (Where to run transfers) |
| `whereami` | `hostname -s` and `$SLURM_JOB_ID` | SKILL.md (First: where are you running?) |
| `sinteractive` (2 sessions, 36 h); `srun` and `salloc` shells unsupported | `srun --pty bash` with explicit partition, CPUs, memory, and time | INTERACTIVE.md (Interactive shells with srun) |
| `sinteractive --tunnel`, `$PORT1` | `ssh -L` through the login node to the job's node | INTERACTIVE.md (Tunnels to notebooks and web apps) |
| HPC OnDemand, hpcondemand.nih.gov | Open OnDemand, ondemand.ncifcrf.gov | ONDEMAND.md |
| VS Code: ProxyCommand into the `sinteractive` node | `frce-cpu` or `frce-gpu`, or ProxyJump into a job the user sized | INTERACTIVE.md (VS Code on a compute node) |
| NoMachine: retired | NoMachine at nx.ncifcrf.gov | INTERACTIVE.md (NoMachine) |
| `svis` and the `visual` partition: retired January 2026; NIH points remote graphics to HPC OnDemand, whose Graphical Session has no GPU | a GPU desktop in OnDemand, or VNC from a GPU session | ONDEMAND.md; INTERACTIVE.md (VNC desktops) |
| NIH HPC's AI-agent policy | none; this skill applies NIH's by analogy | SKILL.md |
| staff@hpc.nih.gov | the FRCE administrators, by email or ServiceNow | ACCESS.md (Support and requests) |

### Storage

| Biowulf | FRCE | Details |
|---|---|---|
| `/home/$USER`, 16 GB | `/home/$USER`, far larger (SKILL.md's storage map) but slow: code and configs, not data | STORAGE.md (Home) |
| `/data/$USER`, `/data/GROUP` | `/scratch/cluster_scratch/$USER` for working data, and group shares under `/mnt` | STORAGE.md (Cluster scratch; Group shares) |
| `--gres=lscratch:N`, `/lscratch/$SLURM_JOB_ID`, deleted at job end | nothing to request: a per-job directory the script makes under `/scratch/local` and removes | JOBS.md (Temporary files) |
| `/scratch`: login node and Helix only, purged after 10 days | no counterpart; `/scratch/cluster_scratch` is the `/data` equivalent above | STORAGE.md (Cluster scratch) |
| `/fdb` reference data | `/SeqIdx`, plus per-application paths and CCBR's references | APPLICATIONS.md (Application index), its Reference data part |
| `~/.snapshot` | `/home/.snapshot` (which areas have snapshots: SKILL.md's storage map) | STORAGE.md (Recovering deleted files) |
| `checkquota`, `dust` | `df -h ~` for home, `du` for scratch | STORAGE.md (Checking usage and quotas) |
| hpcdrive, datashare links, the object store | none documented | STORAGE.md (Group shares); TRANSFER.md |

### Jobs and the scheduler

| Biowulf | FRCE | Details |
|---|---|---|
| `sbatch` (a wrapper) prints only the job ID | stock `sbatch` prints `Submitted batch job N`: add `--parsable` in scripts | JOBS.md (Dependencies) |
| 2 CPUs and 4 GB by default; 1 core = 2 CPUs, counts rounded up to even | 1 CPU = 1 core, no rounding; much larger memory and time defaults | JOBS.md (Flags and defaults) |
| `swarm` | a job array over a commands file | ARRAYS.md (Converting a Biowulf swarmfile) |
| `quick` (under 4 h) | none; `short` stops at 30 minutes | JOBS.md (Partitions and walltime) |
| `norm`: the default, 10 days at most, one node | `norm`: the default, 5 days at most; `--time` can move a job to `short` or `unlimited` | JOBS.md (Partitions and walltime) |
| `multinode` | none needed: every partition takes multi-node jobs | JOBS.md (MPI and multinode jobs) |
| `largemem` (at least 350 GB) | `largemem`, for jobs too big for `norm`'s nodes | HARDWARE.md (Large memory and Dragen) |
| `unlimited` | `unlimited` | JOBS.md (Partitions and walltime) |
| `gpu`, `gpuh200` | `gpu`, for every GPU type including H200 | JOBS.md (GPUs) |
| `interactive` | none: `srun` in `norm`, `short`, or `gpu` | INTERACTIVE.md (Interactive shells with srun) |
| `ccr*`, `forgo`, `persist`, other buy-in partitions | none: refused with `invalid partition specified` | TROUBLESHOOTING.md (Job killed or failed) |
| `nci-dragen`, Biowulf's NCI-funded Dragen server | FRCE's own `nci-dragen` and `dragen`: other servers and rules, so don't reuse Biowulf's scripts | APPLICATIONS.md (Sequencing and genomics) |
| GPUs `p100`, `v100` (16 GB), `v100x`, `a100`, plus L40 and H200 nodes | `p100`, `v100` (32 GB), `a100`, `l40s`, `h200`; no `v100x`, `l40`, or `l4` | JOBS.md (GPUs); HARDWARE.md (GPUs) |
| CPUs per GPU capped (a job over the cap pends forever) | no cap, but stay within the node's per-GPU share | JOBS.md (GPUs); HARDWARE.md (GPUs) |
| `--constraint` features (`x6140`, `gpua100`, `ibhdr200`) | other names, such as the CPU-model tag `x6342`; pick GPUs by gres type | HARDWARE.md (Features and constraints) |
| `newwall` | `scontrol update JobId=N TimeLimit=...` (the user's), within limits | JOBS.md (Changing or cancelling a job) |
| mail to `$USER@biowulf.nih.gov` by default | no known default: always pass `--mail-user` | JOBS.md (Email) |
| "Palantir", as FRCE's differences page calls it ([Stale advice](#stale-advice-on-the-official-pages)) | the HPC REST API, and approved web servers | JOBS.md (Submitting without logging in) |

### Monitoring tools

| Biowulf | FRCE | Details |
|---|---|---|
| `sjobs`, `jobload` | `squeue --me`, `sstat` | MONITORING.md (Your jobs now) |
| `jobhist`, `jobdata`, `dashboard_cli`, the User Dashboard | `sacct`, `seff`; XDMoD for cluster-wide numbers | MONITORING.md (Finished jobs) |
| `batchlim` | `scontrol show partition`, `sacctmgr show qos` | JOBS.md (Partitions and walltime) |
| `freen` | `freen`, Biowulf's program, also on FRCE | MONITORING.md (Cluster load and wait times) |
| `nodetype` | `scontrol show node cnNNN` | HARDWARE.md (Node types) |
| the system status page | the Status and Metrics page and its live partition table | MONITORING.md (Cluster load and wait times) |
| the `dashboard_cli --is-active` wait loop | `--mail-type`, or a dependent job; no polling loops | MONITORING.md (Waiting for a job without polling) |

### Software and services

| Biowulf | FRCE | Details |
|---|---|---|
| Lmod: `module spider`, `module -r`, `(D)`, Lua personal modulefiles | Environment Modules: `module avail -C`, `module search`, `@` version specs, Tcl modulefiles | MODULES.md (Environment Modules, not Lmod) |
| names such as `CUDA/12.1`, `cuDNN/8.9.2/CUDA-12` | lower case and other schemes, such as `cuda/11.8` and `cudnn/8.8.3-cuda11`; bare names can load surprising defaults, so pin | MODULES.md (Loading and pinning versions); DEVELOPMENT.md (CUDA and cuDNN) |
| `python/3.x` modules are conda environments | `python/3.x` modules are staff CPython builds | PYTHON-R.md (Python on FRCE) |
| `mamba_install`, conda under `/data` | a conda module, or your own Miniforge on scratch | PYTHON-R.md (Virtual environments and conda) |
| Apptainer with staff binds (`sing_binds`), cache under `/data` | explicit `-B` binds, cache on scratch | CONTAINERS.md (Running containers) |
| NIH's Snakemake profile and Nextflow `$NXF_CONFIG` | none: write an FRCE profile | WORKFLOWS.md |
| downloads on compute nodes through NIH's proxy | direct, with no proxy | TRANSFER.md (Downloads on the cluster) |
| the "NIH HPC Data Transfer (Biowulf)" Globus collection | FRCE's own collection | TRANSFER.md (Globus) |
| Gaussian | not licensed on FRCE: jobs stay on Biowulf | APPLICATIONS.md (Computational chemistry) |

## Porting a batch script

A Biowulf job and its FRCE port; `mytool`, `VERSION`, and `SHARE` are placeholders. The original, for comparison:

```bash
#!/bin/bash
# Biowulf original: not for FRCE
#SBATCH --partition=quick,norm
#SBATCH --cpus-per-task=16
#SBATCH --mem=64g
#SBATCH --time=4:00:00
#SBATCH --gres=lscratch:200
#SBATCH --constraint=x6140
set -e
module load mytool/2.1
export TMPDIR=/lscratch/$SLURM_JOB_ID
cd /data/$USER/proj
mytool --threads "$SLURM_CPUS_PER_TASK" --tmpdir "$TMPDIR" \
    --ref /fdb/igenomes/Homo_sapiens/UCSC/hg38/Sequence/WholeGenomeFasta/genome.fa s1.bam > s1.out
```

The port, saved as `job.sh`:

```bash
#!/bin/bash
# FRCE port: the user submits it (below)
#SBATCH --partition=norm
#SBATCH --cpus-per-task=16
#SBATCH --mem=64g
#SBATCH --time=4:00:00
#SBATCH --output=%x-%j.out
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true   # module init: MODULES.md (Modules in batch jobs and scripts)
module load mytool/VERSION                             # FRCE's name and version: module avail -C mytool
TMPDIR=$(mktemp -d "/scratch/local/${USER}_${SLURM_JOB_ID}_XXXX"); export TMPDIR   # JOBS.md (Temporary files)
trap 'rm -rf "$TMPDIR"' EXIT
cd /scratch/cluster_scratch/$USER/proj
mytool --threads "$SLURM_CPUS_PER_TASK" --tmpdir "$TMPDIR" \
    --ref /mnt/SHARE/refs/hg38/genome.fa s1.bam > s1.out
```

What changed, and what to check in any port:

1. **Partition.** No `quick`: a 4-hour job goes to `norm` (JOBS.md (Partitions and walltime)).
2. **lscratch.** The `--gres` line is gone (FRCE refuses it). The job makes and removes its own temporary directory, and nothing reserves the space: check free space before a big temporary footprint (STORAGE.md (Node-local scratch)).
3. **Constraint.** Gone: FRCE's features have other names. Choose hardware through the partition and the request's size, and a CPU type, if it matters, by FRCE's tag (HARDWARE.md (Features and constraints)).
4. **Paths.** `/data/$USER` becomes `/scratch/cluster_scratch/$USER`. For `/fdb/...`, look under `/SeqIdx` first (`ls /SeqIdx/igenomesdb/Homo_sapiens` in your session, which also shows the node mounts it), confirming the build rather than assuming Biowulf's layout; otherwise keep a copy on a share, as here (STORAGE.md (Reference data and read-only areas)).
5. **Modules.** Names, case, and versions differ: look each one up (MODULES.md (Finding software)) and pin it.
6. **CPUs and memory.** FRCE counts a CPU as a core, so `--cpus-per-task=16` is 16 cores there and 8 on Biowulf; keep the thread count from `$SLURM_CPUS_PER_TASK` either way. Keep `--mem` too: FRCE's default grows with the CPU count, past what most nodes hold (JOBS.md (Flags and defaults)).
7. **GPU jobs** also change the GPU type (`v100x` → `v100`), drop GPU constraints, and fit CPUs to the node's per-GPU share (JOBS.md (GPUs); HARDWARE.md (GPUs)).
8. **Chained jobs.** `jid=$(sbatch job.sh)` becomes `jid=$(sbatch --parsable job.sh)` (JOBS.md (Dependencies)).
9. **Checks.** `bash -n job.sh`, then `sbatch --test-only job.sh` in your session (JOBS.md (Checklist before handing over)).

```bash
# on the FRCE login node, in the script's directory — the user runs:
sbatch --parsable job.sh
```

## Porting a swarm

FRCE has no swarm. ARRAYS.md (Converting a Biowulf swarmfile) turns a swarmfile into a job array's commands file and maps every swarm option (`-g`, `-t`, `-b`, `-p`, `--module`, `--devel`, and the rest) to the array script's flags, including the resources swarm set implicitly.

## Moving data between the clusters

- No file system is shared, because UIDs differ: data is copied, from Helix or by Globus (TRANSFER.md (Data from Biowulf; Globus)).
- A Biowulf `/data/GROUP` becomes an FRCE group share (requesting one: STORAGE.md (Group shares)).
- Rebuild conda environments on FRCE rather than copying them, since their paths are baked in (PYTHON-R.md (Virtual environments and conda)); SIF images copy as they are.

## Using hpc.nih.gov pages on FRCE

FRCE calls Biowulf's documentation "largely applicable to FRCE". The application usage transfers; the cluster plumbing doesn't. First look for an FRCE page (APPLICATIONS.md (Application index)) and AppDB (MODULES.md (Finding software)); then translate the Biowulf page part by part:

| On the hpc.nih.gov page | On FRCE |
|---|---|
| `module load NAME/VERSION` | FRCE's name and version, from `module avail -C NAME` |
| `sinteractive`, lscratch, the swarm section, `/data` and `/fdb` paths, partitions, `--constraint` | the [translation table](#translation-table) |
| NIH helper commands (`run_singularity`, `ollama_start`, `sing_binds`, `mamba_install`, `jobhist`) | none on FRCE: the underlying commands, from the topic file |
| threads from `$SLURM_CPUS_PER_TASK`, memory advice, the application's own options | carry over as written |

The application index is https://hpc.nih.gov/apps/; page URLs are case-sensitive, so copy the link rather than guessing it. Pages under hpc.nih.gov/nih/ and /systems/status/ load only from the NIH network or VPN: a 403 there means the machine is off that network, not that the page is gone.

## Stale advice on the official pages

- [Biowulf & FRCE differences](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/BiowulfFRCEdifferences): "any documentation from the Biowulf site will be largely applicable to FRCE" → true of applications, not of lscratch, swarm, partitions, node features, Lmod commands, or NIH's helper tools: translate with this file.
- The same page: "Biowulf is about 25 times the size of FRCE both in the number of servers and the total number of cores" → about 10 to 12 times by cores as of Sept 2026: Biowulf's hardware page gives 76,572 cores in its header (its rows add up to about 97,000); FRCE's count: HARDWARE.md (Stale advice on the official pages).
- The same page: Biowulf submits from web servers "though the Palantir service (as does FRCE)" → no hpc.nih.gov page documents Palantir; FRCE's remote route is the HPC REST API (JOBS.md (Submitting without logging in)).

## Going further

- FRCE: [Biowulf & FRCE differences](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/BiowulfFRCEdifferences), [Quick Start](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart), [hardware](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/FRCEHardwareCapabilities).
- Biowulf docs, the originals this file translates: the [User Guide](https://hpc.nih.gov/docs/userguide.html) ([#partitions](https://hpc.nih.gov/docs/userguide.html#partitions), [#int](https://hpc.nih.gov/docs/userguide.html#int), [#local](https://hpc.nih.gov/docs/userguide.html#local), [#gpu](https://hpc.nih.gov/docs/userguide.html#gpu)), [swarm](https://hpc.nih.gov/apps/swarm.html), [Biowulf utilities](https://hpc.nih.gov/docs/biowulf_tools.html), [modules](https://hpc.nih.gov/apps/modules.html), [storage](https://hpc.nih.gov/storage/), [transfers](https://hpc.nih.gov/docs/transfer.html), [important limits](https://hpc.nih.gov/docs/ExpUserGuide.html#important-limits), [hardware](https://hpc.nih.gov/systems/hardware.html), [the AI-agent policy](https://hpc.nih.gov/policies/index.html#AI).
- The `biowulf` skill, if installed, covers work on Biowulf itself.
- Live: `sinfo -s`, `sinfo -o '%P %c %m %G %f'`, `scontrol show partition`, `module avail -C NAME`, `freen`, `sbatch --test-only job.sh`.
