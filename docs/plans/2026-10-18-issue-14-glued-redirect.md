# APM for Claude — Issue 14: The guard misses a redirect written with no space before it — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built test-first by one
> implementer in its own worktree and verified by the manager with the task's targeted tests. The whole
> branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right
> before the PR. **Tasks 1 and 2 are safety-critical and each gets its own review**: Task 2 changes
> `scripts/apm/guard_commands.py` and adds `scripts/apm/guard_redirects.py`, and Task 1 writes the tests that fix
> which verdicts change and which must not. Each review is bounded by ADR 0002
> (`docs/adr/0002-guard-threat-model.md`). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A redirect target is checked against the protected paths and `.apm/` wherever bash reads a redirect:
glued to the word before it (`cat>docs/x.md`), after a heredoc tag (`cat <<'EOF'>docs/x.md`), after a closing
quote (`echo "x">docs/a.md`), and with a file-descriptor prefix (`2>docs/a.md`, `&>docs/a.md`). A `>` or `<`
inside quotes, escaped, or inside a masked message argument is still not read as a redirect.

**Architecture:** One new pure function, `space_redirects`, in a new module `scripts/apm/guard_redirects.py`. It
puts a blank on each side of every run of redirect characters that bash reads outside quotes. `protected_reason` in
`guard_commands.py` reads the tokens of that spaced text as a third reading, after the two it reads today, so the
target becomes a token of its own and the existing token check sees it. The worker check reaches it through
`protected_reason` too. Nothing is removed from the existing readings, so no denial can be lost.

**Tech Stack:** Python 3, standard library only, pytest. Test command: `python -m pytest -q <files>`.

**Spec:** GitHub issue #14 (Rogue-Sentinel/apm-for-claude), and the manager's brief of 2026-10-18.

## Root cause (confirmed by the planner, 2026-10-18, on the branch at 0d49048)

`protected_reason` denies a non-read-only segment when any of its tokens, or a trailing sub-path of one, matches a
protected glob. Its tokens come from `shlex.split` (posix, whitespace-split), which keeps `>` inside a word. So:

- `cat>docs/x.md` is one token. `_candidates` (`guard_commands.py:133`) strips `<>&` only from the **start** of a
  token, and splits on `/`, so it yields `cat>docs/x.md` and `x.md`. Neither matches `docs/**`.
- `cat <<'EOF'>docs/x.md` gives the tokens `cat` and `<<EOF>docs/x.md` (shlex drops the quotes). After the leading
  strip the pieces are `EOF>docs/x.md` and `x.md`.
- `echo "x">docs/a.md` gives `x>docs/a.md`: missed.
- **The reviewer's reading is confirmed and wider than reported:** `2>docs/a.md` is missed even with a blank before
  it (the leading `2` is not stripped), and so is `cmd&>docs/a.md`. `cmd >|docs/a.md` and `cmd>|docs/a.md` are
  denied today, but only because `_SPLIT` cuts the segment at the `|`.
- The second reading (quotes removed) has the same blind spot, because it uses the same tokens.

Probe output on the branch code (synthetic `decide` events, `docs/**` protected): every glued shape in Task 1 is
`none`; the same commands with blanks (`cat > docs/x.md`, `cat > .apm/notes.md` from a worker) are `deny`.

**The instruction behind it.** None that told anyone to write it: `_candidates` assumes a redirect operator starts a
token, which holds only when a blank comes before it. The existing test `"cat x >data/fleet.db"` pins the glued-after
case and nothing pins glued-before. ADR 0005 says of the `cat` heredoc "The file it writes is still checked", and its
`_CAT_OUT` pattern accepts no blank before `>`, so for `cat <<'EOF'>docs/x.md` that sentence was false. After Task 2
it is true; the ADR needs no edit.

