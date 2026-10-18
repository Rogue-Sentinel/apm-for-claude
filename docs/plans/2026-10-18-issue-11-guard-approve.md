# APM for Claude — Issue 11: The guard blocks `apm approve`, so an approval can't be recorded — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built test-first by one
> implementer in its own worktree and verified by the manager with the task's targeted tests. The whole
> branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right
> before the PR. **Every task from 1 to 5 is safety-critical and gets its own review**: Tasks 2 to 5 change
> `scripts/apm/guard*.py`, and Task 1 writes the tests and the record that fix which verdicts change and which
> must not. Each review is bounded by ADR 0002 (`docs/adr/0002-guard-threat-model.md`). Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** The approve call the guard tells the manager to make is read as data and records the approval,
also when the command holds a Windows path; a heredoc that writes text to a `.md` or `.txt` file is read as
data; and every command denial echoes the command as it was typed, not with its message arguments emptied.

**Architecture:** Three small changes in the guard, each in the module that owns it. `guard_cli.py` accepts a
backslash where bash reads it literally (inside single quotes, or inside double quotes when not before `"` or
`\`), so its quote reading still proves that nothing outside quotes chains, redirects or expands.
`guard_data.py` masks the body of a heredoc that a lone `cat` on the command's first line writes to a `.md`
or `.txt` file. The check functions stop echoing the masked segment; `guard.py` echoes the typed command once.
The denial text and the manager's and skills' approve instructions say to run the approve call with the Bash
tool, because the exemption is, and stays, Bash-only.

**Tech Stack:** Python 3, standard library only, pytest. Test command: `python -m pytest -q <files>`.

**Spec:** GitHub issue #11 (Rogue-Sentinel/apm-for-claude), and the manager's reproduction of 2026-10-18
(synthetic main-session PreToolUse events fed to `scripts/hook_pretooluse.py`): the approve call is allowed with
forward-slash paths, single quotes, an apostrophe, `…` and `python3`; it is denied as `destructive command
(recursive rm)` with a backslash path, echoing `--reason ""`; `cat > body.md <<'EOF'` with a body quoting
`git rm -r -q x` is denied; the bare `git rm -r -q ...` is denied, correctly.

## Root causes (confirmed by the planner, 2026-10-18)

1. **A backslash anywhere rules out the data exemption.** `guard_cli._UNSAFE` holds `"\\"`, so
   `is_cli_call` is false for any command with a backslash, `guard._exempt_command` does not exempt it, and the
   command scan reads the unmasked `--command` value (`git rm -r -q ...`) as a command to run. Confirmed with
   `is_cli_call` and `decide` on the repo code: `--command "git rm -r -q .claude\skills\clean-code"` and its
   single-quoted form give `cli=False`, deny.
2. **An approve call from the PowerShell tool is never exempt** (`_exempt_command` checks
   `tool_name == "Bash"`, pinned by `test_record_exemption_is_bash_only_and_main_session_only`). The same call
   with forward slashes, run from PowerShell, is denied with exactly the reported text (`recursive rm`,
   `--reason ""`). Nothing in the denial text or the manager's Safety bullet says to use Bash (only
   `agents/manager.md`'s CLI section does). The issue's own echo has forward slashes, so on the Windows XP12 host
   this is at least as likely a cause as the backslash; both produce the reported symptom. The exemption stays
   Bash-only (see ADR 0005, Task 1); the instruction is fixed (Task 5).
3. **The echo shows the masked text.** `check_command` and `worker_command_violation` run on `mask_data(command)`,
   and every reason producer appends the segment it was given: `destructive_reason`, `protected_reason`, the
   piped-delete reason, `_state_change`, `_unreadable`, `_apm_write`, `gh_write_reason`. So `--reason "x"` is
   shown as `--reason ""`, and a heredoc line is shown as if it were the command.
4. **A heredoc body is data only for `git commit -F -`.** `guard_data._HEREDOC` matches only that head, so the body
   of `cat > body.md <<'EOF'` is split on newlines and each line is scanned as a command.

**The instructions behind it.** `scripts/apm/guard.py` `_ASK_USER` tells the manager to approve "the exact full
command" with no word on the tool or on quoting; `agents/manager.md` (Safety) says the call must hold no `\` at
all, which on Windows rules out most exact commands and leaves no working path; `skills/finishing-a-branch/SKILL.md`
and `skills/worktrees/SKILL.md` repeat the approve instruction without the tool. Task 5 corrects all four.

## Platform facts this plan relies on (2026-10-18)
- Bash, double quotes: a backslash keeps its special meaning only before `$`, `` ` ``, `"`, `\` or a newline;
  elsewhere it is literal. Inside single quotes it is always literal. (Bash manual, "Double Quotes".)
- Bash heredoc: with a quoted tag (`<<'EOF'` or `<<"EOF"`) the body is not expanded; the body ends at the first
  line that is exactly the tag (`<<-` strips leading tabs first).
- Python `shlex.split` (posix): inside double quotes `\` escapes only `"` and `\`, so on the commands Task 2
  accepts it yields the same arguments bash passes. Checked by the planner with a prototype on Python 3 here:
  `"git rm -r -q .claude\skills\clean-code"` splits to `git rm -r -q .claude\skills\clean-code`.
- The Claude Code Bash tool runs bash non-interactively, so history expansion (`!`) does not apply.

## Global Constraints
- Limits (profile defaults): **15** lines of logic per function, **200** per file, for every file this plan
  creates or changes, tests included.
- Standard library only; no new dependency; no new import between guard modules (`guard_cli.py` imports only
  `guard_paths` and `paths`; `guard_data.py` imports only `re`).
- Test-first, no skipped or expected-to-fail tests, no test waits on a person, no existing test weakened, edited or
  deleted. `tests/test_guard.py` is in the debt baseline: nothing is added to it. New tests go in new files; the
  one existing test file that gains tests is `tests/test_guard_cli.py` (59 lines), and only by new test functions.
- **ADR 0002 binds every task.** No verdict loosens for a command that does what the guard must stop. The plan
  turns exactly two classes of denial into allows, both listed in ADR 0005 (Task 1) with why neither runs
  anything the threat model names: (a) one plain call of this plugin's CLI from Bash in the main session whose
  backslashes bash reads literally; (b) a lone `cat` on the command's first line writing a quoted-tag heredoc to a
  `.md` or `.txt` file. Every other verdict is unchanged, and Task 1 pins the realistic neighbors.
- The data exemption stays **Bash-only and main-session-only** (a worker has `agent_id`). `$`, backtick, `\n` and
  `\r` anywhere still rule it out.
- `scripts/hook_pretooluse.py` is not changed.
- American spelling, plain voice in docs.

## Review Focus
Threat model (ADR 0002): the manager or a cooperative worker typing a command by mistake or by misreading its
brief, here mostly while recording an approval on Windows or filing an issue body. Inputs built to evade the
check are known limits, not review targets.
1. **An approve call with a Windows path that has the retry, or anything else, chained to it** stays denied:
   `<CLI> approve --command "git rm -r -q .claude\skills\x" --reason ok; rm -rf build`, the same with
   `&& git rm -r -q .claude\skills\x`, and with `> out.txt`. Tests in Task 1
   (`test_a_chained_approve_call_with_a_windows_path_stays_denied`); code in Task 2.
2. **A backslash that bash reads as an escape** keeps the call out of the exemption: `\"` outside quotes
   (`--command \" ; rm -rf build ; \"`), `"x\" ; rm -rf build ; \""`, a path ending in `\` before the closing quote
   (`"rmdir /s /q C:\build\"`), `"\\server\share"`, and an unquoted `C:\x`. Tests in Task 1
   (`tests/test_guard_cli.py`); code in Task 2.
3. **A heredoc that feeds code stays scanned:** `bash <<'EOF'` with `rm -rf build`; `python - <<'PY'` with
   `os.system('rm -rf build')`; `cat <<'EOF' | bash`; `cat > cleanup.sh <<'EOF'` followed by `bash cleanup.sh`;
   an unquoted tag with `$(rm -rf build)`; a destructive line after the end tag; a `cat` heredoc after `cd x &&`;
   and for a worker, a `python - <<'PY'` script whose text names `apm note 4`. Tests in Task 1
   (`tests/test_guard_heredoc.py`); code in Task 4.
4. **The file a `cat` heredoc writes is still checked:** a worker's `cat > .apm/notes.md <<'EOF'` and, with
   `docs/**` protected, the main session's `cat > docs/x.md <<'EOF'` stay denied. Tests in Task 1; code in Task 4.
5. **The exemption's scope is unchanged:** the same backslash approve call from the PowerShell tool, or from a
   worker, is denied; an approval recorded for `git rm -r -q .claude\skills\clean-code` lets exactly that
   PowerShell retry through and not `git rm -r -q .claude\skills\other`. Tests in Task 1; code in Task 2.

---

## File Structure

```
scripts/apm/guard_cli.py        (modify) a backslash is accepted where bash reads it literally
scripts/apm/guard_data.py       (modify) mask the body of a first-line `cat > f.md|f.txt <<'TAG'` heredoc
scripts/apm/guard.py            (modify) echo the typed command once; denial text names the Bash tool
scripts/apm/guard_commands.py   (modify) destructive, protected and piped-delete reasons no longer echo a segment
scripts/apm/guard_workers.py    (modify) worker reasons no longer echo a segment; state reason names Write/Edit
scripts/apm/guard_github.py     (modify) gh_write_reason no longer echoes a segment
agents/manager.md               (modify) Safety: approve with the Bash tool; where a backslash may stand
skills/finishing-a-branch/SKILL.md  (modify) approve with the Bash tool
skills/worktrees/SKILL.md       (modify) approve with the Bash tool
docs/adr/0005-guard-reads-cli-calls-and-cat-heredocs-as-bash-does.md  (create) the decisions of this plan
docs/adr/README.md              (modify) index row for 0005
tests/test_guard_cli.py         (modify) unit cases for the backslash rule
tests/test_guard_approve.py     (create) decide-level: approve calls with Windows paths, and their neighbors
tests/test_hook_approve.py      (create) hook-level: approve, record, retry; file an issue from a heredoc body
tests/test_guard_echo.py        (create) a denial echoes the command as typed
tests/test_guard_heredoc.py     (create) a cat heredoc to .md/.txt is data; heredocs that feed code are not
tests/test_approve_instructions.py  (create) denial text and docs say how to approve
```

Test helpers in each new file: `ROOT = Path(__file__).resolve().parent.parent`,
`PLUGIN_CLI = (ROOT / "scripts" / "apm_cli.py").as_posix()`, `CLI = f'python "{PLUGIN_CLI}"'`,
`WINDOWS = sys.platform == "win32"`, and a local `_decide(repo, command, tool="Bash", **extra)` built on
`decide(event, Project(main_root=repo, worktree_root=repo), Profile(framework_version="0.3.0", protected_paths=...),
[], [], WINDOWS, approvals)`, as `tests/test_guard.py` does (copy the pattern; do not import from it).

---

### Task 1: Reproduce the bug as failing tests, pin the neighbors, record the decision

**Files:**
- Modify: `tests/test_guard_cli.py` (two new test functions)
- Create: `tests/test_guard_approve.py`, `tests/test_hook_approve.py`, `tests/test_guard_echo.py`,
  `tests/test_guard_heredoc.py`
- Create: `docs/adr/0005-guard-reads-cli-calls-and-cat-heredocs-as-bash-does.md`
- Modify: `docs/adr/README.md` (one row)

**Interfaces:**
- Consumes: `apm.guard.decide`, `apm.guard_cli.is_cli_call`, `hook_pretooluse.run`, `apm_cli.main`,
  `apm.state_store.init_state`, `apm.paths.find_project`, the `git_repo` fixture.
- Produces: `WIN_TARGET = "git rm -r -q .claude\\skills\\clean-code"` (Python literal; the text has single
  backslashes) in `tests/test_guard_approve.py` and `tests/test_hook_approve.py`.

Each test below is marked **FAIL now** (a reproduction; the task that turns it green is named) or **pin** (passes
now and must keep passing). Commands are shown as shell text: one `\` is one backslash in the command, so write
them in Python as raw strings or with doubled backslashes.

- [ ] **Step 1: Write the tests.**
  - `tests/test_guard_cli.py`:
    - `test_a_backslash_bash_reads_literally_keeps_the_call` (parametrized), **FAIL now**, Task 2: `is_cli_call` is
      true for `f'python "{PLUGIN_CLI}" approve --command ... --reason r'` with `--command "git rm -r -q .claude\skills\clean-code"`,
      `--command 'git rm -r -q .claude\skills\clean-code'`, `--command 'Remove-Item -Recurse -Force C:\work\build'`,
      and `task 1 t1 --status done --evidence "ran pytest tests\test_x.py"`.
    - `test_a_backslash_bash_would_read_as_an_escape_rules_the_call_out` (parametrized), **pin**: false for
      `--command \" ; rm -rf build ; \" --reason r`, `--command "x\" ; rm -rf build ; \"" --reason r`,
      `--command "rmdir /s /q C:\build\" --reason r`, `--command "\\server\share" --reason r`,
      `--command C:\x --reason r`.
  - `tests/test_guard_approve.py` (main session, Bash, `cwd` the `git_repo`):
    - `test_an_approve_call_with_a_windows_path_is_data` (parametrized on the three `--command` cases of the first
      `test_guard_cli.py` test, as `f'{CLI} approve --command ... --reason "approved in chat"'`), **FAIL now**,
      Task 2: `kind == "none"`. (The `--evidence` case is a unit test only: its masked text is already allowed.)
    - `test_a_chained_approve_call_with_a_windows_path_stays_denied` (parametrized), **pin**: `kind == "deny"` for
      `f'{CLI} approve --command "{WIN_TARGET}" --reason ok; rm -rf build'`,
      `f'{CLI} approve --command "{WIN_TARGET}" --reason ok && {WIN_TARGET}'`, and
      `f'{CLI} approve --command "{WIN_TARGET}" --reason ok > out.txt'` (each is out of the exemption, so the scan
      reads the `--command` value and denies `recursive rm`).
    - `test_the_windows_approve_call_is_not_exempt_from_powershell_or_a_worker`, **pin**: the first command of
      `test_an_approve_call_with_a_windows_path_is_data` with `tool="PowerShell"` is denied, and with
      `agent_id="w1"` is denied.
    - `test_an_approval_of_a_windows_command_covers_exactly_its_retry`, **pin**: with
      `approvals=[{"command": WIN_TARGET, "reason": "r", "cwd": str(git_repo), "expires_at": "2999-01-01T00:00:00+00:00"}]`,
      a PowerShell event running `WIN_TARGET` is `none`, and one running
      `"git rm -r -q .claude\\skills\\other"` is `deny`.
  - `tests/test_hook_approve.py` (a fixture like `tests/test_cli.py::repo`: `.apm/profile.json` with
    `framework_version` `apm.VERSION`, `init_state(find_project(git_repo))`, `monkeypatch.chdir(git_repo)`):
    - `test_the_approve_call_for_a_windows_path_passes_the_hook_and_its_retry_runs`, **FAIL now**, Task 2. Arrange
      `approve = f'{CLI} approve --command "{WIN_TARGET}" --reason "approved in chat"'`. Assert, in order:
      `hook_pretooluse.run(<Bash event for approve>, {}) == (0, "")`; `apm_cli.main(shlex.split(approve)[2:]) == 0`
      (the arguments bash would pass); `hook_pretooluse.run(<PowerShell event for WIN_TARGET>, {}) == (0, "")`.
    - `test_an_issue_body_written_by_a_heredoc_passes_the_hook`, **FAIL now**, Task 4: the manager's reproduction,
      `"cat > body.md <<'EOF'\nThe guard denied `git rm -r -q x`.\nEOF\n" + f"{CLI} github file --title T --body-file body.md"`,
      gives `(0, "")` in the main session.
  - `tests/test_guard_echo.py`, all **FAIL now**, Task 3:
    - `test_a_powershell_approve_call_is_denied_with_the_command_as_typed`: command
      `f'{CLI} approve --command "git rm -r -q .claude/skills/x" --reason "approved in chat"'`, PowerShell, main
      session: `f"destructive command (recursive rm): {command}. Ask the user in chat" in decision.reason`.
    - `test_a_chained_approve_call_is_denied_with_the_command_as_typed`: Bash,
      `f'{CLI} approve --command "rm -rf build" --reason "user said yes" && echo done'`: the same assertion shape.
    - `test_a_protected_write_is_denied_with_the_whole_command`: protected `data/*.db`, Bash,
      `'cp x data/fleet.db && git commit -m "update data/fleet.db"'`:
      `f"command touches a protected path (data/fleet.db): {command}." in decision.reason`.
    - `test_a_worker_denial_ends_with_the_command_as_typed` (parametrized): worker (`agent_id="w1"`) running
      `'python scripts/apm_cli.py note 4 --text "remember this"'` and `'gh issue create --title "Fix" --body "x"'`:
      `decision.reason.endswith(": " + command)`.
  - `tests/test_guard_heredoc.py`:
    - `test_a_heredoc_written_to_a_text_file_is_data` (parametrized), **FAIL now**, Task 4, main session `none`:
      `"cat > body.md <<'EOF'\nExplain rm -rf build\nEOF"`, `"cat <<'EOF' > notes.txt\ngit clean -fd\nEOF"`,
      `'cat >> body.md <<"EOF"\ngit reset --hard\nEOF'`, `"cat > /tmp/body.md <<-'EOF'\n\tgit push --force\n\tEOF"`.
    - `test_a_worker_may_write_text_naming_an_apm_call`, **FAIL now**, Task 4: worker,
      `"cat > notes.md <<'EOF'\nRun apm debt baseline after the merge.\nEOF"` is `none`.
    - `test_a_heredoc_that_feeds_code_stays_scanned` (parametrized), **pin**, main session `deny`:
      `"bash <<'EOF'\nrm -rf build\nEOF"`, `"python - <<'PY'\nimport os\nos.system('rm -rf build')\nPY"`,
      `"cat <<'EOF' | bash\nrm -rf build\nEOF"`, `"cat > cleanup.sh <<'EOF'\nrm -rf build\nEOF\nbash cleanup.sh"`,
      `"cat > body.md <<EOF\n$(rm -rf build)\nEOF"`, `"cat > body.md <<'EOF'\nok\nEOF\nrm -rf build"`,
      `"cd docs && cat > body.md <<'EOF'\nrm -rf build\nEOF"`.
    - `test_a_worker_script_naming_an_apm_call_stays_denied`, **pin**: worker,
      `"python - <<'PY'\nprint('apm note 4')\nPY"` is `deny` with `"APM state" in decision.reason`.
    - `test_the_file_a_heredoc_writes_is_still_checked`, **pin**: worker `"cat > .apm/notes.md <<'EOF'\nx\nEOF"` is
      `deny`; main session with protected `docs/**`, `"cat > docs/x.md <<'EOF'\nx\nEOF"` is `deny`.
    - `test_a_worker_filing_the_issue_body_is_denied_for_the_cli_call`, **pin**: worker running the manager's
      reproduction command (above) is `deny` with `"APM state" in decision.reason`.
- [ ] **Step 2: Write ADR 0005** at `docs/adr/0005-guard-reads-cli-calls-and-cat-heredocs-as-bash-does.md` from
  `skills/adr/references/adr-template.md`. Title: "ADR-0005: The guard reads an apm CLI call and a `cat` heredoc as
  data only where bash reads them literally". Status: `Accepted, 2026-10-18. Builds on ADR-0002.` (it does not amend
  it). Context: this issue's four causes above. Decision, in bold first, then the rules: the backslash rule of Task 2;
  the `cat` heredoc rule of Task 4; the exemption stays Bash-only (PowerShell's quoting, `""` and the curly quotes it
  treats as quotes, is not read); a denial echoes the command as typed. How ADR 0002 rule 2 was applied: the two
  deny-to-allow classes in Global Constraints, each with why it runs nothing in the threat model (the CLI only
  records text; `cat` only writes text), and that Task 1's pins hold every neighbor. Consequences: a path ending in
  `\` inside double quotes, `\\`, and `\"` still rule the call out (use single quotes); a `.md`/`.txt` file written
  by a heredoc and then executed is a known limit; a heredoc not on the first line, or with an unquoted tag, is still
  scanned; the echo of a long script is long. Alternatives: any backslash inside quotes, read with bash's escapes
  (wider, reasoning about `\"` inside strings is what `_UNSAFE` avoided); forward slashes only, by instruction (the
  approval must equal the retried command, which on Windows holds `\`); comparing approvals with slashes normalized
  (approves a command the user did not see); `shlex` with `punctuation_chars` as the reader (its rules differ from
  bash's in places a reviewer must then prove); exempting PowerShell (new quoting rules to prove, and not needed while
  the Bash tool exists); masking every heredoc with a quoted tag (`bash <<'EOF'` is code). Add the row
  `| [0005](0005-guard-reads-cli-calls-and-cat-heredocs-as-bash-does.md) | The guard reads an apm CLI call and a cat heredoc as data only where bash reads them literally | Accepted, 2026-10-18 |`
  to `docs/adr/README.md`.
- [ ] **Step 3: Run** `python -m pytest -q tests/test_guard_cli.py tests/test_guard_approve.py tests/test_hook_approve.py tests/test_guard_echo.py tests/test_guard_heredoc.py tests/test_docs.py`.
  Expected: every **FAIL now** test fails for the defect (a `deny` where `none` was expected; `--reason ""` or a
  segment where the typed command was expected), never for an import, fixture or syntax error; every **pin** and
  every existing test passes.
- [ ] **Step 4: Commit** `"Reproduce issue 11: the guard denies approve calls, heredoc bodies and echoes masked text"`.
  This commit is red on purpose; the manager verifies the failure reasons, not a pass.

### Task 2: Accept a backslash where bash reads it literally

**Files:**
- Modify: `scripts/apm/guard_cli.py`

**Interfaces:**
- Consumes: Task 1's tests.
- Produces: `is_cli_call(command: str, cwd: Path, windows: bool) -> bool`, signature unchanged. `_UNSAFE` becomes
  `("$", "`", "\n", "\r")`.

- [ ] **Step 1: The failing tests** are Task 1's `test_a_backslash_bash_reads_literally_keeps_the_call`,
  `test_an_approve_call_with_a_windows_path_is_data` and
  `test_the_approve_call_for_a_windows_path_passes_the_hook_and_its_retry_runs`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_guard_cli.py tests/test_guard_approve.py tests/test_hook_approve.py`.
  Expected: those three FAIL; the heredoc hook test also fails (Task 4).
- [ ] **Step 3: Implement** in `scripts/apm/guard_cli.py`: drop `"\\"` from `_UNSAFE`; a double-quoted string is
  `"(?:[^"\\]|\\[^"\\])*"` (every backslash in it is followed by a character other than `"` or `\`; `$`, backtick
  and newline are already ruled out), a single-quoted one stays `'[^']*'`; `_single_command` also returns false when
  a backslash is left in the text outside quotes. Replace the `_UNSAFE` comment with the reason the reading is exact:
  with no `\"` or `\\` inside double quotes and no backslash outside quotes, every quote ends where bash ends it, so
  what is left outside quotes is what bash reads outside quotes; and `shlex.split` reads the same arguments.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_guard_cli.py tests/test_guard_approve.py tests/test_hook_approve.py tests/test_guard.py tests/test_guard_bypasses.py tests/test_guard_workflow.py`.
  Expected: PASS, except `test_an_issue_body_written_by_a_heredoc_passes_the_hook` (Task 4).
- [ ] **Step 5: Commit** `"Read a plain apm CLI call as data when bash reads its backslashes literally"`.

### Task 3: Echo the command as typed in every command denial

**Files:**
- Modify: `scripts/apm/guard.py` (`_command_violation`, `_state_dir_write`)
- Modify: `scripts/apm/guard_commands.py` (`destructive_reason`, `protected_reason`, the piped-delete reason in
  `check_command`)
- Modify: `scripts/apm/guard_workers.py` (`_state_change`, `_unreadable`, `_apm_write`)
- Modify: `scripts/apm/guard_github.py` (`gh_write_reason`)
- Test: `tests/test_guard_echo.py` (one unit test and one pin appended)

**Interfaces:**
- Consumes: Task 1's tests.
- Produces, every signature unchanged, each return value without a trailing `: <segment>`:
  `destructive_reason(segment) -> "destructive command (<label>)" | None`;
  `protected_reason(...) -> "command touches a protected path (<token>)" | None`;
  `check_command(...)` piped case `-> "destructive command (piped recursive delete)"`;
  `gh_write_reason(segment) -> _REASON | None`; `_state_change -> _STATE_REASON`;
  `_unreadable -> "workers may not run a brace expansion too large for the guard to read"`;
  `_apm_write -> "workers do not write .apm/ or the Claude settings; " + <protected_reason>`;
  `_state_dir_write -> "command runs inside the APM state directory"`.
  `guard._command_violation` returns `f"{reason}: {command.strip()}"`, where `command` is the event's command as
  typed. File-write reasons (`check_write`, `worker_file_violation`) are unchanged and get no echo.

- [ ] **Step 1: Write the failing unit tests** in `tests/test_guard_echo.py`:
  - `test_a_check_names_what_it_found_without_echoing`: `destructive_reason("rm -rf build") == "destructive command (recursive rm)"`
    and `protected_reason("cp x data/fleet.db", ["data/*.db"]) == "command touches a protected path (data/fleet.db)"`.
  - `test_the_state_directory_denial_reads_as_before`, **pin** (it already echoes the unmasked command): a Bash
    command `touch x` run with `cwd` the project's state directory (create it) gives a reason starting
    `"APM guard: command runs inside the APM state directory: touch x. Ask the user in chat"`, so the command is
    echoed once, not twice.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_guard_echo.py`. Expected: Task 1's echo tests and
  `test_a_check_names_what_it_found_without_echoing` FAIL (a `: <segment>` suffix, or a masked echo); the pin passes.
- [ ] **Step 3: Implement** the Produces list. No verdict changes: every producer still returns a reason exactly
  when it did, and `_exempt_command` still uses `_state_dir_write` only for its truth.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_guard*.py tests/test_hook*.py`. Expected: PASS, except Task 1's
  tests owned by Tasks 2 and 4 if those are not merged yet. No existing test changed.
- [ ] **Step 5: Commit** `"Echo the command as typed in a guard denial, not with its messages emptied"`.

### Task 4: Read a `cat` heredoc written to a text file as data

**Files:**
- Modify: `scripts/apm/guard_data.py`

**Interfaces:**
- Consumes: Task 1's tests.
- Produces: `mask_data(command: str) -> str`, signature unchanged; it now also empties the body of one heredoc.

- [ ] **Step 1: The failing tests** are Task 1's `test_a_heredoc_written_to_a_text_file_is_data`,
  `test_a_worker_may_write_text_naming_an_apm_call` and `test_an_issue_body_written_by_a_heredoc_passes_the_hook`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_guard_heredoc.py tests/test_hook_approve.py`. Expected: those
  FAIL; every pin passes.
- [ ] **Step 3: Implement** in `scripts/apm/guard_data.py` a second heredoc pattern, `_CAT_HEREDOC`, and apply it in
  `mask_data` first, once, before the shell-string check (a body on the first line's heredoc is `cat`'s data whatever
  else the command runs). Its head is the command's first line (`\A\s*`), holding exactly: `cat`; one output redirect
  `>` or `>>` to an unquoted path of `[\w./:~-]` characters ending in `.md` or `.txt`; and one heredoc operator `<<`
  or `<<-` whose tag is in single or double quotes; in either order, and nothing else but blanks. The body runs to the
  first line that is the tag (blanks around it allowed, which ends the mask at or before bash ends the body). The
  replacement is the head line and the end line, as `_mask_heredoc` does; nothing after the end line is masked. Add
  to the module docstring the known limit: a file written this way and then run (`bash body.md`) is not seen.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_guard_heredoc.py tests/test_hook_approve.py tests/test_guard_data.py tests/test_guard_commands.py tests/test_guard_continuations.py tests/test_guard_bypasses.py tests/test_guard_workers_wrappers.py tests/test_guard_workflow.py`.
  Expected: PASS.
- [ ] **Step 5: Commit** `"Read a cat heredoc written to a .md or .txt file as data"`.

Tasks 2, 3 and 4 touch disjoint files and may run in parallel after Task 1. Task 5 runs after Task 3 (both change
`guard.py` and `guard_workers.py`).

### Task 5: Say how to approve, in the denial and in the instructions

**Files:**
- Modify: `scripts/apm/guard.py` (`_ASK_USER`)
- Modify: `scripts/apm/guard_workers.py` (`_STATE_REASON`)
- Modify: `agents/manager.md` (Safety, the "A guard denial is a stop" bullet)
- Modify: `skills/finishing-a-branch/SKILL.md` (the "The guard blocks these commands" bullet)
- Modify: `skills/worktrees/SKILL.md` (the "The manager never removes one" bullet)
- Create: `tests/test_approve_instructions.py`

**Interfaces:**
- Consumes: Task 3's `_command_violation` (the denial is `PREFIX + reason + ": " + command + _ASK_USER`).
- Produces: `_ASK_USER` keeps its current text and appends, with no newline:
  `" Run the approve call with the Bash tool, on its own, with the command in single quotes if it holds a double quote."`
  `_STATE_REASON` becomes `"workers do not change APM state; report to the manager instead (to search for the text, use
  the Grep tool, and to write it to a file, the Write or Edit tool: neither goes through the shell)"`.

