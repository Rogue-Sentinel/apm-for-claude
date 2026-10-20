# APM for Claude — Issue 19: The guard blocks Claude's own memory folder, and a --path approval can't unblock it — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built test-first by one
> implementer in its own worktree and verified by the manager with the task's targeted tests. The whole
> branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right
> before the PR. **Tasks 1, 2 and 3 are safety-critical and each gets its own review**: Task 1 writes the tests
> that fix which verdicts change and which must not, Task 2 loosens one verdict class (ADR 0006), and Task 3
> changes the denial texts. Every review is bounded by ADR 0002 (`docs/adr/0002-guard-threat-model.md`).
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The main session may write Claude Code's memory folder for this project
(`<config dir>/projects/<slug of the main checkout>/memory/`) with the Write, Edit or NotebookEdit tool, without
an approval. Workers may not. A denial offers only an approval that can lift it: a file-tool write outside the
project or into `.apm/state/` offers none, a protected file inside the project offers `--path` with the path
the denial names, and a command denial offers `--command`.

**Architecture:** A pure function `memory_folder(main_root, config_dir)` in `scripts/apm/guard_paths.py` derives
the folder. `decide` in `scripts/apm/guard.py` takes a new keyword `config_dir` and, for the main session only,
adds that folder to the roots a file write may land in, beside the temp roots. The hook reads the config dir
from the environment (`CLAUDE_CONFIG_DIR` when absolute, else `~/.claude`) and passes it in. For the texts,
`guard_paths.write_denial` says which check fired, and `guard.py` attaches the remedy that fits it.

**Tech Stack:** Python 3, standard library only, pytest. Test command: `python -B -m pytest -q <files>`.

**Spec:** GitHub issue #19 (Rogue-Sentinel/apm-for-claude), and the manager's brief of 2026-10-18.

## Root cause (confirmed by the planner, 2026-10-18, on the branch at 0d49048 + plan)

The manager's reading holds, and it goes a little further than the brief says:

1. **Outside the project, nothing can lift the denial.** `guard_paths.check_write` returns
   `"{target} is outside the project"` when `_in_scope` is false (`guard_paths.py:69`). `_in_scope` accepts only
   `main_root`, `worktree_root` and the temp roots. That return comes before `_protected` ever reads
   `allowed_globs`, so no `--path` approval applies outside the project.
2. **The approval glob is matched against a checkout-relative path, never an absolute one.** Even in the project,
   `_protected` matches `allowed_globs` against `worktree_relative(...)[1]`, the path relative to the checkout
   root (`data/fleet.db`). An absolute `--path` glob can never match anything, in or out of the project.
3. **The denial offers `--path` for every denial in the main session** (`guard._ASK_USER`, appended in
   `decide`), including command denials, which never read path approvals (`_command_violation` gets only the
   command prefixes), and the `.apm/state/` file denial, which comes first in `check_write`.

Probe on the branch code (synthetic `decide` Edit event, main session, empty profile, a temp git repo): an Edit
of `C:\Users\darby\.claude\projects\C--Users-darby-source-repos-VirtualAirline-Plugin-for-XP12\memory\MEMORY.md`
is `deny ... is outside the project. Ask the user in chat ...`. With a live approval whose path is that exact
path, the same path with `/`, `C:/Users/darby/.claude/projects/*/memory/**`, `**/MEMORY.md` or `**`, it is
still `deny`. A worker gets the same denial with no remedy text.

**The instruction behind it.** `agents/manager.md` line 140 tells the manager to record
`(or --path GLOB for a file write)`, and `docs/tutorial.md` lines 295 to 297 quote the denial offering
`--path <glob>`. Neither says the glob is relative to the checkout root or that it cannot reach outside the
project. Task 3 corrects both, and the CLI's `--path` help text.

## Platform facts this plan relies on (2026-10-18)

