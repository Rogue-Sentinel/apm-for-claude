# APM for Claude — Issue 20: Shell commands that write outside the project are never checked by the guard — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built test-first by one
> implementer in its own worktree and verified by the manager with the task's targeted tests. The whole
> branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right
> before the PR. **Tasks 1 to 6 are safety-critical and each gets its own review**: every one touches
> `scripts/apm/guard*.py`, `scripts/hook_pretooluse.py` or the tests that fix which verdicts change. Every
> review is bounded by ADR 0002 (`docs/adr/0002-guard-threat-model.md`). Steps use checkbox (`- [ ]`) syntax
> for tracking.

**Goal:** A Bash or PowerShell command that writes a file outside the project is denied, the way a Write or Edit
there already is. "Outside" means: after resolving against the command's working directory, the target is under
none of the main checkout, the current worktree, the temp folders, the profile's new `write_roots`, and, for the
main session only, this project's memory folder (ADR 0006). Reads, devices (`/dev/null`, `NUL`, `$null`),
descriptor redirects (`2>&1`) and writes that programs such as `git` and `gh` make on their own stay allowed.

**Architecture:** Two new pure modules read a command the way this check needs it: `guard_targets.py` splits it
into segments outside quotes and names the words each segment writes (redirects, `tee`, `cp`/`mv`, `mkdir`,
`touch`, `rm`, `sed -i`, `git`, and the PowerShell cmdlets), and tracks `cd`. A third, `guard_outside.py`, resolves
those words (`~`, `$HOME`, `$env:USERPROFILE`) against the tracked directory and asks whether each lands where the
session may write. `guard.py` runs it after every existing command check, so every existing denial keeps its
reason. The hook passes the home folder and `/tmp` in from the environment, as it already passes the config dir.

**Tech Stack:** Python 3, standard library only, pytest. Test command: `python -B -m pytest -q <files>`, run with the
Bash tool (the guard set below uses shell globs).

**Spec:** GitHub issue #20 (Rogue-Sentinel/apm-for-claude), and the manager's brief of 2026-10-22.

## Decision needed before approval: does the main session get the rule?

The issue leaves this to the plan, and the brief leaves it to the user. **This plan is written for option B, the
planner's recommendation.** Option A changes only what is listed under it.

- **Option A: workers only.** The main session's shell stays unchecked outside the project, as today.
  - Cost: the manager's own plausible mistakes stay open. The transcripts on this machine hold one (below): an
    APM-repo session ran `cd ".../VirtualAirline Plugin for XP12" && git fetch ...; git worktree add -b apm-init ...`
    and `apm setup` there, the incident behind the user's "stay in this repo" rule. The main session's shell also
    stays a side door to `~/.claude/settings.json` and to other projects' memory folders, which its file tools
    already may not write.
  - Delta to this plan: in Task 5, `outside_write` runs only when the event has an `agent_id`; in Task 1, every
    main-session case listed as **FAIL now** becomes a **pin** of `"none"`; the `shell_outside` remedy in Task 6 is
    dropped (workers get no remedy); ADR 0007 records option A.
