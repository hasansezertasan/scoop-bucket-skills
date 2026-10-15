# Bucket Setup Evidence and Cases

## Provenance

Inspected `copier-scoop-bucket` (named `bucket-template` until 2026-10-15) at
`fcc017c` (2026-10-15). That revision includes the
Copier conversion (`638b51a`, PR 27), the move of the manifest scaffolder out to
the `scoop-add` skill (`7a069ee`, PR 28) and the read-only default-permissions
guidance (`fcc017c`, PR 30). Every locator below was rechecked at it. A render of
`638b51a` still ships the scaffolder scripts and the `add-manifest` mise task, and
renders before PR 30 still ask for read/write default permissions; later renders
do neither. Locators are paths in that repository; files under `template/` land
at the same path without the prefix in a rendered bucket. `bucket/` and
`deprecated/` contain only `.gitkeep`, and the template has no tagged release
yet. The cases are synthetic desk scenarios grounded in the
implementation, not observed failed installations or Windows runtime tests.

Read the existing verification, repair, triage and lifecycle references for their
separate evidence boundaries. A recorded Cobo drift failure is a managed
boilerplate failure, not proof of a template, token or shim incident.

## Local evidence map

| Evidence | Locator |
| --- | --- |
| Questions, defaults, template root, post-copy message | `copier.yml` |
| Rendered answers record used by `copier update` | `template/.copier-answers.yml.jinja` |
| What the rendered setup checklist says (read-only default permissions, PR-creation setting, scaffolder pointer) | `template/README.md.jinja`, Setup / Install packages / Add a manifest / Automated updates |
| Token names, producer versus bucket responsibilities | `template/README.md.jinja`, Automated updates; `template/.github/workflows/update-manifests.yml`, `update` job; `update-manifest-dispatch.yml`, Create Pull Request / Report failure |
| CLI → environment → remote precedence | the `scoop-add` skill's `scripts/add_manifest.py` (shim CLI and `main`) and `scripts/bucket_repository.py` (`resolve` / `from_remote`); `tests/test_bucket_repository.py`. Renders from PR 28 (`7a069ee`) onward no longer ship a copy; only `template/scripts/url_fetch.py` remains, for the update workflows |
| Local LF-normalized hash and raw repository/ref URL | the `scoop-add` skill's `scripts/add_manifest.py`, `noop_source`; `template/.gitattributes`; `tests/test_add_manifest.py` |
| API-only authorization and redirect stripping | the `scoop-add` skill's `scripts/url_fetch.py`; `tests/test_url_fetch.py` |
| First-manifest scaffolder and verification ownership | the `scoop-add` and `scoop-verify` skills |
| Local check coverage | `template/.config/mise.toml`, `check` |
| Install working-tree manifests, skip zero hashes, smoke command | `template/.github/workflows/tests.yml`, `discover` and `test` jobs |
| Branch filters and default-ref assumptions | `template/.github/workflows/tests.yml`, `readme.yml`; shim `--bucket-ref` default |
| PR title and branch-name lint, Pull requests: write | `template/.github/workflows/check-pr-title.yml`, `check-branch-name.yml` |
| Cobo PR token boundary | `template/.github/workflows/gitignore-drift.yml`; no `WORKFLOW_TOKEN` input |
| Template renders and its own gate passes | `.github/workflows/template.yml` |

Recheck code rather than treating comments as authoritative: dispatch comments
describe wildcard family selection, but the updater selects the exact token and
its `-pipx` sibling. No `SCOOP_BUCKET_TOKEN` consumer exists at this commit. All
workflows deny permissions by default and each job opts in. Update PR jobs need
Contents and Pull requests write, dispatch failure reporting needs Issues write,
the title and branch lints need Pull requests write, and zizmor declares
Security events write. Do not generalize update-token permissions to every
workflow.

## External documentation checked

Checked 2026-10-15; recheck current docs and destination policy during setup.

- [Copier](https://copier.readthedocs.io): `copier copy` renders files and
  records answers in `.copier-answers.yml`; `copier update` merges later template
  changes using that file.
- [Actions repository settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository):
  Actions enabled by default but controllable by policy, allowed actions, default
  token permissions versus explicit YAML permissions, and the separate GitHub
  Actions PR-creation setting (disabled by default in new personal repos).
- [Token authentication](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token):
  built-in token, job permissions, PAT and App alternatives.
- [Workflow triggering](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow):
  `GITHUB_TOKEN` suppression has exceptions. Current docs describe
  approval-required `pull_request` opened/synchronize/reopened runs; other events
  remain suppressed except workflow and repository dispatch. This is more nuanced
  than the README's summary; inspect actual runs and do not promise all gates run
  automatically.
- [Events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows):
  default-branch constraints for schedules, repository dispatch and manual
  workflows.
- [Repository dispatch API](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event):
  dispatch is a producer signal, not PR creation; the README documents Contents:
  write for a fine-grained producer token.
- [Scoop buckets documentation](https://github.com/ScoopInstaller/Scoop/wiki/Buckets):
  custom Git bucket registration and consumer install checks. Its description of
  ScoopInstaller's different template is not this template's automation.

## Synthetic evaluation cases

### A. Unspecified team destination and first package

Ask for owner and repository, visibility, default branch, the first upstream and
route, and whether the goal is a plan or published readiness. Render with
`copier copy`, not "Use this template". Distinguish rendered files from
Actions, secrets, apps and policy configuration. Keep identity neutral and use
`scoop-add` → `scoop-verify`; do not create a fictional manifest.

### B. Correct origin, stale override, unpublished noop

Honor CLI, environment and remote precedence rather than trusting `origin`
alone. Check ref precedence separately (`--bucket-ref` → `SCOOP_BUCKET_REF` →
`main`); matching bytes on a temporary branch do not make it a durable
publication ref. Scaffolding success does not verify remote content. A raw 404
and uncommitted noop changes block installability until the intended identity
and ref publish matching LF bytes and static `autoupdate` values agree. Do not
reuse the template's raw URL, change a hash blindly, or claim a local CI bucket
bypasses remote shim downloads.

### C. Wrong secret and empty-bucket automation check

Explain the unused `SCOOP_BUCKET_TOKEN` name versus the `WORKFLOW_TOKEN`
fallback, effective permissions, the PR-creation setting, and suppression or
approval-required CI. Distinguish a producer's dispatch credential from the
bucket's branch, PR and failure-issue credentials. Empty checks and dry-runs do
not prove publishing, the separate gates, or Windows installs. Never expose
secrets or recommend blanket privileges to mask missing evidence.

### D. Edited template-managed file, then `copier update`

A bucket owner hand-edited a workflow the template manages and later wants
template fixes. Read `.copier-answers.yml` for the recorded source and version,
run `copier update` (with the user's approval for the working tree) and resolve
conflicts deliberately; do not recommend deleting the answers file or re-running
`copier copy` over the checkout. For `.gitignore`, resolve drift with Cobo's sync
rather than by hand.
