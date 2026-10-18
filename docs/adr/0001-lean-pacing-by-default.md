# ADR-0001: Lean pacing is the default

## Status

Accepted, 2026-10-18.

Amends the build step of the design spec, section 6.2 step 5.

## Context

The design spec (section 6.2, step 5) has the manager run the verification and dispatch a reviewer after
every task: "After each task: the manager runs the verification itself, a reviewer checks the diff, failures
go back with findings, and state is updated." Plans 1 and 2 were built that way, and the skills
(`apm:executing-plans`, `apm:test-first`, `apm:verification`) carried it: the project's whole test suite after
every cycle and every merge, and a reviewer after every task.

The user, who owns this framework and runs it, chose a different pace: run targeted tests while working, run
the full suite once right before the pull request, review the whole branch once at the end, and keep updates
short and plain. The reasons are cost and time. A suite run after every task repeats the same checks the
targeted tests already made, and a reviewer per task spends the most capable model on diffs the final review
reads anyway. Plan 3 (`docs/plans/2026-10-18-plan-3-workflows.md`, Global Constraints) carries the preference as a
build constraint.

Speed is not worth losing the checks that catch real harm. The decision keeps three of them as explicit
triggers for a review of a single task.

## Decision

**Lean pacing is the framework default.**

- **Targeted tests while working.** A worker and the manager run the task's own tests and the tests for the
  files the task changed. Nobody runs the whole suite per task or per merge.
- **The full suite runs exactly once**, through `<CLI> gate`, right before the pull request. It runs a second
  time only if the gate failed and something changed.
- **One whole-branch review at the end**, on the most capable model, as before (merge gate criterion 3). It is
  never skipped.
- **A plain progress line after each task:** what finished, what is next, and roughly how much time is left.
- **A review of a single task, before the next task starts, happens only in three cases:**
  1. the user asks for it;
  2. the profile says `"review": "per-task"`;
  3. the task touches a path in the profile's `workflow.safety_critical`.

  When a task review runs, the fix loop and the retry rule of `apm:executing-plans` apply to it unchanged.

The skills carry the rule: `apm:executing-plans` (the heading `## When to review` replaces
`## Review after every task`), `apm:code-review`, `apm:test-first`, `apm:verification`,
`apm:systematic-debugging`, `apm:parallel-dispatch`, `apm:worktrees` and `apm:writing-plans`.

## Consequences

- **Faster and cheaper builds.** The suite and the reviewer run once instead of once per task.
- **A defect that only the full suite shows is found later.** A task can pass its targeted tests and break a
  distant test; the gate finds it right before the pull request, after more work sits on top. The fix is then
  one wave against the whole branch, not a one-task fix. The targeted set (the tests for every changed file)
  is the defense, and a worker that sees a break outside it reports it.
- **A defect a task review would have caught is found at the end.** The final review sees the whole diff, so
  it still sees the defect, but a later task may have built on it. The three triggers cover the cases where
  that cost is highest: a path the project marked safety-critical, a user who wants the closer look, and a
  project that chose per-task review.
- **The triggers depend on honest configuration.** A project that never fills `workflow.safety_critical` gets
  no automatic per-task review. The audit at init is where those paths are named.
- **The spec's text is amended, not rewritten.** Section 6.2 step 5 keeps its wording and gains one italic
  sentence pointing here.

## Alternatives considered

- **Keep a review after every task.** The spec's original rule. Rejected: it spends the most capable model
  on every diff, and the final review reads the same diffs again.
- **Run the full suite after every task, review once.** Rejected: the same checks run many times, and the
  gate must run the full suite regardless.
- **No per-task review at all.** Rejected: a change to a safety-critical path, such as the guard, is where a
  late finding costs the most, and a user who asks for a closer look must get one.
- **Make pacing a profile option with no default.** Rejected: an unconfigured project would silently get one
  of two behaviors. A default, with `"review": "per-task"` as the opt-in, keeps the first run predictable.