- [ ] **Step 1: Write the failing tests** in `tests/test_approve_instructions.py`:
  - `test_the_denial_says_to_approve_from_bash`: the main-session denial of `rm -rf build` contains
    `"Run the approve call with the Bash tool, on its own"`, still contains `'--command "<the exact full command>"'`,
    and holds no `"\n"`.
  - `test_a_worker_state_denial_names_the_write_tool`: worker `"python - <<'PY'\nprint('apm note 4')\nPY"`: the reason
    contains `"Grep tool"` and `"the Write or Edit tool"`.
  - `test_the_manager_approves_from_bash_and_knows_where_a_backslash_may_stand`: the Safety section of
    `agents/manager.md` contains `"with the Bash tool"` and `"every `\` is inside quotes"`, and no longer contains
    `"holds no `\`, `$` or backtick"`.
  - `test_the_skills_approve_from_bash` (parametrized on `finishing-a-branch`, `worktrees`): the skill's text, with
    runs of whitespace collapsed to one space (the bullets wrap), contains `"approve call with the Bash tool"`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_approve_instructions.py`. Expected: all FAIL (text missing).
- [ ] **Step 3: Implement.** `_ASK_USER` and `_STATE_REASON` as in Produces. In `agents/manager.md`, replace "Run the
  approve call on its own, quoting the command in single quotes if it holds double quotes; the guard reads a CLI call
  as data only when nothing is chained to it and it holds no `\`, `$` or backtick." with "Run the approve call with
  the Bash tool (a PowerShell call is never read as data), on its own, quoting the command in single quotes if it
  holds double quotes; the guard reads a CLI call as data only when nothing is chained to it, it holds no `$` or
  backtick, and every `\` is inside quotes and, inside double quotes, not before a `"` or another `\`." Keep every
  other sentence of the bullet as it is (`tests/test_agents.py` pins several). In the two skills, "Run the approve call
  on its own" becomes "Run the approve call with the Bash tool, on its own".
