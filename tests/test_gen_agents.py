"""Tests for ``scripts/gen_agents.py`` (stdlib ``unittest``, no ai-rulez binary).

Exercises the post-processing and drift comparison on synthetic trees. Run with
``python -m unittest discover -s tests`` from the repo root.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
import unittest.mock
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import gen_agents as gen  # noqa: E402

OUTPUTS = ["AGENTS.md", ".agents/skills/demo/SKILL.md", ".claude/skills/demo/SKILL.md"]


def _symlinks_supported() -> bool:
    try:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "target").write_text("x", encoding="utf-8")
            (base / "link").symlink_to(base / "target")
            return True
    except (OSError, NotImplementedError):
        return False


needs_symlinks = unittest.skipUnless(
    _symlinks_supported(), "symlinks unavailable on this platform"
)


def _fs_case_insensitive(directory: Path) -> bool:
    """True when ``directory`` lives on a case-insensitive filesystem."""
    probe = directory / ".caseprobe.tmp"
    try:
        probe.write_text("x", encoding="utf-8")
        return os.path.samefile(probe, directory / ".CASEPROBE.TMP")
    except OSError:
        return False
    finally:
        try:
            probe.unlink()
        except OSError:
            pass


def write(root: Path, rel: str, text: str = "x\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render(root: Path, files: list[str]) -> None:
    """Lay out ``files`` plus a manifest listing them, as ai-rulez would."""
    for rel in files:
        write(root, rel)
    write(root, gen.MANIFEST, json.dumps({"version": "1", "files": files}))


class DropUnwantedTest(unittest.TestCase):
    def test_removes_files_and_manifest_entries(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            render(root, [*gen.DROPPED, *OUTPUTS])
            gen.drop_unwanted(root)
            for rel in gen.DROPPED:
                self.assertFalse((root / rel).exists(), rel)
            self.assertEqual(gen.expected_files(root), {*OUTPUTS, gen.MANIFEST})

    def test_rewrites_manifest_with_lf(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            render(root, [*gen.DROPPED, *OUTPUTS])
            gen.drop_unwanted(root)
            self.assertNotIn(b"\r", (root / gen.MANIFEST).read_bytes())

    def test_tolerates_missing_file_and_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            gen.drop_unwanted(Path(tmp))

    def test_removes_local_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            render(root, OUTPUTS)
            write(root, f"{gen.CONFIG_DIR}/.generated-manifest.local.json", "{}\n")
            gen.drop_unwanted(root)
            self.assertFalse(
                (root / f"{gen.CONFIG_DIR}/.generated-manifest.local.json").exists()
            )
            self.assertEqual(gen.expected_files(root), {*OUTPUTS, gen.MANIFEST})

    def test_rejects_manifest_parent_escape(self) -> None:
        # A manifest entry with `..` would make sync() read and overwrite a
        # file outside the checkout; refuse instead of traversing.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            render(root, [*OUTPUTS, "../escaped.md"])
            with self.assertRaises(SystemExit):
                gen.expected_files(root)

    def test_rejects_manifest_absolute_path(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            render(root, OUTPUTS)
            write(
                root,
                gen.MANIFEST,
                json.dumps({"version": "1", "files": [*OUTPUTS, "/etc/passwd"]}),
            )
            with self.assertRaises(SystemExit):
                gen.expected_files(root)

    def test_rejects_manifest_windows_escape_paths(self) -> None:
        # On Windows a rooted path resets the join to the drive root and a
        # drive-relative path switches drives, yet neither is "absolute"
        # there; judge anchors/drives with Windows semantics on every
        # platform so the guard cannot be bypassed by backslashes.
        for evil in ("\\outside.md", "D:outside.md", "..\\escaped.md"):
            with self.subTest(evil=evil), self.assertRaises(SystemExit):
                gen.validate_manifest_rel(evil)


class CodexMetadataTest(unittest.TestCase):
    def test_copies_openai_yaml_and_records_it_in_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            render(root, OUTPUTS)
            write(root, ".ai-rulez/skills/demo/agents/openai.yaml", "interface: {}\n")
            gen.add_codex_metadata(root)
            rel = ".agents/skills/demo/agents/openai.yaml"
            self.assertEqual((root / rel).read_text(encoding="utf-8"), "interface: {}\n")
            self.assertIn(rel, gen.expected_files(root))

    def test_noop_without_metadata(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            render(root, OUTPUTS)
            gen.add_codex_metadata(root)
            self.assertEqual(gen.expected_files(root), {*OUTPUTS, gen.MANIFEST})


class CompareTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        base = Path(self._tmp.name)
        self.rendered, self.repo = base / "rendered", base / "repo"
        render(self.rendered, OUTPUTS)
        render(self.repo, OUTPUTS)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_identical_trees_pass(self) -> None:
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_reports_stale_file(self) -> None:
        write(self.repo, "AGENTS.md", "hand edit\n")
        self.assertEqual(gen.compare(self.rendered, self.repo), ["stale: AGENTS.md"])

    def test_reports_missing_file(self) -> None:
        (self.repo / OUTPUTS[1]).unlink()
        self.assertEqual(gen.compare(self.rendered, self.repo), [f"missing: {OUTPUTS[1]}"])

    def test_reports_leftover_file_in_owned_dir(self) -> None:
        write(self.repo, ".agents/skills/old/SKILL.md")
        self.assertEqual(
            gen.compare(self.rendered, self.repo),
            ["not generated: .agents/skills/old/SKILL.md"],
        )

    def test_reports_squatting_junction_as_leftover(self) -> None:
        # is_file() misses junctions, so the owned scan must back the
        # predicate with is_link(): otherwise a squatting junction passes
        # --check and exposes outside content later.
        squat = self.repo / ".agents/skills/squat"
        squat.mkdir()
        (squat / "notes.md").write_text("mine\n", encoding="utf-8")
        real_isjunction = getattr(os.path, "isjunction", None)

        def fake_isjunction(path) -> bool:
            if real_isjunction is not None and real_isjunction(path):
                return True
            return Path(path) == squat

        with unittest.mock.patch.object(
            os.path, "isjunction", fake_isjunction, create=True
        ):
            problems = gen.compare(self.rendered, self.repo)
        self.assertIn("not generated: .agents/skills/squat", problems)

    def test_reports_root_file_no_longer_generated(self) -> None:
        render(self.rendered, OUTPUTS[1:])
        self.assertEqual(
            gen.compare(self.rendered, self.repo),
            [f"stale: {gen.MANIFEST}", "not generated: AGENTS.md"],
        )

    def test_reports_unwanted_root_files(self) -> None:
        write(self.repo, "CLAUDE.md")
        write(self.repo, "GEMINI.md")
        self.assertEqual(
            gen.compare(self.rendered, self.repo),
            ["unwanted: CLAUDE.md", "unwanted: GEMINI.md"],
        )

    @needs_symlinks
    def test_reports_dangling_dropped_link(self) -> None:
        (self.repo / "CLAUDE.md").symlink_to("nowhere")
        self.assertEqual(gen.compare(self.rendered, self.repo), ["unwanted: CLAUDE.md"])

    def test_remove_stale_falls_back_to_rmdir(self) -> None:
        # Detaching a directory link needs directory removal; plain unlink
        # refuses it on Windows.
        with (
            unittest.mock.patch.object(
                gen.os, "unlink", side_effect=PermissionError(13, "denied")
            ),
            unittest.mock.patch.object(gen.os, "rmdir") as rmdir,
            unittest.mock.patch.object(gen, "is_link", return_value=True),
        ):
            gen.remove_stale(Path("/junction"))
        rmdir.assert_called_once_with(Path("/junction"))

    def test_remove_stale_reraises_for_real_directory(self) -> None:
        # A real directory must not be silently rmdir'd: re-raise so a
        # non-empty directory surfaces ENOTEMPTY only via its own path,
        # never partway through the destructive phase.
        with (
            unittest.mock.patch.object(
                gen.os, "unlink", side_effect=IsADirectoryError(21, "dir")
            ),
            unittest.mock.patch.object(gen.os, "rmdir") as rmdir,
            unittest.mock.patch.object(gen, "is_link", return_value=False),
        ):
            with self.assertRaises(IsADirectoryError):
                gen.remove_stale(Path("/realdir"))
        rmdir.assert_not_called()

    def test_remove_stale_tolerates_absence(self) -> None:
        gen.remove_stale(Path(self._tmp.name) / "absent")

    def test_ignores_claude_files_outside_skills(self) -> None:
        write(self.repo, ".claude/settings.local.json", "{}\n")
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    @needs_symlinks
    def test_reports_symlink_at_expected_path_as_stale(self) -> None:
        dest = self.repo / OUTPUTS[0]
        outside = Path(self._tmp.name) / "outside.txt"
        outside.write_bytes(dest.read_bytes())
        dest.unlink()
        dest.symlink_to(outside)
        self.assertEqual(gen.compare(self.rendered, self.repo), [f"stale: {OUTPUTS[0]}"])

    @needs_symlinks
    def test_reports_redirected_parent(self) -> None:
        # Outputs read through a linked parent compare against outside
        # content; the check must flag the redirect instead of passing.
        mirror = Path(self._tmp.name) / "elsewhere" / ".agents" / "skills" / "demo"
        mirror.mkdir(parents=True)
        (mirror / "SKILL.md").write_text("x\n", encoding="utf-8")
        shutil.rmtree(self.repo / ".agents")
        (self.repo / ".agents").symlink_to(mirror.parents[2])
        self.assertEqual(
            gen.compare(self.rendered, self.repo),
            [
                "redirected: .agents/skills/demo/SKILL.md via .agents",
                "not generated: .agents",
            ],
        )

    def test_reports_orphaned_previous_output(self) -> None:
        # A file the previous manifest lists outside the owned sets (say, an
        # instruction file from a removed preset) is reported, not silently
        # passed, and never auto-deleted: the maintainer may have adopted it.
        # The manifest itself reports stale alongside, and one promote run
        # retires both by refreshing it.
        render(self.repo, [*OUTPUTS, "COPILOT.md"])
        write(self.repo, "COPILOT.md")
        self.assertEqual(
            gen.compare(self.rendered, self.repo),
            [f"stale: {gen.MANIFEST}", "orphaned: COPILOT.md"],
        )

    def test_ignores_absent_previous_output(self) -> None:
        render(self.repo, [*OUTPUTS, "COPILOT.md"])
        (self.repo / "COPILOT.md").unlink()
        self.assertEqual(gen.compare(self.rendered, self.repo), [f"stale: {gen.MANIFEST}"])


class RenderTest(unittest.TestCase):
    def test_runs_project_toolchain_from_source_root(self) -> None:
        # Regression lock: the mise shim resolves the ai-rulez version from
        # the working directory, so render must run from the source root
        # (where .config/mise.toml pins it) rather than the staging copy —
        # otherwise a bare environment falls back to whatever ambient config
        # provides (once an ancient npm-wrapped v4).
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, staging = base / "src", base / "staging"
            staging.mkdir()
            with (
                unittest.mock.patch.object(gen.subprocess, "run") as run,
                unittest.mock.patch.object(
                    gen.shutil, "which", return_value="/bin/ai-rulez"
                ),
                unittest.mock.patch.object(gen.shutil, "copytree"),
            ):
                gen.render(source, staging)
            argv, kwargs = run.call_args.args, run.call_args.kwargs
            self.assertEqual(argv[0][0], "/bin/ai-rulez")
            self.assertIn("--no-self-mcp", argv[0])
            self.assertIn("--strict-config", argv[0])
            self.assertEqual(kwargs.get("cwd"), source)
            config_flag = argv[0][argv[0].index("-C") + 1]
            self.assertTrue(
                config_flag.startswith(str(staging)),
                f"config must stay inside staging, got {config_flag!r}",
            )


class SyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        base = Path(self._tmp.name)
        self.rendered, self.repo = base / "rendered", base / "repo"
        render(self.rendered, OUTPUTS)
        render(self.repo, OUTPUTS)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_promotes_rendered_files(self) -> None:
        write(self.repo, "AGENTS.md", "hand edit\n")
        (self.repo / OUTPUTS[1]).unlink()
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [])
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_removes_previously_generated_stale_files(self) -> None:
        stale = ".agents/skills/old/SKILL.md"
        render(self.repo, [*OUTPUTS, stale])
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [stale])
        self.assertFalse((self.repo / stale).exists())

    def test_keeps_hand_added_files_for_check_to_report(self) -> None:
        extra = ".agents/skills/handadded/SKILL.md"
        write(self.repo, extra)
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [])
        self.assertTrue((self.repo / extra).is_file())
        self.assertEqual(
            gen.compare(self.rendered, self.repo), [f"not generated: {extra}"]
        )

    def test_never_deletes_dropped_files(self) -> None:
        render(self.repo, [*OUTPUTS, "CLAUDE.md"])
        write(self.repo, "CLAUDE.md")
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [])
        self.assertTrue((self.repo / "CLAUDE.md").is_file())

    def test_overwrites_hand_file_under_owned_path(self) -> None:
        # Files under the owned sets are generation-owned by location: a
        # hand-authored file at a newly rendered owned path is promoted over
        # (check already reports such strays as not generated). Outside the
        # owned sets the same collision refuses; see below.
        extra = ".agents/skills/new/SKILL.md"
        render(self.rendered, [*OUTPUTS, extra])
        write(self.repo, extra, "hand draft\n")
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [])
        self.assertEqual(
            (self.repo / extra).read_text(encoding="utf-8"), "x\n"
        )
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_promotes_identical_hand_authored_new_output(self) -> None:
        # Byte-identical content is a no-op, not a conflict.
        extra = ".agents/skills/new/SKILL.md"
        render(self.rendered, [*OUTPUTS, extra])
        write(self.repo, extra)
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [])
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_recovers_malformed_manifest_entries(self) -> None:
        write(self.repo, gen.MANIFEST, json.dumps({"version": "1", "files": [None]}))
        self.assertEqual(
            gen.compare(self.rendered, self.repo), [f"stale: {gen.MANIFEST}"]
        )
        gen.sync(self.rendered, self.repo)
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_recovers_missing_manifest_from_owned_paths(self) -> None:
        # Without a previous manifest, owned locations still prove
        # generation ownership, so the run recreates the manifest.
        (self.repo / gen.MANIFEST).unlink()
        write(self.rendered, OUTPUTS[1], "new\n")
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [])
        self.assertTrue((self.repo / gen.MANIFEST).is_file())
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_still_refuses_collision_outside_owned_paths(self) -> None:
        render(self.rendered, [*OUTPUTS, "EXTRA.md"])
        write(self.repo, "EXTRA.md", "hand\n")
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)

    def test_case_only_rename_outside_owned_refreshes_manifest(self) -> None:
        # Outside the owned sets the old spelling is not removal-eligible.
        # On a case-sensitive filesystem the spellings are two files and
        # the distinct hand-authored one still refuses; on a
        # case-insensitive filesystem they are one file, recognised by
        # object identity, and the manifest refreshes.
        render(self.repo, [*OUTPUTS, "Guide.md"])
        render(self.rendered, [*OUTPUTS, "guide.md"])
        write(self.rendered, "guide.md", "new\n")
        if _fs_case_insensitive(Path(self._tmp.name)):
            self.assertEqual(gen.sync(self.rendered, self.repo), [])
            self.assertEqual(
                (self.repo / "guide.md").read_text(encoding="utf-8"), "new\n"
            )
            self.assertEqual(
                (self.repo / gen.MANIFEST).read_text(encoding="utf-8"),
                (self.rendered / gen.MANIFEST).read_text(encoding="utf-8"),
            )
        else:
            with self.assertRaises(SystemExit):
                gen.sync(self.rendered, self.repo)

    def test_case_only_directory_rename(self) -> None:
        # Ancestor directories take the staged casing. A plain exist_ok
        # mkdir would reuse the old-cased directory on insensitive
        # filesystems (failing outright here, hiding the new spelling
        # from case-sensitive checkouts there), so the variant is renamed.
        # Fresh Widget names keep setUp's demo tree out of the way, so the
        # old casing is really on disk wherever the platform allows it.
        old_file = ".agents/skills/Widget/SKILL.md"
        new = ".agents/skills/widget/SKILL.md"
        render(self.repo, [*OUTPUTS, old_file])
        render(self.rendered, [*OUTPUTS, new])
        write(self.rendered, new, "new\n")
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [old_file])
        names = [p.name for p in (self.repo / ".agents/skills").iterdir()]
        self.assertIn("widget", names)
        self.assertEqual((self.repo / new).read_text(encoding="utf-8"), "new\n")
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    @needs_symlinks
    def test_refuses_unowned_link_collision(self) -> None:
        # Links get the same ownership check as regular files: a new output
        # colliding with an unowned link refuses instead of swapping it.
        outside = Path(self._tmp.name) / "outside.txt"
        outside.write_text("precious\n", encoding="utf-8")
        render(self.rendered, [*OUTPUTS, "EXTRA.md"])
        (self.repo / "EXTRA.md").symlink_to(outside)
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertEqual(outside.read_text(encoding="utf-8"), "precious\n")
        self.assertTrue((self.repo / "EXTRA.md").is_symlink())

    @needs_symlinks
    def test_refuses_link_to_owned_file_collision(self) -> None:
        # A hand-authored link pointing at a generated file must not inherit
        # ownership through its target: samefile follows links, so the
        # identity check is restricted to case-only spellings of the same
        # pathname.
        render(self.rendered, [*OUTPUTS, "EXTRA.md"])
        write(self.rendered, "EXTRA.md", "new\n")
        (self.repo / "EXTRA.md").symlink_to(self.repo / OUTPUTS[0])
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertTrue((self.repo / "EXTRA.md").is_symlink())

    def test_same_known_file_rejects_hard_links(self) -> None:
        # Case-variant hard links share an inode but are distinct directory
        # entries on case-sensitive filesystems: they must not count as a
        # case-only rename, or promotion would replace the unowned entry
        # and silently retire the previous spelling from the manifest.
        if _fs_case_insensitive(Path(self._tmp.name)):
            self.skipTest("requires a case-sensitive filesystem")
        old = Path(self._tmp.name) / "Guide.md"
        new = Path(self._tmp.name) / "guide.md"
        old.write_text("old\n", encoding="utf-8")
        try:
            os.link(old, new)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"hard links unsupported: {exc}")
        self.assertTrue(os.path.samefile(old, new))
        self.assertFalse(gen.same_known_file(Path(self._tmp.name), "guide.md", {"Guide.md"}))

    @needs_symlinks
    def test_refuses_dangling_link_collision(self) -> None:
        # A dangling link cannot be content-compared, so it always refuses;
        # previously it fell through to a failing atomic replace.
        render(self.rendered, [*OUTPUTS, "EXTRA.md"])
        (self.repo / "EXTRA.md").symlink_to("nowhere")
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertTrue((self.repo / "EXTRA.md").is_symlink())

    @needs_symlinks
    def test_promotes_identical_unowned_link(self) -> None:
        render(self.rendered, [*OUTPUTS, "EXTRA.md"])
        outside = Path(self._tmp.name) / "outside.txt"
        outside.write_text("x\n", encoding="utf-8")
        (self.repo / "EXTRA.md").symlink_to(outside)
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [])
        self.assertFalse((self.repo / "EXTRA.md").is_symlink())
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_refuses_promotion_with_orphans(self) -> None:
        # Retiring the manifest must not silently drop ownership of an
        # obsolete outside-owned file that every later check would miss.
        render(self.repo, [*OUTPUTS, "ORPHAN.md"])
        write(self.repo, "ORPHAN.md", "obsolete\n")
        old_manifest = (self.repo / gen.MANIFEST).read_text(encoding="utf-8")
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertEqual(
            (self.repo / gen.MANIFEST).read_text(encoding="utf-8"), old_manifest
        )
        self.assertEqual(
            (self.repo / "ORPHAN.md").read_text(encoding="utf-8"), "obsolete\n"
        )

    @needs_symlinks
    def test_reports_linked_owned_root(self) -> None:
        # With no expected paths left under .agents, a link replacing the
        # owned root itself must still be visible instead of passing clean.
        target = Path(self._tmp.name) / "elsewhere"
        (target / "skills" / "rogue").mkdir(parents=True)
        (target / "skills" / "rogue" / "SKILL.md").write_text("x\n", encoding="utf-8")
        render(self.rendered, ["AGENTS.md"])
        shutil.rmtree(self.repo / ".agents")
        (self.repo / ".agents").symlink_to(target)
        self.assertIn("not generated: .agents", gen.compare(self.rendered, self.repo))

    @needs_symlinks
    def test_removes_stale_broken_root_link(self) -> None:
        # A root-owned file replaced by a dangling link is still owned, so
        # dropping it from the render removes the link rather than stranding
        # or refusing it.
        render(self.rendered, OUTPUTS[1:])
        dest = self.repo / OUTPUTS[0]
        dest.unlink()
        dest.symlink_to("nowhere")
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [OUTPUTS[0]])
        self.assertFalse(os.path.lexists(dest))
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_collision_refusal_writes_nothing(self) -> None:
        # A conflicting new path outside the owned sets sorts after a
        # changed output; the refusal must leave even the earlier outputs
        # unpromoted.
        render(self.rendered, [*OUTPUTS, "ZZZ.md"])
        write(self.rendered, OUTPUTS[1], "new\n")
        write(self.repo, "ZZZ.md", "hand draft\n")
        old_manifest = (self.repo / gen.MANIFEST).read_text(encoding="utf-8")
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertEqual(
            (self.repo / OUTPUTS[1]).read_text(encoding="utf-8"), "x\n"
        )
        self.assertEqual(
            (self.repo / gen.MANIFEST).read_text(encoding="utf-8"), old_manifest
        )

    def test_file_becomes_parent_directory(self) -> None:
        blocker = ".agents/skills/old"
        nested = ".agents/skills/old/nested.md"
        render(self.repo, [*OUTPUTS, blocker])
        render(self.rendered, [*OUTPUTS, nested])
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [blocker])
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_directory_becomes_file(self) -> None:
        inner = ".agents/skills/old/inner.md"
        render(self.repo, [*OUTPUTS, inner])
        render(self.rendered, [*OUTPUTS, ".agents/skills/old"])
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [inner])
        self.assertTrue((self.repo / ".agents/skills/old").is_file())
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_directory_with_hand_content_becomes_nothing(self) -> None:
        inner = ".agents/skills/old/inner.md"
        render(self.repo, [*OUTPUTS, inner])
        write(self.repo, ".agents/skills/old/hand.md", "mine\n")
        render(self.rendered, [*OUTPUTS, ".agents/skills/old"])
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertEqual(
            (self.repo / ".agents/skills/old/hand.md").read_text(encoding="utf-8"),
            "mine\n",
        )
        self.assertTrue((self.repo / inner).is_file())

    @needs_symlinks
    def test_directory_with_hand_symlink_becomes_nothing(self) -> None:
        # Non-file entries count as content: a hand-authored link next to
        # stale files still refuses the replacement.
        inner = ".agents/skills/old/inner.md"
        render(self.repo, [*OUTPUTS, inner])
        (self.repo / ".agents/skills/old/link").symlink_to(inner)
        render(self.rendered, [*OUTPUTS, ".agents/skills/old"])
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertTrue((self.repo / ".agents/skills/old/link").is_symlink())

    @needs_symlinks
    def test_directory_with_broken_symlink_becomes_nothing(self) -> None:
        inner = ".agents/skills/old/inner.md"
        render(self.repo, [*OUTPUTS, inner])
        (self.repo / ".agents/skills/old/dangling").symlink_to("nowhere")
        render(self.rendered, [*OUTPUTS, ".agents/skills/old"])
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertTrue((self.repo / ".agents/skills/old/dangling").is_symlink())

    def test_nested_stale_tree_is_replaced(self) -> None:
        inner = ".agents/skills/old/sub/inner.md"
        render(self.repo, [*OUTPUTS, inner])
        render(self.rendered, [*OUTPUTS, ".agents/skills/old"])
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [inner])
        self.assertTrue((self.repo / ".agents/skills/old").is_file())
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    def test_directory_with_hand_junction_becomes_nothing(self) -> None:
        # A junction must take the link branch, not the directory branch:
        # recursing into its target would misclassify it (or crash on
        # paths outside the repo) instead of refusing the replacement.
        inner = ".agents/skills/old/inner.md"
        render(self.repo, [*OUTPUTS, inner])
        handdir = self.repo / ".agents/skills/old/handdir"
        handdir.mkdir()
        (handdir / "keep.md").write_text("mine\n", encoding="utf-8")
        render(self.rendered, [*OUTPUTS, ".agents/skills/old"])
        real_isjunction = getattr(os.path, "isjunction", None)

        def fake_isjunction(path) -> bool:
            if real_isjunction is not None and real_isjunction(path):
                return True
            return Path(path) == handdir

        with unittest.mock.patch.object(
            os.path, "isjunction", fake_isjunction, create=True
        ):
            with self.assertRaises(SystemExit):
                gen.sync(self.rendered, self.repo)
        self.assertEqual(
            (handdir / "keep.md").read_text(encoding="utf-8"), "mine\n"
        )

    def test_parent_blocked_by_hand_file(self) -> None:
        render(self.rendered, [*OUTPUTS, ".agents/skills/new/deep.md"])
        write(self.repo, ".agents/skills/new", "hand file\n")
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertEqual(
            (self.repo / ".agents/skills/new").read_text(encoding="utf-8"), "hand file\n"
        )

    def test_tolerates_missing_repo_manifest(self) -> None:
        base = Path(self._tmp.name)
        fresh, bare = base / "fresh", base / "bare"
        render(fresh, OUTPUTS)
        bare.mkdir()
        removed = gen.sync(fresh, bare)
        self.assertEqual(removed, [])
        self.assertEqual(gen.compare(fresh, bare), [])

    def test_keeps_previous_manifest_on_midloop_failure(self) -> None:
        # A failure past the manifest's sort position keeps the previous
        # manifest, so a retry converges instead of stranding stale outputs.
        stale = ".agents/skills/old/SKILL.md"
        render(self.repo, [*OUTPUTS, stale])
        old_manifest = (self.repo / gen.MANIFEST).read_text(encoding="utf-8")
        real_replace = gen.os.replace

        def failing_replace(src: Path, dest: Path) -> None:
            if ".claude" in str(dest):
                raise OSError("disk full")
            real_replace(src, dest)

        with unittest.mock.patch.object(
            gen.os, "replace", side_effect=failing_replace
        ):
            with self.assertRaises(OSError):
                gen.sync(self.rendered, self.repo)
        self.assertEqual(
            (self.repo / gen.MANIFEST).read_text(encoding="utf-8"), old_manifest
        )
        self.assertEqual(gen.sync(self.rendered, self.repo), [])
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    @needs_symlinks
    def test_refuses_directory_link_at_expected_path(self) -> None:
        # The atomic rename cannot swap a directory link (Windows), so it
        # refuses instead of failing mid-promotion; file links still heal.
        target = Path(self._tmp.name) / "realdir"
        target.mkdir()
        (target / "keep.md").write_text("mine\n", encoding="utf-8")
        dest = self.repo / OUTPUTS[1]
        dest.unlink()
        dest.symlink_to(target, target_is_directory=True)
        old_manifest = (self.repo / gen.MANIFEST).read_text(encoding="utf-8")
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertTrue(dest.is_symlink())
        self.assertEqual((target / "keep.md").read_text(encoding="utf-8"), "mine\n")
        self.assertEqual(
            (self.repo / gen.MANIFEST).read_text(encoding="utf-8"), old_manifest
        )

    @needs_symlinks
    def test_replaces_symlinked_destination(self) -> None:
        # The atomic rename swaps the link itself, so a symlinked
        # destination heals without touching the link target.
        outside = Path(self._tmp.name) / "outside.txt"
        outside.write_text("precious\n", encoding="utf-8")
        (self.repo / OUTPUTS[0]).unlink()
        (self.repo / OUTPUTS[0]).symlink_to(outside)
        write(self.rendered, OUTPUTS[0], "new\n")
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [])
        self.assertEqual(outside.read_text(encoding="utf-8"), "precious\n")
        dest = self.repo / OUTPUTS[0]
        self.assertFalse(dest.is_symlink())
        self.assertEqual(dest.read_text(encoding="utf-8"), "new\n")
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    @needs_symlinks
    def test_heals_broken_symlink_at_expected_path(self) -> None:
        dest = self.repo / OUTPUTS[1]
        dest.unlink()
        dest.symlink_to("nowhere")
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [])
        self.assertTrue(dest.is_file() and not dest.is_symlink())
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    @needs_symlinks
    def test_removes_stale_broken_symlink(self) -> None:
        # A broken link at a previously generated path is still a stale
        # output: removing it deletes the link, never its target.
        stale = ".agents/skills/old/SKILL.md"
        render(self.repo, [*OUTPUTS, stale])
        (self.repo / stale).unlink()
        (self.repo / stale).symlink_to("nowhere")
        removed = gen.sync(self.rendered, self.repo)
        self.assertEqual(removed, [stale])
        self.assertFalse(os.path.lexists(self.repo / stale))
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    @needs_symlinks
    def test_reports_orphaned_broken_symlink(self) -> None:
        render(self.repo, [*OUTPUTS, "ORPHAN.md"])
        (self.repo / "ORPHAN.md").unlink()
        (self.repo / "ORPHAN.md").symlink_to("nowhere")
        self.assertEqual(
            gen.compare(self.rendered, self.repo),
            [f"stale: {gen.MANIFEST}", "orphaned: ORPHAN.md"],
        )
        # Promotion refuses while the orphan stands, so ownership is never
        # retired silently; the link itself is left untouched.
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertTrue((self.repo / "ORPHAN.md").is_symlink())

    @needs_symlinks
    def test_refuses_symlinked_owned_parent(self) -> None:
        elsewhere = Path(self._tmp.name) / "elsewhere"
        elsewhere.mkdir()
        shutil.rmtree(self.repo / ".agents")
        (self.repo / ".agents").symlink_to(elsewhere)
        with self.assertRaises(SystemExit):
            gen.sync(self.rendered, self.repo)
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_refuses_junction_owned_parent(self) -> None:
        # Windows junctions are not symlinks; the guard must catch both.
        elsewhere = Path(self._tmp.name) / "elsewhere"
        elsewhere.mkdir()
        real_isjunction = getattr(os.path, "isjunction", None)

        def fake_isjunction(path) -> bool:
            if real_isjunction is not None and real_isjunction(path):
                return True
            return Path(path) == self.repo / ".agents"

        with unittest.mock.patch.object(
            os.path, "isjunction", fake_isjunction, create=True
        ):
            with self.assertRaises(SystemExit):
                gen.sync(self.rendered, self.repo)
        self.assertTrue((self.repo / ".agents").is_dir())
        self.assertEqual(list(elsewhere.iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "executable-bit semantics")
    def test_promotes_executable_bit(self) -> None:
        staged = self.rendered / OUTPUTS[1]
        staged.chmod(0o755)
        gen.sync(self.rendered, self.repo)
        self.assertTrue(os.stat(self.repo / OUTPUTS[1]).st_mode & 0o100)

    @unittest.skipUnless(os.name == "posix", "executable-bit semantics")
    def test_promotes_manifest_executable_bit(self) -> None:
        # The manifest is copied on a separate path from the other outputs;
        # its mode must be mirrored too, or a "stale mode" report on it
        # could never be repaired by generate.
        (self.rendered / gen.MANIFEST).chmod(0o755)
        gen.sync(self.rendered, self.repo)
        self.assertTrue(os.stat(self.repo / gen.MANIFEST).st_mode & 0o100)
        self.assertEqual(gen.compare(self.rendered, self.repo), [])

    @unittest.skipUnless(os.name == "posix", "hard-link semantics")
    def test_promote_breaks_hard_link(self) -> None:
        # A previously generated destination hard-linked elsewhere must gain
        # its own inode instead of corrupting the shared one.
        outside = Path(self._tmp.name) / "outside.txt"
        outside.write_text("precious\n", encoding="utf-8")
        dest = self.repo / OUTPUTS[0]
        dest.unlink()
        os.link(outside, dest)
        write(self.rendered, OUTPUTS[0], "new\n")
        gen.sync(self.rendered, self.repo)
        self.assertEqual(outside.read_text(encoding="utf-8"), "precious\n")
        self.assertEqual(dest.read_text(encoding="utf-8"), "new\n")
        self.assertEqual(os.stat(dest).st_nlink, 1)

    def test_promote_cleans_up_temp_file_on_failure(self) -> None:
        with unittest.mock.patch.object(
            gen.os, "replace", side_effect=OSError("no rename")
        ):
            with self.assertRaises(OSError):
                gen.sync(self.rendered, self.repo)
        leftovers = [
            p for p in self.repo.rglob(".gen-agents-*.tmp") if p.is_file()
        ]
        self.assertEqual(leftovers, [])

    @unittest.skipUnless(os.name == "posix", "executable-bit semantics")
    def test_reports_mode_drift(self) -> None:
        (self.repo / OUTPUTS[0]).chmod(0o755)
        self.assertEqual(
            gen.compare(self.rendered, self.repo), [f"stale mode: {OUTPUTS[0]}"]
        )


if __name__ == "__main__":
    unittest.main()
