#!/usr/bin/env python3
"""Regenerate agent instructions and skills from ``.ai-rulez/``.

``.ai-rulez/`` is the single source; ``ai-rulez generate`` renders it into
``AGENTS.md``, ``.claude/skills/``, and ``.agents/skills/``. Those outputs are
committed (``.gitignore`` lists only machine-local files), so this wrapper keeps them
reproducible with a render-and-promote flow: ai-rulez owns rendering, the
wrapper owns packaging and drift checks.

- Render into a staging copy, so the side files the presets always write
  (``CLAUDE.md`` and ``GEMINI.md`` would duplicate ``AGENTS.md``, which Claude
  Code and Antigravity read) never touch the checkout. ai-rulez offers no
  switch to turn them off — native ``generate --check`` reports them as
  missing, which is why this wrapper keeps its own ``--check``.
- Promote (the default mode) copies the rendered files over and removes owned
  files the previous render produced but the fresh one no longer lists, so
  deleting a canonical skill removes its generated copies. Promotion refuses
  to write through symlinks and installs every file with an atomic rename
  that preserves modes, so hard links and crashes cannot corrupt shared or
  partial outputs.
  Dropped side files are neither promoted nor deleted by promote: a
  hand-written ``CLAUDE.md`` would shadow ``AGENTS.md`` for the agent that
  reads it, so ``--check`` reports it instead of vaporizing it. A previously
  generated file outside the owned sets is reported as orphaned rather than
  removed, since the maintainer may have adopted it by hand.
- ``--check`` renders into staging and compares it with the working tree, so a
  stale, missing, hand-edited, or unwanted output fails without modifying files.

Standard library only; requires the ``ai-rulez`` binary from ``mise install``.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

REPO = Path(__file__).resolve().parent.parent
CONFIG_DIR = ".ai-rulez"
MANIFEST = f"{CONFIG_DIR}/.generated-manifest.json"
# Preset side files that must never reach the checkout: root duplicates of
# AGENTS.md. (ai-rulez stopped emitting .agents/settings.json under
# `[mcp] self_server = false` + `--no-self-mcp`; if it ever returns it rides
# the manifest like any other output instead of being silently dropped.)
DROPPED = ("CLAUDE.md", "GEMINI.md")
# Directories owned entirely by generation; any other file in them is stale.
# Only skills/ under .claude/, since .claude/ also holds local user settings.
OWNED_DIRS = (".claude/skills", ".agents")
# Root files only generation writes; one the config stops producing is stale.
OWNED_FILES = ("AGENTS.md",)


def find_binary() -> str:
    """Return the ``ai-rulez`` binary path or exit with a pointer to mise."""
    binary = shutil.which("ai-rulez")
    if binary is None:
        sys.exit("ai-rulez not found on PATH; run `mise install` first.")
    return binary


def render(source_root: Path, staging: Path) -> None:
    """Render ``source_root``'s config into ``staging`` and post-process it."""
    # v5 reads only config.toml (migrated from config.yaml); keep the yaml
    # fallback so the script still works on a pre-migration checkout.
    config = staging / CONFIG_DIR / "config.toml"
    shutil.copytree(source_root / CONFIG_DIR, staging / CONFIG_DIR)
    if not config.is_file():
        config = staging / CONFIG_DIR / "config.yaml"
    # Outputs land next to the -C config, but the mise shim resolves the
    # toolchain from the working directory: run from the source root so the
    # project's pinned ai-rulez is used even when the caller invoked this
    # script under a bare environment (a temp cwd would fall back to whatever
    # the ambient mise config provides).
    subprocess.run(
        [
            find_binary(),
            "generate",
            "--quiet",
            "--no-self-mcp",
            "--strict-config",
            "-C",
            str(config),
        ],
        cwd=source_root,
        check=True,
    )
    drop_unwanted(staging)
    add_codex_metadata(staging)


