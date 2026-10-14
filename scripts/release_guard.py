#!/usr/bin/env python3
"""Permit release creation only for the sole pending release at the checked SHA.

release-please can otherwise release an older pending, failed merge on a later
green push. Emits ``is-release-merge=true|false`` for ``$GITHUB_OUTPUT``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PENDING_LABEL = "autorelease: pending"


def is_release_merge(pages: list[list[dict]], sha: str) -> bool:
    """True when exactly one merged pending release PR exists and merged as ``sha``."""
    pending = [
        pr
        for page in pages
        for pr in page
        if pr.get("merged_at")
        and pr.get("base", {}).get("ref") == "main"
        and any(label.get("name") == PENDING_LABEL for label in pr.get("labels", []))
    ]
    return len(pending) == 1 and pending[0].get("merge_commit_sha") == sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pulls", type=Path, required=True, help="`gh api --paginate --slurp` JSON")
    parser.add_argument("--sha", required=True)
    args = parser.parse_args(argv)
    pages = json.loads(args.pulls.read_text(encoding="utf-8"))
    allowed = is_release_merge(pages, args.sha)
    print(f"is-release-merge={str(allowed).lower()}")
    if not allowed:
        print(
            "Release creation skipped: no unique pending release matches the validated commit.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
