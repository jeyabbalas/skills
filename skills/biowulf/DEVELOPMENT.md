Building and installing software from source on Biowulf: where builds run, compilers and CPU targets, autotools and CMake, MPI, CUDA, math libraries, debuggers, Java and Maven, and where other languages keep their packages. Before building, check whether a module, conda package, or container already provides the software (decision order and personal modulefiles: MODULES.md; conda: CONDA.md). Job and GPU request syntax and the multinode MPI template are in JOBS.md, node and GPU models in HARDWARE.md, deep-learning frameworks in DEEP-LEARNING.md.

Table of contents

- [Build inside the session](#build-inside-the-session)
- [Compilers](#compilers)
- [CPU targets: portable or node-specific](#cpu-targets-portable-or-node-specific)
- [Autotools, CMake, and build variables](#autotools-cmake-and-build-variables)
- [MPI](#mpi)
- [CUDA and GPU code](#cuda-and-gpu-code)
- [Math and other libraries](#math-and-other-libraries)
- [Debuggers, profilers, linters](#debuggers-profilers-linters)
- [Java and Maven](#java-and-maven)
- [Other languages](#other-languages)
- [Editors and Stow](#editors-and-stow)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Build inside the session

NIH lets humans do "light editing, code compilation" on the login node; that allowance does not extend to you. Every download, `module load`, configure, and compile runs inside the user's session on a compute node. Write the build as a script, so it can run in the session now or as the user's batch job later:

```bash
#!/bin/bash
# build.sh: run in the session (bash build.sh) or hand the user an sbatch line for it
set -e
name=hello; ver=2.10
prefix=/data/$USER/opt/$name/$ver                  # NIH convention; append -<feature> for a -march=native build
[[ ! -e $prefix ]] || { echo "$prefix exists: ask before overwriting" >&2; exit 1; }
export TMPDIR=/lscratch/$SLURM_JOB_ID              # the job needs --gres=lscratch:N
module purge                                       # start clean, as NIH's handout does
module load gcc/VERSION                            # pin (>= 11 for the flags below); exact names: module -r spider '^gcc$'
cd "$TMPDIR"
wget -q https://ftp.gnu.org/gnu/hello/$name-$ver.tar.gz && tar -xf $name-$ver.tar.gz && cd $name-$ver
./configure --prefix="$prefix" CFLAGS="-O2 -march=x86-64-v3"   # GCC >= 11; runs on every node type (C++/Fortran: same in CXXFLAGS/FCFLAGS)
make -j "${SLURM_CPUS_PER_TASK:-2}"
make check
make install
module list 2>&1 | tee "$prefix/BUILD-MODULES.txt" # record the toolchain beside the install
```

- **Size.** The default session is too small for most builds. Either the user starts a bigger one and restarts you in it (e.g. `sinteractive --cpus-per-task=8 --mem=16g --gres=lscratch:20`), or, better for long builds, you hand them `sbatch --cpus-per-task=16 --mem=32g --gres=lscratch:50 --time=4:00:00 build.sh`. Parallel C++ compiles and links can take GBs each (generic): lower `-j` before you exceed `--mem`.
- **Where things go.** Unpack and build on lscratch (node-local, fast for a build's many small files, gone when the job ends); install to `/data/$USER/opt/<name>/<version>`; the user's own repositories stay in /data. Then write a personal modulefile for the prefix (MODULES.md).
- **No root.** No `sudo`, and `/usr/local` is not writable: aim `--prefix` or `-DCMAKE_INSTALL_PREFIX` at /data. If the instructions need root or a missing system library, the user asks staff (NIH: "please just put in a ticket").
- **Clean environment.** No conda env active while building: its `bin` on the PATH leads CMake and `pkg-config` to the env's headers and libraries instead of the modules' (generic).
- **Downloads** go through the compute-node proxy, so use https URLs (TRANSFER.md). Submodules with `git@github.com:` URLs fail the same way; rewrite them for one command (generic git): `git -c url."https://github.com/".insteadOf="git@github.com:" submodule update --init --recursive`.

## Compilers

- **System GCC** (gcc, g++, gfortran, gdb) is on the PATH of every compute node: the OS vendor's version, "usually the best choice for pre-existing source codes". NIH doesn't state the version (the OS has been Rocky 8 since June 2023); run `gcc --version`.
- **Newer GCC**: `module avail gcc`. A binary built with a module GCC needs that module's runtime at run time: load the same module in the job, or link the runtime in with `-static-libgcc -static-libstdc++` (C++) or `-static-libgfortran`. Forgetting shows up as ``version `GLIBCXX_3.4.NN' not found`` or a missing `libgfortran.so` (generic error text).
- **Intel**: `module avail intel`. C/C++/Fortran, OpenMP, the Intel debugger, MKL, IPP, and LINPACK (plus TBB, per the index); "anecdotal evidence suggests that this compiler suite frequently provides the best performance for calculation-intensive applications".
- **Anything else** (clang/LLVM, NVHPC, oneAPI `icx`/`ifx`, AOCC) is undocumented: `module spider <name>` before relying on it. The index also lists zig.

## CPU targets: portable or node-specific

Biowulf mixes CPU generations, and a job lands on any node type its partition offers unless it carries a `--constraint`. Code built for a newer CPU than the node's dies with `Illegal instruction` (SIGILL). Feature names and CPU models are from the [hardware page](https://hpc.nih.gov/systems/hardware.html) (as of Sept 2026; counts, memory, and GPUs: HARDWARE.md); the microarchitecture, `-march` name, and SIMD columns are generic knowledge:

| Feature | CPU (hardware page) | Found in | Microarchitecture, GCC `-march=` | Widest SIMD |
|---|---|---|---|---|
| `x2680` | Intel E5-2680v4 | CPU nodes; P100 and V100 GPU nodes | Broadwell, `broadwell` | AVX2 |
| `x8860` | Intel E7-8860v4 | 1.5 TB and 3 TB nodes | Broadwell, `broadwell` | AVX2 |
| `e7543`, `e7543p` | AMD Epyc 7543 / 7543p | CPU nodes; A100 GPU nodes | Zen 3, `znver3` | AVX2 |
| `x6140` | Intel Xeon Gold 6140 | CPU nodes; V100x GPU nodes | Skylake-SP, `skylake-avx512` | AVX-512 |
| `x6240` | Intel Xeon Gold 6240 | CPU nodes | Cascade Lake, `cascadelake` | AVX-512 |
| `e9454` | AMD Epyc 9454 | CPU nodes; 3 TB nodes | Zen 4, `znver4` | AVX-512 |
| `e9645` | AMD Epyc 9645 | CPU nodes; H200 GPU nodes | Zen 5, `znver5` | AVX-512 |
| `x6787p` | Intel Xeon 6787p | L40 GPU nodes | Granite Rapids, `graniterapids` | AVX-512, AMX |

This node's feature: `nodetype $(hostname -s)`, or `scontrol show node $(hostname -s) | grep -o 'ActiveFeatures=[^ ]*'`. Strategies (generic GCC flags; `znver4`, `znver5`, and `graniterapids` exist only in newer GCC releases, so test a name first with `gcc -march=znver5 -S -x c /dev/null -o /dev/null`):

- **Portable, the default**: `-O2 -march=x86-64-v3` (GCC ≥ 11) or `-march=haswell` (older GCC). AVX2 with FMA is common to every row, so the binary runs anywhere without a constraint.
- **AVX-512 family**: `-march=x86-64-v4` runs only on the AVX-512 rows, so every CPU job needs `--constraint="x6140|x6240|e9454|e9645"` (NIH app pages use this OR form for GPU features; the grouping is generic).
- **Node-specific**: `-march=native` on a node with feature F, installed as `<version>-F`; every job needs `--constraint=F`. One install per feature you target.
- **Fat binary**: GCC `target_clones` or Intel `-ax<ISA>` pick a code path at run time. NIH's julialang module does the equivalent for Julia (Other languages).
- **Check the project's defaults** (generic; verify): many Makefiles and CMake files add `-march=native` themselves, so grep for it. Intel `-x<ISA>` or `-xHost` binaries may refuse to start on the AMD nodes; for a mixed fleet use `-march=` or `-ax`.

## Autotools, CMake, and build variables

The CMake pattern from NIH's [personal-software handout](https://hpc.nih.gov/training/handouts/managing-personal-software.pdf) (its kallisto example; versions are the handout's):

```bash
module load gcc cmake hdf5 zlib        # dependencies come from modules
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/data/$USER/opt/kallisto/0.46.0 \
      -DCMAKE_EXE_LINKER_FLAGS="$ZLIB_LIBS" \
      -DCMAKE_SKIP_RPATH=YES ..        # $ZLIB_LIBS comes from the zlib module; skipping CMake's rpath lets LD_RUN_PATH apply
make -j "${SLURM_CPUS_PER_TASK:-2}" && make install
```

- **Missing dependency** (`Could NOT find HDF5`, or errors from a too-old system library such as zlib): `module load` it, delete the build directory (CMake caches earlier results, such as the old system zlib it found), and reconfigure. `module show <dep>` lists the paths and helper variables (like `$ZLIB_LIBS`) a module sets.
- **Autotools**: the system autoconf, automake, and libtool "tend to be out of date"; `module load automake` also loads newer autoconf, m4, and libtool. Then `./configure --prefix=...`, `make -j`, `make check`, `make install`.
- **Build variables** (handout): `CPATH` (headers), `LIBRARY_PATH` (libraries to link), `CPPFLAGS` (`-I…`), `LDFLAGS` (`-L…`), `CFLAGS`/`CXXFLAGS`, and `LD_RUN_PATH` (rpath written into the binary; ignored when `-Wl,-rpath` is on the link line).
- **Run-time variables**: `PATH`, `MANPATH`, and `LD_LIBRARY_PATH`, which binaries built with rpath don't need. They belong in the modulefile (MODULES.md).

## MPI

- **Implementations** (development index, as of Sept 2026; list builds with `module avail openmpi/` and `module avail mvapich/ mvapich2/`). OpenMPI is "the most frequently used" and integrates with Slurm; staff recommend 4.0.4 or later (older modules are deprecated and may be removed). MVAPICH2 targets InfiniBand. The index also lists OpenMPI 5.0.5, mvapich 4.1, and mpich 4.2.3, which the MPI page doesn't cover.
- **Module names** encode the compiler and, for CUDA-aware builds, CUDA (old examples: `openmpi/4.0.1/gcc-7.4.0`, `openmpi/4.0.1/cuda-10.1/gcc-7.4.0`). Compile with that module's wrappers (`mpicc`, `mpicxx`, `mpifort`) and its compiler, and load the identical module in the job (generic).
- **InfiniBand only**: "programs compiled against OpenMPI 4 will only run correctly on Biowulf InfiniBand nodes".
- **Launch** inside an allocation ([MPI.html](https://hpc.nih.gov/development/MPI.html)):

```bash
srun --mpi=pmix_v3 ./prog args        # OpenMPI >= 4.0, MVAPICH >= 2.3.4; the rank count comes from Slurm
srun --mpi=pmi2 ./prog args           # some older OpenMPI modules
mpirun -np $SLURM_NTASKS ./prog args  # also supported
srun --mpi=list                       # plugins this Slurm offers (generic; R.html uses --mpi=pmix)
```

- **OpenMPI 4.0.x** prints "confusing (but harmless)" OpenIB/UCX warnings; silence them in the job script with `export OMPI_MCA_btl_openib_allow_ib=1 OMPI_MCA_pml=ucx OMPI_MCA_btl=^openib`.
- **Who runs what**: an `srun`/`mpirun` smoke test inside your own session is allowed but may not work: R.html says MPI code runs from sinteractive, while a comment in its source calls that "not currently true". Try it in a session started with tasks (the user runs e.g. `sinteractive --ntasks=4 --ntasks-per-core=1`); if it hangs or fails, test in a short batch job the user submits. Real runs are batch jobs the user submits; the template (one node type, `--exclusive`, `--ntasks-per-core=1`) and the multinode rules are in JOBS.md. mpi4py: PYTHON.md; Rmpi: R.md; MPI in containers: CONTAINERS.md.

## CUDA and GPU code

- **Modules** (as of Sept 2026; case matters): `module load CUDA` (index: 12.8; versioned like `CUDA/12.1`). cuDNN module names end in the CUDA version they pair with; load both, as NIH does: `module load cuDNN/8.9.2/CUDA-12 CUDA/12.1`. cuDNN ships static and shared libraries; for a version that isn't installed, the user asks staff. Current lists: `module avail CUDA cuDNN`.
- **Build on CPU, test on GPU**: `nvcc` needs no GPU to compile (only `-arch=native` does; generic). Test on a GPU the user allocates, e.g. `sinteractive --gres=gpu:TYPE:1,lscratch:20 --cpus-per-task=8` (type strings and CPUs-per-GPU caps: JOBS.md).
- **Targets**: compile for every GPU type the job can land on, or pin the type in the request. Compute capabilities are generic knowledge, except that an NIH TensorFlow log shows 6.0 for the P100:

| GPU (feature) | Compute capability | `-gencode` pair |
|---|---|---|
| P100 (`gpup100`) | 6.0 | `arch=compute_60,code=sm_60` |
| V100, V100x (`gpuv100`, `gpuv100x`) | 7.0 | `arch=compute_70,code=sm_70` |
| A100 (`gpua100`) | 8.0 | `arch=compute_80,code=sm_80` |
| L40 (`gpul40`) | 8.9 | `arch=compute_89,code=sm_89` |
| H200 (`gpuh200`) | 9.0 | `arch=compute_90,code=sm_90` |

```bash
module load CUDA/12.8     # confirm with module avail CUDA; a 12.x toolkit still targets sm_60 and sm_70
nvcc -O2 -gencode arch=compute_60,code=sm_60 -gencode arch=compute_70,code=sm_70 \
  -gencode arch=compute_80,code=sm_80 -gencode arch=compute_89,code=sm_89 \
  -gencode arch=compute_90,code=sm_90 -gencode arch=compute_90,code=compute_90 -o app app.cu   # last pair: PTX for newer GPUs
# CMake: -DCMAKE_CUDA_ARCHITECTURES="60-real;70-real;80-real;89-real;90" (plain numbers embed PTX for each)   PyTorch extensions: TORCH_CUDA_ARCH_LIST="6.0;7.0;8.0;8.9;9.0+PTX"
```

- **Toolkit limits** (generic; check with `nvcc --list-gpu-arch`): sm_89 and sm_90 need CUDA ≥ 11.8; CUDA 13 drops sm_60 and sm_70, so P100, V100, and V100x code needs a 12.x toolkit.
- **Driver**: on a GPU node the `nvidia-smi` header shows the highest CUDA version the driver supports; binaries from a newer toolkit may fail there with `CUDA driver version is insufficient` (generic).
- **Host code** on GPU nodes follows the CPU table: A100 nodes are Zen 3, L40 nodes Granite Rapids, H200 nodes Zen 5. Frameworks and conda CUDA stacks: DEEP-LEARNING.md.

## Math and other libraries

- **MKL** comes with the Intel compilers, alongside IPP and LINPACK.
- **LAPACK** (`module avail LAPACK`) has static and shared builds. `gcc ... -llapack_pic` links the static library built with PIC. Its static BLAS is not PIC: on ``libblas.a(...) relocation R_X86_64_32 against `.rodata' can not be used when making a shared object; recompile with -fPIC``, link `-l:libblas.so.3` instead.
- **Others on the index** (as of Sept 2026): openblas, FFTW, GSL, Eigen, boost, gflags, glog, glpk, Qt, OpenCV, seqan, FFmpeg, lz4, libpng, libjpeg-turbo, libwebp; the handout adds hdf5 and zlib. Not every module name is stated: search with `module spider <name>`. Library modules can be compiler-specific (an old listing has `fftw/3.3.4/gnu` and `fftw/3.3.4/intel`): link the variant built with your compiler.
- **Threads**: OpenMP and BLAS code you build follows ground rule 2 in SKILL.md (export `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` from the allocation).
- **Temp and log files**: code should honor `TMPDIR`. glog's manual gives `/tmp` as its default log location; set `GLOG_log_dir` (or `--log_dir`): lscratch for throwaway logs, /data to keep them.

## Debuggers, profilers, linters

- `gdb` comes with the system GCC, and the Intel suite includes its debugger. The index's "Debugging" section lists only shellcheck: run it on job scripts before handing them to the user (`module spider shellcheck`).
- NIH documents no valgrind, perf, Nsight Systems/Compute, cuda-gdb, compute-sanitizer, VTune, DDT/Forge, or TotalView. Check `module spider <tool>` and the CUDA module's bin directory (`ls "$(dirname "$(which nvcc)")"`) before promising one.
- Watching a running job's CPU, memory, and GPU use: UTILITIES.md.

## Java and Maven

JDKs live in `/usr/local/Java`; `module load java/<ver>` (`module avail java`) sets `JAVA_HOME`, `PATH`, and `LD_LIBRARY_PATH`. The options on [java.html](https://hpc.nih.gov/development/java.html) apply to any Java tool in a job:

```bash
export JAVA_TOOL_OPTIONS="-Djava.net.useSystemProxies=true"   # the JVM ignores the node's proxy otherwise
java -Xmx12g -XX:ParallelGCThreads=2 -Djava.io.tmpdir=/lscratch/$SLURM_JOB_ID \
     -Djava.awt.headless=true -jar app.jar                      # e.g. in a --mem=16g job with lscratch
```

- `-Xmx` caps only the heap; keep it well below `--mem`, since the JVM also uses memory outside the heap (generic).
- `-XX:ParallelGCThreads=2`: otherwise the JVM sizes garbage collection to the CPUs it detects, which "can easily consume most of the available CPUs". Adjust within the allocation.
- `-Djava.io.tmpdir`: genomic Java tools fill `/tmp`. `-Djava.awt.headless=true`: for tools that fail without an X11 display or keyboard. `-server`: recommended for long runs.
- **Maven**: `module load maven` (sets `M2_HOME` and `M2`, loads a java module). The page is silent on the proxy and `~/.m2`. Generic Maven: keep the local repository off /home with `-Dmaven.repo.local=/data/$USER/m2/repository`; if downloads fail even with `JAVA_TOOL_OPTIONS` set, give Maven a `<proxy>` built from `$https_proxy` in a settings file passed with `mvn -s`. Ant is also on the index.

## Other languages

Package locations below replace home-directory defaults; export them per session or in job scripts, not in dotfiles. Versions quoted are the development index's (as of Sept 2026).

- **Julia**: module `julialang` (identical to `julia`); packages install per user into the depot `~/.julia`.
  - The depot "can grow quite large": with the user's go-ahead, move it as the page does (`cd ~; mv .julia /data/$USER/.julia; ln -s /data/$USER/.julia`).
  - The module sets `JULIA_CPU_TARGET="generic;haswell;broadwell;skylake;cascadelake;znver3"` so precompiled code should run on all node types. For `Illegal instruction` or segfaults the page says to try a fresh cache (caches from before May 2024 lack these targets): with the user's OK, delete `~/.julia/compiled` and precompile again.
  - Set `OMP_NUM_THREADS` and `OPENBLAS_NUM_THREADS`; with `Distributed`, set both to 1 and use `addprocs(parse(Int, ENV["SLURM_CPUS_PER_TASK"]))`. Batch: `julia --project=$HOME/.julia/environments/<env> script.jl`.
- **Perl**: system perl by default, newer versions as modules, many CPAN modules preinstalled (check the page's table or `perl -MName -e1` first). Install with cpanm in a session with memory (the page uses `--mem=20g`). The page appends its variables to `~/.bashrc`; do that only with the user's OK, since a file you source (below) works without touching dotfiles. Modules that won't compile: the user emails staff.

```bash
cat > /data/$USER/perl-env.sh <<'EOF'   # quoted heredoc: variables expand when sourced
export LOCALPERL=/data/$USER/perl       # the page uses ~/perl
export PERL5LIB=$LOCALPERL:$LOCALPERL/lib/perl5 PERL_CPANM_HOME=$LOCALPERL/cpanm
export PERL_CPANM_OPT="-l $LOCALPERL" PATH=$LOCALPERL/bin:$PATH
EOF
source /data/$USER/perl-env.sh && mkdir -p "$PERL_CPANM_HOME" && cpanm TableData
```

- **PyPy**: `module avail pypy`; versions read `<python>-<pypy>` (index: 3.8-7.3.9). The modules provide `virtualenv`: create the env under /data, `source <env>/bin/activate`, then `pip install`. C extensions "may not compile unmodified".
- **Go, Rust, Node.js, Ruby**: on the index (golang, rust, nodejs with "module name: nodejs", Ruby) but without NIH pages; confirm names with `module spider`. Point their caches off /home (generic; run `module show` first so you don't override what a module sets), and pass `-j "${SLURM_CPUS_PER_TASK:-2}"` to `cargo build`:

```bash
export GOPATH=/data/$USER/go GOCACHE=/lscratch/$SLURM_JOB_ID/go-build CARGO_HOME=/data/$USER/cargo
export NPM_CONFIG_PREFIX=/data/$USER/npm-global NPM_CONFIG_CACHE=/data/$USER/npm-cache
export PATH=$GOPATH/bin:$CARGO_HOME/bin:$NPM_CONFIG_PREFIX/bin:$PATH
```

## Editors and Stow

- **Editors** on the index: vim, neovim, emacs (with ESS), nano, nedit (needs X11), SciTE. VS Code: ACCESS.md.
- **Stow** (`module load stow`) symlinks a built tree into a directory already on the PATH: from the directory holding `myapp/`, `stow --target $HOME/.local myapp`; undo with `stow -D --target $HOME/.local myapp`. That changes every later session of the user's, so ask first; a modulefile (MODULES.md) is opt-in and versioned.

## Stale advice on the official pages

- The [development index](https://hpc.nih.gov/development/) shows one version per tool, several old (GCC 10.2.0, Intel 2019.4.243, CMake docs for v3.16) → `module avail <name>` shows what is installed.
- compilers.html: `-static--libg++` → `-static-libstdc++`; it lists `g77`, long gone from GCC; its Intel link is the retired Parallel Studio docs; it never mentions oneAPI or NVHPC.
- autotools.html: "Red Hat/CentOS" and `autoconf/2.69`, `m4/1.4.17`, `libtool/2.4.6` → the OS is Rocky 8, and newer module versions exist.
- MPI.html: written for OpenMPI 4.x and MVAPICH2 2.3.x; its InfiniBand features (ibfdr, ibhdr, ibhdr100) predate ibhdr200 and ibndr200, and the hardware page gives every node type one; the index calls OpenMPI "Ethernet MPI". For OpenMPI 5 or mvapich 4, confirm the plugin with `srun --mpi=list`.
- The userguide's and multinode policy's `--constraint=x2650` (and `x2695`) examples name node types missing from the hardware page (x2695 was removed in April 2026) → use a feature from the CPU table.
- java.html: the `java/1.8.0_92` example is old, and "symlinked to /usr/local/java" conflicts with the Maven sample's `/usr/local/java/jdk-12.0.1` → trust `$JAVA_HOME` after `module load java`.
- julia.html: `export JULIA_PROJECT==...` has a doubled `=`; `rm -rf ~/.julia/new_environment` misses the env's real path `~/.julia/environments/new_environment`; examples use julialang/1.7.1 (index: 1.11.5); `JULIA_CPU_TARGET` (May 2024) has no Zen 4, Zen 5, or Granite Rapids entry.
- perl.html: its `cat << EOF >> ~/.bashrc` is unquoted, so `$LOCALPERL` and `$PATH` expand at write time (`PERL5LIB` becomes `:/lib/perl5` and PATH is frozen) → use the quoted env file above.
- pypy.html runs on the login node with `/spin1` paths and `pypy/2.7-7.3.5`; stow.html runs on Helix → do both in the session, under /data.

## Going further

- https://hpc.nih.gov/development/ — index of compilers, build tools, libraries, languages, and MPI with featured versions (`#compilers`, `#compiler_tools`, `#libraries`, `#languages`, `#mpi`, `#debugging`, `#editors`)
- https://hpc.nih.gov/development/compilers.html — GCC and Intel suites, static runtime flags
- https://hpc.nih.gov/development/MPI.html — OpenMPI and MVAPICH, launch lines, UCX warnings
- https://hpc.nih.gov/development/autotools.html · https://hpc.nih.gov/development/LAPACK.html · https://hpc.nih.gov/development/cuDNN.html
- https://hpc.nih.gov/development/java.html — JVM memory, tmpdir, GC threads, headless mode, proxy
- https://hpc.nih.gov/training/handouts/managing-personal-software.pdf — autotools and CMake walk-throughs, build variables, personal Lua modulefile
- https://hpc.nih.gov/docs/diy_installation/#manual — manual installs and when to contact staff
- https://hpc.nih.gov/systems/hardware.html — node features and CPU models; https://hpc.nih.gov/docs/biowulf_tools.html#nodetype — `nodetype`
- Languages: https://hpc.nih.gov/apps/julia.html#notes · https://hpc.nih.gov/apps/perl.html#personal · https://hpc.nih.gov/apps/pypy.html#envs · https://hpc.nih.gov/apps/Maven.html · https://hpc.nih.gov/apps/stow.html · https://hpc.nih.gov/apps/Matlab.html · https://hpc.nih.gov/apps/mathematica.html · https://hpc.nih.gov/apps/SAS.html
- Upstream: https://slurm.schedmd.com/mpi_guide.html (Slurm MPI plugins) · https://gcc.gnu.org/onlinedocs/ · http://docs.nvidia.com/cuda/
- Live help: `module spider <name>`, `module show <name>`, `gcc --version`, `nvcc --list-gpu-arch`, `srun --mpi=list`, `nodetype $(hostname -s)`, `freen`.
