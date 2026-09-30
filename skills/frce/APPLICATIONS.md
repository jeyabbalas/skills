The scientific applications FRCE documents under Scientific Software: how the application pages work, an index with each application's module and FRCE specifics, reference data on disk, fixes for the official example scripts, and notes by area (sequencing and Dragen, cryo-EM and CryoSPARC, AlphaFold and structural biology, computational chemistry, image analysis, MATLAB). You write and check the scripts; every command here that submits, cancels, or changes a job is the user's to run (ground rules in SKILL.md). Finding, loading, and requesting software: MODULES.md. Job flags, partitions, and GPU requests: JOBS.md. GUIs over X11: INTERACTIVE.md (X11 applications); in the browser: ONDEMAND.md. ML frameworks: DEEP-LEARNING.md. Ollama: LLM-INFERENCE.md. Containers: CONTAINERS.md. CCBR pipelines and their references: WORKFLOWS.md.

Table of contents

- [How the application pages work](#how-the-application-pages-work)
- [Application index](#application-index)
- [Fixing the official examples](#fixing-the-official-examples)
- [Sequencing and genomics](#sequencing-and-genomics)
- [Cryo-EM](#cryo-em)
- [Structural biology and AlphaFold](#structural-biology-and-alphafold)
- [Computational chemistry](#computational-chemistry)
- [Image analysis](#image-analysis)
- [MATLAB](#matlab)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## How the application pages work

- Each page under [Scientific Software](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware) has a "Slurm script" section, written only "when the FRCE administrators have knowledge to write one" (several hold terminal transcripts instead), and collapsed build notes: the staff's install into `/mnt/nasapps/production/<app>/<version>`.
- The build notes name the version installed then, which may be gone or not the default, and AppDB often names another: the index lists what's installed.
- The examples use a staff account's paths under `/scratch/cluster_scratch`, `username@mail.nih.gov`, and inputs that aren't on FRCE (`in.bam`, the Vina `1iep_*` files): substitute the user's own.

## Application index

Versions are `module avail` output (live, Sept 2026), "default" where the modulefile sets one; recheck with `module avail NAME` and pin (MODULES.md (Loading and pinning versions)).

| Application | Module | FRCE specifics | Page |
|---|---|---|---|
| ANNOVAR | `annovar/2020Jun07` | databases in `$ANNOVAR_DATA` (hg19 only), examples in `$ANNOVAR_HOME/example` | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/ANNOVAR) |
| BamTools | `bamtools/2.5.2` | — | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/BamTools) |
| bcftools | `bcftools` 1.16, 1.21, 1.22 | a transcript, no script | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/bcftools) |
| bcl2fastq | `bcl2fastq2/2.20.0`, not the page's `bcl2fastq/2.20.0` | Illumina academic license | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/bcl2fastq) |
| bcl-convert | `bcl-convert` 4.2.7, 4.3.6, 4.4.4 | whole-node `--exclusive` example | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/bclconvert) |
| BEDOPS | `bedops/2.4.41` | — | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/bedops) |
| bedtools | `bedtools` 2.27.1, 2.30.0, 2.31.1 | its script also runs BEDOPS's `bedmap` | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/bedtools) |
| Bowtie, Bowtie2 | `bowtie/1.3.1`; `bowtie2` 2.5.1, 2.5.4 | no script (`???`) | [1](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/bowtie), [2](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/bowtie2) |
| BWA | `bwa/0.7.17` (also `bwa-mem2/2.3`) | — | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/bwa) |
| Conpair | `conpair/0.2` | genome FASTA under `/SeqIdx/igenomesdb` (AppDB) | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/conpair) |
| GATK | `gatk` 4.3.0.0, 4.6.1.0 | a transcript run on the login node | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/GATK) |
| goleft | `goleft` 0.2.5, 0.2.6 | a transcript | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/goleft) |
| HTSlib | `htslib` 1.9, 1.16, 1.21 | sample files under `/mnt/nasapps/production/htslib/` | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/htslib) |
| samtools | `samtools` 1.8, 1.15.1, 1.16.1, 1.21, 1.22.1 | a transcript | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/GenomicsHighThroughputSequencing/samtools) |
| CryoSPARC | none | a per-lab VM that submits to FRCE | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/CryoEM/CryoSPARC) |
| CTFFIND | `ctffind` 4 (default), 4.1.14, 5.0.2 | the script calls `ctffind3`, which the default lacks | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/CryoEM/ctffind) |
| EMAN2 | `EMAN2/2.91` | GUI in an X11 GPU session | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/CryoEM/EMAN2) |
| EMReady | `emready/2.0`; `emready2/latest` | GPU: the page uses two V100s; an example map in `/mnt/nasapps/production/emready/examples/` | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/CryoEM/EMready) |
| crYOLO | `cryolo/1.9.6` | GUI `cryolo_gui.py` (X11 or OnDemand) | [page](https://ncifrederick.cancer.gov/fredi/node/746) |
| AlphaFold | `alphafold/2.3.2_conda` (default), `alphafold/3.0.1`; also `alphafold3/3.0.1` | AF2 databases in `/mnt/alphafold/2.3.2` | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/StructuralBiology/AlphaFold) |
| AlphaPulldown | `alphapulldown` 0.30.7, 1.0.4 | no script | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/StructuralBiology/AlphaPulldown) |
| CCP4 | `ccp4` 8.0.010, 9.0.005, 9.0.011 | GUI `ccp4i2` needs X | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/StructuralBiology/CCP4) |
| ColabFold | `colabfold/1.5.5` | MSAs from a public server | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/StructuralBiology/colabfold) |
| Amber | `amber` 22, 24 | commercial license; GPU example broken | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/ComputationalChemistry/Amber) |
| Gaussian | none | not on FRCE; on Biowulf | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/ComputationalChemistry/Gaussian) |
| GROMACS | `gromacs` 2023.1, 2023.3, 2024.3, 2025.3 | 2025.3 has `gmx`, no `gmx_mpi`; no script | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/ComputationalChemistry/Gromacs) |
| AutoDock Vina | `autodock_vina/1.1.2` | — | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/ComputationalChemistry/AutodockVina) |
| cellpose | `cellpose` 3.0.11, 4.0.6, 4.2.1, and lab variants | GPU training example | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/ImageAnalysis/cellpose) |
| MATLAB | `matlab` R2024b, R2025a | NCI site license | [page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/UncategorizedSoftware/MATLAB) |