- **Option B (recommended): both sessions, with the main session's memory folder open and every main-session
  denial approvable.** A main-session denial offers `approve --command`, which already works for any command
  denial (`_exempt_command`), and names `write_roots` for folders the project writes routinely.
  - Cost, named routines it breaks: in the VirtualAirline XP12 project the manager deploys the built plugin to
    `D:/X-Plane 12/Resources/plugins/VirtualAirline/` and backs up `D:/X-Plane 12/Output/VirtualAirline/career.db`
    (50 distinct commands in the transcripts), builds and logs out of tree in `C:/Users/darby/vab/` and `C:/vaR`
    (MAX_PATH workarounds; 56 distinct commands), and once cloned a repository into `~/tmp-ccs`. Each is denied
    until that project lists the folder under `write_roots` or the user approves the one command. In this repo,
    copying a session-diagnosis report "where the user asks" (`skills/session-diagnosis/SKILL.md`, step 4) needs
    an approval. Editing global config through the shell (`~/.claude/settings.json`, `~/.claude/CLAUDE.md`) needs
    an approval; the file tools already refuse it.
  - What it does not break: writes `gh`, `git`, `claude plugin ...`, `pip` or `npm` make on their own (the target
    is the program's, not a shell write target); `git config --global`; the scratchpad and the temp dir; `/tmp`;
    the memory folder; anything inside the project or its worktrees.
- **Option C (not recommended): the main session checked only for other git checkouts and the config dir.** It
  needs a second, narrower root model to reason about, and still leaves a deploy to an arbitrary folder open.

Workers need `write_roots` under either option: in the XP12 transcripts workers wrote build logs and diffs under
`C:/Users/darby/vab/` in 110 distinct commands.

## Root cause (confirmed by the planner, 2026-10-22, on the branch at 05f044c)

`decide` sends a Bash or PowerShell event to `_command_violation` (`scripts/apm/guard.py:109`), which runs three
checks: the worker rules (`guard_workers.worker_command_violation`), the state-directory check, and
`guard_commands.check_command`. `check_command` matches tokens only against the profile's protected globs, which
are checkout-relative (`protected_reason`, `guard_commands.py:181`). `_command_violation` is never given the temp
roots or the config dir: `decide` passes them only to `_file_violation`, where `guard_paths.write_denial` returns
`"outside"` for a target under no allowed root. So no command is ever compared with the project's roots. The one
outside write a worker is denied is `~/.claude/settings.json`, because its trailing sub-path matches
`WORKER_PROTECTED` (`.claude/settings.json`).

Probe on the branch code, through `hook_pretooluse.run` (a temp git repo with a profile, HOME and the temp root
patched, `O` a folder beside the repo): every one of these is `none` for both the main session and a worker:
`echo x >> <memory>/MEMORY.md`, `echo x >> ~/.claude/projects/<slug>/memory/MEMORY.md`, `echo x>>O/notes.md`,
`python x.py 2>O/err.log`, `echo x | tee -a O/a.md`, `cp README.md O/`, `mv a.txt O/a.txt`, `mkdir -p O/new`,
`touch O/t`, `sed -i 's/a/b/' O/f.md`, `git -C O commit -am x`, `cd O && echo x > f.md`, `cd O && git commit -am x`,
`echo x > ../outside.md`, and from PowerShell `Set-Content -Path O/a.md -Value x`, `'x' | Out-File O/a.md`,
`Copy-Item README.md -Destination O/r.md`, `New-Item -ItemType File -Path O/n.md`. Only
`echo {} > ~/.claude/settings.json` and `Add-Content $env:USERPROFILE/.claude/settings.json x` are denied, and only
for a worker.

**The instruction behind it.** None told anyone to write the gap. ADR 0002's list of what the guard must stop names
"writes to a protected path or to `.apm/`" and not "writes outside the project", so the command check was built
around protected globs; ADR 0006 then recorded the gap as a consequence ("Bash writes outside the project are not
checked by the guard, before or after this change"). Task 5's ADR 0007 adds the shape to the threat model and
amends both records' status lines.

## Evidence from routine work (planner probe, 2026-10-22)

The planner patched a prototype of the rule into the guard in memory (scratchpad only; no production file changed):

- **Existing tests:** with it active, every existing guard and hook test passed (1308 passed: `tests/test_guard*.py`,
  `tests/test_hook*.py`, `tests/test_approve_instructions.py`). No current verdict changed.
- **Past commands:** it was run over every Bash and PowerShell call in this machine's transcripts for the two APM
  projects (9,721 main-session calls, 19,914 worker calls). A first, naive reading (the existing `split_segments`,
  every heredoc line scanned) flagged many false positives: `sed -i 's|a|b|'` cut at the `|` inside quotes,
  `#include <a>\n...` inside a quoted sed script, `>` inside Python and C++ heredoc bodies, and
  `cd /c/.../VirtualAirline\ Plugin\ for\ XP12/...` read with `\` as `/` so the escaped spaces split the path. The
  reading this plan specifies (segments split only outside quotes, bodies of heredocs no shell runs set aside, `\`
  before a blank kept as an escape) removed those. What remains are real outside writes: `~/vab`, `C:/vaR` and the
  X-Plane folders (above), eight main-session commands operating on another checkout, worker typos that wrote to
  the drive root (`> /tmp_full_report.txt`, `rm -f ../../../../../../../tmp_tb.cpp`), and a worker
  `mkdir -p ~/.claude/plans`. Of the rest, one is a variable-built path (`cd / && rm -rf "$T"`), a known limit, and
  one the planner did not trace.

## Platform facts this plan relies on (2026-10-22)

- **Git Bash mounts `/tmp` on the Windows temp folder; Python reads `/tmp` as `C:\tmp`.** Checked on this host:
  `mount` shows `C:/Users/darby/AppData/Local/Temp on /tmp`; `os.path.realpath('/tmp')` is `C:\tmp`. On macOS
  `tempfile.gettempdir()` is under `/var/folders` while `/tmp` is `/private/tmp`. So `/tmp` is added as a shell
  temp root by the hook; the guard reads `/tmp/x` as `C:\tmp\x` and the root as `C:\tmp`, so the verdict is right.
- **Bash reads `\ ` as an escaped blank and `C:\Users` unquoted as `C:Users`;** PowerShell reads `\` as a path
  separator. The word reader treats a `\` before a letter, digit, `_`, `.`, `~` or `-` as a path separator and every
  other `\` as bash's escape, which reads both tools' usual paths correctly.
- **PowerShell expands `~` at the start of a provider path,** and `$HOME`, `$env:USERPROFILE` and `$env:HOME` name
  the home folder; names are case-insensitive. The cmdlet aliases used (`ni`, `md`, `cpi`, `mi`, `ri`, `rd`, `del`,
  `erase`, `ac`, `sl`, `copy`, `move`) are from the planner's knowledge, not verified here; a wrong alias only adds
  a denial for a program that is not a cmdlet.
- **The guard's project comes from the event's `cwd`** (`hook_pretooluse._start_dir`), so a command's starting
  directory is always inside the project it is checked against. Claude Code resets a worker's cwd between Bash
  calls.

## Global Constraints
- Limits (profile defaults): **15** lines of logic per function, **200** per file, for every file this plan creates or
  changes, tests included. Starting numbers (manager's `metrics`): `guard.py` 153 (largest function 12, `decide`),
  `guard_commands.py` 151 (8), `guard_workers.py` 62 (5), `guard_paths.py` 60 (7), `guard_data.py` 38 (6),
  `guard_redirects.py` 14 (1), `hook_pretooluse.py` 58 (10). `guard_words.py` is 28 (planner's `metrics`).
  `profile.py` has no number in the brief; by reading it is about 70, and the manager confirms with `metrics`.
- No touched file is over a limit, so no extraction is required. Task 2 moves code out of `guard.py` anyway, as its
  own pure-move commit, so the new wiring lands in a smaller file.
- Standard library only. The new pure modules read no environment, clock or file; the home folder and `/tmp` come
  from `scripts/hook_pretooluse.py` only. `guard_outside.py` touches the filesystem only through `guard_paths`
  (`realpath`).
- Import direction (no cycle): `guard_targets` → `guard_commands`, `guard_redirects`, `guard_words`;
  `guard_outside` → `guard_commands`, `guard_data`, `guard_paths`, `guard_redirects`, `guard_targets`, `paths`;
  `guard` → `guard_outside`; the hook → `guard`. `guard_commands`, `guard_redirects`, `guard_words`, `guard_data` and
  `guard_paths` import neither new module.
- Test-first; no skipped or expected-to-fail tests; no test waits on a person; no existing test edited, weakened or
  deleted. `tests/test_guard.py` is in the debt baseline: nothing is added to it. New tests go in new files.
- **ADR 0002 binds every task. This plan only adds denials.** The outside check runs after the worker, state-dir and
  `check_command` checks, so every reason given today is given unchanged; nothing is removed from any existing
  reading. `write_roots` only narrows the new denial back toward today's verdict for the folders it names.
- **File-tool verdicts do not change.** `_file_violation`, `write_denial` and `check_write` keep their behavior;
  `write_roots` and `/tmp` never reach them.
- `scripts/apm/guard_workers.py`, `guard_cli.py` and `guard_github.py` are not changed.
- **The guard set** (the targeted regression run named in the tasks):
  `python -B -m pytest -q tests/test_guard*.py tests/test_hook*.py tests/test_approve_instructions.py tests/test_own_limits.py`.
  It includes Task 1's files, so until Task 5 is built its expected result is: every test passes except Task 1's
  **FAIL now** cases, which fail exactly as Task 1 recorded. From Task 5 on, everything passes.
- American spelling, plain voice.

## Review Focus
Threat model (ADR 0002): a cooperative worker or the manager, following a brief, writes outside the project by
habit or by misreading a path: appends to Claude Code's memory, writes a build log or a diff to a home folder, copies
a file into another repository or `cd`s into one and commits, or overshoots with `..` or a leading `/`. Inputs built
to evade the check (a script that writes, `bash -c '...'`, a path in a variable, `eval`) are known limits recorded
in the modules' docstrings, not review targets.
1. **A routine command that only reads or writes inside stays allowed, in both sessions and both tools,** including
   the shapes the probe showed the naive reading gets wrong: a `|` inside a quoted `sed`/`grep` pattern, `>` inside a
   Python, C++ or markdown heredoc body, an escaped blank in a bash path, `2>/dev/null` inside `$(...)` or
   backticks, `/tmp/x` on Windows. Tests in Task 1 (`tests/test_guard_outside_routine.py`), Task 3 and Task 4; code in
   Tasks 3 to 5.
2. **Every existing denial keeps its reason:** `rm -rf O` is still "destructive command (recursive rm)", a write to
   `.apm/state/` is still "protected path", a worker's `.apm/` write is still the worker reason. Tests in Task 1; code
   in Task 5.
3. **The memory folder opens only for the main session, and only strictly under it,** for shell writes as for file
   tools; another project's memory folder, `settings.json` and the folder path itself stay denied. Tests in Task 1;
   code in Task 5.
4. **Where `cd` leaves a command:** `cd docs && echo x > a.md` is inside, `cd O && echo x > f.md` and
   `cd O && git commit` are outside, `cd O && git status` reads. Tests in Task 1 and Task 4; code in Tasks 4 and 5.
5. **`write_roots` opens exactly the named folders, for shell commands only,** and never lifts a destructive or
   protected-path denial. Tests in Task 6; code in Task 6.

---

## File Structure

```
scripts/apm/guard_paths.py         (modify) in_scope, allowed_roots, roots_for become public (moved from guard.py)
scripts/apm/guard_commands.py      (modify) is_exempt and join_continuations become public; no verdict changes
scripts/apm/guard_words.py         (modify) path_words: shell words read as paths
scripts/apm/guard_redirects.py     (modify) split_redirects, is_device: what a redirect writes
scripts/apm/guard_data.py          (modify) strip_heredoc_bodies: set aside bodies no shell runs
scripts/apm/guard_targets.py       (create) segments outside quotes; the words each segment writes; cd: pure
scripts/apm/guard_outside.py       (create) Reach (where a session may write) and outside_write
scripts/apm/guard.py               (modify) decide(home=, shell_temp=); runs outside_write last; shell_outside remedy
scripts/hook_pretooluse.py         (modify) passes the home folder and SHELL_TEMP_ROOTS
scripts/apm/profile.py             (modify) Profile.write_roots
agents/manager.md                  (modify) Safety: where shell commands may write; write_roots needs the user's yes
docs/tutorial.md                   (modify) the write_roots key in "Settings you can change"
docs/adr/0007-shell-commands-write-only-where-the-session-may.md   (create)
docs/adr/0002-guard-threat-model.md                (modify) status line only: "Amended by ADR-0007."
docs/adr/0006-the-main-session-writes-its-memory-folder.md   (modify) status line only: "Amended by ADR-0007."
docs/adr/README.md                 (modify) the 0007 row; the 0002 and 0006 status cells
tests/test_guard_outside.py              (create) decide-level reproductions, Bash, both sessions
tests/test_guard_outside_powershell.py   (create) decide-level reproductions and pins, PowerShell tool
tests/test_guard_outside_routine.py      (create) decide-level pins of routine work, both tools
tests/test_guard_outside_hook.py         (create) hook-level: ~ and $HOME forms, memory via ~, /tmp, a worktree
tests/test_guard_path_words.py           (create) unit tests for path_words
tests/test_guard_redirect_targets.py     (create) unit tests for split_redirects and is_device
tests/test_guard_heredoc_bodies.py       (create) unit tests for strip_heredoc_bodies
tests/test_guard_targets.py              (create) unit tests for command_segments, write_targets, cd_target
tests/test_guard_outside_reach.py        (create) unit tests for Reach.resolve
tests/test_guard_write_roots.py          (create) decide-level tests for write_roots and the remedy text
tests/test_profile_write_roots.py        (create) load and write the write_roots key
```

Test helpers (copy the patterns, do not import them across test files):
- **Decide-level** (`test_guard_outside*.py` except `_hook`, `test_guard_write_roots.py`), as
  `tests/test_guard_redirects_streams.py` does: `WINDOWS = sys.platform == "win32"`, `WORKER = {"agent_id": "w1"}`,
  `BOTH = pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])`. Fixtures under `tmp_path`:
  `repo` (`tmp_path/"repo"`, made, not a git repo), `other` (`tmp_path/"other"`, made), `scratch` (`tmp_path/"scratch"`),
  `cfg` (`tmp_path/"cfg"`). `_decide(repo, command, *, tool="Bash", extra=None, cwd=None, approvals=(), allowlist=(),
  protected=(), **kw) -> Decision` builds `{"tool_name": tool, "cwd": str(cwd or repo), "tool_input": {"command":
  command}, **extra}` and calls `decide(event, Project(main_root=repo, worktree_root=repo),
  Profile(framework_version="0.3.0", protected_paths=protected), list(allowlist), [scratch], WINDOWS,
  list(approvals), config_dir=cfg, **kw)`. Task 1 passes no `home` or `shell_temp` (they do not exist yet), so `/tmp`
  is not a root here and the tests hold on Linux, where `tmp_path` is under `/tmp`. Paths go into commands as
  `p.as_posix()`, and where a case says "native", as `str(p)`. `memory = cfg / "projects" / re.sub(r"[^A-Za-z0-9]",
  "-", str(repo)) / "memory"`.
- **Hook-level** (`test_guard_outside_hook.py`), as `tests/test_guard_memory.py` does: `_init(repo)`, `_run(cwd,
  command, environ, tool="Bash", **extra) -> str` sends a command event through `hook_pretooluse.run`. A fixture
  `isolated` sets `HOME` and `USERPROFILE` to `tmp_path/"home"`, patches `hook_pretooluse.tempfile.gettempdir` to
  `tmp_path/"scratch"`, and `monkeypatch.setattr(hook_pretooluse, "SHELL_TEMP_ROOTS", (), raising=False)` so `/tmp`
  (which holds `tmp_path` on Linux) opens nothing. Every test uses `isolated` except
  `test_a_write_under_slash_tmp_is_allowed`, which sets only `HOME`/`USERPROFILE` and the scratch patch, so it runs
  against the real `SHELL_TEMP_ROOTS`. environ is `{}` (so the config dir is `home/.claude`).

---

### Task 1: Reproduce the bug as failing tests and pin routine work

**Files:**
- Create: `tests/test_guard_outside.py`
- Create: `tests/test_guard_outside_powershell.py`
- Create: `tests/test_guard_outside_routine.py`
- Create: `tests/test_guard_outside_hook.py`

**Interfaces:**
- Consumes: `apm.guard.decide`, `apm.guard.Decision`, `apm.guard.PREFIX`, `apm.paths.Project`, `apm.profile.Profile`,
  `hook_pretooluse.run`, the `git_repo` fixture, `conftest.run_git`.
- Produces: nothing a later task imports. Task 5 turns the **FAIL now** cases green. `hook_pretooluse.SHELL_TEMP_ROOTS`
  is the exact name Task 5 must define (the hook fixture patches it with `raising=False`).

Each case is **FAIL now** (a reproduction: `none` today, `deny` after Task 5) or **pin** (passes now and must keep
passing). `O` is `other.as_posix()`, `S` is `scratch.as_posix()`, `M` is `memory.as_posix()`. Heredocs use `\n`.

- [ ] **Step 1: Write `tests/test_guard_outside.py`** (Bash):
  - `test_a_redirect_outside_the_project_is_denied`, `@BOTH`, `kind == "deny"`. **FAIL now:** `echo x >> O/notes.md`,
    `echo x>>O/notes.md`, `python x.py 2>O/err.log`, `python x.py &>O/out.log`, `echo x > ../outside.md`,
    `"cat > O/body.md <<'EOF'\nx\nEOF"`, `git diff > O/d.diff`, `echo x > "O/with space.md"`, `pytest -q > O/t.log 2>&1`,
    `"echo x > O/a.md\r\n"` (a CR in the command).
  - `test_a_program_writing_outside_the_project_is_denied`, `@BOTH`, `deny`. **FAIL now:** `echo x | tee -a O/a.md`,
    `cp README.md O/`, `cp -r src O/src`, `cp -t O a b`, `mv a.txt O/a.txt`, `mkdir -p O/new`, `touch O/t`,
    `rm O/old.md`, `sed -i 's/a/b/' O/f.md`, `sed -i -e 's/a/b/' O/f.md`, `cp README.md ../../x.md`, `touch /tmp_x.txt`.
  - `test_git_or_cd_into_another_checkout_is_denied`, `@BOTH`, `deny`. **FAIL now:** `git -C O commit -am x`,
    `git -C ../other add .`, `cd O && git commit -am x`, `cd O && git fetch origin`, `cd O && echo x > f.md`,
    `cd .. && touch x`, `cd O; cp a b`.
  - `test_the_memory_folder_opens_only_for_the_main_session`: main, `echo x >> M/MEMORY.md`, `cp notes.md M/`,
    `echo x | tee -a M/MEMORY.md`: `none` (**pin**); the same as a worker: `deny` (**FAIL now**).
  - `test_the_rest_of_the_config_dir_stays_denied`, `@BOTH`, `deny`. **FAIL now:** `echo {} > cfg/settings.json`,
    `echo x >> cfg/CLAUDE.md`, `echo x >> cfg/projects/C--other-repo/memory/MEMORY.md`, `echo x >> M2/x.md` with `M2`
    the sibling `memory2`, `mkdir -p M` (the folder itself).
  - `test_an_outside_denial_names_the_target_and_offers_a_command_approval`: main, `echo x >> O/notes.md`:
    `reason.startswith(PREFIX + "command writes outside the project and the temp folders (")`, `"notes.md" in reason`,
    `'approve --command "<the exact full command>"' in reason`. Worker: the same prefix and `"Ask the user" not in
    reason`. **FAIL now.**
- [ ] **Step 2: Write `tests/test_guard_outside_powershell.py`** (`tool="PowerShell"`):
  - `test_a_powershell_write_outside_the_project_is_denied`, `@BOTH`, `deny`. **FAIL now:**
    `Set-Content -Path O/a.md -Value x`, `Set-Content O/a.md x`, `Add-Content O/a.md x`, `'x' | Out-File O/a.md`,
    `'x' | Out-File -FilePath O/a.md -Append`, `'x' | Tee-Object -FilePath O/a.md`,
    `Copy-Item README.md -Destination O/r.md`, `Copy-Item README.md O/r.md`, `Move-Item a.txt -Destination O/a.txt`,
    `New-Item -ItemType File -Path O/n.md`, `New-Item -ItemType Directory O/d`, `Remove-Item O/old.md`,
    `python x.py > O/out.log`, `python x.py *> O/all.log`, `Set-Location O; git commit -am x`, `cd O; Set-Content f.md x`,
    and native backslash forms `Set-Content -Path "<str(other)>\a.md" -Value x`, `Copy-Item README.md <str(other)>\r.md`.
  - `test_a_routine_powershell_command_stays_allowed`, `@BOTH`, `none`. **Pin:** `git fetch origin *>$null`,
    `python x.py > $null`, `python x.py 2>&1`, `Set-Content -Path docs/a.md -Value x`, `Copy-Item O/x.md -Destination docs/`,
    `Get-Content O/x.md`, `Set-Content -Path S/body.md -Value x`, `New-Item -ItemType Directory -Force S/d`,
    `Set-Location docs; Set-Content a.md x`, `Set-Content -Path docs/a.md -Value "see O/x"`.
- [ ] **Step 3: Write `tests/test_guard_outside_routine.py`**, every case `@BOTH` and a **pin** (`none`) unless named:
  - `test_writing_the_temp_folder_stays_allowed`: `echo x > S/body.md`, `"cat > S/b.md <<'EOF'\nx\nEOF"`,
    `mkdir -p S/probe && cp a S/probe/`, `tee S/log.txt`, `cd S && echo x > f`.
  - `test_a_device_or_a_descriptor_is_not_a_file_write`: `python x.py >/dev/null`, `python x.py 2>/dev/null`,
    `python x.py >/dev/null 2>&1`, `python x.py > NUL`, `pytest -q 2>&1 | tail -5`, `echo x >&2`, `echo x 1>&2`,
    `tee /dev/stderr`, `cp x /dev/null`, `x=$(git rev-parse HEAD 2>/dev/null)`, ``x=`git rev-parse HEAD 2>/dev/null` ``.
  - `test_writing_inside_the_project_stays_allowed`: `echo x > docs/a.md`, `cp a b`, `mkdir -p build/x`,
    `cd docs && echo x > a.md`, `cd docs && cd .. && touch x`, `cd sub/dir && git add . && git commit -m x`,
    `git -C docs status`, `echo x > <repo.as_posix()>/docs/a.md`.
  - `test_an_escaped_blank_in_a_bash_path_is_read_as_bash_reads_it`: with a project root `tmp_path/"my repo"`,
    `cd <posix root with each blank written as "\ ">/docs && git add a.md` and `echo x > my\ notes.md`: `none`.
  - `test_a_quoted_pipe_or_redirect_sign_is_not_a_write`: `sed -i 's|#include <a>|#include <a>\n#include <b>|' src/x.cpp`,
    `grep -E 'a|b>c' docs`, `grep '>' O/x.md`, `grep "a > b" O/x.md`, `git commit -m "write > ~/x"`, `echo "a > O/x"`,
    `echo 'see ../x > y'`.
  - `test_a_heredoc_body_no_shell_runs_is_not_read_as_commands`:
    `"python - <<'PY'\nif a > b: print(a)\nopen('/x') > 0\nPY"`, `"cat > docs/n.md <<'EOF'\n> quoted ../x\nEOF"`,
    `"gh issue create --title t --body \"$(cat <<'EOF'\n> see /etc/x\nEOF\n)\""`.
  - `test_programs_that_write_on_their_own_stay_allowed`: `git commit -am x`, `git push origin HEAD`, `git fetch`,
    `git config --global user.name x`, `gh pr create --title t --body-file S/b.md`, `gh issue list > S/issues.txt`,
    `pip install -e .`.
  - `test_reading_outside_the_project_stays_allowed`: `cat O/x.md`, `ls ..`, `grep -r foo O`, `git -C O log --oneline`,
    `git -C O status`, `cd O && git status`, `cd O && ls`, `cp O/x.md docs/`, `diff O/a docs/a`.
  - `test_an_approval_lifts_an_outside_write_only_in_the_main_session`: approval `{"command": "echo x >> O/notes.md",
    "reason": "r", "cwd": str(repo), "expires_at": <now + 5 min, ISO>}`: main `none` (**pin**), worker `deny`
    (**FAIL now**).
  - `test_a_plan_allowlist_prefix_lifts_an_outside_write`: allowlist `[{"command": "cp dist/app.zip O/"}]`,
    `cp dist/app.zip O/`: `none` for both (**pin**).
  - `test_an_existing_denial_keeps_its_reason`, `PREFIX + reason` starts with the old text for both sessions (**pin**):
    `rm -rf O` → `"destructive command (recursive rm)"`; protected `("data/*.db",)`, `echo x > data/x.db` →
    `"command touches a protected path"`; main `echo x > .apm/state/s.json` → `"command touches a protected path"`;
    worker `echo x > .apm/n.md` → `"workers do not write .apm/ or the Claude settings"`.
- [ ] **Step 4: Write `tests/test_guard_outside_hook.py`:**
  - `test_a_write_under_home_is_denied`, both sessions, Bash unless named, `deny`. **FAIL now:**
    `echo x >> ~/notes.md`, `echo x >> $HOME/notes.md`, `echo x >> "${HOME}/notes.md"`, `cp README.md ~/`,
    PowerShell `Add-Content $env:USERPROFILE/notes.md x`, PowerShell `Add-Content $HOME\notes.md x`.
  - `test_the_settings_file_under_home_is_denied_for_both`: `echo {} > ~/.claude/settings.json`: worker `deny`
    (**pin**: `WORKER_PROTECTED` today), main `deny` (**FAIL now**).
  - `test_the_memory_folder_under_home_is_the_main_sessions_own`: `echo x >> ~/.claude/projects/<slug>/memory/MEMORY.md`
    with `<slug>` from `find_project(repo).main_root`: main `none` (**pin**), worker `deny` (**FAIL now**).
  - `test_a_worktree_session_writes_its_main_checkout`: cwd a linked worktree `.claude/worktrees/w1` of `git_repo`
    (made with `run_git`), `echo x > <git_repo posix>/docs/a.md`: `none` (**pin**); `echo x > <git_repo.parent
    posix>/sibling/x.md`: `deny` (**FAIL now**).
  - `test_reading_home_stays_allowed`: `cat ~/.claude/settings.json`, `ls ~`: `none` (**pin**).
  - `test_a_write_under_slash_tmp_is_allowed` (no `isolated`): `echo x > /tmp/body.md`, `cat > /tmp/b.md <<'EOF'\nx\nEOF`
    (with `\n`): `none` (**pin**).
- [ ] **Step 5: Run** `python -B -m pytest -q tests/test_guard_outside.py tests/test_guard_outside_powershell.py tests/test_guard_outside_routine.py tests/test_guard_outside_hook.py`.
  Expected: every **FAIL now** case fails for the defect (`'none' == 'deny'`, or the reason assertion), never for an
  import, fixture or syntax error; every **pin** passes. Each file is under the limits (`tests/test_own_limits.py`).
- [ ] **Step 6: Commit** `"Reproduce issue 20: shell writes outside the project are never checked"`. This commit is
  red on purpose; the manager verifies the failure reasons, not a pass.

### Task 2: Make the write roots and segment helpers public (pure move)

**Files:**
- Modify: `scripts/apm/guard_paths.py` (receive `allowed_roots`, `roots_for`; rename `_in_scope` → `in_scope`)
- Modify: `scripts/apm/guard.py` (import them; drop `_write_roots`, `_roots_for` and the now-unused imports)
- Modify: `scripts/apm/guard_commands.py` (rename `_is_exempt` → `is_exempt`; extract `join_continuations`)

**Interfaces:**
- Produces, bodies unchanged:
  - `in_scope(target: Path, project: Project, temp_roots: Sequence[Path]) -> bool` (was `_in_scope`).
  - `allowed_roots(project: Project, temp_roots: Sequence[Path], config_dir: Path | None, worker: bool) -> list[Path]`
    (was `guard._write_roots`).
  - `roots_for(target: Path, project: Project, temp_roots: Sequence[Path], config_dir: Path | None, worker: bool) ->
    list[Path]` (was `guard._roots_for`).
  - `is_exempt(segment: str, allowed_prefixes: Sequence[str]) -> bool` (was `_is_exempt`).
  - `join_continuations(command: str) -> str`: the continuation join `split_segments(..., join=True)` does today;
    `split_segments` calls it.
- No test references the old private names (checked by the planner with Grep).

- [ ] **Step 1: Run** the guard set. Expected: the baseline (passes except Task 1's FAIL-now cases); note the counts.
- [ ] **Step 2: Move and rename** as above, one at a time, running the guard set after each. No body changes; the
  move also takes guard.py's direct `os.path.realpath` call into `guard_paths` (a #19 deferred finding).
- [ ] **Step 3: Run** the guard set. Expected: the same passes and the same failures as Step 1, no test changed.
  `guard.py` drops to about 144 lines of logic.
- [ ] **Step 4: Commit** `"Make the guard's write roots and segment helpers public, without changing any verdict"`.

### Task 3: Read what a redirect writes, and set aside heredoc bodies no shell runs

**Files:**
- Modify: `scripts/apm/guard_words.py` (add `path_words`)
- Modify: `scripts/apm/guard_redirects.py` (add `split_redirects`, `is_device`; docstring)
- Modify: `scripts/apm/guard_data.py` (add `strip_heredoc_bodies`; docstring)
- Test: `tests/test_guard_path_words.py`, `tests/test_guard_redirect_targets.py`, `tests/test_guard_heredoc_bodies.py`

**Interfaces:**
- Produces:
  - `path_words(text: str) -> list[str]` in `apm.guard_words`: the shell words of `text` with quotes removed, a `\`
    before `[A-Za-z0-9_.~-]` read as `/`, every other `\` read as bash's escape; on an unterminated quote, the text
    split on blanks. Uses `shlex` (posix).
  - `split_redirects(segment: str) -> tuple[str, list[str]]` in `apm.guard_redirects`: the segment with every unquoted,
    unescaped redirect (its descriptor digits, its operator `[&*]?[<>][<>&]*`, and the word after it) replaced by a
    blank; and, in order, the word of each redirect whose operator holds `>`, read with `path_words`, except a
    descriptor after an operator ending in `&` (`1`, `2`, `-`, `2-`). A word ends at a blank or any of ``<>&|;()` ``.
    Quoted strings and escapes are matched as `space_redirects` matches them.
  - `is_device(word: str) -> bool` in `apm.guard_redirects`: true for `/dev/null`, `/dev/stdout`, `/dev/stderr`,
    `/dev/tty`, `/dev/fd/<digits>`, and, ignoring case, `nul`, `nul:` and `$null`.
  - `strip_heredoc_bodies(command: str) -> str` in `apm.guard_data`: each heredoc's body removed, its head line and its
    end-tag line kept, unless the head line names a shell (`bash`, `sh`, `zsh`, `dash`, `ksh`, `mksh`, `pwsh`,
    `powershell`, `cmd`, by path, `.exe`, any case, not preceded by a word character, `.` or `-`), or the tag is
    unquoted and the body expands (`$(` or a backtick, as `_mask_heredoc` decides). A command holding `\r` is
    returned whole, as `mask_data` does. A body ends at the first line that is the tag, blanks allowed.
  - `mask_data`, `space_redirects`, `shell_words` and every existing function are unchanged.

