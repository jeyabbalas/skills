What SKILL.md's storage map leaves out: what fills home, cluster scratch and node-local scratch in practice, group shares and how they're requested, checking usage, recovering deleted files, permissions and sharing, reference data, and sensitive data. The read-only checks here are yours to run in your session; deleting, restoring over an original, and loosening permissions need the user's go-ahead, and requests to the FRCE administrators or EIT Storage are the user's (ground rules in SKILL.md). Moving data in or out: TRANSFER.md. Per-job temporary directories: JOBS.md (Temporary files). What the reference trees hold: APPLICATIONS.md.

Table of contents

- [Home](#home)
- [Cluster scratch](#cluster-scratch)
- [Node-local scratch](#node-local-scratch)
- [Group shares](#group-shares)
- [Checking usage and quotas](#checking-usage-and-quotas)
- [Recovering deleted files](#recovering-deleted-files)
- [Permissions and sharing](#permissions-and-sharing)
- [Reference data and read-only areas](#reference-data-and-read-only-areas)
- [Sensitive data](#sensitive-data)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Home

- **Speed.** "The share is relatively slow and applications should not process data on the share" ([Storage page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/StorageFRCE)). Have jobs read and write in cluster scratch or a group share.
- **Privacy.** QuickStart: home "is accessible only to the account holder". Share from a group share instead ([Permissions and sharing](#permissions-and-sharing)).
- **What fills it:** tools' default caches and installs. Find the culprit, then move it with the user's go-ahead, as the owning file says:

```bash
# on the compute node (inside your session): the biggest items in home (du walks NFS slowly; run it once)
du -sh ~/.[!.]* ~/* 2>/dev/null | sort -h | tail -15
```

| Culprit | Fix in |
|---|---|
| `~/.cache/pip`, `~/.conda`, `~/miniconda/envs` (the miniconda module's default), a conda or miniforge install | PYTHON-R.md (Virtual environments and conda) |
| `~/.local/lib/python3.*` (pip's fallback) | PYTHON-R.md (Python on FRCE) |
| R libraries under `~/R` | PYTHON-R.md (R packages and libraries) |
| `~/.apptainer`, `~/.singularity` (image caches) | CONTAINERS.md (Apptainer on FRCE) |
| `~/.cache/huggingface`, `~/.cache/torch` | DEEP-LEARNING.md (Data staging and I/O) |
| `~/.ollama/models` | LLM-INFERENCE.md (Models and the shared store) |
| `~/colabfold` (ColabFold's model weights) | APPLICATIONS.md (Structural biology and AlphaFold) |
| `~/.nextflow` | WORKFLOWS.md (Nextflow) |

## Cluster scratch

The Storage page calls it "a high-performance network share" meant for "transient storage of raw data", but it is never purged and has "no protection" (SKILL.md's storage map). So:

- A file deleted or overwritten here is gone: keep irreplaceable inputs where there are snapshots too (a group share that has them, or the user's own systems).
- Keep what rebuilds the rest (code, job scripts, `environment.yml` or `requirements.txt`, `renv.lock`, container definition files) in home or git; the environments, images, and caches themselves stay here.
- It starts private (`drwx------`, live Sept 2026): "Permissions on this directory are initially set to allow access only to the user account but these permissions can be loosened" (QuickStart; how: [Permissions and sharing](#permissions-and-sharing)).
- **It's one file system for everyone, and it was nearly full**: 200 TB, 99% used, 3.5 TB free on 30 Sept 2026. The 5 TB per-user quota reserves nothing: once the share fills, every user's writes fail with "No space left on device". Check the room left before a large write ([Checking usage and quotas](#checking-usage-and-quotas)).
- List cleanup candidates for the user and delete only what they approve:

```bash
# on the compute node (inside your session): largest items, then files over 1 GB unmodified for 90 days (read-only)
du -sh /scratch/cluster_scratch/$USER/* 2>/dev/null | sort -h | tail -20
find /scratch/cluster_scratch/$USER -type f -size +1G -mtime +90 -printf '%TY-%Tm-%Td %s %p\n' 2>/dev/null | sort | head -50
```

Package and image caches have their own cleaners (PYTHON-R.md, CONTAINERS.md); pipeline work directories: WORKFLOWS.md.

## Node-local scratch

`/scratch/local` and `/tmp` are "two names for the same partition" ([hardware page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/FRCEHardwareCapabilities)). Beyond SKILL.md's storage map:

- **Size** (live, Sept 2026): one local XFS volume, 540 GB on the login node and 894 GB on the one compute node checked (48 cores, in the short and norm partitions); other node types may differ. "no quota, limited to volume size" (Storage page), and every job on the node shares it: before writing large temporary files, check `df -h /scratch/local` in a job on that node.
- **`TMPDIR`.** A job's `TMPDIR` is `/tmp/$USER` (live, Sept 2026; a login-shell setting): one directory per user, shared by all of the user's jobs on the node and not cleaned per job, so tools that honor `TMPDIR` leave files there unless the script repoints it at a per-job directory (the pattern: JOBS.md (Temporary files)).
- It's mounted `nodev`, which Apptainer warns about (CONTAINERS.md (Apptainer on FRCE)).
- It buys isolation and spares the shared servers, not speed: "Performance is comparable to that of `/scratch/cluster_scratch`" (Storage page). Copy results to cluster scratch before the job ends: afterwards only a later job on the same node can reach them.

## Group shares

"NFS shares can be created to allow groups to share files between users and to have larger disk quotas" (Storage page). Each belongs to an AD group. Live (Sept 2026) they sit in three places: dozens directly under `/mnt/<share>`, more under `/mnt/projects/<share>` (such as `/mnt/projects/CCBR-Pipelines`), and group scratch directories under `/scratch`, most named `<group>_scratch`. `/mnt` also holds system areas (`alphafold`, `gridftp`, `nasapps`, and others) that aren't group shares.

```bash
# on the compute node (inside your session): the user's groups, then the directories under /mnt and /scratch owned by one of them
id -Gn
ls -ld /mnt/* /mnt/projects/* /scratch/* 2>/dev/null | grep -wFf <(id -Gn | tr ' ' '\n')
```

- **Requesting one** is the user's: the storage form in ServiceNow (its URL, and what to do if the form refuses them: ACCESS.md (Support and requests)). The ticket should include "the name of the group being given access and that the group must have POSIX permissions assigned"; "Optionally, the contents of the share can be hidden from all other users if requested". A new AD group needs POSIX attributes too (ACCESS.md (Accounts and groups)).
- **Changing one.** "The FRCE administrators do not have privileges to modify group membership or to change the share size": membership goes through an AD group request, more space through the storage form. "The ability to change file ownership or permissions is only available on certain shares": on the others, expect `chmod` and `chgrp` to fail.
- **No Windows shares.** "It is not possible to mount SMB/Samba (Windows) shares on or from the FRCE cluster" ([diagram page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/VisualdiagramFRCESystems)): lab drives can't be mounted here, and FRCE storage can't be mapped as a drive on a PC. Data moves by transfer (TRANSFER.md).
- **Archival.** The [Services page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/Services) offers "long-term archival storage" ("available by request") with no path or procedure: the user asks the FRCE administrators or EIT Storage.
- Snapshots on shares: [Recovering deleted files](#recovering-deleted-files).

## Checking usage and quotas

FRCE documents no quota command (no `checkquota`), and `quota -s` is no help: it prints "Connection refused" errors for most shares, then "Disk quotas for user …: none" (live, Sept 2026). Use `df` and `du`, each once, in your session; `du` walks the tree over NFS, so it's slow on many files and never belongs in a loop.

```bash
# on the compute node (inside your session); SHARE is a placeholder
df -h ~                                              # home: Size is the user's 256 GB quota; Used, their usage as the NAS counts it
df -h /scratch/cluster_scratch                       # the whole 200 TB share, not the user's quota: Avail is what anyone can still write
du -sh /scratch/cluster_scratch/$USER                # the user's scratch usage, against the 5 TB quota
find /scratch/cluster_scratch/$USER -type f | wc -l  # file count
df -h /mnt/SHARE                                     # a group share: its own NFS export, so its own size and free space
```

- Room to write in cluster scratch is the smaller of the share's Avail and 5 TB minus the user's usage.
- A group share near its quota: the user asks for more through the storage form (ACCESS.md (Support and requests)).

## Recovering deleted files

Home (retention: SKILL.md's storage map): a copy 15 to 30 days old needs a ServiceNow ticket "directed to the EIT Storage group" (the user's; ACCESS.md (Support and requests)). The Storage page's listing shows one snapshot a day at 23:30, so a file created and lost on the same day is in none.

Snapshot directories are named `<number>_shared-home_shared-home`, not by date (live, Sept 2026). List them with `ls -lc`, as the Storage page does: its change times show each snapshot's 23:30, while the modification times of plain `ls -l` needn't match. `/home/.snapshot` is there on the login node (live), and compute nodes mount the same `/home`, so try it read-only from your session; if it's missing there, give the user the same lines for the login node.

```bash
# on the compute node (inside your session): the snapshots and their times, then every saved copy of one file
ls -lc /home/.snapshot/
ls -l /home/.snapshot/*/"$USER"/path/to/file
# restore beside the original; overwriting the original needs the user's go-ahead
cp -a /home/.snapshot/SNAPSHOT/"$USER"/path/to/file ~/path/to/file.recovered
```

`path/to/file` and `SNAPSHOT` (a name from the listing, such as `4162587_shared-home_shared-home`) are placeholders.

- Group shares: "Snapshots of *most* NFS shares are made daily and kept for a varying number of days depending on the requirements of the share owner. These snapshots are user accessible", but the page gives no location and none was checked live. Try `ls /mnt/SHARE/.snapshot`, by name, since such directories may not show in `ls -a`; if there's none, the user asks the share's owner or the FRCE administrators.
- Cluster scratch and `/scratch/local` have no snapshots.

## Permissions and sharing

Keep home and cluster scratch private unless the user asks to share (ground rule 4 in SKILL.md). FRCE's pages state no umask policy, but shells started with `027` in the live check (Sept 2026), and jobs inherit the submitting shell's mask (`SLURM_UMASK=0027`). NIH HPC's [table](https://hpc.nih.gov/storage/permissions.html#_best) agrees: `027` for most users, `007` for sharing with a group, never `022`, which lets everyone read. New files take the user's primary group (`id -gn`), which in the live check was a personal group named after the user, so group bits share nothing until the files belong to an AD group (below).

```bash
# on the compute node (inside your session): see the mask; set 007 in a shell or job script that writes into a group-shared directory
umask
umask 007
```

Persisting a umask means a line in `~/.bashrc`, which is the user's call (ground rule 6).

To share a directory with an AD group the user belongs to, once they've agreed (these change only files the user owns):

```bash
# on the compute node (inside your session), after the user's go-ahead; GROUP and project are placeholders
chgrp -R GROUP /scratch/cluster_scratch/$USER/project
chmod -R g+rX,o-rwx /scratch/cluster_scratch/$USER/project
find /scratch/cluster_scratch/$USER/project -type d -exec chmod g+s {} +   # new files inherit GROUP
```

- **Parents.** Members also need `x` on every directory above the shared one, and `/scratch/cluster_scratch/$USER` starts out private. Opening it takes `chgrp GROUP` plus `chmod g+x` on it (one group only), an ACL (if ACLs work, below), or `chmod o+x`, which lets anyone on FRCE enter paths they already know, though not list them: the user decides. A group share avoids the problem.
- **ACLs** (live, Sept 2026): home and cluster scratch are NFSv3 mounts (`df -hT` type `nfs`), so NFSv4 ACLs don't apply (`nfs4_getfacl` answers "Operation to request attribute not supported"), and `getfacl` shows only the mode bits, as it does even where ACLs aren't supported. Whether the servers keep POSIX ACLs is untested: try an entry that grants nothing new before relying on one, and if `setfacl` fails, share through a group.

```bash
# on the compute node (inside your session): an ACL entry for the owner grants nothing; a mask:: line in the output means ACLs work
d=$(mktemp -d "/scratch/cluster_scratch/$USER/acl-test.XXXX")
setfacl -m "u:$USER:rwx" "$d" && getfacl "$d"
rmdir "$d"
```

- Colleagues outside the group: the user requests AD group membership for them (ACCESS.md (Accounts and groups)). People without FRCE accounts: Globus (TRANSFER.md (Globus)).
- Biowulf: "Biowulf assigns account uids/gids sequentially while FRCE uses the uids/gids defined in the user's AD profile. Because of this difference, it is not possible to share NFS storage between the installations" ([Biowulf & FRCE differences](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/BiowulfFRCEdifferences)). Copy instead (TRANSFER.md (Data from Biowulf)).

## Reference data and read-only areas

Besides `/mnt/nasapps` (SKILL.md's storage map; production versus development installs: MODULES.md (Finding software)), FRCE has `/SeqIdx`, a general reference tree like Biowulf's `/fdb` that no FRCE page mentions (live, Sept 2026, seen on the login node; `ls /SeqIdx` in your session confirms it), and per-tool areas such as `/mnt/alphafold`. What they hold: the Reference data part of APPLICATIONS.md (Application index).

- Before downloading a large reference, check those and ask whether the user's group keeps one in its share: a duplicate costs scratch space that nothing reclaims.
- Containers see none of these unless bound (CONTAINERS.md (Running containers)).
- Treat other groups' shares and shared pipeline trees as read-only, even where the permissions would let you write.

## Sensitive data

- FRCE's pages say nothing about PII, PHI, or controlled-access data such as dbGaP: no approval and no ban. NIH HPC's rules for Biowulf don't carry over, and FRCE's silence isn't permission; NIH policy and the user's data-use agreements still apply.
- Before regulated data comes onto FRCE, the user confirms it's allowed there and asks the FRCE administrators where it may live (ACCESS.md (Support and requests)).
- Keep it in a group share whose AD group is exactly the authorized people, with contents hidden (an option when the share is requested); never in cluster scratch directories opened to others, Globus shares to outsiders, or anything world-readable.
- What you may read of it: ground rule 4 in SKILL.md.

## Stale advice on the official pages

- [QuickStart](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/QuickStart) gives home "a 48GB quota" → it's 256 GB, as the [Storage page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/StorageFRCE) says (live, Sept 2026: `df -h ~`).
- The [diagram page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/VisualdiagramFRCESystems) labels its storage box "/scratch/cluster_tmp" → the path is `/scratch/cluster_scratch`.
- The Storage page's recovery recipe says "Select the new snapshot" (it means the newest one taken before the loss), and its prose path `/home/.snapshot/timestamp/user` doesn't match the real names (`<number>_shared-home_shared-home`) → pick by the times `ls -lc` shows ([Recovering deleted files](#recovering-deleted-files)). Its "Restores from later than that" means snapshots older than 14 days.
- The Storage page promises snapshots on "most NFS shares" but shows only home's → find a share's snapshots live ([Recovering deleted files](#recovering-deleted-files)).
- The [Services page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/Services) lists "long-term archival storage" with no path or procedure → ask ([Group shares](#group-shares)).

## Going further

- FRCE: [Storage on FRCE](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/StorageFRCE) (areas, shares, the snapshot recipe) · [FRCE Hardware Capabilities](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/FRCEHardwareCapabilities) (standard mounts) · [Visual diagram of FRCE Systems](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/VisualdiagramFRCESystems) · [Miscellaneous Policies and Guidelines](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/MiscellaneousPoliciesandGuidelines) (who changes shares and groups) · [Biowulf & FRCE differences](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/BiowulfFRCEdifferences).
- Biowulf docs, for concepts that apply here too: [umask](https://hpc.nih.gov/storage/permissions.html#_defp) · [ACLs and the pathway rule](https://hpc.nih.gov/storage/acls.html#_pathway).
- Live: `df -h ~`, `df -h /scratch/cluster_scratch`, `du -sh /scratch/cluster_scratch/$USER`, `ls -lc /home/.snapshot`, `id -Gn`, `umask`, `findmnt -T PATH`, `ls /SeqIdx`.
