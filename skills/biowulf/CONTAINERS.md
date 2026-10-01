Singularity and Apptainer on Biowulf: which module to use, where caches and temp files go, pulling Docker images, binding cluster paths, what can and can't be built on the cluster, GPUs, and containers in batch jobs and swarms. Requesting GPUs and lscratch is covered in JOBS.md, swarm options in SWARM.md, Snakemake and Nextflow container settings in WORKFLOWS.md, and choosing a deep-learning framework or image in DEEP-LEARNING.md.

Table of contents

- [Session setup](#session-setup)
- [Pull and run](#pull-and-run)
- [Binding host paths](#binding-host-paths)
- [Building images](#building-images)
- [GPUs](#gpus)
- [Batch jobs and swarms](#batch-jobs-and-swarms)
- [MPI in containers](#mpi-in-containers)
- [Staff-containerized apps](#staff-containerized-apps)
- [Troubleshooting](#troubleshooting)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Session setup

"Singularity cannot be run on the Biowulf login node" ([#int](https://hpc.nih.gov/apps/singularity.html#int)). Do all container work (pulls, builds, conversions, test runs) inside the user's interactive session, and give jobs the same setup. Builds, and pulls or runs from Docker sources, unpack the image in temp space, which must hold "the entire container image, uncompressed" (Sylabs). That temp space defaults to `/tmp`, which is small and shared. So the session needs lscratch larger than the unpacked image; for memory, the staff pull and build examples use 4–10 GB. If the session has no lscratch, ask the user to start one with `--gres=lscratch:N` (JOBS.md).

```bash
# on the compute node, in every shell that uses containers
module load singularity                                # never pin a version: staff keep only one
export SINGULARITY_CACHEDIR=/data/$USER/.singularity   # the default, ~/.singularity/cache, fills /home
[ -d "/lscratch/${SLURM_JOB_ID:-none}" ] && export SINGULARITY_TMPDIR=/lscratch/$SLURM_JOB_ID \
  || echo "no lscratch: builds and conversions will use the small, shared /tmp"
. /usr/local/current/singularity/app_conf/sing_binds  # staff-maintained bind list
echo "$SINGULARITY_BINDPATH"                           # what containers will see
mkdir -p /data/$USER/containers                        # keep .sif files on /data, never /home or lscratch
```

- Staff suggest adding the `SINGULARITY_CACHEDIR` export to `~/.bashrc` for users who run containers often ([#notes](https://hpc.nih.gov/apps/singularity.html#notes)). Offer to do this, and edit the file only with the user's OK. Keep the cache per-user and out of group directories: Sylabs says caches "cannot be shared across users".
- Use the `singularity` module unless the project needs `apptainer`. Staff app modules such as pymc load `singularity`, its page is the more recent of the two, and it is the only module documented to build on Biowulf. `apptainer` is "the Linux Foundation variant of Singularity" and has the same subcommands (`apptainer exec …`). Its page says `$SINGULARITY_*` variables "are deprecated and will be removed", so use the `APPTAINER_*` names with it:

| Item | `singularity` | `apptainer` |
|---|---|---|
| cache | `SINGULARITY_CACHEDIR=/data/$USER/.singularity` | `APPTAINER_CACHEDIR=/data/$USER/.apptainer` |
| temp space | `SINGULARITY_TMPDIR` | `APPTAINER_TMPDIR` |
| bind list | `/usr/local/current/singularity/app_conf/sing_binds` | `/usr/local/current/apptainer/app_conf/sing_binds` |
| bind variable | `SINGULARITY_BINDPATH` | `APPTAINER_BINDPATH` (the apptainer page also says its sing_binds sets `SINGULARITY_BINDPATH`: `cat` the file) |
| builds from a definition file on Biowulf | yes (proot, automatic) | no (per its page) |

Versions (as of Sept 2026): singularity 4.3.7, apptainer 1.4.5. The `[+] Loading singularity …` banner shows the live version, and so does `module -r spider '^singularity$'`. The page transcripts show older versions.

## Pull and run

```bash
# on the compute node, after the setup block
singularity pull /data/$USER/containers/mytool.sif docker://quay.io/ORG/IMAGE:TAG
singularity exec /data/$USER/containers/mytool.sif mytool --version
```

- `singularity pull docker://ubuntu:latest` with no output name writes `ubuntu_latest.sif` to the current directory. `pull` refuses to overwrite an existing file, and so does `build` without a terminal (with one it asks). Use a new name, or add the long `--force` once the user agrees to replace the image (on `build`, `-f` means `--fakeroot`).
- Staff list these registries: Docker Hub, Quay.io, NVIDIA NGC (`docker://nvcr.io/nvidia/<image>:<tag>`), BioContainers, and the Sylabs Cloud Library (`library://…`). Pulls work on compute nodes through the proxy, and every staff example pulls there.
- Run commands with `exec IMAGE COMMAND`. `shell` is interactive, and `run` executes the image's ENTRYPOINT/CMD, often a shell or REPL (ubuntu's `/bin/bash`, python's `python3`) that hangs a non-interactive tool call; with neither, it prints the shell's variables, secrets included.
- `singularity exec docker://…` runs without a pull, but it still converts the image and fills the cache. Pull once and reuse the SIF. Pin a tag rather than `latest`, so reruns get the same image.
- Private registries: the Biowulf docs say nothing about them. Sylabs reads `SINGULARITY_DOCKER_USERNAME` and `SINGULARITY_DOCKER_PASSWORD`, or logs in interactively with `--docker-login`. The user runs that pull. Credentials never go into scripts, swarmfiles, or the chat.
- Biowulf has no Docker (`docker: command not found`), because Docker "provides root access to the host system". If the project has only a Dockerfile, translate it into a definition file (`Bootstrap: docker`, `From:` its base image, its `RUN` steps in `%post`) and build that as shown below. Sylabs' `singularity build --oci` from a Dockerfile is undocumented on Biowulf.
- Programs that drive singularity themselves need the same settings. For Nextflow and Snakemake, see WORKFLOWS.md. R's dyno needs a `/data` cache and a patched babelwhale that passes `http_proxy`/`https_proxy` ([R.html](https://hpc.nih.gov/apps/R.html)).

## Binding host paths

By default, only `$HOME`, `/tmp`, `/dev`, and a few other directories are bound. The container can't see `/data/$USER`, group directories, `/fdb`, or `/lscratch` unless they are bound ([#bind](https://hpc.nih.gov/apps/singularity.html#bind)).

- Source `sing_binds` in every shell and script that runs a container. Staff call this a Biowulf best practice because they update the file when shared filesystems change. Hand-written bind lists can miss symlink targets: `/data/$USER` resolves into `/vf/...`, and that target must be bound too. Keep writing `/data/...` paths.
- The file's contents aren't documented. Check with `echo "$SINGULARITY_BINDPATH"` (or `cat` the file) and add anything missing with `-B`, e.g. `-B /data/GROUPNAME`. `-B` adds to `$SINGULARITY_BINDPATH`; it doesn't replace it.
- Remap a path with `src:dest`. For example, `-B /lscratch/$SLURM_JOB_ID:/tmp` puts the container's `/tmp` on the job's lscratch. Every bind source must exist, so use this only when lscratch is allocated.
- Never bind `/scratch`. It is disabled on compute nodes, and the bind fails with an error.

## Building images

Work down this list and stop at the first option that works:

1. **An existing image.** Run `module spider NAME` first, because staff may already have containerized the app (see [Staff-containerized apps](#staff-containerized-apps)). If not, pull an image from a registry.
2. **A proot build in the session.** Only the `singularity` module is documented to do this, and it happens automatically ("There is nothing special you have to do"). It suits definition files that start from an existing image and add software with package managers.
3. **The Sylabs remote builder (`--remote`).** Use it for builds proot can't handle. The user sets up the token first.
4. **An off-cluster build with root.** The user builds on their own Linux machine, on a VM (give it at least 2 GB of memory), or on a cloud instance, e.g. `sudo singularity build mytool.sif mytool.def`. The user copies the SIF to `/data/$USER/containers` (TRANSFER.md), and you test it in the session.

Avoid three things. Don't use `apptainer build` for a definition file: its page says "containers can't be built on the NIH HPC systems". Don't rely on `--fakeroot`: the proot message suggests it, but Biowulf documents it only for the user's own recent Linux system. Never use `sudo` on the cluster.

**proot builds** ([#create](https://hpc.nih.gov/apps/singularity.html#create); [Sylabs limits](https://docs.sylabs.io/guides/latest/user-guide/build_a_container.html#unprivileged-proot-builds)):

```bash
# on the compute node, after the setup block
singularity build /data/$USER/containers/mytool.sif mytool.def
# expected: INFO:    Using proot to build unprivileged. Not all builds are supported. If build fails, use --remote or --fakeroot.
```

- Supported bootstraps are `docker`/`oci`, `library`, `oras`, and `localimage`. `yum` (and its alias `dnf`), `debootstrap`, `arch`, and `zypper` don't work.
- `%pre` and `%setup` sections aren't supported. `%post` runs as an emulated root; `%test` runs as the user.
- proot builds are slower (ptrace), and privileged operations in `%post` can fail. Sylabs suggests `--remote` for definition files that compile large, complex software from source.
- Staff examples built this way in `sinteractive --mem=8G` or `--mem=4G`: `From: tensorflow/tensorflow:latest` with an `%environment` section, and `From: continuumio/miniconda3:latest` with `apt-get` and `conda install -c conda-forge -c bioconda …` in `%post` ([#batch](https://hpc.nih.gov/apps/singularity.html#batch), [#docker](https://hpc.nih.gov/apps/singularity.html#docker)).

**Remote builds:**

1. The user's steps: log in at https://cloud.sylabs.io/auth/tokens and generate a token. Then, in a shell on a compute node (such as the session's terminal before they start you), run `module load singularity && singularity remote login SylabsCloud` and paste the token at the prompt. The token is stored unencrypted under `~/.singularity/` (`remote.yaml`); never read or print that file.
2. Your step: `singularity build --remote /data/$USER/containers/mytool.sif mytool.def`. The build runs "as the root user, inside a secure single-use virtual machine" at Sylabs, and the SIF is downloaded afterwards. Staff describe it as suited to "small and medium sized containers"; no limits are stated. `--remote` refuses `Bootstrap: localimage`, `-B`, `--nv`, and `--build-arg` (Sylabs). The definition file goes to Sylabs, so keep credentials and controlled-access data out of it.

For starting points, see the staff repo [NIH-HPC/singularity-def-files](https://github.com/NIH-HPC/singularity-def-files). Its files "are not guaranteed to reproduce the same container, or even to produce any container at all". Staff "do not have the resources to manage containers for individual users", so users build and maintain their own images.

## GPUs

- Add `--nv` to `exec`, `run`, or `shell`. Images need no NVIDIA drivers of their own, and the old gpu4singularity script is deprecated ([#gpu](https://hpc.nih.gov/apps/singularity.html#gpu)).
- The session or job must hold a GPU. Request syntax is in JOBS.md; GPU types are in HARDWARE.md.
- The host driver must support the image's CUDA version (a general CUDA rule; NIH's pages don't cover it). `nvidia-smi` on the node shows the highest CUDA version the driver supports. If `nvidia-smi` works inside the container but the framework sees no GPU, pick an image tag built for an older CUDA.

```bash
# on a GPU compute node
singularity pull /data/$USER/containers/tf-gpu.sif docker://tensorflow/tensorflow:latest-gpu
singularity exec --nv /data/$USER/containers/tf-gpu.sif nvidia-smi       # GPU visible inside?
singularity exec --nv /data/$USER/containers/tf-gpu.sif python train.py
```

## Batch jobs and swarms

The user submits jobs from their own login shell, which has none of your session's exports. So every job script and every swarm line needs both of these itself:

1. `module load singularity` (in a swarm, `--module singularity` also does this one); without it, `singularity: command not found`.
2. `. /usr/local/current/singularity/app_conf/sing_binds`, which no swarm option does for you; without it, the container can't see `/data` or `/fdb`.

The wrapper script below does both, as does the no-wrapper swarm line after it. Pull the image once in the session, and point jobs at the SIF by its `/data` path. Never put `docker://` URIs in subjobs that run in parallel: subjobs that start together each convert the image, and Sylabs warns against parallel runs from remote URLs unless the cache filesystem "supports atomic rename" (undocumented for `/data`).

```bash
#!/bin/bash
# /data/$USER/project/run_tool.sh SAMPLE: you write it, the user submits it
set -e
module load singularity
. /usr/local/current/singularity/app_conf/sing_binds
cd /data/$USER/project
singularity exec -B /lscratch/$SLURM_JOB_ID:/tmp /data/$USER/containers/mytool.sif \
    mytool --threads "${SLURM_CPUS_PER_TASK:-2}" "in/$1.bam" "out/$1"
```

Give the user one of these commands. Sizing is covered in JOBS.md and SWARM.md; dry-run the swarm first with `swarm --devel`.

```bash
# on Biowulf (login node), run by the user
sbatch --cpus-per-task=8 --mem=16g --time=4:00:00 --gres=lscratch:20 /data/$USER/project/run_tool.sh s01
swarm -g 16 -t 8 --time=4:00:00 --gres=lscratch:20 tool.swarm   # lines: bash /data/$USER/project/run_tool.sh s01
# or with no wrapper, every line loads singularity and sources the bind list itself:
swarm -g 16 -t 8 --time=4:00:00 --gres=lscratch:20 tool.swarm
#   line: module load singularity && . /usr/local/current/singularity/app_conf/sing_binds && singularity exec /data/$USER/containers/mytool.sif mytool --threads $SLURM_CPUS_PER_TASK in/s01.bam out/s01
```

- The `-B …:/tmp` remap needs the lscratch request. Drop both together. For a GPU job, add `--nv` to the command and a GPU to the request.
- Host variables such as `OMP_NUM_THREADS` pass into the container unless you use `--cleanenv`, but an image's own Dockerfile `ENV` values win over host variables of the same name; override those with `--env OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK` (Sylabs). Size threads from `$SLURM_CPUS_PER_TASK` just as you would outside a container.
- The staff swarm example ([apptainer#swarm](https://hpc.nih.gov/apps/apptainer.html#swarm)) sources `sing_binds` at the login prompt before `swarm` ("This variable will propagate to your jobs") and adds `--module apptainer`. That approach depends on the state of the user's shell, so prefer the self-contained script.

## MPI in containers

The container pages don't cover MPI. NIH's only example is multi-node Horovod ([multinode_DL#horovod](https://hpc.nih.gov/docs/deeplearning/multinode_DL.html#horovod); DEEP-LEARNING.md). It uses the hybrid model: the host's `mpirun -np $SLURM_NTASKS` starts `singularity run --nv IMAGE.sif python …` once per rank. For the host modules, the page advises: "Ideally openmpi and cuda need to match with the container (as much as possible)". The example's `openmpi/4.0.1` modules are deprecated, so pick a current match from `module avail openmpi/`. OpenMPI guidance and launch lines are in DEVELOPMENT.md; multi-node requests are in JOBS.md.

## Staff-containerized apps

Many modules are containers underneath. Staff typically install each app as `appname/ver/bin/CMD -> ../libexec/wrapper.sh`, and the wrapper runs `CMD` inside `libexec/app.sif`. Use these apps like native ones (`module load fmriprep`, then `fmriprep …`). A module may load singularity itself (`module load pymc/3` prints `[+] Loading singularity on cn3344`), and some commands are renamed (`python-pymc`). The usual rules still apply: run them on compute nodes only, with enough memory (fmriprep was one of the containers that hung nodes when it ran out of memory). If no module exists, the user can email staff@hpc.nih.gov to request an install.

To make your own image's commands callable like installed tools, use the staff pattern ([#bind-stationary](https://hpc.nih.gov/apps/singularity.html#bind-stationary)). Put the image and this wrapper in `/data/$USER/opt/hts/libexec/` as `hts.sif` and `wrap` (executable), then symlink `bin/samtools` and `bin/bcftools` to `../libexec/wrap`:

```bash
#!/bin/bash
. /usr/local/current/singularity/app_conf/sing_binds
selfdir="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"
instdir="$(dirname ${selfdir})"
cmd="$(basename $0)"
singularity exec -B "${instdir}" "${selfdir}/hts.sif" "$cmd" "$@"
```

Callers need `/data/$USER/opt/hts/bin` on `PATH` (in the job script, or in a personal modulefile: MODULES.md). The wrapper doesn't load singularity, so callers also need `module load singularity` first. Staff use `$HOME/opt`; `/data` keeps the images out of the home quota.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/home` full; `~/.singularity/cache` is large | Set `SINGULARITY_CACHEDIR` (setup block). The old cache stays in `/home`, and Sylabs says its contents are safe to delete: with the user's OK, `rm -rf ~/.singularity/cache`. For other causes, see STORAGE.md. |
| `No space left on device` during a pull or build | Temp space fell back to `/tmp`. Set `SINGULARITY_TMPDIR` to lscratch, or ask the user for a session with more lscratch. |
| `singularity cache clean` hangs, or fails with `could not prompt user` | It wants a confirmation, even with `--days`. Preview with `--dry-run`, then run it with `--force` once the user agrees (`--days 30` keeps recent entries). |
| `FATAL: container creation failed: mount /gs6->/gs6 error: while mounting /gs6: mount source /gs6 doesn't exist.` | A bind source is missing; here an old bind list or config names a retired filesystem. Drop it and source `sing_binds`. A `/lscratch/$SLURM_JOB_ID` bind in a job without lscratch should fail the same way. |
| Error when binding `/scratch` | `/scratch` is disabled on compute nodes. Use lscratch or `/data`. |
| A `/data` or `/fdb` path is missing inside the container | The path isn't bound, or its `/vf` target isn't. Source `sing_binds`, check `$SINGULARITY_BINDPATH`, and add `-B`. |
| `module load singularity/<version>` fails | Only one version is kept. Load the module without a version. |
| `singularity: command not found` in a job or wrapper | The script never ran `module load singularity`. |
| proot build fails | Check for `%pre`/`%setup` sections, a `yum`/`dnf`/`debootstrap` bootstrap, or privileged steps in `%post`. `--remote, --fakeroot, or the proot command are required` means proot isn't on PATH: `module load singularity` first. Otherwise use `--remote` or an off-cluster build. |
| Errors mentioning `github.com/etcd-io/bbolt` (Singularity 3.x) | The layer database is corrupted (after a filesystem hiccup or a full disk). With the user's OK, run `rm ~/.local/share/containers/cache/blob-info-cache-v1.boltdb`; the file stays in `/home` whatever the cache setting. Singularity 4 keeps this cache as `blob-info-cache-v1.sqlite`. |
| No GPU inside the container | `--nv` is missing, or the allocation has no GPU. |
| A `.sif` is gone after the session ended | It was on lscratch, which is deleted when the job ends. Keep images in `/data/$USER`. |
| The job exceeds its memory, then processes hang in D state and the node slows down | This is the squashFS OOM bug, "generally not a problem" since the 2023 OS upgrade ([#oomkills](https://hpc.nih.gov/apps/singularity.html#oomkills)). Request more memory. The apptainer page's workaround is `apptainer build --sandbox NAME NAME.sif` on a compute node, then running the sandbox directory instead of the SIF. If it recurs, the user emails staff@hpc.nih.gov (the singularity page's ext3 conversion needs root). |
| `WARNING: Bind file source does not exist on host: /etc/resolv.conf`, `WARNING: integrity: signature not found for object group 1`, `WARNING: Skipping container verification`, `warn rootless{dev/…} creating empty file in place of device`, `INFO:    Using cached SIF image` | These appear in staff transcripts with no comment. Ignore them. |

## Stale advice on the official pages

- apptainer.html#create says "containers can't be built on the NIH HPC systems". The singularity page (updated Sept 2025 or later) documents proot builds, so build with the `singularity` module.
- singularity.html#bind-stationary builds with `sudo singularity build hts.simg Singularity` and mentions "GPFS mounts". That text predates proot. Its definition (a docker bootstrap plus `apt-get`) fits proot's limits, so try building it in a session, from a current base image (`debian:9-slim` is end-of-life [generic]). `/data` now lives on VAST (`/vf`); source `sing_binds`, which staff update as filesystems change, and check `$SINGULARITY_BINDPATH`.
- apptainer.html#swarm runs `apptainer exec docker://python …` on every line. Instead, pull once and put the SIF path in each line.
- The `~/.bashrc` snippet on singularity.html#bind binds lscratch whenever `[ -d /lscratch ]` is true. The per-job directory comes with an lscratch allocation, so test `[ -d /lscratch/${SLURM_JOB_ID:-none} ]` instead; that keeps jobs without lscratch from binding a missing directory.
- The transcripts print singularity 4.2.2 and apptainer 1.0.1. Current versions are listed under Session setup; never pin a version.
- The apptainer page links `--remote` and `--fakeroot` to the Sylabs 3.4 docs (the singularity page does so for `--fakeroot`), and documents `apptainer remote login SylabsCloud` → Apptainer no longer ships a SylabsCloud remote and doesn't support `build --remote` (Apptainer docs). Use the singularity module and the Sylabs "latest" docs (4.5, newer than Biowulf's 4.3.7).
- The apptainer page presents the squashFS OOM hang as a current problem. The singularity page says it has been "generally not a problem" since 2023.
- The singularity page's example definitions (DIGITS, Keras, RStudio, Theano in NIH-HPC/singularity-examples) are what the apptainer page calls Legacy, tied to the Singularity Hub archive. Start from a registry image or the staff def-files repo instead.
- The apptainer page's install example builds `hts.sif`, but its tree and wrapper refer to `hts.simg`, and its wrapper drops `-B "${instdir}"`. Use the wrapper under Staff-containerized apps.

## Going further

- [Singularity page](https://hpc.nih.gov/apps/singularity.html): the cache and bind notes (`#notes`), building (`#create`, `#batch`), binds (`#bind`), faking an install (`#bind-stationary`), GPUs (`#gpu`), Docker images (`#docker`), and OOM hangs (`#oomkills`).
- [Apptainer page](https://hpc.nih.gov/apps/apptainer.html): the apptainer module, the registry list, the swarm example (`#swarm`), and the sandbox workaround (`#oomkills`).
- [Sylabs: build a container](https://docs.sylabs.io/guides/latest/user-guide/build_a_container.html): proot limits (`#unprivileged-proot-builds`), remote builds (`#remote-builds`), and Dockerfile builds (`#building-from-dockerfiles`).
- [Sylabs: build environment](https://docs.sylabs.io/guides/latest/user-guide/build_env.html): cache and temp folders (`#cache-folders`, `#temporary-folders`), cache cleaning, and registry credential variables (`#docker`).
- [Sylabs: bind paths](https://docs.sylabs.io/guides/latest/user-guide/bind_paths_and_mounts.html#user-defined-bind-paths) · [Sylabs: MPI](https://docs.sylabs.io/guides/latest/user-guide/mpi.html) · [Apptainer: GPU support](https://apptainer.org/docs/user/main/gpu.html) · [Apptainer: environment variables](https://apptainer.org/docs/user/main/appendix.html#apptainer-s-environment-variables).
- [NIH-HPC/singularity-def-files](https://github.com/NIH-HPC/singularity-def-files): the staff definition files and the wrapper layout. Staff class materials (2020): [Singularity-Tutorial](https://github.com/NIH-HPC/Singularity-Tutorial/tree/2020-03-10) and https://singularity-tutorial.github.io/.
- Live help: `singularity help <subcommand>`, `singularity cache list -v`, `module spider singularity`, `cat /usr/local/current/singularity/app_conf/sing_binds`.
