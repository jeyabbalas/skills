Apptainer and Singularity on FRCE: which runtime to use, pulling Docker and other images, where caches and temporary files go, bind paths, GPUs, building images without root, containers in batch jobs, and shared image collections. You pull, build, and test inside the user's allocation; jobs that run containers are the user's to submit (ground rules in SKILL.md). Docker itself is not available. Internet access for pulls: TRANSFER.md (Downloads on the cluster). GPU requests: JOBS.md (GPUs). Workflow managers' container settings: WORKFLOWS.md. Framework images for deep learning: DEEP-LEARNING.md.

Table of contents

- [Apptainer on FRCE](#apptainer-on-frce)
- [Pulling images](#pulling-images)
- [Running containers](#running-containers)
- [GPUs in containers](#gpus-in-containers)
- [Building images](#building-images)
- [Containers in jobs](#containers-in-jobs)
- [Shared images](#shared-images)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Apptainer on FRCE

"Docker is not supported on the FRCE cluster for a variety of reasons", but Apptainer "can usually run Docker containers" ([Apptainer page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/UncategorizedSoftware/Apptainer)). Three runtimes are installed (live, Sept 2026):

| Runtime | How | Use |
|---|---|---|
| Apptainer 1.5.3, the OS package | `/usr/bin/apptainer` on the login and compute nodes; nothing to load | new work: the newest, and on PATH everywhere |
| Apptainer modules 1.4.0 and 1.4.1 (the default) | `module load apptainer/1.4.1` | rerunning work done with them; the Apptainer page shows 1.4.0 |
| SingularityCE modules 3.10.5 and 4.1.5 (the default) | `module load singularity/4.1.5` | pipelines that require SingularityCE (Sylabs) |

- The OS package also installs `/usr/bin/singularity`, so pipelines that call `singularity` run Apptainer 1.5.3 unless a `singularity` module is loaded; Apptainer reads `SINGULARITY_*` variables when the `APPTAINER_*` ones are unset. SingularityCE reads only `SINGULARITY_*`.
- Run this setup in every shell that pulls or builds. The default cache is `~/.apptainer/cache`, and /home is slow (STORAGE.md (Home)).

```bash
# on the compute node (inside your session)
apptainer --version                                                        # 1.5.3 (the system's) unless a module is loaded
export APPTAINER_CACHEDIR=/scratch/cluster_scratch/$USER/.apptainer/cache
export SINGULARITY_CACHEDIR=$APPTAINER_CACHEDIR                            # read by the singularity modules
mkdir -p "$APPTAINER_CACHEDIR" /scratch/cluster_scratch/$USER/containers
chmod 700 "$APPTAINER_CACHEDIR"
```

- The cache must be yours alone ("Apptainer cache directories cannot be shared across users"): mode 0700, and inside a setgid group share also `chmod g-s` it.
- **Temporary space.** A pull or build unpacks "the entire container image, uncompressed" into `APPTAINER_TMPDIR`, else `TMPDIR`, else `/tmp`, all on the node's local disk by default (STORAGE.md (Node-local scratch)). Keep it local: Apptainer's admin guide says that when building, `TMPDIR`/`APPTAINER_TMPDIR` "should not be set to an NFS location", and cluster scratch is NFS. If a pipeline exports `TMPDIR=/scratch/cluster_scratch/...`, set `APPTAINER_TMPDIR` to a per-job directory under `/scratch/local` (JOBS.md (Temporary files)).
- `WARNING: 'nodev' mount option set on /tmp, it could be a source of failure during build process` is expected here: FRCE's own transcript shows it on a pull that succeeded.
- Keep finished `.sif` images in `/scratch/cluster_scratch/$USER/containers` or a group share (running a SIF from NFS has no restrictions), never in /home or node-local scratch.

## Pulling images

```bash
# on the compute node (inside your session), after the setup block; mytool, ORG, and 1.2 are placeholders
cd /scratch/cluster_scratch/$USER/containers
apptainer pull mytool_1.2.sif docker://quay.io/ORG/mytool:1.2
apptainer exec mytool_1.2.sif mytool --version
```

- **Sources.** `docker://` covers Docker Hub, Quay (BioContainers), GHCR, and NVIDIA NGC (`docker://nvcr.io/...`); `oras://` pulls SIFs stored in OCI registries (the `oras/1.1.0` module adds the ORAS CLI). `library://` doesn't work out of the box: Apptainer's default endpoint "does not support the `library://` protocol". The user can add Sylabs' with `apptainer remote add --no-login SylabsCloud cloud.sycloud.io && apptainer remote use SylabsCloud`, which writes their `~/.apptainer/remote.yaml`.
- **Where to pull.** In your session or a job (internet access: TRANSFER.md (Downloads on the cluster)); the user can also pull on the transfer node. Never on the login node, even by the user: converting layers runs the CPU-heavy `mksquashfs`, which its CPU-time limit (SKILL.md) can kill.
- **Pin a tag** (never `latest`) and pull once. `apptainer exec docker://...` asks the registry for the image digest on every run and converts again whenever the tag moves, and parallel runs from remote URLs are unsafe on a cache in NFS, where "Rename on NFS is only atomic to a single client" (Apptainer admin guide).
- `pull` refuses to overwrite an existing file; `--force` replaces it (with the user's go-ahead).
- **Private registries:** the user runs `apptainer registry login --username NAME docker://docker.io` and types the password (or adds `--docker-login` to one pull). Credentials never go into scripts or the chat.
- **Cache upkeep:** `apptainer cache list -v`, then `apptainer cache clean --dry-run`; `apptainer cache clean --force` (it otherwise waits for a y/N answer) only with the user's go-ahead. Errors that mention `github.com/etcd-io/bbolt` mean a corrupted layer database: with the go-ahead, `rm ~/.local/share/containers/cache/blob-info-cache-v1.boltdb`.

## Running containers

FRCE's `/etc/apptainer/apptainer.conf` keeps Apptainer's default binds (Sept 2026: its only `bind path` lines are `/etc/localtime` and `/etc/hosts`, with `mount home` and `mount tmp` on and `mount hostfs` off): `$HOME`, the current directory, `/tmp`, `/var/tmp`, `/dev`, `/proc`, `/sys`, `/etc/hosts`, and `/etc/localtime`. Everything else (cluster scratch, group shares, `/mnt/nasapps`, reference data in `/SeqIdx` and `/mnt/alphafold`) is invisible until bound:

```bash
# on the compute node (inside your session); SHARE is a placeholder
SIF=/scratch/cluster_scratch/$USER/containers/mytool_1.2.sif
apptainer exec -B /scratch/cluster_scratch/$USER,/mnt/SHARE:/mnt/SHARE:ro "$SIF" mytool --help
```

- `-B src[:dest[:ro]]`, comma-separated or repeated (or `APPTAINER_BINDPATH`), adds to the defaults; every source must exist or the container won't start.
- Use `exec IMAGE COMMAND` from tool calls. `shell` is interactive, and `run` executes the image's runscript, which may start `/bin/bash`; either can hang a non-interactive call. `apptainer inspect --runscript IMAGE` shows what `run` would do.
- **Keep the host's Python and R setup out** of Python and R images:
  - `--cleanenv` passes only a minimal environment, which drops module variables such as `PYTHONHOME` and `PYTHONPATH` (PYTHON-R.md (Python on FRCE)), `R_LIBS`, `R_LIBS_USER`, and `PERL5LIB`.
  - `--no-home` stops `~/.local` packages and `~/.Rprofile` from loading.
  - `--cleanenv` also drops `SLURM_*`, `CUDA_VISIBLE_DEVICES`, and thread counts (it keeps only `TERM` and the proxy variables), so pass what the tool needs with `--env NAME=VALUE`, or put thread counts on the command line, where the host shell expands them.
  - With `--no-home`, a tool that writes under `$HOME` fails: give it a scratch home with `--home DIR` instead.

## GPUs in containers

- The job must hold GPUs (JOBS.md (GPUs)). `--nv` then binds the host's NVIDIA driver libraries and devices, and FRCE's configuration doesn't add it for you (`always use nv = no`); the image needs no driver of its own.
- `--nv` exposes every NVIDIA device on the node, and CUDA picks from `CUDA_VISIBLE_DEVICES`, which passes in from the job, except under `--cleanenv`. With `--cleanenv`, add `--env CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"`, and check it arrived with `printenv CUDA_VISIBLE_DEVICES` inside the container: `nvidia-smi` ignores the variable.
- The image's CUDA must suit the node's GPU and driver: DEVELOPMENT.md (CUDA and cuDNN).

```bash
# on a GPU compute node (inside your GPU session); a PyTorch image in this example
apptainer exec --nv "$SIF" nvidia-smi -L
apptainer exec --nv "$SIF" python -c 'import torch; print(torch.cuda.is_available())'
```

## Building images

Stop at the first option that works: an existing image; a `docker://` image converted with `pull` (or `apptainer build x.sif docker://...`); a definition file built on FRCE; a build elsewhere, copied in.

- **On FRCE.** An unprivileged `apptainer build` implies `--fakeroot`. With no `/etc/subuid` entry for the user (Sept 2026: `grep -c "^$USER:" /etc/subuid` printed 0), the "rootless" mode is out. apptainer.conf allows user namespaces (`allow user ns = yes`), which leaves the "root-mapped user namespace" (helped by a `fakeroot` command if one is installed), "not as complete an emulation as rootless mode": some package installs may fail. Untested on FRCE: try a small build in your session first. Build inside a job (`mksquashfs` is CPU-heavy), with temporary space on the node's local disk (above): NFS doesn't "support `--fakeroot`", per Apptainer's admin guide.

```bash
# on the compute node (inside your session), after the setup block
cd /scratch/cluster_scratch/$USER/containers
apptainer build mytool_1.2.sif mytool.def       # --fakeroot is implied for an unprivileged user
```

- **From a Dockerfile.** Apptainer can't build Dockerfiles; translate one: `Bootstrap: docker` and `From:` the base image, `RUN` steps into `%post`, `ENV` into `%environment`, `CMD`/`ENTRYPOINT` into `%runscript`.
- **Elsewhere.** If fakeroot isn't available or a build fails, the user builds on a Linux machine where they have root (`sudo apptainer build mytool_1.2.sif mytool.def`) or in CI that pushes to a registry, then copies the SIF in (TRANSFER.md) or you pull it. Apptainer has no `--remote` build service.

## Containers in jobs

Pull or build first; jobs use the SIF by path, never a `docker://` URI, which array tasks would each convert at once. A template for the user to submit (flags, sizing, and hand-over: JOBS.md; `mytool`, `SHARE`, and the paths are placeholders):

```bash
#!/bin/bash
#SBATCH --job-name=mytool
#SBATCH --partition=norm
#SBATCH --cpus-per-task=8
#SBATCH --mem=16g
#SBATCH --time=4:00:00
#SBATCH --output=%x_%j.out
set -euo pipefail
apptainer --version                                     # the system Apptainer, no module; logs its version
jobtmp=$(mktemp -d "/scratch/local/${USER}_${SLURM_JOB_ID}_XXXX")   # per-job temp: JOBS.md (Temporary files)
trap 'rm -rf "$jobtmp"' EXIT
proj=/scratch/cluster_scratch/$USER/proj
apptainer exec --cleanenv --no-home \
    -B "$proj,/mnt/SHARE:/mnt/SHARE:ro,$jobtmp:/tmp" \
    --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" \
    /scratch/cluster_scratch/$USER/containers/mytool_1.2.sif \
    mytool --threads "$SLURM_CPUS_PER_TASK" --in "$proj/in/s1.bam" --out "$proj/out/s1"
```

- `$jobtmp:/tmp` gives the container a private `/tmp` on the node's disk that the `trap` removes; drop it only if the tool writes almost nothing there.
- GPU jobs add the GPU request and `--nv`, plus the `CUDA_VISIBLE_DEVICES` pass-through while `--cleanenv` stays ([GPUs in containers](#gpus-in-containers)). Arrays: the same script reading `$SLURM_ARRAY_TASK_ID` (ARRAYS.md).
- MPI inside containers is undocumented on FRCE. The usual hybrid model runs the host's `mpirun` over `apptainer exec`, with an Open MPI in the image that matches the host's (DEVELOPMENT.md (MPI)).

## Shared images

- CCBR keeps prebuilt SIFs for its pipelines under `/mnt/projects/CCBR-Pipelines/SIFs` (e.g. `SIFs/XAVIER`), a third-party share (WORKFLOWS.md (CCBR pipelines on FRCE)): use images by path, and never write there.
- Group shares often hold a group's own images; to share yours, put the SIF in the group share with group read permission (STORAGE.md (Permissions and sharing)), never your private cache.

## Stale advice on the official pages

- [Apptainer page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/UncategorizedSoftware/Apptainer): both transcripts (`apptainer pull ...`, `apptainer run docker://...`) show no `srun`, so they read as login-node commands, where a large conversion can be killed → pull in a session or job ([Pulling images](#pulling-images)).
- Same page: its "SyLabs Documentation" link goes to apptainer.org. Sylabs makes SingularityCE; Apptainer is the Linux Foundation fork → Apptainer docs for `apptainer`, Sylabs docs for the `singularity` modules.
- Same page: it loads the `apptainer` module (1.4.0 in its transcript) and says nothing about caches, binds, GPUs, or building → the system Apptainer 1.5.3 needs no module; this file covers the rest.
- Same page: it points to Biowulf's singularity page and tutorial, whose `sing_binds` file, `/lscratch` binds, `/data` paths, and proot builds are Biowulf-only (FROM-BIOWULF.md).
- [FAQ](https://ncifrederick.cancer.gov/staff/FRCE/FrequentlyAskedQuestions): its "Using containers on FRCE." link is relative (`v/staff/FRCE/...`) and returns 404 → the Apptainer page.
- AppDB lists `singularity` 4.1.5 but neither the Apptainer modules nor the system Apptainer → `apptainer --version`, `module avail apptainer singularity`.

## Going further

- FRCE: [Apptainer](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/UncategorizedSoftware/Apptainer) · AppDB [singularity](https://appdb.ncifcrf.gov/software/singularity) (NIH network).
- Apptainer 1.5 user guide (the system version; the modules are 1.4): [cache](https://apptainer.org/docs/user/1.5/build_env.html#cache-folders) and [temporary folders](https://apptainer.org/docs/user/1.5/build_env.html#temporary-folders) · [default binds](https://apptainer.org/docs/user/1.5/bind_paths_and_mounts.html#system-defined-bind-paths) · [environment from the host](https://apptainer.org/docs/user/1.5/environment_and_metadata.html#environment-from-the-host) · [GPUs](https://apptainer.org/docs/user/1.5/gpu.html#nvidia-gpus-cuda-standard) · [fakeroot builds](https://apptainer.org/docs/user/1.5/fakeroot.html#building-container-images) · [definition file vs Dockerfile](https://apptainer.org/docs/user/1.5/docker_and_oci.html#apptainer-definition-file-vs-dockerfile) · [library:// endpoints](https://apptainer.org/docs/user/1.5/endpoint.html#restoring-pre-apptainer-library-behavior) · [Singularity compatibility](https://apptainer.org/docs/user/1.5/singularity_compatibility.html). Admin guide: [NFS limits](https://apptainer.org/docs/admin/1.5/installation.html#nfs) (temporary space, fakeroot) and [cache on network filesystems](https://apptainer.org/docs/admin/1.5/installation.html#apptainer-cache-atomic-rename).
- SingularityCE (for `singularity/4.1.5`): [user guide 4.1](https://docs.sylabs.io/guides/4.1/user-guide/).
- Biowulf docs (translate binds and paths first): [apptainer.html#bind](https://hpc.nih.gov/apps/apptainer.html#bind) · [apptainer.html#gpu](https://hpc.nih.gov/apps/apptainer.html#gpu).
- Live: `apptainer --version`, `module avail apptainer singularity`, `grep -E '^(bind path|allow)' /etc/apptainer/apptainer.conf`, `grep -c "^$USER:" /etc/subuid`, `apptainer cache list`, `apptainer help exec`.
