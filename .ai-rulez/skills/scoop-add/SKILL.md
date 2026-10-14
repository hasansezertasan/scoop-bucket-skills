---
type: Playbook
title: Scoop Add
description: Use when adding a PyPI shim or prebuilt Windows binary manifest to this Scoop bucket.
x-ai-rulez:
  kind: skill
  id: scoop-add
  metadata:
    name: scoop-add
---

# Add a Scoop Manifest

Read the [template contract](../../references/contract.md) for the task names and paths
this skill relies on.

Use `scripts/add_manifest.py`; do not create a manifest from scratch. First choose
the route from what upstream publishes:

| Upstream artifact | Route | Command |
| --- | --- | --- |
| Python CLI on PyPI | shim | `mise run add-manifest shim <package>` |
| Prebuilt Windows `.zip` | binary | `mise run add-manifest binary <owner>/<repository>` |
| Both | both | run both commands; use `--via pipx` for the shim sibling |

For a shim, `uv` is the default. `--via pipx` gives the manifest a `-pipx`
suffix. The script infers the bucket's GitHub repository from `origin` so the
manifest can download `scripts/noop.ps1`; pass `--bucket-repository` when that
cannot be inferred.

For a binary, the script fetches the latest GitHub release, selects a `.zip`,
computes SHA-256, and inspects the archive for `extract_dir` and `bin`. Use
`--artifact` when several archives exist. Before the first release, use `--seed`
with `--bin` and verify the assumed tag and filename pattern later.

After scaffolding:

1. Review the description, SPDX license, URL pattern, executable, and archive
   layout.
2. Invoke `scoop-verify` for the pre-PR gate: noop URL/hash consistency,
   placeholder handling, smoke commands, README generation, local checks, and
   Windows install evidence.

Keep one package family per pull request and include verification in the PR body.
