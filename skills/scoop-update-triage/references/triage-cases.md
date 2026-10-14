# Update Triage Evidence

At base `127654e3c09e2db69d301b826a2749a3d92da164`, the bucket contains only
`.gitkeep`; inspected local history has no committed package manifests.
The cases below are implementation/regression-derived unless explicitly marked
observed. Reinspect current code when using this skill in another bucket.

## Observed workflow evidence

The four available scheduled runs inspected on 2026-10-08 were successful;
the dispatch workflow had no available runs. Latest scheduled run:
<https://github.com/hasansezertasan/bucket-template/actions/runs/37352758748>,
at `2e6d55f0e82eacac343bd266d9ad24b852ea10da`, reported
`No updates available.` and no PR creation because the branch was not ahead.
Its missing remote `auto-update/scheduled` ref was handled by the PR action;
it was not a failed update. This empty-bucket run proves no package download,
hash validation, or installation.

The separate observed Cobo failure is documented in sibling
`scoop-verify/references/verification-cases.md`. Do not recast managed-boilerplate
drift as an upstream update failure. No observed rename, rate-limit, hash-mismatch,
or rejected-dispatch incident was found in these available update runs.

## Implementation and regression scenarios

| Evidence | Triage lesson |
| --- | --- |
| `scripts/update_manifests.py`: `main`, `_matches`; `tests/test_update_manifests.py`: package-family selection tests | Exact stem plus explicit `-pipx`, not wildcard prefixes. Unknown target succeeds unchanged; no target/empty target scans all. |
| Both update workflows: captured `has_failures`, PR step, final status step; `test_one_failure_does_not_abort_rest` | Partial success can produce a PR even when the job fails. Inspect all errors and retain valid updates. |
| `_latest_github`; `test_missing_tag_name_raises_with_context`; historical `cadac29` | Mocked “rate limited” JSON establishes contextual missing-tag diagnostics, not an observed HTTP 403/429 incident. Check actual HTTP evidence before blaming limits. |
| `_update_manifest` asset HTTPError handling; `test_github_skips_when_asset_missing` | Download 404 warns/skips, unlike discovery 404. Rename versus publication delay is a synthetic diagnostic variation, not a recorded rename. |
| `_update_manifest` same-version early return; `_sha256`; `test_no_change`, `test_github_bump_rewrites_url_and_hash` | Same-version non-placeholder downloads are not checked; bumps hash fetched bytes without comparing an expected trusted checksum. Hash mismatch is a synthetic integrity scenario, not a dedicated updater failure/test. |
| `test_placeholder_manifest_updates_when_version_matches`; architecture coverage and URL-encoding tests | Zero-hash activation is supported; architecture/template consistency and quoted version expansion matter. |
| Versioned extraction/bin tests; `_update_manifest` explicit string `.replace()` and shortcut nesting | Path updates have limited support. Read sibling `scoop-fix-manifest/references/repair-cases.md` before a layout repair. |
| Dispatch `Validate payload` and updater invocation | Raw fields enter via env; anchored patterns precede `$GITHUB_ENV`, quoted package use follows. Invalid payload examples are workflow-derived, not observed rejected events. Version is informational. |
| Scheduled `dry_run` PR condition and updater `main` | Workflow dry-run still downloads/writes locally; there is no updater CLI dry-run or version override. |

Keep evaluation fixtures and downloads outside `bucket/`. Record supplied
fixtures as synthetic and mocked tests as regression-derived. Capture real run
URLs, excerpts and SHAs separately if future incidents provide stronger evidence.
