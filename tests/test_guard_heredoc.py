"""A cat heredoc written to a text file is data; a heredoc that feeds code is still scanned."""
import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.paths import Project
from apm.profile import Profile

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_CLI = (ROOT / "scripts" / "apm_cli.py").as_posix()
CLI = f'python "{PLUGIN_CLI}"'
WINDOWS = sys.platform == "win32"


def _decide(repo: Path, command: str, tool: str = "Bash", protected: tuple = ("data/*.db",), **extra: object) -> Decision:
    event = {"tool_name": tool, "cwd": str(repo), "tool_input": {"command": command}, **extra}
    profile = Profile(framework_version="0.3.0", protected_paths=protected)
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, profile, [], [], WINDOWS, [])


@pytest.mark.parametrize(
    "command",
    [
        "cat > body.md <<'EOF'\nExplain rm -rf build\nEOF",
        "cat <<'EOF' > notes.txt\ngit clean -fd\nEOF",
        'cat >> body.md <<"EOF"\ngit reset --hard\nEOF',
        "cat > /tmp/body.md <<-'EOF'\n\tgit push --force\n\tEOF",
    ],
)
def test_a_heredoc_written_to_a_text_file_is_data(git_repo: Path, command: str) -> None:
    assert _decide(git_repo, command).kind == "none"


def test_a_worker_may_write_text_naming_an_apm_call(git_repo: Path) -> None:
    command = "cat > notes.md <<'EOF'\nRun apm debt baseline after the merge.\nEOF"
    assert _decide(git_repo, command, agent_id="w1").kind == "none"


@pytest.mark.parametrize(
    "command",
    [
        "bash <<'EOF'\nrm -rf build\nEOF",
        "python - <<'PY'\nimport os\nos.system('rm -rf build')\nPY",
        "cat <<'EOF' | bash\nrm -rf build\nEOF",
        "cat > cleanup.sh <<'EOF'\nrm -rf build\nEOF\nbash cleanup.sh",
        "cat > body.md <<EOF\n$(rm -rf build)\nEOF",
        "cat > body.md <<'EOF'\nok\nEOF\nrm -rf build",
        "cd docs && cat > body.md <<'EOF'\nrm -rf build\nEOF",
    ],
)
def test_a_heredoc_that_feeds_code_stays_scanned(git_repo: Path, command: str) -> None:
    assert _decide(git_repo, command).kind == "deny"


def test_a_worker_script_naming_an_apm_call_stays_denied(git_repo: Path) -> None:
    decision = _decide(git_repo, "python - <<'PY'\nprint('apm note 4')\nPY", agent_id="w1")
    assert decision.kind == "deny" and "APM state" in decision.reason


def test_the_file_a_heredoc_writes_is_still_checked(git_repo: Path) -> None:
    worker = _decide(git_repo, "cat > .apm/notes.md <<'EOF'\nx\nEOF", agent_id="w1")
    main = _decide(git_repo, "cat > docs/x.md <<'EOF'\nx\nEOF", protected=("docs/**",))
    assert (worker.kind, main.kind) == ("deny", "deny")


def test_a_worker_filing_the_issue_body_is_denied_for_the_cli_call(git_repo: Path) -> None:
    command = "cat > body.md <<'EOF'\nThe guard denied `git rm -r -q x`.\nEOF\n"
    decision = _decide(git_repo, command + f"{CLI} github file --title T --body-file body.md", agent_id="w1")
    assert decision.kind == "deny" and "APM state" in decision.reason
