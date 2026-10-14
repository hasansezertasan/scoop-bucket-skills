# Verification Evidence

These cases explain why the gate goes beyond JSON syntax and local unit tests.
The template's bucket is empty, and its history contains no committed package
manifests. Package examples below come from regression tests, not observed failed
installs of published manifests. Repository identity in operational commands
still comes from the current remote or an explicit override.

## Observed workflow failure: managed boilerplate

The template's Tests run
<https://github.com/hasansezertasan/bucket-template/actions/runs/37793397032>
at `85a1e2e3687d1c2f931d53443ff244494cd4aa7d` failed Cobo verification:

```text
.gitignore | gitignore | outdated (1 file(s))
1 fragment(s) need updating.
Process completed with exit code 1.
```

Unit tests, JSON lint, and discovery passed; Windows installation was skipped.
Do not diagnose this as a broken manifest or claim installation passed. The
historical Cobo repair `7a1630f781dacedd6b24e213b67708e2ea64385a` used
`cobo sync`; it predates this run and is not proof of this run's repair.

## Regression-derived package cases

| Evidence | Failure to check for | Gate response |
| --- | --- | --- |
| `204526bdaa7efa7e997b07d25dfa0054bf584c22`; `tests/test_add_manifest.py` | CRLF checkout changes the local noop checksum, or the raw URL points at different bytes | Compare canonical local bytes, generated hash, and the exact remote response |
| Same commit; extraction override tests | `extract_dir: dist` still leaves `bin: dist/tool.exe` | Check the executable relative to the extracted directory (`tool.exe` here) |
| `c52d98e13fb139d3f9a1adb8fa6045153105071a`; placeholder tests | Version-based detection misses zero hashes at nonzero versions | Inspect all hashes and verify CI skips placeholders |
| `25d4a4b86717343151a2a976731e729691e28228`; `tests/test_update_manifests.py` | URL/hash update leaves versioned `extract_dir`, `bin`, or shortcuts stale | Review path templates and installed layout |
| `37bf162a9f413c1631efbb1d7d288f6e7463d729`; pipx installer tests | Installing a tool does not expose its command on PATH | Check installer PATH setup and the workflow's current-session PATH |

The smoke command cases follow the actual fallback in
`.github/workflows/tests.yml`: remove trailing `-pipx`, then run `version`.
A CLI that uses `--version` or a different executable needs an override; this is
a workflow-derived scenario, not a claim of a recorded failed package run.
