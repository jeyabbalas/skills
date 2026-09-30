Globus at NIH HPC: the collections and their UUIDs, which steps are the user's, the `globus` CLI on a compute node (transfers, end-of-job copies, timers), web transfers, sharing with outside collaborators, and the cloud connectors. Globus is NIH HPC's recommended way to move large data; choosing among methods, and the non-Globus ones (scp/rsync, rclone for Box and OneDrive, cloud CLIs, downloads on compute nodes), are in TRANSFER.md. Other ways to share (group directories, ACLs, datashare) and quotas are in STORAGE.md; batch-script resources are in JOBS.md.

Table of contents

- [Collections](#collections)
- [Who does what](#who-does-what)
- [Command line](#command-line)
- [Transfers at the end of a batch job](#transfers-at-the-end-of-a-batch-job)
- [Scheduled and recurring transfers](#scheduled-and-recurring-transfers)
- [Web transfers and Globus Connect Personal](#web-transfers-and-globus-connect-personal)
- [Sharing with collaborators](#sharing-with-collaborators)
- [Cloud connectors](#cloud-connectors)
- [Troubleshooting](#troubleshooting)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Collections

From [setup.php#endpoints](https://hpc.nih.gov/docs/globus/setup.php#endpoints) (Sept 2026; confirm with `globus endpoint search NIH`):

| Collection | UUID | Use |
|---|---|---|
| `NIH HPC Data Transfer (Biowulf)` | `e2620047-6d04-11e5-ba46-22000b92c6ec` | The main one: `/home/$USER`, `/data/$USER`, and shared data directories the user can access; 10 data transfer nodes, 100 Gb/s aggregate |
| `NIH HPC Internet2 - AWS S3` | `c24547a8-ef53-4b86-bcf6-d050c55d00f4` | The user's own S3 buckets |
| `NIH HPC Google Cloud Collection` | `46312f97-8565-456d-a1ea-cb3e28e49caa` | Google Cloud Storage |
| `NIH HPC Google Drive Collection` | `22629017-758c-469c-8f75-51eaebcf0417` | Google Drive |
| `NIH HPC OneDrive Collection` | `ba595c6f-8822-4905-8ce9-6e072bb49ce4` | NIH OneDrive |
| `NIH HPC Internet2 - Biowulf /home/data` | `55bad7bd-4b2b-466a-8019-3666483681c2` | `/home` or `/data` over Internet2. **Not** for transfers within NIH (a laptop or another NIH collection); it *may* be faster to other Internet2 sites (NIH's tests were inconclusive) |

- The main collection shows in `globus endpoint search` as `NIH HPC Data Transfer`, owner `nihhpc@globusid.org`. Use the cluster's paths (`/data/$USER/...`). NIH names only `/home`, `/data`, and shared data directories, so stage anything else (e.g. `/lscratch`, object storage) into `/data` first.
- A transfer is an asynchronous task that Globus runs between collections: it outlives your session, retries faults, and emails the user on completion. NIH documents no size or file-count limits; destination quotas still apply.

## Who does what

Globus needs no shell on Biowulf, only the user's NIH login, so often your whole job is a checklist for the user: collection names, UUIDs, exact paths, and option choices (web steps below).

Only the user:
- NIH login (PIV; PIV-exempt users, e.g. on VDI, may use NIH username and password) and every Allow or consent screen, including `globus login` and any re-consent the CLI asks for.
- Installing and configuring Globus Connect Personal (GCP) on their computer.
- Registering cloud credentials (AWS keys, Google sign-in, OneDrive 'Register a Credential'). Never ask for or handle AWS secret keys.
- Emails to staff@hpc.nih.gov (Globus Plus invite, Google Cloud or Drive enablement); you may draft them.
- Creating, changing, or deleting shares and their permissions, even though the CLI could (`globus collection create guest`, `globus endpoint permission ...`); the NCI DME interface.
- Any transfer involving controlled-access data (e.g. dbGaP) or PII/PHI (ground rule 4 in SKILL.md).

Yours, on the compute node, after the user's login: `globus whoami`, `endpoint search`, `ls`, `task show|list|wait`; transfers and timers the user asked for; transfer lines in batch scripts the user submits; pre-flight checks (the source exists and is readable; the destination has room, via `checkquota` when it is Biowulf); drafting the collaborator message. Get the user's explicit go-ahead before anything that deletes or stops: `--delete-destination-extra`, `globus rm`, `globus delete`, `globus task cancel`, `globus timer delete`. Off the cluster, give the user the commands instead.

## Command line

`globus` is globus-cli 3.30.1 (Sept 2026; [apps list](https://hpc.nih.gov/apps/)); the flags here follow the current CLI reference, so if one is rejected, check `globus COMMAND --help`. NIH's sample runs it on Helix but says it "could also be run on any of the Biowulf compute nodes" ([transfer.php#cli](https://hpc.nih.gov/docs/globus/transfer.php#cli)); you run it only there. Data moves between the collections, not through your node, so a small session is enough. NIH never shows a `module load`; if `command -v globus` finds nothing, try `module spider globus`.

Login is the user's. Don't run `globus login` yourself: it waits for a code only the user can get. Give them:

```bash
# the user, in their own terminal on Biowulf (e.g. the session prompt, before starting the agent)
globus login --no-local-server   # open the printed URL, log in with NIH, click Allow, paste the code back
```

The login is saved in their home directory, which every node shares (NIH's sample logs in on Helix and continues on Biowulf), until `globus logout`. Suggest logging out when the work is done, but not while queued jobs still need to submit transfers.

```bash
# on the compute node (you)
globus whoami                                   # user@nih.gov or user@globusid.org; exit 4 = not logged in
globus endpoint search 'NIH HPC Data Transfer'  # a named collection's UUID; the user's GCP: GCP menu → Web: Connection Details
BW=e2620047-6d04-11e5-ba46-22000b92c6ec
globus ls "$BW:/data/$USER/"
globus transfer --recursive --skip-source-errors --fail-on-quota-errors --label "results to lab" \
    "$BW:/data/$USER/project/results/" "$DEST_UUID:/path/on/dest/"    # contents land inside dest/; prints "Task ID: ..."
globus task show "$TASK_ID"                     # status, files, bytes, faults
globus task wait "$TASK_ID" --timeout 1800 --polling-interval 60   # 0 = succeeded; 1 = failed or not done
```

- Exit status 4 from any command (`ConsentRequired`, or no login) means the user must act. Stop and hand them the output; they redo `globus login` (or the consent step the message names) in the browser, then you retry.
- Restart a failed or partial transfer with `--sync-level checksum`: the CLI reference warns that other levels can corrupt data.

Options are the same on the web's transfer options panel, and the long flags except `--dry-run` also work on `globus timer create transfer`. Bold = NIH recommends ([transfer.php#options](https://hpc.nih.gov/docs/globus/transfer.php#options), [CLI reference](https://docs.globus.org/cli/reference/transfer/)):

| Web option | CLI flag | Notes |
|---|---|---|
| sync - only transfer new or changed files | `-s, --sync-level exists\|size\|mtime\|checksum` | `checksum` to resume after a failure |
| delete files on destination that do not exist on source | `--delete-destination-extra` | recursive only; deletes files, so the user's explicit go-ahead |
| preserve source file modification times | `--preserve-timestamp` | |
| verify file integrity after transfer | on by default; `--no-verify-checksum` | verifying adds ~25% to transfer time (NIH tests) |
| encrypt transfer | `--encrypt-data` | adds ~13% (both: ~40%); some endpoints refuse it |
| **Skip files on source with errors** | `--skip-source-errors` | continues past unreadable files; the task reports how many were skipped |
| **Fail on quota errors** | `--fail-on-quota-errors` | stops when the destination hits its quota |
| Notification Settings | `--notify off` or `--notify failed,inactive` | default: email on completion |
| — | `--label`, `--include`/`--exclude GLOB`, `--batch FILE`, `--dry-run` | `--batch`: one `SRC_PATH DST_PATH` per line (`-r` for directories), endpoints as bare UUIDs; `--dry-run` prints without submitting |

## Transfers at the end of a batch job

Compute nodes can't scp to the user's computer; NIH's recommended way to send results out at the end of a batch job is a Globus CLI transfer ([transfer.html#after_batch](https://hpc.nih.gov/docs/transfer.html#after_batch)). The user must have run `globus login` beforehand, since a job can't do the browser step. NIH's example is broken (see Stale advice); end the script like this, and give it to the user to submit:

```bash
#!/bin/bash
# #SBATCH resource lines here (JOBS.md)
set -e
# ... the job's work, with results written to /data/$USER/mydir/ ...
DEST_UUID=...   # destination collection: globus endpoint search, or the user's GCP UUID
task_id="$(globus transfer --recursive --skip-source-errors --fail-on-quota-errors \
    --label "biowulf job $SLURM_JOB_ID" --jmespath 'task_id' --format unix \
    "e2620047-6d04-11e5-ba46-22000b92c6ec:/data/$USER/mydir/" "$DEST_UUID:/path/on/dest/")"
echo "Globus task: $task_id"   # lands in slurm-JOBID.out; later: globus task show "$task_id"
```

- The transfer runs after the job ends and reads the source then: send from `/data`, never `/lscratch` (deleted with the job, and on no collection). A GCP destination must be running at that time.
- Don't `globus task wait` inside the job; waiting burns the allocation. The user gets an email, and `globus task show` works any time.
- If submission fails (exit 4: login or consent missing), `set -e` fails the job; the results stay in `/data`.

## Scheduled and recurring transfers

Globus timers run a transfer on a schedule (a nightly sync to a backup system, a big transfer delayed to Saturday midnight, a weekly move to archive), and "unlike a cron job, your recurring transfers don't depend on the availability of your system" ([globus_cron.php#cron](https://hpc.nih.gov/docs/globus/globus_cron.php#cron)). A GCP endpoint must still be running at each run. On the web: set up the transfer in the File Manager, then set the start time and repeat schedule in the transfer and timer options. CLI:

```bash
# on the compute node (you), after the user's globus login: nightly from next Saturday 00:00 local time, 30 runs
globus timer create transfer --name "dir1-nightly" \
    --start "$(date -d 'next saturday' +%Y-%m-%dT00:00:00%z)" --interval 1d --stop-after-runs 30 \
    --recursive --sync-level checksum --skip-source-errors --fail-on-quota-errors \
    "e2620047-6d04-11e5-ba46-22000b92c6ec:/data/$USER/dir1/" "$DEST_UUID:/backup/dir1/"
globus timer list; globus timer show TIMER_ID
globus timer delete TIMER_ID     # the user's go-ahead first
```

- `--interval` needs units (`8h`, `1d`, `86400s`); `--stop-after-date` is the other end condition. Give `--start` an explicit UTC offset rather than relying on the machine's time zone.
- NIH's page documents the separate `globus-timer` command (globus-timer-cli 0.2.9, Sept 2026), which upstream marks deprecated and no longer maintained. Translate its examples: `globus-timer session login` → `globus login`; `job transfer` → `timer create transfer`; `job list|status|delete` → `timer list|show|delete`; `--source-endpoint A --dest-endpoint B --item SRC DST true` → positional `A:SRC B:DST` plus `--recursive`.

## Web transfers and Globus Connect Personal

The user's checklist ([transfer.php#desktop-biowulf](https://hpc.nih.gov/docs/globus/transfer.php#desktop-biowulf)); fill in the names, paths, and options. If their computer is one end, Globus Connect Personal (GCP) must be running on it.

1. [File Manager](https://app.globus.org/file-manager) → *Log In* → organization "National Institutes of Health" → NIH login.
2. Collection `NIH HPC Data Transfer`, Path `/data/USERNAME/...` (it opens in `/home`) → 'Transfer or Sync to' → the other collection (their GCP's name) and path.
3. Select files or a directory → options (tick 'Skip files on source with errors' and 'Fail on quota errors') → *Start*. 'View details' shows progress; an email arrives on completion.

GCP on the user's computer ([setup.php#globus_connect](https://hpc.nih.gov/docs/globus/setup.php#globus_connect)):
- Install it from the Globus guides (Going further) while **off the VPN**, and decline the 'High Assurance' option: NIH has no High Assurance subscription.
- Windows without admin rights: install into a writable folder (e.g. Desktop\Globus Connect Personal) instead of `C:\Program Files (x86)\Globus Connect Personal`; at 'Windows protected your PC', *More info* → *Run anyway*.
- It sees only the home directory until other folders or network drives are added in its settings, and it must be running during a transfer.
- Globus Plus (in NIH's subscription; the user emails staff@hpc.nih.gov for an invite; it ends on leaving NIH) is needed only for GCP↔GCP transfers (e.g. their desktop and laptop), sharing from a GCP endpoint, or a share hosted on GCP; not for Biowulf↔GCP ([extras.php#plus](https://hpc.nih.gov/docs/globus/extras.php#plus)).
- NIH VDI desktops can't run GCP: VDI↔Biowulf uses WinSCP (TRANSFER.md); for another Globus endpoint ↔ Biowulf, use Globus in the VDI's browser ([extras.php#vdi](https://hpc.nih.gov/docs/globus/extras.php#vdi)).

## Sharing with collaborators

Any HPC user can share a directory from their `/data` or `/home` area with anyone who has a free Globus account, at NIH or elsewhere, without copying data ([sharing.php#sharing](https://hpc.nih.gov/docs/globus/sharing.php#sharing)). The user creates and deletes shares. You can prepare the directory (move or copy files in; symlinks inside it aren't followed) and draft the messages. NIH's rules:

- Share directories, never single files, and never top-level `/home` or `/data`: make a subdirectory, preferably under `/data/$USER`, holding only what is to be shared. Share it with named people only, never 'all users'.
- Access (read, or read/write) covers the whole subtree, and **write also allows deletion**. Read-only is the default; add write only for uploads.
- There is no write-only drop box: one share per collaborator if they shouldn't see each other's data.
- Keep controlled-access data out of shares: NIH forbids making it available to unauthorized users via Globus ([policies#CAD](https://hpc.nih.gov/policies/index.html#CAD)). Shares are for collaborators during a project, not for meeting the NIH data-sharing policy (STORAGE.md).
- Delete the share when the project is done, so files later put in that directory aren't shared unnoticed.

The user's steps: File Manager → select the subdirectory → *Share* (right pane) → *Add a Guest Collection* → leave Path, add a Display Name → *Create Share* → *Add Permissions - Share With* → find the person by email, Globus username, or name → keep *Send Email* and add a message; tick *write* only if needed → *Add Permission*. Revoke a person with the trash can beside them. To review or delete shares: https://app.globus.org/endpoints → 'Administered by You' → right arrow → 'Permissions' tab, or delete ([sharing.php#delete_share](https://hpc.nih.gov/docs/globus/sharing.php#delete_share)).

For the collaborator ([sharing.php#collab](https://hpc.nih.gov/docs/globus/sharing.php#collab)): get a free Globus account (their institution may already provide access); install GCP if downloading to a personal workstation; open the link in Globus's email, select files, choose 'Transfer or Sync to', enter their endpoint and path, and click *Start*. A Biowulf-hosted share needs no Globus Plus.

NCI HPC DME transfers also use a share: the user shares a Biowulf directory (a new folder if data is coming in) with an NCI DME Globus group (*Add Permissions* → *Group* → search `HPCDME`; the NCI DME group says which; read and write for DME → Biowulf), copies the share's UUID from its Overview tab, and starts the transfer in the DME interface ([nci_dme.php#dme](https://hpc.nih.gov/docs/globus/nci_dme.php#dme)).

## Cloud connectors

Setup is a one-time browser flow, all the user's. HPC provides no cloud accounts (see [NIH STRIDES](https://datascience.nih.gov/strides)). Sources: [cloud.php](https://hpc.nih.gov/docs/globus/cloud.php), [od_box.php](https://hpc.nih.gov/docs/globus/od_box.php).

| Target | Setup (user) | Path and notes |
|---|---|---|
| AWS S3 | Open `NIH HPC Internet2 - AWS S3` → NIH login → allow → enter the AWS Access Key and Secret Key | Buckets then appear. Update or delete keys: [Endpoints](https://app.globus.org/endpoints) → the collection → 'Credentials' tab |
| Google Cloud Storage | Email staff@hpc.nih.gov the Google identity used for the bucket and **wait for confirmation**; sign in at google.com; open `NIH HPC Google Cloud Collection` → NIH login → 'Send now and in the future' → the `@nih.gov` identity → allow → *Continue* ×3 (setup, consent, Register a Credential) → Google sign-in, every box ticked | Path **must** be `/bucketname/`, slashes at both ends; blank or `/~/` gives 'Directory Listing Failed. The server was unable to list the contents of this directory' |
| Google Drive | The same staff enablement and consent flow, with `NIH HPC Google Drive Collection` | Path `/My Drive/`. For data shared with the user: confirm it shows under 'Shared with Me' at drive.google.com, then go up one directory or use Path `/Shared With Me/` |
| NIH OneDrive | [Collections](https://app.globus.org/collections) → `NIH HPC OneDrive Collection` → 'Credentials' → *Continue* → `username@nih.gov` → NIH login → *Allow* → 'Register a Credential' → *Continue* → 'Active' | 100 GB per-file limit ([box_onedrive.html](https://hpc.nih.gov/docs/box_onedrive.html)). Won't overwrite an existing name (`nameAlreadyExists`): delete the OneDrive copy or rename the source |
| NIH Box | No Globus connector ("still being configured", as of Sept 2026) | rclone: TRANSFER.md |

S3 and GCS uploads can incur egress charges: the connector may download a file back to verify its checksum (sync transfers, transfers restarted mid-file). NIH's remedy is turning verification off (`--no-verify-checksum`). That trades integrity checking for cost, so it's the user's call.

## Troubleshooting

| Message or symptom | Fix |
|---|---|
| GCP install: browser says 'Login successful', client says `Browser login did not complete. Error: ConnectionError on request` | The user gets off the VPN (from wired NIH or 'NIH Staff' Wi-Fi, switches to 'NIH Guest') and reinstalls |
| `500 Sharing state dir has invalid permissions` when creating a share | `/home/$USER` is at quota: move files to `/data` or delete some (STORAGE.md), then retry |
| `530 Login incorrect. : Sharing not enabled for user ...` or "Your credentials do not provide sufficient access to this endpoint", creating or opening a share | `chmod 0700 /home/$USER/.globus /home/$USER/.globus/sharing && chmod 0400 /home/$USER/.globus/sharing/*` |
| `No effective ACL rules on the endpoint ...` | The share went to an email not linked to the user's Globus ID: [link it](https://docs.globus.org/guides/tutorials/manage-identities/link-to-existing/), or ask the owner to re-share to their usual address |
| 'Transfer terminated because it hit the deadline' | A fault (expired credentials, permissions) went unfixed for 3 days; fix it and resubmit with `--sync-level checksum` |
| OneDrive: `libcurl error 23: Failed writing received data to disk/application`, or timeouts at peak times | NIH gives no fix for the first; retry both |
| Globus login fails in Chrome (NIH authproxy) | Use an incognito window, or delete the authproxy cookies |

## Stale advice on the official pages

- transfer.php#cli says to "activate" endpoints at www.globus.org/app/endpoints (`ClientError.ActivationRequired`, "10 day limit"). That is the legacy model: the current CLI has no activate command and reports consent errors (exit 4) instead, which are the user's step.
- transfer.html#after_batch puts the line-continuation backslash after the destination instead of the source, so the command runs without a destination. Use the script above.
- globus_cron.php uses the deprecated `globus-timer` (translation under Scheduled and recurring transfers), and transfer.php's "Documentation about the Globus CLI" link (globus.github.io/globus-cli) is dead; use the Globus CLI reference in Going further.
- cloud.php says to search 'NIH HPC S3' (the collection is `NIH HPC Internet2 - AWS S3`). Its GCS and Google Drive sections say "S3" and "Google Cloud Storage bucket" where they mean GCS and the Drive account.

## Going further

- [setup.php](https://hpc.nih.gov/docs/globus/setup.php) — collections, NIH login, installing GCP. [transfer.php](https://hpc.nih.gov/docs/globus/transfer.php) — web transfers, options, desktop↔desktop, the CLI sample (`#cli`).
- [globus_cron.php#cron](https://hpc.nih.gov/docs/globus/globus_cron.php#cron) — timers (web; deprecated CLI).
- [sharing.php](https://hpc.nih.gov/docs/globus/sharing.php) — sharing rules and steps, collaborator instructions, deleting shares.
- [cloud.php](https://hpc.nih.gov/docs/globus/cloud.php) · [od_box.php](https://hpc.nih.gov/docs/globus/od_box.php) · [nci_dme.php](https://hpc.nih.gov/docs/globus/nci_dme.php) — S3 and Google; OneDrive and Box; NCI HPC DME.
- [extras.php](https://hpc.nih.gov/docs/globus/extras.php) — Globus Plus, VDI, encryption and performance, troubleshooting (`#trouble`). [managed_endpoint.php](https://hpc.nih.gov/docs/globus/managed_endpoint.php) — for IC system administrators running their own Globus Connect Server.
- [Globus CLI reference](https://docs.globus.org/cli/reference/) · [timer CLI migration guide](https://github.com/globus/globus-timer-cli/blob/HEAD/MIGRATING.rst) · web app: [File Manager](https://app.globus.org/file-manager), [Collections](https://app.globus.org/collections), [Endpoints](https://app.globus.org/endpoints).
- GCP install guides: [Mac](https://docs.globus.org/globus-connect-personal/install/mac/) · [Windows](https://docs.globus.org/globus-connect-personal/install/windows/) · [Linux](https://docs.globus.org/globus-connect-personal/install/linux/). Adding folders: the Mac and Windows guides' `#configuration` sections, and the Linux guide's `#config-paths`.
- Live help: `globus --help`, `globus transfer --help`, `globus timer create transfer --help`, `globus list-commands`.
