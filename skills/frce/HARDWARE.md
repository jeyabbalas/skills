FRCE's compute hardware as Slurm reported it in Sept 2026: CPU node types (generation, cores, memory); GPU types (`--gres` name, compute capability, per-GPU share of CPUs and memory); which types sit in which partitions; features for `--constraint`; the large-memory and Dragen servers; and the interconnect. Every command here is a read-only query you may run in your session (ground rules in SKILL.md). Writing the requests (`--gres` syntax, limits, default memory): JOBS.md. Choosing a GPU for machine learning: DEEP-LEARNING.md. Instruction sets and portable builds: DEVELOPMENT.md. Nodes move between partitions: confirm with `freen` or `sinfo` before relying on a count.

Table of contents

- [Node types](#node-types)
- [GPUs](#gpus)
- [Partitions and node types](#partitions-and-node-types)
- [Features and constraints](#features-and-constraints)
- [Large memory and Dragen](#large-memory-and-dragen)
- [Interconnect](#interconnect)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Node types

CPU nodes in service (live, Sept 2026), with generations from Intel's specifications. Slurm's CPUs are cores (JOBS.md (Flags and defaults)); memory is Slurm's usable figure, the largest `--mem` the node accepts.

| Nodes | CPUs | Generation | Cores | Memory | GB per core | Feature |
|---|---|---|---|---|---|---|
| 66 | 2 × Xeon Gold 6342 | Ice Lake (3rd Gen Xeon Scalable) | 48 | 250g | 5.2 | `x6342` |
| 32 | 2 × Xeon Gold 6150 | Skylake (1st Gen Xeon Scalable) | 36 | 755g | 21 | `x6150` |
| 7 | 2 × Xeon 6740P | Granite Rapids (Xeon 6) | 96 | 2015g | 21 | `x6740P` |
| 2 | 4 × Xeon Platinum 8268 | Cascade Lake (2nd Gen Xeon Scalable) | 96 | 3023g | 31.5 | `x8268` |

The login node (Xeon Gold 6342, 48 cores, 256 GB) and the transfer node (Xeon Gold 6150, 36 cores, 384 GB) are shared hosts, not for jobs (SKILL.md).

- **Memory per core ranges from 5.2 to 31.5 GB.** Slurm starts a job on any node in its partition with enough free CPUs and memory, so the request decides the type unless a feature pins it ([Features and constraints](#features-and-constraints)); which types hold how much: [Large memory and Dragen](#large-memory-and-dragen). A job asking for much more than 5 GB per CPU can still land on a 6342 node and hold memory whose cores then sit idle; ask for what the job needs (MONITORING.md (Sizing the next run)). Without `--mem`, memory grows with the CPUs requested (JOBS.md (Flags and defaults)).
- **CPUs per job.** A request for more CPUs per node than any node in the partition has is refused at submission (the message: TROUBLESHOOTING.md (Error-string index)).

```bash
# on the compute node (inside your session): one line per partition and identical node group
sinfo -e -o '%.10P %.5D %.5c %.9m %.8z %.24G %f'   # partition, nodes, CPUs, memory (MiB), sockets:cores:threads, GPUs, features
```

## GPUs

Live, Sept 2026 (`sinfo -p gpu -e -o '%D %c %m %z %G %f'`), with compute capability from NVIDIA ([current GPUs](https://developer.nvidia.com/cuda/gpus), [legacy GPUs](https://developer.nvidia.com/cuda/gpus/legacy)). The per-GPU columns divide the node's CPUs and memory by its GPUs.

| GPU | `--gres` type | Compute capability | GPU memory | GPUs (nodes × per node) | Host CPUs and memory | CPUs per GPU | Memory per GPU |
|---|---|---|---|---|---|---|---|
| P100 | `p100` | 6.0 (`sm_60`, Pascal) | 16 GB | 52 (16 × 3, 2 × 2) | 2 × Xeon Gold 6150 (Skylake), 36 cores, 377g | 12 (18 on the 2-GPU nodes) | 125g (188g) |
| V100 | `v100` | 7.0 (`sm_70`, Volta) | 32 GB | 112 (14 × 8) | 2 × Xeon Gold 6254 (8 nodes, 36 cores) or 6242R (6 nodes, 40 cores), Cascade Lake, 1448g | 4.5 or 5 | 181g |
| A100 | `a100` | 8.0 (`sm_80`, Ampere) | 80 GB | 4 (2 × 2) | 2 × Xeon Gold 6346 (Ice Lake), 32 cores, 503g | 16 | 251g |
| L40S | `l40s` | 8.9 (`sm_89`, Ada Lovelace) | 48 GB | 60 (15 × 4) | 2 × Xeon Platinum 8562Y+ (Emerald Rapids), 64 cores, 503g | 16 | 125g |
| H200 | `h200` | 9.0 (`sm_90`, Hopper) | 141 GB | 16 (4 × 4) | 2 × Xeon 6710E (Sierra Forest), 128 cores, 1007g | 32 | 251g |

- **Five types, 244 GPUs on 53 nodes.** No L4s are in any partition, whatever the hardware page says ([Stale advice](#stale-advice-on-the-official-pages)). Request syntax and per-user GPU caps: JOBS.md (GPUs). Free and total right now: `freen` (MONITORING.md (Cluster load and wait times)).
- **Stay within the per-GPU share.** FRCE sets no CPUs-per-GPU cap, and a GPU job that takes more than its share leaves the node's other GPUs with too few CPUs for anyone. The V100 nodes are the trap at 4.5–5 CPUs per GPU: the [AlphaFold page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/StructuralBiology/AlphaFold) asks for 8 tasks per V100, so four such jobs take 32 of a 36-core node's CPUs and strand its other four GPUs.
- **Compute capability decides which builds run.** The P100 (6.0) and V100 (7.0) are the oldest and lose toolkit and framework support first. Which CUDA toolkits build for which capability: DEVELOPMENT.md (CUDA and cuDNN); framework wheels: DEEP-LEARNING.md (Installing frameworks).
- **Double precision.** The L40S (8.9) runs FP64 at 1/64 of its FP32 rate, the other four at 1/2 ([CUDA Programming Guide](https://docs.nvidia.com/cuda/archive/12.9.1/cuda-c-programming-guide/index.html#arithmetic-instructions)): double-precision codes belong on an A100, H200, V100, or P100.
- Which GPU for which workload: DEEP-LEARNING.md (Choosing a GPU). Which types each OnDemand form offers: ONDEMAND.md (Apps and their forms).

## Partitions and node types

Live, Sept 2026 (`sinfo -N -o '%N %P %c %m %G %f' | sort -u`). Most CPU nodes serve several partitions at once, so load in one shows up in the others:

| Partition | Nodes | Node types |
|---|---|---|
| `short` | 37 | Xeon Gold 6342; 33 of them also in `norm` |
| `norm` | 101 | 62 × 6342, 32 × 6150, 7 × 6740P |
| `unlimited` | 30 | 26 × 6150 and 4 × 6342, all also in `norm` |
| `largemem` | 2 | the two 8268 nodes |
| `gpu` | 53 | every GPU node ([GPUs](#gpus)) |
| `csbdevel` | 54 | 47 × 6342 and the 7 × 6740P, all also in `norm` or `short` |
| `dragen` | 6 | the CCR Sequencing Facility's Dragen servers ([Large memory and Dragen](#large-memory-and-dragen)) |
| `nci-dragen` | 1 | the DRAGEN server |

Walltimes, per-user caps, and default memory: JOBS.md (Partitions and walltime). Reading the live table: MONITORING.md (Cluster load and wait times).

## Features and constraints

- Every CPU and GPU node carries two features (live, Sept 2026: `sinfo -e -o '%P %c %m %f'`): a CPU-model tag (`x6342`, `x6150`, `x6740P`, `x8268` on the CPU nodes; `x6150`, `x6254`, `x6242R`, `x6342`, `x6346`, `x6710E` on the GPU nodes) and a `uNN` tag of undocumented meaning. The Dragen servers carry a single `dragen-4.x.y` tag instead.
- `--constraint=x6740P` keeps a job on nodes with that feature, `--constraint="x6342|x6150"` on either. In `norm`, `x6342` means the 250g nodes, `x6150` the 755g ones, and `x6740P` the 2 TB ones. Use it to pin a CPU generation (benchmarks, or binaries built for one instruction set: DEVELOPMENT.md (CPU targets)); every constraint shrinks the pool, so the job may wait longer.
- Two GPU node types carry the wrong CPU tag: the A100 hosts (32 cores) are tagged `x6342`, a 24-core part, and the L40S hosts (64 cores) `x6346`, a 16-core part; their core counts fit the hardware page's Xeon Gold 6346 and Platinum 8562Y+. Pick GPUs by `--gres` type, never by these tags.
- Biowulf's feature names don't exist here: translate or remove `--constraint` lines in ported scripts (FROM-BIOWULF.md (Translation table)).
- Don't pick hardware with `--nodelist`: it ties the job to named nodes that may be busy, drained, or moved to another partition.

## Large memory and Dragen

`largemem` is the two 3 TB 8268 nodes; use it only when no smaller type holds the job. For one node's worth of memory:

| Memory the job needs | Node types that hold it |
|---|---|
| up to 250g | every CPU type |
| up to 755g | Xeon Gold 6150, in `norm` and `unlimited` |
| up to 2015g | Xeon 6740P, in `norm` (7 nodes) |
| up to 3023g | `largemem` |

`largemem`'s limits and default memory: JOBS.md (Partitions and walltime).

DRAGEN: the hardware page's "Illumina Dragon Server" (2 × Xeon Gold 6226R, 32 cores with two threads each that Slurm counts as 64 CPUs, 500g, and one custom FPGA card) is `nci-dragen`'s one server. The `dragen` partition's six servers, absent from the hardware page, have 24 or 32 cores with two threads each (48 or 64 CPUs) and 250g or 503g (live, Sept 2026). Who may use them and how to run DRAGEN: APPLICATIONS.md (Sequencing and genomics).

## Interconnect

"All systems are connected by either dual 10Gb or dual 25Gb ethernet cards, both to each other and to the NCI-F network, and by a 100Gb InfiniBand network within the cluster" (hardware page). Which nodes have which Ethernet speed isn't stated, and no InfiniBand features or islands are documented; multi-node MPI: JOBS.md (MPI and multinode jobs). How a node's GPUs connect (NVLink or PCIe) is undocumented too, and it matters for multi-GPU training (DEEP-LEARNING.md (Multi-GPU training)).

```bash
# on the compute node (inside your session): this node's InfiniBand link rate; in a GPU job, how its GPUs connect
cat /sys/class/infiniband/*/ports/*/rate
nvidia-smi topo -m
```

## Stale advice on the official pages

- The [hardware page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/FRCEHardwareCapabilities) is wrong in places → use the tables above (live, Sept 2026):
  - Counts: 62 Xeon Gold 6150 CPU servers (32 in service), 69 Xeon Gold 6342 (66), 19 P100 servers with 3 GPUs each (18, two of them with 2), 10 Xeon Gold 6254 V100 servers (8), 16 L40S servers (15), and 2 L4 servers (none in any partition).
  - "Xeon Platinum 6710E 32 cores" with 64 cores per H200 host: the hosts have 128, two 64-core Xeon 6710E ([Intel](https://www.intel.com/content/www/us/en/products/sku/240363/intel-xeon-6710e-processor-96m-cache-2-40-ghz/specifications.html)), and the part isn't a Platinum.
  - "Xeon 6740P 36 cores @ 2.70GHz" on the CPU-server row: the 6740P has 48 cores at 2.1 GHz ([Intel](https://www.intel.com/content/www/us/en/products/sku/241838/intel-xeon-6740p-processor-288m-cache-2-10-ghz/specifications.html)).
  - "Xeon Platinum 8562Y" for the L40S hosts: the part is the 8562Y+ ([Intel](https://www.intel.com/content/www/us/en/products/sku/237558/intel-xeon-platinum-8562y-processor-60m-cache-2-80-ghz/specifications.html)).
  - "Xeon Gold 6226R 64 cores" for the DRAGEN server: 16 cores per socket; 64 is the two sockets' threads ([Intel](https://www.intel.com/content/www/us/en/products/sku/199347/intel-xeon-gold-6226r-processor-22m-cache-2-90-ghz/specifications.html)).
  - The login ("head") node's "Xeon Gold 6342 24 cores @ 2.70GHz": 2.8 GHz, as in the other 6342 row.
  - The A100's "312 Tensor cores": it has 432; 312 is its FP16 Tensor TFLOPS ([NVIDIA](https://developer.nvidia.com/blog/nvidia-ampere-architecture-in-depth/)).
- [QuickStart](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart) says "The FRCE cluster has three different types of Nvidia GPU's, `p100`, `v100`, and `a100`" → five ([GPUs](#gpus)).
- The hardware page's GPU totals (57 P100, 128 V100, 64 L40S, 8 L4), the [home page](https://ncifrederick.cancer.gov/staff/FRCE) announcement, and the login banner's "16 servers with 4 Nvidia L40s cards each" overstate what's in service: 52 P100, 112 V100, 60 L40S, no L4 (Sept 2026). The partition page's `gpu` "Other Limits" are per-user caps, and stale ones (JOBS.md (Stale advice on the official pages)). The `freen` sample on the [Ollama endpoint page](https://ncifrederick.cancer.gov/staff/FRCE/OllamaEndpoint) predates today's nodes: it shows L4 rows and 96 CPUs per H200 node → count with live `freen`.
- Cluster size: the [System Information](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation) index says "3000+ core", the diagram page "7000+ core"; the CPU and GPU nodes in service have 7,896 cores, about 8,100 with the Dragen servers (Sept 2026) → don't quote a page's total.
- The page titled "Slurm Partitions & Features" lists no features, though every node has them ([Features and constraints](#features-and-constraints)).

## Going further

- [FRCE Hardware Capabilities](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/FRCEHardwareCapabilities) — the node table, network, standard mounts.
- [Visual diagram of FRCE Systems](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/VisualdiagramFRCESystems) — the node classes and how the hosts connect.
- [Slurm Partitions & Features](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/SlurmPartitionsFeatures) — the partition list (limits: JOBS.md).
- [Status and Metrics](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/StatusandMetrics) — the live partition table and wait times (MONITORING.md).
- Intel specifications for the other models: [6150](https://www.intel.com/content/www/us/en/products/sku/120490/intel-xeon-gold-6150-processor-24-75m-cache-2-70-ghz/specifications.html) · [6342](https://www.intel.com/content/www/us/en/products/sku/215276/intel-xeon-gold-6342-processor-36m-cache-2-80-ghz/specifications.html) · [6346](https://www.intel.com/content/www/us/en/products/sku/212457/intel-xeon-gold-6346-processor-36m-cache-3-10-ghz/specifications.html) · [6242R](https://www.intel.com/content/www/us/en/products/sku/199352/intel-xeon-gold-6242r-processor-35-75m-cache-3-10-ghz/specifications.html) · [6254](https://www.intel.com/content/www/us/en/products/sku/192451/intel-xeon-gold-6254-processor-24-75m-cache-3-10-ghz/specifications.html) · [8268](https://www.intel.com/content/www/us/en/products/sku/192481/intel-xeon-platinum-8268-processor-35-75m-cache-2-90-ghz/specifications.html).
- [sinfo](https://slurm.schedmd.com/sinfo.html#OPT_exact) — `--exact` and the `%c %m %z %G %f` fields.
- Live: `freen`, `sinfo -e -o '%P %D %c %m %z %G %f'`, `scontrol show node cnNNN`, `nvidia-smi topo -m` (in a GPU job).
