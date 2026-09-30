Running Python on Biowulf: which interpreter to use, what the `python/3.X` modules contain, installing packages without shadowing them, sizing processes and threads to the allocation, a correct multiprocessing template, Ray, headless plotting, batch and swarm use, and Spyder, rpy2 and mpi4py. Creating your own conda env: CONDA.md. Jupyter kernels: JUPYTER.md. PyTorch and TensorFlow on GPUs: DEEP-LEARNING.md. Swarm options: SWARM.md. Tunnels: TUNNELING.md.

Table of contents

- [Choose the interpreter](#choose-the-interpreter)
- [Installing packages](#installing-packages)
- [Processes and threads](#processes-and-threads)
- [Multiprocessing template](#multiprocessing-template)
- [Ray](#ray)
- [Headless plotting](#headless-plotting)
- [Batch jobs and swarms](#batch-jobs-and-swarms)
- [Spyder, rpy2, mpi4py](#spyder-rpy2-mpi4py)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Choose the interpreter

| Interpreter | Use for | Notes |
|---|---|---|
| `module load python/3.X` | development; work where exact package versions don't matter | conda envs updated regularly: numpy, scipy, scikit-learn, numba, pandas, PyTorch, TensorFlow |
| your own conda env in `/data` | reproducibility, pinned versions, packages the modules lack | setup: CONDA.md |
| `/usr/bin/python3` | almost nothing | the OS Python 3.6, few packages |

- Modules (Sept 2026): `python/3.8` to `python/3.12`. The changelog made `python/3.10` the default in Jun 2023 and records no later change. Check with `module -t avail python` and `module -d avail python` (defaults only), and pin the version in every script.
- 3.11+ modules carry newer PyTorch, TensorFlow and CUDA packages, have no `conda` command, and set `PYTHONNOUSERSITE=1` (next section). For `conda activate`, use the user's own Miniforge (CONDA.md).
- Python 2.7 exists only in user envs.
- numpy and scipy in the modules link Intel MKL, so some operations (e.g. SVD) start threads on their own ([Processes and threads](#processes-and-threads)).
- There is no package table (the page's `#packages` link is dead): run `python -m pip list` after loading the module.
- PATH shadowing runs both ways: the python modules carry CLI tools such as `samtools`, and some app modules put their own Python on PATH (load order and fixes: MODULES.md). After loading, check `which python samtools`.

## Installing packages

- Anything the module lacks goes into an own conda env in `/data` (CONDA.md, which also covers pip inside an env).
- `pip install --user` writes to `~/.local/lib/pythonX.Y/site-packages`, in `/home`:
  - On 3.11+ modules, `PYTHONNOUSERSITE=1` hides that directory: pip ≥ 25.3 refuses `--user` ("User site-packages are disabled for this Python"); older pip "succeeds", then the import fails or finds the module's version. Unsetting the variable restores the old behavior; ask the user first and propose a conda env instead.
  - Elsewhere (3.8–3.10 modules, and own envs with the same Python version) they override the installed packages and cause hard-to-diagnose breakage. If an error disappears under `python -s` (skips user site-packages), a stale home-directory package is the cause: list them with `python -m pip list --user` and ask the user before removing any.
- `~/.cache/pip` counts against the 16 GB `/home` quota; clearing or relocating caches: STORAGE.md.

## Processes and threads

Read the allocation with the page's idiom; 2 is the minimum allocation and the value to assume when the job was not given `--cpus-per-task`:

```python
ncpus = int(os.environ.get("SLURM_CPUS_PER_TASK", "2"))
```

The page demonstrates `multiprocessing.cpu_count()` returning 56 inside a 2-CPU session. Hand `ncpus` to everything that sizes itself:

- Process pools: `Pool(ncpus)`, `ProcessPoolExecutor(max_workers=ncpus)`.
- Nested parallelism: an `XGBClassifier` inside `RandomizedSearchCV(..., n_jobs=-1)` can run N processes × N threads. Give each level `n_jobs` so the product is `ncpus`, e.g. `RandomizedSearchCV(XGBClassifier(n_jobs=2), params, n_jobs=ncpus // 2)`.
- Implicit threads (MKL, OpenBLAS, OpenMP): the modules pin `OMP_NUM_THREADS=1`. To use MKL threads, divide the allocation among the processes, e.g. 4 worker processes on 16 CPUs → 4 threads each:

  ```bash
  export OMP_NUM_THREADS=$(( ${SLURM_CPUS_PER_TASK:-2} / 4 ))   # 4 = worker processes; below 4 CPUs this gives 0: use 1
  ```

  Set thread variables before Python starts, or at least before the first `import numpy`: the libraries read them once, at load.
- Ray: `ray.init(num_cpus=ncpus, ...)` ([Ray](#ray)).

Symptoms and traps:

- Over-threading slows your own job: nodes confine threads to the allocated cores, so the job runs "much slower than normal" while the node's load may look fine ([swarm#details](https://hpc.nih.gov/apps/swarm.html#details)).
- A pool worker killed for exceeding memory leaves `multiprocessing.Pool` waiting until the walltime runs out. Allocate memory for every worker and test small first. `concurrent.futures.ProcessPoolExecutor` raises `BrokenProcessPool` instead of hanging (Python behavior, not in the NIH docs).
- Benchmark before scaling up: the page's cautionary case allocated 56 CPUs to code whose efficiency fell below 50% at 24. Right-sizing from past runs: UTILITIES.md.

## Multiprocessing template

The page's template with its missing `import sys` added (its "set up 50 tasks" comment also contradicted the 100 tasks it creates). Workers ignore SIGINT, so Ctrl-C (or `scancel`, per the page) stops the script cleanly.

```python
#!/usr/bin/env python
import os
import signal
import sys
from multiprocessing import Pool

def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def worker(i):
    return i * i

if __name__ == "__main__":
    nproc = int(os.environ.get("SLURM_CPUS_PER_TASK", "2"))  # allocated CPUs, or 2 outside Slurm
    print("Running on %d CPUs" % nproc)
    tasks = range(0, 100)
    p = Pool(nproc, init_worker)
    try:
        results = p.map(worker, tasks)
    except (KeyboardInterrupt, SystemExit):
        p.terminate()
        p.join()
        sys.exit(1)
    else:
        p.close()
        p.join()
        print("\n".join("%d * %d = %d" % (a, a, b) for a, b in zip(tasks, results)))
```

## Ray

- Ray tries to use every CPU, GPU and all memory on the node, whatever was allocated. In a single-node job, give `ray.init` the allocation: `ray.init(num_cpus=ncpus, num_gpus=<GPUs requested>)`, plus a memory cap below `--mem` (e.g. `object_store_memory=`).
- A multinode Ray cluster is a multinode job with one task per node (the staff template's author could not get more than one per node to work). If the nodes are allocated exclusively, request all of their resources. Start from the template:

```bash
# on the compute node: fetch and adapt the template
git clone https://github.com/NIH-HPC/biowulf_ray.git && cd biowulf_ray   # edit submit-ray
# the user, on the login node, from that directory:
sbatch submit-ray
```

Its README sizes workers with `--cpus-per-task` and `--gpus-per-task` and sends real multinode runs to the multinode partition (the demo fits `quick`); partition and GPU request rules: JOBS.md.

## Headless plotting

Without a display, matplotlib fails with `Could not connect to any X display`. Switch to a non-interactive backend, narrowest scope first:

- In code, before importing pyplot: `import matplotlib; matplotlib.use("agg")`.
- In the job script or your shell: `export MPLBACKEND=agg`. The page also suggests `~/.bashrc`; that edit is the user's call.
- A `matplotlibrc` containing `backend: agg`: in the working directory it affects runs started there; `~/.config/matplotlib/matplotlibrc` affects all the user's jobs (ask first).

## Batch jobs and swarms

python.html has no batch example. This pattern is assembled from the facts above:

```bash
#!/bin/bash
set -e
module load python/3.12                  # pinned; or activate an own env (CONDA.md)
export TMPDIR=/lscratch/$SLURM_JOB_ID    # temp files on lscratch (JOBS.md)
python /data/$USER/proj/run.py           # sizes pools and n_jobs from SLURM_CPUS_PER_TASK
```

Give the user: `sbatch --cpus-per-task=8 --mem=16g --gres=lscratch:10 --time=4:00:00 job.sh`.

- Swarm: load Python in each subjob with `--module`, e.g. `swarm -f run.swarm -g 8 -t 4 --time=2:00:00 --module python/3.12`, which the user runs (options: SWARM.md).
- Each Python start scans many paths on the shared filesystem, so thousands of short Python processes strain it, worst in large swarms whose lines each run several short scripts. Make each process do more work (loop over a batch of inputs per line); bundling lines (SWARM.md) also cuts how many start at once.
- An own conda env in batch or swarm: CONDA.md.

## Spyder, rpy2, mpi4py

**Spyder remote kernel.** The local steps are the user's.

1. The user starts a session with five tunnels, `sinteractive -TTTTT --mem=12g --cpus-per-task=2`, and runs the printed local `ssh -L` command (TUNNELING.md).
2. On the node: `module load python/3.10; spyder_kernel start` (or run it from an own env with the Spyder kernel installed). It writes the connection file `~/kernel-NNNNNN.json`.
3. The user loads that file in local Spyder's remote-kernel dialog, copied locally or read through hpcdrive (ACCESS.md). Without local tunnels, they can enter their login credentials in that dialog instead. Once connected, confirm the kernel runs on a compute node.
4. `spyder_kernel status` checks it; when done, `spyder_kernel stop` and delete the kernel file.

**rpy2** needs the separate `rpy2` module to find the matching R: `module load python/3.X rpy2` (check pairings with `module spider rpy2`). In Jupyter: JUPYTER.md.

**mpi4py.** The only live documentation is the Jan 2022 changelog: mpi4py "migrated to a different MPI library. Use `mpiexec` instead of srun". The page's how-to is commented out; it loaded `mpi4py` and `python/3.9` and ran `mpiexec ./test.py` in a batch job with `--ntasks=8 --ntasks-per-core=1 --partition=multinode`. Treat it as unverified (`module spider mpi4py`); multinode submission rules: JOBS.md.

## Stale advice on the official pages

- python.html intro: `/usr/local/bin/python` links to Python 2.7 → per the Jun 2023 changelog it is Python 3.9, and 2.7 is provided in no form.
- `python.html#packages` (the package table the intro links) doesn't exist → `python -m pip list`. Its conda advice ("mambaforge", `#envs`) is stale too: CONDA.md.
- The rpy2 example loads `python/3.7`, retired in Jun 2023 → a current module.
- The multiprocessing template calls `sys.exit` without `import sys` → fixed above.
- The commented-out mpi4py how-to offers `srun --mpi=pmi2`, contradicting the changelog → `mpiexec`.

## Going further

- https://hpc.nih.gov/apps/python.html — modules and changelog (`#changes`), pitfalls (`#gotcha`), module envs and MKL threading (`#generalenvs`), `#multiprocessing`, `#rpy2`, `#ray`, `#spyder`.
- https://hpc.nih.gov/docs/diy_installation/conda.html — own envs (CONDA.md).
- https://github.com/NIH-HPC/biowulf_ray — the multinode Ray template.
- Live: `module -t avail python`, `module -d avail python`, `python -m pip list`, `module spider rpy2`, `module spider mpi4py`, `spyder_kernel status`.
