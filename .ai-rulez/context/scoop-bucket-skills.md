---
type: Concept
title: Scoop Bucket Skills
x-ai-rulez:
  kind: context
  id: scoop-bucket-skills
---

This repository is a skills repository (root `skills/`) that also installs as a
Claude Code or Codex plugin, and is its own marketplace. It holds skills for
operating a Scoop bucket made from
[`copier-scoop-bucket`](https://github.com/hasansezertasan/copier-scoop-bucket).

#### Agent Instructions

`.ai-rulez/` is the single source for agent instructions and skills.
`AGENTS.md`, root `skills/`, `.claude-plugin/`, `.codex-plugin/`,
`.agents/plugins/marketplace.json`, and `.ai-rulez-generated.json` are
generated from it; edit `.ai-rulez/` and run `mise run agents:generate`, then
commit the generated files. Never hand-edit generated files. Checks report
drift without repairing the checkout. Plugin identity, runtimes and the Codex
interface live in `.ai-rulez/config.toml`; it has no literal version, which
`package.json` supplies (see `CONTRIBUTING.md`).

#### Invariants

- The skills assume the layout in `.ai-rulez/references/contract.md`. Change a
  task name, path, or workflow filename there and in every skill that cites it,
  together.
- Skills read the bucket's scripts for exact CLI options instead of hardcoding
  flags; keep it that way.
- Skills never edit `.gitignore` or other template-managed files by hand.
- Bucket setup renders the Copier template (`scoop-bucket-setup`); it never
  hand-writes template-managed files.
- Maintainer governance stays in `AGENTS.md`, `CONTRIBUTING.md` and `docs/`;
  do not inject it into distributed skills.
- Keep host-loaded paths (`.mcp.json`, `hooks/`, `agents/`, `commands/`) out of
  the repository root: both catalogs install the root, and
  `ai-rulez validate --strict` fails if one appears.
- Scope support claims to saved evidence; see `docs/host-support.md`.

#### Releases

Use Conventional Commit PR titles. release-please owns `CHANGELOG.md`, the
release manifest and the `package.json` version, and bumps the generated plugin
manifests alongside it. Details in `CONTRIBUTING.md`.

#### Commands

```sh
mise install
mise run check
mise run agents:generate
```
