# scoop-bucket-skills

Claude Code plugin with skills for operating a Scoop bucket.

| Skill | Use |
|---|---|
| `scoop-add` | add a PyPI shim or prebuilt Windows binary manifest |
| `scoop-fix-manifest` | repair version discovery, hash drift, archive paths, command exposure |
| `scoop-update-triage` | diagnose failing scheduled or dispatch updates |
| `scoop-remove-or-deprecate` | retire manifests and handle dependents |
| `scoop-verify` | read-only pre-PR readiness gate |

Install:

```sh
/plugin marketplace add hasansezertasan/scoop-bucket-skills
/plugin install scoop-bucket-skills@scoop-bucket-skills
```

The skills assume the layout in [CONTRACT.md](CONTRACT.md).
Other agents can read `.agents/skills/<name>/SKILL.md`.

## Development

Skills are authored in `.ai-rulez/`; `.claude/skills/`, `.agents/skills/` and
`AGENTS.md` are generated and committed.

```sh
mise install
mise run agents:generate
mise run check
```