Six category pages list no applications (Linkage/Phylogenetics, Machine/Deep Learning, Mass Spectrometry, Molecular Dynamics, Systems Biology, X-Ray/NMR), and `module avail` lists about 415 module versions (live, Sept 2026), far more than the pages cover, among them `boltz`, `chai1`, `rfdiffusion`, `ProteinMPNN`, `openfold`, `esm`, `relion`, `motioncor3`, `cryodrgn`, `topaz`, `model_angelo`, `phenix`, `namd`, `openmm`, `msfragger`, `fragpipe`, `cellranger`, `STAR` (2.7.10b), `salmon`, `kraken2`, and `dorado`. For one with no FRCE page, `module help NAME`, `module display NAME`, and AppDB's "How to run" line are the documentation; copy names exactly (MODULES.md (Loading and pinning versions)).

### Reference data

No FRCE page documents these (live, Sept 2026, seen from the login node; `ls` them from your session):

- `/SeqIdx`: genomes (`igenomesdb`, i.e. iGenomes: AppDB's Conpair entry names `igenomesdb/Homo_sapiens/Ensembl/GRCh38/Sequence/WholeGenomeFasta/genome.fa` and its GRCh37 twin; `fastadb`), indexes (`bwadb`, `bowtiedb`, `bowtie2db`, `blastdb`, `blatdb`, `dragmap`), and tool databases (`annovardb`, `alphafold3`, `fastq-screen`, `homer`, `gtdbtk`, `interproscan`, `kronatools`, `liftOver`, and more). Nothing states builds or dates: `ls /SeqIdx/NAME` and read any README before relying on one.
- `/mnt/alphafold`: a directory per version (`2.0.0` through `2.3.2`, `3.0.1`, `alphafold3`), top-level database directories (`bfd`, `uniref90`, `pdb70`, …), and a `README`.
- `$ANNOVAR_DATA` (`/mnt/nasapps/production/annovar/2020Jun07/data`, set by the module) holds only `hg19` (the page documents `refGene`, `cytoBand`, `exac03`, `avsnp147`, and `dbnsfp30a` there). For hg38, check `/SeqIdx/annovardb` (contents unchecked) or ask: "Additional databases can be installed upon request".
- CCBR's genomes and indices: WORKFLOWS.md (CCBR pipelines on FRCE). Ollama models: LLM-INFERENCE.md.
- ABCS mirrors 50+ public databases (GenBank, PDB, UniProt, dbSNP, KEGG, …) behind a web query tool, [bioData](https://biodata-abcc.ncifcrf.gov/) (NIH network), not as files on FRCE. Oracle and MariaDB servers are reachable from compute nodes; the admins can put the user in touch with their DBAs for accounts ([Scientific Database Support](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/ScientificDatabaseSupport)).

Before downloading a large reference, check these places and ask the admins; otherwise put it in a group share or cluster scratch (TRANSFER.md (Downloads on the cluster)).

## Fixing the official examples

Fixes that apply to several pages; per-application fixes are in the sections below.

| On the page | Where | Fix |
|---|---|---|
| `--ntasks=N` for a threaded program, most passing it `$SLURM_NTASKS` or `$SLURM_NPROCS`: Slurm may spread the tasks over nodes while the program runs on one | AlphaFold, ANNOVAR, AutoDock Vina, cellpose, ctffind, EMAN2 | `--nodes=1 --cpus-per-task=N`, and pass `$SLURM_CPUS_PER_TASK` |
| `$SLURM_CPUS_PER_TASK` without `--cpus-per-task`: unset, so the option swallows the next argument | BWA | add `#SBATCH --cpus-per-task=N` |
| `module load load NAME` | bcftools, samtools | `module load NAME` |
| no `#!` line: sbatch refuses the script | cellpose | `#!/bin/bash` as line 1 |
| `???` or an empty script section | GROMACS, Bowtie, Bowtie2, AlphaPulldown | write one, modeled on Biowulf's page for the app (translate with FROM-BIOWULF.md) |
| names copied from elsewhere: a dependency on `alphafold_split.sh`, which the page never creates; `--job-name=bcl2fastq` | AlphaFold, BEDOPS | the predict script ([Structural biology and AlphaFold](#structural-biology-and-alphafold)); the job's own name |
| an unpinned `module load NAME` | every page | pin the tested version (MODULES.md (Loading and pinning versions)) |
| missing `--time`, `--mem`, or both | Amber, colabfold, CCP4 GUI, ctffind, EMAN2 GUI, MATLAB | set both (JOBS.md (Flags and defaults)) |
| staff paths and `--mail-user=username@mail.nih.gov` | AlphaFold, EMAN2 | the user's directory under `/scratch/cluster_scratch/$USER`; the user's own address, or no `--mail-user` |
| a transcript a staff account ran on the login node | GATK | run it in a job or session |
| a fixed `v100` or `p100` | AlphaFold, Amber, cellpose, EMReady | keep it if the job fits, or any type with enough memory (DEEP-LEARNING.md (Choosing a GPU)) |

## Sequencing and genomics

ANNOVAR, with the page's first command made runnable (its relative `humandb/` and `example/` paths don't exist in a job's working directory):

```bash
#!/bin/bash
#SBATCH --job-name=annovar
#SBATCH --partition=norm
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32g
#SBATCH --time=1:00:00
# annovar.sh — the user submits it; the working directory is a placeholder
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true   # `module` in batch shells: MODULES.md
module load annovar/2020Jun07
cd /scratch/cluster_scratch/$USER/annovar
cp -r "$ANNOVAR_HOME/example" .
table_annovar.pl example/ex1.avinput "$ANNOVAR_DATA/hg19" -buildver hg19 -out myanno -remove \
  -protocol refGene,cytoBand,exac03,avsnp147,dbnsfp30a -operation gx,r,f,f,f -nastring . -csvout -polish \
  -xref example/gene_xref.txt -thread "$SLURM_CPUS_PER_TASK"
```

The page's second command needs hg38 databases, which `$ANNOVAR_DATA` lacks: find an hg38 humandb first ([Reference data](#reference-data)).

- BWA: the page indexes a SOLiD color-space `.csfasta` reference for `bwa aln`, but BWA "Disabled the color-space alignment" in 0.6.1 ([NEWS](https://github.com/lh3/bwa/blob/master/NEWS.md)): index a nucleotide FASTA, and use `bwa mem -t "$SLURM_CPUS_PER_TASK"` for current reads.
- bedtools: the script's `bedmap` lines need `module load bedops/2.4.41` too, and the `--ec` line's comment says "no error checking", though `--ec` turns checking on.
- bcl2fastq: the page's `module load bcl2fastq/2.20.0` fails (the module is `bcl2fastq2`). bcl-convert is "the successor"; its page's 4.1.23 is gone. Keep its `--exclusive` (a whole node), or, on part of a node, set its thread options (`bcl-convert --help`) from `$SLURM_CPUS_PER_TASK`.
- Bowtie and Bowtie2 have no script: pass `-p "$SLURM_CPUS_PER_TASK"`.
- Conpair: the transcript saves the tumor pileup as `NA12878_tumor80x.gatk.pileup.txt` and then reads `NA12878_tumor80x.gatk.pileup`; use one name. Its documentation links point at GATK; the tool is [nygenome/Conpair](https://github.com/nygenome/Conpair).
- GATK: the jar is in `/mnt/nasapps/production/gatk/4.6.1.0/`; AppDB's location (`4.0.12.0`) is stale. Whether the module puts the `gatk` launcher on PATH and loads a Java is unchecked: `module display gatk/4.6.1.0` shows both, and GATK 4.6 needs Java 17 or later (`java/17`, not the bare `java` default: MODULES.md (Loading and pinning versions)).
- goleft: the transcript's `pgoleft` is `goleft`. HTSlib: its samples are in `/mnt/nasapps/production/htslib/samples/` or `/mnt/nasapps/production/htslib/1.21/samples` (the page says both); `ls` both.

### Dragen

- `dragen` holds "several servers for the exclusive use by the CCR Sequencing Facility", enforced by an account allow-list; the submit filter sets `--cpus-per-task=48` on every `dragen` job and turns a missing or unlimited `--time` into one year. `nci-dragen` is "1 Illumina Dragen V3 Server" (`dn100`), open to every account. Both live, Sept 2026 ([partitions](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/SlurmPartitionsFeatures); `scontrol show partition nci-dragen`).
- `dn100`'s node feature, `dragen-4.3.13`, presumably names its DRAGEN version (`sinfo -p dragen,nci-dragen -N -o '%N %c %m %f %T'`). Limits and default memory: JOBS.md (Partitions and walltime); the servers and their hyperthreads: HARDWARE.md (Large memory and Dragen).
- FRCE documents no DRAGEN install path, reference hash tables, or usage terms, so the user asks the admins before the first run (ACCESS.md (Support and requests)), although Slurm would accept the job.
- Biowulf has a partition with the same name but its own server and rules: the `nci_dragen_turbo` QOS and a local `/staging` disk ([nci-dragen.html](https://hpc.nih.gov/docs/nci-dragen.html)), and Biowulf pipelines `source /etc/profile.d/edico.sh`. Public code with these settings is Biowulf code; don't carry them to FRCE.

## Cryo-EM

CryoSPARC isn't on the cluster: each lab gets its own VM, which "has privileges to submit jobs to the FRCE cluster" as a service account, with file access through group membership. The page's steps, all requested by the user or the lab (forms: ACCESS.md (Support and requests)):

1. An AD service account with POSIX attributes, named `ncif-<lab>-cryosparc` or `ncif-<lab>-srv`.
2. An AD group with POSIX attributes holding the file owners and the service account (or add the account to an existing group).
3. The data shares: their files must become group-owned and group read/write; "The FRCE admins can make this change".
4. A ServiceNow Linux VM request, custom size: 8 CPUs, 24 GB memory, an 80 GB local disk at `/var/lib/mongo`, `fssrgd-qmlo05p:/shared-home` mounted as `/home`, `fssrgd-qmlo05p:/oel-apps` as `/mnt/nasapps`, plus the data shares; no user-access or firewall rules.
5. "The AppHosting team will install and configure CryoSPARC" and make one lab member Administrator.

The page is silent on cryoSPARC's academic license; as a rule the requester obtains licenses (MODULES.md (When software isn't installed)), so the lab settles it with the admins. Biowulf's per-user model (`csparc`) doesn't apply.

- EMAN2 GUI: the page's `srun --pty -p gpu --gres=gpu:1 --x11 bash` needs `--time` and `--mem` (X11: INTERACTIVE.md (X11 applications)). EMAN2 fails under XQuartz on a Mac: use NoMachine, as the page suggests, or an OnDemand desktop. The display program is `e2display.py`, not `e2display`.
- EMAN2 batch: `--threads=${SLURM_NTASKS}:/scratch/cluster_scratch/${USER}` doesn't parse, because `--threads` takes an integer (e2refine_easy.py). Use `--nodes=1 --cpus-per-task=30` and `--parallel=thread:$SLURM_CPUS_PER_TASK --threads=$SLURM_CPUS_PER_TASK`.
- EMReady: `-g '0,1'` names the job's two GPUs, which CUDA always numbers from 0. `emready2/latest` needs a V100 or newer (AppDB).
- CTFFIND: the page's here-document opens with a bare `<<`, a syntax error; write `<<EOF`. It calls `ctffind3`, but the default `ctffind/4` provides only `ctffind` (live, Sept 2026), whose `--old-school-input` takes the page's CTFFIND3-style lines. Pin `ctffind/4`.

## Structural biology and AlphaFold

The page splits AlphaFold 2 into a CPU job for the MSAs and a GPU job for the models, because in one job "the allocated GPU(s) are idle for the first part of the analysis". Its two scripts in one, with the fixes applied:

```bash
#!/bin/bash
#SBATCH --job-name=af2
#SBATCH --partition=norm
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128g
#SBATCH --time=8:00:00
#SBATCH --output=%x-%j.out
# af2.sh — STAGE=msa (CPU) or STAGE=predict (GPU); the user submits both stages (below)
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true
module load alphafold/2.3.2_conda             # pinned: a bare alphafold follows the default
D=/mnt/alphafold/2.3.2
W=/scratch/cluster_scratch/$USER/af2          # placeholder for the page's staff directory; holds target.fa
args=(--fasta_paths="$W/target.fa" --output_dir="$W/out" --model_preset=multimer
  --num_multimer_predictions_per_model=2 --db_preset=full --data_dir="$D"
  --pdb_seqres_database_path="$D/pdb_seqres/pdb_seqres.txt"
  --uniref30_database_path="$D/uniref30/UniRef30_2021_06/UniRef30_2021_06"
  --uniprot_database_path="$D/uniprot/uniprot.fasta" --uniref90_database_path="$D/uniref90/uniref90.fasta"
  --mgnify_database_path="$D/mgnify/mgy_clusters_2022_05.fa"
  --template_mmcif_dir="$D/pdb_mmcif/mmcif_files" --obsolete_pdbs_path="$D/pdb_mmcif/obsolete.dat"
  --bfd_database_path="$D/bfd/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt"
  --max_template_date=2020-05-14)
case "${STAGE:?set STAGE=msa or STAGE=predict}" in
  msa)     run_alphafold_msa.py "${args[@]}" --run_relax=false --use_gpu_relax=false ;;
  predict) run_alphafold_predict.py "${args[@]}" --use_precomputed_msas=true --run_relax=true --use_gpu_relax=true ;;
  *)       echo "unknown STAGE=$STAGE" >&2; exit 1 ;;
esac
```

```bash
# on the FRCE login node, in /scratch/cluster_scratch/$USER/af2 — the user runs:
jid=$(sbatch --parsable --export=ALL,STAGE=msa af2.sh)
sbatch --dependency=afterok:"$jid" --export=ALL,STAGE=predict --partition=gpu --gres=gpu:v100:1 --cpus-per-task=4 af2.sh
```

- Keep the pin: the page's bare `alphafold` gets whatever the default is (MODULES.md (Loading and pinning versions)), and AppDB already calls 3.0.1 production. The module provides `run_alphafold.py`, `run_alphafold_msa.py`, and a `run` shell function (live, Sept 2026); `run_alphafold_predict.py` is unchecked, so run `command -v run_alphafold_predict.py` in your session before handing over the split, and if it's missing, use the page's single-script `run_alphafold.py` on a GPU.
- Check the flags before handing over: upstream 2.3.2 takes `--db_preset=full_dbs|reduced_dbs` and `--models_to_relax`, not the page's `full` and `--run_relax`, but FRCE's split wrappers are local scripts that may define their own (unchecked). In your session, run `module load alphafold/2.3.2_conda && run_alphafold_msa.py --helpfull 2>&1 | grep -E -A2 'db_preset|relax'` and use what it lists.
- `--max_template_date=2020-05-14` is the CASP14 cut-off and hides newer templates. Use a recent date unless reproducing CASP14.
- Prediction barely uses CPUs, and V100 nodes have the fewest CPUs per GPU (HARDWARE.md (GPUs)), hence `--cpus-per-task=4` rather than the page's 8. Large complexes need a card with more memory (`a100`, `h200`).

AlphaFold 3 (two modulefiles: the index; AppDB names the programs `af3` and `run_alphafold`) has candidate databases in `/mnt/alphafold/3.0.1`, `/mnt/alphafold/alphafold3`, and `/SeqIdx/alphafold3` (contents unchecked; `cat /mnt/alphafold/README` first). FRCE documents no AF3 usage or weights: compare `module display` of both modules before writing a script. Each user obtains the model parameters from Google DeepMind under its terms and keeps them private. Biowulf's [AlphaFold 3 page](https://hpc.nih.gov/apps/alphafold3.html) shows the CPU-pipeline, GPU-inference split, and needs translating (FROM-BIOWULF.md).

ColabFold: `colabfold_batch input.fasta outdir` sends the sequences to the public MMseqs2 server (`api.colabfold.com`, the default) for MSAs, and they leave NIH, since compute nodes reach the internet directly (TRANSFER.md (Downloads on the cluster)): get the user's OK for unpublished sequences. No local ColabFold databases are documented (AppDB has `mmseqs2` for `colabfold_search`); ask the admins. FRCE's install keeps the weights in `~/colabfold`, several GB of home. Prefer a batch job to the page's `srun`; a rerun into the same output directory skips finished predictions.

- CCP4: `ccp4i2` "requires an X-Windows connection", but the page's `srun` lacks `--x11`: add it (INTERACTIVE.md (X11 applications)) or use an OnDemand desktop. The batch `superpose` example asks 8 h and 128g, the AlphaFold scripts' values: size it down. CCP4 carries an academic license (AppDB lists `academic_software_licence.pdf`).
- AlphaPulldown: pin `alphapulldown/0.30.7` or `/1.0.4` (AppDB's 0.30.6 is gone); no FRCE script; upstream: [KosinskiLab/AlphaPulldown](https://github.com/KosinskiLab/AlphaPulldown).

## Computational chemistry

- Amber: the CPU script's `--ntasks=8` with `mpirun pmemd.MPI` is right for MPI. The GPU script is broken: `#SBATCH -gres=gpu:v100:1` has one dash, so sbatch errors or misreads it, and it runs the CPU engine `pmemd.MPI`, leaving the GPU idle. Use `#SBATCH --gres=gpu:v100:1`, `--ntasks=1`, and `pmemd.cuda -O -i mdin -o mdout -inf mdinfo -x mdcrd -r restrt`; `amber/24`, the default, has `pmemd.cuda` and `pmemd.cuda.MPI` (live, Sept 2026). Its license is commercial (MODULES.md (When software isn't installed)), and its page names no group restriction; if in doubt, the user asks the admins.
- Gaussian: "no group has stepped up to purchase the `gaussian` license. It is available on the Biowulf cluster", where it needs membership in the `gaussian` group ([Gaussian](https://hpc.nih.gov/apps/Gaussian.html); the user asks NIH HPC staff); inputs and outputs move by transfer (TRANSFER.md (Data from Biowulf)).
- GROMACS: the job script is `???`. The page documents a 2024.3 build with MPI and CUDA, but the default `gromacs/2025.3` is a thread-MPI build (live, Sept 2026), whose GPU support `gmx --version | grep -E 'GPU support|MPI library'` shows. For one GPU: `--nodes=1 --ntasks=1 --cpus-per-task=16 --gres=gpu:l40s:1`, then `gmx mdrun -deffnm md -ntmpi 1 -ntomp "$SLURM_CPUS_PER_TASK" -nb gpu`. Multi-node runs need an MPI build (`module load gromacs/2024.3 && command -v gmx_mpi`) and JOBS.md (MPI and multinode jobs).
- AutoDock Vina: pass `--cpu "$SLURM_CPUS_PER_TASK"`. The page links the 1.2 docs (its `1iep_*` inputs are their basic docking example), but the only module is 1.1.2: check options against `vina --help`.

## Image analysis

- cellpose: besides the shebang and `--ntasks` fixes ([Fixing the official examples](#fixing-the-official-examples)), pin a numbered version. The page builds 3.0.11; the modules add 4.0.6, 4.2.1, and lab variants (`cd8_gh2ax`, `phenotype3D`, `phenotype3D_multi`) with no default set, so a bare `module load cellpose` follows the sort order to a variant (`module avail -d cellpose` shows which). `cellpose` with no arguments opens the GUI (X11 or an OnDemand desktop).

## MATLAB

- NCI's site license covers MATLAB, Simulink, and "a considerable number of toolboxes".
- "MATLAB is extremely resource-intensive and should not be run on the head node": run it in a job with explicit CPUs and memory.
- GUI: OnDemand, "a simpler interface" per the page (the MATLAB app, a desktop, or Jupyter's MATLAB kernel: ONDEMAND.md), or X11 from an `srun --x11` session (INTERACTIVE.md (X11 applications)); startup "will take a few minutes".
- Command line, which "will start much more quickly": in a session, `module load matlab/R2025a; matlab -nodisplay`.
- Batch, with the page's script fixed ([Stale advice](#stale-advice-on-the-official-pages)):

```bash
#!/bin/bash
#SBATCH --job-name=matlab
#SBATCH --partition=norm
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16g
#SBATCH --time=1:00:00
# matlab.sh — the user submits it from the directory holding hello.m (e.g. disp('Hello World!'))
set -euo pipefail
source /etc/profile.d/modules.sh 2>/dev/null || true
module load matlab/R2025a                     # or matlab/R2024b
matlab -nodisplay -batch "maxNumCompThreads($SLURM_CPUS_PER_TASK); hello"
```

- `maxNumCompThreads` caps MATLAB's implicit threading at the allocation (ground rule 2). For explicit parallelism, `parpool('Processes', N)` with N at most `$SLURM_CPUS_PER_TASK`.

## Stale advice on the official pages

- [Structural Biology](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/StructuralBiology) links crYOLO as `/node/746`, which lands on a login page → https://ncifrederick.cancer.gov/fredi/node/746.
- [MATLAB](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/UncategorizedSoftware/MATLAB): the command-line section "assumes the use of X11 forwarding" (copied from the GUI section) and links a 404 (`/fredi/node/362`) → [Interactive Access](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/InteractiveAccess). Its batch script mixes in terminal output and R code → the script in [MATLAB](#matlab).
- Versions on the pages and in AppDB drift from what's installed (live, Sept 2026): bcl-convert 4.1.23, MATLAB R2024a and R2022b, AlphaPulldown 0.30.6, and BEDOPS 2.4.35 are gone, and several applications have more than one version → `module avail NAME`, then pin. The bcl2fastq and CTFFIND pages name a module and a program that don't exist, and ANNOVAR's hg38 command needs databases `$ANNOVAR_DATA` lacks ([Sequencing and genomics](#sequencing-and-genomics), [Cryo-EM](#cryo-em)).
- [GROMACS](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/ComputationalChemistry/Gromacs) links the bare `gromacs.org` domain, which didn't resolve from the NIH network (Sept 2026) → https://www.gromacs.org/.

## Going further

- FRCE: [Scientific Software](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware) (categories linked from it) · [Software Licenses](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/WorkflowDevelopmentSoftware/CompilersandScriptingLanguages0) · [Scientific Database Support](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/ScientificDatabaseSupport) · [AppDB](https://appdb.ncifcrf.gov/) (NIH network), e.g. [AlphaFold](https://appdb.ncifcrf.gov/software/AlphaFold).
- Biowulf application pages as models, which need translating (FROM-BIOWULF.md: module names, lscratch, swarm, `/fdb`): [AlphaFold 2](https://hpc.nih.gov/apps/alphafold2.html) · [AlphaFold 3](https://hpc.nih.gov/apps/alphafold3.html) · [ColabFold](https://hpc.nih.gov/apps/colabfold.html) · [GROMACS](https://hpc.nih.gov/apps/gromacs.html) · [AMBER](https://hpc.nih.gov/apps/AMBER.html) · [Bowtie2](https://hpc.nih.gov/apps/bowtie2.html) · [EMAN2](https://hpc.nih.gov/apps/EMAN2.html) · [MATLAB](https://hpc.nih.gov/apps/Matlab.html) · [cryoSPARC](https://hpc.nih.gov/nih/cryosparc/) (a different model).
- Upstream: [AlphaFold](https://github.com/google-deepmind/alphafold) · [ColabFold](https://github.com/sokrypton/ColabFold) · [cellpose](https://cellpose.readthedocs.io/en/latest/) · [ANNOVAR](https://annovar.openbioinformatics.org/).
- Live: `module avail NAME`, `module help NAME`, `module display NAME`, `ls /SeqIdx /mnt/alphafold`, `sinfo -p dragen,nci-dragen`.
