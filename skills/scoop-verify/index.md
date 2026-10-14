# Concepts

* [Scoop Verify](SKILL.md) - Decide whether a Scoop bucket change is verified and ready - run the read-only pre-PR readiness gate after adding, updating, repairing, or removing a manifest, and report the verdict with the evidence. Use for readiness verdicts and verification reports: noop URL/hash consistency, smoke commands, placeholder hashes, and whether Windows installation evidence is needed. It never edits manifests; that is scoop-fix-manifest's job.