def add_codex_metadata(root: Path) -> None:
    """Publish each skill's ``agents/openai.yaml`` beside its Codex copy.

    ai-rulez copies only SKILL.md and references/, so the OpenAI display
    metadata would otherwise exist only under ``.ai-rulez/`` and Codex users of
    ``.agents/skills/`` would lose it. The copies join the manifest so they are
    owned, checked, and removed like every other output.
    """
    added = []
    for src in sorted((root / CONFIG_DIR / "skills").glob("*/agents/openai.yaml")):
        rel = f".agents/skills/{src.parent.parent.name}/agents/openai.yaml"
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        added.append(rel)
    manifest = root / MANIFEST
    if not added or not manifest.is_file():
        return
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["files"] = sorted({*data.get("files", []), *added})
    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def drop_unwanted(root: Path) -> None:
    """Delete the unwanted outputs and remove them from the generation manifest."""
    for rel in DROPPED:
        (root / rel).unlink(missing_ok=True)
    # v5 also writes machine-local digests here; they are never committed
    # (.gitignore lists it), and the
    # committed manifest plus per-file Content-Hash lines are enough to verify
    # ownership without it.
    (root / CONFIG_DIR / ".generated-manifest.local.json").unlink(missing_ok=True)
    manifest = root / MANIFEST
    if not manifest.is_file():
        return
    data = json.loads(manifest.read_text(encoding="utf-8"))
    files = data.get("files", [])
    kept = [f for f in files if f not in DROPPED]
    if kept != files:
        data["files"] = kept
        # LF on every platform: .gitattributes checks it out as LF, and a CRLF
        # render on Windows would make --check report it as stale.
        manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def expected_files(root: Path) -> set[str]:
    """Return every output path recorded in ``root``'s manifest, plus the manifest."""
    data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    files = data.get("files", [])
    for rel in files:
        validate_manifest_rel(rel)
    return {*files, MANIFEST}


def validate_manifest_rel(rel: str) -> None:
    """Refuse a manifest entry that could escape the repository.

    ``sync()`` joins each entry onto the staging and checkout roots, and
    ``check_no_symlink()`` only guards link redirection, so an absolute
    path or a ``..`` parent reference would read and atomically overwrite
    a file outside the checkout. The manifest is rendered from repo config
    and must only ever name files beneath the root. Anchors and drives are
    judged with both POSIX and Windows semantics: on Windows a rooted path
    such as ``\\outside.md`` resets the join to the drive root and a
    drive-relative path such as ``D:outside.md`` switches drives, yet
    neither counts as absolute there.
    """
    posix = PurePosixPath(rel)
    windows = PureWindowsPath(rel)
    if (
        not rel
        or posix.anchor
        or windows.anchor
        or windows.drive
        or ".." in posix.parts
        or ".." in windows.parts
    ):
        sys.exit(f"error: refusing manifest entry escaping the repository: {rel!r}")


def owned_files(root: Path) -> set[str]:
    """Return every generation-owned file currently present under ``root``.

    Links count by themselves, never by their targets: a broken symlink at
    a previously generated path is still a stale output to remove, and one
    squatting elsewhere in an owned tree is still a leftover to report.
    Junctions count too: ``is_file()`` misses them, so ``is_link()`` backs
    both predicates. Entries beneath a linked directory are excluded: they
    live outside the checkout, and listing them under repo paths would
    attribute foreign content (or removals) to the tree.
    """
    found = {
        rel
        for rel in OWNED_FILES
        if (root / rel).is_file() or is_link(root / rel)
    }
    for owned in OWNED_DIRS:
        base = root / owned
        if is_link(base):
            # The owned root itself is a link: no manifest lists it and no
            # expected path descends under it anymore, yet it can still
            # expose outside content. Report it as a leftover; removal stays
            # manual, as with any other adopted path.
            found.add(owned)
        elif base.is_dir():
            for p in base.rglob("*"):
                rel = p.relative_to(root).as_posix()
                if (p.is_file() or is_link(p)) and link_ancestor(root, rel) is None:
                    found.add(rel)
    return found


def is_link(path: Path) -> bool:
    """True for symlinks and Windows directory junctions (reparse points).

    ``Path.is_symlink()`` misses junctions, but promotion must refuse both:
    either one would redirect writes outside the checkout. ``os.path``
    exposes junctions from Python 3.12 on; older interpreters fall back to
    symlinks alone.
    """
    if path.is_symlink():
        return True
    isjunction = getattr(os.path, "isjunction", None)
    return bool(isjunction is not None and isjunction(path))


