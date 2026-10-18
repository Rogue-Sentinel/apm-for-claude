# The implementer brief

The manager uses this when it dispatches a worker to build one task. The worker's own agent
definition already carries its standing rules (test-first, stay in your files, never talk to the
user, never run state-changing commands, the structured report). This brief adds the task.

## Dispatch

- `subagent_type: "apm:implementer"` (or `"apm:debugger"` for a bug fix).
- `model`: chosen per "Choosing the model" in `apm:executing-plans`, and always set explicitly. An
  omitted model silently inherits the session's, usually the most expensive one.
- `isolation: "worktree"`, always, alone or in parallel.
- Fill BASE and FEATURE_BRANCH in Step 0 of the brief below.

```
You are implementing Task N: [task name], for issue #[N].

## Step 0: put your worktree on the feature branch (do this first)

A native worktree may start from the default branch, not from the feature branch, so you
could be missing the plan and the earlier tasks. In your own worktree:
1. Run `git rev-parse --show-toplevel`. It must be your own new worktree. If it is the
   manager's checkout or the repository root, stop and report "blocked: not in my own
   worktree"; never build there.
2. Check that BASE ([BASE]) is an ancestor of HEAD:
   `git merge-base --is-ancestor [BASE] HEAD && echo ok`.
3. If it is not, run `git merge --ff-only [FEATURE_BRANCH]`, then check again. If the
   fast-forward refuses, stop and report; do not merge any other way.
Report the outputs as BASE.

## Your task

Read your brief first: [PLAN_PATH], section "### Task N", and its "Global Constraints".
[or: BRIEF_FILE]
It is your requirements, with the exact values to use verbatim. Do not read the rest
of the plan.

## Context

[One line on where this task fits. Interfaces and rulings from earlier tasks that the
brief cannot know. Your resolution of any ambiguity in the brief. A pointer to any
deferred finding recorded in the area this task touches.]

## Your files

You own exactly these: [files from the brief]. Stay inside them. If the task turns out
to need a change anywhere else, stop and report it; do not reach into another file.

## Project knowledge

[The facts from the profile this task needs: commands, layer map, domain warnings.]

## Before you begin

If anything about the requirements, the acceptance criteria, the approach, the
dependencies or your assumptions is unclear, do not guess. Return now with status
"needs decision" and the specific question.

The same holds mid-task. If you meet something unexpected or unclear while you work,
stop and return "needs decision" with what you found and the question, rather than
guessing and building on the guess. Commit nothing half-done; say in the report where
you stopped.

Then run the targeted tests once in your worktree, before you change anything (the tests
for the files you will change), and report the result. If the baseline already fails,
stop and report the failures: whether to proceed is the manager's call. A dirty baseline
makes every later failure ambiguous.

Run targeted tests only, throughout. Do not run the whole suite: the manager runs it
exactly once, through `<CLI> gate`, right before the pull request.

## Your job

Load apm:test-first before you start; it governs every step below.

1. Write the failing test the brief names. Run it. Confirm it fails for the right reason.
2. Write the least code that makes it pass. Run it. Confirm it passes.
   (A pure-move refactoring task has no new failing test: run the suite before the move,
   move the code without changing any test, and run it again. The evidence is the same
   tests passing on both sides.)
3. Refactor if needed, in a separate commit. Refactor and behavior never share a commit.
4. Before you commit, run the task's own tests and the tests for the files you changed,
   once, not after every edit; while iterating, run the focused test for what you are
   changing.
5. Commit, using the brief's commit message.
6. Review your own work (below), then report.

Work from: [worktree path]. Use the project's limits, layer rules and spelling.

## You do not dispatch workers

Do all of this task yourself. Never spawn a helper, and above all never spawn a reviewer
to check your work. Review is the manager's job, and it is already scheduled.

## Code organization

- Follow the file structure the plan defines. Each file has one clear responsibility.
- If a file you are creating grows beyond the plan's intent, stop and report it as a
  concern. Do not split files on your own without the plan.
- If a file you are changing is already large or tangled, work carefully and note it as
  a concern. If it is over a limit and the plan has no extraction task for it, stop and
  report it: you do not add to an over-limit file.
- In an existing codebase, follow its patterns. Improve code you touch as a good
  developer would, but do not restructure anything outside your task.

## When you are in over your head

It is always fine to stop and say "this is too hard for me". Bad work is worse than no
work, and escalating is never penalized. Stop and return "blocked" or "needs decision"
when:
- the task needs an architectural decision with several valid approaches;
- you need to understand code beyond what you were given and cannot find clarity;
- you are unsure whether your approach is correct;
- the task restructures existing code in a way the plan did not anticipate;
- you have read file after file without making progress.
Say exactly what you are stuck on, what you tried, and what help you need.

## Before reporting: review yourself

- Completeness: did I implement everything the brief asks? Miss any requirement? Any
  edge case unhandled?
- Quality: is this my best work? Do the names say what things do, not how?
- Discipline: did I build only what was asked, and nothing extra? Follow existing
  patterns?
- Testing: do the tests verify real behavior, not a mock's? Did I watch each new
  behavior test fail first? Is the output clean, with no stray warnings?
Fix what you find before you report.

## After review findings

If the review finds problems, you will be sent the findings. Fix them, re-run the tests
that cover what you changed, and report what you changed, the covering tests, the
command and its output. The reviewer will not re-run tests for you: your report is the
test evidence.

## Report

[If the evidence will be long: write the full output to REPORT_FILE, in the system
temp directory, and append each fix round's report to the same file. Then return the
structured report below, short, with that path.]

Return the structured report and nothing else:
- status: done, blocked, or needs decision (done with doubts is "done", with the
  doubts under concerns; never silently hand over work you are unsure about)
- files changed
- commands run, with their actual output, including:
  - BASE: the worktree path and the ancestor check from Step 0
  - BASELINE: the targeted test command run before any change, and its result
  - RED: the command, the failing output, and why that failure was expected
  - GREEN: the command and the passing output
  - for a pure-move refactoring, instead of RED and GREEN: the suite before and after
    the move, both passing, with no test edited
- commits created (short hash and subject)
- concerns
- found elsewhere
```
