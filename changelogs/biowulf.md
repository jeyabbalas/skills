# biowulf changelog

Changes to [`biowulf`](../skills/biowulf/SKILL.md), newest first. What major, minor, and patch mean: [README → Versions](../README.md#versions).

## 1.0.0 — 2026-10-01

- First versioned release: the field guide compiled from hpc.nih.gov in September 2026. Earlier changes are in the [commit history](https://github.com/jeyabbalas/skills/commits/biowulf--v1.0.0/skills/biowulf).
- If you installed the plugin at 0.6.0, this also brings a full recheck against the live hpc.nih.gov pages and the tools themselves. Stale facts are fixed: svis and the `visual` partition are retired, and the swarm 26.6, Snakemake 9, and globus-cli 3.30 flags are current. There is a where-am-I row for batch jobs, and the rules on waiting for jobs and deleting files are clearer. Snakemake 9 ignores the NIH profile's `max-jobs-per-second`, so the setup now adds `max-jobs-per-timespan: "1/1s"`.