**One correction to the brief.** In the main session `.apm/notes.md` and `.apm/notes.sh` are not protected (the
main session protects `.git/**`, `.apm/state/**` and the profile's paths), so a main-session write there is allowed
with or without blanks, correctly. The main-session reproductions use `docs/**` and `.apm/state/**`; the `.apm/`
reproductions are a worker's.

## Platform facts this plan relies on (2026-10-18)
- Bash reads `<` and `>` as operators wherever they are unquoted and unescaped; no blank is needed on either side.
  A quoted string glued to `>` ends the word. A digit run glued before it is a file-descriptor prefix. Checked by the
  planner in Git Bash on this host: `echo "x">q1` wrote `q1`; `echo a->q2` wrote `q2` holding `a-`; `echo b 2>q3`
  wrote `q3`; `cat <<'EOF'>q6` wrote `q6`; `echo c\>q4` and `echo "d>q5"` printed their text and wrote nothing.
- Python `shlex.split` (posix, the default) splits only on whitespace and quotes, so a glued operator stays in the
  word. Checked: `shlex.split("cat <<'EOF'>docs/x.md") == ['cat', '<<EOF>docs/x.md']`.

## Global Constraints
- Limits (profile defaults): **15** lines of logic per function, **200** per file, for every file this plan creates
  or changes, tests included. `guard_commands.py` starts at 149 lines, largest function 8.
- Standard library only; no new dependency. `guard_redirects.py` imports only `re`. The one new import between
  modules is `guard_commands` importing `space_redirects` from `guard_redirects`.
- Test-first; no skipped or expected-to-fail tests; no test waits on a person; no existing test edited, weakened or
  deleted. `tests/test_guard.py` is in the debt baseline: nothing is added to it. New tests go in new files.
- **ADR 0002 binds every task.** This plan only tightens. No verdict that is a denial today may become an allow.
  The new reading is added after the two existing readings, never in place of one.
- **The parsing stays on the masked text**, as today: `check_command` and `worker_command_violation` mask first, so
  a message argument (`-m`, `--body`, ...) and a masked heredoc body are emptied before any redirect is read.
- `_is_read_only`, `all_read_only`, `guard_data.py`, `guard_workers.py`, `guard.py`, `guard_cli.py` and
  `scripts/hook_pretooluse.py` are not changed. Issue #13 is not in this plan.
- American spelling, plain voice.

## Review Focus
Threat model (ADR 0002): the manager or a cooperative worker typing a redirect with no blank, by habit or by copying
a shell idiom. Inputs built to evade the check are known limits, not review targets.
1. **A glued write to a protected path is denied, for the main session and a worker:** `cat>docs/x.md`,
   `cat>>docs/x.md`, `cat <<'EOF'>docs/x.md`, `cat<<'EOF'>>docs/x.md`, `python x.py 2>docs/err.md`,
   `python x.py&>docs/x.md`, `echo "x">docs/a.md`, `echo x>.apm/state/s.json`, and the same inside a chain
   (`git add a && cat>docs/a.md`, `cat>docs/a.md; git add .`). Tests in Task 1
   (`test_a_glued_redirect_to_a_protected_path_is_denied`); code in Task 2.
2. **A worker's glued write into `.apm/` or the Claude settings is denied** with the worker reason:
   `cat>.apm/notes.md`, `cat <<'EOF'>>.apm/notes.md`, `cat>.apm/notes.sh`, `echo x 2>.apm/n.md`,
   `echo "x">.apm/n.md`, `git status && echo x>>.apm/n.md`, `echo {}>.claude/settings.json`. Tests in Task 1
   (`test_a_worker_glued_redirect_into_apm_is_denied`); code in Task 2.
3. **A redirect that writes no file stays allowed:** `2>&1`, `>/dev/null`, `2>/dev/null`, `>/dev/null 2>&1`,
   `> out.txt 2>&1`, `pytest -q 2>&1 | tail -5`, for both. Tests in Task 1
   (`test_a_redirect_that_writes_no_file_stays_allowed`); code in Task 2.
4. **A `>` that bash does not read as a redirect stays allowed:** `echo "a -> b"`, `echo 'x => y'`,
   `echo "a>docs/x.md"`, `echo 'a>docs/x.md'`, `git commit -m "a->docs/x.md"`, `git commit -m 'map x=>docs/y.md'`,
   `git log --format='%h>%s'`, and an escaped `\>`; and a markdown heredoc body with arrows, also when its own head is
   glued (`cat <<'EOF'>body.md`). Tests in Task 1 (`test_a_redirect_sign_inside_quotes_or_a_message_stays_allowed`,
   `test_an_arrow_in_a_markdown_heredoc_body_stays_allowed`) and Task 2 (`tests/test_guard_redirects.py`); code in
   Task 2.
5. **No existing verdict loosens:** the spaced reading only adds tokens, and every existing guard test file passes
   unchanged. A glued redirect gets the verdict of its spaced form. Tests in Task 1
   (`test_a_glued_redirect_gets_the_verdict_of_its_spaced_form`) and Task 2's verification run; code in Task 2.

---

## File Structure

```
scripts/apm/guard_redirects.py       (create) set apart the redirect operators bash reads outside quotes: pure, `re` only
scripts/apm/guard_commands.py        (modify) protected_reason also reads the tokens of the spaced segment
tests/test_guard_glued_redirects.py  (create) decide-level reproductions and their neighbors, main session and worker
tests/test_guard_redirects.py        (create) unit tests for space_redirects
```

Test helper in `tests/test_guard_glued_redirects.py`, as `tests/test_guard_heredoc.py` does (copy the pattern; do not
import from it): `WINDOWS = sys.platform == "win32"`, `WORKER = {"agent_id": "w1"}`, and
`_decide(repo, command, **extra) -> Decision` building `{"tool_name": "Bash", "cwd": str(repo), "tool_input":
{"command": command}, **extra}` and calling `decide(event, Project(main_root=repo, worktree_root=repo),
Profile(framework_version="0.3.0", protected_paths=("docs/**",)), [], [], WINDOWS, [])`. Tests that run for both
sessions are parametrized with `@pytest.mark.parametrize("extra", [{}, WORKER], ids=["main", "worker"])`.

**Why a new module.** The helper is the guard's one reader of shell redirects, and issue #13 needs the same reading
(see Risks). `guard_commands.py` stays near 150 lines and gains one import; #13's plan adds to `guard_redirects.py`
instead of pushing `guard_commands.py` toward 200. No existing code moves, so there is no extraction task.

---

### Task 1: Reproduce the bug as failing tests and pin the neighbors

**Files:**
- Create: `tests/test_guard_glued_redirects.py`

**Interfaces:**
- Consumes: `apm.guard.decide`, `apm.guard.Decision`, `apm.paths.Project`, `apm.profile.Profile`, the `git_repo`
  fixture.
- Produces: nothing a later task imports. Task 2 turns the **FAIL now** tests green.

Each case below is **FAIL now** (a reproduction, turned green by Task 2) or **pin** (passes now and must keep
passing). Commands are shell text; write heredocs with `\n` line breaks, as `tests/test_guard_heredoc.py` does.

- [ ] **Step 1: Write the tests.**
  - `test_a_glued_redirect_to_a_protected_path_is_denied`, parametrized on `extra` (main, worker) and on the command;
    asserts `kind == "deny"`. **FAIL now:** `cat>docs/x.md`, `cat>>docs/x.md`, `"cat <<'EOF'>docs/x.md\nx\nEOF"`,
    `"cat<<'EOF'>>docs/x.md\nx\nEOF"`, `'cat <<"EOF">docs/x.md\nx\nEOF'`, `"cat <<EOF>docs/x.md\nx\nEOF"`,
    `python x.py 2>docs/err.md`, `python x.py 2>>docs/err.md`, `python x.py&>docs/x.md`, `echo "x">docs/a.md`,
    `echo 'x'>>docs/a.md`, `git add a && cat>docs/a.md`, `cat>docs/a.md; git add .`, `python x.py | sort>docs/a.md`,
    `echo x>.apm/state/s.json`. **Pin** (denied today only because `_SPLIT` cuts at `|`, or because the blank is
    there): `python x.py>|docs/x.md`, `python x.py >|docs/x.md`, `python x.py &>docs/x.md`.
  - `test_a_worker_glued_redirect_into_apm_is_denied`, worker only, parametrized; asserts `kind == "deny"` and
    `"workers do not write .apm/" in reason`. **FAIL now:** `cat>.apm/notes.md`,
    `"cat <<'EOF'>>.apm/notes.md\nx\nEOF"`, `cat>.apm/notes.sh`, `echo x 2>.apm/n.md`, `echo x&>.apm/n.md`,
    `echo "x">.apm/n.md`, `git status && echo x>>.apm/n.md`, `echo {}>.claude/settings.json`.
  - `test_a_glued_redirect_gets_the_verdict_of_its_spaced_form`, parametrized on `extra` and on (glued, spaced)
    pairs; asserts the two `kind`s are equal. **FAIL now:** (`cat>docs/x.md`, `cat > docs/x.md`),
    (`python x.py 2>docs/e.md`, `python x.py 2> docs/e.md`), (`echo "x">docs/a.md`, `echo "x" > docs/a.md`),
    (`python x.py<docs/in.md`, `python x.py < docs/in.md`). *(The spaced `2> docs/e.md` is denied today because
    `docs/e.md` is then its own token.)*
  - `test_a_redirect_that_writes_no_file_stays_allowed`, parametrized on `extra` and the command; asserts
    `kind == "none"`. **Pin:** `python x.py 2>&1`, `python x.py >/dev/null`, `python x.py 2>/dev/null`,
    `python x.py>/dev/null 2>&1`, `python x.py > out.txt 2>&1`, `pytest -q 2>&1 | tail -5`.
  - `test_a_redirect_sign_inside_quotes_or_a_message_stays_allowed`, parametrized on `extra` and the command; asserts
    `kind == "none"`. **Pin:** `echo "a -> b"`, `echo 'x => y'`, `echo "a>docs/x.md"`, `echo 'a>docs/x.md'`,
    `git commit -m "a->docs/x.md"`, `git commit -m 'map x=>docs/y.md'`, `git log --format='%h>%s'`,
    `echo a\>docs/x.md` (an escaped `>`; write it as a raw string).
  - `test_an_arrow_in_a_markdown_heredoc_body_stays_allowed`, parametrized on `extra` and the command; asserts
    `kind == "none"`. **Pin:** `"cat > body.md <<'EOF'\na -> b\nsee docs/x.md -> docs/y.md\nx=>y\nEOF"`,
    `"cat <<'EOF'>body.md\na -> b\nEOF"`, `"cat >body.md <<'EOF'\na->b\nEOF"`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_guard_glued_redirects.py`. Expected: every **FAIL now** case
  fails for the defect (`'none' == 'deny'`, or unequal kinds in the parity test; in the worker `.apm/` test, the
  `kind` assertion), never for an import, fixture or syntax error; every **pin** passes.
- [ ] **Step 3: Commit** `"Reproduce issue 14: the guard misses a redirect written with no blank before it"`. This
  commit is red on purpose; the manager verifies the failure reasons, not a pass.

### Task 2: Read a redirect target wherever bash reads a redirect

**Files:**
- Create: `scripts/apm/guard_redirects.py`
- Modify: `scripts/apm/guard_commands.py` (`protected_reason` and its docstring; one import)
- Test: `tests/test_guard_redirects.py`

**Interfaces:**
- Consumes: Task 1's tests.
- Produces: `space_redirects(segment: str) -> str` in `apm.guard_redirects`: the segment with one blank put before
  and one after every redirect run that is outside quotes and not escaped; every other character unchanged.
  `protected_reason(segment, globs, cwd=None, root=None) -> str | None`, signature and reason text unchanged.

- [ ] **Step 1: Write the failing unit tests** in `tests/test_guard_redirects.py`:
  - `test_an_unquoted_redirect_is_set_apart` (parametrized, exact output): `cat>docs/x.md` → `cat > docs/x.md`;
    `x 2>>log` → `x 2 >> log`; `x&>log` → `x &> log`; `x 2>&1` → `x 2 >& 1`; `echo "x">log` → `echo "x" > log`;
    `cat <<'EOF'>log` → `cat  << 'EOF' > log`; `x<in` → `x < in`.
  - `test_a_redirect_sign_inside_quotes_or_escaped_is_left_alone` (parametrized; output equals input):
    `echo "a>b"`, `echo 'a>b'`, `git log --format='%h>%s'`, `echo a\>b`, `echo "say \"x>y\""`.
  - `test_an_unterminated_quote_does_not_hide_a_redirect`: `space_redirects('echo "x>y') == 'echo "x > y'`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_guard_redirects.py tests/test_guard_glued_redirects.py`.
  Expected: the unit tests FAIL (no module `apm.guard_redirects`); Task 1's FAIL-now cases still fail.
- [ ] **Step 3: Implement.**
  - `scripts/apm/guard_redirects.py`: one compiled pattern, `re.DOTALL`, whose alternatives are, in order, a
    double-quoted string `"(?:\\.|[^"\\])*"`, a single-quoted string `'[^']*'`, an escaped character `\\.`, and the
    named group `op` `&?[<>][<>&]*`; `space_redirects` substitutes `f" {op} "` for an `op` match and the match itself
    for the others. These are the same quoted-string and escape alternatives as `guard_data._ARGUMENT`, written
    out here so the two modules stay independent. The leading `&` alone is enough: `_SPLIT` has already cut at `&&`,
    `;` and `|`. Module docstring: what it does and why (shlex keeps a glued operator inside the word, so the target
    was never its own token), and the known limits: a glued redirect inside a quoted string that another shell runs
    (`sh -c 'cat>docs/x.md'`, `"$(cat>docs/x.md)"`) is not set apart (the same with blanks is seen through the
    unquoted reading); PowerShell's quoting and escapes are not read (ADR 0005), so a PowerShell `\>` is read as
    bash's escaped `>`.
  - `scripts/apm/guard_commands.py`: `protected_reason` iterates
    `(*_tokens(segment), *_tokens(_unquoted(segment)), *_tokens(space_redirects(segment)))`, in that order, so every
    reason given today is given unchanged. Its docstring gains one sentence: the segment is also read with each
    unquoted redirect set apart, so the target of `cat>docs/x.md` is a token of its own.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_guard_redirects.py tests/test_guard_glued_redirects.py tests/test_guard_commands.py tests/test_guard_heredoc.py tests/test_guard_echo.py tests/test_guard_bypasses.py tests/test_guard_continuations.py tests/test_guard_workers_wrappers.py tests/test_guard_workflow.py tests/test_guard_debt.py tests/test_guard_data.py tests/test_guard_approve.py tests/test_guard.py tests/test_hook_approve.py tests/test_own_limits.py`.
  Expected: PASS, with no existing test changed. (The planner ran this rule, patched in memory, against the existing
  guard and hook test files: 1129 passed.)
- [ ] **Step 5: Commit** `"Read a redirect target however the redirect is spaced"`.

### Task 3: Run the merge gate

- [ ] **Step 1: Run** `<CLI> gate 14`. Expected: PASS: the full suite once, `<CLI> debt check` passing, and every
  structural criterion below met. On a failure, fix the cause in the task that owns it and run the gate again.

Tasks run in order: 1, 2, 3. None may run in parallel.

---

## Structural acceptance criteria (checked before the PR)
- Every file this plan creates or changes is at most 200 lines of logic and every function in it at most 15,
  measured by `<CLI> metrics`: `scripts/apm/guard_commands.py` (starts at 149), `scripts/apm/guard_redirects.py`,
  `tests/test_guard_glued_redirects.py`, `tests/test_guard_redirects.py`. `tests/test_own_limits.py` passes.
- `scripts/apm/guard_redirects.py` imports only `re` and nothing from `apm`; `guard_commands.py` is the only module
  that imports it.
- `protected_reason` still reads the tokens of the segment and of the unquoted segment, before the spaced segment;
  `_candidates`, `_tokens`, `_SPLIT`, `_is_read_only` and `all_read_only` are unchanged.
- Unchanged against `main`: `scripts/apm/guard.py`, `guard_cli.py`, `guard_data.py`, `guard_workers.py`,
  `guard_paths.py`, `guard_github.py`, `guard_words.py`, `scripts/hook_pretooluse.py`, `tests/test_guard.py`, and every
  existing test file.
- `guard_redirects.py`'s docstring names the two known limits of Task 2.
- No ADR is added, and ADR 0002 and ADR 0005 are unchanged (see Risks for why none is needed).
- `<CLI> debt check` passes. `<CLI> gate 14` passes. Merge style: `merge` (profile).

## Allowlisted actions
None. No task writes a protected path, deletes a file, or runs a destructive command. (The safety-critical paths are
reviewed per task; they are not protected paths.)

## Risks
- **New denials are the spaced form's denials.** A non-read-only segment with an unquoted `>` or `<` glued to a
  protected path's name is now denied, as it is today with blanks. That includes an unquoted `->` before such a name
  (`echo a->docs/x.md`), which bash really does read as a redirect, and a line of a heredoc body that is not masked
  (`cat > run.sh <<'EOF'` with `x>docs/a.md` in it), which ADR 0005 already scans. A quoted, escaped or masked `>`
  changes no verdict.
- **Known limits, not loosenings.** A glued redirect inside a quoted string another shell runs, and a PowerShell
  `\>`, are missed today and stay missed. Both go in the new module's docstring.
- **`>|` holds by accident.** It is denied because `_SPLIT` cuts at `|`, not because a redirect is read. Task 1 pins
  it, so a later change to `_SPLIT` cannot drop it unnoticed.
- **Why no ADR.** The change only tightens, so it needs no reading of ADR 0002 rule 2 (ADR 0005 needed one because it
  turned denials into allows). It follows ADR 0005's principle of reading shell text as bash reads it, and the one cost
  it accepts, the quoted-shell-string limit, is the kind ADR 0002 says to record in the module's docstring. A later
  reader asking "why not inside quotes?" finds the answer there. If the manager or the user wants the choice recorded,
  it would be ADR 0006, "The guard reads a redirect only outside quotes", written in Task 2.
- **Issue #13 touches the same reasoning and stays out.** A worker's `cat .apm/profile.json 2>/dev/null` is denied
  before and after this plan; no test here pins it either way, so #13's plan can turn it into an allow without editing
  a test of this one. Build #14 first: both change the same lines of `guard_commands.py`.