def check_no_symlink(repo: Path, rel: str) -> None:
    """Refuse a promotion target under a symlinked or junctioned directory.

    ``mkdir`` and path traversal would otherwise follow the link and touch
    files outside the checkout. Only ancestors are checked: the final
    component itself is always replaced or unlinked, and the atomic rename
    and unlink never follow it, so links at expected or stale paths heal
    instead of bricking the run.
    """
    current = repo
    for part in Path(rel).parts[:-1]:
        current = current / part
        if is_link(current):
            sys.exit(f"error: refusing to promote through symlink: {current}")


def atomic_copyfile(src: Path, dest: Path) -> None:
    """Copy ``src`` over ``dest`` atomically, preserving the file mode.

    The content goes to a fresh temporary file in the destination directory
    that is renamed over the target, so a hard-linked destination gains its
    own inode instead of corrupting the shared one, a symlinked destination
    is replaced rather than followed, and a crash never leaves a truncated
    file behind.
    """
    fd, tmp = tempfile.mkstemp(
        dir=str(dest.parent), prefix=".gen-agents-", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as out, open(src, "rb") as src_file:
            shutil.copyfileobj(src_file, out, 1 << 20)
        shutil.copymode(src, tmp)
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def exec_bit_differs(src: Path, dest: Path) -> bool:
    """True when the owner-execute bits differ (POSIX only; promote mirrors modes)."""
    if os.name != "posix":
        return False
    src_exec = bool(stat.S_IMODE(os.stat(src).st_mode) & 0o100)
    dest_exec = bool(stat.S_IMODE(os.stat(dest).st_mode) & 0o100)
    return src_exec != dest_exec


def link_ancestor(repo: Path, rel: str) -> str | None:
    """Return the nearest ancestor of ``rel`` under ``repo`` that is a link, if any.

    Comparisons through a redirected parent are meaningless: every check
    would read the link target outside the checkout while reporting on the
    checkout path.
    """
    current = repo
    for part in Path(rel).parts[:-1]:
        current = current / part
        if is_link(current):
            return current.relative_to(repo).as_posix()
    return None


def remove_stale(path: Path) -> None:
    """Remove a stale output without following links.

    Plain unlink handles files and file links, but detaching a directory
    link (a Windows junction) needs directory removal instead; either way
    only the link itself goes, never its target. Absent paths are fine.
    """
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except (PermissionError, IsADirectoryError):
        if not is_link(path):
            raise
        os.rmdir(path)


def same_known_file(repo: Path, rel: str, known: set[str]) -> bool:
    """True when ``repo/rel`` is the same filesystem object as a known path.

    Identity, not spelling: on a case-insensitive filesystem a case-only
    rename resolves to the previously recorded file, while on POSIX two
    spellings are two files. Missing sides never match. Only alternate
    case spellings of the same pathname count: a link pointing at a known
    file (symlink or hard link) must not confer ownership, so candidates
    are restricted to the same pathname ignoring case, neither side may
    be a link, and multi-link inodes (hard links) never count as a
    case-only filesystem alias.
    """
    dest = repo / rel
    if is_link(dest):
        return False
    wanted = rel.casefold()
    for other in known:
        if other.casefold() != wanted:
            continue
        other_path = repo / other
        if is_link(other_path):
            continue
        try:
            if os.path.samefile(dest, other_path):
                try:
                    if (
                        os.stat(dest).st_nlink > 1
                        or os.stat(other_path).st_nlink > 1
                    ):
                        continue
                except OSError:
                    continue
                return True
        except OSError:
            continue
    return False


def find_case_variant(parent: Path, name: str) -> Path | None:
    """Return a real subdirectory of ``parent`` that ``name`` resolves to.

    Only real directories qualify: links are refused in preflight, and a
    file variant means a transition the stale cleanup (or refusal) already
    handled. An exact-cased entry (or none resolving at all) yields None.
    """
    wanted = parent / name
    try:
        entries = list(parent.iterdir())
    except OSError:
        return None
    if any(entry.name == name for entry in entries):
        return None
    for entry in entries:
        if entry.is_dir() and not is_link(entry):
            try:
                if os.path.samefile(entry, wanted):
                    return entry
            except OSError:
                continue
    return None


def ensure_cased_dir(repo: Path, rel: str) -> None:
    """Create the parent chain of ``rel`` under ``repo`` with staged casing.

    On case-insensitive filesystems a plain existence check resolves either
    spelling, so ``mkdir(exist_ok=True)`` would reuse a stale-cased
    directory that breaks case-sensitive checkouts (the manifest names the
    new spelling, local comparison resolves either way, Linux CI reports it
    missing). Rename the resolving variant to the staged spelling instead.
    Stale files blocking the way are already unlinked, and linked ancestors
    were refused in preflight.
    """
    current = repo
    for part in Path(rel).parts[:-1]:
        wanted = current / part
        variant = find_case_variant(current, part)
        if variant is not None:
            os.rename(variant, wanted)
        elif not wanted.is_dir() or is_link(wanted):
            wanted.mkdir(parents=True, exist_ok=True)
        current = wanted


def dir_is_fully_stale(dest: Path, repo: Path, removed: set[str]) -> bool:
    """True when everything under ``dest`` is stale-manifest-owned or nothing.

    Only then may promotion replace the directory with a generated file:
    anything else inside is hand-authored content that must be refused, not
    vaporized. Every entry counts, not just regular files: a link is owned
    only by its own recorded path (replacing it removes the link itself,
    never the target), and a subdirectory must itself be fully stale.
    """
    try:
        entries = list(dest.iterdir())
    except OSError:
        return False
    for entry in entries:
        rel = entry.relative_to(repo).as_posix()
        if is_link(entry):
            if rel not in removed:
                return False
        elif entry.is_dir():
            if not dir_is_fully_stale(entry, repo, removed):
                return False
        elif rel not in removed:
            return False
    return True


def sync(rendered: Path, repo: Path) -> list[str]:
    """Promote a staging ``rendered`` tree into ``repo``.

    Runs in two phases. First every destination is validated without writing
    anything: symlinks are refused, hand-authored collisions are refused, and
    file/directory transitions are either cleared (fully stale-manifest-owned)
    or refused. Then stale outputs are removed, files are copied, and the
    manifest replaced last, so a failure keeps the previous manifest and a
    retry recognizes the full previously generated set. Only previously
    generated files under the owned sets are ever removed; hand-added files
    stay for ``--check`` to report, and dropped side files are never touched.
    Returns the removed paths.
    """
    expected = expected_files(rendered)
    try:
        previous = expected_files(repo)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, AttributeError):
        previous = set()
    removed = sorted((previous & owned_files(repo)) - expected - set(DROPPED))
    removed_set = set(removed)
    # Ownership for the collision guard comes from the previous manifest, or
    # — when it is missing or corrupt — from location: files under the owned
    # sets are generation-owned by definition, so a lost manifest still
    # recovers instead of refusing every output as hand-authored.
    owned = owned_files(repo)
    # Retiring ownership must not silence obsolete outputs: a previously
    # generated file outside the owned sets that the fresh render drops
    # refuses the promotion until the maintainer deletes it (obsolete) or
    # moves it aside. Otherwise the manifest refresh would erase the only
    # record and every later check would pass with it still active. Identity
    # is by filesystem object, not spelling, so a case-only rename on a
    # case-insensitive filesystem is not mistaken for an orphan.
    known = expected | owned
    orphaned = sorted(
        rel
        for rel in (previous - expected - set(DROPPED) - owned)
        if os.path.lexists(repo / rel) and not same_known_file(repo, rel, known)
    )
    if orphaned:
        joined = ", ".join(orphaned)
        sys.exit(
            f"error: refusing to retire orphaned outputs: {joined}. Delete "
            "them if they are obsolete, or move them aside; generate will "
            "not drop their ownership silently."
        )
    replace_dirs: list[str] = []
    for rel in sorted(expected):
        check_no_symlink(repo, rel)
    for rel in removed:
        check_no_symlink(repo, rel)
    for rel in sorted(expected - {MANIFEST}):
        dest = repo / rel
        if (
            (dest.is_file() or is_link(dest))
            and rel not in previous
            and rel not in owned
            and not same_known_file(repo, rel, previous | owned)
            and not (
                dest.is_file()
                and filecmp.cmp(rendered / rel, dest, shallow=False)
            )
        ):
            # A new output colliding with unowned content — regular file,
            # file link, or dangling link alike — refuses instead of
            # silently replacing it. Byte-identical content promotes as a
            # no-op; previously generated and owned paths are unaffected.
            sys.exit(
                f"error: refusing to overwrite hand-authored {rel}: it is "
                "neither in the previous manifest nor under a "
                "generation-owned path, and differs from the rendered "
                "output. Move it aside and re-run, or delete it to "
                "adopt the generated file."
            )
        elif dest.is_dir() and not is_link(dest):
            if dir_is_fully_stale(dest, repo, removed_set):
                replace_dirs.append(rel)
            else:
                sys.exit(
                    f"error: cannot promote {rel}: {rel} is a directory "
                    "holding files generation does not own. Remove it and "
                    "re-run, or move its hand-authored content aside first."
                )
        elif is_link(dest) and dest.is_dir():
            # A directory link at an expected path: the atomic rename cannot
            # replace it on Windows, and following it is out of the
            # question. The owner removes the link itself (leaving the
            # target untouched) and re-runs. File links fall through to
            # the atomic copy, which swaps the link itself.
            sys.exit(
                f"error: cannot promote {rel}: {rel} is a directory link. "
                "Remove the link itself (rmdir, not del) and re-run; its "
                "target is left untouched."
            )
        parts = Path(rel).parts[:-1]
        for depth in range(1, len(parts) + 1):
            ancestor = Path(*parts[:depth]).as_posix()
            if (repo / ancestor).is_file() and ancestor not in removed_set:
                sys.exit(
                    f"error: cannot promote {rel}: parent {ancestor} is a "
                    "file generation does not own. Remove it and re-run."
                )
    for rel in replace_dirs:
        shutil.rmtree(repo / rel)
    for rel in removed:
        remove_stale(repo / rel)
    for rel in sorted(expected - {MANIFEST}):
        dest = repo / rel
        ensure_cased_dir(repo, rel)
        atomic_copyfile(rendered / rel, dest)
    dest = repo / MANIFEST
    ensure_cased_dir(repo, MANIFEST)
    atomic_copyfile(rendered / MANIFEST, dest)
    return removed


