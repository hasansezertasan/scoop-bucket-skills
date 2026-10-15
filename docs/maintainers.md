# Operating a Scoop bucket with these skills

The skills assume a bucket made from
[`copier-scoop-bucket`](https://github.com/hasansezertasan/copier-scoop-bucket) and the
layout in the [template contract](../.ai-rulez/references/contract.md). Provide
the bucket checkout and a concrete outcome.

| You want to | Start with |
| --- | --- |
| Set up a new bucket from the template | `scoop-bucket-setup` |
| Add a PyPI shim or a prebuilt Windows binary | `scoop-add` |
| Repair checkver, URLs, hashes, archive paths or commands | `scoop-fix-manifest` |
| Understand a failing scheduled or dispatch update | `scoop-update-triage` |
| Retire a manifest and handle dependents | `scoop-remove-or-deprecate` |
| Decide whether a change is ready for a PR | `scoop-verify` |

Every manifest-changing skill finishes with `scoop-verify`, the read-only
readiness gate. `scoop-update-triage` diagnoses and delegates repairs to
`scoop-fix-manifest`; it does not redesign the updater.

Reports use `passed`, `pending` and `skipped` distinctly. A local gate does
not prove a package installs on Windows; that evidence comes from the bucket's
Windows workflow or a local run of the same steps.

These skills do not change host permissions or authorize outward actions:
pushing, opening a PR, or triggering a remote workflow follows your own
approval rules. Setup renders the template with Copier; creating the repository
and changing its settings or secrets follow the same rules.
