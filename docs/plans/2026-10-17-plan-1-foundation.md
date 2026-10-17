# APM for Claude — Plan 1: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An installable `apm` Claude Code plugin where the manager is the main session, workers exist as
subagents with model defaults, safety hooks block destructive actions and protected-path writes, and the
manager's state lives on an `apm/state` branch that it can brief from.

**Architecture:** This repo is both the plugin and its marketplace. Runtime logic is a stdlib-only Python
package (`scripts/apm/`). Hooks and a `bin/apm` CLI call it. Agents are Markdown definitions. Pure decision
functions (guard, ledger, briefing, settings merge) are unit-tested. Git and hook I/O are tested through
temporary repos and subprocess calls.

**Tech Stack:** Python 3.12+ (stdlib only at runtime), pytest, git ≥ 2.42 (`worktree add --orphan`), Claude Code plugins.

**Spec:** `docs/specs/2026-10-17-apm-for-claude-design.md`

## Roadmap (this plan is 1 of 4)
1. **Foundation** (this plan): plugin, agents, safety hooks, state and briefing, `apm setup`.
2. **The standard:** language-agnostic Clean Code and Clean Architecture skills, a coverage inventory against
   VirtualAirline and superpowers (spec §8.1), the default metrics tool, and the debt ratchet.
3. **Workflows:** init and audit, design conversation, planner, feature and bug paths, the merge gate,
   GitHub issues.
4. **Adoption:** install into VirtualAirline through the framework's own init.

## Platform facts this plan relies on (verified 2026-10-17 against code.claude.com docs)
- The main session runs as a named agent through the `"agent"` key in project `.claude/settings.json`, e.g.
  `"apm:manager"`. **Not** set in the plugin's root `settings.json`, because that would make every project use it.
- `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` caps concurrent subagents. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`
  stops subagents from spawning subagents. Both are set through the project settings' `env`.
- PreToolUse hook stdin has `tool_name`, `tool_input`, `cwd`, and `agent_id` (present only inside a subagent).
  Plugin hooks fire inside subagents. A hook decides by printing
  `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny"|"ask","permissionDecisionReason":"..."}}`
  and exiting 0.
- SessionStart hook stdout `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}` is injected as context.
- On Windows, hook commands run through Git Bash. `${CLAUDE_PLUGIN_ROOT}` uses forward slashes. `bin/` is on the Bash tool's PATH.
- Per-project disable: `"enabledPlugins": {"superpowers@claude-plugins-official": false}` in project settings.
- **Unverified (checked in Task 9):** the `agent` key, both env caps, and hooks in desktop Code-tab sessions.

## Global Constraints
- Runtime code: Python ≥ 3.12, **standard library only**. pytest is a dev dependency only.
- The framework obeys its own standard: **≤ 15 lines of logic per function, ≤ 200 per file** (non-blank,
  non-comment, not a lone bracket). **A class with 7+ public methods needs a stated reason.**
- Test-first for every behavior. No skipped tests. Platform differences are parameters, not `skipif`.
- Refactor and behavior never share a commit.
- American spelling.
- Plugin name `apm`. Marketplace name `rogue-sentinel`. Plugin version `0.1.0`, defined once in
  `scripts/apm/__init__.py` as `VERSION` and mirrored in `plugin.json` (a test keeps them equal).