- **The memory folder is `<config dir>/projects/<slug>/memory/`, with the slug taken from the main checkout's
  root, and every worktree of the repository shares it.** Checked on this host: the six memory folders under
  `C:\Users\darby\.claude\projects\` all sit under main-checkout slugs, none under the 40-odd worktree slugs
  (`...--claude-worktrees-...`). This session runs in a worktree, and its memory folder is
  `C--Users-darby-source-repos-Agentic-Project-Management\memory`, while its transcript folder is the worktree's
  slug. Claude Code's changelog: "Project configs & auto memory now shared across git worktrees of the same
  repository", and a later fix for auto-memory writes "when Claude Code was started in a subdirectory of a git
  repository". `find_project` already computes this root (`main_root`, the parent of the git common dir).
- **The slug is the path with every character outside `[A-Za-z0-9]` turned into `-`.** Checked: that rule turns
  `C:\Users\darby\source\repos\Agentic Project Management`, `C:\Users\darby\source\repos\VirtualAirline-Plugin-for-XP12`
  and this worktree's path into exactly their folder names.
- **Unverified: very long paths.** The changelog mentions a fix for project paths over 200 characters sharing a
  sanitized prefix, which suggests a truncated name plus a hash. A 207-character folder on this host is not
  truncated. Not reproduced by this plan: a truncated folder simply does not match, and the write is denied as
  today (Risks).
- **`CLAUDE_CONFIG_DIR` relocates the config dir.** Project-level `.claude/settings.json` can no longer set it
  (changelog); it comes from the shell, user or managed settings, so a repository file cannot widen the guard.
- **`autoMemoryDirectory` relocates the memory folder, and a repository's settings may set it** (changelog). This
  plan does not read it (Alternatives in ADR 0006).
- **The PreToolUse input carries no memory path.** The guard sees `tool_name`, `tool_input`, `cwd`, `agent_id`
  and the like (`scripts/hook_pretooluse.py`, the changelog's hook entries). `transcript_path` sits in the
  session's cwd slug, which for a worktree session is the worktree's, not the memory folder's.

## Global Constraints
- Limits (profile defaults): **15** lines of logic per function, **200** per file, for every file this plan creates
  or changes, tests included. Starting numbers from the manager's `metrics`: `guard_paths.py` 44 (largest
  function 6), `guard.py` about 124 (11), `guard_workers.py` 62 (5). The brief has no number for
  `scripts/hook_pretooluse.py`; by reading it is a few dozen lines, and the manager confirms with `metrics`.
- Standard library only. No new import edge between modules: `guard.py` already imports `guard_paths`, and the
  hook already imports `guard`.
- Test-first; no skipped or expected-to-fail tests; no test waits on a person; no existing test edited, weakened or
  deleted. `tests/test_guard.py` is in the debt baseline: nothing is added to it. New tests go in new files.
- **ADR 0002 binds every task.** Exactly one class of denial becomes an allow, recorded in ADR 0006 (Task 2):
  a main-session file-tool write under this project's memory folder. Every other verdict is unchanged. Task 3
  changes texts only.
- Workers stay denied: the memory folder is added to the roots only when the event has no `agent_id`.
- `scripts/apm/guard_commands.py`, `guard_redirects.py` (issue #14), `guard_workers.py`, `guard_cli.py`,
  `guard_data.py`, `guard_github.py` and `guard_words.py` are not changed.
- American spelling, plain voice.

## Review Focus
Threat model (ADR 0002): the manager or a cooperative worker using the Write or Edit tool on a path it misread:
another project's memory, the worktree's own slug folder, `settings.json`, a plugin file; or recording the approval
a denial offered and expecting it to work. Inputs built to evade the check are known limits, not review targets.
1. **Only this project's memory folder opens, and only for the main session.** Another project's memory folder,
   the worktree-slug folder (`<slug>--claude-worktrees-w1/memory/`), a sibling (`memory2/`, `memory-old/`), the
   slug folder itself (`<slug>/x.jsonl`), and `..` out of the folder stay denied; a worker's write to the folder
   stays denied. Tests in Task 1 (`tests/test_guard_memory.py`); code in Task 2.
2. **The rest of the config dir stays denied:** `settings.json`, `settings.local.json`, `CLAUDE.md`, a plugin file
   under `plugins/cache/`. Tests in Task 1; code in Task 2.
3. **Which config dir:** `CLAUDE_CONFIG_DIR` when it is set and absolute; otherwise `~/.claude`. When it is set
   elsewhere, the folder under `~/.claude` stays denied. Tests in Task 1; code in Task 2.
4. **No denial offers an approval that cannot lift it,** and every approval still offered works: a command
   denial offers `--command` only, a protected file offers `--path` with the named relative path (and that
   approval lifts it), an outside or `.apm/state/` file write offers none. Tests in Task 1
   (`tests/test_guard_remedies.py`); code in Task 3.
5. **No other verdict loosens:** in-project protections (`.git/**`, `.apm/state/**`, profile paths) are unchanged
   with a config dir set, and every existing guard and hook test passes unchanged. Tests in Task 1 and the
   verification runs of Tasks 2 and 3.

---

## File Structure

```
scripts/apm/guard_paths.py              (modify) memory_folder(); write_denial() names which check fired; check_write wraps it
scripts/apm/guard.py                    (modify) decide(config_dir=...); main-session write roots; a remedy per kind of denial
scripts/hook_pretooluse.py              (modify) read the config dir from the environment and pass it to decide
scripts/apm/cli_parser.py               (modify) the approve --path help text says the path is checkout-relative
agents/manager.md                       (modify) Safety: when --path applies, and that the memory folder needs no approval
docs/tutorial.md                        (modify) the quoted denial text
docs/adr/0006-the-main-session-writes-its-memory-folder.md   (create) the one loosened class, and the --path decision
docs/adr/README.md                      (modify) the index row for 0006
tests/test_guard_memory.py              (create) hook-level reproductions and pins for the memory folder
tests/test_guard_remedies.py            (create) decide-level reproductions and pins for the denial texts
tests/test_guard_memory_folder.py       (create) unit tests for memory_folder with literal slugs
```

No touched file is over a limit, so there is no extraction task.

Test helpers, copied (not imported) from `tests/test_hooks.py` and `tests/test_hooks_worktrees.py`:
- `tests/test_guard_memory.py`: `_init(repo, **extra)` writes `.apm/profile.json` with
  `framework_version = apm.VERSION`; `_run(cwd, path, environ, tool="Edit", **extra) -> str` sends
  `{"tool_name": tool, "cwd": str(cwd), "tool_input": {"file_path": path}, **extra}` (for `NotebookEdit`, key
  `notebook_path`) through `hook_pretooluse.run(json.dumps(event), environ)` and returns `"none"` or the
  `permissionDecision`. An autouse fixture sets `HOME` and `USERPROFILE` to `tmp_path / "home"` and patches
  `hook_pretooluse.tempfile.gettempdir` to return `tmp_path / "scratch"`, so neither the real home nor pytest's
  temp folder (which is under the real temp root, and so already writable) can make a case pass. `cfg =
  tmp_path / "cfg"`; `_memory(cfg, repo) = cfg / "projects" / re.sub(r"[^A-Za-z0-9]", "-",
  str(find_project(repo).main_root)) / "memory"`. The slug formula repeats the implementation's; Task 2's unit
  test checks it against literal folder names.
- `tests/test_guard_remedies.py`: `_decide(repo, event_extra, approvals=(), protected=()) -> Decision` calling
  `decide(event, Project(main_root=repo, worktree_root=repo), Profile(framework_version="0.3.0",
  protected_paths=protected), [], [], WINDOWS, list(approvals))`, as `tests/test_approve_instructions.py` does.
  A live path approval is `{"path": p, "reason": "r", "cwd": str(repo), "expires_at": <now + 5 min, ISO>}`.

---

### Task 1: Reproduce the bug as failing tests and pin the neighbors

**Files:**
- Create: `tests/test_guard_memory.py`
- Create: `tests/test_guard_remedies.py`

**Interfaces:**
- Consumes: `hook_pretooluse.run(stdin: str, environ: Mapping[str, str]) -> tuple[int, str]`,
  `apm.guard.decide`, `apm.paths.Project`, `apm.paths.find_project`, `apm.profile.Profile`, the `git_repo` fixture,
  `conftest.run_git`.
- Produces: nothing a later task imports. Task 2 turns the memory **FAIL now** cases green, Task 3 the remedy ones.

Each case is **FAIL now** (a reproduction) or **pin** (passes now and must keep passing).

- [ ] **Step 1: Write the memory tests** in `tests/test_guard_memory.py`; environ is
  `{"CLAUDE_CONFIG_DIR": str(cfg)}` unless the case says otherwise.
  - `test_the_main_session_may_write_its_memory_folder`, parametrized on tool (`Write`, `Edit`, `NotebookEdit`
    with `memory/notes.ipynb`) and on the path form (native `str(path)`, and `path.as_posix()`), targets
    `memory/MEMORY.md` and `memory/feedback-pace.md`: `"none"`. **FAIL now.**
  - `test_a_worktree_session_writes_the_main_checkouts_memory_folder`: `cwd` is a linked worktree
    `.claude/worktrees/w1` of `git_repo` (made with `run_git`), path `_memory(cfg, git_repo) / "MEMORY.md"`:
    `"none"`. **FAIL now.**
  - `test_without_an_absolute_config_dir_the_folder_under_home_is_used`, parametrized on environ `{}`,
    `{"CLAUDE_CONFIG_DIR": ""}`, `{"CLAUDE_CONFIG_DIR": "cfg"}`; path under `tmp_path/"home"/".claude"`:
    `"none"`. **FAIL now.**
  - `test_a_worker_may_not_write_the_memory_folder`: `agent_id="w1"`, Write and Edit: `"deny"`. **Pin.**
  - `test_the_rest_of_the_config_dir_stays_denied`, parametrized: `cfg/settings.json`, `cfg/settings.local.json`,
    `cfg/CLAUDE.md`, `cfg/plugins/cache/rogue-sentinel/apm/0.3.1/scripts/apm/guard.py`,
    `cfg/projects/C--other-repo/memory/MEMORY.md`, `cfg/projects/<slug>/session.jsonl`,
    `cfg/projects/<slug>--claude-worktrees-w1/memory/MEMORY.md`: `"deny"`. **Pin.**
  - `test_a_path_that_only_looks_like_the_memory_folder_stays_denied`, parametrized: `<slug>/memory2/x.md`,
    `<slug>/memory-old/x.md`, `str(memory) + "/../settings.json"`, `str(memory) + "/../../C--other-repo/memory/MEMORY.md"`
    (written as strings so `..` reaches the guard): `"deny"`. **Pin.**
  - `test_the_home_folder_stays_denied_when_the_config_dir_is_elsewhere`: environ points at `cfg`, path is the
    memory folder under `tmp_path/"home"/".claude"`: `"deny"`. **Pin.**
  - `test_in_project_protections_are_unchanged`, `_init(git_repo, protected_paths=["data/*.db"])`, parametrized:
    `.apm/state/ledger.json`, `.git/config`, `data/fleet.db` under `git_repo`: `"deny"`; and `src/app.py`:
    `"none"`. **Pin.**
- [ ] **Step 2: Write the remedy tests** in `tests/test_guard_remedies.py` (main session unless named):
  - `test_an_outside_file_write_offers_no_approval`, Write and Edit to `git_repo.parent / "outside" / "x.md"`:
    `"approve --" not in reason` and `"make the change themselves" in reason`. **FAIL now.**
  - `test_a_state_dir_file_write_offers_no_approval`, Edit `git_repo/.apm/state/ledger.json`:
    `"approve --" not in reason` and `"only through the CLI" in reason`. **FAIL now.**
  - `test_a_protected_file_write_offers_a_path_approval_only`, protected `("data/*.db",)`, Edit
    `git_repo/data/fleet.db`: `"data/fleet.db is a protected path" in reason`, `"approve --path" in reason`,
    `"--command" not in reason`. **FAIL now.**
  - `test_a_command_denial_offers_a_command_approval_only`, Bash `rm -rf build`:
    `'approve --command "<the exact full command>"' in reason` and `"--path" not in reason`. **FAIL now.**
  - `test_a_path_approval_of_the_named_path_lifts_the_protected_write`: approval path `data/fleet.db`: `"none"`.
    **Pin.**
  - `test_no_path_approval_lifts_an_outside_write`, parametrized on approval path: the exact absolute path, its
    posix form, `**`: `"deny"`. **Pin** (the `--path` decision: outside the project stays unapprovable).
  - `test_a_worker_denial_offers_no_remedy`, worker Edit outside and worker `rm -rf build`:
    `"Ask the user" not in reason`. **Pin.**
- [ ] **Step 3: Run** `python -B -m pytest -q tests/test_guard_memory.py tests/test_guard_remedies.py`. Expected:
  every **FAIL now** case fails for the defect (`'deny' == 'none'`, or the text assertion), never for an import,
  fixture or syntax error; every **pin** passes.
- [ ] **Step 4: Commit** `"Reproduce issue 19: the memory folder is denied and the denial offers approvals that cannot work"`.
  This commit is red on purpose; the manager verifies the failure reasons, not a pass.

### Task 2: Let the main session write its own memory folder

**Files:**
- Modify: `scripts/apm/guard_paths.py` (add `memory_folder`)
- Modify: `scripts/apm/guard.py` (`decide` gains `config_dir`; a helper for the write roots)
- Modify: `scripts/hook_pretooluse.py` (`_guard` takes `environ`; a helper for the config dir)
- Create: `docs/adr/0006-the-main-session-writes-its-memory-folder.md`
- Modify: `docs/adr/README.md` (the row for 0006)
- Test: `tests/test_guard_memory_folder.py`

**Interfaces:**
- Consumes: Task 1's tests.
- Produces:
  - `memory_folder(main_root: Path, config_dir: Path) -> Path` in `apm.guard_paths`:
    `config_dir / "projects" / <str(main_root) with each character outside [A-Za-z0-9] replaced by "-"> / "memory"`.
    Pure; it reads no file and no environment. Use an explicit ASCII class, not `\w`.
  - `decide(event, project, profile, allowlist, temp_roots, windows, approvals=(), config_dir: Path | None = None)
    -> Decision`. Every existing call keeps working unchanged.
  - `_write_roots(project: Project, temp_roots: Sequence[Path], config_dir: Path | None, worker: bool) -> list[Path]`
    in `guard.py`: the temp roots, plus `memory_folder(project.main_root, config_dir)` when `config_dir` is set and
    the event is not a worker's. `decide` passes the result where it passed `temp_roots`.
  - `_config_dir(environ: Mapping[str, str]) -> Path` in `hook_pretooluse.py`: `Path(environ["CLAUDE_CONFIG_DIR"])`
    when that value is non-empty and absolute, else `Path.home() / ".claude"`. `_guard(event, project, environ)`
    passes `config_dir=_config_dir(environ)`.

- [ ] **Step 1: Write the failing unit tests** in `tests/test_guard_memory_folder.py`, each comparing
  `memory_folder(...).parent.name` (the slug) to a literal, and `.name` to `"memory"`:
  - `test_a_windows_root_gives_the_folder_claude_code_uses`:
    `Path(r"C:\Users\darby\source\repos\Agentic Project Management")` → `C--Users-darby-source-repos-Agentic-Project-Management`.
  - `test_a_hyphenated_root_keeps_its_hyphens`: `Path(r"C:\Users\darby\source\repos\VirtualAirline-Plugin-for-XP12")`
    → `C--Users-darby-source-repos-VirtualAirline-Plugin-for-XP12`.
  - `test_a_posix_root_with_dots_and_underscores`: `Path("/home/pat/src/my.repo_v2")` → `-home-pat-src-my-repo-v2`.
  - `test_the_folder_is_under_the_config_dirs_projects`: `memory_folder(root, Path("/cfg")).parent.parent ==
    Path("/cfg/projects")`.
- [ ] **Step 2: Run** `python -B -m pytest -q tests/test_guard_memory_folder.py tests/test_guard_memory.py`. Expected:
  the unit tests FAIL (`memory_folder` cannot be imported); Task 1's memory FAIL-now cases still fail.
- [ ] **Step 3: Implement** the three functions above and the `decide` parameter. `_in_scope`, `is_under` and the
  order of checks in `check_write` are unchanged: the `.apm/state/` check still comes first, and a path in the
  memory folder that is inside a git checkout is still matched against the protected globs.
- [ ] **Step 4: Write ADR 0006** from `skills/adr/references/adr-template.md`, titled
  "ADR-0006: The main session may write Claude Code's memory folder for its project, and a file-tool write
  outside the project cannot be approved". Status: `Accepted, <date>. Builds on ADR-0002 and ADR-0005.`
  It must contain:
  - Context: the three causes above, the probe result, and the XP12 report.
  - Decision, with the folder rule exactly as `memory_folder` and `_config_dir` implement it, main session only.
  - How ADR-0002 rule 2 is read, as ADR-0005 did, and that the user approved that reading for this change when
    approving this plan (with the date). Exactly one class of denial becomes an allow: (a) a Write, Edit or
    NotebookEdit call from the main session whose target, after normalization and `realpath`, is under
    `<config dir>/projects/<slug of main_root>/memory/`. Writing Claude Code's own memory for this project is none
    of the things ADR-0002 says the guard must stop. Every other verdict is unchanged, and the tests pin the
    neighbors: a worker's write, the rest of the config dir, other projects' and the worktree slug's folders,
    siblings and `..`, and the in-project protections.
  - The `--path` decision: a file-tool write outside the project stays unapprovable and the denial stops
    offering one (Task 3), because letting an absolute `--path` glob reach outside the project would add a second,
    wider class for every path a user might approve; and a `--path` approval is checkout-relative.
  - Consequences: long-path slugs, `autoMemoryDirectory` and a symlinked checkout are denied as today (false
    positives, never a loosening); Bash writes outside the project are not checked by the guard at all, before
    or after (not changed here).
  - Alternatives considered: any `<config>/projects/*/memory/**` (wider: another project's memory); the hook's
    `transcript_path` (its folder is the worktree's slug, not memory's); reading `autoMemoryDirectory` (a
    repository's settings could then widen the guard); a profile setting (manual per machine, and the main session
    can edit the profile); letting absolute `--path` globs apply outside the project.
  - Add the row to `docs/adr/README.md`.
- [ ] **Step 5: Run** `python -B -m pytest -q tests/test_guard_memory_folder.py tests/test_guard_memory.py tests/test_guard_remedies.py tests/test_guard_paths.py tests/test_hooks.py tests/test_hooks_worktrees.py tests/test_hook_approve.py tests/test_hook_wrapper.py tests/test_guard.py tests/test_guard_approve.py tests/test_approve_instructions.py tests/test_guard_echo.py tests/test_guard_heredoc.py tests/test_guard_workflow.py tests/test_guard_debt.py tests/test_guard_continuations.py tests/test_guard_workers_wrappers.py tests/test_guard_bypasses.py tests/test_docs.py tests/test_own_limits.py`.
  Expected: everything passes, with no existing test changed, except the four FAIL-now cases of
  `tests/test_guard_remedies.py`, which still fail on their text assertions until Task 3; its pins pass.
- [ ] **Step 6: Commit** `"Let the main session write Claude Code's memory folder for its project"`.

### Task 3: Offer only an approval that can lift the denial

**Files:**
- Modify: `scripts/apm/guard_paths.py` (add `write_denial`; `check_write` returns its reason)
- Modify: `scripts/apm/guard.py` (the remedy texts; `_violation` returns the remedy with the reason)
- Modify: `scripts/apm/cli_parser.py` (the `approve --path` help text, line 42)
- Modify: `agents/manager.md` (Safety, line 140)
- Modify: `docs/tutorial.md` (the quoted denial, lines 295 to 297)

**Interfaces:**
- Consumes: Task 1's remedy tests; Task 2's `decide(..., config_dir=...)` and `_write_roots`.
- Produces:
  - `write_denial(target, project, globs, allowed_globs, temp_roots) -> tuple[Literal["state", "outside",
    "protected"], str] | None` in `apm.guard_paths`: the same checks, in the same order, with the same reason texts
    as today's `check_write`, plus which one fired. `check_write(...) -> str | None` keeps its signature and returns
    the reason of `write_denial`, so `tests/test_guard_paths.py` passes unchanged.
  - In `guard.py`, `_violation(...) -> tuple[str, str] | None` (reason, remedy); `decide` builds
    `PREFIX + reason + ("" if worker else remedy)`. The remedies, exact text (`{_CLI}` as today):
    - command denials, `_COMMAND_REMEDY`: today's `_ASK_USER` with the clause `(or --path <glob> for a file write)`
      removed: `". Ask the user in chat; if they approve this exact action, record it with {_CLI} approve --command
      "<the exact full command>" --reason "<why>", then retry. Run the approve call with the Bash tool, on its own,
      with the command in single quotes if it holds a double quote."`
    - `"protected"`: `". Ask the user in chat; if they approve this exact write, record it with {_CLI} approve --path
      "<the path named above, as written>" --reason "<why>", then retry. Run the approve call with the Bash tool, on
      its own."`
    - `"outside"`: `". No approval lifts this for a file tool. Ask the user in chat to make the change themselves."`
    - `"state"`: `". No approval lifts this: APM state changes only through the CLI ({_CLI}), never by editing its
      files."`
    - A worker's file denial (`worker_file_violation`) carries remedy `""`.
    - *Added by the manager before approval:* the command denial "command runs inside the APM state directory"
      (`_state_dir_write`) also cannot be lifted, because `_exempt_command` refuses an approval for it, so it carries
      the `"state"` remedy, not `_COMMAND_REMEDY`. Task 3 adds the test first, in `tests/test_guard_remedies.py`:
      `test_a_command_in_the_state_directory_offers_no_approval`, which runs a main-session Bash `touch x` with `cwd`
      the state directory and asserts `"approve --command" not in reason` and `"No approval lifts this" in reason`.
      It is seen failing before the change.

- [ ] **Step 1: Confirm the failing tests**: run `python -B -m pytest -q tests/test_guard_remedies.py`. Expected: the four
  FAIL-now cases fail on their text assertions; the pins pass.
- [ ] **Step 2: Implement** `write_denial`, the new `check_write` body, the four remedies and the `_violation` and
  `decide` changes. No check is added, removed or reordered.
- [ ] **Step 3: Correct the instructions behind the bug.**
  - `agents/manager.md` line 140: replace `(or `--path GLOB` for a file write)` with: for a protected file inside the
    project, `--path "<the path the denial names>"`, which is relative to the checkout root; a file-tool write outside
    the project or into `.apm/state/` cannot be approved, so ask the user to make that change. Add one sentence:
    Claude Code's memory folder for this project may be written from the main session without an approval. Keep the
    phrases `Ask the user in chat`, `with the Bash tool` and ``every `\` is inside quotes`` that
    `tests/test_agents.py` and `tests/test_approve_instructions.py` read.
  - `docs/tutorial.md` lines 295 to 297: the quoted denial matches the new command remedy (no `--path` clause).
  - `scripts/apm/cli_parser.py` line 42: `help="the path the user approved writing, relative to the checkout root, as
    the denial names it"`.
- [ ] **Step 4: Run** `python -B -m pytest -q tests/test_guard_remedies.py tests/test_guard_memory.py tests/test_guard_memory_folder.py tests/test_guard_paths.py tests/test_hooks.py tests/test_hooks_worktrees.py tests/test_hook_approve.py tests/test_hook_wrapper.py tests/test_guard.py tests/test_guard_approve.py tests/test_approve_instructions.py tests/test_guard_echo.py tests/test_guard_heredoc.py tests/test_guard_workflow.py tests/test_guard_debt.py tests/test_guard_continuations.py tests/test_guard_workers_wrappers.py tests/test_guard_bypasses.py tests/test_agents.py tests/test_docs.py tests/test_cli.py tests/test_own_limits.py`.
  Expected: PASS, with no existing test changed.
- [ ] **Step 5: Commit** `"Offer only an approval that can lift the denial"`.

### Task 4: Run the merge gate

- [ ] **Step 1: Run** `<CLI> gate 19`. Expected: PASS: the full suite once, `<CLI> debt check` passing, and every
  structural criterion below met. On a failure, fix the cause in the task that owns it and run the gate again.
  Merge style: `merge` (profile).

Tasks run in order: 1, 2, 3, 4. None may run in parallel: Tasks 2 and 3 both change `guard_paths.py` and
`guard.py`, and both depend on Task 1's files.

---

## Structural acceptance criteria (checked before the PR)
- Every file this plan creates or changes is at most 200 lines of logic and every function in it at most 15,
  measured by `<CLI> metrics`: `scripts/apm/guard_paths.py` (starts at 44), `scripts/apm/guard.py` (starts at about
  124, largest function 11), `scripts/hook_pretooluse.py`, `scripts/apm/cli_parser.py`, and the three new test files.
  `tests/test_own_limits.py` passes.
- `memory_folder` is pure (no file, environment or clock access) and lives in `guard_paths.py`; the environment is
  read only in `scripts/hook_pretooluse.py`. No new import between modules.
- The memory folder is added to the write roots only when the event has no `agent_id`.
- `check_write` keeps its signature and its order of checks; `_in_scope`, `is_under`, `_protected` and
  `worker_file_violation` are unchanged.
- No main-session denial text contains `--path` unless its reason is a protected path, and none contains
  `approve --` when its reason is outside the project or inside `.apm/state/`.
- `docs/adr/0006-the-main-session-writes-its-memory-folder.md` exists, lists exactly one loosened class, and has its
  row in `docs/adr/README.md`. ADR 0002 and ADR 0005 are unchanged.
- Unchanged against `main`: `scripts/apm/guard_commands.py`, `guard_workers.py`, `guard_cli.py`, `guard_data.py`,
  `guard_github.py`, `guard_words.py`, `tests/test_guard.py`, and every existing test file.
- `<CLI> debt check` passes. `<CLI> gate 19` passes.

## Allowlisted actions
None. No task writes a protected path, deletes a file, or runs a destructive command. (The safety-critical paths
are reviewed per task; they are not protected paths.)

## Risks
- **One verdict loosens, on purpose.** Main-session file-tool writes under this project's memory folder become
  allowed. ADR 0002 rule 2 makes that a must-fix unless the user approves the reading, as for ADR 0005. **Approving
  this plan approves that reading for this change**, and the plan summary must say so in those words.
- **A wrong slug fails closed.** If Claude Code names the folder differently (a long path truncated with a hash, an
  `autoMemoryDirectory` setting, a checkout reached through a symlink so `resolve()` differs from Claude Code's
  path, a submodule), the derived folder does not exist and the write is denied as today. Nothing wider opens.
  Two different checkouts whose paths sanitize alike (`C:\a b`, `C:\a-b`) share one folder; Claude Code shares it
  too.
- **`CLAUDE_CONFIG_DIR` is trusted from the hook's environment.** It comes from the user's shell or settings, not
  from a repository file (changelog). A relative or empty value is ignored.
- **ADR number.** Issue #14's plan says that if anyone wants its decision recorded it would be ADR 0006. If #14
  merges an ADR first, this record takes the next free number, and the criteria follow it.
- **Remedy texts are user-facing strings other files quote.** Task 3 keeps the phrases existing tests read
  (`. Ask the user in chat` after a command denial, `Run the approve call with the Bash tool, on its own`,
  `--command "<the exact full command>"`).

## Overlap with issue #14
- No shared file. #14 changes `scripts/apm/guard_commands.py` and creates `scripts/apm/guard_redirects.py`,
  `tests/test_guard_glued_redirects.py` and `tests/test_guard_redirects.py`; this plan touches none of them and
  #14's plan leaves `guard.py`, `guard_paths.py` and `hook_pretooluse.py` unchanged.
- No shared verdict. #14 changes command verdicts (redirect targets); this plan changes file-tool verdicts and
  denial texts. #14's tests assert `kind` only, so the text change cannot break them.
- Either may merge first. The second merges `main` in and runs its gate on the combined code, as usual.

## Approval (2026-10-18)

*Approved by the user in chat: "19 is approved", after the plan summary, which said that approving it approves the ADR 0005 reading of ADR 0002 for this one class (a main-session file-tool write under this project's memory folder), recorded in ADR 0006. The manager's pre-approval addition to Task 3 (the state-directory command denial carries the "state" remedy) is part of what was approved. The plan was written when main was at 0d49048; it is built on main at c7604bc, which adds issue #14 (`guard_commands.py`, `guard_redirects.py`), files this plan does not touch.*

## Pre-flight scan

| Tasks | Shared file or interface | Producer vs consumer | Found |
|---|---|---|---|
| 1 ↔ 2 | `tests/test_guard_memory.py` | Task 1 creates the hook-level reproductions; Task 2 turns them green through `decide(..., config_dir=...)` and the hook's `_config_dir(environ)` | agrees |
| 1 ↔ 3 | `tests/test_guard_remedies.py` | Task 1 creates the remedy tests; Task 3 adds `test_a_command_in_the_state_directory_offers_no_approval` first, then turns them green | agrees |
| 2 ↔ 3 | `scripts/apm/guard_paths.py`, `scripts/apm/guard.py` | Task 2 adds `memory_folder` and `_write_roots`; Task 3 consumes `_write_roots` and adds `write_denial` | same files, run in order |
| 2 | ADR number | ADR 0006 is free on main at c7604bc (#14 added no ADR) | agrees |
| 1, 2, 3 | #14's files | none of the three touches `guard_commands.py` or `guard_redirects.py` | disjoint |
| 1 | self | FAIL-now and pins are separated; the hook tests patch the temp root and HOME so the reproductions fail for the right reason | consistent |
| 2 | self | workers stay denied; the folder is derived from `main_root` and the config dir | consistent |
| 3 | self | text-only remedies; `check_write` keeps its signature | consistent |
| 4 | self | the gate | consistent |

Rubric check: Task 1 commits red tests on purpose. Tasks 1–3 are safety-critical: each gets its own review.

## Deferred findings
- Task 1 review (S5) and found elsewhere: ADR 0006 Consequences note that a case-variant path on macOS is denied (false positive only), and that if `~/.claude` is itself a git repository the project's protected globs apply under it (false positives only).
- Task 1 review (S4): a symlink or junction inside the memory folder pointing out of it is a known limit (realpath denies it under an is_under rule; a pin needs Developer Mode on Windows).

*Ruling after the Task 1 review: S1 (a Write to the `memory` path itself, with no file name, stays denied: the rule allows paths strictly under the folder) and S2 (a worker NotebookEdit under the folder stays denied) become pins that Task 2 adds before its code; S3 (Task 3 pins each remedy text in full, not by substring) is added to Task 3. Each constrains what the next task builds, at the cost of a few test lines.*
- Task 2 review (S2): fold `_roots_for` into one `_write_roots(target, ...)` to remove the slice coupling; Task 3 must pass `_file_violation`'s roots (from `_roots_for`) to `check_write`/`write_denial`, never call `_write_roots` alone, or the folder path itself reopens.
- Task 2 review (S3): `Path.home()` in `hook_pretooluse._config_dir` raises RuntimeError when no home dir can be found, and the fail-closed handler then denies every call; catch it and pass `config_dir=None`.
- Task 2 review (S5): pin the Windows case-variant allow and `memory/x/../y.md` (allowed today).

*Ruling after the Task 2 review: S1 is upgraded to must-fix. The plan summary told the user "nothing wider ever opens"; a memory folder that is itself a link (junction or symlink) to a broader folder opens that whole folder to main-session file tools, which is wider than the approved class. Fix in a Task 2 fix round: open the root only when the `memory` component (and its `projects/<slug>` parents) is a real folder, not a link, so a linked memory folder fails closed; pin it; state in ADR 0006 that the folder must not be a link. S4 (two more fail-closed limits: a mapped or subst drive, and a driveless `CLAUDE_CONFIG_DIR` on Windows; and the "slug folder itself" wording) rides along in the same ADR edit. Cost if wrong: a user who links their memory folder elsewhere gets the old denial.*
- Task 2 re-review: the `_link` test helper skips when neither a symlink nor a junction can be made (none skipped on this host); prefer failing, and move `import os` to the top.
- Task 2 re-review: `guard.py` calls `os.path.realpath` directly; a `guard_paths` helper would keep path resolution in one module.

*Ruling during Task 3 (2026-10-20): the manager's pre-approval addition (the state-directory command denial carries the "state" remedy) conflicts with the existing #11 pin `tests/test_guard_echo.py::test_the_state_directory_denial_reads_as_before`, which requires the reason to continue `... touch x. Ask the user in chat`, and this plan forbids editing an existing test. The plan was wrong, not the code. Smallest change that satisfies both: the "state" remedy becomes `". Ask the user in chat. No approval lifts this: APM state changes only through the CLI ({_CLI}), never by editing its files."` It still offers no approval, so it keeps what the user approved. Task 3's own full-text pin for the state remedy is updated to match (it is a new test in this task). Cost if wrong: one sentence of wording.*
- Task 3 review: pin the full state remedy on the state-directory command path too (`reason.endswith("touch x" + STATE_REMEDY)`).
- Task 3 review: `_command_violation` builds `f"{reason}: {command.strip()}"` three times; pick the pair first, format once.
- Task 3 review: `docs/platform-notes.md:29` (historical note) says "or a path glob" without saying it is checkout-relative.
- Task 3 review (found elsewhere): a main-session write to a linked worktree's own `.apm/state/x.json` is treated as a protected path and can be approved, while manager.md says `.apm/state/` writes cannot; same at base, no plausible case. A `--path` approval is not tied to a checkout (same at base).
