# APM for Claude — Plan 3: Workflows — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built test-first by one
> implementer in its own worktree and verified by the manager with the task's targeted tests. The whole
> branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right
> before the PR. Task 2 (the guard) is safety-critical and also gets its own review. Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** The manager runs the spec's workflows end to end. It initializes a project from an audit that the
user approves, takes a feature or a reported bug from a filed GitHub issue to a merged PR with plan approval
as the only touchpoint, routes bugs that workers find to a debugger, and merges only through a merge gate
that checks all four §8.4 criteria. Lean pacing becomes the framework default.

**Architecture:** The workflows are manager orchestration, carried as three new skills (`apm:initializing`,
`apm:running-an-issue`, `apm:merge-gate`), backed by new CLI subcommands with tested logic: `audit` (read-only
scan), `init` (apply an approved audit), `github file|close` (a thin `gh` wrapper that mirrors issues into
the ledger), `gate` (the merge gate), `review` and `note` (new ledger records). New profile settings live
under one key, `workflow`. Pure decisions (settings, ledger records, gate checks, plan parsing, audit
classification) are unit-tested. `git` and `gh` are called through an injected `run`, so tests need neither a
network nor a GitHub account.

**Tech Stack:** Python 3.12+ (stdlib only at runtime), pytest, git ≥ 2.42, GitHub CLI `gh` (optional at
runtime: every `gh` failure is reported with a by-hand fallback, never a crash).

**Spec:** `docs/specs/2026-10-17-apm-for-claude-design.md` §6 (workflows), §7 (state), §8.3–8.4 (ratchet and
merge gate).

## Roadmap (this plan is 3 of 4)
1. **Foundation** (merged): plugin, agents, safety hooks, state and briefing, `apm setup`.
2. **The standard** (merged): skills, coverage inventory, metrics, debt ratchet.
3. **Workflows** (this plan): init and audit, the feature and bug paths, the merge gate, GitHub issues, lean
   pacing, and the Plan 2 follow-ups.
4. **Adoption:** install into VirtualAirline through the framework's own init.

**Boundary with Plan 4.** This plan builds and unit-tests `audit` and `init`, and live-checks `audit`
read-only against VirtualAirline. Running `init` for real on VirtualAirline, including the methodology
overwrite, is Plan 4.

## Global Constraints
- Everything from Plans 1 and 2 still holds: stdlib-only runtime, **≤ 15 lines of logic per function and ≤ 200
  per file** (measured by `apm metrics`), a stated reason for 7+ public methods, test-first, no skipped tests,
  refactor and behavior in separate commits, American spelling, skills language-agnostic, with no banned terms.
- New profile keys live under **one key, `workflow`**, so `profile.py`'s loader keeps them in `extra` without
  changing. Plan 2's `standard` key is unchanged except for `debt_sources[].timeout` (Task 4).
- **Every CLI subcommand is classified for workers**: either read-only (`brief`, `metrics`, `coverage`,
  `audit`, `debt check`) or denied to workers. A test fails when a subcommand is neither (Task 2).
- **Workers never speak outward.** The guard denies workers every `gh` call that writes to GitHub.
- `gh` is optional. Without it, `github` and `audit` report what they could not do and how to do it by hand.
- **Lean pacing is the default** (Task 11, recorded in `docs/adr/0001-lean-pacing-by-default.md`): targeted
  tests while working; the full suite exactly once, through `apm gate`, right before the PR (and again only if
  the gate failed and something changed); one whole-branch review at the end; a one-line plain progress
  update after each task. Per-task review only when the user asks, when the profile says
  `"review": "per-task"`, or when a task touches a `workflow.safety_critical` path.
- `build_parser` is at 13 of 15 lines: new subcommands register through `cli_parser_workflow.py` (Task 5), and
  `build_parser` gains exactly one line.
- Plugin version becomes `0.3.0` in the last task.

## Review Focus
1. **A state-changing subcommand that slips past the worker denylist.** The guard is a denylist (`_MUTATIONS`),
   so a forgotten name is a hole. Tests are in Task 2 (`test_every_subcommand_is_classified`).
2. **`gh` writes disguised from the guard:** extra spaces, `GH.EXE`, a path prefix, after `&&`, `;` or `|`,
   `gh api -X POST`, `--method=PATCH`, or `gh api` with `-f`/`-F`/`--input`, which imply a POST. Reads
   (`gh issue list`, `gh pr view`, `gh api -X GET`) stay allowed. Tests are in Task 2.
3. **The gate passing on stale or partial evidence:** a review recorded before the latest commit, a dirty
   tree, `main` not merged in, a promised document missing, or no test command declared. Tests are in Task 9.
4. **The audit in an unusual repo:** no `origin`, no `gh` or not signed in, no `main` (only `master`), no
   commits yet, a worktree whose folder is gone. The report says what it couldn't read, and doesn't crash.
   Tests are in Task 7.
5. **Init run twice, or run too early:** a coverage gap, a missing decision, or a "finish first" branch not
   merged must refuse, and a second run must not duplicate imported issues, notes or debt issues. Tests are
   in Task 8.

---

## File Structure

```
scripts/apm/workflow_config.py     Workflow, Commands, Checker, Lane from profile["workflow"]; lane_for, needs_task_review
scripts/apm/guard_github.py        which gh calls write to GitHub (denied to workers)
scripts/apm/guard_workers.py       (modify) the denylist gains the new state-changing subcommands; gh writes wired in
scripts/apm/guard_cli.py           (modify) SUBCOMMANDS gains the six new names
scripts/apm/metrics_ref.py         measure the tree at a git ref
scripts/apm/layer_map.py           files matched by two layers' globs
scripts/apm/ledger_workflow.py     notes (decisions, concerns), sub-issues, the final review record
scripts/apm/cli_parser_workflow.py parsers for note, review, github, audit, init, gate
scripts/apm/cli_workflow.py        merges the workflow handlers
scripts/apm/github.py              gh wrapper: create, close, list, issue templates
scripts/apm/cli_github.py          `apm github file|close`
scripts/apm/audit_scan.py          mode, base ref, in-flight work, debt issues
scripts/apm/audit_report.py        audit JSON and the Markdown audit report
scripts/apm/cli_audit.py           `apm audit`
scripts/apm/init_apply.py          refusals and apply for an approved audit
scripts/apm/cli_init.py            `apm init`
scripts/apm/gate_plan.py           a plan's structural criteria and promised documents
scripts/apm/gate.py                the four merge-gate criteria
scripts/apm/cli_gate.py            `apm gate`
skills/initializing/               §6.1 as a skill (+ references)
skills/running-an-issue/           §6.2 and §6.3 as a skill (+ references)
skills/merge-gate/                 §8.4 as a skill
docs/adr/0001-lean-pacing-by-default.md
tests/test_workflow_config.py, test_guard_workflow.py, test_metrics_ref.py, test_layer_map.py,
test_ledger_workflow.py, test_cli_workflow.py, test_github.py, test_cli_github.py, test_audit_*.py,
test_cli_audit.py, test_init_apply.py, test_cli_init.py, test_gate*.py, test_cli_gate.py, test_skills_workflow.py
```

---

### Task 1: Workflow settings in the profile

**Files:**
- Create: `scripts/apm/workflow_config.py`, `tests/test_workflow_config.py`

