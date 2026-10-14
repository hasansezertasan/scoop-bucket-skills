---
description: Set up a new Scoop bucket by rendering bucket-template with Copier, then configure repository identity, Actions settings, update credentials and shim noop publication, and hand the first manifest to scoop-add and scoop-verify. Use for new-bucket bootstrap and for template questions about copier copy or update, WORKFLOW_TOKEN versus the unused SCOOP_BUCKET_TOKEN, and why a fresh bucket's shim manifests are not installable yet.
name: scoop-bucket-setup
---

# Set Up a Scoop Bucket from the Template

Read the [template contract](references/contract.md) for the task names and paths
this skill relies on.

## 1. Establish the destination and outcome

Confirm the intended `owner/repository`, visibility, default branch, local
directory, and the first package and its route. Ask through the native question
tool when these are unspecified or disagree; do not invent an owner or a demo
package. Distinguish a setup plan, a local render, and a published installable
bucket. Follow the user's approval rules for creating repositories, changing
settings or secrets, pushing, opening PRs, and running remote workflows.

Read the template's `copier.yml` for the current questions and defaults, and
the rendered bucket's `README.md`, `AGENTS.md`, `.github/workflows/` and
`.config/mise.toml`, instead of relying on this skill's summary of them. The
rendered README may still document the template's own scaffolder command; follow
`scoop-add` for how to run it. Use
[references/setup-cases.md](references/setup-cases.md) for evidence and worked
cases; recheck its locators after the template changes. Do not redesign
workflows, token plumbing or template files as an implicit setup step. Surface
unsupported choices and agree their scope first.

## 2. Render the template

Render into a new directory with Copier; the template is not a GitHub template
repository, so "Use this template" and `gh repo create --template` do not apply.
Provide the answers from step 1 with `-d name=value` so the run is
reproducible, or answer the prompts; `copier.yml` is the source for the
question names and defaults. Pin the template version with `--vcs-ref` when the
user asks for a specific one.

```sh
uvx copier@9.18.2 copy gh:hasansezertasan/bucket-template <directory>
```

Copier renders files only. Creating the GitHub repository, `git init`, the
`origin` remote, the first commit and the push are separate steps that follow
the user's approval rules. Settings, secrets, labels, rulesets, required checks
and installed apps (Renovate, for example) are not rendered; check each
separately.

Commit `.copier-answers.yml`, and never edit it by hand: `copier update` reads
it to merge later template changes. Files the template manages come from it;
change them through `copier update` (or an agreed template change), not by
editing them to diverge. `.gitignore` is Cobo-managed; use Cobo's sync if
`mise run check` reports drift.

Answers only feed the README install snippet and the LICENSE copyright line.
Scripts and workflows read the bucket identity at run time. Check the rendered
`README.md` title and description and `LICENSE` against the agreed identity.
Do not globally replace owner names: external actions and dependencies are not
bucket identity.

The workflows filter on `main`. Confirm the default branch before relying on
that. If a different branch is requested, inspect every branch filter and noop
ref; `--bucket-ref` alone does not adapt CI. Agree any adaptation separately
rather than claiming support.

## 3. Configure Actions and credentials from actual consumers

In **Settings → Actions → General**, verify Actions is enabled and policy allows
the pinned actions used by the rendered workflows. Check organization or
enterprise limits if settings are unavailable. For automation using
`GITHUB_TOKEN`, enable **Allow GitHub Actions to create and approve pull
requests** where permitted. The README asks for read/write defaults, but the
workflows deny permissions at workflow level and grant them per job. Do not
broaden defaults or jobs to troubleshoot; inspect effective job permissions and
repository policy instead.

Explain the distinct credentials before requesting any secret:

| Consumer | Credential and access |
| --- | --- |
| Scheduled/manual and dispatch update PR steps | Optional bucket secret `WORKFLOW_TOKEN`, otherwise built-in `GITHUB_TOKEN`; branch pushes and PR creation need Contents: write and Pull requests: write on the bucket. |
| Upstream GitHub API reads | Workflow `GITHUB_TOKEN`; local helpers accept `GITHUB_TOKEN` or `GH_TOKEN`. These are not shim download credentials. |
| Dispatch failure issue | Built-in `GITHUB_TOKEN` with Issues: write; the destination comes from `github.repository`. |
| PR title and branch-name lint | Built-in `GITHUB_TOKEN` with Pull requests: write. |
| External release producer calling `POST /dispatches` | A credential authorized for the target bucket; a fine-grained token needs Contents: write for this API. Store it in the producer, not the bucket. |

