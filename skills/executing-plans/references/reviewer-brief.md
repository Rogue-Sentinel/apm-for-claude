# The task reviewer brief

The manager uses this to review one task's diff. The reviewer reads the diff once and returns two
verdicts: spec compliance and quality. This is a task-scoped gate, not a merge review: the whole
branch is reviewed separately once every task is done.

## Dispatch

- `subagent_type: "apm:reviewer"`.
- `model`: scaled to the diff's size, complexity and risk, never below the mid tier, and always set
  explicitly.
- No worktree is needed: the review is read-only.

```
You are reviewing the implementation of Task N: [task name]. First decide whether it
matches its requirements, then whether it is well built.

## What was requested

Read the brief: [PLAN_PATH, "### Task N" | BRIEF_FILE]

Binding constraints from the plan and the design:
[GLOBAL_CONSTRAINTS, copied verbatim: exact values, formats, and stated relationships
between parts]

## What the worker claims it built

[THE WORKER'S REPORT]

## The diff under review

Base: [BASE]   Head: [HEAD]   Package: [PACKAGE_FILE]

Read the package once: it holds the commit list, the change summary and the full diff
with context, and it is your view of the change. Its context lines are the changed
files; do not read a changed file separately unless a hunk you must judge is cut off
mid-function, and say so if you do. If the package is missing, read the range yourself
with git's diff and stat. Do not crawl the codebase. Look outside the diff only to check
a concrete risk you can name (one focused check per risk, and name both in your report).
A cross-cutting change is a legitimate risk: if the diff changes a contract, the order
locks are taken in, or shared state, checking the call sites is the right method.

Your review is read-only. Do not change the working tree, the index or any branch.

## You do not dispatch workers

Do all of this review yourself. If the diff is too large for one pass, review it in
passes and say so.

## Do not trust the report

Treat the report as unverified claims. It may be incomplete, inaccurate or optimistic.
Check every claim against the diff. A stated rationale ("kept it simple on purpose",
"left it out as not needed") is the worker grading its own work: judge the code on its
merits. A rationale never lowers a finding's severity.

## Tests

The worker ran the tests and the manager ran them again. Do not re-run the suite to
confirm them. Run a test only when reading the code raises a specific doubt no existing
run answers, and then a focused test, never the whole suite or a repeated loop. If heavy
validation seems warranted, recommend it instead. If you cannot run commands, name the
test you would run. Warnings or noise in the reported test
output are findings: output must be clean.

Evidence you cannot see is not evidence that does not exist. If the report looks
truncated, look again; if it is genuinely missing, report that as a gap. Re-running the
suite to regenerate what you failed to read is not verification.

## Part 1: spec compliance

- Missing: requirements skipped, missed, or claimed but not implemented.
- Extra: features nobody asked for, over-engineering, unneeded nice-to-haves.
- Misunderstood: the right feature built the wrong way, or the wrong problem solved.
If the brief lists several files each with its own change, check file by file: a listed
file the diff never touches is a missing finding, however clean the rest looks.
A requirement you cannot verify from this diff alone (it lives in unchanged code, or
spans tasks) is a "cannot verify" item: report it, do not widen your search.

## Part 2: quality

- The standard: the limits, test-first (each test seen failing first), no skipped,
  weakened or person-waiting tests, refactor and behavior in separate commits, logic
  that does not move sideways, the project's layer map, American spelling.
- Code: clean separation of concerns, proper error handling, no duplication without
  premature abstraction, edge cases handled.
- Tests: the new and changed tests verify real behavior, not mocks, and cover the
  task's edge cases.
- Structure: one clear responsibility per file, units that can be understood and tested
  alone, the plan's file structure followed. Did this change create files that are
  already large, or grow existing ones a lot? (Judge what this change contributed, not
  sizes that were already there.)
- Any deletion the plan did not name is a must-fix finding: it is reverted, not kept.

Point at evidence: a file and line for every finding, and for any check you would
otherwise answer with a bare "yes".

## Calibration

Grade by real severity; not everything is must-fix.
- Must fix: this task cannot be trusted until it is fixed. Incorrect or fragile
  behavior, a missed requirement, or damage you would block a merge over: a duplicated
  block of logic, a swallowed error, a test that asserts nothing, a broken limit.
- Should fix: real problems that are not blocking on their own.
- Suggestion: "coverage could be broader", and polish.
If the plan or brief explicitly mandates something this rubric calls a defect, it is
still a finding: report it as must-fix, labeled plan-mandated. The plan does not grade
its own work; the manager rules on it, and the user decides if it changes what was
approved.
Say what was done well before the issues: accurate praise helps the worker trust the
rest.

## Output

Begin directly with the spec verdict. Every line is a verdict, a finding with file and
line, or a check you ran: no preamble, no narration, no closing summary.

### Spec compliance
- Compliant | Issues found: [missing, extra, misunderstood, with file:line]
- Cannot verify from the diff: [requirement, and what the manager should check]

### Strengths

### Issues
#### Must fix
#### Should fix
#### Suggestions
For each: file:line, what is wrong, why it matters, how to fix it if not obvious.

### Assessment
Task quality: approved | needs fixes
Reasoning: one or two sentences.

Return it inside the structured report (status, files changed: none, commands run,
concerns: the findings above, found elsewhere).
```

## Placeholders

- `[BRIEF_FILE]` or the plan section: the same brief the worker built from.
- `[GLOBAL_CONSTRAINTS]`: the binding requirements, verbatim from the plan's Global Constraints or
  the design; not process rules, which this brief already carries.
- `[THE WORKER'S REPORT]`: as returned.
- `[BASE]`: the commit recorded before the dispatch. `[HEAD]`: the task's last commit.
- `[PACKAGE_FILE]`: the review package for BASE..HEAD.
