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

The skills assume the layout in the
[template contract](.ai-rulez/references/contract.md). Other agents can read
`skills/<name>/SKILL.md`; see [host support](docs/host-support.md).

## Development

Skills are authored in `.ai-rulez/`; root `skills/`, the plugin manifests and
`AGENTS.md` are generated and committed. See [CONTRIBUTING.md](CONTRIBUTING.md).

```sh
mise install
mise run agents:generate
mise run check
```
