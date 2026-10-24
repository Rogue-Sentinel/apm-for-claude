"""Deny a shell command that writes outside where its session may write.

A Bash or PowerShell command may write only under the main checkout, the current worktree, the temp folders and,
for the main session only, this project's memory folder (strictly under it, as for the file tools: ADR 0006). Any
other write target is outside, and `outside_write` names the first one it finds. The guard runs this check after
every other command check (the worker rules, the state directory, `check_command`), so every reason given before
it existed is still given unchanged; it only adds denials (ADR 0007).

The command is read with its message arguments masked (`mask_data`) and the bodies of heredocs no shell runs set
aside (`strip_heredoc_bodies`), then cut into its readings (`command_readings`). A Bash command is judged on the bash
reading only, since bash reads `\\"` as an escaped quote; a PowerShell command on every reading. Each reading is
judged on its own, from the command's working directory: a `cd` moves the tracked directory for the segments after it
in that reading only. A segment under a plan allowlist prefix is skipped. A device (`/dev/null`, `NUL`, `$null`) is
no file. The shell temp roots (`/tmp`) count only for a Bash command, because Git Bash mounts `/tmp` on the temp
folder while to PowerShell it is a real `C:\\tmp`; the caller leaves them out of `Reach.temp_roots` for PowerShell.
A leading `~`, `$HOME`, `${HOME}`, `$USERPROFILE`, `${USERPROFILE}`, `$env:HOME`, `$env:USERPROFILE` or
`${env:USERPROFILE}`, in any case, names the home folder. A word that ends in a separator (`cp notes.md <memory>/`)
names a folder written into, and is judged as a path inside it.

Known limits: every limit `guard_targets` names (writes a program makes itself, script blocks, `bash -c`, `eval`,
`$(...)` and the rest); a target built from any other variable (`> "$OUT/x"`) is read as a relative name inside the
directory, so it is allowed; a session whose shell already sits outside the project is not guarded at all, because
the project comes from the event's `cwd`; a trailing separator is read as "into this folder" whatever the program,
so the main session's `mkdir -p <memory>/`, `touch "<memory>/"` and `rmdir "<memory>/"` are allowed where the same
word without the separator is denied (the folder normally exists, and a recursive delete of it is still denied as
destructive); a PowerShell drive switch (a segment `D:` followed by a write) is not tracked, so the write is read
from the directory before it; with no home folder known, a home spelling is read as a relative name.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .guard_commands import is_exempt
from .guard_data import mask_data, strip_heredoc_bodies
from .guard_paths import in_scope, roots_for
from .guard_redirects import is_device
from .guard_targets import cd_target, command_readings, write_targets
from .paths import Project, to_native_path

OUTSIDE_REASON = "command writes outside the project and the temp folders"
# Temp folders a shell names that Python's temp dir may not: Git Bash mounts `/tmp` on the Windows temp folder,
# and macOS keeps `/tmp` apart from `tempfile.gettempdir()`. Shell commands only; the file tools never get these.
SHELL_TEMP_ROOTS: tuple[Path, ...] = (Path("/tmp"),)
# The home folder's spellings, followed by `/` or the end of the word.
_HOME = re.compile(r"(?:~|\$(?:env:)?(?:HOME|USERPROFILE)|\$\{(?:env:)?(?:HOME|USERPROFILE)\})(?=/|\Z)", re.IGNORECASE)
# The name of a file inside a folder a word ends in a separator for; only its being inside matters.
_INSIDE = "file"


@dataclass(frozen=True)
class Reach:
    """Where one session's shell may write, and which shell reads the command (`powershell` for the PowerShell tool).
    `write_roots` are the profile's folders, read like any shell word: `~`, absolute, or relative to the main checkout."""

    project: Project
    temp_roots: tuple[Path, ...]
    config_dir: Path | None
    home: Path | None
    worker: bool
    windows: bool
    powershell: bool
    write_roots: tuple[str, ...] = ()

    def resolve(self, word: str, cwd: Path) -> Path:
        """The path a shell word names, read from `cwd`; a leading home spelling becomes `home` when it is known."""
        found = _HOME.match(word)
        if found and self.home is not None:
            word = self.home.as_posix() + word[found.end():]
        return to_native_path(word, cwd, self.windows)

    def writable(self, target: Path) -> bool:
        roots = roots_for(target, self.project, self.temp_roots, self.config_dir, self.worker)
        named = [self.resolve(entry, self.project.main_root) for entry in self.write_roots]
        return in_scope(target, self.project, [*roots, *named])


def _lands_outside(word: str, cwd: Path, reach: Reach) -> Path | None:
    """The target a word names when it is outside, else None. A word that ends in a separator (`cp a dir/`) names a
    folder the command writes into, so it is judged as a path inside that folder."""
    target = reach.resolve(word, cwd)
    landing = target / _INSIDE if word.endswith(("/", "\\")) else target
    return None if reach.writable(landing) else target


def _first_outside(segment: str, cwd: Path, reach: Reach) -> Path | None:
    targets = (_lands_outside(word, cwd, reach) for word in write_targets(segment, reach.powershell) if not is_device(word))
    return next((target for target in targets if target is not None), None)


def _outside_in(reading: Sequence[str], cwd: Path, allowed_prefixes: Sequence[str], reach: Reach) -> Path | None:
    """The first target of one reading that lands outside, following each `cd` from the segment after it."""
    for segment in reading:
        target = None if is_exempt(segment, allowed_prefixes) else _first_outside(segment, cwd, reach)
        if target is not None:
            return target
        place = cd_target(segment, reach.powershell)
        cwd = cwd if place is None else reach.resolve(place, cwd)
    return None


def outside_write(command: str, cwd: Path, allowed_prefixes: Sequence[str], reach: Reach) -> str | None:
    """The reason a command writes outside where its session may, or None. Each reading starts from `cwd`; the
    PowerShell reading is judged only for a PowerShell command, because bash reads `\\"` as an escaped quote."""
    readings = command_readings(strip_heredoc_bodies(mask_data(command)))
    for reading in readings if reach.powershell else readings[:1]:
        target = _outside_in(reading, cwd, allowed_prefixes, reach)
        if target is not None:
            return f"{OUTSIDE_REASON} ({target})"
    return None
