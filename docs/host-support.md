# Host support

The skills are generated into root `skills/` from `.ai-rulez/`. Claude Code
and Codex have catalogs that install the repository root (`./`). OpenCode
does not scan root `skills/`; the root `opencode.json` points it there.

| Host | Packaging | Evidence recorded |
| --- | --- | --- |
| Claude Code | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | `ai-rulez verify --plugin` (hash check of generated files); 2026-10-15, Claude Code 2.1.296, macOS: `claude plugin marketplace add hasansezertasan/scoop-bucket-skills` then `claude plugin install scoop-bucket-skills@scoop-bucket-skills` installed 0.1.0 (user scope, enabled) with all six skills present in the cache. Install only; no skill was invoked |
| Codex | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` | `ai-rulez verify --plugin`; 2026-10-15, codex-cli 0.162.1, macOS: `codex plugin marketplace add <checkout>` then `codex plugin add scoop-bucket-skills@scoop-bucket-skills` installed 0.1.0 (enabled) with all six skills present in the cache. Install only; no skill was invoked |
| OpenCode | `opencode.json` (`skills.paths`) | Not evaluated |
| pi | none declared (no pi package or path configured) | Not evaluated |
| Other agents | `AGENTS.md` | Not evaluated |

Structural validation and completed model turns do not establish task success
by themselves. Add a row's evidence only after recording it (command, host
version, date). Authenticated model evaluations stay out of ordinary CI.

## Install

```sh
/plugin marketplace add hasansezertasan/scoop-bucket-skills
/plugin install scoop-bucket-skills@scoop-bucket-skills
```

For Codex, from a checkout:

```sh
codex plugin marketplace add /absolute/path/to/scoop-bucket-skills
codex plugin add scoop-bucket-skills@scoop-bucket-skills
```
