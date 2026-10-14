---
type: Concept
title: Scoop Bucket Skills
x-ai-rulez:
  kind: context
  id: scoop-bucket-skills
---

This repository is a Claude Code plugin (and its marketplace) holding skills
for operating a Scoop bucket made from
[`bucket-template`](https://github.com/hasansezertasan/bucket-template).

#### Agent Instructions

`.ai-rulez/` is the single source for agent instructions and skills.
`AGENTS.md`, root `skills/`, `.claude-plugin/`, `.codex-plugin/`,
`.agents/plugins/marketplace.json`, and `.ai-rulez-generated.json` are
generated from it; edit `.ai-rulez/` and run `mise run agents:generate`, then
commit the generated files. Never hand-edit generated files. Checks report
drift without repairing the checkout. Plugin identity, runtimes and the Codex
interface live in `.ai-rulez/config.toml`; it has no literal version, which
`pyproject.toml` supplies (see `CONTRIBUTING.md`).

#### Invariants

- The skills assume the layout in `.ai-rulez/references/contract.md`. Change a
  task name, path, or workflow filename there and in every skill that cites it,
  together.
- Skills read the bucket's scripts for exact CLI options instead of hardcoding
  flags; keep it that way.
- Skills never edit `.gitignore` or other template-managed files by hand.
- Bucket setup is out of scope until the Copier template exists.
- Maintainer governance stays in `AGENTS.md`, `CONTRIBUTING.md` and `docs/`;
  do not inject it into distributed skills.
- Keep host-loaded paths (`.mcp.json`, `hooks/`, `agents/`, `commands/`) out of
  the repository root: both catalogs install the root, and
  `ai-rulez validate --strict` fails if one appears.
- Scope support claims to saved evidence; see `docs/host-support.md`.

#### Releases

Use Conventional Commit PR titles. release-please owns `CHANGELOG.md`, the
release manifest and the `pyproject.toml` version; the release workflow then
regenerates the plugin manifests on the release PR. Details in
`CONTRIBUTING.md`.

#### Commands

```sh
mise install
mise run check
mise run agents:generate
```
