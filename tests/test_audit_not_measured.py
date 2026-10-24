import json
import subprocess
from pathlib import Path

from conftest import run_git

from apm.audit_report import audit_json, render_audit
from apm.audit_scan import Audit, audit
from apm.metrics import Report
from apm.standard_config import Limits

FRESH = Audit("fresh", "main", (), (), ())
SKIPPED = Report((), ("Makefile", "ui/app.qrc", "ui/b.qrc"))


def no_gh(argv, **kwargs):
    if argv[0] == "gh":
        raise FileNotFoundError("gh")
    return subprocess.run(argv, **kwargs)


def test_json_carries_the_count_of_files_not_measured() -> None:
    data = audit_json(FRESH, SKIPPED, Limits())

    assert data["files_not_measured"] == 3
    json.dumps(data)


def test_report_names_the_count_in_the_mode_section_next_to_the_verdict() -> None:
    text = render_audit(FRESH, SKIPPED, Limits(), None)

    mode = text.split("## Measured at")[0]
    assert "fresh: no measurable code yet" in mode
    assert "Files not measured: 3" in mode


def test_report_says_zero_when_every_file_was_measured() -> None:
    text = render_audit(FRESH, Report(()), Limits(), None)

    assert "Files not measured: 0" in text


def test_a_repo_whose_only_file_is_a_makefile_is_fresh_and_says_one_not_measured(git_repo: Path) -> None:
    (git_repo / "Makefile").write_text("all:\n\techo hi\n", encoding="utf-8")
    run_git(git_repo, "add", "Makefile")
    run_git(git_repo, "commit", "-m", "add Makefile")

    found, report = audit(git_repo, None, no_gh)
    text = render_audit(found, report, Limits(), None)

    assert found.mode == "fresh"
    assert audit_json(found, report, Limits())["files_not_measured"] == 1
    assert "fresh: no measurable code yet" in text
    assert "Files not measured: 1" in text
