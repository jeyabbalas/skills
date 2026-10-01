Biowulf's compute hardware as of Sept 2026: node types with their `--constraint` features, GPU models, and which partitions hold them. Writing the requests (`--gres`, partitions, the CPUs-per-GPU rule, `gpuh200` limits) is JOBS.md; choosing GPUs for training, DEEP-LEARNING.md; the login node and Helix, ACCESS.md. Hardware changes: confirm with `freen` before relying on a count or a type here.

## Compute nodes

From the [hardware page](https://hpc.nih.gov/systems/hardware.html), Sept 2026. Hyperthreading is on everywhere, so Slurm CPUs = 2 × cores. RAM in parentheses is what `freen` reports as allocatable: the largest `--mem` a job can get on that node type. "Page source" values come from `freen` lines staff left in HTML comments on the hardware page, not its visible text. The hardware page lists no partitions; the Partition column comes from `freen`'s documented example, the announcements, and those comments, so treat it as approximate and read `freen`.

| Nodes | CPU | Features | Cores / CPUs | RAM | SSD (GB) | GPUs | Partition |
|---|---|---|---|---|---|---|---|
| 96 | AMD Epyc 9645 (Zen5) | `e9645` `ibndr200` | 192 / 384 | 1536 GB (1502g, page source) | 7000 | — | norm, per the page source (unconfirmed) |
| 63 | AMD Epyc 9454 | `e9454` `ibhdr200` | 96 / 192 | 768 GB (747g) | 3200 | — | norm |
| 144 | AMD Epyc 7543 | `e7543` `ibhdr200` | 64 / 128 | 512 GB (495g) | 3200 | — | norm |
| 72 | Intel Xeon Gold 6240 | `x6240` `ibhdr100` | 36 / 72 | 384 GB (369g) | 3200 | — | norm |
| 294 | Intel Xeon Gold 6140 | `x6140` `ibhdr100` | 36 / 72 | 384 GB (369g) | 3200 | — | norm, multinode, unlimited |
| 1224 | Intel E5-2680v4 | `x2680` `ibfdr` | 28 / 56 | 256 GB (243g) | 800 | — | norm, multinode |
| 14 | AMD Epyc 9645 | `e9645` `ibndr200` | 192 / 384 | 2258 GB | 7000 | 8 × H200 | gpuh200 (7 nodes), quick (7) |
| 20 | Intel Xeon 6787p | `x6787p` `ibndr200` | 172 / 344 | 768 GB (747g, page source) | 7000 | 8 × L40 | gpu |
| 100 | AMD Epyc 7543p | `e7543p` `ibhdr200` | 32 / 64 | 256 GB (243g) | 3200 | 4 × A100 | gpu |
| 60 | Intel Xeon Gold 6140 | `x6140` `ibhdr` | 36 / 72 | 384 GB (369g) | 1600 | 4 × V100x | gpu |
| 8 | Intel E5-2680v4 | `x2680` `ibfdr` | 28 / 56 | 128 GB (117g) | 800 | 4 × V100 | gpu |
| 48 | Intel E5-2680v4 | `x2680` `ibfdr` | 28 / 56 | 128 GB (117g) | 650 | 4 × P100 | gpu |
| 16 | AMD Epyc 9454 | `e9454` `ibhdr200` | 96 / 192 | 3 TB (3015g) | 3200 | — | largemem |
| 4 | Intel E7-8860v4 | `x8860` `ibfdr` | 72 / 144 | 3 TB (3015g) | 800 | — | largemem |
| 20 | Intel E7-8860v4 | `x8860` `ibfdr` | 72 / 144 | 1.5 TB (1503g) | 800 | — | largemem |

- A CPU feature doesn't pick a partition: `x6140` covers CPU nodes and V100x nodes, `x2680` CPU, V100, and P100 nodes, `e9645` CPU and H200 nodes, and `e7543` also tags 256 GB (243g) buy-in nodes in `quick` (so outside `norm` it doesn't guarantee 495g). Give the partition too, e.g. `--partition=multinode --constraint=x6140`.
- `quick` also runs on idle buy-in nodes (the `freen` example shows `nhlbi` and `forgo` nodes there). Buy-in partitions (`ccr*`, `forgo`, `persist`, …) aren't on the hardware page; `freen` lists them.
- The SSD column caps `--gres=lscratch:N` on that node type.
- Memory ceilings: the largest `norm` type in the visible docs has 747g allocatable (the Experienced User Guide gives `norm` 243–747 GB), but the page source lists the 1.5 TB `e9645` nodes in `norm` at 1502g; confirm with `freen` before sending a 750–1500g job to `norm` rather than `largemem`. `largemem` nodes offer 1503g or 3015g (its rules: JOBS.md).
- Removed 24 Apr–1 May 2026 (about half moved to 1 May): all `x2695`, `x2630`, and K80 nodes, and 40 `x2680` nodes in `norm`. Multinode jobs pinned to `x2695` need only `--constraint=x2680` (same CPUs and memory); `x2630` jobs need new `--ntasks`/`--ntasks-per-node` on `x2680` or `x6140`.

