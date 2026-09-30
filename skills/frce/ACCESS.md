How the user gets an FRCE account and onto the cluster, and how they reach the people who run it: eligibility and the account request, Active Directory groups, yearly validation, host aliases and login names, SSH clients, keys, and X servers, the login shell, status and maintenance, every support channel and ServiceNow form, and ABCS training. Every account, VPN, password, passphrase, browser, ServiceNow, and email step is the user's: give them the exact command, click path, or draft, labeled with where it runs (ground rules in SKILL.md). Host roles and where you may run: SKILL.md. Shells, VS Code, X11 in jobs, and tunnels: INTERACTIVE.md. OnDemand: ONDEMAND.md. Access that fails: TROUBLESHOOTING.md (Access and connection problems).

Table of contents

- [Accounts and groups](#accounts-and-groups)
- [Connecting](#connecting)
- [SSH keys and clients](#ssh-keys-and-clients)
- [Login shell](#login-shell)
- [Status and maintenance](#status-and-maintenance)
- [Support and requests](#support-and-requests)
- [Training](#training)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Accounts and groups

- **Who.** "Any person within NCI or FNLCR is eligible for an account on the FRCE cluster. There is no charge for the account." ([Request Access](https://ncifrederick.cancer.gov/staff/FRCE/Support/AccessRequest))
- **Requesting.** The user files the FRCE Cluster Request Form ([Support and requests](#support-and-requests)) and should "allow 2-3 days for the account to be enabled".
- **Active Directory owns identity.** The account, its UID and GIDs, and every group come from AD, and "The FRCE admins do not have privileges in Active Directory", so creating or changing a group, or adding a member, takes a ServiceNow ticket the user files at https://service.cancer.gov (no form is named).
  - New groups need POSIX attributes: "it is imperative that the request include configuring POSIX attributes for the group." Leave FRCE out of that ticket; mentioning it "may delay assigning the ticket to the appropriate admins."
  - Shares are granted to AD groups, so joining a share is a group-membership ticket. Requesting a new share: [Support and requests](#support-and-requests); how shares work: STORAGE.md (Group shares).
- **Checking groups** is read-only:

```bash
# on the compute node (inside your session), or the user on the login node:
id                          # the user's groups; a new membership shows only in a new login, and can take a while
getent group GROUPNAME      # a line with a GID if the group exists with POSIX attributes; nothing otherwise
```

- **Yearly validation.** "All user accounts will soon need to be validated on a yearly basis", and "inactive accounts may be purged in the future." The form on the [Account Validation](https://ncifrederick.cancer.gov/staff/FRCE/Support/AccountValidation) page loads from the login node's web server, which asks the browser for AD credentials. The user reviews the entries and clicks "Confirm" "even if there are no changes"; a missing division or branch means emailing the administrators. No deadline or consequence is stated (Sept 2026).

## Connecting

The network rule and host roles are in SKILL.md (FRCE at a glance). Logging in is the user's:

```bash
# on the user's computer (NIH network or VPN) — the user runs:
ssh USERNAME@batch.ncifcrf.gov       # USERNAME: the NIH username, lower case, no NIH\ prefix; NIH password
```

- X11 forwarding (`ssh -Y`) and GUI programs in jobs: INTERACTIVE.md (X11 applications); the X server it needs: next section.
- No PIV card: "Currently, it is not necessary to use a PIV card to log into the FRCE systems." If that changes, [PuTTY-CAC](https://risacher.org/putty-cac/) supports PIV ([Connecting to FRCE](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/ConnectingFRCE)).
- Compute nodes are "not directly accessible from outside the FRCE environment" ([Ollama endpoint page](https://ncifrederick.cancer.gov/staff/FRCE/OllamaEndpoint)); everything reaches them through the login node (tunnels, and ssh to a node running one of the user's jobs: INTERACTIVE.md).
- Each login-node session starts with `ulimit -t 600`, set as both soft and hard limit by pam_limits for regular accounts: the 10 CPU-minute rule, counted per process and impossible to raise (live, Sept 2026; open files are capped at 8096 and processes at 16384). Whether batch2 and nx set it too is untested: the user's `ulimit -t` there prints `600` if so. What it kills and how that looks: TROUBLESHOOTING.md (Killed on the login node).
- FRCE publishes no SSH host-key fingerprints and documents no MFA, password-expiry, or lockout rules (Sept 2026). If ssh warns that a host key changed, the user asks the administrators before accepting the new one.

Aliases beyond SKILL.md's host list (DNS, Sept 2026; check with `host NAME` from the NIH network):

| Name | Is | Used for |
|---|---|---|
| `hpcapi.ncifcrf.gov` | the login node, `fsitgl-head01p` | the HPC REST API: JOBS.md (Submitting without logging in) |
| `cnNNN.ncifcrf.gov` | `fsitgl-hpcNNNp.ncifcrf.gov` | Slurm's node name resolves too; either works as a tunnel target (INTERACTIVE.md) |
| `nx.ncifcrf.gov` | `fsitgl-nx04p` | NoMachine: INTERACTIVE.md |
| `ondemand.ncifcrf.gov` | `fsitgl-dmand01p` | Open OnDemand: ONDEMAND.md |
| `xdmod.ncifcrf.gov` | `fsitgl-xdmod01p` | usage metrics: MONITORING.md |

## SSH keys and clients

Clients [Connecting to FRCE](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/ConnectingFRCE) lists for the user's computer ("AA privileges" are NIH admin rights; their file transfer: TRANSFER.md (Graphical clients)):

| Client | X11 | Notes |
|---|---|---|
| OpenSSH (`ssh`, `scp`): macOS, Linux, Windows | macOS: [XQuartz](https://www.xquartz.org); Linux: built in; Windows: an X server below | per the page, Windows Terminal can't come from the Microsoft Store, and its GitHub install needs AA privileges |
| [PuTTY](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) | [VcXsrv](https://sourceforge.net/projects/vcxsrv/) or Xming | installs without AA privileges |
| [MobaXterm](https://mobaxterm.mobatek.net/) | built in | free Home Edition caps open windows but "allows use within a corporate environment"; no AA privileges |
| [Bitvise](https://www.bitvise.com/ssh-client) | none: add VcXsrv | |

Xming is covered by an NIH [site license](https://mirror.nih.gov/licenced/xming/site_license979.pdf), with installers on the [NIH mirror](https://mirror.nih.gov/licenced/xming/www.straightrunning.com/candidate/). PuTTY forwards X11 once Connection → SSH → X11 → "Enable X11 forwarding" is ticked and the X server is running.

**Keys.** "Key-based authentication is strongly recommended for ssh logins, with the caveat that the SSH private key is passphrase protected and kept in a secure environment", meaning "a GFE laptop or known secure personal device" ([SSH key-based authentication](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/SSHkeybasedauthentication)). So the user generates the key on their own computer, never on FRCE, sets a passphrase, and loads it into an agent once per login; nothing then prompts, which VS Code needs (INTERACTIVE.md). Types: ED25519 ("EdDSA is acceptable") or RSA with 2048 or 4096 bits; "none of the other choices should be selected". Tell the user about one exception: `vscode-alloc` creates a key without a passphrase on FRCE (INTERACTIVE.md (VS Code on a compute node)).

```bash
# on the user's computer (macOS, Linux) — the user runs:
ssh-keygen -t ed25519                         # accept the default path; set a passphrase
ssh-copy-id USERNAME@batch.ncifcrf.gov        # appends the public key to ~/.ssh/authorized_keys on FRCE (password once)
ssh-add                                       # once per login; macOS: ssh-add --apple-use-keychain
ssh USERNAME@batch.ncifcrf.gov hostname       # prints fsitgl-head01p.ncifcrf.gov with no prompt
```

Windows OpenSSH has no `ssh-copy-id`; the [VS Code page](https://ncifrederick.cancer.gov/staff/FRCE/VSCodeSlurm)'s one-liner does the same job:

```powershell
# on the user's computer (Windows PowerShell) — the user runs:
ssh-keygen -t ed25519
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh USERNAME@batch.ncifcrf.gov "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
Get-Service ssh-agent | Set-Service -StartupType Manual; Start-Service ssh-agent   # once, in an admin PowerShell (local IT may have to)
ssh-add
```

PuTTY and MobaXterm users make the key in PuTTYgen (MobaXterm: Tools → MobaKeyGen), with a passphrase, and "Save private key" (`.ppk`). The public key to install is the one-line text in PuTTYgen's top pane; the "Save public key" file is in another format. Then:

```bash
# on the FRCE login node — the user runs:
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys      # paste the key (PuTTY pastes with right-click or Shift+Insert), Enter, then Ctrl-D
chmod 600 ~/.ssh/authorized_keys
```

PuTTY takes the `.ppk` under Connection → SSH → Auth → Credentials, and Pageant holds its passphrase ([how-to](https://winscp.net/eng/docs/ui_pageant)); MobaXterm has its own agent (Settings → SSH).

## Login shell

"The default shell for all users is `/bin/bash`. This setting comes from Active Directory and it cannot be changed" ([How to change the login shell](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/Howchangeloginshell)), so `chsh` is no use. The page's workaround switches interactive logins to zsh from `~/.bashrc`. This version of its guard also skips `bash -i -c` callers and hosts without zsh:

```bash
# appended to ~/.bashrc — by the user, or by you only with their OK (ground rule 6); first: cp ~/.bashrc ~/.bashrc.bak
if [ -n "$PS1" ] && [ -z "$BASH_EXECUTION_STRING" ] && [ -x /bin/zsh ]; then
  export SHELL=/bin/zsh
  exec /bin/zsh --login
fi
```

- The guard is essential: without it, "the change would prevent some non-interactive applications like file transfers from working."
- It also turns every `srun --pty bash` shell and every OnDemand or VS Code terminal into zsh; job scripts still run under their `#!` interpreter.
- If an edit breaks interactive logins, restore the backup without an interactive shell: `ssh USERNAME@batch.ncifcrf.gov 'cp ~/.bashrc.bak ~/.bashrc'` (the user, from their computer), or edit the file in OnDemand's file browser (ONDEMAND.md (Files and Globus)).

## Status and maintenance

- **Status.** The [Status and Metrics](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/StatusandMetrics) page opens with the cluster's state ("All systems are working properly." as of Sept 2026) and embeds the live partition table, wait-time graphs, and XDMoD charts (reading them: MONITORING.md).
- **Reboots.** "System reboots are scheduled for the first Tuesday of the month at 8:30 am. Reboots will not affect running or submitted jobs." The login banner names the login node: "The FRCE head node will be rebooted at 8:30am on the first Tuesday of each month for patch management." Neither says for how long, and not every month has one: `last reboot` on batch (Sept 2026) shows it down from 08:31 to 13:38 on Tuesday 1 Sep, none in July or August, and reboots on three other days in June. Its tmux sessions and the `srun --pty` shells started there end with it (INTERACTIVE.md (Interactive shells with srun)), and VS Code connections drop until it's back; jobs, OnDemand sessions, and VS Code allocations carry on.
- **Announcements** appear on the [FRCE home page](https://ncifrederick.cancer.gov/staff/FRCE) under "Announcements:", where the login banner sends users "for announcements concerning upcoming maintenance or hardware/software issues". No mailing list is documented.

Both pages are public, so you can read them yourself:

```bash
# wherever you run (never a login host), if it has internet access — read-only, you may run these:
curl -s https://ncifrederick.cancer.gov/staff/FRCE/Documentation/StatusandMetrics | grep 'Cluster Status' | sed 's/<[^>]*>/ /g'
curl -s https://ncifrederick.cancer.gov/staff/FRCE | grep 'Announcements:' | sed 's/<[^>]*>/ /g'
```

## Support and requests

The user sends every request; you draft it (what to include: TROUBLESHOOTING.md (Asking for help)). ServiceNow (https://service.cancer.gov) needs the user's NIH login, and its forms can't be read without it. "An email is preferred for short questions, otherwise a ticket is required" ([FRCE home](https://ncifrederick.cancer.gov/staff/FRCE)); no response times or support hours are published (Sept 2026).

| Need | Channel | Who acts |
|---|---|---|
| A short question | email NCIFHPCAdministrators@mail.nih.gov | FRCE administrators |
| An incident or problem | [Frederick General Service Request](https://service.cancer.gov/ncisp?id=nci_sc_cat_item&sys_id=94a45b2adb3f2700b21d30ca7c961907), with "FRCE" in the 'Brief Description of Request' field and "as much detail as you can provide" in 'Additional Details or Instructions'; if urgent, email too ([Contact Us](https://ncifrederick.cancer.gov/staff/FRCE/Support/ContactUs)) | FRCE team |
| An account | [FRCE Cluster Request Form](https://service.cancer.gov/ncisp?id=nci_sc_cat_item&sys_id=6d2736951b8c9850abf0ddb6bc4bcb28) | FRCE team, 2–3 days |
| Software installed or updated | [software request form](https://service.cancer.gov/ncisp?id=nci_sc_cat_item&sys_id=8245d45b1bec9110c2cced7bbc4bcbca); what qualifies, licenses: MODULES.md (When software isn't installed) | FRCE team |
| A new share or more quota | [storage request form](https://service.cancer.gov/ncisp?id=nci_sc_cat_item&sys_id=3b3453f31ba58510c2cced7bbc4bcb66); it "may be limited to users located in Frederick. If you are denied access, email us" | the storage group; FRCE admins "are unable to create new network shares or change the quotas" |
| An AD group created or changed, or a member added | a ServiceNow ticket ([Accounts and groups](#accounts-and-groups)) | AD administrators, not FRCE |
| A hardware or cluster-manager feature | email with the subject "FRCE Feature Request" asking for a consultation; if approved, a Frederick General Service Request to track it ([Feature Request](https://ncifrederick.cancer.gov/staff/FRCE/Support/FeatureRequest)) | FRCE team |
| An OnDemand app or file-browser directory | email (ONDEMAND.md) | FRCE administrators |
| Globus access or a Globus problem | a ServiceNow request (no form is named) "explicitly flagged to be directed to the Globus support team" (TRANSFER.md (Globus)) | Globus team; FRCE admins don't manage Globus |
| A Linux VM, e.g. for CryoSPARC | [VM request form](https://service.cancer.gov/ncisp?id=nci_sc_cat_item&sys_id=6d2c29ccdbc7b910c1e32e8813961929) (APPLICATIONS.md (Cryo-EM)) | the VM team; for CryoSPARC, then "The AppHosting team" |
| API partitions; a web server that submits jobs | email (JOBS.md (Submitting without logging in)) | FRCE administrators |
| A `/home` restore older than the self-service window | a ServiceNow ticket "directed to the EIT Storage group" (STORAGE.md (Recovering deleted files)) | EIT Storage |
| Usage metrics beyond XDMoD | email: they "can be made available on request" | FRCE administrators |
| Biowulf, not FRCE | staff@hpc.nih.gov | NIH HPC staff |

## Training

In ABCS's "[FRCE and Computational Science](https://bioinfo-abcc.ncifcrf.gov/training/series/frce-and-computational-science)" talks, event pages and abstracts are public (this host resolves outside NIH too); "Watch Recording" and "View Slides" need NIH Login, so the user opens them and shares what you need. The most useful for working on FRCE:

| Date | Talk | Covers |
|---|---|---|
| 2025-06-24 | [FRCE User Group: Open-OnDemand](https://bioinfo-abcc.ncifcrf.gov/training/event/frce-user-group-open-ondemand-building-549-executive-board-room-nci-frederick-2406251200) | the OnDemand apps (MATLAB, RStudio, VS Code, PyMOL) |
| 2025-11-25 | [Best Practices for Using FRCE Effectively](https://bioinfo-abcc.ncifcrf.gov/training/event/best-practices-for-using-frce-effectively) | choosing among CPU and GPU node types; Slurm's "restrictions and flexibility"; sharing the cluster |
| 2026-08-25 | [Local AI Inference on FRCE](https://bioinfo-abcc.ncifcrf.gov/training/event/local-ai-inference-on-frce) | Ollama from the command line and OnDemand; VS Code Remote SSH into a Slurm session |
| 2026-09-22 | [From Prompt to Pipeline: Agentic AI for Computational Science on FRCE](https://bioinfo-abcc.ncifcrf.gov/training/event/from-prompt-to-pipeline-agentic-ai-for-computational-science-on-frce) | agents for HPC jobs, long GPU runs, debugging, and QC, and "where it needs guardrails": worth the user's time for FRCE agent practice |

Other talks cover a 2023 quick start, NGS, structure prediction, containers, GPUs, imaging, cryo-EM, and Posit on FRCE. FRCE's [Slurm user guides](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/Slurmuserguides) page adds SchedMD's [cheat sheet](https://slurm.schedmd.com/pdfs/summary.pdf) and the NIH HPC [video channel](https://www.youtube.com/@nih_hpc8502/videos) ("Biowulf and FRCE are similar"; translate first: FROM-BIOWULF.md).

## Stale advice on the official pages

- The home, Services, and diagram pages say accounts are for NCI ("Any NCI researcher", "open to all NCI researchers") → the account page's "NCI or FNLCR" governs.
- The key page's Mac/Linux transcript runs `ssh-keygen` on the FRCE login node, as a staff account, against its own "use the private key only on a trusted system" → generate on the user's computer, with a passphrase.
- The key page's PuTTY steps: `chmod 0600 ~/authorized_keys` → `chmod 600 ~/.ssh/authorized_keys`; `mkdir ~/.ssh` fails if it exists → `mkdir -p`; "enter `ctrl-V` to paste" into nano doesn't paste in PuTTY → right-click or Shift+Insert (or the `cat >>` step above); "Connection → Data → SSH → Auth → Credentials" → Connection → SSH → Auth → Credentials.
- Connecting to FRCE: "Quartz is the preferred application" → XQuartz.
- How to change the login shell: `if [ "$PS1" ]` also fires for `bash -i -c` callers and on hosts without zsh → the guard above.
- ABCS Training: "Recordings of these lectures are available from their site" → only after NIH Login.
- Every page's sidebar "FRCE" link goes to `ncifrederick.cancer.gov/FRCE`, which redirects to a staff login → the public root is https://ncifrederick.cancer.gov/staff/FRCE.

## Going further

- FRCE: [Support](https://ncifrederick.cancer.gov/staff/FRCE/Support) (contact, account, software, feature, validation pages) · [Quick Start](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart) · [Connecting to FRCE](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/ConnectingFRCE) · [SSH key-based authentication](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/SSHkeybasedauthentication) · [How to change the login shell](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/Howchangeloginshell) · [Miscellaneous Policies and Guidelines](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/MiscellaneousPoliciesandGuidelines) · [Status and Metrics](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/StatusandMetrics) · [FAQ](https://ncifrederick.cancer.gov/staff/FRCE/FrequentlyAskedQuestions) · [ABCS Training](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/ABCSTraining).
- Biowulf docs, which need translation (other hosts, stricter key rules): [SSH keys](https://hpc.nih.gov/docs/sshkeys.html) · [connection troubleshooting](https://hpc.nih.gov/docs/connect.html#trouble) · [Kerberos logins](https://hpc.nih.gov/docs/gssapi_access.html) (undocumented for FRCE SSH) · [Windows ssh](https://hpc.nih.gov/docs/ssh.html#windows).
- Upstream: [ssh-keygen](https://man.openbsd.org/ssh-keygen), [ssh_config](https://man.openbsd.org/ssh_config), [PuTTY manual](https://www.chiark.greenend.org.uk/~sgtatham/putty/docs.html).
- Live: `id`, `getent group NAME`, `host cn085.ncifcrf.gov`, the two `curl` checks above; the user's `ssh -v USERNAME@batch.ncifcrf.gov exit` for a verbose login log, and their `ulimit -t` and `last reboot | head` on batch.
