#!/usr/bin/env python3
"""Scaffold a new Scoop manifest for this bucket.

Two routes cover prebuilt Windows applications and Python command-line tools:

- **binary**: package a prebuilt Windows ``.zip``
  from a GitHub release. Reads the latest release, downloads the asset to
  compute its sha256, peeks inside the archive for the wrapping folder and the
  ``.exe`` to shim, and writes ``bucket/<name>.json`` with a version-templated
  ``autoupdate`` URL and a ``checkver.github`` block. ``--seed`` writes a
  ``0.0.0`` placeholder for a repo whose Windows build doesn't exist yet.
- **shim**: package a PyPI CLI as a
  ``uv tool install`` (default) or ``pipx install`` shim. There is **no**
  dependency resolution — uv/pipx resolve the tree at install time — so the
  manifest's ``url``/``hash`` are the static ``noop.ps1`` (its hash never moves)
  and only ``version`` ever changes.

Standard library only — no third-party dependencies. Companion to
``update_manifests.py``. See the "Add a manifest" section of README.md
for usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from bucket_repository import resolve as resolve_bucket_repository
from url_fetch import get_json as fetch_json
from url_fetch import request

GITHUB_API = "https://api.github.com"
PYPI = "https://pypi.org/pypi"
# The bucket being edited, not this script's own location: the script ships in
# a plugin and runs against the checkout in the working directory (or
# --bucket-dir / SCOOP_BUCKET_DIR); `_set_bucket_root` rebinds these.
REPO = Path.cwd().resolve()
BUCKET = REPO / "bucket"

# The static placeholder every shim manifest points its `url` at. Scoop requires
# a URL + hash, but the real install is done by the installer script, so the URL
# is a no-op PowerShell file whose sha256 never changes. Keep these in sync with
# the bucket's scripts/noop.ps1. The URL is derived from the bucket's repository
# rather than baked in; its hash is calculated directly from the checked-in file.
NOOP_FILE = REPO / "scripts" / "noop.ps1"


def _set_bucket_root(root: Path) -> None:
    """Point the module at ``root``'s ``bucket/`` and ``scripts/noop.ps1``."""
    global REPO, BUCKET, NOOP_FILE
    REPO = root.resolve()
    if not (REPO / "bucket").is_dir():
        sys.exit(f"error: {REPO} has no bucket/ directory; run from a bucket "
                 "checkout or pass --bucket-dir")
    BUCKET = REPO / "bucket"
    NOOP_FILE = REPO / "scripts" / "noop.ps1"

# 64 zero hex digits: a syntactically valid placeholder sha256 for --seed mode.
# The first `scripts/update_manifests.py` run (autoupdate rewrites url + hash)
# overwrites it once the release ships the .zip.
_PLACEHOLDER_SHA = "0" * 64
_PLACEHOLDER_VERSION = "0.0.0"


@dataclass(frozen=True)
class ArchitectureSpec:
    """Values for one architecture class of a binary manifest."""

    download_url: str
    sha256: str
    extract_dir: str | None
    executable: str
    autoupdate_url: str
    autoupdate_extract_dir: str | None = None
    autoupdate_bin: str | None = None


@dataclass(frozen=True)
class BinaryManifestSpec:
    """Values required to render a binary manifest."""

    token: str
    repository_url: str
    description: str
    license_id: str
    version: str
    checkver: dict
    architectures: dict[str, ArchitectureSpec]


@dataclass(frozen=True)
class ShimManifestSpec:
    """Values required to render a PyPI shim manifest."""

    package: str
    installer: str
    description: str
    homepage: str
    license_id: str
    version: str
    noop_url: str
    noop_hash: str


