Moving data in and out of Biowulf without Globus: which method to use and who runs it, downloads from the compute node through the proxy, the user's own transfers through Helix, cloud buckets, NIH Box and OneDrive, NCBI downloads, and repository uploads. Globus (large transfers, outside collaborators, end-of-job copies home): GLOBUS.md. Where data should land, quotas, sharing, and the HPC object store: STORAGE.md. Mounting Biowulf storage on the user's computer (hpcdrive): ACCESS.md.

Table of contents

- [Which method](#which-method)
- [Downloads from the compute node](#downloads-from-the-compute-node)
- [The user's transfers through Helix](#the-users-transfers-through-helix)
- [Cloud buckets](#cloud-buckets)
- [NIH Box and OneDrive with rclone](#nih-box-and-onedrive-with-rclone)
- [NCBI downloads](#ncbi-downloads)
- [Repository uploads](#repository-uploads)
- [Performance](#performance)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Which method

Every transfer runs either in your session on a compute node (through the proxy) or through Helix. The login node is never the place (its limits: ACCESS.md). Helix sees /home and /data at the same paths as Biowulf.

| Situation | Method | Who runs it, where |
|---|---|---|
| public files, repositories, datasets over http/https/ftp | `wget`, `curl`, `lftp`, `git clone https://…` | you, in the session |
| public SRA data | SRA-toolkit | you, in the session |
| dbGaP (controlled-access) data | SRA-toolkit with the user's dbGaP key | the user (their credentials and data-use terms) |
| S3 or Google Cloud buckets | `aws`, `gsutil` | you, in the session (try); else the user on Helix |
| 1–2 files to or from the user's computer | `scp` via helix.nih.gov | the user, on their computer |
| a few files; a moderate directory tree | `sftp`; `rsync` via helix.nih.gov | the user, on their computer |
| GUI on Windows or Mac | WinSCP or Fugu, host helix.nih.gov | the user |
| small files, opening HTML reports locally | hpcdrive mount (ACCESS.md) | the user |
| more than ~10 GB, unreliable links, outside collaborators, results home from a batch job | Globus (GLOBUS.md) | the user sets it up |
| NIH Box or OneDrive | rclone (OneDrive also via Globus) | the user configures on Helix; then you or the user |
| NCBI via Aspera; uploads to SRA, dbGaP, GEO, OpenNeuro | `ascp`, `scp`/`lftp`, `openneuro` | the user, on Helix |
| the HPC object store | `obj2` (STORAGE.md) | you, in the session |

Your part in user-run transfers: create the destination under /data, check `checkquota`, hand over the exact command with real paths, and afterwards verify arrival from the session (sizes, checksums).

## Downloads from the compute node

The compute nodes' Squid proxy carries http, https, ftp, and rsync-daemon traffic for programs that honor `http_proxy`, `https_proxy`, `ftp_proxy`, or `RSYNC_PROXY`: wget, curl, lftp, rsync, git. NIH's examples set nothing (their `wget` goes through `dtn02-e0:3128` on its own), so the variables appear to be preset. Confirm before relying on them:

```bash
# on the compute node (inside the session)
env | grep -i proxy                             # expect http_proxy, https_proxy, ftp_proxy, RSYNC_PROXY
checkquota                                      # room for it?
wget -P /data/$USER/ref URL                     # or curl -O, lftp
rsync mirror.umd.edu::centos/timestamp.txt .    # rsync-daemon syntax (::) only
git clone https://github.com/ncbi/sra-tools.git
```

What fails from a compute node:

- `rsync`, `scp`, or `sftp` over SSH (e.g. `rsync server.nih.gov:~/file.txt .`), and any outbound `ssh`.
- `git://` URLs and SSH remotes (`git@host:org/repo.git`): switch to the `https://` form.
- Aspera `ascp`: Helix only ([NCBI downloads](#ncbi-downloads)).
- Programs that need the proxy set explicitly: Java (DEVELOPMENT.md), Bioconductor hubs (R.md). The reverse also bites when traffic to localhost or other nodes gets sent to the proxy: h2o (R.md), multi-node training's `no_proxy` (DEEP-LEARNING.md), agent logins in OnDemand (ACCESS.md).

Practice:

- Land downloads in /data/$USER, or on /lscratch for throwaway intermediates; never in /home.
- Big downloads: total the size first (a listing, `aws s3 ls --recursive --summarize`, or `Content-Length`) and compare it with `checkquota`; if it won't fit, stop and offer a storage request, a group directory, or a subset (STORAGE.md). Stream archives into `tar` (`... | tar -xzf - -C DEST`) so they need 1x space, and set `umask 027` so nothing lands world-readable.
- NIH's FAQ says downloads "can not be easily parallelized", and the proxy runs on shared data-transfer nodes. Hold to Helix's limit of 6 parallel downloads (advice).
- If a download will outlast the session, write it as a batch job for the user to submit (JOBS.md); the commands are the same.

## The user's transfers through Helix

Give the user these to run on their computer (NIH network or VPN), with real paths filled in. Always use helix.nih.gov, never biowulf.nih.gov.

```bash
# on the user's computer (the user runs this)
scp myfile USERNAME@helix.nih.gov:/data/USERNAME/project/               # push
scp USERNAME@helix.nih.gov:/data/USERNAME/project/results.tsv .         # pull
rsync -av project/ USERNAME@helix.nih.gov:/data/USERNAME/project/       # directory tree; rerun to resume
```

- **Windows:** WinSCP (protocol SFTP, host helix.nih.gov, NIH username and password) is much faster than PuTTY's `pscp`/`psftp`, the slowest option.
- **Mac and Linux:** `scp`/`sftp` are the fastest and scriptable; Fugu is a slower GUI.
- Avoid FileZilla: NIH HPC warns that its downloads have come bundled with malware.
- **Working on Helix** (tar/gzip of big directories, `rsync` to other servers, `wget` of large sets): the user works inside `tmux` or `screen` and runs no more than 6 downloads in parallel. Transfer tools load as modules there (`rclone`, `aws`, `google-cloud-sdk`, `OpenNeuro_cli`); scientific applications don't run on Helix.
- Helix and the login node reboot monthly (ACCESS.md), so prefer resumable tools (`rsync`, `ascp -k2`) for long runs. If Helix refuses an account locked for inactivity, the user unlocks it at the dashboard (ACCESS.md).
- Compute nodes can't reach the user's computer: results go home through these commands, hpcdrive, or Globus. For a Globus step at the end of a batch job, see GLOBUS.md.

## Cloud buckets

NIH names Helix "the best place" for the cloud CLIs. They use https, which the proxy carries, so running them in the session should work, though that isn't documented; if it fails, hand the commands to the user for Helix. Credentials are the user's to enter (`aws configure` keys, `gcloud init`'s browser sign-in); never print the stored keys.

```bash
# on the compute node (inside the session), or on Helix
module load aws
aws --no-sign-request s3 cp s3://BUCKETNAME/PATH/TO/FOLDER /data/$USER/mydir --recursive   # public bucket, no credentials
aws s3 sync s3://mybucket /data/$USER/mydir                                                  # after the user's aws configure
module load google-cloud-sdk
gsutil -m cp gs://my_bucket/* .                                                              # after the user's gcloud init
```

- `gsutil -m` takes its parallelism from `parallel_thread_count` and `parallel_process_count` in the boto config (`gsutil version -l` shows which file). NIH recommends 4 and 4; in the session, keep threads × processes within the allocation.
- Azure: https://hpc.nih.gov/docs/azure.html. s3cmd: https://s3tools.org/s3cmd. Globus to AWS or Google Cloud: GLOBUS.md.

## NIH Box and OneDrive with rclone

NIH's comparison (dated 15 Sep 2022):

| | Box | OneDrive |
|---|---|---|
| Account | apply at https://boxaccount.nih.gov | automatic for all NIH personnel |
| Space | unlimited | 1 TB, up to 5 TB on request |
| Largest file | 15 GB | 250 GB (Globus limit: GLOBUS.md) |
| Share with | anyone, including outside NIH | NIH only |
| Reachable from | anywhere | NIH network or VPN |

Setup is the user's, because it needs a browser sign-in. OneDrive first needs staff to add the user to the authorized group (email staff@hpc.nih.gov).

```bash
# on Helix
module load rclone
rclone config              # n (new remote), name box, storage box (or onedrive), defaults, then n to the web-browser/auto-config question
# on the user's computer, by the user (rclone installed); paste the token it prints into the Helix prompt
rclone authorize "box"     # or "onedrive"; NIH single sign-on, NIH email, then NIH\username
```

- OneDrive: at `config_driveid`, choose the drive named "OneDrive (business)", whatever its number.
- Tokens expire and must be renewed. If a token is too long to paste, the user runs the whole configuration locally and copies that remote's section into `~/.config/rclone/rclone.conf`.
- An encrypted config needs its password for every command (`read -rs RCLONE_CONFIG_PASS; export RCLONE_CONFIG_PASS`), so those transfers stay with the user. A forgotten password means deleting `rclone.conf` and starting over.
- `rclone.conf` holds live tokens: never print, copy, or commit it.

NIH runs the transfers on Helix. rclone also runs in Biowulf jobs and talks https, so once the remote exists, try from the session; if that fails, the user runs them on Helix.

```bash
module load rclone
rclone copy --progress results.bam box:bam_files                  # copy never deletes
tar -cz mydir | rclone -P rcat box:mydir_$(date +%F).tar.gz        # many small files: stream one tarball
```

- `rclone sync` makes the destination match the source, deleting whatever the source lacks, and `rclone delete` removes files. Both need the user's go-ahead.
- Many small files: `--checkers 128 --transfers 128` helps somewhat; a tarball helps more.
- **Files over the size limit:** the user adds a `chunker` remote wrapping `box:` (e.g. `chunk_size` 10G). Uploads through it arrive as `NAME.rclone_chunk.NNN` plus a small placeholder; reassemble outside rclone with `cat biggerfile.rclone_chunk.* > biggerfile`.
- Folders others share with the user's Box appear in `rclone lsd box:` like their own.
- NIH's sample rates from Helix: Box 24–35 MB/s, OneDrive about 9.5 MB/s.

## NCBI downloads

- **SRA and dbGaP data:** use [SRA-toolkit](https://hpc.nih.gov/apps/sratoolkit.html), not Aspera. SRA-toolkit, NCBI-ngs, ngs-bam, ncbi-vdb, Entrez Direct, and hisat are configured to fetch from NCBI automatically, so they work in the session for public SRA data. dbGaP data is controlled-access: its downloads use the user's key and are the user's (table above; STORAGE.md).
- **NCBI FTP** (anonymous): the page uses the `ftp` client on Helix or Biowulf. In the session, `wget`/`lftp` with `ftp://ftp.ncbi.nlm.nih.gov/...` should work, since the proxy carries ftp. Some data exists only on FTP.
- **Aspera** (`ascp`) is up to ~5× faster than FTP but runs only on Helix: it loads the login node heavily and fails on compute nodes. It needs no module. Since Aspera 4.2, NCBI downloads need `ASPERA_SCP_PASS` set (the page puts it in `~/.bashrc`):

```bash
# on Helix
export ASPERA_SCP_PASS=743128bf-3bf3-45b5-ab14-4602c67f2950
ascp -T -i /opt/aspera/aspera_tokenauth_id_rsa -k2 -l500M \
     anonftp@ftp-trace.ncbi.nlm.nih.gov:/snp/organisms/human_9606/ASN1_flat /data/USERNAME/
```

`-k2` resumes, skipping completed files; `-l500M` matches NCBI's typical 400–500 Mb/s.

## Repository uploads

Published data belongs in a repository (NIH's data-sharing policy: STORAGE.md). Assemble and check the submission in /data from the session; the user runs the upload on Helix with the repository's credentials.

```bash
# on Helix
# SRA: NCBI's portal supplies the key file (not the page's download key) and xxxxx; rerun with -k2 to resume
ascp -i /path/to/ncbi_key_file -QT -l 300m -k1 -d /path/to/directory \
     subasp@upload.ncbi.nlm.nih.gov:uploads/YOUR_EMAIL_XXXXX
# dbGaP: ASPERA_SCP_PASS comes from NCBI; never use -T for dbGaP
export ASPERA_SCP_PASS=######-#####-#####-###
ascp -i /opt/aspera/aspera_tokenauth_id_rsa -Q -l 300m -k 1 -d /path/to/directory \
     asp-dbgap@gap-submit.ncbi.nlm.nih.gov:/protected
# GEO: FTP credentials and workspace from the user's GEO account
scp -r submission_dir geoftp@sftp-private.ncbi.nlm.nih.gov:uploads/your_geo_workspace/
```

- GEO by lftp instead: `lftp ftp://geoftp@ftp-private.ncbi.nlm.nih.gov`, then `cd uploads/your_geo_workspace` and `mirror -R submission_dir`.
- OpenNeuro (BIDS data; NIH recommends Helix):
  1. `module load OpenNeuro_cli`
  2. `openneuro login`: pick the instance and enter an API key from https://openneuro.org/keygen.
  3. `openneuro upload PATH_TO_BIDS_FOLDER` (`-i` ignores warnings). On errors, try `module load OpenNeuro_cli/4.12.1`.

## Performance

- Transfer speed matters only above about 256 MB. Run big transfers off-peak: before 10 am or after 6 pm.
- Tar directories of many small files before moving them, with a date in the tarball's name.
- Globus is NIH's recommended method for most transfers; the other rankings are under [the user's transfers](#the-users-transfers-through-helix).

## Stale advice on the official pages

- transfer.html suggests "blowfish or arcfour" ciphers for speed. Modern OpenSSH builds may not offer them; don't recommend it.
- Its first Aspera example saves to `/scratch/$USER`, which is purged and invisible to compute nodes. Save to /data.
- Its OpenNeuro fallback `NODE_OPTIONS=--no-experimental-openneuro upload PATH_TO_BIDS_FOLDER` is garbled (there's no `openneuro` command in it). Run `openneuro upload …` under the 4.12.1 module and check its help.
- Its end-of-batch-job Globus example misplaces a `\`; GLOBUS.md has a working version.
- box_onedrive.html's comparison dates from 15 Sep 2022. Its Box "Globus connector coming…" is still pending on the Globus pages, so use rclone for Box.

## Going further

- https://hpc.nih.gov/docs/transfer.html — every non-Globus method: [proxy](https://hpc.nih.gov/docs/transfer.html#compute), [NCBI](https://hpc.nih.gov/docs/transfer.html#NCBI), [SRA/dbGaP](https://hpc.nih.gov/docs/transfer.html#SRA), [GEO](https://hpc.nih.gov/docs/transfer.html#GEO), [OpenNeuro](https://hpc.nih.gov/docs/transfer.html#openneuro), [cloud](https://hpc.nih.gov/docs/transfer.html#object), [method comparison](https://hpc.nih.gov/docs/transfer.html#compare)
- https://hpc.nih.gov/docs/box_onedrive.html — full rclone configuration transcripts for Box and OneDrive, chunker setup
- https://hpc.nih.gov/apps/rclone.html — the rclone module and its use in jobs (its object-store setup is stale)
- https://hpc.nih.gov/apps/rclone_smb.html — external SMB shares from Helix with rclone and Kerberos
- https://hpc.nih.gov/docs/azure.html — Azure transfers
- https://hpc.nih.gov/apps/sratoolkit.html · https://hpc.nih.gov/apps/edirect.html — NCBI tools
- https://hpc.nih.gov/apps/ukbb.html · https://hpc.nih.gov/apps/ega.html · https://hpc.nih.gov/apps/gdc-client.html · https://hpc.nih.gov/apps/cgc-uploader.html · https://hpc.nih.gov/docs/bgionlinecli.pdf — UK Biobank, EGA, GDC, CGC, and BGI tools
- NCBI: [Aspera guide](http://www.ncbi.nlm.nih.gov/books/NBK242625/) · [SRA submission](https://www.ncbi.nlm.nih.gov/sra/docs/submitfiles/) · [dbGaP submission](https://www.ncbi.nlm.nih.gov/sra/docs/submitdbgap/) · [GEO FTP](https://www.ncbi.nlm.nih.gov/geo/info/submissionftp.html)
- Live: `env | grep -i proxy`, `rclone --help` or `man rclone`, `aws s3 sync help`, `gsutil version -l`.
