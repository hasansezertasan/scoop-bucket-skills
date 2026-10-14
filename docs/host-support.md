# Host support

Five skills are generated into root `skills/` from `.ai-rulez/`. Claude Code
and Codex have catalogs that install the repository root (`./`). OpenCode
does not scan root `skills/`; the root `opencode.json` points it there.

| Host | Packaging | Evidence recorded |
| --- | --- | --- |
| Claude Code | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | `ai-rulez verify --plugin` (hash check of generated files); installation not yet recorded |
| Codex | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` | `ai-rulez verify --plugin`; installation not yet recorded |
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