def normalize(name: str) -> str:
    """Normalize a name to a Scoop manifest token (lowercase, hyphen-separated)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def clean_desc(summary: str) -> str:
    """Format an upstream summary as a manifest ``description``.

    Strips a leading article and trailing period, then capitalizes the first
    letter — matching the phrasing of the hand-written manifests in ``bucket/``.
    """
    desc = re.sub(r"^(?:A|An|The)\s+", "", (summary or "").strip().rstrip("."))
    return desc[:1].upper() + desc[1:] if desc else desc


def noop_source(repository: str, ref: str = "main") -> tuple[str, str]:
    """Return the public no-op URL and checksum used by shim manifests."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        sys.exit("error: bucket repository must be in owner/repository form")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", ref) or ".." in ref.split("/"):
        sys.exit("error: bucket ref contains unsupported characters")
    url = f"https://raw.githubusercontent.com/{repository}/{ref}/scripts/noop.ps1"
    if not NOOP_FILE.is_file():
        sys.exit(f"error: {NOOP_FILE} not found; shim manifests hash the bucket's "
                 "scripts/noop.ps1, so run from a bucket checkout or pass --bucket-dir")
    raw_bytes = NOOP_FILE.read_bytes().replace(b"\r\n", b"\n")
    sha = hashlib.sha256(raw_bytes).hexdigest()
    return url, sha


def _write_manifest(name: str, data: dict) -> Path:
    """Serialize a manifest to ``bucket/<name>.json`` (4-space indent, trailing NL)."""
    if "/" in name or "\\" in name:
        sys.exit(f"error: name {name!r} must not contain path separators")
    out = BUCKET / f"{name}.json"
    if out.exists():
        sys.exit(f"error: {out.relative_to(BUCKET.parent)} already exists; edit it "
                 "directly or pick another --name")
    out.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# binary route (GitHub release .zip → cask analogue)
# --------------------------------------------------------------------------- #
def parse_repo(ref: str) -> tuple[str, str]:
    """Parse ``owner/repo`` or a GitHub URL into an ``(owner, repo)`` pair."""
    ref = ref.strip()
    m_ssh = re.fullmatch(
        r"(?:[a-zA-Z0-9_.-]+@)?github\.com:([^/]+)/([^/#?]+?)(?:\.git)?/?", ref
    )
    if m_ssh:
        return m_ssh.group(1), m_ssh.group(2)

    if "://" in ref:
        parts = urlsplit(ref)
        if parts.hostname == "github.com":
            path = parts.path.strip("/")
            if path.endswith(".git"):
                path = path[:-4]
            segments = path.split("/")
            if len(segments) == 2 and all(segments):
                return segments[0], segments[1]
        sys.exit(f"error: cannot parse GitHub repo from {ref!r}; pass 'owner/repo' "
                 "or a github.com URL")

    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", ref):
        owner, repo = ref.split("/", 1)
        return owner, repo.removesuffix(".git")

    sys.exit(f"error: cannot parse GitHub repo from {ref!r}; pass 'owner/repo' "
             "or a github.com URL")


def spdx_license(meta: dict) -> str:
    """Best-effort SPDX license id from the GitHub repo metadata."""
    license_info = meta.get("license") or {}
    spdx = (license_info.get("spdx_id") or "").strip()
    # GitHub returns "NOASSERTION" when it can't map the LICENSE file.
    if spdx and spdx != "NOASSERTION":
        return spdx
    return "TODO-set-SPDX-license"


def group_by_architecture(names: list[str]) -> dict[str, str]:
    """Map each architecture class to the one asset name that targets it.

    Exits when a name is 32-bit ARM (Scoop has no such architecture) or when two
    names target the same class, so the caller never has to guess between them.
    """
    grouped: dict[str, list[str]] = {}
    for name in names:
        arch = classify_arch(name)
        if arch is None:
            sys.exit(f"error: {name!r} targets 32-bit ARM, which Scoop has no "
                     "architecture for; pass --artifact to choose the assets to package")
        grouped.setdefault(arch, []).append(name)
    for arch, found in grouped.items():
        if len(found) > 1:
            sys.exit(f"error: multiple assets look like {arch} builds "
                     f"({', '.join(found)}); pass --artifact once per asset to choose")
    return {arch: grouped[arch][0] for arch in ARCH_CLASSES if arch in grouped}


