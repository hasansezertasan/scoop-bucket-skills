# 0002: Adopt the copier-skills template

Status: accepted. Date: 2026-10-16.

This repo's scaffold now comes from the
[`copier-skills`](https://github.com/hasansezertasan/copier-skills) template and
is updated with `copier update`. The skills, `README.md` and `CHANGELOG.md` were
not touched. This record lists what still differs from a plain render and why;
it is not updated as the project evolves.

## Replaced by the template's version

- **Version source.** `pyproject.toml` carried the version only because
  release-please updated it natively. `package.json` now does, with the
  release manifest at the repo root (`0.1.0`, the released version) and the
  plugin manifests bumped by release-please `extra-files`. `scripts/release_guard.py`
  and its test were replaced by the template's `release-merge.mjs` and
  `release-guard.mjs`, which implement the same sole-pending-release rule and
  add a version-drift check. The workflow that regenerated manifests on the
  release PR branch is no longer needed.
- **CI and release workflows, Renovate config, `.node-version`,
  `scripts/check-repo.mjs`.** Taken as rendered.

## Differences kept on purpose

- **`publish_to_npm: false`.** The package is `"private": true` and nothing is
  published to a registry, as before. Turning it on later needs the npm
  bootstrap and trusted publisher in `CONTRIBUTING.md`.
- **`.ai-rulez/config.toml`.** Scoop's custom `AGENTS.md` preset, the AR401 and
  AR402 opt-outs (the skills cite files of the bucket they operate on),
  `shared_resources = ["references"]` and the plugin text stay. Only
  `version_from` changed to `package.json`.
- **Python unit tests.** `npm test` runs `tests/` and `check.yml` has one extra
  step for it; the template ships no tests.
- **mise.** `.config/mise.toml` keeps the Renovate-tracked Copier pin (kept
  equal to the one in `scoop-bucket-setup` by `tests/test_copier_pin.py`) and
  thin tasks (`check`, `test`, `agents:generate`, `agents:eval`) over the npm
  scripts, so the commands in `README.md`, `AGENTS.md` and `CONTRIBUTING.md`
  still work. The ai-rulez pin moved to `package.json`.
- **`CONTRIBUTING.md` and `docs/installation.md`.** The template's versions plus
  scoop-specific sections (development notes, the skill table, the install
  prompt, the skills-installer route, host-support links). These are
  template-owned files, so future template changes merge into them.
- **`.gitignore`.** The template's `node_modules/` plus `__pycache__/` and
  `.ai-rulez/.generated-manifest.local.json`.
- **`.copier-answers.yml` keeps `placeholder_skill: hello`.** The placeholder
  skill is not present here; Copier leaves a deleted file deleted unless the
  template changes it.