- [ ] **Step 1: Write the failing unit tests.**
  - `test_guard_path_words.py`, `test_shell_words_read_as_paths` (exact lists): `cd /c/My\ Repo/sub` →
    `["cd", "/c/My Repo/sub"]`; `Copy-Item a C:\Users\me\b` → `["Copy-Item", "a", "C:/Users/me/b"]`;
    `echo "C:\a b\c"` → `["echo", "C:/a b/c"]`; `Add-Content $HOME\.claude\x a` → `["Add-Content", "$HOME/.claude/x",
    "a"]`; `echo "a` → `["echo", '"a']`.
  - `test_guard_redirect_targets.py`, `test_the_files_a_redirect_writes` (targets, and `rest.split()`):
    `echo x >> a.md` → `["a.md"]`, `["echo", "x"]`; `cat>docs/x.md` → `["docs/x.md"]`, `["cat"]`;
    `python x.py 2>err.log` → `["err.log"]`, `["python", "x.py"]`; `python x.py &>out.log` → `["out.log"]`;
    `python x.py *> all.log` → `["all.log"]`; `echo x >& out.log` → `["out.log"]`; `cat < in.txt > out.txt` →
    `["out.txt"]`, `["cat"]`; `cat <<'EOF' > body.md` → `["body.md"]`, `["cat"]`;
    `cmd > "C:\Users\me\a b.md"` → `["C:/Users/me/a b.md"]`; `x=$(git rev-parse HEAD 2>/dev/null)` → `["/dev/null"]`.
  - `test_a_descriptor_or_a_quoted_sign_is_no_target` (targets `[]`): `python x.py 2>&1`, `echo x >&2`, `x 2>&-`,
    `x <&3`, `echo "a > b"`, `grep '>' x`, `echo a\>b`.
  - `test_a_device_is_not_a_file` (parametrized): true for `/dev/null`, `/dev/stderr`, `/dev/fd/2`, `NUL`, `nul`,
    `$null`, `$NULL`; false for `/dev/nullx`, `null`, `nul.txt`, `docs/null`, `/dev/sda`.
  - `test_guard_heredoc_bodies.py`: `test_a_body_no_shell_runs_is_set_aside`:
    `"python - <<'PY'\nx > /y\nPY"` → `"python - <<'PY'\nPY"`;
    `"cat > a.md <<'EOF'\n> q\nEOF\necho done > ../x"` → `"cat > a.md <<'EOF'\nEOF\necho done > ../x"`;
    `"gh issue create --body \"$(cat <<'EOF'\n> x\nEOF\n)\""` → the same without `> x\n`.
    `test_a_body_a_shell_runs_is_kept` (output equals input): `"bash <<'EOF'\necho x > /y\nEOF"`,
    `"cat <<'EOF' | sh\necho x > /y\nEOF"`, `"pwsh -NoProfile <<'EOF'\nx\nEOF"`, `"python - <<EOF\n$(touch /y)\nEOF"`,
    `"python - <<'PY'\r\nx > /y\r\nPY"` (a CR), `"cat <<< 'x > /y'"`.
