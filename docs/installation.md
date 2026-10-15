# Installation

Your agent is the interface. Install the skills once, then ask your agent to set
up and operate a Scoop bucket; you do not run the individual commands yourself.

Copy this prompt into your coding agent:

```text
Install the scoop-bucket-skills skills: pick the best installation method for
you from https://github.com/hasansezertasan/scoop-bucket-skills/blob/main/docs/installation.md

Then use its scoop-bucket-setup skill to set up a new Scoop bucket from
https://github.com/hasansezertasan/copier-scoop-bucket. Ask me for what you need
(my GitHub owner, the bucket's purpose and the first package), and ask before
you create a repository, change settings or secrets, or push.
```

The prompt points at this page, not at a command, so the routes below can change
without the prompt changing.

## Then use it

Each request below starts a skill. Say what you want in your own words.

| Ask your agent to | Skill |
| --- | --- |
| Set up a new bucket from the template | `scoop-bucket-setup` |
| Add a PyPI shim or a prebuilt Windows binary | `scoop-add` |
| Repair checkver, URLs, hashes, archive paths or commands | `scoop-fix-manifest` |
| Explain a failing scheduled or dispatch update | `scoop-update-triage` |
| Retire a manifest and handle dependents | `scoop-remove-or-deprecate` |
| Check a change is ready for a PR | `scoop-verify` |

## Keep it current

| Ask your agent to | What happens |
| --- | --- |
| Update the scoop-bucket-skills skills | The agent repeats the route it installed with and checks the repository's latest release. |
| Pull the latest template changes into this bucket | The agent runs `uvx copier update` in the bucket, reviews the diff and resolves conflicts with you. |

## For agents reading this page

You were pointed here to install the skills. Do this:

1. Pick the route in the table below that you can run yourself on your platform.
   Prefer a route native to your platform over a manual clone.
2. If a route needs a slash command or an interactive step you cannot run, give the
   user the exact command and ask them to run it. Do not guess at another command.
3. Confirm the install: check that these skills are now available to you:
   `scoop-bucket-setup`, `scoop-add`, `scoop-verify`, `scoop-fix-manifest`,
   `scoop-update-triage`, `scoop-remove-or-deprecate`.
4. If a route fails, fall back to the manual route. Do not report the install as
   done until you have read at least `skills/scoop-bucket-setup/SKILL.md`.
5. Then continue with what the user asked. Ask before you create a repository,
   change repository settings or secrets, or push. Do not install anything else.

| Route | Commands |
| --- | --- |
| Claude Code plugin | `/plugin marketplace add hasansezertasan/scoop-bucket-skills`, then `/plugin install scoop-bucket-skills@scoop-bucket-skills` |
| Codex plugin | clone this repository, then `codex plugin marketplace add /absolute/path/to/scoop-bucket-skills` and `codex plugin add scoop-bucket-skills@scoop-bucket-skills` |
| A skills installer | for example `npx skills add hasansezertasan/scoop-bucket-skills` ([vercel-labs/skills](https://github.com/vercel-labs/skills)), which finds `skills/<name>/SKILL.md` |
| Manual | clone this repository and read `skills/<name>/SKILL.md`, or copy `skills/*` into your agent's skills directory |

None of these routes has a recorded successful installation yet: see
[host support](host-support.md) for the evidence per host. Treat them as
unverified packaging guidance, and tell the user which route you used and whether
you confirmed the skills afterwards.

The skills assume a bucket made from
[`copier-scoop-bucket`](https://github.com/hasansezertasan/copier-scoop-bucket)
and the layout in the [template contract](../.ai-rulez/references/contract.md).
