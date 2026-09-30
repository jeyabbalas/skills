Moving data in and out of FRCE: where each kind of transfer runs and who runs it, rsync and scp through the transfer node, data from Biowulf, graphical clients, Globus, downloads from the internet (compute nodes reach it directly), and instrument data. You prepare destinations, check space, and verify what arrived; transfers that run on a login host or need the user's password, browser, or Globus login are the user's (ground rules in SKILL.md). Where data should land, quotas, and sharing: STORAGE.md. Container pulls and package installs travel the same network paths: CONTAINERS.md, PYTHON-R.md.

Table of contents

- [Where to run transfers](#where-to-run-transfers)
- [scp and rsync](#scp-and-rsync)
- [Data from Biowulf](#data-from-biowulf)
- [Graphical clients](#graphical-clients)
- [Globus](#globus)
- [Downloads on the cluster](#downloads-on-the-cluster)
- [Instrument data](#instrument-data)
- [Stale advice on the official pages](#stale-advice-on-the-official-pages)
- [Going further](#going-further)

## Where to run transfers

Never on the login node: "Transferring large amounts of data can be CPU intensive and a 10-CPU-minute limit is enforced on the FRCE head node. It is recommended that you either log into fsitgl-xfer03p.ncifcrf.gov or set up an interactive batch login for data transfers" ([File Transfers](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/FileTransfers)). That host, batch2, is a shared login host, so everything run there is the user's. Whether it has the login node's CPU-time limit is untested (ACCESS.md (Connecting)); if it does, a long rsync goes in the user's `srun` session under tmux instead (whether compute nodes reach helix.nih.gov is also untested).

| Transfer | Method | Who, where |
|---|---|---|
| The user's computer ↔ FRCE | rsync, scp, or an SFTP client to `batch2.ncifcrf.gov` | the user, on their computer |
| Biowulf ↔ FRCE | rsync with `helix.nih.gov`; Globus for multi-terabyte sets | the user, on batch2 (or in an `srun` session, as above) or in the Globus web app |
| Box, OneDrive, or a Windows (SMB) share → FRCE | download to the user's computer, then as above; FRCE can't mount them (STORAGE.md (Group shares)) | the user |
| Collaborators and other Globus sites | [Globus](#globus) | the user sets it up |
| Internet downloads that fit your session | wget, curl, git, `prefetch`, `aws s3` ([Downloads on the cluster](#downloads-on-the-cluster)) | you, in your session |
| Large or long internet downloads | the same tools in a batch job, or under tmux on batch2 | a job the user submits (JOBS.md), or the user on batch2 |
| Between FRCE areas (`/mnt/gridftp` → scratch, share → share) | rsync | the user on batch2 (the documented place), or you in your session |
| A few small files through a browser | OnDemand's file browser (ONDEMAND.md (Files and Globus)) | the user |

Your part in the user's transfers: create the destination, check its space (STORAGE.md (Checking usage and quotas)), hand over the exact command with real paths, and afterwards verify arrival from your session: file counts and sizes (`find DIR -type f | wc -l; du -sh DIR`), or `md5sum` on both ends for data that matters.

## scp and rsync

```bash
# on the user's computer (NIH network or VPN) — the user runs:
rsync -aP project/ USERNAME@batch2.ncifcrf.gov:/scratch/cluster_scratch/USERNAME/project/          # push a tree; rerun to resume
rsync -aP USERNAME@batch2.ncifcrf.gov:/scratch/cluster_scratch/USERNAME/project/results/ results/  # pull results back
scp sample.bam USERNAME@batch2.ncifcrf.gov:/scratch/cluster_scratch/USERNAME/project/             # a file or two
```

- `USERNAME` is the NIH username (ACCESS.md (Connecting)); the password or key prompt is the user's (ACCESS.md (SSH keys and clients)).
- Compute nodes can't be reached from outside (ACCESS.md (Connecting)): data pushed in lands on shared storage (through batch2, Globus, or OnDemand), never on a node's `/scratch/local`.
- Rerun an interrupted `rsync -aP` to resume it. Leave the page's `-z` off for `.gz`, BAM, CRAM, and image files: it only helps uncompressed data on slow links.
- Windows' built-in OpenSSH has `scp` and `sftp` but no `rsync`: use a [graphical client](#graphical-clients).

## Data from Biowulf

The clusters can't mount each other's storage (STORAGE.md (Permissions and sharing)), so data moves by copy. Pull it on batch2 from Helix, NIH HPC's host for interactive transfers: "Such processes should not be run on the Biowulf login node" ([NIH HPC](https://hpc.nih.gov/docs/transfer.html)).

```bash
# on the transfer node (batch2), inside tmux if available — the user runs (Helix asks for the NIH password):
mkdir -p /scratch/cluster_scratch/$USER/project
cd /scratch/cluster_scratch/$USER/project
rsync -aP USERNAME@helix.nih.gov:/data/USERNAME/project/ .
```

- Size it first: the user totals the source on Helix (`du -sh /data/USERNAME/project`) and you compare that with the space left on FRCE (STORAGE.md (Checking usage and quotas)).
- Multi-terabyte or many-file sets: Globus between NIH HPC's `NIH HPC Data Transfer (Biowulf)` collection (UUID `e2620047-6d04-11e5-ba46-22000b92c6ec`, [setup page](https://hpc.nih.gov/docs/globus/setup.php#endpoints), Sept 2026) and FRCE's ([Globus](#globus)) runs unattended and retries.
- Scripts and habits that come along: FROM-BIOWULF.md (Porting a batch script).

## Graphical clients

- Settings for any SFTP client: host `batch2.ncifcrf.gov`, protocol SFTP, port 22, the NIH username and password, remote folder `/scratch/cluster_scratch/USERNAME`. Never point a client at `batch.ncifcrf.gov`: its file-transfer process would run on the login node, under the 10 CPU-minute kill.
- Clients FRCE names (File Transfers; [Connecting to FRCE](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/ConnectingFRCE)): WinSCP on Windows; MobaXterm and Bitvise, which have SFTP built in; PuTTY has no file transfer, so pair it with WinSCP. FileZilla is on the list too, against NIH HPC's advice ([Stale advice](#stale-advice-on-the-official-pages)). On a Mac or Linux, `scp` and `rsync` ([scp and rsync](#scp-and-rsync)).

## Globus

"The Globus service is not managed by the FRCE admin staff. Access requests and reporting issues must go through Service Now and be explicitly flagged to be directed to the Globus support team" ([Globus / GridFTP](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/Globus)). Every browser and login step is the user's:

1. **Enable.** A ServiceNow request asking for their account to be enabled for Globus, flagged for the Globus support team. No page names the form; the general one is in ACCESS.md (Support and requests).
2. **Log in** at the [Globus web app](https://app.globus.org) with NIH credentials: "Other credentials may not be able to access NIH-shared Globus resources."
3. **Find FRCE's collection** by searching for `nihfnlcr`. The pages' `nihfnlcr#gridftp1` is a legacy owner#name identifier: Globus now names collections by display name and UUID ([Globus docs](https://docs.globus.org/api/transfer/endpoints_and_collections/)) and ended the GridFTP-era Globus Connect Server v4 on 18 December 2023 ([Globus](https://www.globus.org/blog/support-for-globus-connect-server-version-4-ends-on-december-18-2023)). The current name and UUID are undocumented (Sept 2026); the search shows them, as does `globus endpoint search nihfnlcr` (below).
4. **Transfer.** Files land in `/mnt/gridftp/$USER`, the only documented landing path, which doesn't exist before enablement (live, Sept 2026).

The landing area:

- "Some, but not all file shares available to the FRCE cluster are mounted on the Globus servers so transferred files may need to be moved between shares after they are transferred" (File Transfers). The Globus page says to do that "preferably using fsitgl-xfer03p".
- "Currently, there are no user or group quotas on /mnt/gridftp/": it's one 237 TB share for every Globus user (73% full on 30 Sept 2026, `df -h /mnt/gridftp`), with no snapshots documented. Treat it as a landing area and move data on.
- The login node mounts `/mnt/gridftp` (lowercase; live, Sept 2026); whether compute nodes do is unchecked: `ls -ld /mnt/gridftp` in your session.

```bash
# on the transfer node (batch2) — the user runs; or you, in your session, if /mnt/gridftp is mounted there:
rsync -a /mnt/gridftp/$USER/dataset/ /scratch/cluster_scratch/$USER/dataset/
```

Remove the landing copy only after checking the new one, and with the user's go-ahead.

The CLI comes from the `globus/3.35.2` module (Sept 2026). `globus version` urges `globus update`: ignore it, since the module's install is read-only. Its login is a browser step only the user can finish:

```bash
# on FRCE (the login node, or the user's own session) — the user runs, once:
module load globus/3.35.2
globus login --no-local-server   # open the printed URL, sign in, paste the code back
```

After that, you can run the CLI in your session, since compute nodes reach the internet ([Downloads on the cluster](#downloads-on-the-cluster)). The data moves between collections, not through your node:

```bash
# on the compute node (inside your session), after the user's login; the capitalized words are placeholders
module load globus/3.35.2
globus whoami                    # fails if the login is missing or expired: hand back to the user
globus endpoint search nihfnlcr  # FRCE's collection and its UUID
globus transfer --recursive --label "biowulf to frce" SRC_UUID:/SRC_PATH/ FRCE_UUID:/DEST_PATH/   # prints a task ID
globus task show TASK_ID
```

- Globus Connect Personal on the user's computer ([install guides](https://docs.globus.org/globus-connect-personal/install/)): "With the current license arrangement, FRCE users can transfer files between `nihfnlcr#gridftp1` and personal endpoints."
- The Globus page also runs Globus Connect Personal for Linux on FRCE itself (`./globusconnectpersonal -start -restrict-paths /scratch/cluster_scratch/${USER}/`), exposing cluster scratch without the landing area. It names no host, works only while that process runs, and sharing needs Globus Plus ("One endpoint should have the Globus Plus license"): the user checks with the Globus team first.
- Sharing with collaborators: "Within `nihfnlcr#gridftp1`, users can create individual endpoints to have more control of resources to share." The user creates and removes shares; keep controlled-access data out of them (STORAGE.md (Sensitive data)).

## Downloads on the cluster

Compute nodes reach the internet directly, with no proxy (live, 30 Sept 2026): from a compute node, pypi.org, github.com, conda.anaconda.org, Docker Hub's registry, and ollama.com all answered, and no `*_proxy` variable was set. No FRCE page says so, and access has lapsed before ("The compute nodes don't have internet right now", Aug 2023, [XAVIER#34](https://github.com/CCBR/XAVIER/issues/34)), so check once per session before a download that matters:

```bash
# on the compute node (inside your session): run once
env | grep -i _proxy                                                            # expect nothing
curl -sS -m 10 -o /dev/null -w '%{http_code}\n' https://pypi.org/simple/pip/   # 200: direct access; 000 after a timeout: none
```

- **Size first:** compare it with the room left, which the nearly full scratch share can limit (STORAGE.md (Checking usage and quotas)); prefer forms that resume (`wget -c`, `curl -C - -O`, rsync). A download that will outlast your session goes into a batch job for the user (JOBS.md).
- **If the check fails:** hand the download to the user on batch2, then work on the copy from your session.
- **Certificate errors** such as `self signed certificate in certificate chain` usually mean something on the network inspects the traffic. Never turn verification off (`curl -k`, `wget --no-check-certificate`, `pip --trusted-host`, conda's `ssl_verify: false`); report it (TROUBLESHOOTING.md (Asking for help)).
- **git:** clone with `https://` URLs; an SSH remote needs a key on FRCE, the user's to set up.
- **S3:** `module load aws-cli/2.24.9` (also 2.11.4; Sept 2026). Public buckets need no credentials (`aws s3 cp --no-sign-request s3://BUCKET/KEY .`); credentials for private ones are the user's to set up.

SRA data: `module load sra-tools/3.1.0` (the only version, Sept 2026; `prefetch` and `fasterq-dump` aren't installed outside it). `prefetch` needs the internet; `fasterq-dump` doesn't once the accession is local ([NCBI](https://github.com/ncbi/sra-tools/wiki/08.-prefetch-and-fasterq-dump)):

```bash
# on the compute node (inside your session, or in a job script); SRR000001 is a placeholder
module load sra-tools/3.1.0
mkdir -p /scratch/cluster_scratch/$USER/sra && cd /scratch/cluster_scratch/$USER/sra
prefetch SRR000001                  # ./SRR000001, unless vdb-config sends prefetch to its user repository (default ~/ncbi/public); rerun to resume
# FASTQ plus temporary files take about 17 times the accession's size
fasterq-dump SRR000001 -O fastq/ -t "$TMPDIR" -e "${SLURM_CPUS_PER_TASK:-1}"
```

`$TMPDIR` must be a per-job directory made as in JOBS.md (Temporary files), not the shared default `/tmp/$USER` (STORAGE.md (Node-local scratch)); in your session, make one the same way first. Controlled-access (dbGaP) downloads use the user's key and data-use terms, so they're the user's.

## Instrument data

- "NCI laboratories can have workflows that push instrument data directly onto the NCI-F storage and this data it immediately accessible by FRCE" ([Biowulf & FRCE differences](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/BiowulfFRCEdifferences)).
- Setting one up isn't documented: presumably the lab requests a share (the storage form: ACCESS.md (Support and requests)) and has the instrument's output pointed at it; FRCE sees it under `/mnt` (STORAGE.md (Group shares)). The CCR Sequencing Facility's public pipeline code, for example, reads each run in place from its raw-data share (`/mnt/<share>/illumina/RawData_<instrument>/<run>`).
- Read raw runs in place and treat them as read-only: write outputs to cluster scratch or the lab's share, and copy a run only when a tool needs its own copy.

## Stale advice on the official pages

- [File Transfers](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/FileTransfers) pulls from Biowulf with `rsync -azP username@biowulf.nih.gov:/data/username/foo .`, through Biowulf's login node → pull from `helix.nih.gov` on batch2, and drop `-z` for compressed data ([Data from Biowulf](#data-from-biowulf)).
- File Transfers recommends FileZilla; NIH HPC says "There has been a problem with malware getting bundled with Mac and Windows downloads for Filezilla, so we strongly encourage our users to stay far away from it" ([NIH HPC](https://hpc.nih.gov/docs/ExpUserGuide.html#dontuse)) → WinSCP, MobaXterm, or Bitvise.
- [Globus / GridFTP](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/Globus):
  - `nihfnlcr#gridftp1` is a deprecated identifier form → search for `nihfnlcr` ([Globus](#globus)).
  - `/mnt/GridFTP/${USER}/` → `/mnt/gridftp/$USER`; the capitalized path doesn't exist ([Globus](#globus)).
  - "app.globus.com" → app.globus.org.
  - Its personal-endpoint link now only says the page has moved → the [Linux install guide](https://docs.globus.org/globus-connect-personal/install/linux/).
  - Its "Biowulf site" link redirects to https://hpc.nih.gov/docs/globus/, which describes Biowulf's collections, not FRCE's.
- The [diagram page](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/VisualdiagramFRCESystems) draws internet links to the login node, the transfer node, OnDemand, and the Globus server, none to compute nodes → compute nodes reach the internet directly (live, Sept 2026; [Downloads on the cluster](#downloads-on-the-cluster)).

## Going further

- [File Transfers](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/FileTransfers) · [Globus / GridFTP](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/Utilities/Globus) · [Visual diagram of FRCE Systems](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/SystemInformation/VisualdiagramFRCESystems) (hosts, storage, and the Globus server) · [Biowulf & FRCE differences](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/BiowulfFRCEdifferences) · [Connecting to FRCE](https://ncifrederick.cancer.gov/staff/FRCE/Documentation/UsageGuides/ConnectingFRCE) (clients).
- Biowulf docs: [transfer methods and Helix](https://hpc.nih.gov/docs/transfer.html) · [Globus at NIH HPC](https://hpc.nih.gov/docs/globus/) (Biowulf's collections).
- Globus: [CLI reference](https://docs.globus.org/cli/reference/) · Globus Connect Personal for [Mac](https://docs.globus.org/globus-connect-personal/install/mac/), [Windows](https://docs.globus.org/globus-connect-personal/install/windows/), [Linux](https://docs.globus.org/globus-connect-personal/install/linux/).
- NCBI: [prefetch and fasterq-dump](https://github.com/ncbi/sra-tools/wiki/08.-prefetch-and-fasterq-dump). AppDB (NIH network only): [sra-tools](https://appdb.ncifcrf.gov/software/Sra-tools).
- Live: `env | grep -i _proxy`, `curl -sS -m 10 -o /dev/null -w '%{http_code}\n' https://pypi.org/simple/pip/`, `ls -ld /mnt/gridftp/$USER`, `df -h /mnt/gridftp`, `module avail globus sra-tools aws-cli`; on batch2, the user's `ulimit -t`.
