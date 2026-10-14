---
type: Playbook
title: Scoop Verify
description: 'Decide whether a Scoop bucket change is verified and ready - run the read-only pre-PR readiness gate after adding, updating, repairing, or removing a manifest, and report the verdict with the evidence. Use for readiness verdicts and verification reports: noop URL/hash consistency, smoke commands, placeholder hashes, and whether Windows installation evidence is needed. It never edits manifests; that is scoop-fix-manifest''s job.'
x-ai-rulez:
  kind: skill
  id: scoop-verify
  metadata:
    name: scoop-verify
---

# Verify a Scoop Bucket Change

Read the [template contract](../../references/contract.md) for the task names and paths
this skill relies on.

Use this gate after manifest work, including `scoop-add`, and before reporting a
change ready for review. Read the changed manifests and relevant workflow steps;
the local gate alone does not prove that a package installs on Windows.

## 1. Establish the scope

Inspect the diff against the intended base and identify changed package families,
including `-pipx` siblings, and shared scripts or workflows that affect installs.
Get the bucket identity from `origin` or an explicit repository override; never
copy this template's owner into another bucket. For an empty bucket, report that
there are no packages to install.

Read `references/verification-cases.md` when diagnosing failed verification or
checking noop bytes, archive paths, or placeholder behavior. It distinguishes
actual workflow failures from regression-derived examples.

## 2. Check the manifests

- Validate JSON syntax for affected manifests (for example,
  `python -m json.tool bucket/<package>.json`). Review metadata, dependencies,
  installer/uninstaller behavior, and every architecture. JSON syntax validation
  is not full Scoop schema validation.
- Keep `checkver` and `autoupdate` consistent with the concrete version and
  download URL. For binaries, verify the exact release asset and SHA-256, inspect
  the archive, and check `extract_dir` and `bin` relative to the extracted layout.
  Review version-dependent path templates as well as URL templates.
- Inspect top-level and architecture-specific hashes for 64 zeroes. A seeded
  binary is not installable until its actual asset/hash exists. Confirm the
  `Skip placeholder manifests` guard in `.github/workflows/tests.yml` covers it;
  do not install it or call a skipped CI install successful. Use the hash, not
  version `0.0.0`, to recognize placeholders.

### PyPI shims: verify all three noop values

Read the `scoop-add` skill's `scripts/add_manifest.py` (`noop_source`) and the bucket's `scripts/noop.ps1`. The
scaffolder derives its SHA-256 from local bytes with CRLF normalized to LF;
`.gitattributes` keeps the published file LF. To calculate the expected pair,
run from the bucket root, replacing the skill directory, repository and ref with
the intended values (the scaffolder's default ref is `main`):

```sh
python -c 'import sys; sys.path.insert(0, "<scoop-add skill dir>/scripts"); from add_manifest import noop_source; print(noop_source("<owner>/<repository>", "<ref>"))'
```

Compare the result with each affected shim's concrete `url` and `hash`, including
its `-pipx` sibling. Check static `autoupdate.url` / `autoupdate.hash` too; PyPI
updates should change the version without switching the noop download.
Fetch the manifest's exact raw URL and hash the response bytes: a locally correct
hash cannot prove that the remote repository/ref serves the same file. Preserve
any Scoop filename fragment when reviewing the manifest, but exclude it from the
HTTP request. Report missing/unpublished remote content or mismatched bytes as a
blocker. Do not change the hash just to bless an unexplained remote mismatch.

## 3. Check the Windows smoke command

Inspect the `$smoke` map in `.github/workflows/tests.yml`. The default removes a
trailing `-pipx` from the package name and runs `<command> version`. Confirm the
actual installed executable name and upstream CLI syntax. If either differs,
add a package-keyed override, including a separate `-pipx` key when needed, using
a quick, noninteractive command that exits successfully. Review the workflow's
Scoop, uv, and pipx PATH setup; finding an executable in an archive does not prove
that the installed command is on PATH.

## 4. Run the local gate

```sh
mise install
mise run generate-readme
mise run check
```

Review the generated README diff. `check` runs unit tests, README freshness,
YAML/workflow linting, and any template-managed file drift; it does not
download every manifest or perform a Windows install. Resolve failures according
to their source. For drift in files the template manages (such as `.gitignore`),
use the template's sync process instead of editing them by hand. Re-run the gate
after fixes.

## 5. Decide and record Windows verification

Require a real Windows install and smoke test for a new installable package or
changes to download/hash, archive layout, dependencies, installer/uninstaller,
command exposure, or smoke/PATH logic. The `Tests` workflow can provide this
evidence: its Windows job copies working-tree manifests into a local bucket,
installs the package, and invokes its smoke command. Check results for the exact
head SHA and affected packages; an unrelated run or a skipped job is not evidence.
For a local Windows test, follow those same workflow steps so the working-tree
manifest is exercised rather than an old manifest from the remote bucket.

Metadata-only, removal-only, and skill-only changes normally need the local gate
without a new Windows install. For a seeded placeholder, record the intentional
install skip and require verification once a real release activates it. If
Windows evidence is needed but unavailable, mark it pending and report the change
as locally checked, with installability unverified. Triggering a remote workflow,
pushing, or opening a PR follows the user's approval rules.

## Report

Use the [verification report](references/verification-report.md) as a guide.
Summarize the affected packages, local commands and results, URL/hash/layout and
noop checks, smoke command/overrides, and Windows evidence (run URL/head SHA or
local command results). List blockers and intentional skips explicitly. Keep
`passed`, `pending`, and `skipped` distinct so a maintainer knows what remains.
