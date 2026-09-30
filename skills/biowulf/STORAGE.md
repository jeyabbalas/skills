What SKILL.md's storage map leaves out: checking quotas and file counts, freeing a full /home, snapshot recovery, /scratch and /fdb rules, permissions, umask and ACLs, shared group directories, choosing a way to share, datashare links, the object store, and the data rules behind them. Moving data in or out: TRANSFER.md (Globus: GLOBUS.md). Requesting lscratch and pointing `TMPDIR` at it: JOBS.md. Mounting Biowulf storage on the user's computer (hpcdrive): ACCESS.md.

Table of contents

- [Quotas, usage, and file counts](#quotas-usage-and-file-counts)
- [A full /home](#a-full-home)
- [Snapshots and recovering deleted files](#snapshots-and-recovering-deleted-files)
- [/scratch and /fdb](#scratch-and-fdb)
- [Permissions and umask](#permissions-and-umask)
- [ACLs](#acls)
- [Shared group directories](#shared-group-directories)
- [Choosing a sharing method](#choosing-a-sharing-method)
- [Datashare web links](#datashare-web-links)
- [Object storage](#object-storage)
- [Data policy](#data-policy)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Quotas, usage, and file counts

```bash
checkquota                                  # Used/Quota and Files/Limit: /data, each shared dir, /home, object-store buckets
checkquota -a                               # the same with each area's physical path
module load extrautils; dust /data/$USER    # biggest subtrees; dust -f counts files instead
```

- /data areas also have a file-count limit, shown only in `checkquota`'s `Limit` column (31457280 in the page's example; /home shows `n/a`).
- On VAST, files under 128 KB can make `checkquota` and `du` report far more than the `ls` sizes add up to: tar small files that aren't in active use. Keep directories well under 1,000–5,000 files (pages differ); crowded directories slow basic reads and writes.
- Before a big download or a swarm: run one job, total its output and temp files, scale up, and compare with the free space.
- History: the [dashboard](https://hpcnihapps.cit.nih.gov/auth/dashboard)'s Disk Usage tab shows usage and file counts over time, plus monthly Krona plots of /data directories (none for /home, /scratch, or small directories).
- More space: the user files the [storage request form](https://hpcnihapps.cit.nih.gov/auth/dashboard/storage_request.php) with a justification. For a shared directory only its group owner (or PI) can ask; near or at quota, every member gets an alert email. /home stays at 16 GB.

## A full /home

A full /home means "a lot of things can go wrong". Find the culprit with `dust $HOME` (`dust -f $HOME` for file counts), then fix it with the user's go-ahead:

| Culprit | Fix |
|---|---|
| data files | move them to /data/$USER |
| a conda install or envs | they belong under /data: CONDA.md |
| `~/.cache/pip` | `rm -rf ~/.cache/pip` |
| the rest of `~/.cache` (e.g. Hugging Face models), `~/.conda` | move to /data and symlink back (below) |
| `~/.singularity/cache` | point the cache at /data: CONTAINERS.md |
| `~/.vep` | pass `--cache --dir_cache $VEP_CACHEDIR` to every VEP command |
| `~/R/...` (a pre-Jun-2023 R library) or `~/.cache/R/renv` | reinstall under /data, or move renv's cache: R.md |

```bash
# staff's move-and-symlink, same for ~/.conda; the target must not exist yet
mv ~/.cache /data/$USER/.cache && ln -s /data/$USER/.cache ~/.cache
```

## Snapshots and recovering deleted files

| Area | Snapshots | Tape backups |
|---|---|---|
| `/home` | 6 hourly, 6 daily, 8 weekly, in `~/.snapshot` | weekly full + daily incremental, onsite 4 weeks; every 4 weeks a full set goes offsite for 8 weeks |
| `/data/$USER`, shared `/data` | a few days: "2 nightly and 1 weekly" (the same page also says two daily and two weekly); very large directories may keep only one nightly | none |

- A snapshot is a read-only copy: a file is recoverable only if it existed when one was taken. Anything created and deleted between snapshots, or deleted before the oldest one, is gone, as is your session's lscratch once the session ends (copy results to /data as you go). Irreplaceable data belongs on the user's own systems too.
- `.snapshot` is hidden from `ls` but can be entered or listed by name. /data snapshots refresh every weekday and may be briefly unavailable meanwhile: retry later.

The documented steps (the page walks through them on Helix):

```bash
# /home
cd ~/.snapshot; ls                        # Hourly.*, Nightly.*, Weekly.*
cd Nightly.2016-05-06_0010                # the newest snapshot that still has the file
mkdir -p ~/restored && cp -p lostfile ~/restored/   # onto the original only with the user's OK
# /data
ls -ld /data/$USER                        # link target starting /vf/users = VAST
cd /vf/users/.snapshot; ls                # daily_*, weekly_*
cd weekly._2020-06-14T00_00_00.045003UTC
cd $USER                                  # or the shared directory's name
mkdir -p /data/$USER/restored && cp -p lostfile /data/$USER/restored/   # likewise
```

From your session, reading `.snapshot` on a compute node is undocumented: try it read-only, and if the path is missing or unreadable, give the user the steps above to run on Helix.

- Find every snapshot copy at once: `ls -l ~/.snapshot/*/path/to/lostfile` or `ls -l /vf/users/.snapshot/*/$USER/path/to/lostfile`. Go straight to `$USER` or the group's directory; the other names there are other users' data.
- Restore beside the original (e.g. into `/data/$USER/restored/`) unless the user approves overwriting: the page's `cp` onto the original path clobbers any newer file. Run `checkquota` before restoring a large tree.
- The last GPFS system was retired in the 29 Jul–2 Aug 2026 downtime ([announcement](https://hpc.nih.gov/nih/about/announcements.php?1208)), so /data should resolve to `/vf/users/...`. If it doesn't, the page has no recipe: the user asks staff. Versions older than the /home snapshots survive, if at all, only on tape, with no documented self-service restore: the user asks staff@hpc.nih.gov.

## /scratch and /fdb

/scratch exists only on Helix and the login node, so you never see it from the session; it matters when the user works there. There's no per-user directory by default: create one (`mkdir /scratch/NAME`). Up to 10 TB per user, not guaranteed (100 TB shared, low performance). Files are deleted 10 days after last access, and sooner once the area passes 80% full; not backed up.

/fdb holds staff-maintained reference data: BLAST databases (`/fdb/blastdb/nr`, `/fdb/blastdb/nt`, `/fdb/blastdb/swissprot`, …), NCBI data, Illumina iGenomes, Ensembl, and genomic indices. App pages also use `/fdb/igenomes_nf/`, `/fdb/VEP/110/cache`, `/fdb/snpEff/5.1d/data/`, and `/fdb/imagenet`.

- Search https://hpc.nih.gov/refdb/ (by keyword or filename) before downloading a reference into /data.
- Treat /fdb as read-only; the docs say nothing about write access, quotas, or backups. For a new database or an update, the user asks staff@hpc.nih.gov. Binding it into containers: CONTAINERS.md.

## Permissions and umask

- NIH prohibits world access to users' directories. Keep /home and /data at most `g+rwx`, and share through a Unix group or ACLs.
- umask, per NIH's table: `027` is recommended for most users, `077` is private, and `007` suits group sharing where members edit each other's files. `022` and `002` make new files world-readable (warning); `000` is "DANGER". Check it with `umask` and set it per session or job script with `umask 007`. Persisting it means a line in `~/.bashrc`, which needs the user's OK.
- Directory modes (NIH's verdicts): `0700`/`0750` safe; `0770` lets group members delete any file inside, whatever its own mode; `2770` (setgid: new items inherit the group) is the standard for shared directories; `3770` adds the sticky bit so only owners delete (new subdirectories don't inherit it); `0701`/`0703` is "security through obscurity"; `0755` danger; `0777` "INSANE!". Files: `0600`/`0640` safe, `0660` lets the group edit, `0666` danger.

## ACLs

ACLs work only on /data; `setfacl` on /home fails. A `+` after the mode in `ls -l` means ACLs are present, and `getfacl PATH` lists them. Every grant shares data: make it only with the user's go-ahead.

```bash
setfacl -m u:friend:r-x DIR       # one user; a user entry overrides that user's group entries
setfacl -m g:Friends:r-x DIR      # another group
setfacl -m d:u:friend:r-x DIR     # default ACL: inherited by new files and subdirs (independent of the entry above; set both)
setfacl -m g::r-- FILE            # change the owning group's bits without breaking the ACLs
setfacl -x u:friend FILE          # remove one entry (--remove-all strips every ACL)
```

- **The mask trap.** ACLs keep their mask in the group permission bits. `chmod g…` (including `chmod -R g+rwX`) on an ACL'd path rewrites the mask, silently widening or cutting back the effective access of every named entry; use `setfacl -m g::…` instead.
- Inside a directory with default ACLs the umask is ignored. Effective access is entry ∧ mask, so a new file can show `user:friend:r-x  #effective:r--`.
- **Pathway.** A grant deep in a tree also needs `--x` for that user on every parent up to /data/$USER. Keep everything along the path non-world-accessible.
  ```bash
  setfacl -m u:friend:rw- /data/$USER/sub1/sub2/file.txt
  setfacl -m u:friend:--x /data/$USER/sub1/sub2/ /data/$USER/sub1/ /data/$USER/
  ```
- `getfacl_path -p PATH` shows owner, mode, and ACLs for every component of a path. `setfacl_path -p PATH -a '-m u:friend:rX' -d` dry-runs one ACL on every component, skipping root-owned items and symlinks; drop `-d` to apply. Parents get the full entry (listable with `rX`), not just `--x`.
- `mv` and `cp -p` carry the source's ACLs (or lack of them); the target's default ACLs are not applied. Re-apply after moving files into a shared tree.
- Before changing ACLs on shared data (with the user's go-ahead), save them and dry-run:
  ```bash
  getfacl -R -p /data/GROUP/proj > /data/$USER/acl-backup-$(date +%F).txt   # undo: setfacl --restore=FILE
  setfacl --test -R -m g:GROUP:r-X /data/GROUP/proj                          # prints the result, changes nothing
  ```

## Shared group directories

- New: the group owner applies at https://hpcnihapps.cit.nih.gov/auth/dashboard/shared_data_request.php. Joining: the owner adds members via the dashboard or https://hpcnihapps.cit.nih.gov/auth/dashboard/group_change.php. Every member needs a Biowulf account. The directory is reachable from Helix, the login node, compute nodes, and hpcdrive.
- Roles: the group owner is the first member listed. Only the owner (or the PI) can add or remove members and request more quota. The PI holds final responsibility for the data. If the owner leaves NIH, the next listed member becomes owner.
- The top directory is `drwxrws---` with setgid, so new items inherit the group. Items copied or moved in may keep their old group and mode, and subdirectories can lose setgid.
- Members set their umask as agreed with the owner (`007` if everyone edits everything) and make jobs write group-readable files; before leaving, they delete what isn't needed and make the rest group-readable. Group practice: plan subdirectories up front, ≤5,000 files per directory, systematic names, a README per directory, and tar/gzip idle directories (dated names) for the lab or IC archive.
- Only a file's owner can fix its group or mode, and staff won't step in while that owner is still in the group. A departed member's files show a 4–5-digit number as owner; the group owner asks staff to reassign them.

| Symptom | The file's owner runs |
|---|---|
| "Permission denied" opening a folder | `chgrp GROUP DIR; chmod g+rx DIR` |
| can read but not write | `chmod g+w DIR` |
| new folders aren't group-writable | `umask 007` (persisting it in `~/.bashrc` needs the user's OK), then `chmod g+w` on existing ones |
| new folder has the wrong group | `chmod g+s PARENT; chgrp GROUP NEWDIR` |

The groups page's bulk repair can only change files the user owns (`--quiet` hides the errors for the rest). Get the user's go-ahead, and run long repairs under tmux. On trees with ACLs, use `setfacl`, not `chmod g…`:
```bash
chmod -Rc --quiet g+rwX /data/$shared_data_group_name
chown -Rc --quiet :$shared_data_group_name /data/$shared_data_group_name
```

## Choosing a sharing method

| Recipient | Method | Who acts |
|---|---|---|
| HPC account holder, one-off, non-private files | world-readable directory in /scratch (below) | the user, on Helix |
| HPC account holder, part of the user's /data | ACLs | you, once the user approves the exact grants |
| several HPC users, ongoing | shared /data directory and group | the group owner requests it |
| anyone, including outside NIH | Globus share | the user (GLOBUS.md) |
| no HPC account | NIH Box (can share outside NIH) or OneDrive (NIH only) | TRANSFER.md |
| anyone given the URL | datashare link | below |
| none of these fit | staff@hpc.nih.gov | the user |

The /scratch hand-off is for non-private files only: everyone on the systems can read them. Never open a personal `/scratch/$USER` this way, since anyone could then read and delete its files.
```bash
# on Helix
mkdir /scratch/MyUniqDir; chmod a+rx /scratch/MyUniqDir
cp myfile.txt /scratch/MyUniqDir; chmod a+r /scratch/MyUniqDir/myfile.txt
rm -rf /scratch/MyUniqDir        # once the collaborator has copied it (on Helix)
```

## Datashare web links

A `datashare` subdirectory of a /data directory is served at `https://hpc.nih.gov/~[user]/[file]`, read by the web server's user `webcpu` through ACLs. [user] is the /data directory's basename (a group directory gives `https://hpc.nih.gov/~MyGroup/file`); [file] includes any subdirectories below `datashare`. It isn't browseable or indexed, but anyone holding an exact URL can download without logging in. Files are served as downloads, not web pages; a common use is UCSC Genome Browser tracks (`bigDataUrl=https://hpc.nih.gov/~user/bigBedExample.bb`).

Setup publishes data, so it needs the user's go-ahead (never CAD or PII):
```bash
setfacl -m u:webcpu:r-x /data/$USER/
mkdir --mode=0750 /data/$USER/datashare
setfacl -m u:webcpu:r-x,d:u:webcpu:r-x /data/$USER/datashare
```
- Items moved or `cp -p`'d in keep their old ACLs; re-apply access, e.g. `setfacl -R -m u:webcpu:rX /data/$USER/datashare`.
- The page also offers `find /data/user/datashare/ -mindepth 1 -exec chmod o+rX {} \;`. That makes the contents world-readable, which the page calls safe only while /data/$USER grants the world nothing. Use it only if the user explicitly chooses it, and never widen the rest of /data.
- If setup fails, the user contacts staff.

## Object storage

A tape-based SpectraLogic BlackPearl with an S3 API ("buckets"); the older "vaults" system was retired in Summer 2023. Expect high latency.

- It's for data in use that rarely changes; frequently updated data must not go there. Applications must not read or write it directly: stage through /lscratch (or /scratch on Helix) and copy in once writing is done.
- There are no backups and no snapshots: a deleted object is gone.
- Access: the user emails staff@hpc.nih.gov; the user (or staff) puts the key pair, sent by secure email, in `/home/$USER/.boto3` with `chmod 0400`. Never print, copy, or ask for it.

`obj2` works interactively and in batch scripts. Each subcommand has `--help`; add `-b BUCKET` when the bucket name isn't the username.

| Command | Notes |
|---|---|
| `obj2 put` | wildcards OK; the source stays and still counts against its quota |
| `obj2 get` | wildcards OK; can restore mtime and mode of files stored with `obj2 put`, or stream to stdout |
| `obj2 ls` | slow with many objects: keep your own index |
| `obj2 rm` | only the `?` wildcard; permanent, so get the user's go-ahead |
| `obj2 df` | usage per bucket; over the allocation, new objects can't be stored |

rclone and the AWS CLI are also supported (the page configures both on Helix; the user enters the keys). rclone: a remote of type `s3`, provider `Other`, the key pair, region option 1 (v4 signatures, empty region), endpoint `https://bpds3:8443`; add `--s3-no-check-bucket` when putting data, or you may get permission errors. AWS CLI: `aws configure --profile hpc-object`, then `--endpoint-url=https://bpds3:8443` on every call.

```bash
rclone ls hpc-object:bucketname
aws s3 --endpoint-url=https://bpds3:8443 --profile=hpc-object ls s3://bucketname
```

Globus can't reach the object store yet ("planned"; as of Sept 2026, per object.html).

## Data policy

- **PII/PHI:** forbidden anywhere on NIH HPC storage, by any transfer route, unless staff make special arrangements.
- **Controlled-access data** (e.g. dbGaP) is allowed if the user meets the provider's agreement: only authorized users may be able to read it; it never goes into datashare or out to others (e.g. a Globus share with unauthorized people); in a shared directory every group member must be authorized, which the group owner maintains as membership changes.
- **Not archival:** /data is for active work; after publication, move data to an IC archive. Biowulf storage and Globus sharing do not satisfy the NIH Data Management and Sharing Policy. Published data goes to a repository (uploads: TRANSFER.md); the Scientific Director's office advises on which.
- **Leaving NIH:** data is deleted six months after the account is (account timeline: ACCESS.md), unless the user or PI moves it off or transfers it to another account.

## Stale advice on the official pages

- backups.html gives both "2 nightly and 1 weekly" and "two daily and two weekly" for /data. It describes names as `daily_<timestamp>` while its example is `weekly._2020-06-14T00_00_00.045003UTC`, and it calls `Nightly.2016-05-06_0010` a 6 am snapshot. Always `ls` and pick by timestamp. Its Windows mapped-drive recovery section is empty.
- /scratch purge: trust the storage page (10 days after last access; early deletion above 80% full) over the Experienced User Guide ("90%", "purged every two weeks").
- Example paths `/gpfs/gsfs*`, `/gs3`, `/gs11`, and `/spin1` (acls.html, `getfacl_path`, `setfacl_path`) and `/gs6` (groups.html) predate VAST; real output shows `/vf/...`.
- apps/rclone.html configures the retired object store (`os1naccess2`/`os3access1`, vaults, v2 signatures, `--no-check-certificate`). Use object.html's settings above.
- sharing_data.html points Globus links at the old `storage/globus.html` (current: https://hpc.nih.gov/docs/globus/), and its "Acronis" quick link leads nowhere.
- The storage page's `checkquota` sample labels buckets "ObjectStore Vaults".
- The FAQ runs `dust` without `module load extrautils`; load the module if `dust` isn't found.

## Going further

- https://hpc.nih.gov/storage/ — storage areas, `checkquota`, `dust`, Krona plots, best practices
- https://hpc.nih.gov/storage/backups.html — backup and snapshot policy, recovery steps
- https://hpc.nih.gov/storage/permissions.html — mode and umask tables with NIH's verdicts
- https://hpc.nih.gov/storage/acls.html — ACL walkthrough, [pathway](https://hpc.nih.gov/storage/acls.html#_pathway), [troubleshooting](https://hpc.nih.gov/storage/acls.html#_troubleshooting)
- https://hpc.nih.gov/docs/biowulf_tools.html#setfacl_path — `getfacl_path`/`setfacl_path` usage and examples
- https://hpc.nih.gov/storage/sharing_data.html — sharing options by type of collaborator
- https://hpc.nih.gov/docs/groups.html — group roles and the permissions FAQ; slides: https://hpc.nih.gov/training/handouts/Data_Management_for_Groups.pdf
- https://hpc.nih.gov/nih/datashare.html — datashare setup and URLs
- https://hpc.nih.gov/storage/object.html — object store, `obj2`, rclone and AWS CLI setup
- https://hpc.nih.gov/refdb/ — reference data search
- https://hpc.nih.gov/policies/index.html — PII/PHI, CAD, data sharing, account deletion
- Live: `checkquota`, `getfacl_path -h`, `setfacl_path -h`, `obj2 ls --help`, `man setfacl`, `man getfacl`.
