# scoop-bucket-skills

Agent skills for operating a Scoop bucket: set one up, then add, fix, triage,
remove and verify manifests. This is a skills repository (`skills/<name>/SKILL.md`)
that also installs as a Claude Code or Codex plugin.

| Skill | Use |
|---|---|
| `scoop-bucket-setup` | set up a new bucket from the copier-scoop-bucket template |
| `scoop-add` | add a PyPI shim or prebuilt Windows binary manifest |
| `scoop-fix-manifest` | repair version discovery, hash drift, archive paths, command exposure |
| `scoop-update-triage` | diagnose failing scheduled or dispatch updates |
| `scoop-remove-or-deprecate` | retire manifests and handle dependents |
| `scoop-verify` | read-only pre-PR readiness gate |

Install in Claude Code:

```sh
/plugin marketplace add hasansezertasan/scoop-bucket-skills
/plugin install scoop-bucket-skills@scoop-bucket-skills
```

Install in Codex, from a checkout:

```sh
codex plugin marketplace add /absolute/path/to/scoop-bucket-skills
codex plugin add scoop-bucket-skills@scoop-bucket-skills
```

Other agents can read `skills/<name>/SKILL.md`; see
[host support](docs/host-support.md) for what has been verified per host. The
skills assume the layout in the
[template contract](.ai-rulez/references/contract.md).

## Development

Skills are authored in `.ai-rulez/`; root `skills/`, the plugin manifests and
`AGENTS.md` are generated and committed. See [CONTRIBUTING.md](CONTRIBUTING.md).

```sh
mise install
mise run agents:generate
mise run check
```
