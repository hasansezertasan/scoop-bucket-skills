# 0001: Adopt ghost-library-skills practices

Status: accepted. Date: 2026-10-14.

[`ghost-library-skills`](https://github.com/hasansezertasan/ghost-library-skills)
is the reference for how this plugin is packaged, released and evaluated. This
record keeps the reasons; it is not updated as the project evolves.

## Decision

- **Generate packaging with ai-rulez `[plugin]`.** Skills ship from root
  `skills/` with generated Claude and Codex manifests and catalogs, replacing
  hand-written manifests, per-agent skill trees and the render-and-promote
  wrapper script. A single `[plugin] shared_resources` copy makes the
  [contract](../../.ai-rulez/references/contract.md) available to each skill
  installed alone. Skill triage and verification reports are guides under each
  skill's `references/`.
- **One version source, native updater.** `pyproject.toml` carries the version
  because release-please and ai-rulez both read it natively. ai-rulez accepts
  only `Cargo.toml`, `package.json` or `pyproject.toml`, so a bare version file
  was not an option, and a custom regex manager was ruled out.
- **Release-please with a validated-merge guard.** The release workflow runs
  the reusable `check` workflow, regenerates manifests on the release PR, and
  creates a release only for the sole pending merge at the validated SHA.
- **Unfiltered reusable CI.** Path-filtered required checks never report on a
  skipped PR, and nearly every file here is Markdown or JSON.
- **Eval cases per skill.** Each skill carries desk-exercise cases with
  rubrics; the activation ranking is informational and model runs stay out of CI.

## Not adopted

- Their npm and Pi packaging, saved evaluation result archives and automation
  research documents: they serve a larger project and Pi support.
- `local>hasansezertasan/renovate-config`: not verified to suit this
  repository, so Renovate stays on `config:recommended`.

## Consequences

- The plugin path changed from `.claude/skills/` to root `skills/`.
- The required status check name changed from "Agent files are up to date" to
  `validate`; update branch protection.
