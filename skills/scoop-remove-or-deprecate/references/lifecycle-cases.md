# Lifecycle Evidence

## Repository evidence

At base `e2e09e243a4c9bb87fbab4ce106c121b0b2ce778`, both `bucket/` and
`deprecated/` contain only `.gitkeep`. Available local history contains no
committed package JSON or observed package retirement. Commit
`a8fbd3175b59516fe8a3d930ac6b005faaaa4b52` added the archive scaffold;
`e65d04706e46b098bde896f8e8ce1c03db61251d` removed it on a different branch,
not current main. Neither is a package lifecycle incident.

Reinspect implementation and history in the affected bucket. Keep operational
identity derived from its remote/context or an explicit override.

| Source at the base revision | Lifecycle implication |
| --- | --- |
| `scripts/add_manifest.py`: `normalize`, `add_shim`, `render_shim`; `tests/test_add_manifest.py`: pipx naming and rendering cases | Default pipx naming uses the normalized PyPI name plus `-pipx`; `--name` can override it in implementation. Shim installers identify the actual PyPI package and depend on `pipx`/`uv`, not a binary sibling. Filename similarity alone is insufficient. |
| `scripts/add_manifest.py`: `_write_manifest` | Collision checking covers the active destination, not archived names. Inspect archives when reusing/restoring a token; do not assume the scaffolder reconciles them. |
| `scripts/update_manifests.py`: `main`, `_matches`; `tests/test_update_manifests.py`: package-family selection cases | Only immediate active JSON is scanned. Target matches exact stem and its explicit `-pipx` sibling, excluding unrelated prefixes. Archive exclusion follows implementation; the family tests use temporary manifests/mocks, not real retirement. |
| `scripts/gen_readme_packages.py`: `build_table`, `splice`, `main`; `tests/test_gen_readme_packages.py` | Catalog generation scans only active JSON and replaces only the marked table. Empty-table and package-row tests are regression-derived, not historical archive moves. |
| `.github/workflows/tests.yml`: JSON lint, discovery, `test` job's install/smoke steps, `$smoke` | Syntax lint and Windows matrix cover active files only. Smoke overrides use full manifest tokens; fallback strips terminal `-pipx` and runs `version`. Empty bucket skips installs. Archived JSON needs an explicit syntax check. |
| `.github/workflows/readme.yml`: path filters; update workflows | Active deletion triggers catalog automation; archive-only edits do not. Update workflows have no retired-token handling and can report generic no-change success. |

Read sibling `scoop-verify/references/verification-cases.md`,
`scoop-fix-manifest/references/repair-cases.md`, and
`scoop-update-triage/references/triage-cases.md` for verification and updater
boundaries. The observed Cobo failure is managed `.gitignore` drift, not a
removal/deprecation incident; use managed sync rather than hand-editing it.

## Native Scoop behavior: source evidence, not Windows execution

Inspected Scoop revision `e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f` (0.6.0).
These pinned upstream sources establish the native mechanism; verify the actual
client revision and bucket sync before claiming observed behavior:

- [`lib/buckets.ps1:3–29`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/lib/buckets.ps1#L3-L29):
  `Find-BucketDirectory` selects `bucket/` when present unless `-Root` is requested;
  otherwise it returns the repository root. Preserve the empty active directory.
- [`lib/manifest.ps1:1–3,43–112`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/lib/manifest.ps1#L43-L112):
  normal manifest lookup recursively searches the selected active directory.
  Installed bare-name requests tied to a bucket can fall back to root-level
  `deprecated/`; explicit `bucket/app` requests bypass that fallback. Fresh
  lookup does not separately search the archive. URL/local-path requests and
  historical `@version` resolution are distinct routes, not an install ban.
- [`libexec/scoop-list.ps1:43–48`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/libexec/scoop-list.ps1#L43-L48)
  and [`libexec/scoop-info.ps1:61–85`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/libexec/scoop-info.ps1#L61-L85):
  archived filename presence enables installed-app deprecation markers.
  [`info:278–281`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/libexec/scoop-info.ps1#L278-L281)
  displays manifest notes; notes do not implement automatic migration.
- [`lib/core.ps1:567–596`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/lib/core.ps1#L567-L596)
  and [`libexec/scoop-status.ps1:54–75`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/libexec/scoop-status.ps1#L54-L75):
  status checks deprecated presence independently of ordinary manifest absence;
  both `Deprecated` and `Manifest removed` can appear after an archive move.
- [`libexec/scoop-update.ps1:261–302`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/libexec/scoop-update.ps1#L261-L302)
  and [`437–483`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/libexec/scoop-update.ps1#L437-L483):
  updates use ordinary manifests, not the deprecated fallback. Missing targets
  may look current in an ordinary update; forced update can print “No manifest
  available” and still reach exit zero. Neither proves migration or availability.
- [`libexec/scoop-uninstall.ps1:51–104`](https://github.com/ScoopInstaller/Scoop/blob/e6aa3b366bdee8ed138c1e0f7b85192ebdd35d0f/libexec/scoop-uninstall.ps1#L51-L104):
  uninstall uses the saved installed manifest. Editing an archive does not change
  existing uninstall hooks; a Git move does not execute them.

The upstream changelog records deprecation-directory fixes, but inspected tests
provide no dedicated end-to-end retirement test. Source inspection does not
prove install, status, uninstall, or data migration on Windows.

## Synthetic desk scenarios

Use these implementation-grounded situations to evaluate decisions, not as
claims about published packages or failed installations:

- Ambiguous retirement with an independent pipx route, unrelated prefix package
  and surviving reverse dependent: establish outcome and exact per-route scope
  before edits; resolve dependent compatibility.
- Archive both last active routes with an approved replacement: preserve
  `bucket/.gitkeep`, prevent destination overwrite, explain native markers versus
  migration, regenerate the catalog and explicitly check archived JSON syntax.
- Remove only a failed binary while its pipx route survives and an older archive
  exists: do not implicitly delete the archive or retained route; account for
  exact updater selection and misleading successful no-ops.

Keep temporary fixtures outside `bucket/`. Report desk grading separately from
local checks and Windows evidence, without claiming incremental benefit unless
paired results demonstrate it.
