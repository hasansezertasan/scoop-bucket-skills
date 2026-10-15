# Template contract

These skills operate on a Scoop bucket made from
[`copier-scoop-bucket`](https://github.com/hasansezertasan/copier-scoop-bucket). They
read the bucket's own scripts for exact CLI options, but rely on the names and
locations below. A template release that changes any of them must bump the
minimum template version recorded here.

Minimum template version: `copier-scoop-bucket` 0.1.0, the first release after
the Copier conversion.

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
