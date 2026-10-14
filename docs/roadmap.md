# Roadmap

Work that is planned or open, but not yet done. Decisions already taken are in
[docs/decisions](decisions/). Remove an item once it ships and link its
evidence from the relevant guide.

## Features

- **Bucket setup skill.** Out of scope until the Copier template exists; it
  would scaffold the template and set up identity, Actions and update
  credentials. Record the minimum template version in the
  [contract](../.ai-rulez/references/contract.md) when it ships.

## Evidence gaps

- **Model trials.** The eval cases in each skill's `evals/` are desk exercises
  with rubrics; none has a recorded model run yet.
- **Host rediscovery.** [Host support](host-support.md) lists what is
  structurally validated; installation on each host is not yet recorded.
- **Windows installs.** No skill run has been checked against a real Windows
  install of a published manifest; the examples are regression-derived.