## GPUs

| GPU | VRAM | Per node | NVLink | Feature | `--gres` type | Max CPUs per GPU | Partition |
|---|---|---|---|---|---|---|---|
| H200 | 141 GB | 8 | yes | `gpuh200` | `h200`, unverified | 48 | gpuh200, quick |
| L40 | 48 GB | 8 | not stated | `gpul40` | `l40`, unverified | 43 (request ≤ 42) | gpu |
| A100 | 80 GB | 4 | yes | `gpua100` | `a100` | 16 | gpu |
| V100x (V100-SXM2) | 32 GB | 4 | yes | `gpuv100x` | `v100x` | 18 | gpu |
| V100 | 16 GB | 4 | not stated | `gpuv100` | `v100` | 14 | gpu |
| P100 | 16 GB | 4 | not stated | `gpup100` | `p100` | 14 | gpu |

- Max CPUs per GPU = node CPUs ÷ GPUs per node (the rule, and what happens past it: JOBS.md). The user guide states 14 for P100; the others are computed from the node table. CPUs are allocated in whole cores (pairs), so an odd request rounds up: keep L40 jobs at an even count of at most 42 per GPU (inference, unverified).
- Documented `--gres` types are `p100`, `v100`, `v100x`, `a100` (user guide; `dashboard_cli --gpu-type` lists the same four), and `freen` labels those rows `gpu (p100)`, `gpu (a100)`, …. No type string is documented for L40 or H200; read the label `freen` gives their rows before trusting one. Request forms, including the untyped ones: JOBS.md (GPUs).
- K80s are retired; staff say jobs that requested them "should run unmodified on P100 GPUs".

## Which GPU for what

- Start from memory: what must fit on one GPU, unless the code is written for several. Among the types that fit, take what's free (`freen`'s FreeGPUs column).
- L40 (48 GB): staff built these nodes for **single-GPU** jobs; they sit in `gpu` with the same limits as the other non-H200 types.
- H200 (141 GB, NVLink): for **multi-GPU** jobs and jobs needing more GPU memory than L40 (48 GB) or A100 (80 GB) offer. Scarce, with their own partition and limits (JOBS.md).
- A100 (80 GB) and V100x (32 GB) nodes also link their 4 GPUs with NVLink.
- P100 and V100 (16 GB): smaller models and tests.
- When several types would do, widen the pool with an untyped request and a feature OR list (forms: JOBS.md, GPUs).
- A GPU helps only software written for GPUs.

## Node features

