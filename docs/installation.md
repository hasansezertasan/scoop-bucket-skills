# Installation

Scoop Bucket Skills publishes the same skills to five runtimes: Claude Code, Codex, OpenCode, Pi and Antigravity. The skills are generated into `skills/` and the plugin manifests at the repository root.

Your agent can do the install. Copy this prompt into your coding agent:

```text
Install the scoop-bucket-skills skills: pick the best installation method for
you from https://github.com/hasansezertasan/scoop-bucket-skills/blob/main/docs/installation.md

Then use its scoop-bucket-setup skill to set up a new Scoop bucket from
https://github.com/hasansezertasan/copier-scoop-bucket. Ask me for what you need
(my GitHub owner, the bucket's purpose and the first package), and ask before
you create a repository, change settings or secrets, or push.
```

The prompt points at this page, not at a command, so the routes below can change without the prompt changing.

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

1. Pick the route in the table below that you can run yourself on your platform. Prefer a route native to your runtime over a manual clone.
2. If a route needs a slash command or an interactive step you cannot run, give the user the exact command and ask them to run it. Do not guess at another command.
3. Confirm the install with the route's confirm step.
4. Plugin and skills installs usually load in a new session, not in the conversation that installed them. If the skills are not available to you now, read `skills/<name>/SKILL.md` from a clone of this repository (a temporary clone is fine) and tell the user to start a new session so the installed skills load next time.
5. If a route fails, fall back to the manual route. Do not report the install as done until you have confirmed the skills or read a `SKILL.md`.
6. Do not install other agent skills or switch to a different route unless this one fails.

## Routes

| Runtime | Install | Update | Confirm |
| --- | --- | --- | --- |
| Claude Code | `claude plugin marketplace add hasansezertasan/scoop-bucket-skills`, then `claude plugin install scoop-bucket-skills@scoop-bucket-skills` (in a session: `/plugin marketplace add hasansezertasan/scoop-bucket-skills` and `/plugin install scoop-bucket-skills@scoop-bucket-skills`) | `claude plugin marketplace update scoop-bucket-skills`, then `claude plugin update scoop-bucket-skills@scoop-bucket-skills` | `claude plugin list` shows the plugin and its version; run `/reload-plugins` or start a new session to load it |
| Codex | clone this repository, then `codex plugin marketplace add /absolute/path/to/scoop-bucket-skills` and `codex plugin add scoop-bucket-skills@scoop-bucket-skills`; start a new thread | pull the clone, then `codex plugin add scoop-bucket-skills@scoop-bucket-skills` again, and start a new thread (`marketplace upgrade` applies to Git marketplaces, not a local path; this update route has not been verified) | the plugin appears in Codex's plugin list in a new thread |
| OpenCode | git only; see [OpenCode](#opencode) | `git pull` in the clone | the skills are offered by OpenCode's `skill` tool in a new session |
| Pi | `pi install git:github.com/hasansezertasan/scoop-bucket-skills` (not published to npm) | `pi update git:github.com/hasansezertasan/scoop-bucket-skills` (a bare `pi update` updates Pi itself), then restart Pi or reload resources | invoke one of the skills with `/skill:<name>` |
| A skills installer | `npx skills add hasansezertasan/scoop-bucket-skills -g` ([vercel-labs/skills](https://github.com/vercel-labs/skills); `-g` installs for the user so the skills are there in any project, add `-a <your agent>` to target one agent) | `npx skills update -g` (it filters by installed skill names, which are `scoop-add`, `scoop-bucket-setup` and the other skills here, not the repository name, so run it without names to update all) | `npx skills list -g` shows the six skills |
| Antigravity | git only; see [Antigravity](#antigravity) | reinstall with the same command, then restart | `agy plugin list` shows the plugin as installed and enabled; restart Antigravity to load it |
| Manual | clone this repository and read `skills/<name>/SKILL.md`, or copy `skills/*` into your agent's skills directory | `git pull` in the clone, then copy `skills/*` again if you copied them | the clone's `git rev-parse HEAD` matches the latest commit on `main`; if you copied the skills, `for d in <clone>/skills/*/; do diff -r "$d" "<destination>/$(basename "$d")"; done` prints nothing (compare skill by skill: the destination may hold skills from other sources) |

The Pi package declares the `pi-package` keyword and a `pi.skills` entry pointing at `./skills` in `package.json`. To compare an installed version with the latest, use the version in
`.claude-plugin/plugin.json` or the repository's latest GitHub release.

The Claude Code and Codex plugin routes each have one recorded installation
on macOS; the skills installer route has none: see
[host support](host-support.md) for the evidence per host. Treat the installer
route as unverified packaging guidance, and tell the user which route you used, whether
you confirmed the skills afterwards, and whether a new session is needed.

The skills assume a bucket made from
[`copier-scoop-bucket`](https://github.com/hasansezertasan/copier-scoop-bucket)
and the layout in the [template contract](../.ai-rulez/references/contract.md).

## OpenCode

OpenCode installs from git only. Clone the repository, then make each skill discoverable. OpenCode searches `.agents/skills/<name>/SKILL.md` in the project and `~/.agents/skills/<name>/SKILL.md` globally, so link every folder under `skills/` into one of those:

```sh
git clone https://github.com/hasansezertasan/scoop-bucket-skills
mkdir -p ~/.agents/skills
for skill in scoop-bucket-skills/skills/*/; do ln -s "$PWD/${skill%/}" ~/.agents/skills/; done
```

Alternatively, add the clone's `skills/` directory to OpenCode's configuration:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": ["/absolute/path/to/scoop-bucket-skills/skills"]
}
```

To update, run `git pull` in the clone; nothing was copied.

> **Open question.** The official OpenCode documentation shows no way for an npm package to ship skills, so there is no npm route for OpenCode. If that changes, add it here.

## Antigravity

Antigravity installs the plugin straight from the Git URL, so the only artifact is the root `plugin.json` adapter. It carries the plugin name and description, and `scripts/check-repo.mjs` fails when it drifts from the generated Claude manifest.

```sh
agy plugin install https://github.com/hasansezertasan/scoop-bucket-skills
```

This installs into Antigravity's user plugin registry, so the skills are available across repositories. There is no in-place update verb: reinstall with the same command, then restart.

> **Unverified.** Installing from a Git URL has not been exercised against a remote; only `agy plugin validate` on a local clone has been run for this kind of repository, and it validates a source directory rather than proving an install. Confirm with `agy plugin list`, and prefer a supported runtime for production use until an install is verified.
