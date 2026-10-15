"""Tests for repository identity inference."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent / ".ai-rulez/skills/scoop-add/scripts"),
)

import bucket_repository  # noqa: E402


class FromRemoteTest(unittest.TestCase):
    def test_https_remote(self) -> None:
        self.assertEqual(
            bucket_repository.from_remote("https://github.com/acme/scoop-bucket.git"),
            "acme/scoop-bucket",
        )

    def test_ssh_remote(self) -> None:
        self.assertEqual(
            bucket_repository.from_remote("git@github.com:acme/tools.git"),
            "acme/tools",
        )

    def test_non_github_remote(self) -> None:
        self.assertIsNone(
            bucket_repository.from_remote("https://example.com/acme/tools.git")
        )
        self.assertIsNone(
            bucket_repository.from_remote("https://notgithub.com/acme/tools.git")
        )
        self.assertIsNone(
            bucket_repository.from_remote("git@notgithub.com:acme/tools.git")
        )
        self.assertIsNone(
            bucket_repository.from_remote("https://github.com.evil.example/acme/tools.git")
        )

    def test_override_wins_without_running_git(self) -> None:
        with (
            mock.patch.dict(os.environ, {"SCOOP_BUCKET_REPOSITORY": "acme/bucket"}),
            mock.patch.object(bucket_repository.subprocess, "run") as run,
        ):
            self.assertEqual(bucket_repository.resolve(Path(".")), "acme/bucket")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