| Family | Values (Sept 2026) |
|---|---|
| CPU model | `e9645` `e9454` `e7543` `e7543p` `x6787p` `x6240` `x6140` `x2680` `x8860` |
| Size | `coreN`, `cpuN` (2 × cores), `gN` (GB of RAM), `ssdN` (GB of local SSD) |
| InfiniBand | `ibndr200` `ibhdr200` `ibhdr` `ibhdr100` `ibfdr` |
| GPU | `gpuh200` `gpul40` `gpua100` `gpuv100x` `gpuv100` `gpup100` |
| Other, seen in `freen` | buy-in tags such as `nhlbi`, `forgo`, `huygens`; `10g` (Ethernet-only nodes) |

- Documented syntax: one feature, `--constraint=x2680`, or a quoted OR list, `--constraint="gpua100|gpuv100x"`. No NIH page shows Slurm's `&` (AND) form.
- Staff say features matter only when a job needs a particular processor type (e.g. parallel jobs that should all run on the same type) or a node-locked license. Pin a CPU type for multinode MPI (JOBS.md) or for binaries built for one CPU (DEVELOPMENT.md); otherwise leave constraints off, since each one shrinks the set of nodes the job can start on.
- Ask for memory and disk with `--mem` and `--gres=lscratch:N`, not `gN` or `ssdN`: some `gN` tags are wrong (stale-advice section below).

## Check live

```bash
freen                                     # per partition: free nodes, CPUs, GPUs; per node: Cores, CPUs, GPUs, Mem, Disk, Features
freen | grep -E 'Partition|----|gpu'      # GPU node types only
nodetype cn3118                           # one node's features
( nodetype cn3118 ibfdr x2680 && echo yes ) || echo no   # exit 0 only if the node has every listed feature
```

Output fields, `batchlim`, and running these from a compute node: UTILITIES.md.

## Stale advice on the official pages

- Cluster totals disagree: the hardware page header says 1541 nodes and 1024 GPUs while its rows add up to 2,183 nodes and 1,136 GPUs, and the Experienced User Guide and systems page give other figures → don't quote totals; count from `freen`.
- Row typos: the Epyc 9645 CPU row says "96 x" cores and the 3 TB Epyc 9454 row "86 x" → the features (`core192`, `core96`) and the Sept 2026 announcement are right.
- The 128 GB P100 and V100 nodes carry `g256` (`freen` shows `g128`); the H200 nodes list 2258 GB with `g2304`.
- March and August 2026 announcements say "L40S"; the hardware page and the 30 Sep 2026 announcement say "L40".
- The user guide says "All GPU nodes have 4 GPUs" (H200 and L40 nodes have 8), shows only four GPU types in its `freen` sample, and writes "P190" for P100.
- Local disk "generally 800GB" (user guide) or "at least 400 gigabytes" (Experienced User Guide) → 650–7000 GB by node type (table). The 2020 cheat sheet's `k20x` GPUs no longer exist.
- The MPI page names only `ibfdr`, `ibhdr`, `ibhdr100` as InfiniBand features; `ibhdr200` and `ibndr200` exist too. The hardware page's network text still mentions GPFS (the last GPFS system was retired in the 29 Jul–2 Aug 2026 downtime) and doesn't describe NDR.

## Going further

- [Hardware page](https://hpc.nih.gov/systems/hardware.html) — node table, SLURM features (the authoritative names), network, storage.
- [Announcement ?1223](https://hpc.nih.gov/nih/about/announcements.php?1223) — H200, L40, and Zen5 nodes live, `gpuh200` limits; [?1181](https://hpc.nih.gov/nih/about/announcements.php?1181) — the April 2026 retirements and how to adjust constraints.
- [freen and nodetype](https://hpc.nih.gov/docs/biowulf_tools.html#freen) — column meanings; [Allocating GPUs](https://hpc.nih.gov/docs/userguide.html#gpu) — the CPUs-per-GPU rule.
- [Announcements](https://hpc.nih.gov/nih/about/announcements.php) — later hardware changes.
- Live: `freen`, `nodetype NODE`, `batchlim`.
