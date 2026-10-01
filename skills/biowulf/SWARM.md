How to run many independent commands — a per-sample or per-file loop — as a swarm: the swarmfile, choosing `-g`/`-t`/`-p`/`-b`/`--time`, the `--devel` dry run, environment and lscratch per subjob, logs and exit status, and rerunning failed subjobs. swarm is NIH's wrapper around `sbatch --array`: each swarmfile line becomes a subjob, and the whole swarm is one Slurm job (`JOBID`, with subjobs `JOBID_0`, `JOBID_1`, …). sbatch flags, partitions, GPU requests, and dependency types live in JOBS.md; monitoring tools in UTILITIES.md; multi-step pipelines in WORKFLOWS.md.

Table of contents

- [Workflow](#workflow)
- [Writing the swarmfile](#writing-the-swarmfile)
- [Options](#options)
- [Resource arithmetic](#resource-arithmetic)
- [Environment, modules, and lscratch](#environment-modules-and-lscratch)
- [Outputs and exit status](#outputs-and-exit-status)
- [Failures and reruns](#failures-and-reruns)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Workflow

You generate, size, and dry-run; the user submits (ground rules in SKILL.md).

1. **Check the fit.** swarm is "NOT a workflow manager": it runs independent commands. A single command belongs in a batch script (JOBS.md); dependent steps in a workflow manager (WORKFLOWS.md) or in swarms chained with `--dependency`. A loop of `sbatch` calls is what swarm replaces.
2. **Generate the swarmfile with a script** ([rules](#writing-the-swarmfile)).
3. **Measure one real line in the session**: the one with the largest input, since every line gets the same allocation. Lines written with `$SLURM_CPUS_PER_TASK` and `/lscratch/$SLURM_JOB_ID` run unchanged in a session started with `--cpus-per-task` (without it, `$SLURM_CPUS_PER_TASK` is unset) and lscratch, at the session's CPU count (load the modules you'll pass to `--module` first):
   ```bash
   # on the compute node (inside the session)
   line=$(sed -n 17p /data/$USER/proj/run.swarm)                               # the largest input
   /usr/bin/time -v bash -c "$line" 2>&1 | grep -E 'Elapsed|Maximum resident'   # GNU time (generic)
   ```
   `Maximum resident` is the largest single process, not the sum (generic): for lines that run processes side by side (pipes, `&`), add them up or size from a pilot's `jobhist`. Note the line's temp-space use (for `lscratch:N`), and multiply its output size by the line count before comparing with `checkquota` ([storage best practices](https://hpc.nih.gov/storage/#best)). If input sizes vary widely, split the file and size each part.
4. **Pick options** ([arithmetic](#resource-arithmetic)): `-g` and `--time` from the measurement plus a small buffer (sizing recipe: UTILITIES.md), `-t` = the thread count you tested, `--gres=lscratch:N`, then `-p` or `-b`.
5. **Dry run: `swarm --devel` is the only swarm command you run.** It prints the plan and the exact `sbatch --array=...` line and submits nothing; unlike `--debug`/`--no-run`, it writes no scripts. Check the command and subjob counts, per-command GB and threads, and `--time=`, `--cpus-per-task=`, `--mem=` (MB). If `swarm` is missing or fails in the session, give the user the `--devel` command and ask for its output.
   ```bash
   # on the compute node (inside the session)
   cd /data/$USER/proj && swarm --devel -g 5 -t 4 --time 6:00:00 --gres=lscratch:20 --module mytool/1.2 --logdir swarmlogs run.swarm
   ```
6. **Hand over** the same command without `--devel`, after a `cd` to the directory the subjobs should start in:
   ```bash
   # on Biowulf (login node) — the user runs this
   cd /data/$USER/proj
   swarm -g 5 -t 4 --time 6:00:00 --gres=lscratch:20 --module mytool/1.2 --logdir swarmlogs run.swarm
   ```
   The swarm inherits the environment of the shell that submits it — the user's login shell, not your session — so everything the lines need must come from `--module`, `--prolog-source`, or the line itself. For a big swarm, suggest a pilot first (`head -n 20 run.swarm > pilot.swarm`; NIH: start small and work up); rerunnable lines let the full run skip what the pilot finished.

Off the cluster (SKILL.md), steps 3 and 5 become the user's: write the generator (it must run on the cluster to glob the real files; the user can run it at the login prompt, since it only lists files), order lines largest input first so a `head -n 20` pilot includes the worst cases, have the user dry-run the pilot with `--devel` and paste back the output before submitting it, and size the full run from the pilot's `jobhist`.

## Writing the swarmfile

Syntax ([input](https://hpc.nih.gov/apps/swarm.html#input), [directives](https://hpc.nih.gov/apps/swarm.html#directives)):

- One line = one command, as typed at a bash prompt: `;` lists, `&&`, `export`, `cd`, subshells, and `if` all work. csh syntax needs `--usecsh`.
- `#` starts a comment anywhere on a line; the rest of the line is dropped. Lines that need a literal `#` (`${#var}`, URL fragments, IDs) need `--no-comment` or `--comment-char C`. With `--no-comment` the file must hold no comments at all, whole-line or trailing: swarm runs each line inside `( … )`, so a trailing comment swallows the closing parenthesis and the line fails, which `--devel` doesn't catch.
- A line ending in a space and a backslash, with nothing after it, continues on the next line; swarm refuses other forms.
- `#SWARM <options>` lines, flush left, set options from inside the file (`#SWARM -t 4 -g 20 --time 40`) and are never run as commands, even under `--no-comment`. Precedence: command line > `SBATCH_*` variables (`SBATCH_PARTITION`, `SBATCH_TIMELIMIT`, …) > `#SWARM` lines > `--sbatch` options — so put resources on the command line you hand over.

Generating — the swarmfile is your deliverable:

- Absolute paths everywhere, including `cd` targets.
- Unique outputs per line. A program that writes a fixed filename garbles its siblings' output; run each line in its own directory (`cd /data/$USER/proj/run1 && /data/$USER/proj/ped`).
- Steps chained with `&&` ([why](#outputs-and-exit-status)).
- Threads from `$SLURM_CPUS_PER_TASK` ([user guide](https://hpc.nih.gov/docs/userguide.html#submit)), except one per line under `-p` ([why](#resource-arithmetic)). When generating from a shell, escape run-time variables (`\$SLURM_CPUS_PER_TASK`, `\$SLURM_JOB_ID`) so they expand in the subjob.
- No blanks or non-printable characters in file names ([best practices](https://hpc.nih.gov/docs/FAQ.html#best_practices)).
- Rerunnable lines (generic advice): write to lscratch or a temporary name, move the result into place only on success, and skip a line whose final output exists, so a rerun never redoes or clobbers finished work. From lscratch, copy to a temporary name beside the destination and then `mv`: a `mv` across filesystems copies straight to the final name, and a subjob killed mid-copy leaves a partial file that the skip test accepts.
- One log per line (`> logs/NAME.log 2>&1`), so a failure maps to its input without decoding subjob numbers.

```bash
# on the compute node (inside the session) — adapt tool, flags, and paths
p=/data/$USER/proj; mkdir -p $p/out $p/logs $p/swarmlogs
: > $p/run.swarm                                   # truncate: regenerating must not append
for f in $p/in/*.fq.gz; do
  s=$(basename "$f" .fq.gz)
  echo "[[ -s $p/out/$s.bam ]] || { mytool -t \$SLURM_CPUS_PER_TASK -i $f -o /lscratch/\$SLURM_JOB_ID/$s.bam && cp /lscratch/\$SLURM_JOB_ID/$s.bam $p/out/$s.bam.part && mv $p/out/$s.bam.part $p/out/$s.bam; } > $p/logs/$s.log 2>&1" >> $p/run.swarm
done
wc -l $p/run.swarm; head -n 2 $p/run.swarm
```

## Options

`swarm [options] swarmfile`, the file last (`-f swarmfile` still works but is deprecated). This file follows swarm 26.6 (June 2026), whose page is the live one; `swarm -V` shows the installed version. "Per" is what the value applies to. Full list: [usage](https://hpc.nih.gov/apps/swarm.html#usage).

| Option | Per | Meaning and notes |
|---|---|---|
| `-g`, `--gb-per-process G` | line | GB of memory, default 1.5; strictly enforced — a subjob over its memory is killed |
| `-t`, `--threads-per-process T` | line | CPUs, default 1; allocated as whole cores (2 CPUs each) |
| `-p`, `--processes-per-subjob P` | subjob | run P lines at once; an even number up to 128 (an odd one is raised by 1, with a notice on stdout); equals the subjob's CPUs |
| `-b`, `--bundle B` | subjob | run B lines one after another; multiplies the walltime |
| `--time T` (= `--time-per-command`) | line | walltime; `HH:MM:SS` or bare minutes (`--time 40`); always set it |
| `--time-per-subjob T` | subjob | fixed walltime regardless of `-b`/`-p`, for sub-minute lines at high `-b` |
| `-m`, `--module a/1.0,b/2.1` | swarm | modules loaded in every subjob; pin versions (MODULES.md) |
| `--gres=lscratch:N` | subjob | N GB of lscratch. For GPUs, use JOBS.md's `--partition`/`--gres` request with lscratch in the same `--gres`; the swarm page has no GPU example, so check `--devel` |
| `--partition P` | swarm | default `norm`; at most two, comma-separated (`quick,norm`) |
| `--logdir DIR`, `-J NAME` | swarm | where `.o`/`.e` go; job name and file prefix |
| `--dependency afterany:JID` | swarm | wait for another job ([exit status](#outputs-and-exit-status)) |
| `--prolog CMD`, `--prolog-source CMD`, `--epilog CMD` | subjob | run before; source into the lines' shell (env vars, conda); run after. `--prolog` and `--epilog` each add `--prolog-time`/`--epilog-time` (default 10 min) to the walltime; `--prolog-source` adds none |
| `--err-exit` | subjob | stop at the first non-zero exit; "may fail" in subshells or forked processes; no effect under `-p` |
| `--joblog` | subjob | with `-p`: per-line exit codes |
| `--maxrunning N` | swarm | cap on subjobs running at once (I/O-heavy swarms) |
| `--sbatch "OPTS"` | swarm | any other sbatch option, one quoted string; swarm refuses `--time`, `--cpus-per-task`, and `--mem*` there (use `--time`, `-t`, `-g`) |
| `--devel` | — | dry run ([workflow](#workflow)); add `--verbose 5` for the subjob→command tree |
| `--silent` | — | print only the job ID, as the default does unless `#SWARM` lines raise `--verbose`; an odd `-p` still prints its notice, so `jid=$(swarm …)` needs an even `-p` |

Rarer: `--noht` (= `--threads-per-core=1`), `--usecsh`, `--no-comment`, `--comment-char C`, `--merge-output`, `--noout`/`--noerr`, `--oldpack`, `-L`/`--licenses`, `--qos`, `--reservation`, `-v 0-6`, `-V`. `--exclusive` and `--mem=0` are not allowed; a job that truly needs them is an sbatch script.

## Resource arithmetic

For N lines at `-g G`, with NIH's own examples in parentheses ([gandt](https://hpc.nih.gov/apps/swarm.html#gandt), [p](https://hpc.nih.gov/apps/swarm.html#p), [time](https://hpc.nih.gov/apps/swarm.html#time), [devel](https://hpc.nih.gov/apps/swarm.html#devel)); subjob counts round up:

| Setting | Subjobs | CPUs each | Memory each | Walltime each |
|---|---|---|---|---|
| default | N | 2 | 1.5 GB | `--time` |
| `-t T` | N | T rounded up to even (`-t 3` → 4) | G | `--time` |
| `-p P` | N/P | P | G × P (`-p 16` → 24 GB) | `--time` (`-p 16 --time 60` → 60 min) |
| `-b B` | N/B (10,000 at `-b 40` → 250) | 2 | G (`-b 4` → `--mem=1536`) | `--time` × B |
| `-p P -b B` (B ≥ P) | N/B: B lines each, P at a time (32 at `-g 5 -p 4 -b 4` → 8) | P | G × P (`--mem=20480`) | `--time` × ⌈B/P⌉ |
| over 1000 subjobs | folded into 1000 (345,029 lines → 1000 subjobs of up to 346 lines) | | | `--time` × lines per subjob |

- `-p` is for single-threaded lines. `-p P` requests `--cpus-per-task=P`, so `$SLURM_CPUS_PER_TASK` is the subjob's total, shared by P concurrent lines — give each line one thread. Don't combine `-t` above 1 with `-b` larger than `-p`: swarm then starts P × T lines at once in a subjob sized for P (memory G × P). Read the `--devel` line whenever you mix options.
- Single-threaded lines at the default leave a CPU idle; the FAQ recommends `-p 2` ([pending](https://hpc.nih.gov/docs/FAQ.html#pending)).
- Bundle short lines so each subjob runs at least 15 minutes; don't flood the cluster with more than 100 jobs under 15 minutes ([best practices](https://hpc.nih.gov/docs/FAQ.html#best_practices)). `dashboard_cli jobs --bad-swarm` lists past swarms whose subjobs "finished too quickly" (UTILITIES.md).
- swarm refuses to submit when `--time` × bundle exceeds the partition maximum (`batchlim`; JOBS.md). It adds `--prolog`/`--epilog` time after that check, so leave room for it yourself. A short, realistic `--time` can raise priority; running over kills the subjob.
- Memory per line decides the partition for swarm, not JOBS.md's 350g rule: `-g` above 750 needs exactly `--partition largemem`, and swarm refuses `largemem` for `-g` of 750 or less (Failures and reruns).
- `--devel` shows the arithmetic before anything is submitted:

```text
$ swarm --time 00:30:00 -b 4 --devel file.swarm          # a 64-line file
64 commands run in 16 subjobs, each command requiring 1.5 gb and 1 thread, running 4 commands per subjob
sbatch --array=0-15 --job-name="swarm" … --cpus-per-task=1 --mem=1536 --partition=norm --time=02:00:00 …/swarm.batch
```

`--cpus-per-task=` shows T × P as requested (1 by default); Slurm still allocates whole cores, so a subjob gets at least 2 CPUs.

## Environment, modules, and lscratch

Environment scopes ([environment](https://hpc.nih.gov/apps/swarm.html#environment)):

| Scope | How | Catch |
|---|---|---|
| whole swarm | the submitting shell's environment (`VAR=5 swarm ...`), or `--sbatch "--export=..."` | fixed before submission: no `$SLURM_JOB_ID` or `$SLURM_MEM_PER_NODE`. In stock Slurm, `--export=VAR=val` without `ALL,` exports only the listed variables (and `SLURM_*`), while with `ALL,` a variable already set in the submitting shell keeps its shell value (generic) |
| each subjob | `--gres=lscratch:10 --prolog-source 'export TMPDIR=/lscratch/$SLURM_JOB_ID' --prolog-time 1` | single quotes, so it expands in the subjob |
| each line | on the line: `export TMPDIR=/lscratch/$SLURM_JOB_ID/s1; mkdir -p $TMPDIR; cmd ...`, or `VAR=1 cmd` | |

- Modules: `--module`, or `module load` at the start of each line. Conda environments in swarms: CONDA.md. Containers: each subjob must load singularity and source its bind list itself, which the submitting shell doesn't provide (CONTAINERS.md, Batch jobs and swarms). Python and R swarms (many short interpreter starts, Rswarm): PYTHON.md, R.md.
- Set in every subjob: `SLURM_ARRAY_JOB_ID` (one ID for the swarm), `SLURM_JOB_ID` (unique per subjob), `SLURM_ARRAY_TASK_ID` (subjob number; `swarm --help` also lists `SWARM_ARRAY_TASK_ID`, which swarm never sets), `SWARM_PROC_ID` (process slot, `-p` only), `SWARM_COMM_ID` (the line's command number, from 1, not counting comments and blank lines).

lscratch ([lscratch](https://hpc.nih.gov/apps/swarm.html#lscratch)):

- Not automatic: `--gres=lscratch:N` gives each subjob its own N GB at `/lscratch/$SLURM_JOB_ID`, deleted when the subjob ends. Subjobs can't share it. Copy results to `/data` within the line, or once per subjob with `--epilog 'cp -r /lscratch/$SLURM_JOB_ID/output /data/$USER'`.
- Bundled lines (`-b`) run one after another in the same directory: give each line its own subdirectory and delete only that when the line ends. NIH's `cd /lscratch/$SLURM_JOB_ID ; command1 arg1 arg2 ; rm -rf /lscratch/$SLURM_JOB_ID/*` also wipes a `--prolog` copy that later lines still need.
- Packed lines (`-p`) share one allocation at the same time: size N for all P lines, give each line its own subdirectory, and never wipe the whole directory.
- A large input that every line reads: copy it to lscratch once per subjob with `--prolog` (raise `--prolog-time`; several hundred GB can take 30–60 minutes), and pack or bundle so several lines use each copy. If lines each parse a subset out of a file over 8 GB, make the parsing its own job and feed the subsets to the swarm ([best practices](https://hpc.nih.gov/docs/FAQ.html#best_practices)).

## Outputs and exit status

Output files ([output](https://hpc.nih.gov/apps/swarm.html#output), [p](https://hpc.nih.gov/apps/swarm.html#p)):

- `swarm_JOBID_N.o` and `.e` for each subjob, in the submission directory unless `--logdir` (create it first; many files in one directory: STORAGE.md). `-J NAME` replaces the `swarm` prefix; `--merge-output` sends stderr into `.o`.
- Keep the `.e` files (no `--noerr`): Slurm's out-of-memory and time-limit messages land there even when lines log elsewhere.
- With `-p`, each process writes `swarm_JOBID_N_K.{o,e}` plus a shared `swarm_JOBID_N_p.{o,e}` while running; they are condensed into `swarm_JOBID_N.{o,e}` when the subjob ends normally (`--oldpack` keeps them apart). After a cancel or timeout, the reason is in `_p.e`.
- `--joblog` (with `-p`) writes `swarm_JOBID_N.joblog`: unique_jobid, command number, start, end, elapsed seconds, exit code. `cat *.joblog | sort -nk2` reads them all.
- `--prolog`, `--prolog-source`, and `--epilog` output goes to `NAME_JOBID_N.prolog`, `.prolog_source`, and `.epilog` in the log directory: look there when an epilog copy fails.

Exit status ([dependency](https://hpc.nih.gov/apps/swarm.html#dependency)):

- swarm passes "the exit status of the last command executed" to Slurm, so `a ; b` hides a failed `a`. Chain with `&&`, or add `--err-exit`.
- A bundled subjob reports its last line. A packed (`-p`) subjob exits 0 whatever its lines return, unless Slurm kills it: under `-p`, `afterok` is always satisfied, `--mail-type=FAIL` stays silent, and `--err-exit` does nothing, so read the `EXIT CODE:` lines in its `.o` or use `--joblog`. Either way a COMPLETED subjob can contain failed lines — check outputs or the joblog, not just states.
- Slurm folds the subjobs into one status: one failed subjob marks the swarm FAILED. `sacct` and `jobhist` list each `JOBID_N`.
- Downstream jobs wait with `afterany`: under `afterok`, one failed subjob can leave the dependent job pending forever as `(DependencyNeverSatisfied)`. The downstream script should check that its inputs exist. Other dependency types, including `singleton` to collate a swarm: JOBS.md.

```bash
# on Biowulf (login node) — the user runs this; every line submits a job
jid1=$(sbatch first.sh)
jid2=$(swarm --silent --dependency afterany:$jid1 -g 5 --time 2:00:00 run.swarm)
sbatch --dependency=afterany:$jid2 last.sh
```

- Mail: `--sbatch "--mail-type=FAIL"` sends one email per swarm; `--mail-type=END,ARRAY_TASKS` sends one per subjob. Everything else about mail: JOBS.md.

## Failures and reruns

Monitoring is read-only and yours: `sjobs` lists subjobs as `JOBID_N`; after the end, `jobhist JOBID` gives each subjob's State, MemReq, and MemUsed plus the `Submission Path` and `Swarm Command` (UTILITIES.md). Cancelling is the user's: `scancel JOBID` ends the whole swarm, `scancel JOBID_N` one subjob (generic Slurm).

| Symptom | Cause | Fix |
|---|---|---|
| `slurmstepd: error: Detected 1 oom_kill event in StepId=…` (older Slurm, as on the swarm page: `Exceeded job memory limit at some point.`) at the end of `.e`, or an `OUT_OF_MEMORY` or FAILED subjob with MemUsed = MemReq | out of memory (the message can be missing if the subjob died early) | raise `-g` |
| `*** JOB ... CANCELLED AT ... DUE TO TIME LIMIT ***` in `.e` (`_p.e` with `-p`) | walltime | raise `--time` (or `--time-per-subjob`, if set) |
| `ERROR: Total time for bundled commands is greater than partition walltime limit.` | `--time` × bundle over the partition maximum | lower `--time` or `-b`, pick another partition, split the swarmfile, or, for sub-minute lines, `--time-per-subjob` |
| `ERROR: -g N requires --partition largemem` | `-g` above 750 without exactly `--partition largemem` (`norm,largemem` is refused too) | `--partition largemem`, or lower `-g` to 750 or less |
| `ERROR: -g <= 750 must not run on the largemem partition` | `--partition largemem` with `-g` of 750 or less | drop the partition: `norm`'s large nodes take it |
| dependent job stuck in `(DependencyNeverSatisfied)` | `afterok` on a swarm with a failed subjob | the user cancels it and resubmits with `afterany` |
| lines far slower than the session test | more threads than CPUs (often `$SLURM_CPUS_PER_TASK` per line under `-p`) | match threads to `-t`; one per line under `-p` |

Before any rerun:

1. List the failed subjobs (`jobhist JOBID`) and read the tail of their `.e`/`_p.e`. For bundled or packed swarms, also list lines whose outputs are missing.
2. If the cause isn't memory or walltime, reproduce the line in the session and fix it there. NIH: "Don't debug with swarms" — test a fix on one line before resubmitting a swarm. If nothing explains why a swarm stopped early, the swarm page says to ask staff; draft it for the user (TROUBLESHOOTING.md).
3. Build the rerun file and give the user the command:
   - **Most subjobs failed:** the user cancels what's left, `cd`s to the `Submission Path`, and reruns the `Swarm Command` with a higher `-g` (memory) or `--time` (walltime) ([swarm_resubmit](https://hpc.nih.gov/docs/FAQ.html#swarm_resubmit)).
   - **A few failed:** a new swarmfile of just those lines ([swarm_select](https://hpc.nih.gov/docs/FAQ.html#swarm_select)). Regenerate over only the inputs whose final outputs are missing; resubmitting the whole file would turn every finished line into a near-instant subjob. Or take NIH's route, within a few days of the swarm's end: the last word of `jobhist`'s `Submission Command` is the path of `swarm.batch`, and swarm keeps one `cmd.N` per subjob in that directory, also reachable as `/spin1/swarm/$USER/JOBID/` (a daily cleanup deletes these about 5 days after the swarm ends). For an unbundled swarm, `cat cmd.3 cmd.5 cmd.18 > /data/$USER/new_swarm` and check `wc -l` (expect 3). A bundled or packed swarm's `cmd.N` holds several lines, so inspect it first.

```bash
# on Biowulf (login node) — the user runs this
cd /data/$USER/rna-seq/oligos          # the original Submission Path: relative paths in lines resolve here
swarm -g 8 -t 2 --time 160:00:00 /data/$USER/new_swarm
```

For pipelines that often need partial reruns, the FAQ suggests Snakemake (WORKFLOWS.md).

## Stale advice on the official pages

- **Default walltime:** the swarm page says 2 h (`#time`) and `04:00:00` (usage block) → always pass `--time`, and confirm `--time=` in `--devel`.
- **Default memory:** 1.5 GB per the text, "1 gb" in older `--devel` samples → trust your own `--devel` output.
- **Memory thresholds:** "norm has nodes with a maximum of 248GB", largemem above 373 GB, and `--partition largmem` → swarm itself sends only `-g` above 750 to `largemem` (Failures and reruns); the partition is `largemem`.
- **Cores per node:** "8, 16, or 32 cores" → HARDWARE.md.
- **`--sbatch` precedence contradicts itself** (usage: swarm's CPU and memory options win; `#sbatch`: `--sbatch` overrides; `#directives`: lowest) → swarm now refuses time, CPU, and memory options inside `--sbatch`; read the `--devel` sbatch line for the rest.
- **Fixed-output-path example:** relative `cd` paths start "from your home directory", yet subjobs start in the submission directory → absolute paths.
- **Line-continuation example:** `jellyfish count -C` lacks its trailing `\`, and `${#KMER}` would be cut at the `#` → end every continued line in `\`; lines containing `#` need `--no-comment`.
- **`-t auto`** (fmriprep page, 2020 cheat sheet) → swarm has rejected it since March 2025; give `-t N`.
- **Source tarball:** https://hpc.nih.gov/download/swarm.tgz is swarm 23.6 (2023: `-p` capped at 2, no prolog, epilog, or joblog) → the current source is https://github.com/NIH-HPC/swarm.
- **Legacy examples:** `qstat`, `python/2.7`, `blast/2.2.26` with `fastacmd` → current commands and modules (MODULES.md).
- **FAQ generator** (`make_swarmfile.sh`): its header says it submits the swarm, but it doesn't, and it appends with `>>`, so rerunning it duplicates lines.

## Going further

- https://hpc.nih.gov/apps/swarm.html — the swarm page. Deep links: [usage](https://hpc.nih.gov/apps/swarm.html#usage) (every option), [bundling](https://hpc.nih.gov/apps/swarm.html#bundling), [-p](https://hpc.nih.gov/apps/swarm.html#p), [--time](https://hpc.nih.gov/apps/swarm.html#time), [environment](https://hpc.nih.gov/apps/swarm.html#environment), [lscratch](https://hpc.nih.gov/apps/swarm.html#lscratch), [prolog/epilog](https://hpc.nih.gov/apps/swarm.html#prolog_epilog), [--sbatch](https://hpc.nih.gov/apps/swarm.html#sbatch), [--devel](https://hpc.nih.gov/apps/swarm.html#devel), [dependencies and exit status](https://hpc.nih.gov/apps/swarm.html#dependency).
- https://hpc.nih.gov/docs/FAQ.html#swarmfile — generating a swarmfile; [#swarm_resubmit](https://hpc.nih.gov/docs/FAQ.html#swarm_resubmit) and [#swarm_select](https://hpc.nih.gov/docs/FAQ.html#swarm_select) — rerunning a whole swarm or some subjobs.
- https://hpc.nih.gov/docs/job_dependencies.html — dependency types and pipeline scripts.
- https://hpc.nih.gov/training/intro_biowulf — Biowulf Online Class: swarm videos and hands-on exercises.
- https://github.com/NIH-HPC/swarm — swarm's current source (`swarm`, `run_threaded_swarm_commands`), for behavior the page leaves undocumented.
- Per-application swarmfiles: the `#swarm` section of the app's page (lookup in SKILL.md).
- Live help: `swarm --help`, `man swarm`, `swarm -V`; `batchlim` for current walltime and array-size limits.