- [ ] **Step 2: Run** `python -B -m pytest -q tests/test_guard_path_words.py tests/test_guard_redirect_targets.py tests/test_guard_heredoc_bodies.py`.
  Expected: FAIL (the functions cannot be imported).
- [ ] **Step 3: Implement** the four functions. Docstrings: `guard_redirects` adds that `split_redirects` is the
  reader `#13` can use for `_is_read_only`; `guard_data` says why bodies are set aside for the outside check only (a
  body no shell runs is data to its program, and reading it as commands produced the false positives measured in
  this plan), and that the destructive and protected checks still read bodies as ADR 0005 says.
- [ ] **Step 4: Run** the guard set (which includes the three new files). Expected: the new files pass; otherwise as
  the guard set's note says; no existing test changed.
- [ ] **Step 5: Commit** `"Read the files a redirect writes, and set aside heredoc bodies no shell runs"`.

### Task 4: Name the paths each segment of a shell command writes

**Files:**
- Create: `scripts/apm/guard_targets.py`
- Test: `tests/test_guard_targets.py`

**Interfaces:**
- Consumes: Task 2's `join_continuations`; Task 3's `path_words`, `split_redirects`.
- Produces, in `apm.guard_targets` (pure; `re` and the three imports only):
  - `command_segments(text: str) -> list[str]`: `join_continuations(text)` split at `&&`, `||`, `;`, `|`, a newline,
    and a lone `&` (`(?<![<>&])&(?![&>])`), only where these stand outside quotes and escapes; blanks stripped, empty
    pieces dropped.
  - `write_targets(segment: str) -> list[str]`: the redirect targets of `split_redirects(segment)`, then the program
    targets of the rest, read with `path_words`. The program is the first word after leading `NAME=value` words and
    the wrappers `sudo`, `env`, `command`, `nohup`, `time`, with a leading `(` or `{` dropped, by basename, lowercased,
    `.exe` dropped. An option is a word starting with `-`.
    - every non-option word: `tee`, `touch`, `mkdir`, `rm`, `rmdir`, `unlink`, `set-content`, `add-content`, `ac`,
      `out-file`, `tee-object`, `new-item`, `ni`, `md`, `remove-item`, `ri`, `del`, `erase`, `rd`; the word after a
      PowerShell value option (`-value`, `-encoding`, `-itemtype`, `-type`, `-inputobject`, `-width`, `-stream`,
      `-delimiter`, `-name`, any case) is not a target.
    - the destination: `cp`, `mv`, `copy-item`, `cpi`, `copy`, `move-item`, `mi`, `move`: the value of `-t`,
      `--target-directory` (spaced or `=`) or `-destination` (any case), else the last non-option word when there are
      at least two.
    - `sed` with an `-i` option (`-i`, `-i.bak`, a flag group holding `i`, `--in-place`): its file words: every
      non-option word except the values of `-e`/`--expression`/`-f`/`--file` when one is given, else every
      non-option word after the first (the script).
    - `git`: `[the -C value, or "."]` unless the subcommand reads: `status`, `log`, `diff`, `show`, `blame`,
      `rev-parse`, `ls-files`, `ls-tree`, `cat-file`, `describe`, `grep`, `shortlog`, `reflog`, `rev-list`, `merge-base`,
      `for-each-ref`, `show-ref`, `name-rev`, `help`, `version`; or `branch`, `remote`, `tag`, `config`, `worktree`,
      `stash` with no word after them but options, `list` and `show`. No subcommand: no target. Options before the
      subcommand are skipped; `-c` takes a value.
    - every other program: no program targets.
  - `cd_target(segment: str) -> str | None`: for `cd`, `chdir`, `pushd`, `set-location`, `sl`, `push-location`, its
    first non-option word, or `"~"` when it has none; `None` for `cd -` and for any other program.
  - Module docstring: what it reads, and the known limits: writes a program makes itself (`python -c` and scripts,
    `node -e`, `perl -i`, `cmake -B`, `curl -o`, `wget -O`, `tar -C`, `unzip -d`, `dd of=`, `install`, `ln`, `rsync`,
    `robocopy`, `xcopy`, `git clone <dir>`, `git worktree add <dir>`, `git format-patch -o`, .NET calls such as
    `[IO.File]::WriteAllText`); wrappers beyond the short list (`xargs`, `find -exec`, `timeout`); a command string
    another shell runs (`bash -c '...'`), `$(...)` and `eval`; `>|` (cut at the `|`); `popd`, `cd -` and a subshell's
    `cd` (which this reading keeps past the `)`, failing closed); PowerShell parameter abbreviations (`-Dest`),
    arrays (`-Path a,b`), `Join-Path` expressions and `''` quoting; a positional PowerShell value read as a target
    (failing closed).

