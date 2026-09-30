Building software on FRCE: where builds may run, the system and module compilers, instruction sets per node type and portable CPU targets, build systems and install prefixes, Open MPI, CUDA and cuDNN, and Go, Rust, Java, and Perl. You build and test inside the user's allocation; long builds become batch jobs the user submits (ground rules in SKILL.md). Check first for a module, environment, or container (MODULES.md (When software isn't installed)). Node models and counts: HARDWARE.md. Job scripts, GPU requests, and multinode MPI jobs: JOBS.md. Deep-learning frameworks: DEEP-LEARNING.md.

Table of contents

- [Where to build](#where-to-build)
- [Compilers](#compilers)
- [CPU targets](#cpu-targets)
- [Build systems and install prefixes](#build-systems-and-install-prefixes)
- [MPI](#mpi)
- [CUDA and cuDNN](#cuda-and-cudnn)
- [Other languages](#other-languages)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Where to build

- **In the user's allocation:** an `srun` session sized for the build (parallel C++ compiles and links can take gigabytes each), or a batch job the user submits for long builds.
- **On the transfer node (batch2):** FRCE allows "*some* CPU-intensive jobs such as compiling software" there ([system diagram page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/VisualdiagramFRCESystems)). That is the user's option; you never run there.
- **Never on the login node**, where long compiles get killed (SKILL.md).
- **No root.** `dnf install` is out; a missing system library comes from a module, conda, a container, or a request (MODULES.md).
- **Clean toolchain.** `module purge`, then load only the compiler and dependencies. Deactivate conda envs and unload application modules that bundle conda (snakemake, alphafold), or build tools find their headers, libraries, and Python ahead of the ones you meant.
- Source downloads and `git clone`: TRANSFER.md (Downloads on the cluster).

A build script that runs in your session (`bash build_mytool.sh`) or as the user's job; `mytool`, the version, and the tarball are placeholders:

```bash
#!/bin/bash
# build_mytool.sh — the user can submit it: sbatch --partition=norm --cpus-per-task=8 --mem=16g --time=2:00:00 build_mytool.sh
set -euo pipefail
name=mytool; ver=1.2.3
prefix=/scratch/cluster_scratch/$USER/sw/$name/$ver
[[ ! -e $prefix ]] || { echo "$prefix exists: ask before overwriting" >&2; exit 1; }
source /etc/profile.d/modules.sh 2>/dev/null || true     # module init: MODULES.md
module purge
module load gcc/14.3.0                                   # pinned; see Compilers
build=$(mktemp -d "/scratch/local/${USER}_${SLURM_JOB_ID:-$$}_XXXX")   # node-local build tree (JOBS.md (Temporary files))
trap 'rm -rf "$build"' EXIT
tar -xf ~/src/"$name-$ver.tar.gz" -C "$build"            # own line: set -e ignores a failure before &&
cd "$build/$name-$ver"
./configure --prefix="$prefix" CFLAGS="-O2 -march=x86-64-v3" CXXFLAGS="-O2 -march=x86-64-v3"
make -j "${SLURM_CPUS_PER_TASK:-1}"
make check
make install
module -t list > "$prefix/BUILD-MODULES.txt" 2>&1       # the toolchain, recorded beside the install
```

## Compilers

Module lists are as of Sept 2026 (`module avail gcc intel nvhpc`):

| Compiler | How | Notes |
|---|---|---|
| The OS's GCC | always on PATH | version unchecked (`gcc --version` with no module loaded); `-march=x86-64-v3` needs GCC 11 or later |
| GCC modules | `module load gcc/14.3.0` (FRCE's `gcc@14` example) | 10.5.0, 11.5.0, 12.5.0, 13.4.0, 14.3.0, 15.2.0, 16.1.0, and 16.2.0 (the default, which also sets `CC`, `CXX`, `F77`, and `F90`) |
| Intel | `module load intel/2025.2.0` | 2022u4, 2023.1.0, 2025.2.0, 2026.0.1; commercially licensed (MODULES.md (When software isn't installed)). 2025.2.0 and 2026.0.1 have only `icx`, `icpx`, and `ifx`: no `icc`, `icpc`, or `ifort` |
| NVIDIA HPC SDK | `module load nvhpc/26.3` | `nvc`, `nvc++`, `nvfortran` with OpenACC and CUDA Fortran; the only version |
| Clang/LLVM | none | no module; whether the OS has `clang` is unchecked (`command -v clang`); conda-forge packages it |

- A binary built with a module GCC needs that GCC's runtime (`libstdc++`, `libgfortran`) at run time. Load the same module in the job, link it statically (`-static-libstdc++ -static-libgcc`, `-static-libgfortran`), or embed an rpath to the module's `lib64`. Forgetting shows up as ``version `GLIBCXX_3.4.NN' not found``.

## CPU targets

A job runs on whatever node its partition gives it, and code built for a newer CPU than the node's dies with `Illegal instruction`. Each node's CPU-model feature (HARDWARE.md (Features and constraints)) maps to an instruction set (Intel's specifications) and a GCC target:

| Feature | Instruction set | `-march` for tuning |
|---|---|---|
| `x6150` | AVX-512 (x86-64-v4) | `skylake-avx512` |
| `x6254`, `x6242R`, `x8268` | AVX-512 | `cascadelake` |
| `x6342`, `x6346` | AVX-512 | `icelake-server` |
| `x6740P` | AVX-512, AMX | `graniterapids` (GCC 13 or later) |
| `x6710E` (the H200 hosts) | AVX2 only (x86-64-v3) | `sierraforest` (GCC 13 or later) |

The A100 and L40s hosts' tags are wrong (HARDWARE.md (Features and constraints)), but their CPUs have at least what the tags say; the L40s hosts' Emerald Rapids parts take `emeraldrapids` (GCC 13 or later) and have AMX. That the H200 hosts lack AVX-512 follows from their CPU model; `grep -c avx512f /proc/cpuinfo` in a job there confirms it.

- **Portable, the default:** `-O2 -march=x86-64-v3` with a module GCC (11 or later), or `-march=haswell` with an older GCC. That is AVX2 and FMA, which every node has, so the binary runs anywhere.
- **AVX-512** (`-march=x86-64-v4`, `-march=skylake-avx512` or newer, or `-march=native` on almost any node, the transfer node included) runs on every node in the CPU partitions (Sept 2026) but fails on the H200 hosts. A GPU job running such code names another GPU type (JOBS.md (GPUs)) or a CPU feature (HARDWARE.md (Features and constraints)); a bare `--gres=gpu:1` can land on an H200 host.
- Code tuned for one generation can die on an older one, and `-march=native` means the build node's. Many projects add `-march=native` themselves: grep their build files before building on one node type for all.
- This node: `lscpu | grep -E 'Model name|Flags'`. Go binaries have their own version of this problem: [Other languages](#other-languages).

## Build systems and install prefixes

- **Prefix:** `/scratch/cluster_scratch/$USER/sw/NAME/VERSION` for your own tools, or a group share (`/mnt/<share>/sw/...`) for the group's. Keep the build script in /home or git so the install can be rebuilt (STORAGE.md (Cluster scratch)). Then write a personal modulefile (MODULES.md (Personal modulefiles)).
- **CMake** modules: `cmake/3.25.2`, `3.31.0`, and `4.0.3`, the default (Sept 2026). CMake 4 rejects projects whose `cmake_minimum_required` is below 3.5 ("Compatibility with CMake < 3.5 has been removed"): build those with `cmake/3.31.0`, or pass `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`.

```bash
# on the compute node (inside your session), in the unpacked source tree; $prefix as in the template
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
      -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_INSTALL_RPATH="$prefix/lib" \
      -DCMAKE_PREFIX_PATH=/mnt/nasapps/production/DEP/VERSION
cmake --build build -j "${SLURM_CPUS_PER_TASK:-1}" && cmake --install build
```

- A dependency from a module: `module display NAME` shows where it lives; pass that path through `CMAKE_PREFIX_PATH`, or `CPPFLAGS=-I...` and `LDFLAGS=-L...` for autotools.
- Prefer an rpath (`LDFLAGS="-Wl,-rpath,$prefix/lib"`, or CMake's `CMAKE_INSTALL_RPATH`) to `LD_LIBRARY_PATH` in the modulefile. With CMake, keep `CMAKE_INSTALL_LIBDIR=lib` as above: GNUInstallDirs otherwise installs into `lib64` on EL8, where that rpath doesn't point.
- **Spack:** `module load spack/1.1.1` (untested on FRCE). Its prefix is read-only, so before `spack install` send its caches and install tree to cluster scratch: `export SPACK_USER_CACHE_PATH=/scratch/cluster_scratch/$USER/spack`, then `spack config --scope user add config:install_tree:root:/scratch/cluster_scratch/$USER/spack/opt`; `spack config get config` shows what the site already sets.
- Python extensions and R packages compile inside their environment (PYTHON-R.md).

## MPI

- **The modules:** `openmpi` 4.0.7, 4.1.4, 4.1.5, 5.0.3, 5.0.5, and 5.0.9, the default (Sept 2026). FRCE's page builds 5.0.5 with `--with-slurm --with-cuda=$CUDABASE --without-ofi`, so it is CUDA-aware and has no libfabric. The modules load no compiler (`module display openmpi/5.0.9`): `ompi_info | grep -i 'compiler abs'` shows what one was built with, and `mpicc --showme` what its wrapper runs.
- **InfiniBand:** Open MPI 5 dropped the `openib` component and supports InfiniBand "via the UCX (`ucx`) PML"; with OFI also left out of the 5.0.5 build, a module without UCX sends MPI traffic between nodes over TCP. Whether the modules include UCX is unchecked: `ompi_info | grep -i ucx`.
- **Compiling:** load the Open MPI the job will load (JOBS.md's template: `openmpi/5.0.9`), for Fortran also a GCC of the major version it was built with (its `.mod` files need it), then use the wrappers: `module load openmpi/5.0.9 && mpicc -O2 -o hello hello.c`.
- **Launching** happens only inside an allocation: the user's job, or your session if it was started with several tasks. Open MPI's docs recommend `mpirun ./prog` under Slurm, where it takes the rank count and hosts from the allocation. Slurm can also start the ranks, but FRCE sets no `MpiDefault`, so `srun` needs `--mpi=pmix` every time: `srun --mpi=list` shows `pmix` (plugin version `pmix_v2`) and `pmi2` (Sept 2026), and `srun --mpi=pmix ./prog` is the launch FRCE's page shows as `--mpi=pmix_v2`. Never `--mpi=pmi2` with Open MPI 5: "PMI-2 is not supported in Open MPI 5.0.0 and later releases". Multinode job scripts: JOBS.md (MPI and multinode jobs).

## CUDA and cuDNN

- **CUDA modules** (Sept 2026): `cuda/10.2`, `11.8`, `12.0`, `12.1`, `12.8`, `13.0`, and `cuda/cuda10.0`, which bare `module load cuda` gives (MODULES.md (Loading and pinning versions)): always pin. `cuda/cuda10.0` sets `CUDA_HOME` and `CUDABASE` (Open MPI's configure line uses the latter); `module display` shows what another version sets.
- **cuDNN** modules: `cudnn/7.6.5-cuda10.0`, `8.8.3-cuda11`, `8.8.3-cuda12`, `9.8.0-cuda11`, `9.8.0-cuda12`, `9.14.0-cuda12`, and `9.14.0-cuda13`, installed under `/mnt/nasapps/production/cudnn/<version>` with `CUDNN_ROOT_DIR` set. Load the build for your CUDA major version. TensorRT: `tensorRT/8.6.1-cuda11` and `-cuda12`.
- `nvcc` compiles on any node; test on a GPU the user allocates (JOBS.md (GPUs)). Compute capability per GPU type: HARDWARE.md (GPUs). One binary for every FRCE GPU, with a 12.x toolkit:

```bash
# on the compute node (inside your session)
module load cuda/12.8
nvcc -O2 -gencode arch=compute_60,code=sm_60 -gencode arch=compute_70,code=sm_70 \
  -gencode arch=compute_80,code=sm_80 -gencode arch=compute_89,code=sm_89 \
  -gencode arch=compute_90,code=sm_90 -gencode arch=compute_90,code=compute_90 -o app app.cu
# CMake: -DCMAKE_CUDA_ARCHITECTURES="60-real;70-real;80-real;89-real;90"; nvcc --list-gpu-arch lists what a toolkit supports
```

- **CUDA 13 dropped P100 and V100.** "Offline compilation and library support" for Maxwell, Pascal, and Volta were removed in CUDA 13.0, while CUDA 12.x "will continue to be supported" for them. Build P100 (sm_60) and V100 (sm_70) code with a 12.x toolkit. The A100 (sm_80) needs CUDA 11.0 or later, and the L40s (sm_89) and H200 (sm_90) 11.8 or later, which rules out `cuda/10.2` and `cuda/cuda10.0` for all three (`nvcc fatal : Unsupported gpu architecture 'compute_80'`).
- **The driver** caps the runtime: in a GPU session, the `nvidia-smi` header shows the driver version and the newest CUDA it supports (unchecked per node type). A newer runtime fails with `CUDA driver version is insufficient for CUDA runtime version`.

## Other languages

- **Go.** Modules `go/1.20.2`, `1.23.0`, and `1.24.1` (Sept 2026); the OS has an older Go, per the Go page. Staff built 1.24.1 with `GOAMD64=v4`, so it targets v4 by default. Go "does not currently generate any AVX512 instructions", yet a v4 binary refuses to start on a CPU without AVX-512 ("This program can only be run on AMD64 processors with v4 microarchitecture support."), as on the H200 hosts ([CPU targets](#cpu-targets)), possibly including the module's own `go` (unchecked: `go env GOAMD64`; `go version` in a job there). Build with `GOAMD64=v3`, and keep caches off /home:

```bash
# on the compute node (inside your session), or in the build script
export GOAMD64=v3 GOPATH=/scratch/cluster_scratch/$USER/go GOCACHE=/scratch/cluster_scratch/$USER/.cache/go-build
```

- **Rust.** No module (Sept 2026). rustup installs to `~/.rustup` and `~/.cargo` and edits shell profiles unless told otherwise; send both to cluster scratch and skip the profile edits:

```bash
# on the compute node (inside your session)
export RUSTUP_HOME=/scratch/cluster_scratch/$USER/rustup CARGO_HOME=/scratch/cluster_scratch/$USER/cargo
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
export PATH=$CARGO_HOME/bin:$PATH
cargo build --release -j "${SLURM_CPUS_PER_TASK:-1}"
```

- **Java.** Modules `java/1.8.0`, `11`, `17`, `21`, and `24`, plus the OS's `/usr/bin/java` (Sept 2026). Pin `java/17` or `java/21`: the default (MODULES.md (Loading and pinning versions)) is too old for current GATK and Nextflow, which need 17 or later. In jobs, keep `-Xmx` well below `--mem`, pass `-XX:ActiveProcessorCount=$SLURM_CPUS_PER_TASK` (the JVM sizes its GC and thread pools from the CPUs it detects), and set `-Djava.io.tmpdir` to the per-job directory (JOBS.md (Temporary files)).
- **Perl.** Check for an installed module as in MODULES.md (Finding software). Don't run `cpan` at all, not even the docs' `cpan -l`, unless `~/.cpan/CPAN/MyConfig.pm` exists: a first run configures itself, answering its own questions with the defaults when stdin isn't a terminal, bootstraps local::lib into `~/perl5`, and appends its settings to `~/.bashrc` (ground rules in SKILL.md). Install into cluster scratch with `cpanm -l`:

```bash
# on the compute node (inside your session); Some::Module is a placeholder
export PERL_LOCAL=/scratch/cluster_scratch/$USER/perl5 PERL_CPANM_HOME=/scratch/cluster_scratch/$USER/.cpanm   # cpanm's build dirs, else ~/.cpanm
export PERL5LIB=$PERL_LOCAL/lib/perl5${PERL5LIB:+:$PERL5LIB} PATH=$PERL_LOCAL/bin:$PATH   # also in jobs that use them
mkdir -p "$PERL_LOCAL/bin"
command -v cpanm >/dev/null || { curl -fsSL https://cpanmin.us/ -o "$PERL_LOCAL/bin/cpanm" && chmod +x "$PERL_LOCAL/bin/cpanm"; }
cpanm -l "$PERL_LOCAL" Some::Module
```

- Modules also exist for Node.js (`nodejs/20.9.0`), Groovy (`groovy/4.0.11`), and Mono (`mono/6.12.0.90`); PHP, Lua, Tcl, and SWIG have none (Sept 2026): check `command -v NAME` for OS copies.

## Stale advice on the official pages

- [Development Tools](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/DevelopmentTools): a legacy index whose three links (`/node/275`, `/node/274`, `/node/239`) redirect to a staff login page → the Workflow & Development Software pages in Going further.
- [Available Compilers & Scripting Languages](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/AvailableCompilersScriptingLanguages): "Clang is an alternative front-end to the gcc compilers" → Clang is LLVM's front end, and it has no module here. It calls Go "Available only through `module load go`", while the Go page says the OS includes an older one → both exist. It lists Rust and Clang without saying how to get them, and names no modules for R, Perl, PHP, Groovy, SWIG, Lua, Node.js, or Tcl → R, Groovy, and Node.js have modules; Rust, Clang, Perl, PHP, SWIG, Lua, and Tcl don't (Sept 2026).
- [Go](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandScriptingLanguages/Go): the build heading says "the newest release of Python3" (copied), its documentation link is `https://https://go.dev/doc` (→ https://go.dev/doc), and the `GOAMD64=v4` build is covered above.
- [GNU Compiler Collection](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandInterpreters/GNUCompilerCollection): documents a staff build of 13.2.0 (`--with-arch=skylake`, compiled with `gcc/12.2.0`) into the read-only `/mnt/nasapps`; neither version is a module now → `module avail gcc`.
- [open MPI](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/AdditionalLibraries/openMPI): its bare `module load openmpi` now gives 5.0.9, not the 5.0.5 it builds; its build lines' `gcc/12.4.0` no longer exists (12.5.0 does), and their bare `module load cuda` now gives CUDA 10.0. Its `srun -N 4 --mpi=pmix_v2 ./hello` names a valid plugin but, run bare, requests a new 4-node job, which only the user may submit (ground rules in SKILL.md) → inside an allocation, `mpirun` or `srun --mpi=pmix` ([MPI](#mpi)).
- [cudnn](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/AdditionalLibraries/cudnn): a staff recipe that renames the archive in `/mnt/nasapps/production` but copies cuSPARSELt into `.../cudnn/9.8.0-cuda12`, and names no module → `cudnn/9.8.0-cuda12` is one of seven builds (`module avail cudnn`).

## Going further

- FRCE: [Available Compilers & Scripting Languages](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/AvailableCompilersScriptingLanguages) · [GNU Compiler Collection](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandInterpreters/GNUCompilerCollection) · [Go](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandScriptingLanguages/Go) · [Additional Libraries](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/AdditionalLibraries) ([open MPI](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/AdditionalLibraries/openMPI), [cudnn](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/AdditionalLibraries/cudnn)) · [Software Licenses](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandScriptingLanguages0).
- Upstream: [GCC x86 options](https://gcc.gnu.org/onlinedocs/gcc/x86-Options.html) · [CMAKE_POLICY_VERSION_MINIMUM](https://cmake.org/cmake/help/latest/variable/CMAKE_POLICY_VERSION_MINIMUM.html) · [Spack install_tree](https://spack.readthedocs.io/en/latest/config_yaml.html#install-tree-root) · [Open MPI 5 under Slurm](https://docs.open-mpi.org/en/v5.0.x/launching-apps/slurm.html) · [Open MPI 5 on InfiniBand (UCX)](https://docs.open-mpi.org/en/v5.0.x/tuning-apps/networking/ib-and-roce.html) · [Slurm MPI guide](https://slurm.schedmd.com/mpi_guide.html#open_mpi) · [CUDA 13.0 deprecated architectures](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-toolkit-release-notes/index.html#deprecated-architectures) · [Go amd64 levels](https://go.dev/wiki/MinimumRequirements#amd64) · [rustup install options](https://rust-lang.github.io/rustup/installation/other.html) · [cpanm](https://metacpan.org/pod/App::cpanminus).
- Biowulf docs (Lmod module names; translate): [compilers.html](https://hpc.nih.gov/development/compilers.html) · [MPI.html](https://hpc.nih.gov/development/MPI.html) · [cuDNN.html](https://hpc.nih.gov/development/cuDNN.html).
- Live: `gcc --version`, `module avail gcc cuda cudnn openmpi intel nvhpc cmake go java`, `module avail -d cuda`, `ompi_info | grep -i -E 'ucx|pmix|cuda|compiler abs'`, `srun --mpi=list`, `sinfo -o '%P %f'`, `nvidia-smi`, `nvcc --list-gpu-arch`, `lscpu`, `go env GOAMD64`.