- [ ] **Step 4: Run** `python -m pytest -q tests/test_approve_instructions.py tests/test_guard.py tests/test_guard_echo.py tests/test_guard_workflow.py tests/test_guard_continuations.py tests/test_agents.py tests/test_skills.py tests/test_skills_workflow.py tests/test_skills_process.py`.
  Expected: PASS.
- [ ] **Step 5: Commit** `"Tell the manager to run the approve call from Bash, and where a backslash may stand"`.

### Task 6: Run the merge gate

- [ ] **Step 1: Run** `<CLI> gate 11`. Expected: PASS: the full suite once, `<CLI> debt check` passing, and every
  structural criterion below met. On a failure, fix the cause in the task that owns it and run the gate again.

---

## Structural acceptance criteria (checked before the PR)
- Every file this plan creates or changes is at most 200 lines of logic and every function in it at most 15, measured
  by `<CLI> metrics`: `guard.py` (starts at 121), `guard_cli.py` (31), `guard_commands.py` (149), `guard_data.py`
  (28), `guard_workers.py` (61), `guard_github.py` (88), and every test file in File Structure.
  `tests/test_own_limits.py` passes.
- `scripts/hook_pretooluse.py` and `tests/test_guard.py` are unchanged against `main`.
- No existing test is edited, skipped or deleted; `tests/test_guard_cli.py` only gains functions.
  `test_record_exemption_is_bash_only_and_main_session_only` and `test_record_exemption_needs_a_single_plain_cli_call`
  pass unmodified.