- Max workers is **3**. A profile may lower it, never raise it.
- Hooks do **nothing** in a repo without `.apm/profile.json` (the plugin is installed for every project).
- Hooks **fail closed** in an initialized project: an internal error denies the call, with the error as the reason.
- Violations are **denied** inside a worker (`agent_id` present) and **asked** in the main session (the user
  approves that specific action in Claude Code's permission prompt).

## Review Focus
1. **Windows and Git-Bash path forms** (`C:\x`, `C:/x`, `/c/x`, relative with `..`, mixed case drive letters)
   must resolve to the same target for protected-path checks. Tests are in Task 2 and Task 5.
2. **Obfuscated destructive commands:** `rm -r -f`, `rm -fr`, `git push -f`, `git push origin +main`,
   `git reset --hard` hidden after `&&` or `;`, and PowerShell `Remove-Item -Recurse`. Tests are in Task 5.
3. **A hook crash or malformed stdin** in an initialized project must deny, and outside an APM project
   must stay silent. Tests are in Task 6.
4. **A missing or corrupt ledger or state worktree:** the briefing says so instead of crashing, and the guard
   treats it as an empty allowlist. Tests are in Tasks 4, 6 and 7.
5. **Re-running setup** on an already-set-up project or on a project with existing settings must preserve
   unrelated keys and must not duplicate `.gitignore` lines. Tests are in Task 8.

---

## File Structure

```
.claude-plugin/plugin.json         plugin manifest (name apm, version)
.claude-plugin/marketplace.json    marketplace "rogue-sentinel" listing ./ as apm
agents/manager.md                  main-session agent
agents/{auditor,planner,implementer,debugger,reviewer}.md
hooks/hooks.json                   PreToolUse guard, SessionStart briefing
bin/apm                            bash shim -> scripts/apm_cli.py
scripts/hook_pretooluse.py         hook entry: stdin -> guard -> stdout
scripts/hook_session_start.py      hook entry: briefing context
scripts/apm_cli.py                 CLI entry: dispatch subcommands
scripts/apm/__init__.py            VERSION
scripts/apm/paths.py               Project location, path normalization
scripts/apm/profile.py             Profile load/write/defaults
scripts/apm/ledger.py              pure ledger dict operations
scripts/apm/state_store.py         apm/state worktree init, commit, push
scripts/apm/guard_paths.py         protected-path write checks
scripts/apm/guard_commands.py      shell command checks
scripts/apm/guard.py               Decision, decide(), hook output
scripts/apm/briefing.py            render_briefing()
scripts/apm/cli_parser.py          argparse construction
scripts/apm/setup.py               project settings merge, setup_project()
tests/conftest.py                  temp git repo fixtures
tests/test_*.py                    one per module
pytest.ini                         pythonpath = scripts
docs/platform-notes.md             results of Task 9's live checks
```

---

### Task 1: Plugin skeleton and version

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `scripts/apm/__init__.py`, `pytest.ini`, `.gitignore`, `tests/test_manifest.py`

**Interfaces:**
- Produces: `apm.VERSION: str = "0.1.0"`. `pytest.ini` puts `scripts` on `pythonpath`, so tests `import apm`.

- [ ] **Step 1: Write the failing tests** in `tests/test_manifest.py`
  - `test_plugin_manifest_version_matches_package`: load `.claude-plugin/plugin.json`; assert `name == "apm"`, `version == apm.VERSION`.
  - `test_marketplace_lists_apm_from_repo_root`: load `marketplace.json`; assert `name == "rogue-sentinel"`, `owner["name"] == "Rogue-Sentinel"`, and `plugins == [{"name": "apm", "source": "./", "description": <any non-empty str>}]` (compare name/source, check description non-empty).
- [ ] **Step 2: Run** `python -m pytest tests/test_manifest.py -v`. Expected: FAIL (files missing).
- [ ] **Step 3: Create the files.** `plugin.json`: `name`, `version`, `description`, `author: {"name": "Rogue-Sentinel"}`, `license: "UNLICENSED"`. `.gitignore`: `__pycache__/`, `.pytest_cache/`.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "Add the apm plugin skeleton and marketplace"`.

### Task 2: Locating the project and normalizing paths

**Files:**
- Create: `scripts/apm/paths.py`, `tests/conftest.py`, `tests/test_paths.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Project: main_root: Path; worktree_root: Path`, with properties
    `profile_path` (`worktree_root/.apm/profile.json`), `state_dir` (`main_root/.apm/state`),
    `ledger_path` (`state_dir/ledger.json`), and `is_initialized` (`profile_path.exists()`).
  - `find_project(cwd: Path) -> Project | None`: uses `git rev-parse --show-toplevel` and `--git-common-dir`.
    `main_root` is the parent of the common dir. Returns `None` outside a git repo.
  - `to_native_path(raw: str, cwd: Path, windows: bool) -> Path`: absolute and normalized. When `windows`, it
    maps `/c/...` to `C:/...`, accepts `\` separators, and upper-cases the drive letter.
  - `worktree_relative(target: Path) -> tuple[Path, str] | None`: the nearest ancestor that contains `.git`
    (a file or a directory), plus the target's POSIX path relative to it. `None` if there's no ancestor.
  - `conftest.py` fixture `git_repo(tmp_path) -> Path`: an initialized repo with one commit on `main`
    (sets `user.name`/`user.email` locally).

- [ ] **Step 1: Write the failing tests** in `tests/test_paths.py`
  - `test_find_project_in_plain_repo`: `p = find_project(git_repo)`; `p.main_root == p.worktree_root == git_repo.resolve()`.
  - `test_find_project_in_linked_worktree`: `git worktree add ../wt -b x` from `git_repo`; `find_project(wt).main_root == git_repo.resolve()` and `worktree_root == wt.resolve()`.
  - `test_find_project_outside_repo_is_none`: `find_project(tmp_path / "plain")` (an existing non-repo dir) `is None`.
  - `test_to_native_path_forms` (parametrized, `windows=True`, `cwd=Path("C:/repo")`): `"/c/repo/a.txt"`, `"C:\\repo\\a.txt"`, `"c:/repo/a.txt"`, `"sub/../a.txt"` all equal `Path("C:/repo/a.txt")`.
  - `test_to_native_path_posix` (`windows=False`, `cwd=Path("/repo")`): `"/c/x"` stays `Path("/c/x")`. `"a/../b"` becomes `Path("/repo/b")`.
  - `test_worktree_relative`: for `git_repo / "data" / "fleet.db"` (not yet created), returns `(git_repo, "data/fleet.db")`.
- [ ] **Step 2: Run** `python -m pytest tests/test_paths.py -v`. Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** `paths.py`. Use `os.path.normpath` on the string form for `..`, so the target doesn't need to exist. `worktree_relative` walks `target.parents`.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `"Locate the project and normalize Windows and Git-Bash paths"`.

### Task 3: The project profile

**Files:**
- Create: `scripts/apm/profile.py`, `tests/test_profile.py`

**Interfaces:**
- Produces:
  - `ALWAYS_PROTECTED: tuple[str, ...] = (".git/**", ".apm/state/**")`
  - `DEFAULT_MODELS: dict[str, str] = {"auditor": "haiku", "planner": "opus", "implementer": "sonnet", "debugger": "opus", "reviewer": "opus"}`
  - `MAX_WORKERS_CAP = 3`
  - `class ProfileError(Exception)`
  - `@dataclass(frozen=True) class Profile: framework_version: str; protected_paths: tuple[str, ...] = (); max_workers: int = 3; models: Mapping[str, str] = DEFAULT_MODELS`
    (unknown JSON keys are preserved in `extra: Mapping[str, Any]` so that Plans 2 and 3 can add keys without this loader rejecting them).
  - `Profile.protected_globs() -> tuple[str, ...]`: `ALWAYS_PROTECTED + protected_paths`.
  - `load_profile(path: Path) -> Profile`. `write_profile(path: Path, profile: Profile) -> None` (indent 2, sorted keys, trailing newline).

- [ ] **Step 1: Write the failing tests**
  - `test_load_minimal_profile_applies_defaults`: `{"framework_version": "0.1.0"}` gives `max_workers == 3`, `models == DEFAULT_MODELS`, and `protected_globs() == ALWAYS_PROTECTED`.
  - `test_model_overrides_merge_over_defaults`: `"models": {"implementer": "opus"}` gives `models["implementer"] == "opus"` and `models["planner"] == "opus"`.
  - `test_max_workers_above_cap_is_rejected`: `4` raises `ProfileError` matching `"at most 3"`. `test_max_workers_below_one_is_rejected`: `0` raises.
  - `test_missing_version_is_rejected`, `test_invalid_json_is_rejected`, `test_missing_file_is_rejected`: each raises `ProfileError`.
  - `test_round_trip_preserves_unknown_keys`: write then load keeps `extra == {"commands": {"test": "ctest"}}`.
- [ ] **Step 2: Run** `python -m pytest tests/test_profile.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `profile.py`.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `"Load and write the project profile"`.

### Task 4: The ledger and the state branch

**Files:**
- Create: `scripts/apm/ledger.py`, `scripts/apm/state_store.py`, `tests/test_ledger.py`, `tests/test_state_store.py`

**Interfaces:**
- Produces (`ledger.py`, pure, operating on plain dicts):
  - `ISSUE_STATUSES = ("designing", "planning", "awaiting-approval", "building", "integrating", "merged", "blocked", "queued")`
  - `TASK_STATUSES = ("pending", "running", "done", "failed", "blocked")`
  - `ALLOWLIST_STATUSES = ("building", "integrating")`
  - `class LedgerError(Exception)`
  - `empty_ledger() -> dict`: `{"issues": {}, "log": []}`
  - `load_ledger(path: Path) -> dict`: missing file gives `empty_ledger()`. Bad JSON or a missing `issues` key raises `LedgerError`.
  - `save_ledger(path: Path, ledger: dict) -> None`: atomic (temp file, then `os.replace`), indent 2, sorted keys.
  - `upsert_issue(ledger, number: int, **fields) -> dict`: issue keys are `str(number)`. Validates `status`.
    New issues get `tasks: []`, `allowlist: []`, `questions: []`.
  - `update_task(ledger, number: int, task_id: str, **fields) -> dict`: creates the task if missing. A
    transition to `"running"` increments `attempts`. Validates `status`. Raises `LedgerError` for an unknown issue.
  - `add_allow(ledger, number: int, *, path: str | None, command: str | None, reason: str) -> None`: exactly one of path/command.
  - `add_question(ledger, number: int, text: str, blocks: list[str]) -> int` (index). `resolve_question(ledger, number: int, index: int, answer: str) -> None`.
  - `append_log(ledger, number: int | None, event: str, now: datetime) -> None`: ISO-8601 UTC.
  - `active_allowlist(ledger) -> list[dict]`: allowlist entries of issues whose status is in `ALLOWLIST_STATUSES`.
- Produces (`state_store.py`):
  - `STATE_BRANCH = "apm/state"`
  - `init_state(project: Project) -> None`: idempotent. If `state_dir` is already a worktree, no-op. If the
    branch exists locally, or as `origin/apm/state`, `git worktree add` it. Otherwise
    `git worktree add --orphan -b apm/state <state_dir>`, write `empty_ledger()`, commit `"Start APM state"`.
  - `commit_state(project: Project, message: str) -> bool`: `git add -A` and commit in `state_dir` if anything
    changed, then push to `origin` if that remote exists. Returns `True` if pushed. A push failure is reported
    as `False`, not raised.

- [ ] **Step 1: Write the failing ledger tests**
  - `test_missing_ledger_is_empty`, `test_corrupt_ledger_raises`
  - `test_save_then_load_round_trips`
  - `test_upsert_issue_rejects_unknown_status`
  - `test_running_increments_attempts`: running → failed → running gives `attempts == 2`.
  - `test_update_task_unknown_issue_raises`
  - `test_add_allow_requires_exactly_one_kind`
  - `test_active_allowlist_only_from_building_or_integrating`: issue 1 `building` with a path entry, issue 2 `awaiting-approval` with an entry; the result holds only issue 1's entry.
  - `test_question_add_and_resolve`: resolved question has `answer` set and `resolved == True`.
- [ ] **Step 2: Write the failing state-store tests** (using `git_repo`)
  - `test_init_state_creates_orphan_branch_with_empty_ledger`: afterwards `git -C state_dir rev-parse --abbrev-ref HEAD == "apm/state"`, `load_ledger(ledger_path) == empty_ledger()`, and `main`'s tree has no `ledger.json`.
  - `test_init_state_is_idempotent`: calling it twice doesn't raise and leaves one commit on `apm/state`.
  - `test_init_state_reuses_existing_branch`: create the branch, remove the worktree, then call `init_state`; the original commit is still HEAD.
  - `test_commit_state_without_remote_returns_false_and_commits`
  - `test_commit_state_pushes_to_origin`: a bare repo as `origin`; afterwards `git ls-remote origin apm/state` is non-empty and the result is `True`.
- [ ] **Step 3: Run** `python -m pytest tests/test_ledger.py tests/test_state_store.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement** `ledger.py` and `state_store.py`. Use a `_git(args, cwd) -> str` helper (`subprocess.run(check=True, capture_output=True, text=True)`).
- [ ] **Step 5: Run** the tests. Expected: PASS.
- [ ] **Step 6: Commit** `"Keep the manager's ledger on the apm/state branch"`.

### Task 5: The guard's decisions

**Files:**
- Create: `scripts/apm/guard_paths.py`, `scripts/apm/guard_commands.py`, `scripts/apm/guard.py`, `tests/test_guard_paths.py`, `tests/test_guard_commands.py`, `tests/test_guard.py`

**Interfaces:**
- Consumes: `Project`, `to_native_path`, `worktree_relative` (Task 2); `Profile.protected_globs()` (Task 3); allowlist entries `{"path"| "command", "reason"}` and `init_state` (Task 4, for the state-dir test).
- Produces:
  - `guard_paths.check_write(target: Path, project: Project, globs: Sequence[str], allowed_globs: Sequence[str], temp_roots: Sequence[Path]) -> str | None`.
    It returns a reason if (a) the target is outside `project.main_root` and outside every temp root, (b) the
    target is under `project.state_dir`, or (c) its worktree-relative path matches a protected glob
    (`fnmatch`, with `**` matching across `/`) and doesn't match an allowed glob. Otherwise it returns `None`.
    Rule (b) is explicit because the state dir is its own worktree, so `worktree_relative` would see
    `ledger.json` relative to it rather than `.apm/state/ledger.json`.
  - `guard_commands.split_segments(command: str) -> list[str]`: splits on `&&`, `||`, `;`, `|` and newlines. Each segment is stripped.
  - `guard_commands.destructive_reason(segment: str) -> str | None`: case-insensitive patterns, each with a label:
    `rm` with any recursive flag (`-r`, `-R`, `-rf`, `-fr`, `-r -f`, `--recursive`); `git clean`;
    `git reset … --hard`; `git push` with `-f`, `--force`, `--force-with-lease` or a `+refspec`; `git branch -D`;
    `git worktree remove`; `git checkout -- .` and `git restore .`; `drop table` and `drop database`;
    `truncate table`; `Remove-Item … -Recurse`; `rmdir /s`, `rd /s`, `del /s`.
  - `guard_commands.READ_ONLY_PREFIXES = ("cat ", "head ", "tail ", "less ", "ls", "dir", "stat ", "file ", "wc ", "grep ", "rg ", "git log", "git diff", "git show", "git status", "git blame", "sqlite3 -readonly ")`
  - `guard_commands.protected_reason(segment: str, globs: Sequence[str]) -> str | None`: if any shell token
    (`shlex.split(posix=True)`, stripped of a leading `./`, with `\` turned into `/`) matches a protected glob,
    and the segment isn't read-only (a read-only prefix and no `>`), it returns a reason.
  - `guard_commands.check_command(command: str, globs: Sequence[str], allowed_prefixes: Sequence[str]) -> str | None`:
    the first violating segment's reason. A segment that starts with an allowed prefix is exempt.
  - `guard.Decision` (frozen dataclass): `kind: Literal["none", "ask", "deny"]`, `reason: str = ""`.
  - `guard.decide(event: Mapping, project: Project | None, profile: Profile | None, allowlist: Sequence[Mapping], temp_roots: Sequence[Path], windows: bool) -> Decision`.
    It returns `none` if `project` is None or `profile` is None. It routes `Write` and `Edit` through
    `tool_input.file_path`, `NotebookEdit` through `tool_input.notebook_path`, and `Bash` and `PowerShell`
    through `tool_input.command`; any other tool gives `none`. A violation gives `deny` if `event.get("agent_id")`
    is set, otherwise `ask`. The reason starts with `"APM guard: "`.
  - `guard.to_hook_output(decision: Decision) -> dict | None`: `None` for `none`, otherwise the PreToolUse `hookSpecificOutput` dict.

- [ ] **Step 1: Write the failing path tests** (`project = Project(git_repo, git_repo)`)
  - `test_protected_file_is_blocked`: `data/fleet.db` with glob `data/*.db` gives a reason.
  - `test_protected_file_in_linked_worktree_is_blocked`: the same relative path inside a worktree under `main_root/.claude/worktrees/w1`.
  - `test_allowlisted_protected_file_passes`
  - `test_outside_repo_is_blocked`, `test_temp_root_is_allowed`
  - `test_state_dir_is_always_protected`: after `init_state`, `state_dir / "ledger.json"` with no profile globs is still blocked.
  - `test_ordinary_source_file_passes`
- [ ] **Step 2: Write the failing command tests** (parametrized; every row asserts reason is not None, or None)
  - Blocked: `"rm -rf build"`, `"rm -r -f build"`, `"rm -fr x"`, `"echo hi && rm --recursive x"`, `"git push -f"`,
    `"git push origin +main"`, `"git push --force-with-lease"`, `"git reset --hard HEAD~1"`, `"ls; git clean -fdx"`,
    `"git branch -D feat"`, `"git worktree remove ../wt"`, `"git checkout -- ."`, `"sqlite3 x.db 'DROP TABLE pilots'"`,
    `"Remove-Item -Path build -Recurse -Force"`, `"rmdir /s /q build"`.
  - Allowed: `"rm build/tmp.o"`, `"git push origin feat"`, `"git reset HEAD file"`, `"git branch -d feat"`, `"git status"`.
  - Protected (globs `["data/*.db"]`): `"cp x data/fleet.db"` blocked; `"cat data/fleet.db"` allowed;
    `"cat x > data/fleet.db"` blocked; `"python tools/build_fleet_db.py --out data/fleet.db"` blocked, but allowed
    when `allowed_prefixes=["python tools/build_fleet_db.py"]`; `"sqlite3 -readonly data/fleet.db 'select 1'"` allowed.
- [ ] **Step 3: Write the failing decide tests**
  - `test_worker_violation_is_denied` (event with `agent_id`), `test_main_session_violation_is_asked`.
  - `test_uninitialized_project_is_none`, `test_unrelated_tool_is_none` (`Read`).
  - `test_allowlist_from_active_issue_applies`: allowlist `[{"command": "python tools/build_fleet_db.py", "reason": "r"}]` lets the build command through.
  - `test_hook_output_shape`: `to_hook_output(Decision("deny", "x"))["hookSpecificOutput"] == {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "x"}`.
- [ ] **Step 4: Run** `python -m pytest tests/test_guard_paths.py tests/test_guard_commands.py tests/test_guard.py -v`. Expected: FAIL.
- [ ] **Step 5: Implement** the three modules. Patterns live in a module-level tuple of `(re.Pattern, label)`. Keep each file under 200 lines.
- [ ] **Step 6: Run** the tests. Expected: PASS.
- [ ] **Step 7: Commit** `"Decide which writes and commands the guard blocks"`.

### Task 6: Hook entry points

**Files:**
- Create: `hooks/hooks.json`, `scripts/hook_pretooluse.py`, `scripts/hook_session_start.py`, `tests/test_hooks.py`

**Interfaces:**
- Consumes: `find_project`, `load_profile`, `load_ledger`, `active_allowlist`, `decide`, `to_hook_output`, and `render_briefing` (Task 7: build this task first with a stub `render_briefing` that returns `""`, and Task 7 replaces it).
- Produces:
  - `hook_pretooluse.run(stdin: str, environ: Mapping[str, str]) -> tuple[int, str]` (exit code and stdout).
    Its project comes from `event["cwd"]`. `temp_roots` is `[Path(tempfile.gettempdir())]`. `windows` is `os.name == "nt"`.
    A corrupt ledger means an empty allowlist. **Any exception** once the project is known to be initialized
    gives a deny output with `"APM guard error: <exc>"`. **Bad JSON on stdin** gives `(0, "")` if no project can
    be determined; otherwise it denies.
  - `hook_session_start.run(stdin: str, environ: Mapping[str, str]) -> tuple[int, str]`: in an initialized
    project it returns SessionStart `additionalContext` that contains `render_briefing(...)`, plus a
    version-mismatch line when `profile.framework_version != apm.VERSION`. Elsewhere it returns `(0, "")`.
  - `hooks/hooks.json`: a PreToolUse matcher `"Bash|PowerShell|Write|Edit|NotebookEdit"` with the command
    `python "${CLAUDE_PLUGIN_ROOT}/scripts/hook_pretooluse.py"`, and SessionStart (no matcher) with
    `python "${CLAUDE_PLUGIN_ROOT}/scripts/hook_session_start.py"`. Each script inserts its own directory
    into `sys.path` and calls `run(sys.stdin.read(), os.environ)`.

- [ ] **Step 1: Write the failing tests**
  - `test_pretooluse_silent_outside_apm_project`: event with `cwd` = a non-APM `git_repo` and `rm -rf x`; result `(0, "")`.
  - `test_pretooluse_denies_worker_rm_rf`: an initialized `git_repo` (write a minimal profile); output JSON `permissionDecision == "deny"`.
  - `test_pretooluse_fails_closed_on_internal_error`: monkeypatch `decide` to raise; output is deny with `"APM guard error"`.
  - `test_pretooluse_bad_stdin_outside_project_is_silent`: `"not json"` gives `(0, "")`.
  - `test_pretooluse_corrupt_ledger_is_empty_allowlist`: garbage `ledger.json`; an allowlisted-by-nothing build command is still asked (main session).
  - `test_session_start_reports_version_mismatch`: profile version `"0.0.9"`; context contains `"0.0.9"` and `apm.VERSION`.
  - `test_hooks_json_points_at_existing_scripts`: every `${CLAUDE_PLUGIN_ROOT}/...` path in `hooks.json` exists in the repo.
  - `test_hook_script_end_to_end`: `subprocess.run([sys.executable, "scripts/hook_pretooluse.py"], input=<worker rm -rf event>)` prints deny JSON.
- [ ] **Step 2: Run** `python -m pytest tests/test_hooks.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** both scripts and `hooks.json`.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `"Run the guard and the briefing as plugin hooks"`.

### Task 7: The briefing and the `apm` CLI

**Files:**
- Create: `scripts/apm/briefing.py`, `scripts/apm/cli_parser.py`, `scripts/apm_cli.py`, `bin/apm`, `tests/test_briefing.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: the ledger functions and `commit_state` (Task 4), `find_project`, and `load_profile`.
- Produces:
  - `briefing.render_briefing(ledger: dict | None, error: str | None) -> str`. The sections, in order, are
    **Waiting on you** (unresolved questions, with issue number), **Blocked**, **In progress**
    (issue → task counts done/total and running tasks with worker and model), **Queued**, and
    **Recently merged** (last 5 log events of status `merged`). An empty section is omitted. An empty ledger
    gives `"No work recorded yet."`. If `error` is set, the output starts with `"State unavailable: <error>"`.
  - CLI `apm <subcommand>`, run from anywhere inside the project. Every mutation loads the ledger, applies the
    change, saves, logs it, and calls `commit_state`.
    - `apm brief`
    - `apm issue N [--title T] [--kind feature|bug|debt] [--lane L] [--status S] [--branch B] [--plan PATH]`
    - `apm task N ID [--title T] [--status S] [--worker W] [--model M] [--evidence TEXT]`
    - `apm allow N (--path GLOB | --command PREFIX) --reason TEXT`
    - `apm question N --text TEXT [--blocks ID ...]` and `apm resolve N INDEX --answer TEXT`
    - `apm setup` (wired in Task 8)
    - Exit code 2 with a one-line message for a `LedgerError` or an uninitialized project.
  - `bin/apm`: `#!/usr/bin/env bash` then `exec python "$(dirname "$0")/../scripts/apm_cli.py" "$@"` (committed with mode 755: `git update-index --chmod=+x bin/apm`).

- [ ] **Step 1: Write the failing briefing tests**: a ledger with one question, one blocked issue, one building
  issue (2/3 tasks done, one running on `sonnet`), one queued issue and one merged log event. Assert the order
  of the section headings and the key lines. Also cover the empty ledger and the error text.
- [ ] **Step 2: Write the failing CLI tests** (calling `apm_cli.main(argv) -> int` in an initialized `git_repo` with state):
  - `test_issue_then_task_then_brief` (output of `brief` names the issue title and `1/1`)
  - `test_allow_requires_path_or_command` (argparse error → exit 2)
  - `test_mutation_commits_state` (`git -C state_dir log --oneline` grows by one)
  - `test_uninitialized_project_exits_2`
- [ ] **Step 3: Run** `python -m pytest tests/test_briefing.py tests/test_cli.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement.** `cli_parser.build_parser() -> argparse.ArgumentParser`. `apm_cli.main(argv: list[str] | None = None) -> int` dispatches with a dict of handlers, one per subcommand.
- [ ] **Step 5: Run** the tests. Expected: PASS. Replace Task 6's stub import with the real `render_briefing` and re-run `tests/test_hooks.py`.
- [ ] **Step 6: Commit** `"Brief from the ledger and record work through the apm CLI"`.

### Task 8: `apm setup`, the minimum a project needs

**Files:**
- Create: `scripts/apm/setup.py`, `tests/test_setup.py`
- Modify: `scripts/apm/cli_parser.py`, `scripts/apm_cli.py` (wire `setup`)

**Interfaces:**
- Consumes: `Project`, `write_profile`, `Profile`, `init_state`, `apm.VERSION`.
- Produces:
  - `MANAGER_AGENT = "apm:manager"`, `SUPERPOWERS_ID = "superpowers@claude-plugins-official"`
  - `merge_settings(existing: dict, max_workers: int) -> dict`. It returns a new dict that keeps every
    existing key and sets `agent = MANAGER_AGENT`,
    `env.CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS = str(max_workers)`, `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH = "1"`,
    and `enabledPlugins[SUPERPOWERS_ID] = False`.
  - `setup_project(project: Project) -> list[str]`: the repo-relative paths it created or changed. It merges
    `.claude/settings.json` (creating it if needed), writes `.apm/profile.json` only if it's missing (with
    `framework_version = VERSION` and no protected paths), appends `.apm/state/` to `.gitignore` if absent,
    and calls `init_state`. It **commits nothing on the current branch**. Plan 3's init owns the branch and PR.
  - `apm setup` prints the changed paths, one per line.

- [ ] **Step 1: Write the failing tests**
  - `test_merge_settings_preserves_unrelated_keys`: an existing `{"permissions": {"allow": ["Bash(ls)"]}, "env": {"FOO": "1"}}` keeps both and gains the four settings.
  - `test_merge_settings_does_not_mutate_input`
  - `test_setup_project_fresh_repo`: returns `[".claude/settings.json", ".apm/profile.json", ".gitignore"]` (in any order). `load_profile` works, and the state worktree exists.
  - `test_setup_project_is_idempotent`: the second run returns `[]`, and `.gitignore` contains `.apm/state/` exactly once.
  - `test_setup_keeps_existing_profile`: a pre-existing profile with `protected_paths: ["data/*.db"]` is unchanged.
  - `test_cli_setup_prints_changed_paths`
- [ ] **Step 2: Run** `python -m pytest tests/test_setup.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement**, and wire it into the CLI.
- [ ] **Step 4: Run** `python -m pytest -v` (the whole suite). Expected: all PASS.
- [ ] **Step 5: Commit** `"Set a project up for the manager with apm setup"`.

### Task 9: The agents and a live check

**Files:**
- Create: `agents/manager.md`, `agents/auditor.md`, `agents/planner.md`, `agents/implementer.md`, `agents/debugger.md`, `agents/reviewer.md`, `tests/test_agents.py`, `docs/platform-notes.md`

**Interfaces:**
- Consumes: `DEFAULT_MODELS` (Task 3), and the CLI commands (Task 7).
- Produces: plugin agents `apm:manager`, `apm:auditor`, `apm:planner`, `apm:implementer`, `apm:debugger`, `apm:reviewer`.

- [ ] **Step 1: Write the failing tests** in `tests/test_agents.py` (a small `---` frontmatter parser in the test):
  - For each file, `name` equals the file stem, and `description` is non-empty.
  - The manager has `model: inherit`, and its `tools` either is absent or includes `Agent`.
  - For each worker, `model == DEFAULT_MODELS[name]` and `disallowedTools` includes `Agent`.
  - The manager body contains these headings: `## Your role`, `## Talking to the user`, `## Dispatching workers`,
    `## Verifying work`, `## Recording state`, `## Safety`.
  - Each worker body contains `## Report format`, and that section lists `status`, `files changed`,
    `commands run`, `concerns`, and `found elsewhere`.
- [ ] **Step 2: Run** `python -m pytest tests/test_agents.py -v`. Expected: FAIL.
- [ ] **Step 3: Write the agents.** Content each one must carry (wording is the implementer's):
  - **manager:**
    - The user's only contact. Updates as it works, and waits for the user when it needs them.
    - Dispatches by `subagent_type` `apm:<role>` with `model` from the profile (falling back to `DEFAULT_MODELS`). A worker that fails twice is retried one tier stronger (haiku → sonnet → opus), and only then does the manager ask the user.
    - Never more than the profile's `max_workers` at once. Parallel only on tasks with disjoint files, each with `isolation: "worktree"`.
    - Runs verification commands itself, and never accepts a worker's claim as proof.
    - Records every outcome with `apm task` / `apm issue` / `apm question` right away, and answers "where are we?" from `apm brief`.
    - Treats a guard denial as a stop: it asks the user rather than working around it.
    - States that the workflows (init, design, plan, feature and bug paths, merge) arrive in later framework versions. Until then it does only what the user asks, following these rules.
  - **workers:**
    - Their role-specific job from spec §4.
    - Never address the user. Any question goes back in the report.
    - Stay inside their assigned task and files.
    - Never delete files the brief didn't name.
    - The report format is the structured one from spec §4.
- [ ] **Step 4: Run** `python -m pytest -v`. Expected: all PASS.
- [ ] **Step 5: Live check** (manual; record each result in `docs/platform-notes.md` as verified or failed, with what was observed):
  1. `claude plugin marketplace add "C:/Users/darby/source/repos/Agentic Project Management"` (the local path), then `claude plugin install apm@rogue-sentinel`.
  2. In a scratch git repo, run `apm setup` from a session's Bash tool, then start a new **desktop Code-tab** session there. Confirm that the session runs as the manager, and that the SessionStart briefing (`No work recorded yet.`) appears.
  3. Ask the manager to dispatch an implementer that runs `rm -rf build`, and confirm the guard denies it. Ask the manager itself to run `git reset --hard`, and confirm a permission prompt appears.
  4. Ask the manager to dispatch 4 haiku workers at once, each told to sleep briefly. Confirm no more than 3 run, and record how a 4th is refused.
  5. Ask a worker to dispatch a subagent, and confirm it can't (spawn depth 1).
  6. Confirm superpowers' skills are not offered in that project.
  - If anything fails, write the fallback into `docs/platform-notes.md` as an open issue for Plan 3, and tell the user. Don't work around it silently.
- [ ] **Step 6: Commit** `"Define the manager and its workers, and record the live platform check"`.
