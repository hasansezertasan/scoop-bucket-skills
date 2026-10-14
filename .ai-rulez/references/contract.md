# Template contract

These skills operate on a Scoop bucket made from
[`bucket-template`](https://github.com/hasansezertasan/bucket-template). They
read the bucket's own scripts for exact CLI options, but rely on the names and
locations below. A template release that changes any of them must bump the
minimum template version recorded here.

Minimum template version: _unreleased (set when the template is converted to Copier)_.

## mise tasks

| Task | Used by |
|---|---|
| `add-manifest` (`shim <package>` / `binary <owner>/<repo>`) | `scoop-add` |
| `generate-readme` | `scoop-add`, `scoop-fix-manifest`, `scoop-remove-or-deprecate`, `scoop-verify` |
| `check` | `scoop-verify`, `scoop-remove-or-deprecate` |

## Files and directories

| Path | Role |
|---|---|
| `bucket/*.json` | installable manifests |
| `bucket/deprecated/` | retired manifests |
| `scripts/add_manifest.py` | scaffolder (`noop_source`, CLI options) |
| `scripts/update_manifests.py` | version, URL and hash updater |
| `scripts/gen_readme_packages.py` | README package table |
| `scripts/url_fetch.py` | download helper used by the updater |
| `scripts/noop.ps1` | shim noop script; its SHA-256 and raw URL must agree with shim manifests |
| `.github/workflows/tests.yml` | validation and Windows install |
| `.github/workflows/readme.yml` | README freshness |
| `.github/workflows/update-manifests.yml` | scheduled updates |
| `.github/workflows/update-manifest-dispatch.yml` | dispatch updates |
| `AGENTS.md` | the bucket's invariants; skills read it first |

## Not covered

Setting up a new bucket (identity, Actions, update credentials) is not part of
this plugin yet; it will scaffold the Copier template once that exists.
