# Template contract

These skills operate on a Scoop bucket made from
[`copier-scoop-bucket`](https://github.com/hasansezertasan/copier-scoop-bucket). They
read the bucket's own scripts for exact CLI options, but rely on the names and
locations below. A template release that changes any of them must bump the
minimum template version recorded here.

Minimum template version: `copier-scoop-bucket` 0.1.0, the first release after
the Copier conversion.

Check the bucket against it before relying on the layout below: read `_commit`
in the bucket's `.copier-answers.yml`. A tag at or after the minimum (`v0.1.0`,
or a describe form such as `v0.1.0-3-gabc1234`) passes. An older tag predates the
contract, so say so and propose `copier update` with the user's approval; do not
guess at the old layout. A bare hash is indeterminate: it can be a pre-release
render or an untagged ref at or after the minimum. Ask the user which template
revision it was, or check in a template clone that it descends from `v0.1.0`
(`git merge-base --is-ancestor v0.1.0 <hash>`), and propose `copier update` only
when it does not.

## mise tasks

| Task | Used by |
|---|---|
| `generate-readme` | `scoop-add`, `scoop-fix-manifest`, `scoop-remove-or-deprecate`, `scoop-verify` |
| `check` | `scoop-verify`, `scoop-remove-or-deprecate` |

## Files and directories

| Path | Role |
|---|---|
| `bucket/*.json` | installable manifests |
| `deprecated/` | retired manifests (root level; never `bucket/deprecated/`) |
| `scripts/update_manifests.py` | version, URL and hash updater |
| `scripts/gen_readme_packages.py` | README package table |
| `scripts/url_fetch.py` | download helper used by the updater |
| `scripts/noop.ps1` | shim noop script, read by the `scoop-add` scaffolder; its SHA-256 and raw URL must agree with shim manifests |
| `.github/workflows/tests.yml` | validation and Windows install |
| `.github/workflows/readme.yml` | README freshness |
| `.github/workflows/update-manifests.yml` | scheduled updates |
| `.github/workflows/update-manifest-dispatch.yml` | dispatch updates |
| `AGENTS.md` | the bucket's invariants; skills read it first |
| `.copier-answers.yml` | recorded template source, version and answers; `copier update` reads it |

## Bundled with the plugin

The manifest scaffolder (`add_manifest.py`, with `bucket_repository.py` and
`url_fetch.py`) ships inside the `scoop-add` skill and runs against the bucket in
the working directory (`--bucket-dir` / `SCOOP_BUCKET_DIR`). It needs the
bucket's `bucket/` directory and, for shims, `scripts/noop.ps1`.
