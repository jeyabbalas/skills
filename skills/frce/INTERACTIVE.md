How the user gets a shell, IDE, or desktop on a compute node without OnDemand, and how a server you start in a job reaches their browser: `srun --pty` sessions and tmux, ssh into a job's node, choosing a home for a long agent session, VS Code through `frce-cpu` and `frce-gpu`, X11, VNC, NoMachine, and SSH tunnels. Starting and ending a session is the user's (each one is a job: ground rules in SKILL.md), as is every step on their own computer; you work inside the session and hand over the rest as exact commands. OnDemand, which needs none of this: ONDEMAND.md. Partitions, walltime, and GPU request syntax: JOBS.md. SSH clients, keys, and X servers on the user's computer: ACCESS.md.

Table of contents

- [Interactive shells with srun](#interactive-shells-with-srun)
- [Choosing a home for an agent session](#choosing-a-home-for-an-agent-session)
- [VS Code on a compute node](#vs-code-on-a-compute-node)
- [X11 applications](#x11-applications)
- [VNC desktops](#vnc-desktops)
- [NoMachine](#nomachine)
- [Tunnels to notebooks and web apps](#tunnels-to-notebooks-and-web-apps)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Interactive shells with srun

FRCE has no `sinteractive`: a shell on a compute node is `srun --pty`, started from the login node or the transfer node (both can submit). Name the partition, CPUs, memory, and time every time, which the official examples don't ([Stale advice](#stale-advice-on-the-official-pages)). Sessions are jobs: they count against the user's per-partition caps, the submit filter moves them by `--time`, and a `norm` session may overrun its `--time` by 60 minutes (JOBS.md (Partitions and walltime)).

```bash
# on the FRCE login node, inside tmux — the user runs one of:
srun -p norm --cpus-per-task=8 --mem=32g --time=1-00:00:00 --pty bash
srun -p gpu --gres=gpu:l40s:1 --cpus-per-task=8 --mem=64g --time=4:00:00 --pty bash   # GPU types and shares: JOBS.md (GPUs)
```

- Time left, from inside: `squeue -j "$SLURM_JOB_ID" -h -o %L`. The user can lower a session's time limit but not raise it (JOBS.md (Changing or cancelling a job)), so ask for enough up front.

**tmux.** The `srun` client runs in the user's login shell, so a dropped SSH connection or VPN ends the session unless that shell lives in tmux or screen, both installed on the login node (tmux also on the compute node checked; Sept 2026):

```bash
# on the FRCE login node — the user runs:
tmux new -s work          # start srun inside it; detach with Ctrl-b d (screen: screen -S work, Ctrl-a d)
tmux attach -t work       # after reconnecting, on the host that started it: batch and batch2 keep separate tmux servers (screen -r work)
```

**What ends a session**, besides its walltime, `exit`, `scancel`, and going over `--mem`: losing its `srun` client, which runs on the host the user started it from, to a dropped connection without tmux or a reboot of that host (the login node's monthly one spares jobs, not this client: ACCESS.md (Status and maintenance)); or the login node's 10 CPU-minute limit (ACCESS.md (Connecting)) killing that client or the tmux server, which heavy terminal output over days can do (the user's `ps -o pid,time,cmd -u $USER` on the login node shows their totals).

**ssh into a job's node.** Compute nodes run `pam_slurm_adopt` (live, Sept 2026): from the login node, the user can `ssh` to a node where they hold a job, and the session joins that job, sharing its CPUs, memory, and end, without `SLURM_*` variables. (Logins to nodes without a job of theirs are untested; you never ssh yourself: ground rule 7.) With tmux started on the node, work survives dropped connections and login-node reboots:

```bash
# on the FRCE login node — the user runs:
sbatch -p norm --cpus-per-task=8 --mem=32g --time=1-00:00:00 -J hold --wrap 'sleep infinity'
squeue --me -n hold -h -o %N     # the node, e.g. cn126, once the job runs
ssh cn126                        # then on the node: tmux new -s work; later: ssh cn126, tmux attach -t work
```

**Idle sessions.** "Do not keep `srun` sessions open and idle for long periods, as the allocated resources for these sessions are not available to other users. This is particularly important when requesting GPU systems." ([policies](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/MiscellaneousPoliciesandGuidelines)) Tell the user when a session's work is done so they can `exit` it (a held job: `scancel -u $USER -n hold`). Keep GPU work in its own GPU session or batch job, sized for that step, rather than parking in a GPU session between steps.

## Choosing a home for an agent session

Each home is a job the user starts; run SKILL.md's where-am-I check first in any of them.

| Home | The user starts it with | Lasts up to | Ends early on | Suits |
|---|---|---|---|---|
| `srun --pty` shell held by tmux or a NoMachine desktop | SKILL.md's restart recipe | the partition's limit (JOBS.md (Partitions and walltime)) | `exit`, `scancel`, a login-host reboot, a dropped connection without tmux | long work, sized per session |
| tmux on the node of a batch job | [ssh into a job's node](#interactive-shells-with-srun) | its `--time` | `scancel` | long work that must survive disconnects and login-node reboots |
| terminal in an OnDemand app | ONDEMAND.md (Working inside a session) | the session's wall time | Delete | work that must outlive the user's laptop, VPN, and the login node; GUIs alongside |
| local VS Code on `frce-cpu` | [VS Code on a compute node](#vs-code-on-a-compute-node) | 24 h | `scancel` | editing and light agent work: 1 CPU, 20 GB |
| local VS Code on `frce-gpu` | the same | 2 h | `scancel` | short checks on one GPU of any type: 1 CPU, 8 GB |

- `frce-*` terminals and ssh sessions into a job have no `SLURM_*` variables: SKILL.md's third where-am-I row applies. A `frce-*` session has one CPU (`nproc` prints 1): run builds and tests single-threaded there, and ask the user for a bigger home for anything heavier.
- An agent inside VS Code, as an extension or in its terminal, runs under VS Code's server on the node. After the laptop sleeps or the VPN drops, the user reconnects (the allocation is reused) and you check that the agent's work is still running.
- `frce-gpu`'s 2 h rarely covers an agent session: work from a CPU home and hand GPU steps to batch jobs the user submits (JOBS.md (GPUs)).

## VS Code on a compute node

FRCE's [VS Code within Slurm](https://ncifrederick.cancer.gov/staff/FRCE/VSCodeSlurm) route runs local VS Code inside an allocation: "Your terminal, extensions, and tools all run on a compute node, not the login node." Pointing Remote-SSH at `batch.ncifcrf.gov` instead would run VS Code's server on the login node, under its CPU limit. The setup is the user's, on their computer:

1. Install the **Remote - SSH** extension (Microsoft).
2. Log in to batch without prompts, because "VS Code cannot stop to ask for a password partway through connecting": a passphrase-protected key loaded in ssh-agent (ACCESS.md (SSH keys and clients)). Check: `ssh USERNAME@batch.ncifcrf.gov hostname` prints `fsitgl-head01p.ncifcrf.gov` with no prompt.
3. Add the hosts, typed with plain spaces: a copy pasted from the page can carry its non-breaking spaces, which ssh rejects with `Bad configuration option`.

```text
# ~/.ssh/config on the user's computer (Windows: C:\Users\<you>\.ssh\config) — the user adds:
Host frce-*
    User USERNAME
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

Host frce-cpu
    ProxyCommand ssh -o LogLevel=QUIET -o ForwardAgent=yes %r@batch.ncifcrf.gov /mnt/nasapps/production/VSCode/vscode-alloc/vscode-alloc cpu

Host frce-gpu
    ProxyCommand ssh -o LogLevel=QUIET -o ForwardAgent=yes %r@batch.ncifcrf.gov /mnt/nasapps/production/VSCode/vscode-alloc/vscode-alloc gpu
```

   `ssh -G frce-cpu | grep -i proxycommand` checks that the file parses, without connecting. On Windows, if VS Code can't run the ProxyCommand, spell out `C:\Windows\System32\OpenSSH\ssh.exe` in place of `ssh`.
4. Connect to Host `frce-cpu` or `frce-gpu`. "The first connection takes a minute"; if the allocation queues longer than VS Code's "Remote.SSH: Connect Timeout", raise that setting. In its terminal, `hostname` shows `fsitgl-hpcNNNp` and `squeue --me` the `vscode-cpu` or `vscode-gpu` job.

What `vscode-alloc` does on the login node (live, Sept 2026; `cat /mnt/nasapps/production/VSCode/vscode-alloc/vscode-alloc` shows it):
- **A key without a passphrase.** If `~/.ssh/id_rsa` doesn't exist on FRCE, it silently creates one (RSA 4096, no passphrase), and it adds `id_rsa`'s public key to `~/.ssh/authorized_keys` either way. The key only serves the hop to the compute node, but home is shared, so whoever holds the file can log in as the user on any FRCE host, against FRCE's key rule (ACCESS.md (SSH keys and clients)). Tell the user before their first connection: the file must never leave FRCE or be reused, and if they stop using `frce-*`, they can delete it and its `authorized_keys` line; the bigger-allocation route below creates none.
- **A fixed allocation.** It reuses a running job named `vscode-cpu` or `vscode-gpu`, or else waits in `salloc --no-shell` for a new one. `frce-cpu` is `--partition=norm -t 24:00:00`: 1 CPU and 20 GB (`norm`'s defaults) for 24 h. `frce-gpu` is `--partition=gpu --gres=gpu:1 -t 2:00:00`: one GPU of whatever type is free, 1 CPU, and 8 GB for 2 h. The user's config can't change these.
- **An adopted connection.** It then runs `ssh -W NODE:22 NODE`, so VS Code's server and terminals join the job through `pam_slurm_adopt` ([ssh into a job's node](#interactive-shells-with-srun)): no `SLURM_*` variables, one CPU.

Rules and limits:
- "Use `frce-cpu` unless you actually need a GPU." "You can hold one CPU and one GPU session at the same time." "Reconnecting reuses your existing allocation if one is still running"; once it expires, VS Code disconnects, and reconnecting gets a fresh one. The script reuses only a running job, so a retry after a connect timeout can queue a second allocation beside the first: check `squeue --me -n vscode-cpu,vscode-gpu`; the user cancels extras by job ID.
- "**Closing VS Code does not release your allocation.**" The user releases it from the login node, never you, since from inside it would end your own session:

```bash
# on the FRCE login node — the user runs:
scancel -u $USER -n vscode-gpu      # as soon as the GPU work is done: "GPUs are scarce and shared"
scancel -u $USER -n vscode-cpu
```

- The config's trade-offs: `StrictHostKeyChecking no` with `UserKnownHostsFile /dev/null` skips host-key checks on the hop to the compute node, which changes with every allocation (the hop to batch is still checked), and `ForwardAgent=yes` makes the user's agent usable from the login node while connected. Keep both inside these `frce-*` entries.
- **A bigger allocation.** VS Code can attach to any job the user holds the same way (untested with VS Code): the user starts the job sized for the work ([ssh into a job's node](#interactive-shells-with-srun)), writes its node into this entry, and connects to `frce-node`. It inherits the `frce-*` settings above, and the user's own key makes both hops.

```text
# ~/.ssh/config on the user's computer — the user adds, and updates HostName for each job:
Host frce-node
    HostName cn126.ncifcrf.gov
    ProxyJump USERNAME@batch.ncifcrf.gov
```

- VS Code in the browser (code-server) instead: ONDEMAND.md.

## X11 applications

The user needs a local X server and a forwarding login (clients and settings: ACCESS.md (SSH keys and clients)); `srun --x11` carries it to the node:

```bash
# on the user's computer — the user runs:
ssh -Y USERNAME@batch.ncifcrf.gov
# on the FRCE login node — the user runs:
echo "$DISPLAY"          # empty: the login isn't forwarding X, or no X server runs on the user's computer
srun -p norm --cpus-per-task=4 --mem=16g --time=4:00:00 --x11 --pty bash
```

- With `DISPLAY` empty, `srun --x11` stops with `No DISPLAY variable set, cannot setup x11 forwarding`.
- After reattaching tmux from a new login, only new tmux windows get the new `DISPLAY`; start `srun --x11` from one of those.
- X11 crawls with 3D or large images: "VNC will likely provide better performance, especially if the application uses GPUs" ([InteractiveAccess](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/InteractiveAccess)), and the OnDemand FRCE Desktop needs no local X server at all (ONDEMAND.md).
- You can't see or drive these windows. For scripted work, run the program in its batch or headless mode (MATLAB: APPLICATIONS.md (MATLAB)).

## VNC desktops

A full desktop on a compute node, reached through a tunnel: the [InteractiveAccess](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/InteractiveAccess) recipe, fixed. Every step is the user's, since the VNC password is theirs:

```bash
# on the FRCE login node, inside tmux — the user runs:
srun -p norm --cpus-per-task=4 --mem=16g --time=8:00:00 --pty bash
# on the compute node (inside the session) — the user runs:
vncpasswd                # first time only: the VNC password, set before any server starts
vncserver                # note the "New" line, e.g. fsitgl-hpc082p.ncifcrf.gov:1; display :N listens on port 5900+N
# on the user's computer (NIH network or VPN) — the user runs, and leaves the window open:
ssh -N -L 5901:fsitgl-hpc082p.ncifcrf.gov:5901 USERNAME@batch.ncifcrf.gov
```

The user then opens a VNC viewer ([TurboVNC](https://www.turbovnc.org); installing it needs admin rights) at `localhost:5901` (in PuTTY: as under [Tunnels](#tunnels-to-notebooks-and-web-apps), with port 5901). Take the node and display from the "New" line, not from the example.

To finish, the user closes the viewer, runs `vncserver -kill :1` on the node, and `exit`s the `srun` shell. VirtualGL's `vglrun` (GPU-rendered OpenGL) is on the login node (Sept 2026); `command -v vglrun` in the session checks the compute node. FRCE's `vnc.sh` template runs the server half as a batch job (fix it first: MODULES.md (The frce module and example scripts)). The OnDemand FRCE Desktop does all of this in a browser, with a GPU if asked (ONDEMAND.md), and the page itself recommends it.

## NoMachine

`nx.ncifcrf.gov` serves persistent desktops on "a system that has the same file systems available as FRCE and can submit jobs to the FRCE scheduler" ([NoMachine](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/NoMachine)). It is a shared login host, where you never run (SKILL.md); anything heavier than editing or submitting goes in an `srun` session started from its terminal (`--x11` for GUI programs). A NoMachine session keeps running after its window closes, so an `srun` shell inside it survives the user's disconnects, as under tmux.

FRCE's page defers to Biowulf's instructions ("Replace any reference to `biowulf.nih.gov` with `nx.ncifcrf.gov`"), which Biowulf withdrew when it retired NoMachine on 7 Aug 2025. Translated, for the user:

1. Easiest: the web client at https://nx.ncifcrf.gov. Otherwise, install the NoMachine Enterprise Client from https://www.nomachine.com; installing on macOS, and the first run on Windows, need admin rights.
2. In the client, add a connection with Host `nx.ncifcrf.gov` and Protocol SSH, as Biowulf's page had it. Which protocols FRCE's server accepts is undocumented and untested: if SSH fails, the user tries NX. Log in with the NIH username and password, and don't let the client save the password ("against NIH security policy", per Biowulf's page).
3. When done, the user `exit`s the `srun` shells, then logs out from the desktop's menu: closing the window leaves both running and holding resources.

## Tunnels to notebooks and web apps

A server in a job (Jupyter, TensorBoard, Shiny, any web app) reaches the user's browser through an SSH tunnel via the login node; OnDemand's Jupyter, RStudio, and Shiny apps need none (ONDEMAND.md). FRCE has no `--tunnel` and no `$PORT1`: pick a port yourself and bind the server to the node's own name, since the tunnel's last leg runs from the login node to NODE:PORT. That address is reachable from anywhere inside FRCE, so the server's token or password is its only lock: never turn it off, and keep the log that holds it private.

Jupyter, as the [Jupyter Notebooks](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/JupyterNotebooks) page's manual route should read:

```bash
# on the compute node (inside your session)
module load jupyter/7.1.3                               # pinned: MODULES.md (Loading and pinning versions)
port=$(shuf -i 61000-65000 -n 1)                        # random, so users sharing a node don't collide
log=jupyter.$port.log; : > "$log"; chmod 600 "$log"     # the log will hold the access token
nohup jupyter-notebook --no-browser --ip="$(hostname -f)" --port="$port" > "$log" 2>&1 < /dev/null &
echo $! > "jupyter.$port.pid"                           # to stop it later: kill "$(cat jupyter.$port.pid)"
sleep 15; url=$(grep -o 'http://[^ ]*token=[^ ]*' "$log" | head -1); echo "$url"   # empty: wait, grep again
p=${url#http://*:}; p=${p%%/*}                          # the port it took (Jupyter moves if $port is busy)
curl -s --noproxy '*' -o /dev/null -w '%{http_code}\n' "http://$(hostname -f):$p/"   # 200 or 302: it answers
printf 'ssh -N -L 8888:%s:%s %s@batch.ncifcrf.gov\n' "$(hostname -f)" "$p" "$USER"   # the user's tunnel
printf 'http://localhost:8888/%s\n' "${url#http://*/}"                              # the user's URL
```

The user runs the printed `ssh` line on their computer (NIH network or VPN), leaves that window open, and opens the printed URL. In PuTTY: Connection → SSH → Tunnels, Source port `8888`, Destination `NODE:PORT` from the `ssh` line, Add, then Apply (right-click the title bar → Change Settings on a running login). The same pattern serves anything that takes a host and a port:

```bash
# on the compute node (inside your session) — e.g. TensorBoard, or Shiny on the second line:
port=$(shuf -i 61000-65000 -n 1)
nohup tensorboard --logdir runs --host "$(hostname -f)" --port "$port" > "tb.$port.log" 2>&1 < /dev/null &
# nohup Rscript -e "shiny::runApp('app', host='$(hostname -f)', port=$port)" > "shiny.$port.log" 2>&1 < /dev/null &
printf 'ssh -N -L 8888:%s:%s %s@batch.ncifcrf.gov\n' "$(hostname -f)" "$port" "$USER"   # then http://localhost:8888/
```

TensorBoard and Shiny have no login: while they run, anyone inside FRCE who finds the port can open them. Serve only what every FRCE user may see this way; otherwise use an OnDemand app. What to log to TensorBoard: DEEP-LEARNING.md.

If the browser can't connect, the `ssh -N -L` window must still be open, with the node and port from the log; `000` from the `curl` check means nothing listens yet or the server died (read its log).

FRCE's `jupyter.sh` template runs the server as a batch job and mails the user the tunnel command; fix its resources and time before the user submits it (MODULES.md (The frce module and example scripts)). If the mail never arrives or its URL is wrong, read `.jupyter_session` in the submission directory; the page also suggests moving `~/.jupyter` aside (`mv ~/.jupyter ~/.jupyter_bak`, with the user's OK).

## Stale advice on the official pages

- InteractiveAccess's "general command", `srun --export ALL --pty -p short bash`, dies at `short`'s 30 minutes; QuickStart's `srun --pty -p norm --ntasks=1 bash` and the Jupyter page's bare `srun --pty bash` get `norm`'s defaults (JOBS.md (Flags and defaults)), held five days if forgotten → `srun -p norm --cpus-per-task=N --mem=Ng --time=... --pty bash`.
- InteractiveAccess's VNC steps set the password with `vncpasswd` after starting `vncserver` → run it first. Its hostname is typed with a non-breaking hyphen (U+2011), which breaks copy-paste → type `fsitgl-hpc082p` by hand. "Session → Connection → SSH → Tunnels" → Connection → SSH → Tunnels.
- The Jupyter page's manual route tunnels to `fsitgl-hpc085`, which has no DNS record, through the unqualified `fsitgl-head01p` → `fsitgl-hpc085p.ncifcrf.gov` (or `cn085.ncifcrf.gov`) through `batch.ncifcrf.gov`. Its fixed port, 64000, may be another user's on the node → the recipe above. Its PuTTY step shows a URL where Source port and Destination belong, and "the 8888 in Step5 should match 8888 in Step4" means Steps 5 and 6.
- VS Code within Slurm says "leave the passphrase empty" → a passphrase plus ssh-agent (ACCESS.md). Its first test, `ssh batch.ncifcrf.gov hostname`, omits the username → `ssh USERNAME@batch.ncifcrf.gov hostname`. Its config indents with non-breaking spaces → type plain spaces. It doesn't say what `vscode-alloc` requests or that it creates a key without a passphrase → [VS Code on a compute node](#vs-code-on-a-compute-node).
- The older [vscode IDE](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/vscodeIDE) page connects Remote-SSH to the cluster and requests a node from VS Code's terminal, which leaves VS Code's server on the login node → `frce-cpu` or `frce-gpu`. Its VNC route for step-by-step debugging on a GPU node predates `frce-gpu`, whose VS Code debugger runs there.
- The NoMachine page's pointer, https://hpc.nih.gov/docs/nx.html, now shows only Biowulf's retirement notice, and "More local documentation will be forthcoming" hasn't come → the steps above.

## Going further

- FRCE: [Interactive and GUI access](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/InteractiveAccess) · [VS Code within Slurm](https://ncifrederick.cancer.gov/staff/FRCE/VSCodeSlurm) · [Jupyter Notebooks](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/JupyterNotebooks) · [NoMachine](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/RemoteAccessMethods/NoMachine) · [Miscellaneous Policies and Guidelines](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/MiscellaneousPoliciesandGuidelines).
- Biowulf docs, which need translation (`sinteractive` → `srun --pty`; Biowulf's `$PORT1` and localhost-bound servers don't carry over): [SSH tunneling](https://hpc.nih.gov/docs/tunneling/), with PuTTY in [#windows](https://hpc.nih.gov/docs/tunneling/#windows) · [VS Code over Remote-SSH on Windows](https://hpc.nih.gov/apps/vscode.html#win) · [Jupyter pitfalls](https://hpc.nih.gov/apps/jupyter.html#pitfalls).
- Upstream: [srun](https://slurm.schedmd.com/srun.html) (`--pty`, `--x11`) · [pam_slurm_adopt](https://slurm.schedmd.com/pam_slurm_adopt.html) · [tmux](https://github.com/tmux/tmux/wiki) · [VS Code Remote-SSH](https://code.visualstudio.com/docs/remote/ssh) · [TurboVNC](https://www.turbovnc.org) · [NoMachine](https://www.nomachine.com).
- Live: `squeue --me`, `squeue -j "$SLURM_JOB_ID" -h -o %L` (inside a session), `cat /mnt/nasapps/production/VSCode/vscode-alloc/vscode-alloc` (what `frce-*` requests), `ssh -G frce-cpu` (the user's computer), `man srun`.
