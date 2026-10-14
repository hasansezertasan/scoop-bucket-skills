---
description: Repair existing Scoop manifests by editing them when checkver stops matching upstream, autoupdate URL or hash drifts from the real download, extract_dir or bin changes, or hashes are all-zero placeholders. Keep concrete downloads and future update templates aligned, then invoke scoop-verify for the readiness verdict.
name: scoop-fix-manifest
# Content-Hash: blake3:e4e919d3510618291ce2ce38a72886ea8bc524bc4a3d4607e45b6845cbd8b30f
# Source-Hash: blake3:809177ec0a6d5f97278a24c5aaecee0c7b50591bbfbc88b4dec1022a570dbfe9
---

# Repair a Scoop Manifest

Repair the affected package family, including relevant `-pipx` siblings, without
re-scaffolding over curated metadata. Derive bucket identity from `origin` or an
explicit override. Read the manifest, `scripts/update_manifests.py`, and the
relevant upstream release before editing. Read `references/repair-cases.md` for
repository evidence and updater limitations; its examples are regression-derived,
not recorded failed Windows installs.

## 1. Reproduce and classify

Record the failing command or workflow/head SHA, current version, source response,
and affected architecture. Compare all top-level and architecture-specific
`url`, `hash`, `extract_dir`, and `bin` fields with their `autoupdate` counterparts.
Distinguish version discovery, asset selection, checksum, and installed-layout
failures. A Cobo `.gitignore` drift failure is a managed-sync problem, not a
manifest defect; use the managed sync process instead of hand-editing it.

Fetch the exact upstream release metadata and asset list. Check response status
and content: a rate limit, missing release, or HTML error page is not a new asset
or a reason to loosen a version regex. Do not infer Windows filenames or layout
from a tag alone. Preserve existing version/channel policy and investigate a
lower upstream version rather than forcing a downgrade.

## 2. Repair version discovery

- Check the actual source URL/repository, tag prefix, JSON path, and regex against
  the fetched response. Make the narrowest change that selects the intended stable
  release and yields the version used by the concrete asset URL.
- Separate Scoop's native `checkver` behavior from this repository's updater.
  The updater supports `checkver.github` and PyPI `checkver.url`; it strips a
  leading `v` before a digit from GitHub tags, ignores a GitHub regex, and reads
  PyPI `info.version` regardless of `jsonpath`. An updater run cannot prove a
  native regex or JSON path works. Test the native matcher against the response;
  if Scoop/PowerShell is unavailable, report that check pending.
- Keep the source compatible with both consumers. If upstream now requires
  unsupported parsing, report the updater limitation and required follow-up;
  do not silently introduce a checkver form the updater skips or expand this
  repair into an unapproved updater redesign.

## 3. Repair downloads and checksums together

Select the actual Windows asset for each declared architecture. Download the exact
URL to a temporary location, inspect its content and archive, and compute SHA-256
from those bytes. Preserve Scoop filename fragments such as `#/tool.zip` in the
manifest, but omit the fragment from the HTTP request. Investigate unexpected
hash changes, redirects, and substituted assets before accepting new bytes; do
not simply copy a checksum from a failed install message.

Update the concrete URL/hash and matching `autoupdate` URL/hash source together.
Expand the template at the repaired version and compare it with the exact asset
URL, including tag prefix, filename, architecture, and fragment. Check every
architecture; do not pair one architecture's URL with another's checksum.
For native `autoupdate.hash` rules, verify the checksum endpoint and extraction
rule against the same asset. This repository's binary updater instead hashes the
download itself and ignores those rules; do not freeze a binary's current digest
as its future hash. Preserve static hashes only for static downloads such as noop.

For supported version bumps or placeholder activation, use:

```sh
python scripts/update_manifests.py <package>
```

Review the family diff: the command also targets `<package>-pipx`. It skips
same-version non-placeholder manifests, so repair same-version URL/hash drift
directly from verified bytes. Do not falsify the version or temporarily zero a
hash to force the updater. Exit zero, a 404 warning, or “No updates available”
does not establish correctness or installability.

For a PyPI shim, keep the noop download separate from package version discovery.
Compare canonical local noop bytes, the generated SHA-256, and the exact raw
repository/ref URL, including static `autoupdate.url` and `autoupdate.hash` in
each affected sibling. Resolve unpublished or divergent remote bytes before
changing the hash; use `scoop-verify`'s noop procedure.

## 4. Repair archive layout and command exposure

List or extract each actual archive without executing its contents. Derive
`extract_dir` from its directory structure, then resolve every `bin` path relative
to that extracted directory. For example, after extracting `dist`, use
`bin/tool.exe` for `dist/bin/tool.exe`, not `dist/bin/tool.exe` again. Preserve
Scoop bin alias/argument arrays; check each executable target, not the alias as
an archive path. Review shortcuts and installer references to moved executables.

Align version-dependent `autoupdate.extract_dir` and `autoupdate.bin` with the
repaired concrete paths at the correct top-level or architecture scope. Avoid
inventing version-dependent filenames without upstream evidence. The updater
uses string `.replace()` for explicit path templates, and only some concrete
string fields receive version-substitution fallback. It cannot safely process
array-valued bin templates or arbitrary Scoop variables. Preserve valid Scoop
arrays and repair their concrete paths manually. If the installed relative bin
path is demonstrably version-independent (for example, `bin/runner.exe` below
`dist/tool-$version`), remove a redundant `autoupdate.bin` rather than retain an
unsupported array template; the concrete alias array can remain unchanged on
future updates while `extract_dir` changes. Review shortcuts too: explicit
shortcut-template processing is nested under the updater's `autoupdate.bin`
branch, so do not assume independent shortcut templates will be applied.
Report genuinely version-dependent arrays or other unsupported future behavior
as a blocker/follow-up instead of claiming automation is repaired.
Check the Windows workflow's `$smoke` map when the executable or CLI syntax changes.

## 5. Handle all-zero hashes

Inspect both top-level and every architecture hash for 64 zeroes, even at nonzero
versions. Replace a placeholder only when the matching real Windows asset exists
and its checksum and layout have been verified. Confirm the assumed seed tag and
URL template as well as the concrete fields. The updater can activate a
same-version placeholder, but a missing asset yields a warning and no write.

If no asset exists, leave the placeholder recognizable and keep the CI install
guard effective. Report activation blocked and Windows installation intentionally
skipped; never fabricate a digest, remove the guard, or label the skip successful.

## 6. Finish with scoop-verify

Invoke `scoop-verify`. Regenerate the README and run its local gate. Require current-head Windows install and smoke evidence for
changed download/hash/layout/command exposure; record it pending if unavailable.

Report the root cause, evidence source, concrete and template repairs per
architecture, native-checkver/updater checks, and verification results. Keep
passed, pending, and skipped separate. Describe remaining upstream/tooling
blockers explicitly, and follow user approval rules for remote actions.


## Resources

This skill bundles supporting files. Read them on demand when the task calls for them — don't bulk-load.

### References

- [`references/repair-cases.md`](references/repair-cases.md) — Repair Evidence and Updater Boundaries
