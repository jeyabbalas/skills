How the user gets onto Biowulf, and where you can run once they have: the NIH network and SSH, keys and Kerberos, HPC OnDemand and its Graphical Session, X11 and `svis`, VS Code, shell startup files, hpcdrive mounts, accounts, maintenance, and reaching staff. Every VPN, password, passphrase, PIV/MFA, browser, and web-form step is the user's: give them the exact command or click path, labeled with where it runs. `sinteractive` options and limits live in JOBS.md, web-app tunnels in TUNNELING.md, Jupyter in JUPYTER.md, and data movement in TRANSFER.md and GLOBUS.md.

Table of contents

- [Where an agent can live](#where-an-agent-can-live)
- [Connecting over SSH](#connecting-over-ssh)
- [When the user can't connect](#when-the-user-cant-connect)
- [SSH keys and Kerberos](#ssh-keys-and-kerberos)
- [HPC OnDemand](#hpc-ondemand)
- [VS Code](#vs-code)
- [Graphical Session, X11, and svis](#graphical-session-x11-and-svis)
- [Shell startup files](#shell-startup-files)
- [Mounting storage locally (hpcdrive)](#mounting-storage-locally-hpcdrive)
- [Accounts, maintenance, and staff](#accounts-maintenance-and-staff)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Where an agent can live

Each home is a compute-node session that the user creates. The policy and the where-am-I check are in SKILL.md.

| Home | The user creates it with | Good to know |
|---|---|---|
| `sinteractive` shell | the restart recipe in SKILL.md | It ends when its login-node shell ends: a VPN drop without tmux, or the monthly reboot. |
| Terminal of an OnDemand VS Code, Jupyter, or RStudio app, or the agent's extension in OnDemand VS Code | the recipe below | It is a job of its own. It survives disconnects (reconnect from My Interactive Sessions) and login-node reboots, for up to 36 h. |
| Local VS Code attached to the `sinteractive` node over Remote-SSH | [VS Code](#vs-code) | The agent runs as a remote extension, or in VS Code's terminal on the node. This is an SSH login, so see the first bullet below. |
| OnDemand dashboard shell; Graphical Session terminal | — | The dashboard shell's host is undocumented. The Graphical Session runs on "special compute nodes" with a fixed 4 CPUs and 8 GB. Run the where-am-I check before starting an agent there; if it doesn't show a compute node, the user starts `sinteractive` from that terminal. |

The OnDemand home, for the user (NIH network or VPN): open the [VS Code form](https://hpcondemand.nih.gov/pun/sys/dashboard/batch_connect/sys/bc_nih_vscode/session_contexts/new) (for Jupyter, `bc_nih_jupyter` in the same URL) and sign in with PIV or MFA. Set resources and walltime, launch, and connect once the session shows Running. Then open a terminal, `cd /data/$USER/<project>`, and start the agent, or use its VS Code extension.

- **An SSH login to your node lacks the job's environment.** In a Remote-SSH window, or any shell reached by `ssh` to the node, `hostname -s` shows `cnNNNN` but `$SLURM_JOB_ID`, `$SLURM_CPUS_PER_TASK`, and `$PORT1` are unset: the "no job ID" row of SKILL.md's where-am-I table. Treat the shell as on-node once the user confirms it is their session's node. Learn the allocation from the user, or check it once, read-only, with `squeue -u "$USER" -w "$(hostname -s)" -o "%i %C %m %L"`; until then, `${SLURM_CPUS_PER_TASK:-2}` falls back to 2. The `Host cn*` ProxyCommand route exists so VS Code can attach; don't `ssh` through it yourself.
- **Approval status.** NIH HPC's Codex page says: "At the time of writing, Codex is the only NIH-approved AI tool currently possible to use outside of a web interface, as far as we are aware, though things change quickly." It adds: "We cannot endorse the use of anything beyond what is described in the hub." The [NIH AI Hub](https://nih.sharepoint.com/sites/NIH-ai) has the current status of AI tools at NIH; the user should check it.
- **Signing an agent in inside OnDemand** ([codex.html#vscode](https://hpc.nih.gov/nih/codex.html#vscode)). A browser login that redirects to a localhost callback fails there, because the callback server runs on the compute node. The browser ends on a "site cannot be reached" page. The user copies that page's URL, opens a terminal in the session, and runs:

```bash
# on the compute node (the user types this; the URL carries a login token)
read url
# paste the full URL from the browser, then press Enter
http_proxy='' wget -O /dev/null "$url"
```

`read url` keeps the token out of shell history. Keep it out of your context too: never ask for the URL. NIH documents this only for Codex; other tools with a localhost-callback login may work the same way (untested). The same page says Codex logs in "as usual" over Remote-SSH, and that the HHS subscription disables its device-code method ("as of writing"). The Codex CLI is not a module: install it personally with `npm` (install locations: DEVELOPMENT.md), or as the `x86_64-unknown-linux-musl` binary from https://github.com/openai/codex/releases/. One login covers every Codex app on that system.

## Connecting over SSH

- **Network** (the user): the wired NIH network, the NIH-Staff wireless, or the NIH VPN; NCI users can also use NCI RemoteApps. The "NIH Guest" WiFi doesn't work. The [VPN test page](https://hpc.nih.gov/nih/test.html) shows "Access forbidden!" off the VPN. OnDemand, the account forms, the dashboard, and hpcdrive need the same network access.
- **Credentials**: the NIH username and password; the password does not echo. The user types it, and you never ask for it: HHS rules forbid giving it "to anyone, including system administrators".

```bash
# on the user's computer (the user runs this)
ssh username@biowulf.nih.gov         # submit and manage jobs; give the NIH username if the local one differs
ssh username@helix.nih.gov           # interactive transfers, large file operations
ssh $env:username@biowulf.nih.gov    # Windows PowerShell; a plain `ssh biowulf.nih.gov` sends the domain-prefixed local name and fails
```

In PuTTY, put `username@biowulf.nih.gov` in Host Name and save the session. Accept a host key only if it matches one of these SHA256 fingerprints; the MD5 list is at [ssh.html#fingerprint](https://hpc.nih.gov/docs/ssh.html#fingerprint). If the client rejects unknown keys outright, add `-o StrictHostKeyChecking=ask`.

```text
biowulf  RSA 2048    SHA256:rQ6vBSjlXGE56I0nwQfvvDduOwx+C1aRuT6cZnVpS8k
helix    RSA 1024    SHA256:6fz4LcdAE71brp857n29I3+6whMCjAKXPVeZJPCkL7c
both     ECDSA 256   SHA256:BoP/KLS17g+gUuQ7mrCHa9oPPO+MHi/h8WML44iA1dw
both     ED25519 256 SHA256:MBuANYkwgnJAlovbS1Kp1/S2hviPwkc/VOxCuFfW/lo
```

What each host tolerates from the user (agents: SKILL.md):

- `biowulf.nih.gov` is for "light editing, code compilation, job submission, and reading output files" ([ExpUserGuide#donts](https://hpc.nih.gov/docs/ExpUserGuide.html#donts)). A process killer ends any non-root process after 5 minutes of CPU time, and each user is capped at 4 CPUs (as of Sept 2026). `scp` and `sftp` to it fail, and `rsync` dies after about 5 minutes, so transfers go through Helix or Globus (TRANSFER.md). `whereami` there says: "It should only be used to submit jobs. Many modules are not available here and any compute intensive processes or file transfers will get killed."
- `helix.nih.gov` is "intended for interactive file transfers, such as Aspera transfers which are not easily performed on Biowulf compute nodes". It has 48 CPUs (Xeon Gold 6136) and 1.5 TB of memory, and shares `/home` and `/data` with Biowulf. "Scientific applications are not available, and should not be run on Helix."

## When the user can't connect

| Symptom | Cause, and what the user does |
|---|---|
| `ssh` hangs or times out; OnDemand, the dashboard, or hpcdrive won't load | Off the NIH network, or on "NIH Guest". Connect the VPN and check the test page. |
| Password refused from Windows OpenSSH | The local username has a domain prefix. Use `ssh $env:username@…` or type the NIH username. |
| Refused after weeks away | The account locks after 60 days of inactivity. Unlock it at https://hpc.nih.gov/dashboard, or email staff. |
| Refused even with an SSH key | The password expired: keys "will not override expired passwords". Reset it at https://password.nih.gov/. |
| macOS Kerberos login stopped working | The ticket wasn't renewed. Run `klist`, then `kinit`. |
| Processes killed on biowulf; `scp`/`sftp` fail or `rsync` dies there | Login-node limits. Use `sinteractive`, OnDemand, or Helix. |
| `module load` of an application fails | Causes and fixes: MODULES.md. |
| `sinteractive` shell (and the agent) gone | Its login-node shell ended (a VPN drop without tmux, or the monthly reboot). Restart per SKILL.md, or use an OnDemand app for long sessions. |
| OnDemand `Bad Request - Your browser sent a request that this server could not understand.` | Too many large cookies. Clear the browser's cookies. |
| OnDemand `Error -- user has disabled shell: USERNAME` | The account is locked or disabled. Unlock it at https://hpcnihapps.cit.nih.gov/auth/dashboard/, else email staff. |
| OnDemand on Linux: "your connection is not private" | The site uses an internal TLS certificate. Trust the [Federal Common Policy CA G2](https://myitsm.nih.gov/kb_view_customer.do?sysparm_article=KB0020936) root. |
| A new OnDemand app or `sinteractive` fails to submit | Two interactive jobs are already running. End one; the Graphical Session doesn't count. |
| VS Code "Connecting with SSH timed out" | Set "Remote.SSH: Connect Timeout" to 30 seconds. |
| Anything else | Email staff@hpc.nih.gov with the OS, the client and its version (PuTTY, command-line SSH, OnDemand), and the exact error ([connect.html#trouble](https://hpc.nih.gov/docs/connect.html#trouble)). |

## SSH keys and Kerberos

Both spare the user from typing the password; setting either up is the user's job.

- **Key rules** ([sshkeys.html](https://hpc.nih.gov/docs/sshkeys.html)): every private key needs a passphrase, and it must not be the NIH password. Allowed types are RSA (>=2048-bit), ED25519, and ECDSA. A key may go in only one HPC account's `authorized_keys`. Sharing keypairs between users is "strictly prohibited", and violating keys "maybe revoked without warning".
- **Where keys live**: keep private keys on the user's own computer, not on Helix or Biowulf. `~/.ssh/authorized_keys` takes one public key per line.

```bash
# on the user's computer (the user runs this)
ssh-keygen -t rsa -b 4096                      # the pages' example; ED25519 is also allowed. Set a passphrase.
scp ~/.ssh/id_rsa.pub username@helix.nih.gov:~/tmp.pub
# on Helix
mkdir -m 700 -p ~/.ssh; cat tmp.pub >> ~/.ssh/authorized_keys; rm tmp.pub; chmod 0600 ~/.ssh/authorized_keys
# on the user's computer, by the user (may be needed again after a reboot)
ssh-add                                        # if no agent is running: eval "$(ssh-agent -s)" first
```

PuTTY users generate an RSA 4096 key in PuTTYgen. Copy the public-key text from its window into a plain-text file, because the "save the public key" button writes the wrong format; copy that file to Helix and append it as above. Then load the private key under Connection → SSH → Auth.

[Kerberos (GSSAPI)](https://hpc.nih.gov/docs/gssapi_access.html) works for SSH and hpcdrive. NIH Windows workstations get a ticket at logon; PuTTY (v0.62 or later) needs GSSAPI enabled. macOS may not renew tickets on its own, so check before connecting:

```bash
# on the user's computer (the user runs this)
klist                                          # current tickets
kinit your_nih_username@NIH.GOV                # off the NIH domain; capitalization matters. Renew: kinit -R
ssh -o GSSAPIAuthentication=yes username@biowulf.nih.gov
```

## HPC OnDemand

https://hpcondemand.nih.gov needs the NIH network or VPN, then the NIH central login page with a PIV smart card or an MFA authenticator app. Both steps are the user's.

- **Apps.** Every app runs as a Slurm job on a compute node; the dashboard itself uses no Slurm resources. Forms live at `https://hpcondemand.nih.gov/pun/sys/dashboard/batch_connect/sys/<APP>/session_contexts/new`, where `<APP>` is `bc_nih_jupyter` (JUPYTER.md), `bc_nih_rstudio` or `bc_nih_shiny` (R.md), `bc_nih_vscode` ([VS Code](#vs-code)), or `bc_nih_desktop` (Graphical Session). The full list is under "Interactive Apps" or at https://hpcondemand.nih.gov/pun/sys/dashboard/apps/index. The user can request new apps from staff.
- **Sessions.** [My Interactive Sessions](https://hpcondemand.nih.gov/pun/sys/dashboard/batch_connect/sessions) lists running, pending, and past sessions, and reconnects to running ones. To end a session early, the user deletes it there; that is standard Open OnDemand, not described on NIH's page.
- **Limits.** Jupyter, RStudio, and VS Code are interactive jobs. The form sets their resources and walltime (36 h at most), and each takes one of the user's two interactive-job slots, shared with `sinteractive` (JOBS.md). These limits are as of Sept 2026; `batchlim` shows the current ones.
- **No batch submission from the portal.** It "does not currently support direct batch job submission"; the user submits from a terminal inside an app.
- **Files.** The File Browser handles light file management; its "Globus" link handles large transfers (GLOBUS.md).
- **Browser.** Avoid Safari: copy/paste breaks in the Graphical Session, the interactive shell, and MATLAB. RStudio, Jupyter, and VS Code aren't known to be affected. Portal errors are listed [above](#when-the-user-cant-connect).

## VS Code

"VS Code ( vscode ) should ONLY be run from computational nodes. Do not run VS Code on Biowulf or Helix." So never attach VS Code to `biowulf.nih.gov` or `helix.nih.gov`. NIH HPC prefers the OnDemand app as "much simpler and more stable": open the `bc_nih_vscode` form, set resources, launch, then connect. VS Code runs natively on the node, and extensions configured in the first session load from the home directory in later ones.

For local VS Code over Remote-SSH ([#win](https://hpc.nih.gov/apps/vscode.html#win), [#mac](https://hpc.nih.gov/apps/vscode.html#mac)), the one-time setup is all the user's:

1. Install the "Remote Development" extension pack.
2. Install a passphrase-protected key as above and load it with `ssh-add`. On Windows, first check the ssh-agent service in an administrative PowerShell (local IT may need to do this): `Get-Service ssh-agent | Select StartType`. If it shows Disabled, run `Get-Service -Name ssh-agent | Set-Service -StartupType Manual`. Then, in a non-admin PowerShell, run `ssh-agent.exe` and `ssh-add`.
3. Add this block to the local SSH config, and point VS Code's "Remote.SSH: Config File" setting at that file:

```text
# macOS: /Users/USERNAME/.ssh/config        Windows: C:\Users\USERNAME\.ssh\config
Host cn*
User USERNAME
ProxyCommand /usr/bin/ssh -o ForwardAgent=yes USERNAME@biowulf.nih.gov nc -w 120ms %h %p
# Windows line: ProxyCommand C:\Windows\System32\OpenSSH\ssh.exe -o ForwardAgent=yes USERNAME@biowulf.nih.gov nc -w 120ms %h %p
```

For each session, the user starts `sinteractive` in a separate SSH or PuTTY login (inside tmux) and notes the node, `cnNNNN`. They then run "Remote-SSH: Connect to Host" and enter `cnNNNN`. On Windows, click the node name instead of pressing Enter, then choose "linux" and "continue". The window ends when the job does. Jupyter notebooks inside VS Code: JUPYTER.md.

## Graphical Session, X11, and svis

The **OnDemand Graphical Session** ([graphical.html](https://hpc.nih.gov/ondemand/graphical.html)) is an XFCE desktop in the browser. The user launches "Graphical Session" from the dashboard or the `bc_nih_desktop` form. When it shows green and Running on My Interactive Sessions (usually within a couple of minutes), they click "Launch Graphical Session".

- **Resources.** It gets 4 CPUs and 8 GB ("currently"; as of Sept 2026), and each user gets one. It persists across disconnects for up to 7 days and can't be extended. Neither it nor its plain terminals count toward the interactive-job limit, but an `sinteractive` started from its Terminal does.
- **Use.** Real work within those resources is fine. GUI apps in `sinteractive` sessions started from it get X forwarding with no setup. Firefox is available for browser downloads, and lowering the image quality (left slide-out menu) helps on slow links.
- **Helix.** Its Terminal can `ssh` to Helix for transfers and Git over SSH. That is the user's action, never an agent's.
- **NoMachine (NX)** was retired on 7 August 2025; the Graphical Session replaces it. Graphics that fail or crawl: TROUBLESHOOTING.md.

**X11 over SSH.** Staff recommend OnDemand instead on every OS. On Linux, run `ssh -Y username@biowulf.nih.gov`, then test with `xclock`. On macOS it is unsupported, because "the required XQuartz software is no longer maintained". On Windows, PuTTY X11 forwarding plus Xming (started first) or MobaXterm can work, but direct graphical access over SSH from Windows is "not supported by HPC staff".

**svis** ([svis.html](https://hpc.nih.gov/docs/svis.html)) gives GPU-accelerated rendering on the `visual` partition, for jobs that "require intensive remote data visualization"; the Graphical Session has no GPU acceleration. The steps are all the user's:

1. Run `svis` on the login node, with no options; it allocates a whole node.
2. In a new terminal on their computer, run the `ssh -L PORT:localhost:PORT user@biowulf.nih.gov` line it prints.
3. Point a local TurboVNC viewer (installing it may need admin rights) at `localhost::PORT` and log in with NIH credentials.
4. In the desktop, run `module load virtualgl` and launch apps with `vglrun <app>`; MATLAB needs `vglrun matlab -nosoftwareopengl`. Confirm the GPU with `nvidia-smi`.

A black screen with "Unable to contact settings server" means a conda env was active (or auto-activated from `~/.bashrc`) when `svis` ran.

## Shell startup files

bash is the standard shell. `~/.bash_profile` runs for login shells; `~/.bashrc` runs for interactive non-login shells, including the shell `sinteractive` opens on a node. [startup_files.html](https://hpc.nih.gov/docs/startup_files.html) recommends making `.bash_profile` a pass-through, `if [ -f ~/.bashrc ]; then . ~/.bashrc; fi`, with everything else in `.bashrc`.

- **Never pre-load modules or conda.** The page warns: "If there is an error, you will be prevented from logging in." Its "Do not include" examples are `module load python/3.6` and `source /data/user/conda/etc/profile.d/conda.sh`. conda sometimes adds its own init block; removal steps are in CONDA.md.
- **Syntax errors.** A syntax error in `.bashrc` can remove the `module` function.
- **Other shells.** csh/tcsh work (`.cshrc`), but bash is "highly recommend[ed]"; sh, ksh, and zsh get "very limited support".
- **umask.** The default is 027; changing it for shared data is covered in STORAGE.md.

To isolate a startup-file problem, reset to the stock files ([FAQ#graphics_problem](https://hpc.nih.gov/docs/FAQ.html#graphics_problem)). This changes the user's dotfiles, so get their OK first:

```bash
mv ~/.bashrc ~/.bashrc.ORIG; cp -p /etc/skel/.bashrc ~
mv ~/.bash_profile ~/.bash_profile.ORIG; cp -p /etc/skel/.bash_profile ~
module purge
# the user retests in a new session; if fixed, re-add lines one at a time. To undo:
mv ~/.bashrc.ORIG ~/.bashrc; mv ~/.bash_profile.ORIG ~/.bash_profile
```

If a bad edit blocks login entirely, the fix is to revert the file (hpcdrive reaches `/home` without starting a shell) or ask staff.

## Mounting storage locally (hpcdrive)

[hpcdrive](https://hpc.nih.gov/docs/hpcdrive.html) mounts `/home`, `/data`, `/scratch`, and group areas on the user's computer over SMB, from the NIH network or VPN. It suits small files and opening HTML reports in a local browser; bulk data goes through TRANSFER.md or GLOBUS.md. NIH HPC's policies don't mention local agents reading files through it.

- **Paths.** On Windows (Map network drive) the path is `\\hpcdrive.nih.gov\SHARE`; on macOS (Finder → Go → Connect to Server) it is `smb://hpcdrive.nih.gov/SHARE`. SHARE is `USER` for home, `data` for `/data/USER`, `scratch` or `scratch\USER` (`scratch/USER` on macOS), or a group-area name such as `PQRlab`.
- **Windows and macOS.** Windows signs in with the NIH login; a lab PC on an institute domain may need `NIH\username` when prompted. The disk usage Windows shows for `/home` is wrong; `/data` is right. macOS asks for the NIH username and password. A Mac that keeps retrying an old mount: [FAQ#mount-popup](https://hpc.nih.gov/docs/FAQ.html#mount-popup).
- **Linux** needs root. Replace `/etc/krb5.conf` with the page's `NIH.GOV` config and run `kinit your_user_name@NIH.GOV`, then mount, for example: `mount -t cifs -o uid=<your_local_uid>,gid=<your_local_gid>,cruid=<your_local_system_username>,sec=krb5i //hpcdrive.nih.gov/[user] /mnt/bw-home`. An expired ticket hangs the mount; renew it with `kinit -R` (renewable for up to 7 days). On Red Hat, `mount.cifs` isn't setuid root, so user mounts fail.

## Accounts, maintenance, and staff

- **Who.** Researchers in the NIH intramural programs who are listed in NED. Guest Researchers, Volunteers, and Fellows keep accounts for the duration of their NIH status. Extramural grantees aren't eligible (NIH STRIDES: strides@nih.gov). Each person has their own account; accounts are never shared.
- **Requesting.** The user fills in the [request form](https://hpcnihapps.cit.nih.gov/auth/accounts/account_request.php) (NIH network, NIH login) and picks their IC and PI. The PI approves by email, CIT gets the IC's approval for the fee, and login instructions arrive by email. If the PI isn't listed, email staff.
- **Cost.** $40.00 per month per account (as of Sept 2026), covering Biowulf, Helix, and hpcdrive. There are no charges for CPU or storage.
- **Renewal** is yearly, with PI approval. For the 2026–2027 cycle (Sept 2026), the user completes https://hpc.nih.gov/nih/accounts/recert.php by 1 October 2026, and PIs certify during October. Accounts not approved by 1 November are suspended until renewal is complete. PIs fill in the form too and are approved instantly. Accounts created after 1 June 2026 are exempt; the form page says whether it's needed.
- **Locked accounts.** An account locks after 60 days of inactivity. The user unlocks it at https://hpc.nih.gov/dashboard or emails staff. Password resets: https://password.nih.gov/.
- **Leaving NIH.** Accounts go inactive when the user leaves NED and are deleted after more than 14 days out; what happens to the data is in STORAGE.md. To close an account, open a ticket with the [NIH IT Service Desk](http://itservicedesk.nih.gov/). Class accounts: https://hpc.nih.gov/nih/student.html (NIH only). Web tools that need no command line: https://hpcwebapps.cit.nih.gov/.
- **Monthly reboot.** Helix and the Biowulf login node reboot, but not the cluster ([policies#reboots](https://hpc.nih.gov/policies/index.html#reboots)). The reboot is at 8 pm on the first Sunday of the month, or the following Sunday if that Monday is a holiday, with typically 15–30 minutes of downtime. Upcoming dates: the [announcements](https://hpc.nih.gov/nih/about/announcements.php). "These reboots will not affect any jobs", and OnDemand sessions are jobs. An `sinteractive` session, though, depends on its login-node shell (JOBS.md), and tmux runs on the login node too. Expect the session, and any agent in it, to end; NIMH's `spersist` sessions are [documented](https://hpc.nih.gov/docs/nimh.html#persist) to end at the reboot.
- **Announcements.** Longer and emergency maintenance is announced separately. Users are responsible for reading announcements, which appear at login and are emailed to users. The [archive](https://hpc.nih.gov/nih/about/announcements.php) keeps past ones; live service state is at https://hpc.nih.gov/systems/status/.
- **Staff.** The user sends every request; a template is in TROUBLESHOOTING.md. Email staff@hpc.nih.gov (preferred), not individual staff members. Phone (301) 496-4357 reaches the NIH IT Service Desk, which also has an [online form](http://itservicedesk.nih.gov/Support/); it handles routine account and password questions and transfers Biowulf calls to HPC staff. The policies page lists 301-496-4825 for HPC staff. Staff hold virtual Walk-In Consults monthly, announced by email a few days ahead. Science questions go to the intramural lists and Slacks on [contact.html#science](https://hpc.nih.gov/about/contact.html#science).

## Stale advice on the official pages

- The login banners reproduced on ssh.html and svis.html say reboots happen on the "first Monday" at 7:00 AM (7:15AM on svis.html). The current schedule is 8 pm on the first Sunday.
- The FAQ's graphics entry "strongly recommends nomachine", and the MATLAB page says to use `-X` or `-Y` with ssh. NoMachine is retired and X11 on macOS is unsupported: use the Graphical Session.
- vscode.html writes the Mac config path as `.ssh\config`; the real path is `~/.ssh/config`. It also shows only RSA keys, though ED25519 and ECDSA are allowed.
- The Experienced User Guide says OnDemand needs "your PIV card"; an MFA authenticator app works too.
- accounts.html says accounts are "restricted to NIH employees and contractors"; the policies page says they are for "researchers in the NIH intramural research programs". Both require a NED listing and admit Guest Researchers and Volunteers; if eligibility is unclear, the user asks staff.
- hpcdrive.html says the ticket "will expire after 12 hours", but its own krb5.conf sets `ticket_lifetime = 24h`. Its `/data` example reuses `/mnt/bw-home`; give that mount its own directory. "Use option 2 below" points to nothing.
- svis.html dates from 2021 (K20Xm GPU, MATLAB 2020b), and the User Guide's visualization section is commented out. Confirm with staff that the visual partition is still offered.
- Two account-dashboard URLs appear, https://hpc.nih.gov/dashboard and https://hpcnihapps.cit.nih.gov/auth/dashboard/; both work.

## Going further

- [Connecting](https://hpc.nih.gov/docs/connect.html): access methods and the troubleshooting checklist. [SSH](https://hpc.nih.gov/docs/ssh.html): per-OS clients, [host key fingerprints](https://hpc.nih.gov/docs/ssh.html#fingerprint) (MD5 too), and X11.
- [SSH keys](https://hpc.nih.gov/docs/sshkeys.html) and [Kerberos](https://hpc.nih.gov/docs/gssapi_access.html): key policy and per-OS setup.
- [HPC OnDemand](https://hpc.nih.gov/ondemand/) and the [Graphical Session](https://hpc.nih.gov/ondemand/graphical.html): apps, limits, and known issues.
- [VS Code](https://hpc.nih.gov/apps/vscode.html): the OnDemand app and Remote-SSH to a node.
- [Codex on Biowulf](https://hpc.nih.gov/nih/codex.html) (NIH-only): NIH HPC's agent guidance, and extension and CLI logins.
- [svis](https://hpc.nih.gov/docs/svis.html): the visual-partition walkthrough and app examples (AFNI, VMD, ChimeraX, FSLeyes).
- [Startup files](https://hpc.nih.gov/docs/startup_files.html); [hpcdrive](https://hpc.nih.gov/docs/hpcdrive.html), which has the full Linux `krb5.conf`; [Accounts](https://hpc.nih.gov/docs/accounts.html); [Policies](https://hpc.nih.gov/policies/index.html) ([#who](https://hpc.nih.gov/policies/index.html#who), [#helix](https://hpc.nih.gov/policies/index.html#helix)); and [Contact](https://hpc.nih.gov/about/contact.html).
- Live checks: `whereami` (output forms: UTILITIES.md) and `klist`. The user's `ssh -v username@biowulf.nih.gov` prints a verbose client log worth attaching to a help request.
