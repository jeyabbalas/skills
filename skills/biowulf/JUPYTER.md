Jupyter on Biowulf: the HPC OnDemand app (NIH's recommended route), module-named and custom-environment kernels, a Jupyter server inside your own interactive session, notebooks in VS Code, headless runs, and the known pitfalls. The tunnel itself (the user's `ssh -L` line, the handoff, reconnecting) is in TUNNELING.md; OnDemand login and sessions in ACCESS.md; creating and activating the conda env behind a kernel in CONDA.md; RStudio and Shiny in R.md.

Table of contents

- [Choose a route](#choose-a-route)
- [OnDemand Jupyter](#ondemand-jupyter)
- [Kernels](#kernels)
- [A kernel for your own environment](#a-kernel-for-your-own-environment)
- [Jupyter in your own session](#jupyter-in-your-own-session)
- [Running a notebook headless](#running-a-notebook-headless)
- [Pitfalls](#pitfalls)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Choose a route

| Route | When | Who starts it |
|---|---|---|
| [OnDemand Jupyter app](https://hpc.nih.gov/apps/jupyter.html#ondemand) | Default: NIH recommends it, and it needs no tunnel | the user, in a browser |
| Jupyter in your `--tunnel` session (the page's ["Legacy" tunnel method](https://hpc.nih.gov/apps/jupyter.html#general)) | The server should share your allocation, or you need to start, inspect, and restart it yourself | you; the user opens the tunnel |
| [VS Code](https://hpc.nih.gov/apps/vscode.html#jupyter) over Remote-SSH to the session's node | The user already works in local VS Code | the user |

- An OnDemand Jupyter job takes one of the user's interactive-job slots, from the same pool as your own session (JOBS.md).
- VS Code: install the Jupyter extension, open the notebook by its full path (`/data/$USER/x.ipynb`), then pick "Select Kernel" → "Python Environments". Remote-SSH setup: ACCESS.md.

## OnDemand Jupyter

The user fills in the [Jupyter form](https://hpcondemand.nih.gov/pun/sys/dashboard/batch_connect/sys/bc_nih_jupyter/session_contexts/new): resources, walltime, the interface (Jupyter Notebook, Jupyter Lab, or Matlab), and the startup "working directory" (like `cd` before launch). Your part:

- Install any custom kernel first. Kernels in home appear in OnDemand automatically.
- Suggest concrete values: CPUs and memory for the notebook's real work, a walltime, and a working directory under `/data/$USER` (advice: Jupyter's file browser can't go above its start directory).
- If you're working from that job's terminal, its server is already running; don't start another.

## Kernels

- Load `jupyter` without a `python` or `R` module ([pitfalls](https://hpc.nih.gov/apps/jupyter.html#pitfalls)). The kernels set up their own Python or R, and a `python` module loaded alongside breaks Jupyter.
- Pick a kernel named after a module (e.g. `python/3.10`, `R/4.3`) or a custom kernel. The default kernel is Jupyter's own minimal conda env, without the scientific stack.
- List kernels with `jupyter kernelspec list`. The page's listing also has `bash`, `sos`, and `jupyter_matlab_kernel` (MATLAB). Kernels are added and retired along with the modules, so check live.
- For R magics in Python kernels, `module load rpy2` *before* starting Jupyter, then run `%load_ext rpy2.ipython`.
- Version (as of Sept 2026): `jupyter` 5.7.2 per the [apps index](https://hpc.nih.gov/apps/). Check with `module -r spider '^jupyter$'`.

## A kernel for your own environment

NIH's [recommended way](https://hpc.nih.gov/apps/jupyter.html#custom): put a kernelspec for the env in home, where every Jupyter on the cluster finds it, OnDemand included. Installing Jupyter into the env and running that instead loses the module's extensions and "is not compatible with Open OnDemand".

```bash
# on the compute node (inside the job); creating and activating envs: CONDA.md
source ~/bin/myconda && conda activate myenv && conda install --dry-run ipykernel   # must only ADD packages; then rerun with -y (or pip install ipykernel)
/data/$USER/conda/envs/myenv/bin/python -m ipykernel install --user --name myenv --display-name "Python (myenv)"
module load jupyter && jupyter kernelspec list                                # confirm it's listed
```

- Run the install with the env's own python (full path above, or `python` in the activated env before loading `jupyter`). It writes to `~/.local/share/jupyter`. `--name` is the internal id; `--display-name` is what the UI shows.
- Advice: a kernelspec stores the env's absolute interpreter path, so re-run the install after moving or recreating the env. Remove a kernel with `jupyter kernelspec remove myenv`.
- For other languages, install that language's Jupyter kernel package the same way, or ask staff.
- Is a package missing from a module kernel? Add it to your own env and use that env's kernel. Advice: `pip install` from a module kernel lands in `~/.local` (why that breaks: PYTHON.md).

## Jupyter in your own session

The session must have been started with `--tunnel`. Check `echo $PORT1` (if it's unset, see TUNNELING.md).

```bash
# on the compute node (inside the job)
module load jupyter
unset XDG_RUNTIME_DIR                                      # NIH pitfall: a value inherited from the login node breaks Jupyter
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-2} OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-2} MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-2}   # kernels inherit these
cd /data/$USER/myproject                                   # the file browser's root
log=jupyter.$PORT1.log; : > "$log"; chmod 600 "$log"       # will hold the token
nohup jupyter lab --ip localhost --port "$PORT1" --no-browser \
  --ServerApp.port_retries=0 > "$log" 2>&1 < /dev/null &
echo $! > jupyter.$PORT1.pid
grep -m1 -o "http://localhost:$PORT1/lab?token=[0-9a-f]*" "$log"   # repeat until it prints
```

- NIH's flags: `--ip localhost` listens on localhost only, `--port $PORT1` uses the tunneled port, and `--no-browser` because no browser runs on the node. `jupyter notebook` takes the same flags, but its URL isn't under `/lab` (current Notebook prints `/tree?token=...`), so grep the log for `token=` instead.
- `--ServerApp.port_retries=0` (generic advice): without it, Jupyter silently moves to another port when `$PORT1` is busy, and the tunnel can't reach it there. With it, Jupyter exits with an error instead.
- Hand the user the `ssh -L` line and this URL, token included (TUNNELING.md). The token is needed on first connect.
- Stop the server with `kill "$(cat jupyter.$PORT1.pid)"` (interactively: Control-C twice). The user `exit`s the session when nothing else needs it.

## Running a notebook headless

You can't drive a notebook UI. To run a notebook yourself, execute it with the module's nbconvert (generic Jupyter usage, not an NIH recipe), writing to a new file rather than over the user's notebook:

```bash
# on the compute node (inside the job)
module load jupyter
jupyter nbconvert --to notebook --execute --ExecutePreprocessor.kernel_name=py3.10 \
  --output analysis.run.ipynb analysis.ipynb     # kernel id from `jupyter kernelspec list`
```

For long runs, put the same lines in a batch script for the user to submit (JOBS.md).

## Pitfalls

| Symptom | Fix |
|---|---|
| `Jupyter command jupyter-lab not found` | A python module is loaded too: `module purge; module load jupyter` |
| Expected packages are missing | You're on the minimal default kernel: switch to a module-named or custom kernel |
| `PermissionError: [Errno 13] Permission denied: '/run/user/xxxx'` | `unset XDG_RUNTIME_DIR` (tcsh: `unsetenv XDG_RUNTIME_DIR`); the value exported from the login node points to a directory missing on the compute node |
| `%load_ext rpy2.ipython` errors | `module load rpy2`, then restart Jupyter |
| `nbconvert failed: xelatex not found on PATH` | `module load tex` before starting the server |
| Your env's own Jupyter doesn't work in OnDemand | Install a kernelspec for the env instead |
| Browser: connection refused | The user's local `ssh -L` isn't running (TUNNELING.md) |
| The logged URL's port ≠ `$PORT1` | Jupyter moved off a busy `$PORT1`: stop it; if an earlier server of yours holds `$PORT1`, reuse or stop that one, else see TUNNELING.md (port in use). Restart with `--ServerApp.port_retries=0` |

## Stale advice on the official pages

- The example `jupyter kernelspec list` shows kernels under `envs/5.3.0` (py3.8–py3.10, ir42, ir43) → the module has moved on; list kernels live.
- The Lab example starts on `$PORT1` (33327) yet prints a URL on port 40792 → only a URL whose port equals the tunneled port works.
- The page calls running Jupyter on the login node "bad form" → never suggest it: heavy login-node processes get killed, and agents may not run there at all (SKILL.md).
- Example output with `/spin1/...` paths and NotebookApp extensions (`nb_conda`, `nbpresent`) is years old; ignore it.

## Going further

- https://hpc.nih.gov/apps/jupyter.html — pitfalls (#pitfalls), custom kernels (#custom), OnDemand (#ondemand), and the tunnel method (#general).
- https://hpc.nih.gov/apps/vscode.html#jupyter — notebooks in VS Code on a compute node.
- https://youtu.be/bgLJb1anNPA — NIH's video: a quick start and a full tunnel walkthrough (Windows client, "equally applicable to macOS or Linux").
- https://ipython.readthedocs.io/en/stable/install/kernel_install.html#kernels-for-different-environments — kernelspec install options.
- https://docs.jupyter.org/en/latest/install/kernels.html — kernels for other languages.
- Live: `jupyter kernelspec list`, `module help jupyter`, `module -r spider '^jupyter$'`, `jupyter lab --help-all`.
