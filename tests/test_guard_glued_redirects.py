"""A redirect is read wherever bash reads it, with or without a blank before it (issue 14)."""
import sys
from pathlib import Path

import pytest

from apm.guard import Decision, decide
from apm.paths import Project
from apm.profile import Profile

WINDOWS = sys.platform == "win32"
WORKER = {"agent_id": "w1"}
BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])


def _decide(repo: Path, command: str, **extra: object) -> Decision:
    event = {"tool_name": "Bash", "cwd": str(repo), "tool_input": {"command": command}, **extra}
    profile = Profile(framework_version="0.3.0", protected_paths=("docs/**",))
    project = Project(main_root=repo, worktree_root=repo)
    return decide(event, project, profile, [], [], WINDOWS, [])


@BOTH
@pytest.mark.parametrize(
    "command",
    [
        "cat>docs/x.md",
        "cat>>docs/x.md",
        "cat <<'EOF'>docs/x.md\nx\nEOF",
        "cat<<'EOF'>>docs/x.md\nx\nEOF",
        'cat <<"EOF">docs/x.md\nx\nEOF',
        "cat <<EOF>docs/x.md\nx\nEOF",
        "python x.py 2>docs/err.md",
        "python x.py 2>>docs/err.md",
        "python x.py&>docs/x.md",
        'echo "x">docs/a.md',
        "echo 'x'>>docs/a.md",
        "git add a && cat>docs/a.md",
        "cat>docs/a.md; git add .",
        "python x.py | sort>docs/a.md",
        "echo x>.apm/state/s.json",
        "python x.py>|docs/x.md",
        "python x.py >|docs/x.md",
        "python x.py &>docs/x.md",
    ],
)
def test_a_glued_redirect_to_a_protected_path_is_denied(git_repo: Path, command: str, extra: dict) -> None:
    assert _decide(git_repo, command, **extra).kind == "deny"


@pytest.mark.parametrize(
    "command",
    [
        "cat>.apm/notes.md",
        "cat <<'EOF'>>.apm/notes.md\nx\nEOF",
        "cat>.apm/notes.sh",
        "echo x 2>.apm/n.md",
        "echo x&>.apm/n.md",
        'echo "x">.apm/n.md',
        "git status && echo x>>.apm/n.md",
        "echo {}>.claude/settings.json",
    ],
)
def test_a_worker_glued_redirect_into_apm_is_denied(git_repo: Path, command: str) -> None:
    decision = _decide(git_repo, command, **WORKER)
    assert decision.kind == "deny"
    assert "workers do not write .apm/" in decision.reason


@BOTH
@pytest.mark.parametrize(
    ("glued", "spaced"),
    [
        ("cat>docs/x.md", "cat > docs/x.md"),
        ("python x.py 2>docs/e.md", "python x.py 2> docs/e.md"),
        ('echo "x">docs/a.md', 'echo "x" > docs/a.md'),
        ("python x.py<docs/in.md", "python x.py < docs/in.md"),
    ],
)
def test_a_glued_redirect_gets_the_verdict_of_its_spaced_form(git_repo: Path, glued: str, spaced: str, extra: dict) -> None:
    assert _decide(git_repo, glued, **extra).kind == _decide(git_repo, spaced, **extra).kind


@BOTH
@pytest.mark.parametrize(
    "command",
    [
        "python x.py 2>&1",
        "python x.py >/dev/null",
        "python x.py 2>/dev/null",
        "python x.py>/dev/null 2>&1",
        "python x.py > out.txt 2>&1",
        "pytest -q 2>&1 | tail -5",
    ],
)
def test_a_redirect_that_writes_no_file_stays_allowed(git_repo: Path, command: str, extra: dict) -> None:
    assert _decide(git_repo, command, **extra).kind == "none"


@BOTH
@pytest.mark.parametrize(
    "command",
    [
        'echo "a -> b"',
        "echo 'x => y'",
        'echo "a>docs/x.md"',
        "echo 'a>docs/x.md'",
        'git commit -m "a->docs/x.md"',
        "git commit -m 'map x=>docs/y.md'",
        "git log --format='%h>%s'",
        r"echo a\>docs/x.md",
    ],
)
def test_a_redirect_sign_inside_quotes_or_a_message_stays_allowed(git_repo: Path, command: str, extra: dict) -> None:
    assert _decide(git_repo, command, **extra).kind == "none"


@BOTH
@pytest.mark.parametrize(
    "command",
    [
        "cat > body.md <<'EOF'\na -> b\nsee docs/x.md -> docs/y.md\nx=>y\nEOF",
        "cat <<'EOF'>body.md\na -> b\nEOF",
        "cat >body.md <<'EOF'\na->b\nEOF",
        "cat <<'EOF'>body.md\nmoved a.md->docs/b.md\nEOF",
    ],
)
def test_an_arrow_in_a_markdown_heredoc_body_stays_allowed(git_repo: Path, command: str, extra: dict) -> None:
    assert _decide(git_repo, command, **extra).kind == "none"