`SCOOP_BUCKET_TOKEN` appears in setup discussions, but no workflow or script
reads it, so creating it alone has no effect. Use the consumer's actual secret
name; do not invent an alias or edit workflows to read it without agreed scope.
`GITHUB_TOKEN` is supplied by Actions, not a secret the user creates.

Choose the credential path from the desired update-PR CI behavior. The README
describes follow-on suppression with `GITHUB_TOKEN`; current GitHub
documentation also describes approval-required runs for some bot-created
`pull_request` events. Inspect the actual banner, events, filters and
latest-head runs instead of assuming automatic CI or universal suppression. For
automatic runs, the update steps accept a suitable PAT or GitHub App token as
`WORKFLOW_TOKEN`. Verify its target access, expiry and renewal, organization
approval and permissions for the operations above. The workflows consume the
secret directly and do not mint or refresh an App installation token; agree
additional plumbing if needed. Job `permissions` do not grant rights to a
supplied token. Do not recommend blanket `repo`, admin or Actions-write
privileges without a specific operation that needs them.

On the built-in-token path, inspect and approve pending runs when available, or
run the existing manual **Tests** workflow on the update branch under the user's
approval rules. A Tests run does not prove the separate title, branch, drift or
audit workflows ran. `WORKFLOW_TOKEN` serves the two update PR steps, not every
bot workflow; inspect Cobo and other automation independently.

Configure secrets through Settings → Secrets and variables → Actions or secure
CLI input. Never print values, ask for them in chat, commit them or embed them
in shell source. Check the `automated` and `dependencies` labels the update PRs
request, and enable Issues if dispatch failure reporting is wanted. Report
policy or ruleset blockers rather than escalating privileges speculatively.

## 4. Prepare the first manifest and its publication

Run `mise install` in the rendered bucket. Invoke `scoop-add` to select and
scaffold the first package with its scaffolder, run against the bucket; do not
hand-write JSON or invent a demo package. `scoop-add` delegates its gate to `scoop-verify`
(curated metadata, hashes and layout, smoke commands, README regeneration, local
checks, exact-head Windows evidence). Keep one package family per PR.

For a PyPI shim, establish the bucket identity **before** scaffolding.
`--bucket-repository` takes precedence over `SCOOP_BUCKET_REPOSITORY`, which
takes precedence over GitHub `origin`. Inspect stale overrides even with a
correct remote. For a downloaded archive or non-GitHub checkout, use the
explicit repository. Ref selection independently follows `--bucket-ref` →
`SCOOP_BUCKET_REF` → `main`; inspect stale ref overrides and reconcile the
effective ref with the agreed publication ref. Do not leave permanent shim URLs
on a temporary setup branch that may be deleted.

The scaffolder hashes local `scripts/noop.ps1` bytes normalized CRLF→LF; it does
not fetch the generated raw URL. Ensure the intended file is published at the
**repository and exact ref**, then have `scoop-verify` compare its response bytes
with the concrete and static `autoupdate` URL and hash values. An uncommitted
noop edit or an unpublished ref produces locally valid but uninstallable
manifests. Keep `.gitattributes` LF behavior. Do not point at the template to
hide a missing destination file, or replace a hash to bless an unexplained
mismatch.

Verify raw download accessibility for the intended installers. The helper's API
token is not sent to raw GitHub, so a private bucket or 404 is not fixed by
adding `WORKFLOW_TOKEN`. Ask about a supported publication or access outcome
when private downloads block shims. CI's working-tree bucket still downloads
remote noop bytes. Keep first-package install evidence pending until that
boundary is verified, and preserve seeded binary install skips until a real
asset and hash exist.

## 5. Report readiness at the requested level

Use the [setup report](references/setup-report.md) as a guide. Report the
destination and default branch, the template version recorded in
`.copier-answers.yml`, checkout and override identity, rendered versus
separately configured items, credential **names and purposes only**, the first
manifest route, publication and noop status, local checks, and latest-head
Windows install and smoke evidence from `scoop-verify`. Include owner-neutral
consumer commands with the established values:

```powershell
scoop bucket add <bucket-name> https://github.com/<owner>/<repository>
scoop install <bucket-name>/<package>
```

Keep `passed`, `pending` and `skipped` distinct. Empty-bucket checks or an
update dry-run do not exercise installability or branch and PR publication. A
scheduled or manual update `dry_run` skips PR creation but can modify runner
files. Schedules and repository dispatch depend on default-branch workflow
publication; check actual runs before claiming automation works. Hand update
failures to `scoop-update-triage` and manifest repair to `scoop-fix-manifest`.
