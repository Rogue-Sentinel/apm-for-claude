import json
import subprocess
from pathlib import Path

import pytest

from apm.github import (
    GitHubError, IssueTemplate, close_issue, create_issue, issue_templates, list_open_issues, run_gh,
)


class FakeGh:
    """Records every gh call and answers with a canned result."""

    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = "", missing: bool = False) -> None:
        self.calls: list[dict] = []
        self.result = (stdout, returncode, stderr)
        self.missing = missing

    def __call__(self, argv, **kwargs):
        if self.missing:
            raise FileNotFoundError("gh")
        self.calls.append({"argv": list(argv), **kwargs})
        stdout, code, stderr = self.result
        return subprocess.CompletedProcess(argv, code, stdout, stderr)


def test_create_parses_number(tmp_path: Path) -> None:
    fake = FakeGh(stdout="https://github.com/acme/widgets/issues/42\n")

    number, url = create_issue(tmp_path, "Add login", "the body", ["bug", "ui"], run=fake)

    assert (number, url) == (42, "https://github.com/acme/widgets/issues/42")
    assert fake.calls[0]["argv"] == [
        "gh", "issue", "create", "--title", "Add login", "--body-file", "-", "--label", "bug", "--label", "ui",
    ]
    assert fake.calls[0]["input"] == "the body"
    assert fake.calls[0]["cwd"] == tmp_path


def test_create_without_url_raises(tmp_path: Path) -> None:
    fake = FakeGh(stdout="created, trust me\n")

    with pytest.raises(GitHubError, match="no issue URL"):
        create_issue(tmp_path, "T", "B", [], run=fake)


def test_gh_missing_is_github_error(tmp_path: Path) -> None:
    with pytest.raises(GitHubError, match="gh is not installed"):
        run_gh(["issue", "list"], tmp_path, run=FakeGh(missing=True))


def test_gh_failure_carries_stripped_stderr(tmp_path: Path) -> None:
    fake = FakeGh(returncode=1, stderr="  HTTP 403: forbidden\n")

    with pytest.raises(GitHubError) as caught:
        run_gh(["issue", "list"], tmp_path, run=fake)

    assert str(caught.value) == "HTTP 403: forbidden"


def test_close_comments_then_closes(tmp_path: Path) -> None:
    fake = FakeGh()

    close_issue(tmp_path, 7, "Shipped in https://x/pull/1.", run=fake)

    assert fake.calls[0]["argv"] == [
        "gh", "issue", "close", "7", "--comment", "Shipped in https://x/pull/1.",
    ]


def _template(root: Path, name: str, text: str) -> None:
    folder = root / ".github" / "ISSUE_TEMPLATE"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text, encoding="utf-8")


def test_templates_inline_and_block_labels(tmp_path: Path) -> None:
    _template(tmp_path, "bug.yml", "name: Bug report\nlabels: [bug, triage]\nbody:\n  - type: input\n")
    _template(tmp_path, "feature.yaml", 'name: "Feature"\nlabels:\n  - enhancement\n  - \'ui\'\nbody: x\n')
    _template(tmp_path, "task.md", "---\nname: Task\nlabels: chore\n---\nSome text\nlabels: ignored\n")

    found = issue_templates(tmp_path)

    assert found == [
        IssueTemplate("Bug report", ".github/ISSUE_TEMPLATE/bug.yml", ("bug", "triage")),
        IssueTemplate("Feature", ".github/ISSUE_TEMPLATE/feature.yaml", ("enhancement", "ui")),
        IssueTemplate("Task", ".github/ISSUE_TEMPLATE/task.md", ("chore",)),
    ]


def test_templates_skip_config(tmp_path: Path) -> None:
    _template(tmp_path, "config.yml", "blank_issues_enabled: false\n")
    _template(tmp_path, "bug.yml", "name: Bug\n")

    assert [t.name for t in issue_templates(tmp_path)] == ["Bug"]


def test_templates_missing_folder_is_empty(tmp_path: Path) -> None:
    assert issue_templates(tmp_path) == []


def test_list_open_issues_shapes_labels(tmp_path: Path) -> None:
    payload = [{"number": 3, "title": "Slow", "labels": [{"name": "bug"}, {"name": "perf"}]}]
    fake = FakeGh(stdout=json.dumps(payload))

    found = list_open_issues(tmp_path, run=fake)

    assert found == [{"number": 3, "title": "Slow", "labels": ["bug", "perf"]}]
    assert fake.calls[0]["argv"] == [
        "gh", "issue", "list", "--state", "open", "--limit", "500", "--json", "number,title,labels",
    ]