def select_assets(assets: list[dict], wanted: list[str] | None) -> dict[str, dict]:
    """Pick the release assets to package, keyed by architecture class.

    Honors ``--artifact`` (repeatable) or else takes every ``.zip`` asset that does
    not name another operating system.
    """
    if not assets:
        sys.exit("error: the latest release has no downloadable assets; pass --seed "
                 "to scaffold a placeholder, or --artifact once a release exists")
    by_name = {a["name"]: a for a in assets}
    if wanted:
        for name in wanted:
            if name not in by_name:
                sys.exit(f"error: no asset named {name!r}; available: "
                         f"{', '.join(by_name)}")
        names = list(wanted)
    else:
        names = [n for n in by_name
                 if n.lower().endswith(".zip") and not _NON_WINDOWS.search(n)]
        if not names:
            sys.exit("error: no Windows .zip asset found; pass --artifact to choose "
                     "one of: "
                     f"{', '.join(by_name)}")
    return {arch: by_name[name] for arch, name in group_by_architecture(names).items()}


_ARM64 = re.compile(r"arm64|aarch64", re.I)
_X64 = re.compile(r"x64|amd64|x86[-_]?64|win64", re.I)
_X86 = re.compile(r"i[3-6]86|ia32|win32|x86(?![-_]?64)|(?<!\d)386(?!\d)", re.I)
# 32-bit ARM, which Scoop has no architecture for.
_ARM32 = re.compile(
    r"aarch32|arm(?:32|hf|el)|(?<![a-z0-9])arm(?:v\d\w*)?(?![a-z0-9])", re.I)
# Archives for another operating system, skipped when assets are picked by default.
_NON_WINDOWS = re.compile(
    r"(?<![a-z0-9])(?:linux|darwin|mac(?:os)?|osx|apple|freebsd|netbsd|openbsd|android)"
    r"(?![a-z0-9])", re.I)
ARCH_CLASSES = ("64bit", "32bit", "arm64")


def classify_arch(asset_name: str) -> str | None:
    """Return the architecture class an asset name targets, or None for 32-bit ARM.

    A name with no architecture marker counts as ``64bit``. An explicit x64 marker
    outranks a 32-bit one, so ``tool-win32-x64.zip`` is ``64bit``.
    """
    if _ARM64.search(asset_name):
        return "arm64"
    if _X64.search(asset_name):
        return "64bit"
    if _X86.search(asset_name):
        return "32bit"
    if _ARM32.search(asset_name):
        return None
    return "64bit"


def download_zip(url: str) -> str:
    """Download a release asset to a temp file and return its path (caller unlinks)."""
    print(f"==> Downloading {url} to compute sha256 and inspect the archive",
          file=sys.stderr)
    fd, tmp = tempfile.mkstemp(suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as out:
            with urllib.request.urlopen(  # noqa: S310
                request(url, accept="application/octet-stream"), timeout=30
            ) as resp:
                for chunk in iter(lambda: resp.read(1 << 20), b""):
                    out.write(chunk)
    except Exception:
        os.unlink(tmp)
        raise
    return tmp


def sha256_of_file(path: str) -> str:
    """Return the sha256 of a file, reading it in bounded chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_zip(path: str, token: str) -> tuple[str | None, str | None, str]:
    """Infer ``(extract_dir, bin, hint)`` by peeking inside the downloaded archive.

    ``extract_dir`` is the single wrapping folder every entry shares (Scoop strips
    it), or None. ``bin`` is the ``.exe`` to shim: the lone executable, else the
    one whose stem matches ``token``, else None (the caller must be told via
    ``--bin``). ``hint`` warns when either was guessed.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n and not n.endswith("/")]
    except zipfile.BadZipFile as exc:
        sys.exit(f"error: downloaded archive is not a valid .zip: {exc}")

    tops = {n.split("/", 1)[0] for n in names}
    nested = any("/" in n for n in names)
    extract_dir = tops.pop() if len(tops) == 1 and nested else None

    exes = [n for n in names if n.lower().endswith(".exe")]

    def _rel(entry: str) -> str:
        # Scoop strips `extract_dir`, so `bin` must be the executable's path
        # relative to that wrapper — not just its basename. `widget/widget.exe`
        # -> `widget.exe`, but `tool/bin/tool.exe` -> `bin/tool.exe`.
        if extract_dir and entry.startswith(f"{extract_dir}/"):
            return entry[len(extract_dir) + 1:]
        return entry

    def _hint(rel: str) -> str:
        # A nested executable yields a `bin` path with a subfolder; flag it so the
        # maintainer confirms Scoop resolves it (most bundles ship the .exe flat).
        return (f'the executable is nested ("{rel}"); verify Scoop resolves that '
                "bin path") if "/" in rel else ""

    if len(exes) == 1:
        rel = _rel(exes[0])
        return extract_dir, rel, _hint(rel)
    matches = [e for e in exes if Path(e).stem.lower() == token]
    if len(matches) == 1:
        rel = _rel(matches[0])
        return extract_dir, rel, _hint(rel)
    if not exes:
        return extract_dir, None, ("no .exe found in the archive; set --bin to the "
                                   "executable Scoop should shim")
    names_str = ", ".join(exes)
    return extract_dir, None, (f"multiple .exe entries ({names_str}); set --bin to the "
                               "one to shim")


