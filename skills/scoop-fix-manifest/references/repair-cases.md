# Repair Evidence and Updater Boundaries

The bucket is empty and inspected repository history has no committed package
manifests. These are implementation- and regression-derived cases, not observed
failed installations. Inspect current code before applying them in another bucket.
See `scoop-verify/references/verification-cases.md` in the sibling skill for the
separate observed Cobo workflow failure and verification evidence.

## Cases grounded in current implementation and tests

| Evidence | Repair implication |
| --- | --- |
| `scripts/update_manifests.py`: `_latest_github`, `_latest_pypi`; `tests/test_update_manifests.py`: `test_tag_stripping`, `test_unrecognized_checkver_is_skipped_with_warning` | Native regex/JSON-path repair needs separate validation. GitHub tags and PyPI `info.version` are the updater's supported discovery paths; unsupported forms warn and skip. |
| `_update_manifest` same-version early return; `test_no_change` | A successful no-change run does not inspect same-version non-placeholder URLs, hashes, or layout. Repair these directly; do not mutate version/hash to trigger a run. The named test covers a shim; the binary boundary comes from implementation inspection. |
| `test_github_bump_rewrites_url_and_hash`, `test_update_manifest_encodes_version_in_urls` | Binary bumps expand `$version` with URL quoting and hash the actual download, not native `autoupdate.hash` metadata. Compare the expanded URL with the real release asset. |
| `test_github_skips_when_asset_missing` | An asset 404 warns and leaves the manifest unchanged. A zero exit is not proof of a repaired download. |
| `test_placeholder_manifest_updates_when_version_matches`, `test_is_placeholder`; `_is_placeholder` | A zero hash can activate without a version bump. Detection examines top-level and architecture hashes, independent of version. The activation test uses version `0.0.0`; a nonzero seed is a synthetic variation, not a historical failed install. |
| `test_manifest_missing_architecture_in_autoupdate_raises`, `test_autoupdate_extra_architecture_not_in_manifest_raises` | Concrete and template architecture sets must match; a partial repair must not leave stale/missing templates. |
| `test_update_manifest_updates_versioned_extract_dir_and_bin_from_autoupdate`, `test_update_manifest_updates_versioned_paths_fallback_without_autoupdate_templates` | String-valued paths can be updated, but URL/hash success alone does not establish installed layout. |
| `_update_manifest`: explicit `bin`/`extract_dir` template `.replace()` calls | Array-valued bin templates are unsupported by this updater, despite being valid Scoop syntax. Concrete bin arrays do not receive the string fallback. Remove redundant bin templates when the installed relative path is version-independent; keep concrete aliases and versioned extraction templates. Shortcut template processing is nested under explicit bin handling. Disclose remaining automation limits. These boundaries are implementation-derived, not covered by the named string-path regressions. |
| `tests/test_add_manifest.py`: extraction override tests; verification-cases reference | `extract_dir` changes the root against which `bin` resolves. Do not duplicate the extraction prefix. |
| `test_pypi_bump_preserves_shape`; `scripts/add_manifest.py`: `noop_source` | PyPI version updates leave static noop URL/hash intact; repair mismatched noop identity/bytes separately, including the pipx sibling. |

## Evidence to collect during a repair

Record the exact release/source response, selected asset names/architecture,
download URLs and byte digests, archive listings, and concrete/template diff.
Run native checkver separately from the repository updater when available.
Attach relevant workflow log excerpts and head SHA if a real failure exists.
Label supplied fixtures, mocked responses, and desk evaluations synthetic or
regression-derived. Do not call them Windows install evidence.

Keep temporary downloads and evaluation artifacts outside `bucket/`; do not add
fictional packages to this template to demonstrate the skill. Finish using
`scoop-verify` and report unresolved discovery/automation and install checks.
