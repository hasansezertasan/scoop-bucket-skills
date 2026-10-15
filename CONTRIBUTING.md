# Contributing

Read [AGENTS.md](AGENTS.md) for source ownership. The
[maintainer guide](docs/maintainers.md) explains how to use the skills; this
file explains how to change and release the plugin itself.

## Development

```sh
mise install
mise run agents:generate
mise run check
```

`mise run agents:generate` reads `.ai-rulez/` and regenerates `AGENTS.md`, root
`skills/`, the Claude and Codex manifests, both catalogs, and
`.ai-rulez-generated.json`. `mise run check` runs the unit tests, reports drift
without repairing it (`ai-rulez generate --check` and `verify --plugin`), and
validates the sources (`validate --strict`). Keep canonical edits and their
generated output in the same commit.

`validate --strict` reports `AR961 plugin-version-drift` while plugin content
differs from `HEAD` and the version has not changed, so `mise run check` fails
locally until the edit and its generated output are committed. CI validates the
committed tree and release-please owns the version, so this is expected.

`mise run agents:eval` is an offline, informational skill-activation ranking
over the eval prompts; it is not a merge gate. Model-based evaluations need
authentication and cost, so keep them out of CI.

## Commit and PR titles

Use `<type>(optional-scope): <description>`; squash-merged titles determine
releases. `feat:` adds functionality and `fix:` repairs behavior. `docs:`,
`test:`, `chore:`, `ci:` and `build:` alone do not normally trigger a release.
Mark a breaking change with `!` or a `BREAKING CHANGE:` footer. Before 1.0,
breaking changes and features bump the minor version and fixes bump the patch.

## Release flow

`pyproject.toml` is the sole version source. It carries no Python package; it
exists because release-please updates it natively and ai-rulez reads it
(`[plugin] version_from`), so no regular expression keeps two copies in sync.

1. On `main`, the `release` workflow runs the same `check` workflow as CI.
2. release-please opens or updates a PR with the version bump and changelog.
   The workflow then regenerates the plugin manifests on that branch, runs the
   checks, and commits any generated change.
3. Review the whole PR, including generated files, and merge it once checks
   pass. The next `release` run validates that exact merge commit and creates
   the `vX.Y.Z` tag and GitHub Release, but only if it is the sole pending
   release (`scripts/release_guard.py`).

The artifact is the tagged repository tree; nothing is published to a registry.

## Repository setup

Enable GitHub Actions and allow Actions to create pull requests. The release
job needs contents, issues and pull-request write permissions; validation
needs contents read. Action revisions are pinned in the workflows. These
settings live on GitHub; adding workflow files does not change them.

`GITHUB_TOKEN` does not start PR workflows for the release PR it creates. To
get a check on the final head, run the `check` workflow on the release branch:

```sh
gh workflow run check.yml --ref release-please--branches--main
```

Use the branch shown on the PR if its name differs. Require `validate` from
`check` in branch protection.

## Recovery

If validation of a release merge fails transiently, rerun that merge's failed
workflow. A new green push or a manual run on a later commit does not authorize
releasing the older pending merge.