- [ ] **Step 1: Write the failing unit tests** in `tests/test_guard_targets.py` (exact lists):
  - `test_command_segments_split_only_outside_quotes`: `a && b` → `["a", "b"]`; `a | b; c` → `["a", "b", "c"]`;
    `sed 's|a|b|' f && g` → `["sed 's|a|b|' f", "g"]`; `x 2>&1 | y` → `["x 2>&1", "y"]`; `x &>f` → `["x &>f"]`;
    `x & y` → `["x", "y"]`; `echo "a && b"` → one; `"a \\\n&& b"` (a continued line) → `["a", "b"]`.
  - `test_the_words_a_segment_writes`: `echo x >> a.md` → `["a.md"]`; `tee -a a.md b.md` → `["a.md", "b.md"]`;
    `cp a b c dir/` → `["dir/"]`; `cp a` → `[]`; `cp -t dir a b` → `["dir"]`; `cp --target-directory=dir a` →
    `["dir"]`; `mv a b` → `["b"]`; `cp a b 2>/dev/null` → `["/dev/null", "b"]`; `mkdir -p a b` → `["a", "b"]`;
    `rm -f x` → `["x"]`; `sed -i 's/a/b/' f1 f2` → `["f1", "f2"]`; `sed -i -e 's/a/b/' -e 's/c/d/' f` → `["f"]`;
    `sed -i.bak 's/a/b/' f` → `["f"]`; `sed -n 's/a/b/p' f` → `[]`; `sudo tee /etc/x` → `["/etc/x"]`;
    `FOO=1 cp a b` → `["b"]`; `/usr/bin/tee a` → `["a"]`; `tee.exe a` → `["a"]`; `cd x` → `[]`.
  - `test_the_words_a_powershell_segment_writes`: `Set-Content -Path a.md -Value x` → `["a.md"]`;
    `Set-Content a.md x` → `["a.md", "x"]`; `Out-File -FilePath a.md -Append` → `["a.md"]`;
    `Copy-Item a -Destination b` → `["b"]`; `Copy-Item -Path a -Destination b -Recurse` → `["b"]`;
    `Copy-Item a b` → `["b"]`; `New-Item -ItemType Directory -Force d` → `["d"]`; `New-Item -Path p -Name f` → `["p"]`;
    `COPY-ITEM a b` → `["b"]`; `Remove-Item x` → `["x"]`.
  - `test_git_writes_its_working_directory_unless_it_reads`: `git commit -am x` → `["."]`; `git -C ../o commit` →
    `["../o"]`; `git -c a=b commit` → `["."]`; `git -C ../o log` → `[]`; `git status` → `[]`; `git branch -a` → `[]`;
    `git branch new` → `["."]`; `git remote -v` → `[]`; `git worktree list` → `[]`; `git --version` → `[]`.
  - `test_a_program_that_writes_nothing_has_no_targets`: `cat a b`, `ls x`, `grep x y`, `python x.py out`,
    `gh pr create --body-file b`: `[]`.
  - `test_where_cd_goes`: `cd docs` → `"docs"`; `cd` → `"~"`; `cd "my dir"` → `"my dir"`; `cd -` → `None`;
    `pushd ../x` → `"../x"`; `Set-Location -Path x` → `"x"`; `sl x` → `"x"`; `cd docs 2>/dev/null` → `"docs"`;
    `ls` → `None`.
- [ ] **Step 2: Run** `python -B -m pytest -q tests/test_guard_targets.py`. Expected: FAIL (no module).
- [ ] **Step 3: Implement** `guard_targets.py`. Keep each table a module constant and each family a small function, so
  no function passes 15 lines.
- [ ] **Step 4: Run** the guard set. Expected: `tests/test_guard_targets.py` passes; otherwise as the guard set's
  note says.
- [ ] **Step 5: Commit** `"Name the paths each segment of a shell command writes"`.

### Task 5: Deny a shell command that writes outside the project

**Files:**
- Create: `scripts/apm/guard_outside.py`
- Modify: `scripts/apm/guard.py` (`decide` gains `home`, `shell_temp`; `_violation` builds a `Reach`;
  `_command_violation` runs `outside_write` last)
- Modify: `scripts/hook_pretooluse.py` (`SHELL_TEMP_ROOTS`, `_home`, and both passed to `decide`)
- Modify: `agents/manager.md` (Safety: one bullet)
- Create: `docs/adr/0007-shell-commands-write-only-where-the-session-may.md`
- Modify: `docs/adr/0002-guard-threat-model.md`, `docs/adr/0006-the-main-session-writes-its-memory-folder.md` (status
  lines only), `docs/adr/README.md`
- Test: `tests/test_guard_outside_reach.py`

**Interfaces:**
- Consumes: Task 1's tests; Task 2's `in_scope`, `roots_for`, `is_exempt`; Task 3's `is_device`, `strip_heredoc_bodies`;
  Task 4's `command_segments`, `write_targets`, `cd_target`.
- Produces:
  - `Reach` in `apm.guard_outside`, a frozen dataclass: `project: Project`, `temp_roots: tuple[Path, ...]`,
    `config_dir: Path | None`, `home: Path | None`, `worker: bool`, `windows: bool`. Methods:
    - `resolve(word: str, cwd: Path) -> Path`: a leading `~`, `$HOME`, `${HOME}`, `$env:HOME` or `$env:USERPROFILE`
      (the `$env:` names in any case) followed by `/` or the end becomes `home` when `home` is set; then
      `to_native_path(word, cwd, windows)`. Any other variable stays a name.
    - `writable(target: Path) -> bool`: `in_scope(target, project, roots_for(target, project, temp_roots, config_dir,
      worker))`.
  - `OUTSIDE_REASON = "command writes outside the project and the temp folders"`.
  - `outside_write(command: str, cwd: Path, allowed_prefixes: Sequence[str], reach: Reach) -> str | None`: over
    `command_segments(strip_heredoc_bodies(mask_data(command)))`, in order: a `cd_target` moves the tracked directory
    (`reach.resolve`); a segment `is_exempt` under the allowlist prefixes is skipped; each `write_targets` word that is
    not `is_device` is resolved, and the first that is not `reach.writable` returns `f"{OUTSIDE_REASON} ({target})"`.
  - `decide(event, project, profile, allowlist, temp_roots, windows, approvals=(), config_dir=None, home: Path | None
    = None, shell_temp: Sequence[Path] = ()) -> Decision`. Every existing call keeps working.
  - In `guard.py`: `_violation` builds `Reach(project, (*temp_roots, *shell_temp), config_dir, home, worker, windows)`
    for a command event; `_command_violation` runs, in order, the worker check, the state-dir check, `check_command`,
    then `outside_write(command, cwd, prefixes, reach)`, and returns `(f"{reason}: {command.strip()}",
    _REMEDIES["command"])` for it.
  - In the hook: `SHELL_TEMP_ROOTS: tuple[Path, ...] = (Path("/tmp"),)`; `_home() -> Path | None` returns
    `Path.home()`, or `None` when it raises `RuntimeError`; `_guard` passes `home=_home(), shell_temp=SHELL_TEMP_ROOTS`.

