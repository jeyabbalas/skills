Training and running machine-learning models on FRCE's GPUs: which GPU type suits a workload, installing PyTorch, TensorFlow, or JAX builds that run on FRCE's oldest and newest cards, checking that a job really uses its GPU, staging data, multi-GPU training, and TensorBoard. You write and check the scripts; every command here that submits, cancels, or changes a job, or starts an OnDemand or VS Code session, is the user's to run (ground rules in SKILL.md). GPU specs and each GPU's share of its node: HARDWARE.md (GPUs). The `--gres` syntax and type strings: JOBS.md (GPUs). CUDA and cuDNN modules and compiling CUDA code: DEVELOPMENT.md (CUDA and cuDNN). Where environments live and how jobs activate them: PYTHON-R.md. GPU containers: CONTAINERS.md (GPUs in containers). Serving LLMs: LLM-INFERENCE.md.

Table of contents

- [Choosing a GPU](#choosing-a-gpu)
- [Installing frameworks](#installing-frameworks)
- [Checking the GPU from inside a job](#checking-the-gpu-from-inside-a-job)
- [Data staging and I/O](#data-staging-and-io)
- [Multi-GPU training](#multi-gpu-training)
- [TensorBoard and experiment tracking](#tensorboard-and-experiment-tracking)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Choosing a GPU

FRCE gives no ML guidance of its own ([Stale advice](#stale-advice-on-the-official-pages)). Choose by the GPU memory the job needs (weights, activations at your batch size, optimizer state; `--mem` is host RAM), then by what is free: `freen` (MONITORING.md (Cluster load and wait times)); `gpu` waits run far longer than CPU waits. Each type's memory and compute capability: HARDWARE.md (GPUs).

| Type | Good for | Mind |
|---|---|---|
| `l40s` | the default for training and fine-tuning that fits its memory | — |
| `h200` | models, batches, or contexts too big for the others; the biggest single-node jobs | few cards (HARDWARE.md (GPUs)) and a per-user cap: check `freen` first; an `l40s` usually starts sooner |
| `a100` | large single-GPU memory | few cards and the lowest per-user cap, so long waits |
| `v100` | code that runs on CUDA 12 builds | no native bf16, no FlashAttention-2 (both need sm_80+); default PyTorch wheels skip it ([Installing frameworks](#installing-frameworks)) |
| `p100` | small models and tests | the V100's limits, plus no tensor cores |

- Per-user GPU caps, and what happens to a job over one: JOBS.md (Partitions and walltime). OnDemand forms offer fewer types (ONDEMAND.md (Apps and their forms)).
- Keep `--cpus-per-task` and `--mem` within the requested GPUs' share of their node (HARDWARE.md (GPUs)); on V100 nodes that share leaves few DataLoader workers.
- Do everything except GPU compute (environment builds, downloads, preprocessing, packing data) in a CPU session, so no GPU idles while you think. Run real training as batch jobs.

## Installing frameworks

Framework modules exist, though no FRCE page documents them (live, Sept 2026): `pytorch/2.2.2` (early 2024), `tensorflow` 1.14.0, 2.12.0, and 2.20.0, `transformers/4.18.0` (2022), and `R/4.4.3_torch` for R's torch (TensorRT: DEVELOPMENT.md (CUDA and cuDNN)). Test one on your GPU type before relying on it ([Checking the GPU from inside a job](#checking-the-gpu-from-inside-a-job)). The `python/3.13` module has no torch, tensorflow, or jax (its `pip3 list`, live). For current versions, or to add packages, install into your own environment on cluster scratch (PYTHON-R.md (Virtual environments and conda)). Framework wheels bundle their CUDA libraries, so they need no `module load cuda`, only a new enough driver.

PyTorch wheels against FRCE's GPUs, per PyTorch 2.14.1's [wheel build table](https://github.com/pytorch/pytorch/blob/v2.14.1/.ci/manywheel/build_env_setup.py) (Sept 2026; [2.8](https://github.com/pytorch/pytorch/releases/tag/v2.8.0) dropped Pascal and [2.11](https://github.com/pytorch/pytorch/releases/tag/v2.11.0) Volta from the newer CUDA builds):

| Index | Compiled for | FRCE GPUs it runs on | Driver |
|---|---|---|---|
| `cu126` | sm_50–sm_90 | all five types (L40s runs the sm_86 code) | CUDA 12 (≥ 525) |
| `cu130`, `cu132`; plain `pip install torch` is cu130 since 2.11 | sm_75 and newer | A100, L40s, H200; not P100 or V100 | ≥ 580 |

The GPU nodes' driver version is unmeasured (reading it: DEVELOPMENT.md (CUDA and cuDNN)), so `cu126`, which covers all five types on the older driver, is the safe build. Compute nodes reach the package indexes directly (TRANSFER.md (Downloads on the cluster)), so install in your session:

```bash
# on the compute node (inside your session): a venv as in PYTHON-R.md (Virtual environments and conda), then the wheels
df -h /scratch/cluster_scratch      # several GB of wheels and caches; the shared file system can be full (STORAGE.md)
module load python/3.12
python3 -m venv /scratch/cluster_scratch/$USER/envs/torch
source /scratch/cluster_scratch/$USER/envs/torch/bin/activate
unset PYTHONPATH; export PIP_CACHE_DIR=/scratch/cluster_scratch/$USER/.cache/pip
export HF_HOME=/scratch/cluster_scratch/$USER/hf TORCH_HOME=/scratch/cluster_scratch/$USER/torch   # model caches off /home (Data staging and I/O)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
```

- On a card a wheel wasn't built for, PyTorch warns that the GPU is too old or fails with `no kernel image is available for execution on the device`: reinstall from `cu126`.
- PyTorch has published no conda packages since 2.7: in a conda env, use the same pip line.
- TensorFlow: `pip install 'tensorflow[and-cuda]'` (2.21 on PyPI, Sept 2026). [tensorflow.org](https://www.tensorflow.org/install/pip) lists compute capabilities 6.0 and 7.0 among those supported, so P100 and V100 work.
- JAX: `pip install -U "jax[cuda12]"` covers sm_52 and newer; `"jax[cuda13]"` needs sm_75 or newer and a driver ≥ 580 ([JAX install](https://docs.jax.dev/en/latest/installation.html)). Current JAX needs Python ≥ 3.12.

## Checking the GPU from inside a job

```bash
# on the compute node (inside a GPU job or session)
echo "gpus=${SLURM_GPUS_ON_NODE:-none} visible=${CUDA_VISIBLE_DEVICES:-none}"; nvidia-smi -L
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
python -c 'import torch as t; print(t.cuda.is_available(), t.cuda.device_count(), t.cuda.get_device_name(0), t.cuda.get_device_capability(0), t.cuda.get_arch_list())'
python -c 'import tensorflow as tf; print(tf.config.list_physical_devices("GPU"))'
```

- `nvidia-smi` is installed on CPU nodes too (live, Sept 2026), so only its output counts: `nvidia-smi -L` must list the job's cards.
- CUDA numbers the job's GPUs from 0 whatever `CUDA_VISIBLE_DEVICES` holds, so `cuda:0` is the job's first GPU, and device IDs hard-coded on other clusters (`-g '2,3'`) break.
- The capability, e.g. `(7, 0)`, must be covered by `get_arch_list()` (`sm_70`, or an sm_8x entry for an sm_89 card); otherwise switch to the `cu126` build.
- `seff` reports CPU and memory only. Slurm records GPU memory and utilization (`gres/gpumem`, `gres/gpuutil` in its AccountingStorageTRES, live), but whether `sacct -j JOBID -o JobID,TRESUsageInMax%150` shows them is untested, and you can't open another job's node (MONITORING.md (Your jobs now)). So a batch script logs its own utilization: `nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used --format=csv -l 60 > gpu-$SLURM_JOB_ID.csv &` near the top.
- Before any long run, have the user submit a short test (`--time=00:30:00`, a few hundred steps); its seconds per step and peak memory (`torch.cuda.max_memory_allocated()`) size `--time` and the GPU type.

### Interactive GPU sessions

The user starts one of these, and you work inside it: an OnDemand Jupyter session with a GPU card (ONDEMAND.md (Apps and their forms); your env as a kernel: PYTHON-R.md (Jupyter kernels)), a `frce-gpu` VS Code session (its fixed size: INTERACTIVE.md (VS Code on a compute node)), or `srun -p gpu --gres=gpu:TYPE:1 … --pty bash` (INTERACTIVE.md (Interactive shells with srun)). When the test ends, tell the user to end the session; FRCE's idle-session rule stresses GPUs (INTERACTIVE.md (Interactive shells with srun)).

## Data staging and I/O

- Never train from `/home` (slow; STORAGE.md (Home)). A few large files can be read straight from `/scratch/cluster_scratch`. Many small files read every epoch go into a per-job directory on `/scratch/local`, which spares the shared NAS (pattern and cleanup: JOBS.md (Temporary files)); check `df -h /scratch/local` first, since other jobs on the node share it (STORAGE.md (Node-local scratch)).
- Pack small files into shards (tar or WebDataset, HDF5, LMDB) and unpack them once per job.
- DataLoader workers: at most `$SLURM_CPUS_PER_TASK - 1` in total, divided among processes when there are several (ground rule 2).
- Model caches default to home (`~/.cache/huggingface`, `~/.cache/torch`), which is small and slow: `export HF_HOME=/scratch/cluster_scratch/$USER/hf TORCH_HOME=/scratch/cluster_scratch/$USER/torch` before the first download. A filled cache moves with the user's go-ahead: `mv ~/.cache/huggingface /scratch/cluster_scratch/$USER/hf`. For gated models the user logs in (`hf auth login`); never print the token.
- Download datasets and weights from a CPU session before GPU jobs start, and set `HF_HUB_OFFLINE=1` in GPU jobs so a network stall can't hold a GPU.
- Checkpoint to cluster scratch every N minutes and resume from the newest checkpoint: a long `--time` waits longer, and a crash loses everything since the last save, so run long training as a chain of jobs (JOBS.md (Dependencies)). Copy final models to home or a group share; cluster scratch has no backups.

```bash
#!/bin/bash
#SBATCH --job-name=train
#SBATCH --partition=gpu
#SBATCH --gres=gpu:l40s:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64g
#SBATCH --time=24:00:00
#SBATCH --output=%x-%j.out
# train.sh — the user submits it (sbatch train.sh); 16 CPUs and 64 GB fit one L40s's share of its node
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true             # `module` in batch shells: MODULES.md
module load python/3.12                                           # the venv's interpreter (PYTHON-R.md)
unset PYTHONPATH                                                  # as when the venv was built
source /scratch/cluster_scratch/$USER/envs/torch/bin/activate
export HF_HOME=/scratch/cluster_scratch/$USER/hf HF_HUB_OFFLINE=1   # offline: download the weights in a CPU session first
P=/scratch/cluster_scratch/$USER/myproject                       # placeholder project directory
mkdir -p "$P/logs" "$P/ckpt"
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used --format=csv -l 60 > "$P/logs/gpu-$SLURM_JOB_ID.csv" &
TMPDIR=$(mktemp -d "/scratch/local/${USER}_${SLURM_JOB_ID}_XXXX"); export TMPDIR   # JOBS.md (Temporary files)
trap 'rm -rf "$TMPDIR"' EXIT
tar -xf "$P/data/train.tar" -C "$TMPDIR"
python train.py --data "$TMPDIR/train" --workers $(( SLURM_CPUS_PER_TASK - 1 )) \
    --ckpt-dir "$P/ckpt" --resume          # train.py and its flags are placeholders for the user's code
```

## Multi-GPU training

- Only code written for several GPUs (DDP, FSDP, DeepSpeed, Lightning, Accelerate) uses them (JOBS.md (GPUs)). Measure throughput on 1, 2, and 4 GPUs, and stop adding GPUs when each new one adds little.
- Stay on one node, whose GPU count bounds the job (HARDWARE.md (GPUs)): a 4-GPU L40s job is `--gres=gpu:l40s:4 --cpus-per-task=64` (the whole node) with `--mem` below the node's total. Launch one process per GPU:

```bash
# in the batch script (the user submits it)
export OMP_NUM_THREADS=$(( SLURM_CPUS_PER_TASK / SLURM_GPUS_ON_NODE ))
torchrun --standalone --nproc-per-node="$SLURM_GPUS_ON_NODE" train.py --workers $(( OMP_NUM_THREADS - 1 ))
```

- `--standalone` starts the rendezvous on a free port ([torchrun](https://docs.pytorch.org/docs/2.14/elastic/run.html)), so two jobs sharing a GPU node don't collide or merge, which a fixed `--rdzv-endpoint` port risks.
- Whether the job's GPUs share NVLink or only PCIe: `nvidia-smi topo -m` in the job (HARDWARE.md (Interconnect)). PCIe-only GPUs scale worse for large models.
- Multi-node training over InfiniBand (HARDWARE.md (Interconnect)): `gpu` takes multi-node jobs (JOBS.md (MPI and multinode jobs)), but FRCE has no multi-node GPU example or NCCL guidance, and nobody has tested NCCL there. Prefer the biggest single node (4 × H200). If several nodes are unavoidable, the user asks the admins first; then test with `NCCL_DEBUG=INFO` and confirm that the log shows `NET/IB`, not sockets.

## TensorBoard and experiment tracking

- Have the training code write event files under cluster scratch (e.g. `/scratch/cluster_scratch/$USER/myproject/runs`) so they outlive the job.
- TensorBoard needs no GPU: install it into the same env and run it in a small CPU session, not in the training job. Its launch line, the user's tunnel, and its lack of a login: INTERACTIVE.md (Tunnels to notebooks and web apps). Stop it when the user is done.
- MLflow with a file store on cluster scratch works the same way (`mlflow ui`). Hosted trackers (Weights & Biases, Comet) send metrics, and optionally code and artifacts, to outside servers: the user decides whether that's allowed, and `WANDB_MODE=offline` keeps runs local until then.

## Stale advice on the official pages

- The "Machine & Deep Learning Packages" category ([Deep Learning](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/DeepLearning)) is only a definition of deep learning → install frameworks yourself ([Installing frameworks](#installing-frameworks)).
- AppDB lists `tensorflow` only as 1.14.0 (TF1) → the modules include 2.12.0 and 2.20.0 (live, Sept 2026), and `transformers/4.18.0` is too old for current models: [Installing frameworks](#installing-frameworks).
- [Open OnDemand](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/OpenOnDemand): with a GPU, "the applications are already configured to take advantage of the GPU's capabilities" → true for GPU-built applications; your own Python needs a CUDA build of its framework ([Checking the GPU from inside a job](#checking-the-gpu-from-inside-a-job)).
- Official GPU examples default to `p100` and `v100` (QuickStart, the partitions page, app pages) → the oldest cards, which current default PyTorch wheels skip ([Choosing a GPU](#choosing-a-gpu)).

## Going further

- FRCE: [Hardware](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/FRCEHardwareCapabilities) · [Partitions](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/SlurmPartitionsFeatures) · [Jupyter](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/JupyterNotebooks) · [VS Code on a compute node](https://ncifrederick.cancer.gov/staff/FRCE/VSCodeSlurm).
- PyTorch: [release notes](https://github.com/pytorch/pytorch/releases) (per-version CUDA and architecture changes; [2.12](https://github.com/pytorch/pytorch/releases/tag/v2.12.0) dropped cu128, leaving cu130 the default and cu126 for older drivers) · [install selector](https://pytorch.org/get-started/locally/) · [torchrun](https://docs.pytorch.org/docs/2.14/elastic/run.html).
- [TensorFlow pip install](https://www.tensorflow.org/install/pip) · [JAX install](https://docs.jax.dev/en/latest/installation.html) · [NVIDIA compute capabilities](https://developer.nvidia.com/cuda/gpus).
- Biowulf docs, which need translation (FROM-BIOWULF.md: drop lscratch, `--constraint`, retired `k80`): [deep learning](https://hpc.nih.gov/docs/deep_learning.html), [multi-node DL](https://hpc.nih.gov/docs/deeplearning/multinode_DL.html), [TensorBoard](https://hpc.nih.gov/docs/deeplearning/tensorboard.html).
- Live: `freen`, `nvidia-smi`, `sinfo -p gpu -o '%N %G'`, `scontrol show partition gpu`, `module avail pytorch tensorflow`.