**Interfaces:**
- Consumes: `Profile`, `ProfileError` (`profile.py`); `matches_any` (`guard_paths.py`).
- Produces:
  - `@dataclass(frozen=True) class Checker: name: str; command: str`
  - `@dataclass(frozen=True) class Commands: build: str | None = None; test: str | None = None; checkers: tuple[Checker, ...] = ()`
  - `@dataclass(frozen=True) class Lane: name: str; paths: tuple[str, ...]`
  - `MERGE_STYLES = ("merge", "squash", "rebase")`, `REVIEW_MODES = ("end", "per-task")`, `DEFAULT_GATE_TIMEOUT = 1800`
  - `@dataclass(frozen=True) class Workflow: commands: Commands = Commands(); merge_style: str | None = None;
    lanes: tuple[Lane, ...] = (Lane("main", ("**",)),); review: str = "end"; safety_critical: tuple[str, ...] = ();
    gate_timeout: int = DEFAULT_GATE_TIMEOUT; base: str = "main"`
  - `load_workflow(profile: Profile | None) -> Workflow`: reads `profile.extra["workflow"]` (keys `commands`
    {`build`, `test`, `checkers`: [{`name`, `command`}]}, `merge_style`, `lanes`: [{`name`, `paths`}], `review`,
    `safety_critical`, `gate_timeout`, `base`). Defaults when absent. Raises `ProfileError` for an unknown
    merge style or review mode, a non-positive or non-integer timeout, a checker without a name or command, a
    duplicate checker or lane name, a lane with no paths, or a non-string glob.
  - `lane_for(workflow: Workflow, paths: Sequence[str]) -> str | None`: the first lane whose globs match
    every path; `None` when the paths span lanes or match none.
  - `needs_task_review(workflow: Workflow, paths: Sequence[str]) -> bool`: `review == "per-task"`, or any
    path matches `safety_critical`.

- [ ] **Step 1: Write the failing tests**
  - `test_defaults_without_profile`: one lane `main`, review `end`, no merge style, timeout 1800, base `main`.
  - `test_reads_every_key`, `test_unknown_merge_style_rejected`, `test_unknown_review_mode_rejected`,
    `test_bad_timeout_rejected` (0, -1, `"60"`, `true`), `test_checker_needs_name_and_command`,
    `test_duplicate_lane_or_checker_rejected`.
  - `test_lane_for_single_and_spanning`: lanes `plugin` (`src/**`) and `companion` (`companion/**`):
    `["src/a.c"]` gives `plugin`, `["src/a.c", "companion/b.ts"]` gives `None`.
  - `test_needs_task_review`: `end` with `safety_critical=("hooks/**",)` is true for `hooks/x.py` and false
    for `src/a.py`; `per-task` is always true.
- [ ] **Step 2: Run** `python -m pytest tests/test_workflow_config.py -q`. Expected: FAIL (ImportError).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the same tests. Expected: PASS.
- [ ] **Step 5: Commit** `"Read the project's workflow settings from the profile"`.

### Task 2: Workers never change state or write to GitHub (safety-critical: reviewed on its own)

**Files:**
- Create: `scripts/apm/guard_github.py`, `tests/test_guard_workflow.py`
- Modify: `scripts/apm/guard_workers.py` (the denylist gains `note|review|github|init|gate`;
  `worker_command_violation` also calls `gh_write_reason`; new constant `WORKER_READ_ONLY`),
  `scripts/apm/guard_cli.py` (`SUBCOMMANDS` gains `audit`, `init`, `github`, `gate`, `review`, `note`)

**Interfaces:**
- Consumes: `split_segments`, `mask_data` (existing guard helpers).
- Produces:
  - `guard_workers.WORKER_READ_ONLY = ("brief", "metrics", "coverage", "audit", "debt check")`
  - `guard_github.gh_write_reason(segment: str) -> str | None`: a reason when the segment runs `gh` (bare,
    `gh.exe`, or with a path prefix, in any case) with a write verb: `issue` {create, close, reopen, edit,
    comment, delete, transfer, lock, unlock, pin, unpin, develop}; `pr` {create, merge, close, reopen, edit,
    comment, review, ready}; `release` {create, delete, edit, upload}; `repo` {create, delete, edit, rename,
    archive, fork}; `label` {create, edit, delete, clone}; or `api` with `-X`/`--method` (space or `=`) other
    than GET, or with any of `-f`, `-F`, `--field`, `--raw-field`, `--input`. Otherwise `None`. The reason says
    "workers do not write to GitHub; report to the manager instead".
  - Workers only; the main session is unaffected (the manager files and closes issues).

- [ ] **Step 1: Write the failing tests**
  - `test_every_subcommand_is_classified`: for every subcommand name in `build_parser()`'s choices, either it's
    in `WORKER_READ_ONLY`, or a worker running `apm <name> 1` and `python ".../scripts/apm_cli.py" <name> 1` is
    denied. For `debt`, `debt baseline` is denied and `debt check` is allowed.
  - `test_worker_denied_new_mutations` (parametrized): `note`, `review`, `github file`, `github close`, `init`, `gate`.
  - `test_worker_may_run_audit`.
  - `test_gh_writes_denied_to_workers` (parametrized): `gh issue create -t x`, `gh  pr   merge 3`,
    `GH.EXE pr merge 3`, `/usr/bin/gh issue close 2`, `ls && gh issue comment 1 -b hi`, `gh release create v1`,
    `gh api repos/o/r/issues -X POST`, `gh api --method=PATCH repos/o/r`, `gh api repos/o/r/issues -f title=x`,
    `gh api graphql --input q.json`.
  - `test_gh_reads_allowed_to_workers` (parametrized): `gh issue list`, `gh pr view 2`, `gh pr diff 2`,
    `gh api repos/o/r/pulls`, `gh api -X GET repos/o/r`, `gh auth status`.
  - `test_main_session_may_file_and_close`: no `agent_id`, so `gh issue create` and `apm github close 3` give no decision.