- [ ] **Step 1: Write the failing unit tests** in `tests/test_guard_outside_reach.py`, each with `home = Path("/h")`
  (posix) or a `tmp_path` folder, comparing with `to_native_path` of the expected literal:
  `test_home_forms_resolve_to_home` (parametrized): `~/x`, `~`, `$HOME/x`, `${HOME}/x`, `$env:USERPROFILE/x`,
  `$ENV:userprofile/x`, `$env:HOME/x` → `home/x` (or `home`); `test_other_names_stay_relative`: `~user/x`, `$TMPDIR/x`,
  `$Tx/y` → `cwd/<word>`; `test_without_a_home_a_tilde_is_a_name`: `home=None`, `~/x` → `cwd/~/x`.
  And `test_a_hook_without_a_home_still_guards`: patch `Path.home` to raise `RuntimeError`, environ
  `{"CLAUDE_CONFIG_DIR": <abs>}`, a command `echo x > <abs outside>/a.md` through the hook: `deny` (not the
  fail-closed "APM guard error").
- [ ] **Step 2: Run** `python -B -m pytest -q tests/test_guard_outside_reach.py tests/test_guard_outside.py tests/test_guard_outside_powershell.py tests/test_guard_outside_routine.py tests/test_guard_outside_hook.py`.
  Expected: the Reach tests FAIL (no module); Task 1's FAIL-now cases still fail; its pins pass.
