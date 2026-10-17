# Contributing to Scoop Bucket Skills

Read [AGENTS.md](AGENTS.md) for source ownership. The
[maintainer guide](docs/maintainers.md) explains how to use the skills; this
file explains how to change and release the plugin itself.

This file is owned by the [copier-skill-repo](https://github.com/hasansezertasan/copier-skill-repo) template and is merged on `copier update`. Put repo-specific guidance in `README.md`, which the template never overwrites.

## How the repo works

- Skills live under `.ai-rulez/skills/<name>/`. That directory is the source of truth.
- `skills/`, `AGENTS.md` and the plugin and marketplace manifests are generated output. Never edit them by hand.
- After changing anything under `.ai-rulez/`, run `npm run generate` and commit the result.
- `npm run check` is what CI runs. It fails when generated output has drifted.
- Node comes from `.node-version`.

### Scoop Bucket Skills specifics

`npm run generate` reads `.ai-rulez/` and regenerates `AGENTS.md`, root
`skills/`, the Claude and Codex manifests, both catalogs and
`.ai-rulez-generated.json`. `npm test` runs the Python unit tests in `tests/` (`python` on your PATH),
which the template does not ship. Keep canonical edits and their generated
output in the same commit.

`validate --strict` reports `AR961 plugin-version-drift` while plugin content
differs from `HEAD` and the version has not changed, so `npm run check` fails
locally until the edit and its generated output are committed. CI validates the
committed tree and release-please owns the version, so this is expected.

`npm run eval` is an offline, informational skill-activation ranking
over the eval prompts; it is not a merge gate. Model-based evaluations need
authentication and cost, so keep them out of CI.

## Skill layout

The template owns the scaffold, not a skill's content. A skill is a directory:

```text
.ai-rulez/skills/<name>/
├── SKILL.md       required
├── references/    optional: files the skill loads on demand
├── evals/         optional: test prompts and expected outcomes
└── scripts/       optional: helpers the skill runs
```

Only `SKILL.md` is required. The other directories are a convention the template describes and never creates, checks or overwrites.

## Commits and pull requests

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/): `<type>[(scope)][!]: <description>`.
- Pull request titles use the same format, because release-please builds the changelog and picks the next version from them.
- `feat` bumps the minor version, `fix` the patch. A `!` or a `BREAKING CHANGE:` footer marks a breaking change.
- Branch names are `<type>/<description>`, lowercase and hyphenated (`feature`, `bugfix`, `hotfix`, `release`, `chore`).

## Release flow

`package.json` is the sole version source. release-please bumps it, and bumps the generated plugin manifests alongside it, so no copy of the version is kept in sync by hand. The first release is 0.1.0. Before 1.0, a breaking change or a `feat` bumps the minor version and a `fix` bumps the patch.

1. On `main`, the `release` workflow runs the same `check` workflow as CI, then `scripts/release-guard.mjs`, which stops the release when the versions disagree.
2. release-please opens or updates a release PR with the version bump and the changelog. The workflow then regenerates the plugin output on that branch, because release-please cannot update the hash ledger `.ai-rulez-generated.json`: a read-only job runs `npm run generate` and `npm run check` and hands over a patch, and a separate job holding the write token applies it after checking that it touches only generated paths.
3. Review the whole PR, generated files included, and merge it once its checks pass.
4. The next `release` run creates the `vX.Y.Z` tag and GitHub Release for that merge, but only if it is the sole pending release (`scripts/release-merge.mjs`).

The artifact is the tagged repository tree; nothing is published to a registry.

## One-time repository setup

None of these settings can be read from the repository, so CI cannot catch a missing one. Do them once after creating the repo on GitHub.

- [ ] **Allow Actions to open pull requests.** Settings → Actions → General → Workflow permissions → tick "Allow GitHub Actions to create and approve pull requests". Without it release-please cannot open its release PR.
- [ ] **Protect `main`.** Settings → Rules (or Branches) → require a pull request and require the `check` status check to pass before merging.
- [ ] **Close and reopen the release PR before merging it.** release-please runs on the implicit `GITHUB_TOKEN`, and events created with that token start no workflow runs. The release PR therefore reports no required checks until you close and reopen it (`check.yml` runs on `reopened`). Every later update release-please pushes to that PR has the same problem, so reopen it again after each update, or at least once more on the final head right before merging. Instead of reopening, you can run the check on the release branch, which reports on the head commit: `gh workflow run check.yml --ref release-please--branches--main` (use the branch shown on the PR if its name differs).

`publish_to_npm` is off, so `package.json` is `"private": true` and no npm setup is needed. Pi users install from git.

## Recovery

If validation of a release merge fails transiently, rerun that merge's failed workflow. A new green push, or a manual run on a later commit, does not authorize releasing the older pending merge: `scripts/release-merge.mjs` allows a release only for the one pending release PR that merged as the commit being released.