def templatize(text: str, version: str, *, required: bool = False) -> str:
    """Replace the literal version in a URL/tag with Scoop's ``$version`` template.

    A name that never carried the version (``tool-windows.zip``) is returned as is;
    ``required`` makes that a warning, for text that must follow the release.
    """
    if not version:
        return text
    target = version
    if target not in text:
        quoted = quote(version)
        quoted_slash = quote(version, safe="")
        if quoted in text:
            target = quoted
        elif quoted_slash in text:
            target = quoted_slash
        elif quoted_slash.lower() in text:
            target = quoted_slash.lower()
        elif quoted_slash.upper() in text:
            target = quoted_slash.upper()
        else:
            if required:
                print(f"warning: version {version!r} not found in {text!r}; that part "
                      "of the URL won't auto-update on release bumps — verify the "
                      "manifest", file=sys.stderr)
            return text
    # Match the version as a whole token, not inside a longer one, so a short
    # version such as "3" leaves "win32", "armv3" and "x64" alone. A dotted
    # version is distinctive enough to follow only the digit rule.
    before = r"(?<!\d)" if "." in target else r"(?:(?<![0-9A-Za-z])|(?<=(?<![0-9A-Za-z])[vV]))"
    templated = re.sub(rf"{before}{re.escape(target)}(?!\.?\d)", "$version", text)
    if templated == text:
        print(f"warning: version {version!r} appears in {text!r} only inside a longer "
              "number; that part of the URL won't auto-update on release bumps — "
              "verify the manifest", file=sys.stderr)
    return templated


def split_tag(tag: str) -> tuple[str, str]:
    """Split a release tag into ``(tag prefix, version)`` at its first digit."""
    match = re.search(r"\d", tag)
    return (tag[:match.start()], tag[match.start():]) if match else ("", tag)


def github_checkver(repository_url: str, prefix: str) -> dict:
    """Build the ``checkver`` block; add a regex unless Scoop's default reads the tag.

    The default reads an optional ``v`` or ``V``, but the bucket's updater strips only
    a lowercase ``v``, so anything but ``v`` and no prefix gets an explicit regex.
    """
    checkver = {"github": repository_url}
    if prefix not in ("", "v"):
        literal = re.sub(r"([.^$*+?{}\[\]\\|()])", r"\\\1", prefix)
        # A slash may reach the releases page percent-encoded.
        literal = literal.replace("/", "(?:/|%2[Ff])")
        # Scoop applies the regex to the tag name (API mode) or to the whole releases
        # page (HTML mode), so anchor it to the tag link or the start of the tag.
        checkver["regex"] = f"(?:/releases/tag/|^){literal}([\\d.-]+)"
    return checkver


def _url_forms(text: str) -> set[str]:
    """The spellings of ``text`` a GitHub download URL may carry."""
    full = quote(text, safe="")
    lowered = re.sub(r"%[0-9A-F]{2}", lambda m: m.group().lower(), full)
    return {text, quote(text), full, lowered}


