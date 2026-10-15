# Roadmap

Work that is planned or open, but not yet done. Decisions already taken are in
[docs/decisions](decisions/). Remove an item once it ships and link its
evidence from the relevant guide.

## Evidence gaps

- **Model trials.** The eval cases in each skill's `evals/` are desk exercises
  with rubrics. A first run on 2026-10-15 (`ai-rulez eval run`, `claude-plugin-eval`
  runner, default model) passed 8 of 14 cases, but most failures were the
  setup, not the skills: the runner starts every run in an empty directory with
  no bucket checkout, so cases that said "read the repository's code and
  workflows" got generic answers or refusals. The prompts now say no checkout
  is available and ask for the skill's guidance plus the files to inspect; the
  `scoop-fix-manifest` rubric asks the answer to direct reproducing and
  checking, not to do it. On a rerun at three runs per case (Claude Code
  2.1.296, about $3.40 for four skills), `scoop-fix-manifest`,
  `scoop-update-triage` and `scoop-verify` passed every case. One run is not a
  stable result, and a first-trial rerun showed the judge is noisy.
  `scoop-remove-or-deprecate` failed both cases in two runs. A transcript run
  shows correct answers, including for `removal-needs-no-windows-install`,
  which the haiku judge marks failed. With `--judge-model sonnet` that case
  passed three runs and `deprecate-with-pipx-sibling` still failed, although a
  separate per-item Sonnet grading of its three kept answers passed all four
  rubric items each time, so no single item is being rejected and rewording the
  rubric would not help. The runner's verdict on that case is unexplained and
  the skill is not shown to be at fault; the runner reports
  only "outcome checks failed" and `--grader builtin` needs a persistent `[llm]`
  model and `allow_network` in the user config, which was not set up. `scoop-add` and `scoop-bucket-setup` were rerun with the new prompts
  at three runs per case (about $2.20) and passed all five cases. Also open: in the runner's temporary plugin copy the skill's
  `../../references/contract.md` link does not resolve (the generated root
  skills link `references/contract.md`, which exists), so the contract was never
  read in these runs. Do not pass `--runner-arg --json`: it collides with the
  flag ai-rulez sets and the run errors, which then counts as the full
  `--max-cost`. Use `--runner-arg --keep-temp` to keep transcripts. These
  results are not evidence that any skill works on a real bucket.
- **Host skill use.** [Host support](host-support.md) records the plugin
  installing on Claude Code and Codex (macOS) and one skill answering a desk
  prompt on each. That is one prompt and one run per host: no pass rate, and
  no skill has run against a real bucket. OpenCode, pi and other agents are
  not evaluated.
- **Windows installs.** No skill run has been checked against a real Windows
  install of a published manifest; the examples are regression-derived. This
  needs a Windows machine and cannot be done from the macOS development
  setup used so far.
