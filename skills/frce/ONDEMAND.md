Open OnDemand on FRCE (https://ondemand.ncifcrf.gov): getting in, the apps and what their launch forms offer, sessions, the file browser, working and running an agent inside a session, and what to do when the portal misbehaves. Everything in the browser is the user's: signing in, filling in and launching a form (a submission: ground rules in SKILL.md), connecting, and deleting sessions; you work in a running session's terminal and tell the user what to choose. Partition limits and GPU types behind the form choices: JOBS.md and HARDWARE.md. The Ollama + Jupyter app: LLM-INFERENCE.md. Jupyter kernels, R versions, and R libraries: PYTHON-R.md. Shells, VS Code, and tunnels outside OnDemand: INTERACTIVE.md.

Table of contents

- [Getting in](#getting-in)
- [Apps and their forms](#apps-and-their-forms)
- [Sessions](#sessions)
- [Files and Globus](#files-and-globus)
- [Working inside a session](#working-inside-a-session)
- [When OnDemand misbehaves](#when-ondemand-misbehaves)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Getting in

- The user opens https://ondemand.ncifcrf.gov from the NIH network or VPN ("while on site or connected through VPN") and signs in with "NIH Login", which sends the browser to Microsoft's sign-in page for nih.gov (Sept 2026). You can't sign in or click for them.
- Direct links (Sept 2026), under https://ondemand.ncifcrf.gov/pun/sys/dashboard: `/batch_connect/sessions` (My Interactive Sessions), `/apps/index` (All Apps), and `/batch_connect/sys/<app>/session_contexts/new` (an app's form; `<app>` = `bc_desktop/FRCE` for the FRCE Desktop, `jupyter`, or `rstudio-server`).
- The menu bar holds Files, Interactive Apps, My Interactive Sessions, All Apps, Help (with Restart Web Server), and Log Out, but no Clusters menu (OnDemand's usual login-node shell): terminals come from inside the apps ([Working inside a session](#working-inside-a-session)).

## Apps and their forms

From the menus in FRCE's screenshots, 2025-05 to 2026-08; the live list is on the user's All Apps page, and each form shows its current choices:

| App | Menu group | Form fields | Notes |
|---|---|---|---|
| FRCE Desktop | Desktops | Number of cores; GPU card | an Xfce desktop on a compute node; no wall-time field (below) |
| MATLAB | GUIs | undocumented | also on the desktop and as a Jupyter kernel: APPLICATIONS.md (MATLAB) |
| PyCharm, VMD, Napari | GUIs | undocumented | Napari since 2025-10 |
| Jupyter | Servers | Mode (Jupyter Lab or Jupyter Notebook); Project Root Directory; Number of cores; Allocated wall time (hours); Partition; GPU card | kernels: Matlab, Matlab (Connection), Python 3 (ipykernel), R (RKernel); your own, if it lists them (unchecked): PYTHON-R.md (Jupyter kernels) |
| RStudio Server | Servers | R version; Number of cores; Allocated wall time (hours); Partition; GPU card; Number of allocated GPU's | "on one FRCE node"; which R, and packages: PYTHON-R.md (R on FRCE) |
| Shiny | Servers | undocumented | "R Shiny app" in 2025-05 |
| VS Code (codeserver) | Servers | undocumented | VS Code in the browser |
| Ollama + Jupyter | not shown | LLM-INFERENCE.md (Ollama and Jupyter in OnDemand) | JupyterLab with a local Ollama server on a GPU |

- **Desktop time.** The form has no time field, and a new desktop showed "Time Remaining: 119 hours and 59 minutes": plan on 120 h, `norm`'s limit (Sept 2026). A desktop with a GPU card runs in `gpu`, which has no maximum; whether the form sets a limit there is untested (`squeue --me -o '%.12i %.20j %.9P %.11l'` shows a running session's), so the user deletes a GPU desktop as soon as its work is done.
- **Partition** (Jupyter and RStudio forms), with the form's help text: "short - time limit will be set to 30 minutes", "norm - max 120 hours", "unlimited - unlimited run time", "largemem - unlimited run time with 3TB memory per node", "gpu will be automatically selected if a GPU card is requested". "The wall time selection is important as the job will be killed when the limit is reached", and FRCE's submit filter may move the session to the partition that matches it (JOBS.md (Partitions and walltime)).
- **Cores and memory.** "Number of cores" is the session's CPU cores; RStudio's hint adds "The minimum and maximum will change based on your choice of node type." No form asks for memory: unless the app sets it, the session gets the partition's default per core (JOBS.md (Flags and defaults)), so more cores bring more memory. Check it from inside ([Working inside a session](#working-inside-a-session)).
- **GPU card**, by form:

| Form (screenshot) | Choices |
|---|---|
| FRCE Desktop (2025-09) | none, any, P100, V100, A100 |
| Jupyter (2025-10) | none, any, P100, L40s, V100, A100 |
| RStudio Server (2025-05) | none, any, p100 ("Max count of 3"), v100 ("Max count of 8"), a100 ("Max count of 2"), plus "Number of allocated GPU's" |
| Ollama + Jupyter (2026-08) | LLM-INFERENCE.md |

  Choosing a GPU fixes the partition at `gpu`, and "any" takes whatever type is free. For H200s, which no form offers (Sept 2026), the user runs a batch job or an `srun` session (JOBS.md (GPUs)). CPU and memory shares per GPU: HARDWARE.md (GPUs).
- **Limits.** "Multiple OnDemand sessions may be run simultaneously. Resource limitations are the same as for batch scripts submitted through the command line": sessions count against the user's per-partition caps together with their other jobs (JOBS.md (Partitions and walltime)).
- **Other programs.** "Other applications may be requested by sending an email to the FRCE administrators", but "it may be just as easy to open the Linux desktop and run the app from a terminal window" ([Working inside a session](#working-inside-a-session)).
- **Posit.** Posit Connect runs at https://connect.ncifcrf.gov (Sept 2026), and ABCS presented Posit Workbench "on FRCE" in March 2025 (ACCESS.md (Training)). FRCE's docs mention neither, and only third-party code ties Connect to FRCE. For hosting Shiny apps or dashboards, or for Workbench, the user asks the administrators.

## Sessions

- Launching submits a Slurm job, and nothing is used before that: "Having the OnDemand web page displayed does not consume any resources from the FRCE cluster; this occurs only when you start a session."
- My Interactive Sessions shows a card per session: the app with its Slurm job ID ("Jupyter (49971341)"), state (Queued, Starting, Running), Host (`fsitgl-hpcNNNp.ncifcrf.gov`), Time Remaining, the Session ID (a link to the session's files), Delete, and Connect. A desktop card's "View Only (Share-able Link)" is a watch-only link; FRCE doesn't say who may use it, so treat it as screen sharing.
- Running means the job started, not that the app is ready: allow a minute (Ollama + Jupyter longer: LLM-INFERENCE.md).
- "It is possible to disconnect from a running session by closing the browser tab and re-connect using this screen." The session keeps running, and holding its resources, through closed tabs, sleeping laptops, and VPN drops.
- It ends at its wall time, taking unsaved work with it, or when the user clicks Delete, which cancels the job. "we ask that you stop and delete sessions that are either completed or expected to be idle for some time so that the resources are freed for other users." Remind the user when a session's work is done, GPU sessions first.
- A running session's wall time can't be raised (JOBS.md (Changing or cancelling a job)); the user starts a new one. Sessions appear in `squeue --me` alongside the user's other jobs.

## Files and Globus

- Files opens the file browser, which besides home is "configured to list any directories under /mnt, /mnt/projects, /mnt/gridftp, and /scratch/cluster_scratch that you have write access to, other than those that have world permissions". So read-only areas such as `/mnt/nasapps`, and directories open to the world, don't appear; "Please contact us if you need a specific directory added."
- Bulk data moves by scp, rsync, or Globus, not through the browser (TRANSFER.md). Its Globus button ("File browser with Globus support") opens the current directory in Globus, which works once the user's Globus access is enabled (TRANSFER.md (Globus)).
- Its "Show Dotfiles" option reaches `~/.bashrc` and the like, which is how a startup file that breaks logins gets fixed without a shell (ACCESS.md (Login shell)).
- The file browser is the user's; you work through a session's terminal.

## Working inside a session

- **Terminals.** The FRCE Desktop's terminal emulator, JupyterLab's Launcher → Terminal, RStudio's Terminal tab, and the VS Code (codeserver) terminal each open a shell on the session's node, inside its job. Run SKILL.md's where-am-I check there first.
- **Running an agent.** The user opens a terminal, `cd`s to the project, and starts it. It keeps running with the browser closed and ends with the session. The user sizes the form for the agent's heaviest step, and takes a GPU only if it will stay busy (comparison with other homes: INTERACTIVE.md (Choosing a home for an agent session)).
- **Your allocation** is the form's cores plus the session's memory. `SLURM_CPUS_PER_TASK` is set only if the app requests cores per task, which is untested (`echo "$SLURM_CPUS_PER_TASK $SLURM_NTASKS"` in a session terminal shows it), so read the allocation once and size threads and workers from `NumCPUs` (ground rule 2):

```bash
# on the compute node (inside your session) — read-only:
scontrol show job "$SLURM_JOB_ID" | grep -E -o '(NumCPUs|mem|gres/gpu)=[^ ,]*' | sort -u
```

- **GPUs.** "When GPUs are allocated for the session, the applications are already configured to take advantage of the GPU's capabilities. This includes applications that are run from a terminal command line within a Linux desktop." `nvidia-smi` shows the session's GPUs.
- **GUI programs** started from the desktop's terminal display on the desktop: "Bring up a Desktop, open a terminal window and run `module load relion` followed by `relion`."
- **Jobs from a session.** "it is possible to submit further slurm jobs from within the application": the user's call. Ground rule 1 still holds for you: write the script, check it, and hand over the `sbatch` line.

## When OnDemand misbehaves

| Symptom | Cause → what the user does |
|---|---|
| Dashboard pages hang, error, or show stale state | the user's own OnDemand web server → Help → "Restart Web Server", which "does not affect any other users of the system"; running sessions are jobs and carry on |
| A session stays Queued | "The wait time depends on the number of cores as well as time requested" → fewer cores, a shorter wall time, or GPU "any"; causes: TROUBLESHOOTING.md (Job pending too long) |
| Running, but Connect fails | the app is still starting → wait a minute and retry, then read its `output.log` (below) |
| The app dies at start, or the desktop comes up blank | often shell startup: a `~/.bashrc` that activates conda, switches shells, or prints output (a common cause at OnDemand sites; unconfirmed on FRCE) → read `output.log`; changing `~/.bashrc` needs the user's OK (ground rule 6) |
| A session vanished | its wall time ran out, or it was deleted → `sacct -j JOBID` (MONITORING.md (Finished jobs)); start a new one |

Session logs follow Open OnDemand's standard layout (FRCE doesn't document it), and you can read them from any session:

```bash
# on the compute node (inside your session) — read-only:
ls -t ~/ondemand/data/sys/dashboard/batch_connect/sys/        # jupyter, rstudio-server, bc_desktop/FRCE, ...
tail -n 50 ~/ondemand/data/sys/dashboard/batch_connect/sys/APP/output/SESSION_ID/output.log   # SESSION_ID from the card
```

## Stale advice on the official pages

- The OnDemand page says the desktop's "runtime ... is limited to 7 days" → a new desktop showed 120 h, `norm`'s limit ([Apps and their forms](#apps-and-their-forms)).
- It calls the desktop "Persistent" → it is a Slurm job that ends at its time limit or on Delete; save work before either.
- Its app list omits VMD, Napari, and Ollama + Jupyter, and its "VS Code" link leads to the desktop VS Code page (vscodeIDE), not to the code-server app → the table above.
- The Desktop and RStudio forms offer only P100, V100, and A100, and no form offers H200, though the home page and the login banner announce the L40s and H200 nodes → JOBS.md (GPUs).
- The Relion tip's "contact" link lacks `mailto:` and gives a 404 → email the administrators (ACCESS.md (Support and requests)).
- The [system diagram](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/VisualdiagramFRCESystems) page links OnDemand as `/https://ondemand.ncifcrf.gov`, a 404 → https://ondemand.ncifcrf.gov.
- The linked talk "Using OnDemand on Biowulf (mostly applicable)" shows Biowulf's apps, limits, and sign-in → FRCE's forms and this file govern.

## Going further

- FRCE: [Open OnDemand](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/OpenOnDemand) · [Jupyter Notebooks](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/JupyterNotebooks) (the OnDemand walkthrough) · [Ollama with Jupyter through OnDemand](https://ncifrederick.cancer.gov/staff/FRCE/OOD-Jupyter-Ollama) · [MATLAB](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/ScientificSoftware/UncategorizedSoftware/MATLAB) · the ABCS talk "FRCE User Group: Open-OnDemand" (ACCESS.md (Training)).
- Biowulf's OnDemand, for comparison only (other apps, limits, and sign-in): https://hpc.nih.gov/ondemand/.
- Upstream: [Open OnDemand](https://openondemand.org/) · [user documentation](https://osc.github.io/ood-documentation/latest/) · [resources and videos](https://openondemand.org/resources).
- Live: `squeue --me` (sessions are jobs), `scontrol show job "$SLURM_JOB_ID"` (inside a session), `ls ~/ondemand/data/sys/dashboard/batch_connect/sys/`.