def _templatize_tag(tag_part: str, prefix: str, version: str) -> str:
    """Fill the version slot in a URL's tag segment, keeping the tag prefix literal."""
    for spelled_prefix in _url_forms(prefix):
        if (tag_part.startswith(spelled_prefix)
                and tag_part[len(spelled_prefix):] in _url_forms(version)):
            return f"{spelled_prefix}$version"
    return templatize(tag_part, version, required=True)


def render_binary(spec: BinaryManifestSpec) -> dict:
    """Build an ordered binary manifest.

    ``bin`` and ``shortcuts`` stay top-level while every architecture shims the same
    executable, and move into each architecture block once they differ.
    """
    archs = spec.architectures
    shared_bin = (len({a.executable for a in archs.values()}) == 1
                  and len({a.autoupdate_bin for a in archs.values()}) == 1)
    first = next(iter(archs.values()))
    manifest_archs: dict = {}
    autoupdate_archs: dict = {}
    for name, arch in archs.items():
        block: dict = {"url": arch.download_url, "hash": arch.sha256}
        if arch.extract_dir:
            block["extract_dir"] = arch.extract_dir
        autoupdate_block: dict = {"url": arch.autoupdate_url}
        if arch.autoupdate_extract_dir:
            autoupdate_block["extract_dir"] = arch.autoupdate_extract_dir
        if not shared_bin:
            block["bin"] = arch.executable
            block["shortcuts"] = [[arch.executable, spec.token]]
            if arch.autoupdate_bin:
                autoupdate_block["bin"] = arch.autoupdate_bin
                autoupdate_block["shortcuts"] = [[arch.autoupdate_bin, spec.token]]
        manifest_archs[name] = block
        autoupdate_archs[name] = autoupdate_block
    autoupdate: dict = {"architecture": autoupdate_archs}
    if shared_bin and first.autoupdate_bin:
        autoupdate["bin"] = first.autoupdate_bin
        autoupdate["shortcuts"] = [[first.autoupdate_bin, spec.token]]
    data: dict = {
        "version": spec.version,
        "description": spec.description,
        "homepage": spec.repository_url,
        "license": spec.license_id,
        "architecture": manifest_archs,
    }
    if shared_bin:
        data["bin"] = first.executable
        data["shortcuts"] = [[first.executable, spec.token]]
    data["checkver"] = spec.checkver
    data["autoupdate"] = autoupdate
    return data


def _templated_or_none(text: str | None, version: str) -> str | None:
    """Return ``text`` with its version slots filled, or None when it has none."""
    if not text:
        return None
    templated = templatize(text, version)
    return templated if templated != text else None


def _architecture_spec(*, download_url: str, sha256: str, extract_dir: str | None,
                       executable: str, autoupdate_url: str,
                       version: str) -> ArchitectureSpec:
    return ArchitectureSpec(
        download_url=download_url,
        sha256=sha256,
        extract_dir=extract_dir,
        executable=executable,
        autoupdate_url=autoupdate_url,
        autoupdate_extract_dir=_templated_or_none(extract_dir, version),
        autoupdate_bin=_templated_or_none(executable, version),
    )


