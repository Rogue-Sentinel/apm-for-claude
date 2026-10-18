import pytest

from apm.profile import Profile, ProfileError
from apm.workflow_config import (
    Checker, Commands, Lane, Workflow, lane_for, load_workflow, needs_task_review,
)


def _profile(workflow: object) -> Profile:
    return Profile(framework_version="0.2.0", extra={"workflow": workflow})


def test_defaults_without_profile() -> None:
    workflow = load_workflow(None)

    assert workflow.lanes == (Lane("main", ("**",)),)
    assert (workflow.review, workflow.merge_style, workflow.gate_timeout) == ("end", None, 1800)
    assert (workflow.base, workflow.safety_critical, workflow.commands) == ("main", (), Commands())


def test_profile_without_workflow_key_gives_defaults() -> None:
    assert load_workflow(Profile(framework_version="0.2.0")) == Workflow()


def test_reads_every_key() -> None:
    workflow = load_workflow(_profile({
        "commands": {"build": "make", "test": "pytest -q",
                     "checkers": [{"name": "lint", "command": "ruff ."}]},
        "merge_style": "squash",
        "lanes": [{"name": "plugin", "paths": ["src/**"]}, {"name": "companion", "paths": ["companion/**"]}],
        "review": "per-task",
        "safety_critical": ["hooks/**"],
        "gate_timeout": 60,
        "base": "develop",
    }))

    assert workflow == Workflow(
        commands=Commands("make", "pytest -q", (Checker("lint", "ruff ."),)),
        merge_style="squash",
        lanes=(Lane("plugin", ("src/**",)), Lane("companion", ("companion/**",))),
        review="per-task", safety_critical=("hooks/**",), gate_timeout=60, base="develop",
    )


def test_unknown_merge_style_rejected() -> None:
    with pytest.raises(ProfileError, match="merge_style"):
        load_workflow(_profile({"merge_style": "fast-forward"}))


def test_unknown_review_mode_rejected() -> None:
    with pytest.raises(ProfileError, match="review"):
        load_workflow(_profile({"review": "never"}))


@pytest.mark.parametrize("timeout", [0, -1, "60", True])
def test_bad_timeout_rejected(timeout: object) -> None:
    with pytest.raises(ProfileError, match="gate_timeout"):
        load_workflow(_profile({"gate_timeout": timeout}))


@pytest.mark.parametrize("checker", [{"command": "ruff ."}, {"name": "lint"}, {"name": "", "command": "x"}])
def test_checker_needs_name_and_command(checker: object) -> None:
    with pytest.raises(ProfileError, match="checkers"):
        load_workflow(_profile({"commands": {"checkers": [checker]}}))


def test_duplicate_checker_rejected() -> None:
    twice = [{"name": "lint", "command": "a"}, {"name": "lint", "command": "b"}]

    with pytest.raises(ProfileError, match="duplicate"):
        load_workflow(_profile({"commands": {"checkers": twice}}))


def test_duplicate_lane_rejected() -> None:
    twice = [{"name": "a", "paths": ["x/**"]}, {"name": "a", "paths": ["y/**"]}]

    with pytest.raises(ProfileError, match="duplicate"):
        load_workflow(_profile({"lanes": twice}))


@pytest.mark.parametrize("lane", [{"name": "a", "paths": []}, {"name": "a"}, {"name": "a", "paths": [3]}])
def test_lane_needs_string_paths(lane: object) -> None:
    with pytest.raises(ProfileError, match="lanes"):
        load_workflow(_profile({"lanes": [lane]}))


def test_non_string_safety_critical_glob_rejected() -> None:
    with pytest.raises(ProfileError, match="safety_critical"):
        load_workflow(_profile({"safety_critical": [1]}))


def test_unknown_workflow_key_rejected() -> None:
    with pytest.raises(ProfileError, match="unknown keys: mystery"):
        load_workflow(_profile({"mystery": 1}))


def test_lane_for_single_and_spanning() -> None:
    workflow = load_workflow(_profile({"lanes": [
        {"name": "plugin", "paths": ["src/**"]}, {"name": "companion", "paths": ["companion/**"]}]}))

    assert lane_for(workflow, ["src/a.c"]) == "plugin"
    assert lane_for(workflow, ["src/a.c", "companion/b.ts"]) is None
    assert lane_for(workflow, ["docs/readme.md"]) is None


def test_needs_task_review() -> None:
    ending = Workflow(safety_critical=("hooks/**",))

    assert needs_task_review(ending, ["hooks/x.py"]) is True
    assert needs_task_review(ending, ["src/a.py"]) is False
    assert needs_task_review(Workflow(review="per-task"), ["src/a.py"]) is True
