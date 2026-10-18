"""How a project is built and merged: commands, merge style, lanes, review mode and the gate timeout.

Everything here is read from the `workflow` key of the profile (kept in `Profile.extra`), and every
part has a default, so a project with no profile, or no `workflow` key, gets one lane, one review at
the end and the framework's own timeout.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from apm.guard_paths import matches_any
from apm.profile import Profile, ProfileError

MERGE_STYLES = ("merge", "squash", "rebase")
REVIEW_MODES = ("end", "per-task")
DEFAULT_GATE_TIMEOUT = 1800
WORKFLOW_KEYS = ("commands", "merge_style", "lanes", "review", "safety_critical", "gate_timeout", "base")
COMMAND_KEYS = ("build", "test", "checkers")
CHECKER_KEYS = ("name", "command")
LANE_KEYS = ("name", "paths")


@dataclass(frozen=True)
class Checker:
    name: str
    command: str


@dataclass(frozen=True)
class Commands:
    build: str | None = None
    test: str | None = None
    checkers: tuple[Checker, ...] = ()


@dataclass(frozen=True)
class Lane:
    name: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class Workflow:
    commands: Commands = Commands()
    merge_style: str | None = None
    lanes: tuple[Lane, ...] = (Lane("main", ("**",)),)
    review: str = "end"
    safety_critical: tuple[str, ...] = ()
    gate_timeout: int = DEFAULT_GATE_TIMEOUT
    base: str = "main"


def load_workflow(profile: Profile | None) -> Workflow:
    """Read `profile.extra["workflow"]`; raise ProfileError for any part that is malformed."""
    given = _object(profile.extra.get("workflow", {}) if profile else {}, "workflow")
    _known(given, WORKFLOW_KEYS, "workflow")
    defaults = Workflow()
    return Workflow(
        commands=_commands(given["commands"]) if "commands" in given else defaults.commands,
        merge_style=_choice(given.get("merge_style"), MERGE_STYLES, "merge_style", allow_none=True),
        lanes=_lanes(given["lanes"]) if "lanes" in given else defaults.lanes,
        review=_choice(given.get("review", defaults.review), REVIEW_MODES, "review"),
        safety_critical=_globs(given.get("safety_critical", []), "safety_critical"),
        gate_timeout=_timeout(given.get("gate_timeout", DEFAULT_GATE_TIMEOUT)),
        base=_text(given.get("base", defaults.base), "base"),
    )


def lane_for(workflow: Workflow, paths: Sequence[str]) -> str | None:
    """The first lane whose globs match every path; None when the paths span lanes or match none."""
    return next((lane.name for lane in workflow.lanes
                 if paths and all(matches_any(lane.paths, path) for path in paths)), None)


def needs_task_review(workflow: Workflow, paths: Sequence[str]) -> bool:
    """True when review is per task, or any path is on a safety-critical glob."""
    return workflow.review == "per-task" or any(matches_any(workflow.safety_critical, p) for p in paths)


def _known(given: dict[str, Any], allowed: tuple[str, ...], label: str) -> None:
    unknown = sorted(set(given) - set(allowed))
    if unknown:
        raise ProfileError(f"{label} has unknown keys: {', '.join(unknown)}")


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileError(f"{label} must be an object")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProfileError(f"{label} must be a non-empty string")
    return value


def _globs(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ProfileError(f"{label} must be a list of non-empty strings")
    return tuple(value)


def _choice(value: object, allowed: tuple[str, ...], label: str, allow_none: bool = False) -> Any:
    if value is None and allow_none:
        return None
    if value not in allowed:
        raise ProfileError(f"{label} must be one of {', '.join(allowed)}")
    return value


def _timeout(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProfileError("gate_timeout must be a positive integer")
    return value


def _commands(raw: object) -> Commands:
    given = _object(raw, "commands")
    _known(given, COMMAND_KEYS, "commands")
    return Commands(
        build=_text(given["build"], "commands.build") if "build" in given else None,
        test=_text(given["test"], "commands.test") if "test" in given else None,
        checkers=_checkers(given.get("checkers", [])),
    )


def _checkers(raw: object) -> tuple[Checker, ...]:
    if not isinstance(raw, list):
        raise ProfileError("commands.checkers must be a list")
    checkers = tuple(_checker(item, f"commands.checkers[{index}]") for index, item in enumerate(raw))
    _no_duplicates([checker.name for checker in checkers], "commands.checkers")
    return checkers


def _checker(raw: object, label: str) -> Checker:
    given = _object(raw, label)
    _known(given, CHECKER_KEYS, label)
    return Checker(_text(given.get("name"), f"{label}.name"), _text(given.get("command"), f"{label}.command"))


def _lanes(raw: object) -> tuple[Lane, ...]:
    if not isinstance(raw, list):
        raise ProfileError("lanes must be a list")
    lanes = tuple(_lane(item, f"lanes[{index}]") for index, item in enumerate(raw))
    _no_duplicates([lane.name for lane in lanes], "lanes")
    return lanes


def _lane(raw: object, label: str) -> Lane:
    given = _object(raw, label)
    _known(given, LANE_KEYS, label)
    paths = _globs(given.get("paths"), f"{label}.paths")
    if not paths:
        raise ProfileError(f"{label}.paths needs at least one glob")
    return Lane(_text(given.get("name"), f"{label}.name"), paths)


def _no_duplicates(names: list[str], label: str) -> None:
    for name in sorted({n for n in names if names.count(n) > 1}):
        raise ProfileError(f"{label}: duplicate name {name}")
