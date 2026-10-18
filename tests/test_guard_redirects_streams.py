"""PowerShell's all-streams redirect `*>` is one operator, not a glob followed by a redirect."""
import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
WORKER = {"agent_id": "w1"}
BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])
TOOLS = pytest.mark.parametrize("tool_name", ["Bash", "PowerShell"])


def _decide(repo: Path, tool_name: str, command: str, **extra: object) -> Decision:
    event = {"tool_name": tool_name, "cwd": str(repo), "tool_input": {"command": command}, **extra}
    profile = Profile(framework_version="0.3.0", protected_paths=("data/**",))
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, profile, [], [], WINDOWS, [])


@BOTH
@TOOLS
@pytest.mark.parametrize(
    "command",
    ["git fetch origin *>$null", "python x.py *>&1", "npm install *>> install.log", "npm install *> install.log"],
)
def test_an_all_streams_redirect_does_not_expand_as_a_glob(tmp_path: Path, tool_name: str, command: str, extra: dict) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.db").write_text("x")

    decision = _decide(tmp_path, tool_name, command, **extra)

    assert decision.kind == "none"
