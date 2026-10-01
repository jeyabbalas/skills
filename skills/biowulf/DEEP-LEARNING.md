Training, fine-tuning, and serving models on Biowulf GPUs: how GPU work splits between you and the user, framework setup, data staging, verifying and monitoring GPU use, multi-GPU and multi-node training, checkpointing, TensorBoard, and Ollama. GPU request syntax and the CPUs-per-GPU rule are in JOBS.md; GPU models, VRAM, and per-GPU CPU caps in HARDWARE.md; conda mechanics in CONDA.md; container details in CONTAINERS.md; tunnel mechanics in TUNNELING.md; the full `nvidia-smi`/`dashboard_cli` reference in UTILITIES.md.

Table of contents

- [Who does what with GPUs](#who-does-what-with-gpus)
- [First GPU job checklist](#first-gpu-job-checklist)
- [Choosing and requesting GPUs](#choosing-and-requesting-gpus)
- [Framework setup](#framework-setup)
- [Data staging and caches](#data-staging-and-caches)
- [Single-GPU batch template](#single-gpu-batch-template)
- [Verifying and monitoring GPU use](#verifying-and-monitoring-gpu-use)
- [Multi-GPU and multi-node training](#multi-gpu-and-multi-node-training)
- [Walltime, checkpoints, and pipelines](#walltime-checkpoints-and-pipelines)
- [TensorBoard](#tensorboard)
- [Ollama](#ollama)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Who does what with GPUs

You can use a GPU only if it is allocated to the job you run in; other jobs' nodes are off limits, and every submission is the user's (SKILL.md). So:

- **Do everything except GPU compute in a CPU session**: code, env builds, downloads, data packing, preprocessing. No GPU idles while you think.
- **Smoke-test on a GPU** one of two ways:
  - *Short batch test* (preferred): write `smoke.sh` (1 GPU, a few hundred steps, `--time=00:30:00`), give the user the `sbatch` line, and once they report it finished (or after one `sjobs` check), read `slurm-JOBID.out` in the directory they submitted from.
  - *GPU interactive session*: the user starts one and starts you inside it (it counts toward their two interactive jobs; JOBS.md). Test, then tell the user to end it; the GPU idles while you reason.
    ```bash
    # on Biowulf (login node) — the user runs this
    sinteractive --gres=gpu:1,lscratch:50 --constraint="gpuv100x|gpua100|gpul40" -c 8 --mem=32g --time=2:00:00
    ```
- **Real training runs are batch jobs** ("Most jobs should be run as batch jobs"). An interactive session dies with the user's login shell (JOBS.md).
- **H200s interactively**: one per user, for development and testing; the request form is unverified (JOBS.md, GPUs).

## First GPU job checklist

1. **Fit VRAM, not `--mem`**: pick the smallest GPU whose memory holds the model at your batch size; `--mem` is host RAM.
2. **Smoke-test on 1 GPU**: confirm the framework sees it (see Verifying below), and record peak GPU memory (`torch.cuda.max_memory_allocated()`) and seconds per step.
3. **Stage data** into `/lscratch/$SLURM_JOB_ID`, with lscratch in the same `--gres` as the GPU, and `export TMPDIR=/lscratch/$SLURM_JOB_ID`.
4. **Keep CPUs within the per-GPU cap** of every GPU type the job may land on (rule in JOBS.md, values in HARDWARE.md); size DataLoader workers from `$SLURM_CPUS_PER_TASK`.
5. **Set `--time`** from measured step time plus a buffer; don't rely on the partition default.
6. **Checkpoint to `/data`** while training, resumably; copy final outputs off lscratch before the script ends.
7. **Add GPUs only after** one GPU runs well and the code is written for several (see Multi-GPU below).
8. **Hand the user the exact submit line**, labeled `# on Biowulf (login node)`.

## Choosing and requesting GPUs

- Choose by VRAM, then availability: `freen | grep -E 'Partition|----|gpu'` shows free GPUs per type, and its `Disk` column is the most lscratch a job can get on that type.
- When several types would do, request untyped GPUs with a feature OR list (the Ollama page's pattern); it tends to start sooner [inference]. Size the batch for the smallest VRAM in the list. Newer framework builds can drop old GPU architectures, so smoke-test before relying on P100/V100 [generic].
- L40 and H200 have no documented `--gres` type; the lines below use JOBS.md's untyped forms.

```bash
# on Biowulf (login node) — the user runs these; sizes are examples (hardware and limits as of Sept 2026)
# 1 GPU, any listed type; -c 8 is under every listed type's per-GPU cap
sbatch --partition=gpu --gres=gpu:1,lscratch:100 --constraint="gpuv100x|gpua100|gpul40" -c 8 --mem=32g --time=12:00:00 train.sh
# 1 L40 (48 GB; staff: L40 nodes are "optimized for single-GPU jobs")
sbatch --partition=gpu --gres=gpu:1,lscratch:200 --constraint=gpul40 -c 16 --mem=64g --time=24:00:00 train.sh
# 1 A100 (80 GB; documented type string)
sbatch --partition=gpu --gres=gpu:a100:1,lscratch:200 -c 16 --mem=48g --time=24:00:00 train.sh
# 4 H200 on one node (141 GB each, NVLink); gpuh200 batch jobs need >= 2 H200s and <= 24 h (JOBS.md)
sbatch --partition=gpuh200 --gres=gpu:4,lscratch:500 -c 64 --mem=512g --time=24:00:00 train.sh
```

Runs under 4 h can also use `quick`, which holds 7 H200 nodes (Sept 2026) and, in `freen`'s documented example, some A100 buy-in nodes. Whether gpuh200's 2-GPU minimum applies there isn't stated, and `batchlim` shows only maxima: request at least 2 H200s in `quick` too, or the user asks staff.

## Framework setup

| Route | Use when | How (as of Sept 2026) |
|---|---|---|
| Central `python` module | PyTorch, TensorFlow, Keras as shipped | `module load python/3.12` (the 3.11 and 3.12 modules added newer PyTorch and TF in Jan 2025). TF as NIH documents it: `module load cuDNN/8.9.2/CUDA-12 CUDA/12.1 python/3.12` (TF 2.16.2). |
| Conda env in `/data` (CONDA.md) | pinned versions, packages the module lacks | GPU TensorFlow per NIH: `mamba install 'tensorflow=*=cuda*'` |
| Container (CONTAINERS.md) | NGC or vendor images, exact stacks | add `--nv`: `singularity exec --nv docker://tensorflow/tensorflow:latest-gpu python TFlow_example.py` |
| `jax` module | quick JAX tests | `module load jax`, then the `python-jax` wrapper; sets `JAX_HOME`. It is JAX 0.3.x on CUDA 11 (2022-era), so for current JAX use an env or container [inference]. |
| Application module | a packaged DL tool | check [apps#deeplearning](https://hpc.nih.gov/apps/#deeplearning) first (DeepLabCut, nnUNet, BioBERT, SpliceAI, …) |

- Module package sets change; check what you got: `python -c 'import sys, torch; print(sys.version, torch.__version__, torch.version.cuda)'`. python/3.11+ ignore or refuse `pip install --user` (PYTHON.md); make a conda env instead.
- GPU envs built in a CPU session [generic]: conda-forge picks CUDA builds only when it detects a GPU driver, so it can silently resolve CPU-only PyTorch/TF (or refuse `=*=cuda*` pins). Set `CONDA_OVERRIDE_CUDA` to a CUDA 12 version, e.g. `CONDA_OVERRIDE_CUDA=12.4 mamba create -n torch python=3.12 'pytorch=*=cuda*'`, then check that `torch.version.cuda` isn't `None`; a smoke test's `nvidia-smi` shows the highest CUDA the nodes' driver supports. Or build in a GPU session.
- Containers: pull once to a SIF in `/data` and run that file; pass `--nv` on every exec/run. The container's CUDA must be supported by the host driver [generic].
- CUDA and cuDNN modules (naming, pairing, current versions, requesting a missing one) and compiling CUDA code: DEVELOPMENT.md. The TensorFlow line above is the pairing NIH documents.
- Julia Flux, as NIH's page loads it (an old cuDNN; see Stale advice): `module load cuDNN/8.2.1/CUDA-11.3 julialang/1.9.2`; packages land in `~/.julia` in home (moving it: DEVELOPMENT.md).

## Data staging and caches

- **Train from lscratch.** NIH's pattern: lscratch in the same `--gres` as the GPU; inside the job, make dirs under `/lscratch/$SLURM_JOB_ID`, download or untar data there, write outputs there, copy results back. It is wiped when the job ends.
- **Few large files, not many small ones.** Many files in one directory slow lscratch for everyone on the node; NIH suggests subdirectories, sqlite3, or a python shelf. Tar, HDF5, LMDB, or WebDataset shards serve the same purpose [generic].
- **Pre-download datasets before any distributed launch**: "simultaneous setup from the distributed training script has race conditions" (multinode_DL page). Download once to `/data` from a CPU session, then stage.
- **ImageNet is already on disk** at `/fdb/imagenet`, read in place as `--data_dir=/fdb/imagenet` in NIH's benchmarks (2020-era; `ls` it first).
- **Point model caches at `/data` before the first download**: the `dust` example on NIH's storage page shows a Hugging Face cache using 45% of a home directory. The Ollama module already redirects its models; container caches: CONTAINERS.md; moving existing caches: STORAGE.md.
  ```bash
  export HF_HOME=/data/$USER/.cache/huggingface TORCH_HOME=/data/$USER/.cache/torch   # [generic] upstream variables
  ```
- **DataLoader workers**: at most (CPUs ÷ training processes) − 1 per process [generic]: `$SLURM_CPUS_PER_TASK - 1` for one process, but with torchrun's N processes sharing one task, `$(( SLURM_CPUS_PER_TASK / N - 1 ))`. The per-GPU CPU cap bounds this.

## Single-GPU batch template

```bash
#!/bin/bash
# train.sh — the user submits it with an sbatch line from "Choosing and requesting GPUs"
set -e
module load python/3.12                   # or activate a conda env (CONDA.md)
export TMPDIR=/lscratch/$SLURM_JOB_ID
export HF_HOME=/data/$USER/.cache/huggingface
RUN=/data/$USER/myproject/runs/$SLURM_JOB_ID
mkdir -p "$RUN" /lscratch/$SLURM_JOB_ID/out
trap 'cp -r /lscratch/$SLURM_JOB_ID/out "$RUN"/' EXIT    # also runs when set -e aborts the script
tar -xf /data/$USER/myproject/data/train.tar -C /lscratch/$SLURM_JOB_ID
# flag names are placeholders for the user's training script
python train.py --data /lscratch/$SLURM_JOB_ID/train \
    --workers $(( ${SLURM_CPUS_PER_TASK:-2} - 1 )) \
    --out /lscratch/$SLURM_JOB_ID/out \
    --checkpoint-dir /data/$USER/myproject/ckpt --resume   # not per job, so the next job resumes after a timeout; don't count on the trap then
```

## Verifying and monitoring GPU use

```bash
# on the compute node (inside the job or session)
nvidia-smi                                 # this job's GPUs, memory in use, utilization
python -c 'import torch; print(torch.cuda.is_available(), torch.cuda.device_count(), torch.cuda.get_device_name(0))'
python -c 'import tensorflow as tf; print(tf.config.list_physical_devices("GPU"))'
timeout 15m nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used --format=csv -l 10 > gpu.csv &   # [generic] sample a smoke test
```

- NIH's pages expect `True` and the GPU count from PyTorch. Current TensorFlow logs `Created device /job:localhost/replica:0/task:0/device:GPU:0 with N MB memory`; the "Found device 0 with properties" lines on the DL pages are TF 2.1-era. The reliable check is a non-empty `tf.config.list_physical_devices("GPU")`. `whereami -f pretty` also lists the session's GPUs (e.g. `1 a100`).
- A batch job on another node: you can't log in there, so query the dashboard once (values up to a minute old; UTILITIES.md):
  ```bash
  dashboard_cli jobs --jobid JOBID --fields jobid,state,elapsed_time,gpus,gpu_avg,gpu_util,cpus,cpu_util,mem_util
  dashboard_cli jobs --since -5d --gpu-only --fields jobid,partition,gpus,state,elapsed_time,cpu_util,mem_util,gpu_util
  ```
- Reading it [inference]: low `gpu_util` with busy CPUs means the input pipeline is the bottleneck (more workers within the cap, packed or pre-decoded data). Both low means I/O wait (stage to lscratch) or code that isn't using the GPUs. GPU memory near full: smaller batch, mixed precision, or a bigger GPU.

## Multi-GPU and multi-node training

- "**The python code has to explicitly written to use multi-GPU.**" A GPU the code doesn't use is waste; NIH's BERT example requests two GPUs for code that shows no multi-GPU setup.
- Scaling depends on the data. In NIH's benchmarks the V100's CIFAR-10 throughput "maxed" out with 1 GPU while ImageNet scaled well. Measure throughput on 1, 2, and 4 GPUs; NIH's ~0.7 parallel-efficiency bar for CPUs (JOBS.md) is a sensible stopping point for GPUs too [inference].
- Prefer one node [inference]: a user may hold up to 8 H200s in gpuh200 (Sept 2026), a full NVLink node with no inter-node traffic.

Single node, as NIH shows it: TensorFlow `MirroredStrategy` (TF models repo, `mnist_main.py --distribution_strategy=mirrored --num_gpus=$GPU_N`), and PyTorch `nn.DataParallel` only. DDP via `torchrun --standalone --nproc_per_node=N` is upstream's recommended path but undocumented on Biowulf [generic]; smoke-test it on 2 GPUs first.

Multi-node: NIH documents two patterns, both in the `gpu` partition with `--nodes=2` (`multinode` has no GPU nodes).

1. **PyTorch Lightning DDP launched by `srun`** (no torchrun): "pytorch-lightning autodetects Slurm environment and configures NCCL", and it "works best when submitted as a Slurm batch script". NIH's script, modernized:
   ```bash
   #!/bin/bash
   #SBATCH --partition=gpu
   #SBATCH --nodes=2
   #SBATCH --ntasks-per-node=4
   #SBATCH --gres=gpu:a100:4
   #SBATCH --mem=16g
   #SBATCH --time=00:30:00
   # one task per GPU; the page requests gpu:k80:4 (retired)
   source /data/$USER/conda/etc/profile.d/conda.sh && conda activate lightning   # env with torch, torchvision, pytorch-lightning; page: python/3.8 + pip install --user
   srun python torch_test.py 2 4        # nodes, GPUs per node: must match --nodes and --ntasks-per-node
   ```
   - The trainer as NIH writes it: `pl.Trainer(strategy=DDPStrategy(find_unused_parameters=False), accelerator="gpu", num_nodes=nodes, devices=gpus)`, where `devices` is per node. Newer releases also import as `lightning.pytorch` [generic].
   - Add `--cpus-per-task` for DataLoader workers; with one task per GPU, keep it within the per-GPU cap. Progress bars garble the Slurm log; that is expected.
   - lscratch is per node (add it to the `--gres`, e.g. `gpu:a100:4,lscratch:200`), so stage with one task per node. Give `-N` and `-n` explicitly, because a step otherwise inherits the job's `SLURM_NTASKS` [generic]: `srun -N "$SLURM_NNODES" -n "$SLURM_NNODES" --ntasks-per-node=1 tar -xf /data/$USER/train.tar -C /lscratch/$SLURM_JOB_ID`.
2. **Horovod (TensorFlow) in Singularity with host MPI**: `mpirun -np $SLURM_NTASKS -bind-to none -map-by slot -mca pml ob1 -mca btl ^openib -x NCCL_DEBUG=INFO singularity run --nv <image>.sif python ...`, with host openmpi and CUDA that "need to match with the container (as much as possible)". The example is 2019-era ([multinode_DL.html#horovod](https://hpc.nih.gov/docs/deeplearning/multinode_DL.html#horovod)); use it as a pattern.

- **Not documented by NIH**: torchrun rendezvous, `MASTER_ADDR`/`MASTER_PORT`, NCCL network variables (`NCCL_SOCKET_IFNAME`, `NCCL_IB_*`). The only NCCL setting shown is `NCCL_DEBUG=INFO`; start there when a job hangs.
- **Proxy**: the JAX page says gRPC-based distributed features "may require explicit control of the proxy settings on compute nodes" and recommends `export no_proxy="$SLURM_NODELIST"`. [generic] Slurm compresses multi-node lists (`cn[2349-2352]`), which proxy matching won't expand, so expand them and keep existing entries:
  ```bash
  export no_proxy="$no_proxy,$(scontrol show hostnames "$SLURM_NODELIST" | paste -sd, -)"
  ```

## Walltime, checkpoints, and pipelines

- Most NIH DL examples omit `--time`, so they get the gpu partition default (2 h in `batchlim`'s example). Always set it; partition maxima via `batchlim` (JOBS.md).
- NIH's DL pages are silent on checkpointing. Save to `/data` every N minutes or epochs and resume from the newest checkpoint at start. Run long training as a chain of shorter jobs, as NIH's multinode policy recommends for restartable codes: the user submits the chain with `--dependency=afterany:JOBID` (JOBS.md), and each job exits early if training is done, e.g. `[ -e "$CKPT/DONE" ] && exit 0` at the top, with the training script touching `DONE` when it finishes [generic].
- **Split CPU and GPU phases.** NIH's AlphaFold3 guidance: "use CPU nodes for the creation of alignments ... and use GPU nodes only for generating models". Do the same for decompression, tokenization, and feature extraction:
  ```bash
  # on Biowulf (login node) — the user runs this
  jid=$(sbatch --cpus-per-task=16 --mem=64g --time=4:00:00 --gres=lscratch:200 prep.sh)
  sbatch --dependency=afterok:$jid --partition=gpu --gres=gpu:a100:1,lscratch:200 -c 16 --mem=48g --time=24:00:00 train.sh
  ```

## TensorBoard

- The training script must write TensorBoard summaries; point its log dir at `/data` so the logs outlive the job.
- TensorBoard needs no GPU. NIH runs it in the GPU session after training; a small CPU session started with `--tunnel` also works and frees the GPU [inference]. It has no login, so other users on the login node can reach it while the tunnel is up (TUNNELING.md).
  ```bash
  # on the compute node (in a session started with --tunnel)
  module load python/3.12           # NIH's page used python/3.10
  tensorboard --logdir=/data/$USER/myproject/runs --port=$PORT1 --host=localhost
  ```
- Running it in the background, the user's local tunnel command, and port clashes: TUNNELING.md.

## Ollama

Local LLM serving. The module is in "early user testing phase - not all functionality is guaranteed to work"; problems go to staff (the user emails).

```bash
# on the compute node (GPU session), or as the body of a batch script
module load ollama
cd /data/$USER                        # the page sources $SLURM_JOB_ID/ollama.sh relative to this directory
ollama_start                          # prints "Running ollama on localhost:NNNNN"
sleep 2; source $SLURM_JOB_ID/ollama.sh   # sets OLLAMA_HOST
ollama pull gemma3:1b
ollama run gemma3:1b "what is long read sequencing" > response.txt
ollama_stop
```

- The page's request: `--gres=gpu:1,lscratch:10 --constraint="gpuv100|gpuv100x|gpua100" -c 8 --mem=10g`. Batch adds `--partition=gpu`; the interactive sample adds `--tunnel` without explaining it.
- Models live in `/data/$USER/ollama`: the module sets `OLLAMA_MODELS` because `~/.ollama` fills home. To change it, `export OLLAMA_MODELS=/data/$USER/...` after `module load ollama` and before `ollama_start`.
- The model must fit the job's total VRAM, which `--mem` doesn't change. 4-bit quantization cuts memory to about 25% and is "highly recommended". The page's table (as of Sept 2026) predates L40 (48 GB) and H200 (141 GB):

| Model size | VRAM FP16 | VRAM 4-bit | Page's GPU types |
|---|---|---|---|
| 1–3B | 4–6 GB | ~2 GB | P100, V100, V100x, A100 |
| 7–8B | 14–16 GB | ~6–8 GB | P100, V100, V100x, A100 |
| 13–14B | 26–28 GB | ~12–16 GB | V100x, A100 |
| 70B+ | 140 GB+ | ~35–40 GB | A100 (4-bit) |

- Use the server from inside the job (CLI, or the HTTP API at `$OLLAMA_HOST`); reaching it from the user's computer is undocumented. Run `ollama_stop`, and end the session when done.
- What data may go to a model is the user's decision; the page points to the [NIH AI Hub](https://nih.sharepoint.com/sites/NIH-ai) for AI-tool policy.

## Stale advice on the official pages

- `--gres=gpu:k80:N` (most deep_learning.html sections and most multinode_DL.html examples) → K80s were removed 24 Apr–1 May 2026; staff say such jobs "should run unmodified on P100 GPUs" (`gpu:p100:N`). For new work choose by VRAM. This file's examples are modernized.
- `module load python/3.7` (PyTorch, Keras-R) and `python/2.7` (Caffe2) → retired June 2023; use `python/3.12`.
- The TF and Keras batch scripts load only `cuDNN/8.9.2/CUDA-12 CUDA/12.1` → add `python/3.12`, or the job runs whatever `python` is first on PATH.
- The Lightning example's `pip install --user pytorch-lightning` on `python/3.8` → ignored or refused on python/3.11+ (`PYTHONNOUSERSITE=1`); use a conda env.
- Old toolchains: `CUDA/10.x` and `cuDNN/7.6.5/…` (MXNet, Keras-R, Knet), `cuDNN/8.2.1/CUDA-11.3` (Flux, JAX), Horovod's `openmpi/4.0.1/…` modules and TF 1.14 container, MXNet's hand-installed Miniconda (now `mamba_install`, CONDA.md) → check `module avail cuDNN`, `module avail CUDA`, `module avail openmpi/`. The Flux section loads `julialang/1.9.2`, but its transcript and batch script use 1.5.0.
- The DL pages' GPU lists stop at A100 and never mention L40, H200, or `gpuh200` → see Choosing and requesting GPUs.
- The BERT example requests `gpu:p100:2` but shows no multi-GPU setup → request one GPU unless the code uses both.
- The TensorBoard page trains with a TF1-era `mnist_with_summaries.py` from a 2019 clone → any script that writes summaries works.
- Ollama page: `export OLLAMA_MODELS = "your_dir1:your_dir2";` fails in bash ("not a valid identifier"; `=` takes no spaces) and leaves the default in place; its sample constraint omits P100, although its own table rates P100 for models up to 8B.
- JAX page: Notes name the module `JAX`, the example loads `jax` (check with `module spider jax`). Horovod links point to github.com/uber/horovod, now github.com/horovod/horovod [generic].

## Going further

- https://hpc.nih.gov/docs/deep_learning.html — per-framework quickstarts (#tensorflow, #pytorch, #keras, #flux, #mxnet); mind the stale items above.
- https://hpc.nih.gov/docs/deeplearning/multinode_DL.html — MirroredStrategy (#tensorflow), benchmarks (#benchmarks), DataParallel (#pytorch), Horovod (#horovod), Lightning (#lightning).
- https://hpc.nih.gov/docs/deeplearning/tensorboard.html — TensorBoard in a tunneled session (#init, #conn).
- https://hpc.nih.gov/docs/deeplearning/BERT_example.html — end-to-end fine-tuning walkthrough (conda env, output on lscratch, copy back); TF 1.15-era.
- https://hpc.nih.gov/apps/ollama.html — Ollama; https://hpc.nih.gov/apps/JAX.html — JAX module; https://hpc.nih.gov/apps/#deeplearning — packaged DL applications.
- https://hpc.nih.gov/docs/userguide.html#gpu — allocating GPUs and `nvidia-smi`; https://hpc.nih.gov/docs/userguide.html#local — lscratch and `TMPDIR`.
- https://hpc.nih.gov/nih/about/announcements.php?1223 — L40/H200 arrival and `gpuh200` limits (newer announcements may change them).
- https://hpc.nih.gov/apps/apptainer.html#gpu — GPU containers (`--nv`); https://hpc.nih.gov/development/cuDNN.html — cuDNN modules.
- https://hpc.nih.gov/training/deep_learning_by_example.html — NIH's Keras course (slides and videos).
- Live: `freen | grep -E 'Partition|----|gpu'`, `batchlim`, `module avail cuDNN`, `module spider jax`, `nvidia-smi`, `dashboard_cli` (no arguments prints help).
