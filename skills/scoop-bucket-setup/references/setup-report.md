# Setup report

A guide to the evidence, not a file to create on every run. Keep `passed`,
`pending`, and `skipped` distinct. Never record secret values.

- **Outcome level:** plan / rendered locally / repository configured / first package published
- **Destination:** `owner/repository`, visibility, default branch
- **Template:** source and version from `.copier-answers.yml`
- **Checkout identity:** `origin`, and any `SCOOP_BUCKET_REPOSITORY` / `SCOOP_BUCKET_REF` overrides

## Rendered versus configured separately

| Item | Where it lives | Result (`passed` / `failed` / `pending` / `skipped`) |
|---|---|---|
| Files rendered, `.copier-answers.yml` committed | checkout | |
| README title, description and LICENSE identity | rendered files | |
| Actions enabled, PR creation allowed | repository settings | |
| Update credential (`WORKFLOW_TOKEN` or built-in) | secret name and purpose only | |
| Labels `automated` and `dependencies`, Issues if wanted | repository settings | |
| Renovate or other installed apps | repository settings | |
| Required checks and rulesets | repository settings | |

## First manifest

Route, package family, noop publication (repository and ref), and the
`scoop-verify` verdict with its head SHA. State `pending` when Windows install
evidence is unavailable.

## Blockers and intentional skips

Each with its reason and what would clear it.
