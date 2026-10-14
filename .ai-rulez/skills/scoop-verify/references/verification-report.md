# Verification report

A guide to the evidence, not a file to create on every run. Keep `passed`,
`pending`, and `skipped` distinct.

- **Verdict:** ready / blocked / locally checked, installability unverified
- **Bucket and revision:** `origin` identity, base, head SHA
- **Affected packages:** manifest names, including `-pipx` siblings

## Checks

| Check | Command or source | Result (`passed` / `failed` / `pending` / `skipped`) |
|---|---|---|
| Noop URL and hash (shims) | | |
| Concrete and `autoupdate` URL/hash pair | | |
| Placeholder hashes | | |
| Archive layout and `bin` | | |
| README regeneration | | |
| Local gate (`mise run check`) | | |

## Windows install evidence

Run URL and head SHA, or the local command and result. State `pending` when
unavailable.

## Blockers and intentional skips

Each with its reason and what would clear it.
