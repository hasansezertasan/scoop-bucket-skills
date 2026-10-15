# Roadmap

Work that is planned or open, but not yet done. Decisions already taken are in
[docs/decisions](decisions/). Remove an item once it ships and link its
evidence from the relevant guide.

## Evidence gaps

- **Model trials.** The eval cases in each skill's `evals/` are desk exercises
  with rubrics. A first run on 2026-10-15 (`ai-rulez eval run`, `claude-plugin-eval`
  runner, default model, about $3.90) passed 8 of 14 cases: `scoop-add` 2/2 and
  `scoop-bucket-setup` 1/3 at three runs per case, then `scoop-fix-manifest`,
  `scoop-remove-or-deprecate`, `scoop-update-triage` and `scoop-verify` 1/2, 1/2,
  1/2 and 2/3 at one run per case. The one-run figures are not reliable: a rerun
  of `scoop-update-triage` passed the case that had failed. The failures are
  undiagnosed because the runner reports only "outcome checks failed". Next:
  rerun the four skills at three runs per case (roughly $5), then read the
  failing cases against their skills. Until then these results are not evidence
  that any skill works or is broken.
- **Host rediscovery.** [Host support](host-support.md) lists what is
  structurally validated; installation on each host is not yet recorded.
- **Windows installs.** No skill run has been checked against a real Windows
  install of a published manifest; the examples are regression-derived.