- [ ] **Step 2: Run** `python -m pytest tests/test_guard_workflow.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** all guard tests: `python -m pytest tests/test_guard*.py tests/test_debt_guards.py -q`. Expected: PASS (Plan 1 and 2 guard tests unchanged).
- [ ] **Step 5: Commit** `"Keep workers from changing state or writing to GitHub"`.

*Rulings after the Task 2 review (three must-fix findings, each reproduced by the manager): (M1) the `gh`
classification becomes an **allowlist of read verbs per group** for workers: any other verb, any unknown group,
and any built-in or user alias is denied; `api` keeps its GET-only rules. This replaces the denylist of write
verbs, whose own comment said "a verb missing here is a hole" (`gh issue new`, `gh pr new`, `gh ext`, `gh cs`
were holes). (M2) tokens split on shell punctuation as well as whitespace (`$(gh issue create)`,
`gh pr ready>/dev/null`). (M3) every `gh` occurrence in a segment is checked (`exec -a gh gh issue create`).
Folded into the same fix round because they are cheap and safety-relevant: `debt` is denied to workers unless
followed by `check`; a worker's text search for `gh ...` strings is denied on purpose, pinned by a test, and the
reason names the Grep tool; `test_the_new_subcommands_are_cli_calls` asserts through `is_cli_call`; the known
limits (`$GH`, `eval`, a PowerShell backtick escape, `curl`, `git push`, a script the worker writes then runs) are
written in `guard_github.py`'s docstring. Cost if wrong: some rare `gh` reads are denied to workers, who report to
the manager instead.*

*Ruling (a bug the worker found, related to this task): the pre-existing `_APM_MUTATION` pattern misses wrapped
calls (`env apm note 1`, `sudo apm ...`, `xargs apm ...`, `$(apm review 1)`, `(apm github close 3)`), so a worker
could change APM state through a wrapper. It is fixed on this branch in the same fix round, as its own commit,
with regression tests seen failing first. Cost if wrong: one more commit in the re-review.*

*Ruling during Task 2 fix round 1: the shared word splitter lives in a new `scripts/apm/guard_words.py` (outside the round's file list), so `guard_github.py` and `guard_workers.py` share it without an import cycle. `grep -r 'gh issue' docs` moved from the allowed reads to the denied text searches, as the S2 ruling requires. Cost if wrong: one small file.*

*Rulings after the Task 2 re-review (M1, M2, M3, S1, S2, S3 and S6 addressed; the wrapper fix fails open):
(a) the `apm` check is applied as first ruled: an `apm`-program word (bare, by path, `apm.exe`, `.cmd`, `.bat`, or
`apm_cli.py`) followed by a state-changing subcommand **anywhere in a segment** is denied to workers. There is no
wrapper list, so `eval`, `iex`, `Invoke-Expression`, `cmd /c call`, `start`, `timeout 30s`, `watch`, `strace`,
`flock`, `uv run`, `busybox` and `parallel` are all caught. `echo apm note` and `grep apm issue docs` are now
denied on purpose, the same trade S2 made for `gh`. To offset it, `_state_change` runs on `mask_data(command)`, as
`_github_write` does, so a literal commit message is not read as a command (an expanding value such as
`-m "$(apm note 1)"` is still seen). Also: `gh auth status` with `--show-token`/`-t` is denied (it prints the
token, like the already-denied `gh auth token`), and `gh pr checkout` leaves the read allowlist (it moves a
worker's worktree off its task branch). Under the retry rule this was the second failure, so fix round 2 goes to a
fresh worker on opus. Cost if wrong: more false positives for workers, who fail closed and use the Grep tool.*

### Task 3: Metrics follow-ups: plain files, a git ref, and files in two layers

**Files:**
- Create: `scripts/apm/metrics_ref.py`, `scripts/apm/layer_map.py`, `tests/test_metrics_ref.py`, `tests/test_layer_map.py`
- Modify: `scripts/apm/metrics.py` (`report_json` gains `plain` per file), `scripts/apm/cli_standard.py`
  (`--ref` and overlaps), `scripts/apm/cli_parser.py` (`_metrics` gains `--ref REF`; `build_parser` untouched),
  `tests/test_cli_metrics.py`, `tests/test_metrics.py`

**Interfaces:**
- Consumes: `measure_text`, `select_files`, `Report`, `MetricsConfig` (Plan 2); `Standard.layers` (Plan 2); `matches_any`.
- Produces:
  - `report_json`: every file entry gains `"plain": bool`, true when `language_for(path).family == "plain"`
    (measured for size only, not unmeasured because of an error).
  - `metrics_ref.RefError(Exception)`; `ref_files(root: Path, ref: str, run=subprocess.run) -> list[str]`
    (`git ls-tree -r --name-only <ref>`); `measure_at_ref(root: Path, ref: str, config: MetricsConfig,
    paths: Sequence[str] | None = None, run=subprocess.run) -> Report` (text through `git show <ref>:<path>`,
    UTF-8 with `errors="replace"`). An unknown ref raises `RefError(f"unknown ref: {ref}")`.
  - `layer_map.layer_overlaps(paths: Sequence[str], layers: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, str]]`:
    `(path, first layer, second layer)` for each path matched by two layers' globs, sorted by path.
  - CLI: `apm metrics [--json] [--ref REF] [PATH ...]`. With a layer map in the profile, the text output gains
    a `files in two layers:` section and the JSON gains `"layer_overlaps": [[path, a, b], ...]`. It still exits 0.
    An unknown ref prints the error and exits 2.

- [ ] **Step 1: Write the failing tests**
  - `test_plain_flag_in_json`: a `.sh` file has `"plain": true`, and a `.py` file has `false`.
  - `test_measure_at_ref_ignores_working_tree` (`git_repo`): commit a 20-line function, then shrink it uncommitted; measuring at `HEAD` still shows 20.
  - `test_unknown_ref_raises`.
  - `test_layer_overlaps`: layers `domain` (`src/core/**`) and `adapters` (`src/**/io/**`) with `src/core/io/x.py` give one overlap; disjoint globs give none.
  - `test_cli_metrics_ref_and_overlaps`.
- [ ] **Step 2: Run** `python -m pytest tests/test_metrics_ref.py tests/test_layer_map.py tests/test_metrics.py tests/test_cli_metrics.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the same tests, plus `tests/test_own_limits.py`. Expected: PASS.
- [ ] **Step 5: Commit** `"Measure a git ref, flag plain files, and find files in two layers"`.

### Task 4: Small follow-ups: a timeout for debt sources, and an ignored scratch folder

**Files:**
- Modify: `scripts/apm/standard_config.py` (`DebtSource.timeout: int = 300`, read from `debt_sources[].timeout`,
  which must be a positive integer), `scripts/apm/debt_sources.py` (passes the timeout), `scripts/apm/setup.py`
  (`.gitignore` gains `.apm/tmp/` beside `.apm/state/`, idempotent), `tests/test_standard_config.py`,
  `tests/test_debt_sources.py`, `tests/test_setup.py`

**Interfaces:**
- Produces: `run_source` passes `timeout=source.timeout`. `subprocess.TimeoutExpired` raises
  `DebtError(f"{source.name}: timed out after {source.timeout}s")`. `setup.TMP_IGNORE = ".apm/tmp/"`: the gate
  writes command logs there (Task 9).

- [ ] **Step 1: Write the failing tests**: `test_source_timeout_default_and_override`,
  `test_bad_source_timeout_rejected`, `test_run_source_timeout_raises` (an injected `run` that raises
  `TimeoutExpired`), and `test_setup_ignores_tmp_once` (setup run twice adds one line).
- [ ] **Step 2: Run** those three test files. Expected: FAIL.
- [ ] **Step 3: Implement.** **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `"Time out a hung debt checker, and ignore APM scratch files"`.

*Tasks 1 to 4 touch disjoint files and may run in parallel (three at a time).*

### Task 5: Decisions, concerns, sub-issues and the final review in the ledger

**Files:**
- Create: `scripts/apm/ledger_workflow.py`, `scripts/apm/cli_parser_workflow.py`, `scripts/apm/cli_workflow.py`,
  `tests/test_ledger_workflow.py`, `tests/test_cli_workflow.py`
- Modify: `scripts/apm/ledger.py` (`ISSUE_STATUSES` gains `"split"`; `_normalize_issue` defaults `decisions`
  and `concerns` to lists), `scripts/apm/cli_parser.py` (`build_parser` calls `add_workflow_parsers(sub)`;
  `_issue` gains `--parent` as an int), `scripts/apm/cli_handlers.py` (merges `WORKFLOW_HANDLERS`; `issue`
  passes `parent`), `scripts/apm_cli.py` (`REQUIREMENTS` gains `audit: repo`, `init: repo`, `github: state`,
  `gate: state`, `review: state`, `note: state`, all at once so later tasks don't touch this file),
  `scripts/apm/briefing.py`, `tests/test_briefing.py`

**Interfaces:**
- Consumes: `upsert_issue`, `LedgerError`, the `_issue` lookup (`ledger.py`).
- Produces (`ledger_workflow.py`):
  - `add_note(ledger: dict, number: int, kind: Literal["decision", "concern"], text: str, now: datetime) -> bool`:
    appends `{"text", "at"}` to `decisions` or `concerns`. It returns `False` and adds nothing when the same
    text is already there, so a re-run doesn't duplicate.
  - `set_parent(ledger: dict, number: int, parent: int) -> None`: `LedgerError` if the parent is unknown or is the issue itself.
  - `children(ledger: dict, number: int) -> list[int]`, sorted. `parent_progress(ledger: dict, number: int) -> tuple[int, int]`: (merged, total).
  - `record_review(ledger: dict, number: int, *, head: str, open_findings: int, criteria_met: bool, evidence: str, now: datetime) -> dict`:
    sets `issue["review"]`. A negative count raises `LedgerError`.
- Produces (`cli_parser_workflow.py`): `add_workflow_parsers(sub) -> None`, which later tasks extend. `cli_workflow.py`: `WORKFLOW_HANDLERS: dict`.
- CLI:
  - `apm note N (--decision TEXT | --concern TEXT)`
  - `apm review N --open COUNT [--criteria-met] --evidence TEXT`. `head` is `git rev-parse HEAD` in the worktree root.
  - `apm issue N --parent P`
- Briefing: a `split` issue shows `split: K of M sub-issues merged`. An issue with a review shows
  `final review: clean at <sha7>` or `final review: N open findings`. Open concerns are counted.

- [ ] **Step 1: Write the failing tests**: `test_add_note_and_no_duplicate`, `test_set_parent_rejects_self_and_unknown`,
  `test_parent_progress`, `test_record_review_rejects_negative`, `test_cli_note_review_parent` (`git_repo` with
  state set up; the review records the real HEAD), `test_briefing_shows_split_progress_and_review`, and
  `test_old_ledger_without_new_fields_loads`.
- [ ] **Step 2: Run** `python -m pytest tests/test_ledger_workflow.py tests/test_cli_workflow.py tests/test_briefing.py tests/test_ledger.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** **Step 4: Run** them, plus `tests/test_cli*.py`. Expected: PASS.
- [ ] **Step 5: Commit** `"Record decisions, concerns, sub-issues and the final review"`.

*Ruling during Task 5: `tests/test_cli_metrics.py::test_the_requirement_table_keeps_plan_one_behavior` asserts the
table equals Plan 1's five rows exactly, which this task's mandated six rows break. The test gains the six rows
in its expected table, so it stays an exact check (not loosened to a subset); listed in the PR as a test changed
on purpose. Also carried into Task 6: `cli_parser` now imports `cli_parser_workflow`, so `KINDS` is imported
lazily or moved, never imported at module top from `cli_parser` into `cli_parser_workflow`. Cost if wrong: one
test edit.*

### Task 6: Filing and closing GitHub issues

**Files:**
- Create: `scripts/apm/github.py`, `scripts/apm/cli_github.py`, `tests/test_github.py`, `tests/test_cli_github.py`
- Modify: `scripts/apm/cli_parser_workflow.py`, `scripts/apm/cli_workflow.py`

**Interfaces:**
- Consumes: `upsert_issue`, `append_log` (`ledger.py`); `set_parent`, `children`, `parent_progress` (Task 5); `KINDS` (`cli_parser.py`).
- Produces (`github.py`):
  - `class GitHubError(Exception)`
  - `run_gh(args: Sequence[str], root: Path, run=subprocess.run, stdin: str | None = None) -> str`:
    `FileNotFoundError` raises `GitHubError("gh is not installed")`. A non-zero exit raises `GitHubError` with
    the stripped stderr.
  - `@dataclass(frozen=True) class IssueTemplate: name: str; path: str; labels: tuple[str, ...]`, and
    `issue_templates(root: Path) -> list[IssueTemplate]`. These come from `.github/ISSUE_TEMPLATE/*.yml|*.yaml`
    (top-level `name:` and `labels:`, as an inline `[a, b]` or a block list, through a small line reader with
    no YAML library) and `*.md` front matter. `config.yml` is skipped.
  - `create_issue(root, title: str, body: str, labels: Sequence[str], run=...) -> tuple[int, str]`: `gh issue create --title T --body-file - --label L ...`,
    with the body on stdin. The number is parsed from the printed URL (`/issues/(\d+)`). No URL raises `GitHubError`.
  - `close_issue(root, number: int, comment: str, run=...) -> None`
  - `list_open_issues(root, run=...) -> list[dict]`: `gh issue list --state open --limit 500 --json number,title,labels`,
    returned as `[{"number": int, "title": str, "labels": [str]}]`.
- CLI:
  - `apm github file --title T --body-file PATH [--label L]... [--kind feature|bug|debt] [--lane NAME] [--parent P]`.
    It files the issue (with `--parent`, the body ends with `Part of #P`), records the ledger issue (status
    `queued`, with title, kind, lane, `url`, parent), and prints `filed #N: URL`. A `GitHubError` exits 2 with
    `file it by hand, then record it with apm issue N`.
  - `apm github close N --pr URL`: comments `Shipped in URL.`, closes the issue, sets status `merged` and `pr`,
    and logs `shipped in URL`. It refuses (exit 1) unless the issue's status is `integrating` or `merged`. When
    this was a parent's last open child, it prints `all sub-issues of #P are merged; close #P too`.

- [ ] **Step 1: Write the failing tests** (injected `run`, no network): `test_create_parses_number`,
  `test_create_without_url_raises`, `test_gh_missing_is_github_error`, `test_templates_inline_and_block_labels`,
  `test_templates_skip_config`, `test_list_open_issues_shapes_labels`, `test_cli_file_records_ledger_and_parent_line`,
  `test_cli_close_refuses_before_integrating`, `test_cli_close_logs_and_prompts_parent`, and
  `test_cli_file_gh_failure_exits_2_with_hint`.
- [ ] **Step 2: Run** `python -m pytest tests/test_github.py tests/test_cli_github.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `"File and close GitHub issues and mirror them into the ledger"`.

### Task 7: The audit

**Files:**
- Create: `scripts/apm/audit_scan.py`, `scripts/apm/audit_report.py`, `scripts/apm/cli_audit.py`,
  `tests/test_audit_scan.py`, `tests/test_audit_report.py`, `tests/test_cli_audit.py`
- Modify: `scripts/apm/cli_parser_workflow.py`, `scripts/apm/cli_workflow.py`

**Interfaces:**
- Consumes: `measure_at_ref`, `ref_files` (Task 3); `list_open_issues`, `GitHubError` (Task 6); `language_for`;
  `report_json`, `Limits`, `load_standard`; `coverage.render_table`.
- Produces (`audit_scan.py`):
  - `@dataclass(frozen=True) class InFlight: id: str; kind: Literal["branch", "worktree", "plan", "spec", "issue"]; title: str; detail: str`.
    The ids are `branch:<name>`, `worktree:<path>`, `plan:<path>`, `spec:<path>` and `issue:<n>`.
  - `@dataclass(frozen=True) class Audit: mode: Literal["existing", "fresh"]; base: str; notes: tuple[str, ...]; in_flight: tuple[InFlight, ...]; debt_issues: tuple[int, ...]`
  - `resolve_base(root, base: str | None, run) -> tuple[str, list[str]]`: runs `git fetch origin` (a failure
    becomes a note, not an error), then takes the given base, else the first that exists of `origin/main`,
    `main`, `origin/master`, `master`. With no commits it returns `("", ["no commits yet"])`.
  - `detect_mode(files: Sequence[str]) -> Literal["existing", "fresh"]`: existing when any file has a known language.
  - `scan_branches(root, base, run) -> list[InFlight]`: local and `origin/` branches with commits not in `base`
    (`git rev-list --count base..b`). A local and a remote branch of the same name are one item, with detail
    `"N ahead, also on origin"`.
  - `scan_worktrees(root, run) -> list[InFlight]`: from `git worktree list --porcelain`, without the current
    one. The detail is `uncommitted changes`, `clean`, or `folder missing`. Worktrees are reported, never removed.
  - `scan_docs(files) -> list[InFlight]`: tracked `**/plans/*.md` and `**/specs/*.md`.
  - `scan_issues(root, run) -> tuple[list[InFlight], list[int], list[str]]`: open issues, debt issues (title
    starts with `[Debt]` in any case, or a label `debt` or `tech-debt`), and notes (`open issues not read: <reason>`).
  - `audit(root, base: str | None = None, run=subprocess.run) -> tuple[Audit, Report]`: the report is measured at the base.
- Produces (`audit_report.py`):
  - `audit_json(audit: Audit, report: Report, limits: Limits) -> dict`: `{"mode", "base", "notes", "in_flight": [{id, kind, title, detail}], "debt_issues", "totals"}`,
    where `totals` is the debt totals from `debt.snapshot`.
  - `render_audit(audit, report, limits, coverage: dict | None) -> str`: sections `# Audit`, `## Mode`,
    `## Measured at <base>`, `## In-flight work` (a table: Item | Kind | Detail | Decision, with each decision
    cell `finish first / adopt / leave`), `## Debt issues`, `## Capability coverage` (`render_table(coverage)`,
    or `Not inventoried yet.`), and `## Notes`.
- CLI: `apm audit [--base REF] [--json] [--coverage PATH]`. It works in any git repository and is read-only.
  It exits 0, or 2 when not in a git repository.

- [ ] **Step 1: Write the failing tests**: `test_mode_fresh_and_existing`, `test_base_falls_back_to_master`,
  `test_no_origin_is_a_note`, `test_no_commits_is_fresh`, `test_branch_ahead_and_dedup_with_origin`
  (`git_repo` with a fake bare `origin`), `test_worktree_dirty_and_missing`, `test_docs_found`,
  `test_issues_and_debt_issues` (injected `run`), `test_gh_unavailable_is_a_note`,
  `test_report_has_decision_column_and_coverage`, and `test_cli_audit_json_and_not_a_repo`.
- [ ] **Step 2: Run** `python -m pytest tests/test_audit_scan.py tests/test_audit_report.py tests/test_cli_audit.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `"Audit a project: mode, in-flight work, debt issues and coverage"`.

*Ruling during Task 7: debt issues appear only in `debt_issues`, not in `in_flight`, so they need no decision:
spec §6.1 adopts existing debt issues into the ratchet's list automatically. Task 8 adopts every `debt_issues`
entry without a decision. A remote-only branch's detail reads `N ahead, only on origin`; `audit()` also takes
`config: MetricsConfig`; with no main or master, the base falls back to `HEAD` with a note. Cost if wrong: one
line in `scan_issues`.*

### Task 8: Init applies the approved audit

**Files:**
- Create: `scripts/apm/init_apply.py`, `scripts/apm/cli_init.py`, `tests/test_init_apply.py`, `tests/test_cli_init.py`
- Modify: `scripts/apm/cli_parser_workflow.py`, `scripts/apm/cli_workflow.py`

**Interfaces:**
- Consumes: `setup_project` (`setup.py`); `load_inventory`, `find_gaps` (`coverage.py`); `load_standard`;
  `load_workflow` (Task 1); `write_profile`, `Profile`; `current_snapshot`, `load_baseline`, `write_baseline`,
  `accept`, `DEBT_FILE`; `upsert_issue`, `append_log`; `add_note` (Task 5); the audit JSON (Task 7).
- Produces:
  - `AUDIT_DIR = ".apm/audit"`, holding `audit.json` (Task 7's `--json` output), `profile.json` (the approved
    draft profile), `coverage.json` (the project's rule-by-rule inventory, in `standard/coverage.json`'s shape)
    and `decisions.json` (`{in_flight_id: "finish" | "adopt" | "leave"}`). The manager writes these after the
    user approves; workers can't (`.apm/**` is worker-protected).
  - `refusals(root: Path, plugin_root: Path, run=subprocess.run) -> list[str]`: each refusal is one line:
    a missing file in `AUDIT_DIR` (`coverage.json` may be absent only when the audit's mode is `fresh`); every
    `find_gaps` result, prefixed `coverage gap:`; `no decision for <id>`; an unknown decision value;
    `finish first: <id> is not merged into <base> yet` (checked with `git merge-base --is-ancestor`); and a
    draft profile that `load_profile`, `load_standard` or `load_workflow` rejects.
  - `apply(root: Path, issue: int, now: datetime, run=subprocess.run) -> list[str]`: the actions taken, in
    this order. It runs `setup_project`, writes `.apm/profile.json` from the draft, and upserts each adopted
    `issue:<n>` as `queued` with `imported: true`. Each adopted plan or spec becomes a decision note on the
    init issue, `imported <path>: not approved; needs the user's approval before building`. Every other
    decision is also a note. The debt issues are merged into the ledger's top-level `debt_issues` (sorted,
    unique). It writes the debt baseline only if none exists, and logs `initialized from audit`.
    **Idempotent:** a second run adds nothing new.
- CLI: `apm init --issue N`. It prints the refusals and exits 1, or prints the actions and exits 0.
  **Init never edits methodology files.** The manager replaces those as tracked edits on the init branch,
  following the approved audit (`apm:initializing`).

- [ ] **Step 1: Write the failing tests**: `test_refuses_on_coverage_gap`, `test_refuses_missing_decision_and_bad_value`,
  `test_refuses_unmerged_finish_first_branch`, `test_fresh_needs_no_coverage`, `test_refuses_invalid_draft_profile`,
  `test_apply_writes_profile_imports_and_baseline`, `test_imported_plans_are_not_approved` (a note, and no issue
  status `building`), `test_apply_twice_adds_nothing`, and `test_existing_baseline_kept`.
- [ ] **Step 2: Run** `python -m pytest tests/test_init_apply.py tests/test_cli_init.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `"Initialize a project from its approved audit"`.

### Task 9: The merge gate

**Files:**
- Modify: `scripts/apm/cli_debt.py`. **Refactor first, as its own commit:** extract
  `check_result(root: Path, standard: Standard, base: str) -> tuple[bool, str]` from `check`, which now prints
  it. The same `tests/test_cli_debt.py` passes on both sides.
- Create: `scripts/apm/gate_plan.py`, `scripts/apm/gate.py`, `scripts/apm/cli_gate.py`, `tests/test_gate_plan.py`,
  `tests/test_gate.py`, `tests/test_cli_gate.py`
- Modify: `scripts/apm/cli_parser_workflow.py`, `scripts/apm/cli_workflow.py`

**Interfaces:**
- Consumes: `Workflow` (Task 1); `layer_overlaps` (Task 3); `TMP_IGNORE` (Task 4); `issue["review"]` and
  `issue["plan"]` (Task 5); `check_result` (this task); `load_standard`, `tracked_files`.
- Produces (`gate_plan.py`):
  - `structural_criteria(plan_text: str) -> list[str]`: the bullet items under the first heading that starts
    with `## Structural acceptance criteria`, up to the next `## `.
  - `promised_paths(criteria: Sequence[str]) -> list[str]`: the backticked tokens ending in `.md` that have no spaces, `*` or `<`.
- Produces (`gate.py`):
  - `class GateError(Exception)`: the gate can't run (no test command declared, no plan recorded for the issue).
  - `@dataclass(frozen=True) class Check: criterion: int; name: str; passed: bool; detail: str = ""`
  - `@dataclass(frozen=True) class GateResult: checks: tuple[Check, ...]`, with `passed` (property).
  - `run_command(name: str, command: str, root: Path, timeout: int, run=subprocess.run) -> Check`: uses
    `shell=True` and writes the combined output to `.apm/tmp/gate/<name>.log`. On failure the detail is the
    last 20 lines, or `timed out after Ns`.
  - `gate(root: Path, issue: dict, workflow: Workflow, standard: Standard, base: str, run=subprocess.run) -> GateResult`, with checks in this order:
    - **1:** the tree is clean (`git status --porcelain`, ignoring `.apm/tmp/`); `base` is merged in
      (`git merge-base --is-ancestor`); no file is in two layers; then build, test and each checker. If the
      tree is dirty or `base` is not merged, the commands are reported `not run: <why>` and fail.
    - **2:** `check_result` passes.
    - **3:** a review is recorded, its `head` equals `HEAD`, and it has 0 open findings.
    - **4:** the plan file exists, every promised path exists, and the review recorded `criteria_met`. The
      detail lists the number of criteria and any missing paths.
  - `render_gate(result: GateResult) -> str`: one line per check, `PASS|FAIL  <criterion>  <name>  <detail>`,
    then `merge gate: passed` or `merge gate: N failed; stop and ask`.
- CLI: `apm gate N [--base REF]` (default `workflow.base`). It exits 0 when every check passes, 1 when any
  fails, and 2 on a `GateError`. It records nothing: the manager records the output as evidence.
  **This is where the full suite runs**, once, right before the PR.

- [ ] **Step 1: Write the failing tests** (a `git_repo` with an initialized profile and an injected `run` for commands):
  - `test_criteria_and_promised_paths` (Plan 2's real criteria section as a fixture).
  - `test_all_pass`, `test_dirty_tree_fails_and_skips_commands`, `test_base_not_merged_fails`,
    `test_failing_test_command_shows_tail_and_writes_log`, `test_command_timeout`,
    `test_layer_overlap_fails_criterion_1`, `test_debt_regression_fails_criterion_2`.
  - `test_stale_review_fails_criterion_3` (a commit after the review), `test_open_findings_fail_criterion_3`.
  - `test_missing_promised_doc_fails_criterion_4`, `test_criteria_not_met_fails_criterion_4`.
  - `test_no_test_command_is_gate_error_exit_2`, `test_no_plan_is_gate_error_exit_2`.
- [ ] **Step 2: Run** `python -m pytest tests/test_gate_plan.py tests/test_gate.py tests/test_cli_gate.py tests/test_cli_debt.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** (the refactor commit first, then the behavior).
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `"Extract the debt check result for reuse"` (refactor), then `"Gate every merge on the four criteria"`.

### Task 10: The workflow skills

**Files:**
- Create: `skills/initializing/SKILL.md` (+ `references/audit-report-template.md`, `references/auditor-brief.md`),
  `skills/running-an-issue/SKILL.md` (+ `references/issue-body-template.md`, `references/plan-summary-template.md`),
  `skills/merge-gate/SKILL.md`, `tests/test_skills_workflow.py`
- Modify: `agents/manager.md` (**the `## Skills` section only**: three trigger lines, so `test_agents.py`'s
  "every skill is named by an agent" holds)

**Skills and required headings** (Plan 2's harness rules apply: the first `##` is `## When this applies`, the
second is `## The core rule`, the last is `## Common mistakes`, and every reference file is linked):
- `initializing` (§6.1). Core rule: *nothing is overwritten until the user approves the audit, and nothing is
  approved while the coverage table shows a gap.* `## Existing or fresh`, `## Dispatching the auditors` (at
  most 3, on disjoint parts of the tree, reading from the audit's base, not the local checkout),
  `## The audit report`, `## The capability coverage table` (`.apm/audit/coverage.json`, inventoried rule by
  rule), `## In-flight work` (finish first, adopt or leave; stale worktrees reported, never removed; imported
  plans not approved), `## Overwrite versus keep` (methodology replaced; domain knowledge kept; methodology
  choices become declared overrides under `workflow`), `## Approval, then apply` (the init issue,
  `<CLI> init --issue N`, the tracked methodology edits with deletions on the allowlist, the PR),
  `## Debt issues` (adopted, not duplicated; new ones filed as a short ranked list grouped by area, with
  `<CLI> github file --kind debt`, after the user approves), and `## A fresh project` (`apm:design-first`, then
  a scaffold plan).
- `running-an-issue` (§6.2 and §6.3). Core rule: *after the request, the user has one touchpoint, plan
  approval; from approval to merge the manager runs without asking, unless something comes up the plan didn't
  settle.* `## Filing the issue` (`<CLI> github file`, the repo's templates and labels, a branch from the base,
  lane rules; if GitHub and state disagree, state wins), `## The size check`, `## Splitting into sub-issues`
  (`--parent`, status `split`), `## Planning`, `## The plan summary` (including the merge style when the
  profile declares none), `## Building`, `## Pacing` (lean by default: targeted tests per task, the full suite
  once through `<CLI> gate`, one whole-branch review; per-task review when the user asks, the profile says
  `per-task`, or a task touches `workflow.safety_critical`), `## A bug a worker finds` (`apm:debugger`, root
  cause and the wrong instruction behind it; related means its own commit on the same branch, unrelated means
  `<CLI> github file --kind bug`; a design change or a break of the standard is a stop and a question),
  `## Integrating` (`apm:merge-gate`, then `apm:finishing-a-branch`), `## Reporting` (`<CLI> github close`,
  what shipped), `## Lanes and the queue`, and `## Progress updates` (*one plain line after each task: what
  finished, what's next, rough time left*).
- `merge-gate` (§8.4). Core rule: *all four criteria hold, checked by the manager itself, or it doesn't merge;
  it never merges partway and never drops a criterion silently.* `## Running the gate`,
  `## Criterion 1: everything passes`, `## Criterion 2: no debt got worse`,
  `## Criterion 3: the final review is clean` (record it with `<CLI> review`; a commit after the review makes
  it stale), `## Criterion 4: the structure the plan promised`, and `## When a criterion cannot be met`.

- [ ] **Step 1: Write** `tests/test_skills_workflow.py`: `assert_sections` for the three skills, plus the phrases
  `one plain line`, `exactly once`, `<CLI> gate`, `<CLI> github file`, `<CLI> init`, `<CLI> review`, and
  `never removed`, each in the skill that owns it.
- [ ] **Step 2: Run** `python -m pytest tests/test_skills_workflow.py tests/test_skills.py tests/test_agents.py -q`. Expected: FAIL.
- [ ] **Step 3: Write the skills** and the three manager trigger lines. **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit** `"Carry the init, issue and merge-gate workflows as skills"`.

### Task 11: Lean pacing becomes the default

**Files:**
- Modify: `skills/executing-plans/SKILL.md` (`## Review after every task` becomes `## When to review`;
  verification uses targeted tests; the full suite runs at the gate), `skills/executing-plans/references/implementer-brief.md`,
  `skills/code-review/SKILL.md` (the final whole-branch review is the default; per-task only as above),
  `skills/test-first/SKILL.md` (each cycle runs the tests covering the change; the whole suite runs at the
  gate), `skills/worktrees/SKILL.md`, `skills/parallel-dispatch/SKILL.md` (targeted tests after each merge),
  `skills/writing-plans/SKILL.md` (the header blurb and step template match this plan's), `skills/systematic-debugging/SKILL.md`,
  `skills/verification/SKILL.md`, `tests/test_skills_process.py` (the renamed heading), `standard/coverage.json`
  (its two anchors on the old heading), `docs/coverage.md` (regenerated with `apm coverage --table`),
  `docs/specs/2026-10-17-apm-for-claude-design.md` (§6.2 step 5: an italic amendment pointing at the ADR)
- Create: `docs/adr/0001-lean-pacing-by-default.md` (context: the spec's per-task review and the user's
  pacing preference; decision; consequences; the three triggers for per-task review)

- [ ] **Step 1: Update** `tests/test_skills_process.py` to the new heading. **Step 2: Run** it. Expected: FAIL.
- [ ] **Step 3: Edit** the skills, the inventory and the spec, and write the ADR. Regenerate `docs/coverage.md`.
- [ ] **Step 4: Run** `python -m pytest tests/test_skills*.py tests/test_coverage.py -q` and `python scripts/apm_cli.py coverage`. Expected: PASS, and `Gaps: 0`.
- [ ] **Step 5: Commit** `"Make lean pacing the default: targeted tests, one gate, one final review"`.

*Ruling during Task 11: `docs/adr/README.md` (the ADR index `apm:adr` requires) was added outside the file list
and is kept. Two reference files still say "whole suite" (`skills/test-first/references/test-first-checklist.md`,
`skills/code-review/references/reviewer-checklist.md`); they are swept in Task 12 as a same-shape edit.
`test_skills_process.py` gained three tests (eight skills name `<CLI> gate`; no skill says "Review after every
task"; the two worktree files carry the ancestor check). Cost if wrong: one extra file.*

*Task 10 and Task 11 touch disjoint files and may run in parallel with each other and with Tasks 5 to 9.*

### Task 12: The agents run the workflows

**Files:**
- Modify: `agents/manager.md`, `agents/auditor.md`, `agents/debugger.md`, `agents/reviewer.md`, `agents/planner.md`, `agents/implementer.md`, `tests/test_agents.py`

**Interfaces:**
- Consumes: the CLI shapes from Tasks 5 to 9, and the skills from Task 10.
- Produces:
  - **Manager:** the "arrive in a later framework version" paragraph is replaced by `## The workflows`, which
    points at `apm:initializing`, `apm:running-an-issue` and `apm:merge-gate`. "Recording state" documents
    `<CLI> audit`, `<CLI> init`, `<CLI> github`, `<CLI> gate`, `<CLI> review` and `<CLI> note`. Workers may
    also run `<CLI> audit`. "Verifying work" uses targeted tests and says the full suite runs exactly once at
    the gate. "Talking to the user" asks for one plain line per update: what finished, what's next, rough time
    left. The merge style is asked at plan approval when the profile declares none.
  - **Auditor:** runs `<CLI> audit --json` and `<CLI> metrics --json --ref <base>`, and reports in-flight
    work, a draft profile (commands, layers, protected paths, `workflow` overrides, lanes) and a rule-by-rule
    inventory in the `coverage.json` shape. It never removes anything.
  - **Debugger:** follows §6.3 as written in `running-an-issue`. It fixes a wrong skill or agent instruction
    when its brief names the file. A wrong profile fact goes in its report for the manager to record.
  - **Reviewer:** the default job is the final whole-branch review. It reports each structural criterion as
    met or unmet, and the open findings count, for `<CLI> review`.
  - **Planner:** each task names its targeted test command. The plan's last task runs the gate.
  - **Implementer:** runs its task's targeted tests. It runs the full suite only if its brief says so.

- [ ] **Step 1: Write the failing tests**: `CLI_SUBCOMMANDS` gains `audit`, `init`, `github`, `gate`, `review`
  and `note`; the manager doesn't contain `later framework version`; it contains `## The workflows`,
  `one plain line` and `exactly once`; the reviewer contains `whole-branch`.
- [ ] **Step 2: Run** `python -m pytest tests/test_agents.py -q`. Expected: FAIL.
- [ ] **Step 3: Edit the agents.** **Step 4: Run** it. Expected: PASS.
- [ ] **Step 5: Commit** `"Point the agents at the workflows and lean pacing"`.

*Ruling during Task 12: `tests/test_agents.py` would have reached 239 lines of logic (over the file limit), so the
new workflow tests live in `tests/test_agents_workflow.py`. The manager's Skills line "after every task" now reads
as the whole-branch review. `test_manager_follows_the_process_skills_until_the_workflows_ship` was replaced by
`test_manager_points_at_the_workflows_instead_of_waiting_for_them` (on purpose; listed in the PR). The last "whole
suite" line, in `skills/test-first/references/cycle-steps.md`, is swept in Task 14. Cost if wrong: one test file.*

### Task 13: Release 0.3.0: live checks, one review, one gate, the PR

**Files:**
- Modify: `scripts/apm/__init__.py`, `.claude-plugin/plugin.json` (both `0.3.0`), `tests/test_manifest.py`
  if it pins the version, `docs/platform-notes.md`, `.apm/profile.json` (this repo's own `workflow` key:
  `commands.test` `python -m pytest -q`, the merge style the user chose, `review: end`, and `safety_critical`
  `["scripts/apm/guard*.py", "scripts/hook_*.py", "hooks/**"]`. The manager edits this file; workers can't.)

- [ ] **Step 1:** Bump the version. Run `python -m pytest tests/test_manifest.py -q`. Expected: PASS.
- [ ] **Step 2: Live checks** (manual; record each result in `docs/platform-notes.md`): reinstall the plugin, then
  (a) `<CLI> audit` in this repo, and read-only in VirtualAirline, recording the mode, the in-flight count and
  the notes; (b) a worker running `gh issue create` and `<CLI> note` is denied; (c) `<CLI> github file` filed
  this plan's tracking issue at the start of the build, and `<CLI> github close` closes it after the user merges.
- [ ] **Step 3: One whole-branch review** (`apm:reviewer`, `apm:code-review`). Fix the findings, then record it with `<CLI> review N`.
- [ ] **Step 4: Run** `<CLI> gate N`. This is the one full-suite run. Expected: `merge gate: passed`.
- [ ] **Step 5: Commit** `"Release the workflows as apm 0.3.0"`. Push, open the PR with the gate output and
  the live-check results, and list every changed existing test with the reason.

## Allowlisted actions
None. No task writes a protected path, deletes a file, or runs a destructive command. The `.apm/profile.json`
edit in Task 13 is the manager's own, under no protected path.

## Structural acceptance criteria (checked before the PR)
- Every runtime file is at most 200 lines of logic, and every runtime function at most 15
  (`test_framework_meets_its_own_limits`).
- `<CLI> debt check` passes against `main`.
- Every CLI subcommand is classified for workers (`test_every_subcommand_is_classified`), and a worker's `gh`
  writes are denied.
- `agents/manager.md` no longer says the workflows arrive in a later version.
- 25 skills exist, each passing `tests/test_skills.py`. `docs/coverage.md` ends with `**Gaps: 0**`.
- `docs/adr/0001-lean-pacing-by-default.md` exists, and spec §6.2 step 5 carries the italic amendment.
- `docs/platform-notes.md` records the Task 13 live checks.
- No existing test was weakened. Each changed test (the renamed heading, the subcommand lists) is listed in the
  PR with its reason.
- The version is `0.3.0` in `scripts/apm/__init__.py` and `.claude-plugin/plugin.json`.

## Pre-flight scan

*Recorded by the manager before Task 1, 2026-10-18.*

| Pair or task | Produces → consumes | Found |
|---|---|---|
| 1 → 8, 9 | `load_workflow`, `Workflow` | Names agree. |
| 2 ↔ 5–9 | denylist and `SUBCOMMANDS` vs the new parsers | The classification test walks only the parser's real choices, so it holds at each step. `test_guard_debt` checks a subset only. |
| 3 ↔ 5 | both modify `cli_parser.py` (`_metrics` vs `build_parser`/`_issue`) | Same file: run in sequence (5, then 3). |
| 3 → 7, 9 | `measure_at_ref`, `ref_files`, `layer_overlaps` | Names agree. |
| 4 → 9 | `TMP_IGNORE` (`.apm/tmp/`) | Agree; the gate's clean-tree check ignores it too. |
| 5 → 6, 8, 9 | `set_parent`, `add_note`, `issue["review"]`, `issue["plan"]`, `REQUIREMENTS` | Agree; `gate: state` in Task 5 matches Task 9's need for the ledger. |
| 6 → 7 | `list_open_issues`, `GitHubError` | Agree. |
| 7 → 8 | audit JSON (`mode`, `base`, `in_flight[].id`, `debt_issues`) | Agree. |
| 10 ↔ 12 | both modify `agents/manager.md` | Same file: run in sequence (10, then 12). |
| 10 ↔ 11 | new skill directories vs existing skills | Disjoint. |
| Task 5 | `apm issue N --parent P` | Self-consistent with a ruling (below). |
| Task 9 | the criteria fixture | Uses Plan 2's real criteria section, copied into `tests/fixtures/`. |
| Task 13 | live check (c) | Filing "at the start of the build" is impossible before Task 6 exists; see the ruling. |
| Rubric | — | Nothing the plan mandates is a defect by the review rubric. |

*Ruling before Task 1: build order is 1, 2 and 5 in parallel, then 6, then 3 and 4 beside it, then 7, 8, 9,
with 10 and 11 beside them, then 12, then 13. Task 5 comes forward so that Task 6's `apm github file` exists
to file this plan's tracking issue, as the user asked; nothing that was decided changes. Cost if wrong: none.*

*Ruling before Task 1 (Task 5): `apm issue N --parent P` goes through `set_parent`, so the parent is
validated; it is not passed through `upsert_issue` as a plain field. Cost if wrong: one handler line.*

*Ruling before Task 1 (Task 13, check c): the tracking issue is filed with `apm github file` right after
Task 6 merges, from this branch's own CLI. Tasks 1, 2 and 5 are recorded under it once it exists. Cost if
wrong: those three records are written a little late.*

*Ruling before Task 1 (pacing): the user's build instructions and Global Constraints set lean pacing for this
build, so `apm:executing-plans`' per-task review applies only to Task 2 (safety-critical). Workers run the
targeted tests; the manager verifies each task with the same tests plus `test_own_limits` and `debt check`.*

## Added during the build

*Added 2026-10-18 at the user's request, mid-build: user documentation. Built after Task 12 and before Task 13,
so it describes the finished commands; Task 13's PR includes it.*

### Task 14: A README and a short tutorial

**Files:**
- Create: `README.md`, `docs/tutorial.md`, `tests/test_docs.py`

**Interfaces:**
- Consumes: the subcommands from `build_parser()` (Tasks 5 to 9), the three workflow skills (Task 10), the lean
  pacing defaults (Task 11), and the profile keys `standard` (Plan 2) and `workflow` (Task 1).
- Produces:
  - `README.md` (short): what APM is in two or three sentences (the manager is your one point of contact;
    workers build in worktrees; safety hooks; the debt ratchet); requirements (Claude Code, Python 3.12+, git,
    and `gh` optionally); install from the `rogue-sentinel` marketplace; `apm setup`; a five-line quick start;
    and links to the tutorial, the spec and `docs/coverage.md`.
  - `docs/tutorial.md`: a walkthrough on a small example project, each step showing **what you say** to the
    manager, **what it does** (the commands it runs, shortened real output), and **what you decide**. The
    sections are `## 1. Install and set up`, `## 2. Initialize a project` (the audit report, the coverage
    table, in-flight decisions, approval), `## 3. Ask for a feature` (the filed issue, the plan summary, your
    one approval, the one-line progress updates, the gate, the PR), `## 4. Report a bug`,
    `## 5. When a worker finds a bug`, `## 6. Ask where things stand` (`brief`), `## 7. When the guard says
    no` (a denial, your approval in chat, the 10-minute `approve`), `## 8. Debt`, `## 9. Settings you can
    change` (a commented `profile.json` example covering `workflow`, `standard` and `models`), and
    `## 10. Troubleshooting` (no `gh`, a failed gate, a stale review).
  - `tests/test_docs.py`: every `apm <word>` and `<CLI> <word>` in both files names a real subcommand; every
    relative link resolves; no British spelling from Plan 2's list; the tutorial has the ten headings above.

- [ ] **Step 1: Write** `tests/test_docs.py`. **Step 2: Run** `python -m pytest tests/test_docs.py -q`. Expected: FAIL (no files).
- [ ] **Step 3: Write** both documents in plain language, with examples taken from real command output on this branch.
- [ ] **Step 4: Run** the test. Expected: PASS.
- [ ] **Step 5: Commit** `"Add a README and a short tutorial"`.

*Structural acceptance criterion added: `README.md` and `docs/tutorial.md` exist and pass `tests/test_docs.py`.*

*Ruling during Tasks 1, 2 and 5 (found in the build): the platform's `isolation: "worktree"` cut all three
workers' worktrees from `main`'s tip, not from the feature branch, so none could see this plan. All three
stopped as briefed, changing nothing; each was resumed with `git merge --ff-only claude/plan-3-apm-workflows-57bbf0`.
The instruction behind it was wrong: `apm:worktrees` and the implementer brief assume a native worktree starts
from the session's branch. Task 11 (which already edits both files) adds: a native worktree may start from the
default branch, so the worker checks that the recorded BASE is an ancestor of HEAD, and if it is not,
fast-forwards to the feature branch (`--ff-only`) and reports if that refuses. Task 13 records the platform fact
in `docs/platform-notes.md`. Cost if wrong: two paragraphs of skill text.*

## Deferred findings

- Task 1: `workflow_config.py` copies `_known`, `_object` and `_text` (about 15 lines) from `standard_config.py`
  rather than sharing them; sharing would touch a file outside the task. The final review decides.
- Task 1: the worker added an unknown-key check (a typo such as `gate_timout` raises `ProfileError`), matching
  `standard_config`; the brief did not ask for it. `lane_for([])` returns `None`. The final review decides.
- Task 5: `set_parent` rejects self and unknown parents, not longer cycles (a under b under a). The final review decides.
- Task 5: `_mutate` moved to `cli_workflow.mutate` (refactor commit 84fdbd5) to avoid a circular import.
- Task 2 review S4: test-first cannot be confirmed per assertion from history (one commit); the worker's
  mutation check partly covers it.
- Task 2 review S5: `test_every_subcommand_is_classified` reads argparse internals; a public
  `subcommand_names()` would be sturdier.
- Task 2 review (found elsewhere): the worker path check reads a grep pattern holding `.*\` as the protected path
  `.*/` (a false positive in Plan 1 code).
- Task 3: `ref_files` runs `git ls-tree` without `-z`, so a git-quoted file name may be mangled; a gitlink whose
  `git show` fails is skipped silently. Existing test `test_report_json_carries_every_number` gained
  `"plain": False` on purpose.
- Task 6: `apm github close` prints a by-hand hint when `gh issue close` fails (not in the brief);
  `--parent` is checked before `gh` is called.
- Task 4: test_setup_gitignore_without_trailing_newline now also expects `.apm/tmp/` (on purpose). The guard denied a worker's heredoc whose text held `.apm/tmp` as a write to `.apm/` (a Plan 1 false positive; the worker used the Edit tool).
- Task 8: the finish-first check passes when either the local branch or `origin/<name>` is merged into the base (`any`), so a merged local branch with `origin/<name>` ahead passes; `apply` takes `run` but does not use it; refusals print to stdout. The final review decides.
- Task 2 re-review S2: the read allowlist denies a worker's `git commit -m "$(cat <<'EOF' ... EOF)"` whose message
  mentions a `gh` write, because `mask_data` does not mask a quoted-tag heredoc substitution (Plan 1 code in
  `guard_data.py`). The final review decides.
- Task 2 re-review S6: `_RUN_STRING` (`-\w*c`) also matches `grep -c` and `head -c` (false positives that fail
  closed).
