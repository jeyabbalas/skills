How a server on a compute node — Jupyter, TensorBoard, RStudio Server, Shiny, a Spyder kernel, any dashboard — reaches the user's browser, and who does which step: you run the server inside the job, and the user opens the tunnel from their own computer. Each server's own command lives with its app: JUPYTER.md, DEEP-LEARNING.md (TensorBoard), R.md (RStudio Server, Shiny), PYTHON.md (Spyder). Apps that HPC OnDemand offers (Jupyter, RStudio, VS Code, Shiny) need no tunnel and are NIH's recommended route (ACCESS.md); tunnels are for everything else and for servers you run in your own session. `sinteractive` options are in JOBS.md.

Table of contents

- [How the tunnel works](#how-the-tunnel-works)
- [Who does what](#who-does-what)
- [Start the server and hand off](#start-the-server-and-hand-off)
- [The user's side, per OS](#the-users-side-per-os)
- [When `$PORT1` is missing](#when-port1-is-missing)
- [Reconnecting](#reconnecting)
- [Troubleshooting](#troubleshooting)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## How the tunnel works

- **Two legs** ([tunneling](https://hpc.nih.gov/docs/tunneling/)): (1) the user's computer → the login node, opened by the user with `ssh -L N:localhost:N`; (2) the login node → the compute node, created by `sinteractive -T`/`--tunnel`. N is the same port at every hop.
- `--tunnel` puts the port in `$PORT1`. Repeat the short flag for more: `-TT` gives `$PORT1` and `$PORT2`, and the Spyder recipe uses `-TTTTT`. Run one server per port. The session's banner prints the user's local command, with one `-L` per port: `ssh  -L 33327:localhost:33327 biowulf.nih.gov`.
- **Bind the server to localhost** on `$PORTn`, as every NIH example does. Never use `0.0.0.0` or the node's hostname (advice: that opens the server to the whole cluster network).
- **Keep authentication on** (advice): leg 2 ends on the shared login node, where other users could reach the port, so the server's token or password is its only lock. Never start a server with an empty token, and give the tokenized URL to the user only.

## Who does what

| Step | Who | Where |
|---|---|---|
| Start the session with `--tunnel` (`-TT` for two servers), inside tmux: SKILL.md's restart recipe | user | login node |
| Start the server on localhost:`$PORT1`, check it, read its URL | you | compute node |
| Run the `ssh -L` line, leave that window open, and open the URL | user | their computer |
| Re-open a dropped tunnel | user | their computer |
| Stop the server; later, `exit` the session | you; then the user | compute node |

The local leg is always the user's, even when you run on their computer: it logs in to Biowulf with their credentials. Off the cluster, give the user the server command as well, labeled `# on the compute node`.

## Start the server and hand off

```bash
# on the compute node (inside the job)
echo "node=$(hostname -s) PORT1=${PORT1:-unset}"      # unset: see "When $PORT1 is missing"
cd /data/$USER/myproject
log=server.$PORT1.log; : > "$log"; chmod 600 "$log"   # the log will hold the access token
nohup SERVER_COMMAND > "$log" 2>&1 < /dev/null &      # bound to localhost on $PORT1
echo $! > server.$PORT1.pid
tail -n 20 "$log"                                     # repeat until the URL appears
curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' "http://localhost:$PORT1/"
printf 'ssh -L %s:localhost:%s %s@biowulf.nih.gov\n' "$PORT1" "$PORT1" "$USER"
```

- Background the server (generic advice): in the foreground it blocks your tool call until it exits. It still ends with the job.
- The `curl` check (generic) should print an HTTP code such as 200 or 302: the server answers on the node, so any later failure is in the tunnel. `000` means nothing listens on `$PORT1` (yet). `--noproxy` keeps the request off the compute-node web proxy.
- The port in the logged URL must equal `$PORT1`. Some servers silently move to another port when theirs is busy (Jupyter does), and the tunnel can't reach a moved server.
- Give the user the URL exactly as logged, but with the host set to `localhost` if the server printed a node name or `127.0.0.1`.
- The `printf` output is the user's exact local command: on the node, `$USER` is their NIH username. It works in macOS and Linux terminals, WSL, and Windows PowerShell.
- When the user is done: `kill "$(cat server.$PORT1.pid)"`, then delete the log.

Handoff text (fill in the values; for Windows users without ssh, add the PuTTY steps below):

```text
On your computer (on the NIH network or VPN), open a NEW terminal (PowerShell on Windows) and run:
    ssh -L 33327:localhost:33327 jdoe@biowulf.nih.gov
Log in and leave that window open. Then open this in your browser:
    http://localhost:33327/lab?token=...
Tell me when you're finished so I can stop the server.
```

## The user's side, per OS

- **macOS, Linux, WSL, Windows PowerShell**: the `ssh -L` line in a new terminal, left open, then `http://localhost:N/...` in a local browser. Several ports go in one command, one `-L N:localhost:N` each. Windows 10 includes OpenSSH, "although it may be disabled"; then use PuTTY, or WSL's Linux ssh ([tunneling#windows](https://hpc.nih.gov/docs/tunneling/#windows)).
- **Username**: the lines printed by the banner and `reconnect_tunnels` may omit it, and ssh then sends the local username. Add `NIHUSER@` when the two differ. On Windows the local name carries a domain prefix, so in PowerShell use `$env:username@biowulf.nih.gov` or type the NIH username ([ssh#windows](https://hpc.nih.gov/docs/ssh.html#windows)).
- **PuTTY**:
  1. Double-click "Default Settings" and set Host Name to `biowulf.nih.gov`.
  2. Under SSH → Tunnels, set Source port `N` and Destination `localhost:N`, then click **Add** (once per port).
  3. Click **Open**, log in, leave that window alone, and browse to `http://localhost:N/...`.

## When `$PORT1` is missing

`$PORT1` is set only in the shell that `sinteractive --tunnel` started and in its children; a Remote-SSH or other SSH login to the node lacks it (ACCESS.md).

| Situation | Do this |
|---|---|
| No tunnel exists: the session was started without `--tunnel`, or you're in an OnDemand app's terminal | NIH documents no way to add a tunnel to a running job. If the app is on OnDemand, the user can launch it there (it takes an interactive-job slot: JOBS.md). Otherwise the user starts a `--tunnel` session and restarts you in it. |
| The session has a tunnel, but your shell lacks `$PORT1` (e.g. VS Code Remote-SSH to its node) | The tunnel lasts as long as the job. Ask the user for the port from the banner or from `reconnect_tunnels`, then `export PORT1=<port>` and continue as above. |

Never improvise a leg: no `ssh -R` or `ssh -L` from the node to the login node (ground rule 7), and no random port, since only `$PORTn` ports are forwarded.

## Reconnecting

- Tunnel window closed or laptop asleep: the user re-runs the same `ssh -L`, "without losing anything as long as your Slurm job is still alive" ([tunneling](https://hpc.nih.gov/docs/tunneling/)).
- `reconnect_tunnels`, run by the user on the login node, prints the command for all open interactive sessions:

```text
(biowulf)$ reconnect_tunnels
#### INFO: 1 tunnels set up
ssh  -L 45000:localhost:45000 biowulf.nih.gov
```

- On macOS or Linux, the user can make this one step with a local alias (add `NIHUSER@` if usernames differ). `tun` opens every tunnel and leaves a login-node shell open. It runs `reconnect_tunnels` on the login node, so it is never yours to run:

```bash
alias tun='$(ssh biowulf.nih.gov /usr/local/slurm/bin/reconnect_tunnels)'
tun
```

- A VPN drop without tmux ends the session, and you and your server with it (JOBS.md). In the new session, restart the server: the port changes, so hand over a new `ssh -L` line.

## Troubleshooting

| Symptom | Cause → fix |
|---|---|
| Browser: connection refused at `localhost:N` | The user's `ssh -L` isn't running or uses another port → run the exact line in a separate terminal and leave it open |
| `curl` on the node prints `000` | Nothing listens on `$PORT1` → read the log; restart the server |
| The server reports its port in use | A collision → use `$PORT2` if the session has one; otherwise the user starts a new `--tunnel` session |
| Local ssh: `bind ... Address already in use` | Port N is busy on the user's computer, often an old tunnel → close it, or map a free local port: `ssh -L 8890:localhost:N ...`, then browse to `localhost:8890` (generic ssh) |
| ssh rejects the login | The local and NIH usernames differ → add `NIHUSER@` |
| The page asks for a token or password, or says "permission denied" | A stale link: every server start makes new credentials → send the URL from the current log |

## Stale advice on the official pages

- TensorBoard page: if the port is taken, "select another random port … and try tunneling again" → only `$PORTn` ports are forwarded; switch to another `$PORTn` or a new `--tunnel` session.
- TensorBoard's example prints `http://cn0619:45000` → the user always browses to `http://localhost:N`, whatever host a server prints.

## Going further

- https://hpc.nih.gov/docs/tunneling/ — the two legs and `--tunnel`; macOS/Linux and `reconnect_tunnels` (#maclinux); Windows via PowerShell, WSL, or PuTTY, with screenshots (#windows).
- https://hpc.nih.gov/docs/userguide.html#int — `sinteractive` options including `-T`, and tmux for surviving disconnects.
- https://hpc.nih.gov/docs/ssh.html#windows — ssh from PowerShell and the `$env:username` fix.
- https://hpc.nih.gov/docs/deeplearning/tensorboard.html#conn — a worked tunnel for TensorBoard, with port-collision notes.
- https://hpc.nih.gov/apps/python.html#spyder — a five-port tunnel for a Spyder kernel.
- https://hpc.nih.gov/ondemand/ — the apps that need no tunnel.
- Live: `echo $PORT1` (on the node), `sinteractive -h`, `reconnect_tunnels` (the user, on the login node), `man ssh` (see `-L`).
