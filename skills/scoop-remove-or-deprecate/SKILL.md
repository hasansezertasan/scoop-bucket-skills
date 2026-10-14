---
name: scoop-remove-or-deprecate
description: Remove or deprecate a Scoop manifest when retiring an upstream tool, dropping an installation route, or replacing a package. Establish deletion versus native deprecated-directory behavior, identify exact manifests and any real -pipx sibling, preserve independent alternatives and dependents, regenerate the README catalog, and finish with scoop-verify.
---

# Remove or deprecate a manifest

## Establish the intended outcome

Read `AGENTS.md`, the selected manifests, `scripts/add_manifest.py`,
`scripts/update_manifests.py`, `scripts/gen_readme_packages.py`, and applicable
workflows before changing files. Read [lifecycle evidence](references/lifecycle-cases.md)
for repository boundaries and native Scoop behavior. Derive repository identity
from the remote, Actions context, or an explicit override; preserve local work.

Confirm the exact active manifest path/token, upstream identity, reason, affected
installation routes, and any replacement. If the request says only “retire,”
“drop,” or “deprecate” without a clear outcome, ask through the native question
tool before acting:

- **Deprecation:** move the approved active JSON to root-level
  `deprecated/<same-token>.json`, preserving it for native Scoop deprecation
  detection and installed-app information fallback.
- **Removal:** delete the approved active JSON. Ask separately about any existing
  archived copy; deletion of the active route does not authorize deleting history.
- **Continued availability with a warning or automatic migration:** clarify the
  desired behavior and separately approve any mechanism. An archive move alone
  neither keeps ordinary fresh installs available nor migrates users.

Explain that native Scoop, with this repository's `bucket/` layout, excludes
root-level `deprecated/` from ordinary fresh lookup. Installed bare-name lookup
can fall back to the archived manifest; `list`, `info`, and `status` can show
deprecation markers. Normal updates do not update from the archive. Moving or
deleting Git files does not uninstall apps, run shim uninstallers, or migrate
data. Direct URL/path and historical-version installs are separate routes, so
do not promise an absolute install prohibition. Verify the user's Scoop revision
and synced bucket before making runtime claims.

## Bound the manifest set and references

Inspect the selected JSON and the exact candidate `<base>-pipx.json` (or strip
one terminal `-pipx` when starting from that route). Compare homepage/source,
PyPI `checkver`, installer package, backend and exposed commands to establish a
real relationship. The scaffolder permits custom names, so inspect metadata for
renamed alternatives when relevant. Do not infer identity from a prefix or remove
every `<base>-*` file.

Record **retain / deprecate / remove** per confirmed route. A generated pipx shim
depends on `pipx`, not its binary sibling; a uv shim depends on `uv`. Either can
remain independently useful. A failed binary download is not evidence that the
PyPI route should retire. Preserve unrelated packages, retained siblings, shared
package managers and `scripts/noop.ps1`.

Search surviving manifests for reverse references: scalar/array `depends`,
bucket-qualified tokens, installer scripts and other explicit package references.
Inspect README prose/examples outside the generated table, applicable `$smoke`
entries and install lists in `.github/workflows/tests.yml`, update workflows and
pending update PRs. Distinguish a dependency in another bucket from this retiring
token. Resolve affected dependents with the user before leaving a broken active
graph; do not substitute a replacement dependency unless it is compatible.

Confirm replacement availability, command/alias conflicts, persist/config/data
handling and route-specific uninstall effects before giving migration commands.
Shim hooks can uninstall the shared PyPI package; command availability and data
survival require evidence. Put approved reason/replacement/user-action guidance
in existing README prose outside the generated markers and, if useful, archived
`notes` (native `scoop info` displays them). Archive notes are not an automatic
warning on ordinary fresh installs or an update/migration hook.

## Make the approved lifecycle edit

Check the source and archive destination before moving. If an archive already
exists, compare its identity/content/history and ask how to reconcile it; do not
overwrite it or silently leave active and archived copies of the same token.
For explicit removal, handle any existing archive according to the approved
decision. Preserve curated JSON and last version/hash on a move except for
approved guidance; do not manufacture zero hashes or downgrade versions.

Use root-level `deprecated/`, never `bucket/deprecated/`: native lookup recursively
searches the active directory. Preserve `bucket/.gitkeep` when retiring the last
active package so `bucket/` still exists after checkout. Without it Scoop may
fall back to recursively searching the repository root, rediscovering archives.
Preserve existing directory scaffolding; do not redesign deprecation infrastructure.

Review surviving references and remove only obsolete package-specific smoke
overrides or install references as needed for the approved lifecycle operation.
Retain checks for surviving routes/replacements. In this template the install
matrix is derived from active files, so no manual package-list edit is normally
needed. Do not silently change workflow policy or scripts.

Account for automation: the updater scans only immediate `bucket/*.json`; target
`base` selects exactly `base` and `base-pipx`, not arbitrary prefixes. A retained
pipx sibling still matches that base target. Unknown targets can exit successfully
unchanged; no target or an empty target scans all active files. An updater no-op
does not verify retirement, a sibling, or migration. Do not run the updater merely
to test removal—it downloads/writes and has no CLI dry-run. Coordinate producer
dispatch changes and pending update PRs with approval instead of silently changing
external automation or reintroducing retired manifests.

## Repair handoff and verification

Invoke `scoop-fix-manifest` for necessary retained/replacement manifest repairs
(discovery, URLs/hashes, placeholders, extraction, commands/aliases/shortcuts).
If unavailable, read its sibling `SKILL.md` directly or disclose the unavailable
handoff and follow bucket invariants. Keep dependency/replacement decisions
explicit rather than presenting metadata repair as verified compatibility.

Regenerate the active catalog with `mise run generate-readme`; it excludes
`deprecated/` and does not update prose outside its markers. Inspect that only
the approved rows disappear and surviving routes remain. Finish with
`scoop-verify`, including `mise run check` and applicable surviving-manifest checks.
Explicitly check moved JSON syntax and approved notes: active JSON lint, updater,
README generation and Windows install discovery do not cover archived files.

Removal-only changes normally need the local gate, not a fresh Windows install.
Retained/replacement installer or dependency changes may need Windows evidence
under `scoop-verify`; claims about installed-app deprecation, uninstall or migration
need separate runtime evidence. Report an empty install matrix as skipped, not
passed installation. Separate source-inspected behavior and synthetic desk cases
from executed tests; keep fixtures outside the real bucket.

Report exact retained/moved/deleted paths, retirement reason, sibling decisions,
dependent/reference handling, replacement/user guidance, automation consequences,
verification passed/pending/skipped and remaining blockers. Keep publishing and
external changes subject to the user's approval.