- `guard_cli._UNSAFE` still holds `$`, backtick, `\n` and `\r`; `_exempt_command` still requires `tool_name == "Bash"`
  and `decide` still skips it when `agent_id` is set.
- No new import between modules: `guard_cli.py` imports only `guard_paths` and `paths` from `apm`; `guard_data.py`
  imports only `re`.
- `docs/adr/0005-guard-reads-cli-calls-and-cat-heredocs-as-bash-does.md` exists, is Accepted, and has its row in
  `docs/adr/README.md`; `docs/adr/0002-guard-threat-model.md` is unchanged.
- `guard_data.py`'s docstring names the known limit of Task 4; `guard_cli.py`'s comment states why its quote reading
  is exact.
- `agents/manager.md`, `skills/finishing-a-branch/SKILL.md` and `skills/worktrees/SKILL.md` say to run the approve
  call with the Bash tool; `agents/manager.md` no longer says the call must hold no `\`.
- `<CLI> debt check` passes. `<CLI> gate 11` passes. Merge style: `merge` (profile).

## Allowlisted actions
None. No task writes a protected path, deletes a file, or runs a destructive command. (The safety-critical paths are
reviewed per task; they are not protected paths.)

## Risks
- **The rule-2 reading of ADR 0002.** Read literally, rule 2 forbids any denial becoming an allow, which no
  false-positive fix can meet; this plan reads it as "no command that does what the guard must stop", lists the two
  flipped classes exhaustively, and pins their neighbors. The user confirms this reading by approving the plan.
- **The XP12 cause is not proven.** Both the backslash and the PowerShell tool reproduce the reported denial; the
  plan fixes the first in code and the second by instruction. If a Windows session has no Bash tool, the approve flow
  still cannot work, and exempting PowerShell would be its own issue.
- **Commands still denied after the fix:** an approve call whose command holds `$`, a backtick, both kinds of quote,
  `\"`, `\\`, or a path ending in `\` before a closing double quote (single quotes fix the last three); a heredoc not
  on the command's first line, with an unquoted tag, or to a file of another extension; and a `python - <<'PY'` edit
  script whose text names an apm state call (the remedy, the Write or Edit tool, is in the worker denial after
  Task 5). The manager's prompt says to stop and ask the user to run the command when the approve call is denied.
