"""strip_heredoc_bodies sets aside heredoc bodies that no shell runs, and keeps those a shell reads."""
from __future__ import annotations

import pytest

from apm.guard_data import strip_heredoc_bodies

SET_ASIDE = [
    ("python - <<'PY'\nx > /y\nPY", "python - <<'PY'\nPY"),
    (
        "cat > a.md <<'EOF'\n> q\nEOF\necho done > ../x",
        "cat > a.md <<'EOF'\nEOF\necho done > ../x",
    ),
    (
        "gh issue create --body \"$(cat <<'EOF'\n> x\nEOF\n)\"",
        "gh issue create --body \"$(cat <<'EOF'\nEOF\n)\"",
    ),
    ("cat <<-'EOF'\n\techo x > /y\n\tEOF", "cat <<-'EOF'\n\tEOF"),
]


@pytest.mark.parametrize(("command", "expected"), SET_ASIDE)
def test_a_body_no_shell_runs_is_set_aside(command, expected):
    assert strip_heredoc_bodies(command) == expected


KEPT = [
    "bash <<'EOF'\necho x > /y\nEOF",
    "cat <<'EOF' | sh\necho x > /y\nEOF",
    "pwsh -NoProfile <<'EOF'\nx\nEOF",
    "python - <<EOF\n$(touch /y)\nEOF",
    "python - <<'PY'\r\nx > /y\r\nPY",
    "cat <<< 'x > /y'",
    "echo \"a <<EOF\"\necho x > /y\nEOF",
    "python - <<'PY'\nx > /y",
]


@pytest.mark.parametrize("command", KEPT)
def test_a_body_a_shell_runs_is_kept(command):
    assert strip_heredoc_bodies(command) == command