def compare(rendered: Path, repo: Path) -> list[str]:
    """Describe how ``repo``'s outputs differ from a fresh render in ``rendered``."""
    expected = expected_files(rendered)
    try:
        previous = expected_files(repo)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, AttributeError):
        previous = set()
    owned = owned_files(repo)
    problems = []
    for rel in sorted(expected):
        target = repo / rel
        redirect = link_ancestor(repo, rel)
        if redirect is not None:
            problems.append(f"redirected: {rel} via {redirect}")
        elif not target.is_file():
            problems.append(f"missing: {rel}")
        elif is_link(target):
            # Follows to matching content, but the committed artifact is a
            # link, not the rendered regular file; generate heals it.
            problems.append(f"stale: {rel}")
        elif not filecmp.cmp(rendered / rel, target, shallow=False):
            problems.append(f"stale: {rel}")
        elif exec_bit_differs(rendered / rel, target):
            problems.append(f"stale mode: {rel}")
    leftover = owned - expected - set(DROPPED)
    problems.extend(f"not generated: {rel}" for rel in sorted(leftover))
    # A previously generated file outside the owned sets (say, a Copilot
    # instruction file from a removed preset) is neither promoted nor removed:
    # the maintainer may have adopted it by hand. Report it instead of
    # silently passing with obsolete instructions active; one promote run
    # retires the report by refreshing the manifest.
    for rel in sorted(previous - expected - set(DROPPED) - owned):
        # lexists, not is_file: a broken link is still an obsolete entry,
        # and unlinking it removes the link itself, never the target.
        if os.path.lexists(repo / rel):
            problems.append(f"orphaned: {rel}")
    # A dropped file reappearing (say, a hand-written CLAUDE.md) would shadow or
    # contradict AGENTS.md for the agent that reads it. lexists, not
    # is_file: a dangling link is still a committed entry that activates
    # the moment its target appears.
    problems.extend(f"unwanted: {rel}" for rel in DROPPED if os.path.lexists(repo / rel))
    return problems


def check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        render(REPO, work)
        problems = compare(work, REPO)
    if problems:
        print("Generated agent files are out of date with .ai-rulez/:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print("Run `mise run agents:generate` and commit the result.", file=sys.stderr)
        return 1
    return 0


def generate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        render(REPO, work)
        removed = sync(work, REPO)
    for rel in removed:
        print(f"removed stale output: {rel}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if generated files differ from .ai-rulez/, without writing them",
    )
    args = parser.parse_args(argv)
    if args.check:
        return check()
    generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