- [ ] **Step 3: Implement** `guard_outside.py`, the `guard.py` and hook changes. Module docstring: the rule, that it
  runs after every other command check, and its known limits (Task 4's list, by reference; targets built from other
  variables; a session whose shell already sits outside the project is not guarded at all, because the project comes
  from the event's cwd).
- [ ] **Step 4: Write ADR 0007** from `skills/adr/references/adr-template.md`, titled "ADR-0007: A shell command may
  write only where its session may: the project, its worktree, the temp folders, the profile's write roots, and for
  the main session its memory folder". Status: `Accepted, <date>. Builds on ADR-0002, ADR-0005 and ADR-0006. Amends
  ADR-0002 (what the guard must stop) and ADR-0006 (its consequence on Bash writes).` It must contain:
  - Context: the root cause above, the probe result, and the transcript evidence (the counts in this plan's
    "Evidence" section, the cross-repo incident, the XP12 routines).
  - Decision: the rule; which sessions (the user's answer to this plan's decision, with the date); what counts as a
    write target (Task 4's families) and that writes a program makes itself are out of the model, except that a
    `git` command writes its working directory; how a command is read for this check (segments outside quotes, bodies
    no shell runs set aside, devices and descriptors, `/tmp`, the home forms); `write_roots` (Task 6): shell only,
    never the file tools, folders the user approved, never lifting another denial; the denial for the main session
    offers `approve --command`.
  - ADR 0002 rule 2: this change only adds denials, so it needs no reading of it; `write_roots` only narrows the new
    denial toward today's verdict.
  - Consequences: the main-session routines option B breaks (above), the XP12 profile needs `write_roots` before it
    upgrades, the known limits, and that the destructive and protected checks still read heredoc bodies as ADR 0005
    says.
  - Alternatives considered: workers only (option A); option C; an operating-system sandbox (ADR 0002); absolute
    `--path` approvals (ADR 0006 rejected them); write roots from an environment variable (project settings can set
    env); denying every non-read segment after `cd` outside (denies `pytest` and builds wholesale); reading heredoc
    bodies as the destructive check does (the measured false positives).
  - Change the status lines of ADR 0002 and ADR 0006 to add `Amended by ADR-0007.` and nothing else; update their
    index rows and add the 0007 row in `docs/adr/README.md`.
- [ ] **Step 5: Edit `agents/manager.md`** Safety: one bullet after "Protected paths": shell commands may write only
  inside the project and its worktrees, the temp folders, the profile's `write_roots`, and from the main session this
  project's memory folder; any other shell write is denied like a file-tool write outside the project, and in the main
  session it can be approved as a command. Keep the phrases `Ask the user in chat`, `with the Bash tool` and
  ``every `\` is inside quotes`` that `tests/test_agents.py` and `tests/test_approve_instructions.py` read.
- [ ] **Step 6: Run** the guard set, `tests/test_agents.py` and `tests/test_docs.py`. Expected: PASS, every Task 1
  case included, no existing test changed.
- [ ] **Step 7: Commit** `"Deny a shell command that writes outside the project"`.

### Task 6: Let a project name folders outside it that shell commands may write

**Files:**
- Modify: `scripts/apm/profile.py` (`write_roots` field, loader, writer)
- Modify: `scripts/apm/guard_outside.py` (`Reach.write_roots`)
- Modify: `scripts/apm/guard.py` (pass `profile.write_roots`; the `shell_outside` remedy)
- Modify: `docs/tutorial.md` (section 9: the example and the key's line)
- Modify: `agents/manager.md` (Safety: add a folder to `write_roots` only after the user says yes)
- Test: `tests/test_guard_write_roots.py`, `tests/test_profile_write_roots.py`

**Interfaces:**
- Consumes: Task 5's `Reach`, `outside_write`, `_command_violation`.
- Produces:
  - `Profile.write_roots: tuple[str, ...] = ()`, loaded from the top-level key `write_roots` with `_string_list`
    (error text `write_roots must be a list of strings`), added to `_KNOWN_KEYS`; `write_profile` writes the key only
    when it is non-empty, so every profile written today is written unchanged.
  - `Reach.write_roots: tuple[str, ...] = ()`: each entry resolved with `resolve(entry, project.main_root)` (so `~/vab`,
    an absolute path and a checkout-relative path all work) and added to the roots `writable` passes to `roots_for`.
  - `_REMEDIES["shell_outside"] = _REMEDIES["command"] + " If the project writes there routinely, the user can list
    the folder under write_roots in .apm/profile.json."`; `_command_violation` returns it for an `outside_write`
    denial. Workers still get no remedy.
- [ ] **Step 1: Write the failing tests.**
  - `tests/test_profile_write_roots.py`: `test_write_roots_load_from_the_profile` (`["~/vab", "D:/X-Plane 12/Output"]`
    → the tuple); `test_write_roots_must_be_strings` (`"~/vab"` and `[1]` → `ProfileError` with the text above);
    `test_a_profile_without_write_roots_is_written_unchanged` (`"write_roots" not in` the written JSON);
    `test_write_roots_round_trip`.
  - `tests/test_guard_write_roots.py` (decide-level, `home=tmp_path/"home"`, `V = tmp_path/"vab"`), `@BOTH`:
    `test_a_named_folder_opens_for_shell_writes`: `write_roots=(V.as_posix(),)`: `echo x > V/build.log`,
    `cmake --build V/c2 > V/c2.log 2>&1`, `mkdir -p V`, `cp a V/` → `none`; `test_the_home_form_and_a_relative_form_work`:
    `("~/vab",)` with `V = home/"vab"`, and `("../vab",)` with `V = repo.parent/"vab"` → `none`;
    `test_only_the_named_folder_opens`: `echo x > <V>2/x`, `echo x > O/x` → `deny`;
    `test_write_roots_do_not_open_the_file_tools`: a Write to `V/x.md` → `deny`, its reason holding "is outside the
    project" and, in the main session, ending with the file-tool `_REMEDIES["outside"]` text (as today); `test_write_roots_do_not_lift_another_denial`: `rm -rf V/x` → destructive
    reason; `test_the_main_session_denial_names_write_roots`: main `echo x > O/x` → reason ends with the exact
    `shell_outside` remedy; worker → no `"write_roots"` in reason.
- [ ] **Step 2: Run** `python -B -m pytest -q tests/test_profile_write_roots.py tests/test_guard_write_roots.py`. Expected: FAIL
  (no field; `Profile(write_roots=...)` raises `TypeError`, then the verdicts).
- [ ] **Step 3: Implement** the field, the loader and writer, `Reach.write_roots`, the remedy, and `guard.py` passing
  `profile.write_roots`.
- [ ] **Step 4: Docs.** `docs/tutorial.md` section 9: add `"write_roots": ["~/builds"]` to the example and a line:
  "`write_roots`: folders outside the project that shell commands may write, such as an out-of-tree build folder or a
  deploy target. `~` is your home folder; a relative path is relative to the checkout. File tools still write only
  inside the project. Add one only when you mean it: the guard then lets the manager and every worker write there."
  `agents/manager.md` Safety bullet from Task 5 gains: add a folder to `write_roots` only after the user approves that
  folder in chat.
- [ ] **Step 5: Run** the two new files, the guard set, `tests/test_profile.py`, `tests/test_setup.py`,
  `tests/test_cli_init.py`, `tests/test_init_apply.py`, `tests/test_docs.py`, `tests/test_agents.py`. Expected: PASS.
- [ ] **Step 6: Commit** `"Let a project name folders outside it that shell commands may write"`.

### Task 6b: Refuse a `--path` approval that can never match

*Added at approval (2026-10-22): the user asked to fold this existing bug into #20, not to leave it for later.*

**Files:**
- Modify: `scripts/apm/cli_handlers.py` (`approve` and `allow` check `--path` before recording)
- Test: `tests/test_cli_path_approvals.py` (create)

**Interfaces:**
- Produces: `approve --path P` and `allow N --path P` refuse a `P` that can never match a write, with a `UsageError`
  (the CLI's usage-error exit) whose message is exactly:
  `--path must be relative to the checkout root, as the denial names it (got <P>); a write outside the project cannot be approved`.
  Nothing is written to the ledger when it refuses. A `P` can never match when, with `\` read as `/`, it is absolute
  (`/x`), has a drive (`C:x`, `C:/x`), is a UNC or `//` path, starts with `~`, or has a `..` segment.
  `--command` is unchanged.

- [ ] **Step 1: Write the failing tests** in `tests/test_cli_path_approvals.py`, through `apm_cli.main` in an initialized
  tmp project (copy the fixture pattern of `tests/test_hook_approve.py`; do not import it):
  - `test_a_path_that_can_never_match_is_refused` (parametrized on `approve` and `allow 1`, and on
    `/abs/x.md`, `C:/Users/x/MEMORY.md`, `C:\Users\x\MEMORY.md`, `//server/share/x`, `~/x.md`, `../other/x.md`,
    `docs/../../x.md`): exit is the usage-error code, the message above is printed, and the ledger has no new entry.
  - `test_a_checkout_relative_path_is_recorded` (parametrized on `data/fleet.db`, `docs/**`, `.git/config`): exit 0
    and the approval or allow entry holds the path as given.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_cli_path_approvals.py`. Expected: the refusal cases FAIL (exit 0,
  recorded); the accepted cases pass.
- [ ] **Step 3: Implement** one small pure helper in `cli_handlers.py` (or a sibling module if the file would pass its
  limits) and call it from `approve` and `allow` before the ledger write.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_cli_path_approvals.py tests/test_cli.py tests/test_hook_approve.py
  tests/test_guard_remedies.py tests/test_own_limits.py`. Expected: PASS.
- [ ] **Step 5: Commit** `"Refuse a --path approval that can never match"`.

Task 6b touches no guard file and shares no file with Tasks 2 to 6; it may run in parallel with Tasks 2 and 3.

### Task 7: Run the merge gate

- [ ] **Step 1: Run** `<CLI> gate 20`. Expected: PASS: the full suite once, `<CLI> debt check` passing, and every
  structural criterion below met. On a failure, fix the cause in the task that owns it and run the gate again. Merge
  style: `merge` (profile).

Order: Task 1, then Tasks 2 and 3 (disjoint files: `guard_paths.py`, `guard.py`, `guard_commands.py` against
`guard_words.py`, `guard_redirects.py`, `guard_data.py` and three new test files; they may run in parallel), then 4,
5, 6, 7 in order.

---

## Structural acceptance criteria (checked before the PR)
- Every file this plan creates or changes is at most 200 lines of logic and every function in it at most 15, measured
  by `<CLI> metrics`: `guard.py` (starts at 153), `guard_commands.py` (151), `guard_paths.py` (60), `guard_data.py`
  (38), `guard_words.py` (28), `guard_redirects.py` (14), `hook_pretooluse.py` (58), `profile.py`, the two new modules,
  and the eleven new test files. `tests/test_own_limits.py` passes.
- `guard_targets.py`, `guard_redirects.py`, `guard_words.py` and `guard_data.py` read no environment, clock or file.
  The home folder and `/tmp` are read only in `scripts/hook_pretooluse.py`.
- Imports follow the Global Constraints' direction; only `guard.py` imports `guard_outside`; `guard_commands.py`
  imports neither new module.
- `_command_violation` runs the worker check, the state-dir check and `check_command` before `outside_write`; no reason
  text given today changes.
- `_file_violation`, `write_denial`, `check_write` and `worker_file_violation` are unchanged in behavior; `write_roots`
  and `SHELL_TEMP_ROOTS` reach only the command path.
- Task 2 is a pure-move commit: the guard set passes unchanged before and after it.
- `docs/adr/0007-shell-commands-write-only-where-the-session-may.md` exists, records the main-session decision with its
  date, and has its row in `docs/adr/README.md`; ADR 0002 and ADR 0006 differ from main only in their status lines
  and index cells.
- The docstrings of `guard_targets.py`, `guard_outside.py`, `guard_redirects.py` and `guard_data.py` name the known
  limits of Tasks 3 to 5.
- Unchanged against `main`: `guard_workers.py`, `guard_cli.py`, `guard_github.py`, `tests/test_guard.py`, and every
  existing test file.
- `<CLI> debt check` passes. `<CLI> gate 20` passes. Merge style `merge`.

## Allowlisted actions
None. No task writes a protected path, deletes a file, or runs a destructive command. (The safety-critical paths are
reviewed per task; they are not protected paths. The ADR 0002 and 0006 status-line edits are ordinary tracked edits.)

## Risks
- **New denials on routine work in other projects.** The XP12 project writes `~/vab`, `C:/vaR` and two X-Plane folders
  routinely, from the manager and from workers. After this ships, those are denied until its profile lists them under
  `write_roots` (or, in the main session, each is approved). The release notes and the plan summary must say so. This
  plan does not touch that repository.
- **The reading is new and heuristic.** It differs from `split_segments` (quote-aware) and from ADR 0005's heredoc
  handling (bodies no shell runs are set aside), both on purpose and only for this check. The probe found no existing
  verdict changed and removed the measured false positives, but the transcripts are one user's habits. A false
  positive found later is fixed by a pin and a narrower reading, never by dropping the check.
- **`git` in another checkout is read by subcommand.** A read the list misses (`git -C ../o config --get x`) is denied
  in another checkout only; inside the project every git command is allowed.
- **A write root is a repository file that widens the new check.** It cannot widen beyond today (nothing outside is
  checked today), and workers cannot edit the profile (`WORKER_PROTECTED`). The manager can, so manager.md asks for the
  user's yes first. Folding it into file tools is a separate decision (it would loosen ADR 0006's verdicts).
- **`mkdir -p` of the memory folder itself is denied for the main session,** as the file tools deny the folder path
  (ADR 0006). The folder normally exists, because Claude Code makes it.
- **Interaction with #13.** #13 is unchanged here: a worker's `cat .apm/profile.json 2>/dev/null` is still denied by
  the protected check, and no test here pins it either way. This plan makes #13 small: `_is_read_only` can call
  `split_redirects` and allow a read-prefix segment whose every redirect target `is_device`, instead of denying any
  `>`; the outside check already treats those redirects as no write.

## Overlap with other work
- #14 and #19 are merged on this base (05f044c); this plan reuses `space_redirects`' quoting rules, `memory_folder`,
  `is_unlinked` and #19's roots (moved, not copied, in Task 2).
- #13 (queued) touches `guard_commands._is_read_only`; this plan does not. Build #13 after this.

## Approval (2026-10-22)

*The user approved this in chat: "Fold the approve --path fix into #20, and build #13 immediately after #20. Approve #20 with option B (both sessions)." So both the main session and workers get the outside-write rule, as written, with `write_roots` and ADR 0007 recording the decision. The approve --path fix is added as Task 6b. #13 is built right after this issue, before anything else in the queue, reusing `split_redirects` and `is_device`.*

## Pre-flight scan

| Tasks | Shared file or interface | Producer vs consumer | Found |
|---|---|---|---|
| 1 ↔ 2–6 | the four Task 1 test files | Task 1 creates them; Tasks 4 to 6 turn their FAIL-now cases green, and Task 2 changes no verdict | agrees |
| 2 ↔ 3 | files | Task 2: `guard_paths.py`, `guard.py`, `guard_commands.py`. Task 3: `guard_words.py`, `guard_redirects.py`, `guard_data.py` | disjoint; may run in parallel |
| 3 ↔ 4 | `path_words`, `split_redirects`, `is_device`, `strip_heredoc_bodies` | Task 3 produces them, Task 4's `guard_targets.py` consumes them | in order |
| 2, 4 ↔ 5 | `in_scope`, `allowed_roots`, `roots_for`, `is_exempt`, `join_continuations`, and the target readers | Tasks 2 and 4 produce them, Task 5's `guard_outside.py` consumes them | in order |
| 5 ↔ 6 | `guard_outside.py`, `guard.py`, `agents/manager.md` | Task 5 creates `Reach`; Task 6 adds `write_roots` to it and the remedy | same files, in order |
| 6b | `cli_handlers.py`, a new test file | touches no file of Tasks 2 to 6 | disjoint; may run in parallel with Tasks 2 and 3 |
| 1–6, 6b | self | each task names its files and its targeted tests | consistent |
| 7 | self | the gate | consistent |

Rubric check: Task 1 commits red tests on purpose. Task 2 is a pure move (verified by the unchanged suite). Tasks 1 to 6 are safety-critical, and each gets its own review. Task 6b is covered by the final review.

*Ruling during Task 1 (2026-10-22): the plan marked the routine `gh pr create`, `gh issue create` and `gh issue list > file` pins for both sessions, but a worker is already denied them by `guard_github` ("workers do not write to GitHub"), an existing denial this issue must not change. Those pins run for the main session only (`test_gh_calls_the_main_session_makes_stay_allowed`), and the worker heredoc-in-substitution pin uses `git commit -m "$(cat <<EOF ...)"` instead. Cost if wrong: none; the worker denial is pinned by existing tests.*

## Deferred findings
- Task 1 (found elsewhere): the installed worker rules read text inside a quoted argument or a heredoc as a command: a worker's `sed 's/ - .*//'` filter was denied as an `.apm/` write, and a Python heredoc naming `gh issue create` as a GitHub write. Existing false positives on routine work; candidate issue after #13.
- Task 1 review (S1): `test_guard_outside.py:140` asserts `"notes.md" in reason`, which the echoed command satisfies; assert the resolved target in parentheses.
- Task 1 review (S2): the worktree hook test runs for the main session only; make it both sessions.
- Task 1 review (S3, for Task 5): once Task 5 defines `SHELL_TEMP_ROOTS`, drop `raising=False` from the hook fixture's patch, so a rename cannot silently undo the isolation.
- Task 1 review (S4): the placeholder helper replaces `@M` before `@M2` by order, and a tmp path holding `@` would be corrupted; a single regex pass or `{O}` placeholders would avoid it.
- Task 1 review (S5): optional PowerShell pins: `git rev-parse HEAD 2>$null`, `New-Item -ItemType Directory -Force docs | Out-Null`, `Set-Content -Path docs/a.md -Value x -Encoding utf8`.

*Ruling after the Task 1 review: its three must-fix gaps (MF1 the sed pin's literal `\n`, MF2 heredoc-body pins a skipped `strip_heredoc_bodies` would fail, MF3 quoted absolute paths with spaces) touch only Task 1's files and only add or correct pins. Tasks 2 and 3 share no file with them and change no verdict, and the reviewer cleared them, so they run in parallel with the Task 1 fix round; Task 4 waits for the fixed pins and their re-review. Task 5's brief carries S3. Cost if wrong: Tasks 2 and 3 might need a rebase onto the fixed tests, which they do not read.*

*Ruling on the Task 2 review: its one suggestion (guard_commands.py "over 200") counted physical lines (242); the limit is lines of logic, which `metrics` puts at 153, so the file is within the limit and nothing is deferred. Cost if wrong: none.*

*Ruling on Task 3 deviations: (a) `split_redirects` also reads `>|` as an operator, so its target is checked. The plan listed `>|` as a known limit; reading it only adds denials of real outside writes. (b) The heredoc head reader does not treat `<<` inside a one-line quoted string as a heredoc start, so `echo "a <<EOF"` cannot hide a following real write; pinned. Both tighten; cost if wrong: none.*

*Ruling after the Task 3 review: MF1 (the unterminated-quote fallback in `path_words` keeps quote characters, so a PowerShell `"C:\x\"` destination resolves inside the project), MF2 (the separator class `[A-Za-z0-9_.~-]` misreads a `\` before a non-ASCII letter, as in `C:\Users\Ömer`; amended to `[\w.~-]`, Unicode `\w`) and MF3 (pin `>|`) go to a Task 3 fix round. MF2 amends this plan's stated character class in Task 3 and Platform facts; it changes nothing the user approved. The manager's Task 3 brief said bodies fed to `python` must stay; that was a slip: the plan sets `python - <<PY` bodies aside (Task 3, Task 1 pins), and the plan stands. Carried to later briefs: Task 4 gets a unit case where `Copy-Item a "C:\x\"; Remove-Item b` splits into two segments or knowingly fails closed, and drops `>|` from its known limits; Task 5 gets the decide-level reproduction `Copy-Item README.md "<other>\"` must deny.*
- Task 3 review (S1-S7): `#` comments read as code; an arithmetic shift or a comment can start a false heredoc; unlisted shells (`fish`, `csh`, `tcsh`, `nu`, `wsl`, `source /dev/stdin`) have bodies stripped; `_SHELL_NAMED` matches a shell name anywhere on the head line (fails closed); the `> $(f)` docstring wording; unpinned behavior (second heredoc, tag line inside a quoted string, `<<<`, `<(...)`, `tee >(gzip > out.gz)`); `\` before other characters merges path parts.

*Ruling after the Task 4 review (2026-10-22). All five must-fix items go to a Task 4 fix round.*

- *MF1: shell reserved words hide the program. `_program` skips a leading `if then else elif do while until !` (and `time`), kept out of `_WRAPPERS`.*
- *MF2: a stray quote, such as an apostrophe in a `#` comment, stops all later cutting. The fix fails closed: when the PowerShell reading also leaves a quote open, the stray quote is read as a plain character and cutting continues.*
- *MF3: two PowerShell paths ending in `\"` in one segment. **This amends Task 5's interface.** `guard_targets` gains `command_readings(text) -> list[list[str]]`. It returns the bash reading's segments, and also the PowerShell reading's segments when the text holds `\"`. Task 5 judges each reading separately, from a fresh cwd, and denies when any reading names an outside target, in the manner of `guard_commands.readings`/`first_denial`. `command_segments` stays and is the bash reading.*
- *MF4: a PowerShell assignment hides the cmdlet. `_program` skips a leading `$name =` and `$name=`.*
- *MF5: `git stash` with only options is a write. **This amends the plan's git table:** for `stash`, only `list` and `show` read. Task 4's own pin `("git stash", [])` becomes `["."]`.*

*The docstring must name every known limit the review found, to meet this plan's structural criterion that docstrings name the known limits:*
- *PowerShell script blocks and the cmdlets the module does not read (`ForEach-Object { … }`, `Rename-Item`, `Clear-Content`, `Expand-Archive -DestinationPath`, `Invoke-WebRequest -OutFile`);*
- *`git --git-dir`/`--work-tree` and `git config --global`;*
- *the values of wrapper options (`sudo -u bob`, `env -u VAR`).*

*Cost if wrong: more denials of outside writes, and none of routine work inside the project.*

- Task 4 review (S1, manager leans fix in the final review): the destination family ignores PowerShell value options. `Copy-Item src\* D:\X -Include *.dll` names `*.dll` and misses `D:\X`. Skip the values of `-filter`, `-include`, `-exclude` and `-credential`.
- Task 4 review (S3, for Task 6): `path_words` reads `\` followed by a blank as an escape in PowerShell text. `Copy-Item -Destination C:\vab\ -Path a` gives `C:/vab -Path`, a false deny once `write_roots` opens `C:/vab`. Pin it in Task 6.
- Task 4 review (S4): git reads missing from `_GIT_READS`: `ls-remote`, `remote get-url`, `config --get`, `check-ignore`, `show-branch`, `cherry`, `count-objects`, `var`. Each is a false deny in another checkout only, which Risks accepts.
- Task 4 review (S7, S8): smaller misreads that do no harm (`cp -tdir`, `Tee-Object -Variable`, `mkdir -m`, `touch -d`), and docstring wording about the re-read and about cutting inside `$(...)`.

*Recorded after the Task 4 re-review (2026-10-22). MF1–MF5 are addressed. During the round the worker also found a fail-open, `cp a ../o/ # done` naming `done` as the destination, and the manager added its fix to the same round: comments are stripped before cutting, in both readings. Open must-fix: 0.*
- Task 4 re-review (suggestion): a `#` right after an escaped blank (`echo a\ #b > ../o/f`) is read as a comment. Fix: add `(?<!\\\s)` to the comment alternative.
- Task 4 re-review (suggestion): PowerShell backtick escapes are not read, so a string holding `` `" `` and ` #` can lose a redirect in the bash reading. Name this as a known limit or pin it.
- Task 4 re-review (suggestion): the PowerShell reading can invent a target from a bash string that holds `\"`, an operator and then a write program (`echo "x \"a\" && rm ../o/f"`). This fails closed. Name it in the docstring.
- Task 4 re-review (nits): `guard_targets.py:70` reads `spans =[`, and docstring line 10 is too long.

*Ruling during Task 5 (2026-10-22): the existing #11 test `tests/test_guard_heredoc.py::test_a_heredoc_written_to_a_text_file_is_data[cat > /tmp/body.md ...]` calls `decide` directly without a shell temp root, so `/tmp/body.md` became an outside write. In the real hook `SHELL_TEMP_ROOTS` always includes `/tmp`, so the verdict there is unchanged. This plan forbids editing an existing test, so the interface is amended instead: `decide(..., shell_temp=SHELL_TEMP_ROOTS)` defaults to the hook's shell temp roots, defined in the module the hook imports from (or in `guard.py`, imported by the hook). Only this issue's new test helpers (Task 1's four files and `tests/test_guard_outside_reach.py`) pass `shell_temp=()` explicitly, so their outside cases still hold on Linux, where `tmp_path` lies under `/tmp`. Cost if wrong: one default value.*

*Accepted Task 5 deviations: (1) `$Home`, `$HOME` and `${HOME}` are read without regard to case, which only adds denials. (2) A write word ending in `/` or `\` is judged as a path inside that folder, so `cp notes.md <memory>/` writes a file under the memory folder; the main session's `mkdir -p <memory>/` is then allowed while `mkdir -p <memory>` stays denied, and a recursive delete stays denied as destructive. This is recorded in the docstring and in ADR 0007.*

- Task 5 (concern): `_violation` takes 9 parameters; consider a small context object when Task 6 adds `write_roots`.
- Task 5 (concern): no test pins the fresh cwd per reading; the worker could not build a realistic command where it changes the verdict.

*Ruling after the Task 5 review (2026-10-24).*

*The review replayed 3,029 calls from this repo's transcripts and a capped sample of 2,528 from XP12's, and ran 196 hook events. No verdict loosened and no existing reason changed. All new denials are the expected cross-repo and X-Plane deploy writes, except one.*

*M1, upheld as must-fix: the PowerShell reading (`command_readings` reading 1) was judged for Bash-tool events too. It invented a target in a read-only `cd "/d/X-Plane 12" && python -c "...\"...\"..."`, so a real read was denied. The fix: `Reach` gains a `powershell: bool` set from the event's `tool_name`, and a Bash-tool event is judged on reading 0 only. Bash reads `\"` as an escaped quote, so dropping the PowerShell reading there removes only denials of writes bash never makes.*

*Two more fixes ride along, because the same flag makes them one-liners and each closes a missed write a cooperative worker types:*
- *S2: Git Bash's `$USERPROFILE`/`${USERPROFILE}` and PowerShell's `${env:USERPROFILE}` are home spellings.*
- *S3: `SHELL_TEMP_ROOTS` (`/tmp`) applies to Bash-tool events only. In PowerShell, `/tmp` is a real `C:\tmp` folder, which is outside.*

*S5 and S7 become docstring lines: the trailing-`/` deviation also lets the main session `touch`/`rmdir "<memory>/"`, and a PowerShell drive switch (`D:` then a write) is not tracked.*

*Cost if wrong: Bash commands that hold `\"` lose PowerShell-reading denials that bash never acts on, and some PowerShell `/tmp` writes are newly denied.*

- Task 5 review (S1): when `Path.home()` raises and `CLAUDE_CONFIG_DIR` is set, `~` is read as a name, so `echo x > ~/notes.md` is allowed (fails open in an implausible environment). Fix: treat any home-spelled word as outside when home is unknown, or record it as a known limit.
- Task 5 review (S4): ADR 0007 does not say the home spellings match in any case; `manager.md` says "the project and its worktrees" where the code allows the main checkout and the current worktree.
- Task 5 review (S6): more git reads seen as writes in another checkout: `git branch -a --no-merged origin/main`, `git ls-remote` (extends Task 4 S4).
- Task 5 review (S8): `worker` is computed twice; `_violation` takes 9 parameters (for Task 6).
- Task 5 review (found elsewhere): a worker's PowerShell `Get-Content ~\.claude\settings.json` is denied as a write, while Bash `cat` is allowed (existing, outside this diff).
- Task 5 re-review (nit): on macOS, PowerShell `/tmp` is a real temp folder that `gettempdir()` does not return, so pwsh `/tmp/x` is now denied there; limit the exclusion to Windows if it ever matters.
- Task 5 re-review (nit): the `_HOME` line in `guard_outside.py` is about 120 characters.

*Task 5 re-review: M1, S2 and S3 addressed; replays on base, a51e3fc and de3c7c4 (3,065 calls in this repo, 2,528 from XP12): 0 loosened, 0 reason changes; new denials are only the cross-repo incident and the expected X-Plane deploy and backup writes; open 0.*