- **A long echo.** A denial now echoes the whole command, so a long script makes a long message, where it used to
  echo one segment. The check's label or protected token still says what was found.
- **Three copies of the approve instruction** (manager, finishing-a-branch, worktrees) can drift; Task 5's tests pin
  the shared phrase in each.

## Approval (2026-10-18)

*Approved by the user in chat: "Approved: the narrow backslash rule, Bash-only approvals, the cat-heredoc rule, and
ADR 0002 read as 'never allow a command that does what the guard must stop', recorded in ADR 0005."*

## Pre-flight scan

| Tasks | Shared file or interface | Producer vs consumer | Found |
|---|---|---|---|
| 1 ↔ 2 | `is_cli_call`, `WIN_TARGET` | Task 1's unit and decide tests call `is_cli_call(command, cwd, windows)` and `decide`; Task 2 keeps both signatures | agrees |
| 1 ↔ 3 | `tests/test_guard_echo.py` | Task 1 creates it; Task 3 appends one unit test and one pin | same file, Task 3 after Task 1 |
| 1 ↔ 3 | the echo text | Task 1 asserts `"destructive command (recursive rm): {command}. Ask the user in chat"`; Task 3 makes `_command_violation` return `f"{reason}: {command.strip()}"`, then `_ASK_USER` follows | agrees, if `_ASK_USER` starts with ". Ask the user in chat" (checked in Task 3's verification) |
| 1 ↔ 4 | heredoc tests, the hook test | Task 1's heredoc cases; Task 4's `_CAT_HEREDOC` is first-line, `cat`, `.md`/`.txt`, quoted tag | agrees |
| 1 ↔ 5 | worker state denial | Task 1's `test_a_worker_denial_ends_with_the_command_as_typed` (owned by Task 3) and Task 5's new `_STATE_REASON` text | Task 5 changes the reason before the `: command` suffix, so `endswith(": " + command)` still holds; checked in Task 5's verification |
| 2, 3, 4 | files | Task 2: `guard_cli.py`; Task 3: `guard.py`, `guard_commands.py`, `guard_workers.py`, `guard_github.py`, `tests/test_guard_echo.py`; Task 4: `guard_data.py` | disjoint, may run in parallel |
| 3 ↔ 5 | `guard.py`, `guard_workers.py` | Task 3: `_command_violation`, `_state_dir_write`, reason producers; Task 5: `_ASK_USER`, `_STATE_REASON` | same files, Task 5 after Task 3 |
| 1 | self | FAIL-now tests each name the task that turns them green; pins pass now | consistent |
| 2 | self | `_UNSAFE` drops only `\`; criteria require `$`, backtick, `\n`, `\r` stay | consistent |
| 3 | self | no verdict changes; the state-directory pin guards the double echo | consistent |
| 4 | self | the mask applies before the shell-string check, first line only; pins cover code-feeding heredocs | consistent |
| 5 | self | text-only changes, pinned by new tests; `tests/test_agents.py` pins kept | consistent |
| 6 | self | the gate | consistent |

Rubric check: Task 1 commits red tests on purpose (the plan says so). Per-task review applies to Tasks 1–5
(safety-critical). No test asserts nothing; no duplicated logic is mandated.

## Deferred findings
- Task 1 review: pin the single-quoted chained approve call, `CLI approve --command '<WIN_TARGET>' --reason ok && <WIN_TARGET>` (deny).
- Task 1 review: ADR 0005 claims a pin for "a heredoc not on the first line" that does not exist; add `"cd docs\ncat > body.md <<'EOF'\nrm -rf build\nEOF"` (deny) or reword.
- Task 1 review: pin an unquoted heredoc tag whose body quotes a command in backticks (deny).
- Task 1 review: ADR 0005's `cat` rule omits the unquoted `[\w./:~-]` target and the end-at-first-tag-line limit; its Context drops "the XP12 cause is not proven".
- Task 1 review: `tests/test_guard_cli.py` defines `CLI` after the tests; move it up beside `CALL`.
- Task 1 re-review: ADR 0005 states the literal reading of rule 2 twice (Context and Decision); could be trimmed to one place.