def _release_architecture(asset: dict, prefix: str, version: str, token: str,
                          args: argparse.Namespace) -> tuple[ArchitectureSpec, str]:
    """Download one release asset and build its architecture spec and hint."""
    tmp = download_zip(asset["browser_download_url"])
    try:
        sha = sha256_of_file(tmp)
        found_dir, found_exe, hint = inspect_zip(tmp, token)
    finally:
        os.unlink(tmp)
    extract_dir = args.extract_dir or found_dir
    exe = args.bin
    if not exe and found_exe:
        full_exe = f"{found_dir}/{found_exe}" if found_dir else found_exe
        if extract_dir:
            if full_exe.startswith(f"{extract_dir}/"):
                exe = full_exe[len(extract_dir) + 1:]
            elif args.extract_dir:
                sys.exit(f"error: inferred executable '{full_exe}' is outside "
                         f"--extract-dir '{extract_dir}'; pass --bin")
            else:
                exe = full_exe
        else:
            exe = full_exe
    if not exe:
        sys.exit(f"error: {hint or 'could not determine the executable'}")
    concrete_url = asset["browser_download_url"]
    parts = urlsplit(concrete_url)
    path_prefix, sep, rest = parts.path.partition("/releases/download/")
    if sep:
        tag_part, slash, artifact_part = rest.rpartition("/")
        templated_tag = _templatize_tag(tag_part, prefix, version)
        templated_artifact = templatize(artifact_part, version)
        autoupdate_path = f"{path_prefix}{sep}{templated_tag}{slash}{templated_artifact}"
        autoupdate_url = urlunsplit(
            (parts.scheme, parts.netloc, autoupdate_path, parts.query, parts.fragment)
        )
    else:
        autoupdate_url = templatize(concrete_url, version, required=True)
    return _architecture_spec(
        download_url=concrete_url, sha256=sha, extract_dir=extract_dir,
        executable=exe, autoupdate_url=autoupdate_url, version=version,
    ), hint


def _seed_architecture(owner: str, repo: str, artifact: str,
                       args: argparse.Namespace) -> ArchitectureSpec:
    """Build a placeholder architecture spec from this bucket's conventions."""
    version = _PLACEHOLDER_VERSION
    base = f"https://github.com/{owner}/{repo}/releases/download"
    # A filename that carries the placeholder version must follow the release.
    return _architecture_spec(
        download_url=f"{base}/v{version}/{artifact}",
        sha256=_PLACEHOLDER_SHA,
        extract_dir=args.extract_dir,
        executable=args.bin,
        autoupdate_url=f"{base}/v$version/{templatize(artifact, version)}",
        version=version,
    )


