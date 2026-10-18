"""The denial and the instructions say how to record an approval: with the Bash tool."""
import re
import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.paths import Project
from apm.profile import Profile

ROOT = Path(__file__).resolve().parent.parent
WINDOWS = sys.platform == "win32"


def _decide(repo: Path, command: str, **extra: object) -> Decision:
    event = {"tool_name": "Bash", "cwd": str(repo), "tool_input": {"command": command}, **extra}
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, Profile(framework_version="0.3.0"), [], [], WINDOWS, [])


def _safety_section() -> str:
    text = (ROOT / "agents" / "manager.md").read_text(encoding="utf-8")
    return text.split("## Safety", 1)[1]


def test_the_denial_says_to_approve_from_bash(git_repo: Path) -> None:
    reason = _decide(git_repo, "rm -rf build").reason
    assert "Run the approve call with the Bash tool, on its own" in reason
    assert '--command "<the exact full command>"' in reason
    assert "\n" not in reason


def test_a_worker_state_denial_names_the_write_tool(git_repo: Path) -> None:
    reason = _decide(git_repo, "python - <<'PY'\nprint('apm note 4')\nPY", agent_id="w1").reason
    assert "Grep tool" in reason and "the Write or Edit tool" in reason


def test_the_manager_approves_from_bash_and_knows_where_a_backslash_may_stand() -> None:
    safety = _safety_section()
    assert "with the Bash tool" in safety and "every `\\` is inside quotes" in safety
    assert "holds no `\\`, `$` or backtick" not in safety


@pytest.mark.parametrize("skill", ["finishing-a-branch", "worktrees"])
def test_the_skills_approve_from_bash(skill: str) -> None:
    text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "approve call with the Bash tool" in re.sub(r"\s+", " ", text)
