"""Resolve the GitHub repository backing this Scoop bucket."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


from urllib.parse import urlsplit


def from_remote(remote: str) -> str | None:
    """Convert a GitHub remote URL to ``owner/repository`` notation."""
    remote = remote.strip()
    m_ssh = re.fullmatch(
        r"(?:[a-zA-Z0-9_.-]+@)?github\.com:([^/]+)/([^/#?]+?)(?:\.git)?/?", remote
    )
    if m_ssh:
        return f"{m_ssh.group(1)}/{m_ssh.group(2)}"

    parts = urlsplit(remote)
    if parts.hostname == "github.com":
        path = parts.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        segments = path.split("/")
        if len(segments) == 2 and all(segments):
            return f"{segments[0]}/{segments[1]}"
    return None


def resolve(repo_root: Path) -> str | None:
    """Resolve an override or infer the repository from the ``origin`` remote."""
    if override := os.environ.get("SCOOP_BUCKET_REPOSITORY"):
        return override
    try:
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return from_remote(remote)
