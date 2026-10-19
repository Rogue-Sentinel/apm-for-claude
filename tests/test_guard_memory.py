"""Through the hook: the main session writes its project's memory folder; nothing else around it opens."""
import json
import re
from pathlib import Path

import pytest

import apm
import hook_pretooluse
from apm.paths import find_project
from conftest import run_git


def _init(repo: Path, **extra: object) -> None:
    (repo / ".apm").mkdir(exist_ok=True)
    profile = json.dumps({"framework_version": apm.VERSION, **extra})
    (repo / ".apm" / "profile.json").write_text(profile, encoding="utf-8")


def _run(cwd: Path, path: str, environ: dict[str, str], tool: str = "Edit", **extra: object) -> str:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    event = {"tool_name": tool, "cwd": str(cwd), "tool_input": {key: path}, **extra}
    code, out = hook_pretooluse.run(json.dumps(event), environ)
    assert code == 0
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "none"


def _slug(repo: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(find_project(repo).main_root))


def _memory(cfg: Path, repo: Path) -> Path:
    return cfg / "projects" / _slug(repo) / "memory"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch) -> None:
    """Neither the real home nor pytest's temp folder (under the real temp root) may open a path."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(hook_pretooluse.tempfile, "gettempdir", lambda: str(tmp_path / "scratch"))


@pytest.fixture
def cfg(tmp_path: Path) -> Path:
    return tmp_path / "cfg"


@pytest.fixture
def env(cfg: Path) -> dict[str, str]:
    return {"CLAUDE_CONFIG_DIR": str(cfg)}


@pytest.fixture
def repo(git_repo: Path) -> Path:
    _init(git_repo)
    return git_repo


@pytest.mark.parametrize("posix", [False, True], ids=["native", "posix"])
@pytest.mark.parametrize("tool, name", [
    ("Write", "MEMORY.md"), ("Write", "feedback-pace.md"), ("Edit", "MEMORY.md"),
    ("Edit", "feedback-pace.md"), ("NotebookEdit", "notes.ipynb"),
])
def test_the_main_session_may_write_its_memory_folder(
    repo: Path, cfg: Path, env: dict[str, str], tool: str, name: str, posix: bool
) -> None:
    target = _memory(cfg, repo) / name
    assert _run(repo, target.as_posix() if posix else str(target), env, tool) == "none"


def test_a_worktree_session_writes_the_main_checkouts_memory_folder(
    repo: Path, cfg: Path, env: dict[str, str]
) -> None:
    run_git(repo, "worktree", "add", ".claude/worktrees/w1", "-b", "w1")
    target = _memory(cfg, repo) / "MEMORY.md"
    assert _run(repo / ".claude" / "worktrees" / "w1", str(target), env) == "none"


def test_a_worktree_session_may_not_write_its_own_slug_memory_folder(
    repo: Path, cfg: Path, env: dict[str, str]
) -> None:
    run_git(repo, "worktree", "add", ".claude/worktrees/w1", "-b", "w1")
    own_slug = cfg / "projects" / (_slug(repo) + "--claude-worktrees-w1") / "memory" / "MEMORY.md"
    assert _run(repo / ".claude" / "worktrees" / "w1", str(own_slug), env) == "deny"


@pytest.mark.parametrize("environ", [{}, {"CLAUDE_CONFIG_DIR": ""}, {"CLAUDE_CONFIG_DIR": "cfg"}],
                         ids=["unset", "empty", "relative"])
def test_without_an_absolute_config_dir_the_folder_under_home_is_used(
    repo: Path, tmp_path: Path, environ: dict[str, str]
) -> None:
    target = _memory(tmp_path / "home" / ".claude", repo) / "MEMORY.md"
    assert _run(repo, str(target), environ) == "none"


@pytest.mark.parametrize("tool", ["Write", "Edit"])
def test_a_worker_may_not_write_the_memory_folder(
    repo: Path, cfg: Path, env: dict[str, str], tool: str
) -> None:
    target = _memory(cfg, repo) / "MEMORY.md"
    assert _run(repo, str(target), env, tool, agent_id="w1") == "deny"


@pytest.mark.parametrize("relative", [
    "settings.json", "settings.local.json", "CLAUDE.md",
    "plugins/cache/rogue-sentinel/apm/0.3.1/scripts/apm/guard.py",
    "projects/C--other-repo/memory/MEMORY.md",
    "projects/{slug}/session.jsonl",
    "projects/{slug}--claude-worktrees-w1/memory/MEMORY.md",
])
def test_the_rest_of_the_config_dir_stays_denied(
    repo: Path, cfg: Path, env: dict[str, str], relative: str
) -> None:
    target = cfg.as_posix() + "/" + relative.format(slug=_slug(repo))
    assert _run(repo, target, env) == "deny"


@pytest.mark.parametrize("relative", [
    "projects/{slug}/memory2/x.md",
    "projects/{slug}/memory-old/x.md",
    "projects/{slug}/memory/../settings.json",
    "projects/{slug}/memory/../../C--other-repo/memory/MEMORY.md",
])
def test_a_path_that_only_looks_like_the_memory_folder_stays_denied(
    repo: Path, cfg: Path, env: dict[str, str], relative: str
) -> None:
    target = str(cfg) + "/" + relative.format(slug=_slug(repo))
    assert _run(repo, target, env) == "deny"


def test_the_home_folder_stays_denied_when_the_config_dir_is_elsewhere(
    repo: Path, tmp_path: Path, env: dict[str, str]
) -> None:
    target = _memory(tmp_path / "home" / ".claude", repo) / "MEMORY.md"
    assert _run(repo, str(target), env) == "deny"


@pytest.mark.parametrize("relative, verdict", [
    (".apm/state/ledger.json", "deny"), (".git/config", "deny"),
    ("data/fleet.db", "deny"), ("src/app.py", "none"),
])
def test_in_project_protections_are_unchanged(
    git_repo: Path, env: dict[str, str], relative: str, verdict: str
) -> None:
    _init(git_repo, protected_paths=["data/*.db"])
    assert _run(git_repo, str(git_repo / relative), env) == verdict


def test_the_memory_folder_path_itself_stays_denied(
    repo: Path, cfg: Path, env: dict[str, str]
) -> None:
    assert _run(repo, str(_memory(cfg, repo)), env, "Write") == "deny"


def test_a_worker_may_not_edit_a_notebook_in_the_memory_folder(
    repo: Path, cfg: Path, env: dict[str, str]
) -> None:
    target = _memory(cfg, repo) / "notes.ipynb"
    assert _run(repo, str(target), env, "NotebookEdit", agent_id="w1") == "deny"


def _link(link: Path, target: Path) -> None:
    """Make `link` a directory link to `target`: a symlink, else a Windows junction."""
    import os
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        try:
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        except (ImportError, OSError) as exc:
            pytest.skip(f"neither a symlink nor a junction can be created here: {exc}")


@pytest.mark.parametrize("linked", ["memory", "slug"])
@pytest.mark.parametrize("where", ["vault/Other/note.md", "through-the-link/x.md"])
def test_a_linked_memory_folder_opens_nothing(
    repo: Path, cfg: Path, env: dict[str, str], tmp_path: Path, linked: str, where: str
) -> None:
    vault = tmp_path / "vault"
    (vault / "Other").mkdir(parents=True)
    folder = _memory(cfg, repo)
    _link(folder if linked == "memory" else folder.parent, vault)
    target = (tmp_path / where) if where.startswith("vault") else folder / "x.md"
    assert _run(repo, str(target), env, "Write") == "deny"


def test_a_config_dir_behind_a_link_still_opens_the_memory_folder(
    repo: Path, tmp_path: Path
) -> None:
    real = tmp_path / "real-cfg"
    real.mkdir()
    _link(tmp_path / "linked-cfg", real)
    target = _memory(tmp_path / "linked-cfg", repo) / "MEMORY.md"
    assert _run(repo, str(target), {"CLAUDE_CONFIG_DIR": str(tmp_path / "linked-cfg")}) == "none"