def add_binary(args: argparse.Namespace) -> None:
    owner, repo = parse_repo(args.repo)
    token = normalize(args.name or repo)
    try:
        meta = fetch_json(f"{GITHUB_API}/repos/{owner}/{repo}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            sys.exit(f"error: repo {owner}/{repo} not found")
        raise
    repo_url = meta.get("html_url") or f"https://github.com/{owner}/{repo}"
    desc = clean_desc(meta.get("description") or "TODO-set-description")
    license_id = spdx_license(meta)
    hints: list[tuple[str, str]] = []

    if args.seed:
        # No release to introspect: assume this bucket's conventions (a `v<version>`
        # tag and a static asset name) and template a URL the first bump can fill.
        if not args.bin:
            sys.exit("error: --seed can't inspect the archive; pass --bin <name>.exe "
                     "(and --extract-dir if the zip wraps its contents in a folder)")
        version, prefix = _PLACEHOLDER_VERSION, "v"
        # The default name is ours, so its architecture is not read from the token.
        artifacts = (group_by_architecture(args.artifact) if args.artifact
                     else {"64bit": f"{token}-windows.zip"})
        architectures = {arch: _seed_architecture(owner, repo, artifact, args)
                         for arch, artifact in artifacts.items()}
        guesses = "\n".join(
            f"      {arch}: tag v$version   artifact: "
            f"{templatize(artifact, version)}" for arch, artifact in artifacts.items())
        print("==> Seeding placeholder manifest. VERIFY these guessed conventions "
              f"against the first real release:\n{guesses}\n"
              "    update_manifests.py refreshes only version + hash from this URL; "
              "it can't fix a wrong tag/filename pattern.", file=sys.stderr)
    else:
        try:
            release = fetch_json(f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                sys.exit(f"error: {owner}/{repo} has no published 'latest' release; "
                         "use --seed to scaffold a placeholder for the first release")
            raise
        tag = release["tag_name"]
        prefix, version = split_tag(tag)
        if prefix not in ("", "v"):
            print(f"warning: release tag {tag!r} has the prefix {prefix!r}, so the "
                  f"manifest gets a checkver.regex that reads version {version!r}; the "
                  "bucket's updater (scripts/update_manifests.py) ignores "
                  "checkver.regex and strips only a lowercase v, so until it honours "
                  f"the regex it computes {tag!r} on every bump", file=sys.stderr)
        if not re.fullmatch(r"[\d.-]+", version):
            print(f"warning: version {version!r} has characters beyond digits, dots "
                  "and dashes, which Scoop's github checkver cannot capture. The tag "
                  "is split at its first digit, so a digit in the tag's own name "
                  "(win32-v1.2.3) lands in the version; adjust checkver by hand "
                  "before merging", file=sys.stderr)
        architectures = {}
        for arch, asset in select_assets(release.get("assets", []), args.artifact).items():
            spec, hint = _release_architecture(asset, prefix, version, token, args)
            architectures[arch] = spec
            hints.append((arch, hint))

    data = render_binary(
        BinaryManifestSpec(
            token=token,
            repository_url=repo_url,
            description=desc,
            license_id=license_id,
            version=version,
            checkver=github_checkver(repo_url, prefix),
            architectures=architectures,
        )
    )
    out = _write_manifest(token, data)
    print(f"==> Wrote {out.parent.name}/{out.name} (binary, version {version})")
    for arch, hint in hints:
        if hint:
            print(f"warning: {arch}: {hint}" if len(hints) > 1 else f"warning: {hint}",
                  file=sys.stderr)
    _binary_next_steps(token, architectures)


def _binary_next_steps(token: str, architectures: dict[str, ArchitectureSpec]) -> None:
    print(f"\nNext: verify the manifest, then `scoop install <bucket>/{token}` on "
          "Windows.", file=sys.stderr)
    print("      Run `mise run generate-readme` before committing.", file=sys.stderr)
    flat = [arch for arch, spec in architectures.items() if spec.extract_dir is None]
    if flat:
        print(f"      No extract_dir was set for {', '.join(flat)} (archive has no "
              "single wrapping folder) — confirm the .exe sits at the archive root.",
              file=sys.stderr)
    exes = ", ".join(dict.fromkeys(spec.executable for spec in architectures.values()))
    print(f"      Shimming bin: {exes}. Add a smoke-test command to tests.yml if it "
          f"isn't `{token} version`.", file=sys.stderr)


# --------------------------------------------------------------------------- #
# shim route (PyPI package → formula analogue)
# --------------------------------------------------------------------------- #
def pypi_info(package: str) -> dict:
    """Return the ``info`` block of a PyPI package's latest release."""
    try:
        data = fetch_json(f"{PYPI}/{package}/json")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            sys.exit(f"error: PyPI package {package!r} not found")
        raise
    if "info" not in data:
        sys.exit(f"error: PyPI response for {package!r} missing 'info' field")
    return data["info"]


def pypi_homepage(info: dict, package: str) -> str:
    """Best-effort project homepage, preferring an explicit repo/homepage URL.

    ``project_urls`` labels vary in case across packages, so lowercase for
    case-insensitive matching. Prefer the homepage, then the source/repository
    (``.git`` stripped so it reads as a browsable URL like hand-written manifests).
    """
    urls = {key.lower(): value for key, value in (info.get("project_urls") or {}).items()}
    for key in ("homepage", "repository", "source", "source code"):
        if urls.get(key):
            return urls[key].removesuffix(".git")
    return info.get("home_page") or f"https://pypi.org/project/{package}/"


def pypi_license(info: dict) -> str:
    """Best-effort SPDX license from the PEP 639 expression or a short license field."""
    expression = (info.get("license_expression") or "").strip()
    if expression:
        return expression
    raw = (info.get("license") or "").strip()
    if raw and len(raw) <= 40 and "\n" not in raw:
        return raw
    return "TODO-set-SPDX-license"


def render_shim(spec: ShimManifestSpec) -> dict:
    """Build an ordered PyPI shim manifest."""
    return {
        "version": spec.version,
        "description": spec.description,
        "homepage": spec.homepage,
        "license": spec.license_id,
        "depends": spec.installer,
        "url": spec.noop_url,
        "hash": spec.noop_hash,
        "installer": {
            "script": (
                f"uv tool install {spec.package}==$version --force"
                if spec.installer == "uv"
                else f"pipx ensurepath; pipx install {spec.package}==$version --force"
            )
        },
        "uninstaller": {
            "script": f"uv tool uninstall {spec.package}"
            if spec.installer == "uv"
            else f"pipx uninstall {spec.package}"
        },
        "checkver": {"url": f"https://pypi.org/pypi/{spec.package}/json",
                     "jsonpath": "$.info.version"},
        "autoupdate": {"url": spec.noop_url},
    }


def add_shim(args: argparse.Namespace) -> None:
    via = args.via
    info = pypi_info(args.package)
    package = normalize(info.get("name") or args.package)
    version = info["version"]
    # uv shims take the bare tool name; a pipx shim usually coexists with a
    # same-named binary manifest, so it gets a `-pipx` suffix.
    default_name = package if via == "uv" else f"{package}-pipx"
    token = normalize(args.name or default_name)
    suffix = " (uv tool install)" if via == "uv" else " (pipx install)"
    desc = clean_desc(info.get("summary") or "TODO-set-description") + suffix
    homepage = args.homepage or pypi_homepage(info, package)
    license_id = pypi_license(info)

    repository = args.bucket_repository or resolve_bucket_repository(REPO)
    if not repository:
        sys.exit("error: cannot infer this bucket's GitHub repository; pass "
                 "--bucket-repository owner/repository or set "
                 "SCOOP_BUCKET_REPOSITORY")
    noop_url, noop_hash = noop_source(repository, args.bucket_ref)
    data = render_shim(
        ShimManifestSpec(
            package=package,
            installer=via,
            description=desc,
            homepage=homepage,
            license_id=license_id,
            version=version,
            noop_url=noop_url,
            noop_hash=noop_hash,
        )
    )
    out = _write_manifest(token, data)
    print(f"==> Wrote {out.parent.name}/{out.name} ({via} shim, version {version})")
    print(f"\nNext: run `mise run generate-readme`, then `mise run style`. "
          f"If the CLI's smoke-test isn't `{package} version`, add it to the map in "
          ".github/workflows/tests.yml.", file=sys.stderr)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--bucket-dir",
        default=os.environ.get("SCOOP_BUCKET_DIR"),
        help="bucket checkout to edit (default: SCOOP_BUCKET_DIR or the current directory)",
    )
    sub = parser.add_subparsers(dest="route", required=True)

    binary = sub.add_parser(
        "binary", help="package a prebuilt Windows .zip from a GitHub release")
    binary.add_argument("repo", help="GitHub repo as 'owner/repo' or a github.com URL")
    binary.add_argument("--name", help="manifest token (default: normalized repo name)")
    binary.add_argument("--bin", help="the .exe to shim (default: inferred from the zip)")
    binary.add_argument("--extract-dir",
                        help="wrapping folder Scoop strips (default: inferred from the zip)")
    binary.add_argument("--artifact", action="append",
                        help="release asset filename to package, once per architecture "
                             "(default: every .zip, classified by its name)")
    binary.add_argument("--seed", action="store_true",
                        help="write a 0.0.0 placeholder without downloading (requires --bin)")
    binary.set_defaults(func=add_binary)

    shim = sub.add_parser(
        "shim", help="package a PyPI CLI as a uv-tool (default) or pipx shim")
    shim.add_argument("package", help="PyPI package name")
    shim.add_argument("--via", choices=("uv", "pipx"), default="uv",
                      help="installer backend (default: uv)")
    shim.add_argument("--name",
                      help="manifest token (default: <package>, or <package>-pipx for pipx)")
    shim.add_argument("--homepage", help="override the homepage URL")
    shim.add_argument(
        "--bucket-repository",
        help="GitHub owner/repository hosting noop.ps1 (default: infer from origin)",
    )
    shim.add_argument(
        "--bucket-ref",
        default=os.environ.get("SCOOP_BUCKET_REF", "main"),
        help="Git ref serving noop.ps1 (default: SCOOP_BUCKET_REF or main)",
    )
    shim.set_defaults(func=add_shim)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    _set_bucket_root(Path(args.bucket_dir) if args.bucket_dir else Path.cwd())
    args.func(args)


if __name__ == "__main__":
    main()
