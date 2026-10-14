"""Unit tests for scripts/release_guard.py."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from release_guard import PENDING_LABEL, is_release_merge  # noqa: E402


def pr(sha, *, merged=True, base="main", labels=(PENDING_LABEL,)):
    return {
        "merged_at": "2026-01-01T00:00:00Z" if merged else None,
        "base": {"ref": base},
        "labels": [{"name": name} for name in labels],
        "merge_commit_sha": sha,
    }


class ReleaseGuardTest(unittest.TestCase):
    def test_sole_pending_release_at_sha_is_allowed(self):
        self.assertTrue(is_release_merge([[pr("abc")]], "abc"))

    def test_later_sha_does_not_release_older_merge(self):
        self.assertFalse(is_release_merge([[pr("abc")]], "def"))

    def test_two_pending_releases_are_refused_across_pages(self):
        self.assertFalse(is_release_merge([[pr("abc")], [pr("def")]], "abc"))

    def test_unmerged_wrong_base_and_unlabelled_are_ignored(self):
        pages = [[pr("x", merged=False), pr("y", base="dev"), pr("z", labels=())]]
        self.assertFalse(is_release_merge(pages, "x"))
        self.assertTrue(is_release_merge(pages + [[pr("abc")]], "abc"))

    def test_no_pull_requests(self):
        self.assertFalse(is_release_merge([], "abc"))


if __name__ == "__main__":
    unittest.main()
