"""Locate the APM project and normalize Windows and Git-Bash paths."""
from __future__ import annotations

import ntpath
import posixpath
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_GIT_BASH_DRIVE = re.compile(r"^/([A-Za-z])(?:/|$)")
_DRIVE = re.compile(r"^[A-Za-z]:/")


@dataclass(frozen=True)
class Project:
    main_root: Path
    worktree_root: Path

    @property
    def profile_path(self) -> Path:
        """The first profile that exists: this checkout's, the main checkout's, then the
        mirror on the state branch. With none, this checkout's (and not initialized)."""
        candidates = (
            self.worktree_root / ".apm" / "profile.json",
            self.main_root / ".apm" / "profile.json",
            self.state_dir / "profile.json",
        )
        return next((path for path in candidates if path.exists()), candidates[0])

    @property
    def state_dir(self) -> Path:
        return self.main_root / ".apm" / "state"

    @property
    def ledger_path(self) -> Path:
        return self.state_dir / "ledger.json"

    @property
    def is_initialized(self) -> bool:
        return self.profile_path.exists()


def _git(cwd: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False
        )
    except (OSError, ValueError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def find_project(cwd: Path) -> Project | None:
    top = _git(cwd, "rev-parse", "--show-toplevel")
    common = _git(cwd, "rev-parse", "--git-common-dir")
    if not top or not common:
        return None
    main_root = (Path(cwd) / common).resolve().parent
    return Project(main_root=main_root, worktree_root=Path(top).resolve())


def _windows_form(raw: str) -> str:
    text = raw.replace("\\", "/")
    return _GIT_BASH_DRIVE.sub(lambda m: m.group(1).upper() + ":/", text, count=1)


def _windows_path(raw: str, cwd: Path) -> str:
    text = _windows_form(raw)
    if not (_DRIVE.match(text) or text.startswith("/")):
        text = _windows_form(str(cwd)).rstrip("/") + "/" + text
    out = ntpath.normpath(text).replace("\\", "/")
    return out[0].upper() + out[1:] if _DRIVE.match(out) else out


def to_native_path(raw: str, cwd: Path, windows: bool) -> Path:
    if windows:
        return Path(_windows_path(raw, cwd))
    base = str(cwd).replace("\\", "/")
    return Path(posixpath.normpath(posixpath.join(base, raw)))


def worktree_relative(target: Path) -> tuple[Path, str] | None:
    for parent in Path(target).parents:
        if (parent / ".git").exists():
            return parent, Path(target).relative_to(parent).as_posix()
    return None
