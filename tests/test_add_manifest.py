"""Tests for the ``scoop-add`` skill's ``scripts/add_manifest.py`` (stdlib ``unittest``, no network).

Network calls (PyPI, the GitHub API, the asset download) are mocked, so the
suite exercises the pure rendering/inference logic offline. Run with
``python -m unittest discover -s tests`` from the repo root.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
import tempfile
import types
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent / ".ai-rulez/skills/scoop-add/scripts"),
)

import add_manifest as am  # noqa: E402


class HelperTest(unittest.TestCase):
    def test_normalize(self) -> None:
        self.assertEqual(am.normalize("Foo_Bar.Baz"), "foo-bar-baz")

    def test_clean_desc_strips_article_and_period(self) -> None:
        self.assertEqual(am.clean_desc("A neat tool."), "Neat tool")

    def test_clean_desc_capitalizes(self) -> None:
        self.assertEqual(am.clean_desc("generic CLI"), "Generic CLI")

    def test_parse_repo_owner_repo(self) -> None:
        self.assertEqual(am.parse_repo("o/r"), ("o", "r"))

    def test_parse_repo_url_strips_git(self) -> None:
        self.assertEqual(am.parse_repo("https://github.com/o/r.git"), ("o", "r"))

    def test_parse_repo_rejects_garbage(self) -> None:
        with self.assertRaises(SystemExit):
            am.parse_repo("not-a-repo")
        with self.assertRaises(SystemExit):
            am.parse_repo("https://notgithub.com/o/r.git")
        with self.assertRaises(SystemExit):
            am.parse_repo("https://github.com.evil.example/o/r")
        with self.assertRaises(SystemExit):
            am.parse_repo("git@notgithub.com:o/r.git")

    def test_parse_repo_ssh(self) -> None:
        self.assertEqual(am.parse_repo("git@github.com:o/r.git"), ("o", "r"))

    def test_spdx_from_github_meta(self) -> None:
        self.assertEqual(am.spdx_license({"license": {"spdx_id": "MIT"}}), "MIT")

    def test_spdx_noassertion_falls_back(self) -> None:
        self.assertEqual(
            am.spdx_license({"license": {"spdx_id": "NOASSERTION"}}),
            "TODO-set-SPDX-license",
        )

    def test_pypi_homepage_prefers_case_insensitive_homepage(self) -> None:
        info = {"project_urls": {"homepage": "https://github.com/o/r",
                                 "source": "https://github.com/o/r.git"}}
        self.assertEqual(am.pypi_homepage(info, "r"), "https://github.com/o/r")

    def test_pypi_homepage_falls_back_to_source_without_git(self) -> None:
        info = {"project_urls": {"source": "https://github.com/o/r.git"}}
        self.assertEqual(am.pypi_homepage(info, "r"), "https://github.com/o/r")

    def test_pypi_homepage_default_is_pypi(self) -> None:
        self.assertEqual(am.pypi_homepage({}, "r"), "https://pypi.org/project/r/")

    def test_pypi_license_prefers_expression(self) -> None:
        self.assertEqual(am.pypi_license({"license_expression": "MIT"}), "MIT")

    def test_templatize_replaces_version(self) -> None:
        self.assertEqual(am.templatize("v1.2.3", "1.2.3"), "v$version")
        self.assertEqual(am.templatize("release%231", "release#1"), "$version")
        self.assertEqual(am.templatize("v1.0%2B2", "1.0+2"), "v$version")
        self.assertEqual(am.templatize("v1%2F2", "1/2"), "v$version")
        self.assertEqual(am.templatize("v1%2f2", "1/2"), "v$version")
        self.assertEqual(am.templatize("tools/v1/2", "1/2"), "tools/v$version")

    def test_templatize_ignores_versions_inside_longer_numbers(self) -> None:
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(
                am.templatize("tool-win32-v3.zip", "3"), "tool-win32-v$version.zip"
            )
            self.assertEqual(
                am.templatize("tool-armv3-v3.zip", "3"), "tool-armv3-v$version.zip"
            )
            self.assertEqual(am.templatize("x64-1.2.3.1.zip", "1.2.3"), "x64-1.2.3.1.zip")
        self.assertIn("longer number", err.getvalue())

    def test_classify_arch_reads_the_architecture_from_the_asset_name(self) -> None:
        cases = {
            "tool-x86_64-windows.zip": "64bit",
            "tool-windows-amd64.zip": "64bit",
            "tool-win32-x64.zip": "64bit",
            "tool-windows.zip": "64bit",
            "charm-windows.zip": "64bit",
            "tool-windows-arm64.zip": "arm64",
            "tool-aarch64-pc-windows-msvc.zip": "arm64",
            "tool-win-x86.zip": "32bit",
            "tool-win32.zip": "32bit",
            "tool-i686-windows.zip": "32bit",
            "tool_windows_386.zip": "32bit",
            "tool-windows-32bit.zip": "32bit",
            "tool-windows-32-bit.zip": "32bit",
            "tool-win-x32.zip": "32bit",
            "carmel-windows.zip": "64bit",
            "armello-win.zip": "64bit",
            "tool-armv7-windows.zip": None,
            "tool-arm32.zip": None,
            "tool-armhf.zip": None,
            "tool_armv7_windows.zip": None,
            "tool-aarch32.zip": None,
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(am.classify_arch(name), expected)

    def test_templatize_is_silent_when_the_version_is_absent(self) -> None:
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(am.templatize("static.zip", "1.2.3"), "static.zip")
        self.assertEqual(err.getvalue(), "")

    def test_templatize_warns_when_a_required_version_is_absent(self) -> None:
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(
                am.templatize("static", "1.2.3", required=True), "static"
            )
        self.assertIn("won't auto-update", err.getvalue())

    def test_templatize_replaces_every_occurrence(self) -> None:
        self.assertEqual(
            am.templatize("tool-1.2.3/tool-1.2.3.exe", "1.2.3"),
            "tool-$version/tool-$version.exe",
        )

    def test_noop_source_uses_bucket_repository_and_file_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            noop = Path(tmp) / "noop.ps1"
            noop.write_bytes(b"Write-Output hello\r\n")
            with mock.patch.object(am, "NOOP_FILE", noop):
                url, sha = am.noop_source("acme/scoop-tools", "stable")
        self.assertEqual(
            url,
            "https://raw.githubusercontent.com/acme/scoop-tools/stable/scripts/noop.ps1",
        )
        self.assertEqual(sha, hashlib.sha256(b"Write-Output hello\n").hexdigest())

    def test_noop_source_hashes_canonical_lf_even_with_crlf_input(self) -> None:
        with (
            mock.patch.object(am.Path, "is_file", return_value=True),
            mock.patch.object(
                am.Path, "read_bytes", return_value=b"Write-Output hello\r\n"
            ),
        ):
            _, sha = am.noop_source("acme/scoop-tools", "stable")
        expected = hashlib.sha256(b"Write-Output hello\n").hexdigest()
        self.assertEqual(sha, expected)

    def test_noop_source_requires_noop_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(am, "NOOP_FILE", Path(tmp) / "scripts" / "noop.ps1"):
                with self.assertRaises(SystemExit) as ctx:
                    am.noop_source("acme/scoop-tools")
        self.assertIn("noop.ps1", str(ctx.exception))

    def test_noop_source_rejects_invalid_repository(self) -> None:
        with self.assertRaises(SystemExit):
            am.noop_source("not-a-repository")


class BucketRootTest(unittest.TestCase):
    def test_set_bucket_root_points_module_at_the_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "bucket").mkdir()
            with (
                mock.patch.object(am, "REPO", am.REPO),
                mock.patch.object(am, "BUCKET", am.BUCKET),
                mock.patch.object(am, "NOOP_FILE", am.NOOP_FILE),
            ):
                am._set_bucket_root(root)
                self.assertEqual(am.REPO, root)
                self.assertEqual(am.BUCKET, root / "bucket")
                self.assertEqual(am.NOOP_FILE, root / "scripts" / "noop.ps1")

    def test_set_bucket_root_refuses_a_directory_without_bucket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as ctx:
                am._set_bucket_root(Path(tmp))
        self.assertIn("no bucket/ directory", str(ctx.exception))

    def test_bucket_dir_option_defaults_to_environment(self) -> None:
        with mock.patch.dict(os.environ, {"SCOOP_BUCKET_DIR": "/some/bucket"}):
            args = am.build_parser().parse_args(["shim", "pkg"])
        self.assertEqual(args.bucket_dir, "/some/bucket")


def _zip_bytes(entries: list[str]) -> str:
    """Write a throwaway .zip containing ``entries`` and return its path."""
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".zip")
    import os

    os.close(fd)
    with zipfile.ZipFile(path, "w") as archive:
        for name in entries:
            archive.writestr(name, b"x")
    return path


class InspectZipTest(unittest.TestCase):
    def _inspect(self, entries: list[str], token: str):
        import os

        path = _zip_bytes(entries)
        self.addCleanup(lambda: os.unlink(path))
        return am.inspect_zip(path, token)

    def test_single_wrapping_folder_and_lone_exe(self) -> None:
        extract_dir, exe, hint = self._inspect(
            ["widget/widget.exe", "widget/data.bin"], "widget")
        self.assertEqual(extract_dir, "widget")
        self.assertEqual(exe, "widget.exe")
        self.assertEqual(hint, "")

    def test_no_wrapping_folder(self) -> None:
        extract_dir, exe, _ = self._inspect(["tool.exe", "readme.txt"], "tool")
        self.assertIsNone(extract_dir)
        self.assertEqual(exe, "tool.exe")

    def test_nested_exe_keeps_path_relative_to_wrapper(self) -> None:
        # tool/bin/tool.exe under a stripped `extract_dir: tool` must yield
        # `bin/tool.exe`, not `tool.exe` (which wouldn't exist post-extract).
        extract_dir, exe, hint = self._inspect(
            ["tool/bin/tool.exe", "tool/README"], "tool")
        self.assertEqual(extract_dir, "tool")
        self.assertEqual(exe, "bin/tool.exe")
        self.assertIn("nested", hint)

    def test_nested_exe_no_wrapper(self) -> None:
        _, exe, _ = self._inspect(["bin/tool.exe", "readme.txt"], "tool")
        self.assertEqual(exe, "bin/tool.exe")

    def test_multiple_exes_matches_token(self) -> None:
        _, exe, hint = self._inspect(
            ["app/app.exe", "app/helper.exe"], "app")
        self.assertEqual(exe, "app.exe")
        self.assertEqual(hint, "")

    def test_multiple_exes_no_match_returns_hint(self) -> None:
        _, exe, hint = self._inspect(["a.exe", "b.exe"], "c")
        self.assertIsNone(exe)
        self.assertIn("multiple .exe", hint)

    def test_no_exe_returns_hint(self) -> None:
        _, exe, hint = self._inspect(["readme.txt"], "tool")
        self.assertIsNone(exe)
        self.assertIn("no .exe", hint)

    def test_corrupt_zip_exits(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".zip")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(b"not a valid zip file")
            with self.assertRaises(SystemExit) as ctx:
                am.inspect_zip(path, "tool")
            self.assertIn("not a valid .zip", str(ctx.exception))
        finally:
            if os.path.exists(path):
                os.unlink(path)


class SelectAssetsTest(unittest.TestCase):
    def test_lone_zip_is_classified(self) -> None:
        asset = {"name": "app-windows.zip"}
        self.assertEqual(
            am.select_assets([asset, {"name": "notes.txt"}], None), {"64bit": asset}
        )

    def test_assets_are_keyed_by_architecture_in_class_order(self) -> None:
        arm, x64, x86 = (
            {"name": "a-arm64.zip"}, {"name": "a-x64.zip"}, {"name": "a-x86.zip"},
        )
        picked = am.select_assets([arm, x86, x64], None)
        self.assertEqual(list(picked), ["64bit", "32bit", "arm64"])
        self.assertEqual(picked, {"64bit": x64, "32bit": x86, "arm64": arm})

    def test_default_selection_skips_non_windows_archives(self) -> None:
        win, mac, linux = (
            {"name": "tool-windows-x64.zip"},
            {"name": "tool-darwin-arm64.zip"},
            {"name": "tool-linux-x64.zip"},
        )
        self.assertEqual(am.select_assets([win, mac, linux], None), {"64bit": win})

    def test_default_selection_skips_os_names_with_digits_or_suffixes(self) -> None:
        win = {"name": "tool-win64.zip"}
        others = [{"name": n} for n in (
            "tool-linux64.zip", "tool-osx64.zip", "tool-macosx-arm64.zip",
            "tool-darwin64.zip",
        )]
        self.assertEqual(am.select_assets([win, *others], None), {"64bit": win})

    def test_an_explicit_windows_marker_wins_over_unknown_platforms(self) -> None:
        win = {"name": "tool-windows-x64.zip"}
        others = [{"name": n} for n in (
            "tool-solaris-x64.zip", "tool-ubuntu-x64.zip", "tool.zip",
        )]
        self.assertEqual(am.select_assets([*others, win], None), {"64bit": win})

    def test_windows_marker_is_not_read_inside_darwin(self) -> None:
        mac = {"name": "tool-darwin-arm64.zip"}
        with self.assertRaises(SystemExit):
            am.select_assets([mac], None)

    def test_distro_named_archives_are_skipped_without_a_windows_marker(self) -> None:
        plain = {"name": "tool-x64.zip"}
        distros = [{"name": f"tool-{d}-x64.zip"} for d in ("ubuntu", "debian", "fedora")]
        self.assertEqual(am.select_assets([plain, *distros], None), {"64bit": plain})

    def test_explicit_artifact_may_still_name_a_non_windows_looking_asset(self) -> None:
        mac = {"name": "linuxdeploy-darwin-arm64.zip"}
        self.assertEqual(am.select_assets([mac], ["linuxdeploy-darwin-arm64.zip"]),
                         {"arm64": mac})

    def test_only_non_windows_archives_exit(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            am.select_assets([{"name": "tool-linux-x64.zip"}], None)
        self.assertIn("tool-linux-x64.zip", str(ctx.exception))

    def test_explicit_artifacts(self) -> None:
        a, b, c = {"name": "x.zip"}, {"name": "y-arm64.zip"}, {"name": "z.zip"}
        self.assertEqual(
            am.select_assets([a, b, c], ["x.zip", "y-arm64.zip"]),
            {"64bit": a, "arm64": b},
        )

    def test_two_assets_in_one_class_exit_naming_them(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            am.select_assets([{"name": "a.zip"}, {"name": "b.zip"}], None)
        self.assertIn("a.zip", str(ctx.exception))
        self.assertIn("b.zip", str(ctx.exception))
        self.assertIn("--artifact", str(ctx.exception))

    def test_unsupported_architecture_exits(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            am.select_assets([{"name": "a-armv7.zip"}], None)
        self.assertIn("a-armv7.zip", str(ctx.exception))

    def test_unknown_artifact_exits(self) -> None:
        with self.assertRaises(SystemExit):
            am.select_assets([{"name": "a.zip"}], ["nope.zip"])

    def test_no_assets_exits(self) -> None:
        with self.assertRaises(SystemExit):
            am.select_assets([], None)


class RenderTest(unittest.TestCase):
    def test_shim_uv_shape(self) -> None:
        data = am.render_shim(
            am.ShimManifestSpec(
                package="gizmo",
                installer="uv",
                description="Demo (uv tool install)",
                homepage="https://github.com/o/gizmo",
                license_id="MIT",
                version="1.0.0",
                noop_url="https://example.com/noop.ps1",
                noop_hash="a" * 64,
            )
        )
        self.assertEqual(
            list(data),
            ["version", "description", "homepage", "license", "depends", "url",
             "hash", "installer", "uninstaller", "checkver", "autoupdate"],
        )
        self.assertEqual(data["depends"], "uv")
        self.assertEqual(data["installer"]["script"],
                         "uv tool install gizmo==$version --force")
        self.assertEqual(data["uninstaller"]["script"], "uv tool uninstall gizmo")
        self.assertEqual(data["url"], "https://example.com/noop.ps1")
        self.assertEqual(data["hash"], "a" * 64)

    def test_shim_pipx_uses_pipx_commands(self) -> None:
        data = am.render_shim(
            am.ShimManifestSpec(
                package="widget",
                installer="pipx",
                description="Demo (pipx install)",
                homepage="https://github.com/o/widget",
                license_id="MIT",
                version="1.0.0",
                noop_url="https://example.com/noop.ps1",
                noop_hash="a" * 64,
            )
        )
        self.assertEqual(data["depends"], "pipx")
        self.assertEqual(data["installer"]["script"],
                         "pipx ensurepath; pipx install widget==$version --force")
        self.assertEqual(data["uninstaller"]["script"], "pipx uninstall widget")

    def test_binary_shape_and_extract_dir(self) -> None:
        data = am.render_binary(
            am.BinaryManifestSpec(
                token="widget",
                repository_url="https://github.com/o/widget",
                description="Demo",
                license_id="MIT",
                version="1.0.0",
                checkver={"github": "https://github.com/o/widget"},
                architectures={"64bit": am.ArchitectureSpec(
                    download_url="https://github.com/o/widget/releases/download/v1.0.0/widget-windows.zip",
                    sha256="a" * 64,
                    extract_dir="widget",
                    executable="widget.exe",
                    autoupdate_url="https://github.com/o/widget/releases/download/v$version/widget-windows.zip",
                )},
            )
        )
        self.assertEqual(
            list(data),
            ["version", "description", "homepage", "license", "architecture",
             "bin", "shortcuts", "checkver", "autoupdate"],
        )
        self.assertEqual(data["architecture"]["64bit"]["extract_dir"], "widget")
        self.assertEqual(data["bin"], "widget.exe")
        self.assertEqual(data["shortcuts"], [["widget.exe", "widget"]])
        self.assertEqual(data["checkver"], {"github": "https://github.com/o/widget"})

    def test_binary_omits_extract_dir_when_none(self) -> None:
        data = am.render_binary(
            am.BinaryManifestSpec(
                token="tool",
                repository_url="https://github.com/o/tool",
                description="Demo",
                license_id="MIT",
                version="1.0.0",
                checkver={"github": "https://github.com/o/tool"},
                architectures={"64bit": am.ArchitectureSpec(
                    download_url="u",
                    sha256="a" * 64,
                    extract_dir=None,
                    executable="tool.exe",
                    autoupdate_url="u",
                )},
            )
        )
        self.assertNotIn("extract_dir", data["architecture"]["64bit"])

    def test_binary_renders_autoupdate_extract_dir_and_bin(self) -> None:
        data = am.render_binary(
            am.BinaryManifestSpec(
                token="widget",
                repository_url="https://github.com/o/widget",
                description="Demo",
                license_id="MIT",
                version="1.2.3",
                checkver={"github": "https://github.com/o/widget"},
                architectures={"64bit": am.ArchitectureSpec(
                    download_url="https://github.com/o/widget/releases/download/v1.2.3/widget-1.2.3.zip",
                    sha256="a" * 64,
                    extract_dir="widget-1.2.3",
                    executable="widget-1.2.3.exe",
                    autoupdate_url="https://github.com/o/widget/releases/download/v$version/widget-$version.zip",
                    autoupdate_extract_dir="widget-$version",
                    autoupdate_bin="widget-$version.exe",
                )},
            )
        )
        self.assertEqual(data["architecture"]["64bit"]["extract_dir"], "widget-1.2.3")
        self.assertEqual(data["bin"], "widget-1.2.3.exe")
        self.assertEqual(
            data["autoupdate"]["architecture"]["64bit"]["extract_dir"],
            "widget-$version",
        )
        self.assertEqual(data["autoupdate"]["bin"], "widget-$version.exe")
        self.assertEqual(
            data["autoupdate"]["shortcuts"],
            [["widget-$version.exe", "widget"]],
        )


class AddShimTest(unittest.TestCase):
    def setUp(self) -> None:
        # add_shim hashes the bucket's scripts/noop.ps1; give it a stand-in.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        noop = Path(tmp.name) / "noop.ps1"
        noop.write_bytes(b"Write-Output hello\n")
        patcher = mock.patch.object(am, "NOOP_FILE", noop)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _run(self, info: dict, **ns):
        captured = {}
        stderr = io.StringIO()
        fields = {
            "package": "pkg",
            "via": "uv",
            "name": None,
            "homepage": None,
            "bucket_repository": "acme/scoop-bucket",
            "bucket_ref": "main",
            **ns,
        }
        args = types.SimpleNamespace(**fields)
        with (
            mock.patch.object(am, "pypi_info", return_value=info),
            mock.patch.object(am, "_write_manifest",
                              side_effect=lambda n, d: captured.update(name=n, data=d)
                              or Path(f"bucket/{n}.json")),
            mock.patch("sys.stdout", io.StringIO()),
            mock.patch("sys.stderr", stderr),
        ):
            am.add_shim(args)
        captured["stderr"] = stderr.getvalue()
        return captured

    def test_uv_uses_bare_name(self) -> None:
        cap = self._run({"name": "gizmo", "version": "1.0.0", "summary": "Demo tool",
                         "project_urls": {"homepage": "https://github.com/o/gizmo"}})
        self.assertEqual(cap["name"], "gizmo")
        self.assertEqual(cap["data"]["description"], "Demo tool (uv tool install)")

    def test_pipx_appends_suffix(self) -> None:
        cap = self._run({"name": "widget", "version": "1.0.0", "summary": "Demo"},
                        via="pipx")
        self.assertEqual(cap["name"], "widget-pipx")
        self.assertEqual(cap["data"]["depends"], "pipx")
        self.assertTrue(cap["data"]["description"].endswith("(pipx install)"))

    def test_next_step_regenerates_readme_catalog(self) -> None:
        cap = self._run({"name": "widget", "version": "1.0.0", "summary": "Demo"})
        self.assertIn("mise run generate-readme", cap["stderr"])


class WriteManifestTest(unittest.TestCase):
    def _tmp_bucket(self) -> Path:
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_rejects_path_separator(self) -> None:
        with mock.patch.object(am, "BUCKET", self._tmp_bucket()):
            with self.assertRaises(SystemExit):
                am._write_manifest("../evil", {})

    def test_refuses_existing(self) -> None:
        # Self-contained: create the collision in a temp bucket rather than
        # depending on a real manifest in bucket/ (which would also risk the
        # write escaping into the working tree if that file were ever removed).
        bucket = self._tmp_bucket()
        (bucket / "dupe.json").write_text("{}", encoding="utf-8")
        with mock.patch.object(am, "BUCKET", bucket):
            with self.assertRaises(SystemExit):
                am._write_manifest("dupe", {})

    def test_writes_into_patched_bucket(self) -> None:
        bucket = self._tmp_bucket()
        with mock.patch.object(am, "BUCKET", bucket):
            out = am._write_manifest("newpkg", {"version": "1.0.0"})
        self.assertTrue(out.exists())
        self.assertEqual(out.read_text().rstrip("\n"), '{\n    "version": "1.0.0"\n}')


class PypiInfoTest(unittest.TestCase):
    def test_404_exits_cleanly(self) -> None:
        err = urllib.error.HTTPError("u", 404, "Not Found", {}, None)  # type: ignore[arg-type]
        with mock.patch.object(am, "fetch_json", side_effect=err):
            with self.assertRaises(SystemExit):
                am.pypi_info("nope")

    def test_missing_info_key_exits(self) -> None:
        with mock.patch.object(am, "fetch_json", return_value={"releases": {}}):
            with self.assertRaises(SystemExit) as ctx:
                am.pypi_info("broken")
        self.assertIn("missing 'info'", str(ctx.exception))


class AddBinaryTest(unittest.TestCase):
    def test_seed_requires_bin_flag(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        args = argparse.Namespace(
            repo="o/r",
            name="tool",
            seed=True,
            artifact=None,
            extract_dir=None,
            bin=None,
        )
        with (
            mock.patch.object(am, "fetch_json", return_value=meta),
            mock.patch("sys.stderr", io.StringIO()),
            self.assertRaises(SystemExit) as ctx,
        ):
            am.add_binary(args)
        self.assertIn("--bin", str(ctx.exception))

    def test_seed_writes_placeholder_manifest(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        args = argparse.Namespace(
            repo="o/r",
            name="tool",
            seed=True,
            artifact=None,
            extract_dir=None,
            bin="tool.exe",
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["name"] = name
            written["data"] = data
            return Path(f"bucket/{name}.json")

        with (
            mock.patch.object(am, "fetch_json", return_value=meta),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("sys.stdout", io.StringIO()),
            mock.patch("sys.stderr", io.StringIO()),
        ):
            am.add_binary(args)

        self.assertEqual(written["data"]["version"], "0.0.0")
        self.assertEqual(written["data"]["architecture"]["64bit"]["hash"], "0" * 64)

    def test_seed_templatizes_versioned_artifact(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        args = argparse.Namespace(
            repo="o/r", name="tool", seed=True, artifact=["widget-0.0.0.zip"],
            extract_dir=None, bin="tool.exe",
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["data"] = data
            return Path(f"bucket/{name}.json")

        with (
            mock.patch.object(am, "fetch_json", return_value=meta),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("sys.stdout", io.StringIO()),
            mock.patch("sys.stderr", io.StringIO()),
        ):
            am.add_binary(args)

        self.assertEqual(
            written["data"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/v0.0.0/widget-0.0.0.zip",
        )
        self.assertEqual(
            written["data"]["autoupdate"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/v$version/widget-$version.zip",
        )

    def test_repo_not_found_exits_cleanly(self) -> None:
        err = urllib.error.HTTPError("u", 404, "Not Found", {}, None)  # type: ignore[arg-type]
        args = argparse.Namespace(
            repo="missing/repo",
            name=None,
            seed=False,
            artifact=None,
            extract_dir=None,
            bin=None,
        )
        with (
            mock.patch.object(am, "fetch_json", side_effect=err),
            self.assertRaises(SystemExit) as ctx,
        ):
            am.add_binary(args)
        self.assertIn("not found", str(ctx.exception))

    def test_add_binary_rebases_exe_with_extract_dir_override(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        release = {
            "tag_name": "v1.0.0",
            "assets": [{"name": "tool.zip", "browser_download_url": "https://example/tool.zip"}],
        }
        args = argparse.Namespace(
            repo="o/r",
            name="tool",
            seed=False,
            artifact=["tool.zip"],
            extract_dir="dist",
            bin=None,
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["name"] = name
            written["data"] = data
            return Path(f"bucket/{name}.json")

        with (
            mock.patch.object(am, "fetch_json", side_effect=[meta, release]),
            mock.patch.object(am, "download_zip", return_value="/tmp/fake.zip"),
            mock.patch.object(am, "sha256_of_file", return_value="0" * 64),
            mock.patch.object(am, "inspect_zip", return_value=(None, "dist/tool.exe", "")),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("os.unlink"),
            mock.patch("sys.stdout"),
            mock.patch("sys.stderr"),
        ):
            am.add_binary(args)

        self.assertEqual(written["data"]["architecture"]["64bit"]["extract_dir"], "dist")
        self.assertEqual(written["data"]["bin"], "tool.exe")

    def test_add_binary_fails_when_exe_outside_extract_dir_and_no_bin(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        release = {
            "tag_name": "v1.0.0",
            "assets": [{"name": "tool.zip", "browser_download_url": "https://example/tool.zip"}],
        }
        args = argparse.Namespace(
            repo="o/r",
            name="tool",
            seed=False,
            artifact=["tool.zip"],
            extract_dir="other",
            bin=None,
        )

        with (
            mock.patch.object(am, "fetch_json", side_effect=[meta, release]),
            mock.patch.object(am, "download_zip", return_value="/tmp/fake.zip"),
            mock.patch.object(am, "sha256_of_file", return_value="0" * 64),
            mock.patch.object(am, "inspect_zip", return_value=(None, "dist/tool.exe", "")),
            mock.patch("os.unlink"),
            mock.patch("sys.stderr"),
            self.assertRaises(SystemExit),
        ):
            am.add_binary(args)

    def test_add_binary_preserves_url_encoding(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        release = {
            "tag_name": "release#1",
            "assets": [
                {
                    "name": "tool#1.zip",
                    "browser_download_url": "https://github.com/o/r/releases/download/release%231/tool%231.zip",
                }
            ],
        }
        args = argparse.Namespace(
            repo="o/r",
            name="tool",
            seed=False,
            artifact=["tool#1.zip"],
            extract_dir=None,
            bin="tool.exe",
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["name"] = name
            written["data"] = data
            return Path(f"bucket/{name}.json")

        with (
            mock.patch.object(am, "fetch_json", side_effect=[meta, release]),
            mock.patch.object(am, "download_zip", return_value="/tmp/fake.zip"),
            mock.patch.object(am, "sha256_of_file", return_value="0" * 64),
            mock.patch.object(am, "inspect_zip", return_value=(None, "tool.exe", "")),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("os.unlink"),
            mock.patch("sys.stdout"),
            mock.patch("sys.stderr"),
        ):
            am.add_binary(args)

        self.assertEqual(
            written["data"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/release%231/tool%231.zip",
        )
        self.assertEqual(
            written["data"]["autoupdate"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/release%23$version/tool%231.zip",
        )

    def test_add_binary_handles_tag_with_slashes(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        release = {
            "tag_name": "release/v1.0.0",
            "assets": [
                {
                    "name": "tool.zip",
                    "browser_download_url": "https://github.com/o/r/releases/download/release/v1.0.0/tool.zip",
                }
            ],
        }
        args = argparse.Namespace(
            repo="o/r",
            name="tool",
            seed=False,
            artifact=["tool.zip"],
            extract_dir=None,
            bin="tool.exe",
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["name"] = name
            written["data"] = data
            return Path(f"bucket/{name}.json")

        with (
            mock.patch.object(am, "fetch_json", side_effect=[meta, release]),
            mock.patch.object(am, "download_zip", return_value="/tmp/fake.zip"),
            mock.patch.object(am, "sha256_of_file", return_value="0" * 64),
            mock.patch.object(am, "inspect_zip", return_value=(None, "tool.exe", "")),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("os.unlink"),
            mock.patch("sys.stdout"),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            am.add_binary(args)

        self.assertEqual(
            written["data"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/release/v1.0.0/tool.zip",
        )
        self.assertIn("checkver", err.getvalue())
        self.assertEqual(written["data"]["version"], "1.0.0")
        self.assertEqual(
            written["data"]["checkver"],
            {"github": "https://github.com/o/r", "regex": "(?:/releases/tag/|^)release(?:/|%2[Ff])v([\\d.-]+)"},
        )
        self.assertEqual(
            written["data"]["autoupdate"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/release/v$version/tool.zip",
        )

    def test_add_binary_emits_a_regex_for_an_uppercase_tag(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        release = {
            "tag_name": "V1.2.3",
            "assets": [
                {
                    "name": "tool.zip",
                    "browser_download_url": "https://github.com/o/r/releases/download/V1.2.3/tool.zip",
                }
            ],
        }
        args = argparse.Namespace(
            repo="o/r", name="tool", seed=False, artifact=["tool.zip"],
            extract_dir=None, bin="tool.exe",
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["data"] = data
            return Path(f"bucket/{name}.json")

        with (
            mock.patch.object(am, "fetch_json", side_effect=[meta, release]),
            mock.patch.object(am, "download_zip", return_value="/tmp/fake.zip"),
            mock.patch.object(am, "sha256_of_file", return_value="0" * 64),
            mock.patch.object(am, "inspect_zip", return_value=(None, "tool.exe", "")),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("os.unlink"),
            mock.patch("sys.stdout"),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            am.add_binary(args)

        self.assertEqual(written["data"]["version"], "1.2.3")
        self.assertEqual(
            written["data"]["checkver"],
            {"github": "https://github.com/o/r", "regex": "(?:/releases/tag/|^)V([\\d.-]+)"},
        )
        self.assertEqual(
            written["data"]["autoupdate"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/V$version/tool.zip",
        )
        self.assertIn("lowercase v", err.getvalue())

    def test_add_binary_handles_encoded_slashes(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        release = {
            "tag_name": "v1/2",
            "assets": [
                {
                    "name": "tool.zip",
                    "browser_download_url": "https://github.com/o/r/releases/download/v1%2F2/tool.zip",
                }
            ],
        }
        args = argparse.Namespace(
            repo="o/r",
            name="tool",
            seed=False,
            artifact=["tool.zip"],
            extract_dir=None,
            bin="tool.exe",
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["name"] = name
            written["data"] = data
            return Path(f"bucket/{name}.json")

        with (
            mock.patch.object(am, "fetch_json", side_effect=[meta, release]),
            mock.patch.object(am, "download_zip", return_value="/tmp/fake.zip"),
            mock.patch.object(am, "sha256_of_file", return_value="0" * 64),
            mock.patch.object(am, "inspect_zip", return_value=(None, "tool.exe", "")),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("os.unlink"),
            mock.patch("sys.stdout"),
            mock.patch("sys.stderr"),
        ):
            am.add_binary(args)

        self.assertEqual(
            written["data"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/v1%2F2/tool.zip",
        )
        self.assertEqual(
            written["data"]["autoupdate"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/v$version/tool.zip",
        )

    def test_add_binary_templatizes_versioned_paths(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "widget"}
        release = {
            "tag_name": "v1.2.3",
            "assets": [
                {
                    "name": "widget-1.2.3.zip",
                    "browser_download_url": "https://github.com/o/r/releases/download/v1.2.3/widget-1.2.3.zip",
                }
            ],
        }
        args = argparse.Namespace(
            repo="o/r",
            name="widget",
            seed=False,
            artifact=["widget-1.2.3.zip"],
            extract_dir=None,
            bin=None,
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["name"] = name
            written["data"] = data
            return Path(f"bucket/{name}.json")

        with (
            mock.patch.object(am, "fetch_json", side_effect=[meta, release]),
            mock.patch.object(am, "download_zip", return_value="/tmp/fake.zip"),
            mock.patch.object(am, "sha256_of_file", return_value="0" * 64),
            mock.patch.object(
                am,
                "inspect_zip",
                return_value=("widget-1.2.3", "widget-1.2.3.exe", ""),
            ),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("os.unlink"),
            mock.patch("sys.stdout"),
            mock.patch("sys.stderr"),
        ):
            am.add_binary(args)

        self.assertEqual(written["data"]["architecture"]["64bit"]["extract_dir"], "widget-1.2.3")
        self.assertEqual(written["data"]["bin"], "widget-1.2.3.exe")
        self.assertEqual(
            written["data"]["autoupdate"]["architecture"]["64bit"]["extract_dir"],
            "widget-$version",
        )
        self.assertEqual(written["data"]["autoupdate"]["bin"], "widget-$version.exe")
        self.assertEqual(
            written["data"]["autoupdate"]["shortcuts"],
            [["widget-$version.exe", "widget"]],
        )

    def test_add_binary_fails_on_corrupt_zip_even_with_bin_supplied(self) -> None:
        meta = {"html_url": "https://github.com/o/r", "description": "tool"}
        release = {
            "tag_name": "v1.0.0",
            "assets": [{"name": "tool.zip", "browser_download_url": "https://example/tool.zip"}],
        }
        args = argparse.Namespace(
            repo="o/r",
            name="tool",
            seed=False,
            artifact=["tool.zip"],
            extract_dir=None,
            bin="tool.exe",
        )
        fd, path = tempfile.mkstemp(suffix=".zip")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(b"not a valid zip")
            with (
                mock.patch.object(am, "fetch_json", side_effect=[meta, release]),
                mock.patch.object(am, "download_zip", return_value=path),
                mock.patch("sys.stderr"),
                self.assertRaises(SystemExit) as ctx,
            ):
                am.add_binary(args)
            self.assertIn("not a valid .zip", str(ctx.exception))
        finally:
            if os.path.exists(path):
                os.unlink(path)

class AddBinaryInferenceTest(unittest.TestCase):
    """`add_binary` end to end with the network and archives stubbed."""

    META = {"html_url": "https://github.com/o/r", "description": "tool"}

    def _run(self, tag, asset_names, *, bin=None, extract_dir=None, artifact=None,
             archives=None, seed=False):
        """Return ``(manifest, stderr)``; ``archives`` maps asset name -> (dir, exe)."""
        archives = archives or {}
        base = f"https://github.com/o/r/releases/download/{tag}"
        release = {
            "tag_name": tag,
            "assets": [
                {"name": n, "browser_download_url": f"{base}/{n}"} for n in asset_names
            ],
        }
        args = argparse.Namespace(
            repo="o/r", name="tool", seed=seed, artifact=artifact,
            extract_dir=extract_dir, bin=bin,
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["data"] = data
            return Path(f"bucket/{name}.json")

        def fake_inspect(path: str, token: str):
            found_dir, exe = archives.get(path.rsplit("/", 1)[-1], (None, "tool.exe"))
            return found_dir, exe, ""

        with (
            mock.patch.object(am, "fetch_json", side_effect=[self.META, release]),
            mock.patch.object(am, "download_zip", side_effect=lambda url: url),
            mock.patch.object(
                am, "sha256_of_file",
                side_effect=lambda path: hashlib.sha256(path.encode()).hexdigest(),
            ),
            mock.patch.object(am, "inspect_zip", side_effect=fake_inspect),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("os.unlink"),
            mock.patch("sys.stdout", io.StringIO()),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            am.add_binary(args)
        return written["data"], err.getvalue()

    def test_prefixed_tag_gets_a_checkver_regex_and_a_literal_prefix(self) -> None:
        data, err = self._run("release-1.2.3", ["tool.zip"])
        self.assertEqual(data["version"], "1.2.3")
        self.assertEqual(
            data["checkver"],
            {"github": "https://github.com/o/r", "regex": "(?:/releases/tag/|^)release-([\\d.-]+)"},
        )
        self.assertEqual(
            data["autoupdate"]["architecture"]["64bit"]["url"],
            "https://github.com/o/r/releases/download/release-$version/tool.zip",
        )
        self.assertIn("checkver.regex", err)

    def test_regex_accepts_every_url_encoded_prefix_character(self) -> None:
        data, _ = self._run("release#1", ["tool.zip"])
        self.assertEqual(
            data["checkver"]["regex"],
            "(?:/releases/tag/|^)release(?:#|%23)([\\d.-]+)",
        )
        data, _ = self._run("my app-1.0", ["tool.zip"])
        self.assertEqual(
            data["checkver"]["regex"],
            "(?:/releases/tag/|^)my(?: |%20)app-([\\d.-]+)",
        )

    def test_plain_and_lowercase_v_tags_need_no_regex(self) -> None:
        for tag in ("1.2.3", "v1.2.3"):
            with self.subTest(tag=tag):
                data, err = self._run(tag, ["tool.zip"])
                self.assertEqual(data["version"], "1.2.3")
                self.assertEqual(data["checkver"], {"github": "https://github.com/o/r"})
                self.assertNotIn("warning:", err)

    def test_assets_become_one_block_per_architecture(self) -> None:
        data, _ = self._run(
            "v1.0.0", ["tool-x64.zip", "tool-x86.zip", "tool-arm64.zip"]
        )
        base = "https://github.com/o/r/releases/download"
        self.assertEqual(list(data["architecture"]), ["64bit", "32bit", "arm64"])
        self.assertEqual(
            data["architecture"]["32bit"]["url"], f"{base}/v1.0.0/tool-x86.zip"
        )
        self.assertEqual(
            data["autoupdate"]["architecture"]["arm64"]["url"],
            f"{base}/v$version/tool-arm64.zip",
        )
        hashes = {block["hash"] for block in data["architecture"].values()}
        self.assertEqual(len(hashes), 3)

    def test_lone_arm64_asset_is_not_labelled_64bit(self) -> None:
        data, err = self._run("v1.0.0", ["tool-arm64.zip"])
        self.assertEqual(list(data["architecture"]), ["arm64"])
        self.assertNotIn("non-x64", err)

    def test_ambiguous_assets_write_nothing(self) -> None:
        with self.assertRaises(SystemExit):
            self._run("v1.0.0", ["tool-a.zip", "tool-b.zip"])

    def test_explicit_artifacts_pick_the_architectures(self) -> None:
        data, _ = self._run(
            "v1.0.0", ["tool-a.zip", "tool-b.zip", "tool-arm64.zip"],
            artifact=["tool-b.zip", "tool-arm64.zip"],
        )
        self.assertEqual(list(data["architecture"]), ["64bit", "arm64"])
        self.assertTrue(data["architecture"]["64bit"]["url"].endswith("tool-b.zip"))

    def test_extract_dir_is_inferred_per_architecture(self) -> None:
        data, _ = self._run(
            "v1.0.0", ["tool-x64.zip", "tool-arm64.zip"],
            archives={
                "tool-x64.zip": ("tool-1.0.0-x64", "tool.exe"),
                "tool-arm64.zip": ("tool-1.0.0-arm64", "tool.exe"),
            },
        )
        self.assertEqual(
            data["architecture"]["arm64"]["extract_dir"], "tool-1.0.0-arm64"
        )
        self.assertEqual(
            data["autoupdate"]["architecture"]["64bit"]["extract_dir"],
            "tool-$version-x64",
        )

    def test_identical_executables_stay_top_level(self) -> None:
        data, _ = self._run("v1.0.0", ["tool-x64.zip", "tool-arm64.zip"])
        self.assertEqual(data["bin"], "tool.exe")
        self.assertNotIn("bin", data["architecture"]["arm64"])

    def test_differing_executables_move_into_each_architecture(self) -> None:
        data, _ = self._run(
            "v1.0.0", ["tool-x64.zip", "tool-arm64.zip"],
            archives={
                "tool-x64.zip": (None, "tool.exe"),
                "tool-arm64.zip": (None, "tool-arm64.exe"),
            },
        )
        self.assertNotIn("bin", data)
        self.assertNotIn("shortcuts", data)
        self.assertEqual(data["architecture"]["64bit"]["bin"], "tool.exe")
        self.assertEqual(data["architecture"]["arm64"]["bin"], "tool-arm64.exe")
        self.assertEqual(
            data["architecture"]["arm64"]["shortcuts"], [["tool-arm64.exe", "tool"]]
        )

    def test_bin_override_applies_to_every_architecture(self) -> None:
        data, _ = self._run(
            "v1.0.0", ["tool-x64.zip", "tool-arm64.zip"], bin="bin/t.exe",
            archives={
                "tool-x64.zip": (None, "a.exe"),
                "tool-arm64.zip": (None, "b.exe"),
            },
        )
        self.assertEqual(data["bin"], "bin/t.exe")

    def test_digit_in_the_tag_name_warns(self) -> None:
        data, err = self._run("win32-v1.2.3", ["tool.zip"])
        self.assertIn("first digit", err)

    def test_seed_default_artifact_is_always_64bit(self) -> None:
        for token in ("win32-disk-imager", "arm-tool", "arm64-foo"):
            with self.subTest(token=token):
                args = argparse.Namespace(
                    repo="o/r", name=token, seed=True, artifact=None,
                    extract_dir=None, bin="tool.exe",
                )
                written = {}

                def fake_write(name: str, data: dict) -> Path:
                    written["data"] = data
                    return Path(f"bucket/{name}.json")

                with (
                    mock.patch.object(am, "fetch_json", return_value=self.META),
                    mock.patch.object(am, "_write_manifest", side_effect=fake_write),
                    mock.patch("sys.stdout", io.StringIO()),
                    mock.patch("sys.stderr", io.StringIO()),
                ):
                    am.add_binary(args)
                self.assertEqual(list(written["data"]["architecture"]), ["64bit"])

    def test_seed_classifies_repeated_artifacts(self) -> None:
        args = argparse.Namespace(
            repo="o/r", name="tool", seed=True,
            artifact=["tool-x64.zip", "tool-arm64.zip"],
            extract_dir=None, bin="tool.exe",
        )
        written = {}

        def fake_write(name: str, data: dict) -> Path:
            written["data"] = data
            return Path(f"bucket/{name}.json")

        with (
            mock.patch.object(am, "fetch_json", return_value=self.META),
            mock.patch.object(am, "_write_manifest", side_effect=fake_write),
            mock.patch("sys.stdout", io.StringIO()),
            mock.patch("sys.stderr", io.StringIO()),
        ):
            am.add_binary(args)
        data = written["data"]
        self.assertEqual(list(data["architecture"]), ["64bit", "arm64"])
        self.assertEqual(data["architecture"]["arm64"]["hash"], "0" * 64)
        self.assertEqual(
            data["autoupdate"]["architecture"]["arm64"]["url"],
            "https://github.com/o/r/releases/download/v$version/tool-arm64.zip",
        )


if __name__ == "__main__":
    unittest.main()
