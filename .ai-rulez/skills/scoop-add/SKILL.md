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

Use the scaffolder bundled with this skill, `scripts/add_manifest.py` in this
skill's directory; do not create a manifest from scratch. Run it from the bucket
checkout (or pass `--bucket-dir <path>` / set `SCOOP_BUCKET_DIR`), as
`python <skill-dir>/scripts/add_manifest.py <route> ...`. It needs only the
standard library and a `bucket/` directory; shims also need the bucket's
`scripts/noop.ps1`. First choose the route from what upstream publishes:

| Upstream artifact | Route | Command |
| --- | --- | --- |
| Python CLI on PyPI | shim | `add_manifest.py shim <package>` |
| Prebuilt Windows `.zip` | binary | `add_manifest.py binary <owner>/<repository>` |
| Both | both | run both commands; use `--via pipx` for the shim sibling |

For a shim, `uv` is the default. `--via pipx` gives the manifest a `-pipx`
suffix. The script infers the bucket's GitHub repository from `origin` so the
manifest can download `scripts/noop.ps1`; pass `--bucket-repository` when that
cannot be inferred.

For a binary, the script fetches the latest GitHub release, classifies each
`.zip` asset that names Windows (or, when none does, every one that doesn't name
another operating system) as `64bit`, `32bit` or `arm64` from its name (no marker
means `64bit`), and writes one `architecture` block per class, with its own SHA-256
and `extract_dir` from inspecting that archive. Use `--artifact`, once per
asset, when two assets look like the same architecture. The tag's prefix before
its first digit stays literal in the autoupdate URL, and any prefix other than
`v` adds a `checkver.regex`; only a bucket whose updater is from
copier-scoop-bucket v0.2.0 or later reads it (older ones need `copier update`), so
check the warning it prints. Before the first release, use `--seed` with `--bin` and
verify the assumed tag and filename pattern later.

After scaffolding:

1. Review the description, SPDX license, URL pattern, executable, and archive
   layout.
2. Invoke `scoop-verify` for the pre-PR gate: noop URL/hash consistency,
   placeholder handling, smoke commands, README generation, local checks, and
   Windows install evidence.

Keep one package family per pull request and include verification in the PR body.
