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
| Update the scoop-bucket-skills skills | The agent runs the update command for the route it installed with (see the table below), then confirms the new version and tells you to start a new session. |
| Pull the latest template changes into this bucket | The agent runs `uvx copier update` in the bucket, reviews the diff and resolves conflicts with you. |

## For agents reading this page

You were pointed here to install the skills. Do this:

1. Pick the route in the table below that you can run yourself on your platform.
   Prefer a route native to your platform over a manual clone.
2. If a route needs a slash command or an interactive step you cannot run, give the
   user the exact command and ask them to run it. Do not guess at another command.
3. Confirm the install with the route's confirm step in the table.
4. Plugin and skills installs usually load in a new session, not in the
   conversation that installed them. If the skills are not available to you now,
   read `skills/scoop-bucket-setup/SKILL.md` from a clone of this repository (a
   temporary clone is fine) and follow it, and tell the user to start a new
   session so the installed skills load next time.
5. If a route fails, fall back to the manual route. Do not report the install as
   done until you have confirmed the skills or read `scoop-bucket-setup/SKILL.md`.
6. Then continue with what the user asked. Ask before you create a repository,
   change repository settings or secrets, or push. Do not install other agent
   skills or switch to a different route unless this one fails. The setup skill
   itself runs `uvx` (for Copier) and `mise` as it documents; that is expected.

### Routes

| Route | Install | Update | Confirm |
| --- | --- | --- | --- |
| Claude Code plugin | `claude plugin marketplace add hasansezertasan/scoop-bucket-skills`, then `claude plugin install scoop-bucket-skills@scoop-bucket-skills` (in a session: `/plugin marketplace add …` and `/plugin install …`) | `claude plugin marketplace update scoop-bucket-skills`, then `claude plugin update scoop-bucket-skills@scoop-bucket-skills` | `claude plugin list` shows the plugin and its version; run `/reload-plugins` or start a new session to load it |
| Codex plugin | clone this repository, then `codex plugin marketplace add /absolute/path/to/scoop-bucket-skills` and `codex plugin add scoop-bucket-skills@scoop-bucket-skills`; start a new thread | pull the clone, then `codex plugin marketplace upgrade scoop-bucket-skills` (documented in a third-party guide, not in OpenAI's docs; check your Codex version) and start a new thread | the plugin appears in Codex's plugin list in a new thread |
| A skills installer | `npx skills add hasansezertasan/scoop-bucket-skills` ([vercel-labs/skills](https://github.com/vercel-labs/skills)) | `npx skills update scoop-bucket-skills` | `npx skills list` shows the skills |
| Manual | clone this repository and read `skills/<name>/SKILL.md`, or copy `skills/*` into your agent's skills directory | `git pull` in the clone, then copy `skills/*` again if you copied them | `git rev-parse HEAD` matches the latest commit on `main` |

To compare an installed version with the latest, use the version in
`.claude-plugin/plugin.json` or the repository's latest GitHub release.

None of these routes has a recorded successful installation yet: see
[host support](host-support.md) for the evidence per host. Treat them as
unverified packaging guidance, and tell the user which route you used, whether
you confirmed the skills afterwards, and whether a new session is needed.

The skills assume a bucket made from
[`copier-scoop-bucket`](https://github.com/hasansezertasan/copier-scoop-bucket)
and the layout in the [template contract](../.ai-rulez/references/contract.md).
